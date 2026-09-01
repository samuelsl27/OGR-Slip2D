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
        # weighting T_S/cos α — and on the strength of those three numbers
        # v0.1.113 kept T_S and recorded T_S/cos α as "four times worse".
        # That reading did not survive v0.1.142: it compared against ONE of
        # the manual's two published columns, and the manual's other column
        # — Sheahan's own — disagrees with the first by up to 4.7 %, which
        # is more than the gap being adjudicated. See below.
        from ..support_integration import (resolve_support_terms,
                                          support_vertical_load)
        sup = resolve_support_terms(project, surface, slices, slide_sign)
        s_list = slices.slices if hasattr(slices, "slices") else slices

        # v0.1.142 — and the projection is weighted by sec alpha, which is
        # the half v0.1.113 did not settle. Janbu balances SHEAR along the
        # base: Sum S*sec a = Sum W*tan a. Putting an external force
        # P = (P_h, P_v) on a slice into that balance gives
        #
        #     Sum (W - P_v)*tan a  +  Sum P_h  =  Sum S*sec a
        #
        # and with T_S = slide_sign*(P_h*cos a + P_v*sin a) the whole of the
        # support's contribution to the driving side is exactly -T_S*sec a,
        # its normal part arriving through W_eff below. Substituted into the
        # form of this method on a PLANE the result cancels down to the
        # closed-form Coulomb wedge, for Active and for Passive alike:
        #
        #     Active   F = (c'L + (W cos a + T_N) tan phi') / (W sin a - T_S)
        #     Passive  F = (c'L + (W cos a + T_N) tan phi' + T_S) / (W sin a)
        #
        # which is not a convention: on a plane the sliding mass is one free
        # body and the interslice forces cancel in the sum, so every method
        # that closes global force equilibrium owes that number. The two
        # Corps of Engineers, Lowe-Karafiath and Ordinary reproduce it to the
        # last digit; until this version Janbu missed it by +1.9 % at 35 deg
        # and -20.0 % at 50 deg while being EXACT on the same planes with no
        # support at all. See ``tests/test_janbu_wedge_v1142.py``.
        def _sec_weighted(column):
            """Sum of a per-slice support column, each term over cos alpha."""
            if not sup.present:
                return 0.0
            return math.fsum(
                t / max(math.cos(s.base_angle), 1e-9)
                for t, s in zip(column, s_list) if t
            )

        t_active_sec = _sec_weighted(sup.t_active)
        t_passive_sec = _sec_weighted(sup.t_passive)

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
        denominator -= t_active_sec
        active_ratio = (
            t_active_sec / driving_no_support
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
                # v0.1.142 — the support is a LINE LOAD on this slice, so it
                # joins the vertical equilibrium n_alpha comes from instead
                # of being bolted on outside it. Bishop made the same move in
                # v0.1.137; the two are the same statement, and the argument
                # for it is written at ``support_vertical_load``.
                if sup.present:
                    W_eff += support_vertical_load(
                        sup, i_s, s.base_angle, slide_sign, fos)
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

                # v0.1.64 to v0.1.141 a term ``T_N*tan phi'`` was added
                # here, raw, outside the n_alpha normalisation. It is gone:
                # the friction a support's normal component mobilises is
                # whatever this slice's own equilibrium yields from W_eff
                # above, and adding it again outside would be counting it
                # twice with the wrong weight.
                #
                # v0.1.141 measured four combinations of that term and the
                # driving projection and could not choose between them,
                # because the only external evidence in hand was the six
                # published Clouterre planes and the combination that fit
                # them was the one that failed its own load-equals-support
                # identity. The closed-form wedge is what decided it, and it
                # decided against the fit: on those same six planes the two
                # Corps methods, Lowe-Karafiath and Ordinary all reproduce
                # the wedge to the last digit, and the residual they leave
                # against Sheahan's own published column is FLAT (-7.1 % to
                # -8.2 %), which is the signature of the nail geometry the
                # manual does not publish. The combination that fit had a
                # 4.3-point TREND across the same six angles, which is the
                # signature of a formulation error. See
                # ``tests/test_janbu_wedge_v1142.py`` and the header of
                # ``tests/test_support_projection_v1113.py``.

            # v0.1.142 — sec alpha, for the reason given at the top:
            # a PASSIVE support mobilises at T_S/F alongside the base
            # shear, so it carries the same weighting the shear does.
            numerator += t_passive_sec

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
