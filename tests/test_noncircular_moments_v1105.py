# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The moment axis has to reach every term of every moment method.

WHAT INVARIANT THIS PROTECTS. Until v0.1.105, four methods guarded the seismic,
water and support moment terms behind ``if circle_R is not None:``, and
``circle_R`` was only set for a :class:`SlipCircle`. On any other surface —
Block, Path, Simulated Annealing, or a surface the user drew — those terms
silently vanished. Nothing in this suite could see it: every numerical
benchmark it owns fixes either a circle, or a polyline with no earthquake, no
ponded water and no reinforcement on it.

The error ran to +45 % on a plain slope with kh = 0.15 and to +157 % on a
published benchmark, always on the UNSAFE side.

Four independent anchors, none of them a snapshot of what the code prints:

1.  **Invariance of description.** The same arc, described once as a circle and
    once as a polyline sampled from it, over the same model, with the moment axis
    pinned at the circle's own centre so both are measured about the SAME
    point. Same geometry, same loads, same slices — only the type of the object
    changes, so the factor of safety may not. Pinning the axis is part of the
    statement rather than a convenience: Bishop and Ordinary do not satisfy
    force equilibrium, so their answer legitimately depends on where moments
    are taken, and comparing them about two different points would be
    comparing two different questions.

2.  **Mirror symmetry.** A model and its mirror image describe the same slope,
    so they must give the same factor of safety, with and without an
    earthquake. This is what caught the second defect of this version: the
    pseudo-static force is a MAGNITUDE, ``kh·W``, and two methods applied it
    in +x whatever the slope did. On a slope descending to the left it then
    held the mass back, and the factor of safety GREW with the earthquake —
    1.46817 at kh = 0 rising to 2.74151 at kh = 0.20, on a CIRCLE, in
    Ordinary. Nothing checked the seismic term numerically anywhere in this
    suite, and the three benchmark problems that carry one all descend the
    same way, where the sign is right by accident.

3.  **The buoyant identity of Duncan and Wright (2005), chapter 6**, on a
    polyline: total unit weights plus pore pressures plus the boundary water
    forces must give the same factor as buoyant unit weights with no water at
    all. It held on a circle to 0.01 % and failed on a polyline by −27 %.

4.  **The critical seismic coefficient of Loukidis, Bandini and Salgado
    (2003), example 1**: kc = 0.432 is by definition the coefficient that
    leaves the factor of safety at 1.000.

Anchors 1 and 2 are analytic identities; 3 is an analytic identity with a
published origin; 4 is a published number. Rule 1 is satisfied four ways.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ----------------------------------------------------------------------
# A homogeneous slope descending to the RIGHT, and its mirror image about
# x = 40. One arc, sampled into a polyline, in both orientations.
_SLOPE_RIGHT = [(0, 0), (80, 0), (80, 20), (50, 20), (20, 40), (0, 40)]
_SLOPE_LEFT = [(0, 0), (80, 0), (80, 40), (60, 40), (30, 20), (0, 20)]
_MIRROR_X = 80.0
_ARC = dict(centre_x=30.0, centre_y=62.0, radius=30.0)
# The slicer puts a boundary at every vertex of a non-circular surface
# (v0.1.89), so a polyline of N segments cannot be cut into fewer than N
# slices — it returns nothing at all rather than a coarser answer. Keep
# ``_SAMPLES`` comfortably below ``_N_SLICES``.
_N_SLICES = 30
_SAMPLES = 24

_CACHE: dict = {}


def _method_ids():
    from ogr_slip2d.methods import method_registry
    return sorted(method_registry())


