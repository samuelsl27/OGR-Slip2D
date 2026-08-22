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
from .bishop import BishopSimplified


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
        min_lambda: float = -1.5,
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

        circle_R = surface.radius if isinstance(surface, SlipCircle) else None
        circle_yc = surface.centre_y if isinstance(surface, SlipCircle) else None

        # v0.1.64 — supports, resolved once for every inner solve below.
        from ..support_integration import resolve_support_terms
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        x0 = slices.slices[0].base_x_left
        x1 = slices.slices[-1].base_x_right

        # Outer: bracket and refine λ. Wider grid for difficult slopes;
        # v0.1.74 moved it to the base class so the configured range can
        # clip it. This method is the reason the shape reaches ±1.5: the
        # Ej1 reference circle converges here at λ = 1.4919.
        lam_grid = self.lambda_grid()
        samples: list[Tuple[float, float, float, float]] = []
        for lam in lam_grid:
            ff, fm = self._inner_solve(
                slices, lam, kh, kv, slide_sign,
                circle_R, circle_yc, x0, x1, sup,
            )
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
                ff, fm = self._inner_solve(
                    slices, lam, kh, kv, slide_sign,
                    circle_R, circle_yc, x0, x1, sup,
                )
                if (math.isfinite(ff) and math.isfinite(fm)
                        and 0.05 < ff < 50 and 0.05 < fm < 50):
                    samples.append((lam, ff - fm, ff, fm))
            samples.sort(key=lambda r: r[0])
            bracket = _first_bracket(samples)

        if bracket is None:
            best = min(samples, key=lambda r: abs(r[1]))
            _, _, ff, fm = best
            return LEMResult(
                fos=0.5 * (ff + fm),
                converged=abs(best[1]) < 0.02,
                iterations=len(samples),
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message=("GLE: no λ-bracket; using nearest F_f≈F_m"
                               if abs(best[1]) >= 0.02 else None),
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
            ff, fm = self._inner_solve(
                slices, lam_new, kh, kv, slide_sign,
                circle_R, circle_yc, x0, x1, sup,
            )
            if not (math.isfinite(ff) and math.isfinite(fm) and ff > 0 and fm > 0):
                lam_new = 0.5 * (lam_lo + lam_hi)
                ff, fm = self._inner_solve(
                    slices, lam_new, kh, kv, slide_sign,
                    circle_R, circle_yc, x0, x1, sup,
                )
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

        ff_final, fm_final = self._inner_solve(
            slices, lam_lo, kh, kv, slide_sign,
            circle_R, circle_yc, x0, x1, sup,
        )
        if not (math.isfinite(ff_final) and math.isfinite(fm_final)):
            return LEMResult(
                fos=math.nan, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="GLE: divergent at final λ",
            )
        return LEMResult(
            fos=0.5 * (ff_final + fm_final),
            converged=converged,
            iterations=iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            details={
                "lambda": lam_lo,
                "slide_sign": slide_sign,
                # Boundary ratios λ·f(x) evaluated at the n+1 slice
                # boundaries with x normalised over the surface span.
                "boundary_ratios": self._boundary_ratios(
                    slices, lam_lo, x0, x1
                ),
            },
        )

    # ------------------------------------------------------------------
    def _boundary_ratios(self, slices: Slices, lam: float,
                         x0: float, x1: float) -> list[float]:
        """λ·f(x) at each of the n+1 slice boundaries."""
        slist = slices.slices
        xs = [slist[0].base_x_left] + [s.base_x_right for s in slist]
        return [lam * self.f_func(x, x0, x1) for x in xs]

    # ==================================================================
    def _inner_solve(
        self, slices: Slices, lam: float,
        kh: float, kv: float, slide_sign: float,
        circle_R, circle_yc, x0: float, x1: float, sup=None,
    ) -> Tuple[float, float]:
        F = max(0.5, self.initial_fos)
        s_list = slices.slices if hasattr(slices, "slices") else slices
        ff_last = math.nan
        fm_last = math.nan

        for _it in range(80):
            num_m = 0.0
            den_m = 0.0
            num_f = 0.0
            den_f = 0.0

            for i_s, s in enumerate(s_list):
                fx = slice_forces(s, kh, kv)
                # v0.1.61 — soil + ponded water for the base normal;
                # the water thrust resolved along the sliding direction,
                # whose x component is −slide_sign.
                W_eff = fx.w_total
                H_eq = fx.h_seismic
                H_water = -slide_sign * fx.h_water
                # v0.1.64 — the support as an external force on the slice,
                # exactly as in Spencer: its vertical component joins the
                # load the base normal carries, so T_N·tanφ' emerges from
                # the equilibrium instead of being added to the ratio.
                H_support = 0.0
                if sup is not None and sup.present:
                    W_eff -= sup.f_v[i_s]
                    H_support = -slide_sign * sup.f_h[i_s]
                # Flip α once according to detected sliding direction
                alpha = slide_sign * s.base_angle
                l = s.base_length
                b = s.width
                u = s.pore_pressure

                # Per-slice f(x) shape factor for GLE
                f_i = self.f_func(s.x_centre, x0, x1)
                lam_i = lam * f_i

                sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / max(l, 1e-9)
                c_loc, tan_phi = BishopSimplified._local_c_phi(
                    s, s.material, sigma_est
                )

                m_alpha = math.cos(alpha) + math.sin(alpha) * tan_phi / F
                if abs(m_alpha) < 1e-6:
                    return math.nan, math.nan

                S_term = (c_loc * b + (W_eff - u * b) * tan_phi) / m_alpha

                # Moment side
                num_m += S_term
                # v0.1.100 — the MOMENT side takes its arm from the
                # geometry, see ``Slice.weight_arm_ratio``; the FORCE side
                # below keeps sin(alpha), which there is a direction and
                # not an arm.
                den_m += W_eff * slide_sign * s.weight_arm_ratio
                if kh > 0 and circle_R is not None:
                    y_cg = 0.5 * (
                        0.5 * (s.top_y_left + s.top_y_right)
                        + 0.5 * (s.base_y_left + s.base_y_right)
                    )
                    arm = (circle_yc - y_cg) / circle_R
                    den_m += H_eq * arm
                if circle_R is not None:
                    den_m += (
                        -slide_sign
                        * fx.water_moment_about(circle_yc) / circle_R
                    )
                    if sup is not None and sup.present and sup.f_h[i_s]:
                        # The vertical component needs no term: folded
                        # into W_eff, it already rides the R·sin α arm.
                        den_m += (
                            -slide_sign * sup.f_h[i_s]
                            * (circle_yc - sup.y_app[i_s]) / circle_R
                        )

                # Force side: λ·f_i modulates the numerator
                num_f += S_term * math.cos(alpha)
                num_f += lam_i * S_term * math.sin(alpha)
                den_f += W_eff * math.tan(alpha) + H_eq + H_water + H_support

            if abs(den_m) < 1e-9 or abs(den_f) < 1e-9:
                return math.nan, math.nan
            new_fm = num_m / den_m
            new_ff = num_f / den_f
            if not (math.isfinite(new_fm) and math.isfinite(new_ff)):
                return math.nan, math.nan
            if new_fm <= 0 or new_ff <= 0:
                return math.nan, math.nan

            new_F = 0.5 * (new_fm + new_ff)
            ff_last, fm_last = new_ff, new_fm
            # v0.1.100 — not on the first pass; see
            # ``BishopSimplified._general_moment_fos``.
            if _it > 0 and abs(new_F - F) < self.tolerance:
                return new_ff, new_fm
            F = max(0.2, min(new_F, 10.0))

        return ff_last, fm_last
