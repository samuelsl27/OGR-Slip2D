# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A branch is converged when the iteration CONTRACTS, not when one step is small.

WHAT INVARIANT THIS PROTECTS. ``solve_branch`` iterates each of the two GLE
branches to its own fixed point, and the iterate is DAMPED —
``F <- 0.5*(F + f_new)``. A damped iterate has an oscillating transient: its
steps alternate large and small. Until v0.1.172 a single step under the
tolerance was enough to declare the branch converged, so one of the small
ones could fall under a loose tolerance BY LUCK at a fixed point that does
not contract at all. The lambda was then published with a factor of safety
that is not its own, it entered the bracket of the outer lambda search, and
it moved the answer. That is defect D116 of the verification bank, and it is
the exact reverse of D63 (v0.1.159): instead of throwing good lambdas away,
it admitted bad ones.

The rule this file enforces is therefore: **a branch may only be called
converged while its own step sequence is shrinking.** The acceptance test is
the classical one for a contractive fixed point — Isaacson & Keller (1966),
*Analysis of Numerical Methods*, section 3.1 — the step under the tolerance
AND the last two step ratios below 1, which ``interslice`` writes without a
division as ``step < prev_step < prev_step_2``.

WHY THE ANCHOR IS NOT IN THIS FILE. The external reference is the closed
form of a plane wedge, and it lives in ``tests/test_janbu_wedge_v1142.py``,
where ``TestSpencerAndGleSettleOnTheWedge`` asserts it. This file asserts the
MECHANISM instead. Splitting them is deliberate and the reason is on record
in ``test_interslice_budget_v1159.py``: a test of the mechanism that also
owned the reference value could be made to pass by moving the reference.

HOW THE TWO GATES WERE BUILT, because a test of a defect that cannot see the
defect is the trap this project has now walked into ten times (D101, D103,
D127, D129, D118). Neither gate is a snapshot of the old engine — both
reconstruct "where the iteration used to stop" from the CURRENT engine, by
capping ``max_passes`` at the pass the lucky step used to fire on, so nothing
here has to be re-measured if the arithmetic moves:

* the 50 degree plane, moment branch, lambda = 2.0 — the case the ficha
  names. At a tolerance of 1e-3 the old criterion fired on pass 5; the
  iterate there is 16.5 % away from the fixed point of 0.83037, which takes
  585 passes to reach;
* ACADS 1(a), the circle centred at (36, 45) with R = 20, force branch,
  lambda = -1.0. At 0.005 the old criterion fired on pass **2**, which is the
  two-pass row of the ficha's table reproduced on a published model, and the
  iterate there is **13.3 %** away from the fixed point of 0.80135. The
  ficha points at ``test_acads_validation_v178.py`` for ACADS 1(c); that file
  says in its own docstring that 1(c) is not in it, so the second gate is
  built on 1(a), whose geometry is six vertices and one material.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a guard gives is what cost this project two versions in v0.1.82-84.
The criterion rules out the lucky step. It does NOT put the accepted value
within the tolerance of the fixed point: a contraction of ratio r stopped on
a step of ``tol`` still sits within ``tol*r/(1-r)`` of the root, and r
reaches 0.9614 on the wedge. Adding that residual estimate was measured and
deliberately not adopted — it converts lambdas that give a bad number into
lambdas that are LOST, which is D63 running backwards — and
``TestWhatThisDoesNotFix`` asserts the gap so that nobody reads the new
criterion as the wider promise.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# ----------------------------------------------------------------------
# The plane wedge fixture, built here rather than imported: the modules in
# ``tests/`` cannot import one another outside the runner.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
BETA = 50.0

#: The lambda the ficha names. Its moment branch is a SLOW contraction —
#: ratio 0.9614, 585 passes to 1e-12 — whose oscillating transient drops far
#: on pass 5 by luck. Not a divergent branch: that is 2.5, which
#: ``test_interslice_budget_v1159`` already calls ``WANDERING_LAMBDA``.
LUCKY_LAMBDA = 2.0

#: The pass the old criterion fired on, at each of the two loose tolerances.
#: Used to CAP ``max_passes`` and so rebuild the old stopping point from the
#: current engine, rather than to assert a number.
LUCKY_PASS = {5e-3: 3, 1e-3: 5}

#: ACADS 1(a), and the one circle of it this file uses. Chosen by sweeping
#: the model and keeping the branch whose early acceptance was FURTHEST from
#: its fixed point, which is what makes it a gate rather than a coincidence.
ACADS_CIRCLE = (36.0, 45.0, 20.0)
ACADS_LAMBDA = -1.0
ACADS_SLICES = 25

#: Geometry times this AND cohesion times this is the same slope in
#: different units: weight goes as the square of a length and a cohesive
#: force as its product with one.
SIMILARITY_K = 10.0

