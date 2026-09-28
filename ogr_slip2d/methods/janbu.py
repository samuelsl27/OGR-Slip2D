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

For pseudo-static seismic analysis, both inertial forces on the static
weight (Terzaghi 1950; Kramer 1996), with ``kv`` positive DOWN:
    - W → W·(1 + kv)
    - kh adds a horizontal driving force, unscaled:
        Σ W·tan α  →  Σ W·(1 + kv)·tan α + Σ kh·W
      That is exact, not an approximation: the balance is written in the
      horizontal direction, where ``kh·W`` enters as it stands, and on a
      plane it returns the pseudo-static Coulomb wedge to the last digit
      (``tests/test_seismic_convention_v1214.py``). Until v0.1.214 this
      docstring offered ``kh·W·(1 − tan²α)`` and an "approximation" the code
      never made, and the vertical factor was ``(1 − kv)`` (D170).

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
from .base import (
    REASON_ACTIVE_SUPPORT_EXCEEDS_DRIVING,
    REASON_N_ALPHA_COLLAPSED,
    REASON_NON_PHYSICAL_FOS,
    REASON_NOT_CONVERGED,
    REASON_ZERO_DRIVING,
    LEMMethod,
    LEMResult,
    register_method,
    self_consistent_envelope,
)
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
                                          support_failure_details,
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

        # Driving force horizontal: Σ W·(1+kv)·tan α + Σ kh·W
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
                fos=None,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                reason=REASON_ACTIVE_SUPPORT_EXCEEDS_DRIVING,
                admissible=False,
                admissibility_note=(
                    "Active support force exceeds the driving force; "
                    "the factor of safety is undefined for this surface"
                ),
            )

        if abs(denominator) < 1e-9:
            return LEMResult(
                fos=None,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                reason=REASON_ZERO_DRIVING,
                error_message="Zero driving force — surface does not slide",
            )

        fos = self.initial_fos
        converged = False
        iterations = 0
        history: list[float] = []   # v0.1.74, for Steffensen
        # v0.1.210 (D172) -- the support load of the LAST pass, as in
        # Bishop. Here F is the UNCORRECTED one: Janbu Corrected multiplies
        # by f0 only after the iteration, and a load taken at the corrected
        # F would be one no pass used (only a passive support depends on F).
        sigma_load = None
        # v0.1.213 (D84) -- the slices of the LAST pass that entered with no
        # strength because their estimate was clipped; see
        # ``BishopSimplified._zero_strength``.
        zero: list[int] = []
        for it in range(1, self.max_iterations + 1):
            iterations = it
            numerator = 0.0
            sigma_load = [0.0] * len(s_list) if sup.present else None
            zero = []

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
                    load = support_vertical_load(
                        sup, i_s, s.base_angle, slide_sign, fos)
                    W_eff += load
                    sigma_load[i_s] = load
                b = s.width

                # Estimate σ'ₙ
                N_est = W_eff * math.cos(s.base_angle)
                raw = N_est - s.pore_pressure * s.base_length
                N_eff_est = max(0.0, raw)
                sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)
                # v0.1.213 (D84) -- or where the method's own solution put
                # this base; see ``base.self_consistent_envelope``.
                imposed = self._imposed_stress(i_s)
                if imposed is not None:
                    raw, sigma_n_eff = imposed, max(0.0, imposed)

                c, tan_phi = BishopSimplified._local_c_phi(
                    s, s.material, sigma_n_eff
                )
                if raw < 0.0 and BishopSimplified._zero_strength(
                        s, raw, c, tan_phi):
                    zero.append(i_s)

                # n_α = cos²α · (1 + tan α · tan φ' / F)  (with sliding sign)
                n_alpha = (math.cos(s.base_angle) ** 2) * (
                    1.0 + slide_sign * math.tan(s.base_angle) * tan_phi / fos
                )
                if abs(n_alpha) < 1e-6:
                    return LEMResult(
                        fos=None,
                        converged=False,
                        iterations=iterations,
                        method_id=self.METHOD_ID,
                        surface=surface,
                        slices=slices,
                        reason=REASON_N_ALPHA_COLLAPSED,
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
                    fos=None,
                    converged=False,
                    iterations=iterations,
                    method_id=self.METHOD_ID,
                    surface=surface,
                    slices=slices,
                    reason=REASON_NON_PHYSICAL_FOS,
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

        correction = None
        if self._CORRECTION:
            # v0.1.214 (D80) -- ``b1`` from the soil type of the bases; see
            # :func:`janbu_correction`. Published below so the factor a
            # user reads can be traced to the curve it came from.
            f0, b1 = janbu_correction(slices)
            fos *= f0
            correction = {"janbu_b1": b1, "janbu_f0": f0}

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
                # v0.1.189 (D112), and THIS is the method that moves. Janbu
                # derives its sense from ``sign(sum w_total*tan a)`` --
                # ponded water inside ``w_total``, and ``tan`` weighting a
                # steep base far more than ``sin`` -- so it is the one
                # method whose sign the checks could not guess from
                # Bishop's sum. The key is well defined here even though
                # this method divides by ``n_alpha``, because
                # ``n_alpha == cos a * m_alpha`` exactly and ``cos a > 0``:
                # the two forms never differ in SIGN, only in size.
                "slide_sign": slide_sign,
                "m_alpha_sign": slide_sign,
                # v0.1.191 (D167) -- the vertical seismic coefficient this
                # method APPLIED, read by ``checks._applied_kv``: the same
                # ``kv`` handed to ``slice_forces``.
                # v0.1.214 (D173) -- and the horizontal one, so the
                # interslice march of the interpretation applies the
                # loads this method did (``compute_interslice_state``).
                "kh": kh,
                "kv": kv,
                # v0.1.210 (D172) -- read by ``checks._applied_support_load``;
                # None without a support.
                "sigma_support_load": sigma_load,
                # v0.1.213 (D84) -- read by
                # ``analysis_runner.zero_strength_note``.
                "zero_strength_slices": zero,
                **(correction or {}),
            }),
        )


