# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.180 (D146) — when the λ search fails, it says that λ is what failed.

WHAT INVARIANT THIS PROTECTS. Spencer and GLE find their answer by bracketing
the inter-slice inclination λ where the force and the moment factors of safety
agree, and then refining that bracket with a secant. The refinement has two
early exits — ``|g_hi - g_lo| < 1e-12`` and ``|g_new| < tolerance`` — and when
neither fires it spends the whole of ``max_iterations`` and hands back a
result. Until this version that result carried ``REASON_NOT_CONVERGED`` and
``NOT_CONVERGED_NOTE``, which is the code AND the sentence that Bishop and
Janbu give for their own, unrelated loop: "the factor of safety iteration did
not converge". Two loops that fail for unrelated reasons cannot be told apart
by a caller that groups by reason, and grouping is the entire purpose of those
constants (D56). Worse, ``analysis_runner.lambda_fallback_notes`` was gated
behind ``lambda_search_fell_back``, so the one exit of this search with most
to explain was the only one that narrated nothing at all.

WHAT THE FICHA ASKED FOR, AND WHAT THE MEASUREMENT SAID INSTEAD. D146 reports
that on the published circle of verification problem 059, stripped of its
support and at a tolerance of 5e-5, the moment branch is BISTABLE — two fixed
points 0.9 % apart, 0.557124544 and 0.552329138, alternating between two
adjacent doubles of λ — so that g jumps sign without crossing zero and the
secant burns its 50 iterations. The numbers reproduce exactly. The mechanism
does not survive being measured:

  * at that λ the moment branch has ONE attractor, not two. Started from nine
    values of F between 0.3 and 3.0 it lands on 0.557096 to 0.557239 every
    time, all ``converged=True`` and none rescued. Those nine agree to 2.6e-4
    of each other, which is thirty times closer together than any of them is
    to 0.552329138 — the spread of one fixed point, not the gap between two;
  * over thirteen ADJACENT doubles of λ the engine as shipped returns one
    value of F_m, on pass 27 in all thirteen. With ``BRANCH_PAIR_TIGHTEN``
    and ``BRANCH_PAIR_SETTLE`` off it returns two, and the second is admitted
    on pass ELEVEN. 0.552329138 is not a fixed point at all: it is the
    premature acceptance of D145, an alternating step sequence sneaking under
    a loose tolerance, seen from the outside;
  * and the tie-breaker is the tolerance. With those switches off the failure
    exists at 5e-5 and at NO other tolerance measured — 1e-3, 5e-4, 1e-4,
    1e-5, 1e-6 and 1e-7 all close, and the loose ones close near 0.5523 while
    the tight ones close near 0.5594. A real discontinuity of g does not care
    what tolerance you ask for; a premature acceptance is undone by tightening
    it, and that is what happens.

So D146 is D145 seen from the λ loop, and v0.1.179 closed it without anyone
noticing. What this version fixes is the half that is independent of the
refuted mechanism: the exit itself, which could not say what it was.

HOW THE RULE 7 GATE WAS BUILT, because a test of a defect that cannot see the
defect is the trap this project has now walked into ten times (D101, D103,
D118, D127, D129). This change has no switch of its own and does not need one:
the pre-change tree is reachable from here as "the reason is the shared one",
so every case that claims a difference asserts against the string the engine
used to give. The witness that makes the failing exit happen at all is
``_pair_off()``, the in-process switch D145 already ships, and that is said
out loud rather than hidden — see the last class.

WHICH CASES MEASURE THE CHANGE AND WHICH ARE CONTROL, counted rather than
asserted and NAMED rather than counted, because a file that only gives a tally
will be read as one where every case discriminates. Measured against the tree
of 0.1.179 with only this file added: 6 of the 18 FAIL and 12 PASS.

FOUR fail on a measured difference, which is the real coverage:

* ``test_the_reason_is_not_the_one_bishop_and_janbu_give`` — there the λ
  search answers ``not_converged``, the string of another loop;
* ``test_the_message_names_the_residual_the_width_and_the_iterations`` — there
  the sentence is "The factor of safety iteration did not converge within the
  maximum number of iterations", which does not contain the character λ;
