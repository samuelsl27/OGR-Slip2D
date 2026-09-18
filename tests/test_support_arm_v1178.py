# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.178 (D144) — a support's MOMENT is the moment of its force, and a
chord is not an arc.

WHAT INVARIANT THIS PROTECTS. A support force is a line load applied where
the reinforcement crosses the slip surface. Its moment about a circle's
centre is therefore the cross product of that force at that point, and
nothing else:

    M = (x_P − x_c)·F_v − (y_P − y_c)·F_h

``resolve_support_terms`` resolved every support onto the CHORD of the slice
it crosses — ``a = s_list[i].base_angle`` — and the three circular moment
paths took the resulting tangential projection with an arm of exactly R. On
an arc the chord is not the tangent, so that product is not the moment.
Measured on verification problem 85 at 50 slices: chord 50.8600°, tangent
50.3024°, ``t`` = 5680.95 against 5748.21 exact = 9000·(37.624 − 20)/27.594,
**1.170 % short**; F went from 1.556171 to 1.569188, and the published
figure for that circle is 1.575, so the arm was 70 % of the whole distance.

WHY THE CHORD IS NOT A BUG EVERYWHERE, which is what decides the design.
Decomposing a force onto the chord and its normal is a ROTATION: ``t_active``
and ``n_press`` recompose to ``(f_h, f_v)`` bit for bit, and the slice's
force equilibrium is written on a base that IS the chord since v0.1.100. The
force branch telescopes exactly because of it — ``Σ t_active·sec a = F_h``
whatever the angle — and ``TestTheForceBranchStillTelescopes`` below holds
that, green on both sides of this change, because turning the decomposition
itself to the tangent would have BROKEN an exact identity to mend an
approximate one. The only approximate thing in the chain is the ARM, and an
arm is geometry, not a projection. So ``moment_active`` / ``moment_passive``
join ``t_active`` / ``t_passive`` instead of replacing them — exactly as
``Slice.weight_arm_ratio`` joined ``Slice.base_angle`` in v0.1.100, and for
the same reason, written there as "the chord's own angle is no longer the
tangent at xc, so the moment arm is taken from the geometry instead of from
the angle". The weight got that treatment; the reinforcement did not.

THE SHAPE OF THE ERROR, which is what ``TestItIsNotTheChord`` measures. To
first order the relative error is ``Δα·tan α`` with ``Δα = α_chord −
α_tangent``: on problem 85, 9.74e-3 rad × 1.2045 = 1.173 % against the
1.170 % measured. ``Δα`` is O(1/n) with a sign that depends on where inside
its slice the crossing falls, so this is NOT a bias — on the same problem's
other published circle (85.3) the chord runs 0.44° the OTHER way and the
term comes out 1.06 % LONG. A residual that changes sign cannot be waved
away as discretisation, and a test that only watched it shrink would have
been satisfied by the defect.

WHAT THIS FILE DOES NOT CLAIM, said out loud.

* ``TestTheMomentIsTheMomentOfTheForce`` is EXACT BY CONSTRUCTION, to
  1e-15, not to 1e-9. It checks the bookkeeping — that the field is the
  cross product at the point the engine reports — and it does not check
  where that point is. It is here because the bookkeeping is what a future
  edit would break, not because it measures the geometry.
* The crossing point itself is computed against the POLYLINE OF CHORDS
  (``compute_support_effects`` → ``intersection_with_polyline`` →
  ``_slip_polyline``, built from ``base_x_left``/``base_x_right``), so it
  sits O(1/n²) off the arc — about 2e-3 ft on problem 85.
  ``TestTheResidualThatRemains`` measures that leftover and its order
  instead of pretending it is gone: it is worth about 0.007 %, some 160
  times less than the 1.17 % this version closes. D144 shuts the
  first-order term and leaves a named, measured second-order one.
* Not a single assertion here fixes a factor of safety. Every expected
  value is a closed form written in this file, an identity between two
  routes through the engine, or a sign.

