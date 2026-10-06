# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.261, defects D262, D263 and D255 — Slope Limits that filter nothing or
everything, and a parallel grid that threw its notes away, all in silence.

All three were found measuring verification problem 109 of the reference
bank (a stepped gabion wall whose statement declares a second set of Slope
Limits at the toe of the wall and the top of the slope).

Invariants protected:

1. **A Grid Search with two OVERLAPPING Slope Limit windows is refused,
   with its reason** (D262). With two sets the grid generates the radii of
   the circles that run from one window to the other, a rule read off the
   reference on SEPARATE windows only (D77). It gives each crossing of the
   ground the first window that contains it, the windows sorted by their
   left limit, so on a shared stretch every crossing goes to the window
   that starts further left, and with a window inside one that starts
   further left nothing ever belongs to the inner one: the 109 as the
   bank declares it, 0..30 + 14.473..18, had no valid radius at any of 121
   centres and said nothing. The reference's behaviour there is not
   measured anywhere, so the configuration is refused instead of invented.
   Every other search reads the two sets as ranges an end may daylight in,
   which overlap does not break; there, a set lying inside the other gets
   a note, because as a filter it does nothing (rule 7).
2. **A surface refused because an end daylights outside the Slope Limits
   is counted by name, and so is a circle that does not cut the ground
   twice** (D263). Neither left any trace: on the 109 with the limits read
   as starting and ending ranges, a Block Search refused all 5000 of its
   surfaces and left neither an evaluation nor a note. The counts reach
   the census of rejected surfaces under -101, each with its reason (the
   second IS the reference's -101 in its own words), the single-surface
   door names the cause, and a run that ends with no valid surface at all
   says what it counted and that the rest has no recorded reason. Only in
   that case: a filter refusing surfaces is routine, and a note on every
   run is noise.
3. **A parallel grid reports what a sequential one reports** (D255). The
   refusal counters and the pending notes live on the search, not on its
   result, and the workers' copies never sent them back: on the 109, a
   10 x 10 grid gave 99 notes in series and none in parallel, which is the
   default above 400 circles. They come back now, in batch order, and the
   progress bar moves as the batches finish instead of jumping to the end.

ANCHORS. The refusal's premise is the D77 rule itself (degenerate at every
centre with the second window inside the first). The Block Search count is
a closed form: from a point object at (25, 6) under a 45-degree face, the
left rays of 135..160 degrees daylight between x = 14.01 and 20.5, so a
window that excludes that interval refuses every candidate and one that
contains it refuses none. The wall of verification problem 87 (D77's own
model) supplies centres where no radius is valid. The parallel runs are
checked by identity against the sequential one.

COST. A few small searches; the two parallel ones run 539 and 539 circles
at 12 slices. Some 15-25 s, most of it starting the worker processes.
"""
from __future__ import annotations

import math

_SLICES = 20


def _slope():
    """A 20 m slope: toe flat at y = 10 out to x = 20, a 45-degree face to
    (40, 30), crest at y = 30 out to x = 60 (the slope of
    ``test_ground_refusals_v1259``)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    pts = [(0.0, 0.0), (60.0, 0.0), (60.0, 30.0), (40.0, 30.0), (20.0, 10.0),
           (0.0, 10.0)]
    p = Project("D263")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=20.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    p.settings.methods.num_slices = _SLICES
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.advanced.parallel_search = False
    return p


def _limits(p, first, second=None):
    s = p.settings.search
    s.slope_limit_left, s.slope_limit_right = first
    if second is not None:
        s.slope_limit_left_2, s.slope_limit_right_2 = second


def _settings(method, first, second=None):
    from ogr_core.project.settings import SearchSettings
    s = SearchSettings()
    s.search_method = method
    s.slope_limit_left, s.slope_limit_right = first
    if second is not None:
        s.slope_limit_left_2, s.slope_limit_right_2 = second
    return s


def _poly(pts):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))


# The wall of verification problem 87, D77's own model: foundation at
# y = 6, three 3 m tiers with vertical faces at x = 6, 7.2 and 8.4, crest
# at y = 15, model from x = 0 to 24; exit window on the lower bench and
# entry window on the crest (``test_grid_radius_two_windows_v1148``).
_WALL = [(0.0, 0.0), (24.0, 0.0), (24.0, 15.0), (8.4, 15.0), (8.4, 12.0),
         (7.2, 12.0), (7.2, 9.0), (6.0, 9.0), (6.0, 6.0), (0.0, 6.0)]
