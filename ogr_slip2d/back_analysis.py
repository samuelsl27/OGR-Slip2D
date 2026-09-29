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
* The elevation only affects **Bishop**, because that method works from
  moment equilibrium and the elevation sets the moment arm. It has no
  effect on **Janbu**, which considers only force equilibrium: a
  horizontal force enters the horizontal balance identically wherever it
  acts.
* Only **Bishop, Janbu and Janbu Corrected** are supported; the method is
  not defined for the others.
* Every surface is evaluated and the one needing the **largest** force is
  reported.
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

SUPPORTED_METHODS = ("bishop_simplified", "janbu_simplified",
                     "janbu_corrected")


@dataclass
class BackAnalysisSurfaceResult:
    """Required support force for one slip surface."""

    surface: Optional[dict] = None
    active_force: float = math.nan
    passive_force: float = math.nan
    target_fos: float = 1.3
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
            "active_force": c.active_force if c else math.nan,
            "passive_force": c.passive_force if c else math.nan,
            "required_force": self.required_force,
            "unsupported_fos": c.unsupported_fos if c else math.nan,
        }


#: Why a surface was left out of the back analysis when a curved envelope
#: could not be read at the stress the method resolves (v0.1.215, D204).
ENVELOPE_NOT_SETTLED_NOTE = (
    "The strength envelope depends on the normal stress, and on at least "
    "one slice the stress it is read at did not settle on the stress the "
    "method resolves at the target factor of safety; the surface was left "
    "out rather than back-analysed at a point the method does not use.")


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


# ======================================================================
def run_back_analysis(project, search, target_fos=1.3, elevation=0.0,
                      method_id="bishop_simplified", num_slices=25,
                      progress_cb=None) -> BackAnalysisResult:
    """Back-analyse every surface of a search and report the one needing
    the largest support force.

    ``search`` is a configured search object; its surfaces are
    regenerated and each is back-analysed. The main stability results are
    neither used nor modified.
    """
    out = BackAnalysisResult(method_id=method_id, target_fos=target_fos,
                             elevation=elevation)
    if method_id not in SUPPORTED_METHODS:
        out.notes["error"] = (
            f"Back analysis is only available for "
            f"{', '.join(SUPPORTED_METHODS)}.")
        return out
    if not (math.isfinite(target_fos) and target_fos > 0):
        out.notes["error"] = "The target factor of safety must be positive."
        return out

    from .surface import CompositeSurface

    kh = project.seismic.kh if project.seismic.enabled else 0.0
    kv = project.seismic.kv if project.seismic.enabled else 0.0

    try:
        run = search.run(project)
    except Exception as exc:  # noqa: BLE001
        out.notes["error"] = f"search failed: {exc}"
        return out

    best = None
    total = len(run.evaluations)
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
    for i, ev in enumerate(run.evaluations):
        if not ev.is_valid or not ev.slices:
            continue
        if isinstance(ev.surface, CompositeSurface):
            n_composite += 1
            continue
        r = required_force(ev.slices, ev.surface, target_fos, method_id,
                           elevation, kh, kv, project=project)
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
        if best is None or r.governing_force > best.governing_force:
            best = r
        if progress_cb and i % 20 == 0:
            progress_cb(i, total)

    out.critical = best
    if n_composite:
        out.notes["composite_skipped"] = (
            f"{n_composite} composite surface(s) were left out: back "
            f"analysis is written in the circular form of the method, which "
            f"does not hold on the straight stretches of a composite. Turn "
            f"Composite Surfaces off to back-analyse this model, and read "
            f"the result as being about circular surfaces only.")
    if n_unsettled:
        out.notes["envelope_not_settled"] = (
            f"{n_unsettled} surface(s) were left out: "
            f"{ENVELOPE_NOT_SETTLED_NOTE}")
    if best is None:
        out.notes["error"] = (
            "No surface could be back-analysed. Check the target factor "
            "of safety and the search settings.")
    if progress_cb:
        progress_cb(total, total)
    return out
