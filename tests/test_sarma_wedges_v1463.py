# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.463 (D357) — Sarma's method with non-vertical slices: the wedges.

WHAT THIS VERSION ADDS

``ogr_slip2d.sarma.wedges``: the sliding mass, already resolved and judged
by the slicer, cut into wedges by inclined faces, with each wedge's
weight, water and loads; and ``ogr_slip2d.sarma.angles``, the angle of a
face where nobody gives one. Still unregistered: no analysis runs it until
v0.1.464.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **Areas and weights in closed form**, to 1e-12: five wedges over two
   layers and a water table, against the wedge polygons written here by
   hand, cut by the contact and the water table with a clipper written
   here (Sutherland and Hodgman 1974), with the shoelace formula; a tilted
   contact across inclined faces, against the same clipper on a half-plane
   (the first version weighed those wedges whole, −1.3 %); and one wedge
   on a plane against F = (cL + (W cos α − U) tan φ)/(W sin α).
2. **Janbu's simplified method** (Janbu 1954, 1973), to 1e-12: vertical
   faces with no strength, built by the constructor with the slicer's own
   number of slices, are the slicer's slices (their boundaries are its
   cuts, every field the same), and their factor is the engine's
   ``JanbuSimplified`` on those slices: with a water table, ponded water,
   a surcharge, a line load on a cut and one inside, kh = 0.1 with
   kv = ±0.05, a water-filled crack, and mirrored.
3. **The base reads its column** (SHANSEP, Ladd and Foott 1974; a
   vertical-stress ratio): with inclined faces each base's c and tan φ are
   the ones Bishop's method reads on the vertical slice standing on that
   base, cut by the slicer, at the wedge's own Fellenius stress (Fellenius
   1936); read on the wedge instead, they move.
4. **The design standard**: Frank et al. (2004), §11.5, on a dry undrained
   slope with inclined faces: Γ = F/γG under DA1-C1 and F/γcu under DA1-C2;
   and Ru (Bishop and Morgenstern 1960) follows the factored weight along
   the bases, so a frictional slope with Ru keeps its factor; with γG and
   γG,fav apart a face reads the factor of the wedge it leans over.
5. **The published problems 4 and 5** of the verification manual (from
   Hoek 1987): 4 dry 1.198, 4 saturated 0.434 and 5 (γw = 1) 1.091, at
   ±1 %, in both senses of the shear; and the bank's independent tool
   (``_tools/cunas_sarma.py``, which solves the 2n equations directly) at
   1e-6, its weights included. Reducing only the bases misses them by
   +14.8 %, −58 % and +2.8 %: that fixes the convention.
6. **Loads count once, where they are**, and the ponded water is the
   water's: a line load on the top of a face goes half to each wedge, one
   at the corner of a vertical step to the wedge whose top that corner is,
   one inside the soil to the wedge that holds it; a pressure on a step
   by height; the ponded water adds up to γw·(water area) and ½γw·h²; and
   Ru under ponded water integrates as a fine quadrature of the program's
   own u, point by point.
7. **The mirror**: problem 4 reflected gives the same factor.
8. **Rule 7**: the policy, the face strength, the number of wedges, the
   cut at the contacts and each per-vertex datum move the number.
9. **Every refusal has its code**, and a malformed call is a ValueError,
   per-vertex data included.

Measured cost: about 1 s for the file (the slicer and Shapely; the
problems are two and nine wedges).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ----------------------------------------------------------------- problem 4
#: Problem 4 of the verification manual (from Hoek 1987), as the bank
#: transcribes it (``03_Sarma_Problema004/referencia.json`` and its
#: ``modelo.ogr``): the spoil heap on a sheared floor, the published slip
#: surface, and the interface from the kink to the face at x = 82.85, the
#: one the published 1.198 needs (D122). Both materials weigh 15.7 kN/m³.
_EXT4 = ((-50, -20), (250, -20), (250, 14.9), (229.545, 13.6815),
         (111.4, 76.5), (0, 0), (-50, -2.97))
_CONTACT4 = ((0, 0), (108, 6.4), (229.545, 13.6815))
_WT4 = ((-50, -2.97), (0, 0), (111.4, 76.5), (229.545, 13.6815), (250, 14.9))
_SURFACE4 = ((0, 0), (108, 6.4), (128, 67.6737))
_KINK4 = (108.0, 6.4)
#: The tool's interface rises from the kink to the GROUND at x = 82.85.
_THETA4 = math.degrees(math.atan2(76.5 * 82.85 / 111.4 - 6.4, 82.85 - 108.0))
_PUBLISHED4 = {False: 1.198, True: 0.434}
#: ``_tools/cunas_sarma.py`` of the bank (it does not import OGR), run on
#: 2026-11-15 (``test_sarma_solver_v1461``): the largest roots of problem 4
#: at full precision. Its U is Simpson's rule, 3.8e-7 off the exact
#: integral on the scarp, which moves the saturated F by 6e-8.
_TOOL4 = {False: 1.1983391299829478, True: 0.4346620085049817}

# ----------------------------------------------------------------- problem 5
#: Problem 5 (from Hoek 1987), as the bank transcribes it
#: (``03_Sarma_Problema005``): the ground, the water table, the vein with
#: vertex 3 at x = 29 on its straight stretch (the figure draws it there
#: unlabelled; the tool's declared reading), and table 5.2: the angle and
#: the c, φ of each interface at vertices 2 to 9. γ = 2.1 and γw = 1 (the
#: published units, ``unidades_fijadas``) or 9.81.
_EXT5 = ((4, 0), (204, 0), (204, 103), (180, 96), (166, 89), (140, 88),
         (50, 25), (30, 24), (29, 26), (17, 26), (4, 17))
_WT5 = ((4, 17), (17, 23), (30, 22), (50, 24), (70, 33), (146, 80),
        (165, 90), (178, 99), (204, 103))
_SURFACE5 = ((4, 17), (17, 12), (29, 12 - 24 / 13), (30, 10), (50, 8),
             (80, 11), (155, 65), (173, 80), (186, 89), (204, 103))
_TABLE52 = ((90.0, 2.0, 30.0),) * 4 + (
    (114.775, 0.0, 18.0), (123.111, 0.0, 18.0), (128.66, 0.0, 18.0),
    (128.66, 0.0, 18.0))
_PUBLISHED5 = 1.091
#: The same tool on problem 5, run on 2026-11-16 (``montar`` and
#: ``raices`` on the bank's ``modelo.ogr`` and ``modelo_gw981.ogr``, the
#: largest root, unrounded), by γw and sense; and its nine weights [t/m],
#: rounded to 1e-6 as it prints them.
_TOOL5 = {(1.0, "fixed"): 1.0882705296257265,
          (1.0, "kinematic"): 1.0890526340859257,
          (9.81, "fixed"): 0.8240171756597914,
          (9.81, "kinematic"): 0.8239735634030567}
