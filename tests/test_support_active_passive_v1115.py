# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Active / Passive force application moves the number, in every method.

THE INVARIANT. Reinforcement enters the factor of safety on ONE of two
sides, and which one is a setting the user chooses:

    Active   F = (R + T_N·tanφ') / (D − T_S)
    Passive  F = (R + T_N·tanφ' + T_S) / D

``T_S`` is the support force projected on the base of the slice it crosses
and ``T_N`` the projection on the base normal. Only the TANGENTIAL term
changes sides; the normal one is in the numerator either way. The reference
publishes the pair twice over — once for moment equilibrium and once for
force equilibrium — and attributes them to Methods A and B of Duncan &
Wright (2005), chapter 8.

WHAT THIS FILE EXISTS TO STOP. Until v0.1.114 seven of the nine methods
answered the SAME NUMBER for the two settings. On a circle it was five
(Spencer, GLE, Lowe-Karafiath and the two Corps of Engineers); on a
non-circular surface it was seven, because Bishop and Ordinary handed
``t_active + t_passive`` to ``moment_terms`` as one lump on the driving
side. Measured on the reference's own Active/Passive case — Duncan & Wright
(2005) figure 6.34, verification problem 85, circle (14.778, 37.889)
R = 27.141, 50 slices — Bishop separated the two by 20 % and Spencer gave
1.932337 both times.

That is rule 7 of this project: a configurable control that cannot move the
result is worse than not having it, because the user believes the analysis
respects it.

THE ANCHORS, none of them a captured value:

* **A closed form.** With φ' = 0 on a circular surface the moment balance
  is ``F = Σc'·l·R / Σ W·x`` with no base normal and no inter-slice force in
  it, so EVERY moment method must return the same number — and with a
  purely tangential support of known capacity T that number is
  ``Σc'·l / (Σ W·arm − T)`` for Active and ``(Σc'·l + T) / Σ W·arm`` for
  Passive. Nothing on the right-hand side comes out of the solver.

* **An identity between three runs.** For a purely tangential support
  (T_N = 0) the three factors of safety — no support, Active, Passive —
  are three views of the same two sums, so

      F_pas = 1 + F_0 − F_0 / F_act

  identically. It is exact where R and D do not depend on F (Ordinary), and
  close where they do. Setting F_act = 1 in it gives F_pas = 1: the same
  identity the back-analysis of support force is validated against.

* **The reference's own directional statement**, published on the page that
  carries the four equations: *"In general, Passive support will always give
  a lower Factor of Safety than Active support."*

* **Cross-method consistency.** Spencer, GLE and Lowe-Karafiath solve
  complete equilibrium by three different routes and must agree with each
  other in PASSIVE as they already do in ACTIVE. Lowe-Karafiath reaches the
  Passive case a different way from the other two — it never forms a ratio,
  so its reinforcement is divided by F inside the marching recursion — and
  this is what catches the two implementations disagreeing.

A NOTE ON WHAT IS *NOT* ASSERTED HERE, because measuring it is what kept
this change honest. Spencer and GLE get a band against the closed form
rather than the 1e-9 of the ratio methods, and the residual is NOT the
support algebra. On the published circle of problem 85, with φ' = 0, where
Bishop reproduces the closed form exactly:

                       ACTIVE                 PASSIVE
                   before    after        before    after
    Spencer        +8.49 %   +8.41 %     +27.67 %   +4.29 %
    GLE            +0.80 %   +0.72 %     +18.63 %   +1.22 %
    Lowe-Karafiath +10.98 %  +10.98 %    +30.61 %   +5.87 %
    Corps #1        +4.15 %   +4.15 %    +22.57 %   +2.93 %

Two things to read there. The PASSIVE column is this change. The ACTIVE
column barely moves — which says the Active treatment these methods already
had WAS the reference's Eqn. 1 and 2 — and what it leaves behind is a
separate, older discrepancy: Spencer's λ search does not converge on that
circle (it reports so in ``error_message``, "no λ leaves the inter-slice
thrust in net compression") and falls back to the nearest F_f ≈ F_m. It is
+3.79 % off the same closed form there with NO reinforcement at all. The
three force-equilibrium methods are not bound by a moment identity in the
first place.
"""
from __future__ import annotations

import math

H = 12.0
TOE = 30.0
CREST = 50.0        # slope face from (30, 0) to (50, 12)
COHESION = 30.0     # kPa, the φ' = 0 fixture
FRICTION = 20.0     # degrees, the general fixture
#: kN per unit width, constant and known. Deliberately MODEST — it lifts
#: this fixture from F = 1.55 to 1.85 and no further. A capacity comparable
#: to the driving force makes the Active denominator (D − T_S) nearly vanish,
#: and then every method is reading the same ill-conditioned ratio: the three
#: complete-equilibrium methods spread 3.3 % at 60 kN/m and 1.5 % at 20, with
#: nothing about the support algebra different between the two.
CAPACITY = 20.0

#: Every method the registry offers. Not a hand-kept list on purpose: a
#: tenth method added later must face rule 7 too.
_SKIP: tuple = ()


def _method_ids():
    from ogr_slip2d.methods.base import method_registry
    return sorted(m for m in method_registry() if m not in _SKIP)


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)


def _project(application=None, friction=FRICTION, cohesion=8.0,
             capacity=CAPACITY):
    """A homogeneous slope, optionally with one TANGENTIAL support.

    ``UserDefined`` with a single table point, so the capacity is a datum of
    the test and not the outcome of a start-up calculation — the same reason
    verification problem 85 is modelled that way.

    ``TANGENT_TO_SLIP`` is not decoration either: it makes T_N exactly zero,
    which is what lets the closed forms above be written with one unknown
    instead of two.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceOrientation, SupportInstance,
                                  UserDefined)

    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("active-passive")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=cohesion,
                                                 friction_angle=friction))]
    if application is not None:
        p.support_types = [UserDefined(out_of_plane_spacing=1.0,
                                       points=[(0.0, capacity)])]
        p.supports = [SupportInstance(
            type_id="user_defined",
            head=Vertex(43.5, 8.0), tail=Vertex(54.0, 8.0),
            force_application=application,
            orientation=ForceOrientation.TANGENT_TO_SLIP)]
    return p


