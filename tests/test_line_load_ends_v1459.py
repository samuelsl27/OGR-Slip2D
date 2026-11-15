# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.459 (D427) — a load acts on the mass it is on, once, and a model and
its mirror image give one factor of safety.

WHAT WAS WRONG

A load that acts at a POINT went to a slice by an abscissa test of its own,
with an absolute 1e-12 and no look at the elevation:

* the force of a line load, and of a pressure on a vertical face (which the
  slicer integrates into one force), by ``[x_left − 1e-12, x_right − 1e-12)``
  on every slice, the last included: a load on x_r was on no slice, one on
  x_l on the first, one on an interior cut on the slice to its right;
* the excess pore pressure a line load creates, by
  ``|x − x_c| ≤ b/2 + 1e-12``: on an interior cut it loaded both slices with
  all of itself, and on x_r the last slice, whose force it was not on.

Measured on v0.1.458 on the wall of bank problem 048 without its nails, with
100 kN/m at the top of its face: the model and its mirror image differed by
4.9 % on the 60° plane through the toe and by 21.8 % on a circle leaving
through the face. Problem 048 itself puts its shotcrete facing, 13.2 kN/m, at
(12, 8): x_r of all six of its planes, so it was on none of them.

THE RULE (``ogr_core.loads.overburden.edge_share``, the owner's decisions,
three of them after the adversarial review of v0.1.459)

* On an interior cut, within the tolerance: half, wherever it is in height.
* On an end of the mass, within the tolerance: all of it if it is between
  the base and the top there, none otherwise. A circle leaving through the
  face at (12, 3) does not carry a load at (12, 2), nor a mass starting at
  the corner of the toe (12, 1) the load at the top of the face (12, 8).
* Strictly inside: all of it.
* A pressure on a vertical face asks the same rule, and on an end of the
  mass only the part of the face between the base and the top acts, at the
  centroid of that part.
* The tolerance is the model's (``_model_grid_tol``, relative), but never
  over a quarter of the narrowest slice, so two edges never share a load.
* The excess pore pressure goes by the same shares, through the slicer and
  through a design standard, which asks it again.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

* **The mirror image** (x → −x, the failure direction reversed): one factor,
  to 1e-9, with the load on each end and at ±1e-9, ±5e-13, ±tol/2 and
  ±2·tol of it, on the plane and on the circle, with Bishop and Janbu, and
  with Spencer too for the load on x_r of the circle.
