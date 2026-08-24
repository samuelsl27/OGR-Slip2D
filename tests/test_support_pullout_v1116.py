# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.116 — the reinforcement pullout laws, and the stress they need.

INVARIANT PROTECTED: the interface friction angle, the coefficient of
interaction and the friction factor all MOVE THE AVAILABLE FORCE, and
they move it by the published amount.

Until v0.1.116 none of them did. ``GroutedTiebackFriction.force_at`` and
``Geosynthetic.force_at`` computed ``tau = self.adhesion`` while their own
docstrings promised ``a + sigma'_n·tan(phi)``, and the other two modes
returned ``parameter * 10.0`` — literal placeholders. The measured
consequence was not a small error but a BINARY answer: with adhesion = 0
the force was 0.000 kN/m at phi = 0 AND at phi = 33.7, and with
adhesion = 20 it was the whole tensile capacity at both angles. Rule 7 of
this project exists for exactly that, and it was broken four times over
in one file.

The anchors here are EXTERNAL (rule 1), never a capture of what the code
prints today:

* a closed form — a horizontal sheet at depth z under level ground in one
  material has sigma'_v = gamma·z exactly, so every mode has an
  arithmetic answer that owes nothing to this implementation;
* a published equation — FHWA-NHI-10-024 (Berg, Christopher and Samtani
  2009) Eq. 3-2, ``P_r = F*·alpha·sigma'_v·L_e·C`` with ``C = 2`` for
  sheets. It independently fixes the factor of two, the use of the
  EFFECTIVE vertical stress, and that the pullout length is the one
  BEHIND the surface — which is what this project got wrong until now,
  taking the shorter of the two sides;
* the two defining limits of the hyperbolic envelope of Esterhuizen, Filz
  and Duncan (2001): slope tan(phi_0) at the origin, asymptote a_inf;
* buoyancy — submerging the column replaces gamma by gamma' exactly;
* and the pre-v0.1.116 numbers themselves, kept as a REGRESSION for the
  one case the old code got right (adhesion alone, where sigma'_n never
  entered), so the fix cannot silently move a model that had no friction
  to begin with.
"""
from __future__ import annotations

import math

import pytest


# ======================================================================
# Shared fixtures — a level, one-material block. sigma'_v = gamma·z.
# ======================================================================
GAMMA = 18.0
GAMMA_SAT = 20.0
Y_TOP = 10.0
Y_SHEET = 4.0
LENGTH = 6.0
SIGMA_V = GAMMA * (Y_TOP - Y_SHEET)          # 108.0 kPa, exactly
COHESION = 5.0
PHI_SOIL = 30.0


def _level_project(gamma=GAMMA, water_y=None, surcharge=None):
    """A 40 x 10 block of one material, optionally submerged or loaded."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(40.0, 0.0),
        Vertex(40.0, Y_TOP), Vertex(0.0, Y_TOP),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("pullout")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Fill", unit_weight=gamma, sat_unit_weight=GAMMA_SAT,
        use_sat_unit_weight=True,
        strength=MohrCoulomb(cohesion=COHESION, friction_angle=PHI_SOIL),
    )]
    if water_y is not None:
        from ogr_core.materials import PorePressureType
        wt = Polyline(vertices=[Vertex(0.0, water_y), Vertex(40.0, water_y)])
        b = Boundary(polyline=wt, btype=BoundaryType.WATER_TABLE)
        p.add_boundary(b)
        # A water table only produces pore pressure for a material that
        # asks it to; leaving the model at NONE would have measured a DRY
        # slope with a line drawn on it.
        p.materials[0].pore_pressure = PorePressureType.WATER_TABLE
        p.materials[0].water_surface_id = b.id
    if surcharge is not None:
        from ogr_core.loads import DistributedLoad, LoadOrientation
        p.distributed_loads.append(DistributedLoad(
            start=Vertex(0.0, Y_TOP), end=Vertex(40.0, Y_TOP),
            magnitude_1=surcharge,
            orientation=LoadOrientation.VERTICAL,
        ))
    return p


