# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.435 (D413) -- Interpret's charts, their Statistics entries and the
random-variable plot, by the owner's decisions of 2026-11-09.

Invariants protected here:

* **Every informative chart opens non-modal** and stays on its window
  (``ogr_gui.xy_chart.keep_chart``): the histogram, the cumulative, the
  scatter, Show Values Along Surface, the free-body diagram, the Result Table
  and the main window's drawdown sweep were modal (``exec()``), against
  AGENTS.md. Each is checked visible and not modal, with an identity on its
  numbers: the histogram's bars count the valid surfaces, the scatter has a
  point for each, the table's factors are theirs, the free body names its
  slice. A chart the user closed is let go when another opens.
* **The random-variable plot** is non-modal, and its button is grey exactly
  when the core says the variable is not random, with THAT reason
  (``Distribution.not_random_reason``, the rule ``is_random`` reads): one
  modal box named one reason for three. «No distribution» is in the combo:
  without it, selecting a variable an agent switched off stored Normal and
  OK switched it back on (rule 7). The editor is freed after it closes.
* **The sensitivity charts draw the method Interpret shows** when the run
  swept it, else the run's first, and name it: they drew the first, unnamed.
  The tornado's bars are that method's ranking; the plot's curves its sweeps.
* **Under a design standard each deterministic chart names the over-design
  factor**, as the window's summary and its Surfaces table do
  (``reported_quantity``, ``column_caption``): axes, titles and marks, and the
  back analysis' target. Without one, the texts of 0.1.434 byte for byte.
* **Each Statistics entry is enabled by the result it draws** (sensitivity,
  probabilistic, or GM minima), grey with its reason otherwise, and the gates
  follow a statistics run computed with Interpret open: they were computed
  once, when the menus were built.
* **«(none)»** no longer reaches the screen, and the census rule that found it
  (a name carried into a field of a translated text) checks itself.

