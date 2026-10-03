# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D226c — the pore pressures that read the weight follow the weight a design
standard factored: Ru, the excess pore pressure of B-bar loading, and the
water the prescribed-inclination methods integrate on the inter-slice faces.

**The invariant.** In a design-standard analysis the slice weight is the
factored one, and so is every term that reads it: Ru's u = ru·σv takes the
factor the slice's soil took (the ponded water above it does not, it is not
soil), the B-bar excess takes it on the bands that load and each load's own
factor on the loads that create excess. Until v0.1.243 those pore pressures
were computed from the UNFACTORED weight while the weight was factored, and
a design standard made a slope look SAFER than its characteristic model: on
the c′ = 0 slope below with EN 1997-1 DA1-C1, where homogeneity asks Γ = F,
Γ/F was 1.085–1.094 with Ru = 0.25 and 1.233–1.291 with a B-bar of 0.5.

What each class pins, and against what
--------------------------------------
1. Homogeneity, in the nine methods: with c′ = 0 and every permanent action
   scaled alike (γG on the whole weight, or γG = γG,fav slice by slice), all
   forces scale and Γ = F — with Ru, with a B-bar soil loading itself and
   with an embankment that loads a foundation of B-bar > 0.
2. By hand: u under ponded water with Ru is ru·(ξ·γ·z + γw·d); slice by
   slice each base takes its own slice's ξ; a load that creates excess adds
   B̄ times its own factored stress (× 1.35 permanent and driving, × 0
   variable and resisting).
3. The inter-slice water thrust of Lowe-Karafiath and the Corps methods
   scales with the soil's factor.
4. Nothing moves without a standard (u is the formula it always was) and,
   with the switch off (``slicer.DESIGN_PORE_PRESSURE_FOLLOWS_WEIGHT``), the
   v0.1.243 number; the user's project is never touched.

The slope is the one of ``test_tension_crack_truncation_v1109`` (γ = 19)
with c′ = 0 and φ′ = 40° unless said, its circle (55; 58) R 34 sliding right
to left, 160 slices, methods to 1e-12. Comparisons are relative, never ``==``
on doubles of different computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_CX = 55.0
_RU = 0.25
_SLICES = 160
_REL = 5e-9


def _slope(kind="ru", pond=None):
    """The c′ = 0 slope with Ru (``ru``), a B-bar soil that loads itself
    (``bbar``) or neither; ``pond`` a water table at that elevation, which
    ponds over the face below it."""
    import test_tension_crack_truncation_v1109 as U
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    p = U._phi0_slope(crack_y=None)
    m = p.materials[0]
    m.strength = MohrCoulomb(cohesion=0.0, friction_angle=40.0)
    if kind == "ru":
        m.pore_pressure = PorePressureType.RU_COEFFICIENT
        m.ru = _RU
    elif kind == "bbar":
        p.settings.groundwater.excess_pore_pressure = True
        m.b_bar = 0.5
        m.weight_creates_excess = True
    if pond is not None:
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0.0, pond), Vertex(100.0, pond)],
            closed=False), btype=BoundaryType.WATER_TABLE))
    return p


def _embankment():
    """A fill (y > 30) whose weight loads, B-bar 0 itself, over a clay of
    B-bar 0.6 that does not load: the shape the B-bar method is for."""
    import test_tension_crack_truncation_v1109 as U
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    p = U._phi0_slope(crack_y=None)
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(45.0, 30.0), Vertex(100.0, 30.0)], closed=False),
        btype=BoundaryType.MATERIAL))
    fill = Material(name="Fill", unit_weight=20.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=38.0))
    fill.weight_creates_excess = True
    clay = Material(name="Clay", unit_weight=18.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=32.0))
    clay.b_bar = 0.6
    p.materials = [fill, clay]
    p.settings.groundwater.excess_pore_pressure = True
    p.assign_material_at(70.0, 35.0, fill.id)
    p.assign_material_at(70.0, 10.0, clay.id)
    return p


def _da1c1(p):
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset("eurocode7_da1c1")
    return p


def _custom(p, unfav, fav, single):
    ds = p.settings.design_standard
    ds.enabled = True
    ds.standard = "custom"
    ds.factor_permanent = unfav
    ds.factor_permanent_favourable = fav
    ds.single_source_weight = single
    return p


def _sliced(p):
    from ogr_core.project.design_factors import prepare_analysis_project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    work, _rep = prepare_analysis_project(p)
    c = SlipCircle(centre_x=_CX, centre_y=58.0, radius=34.0)
    sl = slice_surface(work, c, num_slices=_SLICES)
    assert sl is not None
    return work, c, sl


def _fos(p, method="bishop_simplified"):
    from ogr_slip2d.methods import get_method
    work, c, sl = _sliced(p)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel)


def _depth(s):
    return 0.5 * (s.top_y_left + s.top_y_right) - 0.5 * (
        s.base_y_left + s.base_y_right)


# ======================================================================
class TestHomogeneity:
    """c′ = 0 and every permanent action scaled alike: Γ = F."""

    def _nine_scale(self, build):
        for m in _nine():
            a = _fos(build(), m)
            b = _fos(_da1c1(build()), m)
            assert _close(a, b), (m, a, b, b / a)
            c = _fos(_custom(build(), 1.35, 1.35, False), m)
            assert _close(a, c), (m, a, c, c / a)

    def test_with_ru(self):
        self._nine_scale(lambda: _slope("ru"))

    def test_with_a_b_bar_soil_loading_itself(self):
        self._nine_scale(lambda: _slope("bbar"))

    def test_with_an_embankment_on_a_b_bar_foundation(self):
        _w, _c, sl = _sliced(_embankment())
        assert any(s.pore_pressure > 1.0 for s in sl.slices), (
            "premise: the fill loads the clay under the surface")
        self._nine_scale(_embankment)


