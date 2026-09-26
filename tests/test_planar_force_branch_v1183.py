# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
On a plane the force branch owes nothing to the thrust, so nothing may be
asked of the thrust before its answer is taken.

WHAT INVARIANT THIS PROTECTS. The factor of safety that closes GLOBAL force
equilibrium on a planar slip surface does not depend on the inter-slice
forces at all. That is not this package's claim: Krahn (2003, "The 2001 R.M.
Hardy Lecture: The limits of limit equilibrium analyses", Can. Geotech. J.
40(3): 643-660, p. 646 and fig. 5) states it as "force equilibrium is
completely independent of interslice shear ... the soil wedge on the planar
slip surface can move without any slippage between the slices", and USACE EM
1110-2-1902 SC-7a reaches the same conclusion from static determinacy — one
slice, two equilibrium equations, two unknowns. Inside ``solve_branch`` the
arithmetic reason is that one base angle makes every ``m_alpha`` equal, so
the sum of base normals carries ``X_i - X_{i+1}``, which telescopes to zero
between two free ends.

WHY THAT NEEDED A VERSION. v0.1.179 (D145) made a branch wait for its thrust
residual before it could be accepted, which is right wherever the factor
depends on the thrust — and that is every surface except this one. On a
plane the gate withheld a state to withhold a number that was already right.
Bank defect D152.

WHAT THE PREVIOUS ACCOUNT GOT WRONG, since the ticket is retired with this
file and its numbers have to outlive it. It said the exemption would need
"a cheap test that ``F_f`` telescopes, and there is none inside the loop,
because it depends on the geometry of the SURFACE and not on the rows".
``SliceRow.alpha`` is that geometry and the rows already carry it. It also
said the family was "a force branch over a POLYLINE", and that is measured
false below: a polyline of two segments moves its force factor by ten per
cent across lambda, and Krahn says the same thing for composite surfaces on
the same page. The family is one base angle, not one surface class.

WHAT THIS FILE DOES NOT CLAIM. Not that the exemption is free of the thrust
altogether: the telescoping is exact in the algebra and fails in the
arithmetic once the cancellation is large enough, which is why the guard
below exists and why it is measured rather than argued. And not that the
recovered branch publishes a settled thrust — it does not, and the case that
says so is here rather than left for someone to discover.

WHAT IT DISCRIMINATES, run against the tree of 0.1.182 with only this file
added: 3 of the 13 fail and 10 pass, and the split is named rather than
counted, because a count hides which kind of failure did the work.

TWO fail on a MEASURED difference, which is the discrimination that means
something: ``test_every_cell_now_agrees_with_the_closed_form``, where the
ACTIVE cell at lambda 1.25 comes back not converged after 271 passes; and
``test_the_recovered_branch_publishes_an_unsettled_thrust``, which cannot
reach its own subject there because the branch it judges is not accepted.

ONE fails on an ABSENT SYMBOL, and that is weak discrimination, labelled as
such instead of counted with the others:
``test_the_threshold_sits_between_them_with_room_on_both_sides`` raises
``ImportError`` for ``PLANAR_ALPHA_SPREAD``. It says the constant is new; it
says nothing about what the constant does.

Of the TEN that pass, THREE are vacuous on the old tree by construction —
``test_and_without_the_switch_exactly_one_of_them_is_lost``,
``test_the_exemption_does_nothing_on_a_polyline`` and
``test_and_nothing_on_the_moment_branch_of_a_plane_either`` all take the
``if keep is None`` exit of ``_off()``, the same idiom ``_lifted`` uses in
``test_interslice_thrust_bound_v1171``. The other SEVEN pass on both trees
ON PURPOSE: five state what is true of a plane whatever the solver does,
one describes what this version did NOT do, and one is the runaway, which
0.1.182 refuses for its own reason — the D145 gate — where this version
refuses it with the guard. That last one is the case to watch: it goes
green on both sides for DIFFERENT reasons, so it is the sibling of the
runaway case in v1171 and not a duplicate of it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

#: The fixture of ``test_anchored_wedge_root_v1177.py``, written out again
#: because the modules in ``tests/`` cannot import one another outside the
#: runner. Same four vertices, same material, same slice count and the same
#: 120 kN/m anchor, so the numbers here and there mean the same thing.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
TIGHT = 1e-10
MAX_IT = 400

