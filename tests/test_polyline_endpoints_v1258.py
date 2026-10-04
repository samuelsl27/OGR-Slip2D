# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.258, defect D244 — the two ends of a polyline slip surface are on the
ground, or the surface is not analysed, and that is said.

Invariants protected:

1. **An end below the ground is refused, with its own reason.** The slicer
   used to judge a polyline's ends only for a base ABOVE the ground. An end
   inside the soil was sliced as it came, the end slice got a vertical face
   from that vertex up to the ground carrying neither strength nor thrust,
   and the surface came out valid and lower without a word (the critical of
   verification problem 15 sunk 5 m and 1 m: Janbu 0.4294 to 0.3929). The
   reference calls such a surface −101, «Only one (or none) slip surface /
   slope intersections». The refusal travels as ``REFUSED_END_BELOW_GROUND``,
   the search counts it apart and its note does not blame the slice count,
   which is what the old unsliceable note did for every refusal.
2. **What is on the ground is untouched, bit for bit,** and three things are
   on the ground although an end is not at the profile's height: an end at
   the foot of a vertical face or on it (the ground has two heights there),
   an end at a tension crack (below the ground on purpose), and an end a
   rounding width under it. The tolerance is ``END_BELOW_GROUND_REL`` =
   1e-4 of the surface's width, chosen on the census of the verification
   bank: archived polylines carry four decimals and sit up to 2e-6 of the
   width under the ground; real burials started at 3.3e-3.
3. **The API puts a hand-entered end on the External Boundary and says
   so**, as the reference does with a slip surface entered by hand.
4. **Rule 7: freeing the ends of the optimisation still moves the number,
   and each end stays on the ground.** Until now a free end moved in the
   plane, and on problem 15 the walk buried both ends in six runs of six.
5. **The non-circular Auto Refine puts both coordinates of its ends on the
   ground**, not only x: the arc's height at a steep end can be a little
   below the ground, and the rule above would throw the trial away.

The switch ``ogr_slip2d.slicer.END_ON_GROUND`` gives the old engine back;
it is used here only to show what the rule changes.

COST. A dozen single-surface evaluations and one short optimisation walk.
A few seconds.
"""
from __future__ import annotations

import math

_SLICES = 30


def _slope(vertical=False, crack=False):
    """A 20 m slope: flat toe at y = 10, face to (40, 30), crest at 30.

    ``vertical``: a vertical face at x = 20 instead of the 45° one.
    ``crack``: a tension crack zone 3 m deep under the crest.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    top = 20.0 if vertical else 40.0
    pts = [(0.0, 0.0), (60.0, 0.0), (60.0, 30.0), (top, 30.0), (20.0, 10.0),
           (0.0, 10.0)]
    p = Project("D244")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if crack:
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(top, 27.0), Vertex(60.0, 27.0)], closed=False),
            btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(name="Soil", unit_weight=20.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    p.settings.methods.num_slices = _SLICES
    return p


def _poly(pts):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))


#: Ends on the ground: (15, 10) on the toe flat and (48, 30) on the crest.
_ON = [(15.0, 10.0), (24.0, 6.0), (34.0, 9.0), (42.0, 18.0), (48.0, 30.0)]
_WIDTH = 48.0 - 15.0


def _with_left_end(dy):
    return [(15.0, 10.0 + dy)] + _ON[1:]


def _evaluate(p, pts, switch=True):
    """One evaluation with the switch as asked, restored afterwards.

    Read with ``getattr`` so that against an engine without the switch the
    controls still run (and pass) and only the behaviour fails."""
    import ogr_slip2d.slicer as SL
    from ogr_slip2d.analysis_runner import build_search
    missing = object()
    before = getattr(SL, "END_ON_GROUND", missing)
    try:
        SL.END_ON_GROUND = switch
        s = build_search(p, "bishop_simplified")
        return s.evaluate_surface(p, _poly(pts)), s
    finally:
        if before is missing:
            del SL.END_ON_GROUND
        else:
            SL.END_ON_GROUND = before


