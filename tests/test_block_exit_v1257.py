# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.257, defect D238 — a Block Search projection leaves the soil at the
exact crossing of its ray with the ground, and no end of a trial surface is
ever below the ground at its own x.

Invariants protected:

1. **The exit is the crossing, on the ray.** Against a profile with an
   inclined face, a flat crest and a vertical step, the exit of a ray is
   the intersection worked out by hand, to rounding — including a point
   part-way up the vertical step. Until v0.1.256 the projection marched
   along the ray in steps of 0.5 model units and returned the ground under
   the first step past the crossing: up to half a step off, and on a face at
   the ground's height, not the ray's.
2. **A start on the ground whose ray points into the air is its own exit.**
   That is the outer corner of every gabion tread of verification problem
   109, where each weak-layer polyline begins. The old first-step return
   took the start's x with the ground under the STEP — on the 109 the toe
   flat, 0.99 m down — and the x-sort then dropped the real start: the
   critical surface began 0.99 m below the corner of the wall.
3. **The same model in metres and in millimetres gives the same surfaces
   in proportion.** The old step and margins were absolute (0.5 and 1.0
   model units), so they were half a metre in one and half a millimetre in
   the other.
4. **The draw does not change.** The exit decides where a surface ends,
   not how many random numbers are drawn nor in what order: with the switch
   on and off the search makes the same draws (the switch is
   ``ogr_slip2d.search.BLOCK_EXACT_EXIT``, so the bank can attribute what
   the fix moves).

The surfaces are recorded by standing in for ``evaluate_surface``, which
also makes the runs cheap: no factor of safety is computed. The Block
Search draws the same candidates whatever their factors are
(``SAME_SURFACES_EVERY_SAMPLE``).

