# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A branch that is cycling is rescued when it says so, not when the pass count
says so — and a root between two grid nodes is looked for.

WHAT INVARIANT THIS PROTECTS. Spencer and GLE reach a factor of safety through
a lambda: the inter-slice inclination where the force and the moment branches
agree. Two things had to be true for that lambda to be found and neither was,
which is why this version changes two things and carries two switches. First,
the branch at that lambda has to be SOLVABLE: the damped iteration
``F <- 0.5*(F + f_new)`` of the moment branch turns, with reinforcement, from
a monotone contraction into a period-2 cycle whose amplitude grows, and the
orbit leaves the region where the factor of safety is finite and positive —
``solve_branch`` returns ``None`` on pass 69, while the relaxation rescue of
v0.1.176 enters on the pass after ``STALL_PATIENCE`` = 80 and never sees it.
Second, that lambda has to be LOOKED AT: the calibrated grid steps 0.8, 1.0,
1.5, and the root of this fixture is at 1.31988.

So the rule this file enforces is: **a branch is given to the rescue when its
own iteration shows it needs it, and a search that brackets nothing looks
inside the gap its lost samples left before it hands back a reserve value.**
Bank defect D148.

WHAT THE MEASUREMENT SAID, because it is not what the ficha assumed, and two
of its three premises are refuted:

* the exit is ONE of the five ``return None`` of ``solve_branch`` and it is
  not the one it looks like. ``moment_fos`` comes back NEGATIVE — measured
  -8.554361524365895 at lambda 1.30 — so the branch leaves through
  ``f_new <= 0.0``. Not the m_alpha collapse, not the vanishing driving term;
* THE ITERATE NEVER LEAVES ``[F_MIN, F_MAX]``, so the repair the ficha asked
  for — "a guard that keeps the iterate inside the window instead of
  returning None" — would do nothing at all (rule 7). ``F`` is clamped on
  every update and sits at 2.8613769780957528 on the pass it dies. What
  leaves the admissible region is the OUTPUT OF THE MAP, downwards;
* the growth is not detectable by the obvious test. A period-2 cycle
  alternates a small step and a large one, so ``step > prev_step`` is true on
  alternate passes and NEVER twice in a row: a three-in-a-row growth test —
  the literal negation of the contraction test of D116 — can no more fire
  here than ``step < prev_step < prev_step_2`` could fire on the alternating
  branch D145 measured. What grows is the envelope of the SAME PHASE,
  ``step > prev_step_2``, continuously from pass 19 to the escape on 69.

AND NEITHER CHANGE ALONE MOVES THE ANSWER, which is the reason both are here
and the reason each has its own switch. Measured on the Passive cell, against
the closed form of the wedge (Coulomb 1776; Duncan & Wright 2005 §6):

    cycle entry   gap refinement   published        error
    off           off              1.765482         +0.9818 %
    off           ON               1.750071         +0.1003 %   still a fallback
    ON            off              1.765482         +0.9818 %
    ON            ON               1.748318         +0.0000 %   lambda 1.3199

The branch repair on its own changes NOTHING, because the lambdas it makes
solvable are not grid nodes; the refinement on its own gets to 0.1 % and still
falls back, because the sample it needs at the far side of the gap is the one
the branch solver cannot produce. An A/B that moved both at once would have
attributed the result to either.

WHY 10 IS THE THRESHOLD AND WHERE IT COMES FROM. Two censuses by
``_tools/ciclo_rama_d148.py`` — the sixteen cells of the wedge ladder (960
branches) and the verification bank (344 rows, 79 problems, 6014 branches) —
published in ``docs/audits/branch_cycle_v1181.md``. The number that decides is
how many ACCEPTED branches a threshold would take away from the damped
iteration, and over the bank the answer is 11 ordinary contractions at K = 3,
one at K = 6 and ZERO at K = 10. The eight accepted branches that K = 10 still
moves all have ``rescued=True``: they are branches the gate of v0.1.176 was
already going to take over on pass 81, reached sooner. That is the invariant
``TestTheEarlyEntryTakesOnlyWhatTheGateWouldHave`` asserts on this fixture.

WHAT THIS FILE DOES NOT CLAIM.

* not that every lost branch comes back. Of the 460 the bank loses this way
  the median dies on pass TWO, with no history for any signature to read, and
  335 of them are FORCE branches — a vanishing driving term, not a cycle. They
  keep dying, and what changes for them is that they are COUNTED;
