# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.171 (D118) — the inter-slice thrust is bounded, and a branch cut for it
says which of three things happened to it.

WHAT INVARIANT THIS PROTECTS. ``interslice.solve_branch`` clamps ``F`` to
[``F_MIN``, ``F_MAX``] and refuses a non-finite ``f_new``, but until this
version the thrust ``E`` — and with it ``X = lambda*f(x)*E``, the base normal
that carries their difference, and every quantity derived from it — had no
bound whatever. So the rule this file enforces is that **a branch must leave
the range where its arithmetic means something only by being thrown away for
it, never by carrying it into the answer.**

WHY THE ANCHOR IS NOT IN THIS FILE. The external reference for these two
methods is the closed form of a plane wedge, and it lives in
``tests/test_janbu_wedge_v1142.py``, whose ``LADDER`` asserts that tightening
the tolerance moves Spencer and GLE TOWARDS it. This file asserts the
MECHANISM instead, and its conservation half is written as an A/B in the same
process — the bound in place against the bound lifted — because that says
"this change moved nothing" directly, without a second copy of a reference
value that could then drift from the first. Splitting them is deliberate: a
test of the mechanism that also owned the reference could be made to pass by
moving the reference.

WHAT THE FICHA ASKED FOR, AND WHY THIS FILE DOES NOT ASSERT IT. P-D118 asks
for a test in which "the divergent branch with ``max_passes=5000`` returns
``None`` with the reason, not ``ValueError``". Measured against the tree of
0.1.170 before anything was written: it already returns ``None``, so that
case is GREEN against the defect and would measure nothing. The
``ValueError: -inf + inf in fsum`` that v0.1.159 recorded could not be
reproduced on the published solver in 2960 direct calls to ``solve_branch``
and 904 whole ``compute_fos`` runs at ceilings of 2000 and 5000 on the two
models the ficha names; the changelog of 0.1.159 says why, if read to the
end — that measurement was taken with the AUTO-SIZING branch solver it was
evaluating, which is not what ships. The runaway is real and the particular
exception it ends in is luck, so what is asserted here is the runaway.

The ficha also names lambda = 2.0 as the divergent one. It converges: 234
passes at 1e-6 and 702 at 1e-14, with the thrust flat at 0.065 of the scale.
:data:`RUNAWAY_LAMBDA` is 2.5, which ``test_interslice_budget_v1159`` already
calls ``WANDERING_LAMBDA``.

THE MEASUREMENT THAT CHOSE THE NUMBER, on the 50 degree plane below, as
``max|E|`` over :func:`interslice._force_scale`:

    passes        10     50    100      200      400     1000
    lambda 2.5   0.021  0.12   0.45   4.1e21   2.6e70  6.3e216
    lambda 2.0   0.028  0.054  0.063   0.065    0.065    0.065  (converges)

Every branch that is an ANSWER peaks at 0.16 or under; a runaway crosses 1
and does not come back. ``THRUST_SCALE_LIMIT = 10`` therefore sits 60 times
above the worst answer and two hundred decades below where the runaway ends.

ONE HONEST LIMIT, asserted rather than left implicit. This bound does not
make ``converged`` mean "sane": a branch can still report convergence while
its thrust is nine orders of magnitude past the weight of the mass, because
``F_f`` is a QUOTIENT whose numerator and denominator are dominated by the
same runaway terms. 132 of them exist on the fixture below. That is P-D116,
it is not fixed here, and ``TestWhatThisDoesNotFix`` pins the evidence so
that the version which does fix it can see what moved.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

#: The plane wedge fixture, built here rather than imported: the modules in
#: ``tests/`` cannot import one another outside the runner, and this
#: geometry is four vertices and one material. Same numbers as
#: ``test_interslice_budget_v1159`` and ``test_janbu_wedge_v1142``.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50

BETA = 50.0
BETAS = (35.0, 40.0, 45.0, 50.0, 55.0)

#: The root of the 50 degree plane, and the slowest branch this package has
#: on record: 254 passes at 1e-14. It is here as the thing the bound must
#: NOT touch.
ROOT_LAMBDA = 1.2269