_EXIT, _ENTRY = (0.0, 6.5), (8.4, 24.0)


def _wall():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in _WALL], closed=True)
    ext.ensure_ccw()
    p = Project("wall")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="fill", unit_weight=18.0,
                            strength=MohrCoulomb(cohesion=0.0,
                                                 friction_angle=34.0))]
    return p


def _grid(slope_limits, **kw):
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    kw.setdefault("min_radius", 0.0)
    kw.setdefault("num_slices", 12)
    return GridSearch(method=BishopSimplified(), slope_limits=slope_limits,
                      **kw)


# ======================================================================
class TestAGridWithOverlappingWindowsIsRefused:
    """Invariant 1, the refusal (D262)."""

    def test_the_rule_as_a_truth_table(self):
        """Refused: nested in both orders, and partial overlap. Accepted:
        separate, touching at one point, a single set, and every search
        but the grid. Fails on v0.1.260, which has no such rule."""
        from ogr_core.project.rules import slope_limit_windows_refusal
        refused = [((0.0, 30.0), (14.473, 18.0)),
                   ((14.473, 18.0), (0.0, 30.0)),
                   ((0.0, 20.0), (10.0, 30.0))]
        accepted = [((0.0, 10.0), (20.0, 30.0)),
                    ((0.0, 10.0), (10.0, 30.0)),
                    ((0.0, 30.0), None)]
        for first, second in refused:
            why = slope_limit_windows_refusal(_settings("grid", first,
                                                        second))
            assert why is not None, (first, second)
            assert why.code == "slope_limit_windows_overlap"
        for first, second in accepted:
            assert slope_limit_windows_refusal(
                _settings("grid", first, second)) is None, (first, second)
        for method in ("block", "path", "slope", "auto_refine"):
            assert slope_limit_windows_refusal(_settings(
                method, (0.0, 30.0), (14.473, 18.0))) is None, method

    def test_the_premise_nested_windows_give_no_radius_anywhere(self):
        """The D77 rule with the second window inside the first: the
        bracket is degenerate (one tangent radius) at EVERY centre of a
        grid over the slope, so refusing takes away nothing that existed.
        With the same two widths made separate, the same centres do have
        brackets, so this can tell the two apart."""
        p = _slope()
        centres = [(x, y) for x in (20.0, 25.0, 30.0, 35.0, 40.0)
                   for y in (35.0, 42.0, 50.0, 60.0)]

        def brackets(windows):
            gs = _grid(windows)
            pts = gs._slope_surface(p)
            return [gs._radius_bracket(xc, yc, pts) for xc, yc in centres]

        nested = brackets(((0.0, 60.0), (20.0, 40.0)))
        assert all(lo == hi for lo, hi in nested), nested
        separate = brackets(((0.0, 20.0), (40.0, 60.0)))
        assert any(hi > lo for lo, hi in separate), separate

    def test_the_analysis_refuses_it_and_says_why(self):
        from ogr_slip2d.analysis_runner import (AnalysisNotConfigured,
                                                check_analysis_settings,
                                                run_analysis)
        p = _slope()
        s = p.settings.search
        s.search_method, s.surface_type = "grid", "circular"
        _limits(p, (0.0, 60.0), (20.0, 40.0))
        try:
            run_analysis(p, method_ids=["bishop_simplified"])
            raise AssertionError("not refused")
        except AnalysisNotConfigured as exc:
            text = " ".join(exc.problems)
        assert "overlap" in text and "[0, 60] and [20, 40]" in text, text
        _limits(p, (0.0, 20.0), (40.0, 60.0))
        assert not any("overlap" in m for m in check_analysis_settings(p))


