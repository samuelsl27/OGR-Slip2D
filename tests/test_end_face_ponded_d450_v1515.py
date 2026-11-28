# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D450 (v0.1.515) — the ponded water against a cliff pushes the mass that
leaves through it.

The invariant
-------------
A surface that leaves through a vertical face of the ground (a cliff, the
face of a wall, the step of a flooded excavation) below the free water has
the wet part of that face, between its exit and the water, as the end of
its mass. The water pushes that end into the mass with the resultant of the
hydrostatic pressure on a plane face,

    F = ½·γw·[(n − y_lo)² − (n − y_hi)²]   at the centroid of the diagram,

with ``n`` the water level and ``[y_lo, y_hi]`` the wet part on the mass;
with the water below the crest of the face, ½·γw·h² at h/3 above the exit
(the expression the tension crack uses, Terzaghi 1943). External water
pressures belong to the total stress on the boundary of the mass (Duncan,
Wright & Brandon 2014, pp. 28-29). Until 0.1.514 nobody counted it: the
slicer reads the free water on the slice TOPS, and the first slice starts
on the face with its top at the crest; Sarma's wedges read it on the ground
between the tops of their faces, and the toe face runs up the cliff. The
block of the ficha (a cliff from (50, 10) to (50, 20), the water at 17, the
exit at 14) summed 0 on both paths where 44.145 kN/m belong.

Checked here against that closed form (rule 1):

* the slicer's first slice and Sarma's first wedge carry +44.145 kN/m at
  the elevation 15, and in the pond's own field (``pond_force_h``, which
  the Ordinary Method keeps out of its base normal, D199);
* the mirror image carries −44.145 kN/m on the LAST slice and wedge;
* with the water above the crest of the face (level 22), the trapezoid:
  ½·γw·(8² − 2²) at 16.4 (the centroid h·(b + 2a)/(3·(a + b)) of a
  trapezoid of sides a = 2·γw and b = 8·γw over h = 6);
* an end that is the wall of a tension crack gets nothing from the pond:
  the crack's water is the thrust there;
* with no free water in front of the face (a water table drawn from the
  face inwards, v0.1.517), nothing, on both paths and in the mirror;
* a surface whose ends are on the flat ground keeps every bit it had
  (control);
* ``END_FACE_PONDED_WATER`` moves the factor of safety, of a vertical-slice
  method and of Sarma's (rule 7).

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


def _pl(points, closed=False):
    return Polyline(vertices=[Vertex(x, y) for x, y in points],
                    closed=closed)


