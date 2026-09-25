# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A mass the tension crack truncated keeps its WALL, however it is handed back.
That is the invariant here (defect D189, v0.1.208).

When the crack truncates a surface it closes the mass with a vertical wall
from the crack line up to the ground (Duncan & Wright 2005, chapter 14),
and the water in the crack pushes on that wall with ½·γw·h² (Terzaghi
1943). The wall travels on the surface OBJECT, as ``tension_crack_wall``.
Two paths handed the very same mass back without that object:

* a NAMED mass — ``x_left``/``x_right`` set by the caller, which is how a
  mass other than the critical one is asked about;
* a POLYLINE rebuilt from its dictionary, since ``to_dict`` does not carry
  the wall — and that is exactly what the probabilistic loop does with a
  critical polyline, sample after sample.

Both arrive with the crest ON the crack line, and the rule that makes the
truncation idempotent reads "on the line" as "not inside the zone". So the
mass kept its geometry and lost its water thrust, on the unsafe side.
Measured with v0.1.207 on the phi = 0 slope below, crack filled: 0.99782
with the wall and 1.07140 without it, on the same slices; on ACADS 1(b)
1.59563 against 1.67246; on the rebuilt polyline 0.97496 against 1.05350.

What each class pins, and against what
--------------------------------------
1. The chord — the path the search takes — has its wall from the crack
   line up to the ground and a thrust of ½·γw·h² to twelve figures. That
   is the closed form the other classes are measured against.
2. The same mass NAMED, without the wall object, gets the same wall, the
   same thrust and the same factor of safety. This is what failed.
3. The edge of the rule, stated rather than hidden: a crest within the
   model's geometric tolerance of the line (1e-6 of the model diagonal —
   the length below which the model's own geometry is not resolved) gets
   its wall, with the closed-form thrust; ten tolerances below the line
   it is another mass and gets none. The crack model is discontinuous
   there, as it always was — but at the scale of the model, not at zero.
4. Rule 7: with ``CRACK_WALL_ON_LINE`` off the named mass loses its wall
   again and the factor moves, on the unsafe side.
5. The polyline through ``to_dict``/``from_dict`` and through the
   probabilistic ``_rebuild_surface`` gets the wall and the factor of the
   polyline evaluated in place, and draws the wall once, not twice.

Comparisons are relative (rel 1e-12) and never ``==`` on doubles: the same
computation on another platform may differ in the last bit.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_tension_crack_truncation_v1109 import (  # noqa: E402
    _CIRCLE, _analysed, _phi0_slope,
)

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_core.geometry.tension_crack import WaterLevelMode  # noqa: E402
from ogr_slip2d.methods import get_method  # noqa: E402
from ogr_slip2d.slicer import slice_surface  # noqa: E402
from ogr_slip2d.surface import SlipCircle, SlipSurface  # noqa: E402

GAMMA_W = 9.81
CRACK_Y = 34.0
GROUND_TOP = 40.0            # the upper flat of the fixture, where the wall is
#: The fixture's model is the box 0..100 x 0..40, so the model's geometric
#: tolerance is written from the geometry and not asked of the code.
MODEL_TOL = 1e-6 * math.hypot(100.0, 40.0)
THRUST = 0.5 * GAMMA_W * (GROUND_TOP - CRACK_Y) ** 2      # 176.58 kN/m


def _filled():
    return _phi0_slope(crack_y=CRACK_Y, mode=WaterLevelMode.FILLED)


def _fos(project, surface, slices, method="bishop_simplified"):
    return float(get_method(method)(tolerance=1e-10)
                 .compute_fos(project, surface, slices).fos)


def _chord(project, num_slices=160):
    c, sl = _analysed(project, num_slices=num_slices)
    assert sl is not None, "the fixture circle must be sliceable"
    return c, sl


def _named(x_left, x_right):
    c = SlipCircle(**_CIRCLE)
    c.x_left, c.x_right = x_left, x_right
    return c


