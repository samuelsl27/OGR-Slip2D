# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.230 — Janbu's soil type is read on EACH base for the anisotropic
models, and a model read without a slice answers its weakest orientation
(defect D219 of the verification bank).

THE DEFECT. The rule of D80 (v0.1.214) gives Janbu's correction the ``b1``
of the soil type of every base: one type throughout, its ``b1`` (0.69 c
only, 0.31 φ only, 0.50 c and φ); more than one, 0.50. But
``base_soil_type`` read each MATERIAL without a slice, and an anisotropic
model without a slice is not what any base computes with: the Anisotropic
Strength Function answered the row of least COHESION, so a table with a "φ
only" range and a "c only" range was classified by one row. A surface all in
the "c only" range took 0.31; one across both, 0.31 where the rule gives
0.50.

THE DECISIONS (the owner's, 2026-09-30):

* ``base_soil_type(material, slice_)`` reads a model that needs the slice,
  and is not one of the classes named there, with the context of THAT base
  (``SliceContext.from_slice``, moved to ``ogr_core`` bit for bit from where
  every method built it, so the type is read from what the solver reads).
  A switch, ``janbu.SOIL_TYPE_PER_BASE``.
* Without a slice, the WEAKEST orientation: the least strength of the
  function's rows at that stress, of Anisotropic Linear at 0 and 90 degrees
  from the bedding (c and tan φ are linear in t, t monotone in the angle),
  of Generalized's rules.

THE REFERENCES (rule 1): the rule of D80 applied by hand -- the type of each
base's range written out, the ``b1`` it gives, and ``F_corr = f0(b1)·F_simp``
with ``f0`` from the chord and depth of the surface computed here -- and an
anchor: a function whose every base falls in one range gives exactly the
correction of a Mohr-Coulomb material with that row, D80's path.

DISCRIMINATION, measured on the v0.1.229 tree: see the changelog of
v0.1.230.
"""
from __future__ import annotations

import math

#: A dry circle whose 30 bases run from -17.9 to +61.7 degrees.
CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30


def _project(strength):
    """The dry slope of ``test_anisotropic_function_ranges_v1218``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("janbu")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="m", unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _solve(strength, method_id):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _project(strength)
    circle = SlipCircle(*CIRCLE)
    sl = slice_surface(p, circle, num_slices=N_SLICES)
    res = method_registry()[method_id]().compute_fos(p, circle, sl)
    assert res.fos is not None, (method_id, res.reason)
    return res, sl


def _shape(slices):
    """r − 1.4·r², with r = d/L of Janbu (1973), computed here: L the chord
    between the two ends of the surface, d the largest distance from it."""
    s = slices.slices
    x0, y0 = s[0].base_x_left, s[0].base_y_left
    x1, y1 = s[-1].base_x_right, s[-1].base_y_right
    L = math.hypot(x1 - x0, y1 - y0)
    pts = [(x0, y0)] + [(b.base_x_right, b.base_y_right) for b in s]
    d = max(abs((y1 - y0) * (px - x0) - (x1 - x0) * (py - y0)) / L
            for px, py in pts)
    r = d / L
    return r - 1.4 * r * r


def _b1_and_check(strength):
    """The ``b1`` Janbu corrected published, after checking that it is the
    one its factor was computed with: F_corr = (1 + b1·g)·F_simp."""
    simp, _sl = _solve(strength, "janbu_simplified")
    corr, sl = _solve(strength, "janbu_corrected")
    b1 = (corr.details or {}).get("janbu_b1")
    g = _shape(sl)
    assert math.isclose(corr.fos / simp.fos, 1.0 + b1 * g, rel_tol=1e-12), (
        corr.fos, simp.fos, b1, g)
    return b1, corr.fos


def _asf(*rows):
    from ogr_core.materials.builtin_models import AnisotropicStrengthFunction
    return AnisotropicStrengthFunction(rows=list(rows))


class _Switch:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        from ogr_slip2d.methods import janbu
        self.old = janbu.SOIL_TYPE_PER_BASE
        janbu.SOIL_TYPE_PER_BASE = self.value

    def __exit__(self, *exc):
        from ogr_slip2d.methods import janbu
        janbu.SOIL_TYPE_PER_BASE = self.old


# ======================================================================
class TestTheRuleOfD80OnAMixedTable:
    """Two ranges, one "φ only" (c = 0) and one "c only" (φ = 0): the type
    of a base is the type of the range it falls in."""

    def test_every_base_in_the_c_only_range(self):
        # Bases from -17.9 to 61.7: all above -20, in the "c only" range.
        b1, _f = _b1_and_check(_asf((-20.0, 0.0, 35.0), (90.0, 40.0, 0.0)))
        assert b1 == 0.69, b1

    def test_every_base_in_the_phi_only_range(self):
        b1, _f = _b1_and_check(_asf((-20.0, 40.0, 0.0), (90.0, 0.0, 35.0)))
        assert b1 == 0.31, b1

    def test_bases_in_both_ranges(self):
        # Bases below 20 degrees are "φ only", above it "c only".
        b1, _f = _b1_and_check(_asf((20.0, 0.0, 35.0), (90.0, 40.0, 0.0)))
        assert b1 == 0.50, b1

    def test_a_range_with_c_and_phi(self):
        b1, _f = _b1_and_check(_asf((20.0, 5.0, 30.0), (90.0, 5.0, 30.0)))
        assert b1 == 0.50, b1


class TestTheAnchor:
    """A function whose every base falls in one range is, base for base,
    the Mohr-Coulomb material of that row: the same b1 and the same
    corrected factor, through the path D80 validated."""

    def test_the_c_only_range_is_undrained(self):
        from ogr_core.materials import MohrCoulomb
        b_asf, f_asf = _b1_and_check(_asf((-20.0, 0.0, 35.0),
                                          (90.0, 40.0, 0.0)))
        b_mc, f_mc = _b1_and_check(MohrCoulomb(cohesion=40.0,
                                               friction_angle=0.0))
        assert b_asf == b_mc == 0.69
        assert math.isclose(f_asf, f_mc, rel_tol=1e-12), (f_asf, f_mc)

    def test_the_phi_only_range_is_frictional(self):
        from ogr_core.materials import MohrCoulomb
        b_asf, f_asf = _b1_and_check(_asf((-20.0, 40.0, 0.0),
                                          (90.0, 0.0, 35.0)))
        b_mc, f_mc = _b1_and_check(MohrCoulomb(cohesion=0.0,
                                               friction_angle=35.0))
        assert b_asf == b_mc == 0.31
        assert math.isclose(f_asf, f_mc, rel_tol=1e-12), (f_asf, f_mc)


class TestTheOtherAnisotropicModels:

    def test_anisotropic_linear_across_the_transition(self):
        """Bedding "φ only", rock mass "c only": bases near the bedding are
        φ only, far from it c only, and between them c and φ."""
        from ogr_core.materials.builtin_models import AnisotropicLinear
        mixed = AnisotropicLinear(c1=0.0, phi1=35.0, c2=40.0, phi2=0.0,
                                  bedding_angle=0.0, A=5.0, B=20.0)
        assert _b1_and_check(mixed)[0] == 0.50
        # A bedding at -60 puts every base (from -17.9 to 61.7 degrees)
        # at least 42 degrees away from it, beyond B: rock mass only.
        rock = AnisotropicLinear(c1=0.0, phi1=35.0, c2=40.0, phi2=0.0,
                                 bedding_angle=-60.0, A=5.0, B=20.0)
        assert _b1_and_check(rock)[0] == 0.69

    def test_generalized_across_two_rules(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        ga = GeneralizedAnisotropic(rules=[
            {"angle_min": -90.0, "angle_max": 20.0,
             "model": {"model_id": "mohr_coulomb",
                       "params": {"cohesion": 0.0, "friction_angle": 35.0}}},
            {"angle_min": 20.0, "angle_max": 90.0,
             "model": {"model_id": "undrained",
                       "params": {"cohesion": 40.0}}}])
        assert _b1_and_check(ga)[0] == 0.50

    def test_generalized_shansep_reads_the_slice(self):
        """Changed on purpose, and written: SHANSEP inside a Generalized
        range reads the vertical stress of the slice, a constant for the
        normal stress, so the base is "c" (it read "φ" without a slice)."""
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_slip2d.methods.janbu import base_soil_type
        ga = GeneralizedAnisotropic(rules=[{
            "angle_min": -90.0, "angle_max": 90.0,
            "model": {"model_id": "shansep",
                      "params": {"A": 0.0, "S": 0.25, "m": 0.8,
                                 "OCR": 1.0, "su_min": 0.0}}}])
        p = _project(ga)
        _res, sl = _solve(ga, "janbu_simplified")
        kinds = {base_soil_type(p.materials[0], s) for s in sl.slices}
        assert kinds == {"c"}, kinds
        with _Switch(False):
            assert base_soil_type(p.materials[0], sl.slices[5]) == "phi"


class TestTheSwitch:

    def test_off_reads_the_material_without_a_slice(self):
        """Rule 7: the switch moves the number. Off, the mixed table is read
        without a slice: its weakest range at zero stress has no strength,
        a curve through the origin, "φ only"."""
        mixed = _asf((20.0, 0.0, 35.0), (90.0, 40.0, 0.0))
        on_b1, on_f = _b1_and_check(mixed)
        with _Switch(False):
            off_b1, off_f = _b1_and_check(mixed)
        assert (on_b1, off_b1) == (0.50, 0.31)
        assert abs(on_f - off_f) > 1e-6 * on_f

    def test_models_without_a_slice_do_not_move(self):
        from ogr_core.materials import MohrCoulomb, Undrained
        from ogr_core.materials.builtin_models import (BartonBandis,
                                                       ShearNormalFunction)
        for st in (MohrCoulomb(cohesion=8.0, friction_angle=27.0),
                   Undrained(cohesion=35.0), BartonBandis(),
                   ShearNormalFunction()):
            on = _solve(st, "janbu_corrected")[0].fos
            with _Switch(False):
                off = _solve(st, "janbu_corrected")[0].fos
            assert math.isclose(on, off, rel_tol=1e-15), (st, on, off)


class TestTheWeakestReading:
    """Without a slice: the weakest orientation, by hand."""

    def test_the_function_takes_its_weakest_row(self):
        m = _asf((-30.0, 10.0, 35.0), (0.0, 1.0, 20.0), (90.0, 5.0, 10.0))
        for s in (0.0, 10.0, 100.0, 300.0):
            want = min(c + s * math.tan(math.radians(p))
                       for c, p in ((10.0, 35.0), (1.0, 20.0), (5.0, 10.0)))
            assert math.isclose(m.shear_strength(s), want, rel_tol=1e-12), s
        # At 100 kPa the weakest is the row of 5 kPa, not the row of least
        # cohesion (1 kPa), which the reading took until v0.1.229.
        least_c = 1.0 + 100.0 * math.tan(math.radians(20.0))
        assert m.shear_strength(100.0) < least_c - 1.0

    def test_anisotropic_linear_at_zero_or_ninety(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        # A bedding stronger than the rock mass at low stress.
        m = AnisotropicLinear(c1=30.0, phi1=10.0, c2=5.0, phi2=20.0,
                              bedding_angle=15.0, A=10.0, B=30.0)
        for s in (0.0, 100.0, 400.0):
            bed = 30.0 + s * math.tan(math.radians(10.0))
            rock = 5.0 + s * math.tan(math.radians(20.0))
            assert math.isclose(m.shear_strength(s), min(bed, rock),
                                rel_tol=1e-12), s

    def test_anisotropic_linear_as_before_when_the_bedding_is_weaker(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        m = AnisotropicLinear()
        s = 80.0
        want = 5.0 + s * math.tan(math.radians(15.0))
        assert math.isclose(m.shear_strength(s), want, rel_tol=1e-15)

    def test_generalized_takes_its_weakest_rule(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        ga = GeneralizedAnisotropic(rules=[
            {"angle_min": -90.0, "angle_max": 0.0,
             "model": {"model_id": "mohr_coulomb",
                       "params": {"cohesion": 20.0, "friction_angle": 10.0}}},
            {"angle_min": 0.0, "angle_max": 90.0,
             "model": {"model_id": "mohr_coulomb",
                       "params": {"cohesion": 2.0, "friction_angle": 30.0}}}])
        for s in (0.0, 50.0, 200.0):
            want = min(20.0 + s * math.tan(math.radians(10.0)),
                       2.0 + s * math.tan(math.radians(30.0)))
            assert math.isclose(ga.shear_strength(s), want, rel_tol=1e-12), s


class TestTheContextIsTheSolversOwn:

    def test_from_slice_reads_the_slice(self):
        from ogr_core.materials.strength_model import SliceContext
        _res, sl = _solve(_asf((90.0, 5.0, 30.0)), "janbu_simplified")
        s = sl.slices[7]
        ctx = SliceContext.from_slice(s, 50.0)
        assert ctx.base_angle_rad == s.base_angle
        want = max((s.weight + getattr(s, "water_weight", 0.0)) / s.width
                   - s.pore_pressure, 0.0)
        assert math.isclose(ctx.sigma_v_eff, want, rel_tol=1e-15)

    def test_a_stand_in_and_a_probe(self):
        """A stand-in with no weight falls back on the stress it is given;
        a probe replaces the vertical stress (D207)."""
        from ogr_core.materials.strength_model import SliceContext

        class _Bare:
            base_angle = 0.3

        ctx = SliceContext.from_slice(_Bare(), 42.0)
        assert ctx.sigma_v_eff == 42.0 and ctx.base_angle_rad == 0.3
        assert ctx.layer_top_y is None and ctx.bedding_angle_deg is None
        ctx = SliceContext.from_slice(_Bare(), 42.0, sigma_v_probe=7.0)
        assert ctx.sigma_v_eff == 7.0
