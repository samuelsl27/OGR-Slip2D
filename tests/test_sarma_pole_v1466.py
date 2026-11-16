# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.466 (D451) — the root of Sarma's method next to a pole.

WHAT WAS WRONG

With the method's default settings (25 wedges, the bisector) the saturated
problem 4 of the verification manual gave F = 0.9004 instead of 0.4347,
admissible and with no note. Its published end, (128; 67.6737), is 3.3e-5
above the ground; the slicer puts the base of the end slice on the ground,
which is right for vertical slices, but the uniform division of the wedges
at x = 123 was cut on the original line, so the two bases of the straight
scarp differed by 6.3e-7 rad. A face normal to its base, in one material,
has q = cos φ′ (1 − tan φ̄′ tan φ′) = 0 at F = tan φ = tan 42° = 0.90040,
a pole the solver cancels only for collinear bases (``solver._pairs``):
it was left with a true root next to it, with forces of 6.5e5 times the
vertical load, and the rule of the largest root took it.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The published problem 4 with the default settings**: the saturated
   and the dry cases at 1e-6 of the bank's tool (``_TOOL4`` of v1463, a
   computation that does not import OGR) and at ±1 % of the published
   1.198 and 0.434, with 25 and with 50 wedges, and equal to what 2 wedges
   give at 1e-9: the identity of a straight stretch of one material
   (v1463 pins it dry; with the end the slicer puts on the ground it needed
   the fix). Mirrored too, where that end is the left one.
2. **The scarp is one line**: its bases have the same α to 1e-12 and the
   solver pairs them (the exact cancellation of a straight base cut by a
   face).
3. **A root next to a pole is said** (``method.sarma_near_pole``, with the
   least |q| of the faces under ``NEAR_POLE_MIN_Q`` = 0.2, the factor kept:
   the owner's decision after the adversarial review, which measured that
   a refusal on the force ratio missed a 3.2° bend and refused a factor
   equal to Janbu's; which root to report is D452): a vertex DRAWN at
   x = 123 and bent 2.6e-6 rad, and the review's 2 m off the chord, are
   said; exactly collinear (0.434662) and a straight base with 6000 kPa of
   face cohesion (the factor equal to Janbu's) are not; the limit moves the
   note (rule 7); the API says it.
4. **A weak-layer clip of a polyline** gets the resolved ends on its base:
   with a joint under the toe, 25 and 50 wedges give what 2 give.
5. **What the fix does not touch**: a circle, a composite, a clip of a
   circle, a polyline with its ends on the ground and an end lifted beyond
   the slicer's tolerance are cut as they were (the same object), and the
   user's surface keeps its own end.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_wedges_v1463 as W63  # noqa: E402

#: The ground of problem 4 at x = 128, on the face of the spoil.
_YE = 76.5 + (128 - 111.4) * (13.6815 - 76.5) / (229.545 - 111.4)


def _p4(wet, n=None):
    p = W63._problem4(wet)[0]
    p.settings.sarma.tolerance = 1e-12
    if n is not None:
        p.settings.sarma.num_slices = n
    return p


def _surface(points, kink=True):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface, attach_vertex_data
    s = SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in points], closed=False))
    if kink:
        attach_vertex_data(s, {W63._KINK4: {"angle": W63._THETA4, "c": None,
                                            "phi": None}})
    return s


def _door(project, surface, methods=("sarma",)):
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    out = evaluate_surfaces(project, surface, list(methods))
    return out.results["sarma"], out


def _codes(out):
    """The codes of the door's warnings, a method's note by its own code
    (the door wraps it in ``note.method``)."""
    codes = []
    for w in out.warnings:
        note = (getattr(w, "args", None) or {}).get("note")
        codes.append(note["code"] if isinstance(note, dict)
                     else getattr(w, "code", None))
    return codes


def _bent(dy):
    """Problem 4 with its end on the ground and a vertex at x = 123, ``dy``
    above the chord: 1e-4 is a bend of 2.6e-6 rad, 2.0 one of 3.2°."""
    yc = 6.4 + 15.0 * (_YE - 6.4) / 20.0
    return [(0.0, 0.0), (108.0, 6.4), (123.0, yc + dy), (128.0, _YE)]


def _straight_with_face_cohesion(c_face):
    """A straight base cut by faces whose given cohesion is ``c_face``: the
    identity that cancels every pole (the factor is Janbu's), while X
    carries c̄′d and the forces grow with ``c_face``, far from any pole."""
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("v1466 straight")
    W63._external(p, ((0, 0), (80, 0), (80, 20), (40, 20), (20, 10), (0, 10)))
    p.materials = [Material(name="soil", unit_weight=20.0, strength=MohrCoulomb(
        cohesion=5.0, friction_angle=30.0))]
    p.settings.sarma.interslice_strength = "given"
    p.settings.sarma.interslice_cohesion = c_face
    p.settings.sarma.interslice_phi = 35.0
    p.settings.sarma.tolerance = 1e-12
    return p, _surface(((20, 10), (45, 20)), kink=False)


