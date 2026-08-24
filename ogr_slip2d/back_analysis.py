# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Back Analysis of Support Force.

Determines the critical slip surface that requires the **maximum support
force** to reach a specified factor of safety — the natural starting
point for designing a support system.

How it works (following the reference specification):

* Rather than iterating to find the factor of safety, the factor of
  safety is **set to the user's target** and the force required to
  achieve it is solved for. Because the factor is fixed, the resisting
  sum can be evaluated directly and the force comes out in closed form —
  no iteration at all.
* The force is assumed **horizontal**, applied at a user-specified
  **elevation**.
* The elevation only affects **Bishop**, because that method works from
  moment equilibrium and the elevation sets the moment arm. It has no
  effect on **Janbu**, which considers only force equilibrium: a
  horizontal force enters the horizontal balance identically wherever it
  acts.
* Only **Bishop, Janbu and Janbu Corrected** are supported; the method is
  not defined for the others.
* Every surface is evaluated and the one needing the **largest** force is
  reported.
* The force is computed under **both** the active and the passive
  assumption, and both are always reported.

The calculation is completely independent of the main stability
analysis: it neither uses nor alters its results.

Active vs passive
-----------------
An **active** force is treated as reducing the driving action (it is
applied to the sliding mass before failure, like a prestressed anchor),
whereas a **passive** force adds to the resistance (it mobilises only as
the mass moves, like an untensioned nail):

    active:   F = R / (D - T)   ->   T = D - R / F
    passive:  F = (R + T) / D   ->   T = F * D - R

with ``R`` the resisting sum evaluated at the target factor and ``D`` the
driving sum. The passive value is the larger of the two, so it is the
conservative one for design.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

SUPPORTED_METHODS = ("bishop_simplified", "janbu_simplified",
                     "janbu_corrected")


@dataclass
class BackAnalysisSurfaceResult:
    """Required support force for one slip surface."""

    surface: Optional[dict] = None
    active_force: float = math.nan
    passive_force: float = math.nan
    target_fos: float = 1.3
    # Converged factor of safety WITHOUT support, filled in by the
    # driver from the real evaluation (see required_force).
    unsupported_fos: float = math.nan
    notes: dict = field(default_factory=dict)

    @property
    def governing_force(self) -> float:
        """The larger (conservative) of the two assumptions."""
        vals = [v for v in (self.active_force, self.passive_force)
                if math.isfinite(v)]
        return max(vals) if vals else math.nan


@dataclass
class BackAnalysisResult:
    """Outcome for one analysis method."""

    method_id: str = ""
    target_fos: float = 1.3
    elevation: float = 0.0
    critical: Optional[BackAnalysisSurfaceResult] = None
    surfaces_analysed: int = 0
    notes: dict = field(default_factory=dict)

    @property
    def required_force(self) -> float:
        return (self.critical.governing_force if self.critical
                else math.nan)

    def summary(self) -> dict:
        c = self.critical
        return {
            "method": self.method_id,
            "target_fos": self.target_fos,
            "elevation": self.elevation,
            "surfaces": self.surfaces_analysed,
            "active_force": c.active_force if c else math.nan,
            "passive_force": c.passive_force if c else math.nan,
            "required_force": self.required_force,
            "unsupported_fos": c.unsupported_fos if c else math.nan,
        }


# ======================================================================
def _sums_at_fixed_fos(slices, surface, target_fos, kh, kv, elevation,
                       method_id):
    """Resisting and driving sums evaluated at a FIXED factor of safety.

    Returns ``(resisting, driving, arm)`` where ``arm`` converts a
    horizontal force into the same units as the driving term (a moment
    arm divided by the radius for Bishop, 1 for Janbu).
    """
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.surface import SlipCircle

    s_list = list(slices)
    if not s_list:
        return None

    driving_raw = sum(s.weight * (1.0 - kv) * math.sin(s.base_angle)
                      for s in s_list)
    slide_sign = 1.0 if driving_raw >= 0 else -1.0

    is_bishop = (method_id == "bishop_simplified")
    circle = surface if isinstance(surface, SlipCircle) else None
    if is_bishop and circle is None:
        return None

    resisting = 0.0
    driving = 0.0
    for s in s_list:
        W_eff = s.weight * (1.0 - kv)
        b = s.width
        alpha = s.base_angle
        N_est = W_eff * math.cos(alpha)
        N_eff_est = max(0.0, N_est - s.pore_pressure * s.base_length)
        sigma = N_eff_est / max(s.base_length, 1e-9)
        c_loc, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                       sigma)
        m_alpha = math.cos(alpha) + (
            slide_sign * math.sin(alpha) * tan_phi / target_fos)
        if abs(m_alpha) < 1e-6:
            return None
        term = (c_loc * b + (W_eff - s.pore_pressure * b) * tan_phi) \
            / m_alpha

        if is_bishop:
            resisting += term
            driving += slide_sign * W_eff * math.sin(alpha)
            if kh:
                y_g = 0.5 * (s.base_y_mid + s.top_y_mid) \
                    if hasattr(s, "top_y_mid") else s.base_y_mid
                driving += kh * W_eff * (y_g - circle.centre_y) \
                    / max(circle.radius, 1e-9)
        else:
            # Janbu: horizontal force equilibrium
            resisting += term * math.cos(alpha)
            driving += slide_sign * W_eff * math.tan(alpha) + kh * W_eff

    if is_bishop:
        # Moment of a horizontal force about the centre is T·(y_c − y_T);
        # dividing by R keeps it commensurate with Σ W sin α.
        arm = (circle.centre_y - elevation) / max(circle.radius, 1e-9)
    else:
        # Force equilibrium: a horizontal force enters directly, and its
        # elevation is irrelevant — exactly as the reference states.
        arm = 1.0
    return resisting, driving, arm


