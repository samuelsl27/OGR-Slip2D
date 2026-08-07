# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.28 — Seepage/stability coupling tests (Phase 4).

Two things are validated:

* **Coupling** — ``PorePressureType.FEM_SEEPAGE`` interpolates the pore
  pressure at each slice base midpoint from the converged FE field, using
  the T3 shape functions (exact for linear fields, already validated in
  Phase 1).
* **Unsaturated policy** — the extended Mohr-Coulomb envelope of
  Fredlund et al. (1978) as implemented by the reference: matric suction
  contributes strength only through ``phi_b`` beyond the ``air entry
  value``. Both parameters default to 0, which reproduces the
  conservative "clamp u at zero" behaviour as a SPECIAL CASE rather than
  as a separate switch.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.hydraulic import (  # noqa: E402
    HydraulicProperties,
    PermeabilityModel,
)
from ogr_core.materials import Material, MohrCoulomb, PorePressureType  # noqa: E402
from ogr_fem2d.mesh import generate_mesh_for_project  # noqa: E402
from ogr_fem2d.solvers import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    UnsaturatedSeepageSolver,
)
from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.slicer import apply_unsaturated_policy  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)


def _mat(phi_b=0.0, aev=0.0):
    return Material(name="s",
                    strength=MohrCoulomb(cohesion=5, friction_angle=30),
                    phi_b=phi_b, air_entry_value=aev)


def _seepage_project(phi_b=0.0, aev=0.0, elements=700):
    p = _ej1_project()
    for m in p.materials:
        m.hydraulic = HydraulicProperties(
            ks=1e-5, model=PermeabilityModel.GARDNER,
            gardner_a=1.0, gardner_n=3.0)
        m.pore_pressure = PorePressureType.FEM_SEEPAGE
        m.phi_b = phi_b
        m.air_entry_value = aev
    p.fem_mesh = generate_mesh_for_project(p, target_elements=elements)
    mesh = p.fem_mesh
    bnd = mesh.boundary_node_ids()
    xs = [mesh.nodes[i].x for i in bnd]
    ys = [mesh.nodes[i].y for i in bnd]
    x_min, x_max, y_min = min(xs), max(xs), min(ys)
    b = SeepageBoundaryConditions()
    for nid in sorted(bnd):
        nd = mesh.nodes[nid]
        if abs(nd.x - x_min) < 1e-6 and nd.y <= 40.0:
            b.add_node(nid, BCType.TOTAL_HEAD, 40.0)
        elif abs(nd.x - x_max) < 1e-6 and nd.y <= 27.0:
            b.add_node(nid, BCType.TOTAL_HEAD, 27.0)
        elif abs(nd.y - y_min) < 1e-6:
            b.add_node(nid, BCType.NODAL_FLOW, 0.0)
        else:
            b.add_node(nid, BCType.UNKNOWN)
    s = UnsaturatedSeepageSolver(
        mesh, {m.id: m.hydraulic for m in p.materials},
        relaxation=0.4, max_iterations=200, tolerance=1e-5)
    p.seepage_result = s.solve_unsaturated(b)
    return p


# ======================================================================
class TestUnsaturatedPolicy:
    def test_positive_pressure_untouched(self):
        u, c = apply_unsaturated_policy(50.0, _mat())
        assert abs(u - 50.0) < 1e-12 and c == 0.0

    def test_defaults_clamp_suction_to_zero(self):
        """phi_b = 0 and AEV = 0 (the reference defaults) make suction
        contribute nothing: the conservative choice."""
        for u_in in (-1.0, -20.0, -500.0):
            u, c = apply_unsaturated_policy(u_in, _mat())
            assert abs(u) < 1e-12, u
            assert c == 0.0

    def test_suction_below_air_entry_keeps_real_u(self):
        """Below the air entry value the soil is still effectively
        saturated, so the true negative u is used and the SATURATED
        friction angle credits the suction."""
        m = _mat(phi_b=15.0, aev=20.0)
        for u_in in (-5.0, -19.9, -20.0):
            u, c = apply_unsaturated_policy(u_in, m)
            assert abs(u - u_in) < 1e-12, u
            assert c == 0.0

    def test_suction_above_air_entry_caps_u_and_adds_cohesion(self):
        m = _mat(phi_b=15.0, aev=20.0)
        u, c = apply_unsaturated_policy(-60.0, m)
        assert abs(u + 20.0) < 1e-12, u
        assert abs(c - (60.0 - 20.0) * math.tan(math.radians(15.0))) < 1e-9

    def test_extra_cohesion_scales_with_suction(self):
        m = _mat(phi_b=20.0, aev=0.0)
        _u1, c1 = apply_unsaturated_policy(-50.0, m)
        _u2, c2 = apply_unsaturated_policy(-100.0, m)
        assert c2 > c1 > 0
        assert abs(c2 - 2.0 * c1) < 1e-9

    def test_zero_phi_b_gives_no_cohesion_even_with_aev(self):
        m = _mat(phi_b=0.0, aev=10.0)
        u, c = apply_unsaturated_policy(-200.0, m)
        assert abs(u + 10.0) < 1e-12
        assert c == 0.0

    def test_none_material_is_safe(self):
        u, c = apply_unsaturated_policy(-50.0, None)
        assert u == -50.0 and c == 0.0

    def test_material_serialisation_round_trip(self):
        m = _mat(phi_b=17.5, aev=33.0)
        m2 = Material.from_dict(m.to_dict())
        assert abs(m2.phi_b - 17.5) < 1e-12
        assert abs(m2.air_entry_value - 33.0) < 1e-12

    def test_defaults_are_zero(self):
        m = Material(name="s", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20))
        assert m.phi_b == 0.0
        assert m.air_entry_value == 0.0