class TestByHand:

    def test_ru_under_ponded_water(self):
        """u = ru·(ξ·γ·z + γw·d): the soil's factor, not the water's."""
        for build, xi in ((lambda: _slope("ru", pond=30.0), 1.0),
                          (lambda: _da1c1(_slope("ru", pond=30.0)), 1.35)):
            work, _c, sl = _sliced(build())
            gamma_w = work.settings.groundwater.pore_fluid_unit_weight
            wet = [s for s in sl.slices
                   if 0.5 * (s.top_y_left + s.top_y_right) < 29.0]
            assert len(wet) > 5, "premise: slices under the pond"
            for s in wet:
                d = 30.0 - 0.5 * (s.top_y_left + s.top_y_right)
                want = _RU * (xi * 19.0 * _depth(s) + gamma_w * d)
                assert _close(s.pore_pressure, want, 1e-12), (
                    s.x_centre, s.pore_pressure, want)

    def test_each_base_takes_its_own_slices_factor(self):
        _w, _c, sl = _sliced(_custom(_slope("ru"), 1.35, 0.9, False))
        for s in sl.slices:
            xi = 1.35 if s.x_centre > _CX else 0.9
            assert s.weight_factor == xi
            assert _close(s.pore_pressure, _RU * xi * 19.0 * _depth(s),
                          1e-12), (s.x_centre, s.pore_pressure)

    def test_a_load_adds_its_own_factored_stress(self):
        """B̄ = 0.5 and no loading soil: under the crest a permanent load
        that drives (× 1.35), on the face a variable one that resists (× 0,
        it is left out, and so is its excess)."""
        from test_load_actions_v1243 import _crest, _face

        def build():
            p = _slope(None)
            p.settings.groundwater.excess_pore_pressure = True
            p.materials[0].b_bar = 0.5
            crest, face = _crest(20.0, "permanent"), _face(20.0)
            crest.creates_excess_pore_pressure = True
            face.creates_excess_pore_pressure = True
            p.distributed_loads = [crest, face]
            return p
        _w, _c, plain = _sliced(build())
        _w, _c, sl = _sliced(_da1c1(build()))
        under_crest = [i for i, s in enumerate(sl.slices)
                       if 62.5 < s.x_centre < 77.5]
        under_face = [i for i, s in enumerate(sl.slices)
                      if 42.5 < s.x_centre < 51.5]
        assert under_crest and under_face
        for i in under_crest:
            assert _close(plain.slices[i].pore_pressure, 10.0, 1e-12)
            assert _close(sl.slices[i].pore_pressure, 13.5, 1e-12)
        for i in under_face:
            assert _close(plain.slices[i].pore_pressure, 10.0, 1e-12)
            assert sl.slices[i].pore_pressure == 0.0


class TestTheInterSliceWater:

    def test_the_thrust_scales_with_the_soil(self):
        from ogr_slip2d.external_forces import interslice_water_thrust
        work, _c, plain = _sliced(_slope("ru"))
        work_d, _c, sl = _sliced(_da1c1(_slope("ru")))
        a = interslice_water_thrust(work, plain)
        b = interslice_water_thrust(work_d, sl)
        assert sum(a) > 100.0, "premise: water on the faces"
        for x, y in zip(a, b):
            assert _close(y, 1.35 * x, 1e-12), (x, y)


# ======================================================================
class TestNothingElseMoves:

    def test_without_a_standard_u_is_the_formula_it_always_was(self):
        work, _c, sl = _sliced(_slope("ru"))
        for s in sl.slices:
            depth = max(0.0, 0.5 * (s.top_y_left + s.top_y_right)
                        - 0.5 * (s.base_y_left + s.base_y_right))
            assert _close(s.pore_pressure, _RU * (19.0 * depth), 1e-15)

    def test_a_material_that_reads_no_weight_is_left_alone(self):
        """A water table under the slope: u is γw·h whatever the factor."""
        from ogr_core.materials import PorePressureType

        def build():
            p = _slope(None, pond=None)
            from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                           Vertex)
            p.add_boundary(Boundary(polyline=Polyline(
                vertices=[Vertex(0.0, 26.0), Vertex(100.0, 30.0)],
                closed=False), btype=BoundaryType.WATER_TABLE))
            p.materials[0].pore_pressure = PorePressureType.WATER_TABLE
            return p
        _w, _c, plain = _sliced(build())
        _w, _c, sl = _sliced(_da1c1(build()))
        assert any(s.pore_pressure > 1.0 for s in plain.slices)
        for a, b in zip(plain.slices, sl.slices):
            assert a.pore_pressure == b.pore_pressure

    def test_off_it_is_the_v0_1_243_number(self):
        import ogr_slip2d.slicer as S
        saved = S.DESIGN_PORE_PRESSURE_FOLLOWS_WEIGHT
        try:
            S.DESIGN_PORE_PRESSURE_FOLLOWS_WEIGHT = False
            off = _fos(_da1c1(_slope("ru")))
        finally:
            S.DESIGN_PORE_PRESSURE_FOLLOWS_WEIGHT = saved
        # Measured with v0.1.243: 3.089071 against F = 2.827493.
        assert abs(off - 3.089071) < 1e-6, off
        assert _close(_fos(_da1c1(_slope("ru"))), _fos(_slope("ru")))

    def test_the_users_project_is_never_touched(self):
        import json
        p = _da1c1(_slope("ru", pond=30.0))
        before = json.dumps(p.to_dict(), sort_keys=True, default=str)
        _w, _c, sl = _sliced(p)
        assert {s.weight_factor for s in sl.slices} == {1.35}
        assert json.dumps(p.to_dict(), sort_keys=True, default=str) == before
