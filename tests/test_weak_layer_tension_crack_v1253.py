# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A tension crack ends each analysed surface where THAT surface meets the
crack boundary, also when a weak layer clipped it (D253).

WHAT INVARIANT THIS PROTECTS. A surface clipped onto a joint used to inherit
the tension-crack wall of the surface it was clipped from, and the slicer
accepted it as already decided. Two defects came out of that, and both are
on the unsafe side:

* a CIRCLE is truncated at the crack by the search before any weak layer is
  considered, so every surface clipped from it kept the circle's wall. Where
  the joint runs above the crack line, the clipped surface went on along the
  joint INSIDE the cracked zone, counting shear strength the crack says is
  not there, and its wall started below its own end. Measured on the planar
  joint below, dry crack: 1.5861 against 1.5570 (+1.87 %), in both handlings;
* a POLYLINE is truncated by the slicer, in place. Under automatic case
  generation the bare case is sliced first, writes its wall on the shared
  base, and every clipped case inherited it: 1.5805 against the 1.5570 of
  "highest" for the same mechanism (+1.51 %), so the answer depended on the
  order the cases were evaluated in.

Both are one rule: the wall goes where the analysed surface meets the crack
boundary. "Once the soil is cracked, all strength on the plane of the crack
is lost" (Duncan, Wright and Brandon 2014, *Soil Strength and Slope
Stability*, 2nd ed., p. 15) and "shear resistance along tension cracks
should be ignored" (USACE EM 1110-2-1902, 2003, p. 1-4). The crack created
by reverse curvature is different, and is still inherited: it belongs to the
circle that generated the mass, where the arc turns back on itself.

WHY THESE ANCHORS. None of the numbers below is a value this code printed.

* THE CLOSED FORM, dry crack. Over a planar joint the Ordinary method is the
  rigid block on a plane, and with a dry tension crack in the upper slope
  surface that is Hoek and Bray (1981), *Rock Slope Engineering*, 3rd ed.,
  ch. 7: ``F = (c A + W cos(psi) tan(phi)) / (W sin(psi))``, with A the
  length of the plane up to the crack and W the weight of the whole block
  up to the wall. The wall stands where the joint meets the crack line,
  ``x_w = 2 + (y_c - 2) * 28 / 8``, and the block is the 80 m2 wedge of
  ``test_weak_layer_v1121`` less the triangle beyond the wall,
  ``(30 - x_w)(10 - y_c) / 2``: 76.0625 m2 with the crack at 8.5 and
  73 m2 with it at 8.0. Moment equilibrium does not move it: on one plane
  the moment of each normal force cancels the moment of the normal
  component of its own weight.
* THE IDENTITY, water in the crack. The thrust has an arm, so the Ordinary
  method is no longer the block on a plane and no closed form is claimed.
  What is claimed is that one mechanism has one factor: the two handlings
  and the two bases below clip to the same surface with the same wall, and
  the circle base and the polyline base turn about the same point, (8, 34),
  which is the centre of the circle AND the axis constructed for the
  polyline from its two ends (midpoint plus the perpendicular).
* RULE 7 has nothing to bite on: no setting is added.

The planar surface needs at least 30 slices (25 refuse it: more mandatory
cuts than slices), so every evaluation passes 40.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_SLICES = 40
_ORD = "ordinary_fellenius"

# --- The planar joint of test_weak_layer_v1121 ------------------------
_EXT = [(0.0, 0.0), (40.0, 0.0), (40.0, 10.0), (10.0, 10.0)]
_GAMMA = 20.0
_JX0, _JY0, _JX1, _JY1 = 2.0, 2.0, 30.0, 10.0
_PSI = math.atan2(_JY1 - _JY0, _JX1 - _JX0)
_C, _PHI = 5.0, 20.0                     # the joint
_CRACK_Y = 8.5

# --- Two bases that clip to the whole joint ----------------------------
# The circle through both ends of the joint with its centre at (8, 34): it
# runs below the joint over its whole length, so the clipped surface is the
# joint, and it meets the crack line at x = 8 + sqrt(409.75) = 28.24, beyond
# the joint's 24.75. The polyline is the one of v1121.
_CX, _CY, _R = 8.0, 34.0, math.sqrt(1060.0)
_POLY = [(2.0, 2.0), (16.0, 1.0), (30.0, 10.0)]


