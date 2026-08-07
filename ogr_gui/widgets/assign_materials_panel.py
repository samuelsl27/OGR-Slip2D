# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Floating "Assign Materials" panel.

Workflow:
    1. User opens Properties → Assign Materials
    2. A floating panel appears with a list of all project materials,
       each with its colour swatch.
    3. User selects a material in the list → that material becomes
       the "active paint".
    4. Canvas enters ASSIGN_MATERIAL mode. Every click on a material
       region (or a closed material boundary) paints it with the
       active material.

Closing the panel returns the canvas to SELECT mode.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ogr_gui.i18n import tr  # noqa: E402


# ======================================================================
class AssignMaterialsPanel(QDockWidget):
    """Floating dock listing materials + paint picker."""

    material_selected = Signal(str)  # material_id (or empty string for none)
    closed_by_user = Signal()

    def __init__(self, materials: list, parent=None) -> None:
        super().__init__("Assign Materials", parent)
        self.setObjectName("AssignMaterialsDock")
        self.setAllowedAreas(
            Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea | Qt.BottomDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetClosable
        )

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(6, 6, 6, 6)

        hint = QLabel(
            "Pick a material below, then click on a region of the canvas\n"
            "to paint it.  Close this panel to exit.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 9pt; padding: 2px;")
        vbox.addWidget(hint)

        self.list = QListWidget()
        self.list.setIconSize(self.list.iconSize() * 1.2)
        for mat in materials:
            item = QListWidgetItem(mat.name)
            item.setData(Qt.UserRole, mat.id)
            # Colour swatch
            swatch = QPixmap(16, 16)
            swatch.fill(QColor(getattr(mat, "color", "#d4a373")))
            item.setIcon(QIcon(swatch))
            self.list.addItem(item)
        # "(None)" entry at the top for unassigning
        none_item = QListWidgetItem("(None — unassign)")
        none_item.setData(Qt.UserRole, "")
        self.list.insertItem(0, none_item)
        if self.list.count() > 1:
            self.list.setCurrentRow(1)  # first material by default
        self.list.itemSelectionChanged.connect(self._emit_selected)
        vbox.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        self.status = QLabel(tr("<i>No material selected</i>"))
        self.status.setStyleSheet("color: #555; font-size: 9pt;")
        btn_row.addWidget(self.status, 1)
        btn_close = QPushButton(tr("Close"))
        btn_close.clicked.connect(lambda: (self.closed_by_user.emit(),
                                             self.close()))
        btn_row.addWidget(btn_close)
        vbox.addLayout(btn_row)

        self.setWidget(container)
        self._emit_selected()

    def _emit_selected(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        mid = item.data(Qt.UserRole) or ""
        name = item.text()
        self.status.setText(f"Active: <b>{name}</b>")
        self.material_selected.emit(mid)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.closed_by_user.emit()
        super().closeEvent(event)