# ======================================================================
class TestASetInsideTheOtherIsSaid:
    """Invariant 1, the note for the other searches (D262)."""

    def _notes(self, method, first, second):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _slope()
        p.settings.search.search_method = method
        _limits(p, first, second)
        return [n for n in settings_warnings(p, ["bishop_simplified"])
                if "lies inside the other" in n]

    def test_a_block_search_with_a_set_inside_the_other_is_told(self):
        """The bank's 109, 0..30 + 14.473..18, as a Block Search. Fails on
        v0.1.260, which says nothing."""
        lines = self._notes("block", (0.0, 30.0), (14.473, 18.0))
        assert len(lines) == 1, lines
        assert "[14.473, 18]" in lines[0] and "[0, 30]" in lines[0]
        assert "does nothing" in lines[0]

    def test_a_path_search_is_told_where_it_still_acts(self):
        lines = self._notes("path", (14.473, 18.0), (0.0, 30.0))
        assert len(lines) == 1 and "Path Search still starts" in lines[0]

    def test_no_note_where_the_second_set_does_act(self):
        """Separate windows, partial overlap (the union is wider than
        either), and the grid (refused, not told)."""
        assert not self._notes("block", (0.0, 10.0), (20.0, 30.0))
        assert not self._notes("block", (0.0, 20.0), (10.0, 30.0))
        assert not self._notes("grid", (0.0, 30.0), (14.473, 18.0))


