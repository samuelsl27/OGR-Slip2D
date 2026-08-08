# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Lowe-Karafiath Method of Slices.

Reference: Lowe, J. & Karafiath, L. (1960). "Stability of earth dams
upon drawdown." Proc. 1st Pan-American Conf. on Soil Mechanics and
Foundation Engineering, Mexico City, Vol. 2, 537-552.  See also the
review by Abramson, Lee, Sharma & Boyce (2001), "Slope Stability and
Stabilization Methods", 2nd ed., Wiley.

The Lowe-Karafiath procedure is a **force-equilibrium** method (it does
NOT satisfy moment equilibrium). Its single defining assumption is the
inclination of the inter-slice resultant at every internal boundary:

        θ_i = ½ · ( β_i + α_i )

where β_i is the inclination of the *ground surface* over the slice and
α_i is the inclination of the *slip surface* (base) of the slice. The
inter-slice force ratio is therefore prescribed directly,

        X_i / E_i = tan θ_i

with no scalar λ to iterate on. Because only force equilibrium is
enforced, the Factor of Safety follows from a single fixed-point
iteration of the horizontal force-balance equation — the same balance
used by the GLE/Spencer force side, but with the per-slice ratio fixed
to tan θ_i instead of λ·f(x).

This keeps the implementation consistent with the already-validated
force-balance machinery (see :class:`GLEMorgensternPrice`) while adding
no new numerical assumptions.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.project import Project

from ..external_forces import interslice_water_thrust, slice_forces
from ..slicer import Slices
from ..surface import SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method
from .bishop import BishopSimplified


