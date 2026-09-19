# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Spencer's Method of Slices.

Reference: Spencer, E. (1967). "A method of analysis of the stability
of embankments assuming parallel inter-slice forces." Géotechnique
17(1), 11-26.

Implementation follows the Fredlund-Krahn (1977) "General Limit
Equilibrium" formulation specialised to f(x) ≡ 1, i.e. a constant
inter-slice force ratio

    X_i / E_i = λ        (Spencer's defining assumption)

Everything below that line — the base normal that carries the inter-slice
shear difference, the horizontal force recursion that produces E, and the
two branches F_f(λ) and F_m(λ) — lives in :mod:`ogr_slip2d.interslice`,
which this method shares with GLE/Morgenstern-Price. The module docstring
carries the equations and the reason each one is written as it is.

What is left here is the OUTER problem: find the λ where the force and the
moment factors of safety agree.

    - sample λ over a calibrated grid until g(λ) = F_f − F_m changes sign
    - refine with a secant/bisection hybrid
    - the answer is F_f = F_m at that λ

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Tuple

from ogr_core.project import Project

from ..slicer import Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import (
    REASON_ALL_LAMBDA_DIVERGED,
    REASON_DIVERGENT_AT_LAMBDA,
    REASON_LAMBDA_NOT_CLOSED,
    REASON_NO_LAMBDA_BRACKET,
    LEMMethod,
    LEMResult,
    register_method,
)
from .bishop import BishopSimplified, driving_shear_forces


@register_method
class Spencer(LEMMethod):
    METHOD_ID = "spencer"
    DISPLAY_NAME = "Spencer"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = True

    # ------------------------------------------------------------------
    def compute_fos(
        self, project: Project, surface: SurfaceProtocol, slices: Slices,
    ) -> LEMResult:
        # A surface with no shear strength anywhere has F = 0 exactly and
        # no iteration to run; see LEMMethod.NO_SHEAR_STRENGTH_NOTE for why
        # this is answered here rather than left to the arithmetic.
        strengthless = self._no_shear_strength_result(surface, slices)
        if strengthless is not None:
            return strengthless

        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # Geometry — only used for the moment expression. A circle has a
        # centre; anything else gets an AXIS, and the moment equation becomes
        # a real sum of moments about it (v0.1.105).
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

        # v0.1.106 — the whole surface is resolved ONCE here and reused at
        # every λ. Spencer is GLE with f(x) = 1 at every boundary, and that
        # is the only line of this method that GLE does not share.
        from ..interslice import (FALLBACK_RESIDUAL_LIMIT, GLESystem,
                                  branch_budget, branch_pair_ok,
                                  refine_lambda_gap)
        from .. import interslice
        s_list = slices.slices if hasattr(slices, "slices") else list(slices)
        system = GLESystem(
            s_list, [1.0] * (len(s_list) + 1), kh, kv, slide_sign,
            circle_R, circle_yc, sup, axis,
            tolerance=self.tolerance, initial_fos=self.initial_fos,
            # v0.1.173 (D117) — until this version ``max_iterations`` bounded
            # the λ secant below and nothing else, while the fixed point this
            # method actually solves ran on a constant the settings could not
            # reach. The floor lives in ``branch_budget`` and not here, so
            # that this line and gle.py's cannot drift apart.
            max_passes=branch_budget(self.max_iterations),
        )

        def solve(lam):
            """The inner solve at one λ, with the geometry already bound."""
            return self._inner_solve(slices, lam, system)

        # Outer loop: bracket λ (= tan θ) and use bisection / secant
        # to drive g(λ) = F_f − F_m to zero. The grid may need to reach
        # ±1.5 for some slope geometries; v0.1.74 moved it to the base
        # class so the range the user configures can clip it.
        lam_grid = self.lambda_grid()
        samples: list[Tuple[float, float, float, float]] = []  # (lam, g, ff, fm)
        for lam in lam_grid:
            ff, fm = solve(lam)
            if (branch_pair_ok(ff, fm)
                    and ff > 0.05 and fm > 0.05 and ff < 50 and fm < 50):
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
                error_message="Spencer: all sampled λ diverged",
                reason=REASON_ALL_LAMBDA_DIVERGED,
            )

        # Find a bracket (sign change in g)
        def _first_bracket(rows):
            for i in range(len(rows) - 1):
                if rows[i][1] * rows[i + 1][1] < 0:
                    return (rows[i], rows[i + 1])
            return None

        bracket = _first_bracket(samples)

        # v0.1.90 — same lazy extension as GLE, and for the same measured
        # reason: 13 of 49 Simulated Annealing candidates failed here with
        # "no λ-bracket" while their root simply sat beyond the calibrated
        # ±1.5. Only surfaces that bracket nothing pay for these samples.
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

        if bracket is None:
            # No bracket → return the sample with smallest |g| (closest
            # to F_f = F_m). Often happens for very stable slopes.
            best = min(samples, key=lambda r: abs(r[1]))
            lam_star, _, ff, fm = best
            # v0.1.159 (D63) — how far apart the two branches actually are
            # at the lambda being handed back, and whether that is inside
            # what the caller asked for. This used to be compared against a
            # hardcoded 0.02, a number with no relation to ``tolerance``:
            # twenty thousand times it at 1e-6. On the 50 degree plane of
            # ``tests/test_janbu_wedge_v1142.py`` at that tolerance Spencer
            # published a factor 0.72 % off the closed form with
            # ``converged=True``, an empty ``error_message`` and an empty
            # ``reason`` — a reserve value wearing the clothes of an answer.
            # Making this the caller's tolerance was tried and measured to
            # be worse than the defect — see ``FALLBACK_RESIDUAL_LIMIT``.
            # The residual travels in ``details`` instead, where saying it
            # vetoes nothing.
            residual = abs(best[1])
            settled = residual < FALLBACK_RESIDUAL_LIMIT
            # v0.1.106 — this path used to discard ``lam_star`` and return a
            # result with an EMPTY ``details``. A surface that reaches here
            # can still be reported as converged (|F_f − F_m| inside the
            # requested tolerance since v0.1.159), and
            # then the slice panel and ``compute_interslice_state`` had no λ
            # to work with and silently marched the surface with zero
            # inter-slice ratios — a Janbu picture over a Spencer number.
            force, _moment = system.states(lam_star)
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
                # v0.1.176 (D125) — through ``support_failure_details`` like
                # the bracketed exit below: until this version a reinforced
                # surface that fell back lost the D94 ``support_failure``
                # key, so the one exit where the reinforcement most needs
                # explaining was the one that could not.
                details=support_failure_details(sup, {
                    "lambda": lam_star,
                    "slide_sign": slide_sign,
                    # v0.1.159 (D63) — this is the path where losing a λ can
                    # decide the answer, so this is the path that has to be
                    # able to say it did. See ``analysis_runner.lambda_budget_note``.
                    "lambda_search_fell_back": True,
                    "lambdas_lost_to_budget": system.n_passes_exhausted,
                    # v0.1.171 (D118) — and the lambdas whose inner
                    # iteration was cut for a runaway thrust, which is
                    # a different loss from the one above. See
                    # ``interslice.THRUST_SCALE_LIMIT``.
                    "lambdas_lost_to_thrust_overflow":
                        system.n_thrust_overflow,
                    # v0.1.176 (D125) — the lambdas whose branch stalled and
                    # the ones that are a pair only thanks to the rescue.
                    # See ``interslice.RESCUE_OMEGA_MIN``.
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
                    "lambda_residual": residual,
                    "lambda_tolerance": self.tolerance,
                    "boundary_ratios": [lam_star] * (len(slices.slices) + 1),
                    "interslice_e": ([] if force is None else
                                     system.boundaries_in_slice_order(
                                         force.boundary_e)),
                    "interslice_x": ([] if force is None else
                                     system.boundaries_in_slice_order(
                                         force.boundary_x)),
                }),
                # v0.1.130 — the same split as the λ-bracket branch of
                # ``gle.py``: "no λ-bracket" is a failed solve and stays a
                # veto, the relaxed-thrust criterion is a preference and
                # moves to ``admissible``. Mixing them meant a surface with
                # a perfectly good bracket was thrown out with the same
                # force as one with none.
                error_message=("" if settled else
                               "Spencer: no λ-bracket; the nearest λ leaves "
                               "F_f − F_m at %.3g" % residual),
                reason=("" if settled else REASON_NO_LAMBDA_BRACKET),
                admissible=not inadmissible,
                admissibility_note=(
                    "" if not inadmissible else
                    "Spencer: no λ leaves the inter-slice thrust in net "
                    "compression; the answer is reported with the criterion "
                    "relaxed"),
            )

        (lam_lo, g_lo, ff_lo, fm_lo), (lam_hi, g_hi, ff_hi, fm_hi) = bracket
        iterations = len(samples)
        converged = False

        # Bisection-secant hybrid: secant when stable, fallback to
        # bisection if g moves the wrong way.
        for _ in range(self.max_iterations):
            iterations += 1
            if abs(g_hi - g_lo) < 1e-12:
                break
            # Secant step
            lam_new = lam_hi - g_hi * (lam_hi - lam_lo) / (g_hi - g_lo)
            # If secant step is outside the bracket, fall back to bisection
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
            # Maintain bracket
            if g_lo * g_new < 0:
                lam_hi, g_hi, ff_hi, fm_hi = lam_new, g_new, ff, fm
            else:
                lam_lo, g_lo, ff_lo, fm_lo = lam_new, g_new, ff, fm

        # Final FoS at converged λ
        ff_final, fm_final = solve(lam_lo)
        if not (branch_pair_ok(ff_final, fm_final)):
            return LEMResult(
                fos=None, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="Spencer: divergent at final λ",
                reason=REASON_DIVERGENT_AT_LAMBDA,
            )
        # v0.1.180 (D146) — what the λ search actually achieved, measured on
        # the pair that produces the factor being returned rather than on
        # ``g_lo``, which can be one refinement stale. The width is what
        # separates the four ways this loop fails to close: a bracket at the
        # floor of the double has no λ left to sample, while a wide one was
        # still being refined when the budget ran out. See
        # ``REASON_LAMBDA_NOT_CLOSED``.
        lam_residual = abs(ff_final - fm_final)
        lam_width = abs(lam_hi - lam_lo)
        force, moment = system.states(lam_lo)
        normals, _mobilised, strengths = _base_forces(system, force)
        # v0.1.107 - ``base_shear_force`` is the DRIVING force in every
        # method now; it used to publish the MOBILISED shear here, which
        # is a factor of the safety factor away. The mobilised shear is
        # exactly ``base_shear_strength / fos``.
        driving = driving_shear_forces(slices, kh, kv, slide_sign)
        # v0.1.106 — the flag comes from the state that was RETURNED, not
        # from which pass produced it. A bisection can land on a lambda its
        # bracketing samples did not share, so "the strict pass found this"
        # is not the same claim as "this answer is admissible".
        from ..interslice import thrust_is_admissible
        inadmissible = force is None or not thrust_is_admissible(force)
        return LEMResult(
            fos=0.5 * (ff_final + fm_final),
            converged=converged,
            iterations=iterations,
            # v0.1.180 (D146) — this used to be ``NOT_CONVERGED_NOTE`` and
            # ``REASON_NOT_CONVERGED``, a sentence about "the factor of
            # safety iteration" that never mentions λ and a code Bishop and
            # Janbu give for their own, unrelated loop. What failed here is
            # the OUTER search for λ, and the three numbers below are what
            # tell its four failure modes apart. See
            # ``REASON_LAMBDA_NOT_CLOSED``.
            error_message=("" if converged else
                           "Spencer: the λ bracket did not close; "
                           "F_f − F_m is %.3g at λ = %.6g, with the bracket "
                           "at %.3g after %d iterations"
                           % (lam_residual, lam_lo, lam_width, iterations)),
            reason="" if converged else REASON_LAMBDA_NOT_CLOSED,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=normals,
            base_shear_force=driving,
            base_shear_strength=strengths,
            # v0.1.130 — this used to go in ``error_message``, and that field
            # is a VETO: it feeds ``is_valid``, which scores the surface
            # ``inf`` in ``search.surface_score`` and excludes it from
            # ``SearchResult.critical`` with no fallback, so a search could
            # never report it. The message said "the answer is reported" and
            # the answer was not reported: it was discarded. ``interslice.py``
            # states the intent — the strict pass "is a PREFERENCE, not a
            # veto" — and ``LEMResult`` says where a converged but physically
            # unreliable answer belongs. It belongs here. ``admissible`` keeps
            # the surface out of the critical pick while other surfaces exist
            # and hands it back when none do (``ok or valid``), which is what
            # a preference means. Defect D37/C1 of the verification bank:
            # verification problems 60, 90 and 93 published a search minimum
            # ABOVE the factor the same engine computes on the manual's own
            # circle, because that circle was solved and then erased.
            admissible=not inadmissible,
            admissibility_note=(
                "" if not inadmissible else
                "Spencer: no λ leaves the inter-slice thrust in net compression; "
                "the answer is reported with the criterion relaxed"),
            details=support_failure_details(sup, {
                "lambda": lam_lo,
                "thrust_admissible": not inadmissible,
                "slide_sign": slide_sign,
                # v0.1.159 (D63) — false here by construction: a bracket was
                # found and refined. Written rather than omitted so that a
                # reader of ``details`` does not have to know which of the
                # two exits produced it.
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
                # v0.1.180 (D146) — the diagnosis of the λ search itself,
                # which this exit could not give until now. ``None`` when a
                # root WAS closed, and that is not coyness: below the
                # tolerance the residual says nothing ``lambda_tolerance``
                # does not already say, and writing a number there would
                # turn 229 archived nulls in the verification bank into
                # values for no defect. Present therefore means the same on
                # both exits of this method — the λ search did not close a
                # root by refinement.
                "lambda_residual": None if converged else lam_residual,
                "lambda_tolerance": self.tolerance,
                "lambda_bracket_width": lam_width,
                # Constant interslice ratio at every boundary (Spencer).
                "boundary_ratios": [lam_lo] * (len(slices.slices) + 1),
                # v0.1.106 — the inter-slice forces themselves, which this
                # method now actually forms. The two ends are zero by
                # construction: a free end carries none.
                "interslice_e": ([] if force is None else
                                 system.boundaries_in_slice_order(
                                     force.boundary_e)),
                "interslice_x": ([] if force is None else
                                 system.boundaries_in_slice_order(
                                     force.boundary_x)),
            }),
        )

    # ==================================================================
    # Inner solver — the two GLE branches at one lambda
    # ==================================================================
    def _inner_solve(self, slices, lam: float, system) -> Tuple[float, float]:
        """Return ``(F_f, F_m)`` at the given inter-slice ratio λ.

        v0.1.106 — the arithmetic moved to :mod:`ogr_slip2d.interslice`, which
        Spencer and GLE now share, and it changed in three ways. The two that
        were defects:

        * the force branch summed ``S·cos α`` where global horizontal
          equilibrium gives ``S·sec α``, so ``F_f(0)`` came out at 0,50 to
          0,79 of Janbu simplified — the identity it must reproduce exactly;
        * both branches were driven by ONE shared iterate ``F = (F_f+F_m)/2``,
          so neither was its own fixed point and ``F_m(0)`` fell 2-4 % short
          of Bishop.

        And the one that made the method a method: the base normal now
        carries the inter-slice shear difference ``(X_R − X_L)``, obtained
        from the horizontal force recursion of Fredlund and Krahn (1977).
        Without it the moment branch contains no λ at all, ``F_m(λ)`` is a
        constant, and the root ``F_f = F_m`` lands on Bishop whatever λ does —
        which is exactly what this method did for its first eighty versions.

        ``slices`` is unused and kept because the tests that watch the λ
        search read λ from the second positional argument.
        """
        return system.branches(lam)


