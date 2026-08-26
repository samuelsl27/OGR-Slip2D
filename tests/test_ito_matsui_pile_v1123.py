# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
An Ito-Matsui pile is a pressure the SOIL decides, integrated to the cut.

THE INVARIANT. In this mode ``PileMicropile.force_at(d, L)`` is not a
property of the pile at all: it is the integral, from the top of the pile
down to depth ``d``, of the lateral pressure the ground develops as it
squeezes between the piles of the row — divided by the spacing, because the
equation gives a force per PILE and this method must return a force per
METRE OF SLOPE. Close the piles up and the pressure rises; open them out
and it falls; take the diameter to zero and it vanishes exactly.

THE ANCHORS, none of them a captured value.

* **Two independent printings of the same equation.** Ito, T. and Matsui,
  T. (1975), *Soils and Foundations* 15(4) 43-59, Eq. (13); and Cai, F. and
  Ugai, K. (2000), *Soils and Foundations* 40(1) 73-84, Eq. (10), which is
  the same expression grouped around ``A``. This file codes the second one
  inline and asserts the two agree, which is a transcription check the
  implementation cannot pass by being self-consistent.

* **Three analytical identities inside the paper itself.** Eq. (13) with
  ``c = 0`` must reproduce its Eq. (14); Eq. (13) as φ → 0 must reproduce
  its Eq. (23); and Eq. (23) must reproduce its own re-derivation from
  Eqs. (16), (19), (21) and (22), which is what rules out a misread of the
  scan rather than a mistyped coefficient.

* **An exact identity the paper does not state.** With the opening equal to
  the spacing — a pile of zero diameter — every term of Eq. (13) cancels
  against another and the pressure is exactly zero. A pile that occupies no
  space cannot make soil squeeze.

* **Cai and Ugai's Eq. (9)**, ``M_P = Q·R·cos θ / D1``, which says where
  the force acts and how its moment is taken. Asserted directly on the
  geometry, so the engine is pinned to the published equation and not to
  its own opinion.

* **The published model**, Cai and Ugai Fig. 2 and Table 1: a 10 m slope at
  1V:1.5H on 10 m of ground, γ = 20, c = 10, φ = 20°, a 0.8 m pile row at
  7.5 m from the toe. Their Bishop factor without piles is 1.13 and their
  Fig. 4 gives 1.54, 1.37, 1.31 and 1.25 for D1/D = 2, 3, 4 and 6. Those
  published factors are checked in the verification bank, not here — this
  file asserts the parts that do not need a search to be reproduced.

WHAT THIS FILE DELIBERATELY MEASURES RATHER THAN ASSUMES. The switch from
Eq. (13) to Eq. (23) near φ = 0 is a numerical decision, not a modelling
one, and the threshold is where the round-off of one crosses the truncation
of the other. ``test_the_switch_sits_where_the_two_errors_cross`` runs that
sweep and would fail if the constant were moved off the crossing, in either
direction.