WHICH CASES MEASURE THE DEFECT AND WHICH ARE CONTROL, counted rather than
claimed. Against the tree of 0.1.177, with only this file added, 9 of the 21
cases FAIL and 12 PASS — and only THREE of the nine discriminate on their own
terms: the two closed forms of ``TestTheClosedFormWithZeroFriction`` (out by
−1.05 % active and −0.17 % passive) and the load-equals-support identity of
``TestTheLoadAndTheSupportAreOneStatement`` (−1.05 %). Those three never
mention ``moment_active``; they are written from the circle's geometry, so
they would still fail against a tree that had never heard of this field.

The other six fail with ``AttributeError`` because they read the new field.
That is WEAK discrimination — it proves the field is new, not that it is
right — and it is labelled here rather than counted, because six cases that
fail for that reason inflate the number without adding evidence.

The 12 that pass on BOTH trees are the controls, and one of them exists for
what this change could have broken rather than for what it fixed:
``TestTheForceBranchStillTelescopes``.
"""
from __future__ import annotations

import math

# ----------------------------------------------------------------------
# A slope, a circle, and two anchors — one horizontal and one genuinely
# inclined, because the identity carries BOTH terms and a horizontal-only
# fixture would measure half of it and look complete.
# ----------------------------------------------------------------------
H, TOE, CREST = 12.0, 30.0, 50.0
GAMMA = 18.0
CIRCLE = (38.0, 26.0, 20.0)

#: Degrees above the horizontal for the inclined anchor. Not 0, not tangent
#: to the surface, and not so steep that the anchor stops crossing the arc.
TILT_DEG = 25.0

#: NO support here is ``TANGENT_TO_SLIP``, and that is deliberate: that
#: orientation takes its DIRECTION from ``_slip_tangent_at_x``, which is the
#: chord's slope too, so today its direction error and its arm error cancel.
#: Measuring D144 through it would measure the cancellation, not the arm.
CAP = 120.0


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
        name="S", unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=friction))]
    return project


def _face_y(x):
    """The slope face, so an anchor head lands ON it (v0.1.138)."""
    return (x - TOE) * H / (CREST - TOE)


def _circle():
    from ogr_slip2d.surface import SlipCircle
    cx, cy, r = CIRCLE
    return SlipCircle(centre_x=cx, centre_y=cy, radius=r)


def _anchor(x_head, orientation, angle=None, application=None,
            capacity=CAP, dx=13.0, dy=4.0):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    y = _face_y(x_head)
    return SupportInstance(
        type_id="end_anchored",
        head=Vertex(x_head, y), tail=Vertex(x_head + dx, y + dy),
        force_application=application or ForceApplication.ACTIVE,
        orientation=orientation,
        user_angle_deg=angle if angle is not None else 0.0,
        name="a%.1f" % x_head)


def _project(supports, cohesion=8.0, friction=20.0, capacity=CAP):
    from ogr_core.project import Project
    from ogr_core.support import EndAnchored
    p = _ground(Project("d144"), cohesion, friction)
    p.support_types = [EndAnchored(anchor_capacity=capacity,
                                   out_of_plane_spacing=1.0)]
    p.supports = list(supports)
    return p


def _horizontal(application=None):
    from ogr_core.support import ForceOrientation
    return _project([_anchor(41.0, ForceOrientation.HORIZONTAL,
                             application=application)])


def _inclined(application=None):
    from ogr_core.support import ForceOrientation
    # The same GEOMETRY as the horizontal one: what tilts is the FORCE.
    # An anchor drawn further down the face never reaches this arc, which
    # only spans x 40.2 to 52.3, and an empty effect list makes every
    # assertion about it vacuous instead of false.
    return _project([_anchor(41.0, ForceOrientation.USER_DEFINED,
                             angle=TILT_DEG, application=application)])


def _both():
    from ogr_core.support import ForceOrientation
    return _project([
        _anchor(41.0, ForceOrientation.HORIZONTAL),
        _anchor(43.0, ForceOrientation.USER_DEFINED, angle=TILT_DEG),
    ])


def _bare(cohesion=8.0, friction=20.0):
    from ogr_core.project import Project
    return _ground(Project("bare"), cohesion, friction)


# ----------------------------------------------------------------------
# Everything below is written from the geometry. None of it asks the
# engine what the answer is.
# ----------------------------------------------------------------------
def _slices(project, surface, n):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=n)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return sl


def _slide_sign(s_list):
    raw = math.fsum(s.weight * math.sin(s.base_angle) for s in s_list)
    return 1.0 if raw >= 0 else -1.0


def _effects(project, surface, sl):
    from ogr_slip2d.support_integration import compute_support_effects
    return compute_support_effects(project, surface, sl)


def _exact_over_r(eff, sign):
    """The cross product at the crossing, divided by R.

    The sign convention is not invented here, it is read off the weight:
    the circular driving sum adds ``slide_sign·W·weight_arm_ratio`` for a
    weight ``(0, −W)`` at abscissa ``x``, i.e. ``−slide_sign·M_z/R`` with
    ``M_z`` the anticlockwise moment about the centre. The couple enters
    the same way (``−slide_sign·couple/R``) and so does the water.
    """
    cx, cy, _r = CIRCLE
    return sign * ((eff.intersection_x - cx) * eff.force_v
                   - (eff.intersection_y - cy) * eff.force_h) / CIRCLE[2]


def _chord_over_r(eff, s_list, sign):
    """What the engine used before D144: the projection on the chord."""
    a = s_list[eff.slice_index].base_angle
    return sign * (eff.force_h * math.cos(a) + eff.force_v * math.sin(a))


def _tangent_angle(eff):
    """Tangent of the arc at the crossing: cos a = (cy − y)/R, sin a = (x − cx)/R."""
    cx, cy, _r = CIRCLE
    return math.atan2(eff.intersection_x - cx, cy - eff.intersection_y)


def _driving_no_support(s_list, sign):
    """``Σ slide_sign·W·weight_arm_ratio`` — the circular driving sum with
    no earthquake, no water and no reinforcement, which is the whole of it
    for this fixture."""
    from ogr_slip2d.external_forces import slice_forces
    return math.fsum(sign * slice_forces(s, 0.0, 0.0).w_total
                     * s.weight_arm_ratio for s in s_list)


def _cohesion_moment(s_list, cohesion):
    """``Σ c·l``. With φ' = 0 the frictional term is identically zero, so
    ``N`` never enters and Bishop, Fellenius and GLE's moment branch are
    the same ratio of two sums."""
    return cohesion * math.fsum(s.base_length for s in s_list)


def _fos(method_id, project, surface, sl):
    from ogr_slip2d.methods.base import method_registry
    return method_registry()[method_id]().compute_fos(
        project, surface, sl).fos


def _terms(project, surface, sl, sign):
    from ogr_slip2d.support_integration import resolve_support_terms
    return resolve_support_terms(project, surface, sl, sign)


# ======================================================================
class TestTheMomentIsTheMomentOfTheForce:
    """The bookkeeping. EXACT BY CONSTRUCTION — see the header: this says
    the field is the cross product at the point the engine reports, not
    that the point is right."""

    def _check(self, project, n):
        surf = _circle()
        sl = _slices(project, surf, n)
        sign = _slide_sign(sl.slices)
        sup = _terms(project, surf, sl, sign)
        act = pas = 0.0
        for eff in _effects(project, surf, sl):
            m = _exact_over_r(eff, sign)
            if eff.is_active:
                act += m
            else:
                pas += m
        assert act or pas, "the fixture put no support on the surface"
        for got, want, what in ((sup.moment_active, act, "active"),
                                (sup.moment_passive, pas, "passive")):
            if want:
                assert abs(got / want - 1.0) < 1e-13, (n, what, got, want)
            else:
                assert got == 0.0, (n, what, got)

    def test_a_horizontal_anchor_at_twenty_fifty_and_two_hundred(self):
        for n in (20, 50, 200):
            self._check(_horizontal(), n)

    def test_an_inclined_anchor_at_twenty_fifty_and_two_hundred(self):
        for n in (20, 50, 200):
            self._check(_inclined(), n)

    def test_a_passive_anchor_lands_in_the_other_field(self):
        from ogr_core.support import ForceApplication
        p = _inclined(ForceApplication.PASSIVE)
        surf = _circle()
        sl = _slices(p, surf, 50)
        sup = _terms(p, surf, sl, _slide_sign(sl.slices))
        assert sup.moment_active == 0.0
        assert sup.moment_passive != 0.0
        self._check(p, 50)

    def test_the_vertical_term_is_not_negligible(self):
        """Or the inclined fixture is a horizontal one in disguise and the
        second half of the cross product is never exercised."""
        surf = _circle()
        p = _inclined()
        sl = _slices(p, surf, 50)
        sign = _slide_sign(sl.slices)
        cx, cy, r = CIRCLE
        for eff in _effects(p, surf, sl):
            v = abs((eff.intersection_x - cx) * eff.force_v) / r
            h = abs((eff.intersection_y - cy) * eff.force_h) / r
            assert v > 0.20 * (v + h), (v, h)

    def test_two_anchors_on_one_slice_add_per_effect(self):
        """And the same sum taken from the |F|-weighted mean point does
        NOT agree, which is why the accumulation is per effect: ``x_app``
        is an average, and the arm of a sum of forces is not the sum of
        arms unless the weights are the moments themselves."""
        surf = _circle()
        p = _both()
        for n in range(5, 16):
            sl = _slices(p, surf, n)
            sign = _slide_sign(sl.slices)
            sup = _terms(p, surf, sl, sign)
            effs = _effects(p, surf, sl)
            if len({e.slice_index for e in effs}) != 1 or len(effs) != 2:
                continue
            cx, cy, r = CIRCLE
            fh = math.fsum(e.force_h for e in effs)
            fv = math.fsum(e.force_v for e in effs)
            i = effs[0].slice_index
            mean = sign * ((sup.x_app[i] - cx) * fv
                           - (sup.y_app[i] - cy) * fh) / r
            per = math.fsum(_exact_over_r(e, sign) for e in effs)
            assert abs(sup.moment_active / per - 1.0) < 1e-13, (n, per)
            assert abs(mean / per - 1.0) > 1e-6, (n, mean, per)
            return
        raise AssertionError("no coarse mesh put both anchors on one slice")


# ======================================================================
class TestItIsNotTheChord:
    """The shape of the error, with no published value anywhere in it.

    The exact term barely moves with the slice count, because the only
    thing that moves it is where the crossing point lands. The chord term
    wanders by about a per cent AND changes sign, which is the signature
    of ``Δα·tan α`` with ``Δα`` O(1/n): a bias does not change sign.
    """

    SWEEP = (20, 40, 80, 160)

    def _series(self, project):
        surf = _circle()
        out = []
        for n in self.SWEEP:
            sl = _slices(project, surf, n)
            sign = _slide_sign(sl.slices)
            effs = _effects(project, surf, sl)
            exact = math.fsum(_exact_over_r(e, sign) for e in effs)
            chord = math.fsum(_chord_over_r(e, sl.slices, sign) for e in effs)
            out.append((n, exact, chord))
        return out

    def test_the_exact_term_hardly_moves_with_the_slice_count(self):
        for project in (_horizontal(), _inclined()):
            ser = self._series(project)
            vals = [e for _n, e, _c in ser]
            spread = (max(vals) - min(vals)) / abs(vals[0])
            assert spread < 1e-3, ser

    def test_the_chord_term_wanders_an_order_of_magnitude_more(self):
        """Measured over n = 20, 40, 80, 160: the chord term spreads
        5.33e-3 against the exact term's 1.96e-4 for the horizontal anchor
        (27x) and 9.24e-4 against 7.91e-5 for the inclined one (12x). The
        bound asserted is 8x, which is the smaller of the two with margin:
        writing 27 here would be freezing this fixture's mesh, and the
        statement is the ORDER, not the figure."""
        for project in (_horizontal(), _inclined()):
            ser = self._series(project)
            ex = [e for _n, e, _c in ser]
            ch = [c for _n, _e, c in ser]
            spread_e = (max(ex) - min(ex)) / abs(ex[0])
            spread_c = (max(ch) - min(ch)) / abs(ch[0])
            assert spread_c > 8.0 * spread_e, (spread_c, spread_e)

    def test_the_chord_deviation_changes_sign_across_the_sweep(self):
        """A discretisation residual with a sign that flips is not a bias
        that a finer mesh will pay off in one direction."""
        signs = set()
        for project in (_horizontal(), _inclined()):
            for _n, e, c in self._series(project):
                signs.add(1 if c > e else -1)
        assert signs == {1, -1}, signs

    def test_the_first_order_law(self):
        """``−Δα·tan(α − θ)`` — trigonometry written here, no solver in it.

        The projection is ``|F|·cos(a − θ)`` with θ the force's own angle,
        so the chord/exact ratio is ``cos(a_c − θ)/cos(a_t − θ)`` and the
        law carries θ. Writing ``tan α`` instead is right only for a
        HORIZONTAL force, and this fixture has an inclined one precisely
        so that the shortcut cannot pass: at 25° it is off by a factor of
        5.8.

        A first-order law is asserted the way a first-order law deserves —
        loosely at the coarsest mesh and tightly at the finest, because
        what makes it a law is that it IMPROVES. Measured ratios:
        0.967 / 1.014 / 0.985 / 1.001 horizontal, 0.804 / 1.081 / 0.912 /
        1.006 inclined, at n = 20 / 40 / 80 / 160.
        """
        surf = _circle()
        seen = 0
        for project in (_horizontal(), _inclined()):
            for n in self.SWEEP:
                sl = _slices(project, surf, n)
                sign = _slide_sign(sl.slices)
                for eff in _effects(project, surf, sl):
                    e = _exact_over_r(eff, sign)
                    c = _chord_over_r(eff, sl.slices, sign)
                    got = c / e - 1.0
                    a_t = _tangent_angle(eff)
                    theta = math.atan2(eff.force_v, eff.force_h)
                    d_a = sl.slices[eff.slice_index].base_angle - a_t
                    law = -d_a * math.tan(a_t - theta)
                    band = 0.02 if n == self.SWEEP[-1] else 0.25
                    assert abs(got / law - 1.0) < band, (n, got, law)
                    seen += 1
        assert seen == 2 * len(self.SWEEP), seen


# ======================================================================
class TestTheClosedFormWithZeroFriction:
    """The anchor, and the class that discriminates.

    With φ' = 0 the frictional term is identically zero, so N never enters
    and the moment balance collapses to a ratio of two sums:

        bare      F = Σc·l / D
        active    F = Σc·l / (D − T)
        passive   F = (Σc·l + T) / D

    with ``D = Σ slide_sign·W·weight_arm_ratio``. Nothing on the right-hand
    side comes out of the solver, and the bare case is the control that
    ``D`` and ``Σc·l`` are what this file says they are — without it, a
    wrong ``D`` and a wrong ``T`` could agree with each other.
    """

    COH = 8.0
    METHODS = ("bishop_simplified", "ordinary_fellenius")

    def test_the_bare_slope_is_the_ratio_of_two_sums(self):
        surf = _circle()
        p = _bare(self.COH, 0.0)
        for n in (20, 50, 200):
            sl = _slices(p, surf, n)
            sign = _slide_sign(sl.slices)
            want = (_cohesion_moment(sl.slices, self.COH)
                    / _driving_no_support(sl.slices, sign))
            for mid in self.METHODS:
                got = _fos(mid, p, surf, sl)
                assert abs(got / want - 1.0) < 1e-12, (mid, n, got, want)

    def _expected(self, project, sl, active):
        sign = _slide_sign(sl.slices)
        num = _cohesion_moment(sl.slices, self.COH)
        den = _driving_no_support(sl.slices, sign)
        t = math.fsum(_exact_over_r(e, sign)
                      for e in _effects(project, _circle(), sl))
        return num / (den - t) if active else (num + t) / den

    def _run(self, project, active, tol=1e-9):
        surf = _circle()
        for n in (20, 50, 200):
            sl = _slices(project, surf, n)
            want = self._expected(project, sl, active)
            for mid in self.METHODS:
                got = _fos(mid, project, surf, sl)
                assert abs(got / want - 1.0) < tol, (mid, n, got, want)

    def test_an_active_support_subtracts_its_exact_moment(self):
        for build in (_horizontal, _inclined):
            self._run(_zero_phi(build()), True)

    def test_a_passive_support_adds_its_exact_moment(self):
        from ogr_core.support import ForceApplication
        for build in (_horizontal, _inclined):
            self._run(_zero_phi(build(ForceApplication.PASSIVE)), False)

    def test_the_chord_form_misses_by_a_hundred_tolerances(self):
        """The control: if the two forms agreed, the case above would pass
        without measuring anything."""
        surf = _circle()
        for build in (_horizontal, _inclined):
            p = _zero_phi(build())
            sl = _slices(p, surf, 50)
            sign = _slide_sign(sl.slices)
            num = _cohesion_moment(sl.slices, self.COH)
            den = _driving_no_support(sl.slices, sign)
            t_c = math.fsum(_chord_over_r(e, sl.slices, sign)
                            for e in _effects(p, surf, sl))
            exact = self._expected(p, sl, True)
            chord = num / (den - t_c)
            assert abs(chord / exact - 1.0) > 1e-4, (chord, exact)


def _zero_phi(project):
    """The same project with φ' = 0, so the closed form applies."""
    from ogr_core.materials import Material, MohrCoulomb
    project.materials = [Material(
        name="S", unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=8.0, friction_angle=0.0))]
    return project