From the review of 0.1.435 (the owner's decisions of 2026-11-10):

* **The editor of random variables is destroyed when it closes, with its
  plots:** a lambda that named the dialog kept it alive from C++, and its
  non-modal plot stayed on screen after Cancel. Selecting a variable and OK
  store nothing: an agent's correlation of -0.8765 came back -0.876.
* **The back analysis names its target by the run's report**, as the rest of
  the window; the hover, the click, Surfaces Crossing Point, Pick GM, the
  cumulative's text fallback, the forms and Graph Query name the over-design
  factor too; each gate says its own reason, by the project's statistics
  settings, and a checked entry that goes grey is unchecked.
* **The drawdown sweep draws each method against its own levels**, and names
  the over-design factor under a standard; the Properties tables and the
  Geometry Cleanup report open non-modal; painting with a deleted material is
  refused and a click outside every region paints nothing and says so; a
  stretched support names its end in Spanish.

One Interpret per flavour (with and without a standard) and one main window
for the file; the grid of test_interpret_i1_v149 (no pool), no modal dialog.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager, ExitStack
from types import SimpleNamespace as NS

try:
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except Exception:  # pragma: no cover
    _HAS_QT = False


def _requires_qt(obj):
    if _HAS_QT:
        return obj
    return type(obj.__name__, (), {}) if isinstance(obj, type) else None


@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(before)


@contextmanager
def _swapped(owner, name, value):
    """``owner.name`` replaced for the block and put back exactly."""
    had = hasattr(owner, "__dict__") and name in owner.__dict__
    raw = owner.__dict__.get(name) if had else None
    setattr(owner, name, value)
    try:
        yield
    finally:
        if had:
            setattr(owner, name, raw)
        else:
            delattr(owner, name)


@contextmanager
def _no_modals():
    """A modal dialog or message box fails the test instead of waiting for
    ever without a screen (as test_fos_chart_v1308)."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")
    with ExitStack() as stack:
        stack.enter_context(_swapped(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swapped(QMessageBox, name,
                                         staticmethod(modal)))
        yield


def _texts_of_figure(widget):
    from PySide6.QtWidgets import QWidget
    out = []
    for w in [widget] + widget.findChildren(QWidget):
        for ax in getattr(getattr(w, "figure", None), "axes", None) or []:
            out += [ax.get_title(), ax.get_xlabel(), ax.get_ylabel()]
            out += [t.get_text() for t in ax.texts]
            legend = ax.get_legend()
            if legend is not None:
                out += [t.get_text() for t in legend.get_texts()]
    return [t for t in out if t]


def _shown(dlg):
    return dlg is not None and dlg.isVisible() and not dlg.isModal()


_RESULTS: list = []
_IW: dict = {}
_WINDOW: list = []
_KEPT: list = []


def _results():
    """The reference slope and a small grid search on it, once."""
    if not _RESULTS:
        from test_slide_validation_ej1 import _ej1_project
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        p = _ej1_project()
        res = {"bishop_simplified": GridSearch(
            method=BishopSimplified(), grid_x=(70, 100), grid_y=(60, 85),
            grid_nx=3, grid_ny=3, radius_increment=10, min_radius=15,
            num_slices=16, min_area=0.5).run(p)}
        _RESULTS.append((p, res))
    return _RESULTS[0]


def _report():
    """A design standard's report, applied (Eurocode 7, DA1 C1)."""
    from ogr_core.project.design_factors import apply_design_factors
    p, _res = _results()
    q = copy.deepcopy(p)
    q.settings.design_standard.enabled = True
    q.settings.design_standard.apply_preset("eurocode7_da1c1")
    _copy, report = apply_design_factors(q)
    assert report.applied
    return report


def _iw(factored=False):
    """Interpret on the reference slope, with or without a standard."""
    if factored not in _IW:
        from ogr_gui.interpret_window import InterpretWindow
        QApplication.instance() or QApplication([])
        p, res = _results()
        _IW[factored] = InterpretWindow(
            p, res, None, factor_report=_report() if factored else None)
    return _IW[factored]


def _window():
    if not _WINDOW:
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        w.project.is_dirty = False
        w.act_load_demo()
        w.project.is_dirty = False
        _WINDOW.append(w)
    return _WINDOW[0]


def _valid(iw):
    return [r for r in iw.search_result.evaluations if r.is_valid]


def _close(*dialogs):
    for d in dialogs:
        if d is not None:
            d.close()


# ======================================================================
@_requires_qt
class TestTheChartsAreNotModal:

    def test_the_population_charts(self):
        iw = _iw()
        valid = _valid(iw)
        with _no_modals():
            hist = iw._histogram()
            cum = iw._cumulative()
            scatter = iw._scatter()
        try:
            for dlg in (hist, cum, scatter):
                assert _shown(dlg) and dlg in iw._chart_windows, dlg
            bars = hist.figure.axes[0].patches
            assert round(sum(b.get_height() for b in bars)) == len(valid)
            points = scatter.ax().collections[0].get_offsets()
            assert len(points) == len(valid)
        finally:
            _close(hist, cum, scatter)

    def test_the_surface_charts(self):
        from PySide6.QtWidgets import QInputDialog, QTableWidget
        iw = _iw()
        valid = _valid(iw)
        with _no_modals(), _language("es"), _swapped(
                QInputDialog, "getInt",
                staticmethod(lambda *a, **k: (2, True))):
            iw._show_values_along()
            values = iw._chart_windows[-1]
            body = iw._free_body_diagram()
            table = iw._add_result_table()
        try:
            for dlg in (values, body, table):
                assert _shown(dlg) and dlg in iw._chart_windows, dlg
            assert type(values).__name__ == "MultiLineDialog"
            assert any(t.startswith("Dovela 2:")
                       for t in _texts_of_figure(body)), _texts_of_figure(body)
            tbl = table.findChildren(QTableWidget)[0]
            shown = sorted(tbl.item(r, 1).text() for r in range(tbl.rowCount()))
            assert shown == sorted("%.4f" % r.fos for r in valid)
        finally:
            _close(values, body, table)

    def test_the_drawdown_sweep_of_the_main_window(self):
        """Non-modal, and each method against ITS levels (the owner's
        decision in the review): one x was kept, the last method's, so a
        level one method lost put the other's factors where they were not
        computed. Under a standard the factor is named for what it is."""
        w = _window()
        # Bishop lost the level 7.5 and Spencer the level 5, which Spencer
        # replaces with the total drawdown (None): their x differ, and the
        # total plots at the lowest level of all, Bishop's 5
        result = NS(notes={},
                    worst=lambda: ("bishop_simplified", 5.0, 1.1),
                    by_method={
                        "bishop_simplified": NS(
                            valid=[(10.0, 1.5, None), (5.0, 1.1, None)],
                            unsafe_margin=lambda: None),
                        "spencer": NS(
                            valid=[(10.0, 1.55, None), (7.5, 1.35, None),
                                   (None, 1.2, None)],
                            unsafe_margin=lambda: None)})
        kept = (getattr(w, "last_drawdown_sweep", None),
                dict(getattr(w, "last_task_notes", {}) or {}))
        seen = {}
        try:
            for applied in (False, True):
                worker = NS(warnings=[], factor_report=NS(applied=applied))
                with _no_modals(), _language("es"), _swapped(
                        w, "sweep_worker", worker):
                    w._on_drawdown_sweep_done(result)
                    bar = w.statusBar().currentMessage()
                dlg = w._chart_windows[-1]
                try:
                    assert _shown(dlg) and type(dlg).__name__ == \
                        "MultiLineDialog"
                    lines = {ln.get_label(): (list(ln.get_xdata()),
                                              list(ln.get_ydata()))
                             for ln in dlg.ax().get_lines()}
                    seen[applied] = (dlg.windowTitle(), bar, lines)
                finally:
                    dlg.close()
        finally:
            w.last_drawdown_sweep, w.last_task_notes = kept
        lines = seen[False][2]
        assert lines == {"Bishop simplificado": ([10.0, 5.0], [1.5, 1.1]),
                         "Spencer": ([10.0, 7.5, 5.0], [1.55, 1.35, 1.2])},             lines
        assert seen[False][0] == ("Factor de seguridad frente al nivel de "
                                  "desembalse")
        assert "FS = 1.1000" in seen[False][1], seen[False][1]
        assert seen[True][0] == ("Factor de sobredimensionamiento frente al "
                                 "nivel de desembalse")
        assert "FSD = 1.1000" in seen[True][1], seen[True][1]

    def test_the_tables_that_only_show(self):
        """The Properties tables and the Geometry Cleanup report open
        non-modal, as the Result Table (the owner's decision)."""
        w = _window()
        before = w.command_stack.history()
        with _no_modals():
            table = w._properties_table("materials")
            report = w.act_geometry_cleanup()
        try:
            for dlg in (table, report):
                assert _shown(dlg) and dlg in w._chart_windows, dlg
        finally:
            _close(table, report)
            while w.command_stack.history()[0] != before[0] \
                    and w.command_stack.can_undo:
                w.command_stack.undo(w.project)
            w.project.is_dirty = False

    def test_a_closed_chart_is_let_go(self):
        iw = _iw()
        with _no_modals():
            first = iw._histogram()
            first.close()
            second = iw._histogram()
        try:
            assert second in iw._chart_windows
            assert first not in iw._chart_windows
        finally:
            _close(second)


# ======================================================================
def _variable(project, dist_type=None):
    from ogr_core.statistics import available_variables
    from ogr_core.statistics.distributions import DistributionType
    rv = next(v for v in available_variables(project) if v.param == "cohesion")
    d = rv.distribution
    d.dist_type = dist_type or DistributionType.NORMAL
    d.std_dev = max(abs(d.mean) * 0.1, 0.1)
    d.rel_min = d.rel_max = 2.0 * d.std_dev
    project.random_variables = [rv]
    return rv


@_requires_qt
class TestTheRandomVariablesPlot:

    def test_the_reason_is_the_rule_of_is_random(self):
        """The three conditions written out here, in the core's order."""
        from ogr_core.statistics.distributions import (Distribution,
                                                       DistributionType as T)
        for t in T:
            for std in (-1.0, 0.0, 1.0):
                for lo, hi in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)):
                    d = Distribution(dist_type=t, mean=10.0, std_dev=std,
                                     rel_min=lo, rel_max=hi)
                    want = ("none" if t is T.NONE
                            else "no_range" if lo == hi == 0.0
                            else "no_std_dev" if t in (T.NORMAL, T.LOGNORMAL)
                            and std <= 0 else "")
                    assert d.not_random_reason() == want, (t, std, lo, hi)
                    assert d.is_random == (not want)

    def test_the_button_says_why(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics.distributions import DistributionType
        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog)
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        with _language("es"):
            # nothing defined, so nothing selected
            empty = RandomVariablesDialog(p)
            _KEPT.append(empty)
            states = [(empty.btn_plot.isEnabled(), empty.btn_plot.statusTip())]
            rv = _variable(p)
            d = RandomVariablesDialog(p)        # opens on the first variable
            _KEPT.append(d)
            d.list_defined.setCurrentRow(0)
            stored = d.defined[rv.key].distribution
            states.append((d.btn_plot.isEnabled(), d.btn_plot.statusTip()))
            d.sp_std.setValue(0.0)
            states.append((d.btn_plot.isEnabled(), d.btn_plot.statusTip()))
            assert d.btn_plot.isEnabled() == stored.is_random
            d.sp_std.setValue(1.0)
            d.sp_rmin.setValue(0.0)
            d.sp_rmax.setValue(0.0)
            states.append((d.btn_plot.isEnabled(), d.btn_plot.statusTip()))
            assert d.btn_plot.isEnabled() == stored.is_random
            d.cbo_dist.setCurrentIndex(d.cbo_dist.findData(
                DistributionType.NONE))
            states.append((d.btn_plot.isEnabled(), d.btn_plot.toolTip()))
            # the last variable removed: only the row's change greys it
            d._remove()
            states.append((d.btn_plot.isEnabled(), d.btn_plot.statusTip()))
        assert states == [
            (False, "Selecciona antes una variable aleatoria."),
            (True, ""),
            (False, "Una distribución normal o lognormal necesita una "
                    "desviación típica mayor que cero."),
            (False, "El rango está vacío: introduce un mínimo relativo o un "
                    "máximo relativo."),
            (False, "Esta variable no tiene distribución: no es aleatoria."),
            (False, "Selecciona antes una variable aleatoria."),
        ], states

    def test_no_distribution_stays_no_distribution(self):
        """Rule 7: selecting a variable switched off and pressing OK leaves
        it off. The combo had no such entry, and stored Normal."""
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics.distributions import DistributionType
        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog)
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        _variable(p, DistributionType.NONE)
        d = RandomVariablesDialog(p)
        _KEPT.append(d)
        d.list_defined.setCurrentRow(0)
        assert d.cbo_dist.currentData() is DistributionType.NONE
        d._accept()
        assert p.random_variables[0].distribution.dist_type \
            is DistributionType.NONE

    def test_the_plot_is_not_modal(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics.distributions import DistributionType
        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog)
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        empty = RandomVariablesDialog(p)
        _KEPT.append(empty)
        _variable(p)
        d = RandomVariablesDialog(p)
        _KEPT.append(d)
        with _no_modals():
            assert empty._plot() is None             # nothing selected
            d.list_defined.setCurrentRow(0)
            dlg = d._plot()
            assert _shown(dlg) and dlg in d._chart_windows
            d.cbo_dist.setCurrentIndex(d.cbo_dist.findData(
                DistributionType.NONE))
            assert d._plot() is None
        dlg.close()

    def test_the_editor_is_freed_with_its_plots(self):
        """Destroyed, not only unparented (review of 0.1.435): a lambda that
        named the dialog kept it alive from C++, as a hidden top-level window
        with its project, and its plot stayed on screen after OK or Cancel,
        showing a distribution Cancel had thrown away."""
        import gc
        import weakref
        import shiboken6
        import ogr_gui.dialogs.random_variables_dialog as RVD
        w = _window()
        kept = list(getattr(w.project, "random_variables", None) or [])
        editors, plots, after = [], [], []

        def run(self, how):
            self.list_defined.setCurrentRow(0)
            plot = self._plot()
            plots.append(plot)
            editors.append(weakref.ref(self))
            if how == "ok":
                self._accept()
            else:
                self.reject()
            after.append(plot.isVisible())
            return how == "ok"
        before = {id(x) for x in QApplication.topLevelWidgets()
                  if isinstance(x, RVD.RandomVariablesDialog)}
        try:
            _variable(w.project)
            for how in ("cancel", "ok"):
                with _no_modals(), _swapped(
                        RVD.RandomVariablesDialog, "exec",
                        lambda self, how=how: run(self, how)):
                    w._edit_random_variables()
            gc.collect()
            QApplication.processEvents()
            assert after == [False, False], after
            assert [r() for r in editors] == [None, None]
            # none of them left as a hidden top-level window (the editors
            # other tests keep, parentless, were there before)
            assert {id(x) for x in QApplication.topLevelWidgets()
                    if isinstance(x, RVD.RandomVariablesDialog)} <= before
            assert not any(shiboken6.isValid(p) for p in plots)
            assert not w.findChildren(RVD.RandomVariablesDialog)
        finally:
            w.project.random_variables = kept
            w.project.is_dirty = False
            w._update_statistics_actions()

    def test_opening_and_ok_change_nothing(self):
        """Selecting a variable and OK store nothing (the owner's decision):
        the controls round what they show (3 decimals of correlation, 6 of
        standard deviation) and wrote it back, so an agent's -0.8765 came back
        -0.876 and a standard deviation of 4e-7 came back 0, the variable
        switched off. Each control stores its own field, and only its own."""
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics import available_variables
        from ogr_core.statistics.distributions import DistributionType
        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog)
        QApplication.instance() or QApplication([])
        p = build_demo_project()
        by = {v.param: v for v in available_variables(p)}
        c, phi = by["cohesion"], by["friction_angle"]
        for v, std in ((c, 1.23456789), (phi, 4e-7)):
            d = v.distribution
            d.dist_type = DistributionType.NORMAL
            d.std_dev = std
            d.rel_min, d.rel_max = 2.5, 3.25
        c.correlated_with, c.correlation = phi.key, -0.8765
        p.random_variables = [c, phi]

        def stored():
            return [(v.key, v.distribution.to_dict() if hasattr(
                v.distribution, "to_dict") else vars(v.distribution).copy(),
                v.correlated_with, v.correlation)
                for v in p.random_variables]
        before = stored()
        d = RandomVariablesDialog(p)
        _KEPT.append(d)
        for row in (1, 0, 1):
            d.list_defined.setCurrentRow(row)
        d._accept()
        assert stored() == before
        assert p.random_variables[1].distribution.is_random
        # a field changed stores that field, and leaves the others as stored
        d = RandomVariablesDialog(p)
        _KEPT.append(d)
        d.list_defined.setCurrentRow(0)
        d.sp_std.setValue(2.0)
        d._accept()
        cv = p.random_variables[0]
        assert cv.distribution.std_dev == 2.0
        assert cv.correlation == -0.8765 and cv.correlated_with == phi.key
        assert cv.distribution.rel_min == 2.5


