# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.288 (D289) — a disabled menu entry looks disabled, and the groundwater
ones say why on the status bar.

The defect: both stylesheets of ``ogr_gui/themes`` give ``QMenu`` a text
colour and no ``:disabled`` rule, and with a stylesheet Qt draws a disabled
item in that same colour. In a new project *Groundwater* showed «Define
Hydraulic Properties…», «Water Pressure Grid…», «Set Boundary Conditions…»
and «Transient Groundwater…» as if they could be used; clicking did nothing
and nothing said why (the GUI test of 0.1.284). The dark theme did the same
to buttons, boxes, drop-downs and views.

What these tests protect:

* with each theme, a disabled menu item is drawn with less contrast against
  the menu than an enabled one (rendered, not read from the stylesheet);
* in each theme, every interactive widget whose text colour the stylesheet
  sets has a ``:disabled`` colour too;
* with the water-table method, the FE groundwater entries carry their
  reason, and hovering the disabled entry puts it on the status bar — Qt
  does not activate a disabled item with the Fusion and windows11 styles
  (``SH_Menu_AllowActiveAndDisabled`` = 0), so a status tip alone would never
  show; with an FE method the entry is enabled and carries none.

The application's stylesheet is restored after each test (rule 5).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QAction, QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu  # noqa: E402

from ogr_gui.i18n import tr  # noqa: E402
from ogr_gui.themes import THEMES, apply_theme  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def _contrast(img, rect, bg) -> int:
    """Largest colour distance from ``bg`` inside ``rect``: the text."""
    best = 0
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            c = img.pixelColor(x, y)
            best = max(best, abs(c.red() - bg.red()) + abs(c.green() - bg.green())
                       + abs(c.blue() - bg.blue()))
    return best


class TestTheThemes:
    def _rendered(self, theme):
        app = _app()
        old = app.styleSheet()
        try:
            apply_theme(app, theme)
            menu = QMenu()
            on = QAction("Compute Groundwater", menu)
            off = QAction("Compute Groundwater", menu)
            off.setEnabled(False)
            menu.addAction(on)
            menu.addAction(off)
            menu.popup(menu.mapToGlobal(menu.pos()))
            app.processEvents()
            img = menu.grab().toImage()
            r_on, r_off = menu.actionGeometry(on), menu.actionGeometry(off)
            bg = img.pixelColor(r_on.right() - 2, r_on.center().y())
            result = _contrast(img, r_on, bg), _contrast(img, r_off, bg)
            menu.hide()
            return result
        finally:
            app.setStyleSheet(old)

    def test_light_draws_a_disabled_item_paler(self):
        on, off = self._rendered("light")
        assert off < 0.75 * on, (on, off)

    def test_dark_draws_a_disabled_item_paler(self):
        on, off = self._rendered("dark")
        assert off < 0.75 * on, (on, off)

    def test_every_coloured_widget_has_a_disabled_colour(self):
        exempt = {"QMainWindow", "QDialog", "QMenuBar", "QStatusBar",
                  "QDockWidget", "QDockWidget::title", "QToolTip",
                  "QStatusBar QLabel"}
        for name, qss in THEMES.items():
            blocks = re.findall(r"([^{}]+)\{([^}]*)\}", re.sub(r"/\*.*?\*/", "", qss, flags=re.S))
            coloured, disabled = set(), set()
            for sels, body in blocks:
                has_colour = re.search(r"(^|[;\s])color\s*:", body) is not None
                for sel in (s.strip() for s in sels.split(",")):
                    if sel.endswith(":disabled") and has_colour:
                        disabled.add(sel[:-len(":disabled")])
                    elif has_colour and ":" not in sel.replace("::", ""):
                        coloured.add("QMenu::item" if sel == "QMenu" else sel)
            missing = sorted(s for s in coloured - exempt if s not in disabled)
            assert not missing, (name, missing)


class TestTheReason:
    def _window(self, method):
        from ogr_gui.main_window import MainWindow
        _app()
        w = MainWindow()
        w.project.settings.groundwater.method = method
        w._update_groundwater_actions()
        return w

    def _gw_menu(self, w):
        # the menu bar's own child, not a wrapper from QAction.menu(): a
        # temporary one of those can leave the menu deleted under PySide
        return next(m for m in w.menuBar().findChildren(QMenu)
                    if m.title() == tr("Groundwater"))

    def test_the_water_table_method_gives_the_fe_entries_their_reason(self):
        w = self._window("water_table")
        try:
            for key in ("gw_hydraulic", "gw_transient"):
                act = w._actions[key]
                assert not act.isEnabled()
                assert "finite-element" in act.statusTip(), (key, act.statusTip())
            for key in ("gw_bcs", "gw_compute", "reset_mesh"):
                assert "mesh" in w._actions[key].statusTip(), key
        finally:
            w.close()

    def test_hovering_a_disabled_entry_puts_its_reason_on_the_status_bar(self):
        w = self._window("water_table")
        menu = self._gw_menu(w)
        try:
            act = w._actions["gw_hydraulic"]
            menu.popup(w.mapToGlobal(w.rect().center()))
            _app().processEvents()
            pos = QPointF(menu.actionGeometry(act).center())
            ev = QMouseEvent(QEvent.Type.MouseMove, pos, QPointF(menu.mapToGlobal(pos.toPoint())),
                             Qt.NoButton, Qt.NoButton, Qt.NoModifier)
            QApplication.sendEvent(menu, ev)
            _app().processEvents()
            assert w.statusBar().currentMessage() == act.statusTip()
        finally:
            menu.hide()
            w.close()

    def test_an_fe_method_enables_them_without_a_reason(self):
        w = self._window("fea_steady")
        try:
            act = w._actions["gw_hydraulic"]
            assert act.isEnabled()
            assert act.statusTip() == ""
        finally:
            w.close()