# ======================================================================
class TestSeepageCoupling:
    def test_seepage_field_has_suction(self):
        p = _seepage_project()
        assert p.seepage_result.converged
        assert min(p.seepage_result.pore_pressure) < 0.0, "no suction"
        assert max(p.seepage_result.pore_pressure) > 0.0

    def test_coupled_fos_lower_than_dry(self):
        """With the conservative defaults the seepage pore pressures must
        REDUCE the factor of safety compared to the dry model."""
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        dry = ev.evaluate_circle(_ej1_project(), _CIRCLE)
        wet = ev.evaluate_circle(_seepage_project(), _CIRCLE)
        assert dry.is_valid and wet.is_valid
        assert wet.fos < dry.fos, (wet.fos, dry.fos)

    def test_phi_b_increases_fos_monotonically(self):
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        fos = []
        for phi_b in (0.0, 10.0, 20.0):
            r = ev.evaluate_circle(_seepage_project(phi_b=phi_b), _CIRCLE)
            assert r.is_valid
            fos.append(r.fos)
        for a, b in zip(fos[:-1], fos[1:]):
            assert b > a, fos

    def test_slices_carry_raw_and_effective_pressure(self):
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        r = ev.evaluate_circle(_seepage_project(), _CIRCLE)
        slices = list(r.slices)
        raws = [s.raw_pore_pressure for s in slices]
        effs = [s.pore_pressure for s in slices]
        # Some slice bases sit in the unsaturated zone
        assert min(raws) < 0.0, "no slice in suction"
        # With the defaults the effective pressure is clamped at zero
        assert min(effs) >= -1e-9
        for raw, eff in zip(raws, effs):
            if raw >= 0:
                assert abs(eff - raw) < 1e-9

    def test_suction_cohesion_recorded_on_slices(self):
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        r = ev.evaluate_circle(_seepage_project(phi_b=20.0), _CIRCLE)
        cs = [s.suction_cohesion for s in r.slices]
        assert max(cs) > 0.0, "no suction cohesion applied"
        assert min(cs) >= 0.0

    def test_missing_seepage_result_is_dry_not_crash(self):
        """A material set to FEM_SEEPAGE with no computed field must fall
        back to zero pore pressure rather than raise."""
        from ogr_core.geometry.primitives import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p = _ej1_project()
        for m in p.materials:
            m.pore_pressure = PorePressureType.FEM_SEEPAGE
        assert pore_pressure_at(p, Vertex(50.0, 20.0), p.materials[0]) == 0.0

    def test_point_outside_mesh_falls_back_to_dry(self):
        from ogr_core.geometry.primitives import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        p = _seepage_project()
        u = pore_pressure_at(p, Vertex(-500.0, -500.0), p.materials[0])
        assert u == 0.0

    def test_all_methods_accept_coupled_project(self):
        from ogr_slip2d import (
            GLEMorgensternPrice,
            JanbuSimplified,
            LoweKarafiath,
            OrdinaryFellenius,
            Spencer,
        )
        p = _seepage_project()
        for m in (OrdinaryFellenius(), BishopSimplified(),
                  JanbuSimplified(), Spencer(), GLEMorgensternPrice(),
                  LoweKarafiath()):
            ev = GridSearch(method=m, num_slices=20, min_area=0.0)
            r = ev.evaluate_circle(p, _CIRCLE)
            assert r is not None and r.is_valid, m.DISPLAY_NAME
            assert 0.1 < r.fos < 5.0, (m.DISPLAY_NAME, r.fos)
