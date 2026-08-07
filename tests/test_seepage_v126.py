# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.26 — Steady-state saturated seepage solver tests (Phase 2).

Validation is against **closed-form solutions**, so every number here has
an exact target rather than a regression snapshot:

    * 1D confined flow: H linear, flux = K.dH/L.height
    * Patch test with a fully anisotropic tensor (Kxy != 0): a constant
      head gradient must be reproduced exactly, and the Darcy velocity
      must equal -K.gradH exactly. This is the rigorous check of the
      tensor rotation plus the Galerkin assembly.
    * Layered media: harmonic mean for flow perpendicular to the layers,
      arithmetic mean for flow parallel to them.
    * Mass balance across sections, including across a 100x permeability
      contrast.
    * Infiltration: total inflow must equal total outflow.
    * Singular (pure Neumann) problems must be reported, not silently
      solved.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_core.geometry.regions import MaterialRegion  # noqa: E402
from ogr_core.hydraulic import HydraulicProperties  # noqa: E402
from ogr_fem2d.mesh import generate_mesh  # noqa: E402
from ogr_fem2d.solvers import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    SeepageSolver,
    default_boundary_conditions,
)


def _rect(x0, y0, x1, y1, mid="m"):
    return MaterialRegion(
        polygon=Polyline(vertices=[Vertex(x0, y0), Vertex(x1, y0),
                                   Vertex(x1, y1), Vertex(x0, y1)],
                         closed=True),
        material_id=mid)


def _box_mesh(L=20.0, H=10.0, h=1.2):
    return generate_mesh([_rect(0, 0, L, H)], target_size=h)


# ======================================================================
class TestConductivityTensor:
    def test_isotropic(self):
        kxx, kyy, kxy = HydraulicProperties(ks=1e-5).conductivity_tensor()
        assert abs(kxx - 1e-5) < 1e-20
        assert abs(kyy - 1e-5) < 1e-20
        assert abs(kxy) < 1e-20

    def test_anisotropic_axis_aligned(self):
        p = HydraulicProperties(ks=1e-4, k2_k1=0.25, k1_angle_deg=0.0)
        kxx, kyy, kxy = p.conductivity_tensor()
        assert abs(kxx - 1e-4) < 1e-18
        assert abs(kyy - 0.25e-4) < 1e-18
        assert abs(kxy) < 1e-18

    def test_rotated_90_swaps_axes(self):
        p = HydraulicProperties(ks=1e-4, k2_k1=0.25, k1_angle_deg=90.0)
        kxx, kyy, kxy = p.conductivity_tensor()
        assert abs(kxx - 0.25e-4) < 1e-18
        assert abs(kyy - 1e-4) < 1e-18

    def test_tensor_positive_definite(self):
        for ang in (0, 15, 30, 45, 60, 90, -30):
            for f in (0.05, 0.5, 1.0, 4.0):
                kxx, kyy, kxy = HydraulicProperties(
                    ks=1e-5, k2_k1=f, k1_angle_deg=ang
                ).conductivity_tensor()
                assert kxx > 0 and kyy > 0
                assert kxx * kyy - kxy * kxy > -1e-30

    def test_trace_invariant_under_rotation(self):
        base = None
        for ang in (0, 20, 45, 77, 90):
            kxx, kyy, _ = HydraulicProperties(
                ks=3e-5, k2_k1=0.3, k1_angle_deg=ang
            ).conductivity_tensor()
            if base is None:
                base = kxx + kyy
            assert abs((kxx + kyy) - base) < 1e-18

    def test_serialisation_round_trip(self):
        # v0.1.27 — the model field is now ``model``/PermeabilityModel;
        # ``unsaturated_model`` remains readable from v0.1.26 files (see
        # test_backwards_compatible_with_v0126_files in the Phase-3 suite).
        from ogr_core.hydraulic import PermeabilityModel
        p = HydraulicProperties(ks=2e-4, k2_k1=0.2, k1_angle_deg=33.0,
                                model=PermeabilityModel.SIMPLE)
        p2 = HydraulicProperties.from_dict(p.to_dict())
        assert abs(p2.ks - 2e-4) < 1e-20
        assert abs(p2.k2_k1 - 0.2) < 1e-12
        assert p2.model == PermeabilityModel.SIMPLE