* not that the Active cell is fixed. Its escape arrives before the crossing
  whatever gate is used, so it still falls back and
  ``TestWhatIsStillOutOfReach`` pins that rather than hiding it;
* not one digit of any reference value. Every number below is either an A/B in
  one process, an identity, a pass count, or a comparison against the closed
  form this file computes itself.

WHICH CASES MEASURE THE CHANGE AND WHICH ARE CONTROL, counted by RUNNING the
file against the tree of 0.1.180 with ``git stash`` rather than written from
memory. Of 23 cases, 11 FAIL there and 12 pass, and the eleven are not all
worth the same, so they are split instead of totalled:

* SEVEN fail by MEASURED DIFFERENCE, which is the discrimination that counts:
  the branch at 1.30 comes back ``None`` instead of settling; only two of the
  four starting values reach a fixed point instead of all four; the two
  lambdas that bracket the root are ``(None, None)``; the method publishes no
  counter for the loss; the refinement note is absent; the attribution table
  reads 0.98 % in all four corners instead of one; and the published answer is
  the "no λ-bracket" refusal instead of the wedge;
* FOUR fail because a symbol does not exist yet — the ``rescue_gate``
  argument, the ``n_inadmissible`` attribute and the two ``details`` keys.
  That is WEAK discrimination and it is labelled as such rather than counted
  with the others: it shows the name was added, not that anything behaves
  differently.

Of the twelve that pass on both trees, six are MADE to pass on both because
they describe the DEFECT and not the repair — which exit is taken, that the
iterate is inside its window, that m_alpha never collapsed, that the steps
alternate, that a three-in-a-row test never fires, that the envelope grows —
and a difference in any of those would mean the diagnosis had stopped holding.
The rest are the declared control: the four constants, the branch that
contracts coming back bit for bit, and the two limits this version does not
remove.

``CYCLE_RUN`` is read with ``getattr`` and never imported at the top, on
purpose: an import would turn all 23 cases into collection errors against the
older tree, and "23 errors" does not say which of them measure the change.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

#: The fixture, literally the one in ``test_interslice_budget_v1159.py``,
#: ``test_janbu_wedge_v1142.py`` and ``test_anchored_wedge_root_v1177.py``.
#: Built here rather than imported because a file in ``tests/`` cannot reach
#: the verification bank and a test that needs a directory outside the
#: repository fails on a clean machine.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
TIGHT = 1e-10
MAX_IT = 400

#: The plane whose root the anchor pushes past the last solvable lambda, and
#: the three lambdas that say so: the last one 0.1.180 reached, the first one
#: it lost, and the one just past the crossing.
BETA = 50.0
LAST_SOLVED = 1.275
FIRST_LOST = 1.30
PAST_ROOT = 1.32

#: Where the branch of ``FIRST_LOST`` leaves through ``f_new <= 0``, measured
#: on the engine with the cycle entry switched off. It is the number
#: ``test_anchored_wedge_root_v1177`` pins as well, and it does not move: this
#: version does not make pass 69 wrong, it arrives before it.
DEATH_PASS = 69


# ----------------------------------------------------------------------
@contextlib.contextmanager
def _uncycled():
    """The branch solver of 0.1.180: the early entry of D148 off, in-process.

    Restored with ``try/finally`` and not in a ``teardown_method``, because
    the runner does not call one — a leaked module flag is the failure mode
    that only shows up in the full suite (rule 5).
    """
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "BRANCH_CYCLE_RESCUE", None)
    if keep is None:
        yield
        return
    interslice.BRANCH_CYCLE_RESCUE = False
    try:
        yield
    finally:
        interslice.BRANCH_CYCLE_RESCUE = keep


@contextlib.contextmanager
def _unrefined():
    """The lambda search of 0.1.180: the gap refinement off, in-process."""
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "LAMBDA_GAP_REFINE", None)
    if keep is None:
        yield
        return
    interslice.LAMBDA_GAP_REFINE = False
    try:
        yield
    finally:
        interslice.LAMBDA_GAP_REFINE = keep


# ----------------------------------------------------------------------
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


def _passive():
    from ogr_core.support import ForceApplication
    return _anchored(ForceApplication.PASSIVE)


def _plane(beta_deg=BETA):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _slices(project, beta_deg=BETA):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, _plane(beta_deg), num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    return sl


