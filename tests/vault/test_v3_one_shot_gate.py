"""One-shot saved Job and interrupted-run guards."""

import pytest

from edp_lab.operating.authority import Denied
from edp_lab.vault.v3_one_shot_gate import classify_one_shot, verify_saved_job


def _saved():
    parameters = ["--request", "/Workspace/Shared/request.json", "--execute"]
    wheel = "/Workspace/Shared/edp-lab/day6-c2000-v3/edp_lab-0.1.0-py3-none-any.whl"
    identity = {"service_principal_name": "87df13c2-1bb7-4a0b-b84a-84e01bdc1764"}
    settings = {
        "max_concurrent_runs": 1, "queue": {"enabled": False},
        "timeout_seconds": 3600, "run_as": identity,
        "tasks": [{"task_key": "day6_v3_one_shot", "max_retries": 0,
                   "retry_on_timeout": False,
                   "disable_auto_optimization": True, "timeout_seconds": 3600,
                   "python_wheel_task": {"package_name": "edp-lab",
                                         "entry_point": "edp-day6-v3",
                                         "parameters": parameters},
                   "environment_key": "v3_fixed_runtime"}],
        "environments": [{"environment_key": "v3_fixed_runtime",
                          "spec": {"dependencies": [wheel]}}],
    }
    return settings, wheel, identity, parameters


def test_exact_saved_one_shot_job():
    settings, wheel, identity, parameters = _saved()
    assert verify_saved_job(settings, wheel_path=wheel, run_as=identity,
                            parameters=parameters)["status"] == "SAVED_ONE_SHOT_SETTINGS_VERIFIED"


@pytest.mark.parametrize("change", [
    lambda value: value.update(disable_auto_optimization=True),
    lambda value: value.update(max_retries=0),
    lambda value: value.update(retry_on_timeout=False),
    lambda value: value.update(queue={"enabled": True}),
    lambda value: value.update(schedule={"quartz_cron_expression": "* * * * * ?"}),
    lambda value: value["tasks"][0].update(max_retries=1),
    lambda value: value["tasks"][0].update(retry_on_timeout=True),
    lambda value: value["tasks"][0].update(disable_auto_optimization=False),
    lambda value: value["tasks"][0].pop("disable_auto_optimization"),
    lambda value: value["tasks"][0].update(new_cluster={}),
    lambda value: value["environments"][0]["spec"].update(dependencies=["other.whl"]),
])
def test_saved_job_drift_denied(change):
    settings, wheel, identity, parameters = _saved()
    change(settings)
    with pytest.raises(Denied):
        verify_saved_job(settings, wheel_path=wheel, run_as=identity,
                         parameters=parameters)


def test_interruption_stops_partial_without_retry():
    assert classify_one_shot(reserved=True, submission_count=1,
                             terminal_success=False,
                             signed_readback_verified=False) == "PARTIAL_RECONCILE_AND_STOP"
    assert classify_one_shot(reserved=True, submission_count=0,
                             terminal_success=False,
                             signed_readback_verified=False) == "PARTIAL_RECONCILE_AND_STOP"
    assert classify_one_shot(reserved=False, submission_count=1,
                             terminal_success=False,
                             signed_readback_verified=False) == "PARTIAL_RECONCILE_AND_STOP"
    assert classify_one_shot(reserved=True, submission_count=1,
                             terminal_success=True,
                             signed_readback_verified=True) == "VERIFIED_EXISTING"
    with pytest.raises(Denied):
        classify_one_shot(reserved=True, submission_count=2,
                          terminal_success=True, signed_readback_verified=True)
