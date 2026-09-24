# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""A force branch lost through the inadmissible door is solved again from
its partner's F (D185, v0.1.193).

WHAT INVARIANT THIS FILE PROTECTS. That ``GLESystem._solve_states`` retries a
force branch that came back with NO state, starting from the moment
branch's converged F at the same lambda and with the relaxation rescue armed
from the first pass, and takes the new state only if it converged. And,
just as much, what that retry CANNOT do: touch a branch that already had a
state, admit a state that did not converge, fire without a converged
partner, or make ``states`` depend on anything but the system and lambda.

THE WITNESS, AND WHY IT IS THIS ONE. Verification problem 059 WITH its
grouted tieback, on the arc figure 59.2 draws (x from 0 to 12.583). It is
built in code from the profile and water table of
``test_lambda_closure_v1180`` plus the tieback of table 59.2, and it
reproduces the bank DIGIT FOR DIGIT against the bank's own model, checked
before any assertion here was written: 0.558355659095 by the lambda reserve
at 1.15625 with the retry off, 0.557188309996 bracketed at 1.3564092506 with
it on.

Why that arc lost its root is measured, not guessed. Bisected over every
version from 0.1.176 to 0.1.192: bracketed at lambda 0.8836 up to v0.1.177,
by the reserve from v0.1.178 on. v0.1.178 (D144) corrected the moment arm
of the support in the circular moment, which is PHYSICS, and it measures as
physics: F_f(lambda) bit for bit identical across the two versions, F_m down
by 1.6 to 2.1 %. The root moved to lambda 1.3564, where the damped update
from ``initial_fos`` = 1.0 -- and even from 0.5570, next to the answer --
oscillates away and leaves through the inadmissible door before pass 30,
long before the rescue gate or ``CYCLE_RUN`` could take it.

WHY NOTHING HERE IS A SNAPSHOT. No factor of safety is fixed against what
this code prints. The anchors are:

* an IDENTITY of the method: at the lambda the search returns, both branches
  converge and ``F_f = F_m`` to the solver's tolerance, and ``g = F_f - F_m``
  changes sign across it. That is what a Spencer root IS (Spencer 1967);
* the A/B in one process, the switch on and off -- rule 7, and the only way
  to say what the switch, and nothing else, moved;
* BIT-IDENTITY of everything the retry cannot reach, measured rather than
  argued: the fused mass, GLE on the same arc, and every lambda whose force
  branch already had a state;
* the contract of the retry, exercised by INJECTING what the branch solver
  returns, because a retry that fails does not happen on this witness;
* AST facts about what the cache depends on.

WHAT THIS FILE DOES NOT CLAIM:

* that the root is admissible. It is not: the thrust is in net tension at
  every lambda on this arc, the reserve's answer was inadmissible too, and
  that is physics and not this switch;
* that 0.557188 is right against the published 0.596. The comparison of
  this arc with the reference belongs to the bank (D147), not here;
* that the moment branch is retried. It is not -- no case needs it, and a
  symmetric switch with no witness is a switch nobody can show moves
  anything.

WHAT THIS FILE DISCRIMINATES, MEASURED and not guessed: run against a
``git worktree`` of v0.1.192 with only this file copied in (and that tree's
``ogr_slip2d`` checked to be the one imported), 14 of the 18 cases FAIL and
4 PASS.

NINE fail on MEASURED BEHAVIOUR, which is the file's case for itself:
``test_with_the_retry_the_arc_brackets`` (the reserve, 0.558356 at lambda
1.15625), ``test_at_the_returned_lambda_both_branches_meet`` (there F_f and
F_m differ by 0.0049), ``test_g_changes_sign_across_the_root``,
``test_the_root_needed_the_retry``, ``test_the_switch_moves_the_number``,
``test_a_branch_that_had_a_state_is_never_touched`` (the sweep never reaches
a lost lambda, so the case would otherwise be vacuous),
``test_a_retried_state_says_which_door_it_came_in_by``,
``test_the_retry_starts_from_the_partner`` and
``test_flipping_the_retry_empties_the_cache``.

