# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.418 (D355) — nine loose details of the fifth and sixth GUI tests (H9,
H14 of ``INFORME_prueba_GUI_0.1.355.md``; H13 of ``…0.1.357.md``), each
closed on its own.

The invariants, one class each:

1. **Two notes end as sentences.** The design standard's note ends in a
   full stop, in both languages (and its twins of the command line and of
   the statistics); «before quoting it» is «antes de darlo por bueno» in
   the five Spanish notes that said «antes de darlo». The English of the
   notes, frozen by D335's tests, is otherwise untouched.
2. **«corrida» is «cálculo»** (the owner's term, 2026-11-03): the retired
   form is in ``test_voice_and_terms_v1325.RETIRED``; here, that the ten
   sentences that said it say «cálculo».
3. **Settings → Advanced shows no internal code and writes decimals with a
   point**, as the program writes numbers: no «error -112», no «78,5», no
   «0,2», read from the real dialog in Spanish.
4. **Properties has its two entries, named apart** (the owner's decision):
   the canvas mode «Asignar material con clic» and the panel «Panel de
   asignar materiales...», each with an icon of its own.
5. **The two tips of a region start alike**: the canvas tip of the drawing
   modes begins with the head of the data tip of Select.
6. **Stretch Support has an icon of its own**: it borrowed Delete Support's.
7. **Preferences is closed before the window answers**: the «Language
   changed…» notice opened over the dialog still on screen, its buttons
   already in the new language and its title in the old one.
8. **A file dialog starts where it makes sense**: in the folder last used
   in that window, before that in the saved project's folder, and otherwise
   in Documents — never in the program's working folder; *Generate Report*
   proposes its name inside that folder.
9. **A message Qt puts in the status bar is cut like the window's own**: an
   action's status tip (for a disabled one, its reason) ends in «…» where
   the indicators begin, with the whole text as the bar's tip. D325 cut only
   what went through ``showMessage``.
"""
from __future__ import annotations

import contextlib
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MISSING = object()


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextlib.contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(before)


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = owner.__dict__.get(name, _MISSING)
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
    """A modal window would wait for ever without a screen: it fails."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window opened")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name, staticmethod(modal)))
        yield


def _window():
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    w.act_load_demo()
    w.project.is_dirty = False
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()


def _spanish_values():
    from ogr_gui.i18n import _DICTS
    return _DICTS["es"]


# ======================================================================
class TestTheNotesEndAsSentences:

    _NOTE = ("Design standard applied: %s — the reported value is an "
             "over-design factor, not a factor of safety, and must exceed 1.")
    _SAMPLES = ("Design standard applied to every sample: %s — the "
                "statistics describe the over-design factor, not the factor "
                "of safety.")

    def test_the_design_standard_note_has_its_full_stop(self):
        from ogr_gui.i18n import tr
        with _language("es"):
            for key in (self._NOTE, self._SAMPLES):
                said = tr(key)
                assert said != key and said.endswith("."), said

    def test_the_window_writes_it(self):
        from ogr_core.project.design_factors import FactorReport
        w = _window()
        try:
            report = FactorReport(standard="eurocode7_da1c1", applied=True)
            for code in ("en", "es"):
                with _language(code):
                    first = w._factor_report_notes(report)[0]
                    assert first.endswith("."), (code, first)
        finally:
            _done(w)

    def test_antes_de_darlo_por_bueno(self):
        es = _spanish_values()
        quoting = [k for k in es if "before quoting it" in k]
        assert len(quoting) == 5, quoting
        for key in quoting:
            assert es[key].rstrip().endswith("antes de darlo por bueno."), \
                (key, es[key])
        assert not [k for k, v in es.items()
                    if re.search(r"antes de darlo\.", v)]


class TestARunIsACalculo:

    def test_the_ten_sentences(self):
        es = _spanish_values()
        keys = [k for k in es if re.search(r"\b(the|this|a|an|between) "
                                           r"runs?\b|\bruns\b", k)]
        said = [es[k] for k in keys]
        assert len([v for v in said if "cálculo" in v]) >= 10, said
        assert not [v for v in said if re.search(r"\bcorridas?\b", v)]


