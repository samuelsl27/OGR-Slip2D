# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Assign Water Surface — bulk assignment of one water surface to materials.

The per-material combo in the Define Materials dialog is the authoritative
place to set this. This dialog exists because assigning the same surface to
eight materials one at a time is the kind of chore that ends with someone
leaving half of them unassigned, silently falling back to "the first
surface of that type". The reference keeps both doors open too, and its
documentation is explicit that this one "is simply a shortcut".

v0.1.95 — three changes, and one of them is the whole point:

* the dialog now shows the **current** water surface of every material, as
  the reference's panel does, so it can be read as a status table and not
  only written as a form;
* *Select All* / *Clear All*, because the chore this exists to remove gets
  worse with twenty materials;
* it is opened AUTOMATICALLY after a water table or a piezometric line is
  drawn — which is what the reference does, and the reason a user ever
  finds it.

**One deliberate difference from the reference, stated because it is a
behavioural difference and not a cosmetic one.** The reference's panel
notes that "assignment for unchecked materials will not be changed": there,
unticking is inert and removing an assignment is done in Define Materials.
Here the boxes open PRE-TICKED to the current state, so the dialog shows
what is true, and unticking a material that points at THIS surface removes
its assignment. Materials pointing at a DIFFERENT surface are never
touched, which is what makes that safe — see :meth:`cleared_material_ids`.
The label at the bottom says so, rather than repeating the reference's
sentence, which would be false here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ogr_gui.i18n import tr


class AssignWaterSurfaceDialog(QDialog):
    """Pick one water surface and the materials that should refer to it.

    ``water_surfaces`` is a list of ``(boundary_id, label)`` and
    ``materials`` a list of ``(material_id, name, current_surface_id)``;
    neither the Project nor the Material class is needed here. The optional
    ``preselect`` is the boundary id to start on — used when the dialog is
    opened straight after drawing that boundary.
    """

    def __init__(
        self,
        water_surfaces: list[tuple[str, str]],
        materials: list[tuple[str, str, str | None]],
        parent=None,
        preselect: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._materials = list(materials)
        #: id -> label, so the "current" column can name a surface the user
        #: is not looking at right now.
        self._labels = {wid: label for wid, label in water_surfaces}

        root = QVBoxLayout(self)

        self.cbo_surface = QComboBox()
        for wid, label in water_surfaces:
            self.cbo_surface.addItem(label, wid)
        if preselect is not None:
            idx = self.cbo_surface.findData(preselect)
            if idx >= 0:
                self.cbo_surface.setCurrentIndex(idx)
        form = QFormLayout()
        form.addRow(tr("Water Surface:"), self.cbo_surface)
        root.addLayout(form)

        buttons_row = QHBoxLayout()
        self.btn_all = QPushButton(tr("Select All"))
        self.btn_none = QPushButton(tr("Clear All"))
        buttons_row.addWidget(self.btn_all)
        buttons_row.addWidget(self.btn_none)
        buttons_row.addStretch(1)
        root.addLayout(buttons_row)

        # A table rather than a column of checkboxes: the second column is
        # the reason this dialog can be read as well as written.
        self.table = QTableWidget(len(self._materials), 2, self)
        self.table.setHorizontalHeaderLabels(
            [tr("Material"), tr("Current Water Surface")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        for row, (mid, name, _current) in enumerate(self._materials):
            item = QTableWidgetItem(name)
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setData(Qt.UserRole, mid)
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem(""))
        root.addWidget(self.table)

        if not self._materials:
            root.addWidget(QLabel(tr("This project has no materials yet.")))

        self.lbl_note = QLabel(tr(
            "Unticking a material removes its assignment to this surface. "
            "Materials assigned to a different water surface are not "
            "changed."))
        self.lbl_note.setWordWrap(True)
        root.addWidget(self.lbl_note)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self.cbo_surface.currentIndexChanged.connect(self._retick)
        self.btn_all.clicked.connect(lambda: self._set_all(True))
        self.btn_none.clicked.connect(lambda: self._set_all(False))
        self._retick()
        self.setWindowTitle(self._title())

    # ------------------------------------------------------------------
    def _title(self) -> str:
        """"Assign <this surface> to Materials", as the reference titles it."""
        label = self.cbo_surface.currentText()
        if not label:
            return tr("Assign Water Surface")
        return "%s %s" % (tr("Assign to Materials:"), label)

    # ------------------------------------------------------------------
    def _set_all(self, on: bool) -> None:
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(
                Qt.Checked if on else Qt.Unchecked)

    # ------------------------------------------------------------------
    def _retick(self, *_args) -> None:
        """Re-read the current state for the surface now selected.

        Called on every combo change, so switching surfaces shows the truth
        about the new one instead of carrying the previous one's ticks over.
        """
        wid = self.cbo_surface.currentData()
        for row, (_mid, _name, current) in enumerate(self._materials):
            item = self.table.item(row, 0)
            item.setCheckState(
                Qt.Checked if (current is not None and current == wid)
                else Qt.Unchecked)
            self.table.item(row, 1).setText(
                self._labels.get(current, tr("None")) if current
                else tr("None"))
        self.setWindowTitle(self._title())

    # ------------------------------------------------------------------
    def selected_surface_id(self) -> str | None:
        return self.cbo_surface.currentData()

    def selected_material_ids(self) -> list[str]:
        return [self.table.item(row, 0).data(Qt.UserRole)
                for row in range(self.table.rowCount())
                if self.table.item(row, 0).checkState() == Qt.Checked]

    def cleared_material_ids(self) -> list[str]:
        """Materials the user unticked — their assignment is removed.

        Returned separately from the ticked ones because "not selected"
        must not silently clear a material that points at a DIFFERENT
        surface; only the ones that pointed at this one are cleared.
        """
        wid = self.cbo_surface.currentData()
        out = []
        for row, (mid, _name, current) in enumerate(self._materials):
            if (self.table.item(row, 0).checkState() != Qt.Checked
                    and current == wid):
                out.append(mid)
        return out
