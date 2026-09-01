# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
On a PLANE the sliding mass is one free body, so every method that closes
global force equilibrium owes the same number — and that number is written
in closed form.

WHAT INVARIANT THIS PROTECTS

For a planar surface at a single angle α the whole mass is a rigid wedge.
Limit equilibrium of a wedge is two equations in two unknowns and has one
answer (Coulomb 1776; the modern statement is Duncan & Wright 2005 §6),
with a support force resolved onto the base as ``T_S`` and ``T_N``:

    ACTIVE   F = ( c'·L + (W·cos α + T_N)·tan φ' ) / (W·sin α − T_S)
    PASSIVE  F = ( c'·L + (W·cos α + T_N)·tan φ' + T_S ) / (W·sin α)

Nothing in that is a convention. Interslice forces are internal to the
wedge and cancel in the sum, so whatever a method assumes about them
cannot change the answer. **Six of the nine are bound by it**: Janbu
Simplified, Janbu Corrected (f₀ = 1 on a plane — see below), the two Corps
of Engineers, Lowe-Karafiath and, since they satisfy force equilibrium
too, Spencer and GLE. Bishop and Ordinary/Fellenius write a MOMENT
equation, so on a plane they are not obliged — and Ordinary passes anyway,
because its ``N = W·cos α + T_N`` is exact here.

Of those, four reproduce it to the last digit and always have: the two
Corps methods, Lowe-Karafiath and Ordinary. They are the control. Spencer
and GLE do not, and that is a separate anomaly reported below.

WHY THIS FILE EXISTS: THE JANBU HALF OF D46

A support and a line load of the same magnitude, at the same point, at the
same angle, gave two different factors of safety. Bishop's half of that
closed in v0.1.137 by resolving the support's normal part inside the
slice's own vertical equilibrium instead of bolting ``T_N·tan φ'`` on
outside ``m_α``. The two Janbu did not follow, and the note at the term in
``ogr_slip2d/methods/janbu.py`` measured four possible combinations and
stopped, in writing, because *"choosing between them needs external
evidence this task does not have"*.

The evidence was not a published number. It is the wedge above, and the
derivation that leads to it. Janbu's balance is ``Σ S·sec α = Σ W·tan α``;
putting an external force ``P = (P_h, P_v)`` on a slice into that balance,

    Σ (W − P_v)·tan α  +  Σ P_h   =   Σ S·sec α

and since ``T_S = slide_sign·(P_h·cos α + P_v·sin α)``, the support owes the
driving side exactly ``−T_S·sec α`` — with its normal part arriving through
``W_eff``, which is what :func:`support_integration.support_vertical_load`
already returns (``down = −P_v``, term for term). Substituting that pair
into Janbu's form on a plane cancels down to the wedge above, for ACTIVE
and for PASSIVE alike. The combination that satisfies the identity is
therefore the combination that is exact, and the other three are not
choices.

AND ONE THING THIS FILE PROVES THAT THE CIRCLE COULD NOT

For Janbu the two channels turn out to be the SAME two terms per slice, so
the load-equals-support identity holds exactly rather than by shrinking —
0.0, 0.0, −1.4e-14 % at 25 / 100 / 400 slices where Bishop, Ordinary and
Spencer carry a mesh residual of 0.087 % falling to 0.002 %. Only the
marching methods, which rebuild the cartesian resultant, are in the same
company. An exact zero is a stronger statement than a shrinking one, and
it is the closing evidence for D46.

MEASURED ON THIS FIXTURE, BEFORE THE CHANGE (v0.1.141)

Error against the closed form, ACTIVE support, 50 slices:

    plane        35°       40°       45°       50°
    Corps #1  +0.000 %  +0.000 %  +0.000 %  +0.000 %
    Lowe-K    +0.000 %  +0.000 %  +0.000 %  +0.000 %
    Ordinary  −0.000 %  +0.000 %  −0.000 %  +0.000 %
    Janbu     +1.934 %  +1.960 %  −0.805 %  −20.013 %

and with the SAME fixture unreinforced, Janbu sits at −0.022 %, +0.051 %,
+0.062 %, +0.033 %. The disagreement is the support term and nothing else,
which is why the unreinforced case is asserted here as a control rather
than assumed.

