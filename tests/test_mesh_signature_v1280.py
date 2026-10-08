# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.280 (D284) — a stored finite-element mesh that is not a mesh of the
model is refused, not solved with the default hydraulic properties.

The defect: ``project.fem_mesh`` survived every edit but Generate and Reset.
Deleting a material (``material_delete`` with ``reassign_to``), redefining
the model (``model_define``) or the window's material dialog left elements
pointing to a material id the solver did not know, and
``SeepageSolver.props_for`` computed them with ``HydraulicProperties()``
(Constant, Ks 1e-6) without a word. Measured on a 20 x 10 box whose region
went from B (Ks 1e-7) to A (Ks 1e-5): 190 of 190 elements orphaned and the
discharge 3e-6 instead of A's 3e-5. And no geometry edit dropped the mesh
either: the canvas moves vertices in place, without notifying.

What these tests protect:

* ``rules.mesh_mismatch`` says why the mesh is not the model's: elements of
  a material that no longer exists (any mesh, also one saved before this
  version), or a fingerprint of the resolved regions stored at meshing that
  no longer matches (a moved vertex, a reassigned region);
* what does NOT change the meshed problem does not trip it: a new
  permeability, saving and loading the project;
* the three doors refuse: the API (``Conflict``), the engine
  (``solve_project_groundwater`` raises ``AnalysisNotConfigured``) and the
  window (a status-bar message, nothing computed);
* the solver, built directly, notes how many elements took the default
  properties;
* once the mesh is regenerated, the discharge is Darcy's for the material
  the region has: q = K (h1 - h2) / L * H (the closed form, rule 1).
