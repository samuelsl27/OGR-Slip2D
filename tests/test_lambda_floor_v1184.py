# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The λ secant stops once its bracket has no double left inside it (D153).

WHAT INVARIANT THIS FILE PROTECTS. That the early cut added in v0.1.184 is an
IDENTITY and not an approximation: on a surface whose bracket has collapsed to
two adjacent doubles, stopping there and spending the rest of
``max_iterations`` produce the same factor, the same λ, the same bracket width
and the same eighteen keys of ``details`` — and the second one costs more
inner solves to say it. If a future change makes the cut fire one turn earlier than
the floor, the factor moves and ``TestTheCutChangesNoDigit`` goes red.

WHY THE MIDPOINT AND NOT A CONSTANT. The guard asks
``0.5 * (lam_lo + lam_hi) == lam_lo or == lam_hi``, which under round-to-
nearest is true exactly when no double lies strictly between the two ends. The
ficha asked for ``eps * max(1.0, abs(lam_lo))`` instead, and that is LOOSER,
not tighter: at ``|λ| < 1`` the bound is two ulps, so a λ can still be left
inside. ``test_the_bracket_is_two_adjacent_doubles`` states the real criterion
with ``math.nextafter`` rather than with any threshold at all.

THE NUMBER THE FICHA PUBLISHED IS NOT THE NUMBER THIS CUT SAVES, and saying so
is half of why this file exists. D153 was opened with "17 calls, the 30 %",
measured on a RELATIVE WINDOW OF 1e-12 over the trace of λ — four orders above
the floor of the double, which is 2**-52. Thirteen of those seventeen are
DISTINCT doubles: λ does move there. At the floor the saving is THREE inner
solves of 57, or 5 %, and ``TestWhatThisDoesNotFix`` keeps the other fourteen
on the record with the reason they cannot be cut: they still have doubles
inside the bracket, so stopping there would end the secant with sampling left
to do, and that WOULD move the factor.

WHERE THE DEFECT ACTUALLY BITES, which is the argument for shipping it. The
floor is reached on pass 48 by GEOMETRY — a 0.2-wide bracket halved down to the
ulp of 0.54 — and not by budget, so the waste is ``max_iterations - 47``. With
the cut off, the witness spends 57 inner solves at the shipped budget of 50 and
207 at 200; with the cut on it spends 54 at BOTH, for the same factor to the
last bit. ``max_iterations`` is a setting the user can raise, and past pass 48
raising it buys nothing at all. Note that ``branch_budget(200) = max(200, 400)``
is still 400, so moving the budget lengthens the secant and leaves the
arithmetic of every branch untouched: the A/B moves one thing.

ON THIS MODEL THE CENSUS SAYS ZERO, and publishing that comes before the fix,
which is the order v0.1.180 wrote down when it reported D153 and deliberately
did not do it. A whole grid search over the 059 model, 1795 surfaces, with the
cut on and then off and the two runs compared surface by surface:

    Spencer, engine as shipped     16077 inner solves ->  16077   (-0)
    GLE, engine as shipped         16355 inner solves ->  16355   (-0)
    Spencer, D145 switched off     17854 inner solves ->  17841  (-13)
    GLE, D145 switched off         17540 inner solves ->  17522  (-18)

ON THIS MODEL AND THE ENGINE AS SHIPPED THE CUT SAVES NOTHING, on either
method: the 4 Spencer surfaces that fail to close λ have brackets 2.1e-2 to
1.3e-1 wide, and the guard never fires. With D145 switched off it does:
4 surfaces of 39 for Spencer and 5 of 23 for GLE.

ONE MODEL IS NOT THE BANK, and the bank answers differently — which is what the
census tool was written for. Whole searches over the verification bank DO find
surfaces whose bracket reaches the floor on the engine as shipped, so the guard
is not dormant there the way the exit of D146 was. The count, its denominator
and the A/B that shows no digit moves are in
``docs/audits/lambda_floor_v1184.md``, and they are what this file's claims
about a real population rest on rather than on the witness alone.