# ======================================================================
class TestConfinedFlow1D:
    L, H, K = 20.0, 10.0, 1.0e-5
    H0, H1 = 10.0, 4.0

    def _solve(self, props=None):
        mesh = _box_mesh(self.L, self.H, 1.2)
        s = SeepageSolver(mesh, {"m": props or HydraulicProperties(ks=self.K)})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, self.H0)
            elif abs(nd.x - self.L) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, self.H1)
        return mesh, s, s.solve(b)

    def test_head_field_is_exact(self):
        """The FE solution of a linear field with linear elements is
        exact to machine precision."""
        mesh, _s, r = self._solve()
        assert r.ok
        for i, nd in enumerate(mesh.nodes):
            exact = self.H0 + (self.H1 - self.H0) * nd.x / self.L
            assert abs(r.total_head[i] - exact) < 1e-9, (i, nd.x)

    def test_flux_matches_darcy(self):
        _m, s, r = self._solve()
        q = abs(s.flux_through_segment(r, self.L / 2, 0.0,
                                       self.L / 2, self.H))
        exact = self.K * (self.H0 - self.H1) / self.L * self.H
        assert abs(q - exact) / exact < 1e-6, (q, exact)

    def test_mass_balance_across_sections(self):
        _m, s, r = self._solve()
        qs = [abs(s.flux_through_segment(r, x, 0.0, x, self.H))
              for x in (2.0, 6.0, 10.0, 14.0, 18.0)]
        assert (max(qs) - min(qs)) / max(qs) < 1e-6, qs

    def test_pressure_head_and_pore_pressure(self):
        mesh, _s, r = self._solve()
        for i, nd in enumerate(mesh.nodes):
            assert abs(r.pressure_head[i]
                       - (r.total_head[i] - nd.y)) < 1e-12
            assert abs(r.pore_pressure[i]
                       - 9.81 * r.pressure_head[i]) < 1e-9

    def test_normal_convention_documented(self):
        """Section normal is the tangent rotated +90 deg: reversing the
        section reverses the sign, magnitude unchanged."""
        _m, s, r = self._solve()
        a = s.flux_through_segment(r, 10.0, 0.0, 10.0, self.H)
        b = s.flux_through_segment(r, 10.0, self.H, 10.0, 0.0)
        assert abs(a + b) < 1e-12 * max(abs(a), 1e-30)
        assert a * b < 0


# ======================================================================
class TestAnisotropicPatchTest:
    """A constant head gradient H = A x + B y + C prescribed on the whole
    boundary must be reproduced exactly, with v = -K gradH exact too."""

    A, B, C = 0.3, 0.2, 5.0
    CASES = [
        HydraulicProperties(ks=1e-5),
        HydraulicProperties(ks=1e-5, k2_k1=0.25),
        HydraulicProperties(ks=1e-5, k2_k1=0.25, k1_angle_deg=45.0),
        HydraulicProperties(ks=2e-4, k2_k1=0.1, k1_angle_deg=30.0),
        HydraulicProperties(ks=5e-6, k2_k1=4.0, k1_angle_deg=-60.0),
    ]

    def _run(self, props):
        mesh = _box_mesh(20.0, 10.0, 1.2)
        s = SeepageSolver(mesh, {"m": props})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            b.add_node(nid, BCType.TOTAL_HEAD,
                       self.A * nd.x + self.B * nd.y + self.C)
        return mesh, s, s.solve(b)

    def test_heads_exact_for_all_tensors(self):
        for props in self.CASES:
            mesh, _s, r = self._run(props)
            assert r.ok
            for i, nd in enumerate(mesh.nodes):
                exact = self.A * nd.x + self.B * nd.y + self.C
                assert abs(r.total_head[i] - exact) < 1e-9, (props.ks, i)

    def test_velocities_exact_for_all_tensors(self):
        for props in self.CASES:
            _m, _s, r = self._run(props)
            kxx, kyy, kxy = props.conductivity_tensor()
            vx_ex = -(kxx * self.A + kxy * self.B)
            vy_ex = -(kxy * self.A + kyy * self.B)
            scale = max(abs(vx_ex), abs(vy_ex), 1e-30)
            for vx, vy in r.velocity:
                assert abs(vx - vx_ex) / scale < 1e-6
                assert abs(vy - vy_ex) / scale < 1e-6

    def test_gradient_magnitude(self):
        _m, _s, r = self._run(self.CASES[0])
        expected = math.hypot(self.A, self.B)
        for g in r.gradient:
            assert abs(g - expected) < 1e-9


