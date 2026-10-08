# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.281 (D277) — through the project's door, the field at t = 0 of a
transient IS the steady analysis of the same model and conditions.

The defect: ``solve_project_groundwater`` solves the steady analysis with
w = 0.4, 200 Picard passes and tolerance 1e-5, while the transient solver
it builds runs with w = 0.5 and the transient tolerance, and its initial
steady state (``solve_transient`` without ``initial_head``) inherited those.
Where the Picard loop stops depends on w (D267), so the two fields differed
at the level of the tolerance and a user comparing them saw two "equal"
fields that were not.

What these tests protect:

* through the door (``solve_project_groundwater``), the transient's stage at
  t = 0 is the steady analysis TO THE BIT, on the rectangular Gardner dam of
  ``test_unsaturated_v127`` with a seepage face;
* the switch ``INITIAL_STEADY_FROM_DOOR`` moves the number (rule 7): off, the
  same comparison differs (by the tolerance, as measured);
* a solver built without ``steady_*`` settings keeps its own, as before
  (``test_transient_initial_state_v1270`` checks the t = 0 stage against
  ``solve_unsaturated`` on that same solver, and still passes).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

L, H, H1, H2 = 20.0, 12.0, 10.0, 2.0
K = 1.0e-5


def _dam(transient):
    """The rectangular Gardner dam as a PROJECT, meshed, with its
    conditions; a transient of two stages (0 and 1 h) under the same
    conditions when ``transient``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.settings import GroundwaterMethod
    from ogr_fem2d.mesh import generate_mesh_for_project
    from ogr_fem2d.solvers.seepage import BCType, SeepageBoundaryConditions
    p = Project("D277")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(L, 0), Vertex(L, H),
                             Vertex(0, H)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="dam", unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(
        ks=K, model=PermeabilityModel.GARDNER, gardner_a=1.0, gardner_n=3.0,
        wc_alpha=3.6, specific_storage=1e-4)
    p.materials = [m]
    p.fem_mesh = generate_mesh_for_project(p, target_size=0.7)
    mesh = p.fem_mesh
    b = SeepageBoundaryConditions()
    tol = 1e-6 * L      # the resolved regions quantise the coordinates
    for nid in sorted(mesh.boundary_node_ids()):
        x, y = mesh.nodes[nid].x, mesh.nodes[nid].y
        if abs(x) < tol:
            b.add_node(nid, BCType.TOTAL_HEAD if y <= H1 + tol
                       else BCType.UNKNOWN, H1)
        elif abs(x - L) < tol:
            b.add_node(nid, BCType.TOTAL_HEAD if y <= H2 + tol
                       else BCType.UNKNOWN, H2)
        elif abs(y - H) < tol:
            b.add_node(nid, BCType.UNKNOWN)
    p.seepage_bcs = b
    gw = p.settings.groundwater
    gw.method = GroundwaterMethod.FEA_STEADY.value
    if transient:
        gw.set_advanced_option("transient")
        gw.transient_time_steps = 2
        gw.transient_stages = [{"time": 0.0, "label": "t = 0"},
                               {"time": 3600.0, "label": "1 h"}]
    return p


def _steady_and_t0():
    from ogr_slip2d.transient_stability import solve_project_groundwater
    steady = solve_project_groundwater(_dam(False))
    stages = solve_project_groundwater(_dam(True))
    assert steady.converged
    assert stages[0].notes.get("initial_state_converged") is True
    return steady.total_head, stages[0].total_head


class TestTheFieldAtTimeZeroIsTheSteadyAnalysis:
    def test_to_the_bit(self):
        a, b = _steady_and_t0()
        assert a == b

    def test_the_switch_moves_it(self):
        import ogr_slip2d.transient_stability as ts
        old = ts.INITIAL_STEADY_FROM_DOOR
        ts.INITIAL_STEADY_FROM_DOOR = False
        try:
            a, b = _steady_and_t0()
        finally:
            ts.INITIAL_STEADY_FROM_DOOR = old
        assert a != b
        assert max(abs(x - y) for x, y in zip(a, b)) < 1e-2

    def test_the_door_has_one_set_of_steady_settings(self):
        import ogr_slip2d.transient_stability as ts
        assert (ts.STEADY_RELAXATION, ts.STEADY_MAX_ITERATIONS,
                ts.STEADY_TOLERANCE) == (0.4, 200, 1e-5)


class TestAScriptKeepsItsOwnSettings:
    def test_no_steady_settings_is_the_solvers_own(self):
        from ogr_fem2d.solvers.seepage import (TransientSeepageSolver,
                                               TransientStage)
        p = _dam(False)
        props = {m.id: m.hydraulic for m in p.materials}
        s = TransientSeepageSolver(p.fem_mesh, props, relaxation=0.5,
                                   tolerance=1e-5, time_steps=2)
        res = s.solve_transient([TransientStage(time=0.0, label="t = 0")],
                                initial_bcs=p.seepage_bcs)
        steady = s.solve_unsaturated(p.seepage_bcs)
        assert res[0].total_head == steady.total_head