* **The clipped face against a quadrature** (composite Simpson, exact for a
  linear ramp): on the circle's exit, the force and its elevation are the
  integral of the pressure over the part of the face between the exit and
  the crest, for faces drawn up or down, constant, triangular and
  trapezoidal, reaching past the crest or not. (Coulomb 1776; Duncan & Wright 2005, §6): on a plane
  the mass is one free body, F = (c′L + N tan φ′)/T with W + P. The six planes
  of problem 048 with its facing, a load on an interior cut, and a pressure
  on the face: Janbu, both Corps of Engineers and Lowe-Karafiath give it to
  1e-6. This is the facing's own effect, which ``test_support_projection_
  v1113`` now leaves out of its two residual tests (the owner's decision).
* **Once:** on both ends and three interior cuts (the first, a mandatory one
  and the last), at fractions of the tolerance, the parts of a load add up
  to 1 inside [x_l − tol, x_r + tol] and to 0 outside, in metres and in
  millimetres alike; below the base on a cut, on the tolerance in height,
  and on slices narrower than the model's tolerance, also once.
* **The excess pore pressure:** Σ Δu·b = B̄·P·(the load's share), the identity
  of a load spread over the slice that carries it, with and without a design
  standard, on a cut and on an end.
* **The switch** ``LOAD_SHARE_AT_EDGES`` moves the numbers, and off gives the
  v0.1.458 behaviour (rule 7).

Measured cost: about 2 s for the file, none of its cases over 0.7 s; most of
it in the 72 slicings of the mirror image, each with its own load, and
Spencer's two circles. Every one of those numbers is checked against the
mirror image, the wedge or the quadrature.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: The wall of bank problem 048 (Clouterre), without its nails: the crest at
#: y = 8 to the face at x = 12, the face down to the bench at y = 1.
_WALL = ((0, 0), (20, 0), (20, 1), (12, 1), (12, 8), (0, 8))
_FACE_X, _CREST_Y, _BENCH_Y, _H = 12.0, 8.0, 1.0, 7.0
_GAMMA, _C, _PHI = 20.0, 3.0, 38.0
_P = 100.0
_N = 50
_WEDGE = ("janbu_simplified", "corps_engineers_1", "corps_engineers_2",
          "lowe_karafiath")
_TWO = ("bishop_simplified", "janbu_simplified")
# Spencer on a plane has no lambda to look for (every one gives the wedge)
# and takes a second a surface, so it is asked only on the circle, and there
# only with the load exactly on x_r: where a load goes is the slicer's
# business, the same for every method, and Bishop and Janbu sweep the rest.


def _wall(mirror=False, scale=1.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    p = Project("D427 wall")
    s = -scale if mirror else scale
    ext = Polyline(vertices=[Vertex(s * x, scale * y) for x, y in _WALL],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Sand", unit_weight=_GAMMA,
                            sat_unit_weight=_GAMMA,
                            strength=MohrCoulomb(cohesion=_C,
                                                 friction_angle=_PHI))]
    p.assign_material_at(*p.resolve_regions()[0].centroid(),
                         p.materials[0].id)
    p.settings.units.failure_direction = (
        FailureDirection.RIGHT_TO_LEFT if mirror
        else FailureDirection.LEFT_TO_RIGHT)
    return p


def _ground_y(x, mirror=False):
    """The wall's ground at x: the crest behind the face, the bench in
    front; at the face itself, its top (a load on the wall)."""
    return _CREST_Y if (-x if mirror else x) <= _FACE_X else _BENCH_Y


def _line(x, y, magnitude=_P, excess=False):
    from ogr_core.geometry import Vertex
    from ogr_core.loads import LineLoad, LoadOrientation
    ld = LineLoad(point=Vertex(x, y), magnitude=magnitude,
                  orientation=LoadOrientation.VERTICAL, name="L")
    ld.creates_excess_pore_pressure = excess
    return ld


def _face(mirror=False, y_low=_BENCH_Y):
    """20 kPa on the face, pushing into the retained ground."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads import DistributedLoad, LoadOrientation
    x = -_FACE_X if mirror else _FACE_X
    return DistributedLoad(
        start=Vertex(x, y_low), end=Vertex(x, _CREST_Y), magnitude_1=20.0,
        orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL,
        angle_deg=0.0 if mirror else 180.0, name="D")


def _plane(mirror=False, angle=60.0, vertex_x=None):
    """A plane through the toe (12, 1) to the crest; with ``vertex_x``, a
    collinear vertex there, which is a mandatory cut."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    dx = _H / math.tan(math.radians(angle))
    pts = [(_FACE_X - dx, _CREST_Y)]
    if vertex_x is not None:
        pts.append((vertex_x, _CREST_Y - (vertex_x - pts[0][0]) * _H / dx))
    pts.append((_FACE_X, _BENCH_Y))
    if mirror:
        pts = [(-x, y) for x, y in reversed(pts)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts]))


def _circle(mirror=False):
    """Leaves through the face at (12, 3): x_r = 12 exactly, by construction
    (a crossing with a vertical segment is its abscissa)."""
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=-10.0 if mirror else 10.0, centre_y=14.0,
                      radius=math.sqrt(125.0))


def _sliced(p, surface):
    from ogr_slip2d.slicer import slice_surface
    with p.regions_frozen():
        sl = slice_surface(p, surface, num_slices=_N)
    assert sl is not None, "the premise: the surface is sliced"
    return sl


