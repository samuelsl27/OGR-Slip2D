# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Colour scale legend and status indicators — Interpret phase I1.

Two widgets the post-processor specification calls for and the window
lacked:

**ColourScaleLegend** — the vertical colour bar that maps colour to
numeric value. It replaces a hand-written HTML table whose bands were
hard-coded, and which therefore said the same thing whatever the results
actually contained. Being generated from the live colour function means
the legend can never disagree with what is drawn on the canvas: both ask
the same object for the colour of a value.

**StatusIndicators** — the clickable SNAP / GRID / ORTHO / OSNAP and
DATA TIPS labels of the status bar, plus the coordinate read-out. The
specification is explicit that these must be **toggleable by clicking the
words**, not only from a dialog, and that the two routes stay in sync.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from ogr_gui.i18n import tr


class ColourScaleLegend(QWidget):
    """Vertical colour bar mapping colours to numeric values.

    The bar is drawn from a **colour function** rather than a fixed list
    of bands, so it always agrees with the canvas: whatever colours the
    result, colours the legend.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._vmin = 0.0
        self._vmax = 3.0
        self._title = tr("Factor of safety")
        self._colour_fn = None
        self._steps = 10
        self._decimals = 2
        self._scientific = False
        self._mark = None            # value to flag on the bar
        self.setMinimumWidth(96)
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    # ------------------------------------------------------------------
    def configure(self, vmin, vmax, colour_fn, title=None, steps=None,
                  decimals=None, scientific=None, mark=None) -> None:
        """Set the range and the colour function.

        ``colour_fn`` takes a value and returns anything QColor accepts.
        """
        if vmax <= vmin:
            vmax = vmin + 1.0
        self._vmin, self._vmax = float(vmin), float(vmax)
        self._colour_fn = colour_fn
        if title is not None:
            self._title = title
        if steps is not None:
            self._steps = max(2, int(steps))
        if decimals is not None:
            self._decimals = max(0, int(decimals))
        if scientific is not None:
            self._scientific = bool(scientific)
        self._mark = mark
        self.update()

    def value_range(self):
        return self._vmin, self._vmax

    def format_value(self, v: float) -> str:
        if self._scientific:
            return f"{v:.{self._decimals}e}"
        return f"{v:.{self._decimals}f}"

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()

        font = QFont(self.font())
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1.0))
        p.setFont(font)
        fm = p.fontMetrics()

        title_h = fm.height() + 4
        p.setPen(QPen(self.palette().windowText().color()))
        p.drawText(QRectF(0, 0, w, title_h), Qt.AlignLeft | Qt.AlignVCenter,
                   self._title)

        bar_w = 20
        top = title_h + 4
        bottom = h - 4
        bar = QRectF(2, top, bar_w, max(bottom - top, 10))

        if self._colour_fn is None:
            p.end()
            return

        # A gradient sampled from the same function the canvas uses, so a
        # non-linear colour map is reproduced faithfully instead of being
        # approximated by two end colours.
        grad = QLinearGradient(bar.left(), bar.bottom(),
                               bar.left(), bar.top())
        samples = 32
        for i in range(samples + 1):
            t = i / samples
            value = self._vmin + t * (self._vmax - self._vmin)
            try:
                grad.setColorAt(t, QColor(self._colour_fn(value)))
            except Exception:  # noqa: BLE001
                grad.setColorAt(t, QColor("#888888"))
        p.fillRect(bar, grad)
        p.setPen(QPen(QColor("#404040"), 1))
        p.drawRect(bar)

        # Tick labels
        for i in range(self._steps + 1):
            t = i / self._steps
            value = self._vmin + t * (self._vmax - self._vmin)
            y = bar.bottom() - t * bar.height()
            p.drawLine(int(bar.right()), int(y), int(bar.right()) + 4,
                       int(y))
            p.drawText(QRectF(bar.right() + 6, y - fm.height() / 2,
                              w - bar.right() - 8, fm.height()),
                       Qt.AlignLeft | Qt.AlignVCenter,
                       self.format_value(value))

        # Marker for a value of interest (the critical factor of safety)
        if self._mark is not None and self._vmax > self._vmin:
            t = (float(self._mark) - self._vmin) / (self._vmax - self._vmin)
            if 0.0 <= t <= 1.0:
                y = bar.bottom() - t * bar.height()
                p.setPen(QPen(QColor("#000000"), 2))
                p.drawLine(int(bar.left()) - 2, int(y),
                           int(bar.right()) + 2, int(y))
        p.end()


# ======================================================================
class ToggleLabel(QLabel):
    """A status-bar word that toggles a boolean when clicked."""

    toggled = Signal(bool)

    def __init__(self, text: str, state: bool = False, parent=None):
        super().__init__(parent)
        self._text = text
        self._state = bool(state)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("Click to toggle %s") % text)
        self._refresh()

    def _refresh(self) -> None:
        on = self._state
        self.setText(self._text)
        # Enabled reads solid, disabled reads greyed: the state must be
        # legible at a glance without reading the word twice.
        self.setStyleSheet(
            "QLabel { padding: 0 6px; font-weight: %s; color: %s; }"
            % ("bold" if on else "normal", "#202020" if on else "#909090"))

    def state(self) -> bool:
        return self._state

    def setState(self, on: bool) -> None:  # noqa: N802
        on = bool(on)
        if on == self._state:
            return
        self._state = on
        self._refresh()
        self.toggled.emit(on)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.setState(not self._state)
        super().mousePressEvent(event)


class StatusIndicators:
    """The status-bar cluster: coordinates plus the toggle words.

    Kept as a plain holder rather than a widget so a window can place the
    pieces where it wants while still driving them as one group.
    """

    NAMES = ("DATA TIPS", "SNAP", "GRID", "ORTHO", "OSNAP")

    def __init__(self, status_bar, initial=None) -> None:
        self.status_bar = status_bar
        initial = initial or {}
        self.coords = QLabel("X: 0.000   Y: 0.000")
        self.coords.setMinimumWidth(170)
        status_bar.addPermanentWidget(self.coords)
        self.labels: dict = {}
        for name in self.NAMES:
            lab = ToggleLabel(name, bool(initial.get(name, False)))
            status_bar.addPermanentWidget(lab)
            self.labels[name] = lab

    # ------------------------------------------------------------------
    def set_coordinates(self, x: float, y: float) -> None:
        self.coords.setText(f"X: {x:.3f}   Y: {y:.3f}")

    def state(self, name: str) -> bool:
        lab = self.labels.get(name)
        return bool(lab and lab.state())

    def set_state(self, name: str, on: bool) -> None:
        lab = self.labels.get(name)
        if lab is not None:
            lab.setState(on)

    def connect(self, name: str, slot) -> None:
        lab = self.labels.get(name)
        if lab is not None:
            lab.toggled.connect(slot)

    def states(self) -> dict:
        return {n: self.state(n) for n in self.NAMES}