# ======================================================================
class TestTheDefaultSettings:

    def test_problem_4_with_25_and_50_wedges(self):
        for wet in (False, True):
            two = _door(_p4(wet, 2), _surface(W63._SURFACE4))[0].fos
            for n in (None, 50):
                got = _door(_p4(wet, n), _surface(W63._SURFACE4))[0].fos
                assert got is not None, (wet, n)
                assert abs(got - W63._TOOL4[wet]) <= 1e-6, (wet, n, got)
                assert abs(got / W63._PUBLISHED4[wet] - 1.0) <= 0.01
                assert abs(got - two) <= 1e-9 * two, (wet, n, got, two)
        # mirrored, the end the slicer puts on the ground is the LEFT one
        from ogr_slip2d.surface import attach_vertex_data
        p, s, angles = W63._problem4(True, mirror=True)
        p.settings.sarma.tolerance = 1e-12
        attach_vertex_data(s, {k: {"angle": a, "c": None, "phi": None}
                               for k, a in angles.items()})
        got = _door(p, s)[0].fos
        assert got is not None and abs(got - W63._TOOL4[True]) <= 1e-6, got

    def test_the_scarp_is_one_line(self):
        from ogr_slip2d.methods.sarma import SarmaNonVertical
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.sarma import solver as SV
        from ogr_slip2d.sarma.wedges import to_solver
        from ogr_slip2d.slicer import slice_surface
        p = _p4(True)
        s = _surface(W63._SURFACE4)
        m = build_method(p, "sarma", 30)
        assert isinstance(m, SarmaNonVertical)
        w = m.wedges_for(p, s, slice_surface(p, s, num_slices=30))
        si = to_solver(w)
        fr = SV._frame(si.bases, si.faces, si.slide_sign, si.head_thrust)
        scarp = [i for i, a in enumerate(fr.alpha) if a > 1.0]
        assert len(scarp) >= 2, fr.alpha
        assert max(fr.alpha[i] for i in scarp) - min(
            fr.alpha[i] for i in scarp) <= 1e-12, [fr.alpha[i] for i in scarp]
        pairs = SV._pairs(fr)
        assert all(pairs.get(j) == j - 1 for j in scarp[1:]), pairs
        # and the user's surface keeps its own end
        assert (s.polyline.vertices[-1].x, s.polyline.vertices[-1].y) \
            == W63._SURFACE4[-1]