WHAT IT DOES NOT CLAIM. Zhang and others (2017), *J. Geotech. Geoenviron.
Eng.* 143(9), argue the 1975 solution underestimates the pile force and
exceeds the passive pressure at close spacings. Nothing here says the
equation is right; it says the implementation is the equation.
"""
from __future__ import annotations

import math

# --- Cai and Ugai (2000), Fig. 2 and Table 1 --------------------------
GAMMA, COH, PHI_DEG = 20.0, 10.0, 20.0
DIAM = 0.8
PILE_X, PILE_TOP, PILE_BOT = 17.5, 15.0, 0.0
EXTERNAL = [(0.0, 0.0), (35.0, 0.0), (35.0, 20.0), (25.0, 20.0),
            (10.0, 10.0), (0.0, 10.0)]


# ======================================================================
# Helpers
# ======================================================================
def _cai_ugai_eq10(c, phi, gz, d1, d2):
    """Eq. (10) of Cai and Ugai (2000), typed from their printing.

    Deliberately NOT sharing a line of code with the implementation: it is
    grouped their way, around ``A``, and it exists so that a slip in
    transcribing one printing cannot be reproduced by the other.
    """
    n = math.tan(math.pi / 4.0 + phi / 2.0) ** 2
    tf = math.tan(phi)
    a = d1 * (d1 / d2) ** (n ** 0.5 * tf + n - 1.0)
    e = math.exp((d1 - d2) / d2 * n * tf * math.tan(math.pi / 8.0 + phi / 4.0))
    g = (2.0 * tf + 2.0 * n ** 0.5 + n ** -0.5) / (n ** 0.5 * tf + n - 1.0)
    q = c * a * ((1.0 / (n * tf)) * (e - 2.0 * n ** 0.5 * tf - 1.0) + g)
    q -= c * (d1 * g - 2.0 * d2 * n ** -0.5)
    q += gz / n * (a * e - d2)
    return q


def _eq23_rederived(c, gz, d1, d2):
    """Eq. (23) rebuilt from Eqs. (16), (19), (21) and (22) of the paper.

    sigma_x = 3c ln D + C3 with C3 from Eq. (21); p_BB' = D1 sigma_x(D1)
    is Eq. (22); the thrust on the plane at x = 0 is Eq. (19),
    ``gamma z - 2c``; and p is the difference. Assembled here term by term
    instead of collected, so that the printed Eq. (23) is checked against
    the derivation and not against itself.
    """
    c3 = c * ((d1 - d2) / d2 * math.tan(math.pi / 8.0)
              - 3.0 * math.log(d2) - 2.0) + gz
    sigma_x_d1 = 3.0 * c * math.log(d1) + c3
    p_bb = d1 * sigma_x_d1
    sigma_x_0 = gz - 2.0 * c
    return p_bb - d2 * sigma_x_0


def _pile(**kw):
    from ogr_core.support import PileMicropile
    base = dict(failure_mode="ito_matsui", out_of_plane_spacing=3.0 * DIAM,
                pile_diameter=DIAM)
    base.update(kw)
    return PileMicropile(**base)


def _project(ratio=3.0, orientation="perpendicular_to_pile", **kw):
    """The published model, with the pile row in Ito-Matsui mode."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)

    p = Project("ito-matsui")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in EXTERNAL], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=COH, friction_angle=PHI_DEG),
        pore_pressure=PorePressureType.NONE)]
    p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT

    stype = _pile(out_of_plane_spacing=ratio * DIAM, **kw)
    p.support_types = [stype]
    p.supports = [SupportInstance(
        type_id="pile_micropile",
        head=Vertex(PILE_X, PILE_TOP), tail=Vertex(PILE_X, PILE_BOT),
        orientation=ForceOrientation(orientation),
        force_application=ForceApplication.PASSIVE)]
    return p


def _circle():
    """A circle that crosses the pile well below its head."""
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=10.5, centre_y=29.0, radius=19.0)


def _fos(method_id, project, surface=None, num_slices=40):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    surface = surface or _circle()
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return method_registry()[method_id]().compute_fos(
        project, surface, sl).fos


def _effect(project, num_slices=40):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    surf = _circle()
    sl = slice_surface(project, surf, num_slices=num_slices)
    eff = compute_support_effects(project, surf, sl)
    return (eff[0] if eff else None), sl