* ``test_the_note_reaches_the_user`` — there the note list comes back empty,
  because the gate asks ``lambda_search_fell_back`` and a bracket WAS found;
* ``test_the_three_keys_are_there_when_it_does_not_close`` — there it names
  the key that is missing.

TWO fail on the ABSENCE of a symbol rather than on a number:
``test_the_reason_is_declared`` (no such constant) and
``test_the_residual_is_none_when_a_root_was_closed`` (KeyError). That is WEAK
discrimination and is labelled rather than counted as strength.

THREE of the twelve that pass are MEANT to, and would be broken if they moved:
``test_the_factor_does_not_move`` and ``test_the_factor_of_the_solved_root_
does_not_move_either`` pin that neither exit's number budged, and
``test_the_loop_keeps_solving_after_the_bracket_stops_moving`` describes
what was NOT done.
The three cases of ``TestTheJumpWasAPrematureAcceptance`` pass on both trees
on purpose: they are about whose defect this was — D145's — and not about this
version, so a difference there would mean the refutation had stopped holding.
The rest are the declared CONTROL classes.

THE EXIT IS DORMANT IN THE VERIFICATION BANK, and publishing that zero is the
point rather than an embarrassment. The census ``_tools/cierre_lambda_d146.py``
walked 344 rows over 79 problems — 236 archived critical surfaces and 108
published ones, 18 skipped with their reason — and NOT ONE takes this exit on
the engine as shipped. Not at the tolerance each problem declares, and not at
a forced 1e-8 either, which is ten thousand times tighter than the bank's own.
With the two D145 switches off it takes it once, on the archived Spencer
critical of problem 027, with the bracket collapsed to 8.0e-14 and a residual
of 11.6 times the tolerance. So the reason this version adds cannot move a
published number, and the changelog says so with the denominator in front.

WHY THE FIXTURE IS WRITTEN IN CODE. ``tests/`` cannot reach the verification
bank, and it should not: a test that needs a directory outside the repository
is a test that fails on a clean machine. The slope below is problem 059 —
seven profile vertices, a 24-vertex water table, one cohesionless sand — and
it reproduces the bank DIGIT FOR DIGIT: 0.559260053369 against the bank's own
model on the same circle, with the same 50 slices, the same mass (x from
-40.75818 to 12.60680) and the same Σu·l. That check was run before any of the
assertions below were written.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a change delivers is what cost this project two versions in v0.1.82-84:

* no assertion here fixes a factor of safety against a reference value. Every
  numeric claim is an A/B in one process, an identity, a count of iterations,
  or a comparison against a number this same file computes;
* the early cut is NOT implemented. A collapsed bracket still spends the whole
  of ``max_iterations`` before saying so, and ``TestWhatThisDoesNotFix`` pins
  that it does, so the day someone adds the cut this file tells them what they
  changed;
* nothing here says which fixed point is "physical". The question the ficha
  asked has no object: there is one;
* the mass evaluated is the FUSED one that D147 describes, not the 12.58 ft
  arc of figure 59.2. That is the ficha's own configuration, kept on purpose
  so that these numbers can be compared with the ones it published.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

# ----------------------------------------------------------------------
# Verification problem 059 — the ficha's own configuration, in code.
# Its support is simply never built: the ficha strips it in memory, and a
# support that is not there cannot be forgotten.
PERFIL = [(-50.0, -30.0), (40.0, -30.0), (40.0, 35.0), (0.0, 20.0),
          (0.0, 0.0), (-10.0, 0.0), (-50.0, -15.0)]
NIVEL = [(-50.0, -15.0), (-10.0, 0.0), (0.0, 0.0), (1.5, 6.2), (3.3, 13.9),
         (5.2, 17.5), (7.1, 19.7), (9.0, 21.2), (10.9, 22.2), (12.8, 23.1),
         (14.7, 23.9), (16.6, 24.6), (18.5, 25.2), (20.4, 25.9), (22.3, 26.6),
         (24.2, 27.3), (26.1, 27.9), (27.9, 28.7), (29.8, 29.4), (31.7, 30.1),
         (33.6, 30.7), (35.5, 31.4), (37.4, 32.1), (40.0, 33.0)]

#: The published circle of figure 59.2, with the radius as published.
CIRCULO = (-30.872, 31.315, 43.975)