_TOOL5_WEIGHTS = (191.1, 376.061538, 31.338462, 651.0, 1189.310326,
                  5315.444399, 922.106376, 340.868339, 217.52056)


def _pl(points, closed=False):
    from ogr_core.geometry import Polyline, Vertex
    return Polyline(vertices=[Vertex(x, y) for x, y in points],
                    closed=closed)


def _external(p, points):
    from ogr_core.geometry import Boundary, BoundaryType
    ext = _pl(points, closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))


def _water(p, points, materials):
    from ogr_core.geometry import Boundary, BoundaryType
    from ogr_core.materials import PorePressureType
    wt = Boundary(polyline=_pl(sorted(points)),
                  btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    for m in materials:
        m.pore_pressure = PorePressureType.WATER_TABLE
        m.water_surface_id = wt.id


def _problem4(wet, mirror=False):
    from ogr_core.geometry import Boundary, BoundaryType
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipSurface
    k = -1.0 if mirror else 1.0

    def m(pts):
        return sorted((k * x, y) for x, y in pts)
    p = Project("v1463 problem 4")
    _external(p, [(k * x, y) for x, y in _EXT4])
    p.add_boundary(Boundary(polyline=_pl(m(_CONTACT4)),
                            btype=BoundaryType.MATERIAL))
    floor = Material(name="Sheared Floor", unit_weight=15.7,
                     strength=MohrCoulomb(cohesion=10.0, friction_angle=6.0))
    spoil = Material(name="Spoil", unit_weight=15.7,
                     strength=MohrCoulomb(cohesion=100.0,
                                          friction_angle=42.0))
    p.materials = [floor, spoil]
    p.assign_material_at(k * 100.0, 40.0, spoil.id)
    if wet:
        _water(p, m(_WT4), (floor, spoil))
    p.settings.groundwater.pore_fluid_unit_weight = 9.81
    theta = 180.0 - _THETA4 if mirror else _THETA4
    return p, SlipSurface(polyline=_pl(m(_SURFACE4))), {
        (k * _KINK4[0], _KINK4[1]): theta}


def _problem5(gw):
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipSurface
    p = Project("v1463 problem 5")
    _external(p, _EXT5)
    m = Material(name="Material 1", unit_weight=2.1,
                 strength=MohrCoulomb(cohesion=2.0, friction_angle=30.0))
    p.materials = [m]
    _water(p, _WT5, (m,))
    p.settings.groundwater.pore_fluid_unit_weight = gw
    vertices = _SURFACE5[1:-1]
    return (p, SlipSurface(polyline=_pl(_SURFACE5)),
            {v: t[0] for v, t in zip(vertices, _TABLE52)},
            {v: t[1:] for v, t in zip(vertices, _TABLE52)})


def _wedges(p, surface, n=2, **kw):
    from ogr_slip2d.sarma.wedges import build_wedges
    from ogr_slip2d.slicer import slice_surface
    v = slice_surface(p, surface, num_slices=30)
    assert v is not None
    reasons = []
    w = build_wedges(p, surface, v, n, reasons=reasons, **kw)
    assert w is not None, reasons
    return w


def _f(w, kh=0.0, kv=0.0, sense="fixed"):
    from ogr_slip2d.sarma.wedges import solve_wedges
    sol = solve_wedges(w, kh, kv, shear_sense=sense, tolerance=1e-12)
    assert sol.converged and sol.fos is not None, sol.message
    return sol.fos


_CACHE: dict = {}


def _p4(wet, mirror=False):
    key = ("4", wet, mirror)
    if key not in _CACHE:
        p, s, angles = _problem4(wet, mirror)
        _CACHE[key] = _wedges(p, s, vertex_angles=angles)
    return _CACHE[key]


def _p5(gw):
    key = ("5", gw)
    if key not in _CACHE:
        p, s, angles, strengths = _problem5(gw)
        _CACHE[key] = _wedges(p, s, vertex_angles=angles,
                              vertex_strength=strengths)
    return _CACHE[key]


# ----------------------------------------------------------- the J slope
def _slope(*, mirror=False, crack=False, kh=0.0, kv=0.0, load=True,
           strength=None, ru=None, contact_y=None, surface=None,
           water_y=12.0):
    """A slope built for the slicer to be EXACT on it: a horizontal water
    table at y = 12 that ponds 2 m on the toe and on the slope up to x = 24
    and crosses no base inside a slice, the ground's vertices, the
    surcharge's start and the water's edge all at vertices of the surface,
    and straight bases, so a slice's midpoint rules are exact. ``ru``
    replaces the water by Ru; ``contact_y`` adds a horizontal contact;
    ``water_y`` = 6 puts the water table across two bases instead (x = 18
    and 45), where it is a cut of the slicer's."""
    from ogr_core.geometry import Boundary, BoundaryType, Vertex
    from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                 WaterLevelMode)
    from ogr_core.loads import DistributedLoad
    from ogr_core.loads.loads import LineLoad, LoadOrientation
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipSurface
    k = -1.0 if mirror else 1.0

    def m(pts):
        return sorted((k * x, y) for x, y in pts)
    p = Project("v1463 slope")
    _external(p, [(k * x, y) for x, y in ((0, 0), (80, 0), (80, 20),
                                          (40, 20), (20, 10), (0, 10))])
    soil = Material(name="soil", unit_weight=18.0, sat_unit_weight=20.0,
                    use_sat_unit_weight=True, strength=strength or MohrCoulomb(cohesion=10.0,
                                                     friction_angle=25.0))
    p.materials = [soil]
    if contact_y is not None:
        p.add_boundary(Boundary(polyline=_pl(m(((0, contact_y),
                                                (80, contact_y)))),
                                btype=BoundaryType.MATERIAL))
        hard = Material(name="hard", unit_weight=21.0,
                        strength=MohrCoulomb(cohesion=40.0,
                                             friction_angle=35.0))
        p.materials.append(hard)
        p.assign_material_at(k * 70.0, 0.5 * contact_y, hard.id)
        p.assign_material_at(k * 70.0, 19.0, soil.id)
    if ru is not None:
        for mat in p.materials:
            mat.pore_pressure = PorePressureType.RU_COEFFICIENT
            mat.ru = ru
    else:
        _water(p, m(((-5, water_y), (85, water_y))), p.materials)
    if load:
        a, b = m(((60, 20), (80, 20)))
        p.distributed_loads.append(DistributedLoad(
            start=Vertex(*a), end=Vertex(*b), magnitude_1=30.0,
            orientation=LoadOrientation.VERTICAL))
        for x in (60.0, 65.0):        # on a cut, and inside a slice
            p.line_loads.append(LineLoad(point=Vertex(k * x, 20.0),
                                         magnitude=50.0))
    if crack:
        p.add_boundary(Boundary(polyline=_pl(m(((-5, 16), (85, 16)))),
                                btype=BoundaryType.TENSION_CRACK))
        p.tension_crack_properties = TensionCrackProperties(
            mode=WaterLevelMode.FILLED)
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh, p.seismic.kv = kh, kv
    pts = surface or ((10, 10), (20, 5), (24, 4.5), (40, 4), (60, 12),
                      (70, 20))
    return p, SlipSurface(polyline=_pl(m(pts)))


