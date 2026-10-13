# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.308 (D311) — "FoS vs time…" of *Interpret Groundwater* is not modal,
and both Interpret windows plot one series.

The defect, found while planning D294/D295: the button opened its chart in a
dialog of its own with ``exec()`` — modal, so the chart could not be held
open next to the model, and without a screen it blocks for ever — and said
"no factor" with a modal box in English. The same chart existed in
*Interpret* (``_graph_sf_with_time``), non-modal and translated, and each
window built the series its own way from the stages' ``notes["fos"]``.

What these tests protect:

* ``fos_history`` gives one series per method, from the stages that have a
  factor (and the initial state's, at t = 0, when it has one, which D312
  will compute);
* the button opens a non-modal window, kept by the window so Qt does not
  collect it, and never calls ``exec()`` (replaced here by one that fails);
* with no factor it says so on the status bar, not in a modal box;
* both windows hand the chart the series of ``fos_history``.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


@contextlib.contextmanager
def _no_modals():
    """A modal dialog or message box fails the test instead of waiting for
    ever without a screen."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


def _result(time, fos=None, initial=False):
    from ogr_fem2d.solvers import SeepageResult
    r = SeepageResult()
    r.notes["time"] = time
    if fos:
        r.notes["fos"] = dict(fos)
    if initial:
        r.notes["initial_state"] = True
    return r


class TestTheSeries:
    def test_one_series_per_method_from_the_stages_with_a_factor(self):
        from ogr_slip2d.transient_stability import fos_history
        stages = [_result(10.0, {"bishop_simplified": 1.4, "spencer": 1.5}),
                  _result(20.0),
                  _result(30.0, {"bishop_simplified": 1.2})]
        assert fos_history(stages) == [
            ("bishop_simplified", [10.0, 30.0], [1.4, 1.2]),
            ("spencer", [10.0], [1.5])]
        assert fos_history([_result(5.0)]) == []

    def test_the_initial_state_goes_first_at_t_zero(self):
        from ogr_slip2d.transient_stability import fos_history
        start = _result(0.0, {"bishop_simplified": 1.7}, initial=True)
        stages = [_result(10.0, {"bishop_simplified": 1.4})]
        assert fos_history(stages, start) == [
            ("bishop_simplified", [0.0, 10.0], [1.7, 1.4])]
        # an initial state without a factor adds nothing
        assert fos_history(stages, _result(0.0)) == fos_history(stages)


def _drawdown(calc_sf):
    from test_transient_v130 import TestStageFactorsOfSafety
    QApplication.instance() or QApplication([])
    return TestStageFactorsOfSafety()._drawdown(times=(1e4, 1e6),
                                                calc_sf=calc_sf)


def _interpret(p, w):
    import matplotlib
    matplotlib.use("Agg")
    from ogr_gui.interpret_groundwater_window import (
        InterpretGroundwaterWindow)
    return InterpretGroundwaterWindow(p, p.seepage_result, w._gw_solver,
                                      None)


class TestTheGroundwaterWindow:
    def test_the_chart_is_not_modal(self):
        p, w = _drawdown(calc_sf=True)
        iw = None
        try:
            iw = _interpret(p, w)
            with _no_modals():
                dlg = iw._plot_fos_history()
            assert dlg is not None
            assert dlg.isVisible() and not dlg.isModal()
            assert dlg in iw._chart_windows
            dlg.close()
        finally:
            if iw is not None:
                iw.close()
            p.is_dirty = False
            w.close()

    def test_no_factor_is_said_on_the_status_bar(self):
        from ogr_gui.i18n import current_language, set_language
        p, w = _drawdown(calc_sf=False)
        iw = None
        before = current_language()
        try:
            iw = _interpret(p, w)
            with _no_modals():
                assert iw._plot_fos_history() is None
            assert "No stage has a computed factor" in \
                iw.statusBar().currentMessage()
            set_language("es")
            with _no_modals():
                iw._plot_fos_history()
            assert "Ninguna etapa" in iw.statusBar().currentMessage()
        finally:
            set_language(before)
            if iw is not None:
                iw.close()
            p.is_dirty = False
            w.close()


class TestBothWindowsPlotOneSeries:
    def test_the_series_handed_to_the_chart(self):
        """Both windows go through ``fos_history`` and ``show_xy_chart``."""
        import types

        import ogr_gui.xy_chart as xy
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d.transient_stability import fos_history
        p, w = _drawdown(calc_sf=True)
        iw = None
        seen = []

        def record(parent, title, series, *a, **k):
            seen.append(series)
            return object()

        try:
            expected = fos_history(p.transient_results,
                                   p.transient_initial_result)
            assert expected and len(expected[0][1]) == 2
            with _swap(xy, "show_xy_chart", record), _no_modals():
                iw = _interpret(p, w)
                iw._plot_fos_history()
                # Interpret's own entry, on a stand-in that has only what
                # it reads: the project and the shared chart of _plot_xy
                stand_in = types.SimpleNamespace(
                    project=p, _info=lambda *a: None)
                stand_in._plot_xy = types.MethodType(
                    InterpretWindow._plot_xy, stand_in)
                InterpretWindow._graph_sf_with_time(stand_in)
            assert seen == [expected, expected]
        finally:
            if iw is not None:
                iw.close()
            p.is_dirty = False
            w.close()
