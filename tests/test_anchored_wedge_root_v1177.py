# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The anchor does not destroy the root. It moves it past the last lambda whose
moment branch can still be solved.

WHAT INVARIANT THIS PROTECTS. On a plane the sliding mass is one rigid wedge,
so every method that closes global force equilibrium owes the closed form
(Coulomb 1776; the modern statement, with the support resolved on the base,
is Duncan & Wright 2005 §6). Spencer and GLE reach it through a lambda: the
inter-slice inclination where the force and the moment factors agree. This
file asserts that when that lambda is not found, the program's own account of
WHY has to match what the branches actually do — and it pins the measurement
that says what they do, because the previous account was wrong.

THE QUESTION, AND THE ANSWER. Defect D119 of the verification bank, opened by
v0.1.159 §8: with the 120 kN/m anchor, Active or Passive, the 50 degree plane
has no lambda bracket, while the 35, 40 and 45 degree planes do. The residual
at the nearest lambda is 0.03 to 0.20 and does not shrink with the tolerance,
and that was read as "there is no root to converge to". Measured sweeping
lambda from -2 to +3 over the twelve combinations of beta and anchor with
Spencer, plus the four GLE cells where the finding lives
(``docs/audits/anchored_wedge_lambda_v1177.md``), the three explanations the
bank's ticket offered are all wrong as written:

* NOT the reinforcement breaking the telescoping of the force branch. ``F_f``
  is EXACTLY constant in lambda with the anchor exactly as without it -- the
  reinforcement enters the thrust recursion, which telescopes out of the
  global balance, and the reinforcement terms of that balance do not depend
  on lambda. Measured spread over the sweep: 1e-14 to 1e-11, and ``F_f``
  reproduces the closed form to 7.3e-11 in the worst of the sixteen cells
  measured;
* NOT parallel branches. ``F_m`` closes on ``F_f`` monotonically: Passive at
  50 degrees goes from g = -0.0443 at lambda 0.90 to -0.0051 at lambda 1.275;
* NOT a root outside the range. There IS a root, at lambda 1.3199, where
  F = 1.74830 -- the closed form to 8e-6.

What happens instead is that the moment branch STOPS BEING SOLVABLE just
short of it. Its damped iteration ``F <- 0.5*(F + f_new)`` turns from the
monotone contraction it is without the anchor (ratio +0.89 at the root of the
bare 50 degree plane, measured in v0.1.159) into a period-2 oscillation whose
amplitude GROWS, and the orbit leaves the region where the factor of safety
is finite and positive: ``solve_branch`` returns ``None`` -- which is none of
the three exits ``GLESystem.branches`` counts. At lambda 1.30, Passive, that
happens on pass 69.

AND 69 IS THE WHOLE POINT: the relaxation rescue of v0.1.176 enters on the
pass after ``STALL_PATIENCE`` = 80, so it never sees this branch, and neither
does the stall test. Bring the gate forward -- ``patience`` is an ARGUMENT of
``solve_branch`` and nothing here changes a module constant -- and the same
solver walks straight to the root it was losing. That is what the classes
below assert, with the gate-independence of the recovered fixed point as the
control that what is reached is a fixed point and not wherever an iteration
happened to stop.

SO WHY THAT PLANE AND NOT THE OTHERS, which is what D119 asked. Because the
anchor moves the crossing UP in lambda (it raises F_f far more than it raises
F_m at a given lambda, and F_m has to fall further to meet it) while it moves
the last solvable lambda DOWN. At 35, 40 and 45 degrees the crossing still
lands inside; at 50 it lands outside: the crossing is at 1.3199 and the
shipped solver loses the branch somewhere between 1.275, which it still
solves, and 1.30, which it does not. Nothing about the anchor is special to
50 degrees except that this is where those two curves cross each other.