"""
from __future__ import annotations

import atexit
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


SOIL = {"model": "mohr_coulomb",
        "params": {"cohesion": 5.0, "friction_angle": 30.0}}
L, H, H1, H2 = 20.0, 10.0, 8.0, 2.0
KS_A, KS_B = 1e-5, 1e-7
_WS = []


def _ws():
    if not _WS:
        from ogr_api import Workspace
        ws = Workspace()
        atexit.register(ws.shutdown)
        _WS.append(ws)
    return _WS[0]


def _box():
    """A 20 x 10 box, materials A and B, B painted on the region, both with
    hydraulic properties, meshed. Returns (ws, project id)."""
    from ogr_api import call
    ws = _ws()
    pid = call(ws, "project_new", name="D284")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, 0], [L, 0], [L, H], [0, H]],
        "materials": [{"name": "A", "unit_weight": 20, "strength": SOIL},
                      {"name": "B", "unit_weight": 20, "strength": SOIL}]})
    call(ws, "material_assign", project_id=pid, material="B", x=10, y=5)
    call(ws, "hydraulic_set", project_id=pid, material="A",
         properties={"ks": KS_A})
    call(ws, "hydraulic_set", project_id=pid, material="B",
         properties={"ks": KS_B})
    call(ws, "mesh_generate", project_id=pid, target_elements=200)
    return ws, pid


def _project(ws, pid):
    return ws.get(pid).project


def _why(project):
    from ogr_core.project.rules import mesh_mismatch
    return mesh_mismatch(project)


class TestWhatTripsIt:
    def test_a_fresh_mesh_is_the_models(self):
        ws, pid = _box()
        p = _project(ws, pid)
        assert p.fem_mesh.notes.get("model_signature")
        assert _why(p) is None

    def test_a_new_permeability_does_not(self):
        from ogr_api import call
        ws, pid = _box()
        call(ws, "hydraulic_set", project_id=pid, material="A",
             properties={"ks": 3e-5})
        assert _why(_project(ws, pid)) is None

    def test_saving_and_loading_does_not(self):
        from ogr_core.project import Project
        ws, pid = _box()
        path = os.path.join(tempfile.mkdtemp(prefix="ogr_d284_"), "m.ogr")
        _project(ws, pid).save(path)
        assert _why(Project.load(path)) is None

    def test_a_deleted_material(self):
        from ogr_api import call
        ws, pid = _box()
        call(ws, "material_delete", project_id=pid, material="B",
             reassign_to="A")
        why = _why(_project(ws, pid))
        assert why is not None and "no longer exists" in why, why

    def test_a_redefined_model(self):
        from ogr_api import call
        ws, pid = _box()
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [L, 0], [L, H], [0, H]],
            "materials": [{"name": "C", "unit_weight": 20,
                           "strength": SOIL}]})
        assert _why(_project(ws, pid)) is not None

    def test_a_region_painted_with_another_material(self):
        from ogr_api import call
        ws, pid = _box()
        call(ws, "material_assign", project_id=pid, material="A", x=10, y=5)
        why = _why(_project(ws, pid))
        assert why is not None and "another geometry" in why, why

    def test_a_vertex_moved_in_place(self):
        """As the canvas does it: no notification."""
        from ogr_core.geometry import Vertex
        ws, pid = _box()
        p = _project(ws, pid)
        verts = p.boundaries[0].polyline.vertices
        v = verts[2]
        verts[2] = Vertex(v.x, v.y + 0.5)
        assert _why(p) is not None

    def test_a_mesh_saved_before_this_version(self):
        """No fingerprint: only the orphan check, which still catches the
        deleted material."""
        from ogr_api import call
        ws, pid = _box()
        _project(ws, pid).fem_mesh.notes.pop("model_signature")
        assert _why(_project(ws, pid)) is None
        call(ws, "material_delete", project_id=pid, material="B",
             reassign_to="A")
        assert _why(_project(ws, pid)) is not None


class TestTheDoorsRefuse:
    def test_the_api(self):
        from ogr_api import Conflict, call
        ws, pid = _box()
        call(ws, "material_delete", project_id=pid, material="B",
             reassign_to="A")
        try:
            call(ws, "groundwater_run", project_id=pid)
        except Conflict as e:
            assert "Regenerate" in str(e)
        else:
            raise AssertionError("groundwater_run solved a mesh of "
                                 "another model")

    def test_the_engine(self):
        from ogr_api import call
        from ogr_slip2d.analysis_runner import AnalysisNotConfigured
        from ogr_slip2d.transient_stability import solve_project_groundwater
        ws, pid = _box()
        call(ws, "material_delete", project_id=pid, material="B",
             reassign_to="A")
        try:
            solve_project_groundwater(_project(ws, pid))
        except AnalysisNotConfigured as e:
            assert "Regenerate" in str(e)
        else:
            raise AssertionError("solve_project_groundwater solved it")


@_requires_qt
class TestTheWindowRefuses:
    def test_nothing_is_computed_and_it_says_why(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project.settings import GroundwaterMethod
        from test_gw_gui_v129 import _assign_head_bcs, _window
        QApplication.instance() or QApplication([])
        ws, pid = _box()
        p = _project(ws, pid)
        p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
        w = _window(p)
        _assign_head_bcs(w, p)
        verts = p.boundaries[0].polyline.vertices
        verts[2] = Vertex(verts[2].x, verts[2].y + 0.5)
        w._compute_groundwater()
        assert p.seepage_result is None
        assert "Regenerate" in w.statusBar().currentMessage()


# ---------------------------------------------------------------- solver
def _darcy_discharge(project, props):
    """Head H1 on the left edge and H2 on the right, saturated: the discharge
    through the box from the mean horizontal velocity (q = vx * H)."""
    from ogr_fem2d.solvers.seepage import (BCType, SeepageBoundaryConditions,
                                           SeepageSolver)
    mesh = project.fem_mesh
    b = SeepageBoundaryConditions()
    # 1e-6 L: the mesher's node registry quantises coordinates (the right
    # edge's nodes sit at x = 19.99999998)
    for i in mesh.boundary_node_ids():
        x = mesh.nodes[i].x
        if abs(x) < 1e-6 * L:
            b.add_node(i, BCType.TOTAL_HEAD, H1)
        elif abs(x - L) < 1e-6 * L:
            b.add_node(i, BCType.TOTAL_HEAD, H2)
    r = SeepageSolver(mesh, props).solve(b)
    vx = [v[0] for v in r.velocity]
    return H * sum(vx) / len(vx), r


class TestTheSolverSaysIt:
    def test_built_directly_with_a_mapping_that_misses_them(self):
        from ogr_api import call
        from ogr_fem2d.solvers import hydraulic_props_of
        ws, pid = _box()
        call(ws, "material_delete", project_id=pid, material="B",
             reassign_to="A")
        p = _project(ws, pid)
        q, r = _darcy_discharge(p, hydraulic_props_of(p))
        assert r.notes.get("default_props_elements") \
            == p.fem_mesh.element_count
        # the default Ks, 1e-6, and not A's
        # 1e-6 relative: the scale of the quantised coordinates
        assert abs(q - 1e-6 * (H1 - H2) / L * H) < 1e-6 * 1e-6

    def test_a_mapped_mesh_gets_no_note_and_darcys_discharge(self):
        """After regenerating, the region's material, A: q = K dh / L * H."""
        from ogr_api import call
        from ogr_fem2d.solvers import hydraulic_props_of
        ws, pid = _box()
        call(ws, "material_delete", project_id=pid, material="B",
             reassign_to="A")
        call(ws, "mesh_generate", project_id=pid, target_elements=200)
        p = _project(ws, pid)
        assert _why(p) is None
        q, r = _darcy_discharge(p, hydraulic_props_of(p))
        assert "default_props_elements" not in r.notes
        exact = KS_A * (H1 - H2) / L * H
        assert abs(q - exact) < 1e-6 * exact, (q, exact)