def _wall_x(crack_y):
    return _JX0 + (crack_y - _JY0) * (_JX1 - _JX0) / (_JY1 - _JY0)


def _closed_form_dry(crack_y):
    """Hoek and Bray (1981): the block on the joint up to the wall."""
    x_w = _wall_x(crack_y)
    area = 80.0 - 0.5 * (_JX1 - x_w) * (_JY1 - crack_y)
    w = _GAMMA * area
    a = math.hypot(x_w - _JX0, crack_y - _JY0)
    return ((_C * a + w * math.cos(_PSI) * math.tan(math.radians(_PHI)))
            / (w * math.sin(_PSI)))


def _model(handling, mode="dry", crack_y=_CRACK_Y):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                 WaterLevelMode)
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("D253")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(*v) for v in _EXT], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Soil", unit_weight=_GAMMA,
        strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0)))
    joint = Material(name="Joint", unit_weight=_GAMMA,
                     strength=MohrCoulomb(cohesion=_C, friction_angle=_PHI))
    p.materials.append(joint)
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(_JX0, _JY0), Vertex(_JX1, _JY1)]),
        btype=BoundaryType.WEAK_LAYER, material_id=joint.id))
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(0.0, crack_y), Vertex(40.0, crack_y)]),
        btype=BoundaryType.TENSION_CRACK))
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode(mode))
    p.settings.search.weak_layer_handling = handling
    p.settings.methods.num_slices = _SLICES
    return p


def _polyline():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline([Vertex(*v) for v in _POLY]))


def _evaluate(project, base):
    from ogr_slip2d.analysis_runner import build_evaluator
    from ogr_slip2d.surface import SlipCircle
    ev = build_evaluator(project, _ORD, num_slices=_SLICES)
    with project.regions_frozen():
        if base == "circle":
            return ev.evaluate_circle(project, SlipCircle(_CX, _CY, _R))
        return ev.evaluate_surface(project, _polyline())


_ROUTES = [(h, b) for h in ("highest", "auto_cases")
           for b in ("polyline", "circle")]


def _close(a, b, tol=1e-12):
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def _assert_on_the_joint(r, crack_y, label):
    from ogr_slip2d.surface import WeakLayerSurface
    assert r is not None and r.is_valid, label
    assert isinstance(r.surface, WeakLayerSurface), (
        label, type(r.surface).__name__)
    wall = r.surface.tension_crack_wall
    expected = (_wall_x(crack_y), crack_y, 10.0)
    assert wall is not None and all(
        _close(p, q) for p, q in zip(wall, expected)), (label, wall)
    assert _close(r.surface.x_right, expected[0]), (label, r.surface.x_right)


# ======================================================================
class TestTheWallIsWhereTheSurfaceMeetsTheCrack:
    """Dry crack: the block on the joint, closed form (Hoek and Bray)."""

    def test_a_polyline_base_in_both_handlings(self):
        f = _closed_form_dry(_CRACK_Y)
        for handling in ("highest", "auto_cases"):
            r = _evaluate(_model(handling), "polyline")
            _assert_on_the_joint(r, _CRACK_Y, handling)
            assert _close(r.fos, f), (handling, r.fos, f)

    def test_a_circle_base_in_both_handlings(self):
        """The search truncates the circle at ITS crossing, 28.24; the
        clipped surface still ends at the joint's, 24.75."""
        f = _closed_form_dry(_CRACK_Y)
        for handling in ("highest", "auto_cases"):
            r = _evaluate(_model(handling), "circle")
            _assert_on_the_joint(r, _CRACK_Y, handling)
            assert _close(r.fos, f), (handling, r.fos, f)

    def test_the_wall_follows_the_crack_line(self):
        """Crack at 8.0: the wall at 23.0 and the 73 m2 block, by every
        route — the wall is the surface's crossing, not a remembered one."""
        f = _closed_form_dry(8.0)
        assert not _close(f, _closed_form_dry(_CRACK_Y), 1e-3)
        for handling, base in _ROUTES:
            r = _evaluate(_model(handling, crack_y=8.0), base)
            _assert_on_the_joint(r, 8.0, (handling, base))
            assert _close(r.fos, f), (handling, base, r.fos, f)

    def test_a_second_pass_keeps_its_own_wall(self):
        """Slicing the answer again changes nothing (the D90 rule: a wall
        that is still the model's is kept to the last bit)."""
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        p = _model("auto_cases")
        r = _evaluate(p, "circle")
        wall = r.surface.tension_crack_wall
        sl = slice_surface(p, r.surface, num_slices=_SLICES)
        again = method_registry()[_ORD]().compute_fos(p, r.surface, sl)
        assert r.surface.tension_crack_wall == wall
        assert _close(again.fos, r.fos), (again.fos, r.fos)