# ======================================================================
class TestABuriedEndIsRefused:
    """Invariant 1."""

    def test_the_premise_the_old_engine_priced_it_lower_and_valid(self):
        p = _slope()
        on, _s = _evaluate(p, _ON, switch=False)
        sunk, _s = _evaluate(p, _with_left_end(-2.0), switch=False)
        assert on.is_valid and sunk.is_valid
        assert sunk.fos < on.fos

    def test_the_slicer_refuses_it_with_its_reason(self):
        """Fails on v0.1.257, which sliced it."""
        from ogr_slip2d.slicer import REFUSED_END_BELOW_GROUND, slice_surface
        why = []
        assert slice_surface(_slope(), _poly(_with_left_end(-2.0)),
                             num_slices=_SLICES, reasons=why) is None
        assert why == [REFUSED_END_BELOW_GROUND]

    def test_the_search_says_why_and_not_the_slice_count(self):
        from ogr_slip2d.search import SearchResult
        p = _slope()
        res, s = _evaluate(p, _with_left_end(-2.0))
        assert res is None
        assert "-101" in s.refusal_text()

        def run_one(project):
            s.evaluate_surface(project, _poly(_with_left_end(-2.0)))
            return SearchResult(method_id=s.method.METHOD_ID)

        s._run = run_one
        r = s.run(p)
        assert r.ends_below_ground == 1
        lines = [n for n in r.notes if "not on the ground surface" in n]
        assert len(lines) == 1 and "slice-count" in lines[0]
        assert not any("Use more slices" in n for n in r.notes)

    def test_the_census_counts_it_as_minus_101(self):
        from ogr_slip2d.interpretation import ERROR_OTHER, invalid_summary
        from ogr_slip2d.search import SearchResult
        r = SearchResult(method_id="bishop_simplified")
        r.ends_below_ground = 3
        r.ends_above_ground = 1
        out = invalid_summary(r)
        assert out["by_code"].get(ERROR_OTHER) == 4
        assert out["by_reason"].get(
            "an end of the polyline is not on the ground surface") == 4

    def test_the_analysis_door_says_it(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        out = evaluate_surfaces(_slope(), _poly(_with_left_end(-2.0)),
                                ["bishop_simplified"])
        assert out.results["bishop_simplified"] is None
        assert any(w.startswith("bishop_simplified: ") and "-101" in w
                   for w in out.warnings)


class TestWhatIsOnTheGroundIsUntouched:
    """Invariant 2."""

    def test_ends_on_the_ground_bit_for_bit(self):
        p = _slope()
        a, _s = _evaluate(p, _ON, switch=True)
        b, _s = _evaluate(p, _ON, switch=False)
        assert a.is_valid and repr(a.fos) == repr(b.fos)

    def test_the_tolerance_is_relative_to_the_width(self):
        p = _slope()
        inside, _s = _evaluate(p, _with_left_end(-0.5e-4 * _WIDTH))
        outside, _s = _evaluate(p, _with_left_end(-2e-4 * _WIDTH))
        assert inside is not None and inside.is_valid
        assert outside is None

    def test_an_end_at_the_foot_of_a_vertical_face_is_on_the_ground(self):
        """At x = 20 the ground is both 10 (the foot) and 30 (the top)."""
        p = _slope(vertical=True)
        pts = [(20.0, 10.0), (28.0, 7.0), (38.0, 12.0), (46.0, 30.0)]
        a, _s = _evaluate(p, pts, switch=True)
        b, _s = _evaluate(p, pts, switch=False)
        assert a is not None and repr(a.fos) == repr(b.fos)

    def test_an_end_at_a_tension_crack_is_exempt(self):
        """The crack truncates the surface at its line, 3 m under the
        crest: below the ground on purpose."""
        p = _slope(crack=True)
        a, _s = _evaluate(p, _ON, switch=True)
        b, _s = _evaluate(p, _ON, switch=False)
        assert a is not None and a.is_valid
        # The premise: the crack DID truncate it, at y = 27 between (42, 18)
        # and (48, 30), so the end analysed is 3 m under the ground.
        assert abs(a.slices[-1].base_x_right - 46.5) < 1e-9
        assert repr(a.fos) == repr(b.fos)

    def test_an_archived_crack_end_a_rounding_off_the_line_is_exempt(self):
        """A polyline rebuilt from an archive: already truncated at the
        crack, its end a rounding width under the crack line and with no
        crack of its own. 2e-4 here, outside the fine tolerance with which
        D189 gives back its wall (1e-6 of the model's diagonal, 6.7e-5 on
        this slope) and inside this rule's (1e-4 of the width, 3.2e-3). The
        end is the crack's (the model says so) and 3 m under the ground. The
        archived critical of verification problem 39 is this case, 4.4e-5
        off on a smaller model: refused when only the surface's own crack
        was asked."""
        p = _slope(crack=True)
        pts = _ON[:-1] + [(46.5, 27.0 - 2e-4)]
        a, _s = _evaluate(p, pts, switch=True)
        b, _s = _evaluate(p, pts, switch=False)
        assert b is not None and b.is_valid
        assert a is not None and repr(a.fos) == repr(b.fos)


class TestTheApiPutsTheEndsOnTheBoundary:
    """Invariant 3."""

    def _ws(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="D244")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [60, 0], [60, 30], [40, 30], [20, 10],
                         [0, 10]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb", "params": {
                               "cohesion": 10.0, "friction_angle": 30.0}}}]})
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], num_slices=_SLICES)
        return ws, pid

    def test_a_buried_end_is_moved_and_said(self):
        from ogr_api import call
        ws, pid = self._ws()
        pts = [list(v) for v in _with_left_end(-2.0)]
        out = call(ws, "surface_evaluate", project_id=pid,
                   surface={"type": "polyline", "points": pts})
        notes = out.get("notes") or []
        assert any("first vertex (15, 8)" in n and "(15, 10)" in n
                   for n in notes), notes
        on = call(ws, "surface_evaluate", project_id=pid,
                  surface={"type": "polyline",
                           "points": [list(v) for v in _ON]})
        assert (out["methods"]["bishop_simplified"]["fos"]
                == on["methods"]["bishop_simplified"]["fos"])

    def test_ends_on_the_ground_get_no_note(self):
        from ogr_api import call
        ws, pid = self._ws()
        out = call(ws, "surface_evaluate", project_id=pid,
                   surface={"type": "polyline",
                            "points": [list(v) for v in _ON]})
        assert not out.get("notes")


