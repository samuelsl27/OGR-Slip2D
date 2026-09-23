# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Post-analysis admissibility checks (anomaly A3).

Implements the two checks the reference performs on a slip surface
*after* the factor of safety has converged:

**Tensile Stress Check.** Negative effective normal stress (tension) can
appear on the base of a slice — typically where the pore pressure is high
or where the base is steeply inclined, as happens near the crest of a
deep-seated surface. When it does, the slice forces may not be
kinematically feasible and the safety factor can be "inaccurate or in the
worst case, completely invalid". The check therefore:

* runs **after** the iteration has converged, never during it;
* tests only a *percentage of slices starting from the toe* (default
  95 %), because the slices at the very crest are legitimately in tension
  — they are, in reality, the tension-crack zone;
* allows zero tensile stress for every strength model except those whose
  criterion defines a finite tensile strength. The reference names three
  -- Hoek-Brown, Generalised Hoek-Brown and Shear-Normal Function -- and
  gives the rule for none. Since v0.1.191 (D165) the two Hoek-Brown models
  get s*sigci/mb, the root of their criterion's bracket, and the
  Shear-Normal Function stays at zero because no source says how; see
  :func:`_material_tensile_strength`;
* invalidates the surface when the limit is exceeded (the reference
  writes error code -120 in place of the safety factor).

**m-alpha Check.** ``m_alpha = cos(alpha) + s·sin(alpha)·tan(phi)/F``,
where ``s`` is the sense of sliding, is the denominator of the base normal
force. It has been suggested (Whitman & Bailey, 1967) that once it drops
below about 0.2 the resulting safety factor should not be quoted without
looking further: a small positive value inflates the normal force and
hence the shear resistance, and a negative value can produce negative
resistance and meaningless factors of safety. Surfaces whose final
iteration has ``m_alpha < 0.2`` on any slice are rejected.

What the limit does **not** say, and the source is explicit about it: a
value below 0.2 does not by itself mean the factor of safety is wrong.
In most cases it can still be calculated and the iteration still
converges. The limit screens out surfaces whose arithmetic has become
untrustworthy, not surfaces known to be wrong — which is why it is a
setting and not a law. The fuller discussion is Ching & Fredlund (1983),
cited here because it is the source the limit's own documentation points
to and **not** because it has been read: it is behind a paywall, no copy
is held with this project's references, and nothing here has been
checked against it.

Under ``phi = 0`` the friction term vanishes and ``m_alpha`` degenerates
to ``cos(alpha)`` exactly, which turns the check into a bare ceiling on
the base angle — 78.463 deg at a limit of 0.2 — with no dependence on
the method or on F. Anchored against a published slice table in
``tests/test_james_bay_v1158.py`` and on this program's own arithmetic in
``tests/test_block_population_v1135.py``.

**v0.1.190 (D61) — that ceiling is KEPT, and this is the decision, not a
description of one still pending.** It is written here because this is
where the limit is read.

*The search for a published case ended negative* (v0.1.158), in the three
sources the assignment named and in a fourth that turned up on the way.
What was wanted: a non-circular surface in ``phi = 0`` soil with a base
angle anywhere near 78 deg and a published factor of safety.

* the 111 problems of the verification bank — 11 have ``phi = 0`` and a
  non-circular half, and only problem 47 publishes surface coordinates:
  a plane at **44.17 deg**. Problem 29's digitised polyline reaches
  **43.4 deg**;
* Duncan, Wright & Brandon (2014) §7.7.6, the James Bay dyke, Fig. 7.29 —
  non-circular, slice by slice, F = 1.17, and its steepest cohesive base
  is **43.7 deg**. It is in the suite;
* USACE (2003), EM 1110-2-1902, Fig. **G-9** — ``phi = 0`` on all twelve
  slices and a base at **+61 deg**, but the surface is **not published as
  a non-circular one**, so it cannot be reproduced as such;