# ======================================================================
class TestTheEquationAgainstItsSources:
    """Two printings, three internal identities and one exact cancellation."""

    def test_the_two_printings_of_the_same_equation_agree(self):
        """Ito and Matsui Eq. (13) against Cai and Ugai Eq. (10)."""
        from ogr_core.support import lateral_force_c_phi
        worst = 0.0
        for c in (0.0, 5.0, 10.0, 40.0):
            for deg in (5.0, 10.0, 20.0, 30.0, 40.0):
                for gz in (0.0, 50.0, 200.0):
                    for d1, d2 in ((2.4, 1.6), (1.6, 0.8), (3.2, 2.4),
                                   (4.8, 4.0), (2.0, 0.2)):
                        phi = math.radians(deg)
                        a = lateral_force_c_phi(c, phi, gz, d1, d2)
                        b = _cai_ugai_eq10(c, phi, gz, d1, d2)
                        if abs(a) > 1e-12:
                            worst = max(worst, abs(a - b) / abs(a))
        assert worst < 1e-13, worst

    def test_a_pile_of_no_diameter_pushes_nothing(self):
        """With the opening equal to the spacing, Eq. (13) is exactly zero.

        The cohesion terms cancel against each other and so does the
        overburden term, for every c, φ, γz and spacing. It is the
        sharpest check on the transcription in this file: get one
        coefficient wrong and the cancellation stops being exact.
        """
        from ogr_core.support import lateral_force_c_phi
        worst = 0.0
        for c in (0.0, 10.0, 100.0):
            for deg in (1.0, 10.0, 20.0, 35.0):
                for gz in (0.0, 100.0, 500.0):
                    for d1 in (1.0, 2.4, 10.0):
                        worst = max(worst, abs(lateral_force_c_phi(
                            c, math.radians(deg), gz, d1, d1)))
        assert worst < 1e-9, worst

    def test_the_cohesionless_case_is_the_general_one_without_cohesion(self):
        from ogr_core.support import (lateral_force_c_phi,
                                      lateral_force_cohesionless)
        for deg in (5.0, 20.0, 35.0):
            for gz in (10.0, 300.0):
                for d1, d2 in ((2.4, 1.6), (1.6, 0.8)):
                    phi = math.radians(deg)
                    assert (lateral_force_c_phi(0.0, phi, gz, d1, d2)
                            == lateral_force_cohesionless(phi, gz, d1, d2))

    def test_the_cohesive_case_is_the_limit_of_the_general_one(self):
        """Eq. (13) → Eq. (23) as φ → 0, and the approach is first order.

        Not merely "close at the end": each decade of φ must divide the
        disagreement by ten, which is what says the two are the same
        expression and not two expressions that happen to be near.
        """
        from ogr_core.support import (lateral_force_c_phi,
                                      lateral_force_cohesive)
        prev = None
        for e in (4, 5, 6, 7):
            phi = 10.0 ** (-e)
            a = lateral_force_c_phi(COH, phi, 100.0, 2.4, 1.6)
            b = lateral_force_cohesive(COH, 100.0, 2.4, 1.6)
            rel = abs(a - b) / abs(b)
            if prev is not None:
                assert 8.0 < prev / rel < 12.0, (e, prev, rel)
            prev = rel
        assert prev < 1e-6

    def test_the_cohesive_case_equals_its_own_rederivation(self):
        """Eq. (23) against Eqs. (16), (19), (21) and (22) reassembled."""
        from ogr_core.support import lateral_force_cohesive
        for c in (0.0, 10.0, 55.0):
            for gz in (0.0, 120.0):
                for d1, d2 in ((2.4, 1.6), (1.6, 0.8), (5.0, 0.5)):
                    a = lateral_force_cohesive(c, gz, d1, d2)
                    b = _eq23_rederived(c, gz, d1, d2)
                    assert abs(a - b) < 1e-9 * max(1.0, abs(b)), (c, gz, d1)

    def test_the_switch_sits_where_the_two_errors_cross(self):
        """The threshold is measured, and this is the measurement.

        Above the crossing the disagreement between the branches is the
        O(φ) truncation of Eq. (23) and falls a decade per decade; below
        it, it is the round-off of Eq. (13)'s cancellation and RISES. The
        constant must sit at the bottom of that valley — moving it either
        way makes the switch less continuous, not more.
        """
        from ogr_core.support import (PHI_SWITCH_RAD, lateral_force_c_phi,
                                      lateral_force_cohesive)
        cases = [(10.0, 100.0, 2.4, 1.6), (40.0, 0.0, 1.6, 0.8),
                 (5.0, 500.0, 4.8, 4.0), (100.0, 50.0, 2.0, 0.2)]

        def gap(phi):
            worst = 0.0
            for c, gz, d1, d2 in cases:
                a = lateral_force_c_phi(c, phi, gz, d1, d2)
                b = lateral_force_cohesive(c, gz, d1, d2)
                if abs(b) > 1e-12:
                    worst = max(worst, abs(a - b) / abs(b))
            return worst

        assert PHI_SWITCH_RAD == 1.0e-8
        here = gap(PHI_SWITCH_RAD)
        assert here < 1.0e-7, here
        # A decade up is truncation-dominated, so it is worse.
        assert gap(PHI_SWITCH_RAD * 10.0) > here
        # Two decades down is round-off dominated, so it is worse too.
        assert gap(PHI_SWITCH_RAD / 100.0) > here

    def test_touching_piles_are_refused_and_not_approximated(self):
        """The (D1/D2) power diverges when the opening closes.

        Returning a very large number would put an arbitrary force into a
        factor of safety with nothing to say it came from a model outside
        its own range.
        """
        import pytest

        from ogr_core.support import lateral_force_c_phi
        for d1, d2 in ((2.4, 0.0), (2.4, -0.1), (0.0, 0.0), (2.4, 2.5)):
            with pytest.raises(ValueError):
                lateral_force_c_phi(COH, 0.35, 100.0, d1, d2)

    def test_the_pressure_grows_linearly_with_depth(self):
        """Cai and Ugai state it in as many words, so it is checkable.

        "This equation implies that the lateral force per unit thickness
        increases linearly with the depth". In one material it does, and
        that is also why 50 samples integrate it without error.
        """
        from ogr_core.support import lateral_force_c_phi
        phi, d1, d2 = math.radians(PHI_DEG), 2.4, 1.6
        q0 = lateral_force_c_phi(COH, phi, 0.0, d1, d2)
        q1 = lateral_force_c_phi(COH, phi, GAMMA * 1.0, d1, d2)
        slope = q1 - q0
        for z in (0.5, 3.0, 7.5, 12.0):
            got = lateral_force_c_phi(COH, phi, GAMMA * z, d1, d2)
            assert abs(got - (q0 + slope * z)) < 1e-9 * max(1.0, abs(got))
        # And it is a rising pressure, not a falling one.
        assert slope > 0.0

    def test_closing_the_row_raises_the_pressure(self):
        """Monotone in the spacing, which is the whole point of the model."""
        from ogr_core.support import clear_spacing, lateral_force
        phi = math.radians(PHI_DEG)
        last = None
        for ratio in (2.0, 3.0, 4.0, 6.0, 10.0):
            d1 = ratio * DIAM
            q = lateral_force(COH, phi, GAMMA * 5.0, d1,
                              clear_spacing(d1, DIAM)) / d1
            if last is not None:
                assert q < last, ratio
            last = q


