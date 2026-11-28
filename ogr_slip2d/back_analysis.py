# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Back Analysis of Support Force.

Determines the critical slip surface that requires the **maximum support
force** to reach a specified factor of safety — the natural starting
point for designing a support system.

How it works (following the reference specification):

* Rather than iterating to find the factor of safety, the factor of
  safety is **set to the user's target** and the force required to
  achieve it is solved for. Because the factor is fixed, the resisting
  sum can be evaluated directly and the force comes out in closed form —
  no iteration at all.
* The force is assumed **horizontal**, applied at a user-specified
  **elevation**.
* The force a surface needs depends on the elevation only with
  **Bishop**, because that method works from moment equilibrium and the
  elevation sets the moment arm. With **Janbu**, which considers only
  force equilibrium, a horizontal force enters the horizontal balance
  identically wherever it acts.
* **Two kinds of surface are not analysed** (v0.1.441, D418; both are the
  reference specification's, paraphrased). The ones whose factor of
  safety already reaches the target: they need no force. And the ones
  the force does not touch -- it acts where the slope is at its
  elevation, and a sliding mass whose top does not reach that elevation
  is not helped by it. So the elevation decides WHICH surfaces are
  analysed with either method, and a more local surface below the target
  may be left out: that is said, since the force found does nothing for
  it. With no surface left there is no force to report, and the reason
  is given instead of a force of zero.
* Only **Bishop, Janbu and Janbu Corrected** are supported; the method is
  not defined for the others.
* Of the surfaces the run analyses, the ones the user drew by hand
  included (v0.1.428, D396), every one that is neither of those two
  kinds is back-analysed, and the one needing the **largest** force is
  reported. Under the rule of the run's critical surface: an
  admissible one when there is any (a surface the post-analysis checks
  reject cannot be the critical surface, and so cannot govern the support
  either), and the one needing the most among them all, said, when the
  checks reject every surface, as ``SearchResult.critical`` falls back too.
* The force is computed under **both** the active and the passive
  assumption, and both are always reported.

The calculation is completely independent of the main stability
analysis: it neither uses nor alters its results.

Active vs passive
-----------------
An **active** force is treated as reducing the driving action (it is
applied to the sliding mass before failure, like a prestressed anchor),
whereas a **passive** force adds to the resistance (it mobilises only as
the mass moves, like an untensioned nail):

    active:   F = R / (D - T)   ->   T = D - R / F
    passive:  F = (R + T) / D   ->   T = F * D - R

with ``R`` the resisting sum evaluated at the target factor and ``D`` the
driving sum. The passive value is the larger of the two, so it is the
conservative one for design.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from . import run_messages as RM

SUPPORTED_METHODS = ("bishop_simplified", "janbu_simplified",
                     "janbu_corrected")


@dataclass
class BackAnalysisSurfaceResult:
    """Required support force for one slip surface."""

    surface: Optional[dict] = None
    active_force: float = math.nan
    passive_force: float = math.nan
    target_fos: float = 1.3
    # v0.1.428 (D396) -- whether it is a surface the user drew by hand; set
    # by the driver, read by the API and the window.
    user_defined: bool = False
    # Converged factor of safety WITHOUT the back-analysed force, filled in
    # by the driver from the real evaluation (see required_force). The name
    # is kept for the API. It has always carried the model's own supports,
    # being the search's own factor; since v0.1.220 (D210) the sums the
    # force is found from carry them too.
    unsupported_fos: float = math.nan
    notes: dict = field(default_factory=dict)

    @property
    def governing_force(self) -> float:
        """The larger (conservative) of the two assumptions."""
        vals = [v for v in (self.active_force, self.passive_force)
                if math.isfinite(v)]
        return max(vals) if vals else math.nan


@dataclass
class BackAnalysisResult:
    """Outcome for one analysis method."""

    method_id: str = ""
    target_fos: float = 1.3
    elevation: float = 0.0
    critical: Optional[BackAnalysisSurfaceResult] = None
    surfaces_analysed: int = 0
    # v0.1.441 (D418) -- the two kinds of surface the back analysis leaves
    # out, counted: the ones already at the target, and the ones below it
    # that the force does not touch. Not in ``surfaces_analysed``.
    surfaces_above_target: int = 0
    surfaces_untouched: int = 0
    # v0.1.516 (D467) -- and, with Bishop, the ones below the target whose
    # circle has its centre below the force (``ARM_ABOVE_CENTRE_REFUSED``).
    # Not in ``surfaces_analysed`` either.
    surfaces_above_centre: int = 0
    notes: dict = field(default_factory=dict)

    @property
    def required_force(self) -> float:
        return (self.critical.governing_force if self.critical
                else math.nan)

    def summary(self) -> dict:
        c = self.critical
        return {
            "method": self.method_id,
            "target_fos": self.target_fos,
            "elevation": self.elevation,
            "surfaces": self.surfaces_analysed,
            "surfaces_above_target": self.surfaces_above_target,
            "surfaces_untouched": self.surfaces_untouched,
            "surfaces_above_centre": self.surfaces_above_centre,
            "active_force": c.active_force if c else math.nan,
            "passive_force": c.passive_force if c else math.nan,
            "required_force": self.required_force,
            "unsupported_fos": c.unsupported_fos if c else math.nan,
        }


#: Why a surface was left out of the back analysis when a curved envelope
#: could not be read at the stress the method resolves (v0.1.215, D204).
#: v0.1.352 (D335): with its code; the sentence is ``run_messages``'.
ENVELOPE_NOT_SETTLED_NOTE = RM.run_note(RM.BACK_ENVELOPE)


class EnvelopeNotSettled(Exception):
    """A slice's envelope point did not converge (see ``_own_stress``)."""


class _NoOwnNormal(Exception):
    """``m_alpha`` vanished while finding a slice's own point: the surface
    is not back-analysed, as when the sum's own denominator vanishes."""


# v0.1.220 (D210) -- the two sums are the METHOD'S, asked of it
# (``bishop.circle_driving_sum``, ``janbu.horizontal_driving_sum`` and
# ``bishop.x0_resisting_pass``), supports included; see
# :func:`_sums_at_fixed_fos`. A module switch, like
# ``methods.base.ENVELOPE_AT_OWN_STRESS``, so an A/B can rebuild the sums
# the back analysis wrote by hand until v0.1.219 and a test can demand that
# it moves the number (rule 7).
LOADS_FROM_METHOD = True


def _own_stress(s, W, sigma, fos, sign):
    """The effective normal stress of one slice at ITS OWN fixed point:
    the stress at which the envelope, read there, gives a normal force
    whose stress is that same stress, with the factor of safety held at
    ``fos`` (v0.1.215, D204; see :func:`_sums_at_fixed_fos`).

    Starts from ``sigma`` (the Fellenius estimate) and iterates
    sigma -> (c, tan phi) at max(0, sigma) -> N(fos) -> N/l - u, with the
    tolerance and the pass limit of the methods' own fixed point. Returns
    the signed stress, or None when ``m_alpha`` vanishes (the surface is
    then not back-analysed, as before); raises :class:`EnvelopeNotSettled`
    when it does not converge.
    """
    from ogr_slip2d.checks import x0_base_normal
    from ogr_slip2d.methods import base as _base
    from ogr_slip2d.methods.bishop import BishopSimplified

    # The floor the stress the method reads is formed with
    # (``checks.base_effective_stresses``), not the 1e-9 of the estimate.
    l = max(s.base_length, 1e-12)
    u = s.pore_pressure
    for _ in range(_base.ENVELOPE_MAX_PASSES):
        c_loc, tan_phi = BishopSimplified._local_c_phi(
            s, s.material, max(0.0, sigma))
        N, _m = x0_base_normal(W, s.base_angle, l, u, c_loc, tan_phi, fos,
                               sign, m_floor=1e-6)
        if N is None:
            return None
        new = N / l - u
        if abs(new - sigma) / max(1.0, abs(new)) < _base.ENVELOPE_STRESS_TOL:
            return new
        sigma = new
    raise EnvelopeNotSettled


# ======================================================================
def _sums_at_fixed_fos(slices, surface, target_fos, kh, kv, elevation,
                       method_id, stress_fos=None, project=None):
    """Resisting and driving sums evaluated at a FIXED factor of safety.

    Returns ``(resisting, driving, arm)`` where ``arm`` converts a
    horizontal force into the same units as the driving term (a moment
    arm divided by the radius for Bishop, 1 for Janbu).

    WHERE A CURVED ENVELOPE IS READ (v0.1.215, D204). Each slice's
    envelope is replaced by its tangent, ``tau ~ c + sigma' tan phi``, and
    the point of tangency decides the resisting sum. Since v0.1.213 (D84)
    the methods read an envelope whose tangent depends on the stress at the
    stress THEY resolve, iterated to the fixed point
    (``methods.base.self_consistent_envelope``); this function still read
    it at the Fellenius estimate ``max(0, W cos a - u l)/l``. With
    Mohr-Coulomb the point does not matter. With a power curve or
    Hoek-Brown the two sums stopped being the same sum, and the identity
    that makes a back analysis mean anything broke: at the factor of safety
    the method gives a surface with no support, the force required is zero.
    Measured with Janbu, passive force before the clip at zero: -107.47
    kN/m on the archived critical surface of verification problem 41 (the
    unsafe side: above the method's own factor the force came out short by
    that much) and +2096 kN/m on the surface of
    ``test_zero_strength_slices_v1213``.

    Two ways out were weighed: iterate the point here, or refuse curved
    envelopes. This iterates, because here the fixed point is EXACT and
    local. The support force is horizontal. It enters Bishop's balance
    only through its moment and Janbu's only through the horizontal sum,
    and neither method lets it into a slice's VERTICAL equilibrium, which
    is where their normal comes from with no inter-slice shear (Bishop
    1955; Janbu 1954):

        N = [ W - s*(c*l*sin a - u*l*tan phi*sin a) / F ] / m_alpha.

    So with F held fixed the normal of a slice depends only on that
    slice's own (c, tan phi), and sigma' -> (c, tan phi) -> N(F) -> sigma'
    closes slice by slice, with no loop over the surface
    (:func:`_own_stress`). At the method's own factor it lands on the point
    the method's global iteration settled on. The normal is the checks'
    (``checks.x0_base_normal``), the very function the methods' fixed point
    reads, so the two cannot drift apart.

    WHICH F THE POINT IS FOUND AT: ``stress_fos``, default ``target_fos``.
    They differ only for Janbu Corrected. Its solver iterates on the
    UNCORRECTED factor and multiplies by Janbu's (1973) f0 at the end, so
    the sums below are formed at ``target/f0`` (v0.1.202). Until v0.1.219
    its fixed point read its stress at the CORRECTED factor, and the point
    that reproduced it was found at the corrected target (at target/f0 the
    stresses missed the method's ``envelope_stress`` by 2.4e-2 relative).
    Since v0.1.220 (D211) the method forms its whole state at the factor its
    equilibrium is solved at (``methods.janbu.STATE_AT_EQUILIBRIUM_FOS``),
    and ``required_force`` finds the point there too, at ``target/f0``.

    WHAT THE SUMS ARE (v0.1.220, D210): the METHOD'S, asked of it --
    ``bishop.circle_driving_sum`` or ``janbu.horizontal_driving_sum`` and
    ``bishop.x0_resisting_pass``, the very functions its solver iterates
    with -- so the loads, the arms and the sense of sliding cannot drift from
    it again. Rebuilt here by hand they had: no ponded water nor its thrust,
    ``sin a`` where Bishop takes ``weight_arm_ratio``, and Bishop's sense of
    sliding for Janbu too. Measured at the method's own factor on the 335
    archived surfaces of the verification bank, the force that must be zero
    came out above 1e-9 of the weight on 208 (up to 1.44 times the weight
    under a reservoir); with the method's sums, on none. The model's
    supports enter as the method applies them when ``project`` is given
    (decision of the owner, 2026-09-28): the force found is the one to ADD
    to the reinforcement already there. ``LOADS_FROM_METHOD`` off rebuilds
    the old sums (:func:`_sums_by_hand`), for an A/B.

    Unchanged, bit for bit: every envelope whose tangent does not depend
    on the stress (``methods.base._envelope_depends_on_stress``), so every
    Mohr-Coulomb back analysis; and everything with
    ``methods.base.ENVELOPE_AT_OWN_STRESS`` off, which is the switch the
    methods' own fixed point answers to, so an A/B that turns it off
    rebuilds the old reading on both sides at once.
    """
    if not LOADS_FROM_METHOD:
        return _sums_by_hand(slices, surface, target_fos, kh, kv, elevation,
                             method_id, stress_fos)
    from ogr_slip2d.methods import base as _base
    from ogr_slip2d.methods import bishop as _bishop
    from ogr_slip2d.methods import janbu as _janbu
    from ogr_slip2d.support_integration import resolve_support_terms
    from ogr_slip2d.surface import SlipCircle

    s_list = list(slices)
    if not s_list:
        return None
    if stress_fos is None:
        stress_fos = target_fos

    is_bishop = (method_id == "bishop_simplified")
    circle = surface if isinstance(surface, SlipCircle) else None
    if is_bishop and circle is None:
        return None

    # Each method's own sense of sliding: Bishop's from sum W(1+kv) sin a,
    # Janbu's from sum W_total tan a (D112). Until v0.1.219 both were
    # Bishop's.
    slide_sign = (_bishop.slide_sense(s_list, kv) if is_bishop
                  else _janbu.slide_sense(s_list, kh, kv))
    # The model's own reinforcement, as the method applies it; with no
    # project, none (``resolve_support_terms`` answers a model without
    # supports with the empty terms, which add nothing anywhere).
    sup = resolve_support_terms(project, surface, s_list, slide_sign)

    # Read at call time, like the methods read it, so a test or an A/B
    # that turns it off reaches this function too.
    imposed = None
    if _base.ENVELOPE_AT_OWN_STRESS:
        depends_cache: dict = {}

        def imposed(i, s, W, sigma):
            # v0.1.215 (D204) -- where the method reads it; see above.
            if not _base._envelope_depends_on_stress(s, depends_cache):
                return None
            own = _own_stress(s, W, sigma, stress_fos, slide_sign)
            if own is None:
                raise _NoOwnNormal
            return own

    try:
        if is_bishop:
            _free, driving = _bishop.circle_driving_sum(
                s_list, circle, kh, kv, slide_sign, sup)
            pas = _bishop.x0_resisting_pass(s_list, kh, kv, slide_sign, sup,
                                            target_fos, imposed)
            passive = sup.moment_passive
            # Moment of a horizontal force about the centre is
            # T·(y_c − y_T); dividing by R keeps it commensurate with the
            # driving sum, which is a moment over R.
            arm = (circle.centre_y - elevation) / max(circle.radius, 1e-9)
        else:
            _free, driving, _active, passive = _janbu.horizontal_driving_sum(
                s_list, kh, kv, slide_sign, sup)
            pas = _bishop.x0_resisting_pass(s_list, kh, kv, slide_sign, sup,
                                            target_fos, imposed, janbu=True)
            # Force equilibrium: a horizontal force enters directly, and
            # its elevation is irrelevant — exactly as the reference states.
            arm = 1.0
    except _NoOwnNormal:
        return None
    if pas.collapsed is not None:
        return None
    return pas.total + passive, driving, arm


def _sums_by_hand(slices, surface, target_fos, kh, kv, elevation, method_id,
                  stress_fos=None):
    """The two sums as the back analysis wrote them by hand until v0.1.219,
    kept only so that ``LOADS_FROM_METHOD`` off rebuilds them for an A/B
    (D210): the soil and its loads without the ponded water or its thrust,
    ``sin a`` as Bishop's weight arm, Bishop's sense of sliding for Janbu
    too, and no supports.
    """
    from ogr_slip2d.external_forces import (seismic_soil_part,
                                            seismic_vertical_load)
    from ogr_slip2d.methods import base as _base
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.surface import SlipCircle

    s_list = list(slices)
    if not s_list:
        return None
    if stress_fos is None:
        stress_fos = target_fos

    driving_raw = sum(seismic_vertical_load(s, kv)
                      * math.sin(s.base_angle) for s in s_list)
    slide_sign = 1.0 if driving_raw >= 0 else -1.0

    is_bishop = (method_id == "bishop_simplified")
    circle = surface if isinstance(surface, SlipCircle) else None
    if is_bishop and circle is None:
        return None

    # Read at call time, like the methods read it, so a test or an A/B
    # that turns it off reaches this function too.
    own_point = _base.ENVELOPE_AT_OWN_STRESS
    depends_cache: dict = {}

    resisting = 0.0
    driving = 0.0
    for s in s_list:
        # v0.1.214 (D170) -- the vertical load under ``kv`` positive DOWN,
        # and below the horizontal seismic force on the STATIC weight, as
        # the solvers apply them through ``slice_forces``. This wrote
        # ``W·(1 − kv)`` and ``kh·W·(1 − kv)`` by hand.
        #
        # v0.1.219 (D206) -- both on the SOIL only: the loads folded into
        # ``weight`` carry no seismic force, as in the solvers.
        W_eff = seismic_vertical_load(s, kv)
        b = s.width
        alpha = s.base_angle
        N_est = W_eff * math.cos(alpha)
        N_eff_est = max(0.0, N_est - s.pore_pressure * s.base_length)
        sigma = N_eff_est / max(s.base_length, 1e-9)
        if own_point and _base._envelope_depends_on_stress(s, depends_cache):
            # v0.1.215 (D204) -- where the method reads it; see above.
            own = _own_stress(s, W_eff, sigma, stress_fos, slide_sign)
            if own is None:
                return None
            sigma = max(0.0, own)
        c_loc, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                       sigma)
        m_alpha = math.cos(alpha) + (
            slide_sign * math.sin(alpha) * tan_phi / target_fos)
        if abs(m_alpha) < 1e-6:
            return None
        term = (c_loc * b + (W_eff - s.pore_pressure * b) * tan_phi) \
            / m_alpha

        if is_bishop:
            resisting += term
            driving += slide_sign * W_eff * math.sin(alpha)
            if kh:
                # v0.1.214 (D170) -- the arm the solver uses,
                # ``(y_c − y_g)/R``: the horizontal force of a slice below
                # the centre drives the rotation. This read
                # ``(y_g − y_c)``, so the earthquake REDUCED the driving sum
                # (4532 → 3093 on a 2:1 slope at kh = 0.1) and the force
                # needed at the method's own factor came out −7599 kN/m
                # where it is ~0 (Janbu, whose balance has no arm, was
                # right). See ``tests/test_seismic_convention_v1214.py``.
                y_g = 0.5 * (s.base_y_mid + s.top_y_mid) \
                    if hasattr(s, "top_y_mid") else s.base_y_mid
                driving += kh * seismic_soil_part(s) \
                    * (circle.centre_y - y_g) \
                    / max(circle.radius, 1e-9)
        else:
            # Janbu: horizontal force equilibrium. The solver divides each
            # term by n_alpha = cos²(alpha)·(1 + tan(alpha)·tan(phi)/F),
            # which is cos(alpha)·m_alpha; ``term`` is already over
            # m_alpha, so it is DIVIDED by cos(alpha) once more.
            #
            # v0.1.202 — this multiplied by cos(alpha): a factor cos²
            # (alpha) off the solver, on the unsafe side. Measured on a
            # 10 m slope: the back analysis said a surface needed 217 kN/m
            # to reach the factor of safety the solver gives it with no
            # support at all (1.39263), where the answer is 0.
            resisting += term / math.cos(alpha)
            driving += (slide_sign * W_eff * math.tan(alpha)
                        + kh * seismic_soil_part(s))

    if is_bishop:
        # Moment of a horizontal force about the centre is T·(y_c − y_T);
        # dividing by R keeps it commensurate with Σ W sin α.
        arm = (circle.centre_y - elevation) / max(circle.radius, 1e-9)
    else:
        # Force equilibrium: a horizontal force enters directly, and its
        # elevation is irrelevant — exactly as the reference states.
        arm = 1.0
    return resisting, driving, arm


