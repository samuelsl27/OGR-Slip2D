# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.118 — a non-circular search may not find LESS than a
circular one on the same model.

**The invariant**, and it is an inequality rather than a value on purpose:
the space of circles is contained in the space of polylines, so whatever a
grid search finds, a path or block search has to be able to reach. When it
cannot, the number the user is shown is too HIGH — a mechanism that exists
and was not reported. Defect D21 / anomaly A19-1.

The comparison is not made against the arc, because that would fail for a
reason that is not a defect: **a polyline of n chords inscribed in an arc
is not the arc**, and it always reads higher. Measured on the four-layer
benchmark of Greco (1996) example 4, the same critical circle gives 1.4332
as an arc, 1.4387 in sixteen chords and 1.4470 in eight. So the tolerance
is not a constant written here by whoever wrote the test: each test below
DISCRETISES the winning circle to the same number of chords the search
itself produced, evaluates that polyline with the same method, and
compares against it. If the method changes, the reference moves with it.

Two things this file protects, both of which were real:

* the segment length must come from the height of the SLOPE. It used to
  come from the relief of the MODEL, so burying the same slope under more
  foundation chopped its slip surfaces more coarsely — 30 m segments and
  eight vertices for a 150 m mass on the benchmark above;
* the Block Search must not reject its way out of a search. Each block
  point draws its y independently, and two undocumented filters demanded
  the result be unimodal, which N independent draws satisfy with
  probability 2^(N-1)/N!. Asking for more groups therefore bought
  rejection rather than freedom: 1852, 1364, 635 and 222 surfaces
  surviving out of 3000 for 2..5 groups on that benchmark, against the
  predicted 1, 0.67, 0.33, 0.13.

Note what is NOT asserted, because it was measured and is false: that a
Block Search with more groups finds a lower minimum. Once the filters are
gone the minimum still rises with the count, and that is what an unguided
random search does — the same budget over one more free vertex samples a
bigger space more thinly. The reference sidesteps it by requiring the user
to place the search objects. See
``TestBlockSearchDoesNotRejectItsWayOut.test_the_number_of_groups_moves_the_number``.
"""
from __future__ import annotations
import math


# ----------------------------------------------------------------------
def _layered_slope(name: str = "d21", base: float = -20.0):
    """A four-layer slope with deep foundation under the toe.

    Scaled after Greco (1996) example 4 — the model that exposed D21 — and
    kept small so the searches below stay cheap. What matters for the test
    is the SHAPE of the problem: two of the four layers have no cohesion,
    so the critical surface has to dive into them, and the External
    Boundary reaches well below the toe, so the relief of the model
    (60 m here) is twice the height of the slope (30 m).

    ``base`` is how far below the toe the model goes. It is a parameter
    because burying the same slope deeper must not change how the slip
    surfaces are chopped up — see ``TestSegmentLengthIsTheSlopeHeight``.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project(name)
    ext = Polyline(vertices=[
        Vertex(0, base), Vertex(130, base), Vertex(130, 10),
        Vertex(85, 40), Vertex(60, 40), Vertex(25, 10), Vertex(0, 10),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    for y in (10.0, 5.0, -5.0):
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(0, y), Vertex(130, y)], closed=False),
            btype=BoundaryType.MATERIAL))

    sup = Material(name="Upper", unit_weight=20.38,
                   strength=MohrCoulomb(cohesion=49.0, friction_angle=29.0))
    l2 = Material(name="L2", unit_weight=17.64,
                  strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0))
    l3 = Material(name="L3", unit_weight=20.38,
                  strength=MohrCoulomb(cohesion=7.84, friction_angle=20.0))
    inf = Material(name="Bottom", unit_weight=17.64,
                   strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0))
    p.materials = [sup, l2, l3, inf]
    p.resolve_regions()
    p.assign_material_at(70.0, 25.0, sup.id)
    p.assign_material_at(65.0, 7.5, l2.id)
    p.assign_material_at(65.0, 0.0, l3.id)
    p.assign_material_at(65.0, base / 2.0, inf.id)

    p.settings.methods.num_slices = 15
    p.settings.statistics.seed = 20260825
    return p


def _method():
    from ogr_slip2d import BishopSimplified
    return BishopSimplified()