# ======================================================================
def _clip_below(poly, y0):
    """The part of ``poly`` with y <= y0 (Sutherland and Hodgman 1974)."""
    out = []
    for i, (x1, y1) in enumerate(poly):
        x2, y2 = poly[(i + 1) % len(poly)]
        in1, in2 = y1 <= y0, y2 <= y0
        if in1:
            out.append((x1, y1))
        if in1 != in2:
            t = (y0 - y1) / (y2 - y1)
            out.append((x1 + t * (x2 - x1), y0))
    return out


def _shoelace(poly):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


class TestTheWeightIsTheArea:
    """A bathtub surface under flat ground at y = 10, two layers (contact
    at y = 5) and a water table at y = 7, with faces given at 60° and 135°
    at the two lower vertices and vertical at the water's crossings."""

    _TOP_60 = 30.0 + 8.0 / math.tan(math.radians(60.0))

    def _model(self):
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.surface import SlipSurface
        p = Project("v1463 bathtub")
        _external(p, ((0, 0), (100, 0), (100, 10), (0, 10)))
        p.add_boundary(Boundary(polyline=_pl(((0, 5), (100, 5))),
                                btype=BoundaryType.MATERIAL))
        lower = Material(name="lower", unit_weight=19.0, sat_unit_weight=21.0,
                         use_sat_unit_weight=True,
                         strength=MohrCoulomb(cohesion=5.0,
                                              friction_angle=30.0))
        upper = Material(name="upper", unit_weight=17.0, sat_unit_weight=19.5,
                         use_sat_unit_weight=True,
                         strength=MohrCoulomb(cohesion=5.0,
                                              friction_angle=30.0))
        p.materials = [lower, upper]
        p.assign_material_at(50.0, 8.0, upper.id)
        p.assign_material_at(50.0, 2.0, lower.id)
        _water(p, ((-1, 7), (101, 7)), (lower, upper))
        return p, SlipSurface(polyline=_pl(((10, 10), (30, 2), (60, 2),
                                            (80, 10))))

    def _by_hand(self):
        t = self._TOP_60
        return [[(10, 10), (17.5, 7), (17.5, 10)],
                [(17.5, 7), (30, 2), (t, 10), (17.5, 10)],
                [(30, 2), (60, 2), (52, 10), (t, 10)],
                [(60, 2), (72.5, 7), (72.5, 10), (52, 10)],
                [(72.5, 7), (80, 10), (72.5, 10)]]

    def _weight(self, poly):
        """γ by bands: lower below 5 (all wet), upper wet 5–7, dry 7–10."""
        below5 = _shoelace(_clip_below(poly, 5.0))
        below7 = _shoelace(_clip_below(poly, 7.0))
        total = _shoelace(poly)
        return 21.0 * below5 + 19.5 * (below7 - below5) + 17.0 * (
            total - below7)

    def test_three_layers_of_weight_by_hand(self):
        from ogr_slip2d.sarma.angles import VERTICAL
        p, s = self._model()
        w = _wedges(p, s, 2, angles=VERTICAL, boundaries_at_materials=False,
                    vertex_angles={(30.0, 2.0): 60.0, (60.0, 2.0): 135.0})
        polys = self._by_hand()
        assert [round(x, 9) for x in w.boundaries] == [10, 17.5, 30, 60,
                                                        72.5, 80]
        for wedge, poly in zip(w, polys):
            assert abs(wedge.area - _shoelace(poly)) <= 1e-12 * wedge.area
            want = self._weight(poly)
            assert abs(wedge.weight - want) <= 1e-12 * want, (
                wedge.index, wedge.weight, want)
            assert abs(wedge.width * wedge.height - wedge.area) <= (
                1e-12 * wedge.area)
        assert abs(w.faces[2].x_top - self._TOP_60) <= 1e-12 * 100
        assert abs(w.faces[3].x_top - 52.0) <= 1e-12 * 100

    def test_a_tilted_contact_across_inclined_faces(self):
        """The contact from (0, 3) to (80, 11) under the slope, faces by
        the bisector and at given angles: each wedge's weight against its
        own polygon cut by the half-plane below the contact, by the clipper
        here."""
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material, MohrCoulomb
        p, s = _slope(load=False, water_y=-50.0)
        p.add_boundary(Boundary(polyline=_pl(((0, 3), (80, 11))),
                                btype=BoundaryType.MATERIAL))
        hard = Material(name="hard", unit_weight=23.0,
                        strength=MohrCoulomb(cohesion=40.0,
                                             friction_angle=35.0))
        p.materials.append(hard)
        p.assign_material_at(70.0, 1.0, hard.id)
        p.assign_material_at(70.0, 19.0, p.materials[0].id)

        def below(poly):
            # the half-plane below the contact, by a rotation that makes it
            # horizontal: y' = y − (3 + 0.1·x)
            turned = [(x, y - 3.0 - 0.1 * x) for x, y in poly]
            return _shoelace(_clip_below(turned, 0.0))  # area-preserving
        crossed = 0
        for kw in ({}, dict(vertex_angles={(24.0, 4.5): 70.0,
                                           (40.0, 4.0): 105.0})):
            w = _wedges(p, s, 8, **kw)
            for wedge in w:
                poly = list(wedge.polygon)
                a_low = below(poly)
                want = 23.0 * a_low + 18.0 * (_shoelace(poly) - a_low)
                assert abs(wedge.weight - want) <= 1e-12 * want, (
                    kw, wedge.index, wedge.weight, want)
                if 0.0 < a_low < _shoelace(poly):
                    crossed += 1
        assert crossed >= 4        # the contact does cross wedges

    def test_one_wedge_on_a_plane_is_the_closed_form(self):
        """One wedge, a constant pore pressure u = 20 kPa: F =
        (cL + (W cos α − U) tan φ)/(W sin α)."""
        from ogr_core.materials import Material, MohrCoulomb, PorePressureType
        from ogr_core.project import Project
        from ogr_slip2d.surface import SlipSurface
        p = Project("v1463 plane")
        _external(p, ((0, -10), (60, -10), (60, 15), (40, 15), (20, 0),
                      (0, 0)))
        m = Material(name="soil", unit_weight=18.0,
                     strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0),
                     pore_pressure=PorePressureType.CONSTANT)
        m.constant_u = 20.0
        p.materials = [m]
        w = _wedges(p, SlipSurface(polyline=_pl(((20, 0), (50, 15)))), 1)
        assert len(w) == 1 and len(w.faces) == 2
        W = 18.0 * _shoelace([(20, 0), (50, 15), (40, 15)])
        L = math.hypot(30.0, 15.0)
        a = math.atan2(15.0, 30.0)
        U = 20.0 * L
        assert abs(w[0].weight - W) <= 1e-12 * W
        assert abs(w[0].pore_force - U) <= 1e-12 * U
        want = (5.0 * L + (W * math.cos(a) - U) * math.tan(math.radians(30)))\
            / (W * math.sin(a))
        assert abs(_f(w) - want) <= 1e-10 * want, (_f(w), want)