# ======================================================================
class TestTheSampledProfile:
    """The first moment, and that it agrees with its own integral."""

    def test_the_centroid_of_a_linear_ramp_is_the_closed_form(self):
        from ogr_core.support import BondProfile
        n, length = 4000, 10.0
        step = length / n
        tau = [30.0 + 38.0 * (i + 0.5) * step for i in range(n)]
        bp = BondProfile.from_samples(tau, length)
        for d in (2.0, 6.0, 10.0):
            area = 30.0 * d + 38.0 * d * d / 2.0
            first = 30.0 * d * d / 2.0 + 38.0 * d ** 3 / 3.0
            assert abs(bp.integral(0.0, d) - area) < 1e-4 * area
            assert abs(bp.moment(0.0, d) - first) < 1e-4 * first

    def test_the_centroid_can_never_fall_outside_the_mobilised_length(self):
        """The two integrals share a convention so the quotient cannot drift.

        Written with different conventions for the last partial segment,
        the centroid of a short mobilised stretch can land beyond its own
        end — a resultant acting below the cut, which is nonsense the
        moment equation would nevertheless accept.
        """
        from ogr_core.support import BondProfile
        bp = BondProfile.from_samples(
            [1.0 + 5.0 * i for i in range(50)], 10.0)
        for k in range(1, 200):
            d = 10.0 * k / 200.0
            arm = bp.moment(0.0, d) / bp.integral(0.0, d)
            assert 0.0 <= arm <= d + 1e-12, d


# ======================================================================
class TestThePileInTheModel:
    """The type, fed by a real project."""

    def test_the_force_is_the_integral_divided_by_the_spacing(self):
        """Rebuilt from the published equation, sample by sample.

        The pressure is linear in depth in one material, so its integral
        to the cut has a closed form and does not need the profile at all
        — which is what makes this a check on the machinery rather than on
        itself.
        """
        from ogr_core.support import clear_spacing, lateral_force
        p = _project(3.0)
        eff, _sl = _effect(p)
        assert eff is not None
        d = PILE_TOP - eff.intersection_y
        assert d > 1.0, "the fixture circle must cut the pile below its head"

        phi = math.radians(PHI_DEG)
        d1 = p.support_types[0].out_of_plane_spacing
        d2 = clear_spacing(d1, DIAM)
        q0 = lateral_force(COH, phi, 0.0, d1, d2)
        q1 = lateral_force(COH, phi, GAMMA, d1, d2)
        expected = (q0 * d + (q1 - q0) * d * d / 2.0) / d1
        assert abs(eff.force_magnitude - expected) < 1e-3 * expected

    def test_refining_the_sampling_does_not_move_the_force(self):
        """50 samples are enough, and this is what says so.

        The same shape of check the pullout profile got in v0.1.116: if
        the answer moved when the step halved, the number published would
        be a property of the sampling and not of the model.
        """
        from ogr_core.support import build_bond_profile
        p = _project(3.0)
        stype, sup = p.support_types[0], p.supports[0]
        ref = None
        for n in (25, 50, 100, 400):
            bp = build_bond_profile(p, sup, stype, segments=n)
            f = stype.force_at(6.0, sup.length(), bp)
            if ref is None:
                ref = f
            else:
                assert abs(f - ref) < 1e-4 * ref, (n, f, ref)

    def test_a_surface_above_the_head_mobilises_nothing(self):
        p = _project(3.0)
        stype, sup = p.support_types[0], p.supports[0]
        from ogr_core.support import build_bond_profile
        bp = build_bond_profile(p, sup, stype)
        assert stype.force_at(0.0, sup.length(), bp) == 0.0

    def test_without_a_project_the_force_is_zero_and_not_a_guess(self):
        """``force_at`` with no profile is a tooltip before the geometry.

        Zero is the honest answer for a force that IS the soil; the
        alternative is a number computed from a soil nobody chose.
        """
        assert _pile().force_at(5.0, 10.0) == 0.0


