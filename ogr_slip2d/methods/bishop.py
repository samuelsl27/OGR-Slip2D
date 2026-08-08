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

from ..external_forces import slice_forces
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

        # Detect sliding direction from the un-seismic driving moment
        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.64 — support terms, resolved with their SIGNS. The sliding
        # sense has to be known first, which is why this moved below the
        # detection above.
        from ..support_integration import resolve_support_terms
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        # Driving moment (denominator of Bishop's FoS expression).
        # Σ W·(1 − kv)·sin α + Σ kh·W·(y_g − y_c)/R
        denominator = 0.0
        circle_R = None
        circle_yc = None
        if isinstance(surface, SlipCircle):
            circle_R = surface.radius
            circle_yc = surface.centre_y
        for s in slices:
            f = slice_forces(s, kh, kv)
            # v0.1.61 — the gravity driving term uses the TOTAL vertical
            # load (soil + ponded water); both act at the slice's x, so
            # they share the moment arm R·sin α.
            denominator += slide_sign * f.w_total * math.sin(s.base_angle)
            if kh > 0 and circle_R is not None:
                y_cg = 0.5 * (
                    0.5 * (s.top_y_left + s.top_y_right)
                    + 0.5 * (s.base_y_left + s.base_y_right)
                )
                arm = (circle_yc - y_cg) / circle_R
                denominator += f.h_seismic * arm
            if circle_R is not None:
                # v0.1.61 — horizontal water forces (ponded water on the
                # slope, water in a tension crack). A force F_h at
                # elevation y has CCW moment (y_c − y)·F_h about the
                # centre; the driving moment is measured as −slide_sign·M/R
                # in the same normalised units as Σ W sin α, which is what
                # makes the seismic term above take the form it has.
                denominator += (
                    -slide_sign * f.water_moment_about(circle_yc) / circle_R
                )

        # v0.1.64 — Active supports subtract their resisting tangential
        # component from the DRIVING side, per the reference:
        #     F_act = (R + T_N·tanφ') / (D − T_S)
        #     F_pas = (R + T_N·tanφ' + T_S) / D
        # This replaces the v0.1.15 convention, which added abs(T_S) to
        # the numerator for both kinds. That was numerically stable but
        # it made the factor of safety symmetric under a 180° flip of the
        # support: a bolt pushing the mass downhill improved it by exactly
        # as much as one holding it back. The instability it was avoiding
        # is real, and is handled below by marking the surface
        # INADMISSIBLE rather than by discarding the sign.
        s_list = slices.slices if hasattr(slices, "slices") else slices
        driving_no_support = denominator
        denominator -= sup.total_active_t()
        # How much of the driving moment the Active supports have taken
        # away. Reported rather than judged: as T_S approaches D the
        # factor of safety grows without bound, which is arithmetically
        # right and physically meaningless, and no threshold separating
        # the two is defensible enough to hard-code.
        active_ratio = (
            sup.total_active_t() / driving_no_support
            if sup.present and abs(driving_no_support) > 1e-9 else 0.0
        )

        # The guard v0.1.15 worried about, made explicit. Reusing the
        # admissibility channel of v0.1.32 keeps the surface in the
        # evaluation list — search algorithms need the feedback — while
        # excluding it from the choice of critical surface.
        if sup.present and denominator <= 0.0:
            return LEMResult(
                fos=math.inf,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                admissible=False,
                admissibility_note=(
                    "Active support force exceeds the driving moment; "
                    "the factor of safety is undefined for this surface"
                ),
            )

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

            for i_s, s in enumerate(s_list):
                # v0.1.61 — the base normal follows from the VERTICAL
                # equilibrium of the slice, so it carries the ponded-water
                # weight but not the horizontal thrust, exactly as the
                # horizontal seismic force is absent from this side too.
                W_eff = slice_forces(s, kh, kv).w_total
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

                # v0.1.64 — frictional resistance mobilised by the NORMAL
                # component of the support, T_N·tanφ'. Added outside the
                # m_α normalisation, as the reference writes it: m_α comes
                # from solving the slice's vertical equilibrium for N under
                # its own weight, whereas the reference treats the support
                # as a force applied directly to the base. Folding it into
                # the vertical equilibrium instead would divide this term
                # by m_α too; the difference is second-order for the usual
                # near-horizontal bases, but it is a modelling choice and
                # not a detail, so it is written down here.
                if sup.present and sup.n_press[i_s]:
                    numerator += sup.n_press[i_s] * tan_phi

            # Passive supports add their resisting tangential component
            # to the numerator; the Active ones already came off the
            # denominator before the iteration started.
            numerator += sup.total_passive_t()

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
        # v0.1.67 — this block reports what the iteration computed, so it
        # has to use the SAME load. Until now it used ``s.weight``, the
        # soil alone, while the iteration above uses ``w_total``, soil
        # plus the ponded water standing on the slice. With a reservoir
        # over the slope the reported base normal came out about a THIRD
        # of the one the factor of safety was built from, and that number
        # is what the tensile-stress admissibility check judges.
        #
        # Second correction in the same block: the effective normal stress
        # on the base is ``N/l − u``, with l the BASE LENGTH. It was
        # computed as ``N/b − u`` with b the slice width, which differs by
        # a factor cos α — and disagreed with ``checks.base_effective_
        # stresses``, which had it right. Note that the ``u·b`` inside
        # Bishop's FoS numerator is NOT the same quantity and is correct
        # as it stands: it comes from the equilibrium algebra, not from a
        # stress definition.
        for s in slices:
            f = slice_forces(s, kh, kv)
            W_eff = f.w_total
            l = max(s.base_length, 1e-9)
            alpha = s.base_angle
            N_est = W_eff * math.cos(alpha)
            N_eff_est = max(0.0, N_est - s.pore_pressure * l)
            sigma_n_eff = N_eff_est / l
            c, tan_phi = self._local_c_phi(s, s.material, sigma_n_eff)
            m_alpha = math.cos(alpha) + (
                slide_sign * math.sin(alpha) * tan_phi / fos
            )
            # Bishop's expression for N, rearranged from the vertical
            # equilibrium of the slice:
            #     N·cos α + slide_sign·S·sin α = W
            # with S = [c·l + (N − u·l)·tan φ] / F the mobilised base
            # shear. A test pins that identity on the values reported.
            N = (W_eff
                 - slide_sign * (c * l * math.sin(alpha)) / fos
                 + slide_sign * (s.pore_pressure * l * tan_phi
                                 * math.sin(alpha)) / fos
                 ) / max(abs(m_alpha), 1e-6)
            sigma_eff = max(0.0, N / l - s.pore_pressure)
            tau = self._shear_strength(s.material, sigma_eff)
            normals.append(N)
            shears.append(slide_sign * W_eff * math.sin(alpha))
            strengths.append(tau * l)

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
            details={"active_support_ratio": active_ratio},
        )