class TestTheAdvancedTab:

    def test_no_code_and_a_decimal_point(self):
        from PySide6.QtWidgets import QLabel, QWidget
        from ogr_gui.dialogs.project_settings_dialog import \
            ProjectSettingsDialog
        _app()
        w = _window()
        try:
            with _language("es"):
                d = ProjectSettingsDialog(w.project.settings, None,
                                          project=w.project)
                # the labels' texts and every widget's tip: the m-alpha
                # sentences sit in a label, a check box and a spin box
                texts = [lb.text() for lb in d.findChildren(QLabel)]
                texts += [c.toolTip() for c in d.findChildren(QWidget)
                          if c.toolTip()]
                d.deleteLater()
            alpha = [t for t in texts if "m-alfa" in t]
            assert len(alpha) >= 3, alpha
            assert any("no admisibles" in t for t in alpha), alpha
            bad = [t for t in texts
                   if "-112" in t or re.search(r"\d,\d", t)]
            assert not bad, bad
        finally:
            _done(w)

    def test_the_english_has_no_code_either(self):
        src = (Path(__file__).resolve().parent.parent / "ogr_gui" /
               "dialogs" / "project_settings_dialog.py").read_text(
                   encoding="utf-8")
        assert "reports them as error" not in src
        assert "marked inadmissible" in src


class TestPropertiesNamesItsTwoEntries:

    def test_two_names_two_icons(self):
        with _language("es"):
            w = _window()
        try:
            mode, panel = w._actions["assign_material"], w._actions["assign"]
            assert mode.text() == "Asignar material con clic", mode.text()
            assert panel.text() == "Panel de asignar materiales...", \
                panel.text()
            assert mode.icon().cacheKey() != panel.icon().cacheKey()
            menu_texts = [a.text() for m in w.menuBar().actions()
                          if m.menu() is not None
                          for a in m.menu().actions()]
            assert mode.text() in menu_texts and panel.text() in menu_texts
        finally:
            _done(w)

    def test_the_mode_says_where_the_panel_is(self):
        from ogr_gui.i18n import tr
        with _language("es"):
            said = tr("Assign Material by Clicking applies to Material and "
                      "Weak Layer boundaries only. Use Properties → Assign "
                      "Materials Panel to paint regions.")
        assert "Panel de asignar materiales" in said, said


class TestTheRegionTipsStartAlike:

    def test_canvas_and_data_tip(self):
        from PySide6.QtWidgets import QGraphicsPathItem
        from ogr_gui import data_tips
        from ogr_gui.i18n import tr
        with _language("es"):
            w = _window()
            try:
                regions = w.project.resolve_regions()
                region = regions[0]
                mat = w.project.material_by_id(region.material_id)
                head = data_tips.region_heading(mat, 1)
                tips = [i.toolTip() for i in w.canvas.scene().items()
                        if isinstance(i, QGraphicsPathItem) and i.toolTip()]
                first = [t for t in tips if t.startswith(head + "\n")]
                assert first, (head, tips[:3])
                assert "área:" in first[0], first[0]
                # the data tip of the same region, as ``tip_at`` builds it
                tip = data_tips.material_tip(
                    mat, data_tips.DataTipMode.MAXIMUM,
                    region_name=tr("region {0}").format(1))
                assert tip.splitlines()[0] == head, (tip, head)
            finally:
                _done(w)


class TestStretchSupportHasItsIcon:

    def test_not_the_eraser(self):
        from ogr_gui.resources import icons
        assert "stretch_support" in icons._CATALOG
        assert icons._CATALOG["stretch_support"][0] != \
            icons._CATALOG["delete_support"][0]
        w = _window()
        try:
            a, b = w._actions["stretch_support"], w._actions["del_support"]
            assert a.icon().cacheKey() != b.icon().cacheKey()
        finally:
            _done(w)


class TestPreferencesClosesBeforeTheWindowAnswers:

    def test_the_dialog_is_gone_when_the_notice_opens(self):
        from ogr_gui.dialogs.preferences_dialog import PreferencesDialog
        from ogr_gui.i18n import current_language
        _app()
        dlg = PreferencesDialog(None)
        seen = []
        dlg.language_changed.connect(lambda code: seen.append(
            ("language", dlg.isVisible())))
        dlg.theme_changed.connect(lambda name: seen.append(
            ("theme", dlg.isVisible())))
        try:
            dlg.show()
            other = "es" if current_language() != "es" else "en"
            dlg.cbo_language.setCurrentIndex(dlg.cbo_language.findData(other))
            dlg._accept()
            assert seen == [("language", False), ("theme", False)], seen
        finally:
            dlg.deleteLater()


