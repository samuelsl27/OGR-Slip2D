# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.42 — Menu reachability.

A whole module can be implemented, tested and still be **invisible**: the
groundwater GUI (five dialogs and an interpret window), the probabilistic
GUI and the support back analysis all had their actions REGISTERED but
never added to any menu, so there was no way to reach them from the menu
bar. Everything worked and nothing was usable.

This test walks the real menu bar and asserts that every registered
action is reachable, which turns that class of mistake into a failure
instead of a silent gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []      # keeps references alive: Qt destroys the QMenus when
#                    the owning MainWindow is garbage-collected, which
#                    made the walk fail with "C++ object already deleted".


def _window():
    QApplication.instance() or QApplication([])
    # Menu titles are translated, so the language must be pinned: another
    # test leaving it in Spanish would otherwise make these look for
    # "Support" while the menu reads "Soporte".
    from ogr_gui.i18n import set_language
    set_language("en")
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    _WINDOWS.append(w)
    return w


def _menu_texts(window):
    """Every action text reachable by walking the menu bar, submenus
    included."""
    found = set()

    def walk(menu):
        for act in menu.actions():
            sub = act.menu()
            if sub is not None:
                walk(sub)
            elif act.text():
                found.add(act.text())

    for act in window.menuBar().actions():
        if act.menu() is not None:
            walk(act.menu())
    return found


@_requires_qt
class TestReachability:
    def test_every_registered_action_is_in_a_menu(self):
        """The check that was missing. Toolbar-only or context-menu-only
        actions would be legitimate exceptions; there are none today, so
        the invariant is simply 'all of them'."""
        w = _window()
        reachable = _menu_texts(w)
        # Actions deliberately not in menus (tool modes driven from the
        # toolbar or the canvas) would go here.
        allowed_absent: set = set()
        missing = sorted(
            key for key, act in w._actions.items()
            if act.text() and act.text() not in reachable
            and key not in allowed_absent)
        assert not missing, (
            f"{len(missing)} actions are registered but unreachable from "
            f"the menu bar: {missing}")

    def test_groundwater_menu_exists_and_is_ordered(self):
        """Groundwater is a top-level menu ordered by the real workflow:
        properties, then mesh, then boundary conditions, then compute,
        then interpret."""
        w = _window()
        texts = None
        for act in w.menuBar().actions():
            if act.menu() is not None and act.text() == "Groundwater":
                # Read the texts here, without holding on to the QMenu:
                # keeping the wrapper alive past the loop can outlive the
                # C++ object.
                texts = [a.text() for a in act.menu().actions()
                         if a.text()]
                break
        assert texts is not None, "no Groundwater menu"
        for expected in ("Define Hydraulic Properties...",
                         "Water Pressure Grid...",
                         "Set Boundary Conditions...",
                         "Compute Groundwater",
                         "Interpret Groundwater"):
            assert expected in texts, expected
        assert texts.index("Define Hydraulic Properties...") < \
            texts.index("Set Boundary Conditions...")
        assert texts.index("Set Boundary Conditions...") < \
            texts.index("Compute Groundwater")
        assert texts.index("Compute Groundwater") < \
            texts.index("Interpret Groundwater")

    def test_mesh_submenu(self):
        w = _window()
        reachable = _menu_texts(w)
        assert w._actions["gen_mesh"].text() in reachable
        assert w._actions["reset_mesh"].text() in reachable

    def test_statistics_menu_exists(self):
        w = _window()
        names = [a.text() for a in w.menuBar().actions() if a.menu()]
        assert "Statistics" in names

    def test_back_analysis_is_in_the_support_menu(self):
        """The reference places it there."""
        w = _window()
        for act in w.menuBar().actions():
            if act.menu() is not None and act.text() == "Support":
                texts = [a.text() for a in act.menu().actions()
                         if a.text()]
                assert any("Back Analysis" in t for t in texts), texts
                return
        raise AssertionError("no Support menu")

    def test_menu_names_are_translatable(self):
        from ogr_gui.i18n import _DICTS
        for name in ("Groundwater", "Statistics", "Mesh"):
            assert name in _DICTS["es"], name
