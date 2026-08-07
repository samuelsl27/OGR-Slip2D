# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.27 — Unsaturated seepage + seepage face tests (Phase 3).

Validation strategy
-------------------
* **k(psi) models** — analytic limits and shape properties of each of the
  six reference models (kr(0) = 1, monotone decay, clamping, and for the
  Simple/General type the documented one-order-of-magnitude drop).
* **Charnyi / Dupuit convergence** — for flow through a rectangular dam
  on an impervious base the discharge is *exactly*
  q = K(H1^2 - H2^2) / (2L) when the zone above the free surface does not
  conduct. Our unsaturated formulation lets that zone conduct, so the
  discharge is legitimately higher; making k(psi) progressively sharper
  must drive it monotonically to the analytic value. That convergence is
  the rigorous test: it validates the solver *and* explains the excess.
* **Seepage face** — the free surface must exit the downstream face
  ABOVE the tailwater level (the defining feature of a seepage face), the
  reaction sign convention is asserted explicitly, and the Picard
  iteration must converge without the active set chattering.
* **Backwards compatibility** — a v0.1.26 model file (with
  ``unsaturated_model: "saturated"``) must load as CONSTANT and reproduce
  the Phase-2 linear result.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_core.geometry.regions import MaterialRegion  # noqa: E402
from ogr_core.hydraulic import (  # noqa: E402
    HydraulicProperties,
    PermeabilityModel,
    SimpleSoilType,
    available_models,
    library_for,
)
from ogr_fem2d.mesh import generate_mesh  # noqa: E402
from ogr_fem2d.solvers import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    SeepageSolver,
    UnsaturatedSeepageSolver,
)

L_DAM, H_DAM, K_DAM = 20.0, 12.0, 1.0e-5
H1, H2 = 10.0, 2.0


def _dam_mesh(h=0.6):
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(L_DAM, 0),
                              Vertex(L_DAM, H_DAM), Vertex(0, H_DAM)],
                    closed=True)
    return generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=h)


def _dam_bcs(mesh):
    """Upstream head H1, downstream head H2, impervious base, and
    Unknown (potential seepage face) on the crest and above the water
    levels on both faces."""
    b = SeepageBoundaryConditions()
    for nid in sorted(mesh.boundary_node_ids()):
        nd = mesh.nodes[nid]
        if abs(nd.x) < 1e-9:
            if nd.y <= H1 + 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, H1)
            else:
                b.add_node(nid, BCType.UNKNOWN)
        elif abs(nd.x - L_DAM) < 1e-9:
            if nd.y <= H2 + 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, H2)
            else:
                b.add_node(nid, BCType.UNKNOWN)
        elif abs(nd.y - H_DAM) < 1e-9:
            b.add_node(nid, BCType.UNKNOWN)
        else:
            b.add_node(nid, BCType.NODAL_FLOW, 0.0)
    return b


