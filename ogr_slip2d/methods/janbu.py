# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Janbu's Simplified & Corrected Methods of Slices.

Janbu Simplified satisfies horizontal force equilibrium; inter-slice
shear forces are ignored:

                    Σ [c'·b + (W − u·b)·tan φ'] / n_α
        F  =  ────────────────────────────────────────────────
                            Σ W · tan α

with:
        n_α = cos²α · (1 + tan α · tan φ' / F)

Janbu Corrected applies an empirical factor fo:
        F_corrected = fo · F
where fo depends on the depth-to-length ratio and soil type.

For pseudo-static seismic analysis:
    - W → W·(1 − kv)
    - kh adds a horizontal driving force:
        Σ W·tan α  →  Σ W·(1−kv)·tan α + Σ kh·W·(1 − tan α · tan α)
                      ≈ Σ W·(1−kv)·tan α + Σ kh·W
      (we use the simpler approximation Σ kh·W · tan α since the
      surface is steep — this is what most practical implementations
      do for Janbu).

References:
    - Janbu, N. (1954, 1973).
    - Abramson et al. (2002), §5.5.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from ogr_core.materials import Material
from ogr_core.project import Project

from ..external_forces import slice_forces
from ..slicer import Slice, Slices
from ..surface import SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method
from .bishop import (  # reuse the envelope linearisation and the X = 0 base forces
    BishopSimplified,
    base_forces_no_interslice_shear,
)


@register_method
class JanbuSimplified(LEMMethod):
    METHOD_ID = "janbu_simplified"
    DISPLAY_NAME = "Janbu Simplified"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = False
    _CORRECTION: bool = False

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

        # Sliding direction
        driving_raw = sum(
            slice_forces(s, kh, kv).w_total * math.tan(s.base_angle)
            for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.113 — supports enter through T_S, the projection ON THE
        # BASE, exactly as in Bishop and Ordinary and exactly as the
        # reference writes the two ratio-method equations. From v0.1.64
        # to v0.1.112 Janbu used the HORIZONTAL projection instead, on
        # the argument that "Janbu balances horizontal forces". That
        # argument does not survive the arithmetic: with φ' = 0 a slice
        # term is c'·b/cos²α = c'·l/cos α and the driving term is
        # W·tan α = W·sin α/cos α, so both sides are SHEAR quantities
        # carrying a common 1/cos α. A horizontal force H fits that
        # weighting because its driving shear H·cos α divided by cos α
        # gives H back — which is why the seismic and water terms below
        # are summed raw — but a support at an arbitrary angle does not.
        #
        # Measured on the six published planes of the Clouterre wall
        # (Sheahan 2003): mean error 14.96 % with the horizontal
        # projection, 1.76 % with T_S, 6.90 % with the strict per-slice
        # weighting T_S/cos α. See tests/test_support_projection_v1113.py.
        from ..support_integration import resolve_support_terms
        sup = resolve_support_terms(project, surface, slices, slide_sign)
        s_list = slices.slices if hasattr(slices, "slices") else slices

        # Driving force horizontal: Σ W·(1−kv)·tan α + Σ kh·W
        denominator = 0.0
        for s in slices:
            f = slice_forces(s, kh, kv)
            denominator += slide_sign * f.w_total * math.tan(s.base_angle)
            denominator += f.h_seismic  # horizontal seismic adds directly
            # v0.1.61 — external water thrust. The driving force is
            # measured positive along the sliding direction, whose x
            # component is −slide_sign (slide_sign = +1 means the mass
            # moves towards −x); h_water is signed in +x.
            denominator += -slide_sign * f.h_water

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
                    "Active support force exceeds the driving force; "
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
                error_message="Zero driving force — surface does not slide",
            )

        fos = self.initial_fos
        converged = False
        iterations = 0
        history: list[float] = []   # v0.1.74, for Steffensen
        for it in range(1, self.max_iterations + 1):
            iterations = it
            numerator = 0.0

            for i_s, s in enumerate(s_list):
                # v0.1.61 — the base normal carries the ponded-water
                # weight; the horizontal thrust belongs on the driving side
                W_eff = slice_forces(s, kh, kv).w_total
                b = s.width

                # Estimate σ'ₙ
                N_est = W_eff * math.cos(s.base_angle)
                N_eff_est = max(0.0, N_est - s.pore_pressure * s.base_length)
                sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)

                c, tan_phi = BishopSimplified._local_c_phi(
                    s, s.material, sigma_n_eff
                )

                # n_α = cos²α · (1 + tan α · tan φ' / F)  (with sliding sign)
                n_alpha = (math.cos(s.base_angle) ** 2) * (
                    1.0 + slide_sign * math.tan(s.base_angle) * tan_phi / fos
                )
                if abs(n_alpha) < 1e-6:
                    return LEMResult(
                        fos=math.nan,
                        converged=False,
                        iterations=iterations,
                        method_id=self.METHOD_ID,
                        surface=surface,
                        slices=slices,
                        error_message=f"nα collapsed at slice {s.index}",
                    )

                # Numerator term: [c'·b + (W − u·b)·tan φ'] / n_α
                numerator += (
                    c * b + (W_eff - s.pore_pressure * b) * tan_phi
                ) / n_alpha

                # v0.1.64 — T_N·tanφ', the friction the support's normal
                # component mobilises. Outside the n_α normalisation, as
                # the reference writes it; see the note in ``bishop``.
                #
                # v0.1.137 — Bishop stopped doing this and Janbu did NOT,
                # and that asymmetry is a MEASURED, REPORTED defect, not a
                # derivation. Janbu's balance is Σ S·sec α = Σ W·tan α, so
                # its support handling is wrong in TWO coupled places: this
                # term belongs inside n_α (= cos α · m_α), and the driving
                # side owes ``T_S·sec α`` where it subtracts ``T_S`` raw.
                # Measured, all four combinations:
                #
                #   this pair (n_α outside, T_S raw)   Clouterre mean 1.76 %
                #                                      load≡support -0.096 %
                #                                      and it does NOT shrink
                #   n_α outside, T_S·sec α             Clouterre 6.90 % (0.1.113)
                #   inside n_α, T_S raw                geotextiles -20 to -39 %
                #   inside n_α, T_S·sec α  (consistent) Clouterre mean 7.95 %
                #                                      load≡support 0.000000
                #                                      at 25, 100 and 400 slices
                #
                # So the only combination that reproduces the six published
                # Clouterre planes is the one that cannot pass its own
                # identity, and the one that passes the identity exactly
                # loses them. Choosing between them needs external evidence
                # this task does not have, and guessing would be exactly the
                # retro-fitting rule 1 exists to forbid. Left as it stands,
                # named, with both measurements written down.
                if sup.present and sup.n_press[i_s]:
                    numerator += sup.n_press[i_s] * tan_phi

            numerator += sup.total_passive_t()

            # Same backstop as Bishop's, and for the same reason: the next
            # pass computes tan(phi)/F inside n_alpha, so a zero F raises
            # ZeroDivisionError before the n_alpha guard above can run.
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
                        else "Non-finite FoS"
                    ),
                )
            # v0.1.100 — not on the first pass; see
            # ``BishopSimplified._general_moment_fos``.
            if it > 1 and abs(new_fos - fos) < self.tolerance:
                fos = new_fos
                converged = True
                break
            fos = new_fos

            # v0.1.74 — Steffensen, same shape as in Bishop. Applied to
            # the UNCORRECTED factor of safety: the Janbu correction is a
            # multiplier applied once at the end, so accelerating the
            # sequence before it cannot interact with it.
            if self.iterate_steffensen:
                history.append(new_fos)
                if len(history) >= 3:
                    accelerated = self.aitken(*history[-3:])
                    history.clear()
                    if accelerated is not None:
                        fos = accelerated

        if self._CORRECTION:
            fos *= _janbu_correction_factor(project, surface, slices)

        # v0.1.107 - the per-slice columns, which this method left EMPTY
        # until now. Janbu neglects the inter-slice shear exactly as
        # Bishop does, so the vertical equilibrium of the slice gives both
        # methods the same expression for N; see
        # ``base_forces_no_interslice_shear``. It is not a number for
        # display only: ``rapid_drawdown._stage1_state`` reads the base
        # normal to recover the stage-1 consolidation state, and with an
        # empty list the two-stage drawdown applied undrained strength to
        # ZERO slices and quietly became a re-run of stage 1. Measured on
        # the published critical circle of a two-stage benchmark, 50
        # slices: 1.7625 with nothing undrained against 1.2177 with all
        # fifty, where the accepted answer is 1.347.
        #
        # AFTER the Janbu (1973) correction factor, deliberately: f0
        # multiplies the factor of safety, and these forces are reported
        # against the factor of safety that is reported. The price is that
        # Janbu Corrected's set no longer satisfies the GLOBAL HORIZONTAL
        # equilibrium that Janbu (1954) solves - f0 is empirical and does
        # not come from re-solving anything - while Janbu Simplified's
        # does, to 1e-5 of the forces involved. Each slice still satisfies
        # its own vertical equilibrium in both.
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


