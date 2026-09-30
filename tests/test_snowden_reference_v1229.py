# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.229 — Snowden Modified Anisotropic Linear is the model the reference
documents, and the C/Phi Function exists (defect D215 of the verification
bank).

THE DEFECT. OGR had another model under the name: c1, φ1, c2, φ2 and a single
B, with a symmetric COSINE transition of c and of the angle φ. The reference
documentation defines it on Anisotropic Linear (Mercer 2012, 2013) with two
additions: a NON-SYMMETRIC anisotropy function of four parameters, A1, B1 on
one side of the bedding and A2, B2 on the other, and strength FUNCTIONS of
σ'ₙ for the bedding and the rock mass ("Shear-Normal function" or
"Cohesion-Friction function"), the strength of an intermediate orientation
being "a weighted average determined by the linear transition of the
anisotropy function". The C/Phi Function ("Cohesion-Friction") did not exist.

THE DECISIONS (the owner's, 2026-09-30, and the plan's):

* α is the angle from the bedding (the 1-direction) to the slice base,
  counter-clockwise, folded into (-90, 90]; (A1, B1) hold for α < 0 and
  (A2, B2) for α ≥ 0 -- the documentation's figures, where alpha is drawn
  from direction 1 to the plane and A1, B1 on the negative side. The base
  angle is geometric (``atan2(dy, dx)``, dx > 0), whatever the failure
  direction: the mirror case below pins that end to end.
