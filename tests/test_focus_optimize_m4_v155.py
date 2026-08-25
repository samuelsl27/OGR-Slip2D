# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.55 — Focus objects and surface optimisation (phase M4).

**Focus objects** narrow a grid search to circles that interact with a
window, a line, a point or a tangent. The geometry is the whole feature,
so it is tested against hand-computable cases rather than against a
search outcome.

**Optimisation** refines a non-circular surface by random walking
(Greco, 1996). Two implementation choices proved to matter and are
pinned down here:

* **Densification.** A Path or Block Search surface may have four
  vertices, leaving two movable points — far too few for a walk to
  reshape anything. Measured: without densifying, the walk improves the
  reference case by 0.0000; densified to twelve vertices it lowers the
  factor of safety by 0.043.
* **The step is floored, not allowed to end the run.** Exiting the moment
  it underflowed gave a walk of ten evaluations, which optimises nothing.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_slip2d import (  # noqa: E402
    BishopSimplified,
    FocusKind as F,
    FocusObject,
    OptimizeSettings,
    Spencer,
    accepts,
    filter_circles,
    optimize_surface,
)
from ogr_slip2d.search import GridSearch, PathSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402


# ======================================================================
class TestFocusPoint:
    def test_accepts_a_circle_passing_through_it(self):
        """A circle of radius 10 about the origin passes exactly through
        (10, 0)."""
        fo = FocusObject(kind=F.POINT, points=[(10.0, 0.0)],
                         tolerance=0.1)
        assert fo.accepts_circle(0.0, 0.0, 10.0) is True

    def test_rejects_one_that_misses(self):
        fo = FocusObject(kind=F.POINT, points=[(10.0, 0.0)],
                         tolerance=0.1)
        assert fo.accepts_circle(0.0, 0.0, 12.0) is False

    def test_tolerance_widens_the_capture(self):
        fo = FocusObject(kind=F.POINT, points=[(10.0, 0.0)],
                         tolerance=2.5)
        assert fo.accepts_circle(0.0, 0.0, 12.0) is True

    def test_a_point_inside_the_disc_is_not_on_the_circle(self):
        """Passing THROUGH a point is not the same as containing it: a
        slip surface that never reaches the point is not focused on it."""
        fo = FocusObject(kind=F.POINT, points=[(1.0, 0.0)],
                         tolerance=0.1)
        assert fo.accepts_circle(0.0, 0.0, 10.0) is False


class TestFocusTangent:
    def test_accepts_a_tangent_circle(self):
        """Centre at (0, 10), radius 10, tangent to y = 0."""
        fo = FocusObject(kind=F.TANGENT, points=[(-50, 0), (50, 0)],
                         tolerance=0.05)
        assert fo.accepts_circle(0.0, 10.0, 10.0) is True

    def test_rejects_a_crossing_circle(self):
        """Crossing is not tangency — the distinction is the point of
        this focus type."""
        fo = FocusObject(kind=F.TANGENT, points=[(-50, 0), (50, 0)],
                         tolerance=0.05)
        assert fo.accepts_circle(0.0, 5.0, 10.0) is False

    def test_rejects_one_that_does_not_reach(self):
        fo = FocusObject(kind=F.TANGENT, points=[(-50, 0), (50, 0)],
                         tolerance=0.05)
        assert fo.accepts_circle(0.0, 20.0, 10.0) is False

    def test_uses_the_infinite_line(self):
        """A circle tangent beyond the drawn extent is still tangent to
        that plane, which is what a weak layer represents."""
        fo = FocusObject(kind=F.TANGENT, points=[(0, 0), (1, 0)],
                         tolerance=0.05)
        assert fo.accepts_circle(500.0, 10.0, 10.0) is True


