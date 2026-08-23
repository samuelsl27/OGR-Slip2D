# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The two Surface Filters have to move the number, and mean what they say.

WHAT INVARIANT THIS PROTECTS — rule 7, in both directions. ``Minimum
Elevation`` and ``Minimum Depth`` were declared in ``SearchSettings``,
editable in the search dialog under "Filters", written to the .ogr and read
by NOBODY: ``build_search`` passed only ``min_area`` to its six branches, so
a user could tick either filter, get back an answer identical to the last
digit — the surface counts included — and conclude that the filter had
nothing to remove. That is anomaly A37-1, and it is the same shape as the
partial factors that were configurable without being applied between v0.1.52
and v0.1.57.

So: a declared filter must change the answer, and an undeclared one must
change nothing whatsoever.

THIS FILE ASSERTS NO FACTOR OF SAFETY, on purpose. Everything here is either
a DIFFERENCE (two runs of one model must disagree), an IDENTITY (every
surface that survived the filter satisfies it, by definition of the filter),
or a COUNT relation. None of them is a number this code printed, so none of
them can consecrate a bug. The value anchor lives where the project keeps
value anchors: ``validacion/casos/006-xstabl-1999-min-depth``, the published
back-analysis problem of the XSTABL Reference Manual (1999) whose statement
asks for a minimum depth of 2 m and whose answer, 0.764, is only reproduced
when the filter reaches the engine.

WHAT THE FILTERS MEAN, and it is not guessable from the names — the four
questions the implementation had to answer, all four settled by the
documentation of the interface this program follows:

* Minimum Depth is the MAXIMUM slice height of the surface, not a per-slice
  test and not a mean: a deep mechanism is deep somewhere.
* that height is measured VERTICALLY, from the slip surface to the ground,
  not normal to either.
* Minimum Elevation is the lowest point of the SURFACE, not of the mass.
* both DISCARD the surface. Neither trims it.

There is a corroboration of the first two that costs nothing and is worth
recording: the circle published for that 1999 problem has a maximum slice
height of 2.011 m against the 2 m its own statement demands. Read as a mean
depth, or as a distance normal to the ground, the published answer would have
been filtered out by the published requirement.

THE MODEL. A 12 m slope on 10 m of foundation, the same geometry the Slope
Search tests use (``test_slope_search_v117.py``), chosen because the
foundation gives the filters something to bite on: circles can dip well below
the toe, which is exactly the population Minimum Elevation exists to remove.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: Kept small on purpose: nothing here needs a converged minimum, only two
#: runs of the same population, and 9x9 centres x 9 radii is 729 surfaces.
_GRID_NX = _GRID_NY = 8
_RADIUS_INCREMENT = 8
_NUM_SLICES = 20

#: Deep enough to remove most of the population of this model without
#: emptying it. Measured, and reported in the tests that use it.
_MIN_DEPTH = 6.0

#: The toe elevation. Circles that dive into the foundation go below it.
_MIN_ELEVATION = 0.0


