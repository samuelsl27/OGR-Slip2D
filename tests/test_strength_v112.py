# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.12 Strength Type updates aligned with Slide PDF spec.

Verifies:
    - Power Curve has the correct 5-parameter form: τ = c + a·(σ_n+d)^b + σ_n·tan(W)
    - Hoek-Brown classic (Hoek 1980) implementation matches Generalized
      HB at a=0.5
    - Hyperbolic envelope has correct asymptotic limits
    - All new models are registered and exportable
"""
from __future__ import annotations
import math


# ======================================================================
class TestPowerCurveSlideForm:
    """Slide PDF: τ = c + a·(σ_n + d)^b + σ_n·tan(W)
    where W is the Waviness angle, NOT a friction angle."""

    def test_pdf_defaults_match(self):
        from ogr_core.materials import PowerCurve
        # PDF screenshot defaults: a=0.7, b=1, c=3, d=0, W=0
        m = PowerCurve()
        assert m.params["a"] == 0.7
        assert m.params["b"] == 1.0
        assert m.params["c"] == 3.0
        assert m.params["d"] == 0.0
        assert m.params["waviness"] == 0.0

    def test_offset_d_shifts_envelope(self):
        """When d > 0, the envelope at σ_n = 0 is c + a·d^b (not just c)."""
        from ogr_core.materials import PowerCurve
        m = PowerCurve(a=2.0, b=0.5, c=1.0, d=9.0, waviness=0.0)
        # τ(0) = 1 + 2·9^0.5 + 0 = 1 + 6 = 7
        assert m.shear_strength(0.0) == 7.0

    def test_waviness_adds_friction_term(self):
        """Waviness W contributes σ_n·tan(W) to the shear strength."""
        from ogr_core.materials import PowerCurve
        m = PowerCurve(a=0.0, b=1.0, c=0.0, d=0.0, waviness=30.0)
        # With a=0, c=0: τ = σ_n·tan(30°)
        sig = 100.0
        assert abs(m.shear_strength(sig) - sig * math.tan(math.radians(30.0))) < 1e-9

    def test_full_formula_evaluation(self):
        from ogr_core.materials import PowerCurve
        m = PowerCurve(a=2.0, b=0.5, c=5.0, d=10.0, waviness=15.0)
        sig = 100.0
        expected = (5.0 + 2.0 * (sig + 10.0) ** 0.5
                    + sig * math.tan(math.radians(15.0)))
        assert abs(m.shear_strength(sig) - expected) < 1e-9


# ======================================================================
class TestHoekBrownClassic:
    """Hoek-Brown 1980 form: σ'₁ = σ'₃ + σ_ci · √(m·σ'₃/σ_ci + s)"""

    def test_pdf_defaults(self):
        from ogr_core.materials import HoekBrown
        m = HoekBrown()
        # PDF screenshot: UCS=15000, m=0.357, s=0.0017
        assert m.params["sigci"] == 15000.0
        assert abs(m.params["m"] - 0.357) < 1e-3
        assert abs(m.params["s"] - 0.0017) < 1e-4

    def test_monotonic_increase(self):
        """τ must monotonically increase with σ'_n."""
        from ogr_core.materials import HoekBrown
        m = HoekBrown(sigci=15000.0, m=0.357, s=0.0017)
        prev = 0.0
        for sig in [10, 100, 500, 1000, 2000, 5000]:
            tau = m.shear_strength(sig)
            assert tau > prev
            prev = tau

    def test_equivalent_to_generalized_at_a_05(self):
        """Mathematically the classic HB == Generalized HB with a=0.5."""
        from ogr_core.materials import HoekBrown, GeneralizedHoekBrown
        sigci, m_const, s = 25000.0, 1.5, 0.005
        hb = HoekBrown(sigci=sigci, m=m_const, s=s)
        ghb = GeneralizedHoekBrown(sigci=sigci, mb=m_const, s=s, a=0.5)
        for sig in [50, 500, 1000, 5000, 20000]:
            assert abs(hb.shear_strength(sig) - ghb.shear_strength(sig)) < 1e-3


# ======================================================================
class TestHyperbolic:
    """τ = (c_∞ · σ_n · tan(φ_0)) / (c_∞ + σ_n · tan(φ_0))"""

    def test_zero_normal_stress_gives_zero(self):
        from ogr_core.materials import Hyperbolic
        m = Hyperbolic(c_inf=150.0, phi_0=20.0)
        assert m.shear_strength(0.0) == 0.0

    def test_asymptotic_limit_at_high_stress(self):
        """As σ_n → ∞, τ approaches c_∞."""
        from ogr_core.materials import Hyperbolic
        c_inf = 150.0
        m = Hyperbolic(c_inf=c_inf, phi_0=20.0)
        tau_huge = m.shear_strength(1e8)
        assert tau_huge < c_inf
        assert tau_huge > 0.99 * c_inf  # within 1% of asymptote

    def test_initial_slope_equals_tan_phi0(self):
        """At σ_n → 0, dτ/dσ → tan(φ_0)."""
        from ogr_core.materials import Hyperbolic
        m = Hyperbolic(c_inf=150.0, phi_0=20.0)
        eps = 0.001
        slope = m.shear_strength(eps) / eps
        expected = math.tan(math.radians(20.0))
        assert abs(slope - expected) < 0.01

    def test_pdf_defaults(self):
        from ogr_core.materials import Hyperbolic
        m = Hyperbolic()
        # PDF screenshot: c_inf=150, phi_0=20
        assert m.params["c_inf"] == 150.0
        assert m.params["phi_0"] == 20.0


# ======================================================================
class TestRegistrationAndExports:
    def test_new_models_in_registry(self):
        from ogr_core.materials import REGISTRY
        ids = REGISTRY.ids()
        assert "hoek_brown_classic" in ids
        assert "hyperbolic" in ids
        # Existing
        assert "hoek_brown" in ids  # generalized
        assert "power_curve" in ids
        assert "vertical_stress_ratio" in ids

    def test_imports_work(self):
        from ogr_core.materials import HoekBrown, Hyperbolic
        assert HoekBrown.MODEL_ID == "hoek_brown_classic"
        assert Hyperbolic.MODEL_ID == "hyperbolic"

    def test_display_names_match_pdf(self):
        """The DISPLAY_NAME shown in the GUI dropdown must match the
        labels in Slide's Strength Type combobox."""
        from ogr_core.materials import (
            HoekBrown, Hyperbolic, GeneralizedHoekBrown, PowerCurve,
        )
        assert HoekBrown.DISPLAY_NAME == "Hoek-Brown"
        assert GeneralizedHoekBrown.DISPLAY_NAME == "Generalized Hoek-Brown"
        assert Hyperbolic.DISPLAY_NAME == "Hyperbolic"
        assert PowerCurve.DISPLAY_NAME == "Power Curve"


# ======================================================================
class TestNoStrengthAndInfinite:
    """Sanity checks on the trivial models."""

    def test_no_strength_returns_zero(self):
        from ogr_core.materials import NoStrength
        m = NoStrength()
        assert m.shear_strength(0.0) == 0.0
        assert m.shear_strength(100.0) == 0.0
        assert m.shear_strength(1e6) == 0.0

    def test_infinite_strength_returns_large_finite(self):
        from ogr_core.materials import InfiniteStrength
        m = InfiniteStrength()
        # Implementation may use a sentinel like 1e18 — must be huge
        assert m.shear_strength(0.0) > 1e10
        assert m.shear_strength(100.0) > 1e10
