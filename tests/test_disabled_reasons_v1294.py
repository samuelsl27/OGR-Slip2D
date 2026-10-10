# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.294 (D289b) — every menu entry that is disabled says why on the status
bar.

D289 (0.1.288) gave a status tip — which ``DisabledReasonFilter`` puts on
the status bar, the only way a disabled entry can say anything with the
Fusion and windows11 styles — to the groundwater entries of
``_update_groundwater_actions``. Measured in a new project, seven more
entries were disabled without one: *Add Drawdown Line*, *Drawdown Level
Sweep* and the four Block Search objects carried their reason only as a
tooltip (which no menu shows, and two of them outside ``tr()``), and the
three Statistics entries had none at all (the second GUI test, H5).

What these tests protect:

* in a new project, every disabled action reachable from the menu bar has
  a status tip;
* with Rapid Drawdown on, the drawdown entries are enabled and carry none;
* with a probabilistic analysis on and no random variables, *Random
  Variables* is enabled and *Compute Statistics* says it needs them.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMenu  # noqa: E402


def _window():
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    w.refresh_action_availability()
    return w


def _in_menus(w):
    ids = set()
    for menu in w.menuBar().findChildren(QMenu):
        for a in menu.actions():
            ids.add(id(a))
    return ids


class TestEveryReason:
    def test_every_disabled_menu_entry_says_why(self):
        w = _window()
        try:
            reachable = _in_menus(w)
            silent = [k for k, a in w._actions.items()
                      if id(a) in reachable and not a.isEnabled()
                      and not a.statusTip()]
            assert not silent, silent
        finally:
            w.close()

    def test_rapid_drawdown_enables_the_drawdown_entries_without_reason(self):
        w = _window()
        try:
            w.project.settings.groundwater.rapid_drawdown = True
            w.refresh_action_availability()
            for key in ("add_drawdown", "drawdown_sweep"):
                act = w._actions[key]
                assert act.isEnabled(), key
                assert act.statusTip() == "", key
        finally:
            w.close()

    def test_statistics_without_variables_says_it_needs_them(self):
        w = _window()
        try:
            w.project.settings.statistics.probabilistic_analysis = True
            w._update_statistics_actions()
            assert w._actions["stat_vars"].isEnabled()
            assert w._actions["stat_vars"].statusTip() == ""
            tip = w._actions["stat_compute"].statusTip()
            assert not w._actions["stat_compute"].isEnabled()
            assert "random variables" in tip, tip
        finally:
            w.close()