FIVE fail on the ABSENCE OF A SYMBOL, which is WEAK discrimination and is
labelled here rather than counted as strength: ``test_the_retry_is_counted``,
``test_the_switch_is_on_by_default``,
``test_the_signature_names_every_switch_solve_states_reads``, and the two
bit-identity cases on the fused mass and on GLE, which hold there too and
fail only on ``n_retried``.

FOUR pass on both trees BY DESIGN: ``test_states_is_still_a_pure_function``
(the identity the cache rests on), ``test_without_it_the_arc_comes_from_the_
reserve`` (the control that the witness still exercises the defect), and the
two contract cases ``test_a_retry_that_does_not_converge_leaves_the_none``
and ``test_no_retry_without_a_converged_partner``, which a tree with no retry
satisfies trivially.

The same worktree also runs the two older files whose fixtures this version
moved -- ``test_relaxed_thrust_v1130`` and ``test_thrust_flag_v1185``, 33
cases -- green: the doors their new fixtures open exist on both trees, so
the move does not lean on the retry.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import ast
import contextlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_lambda_closure_v1180 import CIRCULO, _slope  # noqa: E402

REPO = Path(__file__).parent.parent

#: The bank's tolerance since D134, not the 5e-5 the D146 ficha used.
TOL = 1e-4

#: The arc of figure 59.2: from the toe to the published right end.
ARCO = (0.0, 12.583)

#: The grouted tieback of table 59.2: head, tail, capacities, bond and
#: out-of-plane spacing, with the bond length in feet as the table gives it.
CABEZA, COLA = (0.0, 12.4), (36.3, 2.7)
CAPACIDAD = 184077.69
ADHERENCIA = 5000.0
BULBO_FT = 22.0
SEPARACION = 8.0

#: A lambda inside the stretch the retry recovers on this arc (1.175 to
#: 1.55, measured on a grid of 0.025), and next to the root the search
#: brackets.
LAMBDA_PERDIDO = 1.35

_CACHE: dict = {}


# ----------------------------------------------------------------------
# Utilities. Every switch is put back by hand: the runner has no
# ``monkeypatch`` and does not call ``teardown_method`` (rule 5).
# ----------------------------------------------------------------------
@contextlib.contextmanager
def _retry(on):
    """The retry on or off in this process, restored whatever happens.

    ``getattr(..., None)`` so that the file still runs on a tree without the
    switch: there the manager is a no-op and every case that asserts a
    DIFFERENCE fails on a number, not on a collection error.
    """
    import ogr_slip2d.interslice as interslice

    keep = getattr(interslice, "BRANCH_PARTNER_RETRY", None)
    if keep is None:
        yield
        return
    interslice.BRANCH_PARTNER_RETRY = on
    try:
        yield
    finally:
        interslice.BRANCH_PARTNER_RETRY = keep


@contextlib.contextmanager
def _solve_branch_as(wrap):
    """``interslice.solve_branch`` replaced by ``wrap(orig)``, restored."""
    import ogr_slip2d.interslice as interslice

    orig = interslice.solve_branch
    interslice.solve_branch = wrap(orig)
    try:
        yield
    finally:
        interslice.solve_branch = orig


def _anclado():
    """Problem 059 with its tieback, the bank's tolerance and 50 slices."""
    from ogr_core.geometry import Vertex
    from ogr_core.support import GroutedTieback, SupportInstance

    p = _slope(tolerance=TOL)
    t = GroutedTieback(
        tensile_capacity=CAPACIDAD, plate_capacity=CAPACIDAD,
        bond_strength=ADHERENCIA,
        bond_length_percent=100.0 * BULBO_FT / math.dist(CABEZA, COLA),
        out_of_plane_spacing=SEPARACION)
    p.support_types = [t]
    p.add_support(SupportInstance(type_id=t.TYPE_ID, head=Vertex(*CABEZA),
                                  tail=Vertex(*COLA), name="Tieback"))
    return p