def _sheet(y=Y_SHEET, length=LENGTH, x0=10.0):
    from ogr_core.geometry import Vertex
    from ogr_core.support import SupportInstance
    return SupportInstance(type_id="geosynthetic",
                           head=Vertex(x0, y), tail=Vertex(x0 + length, y))


def _geo(**kw):
    """A geosynthetic whose PULLOUT mode governs.

    The tensile capacity and the connection strength are put out of reach
    on purpose: the identities below are about F1, and letting stripping
    or tensile win would test the ``min`` instead of the law.
    """
    from ogr_core.support import Geosynthetic
    kw.setdefault("tensile_capacity", 1.0e9)
    kw.setdefault("connection_strength", 1.0e9)
    return Geosynthetic(**kw)


def _profile(project, stype, support=None):
    from ogr_core.support import build_bond_profile
    return build_bond_profile(project, support or _sheet(), stype)


# ======================================================================
class TestVerticalEffectiveStress:
    """sigma'_v is the number the whole defect was missing."""

    def test_overburden_is_gamma_times_depth(self):
        from ogr_core.support import sigma_v_effective_at
        p = _level_project()
        sv, u, depth = sigma_v_effective_at(p, 12.0, Y_SHEET)
        assert u == 0.0
        assert depth == pytest.approx(Y_TOP - Y_SHEET, abs=1e-12)
        assert sv == pytest.approx(SIGMA_V, abs=1e-9)

    def test_submerging_replaces_gamma_by_gamma_prime(self):
        """Buoyancy, in closed form.

        With the water table at the ground surface the column weighs
        gamma_sat·z and the pore pressure is gamma_w·z, so the effective
        stress is (gamma_sat − gamma_w)·z. Nothing in the support code
        has any say in that, which is what makes it a check.
        """
        from ogr_core.support import sigma_v_effective_at
        p = _level_project(water_y=Y_TOP)
        gamma_w = p.settings.groundwater.pore_fluid_unit_weight
        z = Y_TOP - Y_SHEET
        sv, u, _ = sigma_v_effective_at(p, 12.0, Y_SHEET)
        assert u == pytest.approx(gamma_w * z, abs=1e-9)
        assert sv == pytest.approx((GAMMA_SAT - gamma_w) * z, abs=1e-9)

    def test_a_surcharge_reaches_the_reinforcement(self):
        """Problem 93 of the verification bank is exactly this case."""
        from ogr_core.support import sigma_v_effective_at
        q = 12.0
        base, _, _ = sigma_v_effective_at(_level_project(), 12.0, Y_SHEET)
        loaded, _, _ = sigma_v_effective_at(
            _level_project(surcharge=q), 12.0, Y_SHEET)
        assert loaded - base == pytest.approx(q, abs=1e-9)

    def test_above_ground_there_is_no_overburden(self):
        from ogr_core.support import sigma_v_effective_at
        sv, _, depth = sigma_v_effective_at(_level_project(), 12.0, Y_TOP + 3)
        assert sv == 0.0 and depth == 0.0


# ======================================================================
class TestPublishedPulloutEquation:
    """FHWA-NHI-10-024 Eq. 3-2: P_r = F*·alpha·sigma'_v·L_e·C, C = 2."""

    def test_friction_factor_mode_reproduces_equation_3_2(self):
        p = _level_project()
        for f_star in (0.2, 0.6, 1.0, 1.5):
            g = _geo(pullout_mode="friction_factor", friction_factor=f_star)
            bond = _profile(p, g)
            for d in (0.0, 1.0, 3.0, 4.5, 6.0):
                L_e = LENGTH - d      # embedment BEHIND the surface
                expected = f_star * SIGMA_V * L_e * 2.0
                assert g.force_at(d, LENGTH, bond) == pytest.approx(
                    expected, abs=1e-9), (f_star, d)

    def test_the_two_faces_are_a_factor_of_two_not_a_choice(self):
        """C = 2 because a sheet has two interfaces with the soil.

        Halving the coverage halves the force, which is the OTHER factor
        in the same equation and must not be confused with this one.
        """
        p = _level_project()
        full = _geo(pullout_mode="friction_factor", friction_factor=0.6)
        half = _geo(pullout_mode="friction_factor", friction_factor=0.6,
                    strip_coverage=50.0)
        f_full = full.force_at(2.0, LENGTH, _profile(p, full))
        f_half = half.force_at(2.0, LENGTH, _profile(p, half))
        assert f_full == pytest.approx(
            0.6 * SIGMA_V * 4.0 * 2.0, abs=1e-9)
        assert f_half == pytest.approx(0.5 * f_full, abs=1e-9)