* Ching & Fredlund (1983) — see above: **not read**, and that is why it
  cannot decide anything here either.

The two that come closest do so from opposite sides: G-9 has the steep
base without the surface, Fig. 7.29 has the surface without the steep
base. **No published case discriminates.**

*The doctrine that would decide it, marked as doctrine and not as a
case.* Duncan, Wright & Brandon §14.4 answers both questions directly —
it states that the 0.2 protects against a mechanism that is explicitly
FRICTIONAL, and it recommends constraining the inclination of a slip
surface in an automatic non-circular search, with a starting guide of
"**45 degrees or less**" and Fig. 14.17 (**Jumikis** 1962) for the
passive-zone angle. Applying that here would move the validated cases,
which is the one thing a feature is not allowed to do. It is cited and
not applied.

*What IS measured, and it does not point the other way.* On the general
branch the ceiling still screens something real — see
:func:`m_alpha_check` — so keeping it is not keeping an inert rule. And
the bank's own witness has gone: on problem 75, the case the defect was
raised on, today's model discards NOTHING for m-alpha (see the closing
note of D61 in the bank). The 0.5354 of the original table came from an
implicit block region the manual never draws and this model no longer
uses.

**So the limit stays at 0.2.** Without an external case, moving a
validity limit is exactly what this project's first rule exists to
prevent. The defences are the reporting note of v0.1.135
(``analysis_runner.m_alpha_margin_note``) and, since v0.1.190, the note
that says which of the two base-angle ceilings governs
(``analysis_runner._base_angle_scope_notes``).

**And what clearing 0.2 does NOT buy, measured here so nobody reads the
decision as an endorsement.** On a synthetic ``phi = 0`` polyline whose
scarp is stepped through its inclination, with every surface CLEARING the
limit, the nine methods disagree by a factor of 6.8 at 70 deg
(min ``m_alpha`` 0.342), 34.9 at 75 deg (0.259) and 1501 at 78 deg
(0.208, i.e. admitted by eight thousandths). The original defect report
put this spread at 44 %. The limit screens arithmetic that has become
untrustworthy; it does not certify what survives.

The two defaults are **not** the same, and saying "both are off" was
false here for the seventy-four versions from v0.1.84 to v0.1.157. The Tensile Stress Check is
**off**, matching the reference, where tensile normal stresses are
permitted unless the user opts in. The m-alpha check is **on** since
v0.1.84, also matching the reference, whose two worked examples filter
with it by default and count what it rejects as error -112 (97 surfaces
of 4851 in the first, 225 in the second). It was off before that on the
strength of a measurement v0.1.82 found to be reading ``m_alpha`` in the
mirror.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from .external_forces import slice_forces

M_ALPHA_LIMIT = 0.2          # Whitman & Bailey (1967)

#: The methods this criterion is APPLIED to. A WHITELIST and not a list of
#: exceptions, for the reason D164 was closed on: an exception list adopts
#: in silence every method born after it, and the price of that mistake
#: here is a surface thrown away by a denominator its own method never
#: formed.
#:
#: v0.1.189 (D111). Membership is not taste. The reference's two worked
#: reports run all seven methods over the SAME population -- 4851 surfaces
#: in the first, 4840 in the second, valid plus invalid, identical for
#: every method -- and print error -112 for exactly these five: 97/225
#: Bishop, 91/146 Janbu (both), 110/250 Spencer, 111/248 GLE. For the
#: Ordinary Method and for Lowe-Karafiath the printed error codes ADD UP
#: to the printed invalid count with no -112 term (1472 and 2401 in the
#: first; 1411 and 2722 in the second), so the absence is an ACCOUNTING
#: IDENTITY and not an unprinted zero. And Lowe-Karafiath is not merely
#: absent from the run: it reports 37 and 129 surfaces under -111, so it
#: saw the same steep-based surfaces of which Bishop discarded 97 and
#: discarded none of them for this reason.
#:
#: The two Corps of Engineers procedures are NOT exercised by either
#: report. They are here by FAMILY INFERENCE, which is a weaker claim and
#: is written as one: the three share ``PrescribedInclinationMethod`` and
#: form their denominator in the single line ``modified_swedish.py``
#: builds it, differing only in the rule for theta.
#:
#: What is NOT decided here is the FORM. Every method that IS screened is
#: screened with Bishop's denominator, exactly as the reference does; what
#: that costs is measured in :func:`base_m_alphas`.
M_ALPHA_SCREENED = frozenset({
    "bishop_simplified",
    "janbu_simplified",
    "janbu_corrected",
    "spencer",
    "gle_morgenstern_price",
})