def _factors(p, surface, methods, tol=1e-10):
    from ogr_slip2d.methods import get_method
    sl = _sliced(p, surface)
    out = {}
    for m in methods:
        r = get_method(m)(tolerance=tol, max_iterations=400).compute_fos(
            p, surface, sl)
        assert r.fos is not None, (m, getattr(r, "reason", None))
        out[m] = r.fos
    return out


def _tol(p):
    from ogr_slip2d.slicer import _model_grid_tol
    return _model_grid_tol(p)


def _ends(p, surface):
    sl = _sliced(p, surface)
    return sl.slices[0].base_x_left, sl.slices[-1].base_x_right


def _share_sum(sl, load_id):
    """What the slices carry of a load, as a fraction of it."""
    return math.fsum(part[2] for s in sl.slices for part in s.load_parts
                     if part[0] == load_id) / _P


def _wedge(angle, extra_n=0.0, extra_t=0.0, p_vertical=0.0):
    """The Coulomb wedge of the 048 wall on a plane through the toe at
    ``angle``, with a vertical load ``p_vertical`` on its top and an extra
    force whose normal and driving components are ``extra_n``, ``extra_t``
    (Coulomb 1776; Duncan & Wright 2005, §6)."""
    b = math.radians(angle)
    dx = _H / math.tan(b)
    w = _GAMMA * 0.5 * _H * dx + p_vertical
    length = _H / math.sin(b)
    n = w * math.cos(b) + extra_n
    t = w * math.sin(b) + extra_t
    return (_C * length + n * math.tan(math.radians(_PHI))) / t


# ======================================================================
class TestTheMirrorImage:
    """x → −x with the failure direction reversed: the right end of one is
    the left end of the other, so any rule that treats them differently
    breaks this."""

    _OFFSETS = (0.0, 1e-9, -1e-9, 5e-13, -5e-13)

    def _check(self, surface_of, methods, on_the_end=()):
        p, q = _wall(), _wall(mirror=True)
        tol = _tol(p)
        offsets = self._OFFSETS + (0.5 * tol, -0.5 * tol, 2 * tol, -2 * tol)
        bad = []
        x_l, x_r = _ends(p, surface_of(False))
        for end in (x_l, x_r):
            for e in offsets:
                x = end + e
                # ``on_the_end`` only with the load exactly on x_r, where it
                # was lost: one more method, not one more rule
                asked = methods + (on_the_end if (e == 0.0 and end == x_r)
                                   else ())
                p.line_loads = [_line(x, _ground_y(x))]
                q.line_loads = [_line(-x, _ground_y(-x, True))]
                a = _factors(p, surface_of(False), asked)
                b = _factors(q, surface_of(True), asked)
                for m in asked:
                    if abs(a[m] - b[m]) > 1e-9 * b[m]:
                        bad.append((end, e, m, a[m], b[m]))
        assert not bad, bad

    def test_on_the_plane_through_the_toe(self):
        self._check(_plane, _TWO)

    def test_on_the_circle_leaving_through_the_face(self):
        self._check(_circle, _TWO, on_the_end=("spencer",))