# ======================================================================
class TestClosedFormIdentities:

    def test_linear_envelope_with_no_adhesion(self):
        """F1 = 2·sigma'_v·tan(delta)·L_o, exactly."""
        p = _level_project()
        L_o = 4.0
        for phi in (5.0, 10.0, 20.0, 25.0, 34.0, 45.0):
            g = _geo(pullout_mode="mohr_coulomb", adhesion=0.0,
                     friction_angle_interface=phi)
            expected = 2.0 * SIGMA_V * math.tan(math.radians(phi)) * L_o
            assert g.force_at(LENGTH - L_o, LENGTH,
                              _profile(p, g)) == pytest.approx(
                                  expected, abs=1e-9), phi

    def test_pullout_is_linear_in_embedded_length(self):
        """The identity the defect report asked for, first half.

        With adhesion 0 and a uniform stress the force must fall by the
        same amount for every metre of embedment lost — a straight line,
        not merely a decreasing function.
        """
        p = _level_project()
        g = _geo(pullout_mode="mohr_coulomb", adhesion=0.0,
                 friction_angle_interface=30.0)
        bond = _profile(p, g)
        forces = [g.force_at(d, LENGTH, bond) for d in range(7)]
        steps = [b - a for a, b in zip(forces[:-1], forces[1:])]
        assert all(s == pytest.approx(steps[0], abs=1e-9) for s in steps)
        assert steps[0] < 0.0                      # and it DECREASES
        assert forces[-1] == pytest.approx(0.0, abs=1e-12)

    def test_pullout_is_linear_in_vertical_stress(self):
        """The identity's second half: F1 proportional to sigma'_v."""
        p = _level_project()
        g = _geo(pullout_mode="mohr_coulomb", adhesion=0.0,
                 friction_angle_interface=30.0)
        L_o = 4.0
        for z in (1.0, 2.5, 6.0, 9.0):
            sheet = _sheet(y=Y_TOP - z)
            expected = 2.0 * GAMMA * z * math.tan(math.radians(30.0)) * L_o
            got = g.force_at(LENGTH - L_o, LENGTH, _profile(p, g, sheet))
            assert got == pytest.approx(expected, abs=1e-9), z

    def test_adhesion_and_friction_add(self):
        """The two terms of the envelope are independent and additive."""
        p = _level_project()
        a_only = _geo(pullout_mode="mohr_coulomb", adhesion=7.0,
                      friction_angle_interface=0.0)
        f_only = _geo(pullout_mode="mohr_coulomb", adhesion=0.0,
                      friction_angle_interface=22.0)
        both = _geo(pullout_mode="mohr_coulomb", adhesion=7.0,
                    friction_angle_interface=22.0)
        fa = a_only.force_at(2.0, LENGTH, _profile(p, a_only))
        ff = f_only.force_at(2.0, LENGTH, _profile(p, f_only))
        fb = both.force_at(2.0, LENGTH, _profile(p, both))
        assert fb == pytest.approx(fa + ff, abs=1e-9)


