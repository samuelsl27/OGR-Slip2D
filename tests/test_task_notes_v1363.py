# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.363 (D340) — the warnings of the calculations that are not Compute
reach *Analysis Notes*, each under its own calculation, in the reader's
language.

The finding (the fifth interface test, 0.1.355, §6): four calculations
returned their warnings to the window and the window threw them away —
``res, _report, _warnings = run_configured_back_analysis(...)``, the
optimisation's ``_w``, the drawdown sweep's worker, and the transient's
per-stage warnings, which nothing read at all (the outcome-level ones went to
the status bar, each replaced by the next and the last by the window's own
line). The back analysis also has two notes of its own, surfaces left out as
composite and envelopes that did not settle, and only ``notes["error"]`` was
read.

What these tests protect, through the real window and the real calculations:

* a warning of each of the four reaches the panel, under the calculation's
  name, in Spanish (``model.slope_limits_one_side``: a second set of Slope
  Limits with one side only, which every one of them reports and none of
  them acts on);
* the transient's stage warnings go under their stage, and the initial
  state's under it;
* the back analysis's own two notes reach it too;
* the status bar line of each calculation says that there are notes and
  where;
* a run with no warnings leaves the panel exactly as it was (rule 7 in
  interface form: the new sections are not there when there is nothing in
  them).
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_CODE = "model.slope_limits_one_side"
_HINT_ES = " — Análisis > Notas del análisis]"


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


_MISSING = object()


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


def _window(project=None):
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    if project is None:
        w.act_load_demo()
    else:
        w._attach_project(project)
    return w


def _done(w):
    panel = getattr(w, "_analysis_notes_panel", None)
    if panel is not None:
        panel.close()
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


def _one_side(project):
    """The note every calculation reports and none acts on."""
    project.settings.search.slope_limit_left_2 = 5.0
    project.settings.search.slope_limit_right_2 = None


def _expected_es(project):
    """The note's line as the panel must say it, in Spanish."""
    from ogr_gui.core_messages import note_line
    from ogr_slip2d.analysis_runner import settings_warnings
    notes = [n for n in settings_warnings(project, ["bishop_simplified"])
             if getattr(n, "code", "") == _CODE]
    assert len(notes) == 1, notes
    line = note_line(notes[0])
    assert line != str(notes[0]), "the note has no Spanish to test with"
    return line


def _section(w, title):
    """The top-level item of the notes panel named ``title``."""
    w.act_analysis_notes()
    tree = w._analysis_notes_panel.tree
    for i in range(tree.topLevelItemCount()):
        top = tree.topLevelItem(i)
        if top.text(0).startswith(title + " ("):
            return top
    return None


def _texts(item) -> list:
    out = []
    for i in range(item.childCount()):
        child = item.child(i)
        out.append(child.text(0))
        out += _texts(child)
    return out


def _tops(w) -> list:
    w.act_analysis_notes()
    tree = w._analysis_notes_panel.tree
    return [tree.topLevelItem(i).text(0)
            for i in range(tree.topLevelItemCount())]


# ======================================================================
class TestBackAnalysis:

    def _run(self, w):
        from PySide6.QtWidgets import QDialog
        with _swap(QDialog, "exec",
                   lambda self: QDialog.DialogCode.Accepted), \
                _swap(w, "_info", lambda *a: None):
            w._back_analysis()

    def test_its_warning_reaches_the_panel(self):
        with _spanish():
            w = _window()
            try:
                _one_side(w.project)
                expected = _expected_es(w.project)
                self._run(w)
                assert w._back_analysis_result.critical is not None
                top = _section(w, "Retroanálisis de la fuerza de soporte")
                assert top is not None, _tops(w)
                assert expected in _texts(top), _texts(top)
                bar = w.statusBar().currentMessage()
                assert bar.endswith("[1 nota(s)" + _HINT_ES), bar
            finally:
                _done(w)

    def test_its_own_two_notes_reach_the_panel(self):
        """``composite_skipped`` and ``envelope_not_settled``: the run is
        faked, because what is under test is that the window reads them;
        the driver that writes them is tested with the driver."""
        import ogr_slip2d.analysis_runner as runner
        from ogr_gui.core_messages import note_line
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.back_analysis import (BackAnalysisResult,
                                              BackAnalysisSurfaceResult)
        own = [RM.run_note(RM.BACK_COMPOSITE_LEFT_OUT, n=2),
               RM.run_note(RM.BACK_ENVELOPE_LEFT_OUT, n=3)]
        res = BackAnalysisResult(
            method_id="bishop_simplified", surfaces_analysed=5,
            critical=BackAnalysisSurfaceResult(
                active_force=10.0, passive_force=12.0, unsupported_fos=1.1),
            notes={"composite_skipped": own[0],
                   "envelope_not_settled": own[1]})
        with _spanish():
            w = _window()
            try:
                with _swap(runner, "run_configured_back_analysis",
                           lambda project, **kw: (res, None, [])):
                    self._run(w)
                top = _section(w, "Retroanálisis de la fuerza de soporte")
                assert top is not None, _tops(w)
                texts = _texts(top)
                for n in own:
                    assert note_line(n) in texts, texts
                    assert note_line(n) != str(n)
                bar = w.statusBar().currentMessage()
                assert bar.endswith("[2 nota(s)" + _HINT_ES), bar
            finally:
                _done(w)

    def test_without_warnings_the_panel_is_as_it_was(self):
        with _spanish():
            w = _window()
            try:
                self._run(w)
                assert w._back_analysis_result.critical is not None
                assert "back_analysis" not in w.last_task_notes
                assert _tops(w) == []
                head = w._analysis_notes_panel.lbl_head.text()
                assert head == "El último análisis no ha generado ninguna nota."
                assert "nota(s)" not in w.statusBar().currentMessage()
            finally:
                _done(w)


