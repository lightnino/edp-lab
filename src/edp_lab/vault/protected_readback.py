"""Separate protected exact-row Delta readback and signed Vault receipt."""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    load_grant,
    verified_document,
)
from edp_lab.vault.load_plan import NAMESPACE, TABLES
from edp_lab.vault.protected_sql import _cli, statement
from edp_lab.vault.standing_authority import signed_policy, validate_policy

COLS = {
    "h_filing": ("filing_hk", "source_namespace", "adsh"),
    "h_concept": ("concept_hk", "source_namespace", "tag", "version"),
    "l_fact_slot": ("fact_slot_hk", "filing_hk", "concept_hk", "context_json"),
    "r_source_occurrence": ("occurrence_hk", "source_instance_id", "archive_member",
                            "member_sha256", "byte_offset", "byte_length", "source_line",
                            "raw_path", "raw_sha256", "binding_sha256", "m1_run_id",
                            "record_kind", "fields_json"),
    "s_fact_assertion": ("assertion_hk", "fact_slot_hk", "occurrence_hk",
                         "parser_contract_version", "parser_profile_id", "m1_model_version",
                         "m1_rule_version", "payload_hashdiff", "value_lexical",
                         "footnote_lexical"),
    "s_num_m2_value": ("occurrence_hk", "field_ordinal", "source_rule_version",
                       "model_version", "conversion_rule_version", "lexical_value",
                       "value_decimal", "conversion_outcome", "conversion_reason"),
    "r_load_event": ("occurrence_hk", "execution_id", "event_kind", "statement_id",
                     "input_manifest_sha256"),
    "vault_reject_quarantine": ("input_identity", "execution_id", "reason_code",
                                "reason_detail",
                                "source_instance_id", "archive_member", "member_sha256",
                                "byte_offset", "byte_length", "source_line", "raw_sha256",
                                "binding_sha256", "input_json", "synthetic_negative_control"),
}


def _expected(rows: list[dict]) -> dict[str, list[tuple[str | None, ...]]]:
    filing = {(r["filing_hk"], "SEC_FSDS", r["adsh"]) for r in rows}
    concept = {(r["concept_hk"], "SEC_FSDS", r["tag"], r["version"]) for r in rows}
    slot = {(r["fact_slot_hk"], r["filing_hk"], r["concept_hk"], r["context_json"])
            for r in rows}
    occurrence = [(r["occurrence_hk"], r["source_instance_id"], r["archive_member"],
                   r["member_sha256"], str(r["byte_offset"]), str(r["byte_length"]),
                   str(r["source_line"]), r["raw_path"], r["raw_sha256"],
                   r["binding_sha256"], r["run_id"], "DATA", r["fields_json"]) for r in rows]
    assertion = [tuple(r[name] for name in COLS["s_fact_assertion"]) for r in rows]
    m2 = [(r["occurrence_hk"], "9", r["m2_source_rule_version"],
           r["m2_model_version"], r["m2_rule_version"], r["value_lexical"],
           r["m2_decimal"], r["m2_outcome"], r["m2_reason"]) for r in rows]
    events = [(r["occurrence_hk"], execution, kind, None,
               "366ca59ac251fa54d0a2c97ebdd8f9cacbcf773231c61aa20a504196a3cf31dc")
              for kind, execution in (("ADMITTED", "day6-vault-proto-c1500-first-v1"),
                                      ("REPLAY", "day6-vault-proto-c1500-replay-v1"))
              for r in rows]
    first = rows[0]
    negatives = []
    for reason, mutation in (
        ("REPLAY_DRIFT", {"value_lexical": "SYNTHETIC_CHANGED_VALUE"}),
        ("FIELD_ORDER_MISMATCH", {"field_order": "REVERSED"}),
        ("MEMBER_SHA_MISMATCH", {"member_sha256": "0" * 64}),
        ("BAD_BYTE_LOCATOR", {"byte_offset": first["byte_offset"] + 1}),
        ("MISSING_BUSINESS_KEY_COMPONENT", {"adsh": ""}),
        ("M2_INELIGIBLE", {"field_ordinal": 8}),
    ):
        input_json = json.dumps({"original_occurrence_hk": first["occurrence_hk"],
                                 "mutation": mutation,
                                 "original_fields_json": first["fields_json"]},
                                sort_keys=True, separators=(",", ":"))
        negatives.append(("SYNTHETIC_NEGATIVE_" + reason,
                          "day6-vault-proto-c1500-negative-v1", reason,
                          "Controlled synthetic mutation; reject promotion",
                          first["source_instance_id"], first["archive_member"],
                          first["member_sha256"], str(first["byte_offset"]),
                          str(first["byte_length"]), str(first["source_line"]),
                          first["raw_sha256"], first["binding_sha256"], input_json,
                          "true"))
    return {"h_filing": list(filing), "h_concept": list(concept),
            "l_fact_slot": list(slot), "r_source_occurrence": occurrence,
            "s_fact_assertion": assertion, "s_num_m2_value": m2,
            "r_load_event": events, "vault_reject_quarantine": negatives}


