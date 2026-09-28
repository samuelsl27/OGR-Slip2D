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

For pseudo-static seismic analysis, both inertial forces on the static
weight (Terzaghi 1950; Kramer 1996), with ``kv`` positive DOWN:
    - W → W·(1 + kv)
    - kh adds a moment to the driving denominator:
        Σ kh · W · (y_centre − y_g) / R
    (``external_forces.slice_forces`` applies both; see its module
    docstring for the convention and for what it replaced in v0.1.214.)

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from ogr_core.materials import Material
from ogr_core.project import Project

from ..external_forces import seismic_soil_weight, slice_forces
from ..slicer import Slice, Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import (
    REASON_ACTIVE_SUPPORT_EXCEEDS_DRIVING,
    REASON_M_ALPHA_COLLAPSED,
    REASON_NON_PHYSICAL_FOS,
    REASON_NOT_CONVERGED,
    REASON_ZERO_DRIVING,
    LEMMethod,
    LEMResult,
    register_method,
    self_consistent_envelope,
)


@register_method
class BishopSimplified(LEMMethod):
    METHOD_ID = "bishop_simplified"
    DISPLAY_NAME = "Bishop Simplified"
    SATISFIES_FORCE = False
    SATISFIES_MOMENT = True

    # ------------------------------------------------------------------
    @staticmethod
    def _local_c_phi(
        slice_: Slice, material: Optional[Material], sigma_n_eff: float,
        sigma_v_probe: Optional[float] = None,
    ) -> tuple[float, float]:
        """Linearise the constitutive envelope at σ'ₙ.

        ``sigma_v_probe`` replaces the slice's own vertical effective stress
        in the context, and is for :meth:`_zero_strength` alone (v0.1.218,
        D207): it asks whether a model that reads σ'v has strength at SOME
        stress, which varying σ'ₙ cannot tell. Every solver leaves it None.

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

        v0.1.213 (D84) — WHERE the callers linearise. This function takes
        whatever stress it is given; the methods used to give it the
        Fellenius estimate ``max(0, W cos a - u l) / l`` once per slice, and
        applied the resulting straight line to the stress their own
        equilibrium resolved. For a curved envelope that is not the
        envelope: a tangent taken elsewhere lies above a concave curve, and
        one taken at a clipped zero on a curve through the origin is zero.
        Since v0.1.213 a stress-dependent envelope is read at the stress the
        method resolves, iterated to the fixed point
        (``base.self_consistent_envelope``); the Fellenius estimate is only
        the first pass.

        The case that settled it was misread for five versions. Perry
        (1993), the given five-slice surface of verification problem 40, is
        published at 0.944 (Janbu simplified) in the verification manual and
        0.98 in Perry's own paper:

            linearised at          Fellenius    own stress
            5 slices (the statement) 0.97388      0.94889
            100 slices               0.95454      0.92947

        Measured in v0.1.153, the 100-slice figures were set against the
        five-slice publication and read as "re-linearising is worse on Perry
        1993". At the discretisation the number was published for, the own
        stress is +0.52 % from the manual and the Fellenius point +3.17 %;
        against Perry's own 0.98 the order reverses (-3.17 % and -0.62 %),
        and that paper was not available to say how it read the envelope.
        What decided was the identity, not the fit: the strength the solver
        used against the envelope at the stress of its own solution was off
        by +2.0 to +2.2 % in the sum on that surface, and by -21 % on the
        critical surface of problem 41 (Jiang, Baker & Yamagami 2003), where
        four slices entered with nothing; at the fixed point it is exact.
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
            # vertical effective stress at the base ≈ (W + W_w)/b − u (per
            # unit width). Use slice attributes when available.
            #
            # v0.1.214 (D166) -- ``+ water_weight``, the ponded water
            # standing on the slice, which the slicer keeps out of
            # ``weight`` so the seismic coefficients cannot reach it. The
            # pore pressure at the base carries the head of that water, so
            # without its weight the estimate fell by ``γ_w·d`` under a
            # reservoir and was clipped to zero -- and SHANSEP, the model
            # that reads it, then fell back to ``su(σ'_n)`` in silence. With
            # it, a submerged column gives ``γ'·h`` whatever the depth of the
            # water: Terzaghi's principle, and the sum the reference
            # documentation writes for its own excess-pore-pressure example.
            # NO seismic coefficient here: this is the consolidation stress
            # a strength model reads, not a load the earthquake applies.
            # By ``getattr`` because ``ogr_core.support.bond`` hands in a
            # stand-in with no water field.
            try:
                b = max(slice_.width, 1e-9)
                sigma_v_total = (slice_.weight
                                 + getattr(slice_, "water_weight", 0.0)) / b
                u = getattr(slice_, "pore_pressure", 0.0)
                sigma_v_eff = max(sigma_v_total - u, 0.0)
            except Exception:  # noqa: BLE001
                sigma_v_eff = sn
            if sigma_v_probe is not None:
                sigma_v_eff = max(float(sigma_v_probe), 0.0)
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
    #: The two stresses [kPa] at which an envelope is asked whether it has
    #: any strength at all (:meth:`_zero_strength`). Two, because one point
    #: can sit on a flat stretch of a user-defined function.
    _STRENGTH_PROBES = (1.0, 100.0)

    @staticmethod
    def _zero_strength(slice_: Slice, raw_estimate: float, c: float,
                       tan_phi: float) -> bool:
        """True when the slice enters its solver with NO shear strength
        because the stress its envelope was read at is negative (v0.1.213,
        D84).

        Every method reads the envelope once per slice at an effective
        normal stress and clips a negative one to zero (see the docstring of
        :meth:`_local_c_phi`). With Mohr-Coulomb that is harmless, since c'
        and tan(phi') do not depend on the point. With a curve through the
        origin, a power curve with ``c = d = 0``, the tangent at zero is
        zero and the slice resists nothing. On a first pass that stress is
        the Fellenius estimate, which can be negative where the solution is
        not; on the passes of ``base.self_consistent_envelope`` it is the
        stress of the method's own solution, and a flagged slice is then a
        base in tension.

        ``raw_estimate`` is the stress (or force) BEFORE the clip; only its
        sign is read. ``c`` and ``tan_phi`` are what the linearisation
        returned, suction cohesion included. A material with no strength at
        either probe stress is strengthless by definition and is not
        flagged: the note this feeds is about strength LOST to the stress it
        was read at, not about a soil that never had any.

        v0.1.218 (D207) -- the probes set the VERTICAL effective stress too.
        SHANSEP and Vertical Stress Ratio read σ'v, not σ'ₙ, and since this
        version a slice whose σ'v is zero or negative (an artesian column)
        gets τ = A, or ``min_strength``, instead of the frictional su(σ'ₙ)
        SHANSEP used to fall back to. With both at zero that is no strength
        at all, and probing σ'ₙ alone would have read the soil as
        strengthless by definition and said nothing. The models that do not
        read σ'v ignore it, so their answer does not change.
        """
        if raw_estimate >= 0.0 or c > 0.0 or tan_phi > 0.0:
            return False
        material = getattr(slice_, "material", None)
        if material is None:
            return False
        for probe in BishopSimplified._STRENGTH_PROBES:
            c1, t1 = BishopSimplified._local_c_phi(slice_, material, probe,
                                                   sigma_v_probe=probe)
            if c1 > 0.0 or t1 > 0.0:
                return True
        return False

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
        from ..support_integration import (support_failure_details,
                                           support_vertical_load)

        axis = axis_for(project, surface)

        fos = max(0.05, self.initial_fos)
        converged = False
        iterations = 0
        # v0.1.210 (D172) -- the support load each slice's stress estimate
        # carried in the LAST pass, published so the checks linearise the
        # envelope where this solver did. See the circular path.
        sigma_load = None
        # v0.1.213 (D84) -- the slices of the LAST pass that entered with no
        # strength because their estimate was clipped; see ``_zero_strength``.
        zero: list[int] = []
        for it in range(1, self.max_iterations + 1):
            iterations = it
            forces = []
            weights = []
            resisting = []
            normals = []
            tangential = [0.0] * len(s_list) if sup.present else None
            tangential_passive = [0.0] * len(s_list) if sup.present else None
            sigma_load = [0.0] * len(s_list) if sup.present else None
            zero = []
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
                    load = support_vertical_load(
                        sup, i_s, s.base_angle, slide_sign, fos)
                    w_n += load
                    sigma_load[i_s] = load
                n_est = w_n * math.cos(s.base_angle)
                raw = n_est - s.pore_pressure * s.base_length
                sigma = max(0.0, raw)
                sigma /= max(s.base_length, 1e-9)
                # v0.1.213 (D84) -- or where the method's own solution put
                # this base, on the passes of ``self_consistent_envelope``.
                imposed = self._imposed_stress(i_s)
                if imposed is not None:
                    raw, sigma = imposed, max(0.0, imposed)
                c, tan_phi = self._local_c_phi(s, s.material, sigma)
                # v0.1.213 (D84) -- reported, not changed; see
                # ``_zero_strength``.
                if raw < 0.0 and self._zero_strength(s, raw, c, tan_phi):
                    zero.append(i_s)
                m_alpha = math.cos(alpha) + math.sin(alpha) * tan_phi / fos
                if abs(m_alpha) < 1e-6:
                    return LEMResult(
                        fos=None, converged=False, iterations=iterations,
                        method_id=self.METHOD_ID, surface=surface,
                        slices=slices,
                        error_message=(f"mα collapsed to {m_alpha:.4g} "
                                       f"at slice {s.index}"),
                        reason=REASON_M_ALPHA_COLLAPSED)
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
                    fos=None, converged=False, iterations=iterations,
                    method_id=self.METHOD_ID, surface=surface, slices=slices,
                    error_message=("Zero driving moment — surface does not "
                                   "slide"),
                    reason=REASON_ZERO_DRIVING)
            new_fos = -terms.shear / terms.driving
            if not math.isfinite(new_fos) or new_fos <= 0.0:
                return LEMResult(
                    fos=None, converged=False, iterations=iterations,
                    method_id=self.METHOD_ID, surface=surface, slices=slices,
                    error_message="Non-physical factor of safety",
                    reason=REASON_NON_PHYSICAL_FOS)
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

        # v0.1.213 (D81) -- the per-slice columns, which this branch left
        # EMPTY from v0.1.92, when it was split off the circular formula,
        # until now: every surface that is not a ``SlipCircle`` -- composite,
        # polyline, weak layer -- published no base normal. Three readers
        # noticed, one of them loudly. The interpretation windows showed a
        # dash, the verification bank published no maximum effective normal
        # stress for 32 of its archived Bishop surfaces, and
        # ``rapid_drawdown._stage1_state`` REFUSES a short list since
        # v0.1.108, so Bishop with a multi-stage drawdown on any non-circular
        # surface came out invalid ("drawdown_not_applicable") every time.
        # From v0.1.92 to v0.1.107, before that guard, it quietly re-solved
        # stage 1 instead.
        #
        # The same function as the circular branch and both Janbu, and not the
        # ``normals`` the loop above just used. They are the same force: the
        # vertical equilibrium of the slice with no inter-slice shear, which
        # is exactly what ``normal`` solves. Since v0.1.216 (D196) they
        # carry the same support load (the column used to leave it out, a
        # limitation all four callers shared; see the docstring below), and
        # they differ in one thing only: the loop's F is the one that
        # ENTERED the last pass, while this is the F returned. One function keeps one meaning for
        # the column on a circle and on a polyline. Fed back into the moment
        # balance about the same axis, Sigma N*f term included (Fredlund and
        # Krahn 1977), the published normals and strengths return the factor
        # of safety: tests/test_bishop_general_base_forces_v1213.py.
        pub_normals, pub_shears, pub_strengths = (
            base_forces_no_interslice_shear(
                s_list, kh, kv, slide_sign, fos,
                envelope_stress=self._envelope_stress,
                support_load=sigma_load))

        return LEMResult(
            fos=fos, converged=converged, iterations=iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=pub_normals,
            base_shear_force=pub_shears,
            base_shear_strength=pub_strengths,
            details=support_failure_details(sup, {
                "moment_axis": axis,
                # v0.1.189 (D112). Here ``alpha`` was already turned by
                # ``slide_sign`` before m_alpha was formed (see above), so
                # in the TRUE frame the denominator is
                # ``cos a + slide_sign*sin a*tan phi/F`` -- the same
                # expression the circular branch writes out. The two keys
                # come from ONE local in ONE statement, because while they
                # were two expressions they could drift apart again: that
                # is the lesson D113 left.
                "slide_sign": slide_sign,
                "m_alpha_sign": slide_sign,
                # v0.1.191 (D167) -- the vertical seismic coefficient this
                # method APPLIED, read by ``checks._applied_kv``: the same
                # ``kv`` handed to ``slice_forces``, so the checks load each
                # slice base as the solver did.
                # v0.1.214 (D173) -- and the horizontal one, so the
                # interslice march of the interpretation applies the
                # loads this method did (``compute_interslice_state``).
                "kh": kh,
                "kv": kv,
                # v0.1.210 (D172) -- the support load the last pass added
                # to each slice's stress estimate, read by
                # ``checks._applied_support_load``; None without a support.
                "sigma_support_load": sigma_load,
                # v0.1.213 (D84) -- read by
                # ``analysis_runner.zero_strength_note``.
                "zero_strength_slices": zero,
            }),
            error_message="" if converged else self.NOT_CONVERGED_NOTE,
            reason="" if converged else REASON_NOT_CONVERGED,
        )

    @self_consistent_envelope
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
            seismic_soil_weight(s.weight, kv) * math.sin(s.base_angle)
            for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.64 — support terms, resolved with their SIGNS. The sliding
        # sense has to be known first, which is why this moved below the
        # detection above.
        from ..support_integration import (resolve_support_terms,
                                           support_failure_details,
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
        # that arm: it states that the normal force does not pass through
        # the centre of rotation, and that a moment arm is calculated for
        # each normal force.
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
        # Σ W·(1 + kv)·sin α + Σ kh·W·(y_c − y_g)/R
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
        # v0.1.178 (D144) -- the MOMENT of the reinforcement and not its
        # projection on the chord. Everything else in this sum is a moment
        # about the centre divided by R -- the weight's, through
        # ``weight_arm_ratio``; the water's; the couple's -- and until this
        # version the support's was the one term formed from an angle
        # instead of from the geometry. See ``SupportTerms.moment_active``.
        denominator -= sup.moment_active
        # How much of the driving moment the Active supports have taken
        # away. Reported rather than judged: as T_S approaches D the
        # factor of safety grows without bound, which is arithmetically
        # right and physically meaningless, and no threshold separating
        # the two is defensible enough to hard-code.
        active_ratio = (
            sup.moment_active / driving_no_support
            if sup.present and abs(driving_no_support) > 1e-9 else 0.0
        )

        # The guard v0.1.15 worried about, made explicit. Reusing the
        # admissibility channel of v0.1.32 keeps the surface in the
        # evaluation list — search algorithms need the feedback — while
        # excluding it from the choice of critical surface.
        if sup.present and denominator <= 0.0:
            return LEMResult(
                fos=None,
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
                reason=REASON_ACTIVE_SUPPORT_EXCEEDS_DRIVING,
            )

        if abs(denominator) < 1e-9:
            return LEMResult(
                fos=None,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                error_message="Zero driving moment — surface does not slide",
                reason=REASON_ZERO_DRIVING,
            )

        # Iterative fixed-point solve for FoS
        fos = self.initial_fos
        converged = False
        iterations = 0
        # v0.1.74 — the last iterates, for the optional Steffensen
        # acceleration. Kept as a short list rather than three variables
        # so the "clear after using them" step cannot half-happen.
        history: list[float] = []

        # v0.1.210 (D172) -- the support load each slice's stress estimate
        # carried in the LAST pass: the one whose sigma produced the factor
        # returned. Published so ``checks`` linearises the envelope where
        # this solver did; it depends on F only through a PASSIVE support
        # (``t_passive / F``), so it is captured, not recomputed at the end.
        sigma_load = None
        # v0.1.213 (D84) -- as in ``_general_moment_fos``.
        zero: list[int] = []
        for it in range(1, self.max_iterations + 1):
            iterations = it
            numerator = 0.0
            sigma_load = [0.0] * len(s_list) if sup.present else None
            zero = []

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
                    load = support_vertical_load(
                        sup, i_s, s.base_angle, slide_sign, fos)
                    W_eff += load
                    sigma_load[i_s] = load

                N_est = W_eff * math.cos(s.base_angle)
                raw = N_est - s.pore_pressure * s.base_length
                N_eff_est = max(0.0, raw)
                sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)
                # v0.1.213 (D84) -- see ``_general_moment_fos``.
                imposed = self._imposed_stress(i_s)
                if imposed is not None:
                    raw, sigma_n_eff = imposed, max(0.0, imposed)

                c, tan_phi = self._local_c_phi(s, s.material, sigma_n_eff)
                if raw < 0.0 and self._zero_strength(s, raw, c, tan_phi):
                    zero.append(i_s)

                m_alpha = math.cos(s.base_angle) + (
                    slide_sign * math.sin(s.base_angle) * tan_phi / fos
                )

                if abs(m_alpha) < 1e-6:
                    return LEMResult(
                        fos=None,
                        converged=False,
                        iterations=iterations,
                        method_id=self.METHOD_ID,
                        surface=surface,
                        slices=slices,
                        error_message=(
                            f"mα collapsed to {m_alpha:.4g} at slice {s.index}"
                        ),
                        reason=REASON_M_ALPHA_COLLAPSED,
                    )

                # Bishop numerator: [c'·b + (W − u·b)·tan φ'] / m_α
                numerator += (
                    c * b + (W_eff - s.pore_pressure * b) * tan_phi
                ) / m_alpha

            # Passive supports add their resisting tangential component
            # to the numerator; the Active ones already came off the
            # denominator before the iteration started.
            numerator += sup.moment_passive

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
                    fos=None,
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
                    reason=REASON_NON_PHYSICAL_FOS,
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
            s_list, kh, kv, slide_sign, fos,
            envelope_stress=self._envelope_stress,
            support_load=sigma_load)

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iterations,
            error_message="" if converged else self.NOT_CONVERGED_NOTE,
            reason="" if converged else REASON_NOT_CONVERGED,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
            base_normal_force=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
            details=support_failure_details(sup, {
                "active_support_ratio": active_ratio,
                # v0.1.189 (D112) -- read by ``checks._denominator_sign``.
                # This IS the sign the m_alpha of this iteration carried.
                "slide_sign": slide_sign,
                "m_alpha_sign": slide_sign,
                # v0.1.191 (D167) -- see the non-circular exit.
                # v0.1.214 (D173) -- and the horizontal one, so the
                # interslice march of the interpretation applies the
                # loads this method did (``compute_interslice_state``).
                "kh": kh,
                "kv": kv,
                # v0.1.210 (D172) -- see above; None without a support.
                "sigma_support_load": sigma_load,
                # v0.1.213 (D84) -- see the non-circular exit.
                "zero_strength_slices": zero,
            }),
        )


# ======================================================================
# v0.1.216 (D196) -- whether the published normal carries the vertical load
# a support puts on the slice, the load the method's own iteration and, since
# v0.1.210, its checks put there (``sigma_support_load``). A module switch,
# like ``base.ENVELOPE_AT_OWN_STRESS``, so an A/B can rebuild the column as
# it was and a test can demand that it moves (rule 7).
SUPPORT_IN_PUBLISHED_NORMAL = True


def base_forces_no_interslice_shear(
    slices,
    kh: float,
    kv: float,
    slide_sign: float,
    fos: float,
    envelope_stress: Optional[list] = None,
    support_load: Optional[list] = None,
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
    Bishop takes it from ``sign(sum W*(1+kv)*sin alpha)`` and Janbu from
    ``sign(sum W_total*tan alpha)``; each has to hand over the one its own
    iteration used, because ``m_alpha`` is not symmetric in alpha and only
    means something read in the same sense of sliding (the v0.1.82
    anomaly, recorded in AGENTS.md).

    Returns ``(normals, driving_shears, strengths)``, all three FORCES in
    kN/m: the base normal N, the driving force ``s*W*sin(alpha)`` and the
    available shear resistance ``tau_f*l``.

    Four callers since v0.1.213: Bishop on a circle and on any other surface
    (D81), and both Janbu.

    ``support_load`` (v0.1.216, D196) is the vertical load each support put
    on each slice in the method's last pass, the list it publishes as
    ``details["sigma_support_load"]``. It is handed over, never recomputed
    here, because a passive support's load depends on F. With
    ``SUPPORT_IN_PUBLISHED_NORMAL`` it joins ``W`` in the stress estimate
    and in ``N``, so the column is the normal of the method's own
    equilibrium and the one the checks read. Until v0.1.215 "support forces
    do not enter N" was a known limitation carried over from where this
    code used to live: on a nail at -15 deg the crossed slice published
    ``N/l - u`` = 12.83 kPa where the method's own normal gives 32.35. The
    driving column keeps the soil's ``W*sin(alpha)``: the support's
    tangential effect is in the method's own terms, not in a slice's shear.

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
    with_support = (SUPPORT_IN_PUBLISHED_NORMAL and support_load is not None)
    for i, s in enumerate(slices):
        f = slice_forces(s, kh, kv)
        W_eff = f.w_total
        # v0.1.216 (D196) -- the load the iteration and the checks carry.
        W_n = W_eff
        if with_support and i < len(support_load) and support_load[i]:
            W_n = W_eff + support_load[i]
        l = max(s.base_length, 1e-9)
        alpha = s.base_angle
        N_est = W_n * math.cos(alpha)
        N_eff_est = max(0.0, N_est - s.pore_pressure * l)
        sigma_n_eff = N_eff_est / l
        # v0.1.213 (D84) -- the point the solver itself linearised at, when
        # ``self_consistent_envelope`` imposed one: this N has to be the one
        # of the same straight line.
        imposed = (envelope_stress[i] if envelope_stress is not None
                   and i < len(envelope_stress) else None)
        if imposed is not None:
            sigma_n_eff = max(0.0, imposed)
        c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma_n_eff)
        m_alpha = math.cos(alpha) + (
            slide_sign * math.sin(alpha) * tan_phi / fos
        )
        # v0.1.213 (D81) - divided by m_alpha WITH ITS SIGN. It was
        # ``max(abs(m_alpha), 1e-6)``, carried over without a reason from
        # where this code used to live. On a slice with m_alpha < 0, a steep
        # toe base with a large tan(phi')/F, that published a normal of the
        # OPPOSITE sign to the one the vertical equilibrium in the docstring
        # gives. It was also opposite to the one ``checks.base_effective_
        # stresses`` rebuilds, and to the one ``_general_moment_fos`` puts in
        # its own moment balance. The stage-1 state of the multi-stage
        # drawdown reads this column, so there the flipped sign turned a
        # base in tension into a consolidated one. The floor keeps its size
        # and takes the sign; the solvers stop well before it, on
        # |m_alpha| < 1e-6.
        N = (W_n
             - slide_sign * (c * l * math.sin(alpha)) / fos
             + slide_sign * (s.pore_pressure * l * tan_phi
                             * math.sin(alpha)) / fos
             ) / math.copysign(max(abs(m_alpha), 1e-6), m_alpha)
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