def _polyline(project):
    """A six-vertex polyline sampled from the circle above.

    Sampled rather than invented so it is guaranteed to daylight and to be
    crossed by the same support; kept to six vertices so it is genuinely
    non-circular and takes the general moment-axis path.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipSurface
    sl = slice_surface(project, _circle(), num_slices=30)
    pts = [(sl.slices[0].base_x_left, sl.slices[0].base_y_left)]
    pts += [(s.base_x_right, s.base_y_right) for s in sl.slices]
    keep = [pts[0], pts[6], pts[12], pts[18], pts[24], pts[-1]]
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in keep]))


def _fos(method_id, project, surface, num_slices=25):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return method_registry()[method_id]().compute_fos(project, surface, sl).fos


def _both(method_id, surface_of, **kw):
    """``(F_active, F_passive)`` for one method on one surface family."""
    from ogr_core.support import ForceApplication
    pa = _project(ForceApplication.ACTIVE, **kw)
    pp = _project(ForceApplication.PASSIVE, **kw)
    surf = surface_of(pa)
    return _fos(method_id, pa, surf), _fos(method_id, pp, surf)


_FAMILIES = (("circular", lambda p: _circle()),
             ("non-circular", _polyline))


# ======================================================================
class TestTheSettingMovesTheNumber:
    """Rule 7. Seven of the nine could not, and said nothing about it."""

    def test_every_method_separates_active_from_passive(self):
        for family, surface_of in _FAMILIES:
            for mid in _method_ids():
                fa, fp = _both(mid, surface_of)
                assert math.isfinite(fa) and math.isfinite(fp), (
                    f"{mid} on the {family} surface: {fa!r} / {fp!r}")
                # A tenth of a percent is far below the ~25 % this fixture
                # actually produces, and far above any convergence noise.
                assert abs(fa - fp) / fa > 1e-3, (
                    f"{mid} on the {family} surface answers {fa:.6f} for "
                    f"Active and {fp:.6f} for Passive: the setting does "
                    f"nothing")

    def test_a_support_that_misses_the_surface_is_indifferent(self):
        """The cheapest way to catch a term added on the wrong side: with
        nothing crossing the slip surface the two settings are the same
        analysis, and both must equal the unreinforced run."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import ForceApplication
        f0 = {}
        for mid in _method_ids():
            f0[mid] = _fos(mid, _project(), _circle())
        for app in (ForceApplication.ACTIVE, ForceApplication.PASSIVE):
            p = _project(app)
            # Well below the toe, so no trial surface reaches it.
            p.supports[0].head = Vertex(5.0, -8.0)
            p.supports[0].tail = Vertex(15.0, -8.0)
            for mid in _method_ids():
                got = _fos(mid, p, _circle())
                assert abs(got - f0[mid]) < 1e-9, (
                    f"{mid}: a support that crosses nothing moved "
                    f"{f0[mid]!r} to {got!r} in {app.value}")


