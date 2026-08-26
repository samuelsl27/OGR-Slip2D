# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Display Options dialog — master controller of the rendering scene graph.

Every checkbox/spinbox in this dialog is two-way bound to a field in
the canvas's :class:`DisplayOptions` dataclass. Changes propagate live
via the Apply button or on-change for toggles.

Layout:
    - Tab "General": boundary visibility, colours, line width,
      ruler/grid/grayscale, vertex display
    - Tab "Stress": mesh, node & element numbers (for future FEM
      overlay)
    - Tab "Water": water pressure grid, flow vectors, ponded water
    - Tab "Boundary Conditions": FEM BC visibility

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import fields, replace
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ogr_gui.canvas import DisplayOptions
from ogr_gui.i18n import tr


# ----------------------------------------------------------------------
class _ColorButton(QPushButton):
    color_changed = Signal(str)

    def __init__(self, hex_color: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(60, 22)
        self._hex = hex_color
        self._refresh()
        self.clicked.connect(self._pick)

    def hex(self) -> str:
        return self._hex

    def set_hex(self, h: str) -> None:
        self._hex = h
        self._refresh()

    def _refresh(self) -> None:
        self.setStyleSheet(
            f"background:{self._hex}; border:1px solid #666; border-radius:2px;"
        )
        self.setText("")

    def _pick(self) -> None:
        c = QColorDialog.getColor(QColor(self._hex), self, tr("Color"))
        if c.isValid():
            self._hex = c.name()
            self._refresh()
            self.color_changed.emit(self._hex)


# ----------------------------------------------------------------------
class DisplayOptionsDialog(QDialog):
    """Master display configuration dialog.

    Accepts the current :class:`DisplayOptions` and returns a new,
    modified instance via :meth:`result_options`.
    """

    options_applied = Signal(object)  # emits DisplayOptions on Apply / OK

    def __init__(self, options: DisplayOptions, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Display Options..."))
        self.resize(560, 480)
        self._opts = replace(options)  # shallow copy

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_general_tab(), tr("View"))
        self.tabs.addTab(self._build_stress_tab(), "Stress")
        self.tabs.addTab(self._build_water_tab(), "Water")
        self.tabs.addTab(self._build_bc_tab(), "Boundary Conditions")

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Apply
            | QDialogButtonBox.RestoreDefaults
            | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._defaults)
        root.addWidget(buttons)

    # ==================================================================
    # Tab: General (boundaries + miscellaneous)
    # ==================================================================
    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        root = QVBoxLayout(w)

        # --- Boundaries group -----------------------------------------
        bnd = QGroupBox(tr("Boundaries"))
        form = QFormLayout(bnd)

        self.chk_external = QCheckBox(tr("External Boundary"))
        self.chk_external.setChecked(self._opts.show_external)
        self.btn_color_external = _ColorButton(self._opts.color_external)

        self.chk_material = QCheckBox(tr("Material Boundary"))
        self.chk_material.setChecked(self._opts.show_material)
        self.btn_color_material = _ColorButton(self._opts.color_material)

        self.chk_water_table = QCheckBox(tr("Water Table"))
        self.chk_water_table.setChecked(self._opts.show_water_table)
        self.btn_color_wt = _ColorButton(self._opts.color_water_table)

        self.chk_piezo = QCheckBox(tr("Piezometric Line"))
        self.chk_piezo.setChecked(self._opts.show_piezometric)
        self.btn_color_piezo = _ColorButton(self._opts.color_piezometric)

        self.chk_crack = QCheckBox(tr("Tension Crack"))
        self.chk_crack.setChecked(self._opts.show_tension_crack)
        self.btn_color_crack = _ColorButton(self._opts.color_tension_crack)

        self.chk_weak_layer = QCheckBox(tr("Weak Layer"))
        self.chk_weak_layer.setChecked(self._opts.show_weak_layer)
        self.btn_color_weak_layer = _ColorButton(self._opts.color_weak_layer)

        self.chk_aniso = QCheckBox(tr("Anisotropic Surface"))
        self.chk_aniso.setChecked(self._opts.show_anisotropic_surface)
        self.btn_color_aniso = _ColorButton(
            self._opts.color_anisotropic_surface)

        for chk, btn, label in [
            (self.chk_external, self.btn_color_external, "External Boundary"),
            (self.chk_material, self.btn_color_material, "Material Boundary"),
            (self.chk_water_table, self.btn_color_wt, "Water Table"),
            (self.chk_piezo, self.btn_color_piezo, "Piezometric Line"),
            (self.chk_crack, self.btn_color_crack, "Tension Crack"),
            (self.chk_weak_layer, self.btn_color_weak_layer, "Weak Layer"),
            (self.chk_aniso, self.btn_color_aniso, "Anisotropic Surface"),
        ]:
            row = QHBoxLayout()
            row.addWidget(chk, 1)
            row.addWidget(QLabel(tr("Color") + ":"))
            row.addWidget(btn)
            container = QWidget()
            container.setLayout(row)
            form.addRow(container)

        self.chk_vertices = QCheckBox(tr("Show Boundary Vertices"))
        self.chk_vertices.setChecked(self._opts.show_boundary_vertices)
        form.addRow(self.chk_vertices)

        self.spn_line_width = QDoubleSpinBox()
        self.spn_line_width.setRange(0.1, 10.0)
        self.spn_line_width.setSingleStep(0.1)
        self.spn_line_width.setValue(self._opts.line_width)
        form.addRow(tr("Line Width:"), self.spn_line_width)

        root.addWidget(bnd)

        # --- Miscellaneous group --------------------------------------
        misc = QGroupBox(tr("Miscellaneous"))
        mform = QFormLayout(misc)

        self.chk_ruler = QCheckBox(tr("Show Ruler"))
        self.chk_ruler.setChecked(self._opts.show_ruler)
        self.chk_grid = QCheckBox(tr("Show Grid"))
        self.chk_grid.setChecked(self._opts.show_grid)
        self.chk_grayscale = QCheckBox(tr("Grayscale"))
        self.chk_grayscale.setChecked(self._opts.grayscale)
        self.chk_scale_items = QCheckBox(tr("Scale display items on zoom"))
        self.chk_scale_items.setChecked(self._opts.scale_display_items_on_zoom)
        self.chk_face_plates = QCheckBox(tr("Show support face plates and anchorage"))
        self.chk_face_plates.setChecked(self._opts.show_support_face_plates)
        self.chk_coord_last = QCheckBox(tr("Coordinates of last vertex"))
        self.chk_coord_last.setChecked(self._opts.show_coordinates_last_vertex)

        for cb in (self.chk_ruler, self.chk_grid, self.chk_grayscale,
                   self.chk_scale_items, self.chk_face_plates, self.chk_coord_last):
            mform.addRow(cb)
        root.addWidget(misc)

        root.addStretch(1)
        return w

    # ==================================================================
    # Tab: Stress (FEM mesh — placeholder until FEM2D module is in)
    # ==================================================================
    def _build_stress_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.chk_mesh = QCheckBox(tr("Discretizations (mesh edges)"))
        self.chk_mesh.setChecked(self._opts.show_mesh)
        self.chk_node_nums = QCheckBox(tr("Node Numbers"))
        self.chk_node_nums.setChecked(self._opts.show_node_numbers)
        self.chk_elem_nums = QCheckBox(tr("Element Numbers"))
        self.chk_elem_nums.setChecked(self._opts.show_element_numbers)

        for cb in (self.chk_mesh, self.chk_node_nums, self.chk_elem_nums):
            form.addRow(cb)

        note = QLabel(
            "<i>Mesh overlays activate once the OGR FEM2D module is available "
            "(planned v0.5.0). Settings here are persisted.</i>"
        )
        note.setWordWrap(True)
        form.addRow(note)
        return w

    # ==================================================================
    # Tab: Water
    # ==================================================================
    def _build_water_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.chk_u_grid = QCheckBox(tr("Water pressure grid values"))
        self.chk_u_grid.setChecked(self._opts.show_water_pressure_grid)
        self.chk_flow = QCheckBox(tr("Flow vectors"))
        self.chk_flow.setChecked(self._opts.show_flow_vectors)
        self.chk_ponded = QCheckBox(tr("Ponded water"))
        self.chk_ponded.setChecked(self._opts.show_ponded_water)
        self.chk_pond_fill = QCheckBox(tr("Fill"))
        self.chk_pond_fill.setChecked(self._opts.ponded_water_fill)
        self.chk_pond_hatch = QCheckBox(tr("Hatch pattern"))
        self.chk_pond_hatch.setChecked(self._opts.ponded_water_hatch)

        for cb in (self.chk_u_grid, self.chk_flow, self.chk_ponded,
                   self.chk_pond_fill, self.chk_pond_hatch):
            form.addRow(cb)
        return w

    # ==================================================================
    # Tab: Boundary conditions
    # ==================================================================
    def _build_bc_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.chk_bc = QCheckBox(tr("Boundary Conditions"))
        self.chk_bc.setChecked(self._opts.show_boundary_conditions)
        self.chk_bc_values = QCheckBox(tr("Boundary Condition Values"))
        self.chk_bc_values.setChecked(self._opts.show_boundary_condition_values)
        for cb in (self.chk_bc, self.chk_bc_values):
            form.addRow(cb)
        return w

    # ==================================================================
    # Apply / OK / Defaults
    # ==================================================================
    def _collect(self) -> DisplayOptions:
        o = self._opts
        o.show_external = self.chk_external.isChecked()
        o.color_external = self.btn_color_external.hex()
        o.show_material = self.chk_material.isChecked()
        o.color_material = self.btn_color_material.hex()
        o.show_water_table = self.chk_water_table.isChecked()
        o.color_water_table = self.btn_color_wt.hex()
        o.show_piezometric = self.chk_piezo.isChecked()
        o.color_piezometric = self.btn_color_piezo.hex()
        o.show_tension_crack = self.chk_crack.isChecked()
        o.color_tension_crack = self.btn_color_crack.hex()
        o.show_weak_layer = self.chk_weak_layer.isChecked()
        o.color_weak_layer = self.btn_color_weak_layer.hex()
        o.show_anisotropic_surface = self.chk_aniso.isChecked()
        o.color_anisotropic_surface = self.btn_color_aniso.hex()

        o.show_boundary_vertices = self.chk_vertices.isChecked()
        o.line_width = self.spn_line_width.value()

        o.show_ruler = self.chk_ruler.isChecked()
        o.show_grid = self.chk_grid.isChecked()
        o.grayscale = self.chk_grayscale.isChecked()
        o.scale_display_items_on_zoom = self.chk_scale_items.isChecked()
        o.show_support_face_plates = self.chk_face_plates.isChecked()
        o.show_coordinates_last_vertex = self.chk_coord_last.isChecked()

        o.show_mesh = self.chk_mesh.isChecked()
        o.show_node_numbers = self.chk_node_nums.isChecked()
        o.show_element_numbers = self.chk_elem_nums.isChecked()

        o.show_water_pressure_grid = self.chk_u_grid.isChecked()
        o.show_flow_vectors = self.chk_flow.isChecked()
        o.show_ponded_water = self.chk_ponded.isChecked()
        o.ponded_water_fill = self.chk_pond_fill.isChecked()
        o.ponded_water_hatch = self.chk_pond_hatch.isChecked()

        o.show_boundary_conditions = self.chk_bc.isChecked()
        o.show_boundary_condition_values = self.chk_bc_values.isChecked()

        return o

    def _apply(self) -> None:
        opts = self._collect()
        self.options_applied.emit(opts)

    def _ok(self) -> None:
        self._apply()
        self.accept()

    def _defaults(self) -> None:
        fresh = DisplayOptions()
        for f in fields(DisplayOptions):
            setattr(self._opts, f.name, getattr(fresh, f.name))

        self.chk_external.setChecked(fresh.show_external)
        self.btn_color_external.set_hex(fresh.color_external)
        self.chk_material.setChecked(fresh.show_material)
        self.btn_color_material.set_hex(fresh.color_material)
        self.chk_water_table.setChecked(fresh.show_water_table)
        self.btn_color_wt.set_hex(fresh.color_water_table)
        self.chk_piezo.setChecked(fresh.show_piezometric)
        self.btn_color_piezo.set_hex(fresh.color_piezometric)
        self.chk_crack.setChecked(fresh.show_tension_crack)
        self.btn_color_crack.set_hex(fresh.color_tension_crack)
        self.chk_weak_layer.setChecked(fresh.show_weak_layer)
        self.btn_color_weak_layer.set_hex(fresh.color_weak_layer)
        self.chk_aniso.setChecked(fresh.show_anisotropic_surface)
        self.btn_color_aniso.set_hex(fresh.color_anisotropic_surface)
        self.chk_vertices.setChecked(fresh.show_boundary_vertices)
        self.spn_line_width.setValue(fresh.line_width)
        self.chk_ruler.setChecked(fresh.show_ruler)
        self.chk_grid.setChecked(fresh.show_grid)
        self.chk_grayscale.setChecked(fresh.grayscale)
        self.chk_scale_items.setChecked(fresh.scale_display_items_on_zoom)
        self.chk_face_plates.setChecked(fresh.show_support_face_plates)
        self.chk_coord_last.setChecked(fresh.show_coordinates_last_vertex)
        self.chk_mesh.setChecked(fresh.show_mesh)
        self.chk_node_nums.setChecked(fresh.show_node_numbers)
        self.chk_elem_nums.setChecked(fresh.show_element_numbers)
        self.chk_u_grid.setChecked(fresh.show_water_pressure_grid)
        self.chk_flow.setChecked(fresh.show_flow_vectors)
        self.chk_ponded.setChecked(fresh.show_ponded_water)
        self.chk_pond_fill.setChecked(fresh.ponded_water_fill)
        self.chk_pond_hatch.setChecked(fresh.ponded_water_hatch)
        self.chk_bc.setChecked(fresh.show_boundary_conditions)
        self.chk_bc_values.setChecked(fresh.show_boundary_condition_values)

    def result_options(self) -> DisplayOptions:
        return self._collect()
