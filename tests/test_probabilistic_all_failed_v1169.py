# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.169 (D127) — a sampling that sampled nothing publishes no number, and
says which of the ways it failed.

WHAT INVARIANT THIS PROTECTS. When every sample of a method failed, the run
came back ``ok`` true with ``PF = nan`` and ``beta = -inf``, an empty
``notes``, and the status bar printed exactly that. Measured against 0.1.168
with the recipe of the ficha::

    ok=True n=0 pf=nan beta=-inf failed=20 notes={}
    m.notes={'warning': '20 of 20 samples could not be evaluated; ...'}

Three pieces made it. ``SampleStatistics`` answered ``nan`` for the mean and
the probability of failure, a plain ``0.0`` for the standard deviation and
``-inf`` for the reliability index — the last because ``nan >= 1.0`` is
False, so a sampling with no data was reported as "failure is certain".
``run_global_minimum`` inserted the method into ``by_method`` anyway. And
``ProbabilisticResult.ok`` was ``bool(self.by_method)``, so a key with
nothing behind it was a result. It is the policy of D56 (v0.1.152, ``fos:
Optional[float]``) applied to the sampler; D59 (v0.1.154) removed ONE cause
of this state and not the door.

WHAT THE MEASUREMENT REFUTES IN THE FICHA, written here because four of
these changed the work and a reader who trusts the ficha will look for code
that is not there:

* its step 2 is IMPOSSIBLE as written. ``test_overall_slope_v137``'s
  ``test_failed_searches_counted`` fails all five searches and then asserts
  ``res.by_method[mid].failed_samples == 5`` — this very state, green today,
  in a file the ficha itself declares untouchable. So in Overall Slope the
  entry STAYS and what turns the run off is ``ok``; only Global Minimum can
  drop it. Pinned below in ``TestOverallSlopeSaysItWithoutLosingTheCount``;
* "save the reason of the last failed sample, which the ``except`` has" asks
  for less than the house already offers, and in one case for something that
  does not exist: a sample whose result comes back with ``is_valid`` false
  never reaches the ``except``. Since D56 an invalid ``LEMResult`` carries
  ``reason``, one of ``ALL_REASONS``, put there so a caller can group by it —
  so the three outcomes are COUNTED, not kept one at a time;
* ``mres.notes[...]`` is read by NOBODY in the program: ``main_window``
  reads ``res.notes``. A reason written per method is the state
  ``test_statistical_rebuild_v1154`` calls a note that does not exist;
* its case (b), "3 of 20 failing gives today's warning", cannot happen: the
  warning is ``failed > 0.2 * num_samples``, and ``3 > 4`` is false. So is
  ``4 > 4``. It takes FIVE, and both sides of that edge are pinned below.

THIS IS NOT A SNAPSHOT TEST. Not one assertion fixes a factor of safety.
What is checked are identities, names and counts recomputed here — the
counted fraction, the conservation ``n + failed == num_samples``, the
wording of a sentence that must NOT change. The engine's arithmetic is
untouched by this version and a snapshot of it would protect nothing.

ONE HONEST LIMIT, and it is a fence rather than an oversight: the guard
covers ``n == 0`` and nothing else. With ONE surviving sample the standard
deviation is still ``0.0`` and the reliability index still ``+inf``, and
``summary()`` can therefore still fail ``allow_nan=False``. Those are
quantities that are defined and degenerate, not quantities that are
missing, and the ``beta inf`` of a scatterless sampling is the very signal
by which v0.1.164 (D91) catches a random variable that no longer writes.
Stating what a guard does NOT cover is what v0.1.82-84 cost this project.

Regla 5 — everything this file patches, it puts back, in a ``finally``.
The runner has no ``monkeypatch``, so the restoring is written out.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_MID = "bishop_simplified"
_OTHER = "spencer"

#: The 20 % sentence, character for character. It is the one thing this
#: version is forbidden to move, so it is quoted and not rebuilt.
_TWENTY_PERCENT = ("5 of 20 samples could not be evaluated; check the "
                   "variable ranges.")

#: Building a deterministic critical surface costs a real search, so the
#: few this file needs are built once. Same pattern as v1152/v1154.
_CACHE: dict = {}


