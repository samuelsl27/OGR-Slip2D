# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.150 — the Auto Refine search generates what its description
says and refines where its description says. Defect D65.

**The invariants**, one class each:

1. A minimum that falls BETWEEN two consecutive divisions is reachable:
   the refinement has to move the division midpoints towards it, so the
   search's minimum improves with the iterations. Asserted on a synthetic
   factor-of-safety field whose minimum is known exactly.
2. The midpoints the circles are fitted through lie ON the slope surface.
3. The tangent sweep runs from the slope of the joining line to the
   vertical, so every circle generated reaches the solver: generated
   equals analysed.
4. The published critical circle of a reference problem is not lower than
   the search's own minimum by more than the closure criterion (0.5 %).

**What was measured, and why each of these failed before.** Verification
problem 14 (Arai and Tagyo 1985, example 1) is searched with the defaults
10/10/10 at 50 %. The search returned 1.437293 while the published critical
circle solves to 1.408452 with the same method, and the factor DESCENDS
without a break along the straight path between the two circles — so the
returned circle was not a local minimum. The prompt's hypothesis was that
the pair of divisions that would generate the published circle did not
survive the 50 % retention. Instrumenting the run refuted it: that pair was
generated and WON in every one of the ten iterations. What actually
happened:

* the five divisions with the lowest average were {0, 1, 2, 8, 9} — the
  flat ground at both ends — in all ten iterations, and the narrowed
  polyline was the contiguous HULL from the first retained division to
  the last, i.e. the whole slope. The midpoints never moved; the ten
  iterations generated the same 450 circles ten times (class 1);
* a division's midpoint was the midpoint of the chord between its ends,
  which for the division holding the toe was (17.71, 16.00): a metre above
  the ground (class 2);
* the tangent sweep was a fixed band of angles relative to the chord, and
  the three steepest of ten always failed the "centre above both points"
  rule: 4500 generated, 3300 analysed (class 3).

With the midpoints on the slope and the documented sweep, iteration 1
alone gives 1.407564 on problem 14 (class 4). The refinement is measured
in the changelog of v0.1.150 as well, including what it still does NOT do.

**The synthetic field** (class 1) is ``1 + ((x_left - X1)/s)² +
((x_right - X2)/s)²`` over the daylight abscissae of the sliding mass, with
X1 halfway between the first two midpoints of iteration 1 and X2 halfway
between the last two — the shape of problem 14's own minimum, a deep circle
from one end of the slope to the other. The exact minimum is 1.0 and no
circle of iteration 1 can get within ``2·(1/2)² = 0.5`` of it. A method
object that returns that field is all the search sees; ``BaseSearch`` asks
a method for ``METHOD_ID`` and ``compute_fos`` and nothing else.
"""
from __future__ import annotations

import math


# ----------------------------------------------------------------------
def _slope():
    """The v0.1.17 Auto Refine test slope: 12 m high, 10 m of foundation,
    30 m of flat ground before the toe and 10 m after the crest."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe + H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("auto-refine-refinement")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    return p


def _ground(project):
    from ogr_core.geometry import BoundaryType
    from ogr_slip2d.search import PathSearch
    ext = next(b for b in project.boundaries
               if b.btype == BoundaryType.EXTERNAL)
    return PathSearch._ground_profile(ext.polyline.vertices)


def _iteration_one_midpoints(project, divisions):
    """Where iteration 1 puts its midpoints: at half the arc length of each
    of ``divisions`` equal divisions of the ground."""
    from ogr_slip2d.search import AutoRefineSearch
    top = _ground(project)
    L = AutoRefineSearch._arc_length(top)
    return [AutoRefineSearch._point_along(top, L * (k + 0.5) / divisions)
            for k in range(divisions)]


