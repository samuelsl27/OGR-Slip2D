# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.328 (D324, D325) — a grey entry of Interpret says why, and a long
status message is not hidden behind the indicators.

The defects, seen in the third test of the interface (H3):

* **D324.** In Interpret, Data → «Graph SF with Time», «Support Force
  Analysis» and «Support Force Diagram» were grey and left the status bar
  empty. Their reason was a tooltip, which no menu shows, and
  ``DisabledReasonFilter`` (D289) lived in ``main_window`` and was
  installed on the main window's menus only (D289b walked those alone).
  The filter moves to ``ogr_gui/disabled_reasons.py`` and Interpret
  installs it; every entry that can be disabled carries its reason as a
  status tip while it is, and none while it is enabled.
* **D325.** QStatusBar draws its message under the permanent indicators,
  so SNAP / GRID / ORTHO / OSNAP hid the end of the long ones. The bars of
  both windows are now an ``ElidingStatusBar``: the message ends in «…»
  where the indicators begin, its whole text is the bar's tooltip while it
  lasts, and ``currentMessage()`` still answers the whole message (the
  tests of the window read it, on windows never shown).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QStatusBar  # noqa: E402

_WINDOWS: list = []

#: The longest status message the third GUI test saw cut.
LONG = ("The Water Pressure Grid is read only with a grid groundwater method "
        "(Project Settings > Groundwater > Method), which also says what its "
        "values are.")


def _interpret(supports=False):
    """Interpret on a small search of the first worked example: no
    transient run, no statistics, and supports only when asked."""
    from test_slide_validation_ej1 import _ej1_project
    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    QApplication.instance() or QApplication([])
    set_language("en")
    p = _ej1_project()
    if supports:
        from ogr_core.geometry import Vertex
        from ogr_core.support import EndAnchored, SupportInstance
        anchor = EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)
        p.support_types = [anchor]
        p.supports = [SupportInstance(
            type_id=anchor.TYPE_ID, head=Vertex(80.0, 60.0),
            tail=Vertex(70.0, 55.0))]
    r = GridSearch(method=BishopSimplified(), grid_x=(75, 95),
                   grid_y=(62, 80), grid_nx=3, grid_ny=3,
                   radius_increment=10, min_radius=15,
                   num_slices=14, min_area=0.5).run(p)
    w = InterpretWindow(p, {"bishop_simplified": r}, None)
    _WINDOWS.append(w)
    return w


def _menu_actions(w):
    """Every action reachable from the window's menu bar. Only the actions:
    a menu wrapper kept from the walk can stop being valid (``findChildren``
    returns deleted menus too), and the window owns its actions."""
    out = []

    def walk(menu):
        for act in menu.actions():
            if act.menu() is not None:
                walk(act.menu())
            elif not act.isSeparator():
                out.append(act)

    for top in w.menuBar().actions():
        if top.menu() is not None:
            walk(top.menu())
    return out


