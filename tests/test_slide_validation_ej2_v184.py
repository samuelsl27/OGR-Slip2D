# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Numerical validation against the Slide reference run Slide2d_Ej_2_General.

WHAT INVARIANT THIS PROTECTS, and why it needed a second benchmark.

Ej_1 already validates the seven methods against a published run, and it
passed throughout the whole life of two bugs that made this model come out
31 % low. Ej_1 could not see them because its external boundary happens to
have no vertex on the bottom edge whose x is unshared by a top vertex, and
because its critical circle happens to define only one sliding mass. Ej_2
has both, so it is the case that pins them down:

1. THE GROUND SURFACE IS THE UPPER ENVELOPE OF THE EXTERNAL BOUNDARY,
   computed over its EDGES. This model's bottom edge carries a vertex at
   (0, 0). Deriving the ground surface from vertices alone published that
   point as terrain and cut a 30 m ravine into flat ground, so the search
   reported a critical circle of FoS = 0.79 that daylighted on the floor
   of the model instead of on the slope.

2. A CIRCLE THAT CROSSES THE GROUND MORE THAN TWICE DEFINES SEVERAL
   SLIDING MASSES, AND THE CRITICAL ONE IS THE ONE ANALYSED. The
   reference's own critical circle crosses this profile four times. Taking
   the leftmost mass picks a 62 m² lens of level ground beyond the toe
   whose driving moment is ~0 — no factor of safety at all — and throws
   the real 184 m² slope failure away as invalid.

3. A SURFACE THAT LEAVES THE SOIL REGION IS NOT ANALYSED. Documented under
   Grid Search ("if a circular surface extends past the lower limits of
   the External Boundary, the surface is discarded") and counted in the
   reference report as error code -103, for 287 of these 4840 surfaces.

Reference (Global Minimums, Slide2d_Ej_2_General.htm). Two distinct
critical circles serve all seven methods:

  BIG   centre (-3.333, 87.632) R = 60.257, endpoints x = 15.342, 47.323
        total slice area 184.457 m2
        bishop 1.155640 | janbu corrected 1.149240 | spencer 1.156640
        lowe-karafiath 1.163100 | GLE/Morgenstern-Price 1.157850
  SMALL centre (12.381, 61.316) R = 30.408, endpoints x = 16.141, 42.126
        total slice area 160.250 m2
        ordinary/fellenius 1.114420 | janbu simplified 1.084930

Grid Search, 25 slices, Radius Increment 10, Composite Surfaces disabled,
tension crack for reverse curvature enabled, no groundwater.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

# Reference critical circles: (centre_x, centre_y, radius)
BIG = (-3.333333, 87.631579, 60.25674)
SMALL = (12.380952, 61.315789, 30.40817)

# Reference factor of safety per method, and which circle carries it.
REFERENCE_FOS = [
    ("ordinary_fellenius", 1.114420, SMALL),
    ("bishop_simplified", 1.155640, BIG),
    ("janbu_simplified", 1.084930, SMALL),
    ("janbu_corrected", 1.149240, BIG),
    ("spencer", 1.156640, BIG),
    ("lowe_karafiath", 1.163100, BIG),
    ("gle_morgenstern_price", 1.157850, BIG),
]

# Reference sliding-mass area, m2
REFERENCE_AREA = {BIG: 184.457, SMALL: 160.250}

# Reference endpoints of the BIG circle — the whole point of invariant 2
BIG_ENDPOINTS = (15.342, 47.323)

# Slip-centre grid, verbatim from the reference model
GRID_X = (-40.0, 70.0)
GRID_Y = (35.0, 135.0)
GRID_NX, GRID_NY = 21, 19
RADIUS_INCREMENT = 10
NUM_SLICES = 25

# (X intervals + 1)(Y intervals + 1)(Radius Increment + 1), documented by
# the reference and reported by it as 4840 surfaces.
EXPECTED_TOTAL = (GRID_NX + 1) * (GRID_NY + 1) * (RADIUS_INCREMENT + 1)

_CACHE: dict = {}


def _ej2_project():
    """The reference model, built from Ej_2_Geometria.txt.

    Built in code rather than loaded from referencias/: the suite must run
    from a clean checkout, and that directory is not part of it.
    """
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
    p = Project("ej2")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))

    m1 = Material(name="Material 1", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=20, friction_angle=35))
    m2 = Material(name="Material 2", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=15, friction_angle=28))
    m3 = Material(name="Material 3", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=26, friction_angle=30))
    p.materials = [m1, m2, m3]

    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(60, 60), Vertex(100, 65)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(25, 40), Vertex(100, 55)], closed=False),
        btype=BoundaryType.MATERIAL))

    regs = p.resolve_regions()
    ordered = sorted(regs, key=lambda r: r.centroid()[1])
    p.assign_material_at(*ordered[0].centroid(), m3.id)
    p.assign_material_at(*ordered[1].centroid(), m2.id)
    p.assign_material_at(*ordered[2].centroid(), m1.id)
    return p


