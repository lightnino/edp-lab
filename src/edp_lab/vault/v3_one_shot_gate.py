"""Read-only checks for the single Owner-installed Day 6 V3 Job.

This module grants no authority and never submits a Job. The protected Owner
installer must compare these checks with a signed exact grant and its ledger.
"""

from __future__ import annotations

from edp_lab.operating.authority import Denied


def verify_saved_job(settings: dict, *, wheel_path: str, run_as: dict,
                     parameters: list[str]) -> dict:
    """Fail closed on any saved setting that can add a submission or retry."""
    tasks = settings.get("tasks")
    if (settings.get("max_concurrent_runs") != 1
            or settings.get("queue", {}).get("enabled") is not False
            or settings.get("disable_auto_optimization") is not True
            or settings.get("max_retries") != 0
            or settings.get("retry_on_timeout") is not False
            or settings.get("timeout_seconds") != 3600
            or settings.get("run_as") != run_as
            or any(settings.get(key) for key in ("schedule", "trigger", "continuous"))
            or not isinstance(tasks, list) or len(tasks) != 1):
        raise Denied("VAULT_V3_SAVED_JOB_BOUND_CHANGED")
    task = tasks[0]
    if (task.get("task_key") != "day6_v3_one_shot"
            or task.get("max_retries") != 0
            or task.get("retry_on_timeout") is not False
            or task.get("timeout_seconds") != 3600
            or task.get("python_wheel_task") != {
                "package_name": "edp-lab",
                "entry_point": "edp-day6-v3",
                "parameters": parameters,
            }
            or task.get("environment_key") != "v3_fixed_runtime"
            or any(key in task for key in
                   ("existing_cluster_id", "new_cluster", "job_cluster_key", "libraries"))):
        raise Denied("VAULT_V3_SAVED_TASK_BOUND_CHANGED")
    environments = settings.get("environments")
    if (not isinstance(environments, list) or len(environments) != 1
            or environments[0].get("environment_key") != "v3_fixed_runtime"
            or environments[0].get("spec", {}).get("dependencies") != [wheel_path]):
        raise Denied("VAULT_V3_SAVED_WHEEL_BOUND_CHANGED")
    return {"status": "SAVED_ONE_SHOT_SETTINGS_VERIFIED",
            "task_key": "day6_v3_one_shot", "run_as": run_as}


def classify_one_shot(*, reserved: bool, submission_count: int,
                      terminal_success: bool, signed_readback_verified: bool) -> str:
    """The original reservation is consumed even if submission is uncertain."""
    if submission_count < 0 or submission_count > 1:
        raise Denied("VAULT_V3_SUBMISSION_LIMIT_BREACHED")
    if signed_readback_verified and reserved and submission_count == 1 and terminal_success:
        return "VERIFIED_EXISTING"
    if reserved or submission_count:
        return "PARTIAL_RECONCILE_AND_STOP"
    return "AUTHORITY_BLOCKED"