def _crest_x_at(y):
    """Where the fixture circle's lower arc, on its crest side, is at ``y``.

    Solved from the circle itself, not from the code under test.
    """
    cx, cy, r = _CIRCLE["centre_x"], _CIRCLE["centre_y"], _CIRCLE["radius"]
    return cx + math.sqrt(r * r - (cy - y) ** 2)


def _same_wall(a, b):
    return (a is not None and b is not None
            and all(math.isclose(p, q, rel_tol=1e-12) for p, q in zip(a, b)))


# ======================================================================
# 1. The chord, against the closed form
# ======================================================================
class TestTheChordHasTheClosedFormThrust:

    def test_the_wall_runs_from_the_crack_up_to_the_ground(self):
        c, _sl = _chord(_filled())
        x, y0, y1 = c.tension_crack_wall
        assert math.isclose(x, _crest_x_at(CRACK_Y), rel_tol=1e-12)
        assert math.isclose(y0, CRACK_Y, rel_tol=1e-12)
        assert math.isclose(y1, GROUND_TOP, rel_tol=1e-12)

    def test_the_thrust_is_half_gamma_w_h_squared(self):
        _c, sl = _chord(_filled())
        assert math.isclose(sl.tension_crack_force, THRUST, rel_tol=1e-12)


# ======================================================================
# 2. The same mass, named, without the wall object
# ======================================================================
class TestANamedMassKeepsItsWall:
    """What failed in v0.1.207: no wall, no thrust, a factor 7 % higher."""

    def test_same_wall_same_thrust_same_factor(self):
        p = _filled()
        c, sl = _chord(p)
        f_chord = _fos(p, c, sl)
        named = _named(c.x_left, c.x_right)
        assert named.tension_crack_wall is None
        sl_n = slice_surface(p, named, num_slices=160)
        assert sl_n is not None
        assert _same_wall(named.tension_crack_wall, c.tension_crack_wall), (
            named.tension_crack_wall, c.tension_crack_wall)
        assert math.isclose(sl_n.tension_crack_force, THRUST, rel_tol=1e-12)
        assert math.isclose(_fos(p, named, sl_n), f_chord, rel_tol=1e-12)

    def test_it_is_not_cut_again(self):
        p = _filled()
        c, _sl = _chord(p)
        named = _named(c.x_left, c.x_right)
        assert slice_surface(p, named, num_slices=160) is not None
        assert math.isclose(named.x_left, c.x_left, rel_tol=1e-12)
        assert math.isclose(named.x_right, c.x_right, rel_tol=1e-12)

    def test_the_same_with_spencer(self):
        """Force AND moment equilibrium: the thrust is in both, and only a
        wall that is really there gives Spencer its chord factor."""
        p = _filled()
        c, sl = _chord(p)
        named = _named(c.x_left, c.x_right)
        sl_n = slice_surface(p, named, num_slices=160)
        assert math.isclose(_fos(p, named, sl_n, "spencer"),
                            _fos(p, c, sl, "spencer"), rel_tol=1e-12)


# ======================================================================
# 3. The edge of the rule, stated
# ======================================================================
class TestTheEdgeIsTheModelTolerance:

    def _named_with_crest_at(self, dy):
        p = _filled()
        c, _sl = _chord(p)
        named = _named(c.x_left, _crest_x_at(CRACK_Y + dy))
        sl = slice_surface(p, named, num_slices=160)
        assert sl is not None
        return named, sl

    def test_half_a_tolerance_below_the_line_gets_its_wall(self):
        named, sl = self._named_with_crest_at(-0.5 * MODEL_TOL)
        assert named.tension_crack_wall is not None
        x, y0, y1 = named.tension_crack_wall
        assert math.isclose(x, named.x_right, rel_tol=1e-12)
        assert math.isclose(y1 - y0, GROUND_TOP - CRACK_Y, rel_tol=1e-12)
        assert math.isclose(sl.tension_crack_force, THRUST, rel_tol=1e-12)

    def test_half_a_tolerance_above_it_is_truncated_back_to_the_line(self):
        named, sl = self._named_with_crest_at(+0.5 * MODEL_TOL)
        assert named.tension_crack_wall is not None
        assert math.isclose(named.x_right, _crest_x_at(CRACK_Y),
                            rel_tol=1e-12)
        assert math.isclose(sl.tension_crack_force, THRUST, rel_tol=1e-12)

    def test_ten_tolerances_below_it_is_another_mass(self):
        named, sl = self._named_with_crest_at(-10.0 * MODEL_TOL)
        assert named.tension_crack_wall is None
        assert sl.tension_crack_force == 0.0


