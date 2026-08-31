# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A support's line load on a surface that is NOT a circle, where nothing was
looking.

WHAT INVARIANT THIS PROTECTS

A support force is a line load on the slice it crosses, so it joins that
slice's VERTICAL equilibrium — the one ``m_α`` is what remains of (Bishop
1955) — and its frictional share reaches the base divided by ``m_α``.
v0.1.137 rewired BOTH of Bishop's paths for that: the circular one, and
:meth:`ogr_slip2d.methods.bishop.BishopSimplified._general_moment_fos`,
where the load now joins ``w_n`` before ``m_α`` and ``sup`` is handed to
``moment_terms`` so the base normal it carries is the true one.

Only the circular half was ever asserted. This file is the other one.

WHY THREE EXISTING FILES ALL MISS IT, AND EACH FOR ITS OWN REASON

* ``test_support_normal_v1137`` and ``test_support_tangential_v1139`` build
  a ``SlipCircle`` and nothing else, so ``_general_moment_fos`` never runs.
* ``test_support_active_passive_v1115`` DOES put every method on a polyline
  — but its quantitative anchor, the closed form, sets **φ' = 0**, and with
  no friction the whole term this is about is identically zero. What is
  left there is qualitative: Active ≠ Passive, and Passive below Active.
* ``test_efp_wall_v1122`` holds the load-equals-support identity, on a
  circle, with a **horizontal ACTIVE** force — and for that combination the
  load is identically zero whatever the geometry:

      down = T_N·cos α − slide_sign·sin α·T_S
           = F·sin α·cos α − F·sin α·cos α = 0

  which is simply the statement that a horizontal force has no vertical
  component. The eight tiered geosynthetic walls that opened defect D44 are
  horizontal sheets too; they are PASSIVE, so their load is not zero, but
  it is ``F·sin α·cos α·(1 − 1/F)`` — small, and never on a polyline.

So the fixture here has to be a support whose force is genuinely INCLINED.

THE TWO ANCHORS, NEITHER OF THEM CAPTURED

1. A CLOSED FORM. For an ACTIVE support the whole expression collapses,
   for a force of magnitude F at angle θ above the horizontal, to

       down = F·sin(α−θ)·cos α − sin α·F·cos(α−θ) = −F·sin θ

   — the vertical component of the force, and nothing else. It does not
   depend on the base angle, on the surface, or on the slice count, which
   is why it discriminates: the trigonometry is written out here and the
   solver plays no part in it.

2. AN IDENTITY. The reference's own page says a support force is applied
   at the point where it cuts the surface and that there it "is simply a
   line load" — that sentence is what v0.1.137 rested on. So the same
   magnitude, at the same point, at the same angle, must give the same
   factor of safety whether it arrives as a support or as a line load.
   That is the definition of a free body, not a convention, and OGR reaches
   the two through completely different code: a support through
   ``resolve_support_terms`` and ``sup``, a line load through the slicer,
   which puts its vertical part in ``weight`` and its horizontal part in
   the external-force channel.

HOW MUCH IT DISCRIMINATES, MEASURED

With ``support_vertical_load`` forced to return 0.0 — the pre-v0.1.137
shape of the arithmetic on this path — the identity on the polyline goes
from −0.087 / −0.019 / −0.0020 % at 50 / 100 / 400 slices to
−3.59 / −3.56 / −3.58 %, and stops shrinking. Ordinary, Spencer and GLE do
not move at all, because none of them calls it. That contrast IS the last
class of this file, so the file proves its own teeth rather than claiming
them.

WHAT WAS MEASURED AND LEFT OUT