* τ = (1 − t)·τ_bedding + t·τ_rock mass, t = clip((|α| − A)/(B − A)).
* Without a slice, the weakest orientation (D219's decision).
* C/Phi: c and φ (the ANGLE) linear in σ'ₙ between rows, "interpolated on the
  cohesion and friction angle level"; the end rows hold outside the table
  (a decision: the documentation does not say).
* A file with the old parameters opens, keeps them and round-trips them,
  shows the nearest form of the new model, and is refused until reviewed.

THE REFERENCES (rule 1): the functions written by hand from the
documentation's text and figure, on both sides and in the three zones; an
identity -- one-row C/Phi functions with A1 = A2, B1 = B2 are Anisotropic
Linear, whose D216 equations interpolate c and tan φ, the same line in t --
in the nine methods; and a mirror identity, the slope reflected with the
bedding and the two sides swapped.

DISCRIMINATION, measured on the v0.1.228 tree: see the changelog of
v0.1.229.
"""
from __future__ import annotations

import copy
import math

#: A dry circle whose bases run from about -18 to +62 degrees.
CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30
SIGMAS = (0.0, 7.5, 60.0, 180.0, 250.0, 420.0)


def _cphi(*rows) -> dict:
    return {"model_id": "c_phi_function", "params": {},
            "rows": [list(r) for r in rows]}


def _snf(*points) -> dict:
    return {"model_id": "shear_normal_function", "params": {},
            "points": [list(p) for p in points]}


#: Non-linear functions, crossing each other: the bedding is the stronger at
#: low stress and the weaker at high stress.
BEDDING = _snf((0.0, 12.0), (100.0, 40.0), (300.0, 80.0))
ROCK_MASS = _cphi((0.0, 4.0, 42.0), (200.0, 25.0, 33.0))
ASYM = dict(bedding_angle=10.0, A1=5.0, B1=25.0, A2=15.0, B2=40.0)


def _snowden(**kw):
    from ogr_core.materials.builtin_models import (
        SnowdenModifiedAnisotropicLinear)
    kw.setdefault("bedding", copy.deepcopy(BEDDING))
    kw.setdefault("rock_mass", copy.deepcopy(ROCK_MASS))
    return SnowdenModifiedAnisotropicLinear(**kw)


def _ctx(base_deg, bedding=None):
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(base_angle_rad=math.radians(base_deg),
                        bedding_angle_deg=bedding)


def _bedding_by_hand(s):
    """The shear-normal function of BEDDING, interpolated by hand."""
    pts = [(0.0, 12.0), (100.0, 40.0), (300.0, 80.0)]
    if s <= pts[0][0]:
        return pts[0][1]
    if s >= pts[-1][0]:
        return pts[-1][1]
    for (s0, t0), (s1, t1) in zip(pts, pts[1:]):
        if s0 <= s <= s1:
            return t0 + (s - s0) / (s1 - s0) * (t1 - t0)
    raise AssertionError(s)


def _rock_by_hand(s):
    """The C/Phi function of ROCK_MASS by hand: c and φ linear in σ'ₙ."""
    (s0, c0, p0), (s1, c1, p1) = (0.0, 4.0, 42.0), (200.0, 25.0, 33.0)
    if s <= s0:
        c, p = c0, p0
    elif s >= s1:
        c, p = c1, p1
    else:
        f = (s - s0) / (s1 - s0)
        c, p = c0 + f * (c1 - c0), p0 + f * (p1 - p0)
    return c + max(s, 0.0) * math.tan(math.radians(p))


def _t_by_hand(alpha, a1, b1, a2, b2):
    a, b = (a1, b1) if alpha < 0 else (a2, b2)
    return min(max((abs(alpha) - a) / (b - a), 0.0), 1.0)


def _slope(strength, mirror=False):
    """The dry slope of ``test_anisotropic_function_ranges_v1218``; with
    ``mirror`` its reflection in x = 30 (x' = 60 − x)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    pts = [(0, -10), (60, -10), (60, h), (crest, h), (toe, 0), (0, 0)]
    if mirror:
        pts = [(60.0 - x, y) for x, y in pts]
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p = Project("snowden")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="bedded", unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _fos(strength, method_id="bishop_simplified", mirror=False):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _slope(strength, mirror)
    xc, yc, r = CIRCLE
    circle = SlipCircle(60.0 - xc if mirror else xc, yc, r)
    sl = slice_surface(p, circle, num_slices=N_SLICES)
    res = method_registry()[method_id]().compute_fos(p, circle, sl)
    assert res.fos is not None, (method_id, res.reason)
    return res.fos


def _raises(fn, *exc_types):
    try:
        fn()
    except exc_types as exc:
        return exc
    raise AssertionError(f"{fn} did not raise {exc_types}")


# ======================================================================
class TestTheFunctionByHand:
    """The documentation's text and figure, written out."""

    def test_both_sides_and_the_three_zones(self):
        from ogr_core.materials.builtin_models import fold_plane_angle_deg
        m = _snowden(**ASYM)
        bad = []
        for base in range(-85, 90, 5):
            alpha = fold_plane_angle_deg(base - 10.0)
            t = _t_by_hand(alpha, 5.0, 25.0, 15.0, 40.0)
            for s in SIGMAS:
                want = ((1.0 - t) * _bedding_by_hand(s)
                        + t * _rock_by_hand(s))
                got = m.shear_strength_ctx(s, _ctx(base))
                if not math.isclose(got, want, rel_tol=1e-12):
                    bad.append((base, s, got, want))
        assert not bad, bad[:5]

    def test_each_zone_on_each_side(self):
        """Bedding only, transition and rock mass only, at angles picked in
        each zone of each side (bedding at 10 degrees)."""
        m = _snowden(**ASYM)
        s = 180.0
        bed, rock = _bedding_by_hand(s), _rock_by_hand(s)
        cases = {                 # base angle: expected t
            10.0 - 3.0: 0.0,      # alpha = -3,  |alpha| <= A1 = 5
            10.0 - 15.0: 0.5,     # alpha = -15, (15 - 5) / (25 - 5)
            10.0 - 30.0: 1.0,     # alpha = -30, beyond B1 = 25
            10.0 + 10.0: 0.0,     # alpha = +10, |alpha| <= A2 = 15
            10.0 + 27.5: 0.5,     # alpha = +27.5, (27.5 - 15) / (40 - 15)
            10.0 + 50.0: 1.0,     # alpha = +50, beyond B2 = 40
        }
        for base, t in cases.items():
            want = (1.0 - t) * bed + t * rock
            got = m.shear_strength_ctx(s, _ctx(base))
            assert math.isclose(got, want, rel_tol=1e-12), (base, got, want)

    def test_the_sides_are_not_the_same(self):
        """A1, B1 hold clockwise from the bedding (alpha < 0), A2, B2
        counter-clockwise: 15 degrees on either side reads a different
        zone -- the transition on one side, the bedding on the other."""
        m = _snowden(**ASYM)
        s = 180.0
        cw = m.shear_strength_ctx(s, _ctx(10.0 - 15.0))
        ccw = m.shear_strength_ctx(s, _ctx(10.0 + 15.0))
        assert math.isclose(ccw, _bedding_by_hand(s), rel_tol=1e-12)
        assert abs(cw - ccw) > 1e-3 * ccw, (cw, ccw)

    def test_a_step_when_a_equals_b(self):
        m = _snowden(bedding_angle=0.0, A1=20.0, B1=20.0, A2=20.0, B2=20.0)
        s = 60.0
        assert math.isclose(m.shear_strength_ctx(s, _ctx(20.0)),
                            _bedding_by_hand(s), rel_tol=1e-12)
        assert math.isclose(m.shear_strength_ctx(s, _ctx(20.001)),
                            _rock_by_hand(s), rel_tol=1e-12)

    def test_the_local_bedding_wins(self):
        """D208 still holds: a bedding in the context replaces the global
        angle."""
        m = _snowden(**ASYM)
        a = m.shear_strength_ctx(180.0, _ctx(40.0, bedding=40.0))
        assert math.isclose(a, _bedding_by_hand(180.0), rel_tol=1e-12)

    def test_an_axis_pointing_left_is_the_same_plane(self):
        m = _snowden(**ASYM)
        for base in (-60.0, -5.0, 20.0, 70.0):
            a = m.shear_strength_ctx(90.0, _ctx(base))
            b = m.shear_strength_ctx(90.0, _ctx(base + 180.0))
            assert math.isclose(a, b, rel_tol=1e-12), base


class TestWithoutASlice:

    def test_the_weakest_orientation(self):
        """The strength is linear in t and t spans [0, 1] on each side, so
        the weakest orientation is the weaker of the two functions."""
        m = _snowden(**ASYM)
        for s in SIGMAS:
            want = min(_bedding_by_hand(s), _rock_by_hand(s))
            assert math.isclose(m.shear_strength(s), want, rel_tol=1e-12), s
        # They cross, so the answer is not one function at every stress.
        assert _bedding_by_hand(0.0) > _rock_by_hand(0.0)
        assert _bedding_by_hand(420.0) < _rock_by_hand(420.0)


# ======================================================================
class TestIdentities:

    def _al_pair(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        al = AnisotropicLinear(c1=5.0, phi1=15.0, c2=20.0, phi2=30.0,
                               bedding_angle=12.0, A=8.0, B=35.0)
        sn = _snowden(bedding_angle=12.0, A1=8.0, B1=35.0, A2=8.0, B2=35.0,
                      bedding=_cphi((0.0, 5.0, 15.0)),
                      rock_mass=_cphi((0.0, 20.0, 30.0)))
        return al, sn

    def test_one_row_functions_are_anisotropic_linear(self):
        al, sn = self._al_pair()
        for base in range(-89, 90, 4):
            for s in SIGMAS:
                a = al.shear_strength_ctx(s, _ctx(base))
                b = sn.shear_strength_ctx(s, _ctx(base))
                assert math.isclose(a, b, rel_tol=1e-12), (base, s, a, b)

    def test_and_so_in_the_nine_methods(self):
        from ogr_slip2d.methods import method_registry
        al, sn = self._al_pair()
        mids = sorted(method_registry())
        assert len(mids) == 9
        for mid in mids:
            a, b = _fos(al, mid), _fos(sn, mid)
            assert math.isclose(a, b, rel_tol=1e-12), (mid, a, b)

    def test_the_mirror_of_the_model(self):
        """alpha and -alpha with the two sides swapped are one strength."""
        m = _snowden(**ASYM)
        w = _snowden(bedding_angle=-10.0, A1=15.0, B1=40.0, A2=5.0, B2=25.0)
        for base in range(-85, 90, 5):
            for s in SIGMAS:
                a = m.shear_strength_ctx(s, _ctx(base))
                b = w.shear_strength_ctx(s, _ctx(-base))
                assert math.isclose(a, b, rel_tol=1e-15), (base, s)

    def test_the_mirror_of_the_slope(self):
        """The slope reflected, the bedding reflected and the two sides
        swapped: the same factor of safety. Only true if the base angle is
        geometric whatever way the slope fails."""
        m = _snowden(bedding_angle=20.0, A1=5.0, B1=25.0, A2=15.0, B2=45.0)
        w = _snowden(bedding_angle=-20.0, A1=15.0, B1=45.0, A2=5.0, B2=25.0)
        for mid in ("bishop_simplified", "spencer"):
            a, b = _fos(m, mid), _fos(w, mid, mirror=True)
            assert math.isclose(a, b, rel_tol=1e-9), (mid, a, b)
        # ...and the swap matters: without it the reflection is another
        # material.
        c = _fos(_snowden(bedding_angle=-20.0, A1=5.0, B1=25.0, A2=15.0,
                          B2=45.0), mirror=True)
        a = _fos(m)
        assert abs(a - c) > 1e-4 * a, (a, c)


class TestEverySettingMovesTheNumber:
    """Rule 7."""

    def test_a1_differs_from_a2(self):
        a = _fos(_snowden(bedding_angle=0.0, A1=0.0, B1=20.0, A2=0.0,
                          B2=20.0))
        b = _fos(_snowden(bedding_angle=0.0, A1=10.0, B1=40.0, A2=0.0,
                          B2=20.0))
        c = _fos(_snowden(bedding_angle=0.0, A1=0.0, B1=20.0, A2=10.0,
                          B2=40.0))
        assert abs(a - b) > 1e-4 * a and abs(a - c) > 1e-4 * a, (a, b, c)

    def test_each_function(self):
        base = _fos(_snowden(**ASYM))
        weak_bed = _fos(_snowden(bedding=_snf((0.0, 6.0), (300.0, 50.0)),
                                 **ASYM))
        weak_rock = _fos(_snowden(rock_mass=_cphi((0.0, 2.0, 35.0)), **ASYM))
        assert weak_bed < base * (1 - 1e-4), (weak_bed, base)
        assert weak_rock < base * (1 - 1e-4), (weak_rock, base)


# ======================================================================
class TestTheRule:

    def _why(self, strength):
        from ogr_core.project.rules import strength_model_refusal
        return strength_model_refusal(strength, "bedded")

    def test_the_defaults_and_the_example_are_valid(self):
        from ogr_core.materials.builtin_models import (
            SnowdenModifiedAnisotropicLinear)
        assert self._why(SnowdenModifiedAnisotropicLinear()) is None
        assert self._why(_snowden(**ASYM)) is None

    def test_a_and_b(self):
        for kw in (dict(A1=30.0, B1=20.0), dict(A2=-1.0), dict(B2=95.0),
                   dict(B1=float("nan"))):
            why = self._why(_snowden(**kw))
            assert why is not None and why.code == "snowden_ab", (kw, why)

    def test_a_function_of_another_kind(self):
        why = self._why(_snowden(bedding={
            "model_id": "mohr_coulomb",
            "params": {"cohesion": 5.0, "friction_angle": 30.0}}))
        assert why.code == "snowden_bedding"
        assert why.cause.code == "snowden_function_type"

    def test_a_table_the_function_may_not_hold(self):
        why = self._why(_snowden(rock_mass=_cphi()))
        assert why.code == "snowden_rock_mass"
        assert why.cause.code == "c_phi_rows_empty"
        why = self._why(_snowden(bedding=_snf((10.0, 5.0), (10.0, 6.0))))
        assert why.code == "snowden_bedding"
        assert why.cause.code == "function_points_order"

    def test_the_analysis_refuses_it_by_name(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        problems = check_analysis_settings(_slope(_snowden(B1=95.0)))
        assert any("'bedded'" in s and "B1" in s for s in problems), problems

    def test_the_api_refuses_it(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        _raises(lambda: strength_from_spec({
            "model": "snowden_anisotropic_linear",
            "params": {"A1": 30.0, "B1": 20.0}}), InvalidArgument)
        _raises(lambda: strength_from_spec({
            "model": "snowden_anisotropic_linear",
            "params": {"c1": 5.0}}), InvalidArgument)
        ok = strength_from_spec({
            "model": "snowden_anisotropic_linear", "params": ASYM,
            "bedding": BEDDING, "rock_mass": ROCK_MASS})
        assert ok.bedding == BEDDING and ok.rock_mass == ROCK_MASS


# ======================================================================
OLD = {"model_id": "snowden_anisotropic_linear",
       "params": {"c1": 5.0, "phi1": 15.0, "c2": 20.0, "phi2": 30.0,
                  "bedding_angle": 10.0, "B": 30.0}}


class TestTheOldFile:

    def _material(self):
        from ogr_core.materials import Material
        return Material.from_dict({"name": "old", "unit_weight": 20.0,
                                   "strength": copy.deepcopy(OLD)})

    def test_it_opens_and_round_trips_untouched(self):
        m = self._material()
        assert m.strength.to_dict() == OLD
        assert m.to_dict()["strength"] == OLD

    def test_it_shows_the_nearest_form(self):
        st = self._material().strength
        assert st.params == {"bedding_angle": 10.0, "A1": 0.0, "B1": 30.0,
                             "A2": 0.0, "B2": 30.0}
        assert st.bedding["rows"] == [[0.0, 5.0, 15.0]]
        assert st.rock_mass["rows"] == [[0.0, 20.0, 30.0]]

    def test_it_is_refused_and_never_computed(self):
        from ogr_core.materials.builtin_models import LegacySnowden
        from ogr_slip2d.analysis_runner import check_analysis_settings
        m = self._material()
        p = _slope(m.strength)
        assert any("0.1.229" in s and "'bedded'" in s
                   for s in check_analysis_settings(p))
        _raises(lambda: m.strength.shear_strength_ctx(50.0, _ctx(5.0)),
                LegacySnowden)
        _raises(lambda: m.strength.shear_strength(50.0), LegacySnowden)

    def test_a_function_that_cannot_be_built_does_not_stop_the_file(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import IncompleteSnowden
        from ogr_core.project.rules import strength_model_refusal
        data = {"model_id": "snowden_anisotropic_linear",
                "params": dict(ASYM), "bedding": {"model_id": "gone"},
                "rock_mass": copy.deepcopy(ROCK_MASS)}
        m = Material.from_dict({"name": "x", "strength": data})
        assert strength_model_refusal(m.strength, "x").code == \
            "snowden_bedding"
        _raises(lambda: m.strength.shear_strength_ctx(50.0, _ctx(5.0)),
                IncompleteSnowden)

    def test_a_random_variable_on_c1_is_unwritable(self):
        from ogr_core.statistics.random_variables import (
            RandomVariable, VariableKind, unwritable_variables)
        p = _slope(_snowden(**ASYM))
        rv = RandomVariable(kind=VariableKind.MATERIAL_STRENGTH,
                            target_id=p.materials[0].id, param="c1")
        assert unwritable_variables(p, [rv], {rv.key: 3.0}) == [rv.key]


# ======================================================================
class TestTheCPhiFunction:

    ROWS = ((0.0, 5.0, 35.0), (100.0, 10.0, 30.0), (300.0, 20.0, 25.0))

    def _m(self, rows=None):
        from ogr_core.materials.builtin_models import CPhiFunction
        return CPhiFunction(rows=rows if rows is not None else self.ROWS)

    def test_by_hand_between_rows_and_outside(self):
        m = self._m()
        cases = {-10.0: (5.0, 35.0), 50.0: (7.5, 32.5),
                 200.0: (15.0, 27.5), 400.0: (20.0, 25.0)}
        for s, (c, phi) in cases.items():
            want = c + max(s, 0.0) * math.tan(math.radians(phi))
            assert math.isclose(m.shear_strength(s), want, rel_tol=1e-12), s

    def test_it_interpolates_the_angle(self):
        """"The interpolation is done on the cohesion and friction angle
        level": at 200 kPa φ is 27.5 degrees, not the angle whose tangent
        is the mean of tan 30 and tan 25."""
        m = self._m()
        by_tangent = 15.0 + 200.0 * 0.5 * (math.tan(math.radians(30.0))
                                           + math.tan(math.radians(25.0)))
        assert abs(m.shear_strength(200.0) - by_tangent) > 1e-3

    def test_one_row_is_mohr_coulomb(self):
        from ogr_core.materials import MohrCoulomb
        m = self._m(((0.0, 7.0, 28.0),))
        mc = MohrCoulomb(cohesion=7.0, friction_angle=28.0)
        for s in SIGMAS:
            assert math.isclose(m.shear_strength(s), mc.shear_strength(s),
                                rel_tol=1e-15), s

    def test_the_tangent_is_the_derivative(self):
        m = self._m()
        for s in (20.0, 50.0, 150.0, 290.0, 350.0):
            h = 1e-4
            fd = (m.shear_strength(s + h) - m.shear_strength(s - h)) / (2 * h)
            assert math.isclose(m.tangent_slope(s), fd, rel_tol=1e-6), s

    def test_design_factors_divide_c_and_tan_phi(self):
        from ogr_core.materials.strength_model import MaterialFactors
        m = self._m()
        before = m.to_dict()
        done = m.design_factored(MaterialFactors(cohesion=1.3, tan_phi=1.2,
                                                 undrained=1.0, shear=1.0))
        f = done.model
        for s in SIGMAS + (130.0, 200.0):
            c, phi = m.c_phi_at(s)
            want = c / 1.3 + max(s, 0.0) * math.tan(math.radians(phi)) / 1.2
            assert math.isclose(f.shear_strength(s), want, rel_tol=1e-12), s
        assert m.to_dict() == before
        from ogr_core.materials.strength_model import StrengthModel
        again = StrengthModel.from_dict(f.to_dict())
        assert math.isclose(again.shear_strength(130.0),
                            f.shear_strength(130.0), rel_tol=1e-15)

    def test_the_rule(self):
        from ogr_core.project.rules import c_phi_rows_refusal
        assert c_phi_rows_refusal(self.ROWS) is None
        for rows, code in (([], "c_phi_rows_empty"),
                           ([(0.0, 5.0)], "c_phi_rows_not_rows"),
                           ([(0.0, -1.0, 30.0)], "c_phi_rows_strength"),
                           ([(0.0, 1.0, 90.0)], "c_phi_rows_strength"),
                           ([(0.0, 1.0, 30.0), (0.0, 2.0, 30.0)],
                            "c_phi_rows_order")):
            assert c_phi_rows_refusal(rows).code == code, rows


# ======================================================================
class TestTheDialog:

    def _dialog(self, *strengths, units=None):
        from PySide6.QtWidgets import QApplication
        from ogr_core.materials import Material
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        mats = [Material(name=f"m{i}", unit_weight=20.0, strength=s)
                for i, s in enumerate(strengths)]
        dlg = MaterialPropertiesDialog(mats, units_obj=units)
        dlg.list.setCurrentRow(0)
        dlg.accepted_calls = []
        dlg.accept = lambda: dlg.accepted_calls.append(True)
        return dlg

    def test_the_functions_are_shown_and_kept(self):
        m = _snowden(**ASYM)
        before = m.to_dict()
        dlg = self._dialog(m)
        labels = {k: v.text()
                  for k, v in dlg.param_panel._function_labels.items()}
        assert labels == {"bedding": "Shear/Normal Function, 3 row(s)",
                          "rock_mass": "C/Phi Function, 2 row(s)"}, labels
        dlg._ok()
        assert dlg.accepted_calls == [True]
        assert dlg.result_materials()[0].strength.to_dict() == before

    def test_the_function_dialog_works_without_exec(self):
        from PySide6.QtWidgets import QTableWidgetItem
        from ogr_gui.dialogs.material_properties_dialog import (
            StrengthFunctionDialog)
        dlg = self._dialog(_snowden(**ASYM))
        f = StrengthFunctionDialog(dlg.param_panel.function("rock_mass"))
        assert f.cbo_kind.currentData() == "c_phi_function"
        f.panel._table.setItem(1, 1, QTableWidgetItem("30"))
        assert f._accept_if_valid()
        dlg.param_panel.set_function("rock_mass", f.result_function())
        dlg._ok()
        rows = dlg.result_materials()[0].strength.rock_mass["rows"]
        assert [list(r) for r in rows] == [[0.0, 4.0, 42.0],
                                           [200.0, 30.0, 33.0]], rows

    def test_the_function_dialog_refuses_what_it_cannot_store(self):
        from PySide6.QtWidgets import QTableWidgetItem
        from ogr_gui.dialogs.material_properties_dialog import (
            StrengthFunctionDialog)
        self._dialog()                  # the application
        f = StrengthFunctionDialog(copy.deepcopy(BEDDING))
        f.panel._table.setItem(1, 0, QTableWidgetItem("0"))
        assert not f._accept_if_valid() and f.result_function() is None
        assert "increase" in f.lbl_problem.text()
        f.panel._table.setItem(1, 0, QTableWidgetItem("x"))
        assert not f._accept_if_valid()
        assert "Row 2" in f.lbl_problem.text()

    def test_the_other_kind_shows_its_own_table(self):
        from ogr_gui.dialogs.material_properties_dialog import (
            StrengthFunctionDialog)
        self._dialog()
        f = StrengthFunctionDialog(copy.deepcopy(BEDDING))
        f.cbo_kind.setCurrentIndex(f.cbo_kind.findData("c_phi_function"))
        assert len(f.panel.table_headers()) == 3
        assert f._accept_if_valid()
        assert f.result_function()["model_id"] == "c_phi_function"

    def test_an_old_material_is_kept_until_it_is_edited(self):
        from ogr_core.materials.strength_model import StrengthModel
        old = StrengthModel.from_dict(copy.deepcopy(OLD))
        dlg = self._dialog(old)
        assert "0.1.229" in dlg.lbl_strength_problem.text()
        dlg._ok()
        assert dlg.result_materials()[0].strength.to_dict() == OLD
        dlg = self._dialog(StrengthModel.from_dict(copy.deepcopy(OLD)))
        dlg.param_panel._editors["A2"].setValue(12.0)
        dlg._ok()
        st = dlg.result_materials()[0].strength
        assert st.legacy_params is None and st.params["A2"] == 12.0

    def test_the_c_phi_table_speaks_the_projects_units(self):
        from ogr_core.materials.builtin_models import CPhiFunction
        from ogr_core.project.units import Units
        rows = [(0.0, 5.123456789, 35.0), (97.3, 10.0, 30.5)]
        dlg = self._dialog(CPhiFunction(rows=rows),
                           units=Units(system_id="imperial_psf"))
        headers = dlg.param_panel.table_headers()
        assert "psf" in headers[0] and "psf" in headers[1], headers
        assert "psf" not in headers[2], headers
        dlg._ok()
        assert dlg.result_materials()[0].strength.rows == rows

    def test_the_texts_have_their_spanish(self):
        """Translated through variables, which the coverage test cannot
        see."""
        from ogr_gui.dialogs.material_properties_dialog import (
            StrengthFunctionDialog, _StrengthParamPanel)
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        texts = [t for _w, b, title in _StrengthParamPanel._FUNCTION_BUTTONS
                 for t in (b, title)]
        texts += [text for _m, text in StrengthFunctionDialog.KINDS]
        missing = [t for t in texts if t not in es]
        assert not missing, missing


class TestTheDesignFactors:

    def test_the_strength_is_divided_by_gamma(self):
        from ogr_core.materials.strength_model import MaterialFactors
        g = 1.37
        m = _snowden(**ASYM)
        f = m.design_factored(MaterialFactors(cohesion=g, tan_phi=g,
                                              undrained=g, shear=g)).model
        for base in (-40.0, -12.0, 0.0, 22.0, 60.0):
            for s in SIGMAS:
                want = m.shear_strength_ctx(s, _ctx(base)) / g
                got = f.shear_strength_ctx(s, _ctx(base))
                assert math.isclose(got, want, rel_tol=1e-12), (base, s)
        assert m.to_dict()["bedding"] == BEDDING
