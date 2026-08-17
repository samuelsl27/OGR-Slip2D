# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.15 — the 9 new constitutive (strength) models that
complete the Slide2 catalogue.

Models: Barton-Bandis, Drained-Undrained, Anisotropic Linear,
Shear/Normal Function, Discrete Function, SHANSEP, Anisotropic
Strength Function, Generalized Anisotropic, Snowden Modified
Anisotropic Linear.
"""
from __future__ import annotations
import math


# ======================================================================
class TestRegistry:
    def test_eighteen_models_registered(self):
        from ogr_core.materials.registry import REGISTRY
        models = REGISTRY.all()
        assert len(models) >= 18, (
            f"Expected ≥18 strength models, got {len(models)}"
        )
        for mid in (
            "barton_bandis", "drained_undrained", "anisotropic_linear",
            "shear_normal_function", "discrete_function", "shansep",
            "anisotropic_strength_function", "generalized_anisotropic",
            "snowden_anisotropic_linear",
        ):
            assert mid in models, f"Missing model: {mid}"


# ======================================================================
class TestBartonBandis:
    def test_formula(self):
        from ogr_core.materials.builtin_models import BartonBandis
        bb = BartonBandis(phi_r=30, JRC=8, JCS=50000)
        sn = 1000.0
        expected = sn * math.tan(math.radians(
            30 + 8 * math.log10(50000 / sn)))
        assert abs(bb.shear_strength(sn) - expected) < 0.1

    def test_capped_at_low_stress(self):
        from ogr_core.materials.builtin_models import BartonBandis
        bb = BartonBandis(phi_r=30, JRC=20, JCS=100000,
                          max_total_friction=75)
        # At very low σ the total angle would exceed 75°; must be capped
        tau = bb.shear_strength(0.001)
        # τ = σ·tan(75°) at the cap
        assert tau <= 0.001 * math.tan(math.radians(75)) + 1e-6

    def test_tangent_positive(self):
        from ogr_core.materials.builtin_models import BartonBandis
        bb = BartonBandis()
        assert bb.tangent_slope(500) > 0


# ======================================================================
class TestDrainedUndrained:
    def test_drained_below_threshold(self):
        from ogr_core.materials.builtin_models import DrainedUndrained
        du = DrainedUndrained(cohesion=5, phi=28, sigma_threshold=100)
        tan28 = math.tan(math.radians(28))
        assert abs(du.shear_strength(50) - (5 + 50 * tan28)) < 1e-6

    def test_capped_above_threshold(self):
        from ogr_core.materials.builtin_models import DrainedUndrained
        du = DrainedUndrained(cohesion=5, phi=28, sigma_threshold=100)
        tan28 = math.tan(math.radians(28))
        cap = 5 + 100 * tan28
        assert abs(du.shear_strength(500) - cap) < 1e-6


# ======================================================================
class TestAnisotropicLinear:
    def test_min_strength_along_bedding(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        from ogr_core.materials.strength_model import SliceContext
        al = AnisotropicLinear(c1=5, phi1=15, c2=20, phi2=30,
                               bedding_angle=0, A=10, B=30)
        ctx = SliceContext(base_angle_rad=0.0)
        tau = al.shear_strength_ctx(100, ctx)
        expected = 5 + 100 * math.tan(math.radians(15))
        assert abs(tau - expected) < 1e-6

    def test_max_strength_across_bedding(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        from ogr_core.materials.strength_model import SliceContext
        al = AnisotropicLinear(c1=5, phi1=15, c2=20, phi2=30,
                               bedding_angle=0, A=10, B=30)
        ctx = SliceContext(base_angle_rad=math.radians(45))
        tau = al.shear_strength_ctx(100, ctx)
        expected = 20 + 100 * math.tan(math.radians(30))
        assert abs(tau - expected) < 1e-6

    def test_needs_context(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        assert AnisotropicLinear().needs_context is True


# ======================================================================
class TestShearNormalFunction:
    def test_interpolation(self):
        from ogr_core.materials.builtin_models import ShearNormalFunction
        f = ShearNormalFunction(points=[(0, 5), (100, 45), (300, 110)])
        assert abs(f.shear_strength(50) - 25.0) < 1e-6
        assert abs(f.shear_strength(200) - 77.5) < 1e-6

    def test_extrapolation_constant(self):
        from ogr_core.materials.builtin_models import ShearNormalFunction
        f = ShearNormalFunction(points=[(0, 5), (100, 45)])
        assert f.shear_strength(-50) == 5.0
        assert f.shear_strength(500) == 45.0

    def test_roundtrip(self):
        from ogr_core.materials.builtin_models import ShearNormalFunction
        f = ShearNormalFunction(points=[(0, 5), (100, 45)])
        d = f.to_dict()
        f2 = ShearNormalFunction.from_dict(d)
        assert f2.points == f.points


# ======================================================================
class TestDiscreteFunction:
    def test_step(self):
        from ogr_core.materials.builtin_models import DiscreteFunction
        f = DiscreteFunction(points=[(0, 10), (100, 50), (200, 80)])
        assert f.shear_strength(150) == 50.0
        assert f.shear_strength(250) == 80.0
        assert f.shear_strength(50) == 10.0


# ======================================================================
class TestSHANSEP:
    def test_formula(self):
        from ogr_core.materials.builtin_models import SHANSEP
        from ogr_core.materials.strength_model import SliceContext
        sh = SHANSEP(S=0.25, m=0.8, OCR=4)
        ctx = SliceContext(sigma_v_eff=100)
        expected = 100 * 0.25 * (4 ** 0.8)
        assert abs(sh.shear_strength_ctx(0, ctx) - expected) < 1e-6

    def test_floor(self):
        from ogr_core.materials.builtin_models import SHANSEP
        from ogr_core.materials.strength_model import SliceContext
        sh = SHANSEP(S=0.25, m=0.8, OCR=1, su_min=10)
        ctx = SliceContext(sigma_v_eff=1.0)  # tiny → su below floor
        assert sh.shear_strength_ctx(0, ctx) == 10.0


# ======================================================================
class TestSnowden:
    def test_cosine_midpoint(self):
        from ogr_core.materials.builtin_models import (
            SnowdenModifiedAnisotropicLinear,
        )
        m = SnowdenModifiedAnisotropicLinear(
            c1=5, phi1=15, c2=20, phi2=30, bedding_angle=0, B=30)
        # At 15° (half of B=30): cosine ratio = 0.5
        c, phi = m._c_phi(15)
        assert abs(c - 12.5) < 1e-6
        assert abs(phi - 22.5) < 1e-6


# ======================================================================
class TestGeneralizedAnisotropic:
    def test_rule_dispatch(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.materials.strength_model import SliceContext
        ga = GeneralizedAnisotropic(rules=[
            {"angle_min": -90, "angle_max": 0,
             "model": {"model_id": "mohr_coulomb",
                       "params": {"cohesion": 10, "friction_angle": 20}}},
            {"angle_min": 0, "angle_max": 90,
             "model": {"model_id": "mohr_coulomb",
                       "params": {"cohesion": 30, "friction_angle": 35}}},
        ])
        # Negative angle → first rule
        ctx_neg = SliceContext(base_angle_rad=math.radians(-30))
        tau_neg = ga.shear_strength_ctx(100, ctx_neg)
        expected_neg = 10 + 100 * math.tan(math.radians(20))
        assert abs(tau_neg - expected_neg) < 1e-6
        # Positive angle → second rule
        ctx_pos = SliceContext(base_angle_rad=math.radians(30))
        tau_pos = ga.shear_strength_ctx(100, ctx_pos)
        expected_pos = 30 + 100 * math.tan(math.radians(35))
        assert abs(tau_pos - expected_pos) < 1e-6


# ======================================================================
class TestModelsInFoS:
    def _slope(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.project import Project
        H = 12.0
        beta = math.radians(30.96)
        toe = 30.0
        crest = toe + H / math.tan(beta)
    # v0.1.89 — the 10 m foundation. This contour used to be
    # ``(0,0) (60,0) (60,H) (crest,H) (toe,0)``, whose closing edge runs back
    # along the bottom one: between x = 0 and the toe at x = 30 the ground
    # surface and the base of the model are the same line at y = 0, enclosing
    # no soil at all. v0.1.84 fixed the two files that depended on the
    # degeneracy to pass and left five that did not; this is one of them.
        base = -10.0
        ext = Polyline(vertices=[
            Vertex(0, base), Vertex(60, base), Vertex(60, H),
            Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
        ], closed=True)
        ext.ensure_ccw()
        p = Project("t")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        return p

    def test_anisotropic_in_full_fos(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import AnisotropicLinear
        from ogr_slip2d import BishopSimplified, GridSearch
        p = self._slope()
        p.materials = [Material(name="M", unit_weight=20,
            strength=AnisotropicLinear(c1=5, phi1=15, c2=20, phi2=30,
                                       A=10, B=30))]
        search = GridSearch(method=BishopSimplified(),
            grid_x=(20, 60), grid_y=(15, 35), grid_nx=6, grid_ny=6,
            radius_increment=2.0, min_radius=8.0, num_slices=20, min_area=0.5)
        r = search.run(p)
        assert r.critical is not None
        assert 0.5 < r.critical.fos < 5.0

    def test_shansep_in_full_fos(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import SHANSEP
        from ogr_slip2d import BishopSimplified, GridSearch
        p = self._slope()
        p.materials = [Material(name="M", unit_weight=20,
            strength=SHANSEP(S=0.3, m=0.8, OCR=2))]
        search = GridSearch(method=BishopSimplified(),
            grid_x=(20, 60), grid_y=(15, 35), grid_nx=6, grid_ny=6,
            radius_increment=2.0, min_radius=8.0, num_slices=20, min_area=0.5)
        r = search.run(p)
        assert r.critical is not None
        assert 0.5 < r.critical.fos < 5.0