#: The plane whose ACTIVE cell D145 took away and D152 gives back, and the
#: four inclinations the sibling file sweeps.
BETA = 50.0
LAMBDAS = (-1.0, 0.0, 0.8, 1.25)
LOST = 1.25

#: The runaway of D118: this plane at this inclination sends its thrust past
#: 6e9 times the force scale. With the bound in place it never survives to
#: be accepted; the guard is what answers for the case where it would.
RUNAWAY_BETA, RUNAWAY_LAMBDA, RUNAWAY_TOL = 55.0, -5.55, 1e-3


def _daylight_x(beta_deg):
    return TOE + H / math.tan(math.radians(beta_deg))


def _bare():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    return p


def _anchored(application=None):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _bare()
    p.support_types = [EndAnchored(anchor_capacity=120.0,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(34.0, 6.0), tail=Vertex(48.0, 11.0),
        force_application=application or ForceApplication.ACTIVE,
        orientation=ForceOrientation.USER_DEFINED, user_angle_deg=15.0)]
    return p


def _plane(beta_deg=BETA):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _polyline(vertices=2):
    """A surface that is NOT a plane, and stays under the ground surface.

    The intermediate vertices are below the slope face on purpose: a
    polyline that crosses it produces no slices at all, and a test whose
    fixture produces nothing asserts nothing.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    top = Vertex(_daylight_x(BETA), H)
    mid = ([Vertex(35.0, 4.0)] if vertices == 2
           else [Vertex(33.0, 2.0), Vertex(36.5, 5.5)])
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(TOE, 0.0)] + mid + [top]))


def _slices(project, surface):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return sl


def _system(project, surface, tolerance=TIGHT):
    """The ``GLESystem`` the METHOD builds — the resolved support included.

    Mirrors ``spencer.py``: the seismic pair, the sign of the driving force,
    the axis, the resolved support and the branch budget. Built with the
    support rather than with ``sup=None`` because the latter measures a
    system nobody solves.
    """
    from ogr_slip2d.interslice import GLESystem, branch_budget
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.support_integration import resolve_support_terms

    sl = _slices(project, surface)
    rows = sl.slices
    raw = sum(s.weight * math.sin(s.base_angle) for s in rows)
    sign = 1.0 if raw >= 0 else -1.0
    sup = resolve_support_terms(project, surface, sl, sign)
    return GLESystem(rows, [1.0] * (len(rows) + 1), 0.0, 0.0, sign,
                     None, None, sup, axis_for(project, surface),
                     tolerance=tolerance, initial_fos=1.0,
                     max_passes=branch_budget(MAX_IT))


def _closed_form(project, beta_deg=BETA):
    """The wedge, from geometry and the model's own support terms.

    The external reference of this file for the VALUE (Coulomb 1776; the
    modern statement with the support resolved on the base is Duncan &
    Wright 2005 §6). Krahn (2003) is the reference for the INDEPENDENCE.
    """
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.support_integration import resolve_support_terms

    sl = _slices(project, _plane(beta_deg))
    raw = sum(slice_forces(s, 0.0, 0.0).w_total * math.tan(s.base_angle)
              for s in sl.slices)
    sup = resolve_support_terms(project, _plane(beta_deg), sl,
                                1.0 if raw >= 0 else -1.0)
    t_n, t_act, t_pas = ((math.fsum(sup.n_press), sup.total_active_t(),
                          sup.total_passive_t()) if sup.present
                         else (0.0, 0.0, 0.0))
    a = math.radians(beta_deg)
    W = GAMMA * 0.5 * H * (_daylight_x(beta_deg) - CREST)
    num = COH * (H / math.sin(a)) + (W * math.cos(a) + t_n) * math.tan(
        math.radians(PHI))
    return (num + t_pas) / (W * math.sin(a) - t_act)


def _force(system, lam, tolerance=None, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam), None,
                        tolerance or system.tolerance, 1.0, **kw)


def _moment(system, lam, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos, system.tolerance, 1.0, **kw)


def _spread(system):
    """The predicate itself, read from the rows the solver receives."""
    a = [r.alpha for r in system.rows]
    return max(a) - min(a)


@contextlib.contextmanager
def _off():
    """The acceptance of 0.1.182: the planar exemption switched off.

    Read with ``getattr`` and restored with ``try/finally`` because the
    runner does not call ``teardown_method`` (rule 5), and because a tree
    without the switch has to leave every case below meaning what it says
    instead of turning the file into collection errors.
    """
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "BRANCH_PLANAR_FORCE", None)
    if keep is None:
        yield False
        return
    interslice.BRANCH_PLANAR_FORCE = False
    try:
        yield True
    finally:
        interslice.BRANCH_PLANAR_FORCE = keep


@contextlib.contextmanager
def _unbounded():
    """The thrust bound of D118 out of the way, to reach the guard.

    ``solve_branch`` reads ``THRUST_SCALE_LIMIT`` inside its own body at
    call time, so patching the module global is enough; the same is NOT
    true of ``max_passes``, whose default binds at ``def`` time.
    """
    import ogr_slip2d.interslice as interslice
    keep = interslice.THRUST_SCALE_LIMIT
    interslice.THRUST_SCALE_LIMIT = 1e300
    try:
        yield
    finally:
        interslice.THRUST_SCALE_LIMIT = keep


def _cells():
    from ogr_core.support import ForceApplication
    return (("bare", _bare()),
            ("active", _anchored(ForceApplication.ACTIVE)),
            ("passive", _anchored(ForceApplication.PASSIVE)))


# ----------------------------------------------------------------------
class TestTheMechanicsThePredicateRestsOn:
    """Krahn (2003) on this fixture, measured rather than quoted.

    Both cases pass on BOTH trees on purpose: they state what is true of a
    plane, not what this version changed. A difference here would mean the
    premise stopped holding, which is exactly when the exemption would have
    to go.
    """

    def test_the_force_factor_does_not_move_with_lambda_on_a_plane(self):
        for tag, project in _cells():
            system = _system(project, _plane())
            seen = [_force(system, lam, max_passes=MAX_IT) for lam in LAMBDAS]
            got = [s.fos for s in seen if s is not None]
            assert len(got) == len(LAMBDAS), (tag, seen)
            spread = (max(got) - min(got)) / abs(got[0])
            assert spread < 1e-9, (tag, spread, got)

    def test_and_it_does_move_on_a_surface_that_is_not_one(self):
        """The control that says the family is one ANGLE, not one class.

        Krahn puts the composite surface in the other box on the same page:
        "both moment and force equilibrium are influenced by the interslice
        shear forces". Two segments are enough to show it, and three more
        so, which is why both are swept instead of one.
        """
        for n in (2, 3):
            system = _system(_bare(), _polyline(n))
            got = [_force(system, lam, max_passes=MAX_IT).fos
                   for lam in LAMBDAS]
            spread = (max(got) - min(got)) / abs(got[0])
            # Ten per cent and eleven, against 1e-14 for the plane. The
            # bound is loose because the point is the ORDER, not the value.
            assert spread > 1e-2, (n, spread, got)


class TestThePredicateIsReadFromTheRows:
    """``SliceRow.alpha``, and the fourteen orders that make the threshold
    carry no decision."""

    def test_a_plane_and_a_polyline_are_not_near_each_other(self):
        plane = _spread(_system(_bare(), _plane()))
        poly = _spread(_system(_bare(), _polyline(2)))
        # Not an exact comparison, and this is why: a real plane does not
        # produce one angle bit for bit.
        assert plane > 0.0, plane
        assert plane < 1e-12, plane
        assert poly > 1e-2, poly
        assert poly / plane > 1e10, (poly, plane)

    def test_the_threshold_sits_between_them_with_room_on_both_sides(self):
        from ogr_slip2d.interslice import PLANAR_ALPHA_SPREAD
        plane = _spread(_system(_bare(), _plane()))
        poly = _spread(_system(_bare(), _polyline(2)))
        assert plane * 1e5 < PLANAR_ALPHA_SPREAD, (plane, PLANAR_ALPHA_SPREAD)
        assert poly / PLANAR_ALPHA_SPREAD > 1e5, (poly, PLANAR_ALPHA_SPREAD)

    def test_the_exemption_does_nothing_on_a_polyline(self):
        """A/B in one process: the switch cannot reach a surface that is
        not a plane, which is what keeps the 5348 branches D145 measured
        where they are. A proof, not a census."""
        system = _system(_bare(), _polyline(2))
        for lam in LAMBDAS:
            with _off() as live:
                was = _force(system, lam, max_passes=MAX_IT)
            now = _force(system, lam, max_passes=MAX_IT)
            if not live:
                continue
            assert was.fos == now.fos, (lam, was.fos, now.fos)
            assert was.passes == now.passes, (lam, was.passes, now.passes)
            assert was.converged == now.converged

    def test_and_nothing_on_the_moment_branch_of_a_plane_either(self):
        """The exemption is the FORCE branch's. On a plane the moment
        factor is the one that depends on the thrust — Krahn again, the two
        curves swap places — so exempting it would be the opposite of what
        the mechanics says."""
        system = _system(_anchored(), _plane())
        for lam in (-1.0, 0.0, 0.8):
            with _off() as live:
                was = _moment(system, lam, max_passes=MAX_IT)
            now = _moment(system, lam, max_passes=MAX_IT)
            if not live or was is None or now is None:
                continue
            assert was.fos == now.fos, (lam, was.fos, now.fos)
            assert was.passes == now.passes, (lam, was.passes, now.passes)


class TestTheCellThatComesBack:
    """Rule 7 in the affirmative: the switch moves a number, and the number
    it moves is the one the closed form predicts."""

    def test_every_cell_now_agrees_with_the_closed_form(self):
        for tag, project in _cells():
            system = _system(project, _plane())
            closed = _closed_form(project)
            for lam in LAMBDAS:
                st = _force(system, lam, max_passes=MAX_IT)
                assert st is not None and st.converged, (tag, lam, st)
                assert abs(st.fos - closed) / closed < 1e-8, (
                    tag, lam, st.fos, closed)

    def test_and_without_the_switch_exactly_one_of_them_is_lost(self):
        """The attribution table, executed rather than written down."""
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.ACTIVE), _plane())
        with _off() as live:
            if not live:
                return
            was = {lam: _force(system, lam, max_passes=MAX_IT)
                   for lam in LAMBDAS}
        now = {lam: _force(system, lam, max_passes=MAX_IT)
               for lam in LAMBDAS}
        lost = [lam for lam in LAMBDAS
                if was[lam] is not None and not was[lam].converged]
        assert lost == [LOST], lost
        assert now[LOST].converged is True
        # And the factor was never the thing that was wrong: the branch the
        # gate refused was already carrying it.
        assert abs(was[LOST].fos - now[LOST].fos) / now[LOST].fos < 1e-10


class TestTheGuardAgainstARunaway:
    """The half of the design that the first attempt got wrong.

    The telescoping is exact in the algebra and NOT in the arithmetic. With
    the bound of D118 lifted, a thrust of 6e9 times the force scale carries
    a factor that is 0.1 per cent off the closed form — small enough to be
    believed and wrong. So the exemption carries its own guard, and it is
    not the bound: the bound is what a test may lift.
    """

    def test_a_runaway_is_refused_even_with_the_bound_lifted(self):
        system = _system(_bare(), _plane(RUNAWAY_BETA),
                         tolerance=RUNAWAY_TOL)
        with _unbounded():
            st = _force(system, RUNAWAY_LAMBDA, tolerance=RUNAWAY_TOL,
                        max_passes=MAX_IT)
        assert st is None or st.converged is False, st.fos

    def test_and_the_factor_it_would_have_carried_was_wrong(self):
        """Measured, so that the guard is not defended by assertion.

        The branch is walked with the guard's own comparison removed the
        only way a test can remove it: by asking for the state the solver
        reaches, and checking what the factor there is worth.
        """
        from ogr_slip2d.interslice import solve_branch
        system = _system(_bare(), _plane(RUNAWAY_BETA),
                         tolerance=RUNAWAY_TOL)
        closed = _closed_form(_bare(), RUNAWAY_BETA)
        with _unbounded():
            st = solve_branch(system.rows,
                              system.lambda_boundary(RUNAWAY_LAMBDA),
                              None, RUNAWAY_TOL, 1.0, max_passes=16)
        assert st is not None
        peak = max(abs(e) for e in st.boundary_e)
        scale = math.fsum(abs(r.w_eff) + r.c_l + abs(r.h_drive)
                          + abs(r.t_active) + abs(r.t_passive)
                          for r in system.rows)
        assert peak / scale > 1e8, peak / scale
        # A tenth of a per cent: believable, and not the answer.
        err = abs(st.fos - closed) / closed
        assert err > 1e-4, (st.fos, closed, err)

    def test_while_the_plane_that_is_an_answer_keeps_it(self):
        """The control: the SAME plane, solved instead of run away with.

        Asked at the tight tolerance and not at the runaway's 1e-3, because
        a branch owes the closed form at the order it was solved to and no
        better — at 1e-3 this one lands 1.2e-4 away, which is the residual
        ``test_branch_contraction_v1172`` measures as ``tol*r/(1-r)`` and
        not an error. Tightening it is what makes the contrast an order of
        magnitude argument rather than a coincidence: this branch reaches
        the closed form to 1e-9, the runaway above misses it by 1.1e-3, and
        six orders separate a solution from something that merely looks
        like one.
        """
        system = _system(_bare(), _plane(RUNAWAY_BETA))
        st = _force(system, 0.0, max_passes=MAX_IT)
        closed = _closed_form(_bare(), RUNAWAY_BETA)
        assert st is not None and st.converged
        assert abs(st.fos - closed) / closed < 1e-8, (st.fos, closed)


class TestWhatThisVersionDoesNotDo:
    """Written down with the number in front, which is how D152 itself was
    found in the file that reported it."""

    def test_the_stall_detector_fix_only_renames_this_exit(self):
        """It counted passes that do not beat F's own record, and F reaching
        its fixed point makes its step 0.0 exactly — a branch succeeding
        read as a branch wandering. Not fixed here, and fixing it alone
        would not have recovered anything: the thrust of the cell above
        contracts at 0.98275 a pass and would need some 1217 passes against
        a ceiling of 400, so the branch would only have changed the name of
        its exit.

        v0.1.209 (D158) fixed it, and this case used to read the source to
        say it had not been. It now executes the prediction instead: with
        the exemption off and the default budget, the detector that watches
        the pair takes the branch past pass 271 and it leaves on pass 400
        out of budget, not converged. The 1218 passes it does need are in
        ``test_stall_pair_v1209``, with a user's budget and the closed form.
        """
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.ACTIVE), _plane())
        with _off() as live:
            if not live:
                return
            st = _force(system, LOST, max_passes=MAX_IT)
        assert st is not None and st.converged is False
        assert st.abandoned == "", st.abandoned
        assert st.passes == MAX_IT, st.passes

    def test_the_recovered_branch_publishes_an_unsettled_thrust(self):
        """The exemption gives back the FACTOR, not a converged thrust.

        On the recovered cell the thrust is still some 8 per cent of the
        force scale away from its own fixed point when the factor is taken,
        and ``thrust_is_admissible`` judges it on that. The node stays out
        of the lambda search either way — before, because the branch was
        not converged; now, because its thrust is inadmissible — so no
        answer moves, and saying which of the two is happening is the
        point.

        v0.1.209 — and the verdict is read on the WRONG thrust. Settled (the
        pair detector of D158 reaches it on pass 1218), this cell's thrust
        is in compression with a margin of +0.420; the thrust of the pass
        the exemption accepts on is at -0.119. The node is out for a reason
        its own fixed point contradicts. Reported, not fixed:
        ``test_stall_pair_v1209::TestWhatThisVersionDoesNotDo``.
        """
        from ogr_core.support import ForceApplication
        from ogr_slip2d.interslice import thrust_is_admissible
        system = _system(_anchored(ForceApplication.ACTIVE), _plane())
        st = _force(system, LOST, max_passes=MAX_IT)
        assert st is not None and st.converged
        assert thrust_is_admissible(st) is False
        # And the eleven cells that were never in question keep theirs.
        for lam in (-1.0, 0.0, 0.8):
            other = _force(system, lam, max_passes=MAX_IT)
            assert thrust_is_admissible(other) is True, lam