#: The methods that form NO such denominator at all. A STRONGER statement
#: than "not screened", and it answers a different question: it is why
#: :func:`ogr_slip2d.analysis_runner.m_alpha_margin_note` stays silent for
#: them, while the prescribed-inclination family still gets a note. That
#: family DOES divide by something -- just not by this -- and with the
#: screen gone the note is the only thing left looking.
#:
#: v0.1.158 (D104) declared this in ``analysis_runner``; v0.1.189 moved it
#: here so that the note and the check read their sets from ONE file.
#: Duncan, Wright & Brandon (2014) 14.4.2 states it from the other side
#: and makes the Ordinary Method one of its four REMEDIES for the problem;
#: and the string ``m_alpha`` does not appear in ``methods/ordinary.py``.
NO_M_ALPHA_DENOMINATOR = frozenset({"ordinary_fellenius"})


# ----------------------------------------------------------------------
def _material_tensile_strength(material) -> float:
    """Allowable tensile stress on a slice base, as a POSITIVE magnitude.

    v0.1.191 (D165) -- asked of the strength model, through
    ``StrengthModel.tensile_strength()``, which is zero unless the model's
    criterion defines a finite tensile strength. Today that is the two
    Hoek-Brown models, sigma_t = s*sigci/mb; the derivation and its sources
    are at ``GeneralizedHoekBrown.tensile_strength``.

    What this replaced could return nothing but 0.0, for three independent
    reasons, each sufficient: it read ``sigma_ci``, ``mb`` and ``s`` as
    attributes, and a strength model keeps them in ``params`` and defines
    no ``__getattr__``; the names did not exist either (``sigci``, and
    ``m`` in the classic model); and its hand-typed whitelist named
    ``generalized_hoek_brown``, which is no model's ``MODEL_ID``, while
    leaving out ``hoek_brown_classic``, which is one. There is no list now:
    each model answers from its own parameters, so the names cannot drift
    away from the envelope that reads them, and a model born later starts
    at zero.

    The Shear-Normal Function stays at zero, and that is a decision, not a
    property of the table: the reference names it among the criteria that
    CAN carry a finite tensile strength, but no source states the rule --
    a table starting at (-50, 0) does reach tau = 0 in tension -- and a
    plausible formula with nothing behind it is the worst outcome here.

    Any failure comes back as 0.0, the answer every other material gets.
    Not out of politeness: ``BaseSearch._is_admissible`` swallows an
    exception from the checks and ADMITS the surface, so raising here would
    let a surface in tension through.
    """
    if material is None:
        return 0.0
    ask = getattr(getattr(material, "strength", None), "tensile_strength",
                  None)
    if not callable(ask):
        return 0.0
    try:
        value = float(ask())
    except Exception:                                     # noqa: BLE001
        return 0.0
    if not (math.isfinite(value) and value > 0.0):
        return 0.0
    return value


