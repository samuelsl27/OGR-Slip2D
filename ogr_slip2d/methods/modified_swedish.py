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
from .bishop import BishopSimplified

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
                 interslice_forces: str = EFFECTIVE_INTERSLICE,
                 **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # v0.1.98 — whether the resultant Z whose inclination is prescribed
        # is the EFFECTIVE inter-slice force (the water pressure on the
        # vertical faces separated out and applied as its own horizontal
        # load) or the TOTAL one. EM 1110-2-1902 §C-4a treats both as
        # legitimate and says the computed factor of safety differs
        # between them; it recommends effective forces for the Corps
        # assumption, while its OWN worked example in Appendix G uses
        # total forces "consistent with most computer software". The
        # choice is the user's, and it is the open question of D20.
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

        normals, shears, strengths = self._base_forces(
            list(slices), ctx, fos)

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iters,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
            details={
                "boundary_ratios": self._boundary_ratios(slices),
                "interslice_forces": self.interslice_forces,
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
               h_water=None, v_support=None):
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

        for s, alpha, th, hw, vs in zip(slices_list, alpha_n, theta,
                                        h_water, v_support):
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
               h_water=None, v_support=None) -> float:
        """Residual inter-slice force left at the down-slope free end.

        Thin wrapper over :meth:`_march`; kept as its own name because it
        is what the root finder reads and what the validation tests drive.
        """
        zs = self._march(slices_list, theta, alpha_n, kh, kv, F,
                         h_water=h_water, v_support=v_support)
        return math.nan if zs is None else zs[-1]

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

        **Why this matters beyond reporting.** Until v0.1.98 only Bishop
        and Ordinary filled ``base_normal``, and ``rapid_drawdown._stage1_
        state`` reads it to recover the stage-1 consolidation state. With
        an empty list the two-stage drawdown applied undrained strength to
        ZERO slices and silently degraded to a re-run of stage 1.
        """
        if ctx is None:
            return [], [], []
        alpha_n, theta, kh, kv, h_water, v_sup = ctx
        zs = self._march(slist, theta, alpha_n, kh, kv, F,
                         h_water=h_water, v_support=v_sup)
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
            has_sup = sup is not None and sup.present
            h_water = [
                orient * (slice_forces(s, kh, kv).h_water
                          + ft[i] - ft[i + 1]
                          + (sup.f_h[i] if has_sup else 0.0))
                for i, s in enumerate(slist)
            ]
            v_sup = [(sup.f_v[i] if has_sup else 0.0)
                     for i in range(len(slist))]
            ctx = (alpha_n, theta, kh, kv, h_water, v_sup)

            def residual(F, alpha_n=alpha_n, theta=theta, hw=h_water,
                         vs=v_sup):
                return self._z_end(slist, theta, alpha_n, kh, kv, F,
                                   h_water=hw, v_support=vs)

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