def required_force(slices, surface, target_fos, method_id="bishop_simplified",
                   elevation=0.0, kh=0.0, kv=0.0, project=None
                   ) -> Optional[BackAnalysisSurfaceResult]:
    """Support force needed to bring ONE surface to ``target_fos``.

    Returns None when the surface cannot be evaluated, or when the
    geometry makes the force indeterminate (a Bishop force applied
    exactly at the centre elevation has no moment arm).

    ``project`` (v0.1.220, D210) is the model the slices were cut from, the
    FACTORED copy when a design standard is on: its supports enter the sums
    as the method applies them, so the force found is the one to ADD to the
    reinforcement already there. Without it no support is counted, which is
    right only for a model that has none.
    """
    if method_id not in SUPPORTED_METHODS:
        return None
    if not (math.isfinite(target_fos) and target_fos > 0):
        return None
    # v0.1.202 — Janbu Corrected iterates on the UNCORRECTED factor and
    # multiplies by Janbu's (1973) f0 at the end, so a corrected target F
    # is an uncorrected F/f0 inside the sums and in the force below. This
    # used the corrected target throughout: 269 kN/m "needed" where the
    # surface already stood at the target unsupported.
    f_eval = target_fos
    stress_fos = target_fos
    if method_id == "janbu_corrected":
        from types import SimpleNamespace

        from ogr_slip2d.methods import janbu as _janbu
        holder = (slices if hasattr(slices, "slices")
                  else SimpleNamespace(slices=list(slices)))
        f0 = _janbu._janbu_correction_factor(None, surface, holder)
        if not f0 > 0:
            return None
        f_eval = target_fos / f0
        # v0.1.220 (D211) -- the point is found where the method finds it,
        # at the factor its equilibrium is solved at (the switch that says
        # so is the method's own).
        if _janbu.STATE_AT_EQUILIBRIUM_FOS:
            stress_fos = f_eval
    surface_dict = (surface.to_dict() if hasattr(surface, "to_dict")
                    else None)
    try:
        # v0.1.215 (D204) -- a curved envelope is read at the stress the
        # method resolves, found at the factor its fixed point reads it at
        # (the target itself; see ``_sums_at_fixed_fos``).
        sums = _sums_at_fixed_fos(slices, surface, f_eval, kh, kv,
                                  elevation, method_id,
                                  stress_fos=stress_fos, project=project)
    except EnvelopeNotSettled:
        # No force rather than a force at a point the method never uses;
        # ``run_back_analysis`` counts these and says so.
        return BackAnalysisSurfaceResult(
            surface=surface_dict, target_fos=target_fos,
            notes={"envelope_not_settled": ENVELOPE_NOT_SETTLED_NOTE})
    if sums is None:
        return None
    resisting, driving, arm = sums
    if abs(arm) < 1e-9:
        return None
    # v0.1.516 (D467) -- a negative arm is Bishop's force ABOVE the centre of
    # the circle (Janbu's arm is 1). Its moment then turns the mass the way
    # it slides, and any force into the slope lowers both factors below:
    # R/(D + T·|arm|) and (R − T·|arm|)/D. No force into the slope can bring
    # the surface up to the target, and the count below gave a negative
    # force that the clip published as 0, «needs no support», for a surface
    # below the target (50 circles of bank problem 037 at target 1.5). See
    # ``ARM_ABOVE_CENTRE_REFUSED``.
    if arm < 0.0 and ARM_ABOVE_CENTRE_REFUSED:
        return BackAnalysisSurfaceResult(
            surface=surface_dict, target_fos=target_fos,
            notes={"above_centre": RM.run_note(
                RM.BACK_SURFACE_ABOVE_CENTRE, y=elevation,
                yc=float(getattr(surface, "centre_y", math.nan)))})

    res = BackAnalysisSurfaceResult(surface=surface_dict,
                                    target_fos=target_fos)
    # NOTE: the unsupported factor of safety is deliberately NOT derived
    # here. The resisting sum is evaluated at the TARGET factor (that is
    # the whole point of the method), so R/D would be one fixed-point
    # step away from the target rather than the converged answer — a
    # misleading number. ``run_back_analysis`` fills the field from the
    # search's own converged evaluation instead.

    # active:  F = R / (D - T·arm)   ->  T = (D - R/F) / arm
    res.active_force = (driving - resisting / f_eval) / arm
    # passive: F = (R + T·arm) / D   ->  T = (F·D - R) / arm
    res.passive_force = (f_eval * driving - resisting) / arm

    # A negative value means the surface already exceeds the target and
    # needs no support; report zero rather than a meaningless negative.
    if res.active_force < 0:
        res.active_force = 0.0
    if res.passive_force < 0:
        res.passive_force = 0.0
    return res


