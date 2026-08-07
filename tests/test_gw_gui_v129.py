# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.29 — Groundwater GUI tests (Phase 5).

Covers the behaviour that the reverse-engineered specification in
``docs/INTERFAZ_AGUA_SUBTERRANEA.md`` singles out as important, i.e. the
rules that make the interface behave correctly rather than merely look
right:

* **hard dependencies** — hydraulic properties only with an FEA
  groundwater method; boundary conditions and compute only once a mesh
  exists; interpret only once a result exists;
* **conditional enabling inside the dialogs** — Ks disabled for User
  Defined, Pick only for models with a library, Value only for the BC
  types that take one, Seepage Face only for flow-type conditions, and
  Infiltration restricted to segments;
* **the full workflow** hydraulic properties → mesh → boundary
  conditions → compute → interpret;
* **invalidation** — regenerating or clearing the mesh must drop the
  stale boundary conditions and result.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _app():
    return QApplication.instance() or QApplication([])


def _fea_project(with_mesh=False, elements=140):
    from test_slide_validation_ej1 import _ej1_project
    from ogr_core.project.settings import GroundwaterMethod
    p = _ej1_project()
    p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
    if with_mesh:
        from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
        from ogr_fem2d.mesh import generate_mesh_for_project
        for m in p.materials:
            m.hydraulic = HydraulicProperties(
                ks=1e-5, model=PermeabilityModel.GARDNER,
                gardner_a=1.0, gardner_n=3.0)
        p.fem_mesh = generate_mesh_for_project(p, target_elements=elements)
    return p


def _assign_head_bcs(w, project, h_left=40.0, h_right=27.0):
    """Prescribe heads on the two vertical edges.

    Needed before computing: the DEFAULT boundary conditions are pure
    Neumann, so the problem is singular and the handler (correctly) pops
    a modal warning — which would block a headless test run.
    """
    from ogr_fem2d.solvers import BCType
    from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
    bcs = w._seepage_bcs()
    sides = boundary_sides(project.fem_mesh)
    for nid in sides["Left edge"]:
        bcs.add_node(nid, BCType.TOTAL_HEAD, h_left)
    for nid in sides["Right edge"]:
        bcs.add_node(nid, BCType.TOTAL_HEAD, h_right)
    project.seepage_bcs = bcs
    return bcs


def _window(project):
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.canvas.set_project(project)
    w.project = project
    w._update_groundwater_actions()
    return w


# ======================================================================
@_requires_qt
class TestMenuDependencies:
    def _state(self, w):
        return {k: w._actions[k].isEnabled()
                for k in ("gw_hydraulic", "gw_bcs", "gw_compute",
                          "gw_interpret")}

    def test_all_disabled_without_fea_method(self):
        _app()
        from test_slide_validation_ej1 import _ej1_project
        w = _window(_ej1_project())
        st = self._state(w)
        assert st["gw_hydraulic"] is False
        assert st["gw_bcs"] is False
        assert st["gw_compute"] is False

    def test_hydraulic_enabled_only_with_fea(self):
        _app()
        w = _window(_fea_project())
        st = self._state(w)
        assert st["gw_hydraulic"] is True
        # Still no mesh → everything downstream stays disabled
        assert st["gw_bcs"] is False
        assert st["gw_compute"] is False
        assert st["gw_interpret"] is False

    def test_bcs_and_compute_need_a_mesh(self):
        _app()
        w = _window(_fea_project(with_mesh=True))
        st = self._state(w)
        assert st["gw_bcs"] is True
        assert st["gw_compute"] is True
        assert st["gw_interpret"] is False

    def test_interpret_needs_a_result(self):
        _app()
        p = _fea_project(with_mesh=True)
        w = _window(p)
        _assign_head_bcs(w, p)      # otherwise the problem is singular
        w._compute_groundwater()
        w._update_groundwater_actions()
        assert p.seepage_result is not None
        assert p.seepage_result.converged, p.seepage_result.notes
        assert w._actions["gw_interpret"].isEnabled() is True

    def test_reset_mesh_invalidates_downstream(self):
        _app()
        p = _fea_project(with_mesh=True)
        w = _window(p)
        _assign_head_bcs(w, p)
        w._compute_groundwater()
        w._reset_fem_mesh()
        assert p.fem_mesh is None
        assert p.seepage_bcs is None
        assert p.seepage_result is None
        assert w._actions["gw_bcs"].isEnabled() is False


