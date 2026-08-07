# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
DXF export dialog — the mirror of the import dialog.

Same shape as its counterpart: the user chooses units and what to
include, sees a summary of what will be written, and confirms.

The one thing worth explaining in the interface is the **layer naming
contract**, because it is what makes the drawing useful rather than just
pretty:

* model geometry goes to the layers the importer recognises, so the
  drawing can be edited in CAD and brought back;
* everything that is a drawing *of results* — loads, mesh, slip surface,
  annotations — goes to ``OGR_X_`` layers that the importer ignores, so
  re-importing cannot turn a load arrow into a material boundary.

The dialog says so directly, rather than leaving the user to discover it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from ogr_core.dxf import BOUNDARY_TO_LAYER, ExportOptions
from ogr_gui.i18n import tr


class DxfExportDialog(QDialog):
    """Choose what to write to a DXF drawing."""

    def __init__(self, project, has_results: bool = False, parent=None):
        super().__init__(parent)
        self.project = project
        self.options = ExportOptions()
        self.setWindowTitle(tr("Export DXF"))
        self.resize(560, 560)

        v = QVBoxLayout(self)

        gb_u = QGroupBox(tr("Units"))
        fu = QFormLayout(gb_u)
        self.cbo_unit = QComboBox()
        for name in ("m", "cm", "mm", "km", "ft", "in"):
            self.cbo_unit.addItem(name, name)
        self.cbo_unit.setToolTip(tr(
            "The model is in metres; coordinates are converted to this "
            "unit and recorded in the file header."))
        fu.addRow(tr("Write coordinates in:"), self.cbo_unit)
        v.addWidget(gb_u)

        gb_c = QGroupBox(tr("Contents"))
        fc = QVBoxLayout(gb_c)
        self.chk_boundaries = QCheckBox(tr("Boundaries (geometry)"))
        self.chk_boundaries.setChecked(True)
        self.chk_supports = QCheckBox(tr("Supports"))
        self.chk_supports.setChecked(True)
        self.chk_loads = QCheckBox(tr("Loads (as arrows)"))
        self.chk_loads.setChecked(True)
        self.chk_mesh = QCheckBox(tr("Finite element mesh"))
        self.chk_mesh.setChecked(False)
        self.chk_mesh.setToolTip(tr(
            "Off by default: a mesh writes one line per element edge, "
            "which can be thousands of entities."))
        self.chk_surface = QCheckBox(tr("Critical slip surface"))
        self.chk_surface.setChecked(True)
        self.chk_annotations = QCheckBox(
            tr("Annotations (title, factor of safety)"))
        self.chk_annotations.setChecked(True)
        for w in (self.chk_boundaries, self.chk_supports, self.chk_loads,
                  self.chk_mesh, self.chk_surface, self.chk_annotations):
            fc.addWidget(w)
        v.addWidget(gb_c)

        self.sp_arrow = QDoubleSpinBox()
        self.sp_arrow.setDecimals(2)
        self.sp_arrow.setRange(0.1, 20.0)
        self.sp_arrow.setValue(2.0)
        self.sp_arrow.setSuffix(" %")
        self.sp_arrow.setToolTip(tr(
            "Length of the load arrows, as a percentage of the model "
            "diagonal, so they stay legible at any model size."))
        gb_a = QGroupBox(tr("Appearance"))
        fa = QFormLayout(gb_a)
        fa.addRow(tr("Load arrow size:"), self.sp_arrow)
        v.addWidget(gb_a)

        # Availability reflects the model, so nothing offered is empty
        self.chk_supports.setEnabled(
            bool(getattr(project, "supports", [])))
        self.chk_loads.setEnabled(
            bool(getattr(project, "distributed_loads", []))
            or bool(getattr(project, "line_loads", [])))
        self.chk_mesh.setEnabled(
            getattr(project, "fem_mesh", None) is not None)
        self.chk_surface.setEnabled(bool(has_results))
        for w in (self.chk_supports, self.chk_loads, self.chk_mesh,
                  self.chk_surface):
            if not w.isEnabled():
                w.setChecked(False)

        note = QLabel(tr(
            "Model geometry is written to the layers the importer "
            "recognises (%s), so the drawing can be edited in CAD and "
            "imported back. Results — loads, mesh, slip surface and "
            "annotations — go to separate OGR_X_ layers that the importer "
            "ignores, so re-importing cannot turn a load arrow into a "
            "material boundary.")
            % ", ".join(sorted(set(BOUNDARY_TO_LAYER.values()))))
        note.setWordWrap(True)
        v.addWidget(note)
        v.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Export"))
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    # ------------------------------------------------------------------
    def _collect(self) -> ExportOptions:
        return ExportOptions(
            unit=self.cbo_unit.currentData(),
            boundaries=self.chk_boundaries.isChecked(),
            supports=self.chk_supports.isChecked(),
            loads=self.chk_loads.isChecked(),
            mesh=self.chk_mesh.isChecked(),
            slip_surface=self.chk_surface.isChecked(),
            annotations=self.chk_annotations.isChecked(),
            arrow_pct=self.sp_arrow.value(),
        )

    def _accept(self) -> None:
        self.options = self._collect()
        self.accept()
