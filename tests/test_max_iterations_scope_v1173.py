# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A setting named for one loop must say which loops it reaches, and reach them.

WHAT INVARIANT THIS PROTECTS. ``Maximum iterations`` is one number on one
Project Settings page, and it governs five loops that are not the same loop.
In six of the nine methods it is the iteration on the factor of safety —
though Lowe-Karafiath and the two Corps of Engineers quietly raise anything
below 60 to 60, so the shipped default of 50 never reaches them either. In
Ordinary/Fellenius it governs nothing, because that method has no iteration
to run. And in Spencer and GLE/Morgenstern-Price it bounded the OUTER search
for the inter-slice inclination and nothing else, while the fixed point those
two methods actually solve — one ``interslice.solve_branch`` call per branch
per sampled lambda — ran on a module constant no setting could reach. That is
defect D117, and it is rule 7 in its quietest form: not a control that does
nothing, but a control that does something other than what its name says,
which is worse, because the user has no way to notice.

So this file enforces two things at once. **The setting must reach the inner
budget** — wired in v0.1.173 through :func:`interslice.branch_budget` — and
**the interface must describe the engine that exists**, because wiring it did
not make the name true on its own: the budget is FLOORED at ``MAX_PASSES``,
so every value at or below the floor still leaves the inner loop where it was.

WHY THE ANCHOR IS NOT IN THIS FILE. The external reference is the closed form
of a plane wedge and it lives in ``tests/test_janbu_wedge_v1142.py``, where
``TestSpencerAndGleSettleOnTheWedge`` asserts the closure criterion itself.
This file asserts the MECHANISM, and it asserts it as identities rather than
as captured digits: not one assertion below spells out a factor of safety. A
test of the mechanism that also owned the reference value could be made to
pass by moving the reference.

HOW THE RULE 7 GATE WAS BUILT, because a test of a defect that cannot see the
defect is the trap this project has now walked into ten times (D101, D103,
D118, D127, D129). The gate is NOT the case the ficha proposes. It asks for
the slow branch of the 50 degree plane at lambda = 2.0, "85 -> 468 passes" —
and measured on the engine that ships, that branch does not lose its lambda
to the ceiling at all: it STALLS on pass 85, at every budget from 400 to
5000, because ``STALL_PATIENCE`` is what binds it and the 468 is what it
would need with the stall test lifted. Written as the ficha writes it, the
rule 7 test would have measured exactly nothing. The case that does
discriminate was found by sweeping 24 combinations of two wedge angles, both
methods and six tolerances from 1e-5 to 1e-10: exactly ONE moves, and it is
the 55 degree plane under Spencer at 1e-10.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a change delivers is what cost this project two versions in v0.1.82-84:

  * that the wiring is reachable from the dialog. It is not. The tolerance
    spin box floors at 1e-6 and the ceiling does not bite until far below
    that, so the effect is reachable from a stored ``.ogr`` and from the API
    and not by typing into Project Settings. That is reported, not fixed.
  * that the corrected attribution in ``GLESystem.branches`` is covered in
    both directions. Only the LOW one is: a branch stalling above 400 with a
    raised budget would be mis-attributed too, and no such branch exists on
    this fixture — zero in 984 branch solves over five angles, four
    tolerances, 41 lambdas and both branches. The high half is correct by
    construction and untested, and saying so is the point.
  * that ``STALL_PATIENCE`` became reachable. It did not, and D117 does not
    ask for it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import ast
import io
import math
from pathlib import Path

#: The plane wedge fixture, built here rather than imported: the modules in
#: ``tests/`` cannot import one another outside the runner.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50

#: The angle, method and tolerance where the inner budget actually decides
#: an answer. One of 24 combinations swept; see the module docstring for why
#: it is not the case the ficha names.
GATE_BETA = 55.0
GATE_TOL = 1e-10

#: Tolerances on the same plane at which the ceiling is NEVER reached, so
#: the factor they agree on is the limit this circle converges to. Used as a
#: yardstick computed on the spot, never as a remembered number.
SETTLED_TOLS = (1e-8, 1e-9)

#: The plane and lambda whose branches are slow enough to spend a small
#: budget without stalling first. From ``test_interslice_budget_v1159``.
ROOT_BETA = 50.0
ROOT_LAMBDA = 1.2269

_REPO = Path(__file__).resolve().parent.parent

