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
    x0_resisting_pass,
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
        slide_sign = slide_sense(slices, kh, kv)

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
                                          support_moments)
        sup = resolve_support_terms(project, surface, slices, slide_sign)
        s_list = slices.slices if hasattr(slices, "slices") else slices

        # v0.1.220 (D210) -- the driving side, without and with the Active
        # supports, and the Passive supports' term, from the one function
        # the back analysis also calls; see :func:`horizontal_driving_sum`
        # for the sec alpha weighting of the supports and why.
        (driving_no_support, denominator,
         t_active_sec, t_passive_sec) = horizontal_driving_sum(
            s_list, kh, kv, slide_sign, sup)
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
        support_force = None   # v0.1.221 (D212), as sigma_load
        # v0.1.213 (D84) -- the slices of the LAST pass that entered with no
        # strength because their estimate was clipped; see
        # ``BishopSimplified._zero_strength``.
        zero: list[int] = []
        imposed = self._imposed_reader()
        for it in range(1, self.max_iterations + 1):
            iterations = it
            # v0.1.220 (D210) -- the resisting sum at this F, from the one
            # function the back analysis also calls. The support is a LINE
            # LOAD on each slice, in the vertical equilibrium n_alpha comes
            # from (v0.1.142, as Bishop since v0.1.137). From v0.1.64 to
            # v0.1.141 a term ``T_N*tan phi'`` was also added raw, outside
            # the n_alpha normalisation; it is gone, because the friction a
            # support's normal component mobilises is whatever the slice's
            # own equilibrium yields, and adding it again outside would count
            # it twice with the wrong weight. What decided it was the
            # closed-form wedge, not the six published Clouterre planes: on
            # them the two Corps methods, Lowe-Karafiath and Ordinary all
            # reproduce the wedge to the last digit and leave a FLAT residual
            # against Sheahan's own column (-7.1 % to -8.2 %), the signature
            # of the nail geometry the manual does not publish, while the
            # combination that fit had a 4.3-point TREND across the same six
            # angles, the signature of a formulation error. See
            # ``tests/test_janbu_wedge_v1142.py`` and the header of
            # ``tests/test_support_projection_v1113.py``.
            pas = x0_resisting_pass(s_list, kh, kv, slide_sign, sup, fos,
                                    imposed, janbu=True)
            sigma_load, zero = pas.sigma_load, pas.zero
            support_force = pas.support_force
            if pas.collapsed is not None:
                return LEMResult(
                    fos=None,
                    converged=False,
                    iterations=iterations,
                    method_id=self.METHOD_ID,
                    surface=surface,
                    slices=slices,
                    reason=REASON_N_ALPHA_COLLAPSED,
                    error_message=f"nα collapsed at slice {pas.collapsed[0]}",
                )

            # v0.1.142 — sec alpha, for the reason given at the top:
            # a PASSIVE support mobilises at T_S/F alongside the base
            # shear, so it carries the same weighting the shear does.
            numerator = pas.total + t_passive_sec

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

        # v0.1.220 (D211) -- the factor of safety this equilibrium was solved
        # at, kept before the correction multiplies it: the per-slice state
        # below is formed at it. See ``STATE_AT_EQUILIBRIUM_FOS``.
        f_eq = fos
        correction = None
        if self._CORRECTION:
            # v0.1.214 (D80) -- ``b1`` from the soil type of the bases; see
            # :func:`janbu_correction`. Published below so the factor a
            # user reads can be traced to the curve it came from.
            f0, b1 = janbu_correction(slices)
            fos *= f0
            correction = {"janbu_b1": b1, "janbu_f0": f0}
        state_fos = f_eq if STATE_AT_EQUILIBRIUM_FOS else fos

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
        # v0.1.220 (D211) -- at the factor the equilibrium was SOLVED at,
        # F0, and not at the corrected f0*F0 as from v0.1.107 to v0.1.219.
        # The reason that choice gave, "these forces are reported against
        # the factor of safety that is reported", cost it Janbu's own
        # GLOBAL HORIZONTAL equilibrium, which f0 does not come from; at F0
        # Janbu Corrected's set is Janbu Simplified's and satisfies it. See
        # the block above ``STATE_AT_EQUILIBRIUM_FOS``.
        normals, shears, strengths = base_forces_no_interslice_shear(
            s_list, kh, kv, slide_sign, state_fos,
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
                # v0.1.221 (D212) -- the whole force of the support on each
                # slice, at the UNCORRECTED F of the last pass (the one its
                # state is formed at, D211), and its moment about the base
                # midpoint: read by the interslice march.
                "support_force": support_force,
                "support_moment": support_moments(sup, s_list),
                # v0.1.213 (D84) -- read by
                # ``analysis_runner.zero_strength_note``.
                "zero_strength_slices": zero,
                **(correction or {}),
                # v0.1.220 (D211) -- read by ``checks.equilibrium_fos``.
                **_equilibrium_keys(f_eq),
            }),
        )


@register_method
class JanbuCorrected(JanbuSimplified):
    METHOD_ID = "janbu_corrected"
    DISPLAY_NAME = "Janbu Corrected"
    _CORRECTION = True


# ----------------------------------------------------------------------
# v0.1.220 (D210) -- the sums of this method, written once for the solver and
# the back analysis; see the block above ``bishop.slide_sense``.


