# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The James Bay dyke — a published slice table for a NON-CIRCULAR surface in
PURELY COHESIVE soil.

**The invariant**: the force-equilibrium recursion must reproduce, slice by
slice, a *second* published spreadsheet of the same equation — this one on a
non-circular surface with ``phi = 0`` — and the critical surface that
spreadsheet describes must have no base anywhere near the ceiling the
m-alpha check imposes on such soil.

Why this case, and why now. Until this version every externally validated
case in this project had ``phi > 0`` and a CIRCULAR surface: the three
``test_slide_validation_*`` files are circles through frictional soils, and
the USACE table in ``test_modified_swedish_v198.py`` is ``c' = 0,
phi' = 30`` on every slice. The two anchors bracket each other — that one is
the friction-only end of the same recursion, this one the cohesion-only end.

Source: Duncan, J. M., Wright, S. G. and Brandon, T. L. (2014), *Soil
Strength and Slope Stability*, 2nd ed. (the edition of Duncan and Wright,
2005), section 7.7.6 "Example 6: James Bay Dike", Figure 7.29 — a force
equilibrium computation with the inter-slice force inclination fixed at
theta = 2.7 deg, the value Spencer's procedure returns for this problem.
The published factor of safety is 1.17, and the book reports the same 1.17
from Spencer and 1.16 from an unrestricted non-circular search. The
equation the figure prints is term for term the one USACE (2003),
EM 1110-2-1902 gives as C-19, which is why the recursion this program
already validates against that manual is the recursion that reproduces it.

**What this file measures for defect D61.** Under ``phi = 0`` the friction
term of ``n_alpha`` vanishes and the quantity degenerates to ``cos(a - t)``
exactly — it stops depending on the factor of safety, and the m-alpha check
stops being a statement about the method and becomes a bare ceiling on the
base angle (78.463 deg at the limit of 0.2). That is not deduced from this
program's arithmetic here: it is PRINTED in the published figure, which
tabulates ``n_alpha`` for three trial factors and shows it identical across
all three for the ten ``phi = 0`` slices while only the single ``phi = 30``
slice moves. D61 asked for a published case with such a soil, a
non-circular surface and a base above 60 deg, against which to decide
whether that ceiling is right. This is the case, and its steepest base in
``phi = 0`` material is 43.7 deg — so it cannot decide the ceiling, because
the ceiling never touches it. The defect stays open; the search is closed.

