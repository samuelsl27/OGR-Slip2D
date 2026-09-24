# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The registry of named operations.

An operation is a plain Python function ``op(ws, **kwargs) -> dict`` with a
stable name, a toolset and a flag saying whether it edits a model. The MCP
server publishes one tool per operation, written by hand so each keeps its
own description and types; the live bridge of phase F4 will forward
``(name, kwargs)`` here unchanged. One registry is what keeps the two
front ends from drifting into two different programs.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..errors import unknown


@dataclass(frozen=True)
class Operation:
    name: str
    func: Callable
    toolset: str
    mutates: bool

    @property
    def summary(self) -> str:
        doc = (self.func.__doc__ or "").strip()
        return doc.splitlines()[0] if doc else ""


REGISTRY: dict[str, Operation] = {}


def operation(name: str, *, toolset: str, mutates: bool = False):
    """Register ``func`` under ``name``."""
    def deco(func):
        if name in REGISTRY:
            raise ValueError(f"operation {name!r} registered twice")
        REGISTRY[name] = Operation(name, func, toolset, mutates)
        return func
    return deco


def call(ws, op_name: str, /, **kwargs):
    """Run the operation ``op_name`` on workspace ``ws``.

    Both leading arguments are positional-only, so an operation may take a
    keyword called ``name`` (``project_new(name=...)``).
    """
    op = REGISTRY.get(op_name)
    if op is None:
        raise unknown("operation", op_name, sorted(REGISTRY))
    return op.func(ws, **kwargs)


# Registration happens on import. The annotation operations live in
# ``annotation_ops`` and not ``annotations``: this package has
# ``from __future__ import annotations``, so ``from . import annotations``
# returns that __future__ feature object instead of importing the module —
# the four operations silently never registered (found in v0.1.196).
from . import (project, model, settings, analysis, view, history,  # noqa: E402,F401
               python, loads, supports, search_objects, annotation_ops,
               files, groundwater)