# ======================================================================
class TestPassiveNeverBeatsActive:
    """*"In general, Passive support will always give a lower Factor of
    Safety than Active support"* — the reference's own page, and it follows
    from the two equations: with F > 1, ``(R+T)/D < R/(D−T)``."""

    def test_passive_is_the_lower_of_the_two(self):
        for family, surface_of in _FAMILIES:
            for mid in _method_ids():
                fa, fp = _both(mid, surface_of)
                assert fp < fa, (
                    f"{mid} on the {family} surface: passive {fp:.6f} is "
                    f"not below active {fa:.6f}")


# ======================================================================
class TestTheClosedFormWithZeroFriction:
    """φ' = 0 on a circle: the factor of safety is a ratio of two sums the
    test computes itself, and every moment method must land on it.

    No base normal appears in it and no inter-slice force does either, which
    is exactly why it discriminates: a method that lets the reinforcement
    perturb the base normal cannot reproduce it. Spencer was +8.2 % out in
    Active and +27.6 % in Passive before v0.1.115.
    """

    _MOMENT = ("ordinary_fellenius", "bishop_simplified", "spencer",
               "gle_morgenstern_price")

    def _sums(self):
        """``(Σc'·l, Σ W·(x − x_c)/R)`` from the slice geometry alone."""
        from ogr_slip2d.slicer import slice_surface
        circ = _circle()
        p = _project(friction=0.0, cohesion=COHESION)
        sl = slice_surface(p, circ, num_slices=40)
        resisting = math.fsum(COHESION * s.base_length for s in sl.slices)
        driving = math.fsum(
            s.weight * (0.5 * (s.base_x_left + s.base_x_right)
                        - circ.centre_x) / circ.radius
            for s in sl.slices)
        return resisting, driving

    def _check(self, application, expected, tol_ratio, tol_rigorous):
        got = {}
        p = _project(application, friction=0.0, cohesion=COHESION)
        for mid in self._MOMENT:
            got[mid] = _fos(mid, p, _circle(), num_slices=40)
        for mid, value in got.items():
            tol = (tol_ratio if mid in ("ordinary_fellenius",
                                        "bishop_simplified")
                   else tol_rigorous)
            err = abs(value - expected) / expected
            assert err < tol, (
                f"{mid} answers {value:.6f} where the closed form is "
                f"{expected:.6f} ({100 * err:+.3f} %)")

    def test_without_reinforcement_every_moment_method_agrees(self):
        r, d = self._sums()
        self._check(None, r / d, 1e-9, 1e-3)

    def test_active_takes_the_capacity_off_the_driving_side(self):
        r, d = self._sums()
        self._check_application("active", r / (d - CAPACITY))

    def test_passive_adds_the_capacity_to_the_resisting_side(self):
        r, d = self._sums()
        self._check_application("passive", (r + CAPACITY) / d)

    def _check_application(self, which, expected):
        from ogr_core.support import ForceApplication
        app = (ForceApplication.ACTIVE if which == "active"
               else ForceApplication.PASSIVE)
        # 2.5 % for the two λ-search methods: see the module docstring on
        # why the residual is the λ fallback and not the support algebra.
        self._check(app, expected, 1e-9, 0.025)

    def test_the_capacity_reaching_the_base_is_the_capacity_declared(self):
        """The premise the two tests above rest on. A TANGENT_TO_SLIP
        support puts its whole magnitude on the base and nothing on the
        normal, so ``T_S`` is the number the fixture wrote down."""
        from ogr_core.support import ForceApplication
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms
        circ = _circle()
        for app, attr in ((ForceApplication.ACTIVE, "t_active"),
                          (ForceApplication.PASSIVE, "t_passive")):
            p = _project(app, friction=0.0, cohesion=COHESION)
            sl = slice_surface(p, circ, num_slices=40)
            sup = resolve_support_terms(p, circ, sl, 1.0)
            assert sup.present
            t_s = math.fsum(getattr(sup, attr))
            other = math.fsum(getattr(
                sup, "t_passive" if attr == "t_active" else "t_active"))
            assert abs(t_s - CAPACITY) < 1e-6, (t_s, CAPACITY)
            assert abs(other) < 1e-12, other
            assert abs(math.fsum(sup.n_press)) < 1e-6, (
                f"a tangential support reported T_N = "
                f"{math.fsum(sup.n_press):.6g}")