# ======================================================================
@contextlib.contextmanager
def _instead_of(module, name, replacement):
    """Swap a module-level name and put it back.

    The NAME in the module, never an attribute of a shared class: the
    sample loop resolves ``_evaluate_on`` as a global on every call, so
    rebinding it is enough, and rebinding nothing else means an escape
    before the ``finally`` cannot leak into another file. That is regla 5
    in its most expensive form to diagnose.
    """
    old = getattr(module, name)
    setattr(module, name, replacement)
    try:
        yield
    finally:
        setattr(module, name, old)


def _project():
    from test_slide_validation_ej1 import _ej1_project
    return _ej1_project()


def _search(_mid=None):
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    # Deliberately coarse: nothing here depends on search resolution.
    return GridSearch(method=BishopSimplified(), grid_x=(75, 95),
                      grid_y=(62, 80), grid_nx=3, grid_ny=3,
                      radius_increment=10, min_radius=15, num_slices=14,
                      min_area=0.5)


def _det(project, methods=(_MID,)):
    """A deterministic critical surface per method, cached by method set."""
    key = tuple(methods)
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch
        out = {}
        for mid in methods:
            out[mid] = GridSearch(
                method=build_method(project, mid, 14), grid_x=(75, 95),
                grid_y=(62, 80), grid_nx=3, grid_ny=3, radius_increment=10,
                min_radius=15, num_slices=14, min_area=0.5).run(
                    project).critical
        _CACHE[key] = out
    return dict(_CACHE[key])


def _vars(project):
    from ogr_core.statistics import (
        Distribution, DistributionType as DT, available_variables,
    )
    mat = project.materials[0]
    c = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    c.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=4.0,
                                  rel_min=12.0, rel_max=12.0)
    return [c]


def _run_gm(project, replacement, num_samples=20, methods=(_MID,)):
    """A Global Minimum run with ``_evaluate_on`` replaced."""
    import ogr_core.statistics.probabilistic as P
    from ogr_core.statistics import SamplingMethod as SM, run_global_minimum

    det = _det(project, methods)
    with _instead_of(P, "_evaluate_on", replacement):
        return run_global_minimum(project, det, _vars(project),
                                  num_samples=num_samples,
                                  sampling=SM.LATIN_HYPERCUBE, seed=1,
                                  num_slices=14)


def _boom(*_a, **_k):
    raise RuntimeError("engineered")


def _invalid(*_a, **_k):
    """A result that DECLARES its failure, the D56 way, and never raises.

    Constructible by design: ``test_no_number_v1152`` pins that a declared
    failure can be built directly, which is what lets this file reach the
    branch the ``except`` never sees.
    """
    from ogr_slip2d.methods.base import LEMResult, REASON_ZERO_DRIVING
    from ogr_slip2d.surface import SlipCircle
    # ``surface`` and ``slices`` are POSITIONAL and required: leaving them
    # out raises TypeError, and the failure would then be counted as
    # "raised", which is exactly the outcome this helper exists to tell
    # apart from an exception.
    return LEMResult(fos=None, converged=False, iterations=1,
                     method_id=_MID,
                     surface=SlipCircle(centre_x=80.0, centre_y=70.0,
                                        radius=25.0),
                     slices=[], error_message="engineered",
                     reason=REASON_ZERO_DRIVING)


def _fails_first(k, replacement):
    """Lose the first ``k`` samples and let the rest through untouched."""
    import ogr_core.statistics.probabilistic as P
    real = P._evaluate_on
    state = {"n": 0}

    def _inner(*a, **kw):
        state["n"] += 1
        if state["n"] <= k:
            return replacement(*a, **kw)
        return real(*a, **kw)
    return _inner


