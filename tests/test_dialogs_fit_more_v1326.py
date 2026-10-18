# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.326 (D319, D320, D321) — the three things the third test of the
interface saw drawn wrong, each by its own measure.

* **D320.** Project Settings cut its page names («Agua sub», «Transitori»,
  narrower still in the dark theme): its list had a maximum of 180 px and
  was the one part of the dialog that could give way. The list is now as
  wide as its widest name, and each page scrolls down instead of being cut
  at the bottom (the Design Standard page cut its last note).
* **D321.** Surface Options set ``setMinimumSize(460, 520)``. On a window an
  explicit minimum REPLACES the one its layout would enforce, so the dialog
  opened, and could be dragged, smaller than its pages: the Block Search
  boxes came out 2–3 px tall and its angle groups empty.
* **D319.** The critical row of the results panel was ``Qt.yellow`` behind
  the theme's text: white on yellow in the dark theme. The disabled header
  of the transient stages read 2.4:1 there.

The census of every dialog (``test_dialogs_fit_v1315``) now also reports
cut labels, check boxes and lists and squashed boxes; this file holds the
three cases above, which that census sees only as one entry each, and the
two pieces the census made necessary in ``ogr_gui/dialog_size.py``:

* ``WrappingCheckBox``: a check box keeps its text on one line, and three
  long ones set the minimum width of their dialogs (740 px in Spanish);
* ``hold_wrapped_height``: a word-wrapped note asks for more height the
  narrower the window is, and Qt does not add it to a WINDOW's minimum, so
  13 dialogs squashed their boxes or cut the note's lines. The hold keeps
  no Python reference to its window, nor the window to it: a cycle between
  the two left them to the garbage collector, which cleared the filter's
  attributes under live Qt objects (the family of D310).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_WINDOWS: list = []


def _rgb(name):
    from PySide6.QtGui import QColor
    c = QColor(name)
    return (c.red(), c.green(), c.blue())


class TestProjectSettingsListsWholePageNames:
    def test_in_both_themes(self):
        import test_dialogs_fit_v1315 as fit
        from ogr_core.project.project import Project
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        for theme in ("light", "dark"):
            with fit._spanish_with(theme) as app:
                p = Project(name="D320")
                d = ProjectSettingsDialog(p.settings, None, project=p)
                d.show()
                app.processEvents()
                try:
                    nav = d.nav
                    assert nav.sizeHintForColumn(0) <= \
                        nav.viewport().width(), (theme,
                                                 nav.sizeHintForColumn(0),
                                                 nav.viewport().width())
                    assert not nav.horizontalScrollBar().isVisible(), theme
                    # each page scrolls down rather than being cut
                    for i in range(d.stack.count()):
                        page = d.stack.widget(i)
                        assert hasattr(page, "widget") and \
                            page.widget() is d.pages[i], i
                finally:
                    d.hide()
                    d.deleteLater()
                    app.processEvents()


class TestSurfaceOptionsKeepsItsLayoutMinimum:
    def test_no_window_minimum_of_its_own(self):
        """The layout's minimum, not a number written for English."""
        import test_dialogs_fit_v1315 as fit
        from PySide6.QtWidgets import QAbstractSpinBox
        from ogr_gui.dialogs.grid_dialogs import SurfaceOptionsDialog
        w = fit._window()
        try:
            for theme in ("light", "dark"):
                with fit._spanish_with(theme) as app:
                    d = SurfaceOptionsDialog(w.project)
                    d.show()
                    app.processEvents()
                    try:
                        # the window's minimum is its layout's own: an
                        # explicit one would REPLACE it
                        m, lay = d.minimumSize(), d.layout().totalMinimumSize()
                        assert m.width() == lay.width(), (m, lay)
                        assert m.height() >= lay.height(), (m, lay)
                        for i in range(d.stack.count()):
                            d.stack.setCurrentIndex(i)
                            app.processEvents()
                            for size in (d.size(), d.minimumSizeHint()):
                                d.resize(size)
                                app.processEvents()
                                low = [(b.height(),
                                        b.minimumSizeHint().height())
                                       for b in d.findChildren(
                                           QAbstractSpinBox)
                                       if b.isVisible() and b.height()
                                       < b.minimumSizeHint().height()]
                                assert low == [], (theme, i, size, low)
                    finally:
                        d.hide()
                        d.deleteLater()
                        app.processEvents()
        finally:
            fit._done(w)


class TestTheCriticalRowReadsInBothThemes:
    def test_its_ink_on_its_background(self):
        from test_dark_theme_v1316 import _ratio
        from ogr_gui.widgets.results_dock import (CRITICAL_ROW_BACKGROUND,
                                                  CRITICAL_ROW_INK)
        QApplication.instance() or QApplication([])
        assert _ratio(_rgb(CRITICAL_ROW_INK),
                      _rgb(CRITICAL_ROW_BACKGROUND)) >= 4.5

    def test_the_row_carries_that_pair(self):
        import test_dialogs_fit_v1315 as fit
        from test_design_factor_report_gui_v1165 import _compute_all
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from ogr_gui.widgets.results_dock import (CRITICAL_ROW_BACKGROUND,
                                                  CRITICAL_ROW_INK)
        w = fit._window()
        try:
            _compute_all(w)
            table = w.results_dock.table
            assert table.rowCount() > 1
            for c in range(table.columnCount()):
                item = table.item(0, c)
                assert item.background().color() == QColor(
                    CRITICAL_ROW_BACKGROUND), c
                assert item.foreground().color() == QColor(
                    CRITICAL_ROW_INK), c
            # control: the other rows keep the theme's own colours
            assert table.item(1, 0).background().style() == Qt.NoBrush
        finally:
            fit._done(w)


