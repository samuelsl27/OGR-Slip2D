# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D442 (v0.1.503) — Interpret's «Critical Probabilistic Surface» toggle DRAWS
the surface, and says when the user defined it.

The invariant
-------------
From v0.1.37 the toggle (``_toggle_critical_prob``) only wrote the PF and
the reliability index on the status bar: ticking it left the canvas the same
image bit for bit (measured with 0.1.485 and again with 0.1.502), the defect
v0.1.126 mended in its neighbour Show GM Surfaces. Since v0.1.454 (D417) the
critical probabilistic surface can be a surface the user defined, and the
status bar did not say so. Now:

* ticking the toggle changes the canvas image, and unticking it gives back
  the image from before, bit for bit (rule 7: the control moves what is
  seen);
* the status bar says «, defined by the user.» (D401's words) exactly when
  the run's critical probabilistic surface is one the user defined
  (``SurfaceProbability.user_defined``, set by the run, which is the only
  one that knows it); the control, the same run without the user's
  polyline, does not say it, and still draws;
* the entry going grey (D413's gate, the statistics gone) unticks it and
  takes the drawing with it.

No number moves: the PF, the index and the surface are D417's. The case is
the one of the ficha, the demo slope with Path Search of 5 without
optimisation, Janbu, one polyline of the user and a normal cohesion (30 %,
range ±60 %), 20 Latin Hypercube samples: there the polyline is the critical
probabilistic surface with PF 10 %. The two statistics runs are computed once
for the file (a few seconds each).
"""
from __future__ import annotations

import hashlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_POLY = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]
_CACHE: dict = {}


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _snap(widget) -> str:
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    widget.grab().toImage().save(buf, "PNG")
    return hashlib.sha1(bytes(buf.data())).hexdigest()


def _windows(with_user: bool):
    """Main window and Interpret for the ficha's case; built once each."""
    if with_user in _CACHE:
        return _CACHE[with_user]
    _app()
    from ogr_core.project.settings import SurfaceType
    from ogr_core.statistics import SamplingMethod, available_variables
    from ogr_core.statistics.distributions import (Distribution,
                                                   DistributionType as T)
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_gui.main_window import MainWindow
    from ogr_slip2d.analysis_runner import (run_analysis,
                                            run_configured_statistics)
    from ogr_slip2d.surface import UserPolylineSurface

    w = MainWindow()
    w.project.is_dirty = False
    w.act_load_demo()
    p = w.project
    s = p.settings.search
    s.surface_type = SurfaceType.NON_CIRCULAR.value
    s.search_method = "path"
    s.path_num_surfaces, s.optimize_enabled = 5, False
    p.settings.methods.enabled_methods = ["janbu_simplified"]
    if with_user:
        p.user_polylines = [UserPolylineSurface.from_points(_POLY)]
    rv = next(v for v in available_variables(p)
              if v.key.endswith(":cohesion"))
    m = rv.distribution.mean
    rv.distribution = Distribution(T.NORMAL, m, 0.3 * m, 0.6 * m, 0.6 * m)
    p.random_variables = [rv]
    st = p.settings.statistics
    st.probabilistic_analysis, st.sensitivity_analysis = True, False
    st.analysis_type, st.num_samples = "overall_slope", 20
    st.sampling_method = SamplingMethod.LATIN_HYPERCUBE.value
    out = run_configured_statistics(p)
    w._prob_result, w._sens_result = out.probabilistic, None
    iw = InterpretWindow(
        p, dict(run_analysis(p, ["janbu_simplified"]).results), w)
    w.interpret_windows.append(iw)
    iw.resize(1200, 800)
    iw.show()
    w._update_statistics_actions()
    # kept to the end of the process, as every MainWindow of the suite is
    _CACHE[with_user] = (w, iw)
    return w, iw


def _cp(w):
    return w._prob_result.reported.critical_probabilistic


class TestTheCriticalProbabilisticSurfaceIsDrawn:
    def test_the_premise_the_users_polyline_is_critical_with_pf_10(self):
        w, _iw = _windows(True)
        cp = _cp(w)
        assert cp is not None
        assert abs(cp.probability_of_failure - 0.10) < 1e-12
        assert cp.user_defined is True

    def test_ticking_draws_and_unticking_gives_the_image_back(self):
        _w, iw = _windows(True)
        act = iw._act_crit_prob
        act.setChecked(False)
        before = _snap(iw.canvas)
        try:
            act.setChecked(True)
            on = _snap(iw.canvas)
            msg = iw.statusBar().currentMessage()
        finally:
            act.setChecked(False)
        after = _snap(iw.canvas)
        assert on != before, "the toggle drew nothing"
        assert after == before
        assert msg.endswith(", defined by the user."), msg
        assert "PF = 10.00 %" in msg, msg

    def test_a_surface_of_the_search_is_not_called_the_users(self):
        w, iw = _windows(False)
        cp = _cp(w)
        assert cp is not None and cp.user_defined is False
        act = iw._act_crit_prob
        act.setChecked(False)
        before = _snap(iw.canvas)
        try:
            act.setChecked(True)
            on = _snap(iw.canvas)
            msg = iw.statusBar().currentMessage()
        finally:
            act.setChecked(False)
        assert on != before
        assert msg.startswith("Critical probabilistic surface: PF = ")
        assert "user" not in msg, msg

    def test_the_grey_gate_unticks_it_and_takes_the_drawing(self):
        w, iw = _windows(True)
        act = iw._act_crit_prob
        act.setChecked(False)
        before = _snap(iw.canvas)
        prob = w._prob_result
        act.setChecked(True)
        try:
            w._prob_result = None
            w._update_statistics_actions()
            assert not act.isEnabled() and not act.isChecked()
            assert _snap(iw.canvas) == before
        finally:
            w._prob_result = prob
            w._update_statistics_actions()
            act.setChecked(False)