Across all four runs — 7180 surface evaluations — the factor moved on NONE and
no key of ``details`` moved on any, which is the measured answer to the one
real risk: ``branches()`` increments ``n_rescued`` once per CALL, so a λ whose
branch needs the rescue would have counted one more for every turn removed.
Not one did. What moves is ``iterations`` on 4 surfaces and 5, and the sentence
that quotes it. See ``docs/audits/lambda_floor_v1184.md``.

WHAT THIS FILE DOES NOT CLAIM:

* no assertion here fixes a factor of safety against a reference value. Every
  numeric claim is an A/B in one process, an identity, an adjacency of doubles
  or a count of calls the engine actually made. The absolute anchor for this
  witness already exists and is better than a fresh snapshot would be:
  ``test_lambda_closure_v1180.test_the_factor_does_not_move`` pins
  0.5559372612135651 and was written BEFORE the cut existed, so if the cut
  moves the factor that case goes red;
* counts are taken on calls to ``_inner_solve`` and never on
  ``LEMResult.iterations``, which means two different things in this method —
  grid samples plus secant turns on the bracketed exit, samples alone on the
  fallback one. ``iterations`` is asserted only where the claim IS about
  ``iterations``;
* nothing here says the cut is worth having on today's engine. It is worth
  zero there, measured, and the argument is the budget and the identity.

WHICH CASES MEASURE THE CHANGE AND WHICH ARE CONTROL, run and not remembered.
Measured against the tree of 0.1.183 with the three engine files stashed and
this file plus the ``max_it`` parameter of ``_slope`` in place: of the 38 cases
in this file and its neighbour, 9 FAIL and 29 PASS.

EIGHT fail on a measured difference, which is the real coverage:

* ``test_the_cut_saves_the_turns_at_the_floor`` — there it saves 0 and not 3;
* ``test_the_published_iteration_count_drops_too`` — 56 against 56;
* ``test_and_the_message_is_the_only_text_that_changes`` — the sentence is
  the same one, because the iteration count it quotes has not moved;
* ``test_with_the_cut_the_budget_stops_being_visible`` — 57 inner solves at a
  budget of 50 and 207 at 200, which is the defect itself;
* ``test_the_saving_grows_with_the_budget_and_the_answer_does_not`` — 0, not
  153;
* ``test_and_spends_less_for_the_same_factor`` — the GLE half of the same;
* and in ``test_lambda_closure_v1180``, both halves of the re-anchored case:
  ``test_the_bracket_floor_no_longer_re_solves_the_same_lambda`` and
  ``test_one_repeat_of_the_final_lambda_survives_the_cut`` see 4 exact repeats
  of the final λ where this version leaves 1.

ONE fails on the ABSENCE of a symbol rather than on a number:
``test_the_switch_is_on_by_default``. That is WEAK discrimination and is
labelled rather than counted as strength.

THE FOUR CASES OF ``TestTheCutChangesNoDigit`` PASS ON BOTH TREES ON PURPOSE.
With no constant to flip, ``_floor_cut`` is a no-op and they compare a run with
itself, so they say nothing there — and that is what they are for: they are the
identity, and the day the cut stops being one they go red on the tree that has
it. ``TestTheBracketReallyReachesTheFloor`` and
``test_without_the_cut_a_bigger_budget_buys_only_calls`` are declared CONTROL
and green on both trees by construction; the last measures the fixed point
WITHOUT needing the switch at all, which is why it is the control for the
rest.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_lambda_closure_v1180 import (  # noqa: E402
    CIRCULO, N_DOVELAS, TOL_FICHA, _pair_off, _slope,
)

#: The GLE witness, and it has to be a different circle: on the circle of
#: figure 59.2 GLE closes λ in ten inner solves and never reaches the floor, so
#: putting the same guard in ``gle.py`` on the strength of Spencer's witness
#: would be an adjustment no case in that method can reach — rule 7 in the
#: twin. Found by walking a whole grid search of the same model with D145
#: switched off and D153 off: 6 of its 23 non-closing surfaces sit at the
#: floor, and this is the first of them.
CIRCULO_GLE = (-32.0, 69.66666666666666, 78.86964881062671)