#: The nine methods, split by what the setting means to each. The partition
#: is asserted against the registry, so adding a method without deciding
#: which group it belongs to turns this file red.
FIXED_POINT_ON_F = ("bishop_simplified", "janbu_simplified",
                    "janbu_corrected", "corps_engineers_1",
                    "corps_engineers_2", "lowe_karafiath")
LAMBDA_SEARCH = ("spencer", "gle_morgenstern_price")
NO_ITERATION = ("ordinary_fellenius",)

#: The three of FIXED_POINT_ON_F that raise a small value to a floor of
#: their own, which is why the shipped default does not reach them.
HAVE_THEIR_OWN_FLOOR = ("corps_engineers_1", "corps_engineers_2",
                        "lowe_karafiath")

#: A fragment of the note, chosen so it cannot match any other warning.
NOTE_MARK = "Maximum iterations is set to"


def _daylight_x(beta_deg):
    return TOE + H / math.tan(math.radians(beta_deg))


@contextlib.contextmanager
def _without_lambda_recovery():
    """Every mechanism that recovers a lambda, switched off in-process.

    RENAMED IN v0.1.181 (D148), and the rename is the point. It was
    ``_unrescued`` and it turned off exactly one thing, the relaxation
    rescue of v0.1.176; this version adds two more ways a lambda comes
    back — the entry by cycle signature and the refinement of the gap a
    lost node leaves — and a helper still called "unrescued" that also
    disabled those would be a name saying less than its body does. That is
    the ``off(tighten=True)`` mistake v0.1.179 paid for out loud.

    What the cases here need is not "no rescue" but "nothing recovering a
    lambda behind my back", because every one of them counts lambdas lost
    to the pass budget, and a mechanism that keeps a lambda alive — or that
    samples new ones, as the gap refinement does — moves that count.
    Measured on the 55 degree plane at 500 iterations: with the refinement
    left on, ``lambdas_lost_to_budget`` reads 3 where this class requires 0,
    and the 3 are branches of lambdas the refinement itself introduced.

    The restoring is written out with ``try/finally`` because the runner
    does not call ``teardown_method`` (rule 5), and a tree without a switch
    has nothing to turn off, so the cases mean the same thing there.
    """
    import ogr_slip2d.interslice as interslice
    nombres = ("BRANCH_RESCUE", "BRANCH_CYCLE_RESCUE", "LAMBDA_GAP_REFINE")
    keep = {n: getattr(interslice, n, None) for n in nombres}
    if keep["BRANCH_RESCUE"] is None:
        yield
        return
    for n, v in keep.items():
        if v is not None:
            setattr(interslice, n, False)
    try:
        yield
    finally:
        for n, v in keep.items():
            if v is not None:
                setattr(interslice, n, v)


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


def _plane(beta_deg):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _solve(method_id, beta_deg, tolerance, max_iterations):
    """``(fos, lambdas lost to the pass budget)`` down the real path.

    The whole point is that nothing here is patched: this is the same call
    the application makes, so what it measures is the wire and not a mock.
    """
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface

    project = _bare()
    surface = _plane(beta_deg)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    result = method_registry()[method_id](
        tolerance=tolerance,
        max_iterations=max_iterations).compute_fos(project, surface, sl)
    details = result.details or {}
    return result.fos, details.get("lambdas_lost_to_budget", 0)


def _system(beta_deg, tolerance, max_passes):
    """A GLE system whose branch budget is set directly.

    Not the settings path: this is the engine's own field, and the floor
    that protects the user lives between the setting and here.
    """
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.slicer import slice_surface

    project = _bare()
    surface = _plane(beta_deg)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    n = len(sl.slices)
    return GLESystem(sl.slices, [1.0] * (n + 1), 0.0, 0.0, 1.0,
                     None, None, None, axis_for(project, surface),
                     tolerance=tolerance, max_passes=max_passes)


def _shipped_default():
    """The default of the FIELD, never a 50 written here."""
    from dataclasses import fields as dataclass_fields

    from ogr_core.project.settings import MethodsSettings
    return next(f.default for f in dataclass_fields(MethodsSettings)
                if f.name == "max_iterations")


def _notes(max_iterations, method_ids):
    from ogr_slip2d.analysis_runner import settings_warnings

    project = _bare()
    project.settings.methods.max_iterations = max_iterations
    return [n for n in settings_warnings(project, method_ids)
            if NOTE_MARK in n]


