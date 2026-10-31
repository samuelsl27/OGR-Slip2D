# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A focused Grid Search opens its process pool for the circles it will SOLVE.

WHAT INVARIANT THIS PROTECTS.

Until v0.1.385 the floor of 400 circles below which a grid stays in-process
was read off the circles the grid NAMES, (nx+1)(ny+1)(rinc+1). A focus
object filters that population before anything is solved, and can leave a
few dozen circles of thousands: bank 078 case 3b keeps 43 of 13 671, and
each of its four methods still started a pool for them (2.45 s against
1.15 s in series, the count included). v0.1.386 applies the same floor to
the circles that reach ``evaluate_circle`` — where walking the grid is cheap,
because the count walks it and the run it keeps in-process walks it again,
where a pool would have shared that walk out.

1. **The floor reads the solved population.** The same kind of focus object
   on both sides of it: a tangent that leaves 380 of the 539 circles opens
   no pool, one that leaves 434 still does; and the comparison is strict, at
   exactly the floor a pool opens.
2. **The count IS that population.** It runs the three refusals of
   ``_run_centres`` — no radius bracket, ``r <= 0``, a focus rejection — and
   must agree with the circles the run hands the solver in every branch: no
   focus, the four kinds, a centre on a limit point, a minimum radius, two
   windows of slope limits, no slope surface. The radii are the ones
   v0.1.385 sampled, bit for bit: the formula moved into ``_grid_radius`` so
   the count and the run cannot drift apart, and the v0.1.385 expression is
   written out below as the reference.
3. **The count is asked only where walking is cheap,** and otherwise the
   nominal floor decides exactly as before (the owner's decision, after the
   review measured the walk: 316 000 focused circles took 4.5–5.1 s counted
   and run in series against 2.2 s in a pool):
   - a focus of point, line or tangent, enabled and well-formed. No focus,
     a window — which samples 72 points of each circle — or an object that
     is not a ``FocusObject`` keep the nominal floor; a window behind a
     tangent too;
   - at most one window of Slope Limits — one is counted, two are not;
   - at most ``_COUNT_MAX_CENTRES`` centres, ``_COUNT_MAX_FOCUS_TESTS``
     circles x active focus objects and ``_COUNT_MAX_PROFILE_WORK`` centres
     x vertices of the External boundary, each checked at its edge; a
     disabled object is not charged.
4. **The count costs nothing when it cannot matter, and can be cancelled:**
   it is asked only when the nominal count would open a pool, it stops at
   the floor, and every centre is a checkpoint.
5. **A run kept in-process never tries the pool,** so a host that cannot
   open one says nothing for it (SN.PARALLEL_FALLBACK) — the owner's
   decision. A run that does try still says so.
6. **A focused grid answers the same through the pool and in series,** bit
   for bit: the identity V8 rests on, for the kind of grid it moves. And
   the run the count keeps in-process is the run v0.1.385's decision gives
   when its pool falls back, notes and the search's counters included: the
   count leaves no trace.

Only the last test solves surfaces, through one real pool. Everywhere else
``evaluate_circle`` is replaced on the instance by a recorder: the count and
the decision never call it, and the series run they lead to stays cheap.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from contextlib import contextmanager

# 7 x 7 centres and 11 radii: 539 circles, over the nominal floor of 400.
GRID_NX = GRID_NY = 6
RADIUS_INCREMENT = 10
N_CENTRES = (GRID_NX + 1) * (GRID_NY + 1)
N_NOMINAL = N_CENTRES * (RADIUS_INCREMENT + 1)