def _slope_project(mirror=False, kh=0.0, axis=None, support=False):
    """The homogeneous slope, optionally mirrored, seismic or reinforced."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SoilNail, SupportInstance)

    pts = _SLOPE_LEFT if mirror else _SLOPE_RIGHT
    p = Project("espejo" if mirror else "derecha")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="suelo", unit_weight=19.0,
                            sat_unit_weight=19.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=25.0))]
    p.assign_material_at(40, 10, p.materials[0].id)
    if kh:
        p.seismic.enabled = True
        p.seismic.kh = kh
        p.seismic.kv = 0.0
    if support:
        # A nail crossing the arc well inside the mass, modest enough that
        # the driving side does not nearly vanish.
        head, tail = (34.0, 30.0), (46.0, 26.0)
        if mirror:
            head = (_MIRROR_X - head[0], head[1])
            tail = (_MIRROR_X - tail[0], tail[1])
        p.support_types = [SoilNail(tensile_capacity=30, plate_capacity=20,
                                    bond_strength=8, out_of_plane_spacing=3.0)]
        p.supports = [SupportInstance(
            type_id="soil_nail", head=Vertex(*head), tail=Vertex(*tail),
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.TANGENT_TO_SLIP)]
    # Rule 5: settings are shared state, so this project gets its own copy
    # before anything is written into it.
    p.settings = copy.deepcopy(p.settings)
    if axis is not None:
        p.settings.search.axis_x, p.settings.search.axis_y = axis
    p.settings.methods.num_slices = _N_SLICES
    return p


def _arc_circle(mirror=False):
    from ogr_slip2d.surface import SlipCircle
    cx = _MIRROR_X - _ARC["centre_x"] if mirror else _ARC["centre_x"]
    return SlipCircle(centre_x=cx, centre_y=_ARC["centre_y"],
                      radius=_ARC["radius"])


def _arc_axis(mirror=False):
    c = _arc_circle(mirror)
    return (c.centre_x, c.centre_y)


def _arc_polyline(mirror=False):
    """The SAME arc, sampled between its own ground crossings."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.geometry.ground import ground_surface
    from ogr_slip2d.surface import SlipSurface

    key = ("arc_poly", mirror)
    if key not in _CACHE:
        base = _arc_circle(False)
        g = ground_surface(
            _slope_project().external_boundary().polyline)
        x_l, x_r = base.intersect_with_ground(g)
        pts = []
        for i in range(_SAMPLES + 1):
            x = x_l + (x_r - x_l) * i / _SAMPLES
            pts.append((x, _arc_circle(False).base_y_at(x)))
        if mirror:
            pts = [(_MIRROR_X - x, y) for x, y in pts]
        _CACHE[key] = SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False))
    return _CACHE[key]


def _evaluate(method_id, project, surface, n=None):
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle
    ev = GridSearch(method=get_method(method_id)(),
                    num_slices=_N_SLICES if n is None else n,
                    min_area=0.0, check_m_alpha=False)
    if isinstance(surface, SlipCircle):
        return ev.evaluate_circle(project, surface)
    return ev.evaluate_surface(project, surface)


def _fos(method_id, project, surface, n=None):
    r = _evaluate(method_id, project, surface, n)
    assert r is not None and r.is_valid, f"{method_id}: sin resultado"
    return float(r.fos)


