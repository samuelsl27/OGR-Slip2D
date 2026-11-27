# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.502 — Interpret's Contour Options dialog starts, fits and restores the
scale the window draws on a Ky or Newmark run.

Since v0.1.500 (D438) the factor field of a seismic run paints the run's
number, on a scale of its own (``ContourSettings.for_reported``), and the
window fits a Newmark displacement over its whole range (percentile 1.0):
its critical end is its top, which the 0.98 that keeps a deep-seated factor
from squashing the scale would cut. The dialog did not know the run's
quantity (reported by the OGR-GUI session, which read it against its twin
``ogr_ui.contours``; confirmed here before the fix). Measured with 0.1.501
on the demo slope with c = 12 kPa, a 5×5×6 grid, Bishop and a 0.3 g, 2 Hz
sinusoid for 4 s plus 2 s of calm, Newmark, one-way:

* the window drew 0 to 31.083 cm and the dialog proposed 0 to 17.862 cm on
  opening, on ticking «automatic range» again and on *Fit*: accepted with
  the box unticked, the critical surface fell outside the scale;
* *Restore Defaults* gave the factor's 0 to 6 in 24 Rainbow bands, not
  reversed, on a Ky run and on a Newmark one.

A third point of the report, that ticking the box set 24 intervals, did not
reproduce: the 24 is the *0 to 6* button's (``_range_0_to_6``), the factor's
preset. On a seismic run that button is now disabled, with its reason
(the interface guide's rule).

The invariants, against the window's own drawing (an identity: the dialog
proposes what the window draws), on the grid of ``test_newmark_upslope_
critical_v1499`` with 3 radius increments, which keeps the separation (the
window's maximum 31.083 cm, the 0.98 percentile 19.589 cm):

* on a Newmark run the four ways the dialog sets a range — opening, the
  box, *Fit*, *Restore Defaults* — give the window's maximum, the critical
  surface's displacement; *Restore Defaults* gives the run's scale (8 bands,
  Hot to cold, reversed);
* on a Ky run *Restore Defaults* gives the Ky's scale, not 0 to 6;
* the *0 to 6* button is disabled with its reason on both, and enabled,
  with its own tooltip, on a run of factors, where nothing else changes
  (*Restore Defaults* is 0 to 6 in 24 bands, the fit is the 0.98 one).

Cost: three runs of small grids (under half a second each) and three
Interpret windows offscreen, each closed after it is read.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_CASES: dict = {}


def _case(mode):
    """``(window contours, values, quantity, critical value)`` of a run:
    "newmark" (c = 12 kPa, the sinusoid), "ky" and "fos" (c = 20 kPa)."""
    if mode not in _CASES:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d.analysis_runner import run_analysis
        if mode == "newmark":
            from test_newmark_upslope_critical_v1499 import _project
            p = _project(False)
            p.settings.search.radius_increment = 3
        else:
            from test_interpret_seismic_centres_v1500 import _project
            p = _project(mode)
        out = run_analysis(p)
        w = InterpretWindow(p, out.results, None,
                            factor_report=out.factor_report)
        try:
            from ogr_gui.contours import ContourSettings
            from ogr_gui.reported_quantity import centre_value
            res = w.search_result
            kind = w._run_quantity()
            crit = (centre_value(p, res, res.critical, kind)
                    if kind != "fos" else res.critical.fos)
            _CASES[mode] = (ContourSettings.from_dict(w.contours.to_dict()),
                            w.current_field_values(), kind, crit)
        finally:
            w.close()
            w.deleteLater()
            app.processEvents()
    return _CASES[mode]


def _dialog(mode):
    from ogr_gui.dialogs.contour_options_dialog import ContourOptionsDialog
    import inspect
    contours, values, kind, _crit = _case(mode)
    # the window's call; a dialog that does not take the run's quantity (the
    # tree before 0.1.502) is asked without it, so that it fails by what it
    # proposes and not by its signature
    known = "quantity" in inspect.signature(ContourOptionsDialog).parameters
    return ContourOptionsDialog(contours, ["fos"], values, None,
                                **({"quantity": kind} if known else {}))


def _close(d):
    from PySide6.QtWidgets import QApplication
    d.close()
    d.deleteLater()
    QApplication.instance().processEvents()


class TestThePremise:

    def test_the_percentile_would_cut_the_critical_displacement(self):
        from ogr_gui.contours import ContourSettings
        contours, values, kind, crit = _case("newmark")
        assert kind == "newmark"
        assert abs(contours.vmax - crit) <= 1e-9 * max(1.0, crit)
        trimmed = ContourSettings()
        trimmed.fit_to(values)
        assert trimmed.vmax < 0.9 * crit, (trimmed.vmax, crit)


class TestANewmarkRun:

    def _max(self):
        return _case("newmark")[0].vmax

    def test_on_opening(self):
        d = _dialog("newmark")
        try:
            assert abs(d.sp_max.value() - self._max()) <= 1e-4
        finally:
            _close(d)

    def test_on_ticking_the_box_again(self):
        d = _dialog("newmark")
        try:
            d.chk_auto.setChecked(False)
            d.chk_auto.setChecked(True)
            assert abs(d.sp_max.value() - self._max()) <= 1e-4
        finally:
            _close(d)

    def test_fit(self):
        d = _dialog("newmark")
        try:
            d._range_fit()
            assert abs(d.sp_max.value() - self._max()) <= 1e-4
        finally:
            _close(d)

    def test_restore_defaults_is_the_runs_scale(self):
        d = _dialog("newmark")
        try:
            d.sp_int.setValue(17)
            d.chk_rev.setChecked(False)
            d._defaults()
            s = d._collect()
            assert (s.intervals, s.reverse, s.palette, s.auto_range) == (
                8, True, "Hot to cold", True)
            assert abs(s.vmax - self._max()) <= 1e-4
        finally:
            _close(d)


class TestAKyRun:

    def test_restore_defaults_is_the_kys_scale(self):
        d = _dialog("ky")
        try:
            d._defaults()
            s = d._collect()
            contours = _case("ky")[0]
            assert (s.intervals, s.reverse, s.palette, s.auto_range) == (
                8, False, "Hot to cold", True)
            assert abs(s.vmin - contours.vmin) <= 1e-4
            assert abs(s.vmax - contours.vmax) <= 1e-4
        finally:
            _close(d)


class TestTheZeroToSixButton:

    def test_disabled_with_its_reason_on_a_seismic_run(self):
        for mode in ("ky", "newmark"):
            d = _dialog(mode)
            try:
                assert not d.btn_0to6.isEnabled(), mode
                assert "Restore Defaults" in d.btn_0to6.toolTip(), mode
            finally:
                _close(d)

    def test_a_run_of_factors_is_what_it_was(self):
        from ogr_gui.contours import ContourSettings
        d = _dialog("fos")
        try:
            assert d.btn_0to6.isEnabled()
            assert d.btn_0to6.toolTip().startswith(
                "Restore the default factor-of-safety range")
            values = _case("fos")[1]
            d._range_fit()
            probe = ContourSettings()
            probe.fit_to(values)
            assert abs(d.sp_max.value() - probe.vmax) <= 1e-4
            d._defaults()
            s = d._collect()
            assert (s.vmin, s.vmax, s.intervals, s.palette, s.reverse) == (
                0.0, 6.0, 24, "Rainbow (24 bands)", False)
        finally:
            _close(d)