WHAT THIS FILE DOES NOT CLAIM

Nothing about Bishop on a plane. It writes a moment equation, the wedge
does not bind it, and it measures −5.6 % to +17.7 % here with support and
−0.3 % to +6.4 % WITHOUT any support at all. That second column is the
point: it is not a support defect, it is what a method of moments does on
a surface with no centre, and this file must not become a reason to
"correct" it.

Nothing about Spencer and GLE against the wedge, and that one IS an
anomaly rather than a derivation. They are bound by it and they miss it,
and the giveaway is that tightening the convergence tolerance moves them
AWAY: on the 50° plane with NO support the error grows from +6.7e-4 at the
shipped 1e-3 to +2.8e-2 at 1e-10, forty times worse for a solve forty
times more converged, while Corps #1 sits at 5e-10 at both. Since it is
there unreinforced it is not this defect. It is measured and frozen in
``TestSpencerAndGleDoNotSettleOnTheWedge`` rather than fixed here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_support_noncircular_v1140 import (  # noqa: E402
    SWEEP, _circle, _gap, _polyline,
)

# ----------------------------------------------------------------------
# A slope steep enough that planes of 35° to 50° daylight on the crest,
# so ``sec α`` runs from 1.22 to 1.56 and the term under discussion is not
# a rounding error. The v1140 slope (31°) cannot host any of them.
# ----------------------------------------------------------------------
H, TOE, CREST = 12.0, 30.0, 38.0        # a 56.3° face
COH, PHI, GAMMA = 5.0, 30.0, 18.0

#: Anchor head ON the face (the ground at x = 34 is exactly 6.0), running
#: up into the slope. Its FORCE is inclined 15° above the horizontal:
#: not horizontal, so the vertical load on the crossed slice is not
#: identically zero, and not along the base either, so ``T_S`` and ``T_N``
#: are both alive. Every earlier support fixture misses one of the two —
#: see the header of ``test_support_noncircular_v1140``.
XS, YS = 34.0, 6.0
TAIL = (48.0, 11.0)
ANGLE_DEG = 15.0
CAPACITY = 120.0

#: Plane angles. 35-45° is where every force method is measured to hold;
#: 50° is included for the exact three plus Janbu only, and the header
#: says why.
BETAS = (35.0, 40.0, 45.0)
BETA_STEEP = 50.0
NSLICES = 50

#: The three that reproduce the wedge to the last digit today, on every
#: angle, with and without support. They are the control: if Janbu were
#: the only one that could not, and they moved too, the cause would be the
#: fixture rather than the method.
EXACT = ("corps_engineers_1", "corps_engineers_2", "lowe_karafiath",
         "ordinary_fellenius")

#: The two that satisfy force equilibrium through a coupled (F, λ) solve.
#: They are bound by the wedge in principle and are NOT asserted against it
#: here — see ``TestSpencerAndGleDoNotSettleOnTheWedge`` and the header.
COMPLETE = ("spencer", "gle_morgenstern_price")

JANBU = ("janbu_simplified", "janbu_corrected")

#: Convergence tolerance for the closed-form assertions, and it has to be
#: said out loud. ``LEMMethod`` defaults to 1e-3 ABSOLUTE, which on a factor
#: of safety of 1.3 is 2e-4 RELATIVE — larger than any formulation term
#: worth arguing about. Ordinary is non-iterative and the marching methods
#: find a root, so they land on the wedge at the default; the two Janbu
#: iterate, and at the default they sit 2e-4 below it. That residual is the
#: iteration and nothing else, which ``TestTheResidualIsTheIteration``
#: asserts by watching it collapse rather than by claiming it.
TIGHT = 1e-10
MAX_IT = 400

#: Relative tolerance for a closed form the arithmetic reproduces exactly.
#: At :data:`TIGHT` the two Janbu sit at 1e-13 and the marching methods'
#: root finders at 2e-9. 1e-7 clears both by two decades and still sits
#: FIVE decades below the smallest term this file adjudicates (Janbu's
#: 0.8 % at 45°), so it cannot be met by accident.
TOL_EXACT = 1e-7
TOL_COMPLETE = 2e-3


