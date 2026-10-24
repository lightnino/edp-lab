"""Protected live FIN and Treasury control execution for preserved C1500 sources."""

import csv
import json
from decimal import Decimal
from pathlib import Path

from edp_lab.operating.authority import (
    Denied,
    canonical,
    digest,
    file_digest,
    load_grant,
    verified_document,
)
from edp_lab.operating.day5_stage_verifier import _query
from edp_lab.operating.protected_verifier import _sign

FIN_FIXTURE = ("sql/reconciliation/fin_eval_v1/observed_expected_results.csv",
               "cd9cb0cf91042938833854d5a2b8a48fb3fdf36a60920292c2f670b7123be150")
TREASURY_FIXTURE = ("metadata/evaluations/fixtures/treasury_lossless6_expected_v1.json",
                    "176fd0be7d52a2f29a0ae54e58c7cd965d95b8c15106553982811f4ed47658a8")
FIN_PREFIX = ("sql/stability/c1500_m2_v1/fin_candidate_prefix.sql",
              "34b446fcda0a056865508d5d0bfe2c812f91efbfc820d0e03cfeafd310a6cfd2")


def _pinned(root: Path, pin: tuple[str, str]) -> Path:
    path = (root / pin[0]).resolve(strict=True)
    if not path.is_relative_to(root) or file_digest(path) != pin[1]:
        raise Denied("CONTROL_FIXTURE_CHANGED")
    return path


def _rows(response: dict) -> list[dict]:
    columns = [column["name"] for column in response["manifest"]["schema"]["columns"]]
    values = response["result"]["data_array"]
    if response["manifest"].get("truncated") or len(values) != response["manifest"][
            "total_row_count"]:
        raise Denied("CONTROL_RESULT_TRUNCATED")
    return [dict(zip(columns, row, strict=True)) for row in values]


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _render_treasury(root: Path, name: str, template: str) -> str:
    fixture = json.loads(_pinned(root, TREASURY_FIXTURE).read_bytes())
    if name == "TRY_001":
        pins = []
        allowed = []
        for row in fixture["sources"]:
            pins.append("(" + ",".join((_quote(row["source_instance_id"]),
                        _quote(row["source_identity"]), _quote(row["raw_sha256"]),
                        str(row["entries"]), str(row["evaluations"]), str(row["valid"]),
                        str(row["missing"]))) + ")")
            allowed.extend("(" + _quote(row["source_instance_id"]) + "," + _quote(q) + ")"
                           for q in row["qnames"])
        template = template.replace("{{PINS}}", ",".join(pins)).replace(
            "{{ALLOWLIST}}", ",".join(allowed))
    if name == "TRY_004":
        prefix = _pinned(root, FIN_PREFIX).read_text().rstrip().removesuffix(",")
        template = template.replace("{{FIN_CANDIDATE_PREFIX}}", prefix)
    if "{{" in template or "}}" in template:
        raise Denied("CONTROL_TEMPLATE_UNRESOLVED")
    return template


def _assess_fin(root: Path, name: str, rows: list[dict]) -> None:
    with _pinned(root, FIN_FIXTURE).open(newline="") as stream:
        fixture = list(csv.DictReader(stream))
    if name == "FIN_001":
        if len(rows) != 2:
            raise Denied("FIN_001_COVERAGE_FAILED")
        for actual, expected in zip(sorted(rows, key=lambda row: row["ddate"]),
                                    fixture[:2], strict=True):
            if actual["ddate"] != expected["ddate"] or actual["fin_001_result"] != "PASS":
                raise Denied("FIN_001_RESULT_FAILED")
            for field, target in (("assets", "assets"), ("liabilities", "liabilities"),
                                  ("equity", "equity_used"), ("reported_total", "reported_total"),
                                  ("difference_1", "correct_difference")):
                if Decimal(actual[field]) != Decimal(expected[target]):
                    raise Denied("FIN_001_FIXTURE_MISMATCH")
            if Decimal(actual["difference_2"]) != 0:
                raise Denied("FIN_001_BALANCE_MISMATCH")
    else:
        expected = fixture[2]
        if len(rows) != 1 or rows[0]["fin_002_result"] != "PASS":
            raise Denied("FIN_002_RESULT_FAILED")
        for field in ("correct_difference", "wrong_equity_difference", "implied_nci"):
            if Decimal(rows[0][field]) != Decimal(expected[field]):
                raise Denied("FIN_002_FIXTURE_MISMATCH")
        if Decimal(rows[0]["wrong_equity_difference"]) == 0:
            raise Denied("FIN_002_NEGATIVE_CONTROL_FAILED")