# ======================================================================
class TestTheSameArcDescribedTwoWays:
    """A circle and the polyline sampled from it are the same surface.

    Four load cases, because the terms that used to vanish only exist in
    three of them: dry (the control, which already passed), seismic, ponded
    water and reinforcement.
    """

    TOL = 0.5      # per cent

    def _compare(self, method_id, kh=0.0, support=False):
        axis = _arc_axis(False)
        circ = _fos(method_id, _slope_project(kh=kh, support=support),
                    _arc_circle(False))
        poly = _fos(method_id,
                    _slope_project(kh=kh, axis=axis, support=support),
                    _arc_polyline(False))
        return circ, poly

    def _assert_all(self, kh=0.0, support=False, label=""):
        bad = []
        for mid in _method_ids():
            circ, poly = self._compare(mid, kh=kh, support=support)
            err = abs(poly - circ) / circ * 100.0
            if err >= self.TOL:
                bad.append(f"{mid}: circulo {circ:.6f} polilinea {poly:.6f} "
                           f"= {err:+.2f} %")
        assert not bad, f"{label}: {bad}"

    def test_dry(self):
        self._assert_all(label="seco")

    def test_with_an_earthquake(self):
        """The case that was +45 % in Spencer and GLE and +152 % in Bishop
        on a mirrored slope."""
        self._assert_all(kh=0.15, label="kh = 0.15")

    def test_with_reinforcement(self):
        self._assert_all(support=True, label="con soporte")

    def test_with_an_earthquake_and_reinforcement(self):
        self._assert_all(kh=0.15, support=True, label="kh y soporte")

    def test_the_two_descriptions_are_really_different_objects(self):
        """Guards the test itself: if the polyline were built as a circle,
        every case above would pass for the wrong reason."""
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        assert isinstance(_arc_circle(False), SlipCircle)
        assert isinstance(_arc_polyline(False), SlipSurface)
        assert len(_arc_polyline(False).polyline.vertices) == _SAMPLES + 1

    def test_the_pinned_axis_is_the_one_that_gets_used(self):
        """The axis is what makes the comparison fair, so it is asserted
        rather than assumed."""
        axis = _arc_axis(False)
        r = _evaluate("bishop_simplified",
                      _slope_project(axis=axis), _arc_polyline(False))
        assert r.details.get("moment_axis") == axis, r.details


# ======================================================================
class TestMirrorSymmetry:
    """A slope and its mirror image are the same slope.

    No method may distinguish them. This is the identity that exposed the
    seismic direction: with the magnitude applied in +x regardless, Bishop
    read 1.318056 one way and 3.332505 the other on the same arc.

    Lowe-Karafiath and the second Corps of Engineers method get a wider band
    because their inter-slice inclination is prescribed from the ground
    slope, which is genuinely orientation-dependent; they deviate by the same
    ~0.3 % with no earthquake at all, so it is not what this test is about.
    """

    TOL = 0.5
    TOL_PRESCRIBED = 1.0
    _PRESCRIBED = ("lowe_karafiath", "corps_engineers_2")

    def _assert_mirror(self, kh):
        bad = []
        for mid in _method_ids():
            a = _fos(mid, _slope_project(kh=kh, axis=_arc_axis(False)),
                     _arc_polyline(False))
            b = _fos(mid, _slope_project(mirror=True, kh=kh,
                                         axis=_arc_axis(True)),
                     _arc_polyline(True))
            err = abs(b - a) / a * 100.0
            tol = self.TOL_PRESCRIBED if mid in self._PRESCRIBED else self.TOL
            if err >= tol:
                bad.append(f"{mid}: derecha {a:.6f} izquierda {b:.6f} "
                           f"= {err:+.2f} % (tolerancia {tol} %)")
        assert not bad, f"kh = {kh}: {bad}"

    def test_dry(self):
        self._assert_mirror(0.0)

    def test_with_an_earthquake(self):
        self._assert_mirror(0.15)

    def test_on_a_circle_too(self):
        """The Ordinary defect of this version lived on the CIRCULAR path, so
        the mirror has to be checked there as well and not only on polylines."""
        bad = []
        for mid in _method_ids():
            a = _fos(mid, _slope_project(kh=0.15), _arc_circle(False))
            b = _fos(mid, _slope_project(mirror=True, kh=0.15),
                     _arc_circle(True))
            err = abs(b - a) / a * 100.0
            tol = (self.TOL_PRESCRIBED if mid in self._PRESCRIBED
                   else self.TOL)
            if err >= tol:
                bad.append(f"{mid}: derecha {a:.6f} izquierda {b:.6f} "
                           f"= {err:+.2f} %")
        assert not bad, bad

    def test_the_earthquake_actually_lowers_the_factor(self):
        """Mirror symmetry alone is not enough: a method that ignored the
        earthquake entirely would pass it. Spencer and GLE did exactly that
        off a circle, returning the dry answer to six figures.

        This is rule 7 on the seismic coefficient — the setting has to move
        the number — and it is asserted on the POLYLINE, where it did not.
        """
        for mid in _method_ids():
            dry = _fos(mid, _slope_project(axis=_arc_axis(False)),
                       _arc_polyline(False))
            quake = _fos(mid, _slope_project(kh=0.15, axis=_arc_axis(False)),
                         _arc_polyline(False))
            assert quake < dry * 0.95, (
                f"{mid}: kh = 0.15 dio {quake:.6f} contra {dry:.6f} en seco")