class TestTheFileDialogsStartWhereItMakesSense:

    def _recording(self, answer=""):
        calls = []

        def ask(parent, title, folder, filters, *a, **k):
            calls.append(folder)
            return answer, ""
        return calls, staticmethod(ask)

    def test_open_starts_in_documents_then_in_the_last_folder(self):
        from PySide6.QtCore import QStandardPaths
        from PySide6.QtWidgets import QFileDialog
        from ogr_gui.file_folders import get_open_file_name
        w = _window()
        try:
            calls, ask = self._recording()
            with _swap(QFileDialog, "getOpenFileName", ask), _no_modals():
                w.act_open()
            docs = QStandardPaths.writableLocation(
                QStandardPaths.DocumentsLocation)
            assert calls == [docs], (calls, docs)
            assert calls[0] != os.getcwd()
            with tempfile.TemporaryDirectory() as tmp:
                picked = os.path.join(tmp, "plano.dxf")
                calls, ask = self._recording(picked)
                with _swap(QFileDialog, "getOpenFileName", ask):
                    get_open_file_name(w, "t", "*")
                calls, ask = self._recording()
                with _swap(QFileDialog, "getOpenFileName", ask), \
                        _no_modals():
                    w.act_import_dxf()
                assert [os.path.normcase(c) for c in calls] == \
                    [os.path.normcase(tmp)], (calls, tmp)
        finally:
            _done(w)

    def test_a_saved_project_starts_in_its_folder(self):
        from PySide6.QtWidgets import QFileDialog
        w = _window()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                w.project.file_path = Path(tmp) / "talud.ogr"
                calls, ask = self._recording()
                # Import DXF asks for the file first; Export DXF opens its
                # options before, and that dialog is modal
                with _swap(QFileDialog, "getOpenFileName", ask), \
                        _no_modals():
                    w.act_import_dxf()
                assert [os.path.normcase(c) for c in calls] == \
                    [os.path.normcase(tmp)], calls
                w.project.file_path = None
        finally:
            _done(w)

    def test_the_report_proposes_its_name_inside_the_folder(self):
        from PySide6.QtWidgets import QFileDialog
        from ogr_gui.file_folders import get_save_file_name
        w = _window()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                w._last_folder = tmp
                calls, ask = self._recording()
                with _swap(QFileDialog, "getSaveFileName", ask):
                    get_save_file_name(w, "t", "*.pdf", "Demo_report.pdf")
                assert calls == [os.path.join(tmp, "Demo_report.pdf")], calls
        finally:
            _done(w)


class TestQtsOwnMessagesAreCutToo:
    """9. Measured at 1366 px with the demo: the bar leaves the message
    447 px, and the longest reason of a disabled action takes 1262. Put by
    the window it ended in «…» with the whole text as the bar's tip (D325);
    put by Qt, as a menu hover does, it was not cut at all and the
    indicators covered its end."""

    def test_a_status_tip_ends_in_an_ellipsis(self):
        from PySide6.QtGui import QStatusTipEvent
        from PySide6.QtWidgets import QApplication, QStatusBar
        app = _app()
        w = _window()
        try:
            w.resize(1366, 728)
            w.show()
            app.processEvents()
            bar = w.statusBar()
            tip = max((a.statusTip() for a in w._actions.values()), key=len)
            fm = bar.fontMetrics()
            assert fm.horizontalAdvance(tip) > bar.message_room(), tip
            QApplication.sendEvent(w, QStatusTipEvent(tip))
            app.processEvents()
            shown = QStatusBar.currentMessage(bar)
            assert shown.endswith("…"), shown
            assert fm.horizontalAdvance(shown) <= bar.message_room()
            assert bar.toolTip() == tip
            assert bar.currentMessage() == tip
            QApplication.sendEvent(w, QStatusTipEvent(""))
            app.processEvents()
            assert QStatusBar.currentMessage(bar) == ""
            assert bar.toolTip() == ""
        finally:
            _done(w)