# ======================================================================
class TestTheThreeRunIdentity:
    """``F_pas = 1 + F_0 − F_0 / F_act`` for a purely tangential support.

    Eliminating R and T from ``F_0 = R/D``, ``F_act = R/(D−T)`` and
    ``F_pas = (R+T)/D`` leaves no free parameter at all. Setting F_act = 1
    gives F_pas = 1, which is the identity the back-analysis of support
    force is checked against.

    Exact only where R and D are independent of F, which among these nine is
    Ordinary alone: every other method has the factor of safety inside its
    own resisting sum. Before v0.1.115 the five methods that ignored the
    setting were ~40 % off this relation, so the 3 % band below still
    separates the two states by more than a decimal order.
    """

    def _rows(self, surface_of):
        from ogr_core.support import ForceApplication
        p0 = _project()
        pa = _project(ForceApplication.ACTIVE)
        pp = _project(ForceApplication.PASSIVE)
        surf = surface_of(pa)
        for mid in _method_ids():
            f0 = _fos(mid, p0, surf)
            fa = _fos(mid, pa, surf)
            fp = _fos(mid, pp, surf)
            yield mid, f0, fa, fp, 1.0 + f0 - f0 / fa

    def test_ordinary_satisfies_it_exactly(self):
        for mid, f0, fa, fp, expected in self._rows(lambda p: _circle()):
            if mid != "ordinary_fellenius":
                continue
            assert abs(fp - expected) / expected < 1e-9, (
                f"F0 {f0:.8f}, F_act {fa:.8f}: F_pas is {fp:.8f} where the "
                f"identity gives {expected:.8f}")

    def test_every_method_stays_within_three_percent_of_it(self):
        for family, surface_of in _FAMILIES:
            for mid, _f0, fa, fp, expected in self._rows(surface_of):
                err = abs(fp - expected) / expected
                assert err < 0.03, (
                    f"{mid} on the {family} surface: F_pas {fp:.6f} against "
                    f"the identity's {expected:.6f} ({100 * err:+.2f} %); "
                    f"F_act was {fa:.6f}")


# ======================================================================
class TestTheCompleteEquilibriumMethodsAgreeInPassive:
    """Spencer, GLE and Lowe-Karafiath reach Passive by two different
    routes — the first two move the term across the fraction bar, the third
    divides the reinforcement by F inside its marching recursion because it
    never forms a ratio to move anything across. They are each other's only
    reference here, and a disagreement means the two routes are not the same
    equation."""

    _THREE = ("spencer", "gle_morgenstern_price", "lowe_karafiath")

    def _spread(self, application):
        vals = [_fos(mid, _project(application), _circle())
                for mid in self._THREE]
        return vals, (max(vals) - min(vals)) / min(vals)

    def test_they_agree_in_active(self):
        from ogr_core.support import ForceApplication
        vals, spread = self._spread(ForceApplication.ACTIVE)
        assert spread < 0.02, dict(zip(self._THREE, vals))

    def test_they_agree_in_passive_too(self):
        from ogr_core.support import ForceApplication
        vals, spread = self._spread(ForceApplication.PASSIVE)
        assert spread < 0.02, dict(zip(self._THREE, vals))