# ----------------------------------------------------------------------
def _ground(project):
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
        strength=MohrCoulomb(cohesion=COH, friction_angle=PHI))]
    return project


def _bare():
    from ogr_core.project import Project
    return _ground(Project("bare"))


def _anchored(application=None):
    from ogr_core.geometry import Vertex
    from ogr_core.project import Project
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _ground(Project("anchored"))
    p.support_types = [EndAnchored(anchor_capacity=CAPACITY,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(XS, YS), tail=Vertex(*TAIL),
        force_application=application or ForceApplication.ACTIVE,
        orientation=ForceOrientation.USER_DEFINED,
        user_angle_deg=ANGLE_DEG)]
    return p


def _plane(beta_deg):
    """A plane through the toe, daylighting on the crest plateau."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _daylight_x(beta_deg):
    return TOE + H / math.tan(math.radians(beta_deg))


def _exact_weight(beta_deg):
    """W of the wedge from GEOMETRY alone — no slicer, no method.

    The mass is the triangle (toe, daylight point, crest), so its area is
    ``½·H·(x_daylight − x_crest)``. This is what keeps the closed form
    below from leaning on the very slicer it is meant to police.
    """
    return GAMMA * 0.5 * H * (_daylight_x(beta_deg) - CREST)


def _slices(project, surface, n=NSLICES):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=n)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return sl


def _fos(method_id, project, surface, n=NSLICES, tolerance=TIGHT):
    from ogr_slip2d.methods.base import method_registry
    method = method_registry()[method_id](tolerance=tolerance,
                                          max_iterations=MAX_IT)
    return method.compute_fos(project, surface,
                              _slices(project, surface, n)).fos


def _terms(project, surface, n=NSLICES):
    """``(T_N, T_S_active, T_S_passive)`` as the solvers receive them."""
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.support_integration import resolve_support_terms
    sl = _slices(project, surface, n)
    raw = sum(slice_forces(s, 0.0, 0.0).w_total * math.tan(s.base_angle)
              for s in sl.slices)
    sup = resolve_support_terms(project, surface, sl,
                                1.0 if raw >= 0 else -1.0)
    if not sup.present:
        return 0.0, 0.0, 0.0
    return (math.fsum(sup.n_press), sup.total_active_t(),
            sup.total_passive_t())


def _wedge(project, beta_deg, n=NSLICES):
    """The closed form. ``W`` and ``L`` from geometry, ``T`` from the model."""
    surface = _plane(beta_deg)
    a = math.radians(beta_deg)
    W = _exact_weight(beta_deg)
    L = H / math.sin(a)
    t_n, t_act, t_pas = _terms(project, surface, n)
    num = COH * L + (W * math.cos(a) + t_n) * math.tan(math.radians(PHI))
    return (num + t_pas) / (W * math.sin(a) - t_act)


def _err(method_id, project, beta_deg, n=NSLICES, tolerance=TIGHT):
    """Relative error of a method against the closed form."""
    w = _wedge(project, beta_deg, n)
    return (_fos(method_id, project, _plane(beta_deg), n, tolerance) - w) / w


def _both():
    from ogr_core.support import ForceApplication
    return (("active", _anchored(ForceApplication.ACTIVE)),
            ("passive", _anchored(ForceApplication.PASSIVE)))


# ======================================================================
class TestTheFixtureIsWhatItClaims:
    """Every premise the closed form rests on, asserted rather than
    assumed. Two of them have already been wrong once in this project: a
    support fixture whose force was horizontal (so half the term was
    identically zero) and one whose φ' was zero (so the other half was)."""

    def test_the_surface_really_is_a_single_plane(self):
        for beta in BETAS + (BETA_STEEP,):
            sl = _slices(_bare(), _plane(beta))
            angles = [abs(s.base_angle) for s in sl.slices]
            spread = max(angles) - min(angles)
            assert spread < 1e-12, (beta, spread)
            assert abs(math.degrees(angles[0]) - beta) < 1e-9, beta

    def test_the_weight_is_the_geometry_and_not_the_slicer(self):
        """What makes the closed form an external anchor: ``W`` and ``L``
        come from the triangle, and the slicer has to agree with them."""
        from ogr_slip2d.external_forces import slice_forces
        for beta in BETAS + (BETA_STEEP,):
            sl = _slices(_bare(), _plane(beta))
            w = math.fsum(slice_forces(s, 0.0, 0.0).w_total
                          for s in sl.slices)
            length = math.fsum(s.base_length for s in sl.slices)
            assert abs(w - _exact_weight(beta)) < 1e-6 * w, (beta, w)
            assert abs(length - H / math.sin(math.radians(beta))) < 1e-9, beta

    def test_both_halves_of_the_support_are_alive(self):
        """``T_S`` and ``T_N`` both non-trivial, at every angle. A
        horizontal force would kill the vertical load and a base-parallel
        one would kill ``T_N``; this fixture does neither."""
        for _name, p in _both():
            for beta in BETAS + (BETA_STEEP,):
                t_n, t_act, t_pas = _terms(p, _plane(beta))
                t_s = t_act + t_pas
                assert t_n > 0.1 * CAPACITY, (beta, t_n)
                assert t_s > 0.5 * CAPACITY, (beta, t_s)

    def test_the_janbu_correction_is_one_on_a_plane(self):
        """f₀ = 1 + b₁·(d/L − 1.4·(d/L)²) with ``d`` the largest offset
        from the chord — and on a plane the chord IS the surface. Asserted
        because the whole file compares Janbu Corrected to the same wedge
        as Janbu Simplified."""
        for beta in BETAS + (BETA_STEEP,):
            for _name, p in _both():
                a = _fos("janbu_simplified", p, _plane(beta))
                b = _fos("janbu_corrected", p, _plane(beta))
                assert abs(b - a) < 1e-12 * a, (beta, a, b)