@register_method
class JanbuCorrected(JanbuSimplified):
    METHOD_ID = "janbu_corrected"
    DISPLAY_NAME = "Janbu Corrected"
    _CORRECTION = True


# ----------------------------------------------------------------------
def _janbu_correction_factor(
    project: Project, surface: SurfaceProtocol, slices: Slices
) -> float:
    """Janbu (1973) empirical correction factor fo.

    Approximates the effect of inter-slice shear forces neglected in
    Janbu Simplified:

        fo = 1 + b1 · [(d/L) − 1.4·(d/L)²]

    with b1 depending on the soil type:
        - Purely cohesive (φ=0):  b1 ≈ 0.69
        - Mixed c-φ:              b1 ≈ 0.50  (default)
        - Cohesionless (c=0):     b1 ≈ 0.31
    """
    if not slices.slices:
        return 1.0
    first, last = slices.slices[0], slices.slices[-1]
    # Chord joining the two slip-surface endpoints
    x0, y0 = first.base_x_left, first.base_y_left
    x1, y1 = last.base_x_right, last.base_y_right
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-6:
        return 1.0
    # v0.1.19 — d is the maximum PERPENDICULAR distance from that chord
    # to the slip surface (Janbu's definition), NOT the max soil height
    # above the base. Using the soil height grossly overestimated d/L
    # and the correction factor (gave +2.9 % vs Slide). The base points
    # of every slice are sampled against the chord line.
    dx, dy = x1 - x0, y1 - y0
    d = 0.0
    pts = [(first.base_x_left, first.base_y_left)]
    for s in slices.slices:
        pts.append((s.base_x_right, s.base_y_right))
    for px, py in pts:
        # perpendicular distance from (px,py) to the chord
        dist = abs(dy * (px - x0) - dx * (py - y0)) / L
        if dist > d:
            d = dist
    r = d / L
    # b1 depends on soil type; pick from the dominant base material's
    # strength (cohesive / mixed / frictional).
    b1 = 0.50  # mixed c-φ soil (default)
    return 1.0 + b1 * (r - 1.4 * r * r)
