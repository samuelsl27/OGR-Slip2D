# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""``GLESystem.states`` remembers the pair it already solved (D159).

WHAT INVARIANT THIS FILE PROTECTS. That the per-λ cache added in v0.1.186 is an
IDENTITY and not an approximation: the same factor to the last bit, the same
nineteen keys of ``details``, the same seven counters, and the same trace of λ
through ``_inner_solve`` — with fewer branch solves underneath. If a future
change lets the cache hand back a pair that a fresh solve would not produce,
``TestTheCacheIsAnIdentity`` goes red.

WHY THE COUNTERS CANNOT MOVE, which is the whole reason the repair is this one
and not the one the ficha spelled out. Every counter increments inside
``GLESystem.branches`` and from the states ``states`` hands it — which
``test_every_counter_moves_inside_branches`` asserts by AST rather than by
reading. The cache sits UNDERNEATH ``branches``: not one call to it disappears.
The ``solve(lam_lo)`` of ``spencer.py`` is a cache HIT and not a deletion, so
``branches`` is entered the same number of times with the same objects. The
other repair D159 offered — dropping that call and using ``ff_lo, fm_lo`` —
WOULD move them, and that is the distinction the ficha did not draw when it
concluded that "esto sí pide un A/B del banco de verdad y su propia corrida".

WHAT IT SAVES, MEASURED, AND THE NUMBER IS NOT THE ONE A FIRST MEASUREMENT GAVE.
A whole grid search of the 059 model with Spencer in one process: 17872 calls to
``states`` for 1795 surfaces, of which 3578 — 20.0 % — ask for a λ this system
has already solved, and those cost 144114 of 757378 branch passes, 19.0 %. The
first version of that measurement said 80 %, and it was wrong for a reason worth
writing down: it keyed the repeats on ``id(system)``, and CPython reuses an id
as soon as the object is freed, so 1795 different surfaces were being read as
one. Keying on a generation counter bumped by ``compute_fos`` gives 20.0 %.

AND THE FICHA'S CAUTION ABOUT THAT NUMBER IS FALSE. D159 warned that counting
calls "puede sobreestimar el tiempo por un factor grande", because the closing
pair "arranca de un ``initial_fos`` pegado al punto fijo". There is no warm
start: ``states`` passes ``self.initial_fos``, written once in ``__init__`` and
never again, so every branch of every λ starts from the same F and a repeat
costs exactly what the first one cost, to the pass. 20.0 % of the calls are
19.0 % of the passes.

THE A/B OF TIME, published whatever it says, because the ficha asked for
seconds. Same process, back to back, ON → OFF → ON on the whole 059 search:
38.0 s, 49.5 s, 41.3 s, with the branch pairs going 28588 → 35744 → 28588. The
two controls differ from each other by 8.7 %, so the clock resolves an effect of
this size and not a smaller one — and the number that carries no noise at all is
the pair count, which drops by exactly 7156 of 35744, 20.02 %, run after run.
Per AGENTS.md, where the controls and the effect are that close it is the
reasoning about the work removed that governs, and here the reasoning is exact:
two pairs per surface that brackets, on 1783 surfaces of 1795.

NO CLOCK IS ASSERTED IN THIS FILE. AGENTS.md is explicit that the stopwatch does
not resolve anything under 10 % and that hot loops drift between sessions. Every
numeric claim below is a count of calls the engine actually made, an identity, an
adjacency of doubles or an AST fact. The seconds live in
``docs/audits/lambda_state_cache_v1186.md``.

THE GUARD IS PART OF THE DESIGN, and it is not the switch. A ``GLESystem`` that
is captured and then asked again across a change of switch would get the stale
pair. That is not hypothetical:
``test_branch_rescue_v1176.py::TestWhatIsCountedAndSaid::test_a_stall_is_counted``
captures the system from an evaluation run with ``BRANCH_RESCUE`` on, and
``CYCLE_LAMBDA`` is 0.40, a node of ``_LAMBDA_SHAPE``, hence already in the
cache. Measured on that cell the force branch is (converged, rescued, 45 passes)
with the rescue on and (not converged, 81 passes) with it off. What keeps that
case honest is that any change in ``_BRANCH_SWITCH_NAMES`` empties the cache,
and ``test_the_guard_is_load_bearing`` shows the failure by neutering the
signature rather than by arguing for it.