# ======================================================================
class TestThePremiseTwoWaysToLoseEverySample:
    """The ficha says the ``except`` has the reason. Measured, there are
    two routes and only one of them goes through it."""

    def test_a_raised_evaluation_loses_the_sample(self):
        res = _run_gm(_project(), _boom, num_samples=4)
        assert not res.ok
        assert "raised RuntimeError" in res.notes["error"]

    def test_an_invalid_result_loses_it_without_ever_raising(self):
        """PREMISE. The replacement returns normally every time, and the
        method still ends with nothing — so the ``except`` the ficha points
        at was never entered."""
        returned = {"n": 0}

        def _counting(*a, **kw):
            returned["n"] += 1
            return _invalid()

        res = _run_gm(_project(), _counting, num_samples=4)
        assert returned["n"] == 4, "the replacement must have returned, " \
                                   "not raised"
        assert not res.ok

    def test_the_note_names_which_of_the_two_happened(self):
        """The whole point of counting by cause: the two runs differ in
        their reason and not only in their count."""
        raised = _run_gm(_project(), _boom, num_samples=4).notes["error"]
        declared = _run_gm(_project(), _invalid,
                           num_samples=4).notes["error"]
        assert "raised RuntimeError" in raised
        assert "raised" not in declared
        assert raised != declared

    def test_the_declared_reason_of_d56_is_the_one_repeated(self):
        from ogr_slip2d.methods.base import REASON_ZERO_DRIVING
        res = _run_gm(_project(), _invalid, num_samples=4)
        assert REASON_ZERO_DRIVING in res.notes["error"]

    def test_the_causes_are_counted_not_kept_one_at_a_time(self):
        """Two of one cause and two of another, both named with their
        count — which is the shape the reference reports and what D56 made
        ``reason`` a named constant for."""
        import ogr_core.statistics.probabilistic as P
        state = {"n": 0}

        def _mixed(*a, **kw):
            state["n"] += 1
            if state["n"] <= 2:
                raise ValueError("engineered")
            return _invalid()

        with _instead_of(P, "_evaluate_on", P._evaluate_on):
            res = _run_gm(_project(), _mixed, num_samples=4)
        said = res.notes["error"]
        assert "raised ValueError x 2" in said, said
        assert "x 2" in said.replace("raised ValueError x 2", ""), said


# ======================================================================
class TestGlobalMinimumWithNoSampleIsNotAResult:
    """The headline. Every one of these fails against 0.1.168."""

    def test_the_run_is_not_ok(self):
        assert not _run_gm(_project(), _boom).ok

    def test_the_method_is_not_offered_among_the_results(self):
        res = _run_gm(_project(), _boom)
        assert _MID not in res.by_method
        assert res.summary() == []

    def test_there_is_no_method_to_report(self):
        assert _run_gm(_project(), _boom).reported is None

    def test_the_reason_reaches_the_key_the_interface_prints(self):
        """``_compute_statistics`` looks at ``notes['error']`` and nowhere
        else, so anywhere else is nowhere."""
        res = _run_gm(_project(), _boom)
        said = res.notes.get("error", "")
        assert _MID in said and "all 20 samples" in said, said

    def test_the_reason_does_not_blame_the_variable_ranges(self):
        """CONSERVATION of the lesson of D59: the ranges are innocent when
        the fault is the surface or the strength."""
        said = _run_gm(_project(), _boom).notes.get("error", "")
        assert "variable ranges" not in said, said

    def test_no_sample_drawn_at_all_is_said_too(self):
        """``num_samples=0`` came back ``ok`` with ``pf`` nan as well, and
        it is a different sentence because nothing was even attempted."""
        res = _run_gm(_project(), _boom, num_samples=0)
        assert not res.ok
        assert "no sample was drawn" in res.notes.get("error", "")

    def test_the_summary_is_valid_json(self):
        """``allow_nan=False`` is the external check D56 chose, and the one
        that says whether this policy is applied or merely declared."""
        p = _project()
        res = _run_gm(p, _fails_first(5, _boom))
        json.dumps(res.summary(), allow_nan=False)


