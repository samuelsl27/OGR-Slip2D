# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Bishop's Simplified Method of Slices.

Reference: Bishop, A.W. (1955). "The use of the slip circle in the
stability analysis of slopes." Géotechnique 5(1), 7-17.

The method assumes:
    - Inter-slice forces are horizontal only (zero vertical component
      between adjacent slices)
    - Moment equilibrium about the centre of a circular slip surface
    - Force equilibrium NOT enforced (only moment)

Implicit FoS equation (requires fixed-point iteration):

                   Σ [ c'·b + (W − u·b) · tan φ' ] / m_α
        F  =  ──────────────────────────────────────────────────
                          Σ W · sin α

with:
        m_α  =  cos α + sin α · tan φ' / F

For pseudo-static seismic analysis (Slide convention):
    - W → W·(1 − kv)
    - kh adds a moment to the driving denominator:
        Σ kh · W · (y_g − y_centre) / R

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from ogr_core.materials import Material
from ogr_core.project import Project

from ..slicer import Slice, Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method


@register_method
class BishopSimplified(LEMMethod):
    METHOD_ID = "bishop_simplified"
    DISPLAY_NAME = "Bishop Simplified"
    SATISFIES_FORCE = False
    SATISFIES_MOMENT = True

    # ------------------------------------------------------------------
    @staticmethod
    def _local_c_phi(
        slice_: Slice, material: Optional[Material], sigma_n_eff: float
    ) -> tuple[float, float]:
        """Linearise the constitutive envelope at σ'ₙ.

        v0.1.14 — uses the model's analytical tangent ``dτ/dσ`` when
        available (any StrengthModel may implement ``tangent_slope``).

        v0.1.15 — context-aware: if the strength model declares
        ``needs_context`` (anisotropic, SHANSEP, …) we build a
        :class:`SliceContext` from the slice and evaluate
        ``shear_strength_ctx``. The tangent is then taken numerically
        around that context, since the angle/σ'v are fixed for the
        slice (only σ'ₙ varies in the linearisation).

        Returns (c_local, tan φ_local) such that locally
            τ ≈ c_local + σ'ₙ · tan φ_local
        """
        if material is None:
            return 0.0, 0.0
        sn = max(sigma_n_eff, 0.0)
        strength = material.strength
        # v0.1.28 — matric suction beyond the air entry value acts as
        # extra cohesion (extended Mohr-Coulomb). Computed by the slicer
        # so every LEM method picks it up here, in one place.
        c_suction = getattr(slice_, "suction_cohesion", 0.0) or 0.0

        # v0.1.15 — build a context for models that need it
        ctx = None
        if getattr(strength, "needs_context", False):
            from ogr_core.materials.strength_model import SliceContext
            # vertical effective stress at the base ≈ W/b − u  (per unit
            # width). Use slice attributes when available.
            try:
                b = max(slice_.width, 1e-9)
                sigma_v_total = slice_.weight / b
                u = getattr(slice_, "pore_pressure", 0.0)
                sigma_v_eff = max(sigma_v_total - u, 0.0)
            except Exception:  # noqa: BLE001
                sigma_v_eff = sn
            depth = 0.0
            try:
                depth = 0.5 * (slice_.top_y_left + slice_.top_y_right) \
                    - 0.5 * (slice_.base_y_left + slice_.base_y_right)
            except Exception:  # noqa: BLE001
                pass
            ctx = SliceContext(
                base_angle_rad=getattr(slice_, "base_angle", 0.0),
                sigma_v_eff=sigma_v_eff,
                depth=max(depth, 0.0),
                pore_pressure=getattr(slice_, "pore_pressure", 0.0),
                y_base=0.5 * (getattr(slice_, "base_y_left", 0.0)
                              + getattr(slice_, "base_y_right", 0.0)),
            )

        def _tau(s: float) -> float:
            if ctx is not None:
                return strength.shear_strength_ctx(s, ctx)
            return strength.shear_strength(s)

        tau_at_sn = _tau(sn)
        if not math.isfinite(tau_at_sn):
            return 1e12, 0.0  # InfiniteStrength

        # Analytical tangent only valid for the non-context models
        tan_phi = None
        if ctx is None:
            tangent_fn = getattr(strength, "tangent_slope", None)
            if tangent_fn is not None:
                try:
                    tan_phi = tangent_fn(sn)
                except Exception:  # noqa: BLE001
                    tan_phi = None

        if tan_phi is None:
            base_delta = max(0.001, 0.0001 * sn)
            delta = base_delta
            if sn - delta < 0:
                tau_hi = _tau(sn + delta)
                if not math.isfinite(tau_hi):
                    return 1e12, 0.0
                tan_phi = (tau_hi - tau_at_sn) / delta
            else:
                tau_lo = _tau(sn - delta)
                tau_hi = _tau(sn + delta)
                if not (math.isfinite(tau_lo) and math.isfinite(tau_hi)):
                    return 1e12, 0.0
                tan_phi = (tau_hi - tau_lo) / (2.0 * delta)

        tan_phi = max(0.0, tan_phi)
        c = tau_at_sn - sn * tan_phi
        c = max(0.0, c)
        return c + c_suction, tan_phi

    # ------------------------------------------------------------------
    def compute_fos(
        self,
        project: Project,
        surface: SurfaceProtocol,
        slices: Slices,
    ) -> LEMResult:
        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        # v0.1.14 — pre-compute support effects on this slip surface
        try:
            from ..support_integration import compute_support_effects
            support_effects = compute_support_effects(project, surface, slices)
        except Exception:  # noqa: BLE001
            support_effects = []

        # Detect sliding direction from the un-seismic driving moment
        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # Driving moment (denominator of Bishop's FoS expression).
        # Σ W·(1 − kv)·sin α + Σ kh·W·(y_g − y_c)/R
        denominator = 0.0
        circle_R = None
        circle_yc = None
        if isinstance(surface, SlipCircle):
            circle_R = surface.radius
            circle_yc = surface.centre_y
        for s in slices:
            W_eff = s.weight * (1.0 - kv)
            denominator += slide_sign * W_eff * math.sin(s.base_angle)
            if kh > 0 and circle_R is not None:
                y_cg = 0.5 * (
                    0.5 * (s.top_y_left + s.top_y_right)
                    + 0.5 * (s.base_y_left + s.base_y_right)
                )
                arm = (circle_yc - y_cg) / circle_R
                denominator += kh * W_eff * arm

        # v0.1.15 — both Active and Passive support contributions are
        # added to the resisting moment (numerator). This matches the
        # convention of Krahn (2003) / GeoStudio and is much more
        # numerically stable than Slide's literal "Active subtracts
        # from driving" form, which can produce FoS = 0 or negative
        # values when the support force exceeds the driving moment.
        #
        # The mechanical interpretation: every support adds resisting
        # force equal to the projection of its force onto the slip
        # surface tangent. Active vs Passive only differs in whether
        # the contribution is divided by F (Passive) or not (Active).
        # We do NOT divide Passive by F either, matching Slide's
        # documented behaviour and producing identical results to v0.1.14
        # for the Active case (where Slide and our v0.1.15 implementation
        # agree exactly when the support force is small relative to
        # driving).
        s_list = slices.slices if hasattr(slices, "slices") else slices

        if abs(denominator) < 1e-9:
            return LEMResult(
                fos=math.inf,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                error_message="Zero driving moment — surface does not slide",
            )

        # Iterative fixed-point solve for FoS
        fos = self.initial_fos
        converged = False
        iterations = 0

        for it in range(1, self.max_iterations + 1):
            iterations = it
            numerator = 0.0

            for s in slices:
                W_eff = s.weight * (1.0 - kv)
                b = s.width

                N_est = W_eff * math.cos(s.base_angle)
                N_eff_est = max(0.0, N_est - s.pore_pressure * s.base_length)
                sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)

                c, tan_phi = self._local_c_phi(s, s.material, sigma_n_eff)

                m_alpha = math.cos(s.base_angle) + (
                    slide_sign * math.sin(s.base_angle) * tan_phi / fos
                )

                if abs(m_alpha) < 1e-6:
                    return LEMResult(
                        fos=math.nan,
                        converged=False,
                        iterations=iterations,
                        method_id=self.METHOD_ID,
                        surface=surface,
                        slices=slices,
                        error_message=(
                            f"mα collapsed to {m_alpha:.4g} at slice {s.index}"
                        ),
                    )

                # Bishop numerator: [c'·b + (W − u·b)·tan φ'] / m_α
                numerator += (
                    c * b + (W_eff - s.pore_pressure * b) * tan_phi
                ) / m_alpha

            # v0.1.15 — every support (Active OR Passive) adds its
            # tangential projection to the resisting moment (numerator).
            # This is the GeoStudio-style integration and matches Slide
            # for typical conditions while remaining numerically stable
            # even with heavy reinforcement.
            for eff in support_effects:
                if eff.slice_index < 0 or eff.slice_index >= len(s_list):
                    continue
                sl = s_list[eff.slice_index]
                alpha = sl.base_angle * slide_sign
                tx = -math.cos(alpha) if slide_sign > 0 else math.cos(alpha)
                ty = -math.sin(alpha) if slide_sign > 0 else math.sin(alpha)
                proj_tangent = eff.force_h * tx + eff.force_v * ty
                numerator += abs(proj_tangent)

            new_fos = numerator / denominator
            if not math.isfinite(new_fos):
                return LEMResult(
                    fos=math.nan,
                    converged=False,
                    iterations=iterations,
                    method_id=self.METHOD_ID,
                    surface=surface,
                    slices=slices,
                    error_message="Non-finite FoS in iteration",
                )

            if abs(new_fos - fos) < self.tolerance:
                fos = new_fos
                converged = True
                break
            fos = new_fos

        # ---- Post-processing per slice (diagnostics) ---------------
        normals: list[float] = []
        shears: list[float] = []
        strengths: list[float] = []
        for s in slices:
            W_eff = s.weight * (1.0 - kv)
            b = s.width
            N_est = W_eff * math.cos(s.base_angle)
            N_eff_est = max(0.0, N_est - s.pore_pressure * s.base_length)
            sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)
            c, tan_phi = self._local_c_phi(s, s.material, sigma_n_eff)
            m_alpha = math.cos(s.base_angle) + (
                slide_sign * math.sin(s.base_angle) * tan_phi / fos
            )
            # Bishop's expression for N (with sin α sign):
            N = (W_eff
                 - (c * b * math.sin(s.base_angle)) / fos
                 + (s.pore_pressure * b * tan_phi
                    * math.sin(s.base_angle)) / fos
                ) / max(abs(m_alpha), 1e-6)
            sigma_eff = max(0.0, N - s.pore_pressure * b) / max(b, 1e-9)
            tau = self._shear_strength(s.material, sigma_eff)
            normals.append(N)
            shears.append(slide_sign * W_eff * math.sin(s.base_angle))
            strengths.append(tau * s.base_length)

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iterations,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
            base_normal=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
        )