# ======================================================================
@_requires_qt
class TestHydraulicPropertiesDialog:
    def _dlg(self):
        _app()
        p = _fea_project()
        from ogr_gui.dialogs.hydraulic_properties_dialog import (
            HydraulicPropertiesDialog,
        )
        return p, HydraulicPropertiesDialog(p, None)

    def test_lists_every_material(self):
        p, d = self._dlg()
        assert d.list.count() == len(p.materials)

    def test_ks_disabled_for_user_defined(self):
        from ogr_core.hydraulic import PermeabilityModel
        _p, d = self._dlg()
        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.USER_DEFINED))
        assert d.sp_ks.isEnabled() is False
        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.GARDNER))
        assert d.sp_ks.isEnabled() is True

    def test_pick_only_for_models_with_library(self):
        from ogr_core.hydraulic import PermeabilityModel
        _p, d = self._dlg()
        for mdl, expected in (
            (PermeabilityModel.CONSTANT, False),
            (PermeabilityModel.SIMPLE, False),
            (PermeabilityModel.USER_DEFINED, False),
            (PermeabilityModel.VAN_GENUCHTEN, True),
            (PermeabilityModel.BROOKS_COREY, True),
            (PermeabilityModel.GARDNER, True),
            (PermeabilityModel.FREDLUND_XING, True),
        ):
            d.cbo_model.setCurrentIndex(d.cbo_model.findData(mdl))
            assert d.btn_pick.isEnabled() is expected, mdl

    def test_custom_m_gates_the_m_field(self):
        _p, d = self._dlg()
        assert d.sp_vg_m.isEnabled() is False
        d.chk_custom_m.setChecked(True)
        assert d.sp_vg_m.isEnabled() is True

    def test_edits_are_saved_on_accept(self):
        from ogr_core.hydraulic import PermeabilityModel
        p, d = self._dlg()
        d.cbo_model.setCurrentIndex(
            d.cbo_model.findData(PermeabilityModel.GARDNER))
        d.sp_ks.setValue(2.5e-5)
        d.sp_k2k1.setValue(0.4)
        d.sp_angle.setValue(15.0)
        d.sp_g_a.setValue(3.0)
        d._accept()
        h = p.materials[0].hydraulic
        assert h is not None
        assert abs(h.ks - 2.5e-5) < 1e-12
        assert abs(h.k2_k1 - 0.4) < 1e-9
        assert abs(h.k1_angle_deg - 15.0) < 1e-9
        assert h.model == PermeabilityModel.GARDNER

    def test_cancel_leaves_materials_untouched(self):
        p, d = self._dlg()
        before = p.materials[0].hydraulic
        d.sp_ks.setValue(9.9e-4)
        d.reject()
        assert p.materials[0].hydraulic is before

    def test_curve_available_for_plot(self):
        _p, d = self._dlg()
        d._store(0)
        curve = d._props[0].curve(psi_max=100.0, n=20)
        assert len(curve) == 21


# ======================================================================
@_requires_qt
class TestBoundaryConditionsDialog:
    def _dlg(self):
        _app()
        p = _fea_project(with_mesh=True)
        w = _window(p)
        bcs = w._seepage_bcs()
        from ogr_gui.dialogs.boundary_conditions_dialog import (
            BoundaryConditionsDialog,
        )
        return p, bcs, BoundaryConditionsDialog(p.fem_mesh, bcs, None)

    def test_sides_cover_every_boundary_node(self):
        from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
        _app()
        p = _fea_project(with_mesh=True)
        sides = boundary_sides(p.fem_mesh)
        total = sum(len(v) for v in sides.values())
        assert total == len(p.fem_mesh.boundary_node_ids())

    def test_value_enabled_only_when_needed(self):
        from ogr_fem2d.solvers import BCType
        _p, _b, d = self._dlg()
        for t, expected in (
            (BCType.TOTAL_HEAD, True),
            (BCType.PRESSURE_HEAD, True),
            (BCType.ZERO_PRESSURE, False),
            (BCType.NODAL_FLOW, True),
            (BCType.INFILTRATION, True),
            (BCType.UNKNOWN, False),
        ):
            d.cbo_type.setCurrentIndex(d.cbo_type.findData(t))
            assert d.sp_value.isEnabled() is expected, t

    def test_seepage_face_only_for_flow_conditions(self):
        from ogr_fem2d.solvers import BCType
        _p, _b, d = self._dlg()
        for t, expected in (
            (BCType.TOTAL_HEAD, False),
            (BCType.ZERO_PRESSURE, False),
            (BCType.NODAL_FLOW, True),
            (BCType.INFILTRATION, True),
        ):
            d.cbo_type.setCurrentIndex(d.cbo_type.findData(t))
            assert d.chk_seepage.isEnabled() is expected, t

    def test_infiltration_restricted_to_segments(self):
        from ogr_fem2d.solvers import BCType
        _p, _b, d = self._dlg()
        d.cbo_type.setCurrentIndex(
            d.cbo_type.findData(BCType.INFILTRATION))
        assert d.cbo_pick.isEnabled() is False
        assert d.cbo_pick.currentData() == "segments"
        d.cbo_type.setCurrentIndex(d.cbo_type.findData(BCType.TOTAL_HEAD))
        assert d.cbo_pick.isEnabled() is True

    def test_assign_sets_conditions(self):
        from ogr_fem2d.solvers import BCType
        _p, bcs, d = self._dlg()
        d.cbo_type.setCurrentIndex(d.cbo_type.findData(BCType.TOTAL_HEAD))
        d.sp_value.setValue(40.0)
        for i in range(d.list_sides.count()):
            if d.list_sides.item(i).data(32) == "Left edge":
                d.list_sides.setCurrentRow(i)
        d._assign()
        heads = [b for b in bcs.nodes if b.bc_type == BCType.TOTAL_HEAD]
        assert heads, "no head condition assigned"
        assert all(abs(b.value - 40.0) < 1e-9 for b in heads)

    def test_restore_defaults(self):
        from ogr_fem2d.solvers import BCType
        _p, bcs, d = self._dlg()
        d._defaults()
        types = {b.bc_type for b in bcs.nodes}
        assert BCType.NODAL_FLOW in types
        assert bcs.segments == []


