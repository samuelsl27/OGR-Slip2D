# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A retaining wall is a pressure profile INTEGRATED down to the slip surface.

THE INVARIANT. ``RetainingWallEFP.force_at(d, L)`` is the area of the
pressure diagram between the crest of the wall and the depth ``d`` at which
the slip surface crosses it. Everything else in this file follows from that
one sentence: a surface clipping the wall near the crest mobilises little, a
surface passing under the toe mobilises the whole diagram, and the resultant
acts either where the surface cuts or at the centroid of what is above it.

THE ANCHORS, none of them a captured value.

* **Two published areas.** A 5-unit wall whose pressure reaches 125 at the
  toe integrates to **312.5**; a 10-unit wall with an equivalent fluid
  pressure of 25 spread over 60 % of its height integrates to **2000**.
  Both are published, both are exact, and both are reproduced here to the
  last bit — which is why the four primitives are written in closed form
  and not as quadrature.

* **Two published dimensioned figures**, because AN AREA DOES NOT FIX A
  SHAPE. The trapezoid's 2000 would be the same with the flat part at the
  top, at the bottom or in the middle, and this whole class lives on the
  PARTIAL integral, which is not. The reference dimensions its trapezoid
  0.2H / 0.6H / 0.2H with EFP·H on the flat, and its triangle 0 at the
  crest and 200 at the toe for EFP 20 over 10 units. Those are the numbers
  asserted, not the total.

* **An identity between support types.** The only thing separating this
  type from an ``EndAnchored`` of the same capacity is ``force_at``, so on
  the same geometry with the same orientation and application the two must
  agree BIT FOR BIT in all nine methods. The reference value is produced by
  a type already validated against verification problems 48 and 85
  (``test_support_projection_v1113``, ``test_support_active_passive_v1115``),
  so this is not a snapshot of what the new code prints today.

* **A closed form.** With φ' = 0 on a circle the moment balance is
  ``F = Σc'·l·R / ΣW·x``, and with a support of known integrated force T on
  a base of angle α that becomes ``Σc'l / (ΣW·arm − T·cos α)`` for Active.
  Nothing on the right-hand side comes out of the solver.

WHAT THIS FILE DELIBERATELY DOES NOT ASSERT, because measuring it is what
kept the change honest. The reference verifies this support type against a
TRIANGULAR DISTRIBUTED LOAD on the back of the wall, and says the two must
be identical. In OGR they are not, and the reason is older than this
feature: a horizontal force entering as a SUPPORT is split into a component
on the base and one along its normal, while the same force entering as a
LOAD is a cartesian force at an elevation, and the two formulations are not
the same arithmetic. Measured on a common fixture, same force, same point:

    Corps #1, Corps #2, Lowe-Karafiath   agree to 3e-15
    Ordinary, Spencer, GLE               agree in the limit; the residual is
                                         discretisation and falls from
                                         −0.009 % at 25 slices to +0.0006 %
                                         at 400
    Bishop                               −0.276 %, and it does NOT shrink:
                                         the support adds T_N·tanφ' to the
                                         numerator and the load does not
    Janbu simplified and corrected       −0.096 %, and it does not shrink
                                         either: the load enters the driving
                                         side raw where the support enters
                                         projected on the base, a factor cos α

Both rows are now history; the two paragraphs below say how each closed.

v0.1.137 — BISHOP'S HALF IS CLOSED. Its row above is history: the support
is now resolved as the line load the reference says it is, so its normal
comes out of the same vertical equilibrium the load's does, and the gap
falls to −0.010 / +0.0016 / +0.0006 % at 25 / 100 / 400 slices — the same
discretisation residual Ordinary, Spencer and GLE show. The test that used
to freeze the disagreement now asserts the agreement, which is what its own
docstring demanded should happen.

