# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — the pseudo-static earthquake is a body force proportional to the
STATIC weight in each direction, and a positive vertical coefficient points
DOWN (defect D170 of the verification bank).

THE CONVENTION, and where it comes from. A pseudo-static analysis replaces the
shaking by the inertial forces of the sliding mass, mass times acceleration in
each direction: ``F_h = k_h·W`` and ``F_v = k_v·W``, both on the static weight
W (Terzaghi 1950; Kramer 1996, §10.6.1; EN 1998-5:2004, §4.1.3.3, ``F_H =
0.5·α·S·W`` and ``F_V = ±0.5·F_H``). What the SIGN of ``k_v`` means is a
definition, and OGR states it in four places — ``SeismicLoad``, the seismic
dialog twice and ``slice_forces`` — the way the reference documentation does:
"a POSITIVE vertical seismic coefficient represents a vertical seismic force
directed DOWNWARDS". So the vertical load is ``W + k_v·W = W·(1 + k_v)``, and
the excess-pore-pressure module already reads it that way (``k_v·σ_v`` ADDS
vertical stress).

THE DEFECT. Until v0.1.213 ``slice_forces`` applied ``W·(1 − k_v)`` — the
opposite sense — and ``F_h = k_h·W·(1 − k_v)``. The second is wrong with
EITHER sign: the horizontal inertial force of a mass does not depend on its
vertical acceleration (orthogonal components of Newton's second law, one
mass). Mononobe-Okabe and EN 1998-5 Annex E write the resultant's inclination
as ``tan θ = k_h / (1 ± k_v)``, which only comes out with ``F_h = k_h·W``;
scaling ``F_h`` by ``(1 − k_v)`` would make it ``k_h``, whatever ``k_v``.
Measured on the plane below (kh = 0.15, kv = +0.1): 0.711390 before, against
0.691024 for the closed form with kv down and 0.691573 with kv up.

THE ANCHORS, none of them a captured value:

1. A CLOSED FORM (rule 1). On a plane the sliding mass is one free body and
   the inter-slice forces cancel, so every method that closes global force
   equilibrium owes the Coulomb wedge under pseudo-static loading
   (Kramer 1996, §10.6.1.1):

       F = [c·L + (W(1+k_v)·cos β − k_h·W·sin β)·tan φ]
           / [W(1+k_v)·sin β + k_h·W·cos β]

   with W from the GEOMETRY of the wedge, not from the slicer. Janbu, the two
   Corps of Engineers and Lowe-Karafiath reproduce it to the solver tolerance.
   (Spencer and GLE on this plane with ``k_h ≠ 0`` fall back to the edge of
   their λ range and are not asserted here: recorded against D143.)

2. Two IDENTITIES on a circle with φ = 0 and constant c_u, where the moment
   balance is ``F = Σc·l·R / [(1+k_v)·ΣW·x + k_h·ΣW·(y_c − y_g)]``:

       F(0, k_v)·(1 + k_v) = F(0, 0)
       1/F(k_h, k_v) − 1/F(k_h, 0) = k_v / F(0, 0)

   The second DISCRIMINATES the coupling: with ``F_h = k_h·W·(1+k_v)`` it
   would read ``F(k_h, k_v)·(1+k_v) = F(k_h, 0)`` instead, and that is
   asserted NOT to hold.

3. ONE sense of "down" in OGR, by executing both: the weight and the seismic
   excess pore pressure grow together with a positive ``k_v``.

4. ``k_v = 0`` is bit for bit what it was, which is the whole verification
   bank (the seismic models there all have ``k_v = 0``).