# ======================================================================
class TestLayeredMedia:
    K1, K2 = 1.0e-4, 1.0e-6      # 100x contrast
    H0, H1 = 10.0, 4.0

    def _solve(self, regions, h=0.9):
        mesh = generate_mesh(regions, target_size=h)
        s = SeepageSolver(mesh, {"a": HydraulicProperties(ks=self.K1),
                                 "b": HydraulicProperties(ks=self.K2)})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, self.H0)
            elif abs(nd.x - 20.0) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, self.H1)
        return mesh, s, s.solve(b)

    def test_series_flow_harmonic_mean(self):
        """Flow perpendicular to two vertical layers → harmonic mean."""
        _m, s, r = self._solve([_rect(0, 0, 10, 10, "a"),
                                _rect(10, 0, 20, 10, "b")])
        q = abs(s.flux_through_segment(r, 5.0, 10.0, 5.0, 0.0))
        k_eq = 20.0 / (10.0 / self.K1 + 10.0 / self.K2)
        exact = k_eq * (self.H0 - self.H1) / 20.0 * 10.0
        assert abs(q - exact) / exact < 1e-4, (q, exact)

    def test_parallel_flow_arithmetic_mean(self):
        """Flow parallel to two horizontal layers → arithmetic mean."""
        _m, s, r = self._solve([_rect(0, 0, 20, 5, "a"),
                                _rect(0, 5, 20, 10, "b")])
        q = abs(s.flux_through_segment(r, 10.0, 10.0, 10.0, 0.0,
                                       samples=600))
        k_eq = (self.K1 * 5.0 + self.K2 * 5.0) / 10.0
        exact = k_eq * (self.H0 - self.H1) / 20.0 * 10.0
        assert abs(q - exact) / exact < 1e-3, (q, exact)

    def test_mass_balance_across_contrast_interface(self):
        _m, s, r = self._solve([_rect(0, 0, 10, 10, "a"),
                                _rect(10, 0, 20, 10, "b")])
        qs = [abs(s.flux_through_segment(r, x, 10.0, x, 0.0))
              for x in (2.0, 5.0, 9.0, 11.0, 15.0, 18.0)]
        assert (max(qs) - min(qs)) / max(qs) < 1e-4, qs

    def test_head_drop_concentrates_in_low_k_layer(self):
        """With a 100x contrast almost the whole head loss must occur in
        the low-permeability layer."""
        mesh, _s, r = self._solve([_rect(0, 0, 10, 10, "a"),
                                   _rect(10, 0, 20, 10, "b")])
        mid = [r.total_head[i] for i, nd in enumerate(mesh.nodes)
               if abs(nd.x - 10.0) < 1e-9]
        assert mid, "no interface nodes"
        h_mid = sum(mid) / len(mid)
        drop_a = self.H0 - h_mid
        drop_b = h_mid - self.H1
        assert drop_b > 90.0 * drop_a, (drop_a, drop_b)


# ======================================================================
class TestBoundaryConditionTypes:
    def test_pressure_head_equals_y_plus_hp(self):
        mesh = _box_mesh(10.0, 10.0, 1.5)
        s = SeepageSolver(mesh, {"m": HydraulicProperties(ks=1e-5)})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            b.add_node(nid, BCType.PRESSURE_HEAD, 3.0)
        r = s.solve(b)
        assert r.ok
        # H = y + 3 everywhere → pressure head 3 everywhere
        for ph in r.pressure_head:
            assert abs(ph - 3.0) < 1e-6

    def test_zero_pressure_gives_hydrostatic_head(self):
        mesh = _box_mesh(10.0, 10.0, 1.5)
        s = SeepageSolver(mesh, {"m": HydraulicProperties(ks=1e-5)})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            b.add_node(nid, BCType.ZERO_PRESSURE)
        r = s.solve(b)
        assert r.ok
        for i, nd in enumerate(mesh.nodes):
            assert abs(r.total_head[i] - nd.y) < 1e-6

    def test_infiltration_mass_balance(self):
        """Total infiltration in must equal total discharge out."""
        mesh = generate_mesh([_rect(0, 0, 10, 10)], target_size=0.8)
        s = SeepageSolver(mesh, {"m": HydraulicProperties(ks=1e-5)})
        q_inf = 2.0e-6
        b = SeepageBoundaryConditions()
        top = sorted([n for n in mesh.boundary_node_ids()
                      if abs(mesh.nodes[n].y - 10.0) < 1e-9],
                     key=lambda i: mesh.nodes[i].x)
        for nid in mesh.boundary_node_ids():
            if abs(mesh.nodes[nid].y) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, 0.0)
        for a, c in zip(top[:-1], top[1:]):
            b.add_segment(a, c, -q_inf)
        r = s.solve(b)
        assert r.ok
        q_out = abs(s.flux_through_segment(r, 0.0, 0.0, 10.0, 0.0,
                                          samples=400))
        assert abs(q_out - q_inf * 10.0) / (q_inf * 10.0) < 1e-3

    def test_nodal_flow_is_neumann(self):
        mesh = _box_mesh(10.0, 10.0, 2.0)
        s = SeepageSolver(mesh, {"m": HydraulicProperties(ks=1e-5)})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.y) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, 0.0)
            else:
                b.add_node(nid, BCType.NODAL_FLOW, 0.0)
        r = s.solve(b)
        assert r.ok
        # No source, no gradient → head equals the prescribed value
        assert max(abs(h) for h in r.total_head) < 1e-6

    def test_singular_problem_is_reported(self):
        mesh = _box_mesh(10.0, 10.0, 2.0)
        s = SeepageSolver(mesh, {"m": HydraulicProperties(ks=1e-5)})
        b = SeepageBoundaryConditions()
        b.add_node(0, BCType.NODAL_FLOW, 0.0)
        r = s.solve(b)
        assert not r.converged
        assert "singular" in r.notes.get("error", "").lower()

    def test_empty_mesh_reported(self):
        from ogr_fem2d.mesh import Mesh
        s = SeepageSolver(Mesh(), {})
        r = s.solve(SeepageBoundaryConditions())
        assert not r.converged

    def test_default_bcs_classify_boundary(self):
        mesh = _box_mesh(20.0, 10.0, 2.0)
        bcs = default_boundary_conditions(mesh)
        types = {b.bc_type for b in bcs.nodes}
        assert BCType.NODAL_FLOW in types
        # Every boundary node must receive exactly one condition
        assert len(bcs.nodes) == len(mesh.boundary_node_ids())

    def test_bcs_serialisation_round_trip(self):
        b = SeepageBoundaryConditions()
        b.add_node(3, BCType.TOTAL_HEAD, 12.5)
        b.add_node(4, BCType.UNKNOWN)
        b.add_segment(3, 4, -1e-6, seepage_face=True)
        b2 = SeepageBoundaryConditions.from_dict(b.to_dict())
        assert len(b2.nodes) == 2 and len(b2.segments) == 1
        assert b2.nodes[0].bc_type == BCType.TOTAL_HEAD
        assert abs(b2.nodes[0].value - 12.5) < 1e-12
        assert b2.segments[0].seepage_face is True

    def test_add_node_overwrites_previous(self):
        b = SeepageBoundaryConditions()
        b.add_node(7, BCType.TOTAL_HEAD, 1.0)
        b.add_node(7, BCType.TOTAL_HEAD, 2.0)
        assert len(b.nodes) == 1
        assert abs(b.nodes[0].value - 2.0) < 1e-12