# ======================================================================
class TestCaiAndUgaiEquationNine:
    """Where the force acts and how its moment is taken."""

    def test_the_force_is_horizontal_and_acts_where_the_surface_cuts(self):
        """The two halves of Cai and Ugai Eq. (9) that are exact.

        Their ``M_P = Q·R·cos θ / D1`` is the moment of a HORIZONTAL force
        ``Q/D1`` applied at the cut, because the vertical offset from the
        centre to a point of a circle whose tangent leans θ is ``R·cos θ``.
        The direction and the point of application are exact and asserted
        here; the arm itself is a discretisation and is checked below.
        """
        p = _project(3.0, "perpendicular_to_pile")
        eff, _sl = _effect(p)
        assert eff is not None
        assert eff.force_v == 0.0
        assert eff.force_magnitude == abs(eff.force_h)
        # And it acts where the surface cuts, not somewhere near it.
        assert (eff.application_x, eff.application_y) == \
            (eff.intersection_x, eff.intersection_y)

    def test_the_arm_is_R_cos_theta_in_the_limit(self):
        """And the residual is the polyline, not the formulation.

        A support intersects the polyline of slice BASES, not the circle,
        so at 40 slices the cut sits a millimetre inside it and the base
        angle is a chord. Both errors fall with the slicing, and saying
        so is the difference between a discretisation and a defect.
        """
        circle = _circle()
        gaps = []
        for n in (40, 1000):
            p = _project(3.0, "perpendicular_to_pile")
            eff, sl = _effect(p, num_slices=n)
            theta = _base_angle_at(sl, eff.intersection_x)
            arm = circle.centre_y - eff.intersection_y
            gaps.append(abs(arm - circle.radius * math.cos(theta)) / arm)
        assert gaps[0] < 2e-3, gaps
        assert gaps[1] < gaps[0] / 3.0, gaps

    def test_the_tangential_share_is_the_one_their_equation_keeps(self):
        """OGR splits the horizontal force; their Eq. (9) keeps one half.

        A horizontal force on an inclined base has a component along it
        and one across it, and the split is EXACT: the tangential share is
        ``F·cos θ``, which is what Cai and Ugai's ``cos θ`` picks out, and
        the normal share is ``F·sin θ``. That second one is not discarded
        by this program — it presses on the base and earns ``T_N·tanφ'`` —
        which is a real difference between the two formulations, measured
        here rather than assumed away.
        """
        from ogr_slip2d.support_integration import resolve_support_terms
        p = _project(3.0, "perpendicular_to_pile")
        eff, sl = _effect(p)
        terms = resolve_support_terms(p, _circle(), sl, 1.0)
        theta = _base_angle_at(sl, eff.intersection_x)
        f = eff.force_magnitude
        # Passive, so the whole tangential share is on that side.
        assert sum(terms.t_active) == 0.0
        assert abs(sum(terms.t_passive) - f * math.cos(theta)) < 1e-9 * f
        assert abs(sum(terms.n_press) - f * math.sin(theta)) < 1e-9 * f
        # Which is the term Cai and Ugai do not have, and it is not small.
        assert sum(terms.n_press) > 0.2 * f

    def test_applying_it_tangentially_instead_changes_the_moment(self):
        """The two orientations are not two ways of writing one thing.

        The reference declares TANGENTIAL the default for a pile; Cai and
        Ugai apply the force horizontally. On a vertical pile the second
        is perpendicular-to-pile, so both are available, and they give
        different numbers by construction — which is why the closure of
        this feature measures both instead of choosing the one that fits.
        """
        a = _fos("bishop_simplified", _project(3.0, "perpendicular_to_pile"))
        b = _fos("bishop_simplified", _project(3.0, "tangent_to_slip"))
        assert abs(a - b) > 1e-4, (a, b)


