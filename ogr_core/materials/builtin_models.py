# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Built-in constitutive (strength) models.

Each class is a self-contained plugin. Adding a new one is a matter of
writing a subclass with ``@register``; no other file needs to change.

Implemented models (matching the reference's Strength Type list):
    - MohrCoulomb            τ = c' + σ'ₙ · tan(φ')
    - Undrained              τ = cu                      (φ = 0 analysis)
    - InfiniteStrength       τ = ∞                       (rigid bedrock)
    - NoStrength             τ = 0                       (water, voids)
    - HoekBrown              σ'₁ = σ'₃ + σci·√(m·σ'₃/σci + s)   (Hoek 1980)
    - GeneralizedHoekBrown   σ'₁ = σ'₃ + σci·((mb·σ'₃/σci + s)^a) (Hoek 2002)
    - PowerCurve             τ = c + a·(σ'ₙ + d)^b + σ'ₙ·tan(W)
    - Hyperbolic             τ = c_∞·σ'ₙ·tan(φ_0) / (c_∞ + σ'ₙ·tan(φ_0))
    - VerticalStressRatio    τ = K · σ'v
    - UndrainedDepthFromLayerTop   c = c_top   + Δc·(y_top   − y)
    - UndrainedDepthFromDatum      c = c_datum + Δc·(y_datum − y)
    - UndrainedDistanceToSlope     c = c_top   + Δc·(distance to slope)

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import ClassVar

from .registry import register
from .strength_model import (FactoredStrength, MaterialFactors, SliceContext,
                             StrengthModel, tan_factored_angle)


# ----------------------------------------------------------------------
# v0.1.225 (D224) -- design-standard partial factors, by category.
#
# Each model says in ``design_factored`` which category of partial factor
# its parameters are (``MaterialFactors``): c′ and tan φ′ (Mohr-Coulomb and
# the models written with them), cu (the undrained ones, whatever gives
# them their cu), or the shear strength τ as a whole (every other envelope,
# the reference documentation's "Shear strength (other models)"). With all
# four factors equal to γ every model's strength is divided by γ exactly,
# at every σ'ₙ, which is the strength reduction the limit-equilibrium
# factor of safety is defined by (Frank et al. 2004, §11.5).
def _factor_params(model, factors_by_param: dict, tangents: dict,
                   category: str) -> FactoredStrength:
    """Divide ``model.params[k]`` by ``factors_by_param[k]``, and the
    TANGENT of each angle ``tangents[k]`` by its factor. A factor of 1
    leaves the value untouched, bit for bit."""
    new, changes = {}, {}
    for k, f in factors_by_param.items():
        if f != 1.0:
            v = model.params[k]
            new[k] = v / f
            changes[k] = (v, new[k])
    for k, f in tangents.items():
        if f != 1.0:
            v = model.params[k]
            new[k] = tan_factored_angle(v, f)
            changes[k] = (v, new[k])
    out = model._with_params(**new) if new else model
    return FactoredStrength(out, changes, category)


class _DesignDivisor:
    """Category "τ" for an envelope its own parameters cannot scale.

    v0.1.225 (D224) -- τ/γ is not a Hoek-Brown or a Barton-Bandis envelope
    of any other parameters (σci/γ, for one, changes the curvature), so
    these models carry a divisor of their shear strength instead. Only the
    analysis copy made by ``ogr_core.project.design_factors`` sets it; it
    travels in ``to_dict`` so a copy of that copy keeps it, and it is 1 --
    bit for bit the model as before -- everywhere else. The tangent is taken
    from ``shear_strength``, so it follows.
    """

    design_divisor: float = 1.0

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        if factors.shear == 1.0:
            return FactoredStrength(self, {}, "τ")
        import copy
        out = copy.deepcopy(self)
        out.design_divisor = self.design_divisor * factors.shear
        return FactoredStrength(
            out, {"shear strength divisor": (self.design_divisor,
                                             out.design_divisor)}, "τ")

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.design_divisor != 1.0:
            d["design_divisor"] = self.design_divisor
        return d

    @classmethod
    def from_dict(cls, data: dict):
        m = cls(**data.get("params", {}))
        m.design_divisor = float(data.get("design_divisor", 1.0))
        return m


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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        return _factor_params(self, {"cohesion": factors.cohesion},
                              {"friction_angle": factors.tan_phi},
                              "c′, tan φ′")


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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        return _factor_params(self, {"cohesion": factors.undrained}, {},
                              "cu")


# ----------------------------------------------------------------------
@register
class InfiniteStrength(StrengthModel):
    """Rigid / unbreakable material. Used for bedrock or retaining structures."""

    MODEL_ID = "infinite_strength"
    DISPLAY_NAME = "Infinite Strength"
    PARAMETERS: dict = {}

    def shear_strength(self, sigma_n_eff: float) -> float:
        return float("inf")

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # Nothing to factor: a modelling device, not a strength.
        return FactoredStrength(self, {}, "—")


# ----------------------------------------------------------------------
@register
class NoStrength(StrengthModel):
    """Zero-strength material. Used for water bodies or open voids."""

    MODEL_ID = "no_strength"
    DISPLAY_NAME = "No Strength (water)"
    PARAMETERS: dict = {}

    def shear_strength(self, sigma_n_eff: float) -> float:
        return 0.0

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        return FactoredStrength(self, {}, "—")


# ----------------------------------------------------------------------
@register
class GeneralizedHoekBrown(_DesignDivisor, StrengthModel):
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
        # v0.1.225 (D224) -- 1 except on a design-factored copy.
        return max(0.0, tau) / self.design_divisor

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

    def tensile_strength(self) -> float:
        """Tensile strength of the rock mass, sigma_t = s*sigci/mb [kPa].

        v0.1.191 (D165). Set sigma'1 = sigma'3 = sigma_t in the criterion,
        sigma'1 = sigma'3 + sigci*(mb*sigma'3/sigci + s)^a, and what is left
        is (mb*sigma_t/sigci + s)^a = 0: the root of the bracket, which does
        not depend on a. It is biaxial tension, and Hoek, Carranza-Torres &
        Corkum (2002) take it as the tensile strength of the rock mass,
        citing Hoek (1983) for the uniaxial and the biaxial values being
        equal in brittle materials. Both sources are cited and not read
        here — no copy is held with this project's references — and the
        anchor is the algebra of the criterion itself, which this docstring
        states and ``tests/test_tensile_strength_rock_v1191.py`` checks.

        Why the biaxial root and not the uniaxial one (sigma'1 = 0): the
        check this feeds compares the NORMAL stress on a plane, and the
        Mohr envelope of the criterion ends at (sigma_t, 0), the failure
        circle of zero diameter at sigma'3 = sigma_t. The uniaxial root
        does depend on a, and it is smaller: with this class's default
        constants by 0.06 % at a = 0.5 and 1.2 % at a = 0.65; with the
        classic model's (m = 0.357, s = 0.0017) by 1.3 % and 12.8 %.

        That this is the tension the Tensile Stress Check should allow is
        an inference of this program: the reference lists this criterion
        among those that CAN carry a finite tensile strength and gives no
        rule.

        Caveat, measured and reported (D171): the envelope
        :meth:`shear_strength` evaluates is not yet this criterion's Mohr
        envelope — it gives tau(0) = 0 where the criterion gives 307.5 kPa
        with the default constants — so this strength belongs to the
        criterion, not to that approximation.

        Zero when sigci, mb or s is not positive and finite: no finite
        tensile strength follows from them.
        """
        sci = self.params["sigci"]
        mb = self.params["mb"]
        s = self.params["s"]
        if not all(math.isfinite(v) and v > 0.0 for v in (sci, mb, s)):
            return 0.0
        return s * sci / mb


# ----------------------------------------------------------------------
@register
class HoekBrown(_DesignDivisor, StrengthModel):
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

    Parameters as the reference documents them: UCS (intact), m, s.
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
        # v0.1.225 (D224) -- 1 except on a design-factored copy.
        return max(0.0, tau) / self.design_divisor

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

    def tensile_strength(self) -> float:
        """Tensile strength, sigma_t = s*sigci/m [kPa] — v0.1.191 (D165).

        The classic criterion is the generalised one with a = 0.5, and the
        root of its bracket is the same; the derivation, the sources (cited,
        not read here) and the D171 caveat are at
        :meth:`GeneralizedHoekBrown.tensile_strength` and hold for both.
        Zero when sigci, m or s is not positive and finite.
        """
        sci = self.params["sigci"]
        m = self.params["m"]
        s = self.params["s"]
        if not all(math.isfinite(v) and v > 0.0 for v in (sci, m, s)):
            return 0.0
        return s * sci / m


# ----------------------------------------------------------------------
@register
class PowerCurve(StrengthModel):
    """Power-curve envelope, in the form the reference uses:

        τ = c + a · (σ'ₙ + d)^b + σ'ₙ · tan(W)

    where:
        a, b — power-curve coefficients
        c    — cohesion intercept
        d    — normal-stress offset (so the envelope can pass below σ'ₙ=0)
        W    — Waviness angle (Patton-style joint roughness contribution)

    This is the form the reference documents for this strength type.
    The Waviness angle is NOT a friction angle — it represents
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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # τ/γ exactly: c/γ + (a/γ)(σ'ₙ + d)^b + σ'ₙ·tan W/γ. Until v0.1.225
        # only ``c`` was divided, because its name matched a list.
        f = factors.shear
        return _factor_params(self, {"c": f, "a": f}, {"waviness": f}, "τ")


# ----------------------------------------------------------------------
@register
class Hyperbolic(StrengthModel):
    """Hyperbolic strength envelope, in the form the reference uses:

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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # τ/γ exactly: (c∞/γ)·σ'ₙ·(tan φ0/γ) / (c∞/γ + σ'ₙ·tan φ0/γ).
        f = factors.shear
        return _factor_params(self, {"c_inf": f}, {"phi_0": f}, "τ")


# ----------------------------------------------------------------------
@register
class VerticalStressRatio(StrengthModel):
    """τ = max(K · σ'v, min_strength): the shear strength at a slice base is
    a constant K times the effective VERTICAL (overburden) stress there.

    v0.1.218 (D207) — the vertical stress is read from the slice context,
    ``ctx.sigma_v_eff``, as SHANSEP reads it. Until this version the model
    declared no context and multiplied K by σ'ₙ instead ("assumes
    σ'ₙ ≈ σ'v"), which made it a frictional soil through the origin with
    tan φ = K: a strength that grew with the normal stress the method
    resolved, and that Janbu's correction classed as φ-only (D80). The
    reference documentation defines the model with the vertical stress
    "computed from the total weight of each slice, and the pore pressure
    acting at the center of the base of each slice"; that is the context's
    ``(W + W_water)/b − u`` (v0.1.214, D166), with no seismic coefficient.
    With the context the strength no longer depends on σ'ₙ, so the method
    reads it as a cohesion (c = τ, tan φ = 0), the same way it reads SHANSEP.

    ``min_strength`` is a floor OGR adds; the reference model has none.
    Without a context (a caller that has no slice) σ'ₙ still stands in for
    σ'v, as it always did.
    """

    MODEL_ID = "vertical_stress_ratio"
    DISPLAY_NAME = "Vertical Stress Ratio"
    PARAMETERS = {
        "K": (0.25, "-", "Strength ratio K = τ/σ'v"),
        "min_strength": (0.0, "kPa", "Minimum shear strength"),
    }

    @property
    def needs_context(self) -> bool:
        return True

    def shear_strength(self, sigma_n_eff: float) -> float:
        return max(self.params["K"] * sigma_n_eff, self.params["min_strength"])

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        return max(self.params["K"] * max(ctx.sigma_v_eff, 0.0),
                   self.params["min_strength"])

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # K·σ'v is an undrained strength ratio (su/σ'v), so its cu factor.
        f = factors.undrained
        return _factor_params(self, {"K": f, "min_strength": f}, {}, "cu")


# ======================================================================
# v0.1.15 — Additional strength models matching the reference's catalogue
# ======================================================================

# ----------------------------------------------------------------------
@register
class BartonBandis(_DesignDivisor, StrengthModel):
    """Barton-Bandis criterion for rock joints / discontinuities.

        τ = σ'ₙ · tan( φr + JRC · log₁₀(JCS / σ'ₙ) )

    where φr is the residual friction angle, JRC the joint roughness
    coefficient, and JCS the joint wall compressive strength
    [Barton & Choubey, 1977; Barton & Bandis, 1990].

    The total friction angle (φr + JRC·log₁₀(JCS/σ'ₙ)) is capped to
    avoid unphysical values at very low σ'ₙ (the reference caps the effective
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
        # v0.1.225 (D224) -- the divisor is 1 except on a design copy.
        return sigma_n * math.tan(math.radians(total_angle)) \
            / self.design_divisor

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
    drained strength evaluated at σ_t). This mirrors the reference's
    Drained-Undrained type, where the undrained cap limits the
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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # c' and tan φ'; the threshold is a stress, not a strength.
        return _factor_params(self, {"cohesion": factors.cohesion},
                              {"phi": factors.tan_phi}, "c′, tan φ′")


# ----------------------------------------------------------------------
def _local_bedding_deg(model, ctx, fallback_param: str = "bedding_angle"):
    """The bedding orientation to measure against, in degrees.

    v0.1.126 — an anisotropic surface answers per point, so when the
    slicer has filled ``ctx.bedding_angle_deg`` that wins; otherwise the
    model falls back on the single global angle it carries. ``None`` and
    0.0 are different answers and are kept different: 0.0 is a horizontal
    bedding somebody entered, ``None`` is nobody having said.
    """
    if ctx is not None and getattr(ctx, "bedding_angle_deg", None) is not None:
        return float(ctx.bedding_angle_deg)
    return float(model.params.get(fallback_param, 0.0))


@register
class AnisotropicLinear(StrengthModel):
    """Anisotropic Linear strength (Mercer 2012, 2013).

    Mohr-Coulomb strength whose cohesion and friction angle depend on the
    acute angle α between the slice base and the bedding (the
    "1-direction"). With

        t = (|α| − A) / (B − A)

    the model is

        t ≤ 0:        c = c1,                 tan φ = tan φ1
        0 < t < 1:    c = c1(1 − t) + c2·t,   tan φ = tan φ1(1 − t) + tan φ2·t
        t ≥ 1:        c = c2,                 tan φ = tan φ2

    (c1, φ1) is the bedding strength, the minimum; (c2, φ2) the rock mass
    strength; A the half-width of the band where only the bedding strength
    applies and B − A the width of the linear transition. A = B is a step at
    A. What values A and B may take lives in
    ``ogr_core.project.rules.anisotropic_linear_refusal`` (0 ≤ A ≤ B).

    v0.1.225 (D216) -- the TANGENT of the friction angle is interpolated,
    as the reference documentation's equations write it ("the cohesion and
    the tangent of the friction angle can be computed for any plane
    orientation"). Until this version OGR interpolated the angle itself:
    with φ1 = 15° and φ2 = 30°, at t = 0.5 that gave 22.5° where the
    equations give 22.91°. The two ends are unchanged bit for bit and the
    parameters mean what they meant, so a saved project needs no migration:
    what was wrong was the formula.

    References:
        Mercer, K. (2012). The history and development of the anisotropic
            linear model: part 1. Australian Centre for Geomechanics, Perth.
        Mercer, K. (2013). The history and development of the anisotropic
            linear model: part 2. Australian Centre for Geomechanics, Perth.

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

    def _c_tan_phi(self, base_angle_deg: float, bedding_deg=None):
        """``(c, tan φ)`` on a plane at ``base_angle_deg``; see the class
        docstring for the equations."""
        a = self.params["A"]
        b = self.params["B"]
        bed = (self.params["bedding_angle"] if bedding_deg is None
               else float(bedding_deg))
        # Angular distance between slice base and bedding, folded to 0–90
        delta = abs(base_angle_deg - bed) % 180.0
        if delta > 90.0:
            delta = 180.0 - delta
        c1, c2 = self.params["c1"], self.params["c2"]
        tan1 = math.tan(math.radians(self.params["phi1"]))
        tan2 = math.tan(math.radians(self.params["phi2"]))
        if delta <= a:
            return c1, tan1
        if delta >= b or b - a < 1e-9:
            return c2, tan2
        t = (delta - a) / (b - a)
        return c1 * (1.0 - t) + c2 * t, tan1 * (1.0 - t) + tan2 * t

    def _c_phi_for_angle(self, base_angle_deg: float, bedding_deg=None):
        """``(c, φ in degrees)``, for callers that want the angle."""
        c, tan_phi = self._c_tan_phi(base_angle_deg, bedding_deg)
        return c, math.degrees(math.atan(tan_phi))

    def shear_strength(self, sigma_n_eff: float) -> float:
        """No slice, no orientation: the WEAKEST one (v0.1.230, D219, the
        owner's decision). c and tan φ are linear in t and t is monotone in
        the angle to the bedding, so the weakest is at 0 or at 90 degrees
        from it -- whatever A and B are, valid or not. It used to be the
        bedding strength (c1, φ1), which is the weakest only while the rock
        mass is the stronger of the two."""
        bed = float(self.params["bedding_angle"])
        s = max(sigma_n_eff, 0.0)
        return min(c + s * tan_phi
                   for c, tan_phi in (self._c_tan_phi(bed, bed),
                                      self._c_tan_phi(bed + 90.0, bed)))

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        base_deg = math.degrees(ctx.base_angle_rad)
        # v0.1.225 (D216) -- tan φ straight from the interpolation, never
        # through the angle and back.
        c, tan_phi = self._c_tan_phi(base_deg, _local_bedding_deg(self, ctx))
        return c + max(sigma_n_eff, 0.0) * tan_phi

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # c and tan φ are interpolated linearly (D216), so dividing both
        # ends divides the whole transition.
        f_c, f_t = factors.cohesion, factors.tan_phi
        return _factor_params(self, {"c1": f_c, "c2": f_c},
                              {"phi1": f_t, "phi2": f_t}, "c′, tan φ′")


# ----------------------------------------------------------------------
@register
class ShearNormalFunction(StrengthModel):
    """User-defined shear-strength function: τ as a piecewise-linear
    function of σ'ₙ, given by a table of (σ'ₙ, τ) points.

    Linear interpolation between points; constant extrapolation beyond
    the table range (the reference's convention).
    """

    MODEL_ID = "shear_normal_function"
    DISPLAY_NAME = "Shear/Normal Function"
    PARAMETERS = {}  # table stored separately

    #: The table a new material starts with; the dialog reads it from here
    #: (v0.1.227, D217) instead of keeping a copy of its own.
    DEFAULT_POINTS = ((0.0, 5.0), (100.0, 45.0), (300.0, 110.0))

    def __init__(self, **params):
        # Accept a 'points' kwarg (list of (sigma, tau)); not part of
        # the numeric PARAMETERS dict.
        pts = params.pop("points", None)
        super().__init__(**params)
        if pts is None:
            pts = list(self.DEFAULT_POINTS)
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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        return _factor_points(self, factors.shear)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["points"] = list(self.points)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ShearNormalFunction":
        return cls(points=data.get("points"), **data.get("params", {}))


def _factor_points(model, f: float) -> FactoredStrength:
    """Divide the τ of every (σ'ₙ, τ) point by ``f``: the table's own
    interpolation (linear, or by steps) then divides τ everywhere."""
    if f == 1.0:
        return FactoredStrength(model, {}, "τ")
    pts = [(s, t / f) for s, t in model.points]
    changes = {f"point {i} τ": (t, t / f)
               for i, (_s, t) in enumerate(model.points, start=1)}
    return FactoredStrength(type(model)(points=pts, **model.params),
                            changes, "τ")


# ----------------------------------------------------------------------
@register
class StepFunction(StrengthModel):
    """Step function of σ'ₙ: like Shear/Normal Function but the strength is
    a *step* function (each σ'ₙ interval has a constant τ), used when
    discrete test results are available. Uses the value of the lower
    bracketing point (no interpolation).

    v0.1.246 (D229) — this model was called "Discrete Function" until this
    version, and the reference's Discrete Function is another thing: a
    field of cu, or of c and φ, over the material (:class:`DiscreteFunction`
    now). It keeps its behaviour and its table under its own name, an
    extension of this program's: the reference has no step function of
    σ'ₙ. A file that saved it as ``discrete_function`` with (σ'ₙ, τ) points
    is read as this model, with the same τ to the last bit.
    """

    MODEL_ID = "step_function"
    DISPLAY_NAME = "Step Function (σ′ₙ)"
    PARAMETERS = {}

    #: v0.1.227 (D217) -- its own; the dialog used to show the shear-normal
    #: function's table for this model too.
    DEFAULT_POINTS = ((0.0, 10.0), (100.0, 50.0), (200.0, 80.0))

    def __init__(self, **params):
        pts = params.pop("points", None)
        super().__init__(**params)
        if pts is None:
            pts = list(self.DEFAULT_POINTS)
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

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        return _factor_points(self, factors.shear)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["points"] = list(self.points)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StepFunction":
        return cls(points=data.get("points"), **data.get("params", {}))


# ----------------------------------------------------------------------
@register
class DiscreteFunction(StrengthModel):
    """Discrete Function — the strength given at scattered (x, y) points of
    the material and interpolated at the base of each slice (v0.1.246,
    D229).

    The reference's documentation: the shear strength is specified "at
    discrete x,y locations throughout a material" and "can then be
    interpolated", for the undrained case (cu, φ = 0) or the drained one (c
    and φ), and for the drained one "the Interpolation is performed
    independently for Cohesion and friction angle". So:

        undrained   τ = cu(x, y)
        drained     τ = c(x, y) + max(σ'ₙ, 0)·tan φ(x, y)

    with (x, y) the middle of the slice base (``SliceContext.x_base`` and
    ``y_base``). ``method`` is the interpolation (``ogr_core.interpolation``:
    inverse distance, the default, being the one whose formula the
    reference's documentation writes; TIN; thin plate spline; linear by
    elevation), with the reference's secondary method where it cannot
    answer. Chugh, modified Chugh, the local spline as a method of its own
    and kriging are not implemented: declared, not approximated.

    After interpolating, cu and c are clipped at 0 and φ to [0, 90): a
    spline can overshoot between the data, and a negative strength is not
    an interpolation of positive ones.

    Without a point to read at — a caller with no slice, a plot of the
    envelope — the field is read at the centroid of its points: there is no
    right answer, and that one is at least inside the data.

    Design factors (D224): undrained, the cu category; drained, c′ and
    tan φ′. They divide what is INTERPOLATED, through divisors the analysis
    copy carries (the mould of the C/Phi Function): φ is interpolated as an
    angle, so factoring each point's tan φ would not divide tan φ between
    them.
    """

    MODEL_ID = "discrete_function"
    DISPLAY_NAME = "Discrete Function"
    PARAMETERS = {}

    FUNCTION_TYPES = ("undrained", "drained")
    METHODS = ("inverse_distance", "tin", "thin_plate_spline",
               "linear_by_elevation")
    #: A new material's table: three points of a field that grows with
    #: depth, so that every method has something to interpolate.
    DEFAULT_POINTS = {
        "undrained": ((0.0, 0.0, 30.0), (20.0, 0.0, 40.0),
                      (10.0, -10.0, 60.0)),
        "drained": ((0.0, 0.0, 5.0, 30.0), (20.0, 0.0, 8.0, 32.0),
                    (10.0, -10.0, 10.0, 34.0)),
    }

    design_c_divisor: float = 1.0
    design_tan_divisor: float = 1.0

    def __init__(self, **params):
        ftype = params.pop("function_type", "undrained")
        method = params.pop("method", "inverse_distance")
        pts = params.pop("points", None)
        super().__init__(**params)
        self.function_type = str(ftype)
        self.method = str(method)
        if pts is None:
            pts = self.DEFAULT_POINTS.get(self.function_type,
                                          self.DEFAULT_POINTS["undrained"])
        # Not validated here: what a valid table is lives in
        # ``ogr_core.project.rules.discrete_function_refusal``, which the
        # dialog, the API and the analysis ask.
        self.points = [tuple(float(v) for v in row) for row in pts]
        self._fields = None

    @property
    def needs_context(self) -> bool:
        return True

    def _field(self):
        """``(c or cu field, φ field or None)``, built once per table."""
        key = (self.function_type, self.method, tuple(self.points))
        if self._fields is None or self._fields[0] != key:
            from ogr_core.interpolation import ScatteredField
            method = (self.method if self.method in self.METHODS
                      else "inverse_distance")
            c = ScatteredField([(r[0], r[1], r[2]) for r in self.points
                                if len(r) >= 3], method)
            phi = (ScatteredField([(r[0], r[1], r[3]) for r in self.points
                                   if len(r) >= 4], method)
                   if self.function_type == "drained" else None)
            self._fields = (key, c, phi)
        return self._fields[1], self._fields[2]

    def _where(self, ctx):
        x = getattr(ctx, "x_base", None) if ctx is not None else None
        if x is not None:
            return float(x), float(ctx.y_base)
        pts = self.points
        if not pts:
            return 0.0, 0.0
        return (sum(r[0] for r in pts) / len(pts),
                sum(r[1] for r in pts) / len(pts))

    def c_phi_at(self, x: float, y: float) -> tuple:
        """``(c, φ)`` interpolated at (x, y) and clipped, before any design
        divisor; ``(cu, 0)`` for the undrained type."""
        c_field, phi_field = self._field()
        c = max(0.0, c_field.value_at(x, y))
        if phi_field is None:
            return c, 0.0
        phi = min(max(phi_field.value_at(x, y), 0.0), 89.999)
        return c, phi

    def shear_strength_ctx(self, sigma_n_eff: float, ctx=None) -> float:
        x, y = self._where(ctx)
        c, phi = self.c_phi_at(x, y)
        if self.function_type != "drained":
            return c / self.design_c_divisor
        return (c / self.design_c_divisor
                + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))
                / self.design_tan_divisor)

    def shear_strength(self, sigma_n_eff: float) -> float:
        return self.shear_strength_ctx(sigma_n_eff, None)

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        import copy
        if self.function_type != "drained":
            f = factors.undrained
            if f == 1.0:
                return FactoredStrength(self, {}, "cu")
            out = copy.deepcopy(self)
            out.design_c_divisor = self.design_c_divisor * f
            return FactoredStrength(
                out, {"cu divisor": (self.design_c_divisor,
                                     out.design_c_divisor)}, "cu")
        f_c, f_t = factors.cohesion, factors.tan_phi
        if f_c == 1.0 and f_t == 1.0:
            return FactoredStrength(self, {}, "c′, tan φ′")
        out = copy.deepcopy(self)
        changes = {}
        if f_c != 1.0:
            out.design_c_divisor = self.design_c_divisor * f_c
            changes["cohesion divisor"] = (self.design_c_divisor,
                                           out.design_c_divisor)
        if f_t != 1.0:
            out.design_tan_divisor = self.design_tan_divisor * f_t
            changes["tan φ divisor"] = (self.design_tan_divisor,
                                        out.design_tan_divisor)
        return FactoredStrength(out, changes, "c′, tan φ′")

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["function_type"] = self.function_type
        d["method"] = self.method
        d["points"] = [list(r) for r in self.points]
        if self.design_c_divisor != 1.0:
            d["design_c_divisor"] = self.design_c_divisor
        if self.design_tan_divisor != 1.0:
            d["design_tan_divisor"] = self.design_tan_divisor
        return d

    @classmethod
    def from_dict(cls, data: dict):
        """A Discrete Function — or, for a file written before v0.1.246, the
        model that file meant.

        Without ``function_type`` the table says what it is by the length
        of its rows: (σ'ₙ, τ) pairs are the step function this model was
        until then, rebuilt as :class:`StepFunction` with the same points
        (the same τ, bit for bit, so nothing is refused); rows of three or
        four are the reference's field, undrained or drained.
        """
        pts = data.get("points")
        ftype = data.get("function_type")
        if ftype is None:
            rows = list(pts or [])
            if rows and all(len(r) == 2 for r in rows):
                return StepFunction(points=pts, **data.get("params", {}))
            ftype = ("drained" if rows and all(len(r) == 4 for r in rows)
                     else "undrained")
        m = cls(points=pts, function_type=ftype,
                method=data.get("method", "inverse_distance"),
                **data.get("params", {}))
        m.design_c_divisor = float(data.get("design_c_divisor", 1.0))
        m.design_tan_divisor = float(data.get("design_tan_divisor", 1.0))
        return m


# ----------------------------------------------------------------------
@register
class CPhiFunction(StrengthModel):
    """C/Phi Function — Mohr-Coulomb cohesion and friction angle as
    functions of the effective normal stress (v0.1.229, D215).

    A table of ``rows`` ``(σ'ₙ, c, φ)``. The reference documentation
    defines the strength type by entering "Effective Normal stress, Cohesion
    and Friction Angle" and says "the interpolation is done on the cohesion
    and friction angle level, meaning for a given value of effective normal
    stress the cohesion and friction angle are interpolated". So between two
    rows c and φ (the angle, in degrees) are linear in σ'ₙ, and

        τ = c(σ'ₙ) + max(σ'ₙ, 0)·tan φ(σ'ₙ).

    Below the first row and above the last the end row holds: a decision,
    since the documentation does not say, and the convention of the
    shear-normal function. What a valid table is (at least one row, finite,
    σ'ₙ strictly increasing, c ≥ 0 and 0 ≤ φ < 90) lives in
    ``ogr_core.project.rules.c_phi_rows_refusal``; the model computes with
    what it is given, in the order given.

    Design factors (categories c′ and tan φ′, D224): the analysis copy
    divides the INTERPOLATED c and tan φ, through two divisors it carries,
    and not the rows: φ is interpolated as an angle, so factoring each
    row's tan φ would divide tan φ exactly only at the rows. The divisors
    are 1 -- this model bit for bit -- everywhere but in that copy.
    """

    MODEL_ID = "c_phi_function"
    DISPLAY_NAME = "C/Phi Function"
    PARAMETERS = {}

    #: The table a new material starts with: a gently curved envelope, the
    #: friction angle falling and the cohesion rising with the stress.
    DEFAULT_ROWS = ((0.0, 5.0, 35.0), (100.0, 10.0, 30.0),
                    (300.0, 20.0, 25.0))

    design_c_divisor: float = 1.0
    design_tan_divisor: float = 1.0

    def __init__(self, **params):
        rows = params.pop("rows", None)
        super().__init__(**params)
        if rows is None:
            rows = self.DEFAULT_ROWS
        # Not sorted: the order IS the table, and an unordered one is
        # refused by the rule rather than silently rearranged.
        self.rows = [(float(s), float(c), float(p)) for (s, c, p) in rows]

    def _segment(self, sigma: float):
        """``(s0, c0, φ0, s1, c1, φ1)`` of the segment holding ``sigma``, or
        None outside the table. A stress on a row belongs to the segment
        that starts there (the first one that holds it)."""
        rows = self.rows
        for (s0, c0, p0), (s1, c1, p1) in zip(rows, rows[1:]):
            if s0 <= sigma < s1:
                return s0, c0, p0, s1, c1, p1
        return None

    def c_phi_at(self, sigma: float):
        """``(c, φ in degrees)`` at ``sigma``, as the class docstring says."""
        rows = self.rows
        if not rows:
            return 0.0, 0.0
        if sigma <= rows[0][0]:
            return rows[0][1], rows[0][2]
        if sigma >= rows[-1][0]:
            return rows[-1][1], rows[-1][2]
        seg = self._segment(sigma)
        if seg is None:           # only an unordered table gets here
            return rows[-1][1], rows[-1][2]
        s0, c0, p0, s1, c1, p1 = seg
        f = (sigma - s0) / (s1 - s0)
        return c0 + f * (c1 - c0), p0 + f * (p1 - p0)

    def shear_strength(self, sigma_n_eff: float) -> float:
        c, phi = self.c_phi_at(sigma_n_eff)
        return (c / self.design_c_divisor
                + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))
                / self.design_tan_divisor)

    def tangent_slope(self, sigma_n_eff: float) -> float:
        """dτ/dσ'ₙ of :meth:`shear_strength`, exactly: on a segment
        ``c′ + tan φ + σ·(1 + tan²φ)·φ′`` (φ′ in radians per unit stress),
        and ``tan φ`` of the end row outside the table. At a row, the
        segment that starts there, as :meth:`_segment` picks it."""
        s = sigma_n_eff
        if not self.rows:
            return 0.0
        _c, phi = self.c_phi_at(s)
        t = math.tan(math.radians(phi))
        seg = self._segment(s)
        dc = dphi = 0.0
        if seg is not None:
            s0, c0, p0, s1, c1, p1 = seg
            dc = (c1 - c0) / (s1 - s0)
            dphi = math.radians(p1 - p0) / (s1 - s0)
        friction = (t + s * (1.0 + t * t) * dphi) if s >= 0.0 else 0.0
        return dc / self.design_c_divisor + friction / self.design_tan_divisor

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        f_c, f_t = factors.cohesion, factors.tan_phi
        if f_c == 1.0 and f_t == 1.0:
            return FactoredStrength(self, {}, "c′, tan φ′")
        import copy
        out = copy.deepcopy(self)
        changes = {}
        if f_c != 1.0:
            out.design_c_divisor = self.design_c_divisor * f_c
            changes["cohesion divisor"] = (self.design_c_divisor,
                                           out.design_c_divisor)
        if f_t != 1.0:
            out.design_tan_divisor = self.design_tan_divisor * f_t
            changes["tan φ divisor"] = (self.design_tan_divisor,
                                        out.design_tan_divisor)
        return FactoredStrength(out, changes, "c′, tan φ′")

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rows"] = [list(r) for r in self.rows]
        if self.design_c_divisor != 1.0:
            d["design_c_divisor"] = self.design_c_divisor
        if self.design_tan_divisor != 1.0:
            d["design_tan_divisor"] = self.design_tan_divisor
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "CPhiFunction":
        m = cls(rows=data.get("rows"), **data.get("params", {}))
        m.design_c_divisor = float(data.get("design_c_divisor", 1.0))
        m.design_tan_divisor = float(data.get("design_tan_divisor", 1.0))
        return m


# ----------------------------------------------------------------------
@register
class SHANSEP(StrengthModel):
    """SHANSEP undrained strength (Ladd & Foott 1974).

        su = max(A + σ'v · S · OCR^m, su_min)

    where S is the normally-consolidated strength ratio su/σ'v, OCR the
    over-consolidation ratio, m the SHANSEP exponent and σ'v the in-situ
    vertical effective stress at the slice base. The undrained strength su
    is the available shear strength (φ = 0 in total-stress terms), so
    τ = su, independent of σ'ₙ but dependent on σ'v.

    v0.1.218 (D207) — three decisions, each with its reason:

    * ``A`` is ADDED, the formula the reference documentation writes,
      ``τ = A + σ'v·S·(OCR)^m``, where it calls A the "minimum undrained
      shear strength". Until this version OGR had only ``su_min`` and took
      ``max(σ'v·S·OCR^m, su_min)``, which differs from the published formula
      whenever A > 0. ``su_min`` stays, as the floor it always was (decision
      of the owner, 2026-09-28): an existing project keeps its number, a
      random variable on it keeps applying, and A = 0 by default gives, bit
      for bit, what v0.1.217 gave.
    * With σ'v ≤ 0 (an artesian or empty column: the context clips it at
      zero) the formula is evaluated AT zero, τ = max(A, su_min). Until this
      version the model switched in silence to ``su(σ'ₙ)``, a frictional
      soil with tan φ = S·OCR^m, which is not the published model at any
      stress. The consolidation term of a soil under no effective
      overburden is zero; what is left is A.
    * σ'v subtracts the pore pressure of the slice INCLUDING any B-bar
      excess, on purpose. SHANSEP reads the consolidation stress, and an
      undrained load does not consolidate: with B-bar = 1 the load raises
      the total stress and the pore pressure by the same amount and leaves
      σ'v where it was before the load, which is exactly the stress the
      strength was consolidated under. The reference documentation's own
      excess-pore-pressure example keeps σ'v at 1872 lb/ft² before and after
      a drawdown for the same reason. (The support bond laws of
      ``ogr_core.support.bond`` compute their σ'v without the excess; that
      path is not this one.)

    Without a context (a caller that has no slice) σ'ₙ stands in for σ'v.

    Needs the vertical effective stress → ``needs_context = True``.
    """

    MODEL_ID = "shansep"
    DISPLAY_NAME = "SHANSEP"
    PARAMETERS = {
        "S": (0.25, "-", "Normally-consolidated strength ratio su/σ'v"),
        "m": (0.8, "-", "SHANSEP exponent"),
        "OCR": (1.0, "-", "Over-consolidation ratio"),
        "A": (0.0, "kPa",
              "Strength added to σ'v·S·OCR^m (the published formula's "
              "'minimum undrained strength')"),
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
        # The product is formed exactly as before v0.1.218 and A is added
        # in front of it, so A = 0 leaves every value bit for bit.
        su = self.params["A"] + max(sigma_v, 0.0) * S * (ocr ** m)
        return max(su, self.params["su_min"])

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self._su(sigma_n_eff)
        # v0.1.218 (D207) -- at σ'v ≤ 0 the formula at zero, not su(σ'ₙ).
        return self._su(max(ctx.sigma_v_eff, 0.0))

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # su is a cu, whatever gives it: dividing A, S and su_min divides
        # max(A + σ'v·S·OCR^m, su_min) exactly.
        f = factors.undrained
        return _factor_params(self, {"A": f, "S": f, "su_min": f}, {}, "cu")


# ----------------------------------------------------------------------
#: v0.1.218 (D209) -- what the analysis says about an Anisotropic Strength
#: Function saved as interpolated POINTS, and what the model raises if an
#: analysis reaches one anyway. One text, so the two cannot drift apart.
ANISOTROPIC_FUNCTION_LEGACY_NOTE = (
    "The Anisotropic Strength Function of material {name!r} was saved as "
    "interpolated points by a version before 0.1.218. Its table is now a "
    "list of angular RANGES (angle to, c, phi), as the reference documents "
    "this strength type, so the same rows would mean something else. Open "
    "the material, review the table as ranges and accept it.")


class LegacyAnisotropicTable(ValueError):
    """An Anisotropic Strength Function still holding the interpolated
    points of a file saved before v0.1.218 (D209). Never computed with."""


def fold_plane_angle_deg(angle_deg: float) -> float:
    """A plane inclination folded into (-90, 90] degrees.

    A plane has no sense: 165 degrees and -15 degrees are the same plane.
    The slicer's base angles already lie in (-90, 90); a support hands in
    the angle of its axis, ``atan2`` of head to tail, which spans
    (-180, 180] (v0.1.218, D209). The vertical, ±90, is +90.
    """
    a = float(angle_deg)
    while a > 90.0:
        a -= 180.0
    while a <= -90.0:
        a += 180.0
    return a


@register
class AnisotropicStrengthFunction(StrengthModel):
    """Anisotropic Strength Function — cohesion and friction angle given
    per RANGE of slice base inclination.

    The angle is the INCLINATION OF THE SLICE BASE itself, measured
    counter-clockwise from the horizontal, in (-90, 90] degrees: the
    slicer's ``alpha = atan2(dy, dx)`` with ``dx > 0``, in degrees. No
    bedding is involved. That is what separates this model from
    ``anisotropic_linear`` and Snowden's, which read the angle BETWEEN the
    base and a bedding direction: here the table itself is the anisotropy,
    written against the base inclination. The generalized model reads its
    ranges the same way since v0.1.225 (D218). Nor does the material dialog
    offer to link an anisotropic surface to it
    (``ogr_core.project.rules.reads_anisotropic_surface``).

    v0.1.218 (D209) — the table is a list of RANGES, ``rows`` of
    ``(angle_to, c, phi)``, as the reference documentation defines this
    strength type: "discrete angular ranges of slice base inclination, each
    with its own cohesion and friction angle", entered as "Angle To, c and
    phi"; the first range starts at -90 and the last must end at +90. So a
    row holds from the previous row's angle (exclusive; -90 for the first)
    up to its own (inclusive):

        [-90, a1] → (c1, φ1),   (a1, a2] → (c2, φ2),   …,   (a_{n-1}, 90]

    c and φ are CONSTANT inside a range. The documentation does not say
    which range owns an angle that falls exactly on a limit; the lower one
    does, the convention of ``GeneralizedAnisotropic._model_for_angle``
    (first rule that fits), written here as a decision. Until this version
    the same numbers were POINTS interpolated linearly, so one table meant
    two different materials in the two programs. What a valid table is
    (strictly increasing, the first above -90, the last +90) lives in
    ``ogr_core.project.rules.anisotropic_function_rows_refusal``; the model
    itself computes with any table it is given, and above the last "angle
    to" (only an invalid table can have one) it takes the last row.

    The rows are a new key, ``rows``, and not the old ``points``, on
    purpose (decision of the owner, 2026-09-28): the model interpolated
    from v0.1.15 to v0.1.125 and from v0.1.215 to v0.1.217, and a .ogr does
    not record the version that wrote it. A file that still holds
    ``points`` opens, keeps them (``legacy_points``) and round-trips them
    untouched, but is never computed with: the analysis refuses it
    (``ANISOTROPIC_FUNCTION_LEGACY_NOTE``) and ``_c_phi`` raises
    :class:`LegacyAnisotropicTable` if a caller gets past that. Reading the
    old points as ranges would change the number in silence.

    The angle is folded into (-90, 90] (:func:`fold_plane_angle_deg`): a
    support reads this model at the angle of its axis, which can point to
    -x, and a plane at 165 degrees is the plane at -15 (v0.1.218).

    Needs the slice base angle → ``needs_context = True``.
    """

    MODEL_ID = "anisotropic_strength_function"
    DISPLAY_NAME = "Anisotropic Strength Function"
    PARAMETERS = {}

    #: The example the reference documentation draws for this strength type:
    #: -90 to -30 with c = 10, phi = 35; -30 to 0 with c = 1, phi = 20; 0 to
    #: 90 with c = 5, phi = 10.
    DEFAULT_ROWS = ((-30.0, 10.0, 35.0), (0.0, 1.0, 20.0), (90.0, 5.0, 10.0))

    def __init__(self, **params):
        rows = params.pop("rows", None)
        legacy = params.pop("points", None)
        super().__init__(**params)
        self.legacy_points = None
        if rows is None and legacy is not None:
            # Kept as they were written; see the class docstring.
            self.legacy_points = [tuple(float(v) for v in p) for p in legacy]
            self.rows = []
            return
        if rows is None:
            rows = self.DEFAULT_ROWS
        # Not sorted: the order IS the table, and an unordered one is
        # refused by the rule rather than silently rearranged.
        self.rows = [(float(a), float(c), float(p)) for (a, c, p) in rows]

    @property
    def needs_context(self) -> bool:
        return True

    def _c_phi(self, angle_deg: float):
        if self.legacy_points is not None:
            raise LegacyAnisotropicTable(
                ANISOTROPIC_FUNCTION_LEGACY_NOTE.format(name="?"))
        rows = self.rows
        if not rows:
            return 0.0, 0.0
        a = fold_plane_angle_deg(angle_deg)
        for angle_to, c, phi in rows:
            # The limit belongs to the lower range. Within 1e-9 degree
            # because the angle arrives in radians: degrees(radians(-30))
            # is -29.999999999999996, and without the margin the documented
            # limit would change hands on the round trip.
            if a <= angle_to + 1e-9:
                return c, phi
        return rows[-1][1], rows[-1][2]

    def shear_strength(self, sigma_n_eff: float) -> float:
        """No slice, no orientation: the WEAKEST range at this stress
        (v0.1.230, D219, the owner's decision). It used to be the range of
        least COHESION, which is not the weakest one at any stress where a
        range with more cohesion has less friction: Janbu's soil type read
        this and classified the whole material by one row."""
        if self.legacy_points is not None:
            raise LegacyAnisotropicTable(
                ANISOTROPIC_FUNCTION_LEGACY_NOTE.format(name="?"))
        if not self.rows:
            return 0.0
        s = max(sigma_n_eff, 0.0)
        return min(c + s * math.tan(math.radians(phi))
                   for _a, c, phi in self.rows)

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        # v0.1.215 (D195) -- the ABSOLUTE base inclination, see the class
        # docstring. v0.1.126 passed the local bedding here as a second
        # argument, which ``_c_phi`` does not take: every method raised
        # TypeError on the first slice of such a material. The argument
        # belonged to Snowden's call, which v0.1.218 (D208) gave it.
        c, phi = self._c_phi(math.degrees(ctx.base_angle_rad))
        return c + max(sigma_n_eff, 0.0) * math.tan(math.radians(phi))

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        if self.legacy_points is not None:
            return FactoredStrength(
                self, {}, "c′, tan φ′",
                note=("a table saved as points before 0.1.218 is refused by "
                      "the analysis, so it was not factored"))
        f_c, f_t = factors.cohesion, factors.tan_phi
        rows, changes = [], {}
        for i, (a, c, phi) in enumerate(self.rows, start=1):
            c2 = c / f_c if f_c != 1.0 else c
            phi2 = tan_factored_angle(phi, f_t) if f_t != 1.0 else phi
            if c2 != c:
                changes[f"row {i} c"] = (c, c2)
            if phi2 != phi:
                changes[f"row {i} phi"] = (phi, phi2)
            rows.append((a, c2, phi2))
        if not changes:
            return FactoredStrength(self, {}, "c′, tan φ′")
        return FactoredStrength(
            AnisotropicStrengthFunction(rows=rows, **self.params), changes,
            "c′, tan φ′")

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.legacy_points is not None:
            d["points"] = [list(p) for p in self.legacy_points]
        else:
            d["rows"] = [list(r) for r in self.rows]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AnisotropicStrengthFunction":
        if data.get("rows") is not None:
            return cls(rows=data["rows"], **data.get("params", {}))
        return cls(points=data.get("points"), **data.get("params", {}))


# ----------------------------------------------------------------------
#: v0.1.225 (D218) -- what the analysis says about a Generalized Anisotropic
#: material that links an anisotropic surface. One text for the rule and the
#: dialog, like ``ANISOTROPIC_FUNCTION_LEGACY_NOTE``.
GENERALIZED_SURFACE_NOTE = (
    "The Generalized Anisotropic material {name!r} links an anisotropic "
    "surface. Its angle ranges are ABSOLUTE slice base inclinations, measured "
    "from the horizontal, as the reference defines this input; until 0.1.225 "
    "OGR subtracted the surface's bedding from the base angle first, so the "
    "same ranges would now select other rules. Open the material, review the "
    "ranges as absolute inclinations and accept it: the link is removed.")


class _AskedByChildren:
    """A ``NEEDS_*`` flag a composite model answers for its children.

    v0.1.225 (D218) -- on an INSTANCE it is true when any child that can be
    built reads the field, so the slicer and the support code measure it
    for a child that needs it. On the CLASS it is False, like any model
    that does not read the field by itself: a plain property would hand the
    class a property object, which is truthy, and the registry would then
    count the composite among the models that switch the expensive field on
    (``test_undrained_depth_v1120``).
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, obj, objtype=None) -> bool:
        if obj is None:
            return False
        return any(getattr(m, self.name, False) for m in obj._children())


class IncompleteGeneralizedAnisotropic(ValueError):
    """A Generalized Anisotropic model asked for an angle that no rule
    covers, or whose rule holds a model that cannot be built (v0.1.225,
    D218). The analysis refuses such a model before it starts
    (``ogr_core.project.rules.generalized_anisotropic_rules_refusal``);
    this is what a caller that gets past the refusal meets, instead of the
    strength of ZERO the model used to return in silence."""


@register
class GeneralizedAnisotropic(StrengthModel):
    """Generalized Anisotropic strength -- any registered strength model
    assigned to a RANGE of slice base inclination.

    Stored as ``rules``, a list of ``{angle_min, angle_max, model}`` where
    ``model`` is another registered model in its dict form. The reference
    documents this input ("Angle Range") as angle ranges ordered counter-
    clockwise from -90 to +90, each range starting where the previous one
    ends, "and assign a material to each range". Since v0.1.228 (D218b) a
    rule may name that material (``material_id``): the analysis then
    computes with the material's strength, resolved on its own copy of the
    project (``ogr_core.project.prepare_analysis_project``), and ``model``
    is the copy the editor shows.

    v0.1.225 (D218) -- five decisions, each with its reason:

    * The ranges are ABSOLUTE inclinations of the slice base, measured
      counter-clockwise from the horizontal and folded into (-90, 90]
      (:func:`fold_plane_angle_deg`): the reference's tutorial for this
      model says it in so many words ("Angles in the dialog are measured
      from horizontal, so 90 degrees represents vertical") and models a
      sub-horizontal bedding by giving it the band -10 to 10. Until this
      version OGR subtracted the local bedding of a linked anisotropic
      surface first (v0.1.126), which no source supports and which put the
      model in a different frame from the Anisotropic Strength Function
      whose ranges the reference describes in the same words (D195). In
      the reference an anisotropic surface belongs to the other input of
      this model, "Angle or Surface", which OGR does not implement; a
      material that still links one is refused
      (``GENERALIZED_SURFACE_NOTE``).
    * The angle is folded ALWAYS. It used to be folded only when a bedding
      was subtracted, so a support, which reads the model at the angle of
      its axis (``atan2``, in (-180, 180]), found no rule at 165 degrees and
      got a strength of zero.
    * The first rule that holds the angle wins, and a limit belongs to the
      lower range, within 1e-9 degree as in
      :class:`AnisotropicStrengthFunction` (the angle arrives in radians).
      What a valid set of rules is -- contiguous from -90 to +90, every
      model buildable -- lives in ``ogr_core.project.rules``; the model
      computes with what it is given, and an angle no rule holds, or a
      model that cannot be built, RAISES
      :class:`IncompleteGeneralizedAnisotropic`. Returning zero was a
      strength nobody entered, which looked like a result (D56, D94).
    * Each rule's model is built once and kept while its dict is unchanged
      (it used to be rebuilt from its dict on every call).
    * The child receives the slice context unchanged, and the model asks
      for the fields its children read (``NEEDS_LAYER_TOP``,
      ``NEEDS_SLOPE_DISTANCE``): a child that measures cu from the slope
      used to get no distance and fall back without a word.

    v0.1.247 (D230) -- what each material gives a slice. The weight is
    always the parent's (the reference: "The unit weight of the parent
    material will be used to calculate the weight of a slice"). The water
    is the parent's while ``use_parent_water`` is True, the default, which
    is what every earlier version computed; with it False, a base whose
    range LINKS a material takes that material's water parameters (water
    surface, Hu, Ru, grid, B-bar of loading, unsaturated strength), as the
    reference's option of the same name describes for the "Angle Range"
    input. The rapid drawdown is always the linked material's: the
    reference's option leaves it out. The slicer and the drawdown read
    these through ``linked_material_id``; a range with no link has no
    material, so the parent stands for it.

    v0.1.248 (D231a) -- the reference's other input, "Angle or Surface"
    (``input_type``): a BASE strength "for failure planes which are not
    within the defined orientation range" of the joints, and JOINTS, each at
    an angle or, from v0.1.249 (D231b), along an anisotropic surface
    (``definition``; the surface's orientation at the point closest to the
    base, as for any anisotropic surface), with its strength, a material or
    a model of its own. ``mapping`` says how a joint's strength gives way to
    the base's with the offset δ between the joint and the base (A and B,
    cosine or linear; :meth:`mapping_fraction`), ``joint_selection`` which
    joint answers when there are several, and ``use_base_if_weaker`` whether
    a base weaker than that joint takes over -- all three fixed once per
    function, as its dialog fixes them. The water and the drawdown are the
    parent's (its note: "Angle or Surface uses the water properties of the
    parent material"); ``use_parent_water`` belongs to "Angle Range" only.

    Needs the slice base angle → ``needs_context = True``.
    """

    MODEL_ID = "generalized_anisotropic"
    DISPLAY_NAME = "Generalized Anisotropic"
    PARAMETERS = {}

    #: v0.1.248 (D231a) -- the reference's two inputs, and the choices its
    #: "Angle or Surface" dialog fixes once per function.
    INPUT_TYPES = ("angle_range", "angle_or_surface")
    DEFINITIONS = ("angle", "surface")
    MAPPINGS = ("ab", "cosine", "linear")
    JOINT_SELECTIONS = ("worst_case", "closest")

    def __init__(self, **params):
        rules = params.pop("rules", None)
        use_parent_water = params.pop("use_parent_water", True)
        input_type = params.pop("input_type", "angle_range")
        base = params.pop("base", None)
        joints = params.pop("joints", None)
        definition = params.pop("definition", "angle")
        mapping = params.pop("mapping", "ab")
        joint_selection = params.pop("joint_selection", "worst_case")
        use_base_if_weaker = params.pop("use_base_if_weaker", True)
        super().__init__(**params)
        # rules: list of dicts {angle_min, angle_max, model: <dict>}
        self.rules = rules or []
        # v0.1.247 (D230) -- see the class docstring. Stored as given: what
        # a valid value is (a bool) lives in ``ogr_core.project.rules``.
        self.use_parent_water = use_parent_water
        # v0.1.248 (D231a) -- the "Angle or Surface" input: a base
        # {material_id?, model} and joints [{angle, A, B, material_id?,
        # model}]. Kept beside the ranges, as the reference keeps the two
        # lists apart; ``input_type`` says which one computes. Stored as
        # given; what is valid lives in ``ogr_core.project.rules``.
        self.input_type = input_type
        self.base = base
        self.joints = joints or []
        self.definition = definition
        self.mapping = mapping
        self.joint_selection = joint_selection
        self.use_base_if_weaker = use_base_if_weaker
        # child key -> (the dict the model was built from, a copy of it,
        # the model or the exception building it raised).
        self._built: dict = {}

    @property
    def needs_context(self) -> bool:
        return True

    @property
    def angle_or_surface(self) -> bool:
        """Whether the "Angle or Surface" input computes (v0.1.248)."""
        return self.input_type == "angle_or_surface"

    # ------------------------------------------------------------------
    # The children: the ranges of "Angle Range", the base and the joints of
    # "Angle or Surface". v0.1.248 (D231a) -- one walk for every consumer
    # of a link (the link resolution and its refusal, the property import,
    # the API, the design factors, the NEEDS_* flags), so that a child
    # added to the model cannot be missed by one of them.
    @staticmethod
    def child_label(key) -> str:
        """``rule 2``, ``the base`` or ``joint 1``, for messages."""
        kind, i = key
        if kind == "rules":
            return f"rule {i + 1}"
        if kind == "base":
            return "the base"
        return f"joint {i + 1}"

    def children_items(self, active_only: bool = False):
        """``(key, entry)`` of every child, ``key`` being ``("rules", i)``,
        ``("base", None)`` or ``("joints", j)`` and ``entry`` its dict
        (``model`` and an optional ``material_id``). ``active_only``: only
        the input that computes."""
        if not active_only or not self.angle_or_surface:
            for i, rule in enumerate(self.rules):
                yield ("rules", i), rule
        if not active_only or self.angle_or_surface:
            if self.base is not None:
                yield ("base", None), self.base
            for j, joint in enumerate(self.joints):
                yield ("joints", j), joint

    def with_children(self, new: dict) -> "GeneralizedAnisotropic":
        """A new model whose children under the keys of ``new`` are the
        entries given, and everything else as here."""
        return self.replaced(
            rules=[new.get(("rules", i), r) for i, r in enumerate(self.rules)],
            base=new.get(("base", None), self.base),
            joints=[new.get(("joints", j), jt)
                    for j, jt in enumerate(self.joints)])

    def _child_model(self, key, entry):
        """The model of a child, built once per content of its dict.

        Kept against a COPY of the dict and compared by value, so a dict
        edited in place is rebuilt rather than served stale. Raises
        :class:`IncompleteGeneralizedAnisotropic` when it cannot be built.
        """
        import copy

        from .strength_model import StrengthModel as _SM

        label = self.child_label(key)
        mdict = entry.get("model") if isinstance(entry, dict) else None
        cached = self._built.get(key)
        if cached is None or cached[0] is not mdict or cached[1] != mdict:
            if not mdict:
                built = IncompleteGeneralizedAnisotropic(
                    f"{label} has no model")
            else:
                try:
                    built = _SM.from_dict(mdict)
                except Exception as exc:  # noqa: BLE001 - reported below
                    built = IncompleteGeneralizedAnisotropic(
                        f"the model of {label} cannot be built: "
                        f"{type(exc).__name__}: {exc}")
            cached = (mdict, copy.deepcopy(mdict), built)
            self._built[key] = cached
        if isinstance(cached[2], Exception):
            raise cached[2]
        return cached[2]

    def _rule_model(self, i: int, rule):
        """The model of rule ``i``; see :meth:`_child_model`."""
        return self._child_model(("rules", i), rule)

    def _rule_index(self, angle_deg: float) -> int:
        """The index of the first rule that holds ``angle_deg``, folded.
        Raises :class:`IncompleteGeneralizedAnisotropic` where the model
        cannot answer (see the class docstring)."""
        a = fold_plane_angle_deg(angle_deg)
        for i, rule in enumerate(self.rules):
            if not isinstance(rule, dict):
                raise IncompleteGeneralizedAnisotropic(
                    f"rule {i + 1} is not a rule: {rule!r}")
            try:
                amin = float(rule.get("angle_min", -90.0))
                amax = float(rule.get("angle_max", 90.0))
            except (TypeError, ValueError):
                raise IncompleteGeneralizedAnisotropic(
                    f"the angles of rule {i + 1} are not numbers") from None
            if amin <= a <= amax + 1e-9:
                return i
        raise IncompleteGeneralizedAnisotropic(
            f"no rule holds a slice base at {a:g} degrees")

    def _model_for_angle(self, angle_deg: float):
        i = self._rule_index(angle_deg)
        return self._rule_model(i, self.rules[i])

    def rule_index_for_angle(self, angle_deg: float) -> int:
        """The index of the rule that holds a base at ``angle_deg``
        (absolute, folded as the strength folds it), v0.1.247 (D230).
        Raises :class:`IncompleteGeneralizedAnisotropic` where the strength
        does: the model never answers in place of a rule it lacks (D218)."""
        return self._rule_index(angle_deg)

    def linked_material_id(self, angle_deg: float):
        """The id of the material the range holding ``angle_deg`` links, or
        None when that range links none (v0.1.247, D230): whose water and
        drawdown parameters a base at that angle can take. Raises as
        :meth:`rule_index_for_angle` does.

        v0.1.248 (D231a) -- None with the "Angle or Surface" input, which
        blends a base and joints and so hands a base to no one material:
        the reference documents that it "uses the water properties of the
        parent material", and its drawdown is the parent's too."""
        if self.angle_or_surface:
            return None
        i = self.rule_index_for_angle(angle_deg)
        return self.rules[i].get("material_id") or None

    def replaced(self, **changes) -> "GeneralizedAnisotropic":
        """A new model with ``changes`` (``rules``, ``use_parent_water``, the
        fields of "Angle or Surface" or a parameter) and everything else as
        here (v0.1.247, D230). The places that rebuild the model -- the
        design factors, the link resolution, the property import, the API --
        go through here, so an attribute added to the model is not dropped
        by one of them."""
        kwargs = {"rules": self.rules,
                  "use_parent_water": self.use_parent_water,
                  "input_type": self.input_type,
                  "base": self.base,
                  "joints": self.joints,
                  "definition": self.definition,
                  "mapping": self.mapping,
                  "joint_selection": self.joint_selection,
                  "use_base_if_weaker": self.use_base_if_weaker,
                  **self.params}
        kwargs.update(changes)
        return GeneralizedAnisotropic(**kwargs)

    def _children(self):
        """The models of the input that computes, those that can be
        built."""
        out = []
        for key, entry in self.children_items(active_only=True):
            try:
                out.append(self._child_model(key, entry))
            except IncompleteGeneralizedAnisotropic:
                continue
        return out

    NEEDS_LAYER_TOP = _AskedByChildren("NEEDS_LAYER_TOP")
    NEEDS_SLOPE_DISTANCE = _AskedByChildren("NEEDS_SLOPE_DISTANCE")

    # ------------------------------------------------------------------
    # v0.1.248 (D231a) -- "Angle or Surface", joints by angle.
    @staticmethod
    def joint_offset_deg(base_angle_deg: float, joint_angle_deg: float):
        """δ, the ACUTE angle between a slice base and a joint, in [0, 90]
        degrees: the reference's "angle offset", folded as Anisotropic
        Linear folds its own (a plane has no sense)."""
        d = abs(float(base_angle_deg) - float(joint_angle_deg)) % 180.0
        return 180.0 - d if d > 90.0 else d

    def mapping_fraction(self, delta_deg: float, joint) -> float:
        """t, how far toward the BASE strength a joint at offset ``delta_deg``
        stands: 0 on the joint, 1 on the base. The reference's three
        mapping functions, from its figure of them (decisions written in
        D231, where its text is silent or contradicts it):

        * ``ab``: the joint up to A, the base from B, linear between --
          the transition of Anisotropic Linear (Mercer 2012, 2013); A = B
          is a step at A;
        * ``linear``: δ/90;
        * ``cosine``: sin²δ = (1 − cos 2δ)/2, the S-shaped curve of its
          figure, flat at both ends and crossing the linear one at 45°. Its
          text ("cosine 1 → base") says the opposite of the figure and of
          its own text for the linear function.
        """
        if self.mapping == "linear":
            return delta_deg / 90.0
        if self.mapping == "cosine":
            return math.sin(math.radians(delta_deg)) ** 2
        try:
            a = float(joint.get("A", 0.0))
            b = float(joint.get("B", 0.0))
        except (TypeError, ValueError, AttributeError):
            raise IncompleteGeneralizedAnisotropic(
                "the A and B of a joint are not numbers") from None
        if delta_deg <= a:
            return 0.0
        if delta_deg >= b or b - a < 1e-9:
            return 1.0
        return (delta_deg - a) / (b - a)

    def _joint_angle(self, j: int, joint, ctx) -> float:
        """The orientation of joint ``j`` at the base of ``ctx``: its angle,
        or (v0.1.249, D231b) the orientation of its anisotropic surface at
        the point closest to the base, which the slicer and the supports
        measure (``SliceContext.surface_angles``). Raises where there is
        none: a surface missing from the model is refused before the
        analysis, and a caller without a base has no point to read it at."""
        if self.definition == "surface":
            sid = joint.get("surface_id") if isinstance(joint, dict) else None
            angles = getattr(ctx, "surface_angles", None) or {}
            if sid not in angles:
                raise IncompleteGeneralizedAnisotropic(
                    f"joint {j + 1}: no orientation of its anisotropic "
                    f"surface at this base")
            return float(angles[sid])
        try:
            return float(joint.get("angle"))
        except (TypeError, ValueError, AttributeError):
            raise IncompleteGeneralizedAnisotropic(
                f"the angle of joint {j + 1} is not a number") from None

    @staticmethod
    def _read(model, sigma_n_eff, ctx):
        if ctx is not None and getattr(model, "needs_context", False):
            return model.shear_strength_ctx(sigma_n_eff, ctx)
        return model.shear_strength(sigma_n_eff)

    def _angle_or_surface_strength(self, sigma_n_eff, ctx, angle_deg):
        """τ on a base at ``angle_deg`` with the "Angle or Surface" input.

        For each joint, τ_j = (1 − t)·τ_joint + t·τ_base at the base's σ'ₙ,
        t from :meth:`mapping_fraction` (with Mohr-Coulomb children this is
        the linear interpolation of c and tan φ that Anisotropic Linear
        writes). Several joints: the lowest τ_j ("Worst Case") or the joint
        with the smallest offset, the first of the list on a tie
        ("Closest"). Then, with ``use_base_if_weaker``, min(τ, τ_base).
        """
        if not self.joints:
            raise IncompleteGeneralizedAnisotropic("there are no joints")
        tau_base = self._read(self._child_model(("base", None), self.base),
                              sigma_n_eff, ctx)
        chosen = None          # (τ_j, δ) of the joint that answers
        for j, joint in enumerate(self.joints):
            model = self._child_model(("joints", j), joint)
            joint_angle = self._joint_angle(j, joint, ctx)
            delta = self.joint_offset_deg(angle_deg, joint_angle)
            t = self.mapping_fraction(delta, joint)
            # The ends without the other strength: 0·τ is not 0 when τ is
            # an infinite strength.
            if t <= 0.0:
                tau = self._read(model, sigma_n_eff, ctx)
            elif t >= 1.0:
                tau = tau_base
            else:
                tau = ((1.0 - t) * self._read(model, sigma_n_eff, ctx)
                       + t * tau_base)
            if chosen is None:
                chosen = (tau, delta)
            elif self.joint_selection == "worst_case":
                if tau < chosen[0]:
                    chosen = (tau, delta)
            # "Closest": the smallest offset; offsets within 1e-9 degree are
            # a tie, which the first of the list wins -- the angle reaches
            # here through radians, and 30 degrees comes back as
            # 29.999999999999996, so an exact comparison would let the
            # rounding pick the joint.
            elif delta < chosen[1] - 1e-9:
                chosen = (tau, delta)
        tau = chosen[0]
        if self.use_base_if_weaker:
            tau = min(tau, tau_base)
        return tau

    # ------------------------------------------------------------------
    def shear_strength(self, sigma_n_eff: float) -> float:
        """No slice, no orientation: the WEAKEST of its children, each read
        without a slice too (v0.1.230, D219, the owner's decision): the
        ranges of "Angle Range", or the base and the joints of "Angle or
        Surface" (v0.1.248). It used to be the rule that holds a horizontal
        base. Raises, as the model does everywhere, when no child can be
        built."""
        children = self._children()
        if not children:
            raise IncompleteGeneralizedAnisotropic(
                "no rule holds a model that can be built"
                if not self.angle_or_surface else
                "neither the base nor any joint holds a model that can be "
                "built")
        return min(m.shear_strength(sigma_n_eff) for m in children)

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        angle = math.degrees(ctx.base_angle_rad) if ctx is not None else 0.0
        # v0.1.225 (D218) -- the ABSOLUTE base inclination; no bedding is
        # subtracted. See the class docstring.
        if self.angle_or_surface:
            return self._angle_or_surface_strength(sigma_n_eff, ctx, angle)
        m = self._model_for_angle(angle)
        if getattr(m, "needs_context", False):
            return m.shear_strength_ctx(sigma_n_eff, ctx)
        return m.shear_strength(sigma_n_eff)

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        """Each child's model by its own category (v0.1.225, D224): the
        ranges, or the base and the joints (v0.1.248); the reference
        documentation says the design factors apply to the child
        materials."""
        new, changes, notes = {}, {}, []
        for key, entry in self.children_items(active_only=True):
            label = self.child_label(key)
            if isinstance(entry, dict) and entry.get("material_id"):
                # v0.1.228 (D218b) -- a child that LINKS a material is given
                # that material's strength on the analysis copy, after the
                # factors: it is factored once, through the material.
                continue
            try:
                child = self._child_model(key, entry)
            except IncompleteGeneralizedAnisotropic:
                notes.append(f"{label}: its model cannot be built, so it "
                             f"was not factored")
                continue
            done = child.design_factored(factors)
            if done.changes:
                new_entry = dict(entry)
                new_entry["model"] = done.model.to_dict()
                new[key] = new_entry
                for k, v in done.changes.items():
                    changes[f"{label} {k}"] = v
            if done.note:
                notes.append(f"{label}: {done.note}")
        out = self.with_children(new) if changes else self
        how = ("the base and each joint by its own model"
               if self.angle_or_surface else "each rule by its own model")
        return FactoredStrength(out, changes, how,
                                note="; ".join(notes) or None)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rules"] = list(self.rules)
        d["use_parent_water"] = self.use_parent_water
        d["input_type"] = self.input_type
        d["base"] = self.base
        d["joints"] = list(self.joints)
        d["definition"] = self.definition
        d["mapping"] = self.mapping
        d["joint_selection"] = self.joint_selection
        d["use_base_if_weaker"] = self.use_base_if_weaker
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GeneralizedAnisotropic":
        # v0.1.247 (D230) -- a file without the key is from before the
        # option, and computed with the parent's water: True keeps it.
        # v0.1.248 (D231a) -- one without the "Angle or Surface" keys is an
        # "Angle Range" function, the only input before.
        return cls(rules=data.get("rules"),
                   use_parent_water=data.get("use_parent_water", True),
                   input_type=data.get("input_type", "angle_range"),
                   base=data.get("base"),
                   joints=data.get("joints"),
                   definition=data.get("definition", "angle"),
                   mapping=data.get("mapping", "ab"),
                   joint_selection=data.get("joint_selection", "worst_case"),
                   use_base_if_weaker=data.get("use_base_if_weaker", True),
                   **data.get("params", {}))


# ----------------------------------------------------------------------
#: v0.1.229 (D215) -- what the analysis says about a Snowden material saved
#: with the parameters of the model OGR had before this version, and what
#: the model raises if an analysis reaches one anyway. One text for both.
SNOWDEN_LEGACY_NOTE = (
    "The Snowden Modified Anisotropic Linear material {name!r} was saved by a "
    "version before 0.1.229, with c1, phi1, c2, phi2 and a single B and a "
    "cosine transition of the friction ANGLE. The model is now the one the "
    "reference documents: a linear transition of the shear strength between "
    "a bedding and a rock mass strength function, with A1, B1, A2 and B2. "
    "The material shows the nearest such form (A1 = A2 = 0, B1 = B2 = B, one "
    "C/Phi row per function), whose numbers are not the old ones: review it "
    "and accept it.")

#: The parameters of the model before v0.1.229; any of them marks a file
#: written by it.
_SNOWDEN_LEGACY_KEYS = ("c1", "phi1", "c2", "phi2", "B")


class LegacySnowden(ValueError):
    """A Snowden material still holding the c1, phi1, c2, phi2 and B of a
    file saved before v0.1.229 (D215). Never computed with."""


class IncompleteSnowden(ValueError):
    """A Snowden material whose bedding or rock mass strength function is
    not a shear-normal or a C/Phi function, or cannot be built (v0.1.229).
    The analysis refuses such a model before it starts
    (``ogr_core.project.rules.snowden_refusal``); this is what a caller that
    gets past the refusal meets."""


@register
class SnowdenModifiedAnisotropicLinear(StrengthModel):
    """Snowden Modified Anisotropic Linear (Mercer 2012, 2013).

    The Anisotropic Linear model with the two additions the reference
    documentation describes (v0.1.229, D215):

    * a NON-SYMMETRIC anisotropy function of four parameters. With α the
      angle from the bedding (the 1-direction) to the slice base, measured
      counter-clockwise and folded into (-90, 90] (the documentation's
      figures: α from direction 1 to the plane; A1 and B1 on the negative
      side, A2 and B2 on the positive one),

          (A, B) = (A1, B1) if α < 0,   (A2, B2) if α ≥ 0
          t = clip((|α| − A) / (B − A), 0, 1)

      and A = B is a step at A;

    * the bedding and rock mass strengths are FUNCTIONS of σ'ₙ, each a
      shear-normal function or a C/Phi function ("Shear-Normal function" or
      "Cohesion-Friction function"), and the strength of an intermediate
      orientation is "a weighted average determined by the linear transition
      of the anisotropy function":

          τ = (1 − t)·τ_bedding(σ'ₙ) + t·τ_rock mass(σ'ₙ).

    With one C/Phi row per function, (c1, φ1) and (c2, φ2), and A1 = A2,
    B1 = B2, this is Anisotropic Linear exactly (D216 interpolates c and
    tan φ, which is the same line in t). The base angle is the slicer's
    ``atan2(dy, dx)`` with dx > 0, a geometric inclination whatever the
    failure direction, so the sign of α is the figures' sign. The bedding
    is the local one of a linked anisotropic surface when the slicer gives
    it (D208), else ``bedding_angle``.

    Without a slice there is no orientation, and the model answers the
    WEAKEST one: the least of the strengths at α = 0, at α → −90 and at
    α = +90 (the strength is linear in t and t is monotone in |α| on each
    side, so no other α can be weaker).

    Until v0.1.229 OGR had another model under this name: c1, φ1, c2, φ2 and
    one B, with a symmetric cosine transition of c and of the ANGLE φ. A
    file that still holds those parameters opens, keeps them
    (``legacy_params``) and round-trips them untouched, and shows the
    nearest form of this model for the user to review; it is never computed
    with: the analysis refuses it (``SNOWDEN_LEGACY_NOTE``) and the model
    raises :class:`LegacySnowden` if a caller gets past that.

    What values A1..B2 and the two functions may take lives in
    ``ogr_core.project.rules.snowden_refusal``. A function that cannot be
    built does not stop the material from loading: the rule refuses it and
    the model raises :class:`IncompleteSnowden` if it is computed with.

    References:
        Mercer, K. (2012). The history and development of the anisotropic
            linear model: part 1. Australian Centre for Geomechanics, Perth.
        Mercer, K. (2013). The history and development of the anisotropic
            linear model: part 2. Australian Centre for Geomechanics, Perth.

    Needs the slice base angle → ``needs_context = True``.
    """

    MODEL_ID = "snowden_anisotropic_linear"
    DISPLAY_NAME = "Snowden Modified Anisotropic Linear"
    PARAMETERS = {
        "bedding_angle": (0.0, "deg",
            "Orientation of the bedding (the 1-direction), counter-clockwise "
            "from horizontal"),
        "A1": (10.0, "deg",
            "Bedding strength only up to this angle, on the clockwise side "
            "of the bedding (negative angles)"),
        "B1": (30.0, "deg",
            "Rock mass strength only beyond this angle, on the clockwise "
            "side of the bedding"),
        "A2": (10.0, "deg",
            "Bedding strength only up to this angle, on the "
            "counter-clockwise side of the bedding"),
        "B2": (30.0, "deg",
            "Rock mass strength only beyond this angle, on the "
            "counter-clockwise side of the bedding"),
    }

    #: The strength functions the bedding and the rock mass may be.
    FUNCTION_IDS = ("shear_normal_function", "c_phi_function")
    #: One C/Phi row each, the default Anisotropic Linear's (c1, φ1) and
    #: (c2, φ2): with the default A and B the two defaults are one material.
    DEFAULT_BEDDING = {"model_id": "c_phi_function", "params": {},
                       "rows": [[0.0, 5.0, 15.0]]}
    DEFAULT_ROCK_MASS = {"model_id": "c_phi_function", "params": {},
                         "rows": [[0.0, 20.0, 30.0]]}

    def __init__(self, **params):
        import copy
        bedding = params.pop("bedding", None)
        rock_mass = params.pop("rock_mass", None)
        self.legacy_params = None
        if any(k in params for k in _SNOWDEN_LEGACY_KEYS):
            # Kept exactly as written, for the round trip; the model shows
            # the nearest form of the new one (see the class docstring).
            self.legacy_params = {k: float(v) for k, v in params.items()}
            old = dict(self.legacy_params)
            b = old.get("B", 30.0)
            bedding = {"model_id": "c_phi_function", "params": {},
                       "rows": [[0.0, old.get("c1", 5.0),
                                 old.get("phi1", 15.0)]]}
            rock_mass = {"model_id": "c_phi_function", "params": {},
                         "rows": [[0.0, old.get("c2", 20.0),
                                   old.get("phi2", 30.0)]]}
            params = {"bedding_angle": old.get("bedding_angle", 0.0),
                      "A1": 0.0, "B1": b, "A2": 0.0, "B2": b}
        super().__init__(**params)
        self.bedding = copy.deepcopy(
            self.DEFAULT_BEDDING if bedding is None else bedding)
        self.rock_mass = copy.deepcopy(
            self.DEFAULT_ROCK_MASS if rock_mass is None else rock_mass)
        # function name -> (the dict it was built from, a copy of it, the
        # model or the exception building it raised); as in Generalized.
        self._built: dict = {}

    @property
    def needs_context(self) -> bool:
        return True

    # ------------------------------------------------------------------
    def function(self, which: str) -> StrengthModel:
        """The ``"bedding"`` or ``"rock_mass"`` strength function, built once
        per content of its dict. Raises :class:`IncompleteSnowden` when it is
        not a shear-normal or C/Phi function or cannot be built."""
        import copy
        data = getattr(self, which)
        cached = self._built.get(which)
        if cached is None or cached[0] is not data or cached[1] != data:
            if not isinstance(data, dict) or \
                    data.get("model_id") not in self.FUNCTION_IDS:
                built = IncompleteSnowden(
                    f"the {which.replace('_', ' ')} function must be a "
                    f"Shear/Normal Function or a C/Phi Function, got "
                    f"{data!r}")
            else:
                try:
                    built = StrengthModel.from_dict(data)
                except Exception as exc:  # noqa: BLE001 - reported below
                    built = IncompleteSnowden(
                        f"the {which.replace('_', ' ')} function cannot be "
                        f"built: {type(exc).__name__}: {exc}")
            cached = (data, copy.deepcopy(data), built)
            self._built[which] = cached
        if isinstance(cached[2], Exception):
            raise cached[2]
        return cached[2]

    def weight(self, alpha_deg: float) -> float:
        """t of the class docstring at ``alpha_deg``, already folded: 0 is
        the bedding strength only, 1 the rock mass strength only."""
        if alpha_deg < 0.0:
            a, b = self.params["A1"], self.params["B1"]
        else:
            a, b = self.params["A2"], self.params["B2"]
        d = abs(alpha_deg)
        if d <= a:
            return 0.0
        if d >= b or b - a < 1e-9:
            return 1.0
        return (d - a) / (b - a)

    def _blend(self, sigma_n_eff: float, t: float) -> float:
        if t <= 0.0:
            return self.function("bedding").shear_strength(sigma_n_eff)
        if t >= 1.0:
            return self.function("rock_mass").shear_strength(sigma_n_eff)
        bed = self.function("bedding").shear_strength(sigma_n_eff)
        rock = self.function("rock_mass").shear_strength(sigma_n_eff)
        return (1.0 - t) * bed + t * rock

    def _refuse_legacy(self) -> None:
        if self.legacy_params is not None:
            raise LegacySnowden(SNOWDEN_LEGACY_NOTE.format(name="?"))

    def shear_strength(self, sigma_n_eff: float) -> float:
        # No slice, no orientation: the weakest one (class docstring).
        self._refuse_legacy()
        return min(self._blend(sigma_n_eff, self.weight(a))
                   for a in (0.0, -90.0, 90.0))

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        self._refuse_legacy()
        # v0.1.218 (D208) -- the LOCAL bedding when a surface gives one.
        alpha = fold_plane_angle_deg(math.degrees(ctx.base_angle_rad)
                                     - _local_bedding_deg(self, ctx))
        return self._blend(sigma_n_eff, self.weight(alpha))

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        """Each function by its own model (D224): a shear-normal function as
        τ, a C/Phi function as c′ and tan φ′. The transition is linear in the
        two strengths, so dividing both divides the blend."""
        if self.legacy_params is not None:
            return FactoredStrength(
                self, {}, "each function by its own model",
                note=("a material saved before 0.1.229 is refused by the "
                      "analysis, so it was not factored"))
        import copy
        changes, notes, new = {}, [], {}
        for which in ("bedding", "rock_mass"):
            try:
                fn = self.function(which)
            except IncompleteSnowden:
                notes.append(f"its {which.replace('_', ' ')} function cannot "
                             f"be built, so it was not factored")
                continue
            done = fn.design_factored(factors)
            if done.changes:
                new[which] = done.model.to_dict()
                for k, v in done.changes.items():
                    changes[f"{which.replace('_', ' ')} {k}"] = v
            if done.note:
                notes.append(f"{which.replace('_', ' ')}: {done.note}")
        out = self
        if new:
            out = copy.deepcopy(self)
            for which, data in new.items():
                setattr(out, which, data)
            out._built = {}
        return FactoredStrength(out, changes, "each function by its own model",
                                note="; ".join(notes) or None)

    def to_dict(self) -> dict:
        import copy
        if self.legacy_params is not None:
            return {"model_id": self.MODEL_ID,
                    "params": dict(self.legacy_params)}
        d = super().to_dict()
        d["bedding"] = copy.deepcopy(self.bedding)
        d["rock_mass"] = copy.deepcopy(self.rock_mass)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SnowdenModifiedAnisotropicLinear":
        return cls(bedding=data.get("bedding"),
                   rock_mass=data.get("rock_mass"),
                   **data.get("params", {}))


# ======================================================================
# v0.1.120 — Undrained strength that VARIES LINEARLY WITH DEPTH
# ======================================================================
#
# Why a straight line, and why it is not invented: in a normally
# consolidated clay the undrained strength is proportional to the vertical
# effective stress, su/σ'v ≈ const (Skempton 1957; Ladd & Foott 1974), and
# σ'v grows linearly with depth under a level deposit. A soft-clay
# foundation is therefore described in practice by
#
#       su(z) = su0 + ρ · z
#
# and that is how the published cases this project validates against state
# it: Low (1989) gives 15 → 30 kPa across a 4 m layer, Duncan (2000) gives
# "100 psf at elevation −20 ft, increasing at 9.8 psf/ft", and Duncan and
# Wright (2005) give cu = 300 + cz·z psf for four values of cz.
#
# What changes between the three models below is ONLY where z is measured
# from. They are three separate registry entries rather than one model with
# a mode switch because this registry is flat by construction: the GUI
# builds its list from REGISTRY.all(), a saved project stores MODEL_ID, and
# a mode that is neither of those would have to be smuggled through both.
# Splitting them also leaves ``undrained`` — the model every existing
# project uses — untouched.


class _UndrainedLinearBase(StrengthModel):
    """Shared body of the three depth-dependent undrained models.

    φ = 0, so τ = c(z) and the strength does not depend on σ'ₙ at all.
    Subclasses supply ``_depth_from(ctx)``; everything else — the linear
    law and the cutoff — lives here so the two cannot drift apart.

    **The cutoff is asymmetric, on purpose.** When it is enabled the value
    is a MAXIMUM strength; but if the rate of change is NEGATIVE the same
    value acts as a MINIMUM instead. That is the rule as stated, and it is
    the useful one: the cutoff always bounds the side the straight line
    runs away on.

    Not registered: it has no MODEL_ID and describes no criterion by
    itself.
    """

    #: Name of the PARAMETERS entry holding the cohesion at z = 0.
    _C_REF: ClassVar[str] = "cohesion_top"

    def __init__(self, **params) -> None:
        # ``cutoff_enabled`` is a BOOLEAN and PARAMETERS only holds floats,
        # so it travels beside them — the same place ``points`` and
        # ``rules`` travel for the table-based models.
        cutoff_enabled = params.pop("cutoff_enabled", False)
        super().__init__(**params)
        self.cutoff_enabled = bool(cutoff_enabled)

    @property
    def needs_context(self) -> bool:
        return True

    # ------------------------------------------------------------------
    def cohesion_at(self, depth: float) -> float:
        """Undrained cohesion at ``depth`` below this model's reference,
        with the cutoff applied.

        Reference: see the module note above (Skempton 1957 and Ladd &
        Foott 1974 for the proportionality that makes the profile linear;
        Low 1989, Duncan 2000 and Duncan and Wright 2005 for the published
        profiles this reproduces).
        """
        rate = self.params["cohesion_change"]
        c = self.params[self._C_REF] + rate * depth
        if self.cutoff_enabled:
            cut = self.params["cutoff"]
            # Negative rate → the line falls with depth → the cutoff is the
            # floor. Positive or zero → it rises → the cutoff is the cap.
            c = max(c, cut) if rate < 0.0 else min(c, cut)
        return c

    def _depth_from(self, ctx: SliceContext):
        """Depth of the slice base below this model's reference, or None
        when the context does not carry what this model needs."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    def shear_strength(self, sigma_n_eff: float) -> float:
        # No context: the only depth that is not a guess is zero, which is
        # the reference elevation itself. Callers that plot an envelope
        # against σ'ₙ land here, and a horizontal line is the honest shape
        # for a φ = 0 material.
        return self.cohesion_at(0.0)

    def shear_strength_ctx(self, sigma_n_eff, ctx: SliceContext | None = None):
        if ctx is None:
            return self.shear_strength(sigma_n_eff)
        depth = self._depth_from(ctx)
        if depth is None:
            return self.shear_strength(sigma_n_eff)
        return self.cohesion_at(depth)

    def tangent_slope(self, sigma_n_eff: float) -> float:
        return 0.0  # φ = 0: the envelope is horizontal in σ'ₙ

    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        # The whole profile is a cu: the value at the reference, the rate
        # and the cutoff are divided alike, so cu(z)/γ exactly. Until
        # v0.1.225 only a parameter NAMED cohesion_top was, which left
        # cu(z) = c_top/γ + Δc·z in two models and the datum one untouched.
        f = factors.undrained
        return _factor_params(self, {self._C_REF: f, "cohesion_change": f,
                                     "cutoff": f}, {}, "cu")

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        d = super().to_dict()
        d["cutoff_enabled"] = self.cutoff_enabled
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "_UndrainedLinearBase":
        return cls(cutoff_enabled=bool(data.get("cutoff_enabled", False)),
                   **data.get("params", {}))


# ----------------------------------------------------------------------
@register
class UndrainedDepthFromLayerTop(_UndrainedLinearBase):
    """Undrained cohesion measured from the TOP OF THE LOCAL LAYER.

        c = c_top + Δc · (y_top − y)

    where y_top is the top of the material band the slice base sits in —
    not the ground surface. Under an embankment on three stacked clays,
    each slice measures from the top of its own clay.

    This is the form the published cases state their profiles in: Low
    (1989) and Borges and Cardoso (2002) both tabulate a Cu at the top and
    a Cu at the bottom of each layer, which is (c_top, Δc) written twice.
    """

    MODEL_ID = "undrained_depth_layer"
    DISPLAY_NAME = "Undrained, c(depth below layer top)"
    NEEDS_LAYER_TOP = True
    PARAMETERS = {
        "cohesion_top": (20.0, "kPa", "Undrained cohesion at the layer top"),
        "cohesion_change": (2.0, "kPa/m",
            "Rate of change of cohesion with depth below the layer top"),
        "cutoff": (100.0, "kPa",
            "Cutoff: a maximum, or a minimum when the rate is negative "
            "(applied only when enabled)"),
    }

    def _depth_from(self, ctx: SliceContext):
        if ctx.layer_top_y is None:
            return None
        return ctx.layer_top_y - ctx.y_base


# ----------------------------------------------------------------------
@register
class UndrainedDepthFromDatum(_UndrainedLinearBase):
    """Undrained cohesion measured from a horizontal DATUM elevation.

        c = c_datum + Δc · (y_datum − y)

    With Δc positive the cohesion GROWS below the datum and FALLS above
    it: the law is a straight line in elevation, not a one-sided ramp, and
    nothing here bounds it from below. That matters wherever the material
    reaches well above its datum — Duncan (2000) states the San Francisco
    Bay Mud profile as "100 psf at elevation −20 ft, +9.8 psf/ft", and that
    line reaches zero at elevation −9.8.

    Unlike the layer-top form this needs no geometry beyond the slice's own
    elevation, so it is the one form that works from any caller.
    """

    MODEL_ID = "undrained_depth_datum"
    DISPLAY_NAME = "Undrained, c(depth below datum)"
    _C_REF = "cohesion_datum"
    PARAMETERS = {
        "cohesion_datum": (20.0, "kPa", "Undrained cohesion at the datum"),
        "cohesion_change": (2.0, "kPa/m",
            "Rate of change of cohesion with (y_datum − y)"),
        "datum": (0.0, "m", "Datum elevation"),
        "cutoff": (100.0, "kPa",
            "Cutoff: a maximum, or a minimum when the rate is negative "
            "(applied only when enabled)"),
    }

    def _depth_from(self, ctx: SliceContext):
        return self.params["datum"] - ctx.y_base


# ----------------------------------------------------------------------
@register
class UndrainedDistanceToSlope(_UndrainedLinearBase):
    """Undrained cohesion measured along the TRUE DISTANCE to the slope.

        c = c_top + Δc · d

    where d is the distance from the slice base centre to the nearest
    point of the ground profile — the perpendicular one under a slope
    face, not the vertical one. On level ground the two coincide, which is
    what ties this model to the layer-top form as an exact identity.
    """

    MODEL_ID = "undrained_slope_distance"
    DISPLAY_NAME = "Undrained, c(distance to slope)"
    NEEDS_SLOPE_DISTANCE = True
    PARAMETERS = {
        "cohesion_top": (20.0, "kPa",
            "Undrained cohesion at the slope surface"),
        "cohesion_change": (2.0, "kPa/m",
            "Rate of change of cohesion with distance from the slope"),
        "cutoff": (100.0, "kPa",
            "Cutoff: a maximum, or a minimum when the rate is negative "
            "(applied only when enabled)"),
    }

    def _depth_from(self, ctx: SliceContext):
        return ctx.slope_distance
