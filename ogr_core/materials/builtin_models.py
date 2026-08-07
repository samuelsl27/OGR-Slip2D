# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Built-in constitutive (strength) models.

Each class is a self-contained plugin. Adding a new one is a matter of
writing a subclass with ``@register``; no other file needs to change.

Implemented models (matching Slide's Strength Type list):
    - MohrCoulomb            τ = c' + σ'ₙ · tan(φ')
    - Undrained              τ = cu                      (φ = 0 analysis)
    - InfiniteStrength       τ = ∞                       (rigid bedrock)
    - NoStrength             τ = 0                       (water, voids)
    - HoekBrown              σ'₁ = σ'₃ + σci·√(m·σ'₃/σci + s)   (Hoek 1980)
    - GeneralizedHoekBrown   σ'₁ = σ'₃ + σci·((mb·σ'₃/σci + s)^a) (Hoek 2002)
    - PowerCurve             τ = c + a·(σ'ₙ + d)^b + σ'ₙ·tan(W)
    - Hyperbolic             τ = c_∞·σ'ₙ·tan(φ_0) / (c_∞ + σ'ₙ·tan(φ_0))
    - VerticalStressRatio    τ = K · σ'v

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from .registry import register
from .strength_model import SliceContext, StrengthModel


# ----------------------------------------------------------------------
@register
class MohrCoulomb(StrengthModel):
    """Classic effective-stress linear failure envelope.

    τ = c' + σ'ₙ · tan(φ')
    """

    MODEL_ID = "mohr_coulomb"
    DISPLAY_NAME = "Mohr-Coulomb"
    PARAMETERS = {
        "cohesion": (10.0, "kPa", "Effective cohesion c'"),
        "friction_angle": (30.0, "deg", "Effective friction angle φ'"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        c = self.params["cohesion"]
        phi_rad = math.radians(self.params["friction_angle"])
        return c + max(0.0, sigma_n_eff) * math.tan(phi_rad)


# ----------------------------------------------------------------------
@register
class Undrained(StrengthModel):
    """Undrained total-stress analysis (φ = 0). τ = cu."""

    MODEL_ID = "undrained"
    DISPLAY_NAME = "Undrained (φ=0)"
    PARAMETERS = {
        "cohesion": (50.0, "kPa", "Undrained shear strength cu"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        return self.params["cohesion"]


# ----------------------------------------------------------------------
@register
class InfiniteStrength(StrengthModel):
    """Rigid / unbreakable material. Used for bedrock or retaining structures."""

    MODEL_ID = "infinite_strength"
    DISPLAY_NAME = "Infinite Strength"
    PARAMETERS: dict = {}

    def shear_strength(self, sigma_n_eff: float) -> float:
        return float("inf")


# ----------------------------------------------------------------------
@register
class NoStrength(StrengthModel):
    """Zero-strength material. Used for water bodies or open voids."""

    MODEL_ID = "no_strength"
    DISPLAY_NAME = "No Strength (water)"
    PARAMETERS: dict = {}

    def shear_strength(self, sigma_n_eff: float) -> float:
        return 0.0


# ----------------------------------------------------------------------
@register
class GeneralizedHoekBrown(StrengthModel):
    """Generalized Hoek-Brown rock-mass failure criterion.

    Strength at a given σ'ₙ is obtained by solving the local tangent of
    the non-linear envelope. Here we use the tangent Mohr-Coulomb
    approximation (Balmer's method simplification).
    """

    MODEL_ID = "hoek_brown"
    DISPLAY_NAME = "Generalized Hoek-Brown"
    PARAMETERS = {
        "sigci": (50000.0, "kPa", "Intact UCS, σci"),
        "mb": (2.5, "-", "Rock-mass constant mb"),
        "s": (0.004, "-", "Rock-mass constant s"),
        "a": (0.5, "-", "Rock-mass exponent a"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        sigma_n = max(sigma_n_eff, 1e-6)
        sci = self.params["sigci"]
        mb = self.params["mb"]
        s = self.params["s"]
        a = self.params["a"]
        # Instantaneous friction angle from HB tangent (Balmer):
        # h = 1 + a·mb·(mb·σ'ₙ/σci + s)^(a-1)
        arg = mb * sigma_n / sci + s
        if arg <= 0:
            return 0.0
        h = 1.0 + a * mb * (arg ** (a - 1.0))
        # Instantaneous shear strength:
        tau = (sigma_n * (h - 1.0) * math.sqrt(h)) / (h + 1.0)
        return max(0.0, tau)

    def tangent_slope(self, sigma_n_eff: float) -> float:
        """v0.1.14 — analytical-style tangent at σ'ₙ.

        The Generalized Hoek-Brown envelope is highly non-linear at low
        confining stress: a centred secant with a fixed Δ is a poor
        approximation. Here we use a centred finite-difference with a
        step scaled to σ'ₙ (1% of σ', floored at 1e-3 kPa) which gives
        machine-precision accuracy for the smooth Balmer form.
        """
        sigma_n = max(sigma_n_eff, 0.0)
        # Step scaled to σ'ₙ for relative accuracy ~1e-6
        delta = max(1e-3, 1e-4 * sigma_n)
        if sigma_n - delta <= 0:
            # Forward difference at very low σ
            tau_hi = self.shear_strength(sigma_n + delta)
            tau_0 = self.shear_strength(sigma_n)
            return max(0.0, (tau_hi - tau_0) / delta)
        tau_hi = self.shear_strength(sigma_n + delta)
        tau_lo = self.shear_strength(sigma_n - delta)
        return max(0.0, (tau_hi - tau_lo) / (2.0 * delta))


# ----------------------------------------------------------------------
@register
class HoekBrown(StrengthModel):
    """Classic Hoek-Brown rock-mass failure criterion (Hoek 1980).

    Principal-stress form:
        σ'₁ = σ'₃ + σ_ci · √(m · σ'₃ / σ_ci + s)

    The shear strength on a plane of normal stress σ'ₙ is obtained from
    the tangent to this envelope. Following Hoek (Brown & Hoek 1992),
    the instantaneous shear strength is computed via Balmer's method
    using a fixed exponent a = 0.5:

        h = 1 + 0.5·m·(m·σ'ₙ/σ_ci + s)^(-0.5)
        τ = σ'ₙ · (h - 1) · √h / (h + 1)

    This is the special case of the Generalized Hoek-Brown with a=0.5,
    which is mathematically equivalent to the original 1980 form.

    Parameters per Slide PDF: UCS (intact), m, s.
    """

    MODEL_ID = "hoek_brown_classic"
    DISPLAY_NAME = "Hoek-Brown"
    PARAMETERS = {
        "sigci": (15000.0, "kPa", "Intact UCS, σci"),
        "m": (0.357, "-", "Hoek-Brown constant m"),
        "s": (0.0017, "-", "Hoek-Brown constant s"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        sigma_n = max(sigma_n_eff, 1e-6)
        sci = self.params["sigci"]
        m = self.params["m"]
        s = self.params["s"]
        # Classic HB has a = 0.5
        arg = m * sigma_n / sci + s
        if arg <= 0:
            return 0.0
        # h = 1 + a·m·(arg)^(a-1), with a = 0.5
        h = 1.0 + 0.5 * m * (arg ** (-0.5))
        if h <= 0:
            return 0.0
        tau = (sigma_n * (h - 1.0) * math.sqrt(h)) / (h + 1.0)
        return max(0.0, tau)

    def tangent_slope(self, sigma_n_eff: float) -> float:
        """v0.1.14 — high-precision finite-difference tangent."""
        sigma_n = max(sigma_n_eff, 0.0)
        delta = max(1e-3, 1e-4 * sigma_n)
        if sigma_n - delta <= 0:
            tau_hi = self.shear_strength(sigma_n + delta)
            tau_0 = self.shear_strength(sigma_n)
            return max(0.0, (tau_hi - tau_0) / delta)
        tau_hi = self.shear_strength(sigma_n + delta)
        tau_lo = self.shear_strength(sigma_n - delta)
        return max(0.0, (tau_hi - tau_lo) / (2.0 * delta))


# ----------------------------------------------------------------------
@register
class PowerCurve(StrengthModel):
    """Power-curve envelope (Slide form):

        τ = c + a · (σ'ₙ + d)^b + σ'ₙ · tan(W)

    where:
        a, b — power-curve coefficients
        c    — cohesion intercept
        d    — normal-stress offset (so the envelope can pass below σ'ₙ=0)
        W    — Waviness angle (Patton-style joint roughness contribution)

    This is the form documented in Slide's PDF (Strenght_Type.pdf,
    page 8). The Waviness angle is NOT a friction angle — it represents
    the dilation contribution of joint surface roughness.
    """

    MODEL_ID = "power_curve"
    DISPLAY_NAME = "Power Curve"
    PARAMETERS = {
        "a": (0.7, "-", "Power-curve coefficient a"),
        "b": (1.0, "-", "Power-curve exponent b"),
        "c": (3.0, "kPa", "Cohesion intercept c"),
        "d": (0.0, "kPa", "Normal-stress offset d"),
        "waviness": (0.0, "deg", "Waviness angle W (joint roughness)"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        sigma_n = max(sigma_n_eff, 0.0)
        a = self.params["a"]
        b = self.params["b"]
        c = self.params["c"]
        d = self.params["d"]
        W = self.params["waviness"]
        # τ = c + a·(σ_n + d)^b + σ_n·tan(W)
        base = sigma_n + d
        if base <= 0:
            power_term = 0.0
        else:
            power_term = a * (base ** b)
        return c + power_term + sigma_n * math.tan(math.radians(W))

    def tangent_slope(self, sigma_n_eff: float) -> float:
        """v0.1.14 — analytical tangent of the Power Curve envelope.

        dτ/dσ = a·b·(σ + d)^(b−1) + tan(W)
        """
        sigma_n = max(sigma_n_eff, 0.0)
        a = self.params["a"]
        b = self.params["b"]
        d = self.params["d"]
        W = self.params["waviness"]
        base = sigma_n + d
        if base <= 0:
            power_term = 0.0
        else:
            power_term = a * b * (base ** (b - 1.0))
        return max(0.0, power_term + math.tan(math.radians(W)))


# ----------------------------------------------------------------------
@register
class Hyperbolic(StrengthModel):
    """Hyperbolic strength envelope (Slide form):

        τ = (c_∞ · σ'ₙ · tan(φ_0)) / (c_∞ + σ'ₙ · tan(φ_0))

    The envelope is asymptotic to two limits:
        - As σ'ₙ → 0:   slope = tan(φ_0)   (initial friction angle at zero
                                            normal stress)
        - As σ'ₙ → ∞:   τ → c_∞            (limiting cohesion at infinite
                                            normal stress)

    Used for rock joints / weathered materials where the failure
    envelope curves over and asymptotes to a maximum shear strength.
    """

    MODEL_ID = "hyperbolic"
    DISPLAY_NAME = "Hyperbolic"
    PARAMETERS = {
        "c_inf": (150.0, "kPa", "Cohesion at σ'ₙ = ∞"),
        "phi_0": (20.0, "deg", "Friction angle at σ'ₙ = 0"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        sigma_n = max(sigma_n_eff, 0.0)
        c_inf = self.params["c_inf"]
        phi_0 = self.params["phi_0"]
        tan_phi0 = math.tan(math.radians(phi_0))
        denom = c_inf + sigma_n * tan_phi0
        if denom <= 1e-12:
            return 0.0
        return (c_inf * sigma_n * tan_phi0) / denom

    def tangent_slope(self, sigma_n_eff: float) -> float:
        """v0.1.14 — analytical tangent of the hyperbolic envelope.

        dτ/dσ = c_∞² · tan(φ_0) / (c_∞ + σ · tan(φ_0))²
        """
        sigma_n = max(sigma_n_eff, 0.0)
        c_inf = self.params["c_inf"]
        phi_0 = self.params["phi_0"]
        tan_phi0 = math.tan(math.radians(phi_0))
        denom = c_inf + sigma_n * tan_phi0
        if denom <= 1e-12:
            return 0.0
        return (c_inf * c_inf * tan_phi0) / (denom * denom)


# ----------------------------------------------------------------------
@register
class VerticalStressRatio(StrengthModel):
    """τ = K · σ'v (assumes σ'ₙ ≈ σ'v). Minimum shear strength floor."""

    MODEL_ID = "vertical_stress_ratio"
    DISPLAY_NAME = "Vertical Stress Ratio"
    PARAMETERS = {
        "K": (0.25, "-", "Strength ratio K = τ/σ'v"),
        "min_strength": (0.0, "kPa", "Minimum shear strength"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        return max(self.params["K"] * sigma_n_eff, self.params["min_strength"])


# ======================================================================
# v0.1.15 — Additional strength models matching the Slide2 catalogue
# ======================================================================

# ----------------------------------------------------------------------
@register
class BartonBandis(StrengthModel):
    """Barton-Bandis criterion for rock joints / discontinuities.

        τ = σ'ₙ · tan( φr + JRC · log₁₀(JCS / σ'ₙ) )

    where φr is the residual friction angle, JRC the joint roughness
    coefficient, and JCS the joint wall compressive strength
    [Barton & Choubey, 1977; Barton & Bandis, 1990].

    The total friction angle (φr + JRC·log₁₀(JCS/σ'ₙ)) is capped to
    avoid unphysical values at very low σ'ₙ (Slide caps the effective
    roughness contribution; we cap the total angle at 70° + φr by
    default through the ``max_angle`` parameter logic in code).
    """

    MODEL_ID = "barton_bandis"
    DISPLAY_NAME = "Barton-Bandis"
    PARAMETERS = {
        "phi_r": (30.0, "deg", "Residual friction angle φr"),
        "JRC": (8.0, "-", "Joint roughness coefficient (0–20)"),
        "JCS": (50000.0, "kPa", "Joint wall compressive strength"),
        "max_total_friction": (75.0, "deg",
            "Cap on (φr + JRC·log₁₀(JCS/σ)) to avoid σ→0 blow-up"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        sigma_n = max(sigma_n_eff, 1e-6)
        phi_r = self.params["phi_r"]
        jrc = self.params["JRC"]
        jcs = self.params["JCS"]
        cap = self.params["max_total_friction"]
        ratio = max(jcs / sigma_n, 1.0)  # log10 ≥ 0
        total_angle = phi_r + jrc * math.log10(ratio)
        total_angle = min(total_angle, cap)
        return sigma_n * math.tan(math.radians(total_angle))

    def tangent_slope(self, sigma_n_eff: float) -> float:
        # Centred finite difference (envelope is strongly non-linear)
        sigma_n = max(sigma_n_eff, 1e-6)
        d = max(1e-4 * sigma_n, 1e-6)
        lo = self.shear_strength(sigma_n - d)
        hi = self.shear_strength(sigma_n + d)
        return (hi - lo) / (2.0 * d)


# ----------------------------------------------------------------------
@register
class DrainedUndrained(StrengthModel):
    """Composite drained/undrained envelope.

    Below a threshold normal stress σ_t the material behaves
    drained (Mohr-Coulomb: c' + σ'ₙ·tanφ'); above σ_t it switches to a
    constant undrained strength cap (a horizontal envelope at the
    drained strength evaluated at σ_t). This mirrors Slide's
    "Drained-Undrained" type where the undrained cap limits the
    available strength at high confinement.
    """

    MODEL_ID = "drained_undrained"
    DISPLAY_NAME = "Drained-Undrained"
    PARAMETERS = {
        "cohesion": (5.0, "kPa", "Effective cohesion c'"),
        "phi": (28.0, "deg", "Effective friction angle φ'"),
        "sigma_threshold": (100.0, "kPa",
            "Normal stress above which the undrained cap applies"),
    }

    def shear_strength(self, sigma_n_eff: float) -> float:
        c = self.params["cohesion"]
        phi = self.params["phi"]
        st = self.params["sigma_threshold"]
        tan_phi = math.tan(math.radians(phi))
        drained = c + max(sigma_n_eff, 0.0) * tan_phi
        cap = c + st * tan_phi
        return min(drained, cap)

    def tangent_slope(self, sigma_n_eff: float) -> float:
        st = self.params["sigma_threshold"]
        if sigma_n_eff <= st:
            return math.tan(math.radians(self.params["phi"]))
        return 0.0  # capped → horizontal


# ----------------------------------------------------------------------
@register
class AnisotropicLinear(StrengthModel):
    """Anisotropic Linear strength (Mercer 2012; Snowden / Slide2).

    Mohr-Coulomb strength whose cohesion and friction angle vary with
    the orientation β of the slip-surface base relative to the
    anisotropy (bedding) direction. Between the bedding orientation
    (angle ``A``, minimum strength) and ``B`` degrees away from it the
    parameters interpolate linearly from (c1, φ1) to (c2, φ2);
    beyond B they stay at (c2, φ2).

        |Δ| = angular distance between slice base and bedding (0–90°)
        if |Δ| ≤ A:           use (c1, φ1)
        elif A < |Δ| < B:     linear interp between the two
        else (|Δ| ≥ B):       use (c2, φ2)

    Needs the slice base angle → ``needs_context = True``.
    """

    MODEL_ID = "anisotropic_linear"
    DISPLAY_NAME = "Anisotropic Linear"
    PARAMETERS = {
        "c1": (5.0, "kPa", "Cohesion along bedding (minimum-strength dir.)"),
        "phi1": (15.0, "deg", "Friction angle along bedding"),
        "c2": (20.0, "kPa", "Cohesion across bedding (maximum-strength dir.)"),
        "phi2": (30.0, "deg", "Friction angle across bedding"),
        "bedding_angle": (0.0, "deg",
            "Orientation of bedding/anisotropy from horizontal"),
        "A": (10.0, "deg", "Half-width of the minimum-strength band"),
        "B": (30.0, "deg",
            "Angular distance beyond which max strength applies"),
    }

    @property
    def needs_context(self) -> bool:
        return True

    def _c_phi_for_angle(self, base_angle_deg: float):
        a = self.params["A"]
        b = self.params["B"]
        bed = self.params["bedding_angle"]
        # Angular distance between slice base and bedding, folded to 0–90
        delta = abs(base_angle_deg - bed) % 180.0
        if delta > 90.0:
            delta = 180.0 - delta
        c1, phi1 = self.params["c1"], self.params["phi1"]
        c2, phi2 = self.params["c2"], self.params["phi2"]
        if delta <= a:
            return c1, phi1
        if delta >= b:
            return c2, phi2
        if b - a < 1e-9:
            return c2, phi2
        t = (delta - a) / (b - a)
        return c1 + t * (c2 - c1), phi1 + t * (phi2 - phi1)

    def shear_strength(self, sigma_n_eff: float) -> float:
        # No context → assume worst case (bedding-aligned, minimum)
        c, phi = self.params["c1"], self.params["phi1"]
        return c + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        base_deg = math.degrees(ctx.base_angle_rad)
        c, phi = self._c_phi_for_angle(base_deg)
        return c + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))


# ----------------------------------------------------------------------
@register
class ShearNormalFunction(StrengthModel):
    """User-defined shear-strength function: τ as a piecewise-linear
    function of σ'ₙ, given by a table of (σ'ₙ, τ) points.

    Linear interpolation between points; constant extrapolation beyond
    the table range (Slide convention).
    """

    MODEL_ID = "shear_normal_function"
    DISPLAY_NAME = "Shear/Normal Function"
    PARAMETERS = {}  # table stored separately

    def __init__(self, **params):
        # Accept a 'points' kwarg (list of (sigma, tau)); not part of
        # the numeric PARAMETERS dict.
        pts = params.pop("points", None)
        super().__init__(**params)
        if pts is None:
            pts = [(0.0, 5.0), (100.0, 45.0), (300.0, 110.0)]
        self.points = [(float(s), float(t)) for (s, t) in pts]
        self.points.sort()

    def shear_strength(self, sigma_n_eff: float) -> float:
        pts = self.points
        if not pts:
            return 0.0
        s = sigma_n_eff
        if s <= pts[0][0]:
            return pts[0][1]
        if s >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            s0, t0 = pts[i]
            s1, t1 = pts[i + 1]
            if s0 <= s <= s1:
                f = (s - s0) / (s1 - s0) if s1 > s0 else 0.0
                return t0 + f * (t1 - t0)
        return pts[-1][1]

    def tangent_slope(self, sigma_n_eff: float) -> float:
        pts = self.points
        s = sigma_n_eff
        for i in range(len(pts) - 1):
            s0, t0 = pts[i]
            s1, t1 = pts[i + 1]
            if s0 <= s <= s1 and s1 > s0:
                return (t1 - t0) / (s1 - s0)
        return 0.0

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["points"] = list(self.points)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ShearNormalFunction":
        return cls(points=data.get("points"), **data.get("params", {}))


# ----------------------------------------------------------------------
@register
class DiscreteFunction(StrengthModel):
    """Discrete strength function: like Shear/Normal Function but the
    strength is a *step* function (each σ'ₙ interval has a constant
    τ), used when discrete test results are available. Uses the value
    of the lower bracketing point (no interpolation).
    """

    MODEL_ID = "discrete_function"
    DISPLAY_NAME = "Discrete Function"
    PARAMETERS = {}

    def __init__(self, **params):
        pts = params.pop("points", None)
        super().__init__(**params)
        if pts is None:
            pts = [(0.0, 10.0), (100.0, 50.0), (200.0, 80.0)]
        self.points = [(float(s), float(t)) for (s, t) in pts]
        self.points.sort()

    def shear_strength(self, sigma_n_eff: float) -> float:
        pts = self.points
        if not pts:
            return 0.0
        s = sigma_n_eff
        if s <= pts[0][0]:
            return pts[0][1]
        val = pts[0][1]
        for s0, t0 in pts:
            if s0 <= s:
                val = t0
            else:
                break
        return val

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["points"] = list(self.points)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "DiscreteFunction":
        return cls(points=data.get("points"), **data.get("params", {}))


# ----------------------------------------------------------------------
@register
class SHANSEP(StrengthModel):
    """SHANSEP undrained strength (Ladd & Foott 1974).

        su = σ'v · S · OCR^m

    where S is the normally-consolidated strength ratio, OCR the
    over-consolidation ratio, m the SHANSEP exponent. The undrained
    strength su is the available shear strength (φ = 0 in total-stress
    terms), so τ = su independent of σ'ₙ but dependent on σ'v.

    Needs the vertical effective stress → ``needs_context = True``.
    """

    MODEL_ID = "shansep"
    DISPLAY_NAME = "SHANSEP"
    PARAMETERS = {
        "S": (0.25, "-", "Normally-consolidated strength ratio su/σ'v"),
        "m": (0.8, "-", "SHANSEP exponent"),
        "OCR": (1.0, "-", "Over-consolidation ratio"),
        "su_min": (0.0, "kPa", "Minimum undrained strength floor"),
    }

    @property
    def needs_context(self) -> bool:
        return True

    def shear_strength(self, sigma_n_eff: float) -> float:
        # Without context, approximate σ'v ≈ σ'ₙ (conservative)
        return self._su(sigma_n_eff)

    def _su(self, sigma_v: float) -> float:
        S = self.params["S"]
        m = self.params["m"]
        ocr = max(self.params["OCR"], 1e-6)
        su = max(sigma_v, 0.0) * S * (ocr ** m)
        return max(su, self.params["su_min"])

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None or ctx.sigma_v_eff <= 0:
            return self._su(sigma_n_eff)
        return self._su(ctx.sigma_v_eff)


# ----------------------------------------------------------------------
@register
class AnisotropicStrengthFunction(StrengthModel):
    """Anisotropic Strength Function — cohesion and friction angle are
    given as functions of the slice base orientation via a table of
    (angle_deg, c, phi) points. Linear interpolation in angle.

    Needs the slice base angle → ``needs_context = True``.
    """

    MODEL_ID = "anisotropic_strength_function"
    DISPLAY_NAME = "Anisotropic Strength Function"
    PARAMETERS = {}

    def __init__(self, **params):
        pts = params.pop("points", None)
        super().__init__(**params)
        # points: list of (angle_deg, c, phi)
        if pts is None:
            pts = [(-90.0, 20.0, 30.0), (0.0, 5.0, 15.0),
                   (90.0, 20.0, 30.0)]
        self.points = [(float(a), float(c), float(p)) for (a, c, p) in pts]
        self.points.sort()

    @property
    def needs_context(self) -> bool:
        return True

    def _c_phi(self, angle_deg: float):
        pts = self.points
        if not pts:
            return 0.0, 0.0
        if angle_deg <= pts[0][0]:
            return pts[0][1], pts[0][2]
        if angle_deg >= pts[-1][0]:
            return pts[-1][1], pts[-1][2]
        for i in range(len(pts) - 1):
            a0, c0, p0 = pts[i]
            a1, c1, p1 = pts[i + 1]
            if a0 <= angle_deg <= a1:
                f = (angle_deg - a0) / (a1 - a0) if a1 > a0 else 0.0
                return c0 + f * (c1 - c0), p0 + f * (p1 - p0)
        return pts[-1][1], pts[-1][2]

    def shear_strength(self, sigma_n_eff: float) -> float:
        # No context → use the minimum-strength entry
        c_min = min(self.points, key=lambda t: t[1])
        return c_min[1] + max(sigma_n_eff, 0.0) * math.tan(
            math.radians(c_min[2]))

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        c, phi = self._c_phi(math.degrees(ctx.base_angle_rad))
        return c + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["points"] = list(self.points)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AnisotropicStrengthFunction":
        return cls(points=data.get("points"), **data.get("params", {}))


# ----------------------------------------------------------------------
@register
class GeneralizedAnisotropic(StrengthModel):
    """Generalized Anisotropic strength — assign ANY base strength
    model to ranges of slice base orientation. A composite of
    (angle_min, angle_max, sub_model) rules; the first matching rule's
    model is used.

    Stored as a list of rules; each rule references another registered
    model by its dict form. Needs context → ``needs_context = True``.
    """

    MODEL_ID = "generalized_anisotropic"
    DISPLAY_NAME = "Generalized Anisotropic"
    PARAMETERS = {}

    def __init__(self, **params):
        rules = params.pop("rules", None)
        super().__init__(**params)
        # rules: list of dicts {angle_min, angle_max, model: <dict>}
        self.rules = rules or []

    @property
    def needs_context(self) -> bool:
        return True

    def _model_for_angle(self, angle_deg: float):
        from .strength_model import StrengthModel as _SM
        for rule in self.rules:
            amin = rule.get("angle_min", -90.0)
            amax = rule.get("angle_max", 90.0)
            if amin <= angle_deg <= amax:
                mdict = rule.get("model")
                if mdict:
                    try:
                        return _SM.from_dict(mdict)
                    except Exception:  # noqa: BLE001
                        return None
        return None

    def shear_strength(self, sigma_n_eff: float) -> float:
        # No context → use the first rule's model, or zero
        if self.rules:
            m = self._model_for_angle(0.0)
            if m is not None:
                return m.shear_strength(sigma_n_eff)
        return 0.0

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        angle = math.degrees(ctx.base_angle_rad) if ctx else 0.0
        m = self._model_for_angle(angle)
        if m is None:
            return 0.0
        if getattr(m, "needs_context", False):
            return m.shear_strength_ctx(sigma_n_eff, ctx)
        return m.shear_strength(sigma_n_eff)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rules"] = list(self.rules)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GeneralizedAnisotropic":
        return cls(rules=data.get("rules"), **data.get("params", {}))


# ----------------------------------------------------------------------
@register
class SnowdenModifiedAnisotropicLinear(StrengthModel):
    """Snowden Modified Anisotropic Linear (Snowden Associates / Slide2).

    A refinement of Anisotropic Linear where, instead of a single
    linear transition, the shear strength is computed from a
    Mohr-Coulomb envelope whose parameters are modulated by an
    anisotropy ratio that varies smoothly (cosine) with the angular
    distance from the bedding orientation. This avoids the sharp
    kinks of the basic linear model.

        ratio = 0.5·(1 − cos(π·min(|Δ|, B)/B))     ∈ [0, 1]
        c   = c1   + ratio·(c2 − c1)
        phi = phi1 + ratio·(phi2 − phi1)

    Needs the slice base angle → ``needs_context = True``.
    """

    MODEL_ID = "snowden_anisotropic_linear"
    DISPLAY_NAME = "Snowden Modified Anisotropic Linear"
    PARAMETERS = {
        "c1": (5.0, "kPa", "Cohesion along bedding"),
        "phi1": (15.0, "deg", "Friction angle along bedding"),
        "c2": (20.0, "kPa", "Cohesion across bedding"),
        "phi2": (30.0, "deg", "Friction angle across bedding"),
        "bedding_angle": (0.0, "deg", "Bedding orientation from horizontal"),
        "B": (30.0, "deg", "Angular distance for full transition"),
    }

    @property
    def needs_context(self) -> bool:
        return True

    def _c_phi(self, base_angle_deg: float):
        bed = self.params["bedding_angle"]
        b = max(self.params["B"], 1e-6)
        delta = abs(base_angle_deg - bed) % 180.0
        if delta > 90.0:
            delta = 180.0 - delta
        x = min(delta, b)
        ratio = 0.5 * (1.0 - math.cos(math.pi * x / b))
        c1, phi1 = self.params["c1"], self.params["phi1"]
        c2, phi2 = self.params["c2"], self.params["phi2"]
        return c1 + ratio * (c2 - c1), phi1 + ratio * (phi2 - phi1)

    def shear_strength(self, sigma_n_eff: float) -> float:
        c, phi = self.params["c1"], self.params["phi1"]
        return c + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        c, phi = self._c_phi(math.degrees(ctx.base_angle_rad))
        return c + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))