WHAT THIS FILE DOES NOT CLAIM. Not that the Active cell has a reachable root:
there the escape is far faster (pass 39 at lambda 1.00, pass 7 at lambda 1.30)
and no gate reaches a fixed point past the crossing, so its root is measured
only as "g is still negative and rising at the last lambda anyone can solve".
Not that every fallback hides a root -- the 45 degree Passive cell falls back
too and its g keeps ONE sign over the whole solvable range, which is the
honest report the original reading described. And nothing at all about
whether the branch solver SHOULD be changed: that is bank defect D148,
reported and deliberately not fixed here (rule 6).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: The fixture, literally the one in ``test_interslice_budget_v1159.py`` and
#: ``test_janbu_wedge_v1142.py``: four vertices and one material. Built here
#: rather than imported because the modules in ``tests/`` cannot import one
#: another outside the runner.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
TIGHT = 1e-10
MAX_IT = 400

#: The plane whose root the anchor pushes out of reach, and the three lambdas
#: that say so: the last one the shipped solver reaches, the first one it
#: loses, and the one just past the crossing.
BETA_STEEP = 50.0
LAST_SOLVED = 1.275
FIRST_LOST = 1.30
PAST_ROOT = 1.32

#: A gate early enough to catch the branch before its orbit escapes. Any
#: value in 25..50 works on this fixture; the cases below check that WHICH
#: one is used does not change the answer.
EARLY_GATE = 30


def _daylight_x(beta_deg):
    return TOE + H / math.tan(math.radians(beta_deg))


def _bare():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    return p


def _anchored(application=None):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _bare()
    p.support_types = [EndAnchored(anchor_capacity=120.0,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(34.0, 6.0), tail=Vertex(48.0, 11.0),
        force_application=application or ForceApplication.ACTIVE,
        orientation=ForceOrientation.USER_DEFINED, user_angle_deg=15.0)]
    return p


def _plane(beta_deg=BETA_STEEP):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _slices(project, beta_deg):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, _plane(beta_deg), num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    return sl


def _system(project, beta_deg=BETA_STEEP, method_id="spencer"):
    """The ``GLESystem`` the METHOD builds, and the reason this helper is not
    the one in ``test_interslice_budget_v1159.py``.

    That one passes ``sup=None``, which puts the reinforcement in the FORCE
    branch -- it reaches ``SliceRow.t_active``/``t_passive`` through the
    slices -- and leaves it out of the MOMENT closure, which receives it
    through that very argument. Measuring the anchored wedge through it
    measures a system nobody solves. Everything below mirrors
    ``spencer.py``: the seismic pair, the sign of the driving force, the
    axis, the resolved support and the branch budget.
    """
    from ogr_slip2d.interslice import GLESystem, branch_budget
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.support_integration import resolve_support_terms

    surface = _plane(beta_deg)
    sl = _slices(project, beta_deg)
    s_list = sl.slices
    raw = sum(s.weight * math.sin(s.base_angle) for s in s_list)
    sign = 1.0 if raw >= 0 else -1.0
    sup = resolve_support_terms(project, surface, sl, sign)
    if method_id == "spencer":
        shape = [1.0] * (len(s_list) + 1)
    else:
        from ogr_slip2d.methods.gle import GLEMorgensternPrice
        m = GLEMorgensternPrice(tolerance=TIGHT, max_iterations=MAX_IT)
        shape = [m.f_func(x, s_list[0].base_x_left, s_list[-1].base_x_right)
                 for x in m._boundary_x(sl)]
    return GLESystem(s_list, shape, 0.0, 0.0, sign, None, None, sup,
                     axis_for(project, surface), tolerance=TIGHT,
                     initial_fos=1.0, max_passes=branch_budget(MAX_IT))


def _closed_form(project, beta_deg=BETA_STEEP):
    """The wedge, from geometry and the model's own support terms.

    The external reference of this file (Coulomb 1776; Duncan & Wright 2005
    §6). Same expression as ``_wedge`` in ``test_janbu_wedge_v1142.py``,
    where every premise it rests on is asserted rather than assumed.
    """
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.support_integration import resolve_support_terms

    sl = _slices(project, beta_deg)
    raw = sum(slice_forces(s, 0.0, 0.0).w_total * math.tan(s.base_angle)
              for s in sl.slices)
    sup = resolve_support_terms(project, _plane(beta_deg), sl,
                                1.0 if raw >= 0 else -1.0)
    t_n, t_act, t_pas = ((math.fsum(sup.n_press), sup.total_active_t(),
                          sup.total_passive_t()) if sup.present
                         else (0.0, 0.0, 0.0))
    a = math.radians(beta_deg)
    W = GAMMA * 0.5 * H * (_daylight_x(beta_deg) - CREST)
    num = COH * (H / math.sin(a)) + (W * math.cos(a) + t_n) * math.tan(
        math.radians(PHI))
    return (num + t_pas) / (W * math.sin(a) - t_act)