def _model(level=17.0, mirror=False, from_face=False):
    """``from_face``: the water table drawn only over the soil, from the
    face inwards, so that the ground in front of the face is dry."""
    def mx(pts):
        return [(100.0 - x, y) for x, y in pts] if mirror else pts
    p = Project("D450")
    ext = _pl(mx([(0, 0), (100, 0), (100, 20), (50, 20), (50, 10),
                  (0, 10)]), closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="soil", unit_weight=18.0,
                 strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0),
                 pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [m]
    line = [(50, level), (101, level)] if from_face else [(-1, level),
                                                          (101, level)]
    wt = Boundary(polyline=_pl(mx(line)), btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    m.water_surface_id = wt.id
    return p


def _surface(points, mirror=False):
    from ogr_slip2d.surface import SlipSurface
    if mirror:
        points = sorted((100.0 - x, y) for x, y in points)
    return SlipSurface(polyline=_pl(points))


_CLIFF = [(50, 14), (60, 12), (80, 13), (90, 20)]


def _cut(p, surface, n=30):
    from ogr_slip2d.slicer import slice_surface
    v = slice_surface(p, surface, num_slices=n)
    assert v is not None
    return v


def _wedges(p, surface, v):
    from ogr_slip2d.sarma.wedges import build_wedges
    reasons: list = []
    w = build_wedges(p, surface, v, 4, reasons=reasons)
    assert w is not None, reasons
    return w


def _line(piece):
    """``(F_h, y)`` of the horizontal water on one slice or wedge."""
    f = piece.water_force_h
    return f, (piece.water_force_h_moment / f if f else None)


class TestEndFacePondedWater:
    def test_the_block_of_the_ficha_on_both_paths(self):
        p = _model()
        s = _surface(_CLIFF)
        v = _cut(p, s)
        w = _wedges(p, s, v)
        want = 0.5 * GW * 3.0 ** 2
        for name, piece, rest in (("slice", v[0], v.slices[1:]),
                                  ("wedge", w[0], list(w)[1:])):
            f, y = _line(piece)
            assert math.isclose(f, want, rel_tol=1e-12), (name, f)
            assert math.isclose(y, 15.0, rel_tol=1e-12), (name, y)
            assert math.isclose(piece.pond_force_h, want, rel_tol=1e-12)
            # nothing else in the mass is under the water
            assert all(r.water_force_h == 0.0 for r in rest), name

    def test_the_mirror_pushes_the_other_way_on_the_last(self):
        p = _model(mirror=True)
        s = _surface(_CLIFF, mirror=True)
        v = _cut(p, s)
        w = _wedges(p, s, v)
        want = -0.5 * GW * 3.0 ** 2
        for name, piece in (("slice", v[-1]), ("wedge", list(w)[-1])):
            f, y = _line(piece)
            assert math.isclose(f, want, rel_tol=1e-12), (name, f)
            assert math.isclose(y, 15.0, rel_tol=1e-12), (name, y)

    def test_water_above_the_crest_is_the_trapezoid(self):
        p = _model(level=22.0)
        s = _surface(_CLIFF)
        v = _cut(p, s)
        w = _wedges(p, s, v)
        a, b, h = 2.0 * GW, 8.0 * GW, 6.0
        want = 0.5 * GW * (8.0 ** 2 - 2.0 ** 2)
        y_want = 14.0 + h * (b + 2 * a) / (3 * (a + b))
        for name, piece in (("slice", v[0]), ("wedge", w[0])):
            # the flat tops above the crest add their (zero) horizontal part
            f, y = _line(piece)
            assert math.isclose(f, want, rel_tol=1e-12), (name, f)
            assert math.isclose(y, y_want, rel_tol=1e-12), (name, y)

    def test_no_pond_in_front_of_the_face_no_thrust(self):
        """v0.1.517 -- the level is read in front of the face: a water
        table drawn from the face inwards leaves the ground in front dry,
        and 0.1.515 read it at the face and pushed 44.145 kN/m anyway."""
        for mirror in (False, True):
            p = _model(mirror=mirror, from_face=True)
            s = _surface(_CLIFF, mirror=mirror)
            v = _cut(p, s)
            w = _wedges(p, s, v)
            assert all(x.water_force_h == 0.0 for x in v), mirror
            assert all(x.water_force_h == 0.0 for x in w), mirror

    def test_a_cracked_end_takes_none_of_the_pond(self):
        from ogr_slip2d import slicer
        p = _model()
        s = _surface(_CLIFF)
        saved = slicer.END_FACE_PONDED_WATER
        slicer.END_FACE_PONDED_WATER = False
        try:
            v = _cut(p, s)
        finally:
            slicer.END_FACE_PONDED_WATER = saved
        ground = slicer._ground_surface_from_external(p.external_boundary())
        tol = slicer._model_grid_tol(p)
        slicer._apply_end_face_water(p, v, ground, (50.0, 14.0, 20.0), tol)
        assert v[0].water_force_h == 0.0
        slicer._apply_end_face_water(p, v, ground, None, tol)
        assert math.isclose(v[0].water_force_h, 0.5 * GW * 9.0,
                            rel_tol=1e-12)

    def test_control_ends_on_the_flat_ground_keep_every_bit(self):
        from ogr_slip2d import slicer
        p = _model()
        s = [(60, 20), (70, 15), (90, 20)]       # wholly on the bench
        on = _cut(p, _surface(s))
        saved = slicer.END_FACE_PONDED_WATER
        slicer.END_FACE_PONDED_WATER = False
        try:
            off = _cut(p, _surface(s))
        finally:
            slicer.END_FACE_PONDED_WATER = saved
        assert [x.to_dict() for x in on] == [x.to_dict() for x in off]

    def test_the_switch_moves_the_factor(self):
        from ogr_slip2d import Spencer, slicer
        from ogr_slip2d.sarma.wedges import solve_wedges

        def factors():
            p = _model()
            s = _surface(_CLIFF)
            v = _cut(p, s)
            lem = Spencer(tolerance=1e-10).compute_fos(p, s, v).fos
            sol = solve_wedges(_wedges(p, s, v), tolerance=1e-10)
            assert sol.converged, sol.message
            return lem, sol.fos

        on = factors()
        saved = slicer.END_FACE_PONDED_WATER
        slicer.END_FACE_PONDED_WATER = False
        try:
            off = factors()
        finally:
            slicer.END_FACE_PONDED_WATER = saved
        # the water pushes into the mass from the side it slides towards
        assert on[0] > off[0] * 1.001, (on, off)
        assert on[1] > off[1] * 1.001, (on, off)
