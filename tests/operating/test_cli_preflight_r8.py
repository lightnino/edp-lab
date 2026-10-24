"""R8 regression fixtures: exact CLI versions, pagination and fail-closed outcomes."""

import json
from pathlib import Path

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.operating.cli_preflight_r8 import (
    CliResponse,
    ProtectedResponseStore,
    exact_uc_missing,
    exact_uc_present,
    inspect_history_page,
    inspect_readonly,
    verify_identity,
)

TABLE = "workspace.edp_lab.n500_input_roster_day5_v1"


def response(code=0, out=b"", err=b""):
    return CliResponse(code, out, err)


def as_json(obj):
    return json.dumps(obj).encode()


def test_authenticated_current_user_only() -> None:
    expected = "test@example.invalid"
    result = verify_identity(response(out=as_json({"userName": expected})),
                             expected_user=expected)
    assert result["status"] == "IDENTITY_VERIFIED"
    verify_identity(response(out=as_json({"user_name": expected})),
                    expected_user=expected)
    for rejected in (
        response(1, err=b"error getting token"),
        response(out=as_json({"userName": "other@example.invalid"})),
        response(out=b"[]"),
        response(out=b"not json"),
        response(0, as_json({"userName": expected}), b"warning containing token"),
    ):
        with pytest.raises(Denied):
            verify_identity(rejected, expected_user=expected)


def test_exact_uc_missing_cli_render_and_json() -> None:
    message = f"Table '{TABLE}' does not exist."
    assert exact_uc_missing(response(1, err=("Error: " + message).encode()),
                            table=TABLE)
    payload = {"error_code": "TABLE_DOES_NOT_EXIST", "message": message}
    assert exact_uc_missing(response(1, out=as_json(payload)), table=TABLE)
    assert exact_uc_missing(response(1, err=b"Error: " + as_json(payload)),
                            table=TABLE)
    for rejected in (
        response(1, err=b"Error: PERMISSION_DENIED"),
        response(1, err=b"Error: connection refused"),
        response(1, err=b"Error: Table 'workspace.edp_lab.other' does not exist."),
        response(0, err=("Error: " + message).encode()),
        response(1, out=b"some output", err=("Error: " + message).encode()),
        response(1, err=b"Not Found"),
        response(1, err=b"Error: {unknown"),
    ):
        assert not exact_uc_missing(rejected, table=TABLE)


def test_exact_uc_present_requires_complete_matching_identity() -> None:
    body = {"full_name": TABLE, "catalog_name": "workspace",
            "schema_name": "edp_lab", "name": "n500_input_roster_day5_v1",
            "table_id": "uc-id"}
    assert exact_uc_present(response(out=as_json(body)), table=TABLE)["table_id_sha256"]
    for bad in (
        response(1, err=b"Error: unauthenticated"),
        response(out=as_json({**body, "name": "other"})),
        response(out=as_json({**body, "full_name": "workspace.edp_lab.other"})),
        response(out=as_json({**body, "table_id": ""})),
        response(out=b"not json"),
        response(out=as_json(body), err=b"warning"),
    ):
        with pytest.raises(Denied):
            exact_uc_present(bad, table=TABLE)


def test_history_requires_complete_accurate_pagination() -> None:
    assert inspect_history_page(response(out=as_json({
        "res": [], "has_next_page": False
    }))) == (0, None)
    assert inspect_history_page(response(out=as_json({
        "has_next_page": False
    }))) == (0, None)
    assert inspect_history_page(response(out=as_json({
        "res": [{"statement_id": "one"}], "has_next_page": True,
        "next_page_token": "NEXT"
    }))) == (1, "NEXT")
    for item in (
        {"res": [], "has_next_page": True},
        {"res": [], "has_next_page": "false"},
        {"res": [], "has_next_page": False, "next_page_token": "EXTRA"},
        {"has_next_page": True},
        {"has_next_page": False, "unexpected": "x"},
        {"res": {}, "has_next_page": False},
    ):
        with pytest.raises(Denied):
            inspect_history_page(response(out=as_json(item)))


def test_readonly_preflight_is_profile_explicit_and_never_authorizes_retry() -> None:
    calls = []
    def invoke(*argv):
        calls.append(argv)
        if argv[:2] == ("current-user", "me"):
            return response(out=as_json({"userName": "test@example.invalid"}))
        if "/api/2.0/sql/history/queries?" in argv[2]:
            if "page_token=" in argv[2]:
                return response(out=as_json({"res": [], "has_next_page": False}))
            return response(out=as_json({
                "res": [{"statement_id": "some-visible-history"}],
                "has_next_page": True, "next_page_token": "A B",
            }))
        return response(1, err=f"Error: Table '{TABLE}' does not exist.".encode())

    result = inspect_readonly(
        cli="databricks", profile="edp-lab",
        expected_user="test@example.invalid", table=TABLE,
        start_ms=1, end_ms=2, expected_uc_state="ABSENT", invoke=invoke)
    assert result["status"] == "READONLY_EVIDENCE_ONLY"
    assert result["pages_checked"] == 2
    assert result["visible_queries"] == 1
    assert result["write_or_recovery_authorized"] is False
    assert result["uncertain_external_effects_resolved"] is False
    assert result["observed_uc_state"] == "ABSENT"
    assert len(result["history_stdout_sha256"]) == 2
    assert all("-p" in call and call[call.index("-p") + 1] == "edp-lab"
               for call in calls)
    assert "page_token=A%20B" in calls[2][2]
    assert all(not any(part == "post" for part in call) for call in calls)