# ======================================================================
class TestOptimisation:

    def test_its_warning_reaches_the_panel(self):
        import test_optimize_wiring_v1104 as ow
        from PySide6.QtWidgets import QInputDialog

        from ogr_slip2d.analysis_runner import build_search
        p = ow._slope()
        sr = build_search(p, "bishop_simplified").run(p)
        assert sr.critical is not None
        _one_side(p)
        with _spanish():
            expected = _expected_es(p)
            w = _window(p)
            try:
                w.last_search_results = {"bishop_simplified": sr}
                w.last_search_result = sr
                with _swap(QInputDialog, "getInt", staticmethod(
                        lambda *a, **k: (ow._MAX_ITERATIONS, True))), \
                        _swap(w, "_info", lambda *a: None):
                    w._optimize_surfaces()
                top = _section(w, "Optimizar superficies")
                assert top is not None, _tops(w)
                assert expected in _texts(top), _texts(top)
                bar = w.statusBar().currentMessage()
                assert _HINT_ES in bar, bar
            finally:
                _done(w)


# ======================================================================
class TestDrawdownSweep:

    def test_its_warning_reaches_the_panel(self):
        import test_drawdown_sweep_v170 as dd
        import test_groundwater_ops_v1200 as go

        import ogr_gui.dialogs.chart_dialogs as charts
        from ogr_api import call
        from ogr_gui.main_window import _DrawdownSweepWorker
        ws = go._ws()
        pid = ws.add(dd._homogeneous()).id
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], surface_type="circular",
             search_method="grid", num_slices=18,
             grid={"x_min": 60, "x_max": 240, "y_min": 160, "y_max": 420,
                   "nx": 3, "ny": 4},
             radius_increment=6, failure_direction="right_to_left")
        p = ws.get(pid).project
        _one_side(p)
        with _spanish():
            expected = _expected_es(p)
            w = _window(p)
            try:
                w.sweep_worker = _DrawdownSweepWorker(
                    p, ["bishop_simplified"], 2, True)
                errors = []
                w.sweep_worker.failed.connect(errors.append)
                w.sweep_worker.run()
                assert not errors, errors
                with _swap(charts.MultiLineDialog, "exec", lambda self: 0):
                    w._on_drawdown_sweep_done(w.sweep_worker.result)
                top = _section(w, "Barrido de niveles de desembalse")
                assert top is not None, _tops(w)
                assert expected in _texts(top), _texts(top)
                bar = w.statusBar().currentMessage()
                assert bar.endswith("[1 nota(s)" + _HINT_ES), bar
            finally:
                _done(w)


# ======================================================================
class TestTransient:

    def test_the_stage_warnings_go_under_their_stage(self):
        import test_initial_factor_v1309 as tf
        p, _full = tf._drawdown()
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        _one_side(p)
        with _spanish():
            expected = _expected_es(p)
            w = _window(p)
            try:
                w._compute_groundwater()
                assert p.transient_results, "the transient did not run"
                top = _section(w, "Agua subterránea transitoria")
                assert top is not None, _tops(w)
                subs = {top.child(i).text(0).rsplit(" (", 1)[0]:
                        _texts(top.child(i)) for i in range(top.childCount())}
                # the initial state and the one stage, each with its notes
                # (this model also says its failure direction, a note
                # nobody had read on a transient either)
                assert sorted(subs) == ["0: t = 0 (estado inicial)",
                                        "Etapa 1: t = 10000"], subs
                for sub, texts in subs.items():
                    assert expected in texts, (sub, texts)
                n = sum(len(t) for t in subs.values())
                bar = w.statusBar().currentMessage()
                assert bar.endswith("[%d nota(s)" % n + _HINT_ES), bar
            finally:
                _done(w)

    def test_a_steady_field_takes_the_transient_notes_away(self):
        w = _window()
        try:
            w.last_task_notes["transient"] = [(None, ["old"])]
            w._set_task_notes("transient", [])
            assert "transient" not in w.last_task_notes
            assert w._task_note_sections() == []
        finally:
            _done(w)


# ======================================================================
class TestThePanelWithoutSections:

    def test_compute_notes_alone_build_the_same_tree(self):
        """Rule 7 in interface form: with no other calculation's notes the
        panel is the panel of before, item for item."""
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        _app()
        notes = ["Some model note.", "bishop_simplified: a method note."]
        old = AnalysisNotesPanel(notes)
        new = AnalysisNotesPanel(notes, None, [("Back analysis", []),
                                               ("Transient", [(None, [])])])
        try:
            def tree(panel):
                t = panel.tree
                return [(t.topLevelItem(i).text(0), _texts(t.topLevelItem(i)))
                        for i in range(t.topLevelItemCount())]
            assert tree(new) == tree(old)
            assert new.lbl_head.text() == old.lbl_head.text()
        finally:
            old.close()
            new.close()

    def test_copy_all_carries_the_sections(self):
        from PySide6.QtWidgets import QApplication

        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        _app()
        panel = AnalysisNotesPanel(["A model note."], None,
                                   [("Transient", [("Stage 1", ["x."])])])
        try:
            panel._copy_all()
            text = QApplication.clipboard().text()
            assert text.splitlines() == ["A model note.",
                                         "Transient, Stage 1: x."], text
        finally:
            panel.close()
