# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — the vertical effective stress a strength model or a bond law is
handed includes the water standing on the ground (defect D166 of the
verification bank).

THE DEFECT, twice. ``BishopSimplified._local_c_phi`` built the context of the
models that need one (SHANSEP reads ``sigma_v_eff``) from

    sigma_v_eff = max(slice_.weight / b - u, 0)

and ``ogr_core.support.bond.sigma_v_effective_at`` weighed the soil column
and the surcharge and subtracted the pore pressure. Neither added the ponded
water, which the slicer keeps out of ``weight`` on purpose (so that the
seismic coefficients do not act on it) — while the pore pressure at the base
DOES carry the head of that water. Under a reservoir the estimate fell by
``γ_w·d`` and was clipped to zero: SHANSEP then silently fell back to
``su(σ'_n)``, the symptom v0.1.67 described on Pilarcitos ("all the undrained
strengths came out zero").

THE ANCHOR is Terzaghi's principle of effective stress: a column of free
water standing on the ground raises the total vertical stress and the pore
pressure by the same ``γ_w·d``, so under a submerged face

    σ'_v = γ'·h      (γ' = γ_sat − γ_w, h the soil column)

and it does NOT depend on the depth of the water. The reference
documentation writes the same sum in its excess-pore-pressure example:
``σ'_v = (30·124.8 + 40·62.4) − 70·62.4`` for 30 ft of soil under 40 ft of
water. The cases read σ'_v back through SHANSEP (``su = S·σ'_v·OCR^m``, Ladd
and Foott 1974) and through the bond law's own function, at two reservoir
levels, and demand both the value and the independence.

What does NOT move: a model with no water on the ground, bit for bit (the
water weight is zero there), and the verification bank, where no SHANSEP
material exists and the one reinforced model with a reservoir (problem 92)
has none of its sheets under the water.
"""
from __future__ import annotations

GAMMA_W = 9.81
GAMMA = 20.0
LEVELS = (72.0, 76.0)
S_RATIO, M_EXP, OCR = 0.25, 0.8, 1.0
CIRCLE = dict(centre_x=52.0, centre_y=186.0, radius=158.2)
N_SLICES = 25

_CACHE: dict = {}


def _project(level=None, strength=None):
    """The dam face of ``test_m_alpha_ponded_v1188`` with a SHANSEP clay."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import SHANSEP
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(260, 0), Vertex(260, 78),
        Vertex(205, 78), Vertex(145, 58),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ponded-shansep")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if level is not None:
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(-5, level),
                                        Vertex(265, level)], closed=False),
            btype=BoundaryType.WATER_TABLE))
    p.materials = [Material(
        name="clay", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=strength or SHANSEP(S=S_RATIO, m=M_EXP, OCR=OCR,
                                     su_min=0.0),
        pore_pressure=(PorePressureType.WATER_TABLE if level is not None
                       else PorePressureType.NONE))]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


def _slices(level):
    if level not in _CACHE:
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _project(level)
        _CACHE[level] = (p, slice_surface(p, SlipCircle(**CIRCLE),
                                          num_slices=N_SLICES).slices)
    return _CACHE[level]


