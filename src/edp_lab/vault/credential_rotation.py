"""Atomic protected Vault service-principal credential rotation primitive."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from edp_lab.operating.authority import Denied


def rotate_config(config: Path, new_contents: str,
                  probe: Callable[[Path], bool]) -> None:
    """Test a staged secret before swapping the protected config in place.

    The caller must obtain the new secret through an owner-controlled process.
    No secret is returned, logged, or written in an agent-writable directory.
    """
    parent = config.parent.resolve(strict=True)
    if (os.geteuid() != 0 or parent.stat().st_uid != 0
            or parent.stat().st_mode & 0o077
            or config.stat().st_uid != 0 or config.stat().st_mode & 0o077):
        raise Denied("VAULT_CREDENTIAL_BOUNDARY_REQUIRED")
    _rotate_file(config, new_contents, probe)


def _rotate_file(config: Path, new_contents: str,
                 probe: Callable[[Path], bool]) -> None:
    parent = config.parent.resolve(strict=True)
    if not new_contents.startswith("[vault-dev]\n") or "client_secret = " not in new_contents:
        raise Denied("VAULT_NEW_CREDENTIAL_INVALID")
    with tempfile.NamedTemporaryFile(mode="w", dir=parent, prefix="rotation-",
                                     delete=False) as stream:
        staged = Path(stream.name)
        os.chmod(staged, 0o600)
        stream.write(new_contents)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if not probe(staged):
            raise Denied("VAULT_NEW_CREDENTIAL_PROBE_FAILED")
        os.replace(staged, config)
    finally:
        if staged.exists():
            staged.unlink()
