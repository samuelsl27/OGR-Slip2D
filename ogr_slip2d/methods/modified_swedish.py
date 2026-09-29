# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Force-equilibrium methods with a PRESCRIBED inter-slice inclination.

Three methods share one engine and differ in a single line: where the
inter-slice inclination θ comes from. The engine is the numerical
solution of the **Modified Swedish Method** as published by the U.S. Army
Corps of Engineers:

    USACE (2003). "Slope Stability", EM 1110-2-1902, Appendix C,
    equations C-19, C-20a-d and C-21 (the recursion), and Appendix G,
    equation G-16 (the base normal force). The original statement of the
    procedure is USACE (1970), EM 1110-2-1902, "Stability of Earth and
    Rock-Fill Dams".

    Z_{i+1} = Z_i + (C1 + C2 + C3 + C4) / n_α

    C1 = W · [ sin α − (tan φ'/F) · cos α ]
    C2 = (U_i − U_{i+1}) · [ cos α + (tan φ'/F) · sin α ]
    C3 = P · [ sin(α − β) − (tan φ'/F) · cos(α − β) ]
    C4 = − (c'·Δℓ − u·Δℓ·tan φ') / F
    n_α = cos(α − θ) + (tan φ'/F) · sin(α − θ)

This program marches with the geometry mirrored in x when the mass slides
towards −x (``orient`` below), which maps α → −α and θ → −θ; under that
mirror the four terms above are term-by-term identical to :meth:`_march`,
including the surface-water load C3, which is carried here as a vertical
part inside ``w_total`` and a horizontal part inside ``h_water`` (the two
decompositions are algebraically the same force).

Verified against the manual's own worked example: driving :meth:`_march`
with the twelve published slices of EM Figure G-9 reproduces the
published inter-slice force column within the rounding of the table and
gives F = 1.3435 against the published **1.35**. See
``tests/test_modified_swedish_v198.py``.

The θ assumptions, and where each one comes from:

    Lowe-Karafiath        θ_i = ½·(β_i + α_i)      varies per slice
    Corps of Engineers #1 θ   = chord of the slip surface   constant
    Corps of Engineers #2 θ_i = β_i                varies per slice

Each method defines θ per SLICE; the force on a boundary is inclined at the
average of its two slices since v0.1.223 (D222; see ``THETA_AT_BOUNDARY``),
which is where the assumption places it ("at each vertical interslice
boundary", EM 1110-2-1902 Sec. C-4a).

References for the assumptions:

    Lowe, J. & Karafiath, L. (1960). "Stability of earth dams upon
    drawdown." Proc. 1st Pan-American Conf. on Soil Mechanics and
    Foundation Engineering, Mexico City, Vol. 2, 537-552.
    USACE (2003), EM 1110-2-1902, §C-4a, for the Corps assumption: "the
    side forces should be assumed to be parallel to the average
    embankment slope ... usually taken to be the slope of a straight line
    drawn between the crest and toe of the slope".

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.project import Project

from ..external_forces import (interslice_water_thrust,
                               seismic_vertical_load, slice_forces)
from ..slicer import Slices
from ..surface import SurfaceProtocol
from .base import (
    REASON_FORCE_BALANCE_DIVERGED,
    REASON_NO_FORCE_BRACKET,
    REASON_NO_SLICES,
    LEMMethod,
    LEMResult,
    register_method,
    self_consistent_envelope,
)
from .bishop import BishopSimplified, driving_shear_forces

#: Accepted values of ``interslice_forces``.
EFFECTIVE_INTERSLICE = "effective"
TOTAL_INTERSLICE = "total"

# v0.1.222 (D220) -- the interslice ratios this family publishes are the
# ones its recursion solved with. ``details["boundary_ratios"]`` gave every
# interior boundary the tangent of the AVERAGE of the θ of its two slices,
# while ``_march`` inclines the force on that boundary at the θ of the slice
# on its left. With θ constant (Corps #1) the two are the same number bit
# for bit; with θ varying (Corps #2, Lowe-Karafiath) the interslice march of
# the interpretation (``postprocess.compute_interslice_state``) rebuilt a
# state that is not the method's: on the slope of
# ``test_support_normal_v1137`` its normals parted from the method's by 5.95
# and 2.79 (in units of max(1, |N|)) and it closed only to 2e-2 and 2e-3;
# with the solver's ratios it reproduces them to 1e-15. No factor reads the
# ratios. A module switch, like ``postprocess.SUPPORT_IN_MARCH``, so an A/B
# can rebuild the old ratios and a test can demand that they move (rule 7).
BOUNDARY_RATIOS_AS_SOLVED = True

# v0.1.223 (D222) -- the interslice force on a boundary is inclined at the
# average of the inclinations of the two slices that share it. Each method of
# the family defines theta per SLICE (``_theta_angles``), and until this
# version the recursion gave each boundary the theta of the slice on its
# LEFT in index order, which always runs left to right in x: the mirror of
# the march (``orient``) negates alpha and theta but keeps the order. Three
# things said that was wrong:
#
# * The definition. Lowe and Karafiath (1960) incline the interslice forces
#   at "the average of the inclinations of the slope (ground surface) and
#   shear surface at each vertical interslice boundary" (USACE 2003,
#   EM 1110-2-1902, Sec. C-4a); Duncan, Wright & Brandon (2014, Table 6.1)
#   say the inclination varies "depending on where the slice boundaries are
#   located", and their Fig. 6.14c draws the ground-slope variant of the
#   Corps assumption (Corps #2 here) the same way: "interslice force here is
#   parallel to average slope here". The inclination belongs to the vertical
#   section the force acts on. Taking the slice on one side evaluates it
#   half a slice away.
# * Symmetry. The same problem reflected about a vertical line gave another
#   factor: the slope of ``test_support_normal_v1137`` and its mirror image,
#   50 slices, Corps #2 1.923682 against 1.906777 (-0.88 %), Lowe-Karafiath
#   1.861010 against 1.859092 (-0.10 %); halving with every doubling of the
#   slices, as a one-sided evaluation does. The average is symmetric by
#   construction; measured, the two factors agree to 1e-10, the tolerance
#   of the root.
# * Accuracy. On a ground and a slip surface whose inclinations vary
#   smoothly the one-sided choice converges at first order in the slice
#   width (observed order 0.97 to 1.03 up to 1 600 slices, with the left
#   and the right one missing on opposite sides) and the average at second
#   order (observed 2.00), to the same limit: the Richardson extrapolation
#   of the old factors lands on the new ones.
#
# External check: the given circle of verification problem 27 (Malkawi,
# Hassan & Sarma 2001, published by the reference program and by XSTABL),
# where the two programs agree that Lowe-Karafiath equals Corps #1 and
# Corps #2 is 0.003 above it. With the average at each boundary OGR gives
# -0.0005 and +0.0023; with the left slice, -0.0020 and +0.0033 (see
# ``test_prescribed_theta_boundary_v1223``).
#
# Why the average of the two slices and not the geometry at the boundary
# (the tangent of a circle, the ground slope at that x): the slices are the
# geometry the method solves -- their chords carry its base angles and their
# tops its weights -- and on that polygon the inclination AT a boundary is
# undefined where two chords meet, the symmetric choice being their
# bisector, which is the average of the two angles. Both converge at second
# order to the same limit (measured); with a ground drawn as a polyline the
# exact one picks up the slope of whichever segment the boundary falls on.
# With theta constant (Corps #1) nothing moves by a bit. A module switch, so
# an A/B can rebuild the old factors and a test can demand that they move.
THETA_AT_BOUNDARY = True

# v0.1.224 (D223) -- Corps of Engineers #1 draws its line to the TOP of a
# tension crack. Its assumption is interpretation 1 of Duncan, Wright &
# Brandon (2014, Fig. 6.14a): a line joining the points where the failure
# surface meets the ground. A tension crack truncates the mass at its crest
# end, and the failure surface -- the slip surface and the crack -- reaches
# the ground at the top of the crack; the line was drawn to its BOTTOM, a
# point of the slip surface below the ground. On the given circle of
# verification problem 27 with its 11 ft crack, whose values the reference
# program and XSTABL publish with the same differences between methods
# (Corps #2 0.007 above Corps #1 dry and 0.006 wet, Lowe-Karafiath 0.010
# below), OGR gave +0.026 and +0.010: Corps #1 fell 1.3 % against the
# offset every other method of that model shares. To the top of the crack,
# +0.0066 / -0.0101 dry and +0.0060 / -0.0098 wet. An end with no crack is
# where the slip surface meets the ground -- which is not the end slice's
# own top when the surface leaves through a vertical face, the reason the
# crack is read from its wall -- and does not move by a bit. A module
# switch, so an A/B can rebuild the old line and a test can demand that it
# moves.
CHORD_TO_CRACK_TOP = True


def boundary_theta(theta):
    """The inclination of each of the n+1 slice boundaries, from the n
    per-slice values ``theta``: the average of the two slices of an
    interior boundary, and the end slice's own at the two free ends, where
    no force acts. With ``THETA_AT_BOUNDARY`` off, the slice on the LEFT of
    each boundary, as the recursion had it until v0.1.222.

    The one place the rule lives: the recursion (``_march``), the base
    normals (``_base_forces``) and the published ratios
    (``_boundary_ratios``) all read it, so what the interpretation shows is
    what was solved (D220). A negated ``theta`` -- the mirrored march --
    gives the negated inclinations exactly."""
    if not theta:
        return []
    if not THETA_AT_BOUNDARY:
        return [theta[0]] + list(theta)
    return ([theta[0]]
            + [0.5 * (a + b) for a, b in zip(theta, theta[1:])]
            + [theta[-1]])


# ======================================================================
class PrescribedInclinationMethod(LEMMethod):
    """Force equilibrium with θ fixed by a geometric rule, not solved for.

    Subclasses implement :meth:`_theta_angles` and nothing else.
    """

    SATISFIES_FORCE = True
    SATISFIES_MOMENT = False

    def __init__(self, *args,
                 interslice_forces: str = TOTAL_INTERSLICE,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # v0.1.98 — whether the resultant Z whose inclination is prescribed
        # is the EFFECTIVE inter-slice force (the water pressure on the
        # vertical faces separated out and applied as its own horizontal
        # load) or the TOTAL one. EM 1110-2-1902 §C-4a treats both as
        # legitimate and says the computed factor of safety differs
        # between them; its OWN worked example in Appendix G uses total
        # forces, and §G-5a says so.
        #
        # v0.1.144 — the default is TOTAL here as well, and deliberately
        # the SAME value ``MethodsSettings.interslice_forces`` carries.
        # Two defaults that disagree is the failure this project has paid
        # for three times over (the frozen method list of v0.1.78, the two
        # Auto Refine questions of D33): whoever instantiates the class
        # directly would silently get a different analysis from whoever
        # goes through ``build_method``. The reasoning for the value, and
        # what it costs, is in ``MethodsSettings.interslice_forces``.
        self.interslice_forces = (
            TOTAL_INTERSLICE if str(interslice_forces).strip().lower()
            == TOTAL_INTERSLICE else EFFECTIVE_INTERSLICE
        )

    # ------------------------------------------------------------------
    def _theta_angles(self, slices: Slices) -> list[float]:
        """θ for each slice, in radians and in the TRUE (unmirrored) frame.

        The one thing that distinguishes the methods of this family.
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    @self_consistent_envelope
    def compute_fos(
        self, project: Project, surface: SurfaceProtocol, slices: Slices,
    ) -> LEMResult:
        # A surface with no shear strength anywhere has F = 0 exactly and
        # no iteration to run; see LEMMethod.NO_SHEAR_STRENGTH_NOTE for why
        # this is answered here rather than left to the arithmetic.
        strengthless = self._no_shear_strength_result(surface, slices)
        if strengthless is not None:
            return strengthless

        if not slices.slices:
            return LEMResult(
                fos=None, converged=False, iterations=0,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message="No slices",
                reason=REASON_NO_SLICES,
            )

        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        # Detect sliding direction from the raw driving moment so the
        # up-slope side is consistently positive (same convention as the
        # rigorous methods).
        driving_raw = sum(
            seismic_vertical_load(s, kv) * math.sin(s.base_angle)
            for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.61 — a method that PRESCRIBES the inter-slice inclination
        # cannot be fed a total inter-slice force without saying so: the
        # water part of it is horizontal, and forcing a resultant
        # dominated by it to lie at θ invents a large vertical component.
        # Separating it is what makes Z the EFFECTIVE force; leaving it in
        # is what makes Z the total one. See ``interslice_water_thrust``
        # and EM 1110-2-1902 §C-4a.
        face_thrust = (
            interslice_water_thrust(project, slices)
            if self.interslice_forces == EFFECTIVE_INTERSLICE else None
        )

        # v0.1.64 — supports, as an external force on each slice.
        from ..support_integration import (resolve_support_terms,
                                           support_failure_details,
                                           support_forces,
                                           support_moments,
                                           support_normal_load)
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        fos, converged, iters, ctx = self._force_balance(
            slices, kh, kv, slide_sign, face_thrust, sup,
        )

        if fos is None or not (math.isfinite(fos) and fos > 0):
            return LEMResult(
                fos=None, converged=False, iterations=iters,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message=f"{self.DISPLAY_NAME}: force balance diverged",
                reason=REASON_FORCE_BALANCE_DIVERGED,
            )

        normals, _mobilised, strengths = self._base_forces(
            list(slices), ctx, fos)
        reversal = self._thrust_reversal(list(slices), ctx, fos)
        # v0.1.107 - ``base_shear_force`` is the DRIVING force in every
        # method now. This one used to publish the MOBILISED shear there,
        # which is a factor of the safety factor away and was 2.58 against
        # 41.0 on the same slice - under an interface row that reads
        # "Driving shear W*sin(alpha)". The mobilised shear is not lost:
        # it is exactly ``base_shear_strength / fos``, which is what the
        # interpretation window already divides for its own row.
        driving = driving_shear_forces(slices, kh, kv, slide_sign)

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iters,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            # v0.1.152 (D56) - sin bracket, ``_force_balance`` devuelve el
            # F muestreado de menor residuo. Es un valor de reserva, no una
            # solucion, y hasta ahora salia con ``converged=False`` y sin
            # una palabra que lo dijera: sobre una masa simetrica los tres
            # metodos de inclinacion prescrita respondian 5.0 -el TECHO de
            # su propia rejilla- con el motivo vacio.
            error_message=("" if converged else
                           f"{self.DISPLAY_NAME}: no F-bracket; reporting "
                           f"the sampled F of smallest residual"),
            reason="" if converged else REASON_NO_FORCE_BRACKET,
            base_normal_force=normals,
            base_shear_force=driving,
            base_shear_strength=strengths,
            details=support_failure_details(sup, {
                "boundary_ratios": self._boundary_ratios(slices),
                "interslice_forces": self.interslice_forces,
                "thrust_reversal": reversal,
                # v0.1.189 (D112). ``slide_sign`` is what this method
                # derived and what it handed to the support resolution and
                # to ``driving_shear_forces``. There is deliberately NO
                # ``m_alpha_sign``, and the reason is a sign trap that runs
                # the other way from the obvious one: with
                # ``alpha_n = orient*a`` and ``theta_n = orient*t``, the
                # denominator ``_march`` forms is, back in the true frame,
                #
                #     D = cos(a - t) - orient*(tan phi/F)*sin(a - t)
                #
                # because this family writes a MINUS where Bishop writes a
                # plus. So ``cos a + s*sin a*tan phi/F`` is not a quantity
                # this family forms for ANY ``s``: writing ``slide_sign``
                # there would be false, and writing ``orient`` would be
                # false the other way round. The march orientation itself
                # is reported and not written; see the changelog.
                "slide_sign": slide_sign,
                # v0.1.191 (D167) -- the vertical seismic coefficient IS
                # published: the Tensile Stress Check runs on this family
                # too, and loads each base with the ``kv`` handed to
                # ``slice_forces`` here (read by ``checks._applied_kv``).
                # v0.1.214 (D173) -- and the horizontal one, so the
                # interslice march of the interpretation applies the
                # loads this method did (``compute_interslice_state``).
                "kh": kh,
                "kv": kv,
                # v0.1.210 (D172) -- what the checks read to judge this
                # surface as this solver solved it: the support load in the
                # stress estimate (``-nf_v``, as ``w_total`` minus it is what
                # the solver linearised at) and the base normal of its OWN
                # solution, which the Tensile Stress Check tests.
                "sigma_support_load": support_normal_load(sup),
                # v0.1.221 (D212) -- the whole force of the support on each
                # slice, at this method's F (its tangential part enters the
                # recursion through ``k0`` mobilised the same way), and its
                # moment about the base midpoint: read by the interslice
                # march.
                "support_force": support_forces(sup, slices, slide_sign, fos),
                "support_moment": support_moments(sup, slices),
                "solved_base_normal": list(normals),
                # v0.1.213 (D84) -- see ``_zero_strength_slices``.
                "zero_strength_slices": self._zero_strength_slices(
                    list(slices), ctx),
            }),
        )

    # ------------------------------------------------------------------
    def _zero_strength_slices(self, slist, ctx) -> list[int]:
        """The slices ``_march`` linearised at a clipped estimate that left
        them with no strength (v0.1.213, D84; see
        ``BishopSimplified._zero_strength``).

        Counted here once, not inside ``_march``, which runs dozens of times
        per surface: its estimate does not depend on F, so every march of a
        surface clips the same slices. The expression is the one in
        ``_march``, term for term, with the same loads from ``ctx``.
        """
        if ctx is None:
            return []
        alpha_n, _theta, kh, kv, _h_water, v_sup, _t_act, _t_pas = ctx
        out: list[int] = []
        for i, s in enumerate(slist):
            W_eff = slice_forces(s, kh, kv).w_total - v_sup[i]
            l = s.base_length
            raw = W_eff * math.cos(alpha_n[i]) - s.pore_pressure * l
            imposed = self._imposed_stress(i)
            if imposed is not None:
                raw = imposed
            if raw >= 0.0:
                continue
            c_loc, tan_phi = BishopSimplified._local_c_phi(
                s, s.material, max(0.0, raw) / (
                    1.0 if imposed is not None else max(l, 1e-9)))
            if BishopSimplified._zero_strength(s, raw, c_loc, tan_phi):
                out.append(i)
        return out

    # ------------------------------------------------------------------
    def _boundary_ratios(self, slices: Slices) -> list[float]:
        """tan θ at each of the n+1 slice boundaries, in the raw frame.

        The inclination :meth:`_march` gave each boundary
        (:func:`boundary_theta`): since v0.1.223 (D222) the average of its
        two slices, which is also what this published until v0.1.221,
        while the recursion took the slice on the left (D220 made the
        publication follow the recursion; D222 moved the recursion). The
        mirror of the march (``orient``) negates α and θ but keeps the
        order of the slices, so the rule is the same in both senses. The
        free ends carry no force and take their end slice's θ. See
        ``BOUNDARY_RATIOS_AS_SOLVED``.
        """
        th = self._theta_angles(slices)
        if not th:
            return []
        if BOUNDARY_RATIOS_AS_SOLVED:
            return [math.tan(t) for t in boundary_theta(th)]
        out = [math.tan(th[0])]
        for i in range(len(th) - 1):
            out.append(math.tan(0.5 * (th[i] + th[i + 1])))
        out.append(math.tan(th[-1]))
        return out

    # ==================================================================
    def _march(self, slices_list, theta, alpha_n, kh, kv, F: float,
               h_water=None, v_support=None, t_support=None):
        """The inter-slice resultant ``Z`` on the right face of every slice.

        Each slice carries a resultant inter-slice force ``Z_i`` on its
        right face, inclined to the horizontal at the angle ``θ_{i+1}`` of
        that boundary, and receives ``Z_{i-1}`` on its left face at the
        angle ``θ_i`` of its left boundary (``boundary_theta``: the n
        per-slice angles ``theta`` give the n+1 boundary ones, v0.1.223,
        D222). Eliminating the base normal ``N`` and the mobilised
        shear ``S = [c·l + (N − u·l)·tanφ]/F`` from the two force
        equilibrium equations of the slice gives the linear recursion

            Z_i = ( Z_{i-1}·D⁻ + const_i ) / D_i

        with
            a       = tanφ / F
            D_i     = cos(α_i − θ_{i+1}) − a·sin(α_i − θ_{i+1})
            D⁻      = cos(α_i − θ_i)     − a·sin(α_i − θ_i)
            const_i = (kh·W − k0·cosα)(cosα − a·sinα)
                      − (W + k0·sinα)(sinα + a·cosα)
            k0      = (c·l − u·l·tanφ) / F

        v0.1.115 — ``t_support`` is a reinforcement force ALONG THE BASE, in
        the sense that resists sliding, already mobilised. It enters through
        ``k0`` and that is exact rather than an analogy: the mobilised shear
        of this recursion is ``S/F = k0 + N·a``, so a resisting tangential
        force ``T`` is literally ``k0 + T``. The caller decides what to pass
        — ``T_S`` for an ACTIVE support, ``T_S/F`` for a PASSIVE one — which
        is the whole of the Active/Passive distinction in a method that never
        forms a ratio to move a term across.

        Until v0.1.114 the support arrived instead as a Cartesian force in
        ``h_water``/``v_support``, whole. For an ACTIVE support that is the
        same statement — ``k0 += T`` changes ``const_i`` by exactly ``−T``,
        and so does the Cartesian pair that represents the same tangential
        force — which is why the Active answers of this family do not move a
        digit in v0.1.115. What a Cartesian load cannot express is a PASSIVE
        support, because ``T/F`` is not a load: it is a resistance that
        develops only as far as the rest of the slope mobilises. That is why
        all three methods of this family answered the same number for both
        settings until now.

        ``D⁻`` is what generalises EM 1110-2-1902 equation C-19 from a
        constant θ to one that varies from slice to slice: with θ constant
        ``D⁻ = D_i`` and the recursion collapses to the manual's
        ``Z_{i+1} = Z_i + (…)/n_α`` exactly.

        Both free ends require Z = 0; starting from ``Z_0 = 0`` the
        residual ``Z_n`` is driven to zero by the correct ``F``.

        Returns ``None`` when the march hits an inadmissible state.
        """
        Z = 0.0
        out: list[float] = []
        # v0.1.223 (D222) -- the inclination of each BOUNDARY: the force on
        # the left face of slice i is the one boundary i carries, and the
        # force on its right face the one boundary i+1 carries.
        theta_b = boundary_theta(theta)
        if h_water is None:
            h_water = [0.0] * len(slices_list)
        if v_support is None:
            v_support = [0.0] * len(slices_list)
        if t_support is None:
            t_support = [0.0] * len(slices_list)

        for i, (s, alpha, hw, vs, ts) in enumerate(zip(
                slices_list, alpha_n, h_water, v_support, t_support)):
            theta_prev, th = theta_b[i], theta_b[i + 1]
            # v0.1.61 — the ponded water rides in the vertical term (it is
            # a load the base has to carry) and its horizontal thrust joins
            # the seismic force in the horizontal slot. This is a
            # force-equilibrium method, so the point of application does
            # not enter: only the resultant does.
            # v0.1.64 — the support's vertical component joins the load
            # the base carries (``f_v`` is +y, ``W_eff`` is +down), so the
            # friction it mobilises comes out of the recursion itself.
            fx = slice_forces(s, kh, kv)
            W_eff = fx.w_total - vs
            l = s.base_length
            u = s.pore_pressure

            sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / max(l, 1e-9)
            # v0.1.213 (D84) -- or where the method's own solution put this
            # base; see ``base.self_consistent_envelope``.
            imposed = self._imposed_stress(i)
            if imposed is not None:
                sigma_est = max(0.0, imposed)
            c_loc, tan_phi = BishopSimplified._local_c_phi(
                s, s.material, sigma_est
            )

            a = tan_phi / F
            ca, sa = math.cos(alpha), math.sin(alpha)
            k0 = (c_loc * l - u * l * tan_phi) / F
            # The reinforcement, already mobilised: see the note above on why
            # a base-tangential force is exactly an addition to ``k0``.
            if ts:
                k0 += ts

            D_i = math.cos(alpha - th) - a * math.sin(alpha - th)
            D_prev = math.cos(alpha - theta_prev) - a * math.sin(alpha - theta_prev)
            # Admissibility: the base term must stay positive (analogous
            # to Bishop's mα > 0). When F is small, tanφ/F grows and this
            # denominator can vanish or flip sign, producing a pole in
            # Z(F) and a *spurious* low-F root. Reject those states so the
            # only sign change left in the residual is the physical one.
            if D_i <= 1e-6 or D_prev <= 1e-6:
                return None

            # v0.1.214 (D170) -- the seismic force from ``slice_forces``,
            # ``kh·W`` on the static weight, and not written out here: this
            # was ``kh·W·(1 − kv)``, the last copy of a coupling the
            # pseudo-static formulation does not have.
            const_i = (
                (fx.h_seismic + hw - k0 * ca) * (ca - a * sa)
                - (W_eff + k0 * sa) * (sa + a * ca)
            )
            Z = (Z * D_prev + const_i) / D_i
            out.append(Z)

        return out

    # ------------------------------------------------------------------
    def _z_end(self, slices_list, theta, alpha_n, kh, kv, F: float,
               h_water=None, v_support=None, t_support=None) -> float:
        """Residual inter-slice force left at the down-slope free end.

        Thin wrapper over :meth:`_march`; kept as its own name because it
        is what the root finder reads and what the validation tests drive.
        """
        zs = self._march(slices_list, theta, alpha_n, kh, kv, F,
                         h_water=h_water, v_support=v_support,
                         t_support=t_support)
        return math.nan if zs is None else zs[-1]

    # ==================================================================
    def _thrust_reversal(self, slist, ctx, F: float) -> float:
        """How far the inter-slice thrust turns against its own sense.

        ``0`` when every interior boundary pushes the same way, ``1`` when
        the largest reversed force is as large as the largest force of the
        dominant sense. It is a DIAGNOSTIC published in ``details``, not a
        veto — what it is for is written below.

        WHY IT EXISTS. This system has more than one root. On the submerged
        slope of Duncan and Wright (2005) figure 6.27, analysed with TOTAL
        inter-slice forces and the water 60 ft above the crest,
        Lowe-Karafiath converges — ``converged = True``, no warning — to
        F = 0.220 where every other method says 1.60. The residual there is
        a genuine zero (|Z_n|/max|Z_i| = 9e-12), so it is not a pole the
        admissibility guard in :meth:`_march` could have caught, and the
        net thrust is compressive, so the criterion Spencer and GLE use
        (:func:`ogr_slip2d.interslice.thrust_is_admissible`) does not catch
        it either: both were measured before this one and both are blind
        here. What IS visible is that the thrust reverses along the
        surface: 23 of 49 boundaries push the opposite way, the largest of
        them 28 % of the peak, where every root that reproduces a published
        factor of safety stays under 2.2 %.

        Reference:
            Ching, R.K.H. & Fredlund, D.G. (1983). "Some difficulties
            associated with the limit equilibrium method of slices." Can.
            Geotech. J. 20(4), 661-672 — on multiple and spurious roots of
            the limit-equilibrium system and on rejecting them by the sign
            of the inter-slice forces.

        SIGN-AGNOSTIC ON PURPOSE. ``Z`` comes out of a march whose
        orientation is chosen by :meth:`_force_balance`, and the mirrored
        one negates it, so "compression is negative" is a property of the
        march and not of the soil. Measuring the reversal against the
        DOMINANT sense of the same march is what keeps a legitimate
        solution from reading as fully reversed merely because it was
        marched from the other end — the failure ``prepare_rows`` documents
        for the GLE recursion, where it put all 39 boundaries of
        verification problem 26 in false tension.

        Costs one extra march per surface, against the sixteen-plus the
        root finder already spends and the one :meth:`_base_forces` spends:
        about 1 %.
        """
        if ctx is None or not slist:
            return 0.0
        alpha_n, theta, kh, kv, h_water, v_sup, t_act, t_pas = ctx
        t_sup = [t_act[i] + t_pas[i] / F for i in range(len(t_act))]
        zs = self._march(slist, theta, alpha_n, kh, kv, F,
                         h_water=h_water, v_support=v_sup, t_support=t_sup)
        # The last entry is the closure residual, driven to zero by F; it
        # is not a boundary force and must not set the scale.
        interior = zs[:-1] if zs else []
        if not interior:
            return 0.0
        peak = max(abs(z) for z in interior)
        if peak <= 0.0:
            return 0.0
        dominant = 1.0 if math.fsum(interior) >= 0.0 else -1.0
        return max(0.0, max(-dominant * z for z in interior)) / peak

    # ==================================================================
    def _base_forces(self, slist, ctx, F: float):
        """Per-slice base normal, mobilised shear and available strength.

        The base normal comes from the VERTICAL equilibrium of the slice
        alone, which is EM 1110-2-1902 equation G-16:

            N = [ W + P·cosβ − ΔZ_v − ((c'Δℓ − u·Δℓ·tanφ')/F)·sinα ]
                / [ cosα + (tanφ'·sinα)/F ]

        with ``ΔZ_v = Z_i·sinθ_{i+1} − Z_{i-1}·sinθ_i`` the net vertical
        component of the two inter-slice forces, each at the angle of its
        boundary (``boundary_theta``, v0.1.223). Horizontal loads —
        seismic, water thrust, the horizontal part of a surface water
        load — do not appear, because they have no vertical component.

        Validated against the manual's own published column: EM Figure
        G-7b lists N for the twelve slices of its worked example and this
        expression reproduces it within the rounding of the table.

        v0.1.107 - the MIDDLE value is the mobilised shear and no longer
        travels to ``LEMResult.base_shear_force``, which is the driving force
        in every method now. It is kept because it is the quantity the
        recursion solved for, and it is reachable from outside as
        ``base_shear_strength / fos``.

        **Why this matters beyond reporting.** Until v0.1.98 only Bishop
        and Ordinary filled the base normal, and ``rapid_drawdown._stage1_
        state`` reads it to recover the stage-1 consolidation state. With
        an empty list the two-stage drawdown applied undrained strength to
        ZERO slices and silently degraded to a re-run of stage 1.
        """
        if ctx is None:
            return [], [], []
        alpha_n, theta, kh, kv, h_water, v_sup, t_act, t_pas = ctx
        t_sup = [t_act[i] + t_pas[i] / F for i in range(len(t_act))]
        zs = self._march(slist, theta, alpha_n, kh, kv, F,
                         h_water=h_water, v_support=v_sup,
                         t_support=t_sup)
        if zs is None:
            return [], [], []

        normals: list[float] = []
        shears: list[float] = []
        strengths: list[float] = []
        z_prev = 0.0
        # v0.1.223 (D222) -- the boundary inclinations ``_march`` used.
        theta_b = boundary_theta(theta)
        for i, s in enumerate(slist):
            alpha = alpha_n[i]
            th_prev, th = theta_b[i], theta_b[i + 1]
            W_eff = slice_forces(s, kh, kv).w_total - v_sup[i]
            l = max(s.base_length, 1e-9)
            u = s.pore_pressure
            sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / l
            imposed = self._imposed_stress(i)       # v0.1.213 (D84)
            if imposed is not None:
                sigma_est = max(0.0, imposed)
            c_loc, tan_phi = BishopSimplified._local_c_phi(
                s, s.material, sigma_est)
            a = tan_phi / F
            ca, sa = math.cos(alpha), math.sin(alpha)
            k0 = (c_loc * l - u * l * tan_phi) / F
            # The reinforcement, already mobilised: see the note above on why
            # a base-tangential force is exactly an addition to ``k0``.
            if t_sup[i]:
                k0 += t_sup[i]
            dz_v = zs[i] * math.sin(th) - z_prev * math.sin(th_prev)
            den = ca - a * sa
            N = (W_eff + dz_v + k0 * sa) / (den if abs(den) > 1e-9 else 1e-9)

            # Reported with its sign, exactly as Bishop does since
            # v0.1.96: clamping σ' at zero hands a base in tension the
            # full cohesion.
            sigma_eff = N / l - u
            c_rep, tan_phi_rep = BishopSimplified._local_c_phi(
                s, s.material, sigma_eff)
            tau = max(0.0, c_rep + sigma_eff * tan_phi_rep)
            normals.append(N)
            # The shear force that force equilibrium actually mobilises,
            # S = [c·l + (N − u·l)·tanφ]/F, and not the driving W·sinα
            # Bishop reports: for a force method this is the quantity
            # the recursion solved for.
            shears.append((c_rep * l + (N - u * l) * tan_phi_rep) / F)
            strengths.append(tau * l)
            z_prev = zs[i]
        return normals, shears, strengths

    # ==================================================================
    def _force_balance(
        self, slices: Slices, kh: float, kv: float, slide_sign: float,
        face_thrust=None, sup=None,
    ):
        """Root-find the Factor of Safety such that the inter-slice force
        recursion closes (``Z_n = 0``).

        The recursion uses the *true* signed base angles (the slide-sign
        flip used by the moment methods would destroy the active/passive
        structure the force recursion relies on). Two marching
        orientations are tried so the method is robust to either sliding
        direction; the first that produces a sign change in the end
        residual is used.

        Returns ``(fos, converged, iterations, ctx)``, where ``ctx`` is the
        marching context of the orientation that solved it, so the base
        forces can be recovered without guessing it again.
        """
        slist = list(slices)
        if not slist:
            return math.nan, False, 0, None
        ft = face_thrust if face_thrust else [0.0] * (len(slist) + 1)
        theta_true = self._theta_angles(slices)

        grid = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        total_iters = 0
        best_fallback = None  # (|residual|, F, ctx)

        for orient in (1.0, -1.0):
            alpha_n = [orient * s.base_angle for s in slist]
            theta = [orient * t for t in theta_true]
            # v0.1.61 — ``orient`` mirrors the geometry in x, so a
            # horizontal force signed in the true +x direction flips with
            # it. The seismic term needs no such factor because it is
            # already expressed as a magnitude along the marching sense.
            # Each slice also receives the NET water thrust of its two
            # vertical faces: the left face pushes it towards +x, the
            # right face towards −x.
            # v0.1.64 — the support's horizontal component is signed in
            # the true +x direction, exactly like the water thrust, so it
            # takes the same ``orient`` mirror.
            # v0.1.115 — and it is the NORMAL part only. The tangential part
            # is not a Cartesian load on the slice: it is reinforcement on
            # the base, so it goes to ``t_support`` and thence to ``k0``.
            has_sup = sup is not None and sup.present
            h_water = [
                orient * (slice_forces(s, kh, kv).h_water
                          + ft[i] - ft[i + 1]
                          + (sup.nf_h[i] if has_sup else 0.0))
                for i, s in enumerate(slist)
            ]
            v_sup = [(sup.nf_v[i] if has_sup else 0.0)
                     for i in range(len(slist))]
            # ACTIVE at face value, PASSIVE divided by the factor of safety.
            # The two are the reference's Eqn. 2 and Eqn. 4: ``F = R/(D − T)``
            # is ``D − T = R/F``, and ``F = (R+T)/D`` is ``D = R/F + T/F``,
            # so the only difference is whether the reinforcement is factored
            # alongside the soil strength. Duncan and Wright (2005) call them
            # Method A and Method B.
            t_act = [(sup.t_active[i] if has_sup else 0.0)
                     for i in range(len(slist))]
            t_pas = [(sup.t_passive[i] if has_sup else 0.0)
                     for i in range(len(slist))]
            ctx = (alpha_n, theta, kh, kv, h_water, v_sup, t_act, t_pas)

            def residual(F, alpha_n=alpha_n, theta=theta, hw=h_water,
                         vs=v_sup, ta=t_act, tp=t_pas):
                ts = [ta[i] + tp[i] / F for i in range(len(ta))]
                return self._z_end(slist, theta, alpha_n, kh, kv, F,
                                   h_water=hw, v_support=vs, t_support=ts)

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
                best_fallback = (abs(r_b), F_b, ctx)

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
            return F_mid, converged, total_iters, ctx

        # No bracket in either orientation — return nearest-residual F.
        if best_fallback is not None:
            return best_fallback[1], False, total_iters, best_fallback[2]
        return math.nan, False, total_iters, None


# ======================================================================
def _ground_angle(s) -> float:
    """Inclination of the ground surface over slice ``s`` (radians)."""
    return math.atan2(s.top_y_right - s.top_y_left, max(s.width, 1e-9))


# ======================================================================
@register_method
class CorpsOfEngineers1(PrescribedInclinationMethod):
    """Corps of Engineers #1 — Modified Swedish, side forces parallel to
    the line joining the two ends of the slip surface.

    Reference: USACE (1970), EM 1110-2-1902, "Stability of Earth and
    Rock-Fill Dams"; restated in USACE (2003), EM 1110-2-1902 §C-4a,
    where the assumption is described as side forces "parallel to the
    average embankment slope ... usually taken to be the slope of a
    straight line drawn between the crest and toe of the slope". All side
    forces have the same inclination.

    The crest and the toe here are the **entry and exit points of the slip
    surface**, which is how the assumption is drawn and implemented in
    practice, and which coincides with the crest-to-toe line whenever the
    surface daylights at both. The angle is taken from the first and last
    slice rather than from the surface object so that a tension crack,
    which truncates the sliding mass, moves the end with it.

    Since v0.1.224 (D223) a cracked end is the TOP of the crack, where the
    failure surface -- the slip surface and the crack -- meets the ground;
    it was the bottom, which is not on the ground at all. See
    ``CHORD_TO_CRACK_TOP``.
    """

    METHOD_ID = "corps_engineers_1"
    DISPLAY_NAME = "Corps of Engineers #1"

    def _theta_angles(self, slices: Slices) -> list[float]:
        slist = list(slices)
        if not slist:
            return []
        x0, y0 = slist[0].base_x_left, slist[0].base_y_left
        x1, y1 = slist[-1].base_x_right, slist[-1].base_y_right
        # v0.1.224 (D223) -- the end a tension crack closes is the top of
        # the crack. The wall travels with the slices; it is taken only at
        # the end it closes (a mass the crack did not truncate -- one of
        # two disjoint ones -- does not end there).
        wall = (getattr(slices, "tension_crack_wall", None)
                if CHORD_TO_CRACK_TOP else None)
        if wall is not None:
            x_wall, _y_bottom, y_top = wall
            tol = 1e-9 * max(abs(x1 - x0), 1.0)
            if abs(x_wall - x1) <= tol:
                y1 = y_top
            elif abs(x_wall - x0) <= tol:
                y0 = y_top
        dx = x1 - x0
        dy = y1 - y0
        # A vertical chord has no inclination to speak of; a slip surface
        # that degenerate is rejected upstream, and 0 keeps the recursion
        # finite instead of handing it a pole.
        theta = math.atan2(dy, dx) if abs(dx) > 1e-12 else 0.0
        return [theta] * len(slist)


# ======================================================================
@register_method
class CorpsOfEngineers2(PrescribedInclinationMethod):
    """Corps of Engineers #2 — Modified Swedish, side forces parallel to
    the ground surface above each slice.

    Unlike #1 the inclination VARIES from slice to slice, and it is zero
    wherever the ground surface is horizontal, so the inter-slice shear
    vanishes there. That consequence is the distinguishing mark of the
    assumption and is stated as such by Krahn (2004), whose table gives "inclination of ground surface at top of
    slice" for this variant against "inclination of a line from crest to
    toe" for #1.

    Not to be confused with the *average* embankment slope of USACE
    (2003) §C-4a, which is a single constant for the whole surface and is
    what #1 implements: the two coincide only on a slope of uniform
    inclination.

    The angle is the ground's over each slice; a boundary takes the average
    of its two slices (v0.1.223, D222), which is Duncan, Wright & Brandon's
    (2014) Fig. 6.14c -- "interslice force here is parallel to average
    slope here" -- and, where the ground has a vertex on the boundary, the
    bisector of its two sides.
    """

    METHOD_ID = "corps_engineers_2"
    DISPLAY_NAME = "Corps of Engineers #2"

    def _theta_angles(self, slices: Slices) -> list[float]:
        return [_ground_angle(s) for s in slices]