def _project():
    """The Ej_2 geometry, dry. Built in code — the suite runs from a clone."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 70), Vertex(70, 70),
        Vertex(55, 55), Vertex(40, 55), Vertex(15, 30), Vertex(-50, 30),
        Vertex(-50, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("pool")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name="Material 1", unit_weight=20,
                 strength=MohrCoulomb(cohesion=20, friction_angle=35)),
    ]
    adv = p.settings.advanced
    adv.parallel_search = True
    adv.parallel_cpu_percent = 100
    return p


def _search(focus=(), **kw):
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    args = dict(
        method=get_method("bishop_simplified")(),
        grid_x=(-40.0, 70.0), grid_y=(35.0, 135.0),
        grid_nx=GRID_NX, grid_ny=GRID_NY,
        radius_increment=RADIUS_INCREMENT, min_radius=0.0,
        num_slices=12, min_area=1.0, focus_objects=list(focus),
    )
    args.update(kw)
    return GridSearch(**args)


def _tangent(tolerance, **kw):
    """A weak layer at y = 10, under the whole slope. Its tolerance sets
    how many of the 539 circles survive: 380 at 30, 434 at 40."""
    from ogr_core.geometry.focus import FocusKind, FocusObject
    return FocusObject(kind=FocusKind.TANGENT,
                       points=[(-50.0, 10.0), (100.0, 10.0)],
                       tolerance=float(tolerance), **kw)


def _window(**kw):
    """A 4 x 4 window under the toe: 13 of the 539 circles cross it."""
    from ogr_core.geometry.focus import FocusKind, FocusObject
    return FocusObject(kind=FocusKind.WINDOW,
                       points=[(24.0, 18.0), (28.0, 18.0), (28.0, 22.0),
                               (24.0, 22.0)], **kw)


def _focus(kind):
    from ogr_core.geometry.focus import FocusKind, FocusObject
    return {
        "point": FocusObject(kind=FocusKind.POINT, points=[(15.0, 30.0)],
                             tolerance=3.0),
        "line": FocusObject(kind=FocusKind.LINE,
                            points=[(0.0, 25.0), (60.0, 25.0)]),
        "tangent": _tangent(10.0),
        "window": _window(),
    }[kind]


class _DuckFocus:
    """A focus object that is not a ``FocusObject``: the circle test is all
    ``focus.accepts`` ever asked of one. It refuses every circle, so a count
    would keep its grid in-process."""

    def accepts_circle(self, cx, cy, r):
        return False


def _solved_circles(search, project):
    """The circles ``_run_centres`` hands the solver, as (x, y, r) floats,
    with the solver replaced by a recorder that refuses them all."""
    seen = []

    def record(_project, circle):
        seen.append((circle.centre_x, circle.centre_y, circle.radius))
        return None

    search.evaluate_circle = record
    centres = search._centres(project)
    result = search._run_centres(project, centres, 0, len(centres))
    return seen, result


def _needs_a_pool(project, n=N_NOMINAL):
    import pytest
    from ogr_slip2d.search import _worker_count
    if _worker_count(project, n) < 2:
        pytest.skip("this machine runs the grid in a single process")


@contextmanager
def _constant(name, value):
    """A module constant of ``ogr_slip2d.search``, set and given back."""
    import ogr_slip2d.search as S
    before = getattr(S, name)
    setattr(S, name, value)
    try:
        yield
    finally:
        setattr(S, name, before)


class _PoolSpy:
    """Replaces ``_parallel_grid_run`` with a recorder that declines, so the
    run falls back to the series path without starting a process. Used in a
    ``with`` so it is restored whatever happens."""

    def __enter__(self):
        import ogr_slip2d.search as S
        self._S, self._real, self.calls = S, S._parallel_grid_run, []

        def spy(search, project, centres, workers):
            self.calls.append((len(centres), workers))
            return None

        S._parallel_grid_run = spy
        return self

    def __exit__(self, *exc):
        self._S._parallel_grid_run = self._real
        return False


def _run_with_spy(search, project):
    search.evaluate_circle = lambda _project, _circle: None
    with _PoolSpy() as spy:
        result = search.run(project)
    return spy.calls, result


def _spy_count(search):
    """Records every call of the instance's count, by its ``stop_at``."""
    calls = []
    real = search._circles_reaching_the_solver

    def spy(project, centres, stop_at=None):
        calls.append(stop_at)
        return real(project, centres, stop_at=stop_at)

    search._circles_reaching_the_solver = spy
    return calls