#: The tolerance at which the pre-D145 engine fails on this circle, and the
#: one the ficha used. Not a round number and not a choice of this file.
TOL_FICHA = 5e-5

#: The λ the ficha names, as the double the search actually visits.
LAMBDA_SALTO = 0.54247266903303981

#: The two values the ficha calls "two fixed points". The first is the
#: attractor; the second is what the pre-D145 acceptance returned on pass 11.
F_M_ATRACTOR = 0.557124544
F_M_PREMATURO = 0.552329138

#: The slices the bank runs this problem with.
N_DOVELAS = 50

_CACHE: dict = {}


def _slope(tolerance=TOL_FICHA, n=N_DOVELAS):
    """Problem 059 without its support.

    ``pore_pressure`` is passed as the ENUM and not as the string
    ``"water_table"``, and that is load-bearing rather than tidy:
    :class:`Material` stores whatever it is given without coercing it, so the
    string compares unequal to every member of ``PorePressureType`` and the
    sand comes out DRY with no error of any kind. Measured on this very
    circle: 1.0886090318268722 instead of 0.5592600533686025. The ``.ogr``
    loader coerces (``PorePressureType(data.get(...))``) and the constructor
    does not, which is why a model built in code can silently disagree with
    the same model loaded from disk. Reported in the changelog of this
    version and not fixed here.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project

    p = Project("059")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in PERFIL], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(x, y) for x, y in NIVEL]),
        btype=BoundaryType.WATER_TABLE))
    sand = Material(name="Sand", unit_weight=120.0, sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0),
                    pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [sand]
    for reg in p.resolve_regions():
        cx, cy = reg.centroid()
        p.assign_material_at(cx, cy, sand.id)
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.methods.num_slices = n
    p.settings.methods.tolerance = tolerance
    return p


def _evaluate(tolerance=TOL_FICHA, method_id="spencer", n=N_DOVELAS):
    """The circle through the SAME door the search uses.

    ``build_search(...).evaluate_surface(...)`` and not ``compute_fos`` on a
    bare circle: a ``SlipCircle`` built from a centre and a radius arrives
    unresolved, and this circle cuts the ground more than twice, so the
    slicer would take the first mass from the left rather than the one the
    bank measured. Same door, same mass, same digits.
    """
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.surface import SlipCircle

    p = _slope(tolerance, n)
    return build_search(p, method_id).evaluate_surface(p, SlipCircle(*CIRCULO))


def _system(tolerance=TOL_FICHA):
    """The ``GLESystem`` the METHOD builds, captured off the class.

    Captured and not rebuilt: the system is a local of ``compute_fos`` and no
    public door returns it, while ``_inner_solve`` receives it as its fourth
    argument. The spy annotates and forwards the call untouched, so the
    engine's own answer cannot differ from the one the bank measured. Cached
    because building it slices the surface, and several classes below want
    the same one.
    """
    from ogr_slip2d.methods.spencer import Spencer
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.surface import SlipCircle

    if tolerance in _CACHE:
        return _CACHE[tolerance]
    grab: list = []
    orig = Spencer._inner_solve

    def spy(self, slices, lam, system, _o=orig, _g=grab):
        if not _g:
            _g.append(system)
        return _o(self, slices, lam, system)

    Spencer._inner_solve = spy
    try:
        p = _slope(tolerance)
        build_search(p, "spencer").evaluate_surface(p, SlipCircle(*CIRCULO))
    finally:
        Spencer._inner_solve = orig
    assert grab, "no inner solve happened: the fixture stopped exercising λ"
    _CACHE[tolerance] = grab[0]
    return grab[0]


def _moment(system, lam, f0=None):
    """The moment branch at one λ, from the engine's own solver."""
    from ogr_slip2d.interslice import solve_branch

    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos, system.tolerance,
                        system.initial_fos if f0 is None else f0,
                        max_passes=system.max_passes)


