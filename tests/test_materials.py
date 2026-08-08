# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for ogr_core.materials."""
from __future__ import annotations

import math

import pytest

from ogr_core.materials import (
    REGISTRY,
    GeneralizedHoekBrown,
    InfiniteStrength,
    Material,
    MohrCoulomb,
    NoStrength,
    PorePressureType,
    PowerCurve,
    StrengthModel,
    Undrained,
    VerticalStressRatio,
    register,
)


class TestBuiltinModels:
    def test_mohr_coulomb(self):
        m = MohrCoulomb(cohesion=10.0, friction_angle=30.0)
        # At σ'ₙ = 100, τ = 10 + 100 * tan(30°) ≈ 67.735
        assert m.shear_strength(100.0) == pytest.approx(10 + 100 * math.tan(math.radians(30)))

    def test_mohr_coulomb_no_negative_stress(self):
        m = MohrCoulomb(cohesion=5.0, friction_angle=20.0)
        # Under tension σ'ₙ < 0, the frictional contribution is clamped
        assert m.shear_strength(-10.0) == pytest.approx(5.0)

    def test_undrained_is_constant(self):
        m = Undrained(cohesion=50.0)
        assert m.shear_strength(0.0) == 50.0
        assert m.shear_strength(1000.0) == 50.0
        assert m.shear_strength(-100.0) == 50.0

    def test_infinite_strength(self):
        m = InfiniteStrength()
        assert math.isinf(m.shear_strength(100.0))

    def test_no_strength(self):
        assert NoStrength().shear_strength(1000.0) == 0.0

    def test_hoek_brown_monotone(self):
        m = GeneralizedHoekBrown(sigci=50000, mb=2.5, s=0.004, a=0.5)
        tau1 = m.shear_strength(10.0)
        tau2 = m.shear_strength(1000.0)
        assert tau1 >= 0.0
        assert tau2 > tau1

    def test_power_curve(self):
        # v0.1.12 — Slide form: τ = c + a·(σ'ₙ + d)^b + σ'ₙ·tan(W)
        m = PowerCurve(a=2.0, b=0.5, c=1.0, d=0.0, waviness=15.0)
        # At σ'ₙ = 100: τ = 1 + 2·(100 + 0)^0.5 + 100·tan(15°)
        expected = 1.0 + 2.0 * (100.0 ** 0.5) + 100.0 * math.tan(math.radians(15.0))
        assert m.shear_strength(100.0) == pytest.approx(expected)

    def test_power_curve_with_offset_d(self):
        # The d offset shifts the envelope: at σ'ₙ = 0, τ = c + a·d^b
        m = PowerCurve(a=2.0, b=0.5, c=5.0, d=4.0, waviness=0.0)
        # At σ'ₙ = 0: τ = 5 + 2·4^0.5 + 0 = 5 + 4 = 9
        assert m.shear_strength(0.0) == pytest.approx(9.0)

    def test_hoek_brown_classic(self):
        # Slide form: σ'₁ = σ'₃ + σ_ci · √(m·σ'₃/σ_ci + s)
        from ogr_core.materials import HoekBrown
        m = HoekBrown(sigci=15000.0, m=0.357, s=0.0017)
        # Should produce a positive shear strength at σ'ₙ = 1000
        tau = m.shear_strength(1000.0)
        assert tau > 0, "HoekBrown should give positive shear at σ'ₙ > 0"
        # And monotonically increasing with σ'ₙ
        assert m.shear_strength(2000.0) > tau

    def test_hyperbolic_asymptotic_limits(self):
        # τ asymptotes to c_∞ as σ'ₙ → ∞, slope = tan(φ_0) at σ'ₙ → 0
        from ogr_core.materials import Hyperbolic
        m = Hyperbolic(c_inf=150.0, phi_0=20.0)
        # At σ'ₙ = 0: τ = 0
        assert m.shear_strength(0.0) == pytest.approx(0.0)
        # As σ'ₙ → ∞ the strength approaches c_inf
        tau_huge = m.shear_strength(1e6)
        assert tau_huge < 150.0
        assert tau_huge > 100.0  # close to but below the asymptote

    def test_vertical_stress_ratio_with_floor(self):
        m = VerticalStressRatio(K=0.3, min_strength=5.0)
        assert m.shear_strength(0.0) == 5.0
        assert m.shear_strength(100.0) == 30.0


class TestRegistry:
    def test_all_builtins_registered(self):
        ids = REGISTRY.ids()
        for expected in [
            "mohr_coulomb", "undrained", "infinite_strength", "no_strength",
            "hoek_brown",          # generalized
            "hoek_brown_classic",  # classic (1980)
            "power_curve", "hyperbolic", "vertical_stress_ratio",
        ]:
            assert expected in ids

    def test_cannot_register_duplicate(self):
        with pytest.raises(ValueError):
            @register
            class DuplicateMC(StrengthModel):
                MODEL_ID = "mohr_coulomb"  # already registered
                DISPLAY_NAME = "dup"
                PARAMETERS = {}

                def shear_strength(self, s):
                    return 0.0

    def test_unknown_model_raises(self):
        with pytest.raises(KeyError):
            REGISTRY.get("nonexistent_model")


class TestStrengthModelSerialization:
    def test_roundtrip_mohr_coulomb(self):
        m = MohrCoulomb(cohesion=15.0, friction_angle=28.0)
        data = m.to_dict()
        m2 = StrengthModel.from_dict(data)
        assert isinstance(m2, MohrCoulomb)
        assert m2.params["cohesion"] == 15.0
        assert m2.params["friction_angle"] == 28.0

    def test_unknown_param_raises(self):
        with pytest.raises(ValueError):
            MohrCoulomb(unknown_param=1.0)


class TestMaterial:
    def test_gamma_below_water_uses_sat(self):
        m = Material(
            name="clay",
            strength=MohrCoulomb(cohesion=10, friction_angle=20),
            unit_weight=19.0,
            sat_unit_weight=21.5,
            # v0.1.60 — γsat is opt-in; without the flag the material has
            # a single unit weight above and below the water table.
            use_sat_unit_weight=True,
        )
        assert m.gamma_at(below_water=False) == 19.0
        assert m.gamma_at(below_water=True) == 21.5

    def test_tooltip_contains_strength_name(self):
        m = Material(name="Test", strength=MohrCoulomb(cohesion=10, friction_angle=20))
        html = m.tooltip_html()
        assert "Mohr-Coulomb" in html
        assert "Test" in html

    def test_serialization_roundtrip(self):
        m = Material(
            name="Sand",
            strength=MohrCoulomb(cohesion=0.0, friction_angle=35.0),
            unit_weight=18.0,
            sat_unit_weight=20.5,
            use_sat_unit_weight=True,
            pore_pressure=PorePressureType.WATER_TABLE,
            color="#ff8800",
        )
        data = m.to_dict()
        m2 = Material.from_dict(data)
        assert m2.name == "Sand"
        assert m2.unit_weight == 18.0
        # The saturated weight and its opt-in flag went untested before
        # v0.1.60, which is how a serialization gap could have hidden.
        assert m2.sat_unit_weight == 20.5
        assert m2.use_sat_unit_weight is True
        assert m2.pore_pressure == PorePressureType.WATER_TABLE
        assert m2.color == "#ff8800"
        assert m2.id == m.id
