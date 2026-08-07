# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Property tables — phase M3.

A read-only overview of the materials, the supports or the hydraulic
properties of the model, side by side in one grid.

**Read-only on purpose.** Editing happens in the dedicated dialogs, where
the validation lives; a second editing path would be a second place for
that validation to be forgotten. What a table is genuinely good at is
COMPARISON — spotting that one material has half the cohesion of its
neighbour, or that a support was left without a capacity — and that is
what this is for.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ogr_gui.i18n import tr


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return tr("yes") if value else tr("no")
    if isinstance(value, float):
        if value != 0.0 and abs(value) < 1e-3:
            return f"{value:.3e}"
        return f"{value:.4g}"
    return str(getattr(value, "value", value))


class PropertiesTableDialog(QDialog):
    """Materials, supports or hydraulic properties as a grid."""

    def __init__(self, project, what: str = "materials", parent=None):
        super().__init__(parent)
        self.project = project
        self.what = what
        self.is_empty = False
        self.empty_message = ""
        titles = {"materials": tr("Material Properties Table"),
                  "supports": tr("Support Properties Table"),
                  "hydraulic": tr("Hydraulic Properties Table")}
        self.setWindowTitle(titles.get(what, tr("Properties")))
        self.resize(900, 480)

        headers, rows = self._collect()
        if not rows:
            self.is_empty = True
            self.empty_message = {
                "materials": tr("No materials are defined."),
                "supports": tr("No supports are defined."),
                "hydraulic": tr(
                    "No material has hydraulic properties. Define them "
                    "in Groundwater → Define Hydraulic Properties."),
            }.get(what, tr("Nothing to show."))
            return

        v = QVBoxLayout(self)
        self.table = QTableWidget(len(rows), len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(_fmt(value))
                if isinstance(value, (int, float)) and \
                        not isinstance(value, bool):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        v.addWidget(self.table, 1)

        note = QLabel(tr(
            "Read-only: edit in the dedicated dialogs, where the "
            "validation lives. Click a column header to sort and compare."))
        note.setWordWrap(True)
        v.addWidget(note)

        btn_copy = QPushButton(tr("Copy to clipboard"))
        btn_copy.clicked.connect(self._copy)
        v.addWidget(btn_copy)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    # ------------------------------------------------------------------
    def _collect(self):
        if self.what == "materials":
            return self._materials()
        if self.what == "supports":
            return self._supports()
        return self._hydraulic()

    def _materials(self):
        mats = list(getattr(self.project, "materials", []))
        if not mats:
            return [], []
        # The union of every strength parameter in use, so materials with
        # different models still line up in one comparable grid.
        params: list = []
        for m in mats:
            for k in (getattr(m.strength, "params", {}) or {}):
                if k not in params:
                    params.append(k)
        headers = [tr("Name"), tr("Strength model"), tr("Unit weight"),
                   tr("Saturated"), tr("Pore pressure")] + \
            [p.replace("_", " ") for p in params]
        rows = []
        for m in mats:
            st = m.strength
            model = (getattr(st, "DISPLAY_NAME", None)
                     or getattr(st, "MODEL_ID", "")) if st else ""
            row = [m.name, model, getattr(m, "unit_weight", None),
                   getattr(m, "sat_unit_weight", None),
                   getattr(m, "pore_pressure", None)]
            row += [(getattr(st, "params", {}) or {}).get(p)
                    for p in params]
            rows.append(row)
        return headers, rows

    def _supports(self):
        sups = list(getattr(self.project, "supports", []))
        if not sups:
            return [], []
        params: list = []
        for s in sups:
            stype = getattr(s, "support_type", None) or s
            for k in (getattr(stype, "PARAMETERS", {}) or {}):
                if k not in params:
                    params.append(k)
        headers = [tr("#"), tr("Type"), tr("Head"), tr("Tail")] + \
            [p.replace("_", " ") for p in params]
        rows = []
        for i, s in enumerate(sups, 1):
            stype = getattr(s, "support_type", None) or s
            head = getattr(s, "head", None)
            tail = getattr(s, "tail", None)
            row = [i,
                   getattr(stype, "DISPLAY_NAME", None)
                   or getattr(stype, "TYPE_ID", ""),
                   f"({head.x:.3f}, {head.y:.3f})" if head else "—",
                   f"({tail.x:.3f}, {tail.y:.3f})" if tail else "—"]
            row += [getattr(stype, p, None) for p in params]
            rows.append(row)
        return headers, rows

    def _hydraulic(self):
        mats = [m for m in getattr(self.project, "materials", [])
                if getattr(m, "hydraulic", None) is not None]
        if not mats:
            return [], []
        headers = [tr("Name"), "Ks", "K2/K1", tr("K1 angle"),
                   tr("Model"), tr("Saturated water content"),
                   tr("Specific storage")]
        rows = []
        for m in mats:
            h = m.hydraulic
            rows.append([m.name, h.ks, h.k2_k1, h.k1_angle_deg,
                         getattr(h.model, "value", h.model),
                         h.wc_sat, h.specific_storage])
        return headers, rows

    # ------------------------------------------------------------------
    def as_text(self) -> str:
        """Tab-separated text, ready to paste into a spreadsheet."""
        headers, rows = self._collect()
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(_fmt(v) for v in row))
        return "\n".join(lines)

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.as_text())
        self.setWindowTitle(self.windowTitle().rstrip(" ✓") + " ✓")