# ----------------------------------------------------------------------
class TestInterpretSaysWhy:
    def test_every_disabled_entry_has_its_reason(self):
        w = _interpret()
        silent = [a.text() for a in _menu_actions(w)
                  if not a.isEnabled() and not a.statusTip()]
        assert silent == [], silent

    def test_the_three_of_the_test_say_it(self):
        w = _interpret()
        names = {a.text(): a for a in _menu_actions(w)}
        for name in ("Graph SF with Time...", "Support Force Analysis...",
                     "Support Force Diagram..."):
            act = names[name]
            assert not act.isEnabled(), name
            assert act.statusTip().startswith("Requires"), (name,
                                                            act.statusTip())

    def test_control_an_enabled_entry_carries_none(self):
        w = _interpret(supports=True)
        names = {a.text(): a for a in _menu_actions(w)}
        act = names["Support Force Analysis..."]
        assert act.isEnabled()
        assert act.statusTip() == ""

    def test_the_pointer_on_it_puts_the_reason_on_the_bar(self):
        from PySide6.QtGui import QMouseEvent
        w = _interpret()
        act = next(a for a in _menu_actions(w)
                   if a.text() == "Graph SF with Time...")
        # reached from the action: a menu wrapper taken from a menu-bar
        # action inside a generator was reported deleted once the generator
        # let go of that action, though the menu itself lived on
        menu = next(o for o in act.associatedObjects()
                    if isinstance(o, QMenu))
        # open, as the user has it: a menu never shown finds no action
        # under a point (``actionAt``). ``popup`` does not block.
        menu.popup(w.mapToGlobal(w.rect().center()))
        QApplication.processEvents()
        try:
            centre = QPointF(menu.actionGeometry(act).center())
            event = QMouseEvent(QEvent.Type.MouseMove, centre,
                                QPointF(menu.mapToGlobal(centre.toPoint())),
                                Qt.NoButton, Qt.NoButton, Qt.NoModifier)
            QApplication.sendEvent(menu, event)
            assert w.statusBar().currentMessage() == act.statusTip()
        finally:
            menu.hide()

    def test_the_filter_keeps_no_python_reference_to_its_window(self):
        from ogr_gui.disabled_reasons import DisabledReasonFilter
        w = _interpret()
        filters = w.findChildren(DisabledReasonFilter)
        assert len(filters) == 1
        assert not any(v is w for v in vars(filters[0]).values())


# ----------------------------------------------------------------------
def _shown_main(width):
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.resize(width, 700)
    w.show()
    QApplication.processEvents()
    _WINDOWS.append(w)
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()


class TestALongMessageIsNotHidden:
    """At 1366 px, a common screen. The indicators of the main window take
    some 880 px: at 900 the message has no room at all, as it had none
    before this version."""

    def test_it_ends_where_the_indicators_begin(self):
        w = _shown_main(1366)
        try:
            bar = w.ogr_status
            bar.showMessage(LONG, 10000)
            shown = QStatusBar.currentMessage(bar)
            assert bar.message_room() > 200, bar.message_room()
            assert shown.endswith("…"), shown
            assert bar.fontMetrics().horizontalAdvance(shown) <= \
                bar.message_room()
            # the whole text: in the tooltip, and for whoever asks
            assert bar.toolTip() == LONG
            assert bar.currentMessage() == LONG
        finally:
            _done(w)

    def test_control_a_short_one_is_whole(self):
        w = _shown_main(1366)
        try:
            bar = w.ogr_status
            bar.showMessage("Ready.", 10000)
            assert QStatusBar.currentMessage(bar) == "Ready."
            assert bar.toolTip() == ""
        finally:
            _done(w)

    def test_a_wider_bar_shows_more_and_keeps_its_time(self):
        w = _shown_main(1366)
        try:
            bar = w.ogr_status
            bar.showMessage(LONG, 10000)
            narrow = QStatusBar.currentMessage(bar)
            until = bar._until
            w.resize(1900, 700)
            QApplication.processEvents()
            wide = QStatusBar.currentMessage(bar)
            assert len(wide) > len(narrow), (narrow, wide)
            assert bar._until == until
        finally:
            _done(w)

    def test_its_tooltip_goes_with_it(self):
        w = _shown_main(1366)
        try:
            bar = w.ogr_status
            bar.showMessage(LONG, 10000)
            assert bar.toolTip() == LONG
            bar.clearMessage()
            assert bar.toolTip() == "" and bar.currentMessage() == ""
        finally:
            _done(w)

    def test_a_window_never_shown_keeps_the_whole_message(self):
        """The window's own tests read the message on windows that are
        never shown, where the bar has no width to cut it to."""
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        _WINDOWS.append(w)
        try:
            w.ogr_status.showMessage(LONG, 10000)
            assert QStatusBar.currentMessage(w.ogr_status) == LONG
        finally:
            _done(w)

    def test_interpret_has_the_same_bar(self):
        from ogr_gui.widgets.status_bar import ElidingStatusBar
        w = _interpret()
        assert isinstance(w.statusBar(), ElidingStatusBar)