def _grid_minimum(project):
    """The circular minimum, and the circle that produced it."""
    from ogr_slip2d.search import GridSearch

    g = GridSearch(method=_method(), num_slices=15,
                   grid_nx=8, grid_ny=8, radius_increment=6)
    r = g.run(project)
    assert r.critical is not None, "the grid found nothing"
    return r.critical


def _chord_reference(project, circle, n_chords: int) -> float:
    """The winning circle, redrawn as ``n_chords`` straight segments.

    This is the honest thing for a polyline search to be measured against,
    and it is computed rather than declared: the discretisation penalty
    belongs to the geometry and the method, not to a tolerance someone
    picked.
    """
    from ogr_core.geometry import (BoundaryType, Polyline, Vertex,
                                   ground_surface, envelope_y_at)
    from ogr_slip2d.search import PathSearch
    from ogr_slip2d.surface import SlipSurface

    ext = [b for b in project.boundaries
           if b.btype == BoundaryType.EXTERNAL][0]
    top = ground_surface(list(ext.polyline.vertices))
    cx, cy, R = circle.centre_x, circle.centre_y, circle.radius

    def arc_y(x):
        d = R * R - (x - cx) ** 2
        return None if d < 0.0 else cy - math.sqrt(d)

    def diff(x):
        a, g = arc_y(x), envelope_y_at(top, x)
        return None if a is None or g is None else a - g

    # Where the arc daylights: the outermost sign changes of arc - ground.
    xs = [cx - R + (2.0 * R) * i / 2000.0 for i in range(2001)]
    roots, prev = [], None
    for x in xs:
        v = diff(x)
        if prev is not None and v is not None and prev[1] is not None \
                and (prev[1] < 0.0) != (v < 0.0):
            a, b = prev[0], x
            for _ in range(60):
                m = 0.5 * (a + b)
                if (diff(a) < 0.0) == (diff(m) < 0.0):
                    a = m
                else:
                    b = m
            roots.append(0.5 * (a + b))
        prev = (x, v)
    assert len(roots) >= 2, "the winning circle does not daylight twice"
    x0, x1 = roots[0], roots[-1]

    pts = []
    for i in range(n_chords + 1):
        x = x0 + (x1 - x0) * i / n_chords
        y = envelope_y_at(top, x) if i in (0, n_chords) else arc_y(x)
        pts.append(Vertex(x, y))
    probe = PathSearch(method=_method(), num_slices=15, num_surfaces=1)
    res = probe.evaluate_surface(
        project, SlipSurface(polyline=Polyline(vertices=pts, closed=False)))
    assert res is not None and res.is_valid, \
        "the discretised circle could not be analysed"
    return res.fos


# ----------------------------------------------------------------------
class TestSegmentLengthIsTheSlopeHeight:
    """The documented recommendation is 0.3H with H the height of the
    SLOPE. ``y_max - y_min`` over the External Boundary is the relief of
    the MODEL, and it counts every metre of foundation under the toe as if
    it were slope."""

    @staticmethod
    def _longest_segment(project) -> float:
        from ogr_slip2d.search import PathSearch
        s = PathSearch(method=_method(), num_slices=15, num_surfaces=40,
                       seed=7)
        r = s.run(project)
        assert r.critical is not None
        v = r.critical.surface.polyline.vertices
        # Every segment but the last is exactly ``segment_length``; the
        # last one is cut short where the surface meets the ground.
        return max(math.hypot(v[i + 1].x - v[i].x, v[i + 1].y - v[i].y)
                   for i in range(len(v) - 1))

    def test_matches_three_tenths_of_the_slope_height(self):
        p = _layered_slope(base=-20.0)
        # Ground runs from y = 10 at the toe bench to y = 40 at the crest.
        assert abs(self._longest_segment(p) - 0.3 * 30.0) < 1e-6

    def test_foundation_depth_does_not_change_it(self):
        """Burying the same slope deeper must not chop it more coarsely.

        This is the defect in one line: with the model's relief standing
        in for the slope's, the two models below asked for segments of
        13.5 m and 18 m for the same 30 m slope.
        """
        shallow = self._longest_segment(_layered_slope(base=-5.0))
        deep = self._longest_segment(_layered_slope(base=-20.0))
        assert abs(shallow - deep) < 1e-6, (shallow, deep)