# ======================================================================
class TestASlopeLimitRefusalHasAName:
    """Invariant 2 (D263)."""

    #: The point object, the left rays and the right rays.
    _P = (25.0, 6.0)
    _LEFT = (135.0, 160.0)
    _RIGHT = (35.0, 45.0)
    _BUDGET = 40

    def _left_exit(self, deg):
        """Where a left ray from ``_P`` daylights, in closed form: on the
        face y = x - 10 (20 <= x <= 40) if it reaches it, else on the toe
        flat y = 10."""
        x0, y0 = self._P
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        t = (x0 - 10.0 - y0) / (s - c)
        if 20.0 <= x0 + t * c <= 40.0:
            return x0 + t * c
        return x0 + (10.0 - y0) / s * c

    def _block(self, windows):
        from ogr_core.geometry import (BlockObjectKind, BlockObjectSpec,
                                       Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_slip2d.analysis_runner import build_search
        p = _slope()
        b = Boundary(polyline=Polyline(vertices=[Vertex(*self._P)],
                                       closed=False),
                     btype=BoundaryType.BLOCK_SEARCH_OBJECT)
        b.block_object = BlockObjectSpec(BlockObjectKind.POINT, group_id=1)
        p.add_boundary(b)
        s = p.settings.search
        s.search_method, s.surface_type = "block", "non_circular"
        s.block_num_surfaces = self._BUDGET
        s.block_left_start_angle_deg, s.block_left_end_angle_deg = self._LEFT
        s.block_right_start_angle_deg, s.block_right_end_angle_deg = \
            self._RIGHT
        s.min_area = 0.0
        _limits(p, *windows)
        return build_search(p, "bishop_simplified").run(p)

    def test_the_premise_where_the_left_rays_daylight(self):
        """Every left ray lands in [14.01, 20.5], monotonically in the
        angle, so the two windows below are on either side of it."""
        xs = [self._left_exit(a) for a in (135.0, 140.0, 150.0, 160.0)]
        assert xs == sorted(xs, reverse=True), xs
        assert 14.0 < xs[-1] and xs[0] < 20.6, xs

    def test_a_block_search_refused_whole_by_the_limits_says_so(self):
        """Left window [0, 10], outside every left exit: all 40 candidates
        are refused by the limits, and the run says it. Fails on v0.1.260:
        no count, no note."""
        from ogr_slip2d.interpretation import ERROR_OTHER, invalid_summary
        r = self._block(((0.0, 10.0), (40.0, 60.0)))
        assert r.valid_count == 0
        assert r.outside_slope_limits == self._BUDGET == r.total_count
        lines = [n for n in r.notes if n.startswith("No trial surface")]
        assert len(lines) == 1, r.notes
        assert ("%d with an end outside the Slope Limits [0, 10] and "
                "[40, 60]" % self._BUDGET) in lines[0], lines[0]
        census = invalid_summary(r)
        assert census["by_reason"].get(
            "an end daylights outside the Slope Limits") == self._BUDGET
        assert census["by_code"].get(ERROR_OTHER) == self._BUDGET
        assert census["not_sliced"] == 0

    def test_the_control_window_over_the_exits_refuses_none(self):
        r = self._block(((10.0, 22.0), (40.0, 60.0)))
        assert r.outside_slope_limits == 0
        assert r.valid_count == self._BUDGET
        assert not any(n.startswith("No trial surface") for n in r.notes)

    def test_a_path_search_counts_the_exits_it_throws_away(self):
        """One window round the toe only: a surface that emerges on the
        crest is outside it. With the whole profile as the window, none
        is."""
        from ogr_slip2d.analysis_runner import build_search
        out = {}
        for window in ((10.0, 25.0), (0.0, 60.0)):
            p = _slope()
            s = p.settings.search
            s.search_method, s.surface_type = "path", "non_circular"
            s.path_num_surfaces = 30
            s.min_area = 0.0
            _limits(p, window)
            out[window] = build_search(p, "bishop_simplified").run(p)
        toe = out[(10.0, 25.0)]
        assert toe.outside_slope_limits > 0
        assert toe.outside_slope_limits <= toe.invalid_count
        assert out[(0.0, 60.0)].outside_slope_limits == 0

    def test_the_single_surface_door_names_the_limits(self):
        """A polyline whose left end, (15, 10), is outside the windows.
        Fails on v0.1.260, which blamed a surface that "does not cut the
        model"."""
        from ogr_slip2d.analysis_runner import build_search
        surface = [(15.0, 10.0), (24.0, 6.0), (34.0, 9.0), (42.0, 18.0),
                   (48.0, 30.0)]
        p = _slope()
        _limits(p, (0.0, 10.0), (40.0, 60.0))
        s = build_search(p, "bishop_simplified")
        assert s.evaluate_surface(p, _poly(surface)) is None
        assert "Slope Limits" in s.refusal_text(), s.refusal_text()
        assert s._outside_slope_limits == 1
        p = _slope()
        _limits(p, (10.0, 20.0), (40.0, 60.0))
        s = build_search(p, "bishop_simplified")
        assert s.evaluate_surface(p, _poly(surface)) is not None

    def test_a_circle_that_misses_the_ground_is_the_references_101(self):
        """D77's centres with no valid radius: the grid emits the tangent
        radius rinc + 1 times at each, and every one of those circles
        misses the ground. All 27 are counted as such, and the run that
        ends with nothing says so."""
        from ogr_slip2d.interpretation import invalid_summary
        r = _grid((_EXIT, _ENTRY), grid_x=(-24.0, -22.1), grid_y=(15.0, 16.8),
                  grid_nx=2, grid_ny=2, radius_increment=2,
                  min_area=2.0).run(_wall())
        assert r.total_count == 27 and r.valid_count == 0
        assert r.misses_ground == 27
        assert invalid_summary(r)["by_reason"].get(
            "the circle does not cut the ground surface twice") == 27
        assert any("27 circles that do not cut the ground twice" in n
                   for n in r.notes), r.notes

    def test_a_run_with_a_valid_surface_says_nothing_of_the_kind(self):
        """The note is for the run that found NOTHING. A grid with valid
        circles, and a search whose generation is two given surfaces of
        which one is refused by the limits and one is fine."""
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import SearchResult
        r = _grid(None, grid_x=(20.0, 40.0), grid_y=(35.0, 55.0), grid_nx=2,
                  grid_ny=2, radius_increment=2, min_area=0.0).run(_slope())
        assert r.valid_count > 0
        assert not any(n.startswith("No trial surface") for n in r.notes)

        p = _slope()
        _limits(p, (10.0, 20.0), (40.0, 60.0))
        s = build_search(p, "bishop_simplified")
        inside = [(15.0, 10.0), (24.0, 6.0), (34.0, 9.0), (42.0, 18.0),
                  (48.0, 30.0)]
        outside = [(5.0, 10.0)] + inside[1:]

        def _run(project):
            out = SearchResult(method_id=s.method.METHOD_ID,
                               objective=s.objective)
            for pts in (outside, inside):
                e = s.evaluate_surface(project, _poly(pts))
                if e is None:
                    out.invalid_count += 1
                    continue
                out.evaluations.append(e)
                out.valid_count += int(e.is_valid)
            return out

        s._run = _run
        out = s.run(p)
        assert out.outside_slope_limits == 1 and out.valid_count == 1
        assert not any(n.startswith("No trial surface") for n in out.notes)


# ======================================================================
class TestAParallelGridSaysWhatASequentialOneSays:
    """Invariant 3 (D255)."""

    def _weak(self, parallel):
        """The slope with a weak layer and a 40-degree base-angle ceiling
        for the surfaces it clips: some fifty clipped circles of this grid
        are discarded, each with a note naming its own steepest base. 7 x 7
        centres x 11 radii = 539 circles, over the 400 that start a pool."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        p = _slope()
        joint = Material(name="Joint", unit_weight=20.0,
                         strength=MohrCoulomb(cohesion=0.0,
                                              friction_angle=20.0))
        p.materials.append(joint)
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(5.0, 6.0), Vertex(55.0, 16.0)], closed=False),
            btype=BoundaryType.WEAK_LAYER, material_id=joint.id))
        s = p.settings.search
        s.search_method, s.surface_type = "grid", "circular"
        s.grid_x_min, s.grid_x_max = 15.0, 40.0
        s.grid_y_min, s.grid_y_max = 35.0, 60.0
        s.grid_nx = s.grid_ny = 6
        s.radius_increment = 10
        s.min_area = 0.0
        p.settings.methods.num_slices = 12
        p.settings.advanced.max_base_angle_deg = 40.0
        p.settings.advanced.parallel_search = parallel
        p.settings.advanced.parallel_cpu_percent = 100
        return p

    def _needs_a_pool(self, p, n):
        from ogr_slip2d.search import _worker_count
        import pytest
        if _worker_count(p, n) < 2:
            pytest.skip("this machine runs the grid in a single process")

    def _run(self, p, mid="bishop_simplified", progress=None):
        """Run, recording whether the parallel path really ran."""
        import ogr_slip2d.search as S
        from ogr_slip2d.analysis_runner import build_search
        real = S._parallel_grid_run
        used = []

        def spy(*a, **k):
            out = real(*a, **k)
            used.append(out is not None)
            return out

        S._parallel_grid_run = spy
        try:
            s = build_search(p, mid)
            if progress is not None:
                s.progress_cb = lambda d, t: progress.append((d, t))
            r = s.run(p)
        finally:
            S._parallel_grid_run = real
        return s, r, used

    def test_the_same_notes_in_the_same_order(self):
        """Fails on v0.1.260: some fifty notes in series, none in
        parallel."""
        self._needs_a_pool(self._weak(True), 539)
        _s1, seq, used = self._run(self._weak(False))
        assert not used
        _s2, par, used = self._run(self._weak(True))
        assert used == [True], used
        assert par.critical.fos == seq.critical.fos
        assert len(seq.notes) > 10, seq.notes
        assert par.notes == seq.notes

    def test_the_same_counters(self):
        """D77's wall with its two windows over a grid that holds centres
        with no valid radius: the circles that miss the ground are counted
        alike, in series and in parallel."""
        from ogr_slip2d.search import _RUN_COUNTERS

        def wall(parallel):
            p = _wall()
            s = p.settings.search
            s.search_method, s.surface_type = "grid", "circular"
            s.grid_x_min, s.grid_x_max = -24.0, -4.0
            s.grid_y_min, s.grid_y_max = 15.0, 40.0
            s.grid_nx = s.grid_ny = 6
            s.radius_increment = 10
            s.min_area = 2.0
            _limits(p, _EXIT, _ENTRY)
            p.settings.methods.num_slices = 12
            p.settings.advanced.parallel_search = parallel
            p.settings.advanced.parallel_cpu_percent = 100
            return p

        self._needs_a_pool(wall(True), 539)
        s1, seq, _ = self._run(wall(False))
        s2, par, used = self._run(wall(True))
        assert used == [True], used
        assert seq.misses_ground > 0
        assert par.misses_ground == seq.misses_ground
        for name in _RUN_COUNTERS:
            assert getattr(s2, name) == getattr(s1, name), name
        assert par.notes == seq.notes

    def test_the_progress_moves_batch_by_batch(self):
        """Fails on v0.1.260, which called the callback once, at the end."""
        p = self._weak(True)
        self._needs_a_pool(p, 539)
        calls = []
        _s, _r, used = self._run(p, progress=calls)
        assert used == [True], used
        assert len(calls) > 2, calls
        assert calls == sorted(calls), calls
        assert calls[-1] == (49, 49), calls