def _base_angle_at(slices, x):
    """Inclination of the slip base at ``x``, radians."""
    for s in slices.slices:
        if s.base_x_left - 1e-9 <= x <= s.base_x_right + 1e-9:
            return math.atan2(s.base_y_right - s.base_y_left,
                              s.base_x_right - s.base_x_left)
    raise AssertionError("x outside the surface")


# ======================================================================
class TestRuleSeven:
    """Every control moves the number, and the one that cannot says so."""

    def test_the_mode_moves_the_number(self):
        shear = _fos("bishop_simplified", _project(3.0, **{
            "failure_mode": "shear", "pile_shear_strength": 300.0}))
        ito = _fos("bishop_simplified", _project(3.0))
        assert abs(shear - ito) > 1e-3, (shear, ito)

    def test_the_diameter_moves_the_number(self):
        """Through the opening D2 = spacing − diameter, and only there."""
        thin = _fos("bishop_simplified", _project(3.0, pile_diameter=0.4))
        fat = _fos("bishop_simplified", _project(3.0, pile_diameter=1.2))
        assert fat > thin + 1e-4, (thin, fat)

    def test_the_spacing_moves_the_number(self):
        """Closing the row up raises the factor, opening it out lowers it."""
        wide = _fos("bishop_simplified", _project(6.0))
        tight = _fos("bishop_simplified", _project(2.0))
        assert tight > wide + 1e-3, (tight, wide)

    def test_only_the_ratio_survives_the_division_by_the_spacing(self):
        """Eq. (13) is homogeneous of degree one in the two lengths.

        Every term of it carries exactly one power of a length, so scaling
        the spacing and the diameter together multiplies ``p`` by the same
        factor — and dividing by ``D1`` cancels it EXACTLY. The force per
        metre of slope therefore depends on the spacing only through
        ``D1/D``, which is not a coincidence of this implementation: it is
        why Cai and Ugai, and the verification manual after them, tabulate
        the problem against *spacing / diameter* and never against either
        one alone.

        It is also the reason the previous test is phrased as it is: a
        spacing sweep at FIXED RATIO would show no effect at all, and
        reading that as an inert setting would be exactly backwards.
        """
        from ogr_core.support import clear_spacing, lateral_force
        phi = math.radians(PHI_DEG)
        for ratio in (2.0, 3.0, 6.0):
            ref = None
            for scale in (0.5, 1.0, 4.0, 25.0):
                d1 = ratio * DIAM * scale
                q = lateral_force(COH, phi, 100.0, d1,
                                  clear_spacing(d1, DIAM * scale)) / d1
                if ref is None:
                    ref = q
                else:
                    assert abs(q - ref) < 1e-12 * abs(ref), (ratio, scale)

    def test_the_location_of_force_moves_the_four_moment_methods(self):
        moment_methods = ("ordinary_fellenius", "bishop_simplified",
                          "spencer", "gle_morgenstern_price")
        for mid in moment_methods:
            a = _fos(mid, _project(3.0, force_location="intersection"))
            b = _fos(mid, _project(3.0, force_location="centroid"))
            assert abs(a - b) > 1e-6, (mid, a, b)

    def test_the_location_of_force_cannot_move_the_other_five(self):
        """The other half of the claim, and the easy one to leave unsaid.

        Moving a force leaves a couple, and a couple has nowhere to go in
        a method that writes force equilibrium alone. Bit for bit, not
        nearly.
        """
        force_methods = ("janbu_simplified", "janbu_corrected",
                         "corps_engineers_1", "corps_engineers_2",
                         "lowe_karafiath")
        for mid in force_methods:
            a = _fos(mid, _project(3.0, force_location="intersection"))
            b = _fos(mid, _project(3.0, force_location="centroid"))
            assert a == b, (mid, a, b)

    def test_the_pile_raises_the_factor_of_safety(self):
        """The obvious one, and it would be embarrassing to leave out."""
        bare = _project(3.0)
        bare.supports = []
        bare.support_types = []
        assert _fos("bishop_simplified", _project(3.0)) > \
            _fos("bishop_simplified", bare) + 1e-3


