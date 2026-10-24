"""Independent exact-key Delta readback for a protected Vault run."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import Denied, canonical, digest, file_digest, verified_document
from edp_lab.vault.broker_v2 import _eligibility, _protected, _signed, load_run_grant
from edp_lab.vault.protected_readback import COLS, _normalized, _sign
from edp_lab.vault.protected_sql import _cli, statement
from edp_lab.vault.standing_v2 import NAMESPACE, TABLES, pinned_path, validate_standing_policy

KEYS = {
    "h_filing": ("filing_hk",),
    "h_concept": ("concept_hk",),
    "l_fact_slot": ("fact_slot_hk",),
    "r_source_occurrence": ("occurrence_hk",),
    "s_fact_assertion": ("assertion_hk",),
    "s_num_m2_value": ("occurrence_hk", "field_ordinal", "conversion_rule_version"),
    "r_load_event": ("occurrence_hk", "execution_id"),
    "vault_reject_quarantine": ("input_identity", "execution_id"),
}


def _literal(value: object) -> str:
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        raise Denied("VAULT_EXPECTED_FIELD_NOT_LEXICAL")
    return "decode(unhex('" + value.encode("utf-8").hex() + "'), 'UTF-8')"


def _where(name: str, rows: list[list]) -> str:
    columns = COLS[name]
    indices = [columns.index(key) for key in KEYS[name]]
    terms = []
    for row in rows:
        parts = []
        for index in indices:
            literal = _literal(row[index])
            if columns[index] == "field_ordinal":
                literal = f"CAST({literal} AS BIGINT)"
            parts.append(f"{columns[index]} <=> {literal}")
        terms.append("(" + " AND ".join(parts) + ")")
    return " OR ".join(terms)


def _expected(plan: dict) -> dict[str, list[list]]:
    tables = plan.get("expected_tables")
    if not isinstance(tables, dict) or set(tables) != set(TABLES):
        raise Denied("VAULT_EXPECTED_TABLE_SET_INVALID")
    values = {}
    for name in TABLES:
        item = tables[name]
        rows = item.get("rows")
        if (item.get("columns") != list(COLS[name]) or not isinstance(rows, list)
                or (not rows and name not in {"s_num_m2_value", "r_load_event",
                                              "vault_reject_quarantine"})
                or any(not isinstance(row, list) or len(row) != len(COLS[name])
                                for row in rows)):
            raise Denied("VAULT_EXPECTED_ROWS_INVALID")
        keys = [tuple(row[COLS[name].index(key)] for key in KEYS[name]) for row in rows]
        if len(set(keys)) != len(keys):
            raise Denied("VAULT_EXPECTED_KEY_DUPLICATE")
        values[name] = rows
    return values


def attest(root: Path, base: Path, grant_path: Path) -> dict:
    _protected(root, base)
    policy = _signed(root, base, "policy.signed.json")
    validate_standing_policy(policy, root=root)
    grant = load_run_grant(root, base, grant_path)
    receipt = _eligibility(root, base, grant["cohort_id"], policy)
    plan_path = pinned_path(root, receipt["load_plan"]["path"], base)
    if file_digest(plan_path) != grant["load_plan_sha256"]:
        raise Denied("VAULT_VERIFIER_PLAN_CHANGED")
    plan = json.loads(plan_path.read_bytes())
    expected = _expected(plan)
    if expected["r_load_event"]:
        raise Denied("VAULT_PLAN_EMBEDDED_RUN_EVENTS_DENIED")
    expected["r_load_event"] = [
        [row[0], grant["run_id"], grant["event_kind"], None,
         grant["input_manifest_sha256"]]
        for row in expected["r_source_occurrence"]
    ]
    ledger = base / "ledger" / grant["run_sha256"]
    for index, stage in enumerate(plan["stages"], 1):
        record = ledger / f"{grant['run_sha256']}-{index:03d}.json"
        if (not record.is_file() or json.loads(record.read_bytes()).get("status")
                != "STAGE_READBACK_VERIFIED"):
            raise Denied("VAULT_STAGE_NOT_VERIFIED")
    audit = ledger / (grant["run_sha256"] + "-audit.json")
    if (not audit.is_file() or json.loads(audit.read_bytes()).get("status")
            != "STAGE_READBACK_VERIFIED"):
        raise Denied("VAULT_RUN_AUDIT_NOT_VERIFIED")
    budget = {"run_sha256": grant["run_sha256"],
              "max_statements": grant["max_statements"],
              "max_runtime_seconds": grant["max_runtime_seconds"]}
    checks = {}
    for name in TABLES:
        full = f"{NAMESPACE}.{name}"
        if name == "s_num_m2_value":
            occurrences = [row[0] for row in expected["r_source_occurrence"]]
            where = "occurrence_hk IN (" + ", ".join(_literal(value) for value in occurrences) + ")"
        elif name == "vault_reject_quarantine":
            executions = {row[1] for row in expected[name]} or {grant["run_id"]}
            where = "execution_id IN (" + ", ".join(_literal(value)
                                                       for value in sorted(executions)) + ")"
        else:
            where = _where(name, expected[name])
        sql = f"SELECT {', '.join(COLS[name])} FROM {full} WHERE " + where
        response = statement(root, base, sql, budget=budget)
        if response.get("manifest", {}).get("total_chunk_count") != 1:
            raise Denied("VAULT_READBACK_CHUNKING_UNSUPPORTED")
        actual = response.get("result", {}).get("data_array", [])
        if _normalized(actual) != _normalized(expected[name]):
            raise Denied("VAULT_EXACT_DELTA_READBACK_MISMATCH_" + name.upper())
        uc = _cli(root, base, "api", "get", "/api/2.1/unity-catalog/tables/" + full)
        if (uc.get("full_name") != full or uc.get("data_source_format") != "DELTA"
                or not uc.get("table_id")):
            raise Denied("VAULT_DELTA_TABLE_IDENTITY_MISMATCH")
        checks[name] = {"rows": len(actual), "statement_id": response["statement_id"],
                        "uc_table_id": uc["table_id"],
                        "rows_sha256": digest(canonical(sorted(
                            (list(row) for row in _normalized(actual).elements()),
                            key=lambda row: json.dumps(row, sort_keys=True))))}
    document = {"schema": "EDP_VAULT_RUN_READBACK_RECEIPT_V2",
                "authority": "protected-verifier-v1", "status": "VERIFIED",
                "run_sha256": grant["run_sha256"], "grant_id": grant["grant_id"],
                "cohort_id": grant["cohort_id"], "namespace": NAMESPACE,
                "workload_kind": grant["workload_kind"],
                "load_plan_sha256": grant["load_plan_sha256"],
                "checks": checks, "verified_at_utc": datetime.now(UTC).isoformat()}
    output = base / "receipts" / (grant["run_sha256"] + ".signed.json")
    if output.exists():
        previous = verified_document(root, output, base / "trust")
        if any(previous.get(key) != value for key, value in document.items()
               if key != "verified_at_utc"):
            raise Denied("VAULT_READBACK_RECEIPT_CHANGED")
    else:
        _sign(document, base / "private/verifier.pem", output)
    return {"status": "VAULT_RUN_READBACK_VERIFIED", "receipt_path": str(output),
            "receipt_sha256": file_digest(output),
            "rows": {name: check["rows"] for name, check in checks.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("root", "base", "grant"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(attest(args.root, args.base, args.grant), sort_keys=True))


if __name__ == "__main__":
    main()
