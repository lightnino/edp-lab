"""Run existing user-scoped credentials only from the root-owned boundary service."""

import os
import re
from configparser import ConfigParser
from pathlib import Path

from edp_lab.operating.authority import Denied


def databricks_argv(*args: str) -> list[str]:
    user = os.environ.get("EDP_DATABRICKS_RUN_AS_USER")
    if os.environ.get("EDP_DAY7_PROTECTED") == "1" and user:
        raise Denied("DAY7_M2M_IDENTITY_REQUIRED")
    if user:
        if os.geteuid() != 0 or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
            raise Denied("PROTECTED_DATABRICKS_IDENTITY_INVALID")
        return ["/usr/bin/sudo", "-n", "-u", user, "-H", "/opt/homebrew/bin/databricks",
                *args]
    if os.geteuid() == 0:
        config = os.environ.get("DATABRICKS_CONFIG_FILE")
        if os.environ.get("EDP_DAY7_PROTECTED") == "1":
            expected = Path("/private/var/db/edp-lab-day7/private/databrickscfg")
            if (config != str(expected) or not expected.is_file()
                    or expected.stat().st_uid != 0 or expected.stat().st_mode & 0o077):
                raise Denied("DAY7_M2M_CREDENTIAL_STORE_REQUIRED")
            parser = ConfigParser(interpolation=None)
            parser.read(expected)
            if (not parser.has_section("edp-lab")
                    or parser.get("edp-lab", "auth_type", fallback="") != "oauth-m2m"
                    or parser.get("edp-lab", "host", fallback="")
                    != "https://dbc-23e7784b-bb6e.cloud.databricks.com"
                    or not parser.get("edp-lab", "client_id", fallback="")
                    or not parser.get("edp-lab", "client_secret", fallback="")):
                raise Denied("DAY7_M2M_CREDENTIALS_REQUIRED")
        else:
            expected = Path("/private/var/db/edp-lab/private/databrickscfg")
            if (config != str(expected) or not expected.is_file()
                    or expected.stat().st_uid != 0 or expected.stat().st_mode & 0o077
                    or os.environ.get("DATABRICKS_AUTH_STORAGE") != "plaintext"):
                raise Denied("PROTECTED_DATABRICKS_CREDENTIAL_STORE_REQUIRED")
        return ["/opt/homebrew/bin/databricks", *args]
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