@register_method
class LoweKarafiath(LEMMethod):
    METHOD_ID = "lowe_karafiath"
    DISPLAY_NAME = "Lowe-Karafiath"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = False

    # ------------------------------------------------------------------
    def compute_fos(
        self, project: Project, surface: SurfaceProtocol, slices: Slices,
    ) -> LEMResult:
        if not slices.slices:
            return LEMResult(
                fos=math.nan, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="No slices",
            )

        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        # Detect sliding direction from the raw driving moment so the
        # up-slope side is consistently positive (same convention as the
        # rigorous methods).
        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.61 — Lowe-Karafiath PRESCRIBES the inter-slice inclination,
        # so it cannot be fed a total inter-slice force: the water part of
        # it is horizontal and must be separated out. See
        # ``interslice_water_thrust`` for what happens otherwise.
        face_thrust = interslice_water_thrust(project, slices)

        fos, converged, iters = self._force_balance(
            slices, kh, kv, slide_sign, face_thrust,
        )

        if not (math.isfinite(fos) and fos > 0):
            return LEMResult(
                fos=math.nan, converged=False, iterations=iters,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="Lowe-Karafiath: force balance diverged",
            )

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iters,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            details={
                "boundary_ratios": self._boundary_ratios(slices),
            },
        )

    # ------------------------------------------------------------------
    def _boundary_ratios(self, slices: Slices) -> list[float]:
        """tan θ at each of the n+1 slice boundaries, in the raw frame.

        θ is defined per slice (average of ground-surface and base
        inclinations); interior boundary values average the two adjacent
        slices.
        """
        slist = slices.slices
        th = [self._interslice_tan_theta_angle(s, 1.0) for s in slist]
        out = [math.tan(th[0])]
        for i in range(len(th) - 1):
            out.append(math.tan(0.5 * (th[i] + th[i + 1])))
        out.append(math.tan(th[-1]))
        return out

    # ==================================================================
    def _z_end(self, slices_list, theta, alpha_n, kh, kv, F: float,
               h_water=None) -> float:
        """Inter-slice resultant ``Z`` left at the down-slope free end
        after marching the force-equilibrium recursion through every
        slice with the trial Factor of Safety ``F``.

        Each slice carries a resultant inter-slice force ``Z_i`` on its
        right face, inclined at the prescribed Lowe-Karafiath angle
        ``θ_i`` to the horizontal. Eliminating the base normal ``N`` and
        the mobilised shear ``S = [c·l + (N − u·l)·tanφ]/F`` from the two
        force-equilibrium equations of the slice gives the linear
        recursion

            Z_i = ( Z_{i-1}·D⁻ + const_i ) / D_i

        with
            a       = tanφ / F
            D_i     = cos(α_i − θ_i)   − a·sin(α_i − θ_i)
            D⁻      = cos(α_i − θ_{i-1}) − a·sin(α_i − θ_{i-1})
            const_i = (kh·W − k0·cosα)(cosα − a·sinα)
                      − (W + k0·sinα)(sinα + a·cosα)
            k0      = (c·l − u·l·tanφ) / F

        Both free ends require Z = 0; starting from ``Z_0 = 0`` the
        residual ``Z_n`` is driven to zero by the correct ``F``.
        """
        a_dummy = None  # noqa: F841 (documented above)
        Z = 0.0
        theta_prev = theta[0] if theta else 0.0
        if h_water is None:
            h_water = [0.0] * len(slices_list)

        for s, alpha, th, hw in zip(slices_list, alpha_n, theta, h_water):
            # v0.1.61 — the ponded water rides in the vertical term (it is
            # a load the base has to carry) and its horizontal thrust joins
            # the seismic force in the horizontal slot. This is a
            # force-equilibrium method, so the point of application does
            # not enter: only the resultant does.
            W_eff = slice_forces(s, kh, kv).w_total
            l = s.base_length
            u = s.pore_pressure

            sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / max(l, 1e-9)
            c_loc, tan_phi = BishopSimplified._local_c_phi(
                s, s.material, sigma_est
            )

            a = tan_phi / F
            ca, sa = math.cos(alpha), math.sin(alpha)
            k0 = (c_loc * l - u * l * tan_phi) / F

            D_i = math.cos(alpha - th) - a * math.sin(alpha - th)
            D_prev = math.cos(alpha - theta_prev) - a * math.sin(alpha - theta_prev)
            # Admissibility: the base term must stay positive (analogous
            # to Bishop's mα > 0). When F is small, tanφ/F grows and this
            # denominator can vanish or flip sign, producing a pole in
            # Z(F) and a *spurious* low-F root. Reject those states so the
            # only sign change left in the residual is the physical one.
            if D_i <= 1e-6 or D_prev <= 1e-6:
                return math.nan

            const_i = (
                (kh * s.weight * (1.0 - kv) + hw - k0 * ca) * (ca - a * sa)
                - (W_eff + k0 * sa) * (sa + a * ca)
            )
            Z = (Z * D_prev + const_i) / D_i
            theta_prev = th

        return Z

    # ==================================================================
    def _force_balance(
        self, slices: Slices, kh: float, kv: float, slide_sign: float,
        face_thrust=None,
    ):
        """Root-find the Factor of Safety such that the inter-slice force
        recursion closes (``Z_n = 0``).

        The recursion uses the *true* signed base angles (the slide-sign
        flip used by the moment methods would destroy the active/passive
        structure the force recursion relies on). Two marching
        orientations are tried so the method is robust to either sliding
        direction; the first that produces a sign change in the end
        residual is used.

        Returns ``(fos, converged, iterations)``.
        """
        slist = list(slices)
        if not slist:
            return math.nan, False, 0
        ft = face_thrust if face_thrust else [0.0] * (len(slist) + 1)

        grid = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        total_iters = 0
        best_fallback = None  # (|residual|, F)

        for orient in (1.0, -1.0):
            alpha_n = [orient * s.base_angle for s in slist]
            theta = [
                orient * self._interslice_tan_theta_angle(s, 1.0)
                for s in slist
            ]
            # v0.1.61 — ``orient`` mirrors the geometry in x, so a
            # horizontal force signed in the true +x direction flips with
            # it. The seismic term needs no such factor because it is
            # already expressed as a magnitude along the marching sense.
            # Each slice also receives the NET water thrust of its two
            # vertical faces: the left face pushes it towards +x, the
            # right face towards −x.
            h_water = [
                orient * (slice_forces(s, kh, kv).h_water
                          + ft[i] - ft[i + 1])
                for i, s in enumerate(slist)
            ]

            def residual(F, alpha_n=alpha_n, theta=theta, hw=h_water):
                return self._z_end(slist, theta, alpha_n, kh, kv, F,
                                   h_water=hw)

            samples = []
            for F in grid:
                r = residual(F)
                if math.isfinite(r):
                    samples.append((F, r))
            total_iters += len(samples)
            if len(samples) < 2:
                continue

            # Track a global fallback (smallest |residual|).
            F_b, r_b = min(samples, key=lambda t: abs(t[1]))
            if best_fallback is None or abs(r_b) < best_fallback[0]:
                best_fallback = (abs(r_b), F_b)

            bracket = None
            for i in range(len(samples) - 1):
                if samples[i][1] * samples[i + 1][1] < 0:
                    bracket = (samples[i], samples[i + 1])
                    break
            if bracket is None:
                continue

            (F_lo, r_lo), (F_hi, r_hi) = bracket
            F_mid = 0.5 * (F_lo + F_hi)
            converged = False
            for _ in range(max(self.max_iterations, 60)):
                total_iters += 1
                if abs(r_hi - r_lo) > 1e-15:
                    F_mid = F_hi - r_hi * (F_hi - F_lo) / (r_hi - r_lo)
                if not (min(F_lo, F_hi) <= F_mid <= max(F_lo, F_hi)):
                    F_mid = 0.5 * (F_lo + F_hi)
                r_mid = residual(F_mid)
                if not math.isfinite(r_mid):
                    F_mid = 0.5 * (F_lo + F_hi)
                    r_mid = residual(F_mid)
                    if not math.isfinite(r_mid):
                        break
                if abs(r_mid) < 1e-6 or abs(F_hi - F_lo) < self.tolerance:
                    converged = True
                    break
                if r_lo * r_mid < 0:
                    F_hi, r_hi = F_mid, r_mid
                else:
                    F_lo, r_lo = F_mid, r_mid
            return F_mid, converged, total_iters

        # No bracket in either orientation — return nearest-residual F.
        if best_fallback is not None:
            return best_fallback[1], False, total_iters
        return math.nan, False, total_iters

    # ------------------------------------------------------------------
    @staticmethod
    def _interslice_tan_theta_angle(s, slide_sign: float) -> float:
        """Lowe-Karafiath inter-slice inclination θ (radians) for slice
        ``s``: the average of the ground-surface and base inclinations,
        both in the normalised (slide-sign flipped) frame."""
        alpha = slide_sign * s.base_angle
        b = max(s.width, 1e-9)
        beta = slide_sign * math.atan2(s.top_y_right - s.top_y_left, b)
        return 0.5 * (alpha + beta)
