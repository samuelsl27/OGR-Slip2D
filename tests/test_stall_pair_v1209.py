# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The stall detector of ``solve_branch`` watches the PAIR (F, X), not F alone.

WHAT INVARIANT THIS PROTECTS. The state the branch loop iterates is the pair
(F, X): since v0.1.179 (D145) the acceptance asks both residuals to be under
the tolerance, and the rescue enters on either. The stall detector did not
follow — it reset only when F's step beat its own record — and its comment
said why that sufficed: "the step of a fixed point that contracts beats its
own record on every pass". That was false precisely at the fixed point. A
branch whose F lands ON it makes ``step`` 0.0, ``0.0 < 0.0`` never holds
again, and the branch was cut for having arrived while its thrust, the half
of the pair still moving, was contracting. Bank defect D158.

``BRANCH_STALL_PAIR`` (v0.1.209) resets the counter when EITHER residual beats
its own record. Three things are held here:

1. RULE 7, AGAINST AN EXTERNAL VALUE. On the anchored wedge of
   ``test_planar_force_branch_v1183`` — ACTIVE anchor, lambda 1.25, the planar
   exemption of D152 switched off so that nothing but the stall test decides
   the branch — the switch OFF cuts it on pass 271 (on Windows; 251 on the
   Linux of the CI, see the note on the witness constants) with ``|dF|``
   exactly 0.0 on 40 of its last 226 passes; ON, with the budget a user's
   ``max_iterations = 2000`` buys, it converges on pass 1218 to the closed
   form of the wedge (Coulomb 1776; Duncan & Wright 2005 §6) to 2.3e-14. The
   factor of a plane does not depend on the thrust (Krahn 2003, Can. Geotech.
   J. 40: 646; USACE EM 1110-2-1902 SC-7a), which is what makes the closed
   form the right reference for a branch whose thrust took 1218 passes.

2. NEUTRALITY, WHICH IS A PROOF AND IS EXECUTED ANYWAY. Nothing outside the
   stall block reads ``stall``, ``best_step`` or ``best_d_x``; ``best_step``
   is updated exactly as before; the thrust can only ADD resets. So the
   trajectory is the old one pass for pass up to the pass the old detector
   broke on, and a branch that did not stall with the switch off is the same
   branch bit for bit with it on. Swept here over the wedge ladder and over
   the validation case ACADS 1(c) under Spencer and GLE, call by call.

3. WHAT IT DOES NOT BUY INSIDE THE DEFAULT BUDGET, said with the number in
   front because D158 said it first: the witness needs ~1218 passes and
   ``MAX_PASSES`` is 400, so with the default budget the switch only changes
   the NAME of its exit — from stalled on pass 271 to out of budget on 400.

WHAT DISCRIMINATES, run against the tree of 0.1.208 with only this file
added (a worktree, ``PYTHONPATH`` pointing at it). ``_pair`` is a no-op on a
tree without the switch and every "on" side uses the default, so the cases
that fail there fail on a MEASURED difference and are named, not counted:
``test_on_it_converges_to_the_closed_form`` (cut on pass 271, not
converged), ``test_inside_the_default_budget_it_only_renames_the_exit``
(271, not 400), ``test_the_planar_exemption_judges_an_unsettled_thrust``
(the settled side never settles), ``test_off_is_the_detector_of_v0_1_208``
(the "on" branch stops where the "off" one does: 271 and 271) and, on an
ABSENT SYMBOL — the weak kind, labelled as such —
``test_it_is_in_the_signature_of_the_lambda_cache``: 5 of 9. The other four
pass on both trees on purpose: the neutrality sweep is the control (both
sides are the same tree there, so it is vacuous by construction and is
evidence only here), and the "off" cases state what v0.1.208 did.

The first push of this file pinned the pass the old detector cuts on (271)
and went red on the Linux of the CI, which cuts on 251; see the note on the
witness constants. Measured before the fix on the CI's three Pythons: 4
failures, all of them that pin.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math
from pathlib import Path

#: The fixture of ``test_anchored_wedge_root_v1177.py`` and
#: ``test_planar_force_branch_v1183.py``, written out again because the
#: modules in ``tests/`` cannot import one another outside the runner.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
TIGHT = 1e-10
MAX_IT = 400