# ======================================================================
class TestTheFloorReadsTheSolvedPopulation:
    """Invariant 1."""

    def test_a_focus_leaving_380_opens_no_pool(self):
        """Fails on v0.1.385, which opened one for the 539 named circles."""
        p = _project()
        _needs_a_pool(p)
        s = _search([_tangent(30)])
        assert s._circles_reaching_the_solver(p, s._centres(p)) == 380
        calls, result = _run_with_spy(s, p)
        assert calls == []
        # the series run did the whole grid: the census is untouched
        assert result.attempts == N_NOMINAL
        assert result.focus_rejected == N_NOMINAL - 380

    def test_the_same_focus_leaving_434_still_opens_one(self):
        p = _project()
        _needs_a_pool(p)
        s = _search([_tangent(40)])
        assert s._circles_reaching_the_solver(p, s._centres(p)) == 434
        calls, _ = _run_with_spy(s, p)
        assert len(calls) == 1
        assert calls[0][0] == N_CENTRES

    def test_at_exactly_the_floor_a_pool_opens(self):
        """The floor moved onto the 380 survivors: 380 opens a pool, one
        more than the survivors does not."""
        p = _project()
        _needs_a_pool(p)
        with _constant("_PARALLEL_MIN_CIRCLES", 380):
            calls, _ = _run_with_spy(_search([_tangent(30)]), p)
        assert len(calls) == 1
        with _constant("_PARALLEL_MIN_CIRCLES", 381):
            calls, _ = _run_with_spy(_search([_tangent(30)]), p)
        assert calls == []


# ======================================================================
class TestTheCountIsTheSolvedPopulation:
    """Invariant 2: the count agrees with the circles the run solves, in
    every branch of ``_run_centres``."""

    def _agree(self, search, project):
        expected = search._circles_reaching_the_solver(
            project, search._centres(project))
        seen, result = _solved_circles(search, project)
        assert expected == len(seen)
        # Every circle is in the run's census once: refused by the focus,
        # or invalid — before the solver, or by the recorder, which refuses
        # all it is handed.
        assert result.attempts == len(search._centres(project)) * (
            search.radius_increment + 1)
        assert result.attempts == result.focus_rejected + result.invalid_count
        return len(seen), result

    def test_without_focus(self):
        n, _ = self._agree(_search(), _project())
        assert n == N_NOMINAL

    def test_with_each_kind_of_focus(self):
        p = _project()
        for kind in ("point", "line", "tangent", "window"):
            n, result = self._agree(_search([_focus(kind)]), p)
            assert 0 < n < N_NOMINAL, kind
            assert result.focus_rejected == N_NOMINAL - n, kind

    def test_with_a_centre_on_a_limit_point(self):
        """(-50, 30) is an end of the slope surface: its bracket is (0, 0),
        and its eleven circles are refused as r <= 0, not by a focus."""
        p = _project()
        s = _search(grid_x=(-50.0, 10.0), grid_y=(30.0, 90.0))
        assert (-50.0, 30.0) in s._centres(p)
        assert s._radius_bracket(-50.0, 30.0, s._slope_surface(p)) == (0.0, 0.0)
        n, result = self._agree(s, p)
        assert n == N_NOMINAL - (RADIUS_INCREMENT + 1)
        assert result.focus_rejected == 0
        assert result.invalid_count - n == RADIUS_INCREMENT + 1

    def test_with_a_minimum_radius(self):
        p = _project()
        n, _ = self._agree(_search([_focus("tangent")], min_radius=20.0), p)
        assert n > 0

    def test_with_two_windows_of_slope_limits(self):
        p = _project()
        s = _search([_focus("point")],
                    slope_limits=((-50.0, 10.0), (60.0, 100.0)))
        assert len(s.slope_limit_sets) == 2
        n, _ = self._agree(s, p)
        assert n > 0

    def test_with_no_slope_surface(self):
        """No external boundary: no centre has a bracket, nothing is
        solved, and the count says so."""
        from ogr_core.project import Project
        p = Project("empty")
        n, result = self._agree(_search(), p)
        assert n == 0
        assert result.invalid_count == N_NOMINAL

    def test_the_radii_are_those_of_v0_1_385(self):
        """The run samples exactly what v0.1.385 sampled. The expression
        below is that version's ``_run_centres``, copied, not called."""
        p = _project()
        s = _search([_focus("line")])
        n_circles = RADIUS_INCREMENT + 1
        slope_pts = s._slope_surface(p)
        expected = []
        for xc, yc in s._centres(p):
            r_min, r_max = s._radius_bracket(xc, yc, slope_pts)
            for k in range(n_circles):
                if n_circles > 1:
                    r = r_min + (r_max - r_min) * k / (n_circles - 1)
                else:
                    r = r_min
                if r <= 0 or s._focus_rejects_circle(xc, yc, r):
                    continue
                expected.append((xc.hex(), yc.hex(), r.hex()))
        seen, _ = _solved_circles(s, p)
        assert [(x.hex(), y.hex(), r.hex()) for x, y, r in seen] == expected

    def test_one_radius_is_the_bracket_floor(self):
        """The ``n_circles == 1`` branch: unreachable from a GridSearch,
        whose radius increment is at least 1, but kept as it was."""
        from ogr_slip2d.search import GridSearch
        assert GridSearch._grid_radius(3.25, 9.5, 0, 1) == 3.25
        assert GridSearch._grid_radius(3.25, 9.5, 0, 2) == 3.25
        assert GridSearch._grid_radius(3.25, 9.5, 1, 2) == 9.5