#: The lambda whose thrust runs away. NOT the 2.0 the ficha names, which
#: converges — see the module docstring.
RUNAWAY_LAMBDA = 2.5

#: A lambda whose moment branch stalls out with the thrust still at 0.11 of
#: the scale, so that "stalled" and "ran away" can be told apart by
#: something other than the name of the test asserting it.
STALLING_LAMBDA = 2.2

#: The plane on which the outer lambda search of Spencer actually loses a
#: lambda to the bound, at a SHIPPED tolerance and with nothing patched.
#: Chosen by measurement, not by taste.
#:
#: v0.1.172 (D116) moved the cell, and the reason is worth keeping because
#: it is NOT that the bound got weaker. The 35 degree plane at 1e-3 now
#: FINDS a lambda bracket where before it had none — ``lambda_search_fell_
#: back`` goes True to False — so the outer search stops sampling at the
#: first sign change and never walks as far as the lambda that runs away.
#: The guard did not stop firing; the search stopped reaching it.
#:
#: The replacement is chosen by measurement and against two requirements,
#: neither of them taste. FIRST, it has to lose a lambda to the bound AND
#: fall back, because the sentence only travels on the fallback path — the
#: coverage limit v0.1.171 reported and did not fix, executable here
#: instead of narrated. SECOND, and this is what fixes the tolerance, it
#: has to do so on BOTH sides of D116: a gate for the D118 bound that only
#: fires on the engine that carries D116 would quietly turn these two cases
#: into a test of the wrong version. Swept over every bare plane from 25 to
#: 70 degrees at four tolerances against both engines, this cell loses two
#: lambdas either way, at 1e-4 and at 1e-6. The other candidates do not:
#: 30 and 32.5 degrees with Spencer at 0.005 are single cells that move
#: with the engine, and 35 at 1e-3 is the one that stopped firing.
#:
#: 1e-4 and not 1e-6 of the two that qualify, because 1e-4 is the tolerance
#: the verification bank actually runs at since 0.1.160.
#:
#: v0.1.183 (D152) — 53.0 and no longer 52.5, and the angle moved because
#: the cell stopped being one. On 52.5 the planar exemption gives the
#: lambda grid back the samples it was losing, the search brackets on its
#: own instead of refining a gap, and the notes go silent — which is not a
#: regression but the behaviour
#: ``test_it_stays_quiet_when_the_search_found_its_bracket`` pins two cases
#: below as correct. A fixture that no longer reaches the narration path
#: cannot test it. 53.0 was chosen against the SAME criteria the paragraphs
#: above set, re-measured on both sides of D152 rather than assumed: it
#: loses lambdas to the bound and narrates them at 1e-4 (7 before, 6 after)
#: AND at 1e-6 (7 and 7), it loses none to the budget on either side, its
#: ``admissible`` and ``fos`` still match the same run with the bound
#: lifted, and Spencer on that plane still solves its bracket without ever
#: reaching the bound, which is what made this GLE's cell to begin with.
OVERFLOW_BETA, OVERFLOW_TOL = 53.0, 1e-4

#: And the method, for the same reason the angle is what it is: this cell
#: is GLE's. Spencer on the same plane solves its bracket and never reaches
#: the bound.
OVERFLOW_MID = "gle_morgenstern_price"

#: Geometry times this AND cohesion times this is the same slope in
#: different units: weight goes as the square of a length and a cohesive
#: force as its product with one, so scaling both leaves every force scaled
#: by k*k and the ratio the bound tests unchanged.
SIMILARITY_K = 10.0


def _daylight_x(beta_deg, k=1.0):
    return (TOE + H / math.tan(math.radians(beta_deg))) * k


def _bare(k=1.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0 * k), Vertex(60 * k, -10.0 * k), Vertex(60 * k, H * k),
        Vertex(CREST * k, H * k), Vertex(TOE * k, 0.0), Vertex(0, 0.0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH * k,
                                                 friction_angle=PHI))]
    return p