class TestPathSearchReachesTheCircularMinimum:
    def test_path_minimum_is_not_above_the_discretised_circle(self):
        from ogr_slip2d.search import PathSearch

        p = _layered_slope()
        circular = _grid_minimum(p)
        s = PathSearch(method=_method(), num_slices=15, num_surfaces=600,
                       seed=11)
        r = s.run(p)
        assert r.critical is not None, "the path search found nothing"
        n = len(r.critical.surface.polyline.vertices) - 1
        ref = _chord_reference(p, circular.surface, n)
        assert r.min_fos <= ref + 1e-9, (
            "path %.6f > same circle in %d chords %.6f (arc %.6f)"
            % (r.min_fos, n, ref, circular.fos))

    def test_the_declared_number_of_surfaces_is_the_valid_one(self):
        """The count the user sets is the number of VALID surfaces;
        invalid ones are discarded and are not part of it. ``attempts``
        publishes what it really cost."""
        from ogr_slip2d.search import PathSearch

        p = _layered_slope()
        s = PathSearch(method=_method(), num_slices=15, num_surfaces=120,
                       seed=3)
        r = s.run(p)
        assert r.valid_count == 120, r.valid_count
        assert r.attempts >= r.valid_count


class TestBlockSearchDoesNotRejectItsWayOut:
    @staticmethod
    def _block(project, groups: int, wide_angles: bool = False,
               num_surfaces: int = 500):
        from ogr_slip2d.optimize import OptimizeSettings
        from ogr_slip2d.search import BlockSearch

        kw = {}
        if wide_angles:
            # The window the reference itself gives as the allowable range
            # for a typical Block Search, and Optimize Surfaces with it:
            # the two together are how the manual describes solving this
            # kind of problem, and neither alone gets there.
            kw = dict(left_start_angle_deg=95.0, left_end_angle_deg=175.0,
                      right_start_angle_deg=5.0, right_end_angle_deg=85.0)
        s = BlockSearch(method=_method(), num_slices=15, num_groups=groups,
                        num_surfaces=num_surfaces, seed=5, **kw)
        if wide_angles:
            s.optimize = OptimizeSettings(enabled=True)
            s.optimize_seed = 13
        return s.run(project)

    def test_the_yield_does_not_collapse_with_more_groups(self):
        """The threshold is the DISCARDED FILTER'S OWN LAW, not a number
        someone liked.

        Some fall-off with the count is legitimate and geometric: every
        block point must land inside the External Boundary, so N of them
        survive with probability p^N. What is not legitimate is
        FACTORIAL fall-off, and that is the signature the unimodal filter
        left: N independently drawn depths come out unimodal with
        probability 2^(N-1)/N!, which is 1 at N = 2 and 0.133 at N = 5.

        So the test asks for twice what that filter alone would have left.
        Measured on the four-layer benchmark, 3000 candidates: before,
        0.617 and 0.074 (fails — 0.074 < 0.164); after, 0.401 and 0.195
        (passes, with the bound at 0.107).
        """
        p = _layered_slope()
        two = self._block(p, 2)
        five = self._block(p, 5)
        assert two.total_count > 0 and five.total_count > 0
        r2 = two.valid_count / two.total_count
        r5 = five.valid_count / five.total_count
        unimodal_law = 2 ** (5 - 1) / math.factorial(5)
        assert r5 >= 2.0 * r2 * unimodal_law, (r2, r5, unimodal_law)

    def test_it_reaches_the_circular_minimum_when_configured_to(self):
        """The inequality holds for a Block Search too — but only with the
        two things the reference itself provides for it.

        With Start Angle = End Angle, which is the default the reference
        SHIPS (135 for the left, 45 for the right), both end chords are
        pinned at 45 degrees. The critical circle of the grid on the
        benchmark daylights at 27.7 and 68.4 degrees, so that family
        cannot contain it and demanding it would be demanding something
        the documented method does not do. Opened to the window the
        reference gives as allowable — 95..175 and 5..85 — the 152.3 and
        68.4 that are needed both fit, and with Optimize Surfaces, which
        is what the manual states it used for this very problem ("Random
        search with Monte-Carlo optimization"), the minimum lands below
        the circular one: 1.4073 against 1.4332 on the benchmark.
        """
        from ogr_slip2d.optimize import OptimizeSettings

        p = _layered_slope()
        circular = _grid_minimum(p)
        s = self._block(p, 2, wide_angles=True, num_surfaces=300)
        assert s.critical is not None
        n = len(s.critical.surface.polyline.vertices) - 1
        ref = _chord_reference(p, circular.surface, n)
        assert s.min_fos <= ref + 1e-9, (
            "block %.6f > same circle in %d chords %.6f (arc %.6f)"
            % (s.min_fos, n, ref, circular.fos))

    def test_the_number_of_groups_moves_the_number(self):
        """Rule 7 — and NOT "more groups finds a lower minimum", which was
        measured and is false.

        The anomaly this file closes read the rise as a defect: 2, 3 and 4
        groups gave 1.467, 1.542 and 1.564, "when more groups should give
        more freedom and therefore a minimum less than or equal". Half of
        that was a defect — the filters that made the yield collapse — and
        half of it is not. The other half is what an unguided random
        search does: the same budget of candidates spread over one more
        free vertex is a thinner sampling of a bigger space, so the best
        of them is worse. Measured here after the filters were removed:
        1.298 at two groups against 1.367 at four, with the surviving
        fraction healthy in both.

        That is why the reference REQUIRES the user to place the Block
        Search objects, and why it is a real limitation to state rather
        than a bug to assert away. What is testable is that the control
        does something at all.
        """
        p = _layered_slope()
        two = self._block(p, 2)
        four = self._block(p, 4)
        assert two.critical is not None and four.critical is not None
        assert abs(four.min_fos - two.min_fos) > 1e-9
        assert len(four.critical.surface.polyline.vertices) >             len(two.critical.surface.polyline.vertices)


