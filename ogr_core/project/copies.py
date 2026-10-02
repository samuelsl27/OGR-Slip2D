# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Copies of a project that share nothing with whoever is watching it.

v0.1.236 (D246). A project bound to the main window carries the window's
own method in ``_listeners`` (``MainWindow._attach_project`` adds
``self._on_project_event``), and ``copy.deepcopy`` copies a bound method by
deep-copying the object it is bound to: the window, which does not copy.
So every statistical run started from the menu died in its first
``clone_project`` with ``TypeError: cannot pickle 'MainWindow' object``,
since v0.1.59, on any project the window had attached (new, opened or the
demo). The tests never saw it: they hand the window a project by
assignment, and the canvas's own listener is a lambda, which ``deepcopy``
shares instead of copying. The operations layer had already solved the
same problem for its jobs (``ogr_api.snapshot.detached_copy``); this is
that recipe, moved where the engine can use it.

WHY ``deepcopy`` AND NEVER A ROUND TRIP THROUGH JSON: see
``ogr_api.snapshot`` — the loader migrates (D182), so
``Project.from_dict(p.to_dict())`` is not an identity.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy

#: Private attributes a detached copy does not carry. The observers belong
#: to whoever is watching the original (the canvas, the window) and do not
#: copy: a bound method drags its object along. The groundwater solver is a
#: cache of the original's finite-element state, rebuilt on demand
#: (``transient_stability.groundwater_query_solver``).
NOT_COPIED = ("_listeners", "_gw_solver")


def detached_copy(project, *, cold_caches: bool = True):
    """A deep copy with no listeners, sharing nothing with ``project``.

    Safe to hand to another thread or pickle into a child process: nothing
    in it points back at the original, and an edit to either is invisible
    to the other.

    ``cold_caches`` drops the copy's region and bounding-box caches, which
    is what a copy handed to another thread needs. A statistical sample
    keeps them (``cold_caches=False``): ``clone_project`` copied them with
    everything else before this function existed, a sample changes
    parameters and not the External or Material boundaries the regions are
    built from, and the cache revalidates on its own signature when they
    do change (``Project.resolve_regions``), so keeping it is the old
    behaviour and costs no recomputation per sample.
    """
    memo = {}
    for name in NOT_COPIED:
        value = project.__dict__.get(name)
        if value is not None:
            memo[id(value)] = [] if name == "_listeners" else None
    clone = copy.deepcopy(project, memo)
    if "_listeners" in clone.__dict__:
        clone._listeners = []
    if cold_caches:
        clone.invalidate_regions_cache()
    return clone