def _plane(beta_deg=BETA, k=1.0):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE * k, 0.0), Vertex(_daylight_x(beta_deg, k), H * k)]))


def _system(beta_deg=BETA, k=1.0, tolerance=1e-14):
    """The GLE system of the plane, ready to be asked for one branch."""
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.slicer import slice_surface

    project = _bare(k)
    surface = _plane(beta_deg, k)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    n = len(sl.slices)
    return GLESystem(sl.slices, [1.0] * (n + 1), 0.0, 0.0, 1.0,
                     None, None, None, axis_for(project, surface),
                     tolerance=tolerance)


def _branch(system, lam, tolerance=1e-14, moment=True, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos if moment else None,
                        tolerance, 1.0, **kw)


def _scale(system):
    from ogr_slip2d.interslice import _force_scale
    return _force_scale(system.rows)


def _peak(state):
    """``max|E|``, written so that a NaN anywhere comes back as a NaN.

    ``max()`` over a sequence containing NaN answers by position, which is
    the same trap the guard itself is written around.
    """
    top = 0.0
    for v in state.boundary_e:
        av = abs(v)
        if not (av <= top):
            top = av
    return top


@contextlib.contextmanager
def _lifted():
    """Run the solver with the bound out of the way, and put it back.

    The runner has no ``monkeypatch``, so the restoring is written out
    (rule 5). Patching the module global is enough and is not a shortcut:
    ``solve_branch`` reads ``THRUST_SCALE_LIMIT`` inside its own body, at
    call time. The same is NOT true of ``max_passes``, whose default is
    bound at ``def`` time — which is why every raised ceiling in this file
    is passed as an argument.
    """
    import ogr_slip2d.interslice as interslice
    keep = interslice.THRUST_SCALE_LIMIT
    interslice.THRUST_SCALE_LIMIT = math.inf
    try:
        yield
    finally:
        interslice.THRUST_SCALE_LIMIT = keep


@contextlib.contextmanager
def _pair_off():
    """The acceptance of 0.1.178: ask about F and not about the thrust.

    Same idiom and same reason as ``_lifted`` above — the runner has no
    ``monkeypatch`` and the switches are read at call time inside
    ``solve_branch``. A tree without them has nothing to turn off, and
    there the case below reads as the measurement it was before v0.1.179.
    """
    import ogr_slip2d.interslice as interslice
    keep_t = getattr(interslice, "BRANCH_PAIR_TIGHTEN", None)
    keep_s = getattr(interslice, "BRANCH_PAIR_SETTLE", None)
    if keep_t is None or keep_s is None:
        yield
        return
    interslice.BRANCH_PAIR_TIGHTEN = False
    interslice.BRANCH_PAIR_SETTLE = False
    try:
        yield
    finally:
        interslice.BRANCH_PAIR_TIGHTEN = keep_t
        interslice.BRANCH_PAIR_SETTLE = keep_s


def _result(method_id, beta_deg=BETA, tolerance=1e-3):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    project = _bare()
    surface = _plane(beta_deg)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    return method_registry()[method_id](
        tolerance=tolerance, max_iterations=400).compute_fos(
            project, surface, sl)