# ======================================================================
def _sensitivity(methods):
    """A sensitivity run over ``methods``: two variables, each method with
    its own factors, so a bar says which method drew it."""
    from ogr_slip2d.sensitivity import SensitivityResult, VariableSensitivity
    VS = VariableSensitivity
    by = {}
    for i, mid in enumerate(methods, 1):
        by[mid] = {
            "k1": VS(key="k1", label="A", values=[1.0, 2.0],
                     fos=[1.0, 1.0 + 0.1 * i]),
            "k2": VS(key="k2", label="B", values=[1.0, 2.0],
                     fos=[1.0, 1.0 - 0.05 * i])}
    return SensitivityResult(by_method=by)


@_requires_qt
class TestTheActiveMethod:

    def test_the_tornado_and_the_plot_draw_the_active_method(self):
        iw = _iw()
        assert iw.active_algorithm() == "bishop_simplified"
        sens = _sensitivity(["spencer", "bishop_simplified"])
        with _no_modals(), _language("es"), _swapped(
                iw, "_stat_results", lambda: (None, sens)):
            tornado = iw._sensitivity_tornado()
            plot = iw._sensitivity_plot()
        try:
            ax = tornado.ax()
            bars = sorted(ax.patches, key=lambda b: b.get_y())
            ticks = [t.get_text() for t in ax.get_yticklabels()]
            got = {t: round(b.get_width(), 12) for t, b in zip(ticks, bars)}
            sweeps = sens.by_method["bishop_simplified"]
            want = {s.label: round(s.fos[-1] - s.fos[0], 12)
                    for s in sweeps.values()}
            assert got == want, (got, want)
            title = "Tornado de sensibilidad — Bishop simplificado"
            assert tornado.windowTitle() == title
            assert title in _texts_of_figure(tornado)
            assert plot.windowTitle() == "Sensibilidad — Bishop simplificado"
            curves = sorted(tuple(round(y, 12) for y in line.get_ydata())
                            for ax2 in _axes_of(plot)
                            for line in ax2.get_lines())
            assert curves == sorted(tuple(round(y, 12) for y in s.fos)
                                    for s in sweeps.values())
        finally:
            _close(tornado, plot)

    def test_without_the_active_method_the_first_named(self):
        iw = _iw()
        sens = _sensitivity(["spencer"])
        with _no_modals(), _language("es"), _swapped(
                iw, "_stat_results", lambda: (None, sens)):
            tornado = iw._sensitivity_tornado()
        try:
            assert tornado.windowTitle() == "Tornado de sensibilidad — Spencer"
        finally:
            _close(tornado)

    def test_the_status_bar_names_the_method_of_a_run_of_two(self):
        import ogr_gui.background as BG
        w = _window()
        said = []
        kept = {k: getattr(w, k, None) for k in (
            "last_statistics_notes", "last_statistics_variables",
            "last_statistics_factor_report", "_prob_result", "_sens_result")}
        try:
            for methods in (["spencer", "bishop_simplified"], ["spencer"]):
                out = NS(deterministic=True, factor_report=None, warnings=[],
                         probabilistic=None, sensitivity=_sensitivity(methods))
                with _language("es"), \
                        _swapped(BG, "run_task", lambda *a, **k: out), \
                        _swapped(w, "_show_statistics", lambda: None):
                    w._compute_statistics()
                    said.append(w.statusBar().currentMessage())
        finally:
            for k, v in kept.items():
                setattr(w, k, v)
            w._update_statistics_actions()
        assert said[0] == "la más influyente (Spencer): A", said
        assert said[1] == "la más influyente: A", said