# ----------------------------------------------------------------------
def _denominator_sign(result) -> float:
    """The sign ``m_alpha`` was formed with, ASKED OF THE METHOD THAT FORMED IT.

    v0.1.82 — this was the bug, and the diagnosis still holds. ``m_alpha``
    is not symmetric in ``alpha``, so it means nothing unless it is read in
    the same sign convention the method used. On the reference critical
    circle — Ej_1, centre (88, 70.5), R = 47.212, sign −1 — reading it in
    the other one turned min m_alpha = +0.928 into −0.010 and "rejected"
    five perfectly ordinary slices. The criterion was never wrong, it was
    being read in the mirror.

    v0.1.189 (D112) — what v0.1.82 did NOT fix is that the sign was still
    RE-DERIVED here instead of being asked for, from a sum that is
    Bishop's. The old name said "slide sign", and that was the third
    mistake: this was never anybody's sense of sliding, it was a guess at
    one method's. Janbu derives its own from
    ``sign(Σ w_total·tan α)`` — a sum in which the ponded water rides in
    ``w_total`` and ``tan`` weights a steep base far more heavily than
    ``sin`` does — so against Janbu the guess can come out backwards.

    Against the others it cannot, and saying why is what keeps this from
    being a bigger claim than it is: Bishop, Spencer, GLE, the Ordinary
    Method and the prescribed-inclination family all derive theirs from
    ``sign(Σ W(1−kv)·sin α)``, and ``(1−kv) ≥ 0`` is a constant
    non-negative factor, which cannot invert a sum. Only at ``kv = 1.0``
    exactly does their sum vanish identically; there the method's own
    (degenerate) answer is now imported, which is the point.

    **The fallback is not courtesy, it is necessity**: a result built by
    hand carries no ``details`` at all (``tests/test_tensile_strength_rock_v1191.py``
    builds one); ``MultiStageDrawdownMethod`` builds its ``details`` as a
    literal and so DROPS the inner method's keys -- all of them but ``kv``
    since v0.1.191; and a plugin method need not publish the key. In those
    the fallback returns the same number it always did, because the methods
    that reach them are the ones whose sum agrees with this one -- with one
    exception, reported and not fixed here (D112b): Janbu inside the
    multi-stage drawdown wrapper, which is D112's own case reached through
    the wrapper. Until v0.1.191 this paragraph named two test files as
    building ``LEMResult`` by hand; they build ``Slice`` only and never
    reach the checks, and no code rebuilds a result from an archived
    ``.h5``.

    Methods that form no such denominator — the Ordinary Method — and the
    prescribed-inclination family, whose denominator is
    ``cos(α−θ) − orient·(tan φ/F)·sin(α−θ)`` and is therefore NOT this
    expression for any sign, deliberately do not publish the key. Writing
    one for them would have been inventing a hybrid no method computes.
    """
    details = getattr(result, "details", None) or {}
    declared = details.get("m_alpha_sign")
    if declared is not None:
        try:
            v = float(declared)
        except (TypeError, ValueError):
            v = 0.0
        if v and math.isfinite(v):
            return math.copysign(1.0, v)
    slices = getattr(result, "slices", None)
    if not slices:
        return 1.0
    # Bishop's sum, kept EXACTLY as it was — same builtin ``sum``, same
    # term order. Swapping in ``fsum`` here would be a silent arithmetic
    # change on a borderline surface, which is not what this fixes.
    driving = sum(s.weight * math.sin(s.base_angle) for s in slices)
    return 1.0 if driving >= 0 else -1.0