def _tree(rel):
    return ast.parse(io.open(_REPO / rel, encoding="utf-8").read())


def _mentions_max_iterations(tree):
    """Every ``self.max_iterations`` in a module, as AST nodes."""
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "max_iterations"
            and isinstance(n.value, ast.Name) and n.value.id == "self"]


# ======================================================================
class TestTheSettingReachesTheInnerLoop:
    """Rule 7 for the wire this version adds: it has to move the number.

    The measurement behind the case is in the module docstring. What is
    asserted here is never a factor of safety, because a captured digit can
    be made to pass by moving the digit.
    """

    def test_raising_it_recovers_a_lambda_the_budget_was_eating(self):
        """v0.1.176 (D125) — measured with the relaxation rescue OFF. With
        it on, the lambda this cell used to lose to the ceiling is
        extrapolated to its fixed point inside the shipped budget, so the
        budget no longer bites here at any setting; the wire is unchanged
        and this is what it still buys when nothing follows the damping.
        The fourth case of this class pins the rescued half."""
        with _without_lambda_recovery():
            _fos_low, lost_low = _solve("spencer", GATE_BETA, GATE_TOL,
                                        _shipped_default())
            _fos_high, lost_high = _solve("spencer", GATE_BETA, GATE_TOL, 500)
        assert lost_low > 0, (
            "the gate does not fire: with the shipped budget this circle no "
            "longer loses a lambda to the ceiling, so the test below is "
            "measuring nothing")
        assert lost_high == 0, lost_high

    def test_and_that_moves_the_answer(self):
        with _without_lambda_recovery():
            fos_low, _ = _solve("spencer", GATE_BETA, GATE_TOL,
                                _shipped_default())
            fos_high, _ = _solve("spencer", GATE_BETA, GATE_TOL, 500)
        assert fos_low is not None and fos_high is not None
        assert abs(fos_high - fos_low) > 1e-3, (fos_low, fos_high)

    def test_the_recovered_answer_is_the_one_the_solver_settles_on(self):
        """The identity, and the reason this is not a snapshot.

        At the two tolerances in ``SETTLED_TOLS`` the ceiling is never
        reached, so what the solver returns there IS the limit of this
        circle, computed in the same breath rather than remembered. Losing
        the lambda pushed the answer AWAY from that limit as the tolerance
        was tightened, which is the signature of D63; giving the branch the
        room it asked for puts it back. Both halves are asserted, because
        only the pair says which direction the defect ran in.
        """
        # v0.1.181 (D148) — the yardstick is computed on the SAME engine as
        # the two values it judges. It was not: ``settled`` ran with every
        # recovery mechanism on and ``near``/``far`` with them off, which was
        # harmless only while none of them moved this cell. Two of them do
        # now — on this plane the settled factor goes 2.593302 to 2.584021
        # with the gap refinement alone and to 2.572160 with both, TOWARDS
        # the closed form of the wedge (+5.36 % to +4.50 %) — so the
        # mismatch stopped being harmless and became a comparison between
        # two different solvers.
        settled = []
        with _without_lambda_recovery():
            for tol in SETTLED_TOLS:
                fos, lost = _solve("spencer", GATE_BETA, tol,
                                   _shipped_default())
                assert lost == 0, (tol, lost)
                settled.append(fos)
        limit = 0.5 * (settled[0] + settled[1])
        spread = abs(settled[0] - settled[1])
        assert spread > 0.0, settled

        with _without_lambda_recovery():
            near, _ = _solve("spencer", GATE_BETA, GATE_TOL, 500)
            far, _ = _solve("spencer", GATE_BETA, GATE_TOL,
                            _shipped_default())
        assert abs(near - limit) < 10.0 * spread, (near, limit, spread)
        assert abs(far - limit) > 100.0 * spread, (far, limit, spread)

    def test_and_since_the_rescue_the_shipped_budget_loses_nothing_here(self):
        """v0.1.176 (D125) — the half the three cases above no longer see:
        with the relaxation rescue on, the shipped budget keeps the lambda
        and the answer is the settled one, so the D117 wire is a reserve
        for a branch the rescue cannot settle rather than the difference on
        this cell. Asserted as the same identity the case above uses."""
        settled = [_solve("spencer", GATE_BETA, tol, _shipped_default())[0]
                   for tol in SETTLED_TOLS]
        limit = 0.5 * (settled[0] + settled[1])
        spread = abs(settled[0] - settled[1])
        fos, lost = _solve("spencer", GATE_BETA, GATE_TOL, _shipped_default())
        assert lost == 0, lost
        assert abs(fos - limit) < 10.0 * spread, (fos, limit, spread)

    def test_the_wire_is_the_only_thing_that_changed_it(self):
        """Same circle, same tolerance, same method: one setting moved."""
        from ogr_slip2d.interslice import MAX_PASSES, branch_budget
        assert branch_budget(_shipped_default()) == MAX_PASSES
        assert branch_budget(500) == 500