# ======================================================================
class TestTheCountIsAskedOnlyWhereWalkingIsCheap:
    """Invariant 3. Every case here leaves fewer than 400 circles, so a
    count would keep it in-process: where it is not asked, the pool opens,
    as in v0.1.385."""

    def _decide(self, search, project):
        _needs_a_pool(project)
        counted = _spy_count(search)
        calls, _ = _run_with_spy(search, project)
        return counted, calls

    def test_the_predicate(self):
        from ogr_core.geometry.focus import FocusKind, FocusObject
        from ogr_slip2d.search import _focus_is_cheap as cheap
        bad_window = FocusObject(kind=FocusKind.WINDOW,
                                 points=[(0.0, 0.0), (1.0, 1.0)])
        for kind in ("point", "line", "tangent"):
            assert cheap([_focus(kind)]), kind
        assert cheap([_window(enabled=False), _tangent(30)])
        assert cheap([bad_window, _tangent(30)])
        assert not cheap([_window()])
        assert not cheap([_tangent(30), _window()])
        assert not cheap([_window(enabled=False)])
        assert not cheap([bad_window])
        assert not cheap([_tangent(30, enabled=False)])
        assert not cheap([_DuckFocus()])
        assert not cheap([_tangent(30), _DuckFocus()])
        assert not cheap([])
        assert not cheap(None)

    def test_a_cheap_focus_is_counted(self):
        counted, calls = self._decide(_search([_tangent(30)]), _project())
        assert counted == [400] and calls == []

    def test_no_focus_is_not_counted(self):
        """No slope surface: not a circle has a bracket, and the nominal
        floor still decides."""
        from ogr_core.project import Project
        p = Project("empty")
        p.settings.advanced.parallel_search = True
        p.settings.advanced.parallel_cpu_percent = 100
        s = _search()
        assert s._circles_reaching_the_solver(p, s._centres(p)) == 0
        counted, calls = self._decide(_search(), p)
        assert counted == [] and len(calls) == 1

    def test_a_window_is_never_counted(self):
        """13 circles cross it, and its pool opens as in v0.1.385."""
        p = _project()
        s = _search([_window()])
        assert s._circles_reaching_the_solver(p, s._centres(p)) == 13
        counted, calls = self._decide(_search([_window()]), p)
        assert counted == [] and len(calls) == 1

    def test_nor_a_window_behind_a_tangent(self):
        counted, calls = self._decide(
            _search([_tangent(30), _window()]), _project())
        assert counted == [] and len(calls) == 1

    def test_a_disabled_window_does_not_count(self):
        counted, calls = self._decide(
            _search([_window(enabled=False), _tangent(30)]), _project())
        assert counted == [400] and calls == []

    def test_an_object_that_is_not_a_focus_object(self):
        """It ran in v0.1.385, and it still runs, on the nominal floor."""
        p = _project()
        s = _search([_DuckFocus()])
        assert s._circles_reaching_the_solver(p, s._centres(p)) == 0
        counted, calls = self._decide(_search([_DuckFocus()]), p)
        assert counted == [] and len(calls) == 1

    def test_one_window_of_slope_limits_is_counted(self):
        """The common case in the bank: explicit limits, one window."""
        s = _search([_tangent(30)], slope_limits=(-50.0, 100.0))
        assert len(s.slope_limit_sets) == 1
        counted, calls = self._decide(s, _project())
        assert counted == [400] and calls == []

    def test_two_windows_of_slope_limits_are_not_counted(self):
        s = _search([_tangent(30)],
                    slope_limits=((-50.0, 10.0), (60.0, 100.0)))
        counted, calls = self._decide(s, _project())
        assert counted == [] and len(calls) == 1

    def test_each_size_limit_at_its_edge(self):
        """Each limit set to exactly this grid's measure, then one less:
        the first is counted, the second keeps the nominal floor."""
        p = _project()
        vertices = len(p.external_boundary().polyline.vertices)
        for name, measure in (("_COUNT_MAX_CENTRES", N_CENTRES),
                              ("_COUNT_MAX_FOCUS_TESTS", N_NOMINAL),
                              ("_COUNT_MAX_PROFILE_WORK",
                               N_CENTRES * vertices)):
            with _constant(name, measure):
                counted, calls = self._decide(_search([_tangent(30)]), p)
            assert counted == [400] and calls == [], name
            with _constant(name, measure - 1):
                counted, calls = self._decide(_search([_tangent(30)]), p)
            assert counted == [] and len(calls) == 1, name

    def test_the_focus_tests_count_every_active_object(self):
        """The bound is the most tests the conjunction can make: circles x
        active objects. Two tangents need twice the room of one; a disabled
        object, which accepts at once, is not charged."""
        p = _project()
        both = [_tangent(30), _tangent(30)]
        with _constant("_COUNT_MAX_FOCUS_TESTS", 2 * N_NOMINAL):
            counted, calls = self._decide(_search(both), p)
        assert counted == [400] and calls == []
        with _constant("_COUNT_MAX_FOCUS_TESTS", 2 * N_NOMINAL - 1):
            counted, calls = self._decide(_search(both), p)
        assert counted == [] and len(calls) == 1
        with _constant("_COUNT_MAX_FOCUS_TESTS", N_NOMINAL):
            counted, calls = self._decide(
                _search([_tangent(30), _tangent(30, enabled=False)]), p)
        assert counted == [400] and calls == []