WHAT THIS FILE DOES NOT CLAIM:

* nothing here fixes a factor of safety against a reference value. The absolute
  anchors already exist and are better than a fresh snapshot: the nine cases of
  ``test_lambda_closure_v1180`` and the four of
  ``test_lambda_floor_v1184.TestTheCutChangesNoDigit``, all written before this
  cache existed, go red if it moves a digit;
* nothing here says the cache is worth having on a surface that does not
  bracket. It is worth two pairs on a surface that brackets and one on a surface
  that falls back, and ``test_the_saving_is_two_pairs_on_a_bracketed_surface``
  says exactly that;
* it does not claim the cache changes what ``_inner_solve`` sees.
  ``test_the_trace_of_inner_solve_is_unchanged`` asserts the opposite, and that
  is what keeps ``test_lambda_closure_v1180.py`` and ``test_lambda_floor_v1184``
  measuring what they measured before.

WHICH CASES MEASURE THE CHANGE AND WHICH ARE CONTROL, run and not remembered.
Measured against the tree of 0.1.185 with the three engine files put back from
HEAD and this file in place: of the 19 cases here, 9 FAIL and 10 PASS.

FIVE fail on a measured difference, which is the strong half of the coverage:

* ``test_the_final_lambda_is_solved_once`` — there the returned λ is solved 3
  times, not 1;
* ``test_the_saving_is_two_pairs_on_a_bracketed_surface`` — 0 branch solves
  saved, not 4; ON 20 and OFF 20, because there is nothing to switch;
* ``test_gle_saves_the_same_two_pairs`` — the GLE half of the same, 22 and 22;
* ``test_the_saving_is_exactly_the_repeats`` — the cache never hits, so the
  identity has nothing to be an identity about;
* ``test_the_guard_is_load_bearing`` — with no cache there is nothing for the
  neutered signature to make stale, so the two sides agree where this version
  needs them to differ.

A NUMBER ON ONE CIRCLE IS ONLY TRUE OF THAT CIRCLE, and the two "two pairs"
cases are exactly that, which is why the identity case exists beside them. On
the archived critical of bank problem 059 the saving is SIX calls and not four,
because one ``evaluate_surface`` builds TWO ``GLESystem`` objects for one
surface — measured: three hits, λ 0.273195 asked three times on the first
system and λ 0.05625 twice on the second. The per-surface saving is therefore
not a constant; what is constant is that one hit is worth exactly one pair.

FOUR fail on the ABSENCE of a symbol rather than on a number. That is
WEAK discrimination, labelled here rather than counted as strength:
``test_the_switch_is_on_by_default``,
``test_the_signature_names_every_switch_solve_branch_reads``,
``test_every_cached_state_still_equals_a_fresh_solve`` and
``test_the_cache_holds_one_entry_per_distinct_lambda``.

THE TEN THAT PASS ON BOTH TREES DO SO ON PURPOSE. They are the identity, and
they say what has NOT moved: with no cache to switch, the ON/OFF comparisons
compare a run with itself, and the AST and IEEE facts are true of both trees.
``test_flipping_a_switch_empties_the_cache`` is green on 0.1.185 for the reason
that makes it worth having on 0.1.186 — there every pair is fresh, so the two
sides of the switch cannot help but differ. The day the cache stops being an
identity, these go red on the tree that has it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_lambda_closure_v1180 import (  # noqa: E402
    CIRCULO, N_DOVELAS, TOL_FICHA, _slope,
)
from test_lambda_floor_v1184 import CIRCULO_GLE  # noqa: E402

REPO = Path(__file__).parent.parent

#: The two methods that go through ``GLESystem``. Spencer and GLE differ in one
#: line — ``shape`` — so a saving that appeared on only one of them would be a
#: saving in the outer loop and not in this cache.
METODOS = (("spencer", CIRCULO), ("gle_morgenstern_price", CIRCULO_GLE))


