# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.217 — the Ordinary Method under a reservoir: a submerged slope has the
factor of the same slope with buoyant weights, at any water depth, on a
circle and on a polyline (defects D199 and D213).

THE IDENTITIES (rule 1).

* Total weights plus the water's boundary pressures and pore pressures must
  give the factor of the buoyant weights with no water at all: Duncan &
  Wright (2005), the case of their Fig. 6.27 (verification problem 70, 30 and
  60 ft of water over the crest, 1.60 by Bishop, Spencer and GLE), and
  Duncan, Wright & Brandon (2014), Section 14.6: "Both approaches should
  give the same factor of safety". With c = 0 that is "submerged = dry":
  the factor of a cohesionless slope does not depend on the unit weight.
* The two ways USACE EM 1110-2-1902 (2003), Appendix C, lets external water
  be modelled -- an external load on the slice tops, or a "soil" with
  c = phi = 0 and the unit weight of water through which the surface runs up
  to the water level -- must give the same factor (Duncan, Wright & Brandon
  2014, Section 14.6, list them as a check of a program). Bishop, the
  control, already agrees; the Ordinary Method did not.

WHAT WAS WRONG. The Ordinary Method resolved the ponded water's pressure on
the slice top WHOLE on the base normal, ``P*cos(a - b)``, which is Eq. C-14
of the EM. But the strength side is C-12: the effective weight ``W - u*b``,
the VERTICAL component of the base's pore force, resolved on the base. The
horizontal component of the top pressure was kept while its counterpart on
the base was dropped, so a uniform rise of the reservoir, which changes no
effective stress, raised the factor: 1.826 at 30 ft and 2.100 at 60 ft on
the circle of problem 70, against 1.513 with buoyant weights (Bishop 1.600).
D199 takes the pond's horizontal thrust out of the normal the strength is
read at (the water enters by its vertical components, as in Duncan, Wright
& Brandon's Bishop, Eq. 6.77, which takes P*cos(beta) only).

On a polyline that was not enough: the general path also takes the MOMENT of
the base normals, and it took the uncorrected N, whose pore part is C-13's
(1.749 at 30 ft, 1.981 at 60 ft with D199 alone). D213 takes the moment of
the method's own total normal, N' + u*l. Both switches, in
``ogr_slip2d.methods.ordinary``: ``POND_THRUST_OUT_OF_NORMAL`` and
``MOMENT_NORMAL_OWN``.

CONTROLS: without a pond nothing moves with ``POND_THRUST_OUT_OF_NORMAL``
(dry, phreatic only, water in a tension crack, a horizontal line load --
the last two share the accumulator the pond writes to, and stay in N); on a
circle ``MOMENT_NORMAL_OWN`` changes nothing, on a dry polyline nothing, and
on a wet polyline it moves the number (rule 7).

TOLERANCES: the buoyant model and the ponded one slice the same mass but
place the water's resultants differently within a slice, so they agree to
discretisation: 5.8e-5 at 50 slices and 3e-6 at 200 on the circle, 7e-7 on
the polyline. The depth invariance is exact up to rounding.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ORD = "ordinary_fellenius"
BISHOP = "bishop_simplified"
DEPTHS = (75.0, 105.0)     # 30 and 60 ft over the crest at 45 ft
_CACHE: dict = {}


# ======================================================================
class _Switches:
    """The two switches of ``ordinary`` set and PUT BACK (no teardown in
    the runner). ``getattr``: on a tree without them, setting them does
    nothing, the old reading, so the cases fail on the number."""

    def __init__(self, pond=True, moment=True):
        self.want = {"POND_THRUST_OUT_OF_NORMAL": pond,
                     "MOMENT_NORMAL_OWN": moment}

    def __enter__(self):
        from ogr_slip2d.methods import ordinary
        self.old = {k: getattr(ordinary, k, None) for k in self.want}
        for k, v in self.want.items():
            setattr(ordinary, k, v)
        return self

    def __exit__(self, *exc):
        from ogr_slip2d.methods import ordinary
        for k, v in self.old.items():
            if v is None:
                vars(ordinary).pop(k, None)
            else:
                setattr(ordinary, k, v)
        return False


def _v70():
    import test_ponded_water_v161 as V
    return V


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**_v70().CIRCLE)


