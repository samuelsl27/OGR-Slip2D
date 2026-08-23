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
from .base import LEMMethod, LEMResult, register_method
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
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="No slices",
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
        from ..support_integration import resolve_support_terms
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
        from ..interslice import GLESystem
        s_list = slices.slices
        shape = [self.f_func(x, x0, x1)
                 for x in self._boundary_x(slices)]
        system = GLESystem(
            s_list, shape, kh, kv, slide_sign, circle_R, circle_yc, sup, axis,
            tolerance=self.tolerance, initial_fos=self.initial_fos,
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
            if (math.isfinite(ff) and math.isfinite(fm)
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
                if (math.isfinite(ff) and math.isfinite(fm)
                        and 0.05 < ff < 50 and 0.05 < fm < 50):
                    samples.append((lam, ff - fm, ff, fm))

        if not samples:
            return LEMResult(
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="GLE: all sampled λ diverged",
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
                if (math.isfinite(ff) and math.isfinite(fm)
                        and 0.05 < ff < 50 and 0.05 < fm < 50):
                    samples.append((lam, ff - fm, ff, fm))
            samples.sort(key=lambda r: r[0])
            bracket = _first_bracket(samples)

        if bracket is None:
            best = min(samples, key=lambda r: abs(r[1]))
            lam_star, _, ff, fm = best
            # v0.1.106 — see ``Spencer.compute_fos``: this path discarded the
            # λ it had and returned an EMPTY ``details``, so a surface that
            # reaches here was drawn with zero inter-slice ratios.
            force, _moment = system.states(lam_star)
            from .spencer import _base_forces
            normals, _mobilised, strengths = _base_forces(system, force)
            # v0.1.107 - ``base_shear_force`` is the DRIVING force in every
            # method now; it used to publish the MOBILISED shear here, which
            # is a factor of the safety factor away. The mobilised shear is
            # exactly ``base_shear_strength / fos``.
            driving = driving_shear_forces(slices, kh, kv, slide_sign)
            return LEMResult(
                fos=0.5 * (ff + fm),
                converged=abs(best[1]) < 0.02,
                iterations=len(samples),
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                base_normal_force=normals,
                base_shear_force=driving,
                base_shear_strength=strengths,
                details={
                    "lambda": lam_star,
                    "slide_sign": slide_sign,
                    "boundary_ratios": [lam_star * fb for fb in system.shape],
                    "interslice_e": ([] if force is None else
                                     system.boundaries_in_slice_order(
                                         force.boundary_e)),
                    "interslice_x": ([] if force is None else
                                     system.boundaries_in_slice_order(
                                         force.boundary_x)),
                },
                error_message=(
                    ("GLE: no λ-bracket; using nearest F_f≈F_m"
                     if abs(best[1]) >= 0.02 else None)
                    if not inadmissible else
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
            lam_new = lam_hi - g_hi * (lam_hi - lam_lo) / (g_hi - g_lo)
            if not (min(lam_lo, lam_hi) <= lam_new <= max(lam_lo, lam_hi)):
                lam_new = 0.5 * (lam_lo + lam_hi)
            ff, fm = solve(lam_new)
            if not (math.isfinite(ff) and math.isfinite(fm) and ff > 0 and fm > 0):
                lam_new = 0.5 * (lam_lo + lam_hi)
                ff, fm = solve(lam_new)
                if not (math.isfinite(ff) and math.isfinite(fm)):
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
        if not (math.isfinite(ff_final) and math.isfinite(fm_final)):
            return LEMResult(
                fos=math.nan, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="GLE: divergent at final λ",
            )
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
        from ..interslice import thrust_is_admissible
        inadmissible = force is None or not thrust_is_admissible(force)
        return LEMResult(
            fos=0.5 * (ff_final + fm_final),
            converged=converged,
            iterations=iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=normals,
            base_shear_force=driving,
            base_shear_strength=strengths,
            error_message=(
                "" if not inadmissible else
                "GLE: no λ leaves the inter-slice thrust in net compression; "
                "the answer is reported with the criterion relaxed"),
            details={
                "lambda": lam_lo,
                "thrust_admissible": not inadmissible,
                "slide_sign": slide_sign,
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
            },
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
