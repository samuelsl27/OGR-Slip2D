# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.269 (D265) — the Picard loop publishes its convergence history, and
the two Interpret entries that read it draw it.

The defect
----------
``solve_unsaturated`` built the change of every pass in a list and kept
only the last one (``picard_delta``). *Iteration History…* and
*Convergence Plot…* read ``notes["history"]``, which nobody wrote, so two
reachable menu entries could only ever say that nothing was recorded, and
a test (``test_interpret_i3_v153``) demanded exactly that.

The invariants
--------------
* **One entry per pass, and it is the unrelaxed change.** The loop stops
  on the RELAXED change w·max|H_new − H| (``picard_delta``); the published
  series is max|H_new − H| itself, which does not depend on w. So the
  identity ``history[-1] · w = picard_delta`` holds to the four
  significant figures the series keeps, and a converged loop ends below
  ``tolerance / w``.
* **The rescue is marked.** When it runs, its entries follow, with the
  same measure max|G(H) − H|, and ``history_segments`` says where each part
  starts; the rescue stops on that measure against the tolerance itself.
* **A transient stage carries the history of its last step.**
* **It survives a save, and the save stays JSON.** Non-finite notes are
  written as null: ``json.dumps`` would write ``NaN``, which is not JSON.
* **Both entries draw** — through ``_plot_xy``, never ``_info`` (which
  opens a modal box, so the tests shadow both on the instance).

Nothing here moves a number: the series is read from the heads, the heads
are not touched. That is checked on the groundwater bank, tree against
tree (``_auditoria/P6_0269`` of the bank).
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import matplotlib
    matplotlib.use("Agg")
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    SeepageResult,
    TransientSeepageSolver,
    TransientStage,
    UnsaturatedSeepageSolver,
)