def _polyline(n_vertices=11):
    """The circle of problem 70 as a polyline, sampled from its own slice
    bases so it daylights; eleven vertices, since each is a mandatory cut
    and 50 slices cannot spend more."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipSurface
    sl = slice_surface(_v70().buoyant(), _circle(), num_slices=400)
    pts = [(sl.slices[0].base_x_left, sl.slices[0].base_y_left)]
    pts += [(s.base_x_right, s.base_y_right) for s in sl.slices]
    idx = [round(i * (len(pts) - 1) / (n_vertices - 1))
           for i in range(n_vertices)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(*pts[i]) for i in idx]))


def _with_cohesion(p, c):
    from ogr_core.materials.builtin_models import MohrCoulomb
    for m in p.materials:
        m.strength = MohrCoulomb(cohesion=c,
                                 friction_angle=_v70().PHI)
    return p


def _dry(c):
    """The slope with its TOTAL unit weight and no water at all."""
    from ogr_core.geometry import Boundary, BoundaryType
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    V = _v70()
    p = Project("v70-dry")
    p.add_boundary(Boundary(polyline=V._external(),
                            btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=V.GAMMA,
                            strength=MohrCoulomb(cohesion=c,
                                                 friction_angle=V.PHI))]
    return p


def _phreatic():
    """Total weights and a water table INSIDE the slope, below the ground
    everywhere: wet bases, no pond."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    V = _v70()
    p = V._base_project("v70-phreatic")
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(-10, 12.0), Vertex(30, 13.0), Vertex(105, 38.0),
        Vertex(150, 40.0)], closed=False), btype=BoundaryType.WATER_TABLE))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=V.COHESION,
                                          friction_angle=V.PHI),
        unit_weight=V.GAMMA, sat_unit_weight=V.GAMMA,
        use_sat_unit_weight=True,
        pore_pressure=PorePressureType.WATER_TABLE)]
    return p


def _fos(key, build, surf, mid, n, pond=True, moment=True):
    k = (key, mid, n, pond, moment, type(surf).__name__)
    if k not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        p = build()
        sl = slice_surface(p, surf, num_slices=n)
        assert sl is not None, key
        with _Switches(pond, moment):
            res = method_registry()[mid]().compute_fos(p, surf, sl)
        assert res.fos is not None, (key, mid, res.reason)
        _CACHE[k] = res.fos
    return _CACHE[k]


def _rel(a, b):
    return abs(a - b) / abs(b)


# ======================================================================
class TestTheSubmergedCircle:

    def test_the_factor_does_not_depend_on_the_depth(self):
        V = _v70()
        a, b = (_fos(("pond", d), lambda d=d: V.ponded(d), _circle(), ORD,
                     50) for d in DEPTHS)
        assert _rel(a, b) < 1e-9, (a, b)

    def test_it_is_the_buoyant_factor(self):
        V = _v70()
        gaps = {}
        for n in (50, 200):
            buoy = _fos("buoyant", V.buoyant, _circle(), ORD, n)
            for d in DEPTHS:
                got = _fos(("pond", d), lambda d=d: V.ponded(d), _circle(),
                           ORD, n)
                gaps[(n, d)] = _rel(got, buoy)
        for d in DEPTHS:
            assert gaps[(50, d)] < 2e-4, gaps
            # discretisation, not a residue: it shrinks with the slices
            assert gaps[(200, d)] < gaps[(50, d)] / 4.0, gaps

    def test_cohesionless_submerged_is_dry(self):
        """c = 0: the factor of the submerged slope is the DRY slope's, with
        its total unit weight -- the literal identity of the defect."""
        V = _v70()
        dry = _fos("dry0", lambda: _dry(0.0), _circle(), ORD, 200)
        for d in DEPTHS:
            got = _fos(("pond0", d),
                       lambda d=d: _with_cohesion(V.ponded(d), 0.0),
                       _circle(), ORD, 200)
            assert _rel(got, dry) < 1e-4, (d, got, dry)

    def test_the_old_reading_grew_with_the_water(self):
        """Guard: the witness shows the defect with the switch off."""
        V = _v70()
        a, b = (_fos(("pond", d), lambda d=d: V.ponded(d), _circle(), ORD,
                     50, pond=False) for d in DEPTHS)
        assert b > a * 1.1, (a, b)