def _applied_kv(result) -> float:
    """The vertical seismic coefficient the method APPLIED, asked of it.

    v0.1.191 (D167) -- read from ``details["kv"]``, which every method
    writes from the same local it hands to ``slice_forces``: the road
    ``m_alpha_sign`` already takes. The checks receive a result and not a
    project, so there is nowhere else to learn it from without keeping a
    second copy -- and two copies of one fact is how D111 and D113 came
    about.

    It is the coefficient APPLIED, not the one stored: a disabled
    earthquake is kv = 0 to every method, whatever the project keeps.

    Absent, or not a finite number, it reads as 0.0, which is what the
    checks assumed before this existed. That covers a result built by hand
    and a plugin method that does not publish the key; for those the load
    is the one without a vertical earthquake, as it always was.
    """
    details = getattr(result, "details", None) or {}
    try:
        kv = float(details.get("kv", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return kv if math.isfinite(kv) else 0.0


def _base_load_and_sigma(s, *, kv: float) -> tuple[float, float]:
    """The base load and the ONE normal stress both checks linearise at.

    ``W`` is :attr:`SliceForces.w_total` — soil plus the ponded water
    standing on the slice — which is the load every method's own
    iteration uses to estimate the stress it evaluates the envelope at
    (see :meth:`BishopSimplified.compute_fos`). Taking it from
    :func:`slice_forces` rather than adding the two terms here is what
    keeps this estimate tied to the solver's instead of merely equal to
    it today.

    v0.1.188 (D113) — there used to be two estimates. v0.1.67 taught
    ``base_effective_stresses`` to carry the ponded water, because
    leaving it out made that check judge a reservoir-loaded slope with
    about a third of the real normal force — "the difference between 'in
    tension' and not". ``base_m_alphas``, the same loop fifteen lines
    below, was not taught. It only shows where the envelope depends on
    sigma, since ``_local_c_phi`` then returns a different ``tan phi``
    for each estimate and the two checks judge the same slice at two
    different stresses: exactly the case v0.1.67 was written for. One
    function returning both quantities is what makes them unable to
    drift apart again.

    v0.1.191 (D167) -- they had not drifted apart; they came in apart, one
    argument further along. This called ``slice_forces(s)`` with the
    default ``kv = 0.0`` while every method calls
    ``slice_forces(s, kh, kv)``, whose soil weight is ``weight * (1 - kv)``,
    so under a vertical earthquake the check judged each slice under a load
    the solver never applied. ``kv`` now comes from the method (see
    :func:`_applied_kv`) and is required, by name and without a default: a
    default of zero is precisely how this function came to miss it, and it
    would do the same to the next caller that forgot. ``kh`` is not passed
    because ``w_total`` does not depend on it -- the horizontal term lives
    in ``h_seismic``. And the sign of kv is ``slice_forces``'s to decide,
    not this function's (D170), which is why it is called and not copied.

    The load enters the normal force directly, so the tensile check moved
    with EVERY envelope; the m-alpha check only where ``tan phi`` depends
    on the stress. With kv = 0 both are unchanged to the last bit, since
    ``x * (1.0 - 0.0)`` is ``x``.

    What even the right kv does NOT make equal to the solver's estimate,
    reported and not fixed here (D172): with supports, Bishop and Janbu add
    ``support_vertical_load`` to this load and Spencer, GLE and the
    prescribed-inclination family subtract ``nf_v``; the Ordinary Method
    estimates its stress with a form of its own; and the floor on ``l`` is
    1e-12 here and 1e-9 in the methods.
    """
    W = slice_forces(s, kv=kv).w_total
    l = max(s.base_length, 1e-12)
    sigma = max(0.0, W * math.cos(s.base_angle) - s.pore_pressure * l) / l
    return W, sigma


def base_effective_stresses(result) -> list[float]:
    """Effective normal stress on each slice base at the converged FoS.

    Uses the classical limit-equilibrium expression for the base normal
    force,

        N = [ W - (c·l·sin(alpha) - u·l·tan(phi)·sin(alpha)) / F ] / m_alpha
        sigma'_n = N / l - u

    which is the quantity the reference tests for tension. Returns an
    empty list when the result carries no usable slices.
    """
    from .methods.bishop import BishopSimplified

    if result is None or not getattr(result, "slices", None):
        return []
    F = getattr(result, "fos", math.nan)
    if not (math.isfinite(F) and F > 0):
        return []

    out: list[float] = []
    sgn = _denominator_sign(result)
    kv = _applied_kv(result)
    for s in result.slices:
        alpha = s.base_angle
        l = max(s.base_length, 1e-12)
        u = s.pore_pressure
        W, sigma_est = _base_load_and_sigma(s, kv=kv)
        c_loc, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                       sigma_est)
        m_alpha = math.cos(alpha) + sgn * math.sin(alpha) * tan_phi / F
        if abs(m_alpha) < 1e-9:
            out.append(float("-inf"))     # degenerate: treat as failing
            continue
        N = (W - sgn * (c_loc * l * math.sin(alpha)
                        - u * l * tan_phi * math.sin(alpha)) / F) / m_alpha
        out.append(N / l - u)
    return out


def base_m_alphas(result) -> list[float]:
    """``m_alpha`` on every slice at the converged FoS.

    Bishop's denominator, ``cos a + s*sin a*tan phi / F``, for EVERY
    method -- including the ones whose own denominator is a different
    expression. That is a decision and not an oversight, so here is what
    it costs and why it stands.

    **This is a MEASUREMENT, not a verdict.** It is computed for every
    method, including those :data:`M_ALPHA_SCREENED` leaves out: the
    reporting note reads it, and so does the rapid-drawdown diagnostic in
    ``rapid_drawdown.py``. The gate that decides admissibility lives in
    :func:`m_alpha_check`. Silencing the measurement would have taken the
    number away from both readers to change one of them.

    **What the other denominators are.** Janbu divides by
    ``n_alpha = cos^2 a * (1 + s*tan a*tan phi/F)``, and that is exactly
    ``cos a * m_alpha`` -- an identity, already written down at
    ``interslice.py``. So for Janbu the two forms never differ in SIGN,
    only in size, and applying 0.2 to ``n_alpha`` is applying
    ``0.2 / cos a`` to ``m_alpha``: a different criterion wearing the same
    number. The prescribed-inclination family divides by
    ``cos(a - t) - orient*(tan phi/F)*sin(a - t)``, which carries its own
    interslice inclination.

    **Measured, on the only published slice table this project holds**
    (Duncan, Wright & Brandon 2014, Fig. 7.29, the James Bay dyke, theta =
    2.7 deg, F = 1.17; the sheet is in ``tests/test_james_bay_v1158.py``):
    the minimum is 0.7230 with Bishop's form, 0.5181 with Janbu's and
    0.6896 with the family's -- a gap of 39.5 % and 4.8 % respectively --
    and the governing slice is not even the same one (11 for Bishop and
    the family, 1 for Janbu). But **all three clear 0.2 comfortably**, so
    that case MEASURES the gap and DECIDES nothing.

    **Why the form is not changed per method.** The number 0.2 is glued to
    a form. Under ``phi = 0`` it degenerates to a bare ceiling on the base
    angle, and each form gives a different one: 78.463 deg for Bishop's,
    63.435 deg for Janbu's -- 15.03 deg apart, with no source saying so.
    Picking a denominator per method would not be choosing a denominator;
    it would be inventing a criterion. What would settle it is a published
    case with a base in the 63.4-78.5 deg band where the two ceilings
    disagree, or a source stating the limit for ``n_alpha``. That is
    defect D61, still open, and the James Bay sheet does not reach it: its
    steepest cohesive base is 43.7 deg.

    What v0.1.189 DID change is which methods the criterion is applied to
    at all; see :data:`M_ALPHA_SCREENED`.
    """
    from .methods.bishop import BishopSimplified

    if result is None or not getattr(result, "slices", None):
        return []
    F = getattr(result, "fos", math.nan)
    if not (math.isfinite(F) and F > 0):
        return []
    out: list[float] = []
    sgn = _denominator_sign(result)
    kv = _applied_kv(result)
    for s in result.slices:
        alpha = s.base_angle
        _W, sigma_est = _base_load_and_sigma(s, kv=kv)
        _c, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                    sigma_est)
        out.append(math.cos(alpha) + sgn * math.sin(alpha) * tan_phi / F)
    return out


