# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Copies of a model that share nothing with it, and a fingerprint of one.

WHY ``deepcopy`` AND NEVER A ROUND TRIP THROUGH JSON. ``Project.from_dict``
is a loader, and a loader migrates: ``AdvancedSettings.from_dict`` rewrites
a ``max_lambda`` of 1.5 as 6.0 because that value, in a file, means "saved
before v0.1.90" (D182). In a copy made in memory it means "the user typed
1.5". So ``Project.from_dict(p.to_dict())`` is not an identity, and a job
analysing such a copy would analyse settings nobody chose. (The engine's own
``apply_design_factors`` copies that way, which is reported in the changelog
of v0.1.194 as widening the reach of D182, and not changed here.)

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import hashlib
import json

#: Private attributes a detached copy must not carry: the observers belong
#: to whoever is watching the original (the canvas, the window) and do not
#: pickle; the groundwater solver is a cache of the original's FE state.
_NOT_COPIED = ("_listeners", "_gw_solver")


def detached_copy(project):
    """A deep copy with no listeners and cold caches.

    Safe to hand to another thread or pickle into a child process: nothing
    in it points back at the original, and an edit to either is invisible
    to the other.
    """
    memo = {}
    for name in _NOT_COPIED:
        value = project.__dict__.get(name)
        if value is not None:
            memo[id(value)] = [] if name == "_listeners" else None
    clone = copy.deepcopy(project, memo)
    if "_listeners" in clone.__dict__:
        clone._listeners = []
    clone.invalidate_regions_cache()
    return clone


def model_hash(project) -> str:
    """SHA-256 of the serialised model, to tell whether it changed.

    ``is_dirty`` cannot answer that: ``Project.save`` clears it and then
    notifies, and the notification sets it again (reported in v0.1.194).
    Anything the analysis reads is in ``to_dict``, so equal hashes mean the
    same model as far as a result is concerned.
    """
    text = json.dumps(project.to_dict(), sort_keys=True, default=str,
                      ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()