NOT tested here, deliberately: the factor of safety obtained by building
the cross section and letting this program slice it. The published weights
say the dyke has a berm — ``W/b`` falls from 523.4 to 481.3 to 442.9 kPa
across slices 5 to 8, so the ground above the flat run is not the crest —
and Figure 7.24 gives that berm as a drawing, not as coordinates. The only
way to close the gap would be to invert ``W_i / b_i`` to recover the
profile, which is deriving the geometry from the very datum the comparison
is supposed to test until the number comes out right. That is a snapshot
with a citation on it, and rule 1 of this project exists to forbid exactly
that. The slice table IS the published datum; it is used as published.
"""
from __future__ import annotations

import math


# ======================================================================
# Duncan, Wright and Brandon (2014), Figure 7.29 — the published sheet.
#
#   b       horizontal width of the slice, m
#   alpha   base inclination, deg, positive where the base is inclined
#           the same way as the slope face (the convention Table 15.1 of
#           the same source states, and the one ``Slice.base_angle`` uses)
#   W       slice weight, kN/m
#   ell     base length, m — published, NOT derived, so that b/cos(alpha)
#           can be checked against it
#   c       cohesion on the base, kPa: the undrained strength of the layer
#           the base runs through
#   phi     friction angle, deg — 30 in the fill, 0 in all three clays
#
# There is no pore pressure anywhere in the published computation: the
# analysis is a total-stress one in undrained clay.
# ======================================================================
JB_F729 = [
    #  b     alpha     W      ell     c    phi
    (7.7, 57.2, 926, 14.3, 0.0, 30.0),
    (4.7, 40.3, 1319, 6.2, 41.0, 0.0),
    (10.2, 38.2, 4019, 12.9, 34.5, 0.0),
    (11.2, 30.2, 5868, 12.9, 31.5, 0.0),
    (12.1, 0.0, 6333, 12.1, 31.5, 0.0),
    (28.2, 0.0, 13572, 28.2, 31.5, 0.0),
    (28.2, 0.0, 13572, 28.2, 31.5, 0.0),
    (11.9, 0.0, 5270, 11.9, 31.5, 0.0),
    (9.9, -33.1, 3064, 11.9, 31.5, 0.0),
    (9.3, -40.6, 1446, 12.3, 34.5, 0.0),
    (4.2, -43.7, 168, 5.8, 41.0, 0.0),
]

#: The inter-slice force inclination of the published computation, deg.
#: The book does not choose it: it is the value Spencer's procedure
#: returns for this problem, which is why reproducing the sheet with it
#: and failing to reproduce it without it (below) means something.
JB_THETA = 2.7

#: The published factor of safety of the sheet, and of Spencer.
JB_F = 1.17

#: ``W sin(alpha)``, the driving column, as printed.
JB_W_SIN_A = [779, 854, 2485, 2952, 0, 0, 0, 0, -1675, -942, -116]

#: ``-c*ell - (W cos(alpha) - u*ell) tan(phi')``, the resisting column at
#: a trial factor of 1, as printed.
JB_RESID_F1 = [-289, -253, -446, -406, -382, -887, -887, -375, -374, -424,
               -238]

#: The accumulated inter-slice force ``Z`` at a trial factor of 1, as
#: printed. The last entry is the force imbalance the book plots against
#: the trial factor to find its root.
JB_Z_F1 = [466, 1225, 3730, 6601, 6218, 5331, 4453, 4068, 1541, -336, -847]

#: ``n_alpha`` as printed, for the three trial factors the figure carries.
#: THIS IS THE MEASUREMENT D61 IS ABOUT. Ten of the eleven rows are the
#: same number in all three columns, because with ``phi = 0`` the term
#: that carries the factor of safety is multiplied by zero. Only slice 1,
#: the one in the fill, moves.
JB_NA_F10 = [1.050, 0.791, 0.814, 0.887, 0.999, 0.999, 0.999, 0.999,
             0.811, 0.728, 0.690]
JB_NA_F12 = [0.972, 0.791, 0.814, 0.887, 0.999, 0.999, 0.999, 0.999,
             0.811, 0.728, 0.690]
JB_NA_F14 = [0.916, 0.791, 0.814, 0.887, 0.999, 0.999, 0.999, 0.999,
             0.811, 0.728, 0.690]

# ----------------------------------------------------------------------
# Duncan, Wright and Brandon (2014), Figure 7.24 — the cross section, as
# layer thicknesses in metres measured down from the crest. The figure
# labels all four, and labels the strengths that Figure 7.29 then uses.
#
#   crest of the dyke   y = +12.0     fill,        phi = 30, gamma = 20
#   foundation surface  y =   0.0     clay crust,  su = 41,  gamma = 20
#   base of the crust   y =  -4.0     marine clay, su = 34.5, gamma = 18.8
#   base of the marine  y = -12.0     lacustrine,  su = 31.2, gamma = 20.3
#   top of the till     y = -18.5     till, "very strong"
#
# The figure gives the lacustrine clay as su = 31.2 and the spreadsheet of
# Figure 7.29 uses 31.5 on its six lacustrine slices. Both are exercised
# below; the difference between the two answers is the honest width of
# this comparison, in the same way the USACE anchor exercises the printed
# 18 deg and the true 18.435 deg of a 3:1 slope.
# ----------------------------------------------------------------------
JB_LAYER_TOP = (12.0, 0.0, -4.0, -12.0)
JB_TILL_TOP = -18.5
JB_LAYER_SU = (0.0, 41.0, 34.5, 31.5)
JB_LAYER_NAME = ("fill", "clay crust", "marine clay", "lacustrine clay")


# ======================================================================
# Helpers. These mirror ``tests/test_modified_swedish_v198.py`` line for
# line, because that file is where this program's force-equilibrium
# recursion is already anchored to a published table and the point here
# is to drive the SAME production recursion with a SECOND one.
# ======================================================================
def _material(c: float, phi: float):
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    return Material(name="JB", unit_weight=20.0,
                    strength=MohrCoulomb(cohesion=c, friction_angle=phi))


def _slices(rows):
    """Real :class:`Slice` objects carrying the published quantities.

    Only the quantities the recursion reads are meaningful here: width,
    base angle, base length, weight, pore pressure and material. The
    base and top coordinates are placed on a local frame per slice
    because the recursion never asks where a slice is, only how it is
    inclined — the same simplification the USACE anchor makes.
    """
    from ogr_slip2d.slicer import Slice
    out = []
    for i, (b, ad, W, ell, c, phi) in enumerate(rows):
        a = math.radians(ad)
        out.append(Slice(
            index=i, x_centre=0.0, width=b,
            base_x_left=0.0, base_x_right=b,
            base_y_left=0.0, base_y_right=ell * math.sin(a),
            base_angle=a, base_length=ell,
            top_y_left=0.0, top_y_right=0.0,
            weight=W, pore_pressure=0.0,
            water_weight=0.0, water_force_h=0.0,
            material=_material(c, phi),
        ))
    return out


def _engine():
    """A member of the family, used only for its recursion.

    Any of the three would do: the recursion is shared and theta is
    supplied explicitly here. The classes that validate each theta RULE
    live in ``test_modified_swedish_v198.py``; this file validates the
    recursion those rules feed.
    """
    from ogr_slip2d.methods import CorpsOfEngineers1
    return CorpsOfEngineers1()


def _march(rows, theta_deg: float, F: float):
    """The published column, in the frame the book marches in.

    The book walks from the crest to the toe. This program mirrors the
    geometry in x when the mass slides that way (``orient = -1`` inside
    ``_force_balance``), which maps alpha to -alpha and theta to -theta.
    Doing that here by hand is what lets the published table drive the
    production recursion untouched — and it is exact rather than a
    convenience, because ``cos(a - t) - k sin(-(a - t))`` is
    ``cos(a - t) + k sin(a - t)``, which is ``n_alpha`` itself.
    """
    slist = _slices(rows)
    n = len(slist)
    alpha_n = [-s.base_angle for s in slist]
    theta = [-math.radians(theta_deg)] * n
    return _engine()._march(slist, theta, alpha_n, 0.0, 0.0, F,
                            h_water=[0.0] * n, v_support=[0.0] * n)


def _root(rows, theta_deg: float, lo: float = 0.8, hi: float = 2.0):
    """Bisect on the closure force, which is what the book does by
    plotting the imbalance of the last slice against the trial factor."""
    def f(F):
        z = _march(rows, theta_deg, F)
        assert z is not None, f"the recursion aborted at F = {F}"
        return z[-1]

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


def _with_lacustrine(su: float):
    """The same table with the lacustrine strength of Figure 7.24."""
    return [(b, a, W, ell, su if abs(c - 31.5) < 1e-9 else c, phi)
            for (b, a, W, ell, c, phi) in JB_F729]


def _n_alpha(rows, theta_deg: float, F: float):
    """``n_alpha`` as the published figure defines it."""
    t = math.radians(theta_deg)
    out = []
    for (_b, ad, _W, _ell, _c, phi) in rows:
        a = math.radians(ad)
        out.append(math.cos(a - t)
                   + math.sin(a - t) * math.tan(math.radians(phi)) / F)
    return out


def _surface_from_the_table():
    """The slip surface the published columns describe.

    ``dy = b tan(alpha)`` marched from the crest. This is geometry, not
    an assumption: b and alpha are both published, and the result is
    checked against the layer boundaries of a DIFFERENT published figure
    below, which is what makes it evidence rather than a construction.
    """
    xs, ys = [0.0], [JB_LAYER_TOP[0]]
    for (b, ad, _W, _ell, _c, _phi) in JB_F729:
        xs.append(xs[-1] + b)
        ys.append(ys[-1] - b * math.tan(math.radians(ad)))
    return xs, ys


def _layer_of(y: float) -> int:
    """Index of the layer a base at ``y`` runs through.

    A slice base belongs to the material ABOVE it, so the interval is
    open below and closed above: the flat run along the top of the till
    is lacustrine clay, which is what the published c column says it is.
    """
    bounds = list(JB_LAYER_TOP) + [JB_TILL_TOP]
    for i in range(len(JB_LAYER_TOP)):
        if bounds[i + 1] < y <= bounds[i] + 1e-9:
            return i
    return -1


# ======================================================================
class TestThePublishedSheetClosesOnItself:
    """Anchor 1 — the source is self-consistent, checked without the
    engine at all.

    If the printed columns did not close on each other there would be
    nothing to validate against, and a transcription slip in the table
    above would look exactly like an engine defect further down. This is
    the cheapest place to catch one.
    """

    def test_base_length_is_the_width_over_the_cosine(self):
        for i, (b, ad, _W, ell, _c, _phi) in enumerate(JB_F729):
            got = b / math.cos(math.radians(ad))
            assert abs(got - ell) / ell < 0.01, (i, got, ell)

    def test_the_driving_column_is_the_weight_times_the_sine(self):
        scale = max(abs(v) for v in JB_W_SIN_A)
        for i, (_b, ad, W, _ell, _c, _phi) in enumerate(JB_F729):
            got = W * math.sin(math.radians(ad))
            assert abs(got - JB_W_SIN_A[i]) < 0.005 * scale, (i, got)

    def test_the_resisting_column_is_the_strength_at_a_trial_of_one(self):
        scale = max(abs(v) for v in JB_RESID_F1)
        for i, (_b, ad, W, ell, c, phi) in enumerate(JB_F729):
            a = math.radians(ad)
            tp = math.tan(math.radians(phi))
            got = -(c * ell) - (W * math.cos(a)) * tp
            assert abs(got - JB_RESID_F1[i]) < 0.005 * scale, (i, got)

    def test_n_alpha_does_not_move_with_the_factor_where_phi_is_zero(self):
        """The measurement D61 is about, read off the published figure.

        Ten of the eleven slices carry ``phi = 0``. For those the term
        that contains the factor of safety is multiplied by zero, so the
        three published columns are the same column. Only slice 1, the
        one in the fill, is a function of F at all.
        """
        for i in range(1, len(JB_F729)):
            assert JB_NA_F10[i] == JB_NA_F12[i] == JB_NA_F14[i], i
        assert len({JB_NA_F10[0], JB_NA_F12[0], JB_NA_F14[0]}) == 3

    def test_and_that_is_arithmetic_not_a_coincidence_of_printing(self):
        """The same statement, recomputed from the definition."""
        for F in (1.0, 1.2, 1.4):
            got = _n_alpha(JB_F729, JB_THETA, F)
            for i in range(1, len(JB_F729)):
                # cos(a - t) exactly, with no F in it anywhere.
                assert abs(got[i]
                           - math.cos(math.radians(JB_F729[i][1] - JB_THETA))
                           ) < 1e-12, (i, F)

    def test_the_published_n_alpha_columns_are_reproduced(self):
        for F, pub in ((1.0, JB_NA_F10), (1.2, JB_NA_F12), (1.4, JB_NA_F14)):
            got = _n_alpha(JB_F729, JB_THETA, F)
            for i, (g, p) in enumerate(zip(got, pub)):
                assert abs(g - p) < 0.002, (F, i, g, p)


# ======================================================================
class TestTheRecursionReproducesTheSheet:
    """Anchor 2 — this program's production recursion, against the
    published columns and the published factor of safety."""

    def test_the_interslice_force_column(self):
        got = _march(JB_F729, JB_THETA, 1.0)
        assert got is not None
        scale = max(abs(v) for v in JB_Z_F1)
        worst = max(abs(g - p) for g, p in zip(got, JB_Z_F1))
        assert worst < 0.005 * scale, (worst, scale, got)

    def test_the_factor_of_safety_the_book_publishes(self):
        got = _root(JB_F729, JB_THETA)
        assert abs(got - JB_F) / JB_F < 0.005, got

    def test_the_strength_the_section_figure_gives_lands_there_too(self):
        """Figure 7.24 says the lacustrine clay is su = 31.2; the
        spreadsheet uses 31.5. Both reproduce the published factor, and
        the gap between them is the width of this comparison."""
        got = _root(_with_lacustrine(31.2), JB_THETA)
        assert abs(got - JB_F) / JB_F < 0.005, got

    def test_the_inclination_is_identified_by_the_data_not_assumed(self):
        """theta = 2.7 deg is not a knob that was turned until the
        answer appeared: marching the same sheet with horizontal side
        forces misses the published factor by several per cent."""
        with_theta = _root(JB_F729, JB_THETA)
        without = _root(JB_F729, 0.0)
        assert abs(without - JB_F) / JB_F > 0.05, without
        assert abs(with_theta - JB_F) / JB_F < 0.005, with_theta

    def test_the_recursion_never_aborts_over_the_bracket(self):
        """``_march`` returns None when its denominator collapses. On
        this sheet it cannot: with phi = 0 on ten slices the denominator
        is cos(a - t), which is 0.69 at worst."""
        for F in (0.8, 1.0, 1.17, 1.4, 2.0):
            assert _march(JB_F729, JB_THETA, F) is not None, F


# ======================================================================
class TestTheGeometryOfTheTableIsTheGeometryOfTheSection:
    """Anchor 3 — the strongest of the four, and pure geometry.

    Figure 7.29 prints b and alpha; Figure 7.24 prints the layer
    thicknesses and the strengths. Neither mentions the other. Marching
    ``dy = b tan(alpha)`` from the crest has to land on the boundaries of
    the second figure, and the layer each slice lands in has to carry the
    strength the first figure gives it. Two published figures agreeing
    to within centimetres is what makes this a case and not a table.
    """

    def test_the_surface_lands_on_the_published_layer_boundaries(self):
        _xs, ys = _surface_from_the_table()
        # After slices 1..4 the surface has crossed the whole profile,
        # and after 9..11 it has climbed back out through it.
        expected = {1: 0.0, 2: -4.0, 3: -12.0, 4: JB_TILL_TOP,
                    9: -12.0, 10: -4.0, 11: 0.0}
        for k, want in expected.items():
            assert abs(ys[k] - want) < 0.10, (k, ys[k], want)

    def test_the_flat_run_is_on_top_of_the_till(self):
        xs, ys = _surface_from_the_table()
        for k in (4, 5, 6, 7, 8):
            assert abs(ys[k] - JB_TILL_TOP) < 0.10, (k, ys[k])
        assert abs((xs[8] - xs[4]) - 80.4) < 0.1, xs[8] - xs[4]

    def test_each_slice_carries_the_strength_of_the_layer_it_runs_in(self):
        """The link between the two figures, slice by slice."""
        _xs, ys = _surface_from_the_table()
        for i, (_b, _ad, _W, _ell, c, _phi) in enumerate(JB_F729):
            mid = 0.5 * (ys[i] + ys[i + 1])
            layer = _layer_of(mid)
            assert layer >= 0, (i, mid)
            assert abs(JB_LAYER_SU[layer] - c) < 1e-9, (
                i, JB_LAYER_NAME[layer], c)

    def test_the_one_frictional_slice_is_the_one_in_the_fill(self):
        _xs, ys = _surface_from_the_table()
        for i, (_b, _ad, _W, _ell, _c, phi) in enumerate(JB_F729):
            mid = 0.5 * (ys[i] + ys[i + 1])
            in_fill = _layer_of(mid) == 0
            assert (phi > 0.0) is in_fill, (i, phi, mid)


# ======================================================================
class TestWhatThisSaysAboutTheMAlphaCeiling:
    """Anchor 4 — the measurement the defect asked for, and the reason
    it does not settle it.

    D61 asked for a published case with a non-circular surface in
    ``phi = 0`` soil and a base above 60 deg, against which to decide
    whether the 0.2 limit is the right one for such soil. This is that
    case in every respect but the last: the steepest base in cohesive
    material is 43.7 deg, and the steepest anywhere is 57.2 deg, on the
    one slice that has friction. The published critical surface never
    approaches the ceiling, so it cannot calibrate it.
    """

    def test_no_base_in_cohesive_material_reaches_sixty_degrees(self):
        steep = max(abs(ad) for (_b, ad, _W, _ell, _c, phi) in JB_F729
                    if phi == 0.0)
        assert abs(steep - 43.7) < 1e-9, steep
        assert steep < 60.0, steep

    def test_the_steepest_base_of_all_is_the_frictional_one(self):
        steep = max(abs(ad) for (_b, ad, _W, _ell, _c, _phi) in JB_F729)
        assert abs(steep - 57.2) < 1e-9, steep
        worst = max(JB_F729, key=lambda r: abs(r[1]))
        assert worst[5] > 0.0, worst

    def test_the_published_surface_sits_far_below_the_ceiling(self):
        """The ceiling the limit imposes on purely cohesive soil, and how
        far the published answer is from it. Imported rather than
        written out, so that moving the limit moves this test."""
        from ogr_slip2d.checks import M_ALPHA_LIMIT
        ceiling = math.degrees(math.acos(M_ALPHA_LIMIT))
        assert abs(ceiling - 78.463) < 0.001, ceiling
        steep = max(abs(ad) for (_b, ad, _W, _ell, _c, phi) in JB_F729
                    if phi == 0.0)
        assert steep < ceiling - 30.0, (steep, ceiling)

    def test_the_check_would_have_measured_a_different_number(self):
        """NOT a validation — a measured inequality, and the evidence for
        defect D111.

        ``checks.base_m_alphas`` always evaluates the Bishop form, with
        the inter-slice inclination set to zero. The published sheet is a
        force-equilibrium procedure whose denominator carries its own
        theta. The source separates the two explicitly (its Eq. 14.5 for
        Spencer and Eq. 14.6 for Bishop, "identical ... when the
        interslice force inclination is set to zero"), and under phi = 0
        they are cos(a) against cos(a - t), which are different numbers.
        Comparing them as though they were the same is what this file
        must not do, so it asserts that they differ instead.
        """
        pub = _n_alpha(JB_F729, JB_THETA, 1.0)
        bishop_form = _n_alpha(JB_F729, 0.0, 1.0)
        # Slice 11, the steepest cohesive base, is where it is widest.
        assert abs(bishop_form[10] - 0.7230) < 5e-4, bishop_form[10]
        assert abs(pub[10] - 0.6896) < 5e-4, pub[10]
        rel = abs(bishop_form[10] - pub[10]) / pub[10]
        assert rel > 0.03, rel


# ======================================================================
def _positioned_slices(rows, top_y: float = 0.0):
    """The same published slices, placed on the reconstructed surface.

    A method that takes moments needs to know WHERE each slice is, which
    the marching recursion above does not. The positions come from the
    same two published columns the geometry test uses, so nothing new is
    assumed here — and ``top_y`` is shown to be inert below rather than
    asserted to be, because it is the one quantity in this file that is
    not published.
    """
    from ogr_slip2d.slicer import Slice
    xs, ys = _surface_from_the_table()
    out = []
    for i, (b, ad, W, ell, c, phi) in enumerate(rows):
        out.append(Slice(
            index=i, x_centre=0.5 * (xs[i] + xs[i + 1]), width=b,
            base_x_left=xs[i], base_x_right=xs[i + 1],
            base_y_left=ys[i], base_y_right=ys[i + 1],
            base_angle=math.radians(ad), base_length=ell,
            top_y_left=top_y, top_y_right=top_y,
            weight=W, pore_pressure=0.0,
            water_weight=0.0, water_force_h=0.0,
            material=_material(c, phi),
        ))
    return out


def _slip_surface():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    xs, ys = _surface_from_the_table()
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in zip(xs, ys)]))


def _spencer(rows, top_y: float = 0.0):
    from ogr_core.project import Project
    from ogr_slip2d.slicer import Slices
    from ogr_slip2d.methods import Spencer
    return Spencer().compute_fos(Project(), _slip_surface(),
                                 Slices(_positioned_slices(rows, top_y)))


class TestSpencerFindsBothNumbersTheBookPublishes:
    """Anchor 5 — the independent one, and the strongest claim here.

    The book does not choose theta = 2.7 deg: it reports it as the value
    Spencer's procedure returns for this problem, and separately reports
    Spencer's factor of safety as 1.17. So the published source carries
    TWO numbers, and a procedure that genuinely implements Spencer has to
    find both of them from the geometry alone, without being told either.

    This is a different assertion from anchor 2. There the published
    inclination was handed to the recursion and only the factor had to
    come out; here nothing is handed over and the inclination is part of
    the answer.
    """

    def test_spencer_reproduces_the_published_factor_of_safety(self):
        res = _spencer(JB_F729)
        assert res.converged, res.error_message
        assert abs(res.fos - JB_F) / JB_F < 0.01, res.fos

    def test_and_recovers_the_inclination_the_book_took_from_it(self):
        res = _spencer(JB_F729)
        theta = math.degrees(math.atan(res.details["lambda"]))
        assert abs(theta - JB_THETA) < 0.5, theta

    def test_the_answer_rests_only_on_published_quantities(self):
        """The slice top elevation is the one number in this file that
        the source does not publish, so it must not matter — and it does
        not, bit for bit, over a range wider than the whole section.

        Without this the anchor above would be resting on a value chosen
        here, which is the trap the module docstring refuses for the
        cross section as a whole.
        """
        answers = {_spencer(JB_F729, top).fos
                   for top in (-18.0, 0.0, 6.0, 12.0, 100.0)}
        assert len(answers) == 1, answers