# ----------------------------------------------------------------------
def _toe_ordered_slices(result):
    """Slice indices ordered from the TOE of the surface inwards.

    The toe is the down-slope end, i.e. the end whose ground surface is
    lower. The reference measures its "percentage of slices" from there.
    """
    slices = list(result.slices)
    n = len(slices)
    if n == 0:
        return []
    y_left = slices[0].top_y_left
    y_right = slices[-1].top_y_right
    order = list(range(n))
    if y_left < y_right:
        return order           # toe at the left end
    return order[::-1]         # toe at the right end


def tensile_stress_check(result, percent_of_slices: float = 95.0):
    """Reference-style Tensile Stress Check.

    Returns ``(passed, offending_indices)``. ``passed`` is False when any
    tested slice carries an effective normal stress more tensile than its
    material allows.
    """
    stresses = base_effective_stresses(result)
    if not stresses:
        return True, []
    order = _toe_ordered_slices(result)
    n_test = int(round(len(order) * max(0.0, min(100.0, percent_of_slices))
                       / 100.0))
    tested = order[:max(0, n_test)]
    slices = list(result.slices)
    bad: list[int] = []
    for i in tested:
        allowed = _material_tensile_strength(slices[i].material)
        if stresses[i] < -allowed - 1e-9:
            bad.append(i)
    return (not bad), bad


