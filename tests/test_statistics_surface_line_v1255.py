# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The statistics window names the surface each Global Minimum method was
sampled on, and says the samples that answered for another mechanism under a
title of their own (D128).

WHAT INVARIANT THIS PROTECTS. ``MethodProbabilisticResult.surface`` has been
written since v0.1.35 and read by nobody but the tests: the window said what
the samples gave and never what they were sampled on — and two methods of
one model can be sampled on different circles. Now:

* ``summary()["surface_key"]`` carries the identity of that surface (the API
  and the MCP server inherit it), and the window's status line names it —
  type, centre and radius or base, the weak layers by their material, and the
  extent of the mass — in Global Minimum only: in Overall Slope every sample
  searches anew and no single surface was sampled;
* the lines that say samples answered for another sliding mass (D89) or
  another weak-layer case (D85) leave "What this run could not do:", which
  they never were, for their own title. The engine gives the split
  (``switch_lines``); they stay in ``note_lines`` for every other reader, and
  the window parses nothing.

WHY THESE ANCHORS. The surface text is checked against the geometry typed
here; the switch lines against the run of ``test_mass_switch_note_v1238``,
whose count that file already checks against a replay. Rule 7 in interface
form: a sound run's window shows neither new label.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _app():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _mass_switch_run(wide=True):
    """The notched model of v1238: with a wide cohesion some samples
    answer for the other sliding mass of the deterministic circle."""
    import test_mass_switch_note_v1238 as M
    res = M._global_minimum(M._wide() if wide else M._narrow())
    return M._model()[0], res


# ======================================================================
class TestTheSurfaceText:

    def test_a_circle(self):
        from ogr_gui.statistics_window import surface_text
        sd = {"type": "circle", "centre_x": 8.0, "centre_y": 34.0,
              "radius": 32.5576, "x_left": 2.0, "x_right": 30.0}
        assert surface_text(sd) == (
            "Sampled surface: circle of centre (8.00, 34.00) and radius "
            "32.56, from x = 2.00 to 30.00")

    def test_a_composite(self):
        from ogr_gui.statistics_window import surface_text
        sd = {"type": "composite", "centre_x": 55.0, "centre_y": 58.0,
              "radius": 34.0, "x_left": 30.0, "x_right": 80.0,
              "vertices": [[30.0, 40.0], [80.0, 40.0]]}
        assert surface_text(sd) == (
            "Sampled surface: composite surface clipped from the circle of "
            "centre (55.00, 58.00) and radius 34.00, from x = 30.00 to 80.00")

    def test_a_polyline(self):
        from ogr_gui.statistics_window import surface_text
        sd = {"type": "polyline", "polyline": {
            "vertices": [[2.0, 2.0], [16.0, 1.0], [30.0, 10.0]]}}
        assert surface_text(sd) == (
            "Sampled surface: polyline of 3 vertices, from x = 2.00 to 30.00")

    def test_a_weak_layer_names_its_layer_by_its_material(self):
        """The critical of the planar joint of v1121: along «Joint», on the
        polyline it was clipped from."""
        import test_weak_layer_statistics_v1251 as W
        from ogr_gui.statistics_window import surface_text
        p = W._planar()
        sd = W._det_surface(p, W._ORD, W._below_the_joint()).surface.to_dict()
        assert sd["type"] == "weak_layer"
        text = surface_text(sd, p)
        joint = [m.name for m in p.materials
                 if m.id == sd["weak_layers"][0]["material_id"]][0]
        assert text.startswith("Sampled surface: along the weak layer «%s»"
                               % joint), text
        assert "; its base: polyline of 3 vertices" in text, text

    def test_nothing_to_name_is_no_text(self):
        from ogr_gui.statistics_window import surface_text
        assert surface_text(None) == ""
        assert surface_text({"type": "unknown"}) == ""


class TestTheSummaryCarriesTheKey:

    def test_it_is_the_deterministic_surface_s_key(self):
        from ogr_core.statistics.probabilistic import _surface_key
        _p, res = _mass_switch_run(wide=False)
        (mres,) = res.by_method.values()
        key = mres.summary()["surface_key"]
        assert key and key == _surface_key(mres.surface)
        assert key.startswith(mres.surface["type"] + ":"), key


class TestTheWindow:

    def test_global_minimum_names_the_surface(self):
        _app()
        from ogr_gui.statistics_window import StatisticsWindow, surface_text
        p, res = _mass_switch_run(wide=False)
        (mres,) = res.by_method.values()
        w = StatisticsWindow(p, res, None, None)
        try:
            assert surface_text(mres.surface, p) in w.status.text()
        finally:
            w.deleteLater()

    def test_overall_slope_has_no_surface_line(self):
        import dataclasses
        _app()
        from ogr_core.statistics import ProbabilisticType
        from ogr_gui.statistics_window import StatisticsWindow
        p, res = _mass_switch_run(wide=False)
        os_res = dataclasses.replace(
            res, analysis_type=ProbabilisticType.OVERALL_SLOPE)
        w = StatisticsWindow(p, os_res, None, None)
        try:
            assert "Sampled surface" not in w.status.text()
        finally:
            w.deleteLater()

    def test_a_change_of_mass_has_its_own_title(self):
        _app()
        from ogr_gui.statistics_window import StatisticsWindow
        p, res = _mass_switch_run(wide=True)
        assert len(res.switch_lines) == 1, res.switch_lines
        line = res.switch_lines[0]
        assert line in res.note_lines          # every other reader keeps it
        w = StatisticsWindow(p, res, None, None)
        try:
            assert not w.lbl_switch_notes.isHidden()
            assert w.lbl_switch_notes.text() == (
                "Samples that answered for another mechanism:\n" + line)
            assert line not in w.lbl_run_notes.text()
        finally:
            w.deleteLater()

    def test_a_sweep_that_changes_mass_has_it_too(self):
        _app()
        import test_mass_switch_note_v1238 as M
        from ogr_core.statistics import run_sensitivity
        from ogr_gui.statistics_window import StatisticsWindow
        p, V = M._model()
        sens = run_sensitivity(p, {M._MID: M._deterministic()}, [M._wide()],
                               num_slices=V._SLICES)
        assert len(sens.switch_lines) == 1, sens.switch_lines
        assert sens.switch_lines[0] in sens.note_lines
        w = StatisticsWindow(p, None, sens, None)
        try:
            assert sens.switch_lines[0] in w.lbl_switch_notes.text()
            assert sens.switch_lines[0] not in w.lbl_run_notes.text()
        finally:
            w.deleteLater()

    def test_a_sound_run_shows_neither_label(self):
        _app()
        from ogr_gui.statistics_window import StatisticsWindow
        p, res = _mass_switch_run(wide=False)
        assert res.switch_lines == [] and res.note_lines == []
        w = StatisticsWindow(p, res, None, None)
        try:
            assert w.lbl_switch_notes.isHidden()
            assert w.lbl_run_notes.isHidden()
        finally:
            w.deleteLater()

    def test_the_title_is_translated(self):
        _app()
        from ogr_gui.i18n import current_language, set_language, tr
        before = current_language()
        try:
            set_language("es")
            assert tr("Samples that answered for another mechanism:") == (
                "Muestras que contestaron por otro mecanismo:")
            assert tr("Sampled surface: %s") == "Superficie muestreada: %s"
        finally:
            set_language(before)