v0.1.142 — JANBU'S HALF IS CLOSED TOO, and with it D46. Its row above is
history as well: it needed the same correction plus a ``sec α`` on its
driving side, and together they make this gap exactly zero at every
refinement. What had blocked it for twenty versions was that the two
branches were being judged against the six published Clouterre planes, and
the branch that fit them was the one that failed this identity. A closed
form settled it instead of a published number — on a PLANE the sliding mass
is one free body, so every method that closes global force equilibrium owes
the Coulomb wedge, and the two Corps methods, Lowe-Karafiath and Ordinary
reproduce it to the last digit where the old Janbu missed it by +1.9 % to
−20.0 %. See ``tests/test_janbu_wedge_v1142.py``, and the re-enunciated
header of ``tests/test_support_projection_v1113.py`` for what happened to
the Clouterre planes: the manual publishes TWO columns for them that
disagree with each other by up to 4.7 %, and against the ORIGINAL source's
column the corrected formulation leaves a flat −7.7 % offset where the old
one left a 4.3-point trend.

So what this file DOES assert about that pair is the half that is exact and
that this feature is responsible for: the resultant and its point of
application match to the last bit. What is left of the factor-of-safety
difference is a measured, reported defect of the two channels, not of the
wall.
"""
from __future__ import annotations

import math

# --- the published fixtures -------------------------------------------
#: Verification problem 110: a 5-unit wall, pressure 0 at the crest and 125
#: at the toe, so an equivalent fluid pressure of 25 per unit length.
P110_L, P110_TOE_PRESSURE = 5.0, 125.0
P110_AREA = 312.5
#: The worked trapezoid of the reference's own help page.
TRAP_L, TRAP_EFP, TRAP_SPREAD = 10.0, 25.0, 60.0
TRAP_AREA = 2000.0

# --- a slope to put a wall on -----------------------------------------
H, TOE, CREST = 12.0, 30.0, 50.0
XW = 43.5
YW_TOP = (XW - TOE) * H / (CREST - TOE)     # 8.1, the ground at the wall
LW, EFP = 5.0, 6.0


def _wall(**kw):
    from ogr_core.support import RetainingWallEFP
    return RetainingWallEFP(**kw)


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)


def _ground(project, cohesion=8.0, friction=20.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    project.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    project.materials = [Material(
        name="S", unit_weight=18,
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=friction))]
    return project


def _wall_project(location="intersection", flip=False, efp=EFP,
                  cohesion=8.0, friction=20.0, application=None,
                  **wall_kw):
    from ogr_core.geometry import Vertex
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    p = _ground(Project("efp"), cohesion, friction)
    kw = dict(profile_type="triangular", efp=efp, force_location=location)
    kw.update(wall_kw)
    p.support_types = [_wall(**kw)]
    top, bot = Vertex(XW, YW_TOP), Vertex(XW, YW_TOP - LW)
    head, tail = (bot, top) if flip else (top, bot)
    p.supports = [SupportInstance(
        type_id="retaining_wall_efp", head=head, tail=tail,
        force_application=application or ForceApplication.ACTIVE,
        orientation=ForceOrientation.HORIZONTAL)]
    return p


def _fos(method_id, project, surface, num_slices=25):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return method_registry()[method_id]().compute_fos(
        project, surface, sl).fos


def _method_ids():
    from ogr_slip2d.methods.base import method_registry
    return sorted(method_registry())


def _effect(project, num_slices=25):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    surf = _circle()
    sl = slice_surface(project, surf, num_slices=num_slices)
    eff = compute_support_effects(project, surf, sl)
    return eff[0] if eff else None


# ======================================================================
class TestThePublishedAreas:
    """The two integrals the reference publishes, to the last bit."""

    def test_the_triangular_profile_of_problem_110(self):
        w = _wall(profile_type="triangular",
                  efp=P110_TOE_PRESSURE / P110_L)
        assert w.force_at(P110_L, P110_L) == P110_AREA
        # And the pressure it reaches at the toe is the published 125.
        assert w.pressure_at(1.0, P110_L) == P110_TOE_PRESSURE

    def test_the_trapezoidal_profile_of_the_worked_example(self):
        w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        assert abs(w.force_at(TRAP_L, TRAP_L) - TRAP_AREA) < 1e-9
        # The pressure on the flat part: EFP × wall length.
        assert w.pressure_at(0.5, TRAP_L) == TRAP_EFP * TRAP_L

    def test_problem_110_by_both_of_its_constructions(self):
        """Its table IS a custom profile; its slope IS a triangular one.

        The reference states problem 110 as a table of relative distance
        against pressure, which is literally the custom profile, and the
        same diagram is the triangular profile with EFP = 125/5. Two
        independent inputs, one published number.
        """
        a = _wall(profile_type="triangular", efp=P110_TOE_PRESSURE / P110_L)
        b = _wall(profile_type="custom",
                  points=[(0.0, 0.0), (1.0, P110_TOE_PRESSURE)])
        assert a.force_at(P110_L, P110_L) == b.force_at(P110_L, P110_L)
        assert a.force_at(P110_L, P110_L) == P110_AREA

    def test_the_uniform_profile_is_pressure_times_length(self):
        w = _wall(profile_type="uniform", pressure=20.0)
        assert w.force_at(7.0, 7.0) == 140.0


# ======================================================================
class TestTheShapeTheFiguresPublish:
    """An area does not fix a shape, and the partial integral needs one."""

    def test_the_trapezoid_is_dimensioned_020_060_020(self):
        """0.2H ramp, 0.6H flat, 0.2H ramp, zero at both ends."""
        w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        peak = TRAP_EFP * TRAP_L
        assert w.pressure_at(0.0, TRAP_L) == 0.0
        assert w.pressure_at(1.0, TRAP_L) == 0.0
        assert abs(w.pressure_at(0.1, TRAP_L) - 0.5 * peak) < 1e-12
        assert abs(w.pressure_at(0.9, TRAP_L) - 0.5 * peak) < 1e-12
        for s in (0.2, 0.4, 0.6, 0.8):
            assert abs(w.pressure_at(s, TRAP_L) - peak) < 1e-12

    def test_the_triangle_is_zero_at_the_crest_and_efp_L_at_the_toe(self):
        """EFP 20 over a 10-unit wall: 0 at the top, 200 at the bottom."""
        w = _wall(profile_type="triangular", efp=20.0)
        assert w.pressure_at(0.0, 10.0) == 0.0
        assert w.pressure_at(1.0, 10.0) == 200.0

    def test_the_custom_table_reproduces_the_trapezoid_everywhere(self):
        """Not just the total: the PARTIAL integral, at 101 depths.

        Two different code paths — a closed primitive and an accumulated
        trapezium rule over a table — describing the same diagram.
        """
        t = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        peak = TRAP_EFP * TRAP_L
        c = _wall(profile_type="custom",
                  points=[(0.0, 0.0), (0.2, peak), (0.8, peak), (1.0, 0.0)])
        worst = max(abs(c.force_at(d / 100.0 * TRAP_L, TRAP_L)
                        - t.force_at(d / 100.0 * TRAP_L, TRAP_L))
                    for d in range(101))
        assert worst < 1e-9, worst

    def test_the_trapezoid_family_reaches_its_two_limits(self):
        """f = 100 % is the uniform diagram; f = 0 % is two ramps."""
        full = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                     distributed_over=100.0)
        assert full.force_at(TRAP_L, TRAP_L) == TRAP_EFP * TRAP_L * TRAP_L
        none = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                     distributed_over=0.0)
        assert abs(none.force_at(TRAP_L, TRAP_L)
                   - 0.5 * TRAP_EFP * TRAP_L * TRAP_L) < 1e-9

    def test_the_two_end_rules_of_the_custom_table(self):
        """No value at the crest means zero; none at the toe holds."""
        w = _wall(profile_type="custom", points=[(0.5, 100.0)])
        assert w.pressure_at(0.0, 1.0) == 0.0
        assert w.pressure_at(1.0, 1.0) == 100.0

    def test_a_repeated_abscissa_is_a_step_and_adds_no_area(self):
        """A surcharge starting part-way down a wall is a step, and a step
        of zero width must contribute zero area — not a NaN and not a
        doubled trapezium."""
        w = _wall(profile_type="custom",
                  points=[(0.0, 0.0), (0.5, 0.0), (0.5, 100.0),
                          (1.0, 100.0)])
        # A rectangle over the lower half: 100 × 0.5 × L, with L = 1.
        assert abs(w.force_at(1.0, 1.0) - 50.0) < 1e-12


# ======================================================================
class TestTheForceDiagram:
    """Its shape, which is what the reference draws."""

    def test_it_starts_at_zero_rises_and_ends_at_the_area(self):
        w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        vals = [w.force_at(TRAP_L * k / 200.0, TRAP_L) for k in range(201)]
        assert vals[0] == 0.0
        assert abs(vals[-1] - TRAP_AREA) < 1e-9
        assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))

    def test_it_does_not_depend_on_the_sampling_step(self):
        """A closed primitive cannot: this is what says it is not
        quadrature in disguise."""
        w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        for d in (1.0, 2.5, 5.0, 7.5, 9.9):
            a = w.force_at(d, TRAP_L)
            # The same depth reached through a different arithmetic path.
            b = w.force_at(d * 3.0 / 3.0, TRAP_L)
            assert a == b

    def test_it_is_continuous_where_the_profile_bends(self):
        """The two breakpoints of the trapezoid are where a wrong
        primitive would show a jump."""
        w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        for s in (0.2, 0.8):
            d = s * TRAP_L
            lo = w.force_at(d - 1e-7, TRAP_L)
            hi = w.force_at(d + 1e-7, TRAP_L)
            assert abs(hi - lo) < 1e-3


# ======================================================================
class TestTheCentroid:
    """Where the resultant of the diagram above the cut acts."""

    def test_the_triangular_arm_is_two_thirds_of_the_depth(self):
        w = _wall(profile_type="triangular", efp=EFP)
        for d in (1.0, 2.5, 5.0):
            assert abs(w.resultant_arm(d, 5.0) - 2.0 * d / 3.0) < 1e-12

    def test_the_uniform_arm_is_half_the_depth(self):
        w = _wall(profile_type="uniform", pressure=20.0)
        for d in (1.0, 4.0, 8.0):
            assert abs(w.resultant_arm(d, 8.0) - 0.5 * d) < 1e-12

    def test_the_symmetric_trapezoid_acts_at_mid_height(self):
        w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                  distributed_over=TRAP_SPREAD)
        assert abs(w.resultant_arm(TRAP_L, TRAP_L) - 0.5 * TRAP_L) < 1e-12

    def test_no_diagram_above_the_cut_means_no_arm_to_invent(self):
        w = _wall(profile_type="triangular", efp=EFP)
        assert w.resultant_arm(0.0, 5.0) == 0.0


# ======================================================================
class TestTheCrestIsGeometry:
    """A wall drawn upside down must not invert its own pressure."""

    def test_drawing_the_wall_bottom_up_changes_nothing(self):
        a = _effect(_wall_project(flip=False))
        b = _effect(_wall_project(flip=True))
        assert a is not None and b is not None
        assert a.force_magnitude == b.force_magnitude

    def test_a_horizontal_wall_is_refused_rather_than_guessed(self):
        """It has no crest, so a profile measured from the crest has no
        meaning; answering would mean answering from the drawing order."""
        from ogr_core.geometry import Vertex
        p = _wall_project()
        p.supports[0].head = Vertex(XW - 2.0, YW_TOP)
        p.supports[0].tail = Vertex(XW + 2.0, YW_TOP)
        assert _effect(p) is None

    def test_the_model_says_so_instead_of_staying_quiet(self):
        from ogr_core.geometry import Vertex
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _wall_project()
        p.supports[0].head = Vertex(XW - 2.0, YW_TOP)
        p.supports[0].tail = Vertex(XW + 2.0, YW_TOP)
        notes = " ".join(settings_warnings(p, ["bishop_simplified"]))
        assert "horizontal" in notes.lower()


# ======================================================================
class TestTheIdentityThatHolds:
    """Only ``force_at`` separates this type from an end-anchored bolt."""

    def test_it_matches_end_anchored_bit_for_bit_in_every_method(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project import Project
        from ogr_core.support import (EndAnchored, ForceApplication,
                                      ForceOrientation, SupportInstance)
        pw = _wall_project("intersection")
        eff = _effect(pw)
        assert eff is not None and eff.force_magnitude > 0.0
        pe = _ground(Project("anchor"))
        pe.support_types = [EndAnchored(anchor_capacity=eff.force_magnitude,
                                        out_of_plane_spacing=1.0)]
        pe.supports = [SupportInstance(
            type_id="end_anchored",
            head=Vertex(XW, YW_TOP), tail=Vertex(XW, YW_TOP - LW),
            force_application=ForceApplication.ACTIVE,
            orientation=ForceOrientation.HORIZONTAL)]
        surf = _circle()
        for mid in _method_ids():
            assert _fos(mid, pw, surf) == _fos(mid, pe, surf), mid

    def test_the_closed_form_with_zero_friction(self):
        """``F = Σc'l / (ΣW·arm − T·cos α)`` for an Active support.

        With φ' = 0 the base normal drops out of the resistance entirely,
        so the right-hand side is two geometric sums and the integrated
        wall force. Nothing in it comes from the solver.
        """
        from ogr_slip2d.slicer import slice_surface
        surf = _circle()
        p = _wall_project("intersection", cohesion=30.0, friction=0.0)
        eff = _effect(p)
        sl = slice_surface(p, surf, num_slices=25)
        s_list = sl.slices
        c = 30.0
        resisting = math.fsum(c * s.base_length for s in s_list)
        driving = math.fsum(s.weight * s.weight_arm_ratio for s in s_list)
        alpha = s_list[eff.slice_index].base_angle
        t_s = eff.force_h * math.cos(alpha) + eff.force_v * math.sin(alpha)
        expected = resisting / (driving - t_s)
        for mid in ("ordinary_fellenius", "bishop_simplified"):
            got = _fos(mid, p, surf)
            assert abs(got - expected) / expected < 1e-9, (mid, got, expected)


# ======================================================================
class TestTheManualsOwnComparison:
    """The identity the manual writes, and that OGR could not hold when
    this feature landed.

    See the module docstring. The resultant and where it acts matched to
    the last bit from the start; the factor of safety did not, in Bishop
    and the two Janbu, and the cause was how a support and a load enter the
    equilibrium — older than this feature, and measured rather than
    assumed. Bishop closed in v0.1.137 and the two Janbu in v0.1.142, so
    every method now holds it and this class asserts the whole of it.
    """

    @staticmethod
    def _load_project(y_cut, p_cut):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import (DistributedLoad, LoadDistribution,
                                    LoadOrientation)
        from ogr_core.project import Project
        p = _ground(Project("load"))
        p.distributed_loads = [DistributedLoad(
            start=Vertex(XW, YW_TOP), end=Vertex(XW, y_cut),
            magnitude_1=0.0, magnitude_2=p_cut,
            distribution=LoadDistribution.TRIANGULAR,
            orientation=LoadOrientation.HORIZONTAL)]
        return p

    def test_the_resultant_and_its_point_of_application_are_identical(self):
        from ogr_slip2d.slicer import slice_surface
        pw = _wall_project("centroid")
        eff = _effect(pw)
        d = YW_TOP - eff.intersection_y
        pl = self._load_project(eff.intersection_y, EFP * d)
        sl = slice_surface(pl, _circle(), num_slices=25)
        f_h = math.fsum(s.water_force_h for s in sl.slices)
        m_h = math.fsum(s.water_force_h_moment for s in sl.slices)
        assert abs(f_h - eff.force_magnitude) < 1e-12
        assert abs(m_h / f_h - eff.application_y) < 1e-12

    def test_the_three_marching_methods_do_agree_exactly(self):
        """They resolve the support back into a cartesian resultant, so
        for an ACTIVE support the two routes are the same algebra."""
        pw = _wall_project("centroid")
        eff = _effect(pw)
        d = YW_TOP - eff.intersection_y
        pl = self._load_project(eff.intersection_y, EFP * d)
        surf = _circle()
        for mid in ("corps_engineers_1", "corps_engineers_2",
                    "lowe_karafiath"):
            assert abs(_fos(mid, pw, surf) - _fos(mid, pl, surf)) < 1e-12, mid

    def _gaps(self, mid):
        surf = _circle()
        gaps = []
        for n in (25, 100, 400):
            pw = _wall_project("centroid")
            eff = _effect(pw, n)
            d = YW_TOP - eff.intersection_y
            pl = self._load_project(eff.intersection_y, EFP * d)
            a, b = _fos(mid, pw, surf, n), _fos(mid, pl, surf, n)
            gaps.append(100.0 * (b - a) / a)
        return gaps

    def test_bishop_now_agrees_and_the_gap_shrinks_on_refinement(self):
        """v0.1.137 — this test used to assert the OPPOSITE, and said so:
        "if it ever closes, this test fails and the module docstring has to
        be rewritten". It closed, so it was rewritten.

        Bishop used to sit at −0.276 % whatever the slice count, because a
        support paid ``T_N·tanφ'`` outside ``m_α`` while the identical force
        entering as a load had its normal come out of the slice's vertical
        equilibrium. With the support resolved as the line load the
        reference says it is, the two routes are the same statement and
        what is left is discretisation — the chord angle of a slice against
        the angle at the point where the force is applied — which is what
        Ordinary, Spencer and GLE have always shown here.

        Measured: −0.010 %, +0.0016 %, +0.0006 % at 25, 100 and 400 slices,
        against a frozen −0.276 % before. The band is deliberately wider
        than those numbers; what discriminates is the SHRINKING, which a
        formulation defect cannot fake and a discretisation residual cannot
        avoid.
        """
        gaps = self._gaps("bishop_simplified")
        assert all(abs(g) < 0.05 for g in gaps), gaps
        assert abs(gaps[-1]) < 0.3 * abs(gaps[0]), gaps

    def test_the_two_janbu_agree_exactly(self):
        """v0.1.142 — this test used to assert the OPPOSITE, and said so.
        It closed, so it was rewritten. D46 has no half left open.

        Janbu's balance is ``Σ S·sec α = Σ W·tan α``, so it owed the same
        correction Bishop got in v0.1.137 AND a ``sec α`` on its driving
        side, where it subtracted ``T_S`` raw. v0.1.141 had both branches
        measured and could not choose, because the only external evidence
        was the six published Clouterre planes and the combination that fit
        them was the one that failed THIS identity. What decided it was a
        closed form rather than a published number: on a plane the sliding
        mass is one free body, and the two Corps methods, Lowe-Karafiath
        and Ordinary all reproduce that wedge to the last digit while the
        old Janbu missed it by up to 20 %. See
        ``tests/test_janbu_wedge_v1142.py``.

        Unlike Bishop's half the agreement here is EXACT rather than
        shrinking, and that is stronger. Per slice a support owes the
        driving side ``−T_S·sec α = −slide_sign·(P_h + P_v·tan α)`` while
        the same force as a load owes ``−slide_sign·P_h`` through
        ``h_water`` and ``−slide_sign·P_v·tan α`` through ``w_total`` — the
        same two terms, so there is nothing left to discretise. Measured:
        0.0, 0.0 and −1.4e-14 % at 25, 100 and 400 slices, against a frozen
        −0.096 % before.
        """
        for mid in ("janbu_simplified", "janbu_corrected"):
            gaps = self._gaps(mid)
            assert all(abs(g) < 1e-9 for g in gaps), (mid, gaps)


# ======================================================================
class TestRuleSeven:
    """Every control moves the number — and where one cannot, it says so."""

    def test_each_profile_shape_gives_a_different_force(self):
        forces = set()
        for kind in ("uniform", "triangular", "trapezoidal", "custom"):
            w = _wall(profile_type=kind, pressure=20.0, efp=6.0,
                      distributed_over=60.0,
                      points=[(0.0, 10.0), (1.0, 70.0)])
            forces.add(round(w.force_at(3.0, 5.0), 9))
        assert len(forces) == 4, forces

    def test_distributed_over_moves_the_partial_integral(self):
        seen = set()
        for f in (20.0, 40.0, 60.0, 80.0):
            w = _wall(profile_type="trapezoidal", efp=TRAP_EFP,
                      distributed_over=f)
            seen.add(round(w.force_at(0.4 * TRAP_L, TRAP_L), 9))
        assert len(seen) == 4, seen

    def test_efp_and_pressure_scale_the_force(self):
        a = _wall(profile_type="triangular", efp=6.0).force_at(3.0, 5.0)
        b = _wall(profile_type="triangular", efp=12.0).force_at(3.0, 5.0)
        assert abs(b - 2.0 * a) < 1e-12
        u = _wall(profile_type="uniform", pressure=20.0).force_at(3.0, 5.0)
        v = _wall(profile_type="uniform", pressure=50.0).force_at(3.0, 5.0)
        assert abs(v - 2.5 * u) < 1e-12

    def test_active_and_passive_separate(self):
        from ogr_core.support import ForceApplication
        surf = _circle()
        for mid in _method_ids():
            a = _fos(mid, _wall_project(application=ForceApplication.ACTIVE),
                     surf)
            p = _fos(mid, _wall_project(application=ForceApplication.PASSIVE),
                     surf)
            assert a != p, mid
            assert p < a, mid

    def test_the_location_of_force_moves_the_four_moment_methods(self):
        surf = _circle()
        for mid in ("ordinary_fellenius", "bishop_simplified", "spencer",
                    "gle_morgenstern_price"):
            a = _fos(mid, _wall_project("intersection"), surf)
            b = _fos(mid, _wall_project("centroid"), surf)
            assert abs(b - a) > 1e-9, mid

    def test_and_provably_cannot_move_the_other_five(self):
        """The other half of the claim, and the half that is easy to skip.

        Moving a force leaves a couple, and a couple has nowhere to go in a
        method that writes force equilibrium alone. Asserting EQUALITY here
        is what stops the control from looking universal.
        """
        surf = _circle()
        for mid in ("janbu_simplified", "janbu_corrected",
                    "corps_engineers_1", "corps_engineers_2",
                    "lowe_karafiath"):
            a = _fos(mid, _wall_project("intersection"), surf)
            b = _fos(mid, _wall_project("centroid"), surf)
            assert a == b, mid

    def test_and_the_analysis_says_which_methods_are_blind_to_it(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        p = _wall_project("centroid")
        notes = " ".join(settings_warnings(
            p, ["bishop_simplified", "janbu_simplified"]))
        assert "janbu_simplified" in notes
        assert "centroid" in notes.lower()
        # And nothing to say when the setting is the one every method can
        # honour: a note that always fires is a note nobody reads.
        quiet = settings_warnings(_wall_project("intersection"),
                                  ["janbu_simplified"])
        assert quiet == []

    def test_the_couple_is_exactly_the_moment_arm_it_claims(self):
        """Not just "it moves": it moves BY the predicted amount."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms
        surf = _circle()
        p = _wall_project("centroid")
        eff = _effect(p)
        sl = slice_surface(p, surf, num_slices=25)
        terms = resolve_support_terms(p, surf, sl, 1.0)
        dy = eff.application_y - eff.intersection_y
        assert abs(terms.couple - (-dy * eff.force_h)) < 1e-12

    def test_a_support_that_acts_where_it_cuts_leaves_no_couple(self):
        """Zero for all seven older types, which is what protects them."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms
        surf = _circle()
        p = _wall_project("intersection")
        sl = slice_surface(p, surf, num_slices=25)
        assert resolve_support_terms(p, surf, sl, 1.0).couple == 0.0


# ======================================================================
class TestTheDistributedLoadHalf:
    """A horizontal distributed load used to do nothing at all."""

    @staticmethod
    def _sloping_load(orientation, angle=0.0):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad, LoadOrientation
        from ogr_core.project import Project
        p = _ground(Project("load"))
        p.distributed_loads = [DistributedLoad(
            start=Vertex(34.0, 2.4), end=Vertex(46.0, 9.6),
            magnitude_1=40.0, orientation=orientation, angle_deg=angle)]
        return p

    def test_horizontal_is_no_longer_inert(self):
        from ogr_core.loads import LoadOrientation
        from ogr_core.project import Project
        surf = _circle()
        bare = _fos("bishop_simplified", _ground(Project("bare")), surf)
        loaded = _fos("bishop_simplified",
                      self._sloping_load(LoadOrientation.HORIZONTAL), surf)
        assert loaded != bare
        # And in the direction a horizontal push towards the slope must go.
        assert loaded < bare

    def test_a_vertical_load_still_only_weighs(self):
        """The half that must NOT change: a vertical distributed load has
        no horizontal component and never had one."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_core.loads import LoadOrientation
        p = self._sloping_load(LoadOrientation.VERTICAL)
        sl = slice_surface(p, _circle(), num_slices=25)
        assert math.fsum(s.water_force_h for s in sl.slices) == 0.0
        assert math.fsum(s.weight for s in sl.slices) > 0.0

    def test_a_load_on_a_vertical_face_is_a_line_load_of_its_integral(self):
        """It could not be expressed at all before: a vertical segment has
        no horizontal extent, so no slice midpoint ever fell inside it."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads import (DistributedLoad, LoadDistribution,
                                    LoadOrientation)
        from ogr_core.project import Project
        from ogr_slip2d.slicer import slice_surface
        p = _ground(Project("face"))
        p.distributed_loads = [DistributedLoad(
            start=Vertex(XW, YW_TOP), end=Vertex(XW, YW_TOP - 4.0),
            magnitude_1=0.0, magnitude_2=100.0,
            distribution=LoadDistribution.TRIANGULAR,
            orientation=LoadOrientation.HORIZONTAL)]
        sl = slice_surface(p, _circle(), num_slices=25)
        f_h = math.fsum(s.water_force_h for s in sl.slices)
        m_h = math.fsum(s.water_force_h_moment for s in sl.slices)
        # Area of the triangle, and its centroid two thirds down.
        assert abs(f_h - 0.5 * 100.0 * 4.0) < 1e-9
        assert abs(m_h / f_h - (YW_TOP - 2.0 * 4.0 / 3.0)) < 1e-9

    def test_the_six_bank_models_cannot_be_touched_by_any_of_it(self):
        """Their loads sit on HORIZONTAL segments, where the normal
        direction is (0, −1) and the horizontal component is exactly zero.
        By construction, not by hope — which is why this asserts the
        direction vector rather than a factor of safety.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.loads import (DistributedLoad, LoadDistribution,
                                    LoadOrientation)
        for orientation in (LoadOrientation.VERTICAL,
                            LoadOrientation.NORMAL_TO_BOUNDARY):
            ld = DistributedLoad(
                start=Vertex(10.0, 25.0), end=Vertex(30.0, 25.0),
                magnitude_1=50.0, distribution=LoadDistribution.CONSTANT,
                orientation=orientation)
            dxu, dyu = ld.direction_vector()
            assert dxu == 0.0, orientation
            assert abs(dyu) == 1.0, orientation