class _Recorder:
    """Records every (p1, p2, theta) the sweep constructs, per iteration."""

    def __init__(self):
        self.rows = []
        self.iteration = -1

    def install(self):
        from ogr_slip2d.search import AutoRefineSearch
        self._cls = AutoRefineSearch
        self._orig = AutoRefineSearch._circle_through_two_points_half_angle
        rec = self

        def wrapped(x1, y1, x2, y2, theta):
            c = rec._orig(x1, y1, x2, y2, theta)
            rec.rows.append((rec.iteration, (x1, y1), (x2, y2), theta, c))
            return c
        AutoRefineSearch._circle_through_two_points_half_angle = staticmethod(
            wrapped)
        return self

    def uninstall(self):
        # Rule 5: the class is module-level state.
        self._cls._circle_through_two_points_half_angle = staticmethod(
            self._orig)

    def progress(self, done, total):
        self.iteration = done

    def midpoints(self, iteration):
        pts = set()
        for it, p1, p2, _t, _c in self.rows:
            if it == iteration:
                pts.add((round(p1[0], 9), round(p1[1], 9)))
                pts.add((round(p2[0], 9), round(p2[1], 9)))
        return sorted(pts)


# ----------------------------------------------------------------------
class _FieldMethod:
    """A method whose factor of safety is a known function of where the
    mass daylights. Not registered (rule 5)."""

    METHOD_ID = "synthetic_field_for_test"
    DISPLAY_NAME = "Synthetic field"

    def __init__(self, x1, x2, scale):
        self.x1, self.x2, self.scale = x1, x2, scale

    def value(self, xl, xr):
        return (1.0 + ((xl - self.x1) / self.scale) ** 2
                + ((xr - self.x2) / self.scale) ** 2)

    def compute_fos(self, project, surface, slices):
        from ogr_slip2d.methods.base import LEMResult
        return LEMResult(
            fos=self.value(slices[0].base_x_left, slices[-1].base_x_right),
            converged=True, iterations=1, method_id=self.METHOD_ID,
            surface=surface, slices=slices)


def _field_search(project, divisions, iterations):
    from ogr_slip2d.search import AutoRefineSearch
    mids = _iteration_one_midpoints(project, divisions)
    x1 = 0.5 * (mids[0][0] + mids[1][0])
    x2 = 0.5 * (mids[-2][0] + mids[-1][0])
    spacing = mids[1][0] - mids[0][0]
    method = _FieldMethod(x1, x2, spacing)
    search = AutoRefineSearch(method=method, divisions=divisions,
                              circles_per_division=6,
                              iterations=iterations, num_slices=20,
                              check_m_alpha=False)
    return search, method, spacing


class TestAMinimumBetweenTwoDivisionsIsReachable:
    """Class 1 — the closure criterion's own test."""

    DIVISIONS = 10

    def test_iteration_one_cannot_reach_it_by_construction(self):
        """The field is built so that no circle of the first iteration
        gets closer than half a division to either abscissa — otherwise
        the next test could pass without refining at all."""
        p = _slope()
        search, method, spacing = _field_search(p, self.DIVISIONS, 1)
        r = search.run(p)
        assert r.critical is not None
        # Both daylight points at least spacing/2 from the optimum: the
        # field there is at least 1 + 2·(1/2)² = 1.5.
        assert r.critical.fos >= 1.5 - 1e-6, r.critical.fos

    def test_the_refinement_moves_the_midpoints_towards_it(self):
        """Six iterations halve the division length six times; the answer
        has to land within a tenth of the ORIGINAL spacing of the optimum
        on both sides (field < 1 + 2·0.1² = 1.02). Before v0.1.150 the
        retained divisions were the two ends, their hull was the whole
        slope, and the sixth iteration repeated the first: 1.5."""
        p = _slope()
        search, method, spacing = _field_search(p, self.DIVISIONS, 6)
        r = search.run(p)
        assert r.critical is not None
        assert r.critical.fos < 1.02, r.critical.fos
        xl = r.critical.slices[0].base_x_left
        xr = r.critical.slices[-1].base_x_right
        assert abs(xl - method.x1) < 0.1 * spacing, (xl, method.x1)
        assert abs(xr - method.x2) < 0.1 * spacing, (xr, method.x2)

    def test_more_iterations_never_do_worse(self):
        """The population is kept, so the minimum is monotone in the
        iteration count — and here it must be STRICTLY better, because a
        refinement that leaves the midpoints where they were is the
        defect (rule 7: a setting that does nothing)."""
        p = _slope()
        one, _m, _s = _field_search(p, self.DIVISIONS, 1)
        three, _m, _s = _field_search(p, self.DIVISIONS, 3)
        f1 = one.run(p).critical.fos
        f3 = three.run(p).critical.fos
        assert f3 < f1 - 0.05, (f1, f3)