# ----------------------------------------------------------------------
# Utilities. Every switch is put back by hand: the runner has no
# ``monkeypatch`` and does not call ``teardown_method`` (rule 5).
# ----------------------------------------------------------------------
@contextlib.contextmanager
def _cache(on):
    """The cache on or off in this process, restored whatever happens.

    ``getattr(..., None)`` so that this file still runs against a tree with no
    such constant instead of turning every case into a collection error — there
    the manager is a no-op, and every case that asserts a DIFFERENCE fails on a
    number, which is the strong half of the breakdown in the header.
    """
    import ogr_slip2d.interslice as interslice

    keep = getattr(interslice, "LAMBDA_STATE_CACHE", None)
    if keep is None:
        yield
        return
    interslice.LAMBDA_STATE_CACHE = on
    try:
        yield
    finally:
        interslice.LAMBDA_STATE_CACHE = keep


@contextlib.contextmanager
def _signature_neutered():
    """``_branch_switches`` made constant, i.e. the guard taken away.

    Only used by ``test_the_guard_is_load_bearing``, which has to show that the
    signature is what stops a stale pair rather than assert that it is.
    """
    import ogr_slip2d.interslice as interslice

    keep = getattr(interslice, "_branch_switches", None)
    if keep is None:
        yield
        return
    interslice._branch_switches = lambda: ()
    try:
        yield
    finally:
        interslice._branch_switches = keep


