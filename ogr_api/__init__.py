# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
OGR Slip2D — the operations layer (spec 008).

Everything the program can do to a model, as named operations with typed
arguments and JSON-safe answers, usable without Qt and without the MCP SDK:

    from ogr_api import Workspace, call

    ws = Workspace()
    pid = call(ws, "project_new", name="Demo")["project_id"]
    call(ws, "model_define", project_id=pid, spec={...})
    out = call(ws, "analysis_run", project_id=pid, wait_seconds=60)

It sits ABOVE the engine (``ogr_core``, ``ogr_slip2d``, ``ogr_fem2d``) and
BELOW every front end: the MCP server (``ogr_mcp``), and — from phase F4 —
the live bridge inside the interface. It never imports PySide6, ``ogr_gui``
or ``mcp``; ``tests/test_api_layering_v1194.py`` fails if it does.

What it adds on top of the engine, and why each piece exists:

* **handles** — a model lives under a ``project_id`` the caller passes back,
  because the 2026-07-28 MCP protocol keeps no session;
* **validation** — the engine's dataclasses accept a misspelled setting in
  silence and an unknown search method becomes a grid search; here both are
  refused, with a suggestion;
* **undo** — every edit, including a Python script, is one undo step;
* **jobs** — an analysis runs in a child process that can be cancelled,
  because the engine cannot be interrupted and a run can take an hour;
* **summaries and a PNG render** — a language model reads a summary, not a
  30 MB result object.

Author: Samuel Sáez López (UPCT)
"""
__version__ = "0.1.204"

from .errors import (  # noqa: E402
    Busy,
    Conflict,
    InvalidArgument,
    JobFailed,
    NotConfigured,
    NotFound,
    OgrApiError,
)
from .workspace import Workspace  # noqa: E402
from .ops import REGISTRY as OPERATIONS, call  # noqa: E402

__all__ = [
    "Workspace",
    "call",
    "OPERATIONS",
    "OgrApiError",
    "NotFound",
    "InvalidArgument",
    "Conflict",
    "NotConfigured",
    "Busy",
    "JobFailed",
]
