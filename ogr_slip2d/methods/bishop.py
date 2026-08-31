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
                # v0.1.120 — measured by the slicer, which is the only
                # thing that knows the layer contacts and the ground
                # profile. Passed through unchanged, None included: a
                # model that needs one and is handed None must fall back,
                # not read a depth off the other field.
                layer_top_y=getattr(slice_, "layer_top_y", None),
                slope_distance=getattr(slice_, "slope_distance", None),
                # v0.1.126 — the local bedding orientation, for the three
                # anisotropic models. None when the material names no
                # anisotropic surface, and they then use the single global
                # angle they carry, exactly as before this existed.
                bedding_angle_deg=getattr(slice_, "bedding_angle_deg", None),
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
    # ------------------------------------------------------------------
    def _general_moment_fos(self, project, surface, slices, s_list,
                            kh, kv, slide_sign, sup) -> LEMResult:
        """Bishop on a surface that is not a circle: real moments about an
        axis, written as cross products by :mod:`ogr_slip2d.moment_balance`.

        Every sign in that module comes from the geometry rather than from a
        hand-derived arm, and the reason is recorded there: three earlier
        attempts at this got one wrong each time.

        v0.1.105 — two terms of this balance were wrong, and both only with
        loads the two reference surfaces do not carry, which is why v0.1.92
        published them marked "unvalidated" and nothing caught them:

        * the **horizontal water thrust had no moment at all**. On the
          non-circular surface of verification problem 42 the buoyant identity
          of Duncan and Wright (2005) — total weights plus u plus the boundary
          water forces must equal buoyant weights with no water — came out at
          −26.35 %, against −0.01 % on a circle. With the term: −0.51 %.
        * the **seismic force was applied in +x whatever the slope did**. It
          is a magnitude, so it needs the failure sense; see the module
          docstring for the mirrored-slope measurement.

        Reference for the method: Bishop (1955); the general form with a
        moment axis follows Abramson, Lee, Sharma & Boyce (2001), which the
        reference's documentation cites for the equations of every method.
        """
        from ..moment_balance import axis_for, moment_terms
        from ..support_integration import support_vertical_load

        axis = axis_for(project, surface)

        fos = max(0.05, self.initial_fos)
        converged = False
        iterations = 0
        for it in range(1, self.max_iterations + 1):
            iterations = it
            forces = []
            weights = []
            resisting = []
            normals = []
            tangential = [0.0] * len(s_list) if sup.present else None
            tangential_passive = [0.0] * len(s_list) if sup.present else None
            for i_s, s in enumerate(s_list):
                f = slice_forces(s, kh, kv)
                w = f.w_total
                alpha = slide_sign * s.base_angle
                # v0.1.137 — the support's line load joins the slice's own
                # vertical equilibrium, exactly as on the circular path and
                # as ``interslice.prepare_rows`` already did for the
                # complete-equilibrium methods. ``w`` itself stays the SOIL
                # weight: the driving moment below takes the support's
                # moment from ``sup`` and the two tangential lists, so
                # feeding it here as well would count that force twice.
                w_n = w
                if sup.present:
                    w_n += support_vertical_load(
                        sup, i_s, s.base_angle, slide_sign, fos)
                n_est = w_n * math.cos(s.base_angle)
                sigma = max(0.0, n_est - s.pore_pressure * s.base_length)
                sigma /= max(s.base_length, 1e-9)
                c, tan_phi = self._local_c_phi(s, s.material, sigma)
                m_alpha = math.cos(alpha) + math.sin(alpha) * tan_phi / fos
                if abs(m_alpha) < 1e-6:
                    return LEMResult(
                        fos=math.nan, converged=False, iterations=iterations,
                        method_id=self.METHOD_ID, surface=surface,
                        slices=slices,
                        error_message=(f"mα collapsed to {m_alpha:.4g} "
                                       f"at slice {s.index}"))
                # Q = S·F, the resisting force with the factor divided out.
                q = (c * s.width
                     + (w_n - s.pore_pressure * s.width) * tan_phi) / m_alpha
                # N from the slice's own vertical equilibrium, the same one
                # m_alpha comes from. On a circle this force points at the
                # centre and takes no moment; on a polyline it does, and the
                # reference's documentation is explicit that it accounts for
                # it ("the normal force does not pass through the center of
                # rotation").
                normal = ((w_n - (q / fos) * math.sin(alpha))
                          / max(math.cos(alpha), 1e-9))
                forces.append(f)
                weights.append(w)
                resisting.append(q)
                normals.append(normal)
                # A support's TANGENTIAL force acts along the base opposing
                # the slide — the same direction as the shear, so the same
                # sign — but Active and Passive land on OPPOSITE sides of the
                # balance, exactly as they do on the circular path.
                #
                # v0.1.115 — until then both went through ``tangential``,
                # i.e. both were treated as Active, and Bishop answered the
                # same figure for the two settings on every non-circular
                # surface. The claim that "a moment balance has one side" was
                # what justified it, and it is false: a moment balance has a
                # numerator and a denominator like any other, and the
                # reference publishes the pair for moment equilibrium
                # separately from the pair for force equilibrium.
                if tangential is not None:
                    tangential[i_s] = sup.t_active[i_s]
                    tangential_passive[i_s] = sup.t_passive[i_s]

            # v0.1.137 — ``sup`` IS passed now, and that is not a relaxation
            # of the anti-double-counting rule but what the rule asks for.
            # The support appears in this balance exactly once: its NORMAL
            # part as a force at its own application point (``sup``) and its
            # TANGENTIAL part through the two lists. What changed is that
            # ``resisting`` no longer smuggles a second copy of the normal
            # part in as a bolted-on ``T_N·tanφ'``; ``normals`` instead
            # carries the base normal at its true value, support included,
            # which is the force whose moment this axis needs. Spencer and
            # GLE have called ``moment_terms`` this way since v0.1.115.
            terms = moment_terms(
                axis, s_list, weights, resisting, normals, kh=kh, kv=kv,
                sup=sup if sup.present else None,
                tangential=tangential, tangential_passive=tangential_passive,
                forces=forces,
                couple=sup.couple if sup.present else 0.0)
            if abs(terms.driving) < 1e-9:
                return LEMResult(
                    fos=math.inf, converged=False, iterations=iterations,
                    method_id=self.METHOD_ID, surface=surface, slices=slices,
                    error_message=("Zero driving moment — surface does not "
                                   "slide"))
            new_fos = -terms.shear / terms.driving
            if not math.isfinite(new_fos) or new_fos <= 0.0:
                return LEMResult(
                    fos=math.nan, converged=False, iterations=iterations,
                    method_id=self.METHOD_ID, surface=surface, slices=slices,
                    error_message="Non-physical factor of safety")
            # v0.1.100 — never on the FIRST pass. The stopping rule is a
            # STEP between two successive iterates, and the initial guess is
            # not an iterate: comparing against it measures the distance from
            # a value chosen by the program, not the distance to a fixed
            # point. Where the map is slow near the guess the two look the
            # same and are not — on the ACADS 1(c) validation case a circle
            # daylighting at 90 deg mapped F = 1.0 to 0.995, inside the
            # model's own tolerance of 0.005, and was published as converged
            # with a factor of safety of 0.995 whose real fixed point is
            # 5.51. It then won the search, 29 % below the published value.
            #
            # The contraction argument that justifies this criterion (see
            # tests/test_convergence_tolerance_v198.py) is about ITERATES; it
            # says nothing about the first step, so the first step does not
            # get to end the iteration.
            if it > 1 and abs(new_fos - fos) < self.tolerance:
                fos = new_fos
                converged = True
                break
            fos = 0.5 * fos + 0.5 * new_fos

        return LEMResult(
            fos=fos, converged=converged, iterations=iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            details={"moment_axis": axis},
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
        from ..support_integration import (resolve_support_terms,
                                           support_vertical_load)
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        s_list = slices.slices if hasattr(slices, "slices") else slices

        # v0.1.92 — a NON-CIRCULAR surface does not get the formula below.
        #
        # ``Σ W sinα`` over ``Σ Q`` is the driving-over-resisting moment
        # ratio only because a circle's radius is the same for every slice
        # and cancels top and bottom. On a polyline every slice base has its
        # own arm, and the base normal stops pointing at the axis, so it
        # contributes a moment of its own that this form has no term for.
        # The reference's documentation is explicit that it does compute
        # that arm ("Slide2 does account for the fact that the normal force
        # does not pass through the center of rotation by calculating the
        # moment arm associated with each normal force").
        #
        # Measured on the two reference non-circular surfaces, against the
        # values the reference reports for them:
        #
        #     Ej_1    Σ W sinα form  +2.01 %      full moments  -0.01 %
        #     Ej_2    Σ W sinα form  +4.06 %      full moments  -0.14 %
        #
        # The circular path below is left untouched rather than expressed
        # through the general one, so no circle can move: the two are not
        # bit-identical anyway, because the circular formula idealises each
        # slice base as an ARC of arm R while the general one takes the
        # straight CHORD the slicer actually built. That difference is
        # O(theta^2) per slice — 0.055 to 0.067 % over these models with 25
        # slices — and it is a real modelling choice, not an error. Applying
        # the general form to circles would therefore have moved every
        # validated result by half a per mil for no gain.
        #
        # v0.1.105 — the dispatch moved UP here, ahead of the circular
        # denominator it was sitting behind. That denominator is discarded
        # for a polyline, but the two guards it feeds were not: a
        # non-circular surface could be answered "zero driving moment", or
        # marked inadmissible for support, on the strength of a number
        # nothing was going to use. Both guards belong to the circular
        # formula, and ``_general_moment_fos`` has always carried its own.
        if not isinstance(surface, SlipCircle):
            return self._general_moment_fos(
                project, surface, slices, s_list, kh, kv, slide_sign, sup)

        # Driving moment (denominator of Bishop's FoS expression).
        # Σ W·(1 − kv)·sin α + Σ kh·W·(y_g − y_c)/R
        # Only a circle reaches this point, so these are never None and
        # the terms below are never skipped. Before v0.1.105 they were
        # guarded by ``circle_R is not None`` here AND the non-circular
        # surface still ran the loop, which is how a polyline came to lose
        # its seismic and water moments without anything saying so.
        denominator = 0.0
        circle_R = surface.radius
        circle_yc = surface.centre_y
        for s in slices:
            f = slice_forces(s, kh, kv)
            # v0.1.61 — the gravity driving term uses the TOTAL vertical
            # load (soil + ponded water); both act at the slice's x, so
            # they share the moment arm R·sin α.
            # v0.1.100 — the arm of this vertical load is a GEOMETRIC
            # quantity, not the sine of the base angle; the two coincide
            # only while the base is the tangent at the slice's own x.
            # See ``Slice.weight_arm_ratio``.
            denominator += slide_sign * f.w_total * s.weight_arm_ratio
            if kh > 0:
                y_cg = 0.5 * (
                    0.5 * (s.top_y_left + s.top_y_right)
                    + 0.5 * (s.base_y_left + s.base_y_right)
                )
                arm = (circle_yc - y_cg) / circle_R
                denominator += f.h_seismic * arm
            # v0.1.61 — horizontal water forces (ponded water on the slope,
            # water in a tension crack). A force F_h at elevation y has CCW
            # moment (y_c − y)·F_h about the centre; the driving moment is
            # measured as −slide_sign·M/R in the same normalised units as
            # Σ W sin α, which is what makes the seismic term above take the
            # form it has.
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
        if sup.present and sup.couple:
            # v0.1.122 -- the couple left over when a support's resultant
            # acts somewhere other than where it crosses the surface. Same
            # normalisation as the horizontal water moment two lines up: a
            # CCW moment enters the driving side as -slide_sign*M/R.
            denominator += -slide_sign * sup.couple / circle_R

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
        # v0.1.74 — the last iterates, for the optional Steffensen
        # acceleration. Kept as a short list rather than three variables
        # so the "clear after using them" step cannot half-happen.
        history: list[float] = []

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

                # v0.1.137 — the support is a LINE LOAD on this slice, so it
                # joins the vertical equilibrium m_alpha comes from instead of
                # being bolted on outside it. See
                # ``support_integration.support_vertical_load``.
                if sup.present:
                    W_eff += support_vertical_load(
                        sup, i_s, s.base_angle, slide_sign, fos)

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

            # Passive supports add their resisting tangential component
            # to the numerator; the Active ones already came off the
            # denominator before the iteration started.
            numerator += sup.total_passive_t()

            # ``new_fos <= 0`` has to stop the iteration, not just a
            # non-finite one. The next pass computes tan(phi)/F, so a zero
            # F raises ZeroDivisionError before the m_alpha guard below can
            # ever run — that is the crash a strengthless surface used to
            # cause, and this is the backstop for any OTHER route to the
            # same place (a cancelling numerator, a negative driving term).
            # ``_general_moment_fos`` has always had this guard; the
            # circular path is the one that was missing it.
            new_fos = numerator / denominator
            if not math.isfinite(new_fos) or new_fos <= 0.0:
                finite = math.isfinite(new_fos)
                return LEMResult(
                    fos=new_fos if finite else math.nan,
                    converged=False,
                    iterations=iterations,
                    method_id=self.METHOD_ID,
                    surface=surface,
                    slices=slices,
                    error_message=(
                        f"Non-physical factor of safety {new_fos:.4g} "
                        f"in iteration" if finite
                        else "Non-finite FoS in iteration"
                    ),
                )

            # See the note in ``_general_moment_fos``: the first step is
            # measured from the initial guess, not from an iterate.
            if it > 1 and abs(new_fos - fos) < self.tolerance:
                fos = new_fos
                converged = True
                break
            fos = new_fos

            # Steffensen: extrapolate from every third iterate. The
            # convergence test above is unchanged, so the option changes
            # how fast the sequence gets there and not what it is
            # converging to.
            if self.iterate_steffensen:
                history.append(new_fos)
                if len(history) >= 3:
                    accelerated = self.aitken(*history[-3:])
                    history.clear()
                    if accelerated is not None:
                        fos = accelerated

        # ---- Post-processing per slice (diagnostics) ---------------
        normals, shears, strengths = base_forces_no_interslice_shear(
            s_list, kh, kv, slide_sign, fos)

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iterations,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
            base_normal_force=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
            details={"active_support_ratio": active_ratio},
        )


