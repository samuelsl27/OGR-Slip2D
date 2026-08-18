# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Assigning a water surface to a material has to MOVE THE NUMBER.

WHAT INVARIANT THIS PROTECTS.

``Assign Water Surface`` wrote ``Material.water_surface_id`` and nothing
else, from v0.1.62 until v0.1.95. ``pore_pressure_at`` returns 0.0 out of

    if ppt == PorePressureType.NONE: return 0.0

BEFORE it ever reads that field, so ticking a material in the dialog
changed the project file and changed no result whatsoever. Measured on the
Ej_2 piezometric geometry: u at (0, 10) stayed at 0.000 kPa with the id
written, and became 196.200 kPa once ``pore_pressure`` was set too.

That is rule 7 — "ningún ajuste puede no hacer nada" — and it is the same
failure the design-standard partial factors had between v0.1.52 and
v0.1.57: configurable, stored, and never applied. The anchor here is
therefore not a captured factor of safety but the closed form the reference
documents,

    u = gamma_w * Hu * h

so the test says what the number must BE, not what it happened to be.

The second half of the file covers the dialog itself. Note what it does
NOT do: it never calls ``exec()``. A modal dialog opened in code a test
runs blocks forever without a screen, which is why the automatic prompt
sits behind ``MainWindow.PROMPT_ASSIGN_ON_DRAW`` — and why that switch is
itself tested.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

GAMMA_W = 9.81
_WINDOWS: list = []


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ======================================================================
def _project_with_piezo():
    """Flat-topped block with one piezometric line 10 m above the base.

    Deliberately simple: a horizontal piezo line makes ``u = gamma_w * h``
    exact, so the assertion is an identity and not a measurement.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(-10, 0), Vertex(60, 0), Vertex(60, 40), Vertex(-10, 40),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("assign")
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name="Material 1", unit_weight=20,
                 strength=MohrCoulomb(cohesion=10, friction_angle=30)),
        Material(name="Material 2", unit_weight=20,
                 strength=MohrCoulomb(cohesion=10, friction_angle=30)),
    ]
    piezo = Boundary(polyline=Polyline(
        vertices=[Vertex(-10, 30), Vertex(60, 30)], closed=False),
        btype=BoundaryType.PIEZOMETRIC)
    p.add_boundary(piezo)
    return p, piezo


def _window(project):
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    w.PROMPT_ASSIGN_ON_DRAW = False      # never pop a modal from a test
    w.project = project
    _WINDOWS.append(w)
    return w


def _u_at(project, material, x, y, ground=40.0):
    from ogr_core.geometry import Vertex
    from ogr_core.hydraulic.pore_pressure import pore_pressure_at
    return pore_pressure_at(project, Vertex(x, y), material,
                            ground_surface_y=ground)


# ======================================================================
class TestTheAssignmentMovesTheNumber:
    """Rule 7, with the closed form as the anchor."""

    def test_before_the_assignment_the_material_is_dry(self):
        p, _piezo = _project_with_piezo()
        assert _u_at(p, p.materials[0], 0.0, 20.0) == 0.0

    def test_assigning_makes_u_the_documented_closed_form(self):
        from ogr_core.materials import PorePressureType
        p, piezo = _project_with_piezo()
        w = _window(p)
        m1 = p.materials[0]
        w.apply_water_surface_assignment(piezo.id, [m1.id], [])
        # The piezo line is flat at y = 30, the point is at y = 20.
        assert math.isclose(_u_at(p, m1, 0.0, 20.0), 10.0 * GAMMA_W,
                            rel_tol=1e-12)
        assert m1.pore_pressure == PorePressureType.PIEZO_LINE
        assert m1.water_surface_id == piezo.id

    def test_writing_only_the_id_would_have_changed_nothing(self):
        """The defect itself, pinned so it cannot come back.

        Without this the test above could pass while the dialog handler
        quietly went back to writing one field: nothing else in the suite
        would notice.
        """
        p, piezo = _project_with_piezo()
        m1 = p.materials[0]
        m1.water_surface_id = piezo.id          # the pre-v0.1.95 behaviour
        assert _u_at(p, m1, 0.0, 20.0) == 0.0

    def test_an_untouched_material_stays_dry(self):
        p, piezo = _project_with_piezo()
        w = _window(p)
        w.apply_water_surface_assignment(piezo.id, [p.materials[0].id], [])
        assert _u_at(p, p.materials[1], 0.0, 20.0) == 0.0

    def test_unticking_puts_the_material_back_to_dry(self):
        from ogr_core.materials import PorePressureType
        p, piezo = _project_with_piezo()
        w = _window(p)
        m1 = p.materials[0]
        w.apply_water_surface_assignment(piezo.id, [m1.id], [])
        assert _u_at(p, m1, 0.0, 20.0) > 0.0
        w.apply_water_surface_assignment(piezo.id, [], [m1.id])
        assert m1.pore_pressure == PorePressureType.NONE
        assert m1.water_surface_id is None
        assert _u_at(p, m1, 0.0, 20.0) == 0.0

    def test_a_material_on_ru_keeps_its_own_model_when_cleared(self):
        """Unticking may not silently take over a model it never set.

        Ru, a constant and a finite-element field are pore-pressure models
        this dialog does not offer, so clearing a water-surface assignment
        must not reach in and reset them to NONE.
        """
        from ogr_core.materials import PorePressureType
        p, piezo = _project_with_piezo()
        w = _window(p)
        m2 = p.materials[1]
        m2.pore_pressure = PorePressureType.RU_COEFFICIENT
        m2.ru = 0.3
        w.apply_water_surface_assignment(piezo.id, [], [m2.id])
        assert m2.pore_pressure == PorePressureType.RU_COEFFICIENT

    def test_a_water_table_gets_the_water_table_model(self):
        """The model written follows the TYPE of the surface chosen."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import PorePressureType
        p, _piezo = _project_with_piezo()
        wt = Boundary(polyline=Polyline(
            vertices=[Vertex(-10, 25), Vertex(60, 25)], closed=False),
            btype=BoundaryType.WATER_TABLE)
        p.add_boundary(wt)
        w = _window(p)
        m1 = p.materials[0]
        w.apply_water_surface_assignment(wt.id, [m1.id], [])
        assert m1.pore_pressure == PorePressureType.WATER_TABLE
        assert math.isclose(_u_at(p, m1, 0.0, 20.0), 5.0 * GAMMA_W,
                            rel_tol=1e-12)