# ======================================================================
_JANBU = (
    ("water, ponding, surcharge and line loads", {}),
    ("kh 0.1 kv +0.05", dict(kh=0.1, kv=0.05)),
    ("kh 0.1 kv -0.05, mirrored", dict(kh=0.1, kv=-0.05, mirror=True)),
    ("a water-filled crack", dict(crack=True)),
    ("a water-filled crack, mirrored", dict(crack=True, mirror=True)),
    ("a water table across two bases", dict(water_y=6.0)),
)


class TestJanbuOnTheSlicersSlices:

    def test_vertical_faces_without_strength_are_janbu(self):
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.sarma.angles import VERTICAL
        from ogr_slip2d.sarma.wedges import NO_STRENGTH, build_wedges
        from ogr_slip2d.slicer import slice_surface
        seen = set()
        for label, kw in _JANBU:
            for n in (12, 25):
                p, s = _slope(**kw)
                v = slice_surface(p, s, num_slices=n)
                w = build_wedges(p, s, v, n, angles=VERTICAL,
                                 face_strength=NO_STRENGTH)
                # the constructor's boundaries are the slicer's cuts, and
                # vertical faces on them are its slices, field by field
                assert [x.base_x_left for x in w] == [x.base_x_left
                                                      for x in v], label
                # The crack's water is the thrust on the head face of the
                # wedges, and a horizontal force on the slicer's wall slice.
                wall = {}
                if v.tension_crack_force:
                    end = 0 if kw.get("mirror") else len(v) - 1
                    wall[end] = (v.tension_crack_force
                                 * (1.0 if kw.get("mirror") else -1.0))
                for a, b in zip(w, v):
                    for name in ("weight", "soil_weight", "water_weight",
                                 "water_force_h", "pore_pressure"):
                        x, y = getattr(a, name), getattr(b, name)
                        if name == "water_force_h":
                            x += wall.get(a.index, 0.0)
                        assert abs(x - y) <= 1e-12 * max(1.0, abs(y)), (
                            label, n, a.index, name, x, y)
                janbu = method_registry()["janbu_simplified"]()
                janbu.tolerance = 1e-12
                want = janbu.compute_fos(p, s, v).fos
                got = _f(w, p.seismic.kh if p.seismic.enabled else 0.0,
                         p.seismic.kv if p.seismic.enabled else 0.0)
                assert abs(got - want) <= 1e-12 * want, (label, n, got, want)
                if w.tension_crack_force:
                    seen.add("crack")
                    # the crack's water is the thrust on the head face,
                    # not a force on a base
                    from ogr_slip2d.sarma.wedges import to_solver
                    s_in = to_solver(w)
                    assert s_in.head_thrust == v.tension_crack_force
                    assert [x.force_x for x in s_in.bases] == [
                        x.water_force_h for x in w]
                if any(x.water_weight > 0.0 for x in w):
                    seen.add("ponded")
                if any(lp[0] for x in w for lp in x.load_parts):
                    seen.add("loads")
                if any(abs(x - 18.0) < 1e-9 for x in w.boundaries):
                    seen.add("water cut")
        assert seen == {"crack", "ponded", "loads", "water cut"}, seen

    def test_a_curved_envelope_read_where_janbu_reads_it(self):
        """A power-curve envelope, read once at the Fellenius estimate of
        each base (the fixed point at the method's own stress switched
        off, as Janbu then reads it): through the constructor, the same."""
        from ogr_core.materials.builtin_models import PowerCurve
        from ogr_slip2d.methods import base, method_registry
        from ogr_slip2d.sarma.angles import VERTICAL
        from ogr_slip2d.sarma.wedges import NO_STRENGTH, build_wedges
        from ogr_slip2d.slicer import slice_surface
        old = base.ENVELOPE_AT_OWN_STRESS
        base.ENVELOPE_AT_OWN_STRESS = False
        try:
            p, s = _slope(strength=PowerCurve(a=1.107, b=0.86, c=4.0, d=0.0,
                                              waviness=0.0))
            v = slice_surface(p, s, num_slices=12)
            janbu = method_registry()["janbu_simplified"]()
            janbu.tolerance = 1e-12
            want = janbu.compute_fos(p, s, v).fos
        finally:
            base.ENVELOPE_AT_OWN_STRESS = old
        w = build_wedges(p, s, v, 12, angles=VERTICAL,
                         face_strength=NO_STRENGTH)
        from ogr_slip2d.sarma.wedges import to_solver
        assert len({round(x.tan_phi, 9) for x in to_solver(w).bases}) > 3
        got = _f(w)
        assert abs(got - want) <= 1e-12 * want, (got, want)


# ======================================================================
class TestTheBaseReadsItsColumn:

    def _check(self, strength):
        from ogr_core.materials.strength_model import local_c_phi
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.sarma.wedges import to_solver
        from ogr_slip2d.slicer import slice_surface
        p, s = _slope(strength=strength)
        w = _wedges(p, s, 8, face_strength=(5.0, 20.0))
        assert any(abs(f.delta) > 0.05 for f in w.faces)   # inclined
        cols = slice_surface(p, s, cuts=w.boundaries)
        moved = 0.0
        for b, wedge, col in zip(to_solver(w).bases, w, cols):
            f = slice_forces(wedge)
            sigma = max(0.0, f.w_total * math.cos(wedge.base_angle)
                        - wedge.pore_force) / wedge.base_length
            c, t = local_c_phi(col, col.material, sigma)
            assert abs(b.cohesion - c) <= 1e-12 * max(1.0, c)
            assert abs(b.tan_phi - t) <= 1e-12 * max(1.0, t)
            c_w, _t = local_c_phi(wedge, col.material, sigma)
            moved = max(moved, abs(c_w - c) / max(c, 1e-9))
        return moved

    def test_shansep(self):
        from ogr_core.materials.builtin_models import SHANSEP
        assert self._check(SHANSEP(S=0.25, m=0.8, OCR=2.0, A=5.0)) > 1e-3

    def test_a_vertical_stress_ratio(self):
        from ogr_core.materials.builtin_models import VerticalStressRatio
        assert self._check(VerticalStressRatio(K=0.4,
                                               min_strength=2.0)) > 1e-3