#: Both branches take a while, and six classes below want the same answers.
_CACHE: dict = {}


@contextlib.contextmanager
def _floor_cut(on):
    """The cut on or off, in this process, restored by hand.

    ``getattr(..., None)`` so the file still runs against a tree that has no
    such constant, instead of turning all nineteen cases into collection
    errors — and "nineteen errors" says nothing about which of them measure
    the change. There the manager is a no-op, so every case that asserts a
    DIFFERENCE between the two runs fails on a number, which is the strong
    half of the breakdown above. The restoring is written out because the
    runner has no ``monkeypatch`` and does not call ``teardown_method``
    (rule 5).
    """
    import ogr_slip2d.interslice as interslice

    keep = getattr(interslice, "LAMBDA_BRACKET_FLOOR_CUT", None)
    if keep is None:
        yield
        return
    interslice.LAMBDA_BRACKET_FLOOR_CUT = on
    try:
        yield
    finally:
        interslice.LAMBDA_BRACKET_FLOOR_CUT = keep


def _method(method_id):
    from ogr_slip2d.methods.gle import GLEMorgensternPrice
    from ogr_slip2d.methods.spencer import Spencer

    return Spencer if method_id == "spencer" else GLEMorgensternPrice


def _run(method_id="spencer", cut=True, max_it=None):
    """``(result, every λ the engine solved, in order)`` on a floor witness.

    The same spy ``test_lambda_closure_v1180._trace`` uses, kept here because
    this one has to reach two methods and two circles. It annotates and
    forwards the call untouched, so the engine's own answer cannot differ from
    the one measured without it.
    """
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.surface import SlipCircle

    clave = (method_id, bool(cut), max_it)
    if clave in _CACHE:
        return _CACHE[clave]

    circulo = CIRCULO if method_id == "spencer" else CIRCULO_GLE
    cls = _method(method_id)
    traza: list = []
    orig = cls._inner_solve

    def spy(self, slices, lam, system, _o=orig, _t=traza):
        ff, fm = _o(self, slices, lam, system)
        _t.append(float(lam))
        return ff, fm

    cls._inner_solve = spy
    try:
        with _pair_off(), _floor_cut(cut):
            p = _slope(TOL_FICHA, N_DOVELAS, max_it)
            r = build_search(p, method_id).evaluate_surface(
                p, SlipCircle(*circulo))
    finally:
        cls._inner_solve = orig
    _CACHE[clave] = (r, traza)
    return r, traza


# ======================================================================
class TestTheBracketReallyReachesTheFloor:
    """CONTROL. Without this, everything below is about a different state."""

    def test_the_witness_does_not_close_lambda(self):
        """Both witnesses take the exit the cut lives on, or nothing applies."""
        for mid in ("spencer", "gle_morgenstern_price"):
            r, _t = _run(mid, cut=False)
            assert not r.converged, (
                "%s closes λ on its witness now; the fixture has stopped "
                "producing the state D153 is about" % mid)
            assert r.reason == "lambda_not_closed", (
                "%s answers %r and not the λ reason" % (mid, r.reason))

    def test_the_bracket_is_two_adjacent_doubles(self):
        """The criterion stated exactly, with no threshold anywhere in it.

        ``lambda`` is the low end and ``lambda_bracket_width`` the distance to
        the high one, so the bracket has nothing inside it exactly when the
        next representable double above the low end IS the high end. This is
        what the guard asks; the ficha's ``eps * max(1, |λ|)`` would also admit
        a bracket two ulps wide, which still has a λ in it.
        """
        for mid in ("spencer", "gle_morgenstern_price"):
            r, _t = _run(mid, cut=False)
            lam = r.details["lambda"]
            ancho = r.details["lambda_bracket_width"]
            assert math.nextafter(lam, math.inf) == lam + ancho, (
                "%s: the bracket is %r wide at λ = %r, which is more than one "
                "ulp. The floor is not reached and the cut below is measuring "
                "something else." % (mid, ancho, lam))

    def test_and_the_residual_clears_the_tolerance_with_room(self):
        """The guard's second half is satisfied here, and by how much.

        The cut also asks that BOTH ends of the bracket be at or above the
        tolerance, because a bracket end taken straight from the grid was
        never tested against it and the loop could still close on one. The
        residual published at the returned λ is that end's own ``|g|``; the
        margin is thin on one witness and wide on the other, and both are
        stated rather than hidden.
        """
        for mid, veces in (("spencer", 40.0), ("gle_morgenstern_price", 4.0)):
            r, _t = _run(mid, cut=False)
            resid = r.details["lambda_residual"]
            tol = r.details["lambda_tolerance"]
            assert resid >= veces * tol, (
                "%s: the residual is %r against a tolerance of %r, only %.1f "
                "times it. Below 1.0 the guard would stand aside and the cut "
                "would never fire on this witness."
                % (mid, resid, tol, resid / tol))


