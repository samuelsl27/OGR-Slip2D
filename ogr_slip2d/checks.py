# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Post-analysis admissibility checks (anomaly A3).

Implements the two checks the reference performs on a slip surface
*after* the factor of safety has converged:

**Tensile Stress Check.** Negative effective normal stress (tension) can
appear on the base of a slice — typically where the pore pressure is high
or where the base is steeply inclined, as happens near the crest of a
deep-seated surface. When it does, the slice forces may not be
kinematically feasible and the safety factor can be "inaccurate or in the
worst case, completely invalid". The check therefore:

* runs **after** the iteration has converged, never during it;
* tests only a *percentage of slices starting from the toe* (default
  95 %), because the slices at the very crest are legitimately in tension
  — they are, in reality, the tension-crack zone;
* allows zero tensile stress for every strength model **except**
  Hoek-Brown, Generalised Hoek-Brown and Shear-Normal Function, which
  have a genuine finite tensile strength;
* invalidates the surface when the limit is exceeded (the reference
  writes error code -120 in place of the safety factor).

**m-alpha Check.** ``m_alpha = cos(alpha) + s·sin(alpha)·tan(phi)/F``,
where ``s`` is the sense of sliding, is the denominator of the base normal
force. Whitman & Bailey (1967) showed that
once it drops below about 0.2 the resulting safety factor becomes
unreliable: a small positive value inflates the normal force and hence
the shear resistance, and a negative value can produce negative
resistance and meaningless factors of safety. Surfaces whose final
iteration has ``m_alpha < 0.2`` on any slice are rejected.

Both checks are **disabled by default**, matching the reference, where
tensile normal stresses are permitted unless the user opts in.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# Strength models that can carry a genuine tensile strength. For every
# other model the allowable tensile stress is zero.
_TENSILE_CAPABLE = {
    "hoek_brown",
    "generalized_hoek_brown",
    "shear_normal_function",
}

M_ALPHA_LIMIT = 0.2          # Whitman & Bailey (1967)


# ----------------------------------------------------------------------
def _material_tensile_strength(material) -> float:
    """Allowable tensile stress on a slice base, as a POSITIVE magnitude.

    Zero for all strength criteria except Hoek-Brown, Generalised
    Hoek-Brown and Shear-Normal Function.
    """
    if material is None:
        return 0.0
    strength = getattr(material, "strength", None)
    model_id = getattr(strength, "MODEL_ID", None) or getattr(
        strength, "model_id", None)
    if model_id not in _TENSILE_CAPABLE:
        return 0.0
    # Hoek-Brown family: sigma_t = s*sigma_ci/mb (magnitude)
    sci = getattr(strength, "sigma_ci", None)
    mb = getattr(strength, "mb", None) or getattr(strength, "m_b", None)
    sparam = getattr(strength, "s", None)
    if sci and mb and sparam is not None and mb > 0:
        try:
            return abs(float(sparam) * float(sci) / float(mb))
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0
    # Shear-Normal functions may declare it explicitly
    for attr in ("tensile_strength", "sigma_t"):
        v = getattr(strength, attr, None)
        if v:
            try:
                return abs(float(v))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


# ----------------------------------------------------------------------
def _slide_sign(result) -> float:
    """The sense of sliding, derived exactly as the solvers derive it.

    v0.1.82 — this was the bug. ``m_alpha`` is not symmetric in ``alpha``,
    so it can only be evaluated in the same sign convention the method
    used. Every solver takes the sense of sliding from ``sign(Σ W·sin α)``
    (see :meth:`BishopSimplified.compute_fos`) and carries it into
    ``m_alpha = cos α + slide_sign·sin α·tan φ / F``; these checks dropped
    the factor, which flips the branch whenever the mass slides towards
    decreasing x.

    On the reference critical circle — Ej_1, centre (88, 70.5), R = 47.212,
    ``slide_sign = −1`` — that turned min m_alpha = +0.928 into −0.010 and
    "rejected" five perfectly ordinary slices. It is the anomaly recorded
    in AGENTS.md: the criterion was never wrong, it was being read in the
    mirror.
    """
    slices = getattr(result, "slices", None)
    if not slices:
        return 1.0
    driving = sum(s.weight * math.sin(s.base_angle) for s in slices)
    return 1.0 if driving >= 0 else -1.0