# ======================================================================
@_requires_qt
class TestFullWorkflow:
    def test_end_to_end(self):
        """Hydraulic properties → mesh → boundary conditions → compute →
        interpret."""
        import matplotlib
        matplotlib.use("Agg")
        _app()
        from ogr_fem2d.solvers import BCType
        p = _fea_project(with_mesh=True, elements=160)
        w = _window(p)
        bcs = w._seepage_bcs()
        from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
        sides = boundary_sides(p.fem_mesh)
        for nid in sides["Left edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 40.0)
        for nid in sides["Right edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 27.0)
        p.seepage_bcs = bcs
        w._compute_groundwater()
        r = p.seepage_result
        assert r is not None and r.converged, (r.notes if r else None)
        assert min(r.pore_pressure) < 0.0, "no suction in the field"
        from ogr_gui.interpret_groundwater_window import (
            InterpretGroundwaterWindow,
        )
        iw = InterpretGroundwaterWindow(p, r, w._gw_solver, None)
        assert iw.cbo_field.count() == 3
        for i in range(3):
            iw.cbo_field.setCurrentIndex(i)
            iw._redraw()          # must not raise for any field
        assert "nodes" in iw.status.text()

    def test_compute_without_hydraulic_properties_uses_defaults(self):
        _app()
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_fem2d.solvers import BCType
        p = _fea_project()
        p.fem_mesh = generate_mesh_for_project(p, target_elements=120)
        w = _window(p)
        bcs = w._seepage_bcs()
        from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
        sides = boundary_sides(p.fem_mesh)
        for nid in sides["Left edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 40.0)
        for nid in sides["Right edge"]:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 27.0)
        p.seepage_bcs = bcs
        w._compute_groundwater()      # must not raise
        assert p.seepage_result is not None

    def test_boundary_conditions_survive_save_load(self):
        _app()
        from ogr_core.project import Project
        from ogr_fem2d.solvers import BCType
        p = _fea_project(with_mesh=True, elements=120)
        w = _window(p)
        bcs = w._seepage_bcs()
        bcs.add_node(0, BCType.TOTAL_HEAD, 12.5)
        p.seepage_bcs = bcs
        p2 = Project.from_dict(p.to_dict())
        assert p2.seepage_bcs is not None
        assert any(abs(b.value - 12.5) < 1e-9 for b in p2.seepage_bcs.nodes)


# ======================================================================
@_requires_qt
class TestMaterialDialogUnsaturatedFields:
    def test_fields_present_and_saved(self):
        _app()
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        p = _fea_project()
        d = MaterialPropertiesDialog(p.materials, None,
                                     gw_method="fea_steady")
        assert hasattr(d, "dsp_phi_b")
        assert hasattr(d, "dsp_aev")
        # Visible because the groundwater method is an FEA
        assert d.dsp_phi_b.isEnabled() is True

    def test_fields_hidden_without_fea(self):
        _app()
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        d = MaterialPropertiesDialog(p.materials, None, gw_method="none")
        assert d.dsp_phi_b.isEnabled() is False