# ======================================================================
class TestTheClosedFormOnAPlane:
    """The anchor. Six methods, one number, no published value involved."""

    def test_the_three_exact_methods_reproduce_it(self):
        """The control, and the reason the rest of the file is readable:
        if these moved, the fixture would be wrong, not the method."""
        for name, p in _both():
            for beta in BETAS + (BETA_STEEP,):
                for mid in EXACT:
                    e = _err(mid, p, beta)
                    assert abs(e) < TOL_EXACT, (name, beta, mid, e)

    def test_they_reproduce_it_unreinforced_too(self):
        for beta in BETAS + (BETA_STEEP,):
            for mid in EXACT:
                e = _err(mid, _bare(), beta)
                assert abs(e) < TOL_EXACT, (beta, mid, e)

    def test_both_janbu_reproduce_it(self):
        """The defect. Before v0.1.142 this failed by +1.93 %, +1.96 %,
        −0.81 % and −20.01 % on the four ACTIVE angles, and by +1.53 %,
        +1.69 %, +0.58 % and −4.29 % on the PASSIVE ones."""
        for name, p in _both():
            for beta in BETAS + (BETA_STEEP,):
                for mid in JANBU:
                    e = _err(mid, p, beta)
                    assert abs(e) < TOL_EXACT, (name, beta, mid, e)

    def test_janbu_already_reproduced_it_without_a_support(self):
        """The control that says the disagreement above is the support
        term and nothing else: unreinforced, the same method on the same
        planes is already exact."""
        for beta in BETAS + (BETA_STEEP,):
            for mid in JANBU:
                e = _err(mid, _bare(), beta)
                assert abs(e) < TOL_EXACT, (beta, mid, e)

    def test_bishop_is_not_bound_by_it_and_that_is_not_a_defect(self):
        """Written as an assertion so nobody 'fixes' Bishop against this
        file: it misses the wedge WITHOUT any support at all, which is
        what a method of moments does on a surface that has no centre."""
        worst = max(abs(_err("bishop_simplified", _bare(), beta))
                    for beta in BETAS + (BETA_STEEP,))
        assert worst > 1e-3, worst


