# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Critical (yield) seismic coefficient of a slip surface.

``Ky`` is the horizontal pseudo-static coefficient that lowers the factor
of safety of one surface to a target — 1.0 unless the user asks for
something else. It is how the seismic capacity of a slope is stated
without committing to an earthquake ("this slope holds 0.14 g"), and it
is the **critical acceleration** a Newmark analysis integrates against.

Jibson (1993) lists two ways of obtaining it and puts this one first:
iterating a static limit-equilibrium analysis over horizontal
accelerations until the factor of safety reaches 1.0. The other,
``a_c = (FS − 1)·g·sin α`` with α the thrust angle, is Newmark's
simplification; it is not what this module computes, and it is not
equivalent — it replaces the whole equilibrium by one angle.

Two things this module does NOT do, and both are decisions:

* it does not touch the vertical coefficient. Newmark analysis is
  horizontal, and ``kv`` stays at whatever the project says, so a project
  with a vertical component gets its Ky *with* that component present
  rather than a different problem silently solved;
* it does not modify the project. The trial coefficient goes into a
  shallow copy, the same way a drawdown stage or a set of partial factors
  does — the user's model may not move because something was analysed.

The slices are computed ONCE and reused for every trial. That is not an
optimisation with a caveat: the slicer does not read the seismic
coefficient at all (the seismic force is formed inside each method from
the slice weights), so the same slices are the right slices for every
value of ``kh``.

Reference: Jibson, R.W. (1993). Predicting earthquake-induced landslide
displacements using Newmark sliding block analysis. Transportation
Research Record 1411, 9-17.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
from typing import Callable, Optional

__all__ = [
    "YieldAccelerationResult",
    "critical_coefficient_from",
    "critical_seismic_coefficient",
    "DEFAULT_K_STEP",
    "DEFAULT_K_MAX",
]

# Width of the ascending scan. It sets the resolution at which "the FIRST
# crossing" is resolved, which matters only if FS(k) is not monotonically
# decreasing — and on every case in the validation bank it is.
DEFAULT_K_STEP = 0.05
# Above this the search gives up and says so. A slope that still stands at
# k = 1 is not one a horizontal pseudo-static analysis has anything left
# to say about, and walking further costs a full solve per step.
DEFAULT_K_MAX = 1.0
# How close in k the bracket has to get. One part in a hundred thousand is
# three orders finer than the three decimals a Ky is ever quoted to, and
# with the Illinois refinement below it costs nothing to ask for.
_K_TOL = 1e-5
# ...and how close the FACTOR has to get, which is the condition actually
# being solved. Whichever arrives first ends the refinement.
_FOS_TOL = 1e-7
_MAX_EVALUATIONS = 40


class YieldAccelerationResult:
    """What one Ky solve produced.

    ``ky`` is NaN when no crossing was found; ``note`` then says why. A
    surface with no answer must not come back as a number, because a
    plausible number is exactly what gets averaged into a report.
    """

    __slots__ = ("ky", "fos_initial", "fos_at_ky", "evaluations", "note")

    def __init__(self, ky: float, fos_initial: float, fos_at_ky: float,
                 evaluations: int, note: str = "") -> None:
        self.ky = ky
        self.fos_initial = fos_initial
        self.fos_at_ky = fos_at_ky
        self.evaluations = evaluations
        self.note = note

    @property
    def found(self) -> bool:
        return math.isfinite(self.ky)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"YieldAccelerationResult(ky={self.ky:.6g}, "
                f"fos0={self.fos_initial:.6g}, evals={self.evaluations})")


