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
    ) -> None:
        super().__init__(tolerance, max_iterations, initial_fos)
        self.f_func = interslice_func

    def compute_fos(self, project: Project, surface, slices) -> LEMResult:
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

        x0 = slices.slices[0].base_x_left
        x1 = slices.slices[-1].base_x_right

        # Outer: bracket and refine λ. Wider grid for difficult slopes.
        lam_grid = [-1.5, -1.0, -0.6, -0.4, -0.2, -0.1, 0.0,
                    0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5]
        samples: list[Tuple[float, float, float, float]] = []
        for lam in lam_grid:
            ff, fm = self._inner_solve(
                slices, lam, kh, kv, slide_sign,
                circle_R, circle_yc, x0, x1,
            )
            if (math.isfinite(ff) and math.isfinite(fm)
                    and 0.05 < ff < 50 and 0.05 < fm < 50):
                samples.append((lam, ff - fm, ff, fm))

        if not samples:
            return LEMResult(
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="GLE: all sampled λ diverged",
            )

        bracket = None
        for i in range(len(samples) - 1):
            if samples[i][1] * samples[i + 1][1] < 0:
                bracket = (samples[i], samples[i + 1])
                break

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
                circle_R, circle_yc, x0, x1,
            )
            if not (math.isfinite(ff) and math.isfinite(fm) and ff > 0 and fm > 0):
                lam_new = 0.5 * (lam_lo + lam_hi)
                ff, fm = self._inner_solve(
                    slices, lam_new, kh, kv, slide_sign,
                    circle_R, circle_yc, x0, x1,
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
            circle_R, circle_yc, x0, x1,
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
        circle_R, circle_yc, x0: float, x1: float,
    ) -> Tuple[float, float]:
        F = max(0.5, self.initial_fos)
        ff_last = math.nan
        fm_last = math.nan

        for _ in range(80):
            num_m = 0.0
            den_m = 0.0
            num_f = 0.0
            den_f = 0.0

            for s in slices:
                W_eff = s.weight * (1.0 - kv)
                H_eq = kh * W_eff
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
                den_m += W_eff * math.sin(alpha)
                if kh > 0 and circle_R is not None:
                    y_cg = 0.5 * (
                        0.5 * (s.top_y_left + s.top_y_right)
                        + 0.5 * (s.base_y_left + s.base_y_right)
                    )
                    arm = (circle_yc - y_cg) / circle_R
                    den_m += kh * W_eff * arm

                # Force side: λ·f_i modulates the numerator
                num_f += S_term * math.cos(alpha)
                num_f += lam_i * S_term * math.sin(alpha)
                den_f += W_eff * math.tan(alpha) + H_eq

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
            if abs(new_F - F) < self.tolerance:
                return new_ff, new_fm
            F = max(0.2, min(new_F, 10.0))

        return ff_last, fm_last