class TestTheWedgeWithItsLoad:
    """A plane is one free body: the force-equilibrium methods owe the
    wedge with W + P, wherever P is on its top, its two ends included."""

    def test_the_six_planes_of_048_with_their_facing(self):
        """The shotcrete facing of problem 048, 13.2 kN/m at (12, 8), on
        each of the six published planes: lost at x_r until v0.1.458."""
        p = _wall()
        p.line_loads = [_line(_FACE_X, _CREST_Y, magnitude=13.2)]
        bad = []
        for angle in (45, 50, 55, 60, 65, 70):
            want = _wedge(angle, p_vertical=13.2)
            got = _factors(p, _plane(angle=angle), _WEDGE)
            bad += [(angle, m, f, want) for m, f in got.items()
                    if abs(f - want) > 1e-6 * want]
        assert not bad, bad

    def test_a_load_on_both_ends_and_inside(self):
        p = _wall()
        x_l, x_r = _ends(p, _plane())
        want = _wedge(60, p_vertical=_P)
        bad = []
        for x in (x_l, 0.5 * (x_l + x_r), x_r):
            p.line_loads = [_line(x, _CREST_Y)]
            got = _factors(p, _plane(), _WEDGE)
            bad += [(x, m, f, want) for m, f in got.items()
                    if abs(f - want) > 1e-6 * want]
        assert not bad, bad

    def test_a_pressure_on_the_face_is_the_wedge_with_the_face_force(self):
        """20 kPa over the whole face, which a plane through the toe has
        above its base all the way: H = 140 kN/m into the retained ground."""
        p = _wall()
        p.distributed_loads = [_face()]
        dxu, dyu = p.distributed_loads[0].direction_vector()
        h = 20.0 * _H
        b = math.radians(60.0)
        # the base normal into the ground below, and the downslope direction
        n = h * (-dxu * math.sin(b) - dyu * math.cos(b))
        t = h * (dxu * math.cos(b) - dyu * math.sin(b))
        want = _wedge(60, extra_n=n, extra_t=t)
        got = _factors(p, _plane(), _WEDGE)
        bad = [(m, f, want) for m, f in got.items()
               if abs(f - want) > 1e-6 * want]
        assert not bad, bad


class TestAnInteriorCut:
    """A load exactly on a mandatory cut: half to each slice beside it."""

    def test_each_slice_beside_it_carries_half(self):
        p = _wall()
        p.line_loads = [_line(10.0, _CREST_Y)]
        sl = _sliced(p, _plane(vertex_x=10.0))
        carried = [(s.base_x_left, s.base_x_right, part[2])
                   for s in sl.slices for part in s.load_parts
                   if part[0] == p.line_loads[0].id]
        assert len(carried) == 2, carried
        assert carried[0][1] == 10.0 == carried[1][0], carried
        assert all(c[2] == 0.5 * _P for c in carried), carried

    def test_the_mirror_image_and_the_wedge(self):
        p, q = _wall(), _wall(mirror=True)
        p.line_loads = [_line(10.0, _CREST_Y)]
        q.line_loads = [_line(-10.0, _CREST_Y)]
        a = _factors(p, _plane(vertex_x=10.0), _TWO)
        # ``_plane`` mirrors the vertex with the rest of the plane
        b = _factors(q, _plane(mirror=True, vertex_x=10.0), _TWO)
        for m in _TWO:
            assert abs(a[m] - b[m]) <= 1e-9 * b[m], (m, a[m], b[m])
        want = _wedge(60, p_vertical=_P)
        assert abs(a["janbu_simplified"] - want) <= 1e-6 * want, (a, want)


