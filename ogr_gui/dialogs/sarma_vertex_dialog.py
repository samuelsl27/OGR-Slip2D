# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The data of Sarma's method per vertex of a user's non-circular surface
(v0.1.465, D357): the angle of the face that rises from each interior
vertex, and its cohesion and friction angle, in a table.

One row per interior vertex (an end has no face). The coordinates are read
only; an empty cell is «no datum», and the face then takes the policy and
the face strength of Settings → Methods → Sarma. The cohesion is in the
project's units of stress. The data are checked by the one rule of the core
(``checked_vertex_data``): a value it refuses is said under the table and
the dialog stays open, so nothing invalid reaches the model.

A cell whose text was not edited keeps the stored value as it is: shown
with ``%g`` and in the user's units, re-read it would come back rounded or
converted, and OK without a change moved the data (the review of v0.1.465).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from PySide6.QtCore import Qt

from ogr_gui.i18n import tr


class _NotANumber:
    """A cell whose text is not a number: said, never stored."""

    def __init__(self, text: str) -> None:
        self.text = text


class SarmaVertexDialog(QDialog):
    """The table of angle, c and φ per interior vertex of ``polyline`` (a
    ``UserPolylineSurface``); :meth:`result_data` is what was accepted, in
    the model's units, as ``checked_vertex_data`` returns it."""

    def __init__(self, polyline, units=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Sarma Data per Vertex"))
        self._polyline = polyline
        self._result = None
        if units is None:
            # the model's own (SI), when no project's units are handed in
            from ogr_core.project.units import Units
            units = Units()
        self._system = units.get_system()
        from ogr_core.units.quantities import Quantity
        self._quantity = Quantity.SHEAR_STRENGTH
        c_unit = self._system.label_for(self._quantity)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr(
            "Leave a cell empty for no datum: the face then takes the angle "
            "policy and the face strength of Settings → Methods → Sarma. The "
            "angle is in degrees counter-clockwise from +x (90 is "
            "vertical); the cohesion and the friction angle go together.")))
        interior = list(polyline.points[1:-1])
        self.table = QTableWidget(len(interior), 5)
        self.table.setHorizontalHeaderLabels([
            "X", "Y", tr("Angle [°]"),
            tr("Cohesion [%s]") % c_unit, tr("Friction angle [°]")])
        data = getattr(polyline, "vertex_data", None) or {}
        #: ``{(row, col): (text shown, stored value)}``: what a cell nobody
        #: edited gives back
        self._shown = {}
        for r, (x, y) in enumerate(interior):
            for col, v in ((0, x), (1, y)):
                item = QTableWidgetItem("%g" % v)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, col, item)
            datum = data.get((x, y)) or {}
            for col, key in ((2, "angle"), (3, "c"), (4, "phi")):
                stored = datum.get(key)
                text = ""
                if stored is not None:
                    try:
                        shown = float(stored)
                        if key == "c":
                            shown = self._system.to_user(shown,
                                                         self._quantity)
                        text = "%g" % shown
                    except (TypeError, ValueError):
                        # a hand-edited file: shown as written, and the
                        # rule says why when OK is pressed
                        text = str(stored)
                self._shown[(r, col)] = (text, stored)
                self.table.setItem(r, col, QTableWidgetItem(text))
        lay.addWidget(self.table)
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #b00020;")
        lay.addWidget(self.lbl_error)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _cell(self, r: int, col: int):
        """The value of a cell in the model's units: the stored one when
        its text is the one shown, None when empty, else the number typed
        (the cohesion converted), or a ``_NotANumber``."""
        item = self.table.item(r, col)
        text = (item.text() if item is not None else "").strip()
        shown, stored = self._shown.get((r, col), (None, None))
        if shown is not None and text == shown:
            return stored
        if not text:
            return None
        try:
            value = float(text.replace(",", "."))
        except ValueError:
            return _NotANumber(text)
        if col == 3:
            value = self._system.from_user(value, self._quantity)
        return value

    def _accept(self) -> None:
        from ogr_core.geometry.user_polyline import (NotASurface,
                                                     checked_vertex_data)
        from ogr_gui.canvas.canvas_view import user_surface_refusal_text
        interior = list(self._polyline.points[1:-1])
        rows = []
        for r, (x, y) in enumerate(interior):
            angle, c, phi = (self._cell(r, col) for col in (2, 3, 4))
            for v in (angle, c, phi):
                if isinstance(v, _NotANumber):
                    self.lbl_error.setText(tr(
                        "Row {row}: «{text}» is not a number.").format(
                            row=r + 1, text=v.text))
                    return
            rows.append({"x": x, "y": y, "angle": angle, "c": c,
                         "phi": phi})
        try:
            self._result = checked_vertex_data(self._polyline.points, rows)
        except NotASurface as exc:
            # the rule's reason in the window's words, not the core's
            # English (the review of v0.1.465)
            self.lbl_error.setText(user_surface_refusal_text(exc))
            return
        self.accept()

    def result_data(self):
        """The accepted data (``checked_vertex_data``), or None."""
        return self._result