@register_method
class JanbuCorrected(JanbuSimplified):
    METHOD_ID = "janbu_corrected"
    DISPLAY_NAME = "Janbu Corrected"
    _CORRECTION = True


# ----------------------------------------------------------------------
# v0.1.214 (D80) -- the ``b1`` of Janbu's correction follows the soil type.
#
# WHAT WAS WRONG. The docstring below offered three values, a comment told
# the reader to take the one of the material that dominates the base, and
# the code wrote ``b1 = 0.50`` always: a documented choice that was never
# made (rule 7).
#
# WHAT IT DOES. Janbu computed his curves for HOMOGENEOUS slopes, one per
# soil type; for a surface through several types the reference
# documentation takes the c-φ curve. So the type is read on EVERY base: one
# type throughout gives its own ``b1``, two or more give 0.50. Not the
# "dominant" material: measured on the 38 Janbu-corrected rows of the
# verification bank, the dominant type by base length or by slice area
# worsens five rows (006, 008, 009, 065, 074) that the all-bases rule
# leaves where they were, and the all-bases rule improves seven rows with a
# published value against one it worsens (050, a reinforced slope).
#
# A module switch, read at call time as ``base.ENVELOPE_AT_OWN_STRESS`` is,
# so an A/B can turn it off and a test can demand that it moves the number.
# Off, every surface gets 0.50, as before v0.1.214.
B1_BY_SOIL_TYPE = True

#: Janbu (1973): c only (φ = 0), φ only (c = 0), and c and φ.
JANBU_B1 = {"c": 0.69, "phi": 0.31, "c-phi": 0.50}

#: The stresses [kPa] an envelope with no Mohr-Coulomb parameters is read at
#: to tell its type: zero (is there strength with no normal stress?) and two
#: far apart to see whether it is flat. The low one is 10 and not 100 so
#: that a drained-undrained envelope, frictional at low stress and capped
#: above, is not read as flat.
_TYPE_PROBES = (0.0, 10.0, 200.0)