# ======================================================================
class TestProjectIntegration:
    def test_material_hydraulic_round_trip(self):
        from ogr_core.materials import Material, MohrCoulomb
        m = Material(name="soil", strength=MohrCoulomb(cohesion=5,
                                                      friction_angle=30),
                     hydraulic=HydraulicProperties(ks=3e-5, k2_k1=0.4,
                                                   k1_angle_deg=12.0))
        m2 = Material.from_dict(m.to_dict())
        assert m2.hydraulic is not None
        assert abs(m2.hydraulic.ks - 3e-5) < 1e-20
        assert abs(m2.hydraulic.k1_angle_deg - 12.0) < 1e-12

    def test_material_without_hydraulic(self):
        from ogr_core.materials import Material, MohrCoulomb
        m = Material(name="s", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20))
        assert Material.from_dict(m.to_dict()).hydraulic is None

    def test_solve_project_reports_singular_with_defaults(self):
        """The default BCs alone are a pure-Neumann problem; the driver
        must say so instead of returning a bogus field."""
        from ogr_fem2d.solvers import solve_project_seepage
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        for m in p.materials:
            m.hydraulic = HydraulicProperties(ks=1e-6)
        r = solve_project_seepage(p, target_elements=250)
        assert not r.converged
        assert "singular" in r.notes.get("error", "").lower()

    def test_solve_project_with_head_bcs(self):
        """Reference slope with a head difference across the model."""
        from ogr_fem2d.solvers import (
            BCType as BT,
            SeepageBoundaryConditions as SBC,
            solve_project_seepage,
        )
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        for m in p.materials:
            m.hydraulic = HydraulicProperties(ks=1e-6)
        from ogr_fem2d.mesh import generate_mesh_for_project
        p.fem_mesh = generate_mesh_for_project(p, target_elements=400)
        mesh = p.fem_mesh
        xs = [mesh.nodes[i].x for i in mesh.boundary_node_ids()]
        x_min, x_max = min(xs), max(xs)
        bcs = SBC()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x - x_min) < 1e-6:
                bcs.add_node(nid, BT.TOTAL_HEAD, 40.0)
            elif abs(nd.x - x_max) < 1e-6:
                bcs.add_node(nid, BT.TOTAL_HEAD, 20.0)
        r = solve_project_seepage(p, bcs)
        assert r.ok
        # Heads must stay between the two prescribed values (maximum
        # principle for a pure diffusion problem)
        assert min(r.total_head) > 20.0 - 1e-6
        assert max(r.total_head) < 40.0 + 1e-6