def m_alpha_check(result, limit: float = M_ALPHA_LIMIT):
    """Reference-style m-alpha check (Whitman & Bailey, 1967).

    Returns ``(passed, offending_indices)``.

    v0.1.189 (D111) -- the criterion is NOT applied to every method. Which
    ones, and the published evidence that decides it, are at
    :data:`M_ALPHA_SCREENED`.

    The gate is here and not in :func:`check_surface` or in
    ``BaseSearch._is_admissible``, for two reasons. Those two are DOORS --
    the search is one caller of several -- and a gate on one door leaves
    the others willing to reject a surface the first one would keep, which
    is the shape of the defect being closed: until now the exclusion
    existed only in the reporting note, so the check screened a method the
    note had already declared it had nothing to say about. And
    ``check_surface``'s subject is BOTH checks, while the evidence here
    speaks only about this one -- the reports do not print -120 for these
    methods either, but the Tensile Stress Check is OFF by default in both
    worked examples, so that silence proves nothing and is not borrowed.

    A result with no ``method_id`` is screened, which is what happened
    before: this narrows behaviour for four named methods and for nothing
    else.

    v0.1.190 (D114) -- what "under ``phi = 0`` this stops being a
    statement about the method" does and does not mean. The claim is half
    right, and the half that is wrong is the half D61 lives in. Under
    ``phi = 0`` this gate IS a ceiling of 78.463 deg on the base angle,
    and the question is whether the quantity it screens by reaches the
    answer.

    **The exact half.** With ``tan phi = 0`` and ``u = 0`` the resisting
    term is ``q = c*b / m_alpha = c*b / cos a = c*l`` EXACTLY, because on
    a straight chord ``l`` IS ``b / cos a``. So ``m_alpha`` cancels, and
    on the CIRCULAR Bishop branch the criterion screens by a quantity
    that does not touch the number it screens.

    **The half that is wrong, and it is the general branch.** In
    ``methods/bishop.py::_general_moment_fos`` the normal force keeps the
    cosine that ``q`` shed::

        normal = (w_n - (q/F) sin a) / cos a          # 1/cos a = 1/m_alpha

    and ``normals`` enters ``moment_balance.moment_terms`` with an arm of
    its own, on the DENOMINATOR side: ``MomentTerms.driving`` is
    ``weight + normal + external`` and ``F = -shear / driving`` (the
    moment split is Fredlund & Krahn, 1977). So on a polyline the steep
    base is not filtered out of the answer -- it is part of it.

    **Measured** (``_tools/censo_techos_d114_d61.py`` in the verification
    bank; the table is in ``docs/audits/phi_zero_ceilings_v1190.md``):

    * on the PUBLISHED James Bay surface, whose steepest cohesive base is
      43.7 deg and therefore nowhere near the ceiling, the normal force
      of that base carries **3.66 %** of the driving moment, and removing
      only its contribution moves the factor **-3.53 %**;
    * stepping a synthetic ``phi = 0`` scarp from 40 to 76 deg,
      ``terms.normal / terms.driving`` falls MONOTONICALLY from **+18.0 %
      to -131.6 %** -- past 74 deg the term D61 treated as cancelled is
      larger in magnitude than the whole driving moment;
    * on a CIRCLE with the axis at the centre the same moment is **zero
      by construction** and not merely small: ``base_frame`` takes the
      midpoint of the chord and its perpendicular, which is the chord's
      perpendicular bisector and passes exactly through the centre, so it
      vanishes for ARBITRARY normals. Measured residual **2.9e-16**
      relative, over two radii and two slice counts.

    That is the contrast, and it is why the ceiling is not loosened: on
    the branch the defect is about, it still screens something real. The
    decision itself is at the top of this module.
    """
    method_id = getattr(result, "method_id", "") or ""
    if method_id and method_id not in M_ALPHA_SCREENED:
        return True, []
    vals = base_m_alphas(result)
    if not vals:
        return True, []
    bad = [i for i, v in enumerate(vals) if v < limit]
    return (not bad), bad