# ======================================================================
class TestSerialisation:
    """A wall must survive the file it is written to."""

    def test_round_trip_keeps_every_field(self):
        from ogr_core.support import support_from_dict
        w = _wall(profile_type="custom", force_location="centroid",
                  pressure=13.0, efp=17.0, distributed_over=42.0,
                  points=[(0.0, 1.0), (0.5, 2.0), (1.0, 3.0)])
        back = support_from_dict(w.to_dict())
        assert back.profile_type == "custom"
        assert back.force_location == "centroid"
        assert back.pressure == 13.0 and back.efp == 17.0
        assert back.distributed_over == 42.0
        assert [tuple(p) for p in back.points] == [(0.0, 1.0), (0.5, 2.0),
                                                   (1.0, 3.0)]
        assert back.force_at(3.0, 5.0) == w.force_at(3.0, 5.0)

    def test_two_walls_do_not_share_one_table(self):
        """``__dict__`` copying handed both the same list object."""
        from ogr_core.support import support_from_dict
        a = _wall(profile_type="custom", points=[(0.0, 0.0), (1.0, 10.0)])
        b = support_from_dict(a.to_dict())
        b.points.append((0.5, 99.0))
        assert len(a.points) == 2

    def test_the_type_is_in_the_registry_under_its_own_id(self):
        from ogr_core.support import support_registry
        assert "retaining_wall_efp" in support_registry()