# ======================================================================
class TestTheRunawayIsCutAndSaysWhy:
    """The branch that ran away is abandoned, at the first pass it does it,
    and it comes back saying which of the solver's refusals this was."""

    def test_the_runaway_branch_is_abandoned_with_its_reason(self):
        system = _system()
        state = _branch(system, RUNAWAY_LAMBDA, max_passes=5000,
                        patience=10 ** 9)
        assert state is not None, "the branch vanished instead of reporting"
        assert state.abandoned == "thrust overflow", state.abandoned
        assert state.converged is False
        assert state.passes < 5000, (
            "it used the whole ceiling, so the ceiling is still the lock")

    def test_it_stops_at_the_first_pass_that_crosses_the_bound(self):
        """An identity, not a captured pass number.

        Whatever pass the guard stops on, the pass BEFORE it must be under
        the bound — otherwise the guard is firing late, and how late would
        be nobody's decision.
        """
        from ogr_slip2d.interslice import THRUST_SCALE_LIMIT
        system = _system()
        limit = THRUST_SCALE_LIMIT * _scale(system)
        state = _branch(system, RUNAWAY_LAMBDA, max_passes=5000,
                        patience=10 ** 9)
        assert state.abandoned == "thrust overflow"
        assert _peak(state) > limit, "it stopped without the bound crossed"
        before = _branch(system, RUNAWAY_LAMBDA, max_passes=state.passes - 1,
                         patience=10 ** 9)
        assert before.abandoned == "", before.abandoned
        assert _peak(before) <= limit, (
            "the pass before the guard fired was already over the bound")

    def test_everything_it_hands_back_is_still_a_number(self):
        """The point of cutting early: nothing downstream meets an infinity.

        ``math.fsum`` raises on -inf and +inf together, and it is reached
        from the moment expression of a circle, from ``moment_balance`` off
        one, and from ``thrust_is_admissible``.
        """
        system = _system()
        state = _branch(system, RUNAWAY_LAMBDA, max_passes=5000,
                        patience=10 ** 9)
        for name in ("boundary_e", "boundary_x", "normals", "resisting"):
            for v in getattr(state, name):
                assert math.isfinite(v), (name, v)
        assert math.isfinite(state.fos)

    def test_without_the_bound_the_same_branch_leaves_the_number_range(self):
        """What the guard is for, measured rather than asserted about.

        Without it the same lambda carries a thrust two hundred decades past
        anything the slope could hold, into every per-slice array the result
        publishes.
        """
        system = _system()
        scale = _scale(system)
        with _lifted():
            far = _branch(system, RUNAWAY_LAMBDA, max_passes=1000,
                          patience=10 ** 9)
        assert far.abandoned == ""
        assert _peak(far) / scale > 1e100, _peak(far) / scale


# ======================================================================
class TestTheBoundIsRelativeToTheModel:
    """A limit on a force written as a force is a limit that means one thing
    in metres and another in feet. ``AGENTS.md`` forbids it, and this class
    is what would go red the day someone wrote ``10000.0`` in kN."""

    def test_the_same_slope_at_ten_times_the_size_gets_the_same_verdict(self):
        small, big = _system(), _system(k=SIMILARITY_K)
        assert _scale(big) > _scale(small) * 50, (
            "the fixture stopped being a bigger version of the same slope")
        out = []
        for system in (small, big):
            state = _branch(system, RUNAWAY_LAMBDA, max_passes=5000,
                            patience=10 ** 9)
            out.append((state.abandoned, state.converged, state.passes,
                        _peak(state) / _scale(system)))
        assert out[0][:3] == out[1][:3], out
        assert abs(out[0][3] - out[1][3]) < 1e-6 * out[0][3], out

    def test_the_scale_is_not_the_weight_alone(self):
        """And that is a decision with a case behind it.

        The thin lens of the disjoint-mass problem carries 0.9 ft of soil at
        F = 34.3: small weight, large cohesion. A bound written against
        ``sum(W)`` would be tight there for a reason that has nothing to do
        with the thrust.
        """
        from ogr_slip2d.interslice import _force_scale
        system = _system()
        weight_only = math.fsum(abs(r.w_eff) for r in system.rows)
        scale = _force_scale(system.rows)
        assert scale > weight_only, (scale, weight_only)
        assert math.isclose(
            scale,
            math.fsum(abs(r.w_eff) + r.c_l + abs(r.h_drive)
                      + abs(r.t_active) + abs(r.t_passive)
                      for r in system.rows))