# ======================================================================
class TestTheLoadAndTheSupportAreOneStatement:
    """The independent control, and the one this file would fail on if the
    design were wrong.

    The same horizontal force, at the same point, must give the same factor
    of safety whether it arrives as a SUPPORT or as a LOAD. That is the
    definition of a free body, and OGR reaches the two through different
    code: a support through ``resolve_support_terms``, a load through the
    slicer, which stores its horizontal part and the moment of that part
    about y = 0.

    The load side always had the exact arm. The support side did not, and
    ``test_efp_wall_v1122`` measured the gap as a residual that SHRANK with
    refinement — its own docstring naming the cause, "the chord angle of a
    slice against the angle at the point where the force is applied",
    forty versions before this ficha existed. With the arm exact there is
    nothing left to discretise: a horizontal force's ``support_vertical_load``
    is identically zero (``F_h·sin a·cos a − sin a·F_h·cos a``), so the two
    routes are the same algebra and the agreement is EXACT, not shrinking.
    """

    SPAN = 1.0

    def _pair(self, n):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import (DistributedLoad, LoadDistribution,
                                    LoadOrientation)
        from ogr_core.project import Project
        surf = _circle()
        ps = _zero_phi(_horizontal())
        sl = _slices(ps, surf, n)
        eff = _effects(ps, surf, sl)[0]
        p_load = _zero_phi(_ground(Project("load"), 8.0, 0.0))
        half = 0.5 * self.SPAN
        press = eff.force_h / self.SPAN
        p_load.distributed_loads = [DistributedLoad(
            start=Vertex(eff.intersection_x, eff.intersection_y + half),
            end=Vertex(eff.intersection_x, eff.intersection_y - half),
            magnitude_1=press, magnitude_2=press,
            distribution=LoadDistribution.CONSTANT,
            orientation=LoadOrientation.HORIZONTAL)]
        return ps, p_load, surf

    def test_the_resultant_and_its_height_are_the_same(self):
        ps, pl, surf = self._pair(50)
        sl = _slices(pl, surf, 50)
        f_h = math.fsum(s.water_force_h for s in sl.slices)
        m_h = math.fsum(s.water_force_h_moment for s in sl.slices)
        eff = _effects(ps, surf, _slices(ps, surf, 50))[0]
        assert abs(abs(f_h) - abs(eff.force_h)) < 1e-9, (f_h, eff.force_h)
        assert abs(m_h / f_h - eff.intersection_y) < 1e-9

    def test_the_two_moment_methods_agree_at_every_slice_count(self):
        for n in (20, 50, 200):
            ps, pl, surf = self._pair(n)
            for mid in ("bishop_simplified", "ordinary_fellenius"):
                a = _fos(mid, ps, surf, _slices(ps, surf, n))
                b = _fos(mid, pl, surf, _slices(pl, surf, n))
                assert abs(a / b - 1.0) < 1e-9, (mid, n, a, b)


