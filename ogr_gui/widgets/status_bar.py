# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Custom status bar with SNAP / GRID / ORTHO / OSNAP toggles, live
coordinate readout, and a manual (X, Y) entry field for typing exact
vertex positions during a boundary drawing (v0.1.3).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator, QMouseEvent, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStatusBar,
    QWidget,
)

from ogr_gui.i18n import tr


# ----------------------------------------------------------------------
class _ToggleLabel(QLabel):
    """A QLabel that acts like a toggle button."""
    toggled = Signal(bool)

    def __init__(self, text: str, active: bool = False, parent=None) -> None:
        super().__init__(text, parent)
        self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self._refresh()

    def isChecked(self) -> bool:  # noqa: N802
        return self._active

    def setChecked(self, v: bool) -> None:  # noqa: N802
        if v != self._active:
            self._active = v
            self._refresh()
            self.toggled.emit(self._active)

    def mousePressEvent(self, ev: QMouseEvent) -> None:  # noqa: N802
        self.setChecked(not self._active)

    def _refresh(self) -> None:
        # v0.1.316 (D301) — "on" paints its own background, so it reads on
        # either theme; "off" is text on the bar's, and asks the theme
        from ogr_gui.themes import theme_color
        self.setStyleSheet(
            "padding: 2px 8px; border-radius: 3px; "
            + ("background: #b9d7f7; color: #10305a; font-weight: 500;"
               if self._active else "background: transparent; color: %s;"
               % theme_color("toggle_off"))
        )


