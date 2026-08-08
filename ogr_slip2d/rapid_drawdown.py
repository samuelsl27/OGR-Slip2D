# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Multi-stage rapid drawdown: Lowe-Karafiath, Duncan-Wright-Wong and the
Corps of Engineers two-stage procedure.

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

    Stage 3   Only Duncan-Wright-Wong. If the DRAINED strength at the
              post-drawdown effective stress is smaller than the undrained
              one, the drained value is used instead and the analysis is
              rerun. An undrained strength above the drained one can only
              be sustained by negative pore pressures, which cavitation or
              partial drainage may not allow.

Because stage 3 can only ever lower a strength, ``FS_DWW ≤ FS_LK`` holds
for every model by construction — which is why the two share one function
and a flag here instead of being two parallel implementations. A property
test pins it.

Sign and level conventions
--------------------------
The **water table is the INITIAL (full reservoir) level and the drawdown
line is the FINAL, lower one**, following the reference and the published
cases (Pilarcitos: initial y = 72 ft, drawdown y = 37 ft). Note that the
B-bar model in ``ogr_core.hydraulic.pore_pressure`` uses the OPPOSITE
convention — it requires the drawdown line to sit ABOVE the water table —
and that conflict is real, pre-existing and reported rather than silently
resolved here; changing it would move the factor of safety of every saved
project that uses B-bar.

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

from ogr_core.geometry import BoundaryType
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
def _level_project(project, use_drawdown: bool):
    """A copy of the project whose water table is one of the two levels.

    The user's project is never touched: the procedure needs to analyse
    the same geometry at two different reservoir levels, and both the pore
    pressures and the ponding load follow the water table.
    """
    p = copy.copy(project)
    p.boundaries = list(project.boundaries)
    if not use_drawdown:
        # Stage 1: the initial level. The drawdown line must not pond.
        p.boundaries = [b for b in p.boundaries
                        if b.btype != BoundaryType.DRAWDOWN]
        return p

    drawdown = next((b for b in project.boundaries
                     if b.btype == BoundaryType.DRAWDOWN), None)
    kept = [b for b in p.boundaries
            if b.btype not in (BoundaryType.WATER_TABLE,
                               BoundaryType.DRAWDOWN)]
    if drawdown is not None:
        moved = copy.copy(drawdown)
        moved.btype = BoundaryType.WATER_TABLE
        kept.append(moved)
    # No drawdown line at all means TOTAL drawdown: no water left, which
    # is the reference's convention for an undefined final level.
    p.boundaries = kept
    return p


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
    Duncan-Wright-Wong run the same code with ``stage3`` on or off, which
    is what makes ``FS_DWW ≤ FS_LK`` structural rather than hopeful.
    """
    from .slicer import slice_surface

    if procedure not in MULTISTAGE_METHODS:
        raise RapidDrawdownError(f"Unknown drawdown procedure: {procedure}")
    stage3 = (procedure == DWW)
    corps = (procedure == CORPS_2)

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
            # Corps 1970: the composite envelope, evaluated at the
            # effective stress from BEFORE the drawdown. Using the one
            # after is precisely the refinement Duncan-Wright-Wong add.
            tau_ff = composite_strength(
                sigma_fc, _r_of(mat, phi_eff), c_eff, phi_eff)
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
    if not stage3 or not tau_by_index:
        return res

    # ---- Stage 3: drained check (Duncan-Wright-Wong only) ------------
    normals2 = list(getattr(r2, "base_normal", ()) or ())
    switched: dict = {}
    for i, tau_ff in tau_by_index.items():
        if i >= len(normals2):
            continue
        s = sl2u.slices[i]
        l = max(s.base_length, 1e-9)
        sigma_d = max(0.0, normals2[i]) / l                  # (9)
        c_eff, phi_eff = _effective_c_phi(sl2.slices[i].material)
        tau_drained = c_eff + sigma_d * math.tan(math.radians(phi_eff))
        if tau_drained < tau_ff:                             # (10)
            switched[i] = tau_drained
    if not switched:
        res.fos_stage3 = r2.fos
        return res

    merged = dict(tau_by_index)
    merged.update(switched)
    r3 = method.compute_fos(p2, surface, _undrained_slices(sl2, merged))
    res.fos_stage3 = r3.fos if math.isfinite(r3.fos) else r2.fos
    res.n_stage3_switched = len(switched)
    # The procedure takes the LOWER of the two, which is what makes
    # FS_DWW <= FS_LoweKarafiath hold for any model.
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
            },
        )


def wrap_for_drawdown(method, project, num_slices: int = 25):
    """Wrap ``method`` when the project asks for a multi-stage drawdown.

    Returns the method unchanged otherwise, so this can be applied
    unconditionally at the one place where methods are instantiated —
    which is the point: a second place that forgot to apply it would give
    a silently different answer.
    """
    gw = project.settings.groundwater
    if not gw.rapid_drawdown:
        return method
    if gw.rapid_drawdown_method not in MULTISTAGE_METHODS:
        return method        # B-bar works through the pore-pressure model
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
    if gw.rapid_drawdown_method not in MULTISTAGE_METHODS:
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
    return None