# ----------------------------------------------------------------------
def _base_forces(system, force):
    """Per-slice base normal, mobilised shear and available strength.

    Reported from the FORCE branch, which is the one that solved a per-slice
    equilibrium: its ``N`` satisfies the vertical equilibrium of each slice
    including the inter-slice shear, and its ``S/F`` is the shear that
    equilibrium actually mobilises. Until v0.1.106 these three lists were
    empty for Spencer and GLE, which mattered beyond reporting —
    ``rapid_drawdown._stage1_state`` reads ``base_normal_force`` to recover the
    stage-1 consolidation state and silently did nothing without it.

    v0.1.107 - the MIDDLE value is the mobilised shear and no longer travels
    to ``LEMResult.base_shear_force``, which is the driving force in every
    method now. It is kept because it is the quantity this branch solved for,
    and it is reachable from outside as ``base_shear_strength / fos``.
    """
    if force is None:
        return [], [], []
    F = force.fos
    # Everything the branch produced is in MARCHING order; the caller and the
    # slice panel index by slice.
    rows = system.to_slice_order(system.rows)
    n_of = system.to_slice_order(force.normals)
    normals: list[float] = []
    shears: list[float] = []
    strengths: list[float] = []
    for i, r in enumerate(rows):
        n_i = n_of[i]
        length = max(r.length, 1e-9)
        # Reported with its sign, exactly as Bishop does since v0.1.96:
        # clamping sigma' at zero hands a base in tension the full cohesion.
        sigma_eff = n_i / length - r.u
        c_rep, tan_phi_rep = BishopSimplified._local_c_phi(
            system.s_list[i], system.s_list[i].material, sigma_eff)
        tau = max(0.0, c_rep + sigma_eff * tan_phi_rep)
        normals.append(n_i)
        shears.append((c_rep * length + (n_i - r.u * length) * tan_phi_rep) / F)
        strengths.append(tau * length)
    return normals, shears, strengths