# ======================================================================
class TestTheCeilingIsNoLongerTheLock:
    """Step 3 of the ficha: with the bound in place, raise the ceiling IN
    THE TEST and check that nothing leaves the number range."""

    def test_no_branch_leaves_the_number_range_at_five_thousand_passes(self):
        """Step 3 of P-D118 — and it is GREEN ON BOTH SIDES, which is the
        finding rather than a weakness of the test.

        The ficha expects this to be the case that goes red without the
        bound, because it expects ``ValueError: -inf + inf in fsum``.
        Measured, the published solver does not raise it: the runaway ends
        in a non-finite ``f_new`` and a silent ``None`` instead. So this
        asserts what step 3 asks — that raising the ceiling in the TEST and
        not in the code leaves nothing outside the number range — and the
        discrimination lives in
        ``TestTheRunawayIsCutAndSaysWhy``. A test whose docstring does not
        say which of the two it is will be read as the one it is not.
        """
        lambdas = (-1.5, 0.0, ROOT_LAMBDA, 2.0, RUNAWAY_LAMBDA, 4.0)
        checked = 0
        for beta in (40.0, BETA):
            system = _system(beta)
            for lam in lambdas:
                for moment in (True, False):
                    state = _branch(system, lam, moment=moment,
                                    max_passes=5000, patience=10 ** 9)
                    if state is None:
                        continue
                    checked += 1
                    assert math.isfinite(_peak(state)), (beta, lam, moment)
                    for v in state.resisting:
                        assert math.isfinite(v), (beta, lam, moment, v)
        assert checked >= 16, checked

    def test_the_two_constants_the_ficha_freezes_are_where_they_were(self):
        """CONTROL — green before and after, and declared so.

        It guards against a mistake THIS design could make (buying the
        guard by loosening the two locks it is meant to relieve), not
        against the defect it removes. P-D118 freezes both until the bound
        has shown they are redundant, because moving them here would mix
        two causes.
        """
        from ogr_slip2d.interslice import MAX_PASSES, STALL_PATIENCE
        assert MAX_PASSES == 400
        assert STALL_PATIENCE == 80


# ======================================================================
class TestTheThreeRefusalsAreToldApart:
    """``n_thrust_rejected`` is about the stress state, ``n_passes_exhausted``
    about the solver's budget, ``n_thrust_overflow`` about the arithmetic
    leaving the range where it means anything. Three counters because they
    are three claims; the day they share one, the answer to "why did this
    lambda disappear" goes back to being "something went wrong"."""

    def test_a_runaway_raises_only_its_own_counter(self):
        system = _system()
        assert system.branches(RUNAWAY_LAMBDA) == (None, None)
        assert system.n_thrust_overflow > 0
        assert system.n_passes_exhausted == 0
        assert system.n_thrust_rejected == 0

    def test_a_stalled_branch_raises_none_of_them(self):
        """Measured, not assumed: at :data:`STALLING_LAMBDA` the moment
        branch stalls out with the thrust still at 0.11 of the scale, so
        this is a stall and not a runaway wearing its clothes."""
        from ogr_slip2d.interslice import THRUST_SCALE_LIMIT
        system = _system()
        state = _branch(system, STALLING_LAMBDA)
        assert state.converged is False and state.abandoned == ""
        assert _peak(state) < THRUST_SCALE_LIMIT * _scale(system)
        assert system.branches(STALLING_LAMBDA) == (None, None)
        assert system.n_thrust_overflow == 0

    def test_a_lambda_that_solves_raises_nothing_at_all(self):
        system = _system(tolerance=1e-6)
        ff, fm = system.branches(ROOT_LAMBDA)
        assert ff is not None and fm is not None, (ff, fm)
        assert system.n_thrust_overflow == 0
        assert system.n_passes_exhausted == 0