# ======================================================================
class TestARootNextToAPoleIsSaid:
    """Said with a note, the factor kept (the owner's decision after the
    review; which root to report is D452)."""

    def test_a_drawn_bend_and_the_collinear_vertex(self):
        straight, out = _door(_p4(True), _surface(_bent(0.0)))
        assert abs(straight.fos - W63._TOOL4[True]) <= 1e-6, straight.fos
        assert straight.details["sarma_min_abs_q"] >= 0.2
        assert "method.sarma_near_pole" not in _codes(out)
        bent, out = _door(_p4(True), _surface(_bent(1e-4)))
        # the root next to the pole at tan 42°, kept, and said
        assert abs(bent.fos - math.tan(math.radians(42.0))) <= 1e-4, bent.fos
        assert bent.details["sarma_min_abs_q"] < 1e-3
        assert bent.details["sarma_max_force_ratio"] > 1e4
        assert "method.sarma_near_pole" in _codes(out), out.warnings

    def test_the_cases_of_the_review(self):
        """A vertex 2 m off the chord (3.2°) leaves a root above a pole with
        forces of only 7.5 times the load: said, its least |q| is 0.074. A
        face cohesion of 6000 kPa on a straight base reaches 10.9 times the
        load far from any pole: not said, its least |q| is 0.88."""
        r, out = _door(_p4(True), _surface(_bent(2.0)))
        assert r.fos is not None and r.details["sarma_min_abs_q"] < 0.2
        assert r.details["sarma_max_force_ratio"] < 10.0
        assert "method.sarma_near_pole" in _codes(out)
        p, s = _straight_with_face_cohesion(6000.0)
        r, out = _door(p, s, ("sarma", "janbu_simplified"))
        janbu = out.results["janbu_simplified"].fos
        assert abs(r.fos / janbu - 1.0) <= 1e-4, (r.fos, janbu)
        assert r.details["sarma_max_force_ratio"] > 10.0
        assert r.details["sarma_min_abs_q"] > 0.5
        assert "method.sarma_near_pole" not in _codes(out)

    def test_the_limit_moves_the_note(self):
        import ogr_slip2d.methods.sarma as MS
        saved = MS.NEAR_POLE_MIN_Q
        try:
            MS.NEAR_POLE_MIN_Q = 0.0
            _r, out = _door(_p4(True), _surface(_bent(1e-4)))
            assert "method.sarma_near_pole" not in _codes(out)
            MS.NEAR_POLE_MIN_Q = 10.0
            _r, out = _door(_p4(True), _surface(_bent(0.0)))
            assert "method.sarma_near_pole" in _codes(out)
        finally:
            MS.NEAR_POLE_MIN_Q = saved
        assert MS.NEAR_POLE_MIN_Q == 0.2

    def test_the_api_says_it(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = ws.add(_p4(True)).id
        out = call(ws, "surface_evaluate", project_id=pid, surface={
            "type": "polyline", "points": [list(v) for v in _bent(1e-4)],
            "sarma": [{"x": 108.0, "y": 6.4, "angle": W63._THETA4}]},
            methods=["sarma"])
        assert out["methods"]["sarma"]["fos"] is not None
        assert "method.sarma_near_pole" in str(out), out


# ======================================================================
class TestAWeakLayerClipOfAPolyline:

    def test_its_base_gets_the_resolved_ends(self):
        """Problem 4 with a weak joint of the floor's material under the toe
        stretch: before the fix the saturated case kept the root by the pole
        (0.9004) and the dry one its drift; now 25 and 50 wedges give what 2
        give (the identity of a straight stretch), with no note."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

        def run(wet, n):
            p = _p4(wet, n)
            floor = p.materials[0]
            p.boundaries.append(Boundary(polyline=Polyline([
                Vertex(10.0, 0.3), Vertex(50.0, 3.5), Vertex(100.0, 5.0)]),
                btype=BoundaryType.WEAK_LAYER, material_id=floor.id))
            r, out = _door(p, _surface(W63._SURFACE4))
            assert type(r.surface).__name__ == "WeakLayerSurface"
            assert "method.sarma_near_pole" not in _codes(out)
            return r.fos
        for wet in (False, True):
            two = run(wet, 2)
            for n in (None, 50):
                got = run(wet, n)
                assert abs(got - two) <= 1e-9 * two, (wet, n, got, two)


# ======================================================================
class TestWhatTheFixDoesNotTouch:

    def test_only_a_polyline_with_an_end_put_on_the_ground(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.sarma.wedges import _with_resolved_ends
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import (CompositeSurface, SlipCircle,
                                        SlipSurface, WeakLayerSurface)
        p = _p4(False)
        moved = _surface(W63._SURFACE4)
        v = slice_surface(p, moved, num_slices=30)
        cut = _with_resolved_ends(moved, v)
        assert cut is not moved
        assert (cut.polyline.vertices[-1].x, cut.polyline.vertices[-1].y) \
            == (v[-1].base_x_right, v[-1].base_y_right)
        assert cut.polyline.vertices[-1].y != W63._SURFACE4[-1][1]
        assert cut.tension_cracks is not moved.tension_cracks
        assert cut.vertex_angles == moved.vertex_angles
        on_ground = _surface(_bent(0.0))
        v2 = slice_surface(p, on_ground, num_slices=30)
        assert _with_resolved_ends(on_ground, v2) is on_ground
        circle = SlipCircle(centre_x=60.0, centre_y=120.0, radius=110.0)
        assert _with_resolved_ends(circle, v) is circle
        comp = CompositeSurface.__new__(CompositeSurface)
        assert _with_resolved_ends(comp, v) is comp
        on_circle = WeakLayerSurface(base=circle)
        assert _with_resolved_ends(on_circle, v) is on_circle
        on_polyline = WeakLayerSurface(base=moved)
        cut = _with_resolved_ends(on_polyline, v)
        assert cut is not on_polyline and cut.base is not moved
        assert cut.base.polyline.vertices[-1].y == v[-1].base_y_right
        assert moved.polyline.vertices[-1].y == W63._SURFACE4[-1][1]
        # an end lifted beyond the slicer's tolerance is no end it put on
        # the ground: not moved
        lifted = SlipSurface(polyline=Polyline(vertices=[
            Vertex(x, y) for x, y in W63._SURFACE4[:-1]] + [
            Vertex(128.0, v[-1].base_y_right + 1.0)], closed=False))
        assert _with_resolved_ends(lifted, v) is lifted