def _slope():
    """A 12 m slope on 10 m of foundation."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe + H / math.tan(beta)
    base = -10.0
    ext = Polyline(vertices=[
        Vertex(0, base), Vertex(60, base), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("surface filters")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    s = p.settings.search
    s.search_method = "grid"
    s.grid_x_min, s.grid_x_max = 20.0, 60.0
    s.grid_y_min, s.grid_y_max = 15.0, 40.0
    s.grid_nx, s.grid_ny = _GRID_NX, _GRID_NY
    s.radius_increment = _RADIUS_INCREMENT
    p.settings.methods.num_slices = _NUM_SLICES
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    return p


_CACHE: dict = {}


def _run(**filters):
    """The configured search, run through ``build_search`` as the app does.

    Cached: every test below wants one of three runs of the same 729
    surfaces, and re-running them per test would multiply the cost of this
    file by five for no extra coverage.
    """
    key = tuple(sorted(filters.items()))
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import build_search
        p = _slope()
        for name, value in filters.items():
            setattr(p.settings.search, name, value)
        search = build_search(p, "bishop_simplified")
        _CACHE[key] = (p, search.run(p))
    return _CACHE[key]


def _max_slice_height(result):
    """Maximum vertical slice height of an evaluated surface."""
    slices = getattr(result, "slices", None)
    if not slices:
        return None
    return max(s.height for s in slices)


# ======================================================================
class TestTheFilterMovesTheNumber:
    """Rule 7. Neither of these assertions is about a VALUE; both are
    about a model answering differently when told to."""

    def test_minimum_depth_changes_the_critical_surface(self):
        _, off = _run()
        _, on = _run(min_depth=_MIN_DEPTH)
        assert off.critical is not None and on.critical is not None
        assert on.critical.fos != off.critical.fos, (
            "Minimum Depth changed nothing — the setting is decoration "
            f"(both runs give {off.critical.fos:.6f})")
        # And not merely a different number: a different surface.
        a, b = off.critical.surface, on.critical.surface
        assert (a.centre_x, a.centre_y, a.radius) != \
               (b.centre_x, b.centre_y, b.radius)

    def test_minimum_depth_removes_the_shallow_ones(self):
        """The filtered minimum must be DEEPER, which is the whole point.

        Not "different": a filter for shallow surfaces that returned a
        shallower answer would be wired backwards, and a test that only
        asked for a change would pass on it.
        """
        _, off = _run()
        _, on = _run(min_depth=_MIN_DEPTH)
        h_off = _max_slice_height(off.critical)
        h_on = _max_slice_height(on.critical)
        assert h_off <= _MIN_DEPTH < h_on, (
            f"unfiltered minimum is {h_off:.3f} m deep, filtered one "
            f"{h_on:.3f} m, threshold {_MIN_DEPTH} m")

    def test_minimum_elevation_changes_the_critical_surface(self):
        _, off = _run()
        _, on = _run(min_elevation=_MIN_ELEVATION)
        assert on.critical.fos != off.critical.fos, (
            "Minimum Elevation changed nothing — the setting is decoration")

    def test_minimum_elevation_lifts_the_critical_surface(self):
        """Same argument as the depth one: the direction is part of the
        claim."""
        from ogr_slip2d.surface import lowest_elevation
        _, off = _run()
        _, on = _run(min_elevation=_MIN_ELEVATION)
        assert lowest_elevation(off.critical.surface) < _MIN_ELEVATION
        assert lowest_elevation(on.critical.surface) >= _MIN_ELEVATION


# ======================================================================
class TestTheFilterMeansWhatItSays:
    """Identities, not measurements: every surface that survived satisfies
    the filter, because that is what the filter IS."""

    def test_every_analysed_surface_is_deep_enough(self):
        _, res = _run(min_depth=_MIN_DEPTH)
        checked = 0
        for r in res.evaluations:
            h = _max_slice_height(r)
            if h is None:
                continue
            checked += 1
            assert h > _MIN_DEPTH, (
                f"a surface {h:.4f} m deep survived a {_MIN_DEPTH} m filter")
        assert checked > 20, f"only {checked} surfaces to check"

    def test_every_analysed_surface_is_high_enough(self):
        from ogr_slip2d.surface import lowest_elevation
        _, res = _run(min_elevation=_MIN_ELEVATION)
        checked = 0
        for r in res.evaluations:
            y = lowest_elevation(r.surface)
            if y is None:
                continue
            checked += 1
            assert y >= _MIN_ELEVATION, (
                f"a surface reaching y = {y:.4f} survived a "
                f"{_MIN_ELEVATION} filter")
        assert checked > 20, f"only {checked} surfaces to check"

    def test_the_unfiltered_run_does_contain_what_the_filters_remove(self):
        """Otherwise the two tests above would pass on an empty promise.

        A filter that removes nothing is indistinguishable from a filter
        that is not wired up, which is precisely the failure this file
        exists for.
        """
        from ogr_slip2d.surface import lowest_elevation
        _, res = _run()
        shallow = sum(1 for r in res.evaluations
                      if (_max_slice_height(r) or math.inf) <= _MIN_DEPTH)
        low = sum(1 for r in res.evaluations
                  if (lowest_elevation(r.surface) or math.inf)
                  < _MIN_ELEVATION)
        assert shallow > 0 and low > 0, (shallow, low)


# ======================================================================
class TestFilteringDoesNotMoveTheDenominator:
    """v0.1.83's invariant, which a new filter is well placed to break.

    A filtered surface was still GENERATED, so it has to keep appearing in
    the totals: filtering moves surfaces from valid to invalid and never
    changes how many there were. The reason it matters is that the number
    a user compares between two runs must not depend on which options were
    ticked — the same argument that made 1697 vanished circles a defect.
    """

    def test_the_population_is_the_same_size_with_and_without(self):
        _, off = _run()
        _, depth = _run(min_depth=_MIN_DEPTH)
        _, elev = _run(min_elevation=_MIN_ELEVATION)
        assert off.total_count == depth.total_count == elev.total_count
        expected = (_GRID_NX + 1) * (_GRID_NY + 1) * (_RADIUS_INCREMENT + 1)
        assert off.total_count == expected

    def test_valid_plus_invalid_still_adds_up(self):
        for filters in ({}, {"min_depth": _MIN_DEPTH},
                        {"min_elevation": _MIN_ELEVATION}):
            _, res = _run(**filters)
            assert res.valid_count + res.invalid_count == res.total_count, \
                filters

    def test_a_filter_only_ever_removes(self):
        _, off = _run()
        _, on = _run(min_depth=_MIN_DEPTH)
        assert on.valid_count < off.valid_count
        assert on.invalid_count > off.invalid_count


# ======================================================================
class TestUndeclaredFiltersChangeNothing:
    """The other half of rule 7, and the half that protects every model
    already in the bank: a filter left unticked must be as if it did not
    exist."""

    def _direct(self, **extra):
        from ogr_slip2d import BishopSimplified, GridSearch
        p = _slope()
        search = GridSearch(
            method=BishopSimplified(), grid_x=(20.0, 60.0),
            grid_y=(15.0, 40.0), grid_nx=_GRID_NX, grid_ny=_GRID_NY,
            radius_increment=_RADIUS_INCREMENT, min_radius=0.0,
            num_slices=_NUM_SLICES, min_area=1.0, **extra)
        return search.run(p)

    def test_none_is_indistinguishable_from_not_passing_it(self):
        """Bit for bit, not "within a tolerance"."""
        plain = self._direct()
        explicit = self._direct(min_elevation=None, min_depth=None)
        assert plain.critical.fos == explicit.critical.fos
        assert plain.total_count == explicit.total_count
        assert plain.valid_count == explicit.valid_count
        assert plain.invalid_count == explicit.invalid_count
        assert len(plain.evaluations) == len(explicit.evaluations)

    def test_the_configured_route_defaults_both_to_off(self):
        """A project that says nothing about the filters must produce a
        search that filters nothing.

        Deliberately NOT a comparison against ``_direct()`` above: those
        two searches differ for reasons that have nothing to do with this
        change — ``build_search`` also hands the method the project's
        convergence settings and the slope limits, which a hand-built
        ``BishopSimplified()`` does not have. Asserting they agree would
        be a claim about something else, and it would fail for the wrong
        reason. The bit-for-bit proof is the test above; this one closes
        the plumbing.
        """
        from ogr_slip2d.analysis_runner import build_search
        search = build_search(_slope(), "bishop_simplified")
        assert search.min_depth is None
        assert search.min_elevation is None


# ======================================================================
class TestAllSixSearchesReceiveThem:
    """The filters are global to every search, and this is what stops the
    seventh strategy from being the one that forgets.

    It is not a formality. Every search absorbs unknown keywords through
    ``**legacy_kwargs``, so a filter that ``build_search`` sends and a
    search does not name is swallowed in SILENCE — the same failure as
    A37-1, one branch at a time instead of all six at once.
    """

    METHODS = ("grid", "slope", "auto_refine", "block", "path",
               "simulated_annealing")

    def test_every_branch_of_build_search_gets_both_filters(self):
        from ogr_slip2d.analysis_runner import build_search
        for method in self.METHODS:
            p = _slope()
            p.settings.search.search_method = method
            p.settings.search.min_depth = 3.25
            p.settings.search.min_elevation = -1.75
            search = build_search(p, "bishop_simplified")
            assert search is not None, method
            assert search.min_depth == 3.25, method
            assert search.min_elevation == -1.75, method

    def test_path_search_keeps_its_own_named_argument(self):
        """Path Search has used ``min_elevation`` since it was written, as
        the floor of its vertex sampling. Passing the project's value must
        set BOTH that floor and the filter, or the two would disagree."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import PathSearch
        s = PathSearch(method=BishopSimplified(), min_elevation=-4.0)
        assert s.min_elevation == -4.0

    def test_a_search_built_by_hand_still_defaults_to_off(self):
        from ogr_slip2d import BishopSimplified, GridSearch
        s = GridSearch(method=BishopSimplified())
        assert s.min_depth is None and s.min_elevation is None