def _evalua(on, extremos=ARCO, metodo="spencer"):
    """``(result, system)`` through the door the bank evaluates by.

    ``GridSearch.evaluate_circle`` with the named mass, which is what
    ``ejecutar_caso.py`` does and what reproduces the bank to the digit. The
    system is captured off ``_inner_solve`` and matched to the result by its
    slices, as ``curva_lambda.py`` does: one evaluation may build more than
    one system.
    """
    key = (on, extremos, metodo)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.methods.gle import GLEMorgensternPrice
    from ogr_slip2d.methods.spencer import Spencer
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle

    cls = Spencer if metodo == "spencer" else GLEMorgensternPrice
    grab: list = []
    orig = cls._inner_solve

    def spy(self, slices, lam, system, _o=orig, _g=grab):
        if not any(s is system for _sl, s in _g):
            _g.append((slices, system))
        return _o(self, slices, lam, system)

    p = _anclado()
    circulo = SlipCircle(*CIRCULO)
    if extremos is not None:
        circulo.x_left, circulo.x_right = extremos
    cls._inner_solve = spy
    try:
        with _retry(on):
            r = GridSearch(method=build_method(p, metodo, 50), num_slices=50,
                           min_area=0.0).evaluate_circle(p, circulo)
    finally:
        cls._inner_solve = orig
    assert r is not None, "the circle defines no evaluable mass"
    sistemas = [s for sl, s in grab if sl is r.slices]
    assert sistemas, "no system shares its slices with the result"
    _CACHE[key] = (r, sistemas[0])
    return _CACHE[key]


def _mismo_estado(a, b):
    """Two branch states equal field by field, lists included."""
    if a is None or b is None:
        return a is b
    return (a.fos == b.fos and a.converged == b.converged
            and a.passes == b.passes and a.abandoned == b.abandoned
            and a.rescued == b.rescued and a.normals == b.normals
            and a.resisting == b.resisting and a.boundary_e == b.boundary_e
            and a.boundary_x == b.boundary_x)


# ======================================================================
class TestTheRootItFinds:
    """With the retry, the arc brackets a real Spencer root."""

    def test_with_the_retry_the_arc_brackets(self):
        r, _s = _evalua(True)
        assert r.is_valid
        assert r.details.get("lambda_search_fell_back") is False, (
            "the arc still comes from the reserve: the lost lambdas were not "
            "recovered (fos %r, lambda %r)"
            % (r.fos, r.details.get("lambda")))

    def test_without_it_the_arc_comes_from_the_reserve(self):
        """What v0.1.178 to v0.1.192 answered, reproduced with the switch
        off in THIS process -- the control that says the witness still
        exercises the defect."""
        r, _s = _evalua(False)
        assert r.details.get("lambda_search_fell_back") is True

    def test_the_switch_moves_the_number(self):
        """Rule 7: a switch that does not move the answer is worse than
        none."""
        on, _s1 = _evalua(True)
        off, _s2 = _evalua(False)
        assert on.fos != off.fos
        assert abs(on.details["lambda"] - off.details["lambda"]) > 0.1

    def test_at_the_returned_lambda_both_branches_meet(self):
        """The IDENTITY that defines the root: F_f = F_m there, to the
        solver's tolerance, with both branches converged. Solved afresh
        from the system and not read from the cache."""
        r, s = _evalua(True)
        lam = r.details["lambda"]
        with _retry(True):
            f, m = s._solve_states(lam)
        assert f is not None and f.converged, "force branch lost at the root"
        assert m is not None and m.converged, "moment branch lost at the root"
        assert abs(f.fos - m.fos) <= s.tolerance, (
            "F_f %.9f and F_m %.9f differ by more than the tolerance %g"
            % (f.fos, m.fos, s.tolerance))
        assert abs(r.fos - f.fos) <= s.tolerance
        assert abs(r.fos - m.fos) <= s.tolerance

    def test_g_changes_sign_across_the_root(self):
        """A crossing and not a touching: g = F_f - F_m is positive just
        below the returned lambda and negative just above it."""
        r, s = _evalua(True)
        lam = r.details["lambda"]
        with _retry(True):
            fa, ma = s._solve_states(lam - 0.01)
            fb, mb = s._solve_states(lam + 0.01)
        for st in (fa, ma, fb, mb):
            assert st is not None and st.converged
        assert fa.fos - ma.fos > 0.0 > fb.fos - mb.fos, (
            "g does not change sign across lambda %.6f: %+.3e and %+.3e"
            % (lam, fa.fos - ma.fos, fb.fos - mb.fos))

    def test_the_root_needed_the_retry(self):
        """The force branch AT the root is one the retry produced: without
        it, the same lambda has no force state at all. This is what the
        reserve was covering for."""
        r, s = _evalua(True)
        lam = r.details["lambda"]
        with _retry(True):
            f_on, _m1 = s._solve_states(lam)
        with _retry(False):
            f_off, _m2 = s._solve_states(lam)
        assert f_off is None
        assert f_on is not None and f_on.converged and f_on.retried


