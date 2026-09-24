# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
``python_exec``: arbitrary Python against a model — by design.

The owner chose to keep it always available (2026-09-24), as Blender's and
QGIS's servers do, for whatever no dedicated operation covers yet. It runs
in the SERVER process with the full power of that process; the only
protection is who can reach the server, which is why the HTTP transport
always demands a token (see ``docs/mcp/seguridad.md``).

The namespace persists per model between calls and holds, like the
interface's terminal (``TerminalDock.attach_context``): ``project``,
``np``, ``ogr_core``, ``ogr_slip2d`` — plus ``api``, which calls any
operation of this layer (``api.material_set(name=..., ...)``), and
``result(result_id)``, which returns a stored result in full.

The whole script is ONE undo step, and an edit made through ``api`` inside
it belongs to that step.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import inspect
from typing import Optional

from . import REGISTRY, call, operation


class ApiFacade:
    """``api.<operation>(**kwargs)``, with ``project_id`` filled in."""

    def __init__(self, ws, project_id: Optional[str]) -> None:
        self._ws = ws
        self._pid = project_id

    def __getattr__(self, name):
        if name.startswith("_") or name not in REGISTRY:
            raise AttributeError(
                f"api has no operation {name!r}; see api.operations()")
        op = REGISTRY[name]
        takes_pid = "project_id" in inspect.signature(op.func).parameters

        def invoke(**kwargs):
            if takes_pid and "project_id" not in kwargs and self._pid:
                kwargs["project_id"] = self._pid
            return call(self._ws, name, **kwargs)

        invoke.__doc__ = op.func.__doc__
        return invoke

    def operations(self) -> list[str]:
        return sorted(REGISTRY)

    def __dir__(self):
        return self.operations()


def _namespace(ws, handle) -> dict:
    import numpy as np

    import ogr_core
    import ogr_slip2d

    ns = handle.exec_ns if handle is not None else ws.__dict__.setdefault(
        "_exec_ns", {})
    ns.update({
        "np": np, "ogr_core": ogr_core, "ogr_slip2d": ogr_slip2d,
        "api": ApiFacade(ws, handle.id if handle else None),
        "result": lambda rid: ws.find_result(rid)[1].payload(),
    })
    if handle is not None:
        ns["project"] = handle.project
    return ns


@operation("python_exec", toolset="python", mutates=True)
def python_exec(ws, code: str, project_id: Optional[str] = None) -> dict:
    """Run Python with `project`, `api`, `np`, `ogr_core`, `ogr_slip2d`."""
    from ..pyexec import run_python

    if not ws.projects and project_id is None:
        out = run_python(code, _namespace(ws, None))
        return {"project_id": None, **out}
    handle = ws.get(project_id)

    def edit(project):
        out = run_python(code, _namespace(ws, handle))
        if not out["ok"]:
            # A script that raised half-way must not leave half its edits
            # behind: raising here makes the snapshot put the model back.
            raise _ScriptFailed(out)
        return out

    try:
        out = ws.mutate(handle.id, "Python script", edit)
    except _ScriptFailed as failed:
        return {"project_id": handle.id, **failed.out, "rolled_back": True}
    return {"project_id": handle.id, **out, "rolled_back": False}


class _ScriptFailed(Exception):
    def __init__(self, out: dict) -> None:
        super().__init__(out.get("error"))
        self.out = out