class TestFocusLine:
    def test_accepts_a_crossing_circle(self):
        fo = FocusObject(kind=F.LINE, points=[(0, -20), (0, 20)])
        assert fo.accepts_circle(0.0, 0.0, 10.0) is True

    def test_rejects_a_distant_circle(self):
        fo = FocusObject(kind=F.LINE, points=[(100, -20), (100, 20)])
        assert fo.accepts_circle(0.0, 0.0, 10.0) is False

    def test_segment_wholly_inside_does_not_cross(self):
        """A segment buried inside the disc never meets the arc."""
        fo = FocusObject(kind=F.LINE, points=[(-1, 0), (1, 0)])
        assert fo.accepts_circle(0.0, 0.0, 10.0) is False


class TestFocusWindow:
    def test_accepts_a_circle_passing_through(self):
        fo = FocusObject(kind=F.WINDOW,
                         points=[(8, -2), (12, -2), (12, 2), (8, 2)])
        assert fo.accepts_circle(0.0, 0.0, 10.0) is True

    def test_rejects_one_that_misses_the_window(self):
        fo = FocusObject(kind=F.WINDOW,
                         points=[(50, 50), (60, 50), (60, 60), (50, 60)])
        assert fo.accepts_circle(0.0, 0.0, 10.0) is False

    def test_window_containing_the_centre_but_not_the_arc(self):
        """The circumference is what matters, not the centre."""
        fo = FocusObject(kind=F.WINDOW,
                         points=[(-1, -1), (1, -1), (1, 1), (-1, 1)])
        assert fo.accepts_circle(0.0, 0.0, 10.0) is False


class TestFocusCombination:
    def test_no_objects_accepts_everything(self):
        """The feature must cost nothing when unused."""
        assert accepts([], 0.0, 0.0, 10.0) is True
        assert accepts(None, 0.0, 0.0, 10.0) is True

    def test_objects_are_combined_with_and(self):
        """Adding a second object must NARROW the search: that is what
        'focus' means."""
        a = FocusObject(kind=F.POINT, points=[(10, 0)], tolerance=0.1)
        b = FocusObject(kind=F.POINT, points=[(0, 50)], tolerance=0.1)
        assert accepts([a], 0.0, 0.0, 10.0) is True
        assert accepts([a, b], 0.0, 0.0, 10.0) is False

    def test_disabled_object_filters_nothing(self):
        fo = FocusObject(kind=F.POINT, points=[(999, 999)],
                         tolerance=0.1, enabled=False)
        assert fo.accepts_circle(0.0, 0.0, 10.0) is True

    def test_malformed_object_filters_nothing(self):
        """Rather than silently rejecting every surface."""
        fo = FocusObject(kind=F.WINDOW, points=[(0, 0)])
        assert fo.valid is False
        assert fo.accepts_circle(0.0, 0.0, 10.0) is True

    def test_round_trip(self):
        fo = FocusObject(kind=F.TANGENT, points=[(0, 1), (5, 1)],
                         tolerance=0.75, enabled=False)
        fo2 = FocusObject.from_dict(fo.to_dict())
        assert fo2.kind == F.TANGENT
        assert abs(fo2.tolerance - 0.75) < 1e-12
        assert fo2.enabled is False
        assert fo2.id == fo.id


class TestFocusOnARealSearch:
    def test_filter_reduces_the_candidate_set(self):
        p = _ej1_project()
        run = GridSearch(method=BishopSimplified(), grid_x=(60, 110),
                         grid_y=(55, 95), grid_nx=4, grid_ny=4,
                         radius_increment=10, min_radius=10,
                         num_slices=14, min_area=0.5).run(p)
        circles = [e.surface for e in run.evaluations if e.is_valid]
        assert circles
        tangent = FocusObject(kind=F.TANGENT,
                              points=[(0, 15), (120, 15)], tolerance=0.5)
        kept = filter_circles([tangent], circles)
        assert 0 < len(kept) < len(circles)

    def test_every_kept_circle_satisfies_the_object(self):
        p = _ej1_project()
        run = GridSearch(method=BishopSimplified(), grid_x=(60, 110),
                         grid_y=(55, 95), grid_nx=4, grid_ny=4,
                         radius_increment=10, min_radius=10,
                         num_slices=14, min_area=0.5).run(p)
        circles = [e.surface for e in run.evaluations if e.is_valid]
        fo = FocusObject(kind=F.WINDOW,
                         points=[(50, 10), (90, 10), (90, 35), (50, 35)])
        for c in filter_circles([fo], circles):
            assert fo.accepts_circle(c.centre_x, c.centre_y, c.radius)