# ======================================================================
class TestWhatItCannotReach:
    """Everything the retry cannot touch, measured bit for bit."""

    def test_the_fused_mass_does_not_move_a_bit(self):
        on, s_on = _evalua(True, extremos=None)
        off, _s = _evalua(False, extremos=None)
        assert on.fos == off.fos
        assert on.details["lambda"] == off.details["lambda"]
        assert s_on.n_retried == 0

    def test_gle_on_the_same_arc_does_not_move_a_bit(self):
        """GLE brackets this arc on its own -- its shape function puts the
        root where the force branch converges -- so the retry never fires."""
        on, s_on = _evalua(True, metodo="gle_morgenstern_price")
        off, _s = _evalua(False, metodo="gle_morgenstern_price")
        assert on.fos == off.fos
        assert on.details["lambda"] == off.details["lambda"]
        assert s_on.n_retried == 0

    def test_a_branch_that_had_a_state_is_never_touched(self):
        """Over the whole sampled range of this arc: wherever the force
        branch came back with a state, the retry changes nothing in it, to
        the last list entry. And the sweep is not vacuous: it also finds
        the lambdas the retry does recover."""
        _r, s = _evalua(True)
        recuperados = 0
        for k in range(60):
            lam = -0.5 + 0.05 * k
            with _retry(False):
                f_off, m_off = s._solve_states(lam)
            with _retry(True):
                f_on, m_on = s._solve_states(lam)
            assert _mismo_estado(m_on, m_off), "moment branch moved at %g" % lam
            if f_off is not None:
                assert _mismo_estado(f_on, f_off), (
                    "the retry touched a force branch that had a state at "
                    "lambda %g" % lam)
            elif f_on is not None:
                recuperados += 1
        assert recuperados > 0, "the sweep never reached a lost lambda"

    def test_a_retry_that_does_not_converge_leaves_the_none(self):
        """Injected, because it does not happen on this witness: the retry
        is TAKEN ONLY IF IT CONVERGED, for a retry that returns nothing and
        for one that returns an unconverged state alike."""
        from ogr_slip2d.interslice import BranchState

        _r, s = _evalua(True)
        for devuelve in ("none", "sin_converger"):
            def wrap(orig, _d=devuelve):
                def fake(*a, **kw):
                    if kw.get("rescue_gate") == 1:
                        if _d == "none":
                            return None
                        return BranchState(fos=0.5, converged=False, passes=3,
                                           normals=[], resisting=[],
                                           boundary_e=[], boundary_x=[])
                    return orig(*a, **kw)
                return fake
            with _retry(True), _solve_branch_as(wrap):
                f, m = s._solve_states(LAMBDA_PERDIDO)
            assert m is not None and m.converged
            assert f is None, ("an unconverged retry (%s) was taken" % devuelve)

    def test_no_retry_without_a_converged_partner(self):
        """No partner, no start value, no retry: with the moment branch
        made to fail, the retry is never even attempted."""
        _r, s = _evalua(True)
        intentos: list = []

        def wrap(orig):
            def fake(*a, **kw):
                if kw.get("rescue_gate") == 1:
                    intentos.append(a[4] if len(a) > 4 else None)
                if len(a) > 2 and a[2] is not None:     # the moment branch
                    return None
                return orig(*a, **kw)
            return fake

        with _retry(True), _solve_branch_as(wrap):
            f, m = s._solve_states(LAMBDA_PERDIDO)
        assert m is None and f is None
        assert intentos == []

    def test_the_retry_starts_from_the_partner(self):
        """The start value IS the moment branch's F at the same lambda --
        the one number available without reading another lambda."""
        _r, s = _evalua(True)
        arranques: list = []

        def wrap(orig):
            def spy(*a, **kw):
                if kw.get("rescue_gate") == 1:
                    arranques.append(a[4])
                return orig(*a, **kw)
            return spy

        with _retry(True), _solve_branch_as(wrap):
            _f, m = s._solve_states(LAMBDA_PERDIDO)
        assert m is not None and m.converged
        assert arranques == [m.fos]