# ======================================================================
class TestTheCutChangesNoDigit:
    """The criterion of the ficha, literally: same λ and same factor.

    WEAK discrimination against a tree without the constant, where
    ``_floor_cut`` is a no-op and these compare a run with itself. Labelled,
    not counted as strength.
    """

    def test_the_factor_is_the_same_double(self):
        for mid in ("spencer", "gle_morgenstern_price"):
            con, _a = _run(mid, cut=True)
            sin, _b = _run(mid, cut=False)
            assert con.fos == sin.fos, (
                "%s: the cut moved the factor, %r against %r. The loop state "
                "past the floor was supposed to be a fixed point."
                % (mid, con.fos, sin.fos))

    def test_the_lambda_and_the_width_are_the_same_doubles(self):
        for mid in ("spencer", "gle_morgenstern_price"):
            con, _a = _run(mid, cut=True)
            sin, _b = _run(mid, cut=False)
            assert con.details["lambda"] == sin.details["lambda"]
            assert (con.details["lambda_bracket_width"]
                    == sin.details["lambda_bracket_width"])
            assert (con.details["lambda_residual"]
                    == sin.details["lambda_residual"])

    def test_the_verdict_and_the_reason_do_not_move(self):
        for mid in ("spencer", "gle_morgenstern_price"):
            con, _a = _run(mid, cut=True)
            sin, _b = _run(mid, cut=False)
            for campo in ("converged", "reason", "admissible",
                          "admissibility_note", "is_valid"):
                assert getattr(con, campo) == getattr(sin, campo), (
                    "%s: %s moved, %r against %r"
                    % (mid, campo, getattr(con, campo), getattr(sin, campo)))

    def test_nothing_in_details_moves_at_all(self):
        """The whole dictionary, because a key nobody thought of is the risk.

        This is the case that answers, in the suite and not in a comment,
        whether a wasted turn can move a published counter. ``branches()``
        increments ``n_rescued`` once per CALL, so a λ whose branch needs the
        rescue would count one more for every turn the cut removes; the four
        ``lambdas_lost_to_*`` counters cannot move, because a bracket end has
        both branches converged by construction and the guards in
        ``interslice.py`` return early on it.
        """
        for mid in ("spencer", "gle_morgenstern_price"):
            con, _a = _run(mid, cut=True)
            sin, _b = _run(mid, cut=False)
            movidas = sorted(k for k in set(con.details) | set(sin.details)
                             if con.details.get(k) != sin.details.get(k))
            assert movidas == [], (
                "%s: the cut moved %s in details. If that is "
                "`lambdas_rescued`, the changelog owes the bank a number."
                % (mid, movidas))