#: The witness of D158: the ACTIVE cell of the 50 degree plane at lambda 1.25.
BETA = 50.0
WITNESS_LAMBDA = 1.25
#: The pass the old detector cuts the witness on is NOT pinned, and the first
#: push of this file said why by failing: 271 on the Windows it was measured
#: on, 251 on the Linux of the CI (Python 3.11-3.13). The cut comes
#: ``STALL_PATIENCE`` passes after F's step last beat its record, and which
#: pass lands on 0.0 bit for bit is platform arithmetic -- the lesson of
#: v0.1.205, walked into again with a pass count instead of a double. What
#: holds on both is the law: the cut comes after ``STALL_PATIENCE`` and inside
#: the budget, with F already on the closed form.
#: The budget ``branch_budget`` gives a user's ``max_iterations = 2000``.
LONG_BUDGET = 2000

LAMBDAS = (-1.0, 0.0, 0.8, 1.25)

_ACADS = (Path(__file__).resolve().parent.parent
          / "validacion" / "casos" / "003-acads-1c" / "modelo.ogr")
#: The published critical circle of ACADS 1(c), and the crawling circle of
#: v0.1.100 on the same grid (see ``test_convergence_tolerance_v198``).
_ACADS_CIRCLES = ((34.121, 43.254, 18.781), (50.0, 35.0, 9.181818181818182))


# ----------------------------------------------------------------------
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


def _polyline():
    """Not a plane, and under the slope face (see v1183 for why)."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(35.0, 4.0), Vertex(_daylight_x(BETA), H)]))


def _system(project, surface, tolerance=TIGHT, max_it=MAX_IT):
    """The ``GLESystem`` the method builds, the resolved support included."""
    from ogr_slip2d.interslice import GLESystem, branch_budget
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import resolve_support_terms

    sl = slice_surface(project, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the surface produced no slices"
    rows = sl.slices
    raw = sum(s.weight * math.sin(s.base_angle) for s in rows)
    sign = 1.0 if raw >= 0 else -1.0
    sup = resolve_support_terms(project, surface, sl, sign)
    return GLESystem(rows, [1.0] * (len(rows) + 1), 0.0, 0.0, sign,
                     None, None, sup, axis_for(project, surface),
                     tolerance=tolerance, initial_fos=1.0,
                     max_passes=branch_budget(max_it))


def _closed_form(project, beta_deg=BETA):
    """The wedge, from geometry and the model's own support terms.

    Coulomb (1776) for the value, with the support resolved on the base as in
    Duncan & Wright (2005) §6; Krahn (2003) for its independence from the
    thrust. The same function as ``test_planar_force_branch_v1183``.
    """
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import resolve_support_terms

    sl = slice_surface(project, _plane(beta_deg), num_slices=NSLICES)
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


@contextlib.contextmanager
def _pair(value):
    """``BRANCH_STALL_PAIR`` set to ``value`` and ALWAYS restored.

    ``try/finally`` and not a teardown: the runner does not call
    ``teardown_method`` (rule 5), and a switch left off would silently turn
    every later file into a test of v0.1.208. A tree WITHOUT the switch is
    the old detector already, so there it changes nothing — the idiom of
    ``_unrescued`` — and every "on" side below uses the default instead of
    this, so that against 0.1.208 it fails on the measured difference and
    not on a missing name.
    """
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "BRANCH_STALL_PAIR", None)
    if keep is None:
        yield
        return
    interslice.BRANCH_STALL_PAIR = value
    try:
        yield
    finally:
        interslice.BRANCH_STALL_PAIR = keep


@contextlib.contextmanager
def _planar_off():
    """The planar exemption of D152 out of the way, so the stall test decides.

    With it on, the witness is admitted on pass 48 and never reaches the
    detector at all — which is why D152 could close without touching it.
    """
    import ogr_slip2d.interslice as interslice
    keep = interslice.BRANCH_PLANAR_FORCE
    interslice.BRANCH_PLANAR_FORCE = False
    try:
        yield
    finally:
        interslice.BRANCH_PLANAR_FORCE = keep


def _force(system, lam, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam), None,
                        system.tolerance, 1.0, **kw)


def _moment(system, lam, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos, system.tolerance, 1.0, **kw)


def _stalled(state, max_passes):
    """The exit ``GLESystem.branches`` counts as a stall, read the same way."""
    return (state is not None and not state.converged
            and not state.abandoned and state.passes < max_passes)


def _same(a, b):
    if a is None or b is None:
        return a is None and b is None
    return (a.fos == b.fos and a.passes == b.passes
            and a.converged == b.converged and a.abandoned == b.abandoned
            and a.rescued == b.rescued
            and list(a.boundary_x) == list(b.boundary_x)
            and list(a.boundary_e) == list(b.boundary_e))


# ----------------------------------------------------------------------
class TestTheWitnessOfD158:
    """Rule 7: the switch moves a number, and to the closed form."""

    def test_off_the_branch_is_cut_for_having_arrived(self):
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.ACTIVE), _plane(),
                         max_it=LONG_BUDGET)
        with _planar_off(), _pair(False):
            st = _force(system, WITNESS_LAMBDA, max_passes=system.max_passes)
        from ogr_slip2d.interslice import STALL_PATIENCE
        assert _stalled(st, system.max_passes), (st.passes, st.converged)
        assert STALL_PATIENCE < st.passes < MAX_IT, st.passes
        # F was already right: the stall cut a branch whose factor was the
        # answer and whose thrust was still on its way.
        closed = _closed_form(_anchored(ForceApplication.ACTIVE))
        assert abs(st.fos - closed) / closed < 1e-12, (st.fos, closed)

    def test_on_it_converges_to_the_closed_form(self):
        from ogr_core.support import ForceApplication
        project = _anchored(ForceApplication.ACTIVE)
        system = _system(project, _plane(), max_it=LONG_BUDGET)
        closed = _closed_form(project)
        with _planar_off():
            st = _force(system, WITNESS_LAMBDA, max_passes=system.max_passes)
        assert st is not None and st.converged, (st.passes, st.abandoned)
        # More than the default budget: this is an answer only a user's
        # ``max_iterations`` can buy, which is what item 3 is about.
        assert st.passes > MAX_IT, st.passes
        assert abs(st.fos - closed) / closed < 1e-8, (st.fos, closed)

    def test_inside_the_default_budget_it_only_renames_the_exit(self):
        """D158's own prediction, executed rather than quoted."""
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.ACTIVE), _plane())
        with _planar_off():
            with _pair(False):
                was = _force(system, WITNESS_LAMBDA, max_passes=MAX_IT)
            now = _force(system, WITNESS_LAMBDA, max_passes=MAX_IT)
        assert _stalled(was, MAX_IT), (was.passes, was.converged)
        assert now.converged is False and now.abandoned == ""
        assert now.passes == MAX_IT, now.passes

    def test_with_the_exemption_on_nothing_moves(self):
        """The shipped configuration admits the witness on pass 48 through
        the planar exemption, before the detector can say anything."""
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.ACTIVE), _plane())
        with _pair(False):
            was = _force(system, WITNESS_LAMBDA, max_passes=MAX_IT)
        now = _force(system, WITNESS_LAMBDA, max_passes=MAX_IT)
        assert was.converged and _same(was, now), (was.passes, now.passes)