class TestFocusInTheSearchEngine:
    """The filter must act BEFORE evaluation, or focusing saves nothing:
    rejecting a circle costs two distance calculations, evaluating one
    costs a full slicing and iteration."""

    _KW = dict(grid_x=(60, 110), grid_y=(55, 95), grid_nx=4, grid_ny=4,
               radius_increment=10, min_radius=10, num_slices=14,
               min_area=0.5)

    def test_focus_reduces_the_number_evaluated(self):
        p = _ej1_project()
        base = GridSearch(method=BishopSimplified(), **self._KW).run(p)
        tangent = FocusObject(kind=F.TANGENT,
                              points=[(0, 15), (120, 15)], tolerance=1.0)
        focused = GridSearch(method=BishopSimplified(),
                             focus_objects=[tangent], **self._KW).run(p)
        assert len(focused.evaluations) < len(base.evaluations) / 2, (
            len(focused.evaluations), len(base.evaluations))

    def test_focused_search_still_finds_something(self):
        p = _ej1_project()
        tangent = FocusObject(kind=F.TANGENT,
                              points=[(0, 15), (120, 15)], tolerance=1.0)
        run = GridSearch(method=BishopSimplified(),
                         focus_objects=[tangent], **self._KW).run(p)
        assert run.critical is not None
        assert run.valid_count > 0

    def test_every_evaluated_circle_satisfies_the_focus(self):
        p = _ej1_project()
        window = FocusObject(kind=F.WINDOW,
                             points=[(50, 10), (90, 10), (90, 35),
                                     (50, 35)])
        run = GridSearch(method=BishopSimplified(),
                         focus_objects=[window], **self._KW).run(p)
        for ev in run.evaluations:
            c = ev.surface
            assert window.accepts_circle(c.centre_x, c.centre_y,
                                         c.radius)

    def test_no_focus_leaves_the_search_unchanged(self):
        """The feature must cost nothing when unused."""
        p = _ej1_project()
        a = GridSearch(method=BishopSimplified(), **self._KW).run(p)
        b = GridSearch(method=BishopSimplified(), focus_objects=[],
                       **self._KW).run(p)
        assert len(a.evaluations) == len(b.evaluations)
        assert abs(a.critical.fos - b.critical.fos) < 1e-12

    def test_disabled_focus_is_not_applied_by_the_engine(self):
        p = _ej1_project()
        off = FocusObject(kind=F.POINT, points=[(999, 999)],
                          tolerance=0.1, enabled=False)
        a = GridSearch(method=BishopSimplified(), **self._KW).run(p)
        b = GridSearch(method=BishopSimplified(), focus_objects=[off],
                       **self._KW).run(p)
        assert len(a.evaluations) == len(b.evaluations)

    def test_slope_limits_restrict_the_search(self):
        p = _ej1_project()
        wide = GridSearch(method=BishopSimplified(), **self._KW).run(p)
        narrow = GridSearch(method=BishopSimplified(),
                            slope_limits=(20.0, 80.0), **self._KW).run(p)
        assert len(narrow.evaluations) <= len(wide.evaluations)
        assert narrow.critical is not None

    def test_limits_persist_on_the_project(self):
        """None means automatic — derived from the ground surface, which
        keeps a model portable between geometries."""
        from ogr_core.project import Project
        p = Project(name="x")
        assert p.settings.search.slope_limit_left is None
        p.settings.search.slope_limit_left = 10.0
        p.settings.search.slope_limit_right = 90.0
        p2 = Project.from_dict(p.to_dict())
        assert p2.settings.search.slope_limit_left == 10.0
        assert p2.settings.search.slope_limit_right == 90.0

    def test_focus_objects_persist_on_the_project(self):
        from ogr_core.project import Project
        p = Project(name="x")
        assert p.focus_objects == []
        p.focus_objects.append(FocusObject(
            kind=F.TANGENT, points=[(0, 15), (120, 15)], tolerance=0.75))
        p2 = Project.from_dict(p.to_dict())
        assert len(p2.focus_objects) == 1
        assert p2.focus_objects[0].kind == F.TANGENT
        assert abs(p2.focus_objects[0].tolerance - 0.75) < 1e-12