# ======================================================================
class TestItSpendsLessToSayTheSameThing:
    """Rule 7: an adjustment that changes nothing is worse than none."""

    def test_the_cut_saves_the_turns_at_the_floor(self):
        for mid, ahorro in (("spencer", 3), ("gle_morgenstern_price", 3)):
            _c, con = _run(mid, cut=True)
            _s, sin = _run(mid, cut=False)
            assert len(sin) - len(con) == ahorro, (
                "%s saves %d inner solves and not %d (%d against %d). Each "
                "turn past the floor is exactly one solve, because the "
                "double-solve path needs a branch pair to fail and the ends "
                "already produced good ones."
                % (mid, len(sin) - len(con), ahorro, len(con), len(sin)))

    def test_the_published_iteration_count_drops_too(self):
        for mid in ("spencer", "gle_morgenstern_price"):
            con, _a = _run(mid, cut=True)
            sin, _b = _run(mid, cut=False)
            assert con.iterations < sin.iterations, (
                "%s: iterations did not drop (%d against %d)"
                % (mid, con.iterations, sin.iterations))

    def test_and_the_message_is_the_only_text_that_changes(self):
        """The one published string the cut moves, said out loud.

        The sentence carries ``%d`` of ``iterations`` inside it, so it changes
        whenever the cut fires — and ``LEMResult.to_dict`` archives it as
        ``error``. It is the only text that moves: the reason and the
        admissibility note are identical.
        """
        con, _a = _run("spencer", cut=True)
        sin, _b = _run("spencer", cut=False)
        assert con.error_message != sin.error_message, (
            "the message did not change, so it is not quoting the iteration "
            "count any more and this case has stopped meaning anything")
        assert con.reason == sin.reason
        assert con.admissibility_note == sin.admissibility_note


# ======================================================================
class TestTheBudgetIsWhereItBites:
    """The argument of the whole version, executed rather than written."""

    def test_without_the_cut_a_bigger_budget_buys_only_calls(self):
        """CONTROL, and green on both trees: the defect as an identity.

        Quadrupling ``max_iterations`` on a collapsed bracket produces the
        same factor, the same λ and the same width, and 150 more inner solves
        to produce them. This is the fixed point measured WITHOUT needing the
        switch at all, which is why it is the control for everything above.
        """
        for mid in ("spencer", "gle_morgenstern_price"):
            corto, tc = _run(mid, cut=False, max_it=50)
            largo, tl = _run(mid, cut=False, max_it=200)
            assert corto.fos == largo.fos, (
                "%s: the extra budget moved the factor, %r against %r"
                % (mid, corto.fos, largo.fos))
            assert corto.details["lambda"] == largo.details["lambda"]
            assert (corto.details["lambda_bracket_width"]
                    == largo.details["lambda_bracket_width"])
            assert len(tl) - len(tc) == 150, (
                "%s: the extra budget bought %d extra inner solves, not 150. "
                "If this is 0 the loop is leaving by some other exit and the "
                "defect is not what it was." % (mid, len(tl) - len(tc)))

    def test_with_the_cut_the_budget_stops_being_visible(self):
        """The strong discriminator, and it does not need the switch.

        On 0.1.183 these differ by 150. On 0.1.184 they are equal, because the
        loop leaves at the floor and the floor is set by geometry.
        """
        for mid in ("spencer", "gle_morgenstern_price"):
            _a, corto = _run(mid, cut=True, max_it=50)
            _b, largo = _run(mid, cut=True, max_it=200)
            assert len(corto) == len(largo), (
                "%s still spends the budget: %d inner solves at 50 and %d at "
                "200. The cut is not firing." % (mid, len(corto), len(largo)))

    def test_the_saving_grows_with_the_budget_and_the_answer_does_not(self):
        for mid in ("spencer", "gle_morgenstern_price"):
            con, tc = _run(mid, cut=True, max_it=200)
            sin, ts = _run(mid, cut=False, max_it=200)
            assert len(ts) - len(tc) == 153, (
                "%s saves %d inner solves at a budget of 200, not 153"
                % (mid, len(ts) - len(tc)))
            assert con.fos == sin.fos


