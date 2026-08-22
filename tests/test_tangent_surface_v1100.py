# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slip surfaces that daylight with a VERTICAL TANGENT (anomaly A23-1).

WHAT INVARIANT THIS PROTECTS, and what it deliberately does not claim.

A circle whose centre sits at the elevation of the crest leaves the ground
at its own extreme, |x - x_c| = R, where the tangent is vertical. That is an
ordinary configuration — the reference critical circle of verification
problem 23 (Low 1989) is exactly one — and it used to break three separate
ways at once:

1. COVERAGE. ``33.557 - 18.001`` evaluates to 15.556000000000001, one ulp
   past R, so ``SlipCircle.base_y_at`` reported "not on the circle" and the
   slicer dropped the last slice IN SILENCE. The arc came up short, and
   because the missing arc scales as sqrt(slice width) the deficit shrank
   only as 1/sqrt(n): Bishop read 0.897 with 30 slices and was still at
   1.126 with 640, which looks exactly like slow convergence and is not.
   Hence the first case below, which has no tolerance at all: one slice per
   interval, or no surface.

2. ACCURACY. With the slice recovered, taking the base angle from the
   tangent at the slice MIDPOINT and its length from b/cos(alpha) measures
   a fast-turning arc with the secant of its midpoint slope, converging to
   1/sqrt(2) of the true arc at a vertical tangent. Hence the second case,
   which compares against a CLOSED FORM rather than against another slice
   count: with phi = 0, moment equilibrium about the centre of a circular
   surface gives F = c*L_arc*R / M exactly, with M the moment of the
   weight. A test that only compared n against n would have passed on the
   old code, which was 2.6 % wrong at n = 30 and flat.

3. SILENCE. On such a surface the factor of safety genuinely DOES depend on
   the number of slices, for any slicing uniform in x — with the chord base
   the problem-23 circle reads 1.192 at 30 slices and 1.147 at 240, and the
   published reference values are themselves values at a slice count. That
   is not a defect left unfixed; it is a property of the surface, and the
   only wrong thing to do with it is to say nothing. Hence the last case.

The third class pins the invariant where it IS true — a surface that
daylights at an ordinary angle must not depend on the slice count — so that
the first two cannot be satisfied by a formulation that has simply stopped
converging everywhere.

Reference for the closed form: moment equilibrium of a circular surface
with an undrained (phi = 0) strength, e.g. Bishop, A.W. (1955), "The use of
the slip circle in the stability analysis of slopes", Géotechnique 5(1),
7-17, whose F reduces to c*L*R / sum(W*x) when tan phi vanishes, since
m_alpha is then cos(alpha) and c*b/cos(alpha) = c*l.
"""
from __future__ import annotations

import math

import pytest


GAMMA = 20.0          # kN/m3
CU = 40.0             # kPa, undrained, phi = 0

# Centre at the crest elevation (y = 10), so the arc daylights at
# x = 22 + 16 = 38 with a VERTICAL tangent, on the flat crest.
_TANGENT = (22.0, 10.0, 16.0)
# Same model, a circle that daylights at an ordinary angle.
_ORDINARY = (20.0, 22.0, 26.0)
# Same model, centre a hair ABOVE the crest, so the exit is near-vertical
# (89.96 deg) but not exactly on the arc's extreme. This is the second
# trigger: the root is not a round number, and six decimals of it were not
# enough where dy/dx runs to 1600.
_NEAR_TANGENT = (22.0, 10.01, 16.0)

# The circle of the anomaly itself, verification problem 23 (Low 1989).
# Kept as bare numbers rather than as a model: the arithmetic IS the bug.
_A23_CENTRE_X, _A23_CENTRE_Y, _A23_RADIUS = 18.001, 16.000, 15.556


def _slope_project():
    """Homogeneous undrained slope: toe at (10, 0), crest at (30, 10)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import Undrained
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(50, -10), Vertex(50, 10), Vertex(30, 10),
        Vertex(10, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("tangent-exit")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="clay", unit_weight=GAMMA,
                            strength=Undrained(cohesion=CU))]
    return p


