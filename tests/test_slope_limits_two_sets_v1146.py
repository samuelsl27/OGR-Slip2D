# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.146 — the Slope Limits may describe TWO windows.

**The invariant**: the windows are a FILTER on where a surface daylights,
and the filter is membership — each end must land in one of the windows,
not merely between the outermost two. The span between two windows
contains the gap, and excluding the gap is the only reason to declare two
windows instead of one wide one. Defect D50.

What this protects, and it is rule 7 rather than a value: before v0.1.146
``SearchSettings`` held one pair of limits, so a model whose statement
restricts daylighting to a toe window and a crest window could only say
the union of the two — which, on the reference bank's problem for exactly
this, filtered nothing at all. The search settled on a shallow slice of a
zero-strength layer that daylighted inside the gap, 73 % below the
published factor, and every setting in the file was correct.

**These tests do not validate a factor of safety.** The external reference
for that is the published search table of the bank problem, and that
comparison lives in the bank, not here. What is asserted here is that the
setting reaches all seven search branches, that it moves the number, and
that a model which does not declare a second window means exactly what it
meant before the field existed.

One thing that was measured and is NOT asserted, because it is false: that
the bank problem discriminates between membership and the stricter reading
in which one end must be in the toe window and the other in the crest
window. On that model the two give the identical critical circle and the
identical 1546 valid surfaces, so nothing published chooses between them.
The reference states its own rule outright — with two sets it "still
searches each set of limits independently, as well as between the two" —
and that is the rule implemented. The alternative is recorded here so that
nobody re-derives it from the agreement of a case that cannot tell.
"""
from __future__ import annotations


# ======================================================================
def _weak_crust_slope(name: str = "d50"):
    """A slope whose free minimum is a shallow skin in mid-face.

    The shape is after the bank problem that exposed D50: a cohesionless
    upper layer over a firm one, so the lowest factor belongs to a thin
    slice that daylights halfway up the face rather than to the deep
    mechanism the statement is about. That is what makes the gap between
    two windows observable — with a single span covering both windows the
    skin is admissible, and it wins.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project(name)
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(200, -10), Vertex(200, 60),
        Vertex(140, 60), Vertex(60, 20), Vertex(0, 20)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, 14), Vertex(200, 14)], closed=False),
        btype=BoundaryType.MATERIAL))

    weak = Material(name="Weak", unit_weight=19.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=12.0))
    firm = Material(name="Firm", unit_weight=20.0,
                    strength=MohrCoulomb(cohesion=60.0, friction_angle=30.0))
    p.materials = [weak, firm]
    p.resolve_regions()
    p.assign_material_at(100.0, 30.0, weak.id)
    p.assign_material_at(100.0, 0.0, firm.id)
    p.settings.methods.num_slices = 15
    p.settings.statistics.seed = 20260902
    return p


def _method():
    from ogr_slip2d import BishopSimplified
    return BishopSimplified()


# The toe window, the crest window, and the span that contains both. The
# free minimum of the model above daylights at x = 73.9 .. 81.9, which is
# inside SPAN and inside NEITHER window: that is the whole measurement.
TOE = (20.0, 60.0)
CREST = (150.0, 190.0)
SPAN = (20.0, 190.0)


def _grid(project, limits):
    from ogr_slip2d.search import GridSearch
    return GridSearch(method=_method(), num_slices=15,
                      slope_limits=limits, seed=7).run(project)


# ======================================================================
class TestTheSecondWindowMovesTheNumber:
    """Rule 7, and the closure criterion of D50.

    A control that does not change the result is worse than no control at
    all, because the user believes the analysis honours it. Two windows
    have to differ from the single span that covers them — otherwise the
    field is decoration.
    """

    def test_two_windows_reject_what_the_span_accepts(self):
        span = _grid(_weak_crust_slope(), SPAN)
        two = _grid(_weak_crust_slope(), (TOE, CREST))
        assert span.critical is not None
        assert two.critical is not None

        # Measured on this model: 0.425782 against 0.557293, +30.9 %. The
        # assertion is deliberately far looser than the measurement, so it
        # states the SIGN and the order of magnitude rather than freezing
        # a number a solver change would have to come back and edit.
        assert two.critical.fos > span.critical.fos * 1.10, (
            span.critical.fos, two.critical.fos)
        assert two.valid_count < span.valid_count

    def test_the_span_minimum_is_the_one_in_the_gap(self):
        """Why the number moves, not just that it does.

        If the span's minimum did NOT daylight in the gap, the test above
        would be measuring something else — a coincidence of the search,
        or a filter unrelated to the windows.
        """
        c = _grid(_weak_crust_slope(), SPAN).critical
        assert c is not None
        for x in (c.surface.x_left, c.surface.x_right):
            assert TOE[1] < x < CREST[0], x

    def test_the_two_window_minimum_daylights_in_the_windows(self):
        c = _grid(_weak_crust_slope(), (TOE, CREST)).critical
        assert c is not None
        for x in (c.surface.x_left, c.surface.x_right):
            assert (TOE[0] - 1e-6 <= x <= TOE[1] + 1e-6
                    or CREST[0] - 1e-6 <= x <= CREST[1] + 1e-6), x