# ======================================================================
class TestTheDesignStandard:

    def _phi0(self, preset=None, single=True):
        import test_tension_crack_truncation_v1109 as U
        from ogr_core.materials.builtin_models import Undrained
        from ogr_core.project.design_factors import prepare_analysis_project
        from ogr_slip2d.sarma.wedges import NO_STRENGTH
        from ogr_slip2d.surface import SlipCircle
        p = U._phi0_slope(crack_y=None)
        p.materials[0].strength = Undrained(cohesion=U._C)
        if preset is not None:
            ds = p.settings.design_standard
            ds.enabled = True
            assert ds.apply_preset(preset)
            ds.single_source_weight = single
        work, _rep = prepare_analysis_project(p)
        w = _wedges(work, SlipCircle(centre_x=55.0, centre_y=58.0,
                                     radius=34.0), 12,
                    face_strength=NO_STRENGTH)
        assert any(abs(f.delta) > 0.05 for f in w.faces)
        return _f(w)

    def test_frank_et_al_on_inclined_faces(self):
        """Frank et al. (2004), §11.5: Γ = F/(γG·γcu)."""
        F = self._phi0()
        for preset, divisor in (("eurocode7_da1c1", 1.35),
                                ("eurocode7_da1c2", 1.4)):
            got = self._phi0(preset)
            assert abs(got - F / divisor) <= 5e-9 * F, (preset, got, F)

    def test_a_face_reads_the_factor_of_the_wedge_it_leans_over(self):
        """γG on the wedges that drive and γG,fav = 1 on the rest: Ru on a
        face scales by the factor of the wedge above it, the one it leans
        over (the column above an inclined face lies in that wedge)."""
        from ogr_core.materials import MohrCoulomb
        from ogr_core.project.design_factors import prepare_analysis_project
        out = {}
        for preset in (None, "eurocode7_da1c1"):
            p, s = _slope(ru=0.3, load=False,
                          strength=MohrCoulomb(cohesion=0.0,
                                               friction_angle=30.0))
            if preset:
                ds = p.settings.design_standard
                ds.enabled = True
                assert ds.apply_preset(preset)
                ds.single_source_weight = False
            work, _rep = prepare_analysis_project(p)
            out[preset] = _wedges(work, s, 1,
                                  vertex_angles={(24.0, 4.5): 60.0,
                                                 (40.0, 4.0): 125.0})
        char, design = out[None], out["eurocode7_da1c1"]
        factors = [x.weight_factor for x in design]
        assert len(set(factors)) == 2, factors                # premise
        seen = set()
        for a, b_ in zip(char.faces[1:-1], design.faces[1:-1]):
            k = a.index
            if abs(a.theta - 0.5 * math.pi) <= 1e-12:
                continue
            over = factors[k - 1] if a.theta < 0.5 * math.pi else factors[k]
            seen.add(over)
            assert abs(b_.water_force - over * a.water_force) <= (
                1e-12 * b_.water_force), (k, b_.water_force, a.water_force)
        assert len(seen) == 2, seen

    def test_ru_follows_the_factored_weight(self):
        """c′ = 0 with Ru: weight and pore pressure both × γG, F stays."""
        from ogr_core.materials import MohrCoulomb
        from ogr_core.project.design_factors import prepare_analysis_project
        out = {}
        for preset in (None, "eurocode7_da1c1"):
            p, s = _slope(ru=0.3, load=False,
                          strength=MohrCoulomb(cohesion=0.0,
                                               friction_angle=30.0))
            if preset:
                ds = p.settings.design_standard
                ds.enabled = True
                assert ds.apply_preset(preset)
                ds.single_source_weight = True
            work, _rep = prepare_analysis_project(p)
            out[preset] = _wedges(work, s, 8)
        char, design = out[None], out["eurocode7_da1c1"]
        for a, b in zip(char, design):
            assert b.weight_factor == 1.35
            assert abs(b.pore_force - 1.35 * a.pore_force) <= (
                1e-12 * b.pore_force)
        F, G = _f(char), _f(design)
        assert abs(G - F) <= 5e-9 * F, (F, G)


# ======================================================================
class TestThePublishedCases:

    def test_problem_4(self):
        for wet in (False, True):
            w = _p4(wet)
            assert [x.material.name for x in w] == ["Sheared Floor", "Spoil"]
            for sense in ("fixed", "kinematic"):
                F = _f(w, sense=sense)
                assert abs(F / _PUBLISHED4[wet] - 1.0) <= 0.01, (wet, F)
                assert abs(F - _TOOL4[wet]) <= 1e-6, (wet, sense, F)

    def test_problem_5(self):
        for gw in (1.0, 9.81):
            w = _p5(gw)
            assert len(w) == 9 and not w.unused_vertex_data
            assert [round(x.weight, 6) for x in w] == list(_TOOL5_WEIGHTS)
            for sense in ("fixed", "kinematic"):
                F = _f(w, sense=sense)
                assert abs(F - _TOOL5[gw, sense]) <= 1e-6, (gw, sense, F)
                if gw == 1.0:
                    assert abs(F / _PUBLISHED5 - 1.0) <= 0.01, (sense, F)

    def test_reducing_only_the_bases_misses_the_published(self):
        """Sarma's 1973 vertical-slice method divides only the bases'
        strength: here as a fixed point, the faces' strength multiplied
        back by F until F stops moving."""
        from ogr_slip2d.sarma.solver import Face, solve
        from ogr_slip2d.sarma.wedges import to_solver
        cases = ((_p4(False), _PUBLISHED4[False], 0.148),
                 (_p4(True), _PUBLISHED4[True], -0.580),
                 (_p5(1.0), _PUBLISHED5, 0.028))
        for w, published, want in cases:
            s = to_solver(w)
            F = _f(w)
            for _ in range(200):
                undivided = [Face(x.delta, x.length, x.water_force,
                                  x.cohesion * F, x.tan_phi * F)
                             for x in s.faces]
                F_next = solve(s.bases, undivided, slide_sign=s.slide_sign,
                               tolerance=1e-12).fos
                if abs(F_next - F) <= 1e-12:
                    break
                F = F_next
            off = F_next / published - 1.0
            assert abs(off - want) <= 0.005, (published, F_next, off)

    def test_the_mirror(self):
        for wet in (False, True):
            for sense in ("fixed", "kinematic"):
                a, b = _f(_p4(wet), sense=sense), _f(_p4(wet, True),
                                                     sense=sense)
                assert abs(a - b) <= 1e-9 * a, (wet, sense, a, b)


