# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Corps of Engineers #1 and #2 — the Modified Swedish Method.

**The invariant**: the force-equilibrium recursion these two methods (and
Lowe-Karafiath) share must reproduce, slice by slice, the worked example
that USACE publishes in the manual the methods come from — and each
method's θ rule must be exactly the geometry it claims, not something
that merely looks like it.

Why validate it this way. A method of this family is two independent
pieces: a recursion, and a rule for where θ comes from. Each is checked
against its own external reference:

* the RECURSION against USACE (2003), EM 1110-2-1902, Appendix G, whose
  Figures G-7a, G-7b and G-9 print the complete slice table of a worked
  rapid-drawdown example — the inter-slice force column, the base normal
  column and the factor of safety, computed with a spreadsheet and
  published. The manual states its own numbers were rounded for the
  tables, so the tolerances below are stated as a fraction of each
  column's own scale rather than per value;
* the θ RULES against plain geometry, which is exact arithmetic;
* and the two joined together against the identity EM §C-4a names in
  words: horizontal inter-slice forces in a force-equilibrium procedure
  "is sometimes referred to as the 'Simplified Janbu' Method". Setting
  θ = 0 must therefore reproduce this program's own, separately
  validated, Janbu Simplified.

The manual's example is the same problem the Slide verification bank
numbers 95, whose panel names ``corp of eng#1`` as the slice method and
which the bank had attributed to Bishop — that mis-attribution is what
made these two methods worth writing (defect D31 of the bank audit).