# ======================================================================
class TestShearModeIsUntouched:
    """A pile that is not in the new mode must not notice it exists."""

    def test_the_constant_force_is_still_the_constant(self):
        from ogr_core.support import PileMicropile
        p = PileMicropile(pile_shear_strength=100.0, out_of_plane_spacing=2.0)
        assert p.force_at(0.0, 5.0) == 50.0
        assert p.force_at(5.0, 5.0) == 50.0
        assert p.force_at(2.5, 5.0, None) == 50.0

    def test_shear_mode_builds_no_profile(self):
        """It would be 50 soil samples per pile per analysis, unread."""
        from ogr_core.support import build_bond_profile
        p = _project(3.0, failure_mode="shear")
        stype, sup = p.support_types[0], p.supports[0]
        assert not stype.NEEDS_BOND_PROFILE
        assert build_bond_profile(p, sup, stype).total == 0.0

    def test_shear_mode_does_not_measure_from_the_top(self):
        """Which also means a flat pile is still analysed, not excluded."""
        from ogr_core.support import PileMicropile
        assert not PileMicropile().MEASURED_FROM_TOP
        assert PileMicropile(failure_mode="ito_matsui").MEASURED_FROM_TOP

    def test_an_unknown_mode_degrades_to_shear(self):
        """A project written by a newer version must still open.

        Falling back to the mode that needs no soil is the only fallback
        that cannot invent a force.
        """
        from ogr_core.support import PileMicropile
        p = PileMicropile(failure_mode="whatever_comes_next")
        assert not p.NEEDS_BOND_PROFILE
        assert p.force_at(3.0, 5.0) == 50.0


# ======================================================================
class TestTheEquivalentEnvelope:
    """c and φ come from the linearisation the nine methods already use."""

    def test_it_is_the_same_linearisation_bishop_uses(self):
        from ogr_core.materials import HoekBrown, MohrCoulomb
        from ogr_core.support import equivalent_c_phi_at
        from ogr_slip2d.methods.bishop import BishopSimplified
        p = _project(3.0)
        for model in (MohrCoulomb(cohesion=COH, friction_angle=PHI_DEG),
                      HoekBrown()):
            p.materials[0].strength = model
            p.invalidate_regions_cache()
            for sv in (10.0, 60.0, 250.0):
                mine = equivalent_c_phi_at(p, PILE_X, 12.0, sv)
                theirs = BishopSimplified._local_c_phi(
                    None, p.materials[0], sv)
                assert mine == theirs, (model, sv, mine, theirs)

    def test_mohr_coulomb_gives_back_exactly_what_was_typed(self):
        from ogr_core.support import equivalent_c_phi_at
        p = _project(3.0)
        c, tan_phi = equivalent_c_phi_at(p, PILE_X, 12.0, 60.0)
        assert abs(c - COH) < 1e-9
        assert abs(tan_phi - math.tan(math.radians(PHI_DEG))) < 1e-9

    def test_infinite_strength_does_not_become_an_infinite_pile(self):
        from ogr_core.materials import InfiniteStrength
        from ogr_core.support import equivalent_c_phi_at
        p = _project(3.0)
        p.materials[0].strength = InfiniteStrength()
        p.invalidate_regions_cache()
        assert equivalent_c_phi_at(p, PILE_X, 12.0, 60.0) == (0.0, 0.0)


# ======================================================================
class TestSerialisation:
    """Round trips, and files written before this version."""

    def test_round_trip_keeps_the_mode(self):
        from ogr_core.support import PileMicropile, support_from_dict
        a = _pile(force_location="centroid", pile_diameter=1.25)
        b = support_from_dict(a.to_dict())
        assert isinstance(b, PileMicropile)
        assert b.failure_mode == "ito_matsui"
        assert b.pile_diameter == 1.25
        assert b.force_location == "centroid"

    def test_a_file_from_before_this_version_still_opens_as_shear(self):
        """And gives the number it gave then, not a new one.

        The three fields did not exist in 0.1.122, so a project saved by
        it carries none of them.
        """
        from ogr_core.support import support_from_dict
        old = {"type_id": "pile_micropile", "pile_shear_strength": 240.0,
               "out_of_plane_spacing": 3.0}
        p = support_from_dict(old)
        assert p.failure_mode == "shear"
        assert p.force_at(1.0, 5.0) == 80.0
        assert not p.NEEDS_BOND_PROFILE