class TestNeutrality:
    """A branch that did not stall with the switch off is the same branch.

    Item 2 of the module docstring, run call by call. Each comparison stops
    at the first branch that DID stall with the switch off, because from
    there on the two runs are allowed to differ and may ask the solver
    different questions.
    """

    def test_the_wedge_ladder_branch_by_branch(self):
        from ogr_core.support import ForceApplication
        cells = (_bare(), _anchored(ForceApplication.ACTIVE),
                 _anchored(ForceApplication.PASSIVE))
        compared = stalled = 0
        for project in cells:
            for surface in (_plane(50.0), _plane(55.0), _polyline()):
                for tol in (TIGHT, 1e-4):
                    system = _system(project, surface, tolerance=tol)
                    for lam in LAMBDAS:
                        for branch in (_force, _moment):
                            with _pair(False):
                                was = branch(system, lam, max_passes=MAX_IT)
                            now = branch(system, lam, max_passes=MAX_IT)
                            if _stalled(was, MAX_IT):
                                stalled += 1
                                continue
                            compared += 1
                            assert _same(was, now), (lam, tol, branch.__name__)
        # Not vacuous: most of the ladder converges, and the sweep reaches
        # at least the witness among the ones that stall.
        assert compared > 100, compared
        assert stalled >= 1, stalled

    def test_the_validation_case_call_by_call(self):
        """ACADS 1(c), Spencer and GLE, the whole method and not one branch.

        Every call to ``solve_branch`` is recorded in both runs; up to the
        first call that stalled with the switch off the two sequences must be
        identical, and when none stalled the published factor must be too.
        """
        if not _ACADS.is_file():
            return
        from ogr_core.project import Project
        from ogr_slip2d import SlipCircle, slice_surface
        import ogr_slip2d.interslice as interslice
        from ogr_slip2d.methods import GLEMorgensternPrice, Spencer

        project = Project.load(_ACADS)
        orig = interslice.solve_branch
        compared = 0
        for cx, cy, r in _ACADS_CIRCLES:
            circle = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
            slices = slice_surface(project, circle, num_slices=25)
            for cls in (Spencer, GLEMorgensternPrice):
                for tol in (1e-3, 1e-7):
                    runs = {}
                    for value in (False, True):
                        calls = []

                        def rec(*a, _calls=calls, **k):
                            st = orig(*a, **k)
                            _calls.append((st, k.get("max_passes",
                                                     interslice.MAX_PASSES)))
                            return st

                        interslice.solve_branch = rec
                        try:
                            with (_pair(False) if value is False
                                  else contextlib.nullcontext()):
                                res = cls(tolerance=tol).compute_fos(
                                    project, circle, slices)
                        finally:
                            interslice.solve_branch = orig
                        runs[value] = (res, calls)
                    (r_off, c_off), (r_on, c_on) = runs[False], runs[True]
                    any_stall = False
                    for (a, mp), (b, _mp) in zip(c_off, c_on):
                        if _stalled(a, mp):
                            any_stall = True
                            break
                        compared += 1
                        assert _same(a, b), (cls.__name__, tol, cx)
                    if not any_stall:
                        assert len(c_off) == len(c_on)
                        assert r_off.fos == r_on.fos, (cls.__name__, tol)
        assert compared > 0, compared