NOT tested here, deliberately: whether the inter-slice resultant should
be the effective or the total force when there is water. The manual
treats both as legitimate (§C-4a) and this version makes it a project
setting; the test below only pins that the setting MOVES THE NUMBER
(rule 7), because which of the two is right is the open question of D20.
"""
from __future__ import annotations

import math


# ----------------------------------------------------------------------
# USACE (2003), EM 1110-2-1902, Appendix G — worked example, Figure G-7a
# (first stage) and G-7b (base normal). Units: kips, ksf, feet, degrees.
#
#   W       total slice weight
#   P       water load on the top of the slice (normal to it)
#   alpha   base inclination
#   beta    inclination of the top of the slice (18 deg = a 3:1 slope)
#   ell     base length
#   u       pore water pressure on the base
#   z_pub   published inter-slice force on the downslope side, at F = 3.49
#   n_pub   published total normal force on the base (Figure G-7b)
#
# c' = 0 and phi' = 30 deg on every slice. The slices run from the crest
# (slice 1) to the toe (slice 12), which is the order the manual marches.
EM_G7A = [
    #  W    P   alpha beta ell    u   z_pub n_pub
    (2, 0, 61, 18, 8, 0.00, 2, 2),
    (58, 0, 55, 18, 35, 0.89, 53, 63),
    (109, 0, 46, 18, 26, 2.36, 132, 111),
    (137, 0, 40, 18, 23, 3.40, 215, 134),
    (241, 10, 32, 18, 32, 4.39, 332, 240),
    (204, 23, 24, 18, 24, 5.24, 403, 214),
    (212, 38, 18, 18, 24, 5.78, 448, 238),
    (196, 47, 11, 18, 22, 6.15, 465, 236),
    (249, 83, 4, 18, 31, 6.36, 439, 336),
    (230, 119, -5, 18, 35, 6.34, 338, 379),
    (136, 124, -14, 18, 31, 6.02, 195, 315),
    (55, 159, -23, 18, 35, 5.36, 10, 302),
]
EM_G7A_F = 3.49

# Figure G-9 — second stage of the same example. All materials undrained
# (phi = 0), no external water load and no pore pressure, cohesion equal
# to the undrained strength Figure G-7b derived. The manual's answer, and
# the number the Slide verification manual quotes as "Reference factor of
# safety = 1.35 [Corps of Engineers]".
EM_G9 = [
    #  W   alpha ell    c    z_pub
    (2, 61, 8, 0.15, 1),
    (58, 55, 35, 0.53, 42),
    (109, 46, 26, 1.10, 106),
    (137, 40, 23, 1.45, 174),
    (241, 32, 32, 1.73, 262),
    (204, 24, 24, 2.10, 309),
    (212, 18, 24, 2.35, 331),
    (196, 11, 22, 2.46, 329),
    (249, 4, 31, 2.53, 288),
    (230, -5, 35, 2.52, 197),
    (136, -14, 31, 2.40, 93),
    (55, -23, 35, 1.78, 0),
]
EM_G9_F = 1.35

#: The side force inclination of the worked example. The manual prints
#: beta = 18 deg for every slice in the tables and its Figure G-5 gives
#: the embankment as 3:1, whose true angle is arctan(1/3) = 18.435 deg.
#: Both are exercised: the printed value against the printed columns, the
#: true one against the published factor of safety.
EM_THETA_PRINTED = 18.0
EM_THETA_TRUE = math.degrees(math.atan(1.0 / 3.0))


# ----------------------------------------------------------------------
def _material(c: float, phi: float):
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    return Material(name="EM", unit_weight=0.135,
                    strength=MohrCoulomb(cohesion=c, friction_angle=phi))


def _em_slices(rows, with_water: bool):
    """Real :class:`Slice` objects carrying the published quantities.

    The manual's alpha is positive when the base is inclined in the same
    direction as the slope; this program's ``base_angle`` uses the same
    convention, so the two agree without a conversion. The water load P
    is normal to the top of the slice, and is split the way this program
    splits it everywhere else: a vertical part the base has to carry and
    a horizontal part that joins the driving side. The two decompositions
    are algebraically the same force, which is what makes the comparison
    meaningful rather than a coincidence.
    """
    from ogr_slip2d.slicer import Slice
    out = []
    h_water = []
    for i, row in enumerate(rows):
        if with_water:
            W, P, ad, bd, ell, u, _z, _n = row
            c, phi = 0.0, 30.0
        else:
            W, ad, ell, c, _z = row
            P, bd, u, phi = 0.0, 18.0, 0.0, 0.0
        a = math.radians(ad)
        b = math.radians(bd)
        out.append(Slice(
            index=i, x_centre=0.0, width=ell * math.cos(a),
            base_x_left=0.0, base_x_right=ell * math.cos(a),
            base_y_left=0.0, base_y_right=ell * math.sin(a),
            base_angle=a, base_length=ell,
            top_y_left=0.0, top_y_right=0.0,
            weight=W, pore_pressure=u,
            water_weight=P * math.cos(b),
            water_force_h=P * math.sin(b),
            material=_material(c, phi),
        ))
        h_water.append(-P * math.sin(b))
    return out, h_water


def _em_context(rows, with_water: bool, theta_deg: float):
    """``(slices, ctx)`` in the frame the manual marches in.

    The manual walks from the crest to the toe. This program mirrors the
    geometry in x when the mass slides that way (``orient = -1`` inside
    ``_force_balance``), which maps alpha to -alpha and theta to -theta
    and flips the sign of a horizontal force expressed in the true +x
    direction. Doing that here by hand is what lets the published table
    drive the production recursion untouched.
    """
    slist, h_water = _em_slices(rows, with_water)
    alpha_n = [-s.base_angle for s in slist]
    theta = [-math.radians(theta_deg)] * len(slist)
    ctx = (alpha_n, theta, 0.0, 0.0, h_water, [0.0] * len(slist))
    return slist, ctx


def _engine():
    """A member of the family, used only for its recursion.

    Any of the three would do: the recursion is shared and theta is
    supplied explicitly here, which is the point — this class validates
    the engine, and the classes below validate each theta rule.
    """
    from ogr_slip2d.methods import CorpsOfEngineers1
    return CorpsOfEngineers1()


def _march(rows, with_water, theta_deg, F):
    slist, ctx = _em_context(rows, with_water, theta_deg)
    alpha_n, theta, kh, kv, hw, vs = ctx
    return _engine()._march(slist, theta, alpha_n, kh, kv, F,
                            h_water=hw, v_support=vs)


def _root(rows, with_water, theta_deg, lo=0.5, hi=6.0):
    """Bisect on the closure force, which is what the manual does by
    plotting the imbalance of the last slice against the trial factor."""
    def f(F):
        return _march(rows, with_water, theta_deg, F)[-1]

    a, b = lo, hi
    fa = f(a)
    for _ in range(200):
        m = 0.5 * (a + b)
        fm = f(m)
        if fa * fm <= 0:
            b = m
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


# ======================================================================
class TestTheRecursionAgainstTheManualsOwnTable:
    """EM 1110-2-1902 Appendix G, printed slice by slice."""

    def test_second_stage_interslice_forces(self):
        """Figure G-9. phi = 0 everywhere, so nothing here depends on the
        pore-pressure or friction terms: it is the cleanest published
        exercise of the recursion there is."""
        got = _march(EM_G9, False, EM_THETA_PRINTED, EM_G9_F)
        pub = [r[-1] for r in EM_G9]
        scale = max(abs(v) for v in pub)
        worst = max(abs(g - p) for g, p in zip(got, pub))
        assert worst <= 0.02 * scale, (
            f"worst {worst:.1f} kips on a column whose largest value is "
            f"{scale:.0f}: {[round(v, 1) for v in got]} vs {pub}")

    def test_second_stage_factor_of_safety(self):
        """The manual's answer for this example is F = 1.35, and it is
        the number the Slide verification manual quotes as the reference
        for its problem 95."""
        f_true = _root(EM_G9, False, EM_THETA_TRUE)
        f_printed = _root(EM_G9, False, EM_THETA_PRINTED)
        err_true = abs(f_true - EM_G9_F) / EM_G9_F
        err_printed = abs(f_printed - EM_G9_F) / EM_G9_F
        # The 3:1 embankment angle is the geometry the figure gives; the
        # tables print it rounded to 18 deg, and the difference between
        # the two is the honest width of this comparison.
        assert err_true < 0.01, (f_true, err_true)
        assert err_printed < 0.015, (f_printed, err_printed)

    def test_first_stage_interslice_forces(self):
        """Figure G-7a. Adds pore pressure on the base and a water load on
        the top of the slice, so it exercises the two terms G-9 cannot."""
        got = _march(EM_G7A, True, EM_THETA_PRINTED, EM_G7A_F)
        pub = [r[6] for r in EM_G7A]
        scale = max(abs(v) for v in pub)
        worst = max(abs(g - p) for g, p in zip(got, pub))
        assert worst <= 0.02 * scale, (
            f"worst {worst:.1f} kips on a column whose largest value is "
            f"{scale:.0f}: {[round(v, 1) for v in got]} vs {pub}")

    def test_first_stage_closes_where_the_manual_says(self):
        """The manual reports F = 3.49 for the stage and calls the 10 kips
        left on the last slice negligible against inter-slice forces of
        400 and more. The recursion has to leave a residual of that same
        order — not zero, which the rounded inputs cannot give, and not
        hundreds, which a wrong equation would.

        Measured: 11.6 kips against the published 10, both about 2.5 % of
        the 465 kips the column peaks at.
        """
        got = _march(EM_G7A, True, EM_THETA_PRINTED, EM_G7A_F)
        scale = max(abs(r[6]) for r in EM_G7A)
        published_residual = EM_G7A[-1][6]
        assert abs(got[-1]) <= 0.05 * scale, got[-1]
        assert abs(got[-1] - published_residual) <= 0.02 * scale, got[-1]

    def test_the_angle_is_identified_by_the_data_not_assumed(self):
        """theta is the one quantity of the example the tables do not
        print, so it is worth showing that it is pinned rather than
        chosen: with horizontal side forces the same slices close nowhere
        near the published column."""
        wrong = _march(EM_G9, False, 0.0, EM_G9_F)
        pub = [r[-1] for r in EM_G9]
        scale = max(abs(v) for v in pub)
        assert abs(wrong[-1]) > 0.2 * scale, (
            "theta = 0 must NOT reproduce the manual's closure")


# ======================================================================
class TestTheBaseNormalAgainstTheManualsOwnColumn:
    """EM Figure G-7b prints N for the twelve slices.

    Until v0.1.98 only Bishop and Ordinary filled ``base_normal``, and the
    two-stage rapid drawdown reads it to recover the stage-1 consolidation
    state: with an empty list it applied undrained strength to ZERO slices
    and silently degraded to a re-run of stage 1.
    """

    def test_base_normal_reproduces_the_published_column(self):
        slist, ctx = _em_context(EM_G7A, True, EM_THETA_PRINTED)
        normals, _shears, _strengths = _engine()._base_forces(
            slist, ctx, EM_G7A_F)
        pub = [r[7] for r in EM_G7A]
        scale = max(abs(v) for v in pub)
        worst = max(abs(g - p) for g, p in zip(normals, pub))
        assert worst <= 0.03 * scale, (
            f"worst {worst:.1f} kips on a column whose largest value is "
            f"{scale:.0f}: {[round(v, 1) for v in normals]} vs {pub}")

    def test_every_slice_gets_a_normal_a_shear_and_a_strength(self):
        slist, ctx = _em_context(EM_G7A, True, EM_THETA_PRINTED)
        normals, shears, strengths = _engine()._base_forces(
            slist, ctx, EM_G7A_F)
        assert len(normals) == len(shears) == len(strengths) == len(slist)

    def test_the_reported_shear_is_the_strength_divided_by_the_factor(self):
        """An identity, not a measurement: what force equilibrium
        mobilises is the available strength scaled down by F."""
        slist, ctx = _em_context(EM_G7A, True, EM_THETA_PRINTED)
        _normals, shears, strengths = _engine()._base_forces(
            slist, ctx, EM_G7A_F)
        for i, (s_mob, s_av) in enumerate(zip(shears, strengths)):
            if s_av > 1e-9:
                assert abs(s_mob - s_av / EM_G7A_F) < 1e-6 * max(1.0, s_av), i


# ======================================================================
class TestTheThetaRulesAreExactlyTheGeometry:
    """Each method claims a geometric rule. Arithmetic, so it is exact."""

    @staticmethod
    def _sliced():
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _ej1_project()
        c = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        return p, c, slice_surface(p, c, 25)

    def test_corps_1_is_the_chord_of_the_slip_surface(self):
        from ogr_slip2d.methods import CorpsOfEngineers1
        _p, _c, sl = self._sliced()
        th = CorpsOfEngineers1()._theta_angles(sl)
        a, b = sl.slices[0], sl.slices[-1]
        expected = math.atan2(b.base_y_right - a.base_y_left,
                              b.base_x_right - a.base_x_left)
        assert len(set(round(t, 12) for t in th)) == 1, "must be constant"
        assert abs(th[0] - expected) < 1e-12, (th[0], expected)

    def test_corps_2_is_the_ground_slope_over_each_slice(self):
        from ogr_slip2d.methods import CorpsOfEngineers2
        _p, _c, sl = self._sliced()
        th = CorpsOfEngineers2()._theta_angles(sl)
        for t, s in zip(th, sl.slices):
            expected = math.atan2(s.top_y_right - s.top_y_left,
                                  max(s.width, 1e-9))
            assert abs(t - expected) < 1e-12, (t, expected)

    def test_corps_2_is_horizontal_where_the_ground_is(self):
        """The consequence that distinguishes #2 from #1 and from
        Lowe-Karafiath: no interslice shear under flat ground. Ej_1 has a
        flat crest, so some slices must show it."""
        from ogr_slip2d.methods import CorpsOfEngineers2
        _p, _c, sl = self._sliced()
        th = CorpsOfEngineers2()._theta_angles(sl)
        flat = [t for t, s in zip(th, sl.slices)
                if abs(s.top_y_right - s.top_y_left) < 1e-12]
        assert flat, "Ej_1 has a flat crest; some slices sit under it"
        assert all(abs(t) < 1e-12 for t in flat)

    def test_the_three_rules_are_three_different_rules(self):
        from ogr_slip2d.methods import (CorpsOfEngineers1, CorpsOfEngineers2,
                                        LoweKarafiath)
        _p, _c, sl = self._sliced()
        t1 = CorpsOfEngineers1()._theta_angles(sl)
        t2 = CorpsOfEngineers2()._theta_angles(sl)
        tl = LoweKarafiath()._theta_angles(sl)
        assert t1 != t2 and t2 != tl and t1 != tl


# ======================================================================
class TestTheIdentityTheManualNames:
    """EM §C-4a: "The assumption of horizontal interslice forces in
    procedures that only satisfy force equilibrium ... is sometimes
    referred to as the 'Simplified Janbu' Method."

    So theta = 0 through this recursion must reproduce this program's own
    Janbu Simplified, which is validated separately against the reference
    factor of safety. Two independent implementations of the same
    equation, which is worth more than either alone.
    """

    def test_theta_zero_is_janbu_simplified(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.methods.modified_swedish import (
            PrescribedInclinationMethod)
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        class _HorizontalSideForces(PrescribedInclinationMethod):
            METHOD_ID = "_test_theta_zero"
            DISPLAY_NAME = "theta = 0"

            def _theta_angles(self, slices):
                return [0.0] * len(list(slices))

        p = _ej1_project()
        c = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl = slice_surface(p, c, 25)
        got = _HorizontalSideForces().compute_fos(p, c, sl)
        janbu = get_method("janbu_simplified")().compute_fos(p, c, sl)
        assert got.converged and janbu.converged
        err = abs(got.fos - janbu.fos) / janbu.fos
        assert err < 0.005, (got.fos, janbu.fos, err)


# ======================================================================
class TestRuleSeven:
    """Three methods that always agreed would be one method with three
    names, and a setting that never moves the number is worse than no
    setting."""

    @staticmethod
    def _fos(mid, wet=True, **kw):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        if wet:
            p = _wet_project()
            c = SlipCircle(centre_x=_WET_CIRCLE[0], centre_y=_WET_CIRCLE[1],
                           radius=_WET_CIRCLE[2])
        else:
            p = _ej1_project()
            c = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl = slice_surface(p, c, 25)
        return get_method(mid)(**kw).compute_fos(p, c, sl).fos

    def test_the_three_prescribed_methods_give_three_numbers(self):
        """Measured on the wet model: 0.830 / 0.896 / 0.972, which is 7 %
        and 8 % apart. That is where the three assumptions actually bite —
        a benched profile with a water table."""
        got = {mid: self._fos(mid) for mid in
               ("lowe_karafiath", "corps_engineers_1", "corps_engineers_2")}
        vals = sorted(got.values())
        assert all(math.isfinite(v) and v > 0 for v in vals), got
        for a, b in zip(vals, vals[1:]):
            assert abs(a - b) / b > 0.01, got

    def test_on_a_plain_uniform_slope_they_nearly_coincide(self):
        """And that is a fact about the geometry, not a defect, so it is
        pinned rather than left to be rediscovered as a bug.

        On a uniform slope cut by a circle, the chord of the slip surface
        and the mean of the Lowe-Karafiath angles are almost the same
        line, so #1 and Lowe-Karafiath land within a few parts in 10^5 of
        each other (measured on Ej_1: 0.83827 against 0.83830). #2 still
        separates, because a flat crest drives its angle to zero there.
        """
        got = {mid: self._fos(mid, wet=False) for mid in
               ("lowe_karafiath", "corps_engineers_1", "corps_engineers_2")}
        close = abs(got["lowe_karafiath"] - got["corps_engineers_1"])
        assert 0.0 < close / got["corps_engineers_1"] < 1e-3, got
        apart = abs(got["corps_engineers_2"] - got["corps_engineers_1"])
        assert apart / got["corps_engineers_1"] > 1e-3, got

    def test_the_interslice_force_setting_moves_the_number(self):
        """With water, and only with water: the setting decides whether
        the pressure on the vertical faces is inside the resultant whose
        inclination is prescribed. Dry, the two are the same analysis by
        construction, and that half is asserted too."""
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _wet_project()
        c = SlipCircle(centre_x=_WET_CIRCLE[0], centre_y=_WET_CIRCLE[1],
                       radius=_WET_CIRCLE[2])
        sl = slice_surface(p, c, 25)
        wet = {}
        for mode in ("effective", "total"):
            wet[mode] = get_method("corps_engineers_1")(
                interslice_forces=mode).compute_fos(p, c, sl).fos
        assert all(math.isfinite(v) and v > 0 for v in wet.values()), wet
        rel = abs(wet["effective"] - wet["total"]) / wet["effective"]
        assert rel > 0.01, wet

        p_dry = _ej1_project()
        c_dry = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl_dry = slice_surface(p_dry, c_dry, 25)
        dry = [get_method("corps_engineers_1")(
            interslice_forces=mode).compute_fos(p_dry, c_dry, sl_dry).fos
            for mode in ("effective", "total")]
        assert abs(dry[0] - dry[1]) < 1e-12, dry

    def test_an_unknown_value_falls_back_to_the_default(self):
        from ogr_slip2d.methods import CorpsOfEngineers1
        assert CorpsOfEngineers1(
            interslice_forces="nonsense").interslice_forces == "effective"
        assert CorpsOfEngineers1(
            interslice_forces="TOTAL").interslice_forces == "total"


# ======================================================================
class TestTheyAreRegisteredAsForceMethods:
    def test_registered_with_the_ids_the_enum_declares(self):
        from ogr_core.project.settings import LEMMethod as LEM
        from ogr_slip2d.methods import method_registry
        reg = method_registry()
        for m in (LEM.CORPS_OF_ENGINEERS_1, LEM.CORPS_OF_ENGINEERS_2):
            assert m.value in reg, m.value
            cls = reg[m.value]
            assert cls.SATISFIES_FORCE is True
            assert cls.SATISFIES_MOMENT is False

    def test_they_publish_boundary_ratios_for_the_line_of_thrust(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _ej1_project()
        c = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl = slice_surface(p, c, 25)
        for mid in ("corps_engineers_1", "corps_engineers_2"):
            res = get_method(mid)().compute_fos(p, c, sl)
            ratios = res.details.get("boundary_ratios")
            assert ratios and len(ratios) == len(sl.slices) + 1, mid

    def test_the_cli_resolves_both_by_id_and_by_alias(self):
        from ogr_cli.__main__ import _resolve_method
        assert _resolve_method("corps_engineers_1") == "corps_engineers_1"
        assert _resolve_method("corps1") == "corps_engineers_1"
        assert _resolve_method("coe2") == "corps_engineers_2"

    def test_the_report_knows_their_names(self):
        from ogr_core.report.report_generator import _method_name
        assert _method_name("corps_engineers_1") == "Corps of Engineers #1"
        assert _method_name("corps_engineers_2") == "Corps of Engineers #2"


# ----------------------------------------------------------------------
# Model builders. Ej_1 is the dry reference slope every LEM method in this
# program is validated on; the wet one is a slope with a water table, and
# is where the effective/total split can show at all.
def _ej1_project():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, 50), Vertex(50, 50), Vertex(75, 25), Vertex(120, 25),
        Vertex(120, 0), Vertex(0, 0),
    ], closed=True)
    p = Project(name="ej1")
    p.boundaries.append(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Soil", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0)))
    return p


#: Deep circle through the saturated foundation of ``_wet_project``. Chosen
#: because it is where the three assumptions separate: the ground above it
#: runs from flat crest to slope face to flat toe, so #2's angle sweeps
#: while #1's stays constant, and the pore pressure on the vertical faces
#: is large enough for the effective/total split to matter.
_WET_CIRCLE = (40.0, 40.0, 38.0)


def _wet_project():
    """A benched slope with a water table, built here rather than imported
    so this file does not depend on the shape of another test module."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(80, 0), Vertex(80, 10), Vertex(50, 10),
        Vertex(20, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("wet")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(-5, 29), Vertex(20, 29), Vertex(50, 10), Vertex(85, 10),
    ], closed=False), btype=BoundaryType.WATER_TABLE))
    p.materials = [Material(
        name="Soil", unit_weight=19.0, sat_unit_weight=20.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
        pore_pressure=PorePressureType.WATER_TABLE)]
    return p