# ======================================================================
class TestCoefficientOfInteraction:
    """tau = Ci · tau_soil — the bond coefficient of Jewell (1996)."""

    def test_ci_one_takes_the_whole_soil_strength(self):
        p = _level_project()
        g = _geo(pullout_mode="coefficient", coefficient_of_interaction=1.0)
        tau_soil = COHESION + SIGMA_V * math.tan(math.radians(PHI_SOIL))
        expected = 2.0 * tau_soil * 4.0
        assert g.force_at(2.0, LENGTH, _profile(p, g)) == pytest.approx(
            expected, abs=1e-9)

    def test_ci_zero_takes_none_of_it(self):
        p = _level_project()
        g = _geo(pullout_mode="coefficient", coefficient_of_interaction=0.0)
        assert g.force_at(2.0, LENGTH, _profile(p, g)) == 0.0

    def test_force_is_proportional_to_ci(self):
        p = _level_project()
        tau_soil = COHESION + SIGMA_V * math.tan(math.radians(PHI_SOIL))
        for ci in (0.2, 0.5, 0.8, 1.0):
            g = _geo(pullout_mode="coefficient",
                     coefficient_of_interaction=ci)
            assert g.force_at(2.0, LENGTH, _profile(p, g)) == pytest.approx(
                2.0 * ci * tau_soil * 4.0, abs=1e-9), ci

    def test_it_reads_the_material_the_sheet_actually_lies_in(self):
        """Ci is a fraction of the SURROUNDING soil, so changing that
        soil must change the interface — that is the whole difference
        between this mode and the Mohr-Coulomb one."""
        from ogr_core.materials import MohrCoulomb
        p = _level_project()
        g = _geo(pullout_mode="coefficient", coefficient_of_interaction=0.8)
        weak = g.force_at(2.0, LENGTH, _profile(p, g))
        p.materials[0].strength = MohrCoulomb(cohesion=COHESION,
                                              friction_angle=40.0)
        p.invalidate_regions_cache()
        strong = g.force_at(2.0, LENGTH, _profile(p, g))
        assert strong > weak * 1.1

    def test_no_project_means_no_soil_to_take_a_fraction_of(self):
        """Zero, not a placeholder. v0.1.115 answered ``Ci * 10.0``."""
        from ogr_core.support import Geosynthetic
        g = Geosynthetic(pullout_mode="coefficient",
                         coefficient_of_interaction=0.8)
        assert g.force_at(2.0, LENGTH) == 0.0


# ======================================================================
class TestHyperbolicEnvelope:
    """Esterhuizen, Filz and Duncan (2001), by its two defining limits."""

    def test_initial_tangent_is_tan_phi_zero(self):
        from ogr_core.support import interface_shear
        a_inf, phi0 = 50.0, 30.0
        s = 1.0e-6
        tau = interface_shear(s, a_inf, phi0, "hyperbolic")
        assert tau / s == pytest.approx(math.tan(math.radians(phi0)),
                                        rel=1e-6)

    def test_asymptote_is_the_adhesion(self):
        from ogr_core.support import interface_shear
        a_inf, phi0 = 50.0, 30.0
        assert interface_shear(1.0e12, a_inf, phi0,
                               "hyperbolic") == pytest.approx(a_inf, rel=1e-6)

    def test_it_never_exceeds_the_linear_envelope(self):
        """The hyperbola is the linear envelope bent over, so it lies
        below tan(phi_0)·sigma at every stress. A user who switches model
        without changing the numbers gets LESS strength, never more."""
        from ogr_core.support import interface_shear
        for s in (1.0, 10.0, 100.0, 1000.0):
            hyp = interface_shear(s, 50.0, 30.0, "hyperbolic")
            lin = s * math.tan(math.radians(30.0))
            assert hyp < lin

    def test_the_model_choice_moves_the_support_force(self):
        p = _level_project()
        lin = _geo(pullout_mode="mohr_coulomb", adhesion=50.0,
                   friction_angle_interface=30.0,
                   shear_strength_model="linear")
        hyp = _geo(pullout_mode="mohr_coulomb", adhesion=50.0,
                   friction_angle_interface=30.0,
                   shear_strength_model="hyperbolic")
        f_lin = lin.force_at(2.0, LENGTH, _profile(p, lin))
        f_hyp = hyp.force_at(2.0, LENGTH, _profile(p, hyp))
        assert f_hyp < f_lin


