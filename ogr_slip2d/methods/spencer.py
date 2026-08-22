# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Spencer's Method of Slices.

Reference: Spencer, E. (1967). "A method of analysis of the stability
of embankments assuming parallel inter-slice forces." Géotechnique
17(1), 11-26.

Implementation follows the Fredlund-Krahn (1977) "General Limit
Equilibrium" formulation specialised to f(x) ≡ 1 (constant inter-
slice force ratio):

    Force equilibrium (horizontal direction):
                                F_f
        Σ Q_i =  0    where    Q_i = ──────────────────────────────
                                     m_α(F_f) · cos(α − θ)

        with Q_i = c'·l·cos α + (W − u·b)·tan φ' · cos α
                   − [W·sin α − kh·W·cos α] · m_α
                   − N_int_i  (inter-slice net horizontal contribution)

    Moment equilibrium about the centre of rotation:
        F_m = Σ [c'·l + (N − u·l)·tan φ'] · R
              ─────────────────────────────────
              Σ W · R · sin α  +  Σ kh·W·y_arm

    Inter-slice force ratio:
        X_i / E_i = λ        (constant for Spencer)

The simultaneous equations F_m(λ) = F_f(λ) = F yield Spencer's FoS.

Practical implementation:
    - Outer Newton iteration on λ to drive g(λ) = F_f − F_m → 0
    - Inner fixed-point iteration on F at each λ
    - For circular surfaces R cancels in F_m

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Tuple

from ogr_core.project import Project

