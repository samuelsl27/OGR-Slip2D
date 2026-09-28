# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — the ``b1`` of Janbu's correction factor follows the soil type of
the slip surface (defect D80 of the verification bank).

THE FACTOR. Janbu (1973) corrects his simplified method, which neglects the
inter-slice shear, by an empirical factor read off curves he computed for
HOMOGENEOUS slopes against his rigorous generalized procedure:

    f0 = 1 + b1·[(d/L) − 1.4·(d/L)²]

with L the chord between the two ends of the slip surface and d the largest
perpendicular distance from that chord to the surface, and

    b1 = 0.69   c only (φ = 0)
    b1 = 0.31   φ only (c = 0)
    b1 = 0.50   c and φ

(also in Abramson, Lee, Sharma & Boyce 2002, §5.5). Janbu's curves are for a
single soil, so they say nothing about a surface that crosses several; the
reference documentation settles that case by taking the c-φ curve (0.50)
whenever the slip surface passes through more than one soil type.

THE DEFECT. Until v0.1.213 the docstring offered the three values, a comment
said "pick from the dominant base material's strength", and the code wrote
``b1 = 0.50`` always: a documented choice that was never made (rule 7).
Measured on the 38 Janbu-corrected rows of the verification bank before the
change, the rule of the reference moves only the single-type surfaces, and
improves seven rows with a published value while worsening one (a reinforced
slope); taking the "dominant" material by base length instead worsens five.

THE INVARIANTS.

1. An IDENTITY: Janbu Corrected is Janbu Simplified times ``f0``, with ``f0``
   recomputed here from the slice geometry and the ``b1`` of the TYPE — not
   read from the method. To 1e-12.
2. The type is the type of EVERY base: c only (Undrained, SHANSEP, the
   undrained-with-depth family, Mohr-Coulomb with φ = 0), φ only
   (Mohr-Coulomb with c = 0), c-φ otherwise; any other envelope by its
   shape (through the origin → φ only, flat → c only); two types on one
   surface give 0.50; two different materials of the same type keep it;
   a base with no strength or infinite strength takes no part.
3. Rule 7: the switch ``B1_BY_SOIL_TYPE`` moves the number — off, every
   surface gets 0.50, as before.
4. The back analysis applies the same factor, so the force needed at the
   method's own factor of safety is still zero.
"""
from __future__ import annotations

import math

OUTLINE = ((0, 0), (120, 0), (120, 40), (70, 40), (30, 20), (0, 20))
#: Deep enough to cross the lower layer of the two-layer cases (y < 12).
CIRCLE = (55.0, 62.0, 55.0)
LAYER_Y = 12.0
N_SLICES = 40

B1 = {"c": 0.69, "phi": 0.31, "c-phi": 0.50}

_CACHE: dict = {}


def _undrained():
    from ogr_core.materials import Undrained
    return Undrained(cohesion=40.0)


def _mc(c, phi):
    from ogr_core.materials import MohrCoulomb
    return MohrCoulomb(cohesion=c, friction_angle=phi)


def _project(upper, lower=None):
    """The 2:1 slope; one material, or ``upper`` over ``lower`` at y = 12."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in OUTLINE], closed=True)
    ext.ensure_ccw()
    p = Project("janbu-b1")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    top = Material(name="upper", unit_weight=19.0, sat_unit_weight=19.0,
                   strength=upper)
    if lower is None:
        p.materials = [top]
        return p
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, LAYER_Y), Vertex(120, LAYER_Y)]),
        btype=BoundaryType.MATERIAL))
    bottom = Material(name="lower", unit_weight=19.0, sat_unit_weight=19.0,
                      strength=lower)
    p.materials = [top, bottom]
    for reg in p.resolve_regions():
        cx, cy = reg.centroid()
        p.assign_material_at(cx, cy, (bottom if cy < LAYER_Y else top).id)
    return p


CASES = {
    "phi=0": (lambda: _project(_undrained()), "c"),
    "c=0": (lambda: _project(_mc(0.0, 30.0)), "phi"),
    "c-phi": (lambda: _project(_mc(10.0, 25.0)), "c-phi"),
    "c over c-phi": (lambda: _project(_undrained(), _mc(10.0, 25.0)),
                     "c-phi"),
    "c over c": (lambda: _project(_undrained(), _mc(60.0, 0.0)), "c"),
    "phi over phi": (lambda: _project(_mc(0.0, 30.0), _mc(0.0, 35.0)),
                     "phi"),
}


def _switch(on):
    from ogr_slip2d.methods import janbu
    old = getattr(janbu, "B1_BY_SOIL_TYPE", None)
    janbu.B1_BY_SOIL_TYPE = on
    return old


def _restore(old):
    from ogr_slip2d.methods import janbu
    if old is None:
        vars(janbu).pop("B1_BY_SOIL_TYPE", None)
    else:
        janbu.B1_BY_SOIL_TYPE = old


def _solve(case, method_id, by_type=True):
    key = (case, method_id, by_type)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = CASES[case][0]()
    cx, cy, r = CIRCLE
    surf = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
    sl = slice_surface(p, surf, num_slices=N_SLICES)
    m = method_registry()[method_id]()
    m.tolerance = 1e-12
    old = _switch(by_type)
    try:
        res = m.compute_fos(p, surf, sl)
    finally:
        _restore(old)
    assert res.fos is not None, (case, method_id, res.error_message)
    _CACHE[key] = (p, res)
    return p, res