def _sigma_v_seen(s):
    """σ'_v as SHANSEP saw it: its strength does not depend on σ'_n, so the
    linearisation returns c = su and tan φ = 0 at any stress."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    c, tan_phi = BishopSimplified._local_c_phi(s, s.material, 50.0)
    assert abs(tan_phi) < 1e-9, tan_phi
    return c / (S_RATIO * OCR ** M_EXP)


def _submerged(s, level):
    return max(s.top_y_left, s.top_y_right) < level


def _straight_top(s):
    """A slice whose ground is ONE segment. Where a profile vertex falls
    inside the slice the soil column is its exact mean height
    (``top_y_mean``) while the ponded water stands on the chord midpoint,
    so ``γ'·h`` holds there only to the size of the corner cut off; the
    independence from the water depth holds everywhere."""
    mid = 0.5 * (s.top_y_left + s.top_y_right)
    return s.top_y_mean is None or abs(s.top_y_mean - mid) < 1e-9


# ======================================================================
class TestShansepSeesTheBuoyantWeight:

    def test_the_fixture_is_under_water(self):
        _p, sl = _slices(LEVELS[0])
        assert sum(1 for s in sl if _submerged(s, LEVELS[0])) >= 5

    def test_sigma_v_is_the_buoyant_column(self):
        _p, sl = _slices(LEVELS[0])
        bad, seen = [], 0
        for s in sl:
            if not (_submerged(s, LEVELS[0]) and _straight_top(s)):
                continue
            seen += 1
            expected = (GAMMA - GAMMA_W) * s.height
            got = _sigma_v_seen(s)
            if abs(got - expected) > 1e-9 * max(1.0, expected):
                bad.append((s.index, got, expected))
        assert seen >= 5 and not bad, (seen, bad[:3])

    def test_and_does_not_depend_on_the_depth_of_the_water(self):
        _p1, low = _slices(LEVELS[0])
        _p2, high = _slices(LEVELS[1])
        compared = 0
        for a, b in zip(low, high):
            if not (_submerged(a, LEVELS[0]) and _submerged(b, LEVELS[1])):
                continue
            compared += 1
            va, vb = _sigma_v_seen(a), _sigma_v_seen(b)
            assert abs(va - vb) <= 1e-12 * max(1.0, va), (a.index, va, vb)
        assert compared >= 5, compared

    def test_a_dry_model_is_bit_for_bit_what_it_was(self):
        """``su`` written exactly as SHANSEP computes it from ``W/b − u``."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _project(None)
        for s in slice_surface(p, SlipCircle(**CIRCLE),
                               num_slices=N_SLICES).slices:
            b = max(s.width, 1e-9)
            su = max(max(s.weight / b - s.pore_pressure, 0.0), 0.0) \
                * S_RATIO * (max(OCR, 1e-6) ** M_EXP)
            c, _t = BishopSimplified._local_c_phi(s, s.material, 50.0)
            assert s.water_weight == 0.0 and s.pore_pressure == 0.0
            assert c == su, (s.index, c, su)


class TestTheBondLawSeesTheBuoyantWeight:
    """``sigma_v_effective_at`` below the submerged face of the same dam:
    the ground at x = 100 is at y = 40, 32 m under the lower reservoir."""

    X, GROUND = 100.0, 40.0

    def test_sigma_v_is_the_buoyant_column(self):
        from ogr_core.support.bond import sigma_v_effective_at
        for level in LEVELS:
            p = _project(level)
            for depth in (2.0, 10.0, 25.0):
                sv, u, d = sigma_v_effective_at(p, self.X,
                                                self.GROUND - depth)
                assert abs(d - depth) < 1e-9, (d, depth)
                assert abs(u - GAMMA_W * (level - self.GROUND + depth)) \
                    < 1e-9 * u, (u, level, depth)
                expected = (GAMMA - GAMMA_W) * depth
                assert abs(sv - expected) < 1e-9 * expected, (level, depth,
                                                              sv, expected)

    def test_a_dry_point_is_unchanged(self):
        from ogr_core.support.bond import sigma_v_effective_at
        p = _project(None)
        sv, u, d = sigma_v_effective_at(p, self.X, self.GROUND - 10.0)
        assert u == 0.0 and abs(sv - GAMMA * 10.0) < 1e-9, (sv, u)


class TestThePublishedExample:
    """The reference documentation works one example in its page on excess
    pore pressure: 30 ft of soil at 124.8 lb/ft3 under 40 ft of water at
    62.4 lb/ft3 give an effective vertical stress of 1872 lb/ft2, the sum
    written with the water column inside the total stress. Units do not
    enter the arithmetic, so the same numbers go in as they stand."""

    def test_thirty_feet_under_forty_feet_of_water(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb, PorePressureType
        from ogr_core.project import Project
        from ogr_core.support.bond import sigma_v_effective_at
        ext = Polyline(vertices=[Vertex(0, -60), Vertex(100, -60),
                                 Vertex(100, 0), Vertex(0, 0)], closed=True)
        ext.ensure_ccw()
        p = Project("published-example")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(-5, 40.0), Vertex(105, 40.0)], closed=False),
            btype=BoundaryType.WATER_TABLE))
        p.materials = [Material(
            name="soil", unit_weight=124.8, sat_unit_weight=124.8,
            strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0),
            pore_pressure=PorePressureType.WATER_TABLE)]
        p.settings.groundwater.pore_fluid_unit_weight = 62.4
        sv, u, depth = sigma_v_effective_at(p, 50.0, -30.0)
        assert abs(depth - 30.0) < 1e-9 and abs(u - 70 * 62.4) < 1e-9
        assert abs(sv - 1872.0) < 1e-9, sv