def _under_the_toe(mirror=False):
    """A polyline from the crest under the toe to the bench, with a vertex
    at the face: the face is inside the mass and on a mandatory cut."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    pts = [(6.0, _CREST_Y), (_FACE_X, 0.5), (16.0, _BENCH_Y)]
    if mirror:
        pts = [(-x, y) for x, y in reversed(pts)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts]))


class TestAFaceOnAnInteriorCut:
    """The rule of a line load holds for a pressure on a face too: on a cut,
    half to each slice beside it."""

    def test_each_slice_beside_it_carries_half(self):
        p = _wall()
        p.distributed_loads = [_face()]
        sl = _sliced(p, _under_the_toe())
        face_id = p.distributed_loads[0].id
        carried = [(s.base_x_left, s.base_x_right, part[3])
                   for s in sl.slices for part in s.load_parts
                   if part[0] == face_id]
        dxu, _dyu = p.distributed_loads[0].direction_vector()
        whole = 20.0 * _H * dxu
        assert len(carried) == 2, carried
        assert carried[0][1] == _FACE_X == carried[1][0], carried
        assert all(c[2] == 0.5 * whole for c in carried), (carried, whole)

    def test_the_mirror_image(self):
        p, q = _wall(), _wall(mirror=True)
        p.distributed_loads = [_face()]
        q.distributed_loads = [_face(mirror=True)]
        a = _factors(p, _under_the_toe(), _TWO)
        b = _factors(q, _under_the_toe(mirror=True), _TWO)
        for m in _TWO:
            assert abs(a[m] - b[m]) <= 1e-9 * b[m], (m, a[m], b[m])


class TestBelowTheBase:
    """The circle leaves through the face at (12, 3): what is on the face
    below its exit holds up the ground in front, not the mass."""

    def test_a_line_load_below_the_exit_is_not_on_the_mass(self):
        for mirror in (False, True):
            # each model against itself without the load: bit for bit
            bare = _factors(_wall(mirror), _circle(mirror), _TWO)
            p = _wall(mirror)
            x = -_FACE_X if mirror else _FACE_X
            p.line_loads = [_line(x, 2.0)]
            low = _factors(p, _circle(mirror), _TWO)
            assert low == bare, (mirror, low, bare)
            p.line_loads = [_line(x, _CREST_Y)]
            high = _factors(p, _circle(mirror), _TWO)
            inside = x - 1e-9 if not mirror else x + 1e-9
            p.line_loads = [_line(inside, _CREST_Y)]
            assert high == _factors(p, _circle(mirror), _TWO)
            assert all(high[m] != bare[m] for m in bare), (high, bare)

    def test_a_face_pressure_counts_only_above_the_exit(self):
        """The same 20 kPa drawn from y = 1 or from y = 3, the exit: one
        factor, to 1e-9. A face clipped to the part above the base."""
        for mirror in (False, True):
            bare = _factors(_wall(mirror), _circle(mirror), _TWO)
            p = _wall(mirror)
            p.distributed_loads = [_face(mirror)]
            whole = _factors(p, _circle(mirror), _TWO)
            p.distributed_loads = [_face(mirror, y_low=3.0)]
            above = _factors(p, _circle(mirror), _TWO)
            for m in _TWO:
                assert abs(whole[m] - above[m]) <= 1e-9 * above[m], (
                    mirror, m, whole[m], above[m])
                assert abs(whole[m] - bare[m]) > 1e-3 * bare[m], (m, bare)


def _berm(mirror=False):
    """A mass in front of the wall, starting at the corner of its toe: its
    end at x = 12 has the bench, y = 1, for a top."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    pts = [(_FACE_X, _BENCH_Y), (14.0, 0.3), (17.0, _BENCH_Y)]
    if mirror:
        pts = [(-x, y) for x, y in reversed(pts)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts]))


class TestTheTopOfTheMass:
    """On an end, a load is on the mass only between its base and its top:
    the crest of the wall is not on a mass at its foot."""

    def test_a_mass_at_the_foot_of_the_wall_carries_nothing_of_it(self):
        for mirror in (False, True):
            s = -1.0 if mirror else 1.0
            p = _wall(mirror)
            p.line_loads = [_line(s * _FACE_X, _CREST_Y)]
            sl = _sliced(p, _berm(mirror))
            assert _share_sum(sl, p.line_loads[0].id) == 0.0, mirror
            p.line_loads = [_line(s * _FACE_X, _BENCH_Y)]
            sl = _sliced(p, _berm(mirror))
            assert _share_sum(sl, p.line_loads[0].id) == 1.0, mirror
            p.line_loads = []
            p.distributed_loads = [_face(mirror)]
            sl = _sliced(p, _berm(mirror))
            assert not [part for x in sl.slices for part in x.load_parts], (
                mirror, "the face of the wall is not on the berm")


def _quadrature(load, y_lo, y_hi, n=2000):
    """∫p dy and ∫y·p dy of a vertical-segment load over the part of it in
    [y_lo, y_hi], by composite Simpson (exact for a linear ramp, and by
    another road than the slicer's closed form)."""
    y1, y2 = load.start.y, load.end.y
    a, b = max(min(y1, y2), y_lo), min(max(y1, y2), y_hi)
    h = (b - a) / n
    f = m = 0.0
    for i in range(n + 1):
        y = a + i * h
        w = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
        p = load.pressure_at((y - y1) / (y2 - y1))
        f += w * p
        m += w * y * p
    return f * h / 3.0, m * h / 3.0