# ======================================================================
class TestOptimisation:
    # The starting surface is computed once and reused: re-running a Path
    # Search per test was the bulk of the cost and adds nothing to the
    # invariants under test.
    _CACHE = {}

    def _start(self):
        if not self._CACHE:
            p = _ej1_project()
            # v0.1.118 — the segment length is PINNED, and stating the
            # premise beats inheriting it. These tests need the SHORT
            # surface, the one with few movable vertices, because that is
            # the fragile case for the walk. It used to arrive by accident:
            # the automatic length was 0.3 x the relief of the MODEL, and
            # Ej_1 carries 25 m of foundation under its toe bench, so the
            # search chopped a 25 m slope into 15 m segments. With the
            # relief of the SLOPE, as the reference states it, the
            # automatic value is 7.5 and the same search returns fourteen
            # vertices — a perfectly good surface, and the wrong one for
            # what is being measured here.
            run = PathSearch(method=Spencer(), num_paths=15,
                             num_slices=14, seed=3,
                             segment_length=15.0).run(p)
            self._CACHE["v"] = (p, run.critical.surface,
                                run.critical.fos)
        p, surf, fos = self._CACHE["v"]
        evaluator = PathSearch(method=Spencer(), num_slices=14,
                               min_area=0.0)
        return p, evaluator, surf, fos

    def test_the_walk_spends_the_budget_it_was_given(self):
        """v0.1.104 — this test used to assert the opposite finding, and
        the reason it changed is worth more than the assertion.

        It was called ``test_densification_is_what_makes_it_work`` and it
        claimed: with the handful of vertices a Path Search produces, the
        walk
        barely moves the factor of safety; densified to twelve, it lowers
        it appreciably. Measured on this very surface, at 200 evaluations
        and seed 7:

            v0.1.103   densify_to=0    +0.0007 in  36 evaluations, 3 accepted
                       densify_to=12   +0.0228 in 200 evaluations, 22 accepted
            v0.1.104   densify_to=0    +0.0939 in 200 evaluations, 91 accepted
                       densify_to=12   +0.0765 in 200 evaluations, 75 accepted

        Read the middle column. The old plain walk did not fail to find
        anything — it STOPPED, after 36 of the 200 evaluations it was
        given, and the two things that stopped it were both this module's
        own inventions rather than the reference's: an acceptance deadband
        of 1e-4 (the documented rule is simply "if the factor of safety
        for the modified surface is lower [...] the new surface replaces
        the original"), and a hard-coded limit of six fruitless passes.
        With two movable vertices, improvements below the deadband are
        most of what there is, so the walk ran out of patience at once.
        The 0.0007 was measuring the stopping rule, not densification.

        So the invariant this file protects here is now the one that was
        actually violated: **a walk that still has budget and is still
        finding improvements must not stop**. Densification remains what
        gives a four-vertex surface room to be reshaped — it is asserted
        by ``test_densified_surface_has_the_requested_vertices`` and by
        the vertex count — but it is no longer the difference between
        working and not working, and saying that it is would be recording
        a measurement that has been superseded.

        The threshold is a CONTRAST against the number the old stopping
        rule produced, two orders of magnitude below either column, not a
        capture of what this code prints today.

        v0.1.105 — THE SEED WAS DOING TOO MUCH OF THE WORK, and that is a
        second finding, kept because it explains why this case moved.

        Asserting ``iterations > 150`` on ONE seed does not measure "the walk
        spends its budget"; it measures whether that particular walk got
        lucky. Swept over eight seeds on this very surface, before and after
        the moment-axis change of v0.1.105:

            v0.1.104   plain   7 of 8 seeds reach 200, seed 13 stops at 100
            v0.1.105   plain   6 of 8 seeds reach 200, seed 13 at 99, seed 7 at 57

        Seed 13 was ALREADY below the threshold in v0.1.104, so this case was
        one nudge away from failing there too — it happened to be calibrated
        on a seed that survived. And the walk did not get worse: across the
        eight seeds v0.1.105 improves the factor by +0.0592 to +0.1391 against
        +0.0926 to +0.1079, so it finds MORE, with one unlucky seed finding
        less.

        The variation itself — a factor of 2.4 between seeds on the same
        surface with the same budget — is a real property of this random walk
        and is NOT addressed here; it is the same family as the Simulated
        Annealing start that depended on luck (rule 6 of AGENTS.md). What is
        addressed is the measurement: the assertion now runs over a spread of
        seeds and holds the MEDIAN, which is what "spends the budget it was
        given" actually claims and what a return of the old stopping rule
        would drag down.
        """
        import statistics
        p, ev, surf, _f0 = self._start()
        assert len(surf.polyline.vertices) == 5, (
            "the premise: this is the short surface a Path Search makes")
        # Only the PLAIN walk is swept. With two movable vertices it is the
        # fragile one — it is where a seed stops early in both versions — and
        # sweeping the densified walk as well found nothing: twelve vertices
        # reach the full 200 on all eight seeds, before and after. Five seeds
        # rather than eight because the sweep is not free: the whole file went
        # from 11 s to 45 s at eight, and to about 21 s here.
        seeds = (1, 3, 5, 7, 11)
        plain = [
            optimize_surface(p, ev, surf,
                             OptimizeSettings(max_iterations=200, seed=seed,
                                              densify_to=0))[2]
            for seed in seeds
        ]
        _s2, _r2, dense = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=200, seed=7,
                                          densify_to=12))

        # Every walk must find something. This half was never seed-fragile:
        # the worst seed of either version is +0.04.
        for seed, rep in zip(seeds, plain):
            assert rep.improvement > 0.01, (seed, rep.summary())
        assert dense.improvement > 0.01, dense.summary()

        # And the budget itself: the walk may not abandon it while it is
        # still buying improvements. 36 of 200 was the defect, and it was the
        # TYPICAL walk that stopped there, not one unlucky seed — so the
        # median is the statistic that catches its return, and it tolerates
        # two unlucky seeds out of five without going blind to the defect.
        median = statistics.median(r.iterations for r in plain)
        assert median > 150, (median, [r.summary() for r in plain])
        assert dense.iterations > 150, dense.summary()

    def test_the_starting_surface_is_fully_sliced(self):
        """Why the numbers above are what they are, pinned separately.

        A Path Search minimum built from fewer slices than it asked for is
        not a minimum, it is a shorter surface. Before v0.1.100 this one was
        twelve of fourteen."""
        from ogr_slip2d.slicer import slice_surface
        p, _ev, surf, _f0 = self._start()
        sl = slice_surface(p, surf, 14)
        assert sl is not None
        assert len(sl) == 14, len(sl)

    def test_never_returns_a_worse_surface(self):
        """A walk that ends worse than it started would be useless: only
        improvements are accepted."""
        p, ev, surf, _f0 = self._start()
        _s, _r, rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=60, seed=1))
        assert rep.final_fos <= rep.initial_fos + 1e-9

    def test_it_starts_from_the_surface_it_was_given(self):
        """v0.1.90 — this used to ride along in the case above as
        ``abs(rep.initial_fos - f0) < 0.05``, and it was measuring
        something else: with the default ``densify_to=12`` the optimiser
        reports the factor of safety of the DENSIFIED surface, which is a
        different surface from the four-vertex one ``f0`` came from. The
        0.05 was a capture of how far densification happened to move that
        particular surface, and when v0.1.90's λ range changed which of
        fifteen random paths comes out critical, the new one moved 0.061.
        Nothing had broken; the tolerance was measuring the wrong thing.

        Without densification the claim is an IDENTITY and needs no
        tolerance at all: the walk must start from exactly the number the
        evaluator gives for the surface it was handed.
        """
        p, ev, surf, f0 = self._start()
        _s, _r, rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=1, seed=1,
                                          densify_to=0))
        assert rep.initial_fos == f0, (rep.initial_fos, f0)

    def test_result_is_a_valid_surface(self):
        p, ev, surf, _f0 = self._start()
        best, res, _rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=50, seed=2))
        assert res is not None and res.is_valid
        xs = [v.x for v in best.polyline.vertices]
        assert xs == sorted(xs), "x must stay increasing"

    def test_densified_surface_has_the_requested_vertices(self):
        p, ev, surf, _f0 = self._start()
        best, _r, _rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=40, seed=5,
                                          densify_to=10))
        assert len(best.polyline.vertices) == 10

    def test_endpoints_are_fixed_by_default(self):
        """Keeping them preserves the entry and exit the search found."""
        p, ev, surf, _f0 = self._start()
        first = (surf.polyline.vertices[0].x, surf.polyline.vertices[0].y)
        last = (surf.polyline.vertices[-1].x,
                surf.polyline.vertices[-1].y)
        best, _r, _rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=50, seed=4,
                                          densify_to=8))
        assert abs(best.polyline.vertices[0].x - first[0]) < 1e-9
        assert abs(best.polyline.vertices[-1].x - last[0]) < 1e-9

    def test_seed_is_reproducible(self):
        p, ev, surf, _f0 = self._start()
        a = optimize_surface(p, ev, surf,
                             OptimizeSettings(max_iterations=40, seed=9))[2]
        b = optimize_surface(p, ev, surf,
                             OptimizeSettings(max_iterations=40, seed=9))[2]
        assert abs(a.final_fos - b.final_fos) < 1e-12

    def test_iteration_budget_is_respected(self):
        p, ev, surf, _f0 = self._start()
        _s, _r, rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=50, seed=6))
        assert rep.iterations <= 50

    def test_a_two_point_surface_is_refused_with_a_reason(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipSurface
        p, ev, _s, _f = self._start()
        flat = SlipSurface(polyline=Polyline(
            vertices=[Vertex(0, 0), Vertex(1, 0)], closed=False))
        _best, _res, rep = optimize_surface(
            p, ev, flat, OptimizeSettings(densify_to=0))
        assert "error" in rep.notes
        assert "three vertices" in rep.notes["error"]

    def test_settings_round_trip(self):
        o = OptimizeSettings(enabled=True, max_iterations=123,
                             densify_to=15, seed=42,
                             move_endpoints=True)
        o2 = OptimizeSettings.from_dict(o.to_dict())
        assert o2.enabled is True
        assert o2.max_iterations == 123
        assert o2.densify_to == 15
        assert o2.seed == 42
        assert o2.move_endpoints is True

    def test_report_summary(self):
        p, ev, surf, _f0 = self._start()
        _s, _r, rep = optimize_surface(
            p, ev, surf, OptimizeSettings(max_iterations=40, seed=8))
        text = rep.summary()
        assert "→" in text and "evaluations" in text
        assert rep.accepted + rep.rejected == rep.iterations