# ======================================================================
class TestTheFloorCannotTakeAnythingAway:
    """Lowering the setting is not the mirror of raising it.

    Since v0.1.172 no branch converges before its third pass and
    ``STALL_PATIENCE`` is 80, so a budget the user could push below those
    would not trim a wasteful iteration — it would delete lambdas that are
    answers today. ``TestPatienceCannotChangeWhatAlreadyConverged`` in
    ``test_interslice_budget_v1159`` is the promise this protects.
    """

    def test_the_floor_is_the_budget_the_solver_already_had(self):
        from ogr_slip2d.interslice import MAX_PASSES, branch_budget
        for low in (1, 2, 10, 50, MAX_PASSES):
            assert branch_budget(low) == MAX_PASSES, low
        for high in (MAX_PASSES + 1, 500, 5000):
            assert branch_budget(high) == high, high

    def test_every_stored_project_buys_exactly_what_it_bought_before(self):
        """Why zero moved digits is an IDENTITY and not a measurement.

        The shipped default is at or under the floor, so the wired
        expression hands the branch solver the same integer the unwired
        default handed it. Every project written by this program carries
        that default unless someone changed it, which is why the
        verification bank cannot move.
        """
        from ogr_slip2d.interslice import MAX_PASSES, branch_budget
        assert branch_budget(_shipped_default()) == MAX_PASSES

    def test_a_tiny_setting_does_not_cost_a_lambda(self):
        base = _solve("spencer", GATE_BETA, GATE_TOL, _shipped_default())
        for low in (1, 2, 10):
            assert _solve("spencer", GATE_BETA, GATE_TOL, low) == base, low

    def test_nor_on_the_plane_whose_branches_are_slow(self):
        """On THIS plane the factor does move, and the reason is the whole
        point of the ficha, so it is measured apart instead of asserted
        away. What the floor promises is that the INNER budget takes
        nothing: no lambda is lost to it at any setting. The outer lambda
        secant is a different loop and starving it is that loop's business
        — see the test below.
        """
        losses = {low: _solve("spencer", ROOT_BETA, GATE_TOL, low)[1]
                  for low in (1, 2, 10, _shipped_default())}
        assert set(losses.values()) == {0}, losses

    def test_what_lowering_it_moves_is_the_outer_search(self):
        """The line the tooltip draws, drawn here as a measurement.

        The first version of this class asserted the factor was identical
        at every small setting and it was WRONG — which is worth keeping,
        because being wrong in exactly that way is the defect this file is
        about. ``max_iterations`` has always bounded the secant on the
        inter-slice inclination, and starving that secant moves the answer
        and stops the result converging. It is the INNER fixed point the
        floor protects, and conflating the two is the confusion D117 names.
        """
        starved = _solve("spencer", ROOT_BETA, GATE_TOL, 1)
        fed = _solve("spencer", ROOT_BETA, GATE_TOL, _shipped_default())
        assert starved[1] == fed[1] == 0, (starved, fed)
        assert abs(starved[0] - fed[0]) > 1e-6, (starved[0], fed[0])

    def test_and_the_branch_solver_never_saw_the_difference(self):
        """The other half of the same statement, at the branch itself: the
        two settings hand ``solve_branch`` the same budget, so the state it
        returns is identical bit for bit."""
        from ogr_slip2d.interslice import branch_budget, solve_branch
        assert branch_budget(1) == branch_budget(_shipped_default())
        system = _system(ROOT_BETA, GATE_TOL, branch_budget(1))
        other = _system(ROOT_BETA, GATE_TOL,
                        branch_budget(_shipped_default()))
        a = solve_branch(system.rows, system.lambda_boundary(ROOT_LAMBDA),
                         system._moment_fos, GATE_TOL, 1.0,
                         max_passes=system.max_passes)
        b = solve_branch(other.rows, other.lambda_boundary(ROOT_LAMBDA),
                         other._moment_fos, GATE_TOL, 1.0,
                         max_passes=other.max_passes)
        assert (a.fos, a.passes, a.converged) == (b.fos, b.passes,
                                                  b.converged)

    def test_and_gle_answers_the_same_way(self):
        base = _solve("gle_morgenstern_price", GATE_BETA, GATE_TOL,
                      _shipped_default())
        for low in (1, 2, 10):
            assert _solve("gle_morgenstern_price", GATE_BETA, GATE_TOL,
                          low) == base, low