class TestTheClippedFace:
    """On an end, the part of a face on the mass, at its own centroid:
    against a quadrature of the pressure over that part."""

    def _faces(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import (DistributedLoad, LoadDistribution,
                                    LoadOrientation)
        out = []
        for (y_a, y_b), (m1, m2), dist in (
                ((1.0, 9.0), (0.0, 30.0), LoadDistribution.TRIANGULAR),
                ((9.0, 1.0), (0.0, 30.0), LoadDistribution.TRIANGULAR),
                ((9.0, 1.0), (10.0, 40.0), LoadDistribution.TRAPEZOIDAL),
                ((1.0, 8.0), (20.0, 20.0), LoadDistribution.CONSTANT)):
            out.append(DistributedLoad(
                start=Vertex(_FACE_X, y_a), end=Vertex(_FACE_X, y_b),
                magnitude_1=m1, magnitude_2=m2, distribution=dist,
                orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL,
                angle_deg=180.0, name="D"))
        return out

    def test_on_the_circle_it_is_the_face_between_its_exit_and_the_crest(self):
        """Exit at (12, 3), the crest at 8: the faces reach from 1 to 9 or
        to 8, drawn up or down, with three distributions."""
        bad = []
        for face in self._faces():
            p = _wall()
            p.distributed_loads = [face]
            last = _sliced(p, _circle()).slices[-1]
            f, m = _quadrature(face, 3.0, _CREST_Y)
            got_f, got_y = -last.water_force_h, (last.water_force_h_moment
                                                  / last.water_force_h)
            if (abs(got_f - f) > 1e-9 * f
                    or abs(got_y - m / f) > 1e-9 * _CREST_Y):
                bad.append((face.start.y, face.end.y, got_f, f, got_y, m / f))
        assert not bad, bad

    def test_a_foot_within_the_tolerance_below_the_base_is_not_clipped(self):
        """The plane through the toe has its base at y = 1 on x_r: a face
        from tol/2 below it acts whole; from 2·tol below, only above it."""
        from ogr_core.geometry import Vertex
        p = _wall()
        tol = _tol(p)
        for below, height in ((0.5 * tol, _H + 0.5 * tol), (2 * tol, _H)):
            face = _face()
            face.start = Vertex(_FACE_X, _BENCH_Y - below)
            p.distributed_loads = [face]
            last = _sliced(p, _plane()).slices[-1]
            want = 20.0 * height
            assert abs(-last.water_force_h - want) <= 1e-12 * want, (
                below, -last.water_force_h, want)


class TestTheTolerances:
    """The model's tolerance, in height too, and never wider than a quarter
    of the narrowest slice."""

    def test_in_height_on_the_base_and_on_the_top(self):
        p = _wall()
        tol = _tol(p)
        cases = [(_plane(), _FACE_X, _BENCH_Y - 0.5 * tol, 1.0),
                 (_plane(), _FACE_X, _BENCH_Y - 2.0 * tol, 0.0),
                 (_circle(), _FACE_X, _CREST_Y + 0.5 * tol, 1.0),
                 (_circle(), _FACE_X, _CREST_Y + 2.0 * tol, 0.0)]
        bad = []
        for surface, x, y, want in cases:
            p.line_loads = [_line(x, y)]
            got = _share_sum(_sliced(p, surface), p.line_loads[0].id)
            if got != want:
                bad.append((y, got, want))
        assert not bad, bad

    def test_below_the_base_on_an_interior_cut_it_still_counts_once(self):
        """A load inside the soil counts whole inside a slice, so on a cut
        it counts once too, half and half: the same a hair beside it."""
        p = _wall()
        surface = _plane(vertex_x=10.0)
        y_cut = surface.base_y_at(10.0)
        bad = []
        for x in (10.0, 10.0 + 0.5 * _tol(p), 10.01, 9.99):
            p.line_loads = [_line(x, y_cut - 0.5)]
            got = _share_sum(_sliced(p, surface), p.line_loads[0].id)
            if abs(got - 1.0) > 1e-12:
                bad.append((x, got))
        assert not bad, bad

    def test_slices_narrower_than_the_model_tolerance(self):
        """The wall a thousand times larger (tol 0.0215 m) and a 4 m wedge
        at its crest in 500 slices of 8 mm: a load on x_l and one on a cut
        still count once."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipSurface
        k = 1000.0
        p = _wall(scale=k)
        wedge = SlipSurface(polyline=Polyline(vertices=[
            Vertex(k * _FACE_X - 4.0, k * _CREST_Y),
            Vertex(k * _FACE_X, k * _CREST_Y - 4.0)]))
        assert _tol(p) > 4.0 / 500, "the premise: slices under the tolerance"
        bad = []
        with p.regions_frozen():
            bare = slice_surface(p, wedge, num_slices=500)
            assert bare is not None
            for x in (bare.slices[0].base_x_left, bare.slices[250].base_x_left):
                p.line_loads = [_line(x, k * _CREST_Y)]
                sl = slice_surface(p, wedge, num_slices=500)
                got = _share_sum(sl, p.line_loads[0].id)
                if abs(got - 1.0) > 1e-12:
                    bad.append((x, got))
        assert not bad, bad


class TestOnce:
    """At the two ends and on three interior cuts (the first, the mandatory
    one at x = 10 and the last), at fractions of the tolerance. Every cut is
    the same code; the three are where a rule special-casing the first, a
    mandatory or the last interior cut would show."""

    _FRACTIONS = (-2.0, -0.5, 0.0, 0.5, 2.0)
    _SWEEPS = {}

    @classmethod
    def _sweep(cls, scale):
        if scale in cls._SWEEPS:
            return cls._SWEEPS[scale]
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipSurface
        p = _wall(scale=scale)
        surface = SlipSurface(polyline=Polyline(vertices=[
            Vertex(scale * v.x, scale * v.y)
            for v in _plane(vertex_x=10.0).polyline.vertices]))
        tol = _tol(p)
        bare = _sliced(p, surface)
        cuts = [s.base_x_left for s in bare.slices[1:]]
        assert 10.0 * scale in cuts, "the premise: the vertex is a cut"
        x_l, x_r = bare.slices[0].base_x_left, bare.slices[-1].base_x_right
        where = [("first cut", cuts[0]), ("cut at 10", 10.0 * scale),
                 ("last cut", cuts[-1]), ("x_l", x_l), ("x_r", x_r)]
        out = []
        for name, x0 in where:
            for f in cls._FRACTIONS:
                x = x0 + f * tol
                ld = _line(x, scale * _ground_y(x / scale))
                p.line_loads = [ld]
                got = _share_sum(_sliced(p, surface), ld.id)
                outside = ((name == "x_l" and f == -2.0)
                           or (name == "x_r" and f == 2.0))
                out.append((name, f, got, 0.0 if outside else 1.0))
        cls._SWEEPS[scale] = out
        return out

    def test_the_parts_add_up_to_one_load_or_none(self):
        bad = [r for r in self._sweep(1.0) if abs(r[2] - r[3]) > 1e-12]
        assert not bad, bad

    def test_in_millimetres_it_decides_the_same(self):
        metres = [(w, f, round(g, 12)) for w, f, g, _ in self._sweep(1.0)]
        mm = [(w, f, round(g, 12)) for w, f, g, _ in self._sweep(1000.0)]
        assert metres == mm, (metres, mm)


class TestTheExcessPorePressure:
    """Σ Δu·b over the slices is B̄·P times the part the slices carry: a
    load spread over the slice that carries it, and over no other."""

    @staticmethod
    def _excess(p, surface, ld):
        sl = _sliced(p, surface)
        return math.fsum(s.pore_pressure * s.width for s in sl.slices), sl

    @staticmethod
    def _loaded(ld, mirror=False):
        p = _wall(mirror)
        p.settings.groundwater.excess_pore_pressure = True
        p.materials[0].b_bar = 1.0
        p.line_loads = [ld]
        return p

    def test_on_an_interior_cut_it_counts_once(self):
        ld = _line(10.0, _CREST_Y, excess=True)
        got, _sl = self._excess(self._loaded(ld), _plane(vertex_x=10.0), ld)
        assert abs(got - _P) <= 1e-9 * _P, got

    def test_on_x_r_it_counts_and_below_the_exit_it_does_not(self):
        ld = _line(_FACE_X, _CREST_Y, excess=True)
        got, _sl = self._excess(self._loaded(ld), _plane(), ld)
        assert abs(got - _P) <= 1e-9 * _P, got
        ld = _line(_FACE_X, 2.0, excess=True)
        got, _sl = self._excess(self._loaded(ld), _circle(), ld)
        assert got == 0.0, got

    def test_a_design_standard_factors_it_once(self):
        """Through ``design_actions.refresh_pore_pressures``, which asks the
        excess again with each load's factor."""
        from ogr_core.project.design_factors import prepare_analysis_project
        ld = _line(10.0, _CREST_Y, excess=True)
        p = self._loaded(ld)
        ds = p.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da1c1")
        work, _report = prepare_analysis_project(p)
        got, sl = self._excess(work, _plane(vertex_x=10.0), ld)
        xi = sl.load_factors[ld.id][2]
        assert xi != 1.0, "the premise: the standard factors this load"
        assert abs(got - xi * _P) <= 1e-9 * _P, (got, xi)

    def test_a_design_standard_on_an_end_of_the_mass(self):
        """The same with the load on x_r: ``refresh_pore_pressures`` must
        know which slice is the last, or it gives half."""
        from ogr_core.project.design_factors import prepare_analysis_project
        ld = _line(_FACE_X, _CREST_Y, excess=True)
        p = self._loaded(ld)
        ds = p.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da1c1")
        work, _report = prepare_analysis_project(p)
        got, sl = self._excess(work, _plane(), ld)
        xi = sl.load_factors[ld.id][2]
        assert xi != 1.0, "the premise: the standard factors this load"
        assert abs(got - xi * _P) <= 1e-9 * _P, (got, xi)


class TestTheSwitch:
    """``LOAD_SHARE_AT_EDGES`` moves the numbers; off, the v0.1.458 rule."""

    def test_off_is_the_old_rule_and_on_is_not(self):
        import ogr_core.loads.overburden as ov
        saved = ov.LOAD_SHARE_AT_EDGES
        try:
            results = {}
            for on in (False, True):
                ov.LOAD_SHARE_AT_EDGES = on
                p = _wall()
                bare = _factors(p, _plane(), _TWO)
                p.line_loads = [_line(_FACE_X, _CREST_Y)]
                at_x_r = _factors(p, _plane(), _TWO)
                cut = _line(10.0, _CREST_Y, excess=True)
                q = TestTheExcessPorePressure._loaded(cut)
                excess, sl = TestTheExcessPorePressure._excess(
                    q, _plane(vertex_x=10.0), cut)
                parts = [part[2] for s in sl.slices for part in s.load_parts
                         if part[0] == cut.id]
                results[on] = (at_x_r == bare, parts, excess)
        finally:
            ov.LOAD_SHARE_AT_EDGES = saved
        lost, parts, excess = results[False]
        assert lost, "off: a load on x_r is on no slice"
        assert parts == [_P], parts
        assert abs(excess - 2.0 * _P) <= 1e-9 * _P, excess
        lost, parts, excess = results[True]
        assert not lost
        assert parts == [0.5 * _P, 0.5 * _P], parts
        assert abs(excess - _P) <= 1e-9 * _P, excess