DISCRIMINATION against the v0.1.213 tree: see the changelog of v0.1.214.
"""
from __future__ import annotations

import math

# The 56.3° slope of ``test_janbu_wedge_v1142``, so a plane of 40° daylights
# on the crest plateau.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
BETA = 40.0
NSLICES = 50
#: The four methods that close global force equilibrium on a plane and
#: reproduce the static wedge to the last digit (see the header).
WEDGE_METHODS = ("janbu_simplified", "corps_engineers_1",
                 "corps_engineers_2", "lowe_karafiath")
#: How close each one lands. Janbu iterates on ``tolerance`` and reaches
#: 4e-13 at 1e-12; the prescribed-inclination family closes its force
#: balance with a bisection of its own that does not read ``tolerance`` and
#: stops at 1e-10 to 2e-9 relative on this plane (measured, the same with
#: 1e-8 and 1e-14). Either band is four orders below what the convention
#: moves here (5 to 10 %).
WEDGE_TOL = {"janbu_simplified": 1e-11}
WEDGE_TOL_DEFAULT = 1e-8
#: (kh, kv): both signs of kv, with and without kh.
SHAKES = ((0.0, 0.2), (0.0, -0.2), (0.15, 0.1), (0.15, -0.1), (0.1, 0.0))

#: The 2:1 undrained slope and circle of the D170 record (c_u = 40 kPa).
OUTLINE_21 = ((0, 0), (120, 0), (120, 40), (70, 40), (30, 20), (0, 20))
CIRCLE_21 = (55.0, 62.0, 48.0)
CU = 40.0

_CACHE: dict = {}


# ======================================================================
def _daylight_x():
    return TOE + H / math.tan(math.radians(BETA))


def _wedge_project(kh, kv):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("wedge")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh = kh
    p.seismic.kv = kv
    return p


def _plane():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(), H)]))


def _closed_wedge(kh, kv):
    """The pseudo-static Coulomb wedge, from the geometry alone."""
    w = GAMMA * 0.5 * H * (_daylight_x() - CREST)
    length = math.hypot(_daylight_x() - TOE, H)
    b = math.radians(BETA)
    t = math.tan(math.radians(PHI))
    wv = w * (1.0 + kv)
    return ((COH * length + (wv * math.cos(b) - kh * w * math.sin(b)) * t)
            / (wv * math.sin(b) + kh * w * math.cos(b)))


def _solve(method_id, project, surface, n, tolerance=1e-12):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=n)
    m = method_registry()[method_id]()
    m.tolerance = tolerance
    res = m.compute_fos(project, surface, sl)
    assert res.fos is not None, (method_id, res.reason, res.error_message)
    return res


def _wedge_fos(method_id, kh, kv):
    key = ("wedge", method_id, kh, kv)
    if key not in _CACHE:
        _CACHE[key] = _solve(method_id, _wedge_project(kh, kv), _plane(),
                             NSLICES).fos
    return _CACHE[key]


def _circle_project(kh, kv):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, Undrained
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in OUTLINE_21],
                   closed=True)
    ext.ensure_ccw()
    p = Project("undrained-21")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="clay", unit_weight=20.0,
                            sat_unit_weight=20.0,
                            strength=Undrained(cohesion=CU))]
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh = kh
    p.seismic.kv = kv
    return p


def _circle_fos(method_id, kh, kv):
    key = ("circle", method_id, kh, kv)
    if key not in _CACHE:
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = CIRCLE_21
        _CACHE[key] = _solve(method_id, _circle_project(kh, kv),
                             SlipCircle(centre_x=cx, centre_y=cy, radius=r),
                             25).fos
    return _CACHE[key]


# ======================================================================
class TestTheClosedWedge:
    """Anchor 1: the pseudo-static Coulomb wedge on a plane."""

    def test_the_static_wedge_is_the_starting_point(self):
        expected = _closed_wedge(0.0, 0.0)
        for mid in WEDGE_METHODS:
            got = _wedge_fos(mid, 0.0, 0.0)
            tol = WEDGE_TOL.get(mid, WEDGE_TOL_DEFAULT)
            assert abs(got / expected - 1.0) < tol, (mid, got, expected)

    def test_every_force_method_owes_the_closed_form_under_shaking(self):
        bad = []
        for kh, kv in SHAKES:
            expected = _closed_wedge(kh, kv)
            for mid in WEDGE_METHODS:
                got = _wedge_fos(mid, kh, kv)
                tol = WEDGE_TOL.get(mid, WEDGE_TOL_DEFAULT)
                if abs(got / expected - 1.0) >= tol:
                    bad.append((mid, kh, kv, got / expected - 1.0))
        assert not bad, bad

    def test_a_downward_coefficient_is_not_an_upward_one(self):
        """The two conventions give different wedges; the engine must sit on
        the documented one and away from the other."""
        for kv in (0.2, -0.2):
            down = _closed_wedge(0.0, kv)
            up = _closed_wedge(0.0, -kv)
            got = _wedge_fos("janbu_simplified", 0.0, kv)
            assert abs(up / down - 1.0) > 1e-2, (up, down)
            assert abs(got / down - 1.0) < 1e-11, (kv, got, down, up)

    def test_the_horizontal_force_does_not_follow_the_vertical_one(self):
        """``F_h = k_h·W·(1 ± k_v)`` would be a different wedge."""
        kh, kv = 0.15, 0.1
        w = GAMMA * 0.5 * H * (_daylight_x() - CREST)
        length = math.hypot(_daylight_x() - TOE, H)
        b, t = math.radians(BETA), math.tan(math.radians(PHI))
        wv = w * (1.0 + kv)
        coupled = ((COH * length + (wv * math.cos(b)
                                    - kh * wv * math.sin(b)) * t)
                   / (wv * math.sin(b) + kh * wv * math.cos(b)))
        got = _wedge_fos("janbu_simplified", kh, kv)
        assert abs(coupled / _closed_wedge(kh, kv) - 1.0) > 1e-3
        assert abs(got / coupled - 1.0) > 1e-3, (got, coupled)


class TestTheCircleIdentities:
    """Anchor 2: φ = 0 on a circle, where the moment balance is closed."""

    METHODS = ("bishop_simplified", "ordinary_fellenius")

    def test_the_vertical_coefficient_scales_the_driving_moment(self):
        for mid in self.METHODS:
            f0 = _circle_fos(mid, 0.0, 0.0)
            for kv in (0.2, -0.2):
                f = _circle_fos(mid, 0.0, kv)
                assert abs(f * (1.0 + kv) / f0 - 1.0) < 1e-12, (mid, kv, f,
                                                                f0)

    def test_the_force_methods_scale_the_same_way(self):
        """With kh = 0 every load scales by (1 + kv) and the cohesion does
        not, so every method owes F(0)/(1 + kv); Janbu's balance is linear
        in both coefficients, so it owes the second identity as well."""
        for mid, tol in (("janbu_simplified", 1e-12),
                         ("janbu_corrected", 1e-12),
                         ("corps_engineers_1", 1e-8),
                         ("corps_engineers_2", 1e-8),
                         ("lowe_karafiath", 1e-8)):
            f0 = _circle_fos(mid, 0.0, 0.0)
            for kv in (0.2, -0.2):
                f = _circle_fos(mid, 0.0, kv)
                assert abs(f * (1.0 + kv) / f0 - 1.0) < tol, (mid, kv, f, f0)
        for mid in ("janbu_simplified", "janbu_corrected"):
            f00 = _circle_fos(mid, 0.0, 0.0)
            for kv in (0.2, -0.2):
                lhs = (1.0 / _circle_fos(mid, 0.1, kv)
                       - 1.0 / _circle_fos(mid, 0.1, 0.0))
                assert abs(lhs - kv / f00) < 1e-12 / f00, (mid, kv)

    def test_the_d170_record_reads_the_other_way_round_now(self):
        """The record measured 0.6869 / 0.8586 / 0.5724 for kv = 0 / +0.2 /
        -0.2, which is F(0)/(1 - kv): the upward sense. The downward one is
        F(0)/(1 + kv), so +0.2 now LOWERS the factor. The 0.6869 is OGR's
        own number, a GUARD that the fixture is the record's slope, not an
        anchor: the anchor is the identity."""
        f0 = _circle_fos("bishop_simplified", 0.0, 0.0)
        down = _circle_fos("bishop_simplified", 0.0, 0.2)
        up = _circle_fos("bishop_simplified", 0.0, -0.2)
        assert abs(f0 - 0.6869) < 5e-5, f0
        assert down < f0 < up, (down, f0, up)
        assert abs(down - f0 / 1.2) < 1e-12 and abs(up - f0 / 0.8) < 1e-12

    def test_the_vertical_term_does_not_interact_with_the_horizontal(self):
        for mid in self.METHODS:
            f00 = _circle_fos(mid, 0.0, 0.0)
            for kv in (0.2, -0.2):
                lhs = (1.0 / _circle_fos(mid, 0.1, kv)
                       - 1.0 / _circle_fos(mid, 0.1, 0.0))
                assert abs(lhs - kv / f00) < 1e-12 / f00, (mid, kv, lhs,
                                                           kv / f00)

    def test_and_the_coupled_identity_does_not_hold(self):
        """The control: the identity a coupled ``F_h`` would satisfy."""
        f_h0 = _circle_fos("bishop_simplified", 0.1, 0.0)
        f_hv = _circle_fos("bishop_simplified", 0.1, 0.2)
        assert abs(f_hv * 1.2 / f_h0 - 1.0) > 1e-3, (f_hv, f_h0)


class TestOneSenseOfDown:
    """Anchor 3: the weight and the seismic excess pore pressure agree."""

    def test_the_weight_and_the_excess_pore_pressure_move_together(self):
        from ogr_core.hydraulic.excess_pore_pressure import (
            seismic_delta_sigma_v)
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = CIRCLE_21
        for kv in (0.2, -0.2):
            p = _circle_project(0.0, kv)
            p.seismic.creates_excess_pore_pressure = True
            s = slice_surface(p, SlipCircle(centre_x=cx, centre_y=cy,
                                            radius=r), num_slices=25).slices[5]
            heavier = slice_forces(s, 0.0, kv).w_soil - s.weight
            more_stress = seismic_delta_sigma_v(p, 100.0)
            assert heavier * more_stress > 0.0, (kv, heavier, more_stress)
            assert math.copysign(1.0, heavier) == math.copysign(1.0, kv)

    def test_the_two_components_are_on_the_static_weight(self):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = CIRCLE_21
        p = _circle_project(0.15, 0.2)
        for s in slice_surface(p, SlipCircle(centre_x=cx, centre_y=cy,
                                             radius=r), num_slices=25).slices:
            f = slice_forces(s, 0.15, 0.2)
            assert abs(f.w_soil - 1.2 * s.weight) <= 1e-12 * s.weight
            assert abs(f.h_seismic - 0.15 * s.weight) <= 1e-12 * s.weight


class TestKvZeroIsUntouched:
    """Anchor 4: the verification bank runs with k_v = 0 everywhere."""

    def test_bit_for_bit(self):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = CIRCLE_21
        p = _circle_project(0.15, 0.0)
        for s in slice_surface(p, SlipCircle(centre_x=cx, centre_y=cy,
                                             radius=r), num_slices=25).slices:
            f = slice_forces(s, 0.15, 0.0)
            assert f.w_soil == s.weight
            assert f.h_seismic == 0.15 * s.weight
            assert f.w_total == s.weight + s.water_weight


class TestTheBackAnalysisShakesTheSameWay:
    """The back analysis of support force (``back_analysis``) rebuilds the
    driving sum by hand, so it has to apply the earthquake as the solver
    does. Its identity, from v0.1.202: at the method's OWN factor of safety
    the force needed is zero. Read unclipped — ``required_force`` clips
    negatives to zero and would hide exactly this (see D204).

    Until v0.1.214 Bishop's term took the arm ``(y_g − y_c)/R``, the
    opposite of the solver's ``(y_c − y_g)/R``: on this slope at kh = 0.1
    the earthquake cut the driving sum from 4532 to 3093 and the force at
    the method's own factor came out −7599 kN/m."""

    def _force_at_own_factor(self, method_id, kh, kv):
        from ogr_slip2d.back_analysis import _sums_at_fixed_fos
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        from ogr_core.materials import MohrCoulomb
        p = _circle_project(kh, kv)
        p.materials[0].strength = MohrCoulomb(cohesion=15.0,
                                              friction_angle=25.0)
        circ = SlipCircle(centre_x=55.0, centre_y=62.0, radius=48.0)
        sl = slice_surface(p, circ, num_slices=30)
        res = _solve(method_id, p, circ, 30)
        resisting, driving, arm = _sums_at_fixed_fos(
            sl.slices, circ, res.fos, kh, kv, 30.0, method_id)
        return (res.fos * driving - resisting) / arm, driving

    def test_zero_at_the_methods_own_factor_under_shaking(self):
        for kh, kv in ((0.1, 0.0), (0.1, 0.1), (0.1, -0.1)):
            force, _d = self._force_at_own_factor("janbu_simplified", kh, kv)
            assert abs(force) < 1e-6, (kh, kv, force)
            # Bishop keeps the residual of its normal-force estimate, a few
            # tenths of a percent of the driving sum; the sign error was
            # 2.5 times the whole sum.
            force, d = self._force_at_own_factor("bishop_simplified", kh, kv)
            assert abs(force) < 5e-3 * abs(d), (kh, kv, force, d)

    def test_the_earthquake_adds_to_the_driving_sum(self):
        _f, still = self._force_at_own_factor("bishop_simplified", 0.0, 0.0)
        _f, shaken = self._force_at_own_factor("bishop_simplified", 0.1, 0.0)
        assert shaken > still, (still, shaken)