# ======================================================================
class TestSpendingABudgetIsCountedAsSpendingIt:
    """``n_passes_exhausted`` has to count against the budget USED.

    v0.1.159 created that counter precisely to separate "the solver's own
    limit decided this" from "the branch wandered", and it compared the pass
    count to the module constant. That was right while the constant WAS the
    budget. The moment the budget became configurable the comparison started
    answering about a number the branch never had.

    Only the low direction is reachable, and the module docstring says so.
    """

    def _states(self, budget):
        system = _system(ROOT_BETA, GATE_TOL, budget)
        force, moment = system.states(ROOT_LAMBDA)
        return system, [s for s in (force, moment) if s is not None]

    def test_a_branch_cut_by_a_small_budget_used_every_pass_it_had(self):
        _system_, states = self._states(50)
        spent = [s for s in states
                 if not s.converged and not s.abandoned and s.passes == 50]
        assert spent, [(s.converged, s.passes) for s in states]

    def test_and_the_counter_says_so(self):
        """An identity: the counter equals the branches that spent it all,
        recomputed here rather than written down as a 2."""
        system, states = self._states(50)
        expected = sum(1 for s in states
                       if not s.converged and not s.abandoned
                       and s.passes >= 50)
        system.branches(ROOT_LAMBDA)
        assert system.n_passes_exhausted == expected, (
            system.n_passes_exhausted, expected)
        assert expected > 0, "the case stopped exhausting anything"

    def test_the_old_comparison_would_have_counted_none_of_them(self):
        """The before half, run rather than remembered.

        Against the module constant the same branches score zero, which is
        what made this worth changing and what makes the assertion above
        discriminate instead of passing in the vacuum.
        """
        from ogr_slip2d.interslice import MAX_PASSES
        _system_, states = self._states(50)
        against_constant = sum(1 for s in states
                               if not s.converged and not s.abandoned
                               and s.passes >= MAX_PASSES)
        assert against_constant == 0, against_constant

    def test_a_budget_that_is_enough_counts_nothing(self):
        """The control: the counter must not fire on a branch that solved."""
        system = _system(ROOT_BETA, GATE_TOL, 400)
        pair = system.branches(ROOT_LAMBDA)
        assert pair[0] is not None and pair[1] is not None, pair
        assert system.n_passes_exhausted == 0, system.n_passes_exhausted