#: Where a fixed point is resolved when it is used as the yardstick. The
#: patience is lifted because the yardstick must not be the thing under
#: test: a branch abandoned by the stall detector would hand back its last
#: iterate and every distance measured against it would be meaningless.
REFERENCE_TOL = 1e-12
REFERENCE_PASSES = 4000
NO_PATIENCE = 10 ** 9


def _daylight_x(beta_deg, k=1.0):
    return (TOE + H / math.tan(math.radians(beta_deg))) * k


def _bare(k=1.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0 * k), Vertex(60 * k, -10.0 * k), Vertex(60 * k, H * k),
        Vertex(CREST * k, H * k), Vertex(TOE * k, 0), Vertex(0, 0),
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


def _system(beta_deg=BETA, k=1.0):
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
                     tolerance=1e-14)


# ----------------------------------------------------------------------
def _acads_1a():
    """ACADS problem 1(a), verbatim from the statement — the same six
    vertices and one material as ``test_acads_validation_v178``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(20, 20), Vertex(70, 20), Vertex(70, 35),
        Vertex(50, 35), Vertex(30, 25), Vertex(20, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ACADS 1(a)")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=3.0, friction_angle=19.6))]
    return p


def _acads_system():
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import resolve_support_terms
    from ogr_slip2d.surface import SlipCircle

    p = _acads_1a()
    c = SlipCircle(*ACADS_CIRCLE)
    sl = slice_surface(p, c, num_slices=ACADS_SLICES)
    assert sl is not None and sl.slices, "the circle produced no slices"
    sup = resolve_support_terms(p, c, sl, 1.0)
    return GLESystem(sl.slices, [1.0] * (len(sl.slices) + 1),
                     0.0, 0.0, 1.0, c.radius, c.centre_y, sup, None,
                     tolerance=1e-3)


# ----------------------------------------------------------------------
def _branch(system, lam, tolerance, moment=True, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos if moment else None,
                        tolerance, 1.0, **kw)


def _fixed_point(system, lam, moment=True):
    """The branch driven to its fixed point, as a yardstick and not as a
    result: tight tolerance, the pass budget raised and the stall detector
    out of the way, so that what comes back is the root and not wherever
    one of the solver's own limits stopped it."""
    st = _branch(system, lam, REFERENCE_TOL, moment,
                 max_passes=REFERENCE_PASSES, patience=NO_PATIENCE)
    assert st is not None and st.converged, (lam, st)
    return st.fos


def _iterate_at(system, lam, pass_count, moment=True):
    """Where the iterate WAS after ``pass_count`` passes.

    This is how the two gates avoid holding a snapshot of the engine they
    replace: capping the budget reproduces the old stopping point out of
    the current arithmetic. It is not bit-identical to what the old
    criterion published — that one took ``f_new`` and this one the damped
    average of the same pass — and it does not need to be, because what the
    gates assert is a DISTANCE of ten per cent and more.
    """
    st = _branch(system, lam, 1e-14, moment, max_passes=pass_count)
    assert st is not None and st.passes == pass_count, (lam, st)
    return st.fos


def _rel(a, b):
    return abs(a - b) / abs(b)