# ======================================================================
class TestTheCountCostsNothingWhenItCannotMatter:
    """Invariant 4."""

    def test_not_asked_when_parallel_search_is_off(self):
        p = _project()
        p.settings.advanced.parallel_search = False
        s = _search([_tangent(30)])
        calls = _spy_count(s)
        _run_with_spy(s, p)
        assert calls == []

    def test_not_asked_below_the_nominal_floor(self):
        p = _project()
        s = _search([_tangent(30)], grid_nx=4, grid_ny=4)   # 275 circles
        calls = _spy_count(s)
        _run_with_spy(s, p)
        assert calls == []

    def test_it_stops_at_the_floor(self):
        """400 circles are reached on the 37th centre (37 x 11 = 407): no
        bracket is measured after it."""
        p = _project()
        s = _search()
        brackets = []
        real = s._radius_bracket

        def counting(xc, yc, slope_pts):
            brackets.append((xc, yc))
            return real(xc, yc, slope_pts)

        s._radius_bracket = counting
        assert s._circles_reaching_the_solver(
            p, s._centres(p), stop_at=400) == 400
        assert len(brackets) == 37
        brackets.clear()
        assert s._circles_reaching_the_solver(p, s._centres(p)) == N_NOMINAL
        assert len(brackets) == N_CENTRES

    def test_every_centre_is_a_checkpoint(self):
        from ogr_core.progress import watching
        p = _project()
        s = _search([_tangent(30)])
        seen = []
        with watching(lambda: seen.append(1)):
            s._circles_reaching_the_solver(p, s._centres(p))
        assert len(seen) == N_CENTRES

    def test_a_stop_at_a_checkpoint_stops_the_count(self):
        """What the window's Cancel does: its check raises, here at the
        third centre, and the count goes no further."""
        import pytest
        from ogr_core.progress import watching

        class Stopped(Exception):
            pass

        p = _project()
        s = _search([_tangent(30)])
        brackets = []
        real = s._radius_bracket
        s._radius_bracket = lambda xc, yc, pts: (
            brackets.append(1) or real(xc, yc, pts))
        ticks = []

        def check():
            ticks.append(1)
            if len(ticks) == 3:
                raise Stopped()

        with watching(check):
            with pytest.raises(Stopped):
                s._circles_reaching_the_solver(p, s._centres(p))
        assert len(brackets) == 2


