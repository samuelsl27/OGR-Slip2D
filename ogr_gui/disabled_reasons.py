# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Why a menu entry is disabled, on the status bar of its window.

v0.1.288 (D289) wrote ``DisabledReasonFilter`` for the main window, and
v0.1.294 (D289b) gave every disabled entry of its menus a reason. The
Interpret window had neither: «Graph SF with Time», «Support Force
Analysis» and «Support Force Diagram» were grey and left the status bar
empty (the third GUI test, H3). v0.1.328 (D324) moves the filter here, so a
window that ``main_window`` imports can install it too.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QMenu


class DisabledReasonFilter(QObject):
    """v0.1.288 (D289) — puts on the status bar the status tip of the
    DISABLED menu entry under the pointer.

    Qt shows an action's status tip only when the menu makes it the current
    action, and with the Fusion and windows11 styles it never does that for
    a disabled one (``SH_Menu_AllowActiveAndDisabled`` is 0): the reason a
    groundwater entry is disabled would never be seen. Enabled entries are
    left to Qt.

    v0.1.328 — it reaches its window as its Qt parent and keeps no Python
    reference to it: the window keeps the filter, and a cycle between the
    two is left to the garbage collector (the family of D310).
    """

    def __init__(self, window) -> None:
        super().__init__(window)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.MouseMove and isinstance(obj, QMenu):
            act = obj.actionAt(event.position().toPoint())
            if act is not None and not act.isEnabled() and act.statusTip():
                window = self.parent()
                if window is not None:
                    window.statusBar().showMessage(act.statusTip(), 5000)
        return False


def install(window) -> DisabledReasonFilter:
    """One filter on every menu of ``window``'s menu bar, submenus too."""
    reasons = DisabledReasonFilter(window)
    for menu in window.menuBar().findChildren(QMenu):
        menu.installEventFilter(reasons)
    return reasons


def gate(action, enabled, reason: str) -> None:
    """Enable ``action``, or disable it saying why.

    The reason is its status tip while it is disabled, which the filter puts
    on the status bar, and nothing while it is enabled: an enabled entry
    shows what it does, not what it needed (D289b).
    """
    enabled = bool(enabled)
    action.setEnabled(enabled)
    action.setStatusTip("" if enabled else reason)