def _grid_search(method_id: str):
    """Run the reference Grid Search once and reuse it.

    The full grid is 4840 circles and takes several seconds; sharing one
    run between the cases that need it is what keeps this file cheap.
    """
    if method_id in _CACHE:
        return _CACHE[method_id]
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    gs = GridSearch(method=get_method(method_id)(), grid_x=GRID_X,
                    grid_y=GRID_Y, grid_nx=GRID_NX, grid_ny=GRID_NY,
                    radius_increment=RADIUS_INCREMENT, min_radius=2.0,
                    num_slices=NUM_SLICES, min_area=1.0)
    _CACHE[method_id] = (gs.run(_ej2_project()))
    return _CACHE[method_id]


class TestGroundSurfaceEj2:
    """Invariant 1 — the bottom-edge vertex is not terrain."""

    def test_upper_envelope_ignores_the_bottom_vertex(self):
        from ogr_core.geometry import ground_surface
        p = _ej2_project()
        gs = ground_surface(p.external_boundary())
        at_zero = [v for v in gs.vertices if abs(v.x) < 1e-9]
        assert at_zero, "x = 0 must be a breakpoint of the profile"
        # The external boundary has a vertex at (0, 0) on its bottom edge.
        # Ground there is the flat terrain at y = 30.
        assert abs(at_zero[0].y - 30.0) < 1e-9, at_zero[0].y

    def test_profile_is_monotone_over_the_flat_terrain(self):
        """No ravine anywhere between the left edge and the slope toe."""
        from ogr_core.geometry import upper_y_at
        p = _ej2_project()
        verts = list(p.external_boundary().polyline.vertices)
        for x in (-50.0, -40.0, -25.0, -10.0, 0.0, 7.5, 15.0):
            assert abs(upper_y_at(verts, x) - 30.0) < 1e-9, x

    def test_slicer_and_search_agree_on_the_profile(self):
        """Two call sites, one definition. They diverged for 80 versions."""
        from ogr_slip2d.search import PathSearch
        from ogr_slip2d.slicer import _ground_surface_from_external
        p = _ej2_project()
        ext = p.external_boundary()
        a = [(v.x, v.y) for v in _ground_surface_from_external(ext).vertices]
        b = [(v.x, v.y)
             for v in PathSearch._ground_profile(list(ext.polyline.vertices))]
        assert a == b, (a, b)

    def test_the_memo_follows_an_edited_boundary(self):
        """The envelope is memoised; moving a vertex must still show.

        The profile is asked for once per slip surface, so a Grid Search
        asks thousands of times for one unchanging boundary and the answer
        is cached. The boundary is edited IN PLACE by the modeller, so the
        cache is keyed on coordinates: keyed on the object it would hand
        back the old profile after every vertex drag, which is the same
        class of silent-wrong-terrain bug this version exists to fix.
        """
        from ogr_core.geometry import Polyline, Vertex, ground_surface
        box = Polyline(vertices=[Vertex(0, 0), Vertex(10, 0),
                                 Vertex(10, 5), Vertex(0, 5)], closed=True)
        before = [(v.x, v.y) for v in ground_surface(box).vertices]
        assert before == [(0, 5.0), (10, 5)], before
        box.vertices[2] = Vertex(10, 9)
        after = [(v.x, v.y) for v in ground_surface(box).vertices]
        assert after == [(0, 5.0), (10, 9)], after