# v0.1.441 (D418) -- the two surfaces a back analysis does not analyse (see
# the module docstring). A module switch, read at call time like
# ``LOADS_FROM_METHOD``, so an A/B can rebuild the back analysis that
# analysed every surface (until v0.1.440) and a test can demand that the
# screens move the answer.
REFERENCE_SCREENS = True

#: v0.1.516 (D467) -- with Bishop, a surface whose circle has its centre
#: below the force is left out with its note (the owner's decision of
#: 2026-11-28, of three: leave it out, give the force with its sign, or
#: keep the 0 and warn). The rule is the sign of the arm, geometric and
#: exact: no factor is read. A module switch, read at call time, so an A/B
#: can rebuild the clip to 0 of until v0.1.515 and a test can demand that
#: the rule moves the answer.
ARM_ABOVE_CENTRE_REFUSED = True


def model_of_slices(project):
    """The model the slices of a run of ``project`` were computed on, as
    the supports have to read it (v0.1.494, D432).

    ``project`` itself, unless it asks for a rapid drawdown: then the model
    at the drawn-down level, ``level_project(project, use_drawdown=True)``
    (Duncan, Wright & Wong 1990; the same call the procedures make). Every
    procedure publishes the slices of its drawn-down stage -- the second
    stage of Lowe-Karafiath, the capped last pass of Duncan-Wright-Wong and
    of Corps 2, and B-bar's one pass -- and computes the support forces of
    those slices on that model. A support whose capacity is read from the
    soil (a geosynthetic in coefficient mode, Jewell 1996, and every type
    with a bond profile) reads the effective vertical stress, and with it
    the water: at the initial level it is another force. Measured on the
    Pilarcitos embankment of ``test_rapid_drawdown_v168`` with a sheet in
    coefficient mode between the two levels: the force of D210's identity
    was +0.173 of the weight with the model as drawn, 0 (to 1e-14) with this
    one, under all four procedures, Janbu and Bishop; and at a target of
    1.1 F a passive force 3.2 times the one the computed model asks for.

    ``project`` is the model the run was given -- the factored copy under
    a design standard (D210) -- and is never modified. Only the water
    moves, so the ground the screens of D418 read is the same in both.
    """
    gw = getattr(getattr(project, "settings", None), "groundwater", None)
    if gw is None or not getattr(gw, "rapid_drawdown", False):
        return project
    from .rapid_drawdown import level_project
    return level_project(project, use_drawdown=True)


