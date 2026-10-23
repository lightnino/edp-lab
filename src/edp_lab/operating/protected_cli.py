"""Run existing user-scoped credentials only from the root-owned boundary service."""

import os
import re

from edp_lab.operating.authority import Denied


def databricks_argv(*args: str) -> list[str]:
    user = os.environ.get("EDP_DATABRICKS_RUN_AS_USER")
    if user:
        if os.geteuid() != 0 or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
            raise Denied("PROTECTED_DATABRICKS_IDENTITY_INVALID")
        return ["/usr/bin/sudo", "-n", "-u", user, "-H", "/opt/homebrew/bin/databricks",
                *args]
    return ["databricks", *args]


def git_argv(*args: str) -> list[str]:
    user = os.environ.get("EDP_GIT_RUN_AS_USER")
    if user:
        if os.geteuid() != 0 or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
            raise Denied("PROTECTED_GIT_IDENTITY_INVALID")
        binary = {"git": "/usr/bin/git", "gh": "/opt/homebrew/bin/gh"}.get(args[0])
        if binary is None:
            raise Denied("PROTECTED_GIT_PROGRAM_INVALID")
        return ["/usr/bin/sudo", "-n", "-u", user, "-H", binary, *args[1:]]
    return list(args)