Comparing the support's contribution ``ΔF = F(with) − F(without)`` between
the circular path and the same circle written as a dense polyline. It does
not discriminate: Bishop's ratio is 1.011 today and 1.026 with the branch
annulled, against a baseline that is not 1 to begin with — the two paths
take the arc and the chord respectively, which ``bishop.py`` documents as a
deliberate modelling choice. A near-identity with a moving baseline proves
nothing, so it is recorded here instead of asserted.
"""
from __future__ import annotations

import math

# ----------------------------------------------------------------------
# A slope, an inclined anchor, and the same circle written as a polyline.
# ----------------------------------------------------------------------
H, TOE, CREST = 12.0, 30.0, 50.0

#: Anchor head on the slope face — the ground at x = 41 is exactly 6.6 —
#: running up into the slope so it cuts the trial surface well below the
#: crest, where the bases are steep.
XS, YS = 41.0, 6.6
TAIL = (52.0, 10.0)

#: Degrees above the horizontal. The point of the fixture: NOT horizontal,
#: so ``down`` is not identically zero, and not tangent either, so both
#: branches of the load are alive.
ANGLE_DEG = 20.0
CAPACITY = 40.0

CIRCLE = (38.0, 26.0, 20.0)

#: Six vertices sampled off that circle. Six, and not sixty, for two
#: reasons: it is unmistakably a polyline rather than a circle in disguise,
#: and ``slice_surface`` refuses a polyline with more vertices than the
#: requested number of slices — 40 vertices with 25 slices returns None.
POLY_VERTICES = 6

#: Slice counts for the refinement sweep. The gap changes sign below 50, so
#: the shrinking is asserted over a range where it is monotone.
SWEEP = (50, 100, 400)


def _ground(project, cohesion=5.0, friction=25.0):
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


def _bare():
    from ogr_core.project import Project
    return _ground(Project("bare"))


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=CIRCLE[0], centre_y=CIRCLE[1],
                      radius=CIRCLE[2])


def _anchored(application=None, angle=ANGLE_DEG, capacity=CAPACITY):
    from ogr_core.geometry import Vertex
    from ogr_core.project import Project
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _ground(Project("anchored"))
    p.support_types = [EndAnchored(anchor_capacity=capacity,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(XS, YS), tail=Vertex(*TAIL),
        force_application=application or ForceApplication.ACTIVE,
        orientation=ForceOrientation.USER_DEFINED,
        user_angle_deg=angle)]
    return p


def _polyline():
    """The circle above, resampled as a polyline of :data:`POLY_VERTICES`.

    Sampled rather than invented so it is guaranteed to daylight and to be
    crossed by the same anchor — the same trick ``test_support_active_
    passive_v1115`` uses, and for the same reason.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipSurface
    sl = slice_surface(_bare(), _circle(), num_slices=200)
    pts = [(sl.slices[0].base_x_left, sl.slices[0].base_y_left)]
    pts += [(s.base_x_right, s.base_y_right) for s in sl.slices]
    idx = [round(i * (len(pts) - 1) / (POLY_VERTICES - 1))
           for i in range(POLY_VERTICES)]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(*pts[i]) for i in idx]))


def _slices(project, surface, n):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=n)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return sl


def _fos(method_id, project, surface, n=50):
    from ogr_slip2d.methods.base import method_registry
    sl = _slices(project, surface, n)
    return method_registry()[method_id]().compute_fos(
        project, surface, sl).fos


def _effect(project, surface, n=50):
    from ogr_slip2d.support_integration import compute_support_effects
    eff = compute_support_effects(project, surface,
                                  _slices(project, surface, n))
    return eff[0] if eff else None


