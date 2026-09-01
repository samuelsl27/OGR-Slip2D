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

from ..external_forces import interslice_water_thrust, slice_forces
from ..slicer import Slices
from ..surface import SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method
from .bishop import BishopSimplified, driving_shear_forces

#: Accepted values of ``interslice_forces``.
EFFECTIVE_INTERSLICE = "effective"
TOTAL_INTERSLICE = "total"


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
        from ..support_integration import resolve_support_terms
        sup = resolve_support_terms(project, surface, slices, slide_sign)

        fos, converged, iters, ctx = self._force_balance(
            slices, kh, kv, slide_sign, face_thrust, sup,
        )

        if not (math.isfinite(fos) and fos > 0):
            return LEMResult(
                fos=math.nan, converged=False, iterations=iters,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                error_message=f"{self.DISPLAY_NAME}: force balance diverged",
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
            base_normal_force=normals,
            base_shear_force=driving,
            base_shear_strength=strengths,
            details={
                "boundary_ratios": self._boundary_ratios(slices),
                "interslice_forces": self.interslice_forces,
                "thrust_reversal": reversal,
            },
        )

    # ------------------------------------------------------------------
    def _boundary_ratios(self, slices: Slices) -> list[float]:
        """tan θ at each of the n+1 slice boundaries, in the raw frame.

        θ is defined per slice; interior boundary values average the two
        adjacent slices.
        """
        th = self._theta_angles(slices)
        if not th:
            return []
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
        right face, inclined at the prescribed angle ``θ_i`` to the
        horizontal. Eliminating the base normal ``N`` and the mobilised
        shear ``S = [c·l + (N − u·l)·tanφ]/F`` from the two force
        equilibrium equations of the slice gives the linear recursion

            Z_i = ( Z_{i-1}·D⁻ + const_i ) / D_i

        with
            a       = tanφ / F
            D_i     = cos(α_i − θ_i)   − a·sin(α_i − θ_i)
            D⁻      = cos(α_i − θ_{i-1}) − a·sin(α_i − θ_{i-1})
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
        theta_prev = theta[0] if theta else 0.0
        if h_water is None:
            h_water = [0.0] * len(slices_list)
        if v_support is None:
            v_support = [0.0] * len(slices_list)
        if t_support is None:
            t_support = [0.0] * len(slices_list)

        for s, alpha, th, hw, vs, ts in zip(slices_list, alpha_n, theta,
                                            h_water, v_support, t_support):
            # v0.1.61 — the ponded water rides in the vertical term (it is
            # a load the base has to carry) and its horizontal thrust joins
            # the seismic force in the horizontal slot. This is a
            # force-equilibrium method, so the point of application does
            # not enter: only the resultant does.
            # v0.1.64 — the support's vertical component joins the load
            # the base carries (``f_v`` is +y, ``W_eff`` is +down), so the
            # friction it mobilises comes out of the recursion itself.
            W_eff = slice_forces(s, kh, kv).w_total - vs
            l = s.base_length
            u = s.pore_pressure

            sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / max(l, 1e-9)
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

            const_i = (
                (kh * s.weight * (1.0 - kv) + hw - k0 * ca) * (ca - a * sa)
                - (W_eff + k0 * sa) * (sa + a * ca)
            )
            Z = (Z * D_prev + const_i) / D_i
            out.append(Z)
            theta_prev = th

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

        with ``ΔZ_v = Z_i·sinθ_i − Z_{i-1}·sinθ_{i-1}`` the net vertical
        component of the two inter-slice forces. Horizontal loads —
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
        th_prev = theta[0] if theta else 0.0
        for i, s in enumerate(slist):
            alpha = alpha_n[i]
            th = theta[i]
            W_eff = slice_forces(s, kh, kv).w_total - v_sup[i]
            l = max(s.base_length, 1e-9)
            u = s.pore_pressure
            sigma_est = max(0.0, W_eff * math.cos(alpha) - u * l) / l
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
            th_prev = th
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
    """

    METHOD_ID = "corps_engineers_1"
    DISPLAY_NAME = "Corps of Engineers #1"

    def _theta_angles(self, slices: Slices) -> list[float]:
        slist = list(slices)
        if not slist:
            return []
        dx = slist[-1].base_x_right - slist[0].base_x_left
        dy = slist[-1].base_y_right - slist[0].base_y_left
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
    assumption and is stated as such in Krahn's SLOPE/W formulation
    reference, whose table gives "inclination of ground surface at top of
    slice" for this variant against "inclination of a line from crest to
    toe" for #1.

    Not to be confused with the *average* embankment slope of USACE
    (2003) §C-4a, which is a single constant for the whole surface and is
    what #1 implements: the two coincide only on a slope of uniform
    inclination.
    """

    METHOD_ID = "corps_engineers_2"
    DISPLAY_NAME = "Corps of Engineers #2"

    def _theta_angles(self, slices: Slices) -> list[float]:
        return [_ground_angle(s) for s in slices]