# ======================================================================
class TestTheModelNotes:
    """What the analysis says about a model outside the theory."""

    def test_a_row_with_no_opening_is_reported(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project(1.0)         # spacing = diameter, no gap at all
        notes = " ".join(settings_warnings(p, ["bishop_simplified"]))
        assert "opening" in notes.lower()
        # And it really does apply no force, rather than a huge one.
        eff, _sl = _effect(p)
        assert eff is None

    def test_a_leaning_pile_is_reported(self):
        from ogr_core.geometry import Vertex
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project(3.0)
        p.supports[0].tail = Vertex(PILE_X + 6.0, PILE_BOT)
        notes = " ".join(settings_warnings(p, ["bishop_simplified"]))
        assert "vertical" in notes.lower()

    def test_a_vertical_pile_in_dry_ground_says_nothing(self):
        """A note that always fires is a note nobody reads."""
        from ogr_slip2d.analysis_runner import settings_warnings
        from ogr_slip2d.ito_matsui_notes import ito_matsui_notes
        p = _project(3.0)
        assert ito_matsui_notes(p, ["bishop_simplified"]) == []
        assert isinstance(settings_warnings(p, ["bishop_simplified"]), list)

    def test_the_location_of_force_note_names_the_blind_methods(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _project(3.0, force_location="centroid")
        notes = " ".join(settings_warnings(
            p, ["bishop_simplified", "janbu_simplified"]))
        assert "janbu_simplified" in notes
        assert "centroid" in notes.lower()
        # And it stays quiet when every method asked for can honour it.
        quiet = " ".join(settings_warnings(p, ["bishop_simplified"]))
        assert "centroid" not in quiet.lower()

    def test_the_note_reaches_a_pile_and_not_only_a_wall(self):
        """The reason it moved out of the retaining wall module.

        Written there, this sentence would have been silent for the second
        type that offers the same control — and nothing would have said so.
        """
        from ogr_slip2d.support_notes import force_location_notes
        assert force_location_notes(
            _project(3.0, force_location="centroid"),
            ["janbu_simplified"])
        assert force_location_notes(_project(3.0), ["janbu_simplified"]) == []


# ======================================================================
class TestTheDialogKnowsWhichComboGoverns:
    """The defect this feature found in the one before it."""

    def test_each_mode_enables_only_the_fields_it_reads(self):
        """Until v0.1.123 the dialog assumed the combo was "profile_type".

        A second type declaring ``PARAMETER_USED_BY`` therefore got a
        combo that greyed out nothing, and four fields editable in both
        modes — the exact defect that block exists to prevent. It did not
        show because only one type declared it.
        """
        from PySide6.QtWidgets import QApplication

        from ogr_core.support import PileMicropile, RetainingWallEFP
        from ogr_gui.dialogs.define_support_dialog import _SupportParamPanel

        # Building a widget without one takes the whole process down with
        # no traceback, which is a long way to find out.
        QApplication.instance() or QApplication([])

        expected = {
            "shear": {"pile_shear_strength", "out_of_plane_spacing"},
            "ito_matsui": {"out_of_plane_spacing", "pile_diameter",
                           "force_location"},
        }
        panel = _SupportParamPanel()
        panel.set_type(PileMicropile, {})
        combo = panel._editors[PileMicropile.MODE_FIELD]
        for mode, used in expected.items():
            idx = [i for i in range(combo.count())
                   if combo.itemData(i) == mode][0]
            combo.setCurrentIndex(idx)
            on = {k for k, e in panel._editors.items()
                  if e.isEnabled() and k != PileMicropile.MODE_FIELD}
            assert on == used, (mode, on)
        # The wall, whose behaviour must be exactly what it was.
        panel2 = _SupportParamPanel()
        panel2.set_type(RetainingWallEFP, {})
        combo2 = panel2._editors[RetainingWallEFP.MODE_FIELD]
        for mode, used in (("uniform", {"pressure", "force_location"}),
                           ("triangular", {"efp", "force_location"})):
            idx = [i for i in range(combo2.count())
                   if combo2.itemData(i) == mode][0]
            combo2.setCurrentIndex(idx)
            on = {k for k, e in panel2._editors.items()
                  if e.isEnabled() and k != RetainingWallEFP.MODE_FIELD}
            assert on == used, (mode, on)
            assert not panel2._table_group.isEnabled()