@contextlib.contextmanager
def _pair_off(tighten=True, settle=True):
    """The acceptance of 0.1.178, in this process.

    The runner has no ``monkeypatch`` and does not run ``teardown_method``, so
    the restoring is written out (rule 5). A tree without the switches has
    nothing to turn off, and there the CONTROL cases still mean what they say
    while the discriminating ones fail — which is the point of them.
    """
    import ogr_slip2d.interslice as interslice
    keep_t = getattr(interslice, "BRANCH_PAIR_TIGHTEN", None)
    keep_s = getattr(interslice, "BRANCH_PAIR_SETTLE", None)
    if keep_t is None or keep_s is None:
        yield
        return
    if tighten:
        interslice.BRANCH_PAIR_TIGHTEN = False
    if settle:
        interslice.BRANCH_PAIR_SETTLE = False
    try:
        yield
    finally:
        interslice.BRANCH_PAIR_TIGHTEN = keep_t
        interslice.BRANCH_PAIR_SETTLE = keep_s


def _adjacent(lam, k=6):
    """``2k+1`` consecutive doubles centred on ``lam``."""
    out = [lam]
    x = lam
    for _ in range(k):
        x = math.nextafter(x, 1.0)
        out.append(x)
    x = lam
    for _ in range(k):
        x = math.nextafter(x, 0.0)
        out.insert(0, x)
    return out


def _trace(tolerance=TOL_FICHA):
    """``(result, every λ the engine actually solved, in order)``.

    The same capture ``_system`` uses, kept separate because this one wants
    the whole list and not the object. It is how the cost claim below is
    MEASURED rather than inferred from ``LEMResult.iterations``, which means
    two different things in this method — the grid samples plus the secant
    turns on this exit, and only the samples on the fallback one.
    """
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.methods.spencer import Spencer
    from ogr_slip2d.surface import SlipCircle

    traza: list = []
    orig = Spencer._inner_solve

    def spy(self, slices, lam, system, _o=orig, _t=traza):
        ff, fm = _o(self, slices, lam, system)
        _t.append(float(lam))
        return ff, fm

    Spencer._inner_solve = spy
    try:
        p = _slope(tolerance)
        r = build_search(p, "spencer").evaluate_surface(p, SlipCircle(*CIRCULO))
    finally:
        Spencer._inner_solve = orig
    return r, traza


def _reason_constant():
    """``REASON_LAMBDA_NOT_CLOSED``, or ``None`` on a tree without it.

    Read with ``getattr`` and not imported at module level ON PURPOSE: an
    ImportError here would turn every case in this file into a collection
    error against the previous tree, and "18 errors" says nothing about which
    cases measure the change. This way the cases that need it fail on the
    value, one by one, and the header above can name them.
    """
    from ogr_slip2d.methods import base

    return getattr(base, "REASON_LAMBDA_NOT_CLOSED", None)


# ======================================================================
class TestTheMomentBranchHasOneFixedPoint:
    """The refutation. CONTROL: true on both trees, and meant to be.

    D146 says the branch is bistable. It is not, and the cheapest way to see
    it is to start the iteration from nine different places: a map with two
    attractors sends different starts to different limits, and this one does
    not. What the nine DO show is the residual gap of a slow contraction that
    ``test_branch_contraction_v1172`` already measures — a branch stopped on a
    step of ``tol`` sits within ``tol*r/(1-r)`` of its root — which is why
    they agree to 2.6e-4 and not to 1e-12.
    """

    def test_nine_starts_reach_the_same_attractor(self):
        system = _system()
        vals = []
        for f0 in (0.3, 0.5, 0.5523, 0.5547, 0.5571, 0.6, 1.0, 1.5, 3.0):
            st = _moment(system, LAMBDA_SALTO, f0)
            assert st is not None, "the branch vanished from start F = %g" % f0
            assert st.converged, (
                "the branch from start F = %g did not converge, so this case "
                "is no longer measuring where it lands" % f0)
            assert not st.rescued, (
                "the branch from start F = %g needed the relaxation rescue; "
                "that is a different mechanism and would make the comparison "
                "below mean something else" % f0)
            vals.append(st.fos)
        spread = (max(vals) - min(vals)) / min(vals)
        assert spread < 1e-3, (
            "the nine starts no longer agree (relative spread %.3e): either "
            "the fixture stopped being the one that was measured, or there "
            "really are two attractors now" % spread)

    def test_and_it_is_nowhere_near_the_second_value_the_ficha_reports(self):
        system = _system()
        vals = [_moment(system, LAMBDA_SALTO, f0).fos
                for f0 in (0.3, 0.5, 0.6, 1.0, 1.5, 3.0)]
        spread = max(vals) - min(vals)
        gap = abs(F_M_ATRACTOR - F_M_PREMATURO)
        assert gap > 10.0 * spread, (
            "the six starts scatter by %.3e while the ficha's two 'fixed "
            "points' are %.3e apart. They are no longer separable, so this "
            "case can no longer tell one attractor from two." % (spread, gap))
        for v in vals:
            assert abs(v - F_M_ATRACTOR) < abs(v - F_M_PREMATURO), (
                "a start landed closer to %.9f, the value the pre-D145 "
                "acceptance returned, than to the attractor %.9f"
                % (F_M_PREMATURO, F_M_ATRACTOR))


