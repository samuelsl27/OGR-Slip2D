# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.14 — analytical / high-precision tangent slopes for
non-linear strength envelopes (Hoek-Brown, Power Curve, Hyperbolic).

These models were giving FoS results different from Slide because the
``BishopSimplified._local_c_phi`` linearisation used a coarse secant
that was inaccurate at low confining stress (slices near the slope
surface). v0.1.14 replaces the secant with the model's analytical
``tangent_slope`` whenever available.
"""
from __future__ import annotations
import math


# ======================================================================
class TestTangentSlope:
    def test_mohr_coulomb_has_no_tangent_method(self):
        """Linear models don't need a tangent override — fallback to
        centred secant which recovers tan(φ) exactly."""
        from ogr_core.materials import MohrCoulomb
        m = MohrCoulomb(cohesion=10, friction_angle=20)
        # If tangent_slope exists it should still equal tan(20°)
        if hasattr(m, "tangent_slope"):
            assert abs(m.tangent_slope(100) - math.tan(math.radians(20))) < 1e-9

    def test_hoek_brown_classic_tangent_matches_balmer(self):
        """The analytical tangent of HB-classic must match the secant
        of a fine finite-difference (verification of the closed form
        / fine finite-difference)."""
        from ogr_core.materials import HoekBrown
        m = HoekBrown(sigci=15000, m=0.357, s=0.0017)
        for sn in [10, 50, 100, 500, 1000, 5000]:
            ts = m.tangent_slope(sn)
            # Verify against a very fine secant
            delta = 1e-3
            secant = (m.shear_strength(sn + delta)
                      - m.shear_strength(sn - delta)) / (2.0 * delta)
            assert abs(ts - secant) < 0.01, (
                f"tangent_slope at σ={sn} mismatch: ts={ts:.4f}, "
                f"secant={secant:.4f}"
            )

    def test_generalized_hb_equal_to_classic_at_a_half(self):
        """When a=0.5 the Generalized HB reduces to the classic HB.
        Their tangent slopes should be identical for the same params."""
        from ogr_core.materials import HoekBrown, GeneralizedHoekBrown
        hb = HoekBrown(sigci=15000, m=0.357, s=0.0017)
        ghb = GeneralizedHoekBrown(sigci=15000, mb=0.357, s=0.0017, a=0.5)
        for sn in [10, 100, 1000, 10000]:
            t_hb = hb.tangent_slope(sn)
            t_ghb = ghb.tangent_slope(sn)
            assert abs(t_hb - t_ghb) < 1e-3, (
                f"At σ={sn}: HB={t_hb:.4f}, GHB(a=0.5)={t_ghb:.4f}"
            )

    def test_hoek_brown_tangent_decreases_with_sigma(self):
        """HB envelope is concave: tangent slope must decrease as σ
        increases (rock-mass becomes 'less frictional' at high stress)."""
        from ogr_core.materials import HoekBrown
        m = HoekBrown(sigci=15000, m=0.357, s=0.0017)
        last = math.inf
        for sn in [10, 50, 100, 500, 1000, 5000]:
            ts = m.tangent_slope(sn)
            assert ts < last, f"tangent should decrease but {ts} >= {last}"
            last = ts

    def test_power_curve_analytical_tangent(self):
        """Power Curve: dτ/dσ = a·b·(σ+d)^(b-1) + tan(W)"""
        from ogr_core.materials import PowerCurve
        m = PowerCurve(a=2.0, b=0.5, c=3.0, d=0.0, waviness=15.0)
        # At σ=100, d=0: a·b·(100)^(-0.5) + tan(15°)
        expected = 2.0 * 0.5 * (100.0 ** -0.5) + math.tan(math.radians(15.0))
        actual = m.tangent_slope(100.0)
        assert abs(actual - expected) < 1e-6, (
            f"PowerCurve tangent at σ=100: expected {expected:.6f}, "
            f"got {actual:.6f}"
        )

    def test_hyperbolic_analytical_tangent(self):
        """Hyperbolic: dτ/dσ = c²·k / (c + σ·k)² where k = tan(φ_0)."""
        from ogr_core.materials import Hyperbolic
        m = Hyperbolic(c_inf=150, phi_0=20)
        k = math.tan(math.radians(20))
        for sn in [0, 10, 100, 1000]:
            denom = 150 + sn * k
            expected = (150 * 150 * k) / (denom * denom)
            actual = m.tangent_slope(sn)
            assert abs(actual - expected) < 1e-6, (
                f"Hyperbolic tangent at σ={sn}: expected {expected:.6f}, "
                f"got {actual:.6f}"
            )

    def test_hyperbolic_tangent_decays_to_zero(self):
        """As σ→∞, tangent → 0 (envelope becomes horizontal at c_∞)."""
        from ogr_core.materials import Hyperbolic
        m = Hyperbolic(c_inf=150, phi_0=20)
        assert m.tangent_slope(1e8) < 1e-3


# ======================================================================
class TestBishopUsesTangent:
    """Bishop._local_c_phi must call tangent_slope on the strength
    model when available, falling back to centred secant otherwise."""

    def test_bishop_local_c_phi_for_hb_uses_tangent(self):
        from ogr_core.materials import HoekBrown, Material
        from ogr_slip2d.methods.bishop import BishopSimplified
        m = Material(name="rock",
                     strength=HoekBrown(sigci=15000, m=0.357, s=0.0017))
        # At σ=100, c, tan_phi = local linearisation
        c, tan_phi = BishopSimplified._local_c_phi(None, m, 100.0)
        # Should match the analytical tangent at σ=100
        expected_tan_phi = m.strength.tangent_slope(100.0)
        assert abs(tan_phi - expected_tan_phi) < 1e-4, (
            f"Bishop didn't use HB's analytical tangent: "
            f"got {tan_phi:.4f}, expected {expected_tan_phi:.4f}"
        )
        # And c should satisfy τ(σ) = c + σ·tan_phi at σ=100
        tau_at_100 = m.strength.shear_strength(100.0)
        assert abs((c + 100 * tan_phi) - tau_at_100) < 1e-3