class TestTheSubmergedPolyline:
    """The general path: D199 and D213 together."""

    def test_the_factor_does_not_depend_on_the_depth(self):
        V = _v70()
        a, b = (_fos(("pond", d), lambda d=d: V.ponded(d), _polyline(), ORD,
                     50) for d in DEPTHS)
        assert _rel(a, b) < 1e-9, (a, b)

    def test_it_is_the_buoyant_factor(self):
        V = _v70()
        buoy = _fos("buoyant", V.buoyant, _polyline(), ORD, 50)
        for d in DEPTHS:
            got = _fos(("pond", d), lambda d=d: V.ponded(d), _polyline(),
                       ORD, 50)
            assert _rel(got, buoy) < 1e-5, (d, got, buoy)

    def test_without_the_moment_normal_it_still_grew(self):
        """Guard: D199 alone does not hold on a polyline, which is why D213
        exists."""
        V = _v70()
        a, b = (_fos(("pond", d), lambda d=d: V.ponded(d), _polyline(), ORD,
                     50, moment=False) for d in DEPTHS)
        assert b > a * 1.05, (a, b)


def _water_as_soil(wt):
    """The EM's other way: the reservoir as a 'soil' with c = phi = 0 and
    the unit weight of water, the model widened so the circle runs up to
    the water surface on both sides."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    V = _v70()
    ext = Polyline(vertices=[Vertex(-40, 0), Vertex(180, 0),
                             Vertex(180, wt), Vertex(-40, wt)], closed=True)
    ext.ensure_ccw()
    p = Project("v70-water-as-soil")
    p.settings.groundwater.pore_fluid_unit_weight = V.GAMMA_W
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(-40, 15), Vertex(30, 15), Vertex(105, 45), Vertex(180, 45)],
        closed=False), btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(-50, wt), Vertex(190, wt)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    soil = Material(name="Soil", strength=MohrCoulomb(
        cohesion=V.COHESION, friction_angle=V.PHI), unit_weight=V.GAMMA,
        sat_unit_weight=V.GAMMA, use_sat_unit_weight=True,
        pore_pressure=PorePressureType.WATER_TABLE)
    water = Material(name="Water", strength=MohrCoulomb(
        cohesion=0.0, friction_angle=0.0), unit_weight=V.GAMMA_W,
        sat_unit_weight=V.GAMMA_W, use_sat_unit_weight=True,
        pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [soil, water]
    regs = sorted(p.resolve_regions(), key=lambda r: r.centroid()[1])
    p.assign_material_at(*regs[0].centroid(), soil.id)
    p.assign_material_at(*regs[1].centroid(), water.id)
    return p


class TestTheEMsTwoWaysAgree:
    """Water as a load and water as a strengthless soil, 200 slices."""

    def _pair(self, mid, d, **sw):
        V = _v70()
        load = _fos(("pond", d), lambda: V.ponded(d), _circle(), mid, 200,
                    **sw)
        soil = _fos(("soil", d), lambda: _water_as_soil(d), _circle(), mid,
                    200, **sw)
        return load, soil

    def test_the_ordinary_method(self):
        for d in DEPTHS:
            load, soil = self._pair(ORD, d)
            assert _rel(load, soil) < 1e-4, (d, load, soil)

    def test_bishop_the_control(self):
        for d in DEPTHS:
            load, soil = self._pair(BISHOP, d)
            assert _rel(load, soil) < 1e-4, (d, load, soil)

    def test_the_old_reading_disagreed(self):
        """Guard: the pair is not trivially equal."""
        load, soil = self._pair(ORD, 105.0, pond=False)
        assert _rel(load, soil) > 0.1, (load, soil)


# ======================================================================
class TestThePondsThrustIsKeptApart:

    def test_it_sums_to_the_thrust_on_the_face(self):
        """The circle of problem 70 covers the whole face (30,15)-(105,45):
        the pond's horizontal components add up to the hydrostatic thrust on
        its vertical projection, gamma_w*((d-15)^2 - (d-45)^2)/2.

        To 1e-5 and not to rounding: the circle leaves the ground 0.01 ft
        left of the toe, the cut at the toe is merged into that first slice
        (cuts closer than 1e-3 of a width are), and a slice whose top is
        kinked takes its pond thrust with the slope of the chord. Measured
        8e-6 at both depths."""
        from ogr_slip2d.slicer import slice_surface
        V = _v70()
        for d in DEPTHS:
            sl = slice_surface(V.ponded(d), _circle(), num_slices=50)
            got = sum(s.pond_force_h for s in sl.slices)
            want = 0.5 * V.GAMMA_W * ((d - 15.0) ** 2 - (d - 45.0) ** 2)
            assert math.isclose(got, want, rel_tol=1e-5), (d, got, want)

    def test_it_is_inside_the_water_force_not_added_to_it(self):
        from ogr_slip2d.slicer import slice_surface
        sl = slice_surface(_v70().ponded(105.0), _circle(), num_slices=50)
        for s in sl.slices:
            assert s.pond_force_h == s.water_force_h, s.index


class TestWhatDoesNotMove:
    """Without a pond the switch is inert; the moment normal is inert on a
    circle and on a dry polyline, and moves a wet one (rule 7)."""

    def _both(self, key, build, surf, n=50, which="pond"):
        on = _fos(key, build, surf, ORD, n)
        off = _fos(key, build, surf, ORD, n,
                   **({"pond": False} if which == "pond"
                      else {"moment": False}))
        return off, on

    def test_dry_and_phreatic_only(self):
        for key, build in (("dry", lambda: _dry(100.0)),
                           ("phreatic", _phreatic)):
            for surf in (_circle(), _polyline()):
                off, on = self._both(key, build, surf)
                assert off == on, (key, type(surf).__name__, off, on)

    def test_water_in_a_tension_crack_stays_in_the_normal(self):
        import test_ponded_water_v161 as V
        from ogr_core.geometry import WaterLevelMode
        from ogr_slip2d.surface import SlipCircle
        case = V.TestTensionCrackForceReachesTheResult()
        circ = SlipCircle(**case._CIRCLE)
        off, on = self._both(
            "crack", lambda: case._project(WaterLevelMode.FILLED), circ, 30)
        assert off == on, (off, on)

    def test_a_horizontal_line_load_stays_in_the_normal(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad, LoadOrientation

        def build():
            p = _dry(100.0)
            p.line_loads.append(LineLoad(
                point=Vertex(80.0, 35.0), magnitude=2000.0,
                orientation=LoadOrientation.HORIZONTAL))
            return p
        for surf in (_circle(), _polyline()):
            off, on = self._both("hload", build, surf)
            assert off == on, (type(surf).__name__, off, on)

    def test_the_moment_normal_is_inert_on_a_circle_and_a_dry_polyline(self):
        V = _v70()
        off, on = self._both(("pond", 105.0), lambda: V.ponded(105.0),
                             _circle(), which="moment")
        assert off == on, (off, on)
        off, on = self._both("dry", lambda: _dry(100.0), _polyline(),
                             which="moment")
        assert off == on, (off, on)

    def test_the_moment_normal_moves_a_wet_polyline(self):
        """Rule 7, D213: a water table inside the slope, no pond."""
        off, on = self._both("phreatic", _phreatic, _polyline(),
                             which="moment")
        assert _rel(on, off) > 1e-4, (off, on)