class TestTheSwitchIsWiredLikeItsSiblings:

    def test_it_is_in_the_signature_of_the_lambda_cache(self):
        """A pair cached with the switch on may not answer with it off."""
        from ogr_core.support import ForceApplication
        from ogr_slip2d.interslice import _BRANCH_SWITCH_NAMES
        assert "BRANCH_STALL_PAIR" in _BRANCH_SWITCH_NAMES
        system = _system(_anchored(ForceApplication.ACTIVE), _plane())
        with _planar_off():
            on, _m = system.states(WITNESS_LAMBDA)
            with _pair(False):
                off, _m = system.states(WITNESS_LAMBDA)
        # Out of budget against stalled (on pass 271 here, 251 on the CI):
        # two different answers, so a cache that ignored the switch would be
        # caught here.
        assert on.passes == MAX_IT and _stalled(off, MAX_IT), (
            on.passes, off.passes)

    def test_off_is_the_detector_of_v0_1_208(self):
        """The switch off must be the old detector, and what DEFINES it is the
        property the neutrality proof rests on, not a pass number that
        differs between platforms: the two variants are the same branch bit
        for bit up to the pass before the old detector cuts, and only the new
        one goes on from there."""
        from ogr_core.support import ForceApplication
        system = _system(_anchored(ForceApplication.ACTIVE), _plane(),
                         max_it=LONG_BUDGET)
        with _planar_off():
            with _pair(False):
                off = _force(system, WITNESS_LAMBDA,
                             max_passes=system.max_passes)
                before_off = _force(system, WITNESS_LAMBDA,
                                    max_passes=off.passes - 1)
            before_on = _force(system, WITNESS_LAMBDA,
                               max_passes=off.passes - 1)
            on = _force(system, WITNESS_LAMBDA, max_passes=system.max_passes)
        assert _stalled(off, system.max_passes), off.passes
        assert _same(before_off, before_on), off.passes
        assert on.passes > off.passes and on.converged, (on.passes, off.passes)


class TestWhatThisVersionDoesNotDo:
    """Reported with the number in front, not fixed here (rule 6)."""

    def test_the_planar_exemption_judges_an_unsettled_thrust(self):
        """The exemption of D152 admits the witness on pass 48 and hands
        ``thrust_is_admissible`` the thrust of pass 48. There its resultant
        is in TENSION (margin -0.119); the settled thrust the pair detector
        reaches on pass 1218 is in COMPRESSION (margin +0.420). The verdict
        on the node is the opposite of the verdict on the fixed point.

        On a plane the factor does not depend on the thrust, so the number
        the exemption publishes is right; what is read too early is the
        sign the admissibility rests on — the quantity of D155. Nothing
        moves in the bank today (the one planar force branch of the bench,
        problem 047, is a given surface), and changing when the exemption
        reads the thrust is a change of its own, with its own ticket.
        """
        from ogr_core.support import ForceApplication
        from ogr_slip2d.interslice import thrust_is_admissible, thrust_margin
        project = _anchored(ForceApplication.ACTIVE)
        system = _system(project, _plane(), max_it=LONG_BUDGET)
        early = _force(system, WITNESS_LAMBDA, max_passes=MAX_IT)
        assert early.converged and early.passes < 100, early.passes
        assert thrust_is_admissible(early) is False
        with _planar_off():
            settled = _force(system, WITNESS_LAMBDA,
                             max_passes=system.max_passes)
        assert settled.converged
        assert thrust_is_admissible(settled) is True
        assert thrust_margin(early) < -0.1 and thrust_margin(settled) > 0.4, (
            thrust_margin(early), thrust_margin(settled))
        # And the factor is the same answer both ways, which is the half of
        # the exemption that is right.
        assert abs(early.fos - settled.fos) / settled.fos < 1e-9
