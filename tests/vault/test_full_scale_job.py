"""No-network tests of one-shot reservation and unsigned readback."""

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.vault.full_scale_job import read_freeze_candidate, readback_batch, submit_batch
from tests.vault.test_full_scale_boundary import _authority, _batch


class Transport:
    calls = 0

    def submit(self, payload):
        self.calls += 1
        assert payload["tasks"][0]["max_retries"] == 0
        return {"run_id": 123}

    def get_run(self, run_id):
        return {"run_id": run_id, "state": {"life_cycle_state": "TERMINATED",
                                           "result_state": "SUCCESS"}}


def test_submit_once_then_readback_requires_delta_check(tmp_path):
    authority = _authority() | {"trusted_signature_verified": True,
                                "deployment_sha256_verified": True,
                                "source_manifest_verified": True,
                                "notebook_path": "/Workspace/pinned/vault"}
    transport = Transport()
    request = _batch()
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger = tmp_path / "protected-ledger"
    result = submit_batch(request, authority, repo, ledger, transport)
    assert result["status"] == "SUBMITTED_REQUIRES_READBACK"
    assert readback_batch(request, repo, ledger, transport)["status"] == (
        "JOB_TERMINAL_SUCCESS_DELTA_READBACK_REQUIRED")
    with pytest.raises(Denied):
        submit_batch(request, authority, repo, ledger, transport)
    assert transport.calls == 1


def test_untrusted_authority_cannot_reserve(tmp_path):
    with pytest.raises(Denied):
        submit_batch(_batch(), _authority(), tmp_path / "repo",
                     tmp_path / "protected-ledger", Transport())
    assert not list(tmp_path.iterdir())


def test_worktree_ledger_denied(tmp_path):
    authority = _authority() | {"trusted_signature_verified": True,
                                "deployment_sha256_verified": True,
                                "source_manifest_verified": True}
    with pytest.raises(Denied, match="VAULT_LEDGER_MUST_BE_PROTECTED"):
        submit_batch(_batch(), authority, tmp_path, tmp_path / "ledger", Transport())


def test_timeout_is_durable_uncertain_and_never_replayed(tmp_path):
    class TimeoutTransport(Transport):
        def submit(self, payload):
            self.calls += 1
            raise TimeoutError("uncertain remote submit")

    authority = _authority() | {"trusted_signature_verified": True,
                                "deployment_sha256_verified": True,
                                "source_manifest_verified": True,
                                "notebook_path": "/Workspace/pinned/vault"}
    transport = TimeoutTransport()
    repo = tmp_path / "repo"
    repo.mkdir()
    ledger = tmp_path / "ledger"
    assert submit_batch(_batch(), authority, repo, ledger, transport)["status"] == (
        "UNCERTAIN_REQUIRES_READBACK")
    with pytest.raises(Denied, match="VAULT_BATCH_UNCERTAIN_RECONCILE_EXTERNALLY"):
        readback_batch(_batch(), repo, ledger, transport)
    with pytest.raises(Denied):
        submit_batch(_batch(), authority, repo, ledger, transport)
    assert transport.calls == 1


def test_unsigned_freeze_candidate_requires_complete_live_readback():
    class Reader:
        def table(self, namespace, name):
            return {"uc_table_id": "uc-1", "delta_version": 0, "row_count": 1,
                    "history_sha256": "a" * 64, "readback_sha256": "a" * 64}

        def source_coverage(self, namespace, source_ids):
            return {sid: "LOADED" for sid in source_ids}

    authority = _authority() | {"trusted_signature_verified": True}
    candidate = read_freeze_candidate(authority, Reader())
    assert candidate["status"] == "LIVE_READBACK_COMPLETE"
    assert len(candidate["tables"]) == 2
    assert len(candidate["source_coverage"]) == 2
