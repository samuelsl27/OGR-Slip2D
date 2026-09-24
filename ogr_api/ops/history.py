# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Undo and redo.

Every edit made through this layer — including a whole ``python_exec``
script — is one step here, and a step restores the model exactly as it
was (``SnapshotCommand``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..coerce import coerce_value
from ..errors import InvalidArgument, unknown
from . import operation


@operation("project_history", toolset="history", mutates=True)
def project_history(ws, project_id: Optional[str] = None,
                    action: str = "list", steps: int = 1) -> dict:
    """List, undo or redo edits."""
    if action not in ("list", "undo", "redo"):
        raise unknown("history action", action, ["list", "undo", "redo"])
    steps = coerce_value(steps, int, "steps")
    if not 1 <= steps <= 200:
        raise InvalidArgument("steps must be between 1 and 200.")
    handle = ws.get(project_id)
    done = []
    with ws.reading(handle.id, f"history {action}") as project:
        for _ in range(steps if action != "list" else 0):
            cmd = (handle.stack.undo(project) if action == "undo"
                   else handle.stack.redo(project))
            if cmd is None:
                break
            d = cmd.description
            done.append(d() if callable(d) else str(d))
        undo, redo = handle.stack.history()
    return {"project_id": handle.id, "action": action, "done": done,
            "undo": undo[-10:], "redo": redo[-10:]}