# ======================================================================
class TestFacesOnAStraightStretch:
    """Two wedges on one straight base of one material add up to the
    wedge they split: their two force balances sum to its one, with the
    forces on the face between them cancelling, and that sum and its
    unknowns (N′ and F) close by themselves. So a face on such a stretch
    leaves F where it was, at any angle, with any strength and any water:
    the equilibrium of rigid bodies, not a property of this code."""

    def test_more_faces_on_the_straight_stretches_change_nothing(self):
        p, s = _slope(kh=0.1, kv=0.05)
        F = _f(_wedges(p, s, 1), 0.1, 0.05)
        on_the_stretch = (48.0, 7.2)          # a division, not a vertex
        for n, kw in ((8, {}), (14, {}),
                      (14, dict(vertex_angles={on_the_stretch: 99.0})),
                      (14, dict(vertex_strength={on_the_stretch:
                                                 (30.0, 40.0)}))):
            w = _wedges(p, s, n, **kw)
            assert len(w) > 5 and not w.unused_vertex_data, (n, kw)
            got = _f(w, 0.1, 0.05)
            assert abs(got - F) <= 1e-10 * F, (n, kw, got, F)
        # the premise: the same data on a vertex of the surface moves it
        moved = _f(_wedges(p, s, 14, vertex_strength={(40.0, 4.0):
                                                      (30.0, 40.0)}),
                   0.1, 0.05)
        assert abs(moved - F) > 1e-3 * F