class TestFreeEndsSlideAlongTheGround:
    """Invariant 4 (rule 7)."""

    def test_the_number_moves_and_the_ends_stay_on_the_ground(self):
        from ogr_core.geometry import distance_to_profile, ground_surface
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface

        p = _slope()
        s = build_search(p, "bishop_simplified")
        fixed = optimize_surface(p, s, _poly(_ON), OptimizeSettings(
            seed=4, max_iterations=300, move_endpoints=False))
        free = optimize_surface(p, s, _poly(_ON), OptimizeSettings(
            seed=4, max_iterations=300, move_endpoints=True))
        assert free[1] is not None and fixed[1] is not None
        assert free[1].fos != fixed[1].fos
        g = ground_surface(p.external_boundary())
        for v in (free[0].polyline.vertices[0],
                  free[0].polyline.vertices[-1]):
            assert distance_to_profile(g, v.x, v.y) < 1e-9, (v.x, v.y)


class TestTheAutoRefineEndsAreOnTheGround:
    """Invariant 5."""

    def test_both_coordinates(self):
        from ogr_core.geometry import envelope_y_at, ground_surface
        from ogr_slip2d.search import AutoRefineNonCircularSearch
        from ogr_slip2d.surface import SlipCircle

        p = _slope()
        g = ground_surface(p.external_boundary())
        c = SlipCircle(centre_x=22.0, centre_y=44.0, radius=34.0)
        x0, x1 = _crossings(g, c)
        c.x_left, c.x_right = x0, x1
        poly = AutoRefineNonCircularSearch._arc_polyline(c, 12)
        AutoRefineNonCircularSearch._pin_ends_to_ground(p, poly)
        v0, v1 = poly.polyline.vertices[0], poly.polyline.vertices[-1]
        assert v0.y == envelope_y_at(g, v0.x, side=1)
        assert v1.y == envelope_y_at(g, v1.x, side=-1)
        assert (v0.x, v1.x) == (x0, x1)


def _crossings(g, c):
    """The two abscissae where the lower arc of ``c`` meets ``g``, by
    bisection on the vertical gap (a hand-made helper for the test)."""
    from ogr_core.geometry import envelope_y_at

    def gap(x):
        d = c.radius ** 2 - (x - c.centre_x) ** 2
        return envelope_y_at(g, x) - (c.centre_y - math.sqrt(max(d, 0.0)))

    def root(a, b):
        for _ in range(200):
            m = 0.5 * (a + b)
            if (gap(a) > 0) == (gap(m) > 0):
                a = m
            else:
                b = m
        return 0.5 * (a + b)

    # Inside the profile's span (0..60): at x = 0 the arc is above the toe
    # flat, at its lowest point (x = 22) under the face, and at x = 56 at the
    # height of its centre, above the crest. One crossing in each bracket.
    return root(0.0, c.centre_x), root(c.centre_x, c.centre_x + c.radius)
