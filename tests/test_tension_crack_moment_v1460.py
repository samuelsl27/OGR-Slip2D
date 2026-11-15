# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.460 (D428) — the water in a tension crack acts a third of the WATER's
height above the crack bottom, and the methods take its moment there.

WHAT WAS WRONG, AND WHAT WAS NOT

``Slices.tension_crack_arm`` was documented as "the vertical distance from
the crack base to the centroid of the water column". It is neither: the
slicer stores an ELEVATION, ``crack_bottom_y + h_w / 3``, and h/3 is the
centroid of the triangular pressure diagram (Terzaghi 1943), not of the
column (h/2). The comment is fixed in this version.

In v0.1.459 the MOMENT was right: no method reads the field; the methods
that take moments read the moment ``add_water_force(f_h, y=...)`` leaves on
the wall slice, at that elevation (the force-equilibrium ones, the force).
What was missing is a test of that line of action. Measured on v0.1.435
with two mutants over the 127 tests of the nine crack files: the line at
h/2 (+0.31 % on the closed form below) failed none, and the line at h/3
above y = 0 (−9.6 %) failed one, a search against a ±5 % band. This file
fails with both. It passes on the tree of v0.1.459, because the moment was
right there: that is stated, not hidden.

The adversarial review of v0.1.460 found that a full crack alone cannot
tell the height of the WATER from the height of the WALL, which are then
the same number: a line at a third of the wall, or at the crest minus two
thirds of the water, passed. The crack is also asked half and a quarter
full, where those lines are 8e-4 and 2.5e-3 off the closed form.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

* **The closed form.** On the φ = 0 slope of ``test_tension_crack_
  truncation_v1109`` (its ground, circle, cohesion and unit weight) with the
  crack at y = 34 and the water h_w above its bottom, moment equilibrium of
  the circle about its centre gives, whatever the interslice assumption,

      F = c·L_arc·R / (M_soil + ½·γw·h_w²·(y_c − y_bottom − h_w/3))

  (Bishop 1955; the thrust of a hydrostatic triangle at its centroid,
  Terzaghi 1943). The ends, L_arc and a Simpson quadrature of M_soil are
  written here; γw is written apart, and its premise is that it is the
  project's. Full, Bishop, Spencer, GLE and the Ordinary method give it with
  320 slices to 3e-5 (6.1e-6 measured: the slicing error is O(1/n²), 2.4e-5
  at 160; the margin leaves room for a legitimate change of the slicing, and
  the narrowest mutant is 8e-4 off); half and a quarter full, Bishop and the
  Ordinary method.
* **The moment by hand.** On the wall slice, full, half and a quarter full:
  the crack water's force is −½·γw·h_w² (it pushes to −x, out of the slope),
  its line of action is at the elevation y_bottom + h_w/3, and its moment
  about the centre, through the methods' own ``slice_forces``, is the thrust
  times −(y_c − y_bottom − h_w/3), all to 1e-9.

Measured cost: about 0.7 s for the file in the runner, about 0.45 s of it in
the methods on 320 slices.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from test_tension_crack_truncation_v1109 import (  # noqa: E402
    _C, _CIRCLE, _GAMMA, _ground_y, _phi0_slope,
)

#: The crack line and the crest above it: a 6 m wall.
_CRACK_Y, _TOP_Y = 34.0, 40.0
#: Written apart from the project, so the closed form does not ask the code
#: under test for it; ``test_the_project_uses_the_unit_weight_written_here``
#: checks it is the project's.
_GAMMA_W = 9.81
_N = 320
_FILLS = (100.0, 50.0, 25.0)
_METHODS = ("bishop_simplified", "spencer", "gle_morgenstern_price",
            "ordinary_fellenius")
_TOL = 3e-5


def _arc_y(x):
    cx, cy, r = _CIRCLE["centre_x"], _CIRCLE["centre_y"], _CIRCLE["radius"]
    return cy - math.sqrt(max(r * r - (x - cx) ** 2, 0.0))


def _ends():
    """The left end where the arc meets the ground (bisection), and the
    right one where it meets the crack line, from the geometry alone."""
    cx, cy, r = _CIRCLE["centre_x"], _CIRCLE["centre_y"], _CIRCLE["radius"]
    lo, hi = cx - r, cx
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _ground_y(mid) - _arc_y(mid) > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi), cx + math.sqrt(r * r - (cy - _CRACK_Y) ** 2)