# ----------------------------------------------------------------------
class _CoordInput(QLineEdit):
    """Compact ``x, y`` entry field.

    On Enter, emits :attr:`coords_submitted(x, y)`. Accepts any of:
        - ``12.5, 3.2``
        - ``12.5 3.2``
        - ``12.5;3.2``
    """
    coords_submitted = Signal(float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("x, y")
        self.setMaximumWidth(130)
        self.setToolTip(
            tr("While drawing a boundary, type X,Y and press Enter to add\n"
            "that exact vertex to the in-progress polyline.")
        )
        # Accept a pair of signed floats separated by comma, space, or semicolon
        rx = QRegularExpression(r"^-?\d+(\.\d+)?\s*[,;\s]\s*-?\d+(\.\d+)?$")
        self.setValidator(QRegularExpressionValidator(rx, self))
        self.returnPressed.connect(self._submit)

    def _submit(self) -> None:
        txt = self.text().strip()
        if not txt:
            return
        parts = (txt.replace(";", ",").replace(",", " ")).split()
        if len(parts) != 2:
            return
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            return
        self.coords_submitted.emit(x, y)
        self.clear()


# ======================================================================
class ElidingStatusBar(QStatusBar):
    """A status bar whose message ends in «…» where its indicators begin,
    with the whole text as the bar's tooltip while it lasts (v0.1.328, D325).

    QStatusBar draws its message under whatever is permanent on the right,
    so the end of a long one was hidden behind SNAP / GRID / ORTHO / OSNAP:
    «… un método de agua por rejilla (…), que ader…». The text is cut to the
    room the indicators leave and cut again when the bar changes size,
    without restarting the message's time.

    ``currentMessage()`` answers the WHOLE message: what the window said,
    not what fitted. A message Qt shows by itself (an action's status tip,
    sent from C++) is not cut, and is answered as shown.
    """

    #: Room kept between the message and the first indicator, in pixels.
    GAP_PX = 8

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._full = ""
        self._shown = ""
        self._until: Optional[float] = None
        self.messageChanged.connect(self._on_message_changed)

    def showMessage(self, text: str, timeout: int = 0) -> None:  # noqa: N802
        self._full = text or ""
        self._until = (time.monotonic() + timeout / 1000.0
                       if timeout and timeout > 0 else None)
        self._show(timeout)

    def currentMessage(self) -> str:  # noqa: N802
        shown = super().currentMessage()
        if shown and shown == self._shown:
            return self._full
        return shown

    def clearMessage(self) -> None:  # noqa: N802
        self._full = self._shown = ""
        self._until = None
        self.setToolTip("")
        super().clearMessage()

    def message_room(self) -> int:
        """The width, in pixels, the message has left of the indicators."""
        right = self.width()
        for child in self.findChildren(QWidget, "", Qt.FindDirectChildrenOnly):
            if child.isVisible() and child.x() > 0:
                right = min(right, child.x())
        return right - self.GAP_PX

    def _show(self, timeout: int) -> None:
        text = self._full
        room = self.message_room()
        if self.isVisible() and room > 0:
            text = self.fontMetrics().elidedText(self._full, Qt.ElideRight,
                                                 room)
        self._shown = text
        self.setToolTip(self._full if text != self._full else "")
        super().showMessage(text, timeout)

    def _on_message_changed(self, text: str) -> None:
        if not text:
            # the message's time ran out, or another took its place
            self._full = self._shown = ""
            self._until = None
            self.setToolTip("")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self._full or super().currentMessage() != self._shown:
            return
        if self._until is None:
            self._show(0)
            return
        left = int((self._until - time.monotonic()) * 1000)
        if left > 0:
            self._show(left)


# ======================================================================
class OgrStatusBar(ElidingStatusBar):
    """Status bar: hint message + snap toggles + X/Y readout + manual input."""

    snap_toggled = Signal(bool)
    grid_toggled = Signal(bool)
    ortho_toggled = Signal(bool)
    osnap_toggled = Signal(bool)
    manual_coords_submitted = Signal(float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Coord readout
        self.coord_label = QLabel(tr("X: 0.000   Y: 0.000"))
        self.coord_label.setMinimumWidth(170)

        # Manual coord input
        self.coord_input = _CoordInput(self)
        self.coord_input.coords_submitted.connect(self.manual_coords_submitted.emit)

        # Toggle indicators
        self.snap = _ToggleLabel(tr("SNAP"), True)
        self.grid = _ToggleLabel(tr("GRID"), True)
        self.ortho = _ToggleLabel(tr("ORTHO"), False)
        self.osnap = _ToggleLabel(tr("OSNAP"), False)

        self.snap.toggled.connect(self.snap_toggled.emit)
        self.grid.toggled.connect(self.grid_toggled.emit)
        self.ortho.toggled.connect(self.ortho_toggled.emit)
        self.osnap.toggled.connect(self.osnap_toggled.emit)

        # Assemble — right side
        for w in (self.snap, self.grid, self.ortho, self.osnap):
            self.addPermanentWidget(w)
        self._extra_toggles: dict = {}
        self._sep = QLabel(" │ ")
        self.addPermanentWidget(self._sep)
        self.addPermanentWidget(self.coord_label)
        self.addPermanentWidget(QLabel("  "))  # spacer
        self.addPermanentWidget(QLabel(tr("Enter X,Y:")))
        self.addPermanentWidget(self.coord_input)
        self.retheme()

    # ------------------------------------------------------------------
    def retheme(self) -> None:
        """Colour the readout and the separator for the active theme, and
        the toggles that are off (v0.1.316, D301: #4a4a4a on the dark bar
        could hardly be read)."""
        from ogr_gui.themes import theme_color
        self.coord_label.setStyleSheet(
            "color: %s; font-family: monospace;" % theme_color("status_text"))
        self._sep.setStyleSheet("color: %s;" % theme_color("separator"))
        for t in (self.snap, self.grid, self.ortho, self.osnap,
                  *getattr(self, "_extra_toggles", {}).values()):
            t._refresh()

    def update_coords(self, x: float, y: float) -> None:
        self.coord_label.setText(f"X: {x:+.3f}   Y: {y:+.3f}")

    # ------------------------------------------------------------------
    def add_toggle(self, text: str, active: bool = False):
        """Add another clickable indicator to the status bar.

        v0.1.51 — the bar shipped with SNAP / GRID / ORTHO / OSNAP hard
        wired. DATA TIPS needed one too, and a later phase will want
        others, so the bar grows through this instead of by editing its
        constructor each time.
        """
        if not hasattr(self, "_extra_toggles"):
            self._extra_toggles = {}
        existing = self._extra_toggles.get(text)
        if existing is not None:
            return existing
        label = _ToggleLabel(text, active)
        self.addPermanentWidget(label)
        self._extra_toggles[text] = label
        return label

    def toggle(self, text: str):
        """An indicator added with :meth:`add_toggle`, or None."""
        return getattr(self, "_extra_toggles", {}).get(text)
