# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.128 — the non-circular Auto Refine exists, and its vertex
count moves the number.

**The invariant**: declaring Surface Type = Non-Circular with Search
Method = Auto Refine must run a search that returns POLYLINES and that
reads ``auto_refine_num_vertices_along_surface``. Until this version it
returned circles: ``build_search`` dispatched on the method alone, Auto
Refine is offered under both surface types, and the setting that
configures the conversion had no reader anywhere in the engine — it sat
in the frozen inventory of ``test_settings_coverage_v1103.py`` as defect
D32.

Rule 7, in the form that costs most. A search declared non-circular whose
answer equals the circular one does not look like a bug: it looks like
the two families agreeing, which is the conclusion a verification bank
exists to be able to draw. Four problems of the Duncan and Wright series
declare *auto refine search* and publish a non-circular column; had the
bank been built with the method its statements name, that column would
have republished the circular number with every appearance of normality.

**What validates the conversion, and why it is not the obvious thing.**
The natural check — refine the polyline and watch it reproduce the arc —
fails for Bishop, Ordinary and every other moment-only method, and NOT
because the conversion is wrong. ``moment_axis`` records the reason
(anomaly D47): a polyline has no centre of rotation, the automatic axis
is not the generating circle's centre, and a moment-only factor of safety
therefore depends on a point that moved. Measured on verification
problem 77, Bishop against the arc: -2.64 % at 8 vertices, -2.55 % at 32,
-2.56 % at 128 — flat, so it is the axis and not the discretisation. The
size and even the SIGN of that residual are properties of the model: on
the slope built below the same comparison gives +1.11 %, +0.34 %,
+0.30 %.

Spencer satisfies force AND moment equilibrium, so its answer cannot
depend on where moments are taken, and it is the honest instrument for
this question. On the slope built below its error against the arc falls
+0.2920 %, +0.0472 %, +0.0151 %, +0.0096 % for 8, 16, 32 and 64 vertices
— close to a factor of four per doubling, which is what an inscribed
polygon does — while Bishop on the same circle stops at +0.31 % and stays
there. CONVERGENCE is therefore what these tests assert, not a tolerance
at any one vertex count: it is the property a correct conversion has and
a wrong one does not, and it is the half of the comparison that the
moment axis cannot contaminate.
"""
from __future__ import annotations
import math


def _slope(name: str = "auto-refine-nc"):
    """A small slope, deliberately cheap.

    The Auto Refine loop is C(divisions, 2) x circles x iterations, NOT
    divisions x circles x iterations, so a modest-looking panel is a
    quadratic amount of work. Every test below keeps the divisions in
    single figures for that reason.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 10.0
    beta = math.radians(35.0)
    toe = 20.0
    crest = toe + H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, -8.0), Vertex(45, -8.0), Vertex(45, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=19,
                            strength=MohrCoulomb(cohesion=10,
                                                 friction_angle=25))]
    # Comfortably above the vertex counts used here: a polyline of N
    # vertices makes N-1 mandatory slice boundaries and the slicer refuses
    # a surface with more segments than slices. That rule has its own
    # tests below; it must not contaminate the others.
    p.settings.methods.num_slices = 80
    p.settings.statistics.seed = 20260829
    return p


def _project(surface_type: str, num_vertices: int = 12, optimize=False):
    p = _slope(f"{surface_type}-{num_vertices}")
    s = p.settings.search
    s.surface_type = surface_type
    s.search_method = "auto_refine"
    s.auto_refine_divisions_along_slope = 5
    s.auto_refine_circles_per_division = 4
    s.auto_refine_num_iterations = 2
    s.auto_refine_num_vertices_along_surface = num_vertices
    # Explicit, not automatic: the optimisation is ON by default for this
    # pair, and a random walk over the winners would hide the very thing
    # most of these tests measure.
    s.optimize_enabled = optimize
    return p


def _run(surface_type, num_vertices=12, method="bishop_simplified",
         optimize=False):
    from ogr_slip2d.analysis_runner import build_search
    p = _project(surface_type, num_vertices, optimize)
    return build_search(p, method).run(p)


# ======================================================================
class TestTheSearchThatIsBuilt:
    """The dispatch that had never asked the question."""

    def test_non_circular_builds_the_non_circular_search(self):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import AutoRefineNonCircularSearch
        search = build_search(_project("non_circular"), "bishop_simplified")
        assert isinstance(search, AutoRefineNonCircularSearch)

    def test_circular_still_builds_the_circular_search(self):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import (AutoRefineNonCircularSearch,
                                       AutoRefineSearch)
        search = build_search(_project("circular"), "bishop_simplified")
        assert isinstance(search, AutoRefineSearch)
        assert not isinstance(search, AutoRefineNonCircularSearch)

    def test_the_vertex_count_reaches_the_search(self):
        """The reproduction of D32, inverted: the object used not to carry
        the number at all."""
        from ogr_slip2d.analysis_runner import build_search
        search = build_search(_project("non_circular", 37),
                              "bishop_simplified")
        assert search.num_vertices == 37

    def test_it_returns_polylines_and_not_circles(self):
        from ogr_slip2d.surface import SlipCircle
        r = _run("non_circular")
        assert r.critical is not None
        assert not isinstance(r.critical.surface, SlipCircle)
        for e in r.evaluations:
            assert getattr(e.surface, "polyline", None) is not None

    def test_the_circular_one_still_returns_circles(self):
        """The seam ``_evaluate_trial`` must not have moved the circular
        search, which four models of the reference bank use."""
        from ogr_slip2d.surface import SlipCircle
        r = _run("circular")
        assert r.critical is not None
        assert isinstance(r.critical.surface, SlipCircle)