def _closed_form(fill):
    """F, the thrust, its elevation and its moment about the centre, with
    the crack ``fill`` per cent full."""
    cx, cy, r = _CIRCLE["centre_x"], _CIRCLE["centre_y"], _CIRCLE["radius"]
    x_l, x_r = _ends()
    l_arc = r * (math.asin((x_r - cx) / r) - math.asin((x_l - cx) / r))
    n = 20001                                   # odd, so Simpson closes
    h = (x_r - x_l) / (n - 1)
    total = 0.0
    for i in range(n):
        x = x_l + i * h
        w = 1 if i in (0, n - 1) else (4 if i % 2 else 2)
        total += w * _GAMMA * (_ground_y(x) - _arc_y(x)) * (x - cx)
    m_soil = abs(total * h / 3.0)
    hw = (_TOP_Y - _CRACK_Y) * fill / 100.0
    thrust = 0.5 * _GAMMA_W * hw * hw
    line_y = _CRACK_Y + hw / 3.0
    m_water = thrust * (cy - line_y)
    return _C * l_arc * r / (m_soil + m_water), thrust, line_y, m_water


_SLICED = {}


def _sliced(fill=100.0):
    """The crack ``fill`` per cent full, sliced once for the file."""
    if fill not in _SLICED:
        from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                     WaterLevelMode)
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _phi0_slope(crack_y=_CRACK_Y)
        p.tension_crack_properties = TensionCrackProperties(
            mode=WaterLevelMode.PERCENT_FILLED, percent_filled=fill)
        c = SlipCircle(**_CIRCLE)
        sl = slice_surface(p, c, num_slices=_N)
        assert sl is not None, "the premise: the circle is sliced"
        _SLICED[fill] = (p, c, sl)
    return _SLICED[fill]


def _wall_slice(c, sl):
    """The slice whose face is the crack wall: the one at its end."""
    wall_x = c.tension_crack_wall[0]
    first, last = sl.slices[0], sl.slices[-1]
    return last if abs(last.base_x_right - wall_x) < abs(
        first.base_x_left - wall_x) else first


class TestThePremises:

    def test_the_project_uses_the_unit_weight_written_here(self):
        p, _c, _sl = _sliced()
        assert p.settings.groundwater.pore_fluid_unit_weight == _GAMMA_W

    def test_the_slicer_ends_the_circle_on_the_crack_line(self):
        _p, c, sl = _sliced()
        x_l, x_r = _ends()
        assert abs(sl.slices[0].base_x_left - x_l) <= 1e-9 * x_r
        assert abs(sl.slices[-1].base_x_right - x_r) <= 1e-9 * x_r
        wall = c.tension_crack_wall
        assert (math.isclose(wall[1], _CRACK_Y, rel_tol=1e-12)
                and math.isclose(wall[2], _TOP_Y, rel_tol=1e-12)), wall


class TestTheMomentByHand:
    """The crack water on the wall slice, against the hydrostatic triangle,
    full and partly full."""

    def test_the_thrust_its_line_of_action_and_its_moment(self):
        from ogr_slip2d.external_forces import slice_forces
        bad = []
        for fill in _FILLS:
            _f, thrust, line_y, m_water = _closed_form(fill)
            _p, c, sl = _sliced(fill)
            ws = _wall_slice(c, sl)
            got_y = ws.water_force_h_moment / ws.water_force_h
            got_m = slice_forces(ws).water_moment_about(_CIRCLE["centre_y"])
            if (abs(ws.water_force_h + thrust) > 1e-9 * thrust
                    or abs(got_y - line_y) > 1e-9 * _TOP_Y
                    or abs(got_m + m_water) > 1e-9 * m_water):
                bad.append((fill, ws.water_force_h, -thrust, got_y, line_y,
                            got_m, -m_water))
        assert not bad, bad

    def test_the_field_is_the_same_elevation(self):
        bad = []
        for fill in _FILLS:
            _f, _thrust, line_y, _m = _closed_form(fill)
            _p, _c, sl = _sliced(fill)
            if abs(sl.tension_crack_arm - line_y) > 1e-9 * _TOP_Y:
                bad.append((fill, sl.tension_crack_arm, line_y))
        assert not bad, bad


class TestTheClosedForm:
    """Moment equilibrium of a φ = 0 circle, whatever the interslice
    assumption: the methods that close it give F."""

    @staticmethod
    def _check(fill, methods):
        from ogr_slip2d.methods import get_method
        want = _closed_form(fill)[0]
        p, c, sl = _sliced(fill)
        bad = []
        for mid in methods:
            got = get_method(mid)(tolerance=1e-10, max_iterations=400) \
                .compute_fos(p, c, sl).fos
            if got is None or abs(got - want) > _TOL * want:
                bad.append((fill, mid, got, want))
        return bad

    def test_four_methods_give_it_with_the_crack_full(self):
        bad = self._check(100.0, _METHODS)
        assert not bad, bad

    def test_half_and_a_quarter_full(self):
        bad = []
        for fill in (50.0, 25.0):
            bad += self._check(fill, ("bishop_simplified",
                                      "ordinary_fellenius"))
        assert not bad, bad
