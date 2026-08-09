# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Rapid drawdown: Lowe-Karafiath, Duncan-Wright-Wong, the Corps of
Engineers two-stage procedure, and the effective-stress B-bar model.

When a reservoir is emptied faster than the embankment can drain, a
low-permeability zone keeps the pore pressures of the full-reservoir state
while losing the stabilising weight of the water. The three procedures
here all answer the same question — what shear strength does that soil
actually have afterwards — and differ only in how they get it.

    Stage 1   Full reservoir, EFFECTIVE stresses. Gives, per slice, the
              consolidation state the soil reached:
                  σ'_fc = N' / Δl                                    (2)
                  τ_fc  = (c' + σ'_fc·tan φ') / FS₁                  (3)
              τ_fc is the MOBILISED shear, not the strength: it follows
              from the definition of the factor of safety, τ = s / FS.

    Stage 2   Drawn-down level. Each undrained slice gets an undrained
              strength interpolated between the two physical extremes,
              and is analysed in total stresses (c = τ_ff, φ = 0, u = 0).

    Stage 3   The drained cap. If the DRAINED strength at the
              post-drawdown effective stress is smaller than the undrained
              one, the drained value is used instead and the analysis is
              rerun. An undrained strength above the drained one can only
              be sustained by negative pore pressures, which cavitation or
              partial drainage may not allow. Duncan-Wright-Wong call this
              their third stage; for the Corps it is the other half of
              the composite envelope (v0.1.69). Lowe-Karafiath skip it.
              Since v0.1.70 it is iterated to a fixed point rather than
              applied once, because the cap and the stresses it is read
              at depend on each other — see ``CAP_RELAXATION``.

So what actually separates the three is one thing each:

    Lowe-Karafiath ....... K_c = 1 envelope interpolated by K_c, no cap
    Duncan-Wright-Wong ... the same, capped
    Corps of Engineers ... the R envelope directly, capped the same way

Because the cap can only ever lower a strength, ``FS_DWW ≤ FS_LK`` holds
for every model by construction — which is why the two share one function
and a flag here instead of being two parallel implementations. A property
test pins it.

The fourth procedure, B-bar, is not multi-stage: it is a single
effective-stress analysis at the drawn-down level in which the undrained
materials carry the pore pressure of the initial state, less whatever
Skempton's coefficient lets them shed as the water load comes off:

    Δu = B̄ · Δσ_v,   Δσ_v = −γ_w·(h_ponded,initial − h_ponded,final)

Δσ_v is the weight of the PONDED COLUMN removed above the point, capped
by the ground surface — not the gap between the two water surfaces. The
difference is the whole slope face, where the ground stands between the
two levels, and that is exactly where the critical surface runs.

Sign and level conventions
--------------------------
The **water table is the INITIAL (full reservoir) level and the drawdown
line is the FINAL, lower one**, following the reference and the published
cases (Pilarcitos 72 → 37 ft, Morgenstern 100 → 50 ft, Appendix G
103 → 24 ft). Until v0.1.69 the B-bar model demanded the opposite and
three further defects cancelled against it, so that at B̄ = 1 the
"drawdown" factor of safety came out equal to the one from before the
drawdown. All four procedures now ask
``ogr_core.hydraulic.drawdown_levels`` which line is which.

References:
    Corps of Engineers (1970). *Stability of Earth and Rock Fill Dams*,
        EM 1110-2-1902.
    Corps of Engineers (2003). *Slope Stability*, EM 1110-2-1902,
        Appendix G: Procedures and Examples for Rapid Drawdown.
    Duncan, J. M., Wright, S. G. y Wong, K. S. (1990). "Slope Stability
        during Rapid Drawdown". H. Bolton Seed Memorial Symposium,
        vol. 2, pp. 253-272.
    Lowe, J. y Karafiath, L. (1960). "Stability of Earth Dams upon
        Drawdown". 1st PanAmerican Conf. on Soil Mechanics and Foundation
        Engineering, Mexico D.F., vol. 2, pp. 537-552.
    Morgenstern, N. (1963). "Stability charts for earth slopes during
        rapid drawdown". Géotechnique 13(2), pp. 121-131. The published
        case the B-bar model is validated against.
    Skempton, A. W. (1954). "The pore-pressure coefficients A and B".
        Géotechnique 4(4), pp. 143-147.
    Wright, S. G. y Duncan, J. M. (1987). *An Examination of Slope
        Stability Computation Procedures for Sudden Drawdown*. Misc.
        Paper GL-87-25, USACE WES.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Optional

from ogr_core.geometry import Vertex
from ogr_core.hydraulic.drawdown_levels import (
    drawdown_line_is_inverted,
    level_project,
)
from ogr_core.hydraulic.ponded_water import ponded_depth_at
from ogr_core.hydraulic.pore_pressure import pore_pressure_at
from ogr_core.materials import Material
from ogr_core.materials.drawdown_envelopes import (
    Kc1Envelope,
    REnvelope,
    composite_strength,
)

# The three procedures, as stored in ``GroundwaterSettings``.
DWW = "duncan_wright"
LOWE_KARAFIATH = "lowe_karafiath"
CORPS_2 = "corps_2"
B_BAR = "b_bar"

MULTISTAGE_METHODS = (DWW, LOWE_KARAFIATH, CORPS_2)

# v0.1.70 — the drained cap is a fixed point, not a single substitution.
# Capping a slice lowers the factor of safety, which moves the base
# normals, which moves the cap; applied once, the answer depends on where
# you happened to stop. Undamped the iteration oscillates, so it is
# under-relaxed. The measurement that licenses the whole thing is not the
# speed but that **the fixed point does not depend on the relaxation**,
# which is what makes the converged value a property of the model:
#
#     omega   Appendix G Corps    Appendix G DWW    Pilarcitos Corps
#     1.00    1.3493 (18 passes)  1.4455 (16)       0.8656 (40, unconverged)
#     0.70    1.3494  (9)         1.4456  (8)       0.8658  (6)
#     0.50    1.3495 (12)         1.4457 (11)       0.8658  (4)
#     0.35    1.3496 (16)         1.4458 (14)       0.8658  (5)
#
# v0.1.71 — that table is why the default was 0.70, and it was the wrong
# reading, because every column of it is the CRITICAL surface. Over the
# whole Pilarcitos grid (729 candidates, 185 valid) the picture inverts:
#
#     omega   DWW passes  stuck   Corps passes  stuck   critical FoS
#     0.70       515        8         613       12      1.0847 / 0.8383
#     0.50       365        0         381        0      1.0847 / 0.8383
#     0.35       453        0         441        1      1.0847 / 0.8383
#
# 0.50 wins on every axis — no surface left unconverged, the same
# critical factors of safety, and 29-38 % less work, because a surface
# that never converges burns the whole budget every time. Note it is NOT
# monotone: 0.35 puts one back. A fixed relaxation is therefore fragile
# by construction, which is why the loop also HALVES it whenever the
# factor of safety reverses direction between passes — a period-2 cycle
# is the failure mode, and halving is what breaks it.
CAP_RELAXATION = 0.50
CAP_RELAXATION_MIN = 0.05    # below this, damping is not the problem
CAP_TOL = 1e-4               # on the factor of safety, between passes
CAP_MAX_PASSES = 20


class RapidDrawdownError(RuntimeError):
    """A modelling error the user has to resolve, not a numerical hiccup."""


@dataclass
class DrawdownResult:
    """Outcome of a multi-stage run, with the intermediate stages kept.

    The stages are returned rather than discarded because the whole point
    of the procedure is that stage 1 conditions stage 2: a factor of
    safety that cannot be traced back to the consolidation state it came
    from is not auditable.
    """

    fos: float
    method: str
    fos_stage1: float
    fos_stage2: float
    fos_stage3: Optional[float] = None
    n_undrained_slices: int = 0
    n_stage3_switched: int = 0
    # v0.1.70 — how many passes the drained cap needed to settle.
    n_cap_passes: int = 0
    # v0.1.71 — and whether it actually settled. False means the factor
    # of safety above is the CENTRE of a cycle the cap never left, not a
    # converged value; ``cap_min_m_alpha`` then carries the diagnostic,
    # because the slice that cycles is always one with a small m-alpha.
    cap_converged: bool = True
    cap_min_m_alpha: Optional[float] = None
    note: str = ""


# ----------------------------------------------------------------------
def _effective_c_phi(material) -> tuple[float, float]:
    """Effective c' and φ' of a material, in kPa and degrees.

    Only a linear effective envelope makes sense here: the procedure
    overwrites c and φ per slice, so a curved envelope (power, Hoek-Brown)
    would be silently replaced by a straight line rather than honoured.
    Refused explicitly instead.
    """
    strength = getattr(material, "strength", None)
    params = getattr(strength, "params", None) or {}
    mid = getattr(strength, "MODEL_ID", "")
    if mid == "mohr_coulomb":
        return (float(params.get("cohesion", 0.0)),
                float(params.get("friction_angle", 0.0)))
    if mid == "undrained":
        return float(params.get("cohesion", 0.0)), 0.0
    raise RapidDrawdownError(
        f"Rapid drawdown needs a linear effective envelope; material "
        f"'{getattr(material, 'name', '?')}' uses '{mid}'. A curved "
        f"envelope cannot be carried through a procedure that rewrites "
        f"c and phi on every slice."
    )


def _kc1_of(material, phi_eff_deg: float) -> Kc1Envelope:
    env = getattr(material, "drawdown_envelope", None)
    if isinstance(env, Kc1Envelope):
        return env
    if isinstance(env, REnvelope):
        return env.to_kc1(phi_eff_deg)
    raise RapidDrawdownError(
        f"Material '{getattr(material, 'name', '?')}' is marked undrained "
        f"but has no R or Kc=1 envelope defined.")


def _r_of(material, phi_eff_deg: float) -> REnvelope:
    env = getattr(material, "drawdown_envelope", None)
    if isinstance(env, REnvelope):
        return env
    if isinstance(env, Kc1Envelope):
        return env.to_r(phi_eff_deg)
    raise RapidDrawdownError(
        f"Material '{getattr(material, 'name', '?')}' is marked undrained "
        f"but has no R or Kc=1 envelope defined.")


# ----------------------------------------------------------------------
def undrained_strength_dww(
    sigma_fc: float,
    tau_fc: float,
    c_eff: float,
    phi_eff_deg: float,
    kc1: Kc1Envelope,
) -> float:
    """Anisotropically-consolidated undrained strength τ_ff of a slice.

    Interpolates linearly in K_c between the two physical extremes,
    both evaluated at the SAME σ'_fc::

        τ_ff|Kc=1  = d + σ'_fc·tan ψ            (IC-U tests, lower bound)
        τ_ff|Kc=Kf = c' + σ'_fc·tan φ'          (drained, upper bound)

        τ_ff = [ (K_f − K_1)·τ_ff|Kc=1 + (K_1 − 1)·τ_ff|Kc=Kf ]
               / (K_f − 1)                                        (5)

    The upper bound is the DRAINED envelope because at K_c = K_f failure
    happens during consolidation itself, so σ'_ff = σ'_fc and τ_fc = τ_ff.

    K_1 is the slice's own consolidation stress ratio and K_f the one that
    would cause failure while consolidating::

        K_1 = [σ'_fc + τ_fc·(sin φ' + 1)/cos φ']
              / [σ'_fc + τ_fc·(sin φ' − 1)/cos φ']                 (4)
        K_f = [(σ'_fc + c'·cos φ')·(1 + sin φ')]
              / [(σ'_fc − c'·cos φ')·(1 − sin φ')]                 (6)

    Where the interpolation is ill-conditioned the fallback is the LOWER
    of the two bounds — never a silent zero, and never an extrapolation.
    """
    phi = math.radians(phi_eff_deg)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    tau_kc1 = kc1.strength_at(sigma_fc)
    tau_kf = c_eff + max(0.0, sigma_fc) * math.tan(phi)
    floor = min(tau_kc1, tau_kf)

    if abs(cos_p) < 1e-9:
        return max(0.0, floor)

    # (7) and (8): the minor principal stresses of the two states. Zero is
    # excluded as well as negatives — it is the denominator of K_1, and a
    # NaN swallowed by a later max(0, ...) would leave the slice with no
    # strength at all while looking like a legitimate answer.
    s3_1 = sigma_fc + tau_fc * (sin_p - 1.0) / cos_p
    if not (s3_1 > 1e-12):
        return max(0.0, floor)
    denom_kf = (sigma_fc - c_eff * cos_p) * (1.0 - sin_p)
    if abs(denom_kf) < 1e-12:
        return max(0.0, floor)

    s1_1 = sigma_fc + tau_fc * (sin_p + 1.0) / cos_p
    k_1 = s1_1 / s3_1
    k_f = ((sigma_fc + c_eff * cos_p) * (1.0 + sin_p)) / denom_kf

    if not (math.isfinite(k_1) and math.isfinite(k_f)):
        return max(0.0, floor)
    if abs(k_f - 1.0) < 1e-9:
        return max(0.0, tau_kc1)
    # Outside [1, K_f] the formula extrapolates instead of interpolating,
    # which is what produces decreasing and eventually negative strengths.
    k_1 = min(max(k_1, 1.0), k_f)

    tau_ff = ((k_f - k_1) * tau_kc1 + (k_1 - 1.0) * tau_kf) / (k_f - 1.0)
    if not math.isfinite(tau_ff):
        return max(0.0, floor)
    return max(0.0, tau_ff)


# ----------------------------------------------------------------------
# v0.1.69 — the level projection moved to ``ogr_core.hydraulic`` so the
# B-bar model, which lives on the other side of that boundary, asks the
# same function which line is which. Kept under the old private name
# because the call sites here read better for it.
_level_project = level_project


def _stage1_state(project, surface, slices, result):
    """(σ'_fc, τ_fc) sampled along the surface, from the stage-1 solution.

    Returned as a list of ``(x_left, x_right, σ'_fc, τ_fc)`` rather than
    indexed by slice, because the stage-2 slicing is NOT the same: since
    v0.1.66 the water table is a mandatory slice cut, and the two stages
    have different water tables by construction. Matching by slice index
    would quietly pair up slices from different places on the surface.
    """
    normals = list(getattr(result, "base_normal", ()) or ())
    fs1 = result.fos
    out = []
    for i, s in enumerate(slices.slices):
        if i >= len(normals):
            break
        l = max(s.base_length, 1e-9)
        n_eff = normals[i] - s.pore_pressure * l          # (2)
        sigma_fc = max(0.0, n_eff) / l
        mat = s.material
        try:
            c_eff, phi_eff = _effective_c_phi(mat)
        except RapidDrawdownError:
            c_eff, phi_eff = 0.0, 0.0
        tau_fc = (c_eff + sigma_fc * math.tan(math.radians(phi_eff))) / fs1
        out.append((s.base_x_left, s.base_x_right, sigma_fc, tau_fc))
    return out


def _sample_state(state, x: float):
    """The stage-1 consolidation state at abscissa ``x``."""
    if not state:
        return None
    for x0, x1, sigma, tau in state:
        if x0 <= x <= x1:
            return sigma, tau
    # Outside the stage-1 extent: the surface daylights differently at the
    # two levels. Take the nearest end rather than inventing a state.
    if x < state[0][0]:
        return state[0][2], state[0][3]
    return state[-1][2], state[-1][3]


def _undrained_slices(slices, tau_by_index: dict):
    """Copy of the slices with the undrained ones in total stresses.

    ``c = τ_ff``, ``φ = 0`` and ``u = 0``: the strength is a total-stress
    one, so feeding it a pore pressure as well would subtract the water
    twice.
    """
    from ogr_core.materials.builtin_models import Undrained

    out = copy.copy(slices)
    out.slices = []
    for i, s in enumerate(slices.slices):
        if i not in tau_by_index:
            out.slices.append(s)
            continue
        s2 = copy.copy(s)
        base = s.material
        s2.material = Material(
            name=f"{getattr(base, 'name', 'soil')} (stage 2)",
            strength=Undrained(cohesion=tau_by_index[i]),
            unit_weight=getattr(base, "unit_weight", 20.0),
            sat_unit_weight=getattr(base, "sat_unit_weight", 21.0),
            use_sat_unit_weight=getattr(base, "use_sat_unit_weight", False),
        )
        s2.pore_pressure = 0.0
        s2.raw_pore_pressure = 0.0
        s2.suction_cohesion = 0.0
        out.slices.append(s2)
    return out


# ----------------------------------------------------------------------
def rapid_drawdown_fos(
    project,
    surface,
    method,
    *,
    num_slices: int = 25,
    procedure: str = DWW,
) -> DrawdownResult:
    """Factor of safety after a rapid drawdown, by the chosen procedure.

    ``procedure`` is one of :data:`MULTISTAGE_METHODS`. Lowe-Karafiath and
    Duncan-Wright-Wong run the same code with ``drained_cap`` on or off,
    which is what makes ``FS_DWW ≤ FS_LK`` structural rather than hopeful.

    The Corps takes that cap too (v0.1.69 — see ``composite_strength``),
    so what actually separates the three is one thing each:

        Lowe-Karafiath ... K_c = 1 envelope interpolated by K_c, no cap
        Duncan-W-Wong .... the same, capped by the drained strength
        Corps of Eng. .... the R envelope directly, capped the same way
    """
    from .slicer import slice_surface

    if procedure not in MULTISTAGE_METHODS:
        raise RapidDrawdownError(f"Unknown drawdown procedure: {procedure}")
    corps = (procedure == CORPS_2)
    drained_cap = procedure in (DWW, CORPS_2)

    # ---- Stage 1: full reservoir, effective stresses -----------------
    p1 = _level_project(project, use_drawdown=False)
    sl1 = slice_surface(p1, surface, num_slices=num_slices)
    if sl1 is None:
        raise RapidDrawdownError(
            "The slip surface could not be sliced at the initial level")
    r1 = method.compute_fos(p1, surface, sl1)
    if not (math.isfinite(r1.fos) and r1.fos > 0.0):
        raise RapidDrawdownError(
            "Stage 1 did not produce a usable factor of safety")
    if r1.fos < 1.0:
        # The procedure assumes the slope was stable BEFORE the drawdown.
        # With FS1 < 1 the consolidation state sits above the failure
        # envelope, K_1 comes out greater than K_f and equation (5) stops
        # interpolating and starts extrapolating — giving strengths that
        # fall and eventually go negative. In an automatic search that
        # hands victory to surfaces with a fictitious FoS near zero.
        raise RapidDrawdownError(
            f"Stage 1 factor of safety is {r1.fos:.3f} < 1: the slope is "
            f"not stable with the reservoir full, and the rapid-drawdown "
            f"procedure does not apply to it")

    state = _stage1_state(project, surface, sl1, r1)

    # ---- Stage 2: drawn-down level, undrained strengths --------------
    p2 = _level_project(project, use_drawdown=True)
    sl2 = slice_surface(p2, surface, num_slices=num_slices)
    if sl2 is None:
        raise RapidDrawdownError(
            "The slip surface could not be sliced at the drawn-down level")

    tau_by_index: dict = {}
    for i, s in enumerate(sl2.slices):
        mat = s.material
        if not getattr(mat, "undrained_behaviour", False):
            continue          # freely draining: keeps c', phi' and its u
        sampled = _sample_state(state, s.x_centre)
        if sampled is None:
            continue
        sigma_fc, tau_fc = sampled
        c_eff, phi_eff = _effective_c_phi(mat)
        if corps:
            # Corps 1970: the R envelope read directly at the effective
            # consolidation stress. The other half of the composite — the
            # drained cap — is applied below, with the stresses that
            # exist after the drawdown.
            tau_ff = _r_of(mat, phi_eff).strength_at(sigma_fc)
        else:
            tau_ff = undrained_strength_dww(
                sigma_fc, tau_fc, c_eff, phi_eff,
                _kc1_of(mat, phi_eff))
        tau_by_index[i] = max(0.0, tau_ff)

    sl2u = _undrained_slices(sl2, tau_by_index)
    r2 = method.compute_fos(p2, surface, sl2u)
    if not math.isfinite(r2.fos):
        raise RapidDrawdownError("Stage 2 did not converge")

    res = DrawdownResult(
        fos=r2.fos, method=procedure, fos_stage1=r1.fos, fos_stage2=r2.fos,
        n_undrained_slices=len(tau_by_index),
    )
    if not drained_cap or not tau_by_index:
        return res

    # ---- The drained cap: DWW's third stage, and the other half of the
    #      Corps' composite envelope. Iterated to a fixed point, because
    #      capping a strength lowers the factor of safety, which moves the
    #      base normals, which moves the cap. See CAP_RELAXATION.
    cur = dict(tau_by_index)
    omega = CAP_RELAXATION      # local: a hard surface must not leak into
                                # the next one through a module constant
    prev_fos = r2.fos
    prev_delta = None
    last = r2
    recent: list[float] = []    # factors of safety of the CAPPED passes
    passes = 0
    converged = False
    for _ in range(CAP_MAX_PASSES):
        normals2 = list(getattr(last, "base_normal", ()) or ())
        nxt: dict = {}
        for i, tau_ff in tau_by_index.items():
            if i >= len(normals2):
                nxt[i] = cur[i]
                continue
            l = max(sl2.slices[i].base_length, 1e-9)
            sigma_d = max(0.0, normals2[i]) / l               # (9)
            c_eff, phi_eff = _effective_c_phi(sl2.slices[i].material)
            # The cap is always taken against the ORIGINAL undrained
            # strength, never against the already-capped value: feeding
            # the capped one back would let it ratchet down without a
            # floor instead of settling on min(undrained, drained).
            target = composite_strength(                      # (10)
                tau_ff, sigma_d, c_eff, phi_eff)
            nxt[i] = (1.0 - omega) * cur[i] + omega * target
        if all(abs(nxt[i] - cur[i]) < 1e-12 for i in nxt):
            # Nothing moved, so re-solving would return the same factor
            # of safety. On the first pass this is the surface where the
            # cap never bites at all, and it must cost no extra solve —
            # that was the whole of the pre-v0.1.70 fast path.
            converged = True
            break
        cur = nxt
        r3 = method.compute_fos(p2, surface, _undrained_slices(sl2, cur))
        if not math.isfinite(r3.fos):
            break
        last = r3
        recent.append(r3.fos)
        passes += 1
        delta = r3.fos - prev_fos
        if abs(delta) < CAP_TOL:
            converged = True
            break
        # v0.1.71 — a reversal is the signature of the period-2 cycle
        # that used to leave surfaces unconverged. Halving on each
        # reversal collapses it; a fixed relaxation only works until a
        # model crosses whatever threshold that particular value sits on.
        if prev_delta is not None and delta * prev_delta < 0.0:
            omega = max(CAP_RELAXATION_MIN, 0.5 * omega)
        prev_delta = delta
        prev_fos = r3.fos

    if converged or len(recent) < 2:
        res.fos_stage3 = recent[-1] if recent else r2.fos
    else:
        # v0.1.71 — NEVER the last iterate on its own. If the cap is
        # still cycling, the last iterate is one horn of the cycle and
        # the answer would depend on the parity of CAP_MAX_PASSES: the
        # same surface gave 1.2486 at 19 passes and 1.2547 at 20. The
        # midpoint is the cycle centre, and it does not care where the
        # budget ran out.
        res.fos_stage3 = 0.5 * (recent[-1] + recent[-2])
    res.n_cap_passes = passes
    res.cap_converged = converged
    if not converged:
        # Report WHY, with the diagnostic that identified the mechanism:
        # the cycling slice is always the steep one at the crest end,
        # where a small m-alpha amplifies dN/dF and closes the loop.
        # Measured on Pilarcitos, the split had no overlap — surfaces
        # that cycled had min m-alpha 0.45-0.72, ones that converged
        # 0.96-1.05. Only computed here, so the normal path pays nothing.
        from .checks import base_m_alphas

        vals = base_m_alphas(last)
        res.cap_min_m_alpha = min(vals) if vals else None
    res.n_stage3_switched = sum(
        1 for i, tau_ff in tau_by_index.items() if cur[i] < tau_ff - 1e-12)
    # Every iterate is a convex combination of the undrained strength and
    # something no larger than it, so cur[i] <= tau_by_index[i] always —
    # which is what keeps FS_DWW <= FS_LoweKarafiath structural.
    res.fos = min(res.fos_stage2, res.fos_stage3)
    return res


# ----------------------------------------------------------------------
class MultiStageDrawdownMethod:
    """A LEM method whose factor of safety is the post-drawdown one.

    The search evaluates surfaces through ``compute_fos``, so routing the
    multi-stage procedure through the same call is what makes choosing it
    in the interface actually change the number. Before this existed, the
    drawdown combo offered four entries and only B-bar computed anything.

    The slices the search hands over are ignored on purpose: the procedure
    needs the mass sliced at TWO different reservoir levels, and neither
    of them is the one the caller happened to build.
    """

    def __init__(self, inner, procedure: str, num_slices: int = 25) -> None:
        self.inner = inner
        self.procedure = procedure
        self.num_slices = num_slices

    @property
    def METHOD_ID(self) -> str:          # noqa: N802 (protocol name)
        return getattr(self.inner, "METHOD_ID", "unknown")

    @property
    def DISPLAY_NAME(self) -> str:       # noqa: N802 (protocol name)
        return getattr(self.inner, "DISPLAY_NAME", "?")

    def compute_fos(self, project, surface, slices):
        from .methods.base import LEMResult

        try:
            res = rapid_drawdown_fos(
                project, surface, self.inner,
                num_slices=self.num_slices, procedure=self.procedure)
        except RapidDrawdownError as exc:
            # A surface the procedure does not apply to is not a failure
            # of the run: in a search most candidates are like that. It
            # comes back invalid with the reason attached, so the Invalid
            # Surfaces report can group them.
            return LEMResult(
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message=str(exc),
            )
        return LEMResult(
            fos=res.fos, converged=True, iterations=3 if res.fos_stage3
            else 2,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            details={
                "drawdown_procedure": res.method,
                "fos_stage1": res.fos_stage1,
                "fos_stage2": res.fos_stage2,
                "fos_stage3": res.fos_stage3,
                "undrained_slices": res.n_undrained_slices,
                "stage3_switched": res.n_stage3_switched,
                # v0.1.70 — reported so a surface whose drained cap did
                # not settle is visible rather than silently taken at
                # wherever the iteration stopped.
                "cap_passes": res.n_cap_passes,
                "cap_converged": res.cap_converged,
                "cap_min_m_alpha": res.cap_min_m_alpha,
            },
        )


# ----------------------------------------------------------------------
def b_bar_pore_pressures(project, slices) -> int:
    """Overwrite the pore pressure of every undrained slice, in place.

    ``slices`` must have been built on the FINAL level — the copy that
    :func:`level_project` returns with ``use_drawdown=True`` — so that the
    ponding load, the saturated unit weights and the pore pressure of the
    freely draining materials are all the post-drawdown ones already.
    What is left is the excess the undrained materials keep::

        u = u_initial + B̄ · Δσ_v,   Δσ_v = −γ_w·(h_ini − h_fin)

    where ``h`` is the depth of ponded water standing on the ground
    ABOVE the slice, so a point under the slope face — where the ground
    lies between the two levels — sees only the column that was really
    resting on it. Returns how many slices were changed.

    Two details that are decisions, not accidents:

    * the gate is ``undrained_behaviour`` alone, not ``b_bar > 0``. With
      the coefficient as a second gate the model would be discontinuous
      at zero: B̄ = 0.001 keeps essentially the whole initial pore
      pressure while B̄ = 0 would drop to the final level, two very
      different answers either side of nothing. The checkbox says whether
      the soil can drain; B̄ says how much of the unloading its pore
      water follows.
    * the result is clamped at zero. Negative pore pressures here would
      be suction the drawdown created, and leaning on them is precisely
      what the Corps' composite envelope exists to avoid.
    """
    gamma_w = project.settings.groundwater.pore_fluid_unit_weight
    initial = level_project(project, use_drawdown=False)
    final = level_project(project, use_drawdown=True)
    n = 0
    for s in slices.slices:
        mat = s.material
        if mat is None or not getattr(mat, "undrained_behaviour", False):
            continue
        x = s.x_centre
        y_ground = s.top_y_mid
        u_ini = pore_pressure_at(
            initial, Vertex(x, s.base_y_mid), mat,
            ground_surface_y=y_ground)
        delta_sigma_v = -gamma_w * (ponded_depth_at(initial, x, y_ground)
                                    - ponded_depth_at(final, x, y_ground))
        u = max(0.0, u_ini + float(getattr(mat, "b_bar", 0.0))
                * delta_sigma_v)
        s.pore_pressure = u
        s.raw_pore_pressure = u
        # The unsaturated policy already ran on the final-level pressure;
        # this one is clamped non-negative, so there is no suction left
        # for it to turn into cohesion.
        s.suction_cohesion = 0.0
        n += 1
    return n


class BBarDrawdownMethod:
    """A LEM method whose pore pressures are the post-drawdown B-bar ones.

    Same shape as :class:`MultiStageDrawdownMethod`, and for the same
    reason: the search evaluates surfaces through ``compute_fos``, so the
    only way for the choice made in the interface to reach the number is
    to route it through that call. Until v0.1.69 B-bar instead patched
    the pore-pressure model from inside, where neither the ground surface
    nor the ponding load is visible.
    """

    def __init__(self, inner, num_slices: int = 25) -> None:
        self.inner = inner
        self.num_slices = num_slices

    @property
    def METHOD_ID(self) -> str:          # noqa: N802 (protocol name)
        return getattr(self.inner, "METHOD_ID", "unknown")

    @property
    def DISPLAY_NAME(self) -> str:       # noqa: N802 (protocol name)
        return getattr(self.inner, "DISPLAY_NAME", "?")

    def compute_fos(self, project, surface, slices):
        from .methods.base import LEMResult
        from .slicer import slice_surface

        p2 = level_project(project, use_drawdown=True)
        sl2 = slice_surface(p2, surface, num_slices=self.num_slices)
        if sl2 is None:
            return LEMResult(
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="The slip surface could not be sliced at "
                              "the drawn-down level",
            )
        n = b_bar_pore_pressures(project, sl2)
        res = self.inner.compute_fos(p2, surface, sl2)
        details = dict(getattr(res, "details", None) or {})
        details["drawdown_procedure"] = B_BAR
        details["undrained_slices"] = n
        res.details = details
        return res


# ----------------------------------------------------------------------
def wrap_for_drawdown(method, project, num_slices: int = 25):
    """Wrap ``method`` when the project asks for a rapid drawdown.

    Returns the method unchanged otherwise, so this can be applied
    unconditionally at the one place where methods are instantiated —
    which is the point: a second place that forgot to apply it would give
    a silently different answer.
    """
    gw = project.settings.groundwater
    if not gw.rapid_drawdown:
        return method
    if gw.rapid_drawdown_method == B_BAR:
        return BBarDrawdownMethod(method, num_slices=num_slices)
    if gw.rapid_drawdown_method not in MULTISTAGE_METHODS:
        return method
    return MultiStageDrawdownMethod(
        method, gw.rapid_drawdown_method, num_slices=num_slices)


def check_drawdown_settings(project) -> Optional[str]:
    """Why this project cannot run a rapid drawdown, or None if it can.

    The procedures define both reservoir levels with water surfaces, so
    they are incompatible with Ru, with a pressure grid and with a
    finite-element seepage field. Checked here rather than only in the
    dialog: a project can be built by the CLI or edited by hand, and an
    analysis that quietly ignores the groundwater method the user chose
    is worse than one that refuses.
    """
    gw = project.settings.groundwater
    if not gw.rapid_drawdown:
        return None
    if gw.rapid_drawdown_method not in MULTISTAGE_METHODS + (B_BAR,):
        return None
    allowed = ("water_table", "piezo_line")
    if gw.method not in allowed:
        return (
            f"Rapid drawdown defines both reservoir levels with water "
            f"surfaces, so it cannot run with groundwater method "
            f"'{gw.method}'. Choose Water Surfaces."
        )
    if not any(getattr(m, "undrained_behaviour", False)
               for m in project.materials):
        return (
            "No material is marked as having undrained behaviour, so the "
            "drawdown would not change any strength. Tick Undrained "
            "Behaviour on the low-permeability materials."
        )
    # v0.1.69 — until this version the B-bar model REQUIRED this, and the
    # multi-stage ones required the opposite. Now there is one convention
    # and a line drawn on the wrong side of it is a modelling error with
    # a message, not a silent nothing.
    if drawdown_line_is_inverted(project):
        return (
            "The Drawdown Line lies ABOVE the Water Table. The water "
            "table is the initial reservoir level and the drawdown line "
            "the final, lower one; swap them."
        )
    return None