def _normalized(values: list[list]) -> Counter:
    return Counter(tuple(None if value is None else
                         ("true" if value else "false") if isinstance(value, bool)
                         else str(value) for value in row)
                   for row in values)


def _sign(document: dict, key: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory() as temp:
        message, signature = (Path(temp) / name for name in ("message", "signature"))
        message.write_bytes(canonical(document))
        subprocess.run(["/opt/homebrew/bin/openssl", "pkeyutl", "-sign",
                        "-inkey", str(key), "-rawin", "-in", str(message),
                        "-out", str(signature)], capture_output=True, check=True, timeout=15)
        envelope = {"document": document,
                    "signature_base64": base64.b64encode(signature.read_bytes()).decode()}
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical(envelope))
        stream.flush()
        os.fsync(stream.fileno())


def attest(root: Path, base: Path, grant_path: Path) -> dict:
    root, base = root.resolve(strict=True), base.resolve(strict=True)
    if (os.geteuid() != 0 or base.is_relative_to(root)
            or grant_path.resolve().parent != (base / "grants").resolve()):
        raise Denied("VAULT_VERIFIER_NOT_PROTECTED")
    policy = signed_policy(root, base / "trust/policy.signed.json", base / "trust")
    sample = root / "runs/day6-vault-prototype/sample-manifest.json"
    projected = root / "runs/day6-vault-prototype/projected-manifest.json"
    plan = root / "runs/day6-vault-prototype/load-plan.json"
    _selected, retained = validate_policy(root, policy, sample, projected, plan)
    grant = load_grant(root, grant_path, base / "trust")
    if grant["contracts"]["queue"]["sha256"] != file_digest(plan):
        raise Denied("VAULT_GRANT_PLAN_MISMATCH")
    for index, stage in enumerate(retained["stages"], 1):
        ledger = base / "ledger" / f"vault-c1500-{index:02d}-{stage['id']}.json"
        if (not ledger.is_file() or json.loads(ledger.read_bytes()).get("status")
                != "STAGE_READBACK_VERIFIED"):
            raise Denied("VAULT_STAGE_NOT_VERIFIED")
    expected = _expected(json.loads(projected.read_bytes())["rows"])
    checks = {}
    for name in TABLES:
        full = f"{NAMESPACE}.{name}"
        response = statement(root, base, f"SELECT {', '.join(COLS[name])} FROM {full}")
        manifest = response.get("manifest", {})
        if manifest.get("total_chunk_count") != 1:
            raise Denied("VAULT_READBACK_CHUNKING_UNSUPPORTED")
        actual = response.get("result", {}).get("data_array", [])
        if _normalized(actual) != _normalized(expected[name]):
            raise Denied("VAULT_PERSISTED_ROW_MISMATCH_" + name.upper())
        uc = _cli(root, base, "api", "get", "/api/2.1/unity-catalog/tables/" + full)
        if (uc.get("full_name") != full or not uc.get("table_id")
                or uc.get("data_source_format") != "DELTA"):
            raise Denied("VAULT_DELTA_TABLE_IDENTITY_MISMATCH")
        checks[name] = {"rows": len(actual), "statement_id": response["statement_id"],
                        "uc_table_id": uc["table_id"],
                        "rows_digest": digest(canonical(sorted(
                            (list(t) for t in _normalized(actual).elements()),
                            key=lambda r: json.dumps(r, sort_keys=True))))}
    receipt = base / "receipts/vault-c1500-final-v1.signed.json"
    document = {"schema": "EDP_VAULT_PROTOTYPE_READBACK_RECEIPT_V1",
                "authority": "protected-verifier-v1", "status": "VERIFIED",
                "live_readback": True, "cohort": "C1500",
                "namespace": NAMESPACE, "grant_id": grant["grant_id"],
                "sample_rows_sha256": policy["sample_rows_sha256"],
                "plan_file_sha256": file_digest(plan),
                "checks": checks, "verified_at_utc": datetime.now(UTC).isoformat()}
    if receipt.exists():
        prior = verified_document(root, receipt, base / "trust")
        if any(prior.get(name) != document[name] for name in document
               if name != "verified_at_utc"):
            raise Denied("VAULT_FINAL_RECEIPT_CHANGED")
    else:
        _sign(document, base / "private/verifier.pem", receipt)
    return {"status": "VAULT_PROTOTYPE_READBACK_VERIFIED",
            "receipt_path": str(receipt), "receipt_sha256": file_digest(receipt),
            "counts": {name: check["rows"] for name, check in checks.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("root", "base", "grant"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(attest(args.root, args.base, args.grant), sort_keys=True))


if __name__ == "__main__":
    main()