# ======================================================================
class TestTheCacheIsStillAnIdentity:
    """``states`` stays a pure function of the system and lambda."""

    def test_the_signature_names_every_switch_solve_states_reads(self):
        """By AST over the BODY of ``GLESystem._solve_states``: every module
        global it reads that is an assignment of the module is in
        ``_STATES_SWITCH_NAMES``, and nothing else is. Called functions and
        classes are not assignments and do not count."""
        import ogr_slip2d.interslice as interslice

        nombres = getattr(interslice, "_STATES_SWITCH_NAMES", None)
        assert nombres is not None, "no second signature on this tree"
        arbol = ast.parse((REPO / "ogr_slip2d" / "interslice.py")
                          .read_text(encoding="utf-8"))
        datos = set()
        for n in arbol.body:
            if isinstance(n, ast.Assign):
                datos.update(t.id for t in n.targets if isinstance(t, ast.Name))
        clase = next(n for n in arbol.body
                     if isinstance(n, ast.ClassDef) and n.name == "GLESystem")
        fn = next(n for n in clase.body
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "_solve_states")
        locales = {a.arg for a in fn.args.args}
        for st in fn.body:
            for sub in ast.walk(st):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    locales.add(sub.id)
        leidos = {x.id for st in fn.body for x in ast.walk(st)
                  if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)
                  and x.id in datos and x.id not in locales}
        assert leidos == set(nombres), (
            "the second signature and what ``_solve_states`` reads have "
            "drifted apart. Missing: %r. Listed but not read: %r."
            % (sorted(leidos - set(nombres)), sorted(set(nombres) - leidos)))

    def test_flipping_the_retry_empties_the_cache(self):
        """A system asked again across a change of the switch must not hand
        back the pair it solved under the other setting."""
        _r, s = _evalua(True)
        with _retry(True):
            f_on, _m1 = s.states(LAMBDA_PERDIDO)
        with _retry(False):
            f_off, _m2 = s.states(LAMBDA_PERDIDO)
        with _retry(True):
            f_again, _m3 = s.states(LAMBDA_PERDIDO)
        assert f_on is not None and f_on.retried
        assert f_off is None, "a stale retried pair came out of the cache"
        assert f_again is not None and f_again.retried

    def test_states_is_still_a_pure_function(self):
        """The retry reads nothing but the system and this lambda: the
        cached pair and a fresh solve agree field by field."""
        _r, s = _evalua(True)
        with _retry(True):
            cached = s.states(LAMBDA_PERDIDO)
            fresh = s._solve_states(LAMBDA_PERDIDO)
        for a, b in zip(cached, fresh):
            assert _mismo_estado(a, b)


# ======================================================================
class TestItIsCountedAndSaid:
    """A retry that fires is counted, and a retried state says so."""

    def test_the_retry_is_counted(self):
        _on, s_on = _evalua(True)
        _off, s_off = _evalua(False)
        assert s_on.n_retried >= 1
        assert s_off.n_retried == 0

    def test_a_retried_state_says_which_door_it_came_in_by(self):
        """Accepted by the rescue's test, so it is ``rescued``; and
        ``retried``, so the census can tell it from the ordinary rescue."""
        _r, s = _evalua(True)
        with _retry(True):
            f, _m = s._solve_states(LAMBDA_PERDIDO)
        assert f is not None and f.converged
        assert f.retried and f.rescued

    def test_the_switch_is_on_by_default(self):
        import ogr_slip2d.interslice as interslice

        assert getattr(interslice, "BRANCH_PARTNER_RETRY", None) is True