# ======================================================================
class TestTheBuoyantIdentityOnANonCircularSurface:
    """Duncan and Wright (2005), chapter 6, on a polyline.

    With a horizontal water surface, two procedures must agree:

        totals    total unit weights + pore pressures + the boundary water
                  forces on the submerged face
        buoyant   γ' = γ − γ_w below the water, no water anywhere

    The model is the one ``test_ponded_water_v161`` already validates against
    the published referee value of 1.60 — reused rather than rebuilt, so the
    two files cannot drift apart — with its circle replaced by the polyline
    sampled from that same circle.
    """

    TOL = 1.0

    @staticmethod
    def _polyline():
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry.ground import ground_surface
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        from test_ponded_water_v161 import CIRCLE, buoyant
        key = "ponded_poly"
        if key not in _CACHE:
            c = SlipCircle(**CIRCLE)
            g = ground_surface(buoyant().external_boundary().polyline)
            x_l, x_r = c.intersect_with_ground(g)
            pts = []
            for i in range(_SAMPLES + 1):
                x = x_l + (x_r - x_l) * i / _SAMPLES
                pts.append((x, SlipCircle(**CIRCLE).base_y_at(x)))
            _CACHE[key] = SlipSurface(polyline=Polyline(
                vertices=[Vertex(x, y) for x, y in pts], closed=False))
        return _CACHE[key]

    @staticmethod
    def _with_axis(project):
        from test_ponded_water_v161 import CIRCLE
        p = copy.deepcopy(project)
        p.settings.search.axis_x = CIRCLE["centre_x"]
        p.settings.search.axis_y = CIRCLE["centre_y"]
        return p

    #: Ordinary/Fellenius is NOT in this list, and the omission is measured
    #: rather than assumed: on this deeply submerged model it misses the
    #: identity by +66.41 % — 2.517148 against 1.512605 — and it does so
    #: identically before and after v0.1.105, on the CIRCLE as much as on the
    #: polyline. ``test_ponded_water_v161`` leaves it out of its own
    #: ``RIGOROUS`` list for the same reason. It is a real limitation of the
    #: method with deep ponded water and it belongs to no part of this
    #: version; on the shallower problem-42 geometry the same method now
    #: satisfies the identity to +0.69 % on a polyline, against −22.87 %
    #: before, which is what this version did change.
    METHODS = ("bishop_simplified", "spencer", "gle_morgenstern_price",
               "janbu_simplified")

    def test_the_two_procedures_agree_on_a_polyline(self):
        from test_ponded_water_v161 import buoyant, ponded
        surface = self._polyline()
        bad = []
        for mid in self.METHODS:
            a = _fos(mid, self._with_axis(ponded(150.0)), surface, n=50)
            b = _fos(mid, self._with_axis(buoyant()), surface, n=50)
            err = abs(a - b) / b * 100.0
            if err >= self.TOL:
                bad.append(f"{mid}: totales {a:.6f} boyante {b:.6f} "
                           f"= {err:+.2f} %")
        assert not bad, bad

    def test_the_identity_still_holds_on_the_circle(self):
        """The control. If this broke too, the polyline would not be the
        thing at fault."""
        from test_ponded_water_v161 import CIRCLE, buoyant, ponded
        from ogr_slip2d.surface import SlipCircle
        for mid in self.METHODS:
            a = _fos(mid, ponded(150.0), SlipCircle(**CIRCLE), n=50)
            b = _fos(mid, buoyant(), SlipCircle(**CIRCLE), n=50)
            assert abs(a - b) / b * 100.0 < self.TOL, (mid, a, b)