def _circle(spec):
    from ogr_slip2d.surface import SlipCircle
    cx, cy, r = spec
    return SlipCircle(centre_x=cx, centre_y=cy, radius=r)


def _sliced(p, spec, n):
    from ogr_slip2d.slicer import slice_surface
    c = _circle(spec)
    return c, slice_surface(p, c, n)


def _bishop(p, spec, n):
    from ogr_slip2d.methods import get_method
    c, sl = _sliced(p, spec, n)
    assert sl is not None, f"the slicer refused the surface at n={n}"
    return get_method("bishop_simplified")().compute_fos(p, c, sl).fos


def _closed_form(p, spec):
    """F = c * L_arc * R / M for a phi = 0 circular surface.

    ``L_arc`` is the exact arc length between the two ground crossings and
    ``M`` the moment of the sliding mass about the centre, integrated to a
    precision far finer than any slicing under test, so the comparison
    measures the slicing and not the reference.
    """
    from ogr_slip2d.slicer import (
        _ground_surface_from_external, _interp_y_on_polyline,
    )
    c = _circle(spec)
    ground = _ground_surface_from_external(p.external_boundary())
    x_l, x_r = c.candidate_chords(ground)[0]

    def psi(x):
        return math.asin(max(-1.0, min(1.0, (x - c.centre_x) / c.radius)))

    arc = c.radius * (psi(x_r) - psi(x_l))

    n = 100_000
    dx = (x_r - x_l) / n
    moment = 0.0
    for i in range(n):
        x = x_l + dx * (i + 0.5)
        h = _interp_y_on_polyline(ground, x) - c.base_y_at(x)
        moment += GAMMA * h * dx * (x - c.centre_x)
    return CU * arc * c.radius / moment


class TestVerticalTangentArithmetic:
    """The one-ulp overshoot that started it, as bare arithmetic."""

    def _a23(self):
        from ogr_slip2d.surface import SlipCircle
        return SlipCircle(centre_x=_A23_CENTRE_X, centre_y=_A23_CENTRE_Y,
                          radius=_A23_RADIUS)

    def test_the_arc_extreme_is_on_the_arc(self):
        """``33.557 - 18.001`` is 15.556000000000001, so the exit of the
        problem-23 circle sits one ulp outside its own radius. Reading that
        as "not on the circle" is what cost the last slice."""
        c = self._a23()
        x_exit = _A23_CENTRE_X + _A23_RADIUS
        assert (x_exit - _A23_CENTRE_X) > _A23_RADIUS, (
            "the fixture no longer reproduces the round-off it was "
            "built for")
        y = c.base_y_at(x_exit)
        assert y is not None, "base_y_at refused the arc's own extreme"
        assert y == pytest.approx(_A23_CENTRE_Y, abs=1e-9)

    def test_the_tangent_there_is_vertical_not_horizontal(self):
        """It used to answer 0 rad — not imprecise, backwards."""
        c = self._a23()
        a = math.degrees(c.base_angle_at(_A23_CENTRE_X + _A23_RADIUS))
        assert a == pytest.approx(90.0, abs=1e-6), a
        a_left = math.degrees(c.base_angle_at(_A23_CENTRE_X - _A23_RADIUS))
        assert a_left == pytest.approx(-90.0, abs=1e-6), a_left

    def test_the_ground_crossing_keeps_its_precision(self):
        """Rounding the crossing to six decimals is harmless in x and not in
        y: next to a near-vertical tangent dy/dx is in the thousands, so it
        placed the endpoint ~2e-4 above the ground — past the tolerance that
        decided whether the last slice existed."""
        from ogr_slip2d.slicer import _ground_surface_from_external
        from ogr_slip2d.surface import ground_y_at

        p = _slope_project()
        ground = _ground_surface_from_external(p.external_boundary())
        c = _circle(_NEAR_TANGENT)
        chords = c.candidate_chords(ground)
        assert chords, "the near-tangent circle found no sliding mass"
        for x_l, x_r in chords:
            for x in (x_l, x_r):
                off = abs(c.base_y_at(x) - ground_y_at(ground, x))
                assert off < 1e-9 * c.radius, (x, off)