# ======================================================================
class TestOverallSlopeSaysItWithoutLosingTheCount:
    """Why the two loops DIVERGE, pinned so nobody unifies them."""

    def _run(self, factory, num_samples=5, mids=(_MID,)):
        from ogr_core.statistics import (
            SamplingMethod as SM, run_overall_slope,
        )
        p = _project()
        return p, run_overall_slope(p, factory, _vars(p), list(mids),
                                    num_samples=num_samples,
                                    sampling=SM.LATIN_HYPERCUBE, seed=1)

    def test_the_method_keeps_its_entry_and_its_failed_count(self):
        """CONSERVATION, and the reason this file exists in two shapes.

        ``test_overall_slope_v137.test_failed_searches_counted`` asserts
        exactly this and the ficha lists that file as untouchable, so here
        the entry may NOT be dropped the way Global Minimum drops it.
        Anyone who "unifies" the two loops fails here with the reason in
        front of them.
        """
        def _broken(_mid):
            raise RuntimeError("engineered")

        _p, res = self._run(_broken)
        assert res.by_method[_MID].failed_samples == 5
        assert "warning" in res.by_method[_MID].notes

    def test_but_it_reports_no_probability_of_failure(self):
        def _broken(_mid):
            raise RuntimeError("engineered")

        _p, res = self._run(_broken)
        ores = res.by_method[_MID]
        assert ores.statistics.n == 0
        assert ores.probability_of_failure is None
        assert ores.reliability_index is None

    def test_the_run_is_not_ok_and_the_reason_rises_to_error(self):
        """This function had no roll-up at all: ``by_method`` was filled
        unconditionally, so ``ok`` was always true past the guards."""
        def _broken(_mid):
            raise RuntimeError("engineered")

        _p, res = self._run(_broken)
        assert not res.ok
        assert _MID in res.notes.get("error", "")

    def test_a_search_with_no_critical_is_named_apart_from_one_that_raised(
            self):
        class _Empty:
            critical = None
            evaluations: list = []

        class _Silent:
            def run(self, _project):
                return _Empty()

        def _broken(_mid):
            raise RuntimeError("engineered")

        _p, raised = self._run(_broken)
        _q, silent = self._run(lambda _mid: _Silent())
        assert "raised RuntimeError" in raised.notes["error"]
        assert "no critical surface" in silent.notes["error"]

    def test_a_healthy_overall_slope_run_says_nothing_new(self):
        """CONSERVATION: the guard must be MUTE on a sound model."""
        _p, res = self._run(_search, num_samples=3)
        assert res.ok
        assert "error" not in res.notes
        assert "warning" not in res.notes


# ======================================================================
class TestAMixedRunIsStillARun:
    """One method answers, another loses everything."""

    def _mixed(self, num_samples=4):
        """The first method loses everything, the second answers.

        Chosen BY CALL ORDER and not by asking the search which method it
        holds: measured, an ``LEMMethod`` exposes no ``method_id``, and
        ``run_global_minimum`` walks ``critical_surfaces`` in insertion
        order, so the first ``num_samples`` evaluations are the first
        method's and no others.
        """
        from ogr_core.statistics import (
            SamplingMethod as SM, run_global_minimum,
        )
        p = _project()
        det = _det(p, (_MID, _OTHER))
        import ogr_core.statistics.probabilistic as P
        with _instead_of(P, "_evaluate_on",
                         _fails_first(num_samples, _boom)):
            return run_global_minimum(p, det, _vars(p),
                                      num_samples=num_samples,
                                      sampling=SM.LATIN_HYPERCUBE, seed=1,
                                      num_slices=14)

    def test_the_run_is_ok_when_one_method_answered(self):
        res = self._mixed()
        assert res.ok
        assert _MID not in res.by_method
        assert _OTHER in res.by_method

    def test_the_summary_speaks_for_the_method_that_has_a_sample(self):
        """Against 0.1.168 ``next(iter(...))`` could hand back the empty
        one; ``reported`` cannot."""
        res = self._mixed()
        assert res.reported is res.by_method[_OTHER]
        assert isinstance(res.reported.probability_of_failure, float)

    def test_the_lost_method_is_named_in_the_warning(self):
        """The partial silence: a PF computed over fewer methods than the
        user asked for, said out loud."""
        res = self._mixed()
        assert _MID in res.notes.get("warning", "")
        assert "error" not in res.notes

    def test_nothing_is_said_when_nothing_was_lost(self):
        """CONSERVATION, and the twin of regla 7: a guard that speaks on a
        sound run is a guard that has stopped measuring."""
        import ogr_core.statistics.probabilistic as P
        p = _project()
        res = _run_gm(p, P._evaluate_on, num_samples=4)
        assert res.ok
        assert "error" not in res.notes
        assert "warning" not in res.notes