# ======================================================================
class TestTheTrendIsWhatDiscriminates:
    """A formulation error leaves a trend across the angles; a geometry
    error does not. That argument decided v0.1.113 and it decides here —
    only now it is measured against a closed form instead of a published
    column, so there is no geometry left to blame."""

    def test_the_janbu_error_used_to_run_with_the_plane_angle(self):
        """The three exact methods are flat at zero across the sweep. If
        Janbu's error were the mesh, it would be flat too."""
        for _name, p in _both():
            errs = [_err("janbu_simplified", p, beta)
                    for beta in BETAS + (BETA_STEEP,)]
            assert max(errs) - min(errs) < TOL_EXACT, errs

    def test_refining_the_mesh_does_not_change_the_answer(self):
        """On a plane every slice has the same angle, so there is no
        chord-versus-tangent residual to shrink: the closed form must come
        out at any slice count. That is what separates this anchor from
        the load-equals-support identity below."""
        from ogr_core.support import ForceApplication
        p = _anchored(ForceApplication.PASSIVE)
        for n in (10, 50, 200):
            for mid in ("janbu_simplified", "corps_engineers_1"):
                e = _err(mid, p, 40.0, n)
                assert abs(e) < TOL_EXACT, (n, mid, e)


# ======================================================================
class TestSpencerAndGleDoNotSettleOnTheWedge:
    """An anomaly found while writing this file, asserted as a FACT with a
    band rather than as a target. If it is ever fixed these tests fail and
    what is written here has to be rewritten — which is the point.

    Spencer and GLE close global force equilibrium, so on a plane the wedge
    binds them exactly as it binds the four in :data:`EXACT`. They do not
    meet it, and the giveaway is that TIGHTENING the convergence tolerance
    moves them AWAY from it: on the 50° plane with no support at all, the
    error grows from +6.7e-4 at the default 1e-3 to +2.8e-2 at 1e-10 —
    forty times worse for a solve that is supposed to be forty times more
    converged. Corps #1 sits at 5e-10 at both, and Janbu now goes from
    2e-5 to 2e-12.

    Two things are already known and neither is a diagnosis:

      * it is NOT the support. The numbers above are the UNREINFORCED
        model, and the anomaly is there in full;
      * it is not monotone either — at 45° with an active support, GLE runs
        −1.9e-4, −1.0e-7, −8.3e-12 across the three tolerances while
        Spencer runs −6.6e-4, −1.1e-3, −2.7e-3.

    A coupled solve landing on a different point when the bracket tightens
    is what a SPURIOUS ROOT looks like, and this project has met one before
    (D10, v0.1.106). Named, measured, not touched by this version.
    """

    STEEP_UNREINFORCED = ((1e-3, 1e-3), (1e-10, 1e-2))

    def test_tightening_the_tolerance_makes_them_worse_not_better(self):
        for mid in COMPLETE:
            loose = abs(_err(mid, _bare(), BETA_STEEP, tolerance=1e-3))
            tight = abs(_err(mid, _bare(), BETA_STEEP, tolerance=1e-10))
            assert tight > 10.0 * loose, (mid, loose, tight)

    def test_the_methods_that_do_settle_are_the_control(self):
        """Same fixture, same tolerances: four methods flat, and Janbu
        collapsing. Without this the test above could be the fixture."""
        for mid in EXACT + ("janbu_simplified",):
            loose = abs(_err(mid, _bare(), BETA_STEEP, tolerance=1e-3))
            tight = abs(_err(mid, _bare(), BETA_STEEP, tolerance=1e-10))
            assert tight <= max(loose, 1e-8), (mid, loose, tight)

    def test_they_are_still_close_enough_at_the_default_to_be_quoted(self):
        """The size of it, so the finding is not read as worse than it is:
        at the tolerance OGR actually ships, both are within 3 % of the
        wedge on every plane here."""
        for name, p in _both():
            for beta in BETAS + (BETA_STEEP,):
                for mid in COMPLETE:
                    e = _err(mid, p, beta, tolerance=1e-3)
                    assert abs(e) < 3e-2, (name, beta, mid, e)