def ground_of(project):
    """The ground profile the tops of the slices lie on, or None for a
    model without an external boundary. Found once per run and handed to
    :func:`mass_top_range`."""
    from ogr_core.geometry.ground import ground_surface
    external = project.external_boundary() if project is not None else None
    return ground_surface(external) if external is not None else None


def mass_top_range(slices, ground=None) -> Optional[tuple]:
    """``(lowest, highest)`` elevation of the TOP of a sliding mass: of the
    ground between its two ends (v0.1.441, D418).

    The top of every slice lies on the ground, so its range is that of the
    ground profile between the first and the last slice: the elevations at
    the slice edges and, with ``ground``, those of the profile's vertices
    that fall between the two ends. The vertices are not optional: the
    slicer cuts where the slip surface changes layer or direction, not at
    the ground's vertices, so a berm or a crest inside one slice is in no
    slice edge. A mass clipped by a tension crack ends at the crack, and
    its top is the ground up to there.

    And the mass's own VERTICAL face, where it has one. A surface that
    leaves the ground through the face of a wall or a vertical cut ends at
    the wall's abscissa with its base part-way up: the stretch of the face
    from there to the crest is the free surface of that mass, and a force
    on it touches it. The two vertices of the step share the end's
    abscissa and are not "between the ends", so the end of the BASE is
    taken too when it lies on the ground (the review of 0.1.441: read
    without it, a force on the face of a vertical cut touched no mass, and
    a face one millimetre off the vertical all of them). The bottom of a
    tension crack is not on the ground, and is not taken.
    """
    sl = list(slices)
    if not sl:
        return None
    first = min(sl, key=lambda s: s.base_x_left)
    last = max(sl, key=lambda s: s.base_x_right)
    x_l, x_r = first.base_x_left, last.base_x_right
    heights = [s.top_y_left for s in sl] + [s.top_y_right for s in sl]
    if ground is not None:
        from ogr_core.geometry.ground import envelope_y_at
        heights += [v.y for v in ground.vertices if x_l < v.x < x_r]
        for x, base_y in ((x_l, getattr(first, "base_y_left", None)),
                          (x_r, getattr(last, "base_y_right", None))):
            if base_y is None:
                continue
            here = [h for h in (envelope_y_at(ground, x),
                                envelope_y_at(ground, x, side=-1),
                                envelope_y_at(ground, x, side=1),
                                envelope_y_at(ground, x, upper=False))
                    if h is not None]
            if here:
                tol = 1e-9 * max(abs(min(here)), abs(max(here)), 1.0)
                if min(here) - tol <= base_y <= max(here) + tol:
                    heights.append(base_y)
    return min(heights), max(heights)