# ======================================================================
class TestPermeabilityModels:
    ALL = [PermeabilityModel.CONSTANT, PermeabilityModel.SIMPLE,
           PermeabilityModel.BROOKS_COREY,
           PermeabilityModel.FREDLUND_XING, PermeabilityModel.GARDNER,
           PermeabilityModel.VAN_GENUCHTEN]

    def test_all_reference_models_available(self):
        avail = available_models()
        for m in self.ALL:
            assert m in avail, m
        assert PermeabilityModel.USER_DEFINED in avail

    def test_saturated_limit_is_one(self):
        for m in self.ALL:
            p = HydraulicProperties(ks=1e-5, model=m)
            assert abs(p.relative_permeability(0.0) - 1.0) < 1e-12, m
            assert abs(p.relative_permeability(-5.0) - 1.0) < 1e-12, m

    def test_monotone_non_increasing(self):
        for m in self.ALL:
            p = HydraulicProperties(ks=1e-5, model=m)
            prev = 1.0
            for psi in (0.5, 1, 2, 5, 10, 50, 100, 500, 1000):
                kr = p.relative_permeability(psi)
                assert kr <= prev + 1e-12, (m, psi)
                prev = kr

    def test_bounded_between_kr_min_and_one(self):
        for m in self.ALL:
            p = HydraulicProperties(ks=1e-5, model=m, kr_min=1e-7)
            for psi in (0, 1, 100, 1e4, 1e6):
                kr = p.relative_permeability(psi)
                assert 1e-7 - 1e-15 <= kr <= 1.0, (m, psi, kr)

    def test_simple_general_drops_one_decade_then_flat(self):
        """Documented behaviour: the Simple/General curve falls by one
        order of magnitude over the initial suction range and then stays
        constant."""
        p = HydraulicProperties(ks=1e-5, model=PermeabilityModel.SIMPLE,
                                simple_soil_type=SimpleSoilType.GENERAL)
        assert abs(p.relative_permeability(100.0) - 0.1) < 1e-9
        assert abs(p.relative_permeability(5000.0) - 0.1) < 1e-9

    def test_simple_soil_types_ordered_by_texture(self):
        """Sand must desaturate at lower suction than clay."""
        sand = HydraulicProperties(model=PermeabilityModel.SIMPLE,
                                   simple_soil_type=SimpleSoilType.SAND)
        clay = HydraulicProperties(model=PermeabilityModel.SIMPLE,
                                   simple_soil_type=SimpleSoilType.CLAY)
        assert sand.relative_permeability(20.0) < clay.relative_permeability(20.0)

    def test_brooks_corey_saturated_below_bubbling_pressure(self):
        p = HydraulicProperties(model=PermeabilityModel.BROOKS_COREY,
                                bc_psi_b=30.0, bc_lambda=0.6)
        assert abs(p.relative_permeability(10.0) - 1.0) < 1e-12
        assert abs(p.relative_permeability(29.9) - 1.0) < 1e-12
        assert p.relative_permeability(60.0) < 1.0

    def test_brooks_corey_exponent(self):
        """kr = (psi_b/psi)^(2+3.lambda) above the bubbling pressure."""
        lam, psib = 0.5, 20.0
        p = HydraulicProperties(model=PermeabilityModel.BROOKS_COREY,
                                bc_lambda=lam, bc_psi_b=psib, kr_min=1e-30)
        psi = 80.0
        expect = (psib / psi) ** (2.0 + 3.0 * lam)
        assert abs(p.relative_permeability(psi) - expect) < 1e-12

    def test_van_genuchten_default_m_from_n(self):
        """By default m = 1 - 1/n (the Mualem restriction)."""
        n = 2.0
        auto = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN,
                                   vg_alpha=0.1, vg_n=n)
        custom = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN,
                                     vg_alpha=0.1, vg_n=n,
                                     vg_custom_m=True, vg_m=1.0 - 1.0 / n)
        for psi in (1.0, 10.0, 100.0):
            assert abs(auto.relative_permeability(psi)
                       - custom.relative_permeability(psi)) < 1e-12

    def test_van_genuchten_custom_m_changes_result(self):
        base = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN,
                                   vg_alpha=0.1, vg_n=2.0)
        other = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN,
                                    vg_alpha=0.1, vg_n=2.0,
                                    vg_custom_m=True, vg_m=0.2)
        assert abs(base.relative_permeability(10.0)
                   - other.relative_permeability(10.0)) > 1e-6

    def test_gardner_form(self):
        """kr = 1/(1 + a.h^n)."""
        a, n = 0.05, 2.0
        p = HydraulicProperties(model=PermeabilityModel.GARDNER,
                                gardner_a=a, gardner_n=n, kr_min=1e-30)
        h = 10.0
        assert abs(p.relative_permeability(h)
                   - 1.0 / (1.0 + a * h ** n)) < 1e-12

    def test_fredlund_xing_form(self):
        """kr = 1 / {ln[e + (psi/A)^B]}^C."""
        A, B, C = 50.0, 2.0, 1.0
        p = HydraulicProperties(model=PermeabilityModel.FREDLUND_XING,
                                fx_a=A, fx_b=B, fx_c=C, kr_min=1e-30)
        psi = 200.0
        expect = 1.0 / math.log(math.e + (psi / A) ** B) ** C
        assert abs(p.relative_permeability(psi) - expect) < 1e-12

    def test_user_defined_interpolation(self):
        p = HydraulicProperties(
            model=PermeabilityModel.USER_DEFINED, kr_min=1e-30,
            user_curve=[(0.0, 1e-5), (100.0, 1e-6), (1000.0, 1e-8)])
        assert abs(p.relative_permeability(0.0) - 1.0) < 1e-12
        assert abs(p.relative_permeability(100.0) - 0.1) < 1e-9
        assert abs(p.relative_permeability(1000.0) - 1e-3) < 1e-9
        # Beyond the table it holds the last value
        assert abs(p.relative_permeability(5000.0) - 1e-3) < 1e-9

    def test_k_at_suction_scales_ks(self):
        p = HydraulicProperties(ks=4e-5, model=PermeabilityModel.GARDNER,
                                gardner_a=0.05, gardner_n=2.0)
        assert abs(p.k_at_suction(10.0)
                   - 4e-5 * p.relative_permeability(10.0)) < 1e-20

    def test_tensor_at_suction_preserves_anisotropy_ratio(self):
        p = HydraulicProperties(ks=1e-5, k2_k1=0.25, k1_angle_deg=30.0,
                                model=PermeabilityModel.GARDNER,
                                gardner_a=0.05, gardner_n=2.0)
        kxx0, kyy0, kxy0 = p.conductivity_tensor()
        kxx, kyy, kxy = p.conductivity_tensor_at(20.0)
        kr = p.relative_permeability(20.0)
        assert abs(kxx - kxx0 * kr) < 1e-24
        assert abs(kyy - kyy0 * kr) < 1e-24
        assert abs(kxy - kxy0 * kr) < 1e-24

    def test_plot_curve_and_pick_library(self):
        """Support for the reference's Plot and Pick buttons."""
        p = HydraulicProperties(model=PermeabilityModel.VAN_GENUCHTEN)
        curve = p.curve(psi_max=1000.0, n=40)
        assert len(curve) == 41
        assert abs(curve[0][1] - 1.0) < 1e-12
        assert curve[-1][1] <= curve[1][1]
        lib = library_for(PermeabilityModel.VAN_GENUCHTEN)
        assert "Sand" in lib and "Clay" in lib
        assert "vg_alpha" in lib["Sand"] and "vg_n" in lib["Sand"]
        for model in (PermeabilityModel.BROOKS_COREY,
                      PermeabilityModel.GARDNER,
                      PermeabilityModel.FREDLUND_XING):
            assert library_for(model), model

    def test_serialisation_round_trip_all_models(self):
        for m in available_models():
            p = HydraulicProperties(ks=3e-5, k2_k1=0.4, k1_angle_deg=20.0,
                                    model=m, bc_lambda=0.8, fx_a=77.0,
                                    gardner_a=0.02, vg_n=1.8,
                                    user_curve=[(0.0, 1e-5), (10.0, 1e-6)])
            p2 = HydraulicProperties.from_dict(p.to_dict())
            assert p2.model == m
            assert abs(p2.ks - 3e-5) < 1e-20
            assert abs(p2.vg_n - 1.8) < 1e-12
            for psi in (0.0, 5.0, 100.0):
                assert abs(p2.relative_permeability(psi)
                           - p.relative_permeability(psi)) < 1e-12

    def test_backwards_compatible_with_v0126_files(self):
        """A v0.1.26 file used ``unsaturated_model`` where "saturated"
        meant constant permeability."""
        legacy = {"ks": 2e-6, "k2_k1": 1.0, "k1_angle_deg": 0.0,
                  "unsaturated_model": "saturated"}
        p = HydraulicProperties.from_dict(legacy)
        assert p.model == PermeabilityModel.CONSTANT
        assert abs(p.relative_permeability(500.0) - 1.0) < 1e-12
        legacy2 = dict(legacy, unsaturated_model="van_genuchten")
        assert HydraulicProperties.from_dict(legacy2).model == \
            PermeabilityModel.VAN_GENUCHTEN