COST. A few Block Search runs of 60 candidates without evaluation, and a
handful of ray exits. About a second.
"""
from __future__ import annotations

import math

_SEED = 11

#: A gabion-like step after verification problem 109: risers leaning 11°
#: off the vertical and treads that dip slightly back, then a flat crest.
#: The polyline starts at the outer corner of the first tread.
_GROUND = [(0.0, 5.0), (10.0, 5.0), (10.2, 6.0), (11.2, 5.9), (11.4, 7.0),
           (30.0, 7.0)]
_CORNER = (10.2, 6.0)
_JOINT = [_CORNER, (18.0, 5.2)]


def _profile(scale=1.0):
    from ogr_core.geometry import Vertex
    return [Vertex(x * scale, y * scale) for x, y in
            [(0, 10), (20, 10), (20, 20), (40, 30), (60, 30)]]


def _exit(x, y, deg, scale=1.0):
    from ogr_core.geometry import ray_ground_exit
    return ray_ground_exit(_profile(scale), x * scale, y * scale,
                           math.radians(deg), 1e-6 * 60.0 * scale)


class TestTheExitIsTheCrossing:
    """Invariant 1, on a hand profile: (0,10)-(20,10), a vertical step to
    (20,20), a 1:2 face to (40,30), a crest to (60,30)."""

    def test_through_the_face(self):
        """From (30, 15) at 135°: y = 45 − x meets y = 10 + x/2 at
        x = 70/3, y = 65/3."""
        x, y = _exit(30.0, 15.0, 135.0)
        assert abs(x - 70.0 / 3.0) < 1e-12 and abs(y - 65.0 / 3.0) < 1e-12

    def test_through_the_crest(self):
        """From (30, 5) at 45°: y = x − 25 meets y = 30 at x = 55."""
        x, y = _exit(30.0, 5.0, 45.0)
        assert abs(x - 55.0) < 1e-12 and abs(y - 30.0) < 1e-12

    def test_part_way_up_the_vertical_step(self):
        """From (25, 12) at 170°, the ray meets x = 20 at
        y = 12 + 5·tan 10°, between the foot (10) and the top (20) of the
        step: the exit is ON the riser."""
        x, y = _exit(25.0, 12.0, 170.0)
        assert abs(x - 20.0) < 1e-12
        assert abs(y - (12.0 + 5.0 * math.tan(math.radians(10.0)))) < 1e-12

    def test_from_the_ground_into_the_soil_and_out_again(self):
        """From (30, 25), on the face, at 20°: below the 1:2 face, so into
        the soil, and out through the crest at 30 + 5/tan 20°."""
        x, y = _exit(30.0, 25.0, 20.0)
        assert abs(x - (30.0 + 5.0 / math.tan(math.radians(20.0)))) < 1e-9
        assert abs(y - 30.0) < 1e-9

    def test_a_ray_into_the_soil_has_no_exit(self):
        assert _exit(30.0, 5.0, -45.0) is None

    def test_a_start_in_the_air_has_no_exit(self):
        assert _exit(30.0, 29.0, 135.0) is None

    def test_in_millimetres_the_same_point_in_proportion(self):
        for args in ((30.0, 15.0, 135.0), (30.0, 5.0, 45.0),
                     (25.0, 12.0, 170.0)):
            m = _exit(*args)
            mm = _exit(*args, scale=1000.0)
            assert abs(mm[0] - 1000.0 * m[0]) < 1e-9 * 1000.0 * 60.0
            assert abs(mm[1] - 1000.0 * m[1]) < 1e-9 * 1000.0 * 60.0


class TestAStartOnTheGround:
    """Invariant 2, on the hand profile and on the step model."""

    def test_the_top_of_a_step_into_the_air_is_its_own_exit(self):
        """At (20, 20), the top of the step, 135° and 225° both point out
        of the soil. 225° then runs through the air and lands on the flat
        at the foot: that is an ENTRY, and skipping the start would have
        reported it as the exit."""
        assert _exit(20.0, 20.0, 135.0) == (20.0, 20.0)
        assert _exit(20.0, 20.0, 225.0) == (20.0, 20.0)


# ======================================================================
def _step_model(scale=1.0):
    from ogr_core.geometry import (BlockObjectKind, BlockObjectSpec,
                                   Boundary, BoundaryType, Polyline, Vertex)
    from ogr_core.geometry.block_object import PolylinePointMode
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("D238")
    pts = [(0.0, 0.0), (30.0, 0.0)] + list(reversed(_GROUND))
    ext = Polyline(vertices=[Vertex(x * scale, y * scale) for x, y in pts],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=20.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    joint = Boundary(polyline=Polyline(vertices=[
        Vertex(x * scale, y * scale) for x, y in _JOINT], closed=False),
        btype=BoundaryType.BLOCK_SEARCH_OBJECT)
    joint.block_object = BlockObjectSpec(
        BlockObjectKind.POLYLINE, left_point=PolylinePointMode.END_POINT)
    p.add_boundary(joint)
    s = p.settings.search
    s.search_method = "block"
    s.surface_type = "non_circular"
    return p


def _candidates(scale=1.0, left=(135.0, 135.0), right=(30.0, 60.0)):
    """Every trial surface the search hands to the evaluator, in order,
    with the uniform draws it made. Nothing is evaluated."""
    import random

    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.search import BlockSearch

    p = _step_model(scale)
    s = BlockSearch(method=BishopSimplified(), num_slices=12,
                    num_surfaces=60, seed=_SEED,
                    left_start_angle_deg=left[0], left_end_angle_deg=left[1],
                    right_start_angle_deg=right[0],
                    right_end_angle_deg=right[1])
    seen, draws = [], []
    s.evaluate_surface = lambda project, surface: seen.append(
        [(v.x, v.y) for v in surface.polyline.vertices])
    original = random.Random.uniform

    def spy(self, a, b):
        draws.append((a, b))
        return original(self, a, b)

    random.Random.uniform = spy
    try:
        r = s.run(p)
    finally:
        random.Random.uniform = original
    return seen, draws, r


def _ground_below(x, y, scale=1.0):
    """How far (x, y) is below the ground at its own x; ≤ 0 when it is not.

    At a step the ground has two heights; the LOWER is the one a point on
    the face is measured against."""
    from ogr_core.geometry import Polyline, Vertex, envelope_y_at
    g = Polyline(vertices=[Vertex(a * scale, b * scale) for a, b in _GROUND])
    heights = [h for h in (envelope_y_at(g, x), envelope_y_at(g, x, side=-1),
                           envelope_y_at(g, x, side=1)) if h is not None]
    return min(heights) - y


class TestNoEndIsBuried:
    """Invariants 2 and 3, through the search."""

    def test_the_premise_the_search_makes_surfaces_here(self):
        seen, _draws, _r = _candidates()
        assert len(seen) > 20

    def test_every_surface_starts_on_the_corner_of_the_tread(self):
        """Fails on v0.1.256: the first-step return put the start at
        (10.2, 5.0), a metre below the corner, and the sort dropped the
        corner."""
        seen, _draws, _r = _candidates()
        assert seen and all(s[0] == _CORNER for s in seen), seen[:3]

    def test_no_end_is_below_the_ground(self):
        seen, _draws, _r = _candidates()
        for s in seen:
            for x, y in (s[0], s[-1]):
                assert _ground_below(x, y) <= 1e-9, (x, y)

    def test_the_right_end_is_where_its_ray_meets_the_ground(self):
        """Each right end is ON the ground profile and on the 45° line from
        the last chain point: the ray's own point, not the ground under a
        step. (Near the corner the joint runs a millimetre under the
        dipping tread, so those rays come out through the tread rather than
        the crest; the identity holds either way.)"""
        from ogr_core.geometry import Polyline, Vertex, distance_to_profile

        g = Polyline(vertices=[Vertex(a, b) for a, b in _GROUND])
        seen, _draws, _r = _candidates(right=(45.0, 45.0))
        assert seen
        for s in seen:
            (xa, ya), (xb, yb) = s[-2], s[-1]
            assert distance_to_profile(g, xb, yb) < 1e-12, (xb, yb)
            assert abs((yb - ya) - (xb - xa)) < 1e-12

    def test_millimetres_give_the_same_surfaces_in_proportion(self):
        """Fails on v0.1.256, whose step of 0.5 was half a metre in one and
        half a millimetre in the other."""
        m, _d, _r = _candidates()
        mm, _d2, _r2 = _candidates(scale=1000.0)
        assert len(m) == len(mm)
        for a, b in zip(m, mm):
            assert len(a) == len(b)
            for (xa, ya), (xb, yb) in zip(a, b):
                assert abs(xb - 1000.0 * xa) < 1e-6
                assert abs(yb - 1000.0 * ya) < 1e-6


class TestTheDrawDoesNotChange:
    """Invariant 4: the switch moves where a surface ends, never the draw."""

    def test_the_same_draws_with_the_switch_on_and_off(self):
        import ogr_slip2d.search as S

        before = getattr(S, "BLOCK_EXACT_EXIT", None)
        try:
            S.BLOCK_EXACT_EXIT = True
            seen_on, draws_on, r_on = _candidates()
            S.BLOCK_EXACT_EXIT = False
            seen_off, draws_off, r_off = _candidates()
        finally:
            if before is None:
                del S.BLOCK_EXACT_EXIT
            else:
                S.BLOCK_EXACT_EXIT = before
        assert draws_on == draws_off
        assert r_on.attempts == r_off.attempts == 60
        assert seen_on and seen_off