# ======================================================================
class TestTheResidualIsTheIteration:
    """Why the assertions above set a tolerance instead of taking the
    default, said as a measurement rather than as an excuse.

    At the class default of 1e-3 ABSOLUTE the two Janbu sit ~2e-4 below the
    wedge. Tightening the tolerance by five decades drops that by five
    decades — which a formulation term cannot do, and which is the same
    discriminator the refinement sweeps use elsewhere in this project.
    """

    def test_it_collapses_with_the_convergence_tolerance(self):
        from ogr_core.support import ForceApplication
        p = _anchored(ForceApplication.ACTIVE)
        prev = None
        for tol in (1e-3, 1e-8, 1e-12):
            e = abs(_err("janbu_simplified", p, 40.0, tolerance=tol))
            if prev is not None:
                assert e < 0.01 * prev, (tol, e, prev)
            prev = e
        assert prev < 1e-12, prev

    def test_the_default_residual_is_small_and_of_that_size(self):
        """It is not zero at the default, and saying so is the point: the
        number OGR reports out of the box carries the iteration, and the
        iteration is 2e-4 here, not the 1.9 % to 20 % this file opened
        with."""
        from ogr_core.support import ForceApplication
        for app in (ForceApplication.ACTIVE, ForceApplication.PASSIVE):
            for beta in BETAS + (BETA_STEEP,):
                e = abs(_err("janbu_simplified", _anchored(app), beta,
                             tolerance=1e-3))
                assert e < 1e-3, (app, beta, e)


# ======================================================================
class TestASupportAndALineLoadAreTheSameFreeBody:
    """The identity D46 is named for, on the two methods it was still open
    on. Same magnitude, same point, same angle, two unrelated code paths.

    The fixture is the one from ``test_support_noncircular_v1140`` — an
    INCLINED anchor on a polyline — deliberately, because there the two
    routes are not algebraically identical and what is left over is
    discretisation, which shrinks. On the circle of ``test_efp_wall_v1122``
    the force is horizontal and ACTIVE, and there the agreement is exact
    rather than shrinking; that half is asserted in its own file.
    """

    #: For Janbu the agreement is EXACT, not merely shrinking, and that is
    #: stronger. Per slice the support owes the driving side
    #: ``−T_S·sec α = −slide_sign·(P_h + P_v·tan α)``, while the same force
    #: as a load owes ``−slide_sign·P_h`` through ``h_water`` and
    #: ``−slide_sign·P_v·tan α`` through ``w_total`` — the same two terms.
    #: The normal halves match too, because ``support_vertical_load``
    #: returns exactly ``−P_v``. Nothing is left over to discretise, so the
    #: band is machine precision rather than the 0.5 % v1140 needs for
    #: Bishop. Only the marching methods, which rebuild the cartesian
    #: resultant, are in the same company.
    TOL = 1e-9

    def test_both_janbu_hold_it_on_the_polyline(self):
        surf = _polyline()
        for mid in JANBU:
            gaps = [_gap(mid, surf, n) for n in SWEEP]
            assert all(abs(g) < self.TOL for g in gaps), (mid, gaps)

    def test_both_janbu_hold_it_on_the_circle(self):
        surf = _circle()
        for mid in JANBU:
            gaps = [_gap(mid, surf, n) for n in SWEEP]
            assert all(abs(g) < self.TOL for g in gaps), (mid, gaps)

    def test_the_methods_that_only_shrink_are_the_control(self):
        """Bishop, Ordinary and Spencer reach the two channels through
        genuinely different arithmetic, so they carry a mesh residual that
        SHRINKS — 0.087 % to 0.002 % on the polyline. If Janbu's exact zero
        were the fixture rather than the algebra, theirs would be zero too.
        """
        surf = _polyline()
        for mid in ("bishop_simplified", "ordinary_fellenius", "spencer"):
            gaps = [_gap(mid, surf, n) for n in SWEEP]
            assert abs(gaps[0]) > 1e-3, (mid, gaps)
            assert abs(gaps[-1]) < 0.3 * abs(gaps[0]), (mid, gaps)

    def test_janbu_is_no_worse_than_the_methods_that_never_had_it(self):
        surf = _polyline()
        mine = max(abs(_gap(mid, surf, 100)) for mid in JANBU)
        theirs = max(abs(_gap(mid, surf, 100))
                     for mid in ("ordinary_fellenius", "spencer",
                                 "gle_morgenstern_price"))
        assert mine <= theirs + 1e-9, (mine, theirs)