def base_soil_type(material) -> Optional[str]:
    """The soil type of Janbu's curves for one base material.

    ``"c"`` (strength independent of the normal stress: φ = 0),
    ``"phi"`` (no strength without normal stress: c = 0), ``"c-phi"``, or
    None for a base that has no type — no material, no strength at all, or
    infinite strength — which then does not take part in the choice.

    The classes that say what they are answer by their parameters: Mohr-
    Coulomb by its c and φ; the undrained models (constant, with depth, and
    SHANSEP) are φ = 0 by construction, and SHANSEP must be named because
    without its context it would read as φ only. So must Vertical Stress
    Ratio since v0.1.218 (D207): it reads the vertical stress of the slice,
    not σ'ₙ, so on a base its strength is a constant and the method reads
    it as a cohesion, while its context-free envelope (K·σ'ₙ, the stand-in
    for a caller with no slice) is a line through the origin that the probes
    below would call φ only. Every other envelope is
    classified by its SHAPE (decision of the owner, 2026-09-27): a curve
    through the origin is a frictional soil and gets the φ-only curve, not
    the c-φ one, which is 0.50 against 0.31 and the unsafe side (a power
    curve with c = d = 0, Barton-Bandis, a hyperbolic envelope).
    """
    from ogr_core.materials import (InfiniteStrength, MohrCoulomb,
                                    NoStrength, Undrained)
    from ogr_core.materials.builtin_models import (SHANSEP,
                                                   VerticalStressRatio,
                                                   _UndrainedLinearBase)
    if material is None:
        return None
    st = material.strength
    if isinstance(st, (NoStrength, InfiniteStrength)):
        return None
    if isinstance(st, (Undrained, SHANSEP, VerticalStressRatio,
                       _UndrainedLinearBase)):
        return "c"
    if isinstance(st, MohrCoulomb):
        c = float(st.params.get("cohesion", 0.0) or 0.0)
        phi = float(st.params.get("friction_angle", 0.0) or 0.0)
        if c > 0.0 and phi > 0.0:
            return "c-phi"
        if c > 0.0:
            return "c"
        if phi > 0.0:
            return "phi"
        return None
    try:
        t0, t1, t2 = (float(st.shear_strength(p)) for p in _TYPE_PROBES)
    except (ArithmeticError, ValueError):
        # An envelope that cannot be read at a probe keeps the c-φ curve,
        # which is what every surface got before v0.1.214.
        return "c-phi"
    if not all(math.isfinite(t) for t in (t0, t1, t2)):
        return None
    scale = max(1.0, abs(t2))
    if max(abs(t0), abs(t1), abs(t2)) <= 1e-12 * scale:
        return None                     # no strength at all
    if abs(t2 - t1) <= 1e-9 * scale:
        return "c"
    # 1e-6 and not 1e-12: a model may clamp the stress away from zero
    # before a logarithm (Barton-Bandis reads 1e-6 kPa) and still be a
    # curve through the origin.
    if abs(t0) <= 1e-6 * scale:
        return "phi"
    return "c-phi"


def janbu_correction(slices) -> tuple[float, float]:
    """Janbu (1973) empirical correction factor f0, and the ``b1`` used.

    Approximates the effect of the inter-slice shear forces that Janbu
    Simplified neglects:

        f0 = 1 + b1 · [(d/L) − 1.4·(d/L)²]

    with L the chord between the two ends of the slip surface and d the
    largest perpendicular distance from that chord to the surface. ``b1``
    is read off Janbu's curves for the soil type: 0.69 with c only, 0.31
    with φ only, 0.50 with c and φ. Janbu computed them for homogeneous
    slopes; a surface whose bases are of more than one type takes the c-φ
    value, the rule of the reference documentation (see the block above and
    :func:`base_soil_type`). With ``B1_BY_SOIL_TYPE`` off, 0.50 always.

    References:
        Janbu, N. (1973). "Slope stability computations." In Hirschfeld &
            Poulos (eds.), Embankment-Dam Engineering, Casagrande Volume,
            Wiley, 47-86.
        Abramson, L.W., Lee, T.S., Sharma, S. & Boyce, G.M. (2002). "Slope
            Stability and Stabilization Methods", 2nd ed., Wiley, §5.5.

    Takes the slices alone — a :class:`Slices` or a plain list — because
    the back analysis calls it with no project.
    """
    s_list = slices.slices if hasattr(slices, "slices") else list(slices)
    b1 = JANBU_B1["c-phi"]
    if B1_BY_SOIL_TYPE:
        kinds = {base_soil_type(s.material) for s in s_list} - {None}
        if len(kinds) == 1:
            b1 = JANBU_B1[kinds.pop()]
    if not s_list:
        return 1.0, b1
    first, last = s_list[0], s_list[-1]
    # Chord joining the two slip-surface endpoints
    x0, y0 = first.base_x_left, first.base_y_left
    x1, y1 = last.base_x_right, last.base_y_right
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-6:
        return 1.0, b1
    # v0.1.19 — d is the maximum PERPENDICULAR distance from that chord
    # to the slip surface (Janbu's definition), NOT the max soil height
    # above the base. Using the soil height grossly overestimated d/L
    # and the correction factor (gave +2.9 % against the reference). The base points
    # of every slice are sampled against the chord line.
    dx, dy = x1 - x0, y1 - y0
    d = 0.0
    pts = [(first.base_x_left, first.base_y_left)]
    for s in s_list:
        pts.append((s.base_x_right, s.base_y_right))
    for px, py in pts:
        # perpendicular distance from (px,py) to the chord
        dist = abs(dy * (px - x0) - dx * (py - y0)) / L
        if dist > d:
            d = dist
    r = d / L
    return 1.0 + b1 * (r - 1.4 * r * r), b1


def _janbu_correction_factor(
    project: Project, surface: SurfaceProtocol, slices: Slices
) -> float:
    """The factor f0 alone; see :func:`janbu_correction`.

    Kept under its old name for the back analysis, which calls it with
    ``project=None``: the soil type is read from the slices.
    """
    return janbu_correction(slices)[0]