# ======================================================================
class TestRuleSevenEveryKnobMoves:
    """Rule 7 of this project, applied to every control that was inert."""

    def test_the_pullout_parameter_moves_the_force(self):
        p = _level_project()
        cases = [
            ("mohr_coulomb", "friction_angle_interface",
             [0.0, 10.0, 25.0, 40.0]),
            ("coefficient", "coefficient_of_interaction",
             [0.1, 0.4, 0.7, 1.0]),
            ("friction_factor", "friction_factor", [0.1, 0.4, 0.7, 1.0]),
        ]
        for mode, param, values in cases:
            seen = []
            for v in values:
                g = _geo(pullout_mode=mode, **{param: v})
                seen.append(g.force_at(2.0, LENGTH, _profile(p, g)))
            assert all(b > a
                       for a, b in zip(seen[:-1], seen[1:])), (mode, seen)
            assert seen[-1] > seen[0] * 1.5, (mode, seen)

    def test_grouted_tieback_friction_angle_moves_the_force(self):
        """The other half of the defect, in the other class."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import (GroutedTiebackFriction,
                                      SupportInstance, build_bond_profile)
        p = _level_project()
        anchor = SupportInstance(
            type_id="grouted_tieback_friction",
            head=Vertex(10.0, Y_SHEET), tail=Vertex(10.0 + LENGTH, Y_SHEET))
        seen = []
        for phi in (0.0, 10.0, 25.0, 40.0):
            s = GroutedTiebackFriction(
                adhesion=0.0, friction_angle_bond=phi,
                bond_length_percent=100.0, grout_diameter=0.30,
                out_of_plane_spacing=1.5, tensile_capacity=1.0e9,
                plate_capacity=1.0e9)
            seen.append(s.force_at(2.0, LENGTH,
                                   build_bond_profile(p, anchor, s)))
        assert seen[0] == 0.0
        assert all(b > a for a, b in zip(seen[:-1], seen[1:])), seen

    def test_strip_coverage_moves_the_force(self):
        p = _level_project()
        seen = []
        for a in (25.0, 50.0, 100.0):
            g = _geo(pullout_mode="friction_factor", friction_factor=0.6,
                     strip_coverage=a)
            seen.append(g.force_at(2.0, LENGTH, _profile(p, g)))
        assert seen[1] == pytest.approx(2.0 * seen[0], abs=1e-9)
        assert seen[2] == pytest.approx(4.0 * seen[0], abs=1e-9)

    def test_connection_strength_moves_the_force_at_the_head(self):
        """It IS the force at the head of the diagram."""
        from ogr_core.support import Geosynthetic
        p = _level_project()
        for c in (0.0, 5.0, 12.5):
            g = Geosynthetic(pullout_mode="friction_factor",
                             friction_factor=0.6, tensile_capacity=1.0e9,
                             connection_strength=c)
            assert g.force_at(0.0, LENGTH,
                              _profile(p, g)) == pytest.approx(c, abs=1e-9)

    def test_anchorage_moves_the_force(self):
        """An anchored embedded end removes pullout as a mode."""
        from ogr_core.support import Geosynthetic
        p = _level_project()
        kw = dict(pullout_mode="friction_factor", friction_factor=0.6,
                  tensile_capacity=1.0e9, connection_strength=1.0e9)
        free = Geosynthetic(anchorage="none", **kw)
        held = Geosynthetic(anchorage="embedded_end", **kw)
        # At the very tail there is no embedment left, so a free end can
        # carry nothing and an anchored one carries what the sheet can.
        assert free.force_at(LENGTH, LENGTH, _profile(p, free)) == 0.0
        assert held.force_at(LENGTH, LENGTH, _profile(p, held)) > 0.0

    def test_reference_elevation_is_no_longer_inert(self):
        """v0.1.116 — a SECOND dead control found next to the first.

        ``reference_elevation`` was declared, editable and serialised
        since v0.1.14 and read by nobody. It is now the datum of the
        F*(depth) function, and the test that proves it is that moving
        the datum moves the number.
        """
        p = _level_project()
        common = dict(pullout_mode="friction_factor",
                      friction_factor_mode="function",
                      friction_factor=0.2, reference_depth=10.0,
                      friction_factor_at_depth=1.2)
        at_top = _geo(reference_elevation=Y_TOP, **common)
        higher = _geo(reference_elevation=Y_TOP + 5.0, **common)
        f_top = at_top.force_at(2.0, LENGTH, _profile(p, at_top))
        f_high = higher.force_at(2.0, LENGTH, _profile(p, higher))
        assert f_high > f_top          # deeper below the datum ⇒ larger F*

    def test_friction_factor_function_interpolates_linearly(self):
        """F* between its two published points, constant outside."""
        p = _level_project()
        g = _geo(pullout_mode="friction_factor",
                 friction_factor_mode="function",
                 friction_factor=0.2, reference_elevation=Y_TOP,
                 reference_depth=6.0, friction_factor_at_depth=0.8)
        # The sheet sits 6 m below the datum: F* is at its second value.
        got = g.force_at(2.0, LENGTH, _profile(p, g))
        assert got == pytest.approx(0.8 * SIGMA_V * 4.0 * 2.0, abs=1e-9)
        # Halfway down, F* is halfway between the two.
        sheet_mid = _sheet(y=Y_TOP - 3.0)
        g2 = _geo(pullout_mode="friction_factor",
                  friction_factor_mode="function",
                  friction_factor=0.2, reference_elevation=Y_TOP,
                  reference_depth=6.0, friction_factor_at_depth=0.8)
        got2 = g2.force_at(2.0, LENGTH, _profile(p, g2, sheet_mid))
        assert got2 == pytest.approx(0.5 * GAMMA * 3.0 * 4.0 * 2.0, abs=1e-9)


# ======================================================================
class TestForceDiagramShape:
    """The published diagram: stripping up, tensile flat, pullout down."""

    def test_force_is_continuous_along_the_support(self):
        """No step where a trial surface crosses a sample point.

        The profile is sampled at 50 points; if ``integral`` snapped to
        segment boundaries instead of interpolating inside them, the
        available force would jump every L/50 metres and a search would
        see 50 little cliffs. The bound is the largest change the law
        itself can produce over one step.
        """
        p = _level_project()
        g = _geo(pullout_mode="friction_factor", friction_factor=0.6,
                 connection_strength=0.0)
        bond = _profile(p, g)
        n = 997                        # deliberately not a multiple of 50
        step = LENGTH / n
        prev = g.force_at(0.0, LENGTH, bond)
        worst = 0.0
        for i in range(1, n + 1):
            cur = g.force_at(i * step, LENGTH, bond)
            worst = max(worst, abs(cur - prev))
            prev = cur
        # Two faces, uniform tau: |dF/ds| = 2·tau, so one step can move
        # the force by at most 2·tau·step plus rounding.
        bound = 2.0 * 0.6 * SIGMA_V * step * 1.000001
        assert worst <= bound, (worst, bound)

    def test_the_diagram_rises_then_falls(self):
        from ogr_core.support import Geosynthetic
        p = _level_project()
        g = Geosynthetic(pullout_mode="friction_factor", friction_factor=0.6,
                         tensile_capacity=200.0, connection_strength=10.0)
        bond = _profile(p, g)
        xs = [i * LENGTH / 60 for i in range(61)]
        fs = [g.force_at(x, LENGTH, bond) for x in xs]
        peak = max(range(len(fs)), key=lambda i: fs[i])
        assert 0 < peak < len(fs) - 1
        assert fs[0] == pytest.approx(10.0, abs=1e-9)      # connection
        assert fs[-1] == pytest.approx(0.0, abs=1e-9)      # nothing left
        assert max(fs) <= 200.0 + 1e-9                     # tensile caps it

    def test_tensile_capacity_caps_the_whole_diagram(self):
        from ogr_core.support import Geosynthetic
        p = _level_project()
        g = Geosynthetic(pullout_mode="friction_factor", friction_factor=5.0,
                         tensile_capacity=25.0, connection_strength=1.0e9)
        bond = _profile(p, g)
        assert all(g.force_at(x * 0.1, LENGTH, bond) <= 25.0 + 1e-9
                   for x in range(61))

    def test_halving_the_sampling_step_does_not_move_the_answer(self):
        """50 segments is a discretisation, so it has to be shown not to
        matter — otherwise the published factors would depend on it."""
        from ogr_core.support import build_bond_profile
        p = _level_project()
        g = _geo(pullout_mode="coefficient", coefficient_of_interaction=0.8)
        sheet = _sheet()
        coarse = build_bond_profile(p, sheet, g, segments=25)
        fine = build_bond_profile(p, sheet, g, segments=200)
        for d in (0.5, 2.0, 4.0, 5.5):
            assert g.force_at(d, LENGTH, coarse) == pytest.approx(
                g.force_at(d, LENGTH, fine), rel=1e-9)


# ======================================================================
class TestBackwardCompatibility:
    """The one case the old code got right must not move."""

    def test_adhesion_only_reproduces_v0_1_115(self):
        """Measured on 0.1.115 before the change, with the geosynthetic
        of verification problem 30 (Borges and Cardoso 2002): tensile
        200 kN/m, not anchored. sigma'_n never entered this answer, so
        the fix must leave it alone to the last bit."""
        from ogr_core.support import Geosynthetic
        g = Geosynthetic(tensile_capacity=200.0, adhesion=20.0,
                         friction_angle_interface=33.7)
        assert g.force_at(14.7, 28.0) == 200.0
        g0 = Geosynthetic(tensile_capacity=200.0, adhesion=0.0,
                          friction_angle_interface=33.7)
        assert g0.force_at(14.7, 28.0) == 0.0

    def test_tieback_adhesion_only_reproduces_v0_1_115(self):
        from ogr_core.support import GroutedTiebackFriction
        s = GroutedTiebackFriction(adhesion=20.0, friction_angle_bond=33.7,
                                   out_of_plane_spacing=3.0)
        assert s.force_at(14.7, 28.0) == pytest.approx(26.38937829015426,
                                                       rel=1e-12)

    def test_new_parameters_survive_a_round_trip(self):
        from ogr_core.support import Geosynthetic, support_from_dict
        g = Geosynthetic(strip_coverage=67.0, connection_strength=8.0,
                         anchorage="slope_face",
                         shear_strength_model="hyperbolic",
                         friction_factor_mode="function",
                         reference_depth=4.0, friction_factor_at_depth=0.9)
        back = support_from_dict(g.to_dict())
        assert back.strip_coverage == 67.0
        assert back.connection_strength == 8.0
        assert back.anchorage == "slope_face"
        assert back.shear_strength_model == "hyperbolic"
        assert back.friction_factor_mode == "function"
        assert back.reference_depth == 4.0
        assert back.friction_factor_at_depth == 0.9

    def test_an_old_file_without_the_new_keys_still_loads(self):
        """A .ogr written before v0.1.116 carries none of them."""
        from ogr_core.support import support_from_dict
        old = {"type_id": "geosynthetic", "tensile_capacity": 50.0,
               "pullout_mode": "mohr_coulomb", "adhesion": 10.0,
               "friction_angle_interface": 25.0,
               "coefficient_of_interaction": 0.8, "friction_factor": 0.6,
               "reference_elevation": 0.0}
        g = support_from_dict(old)
        assert g.strip_coverage == 100.0 and g.anchorage == "none"
        assert g.force_at(1.0, 10.0) == 20.0     # the v0.1.14 number


# ======================================================================
class TestBondProfile:

    def test_integral_of_a_uniform_profile_is_tau_times_length(self):
        from ogr_core.support import BondProfile
        bp = BondProfile.uniform(7.0, 10.0)
        assert bp.integral(0.0, 10.0) == pytest.approx(70.0, abs=1e-12)
        assert bp.integral(2.0, 5.0) == pytest.approx(21.0, abs=1e-12)
        assert bp.integral(5.0, 2.0) == pytest.approx(21.0, abs=1e-12)

    def test_integral_is_additive_over_a_split(self):
        from ogr_core.support import BondProfile
        bp = BondProfile.from_samples([1.0, 4.0, 9.0, 16.0], 8.0)
        whole = bp.integral(0.0, 8.0)
        for cut in (0.3, 2.0, 4.7, 6.0):
            assert bp.integral(0.0, cut) + bp.integral(
                cut, 8.0) == pytest.approx(whole, abs=1e-12)

    def test_limits_are_clamped_to_the_support(self):
        from ogr_core.support import BondProfile
        bp = BondProfile.uniform(3.0, 5.0)
        assert bp.integral(-10.0, 100.0) == pytest.approx(15.0, abs=1e-12)
        assert bp.integral(7.0, 9.0) == 0.0

    def test_a_zero_length_support_has_no_bond(self):
        from ogr_core.support import BondProfile
        bp = BondProfile.uniform(3.0, 0.0)
        assert bp.integral(0.0, 1.0) == 0.0 and bp.total == 0.0

    def test_types_that_do_not_need_it_do_not_pay_for_it(self):
        """Building a 50-sample profile for a constant-force bolt would
        cost a search real time for a number nobody reads."""
        from ogr_core.support import (EndAnchored, SoilNail,
                                      build_bond_profile)
        p = _level_project()
        for stype in (EndAnchored(), SoilNail()):
            assert not stype.NEEDS_BOND_PROFILE
            assert build_bond_profile(p, _sheet(), stype).total == 0.0

    def test_infinite_strength_does_not_leak_into_the_interface(self):
        """Rigid bedrock is a modelling device, not an unpullable sheet.

        An infinity here would silently delete the pullout mode from the
        minimum, which is the unsafe direction.
        """
        from ogr_core.materials import InfiniteStrength
        p = _level_project()
        p.materials[0].strength = InfiniteStrength()
        p.invalidate_regions_cache()
        g = _geo(pullout_mode="coefficient", coefficient_of_interaction=0.8)
        f = g.force_at(2.0, LENGTH, _profile(p, g))
        assert math.isfinite(f)


# ======================================================================
class TestAnalysisLevel:
    """Rule 7 where it actually matters: the factor of safety."""

    def test_interface_friction_raises_the_factor_of_safety(self):
        """The knob has to move the ANSWER, not just a helper function.

        A frictionless interface can develop no pullout resistance, so
        the sheets carry nothing and the slope is bare. Giving the
        interface friction lets them carry load, and the factor rises.
        """
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      Geosynthetic, SupportInstance)
        from ogr_slip2d import BishopSimplified, GridSearch

        H, toe = 12.0, 30.0
        crest = toe + H / math.tan(math.radians(30.96))
        ext = Polyline(vertices=[
            Vertex(0, -10), Vertex(60, -10), Vertex(60, H),
            Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
        ], closed=True)
        ext.ensure_ccw()

        def build(phi_int):
            p = Project("reinforced")
            p.add_boundary(Boundary(polyline=ext,
                                    btype=BoundaryType.EXTERNAL))
            p.materials = [Material(
                name="S", unit_weight=18.0,
                strength=MohrCoulomb(cohesion=5.0, friction_angle=20.0))]
            sheet = Geosynthetic(
                tensile_capacity=120.0, pullout_mode="mohr_coulomb",
                adhesion=0.0, friction_angle_interface=phi_int,
                connection_strength=120.0)
            p.support_types = [sheet]
            for i in range(5):
                frac = (i + 0.5) / 5.0
                hx = toe + frac * (crest - toe)
                hy = frac * H
                p.supports.append(SupportInstance(
                    type_id="geosynthetic",
                    head=Vertex(hx, hy), tail=Vertex(hx + 10.0, hy),
                    force_application=ForceApplication.PASSIVE,
                    orientation=ForceOrientation.PARALLEL_TO_SUPPORT))
            return p

        search = GridSearch(
            method=BishopSimplified(), grid_x=(20, 60), grid_y=(15, 35),
            grid_nx=6, grid_ny=6, radius_increment=2.0, min_radius=8.0,
            num_slices=25, min_area=0.5)
        fos_none = search.run(build(0.0)).critical.fos
        fos_some = search.run(build(30.0)).critical.fos
        assert fos_some > fos_none * 1.02, (fos_none, fos_some)

    def test_the_bond_cache_is_dropped_when_the_freeze_starts(self):
        """A profile must not outlive an edit made between two runs.

        The cache has no cheap signature of its own — it depends on the
        boundaries, the materials, the water and the loads at once — so
        correctness rests on it being cleared here. If it were not, a
        model edited between two analyses would be analysed with the
        stresses of the first.
        """
        p = _level_project()
        p._support_bond_cache = {"stale": object()}
        with p.regions_frozen():
            assert p._support_bond_cache is None