W, TOL = 0.4, 1e-5


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _dam():
    """The rectangular Gardner dam of ``test_unsaturated_v127``."""
    spec = importlib.util.spec_from_file_location(
        "t127_d265", Path(__file__).parent / "test_unsaturated_v127.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    mesh = t._dam_mesh(0.7)
    props = {"m": HydraulicProperties(
        ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
        gardner_n=3.0,
        # the retention these numbers were measured with (the
        # default alpha up to 0.1.277; v0.1.278, D275)
        wc_alpha=3.6)}
    return mesh, props, t._dam_bcs(mesh)


_CACHE: dict = {}


def _runs():
    if not _CACHE:
        mesh, props, bcs = _dam()
        _CACHE["loop"] = UnsaturatedSeepageSolver(
            mesh, props, relaxation=W, max_iterations=250,
            tolerance=TOL).solve_unsaturated(bcs)
        # One pass is not enough: the rescue takes over from it.
        _CACHE["rescue"] = UnsaturatedSeepageSolver(
            mesh, props, relaxation=W, max_iterations=1,
            tolerance=TOL).solve_unsaturated(bcs)
        _CACHE["dam"] = (mesh, props, bcs)
    return _CACHE


class TestTheSteadyHistory:
    def test_one_entry_per_pass(self):
        r = _runs()["loop"]
        assert r.converged and "rescue" not in r.notes, r.notes
        assert len(r.notes["history"]) == r.iterations > 3
        assert r.notes["history_segments"] == [["picard", 0]]
        assert r.notes["tolerance"] == TOL

    def test_the_entries_are_the_unrelaxed_change(self):
        r = _runs()["loop"]
        last = r.notes["history"][-1]
        # four significant figures: the identity holds to 5e-4 relative
        assert abs(last * W - r.notes["picard_delta"]) \
            <= 5e-4 * r.notes["picard_delta"], (last, r.notes)
        # the loop stopped on the relaxed change: below tol / w, and in
        # this run not below tol itself (what the chart's line shows)
        assert TOL <= last < TOL / W, last

    def test_the_first_passes_move_the_most(self):
        h = _runs()["loop"].notes["history"]
        assert max(h[:3]) > 100 * h[-1], h

    def test_the_rescue_is_marked(self):
        r = _runs()["rescue"]
        assert r.converged and r.notes["rescue"].startswith("anderson"), \
            r.notes
        h, seg = r.notes["history"], r.notes["history_segments"]
        assert seg[0] == ["picard", 0]
        assert seg[1][0].startswith("anderson") and seg[1][1] == 1, seg
        # one entry per map evaluation: the loop's pass plus the rescue's
        assert len(h) == r.iterations, (len(h), r.iterations)
        # the rescue stops on the unrelaxed change against tol itself
        assert h[-1] < TOL, h[-3:]

    def test_it_survives_a_save(self):
        r = _runs()["loop"]
        text = json.dumps(r.to_dict(), allow_nan=False)
        back = SeepageResult.from_dict(json.loads(text))
        assert back.notes["history"] == r.notes["history"]
        assert back.notes["history_segments"] == r.notes["history_segments"]


class TestTheSaveIsJson:
    def test_non_finite_notes_are_written_as_null(self):
        r = SeepageResult(total_head=[1.0], converged=True)
        r.notes.update({"picard_delta": float("nan"),
                        "rescue_residual": float("inf"),
                        "history": [1.0, None],
                        "nested": {"a": [float("-inf"), 2.0]}})
        d = r.to_dict()
        json.dumps(d, allow_nan=False)          # raises on NaN / inf
        n = d["notes"]
        assert n["picard_delta"] is None and n["rescue_residual"] is None
        assert n["history"] == [1.0, None]
        assert n["nested"] == {"a": [None, 2.0]}
        # and the in-memory result is not touched
        assert math.isnan(r.notes["picard_delta"])


class TestATransientStage:
    def test_carries_the_history_of_its_last_step(self):
        mesh, props, bcs = _runs()["dam"]
        s = TransientSeepageSolver(mesh, props, relaxation=0.5,
                                   tolerance=TOL, time_steps=2,
                                   max_picard=30)
        st = s.solve_transient([TransientStage(time=3600.0, bcs=bcs)],
                               initial_bcs=bcs)[-1]
        h = st.notes["history"]
        assert 1 <= len(h) <= 30, h
        assert st.notes["history_segments"] == [["picard", 0]]
        assert st.notes["relaxation"] == 0.5
        assert st.notes["tolerance"] == TOL
        if st.converged:
            assert h[-1] < TOL / 0.5, h


@_requires_qt
class TestTheTwoEntriesDraw:
    def _window(self, result):
        from test_interpret_i3_v153 import _interpret
        p, _r, w = _interpret()
        p.seepage_result = result
        plotted, shown = [], []
        w._plot_xy = lambda *a, **k: plotted.append((a, k))
        w._info = lambda *a, **k: shown.append(a)
        return w, plotted, shown

    def test_iteration_history(self):
        r = _runs()["loop"]
        w, plotted, shown = self._window(r)
        w._gw_iteration_history()
        assert not shown and len(plotted) == 1, (plotted, shown)
        (title, series, _xl, _yl), _k = plotted[0]
        assert len(series) == 1
        _label, xs, ys = series[0]
        assert xs == list(range(1, r.iterations + 1))
        assert ys == r.notes["history"]

    def test_convergence_plot_with_the_stop_threshold(self):
        r = _runs()["loop"]
        w, plotted, shown = self._window(r)
        w._gw_convergence()
        assert not shown and len(plotted) == 1, (plotted, shown)
        (title, series, _xl, _yl), kw = plotted[0]
        assert kw.get("yscale") == "log"
        assert series[0][2] == r.notes["history"]
        # the loop's own stop line: tolerance / relaxation
        assert series[1][2] == [TOL / W, TOL / W], series[1]

    def test_the_rescue_is_its_own_series(self):
        r = _runs()["rescue"]
        w, plotted, _shown = self._window(r)
        w._gw_iteration_history()
        (_t, series, _xl, _yl), _k = plotted[0]
        assert len(series) == 2, [s[0] for s in series]
        assert series[0][1] == [1]
        assert series[1][1][0] == 2
        w._gw_convergence()
        (_t, series, _xl, _yl), _k = plotted[1]
        # loop, rescue, and one stop line for each
        assert [s[2] for s in series[2:]] == [[TOL / W, TOL / W],
                                             [TOL, TOL]], series[2:]

    def test_the_real_chart_opens(self):
        from test_interpret_i3_v153 import _interpret
        p, _r, w = _interpret()
        p.seepage_result = _runs()["rescue"]
        shown = []
        w._info = lambda *a, **k: shown.append(a)
        dlg = w._gw_convergence() or w._chart_windows[-1]
        assert dlg is not None and not shown