# ======================================================================
class TestRuleSeven:
    """The closing criterion of the defect: two values of the setting,
    and the result has to change or the setting does not exist."""

    def test_the_vertex_count_moves_the_number(self):
        few = _run("non_circular", 4)
        many = _run("non_circular", 20)
        assert few.critical is not None and many.critical is not None
        assert abs(few.critical.fos - many.critical.fos) > 1e-9, (
            few.critical.fos, many.critical.fos)

    def test_the_surface_has_the_vertices_that_were_asked_for(self):
        """N vertices, N-1 segments — the reference's own counting: "if
        the Number of vertices = 4, a circle will be converted into a
        piecewise linear surface with 3 segments"."""
        for n in (4, 9, 20):
            r = _run("non_circular", n)
            assert r.critical is not None
            verts = r.critical.surface.polyline.vertices
            assert len(verts) == n, (n, len(verts))

    def test_the_two_surface_types_do_not_agree_by_accident(self):
        """The failure D32 would have produced on the bank: the same
        model, the two surface types, the same number."""
        circ = _run("circular")
        non = _run("non_circular")
        assert circ.critical is not None and non.critical is not None
        assert abs(circ.critical.fos - non.critical.fos) > 1e-9


# ======================================================================
class TestTheConversionIsTheDocumentedOne:
    """"Sub-dividing the circular arc into approximately equal divisions,
    and joining the resulting vertices with straight line segments"."""

    def _circle_and_search(self):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import AutoRefineNonCircularSearch
        p = _project("circular")
        circular = build_search(p, "bishop_simplified")
        critical = circular.run(p).critical
        assert critical is not None
        nc = AutoRefineNonCircularSearch(method=circular.method,
                                         num_slices=200)
        return p, nc, critical.surface

    def test_every_vertex_lies_on_the_generating_circle(self):
        p, nc, circle = self._circle_and_search()
        poly = nc._arc_polyline(circle, 32)
        for v in poly.polyline.vertices:
            d = math.hypot(v.x - circle.centre_x, v.y - circle.centre_y)
            assert abs(d - circle.radius) <= 1e-9 * circle.radius, d

    def test_the_central_angles_are_equal(self):
        """Equal ANGLE and not equal x. On a circle equal angle is equal
        arc length, which is what "equal divisions of the arc" means;
        equal-x spacing puts its longest chords at the steep daylighting
        ends, exactly where the polyline departs most from the arc."""
        p, nc, circle = self._circle_and_search()
        poly = nc._arc_polyline(circle, 24)
        ang = [math.atan2(v.y - circle.centre_y, v.x - circle.centre_x)
               for v in poly.polyline.vertices]
        steps = [b - a for a, b in zip(ang[:-1], ang[1:])]
        assert max(steps) - min(steps) <= 1e-9 * abs(steps[0]), steps

    def test_it_spans_the_arc_it_came_from(self):
        p, nc, circle = self._circle_and_search()
        poly = nc._arc_polyline(circle, 16)
        verts = poly.polyline.vertices
        assert abs(verts[0].x - circle.x_left) <= 1e-12
        assert abs(verts[-1].x - circle.x_right) <= 1e-12

    def test_a_complete_equilibrium_method_reproduces_the_arc(self):
        """Rule 1, and the only method that can answer this question.

        Spencer satisfies force and moment equilibrium, so its factor of
        safety cannot depend on where moments are taken — which is what
        makes it, and not Bishop, the instrument for asking whether a
        refined polyline IS its arc.

        The assertion is CONVERGENCE and not a tolerance at any one
        count, because convergence is the property a correct conversion
        has and a wrong one does not. An inscribed polygon approaches its
        arc with the square of the chord, and the measured sequence is
        that: +0.2920 %, +0.0472 %, +0.0151 %, +0.0096 % for 8, 16, 32
        and 64 vertices — very nearly a factor of four per doubling, then
        flattening onto the floor of the solver's own tolerance.

        The same sequence under Bishop, for contrast, is +1.11 %,
        +0.476 %, +0.343 %, +0.312 %: it stops falling at about 0.3 % and
        stays there. That is not this conversion, it is anomaly D47 — the
        automatic moment axis of a polyline is not the centre of the
        circle it was cut from, and a moment-only method is entitled to
        notice. ``moment_axis`` carries the measurement and
        ``tests/test_moment_axis_v1126.py`` the invariant.
        """
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import AutoRefineNonCircularSearch
        p = _project("circular")
        circular = build_search(p, "spencer")
        critical = circular.run(p).critical
        assert critical is not None
        nc = AutoRefineNonCircularSearch(method=circular.method,
                                         num_slices=200)
        with p.regions_frozen():
            arc = nc._best_of_masses(p, (critical.surface,))
            assert arc is not None
            errors = []
            for n in (8, 16, 32, 64):
                poly = nc._arc_polyline(critical.surface, n)
                res = nc._best_of_masses(p, (poly,))
                assert res is not None, n
                errors.append(abs(res.fos - arc.fos) / arc.fos)
            # Refining never makes it worse...
            for coarse, fine in zip(errors[:-1], errors[1:]):
                assert fine <= coarse + 1e-12, errors
            # ...it improves by a lot over the range...
            assert errors[0] > 4.0 * errors[-1], errors
            # ...and it arrives, which a wrong conversion would not.
            assert errors[-1] < 5e-4, errors