def base_effective_stresses(result) -> list[float]:
    """Effective normal stress on each slice base at the converged FoS.

    Uses the classical limit-equilibrium expression for the base normal
    force,

        N = [ W - (c·l·sin(alpha) - u·l·tan(phi)·sin(alpha)) / F ] / m_alpha
        sigma'_n = N / l - u

    which is the quantity the reference tests for tension. Returns an
    empty list when the result carries no usable slices.
    """
    from .methods.bishop import BishopSimplified

    if result is None or not getattr(result, "slices", None):
        return []
    F = getattr(result, "fos", math.nan)
    if not (math.isfinite(F) and F > 0):
        return []

    out: list[float] = []
    sgn = _slide_sign(result)
    for s in result.slices:
        alpha = s.base_angle
        l = max(s.base_length, 1e-12)
        u = s.pore_pressure
        # v0.1.67 — the base has to carry the ponded water standing on the
        # slice as well as the soil. Leaving it out made this check judge
        # a reservoir-loaded slope with about a third of the real normal
        # force, which is the difference between "in tension" and not.
        W = s.weight + getattr(s, "water_weight", 0.0)
        sigma_est = max(0.0, W * math.cos(alpha) - u * l) / l
        c_loc, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                       sigma_est)
        m_alpha = math.cos(alpha) + sgn * math.sin(alpha) * tan_phi / F
        if abs(m_alpha) < 1e-9:
            out.append(float("-inf"))     # degenerate: treat as failing
            continue
        N = (W - sgn * (c_loc * l * math.sin(alpha)
                        - u * l * tan_phi * math.sin(alpha)) / F) / m_alpha
        out.append(N / l - u)
    return out


def base_m_alphas(result) -> list[float]:
    """``m_alpha`` on every slice at the converged FoS."""
    from .methods.bishop import BishopSimplified

    if result is None or not getattr(result, "slices", None):
        return []
    F = getattr(result, "fos", math.nan)
    if not (math.isfinite(F) and F > 0):
        return []
    out: list[float] = []
    sgn = _slide_sign(result)
    for s in result.slices:
        alpha = s.base_angle
        l = max(s.base_length, 1e-12)
        u = s.pore_pressure
        sigma_est = max(0.0, s.weight * math.cos(alpha) - u * l) / l
        _c, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                    sigma_est)
        out.append(math.cos(alpha) + sgn * math.sin(alpha) * tan_phi / F)
    return out


# ----------------------------------------------------------------------
def _toe_ordered_slices(result):
    """Slice indices ordered from the TOE of the surface inwards.

    The toe is the down-slope end, i.e. the end whose ground surface is
    lower. The reference measures its "percentage of slices" from there.
    """
    slices = list(result.slices)
    n = len(slices)
    if n == 0:
        return []
    y_left = slices[0].top_y_left
    y_right = slices[-1].top_y_right
    order = list(range(n))
    if y_left < y_right:
        return order           # toe at the left end
    return order[::-1]         # toe at the right end


def tensile_stress_check(result, percent_of_slices: float = 95.0):
    """Reference-style Tensile Stress Check.

    Returns ``(passed, offending_indices)``. ``passed`` is False when any
    tested slice carries an effective normal stress more tensile than its
    material allows.
    """
    stresses = base_effective_stresses(result)
    if not stresses:
        return True, []
    order = _toe_ordered_slices(result)
    n_test = int(round(len(order) * max(0.0, min(100.0, percent_of_slices))
                       / 100.0))
    tested = order[:max(0, n_test)]
    slices = list(result.slices)
    bad: list[int] = []
    for i in tested:
        allowed = _material_tensile_strength(slices[i].material)
        if stresses[i] < -allowed - 1e-9:
            bad.append(i)
    return (not bad), bad


def m_alpha_check(result, limit: float = M_ALPHA_LIMIT):
    """Reference-style m-alpha check (Whitman & Bailey, 1967).

    Returns ``(passed, offending_indices)``.
    """
    vals = base_m_alphas(result)
    if not vals:
        return True, []
    bad = [i for i, v in enumerate(vals) if v < limit]
    return (not bad), bad


# ----------------------------------------------------------------------
def check_surface(result, tensile: bool = False,
                  tensile_percent: float = 95.0,
                  m_alpha: bool = False,
                  m_alpha_limit: float = M_ALPHA_LIMIT):
    """Run the enabled post-analysis checks on a converged result.

    Returns ``(passed, reason)`` where ``reason`` is None when the
    surface passes, or a short explanation suitable for reporting.
    """
    if result is None or not getattr(result, "is_valid", False):
        return True, None
    if tensile:
        ok, bad = tensile_stress_check(result, tensile_percent)
        if not ok:
            return False, (
                f"tensile stress on {len(bad)} slice base(s) "
                f"(error -120)")
    if m_alpha:
        ok, bad = m_alpha_check(result, m_alpha_limit)
        if not ok:
            return False, (
                f"m_alpha < {m_alpha_limit} on {len(bad)} slice(s)")
    return True, None