def _moment(system, lam, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos, TIGHT, kw.pop("initial_fos", 1.0),
                        **kw)


def _force(system, lam, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam), None,
                        TIGHT, 1.0, **kw)


def _fixed_point(system, lam, gate, initial_fos=1.0):
    """``F_m`` at one lambda through a gate given as an ARGUMENT.

    ``patience`` governs two things at once inside ``solve_branch``: when the
    v0.1.176 rescue enters, and when the stall test gives up. Lowering it
    therefore brings the rescue forward, which is the whole experiment -- and
    it is an argument of a public function, so nothing global moves and
    nothing has to be restored (rule 5).
    """
    st = _moment(system, lam, initial_fos=initial_fos, max_passes=4000,
                 patience=gate)
    return None if (st is None or not st.converged) else st.fos


def _reach(system, lam, gates=(25, 30, 40, 45), starts=(1.0, None)):
    """The fixed point at one lambda, tried through several gates AND several
    starting values, with the agreement between them returned.

    Both matter, and which one matters changes with lambda: at 1.315 only the
    later gates arrive, at 1.32 only the start near the wedge does. That is
    itself a measurement — the window narrows as the crossing approaches —
    and it is why no case below hangs on one combination. ``None`` in
    ``starts`` means the force branch's own value, which is the wedge and
    therefore the best guess available without assuming the answer.

    Returns ``(value, paths, spread)`` or ``(None, 0, None)``.
    """
    fallback = _force(system, 0.0, max_passes=MAX_IT)
    seen = []
    for gate in gates:
        for start in starts:
            if start is None:
                if fallback is None:
                    continue
                start = fallback.fos
            value = _fixed_point(system, lam, gate, initial_fos=start)
            if value is not None:
                seen.append(value)
    if not seen:
        return None, 0, None
    return seen[0], len(seen), max(seen) - min(seen)


def _dies_on(system, lam, ceiling=400):
    """The first pass on which the branch stops having a value at all.

    Zero when it never does. Found by bisection on ``max_passes`` because
    ``solve_branch`` reports no trace of its own orbit: a branch that comes
    back ``None`` came back with nothing to read.
    """
    if _moment(system, lam, max_passes=ceiling, patience=10 ** 9) is not None:
        return 0
    lo, hi = 1, ceiling
    while lo < hi:
        mid = (lo + hi) // 2
        if _moment(system, lam, max_passes=mid, patience=10 ** 9) is None:
            hi = mid
        else:
            lo = mid + 1
    return lo


def _result(project, beta_deg=BETA_STEEP, method_id="spencer",
            tolerance=TIGHT):
    from ogr_slip2d.methods.base import method_registry
    return method_registry()[method_id](
        tolerance=tolerance, max_iterations=MAX_IT).compute_fos(
            project, _plane(beta_deg), _slices(project, beta_deg))


def _both():
    from ogr_core.support import ForceApplication
    return (("active", _anchored(ForceApplication.ACTIVE)),
            ("passive", _anchored(ForceApplication.PASSIVE)))