class TestChordSelectionEj2:
    """Invariant 2 — the analysed mass is the critical one."""

    def test_reference_circle_defines_two_masses(self):
        from ogr_core.geometry import ground_surface
        from ogr_slip2d.surface import SlipCircle
        p = _ej2_project()
        cx, cy, r = BIG
        circle = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        chords = circle.candidate_chords(ground_surface(p.external_boundary()))
        assert len(chords) == 2, chords
        # The leftmost one is the lens of level ground beyond the toe.
        assert chords[0][0] < 0.0 < chords[0][1] < BIG_ENDPOINTS[0]

    def test_reference_circle_resolves_to_the_slope_mass(self):
        """The mass analysed must be the reference's, not the lens."""
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej2_project()
        cx, cy, r = BIG
        gs = GridSearch(method=get_method("bishop_simplified")(),
                        num_slices=NUM_SLICES, min_area=0.0)
        res = gs.evaluate_circle(
            p, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
        assert res is not None, "the reference critical circle was rejected"
        sd = res.surface.to_dict()
        assert abs(sd["x_left"] - BIG_ENDPOINTS[0]) < 0.05, sd["x_left"]
        assert abs(sd["x_right"] - BIG_ENDPOINTS[1]) < 0.05, sd["x_right"]


class TestReferenceCirclesEj2:
    """The seven methods on the reference circles, to within 0.5 %."""

    def test_all_seven_methods(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej2_project()
        worst = []
        for method_id, ref, (cx, cy, r) in REFERENCE_FOS:
            gs = GridSearch(method=get_method(method_id)(),
                            num_slices=NUM_SLICES, min_area=0.0)
            res = gs.evaluate_circle(
                p, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
            assert res is not None, method_id
            assert res.is_valid, (method_id, res.error_message)
            err = abs(res.fos - ref) / ref
            worst.append((method_id, res.fos, ref, err))
            assert err < 0.005, (method_id, res.fos, ref, err)
        assert len(worst) == 7

    def test_sliding_mass_area(self):
        """Same mass as the reference, so the factors compare like for like.

        The chord is taken from the circle itself, not from the reference's
        printed endpoints: those carry three decimals, and feeding
        x_right = 47.323 instead of the true crossing at 47.322908 puts the
        arc 1.4e-4 above the ground there — enough for the slicer to drop
        the last slice and lose 0.6 % of the area. Printed precision is not
        exact geometry.
        """
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        from ogr_core.geometry import ground_surface
        p = _ej2_project()
        ground = ground_surface(p.external_boundary())
        for circle_def, ref_area in REFERENCE_AREA.items():
            cx, cy, r = circle_def
            c = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
            chords = c.candidate_chords(ground)
            # The mass on the slope is the one whose left end is at the toe
            # of the slope face, i.e. the rightmost candidate.
            c.x_left, c.x_right = chords[-1]
            sl = slice_surface(p, c, num_slices=NUM_SLICES)
            assert sl is not None
            area = sum(s.width * max(s.height, 0.0) for s in sl)
            assert abs(area - ref_area) / ref_area < 0.005, (area, ref_area)


class TestSoilContainmentEj2:
    """Invariant 3 — nothing analysed may leave the soil region."""

    def test_no_analysed_surface_dips_below_the_model_floor(self):
        p = _ej2_project()
        y_floor = min(v.y for v in p.external_boundary().polyline.vertices)
        result = _grid_search("bishop_simplified")
        offenders = []
        for ev in result.evaluations:
            if not ev.is_valid:
                continue
            sd = ev.surface.to_dict()
            if sd.get("radius") is None:
                continue
            if sd["centre_y"] - sd["radius"] < y_floor - 1e-9:
                offenders.append(sd)
        assert not offenders, (
            "%d analysed surfaces reach below y = %.1f, the first at "
            "centre (%.3f, %.3f) R = %.3f"
            % (len(offenders), y_floor, offenders[0]["centre_x"],
               offenders[0]["centre_y"], offenders[0]["radius"]))

    def test_a_circle_through_the_floor_is_rejected(self):
        """The circle the search used to report as critical."""
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej2_project()
        # Centre (-13.810, 35.000) R = 37.049 reaches y = -2.05, below the
        # bottom of the model at y = 0. It was reported as the global
        # minimum at FoS = 0.792 against a reference of 1.156.
        gs = GridSearch(method=get_method("bishop_simplified")(),
                        num_slices=NUM_SLICES, min_area=1.0)
        res = gs.evaluate_circle(
            p, SlipCircle(centre_x=-13.810, centre_y=35.0, radius=37.049))
        if res is not None:
            sd = res.surface.to_dict()
            assert sd["centre_y"] - sd["radius"] >= -1e-9, sd


class TestGridSearchEj2:
    """The full search, against the reference global minimum."""

    def test_generated_population_matches_the_reference(self):
        result = _grid_search("bishop_simplified")
        assert result.total_count == EXPECTED_TOTAL, result.total_count

    def test_bishop_global_minimum_within_two_percent(self):
        """Within 2 %, not 0.5 %.

        The per-centre radius sampling is not the reference's — the
        reference's own critical radius, 60.257 at centre
        (-3.333, 87.632), is not among the eleven this program generates
        there — so the search lands on a neighbouring circle. On the SAME
        circle the agreement is 0.07 % (see TestReferenceCirclesEj2); the
        residue here is sampling, not formulation, and the radius rule is
        the open item recorded in the v0.1.84 changelog.
        """
        result = _grid_search("bishop_simplified")
        assert result.critical is not None
        err = abs(result.critical.fos - 1.155640) / 1.155640
        assert err < 0.02, (result.critical.fos, err)

    def test_critical_surface_daylights_on_the_slope(self):
        """Not on the floor of the model, which is what the bug did."""
        result = _grid_search("bishop_simplified")
        sd = result.critical.surface.to_dict()
        # The slope face runs from (15, 30) to (40, 55); the reference
        # enters at x = 15.342 and exits at x = 47.323.
        assert 10.0 < sd["x_left"] < 25.0, sd["x_left"]
        assert 35.0 < sd["x_right"] < 60.0, sd["x_right"]


class TestModelEj2:
    def test_three_regions(self):
        assert len(_ej2_project().resolve_regions()) == 3