# ----------------------------------------------------------------------
def screen_surface(result, tensile: bool = False,
                   tensile_percent: float = 95.0,
                   m_alpha: bool = False,
                   m_alpha_limit: float = M_ALPHA_LIMIT):
    """Run the enabled post-analysis checks on a converged result.

    Returns ``(passed, screen, note)``: ``screen`` is the check that
    rejected the surface, one of ``methods.base.ALL_SCREENS`` (empty when it
    passes), and ``note`` the short explanation for a human, None when it
    passes.

    v0.1.192 (D177) — the ``screen`` is new and the note is not: a caller
    that needs to know WHICH check fired now reads the constant instead of
    searching the prose, which is how the raw-data export came to file the
    tensile rejection under the generic code. The notes are unchanged
    character for character, because the search, Optimize Surfaces and the
    interpretation window all read them.

    The tensile check runs first and the first rejection is the answer, so
    a surface failing both is reported — and exported — as tensile.
    """
    from .methods.base import SCREEN_M_ALPHA, SCREEN_TENSILE_STRESS

    if result is None or not getattr(result, "is_valid", False):
        return True, "", None
    if tensile:
        ok, bad = tensile_stress_check(result, tensile_percent)
        if not ok:
            return False, SCREEN_TENSILE_STRESS, (
                f"tensile stress on {len(bad)} slice base(s) "
                f"(error -120)")
    if m_alpha:
        ok, bad = m_alpha_check(result, m_alpha_limit)
        if not ok:
            return False, SCREEN_M_ALPHA, (
                f"m_alpha < {m_alpha_limit} on {len(bad)} slice(s)")
    return True, "", None


def check_surface(result, tensile: bool = False,
                  tensile_percent: float = 95.0,
                  m_alpha: bool = False,
                  m_alpha_limit: float = M_ALPHA_LIMIT):
    """Run the enabled post-analysis checks on a converged result.

    Returns ``(passed, reason)`` where ``reason`` is None when the
    surface passes, or a short explanation suitable for reporting. The
    two-value form every caller written before v0.1.192 unpacks; see
    :func:`screen_surface` for which check fired.
    """
    passed, _screen, note = screen_surface(
        result, tensile=tensile, tensile_percent=tensile_percent,
        m_alpha=m_alpha, m_alpha_limit=m_alpha_limit)
    return passed, note