# ======================================================================
class TestTheEmptyStatisticIsNotANumber:
    def test_no_sample_means_no_statistic(self):
        from ogr_core.statistics import SampleStatistics
        st = SampleStatistics()
        assert st.mean is None
        assert st.std_dev is None
        assert st.minimum is None
        assert st.maximum is None
        assert st.probability_of_failure() is None
        assert st.reliability_index() is None
        assert st.lognormal_reliability_index() is None

    def test_the_reliability_index_used_to_say_failure_was_certain(self):
        """The worst of the three old shapes, and the one nothing pinned.

        ``std_dev`` short-circuited to ``0.0`` for ``n < 2`` and then
        ``nan >= 1.0`` was False, so an empty sampling answered ``-inf``.
        A ``nan`` at least looks wrong.
        """
        from ogr_core.statistics import SampleStatistics
        assert SampleStatistics().reliability_index() != float("-inf")

    def test_one_sample_is_where_the_guard_stops(self):
        """THE FENCE, declared. With data present the degenerate answers
        stay: they are defined quantities, and the ``inf`` is D91's signal
        for a variable that no longer writes."""
        from ogr_core.statistics import SampleStatistics
        st = SampleStatistics(values=[1.5])
        assert st.mean == 1.5
        assert st.std_dev == 0.0
        assert st.probability_of_failure() == 0.0
        assert st.reliability_index() == float("inf")
        assert math.isnan(st.lognormal_reliability_index())

    def test_the_ordinary_case_is_recomputed_and_unchanged(self):
        """CONSERVATION, recomputed here rather than fixed: regla 1."""
        import statistics as pystat
        from ogr_core.statistics import SampleStatistics
        vals = [0.8, 1.1, 1.4, 0.95, 1.25]
        st = SampleStatistics(values=list(vals))
        assert abs(st.mean - pystat.mean(vals)) < 1e-15
        assert abs(st.std_dev - pystat.stdev(vals)) < 1e-15
        assert st.probability_of_failure() == 2 / 5
        assert abs(st.reliability_index()
                   - (pystat.mean(vals) - 1.0) / pystat.stdev(vals)) < 1e-12


# ======================================================================
class TestTheTwentyPercentSentenceDidNotMove:
    """What the ficha asked for with the wrong number."""

    def test_five_of_twenty_trips_it_and_the_words_are_the_same(self):
        res = _run_gm(_project(), _fails_first(5, _boom))
        assert res.by_method[_MID].notes["warning"] == _TWENTY_PERCENT

    def test_four_of_twenty_does_not(self):
        """The other side of the edge, and why the ficha's "3 of 20" does
        not exist: the test is ``failed > 0.2 * n``, so 3 and 4 both fall
        on the silent side."""
        res = _run_gm(_project(), _fails_first(4, _boom))
        assert "warning" not in res.by_method[_MID].notes

    def test_a_method_with_five_failures_is_still_a_result(self):
        """CONSERVATION: the new guard must not swallow the partial case,
        and the count is conserved."""
        res = _run_gm(_project(), _fails_first(5, _boom))
        mres = res.by_method[_MID]
        assert res.ok
        assert mres.statistics.n == 15
        assert mres.statistics.n + mres.failed_samples == 20
        assert isinstance(mres.probability_of_failure, float)


# ======================================================================
try:
    import matplotlib
    matplotlib.use("Agg")
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


@_requires_qt
class TestTheInterfaceShowsANumberOrTheReason:
    def _window(self):
        from test_statistics_gui_v138 import _define_vars, _project, _window
        QApplication.instance() or QApplication([])
        p = _project(n=6)
        _define_vars(p)
        return _window(p)

    def test_an_all_failed_run_prints_the_reason_instead_of_nan(self):
        import ogr_core.statistics.probabilistic as P
        w = self._window()
        try:
            with _instead_of(P, "_evaluate_on", _boom):
                w._compute_statistics()
            assert w._prob_result is None
            said = w.ogr_status.currentMessage()
            assert "nan" not in said, said
        finally:
            w.close()

    def test_the_reason_also_reaches_the_analysis_notes_panel(self):
        """A note nobody can still read is a note that does not exist: the
        status bar keeps one message and drops it after twelve seconds."""
        import ogr_core.statistics.probabilistic as P
        w = self._window()
        try:
            with _instead_of(P, "_evaluate_on", _boom):
                w._compute_statistics()
            assert any("bishop" in n for n in w.last_statistics_notes), \
                w.last_statistics_notes
        finally:
            w.close()

    def test_a_healthy_run_is_unchanged(self):
        """CONSERVATION: the ordinary path still reports a number."""
        w = self._window()
        try:
            w._compute_statistics()
            assert w._prob_result is not None and w._prob_result.ok
            assert "nan" not in w.ogr_status.currentMessage()
        finally:
            w.close()