# ======================================================================
class TestTheDialog:
    """The panel itself — read as a table, written as a form."""

    def _dialog(self, project, piezo, preselect=None):
        from ogr_gui.dialogs.assign_water_surface_dialog import (
            AssignWaterSurfaceDialog,
        )
        _app()
        surfaces = [(piezo.id, "Piezometric Line 1")]
        mats = [(m.id, m.name, m.water_surface_id) for m in project.materials]
        return AssignWaterSurfaceDialog(surfaces, mats, None,
                                        preselect=preselect)

    def test_current_column_reports_none_when_unassigned(self):
        from PySide6.QtCore import Qt
        p, piezo = _project_with_piezo()
        dlg = self._dialog(p, piezo)
        assert dlg.table.rowCount() == 2
        for row in range(2):
            assert dlg.table.item(row, 0).checkState() == Qt.Unchecked
            assert dlg.table.item(row, 1).text() != ""

    def test_boxes_open_pre_ticked_to_the_current_state(self):
        from PySide6.QtCore import Qt
        p, piezo = _project_with_piezo()
        p.materials[0].water_surface_id = piezo.id
        dlg = self._dialog(p, piezo)
        assert dlg.table.item(0, 0).checkState() == Qt.Checked
        assert dlg.table.item(1, 0).checkState() == Qt.Unchecked

    def test_select_all_and_clear_all(self):
        p, piezo = _project_with_piezo()
        dlg = self._dialog(p, piezo)
        dlg._set_all(True)
        assert len(dlg.selected_material_ids()) == 2
        dlg._set_all(False)
        assert dlg.selected_material_ids() == []

    def test_only_materials_pointing_here_are_reported_as_cleared(self):
        """The rule that makes unticking safe."""
        p, piezo = _project_with_piezo()
        p.materials[0].water_surface_id = piezo.id
        p.materials[1].water_surface_id = "some-other-surface"
        dlg = self._dialog(p, piezo)
        dlg._set_all(False)
        assert dlg.cleared_material_ids() == [p.materials[0].id]

    def test_preselect_picks_the_boundary_just_drawn(self):
        p, piezo = _project_with_piezo()
        dlg = self._dialog(p, piezo, preselect=piezo.id)
        assert dlg.selected_surface_id() == piezo.id

    def test_the_title_names_the_surface(self):
        p, piezo = _project_with_piezo()
        dlg = self._dialog(p, piezo)
        assert "Piezometric Line 1" in dlg.windowTitle()


# ======================================================================
class TestTheAutomaticPrompt:
    """Drawing a water surface offers the assignment, and tests can stop it."""

    def test_the_switch_is_on_by_default(self):
        from ogr_gui.main_window import MainWindow
        assert MainWindow.PROMPT_ASSIGN_ON_DRAW is True

    def test_nothing_opens_when_the_switch_is_off(self):
        """The guard that keeps the suite from hanging on a modal."""
        p, piezo = _project_with_piezo()
        w = _window(p)                      # sets PROMPT_ASSIGN_ON_DRAW False
        opened = []
        w.act_assign_water_surface = lambda **kw: opened.append(kw)
        w._maybe_prompt_assign_water_surface(piezo)
        assert opened == []

    def test_a_water_surface_triggers_the_prompt(self):
        p, piezo = _project_with_piezo()
        w = _window(p)
        w.PROMPT_ASSIGN_ON_DRAW = True
        opened = []
        w.act_assign_water_surface = lambda **kw: opened.append(kw)
        w._maybe_prompt_assign_water_surface(piezo)
        assert opened == [{"preselect": piezo.id}]

    def test_a_material_boundary_does_not(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p, _piezo = _project_with_piezo()
        w = _window(p)
        w.PROMPT_ASSIGN_ON_DRAW = True
        opened = []
        w.act_assign_water_surface = lambda **kw: opened.append(kw)
        mat = Boundary(polyline=Polyline(
            vertices=[Vertex(0, 10), Vertex(50, 10)], closed=False),
            btype=BoundaryType.MATERIAL)
        w._maybe_prompt_assign_water_surface(mat)
        assert opened == []

    def test_no_materials_means_no_prompt(self):
        p, piezo = _project_with_piezo()
        p.materials = []
        w = _window(p)
        w.PROMPT_ASSIGN_ON_DRAW = True
        opened = []
        w.act_assign_water_surface = lambda **kw: opened.append(kw)
        w._maybe_prompt_assign_water_surface(piezo)
        assert opened == []