def _rescue_module():
    """``test_branch_rescue_v1176`` as a module, for its 091 witness."""
    spec = importlib.util.spec_from_file_location(
        "_rescue_for_cache", Path(__file__).parent / "test_branch_rescue_v1176.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _method(method_id):
    from ogr_slip2d.methods.gle import GLEMorgensternPrice
    from ogr_slip2d.methods.spencer import Spencer

    return Spencer if method_id == "spencer" else GLEMorgensternPrice


def _solve(method_id, circle, cache_on):
    """``(result, per-λ record, total branch solves)`` on one surface.

    The record is ``[(λ, branch solves that call cost), ...]`` in order, taken
    by wrapping ``GLESystem.states`` — which exists on BOTH trees, so the counts
    below discriminate on a number and not on a missing attribute. A cost of 0
    is a cache hit and a cost of 2 is a pair actually solved.
    """
    import ogr_slip2d.interslice as interslice
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.surface import SlipCircle

    registro: list = []
    total = [0]
    orig_states = interslice.GLESystem.states
    orig_solve = interslice.solve_branch

    def sb(*a, _o=orig_solve, **k):
        total[0] += 1
        return _o(*a, **k)

    def spy(self, lam, _o=orig_states):
        antes = total[0]
        out = _o(self, lam)
        registro.append((float(lam), total[0] - antes))
        return out

    interslice.solve_branch = sb
    interslice.GLESystem.states = spy
    try:
        with _cache(cache_on):
            p = _slope(TOL_FICHA, N_DOVELAS)
            r = build_search(p, method_id).evaluate_surface(p, SlipCircle(*circle))
    finally:
        interslice.GLESystem.states = orig_states
        interslice.solve_branch = orig_solve
    return r, registro, total[0]


def _solved_at(registro, lam):
    """How many branch PAIRS were actually solved at exactly this λ."""
    return sum(c for x, c in registro if x == lam) // 2


def _fields(state):
    """Every field of a ``BranchState``, lists included, for a bit comparison."""
    if state is None:
        return None
    return (state.fos, state.converged, state.passes, state.abandoned,
            state.rescued, tuple(state.normals), tuple(state.resisting),
            tuple(state.boundary_e), tuple(state.boundary_x))


def _source(rel):
    return io.open(REPO / rel, encoding="utf-8").read()


# ======================================================================
class TestTheCacheIsAnIdentity:
    """The half that says what has NOT moved. Green on both trees on purpose:
    with no cache to switch, these compare a run with itself — and the day the
    cache stops being an identity they go red on the tree that has it."""

    def test_two_calls_from_scratch_agree_bit_for_bit(self):
        """``states`` is deterministic — asserted, at last, instead of claimed.

        ``interslice.py`` has been claiming this in the docstring of
        ``thrust_rejected_pairs`` since v0.1.182, and ``recover_thrust_edge``
        leans on it to trust a pair recorded on an earlier pass. It was never
        tested. With the cache OFF, so that the repeat is a real second solve.
        """
        import ogr_slip2d.interslice as interslice
        from ogr_slip2d.analysis_runner import build_method

        sistema = _capture_system("spencer", CIRCULO)
        metodo = build_method(_slope(TOL_FICHA, N_DOVELAS), "spencer")
        comparados = 0
        with _cache(False):
            for lam in metodo.lambda_grid():
                uno = tuple(_fields(s) for s in sistema.states(lam))
                otro = tuple(_fields(s) for s in sistema.states(lam))
                assert uno == otro, (
                    "states(%r) gave two different answers on the same system. "
                    "The cache of v0.1.186 rests on this, and so did "
                    "``recover_thrust_edge`` before it." % lam)
                comparados += 1
        assert comparados > 5, comparados
        assert interslice is not None

    def test_nothing_the_result_publishes_moves(self):
        """The attribution table: ON and OFF publish the same result.

        Every key of ``details`` and every field of ``LEMResult`` that a caller
        can read, not just ``fos`` — because what D159 risked was the counters,
        and those travel in ``details``.
        """
        for method_id, circle in METODOS:
            con, _r1, _n1 = _solve(method_id, circle, True)
            sin, _r2, _n2 = _solve(method_id, circle, False)
            assert con.fos == sin.fos, (method_id, con.fos, sin.fos)
            assert con.converged == sin.converged, method_id
            assert con.iterations == sin.iterations, method_id
            assert con.reason == sin.reason, method_id
            assert con.error_message == sin.error_message, method_id
            assert con.admissible == sin.admissible, method_id
            assert con.admissibility_note == sin.admissibility_note, method_id
            a, b = con.details or {}, sin.details or {}
            assert set(a) == set(b), (method_id, set(a) ^ set(b))
            movidas = [k for k in a if a[k] != b[k]]
            assert not movidas, (method_id, movidas)

    def test_no_counter_moves(self):
        """The seven counters, read off the system itself.

        ``details`` already carries them, and the case above compares it. This
        one asks the object, so that a counter that stopped being published
        would still be watched.
        """
        nombres = ("n_thrust_rejected", "n_passes_exhausted",
                   "n_thrust_overflow", "n_stalled", "n_rescued",
                   "n_inadmissible")
        for method_id, circle in METODOS:
            con = _capture_system(method_id, circle, cache_on=True)
            sin = _capture_system(method_id, circle, cache_on=False)
            for nombre in nombres:
                assert getattr(con, nombre) == getattr(sin, nombre), (
                    method_id, nombre, getattr(con, nombre),
                    getattr(sin, nombre))
            assert (len(con.thrust_rejected_pairs)
                    == len(sin.thrust_rejected_pairs)), method_id

    def test_the_trace_of_inner_solve_is_unchanged(self):
        """The λ the engine ASKS for are the same; only the solves drop.

        This is what keeps
        ``test_lambda_closure_v1180.test_the_bracket_floor_no_longer_re_solves_the_same_lambda``
        and its twin in ``test_lambda_floor_v1184`` measuring what they
        measured: the repeat of the final λ is still a CALL, so their count of 1
        is untouched by this version.
        """
        for method_id, circle in METODOS:
            _r1, con, _n1 = _solve(method_id, circle, True)
            _r2, sin, _n2 = _solve(method_id, circle, False)
            assert [x for x, _c in con] == [x for x, _c in sin], method_id

    def test_minus_zero_and_zero_are_the_same_lambda(self):
        """``-0.0 == 0.0`` and they hash alike, so the dict fuses them.

        Harmless, and measured rather than asserted: with the cache OFF the two
        branches agree field by field, so fusing them cannot change an answer.
        If that ever stops being true this case says so before the cache can
        hide it.
        """
        sistema = _capture_system("spencer", CIRCULO)
        with _cache(False):
            mas = tuple(_fields(s) for s in sistema.states(0.0))
            menos = tuple(_fields(s) for s in sistema.states(-0.0))
        assert mas == menos, (
            "+0.0 and -0.0 no longer give the same branches, so the cache "
            "fusing them is no longer harmless.")

    def test_a_nan_lambda_never_returns_a_stale_pair(self):
        """NaN never matches itself, so it is re-solved — the safe direction.

        No NaN λ is reachable today, which is exactly why there is no branch
        guarding it: a guard that cannot fire is a claim nobody can check. What
        this asserts is that the failure mode, if one ever arrives, is a
        recompute and not a wrong answer.
        """
        sistema = _capture_system("spencer", CIRCULO)
        uno = sistema.states(float("nan"))
        otro = sistema.states(float("nan"))
        assert uno is not otro, (
            "a NaN λ came back from the cache, which means NaN started "
            "matching itself and the cache can now hand back another λ's pair.")
        for s in uno + otro:
            assert s is None or math.isnan(s.fos) or math.isfinite(s.fos)

    def test_every_counter_moves_inside_branches(self):
        """By AST: no counter is touched outside ``branches`` and ``__init__``.

        The load-bearing step of "the cache cannot move a counter". Written as a
        test and not as a sentence because the sentence is only true until
        somebody increments one somewhere else, and then the cache's guarantee
        quietly stops holding.
        """
        contadores = {"n_thrust_rejected", "n_passes_exhausted",
                      "n_thrust_overflow", "n_stalled", "n_rescued",
                      "n_inadmissible", "thrust_rejected_pairs"}
        arbol = ast.parse(_source("ogr_slip2d/interslice.py"))
        clase = next(n for n in ast.walk(arbol)
                     if isinstance(n, ast.ClassDef) and n.name == "GLESystem")
        fuera = []
        for metodo in clase.body:
            if not isinstance(metodo, ast.FunctionDef):
                continue
            for nodo in ast.walk(metodo):
                objetivos = []
                if isinstance(nodo, ast.AugAssign):
                    objetivos = [nodo.target]
                elif isinstance(nodo, ast.Assign):
                    objetivos = list(nodo.targets)
                for t in objetivos:
                    base = t.value if isinstance(t, ast.Subscript) else t
                    if (isinstance(base, ast.Attribute)
                            and base.attr in contadores
                            and metodo.name not in ("__init__", "branches")):
                        fuera.append((metodo.name, base.attr))
        assert not fuera, (
            "a counter is written outside ``branches``: %r. The cache of "
            "v0.1.186 guarantees the counters only because every increment "
            "happens above it." % (fuera,))

    def test_the_system_never_rewrites_what_the_cache_depends_on(self):
        """By AST: the six inputs of ``states`` are written only in ``__init__``.

        ``rows``, ``shape``, ``tolerance``, ``initial_fos``, ``max_passes`` and
        ``_moment_fos``. If any of them became mutable during the life of a
        system, a cached pair could stop being what a fresh solve would give,
        and nothing else in this file would notice.
        """
        entradas = {"rows", "shape", "tolerance", "initial_fos", "max_passes",
                    "_moment_fos"}
        arbol = ast.parse(_source("ogr_slip2d/interslice.py"))
        clase = next(n for n in ast.walk(arbol)
                     if isinstance(n, ast.ClassDef) and n.name == "GLESystem")
        fuera = []
        for metodo in clase.body:
            if not isinstance(metodo, ast.FunctionDef):
                continue
            for nodo in ast.walk(metodo):
                objetivos = (list(nodo.targets) if isinstance(nodo, ast.Assign)
                             else [nodo.target] if isinstance(nodo, ast.AugAssign)
                             else [])
                for t in objetivos:
                    for sub in ast.walk(t):
                        if (isinstance(sub, ast.Attribute)
                                and sub.attr in entradas
                                and isinstance(sub.ctx, ast.Store)
                                and metodo.name != "__init__"):
                            fuera.append((metodo.name, sub.attr))
        assert not fuera, (
            "an input of ``states`` is rewritten after construction: %r"
            % (fuera,))


# ======================================================================
class TestTheSavingIsReal:
    """Rule 7 from the other side: a switch that changes no number is worse
    than no switch. These measure the number it changes — branch solves — and
    they fail on 0.1.185 on that number and not on a missing symbol."""

    def test_the_final_lambda_is_solved_once(self):
        """The λ the method returns is SOLVED once and ASKED for three times.

        Before this version it was solved three times: the sample or secant turn
        that produced it, the ``solve(lam_lo)`` of the closing lines and the
        ``system.states(lam_lo)`` two lines below. That is D159 in one number.
        """
        for method_id, circle in METODOS:
            r, registro, _n = _solve(method_id, circle, True)
            lam = (r.details or {}).get("lambda")
            assert lam is not None, method_id
            pedido = sum(1 for x, _c in registro if x == lam)
            resuelto = _solved_at(registro, lam)
            assert pedido >= 3, (method_id, pedido)
            assert resuelto == 1, (
                "%s: the returned λ was solved %d times, not 1. More than 1 "
                "means the cache stopped catching the closing pair; 0 would "
                "mean the CALL went too, which moves the counters."
                % (method_id, resuelto))

    def test_the_saving_is_two_pairs_on_a_bracketed_surface(self):
        """Spencer: exactly two branch pairs fewer, and the same factor.

        Two and not "fewer": the closing lines ask for the same λ twice, and a
        surface that brackets pays both. A different number would mean the cache
        is catching something else as well, and that is worth knowing.
        """
        con, _r1, pares_con = _solve("spencer", CIRCULO, True)
        sin, _r2, pares_sin = _solve("spencer", CIRCULO, False)
        assert con.fos == sin.fos, (con.fos, sin.fos)
        assert pares_sin - pares_con == 4, (
            "%d branch solves saved, not 4 (two pairs). ON %d, OFF %d."
            % (pares_sin - pares_con, pares_con, pares_sin))

    def test_gle_saves_the_same_two_pairs(self):
        """The GLE half. The two methods share every line of this loop."""
        con, _r1, pares_con = _solve("gle_morgenstern_price", CIRCULO_GLE, True)
        sin, _r2, pares_sin = _solve("gle_morgenstern_price", CIRCULO_GLE, False)
        assert con.fos == sin.fos, (con.fos, sin.fos)
        assert pares_sin - pares_con == 4, (
            "%d branch solves saved, not 4. ON %d, OFF %d."
            % (pares_sin - pares_con, pares_con, pares_sin))

    def test_the_saving_is_exactly_the_repeats(self):
        """One cache hit is worth exactly one branch PAIR, and no witness.

        The two cases above pin a number on one circle each, and a number on
        one circle is only ever true of that circle: measured on the archived
        critical of bank problem 059 the saving is SIX calls and not four,
        because ``evaluate_surface`` builds TWO ``GLESystem`` objects for one
        surface and the repeats fall where they fall. This case asserts the
        identity instead -- every call to ``states`` that solves nothing saved
        exactly two calls to ``solve_branch`` -- which is what is actually
        true, and it cannot rot when the outer search changes shape.
        """
        import ogr_slip2d.interslice as interslice
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.surface import SlipCircle

        for method_id, circle in METODOS:
            total, aciertos = [0], [0]
            orig_solve = interslice.solve_branch
            orig_states = interslice.GLESystem.states

            def sb(*a, _o=orig_solve, **k):
                total[0] += 1
                return _o(*a, **k)

            def st(self, lam, _o=orig_states):
                antes = total[0]
                out = _o(self, lam)
                if total[0] == antes:
                    aciertos[0] += 1
                return out

            interslice.solve_branch = sb
            interslice.GLESystem.states = st
            try:
                with _cache(True):
                    p = _slope(TOL_FICHA, N_DOVELAS)
                    build_search(p, method_id).evaluate_surface(
                        p, SlipCircle(*circle))
            finally:
                interslice.GLESystem.states = orig_states
                interslice.solve_branch = orig_solve
            con, hits = total[0], aciertos[0]
            _r, _reg, sin = _solve(method_id, circle, False)
            assert hits > 0, (method_id, "the cache never hits")
            assert sin - con == 2 * hits, (
                "%s: %d calls saved with %d hits, and a hit is one pair"
                % (method_id, sin - con, hits))

    def test_the_cache_holds_one_entry_per_distinct_lambda(self):
        """The memory bound of the header, as a number and not a paragraph.

        WEAK discrimination: on a tree without the attribute this fails on its
        absence.
        """
        sistema = _capture_system("spencer", CIRCULO)
        registro = getattr(sistema, "_state_cache", None)
        assert registro is not None, "no cache on this system"
        assert len(registro) > 5, len(registro)
        assert len(registro) < 600, (
            "%d entries: more than the grid, its extension, the gap probes and "
            "``max_iterations`` together can produce." % len(registro))

    def test_the_switch_is_on_by_default(self):
        """Rule 7 the other way round: the shipped default does the caching.

        WEAK discrimination — on 0.1.185 this fails on a missing symbol and not
        on a number.
        """
        import ogr_slip2d.interslice as interslice

        assert getattr(interslice, "LAMBDA_STATE_CACHE", None) is True


# ======================================================================
class TestTheGuardAgainstAStalePair:
    """A ``GLESystem`` outlives the call that built it — every measuring tool in
    this repository captures one — and the switches it was solved under can
    change underneath it. The signature is what stops that being silent."""

    def test_flipping_a_switch_empties_the_cache(self):
        """The 091 witness: λ = 0.40 is a grid node and is already cached.

        With ``BRANCH_RESCUE`` off, the force branch there does NOT converge and
        spends 81 passes. With it on, it converges through the rescue in 45. The
        evaluation that builds the system runs with the rescue on, so without
        the signature the second question would be answered by the first.
        """
        w = _rescue_module()
        sistema = w._system_091()
        con, _m = sistema.states(w.CYCLE_LAMBDA)
        assert con is not None and con.converged and con.rescued, (
            "the fixture stopped producing a rescued branch at λ = %r"
            % (w.CYCLE_LAMBDA,))
        with w._unrescued():
            sin, _m2 = sistema.states(w.CYCLE_LAMBDA)
        assert sin is not None, sin
        assert not sin.converged, (
            "with the rescue off the branch converged anyway, so this cell no "
            "longer separates the two sides")
        assert not sin.rescued
        assert sin.passes != con.passes, (sin.passes, con.passes)

    def test_the_guard_is_load_bearing(self):
        """Take the signature away and the stale pair comes back.

        Shown rather than argued. With ``_branch_switches`` made constant the
        cache cannot tell the two configurations apart, so asking inside
        ``_unrescued()`` returns the RESCUED branch — the opposite of the truth,
        and exactly what ``test_a_stall_is_counted`` would then be measuring.
        """
        w = _rescue_module()
        with _signature_neutered():
            # The signature has to be away while the cache is FILLED as well,
            # which is the shape of the real hazard: the evaluation runs under
            # one configuration and the question arrives under another. Filling
            # it first and neutering afterwards proves nothing -- the change of
            # signature would itself empty the cache, which is the guard doing
            # its job.
            sistema = w._system_091()
            with w._unrescued():
                viciado, _m = sistema.states(w.CYCLE_LAMBDA)
        otro = w._system_091()
        with w._unrescued():
            honesto, _m2 = otro.states(w.CYCLE_LAMBDA)
        assert viciado.converged and not honesto.converged, (
            "neutering the signature no longer produces a stale pair, so the "
            "guard has stopped being what keeps the cache honest: %r vs %r"
            % (viciado.converged, honesto.converged))
        assert viciado.passes != honesto.passes

    def test_every_cached_state_still_equals_a_fresh_solve(self):
        """Nobody mutates a shared ``BranchState``, and nothing drifts.

        The cache hands the SAME object to several readers, so a reader that
        wrote to one of its four lists would poison every later hit. Rather than
        inspect the readers, this re-solves every cached λ from scratch and
        compares field by field and element by element. It also closes the other
        half: if ``solve_branch`` ever stopped being deterministic, this is
        where it would show.

        WEAK discrimination: on a tree without the attribute it fails on its
        absence.
        """
        for method_id, circle in METODOS:
            sistema = _capture_system(method_id, circle)
            registro = getattr(sistema, "_state_cache", None)
            assert registro, (method_id, "no cache to check")
            comprobados = 0
            with _cache(False):
                for lam, guardado in list(registro.items()):
                    if lam != lam:                      # NaN, never stored
                        continue
                    fresco = sistema._solve_states(lam)
                    assert (tuple(_fields(s) for s in guardado)
                            == tuple(_fields(s) for s in fresco)), (
                        "%s: the cached pair at λ = %r is not what a fresh "
                        "solve gives" % (method_id, lam))
                    comprobados += 1
            assert comprobados > 5, (method_id, comprobados)


# ======================================================================
class TestTheSignatureCannotGoStale:
    """``_BRANCH_SWITCH_NAMES`` is a list kept by hand, and this project has
    written down what a hand-kept list costs: three of the seven version sites
    stayed frozen for seventeen versions behind a document that said four."""

    def test_the_signature_names_every_switch_solve_branch_reads(self):
        """By AST, over the BODY of ``solve_branch`` and not its signature.

        The distinction is load-bearing: ``MAX_PASSES``, ``F_MIN``, ``F_MAX``
        and ``STALL_PATIENCE`` appear only as default expressions, which Python
        evaluates at ``def`` time, so patching the module attribute afterwards
        changes nothing and they are NOT inputs of a cached pair.

        WEAK discrimination: on 0.1.185 this fails on a missing symbol.
        """
        import ogr_slip2d.interslice as interslice

        nombres = getattr(interslice, "_BRANCH_SWITCH_NAMES", None)
        assert nombres is not None, "no signature on this tree"
        arbol = ast.parse(_source("ogr_slip2d/interslice.py"))
        datos = set()
        for n in arbol.body:
            if isinstance(n, ast.Assign):
                datos.update(t.id for t in n.targets if isinstance(t, ast.Name))
        fn = next(n for n in arbol.body
                  if isinstance(n, ast.FunctionDef) and n.name == "solve_branch")
        locales = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
        for st in fn.body:
            for sub in ast.walk(st):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    locales.add(sub.id)
        leidos = {s.id for st in fn.body for s in ast.walk(st)
                  if isinstance(s, ast.Name) and isinstance(s.ctx, ast.Load)
                  and s.id in datos and s.id not in locales}
        # ``_BRANCH_SWITCH_NAMES`` itself is not read by ``solve_branch``.
        assert leidos == set(nombres), (
            "the signature and what ``solve_branch`` reads have drifted apart. "
            "Missing from the signature: %r. Listed but not read: %r."
            % (sorted(leidos - set(nombres)), sorted(set(nombres) - leidos)))

    def test_the_four_that_live_only_in_the_defaults_are_still_four(self):
        """And they stay OUT of the signature, with their names written down.

        If one of them ever moves into the body it becomes a real input of a
        cached pair, and the case above would then demand it. This one says
        which four are expected to stay outside, so that the move is visible
        from either side.
        """
        arbol = ast.parse(_source("ogr_slip2d/interslice.py"))
        fn = next(n for n in arbol.body
                  if isinstance(n, ast.FunctionDef) and n.name == "solve_branch")
        defaults = {d.id for d in (fn.args.defaults
                                   + [d for d in fn.args.kw_defaults if d])
                    if isinstance(d, ast.Name)}
        assert defaults == {"MAX_PASSES", "F_MIN", "F_MAX", "STALL_PATIENCE"}, (
            "the defaults of ``solve_branch`` changed: %r" % (sorted(defaults),))


# ----------------------------------------------------------------------
def _capture_system(method_id, circle, cache_on=True):
    """The ``GLESystem`` the method built, captured off the class.

    The idiom of ``test_branch_rescue_v1176._system_091`` and of the three
    census tools in the verification bank: the engine's own rows and support
    terms, not a copy that could drift.
    """
    import ogr_slip2d.interslice as interslice
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.surface import SlipCircle

    cls = _method(method_id)
    cap: list = []
    orig = cls._inner_solve

    def spy(self, slices, lam, system, _o=orig, _c=cap):
        if not _c:
            _c.append(system)
        return _o(self, slices, lam, system)

    cls._inner_solve = spy
    try:
        with _cache(cache_on):
            p = _slope(TOL_FICHA, N_DOVELAS)
            build_search(p, method_id).evaluate_surface(p, SlipCircle(*circle))
    finally:
        cls._inner_solve = orig
    assert cap, "the method never solved a branch"
    assert interslice is not None
    return cap[0]