class TestSliceCoverage:
    """The slicer builds one slice per interval, or refuses the surface."""

    def test_no_slice_is_dropped_at_a_vertical_tangent(self):
        p = _slope_project()
        for spec in (_TANGENT, _NEAR_TANGENT):
            for n in (30, 60, 120):
                _c, sl = _sliced(p, spec, n)
                assert sl is not None, (spec, n)
                assert len(sl) == n, (spec, n, len(sl))

    def test_the_arc_reaches_the_ground_crossings(self):
        """The dropped slice was always the last one, so the arc stopped
        short of the exit — and that missing arc was 25 % of the factor."""
        p = _slope_project()
        for n in (30, 60, 120):
            c, sl = _sliced(p, _TANGENT, n)
            assert sl[-1].base_x_right == pytest.approx(c.x_right, abs=1e-9)
            assert sl[0].base_x_left == pytest.approx(c.x_left, abs=1e-9)

    def test_the_exit_really_is_the_vertical_tangent(self):
        """Guards the fixture itself: if this circle ever stopped exiting at
        |x - x_c| = R the rest of the file would be testing nothing."""
        p = _slope_project()
        c, _sl = _sliced(p, _TANGENT, 30)
        assert c.x_right == pytest.approx(c.centre_x + c.radius, abs=1e-9)
        assert abs(math.degrees(c.base_angle_at(c.x_right))) == \
            pytest.approx(90.0, abs=1e-6)


class TestClosedForm:
    """The external anchor: phi = 0 moment equilibrium has an exact answer."""

    def test_bishop_matches_the_closed_form(self):
        p = _slope_project()
        exact = _closed_form(p, _TANGENT)
        got = _bishop(p, _TANGENT, 120)
        assert abs(got - exact) / exact < 0.01, (got, exact)

    def test_the_error_shrinks_with_refinement(self):
        """Not a convergence test between slice counts — a check that the
        distance to a KNOWN answer goes down. The old slicing failed this
        one from below while looking perfectly convergent."""
        p = _slope_project()
        exact = _closed_form(p, _TANGENT)
        errors = [abs(_bishop(p, _TANGENT, n) - exact) / exact
                  for n in (30, 60, 120)]
        assert errors[1] < errors[0], errors
        assert errors[2] < errors[1], errors


class TestOrdinaryExitStillConverges:
    """Where the invariant holds, it has to keep holding."""

    def test_factor_of_safety_does_not_depend_on_the_slice_count(self):
        p = _slope_project()
        values = [_bishop(p, _ORDINARY, n) for n in (30, 60, 120)]
        spread = max(values) / min(values) - 1.0
        assert spread < 0.01, values

    def test_this_surface_is_not_tangent(self):
        """Otherwise this class would be the same case as the first."""
        p = _slope_project()
        c, _sl = _sliced(p, _ORDINARY, 30)
        assert abs(math.degrees(c.base_angle_at(c.x_right))) < 85.0


class TestTheRunSaysSo:
    """A factor of safety that depends on n must not be reported silently."""

    def _note(self, spec, n=30):
        from ogr_slip2d.analysis_runner import daylight_tangent_note
        from ogr_slip2d.methods import get_method
        p = _slope_project()
        c, sl = _sliced(p, spec, n)
        res = get_method("bishop_simplified")().compute_fos(p, c, sl)
        return daylight_tangent_note(res, n)

    def test_a_vertical_exit_is_reported(self):
        notes = self._note(_TANGENT)
        assert notes, "a 90 deg exit produced no warning"
        assert "90" in notes[0]
        assert "30 slices" in notes[0]

    def test_an_ordinary_exit_is_not(self):
        assert self._note(_ORDINARY) == []