# ======================================================================
class TestLoadsOnTheTop:

    def test_a_line_load_on_a_face_top_goes_half_to_each(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad
        p, s = _slope(load=False)
        w = _wedges(p, s, 8)
        face = next(f for f in w.faces[1:-1] if abs(f.delta) > 0.05)
        p.line_loads.append(LineLoad(point=Vertex(face.x_top, face.y_top),
                                     magnitude=100.0))
        loaded = _wedges(p, s, 8)
        added = [b.weight - a.weight for a, b in zip(w, loaded)]
        k = face.index
        assert abs(added[k - 1] - 50.0) <= 1e-9 and abs(added[k] - 50.0) \
            <= 1e-9, added
        assert abs(sum(added) - 100.0) <= 1e-9

    def test_the_surcharge_is_the_loads(self):
        """30 kPa from x = 60 to the head of the mass at x = 70, whatever
        the faces: 300 kN/m, cut where a top straddles its start."""
        from ogr_slip2d.sarma.angles import POLICIES
        for policy in POLICIES:
            p, s = _slope()
            w = _wedges(p, s, 8, angles=policy)
            (load,) = p.distributed_loads
            surcharge = sum(lp[2] for x in w for lp in x.load_parts
                            if lp[0] == load.id)
            assert abs(surcharge - 300.0) <= 1e-9, (policy, surcharge)
            # and the two line loads of 50, at x = 60 and 65, once each
            total = sum(x.weight - x.soil_weight for x in w)
            assert abs(total - 400.0) <= 1e-9, (policy, total)

    def _step(self):
        """A vertical step from (50, 10) to (50, 20), and a face given from
        (70, 2) to (50, 12), half way up it."""
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.surface import SlipSurface
        p = Project("v1463 step")
        _external(p, ((0, 0), (100, 0), (100, 20), (50, 20), (50, 10),
                      (0, 10)))
        p.materials = [Material(name="soil", unit_weight=18.0,
                                strength=MohrCoulomb(cohesion=10.0,
                                                     friction_angle=30.0))]
        s = SlipSurface(polyline=_pl(((20, 10), (40, 2), (70, 2), (90, 20))))
        angles = {(70.0, 2.0): math.degrees(math.atan2(10.0, -20.0)),
                  (40.0, 2.0): 90.0}
        return p, s, angles

    def test_on_a_vertical_step_a_load_goes_where_it_is(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad
        from ogr_core.loads.loads import LineLoad, LoadOrientation
        p, s, angles = self._step()
        bare = _wedges(p, s, 1, vertex_angles=angles)
        assert abs(bare.faces[2].x_top - 50.0) <= 1e-12 * 100
        assert abs(bare.faces[2].y_top - 12.0) <= 1e-12 * 100
        for point, want in (((50.0, 20.0), [0, 0, 500]),   # crest corner
                            ((50.0, 10.0), [0, 500, 0]),   # toe corner
                            ((50.0, 12.0), [0, 250, 250])):  # the face top
            p, s, angles = self._step()
            p.line_loads.append(LineLoad(point=Vertex(*point),
                                         magnitude=500.0))
            w = _wedges(p, s, 1, vertex_angles=angles)
            added = [b_.weight - a_.weight for a_, b_ in zip(bare, w)]
            assert all(abs(x - y) <= 1e-9 for x, y in zip(added, want)), (
                point, added)
        p, s, angles = self._step()
        p.distributed_loads.append(DistributedLoad(
            start=Vertex(50.0, 10.0), end=Vertex(50.0, 20.0),
            magnitude_1=50.0, orientation=LoadOrientation.HORIZONTAL))
        w = _wedges(p, s, 1, vertex_angles=angles)
        pushed = [x.water_force_h for x in w]
        # 50 kPa on 2 m of the middle wedge's top and on 8 m of the last's
        assert all(abs(abs(x) - y) <= 1e-9 for x, y in zip(pushed,
                                                           (0, 100, 400))), \
            pushed

    def test_a_load_inside_the_soil_goes_to_the_wedge_that_holds_it(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad
        from shapely.geometry import Point, Polygon
        p, s = _slope(load=False)
        bare = _wedges(p, s, 8)
        face = next(f for f in bare.faces[1:-1] if f.theta < 0.45 * math.pi)
        k = face.index
        # a point just on the head side of a face leaning toward +x, low
        # down: inside wedge k, under the top of wedge k − 1
        point = (face.x_base + 0.3 * (face.x_top - face.x_base) + 0.2,
                 face.y_base + 0.3 * (face.y_top - face.y_base))
        holder = next(i for i, x in enumerate(bare)
                      if Polygon(x.polygon).contains(Point(point)))
        assert holder == k and point[0] < face.x_top   # premise
        p.line_loads.append(LineLoad(point=Vertex(*point), magnitude=300.0))
        w = _wedges(p, s, 8)
        added = [b_.weight - a_.weight for a_, b_ in zip(bare, w)]
        assert abs(added[k] - 300.0) <= 1e-9 and abs(sum(added) - 300.0) \
            <= 1e-9, added

    def test_ru_under_ponded_water_is_the_programs_u(self):
        """U on every base and PW on every face against a fine midpoint
        rule of ``pore_pressure_at`` itself, point by point: the bend where
        the ponding level meets the ground is no vertex of anything."""
        from ogr_core.geometry import Vertex
        from ogr_core.geometry.ground import envelope_y_at
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        from ogr_slip2d import slicer
        from ogr_core.geometry import Boundary, BoundaryType
        p, s = _slope(load=False, ru=0.3)
        # a water table that ponds 2.5 m on the toe and that no material
        # reads: Ru carries the water inside the soil
        p.add_boundary(Boundary(polyline=_pl(((-5, 12.5), (85, 12.5))),
                                btype=BoundaryType.WATER_TABLE))
        from ogr_slip2d.sarma.angles import VERTICAL
        w = _wedges(p, s, 1, angles=VERTICAL,
                    vertex_angles={(24.0, 4.5): 60.0, (40.0, 4.0): 125.0})
        ground = slicer._ground_surface_from_external(p.external_boundary())
        m = p.materials[0]

        def brute(a, b_, n=3000):
            L = math.hypot(b_[0] - a[0], b_[1] - a[1])
            tot = 0.0
            for i in range(n):
                t = (i + 0.5) / n
                x, y = a[0] + t * (b_[0] - a[0]), a[1] + t * (b_[1] - a[1])
                tot += pore_pressure_at(p, Vertex(x, y), m,
                                        ground_surface_y=envelope_y_at(
                                            ground, x))
            return tot * L / n
        for x in w:
            want = brute((x.base_x_left, x.base_y_left),
                         (x.base_x_right, x.base_y_right))
            assert abs(x.pore_force - want) <= 2e-5 * want, (
                x.index, x.pore_force, want)
        for f in w.faces[1:-1]:
            want = brute((f.x_base, f.y_base), (f.x_top, f.y_top))
            assert abs(f.water_force - want) <= 2e-5 * want, (
                f.index, f.water_force, want)
        assert any(x.water_weight > 0.0 for x in w)          # it ponds

    def test_the_ponded_water_is_the_waters(self):
        """2 m on the toe from x = 10 and down to nothing at x = 24 on the
        slope: γw·24 down, and ½γw·2² against the slope, whatever the
        faces."""
        from ogr_slip2d.sarma.angles import POLICIES
        for policy in POLICIES:
            w = _wedges(*_slope(load=False), 8, angles=policy)
            gw = 9.81
            down = sum(x.water_weight for x in w)
            across = sum(x.water_force_h for x in w)
            assert abs(down - gw * 24.0) <= 1e-9 * gw * 24.0, (policy, down)
            assert abs(across - 0.5 * gw * 4.0) <= 1e-9 * gw, (policy,
                                                                across)


# ======================================================================
class TestEveryOptionMovesTheNumber:

    def test_each_option(self):
        from ogr_slip2d.sarma.angles import MEAN_NORMAL, VERTICAL
        from ogr_slip2d.sarma.wedges import NO_STRENGTH
        p, s = _slope(load=False)
        base = _f(_wedges(p, s, 8))
        options = {
            "vertical": dict(angles=VERTICAL),
            "mean normal": dict(angles=MEAN_NORMAL),
            "no face strength": dict(face_strength=NO_STRENGTH),
            "given face strength": dict(face_strength=(2.0, 15.0)),
            "vertex angle": dict(vertex_angles={(40.0, 4.0): 90.0}),
            "vertex strength": dict(vertex_strength={(40.0, 4.0):
                                                     (0.0, 5.0)}),
        }
        for label, kw in options.items():
            got = _f(_wedges(p, s, 8, **kw))
            assert abs(got - base) > 1e-4 * base, (label, got, base)
        p, s = _slope(load=False, contact_y=7.0)
        on, off = (_wedges(p, s, 2, boundaries_at_materials=b)
                   for b in (True, False))
        assert len(on) > len(off)
        assert abs(_f(on) - _f(off)) > 1e-4 * _f(on)

    def test_the_number_of_wedges_on_a_circle(self):
        """On a circle the bases are chords, and more wedges are another
        surface (on a straight stretch of one material they are not: see
        ``TestFacesOnAStraightStretch``)."""
        from ogr_slip2d.sarma.wedges import NO_STRENGTH
        import test_tension_crack_truncation_v1109 as U
        from ogr_slip2d.surface import SlipCircle
        p = U._phi0_slope(crack_y=None)
        a, b = (_f(_wedges(p, SlipCircle(centre_x=55.0, centre_y=58.0,
                                         radius=34.0), n,
                           face_strength=NO_STRENGTH)) for n in (8, 16))
        assert abs(a - b) > 1e-4 * a, (a, b)

    def test_a_face_across_a_contact_takes_the_mean_by_length(self):
        """Mohr–Coulomb on both sides: c̄ and tan φ̄ are the means weighted
        by the length of the face in each (soil c = 10, φ = 25 over the
        contact at y = 7; hard c = 40, φ = 35 under it)."""
        p, s = _slope(load=False, contact_y=7.0)
        w = _wedges(p, s, 2)
        crossing = [f for f in w.faces[1:-1] if f.y_base < 7.0 < f.y_top]
        assert crossing
        for f in crossing:
            low = (7.0 - f.y_base) / (f.y_top - f.y_base)
            c = 40.0 * low + 10.0 * (1.0 - low)
            t = (math.tan(math.radians(35.0)) * low
                 + math.tan(math.radians(25.0)) * (1.0 - low))
            assert abs(f.cohesion - c) <= 1e-9 * c, (f.index, f.cohesion, c)
            assert abs(f.tan_phi - t) <= 1e-12, (f.index, f.tan_phi, t)

    def test_a_vertex_s_strength_comes_before_the_given_one(self):
        p, s = _slope(load=False)
        w = _wedges(p, s, 1, face_strength=(2.0, 15.0),
                    vertex_strength={(40.0, 4.0): (7.0, 11.0)})
        by_x = {round(f.x_base, 9): f for f in w.faces[1:-1]}
        assert by_x[40.0].strength_source == "vertex"
        assert by_x[40.0].cohesion == 7.0
        assert by_x[24.0].strength_source == "given"
        assert by_x[24.0].cohesion == 2.0

    def test_the_policies_by_hand(self):
        """At the kink (40, 4) between a base falling 0.5 in 16 m and one
        rising 8 in 20 m: the bisector at 90° + (α₁ + α₂)/2, the mean
        normal along l₁n₁ + l₂n₂."""
        from ogr_slip2d.sarma.angles import BISECTOR, MEAN_NORMAL, VERTICAL
        a1, a2 = math.atan2(-0.5, 16.0), math.atan2(8.0, 20.0)
        l1, l2 = math.hypot(16.0, 0.5), math.hypot(20.0, 8.0)
        want = {
            VERTICAL: 0.5 * math.pi,
            BISECTOR: 0.5 * math.pi + 0.5 * (a1 + a2),
            MEAN_NORMAL: math.atan2(l1 * math.cos(a1) + l2 * math.cos(a2),
                                    -l1 * math.sin(a1) - l2 * math.sin(a2))}
        p, s = _slope(load=False)
        for policy, theta in want.items():
            w = _wedges(p, s, 1, angles=policy)
            f = next(f for f in w.faces if round(f.x_base, 9) == 40.0)
            assert abs(f.theta - theta) <= 1e-12, (policy, f.theta, theta)
            assert f.angle_source == policy
        assert abs(want[BISECTOR] - want[MEAN_NORMAL]) > 1e-3   # premise

    def test_only_the_line_of_a_given_angle_counts(self):
        p, s, angles = _problem4(False)
        turned = {k: v + 180.0 for k, v in angles.items()}
        assert abs(_f(_wedges(p, s, vertex_angles=turned)) - _f(_p4(False)))             <= 1e-12 * _f(_p4(False))

    def test_data_for_a_vertex_the_surface_has_not(self):
        p, s = _slope(load=False)
        w = _wedges(p, s, 8, vertex_angles={(41.0, 4.0): 70.0})
        assert w.unused_vertex_data == [("angle", (41.0, 4.0))]


# ======================================================================
class TestEveryRefusalHasItsCode:

    def _refused(self, p, s, n=1, **kw):
        from ogr_slip2d.sarma.wedges import build_wedges
        from ogr_slip2d.slicer import slice_surface
        v = slice_surface(p, s, num_slices=30)
        assert v is not None
        reasons = []
        assert build_wedges(p, s, v, n, reasons=reasons, **kw) is None
        assert len(reasons) == 1, reasons
        return reasons[0]

    def test_each(self):
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.materials.builtin_models import Undrained
        from ogr_slip2d import messages as msg
        from ogr_slip2d.sarma.angles import VERTICAL
        p, s = _slope(load=False)
        p.settings.groundwater.excess_pore_pressure = True
        assert self._refused(p, s)[0] == msg.SARMA_EXCESS_PORE_PRESSURE
        p, s = _slope(load=False)
        code, args = self._refused(p, s, vertex_angles={(40.0, 4.0): 180.0})
        assert code == msg.SARMA_FACE_HORIZONTAL and args["face"] == 4
        code, args = self._refused(p, s, vertex_angles={(60.0, 12.0): 10.0})
        assert code == msg.SARMA_FACE_NO_EXIT and args["face"] == 5
        code, args = self._refused(p, s, vertex_angles={(24.0, 4.5): 30.0,
                                                        (40.0, 4.0): 150.0})
        assert code == msg.SARMA_FACES_CROSS and args == {"face": 3,
                                                          "next": 4}
        p, s = _slope(load=False, surface=(
            (10, 10), (20, 5), (24, 4.5), (40, 4), (60, 12), (64, 17),
            (66, 15), (70, 20)))
        code, args = self._refused(p, s, angles=VERTICAL, vertex_angles={
            (60.0, 12.0): 45.0, (64.0, 17.0): 30.0, (66.0, 15.0): 54.0})
        assert code == msg.SARMA_WEDGE_INVALID and args == {"wedge": 5}
        p, s = _slope(load=False)
        gone = Material(name="gone", unit_weight=18.0,
                        strength=MohrCoulomb(cohesion=1.0,
                                             friction_angle=1.0))
        p.materials.append(gone)
        p.add_boundary(Boundary(polyline=_pl(((50, 15), (52, 15), (52, 17),
                                              (50, 17)), closed=True),
                                btype=BoundaryType.MATERIAL))
        p.assign_material_at(51.0, 16.0, gone.id)
        p.materials.remove(gone)
        code, args = self._refused(p, s)
        assert code == msg.SARMA_WEDGE_OUTSIDE, (code, args)
        p, s = _slope(load=False, strength=Undrained(cohesion=30.0))
        code, args = self._refused(p, s)
        assert code == msg.SARMA_FACE_STRENGTH and args["material"] == "soil"

    def test_every_code_has_its_sentence(self):
        from ogr_slip2d import messages as msg
        for code in (msg.SARMA_EXCESS_PORE_PRESSURE,
                     msg.SARMA_FACE_HORIZONTAL, msg.SARMA_FACE_NO_EXIT,
                     msg.SARMA_FACES_CROSS, msg.SARMA_WEDGE_INVALID,
                     msg.SARMA_WEDGE_OUTSIDE, msg.SARMA_FACE_STRENGTH):
            assert code.startswith("lem.sarma_")
            assert msg.text(code, face=2, next=3, wedge=1, angle=12.5,
                            material="m") != code

    def test_a_malformed_call_is_an_error(self):
        from ogr_slip2d.sarma.wedges import build_wedges
        from ogr_slip2d.slicer import slice_surface
        p, s = _slope(load=False)
        v = slice_surface(p, s, num_slices=30)
        for kw in (dict(angles="radial"), dict(face_strength="average"),
                   dict(face_strength=(5.0, 90.0)),
                   dict(face_strength=(-1.0, 20.0)), dict(num_wedges=0)):
            args = dict(num_wedges=4)
            args.update(kw)
            try:
                build_wedges(p, s, v, **args)
            except ValueError:
                continue
            raise AssertionError(kw)
        for bad in (None, []):
            try:
                build_wedges(p, s, bad)
            except ValueError:
                continue
            raise AssertionError(bad)
        for kw in (dict(vertex_strength={(40.0, 4.0): (-5.0, 20.0)}),
                   dict(vertex_strength={(40.0, 4.0): (5.0, 95.0)}),
                   dict(vertex_strength={(40.0, 4.0): (math.nan, 20.0)}),
                   dict(vertex_angles={(40.0, 4.0): math.nan}),
                   dict(vertex_angles={(40.0, 4.0): 80.0,
                                       (40.0 + 1e-9, 4.0): 85.0})):
            try:
                build_wedges(p, s, v, 4, **kw)
            except ValueError:
                continue
            raise AssertionError(kw)
        for cuts in ((10.0, 30.0), (10.0, 50.0, 40.0, 70.0), (70.0,)):
            try:
                slice_surface(p, s, cuts=cuts)
            except ValueError:
                continue
            raise AssertionError(cuts)