# ======================================================================
class TestTheJumpWasAPrematureAcceptance:
    """Whose defect it was. DISCRIMINATES against the 0.1.178 acceptance.

    Every case here is an A/B in one process against ``_pair_off()``. None of
    them discriminates against the tree of 0.1.179, because none of them is
    about this version's change: they are about WHY the ficha's symptom is
    gone, and the answer is D145.
    """

    def test_the_shipped_acceptance_is_single_valued_across_adjacent_doubles(
            self):
        system = _system()
        seen = {round(_moment(system, lam).fos, 9)
                for lam in _adjacent(LAMBDA_SALTO)}
        assert len(seen) == 1, (
            "F_m takes %d values over thirteen ADJACENT doubles of λ: %s. "
            "The engine as shipped returns one." % (len(seen), sorted(seen)))

    def test_the_old_acceptance_is_two_valued_and_the_extra_one_is_early(self):
        system = _system()
        with _pair_off():
            pairs = {(round(st.fos, 9), st.passes)
                     for st in (_moment(system, lam)
                                for lam in _adjacent(LAMBDA_SALTO))}
        assert len(pairs) == 2, (
            "with the D145 acceptance off, F_m takes %d values over thirteen "
            "adjacent doubles: %s. The measurement that opened this was two."
            % (len(pairs), sorted(pairs)))
        by_value = dict(pairs)
        early = min(by_value.items(), key=lambda kv: kv[1])
        late = max(by_value.items(), key=lambda kv: kv[1])
        assert early[1] < late[1], "both values were admitted on the same pass"
        assert abs(early[0] - F_M_PREMATURO) < 1e-6, (
            "the value admitted first is %.9f and not the %.9f the ficha "
            "calls a second fixed point" % (early[0], F_M_PREMATURO))
        assert abs(late[0] - F_M_ATRACTOR) < 1e-6, (
            "the value admitted last is %.9f and not the attractor %.9f"
            % (late[0], F_M_ATRACTOR))

    def test_tightening_the_tolerance_undoes_it(self):
        """The tie-breaker, and the reason the word "bistable" does not fit.

        Asking for MORE precision cannot repair a genuine discontinuity of g:
        the jump would still be there, and a tighter tolerance would only make
        the secant refuse it sooner. It repairs a premature acceptance,
        because the step that sneaked under the loose tolerance does not
        sneak under the tight one.
        """
        with _pair_off():
            loose = _evaluate(TOL_FICHA)
            tight = _evaluate(1e-5)
        assert not loose.converged, (
            "with the D145 acceptance off, the λ search now closes at %g. "
            "The fixture has stopped reproducing the ficha." % TOL_FICHA)
        assert tight.converged, (
            "tightening the tolerance from %g to 1e-5 did not undo the "
            "failure, which is what a premature acceptance does and a "
            "discontinuity does not" % TOL_FICHA)
        # Against the tolerance as a literal and NOT against
        # ``details["lambda_tolerance"]``, which this version adds: a case
        # about whose defect this was has to mean the same on both trees.
        assert abs(tight.fos - loose.fos) > 1e-5