# ======================================================================
class TestTheReasonReachesTheUser:
    """A note nobody shows is a note that does not exist. The count travels
    in ``details`` and the sentence in ``analysis_runner``, and neither of
    them vetoes anything — ``error_message`` feeds ``is_valid``, which
    ``search.surface_score`` scores at infinity, and that is D37/C1."""

    def test_a_real_run_publishes_the_count(self):
        """The whole path, with nothing patched: a real slope, the shipped
        tolerance, the outer lambda search losing one of its samples."""
        r = _result(OVERFLOW_MID, OVERFLOW_BETA, OVERFLOW_TOL)
        details = r.details or {}
        # Reported by key and not by dumping ``details``: it carries the
        # n+1 thrust arrays, and a failure that prints them buries itself.
        told = {k: details.get(k) for k in
                ("lambdas_lost_to_thrust_overflow", "lambdas_lost_to_budget",
                 "lambda_search_fell_back")}
        assert told["lambdas_lost_to_thrust_overflow"], told
        assert told["lambdas_lost_to_budget"] == 0, (
            "the two losses are being confused for one another: %r" % (told,))

    def test_and_the_note_says_it_without_vetoing(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        from ogr_slip2d.interslice import THRUST_SCALE_LIMIT
        r = _result(OVERFLOW_MID, OVERFLOW_BETA, OVERFLOW_TOL)
        notes = lambda_fallback_notes(r)
        said = [n for n in notes if "thrust" in n]
        assert said, notes
        assert ("%g" % THRUST_SCALE_LIMIT) in said[0], said[0]
        # A note is not a veto: ``error_message`` feeds ``is_valid``, which
        # ``search.surface_score`` scores at infinity, so a surface that
        # lost a lambda here still competes for the minimum. D37/C1.
        assert r.error_message == "", r.error_message
        assert r.reason == "", r.reason
        assert r.converged is True
        # ``admissible`` is False on THIS plane and was before the bound
        # existed — the soil faces come out in net tension and the thrust
        # criterion is relaxed, which is the problem-85 path and nothing to
        # do with D118. Asserted against the same run with the bound lifted
        # rather than against the word False, so that it stays a statement
        # about what this change does NOT move.
        with _lifted():
            was = _result(OVERFLOW_MID, OVERFLOW_BETA, OVERFLOW_TOL)
        assert r.admissible == was.admissible
        assert r.fos == was.fos, (r.fos, was.fos)

    def test_the_note_stays_quiet_when_nothing_overflowed(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        class _Fake:
            details = {"lambda_search_fell_back": True,
                       "lambdas_lost_to_thrust_overflow": 0}
        assert lambda_fallback_notes(_Fake()) == []

    def test_it_stays_quiet_when_the_search_found_its_bracket(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        class _Fake:
            details = {"lambda_search_fell_back": False,
                       "lambdas_lost_to_thrust_overflow": 7}
        assert lambda_fallback_notes(_Fake()) == []

    def test_it_avoids_the_three_substrings_the_bank_reserves(self):
        """The verification bank greps these out of ``avisos`` to classify a
        row, so a new note that happens to contain one would file itself
        under somebody else's defect."""
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        class _Fake:
            details = {"lambda_search_fell_back": True,
                       "lambdas_lost_to_thrust_overflow": 2}
        notes = lambda_fallback_notes(_Fake())
        assert notes
        for note in notes:
            for text in (note, note.lower()):
                assert "edge of the search grid" not in text
                assert "path_optimize" not in text
                assert not ("stable" in text and "head" in text)


# ======================================================================
class TestNothingThatWasAnAnswerMoves:
    """CONSERVATION — green before and after, and declared so.

    It does not measure the defect; it measures that removing the defect
    cost nothing, which is the half of a numerical change that is easiest
    to leave unwritten and most expensive to get wrong. The comparison is
    an A/B in one process against the same solver with the bound lifted,
    so there is no snapshot to go stale.
    """

    def test_a_branch_that_was_an_answer_is_bit_for_bit_what_it_was(self):
        checked = 0
        for beta in BETAS:
            system = _system(beta)
            for lam in (-1.5, -0.5, 0.0, 0.5, ROOT_LAMBDA, 1.5, 2.0):
                for moment in (True, False):
                    now = _branch(system, lam, moment=moment, max_passes=400)
                    with _lifted():
                        was = _branch(system, lam, moment=moment,
                                      max_passes=400)
                    if now is None or not now.converged:
                        continue
                    checked += 1
                    assert was is not None and was.converged, (beta, lam)
                    assert now.fos == was.fos, (beta, lam, moment,
                                                now.fos, was.fos)
                    assert now.passes == was.passes, (beta, lam, moment)
        assert checked >= 40, checked

    def test_the_wedge_planes_do_not_move_at_three_tolerances(self):
        from ogr_slip2d.methods.base import method_registry
        from ogr_slip2d.slicer import slice_surface
        checked = 0
        for beta in BETAS:
            for method_id in ("spencer", "gle_morgenstern_price"):
                for tol in (1e-3, 1e-6, 1e-10):
                    seen = []
                    for lift in (False, True):
                        ctx = _lifted() if lift else contextlib.nullcontext()
                        with ctx:
                            project = _bare()
                            surface = _plane(beta)
                            sl = slice_surface(project, surface,
                                               num_slices=NSLICES)
                            r = method_registry()[method_id](
                                tolerance=tol,
                                max_iterations=400).compute_fos(
                                    project, surface, sl)
                        seen.append((r.fos, r.converged, r.error_message,
                                     (r.details or {}).get("lambda")))
                    checked += 1
                    assert seen[0] == seen[1], (beta, method_id, tol, seen)
        assert checked == len(BETAS) * 2 * 3, checked


# ======================================================================
class TestWhatThisDoesNotFix:
    """What was EVIDENCE for P-D116 and is now the record of its repair.

    ``F_f`` is a quotient whose numerator and denominator are dominated by
    the same runaway terms, so their RATIO can settle while both explode.
    Until v0.1.179 the convergence test looked only at that ratio, and a
    branch could report a fixed point it had reached on nonsense: the bound
    of this version kept those states out of the ANSWER, but it did not stop
    the test from being fooled. This class was pinned with the number in
    front "so that the version which fixes P-D116 can see exactly what it
    moved", and v0.1.179 (D145) is that version.

    What it moved, measured on the very branch pinned here: with the bound
    lifted, the force branch of the 55 degree plane at lambda -5.55 used to
    be declared converged with its thrust at more than 1e9 times the force
    scale. It is not declared converged any more, because the acceptance now
    asks about the thrust residual as well as the step in F, and this is the
    most extreme case in the suite of the two disagreeing.

    What still is not fixed, and stays here: ``converged`` does not mean
    "admissible". The pair test asks whether X has stopped MOVING, and
    ``thrust_is_admissible`` asks about the sign of the thrust it settled
    on. They remain two different questions and v0.1.179 does not merge
    them.
    """

    def test_a_converged_branch_is_no_longer_built_on_a_runaway(self):
        """v0.1.179 (D145) — the flip this class was written to record. The
        aserrtions are the same three facts about the same branch; the one
        that changed is the verdict, and it changed from True to False.

        The two thrust facts are asserted BEFORE the verdict and unchanged,
        so that the case cannot go green because the fixture stopped
        producing a runaway — which is how a test of a repaired defect
        quietly stops measuring anything.
        """
        from ogr_slip2d.interslice import THRUST_SCALE_LIMIT
        system = _system(55.0)
        limit = THRUST_SCALE_LIMIT * _scale(system)
        with _pair_off(), _lifted():
            fooled = _branch(system, -5.55, tolerance=1e-3, moment=False,
                             max_passes=400)
        # The three facts this class was pinned with, unchanged and asserted
        # FIRST: the branch was declared converged, and its thrust was past
        # a billion times the force scale while it said so. Measured with
        # the old acceptance, because they describe what v0.1.179 moved
        # away from — and because a case that only asserted the new verdict
        # would go green the day the fixture stopped producing a runaway.
        assert fooled is not None and fooled.converged is True
        assert _peak(fooled) > 1e9 * _scale(system), _peak(fooled)
        assert _peak(fooled) > limit
        # And the verdict. ``None`` and not merely "not converged": with the
        # bound lifted the branch runs on and leaves through one of the
        # guards that refuse a state outright, which is a stronger answer
        # than the one this class was written expecting.
        with _lifted():
            now = _branch(system, -5.55, tolerance=1e-3, moment=False,
                          max_passes=400)
        assert now is None or now.converged is False, now.fos

    def test_and_the_bound_is_what_keeps_it_out_of_the_answer(self):
        system = _system(55.0)
        state = _branch(system, -5.55, tolerance=1e-3, moment=False,
                        max_passes=400)
        assert state.abandoned == "thrust overflow", state.abandoned
        assert state.converged is False