# ----------------------------------------------------------------------
class TestTheMidpointsLieOnTheSlope:
    """Class 2 — the circles are fitted through points of the ground."""

    def test_every_midpoint_is_on_the_ground_surface(self):
        """Ten divisions of this ground put the toe vertex INSIDE a
        division (the toe is at arc length 30 of 63.3, the division
        boundaries at multiples of 6.33), and the crest inside another. The
        chord midpoint of such a division is off the ground; the point at
        half its arc length is on it."""
        from ogr_core.geometry import Polyline, envelope_y_at
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p = _slope()
        top = _ground(p)
        span = top[-1].x - top[0].x
        rec = _Recorder().install()
        try:
            AutoRefineSearch(method=BishopSimplified(), divisions=10,
                             circles_per_division=2, iterations=1,
                             num_slices=15, progress_cb=rec.progress).run(p)
        finally:
            rec.uninstall()
        mids = rec.midpoints(0)
        assert len(mids) == 10, mids
        poly = Polyline(vertices=list(top))
        off = [(x, y) for x, y in mids
               if abs(envelope_y_at(poly, x) - y) > 1e-9 * span]
        assert not off, off
        # And the division holding the toe really does straddle it: one
        # midpoint on the flat ground just before it, one on the face.
        assert any(abs(y) < 1e-9 for x, y in mids if x > 24.0), mids

    def test_a_division_straddling_a_vertex_has_its_midpoint_on_the_arc(self):
        """The helper itself, on the toe: arc length 30 is the vertex, so
        the point at 30 is (30, 0) and the point at 33 is 3 m up the
        face — not on the chord across the corner."""
        from ogr_slip2d.search import AutoRefineSearch
        top = _ground(_slope())
        x, y = AutoRefineSearch._point_along(top, 30.0)
        assert abs(x - 30.0) < 1e-9 and abs(y) < 1e-9
        x, y = AutoRefineSearch._point_along(top, 33.0)
        beta = math.radians(30.96)
        assert abs(x - (30.0 + 3.0 * math.cos(beta))) < 1e-9
        assert abs(y - 3.0 * math.sin(beta)) < 1e-9