# ======================================================================
class TestTheExitSaysWhatDidNotClose:
    """DISCRIMINATES against the tree of 0.1.179. This is the change.

    The witness is built with ``_pair_off()``, and that is stated rather than
    disguised: on the engine as shipped no surface of the verification bank
    reaches this exit — 344 rows, and zero, at the bank's tolerance and at a
    forced 1e-8 alike. What the switch buys is a reachable instance of an exit
    the engine still has, not a defect that is still live.
    """

    def _failing(self):
        with _pair_off():
            return _evaluate(TOL_FICHA)

    def test_the_reason_is_not_the_one_bishop_and_janbu_give(self):
        from ogr_slip2d.methods.base import REASON_NOT_CONVERGED

        r = self._failing()
        assert not r.converged, "the fixture stopped producing the failure"
        assert r.reason != REASON_NOT_CONVERGED, (
            "the λ search still answers with %r, which is what Bishop's and "
            "Janbu's factor-of-safety iteration answers with. A caller "
            "grouping by reason cannot tell the two loops apart."
            % REASON_NOT_CONVERGED)
        assert r.reason == _reason_constant(), (
            "expected the λ-closure reason, got %r" % (r.reason,))

    def test_the_reason_is_declared(self):
        from ogr_slip2d.methods.base import ALL_REASONS

        reason = _reason_constant()
        assert reason is not None, (
            "there is no REASON_LAMBDA_NOT_CLOSED: a reason born as a loose "
            "string cannot be grouped, and grouping is the point (D56)")
        assert reason in ALL_REASONS, (
            "%r is not in ALL_REASONS, so test_no_number_v1152 will reject "
            "it the first time a run emits it" % reason)

    def test_the_message_names_the_residual_the_width_and_the_iterations(self):
        r = self._failing()
        det = r.details or {}
        msg = r.error_message
        assert "λ" in msg, (
            "the message does not mention λ at all, which is the whole "
            "complaint of D146: %r" % msg)
        for numero, nombre in (
                ("%.3g" % det["lambda_residual"], "the residual"),
                ("%.3g" % det["lambda_bracket_width"], "the bracket width"),
                ("%d" % r.iterations, "the iteration count")):
            assert numero in msg, (
                "%s (%s) is not in the message, so a reader cannot tell a "
                "collapsed bracket from a slow one: %r"
                % (nombre, numero, msg))

    def test_the_note_reaches_the_user(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        r = self._failing()
        notes = lambda_fallback_notes(r)
        assert notes, (
            "this exit still narrates nothing. It is gated behind "
            "``lambda_search_fell_back``, which is False here because a "
            "bracket WAS found — and that was the second half of D146.")
        assert any("%.3g" % (r.details or {})["lambda_residual"] in n
                   for n in notes), (
            "the note does not carry the residual: %r" % (notes,))

    def test_it_avoids_the_three_substrings_the_bank_reserves(self):
        """The verification bank reads warning text to decide whether D40 is
        still closed, and three substrings are spoken for. The ban is wider
        than it looks: "unstable" contains "stable" and "ahead" contains
        "head", so the test is on the raw text and on its lowercase form.
        """
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        r = self._failing()
        texto = " ".join(lambda_fallback_notes(r)) + " " + r.error_message
        for crudo in (texto, texto.lower()):
            assert "edge of the search grid" not in crudo
            assert "path_optimize" not in crudo
            assert not ("stable" in crudo and "head" in crudo), (
                "the text contains both reserved substrings: %r" % crudo)


# ======================================================================
class TestTheKeysTheBankWouldCount:
    """DISCRIMINATES. The contract ``_tools/cierre_lambda_d146.py`` reads.

    Same shape as ``test_fallback_origin_v1175.TestTheKeysTheBankCounts``:
    the keys are asserted BY NAME, because a census that looks for a key the
    engine renamed counts zero and reports a clean bill of health.
    """

    def test_the_three_keys_are_there_when_it_does_not_close(self):
        with _pair_off():
            r = _evaluate(TOL_FICHA)
        det = r.details or {}
        for clave in ("lambda_residual", "lambda_tolerance",
                      "lambda_bracket_width"):
            assert clave in det, "missing details key %r" % clave
        assert det["lambda_residual"] > det["lambda_tolerance"], (
            "the residual (%r) is not above the tolerance (%r), so this exit "
            "is not the one being measured"
            % (det["lambda_residual"], det["lambda_tolerance"]))
        assert det["lambda_bracket_width"] < 1e-12, (
            "the bracket is %r wide, so it did not collapse and this witness "
            "is measuring the budget exit instead"
            % det["lambda_bracket_width"])
        assert det["lambda_search_fell_back"] is False, (
            "this is the bracketed exit, not the fallback: confusing them is "
            "what made the census of D120 count the wrong rows")

    def test_the_residual_is_none_when_a_root_was_closed(self):
        """Deliberate, and the reason is a number.

        Below the tolerance the residual says nothing ``lambda_tolerance``
        does not already say, and writing one there would turn 229 archived
        nulls in the verification bank into values for no defect. So the key
        means the same thing on both exits of this method: present means the
        λ search did not close a root by refinement.
        """
        r = _evaluate(TOL_FICHA)
        assert r.converged, "the fixture stopped closing on the shipped tree"
        assert (r.details or {})["lambda_residual"] is None


# ======================================================================
class TestItVetoesExactlyAsBefore:
    """CONTROL. The change is what the result SAYS, never what it is worth."""

    def test_the_factor_does_not_move(self):
        with _pair_off():
            r = _evaluate(TOL_FICHA)
        assert r.fos == 0.5559372612135651, (
            "the factor this exit hands back moved to %r. This version was "
            "supposed to change the reason and nothing else." % (r.fos,))

    def test_it_is_still_invalid(self):
        with _pair_off():
            r = _evaluate(TOL_FICHA)
        assert r.error_message, (
            "the message went empty, which would make this surface VALID and "
            "let it compete for the search minimum — see the note on "
            "``error_message`` being a veto in ``Spencer.compute_fos``")
        assert not r.is_valid


# ======================================================================
class TestASolvedRootStillSaysNothing:
    """CONTROL. A surface whose λ closes must be untouched by all of this."""

    def test_no_reason_no_message_no_note(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        r = _evaluate(TOL_FICHA)
        assert r.converged
        assert r.reason == "", "a solved root grew a reason: %r" % (r.reason,)
        assert r.error_message == ""
        assert lambda_fallback_notes(r) == [], (
            "a solved root now warns about something: %r"
            % (lambda_fallback_notes(r),))

    def test_the_factor_of_the_solved_root_does_not_move_either(self):
        r = _evaluate(TOL_FICHA)
        assert r.fos == 0.5592600533686025, (
            "the factor on the closing path moved to %r" % (r.fos,))


# ======================================================================
class TestWhatThisDoesNotFix:
    """The half that was reported and NOT corrected (rule 6)."""

    def test_the_loop_keeps_solving_after_the_bracket_stops_moving(self):
        """No early cut, on purpose, and pinned so the next version sees it.

        When the bracket reaches the floor of the double there is no λ left
        between its two ends, so every remaining turn re-solves two branches
        — up to ``MAX_PASSES`` passes each — for an answer that is settled in
        advance. Counted on the calls the engine actually made, and NOT on
        ``iterations``: that field is the grid samples plus the secant turns
        here and the samples alone on the fallback exit, so a claim about the
        budget built on it would be comparing two different quantities. This
        is D153; cutting there needs its own A/B and its own version.
        """
        with _pair_off():
            r, traza = _trace(TOL_FICHA)
        assert not r.converged, "the fixture stopped producing the failure"
        last = traza[-1]
        stuck = next(i for i in range(len(traza))
                     if all(abs(l - last) <= 1e-12 * max(1.0, abs(last))
                            for l in traza[i:]))
        wasted = len(traza) - stuck - 1
        assert wasted > 10, (
            "only %d of the %d inner solves happen after λ stops moving. If "
            "that is the early cut of D153, this case is the one that should "
            "have been rewritten with it." % (wasted, len(traza)))

    def test_the_exit_is_dormant_on_the_engine_as_shipped(self):
        """The ficha's own witness closes now, and the census found no other.

        344 rows of the verification bank, 236 archived criticals and 108
        published surfaces over 79 problems, and none reaches this exit — at
        the tolerance each problem declares or at a forced 1e-8. This case
        pins the one number of that census that lives inside the repository.
        """
        r = _evaluate(TOL_FICHA)
        assert r.converged and r.reason == "", (
            "the ficha's own configuration fails again on the shipped "
            "engine (reason %r). Either D145 regressed or something new "
            "reopened the jump." % (r.reason,))