#: One ``GLESystem`` per (anchor, beta, method), built once. Spencer and GLE
#: cost about 50 ms a surface and this file solves branches in the hundreds;
#: sharing the system between cases is what keeps it from being an expensive
#: file, the same lesson ``test_lambda_closure_v1180`` recorded.
_SYSTEMS: dict = {}


def _system(kind="passive", beta_deg=BETA, method_id="spencer"):
    """The ``GLESystem`` the METHOD builds — with ``sup`` and ``axis``.

    Not the helper of ``test_interslice_budget_v1159.py``, which passes
    ``sup=None``: that puts the reinforcement in the FORCE branch only and
    leaves it out of the moment closure, so it measures a system nobody
    solves. Everything here mirrors ``spencer.py``.
    """
    key = (kind, beta_deg, method_id)
    if key in _SYSTEMS:
        return _SYSTEMS[key]
    from ogr_slip2d.interslice import GLESystem, branch_budget
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.support_integration import resolve_support_terms

    project = {"passive": _passive, "bare": _bare,
               "active": _anchored}[kind]()
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
    system = GLESystem(s_list, shape, 0.0, 0.0, sign, None, None, sup,
                       axis_for(project, surface), tolerance=TIGHT,
                       initial_fos=1.0, max_passes=branch_budget(MAX_IT))
    _SYSTEMS[key] = system
    return system


def _moment(system, lam, **kw):
    from ogr_slip2d.interslice import solve_branch
    kw.setdefault("max_passes", system.max_passes)
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos, system.tolerance,
                        kw.pop("initial_fos", 1.0), **kw)