def required_force(slices, surface, target_fos, method_id="bishop_simplified",
                   elevation=0.0, kh=0.0, kv=0.0
                   ) -> Optional[BackAnalysisSurfaceResult]:
    """Support force needed to bring ONE surface to ``target_fos``.

    Returns None when the surface cannot be evaluated, or when the
    geometry makes the force indeterminate (a Bishop force applied
    exactly at the centre elevation has no moment arm).
    """
    if method_id not in SUPPORTED_METHODS:
        return None
    if not (math.isfinite(target_fos) and target_fos > 0):
        return None
    sums = _sums_at_fixed_fos(slices, surface, target_fos, kh, kv,
                              elevation, method_id)
    if sums is None:
        return None
    resisting, driving, arm = sums
    if abs(arm) < 1e-9:
        return None

    res = BackAnalysisSurfaceResult(
        surface=(surface.to_dict() if hasattr(surface, "to_dict")
                 else None),
        target_fos=target_fos)
    # NOTE: the unsupported factor of safety is deliberately NOT derived
    # here. The resisting sum is evaluated at the TARGET factor (that is
    # the whole point of the method), so R/D would be one fixed-point
    # step away from the target rather than the converged answer — a
    # misleading number. ``run_back_analysis`` fills the field from the
    # search's own converged evaluation instead.

    # active:  F = R / (D - T·arm)   ->  T = (D - R/F) / arm
    res.active_force = (driving - resisting / target_fos) / arm
    # passive: F = (R + T·arm) / D   ->  T = (F·D - R) / arm
    res.passive_force = (target_fos * driving - resisting) / arm

    # A negative value means the surface already exceeds the target and
    # needs no support; report zero rather than a meaningless negative.
    if res.active_force < 0:
        res.active_force = 0.0
    if res.passive_force < 0:
        res.passive_force = 0.0
    return res


# ======================================================================
def run_back_analysis(project, search, target_fos=1.3, elevation=0.0,
                      method_id="bishop_simplified", num_slices=25,
                      progress_cb=None) -> BackAnalysisResult:
    """Back-analyse every surface of a search and report the one needing
    the largest support force.

    ``search`` is a configured search object; its surfaces are
    regenerated and each is back-analysed. The main stability results are
    neither used nor modified.
    """
    out = BackAnalysisResult(method_id=method_id, target_fos=target_fos,
                             elevation=elevation)
    if method_id not in SUPPORTED_METHODS:
        out.notes["error"] = (
            f"Back analysis is only available for "
            f"{', '.join(SUPPORTED_METHODS)}.")
        return out
    if not (math.isfinite(target_fos) and target_fos > 0):
        out.notes["error"] = "The target factor of safety must be positive."
        return out

    from .surface import CompositeSurface

    kh = project.seismic.kh if project.seismic.enabled else 0.0
    kv = project.seismic.kv if project.seismic.enabled else 0.0

    try:
        run = search.run(project)
    except Exception as exc:  # noqa: BLE001
        out.notes["error"] = f"search failed: {exc}"
        return out

    best = None
    total = len(run.evaluations)
    # v0.1.111 — composite surfaces are COUNTED and reported, not passed
    # over. ``required_force`` writes Bishop in its circular form, which
    # assumes every base normal points at the centre and every moment arm
    # is R; on the straight stretch of a composite neither holds, so it
    # answers None rather than a plausible wrong number. That is the right
    # refusal, but a silent one would be worse than the defect this version
    # fixes: with Composite Surfaces enabled the back-analysis would report
    # a governing force drawn from a population it never says it shrank.
    n_composite = 0
    for i, ev in enumerate(run.evaluations):
        if not ev.is_valid or not ev.slices:
            continue
        if isinstance(ev.surface, CompositeSurface):
            n_composite += 1
            continue
        r = required_force(ev.slices, ev.surface, target_fos, method_id,
                           elevation, kh, kv)
        out.surfaces_analysed += 1
        if r is None:
            continue
        # The converged, unsupported factor comes from the evaluation
        # itself — the only place it is actually known.
        r.unsupported_fos = ev.fos
        if best is None or r.governing_force > best.governing_force:
            best = r
        if progress_cb and i % 20 == 0:
            progress_cb(i, total)

    out.critical = best
    if n_composite:
        out.notes["composite_skipped"] = (
            f"{n_composite} composite surface(s) were left out: back "
            f"analysis is written in the circular form of the method, which "
            f"does not hold on the straight stretches of a composite. Turn "
            f"Composite Surfaces off to back-analyse this model, and read "
            f"the result as being about circular surfaces only.")
    if best is None:
        out.notes["error"] = (
            "No surface could be back-analysed. Check the target factor "
            "of safety and the search settings.")
    if progress_cb:
        progress_cb(total, total)
    return out