# ======================================================================
def base_forces_no_interslice_shear(
    slices,
    kh: float,
    kv: float,
    slide_sign: float,
    fos: float,
) -> tuple[list[float], list[float], list[float]]:
    """Per-slice base normal, driving shear and available strength, with X = 0.

    Not "Bishop's block", which is why it does not live inside the class:
    it is the VERTICAL equilibrium of one slice when the inter-slice shear
    is neglected, and that assumption is shared by Bishop (1955) and by
    Janbu (1954, 1973). Eliminating the mobilised base shear
    ``S = [c'*l + (N - u*l)*tan(phi')] / F`` from

        N*cos(alpha) + s*S*sin(alpha) = W

    gives the expression both methods use for the base normal:

        N = [ W - (c'*l*sin(alpha) - u*l*tan(phi')*sin(alpha)) / F ] / m_alpha
        m_alpha = cos(alpha) + s*sin(alpha)*tan(phi') / F

    ``slide_sign`` is a PARAMETER and is deliberately not recomputed here.
    Bishop takes it from ``sign(sum W*(1-kv)*sin alpha)`` and Janbu from
    ``sign(sum W_total*tan alpha)``; each has to hand over the one its own
    iteration used, because ``m_alpha`` is not symmetric in alpha and only
    means something read in the same sense of sliding (the v0.1.82
    anomaly, recorded in AGENTS.md).

    Returns ``(normals, driving_shears, strengths)``, all three FORCES in
    kN/m: the base normal N, the driving force ``s*W*sin(alpha)`` and the
    available shear resistance ``tau_f*l``.

    Known limitation, carried over unchanged from where this code used to
    live: support forces do not enter ``N``. They enter the factor of
    safety through their own terms, but the reported normal is the one the
    soil alone carries.

    References: Bishop, A.W. (1955), Geotechnique 5(1), 7-17; Janbu, N.
    (1954, 1973).
    """
    normals: list[float] = []
    shears: list[float] = []
    strengths: list[float] = []
    # v0.1.67 - this block reports what the iteration computed, so it has
    # to use the SAME load. It used to use ``s.weight``, the soil alone,
    # while the iteration uses ``w_total``, soil plus the ponded water
    # standing on the slice. With a reservoir over the slope the reported
    # base normal came out about a THIRD of the one the factor of safety
    # was built from, and that number is what the tensile-stress
    # admissibility check judges.
    #
    # Second correction in the same block: the effective normal stress on
    # the base is ``N/l - u``, with l the BASE LENGTH. It was computed as
    # ``N/b - u`` with b the slice width, which differs by a factor
    # cos alpha - and disagreed with ``checks.base_effective_stresses``,
    # which had it right. Note that the ``u*b`` inside Bishop's FoS
    # numerator is NOT the same quantity and is correct as it stands: it
    # comes from the equilibrium algebra, not from a stress definition.
    for s in slices:
        f = slice_forces(s, kh, kv)
        W_eff = f.w_total
        l = max(s.base_length, 1e-9)
        alpha = s.base_angle
        N_est = W_eff * math.cos(alpha)
        N_eff_est = max(0.0, N_est - s.pore_pressure * l)
        sigma_n_eff = N_eff_est / l
        c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma_n_eff)
        m_alpha = math.cos(alpha) + (
            slide_sign * math.sin(alpha) * tan_phi / fos
        )
        N = (W_eff
             - slide_sign * (c * l * math.sin(alpha)) / fos
             + slide_sign * (s.pore_pressure * l * tan_phi
                             * math.sin(alpha)) / fos
             ) / max(abs(m_alpha), 1e-6)
        # v0.1.96 - sigma' is reported WITH ITS SIGN, and the envelope is
        # read at that signed value. It used to be clamped at zero here,
        # and again inside ``MohrCoulomb.shear_strength``, so a base in
        # tension was published with the full cohesion:
        #
        #   Ej_2 piezometrica, dovela 25, sigma' = -11.27 kPa
        #     reference   tau = 15 + (-11.27)*tan 28 deg =  9.005 kPa
        #     clamped     tau = 15 + max(0, -11.27)*... = 15.000 kPa (+66 %)
        #
        # Only water can drive sigma' negative, which is why two dry
        # benchmarks never showed it. The FACTOR OF SAFETY does not move:
        # this runs after convergence and reports, and Bishop's numerator
        # uses ``(W - u*b)*tanphi``, which never passed through here.
        # ``checks.base_effective_stresses`` - the one the Tensile Stress
        # Check reads - has always returned sigma' signed, so the two
        # agree now instead of only one of them being right.
        #
        # The envelope is evaluated through the LINEARISATION rather than
        # through ``shear_strength`` so this stays correct for the
        # non-linear models too: for Mohr-Coulomb it is exact, and for
        # Hoek-Brown it is the tangent at the air-entry point extended
        # into tension, which is the natural reading and beats truncating.
        # Floored at zero because a negative shear STRENGTH is not a
        # physical quantity - that is what the Tensile Stress Check is for.
        sigma_eff = N / l - s.pore_pressure
        c_rep, tan_phi_rep = BishopSimplified._local_c_phi(
            s, s.material, sigma_eff)
        tau = max(0.0, c_rep + sigma_eff * tan_phi_rep)
        normals.append(N)
        shears.append(slide_sign * W_eff * math.sin(alpha))
        strengths.append(tau * l)
    return normals, shears, strengths


# ======================================================================
def driving_shear_forces(
    slices, kh: float, kv: float, slide_sign: float,
) -> list[float]:
    """``s*W_total*sin(alpha)`` on every slice base, in kN/m.

    v0.1.107 - the one meaning ``LEMResult.base_shear_force`` now carries
    in every method. It used to be this in Bishop and Ordinary and the
    MOBILISED shear in the other five that filled it, which is a factor of
    the safety factor apart and was 2.58 against 41.0 on the same slice of
    the same surface - printed under an interface row that says "Driving
    shear W*sin(alpha)". The mobilised shear is not lost: it is exactly
    ``base_shear_strength / fos``, which is what the interpretation window
    already divides for its own "Mobilised shear" row.
    """
    return [slide_sign * slice_forces(s, kh, kv).w_total * math.sin(s.base_angle)
            for s in slices]