def force_touches(top_range, elevation) -> bool:
    """Whether a horizontal force at ``elevation`` is applied ON the sliding
    mass: the point of the slope at that elevation lies on the top of the
    mass, i.e. the elevation is within the range of that top (the owner's
    decision of 2026-11-12, of the two readings of "in contact with the
    mass"). The ends are in; the tolerance is relative to the elevations,
    for the last bits of an interpolated ground height.

    The other reading -- the line of action crosses the mass anywhere, down
    to its base -- also takes a mass the force would only reach below the
    ground. The two were measured side by side on the reference slope, the
    demo and the bench's problem 37 before this was written and never
    differed there: a circle leaves the ground where its base does.
    """
    lo, hi = top_range
    tol = 1e-9 * max(abs(lo), abs(hi), hi - lo)
    return lo - tol <= elevation <= hi + tol


def required_force_of_result(result, target_fos, elevation, project,
                             method_id=None
                             ) -> Optional[BackAnalysisSurfaceResult]:
    """Support force needed to bring the surface of ONE computed result to
    ``target_fos`` (v0.1.440, D419).

    A count made on a result reads the result. The slices and the surface
    are the run's, and so are the seismic coefficients: ``details["kh"]``
    and ``details["kv"]``, what the method APPLIED (0 with the earthquake
    off, and with the seismic factor of a design standard already in them),
    as the free body reads them since v0.1.214 (D173). The method is the
    result's own unless ``method_id`` names another.

    ``project`` is the model the result was computed on -- the factored
    copy when a design standard is on (``prepare_analysis_project``). Its
    supports are what is read (see :func:`required_force`), and through a
    support whatever that support reads of the model: a sheet whose
    pull-out is a fraction of the soil's strength reads the materials, the
    water and the loads around it, which is why the factored copy and the
    project as drawn do not price it alike. The caller answers for it
    being that model: a result does not carry the supports it was computed
    with, only their forces slice by slice at the method's own factor,
    which cannot be read at another one. Under a rapid drawdown the supports
    are read at the drawn-down level, the one the slices were computed at
    (:func:`model_of_slices`, v0.1.494, D432): the caller still hands over
    the model of the run, and the rule is the engine's, as in the run.

    Until this version the interpretation window passed the run's slices
    with the coefficients and the supports of the project AS IT IS NOW:
    258.49 kN/m where the run's data give 145.99 after raising kh to 0.1,
    36.42 after adding a nail, and 258.49 against 314.73 with nothing
    changed at all under a standard whose seismic factor is 1.5.

    What checks it is an identity (Bishop 1955; Janbu 1954): at the
    result's own factor of safety, with the data it was computed with, the
    force is zero.
    """
    # The slices as the result holds them: the ones a large run left in its
    # store (``SpilledSlices``) read back as they are walked.
    slices = getattr(result, "slices", None)
    if not slices:
        return None
    details = getattr(result, "details", None) or {}
    # Read as ``postprocess.compute_interslice_state`` reads them: a result
    # built by hand, without them, had no earthquake.
    kh = float(details.get("kh", 0.0) or 0.0)
    kv = float(details.get("kv", 0.0) or 0.0)
    if method_id is None:
        method_id = getattr(result, "method_id", None)
    # v0.1.494 (D432) -- the supports read at the level the slices were
    # computed on: the drawn-down one under a rapid drawdown
    r = required_force(slices, result.surface, target_fos, method_id,
                       elevation, kh, kv, project=model_of_slices(project))
    # v0.1.516 (D467) -- a force above the centre (``above_centre``) is
    # judged after the two screens, as the run judges it: a surface already
    # at the target needs nothing, and one the force does not touch is said
    # to be that, whatever the arm.
    if (r is None or (r.notes and "above_centre" not in r.notes)
            or not REFERENCE_SCREENS):
        # What the method cannot price is said first, as the run says it
        # (Bishop and a surface that is not a circle, an envelope that did
        # not settle); the two screens are for a surface it can price.
        return r
    # v0.1.441 (D418) -- the run's two screens, for the one surface a window
    # prices (the owner's decision: one rule for both). It printed "active:
    # 0.00, passive: 0.00" for a surface already above the target, and a
    # force for one the force does not touch.
    fos = getattr(result, "fos", None)
    if fos is not None and fos >= target_fos:
        return BackAnalysisSurfaceResult(
            surface=r.surface, target_fos=target_fos,
            notes={"above_target": RM.run_note(
                RM.BACK_SURFACE_ABOVE_TARGET, factor=fos)})
    top = mass_top_range(slices, ground_of(project))
    if top is not None and not force_touches(top, elevation):
        return BackAnalysisSurfaceResult(
            surface=r.surface, target_fos=target_fos,
            notes={"untouched": RM.run_note(
                RM.BACK_SURFACE_UNTOUCHED, y=elevation, lo=top[0],
                hi=top[1])})
    return r