# ======================================================================
class TestTheForceBranchIsTheWedgeWhateverLambdaIs:
    """The first hypothesis the bank's ticket offered, refuted by measuring.

    It proposed that the reinforcement breaks the telescoping that makes
    ``F_f`` constant on a plane: the anchor adds ``t_mob*cos a`` to the
    thrust recursion, and that term does not telescope. True about the
    thrust, irrelevant to the branch — ``F_f`` comes out of the GLOBAL force
    balance, where the inter-slice shears cancel in pairs and the two
    reinforcement terms do not depend on lambda at all. So ``F_f`` is as
    constant with the anchor as without it, and equal to the closed form.

    Which matters beyond the refutation: it is what makes the crossing
    readable. If ``F_f`` is a horizontal line at the wedge, then "no root" can
    only mean that ``F_m`` never gets down to it, and the recovered root is
    obliged to BE the wedge — which is the check in the third class.
    """

    #: Inside the window where the FORCE branch converges in all three
    #: cells. It has one of its own: with the Active anchor it is cut for a
    #: runaway thrust from lambda 1.425 (D118), which is a different limit
    #: from the moment branch's and not what this class is about.
    LAMBDAS = (-1.0, 0.0, 0.8, 1.25)

    def _cells(self):
        return (("bare", _bare()),) + _both()

    def test_it_does_not_move_with_lambda_anchor_or_not(self):
        for name, project in self._cells():
            system = _system(project)
            seen = []
            for lam in self.LAMBDAS:
                state = _force(system, lam, max_passes=MAX_IT)
                assert state is not None and state.converged, (name, lam)
                seen.append(state.fos)
            spread = (max(seen) - min(seen)) / seen[0]
            assert spread < 1e-9, (name, spread, seen)

    def test_and_it_is_the_closed_form(self):
        for name, project in self._cells():
            state = _force(_system(project), 0.0, max_passes=MAX_IT)
            wedge = _closed_form(project)
            assert abs((state.fos - wedge) / wedge) < 1e-8, (name, state.fos,
                                                             wedge)


# ======================================================================
class TestTheMomentBranchStopsBeingSolvableBeforeTheCrossing:
    """What actually happens, and the fourth exit nobody counts.

    ``GLESystem.branches`` tells three reasons for abandoning a branch apart
    — a runaway thrust, an exhausted budget, a stall — and reports each one.
    This is a fourth: ``solve_branch`` returns ``None``, having produced a
    factor of safety that is not finite and positive, and there is no state
    to read and no counter to raise. It is reached here on pass 69 of the
    Passive cell at lambda 1.30, which is BEFORE ``STALL_PATIENCE``, so
    neither the stall test nor the v0.1.176 rescue is ever consulted.
    """

    def test_the_last_solvable_lambda_is_still_short_of_the_crossing(self):
        """Both branches converge, and ``F_m`` is still ABOVE ``F_f``: the
        search has not crossed anything by the time it runs out of lambdas."""
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.PASSIVE))
        force = _force(system, LAST_SOLVED, max_passes=MAX_IT)
        moment = _moment(system, LAST_SOLVED, max_passes=MAX_IT)
        assert force is not None and force.converged
        assert moment is not None and moment.converged, moment
        assert force.fos - moment.fos < 0.0, (force.fos, moment.fos)

    def test_the_next_lambda_has_no_branch_at_all(self):
        """Not stalled, not out of budget, not a runaway thrust: ``None``,
        which is the one outcome ``branches`` cannot name."""
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.PASSIVE))
        assert _moment(system, FIRST_LOST, max_passes=MAX_IT) is None
        assert _force(system, FIRST_LOST, max_passes=MAX_IT) is not None

    def test_and_it_gives_up_before_the_rescue_could_see_it(self):
        """The load-bearing number of this whole file. The rescue enters on
        the pass after ``STALL_PATIENCE``; this branch is gone before that,
        so the mechanism that cured the period-2 cycle of verification
        problem 091 in v0.1.176 never gets the chance here."""
        from ogr_core.support import ForceApplication
        from ogr_slip2d.interslice import STALL_PATIENCE
        system = _system(_anchored(ForceApplication.PASSIVE))
        died = _dies_on(system, FIRST_LOST)
        assert 0 < died < STALL_PATIENCE, (died, STALL_PATIENCE)

    def test_so_the_shipped_search_reports_no_bracket(self):
        """The end of the chain, through the method's own door."""
        for name, project in _both():
            details = _result(project).details or {}
            assert details.get("lambda_search_fell_back") is True, name


