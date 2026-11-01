# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.402 (D387) — an agent's analysis shown in the window is loaded from its
job once, and the window and the API share it.

WHAT INVARIANT THIS PROTECTS.

Found in the census of D383 (2026-11-01), after the interface test of
0.1.397. ``_finish_analysis`` stored the result with a lazy loader
(``loader=job.load_results``). When the agent worked on the window and the
model had not changed, it unpickled ``result.pkl`` to show it there. At the
first question (``results_get``, ``results_query``) the ``StoredResult``
called the same loader again and kept what it returned. So the window's
process held two full copies of the same result, slices included: at 57 kB
an evaluation, gigabytes on a big grid. It dated from 0.1.203.

1. **On the window, one load:** the job's result is unpickled once, the
   window shows it, and the stored result answers with the same objects
   without loading again.
2. **Without a window, still lazy:** nothing is loaded until a question
   needs it, and then once.
3. **A changed model is not shown** and is not loaded (as before): the
   result is of a model that no longer exists.

A fake job counts the loads; the workspace and its stored results are real.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))


def _setup(with_window: bool, model_changed: bool = False):
    from ogr_api.snapshot import model_hash
    from ogr_api.workspace import Workspace
    from ogr_core.project import Project
    ws = Workspace()
    handle = ws.add(Project())
    loads, shown = [], []

    def load_results():
        # new objects at every load, as unpickling ``result.pkl`` gives
        loads.append(1)
        return {"results": {"bishop_simplified": object()},
                "factor_report": None, "warnings": []}
    fingerprint = model_hash(handle.project)
    if model_changed:
        fingerprint = "an earlier model"
    job = SimpleNamespace(id="j_test", model_hash=fingerprint,
                          load_results=load_results, result_id=None)
    if with_window:
        ws.host = SimpleNamespace(
            handle_id=handle.id,
            show_analysis=lambda results, report, warnings: shown.append(
                results))
    return ws, handle, job, loads, shown


class TestLoadedOnce:
    """Invariants 1 to 3."""

    def test_on_the_window_one_load_shared(self):
        from ogr_api.ops.analysis import _finish_analysis
        ws, handle, job, loads, shown = _setup(with_window=True)
        out = _finish_analysis(ws, job, handle, {})
        assert out == {"shown_in_window": True}
        assert len(loads) == 1 and len(shown) == 1
        res = handle.results[job.result_id]
        results = res.payload()["results"]
        assert len(loads) == 1, "the stored result loaded it again"
        assert results is shown[0], "the window and the API hold two copies"

    def test_without_a_window_still_lazy(self):
        from ogr_api.ops.analysis import _finish_analysis
        ws, handle, job, loads, shown = _setup(with_window=False)
        assert _finish_analysis(ws, job, handle, {}) == {}
        assert loads == [], "loaded with nobody asking"
        res = handle.results[job.result_id]
        res.payload()
        res.payload()
        assert len(loads) == 1

    def test_a_changed_model_is_not_shown(self):
        from ogr_api.ops.analysis import _finish_analysis
        ws, handle, job, loads, shown = _setup(with_window=True,
                                               model_changed=True)
        assert _finish_analysis(ws, job, handle, {}) == {}
        assert loads == [] and shown == []