from ..external_forces import slice_forces
from ..slicer import Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method
from .bishop import BishopSimplified


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

        # Geometry — only used for the moment expression
        circle_R = surface.radius if isinstance(surface, SlipCircle) else None
        circle_yc = surface.centre_y if isinstance(surface, SlipCircle) else None

        # v0.1.64 — supports, resolved once for every inner solve below.
        from ..support_integration import resolve_support_terms
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        # Outer loop: bracket λ (= tan θ) and use bisection / secant
        # to drive g(λ) = F_f − F_m to zero. The grid may need to reach
        # ±1.5 for some slope geometries; v0.1.74 moved it to the base
        # class so the range the user configures can clip it.
        lam_grid = self.lambda_grid()
        samples: list[Tuple[float, float, float, float]] = []  # (lam, g, ff, fm)
        for lam in lam_grid:
            ff, fm = self._inner_solve(
                slices, lam, kh, kv, slide_sign, circle_R, circle_yc, sup,
            )
            if (math.isfinite(ff) and math.isfinite(fm)
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

        if not samples:
            return LEMResult(
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="Spencer: all sampled λ diverged",
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
                ff, fm = self._inner_solve(
                    slices, lam, kh, kv, slide_sign, circle_R, circle_yc, sup,
                )
                if (math.isfinite(ff) and math.isfinite(fm)
                        and 0.05 < ff < 50 and 0.05 < fm < 50):
                    samples.append((lam, ff - fm, ff, fm))
            samples.sort(key=lambda r: r[0])
            bracket = _first_bracket(samples)

        if bracket is None:
            # No bracket → return the sample with smallest |g| (closest
            # to F_f = F_m). Often happens for very stable slopes.
            best = min(samples, key=lambda r: abs(r[1]))
            lam_star, _, ff, fm = best
            return LEMResult(
                fos=0.5 * (ff + fm),
                converged=abs(best[1]) < 0.02,
                iterations=len(samples),
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message=("Spencer: no λ-bracket; using nearest F_f≈F_m"
                               if abs(best[1]) >= 0.02 else None),
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

            ff, fm = self._inner_solve(
                slices, lam_new, kh, kv, slide_sign, circle_R, circle_yc, sup,
            )
            if not (math.isfinite(ff) and math.isfinite(fm) and ff > 0 and fm > 0):
                lam_new = 0.5 * (lam_lo + lam_hi)
                ff, fm = self._inner_solve(
                    slices, lam_new, kh, kv, slide_sign, circle_R, circle_yc, sup,
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
            # Maintain bracket
            if g_lo * g_new < 0:
                lam_hi, g_hi, ff_hi, fm_hi = lam_new, g_new, ff, fm
            else:
                lam_lo, g_lo, ff_lo, fm_lo = lam_new, g_new, ff, fm

        # Final FoS at converged λ
        ff_final, fm_final = self._inner_solve(
            slices, lam_lo, kh, kv, slide_sign, circle_R, circle_yc, sup,
        )
        if not (math.isfinite(ff_final) and math.isfinite(fm_final)):
            return LEMResult(
                fos=math.nan, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="Spencer: divergent at final λ",
            )
        return LEMResult(
            fos=0.5 * (ff_final + fm_final),
            converged=converged,
            iterations=iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            details={
                "lambda": lam_lo,
                "slide_sign": slide_sign,
                # Constant interslice ratio at every boundary (Spencer).
                "boundary_ratios": [lam_lo] * (len(slices.slices) + 1),
            },
        )

    # ==================================================================
    # Inner solver — fixed-point iteration on F at fixed λ
    # ==================================================================
    def _inner_solve(
        self, slices: Slices, lam: float,
        kh: float, kv: float, slide_sign: float,
        circle_R, circle_yc, sup=None,
    ) -> Tuple[float, float]:
        """Return (F_f, F_m) at the given inter-slice ratio λ.

        Convention: alpha_local = slide_sign * s.base_angle so that
        the up-slope side is consistently positive. The driving terms
        in the denominator are then ALWAYS positive (we slide in the
        +α_local direction).
        """
        F = max(0.5, self.initial_fos)
        s_list = slices.slices if hasattr(slices, "slices") else slices

        ff_last = math.nan
        fm_last = math.nan

        for _ in range(80):
            num_m = 0.0
            den_m = 0.0
            num_f = 0.0
            den_f = 0.0

            for i_s, s in enumerate(s_list):
                fx = slice_forces(s, kh, kv)
                # v0.1.61 — total vertical load (soil + ponded water) for
                # everything that the base normal sees.
                W_eff = fx.w_total
                H_eq = fx.h_seismic
                # External water thrust resolved along the sliding
                # direction, whose x component is −slide_sign.
                H_water = -slide_sign * fx.h_water
                # v0.1.64 — the support enters as an EXTERNAL FORCE on the
                # slice rather than as a term bolted onto the ratio. That
                # is what a method promising full equilibrium requires,
                # and it pays for itself: the vertical component joins the
                # load the base normal carries, so the friction it
                # mobilises (T_N·tanφ') falls out of the equilibrium
                # instead of having to be added by hand as in Bishop.
                H_support = 0.0
                if sup is not None and sup.present:
                    W_eff -= sup.f_v[i_s]        # f_v is +y, W is +down
                    H_support = -slide_sign * sup.f_h[i_s]
                # Flip α according to detected sliding direction so the
                # driving terms are positive. After this flip, slope
                # rises towards +x.
                alpha = slide_sign * s.base_angle
                l = s.base_length
                b = s.width
                u = s.pore_pressure

                sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / max(l, 1e-9)
                c_loc, tan_phi = BishopSimplified._local_c_phi(
                    s, s.material, sigma_est
                )

                m_alpha = math.cos(alpha) + math.sin(alpha) * tan_phi / F
                if abs(m_alpha) < 1e-6:
                    return math.nan, math.nan

                S_term = (c_loc * b + (W_eff - u * b) * tan_phi) / m_alpha

                # --- Moment equilibrium (driving = + Σ W·sin α) ----
                num_m += S_term
                den_m += W_eff * math.sin(alpha)
                if kh > 0 and circle_R is not None:
                    y_cg = 0.5 * (
                        0.5 * (s.top_y_left + s.top_y_right)
                        + 0.5 * (s.base_y_left + s.base_y_right)
                    )
                    arm = (circle_yc - y_cg) / circle_R
                    den_m += H_eq * arm
                if circle_R is not None:
                    # Moment of the horizontal water forces about the
                    # centre, normalised by R like every other term here.
                    den_m += (
                        -slide_sign
                        * fx.water_moment_about(circle_yc) / circle_R
                    )
                    if sup is not None and sup.present and sup.f_h[i_s]:
                        # Same normalised form. The VERTICAL component
                        # needs no term of its own: folded into W_eff
                        # above, it already rides the R·sin α arm.
                        den_m += (
                            -slide_sign * sup.f_h[i_s]
                            * (circle_yc - sup.y_app[i_s]) / circle_R
                        )

                # --- Force equilibrium horizontal -----------------
                # Numerator includes λ-modulation of the resultant
                num_f += S_term * math.cos(alpha)
                num_f += lam * S_term * math.sin(alpha)
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
            if abs(new_F - F) < self.tolerance:
                return new_ff, new_fm
            F = max(0.2, min(new_F, 10.0))

        return ff_last, fm_last
