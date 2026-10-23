"""Cohort-neutral Vault 0A authorization and replay boundaries.

These pure checks are used by protected services. A repository policy or cohort
receipt is never authority merely because it passes these structural checks:
the service must first verify the owner/verifier signature with protected trust.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from edp_lab.operating.authority import Denied, file_digest

NAMESPACE = "workspace.edp_lab_day6_vault_proto"
TABLES = (
    "h_filing", "h_concept", "l_fact_slot", "r_source_occurrence",
    "s_fact_assertion", "s_num_m2_value", "r_load_event",
    "vault_reject_quarantine",
)
WRITE_KINDS = frozenset({"MERGE_INSERT_ONLY"})
READ_KINDS = frozenset({"READBACK"})
FORBIDDEN_SQL = re.compile(
    r"\b(DROP|DELETE|UPDATE|TRUNCATE|REPLACE|OVERWRITE|ALTER|CREATE)\b",
    re.IGNORECASE,
)
SHA = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9_.:-]{8,120}\Z")
COHORT = re.compile(r"[A-Za-z0-9_.:-]{1,120}\Z")


def _utc(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise Denied("VAULT_TIME_INVALID") from exc
    if instant.tzinfo is None:
        raise Denied("VAULT_TIME_UNZONED")
    return instant.astimezone(UTC)


def _sha(value: object) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def validate_standing_policy(policy: dict, *, now: datetime | None = None,
                             root: Path | None = None) -> None:
    """Check only durable infrastructure bounds; no cohort or sample pins."""
    if (policy.get("schema") != "EDP_VAULT_STANDING_POLICY_V2"
            or policy.get("authority") != "requesting-owner-vault-dev-v2"
            or policy.get("namespace") != NAMESPACE
            or policy.get("tables") != list(TABLES)
            or policy.get("warehouse_max_cluster_size") != "2X-Small"
            or policy.get("warehouse_max_clusters") != 1
            or policy.get("warehouse_name") != "EDP Vault Dev V2"
            or (policy.get("status") == "OWNER_INSTALLED_STANDING_POLICY" and
                re.fullmatch(r"[0-9a-f]{16}", policy.get("warehouse_id", "")) is None)
            or policy.get("day5_resources_allowed") is not False
            or policy.get("raw_writes_allowed") is not False
            or policy.get("c2000_full_integration_allowed") is not False
            or policy.get("destructive_sql_allowed") is not False
            or policy.get("max_grant_seconds", 0) > 3600
            or policy.get("max_grant_seconds", 0) < 1
            or policy.get("max_run_statements", 0) > 100
            or policy.get("max_run_statements", 0) < 1
            or policy.get("max_total_grants", 0) < 1
            or policy.get("max_total_grants", 0) > 128
            or policy.get("max_total_sql_statements", 0) < 1
            or policy.get("max_total_sql_statements", 0) > 10_000
            or policy.get("max_run_runtime_seconds", 0) > 7200
            or policy.get("max_run_runtime_seconds", 0) < 1
            or policy["max_run_runtime_seconds"] > policy["max_grant_seconds"]
            or policy.get("max_run_data_occurrences", 0) > 1000
            or policy.get("max_run_data_occurrences", 0) < 1
            or policy.get("max_run_synthetic_rows", -1) > 20
            or policy.get("max_run_synthetic_rows", -1) < 0
            or policy.get("max_retries_per_statement") != 0
            or policy.get("allowed_write_kinds") != ["MERGE_INSERT_ONLY"]
            or policy.get("allowed_read_kinds") != ["READBACK"]
            or policy.get("cohort_receipt_authority") != "protected-verifier-v1"):
        raise Denied("VAULT_STANDING_SCOPE_INVALID")
    if not isinstance(policy.get("contracts"), list) or not policy["contracts"]:
        raise Denied("VAULT_APPROVED_CONTRACTS_MISSING")
    for contract in policy["contracts"]:
        if (set(contract) != {"version", "path", "sha256"} or not _sha(contract["sha256"])
                or not isinstance(contract["version"], str)):
            raise Denied("VAULT_CONTRACT_PIN_INVALID")
    if not isinstance(policy.get("mapping_rules"), list) or not policy["mapping_rules"]:
        raise Denied("VAULT_APPROVED_RULES_MISSING")
    for rule in policy["mapping_rules"]:
        if (set(rule) != {"version", "path", "sha256"} or not _sha(rule["sha256"])
                or not isinstance(rule["version"], str)):
            raise Denied("VAULT_RULE_PIN_INVALID")
    if root is not None:
        for pin in (*policy["contracts"], *policy["mapping_rules"]):
            relative = Path(pin["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise Denied("VAULT_SEMANTIC_PIN_OUTSIDE_REPOSITORY")
            path = (root / relative).resolve(strict=True)
            if not path.is_relative_to(root.resolve()) or file_digest(path) != pin["sha256"]:
                raise Denied("VAULT_SEMANTIC_PIN_CHANGED")
    current = now or datetime.now(UTC)
    if not _utc(policy["issued_at"]) <= current < _utc(policy["expires_at"]):
        raise Denied("VAULT_STANDING_POLICY_NOT_CURRENT")


def validate_cohort_receipt(policy: dict, receipt: dict, root: Path,
                            *, now: datetime | None = None) -> None:
    """Consume a separately signed, independently verified cohort receipt."""
    validate_standing_policy(policy, now=now, root=root)
    if (receipt.get("schema") != "EDP_VAULT_COHORT_ELIGIBILITY_V1"
            or receipt.get("authority") != policy["cohort_receipt_authority"]
            or receipt.get("status") != "VERIFIED_FROZEN"
            or receipt.get("workload_kind") not in {"BOUNDED_PROTOTYPE", "FULL_INTEGRATION"}
            or (receipt.get("workload_kind") == "FULL_INTEGRATION" and
                policy["c2000_full_integration_allowed"] is False)
            or not isinstance(receipt.get("cohort_id"), str)
            or not COHORT.fullmatch(receipt["cohort_id"])
            or receipt.get("namespace") != NAMESPACE
            or receipt.get("tables") != list(TABLES)
            or receipt.get("data_occurrence_limit", 0) < 1
            or receipt.get("data_occurrence_limit", 0) > policy["max_run_data_occurrences"]
            or receipt.get("synthetic_row_limit", -1) < 0
            or receipt.get("synthetic_row_limit", -1) > policy["max_run_synthetic_rows"]
            or not _sha(receipt.get("input_manifest_sha256"))
            or not _sha(receipt.get("load_plan_sha256"))
            or not _sha(receipt.get("independent_freeze_receipt_sha256"))):
        raise Denied("VAULT_COHORT_RECEIPT_SCOPE_INVALID")
    if (receipt.get("contract") not in policy["contracts"]
            or receipt.get("mapping_rule") not in policy["mapping_rules"]):
        raise Denied("VAULT_COHORT_SEMANTICS_UNAPPROVED")
    if not _utc(receipt["issued_at"]) <= (now or datetime.now(UTC)) < _utc(receipt["expires_at"]):
        raise Denied("VAULT_COHORT_RECEIPT_EXPIRED")
    for name in ("freeze", "source_manifest", "approval", "input_manifest", "load_plan"):
        item = receipt.get(name)
        if not isinstance(item, dict) or set(item) != {"path", "sha256"} or not _sha(item["sha256"]):
            raise Denied("VAULT_COHORT_PIN_INVALID")
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise Denied("VAULT_COHORT_PIN_OUTSIDE_REPOSITORY")
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or file_digest(path) != item["sha256"]:
            raise Denied("VAULT_COHORT_PIN_CHANGED")
    if (receipt["input_manifest"]["sha256"] != receipt["input_manifest_sha256"]
            or receipt["load_plan"]["sha256"] != receipt["load_plan_sha256"]):
        raise Denied("VAULT_COHORT_PLAN_PIN_MISMATCH")
    sources = receipt.get("sources")
    if (not isinstance(sources, dict) or not sources
            or any(not IDENTIFIER.fullmatch(sid) or not _sha(raw_sha)
                   for sid, raw_sha in sources.items())):
        raise Denied("VAULT_COHORT_SOURCES_INVALID")


def validate_run(policy: dict, receipt: dict, run: dict) -> None:
    """Bind one request to an eligible cohort and exact immutable inputs."""
    if (run.get("schema") != "EDP_VAULT_RUN_REQUEST_V1"
            or run.get("cohort_id") != receipt["cohort_id"]
            or run.get("workload_kind") != receipt["workload_kind"]
            or not isinstance(run.get("run_id"), str)
            or not IDENTIFIER.fullmatch(run["run_id"])
            or run.get("namespace") != NAMESPACE
            or run.get("tables") != list(TABLES)
            or run.get("contract") != receipt["contract"]
            or run.get("mapping_rule") != receipt["mapping_rule"]
            or run.get("sources") != receipt["sources"]
            or run.get("event_kind") not in {"ADMITTED", "REPLAY"}
            or run.get("input_manifest_sha256") != receipt["input_manifest_sha256"]
            or run.get("load_plan_sha256") != receipt["load_plan_sha256"]
            or run.get("data_occurrences", 0) < 1
            or run.get("data_occurrences", 0) > receipt["data_occurrence_limit"]
            or run.get("synthetic_rows", -1) < 0
            or run.get("synthetic_rows", -1) > receipt["synthetic_row_limit"]
            or run.get("max_statements", 0) < 1
            or run.get("max_statements", 0) > policy["max_run_statements"]
            or run.get("max_runtime_seconds", 0) < 1
            or run.get("max_runtime_seconds", 0) > policy["max_run_runtime_seconds"]):
        raise Denied("VAULT_RUN_OUT_OF_SCOPE")


def grant_for_run(policy: dict, receipt: dict, run: dict,
                  *, now: datetime | None = None) -> dict:
    """Build an unsigned short-lived grant; only the protected broker signs it."""
    current = now or datetime.now(UTC)
    validate_run(policy, receipt, run)
    expires = min(current + timedelta(seconds=policy["max_grant_seconds"]),
                  _utc(policy["expires_at"]), _utc(receipt["expires_at"]))
    if expires <= current:
        raise Denied("VAULT_GRANT_WINDOW_EXHAUSTED")
    canonical_run = json.dumps(run, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode()
    return {"schema": "EDP_VAULT_RUN_GRANT_V1", "authority": "vault-policy-broker-v2",
            "grant_id": hashlib.sha256(canonical_run).hexdigest(),
            "run_sha256": hashlib.sha256(canonical_run).hexdigest(),
            "cohort_id": run["cohort_id"], "run_id": run["run_id"],
            "workload_kind": run["workload_kind"],
            "event_kind": run["event_kind"],
            "namespace": NAMESPACE, "tables": list(TABLES),
            "sources": run["sources"], "contract": run["contract"],
            "mapping_rule": run["mapping_rule"],
            "input_manifest_sha256": run["input_manifest_sha256"],
            "load_plan_sha256": run["load_plan_sha256"],
            "data_occurrences": run["data_occurrences"],
            "synthetic_rows": run["synthetic_rows"],
            "max_statements": run["max_statements"],
            "max_runtime_seconds": run["max_runtime_seconds"],
            "issued_at": current.isoformat(), "expires_at": expires.isoformat(),
            "revocation_id": policy["policy_id"]}


def authorize_stage(grant: dict, stage: dict, *, used_statements: int,
                    uncertain_operation_ids: set[str]) -> None:
    """Authorize a single fixed-plan SQL stage, never arbitrary caller SQL."""
    operation_id = stage.get("operation_id")
    if operation_id in uncertain_operation_ids:
        raise Denied("VAULT_UNCERTAIN_WRITE_REPLAY_DENIED")
    if (not isinstance(operation_id, str) or not IDENTIFIER.fullmatch(operation_id)
            or used_statements >= grant["max_statements"]
            or stage.get("kind") not in WRITE_KINDS | READ_KINDS
            or stage.get("table") not in {f"{NAMESPACE}.{name}" for name in TABLES}
            or not _sha(stage.get("statement_sha256"))
            or stage.get("load_plan_sha256") != grant["load_plan_sha256"]):
        raise Denied("VAULT_STAGE_OUT_OF_SCOPE")
    sql = stage.get("statement")
    if (not isinstance(sql, str) or ";" in sql
            or hashlib.sha256(sql.encode()).hexdigest() != stage["statement_sha256"]
            or FORBIDDEN_SQL.search(sql)):
        raise Denied("VAULT_SQL_UNAUTHORIZED")
    if stage["kind"] == "MERGE_INSERT_ONLY":
        if (not sql.startswith(f"MERGE INTO {stage['table']} AS t\n")
                or "WHEN NOT MATCHED THEN INSERT" not in sql
                or "WHEN MATCHED THEN" in sql):
            raise Denied("VAULT_SQL_UNAUTHORIZED")
    elif (not sql.startswith("SELECT ")
          or f" FROM {stage['table']}" not in sql
          or re.search(r"\b(JOIN|UNION|INTERSECT|EXCEPT)\b", sql, re.IGNORECASE)):
        raise Denied("VAULT_SQL_UNAUTHORIZED")