# ----------------------------------------------------------------------
class TestTheSweepRunsFromTheChordToTheVertical:
    """Class 3 — the documented angular range, and all of it valid."""

    def test_the_construction_keeps_the_centre_above_both_points(self):
        """Half central angle θ (Euclid III.32): at θ → 0 the circle is
        flat, at θ = 90° − chord slope the tangent at the upper point is
        vertical — the centre level with that point — and in between the
        centre is above both points. On a 27° chord that is the whole of
        (0°, 63°)."""
        from ogr_slip2d.search import AutoRefineSearch
        x1, y1 = 10.0, 5.0
        chord_ang = math.radians(27.0)
        x2, y2 = x1 + 40 * math.cos(chord_ang), y1 + 40 * math.sin(chord_ang)
        theta_max = 0.5 * math.pi - chord_ang
        for k in range(1, 100):
            theta = theta_max * k / 100
            c = AutoRefineSearch._circle_through_two_points_half_angle(
                x1, y1, x2, y2, theta)
            assert c is not None, theta
            cx, cy, r = c
            assert abs(math.hypot(cx - x1, cy - y1) - r) < 1e-9 * r
            assert abs(math.hypot(cx - x2, cy - y2) - r) < 1e-9 * r
            assert cy >= max(y1, y2) - 1e-9, (math.degrees(theta), cy)
        cx, cy, r = AutoRefineSearch._circle_through_two_points_half_angle(
            x1, y1, x2, y2, theta_max)
        assert abs(cy - y2) < 1e-9 * r, "vertical tangent at the upper point"
        assert abs(r - 40 / (2 * math.sin(theta_max))) < 1e-9 * r

    def test_the_sweep_is_the_documented_range_in_equal_steps(self):
        """Every pair the run constructs sweeps θ from the offset to
        90° − |chord slope| − offset in equal steps, and the construction
        never fails on any of them."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p = _slope()
        rec = _Recorder().install()
        try:
            AutoRefineSearch(method=BishopSimplified(), divisions=6,
                             circles_per_division=5, iterations=1,
                             num_slices=15, progress_cb=rec.progress).run(p)
        finally:
            rec.uninstall()
        eps = AutoRefineSearch._SWEEP_OFFSET
        by_pair: dict = {}
        for _it, p1, p2, theta, c in rec.rows:
            assert c is not None, (p1, p2, theta)
            by_pair.setdefault((p1, p2), []).append(theta)
        assert len(by_pair) == math.comb(6, 2)
        for (p1, p2), thetas in by_pair.items():
            slope = abs(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
            theta_max = 0.5 * math.pi - slope
            expected = [eps + (theta_max - 2 * eps) * c / 4 for c in range(5)]
            assert len(thetas) == 5
            for got, exp in zip(thetas, expected):
                assert abs(got - exp) < 1e-12, (p1, p2, thetas)

    def test_generated_equals_analysed(self):
        """No focus objects and no vertical chords: every attempt reaches
        the solver. Before v0.1.150 this slope lost the steepest angles of
        every pair to the centre rule; problem 14 lost 1200 of 4500."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p = _slope()
        r = AutoRefineSearch(method=BishopSimplified(), divisions=6,
                             circles_per_division=4, iterations=2,
                             num_slices=15).run(p)
        assert r.attempts == AutoRefineSearch.surfaces_generated(6, 4, 2)
        assert r.total_count == r.attempts, (r.total_count, r.attempts)

    def test_the_retained_divisions_are_shared_by_length(self):
        """Largest-remainder apportionment: the sum is the count asked
        for, every piece gets at least one, and a piece twice as long gets
        about twice the divisions."""
        from ogr_slip2d.search import AutoRefineSearch
        alloc = AutoRefineSearch._allocate_divisions
        assert alloc([21.6, 14.4], 10) == [6, 4]
        assert alloc([10.0], 10) == [10]
        assert sum(alloc([1.0, 1.0, 1.0], 10)) == 10
        assert alloc([100.0, 0.1], 10) == [9, 1]
        assert sum(alloc([5.0, 1.0, 1.0, 1.0, 1.0], 5)) == 5


# ----------------------------------------------------------------------
class TestTheReferenceProblem:
    """Class 4 — verification problem 14, the case that opened D65.

    The model is ``validacion/casos/004-arai-tagyo-1985-ej1`` (the same
    slope, c' = 41.65 kPa, φ' = 15°, γ = 18.82 kN/m³, no water). The
    published critical circle for it is centre (24.499, 50.278), radius
    35.906, and the engine solves it to 1.408452 with Bishop at 30 slices;
    that number is the one D65 says must not move, because it is what
    shows the method is right and the search was not.

    Three iterations rather than the model's ten, on purpose: the first
    iteration already meets the criterion, and the refinement is asserted
    on the synthetic field above where it costs nothing. Cost of this
    class: about 1350 circles, ~15 s.
    """

    PUBLISHED_CENTRE = (24.499, 50.278)
    PUBLISHED_RADIUS = 35.906
    FOS_ON_PUBLISHED_CIRCLE = 1.408452

    @staticmethod
    def _project():
        from pathlib import Path
        from ogr_core.project import Project
        root = Path(__file__).resolve().parent.parent
        return Project.load(root / "validacion" / "casos"
                            / "004-arai-tagyo-1985-ej1" / "modelo.ogr")

    @staticmethod
    def _bishop(project):
        """Through ``build_method``, as the bank's own tool does: it is the
        one place the user's convergence settings are attached, and a bare
        ``BishopSimplified()`` answers 1.408853 here — the same circle,
        0.03 % apart, which is exactly the kind of drift the number
        exists to catch."""
        from ogr_slip2d.analysis_runner import build_method
        return build_method(project, "bishop_simplified", 30)

    def test_the_method_on_the_published_circle_has_not_moved(self):
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = self._project()
        r = GridSearch(method=self._bishop(p), num_slices=30,
                       min_area=0.0).evaluate_circle(
            p, SlipCircle(centre_x=self.PUBLISHED_CENTRE[0],
                          centre_y=self.PUBLISHED_CENTRE[1],
                          radius=self.PUBLISHED_RADIUS))
        assert r is not None and r.is_valid
        err = abs(r.fos - self.FOS_ON_PUBLISHED_CIRCLE) / self.FOS_ON_PUBLISHED_CIRCLE
        assert err < 1e-4, r.fos

    def test_auto_refine_reaches_the_published_circle_to_half_a_percent(self):
        """The closure criterion of D65, verbatim: with 10 divisions, 10
        circles per division and 50 % retained, the search's minimum does
        not exceed the factor on the published circle by more than 0.5 %.
        Measured 1.407564 at v0.1.150 against 1.437293 before."""
        from ogr_slip2d.search import AutoRefineSearch
        p = self._project()
        r = AutoRefineSearch(method=self._bishop(p), divisions=10,
                             circles_per_division=10, iterations=3,
                             next_iter_fraction=0.5, num_slices=30).run(p)
        assert r.critical is not None
        ceiling = self.FOS_ON_PUBLISHED_CIRCLE * 1.005
        assert r.critical.fos <= ceiling, (r.critical.fos, ceiling)
        # And not implausibly lower: the field between the two circles
        # bottoms out near 1.4069, so a search far below would be reporting
        # a surface that is not a mechanism.
        assert r.critical.fos > 1.39, r.critical.fos