# ----------------------------------------------------------------------
def critical_coefficient_from(
    fos_at: Callable[[float], float],
    *,
    target_fos: float = 1.0,
    fos_initial: Optional[float] = None,
    k_step: float = DEFAULT_K_STEP,
    k_max: float = DEFAULT_K_MAX,
) -> YieldAccelerationResult:
    """Solve ``FS(kh) = target_fos`` for the SMALLEST non-negative ``kh``.

    ``fos_at`` returns the factor of safety for a horizontal coefficient,
    or a non-finite value when that coefficient cannot be solved.
    ``fos_initial`` is ``FS(0)`` when the caller already has it — every
    caller inside a search does, and reusing it is one solve saved per
    surface.

    Three outcomes, and they are different answers rather than degrees of
    the same one:

    * ``FS(0) <= target`` — the surface is already at or past the target
      with no earthquake at all, so ``Ky = 0``. This is what the reference
      documents, and it is not a failure;
    * a crossing is found — ``ky`` is it, and ``fos_at_ky`` is the factor
      the solver actually gets there, which is the reference's own
      verification of the number;
    * no crossing below ``k_max`` — ``ky`` is NaN with a note.

    The scan walks UPWARD from zero and stops at the first coefficient
    that reaches the target, so the answer is the first crossing at the
    resolution of ``k_step``. A secant prediction is used to skip ahead,
    limited to twice ``k_step`` per move so that the walk stays a walk;
    without the limit a single jump could step over a crossing and the
    word "critical" would stop being true.
    """
    evals = 0

    def f(k: float) -> float:
        nonlocal evals
        evals += 1
        try:
            return float(fos_at(k))
        except Exception:
            return math.nan

    f0 = fos_initial if fos_initial is not None else f(0.0)
    if not math.isfinite(f0):
        return YieldAccelerationResult(math.nan, f0, math.nan, evals,
                                       "the surface has no factor of safety")
    if f0 <= target_fos:
        # Already at the target without any earthquake. The reference
        # reports zero here rather than a negative coefficient, and so
        # does this: a negative kh is a force up the slope, which is a
        # different question from the one being asked.
        return YieldAccelerationResult(0.0, f0, f0, evals, "")

    step = max(k_step, _K_TOL)
    lo, f_lo = 0.0, f0
    hi = math.nan
    f_hi = math.nan
    k = step
    while k <= k_max + 1e-12 and evals < _MAX_EVALUATIONS:
        fk = f(k)
        if not math.isfinite(fk):
            # A coefficient this surface cannot be solved at. Treat the
            # gap as unexplored and keep walking rather than declaring a
            # crossing that was never seen.
            lo, f_lo = k, math.nan
            k += step
            continue
        if fk <= target_fos:
            hi, f_hi = k, fk
            break
        # Still above the target. Predict where it would cross if it went
        # on falling at the rate just measured, and skip ahead — but by
        # no more than two steps, so a crossing cannot be jumped over.
        nxt = k + step
        if math.isfinite(f_lo) and f_lo > fk:
            slope = (f_lo - fk) / (k - lo)
            if slope > 0.0:
                pred = k + (fk - target_fos) / slope
                if pred > nxt:
                    nxt = min(pred, k + 2.0 * step)
        lo, f_lo = k, fk
        k = nxt

    if not math.isfinite(hi):
        return YieldAccelerationResult(
            math.nan, f0, math.nan, evals,
            f"no coefficient below {k_max:g} brings the factor to "
            f"{target_fos:g}")

    if not math.isfinite(f_lo):
        # The lower end of the bracket was a coefficient that could not be
        # solved, so the interval is not one the factor is known across.
        lo = max(0.0, hi - step)
        f_lo = f0

    # Refinement inside the bracket, by the Illinois variant of regula
    # falsi. Bracket-preserving like bisection — the answer cannot leave
    # the interval the scan established — but it converges on a nearly
    # linear FS(k) in about a third of the evaluations, and this runs once
    # per surface over thousands of surfaces. Plain bisection to 1e-4 in k
    # cost ten solves where this costs three or four.
    #
    # The stopping test is on the FACTOR, not only on k: what is being
    # solved is "the factor reaches the target", and a bracket narrow in k
    # says nothing about that on a surface where FS moves quickly.
    side = 0
    while (abs(f_hi - target_fos) > _FOS_TOL
           and (hi - lo) > _K_TOL and evals < _MAX_EVALUATIONS):
        if not math.isfinite(f_lo) or not math.isfinite(f_hi) or f_lo == f_hi:
            mid = 0.5 * (lo + hi)
        else:
            mid = lo + (hi - lo) * (f_lo - target_fos) / (f_lo - f_hi)
            if not (lo < mid < hi):
                mid = 0.5 * (lo + hi)
        fm = f(mid)
        if not math.isfinite(fm):
            break
        if fm <= target_fos:
            hi, f_hi = mid, fm
            if side < 0 and math.isfinite(f_lo):
                f_lo = target_fos + 0.5 * (f_lo - target_fos)
            side = -1
        else:
            lo, f_lo = mid, fm
            if side > 0 and math.isfinite(f_hi):
                f_hi = target_fos + 0.5 * (f_hi - target_fos)
            side = 1
        if abs(fm - target_fos) <= _FOS_TOL:
            break

    return YieldAccelerationResult(hi, f0, f_hi, evals, "")


# ----------------------------------------------------------------------
def critical_seismic_coefficient(
    method, project, surface, slices, *,
    target_fos: float = 1.0,
    fos_initial: Optional[float] = None,
    k_step: float = DEFAULT_K_STEP,
    k_max: float = DEFAULT_K_MAX,
) -> YieldAccelerationResult:
    """``Ky`` of one surface, solved with one limit-equilibrium method.

    The trial coefficient is applied to a **shallow copy** of the project
    carrying its own :class:`SeismicLoad`; the caller's project is not
    touched. The slices are the caller's and are reused unchanged — see
    the module docstring for why that is exact rather than convenient.
    """
    from ogr_core.loads.loads import SeismicLoad

    base = project.seismic
    trial_project = copy.copy(project)

    def fos_at(kh: float) -> float:
        trial_project.seismic = SeismicLoad(
            kh=kh, kv=base.kv if base.enabled else 0.0, enabled=True,
            creates_excess_pore_pressure=base.creates_excess_pore_pressure)
        res = method.compute_fos(trial_project, surface, slices)
        if res is None or not res.is_valid:
            return math.nan
        return res.fos

    return critical_coefficient_from(
        fos_at, target_fos=target_fos, fos_initial=fos_initial,
        k_step=k_step, k_max=k_max)
