# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.369 (D343, D345) — the window names a method by its name and a force
with its unit, and the *Surfaces* tables head their value column with what
it holds: FoS, an over-design factor (FSD) with a design standard, Ky on a
search for the critical seismic coefficient.

The findings (the fifth interface test, 0.1.355):

* H5 — the back analysis's status bar said "Retroanálisis
  (bishop_simplified): fuerza necesaria 101.1 …": the template received
  ``values["method_id"]`` as it was, and the forces had no unit;
* H3 — the legend of *Factor of safety vs time* said "bishop_simplified"
  and "janbu_simplified": ``fos_history`` labels each series by its
  identifier, which the API reads, and both windows handed it to the chart
  unchanged. The drawdown sweep (its status bar and its chart) and the
  method list of Optimize Surfaces did the same (the family D315 closed
  elsewhere);
* H9 — with the design standard on, the Interpret *Surfaces* table headed
  "FS" a column of over-design factors (the summary says "Factor de
  sobredimensionamiento", the PDF "FSD"). And on a Ky search, the table
  lists the surfaces BY Ky but printed their factors under "FoS".

The owner's decisions (2026-10-25): on a Ky search the column heads "Ky"
and holds each surface's Ky, in the main window's results panel too; the
force is converted to the project's units through the quantity the unit
system names "force per unit length".

What these tests protect, through the real windows, in Spanish and English:

* the back analysis status bar names the method and gives kN/m (and the
  imperial label in an imperial project);
* the series of both FoS-vs-time charts carry the method's name;
* the heading of both *Surfaces* tables: "FS" without a standard, "FSD" with
  one (values unchanged), "Ky" with the Ky values on a Ky search.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MISSING = object()


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextmanager
def _lang(code):
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(before)


@contextmanager
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


def _window():
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    w.act_load_demo()
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


# ======================================================================
class TestTheBackAnalysisBar:

    def _bar(self, w):
        from PySide6.QtWidgets import QDialog
        with _swap(QDialog, "exec",
                   lambda self: QDialog.DialogCode.Accepted), \
                _swap(w, "_info", lambda *a: None):
            w._back_analysis()
        return w.statusBar().currentMessage()

    def test_spanish(self):
        with _lang("es"):
            w = _window()
            try:
                bar = self._bar(w)
            finally:
                _done(w)
        assert bar.startswith("Retroanálisis (Bishop simplificado): "
                              "fuerza necesaria "), bar
        assert "_" not in bar.split("(")[1].split(")")[0], bar
        assert bar.count("kN/m") == 3, bar

    def test_english_and_imperial_units(self):
        with _lang("en"):
            w = _window()
            try:
                w.project.settings.units.system_id = "imperial_psf"
                bar = self._bar(w)
            finally:
                _done(w)
        from ogr_gui.labels import method_name
        with _lang("en"):
            name = method_name("bishop_simplified")
        assert bar.startswith("Back analysis (%s): " % name), bar
        assert "_" not in name
        assert "kN/m" not in bar and bar.count("lbs/ft") == 3, bar


# ======================================================================
class TestTheFosVsTimeLegend:

    def test_both_windows_name_the_methods(self):
        import types

        import test_fos_chart_v1308 as fc
        import ogr_gui.xy_chart as xy
        from ogr_gui.interpret_window import InterpretWindow
        seen = []

        def record(parent, title, series, *a, **k):
            seen.append([s[0] for s in series])
            return object()
        p, w = fc._drawdown(calc_sf=True)
        iw = None
        try:
            with _lang("es"), _swap(xy, "show_xy_chart", record), \
                    fc._no_modals():
                iw = fc._interpret(p, w)
                iw._plot_fos_history()
                stand_in = types.SimpleNamespace(
                    project=p, _info=lambda *a: None)
                stand_in._plot_xy = types.MethodType(
                    InterpretWindow._plot_xy, stand_in)
                InterpretWindow._graph_sf_with_time(stand_in)
        finally:
            if iw is not None:
                iw.close()
            p.is_dirty = False
        assert len(seen) == 2 and seen[0] == seen[1], seen
        assert seen[0] and all("_" not in label for label in seen[0]), seen
        assert "Bishop simplificado" in seen[0], seen


# ======================================================================
def _demo_result(standard=None):
    from ogr_core.project.demo import build_demo_project
    from ogr_slip2d.analysis_runner import run_analysis
    p = build_demo_project()
    if standard:
        p.settings.design_standard.enabled = True
        p.settings.design_standard.apply_preset(standard)
    out = run_analysis(p, ["bishop_simplified"])
    return p, out.results["bishop_simplified"], out.factor_report


def _heading(table):
    return table.horizontalHeaderItem(1).text()


def _both_tables(p, result, report):
    """(heading, first value) of the Interpret *Surfaces* table and of the
    main window's results panel."""
    from ogr_gui.interpret_window import _ResultsTableDock
    from ogr_gui.widgets.results_dock import ResultsDock
    _app()
    a = _ResultsTableDock()
    b = ResultsDock()
    try:
        a.show_result(result, report)
        b.show_result(result, report)
        return ((_heading(a.table), a.table.item(0, 1).text()),
                (_heading(b.table), b.table.item(0, 1).text()))
    finally:
        a.close()
        b.close()


class TestTheSurfacesHeading:

    def test_without_a_standard(self):
        p, r, rep = _demo_result()
        with _lang("es"):
            got = _both_tables(p, r, rep)
        want = "%.4f" % r.top_n(1)[0].fos
        assert got == (("FS", want), ("FS", want)), got
        with _lang("en"):
            got = _both_tables(p, r, rep)
        assert got == (("FoS", want), ("FoS", want)), got

    def test_with_the_design_standard(self):
        p, r, rep = _demo_result("eurocode7_da1c1")
        assert getattr(rep, "applied", False), "the standard did not apply"
        want = "%.4f" % r.top_n(1)[0].fos     # the value is unchanged
        with _lang("es"):
            got = _both_tables(p, r, rep)
        assert got == (("FSD", want), ("FSD", want)), got
        with _lang("en"):
            got = _both_tables(p, r, rep)
        assert got == (("ODF", want), ("ODF", want)), got

    def test_on_a_ky_search(self):
        """A stand-in result with the Ky objective: the column heads Ky and
        holds each surface's Ky, in the order the search lists them."""
        from types import SimpleNamespace as NS
        rows = [NS(fos=1.05, details={"ky": 0.081},
                   surface=NS(to_dict=lambda: {"centre_x": 1.0,
                                               "centre_y": 2.0,
                                               "radius": 3.0}),
                   method_id="bishop_simplified"),
                NS(fos=0.98, details={"ky": 0.094},
                   surface=NS(to_dict=lambda: {"centre_x": 1.0,
                                               "centre_y": 2.0,
                                               "radius": 3.0}),
                   method_id="bishop_simplified")]
        result = NS(objective="ky", critical=rows[0], evaluations=rows,
                    method_id="bishop_simplified", valid_count=2,
                    invalid_count=0, analysed_count=2,
                    top_n=lambda n: rows[:n])
        with _lang("es"):
            got = _both_tables(None, result, None)
        assert got == (("Ky", "0.0810"), ("Ky", "0.0810")), got
