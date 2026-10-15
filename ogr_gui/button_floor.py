# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.315 (D293) — the buttons of a dialog's button box are at least
100 px wide, and never narrower than their text.

The themes gave every ``QPushButton`` a ``min-width: 70px``. In a style
sheet that REPLACES the minimum the text asks for, so a layout short of
room squeezed buttons under their text: in Spanish the transient dialog
cut its four buttons ("Capturar condiciones actuales" got 144 of its
279 px), and with Qt's Spanish catalog "Restaurar los valores
predeterminados" got 220 of its 339 px in Display Options. A style sheet
cannot say "70 px or the text, whichever is wider", so the floor moved
here (the owner's decision, 2026-10-15): when a button of a
``QDialogButtonBox`` is polished it gets a minimum width of 100 px — the
70 of the old rule plus its 14 px padding on each side and its border —
or its own width, whichever is larger. OK and Cancel look as they did,
and no other button has a floor at all.

It acts only while one of the program's themes is the application's
style sheet, since the floor replaces a rule of the themes: a test that
puts the style sheet back leaves the filter installed and inert.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QPushButton

#: The width the themes' ``min-width: 70px`` gave a button: 70 of content,
#: 14 px of padding on each side and a 1 px border.
BOX_BUTTON_MIN_WIDTH = 100

_POLISH = QEvent.Type.Polish


class ButtonFloor(QObject):
    """The application-wide event filter of this module."""

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt API)
        if event.type() != _POLISH or not isinstance(obj, QPushButton):
            return False
        if not isinstance(obj.parent(), QDialogButtonBox):
            return False
        from ogr_gui.themes import THEMES
        app = QApplication.instance()
        if app is None or app.styleSheet() not in THEMES.values():
            return False
        obj.setMinimumWidth(max(BOX_BUTTON_MIN_WIDTH,
                                obj.sizeHint().width()))
        return False


_floor: Optional[ButtonFloor] = None


def install(app: Optional[QApplication] = None) -> ButtonFloor:
    """Install the floor on ``app`` (the running application by default).
    Idempotent: a second call returns the filter already installed."""
    global _floor
    app = app or QApplication.instance()
    if _floor is None:
        _floor = ButtonFloor(app)
        app.installEventFilter(_floor)
    return _floor