# ======================================================================
class TestTheSlicerRefusesTooManyVertices:
    """A polyline of N vertices has N-1 mandatory slice boundaries, and
    ``_slice_bounds`` refuses a surface whose segments outnumber the
    slices. The vertex spinbox reaches 100 while the default slice count
    is 25, so this is one control away — and it does not fail cleanly:
    material boundaries and the water table take cuts of their own, per
    surface, so the search quietly drops the surfaces that cross the most
    layers and keeps the rest."""

    def test_a_run_that_loses_surfaces_says_so(self):
        p = _project("non_circular", 40)
        p.settings.methods.num_slices = 20
        from ogr_slip2d.analysis_runner import build_search
        r = build_search(p, "bishop_simplified").run(p)
        assert any("could not be sliced" in n for n in r.notes), r.notes

    def test_a_run_within_the_budget_says_nothing(self):
        r = _run("non_circular", 12)
        assert not any("could not be sliced" in n for n in r.notes), r.notes

    def test_the_certain_case_is_predicted_before_running(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project("non_circular", 40)
        p.settings.methods.num_slices = 20
        notes = settings_warnings(p, ("bishop_simplified",))
        assert any("mandatory slice boundary" in n for n in notes), notes

    def test_it_is_silent_when_the_budget_is_enough(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        notes = settings_warnings(_project("non_circular", 12),
                                  ("bishop_simplified",))
        assert not any("mandatory slice boundary" in n for n in notes)


# ======================================================================
class TestOptimizeSurfacesReachesIt:
    """"The Optimize Surfaces option is automatically ON by default for
    the Auto Refine (Non-Circular) search method"."""

    def test_it_is_on_by_default_for_the_pair(self):
        from ogr_core.project.settings import optimize_enabled_for
        p = _project("non_circular")
        p.settings.search.optimize_enabled = None       # automatic
        assert optimize_enabled_for(p.settings.search) is True

    def test_it_is_off_by_default_for_the_circular_one(self):
        """The default is a property of the PAIR. The circular Auto Refine
        shares the method id and has no vertices to move."""
        from ogr_core.project.settings import optimize_enabled_for
        p = _project("circular")
        p.settings.search.optimize_enabled = None
        assert optimize_enabled_for(p.settings.search) is False

    def test_the_search_is_built_with_it(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _project("non_circular")
        p.settings.search.optimize_enabled = None
        search = build_search(p, "bishop_simplified")
        assert search.optimize is not None and search.optimize.enabled

    def test_the_circular_one_is_not(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _project("circular")
        p.settings.search.optimize_enabled = None
        assert build_search(p, "bishop_simplified").optimize is None

    def test_no_note_says_the_setting_was_ignored(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project("non_circular")
        p.settings.search.optimize_enabled = True
        notes = settings_warnings(p, ("bishop_simplified",))
        assert not any("The setting was ignored" in n for n in notes), notes

    def test_the_circular_one_still_gets_that_note(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project("circular")
        p.settings.search.optimize_enabled = True
        notes = settings_warnings(p, ("bishop_simplified",))
        assert any("The setting was ignored" in n for n in notes), notes


# ======================================================================
class TestSurfaceTypeAndMethodMustAgree:
    """The class of defect D32 belongs to. The two controls are stored
    independently and nothing compared them, so a pair that cannot be
    honoured ran the method's own search and said nothing."""

    def test_a_circular_method_under_non_circular_warns(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project("non_circular")
        p.settings.search.search_method = "grid"
        notes = settings_warnings(p, ("bishop_simplified",))
        assert any("does not search for that kind of surface" in n
                   for n in notes), notes

    def test_a_non_circular_method_under_circular_warns(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project("circular")
        p.settings.search.search_method = "block"
        notes = settings_warnings(p, ("bishop_simplified",))
        assert any("does not search for that kind of surface" in n
                   for n in notes), notes

    def test_neither_auto_refine_pairing_warns(self):
        """Auto Refine is legitimately in both families, and after this
        version both are honoured."""
        from ogr_slip2d.analysis_runner import settings_warnings
        for st in ("circular", "non_circular"):
            notes = settings_warnings(_project(st), ("bishop_simplified",))
            assert not any("does not search for that kind of surface" in n
                           for n in notes), (st, notes)
