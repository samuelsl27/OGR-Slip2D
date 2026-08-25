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

    # ------------------------------------------------------------------
    def _general_moment_fos(self, project, surface, slices, s_list,
                            kh, kv, slide_sign, sup) -> LEMResult:
        """Fellenius on a surface that is not a circle.

        The cleanest of the four general paths, and the reason is the method's
        own defining assumption: Fellenius ignores the forces between slices
        entirely, so the base normal is simply the projection of the slice's
        EXTERNAL forces onto the base normal, with nothing implicit in it and
        no dependence on the factor of safety. There is no iteration either —
        the factor is a plain ratio of moments.

        That is also why it lands where the more elaborate methods do not.
        Against the two non-circular surfaces the reference program reports:

            Ej_1   published 0.897423    Σ W sinα form 0.891561    here 0.897423
            Ej_2   published 1.369210    Σ W sinα form 1.378300    here 1.369209

        Reference: Fellenius (1927); pore-pressure correction of Turnbull &
        Hvorslev (1967); the general form with a moment axis follows Abramson,
        Lee, Sharma & Boyce (2001).
        """
        from ..moment_balance import (axis_for, base_frame, moment_terms,
                                      rotation_sense)
        from .bishop import BishopSimplified as _B

        axis = axis_for(project, surface)
        forces = [slice_forces(s, kh, kv) for s in s_list]
        weights = [f.w_total for f in forces]
        # The rotation has to be known BEFORE the normals: the seismic force
        # is a magnitude and has to be pointed the right way first.
        rot = rotation_sense(axis, s_list, weights)

        ox, oy = axis
        normals: list[float] = []
        resisting: list[float] = []
        driving_forces: list[float] = []
        tangential = [0.0] * len(s_list) if sup.present else None
        tangential_passive = [0.0] * len(s_list) if sup.present else None
        n_negative_normal = 0
        for i, s in enumerate(s_list):
            f = forces[i]
            xm, ym, tx, ty, nx, ny = base_frame(axis, s)
            # N = −(sum of external forces)·n̂, the Fellenius normal.
            fx = rot * f.h_seismic + f.h_water
            fy = -f.w_total
            # v0.1.115 — the support does NOT enter here, and until then it
            # did, WHOLE. Two things were wrong with that. Its normal part
            # landed inside ``N``, so the frictional resistance it mobilises
            # was already in ``strength`` below — and then ``T_N·tan φ'`` was
            # added a SECOND time a few lines down. Measured on a nail
            # perpendicular to a horizontal pile (T_N = −9.0 kN/m lifting,
            # tan φ' = 0.364) the polyline sampled from a circle answered
            # 1.530128 where the circle itself gave 1.552546, a −1.44 % gap
            # against the +0.14 % the same two paths differ by with no
            # support at all. And the CIRCULAR path of this same method has
            # never put the support in ``N``: it adds ``T_N·tan φ'`` to the
            # strength and nothing else. Two paths of one method disagreeing
            # about a free body is the defect, whichever of them is nicer.
            N = -(fx * nx + fy * ny)
            # The DOWNSLOPE tangent, for the reported driving force: the base
            # moves with the rotation, and the shear opposes that motion, so
            # downslope is the direction of the motion itself. Same rule as
            # ``moment_terms``; kept here because ``base_shear_force`` in a
            # LEMResult is defined as the driving force on the slice — the
            # circular path reports W·sin α — and it is a FORCE, so a moment
            # cannot be put in its place.
            vx, vy = -rot * (ym - oy), rot * (xm - ox)
            down = 1.0 if (vx * tx + vy * ty) >= 0.0 else -1.0
            driving_forces.append(down * (fx * tx + fy * ty))
            # The pore-pressure force over the base's VERTICAL PROJECTION,
            # u·l·cos²α — Turnbull & Hvorslev (1967). Same term as the
            # circular path; see the note there for what it cost to omit.
            cos_a = math.cos(s.base_angle)
            N_eff = N - s.pore_pressure * s.base_length * cos_a * cos_a
            if N_eff < 0.0:
                n_negative_normal += 1
            sigma_n_eff = max(0.0, N_eff) / max(s.base_length, 1e-9)
            # v0.1.120 — through ``_local_c_phi``, like the other eight
            # methods. It used to be ``self._shear_strength``, which asked
            # the model for tau WITHOUT a SliceContext: Ordinary was the
            # only method that did, and so the only one that ignored
            # SHANSEP, the four anisotropic models, the three depth
            # profiles and the matric-suction cohesion. See the note in
            # the circular path for the measurement.
            c_loc, tan_phi = _B._local_c_phi(s, s.material, sigma_n_eff)
            strength = (c_loc + sigma_n_eff * tan_phi) * s.base_length
            if sup.present:
                if sup.n_press[i]:
                    strength += sup.n_press[i] * tan_phi
                # Its own branch: a support can be purely tangential to the
                # base, and then ``n_press`` is zero while the force that
                # actually holds the slice back is not.
                #
                # v0.1.115 — split by Active/Passive, which is the whole of
                # the anomaly: until then the SUM went to the driving side,
                # so this path answered the same figure for both settings.
                tangential[i] = sup.t_active[i]
                tangential_passive[i] = sup.t_passive[i]
            normals.append(N)
            resisting.append(strength)

        # ``sup`` is not passed: like Bishop, this path splits the support
        # into a normal part (inside ``resisting``) and a tangential one
        # (``tangential``), which is the same split the circular path makes.
        terms = moment_terms(axis, s_list, weights, resisting, normals,
                             kh=kh, kv=kv, tangential=tangential,
                             tangential_passive=tangential_passive,
                             rotation=rot, forces=forces,
                             couple=sup.couple if sup.present else 0.0)
        if abs(terms.driving) < 1e-9:
            return LEMResult(
                fos=math.inf, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="Zero driving moment — surface does not slide",
            )
        fos = -terms.shear / terms.driving
        if not math.isfinite(fos) or fos <= 0.0:
            return LEMResult(
                fos=fos if math.isfinite(fos) else math.nan,
                converged=False, iterations=0, method_id=self.METHOD_ID,
                surface=surface, slices=slices,
                error_message="Non-physical factor of safety",
            )
        return LEMResult(
            fos=fos, converged=True, iterations=1,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=normals,
            base_shear_force=driving_forces,
            base_shear_strength=resisting,
            details={
                "negative_effective_normal": n_negative_normal,
                "num_slices": len(normals),
                "moment_axis": terms.axis,
            },
        )

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
        from ..moment_balance import slice_cg_y
        from ..support_integration import resolve_support_terms
        from .bishop import BishopSimplified as _B
        sup = resolve_support_terms(project, surface, slices, slide_sign)
        s_list = slices.slices if hasattr(slices, "slices") else slices

        # v0.1.105 — a surface with no centre gets a real moment balance
        # about the axis instead, exactly as Bishop has since v0.1.92. Until
        # now this method ran the circular formula on a polyline with
        # ``circle_R`` left at None, which silently deleted the water term
        # below and gave the weight ``sin α`` for a moment arm.
        if not isinstance(surface, SlipCircle):
            return self._general_moment_fos(
                project, surface, slices, s_list, kh, kv, slide_sign, sup)

        # v0.1.61 — the horizontal water forces act on the TOP of the
        # slice, not on its base, so they enter the driving side through
        # their MOMENT about the centre of rotation — the same normalised
        # form Bishop uses — and not as a tangential component at the base.
        # Ordinary/Fellenius is a moment method, so R cancels here too.
        circle_R = surface.radius
        circle_yc = surface.centre_y

        for i_s, s in enumerate(s_list):
            f = slice_forces(s, kh, kv)
            W = f.w_total
            # v0.1.105 — ``f.h_seismic`` rather than ``s.weight · kh``: the
            # inertial force is proportional to the weight AFTER the vertical
            # coefficient, ``kh·W·(1 − kv)``, which is what every other method
            # in this project uses and what the pseudo-static formulation
            # says. With kv = 0 — every seismic model in the benchmark — the
            # two are the same number, which is why it went unnoticed.
            H = f.h_seismic * slide_sign
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

            # v0.1.120 — ORDINARY READS THE ENVELOPE THROUGH THE SAME
            # LINEARISATION AS EVERY OTHER METHOD.
            #
            # This was ``self._shear_strength(s.material, sigma_n_eff)``,
            # which calls ``shear_strength`` with no SliceContext. Eight of
            # the registered models need one — SHANSEP, the four
            # anisotropic ones and the three depth profiles of v0.1.120 —
            # and every one of them answers its no-context fallback
            # instead: SHANSEP takes sigma'v = sigma'n, the anisotropic
            # ones take their weakest direction, and a depth profile takes
            # the value at its own reference elevation. The suction
            # cohesion, which ``_local_c_phi`` adds, was not seen either,
            # against what the v0.1.28 changelog claims about "the seven
            # methods".
            #
            # Measured on one circle of a homogeneous slope, 50 slices,
            # against Bishop on the same circle:
            #
            #     mohr_coulomb (the control)          -11.1 %
            #     shansep                             -22.3 %
            #     anisotropic_linear                  -55.6 %
            #     undrained_depth_datum               -67.8 %
            #
            # Fellenius is the conservative member of the family, and the
            # control says by how much. What exceeded it was the strength
            # law going unread. It surfaced when verification problem 23
            # stopped approximating its depth profile with four bands:
            # Fellenius fell from 1.3674 to 1.1710 against a published
            # 1.370 while Bishop moved 0.3 %, because the bands were plain
            # ``undrained`` and needed no context.
            c_loc, tan_phi = _B._local_c_phi(s, s.material, sigma_n_eff)
            tau = c_loc + sigma_n_eff * tan_phi
            strength = tau * s.base_length

            # v0.1.105 — the seismic term was ``H·cos α``, and it was wrong
            # twice over.
            #
            # THE SIGN. ``H`` carries ``slide_sign``, so on a slope descending
            # to the RIGHT — where ``slide_sign`` is −1 — that term SUBTRACTED
            # from the driving moment and the factor of safety GREW with the
            # earthquake. Homogeneous dry slope, one circle, on the CIRCULAR
            # path:
            #
            #     descending right    kh 0 → 0.10 → 0.20   1.46817  1.89347  2.74151
            #     mirrored            kh 0 → 0.10 → 0.20   1.46817  1.13791  0.91751
            #
            # Nothing caught it because no test in this suite checked the
            # seismic term numerically, and the three benchmark problems that
            # carry an earthquake all descend to the left, where the sign is
            # right by accident. ``H`` keeps its sign in ``N`` above, where it
            # belongs: there the force is resolved, not measured.
            #
            # THE FORM. ``cos α`` is the projection of a horizontal force on
            # the base, not a moment arm. Every other term of this driving sum
            # is a moment divided by R — the weight's, the water's — and the
            # same force in Bishop takes the arm ``(y_c − y_g)/R``. It does
            # here now, which is also what lets a polyline and the arc it was
            # sampled from give the same answer under an earthquake.
            driving = (
                # v0.1.100 — geometric moment arm, see
                # ``Slice.weight_arm_ratio``.
                slide_sign * W * s.weight_arm_ratio
                + f.h_seismic * (circle_yc - slice_cg_y(s)) / circle_R
                - slide_sign * f.water_moment_about(circle_yc) / circle_R
            )

            # v0.1.64 — frictional resistance mobilised by the support's
            # NORMAL component, T_N·tanφ'. Ordinary resolves everything on
            # the base already, so it lands naturally here.
            if sup.present and sup.n_press[i_s]:
                strength += sup.n_press[i_s] * tan_phi

            numerator += strength
            denominator += driving

            normals.append(N)
            shears.append(driving)
            strengths.append(strength)

        # Reference formulation, as for every other method:
        #     F_act = (R + T_N·tanφ') / (D − T_S)
        #     F_pas = (R + T_N·tanφ' + T_S) / D
        if sup.present and sup.couple:
            # v0.1.122 -- the couple left over when a support's resultant
            # acts somewhere other than where it crosses the surface. Same
            # normalisation as the horizontal water moment two lines up: a
            # CCW moment enters the driving side as -slide_sign*M/R.
            denominator += -slide_sign * sup.couple / circle_R

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
            base_normal_force=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
            details={
                "negative_effective_normal": n_negative_normal,
                "num_slices": len(normals),
                "active_support_ratio": active_ratio,
            },
        )