# ----------------------------------------------------------------------
def _mirrored_slope():
    """The same slope facing LEFT: crest at x = 0..10, toe at x = 30, flat
    ground to x = 60. Every chord between a crest midpoint and a toe
    midpoint now descends to the right."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe - H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, 0),
        Vertex(toe, 0), Vertex(crest, H), Vertex(0, H),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("auto-refine-refinement-mirrored")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    return p


def _walled_slope():
    """A vertical face: 6 m of wall at x = 30 between the flat ground and
    a bench, then a 2:1 slope. Two midpoints can land on the wall, and
    their chord is vertical: no angular range at all."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, 12.0),
        Vertex(48, 12.0), Vertex(36, 6.0), Vertex(30, 6.0), Vertex(30, 0),
        Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("auto-refine-refinement-wall")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=19,
                            strength=MohrCoulomb(cohesion=15,
                                                 friction_angle=25))]
    return p


class TestTheScenariosTheBankDoesNotCover:
    """The four Auto Refine problems of the bank all face right, have no
    wall and no Slope Limits. These are the cases they cannot vouch for."""

    def test_a_slope_facing_left_refines_the_same_way(self):
        """Mirror image: the search on the mirrored slope must find the
        same factor as on the original, to the solver's tolerance, and
        the mirrored centre. The sweep is written in terms of |chord
        slope| for exactly this reason."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        kw = dict(divisions=8, circles_per_division=6, iterations=4,
                  num_slices=20)
        right = AutoRefineSearch(method=BishopSimplified(), **kw).run(_slope())
        left = AutoRefineSearch(method=BishopSimplified(),
                                **kw).run(_mirrored_slope())
        assert right.critical is not None and left.critical is not None
        assert right.total_count == left.total_count == right.attempts
        rel = abs(left.critical.fos - right.critical.fos) / right.critical.fos
        assert rel < 2e-3, (right.critical.fos, left.critical.fos)
        rs, ls = right.critical.surface, left.critical.surface
        assert abs((60.0 - rs.centre_x) - ls.centre_x) < 0.5, (rs, ls)
        assert abs(rs.centre_y - ls.centre_y) < 0.5, (rs, ls)

    def test_the_synthetic_field_is_reached_on_the_mirrored_slope(self):
        """The refinement itself, mirrored: the minimum at both ends of a
        left-facing slope is found to the same tolerance."""
        p = _mirrored_slope()
        search, method, spacing = _field_search(p, 10, 6)
        r = search.run(p)
        assert r.critical is not None
        assert r.critical.fos < 1.02, r.critical.fos

    def test_a_minimum_in_the_middle_of_the_slope_is_refined_too(self):
        """A frictional soil (c' = 0.5 kPa, φ' = 35°) fails in a shallow
        face circle, so the minimum sits in the MIDDLE divisions, where the
        old hull-of-the-retained rule happened to work. The new rule must
        not lose that case: the refined answer improves on the first
        iteration and stays a face mechanism."""
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p = _slope()
        p.materials = [Material(name="S", unit_weight=18,
                                strength=MohrCoulomb(cohesion=0.5,
                                                     friction_angle=35))]
        one = AutoRefineSearch(method=BishopSimplified(), divisions=8,
                               circles_per_division=6, iterations=1,
                               num_slices=20).run(p)
        five = AutoRefineSearch(method=BishopSimplified(), divisions=8,
                                circles_per_division=6, iterations=5,
                                num_slices=20).run(p)
        assert one.critical is not None and five.critical is not None
        assert five.critical.fos < one.critical.fos, (one.critical.fos,
                                                     five.critical.fos)
        # A face circle on a 31° slope in φ' = 35° soil: tan35/tan31 ≈ 1.17
        # is the infinite-slope factor it converges towards from above.
        assert 1.05 < five.critical.fos < 1.5, five.critical.fos
        xl = five.critical.slices[0].base_x_left
        assert xl > 25.0, "a face mechanism daylights on or near the face"

    def test_slope_limits_confine_the_midpoints_and_the_refinement(self):
        """With the Slope Limits at (20, 55) no midpoint of any iteration
        falls outside them, and the answer daylights inside them."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p = _slope()
        rec = _Recorder().install()
        try:
            r = AutoRefineSearch(method=BishopSimplified(), divisions=8,
                                 circles_per_division=5, iterations=4,
                                 num_slices=20, slope_limits=(20.0, 55.0),
                                 progress_cb=rec.progress).run(p)
        finally:
            rec.uninstall()
        assert r.critical is not None
        for it in range(4):
            mids = rec.midpoints(it)
            assert mids, it
            assert all(20.0 - 1e-9 <= x <= 55.0 + 1e-9 for x, _y in mids), (
                it, mids)
        assert r.critical.slices[0].base_x_left >= 20.0 - 1e-6
        assert r.critical.slices[-1].base_x_right <= 55.0 + 1e-6

    def test_a_vertical_face_is_survived_and_counted(self):
        """Midpoints can land on the wall; a pair of them has a vertical
        chord and no angular range between "flat" and "vertical". Those
        attempts are counted (the published number is what was
        ATTEMPTED), every circle that IS constructed is a real one, and
        the search still returns a mechanism."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import AutoRefineSearch
        p = _walled_slope()
        rec = _Recorder().install()
        try:
            r = AutoRefineSearch(method=BishopSimplified(), divisions=12,
                                 circles_per_division=4, iterations=3,
                                 num_slices=20,
                                 progress_cb=rec.progress).run(p)
        finally:
            rec.uninstall()
        assert r.attempts == AutoRefineSearch.surfaces_generated(12, 4, 3)
        assert r.total_count <= r.attempts
        assert r.critical is not None and r.critical.fos > 0.5
        on_wall = [m for m in rec.midpoints(0) if abs(m[0] - 30.0) < 1e-9
                   and 0.0 < m[1] < 6.0]
        assert on_wall, rec.midpoints(0)
        assert all(c is not None for *_rest, c in rec.rows)

    def test_the_yield_acceleration_objective_is_what_gets_refined(self):
        """The retention ranks by ``score``, the scalar every search
        minimises, so with Compute ky on it refines towards the lowest
        yield acceleration and the critical surface is the population's
        minimum of THAT objective — not of the factor of safety."""
        from ogr_core.project.settings import SeismicAnalysisSettings
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import (AutoRefineSearch, OBJECTIVE_KY,
                                       surface_score)
        p = _slope()
        settings = SeismicAnalysisSettings(compute_ky=True)
        r = AutoRefineSearch(method=BishopSimplified(), divisions=6,
                             circles_per_division=4, iterations=3,
                             num_slices=15, seismic_analysis=settings).run(p)
        assert r.objective == OBJECTIVE_KY
        assert r.critical is not None
        valid = [e for e in r.evaluations if e.is_valid]
        best = min(surface_score(e, OBJECTIVE_KY) for e in valid)
        assert abs(surface_score(r.critical, OBJECTIVE_KY) - best) < 1e-12
        # And the objective is a different ordering from the factor: the
        # lowest-ky surface is not (necessarily) the lowest-FoS one.
        assert r.critical.fos >= min(e.fos for e in valid) - 1e-12