# ======================================================================
class TestTheRootIsThereWhenTheGateComesForward:
    """The root v0.1.159 said did not exist, reached with the same solver.

    ``patience`` is an argument of ``solve_branch``. Passing a smaller one
    brings the rescue forward to where the orbit still is, and the branch
    that returned ``None`` walks to a fixed point. Nothing global is touched,
    so there is nothing to restore and no way for this class to leak into
    another file (rule 5).

    The control that decides whether this measures anything is
    ``test_which_gate_it_is_does_not_matter``: a fixed point is where the
    iteration would stay, so several gates have to land on the SAME number.
    Measured spread over four gates and two starting values: 1.3e-11. And
    ``test_an_earlier_gate_does_not_move_what_already_converged`` is the
    other half — the early gate is not a different answer to the same
    question, it is an answer where there used to be none.
    """

    GATES = (25, 30, 40, 50)

    def _passive(self):
        from ogr_core.support import ForceApplication
        return _anchored(ForceApplication.PASSIVE)

    def test_the_branch_that_had_none_solves_with_an_earlier_gate(self):
        system = _system(self._passive())
        value, paths, _spread = _reach(system, FIRST_LOST)
        assert value is not None and paths > 1, (value, paths)

    def test_and_g_changes_sign_just_above_it(self):
        """Which is what "there is a root" means for this method: the two
        factors are on opposite sides of each other at two lambdas the
        solver can reach."""
        system = _system(self._passive())
        ff = _force(system, 0.0, max_passes=MAX_IT).fos
        below, _p, _s = _reach(system, 1.315)
        above, _p2, _s2 = _reach(system, PAST_ROOT)
        assert below is not None and above is not None, (below, above)
        assert (ff - below) < 0.0 < (ff - above), (ff, below, above)

    def test_the_recovered_root_is_the_wedge(self):
        """And this is why it is a root and not a coincidence. On a plane
        every method that closes force equilibrium owes the closed form, so
        a lambda where ``F_m`` meets ``F_f`` has to meet it AT the wedge.
        Measured 8e-6 away from it, against the 1e-2 the published fallback
        sits at."""
        project = self._passive()
        system = _system(project)
        wedge = _closed_form(project)
        recovered, paths, _spread = _reach(system, PAST_ROOT)
        assert recovered is not None, paths
        near = abs((recovered - wedge) / wedge)
        published = abs((_result(project).fos - wedge) / wedge)
        assert near < 1e-4, near
        assert published > 100 * near, (published, near)

    def test_which_gate_it_is_does_not_matter(self):
        system = _system(self._passive())
        value, paths, spread = _reach(system, PAST_ROOT, gates=self.GATES)
        assert value is not None and paths >= 3, paths
        assert spread < 1e-8, (spread, paths)

    def test_an_earlier_gate_does_not_move_what_already_converged(self):
        """The neutrality half. Where the shipped gate reaches a fixed point,
        the early one reaches the same fixed point — so what the experiment
        adds is coverage, not a different answer."""
        system = _system(self._passive())
        shipped = _fixed_point(system, LAST_SOLVED, 80)
        early = _fixed_point(system, LAST_SOLVED, EARLY_GATE)
        assert shipped is not None and early is not None
        assert abs(shipped - early) < 1e-9, (shipped, early)


# ======================================================================
class TestWhatTheProgramPublishesMeanwhile:
    """The other end of it: what a user of 0.1.176 gets on these two cells.

    A refusal, which is the right shape — ``converged`` false, a reason, the
    residual in the message — and a number 1 % to 3.5 % from the wedge. What
    this class pins is that the distance is not the iteration: the residual
    is orders above the tolerance asked for and does not shrink with it,
    while the recovered root of the class above is 8e-6 from the closed form
    at the same settings.
    """

    def test_the_two_steep_cells_publish_a_refused_fallback(self):
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT
        for name, project in _both():
            r = _result(project)
            details = r.details or {}
            assert details["lambda_residual"] > FALLBACK_RESIDUAL_LIMIT, name
            assert r.converged is False, name
            assert r.error_message, name

    def test_and_the_residual_does_not_follow_the_tolerance(self):
        """The signature that separates "cannot reach the root" from "has not
        reached it yet". Three decades of tolerance, same residual."""
        for name, project in _both():
            seen = []
            for tol in (1e-4, 1e-7, 1e-10):
                details = _result(project, tolerance=tol).details or {}
                seen.append(details["lambda_residual"])
            assert max(seen) - min(seen) < 0.01 * max(seen), (name, seen)
            assert min(seen) > 1e-2, (name, seen)