def _shape_term(slices):
    """``(d/L) − 1.4·(d/L)²`` from the base vertices, written out here."""
    s_list = list(slices)
    x0, y0 = s_list[0].base_x_left, s_list[0].base_y_left
    x1, y1 = s_list[-1].base_x_right, s_list[-1].base_y_right
    length = math.hypot(x1 - x0, y1 - y0)
    pts = [(x0, y0)] + [(s.base_x_right, s.base_y_right) for s in s_list]
    d = max(abs((y1 - y0) * (px - x0) - (x1 - x0) * (py - y0)) / length
            for px, py in pts)
    r = d / length
    return r - 1.4 * r * r


# ======================================================================
class TestTheFactorFollowsTheSoilType:

    def test_every_case_crosses_what_its_name_says(self):
        """A control on the fixture: the two-layer circles really do cut
        both layers, or the mixed case would be a homogeneous one."""
        for case in ("c over c-phi", "c over c", "phi over phi"):
            _p, res = _solve(case, "janbu_corrected")
            names = {s.material.name for s in res.slices if s.material}
            assert names == {"upper", "lower"}, (case, names)

    def test_corrected_is_simplified_times_f0_of_the_type(self):
        bad = []
        for case, (_build, kind) in CASES.items():
            _p, simp = _solve(case, "janbu_simplified")
            _p, corr = _solve(case, "janbu_corrected")
            f0 = 1.0 + B1[kind] * _shape_term(corr.slices)
            if abs(corr.fos / (simp.fos * f0) - 1.0) > 1e-12:
                bad.append((case, corr.fos / simp.fos, f0))
        assert not bad, bad

    def test_the_result_says_which_b1_it_used(self):
        for case, (_build, kind) in CASES.items():
            _p, corr = _solve(case, "janbu_corrected")
            d = corr.details or {}
            assert d.get("janbu_b1") == B1[kind], (case, d.get("janbu_b1"))
            f0 = 1.0 + B1[kind] * _shape_term(corr.slices)
            assert abs(d.get("janbu_f0", math.nan) - f0) < 1e-12, (case, d)

    def test_the_simplified_method_does_not_carry_a_factor(self):
        _p, simp = _solve("phi=0", "janbu_simplified")
        assert "janbu_b1" not in (simp.details or {})


class TestRuleSeven:

    def test_the_switch_moves_the_single_type_surfaces(self):
        for case in ("phi=0", "c=0", "c over c", "phi over phi"):
            _p, on = _solve(case, "janbu_corrected", True)
            _p, off = _solve(case, "janbu_corrected", False)
            g = _shape_term(on.slices)
            kind = CASES[case][1]
            expected = (1.0 + B1[kind] * g) / (1.0 + 0.5 * g)
            assert abs(on.fos / off.fos - expected) < 1e-12, (case, on.fos,
                                                              off.fos)
            assert abs(on.fos / off.fos - 1.0) > 1e-3, (case, g)
            assert (off.details or {}).get("janbu_b1") == 0.5

    def test_and_leaves_the_mixed_and_c_phi_ones_alone(self):
        for case in ("c-phi", "c over c-phi"):
            _p, on = _solve(case, "janbu_corrected", True)
            _p, off = _solve(case, "janbu_corrected", False)
            assert on.fos == off.fos, (case, on.fos, off.fos)


class TestTheBackAnalysisAppliesTheSameFactor:

    def test_no_force_is_needed_at_the_methods_own_factor(self):
        from ogr_slip2d.back_analysis import required_force
        for case in ("phi=0", "c=0"):
            _p, corr = _solve(case, "janbu_corrected")
            w = sum(s.weight for s in corr.slices)
            ba = required_force(corr.slices, corr.surface, corr.fos,
                                "janbu_corrected", 5.0)
            assert ba.active_force < 1e-6 * w, (case, ba.active_force)


class TestTheTypeOfEachModel:
    """``base_soil_type`` on one material at a time."""

    def _type(self, strength):
        from ogr_core.materials import Material
        from ogr_slip2d.methods.janbu import base_soil_type
        return base_soil_type(Material(name="m", unit_weight=19.0,
                                       strength=strength))

    def test_the_classes_that_say_what_they_are(self):
        from ogr_core.materials import (InfiniteStrength, NoStrength,
                                        UndrainedDistanceToSlope)
        from ogr_core.materials.builtin_models import SHANSEP
        assert self._type(_undrained()) == "c"
        assert self._type(SHANSEP()) == "c"
        assert self._type(UndrainedDistanceToSlope()) == "c"
        assert self._type(_mc(10.0, 25.0)) == "c-phi"
        assert self._type(_mc(0.0, 30.0)) == "phi"
        assert self._type(_mc(40.0, 0.0)) == "c"
        assert self._type(_mc(0.0, 0.0)) is None
        assert self._type(NoStrength()) is None
        assert self._type(InfiniteStrength()) is None

    def test_any_other_envelope_by_its_shape(self):
        """The owner's decision of 2026-09-27: a curve through the origin is
        a frictional soil (0.31, not the unsafe 0.50)."""
        from ogr_core.materials import PowerCurve
        through = PowerCurve(a=3.4, b=0.6, c=0.0, d=0.0, waviness=0.0)
        shifted = PowerCurve(a=3.4, b=0.6, c=0.0, d=5.0, waviness=0.0)
        assert self._type(through) == "phi"
        assert self._type(shifted) == "c-phi"

    def test_a_base_with_no_type_takes_no_part(self):
        """A φ-only layer over a layer with no strength at all is still a
        φ-only surface."""
        from ogr_core.materials import Material, NoStrength
        from ogr_slip2d.methods.janbu import janbu_correction
        _p, corr = _solve("c=0", "janbu_corrected")
        slices = list(corr.slices)
        empty = Material(name="void", unit_weight=19.0, strength=NoStrength())
        original = slices[0].material
        try:
            slices[0].material = empty
            _f0, b1 = janbu_correction(slices)
        finally:
            slices[0].material = original
        assert b1 == 0.31, b1