class TestTheDisabledHeaderReadsInTheDarkTheme:
    def test_the_last_rule_for_it(self):
        from test_dark_theme_v1316 import _ratio
        from ogr_gui.themes import _DARK
        rules = re.findall(r"QHeaderView::section:disabled\s*\{\s*color:\s*"
                           r"(#[0-9a-fA-F]{6})", _DARK)
        assert rules, "no rule of its own"
        header = re.search(r"QHeaderView::section\s*\{[^}]*?"
                           r"background-color:\s*(#[0-9a-fA-F]{6})", _DARK)
        # a later rule wins over the shared disabled grey
        assert _ratio(_rgb(rules[-1]), _rgb(header.group(1))) >= 4.0


class TestTheListInksFollowTheTheme:
    def test_dxf_import_and_problems(self):
        """Fixed greys and reds in a list read on one theme only."""
        root = Path(__file__).resolve().parent.parent / "ogr_gui" / "dialogs"
        for name in ("dxf_import_dialog.py", "dxf_problems_panel.py"):
            src = (root / name).read_text(encoding="utf-8")
            fixed = re.findall(r"setForeground\([^)]*(?:Qt\.\w+|"
                               r"QColor\(\s*['\"]#|QColor\(\s*\d)", src)
            assert fixed == [], (name, fixed)
            assert "theme_color(" in src, name


class TestTheWrappingCheckBox:
    """A check box whose text wraps, and nothing else of it changes."""

    TEXT = ("Anchors: the permanent-action factor on the effective stress of "
            "the bond")

    def _box(self):
        from ogr_gui.dialog_size import WrappingCheckBox
        QApplication.instance() or QApplication([])
        box = WrappingCheckBox(self.TEXT)
        _WINDOWS.append(box)
        return box

    def test_it_asks_for_more_lines_the_narrower_it_is(self):
        box = self._box()
        wide = box.heightForWidth(2000)
        narrow = box.heightForWidth(box.minimumSizeHint().width())
        assert box.hasHeightForWidth()
        assert narrow > wide, (narrow, wide)
        # and its minimum is below one line of its text, the width a plain
        # check box imposes on its dialog
        from PySide6.QtWidgets import QCheckBox
        plain = QCheckBox(self.TEXT)
        _WINDOWS.append(plain)
        assert box.minimumSizeHint().width() < \
            plain.minimumSizeHint().width(), (
                box.minimumSizeHint().width(),
                plain.minimumSizeHint().width())

    def test_a_form_layout_gives_it_its_lines(self):
        """A check box is Fixed in height, and a layout never gives a Fixed
        item more than its one-line hint: the first version wrapped its text
        and was cut to one line in Surface Options (20 px of 35)."""
        from PySide6.QtWidgets import QFormLayout, QSpinBox, QWidget
        box = self._box()
        page = QWidget()
        _WINDOWS.append(page)
        form = QFormLayout(page)
        form.addRow("A label as wide as the ones of the options:", QSpinBox())
        form.addRow("", box)
        page.resize(box.minimumSizeHint().width() * 2, 400)
        page.show()
        QApplication.processEvents()
        try:
            assert box.heightForWidth(box.width()) > box.minimumSizeHint().height()
            assert box.height() >= box.heightForWidth(box.width()), (
                box.width(), box.height(), box.heightForWidth(box.width()))
        finally:
            page.hide()

    def test_control_a_plain_check_box_does_not_wrap(self):
        from PySide6.QtWidgets import QCheckBox
        QApplication.instance() or QApplication([])
        plain = QCheckBox(self.TEXT)
        _WINDOWS.append(plain)
        assert not plain.hasHeightForWidth()
        assert plain.minimumSizeHint().width() >= \
            plain.fontMetrics().horizontalAdvance(self.TEXT)

    def test_it_keeps_its_text_and_a_click_on_the_last_line_ticks_it(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        box = self._box()
        width = box.minimumSizeHint().width()
        box.resize(width, box.heightForWidth(width))
        box.show()
        QApplication.processEvents()
        assert box.text() == self.TEXT
        assert not box.isChecked()
        QTest.mouseClick(box, Qt.LeftButton, Qt.NoModifier,
                         QPoint(box.width() - 4, box.height() - 4))
        assert box.isChecked()
        box.hide()


class TestTheHoldKeepsNoCycle:
    """The window reaches its hold by name and the hold its window as its
    Qt parent: a Python cycle between them would be left to the garbage
    collector, which clears attributes under live Qt objects (D310)."""

    def test_neither_holds_the_other_in_python(self):
        import gc
        from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
        from ogr_gui.dialog_size import _WrappedHeight, hold_wrapped_height
        QApplication.instance() or QApplication([])
        d = QDialog()
        _WINDOWS.append(d)
        note = QLabel("word " * 80)
        note.setWordWrap(True)
        QVBoxLayout(d).addWidget(note)
        hold_wrapped_height(d)
        hold_wrapped_height(d)  # a second call adds nothing
        holds = d.findChildren(_WrappedHeight)
        assert len(holds) == 1
        assert not any(v is d for v in vars(holds[0]).values())
        assert not any(v is holds[0] for v in vars(d).values())
        gc.collect()
        d.show()
        QApplication.processEvents()
        # the wrapped note is whole at the window's minimum width
        d.resize(d.minimumWidth(), d.minimumHeight())
        QApplication.processEvents()
        assert note.height() >= note.heightForWidth(note.width())
        d.hide()