# ======================================================================
class TestTheCriticalSeismicCoefficientOfLoukidis:
    """Loukidis, Bandini and Salgado (2003), example 1.

    A 3:1 slope 25 m high, c' = 25 kPa, φ' = 30°, γ = 20 kN/m³. The paper
    publishes the CRITICAL seismic coefficient — the one that leaves the
    factor of safety at exactly 1.000 — as kc = 0.432 for the dry slope. That
    is the anchor: not a number this program produced, and not one taken from
    another program either.

    The surface is an INPUT here, not the claim: it is the arc this program's
    own grid search finds critical, described as a polyline. What is asserted
    against Loukidis is the factor of safety on it. Before v0.1.105 the same
    arc gave 0.99179 as a circle and 2.55526 as a polyline.
    """

    KC = 0.432
    ARC = dict(centre_x=16.5, centre_y=109.0, radius=110.28186)
    TOL = 1.0

    @staticmethod
    def _project(axis=None):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        p = Project("loukidis")
        ext = Polyline(vertices=[Vertex(x, y) for x, y in (
            (-50, -25), (150, -25), (150, 25), (75, 25), (0, 0), (-50, 0))],
            closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="Clay", unit_weight=20.0,
                                sat_unit_weight=20.0,
                                strength=MohrCoulomb(cohesion=25.0,
                                                     friction_angle=30.0))]
        p.assign_material_at(0.0, -10.0, p.materials[0].id)
        p.seismic.enabled = True
        p.seismic.kh = TestTheCriticalSeismicCoefficientOfLoukidis.KC
        p.seismic.kv = 0.0
        p.settings = copy.deepcopy(p.settings)
        if axis is not None:
            p.settings.search.axis_x, p.settings.search.axis_y = axis
        return p

    @classmethod
    def _surfaces(cls):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry.ground import ground_surface
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        if "loukidis" not in _CACHE:
            c = SlipCircle(**cls.ARC)
            g = ground_surface(cls._project().external_boundary().polyline)
            x_l, x_r = c.intersect_with_ground(g)
            pts = []
            for i in range(50 + 1):
                x = x_l + (x_r - x_l) * i / 50
                pts.append((x, SlipCircle(**cls.ARC).base_y_at(x)))
            _CACHE["loukidis"] = (SlipCircle(**cls.ARC), SlipSurface(
                polyline=Polyline(vertices=[Vertex(x, y) for x, y in pts],
                                  closed=False)))
        return _CACHE["loukidis"]

    def test_the_factor_is_one_on_a_non_circular_surface(self):
        circ, poly = self._surfaces()
        axis = (self.ARC["centre_x"], self.ARC["centre_y"])
        bad = []
        for mid in ("spencer", "bishop_simplified", "gle_morgenstern_price"):
            f = _fos(mid, self._project(axis), poly, n=50)
            err = abs(f - 1.0) * 100.0
            if err >= self.TOL:
                bad.append(f"{mid}: {f:.6f} contra 1.000 = {err:+.2f} %")
        assert not bad, bad

    def test_the_circle_and_the_polyline_agree(self):
        circ, poly = self._surfaces()
        axis = (self.ARC["centre_x"], self.ARC["centre_y"])
        for mid in ("spencer", "bishop_simplified", "gle_morgenstern_price",
                    "ordinary_fellenius", "janbu_simplified"):
            a = _fos(mid, self._project(), circ, n=50)
            b = _fos(mid, self._project(axis), poly, n=50)
            assert abs(b - a) / a * 100.0 < self.TOL, (mid, a, b)