# ======================================================================
class TestNotEveryFallbackHidesAReachableRoot:
    """The cell that keeps the finding from being over-read.

    The 45 degree plane with the Passive anchor falls back too, and there the
    original reading is the right one: ``g`` keeps ONE sign across every
    lambda either branch can solve, and it shrinks so slowly with lambda that
    nothing in the searched range crosses. A file that only showed the 50
    degree cell would invite the conclusion that a fallback always means a
    lost root, and this class is here to refuse that conclusion.

    It is also why the class above measures a SIGN CHANGE rather than a small
    residual: at 45 degrees Passive the residual is 1.2e-3, forty times
    smaller than the Passive cell at 50 degrees, and it is the one WITHOUT a
    reachable root.
    """

    BETA = 45.0
    LAMBDAS = (-1.4, -0.1, 1.0, 1.75)

    def test_g_keeps_one_sign_over_everything_that_solves(self):
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.PASSIVE), self.BETA)
        signs = []
        for lam in self.LAMBDAS:
            force = _force(system, lam, max_passes=MAX_IT)
            moment = _moment(system, lam, max_passes=MAX_IT)
            assert force is not None and force.converged, lam
            assert moment is not None and moment.converged, lam
            signs.append(force.fos - moment.fos > 0.0)
        assert all(signs) or not any(signs), signs

    def test_and_its_fallback_is_the_small_honest_one(self):
        """Under ``FALLBACK_RESIDUAL_LIMIT``, so it is published as an
        answer — which is a different thing from the refusal at 50 degrees
        and has to stay a different thing."""
        from ogr_core.support import ForceApplication
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT
        details = _result(_anchored(ForceApplication.PASSIVE),
                          self.BETA).details or {}
        assert details.get("lambda_search_fell_back") is True
        assert details["lambda_residual"] < FALLBACK_RESIDUAL_LIMIT


# ======================================================================
class TestTheFixtureStillDiscriminates:
    """CONTROL. Every case above is about a search that finds nothing, so
    the fixture could go green by finding nothing ANYWHERE — a support that
    stopped being applied, a slicer that stopped producing slices, a method
    that refuses everything. These are the cells that must keep working, and
    they are the same cells that make D119's question a question: the anchor
    is the same 120 kN/m and only the steep plane loses its root.
    """

    def test_the_shallower_anchored_planes_still_bracket_a_root(self):
        for name, project in _both():
            for beta in (35.0, 40.0):
                details = _result(project, beta).details or {}
                assert details.get("lambda_search_fell_back") is False, (
                    name, beta)

    def test_the_45_degree_plane_brackets_one_with_the_active_anchor(self):
        from ogr_core.support import ForceApplication
        details = _result(_anchored(ForceApplication.ACTIVE), 45.0).details
        assert (details or {}).get("lambda_search_fell_back") is False

    def test_the_unreinforced_steep_plane_brackets_one_too(self):
        """Same plane, same slicer, no anchor: the root is found and the
        answer is the wedge. Whatever the anchor does, it is not breaking
        the geometry."""
        project = _bare()
        r = _result(project)
        details = r.details or {}
        assert details.get("lambda_search_fell_back") is False
        wedge = _closed_form(project)
        assert abs((r.fos - wedge) / wedge) < 1e-8, (r.fos, wedge)

    def test_the_anchor_is_actually_in_the_system(self):
        """Rule 7 for a fixture: a support that resolved to nothing would
        make every claim above vacuous, and this fixture has had that bug
        before (``test_janbu_wedge_v1142`` documents a horizontal-force
        support whose term was identically zero)."""
        from ogr_slip2d.support_integration import resolve_support_terms
        for name, project in _both():
            sl = _slices(project, BETA_STEEP)
            sup = resolve_support_terms(project, _plane(BETA_STEEP), sl, 1.0)
            assert sup.present, name
            assert (abs(sup.total_active_t()) + abs(sup.total_passive_t())
                    ) > 1.0, name
            assert _closed_form(project) != _closed_form(_bare()), name
