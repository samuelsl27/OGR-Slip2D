# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Ordinary (Fellenius / Swedish) Method of Slices.

Simplest LEM method: ignores inter-slice forces entirely. Satisfies
moment equilibrium about the centre of a circular surface only.

Formulation (circular surface):

    FS = Σ [c'·l + (W cos α − u·l·cos²α) · tan φ'] / Σ (W sin α)

where
    l   = base length of slice
    α   = base inclination (positive if rising to the right)
    W   = slice weight
    u   = pore pressure at slice base midpoint
    c'  = effective cohesion at the base
    φ'  = effective friction angle at the base

Non-iterative → always returns converged=True.

The pore-pressure term uses the vertical projection of the base,
u·l·cos²α, which is the correction of Turnbull & Hvorslev (1967); with
u·l instead, the method disagrees with the reference by −24.7 % on the
Ej_2 piezometric benchmark and by nothing at all on a dry model.

Reference: Fellenius (1927); Turnbull, W.J. & Hvorslev, M.J. (1967),
"Special problems in slope stability", ASCE JSMFD 93(SM4), 499-528.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.project import Project

from ..external_forces import slice_forces
from ..slicer import Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method


@register_method
class OrdinaryFellenius(LEMMethod):
    METHOD_ID = "ordinary_fellenius"
    DISPLAY_NAME = "Ordinary / Fellenius"
    SATISFIES_FORCE = False
    SATISFIES_MOMENT = True

    def compute_fos(
        self,
        project: Project,
        surface: SurfaceProtocol,
        slices: Slices,
    ) -> LEMResult:
        # A surface with no shear strength anywhere has F = 0 exactly and
        # no iteration to run; see LEMMethod.NO_SHEAR_STRENGTH_NOTE for why
        # this is answered here rather than left to the arithmetic.
        strengthless = self._no_shear_strength_result(surface, slices)
        if strengthless is not None:
            return strengthless

        numerator = 0.0
        denominator = 0.0

        normals: list[float] = []
        shears: list[float] = []
        strengths: list[float] = []
        n_negative_normal = 0

        # Optional seismic load
        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        # Determine sliding direction from the un-seismic driving moment
        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.64 — supports reach every method now, not only Bishop. The
        # sliding sense has to be known first, because the resisting
        # tangential component is defined against it.
        from ..support_integration import resolve_support_terms
        from .bishop import BishopSimplified as _B
        sup = resolve_support_terms(project, surface, slices, slide_sign)
        s_list = slices.slices if hasattr(slices, "slices") else slices

        # v0.1.61 — the horizontal water forces act on the TOP of the
        # slice, not on its base, so they enter the driving side through
        # their MOMENT about the centre of rotation — the same normalised
        # form Bishop uses — and not as a tangential component at the base.
        # Ordinary/Fellenius is a moment method, so R cancels here too.
        circle_R = surface.radius if isinstance(surface, SlipCircle) else None
        circle_yc = (surface.centre_y
                     if isinstance(surface, SlipCircle) else None)

        for i_s, s in enumerate(s_list):
            f = slice_forces(s, kh, kv)
            W = f.w_total
            H = s.weight * kh * slide_sign
            # A horizontal force resolved on the base: the inward normal
            # is (−sin α, cos α), so it adds ``+F_h·sin α`` to the base
            # reaction.
            Hw = f.h_water
            # Base-normal effective stress
            N = (W * math.cos(s.base_angle)
                 - H * math.sin(s.base_angle)
                 + Hw * math.sin(s.base_angle))
            # v0.1.94 — the pore-pressure force is taken over the base's
            # VERTICAL PROJECTION, u·l·cos²α, and not over the whole base
            # length. This is the correction of Turnbull & Hvorslev (1967)
            # — Lambe & Whitman (1969) call it the Ordinary method with
            # corrected pore pressure — and it is what the reference
            # implements. Measured against its published slice table on the
            # Ej_2 piezometric model, u·l·cos²α reproduces the effective
            # normal stress of the 22 slices carrying water to within
            # 0.03 %, while u·l is out by up to 118 %.
            #
            # The two forms are IDENTICAL when u = 0, which is why eighty
            # versions of dry reference models never saw this: the whole
            # error is proportional to u·(1 − cos²α), so it needs both water
            # AND an inclined base to exist at all. On that circle it cost
            # −24.7 % on the factor of safety.
            cos_a = math.cos(s.base_angle)
            N_eff = N - s.pore_pressure * s.base_length * cos_a * cos_a
            # v0.1.62 — count the slices whose effective normal force comes
            # out negative.
            #
            # v0.1.94 — and the explanation that stood here was WRONG, which
            # is the part worth keeping written down. It called this "THE
            # failure mode of the method, not of this implementation",
            # citing Whitman and Bailey (1967) and their errors of up to
            # 60 %. On the Ej_2 piezometric circle it was 5 slices of 25,
            # with σ' down to −7.3 kPa; with the correction above, NOT ONE
            # of the 25 comes out negative. The negative normals were made
            # by the uncorrected water term, and a citation was covering
            # for them.
            if N_eff < 0.0:
                n_negative_normal += 1
            sigma_n_eff = max(0.0, N_eff) / max(s.base_length, 1e-9)

            tau = self._shear_strength(s.material, sigma_n_eff)
            strength = tau * s.base_length

            driving = (
                slide_sign * W * math.sin(s.base_angle)
                + H * math.cos(s.base_angle)
            )
            if circle_R is not None:
                driving += (
                    -slide_sign * f.water_moment_about(circle_yc) / circle_R
                )

            # v0.1.64 — frictional resistance mobilised by the support's
            # NORMAL component, T_N·tanφ'. Ordinary resolves everything on
            # the base already, so it lands naturally here.
            if sup.present and sup.n_press[i_s]:
                _c, tan_phi = _B._local_c_phi(s, s.material, sigma_n_eff)
                strength += sup.n_press[i_s] * tan_phi

            numerator += strength
            denominator += driving

            normals.append(N)
            shears.append(driving)
            strengths.append(strength)

        # Reference formulation, as for every other method:
        #     F_act = (R + T_N·tanφ') / (D − T_S)
        #     F_pas = (R + T_N·tanφ' + T_S) / D
        numerator += sup.total_passive_t()
        driving_no_support = denominator
        denominator -= sup.total_active_t()
        active_ratio = (
            sup.total_active_t() / driving_no_support
            if sup.present and abs(driving_no_support) > 1e-9 else 0.0
        )
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

        fos = numerator / denominator
        return LEMResult(
            fos=fos,
            converged=True,
            iterations=1,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
            base_normal=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
            details={
                "negative_effective_normal": n_negative_normal,
                "num_slices": len(normals),
                "active_support_ratio": active_ratio,
            },
        )