# ======================================================================
class TestTheTwinLoopGotTheSameCut:
    """``gle.py`` keeps the λ search of ``spencer.py`` line for line."""

    def test_gle_reaches_the_floor_on_its_own_witness(self):
        r, _t = _run("gle_morgenstern_price", cut=False)
        lam = r.details["lambda"]
        assert math.nextafter(lam, math.inf) == (
            lam + r.details["lambda_bracket_width"])

    def test_and_spends_less_for_the_same_factor(self):
        con, tc = _run("gle_morgenstern_price", cut=True)
        sin, ts = _run("gle_morgenstern_price", cut=False)
        assert len(tc) < len(ts), (
            "GLE spends %d inner solves with the cut and %d without it: the "
            "twin loop did not get the guard, or its witness stopped reaching "
            "the floor" % (len(tc), len(ts)))
        assert con.fos == sin.fos, (
            "GLE: the cut moved the factor, %r against %r"
            % (con.fos, sin.fos))

    def test_the_switch_is_on_by_default(self):
        """Rule 7 from the other side: the shipped default does the cut.

        WEAK discrimination — on 0.1.183 this fails on a missing symbol and
        not on a number.
        """
        import ogr_slip2d.interslice as interslice

        assert getattr(interslice, "LAMBDA_BRACKET_FLOOR_CUT", None) is True


# ======================================================================
class TestWhatThisDoesNotFix:
    """Reported and NOT corrected (rule 6)."""

    def test_the_turns_inside_the_fichas_window_are_still_spent(self):
        """The fourteen the cut cannot reach, and why it must not.

        D153 counted with a relative window of 1e-12 and called the result "a
        λ that cannot move". Most of that tail is DISTINCT doubles, so there
        are λ still to sample there: cutting them would end the secant early
        and move the factor. What grinds there is the bracket halving against
        a discontinuous g, which is D145's subject, closed in v0.1.179.
        """
        _r, traza = _run("spencer", cut=True)
        ultimo = traza[-1]
        cola = [lam for lam in traza
                if abs(lam - ultimo) <= 1e-12 * max(1.0, abs(ultimo))]
        assert len(set(cola)) > 10, (
            "only %d of the %d calls inside the window are distinct doubles. "
            "If that has collapsed to one, the window and the floor have "
            "become the same thing." % (len(set(cola)), len(cola)))

    def test_one_repeat_of_the_final_lambda_survives_the_cut(self):
        """D159, found while measuring this one and CLOSED in v0.1.186.

        After the cut the only call that still repeats a λ exactly is the
        ``solve(lam_lo)`` that follows the loop, which asks for a pair the loop
        already holds in ``ff_lo, fm_lo`` and never reads. Over a whole Spencer
        search that is 1795 of 17872 branch pairs, and the
        ``system.states(lam_lo)`` two lines below it is another 1795 — 20.0 %
        of the method, asking twice for what it already has.

        v0.1.186 (D159) — and the repair KEPT BOTH CALLS, which is why this
        count is still 1 and not 0. What it removed is the re-solve
        underneath, with a per-λ cache in ``GLESystem.states``; the calls stay
        because each one is a call to ``branches``, and ``branches`` is where
        every counter ``details`` publishes gets incremented. The other repair
        the ficha offered — dropping the call and using ``ff_lo, fm_lo`` —
        would have moved them. So this trace is untouched by that version, and
        the count that dropped is pinned in
        ``tests/test_lambda_state_cache_v1186.py``.
        """
        _r, traza = _run("spencer", cut=True)
        ultimo = traza[-1]
        repetidas = sum(1 for lam in traza if lam == ultimo) - 1
        assert repetidas == 1, (
            "%d calls repeat the final λ exactly, not 1. Before the cut there "
            "were 4; 0 would mean the final CALL went, which D159 deliberately "
            "did not remove." % repetidas)

    def test_the_other_guard_in_this_loop_still_has_no_birth_certificate(self):
        """``abs(g_hi - g_lo) < 1e-12`` is the last bare number in here.

        Every other constant of the λ search carries a ``#:`` block saying
        where it came from and what it was measured on. This one is a literal
        in the middle of the loop, in a project where D120 left written what a
        threshold without a provenance costs. Not touched by this version, and
        this case is the record that it was seen.
        """
        import ast
        import io

        fuente = io.open(
            Path(__file__).parent.parent / "ogr_slip2d" / "methods"
            / "spencer.py", encoding="utf-8").read()
        assert "abs(g_hi - g_lo) < 1e-12" in fuente, (
            "the bare 1e-12 is gone from spencer.py. If it was given a named "
            "constant with a block of its own, delete this case; if it was "
            "merely moved, this file has stopped watching it.")
        ast.parse(fuente)