# ======================================================================
class TestReactionSignConvention:
    def test_positive_reaction_means_inflow(self):
        """Pinned explicitly because the seepage-face switching depends on
        it: a POSITIVE nodal reaction means water entering the domain."""
        mesh = _dam_mesh(2.0)
        s = SeepageSolver(mesh, {"m": HydraulicProperties(ks=K_DAM)})
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, 10.0)
            elif abs(nd.x - L_DAM) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, 4.0)
        r = s.solve(b)
        assert r.ok and r.reactions
        inflow = sum(r.reactions[i] for i in mesh.boundary_node_ids()
                     if abs(mesh.nodes[i].x) < 1e-9)
        outflow = sum(r.reactions[i] for i in mesh.boundary_node_ids()
                      if abs(mesh.nodes[i].x - L_DAM) < 1e-9)
        assert inflow > 0.0, inflow
        assert outflow < 0.0, outflow
        # Global balance
        assert abs(inflow + outflow) < 1e-6 * abs(inflow)


# ======================================================================
class TestUnsaturatedDam:
    def _solve(self, props, h=0.7, relaxation=0.4, max_iterations=250):
        mesh = _dam_mesh(h)
        s = UnsaturatedSeepageSolver(mesh, {"m": props},
                                     relaxation=relaxation,
                                     max_iterations=max_iterations,
                                     tolerance=1e-5)
        return s, s.solve_unsaturated(_dam_bcs(mesh))

    def test_converges_without_chatter(self):
        """The plain nodal-switching algorithm chatters (the active set
        flips indefinitely). With the hysteresis band and the per-node
        switch budget the iteration must settle."""
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.GARDNER,
                                    gardner_a=1.0, gardner_n=3.0)
        _s, r = self._solve(props)
        assert r.converged, r.notes
        assert r.iterations < 200, r.iterations

    def test_free_surface_exits_above_tailwater(self):
        """The defining feature of a seepage face: the free surface meets
        the downstream face ABOVE the downstream water level."""
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.GARDNER,
                                    gardner_a=1.0, gardner_n=3.0)
        s, r = self._solve(props)
        fs = s.free_surface_points(r)
        assert fs, "no free surface traced"
        x_exit, y_exit = fs[-1]
        assert x_exit > 0.8 * L_DAM, x_exit
        assert y_exit > H2, (y_exit, H2)
        assert y_exit < H1, (y_exit, H1)

    def test_free_surface_starts_near_upstream_head(self):
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.GARDNER,
                                    gardner_a=1.0, gardner_n=3.0)
        s, r = self._solve(props)
        fs = s.free_surface_points(r)
        assert fs
        _x0, y0 = fs[0]
        assert abs(y0 - H1) < 1.0, y0

    def test_free_surface_monotonically_descends(self):
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.GARDNER,
                                    gardner_a=1.0, gardner_n=3.0)
        s, r = self._solve(props)
        fs = s.free_surface_points(r)
        assert len(fs) > 10
        ys = [p[1] for p in fs]
        # Allow small local noise from the discrete tracing
        drops = sum(1 for a, b in zip(ys[:-1], ys[1:]) if b <= a + 0.25)
        assert drops > 0.9 * (len(ys) - 1), (drops, len(ys))

    def test_seepage_face_nodes_reported(self):
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.GARDNER,
                                    gardner_a=1.0, gardner_n=3.0)
        _s, r = self._solve(props)
        assert r.seepage_nodes, "no seepage-face nodes activated"

    def test_discharge_converges_to_charnyi_as_kpsi_sharpens(self):
        """For a rectangular dam on an impervious base the discharge is
        exactly q = K(H1^2 - H2^2)/(2L) when the zone above the free
        surface does not conduct (Charnyi's result). Our unsaturated zone
        DOES conduct, so q is legitimately larger; sharpening k(psi) must
        drive q monotonically down to the analytic value."""
        q_exact = K_DAM * (H1 ** 2 - H2 ** 2) / (2.0 * L_DAM)
        cases = [
            dict(gardner_a=0.05, gardner_n=2.0),
            dict(gardner_a=1.0, gardner_n=3.0),
            dict(gardner_a=50.0, gardner_n=4.0),
            dict(gardner_a=1.0e4, gardner_n=5.0),
        ]
        errs = []
        for kw in cases:
            props = HydraulicProperties(
                ks=K_DAM, kr_min=1e-8,
                model=PermeabilityModel.GARDNER, **kw)
            s, r = self._solve(props, h=0.6)
            assert r.converged, (kw, r.notes)
            q = abs(s.flux_through_segment(r, L_DAM / 2, H_DAM,
                                           L_DAM / 2, 0.0, samples=700))
            errs.append(abs(q - q_exact) / q_exact)
        # Monotone improvement and a tight sharp-limit error
        for a, b in zip(errs[:-1], errs[1:]):
            assert b < a + 1e-3, errs
        assert errs[-1] < 0.05, errs

    def test_constant_model_matches_linear_solver(self):
        """With CONSTANT permeability and no seepage faces the non-linear
        solver must reproduce the Phase-2 linear result exactly."""
        mesh = _dam_mesh(1.2)
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.CONSTANT)
        b = SeepageBoundaryConditions()
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, H1)
            elif abs(nd.x - L_DAM) < 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, H2)
            else:
                b.add_node(nid, BCType.NODAL_FLOW, 0.0)
        lin = SeepageSolver(mesh, {"m": props}).solve(b)
        nl = UnsaturatedSeepageSolver(mesh, {"m": props},
                                      relaxation=1.0,
                                      tolerance=1e-9).solve_unsaturated(b)
        assert lin.ok and nl.converged
        for a, c in zip(lin.total_head, nl.total_head):
            assert abs(a - c) < 1e-6

    def test_non_convergence_is_reported(self):
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.VAN_GENUCHTEN,
                                    vg_alpha=5.0, vg_n=3.0, kr_min=1e-12)
        _s, r = self._solve(props, h=1.2, relaxation=1.0,
                            max_iterations=2)
        if not r.converged:
            assert "warning" in r.notes or "error" in r.notes

    def test_kr_range_reported(self):
        props = HydraulicProperties(ks=K_DAM,
                                    model=PermeabilityModel.GARDNER,
                                    gardner_a=50.0, gardner_n=4.0,
                                    kr_min=1e-8)
        _s, r = self._solve(props)
        assert r.notes["kr_min"] < 1.0
        assert abs(r.notes["kr_max"] - 1.0) < 1e-9

    def test_empty_mesh_reported(self):
        from ogr_fem2d.mesh import Mesh
        s = UnsaturatedSeepageSolver(Mesh(), {})
        r = s.solve_unsaturated(SeepageBoundaryConditions())
        assert not r.converged