# ======================================================================
class TestALuckyStepIsNotConvergence:
    """The defect itself, on two models that share no geometry, no
    material and no branch: the 50 degree plane on its MOMENT branch and a
    published ACADS circle on its FORCE branch."""

    def test_the_wedge_branch_is_not_accepted_at_the_lucky_pass(self):
        """The count and not the value: at both loose tolerances the branch
        used to stop on pass 3 and pass 5, and it may not any more."""
        system = _system()
        for tol, lucky in LUCKY_PASS.items():
            st = _branch(system, LUCKY_LAMBDA, tol)
            assert st is not None, tol
            assert st.passes > lucky, (tol, st.passes, lucky)

    def test_and_where_it_used_to_stop_was_far_from_the_fixed_point(self):
        """Which is what makes it a defect and not a preference. The
        iterate at the lucky pass is a sixth of the way out; what the
        branch settles on now is inside a quarter of that."""
        system = _system()
        root = _fixed_point(system, LUCKY_LAMBDA)
        for tol, lucky in LUCKY_PASS.items():
            was = _rel(_iterate_at(system, LUCKY_LAMBDA, lucky), root)
            assert was > 0.15, (tol, was)
            st = _branch(system, LUCKY_LAMBDA, tol)
            if st.converged:
                assert _rel(st.fos, root) < 0.25 * was, (tol, st.fos, was)

    def test_the_same_thing_on_a_published_model(self):
        """ACADS 1(a), force branch, at the tolerance ``ProjectSettings``
        ships. Two passes, and thirteen per cent out."""
        system = _acads_system()
        root = _fixed_point(system, ACADS_LAMBDA, moment=False)
        was = _rel(_iterate_at(system, ACADS_LAMBDA, 2, moment=False), root)
        assert was > 0.13, was
        st = _branch(system, ACADS_LAMBDA, 5e-3, moment=False)
        assert st is not None and st.converged
        assert st.passes > 2, st.passes
        assert _rel(st.fos, root) < 0.02, (st.fos, root)

    def test_tightening_the_tolerance_walks_towards_the_fixed_point(self):
        """The property the lucky step breaks, asserted as a trend rather
        than as three numbers: where a lucky step lands has nothing to do
        with how tight the tolerance is, so under the old criterion this
        trend was an accident rather than a consequence.

        CONTROL, and measured rather than assumed: it is GREEN on both
        sides of this change, because on this particular branch the lucky
        value happened to fall on the right side of the trend. It is here
        for what it would catch if the criterion ever started stopping
        branches in the wrong order, not for the defect — and saying which
        of the two it is, is the point, because a case that does not will
        be read as the one it is not."""
        system = _acads_system()
        root = _fixed_point(system, ACADS_LAMBDA, moment=False)
        errs = []
        for tol in (5e-3, 1e-3, 1e-4):
            st = _branch(system, ACADS_LAMBDA, tol, moment=False)
            assert st is not None and st.converged, tol
            errs.append(_rel(st.fos, root))
        assert errs[0] > errs[1] > errs[2], errs

    def test_and_on_the_wedge_too_as_far_as_it_converges(self):
        """The same trend on the other model. It stops at 1e-3 and the
        reason is not this criterion: at 1e-4 this branch is taken by the
        stall detector, which ``TestWhatThisDoesNotFix`` records.

        CONTROL as well, and for the same measured reason as the case
        above: green on both sides. Two of the five cases in this class
        are controls and three discriminate, and the file says which."""
        system = _system()
        root = _fixed_point(system, LUCKY_LAMBDA)
        errs = []
        for tol in (5e-3, 1e-3):
            st = _branch(system, LUCKY_LAMBDA, tol)
            assert st is not None and st.converged, tol
            errs.append(_rel(st.fos, root))
        assert errs[0] > errs[1], errs


# ======================================================================
class TestWhatTheCriterionIs:
    """The mechanism, asserted through behaviour and never by reading the
    source: seeing one ratio takes two steps and seeing two takes three."""

    def test_no_branch_converges_before_its_third_pass(self):
        """The price of the criterion, and the one thing that would give it
        away if the sentinel it starts from were ``+inf`` instead of
        ``-inf``: with ``+inf`` the chained comparison is already true on
        the second pass, having seen a single ratio, and the two-pass
        acceptance this file exists to refuse comes straight back.

        Swept rather than sampled, and BOTH sides are asserted: that
        nothing lands under three, and that three is actually reached, so
        the case cannot be satisfied by a solver that simply got slower.
        """
        system = _system()
        seen = []
        for k in range(13):
            lam = -1.0 + 0.25 * k
            for tol in (5e-3, 1e-3, 1e-4):
                for moment in (True, False):
                    st = _branch(system, lam, tol, moment)
                    if st is None or not st.converged:
                        continue
                    seen.append(st.passes)
                    assert st.passes >= 3, (lam, tol, moment, st.passes)
        assert seen, "the sweep stopped producing converged branches"
        assert min(seen) == 3, min(seen)

    def test_a_branch_that_lands_on_its_answer_converges_at_once(self):
        """``dF = 0`` — the exact fixed point, which is the strongest
        contraction there is and the one the ratio test cannot see, because
        ``0 < 0`` is false.

        CONTROL, declared: it is green on both sides of this change, since
        the criterion it replaces accepted a zero step without asking
        anything. What it guards is an error THIS design can make and the
        old one could not — drop the ``step == 0.0`` clause and the branch
        never beats its own zero step again, dies by stall, and the lambda
        disappears. So the case guards a clause and not a slope, and the
        ficha names it as the ``I5`` identity.

        Driven with a CONSTANT moment expression rather than a real one:
        the guard is arithmetic, not geotechnics, and a constant is the only
        way to make the step identically zero from the first pass.
        """
        from ogr_slip2d.interslice import solve_branch
        system = _system()
        target = 1.234567
        st = solve_branch(system.rows, system.lambda_boundary(0.0),
                          lambda normals, resisting: target,
                          1e-14, target)
        assert st is not None and st.converged, st
        assert st.passes == 2, st.passes
        assert st.fos == target, st.fos