def _axes_of(widget):
    from PySide6.QtWidgets import QWidget
    out = []
    for w in [widget] + widget.findChildren(QWidget):
        out += list(getattr(getattr(w, "figure", None), "axes", None) or [])
    return out


# ======================================================================
@_requires_qt
class TestTheFactorUnderAStandard:

    def _charts(self, iw, language):
        from PySide6.QtWidgets import QDialog, QInputDialog
        with _language(language):
            with _no_modals(), _swapped(
                    QInputDialog, "getInt",
                    staticmethod(lambda *a, **k: (2, True))):
                charts = {"hist": iw._histogram(), "cum": iw._cumulative(),
                          "scatter": iw._scatter(),
                          "body": iw._free_body_diagram(),
                          "table": iw._add_result_table()}
                iw._show_values_along()
                charts["values"] = iw._chart_windows[-1]
            forms = []

            def accept(dlg):
                forms.append(dlg.windowTitle())
                return QDialog.Accepted
            with _swapped(QDialog, "exec", accept):
                charts["along"] = iw._graph_sf_along_slope()
            self.forms = forms
        return charts

    def test_every_chart_names_the_over_design_factor(self):
        from ogr_gui.reported_quantity import column_caption, reported_quantity
        iw = _iw(factored=True)
        res = iw.search_result
        with _language("es"):
            caption = reported_quantity(res, iw.factor_report)[1]
            short = column_caption(res, iw.factor_report)
        charts = self._charts(iw, "es")
        try:
            assert caption == "Factor de sobredimensionamiento" and short == "FSD"
            hist, cum = charts["hist"], charts["cum"]
            assert hist.figure.axes[0].get_xlabel() == caption
            assert "FSD = 1.0" in _texts_of_figure(hist)
            assert hist.chk_mark_one.text() == "Marcar FSD = 1.0"
            assert hist.windowTitle() == ("Histograma — distribución del "
                                          "factor de sobredimensionamiento")
            assert cum.figure.axes[0].get_xlabel() == caption
            assert any(t.startswith("P(FSD<1) = ")
                       for t in _texts_of_figure(cum))
            assert cum.windowTitle() == ("Acumulada — función de distribución "
                                         "del FSD")
            sc = charts["scatter"].ax()
            assert sc.get_ylabel() == caption
            assert sc.get_title().startswith("FSD frente al radio — ")
            along = charts["along"]
            assert along.ax().get_ylabel() == caption
            assert along.windowTitle() == ("Factor de sobredimensionamiento a "
                                           "lo largo del talud")
            # and the form that asks for it
            assert self.forms == ["Factor de sobredimensionamiento a lo "
                                  "largo del talud"], self.forms
            assert "(FSD=" in charts["values"].windowTitle()
            assert any("FSD=" in t and t.startswith("Dovela 2:")
                       for t in _texts_of_figure(charts["body"]))
            from PySide6.QtWidgets import QTableWidget
            tbl = charts["table"].findChildren(QTableWidget)[0]
            assert tbl.horizontalHeaderItem(1).text() == short
            for dlg in charts.values():
                for t in _texts_of_figure(dlg) + [dlg.windowTitle()]:
                    assert "Factor de seguridad" not in t, t
            # the contour legend of the factor
            kept = iw.contours.field
            try:
                iw.contours.field = "fos"
                with _language("es"):
                    iw._refresh_legend()
                assert iw.legend._title == caption, iw.legend._title
            finally:
                iw.contours.field = kept
        finally:
            _close(*charts.values())

    def test_without_a_standard_the_texts_of_0434(self):
        iw = _iw()
        charts = self._charts(iw, "en")
        try:
            hist = charts["hist"]
            assert hist.figure.axes[0].get_xlabel() == "Factor of Safety"
            assert "FoS = 1.0" in _texts_of_figure(hist)
            assert hist.chk_mark_one.text() == "Mark FoS = 1.0"
            assert hist.windowTitle() == ("Histogram — Factor of Safety "
                                          "distribution")
            assert any(t.startswith("P(FoS<1) = ")
                       for t in _texts_of_figure(charts["cum"]))
            assert charts["cum"].windowTitle() == "Cumulative — FoS CDF"
            assert charts["scatter"].ax().get_title().startswith(
                "FoS vs Radius — ")
            assert charts["along"].ax().get_ylabel() == "Factor of safety"
            assert charts["along"].windowTitle() == ("Factor of Safety Along "
                                                     "Slope")
            assert self.forms == ["Factor of Safety Along Slope"], self.forms
            assert "(FoS=" in charts["values"].windowTitle()
            from PySide6.QtWidgets import QTableWidget
            tbl = charts["table"].findChildren(QTableWidget)[0]
            assert tbl.horizontalHeaderItem(1).text() == "FoS"
        finally:
            _close(*charts.values())

    def test_the_back_analysis_names_its_target(self):
        """With a standard the target is an over-design factor (the owner's
        decision), named by the RUN's report, as the rest of the window
        (review of 0.1.435): the force is read off the run's slices, so the
        project's standard of now does not say what the target is. Each run
        is asked with the project's standard the other way round.

        v0.1.440 (D419) -- the preparation changed on purpose, the
        assertions did not. The window without a standard was built first
        and the standard set on its project afterwards: that is a model
        changed since the run, which the back analysis now refuses before
        asking anything. So that window is built AFTER the standard is set
        (a hand-built window takes the model as it is), with the run's
        report still saying there was none -- which is what this reads."""
        from PySide6.QtWidgets import QInputDialog
        import ogr_slip2d.back_analysis as BA
        from ogr_gui.interpret_window import InterpretWindow
        settings = _iw().project.settings
        kept = copy.deepcopy(settings.design_standard)
        seen = {}
        for factored in (True, False):
            for envelope in (False, True):
                asked, said = [], []

                def get_double(_parent, _title, label, value, *a, **k):
                    asked.append(label)
                    # v0.1.441 (D418) -- the elevation, the second input,
                    # typed on the slope face (35; it runs from 25 to 50):
                    # at the prefilled default, 0, the force touches no
                    # mass, and the window says so instead of a force
                    return (35.0 if len(asked) == 2 else value), True
                unsettled = NS(notes={"envelope_not_settled": True})
                fresh = None
                try:
                    if factored:
                        iw = _iw(True)
                    else:                     # the project has one now
                        settings.design_standard.enabled = True
                        settings.design_standard.apply_preset(
                            "eurocode7_da1c1")
                        p, res = _results()
                        iw = fresh = InterpretWindow(p, res, None,
                                                     factor_report=None)
                    with ExitStack() as stack:
                        stack.enter_context(_language("es"))
                        stack.enter_context(_swapped(
                            QInputDialog, "getDouble",
                            staticmethod(get_double)))
                        stack.enter_context(_swapped(
                            iw, "_info", lambda m, *a, **k: said.append(m)))
                        if envelope:
                            stack.enter_context(_swapped(
                                BA, "required_force",
                                lambda *a, **k: unsettled))
                        iw._back_analysis_report()
                finally:
                    settings.design_standard = copy.deepcopy(kept)
                    if fresh is not None:
                        fresh.close()
                        fresh.deleteLater()
                seen[factored, envelope] = (asked[0],
                                            said[0].split("\n")[0])
        assert seen[True, False][0] == \
            "Factor de sobredimensionamiento objetivo:", seen
        assert seen[True, False][1].startswith(
            "Fuerza de soporte requerida para FSD = "), seen
        assert "con el factor de sobredimensionamiento objetivo" in \
            seen[True, True][1], seen
        assert seen[False, False][0] == "Factor de seguridad objetivo:", seen
        assert seen[False, False][1].startswith(
            "Fuerza de soporte requerida para FS = "), seen
        assert "con el factor de seguridad objetivo" in seen[False, True][1]

    def test_the_read_outs_and_the_queries(self):
        """The hover, the click, Surfaces Crossing Point (its form and its
        answer), Pick GM (by the source of its minima), the cumulative's text
        fallback and Graph Query of the factor: each says what the window's
        summary says (review of 0.1.435: none was read by a test)."""
        from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QLabel
        import ogr_gui.dialogs.chart_dialogs as CD
        got = {}
        for factored in (True, False):
            iw = _iw(factored)
            res = iw.search_result
            crit = res.critical
            sd = crit.surface.to_dict()
            cx, cy = sd["centre_x"], sd["centre_y"]
            kept = {k: getattr(iw, k, None) for k in (
                "_hover_grid_idx", "_selected_surface_id", "_selected_result")}
            queries = list(getattr(iw, "_query_points", None) or [])
            said = []
            try:
                with _language("es"), _no_modals(), _swapped(
                        iw, "_info", lambda m, *a, **k: said.append(m)):
                    iw._hover_grid_idx = None
                    iw._on_canvas_hover(cx, cy)
                    hover = iw.statusBar().currentMessage()
                    iw._on_canvas_click_default(cx, cy)
                    click = iw.statusBar().currentMessage()
                    # a point on the critical surface's base
                    s = crit.slices[len(crit.slices) // 2]
                    form = []

                    def through(dlg):
                        form.append(dlg.findChildren(QLabel)[0].text())
                        spins = dlg.findChildren(QDoubleSpinBox)
                        spins[0].setValue(s.base_x_left)
                        spins[1].setValue(s.base_y_left)
                        return QDialog.Accepted
                    with _swapped(QDialog, "exec", through):
                        iw._surfaces_through_point()
                    point = said[-1]
                    # Pick GM: a search's minima carry the window's factor
                    with _swapped(res, "minima", [crit]):
                        iw._pick_gm_surfaces()
                    pick = iw._pick_minima_dialog
                    from PySide6.QtWidgets import QListWidget
                    gm_search = pick.findChildren(QListWidget)[0].item(0).text()
                    pick.close()
                    # ... a probabilistic run's carry the statistics' (here
                    # without a standard, whatever the window's)
                    prob = NS(ok=True, reported=NS(global_minima=[
                        dict(sd, _fos=crit.fos)]))
                    with _swapped(iw, "_stat_results", lambda: (prob, None)):
                        iw._pick_gm_surfaces()
                    pick = iw._pick_minima_dialog
                    gm_prob = pick.findChildren(QListWidget)[0].item(0).text()
                    pick.close()

                    def no_chart(*a, **k):
                        raise ImportError("no matplotlib")
                    with _swapped(CD, "CumulativeDialog", no_chart):
                        iw._cumulative()
                    fallback = said[-1]
                    graph = iw._graph_query_data(
                        "fos", labels={"fos": "Factor de seguridad"})
                    graph_texts = (graph.windowTitle(),
                                   _axes_of(graph)[0].get_ylabel())
                    graph.close()
            finally:
                for k, v in kept.items():
                    setattr(iw, k, v)
                iw._query_points = queries
                iw._refresh_canvas_with_highlights()
            got[factored] = dict(hover=hover, click=click, form=form[0],
                                 point=point, gm_search=gm_search,
                                 gm_prob=gm_prob, fallback=fallback,
                                 graph=graph_texts)
        f, n = got[True], got[False]
        assert "FSD mínimo en este centro" in f["hover"], f["hover"]
        assert "FS mínimo en este centro" in n["hover"], n["hover"]
        assert " — FSD = " in f["click"] and " — FS = " in n["click"], got
        assert f["form"].endswith("la de menor factor de "
                                  "sobredimensionamiento."), f["form"]
        assert n["form"].endswith("la de menor factor de seguridad."), n
        assert "Menor factor de sobredimensionamiento entre ellas: FSD = " \
            in f["point"], f["point"]
        assert "Menor factor de seguridad entre ellas: FS = " in n["point"]
        assert f["gm_search"].endswith("FSD = %.3f" % _iw(True).search_result
                                       .critical.fos), f["gm_search"]
        assert n["gm_search"].endswith("FS = %.3f" % _iw(False).search_result
                                       .critical.fos), n["gm_search"]
        assert "|   FS = " in f["gm_prob"], f["gm_prob"]
        assert "FSD &lt; 1,0" in f["fallback"] and "P(FSD &lt; 1)" in \
            f["fallback"], f["fallback"]
        assert "FS &lt; 1" in n["fallback"], n["fallback"]
        assert f["graph"] == ("Factor de sobredimensionamiento",) * 2, f
        assert n["graph"] == ("Factor de seguridad",) * 2, n

    def test_the_supports_on_the_critical_surface(self):
        said = []
        for factored in (True, False):
            iw = _iw(factored)
            with _language("es"), _swapped(
                    iw, "_info", lambda m, *a, **k: said.append(m)):
                iw._support_force_analysis()
        assert said[0].startswith("Soportes en la superficie crítica (FSD = ")
        assert said[1].startswith("Soportes en la superficie crítica (FS = ")


# ======================================================================
_SENS_RUN = ("Requires a sensitivity analysis: run Statistics → Compute "
             "Statistics in the modeller.")
_SENS_ON = ("Requires a sensitivity analysis: switch it on in Project "
            "Settings > Statistics and run Statistics → Compute Statistics "
            "in the modeller.")
_PROB_RUN = ("Requires a probabilistic analysis: run Statistics → Compute "
             "Statistics in the modeller.")
_PROB_ON = ("Requires a probabilistic analysis: switch it on in Project "
            "Settings > Statistics and run Statistics → Compute Statistics "
            "in the modeller.")
_GM = ("Requires a probabilistic analysis, or a search that reports several "
       "minima (a multimodal search or an Overall Slope run).")


@_requires_qt
class TestTheGatesFollowTheResults:

    def test_each_entry_follows_the_result_it_draws(self):
        """At each step every entry is enabled exactly when its result is
        there, and grey with ITS reason otherwise -- the text, not only that
        there is one (review of 0.1.435). The reason sends the user where the
        missing analysis is switched on when it is off: Compute Statistics
        alone could not help then."""
        import ogr_gui.background as BG
        from ogr_gui.interpret_window import InterpretWindow
        w = _window()
        _p, res = _results()
        iw = InterpretWindow(w.project, res, w)
        w.interpret_windows.append(iw)
        prob = NS(ok=True, notes={}, note_lines=[], switch_lines=[],
                  reported=NS(probability_of_failure=0.1,
                              reliability_index=1.3))
        sens = _sensitivity(["bishop_simplified"])
        st = w.project.settings.statistics
        kept = {k: getattr(w, k, None) for k in (
            "last_statistics_notes", "last_statistics_variables",
            "last_statistics_factor_report", "_prob_result", "_sens_result")}
        kept_st = (st.probabilistic_analysis, st.sensitivity_analysis)
        entries = {"sens": (iw._act_sens_plot, iw._act_sens_tornado),
                   "prob": (iw._act_conv_plot, iw._act_export_stats,
                            iw._act_crit_prob),
                   "gm": (iw._act_show_gm, iw._act_pick_gm)}

        def state():
            return {k: [(a.isEnabled(), a.statusTip()) for a in acts]
                    for k, acts in entries.items()}
        steps = []
        try:
            st.probabilistic_analysis = st.sensitivity_analysis = False
            w._prob_result = w._sens_result = None
            w._update_statistics_actions()
            steps.append(state())
            st.probabilistic_analysis = st.sensitivity_analysis = True
            for p_res, s_res in ((prob, None), (None, sens)):
                out = NS(deterministic=True, factor_report=None, warnings=[],
                         probabilistic=p_res, sensitivity=s_res)
                with _swapped(BG, "run_task", lambda *a, **k: out), \
                        _swapped(w, "_show_statistics", lambda: None):
                    w._compute_statistics()
                steps.append(state())
            w._prob_result = w._sens_result = None
            w._update_statistics_actions()
            steps.append(state())
        finally:
            st.probabilistic_analysis, st.sensitivity_analysis = kept_st
            for k, v in kept.items():
                setattr(w, k, v)
            w.interpret_windows.remove(iw)
            iw.close()
            w._update_statistics_actions()

        def grey(reason, n):
            return [(False, reason)] * n
        on2, on3 = [(True, "")] * 2, [(True, "")] * 3
        assert steps[0] == {"sens": grey(_SENS_ON, 2), "prob": grey(_PROB_ON, 3),
                            "gm": grey(_GM, 2)}, steps[0]
        assert steps[1] == {"sens": grey(_SENS_RUN, 2), "prob": on3,
                            "gm": on2}, steps[1]
        assert steps[2] == {"sens": on2, "prob": grey(_PROB_RUN, 3),
                            "gm": grey(_GM, 2)}, steps[2]
        assert steps[3] == {"sens": grey(_SENS_RUN, 2),
                            "prob": grey(_PROB_RUN, 3),
                            "gm": grey(_GM, 2)}, steps[3]

    def test_a_search_with_minima_and_the_method_shown(self):
        """The GM entries follow the minima of the method on screen with no
        statistics at all: a change of method re-gates them."""
        from ogr_gui.interpret_window import InterpretWindow
        QApplication.instance() or QApplication([])
        _p, res = _results()
        plain = res["bishop_simplified"]
        multi = copy.copy(plain)
        multi.minima = [plain.critical]
        iw = InterpretWindow(_p, {"bishop_simplified": plain,
                                  "spencer": multi}, None)
        _KEPT.append(iw)
        seen = []
        try:
            for mid in ("bishop_simplified", "spencer", "bishop_simplified"):
                iw.cb_method.setCurrentIndex(iw.cb_method.findData(mid))
                seen.append([(a.isEnabled(), a.statusTip()) for a in (
                    iw._act_show_gm, iw._act_pick_gm)])
        finally:
            iw.close()
        off, on = [(False, _GM)] * 2, [(True, "")] * 2
        assert seen == [off, on, off], seen

    def test_a_checked_entry_that_goes_grey_is_unchecked(self):
        """As the line of thrust: Show GM stayed ticked over the minima of a
        result that was gone, and the only entry that clears them was grey."""
        from ogr_gui.interpret_window import InterpretWindow
        w = _window()
        _p, res = _results()
        iw = InterpretWindow(w.project, res, w)
        w.interpret_windows.append(iw)
        prob = NS(ok=True, notes={}, reported=NS(global_minima=[]))
        kept = (getattr(w, "_prob_result", None),
                getattr(w, "_sens_result", None))
        try:
            w._prob_result, w._sens_result = prob, None
            w._update_statistics_actions()
            for act in (iw._act_show_gm, iw._act_crit_prob):
                assert act.isEnabled()
                act.blockSignals(True)
                act.setChecked(True)
                act.blockSignals(False)
            w._prob_result = None
            w._update_statistics_actions()
            assert [(a.isEnabled(), a.isChecked()) for a in (
                iw._act_show_gm, iw._act_crit_prob)] == [(False, False)] * 2
            assert iw._show_minima is False
        finally:
            w._prob_result, w._sens_result = kept
            w.interpret_windows.remove(iw)
            iw.close()
            w._update_statistics_actions()

    def test_the_reasons_say_what_is_missing(self):
        iw = _iw()
        with _language("es"), _swapped(iw, "_stat_results",
                                       lambda: (None, None)):
            iw.refresh_statistics_gates()
            tips = {a.text(): a.statusTip() for a in (
                iw._act_sens_plot, iw._act_conv_plot, iw._act_show_gm)}
        try:
            assert tips[iw._act_sens_plot.text()].startswith(
                "Requiere un análisis de sensibilidad: ")
            assert tips[iw._act_conv_plot.text()].startswith(
                "Requiere un análisis probabilístico: ")
            assert tips[iw._act_show_gm.text()].startswith(
                "Requiere un análisis probabilístico, o una búsqueda que "
                "informe de varios mínimos")
        finally:
            iw.refresh_statistics_gates()


# ======================================================================
def _inside(project):
    """A point inside the first region of ``project``."""
    from shapely.geometry import Polygon
    region = project.resolve_regions()[0]
    pt = Polygon([(v.x, v.y) for v in region.polygon.vertices]
                 ).representative_point()
    return pt.x, pt.y


@_requires_qt
class TestPaintingAMaterial:
    """«(none)» left the screen with the owner's decision of the review: an
    id the Assign panel kept after its material was deleted is refused, and
    a click outside every region paints nothing and says so. Neither leaves a
    step to undo; a click inside, the control, paints and leaves one."""

    def test_refused_outside_and_painted(self):
        w = _window()
        kept = w._assign_active_material_id
        mat = w.project.materials[0]
        x, y = _inside(w.project)
        said, steps = {}, {}
        before = w.command_stack.history()
        assigned = [dict(a) for a in w.project.region_assignments]
        try:
            with _language("es"):
                for case, mid, pt in (("deleted", "no-such-material", (x, y)),
                                      ("outside", mat.id, (-1e4, -1e4)),
                                      ("inside", mat.id, (x, y))):
                    w._assign_active_material_id = mid
                    w._on_canvas_assign_click(*pt)
                    said[case] = w.ogr_status.currentMessage()
                    steps[case] = w.command_stack.history()[0]
                    if case != "inside":
                        assert [dict(a) for a in
                                w.project.region_assignments] == assigned
        finally:
            while w.command_stack.history()[0] != before[0] \
                    and w.command_stack.can_undo:
                w.command_stack.undo(w.project)
            w._assign_active_material_id = kept
            w.project.is_dirty = False
        assert said["deleted"] == ("El material elegido en el panel Asignar "
                                   "ya no existe: elige otro."), said
        assert said["outside"] == ("El clic cae fuera de toda región: no se "
                                   "ha pintado nada."), said
        assert said["inside"] == "Región pintada con «%s»." % mat.name, said
        assert steps["deleted"] == steps["outside"] == before[0]
        assert len(steps["inside"]) == len(before[0]) + 1


@_requires_qt
class TestStretchingASupport:
    """The census rule of this version, widened in its review, found «Soporte
    1 head estirado.»: one text per end, the owner's decision."""

    def test_each_end_by_its_name(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support.support import SupportInstance
        w = _window()
        s = SupportInstance(type_id="end_anchored", head=Vertex(30.0, 20.0),
                            tail=Vertex(36.0, 17.0))
        w.project.supports.append(s)
        said = []
        try:
            with _language("es"):
                w._on_stretch_support_picked(36.0, 17.0, 38.0, 16.0)
                said.append(w.ogr_status.currentMessage())
                w._on_stretch_support_picked(30.0, 20.0, 29.0, 21.0)
                said.append(w.ogr_status.currentMessage())
            with _language("en"):
                w._on_stretch_support_picked(29.0, 21.0, 30.0, 20.0)
                said.append(w.ogr_status.currentMessage())
        finally:
            for _ in range(3):
                w.command_stack.undo(w.project)
            if s in w.project.supports:
                w.project.supports.remove(s)
            w.project.supports[:] = [x for x in w.project.supports
                                     if x.id != s.id]
            w.project.is_dirty = False
        assert said == ["Soporte 1 estirado por la cola.",
                        "Soporte 1 estirado por la cabeza.",
                        "Support 1 head stretched."], said


class TestTheCensusRule:
    """The rule of test_gui_spanish_v1318 that found «(none)»: a name carried
    into a field of a translated text is read where it is set. Widened in the
    review of 0.1.435 (each way below was a hole it measured), and its
    controls: a nested function's names are its own, and a literal the
    function translates in place is not English on screen."""

    def test_it_checks_itself(self):
        from test_gui_spanish_v1318 import loose
        head = 'def f(self, m, x):\n'
        found = {
            "if-else": '    name = m.name if m else "(none)"\n'
                       '    self.s.showMessage(tr("A {0}.").format(name))\n',
            "%": '    x = "gone"\n'
                 '    self.s.showMessage(tr("A %s") % x)\n',
            "keyword": '    name = "gone"\n'
                       '    self.s.showMessage(tr("A {n}.").format(n=name))\n',
            "% tuple": '    name = "gone"\n'
                       '    self.s.showMessage(tr("A %s %d") % (name, 1))\n',
            "% dict": '    name = "gone"\n'
                      '    self.s.showMessage(tr("A %(n)s") % {"n": name})\n',
            "% a name holding a tuple":
                '    args = ("gone", 1)\n'
                '    self.s.showMessage(tr("A %s %d") % args)\n',
            "*args": '    args = ["gone"]\n'
                     '    self.s.showMessage(tr("A {0}").format(*args))\n',
            "every target": '    name = other = "gone"\n'
                            '    self.s.showMessage(tr("A {0}").format(other))\n',
            "the first assignment":
                '    name = "gone"\n'
                '    name = m.name\n'
                '    self.s.showMessage(tr("A {0}").format(name))\n',
            "the last assignment":
                '    name = m.name\n'
                '    name = "gone"\n'
                '    self.s.showMessage(tr("A {0}").format(name))\n',
            "a tuple target": '    a, name = 1, "gone"\n'
                              '    self.s.showMessage(tr("A {0}").format(name))\n',
            "an annotation": '    name: str = "gone"\n'
                             '    self.s.showMessage(tr("A {0}").format(name))\n',
            "+=": '    name = m.name\n'
                  '    name += " gone"\n'
                  '    self.s.showMessage(tr("A {0}").format(name))\n',
            "for over literals":
                '    for name in ("head", "tail"):\n'
                '        self.s.showMessage(tr("A {0}").format(name))\n',
            ":=": '    if (name := "gone"):\n'
                  '        self.s.showMessage(tr("A {0}").format(name))\n',
            "self.attr": '    self.name = "gone"\n'
                         '    self.s.showMessage(tr("A {0}").format(self.name))\n',
            "str(name)": '    name = "gone"\n'
                         '    self.s.showMessage(tr("A {0}").format(str(name)))\n',
            "name.strip()": '    name = "gone "\n'
                            '    self.s.showMessage(tr("A {0}").format(name.strip()))\n',
            "a second name": '    a = "gone"\n'
                             '    name = a\n'
                             '    self.s.showMessage(tr("A {0}").format(name))\n',
            "a template saved": '    msg = tr("A {0}")\n'
                                '    name = "gone"\n'
                                '    self.s.showMessage(msg.format(name))\n',
        }
        for why, body in found.items():
            assert loose(head + body), why
        clean = {
            "translated": '    name = m.name if m else tr("(none)")\n'
                          '    self.s.showMessage(tr("A {0}.").format(name))\n',
            "data": '    name = m.name\n'
                    '    self.s.showMessage(tr("A {0}.").format(name))\n',
            "nested": '    name = m.name\n'
                      '    def g():\n'
                      '        name = "internal-id"\n'
                      '        return name\n'
                      '    self.s.showMessage(tr("A {0}.").format(name))\n',
            "translated in place": '    name = "Untitled"\n'
                                   '    name = tr(name)\n'
                                   '    self.s.showMessage(tr("A {0}.").format(name))\n',
            "not a translated text": '    name = "gone"\n'
                                     '    path = "{0}.csv".format(name)\n',
        }
        for why, body in clean.items():
            assert not loose(head + body), why