# ======================================================================
class TestVerificationProblem85:
    """The reference's own Active/Passive case: Duncan & Wright (2005)
    figure 6.34, a 20 ft saturated-clay slope with one horizontal 9000 lb/ft
    tieback at mid-height.

    Evaluated on the ONE surface the manual publishes for it — the panel of
    figure 85.2, GLE/Morgenstern-Price, centre (15.446, 37.624) R 27.594 —
    because comparing a method against a factor of safety obtained on a
    different surface measures two things at once. The manual gives 1.575
    there for the Active case.

    Its Passive figure, 1.378, sits on a critical surface the manual does
    NOT publish, so it is quoted as an order of magnitude and not asserted
    tightly. What IS asserted is the closed form: φ' = 0 makes the moment
    balance a ratio of two sums, so Bishop and GLE must agree on this circle
    in both settings whatever the manual says. They were 18.63 % apart in
    Passive until v0.1.115 and are 1.22 % apart now.

    READ THIS BEFORE DEBUGGING A FAILURE HERE. **The λ search does not
    converge on this circle**, with reinforcement or without it. Both Spencer
    and GLE come back with ``converged=False`` and the message "no λ leaves
    the inter-slice thrust in net compression", and what they return is the
    nearest F_f ≈ F_m fallback. Measured: the φ' = 0 closed form for the
    Active case is 1.5708 at 200 slices and Spencer answers 1.7012, +8.3 %;
    with no support at all it is +3.79 % off. So the two assertions below are
    anchored on a FALLBACK VALUE, and they are here for what they do catch —
    the setting moving the number by more than a tenth, and GLE landing near
    the published figure — not as a measurement of the formulation. If one of
    them moves, look at the λ search first: an experiment in v0.1.115 that
    changed only the reinforcement's place in the slice equilibrium swung GLE
    here from +0.14 % to −8.62 % without touching anything this class is
    about. The bands are 2 % and 1.5 % for that reason and tightening them
    would be asserting the stability of a fallback.
    """

    CENTRE = (15.446, 37.624)
    RADIUS = 27.594
    PUBLISHED_ACTIVE = 1.575

    def _project(self, application):
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_core.support import (ForceOrientation, SupportInstance,
                                      UserDefined)
        # Imperial units throughout: ft, psf, pcf.
        ext = Polyline(vertices=[Vertex(15, 10), Vertex(57, 10),
                                 Vertex(57, 30), Vertex(25, 30)],
                       closed=True)
        ext.ensure_ccw()
        p = Project("p85")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="saturated clay", unit_weight=98.0,
                                strength=MohrCoulomb(cohesion=350.0,
                                                     friction_angle=0.0))]
        p.support_types = [UserDefined(out_of_plane_spacing=1.0,
                                       points=[(0.0, 9000.0)])]
        p.supports = [SupportInstance(
            type_id="user_defined",
            head=Vertex(20.0, 20.0), tail=Vertex(57.0, 20.0),
            force_application=application,
            orientation=ForceOrientation.HORIZONTAL)]
        return p

    def _surface(self):
        from ogr_slip2d.surface import SlipCircle
        return SlipCircle(centre_x=self.CENTRE[0], centre_y=self.CENTRE[1],
                          radius=self.RADIUS)

    def _fos(self, method_id, application):
        return _fos(method_id, self._project(application), self._surface(),
                    num_slices=100)

    def test_gle_reproduces_the_published_active_factor(self):
        from ogr_core.support import ForceApplication
        got = self._fos("gle_morgenstern_price", ForceApplication.ACTIVE)
        err = (got - self.PUBLISHED_ACTIVE) / self.PUBLISHED_ACTIVE
        assert abs(err) < 0.02, (
            f"GLE gives {got:.6f} on the published circle against "
            f"{self.PUBLISHED_ACTIVE} ({100 * err:+.2f} %)")

    def test_the_setting_moves_it_by_more_than_a_tenth(self):
        """The manual separates its own Bishop pair by 13.5 % and its GLE
        pair by 12.5 %. Anything of that order is the point; the equality to
        six digits that stood until v0.1.114 is not."""
        from ogr_core.support import ForceApplication
        fa = self._fos("gle_morgenstern_price", ForceApplication.ACTIVE)
        fp = self._fos("gle_morgenstern_price", ForceApplication.PASSIVE)
        assert (fa - fp) / fa > 0.10, (fa, fp)

    def test_bishop_and_gle_agree_on_this_circle_in_both_settings(self):
        """φ' = 0 makes the moment balance a ratio of two sums with no base
        normal in it, so a simplified method and a complete-equilibrium one
        have nothing left to differ about. GLE was 0.80 % from Bishop in
        Active and 18.63 % in Passive; it is 0.72 % and 1.22 % now."""
        from ogr_core.support import ForceApplication
        for app in (ForceApplication.ACTIVE, ForceApplication.PASSIVE):
            b = self._fos("bishop_simplified", app)
            g = self._fos("gle_morgenstern_price", app)
            assert abs(b - g) / b < 0.015, (
                f"{app.value}: Bishop {b:.6f} against GLE {g:.6f}")