# ======================================================================
class TestTheScaleIsTheModelsOwn:
    """A criterion written on RATIOS of steps carries no units, and this is
    where that is checked rather than assumed."""

    def test_the_same_slope_ten_times_larger_gives_the_same_verdict(self):
        """Geometry times k and cohesion times k is the same slope in other
        units, so the factor of safety — a ratio — must not move at all,
        and neither must the pass on which the branch stops."""
        small = _system()
        large = _system(k=SIMILARITY_K)
        for tol in (5e-3, 1e-3):
            a = _branch(small, LUCKY_LAMBDA, tol)
            b = _branch(large, LUCKY_LAMBDA, tol)
            assert (a is None) == (b is None), tol
            assert a.converged == b.converged, tol
            assert a.passes == b.passes, (tol, a.passes, b.passes)
            assert _rel(a.fos, b.fos) < 1e-9, (tol, a.fos, b.fos)


# ======================================================================
class TestWhatThisDoesNotFix:
    """Rule 6 made executable. Both of these are real, both are measured,
    and both are deliberately left alone — so they are asserted here, and
    the day one of them is repaired this class goes red and says which."""

    def test_an_accepted_value_can_still_sit_far_from_the_tolerance(self):
        """The residual estimate that was NOT adopted. A contraction of
        ratio r stopped on a step of ``tol`` sits within ``tol*r/(1-r)`` of
        the root, and on this branch r is 0.96, so the accepted value is
        tens of times the tolerance away from the fixed point. Asserted so
        that the criterion is not read as the wider promise it does not
        make."""
        system = _system()
        root = _fixed_point(system, LUCKY_LAMBDA)
        tol = 5e-3
        st = _branch(system, LUCKY_LAMBDA, tol)
        assert st is not None and st.converged
        assert abs(st.fos - root) > 3 * tol, (st.fos, root, tol)

    def test_the_stall_record_still_takes_a_slow_branch(self):
        """The limit ``STALL_PATIENCE`` documents: an accidental early
        record is what the genuine contraction then has to beat. At 1e-4
        this branch is still abandoned rather than converged, and it is
        abandoned by the stall test — not by the pass budget and not by the
        thrust bound, which is what tells the three refusals apart."""
        from ogr_slip2d.interslice import MAX_PASSES
        system = _system()
        st = _branch(system, LUCKY_LAMBDA, 1e-4)
        assert st is not None
        assert st.converged is False, st.fos
        assert st.abandoned == "", st.abandoned
        assert st.passes < MAX_PASSES, st.passes

    def test_but_it_no_longer_decides_the_answer_at_the_looser_ones(self):
        """The half of that limit this version DOES move, and the reason it
        is worth writing down: the record used to be set by the lucky step
        itself, so the two defects fed each other. With the lucky step
        refused, the same branch at 1e-3 now converges instead of being
        abandoned."""
        system = _system()
        st = _branch(system, LUCKY_LAMBDA, 1e-3)
        assert st is not None and st.converged is True, st
        assert st.passes > LUCKY_PASS[1e-3], st.passes


# ======================================================================
class TestTheControl:
    """Declared CONTROL, and the docstrings say so in so many words,
    because a case that does not say which of the two things it is will be
    read as the one it is not.

    These are green on BOTH sides of this change and they are here to guard
    against an error THIS design can make — buying the criterion by making
    every branch slower, or by disturbing the branches that were already
    contracting cleanly — and not against the defect it removes.
    """

    def test_a_clean_contraction_is_untouched(self):
        """CONTROL. At lambda = 0 the step ratio is a constant 0.729 from
        the first pass, so there is no oscillating transient for the
        criterion to wait out and nothing about this branch may move. The
        two tight tolerances are the ones asserted because at 0.005 and
        1e-3 this branch converges on pass 2 and the three-pass minimum
        moves it by design — which is the trade, and it is stated rather
        than hidden."""
        system = _system()
        for tol, expected in ((1e-4, 10), (1e-10, 53)):
            st = _branch(system, 0.0, tol)
            assert st is not None and st.converged, tol
            assert st.passes == expected, (tol, st.passes, expected)

    def test_the_ladder_of_the_wedge_keeps_decreasing(self):
        """CONTROL. The staircase of v0.1.159: at a tight tolerance the
        steps of a converging branch shrink monotonically, which is the
        property the whole criterion rests on. Measured on the branch as it
        runs rather than claimed, by asking for the same branch at
        successive pass budgets and watching the iterate settle."""
        system = _system()
        root = _fixed_point(system, 0.0)
        errs = [_rel(_iterate_at(system, 0.0, n), root)
                for n in (10, 20, 40, 60)]
        assert all(b < a for a, b in zip(errs, errs[1:])), errs

    def test_a_branch_that_never_contracts_is_still_refused(self):
        """CONTROL. The divergent lambda of ``test_interslice_budget_v1159``
        is refused before this change and after it. It is here so that a
        future reading of this file cannot mistake the criterion for the
        thing that rejects a runaway — that is the thrust bound of
        v0.1.171, and it keeps its own file."""
        system = _system()
        st = _branch(system, 2.5, 1e-3)
        assert st is not None
        assert st.converged is False, st.fos