def slide_sense(slices, kh: float, kv: float) -> float:
    """Janbu's sense of sliding: the sign of ``sum W_total tan a``, ponded
    water inside ``W_total`` and ``tan`` weighting a steep base far more than
    Bishop's ``sin`` (the method D112 is about). Moved out of
    ``compute_fos`` so the back analysis asks this method for its own sense
    (v0.1.220, D210) instead of Bishop's."""
    driving_raw = sum(
        slice_forces(s, kh, kv).w_total * math.tan(s.base_angle)
        for s in slices
    )
    return 1.0 if driving_raw >= 0 else -1.0


def horizontal_driving_sum(slices, kh: float, kv: float, slide_sign: float,
                           sup) -> tuple[float, float, float, float]:
    """Janbu's driving side and its two support terms, as
    ``(driving without the Active supports, driving with them,
    Active term, Passive term)`` (v0.1.220, D210; moved out of
    ``compute_fos`` unchanged, bit for bit).

        driving = sum s*W_total*tan a + sum kh*W_soil - s*H_water
                  [- sum T_active*sec a]

    v0.1.142 — the support projection is weighted by sec alpha, which is
    the half v0.1.113 did not settle. Janbu balances SHEAR along the base:
    Sum S*sec a = Sum W*tan a. Putting an external force P = (P_h, P_v) on
    a slice into that balance gives

        Sum (W - P_v)*tan a  +  Sum P_h  =  Sum S*sec a

    and with T_S = slide_sign*(P_h*cos a + P_v*sin a) the whole of the
    support's contribution to the driving side is exactly -T_S*sec a, its
    normal part arriving through the slice's load in
    :func:`bishop.x0_resisting_pass`. Substituted into the form of this
    method on a PLANE the result cancels down to the closed-form Coulomb
    wedge, for Active and for Passive alike:

        Active   F = (c'L + (W cos a + T_N) tan phi') / (W sin a - T_S)
        Passive  F = (c'L + (W cos a + T_N) tan phi' + T_S) / (W sin a)

    which is not a convention: on a plane the sliding mass is one free body
    and the interslice forces cancel in the sum, so every method that closes
    global force equilibrium owes that number. The two Corps of Engineers,
    Lowe-Karafiath and Ordinary reproduce it to the last digit; until
    v0.1.142 Janbu missed it by +1.9 % at 35 deg and -20.0 % at 50 deg while
    being EXACT on the same planes with no support at all. See
    ``tests/test_janbu_wedge_v1142.py``.
    """
    s_list = slices.slices if hasattr(slices, "slices") else slices

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
    for s in s_list:
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
    return driving_no_support, denominator, t_active_sec, t_passive_sec


# ----------------------------------------------------------------------
# v0.1.220 (D211) -- Janbu Corrected forms its per-slice STATE at the factor
# its equilibrium is solved at, F0, not at the corrected F = f0*F0.
#
# WHAT WAS WRONG. The solver iterates on the uncorrected factor and
# multiplies by f0 at the end (Janbu 1973), and everything read afterwards --
# the stress a curved envelope is linearised at (D84), the columns, the
# m-alpha and tension checks, the interslice march, stage 1 of the multi-
# stage drawdown -- was formed at the corrected F: a state no pass solved.
# With a power curve the fixed point settled 2.4e-2 away from the stress the
# solver's own equilibrium resolves.
#
# WHAT DECIDED IT (the owner, 2026-09-29, after measuring side B -- only the
# envelope point and the back analysis at F0 -- and side C, all of it):
#
# * F0 is the factor OF THE SOLUTION: Duncan, Wright & Brandon (2014,
#   Fig. 6.13) write F = f0*F0 with "F0 = factor of safety from force
#   equilibrium solution with horizontal interslice forces", and the
#   reference documentation obtains the corrected factor "by multiplying the
#   Janbu Simplified safety factor for the surface" by f0. The correction is
#   an empirical adjustment of the NUMBER (Janbu compared his simplified and
#   generalized procedures on homogeneous slopes); it re-solves nothing.
# * the reference's two worked reports print the SAME count of every error
#   code for the two Janbu (Ej_1: 3264 valid, -112 91 in both; Ej_2: -112 146
#   in both). Only a state formed at F0 gives that identity: at the corrected
#   F this program counted 90 against 92 and 159 against 162.
# * the mobilised shear is the EQUILIBRIUM shear stress, tau = s/F, "the
#   shear stress required to maintain a just-stable slope" (Duncan, Wright &
#   Brandon 2014, §6.1, Eqs. 6.1-6.2): the F is the one the equilibrium
#   equations are solved with, and here that is F0. At F0 the published
#   normal and tau_f/F0 close each slice's vertical equilibrium and Janbu's
#   own horizontal balance; at f0*F0 they close neither, and s/(f0*F0) is the
#   equilibrium stress of no solution anyone computed.
#
# Measured on the verification bank: the 34 Janbu Corrected rows keep every
# factor and every critical surface; the -112 count moves in 14 of them and
# the published sigma'n_max of the critical in 32 (up to -4.8 %; none has a
# published value); problem 40, the one curved envelope, moves -0.0024 %.
#
# A module switch, like ``B1_BY_SOIL_TYPE``, so an A/B can rebuild the state
# at the corrected F and a test can demand that it moves (rule 7). Side B was
# measured and dropped: it read the envelope at F0 and checked it at F, which
# is incoherent by construction.
STATE_AT_EQUILIBRIUM_FOS = True


def _equilibrium_keys(f_eq: float) -> dict:
    """The ``details`` key that tells the readers of the state which F it was
    formed at (v0.1.220, D211): ``checks.equilibrium_fos`` reads it. Absent
    with the switch off, so every reader falls back to the reported F."""
    if STATE_AT_EQUILIBRIUM_FOS:
        return {"equilibrium_fos": f_eq}
    return {}


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