# ======================================================================
# 4. Rule 7: the switch moves the number
# ======================================================================
class TestTheSwitchMovesTheNumber:

    def test_off_the_named_mass_loses_its_wall_on_the_unsafe_side(self):
        import ogr_slip2d.slicer as slicer
        p = _filled()
        c, _sl = _chord(p)
        on = _named(c.x_left, c.x_right)
        sl_on = slice_surface(p, on, num_slices=160)
        f_on = _fos(p, on, sl_on)
        before = slicer.CRACK_WALL_ON_LINE
        slicer.CRACK_WALL_ON_LINE = False
        try:
            off = _named(c.x_left, c.x_right)
            sl_off = slice_surface(p, off, num_slices=160)
            f_off = _fos(p, off, sl_off)
        finally:
            slicer.CRACK_WALL_ON_LINE = before
        assert off.tension_crack_wall is None
        assert sl_off.tension_crack_force == 0.0
        # Without the water pushing, the mass is SAFER than it is.
        assert f_off / f_on - 1.0 > 0.01, (f_on, f_off)


# ======================================================================
# 5. A polyline rebuilt from its dictionary
# ======================================================================
class TestARebuiltPolylineKeepsItsWall:
    """The probabilistic loop rebuilds a critical polyline from its
    dictionary for every sample; until v0.1.208 each sample lost the
    thrust."""

    def _arc_polyline(self):
        # The fixture arc from ground to ground on the model WITHOUT the
        # crack, in 60 chords: it daylights on the upper flat, above the
        # crack, so the crack has to cut it.
        dry = _phi0_slope(crack_y=None)
        c, sl = _analysed(dry, num_slices=60)
        assert sl is not None
        cx, cy, r = _CIRCLE["centre_x"], _CIRCLE["centre_y"], _CIRCLE["radius"]
        xa, xb = c.x_left, c.x_right
        return SlipSurface(polyline=Polyline(vertices=[
            Vertex(xa + (xb - xa) * i / 60.0,
                   cy - math.sqrt(max(r * r - (xa + (xb - xa) * i / 60.0
                                               - cx) ** 2, 0.0)))
            for i in range(61)], closed=False))

    def _evaluated(self):
        p = _filled()
        s = self._arc_polyline()
        sl = slice_surface(p, s, num_slices=60)
        assert sl is not None and s.tension_crack_wall is not None
        return p, s, sl

    def test_from_dict_gives_the_same_wall_and_factor(self):
        p, s, sl = self._evaluated()
        r = SlipSurface.from_dict(s.to_dict())
        sl_r = slice_surface(p, r, num_slices=60)
        assert sl_r is not None
        assert _same_wall(r.tension_crack_wall, s.tension_crack_wall)
        assert math.isclose(sl_r.tension_crack_force, THRUST, rel_tol=1e-12)
        assert math.isclose(_fos(p, r, sl_r), _fos(p, s, sl), rel_tol=1e-12)

    def test_the_probabilistic_rebuild_too(self):
        from ogr_core.statistics.probabilistic import _rebuild_surface
        p, s, sl = self._evaluated()
        r = _rebuild_surface(s.to_dict())
        sl_r = slice_surface(p, r, num_slices=60)
        assert sl_r is not None
        assert _same_wall(r.tension_crack_wall, s.tension_crack_wall)
        assert math.isclose(_fos(p, r, sl_r), _fos(p, s, sl), rel_tol=1e-12)

    def test_the_wall_is_drawn_once(self):
        p, s, _sl = self._evaluated()
        r = SlipSurface.from_dict(s.to_dict())
        assert len(r.tension_cracks) == 1          # brought back for drawing
        assert slice_surface(p, r, num_slices=60) is not None
        assert len(r.tension_cracks) == 1, r.tension_cracks