class TestSlopeLimitsAreHonoured:
    """Rule 7. The Slope Limits always filter, whatever the search, and
    they steer the Path Search's initiation range. Until v0.1.118 the Path
    Search had no such argument at all and the Block Search was never
    handed one."""

    def test_narrowing_them_moves_the_path_search(self):
        from ogr_slip2d.search import PathSearch

        p = _layered_slope()
        kw = dict(method=_method(), num_slices=15, num_surfaces=300, seed=9)
        wide = PathSearch(**kw).run(p)
        narrow = PathSearch(slope_limits=(30.0, 80.0), **kw).run(p)
        assert wide.critical is not None and narrow.critical is not None
        assert abs(narrow.min_fos - wide.min_fos) > 1e-9
        for v in narrow.critical.surface.polyline.vertices:
            assert 30.0 - 1e-6 <= v.x <= 80.0 + 1e-6, v.x

    def test_they_filter_the_block_search_too(self):
        """The reference exempts the Block Search from GENERATING with the
        limits — its vertices come from the search objects — and exempts
        nothing from being FILTERED by them. It was never handed a value
        to filter on.

        The limits here are wider than the Path Search's above, and that
        is the geometry talking: a block surface leaves its outermost
        vertex at the projection angle, so both ends daylight well outside
        the span the vertices occupy. Narrowed to (30, 80) this model
        returns NO surface at all — correct, and useless as a measurement.
        """
        from ogr_slip2d.search import BlockSearch

        p = _layered_slope()
        kw = dict(method=_method(), num_slices=15, num_groups=3,
                  num_surfaces=400, seed=9)
        wide = BlockSearch(**kw).run(p)
        narrow = BlockSearch(slope_limits=(15.0, 100.0), **kw).run(p)
        assert wide.critical is not None and narrow.critical is not None
        assert abs(narrow.min_fos - wide.min_fos) > 1e-9
        assert narrow.valid_count < wide.valid_count
        v = narrow.critical.surface.polyline.vertices
        assert 15.0 - 1e-6 <= v[0].x and v[-1].x <= 100.0 + 1e-6

    def test_build_search_hands_them_to_every_search(self):
        """The settings page writes one pair of limits; the seven branches
        of ``build_search`` are where one of them gets forgotten, and five
        of them had been.

        v0.1.129 — it said six and walked six. ``particle_swarm`` arrived
        in v0.1.126 with its own branch and was never added here, so for
        three versions the test that exists to catch a forgotten branch had
        forgotten one.
        """
        from ogr_slip2d.analysis_runner import build_search

        p = _layered_slope()
        p.settings.search.slope_limit_left = 30.0
        p.settings.search.slope_limit_right = 80.0
        for m in ("grid", "slope", "auto_refine", "block", "path",
                  "simulated_annealing", "particle_swarm"):
            p.settings.search.search_method = m
            s = build_search(p, "bishop_simplified")
            assert s.slope_limits == (30.0, 80.0), m
