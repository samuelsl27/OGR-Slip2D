# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.303 (D292) — materials, properties and groundwater are undo steps.

The first GUI test deleted a material in *Define Materials* and changed a
Ks in the hydraulic dialog; *Edit > Undo* then undid an agent's boundary
condition, because neither dialog left a step. This version takes the 13
methods of that family through ``_model_step`` (``@undo_step``), with the
names the API uses where the operation is the same:

=================================  =========================
Define Materials                   Define materials
Import Properties                  Import properties
Assign Water Surface               Assign water surface
right-click > Assign Material      Assign material
Define Tension Crack               Set tension crack
Define Hydraulic Properties        Hydraulic properties
Water Pressure Grid                Water pressure grid
Set Boundary Conditions            Set boundary conditions
Transient Groundwater              Transient groundwater
Generate / Reset FE Mesh           Generate FE mesh / Reset FE mesh
Compute Groundwater                Compute groundwater
=================================  =========================

The mesh and the computed field are steps with the heavy attributes, as in
the API (the owner's decision, 2026-10-12): undoing a computation gives
back the field that was there before it.

And an anomaly reported before fixing it: computing the groundwater never
marked the project modified — not from the window, not from an agent —
though the field is saved in the .ogr, so closing after a computation asked
nothing and lost it. A recorded step marks it now, and ``WindowHost.
after_edit`` does the same for an agent's edit.

For each site, through the window's method with its dialog replaced
(``_swap``, the idiom of ``test_f2_rules_v1196``): accepting leaves one
named step, undo gives back the model exactly (JSON), redo the accepted
one; cancelling leaves no step and the project as clean as it was. One test
mixes window steps with an agent's.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.is_dirty = False
    return w


def _clean(w):
    """The window as just opened: no steps, nothing to save."""
    w.command_stack.clear()
    w.project.is_dirty = False


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _accepted(w, name, act):
    """Run ``act`` (the user accepting the dialog): one step called
    ``name``; undo gives the model back, redo the accepted one."""
    before = _json(w.project)
    act()
    after = _json(w.project)
    assert after != before, name
    assert w.command_stack.history() == ([name], []), \
        w.command_stack.history()
    assert w.project.is_dirty, name
    w.act_undo()
    assert _json(w.project) == before, name
    w.act_redo()
    assert _json(w.project) == after, name


def _cancelled(w, act):
    before = _json(w.project)
    act()
    assert _json(w.project) == before
    assert w.command_stack.history() == ([], [])
    assert not w.project.is_dirty


def _int_box(value, ok=True):
    from PySide6.QtWidgets import QInputDialog
    return _swap(QInputDialog, "getInt",
                 staticmethod(lambda *a, **k: (value, ok)))


def _with_mesh(w, elements=80):
    with _int_box(elements):
        w._generate_fem_mesh()
    assert w.project.fem_mesh is not None
    _clean(w)


# ----------------------------------------------------------------------
class TestMaterialsAndProperties:
    def test_define_materials(self):
        import ogr_gui.main_window as mw
        real = mw.MaterialPropertiesDialog

        class _Accept(real):
            def exec(self):
                self.materials[0].unit_weight = 25.0
                return 1

        class _Cancel(real):
            def exec(self):
                self.materials[0].unit_weight = 26.0
                return 0

        w = _window()
        try:
            with _swap(mw, "MaterialPropertiesDialog", _Cancel):
                _cancelled(w, w.act_define_materials)
            with _swap(mw, "MaterialPropertiesDialog", _Accept):
                _accepted(w, "Define materials", w.act_define_materials)
        finally:
            _done(w)

    def test_import_properties(self):
        import tempfile

        from PySide6.QtWidgets import QFileDialog, QInputDialog
        from ogr_core.project.demo import build_demo_project
        other = build_demo_project()
        other.materials[0].name = "Imported clay"
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "other.ogr")
            other.save(path)
            w = _window()
            try:
                with _swap(QFileDialog, "getOpenFileName",
                           staticmethod(lambda *a, **k: (path, ""))):
                    with _swap(QInputDialog, "getItem",
                               staticmethod(lambda *a, **k: ("", False))):
                        _cancelled(w, w._import_properties)
                    with _swap(QInputDialog, "getItem",
                               staticmethod(lambda *a, **k: ("Materials",
                                                             True))):
                        _accepted(w, "Import properties",
                                  w._import_properties)
            finally:
                _done(w)

    def test_assign_water_surface(self):
        import ogr_gui.dialogs.assign_water_surface_dialog as aws
        w = _window()
        try:
            mat = w.project.materials[0]
            wid = mat.water_surface_id
            assert wid
            with _swap(aws.AssignWaterSurfaceDialog, "exec",
                       lambda self: 0):
                _cancelled(w, w.act_assign_water_surface)
            _accepted(w, "Assign water surface",
                      lambda: w.apply_water_surface_assignment(
                          wid, [], [mat.id]))
        finally:
            _done(w)

    def test_right_click_assign_material(self):
        from ogr_core.materials import Material, MohrCoulomb
        w = _window()
        try:
            rock = Material(name="Rock", unit_weight=24.0,
                            strength=MohrCoulomb(cohesion=50.0,
                                                 friction_angle=40.0))
            w.project.materials.append(rock)
            _clean(w)
            xmin, ymin, xmax, ymax = w.project.bounding_box()
            _accepted(w, "Assign material",
                      lambda: w._do_assign_material_at(
                          xmin + 0.1 * (xmax - xmin),
                          ymin + 0.05 * (ymax - ymin), rock.id))
        finally:
            _done(w)

    def test_define_tension_crack(self):
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                     WaterLevelMode)
        import ogr_gui.dialogs.tension_crack_dialog as tcd

        class _Fake:
            accept = 1

            def __init__(self, project, parent=None):
                pass

            def exec(self):
                return self.accept

            def result_properties(self):
                return TensionCrackProperties(mode=WaterLevelMode.DRY)

        class _No(_Fake):
            accept = 0

        w = _window()
        try:
            xmin, ymin, xmax, ymax = w.project.bounding_box()
            w.project.boundaries.append(Boundary(
                polyline=Polyline(vertices=[
                    Vertex(xmin, ymax - 2.0), Vertex(xmax, ymax - 2.0)],
                    closed=False),
                btype=BoundaryType.TENSION_CRACK))
            _clean(w)
            with _swap(tcd, "DefineTensionCrackDialog", _No):
                _cancelled(w, w.act_define_tension_crack)
            with _swap(tcd, "DefineTensionCrackDialog", _Fake):
                _accepted(w, "Set tension crack", w.act_define_tension_crack)
        finally:
            _done(w)