# ======================================================================
class TestTheLabelDescribesTheEngineThatExists:
    """The census the tooltip publishes, tied to the code that makes it true.

    Every sentence the control shows is a claim about a loop somewhere in
    ``ogr_slip2d/methods``. Asserting them here is what turns the tooltip
    from prose into something that goes red when it stops being true — which
    is the only difference between documentation and a guarantee.
    """

    def test_the_three_groups_are_exactly_the_registry(self):
        from ogr_slip2d.methods.base import _METHOD_REGISTRY
        declared = set(FIXED_POINT_ON_F) | set(LAMBDA_SEARCH) | set(
            NO_ITERATION)
        assert declared == set(_METHOD_REGISTRY), (
            declared ^ set(_METHOD_REGISTRY))
        assert len(declared) == (len(FIXED_POINT_ON_F) + len(LAMBDA_SEARCH)
                                 + len(NO_ITERATION)), "a method is in two"

    def test_ordinary_has_no_iteration_to_bound(self):
        assert _mentions_max_iterations(
            _tree("ogr_slip2d/methods/ordinary.py")) == []

    def test_bishop_and_janbu_take_the_value_as_written(self):
        """Inside a ``range``, with nothing between it and the loop."""
        for rel in ("ogr_slip2d/methods/bishop.py",
                    "ogr_slip2d/methods/janbu.py"):
            ranges = [n for n in ast.walk(_tree(rel))
                      if isinstance(n, ast.Call)
                      and getattr(n.func, "id", None) == "range"
                      and any(_mentions_max_iterations(ast.Module([a], []))
                              for a in n.args)]
            assert ranges, rel

    def test_three_methods_raise_a_small_value_to_a_floor_of_sixty(self):
        """The half of the census the ficha missed, and the reason the
        tooltip names 60: the shipped default of 50 does not reach these
        three either."""
        calls = [n for n in ast.walk(
            _tree("ogr_slip2d/methods/modified_swedish.py"))
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "max"
            and len(n.args) == 2
            and _mentions_max_iterations(ast.Module([n.args[0]], []))
            and isinstance(n.args[1], ast.Constant)]
        assert len(calls) == 1, len(calls)
        assert calls[0].args[1].value == 60, calls[0].args[1].value
        assert _shipped_default() < 60, (
            "the default now reaches these three, so the tooltip sentence "
            "about a floor of 60 has stopped being true for it")

    def test_spencer_and_gle_hand_it_to_the_branch_budget(self):
        for rel in ("ogr_slip2d/methods/spencer.py",
                    "ogr_slip2d/methods/gle.py"):
            wired = [n for n in ast.walk(_tree(rel))
                     if isinstance(n, ast.Call)
                     and getattr(n.func, "id", None) == "branch_budget"
                     and _mentions_max_iterations(
                         ast.Module(list(n.args), []))]
            assert len(wired) == 1, (rel, len(wired))

    def test_and_the_system_carries_it_down_to_every_branch(self):
        tree = _tree("ogr_slip2d/interslice.py")
        top = {n.name: n for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        assert "branch_budget" in top, "the floor has no single owner"
        gle = top.get("GLESystem")
        methods = {m.name: m for m in (gle.body if gle else [])
                   if isinstance(m, ast.FunctionDef)}
        states = ast.unparse(methods["states"])
        assert states.count("max_passes=self.max_passes") == 2, states
        assert "self.max_passes" in ast.unparse(methods["branches"])

    def test_the_setting_still_bounds_the_lambda_search_as_well(self):
        """It gained a loop; it did not swap one for another."""
        for rel in ("ogr_slip2d/methods/spencer.py",
                    "ogr_slip2d/methods/gle.py"):
            ranges = [n for n in ast.walk(_tree(rel))
                      if isinstance(n, ast.Call)
                      and getattr(n.func, "id", None) == "range"
                      and any(_mentions_max_iterations(ast.Module([a], []))
                              for a in n.args)]
            assert len(ranges) == 1, (rel, len(ranges))

    def test_the_search_budget_no_longer_shares_the_name(self):
        """Step 3 of the ficha: a grep for one must not land on the other."""
        src = io.open(_REPO / "ogr_slip2d/search.py", encoding="utf-8").read()
        assert "max_passes" not in src
        assert "LMC_MAX_PASSES" in src


# ======================================================================
class TestTheRunSaysWhichLoopItBounded:
    """The note, and the two things it must not do.

    It must not speak on a run where the user left the value alone — a note
    on every sound run is a note nobody reads — and it must not invent a
    method. ``analysis_notes_panel._split`` files a note under the first
    token before a colon when that token has no spaces, so a sentence
    opening "Spencer/GLE: ..." lands under a method group that does not
    exist. That is D129, closed three versions ago, and it is the wording
    the ficha proposes.
    """

    def test_it_says_the_inner_loop_was_not_reached(self):
        notes = _notes(200, ["spencer"])
        assert len(notes) == 1, notes
        assert "400" in notes[0], notes[0]

    def test_and_says_the_other_thing_when_it_was(self):
        notes = _notes(500, ["gle_morgenstern_price"])
        assert len(notes) == 1, notes
        assert "500" in notes[0], notes[0]
        assert notes[0] != _notes(200, ["spencer"])[0]

    def test_it_is_silent_at_the_shipped_default(self):
        assert _notes(_shipped_default(), ["spencer"]) == []
        assert _notes(_shipped_default(),
                      ["gle_morgenstern_price", "bishop_simplified"]) == []

    def test_it_is_silent_for_methods_it_is_not_about(self):
        assert _notes(500, ["bishop_simplified"]) == []
        assert _notes(500, ["ordinary_fellenius", "janbu_corrected"]) == []
        assert _notes(500, []) == []

    def test_it_does_not_invent_a_method_in_the_notes_panel(self):
        """Run through the panel's REAL splitter, not a copy of its rule."""
        from ogr_gui.dialogs.analysis_notes_panel import _split
        for value in (2, 200, 500):
            for note in _notes(value, ["spencer"]):
                group, _sentence = _split(note)
                assert group == "Model", (group, note)

    def test_it_reuses_the_engine_numbers_rather_than_repeating_them(self):
        """The floor in the sentence is the floor in the code."""
        from ogr_slip2d.interslice import MAX_PASSES
        note = _notes(200, ["spencer"])[0]
        assert str(MAX_PASSES) in note, note


# ======================================================================
class TestTheControlItself:
    """Declared CONTROL: green before this version and green after it.

    These guard against a mistake THIS design could make rather than against
    the defect it removes. The cheap way to make a configurable budget look
    useful is to loosen the two locks it sits beside, and a test file that
    did not say which of its cases are controls would be read as claiming
    they measure the fix.
    """

    def test_the_stall_patience_did_not_move(self):
        from ogr_slip2d.interslice import STALL_PATIENCE
        assert STALL_PATIENCE == 80, STALL_PATIENCE

    def test_the_floor_did_not_move(self):
        from ogr_slip2d.interslice import MAX_PASSES
        assert MAX_PASSES == 400, MAX_PASSES

    def test_the_thrust_bound_did_not_move(self):
        from ogr_slip2d.interslice import THRUST_SCALE_LIMIT
        assert THRUST_SCALE_LIMIT == 10.0, THRUST_SCALE_LIMIT

    def test_the_default_the_whole_argument_rests_on_did_not_move(self):
        assert _shipped_default() == 50, _shipped_default()


# ======================================================================
class TestTheControlOnScreen:
    """Every test here restores English on exit: leaving the language set to
    Spanish leaked into other suites, where translated menu titles no longer
    matched the names being looked up."""

    def teardown_method(self, _m=None):
        from ogr_gui.i18n import set_language
        set_language("en")

    def _page(self):
        from PySide6.QtWidgets import QApplication

        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        QApplication.instance() or QApplication([])
        dialog = ProjectSettingsDialog(ProjectSettings())
        _WINDOWS.append(dialog)
        return dialog.pages[1]

    def test_the_control_carries_the_census(self):
        from ogr_slip2d.interslice import MAX_PASSES
        tip = self._page().spn_iter.toolTip()
        assert tip, "the control still explains nothing"
        assert str(MAX_PASSES) in tip, tip
        for fragment in ("Bishop", "Lowe-Karafiath", "Ordinary", "Spencer",
                         "60"):
            assert fragment in tip, (fragment, tip)

    def test_the_seepage_control_did_not_inherit_the_sentence(self):
        """The old key is shared with the groundwater page and with
        ``transient_stages_dialog``, which iterate a seepage solver and have
        nothing to do with Spencer. Renaming the key instead of adding one
        would have relabelled both."""
        from PySide6.QtWidgets import QApplication

        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        QApplication.instance() or QApplication([])
        dialog = ProjectSettingsDialog(ProjectSettings())
        _WINDOWS.append(dialog)
        transient = dialog.pages[3]
        assert not transient.sp_iter.toolTip()

    def test_both_new_strings_are_translated(self):
        """A key without a Spanish entry falls back to English in silence,
        which is the ``"Add Grid"`` / ``"Add Grid..."`` defect of v0.1.166."""
        from ogr_gui.i18n import set_language, tr
        page = self._page()
        # v0.1.174 — identified by THIS control's own words. The filter used
        # to be "scope differs" alone, which was under-specified the day it
        # was written and stopped being true the day a second control on the
        # same page adopted the same phrasing for the same reason (D115).
        # Nothing about what this case asserts has changed.
        keys = [k for k in _dialog_tr_keys()
                if "Maximum iterations (scope differs" in k
                or "bounds a different loop" in k]
        assert len(keys) == 2, keys
        set_language("es")
        for key in keys:
            assert tr(key) != key, key
        assert page is not None


def _dialog_tr_keys():
    """Every literal the Methods page hands to ``tr``."""
    tree = _tree("ogr_gui/dialogs/project_settings_dialog.py")
    return [n.args[0].value for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "tr"
            and n.args and isinstance(n.args[0], ast.Constant)
            and isinstance(n.args[0].value, str)]


_WINDOWS: list = []