def _closed_form(project, beta_deg=BETA):
    """The wedge, from geometry and the model's own support terms.

    The external reference of this file (Coulomb 1776; the modern statement,
    with the support resolved on the base, is Duncan & Wright 2005 §6).
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


def _result(project, beta_deg=BETA, method_id="spencer", tolerance=TIGHT):
    from ogr_slip2d.methods.base import method_registry
    return method_registry()[method_id](
        tolerance=tolerance, max_iterations=MAX_IT).compute_fos(
            project, _plane(beta_deg), _slices(project, beta_deg))


def _steps(system, lam, upto, **kw):
    """The step of each pass, from the engine, with ``max_passes`` as a time
    machine — the idiom of ``test_branch_contraction_v1172._iterate_at``.

    ``|f_new - F|`` is not stored anywhere, so it is reconstructed from two
    consecutive iterates. The factor is 2 because the ordinary update keeps
    the damped mean, and the pass that ACCEPTS keeps ``f_new`` instead — none
    of the passes read here accepts, which is asserted rather than assumed.
    """
    out, prev = [], 1.0
    for j in range(1, upto + 1):
        st = _moment(system, lam, max_passes=j, **kw)
        if st is None:
            break
        assert not st.converged, ("pass %d accepted; the factor of 2 below "
                                  "would be wrong there" % j)
        out.append(2.0 * abs(st.fos - prev))
        prev = st.fos
    return out


# ======================================================================
class TestTheExitIsTheFifthOneAndTheIterateIsInsideItsWindow:
    """WHICH ``return None`` this is, and the repair that would do nothing.

    Both halves refute the ficha rather than confirming it, which is why they
    are asserted and not assumed: the branch leaves because the MAP returns a
    negative factor of safety, while the ITERATE is comfortably inside
    ``[F_MIN, F_MAX]`` the whole time.
    """

    def test_the_branch_dies_where_the_ficha_says_and_no_later(self):
        with _uncycled():
            assert _moment(_system(), FIRST_LOST) is None
            assert _moment(_system(), FIRST_LOST,
                           max_passes=DEATH_PASS) is None
            alive = _moment(_system(), FIRST_LOST, max_passes=DEATH_PASS - 1)
        assert alive is not None and not alive.converged, alive

    def test_the_iterate_is_well_inside_the_window_when_it_dies(self):
        """So a guard that clamped the ITERATE would change nothing — rule 7
        applied to a repair before it is written rather than after."""
        from ogr_slip2d.interslice import F_MAX, F_MIN
        with _uncycled():
            last = _moment(_system(), FIRST_LOST, max_passes=DEATH_PASS - 1)
        assert last is not None
        assert F_MIN < last.fos < F_MAX, last.fos
        # Not marginal, either: an order of magnitude from either end.
        assert 10 * F_MIN < last.fos < F_MAX / 10, last.fos

    def test_and_what_leaves_the_region_is_the_map_going_negative(self):
        """The moment closure returns a NEGATIVE factor of safety, which is
        the branch of ``f_new <= 0.0`` and not the m_alpha collapse."""
        from ogr_slip2d.interslice import solve_branch
        system = _system()
        seen = []

        def spy(normals, resisting, _inner=system._moment_fos, _s=seen):
            value = _inner(normals, resisting)
            _s.append(value)
            return value

        with _uncycled():
            solve_branch(system.rows, system.lambda_boundary(FIRST_LOST),
                         spy, system.tolerance, 1.0, max_passes=DEATH_PASS)
        assert seen, "the moment closure was never called"
        assert seen[-1] is not None, "that would be the vanishing-driving exit"
        assert seen[-1] < 0.0, seen[-1]

    def test_m_alpha_never_collapsed(self):
        """The other candidate exit, ruled out from its own definition."""
        with _uncycled():
            last = _moment(_system(), FIRST_LOST, max_passes=DEATH_PASS - 1)
        worst = min(abs(r.cos_a + r.sin_a * r.tan_phi / last.fos)
                    for r in _system().rows)
        assert worst > 1e-6, worst


# ======================================================================
class TestTheCycleIsTwoPhasedSoTheObviousTestCannotFire:
    """Why the signature is ``step > prev_step_2`` and not ``step >
    prev_step``, measured rather than argued.

    This is D145 seen in a mirror. There, a converging branch whose steps
    alternated could never satisfy ``step < prev_step < prev_step_2`` and had
    to wait a hundred passes to be admitted. Here a DIVERGING branch whose
    steps alternate can never satisfy the same chain read upwards, so the
    literal negation of the contraction test would arm nothing, ever.
    """

    WINDOW = 40

    def test_the_steps_alternate_instead_of_growing_monotonically(self):
        with _uncycled():
            steps = _steps(_system(), FIRST_LOST, self.WINDOW)
        assert len(steps) == self.WINDOW, len(steps)
        ups = [steps[i] > steps[i - 1] for i in range(1, len(steps))]
        assert any(ups) and not all(ups), "it neither only grows nor only shrinks"
        # The claim in the title: never twice in a row over the window.
        assert not any(ups[i] and ups[i + 1] for i in range(len(ups) - 1)), ups

    def test_so_a_three_in_a_row_growth_test_would_never_arm(self):
        """The rule that was NOT used, asserted so nobody writes it later."""
        with _uncycled():
            steps = _steps(_system(), FIRST_LOST, self.WINDOW)
        fires = [i for i in range(2, len(steps))
                 if steps[i] > steps[i - 1] > steps[i - 2]]
        assert fires == [], fires

    def test_but_the_envelope_of_the_same_phase_does_grow(self):
        """And this one arms, which is the whole choice of the signature."""
        with _uncycled():
            steps = _steps(_system(), FIRST_LOST, self.WINDOW)
        run = best = 0
        for i in range(2, len(steps)):
            run = run + 1 if steps[i] > steps[i - 2] else 0
            best = max(best, run)
        # Read with ``getattr`` and not imported, on purpose: against a tree
        # without the constant an import turns this case into a collection
        # error, and "it errored" does not say whether the envelope grows.
        import ogr_slip2d.interslice as interslice
        want = getattr(interslice, "CYCLE_RUN", 10)
        assert best >= want, (best, want)


# ======================================================================
class TestTheEarlyEntryTakesOnlyWhatTheGateWouldHave:
    """The neutrality half, and the reason a census had to be run.

    The claim is NOT that the signature never fires on a branch that
    converges — over the bank it fires on eight of them. It is that none of
    those eight converges by ordinary contraction: every one is already
    ``rescued``, i.e. a branch the gate of v0.1.176 was going to take over on
    pass 81 anyway, reached sooner. A branch the damped iteration is settling
    on its own is never taken away from it.
    """

    #: Cells that converge by ordinary contraction on this fixture, one per
    #: anchor state, chosen across beta and lambda rather than around one
    #: value so that the control cannot be an accident of a single cell.
    CLEAN = (("bare", 35.0, 0.70), ("bare", 50.0, 0.00),
             ("passive", 45.0, 0.20), ("active", 40.0, 0.50))

    def test_a_branch_that_contracts_is_bit_for_bit_untouched(self):
        for kind, beta, lam in self.CLEAN:
            system = _system(kind, beta)
            with _uncycled():
                was = _moment(system, lam)
            now = _moment(system, lam)
            assert was is not None and was.converged, (kind, beta, lam)
            assert not was.rescued, (kind, beta, lam, "not an ordinary one")
            assert now is not None and now.converged
            assert now.fos == was.fos, (kind, beta, lam, was.fos, now.fos)
            assert now.passes == was.passes, (kind, beta, lam)
            assert now.rescued is False, (kind, beta, lam)

    def test_and_the_branch_that_died_now_settles(self):
        with _uncycled():
            assert _moment(_system(), FIRST_LOST) is None
        now = _moment(_system(), FIRST_LOST)
        assert now is not None and now.converged, now
        assert now.rescued is True, "it can only have arrived through the rescue"

    def test_what_it_settles_on_does_not_depend_on_where_it_started(self):
        """A fixed point is where the iteration would STAY, so several
        starting values have to reach the same number. Without this the case
        above would only say that the iteration stopped somewhere."""
        seen = []
        for start in (0.6, 1.0, 1.8, 3.0):
            st = _moment(_system(), FIRST_LOST, initial_fos=start)
            if st is not None and st.converged:
                seen.append(st.fos)
        assert len(seen) >= 3, seen
        assert max(seen) - min(seen) < 1e-8, (max(seen) - min(seen), seen)


# ======================================================================
class TestTheRootIsFoundAndBothChangesAreNeeded:
    """End to end, through the method's own door, with the attribution.

    The closure criterion of D148 is that the shipped solver find the root at
    lambda 1.3199. It does — and the table below is why both switches exist,
    because with either one alone it does not.
    """

    def test_the_two_lambdas_that_bracket_the_root_are_solvable_now(self):
        system = _system()
        with _uncycled():
            assert system.branches(FIRST_LOST) == (None, None)
            assert system.branches(PAST_ROOT) == (None, None)
        lo = system.branches(FIRST_LOST)
        hi = system.branches(PAST_ROOT)
        assert None not in lo and None not in hi, (lo, hi)
        g_lo, g_hi = lo[0] - lo[1], hi[0] - hi[1]
        assert g_lo < 0.0 < g_hi, (g_lo, g_hi)

    def test_the_published_answer_is_the_closed_form(self):
        project = _passive()
        wedge = _closed_form(project)
        r = _result(project)
        assert r.converged is True, r.error_message
        assert abs((r.fos - wedge) / wedge) < 1e-6, (r.fos, wedge)
        details = r.details or {}
        assert details.get("lambda_search_fell_back") is not True, details
        assert abs(details["lambda"] - 1.31988) < 1e-3, details["lambda"]

    def test_and_neither_change_alone_does_it(self):
        """The attribution table, executed. Three of the four corners are
        made to fail the same assertion for three different reasons, which
        is what makes the fourth one mean something."""
        project = _passive()
        wedge = _closed_form(project)
        errors = {}
        for cycle in (False, True):
            for refine in (False, True):
                with contextlib.ExitStack() as stack:
                    if not cycle:
                        stack.enter_context(_uncycled())
                    if not refine:
                        stack.enter_context(_unrefined())
                    r = _result(project)
                errors[(cycle, refine)] = abs((r.fos - wedge) / wedge)
        assert errors[(True, True)] < 1e-6, errors
        for corner in ((False, False), (False, True), (True, False)):
            assert errors[corner] > 100 * errors[(True, True)], (corner, errors)
        # The branch repair alone changes nothing at all: the lambdas it
        # makes solvable are not grid nodes.
        assert errors[(True, False)] == errors[(False, False)], errors


# ======================================================================
class TestTheFifthExitIsCounted:
    """The exit that decided the answer and raised no counter.

    ``GLESystem.branches`` opened its loop with ``if state is None or
    state.converged: continue``, so a lambda lost to a branch with no state
    left all three counters reading zero — which is how the diagnosis of
    v0.1.159, v0.1.171 and v0.1.176 came to point somewhere else here.
    """

    def test_a_lost_branch_raises_the_new_counter(self):
        system = _system()
        with _uncycled():
            before = system.n_inadmissible
            system.branches(FIRST_LOST)
            assert system.n_inadmissible == before + 1, system.n_inadmissible

    def test_and_it_is_kept_apart_from_the_three_that_existed(self):
        system = _system()
        with _uncycled():
            counts = (system.n_stalled, system.n_passes_exhausted,
                      system.n_thrust_overflow)
            system.branches(FIRST_LOST)
            after = (system.n_stalled, system.n_passes_exhausted,
                     system.n_thrust_overflow)
        assert after == counts, (counts, after)

    def test_the_method_publishes_it(self):
        with _uncycled(), _unrefined():
            details = _result(_anchored()).details or {}
        assert "lambdas_lost_to_inadmissible" in details, sorted(details)
        assert details["lambdas_lost_to_inadmissible"] > 0, details

    def test_and_it_reaches_the_user_as_a_note(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        with _uncycled(), _unrefined():
            r = _result(_anchored())
        notes = lambda_fallback_notes(r)
        lost = (r.details or {})["lambdas_lost_to_inadmissible"]
        assert any(str(lost) in n and "admissible solution" in n
                   for n in notes), notes

    def test_the_refinement_is_reportable_even_though_it_succeeded(self):
        """The door v0.1.180 had to open for ``REASON_LAMBDA_NOT_CLOSED``,
        opened again: this note fires precisely when the surface did NOT
        fall back, so a gate on ``lambda_search_fell_back`` would silence the
        one search with something new to say."""
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        r = _result(_passive())
        assert (r.details or {}).get("lambda_search_fell_back") is not True
        assert (r.details or {})["lambda_gap_refined"] > 0, r.details
        assert any("bracketed nothing" in n for n in lambda_fallback_notes(r))


# ======================================================================
class TestTheControl:
    """Declared control: what this version is not allowed to have moved."""

    def test_the_four_constants_did_not_move(self):
        import ogr_slip2d.interslice as interslice
        assert interslice.STALL_PATIENCE == 80
        assert interslice.MAX_PASSES == 400
        assert interslice.FALLBACK_RESIDUAL_LIMIT == 0.02
        assert interslice.THRUST_SCALE_LIMIT == 10.0
        assert interslice.F_MIN == 0.05 and interslice.F_MAX == 50.0

    def test_the_gate_argument_defaults_to_the_old_behaviour(self):
        """``rescue_gate=None`` has to mean ``patience``, or the separation
        of the two roles would be a change of behaviour dressed as a
        refactor."""
        system = _system()
        a = _moment(system, LAST_SOLVED)
        b = _moment(system, LAST_SOLVED, rescue_gate=None)
        c = _moment(system, LAST_SOLVED, rescue_gate=80)
        assert a is not None and a.fos == b.fos == c.fos
        assert a.passes == b.passes == c.passes

    def test_a_surface_that_brackets_does_not_refine_anything(self):
        """The refinement may not cost anything where nothing was wrong."""
        r = _result(_bare(), beta_deg=35.0)
        details = r.details or {}
        assert details.get("lambda_search_fell_back") is not True, details
        assert details["lambda_gap_refined"] == 0, details


# ======================================================================
class TestWhatIsStillOutOfReach:
    """Rule 6 made executable: the cells this version does NOT fix.

    The day one of these is repaired this class goes red and says which,
    which is the only way a limitation stays honest across versions.
    """

    def test_the_active_cell_still_falls_back(self):
        """Its escape arrives before the crossing whatever gate is used, so
        no entry to the rescue reaches it. Reported, not hidden."""
        details = _result(_anchored()).details or {}
        assert details.get("lambda_search_fell_back") is True, details

    def test_a_branch_that_dies_too_early_has_no_signature_to_read(self):
        """Most of what the bank loses this way dies on pass two, with no
        history any run length could see. The guard does not reach them and
        this says so with a number."""
        import ogr_slip2d.interslice as interslice
        want = getattr(interslice, "CYCLE_RUN", 10)
        system = _system()
        # lambda 1.75 on this cell dies in single digits; the signature
        # cannot have accumulated CYCLE_RUN passes by then.
        with _uncycled():
            died = None
            for k in range(1, 40):
                if _moment(system, 1.75, max_passes=k) is None:
                    died = k
                    break
        assert died is not None and died <= want, died
        assert _moment(system, 1.75) is None, "still lost, and counted"