# ----------------------------------------------------------------------
class _Writer:
    """A dialog that writes the model on OK, as the real one does in its
    accept; ``write`` says what."""
    result = 1

    def __init__(self, *args, **kwargs):
        self.args = args

    def exec(self):
        if self.result:
            self.write(*self.args)
        return self.result

    def setParent(self, parent):  # noqa: N802 (Qt API)
        pass


class TestGroundwater:
    def test_hydraulic_properties(self):
        from ogr_core.hydraulic import HydraulicProperties
        import ogr_gui.dialogs.hydraulic_properties_dialog as hpd

        class _Ks(_Writer):
            def write(self, project, parent):
                project.materials[0].hydraulic = HydraulicProperties(
                    ks=3.5e-6)

        class _No(_Ks):
            result = 0

        w = _window()
        try:
            with _swap(hpd, "HydraulicPropertiesDialog", _No):
                _cancelled(w, w._define_hydraulic_properties)
            with _swap(hpd, "HydraulicPropertiesDialog", _Ks):
                _accepted(w, "Hydraulic properties",
                          w._define_hydraulic_properties)
        finally:
            _done(w)

    def test_water_pressure_grid(self):
        from ogr_core.hydraulic.water_pressure_grid import WaterPressureGrid
        import ogr_gui.dialogs.water_pressure_grid_dialog as wpg

        class _Grid(_Writer):
            def write(self, project, parent):
                project.water_pressure_grid = WaterPressureGrid(points=[
                    (0.0, 0.0, 10.0), (20.0, 0.0, 5.0), (0.0, 10.0, 1.0)])

        class _No(_Grid):
            result = 0

        w = _window()
        try:
            with _swap(wpg, "WaterPressureGridDialog", _No):
                _cancelled(w, w._edit_water_pressure_grid)
            with _swap(wpg, "WaterPressureGridDialog", _Grid):
                _accepted(w, "Water pressure grid",
                          w._edit_water_pressure_grid)
        finally:
            _done(w)

    def test_boundary_conditions(self):
        import ogr_gui.dialogs.boundary_conditions_dialog as bcd

        class _Ok(_Writer):
            def write(self, mesh, bcs, parent):
                pass                     # the window stores the copy

        class _No(_Ok):
            result = 0

        w = _window()
        try:
            _with_mesh(w)
            with _swap(bcd, "BoundaryConditionsDialog", _No):
                _cancelled(w, w._set_boundary_conditions)
            with _swap(bcd, "BoundaryConditionsDialog", _Ok):
                _accepted(w, "Set boundary conditions",
                          w._set_boundary_conditions)
        finally:
            _done(w)

    def test_transient_stages(self):
        import ogr_gui.dialogs.transient_stages_dialog as tsd

        class _Tol(_Writer):
            def write(self, settings, parent):
                settings.transient_tolerance = 0.0025

        class _No(_Tol):
            result = 0

        w = _window()
        try:
            with _swap(tsd, "TransientStagesDialog", _No):
                _cancelled(w, w._edit_transient_stages)
            with _swap(tsd, "TransientStagesDialog", _Tol):
                _accepted(w, "Transient groundwater",
                          w._edit_transient_stages)
        finally:
            _done(w)

    def test_generate_and_reset_the_mesh(self):
        w = _window()
        try:
            with _int_box(0, ok=False):
                _cancelled(w, w._generate_fem_mesh)
            with _int_box(80):
                _accepted(w, "Generate FE mesh", w._generate_fem_mesh)
            assert w.project.fem_mesh is not None
            _clean(w)
            _accepted(w, "Reset FE mesh", w._reset_fem_mesh)
            assert w.project.fem_mesh is None
        finally:
            _done(w)

    def test_compute_groundwater_is_a_step_and_marks_the_project(self):
        w = _window()
        try:
            _with_mesh(w)
            assert w.project.seepage_result is None
            _accepted(w, "Compute groundwater", w._compute_groundwater)
            assert w.project.seepage_result is not None
            w.act_undo()
            assert w.project.seepage_result is None
        finally:
            _done(w)

    def test_an_agent_field_marks_the_window_project(self):
        """The same anomaly by the other door: ``_finish_groundwater``
        writes the field through ``Workspace.mutate`` and notifies
        nothing; ``WindowHost.after_edit`` marks the project."""
        import copy

        from ogr_core.project.commands import HEAVY_ATTRS, LIGHT_ATTRS
        from ogr_gui.agent_bridge import AgentBridge
        w = _window()
        br = AgentBridge(w)
        try:
            _with_mesh(w)
            w._compute_groundwater()
            field = copy.deepcopy(w.project.seepage_result)
            w.act_undo()
            _clean(w)

            def write(project):
                project.seepage_result = copy.deepcopy(field)
            br.ws.mutate(br.host.handle_id, "Compute groundwater", write,
                         attrs=LIGHT_ATTRS + HEAVY_ATTRS)
            assert w.command_stack.history() == (["Compute groundwater"], [])
            assert w.project.is_dirty
        finally:
            br.ws.shutdown()
            _done(w)

    def test_with_an_agent_step_in_between(self):
        from ogr_api import call
        from ogr_gui.agent_bridge import AgentBridge
        w = _window()
        br = AgentBridge(w)
        try:
            s0 = _json(w.project)
            with _int_box(80):
                w._generate_fem_mesh()
            s1 = _json(w.project)
            call(br.ws, "settings_set", changes={"methods.num_slices": 31})
            s2 = _json(w.project)
            w._compute_groundwater()
            s3 = _json(w.project)
            assert w.command_stack.history()[0] == [
                "Generate FE mesh", "Change settings", "Compute groundwater"]
            for expected in (s2, s1, s0):
                w.act_undo()
                assert _json(w.project) == expected
            for expected in (s1, s2, s3):
                w.act_redo()
                assert _json(w.project) == expected
        finally:
            br.ws.shutdown()
            _done(w)