def _line_load_twin(eff):
    """The same force, at the same point, arriving as a line load."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads import LineLoad, LoadOrientation
    from ogr_core.project import Project
    p = _ground(Project("line-load"))
    p.line_loads = [LineLoad(
        point=Vertex(eff.application_x, eff.application_y),
        magnitude=eff.force_magnitude,
        orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL,
        angle_deg=math.degrees(eff.force_angle_rad))]
    return p


def _gap(method_id, surface, n):
    """``100·(F_load − F_support)/F_support`` in per cent."""
    p = _anchored()
    eff = _effect(p, surface, n)
    assert eff is not None, "the anchor does not cross this surface"
    twin = _line_load_twin(eff)
    a = _fos(method_id, p, surface, n)
    b = _fos(method_id, twin, surface, n)
    return 100.0 * (b - a) / a


#: The three that do NOT call ``support_vertical_load``. They are the
#: control in the last class and the scale of the discretisation residual
#: everywhere else: when the four move together, the cause is the mesh.
CONTROLS = ("ordinary_fellenius", "spencer", "gle_morgenstern_price")


# ======================================================================
class TestTheFixtureIsWhatItClaims:
    """Every premise the rest of the file rests on, asserted rather than
    assumed. Three of them have already been wrong once in this project:
    a support that crossed nothing, a surface that took the circular
    shortcut, and a force with no vertical component."""

    def test_the_surface_is_not_a_circle(self):
        """The dispatch in ``bishop.py`` is exactly ``not isinstance(
        surface, SlipCircle)``, so this is the whole premise of the file:
        fail it and every assertion below is testing the circular path
        again."""
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        surf = _polyline()
        assert isinstance(surf, SlipSurface)
        assert not isinstance(surf, SlipCircle)
        assert len(surf.polyline.vertices) == POLY_VERTICES

    def test_the_anchor_crosses_it_and_the_base_there_is_steep(self):
        """``cos α / m_α`` is what separates the two arithmetics, and it
        only departs from 1 on a steep base: it is 0.71 at 51°."""
        surf = _polyline()
        p = _anchored()
        eff = _effect(p, surf, 50)
        assert eff is not None
        sl = _slices(p, surf, 50)
        alpha = abs(math.degrees(sl.slices[eff.slice_index].base_angle))
        assert alpha > 25.0, alpha

    def test_the_force_has_a_real_vertical_component(self):
        """With a horizontal force the load is identically zero — see the
        module docstring — so a fixture that let the angle drift back to
        the horizontal would go green without measuring anything."""
        eff = _effect(_anchored(), _polyline(), 50)
        assert abs(math.degrees(eff.force_angle_rad) - ANGLE_DEG) < 1e-9
        assert abs(eff.force_v) > 0.3 * abs(eff.force_magnitude)

    def test_the_support_is_worth_enough_to_be_visible(self):
        """A support so weak that the identity holds by rounding would
        prove nothing either."""
        surf = _polyline()
        gain = _fos("bishop_simplified", _anchored(), surf, 100) - _fos(
            "bishop_simplified", _bare(), surf, 100)
        assert gain > 0.3, gain


# ======================================================================
class TestTheLoadIsTheVerticalComponentOfTheForce:
    """The closed form. For an ACTIVE support,

        down = T_N·cos α − slide_sign·sin α·T_S
             = F·sin(α−θ)·cos α − sin α·F·cos(α−θ)
             = −F·sin θ

    by the sine subtraction formula, for every α. Nothing in it comes from
    the solver, and it holds on a circle and on a polyline alike because
    it never mentions the surface.
    """

    def _measure(self, surface, angle, n=50):
        from ogr_slip2d.support_integration import (resolve_support_terms,
                                                    support_vertical_load)
        p = _anchored(angle=angle)
        sl = _slices(p, surface, n)
        sup = resolve_support_terms(p, surface, sl.slices, 1.0)
        assert sup.present, "no support resolved onto this surface"
        i = max(range(len(sup.n_press)),
                key=lambda k: abs(sup.n_press[k]) + abs(sup.t_active[k]))
        down = support_vertical_load(
            sup, i, sl.slices[i].base_angle, 1.0, 1.5)
        eff = _effect(p, surface, n)
        return down, eff, sl.slices[i].base_angle

    def test_it_equals_minus_f_sin_theta_on_the_polyline(self):
        surf = _polyline()
        for angle in (5.0, 20.0, 35.0):
            down, eff, _a = self._measure(surf, angle)
            expected = -eff.force_magnitude * math.sin(math.radians(angle))
            assert abs(down - expected) < 1e-9 * eff.force_magnitude, (
                angle, down, expected)

    def test_it_equals_the_same_thing_on_the_circle(self):
        """Same statement, other path. If the two ever disagree, one of
        the two dispatches has grown a term of its own."""
        for angle in (5.0, 20.0, 35.0):
            down, eff, _a = self._measure(_circle(), angle)
            expected = -eff.force_magnitude * math.sin(math.radians(angle))
            assert abs(down - expected) < 1e-9 * eff.force_magnitude, (
                angle, down, expected)

    def test_it_does_not_depend_on_the_base_angle(self):
        """The α's cancel in the closed form, so the same force on two
        differently inclined bases must put the SAME load on its slice.

        The two bases come from the two surfaces, not from two mesh
        densities: on a polyline every slice of one segment shares that
        segment's slope, so refining the mesh leaves α untouched to the
        last bit. The first version of this test refined instead, and its
        own guard caught it — the number it was comparing was the same
        number twice.
        """
        pairs = [self._measure(surf, ANGLE_DEG)[::2]
                 for surf in (_circle(), _polyline())]
        (down_c, alpha_c), (down_p, alpha_p) = pairs
        assert abs(math.degrees(alpha_c) - math.degrees(alpha_p)) > 0.5, (
            "the two surfaces gave the same base angle, so this proves "
            "nothing: %r" % (pairs,))
        assert abs(down_c - down_p) < 1e-9 * CAPACITY, pairs

    def test_a_horizontal_active_force_puts_no_load_on_its_slice(self):
        """Stated as an assertion because it is the reason this file had
        to exist: with a horizontal force the term is identically zero,
        and every fixture that already covered supports had one."""
        from ogr_core.support import ForceOrientation
        from ogr_slip2d.support_integration import (resolve_support_terms,
                                                    support_vertical_load)
        surf = _polyline()
        p = _anchored()
        p.supports[0].orientation = ForceOrientation.HORIZONTAL
        sl = _slices(p, surf, 50)
        sup = resolve_support_terms(p, surf, sl.slices, 1.0)
        for i, s in enumerate(sl.slices):
            down = support_vertical_load(sup, i, s.base_angle, 1.0, 1.5)
            assert abs(down) < 1e-9 * CAPACITY, (i, down)
        # ...and it is NOT because the support is doing nothing.
        assert max(abs(x) for x in sup.n_press) > 0.1 * CAPACITY


# ======================================================================
class TestASupportAndALineLoadAreTheSameFreeBody:
    """The identity, on the path nothing was checking.

    The same magnitude, at the same point, at the same angle, reaching the
    solver by two unrelated routes. What is left over must be
    discretisation, and discretisation shrinks.
    """

    #: Wider than anything measured (the largest is 0.13 % at 50 slices),
    #: and two orders below the −3.6 % the annulled branch produces. A
    #: band that only just fits today's numbers is a snapshot.
    TOL = 0.5

    def test_bishop_holds_it_on_the_polyline(self):
        surf = _polyline()
        gaps = [_gap("bishop_simplified", surf, n) for n in SWEEP]
        assert all(abs(g) < self.TOL for g in gaps), gaps
        # What discriminates is the SHRINKING, which a formulation defect
        # cannot fake and a discretisation residual cannot avoid.
        assert abs(gaps[-1]) < 0.3 * abs(gaps[0]), gaps

    def test_the_three_that_never_had_the_defect_hold_it_too(self):
        """Their residual is the scale of the mesh error on this fixture:
        if Bishop's were much larger than theirs, the excess would be
        Bishop's own."""
        surf = _polyline()
        for mid in CONTROLS:
            gaps = [_gap(mid, surf, n) for n in SWEEP]
            assert all(abs(g) < self.TOL for g in gaps), (mid, gaps)
            assert abs(gaps[-1]) < 0.3 * abs(gaps[0]), (mid, gaps)

    def test_bishop_is_no_worse_than_the_controls(self):
        surf = _polyline()
        mine = abs(_gap("bishop_simplified", surf, 100))
        theirs = max(abs(_gap(mid, surf, 100)) for mid in CONTROLS)
        assert mine <= theirs + 1e-9, (mine, theirs)