# ======================================================================
class TestBothDoorsIntoTheEngineFilter:
    """``evaluate_circle`` and ``evaluate_surface`` are the only two ways
    in, and the non-circular searches use the second one. A filter on one
    door only would be a filter every block, path and annealing run could
    walk around."""

    def test_a_shallow_circle_is_refused(self):
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _slope()
        # A face circle: it daylights on the slope and is 2.32 m thick at
        # its deepest, so a 5 m filter has to refuse it.
        shallow = SlipCircle(centre_x=40.0, centre_y=20.0, radius=14.0)
        loose = GridSearch(method=BishopSimplified(), num_slices=_NUM_SLICES)
        accepted = loose.evaluate_circle(p, shallow)
        assert accepted is not None
        assert _max_slice_height(accepted) < 5.0
        strict = GridSearch(method=BishopSimplified(),
                            num_slices=_NUM_SLICES, min_depth=5.0)
        assert strict.evaluate_circle(p, shallow) is None

    def test_a_deep_polyline_is_refused_by_minimum_elevation(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.surface import SlipSurface
        p = _slope()
        # Toe to slope face, dipping to y = -5 through the foundation.
        # The upper end is 8.39 and not 8.40: the ground there is at
        # 8.396, and a surface poking 4 mm above its own ground is one the
        # slicer refuses whole since v0.1.100 — which would have made this
        # test pass for entirely the wrong reason.
        surf = SlipSurface(polyline=Polyline(vertices=[
            Vertex(30.0, 0.0), Vertex(35.0, -5.0), Vertex(44.0, 8.39)],
            closed=False))
        loose = GridSearch(method=BishopSimplified(), num_slices=_NUM_SLICES)
        assert loose.evaluate_surface(p, surf) is not None
        strict = GridSearch(method=BishopSimplified(),
                            num_slices=_NUM_SLICES, min_elevation=0.0)
        assert strict.evaluate_surface(p, surf) is None


# ======================================================================
class TestLowestElevation:
    """The one piece of new geometry, and the trap it exists to avoid.

    ``SlipCircle.x_range()`` answers with the extent of the WHOLE circle,
    ``xc ± R``, not with the chord that is actually analysed. Reading the
    lowest point off that would put the bottom of the circle on surfaces
    that never reach it.
    """

    def test_centre_inside_the_span_gives_the_bottom_of_the_circle(self):
        from ogr_slip2d.surface import SlipCircle, lowest_elevation
        c = SlipCircle(centre_x=10.0, centre_y=20.0, radius=5.0)
        c.x_left, c.x_right = 6.0, 14.0
        assert lowest_elevation(c) == 15.0

    def test_centre_outside_the_span_gives_the_nearer_endpoint(self):
        """An arc that does not straddle its own centre is monotone, so
        its lowest point is an END of the chord — never ``yc − R``."""
        from ogr_slip2d.surface import SlipCircle, lowest_elevation
        c = SlipCircle(centre_x=10.0, centre_y=20.0, radius=5.0)
        c.x_left, c.x_right = 12.0, 14.0          # right of the centre
        expected = min(c.base_y_at(12.0), c.base_y_at(14.0))
        got = lowest_elevation(c)
        assert abs(got - expected) < 1e-12
        assert got > 15.0, "the bottom of the circle is not on this arc"

    def test_a_polyline_answers_with_its_lowest_vertex(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipSurface, lowest_elevation
        s = SlipSurface(polyline=Polyline(vertices=[
            Vertex(0.0, 10.0), Vertex(5.0, 3.0), Vertex(9.0, 7.0)],
            closed=False))
        assert lowest_elevation(s) == 3.0

    def test_an_unresolved_circle_falls_back_to_its_full_extent(self):
        """With no endpoints there is no chord to speak of, and the honest
        answer is the lowest point the circle has."""
        from ogr_slip2d.surface import SlipCircle, lowest_elevation
        c = SlipCircle(centre_x=10.0, centre_y=20.0, radius=5.0)
        assert lowest_elevation(c) == 15.0