class TestWaterInTheCrack:

    def test_the_four_routes_give_one_number(self):
        """One mechanism, one factor: both handlings, both bases, the same
        wall and the same moment axis. The thrust acts: below the dry
        closed form."""
        fs = {}
        for handling, base in _ROUTES:
            r = _evaluate(_model(handling, mode="filled"), base)
            _assert_on_the_joint(r, _CRACK_Y, (handling, base))
            fs[(handling, base)] = r.fos
        first = next(iter(fs.values()))
        assert all(_close(f, first) for f in fs.values()), fs
        assert first < _closed_form_dry(_CRACK_Y), fs


class TestTheBareCase:
    """Automatic case generation slices the bare mass on a copy."""

    def _variants(self, mode="dry"):
        from ogr_slip2d.weak_layers import (weak_layer_bands,
                                            weak_layer_variants)
        p = _model("auto_cases", mode=mode)
        base = _polyline()
        cases = list(weak_layer_variants(base, weak_layer_bands(p),
                                         handling="auto_cases"))
        return p, base, cases

    def test_slicing_it_leaves_the_shared_base_alone(self):
        from ogr_slip2d.slicer import slice_surface
        p, base, cases = self._variants()
        assert len(cases) == 2
        before = [(v.x, v.y) for v in base.polyline.vertices]
        with p.regions_frozen():
            sl = slice_surface(p, cases[0], num_slices=_SLICES)
        assert sl is not None
        # The bare case itself WAS truncated at its own crossing: the
        # segment (16, 1)-(30, 10) meets y = 8.5 at 16 + 7.5 * 14 / 9 ...
        x_bare = 16.0 + (_CRACK_Y - 1.0) * 14.0 / 9.0
        assert _close(cases[0].x_range()[1], x_bare), cases[0].x_range()
        assert _close(cases[0].tension_crack_wall[0], x_bare)
        # ... and the base every clipped case is built from was not.
        assert [(v.x, v.y) for v in base.polyline.vertices] == before
        assert base.tension_crack_wall is None
        assert base.tension_cracks == []
        assert cases[1].base is base

    def test_it_is_the_same_surface_analysed_apart(self):
        """Same identifier, and the factor of the bare polyline evaluated
        on its own, with water in the crack (where the axis matters)."""
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        p, base, cases = self._variants(mode="filled")
        assert cases[0].id == base.id
        assert cases[0].polyline.id == base.polyline.id
        alone = _polyline()
        with p.regions_frozen():
            f0 = method_registry()[_ORD]().compute_fos(
                p, cases[0], slice_surface(p, cases[0],
                                           num_slices=_SLICES)).fos
            f1 = method_registry()[_ORD]().compute_fos(
                p, alone, slice_surface(p, alone, num_slices=_SLICES)).fos
        assert f0 == f1, (f0, f1)


class TestReverseCurvatureIsStillTheCircles:

    def test_only_the_users_wall_is_not_inherited(self):
        """Both are drawn as (x, bottom, top) in ``tension_cracks``; the one
        equal to the base's ``tension_crack_wall`` is the user's crack."""
        from ogr_slip2d.surface import SlipCircle, WeakLayerSurface
        c = SlipCircle(centre_x=20.0, centre_y=4.0, radius=10.0)
        c.x_left, c.x_right = 12.0, 30.0
        reverse = (30.0, 4.0, 10.0)          # at x_c + R, from the centre up
        wall = (24.0, 8.5, 10.0)             # the user's crack
        c.tension_cracks = [reverse, wall]
        c.tension_crack_wall = wall
        w = WeakLayerSurface(base=c, bands=())
        assert w.tension_cracks == [reverse]
        assert w.tension_crack_wall is None
        assert c.tension_cracks == [reverse, wall]     # the base keeps it
        assert c.tension_crack_wall == wall