# ======================================================================
class TestThisFileWouldHaveFailedAgainstTheOldArithmetic:
    """A test that does not fail against the defect it claims to protect
    protects nothing.

    ``support_vertical_load`` is forced to return 0.0, which is the shape
    the non-circular path had before v0.1.137 as far as the slice's
    vertical equilibrium is concerned. The patch is undone in ``finally``:
    rule 5, and a leaked monkeypatch on a production module is the worst
    kind, because it only shows up in the FULL suite.
    """

    @staticmethod
    def _with_branch_annulled(fn):
        import ogr_slip2d.support_integration as si
        good = si.support_vertical_load
        si.support_vertical_load = lambda *a, **kw: 0.0
        try:
            return fn()
        finally:
            si.support_vertical_load = good

    def test_the_identity_breaks_and_stops_shrinking(self):
        surf = _polyline()
        gaps = self._with_branch_annulled(
            lambda: [_gap("bishop_simplified", surf, n) for n in SWEEP])
        assert all(abs(g) > 2.0 for g in gaps), gaps
        # It does not shrink: that is what separates a formulation error
        # from a mesh residual, and it is the same signature v0.1.137
        # found on the circle at a frozen −0.276 %.
        assert abs(gaps[-1]) > 0.8 * abs(gaps[0]), gaps

    def test_the_controls_do_not_move_at_all(self):
        """None of the three calls the function, so annulling it must be
        invisible to them. If one moves, the patch is reaching somewhere
        it should not and the class above proves nothing."""
        surf = _polyline()
        before = {mid: _gap(mid, surf, 100) for mid in CONTROLS}
        after = self._with_branch_annulled(
            lambda: {mid: _gap(mid, surf, 100) for mid in CONTROLS})
        for mid in CONTROLS:
            assert before[mid] == after[mid], (mid, before[mid], after[mid])

    def test_the_patch_is_undone(self):
        """Rule 5, asserted rather than trusted."""
        import ogr_slip2d.support_integration as si
        original = si.support_vertical_load
        self._with_branch_annulled(lambda: None)
        assert si.support_vertical_load is original
