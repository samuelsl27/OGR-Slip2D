# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Assign Water Surface — bulk assignment of one water surface to materials.

The per-material combo in the Define Materials dialog is the authoritative
place to set this. This dialog exists because assigning the same surface to
eight materials one at a time is the kind of chore that ends with someone
leaving half of them unassigned, silently falling back to "the first
surface of that type".

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from ogr_gui.i18n import tr


class AssignWaterSurfaceDialog(QDialog):
    """Pick one water surface and the materials that should refer to it.

    ``water_surfaces`` is a list of ``(boundary_id, label)`` and
    ``materials`` a list of ``(material_id, name, current_surface_id)``;
    neither the Project nor the Material class is needed here.
    """

    def __init__(
        self,
        water_surfaces: list[tuple[str, str]],
        materials: list[tuple[str, str, str | None]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Assign Water Surface"))
        self._materials = list(materials)

        root = QVBoxLayout(self)

        self.cbo_surface = QComboBox()
        for wid, label in water_surfaces:
            self.cbo_surface.addItem(label, wid)
        form = QFormLayout()
        form.addRow(tr("Water Surface:"), self.cbo_surface)
        root.addLayout(form)

        grp = QGroupBox(tr("Apply to materials"))
        vb = QVBoxLayout(grp)
        self.checks: list[QCheckBox] = []
        for mid, name, current in self._materials:
            cb = QCheckBox(name)
            # Pre-tick the materials already pointing at the selected
            # surface, so reopening the dialog shows the current state
            # instead of an empty form the user has to rebuild.
            cb.setChecked(current is not None
                          and current == self.cbo_surface.currentData())
            cb.setProperty("material_id", mid)
            self.checks.append(cb)
            vb.addWidget(cb)
        if not self.checks:
            vb.addWidget(QLabel(tr("This project has no materials yet.")))
        root.addWidget(grp)

        self.cbo_surface.currentIndexChanged.connect(self._retick)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    # ------------------------------------------------------------------
    def _retick(self, *_args) -> None:
        wid = self.cbo_surface.currentData()
        for cb, (_mid, _name, current) in zip(self.checks, self._materials):
            cb.setChecked(current is not None and current == wid)

    # ------------------------------------------------------------------
    def selected_surface_id(self) -> str | None:
        return self.cbo_surface.currentData()

    def selected_material_ids(self) -> list[str]:
        return [cb.property("material_id")
                for cb in self.checks if cb.isChecked()]

    def cleared_material_ids(self) -> list[str]:
        """Materials the user unticked — their assignment is removed.

        Returned separately from the ticked ones because "not selected"
        must not silently clear a material that points at a DIFFERENT
        surface; only the ones that pointed at this one are cleared.
        """
        wid = self.cbo_surface.currentData()
        out = []
        for cb, (mid, _name, current) in zip(self.checks, self._materials):
            if not cb.isChecked() and current == wid:
                out.append(mid)
        return out
