"""One-shot Owner-authorized C2000 DEV Vault load; no protected V2 grant claims."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import time
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from edp_lab.operating.authority import file_digest
from edp_lab.vault.load_plan import NAMESPACE, TABLES, render_v2
from edp_lab.vault.protected_readback import COLS, _expected, _normalized
from edp_lab.vault.prototype import project, validate_batch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/day6-vault-c2000-step2-live-v1"
RAW_ROOT = Path("/Users/lightnino/Projects/edp-lab")
WAREHOUSE = "589e80595c7c8cb8"
INPUT_SHA = "ee7adf7c39d3fc702692d3b5fe8561d14ecdac33c592f823ae0ddea4d4daf613"
PROJECTED_SHA = "993e9588617ea5132d80bf3dfc84cacd5e382f01a50adcb86c97ee141a11efbb"
PLAN_SHA = "241ed0e10e041587bcd132f667960f7e7f1521c537275460c2f2ab08647c931f"
FREEZE_SHA = "324ca5e416adabc443d18d8066fbccdf137f4cb50aa20934e645615f4ee77ff3"
ROSTER_SHA = "2a72b8f8483e2181a3112a26b5d68d702b92308def6e74978838b155cfd85312"
RESULT_SHA = "942fa887ceea8cf5c9bc64c603c2044e1b643b01fcbc29909ce264c024b69374"
CONTRACT_SHA = "681c3f6a9a4446b5357c3ab6c6534e6fd5b8cf944f967ea9ab27dcc2c8b5aabe"
SERIALIZER_SHA = "c80c43e299424947d1d4c6bcd2211235bebd79efc03923e2a9db55bc682a659a"
SOURCES = {"SRC000005": 10, "SRC000054": 9, "SRC000064": 108}
EXPECTED = {"h_filing": 20, "h_concept": 24, "l_fact_slot": 76,
            "r_source_occurrence": 127, "s_fact_assertion": 127,
            "s_num_m2_value": 127, "r_load_event": 127,
            "vault_reject_quarantine": 6}
RUN_ID = "vault-c2000-bounded-v1"
MAX_STATEMENTS = 60
MAX_SECONDS = 3600


def require(ok: bool, code: str) -> None:
    if not ok:
        raise RuntimeError(code)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def cli(*args: str, timeout: int = 180) -> dict:
    response = subprocess.run(["databricks", *args, "-p", "edp-lab", "-o", "json"],
                              capture_output=True, text=True, timeout=timeout, check=False)
    require(response.returncode == 0, "DATABRICKS_CLI_FAILED: " + response.stderr[:300])
    return json.loads(response.stdout)


def pinned_inputs() -> tuple[dict, list[dict]]:
    cohort = ROOT / "metadata/freezes/C2000_v1"
    freeze_path = cohort / "freeze.json"
    require(file_digest(freeze_path) == FREEZE_SHA, "FREEZE_HASH_CHANGED")
    freeze = json.loads(freeze_path.read_bytes())
    require(freeze["cohort"] == "C2000" and freeze["files_sha256"]["C2000.bindings.json"]
            == ROSTER_SHA, "FREEZE_SCOPE_CHANGED")
    for name, expected in freeze["files_sha256"].items():
        require(file_digest(cohort / name) == expected, "FREEZE_MEMBER_CHANGED_" + name)
    result_path = ROOT / "metadata/freezes/O_C2000_M2_v1/databricks_result_freeze_v1.json"
    require(file_digest(result_path) == RESULT_SHA, "RESULT_FREEZE_CHANGED")
    result = json.loads(result_path.read_bytes())
    require(result["input_freeze_sha256"] == FREEZE_SHA and result["accepted_tasks"] == 513,
            "RESULT_FREEZE_SCOPE_CHANGED")
    require(file_digest(ROOT / "docs/vault_load_contract_v1.md") == CONTRACT_SHA
            and file_digest(ROOT / "scripts/day6_vault_contract_v1.py") == SERIALIZER_SHA,
            "APPROVED_CONTRACT_CHANGED")
    folder = ROOT / "runs/day6-vault-c2000-v1"
    input_path, projected_path, plan_path = (folder / name for name in
                                             ("input_manifest.json", "projected_manifest.json",
                                              "load_plan.json"))
    require(file_digest(input_path) == INPUT_SHA and file_digest(projected_path)
            == PROJECTED_SHA and file_digest(plan_path) == PLAN_SHA, "INPUT_OR_PLAN_CHANGED")
    inp = json.loads(input_path.read_bytes())
    projected = json.loads(projected_path.read_bytes())
    plan = json.loads(plan_path.read_bytes())
    rows = inp["rows"]
    require(len(rows) == 127 and Counter(r["source_instance_id"] for r in rows) == SOURCES,
            "SAMPLE_MEMBERSHIP_CHANGED")
    require([project(row, projected["approved_bindings"]) for row in rows]
            == projected["rows"], "PROJECTION_CHANGED")
    validate_batch(projected["rows"])
    old = json.loads((ROOT / "runs/day6-vault-prototype/sample-manifest.json").read_bytes())
    require(rows == old["rows"] and inp["historical_rows_sha256"] == old["rows_sha256"],
            "PINNED_M1_SAMPLE_CHANGED")
    expected = _expected(projected["rows"], include_events=False,
                         include_negatives=True,
                         negative_execution_id="vault-negative-C2000")
    require(plan == render_v2(projected["rows"], cohort_id="C2000",
                              input_manifest_sha256=INPUT_SHA,
                              expected_table_counts={k: len(v) for k, v in expected.items()},
                              synthetic_negatives=True), "RENDERED_PLAN_CHANGED")
    require(plan["namespace"] == NAMESPACE and plan["data_occurrences"] == 127
            and plan["synthetic_rows"] == 6 and len(plan["stages"]) == 7,
            "PLAN_SCOPE_CHANGED")
    roster = {r["source_instance_id"]: r for r in
              json.loads((cohort / "C2000.bindings.json").read_bytes())}
    for sid in SOURCES:
        source_rows = [r for r in rows if r["source_instance_id"] == sid]
        first = source_rows[0]
        require(all(r["raw_path"] == roster[sid]["raw_path"]
                    and r["raw_sha256"] == roster[sid]["raw_sha256"]
                    and r["member_sha256"] == first["member_sha256"]
                    and r["archive_member"] == "num.txt" for r in source_rows),
                "RAW_ROSTER_MISMATCH")
        raw = RAW_ROOT / first["raw_path"]
        require(raw.resolve(strict=True).is_relative_to((RAW_ROOT / "data/raw").resolve()),
                "RAW_PATH_OUTSIDE_ROOT")
        require(file_digest(raw) == first["raw_sha256"], "RAW_ZIP_CHANGED")
        with zipfile.ZipFile(raw) as archive:
            require(archive.namelist().count("num.txt") == 1, "RAW_MEMBER_AMBIGUOUS")
            h = hashlib.sha256()
            with archive.open("num.txt") as member:
                for chunk in iter(lambda: member.read(1024 * 1024), b""):
                    h.update(chunk)
        require(h.hexdigest() == first["member_sha256"], "RAW_MEMBER_CHANGED")
    return plan, projected["rows"]


class Run:
    def __init__(self, resume_after_no_submit: bool = False,
                 resume_failed_event: bool = False) -> None:
        OUT.mkdir(parents=True, exist_ok=True)
        self.path = OUT / "journal.json"
        if resume_failed_event:
            self.path = OUT / "journal-attempt-2.json"
            require(self.path.exists(), "FAILED_EVENT_JOURNAL_MISSING")
            self.state = json.loads(self.path.read_bytes())
            entries = self.state["statements"]
            require(self.state["status"] == "PARTIAL_OR_FAILED_REQUIRES_INSPECTION"
                    and self.state["counts"] == {k: v for k, v in EXPECTED.items()
                                                 if k != "r_load_event"}
                    and len(entries) == 30
                    and entries[-1]["label"] == "write-08-r_load_event"
                    and entries[-1]["status"] == "FAILED"
                    and entries[-1]["statement_id"]
                    == "01f1cfc5-c66a-1b95-9e60-81c5a5584fe3",
                    "FAILED_EVENT_CHECKPOINT_CHANGED")
            elapsed = (datetime.now(UTC) - datetime.fromisoformat(
                self.state["started_at_utc"])).total_seconds()
            require(0 <= elapsed < MAX_SECONDS, "RUN_WINDOW_EXHAUSTED")
            self.started = time.monotonic() - elapsed
            return
        if resume_after_no_submit:
            require(self.path.exists(), "NO_PRIOR_ATTEMPT")
            prior = json.loads(self.path.read_bytes())
            require(prior["status"] == "PARTIAL_OR_FAILED_REQUIRES_INSPECTION"
                    and prior["statements"] == [] and prior["counts"] == {},
                    "PRIOR_ATTEMPT_MAY_HAVE_SUBMITTED_SQL")
            self.path = OUT / "journal-attempt-2.json"
        require(not self.path.exists(), "EXISTING_RUN_REQUIRES_INSPECTION")
        self.started = time.monotonic()
        self.state = {"schema": "C2000_VAULT_DEV_STEP2_JOURNAL_V1", "status": "STARTED",
                      "run_id": RUN_ID, "input_manifest_sha256": INPUT_SHA,
                      "load_plan_sha256": PLAN_SHA, "warehouse_id": WAREHOUSE,
                      "started_at_utc": datetime.now(UTC).isoformat(),
                      "statements": [], "counts": {}}
        save(self.path, self.state)

    def persist(self) -> None:
        save(self.path, self.state)

    def submit(self, label: str, sql: str, *, write: bool = False) -> dict:
        require(len(self.state["statements"]) < MAX_STATEMENTS, "STATEMENT_CAP_EXHAUSTED")
        require(time.monotonic() - self.started < MAX_SECONDS, "RUNTIME_CAP_EXHAUSTED")
        if write:
            require(sql.startswith("MERGE INTO " + NAMESPACE + ".")
                    and "WHEN MATCHED THEN" not in sql and ";" not in sql,
                    "WRITE_OUTSIDE_DEV_SCOPE")
        else:
            require(sql.startswith("SELECT ") and ";" not in sql,
                    "READ_QUERY_OUTSIDE_SCOPE")
        entry = {"label": label, "sql_sha256": digest(sql), "write": write,
                 "status": "SUBMISSION_RESERVED"}
        self.state["statements"].append(entry)
        self.persist()
        request = {"warehouse_id": WAREHOUSE, "statement": sql,
                   "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
                   "disposition": "INLINE"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=OUT,
                                         delete=False) as stream:
            json.dump(request, stream)
            request_path = Path(stream.name)
        try:
            response = cli("api", "post", "/api/2.0/sql/statements", "--json",
                           "@" + str(request_path), timeout=180)
            entry["statement_id"] = response.get("statement_id")
            entry["status"] = response.get("status", {}).get("state", "UNKNOWN")
            self.persist()
            require(isinstance(entry["statement_id"], str), "SUBMISSION_UNCERTAIN")
            deadline = min(time.monotonic() + 600, self.started + MAX_SECONDS)
            while entry["status"] in {"PENDING", "RUNNING"}:
                require(time.monotonic() < deadline, "STATEMENT_TIMEOUT_UNCERTAIN")
                time.sleep(3)
                response = cli("api", "get", "/api/2.0/sql/statements/"
                               + entry["statement_id"], timeout=180)
                entry["status"] = response.get("status", {}).get("state", "UNKNOWN")
                self.persist()
            require(entry["status"] == "SUCCEEDED"
                    and (write or response.get("manifest", {}).get("truncated") is False),
                    "STATEMENT_FAILED_OR_TRUNCATED")
            save(OUT / (label + ".json"), response)
            return response
        finally:
            request_path.unlink(missing_ok=True)

    def scalar(self, label: str, sql: str) -> tuple[int, str]:
        result = self.submit(label, sql)
        rows = result.get("result", {}).get("data_array", [])
        require(len(rows) == 1 and len(rows[0]) == 1, "SCALAR_SHAPE_INVALID")
        return int(rows[0][0]), result["statement_id"]


def audit_sql(occurrences: list[str], statement_id: str) -> str:
    require(len(occurrences) == len(set(occurrences)) == 127
            and all(len(value) == 64 for value in occurrences), "AUDIT_SCOPE_INVALID")
    def literal(value: str) -> str:
        return "decode(unhex('" + value.encode().hex() + "'), 'UTF-8')"

    values = ",\n    ".join("('" + hk.encode().hex() + "')" for hk in occurrences)
    table = f"{NAMESPACE}.r_load_event"
    return (f"MERGE INTO {table} AS t\n"
            "USING (SELECT decode(unhex(v.c1), 'UTF-8') AS occurrence_hk "
            f"FROM VALUES\n    {values}\nAS v(c1)) AS s\n"
            f"ON t.occurrence_hk=s.occurrence_hk AND t.execution_id={literal(RUN_ID)}\n"
            "WHEN NOT MATCHED THEN INSERT "
            "(occurrence_hk, execution_id, load_dts, event_kind, statement_id, "
            "input_manifest_sha256) VALUES "
            f"(s.occurrence_hk, {literal(RUN_ID)}, current_timestamp(), "
            f"{literal('ADMITTED')}, {literal(statement_id)}, {literal(INPUT_SHA)})")


def execute(*, resume_after_no_submit: bool = False,
            resume_failed_event: bool = False) -> dict:
    plan, _rows = pinned_inputs()
    run = Run(resume_after_no_submit, resume_failed_event)
    try:
        occurrence_write_id = None
        if resume_failed_event:
            failed_id = run.state["statements"][-1]["statement_id"]
            remote = cli("api", "get", "/api/2.0/sql/statements/" + failed_id)
            error = remote.get("status", {}).get("error", {})
            require(remote.get("status", {}).get("state") == "FAILED"
                    and "INVALID_INLINE_TABLE" in error.get("message", ""),
                    "FAILED_WRITE_NOT_RECONCILED")
            run.state["failed_event_reconciliation"] = {
                "statement_id": failed_id, "status": "FAILED", "error": error}
            run.persist()
            for name in TABLES:
                count, _ = run.scalar("reconcile-" + name,
                                      f"SELECT COUNT(*) FROM {NAMESPACE}.{name}")
                require(count == (0 if name == "r_load_event" else EXPECTED[name]),
                        "PERSISTED_STATE_CHANGED_" + name)
            occurrence_write_id = next(entry["statement_id"] for entry in
                                       run.state["statements"] if entry["label"]
                                       == "write-04-r_source_occurrence")
        else:
            for name in TABLES:
                full = f"{NAMESPACE}.{name}"
                uc = cli("tables", "get", full)
                require(uc.get("full_name") == full and uc.get("table_type") == "MANAGED"
                        and uc.get("data_source_format") == "DELTA", "VAULT_TABLE_CHANGED")
                count, _ = run.scalar("initial-" + name, f"SELECT COUNT(*) FROM {full}")
                require(count == 0, "VAULT_TABLE_NOT_EMPTY_" + name)
            for index, stage in enumerate(plan["stages"], 1):
                name = stage["table"].split(".")[-1]
                require(name in TABLES and stage["table"] == f"{NAMESPACE}.{name}"
                        and stage["kind"] == "MERGE_INSERT_ONLY"
                        and digest(stage["statement"]) == stage["statement_sha256"]
                        and digest(stage["precheck"]) == stage["precheck_sha256"],
                        "STAGE_PIN_CHANGED")
                mismatch, _ = run.scalar(f"precheck-{index:02d}", stage["precheck"])
                require(mismatch == 0, "PRECHECK_COMPONENT_DRIFT")
                written = run.submit(f"write-{index:02d}-{name}", stage["statement"], write=True)
                if name == "r_source_occurrence":
                    occurrence_write_id = written["statement_id"]
                count, _ = run.scalar(f"count-{index:02d}-{name}",
                                      f"SELECT COUNT(*) FROM {stage['table']}")
                require(count == stage["expected_rows"] == EXPECTED[name],
                        "STAGE_COUNT_MISMATCH_" + name)
                run.state["counts"][name] = count
                run.persist()
        require(occurrence_write_id is not None, "OCCURRENCE_WRITE_ID_MISSING")
        occurrences = [row[0] for row in plan["expected_tables"]["r_source_occurrence"]["rows"]]
        event_sql = audit_sql(occurrences, occurrence_write_id)
        run.submit("write-08-r_load_event", event_sql, write=True)
        count, _ = run.scalar("count-08-r_load_event",
                              f"SELECT COUNT(*) FROM {NAMESPACE}.r_load_event")
        require(count == 127, "LOAD_EVENT_COUNT_MISMATCH")
        run.state["counts"]["r_load_event"] = count
        run.persist()
        for name in TABLES:
            columns = COLS[name]
            response = run.submit("exact-" + name,
                                  f"SELECT {', '.join(columns)} FROM {NAMESPACE}.{name}")
            actual = response.get("result", {}).get("data_array", [])
            if name == "r_load_event":
                require(len(actual) == 127 and all(
                    row[2] == "ADMITTED" and row[3] == occurrence_write_id
                    and row[4] == INPUT_SHA for row in actual), "AUDIT_ROWS_INVALID")
                require({row[0] for row in actual} == set(occurrences),
                        "AUDIT_OCCURRENCE_COVERAGE_CHANGED")
            else:
                expected = plan["expected_tables"][name]["rows"]
                require(_normalized(actual) == _normalized(expected),
                        "EXACT_ROW_MISMATCH_" + name)
            require(len(actual) == EXPECTED[name], "EXACT_COUNT_MISMATCH_" + name)
        m2, _ = run.scalar("m2-outcomes", f"SELECT COUNT(*) FROM {NAMESPACE}.s_num_m2_value "
                            "WHERE conversion_outcome='VALID'")
        blank, _ = run.scalar("m2-blank", f"SELECT COUNT(*) FROM {NAMESPACE}.s_num_m2_value "
                               "WHERE conversion_outcome='BLANK'")
        require((m2, blank) == (125, 2), "M2_OUTCOME_COUNTS_CHANGED")
        run.state.update({"status": "VAULT_PROTOTYPE_VALIDATED",
                          "completed_at_utc": datetime.now(UTC).isoformat(),
                          "m2_outcomes": {"VALID": m2, "BLANK": blank},
                          "occurrence_write_statement_id": occurrence_write_id,
                          "source_counts": SOURCES})
        run.persist()
        return {"status": run.state["status"], "counts": run.state["counts"],
                "statements": len(run.state["statements"]), "journal": str(run.path)}
    except Exception as exc:
        run.state["status"] = "PARTIAL_OR_FAILED_REQUIRES_INSPECTION"
        run.state["error"] = str(exc)[:500]
        run.persist()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-after-no-submit", action="store_true")
    parser.add_argument("--resume-failed-event", action="store_true")
    args = parser.parse_args()
    print(json.dumps(execute(resume_after_no_submit=args.resume_after_no_submit,
                             resume_failed_event=args.resume_failed_event), sort_keys=True))
