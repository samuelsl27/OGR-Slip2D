# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.195 (spec 008) — every action of the program has an agent equivalent,
a written reason not to, or a phase that will give it one.

Rule 3 exists because a module shipped invisible: its actions were
registered and never reached a menu. The agent can be left behind the same
way — a new menu action nobody maps is something the program can do and an
agent cannot, silently. So this file builds the REAL main window and holds
``ogr_api/inventory.py`` to it:

* every key of ``MainWindow._actions`` is classified exactly once —
  MAPPED, UI_ONLY or PENDING — and nothing is classified that is not an
  action;
* every MAPPED action names an operation that exists in ``ogr_api``;
* every UI_ONLY action carries its reason, and every PENDING one a phase of
  spec 008;
* the number of PENDING actions never exceeds its ceiling, which only goes
  down. Phase F4 closes with it at zero.
"""
from __future__ import annotations

_WINDOWS: list = []


def _keys():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    QApplication.instance() or QApplication([])
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    _WINDOWS.append(w)
    return set(w._actions)


class TestTheInventory:
    def test_every_action_is_classified_exactly_once(self):
        from ogr_api.inventory import MAPPED, PENDING, UI_ONLY
        keys = _keys()
        if keys is None:  # pragma: no cover
            return
        groups = (set(MAPPED), set(UI_ONLY), set(PENDING))
        for i, a in enumerate(groups):
            for b in groups[i + 1:]:
                assert not a & b, sorted(a & b)
        classified = set().union(*groups)
        assert not keys - classified, (
            "actions an agent cannot reach and nobody decided about: "
            f"{sorted(keys - classified)} — map them in "
            f"ogr_api/inventory.py")
        assert not classified - keys, (
            f"classified but not actions: {sorted(classified - keys)}")

    def test_mapped_actions_name_real_operations(self):
        from ogr_api import OPERATIONS
        from ogr_api.inventory import MAPPED
        bad = {k: op for k, op in MAPPED.items() if op not in OPERATIONS}
        assert not bad, bad

    def test_reasons_and_phases_are_written(self):
        from ogr_api.inventory import PENDING, UI_ONLY
        assert all(r.strip() for r in UI_ONLY.values())
        assert set(PENDING.values()) <= {"F2", "F3", "F4"}

    def test_pending_only_goes_down(self):
        from ogr_api.inventory import PENDING, PENDING_CEILING
        assert len(PENDING) <= PENDING_CEILING, (
            f"{len(PENDING)} pending actions, ceiling {PENDING_CEILING}: "
            f"a new action must be mapped, not added to the backlog")