# ======================================================================
def run_back_analysis(project, search, target_fos=1.3, elevation=0.0,
                      method_id="bishop_simplified",
                      progress_cb=None) -> BackAnalysisResult:
    """Back-analyse the surfaces of a run that are below the target and
    that the force touches, and report the one needing the largest support
    force.

    ``search`` is a configured search object; its surfaces are
    regenerated and each of those is back-analysed. The main stability
    results are neither used nor modified. The slicing is the search's own.

    v0.1.441 (D418) -- "below the target and that the force touches": until
    this version every valid surface was priced. One whose factor already
    reaches the target needs no force (``surfaces_above_target``), and one
    whose sliding mass the force does not touch is not helped by it
    (``surfaces_untouched``, :func:`force_touches`); neither counts in
    ``surfaces_analysed``. The second kind is always said: those surfaces
    stay below the target. With none left there is no force, and
    ``notes["error"]`` is the reason instead of a force of zero on the
    first surface of the list.

    v0.1.428 (D396) -- "every surface a run analyses": the user's surfaces
    too, which the run analyses after the search and may report as its
    critical one. Until this version only the search population was read,
    so with a hand-drawn polyline critical the force of ANOTHER surface was
    published, on the unsafe side (190.99 against 259.02 kN/m on the demo
    slope, Janbu). And with the same rule as the run's critical surface:
    an inadmissible surface cannot govern while an admissible one is there
    (one rule for every surface, the owner's decision), said only when it
    would have; when the checks reject every surface, the one needing the
    most among them governs and that is said, as ``SearchResult.critical``
    falls back to all of them. A surface Bishop cannot back-analyse (not a
    circle) is left out and said, not counted as analysed.

    v0.1.263 (with D248) — the ``num_slices=25`` parameter is gone. It was
    never read: the slices come from ``search``, and a setting that does not
    reach the number is worse than none (rule 7). A caller that still
    passes it gets a TypeError that says so, instead of a result that
    ignores it.
    """
    out = BackAnalysisResult(method_id=method_id, target_fos=target_fos,
                             elevation=elevation)
    if method_id not in SUPPORTED_METHODS:
        out.notes["error"] = RM.run_note(
            RM.BACK_ONLY_FOR, methods=", ".join(SUPPORTED_METHODS))
        return out
    if not (math.isfinite(target_fos) and target_fos > 0):
        out.notes["error"] = RM.run_note(RM.BACK_TARGET_POSITIVE)
        return out

    from .search import all_evaluations_of, is_user_surface_of
    from .surface import CompositeSurface, SlipCircle

    kh = project.seismic.kh if project.seismic.enabled else 0.0
    kv = project.seismic.kv if project.seismic.enabled else 0.0

    # v0.1.408 (D383) — the population is read once, in order, and thrown
    # away: a large grid spills it as a Compute does, and it comes back one
    # surface at a time below. The search keeps no store afterwards.
    from .slice_store import SliceStore, SpilledSlices, wants_store
    own_store = (getattr(search, "slice_store", None) is None
                 and wants_store(search))
    if own_store:
        search.slice_store = SliceStore()
    try:
        run = search.run(project)
    except Exception as exc:  # noqa: BLE001
        out.notes["error"] = RM.run_note(RM.BACK_SEARCH_FAILED,
                                         error=str(exc))
        return out
    finally:
        if own_store:
            search.slice_store = None

    best = None
    population = all_evaluations_of(run)
    total = len(population)
    # v0.1.111 — composite surfaces are COUNTED and reported, not passed
    # over. ``required_force`` writes Bishop in its circular form, which
    # assumes every base normal points at the centre and every moment arm
    # is R; on the straight stretch of a composite neither holds, so it
    # answers None rather than a plausible wrong number. That is the right
    # refusal, but a silent one would be worse than the defect this version
    # fixes: with Composite Surfaces enabled the back-analysis would report
    # a governing force drawn from a population it never says it shrank.
    n_composite = 0
    n_unsettled = 0
    # v0.1.428 (D396) -- Bishop is written about a circle's centre, and a
    # polyline or a surface a weak layer clipped has none: priced None,
    # these were counted as analysed and the result said "no surface could
    # be back-analysed" without the reason. Counted apart now, like the
    # composite ones above.
    n_not_circle = 0
    is_bishop = method_id == "bishop_simplified"
    # v0.1.441 (D418) -- the two surfaces a back analysis does not analyse,
    # counted apart like the ones above and said. One that already reaches
    # the target needs no force: it was priced, clipped to zero, and with
    # every surface above the target a force of 0 kN/m was published on the
    # first of the list as the governing one. One the force does not touch
    # cannot be helped by it: with the force above the crest Bishop
    # published 228 and 548 kN/m on the demo slope, growing with the arm.
    screens = REFERENCE_SCREENS
    ground = ground_of(project) if screens else None
    # v0.1.494 (D432) -- once, for every surface: the model the supports
    # are read on, the drawn-down one under a rapid drawdown
    priced_on = model_of_slices(project)
    n_above = 0
    untouched = []          # the top range of each one left out
    n_above_centre = 0      # v0.1.516 (D467)
    # The inadmissible surfaces, with their forces: to say whether one of
    # them would have governed (a screen that changed the answer is said;
    # one that did not is not noise worth a note on every run), and to fall
    # back on them when they are all there is, as ``critical`` does.
    rejected = []
    for i, ev in enumerate(population):
        # v0.1.441 (D418, its review) -- first, for every surface: this was
        # the last line of the loop, which the surfaces left out never
        # reach. With the two screens most of a population is left out,
        # and with the force touching none the bar stood still and Cancel,
        # which comes in through this call, could not.
        if progress_cb and i % 20 == 0:
            progress_cb(i, total)
        if not ev.is_valid or not ev.slices:
            continue
        if isinstance(ev.surface, CompositeSurface):
            n_composite += 1
            continue
        if is_bishop and not isinstance(ev.surface, SlipCircle):
            n_not_circle += 1
            continue
        # At or above the target: "below" is the reference's word, and a
        # surface exactly at the target needs nothing either. Asked before
        # its slices are read back from the store.
        if screens and ev.fos >= target_fos:
            n_above += 1
            continue
        slices = ev.slices
        if type(slices) is SpilledSlices:
            slices = slices.materialize()
        if screens:
            top = mass_top_range(slices, ground)
            if top is not None and not force_touches(top, elevation):
                untouched.append(top)
                continue
        # v0.1.516 (D467) -- with Bishop, the force above the centre of the
        # circle cannot raise its factor: left out and counted, before it is
        # priced, by the same sign ``required_force`` reads (arm < 0).
        if (is_bishop and ARM_ABOVE_CENTRE_REFUSED
                and elevation > ev.surface.centre_y):
            n_above_centre += 1
            continue
        r = required_force(slices, ev.surface, target_fos, method_id,
                           elevation, kh, kv, project=priced_on)
        out.surfaces_analysed += 1
        if r is None:
            continue
        # v0.1.215 (D204) -- counted, for the same reason composite
        # surfaces are: a population shrunk in silence is a wrong answer.
        if r.notes.get("envelope_not_settled"):
            n_unsettled += 1
            continue
        # The converged, unsupported factor comes from the evaluation
        # itself — the only place it is actually known.
        r.unsupported_fos = ev.fos
        # v0.1.152 (D56) — ``governing_force`` is NaN when neither
        # assumption produced a finite force, and a NaN loses every
        # comparison it takes part in. So a NaN reaching ``best`` first
        # would stay there for the rest of the run: every later candidate
        # asks ``x > nan``, which is False, and the report would publish a
        # required force of NaN with no note at all — the "No surface could
        # be back-analysed" message below only fires on ``best is None``.
        # It is the same defect as D56 one level up, and it is closed the
        # same way: a candidate with no number is not a candidate.
        if not math.isfinite(r.governing_force):
            continue
        if not getattr(ev, "admissible", True):
            rejected.append((r, ev))
            continue
        r.user_defined = is_user_surface_of(run, ev)
        if best is None or r.governing_force > best.governing_force:
            best = r

    if best is None and rejected:
        # Every candidate is inadmissible: the run's critical surface is then
        # one of them (``SearchResult.critical``: "the checks are ignored
        # rather than returning nothing"), and so is the back analysis'.
        best, ev_best = max(rejected, key=lambda t: t[0].governing_force)
        best.user_defined = is_user_surface_of(run, ev_best)
        out.notes["all_inadmissible"] = RM.run_note(RM.BACK_ALL_INADMISSIBLE)
    elif best is not None:
        above = [r for r, _ev in rejected
                 if r.governing_force > best.governing_force]
        if above:
            out.notes["inadmissible_governed"] = RM.run_note(
                RM.BACK_INADMISSIBLE_GOVERNED, n=len(above))
    out.critical = best
    if n_composite:
        out.notes["composite_skipped"] = RM.run_note(
            RM.BACK_COMPOSITE_LEFT_OUT, n=n_composite)
    if n_unsettled:
        out.notes["envelope_not_settled"] = RM.run_note(
            RM.BACK_ENVELOPE_LEFT_OUT, n=n_unsettled)
    if n_not_circle:
        out.notes["not_circular_skipped"] = RM.run_note(
            RM.BACK_NOT_CIRCULAR_LEFT_OUT, n=n_not_circle)
    if best is not None and best.user_defined:
        out.notes["user_governs"] = RM.run_note(RM.BACK_USER_GOVERNS)
    # v0.1.441 (D418) -- the two screens. When they leave nothing to price,
    # the count IS the reason (one note, the same object under both keys:
    # the window says the error and then every other note). The surfaces
    # the force does not touch come first: they are below the target and
    # stay there, which is what the user has to know.
    #
    # The ones already at the target are counted and NOT said while there is
    # a force to publish: leaving them out does not change it (they needed
    # none), nearly every run has some, and a run with nothing to warn of
    # leaves no note (D340). They are said when they are the reason there
    # is no force.
    out.surfaces_above_target = n_above
    out.surfaces_untouched = len(untouched)
    out.surfaces_above_centre = n_above_centre
    nothing_priced = best is None and not out.surfaces_analysed
    # v0.1.516 (D467) -- said always, like the untouched ones: those
    # surfaces stay below the target, and no force at this elevation helps
    if n_above_centre:
        out.notes["above_centre_skipped"] = RM.run_note(
            RM.BACK_NONE_ABOVE_CENTRE if nothing_priced
            else RM.BACK_ABOVE_CENTRE_LEFT_OUT,
            n=n_above_centre, y=elevation)
    if untouched:
        if nothing_priced:
            out.notes["untouched_skipped"] = RM.run_note(
                RM.BACK_NONE_UNTOUCHED, y=elevation, n=len(untouched),
                lo=min(t[0] for t in untouched),
                hi=max(t[1] for t in untouched))
        else:
            out.notes["untouched_skipped"] = RM.run_note(
                RM.BACK_UNTOUCHED_LEFT_OUT, n=len(untouched), y=elevation)
    if best is None:
        # The reason when it is known: Bishop with nothing but surfaces that
        # are not circles (a non-circular run) is not a matter of "the
        # target factor and the search settings" that BACK_NONE points at.
        # Nor is a force that touches no mass, or a run already at the
        # target (v0.1.441): each is said by its own note.
        # The surfaces at the target come before the ones Bishop cannot
        # price (the review of 0.1.441): with every circle at the target and
        # one polyline of the user's, the reason was said to be the
        # polyline, and nothing said that the circles needed no force. The
        # note of the surfaces that are not circles is still given beside
        # it.
        if nothing_priced and untouched:
            out.notes["error"] = out.notes["untouched_skipped"]
        elif nothing_priced and n_above_centre:
            out.notes["error"] = out.notes["above_centre_skipped"]
        elif nothing_priced and n_above:
            out.notes["error"] = out.notes["above_target"] = RM.run_note(
                RM.BACK_NONE_ABOVE_TARGET)
        elif n_not_circle and not out.surfaces_analysed:
            out.notes["error"] = out.notes["not_circular_skipped"]
        else:
            out.notes["error"] = RM.run_note(RM.BACK_NONE)
    if progress_cb:
        progress_cb(total, total)
    return out
