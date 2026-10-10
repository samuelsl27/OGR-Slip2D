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

import hashlib
import json

from ogr_core.project.copies import NOT_COPIED as _NOT_COPIED  # noqa: F401
from ogr_core.project.copies import detached_copy as _detached_copy


def detached_copy(project):
    """A deep copy with no listeners and cold caches.

    Safe to hand to another thread or pickle into a child process: nothing
    in it points back at the original, and an edit to either is invisible
    to the other.

    v0.1.236 (D246) — the recipe lives in ``ogr_core.project.copies`` now,
    where the statistical engine's ``clone_project`` can use it too: that
    one was a bare ``deepcopy``, and on a project bound to the main window
    it died on the window's own listener. This keeps the operations
    layer's contract (cold caches) and its name.
    """
    return _detached_copy(project, cold_caches=True)


def model_hash(project) -> str:
    """SHA-256 of what an ANALYSIS reads, to tell whether a result is stale.

    The annotation layer is left out (v0.1.196): the solver never reads it
    (``tech-stack.md``: "the solver never reads ``Project.annotations``"), so
    drawing a dimension line must not mark a result as computed on another
    model. Everything else in ``to_dict`` is in.
    """
    data = project.to_dict()
    data.pop("annotations", None)
    return _sha(data)


def document_hash(project) -> str:
    """SHA-256 of the WHOLE serialised model, annotations included.

    What "unsaved changes" means. ``is_dirty`` could not answer it until
    v0.1.203: ``Project.save`` cleared it and then notified, and the
    notification set it again (reported in v0.1.194). ``Project._notify``
    leaves it alone for "saved" since then, and the window asks it before
    closing (v0.1.296, D283).
    """
    return _sha(project.to_dict())


def _sha(data) -> str:
    text = json.dumps(data, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()