# ======================================================================
class TestTheFallbackNote:
    """Invariant 5."""

    def _run_broken(self, search):
        import concurrent.futures as cf

        class _Boom:
            def __init__(self, *a, **kw):
                raise OSError("no process pool on this host")

        p = _project()
        _needs_a_pool(p)
        search.evaluate_circle = lambda _project, _circle: None
        real = cf.ProcessPoolExecutor
        cf.ProcessPoolExecutor = _Boom
        try:
            return search.run(p)
        finally:
            cf.ProcessPoolExecutor = real

    def test_a_run_kept_in_process_says_nothing(self):
        """The owner's decision: nothing was going to be shared out."""
        got = self._run_broken(_search([_tangent(30)]))
        assert not any("ran in one" in n for n in got.notes), got.notes

    def test_a_run_that_tries_still_says_so(self):
        got = self._run_broken(_search([_tangent(40)]))
        lines = [n for n in got.notes if "ran in one" in n]
        assert len(lines) == 1, got.notes
        assert "OSError: no process pool on this host" in lines[0]


# ======================================================================
class TestAFocusedGridAnswersTheSameThroughThePool:
    """Invariant 6. The one test here that solves, and opens a real pool.
    The floor is lowered to 30 for it, which the identity does not depend
    on: 82 circles pass the tangent, so the pool opens with a fifth of the
    solving that 434 would cost, and its answer must be the series answer
    to the last bit."""

    def _fingerprint(self, result):
        out = []
        for e in result.evaluations:
            sd = e.surface.to_dict()
            out.append((repr(e.fos), e.converged, e.iterations, e.is_valid,
                        e.admissible, e.error_message,
                        repr(sd.get("centre_x")), repr(sd.get("centre_y")),
                        repr(sd.get("radius")), len(e.slices)))
        return (out, result.valid_count, result.invalid_count,
                result.attempts, result.focus_rejected,
                repr(result.critical.fos) if result.critical else None)

    def test_pool_and_series(self):
        import ogr_slip2d.search as S
        p = _project()
        _needs_a_pool(p)
        pooled = []
        real = S._parallel_grid_run

        def spy(*a, **kw):
            out = real(*a, **kw)
            pooled.append(out is not None)
            return out

        S._parallel_grid_run = spy
        try:
            with _constant("_PARALLEL_MIN_CIRCLES", 30):
                through_pool = _search([_tangent(10)]).run(p)
        finally:
            S._parallel_grid_run = real
        assert pooled == [True], "the pool did not run"
        assert N_NOMINAL - through_pool.focus_rejected == 82
        q = _project()
        q.settings.advanced.parallel_search = False
        in_series = _search([_tangent(10)]).run(q)
        assert self._fingerprint(through_pool) == self._fingerprint(in_series)
        assert through_pool.valid_count > 0

    def test_the_count_leaves_no_trace(self):
        """The run the count keeps in-process, against v0.1.385's decision
        for the same grid with its pool declined by the spy, so both end in
        the same series run and only the count tells them apart: the same
        evaluations, notes, census and counters of the search."""
        import ogr_slip2d.search as S
        p = _project()
        _needs_a_pool(p)

        def run(old):
            s = _search([_tangent(30)])
            real = S.GridSearch.__dict__["_too_few_reach_the_solver"]
            if old:
                S.GridSearch._too_few_reach_the_solver = (
                    lambda self, project, centres: False)
            try:
                with _PoolSpy() as spy:
                    result = s.run(p)
            finally:
                S.GridSearch._too_few_reach_the_solver = real
            counters = {name: getattr(s, name, 0) for name in S._RUN_COUNTERS}
            return spy.calls, result, counters

        new_calls, new, new_counters = run(False)
        old_calls, old, old_counters = run(True)
        assert new_calls == [] and len(old_calls) == 1
        assert self._fingerprint(new) == self._fingerprint(old)
        assert new.notes == old.notes
        assert new_counters == old_counters
        assert ((new.misses_ground, new.outside_slope_limits)
                == (old.misses_ground, old.outside_slope_limits))
        assert new.valid_count > 0
