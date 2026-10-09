# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.285 (D286) — the mouse wheel changes a number box or a drop-down only
when it has the focus; otherwise it scrolls whatever contains it.

Qt gives every ``QAbstractSpinBox`` and ``QComboBox`` the focus policy
``WheelFocus``: the wheel focuses them AND steps them. In a long dialog
that the user scrolls with the wheel, whichever box passes under the
pointer changes value — the GUI test of 0.1.284 saw the Gardner ``a`` of
the hydraulic dialog go from 0.01 to 0 that way, and pressing OK would
have stored it. A parameter changed without the user seeing it change is
the worst outcome this program can have, so the rule is application-wide:

* when a box or a drop-down is polished, ``WheelFocus`` becomes
  ``StrongFocus`` (click or Tab still focus it; the wheel no longer does);
* a wheel event reaching one without the focus is ignored and marked
  handled, so Qt passes it on to the parent — the scroll area moves.

The canvas (zoom), lists, tables and scroll bars are not touched. The
filter sees every event of the application; it costs one comparison of
the event type for all but wheel and polish events.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox

#: Switch off to give the wheel back to every box, focused or not (the
#: behaviour up to 0.1.284).
WHEEL_NEEDS_FOCUS = True

_GUARDED = (QAbstractSpinBox, QComboBox)
_WHEEL = QEvent.Type.Wheel
_POLISH = QEvent.Type.Polish


class WheelGuard(QObject):
    """The application-wide event filter of this module."""

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt API)
        t = event.type()
        if t != _WHEEL and t != _POLISH:
            return False
        if not WHEEL_NEEDS_FOCUS or not isinstance(obj, _GUARDED):
            return False
        if t == _POLISH:
            if obj.focusPolicy() == Qt.FocusPolicy.WheelFocus:
                obj.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            return False
        if obj.hasFocus():
            return False
        # Ignored AND handled: the box does not step, and Qt hands the
        # (spontaneous) event on to the parent, which scrolls.
        event.ignore()
        return True


_guard: Optional[WheelGuard] = None


def install(app: Optional[QApplication] = None) -> WheelGuard:
    """Install the guard on ``app`` (the running application by default).
    Idempotent: a second call returns the guard already installed."""
    global _guard
    app = app or QApplication.instance()
    if _guard is None:
        _guard = WheelGuard(app)
        app.installEventFilter(_guard)
    return _guard


def uninstall(app: Optional[QApplication] = None) -> None:
    """Remove the guard (tests that must leave the application as they
    found it)."""
    global _guard
    app = app or QApplication.instance()
    if _guard is not None and app is not None:
        app.removeEventFilter(_guard)
    _guard = None


def installed() -> bool:
    return _guard is not None
