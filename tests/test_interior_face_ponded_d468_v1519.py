# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D468 (v0.1.519) — the ponded water against a cliff INSIDE the top of a mass
pushes the mass, on the slice of the cliff's high side.

The invariant
-------------
A mass that runs under a cliff (a vertical face of the ground) and leaves
above it has the wet part of the face as part of its boundary: the free
water in front pushes it with the resultant of the hydrostatic pressure on
a plane face, ½·γw·h² at h/3 above the foot with the water below the crest
(the closed form of D450, ``slicer.end_face_water``). On the block of the
ficha (a cliff from (50, 10) to (50, 20), the water at 17, a mass from
(40, 10) to (90, 20)) that is ½·γw·7² = 240.345 kN/m toward +x at the
elevation 12.333. Until 0.1.518 the slicer lost it or guessed it, by the
number of slices: on a cut the face was nobody's top and gave 0; inside a
slice it was read as part of a straight top, 196.2 with 97 slices.

The owner's decision (2026-11-28): the face is a mandatory cut, and the
thrust goes whole to the slice of its HIGH side, whose side the face is. On
the low side, whole or half, it would act above that slice's own top (10),
in the air; measured with the thrust on a cut, Spencer 2.61580 on the high
side, 2.65413 on the low one, 2.63486 half and half, 2.16582 without.

Checked here, against the closed form (rule 1):

* 240.345 kN/m at 12.333 on the slice that starts at the face, with 30, 31
  and 97 slices, the face being a slice boundary in all three;
* the mirror image: −240.345 on the slice that ends at the face;
* Sarma's wedges carry the same 240.345 (the step lies inside a wedge's
  top, which already integrated it);
* with no free water in front of the face (the water table at 5 in front
  of it, below its foot, and at 17 behind), the rule does nothing: no cut
  and no thrust, the slices of the switch off bit for bit. (The slice that
  holds the face there still reads water off the chord of its top, 196.2
  kN/m with 97 slices: a defect of its own, reported and not fixed here;
  making such a face a cut moved the validated slicing of bank problem 059,
  whose water table rises from the foot of its wall);
* the control: with the water below the foot of the face, the slices are
  the ones of the switch off, bit for bit;
* ``INTERIOR_FACE_PONDED_WATER`` moves the factor of safety (rule 7).

Cost: a handful of slicings of one small model; well under 1 s.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material, MohrCoulomb, PorePressureType
from ogr_core.project import Project

GW = 9.81
_WANT = 0.5 * GW * 7.0 ** 2
_Y = 10.0 + 7.0 / 3.0
_MASS = [(40, 10), (55, 5), (80, 13), (90, 20)]     # no vertex at the cliff


def _pl(points, closed=False):
    return Polyline(vertices=[Vertex(x, y) for x, y in points],
                    closed=closed)


def _model(level=17.0, mirror=False, from_face=False):
    def mx(pts):
        return [(100.0 - x, y) for x, y in pts] if mirror else pts
    p = Project("D468")
    ext = _pl(mx([(0, 0), (100, 0), (100, 20), (50, 20), (50, 10),
                  (0, 10)]), closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="soil", unit_weight=18.0,
                 strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0),
                 pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [m]
    # ``from_face``: the water table at 5 in front of the face (below its
    # foot, 10) and at ``level`` behind it, so that no free water stands
    # against the face
    line = ([(-1, 5), (50, 5), (50, level), (101, level)] if from_face
            else [(-1, level), (101, level)])
    wt = Boundary(polyline=_pl(mx(line)), btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    m.water_surface_id = wt.id
    return p


def _surface(mirror=False):
    from ogr_slip2d.surface import SlipSurface
    pts = _MASS
    if mirror:
        pts = sorted((100.0 - x, y) for x, y in pts)
    return SlipSurface(polyline=_pl(pts))


def _cut(p, s, n=30):
    from ogr_slip2d.slicer import slice_surface
    v = slice_surface(p, s, num_slices=n)
    assert v is not None
    return v


def _switch(on, fn):
    from ogr_slip2d import slicer
    saved = slicer.INTERIOR_FACE_PONDED_WATER
    slicer.INTERIOR_FACE_PONDED_WATER = on
    try:
        return fn()
    finally:
        slicer.INTERIOR_FACE_PONDED_WATER = saved


class TestInteriorFacePondedWater:
    def test_the_block_on_the_high_side_whatever_the_slices(self):
        p = _model()
        for n in (30, 31, 97):
            v = _cut(p, _surface(), n)
            wet = [s for s in v if s.water_force_h]
            assert len(wet) == 1, (n, len(wet))
            s = wet[0]
            assert abs(s.base_x_left - 50.0) < 1e-9, (n, s.base_x_left)
            assert math.isclose(s.water_force_h, _WANT, rel_tol=1e-12), n
            assert math.isclose(s.water_force_h_moment / s.water_force_h,
                                _Y, rel_tol=1e-12), n
            assert math.isclose(s.pond_force_h, _WANT, rel_tol=1e-12), n

    def test_the_mirror_on_the_slice_that_ends_at_the_face(self):
        p = _model(mirror=True)
        v = _cut(p, _surface(mirror=True), 97)
        wet = [s for s in v if s.water_force_h]
        assert len(wet) == 1
        assert abs(wet[0].base_x_right - 50.0) < 1e-9
        assert math.isclose(wet[0].water_force_h, -_WANT, rel_tol=1e-12)

    def test_sarma_carries_the_same_thrust(self):
        from ogr_slip2d.sarma.wedges import build_wedges
        p = _model()
        s = _surface()
        w = build_wedges(p, s, _cut(p, s), 4)
        assert w is not None
        assert math.isclose(sum(x.water_force_h for x in w), _WANT,
                            rel_tol=1e-9)

    def test_no_water_in_front_the_rule_does_nothing(self):
        """With the water table above the foot BEHIND the face only, no
        cut and no thrust: the slices of the switch off, bit for bit."""
        p = _model(from_face=True)
        on = _cut(p, _surface(), 97)
        off = _switch(False, lambda: _cut(p, _surface(), 97))
        assert [s.to_dict() for s in on] == [s.to_dict() for s in off]

    def test_control_dry_face_bit_for_bit(self):
        p = _model(level=9.0)               # below the foot of the face
        on = _cut(p, _surface(), 97)
        off = _switch(False, lambda: _cut(p, _surface(), 97))
        assert [s.to_dict() for s in on] == [s.to_dict() for s in off]

    def test_the_switch_moves_the_factor(self):
        from ogr_slip2d import Spencer

        def fos():
            p = _model()
            s = _surface()
            return Spencer(tolerance=1e-10).compute_fos(
                p, s, _cut(p, s, 97)).fos

        on = fos()
        off = _switch(False, fos)
        assert on > off * 1.05, (on, off)