# ======================================================================
class TestOneWindowMeansWhatItAlwaysMeant:
    """Criterion 1: a model that does not declare the second set must be
    read exactly as it was before the field existed."""

    def test_a_bare_pair_is_still_a_bare_pair(self):
        from ogr_slip2d.search import _normalise_slope_limits

        assert _normalise_slope_limits((30.0, 80.0)) == ((30.0, 80.0),)
        assert _normalise_slope_limits((80.0, 30.0)) == ((30.0, 80.0),)
        assert _normalise_slope_limits(None) is None

    def test_the_hull_of_one_window_is_that_window(self):
        from ogr_slip2d.search import GridSearch

        s = GridSearch(method=_method(), slope_limits=(30.0, 80.0))
        assert s.slope_limits == (30.0, 80.0)
        assert s.slope_limit_sets == ((30.0, 80.0),)

    def test_membership_reduces_to_the_interval(self):
        from ogr_slip2d.search import _within_slope_limits

        one = ((30.0, 80.0),)
        for x in (30.0, 55.0, 80.0):
            assert _within_slope_limits(x, one, 1e-9)
        for x in (29.0, 81.0):
            assert not _within_slope_limits(x, one, 1e-9)

    def test_the_gap_is_excluded_and_the_hull_is_not(self):
        from ogr_slip2d.search import _slope_limits_hull, _within_slope_limits

        two = (TOE, CREST)
        assert _slope_limits_hull(two) == (TOE[0], CREST[1])
        # 100 is inside the hull and inside neither window. If this ever
        # passes, the filter has quietly become the span again.
        assert not _within_slope_limits(100.0, two, 1e-9)
        assert _within_slope_limits(55.0, two, 1e-9)
        assert _within_slope_limits(160.0, two, 1e-9)

    def test_settings_default_to_no_second_window(self):
        from ogr_core.project.settings import SearchSettings

        s = SearchSettings()
        assert s.slope_limit_left_2 is None
        assert s.slope_limit_right_2 is None

    def test_round_trip_through_the_project_file(self, tmp_path):
        from ogr_core.project import Project

        p = _weak_crust_slope()
        p.settings.search.slope_limit_left = TOE[0]
        p.settings.search.slope_limit_right = TOE[1]
        p.settings.search.slope_limit_left_2 = CREST[0]
        p.settings.search.slope_limit_right_2 = CREST[1]
        path = tmp_path / "two_sets.ogr"
        p.save(str(path))
        back = Project.load(str(path)).settings.search
        assert (back.slope_limit_left, back.slope_limit_right) == TOE
        assert (back.slope_limit_left_2, back.slope_limit_right_2) == CREST


# ======================================================================
class TestEverySearchReceivesBothWindows:
    """Criterion 2. The filter lives once, in ``_best_of_masses``, so what
    has to be proven per branch is that the value ARRIVES — which is the
    failure D21 found, with five of six branches never handed one."""

    def test_build_search_hands_both_windows_to_every_branch(self):
        from ogr_slip2d.analysis_runner import build_search

        p = _weak_crust_slope()
        p.settings.search.slope_limit_left = TOE[0]
        p.settings.search.slope_limit_right = TOE[1]
        p.settings.search.slope_limit_left_2 = CREST[0]
        p.settings.search.slope_limit_right_2 = CREST[1]
        for m in ("grid", "slope", "auto_refine", "block", "path",
                  "simulated_annealing", "particle_swarm"):
            p.settings.search.search_method = m
            s = build_search(p, "bishop_simplified")
            assert s.slope_limit_sets == (TOE, CREST), m
            # And the hull, which is what GENERATION reads, still spans.
            assert s.slope_limits == (TOE[0], CREST[1]), m

    def test_an_orphan_second_window_is_dropped_not_promoted(self):
        """The second set is defined on top of the first, never instead of
        it. Promoting an orphan would silently move a Path Search's
        initiation range to the wrong end of the slope."""
        from ogr_slip2d.analysis_runner import _slope_limits

        p = _weak_crust_slope()
        s = p.settings.search
        s.slope_limit_left_2, s.slope_limit_right_2 = CREST
        assert _slope_limits(s) is None

        s.slope_limit_left, s.slope_limit_right = TOE
        s.slope_limit_right_2 = None          # half a window is no window
        assert _slope_limits(s) == (TOE,)

    def test_a_dropped_window_is_announced(self):
        """Rule 7 again: a value the file carries and the analysis ignores
        has to be said out loud."""
        from ogr_slip2d.analysis_runner import settings_warnings

        p = _weak_crust_slope()
        s = p.settings.search
        s.slope_limit_left, s.slope_limit_right = TOE
        s.slope_limit_left_2 = CREST[0]        # and no right half
        notes = " ".join(settings_warnings(p))
        assert "second set of Slope Limits" in notes


# ======================================================================
class TestPathSearchStartsInTheToeWindow:
    """The one place where two windows change GENERATION rather than
    filtering.

    The reference states the rule in two halves: with a SINGLE set the
    range is divided in half and the half nearest the toe is used; with a
    DOUBLE set the set nearest the toe is used. Only the first half was
    reachable before D50, and it is what v0.1.118 implemented.
    """

    def test_start_points_land_in_the_toe_window(self):
        from ogr_slip2d.search import PathSearch

        p = _weak_crust_slope()
        r = PathSearch(method=_method(), num_slices=15, num_surfaces=200,
                       slope_limits=(TOE, CREST), seed=11).run(p)
        assert r.critical is not None
        verts = r.critical.surface.polyline.vertices
        start = min(verts[0].x, verts[-1].x)
        assert TOE[0] - 1e-6 <= start <= TOE[1] + 1e-6, start

    def test_a_single_window_still_halves_it(self):
        """The v0.1.118 behaviour has to survive: with one window the
        initiation range is its toe-side HALF, so a start point beyond the
        midpoint would mean the double-set branch had swallowed both."""
        from ogr_slip2d.search import PathSearch

        p = _weak_crust_slope()
        r = PathSearch(method=_method(), num_slices=15, num_surfaces=200,
                       slope_limits=SPAN, seed=11).run(p)
        assert r.critical is not None
        verts = r.critical.surface.polyline.vertices
        start = min(verts[0].x, verts[-1].x)
        assert start <= 0.5 * (SPAN[0] + SPAN[1]) + 1e-6, start
