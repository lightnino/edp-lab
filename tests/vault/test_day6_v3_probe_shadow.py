"""Prevent the launchd service socket check from hiding its probe handler."""

from __future__ import annotations

import inspect
import symtable

from edp_lab.vault import v3_service


def test_v3_service_probe_dispatch_cannot_be_shadowed_by_local_socket():
    """serve() closes over probe() in Handler; a local 'as probe' breaks it."""
    source = inspect.getsource(v3_service.serve)
    table = symtable.symtable(source, "v3_service.serve", "exec")
    serve = next(child for child in table.get_children() if child.get_name() == "serve")
    assert not serve.lookup("probe").is_local()
    assert callable(v3_service.probe)
    assert "as existing_socket" in source
