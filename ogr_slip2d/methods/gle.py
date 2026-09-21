# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
GLE / Morgenstern-Price Method of Slices.

Reference: Fredlund, D.G. & Krahn, J. (1977). "Comparison of slope
stability methods of analysis." Can. Geotech. J. 14(3), 429-439.

Generalises Spencer by allowing a non-constant inter-slice force
ratio:
        X_i / E_i = λ · f(x_i)

Common shape functions:
    f(x) = 1                 → reduces exactly to Spencer
    f(x) = sin(π·(x−x0)/L)   → Morgenstern-Price half-sine (default)
    trapezoidal              → ramp/flat/ramp
    user-defined             → arbitrary callable

Same outer-inner iteration structure as Spencer:
    outer secant on λ until F_f(λ) = F_m(λ)
    inner fixed-point on F at each λ.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Callable, Tuple

from ogr_core.project import Project

from ..external_forces import slice_forces
from ..slicer import Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import (
    REASON_ALL_LAMBDA_DIVERGED,
    REASON_DIVERGENT_AT_LAMBDA,
    REASON_LAMBDA_NOT_CLOSED,
    REASON_NO_LAMBDA_BRACKET,
    REASON_NO_SLICES,
    LEMMethod,
    LEMResult,
    register_method,
)
from .bishop import BishopSimplified, driving_shear_forces


# ----------------------------------------------------------------------
def half_sine(x: float, x0: float, x1: float) -> float:
    if x1 <= x0:
        return 1.0
    return math.sin(math.pi * (x - x0) / (x1 - x0))


def constant(x: float, x0: float, x1: float) -> float:
    return 1.0


def trapezoidal(x: float, x0: float, x1: float) -> float:
    if x1 <= x0:
        return 1.0
    t = (x - x0) / (x1 - x0)
    if t < 0.25:
        return t / 0.25
    if t > 0.75:
        return (1.0 - t) / 0.25
    return 1.0


def clipped_sine(x: float, x0: float, x1: float) -> float:
    """Half sine with its ends lifted off zero.

    A function that reaches exactly zero at both ends forbids any
    interslice shear there. The clipped form keeps a fraction of it,
    which is what the reference offers when the end conditions matter.
    """
    if x1 <= x0:
        return 1.0
    t = (x - x0) / (x1 - x0)
    end = 0.2
    return end + (1.0 - end) * math.sin(math.pi * t)


# v0.1.74 — named so the interface can offer them and a project can
# store the choice. Until now GLE always used the half sine and the user
# had no way to say otherwise, even though the constructor had accepted
# a function since the method was written.
#
# The x coordinate is normalised over the slip surface, and x = 0 is
# always the LEFT-hand end whatever the failure direction is: the
# function is NOT mirrored when the direction is flipped. That is the
# reference's convention, and following it is what keeps a stored value
# meaning the same thing in both programs.
INTERSLICE_FUNCTIONS = {
    "half_sine": half_sine,
    "constant": constant,
    "trapezoidal": trapezoidal,
    "clipped_sine": clipped_sine,
}


def interslice_function(name: str):
    """Look a function up by its stored id, falling back to the half sine."""
    return INTERSLICE_FUNCTIONS.get(str(name), half_sine)


