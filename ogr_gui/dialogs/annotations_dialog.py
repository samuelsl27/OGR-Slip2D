# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Annotation manager — phase M3.

Lists the annotation layer and offers the object operations the drawing
tools need: visibility, Z-order, duplicate, delete, and copying one
object's appearance onto others.

The list is the only place the annotation layer is manipulated in bulk,
which keeps those operations in one implementation rather than scattered
across the tool handlers.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ogr_gui.i18n import tr


class AnnotationsDialog(QDialog):
    """Manage the annotation layer."""

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle(tr("Annotations"))
        self.resize(720, 440)

        v = QVBoxLayout(self)
        v.addWidget(QLabel(tr(
            "Annotations are drawn on the model but take no part in the "
            "analysis. Use Convert Tool to Boundary to turn one into "
            "geometry.")))

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [tr("Type"), tr("Points"), tr("Text"), tr("Z"),
             tr("Visible")])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.table, 1)

        row = QHBoxLayout()
        for label, slot in ((tr("Toggle visible"), self._toggle),
                            (tr("Bring to front"), self._front),
                            (tr("Send to back"), self._back),
                            (tr("Duplicate"), self._duplicate),
                            (tr("Copy style to others"), self._copy_style),
                            (tr("Delete"), self._delete)):
            b = QPushButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        v.addLayout(row)

        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.table.setRowCount(0)
        for ann in self.layer.ordered():
            r = self.table.rowCount()
            self.table.insertRow(r)
            cells = [ann.kind.value, str(len(ann.points)), ann.text,
                     str(ann.z_order),
                     tr("yes") if ann.style.visible else tr("no")]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.UserRole, ann.id)
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()

    def _selected_id(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        item = self.table.item(r, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_ids(self):
        ids = []
        for idx in self.table.selectionModel().selectedRows() \
                if self.table.selectionModel() else []:
            item = self.table.item(idx.row(), 0)
            if item:
                ids.append(item.data(Qt.UserRole))
        return ids or ([self._selected_id()] if self._selected_id()
                       else [])

    # ------------------------------------------------------------------
    def _toggle(self) -> None:
        aid = self._selected_id()
        ann = self.layer.get(aid) if aid else None
        if ann is not None:
            ann.style.visible = not ann.style.visible
            self.refresh()

    def _front(self) -> None:
        aid = self._selected_id()
        if aid and self.layer.bring_to_front(aid):
            self.refresh()

    def _back(self) -> None:
        aid = self._selected_id()
        if aid and self.layer.send_to_back(aid):
            self.refresh()

    def _duplicate(self) -> None:
        aid = self._selected_id()
        if not aid:
            return
        # Offset so the copy is visible instead of hiding exactly behind
        # the original.
        ann = self.layer.get(aid)
        span = 1.0
        bb = ann.bbox() if ann else None
        if bb:
            span = max(bb[2] - bb[0], bb[3] - bb[1], 1.0) * 0.1
        self.layer.duplicate(aid, span, -span)
        self.refresh()

    def _copy_style(self) -> None:
        ids = self._selected_ids()
        if len(ids) < 2:
            return
        self.layer.copy_style(ids[0], ids[1:])
        self.refresh()

    def _delete(self) -> None:
        for aid in self._selected_ids():
            self.layer.remove(aid)
        self.refresh()