def _assess_treasury(root: Path, name: str, rows: list[dict]) -> None:
    fixture = json.loads(_pinned(root, TREASURY_FIXTURE).read_bytes())
    values = [list(row.values()) for row in rows]
    if not values or any(row[0] != name + "_V1" for row in values):
        raise Denied("TREASURY_CONTROL_ID_MISMATCH")
    if name == "TRY_001":
        expected = {row["source_instance_id"]: row for row in fixture["sources"]}
        if len(values) != 5 or {row[1] for row in values} != set(expected):
            raise Denied("TRY_001_COVERAGE_FAILED")
        for row in values:
            pin = expected[row[1]]
            pairs = ((2, 3, pin["entries"]), (4, 5, len(pin["qnames"])),
                     (6, 7, pin["evaluations"]), (8, 9, pin["valid"]),
                     (10, 11, pin["missing"]))
            if any(int(row[a]) != n or int(row[b]) != n for a, b, n in pairs):
                raise Denied("TRY_001_COUNT_MISMATCH")
            if int(row[12]) or int(row[13]):
                raise Denied("TRY_001_LINEAGE_MISMATCH")
        return
    if len(values) != 1:
        raise Denied("TREASURY_CONTROL_COVERAGE_FAILED")
    row = values[0]
    if name == "TRY_002":
        okay = int(row[1]) == 12793 and int(row[2]) == 12793 and all(
            int(value) == 0 for value in row[3:])
    elif name == "TRY_003":
        okay = tuple(map(int, row[1:])) == (12948, 12948, 12793, 12793, 155,
                                             155, 0, 0, 0, 0, 249, 0)
    else:
        okay = len(row) == 6 and tuple(map(int, row[1:])) == (34564, 0, 0, 12793, 5)
    if not okay:
        raise Denied(name + "_LIVE_RESULT_FAILED")


def attest_controls(root: Path, queue_path: Path, grant_path: Path,
                    state_path: Path, trust: Path, key: Path) -> dict:
    root = root.resolve()
    if any(path.resolve().is_relative_to(root) for path in (trust, key)):
        raise Denied("VERIFIER_MUST_BE_PROTECTED")
    queue = json.loads(queue_path.read_bytes())
    grant = load_grant(root, grant_path, trust)
    state = json.loads(state_path.read_bytes())
    if (queue["cohort"] != "C2000" or grant["authority"] != "policy-broker-v1"
            or state["queue_sha256"] != file_digest(queue_path)
            or state["grant_id"] != grant["grant_id"]
            or state["tasks"]["P9"]["status"] != "COMPLETE"
            or state["tasks"]["P10-P11"]["status"] != "PLANNED"):
        raise Denied("CONTROL_CHECKPOINT_MISMATCH")
    registry = json.loads((root / queue["contracts"]["registry"]["path"]).read_bytes())
    selected = [entry for entry in registry["controls"]
                if entry["execution"] == "databricks_sql" and set(entry["tags"]) <= set(queue["tags"])]
    if {entry["id"] for entry in selected} != set(queue["tasks"][-3]["control_ids"]) - {
            "LOSSLESS_1_TO_5_LOCAL_V1"}:
        raise Denied("CONTROL_SELECTION_CHANGED")
    receipts = {}
    for entry in selected:
        name = entry["id"].removesuffix("_V1")
        output = trust.parent / "receipts" / f"control-{entry['id']}.json"
        if output != Path(next(task for task in queue["tasks"] if task["id"] == "P10-P11")[
                "receipts"][entry["id"]]):
            raise Denied("CONTROL_RECEIPT_PATH_CHANGED")
        if output.exists():
            prior = verified_document(root, output, trust)
            if (prior.get("schema") != "EDP_LIVE_CONTROL_RECEIPT_V1"
                    or prior.get("authority") != "protected-verifier-v1"
                    or prior.get("control_id") != entry["id"]
                    or prior.get("sql_sha256") != entry["sha256"]
                    or prior.get("queue_sha256") != file_digest(queue_path)
                    or prior.get("status") != "PASS"
                    or prior.get("live_databricks") is not True):
                raise Denied("CONTROL_RECEIPT_CHANGED")
            receipts[entry["id"]] = file_digest(output)
            continue
        template = (root / entry["path"]).resolve(strict=True)
        if not template.is_relative_to(root) or file_digest(template) != entry["sha256"]:
            raise Denied("CONTROL_SQL_CHANGED")
        sql = template.read_text()
        if name.startswith("TRY_"):
            sql = _render_treasury(root, name, sql)
        result = _query(sql, expected_rows=None)
        rows = _rows(result)
        if name.startswith("FIN_"):
            _assess_fin(root, name, rows)
        else:
            _assess_treasury(root, name, rows)
        document = {"schema": "EDP_LIVE_CONTROL_RECEIPT_V1",
                    "authority": "protected-verifier-v1", "control_id": entry["id"],
                    "sql_sha256": entry["sha256"], "status": "PASS",
                    "live_databricks": True, "statement_id": result["statement_id"],
                    "response_sha256": digest(canonical(result)),
                    "queue_sha256": file_digest(queue_path)}
        _sign(document, key, output)
        receipts[entry["id"]] = file_digest(output)
    return receipts