# ----------------------------------------------------------------------
@register_method
class GLEMorgensternPrice(LEMMethod):
    METHOD_ID = "gle_morgenstern_price"
    DISPLAY_NAME = "GLE / Morgenstern-Price"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = True

    def __init__(
        self,
        tolerance: float = 1e-3,
        max_iterations: int = 50,
        initial_fos: float = 1.0,
        interslice_func: Callable[[float, float, float], float] = half_sine,
        min_lambda: float = -0.1,
        # v0.1.90 — the reference's own upper default. It does not widen
        # the first sampling pass; see BaseSearch.lambda_grid.
        max_lambda: float = 6.0,
        iterate_steffensen: bool = False,
    ) -> None:
        # v0.1.74 — this signature has to accept EVERY argument the base
        # class does, because the caller hands the same configuration to
        # all five methods at once. Overriding __init__ and forgetting
        # one of them raised a TypeError while building the method map,
        # which the compute worker caught and turned into an empty
        # result — and an empty result reaches a modal QMessageBox that
        # blocks forever without a screen. Cost: one hung test suite.
        super().__init__(tolerance, max_iterations, initial_fos,
                         min_lambda, max_lambda, iterate_steffensen)
        self.f_func = interslice_func

    def compute_fos(self, project: Project, surface, slices) -> LEMResult:
        # A surface with no shear strength anywhere has F = 0 exactly and
        # no iteration to run; see LEMMethod.NO_SHEAR_STRENGTH_NOTE for why
        # this is answered here rather than left to the arithmetic.
        strengthless = self._no_shear_strength_result(surface, slices)
        if strengthless is not None:
            return strengthless

        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        if not slices.slices:
            return LEMResult(
                fos=None, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="No slices",
                reason=REASON_NO_SLICES,
            )

        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # A circle has a centre; anything else gets an AXIS, and the moment
        # equation becomes a real sum of moments about it (v0.1.105).
        circle_R = surface.radius if isinstance(surface, SlipCircle) else None
        circle_yc = surface.centre_y if isinstance(surface, SlipCircle) else None
        axis = None
        if circle_R is None:
            from ..moment_balance import axis_for
            axis = axis_for(project, surface)

        # v0.1.64 — supports, resolved once for every inner solve below.
        from ..support_integration import (resolve_support_terms,
                                           support_failure_details)
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        x0 = slices.slices[0].base_x_left
        x1 = slices.slices[-1].base_x_right

        # v0.1.106 — the whole surface resolved ONCE, reused at every λ. The
        # shape function is evaluated at the slice BOUNDARIES and not at the
        # slice centres, because X_i lives on a boundary: it is the vertical
        # inter-slice force there, and ``_boundary_ratios`` has always
        # reported it that way. Until now the solver used f(x_centre) and the
        # report used f(x_boundary), so the two disagreed about the very
        # quantity the method is defined by.
        from ..interslice import (FALLBACK_RESIDUAL_LIMIT, GLESystem,
                                  branch_budget, branch_pair_ok,
                                  recover_thrust_edge,
                                  refine_lambda_gap,
                                  thrust_is_admissible, thrust_margin)
        from .. import interslice
        s_list = slices.slices
        shape = [self.f_func(x, x0, x1)
                 for x in self._boundary_x(slices)]
        system = GLESystem(
            s_list, shape, kh, kv, slide_sign, circle_R, circle_yc, sup, axis,
            tolerance=self.tolerance, initial_fos=self.initial_fos,
            # v0.1.173 (D117) — see the twin line in spencer.py. The floor is
            # ``branch_budget``'s and not this call's, deliberately.
            max_passes=branch_budget(self.max_iterations),
        )

        def solve(lam):
            """The inner solve at one λ, with the geometry already bound."""
            return self._inner_solve(slices, lam, system)

        # Outer: bracket and refine λ. Wider grid for difficult slopes;
        # v0.1.74 moved it to the base class so the configured range can
        # clip it. This method is the reason the shape reaches ±1.5: the
        # Ej1 reference circle converges here at λ = 1.4919.
        lam_grid = self.lambda_grid()
        samples: list[Tuple[float, float, float, float]] = []
        for lam in lam_grid:
            ff, fm = solve(lam)
            if (branch_pair_ok(ff, fm)
                    and 0.05 < ff < 50 and 0.05 < fm < 50):
                samples.append((lam, ff - fm, ff, fm))
                # v0.1.93 — stop at the FIRST sign change instead of
                # sampling the whole shape and looking afterwards. Neutral
                # by construction: ``_first_bracket`` scans consecutive
                # pairs in ascending λ and returns the first, and samples
                # are appended in that same order, so the bracket found
                # here is the one it would have found — hence the same
                # root. Measured on the Ej_2 reference grid, 82 % of
                # Spencer's inner solves were this sampling and only 3 per
                # surface were the bisection that actually finds λ.
                #
                # Only cut when a bracket EXISTS. The two paths that need
                # the whole grid are untouched, because both are reached
                # only when nothing bracketed: the "no bracket" fallback
                # picks ``min(samples, key=|g|)`` over every sample, and
                # the v0.1.90 λ-extension runs only after the shape is
                # exhausted.
                if len(samples) > 1 and samples[-2][1] * samples[-1][1] < 0:
                    break

        # v0.1.106 — nothing survived the strict pass. Before giving up,
        # sample again WITHOUT the inter-slice thrust criterion and say so:
        # a surface with no admissible λ anywhere is a real answer about the
        # stress state, but it is not a reason to hand back a NaN where the
        # previous version handed back a number. Measured on the reinforced
        # slope of verification problem 85, where 9000 kN/m of anchorage puts
        # the soil faces in net tension at every λ.
        inadmissible = False
        if not samples and system.n_thrust_rejected:
            inadmissible = True
            system.strict = False
            for lam in lam_grid:
                ff, fm = solve(lam)
                if (branch_pair_ok(ff, fm)
                        and 0.05 < ff < 50 and 0.05 < fm < 50):
                    samples.append((lam, ff - fm, ff, fm))

        if not samples:
            return LEMResult(
                fos=None, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="GLE: all sampled λ diverged",
                reason=REASON_ALL_LAMBDA_DIVERGED,
            )

        def _first_bracket(rows):
            for i in range(len(rows) - 1):
                if rows[i][1] * rows[i + 1][1] < 0:
                    return (rows[i], rows[i + 1])
            return None

        bracket = _first_bracket(samples)

        # v0.1.90 — the calibrated grid brackets nothing: reach further out
        # before giving up. F_f − F_m is monotone in λ for these surfaces,
        # so "no sign change" here usually means the root is beyond ±1.5,
        # not that there is none. Sampled lazily, so every surface that
        # brackets above is untouched. See BaseSearch._LAMBDA_EXTENSION.
        if bracket is None:
            for lam in self.lambda_grid_extension():
                ff, fm = solve(lam)
                if (branch_pair_ok(ff, fm)
                        and 0.05 < ff < 50 and 0.05 < fm < 50):
                    samples.append((lam, ff - fm, ff, fm))
            samples.sort(key=lambda r: r[0])
            bracket = _first_bracket(samples)

        # v0.1.181 (D148) — and, still with no bracket, look INSIDE the gap a
        # lost λ node left behind. The grid steps 0.8, 1.0, 1.5, so a root at
        # 1.31988 with 1.5 unsolvable is invisible to every sample above:
        # fixing the branch solver made 1.30 and 1.32 solvable and the sign
        # change is between them, but neither is a grid node. Only a surface
        # that bracketed nothing pays for this; see
        # ``interslice.GAP_REFINE_STEPS``.
        refinados = 0
        if bracket is None and interslice.LAMBDA_GAP_REFINE:
            extra = refine_lambda_gap(
                samples, solve,
                list(lam_grid) + list(self.lambda_grid_extension()))
            if extra:
                refinados = len(extra)
                samples.extend(extra)
                samples.sort(key=lambda r: r[0])
                bracket = _first_bracket(samples)

        # v0.1.182 (D149) -- and, still with no bracket, put back the lambdas
        # the thrust criterion set aside. Last of the four steps and by far
        # the cheapest: it re-solves NOTHING, because ``branches`` recorded
        # the pair it was about to throw away. AFTER the gap refinement and
        # not before, because the refinement only probes BETWEEN samples and
        # never sees a fuller set either way -- on success this sets
        # ``bracket`` and the refinement does not run, on failure the rows
        # are left untouched -- while putting it first would silently rewrite
        # ``lambda_gap_refined`` on the surfaces v0.1.181 already fixed.
        # See ``interslice.LAMBDA_EDGE_RECOVERY``.
        perdidos_traccion = len(system.thrust_rejected_pairs)
        recuperados = 0
        if (bracket is None and not inadmissible
                and interslice.LAMBDA_EDGE_RECOVERY):
            filas, b = recover_thrust_edge(samples,
                                           system.thrust_rejected_pairs)
            if b is not None:
                recuperados = len(filas) - len(samples)
                samples, bracket = filas, b
                # The secant has to be able to evaluate lambda on the side
                # the criterion rejected -- the bracket straddles it by
                # construction -- or every iterate there comes back
                # ``(None, None)`` and the bracket never closes.
                system.strict = False

        if bracket is None:
            best = min(samples, key=lambda r: abs(r[1]))
            lam_star, _, ff, fm = best
            # v0.1.106 — see ``Spencer.compute_fos``: this path discarded the
            # λ it had and returned an EMPTY ``details``, so a surface that
            # reaches here was drawn with zero inter-slice ratios.
            # v0.1.159 (D63) — the residual this fallback is handing back,
            # published rather than swallowed. See
            # ``interslice.FALLBACK_RESIDUAL_LIMIT`` for why the boundary is
            # not the caller's tolerance; this file keeps the same λ search
            # as ``spencer.py`` line for line, so it keeps this too.
            residual = abs(best[1])
            settled = residual < FALLBACK_RESIDUAL_LIMIT
            force, _moment = system.states(lam_star)
            # v0.1.185 (D156) — see ``Spencer.compute_fos``: the flag of this
            # exit comes from the state it RETURNS and no longer from which
            # pass produced the sample. See
            # ``interslice.THRUST_FLAG_FROM_STATE``.
            estado_inadmisible = (force is None
                                  or not thrust_is_admissible(force))
            flag_inadmisible = (estado_inadmisible
                                if interslice.THRUST_FLAG_FROM_STATE
                                else inadmissible)
            from .spencer import _base_forces
            normals, _mobilised, strengths = _base_forces(system, force)
            # v0.1.107 - ``base_shear_force`` is the DRIVING force in every
            # method now; it used to publish the MOBILISED shear here, which
            # is a factor of the safety factor away. The mobilised shear is
            # exactly ``base_shear_strength / fos``.
            driving = driving_shear_forces(slices, kh, kv, slide_sign)
            return LEMResult(
                fos=0.5 * (ff + fm),
                converged=settled,
                iterations=len(samples),
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                base_normal_force=normals,
                base_shear_force=driving,
                base_shear_strength=strengths,
                # v0.1.176 (D125) — through ``support_failure_details``,
                # see ``Spencer.compute_fos``.
                details=support_failure_details(sup, {
                    "lambda": lam_star,
                    # v0.1.185 (D156) — this exit did not write the key at
                    # all, see ``Spencer.compute_fos``.
                    "thrust_admissible": not estado_inadmisible,
                    # v0.1.185 (D155) — see ``interslice.thrust_margin``.
                    "thrust_margin": thrust_margin(force),
                    "slide_sign": slide_sign,
                    # v0.1.159 (D63) — see ``Spencer.compute_fos``.
                    "lambda_search_fell_back": True,
                    "lambdas_lost_to_budget": system.n_passes_exhausted,
                    # v0.1.171 (D118) — and the lambdas whose inner
                    # iteration was cut for a runaway thrust, which is
                    # a different loss from the one above. See
                    # ``interslice.THRUST_SCALE_LIMIT``.
                    "lambdas_lost_to_thrust_overflow":
                        system.n_thrust_overflow,
                    # v0.1.176 (D125) — see ``Spencer.compute_fos``.
                    "lambdas_lost_to_stall": system.n_stalled,
                    # v0.1.181 (D148) — and the lambdas whose branch came
                    # back with no state at all, which until this version
                    # left every counter above reading zero. See
                    # ``interslice.GLESystem.n_inadmissible``.
                    "lambdas_lost_to_inadmissible": system.n_inadmissible,
                    "lambdas_rescued": system.n_rescued,
                    # v0.1.181 (D148) — how many extra lambdas were sampled
                    # inside the gap a lost node left. Zero on every surface
                    # that brackets, because the refinement only runs when
                    # nothing did. See ``interslice.GAP_REFINE_STEPS``.
                    "lambda_gap_refined": refinados,
                    "lambda_edge_recovered": recuperados,
                    # v0.1.182 (D149) -- how many INCLINATIONS the thrust
                    # criterion set aside, which is NOT ``n_thrust_rejected``:
                    # that counter increments outside the ``strict`` test, so
                    # the all-or-nothing sweep of v0.1.106 doubles it. See
                    # ``interslice.GLESystem.thrust_rejected_pairs``.
                    "lambdas_lost_to_thrust_tension": perdidos_traccion,
                    "lambda_residual": residual,
                    "lambda_tolerance": self.tolerance,
                    "boundary_ratios": [lam_star * fb for fb in system.shape],
                    "interslice_e": ([] if force is None else
                                     system.boundaries_in_slice_order(
                                         force.boundary_e)),
                    "interslice_x": ([] if force is None else
                                     system.boundaries_in_slice_order(
                                         force.boundary_x)),
                }),
                # v0.1.130 — the two judgements this field used to mix are
                # now separate, because they are not the same claim. "No
                # λ-bracket" stays in ``error_message``: there is no root,
                # the pair returned is the nearest crossing, and
                # ``converged`` above already says so. The relaxed-thrust
                # criterion moves to ``admissible`` for the reason given in
                # ``Spencer.compute_fos``. Verification problems 85 (GLE) and
                # 91 (Spencer) reach the engine by THIS branch and do not
                # converge, so what the bank publishes on their circle is a
                # fallback value, not a measurement.
                error_message=("" if settled else
                               "GLE: no λ-bracket; the nearest λ leaves "
                               "F_f − F_m at %.3g" % residual),
                reason=("" if settled else REASON_NO_LAMBDA_BRACKET),
                admissible=not flag_inadmisible,
                # v0.1.185 (D156) — the note follows the FLAG and its wording
                # is untouched; see ``Spencer.compute_fos`` for why re-wording
                # it would have measured something else.
                admissibility_note=(
                    "" if not flag_inadmisible else
                    "GLE: no λ leaves the inter-slice thrust in net "
                    "compression; the answer is reported with the criterion "
                    "relaxed"),
            )

        (lam_lo, g_lo, ff_lo, fm_lo), (lam_hi, g_hi, ff_hi, fm_hi) = bracket
        iterations = len(samples)
        converged = False

        for _ in range(self.max_iterations):
            iterations += 1
            if abs(g_hi - g_lo) < 1e-12:
                break
            # v0.1.184 (D153) - nothing is left between the two ends, so
            # every remaining turn would re-solve a lambda that rounds to
            # one of them and hand back the g it already has: the loop
            # state past this point is a FIXED POINT, not a slow descent.
            # The midpoint test carries no constant because the grid of the
            # doubles is itself relative to magnitude, and both ends have to
            # clear the tolerance first because a bracket end taken straight
            # from the grid was never tested against it. See
            # ``interslice.LAMBDA_BRACKET_FLOOR_CUT``.
            if interslice.LAMBDA_BRACKET_FLOOR_CUT:
                mid = 0.5 * (lam_lo + lam_hi)
                if ((mid == lam_lo or mid == lam_hi)
                        and abs(g_lo) >= self.tolerance
                        and abs(g_hi) >= self.tolerance):
                    break
            lam_new = lam_hi - g_hi * (lam_hi - lam_lo) / (g_hi - g_lo)
            if not (min(lam_lo, lam_hi) <= lam_new <= max(lam_lo, lam_hi)):
                lam_new = 0.5 * (lam_lo + lam_hi)
            ff, fm = solve(lam_new)
            if not (branch_pair_ok(ff, fm) and ff > 0 and fm > 0):
                lam_new = 0.5 * (lam_lo + lam_hi)
                ff, fm = solve(lam_new)
                if not (branch_pair_ok(ff, fm)):
                    break
            g_new = ff - fm
            if abs(g_new) < self.tolerance:
                lam_lo = lam_new
                g_lo = g_new
                ff_lo, fm_lo = ff, fm
                converged = True
                break
            if g_lo * g_new < 0:
                lam_hi, g_hi, ff_hi, fm_hi = lam_new, g_new, ff, fm
            else:
                lam_lo, g_lo, ff_lo, fm_lo = lam_new, g_new, ff, fm

        ff_final, fm_final = solve(lam_lo)
        if not (branch_pair_ok(ff_final, fm_final)):
            return LEMResult(
                fos=None, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="GLE: divergent at final λ",
                reason=REASON_DIVERGENT_AT_LAMBDA,
            )
        # v0.1.180 (D146) — see ``Spencer.compute_fos``: measured on the pair
        # that produces the factor being returned and not on ``g_lo``, which
        # can be one refinement stale.
        lam_residual = abs(ff_final - fm_final)
        lam_width = abs(lam_hi - lam_lo)
        force, moment = system.states(lam_lo)
        from .spencer import _base_forces
        normals, _mobilised, strengths = _base_forces(system, force)
        # v0.1.107 - ``base_shear_force`` is the DRIVING force in every
        # method now; it used to publish the MOBILISED shear here, which
        # is a factor of the safety factor away. The mobilised shear is
        # exactly ``base_shear_strength / fos``.
        driving = driving_shear_forces(slices, kh, kv, slide_sign)
        # v0.1.106 — see ``Spencer.compute_fos``: the flag is a property of
        # the state returned, not of the pass that found it.
        inadmissible = force is None or not thrust_is_admissible(force)
        return LEMResult(
            fos=0.5 * (ff_final + fm_final),
            converged=converged,
            iterations=iterations,
            # v0.1.180 (D146) — see ``Spencer.compute_fos``: what failed here
            # is the OUTER search for λ, and it used to answer with the code
            # and the sentence of the factor-of-safety iteration of Bishop
            # and Janbu. See ``REASON_LAMBDA_NOT_CLOSED``.
            error_message=("" if converged else
                           "GLE: the λ bracket did not close; "
                           "F_f − F_m is %.3g at λ = %.6g, with the bracket "
                           "at %.3g after %d iterations"
                           % (lam_residual, lam_lo, lam_width, iterations)),
            reason="" if converged else REASON_LAMBDA_NOT_CLOSED,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=normals,
            base_shear_force=driving,
            base_shear_strength=strengths,
            # v0.1.130 — see the note in ``Spencer.compute_fos``: this is a
            # PREFERENCE and ``error_message`` is a veto. Moved to
            # ``admissible``, which is where ``LEMResult`` says a converged
            # but physically unreliable answer belongs.
            admissible=not inadmissible,
            admissibility_note=(
                "" if not inadmissible else
                "GLE: no λ leaves the inter-slice thrust in net compression; "
                "the answer is reported with the criterion relaxed"),
            details=support_failure_details(sup, {
                "lambda": lam_lo,
                "thrust_admissible": not inadmissible,
                # v0.1.185 (D155) — see ``interslice.thrust_margin``.
                "thrust_margin": thrust_margin(force),
                "slide_sign": slide_sign,
                # v0.1.159 (D63) — see ``Spencer.compute_fos``.
                "lambda_search_fell_back": False,
                "lambdas_lost_to_budget": system.n_passes_exhausted,
                # v0.1.171 (D118) — see the fallback branch above.
                "lambdas_lost_to_thrust_overflow":
                    system.n_thrust_overflow,
                # v0.1.176 (D125) — see the fallback branch above.
                "lambdas_lost_to_stall": system.n_stalled,
                "lambdas_lost_to_inadmissible": system.n_inadmissible,
                "lambdas_rescued": system.n_rescued,
                "lambda_gap_refined": refinados,
                "lambda_edge_recovered": recuperados,
                # v0.1.182 (D149) -- how many INCLINATIONS the thrust
                # criterion set aside, which is NOT ``n_thrust_rejected``:
                # that counter increments outside the ``strict`` test, so
                # the all-or-nothing sweep of v0.1.106 doubles it. See
                # ``interslice.GLESystem.thrust_rejected_pairs``.
                "lambdas_lost_to_thrust_tension": perdidos_traccion,
                # v0.1.180 (D146) — see ``Spencer.compute_fos`` for why the
                # residual is ``None`` when a root WAS closed.
                "lambda_residual": None if converged else lam_residual,
                "lambda_tolerance": self.tolerance,
                "lambda_bracket_width": lam_width,
                # Boundary ratios λ·f(x) evaluated at the n+1 slice
                # boundaries with x normalised over the surface span. The
                # solver uses exactly this list (v0.1.106).
                "boundary_ratios": [lam_lo * fb for fb in system.shape],
                "interslice_e": ([] if force is None else
                                 system.boundaries_in_slice_order(
                                     force.boundary_e)),
                "interslice_x": ([] if force is None else
                                 system.boundaries_in_slice_order(
                                     force.boundary_x)),
            }),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _boundary_x(slices: Slices) -> list[float]:
        """The abscissa of each of the n+1 slice boundaries."""
        slist = slices.slices
        return [slist[0].base_x_left] + [s.base_x_right for s in slist]

    # ------------------------------------------------------------------
    def _boundary_ratios(self, slices: Slices, lam: float,
                         x0: float, x1: float) -> list[float]:
        """λ·f(x) at each of the n+1 slice boundaries."""
        return [lam * self.f_func(x, x0, x1)
                for x in self._boundary_x(slices)]

    # ==================================================================
    def _inner_solve(self, slices, lam: float, system) -> Tuple[float, float]:
        """Return ``(F_f, F_m)`` at the given inter-slice ratio λ.

        v0.1.106 — the arithmetic moved to :mod:`ogr_slip2d.interslice`, which
        this method now shares with Spencer line for line: GLE differs only in
        the shape function f(x), so "GLE with a constant f IS Spencer" became
        an identity of the code rather than of the documentation. See
        :meth:`Spencer._inner_solve` for the three things that changed, and
        ``docs/audits/spencer_gle_interslice_v179.md`` for the measurements.

        ``slices`` is unused and kept because the tests that watch the λ
        search read λ from the second positional argument.
        """
        return system.branches(lam)