def test_readonly_preflight_rejects_unknown_auth_or_remote() -> None:
    def cannot_auth(*argv):
        return response(1, err=b"cannot configure default credentials")
    with pytest.raises(Denied, match="PREFLIGHT_IDENTITY_FAILED"):
        inspect_readonly(cli="databricks", profile="edp-lab",
                         expected_user="test@example.invalid",
                         table=TABLE, start_ms=1, end_ms=2,
                         expected_uc_state="PRESENT",
                         invoke=cannot_auth)

    def missing_history(*argv):
        if argv[:2] == ("current-user", "me"):
            return response(out=as_json({"userName": "test@example.invalid"}))
        return response(1, err=b"403")
    with pytest.raises(Denied, match="PREFLIGHT_HISTORY_CLI_FAILED"):
        inspect_readonly(cli="databricks", profile="edp-lab",
                         expected_user="test@example.invalid",
                         table=TABLE, start_ms=1, end_ms=2,
                         expected_uc_state="PRESENT",
                         invoke=missing_history)
    with pytest.raises(Denied, match="PREFLIGHT_PROFILE_INVALID"):
        inspect_readonly(cli="databricks", profile="--unsafe",
                         expected_user="test@example.invalid",
                         table=TABLE, start_ms=1, end_ms=2,
                         expected_uc_state="PRESENT")


def test_present_preflight_never_infers_no_remote_effect() -> None:
    def invoke(*argv):
        if argv[:2] == ("current-user", "me"):
            return response(out=as_json({"userName": "test@example.invalid"}))
        if "/sql/history/queries?" in argv[2]:
            return response(out=as_json({"res": [], "has_next_page": False}))
        return response(out=as_json({
            "full_name": TABLE, "catalog_name": "workspace", "schema_name": "edp_lab",
            "name": "n500_input_roster_day5_v1", "table_id": "uc-id"}))
    result = inspect_readonly(
        cli="databricks", profile="edp-lab", expected_user="test@example.invalid",
        table=TABLE, start_ms=1, end_ms=2, expected_uc_state="PRESENT",
        invoke=invoke)
    assert result["observed_uc_state"] == "PRESENT"
    assert result["visible_queries"] == 0
    assert result["uncertain_external_effects_resolved"] is False
    assert result["write_or_recovery_authorized"] is False


@pytest.mark.parametrize(("history", "reason"), [
    ({"res": [], "has_next_page": True}, "PREFLIGHT_HISTORY_NEXT_PAGE_MISSING"),
    ({"res": [], "has_next_page": True, "next_page_token": "repeat"},
     "PREFLIGHT_HISTORY_PAGE_LIMIT"),
])
def test_incomplete_history_blocks_before_uc(history, reason) -> None:
    calls = []
    def invoke(*argv):
        calls.append(argv)
        if argv[:2] == ("current-user", "me"):
            return response(out=as_json({"userName": "test@example.invalid"}))
        return response(out=as_json(history))
    with pytest.raises(Denied, match=reason):
        inspect_readonly(
            cli="databricks", profile="edp-lab", expected_user="test@example.invalid",
            table=TABLE, start_ms=1, end_ms=2, expected_uc_state="PRESENT",
            max_pages=1, invoke=invoke)
    assert all("unity-catalog" not in " ".join(call) for call in calls)


def test_raw_response_sink_is_explicit_and_unprotected_path_rejected(
        tmp_path: Path) -> None:
    with pytest.raises(Denied, match="PREFLIGHT_EVIDENCE_DIR_UNTRUSTED"):
        ProtectedResponseStore(tmp_path)
    captured = []
    def invoke(*argv):
        if argv[:2] == ("current-user", "me"):
            return response(out=as_json({"userName": "test@example.invalid"}))
        if "/sql/history/queries?" in argv[2]:
            return response(out=as_json({"has_next_page": False}))
        return response(out=as_json({
            "full_name": TABLE, "catalog_name": "workspace", "schema_name": "edp_lab",
            "name": "n500_input_roster_day5_v1", "table_id": "uc-id"}))
    result = inspect_readonly(
        cli="databricks", profile="edp-lab", expected_user="test@example.invalid",
        table=TABLE, start_ms=1, end_ms=2, expected_uc_state="PRESENT",
        invoke=invoke, raw_response_store=lambda label, value:
        captured.append((label, value)))
    assert [label for label, _ in captured] == ["identity", "history-000", "uc-target"]
    assert result["raw_responses_preserved_in_protected_store"] is True