# ======================================================================
class TestTheForceBranchStillTelescopes:
    """CONTROL, green on both sides of this change, and the reason the
    decomposition itself was NOT turned to the tangent.

    ``Σ t_active·sec a`` is the horizontal force the reinforcement delivers,
    and it comes out exactly right with the chord because the same angle
    appears in the projection and in the secant. Resolving the support on
    the arc while the slices still run on chords would have made this sum
    ``F_h·cos α_tangent/cos α_chord`` — off by the very 1.17 % this version
    is about, in the one branch that was already exact.
    """

    def test_the_secant_sum_is_the_horizontal_force(self):
        surf = _circle()
        for build in (_horizontal, _inclined):
            p = build()
            for n in (20, 50, 200):
                sl = _slices(p, surf, n)
                sign = _slide_sign(sl.slices)
                sup = _terms(p, surf, sl, sign)
                effs = _effects(p, surf, sl)
                want = math.fsum(
                    sign * (e.force_h + e.force_v
                            * math.tan(sl.slices[e.slice_index].base_angle))
                    for e in effs)
                got = math.fsum(
                    t / math.cos(s.base_angle)
                    for t, s in zip(sup.t_active, sl.slices) if t)
                assert abs(got / want - 1.0) < 1e-12, (n, got, want)


# ======================================================================
class TestWhatDoesNotMove:
    """The restriction the ficha states, held by assertions rather than by
    an argument: nothing but the circular moment arm."""

    def test_the_chord_decomposition_is_untouched(self):
        """Bit for bit, and the normal part still recomposes the force."""
        surf = _circle()
        for build in (_horizontal, _inclined):
            p = build()
            sl = _slices(p, surf, 50)
            sign = _slide_sign(sl.slices)
            sup = _terms(p, surf, sl, sign)
            fh = fv = 0.0
            for eff in _effects(p, surf, sl):
                i = eff.slice_index
                a = sl.slices[i].base_angle
                t_r = sign * (eff.force_h * math.cos(a)
                              + eff.force_v * math.sin(a))
                t_n = eff.force_h * math.sin(a) - eff.force_v * math.cos(a)
                assert sup.t_active[i] == t_r, (sup.t_active[i], t_r)
                assert sup.n_press[i] == t_n, (sup.n_press[i], t_n)
                fh, fv = eff.force_h, eff.force_v
                # the normal part in cartesians is the rotation back
                assert abs(sup.nf_h[i] - t_n * math.sin(a)) < 1e-12
                assert abs(sup.nf_v[i] + t_n * math.cos(a)) < 1e-12

    def test_a_plane_falls_back_to_the_chord_sum(self):
        """On a surface with no centre the new field IS the old sum —
        ``==``, not a tolerance. A default of zero would have deleted the
        reinforcement in silence, which is the lesson of D94."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipSurface
        poly = Polyline(vertices=[Vertex(TOE, 0.0), Vertex(52.0, H)])
        surf = SlipSurface(polyline=poly)
        for build in (_horizontal, _inclined):
            p = build()
            sl = _slices(p, surf, 40)
            sup = _terms(p, surf, sl, _slide_sign(sl.slices))
            if not sup.present:
                continue
            assert sup.moment_active == sup.total_active_t()
            assert sup.moment_passive == sup.total_passive_t()

    def test_a_slope_with_no_support_cannot_be_touched(self):
        """``resolve_support_terms`` returns before allocating anything."""
        from ogr_slip2d.support_integration import resolve_support_terms
        surf = _circle()
        p = _bare()
        sl = _slices(p, surf, 50)
        sup = resolve_support_terms(p, surf, sl, 1.0)
        assert not sup.present
        assert sup.moment_active == 0.0 and sup.moment_passive == 0.0


# ======================================================================
class TestTheResidualThatRemains:
    """What D144 does NOT close, measured instead of assumed away.

    The crossing point comes from ``intersection_with_polyline`` against the
    polyline of CHORDS, so it sits inside the arc by about ``R·θ²/8``. The
    moment that costs is second order and it is named here so that whoever
    measures a non-zero residual later knows which term it is.
    """

    def test_the_crossing_sits_off_the_arc_and_closes_like_one_over_n_squared(self):
        surf = _circle()
        cx, cy, r = CIRCLE
        p = _inclined()
        far = []
        for n in (20, 40, 80):
            sl = _slices(p, surf, n)
            eff = _effects(p, surf, sl)[0]
            d = math.hypot(eff.intersection_x - cx,
                           eff.intersection_y - cy)
            far.append(abs(d - r))
        assert far[0] < 0.05 * r, far
        for a, b in zip(far, far[1:]):
            assert 2.5 < a / b < 6.0, far

    def test_the_residual_converges_and_the_defect_does_not(self):
        """The statement is not "the leftover is small" — on THIS fixture
        it is 28 % of the defect at 20 slices, because the crossing sits
        on a gentle stretch of arc where the chord error is mild. The
        statement is that they are different ORDERS and behave differently.

        Measured over n = 20 / 40 / 80 / 160 on the inclined anchor:

            residual   1.38e-4  3.30e-5  9.22e-6  1.61e-6   falls ~4x, O(1/n²)
            defect     4.93e-4  3.69e-4  9.03e-5  1.32e-4   does NOT fall

        The defect goes back UP between 80 and 160 slices, which is the
        same sign-flipping wander ``TestItIsNotTheChord`` measures, and it
        is why refining a mesh was never going to pay this off. On problem
        85 the separation is starker still: 0.007 % against 1.17 %.
        """
        surf = _circle()
        cx, cy, r = CIRCLE
        p = _inclined()
        res, defect = [], []
        for n in (20, 40, 80, 160):
            sl = _slices(p, surf, n)
            sign = _slide_sign(sl.slices)
            eff = _effects(p, surf, sl)[0]
            d = math.hypot(eff.intersection_x - cx, eff.intersection_y - cy)
            ax = cx + (eff.intersection_x - cx) * r / d
            ay = cy + (eff.intersection_y - cy) * r / d
            on_arc = sign * ((ax - cx) * eff.force_v
                             - (ay - cy) * eff.force_h) / r
            reported = _exact_over_r(eff, sign)
            chord = _chord_over_r(eff, sl.slices, sign)
            res.append(abs(reported / on_arc - 1.0))
            defect.append(abs(chord / reported - 1.0))
        for a, b in zip(res, defect):
            assert a < 0.5 * b, (res, defect)
        for a, b in zip(res, res[1:]):
            assert 2.5 < a / b < 6.5, res
        assert any(b > a for a, b in zip(defect, defect[1:])), defect
