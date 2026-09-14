# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.170 (D129) — a method the run could not use is named, once, by name,
and on its own line.

WHAT INVARIANT THIS PROTECTS. When a statistical run is asked for several
methods and only SOME of them can be run, the user saw one method fewer and
no useful signal. v0.1.169 (D127) built the channel for the case where a
method loses every sample; this is the half that was left. Measured against
0.1.169, driving ``_publish_method_losses`` and the real ``_split`` of
``AnalysisNotesPanel``::

    A  a method with no samples   -> "bishop_simplified: all 10 samples..."
                                     grouped under `bishop_simplified`  OK
    B  a method REFUSED by                                              --
       _cannot_reevaluate         -> "The deterministic critical surface
                                      is a composite one... this method
                                      was skipped."
                                     grouped under `Model`              BAD
    C  two methods lost           -> both joined into ONE string,
                                     all of it under `bishop_simplified` BAD

B is the ficha's own case: the user read "this method was skipped" without
being told WHICH. The cause was that ``_no_sample_note`` wrote a
``"<mid>: "`` prefix and the three sentences of ``_cannot_reevaluate`` did
not -- an invariant honoured by two writers out of five. The cause of C was
that the roll-up produced one joined string, while ``_split`` takes only the
FIRST prefix in a line.

WHAT THE MEASUREMENT REFUTES IN THE FICHA, written here because a reader who
trusts it will look for code that is not there:

* its closing criterion is already satisfied and cannot fail. It asks for a
  ``grep`` of ``last_statistics_notes`` in ``main_window.py`` with "at least
  two lines"; there were EIGHT before this version was started, put there by
  v0.1.164 and v0.1.169. It is the ghost of the 210 budget again;
* its step 1 was already done for ``run_global_minimum``. Writing it as
  worded would have said the sentence TWICE, because ``notes["warning"]``
  already contains the per-method lines;
* its step 1 asks to walk "every key of ``res.notes`` that is a requested
  method and is not in ``by_method``". That is dispatching on the shape of a
  dictionary, which the docstring of ``_publish_method_losses`` calls
  "literally D59" -- and here it is also measurably wrong: ``run_sensitivity``
  keeps a key called ``"variables"`` that is not a method, and the panel
  would file it under a phantom method of that name;
* every one of its line citations was stale on the day it was read, which is
  why nothing here is located by line number and everything by symbol name;
* the file is not ``_v1160``: ``_vNNNN`` is the version the test LANDS in.

WHAT THIS FILE MEASURES, and it was checked rather than assumed: against
the 0.1.169 tree with only this file added, 26 of its 34 cases fail and 8
pass -- and the 8 are the ones that should. Six are CONSERVATION (the
v0.1.154 roll-up, v1164's empty-channel fence, the status bar still
reporting the survivor, the engine still refusing a composite, a partial run
still publishing a number, and the 20 % sentence word for word) and two are
declared CONTROL below: they are green on both sides on purpose, because
they guard against a mistake this design could make rather than against the
defect it removes, and a test whose docstring does not say which of the two
it is will be read as the wrong one.

THIS IS NOT A SNAPSHOT TEST. Not one assertion fixes a factor of safety.
What is checked are identities, names, counts and groupings recomputed here:
that the store keeps the bare fact and the channel puts the name on, that
two losses are two lines, that a sentence reaching ``notes`` also reaches
``note_lines``, and that a sound run says nothing at all.

ONE HONEST LIMIT, a fence rather than an oversight. ``_compute_statistics``
only keeps a result when it is ``ok``, so a run that failed ENTIRELY never
reaches ``StatisticsWindow``: the label pinned below is for the PARTIAL case,
which is what D129 is about, and the total case stays with the status bar
and the notes panel. And in ``run_sensitivity`` a method that entered the
sweep and came out with zero valid points still leaves ``by_method`` without
a note of its own; there is no measured reproduction of that state, and
inventing a sentence for it would be the ajuste-que-no-hace-nada of regla 7.

Regla 5 — everything this file patches, it puts back, in a ``finally``. The
runner has no ``monkeypatch``, so the restoring is written out, and the
non-modal windows it opens are closed.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_probabilistic_all_failed_v1169 import (  # noqa: E402
    _MID, _OTHER, _TWENTY_PERCENT, _det, _fails_first, _instead_of,
    _project as _ej1, _run_gm, _vars,
)

#: The method the real door loses, and the one it keeps. MEASURED, not
#: chosen: on the notched model Spencer loses every sample of its own
#: accord (``no_lambda_bracket``), so using it as the survivor would have
#: produced a TOTAL loss dressed as a partial one -- the test would have
#: passed for the wrong reason. Bishop and Janbu both sample cleanly there.
_LOST = "janbu_simplified"
_KEPT = _MID
_SPENCER = "spencer"


# ======================================================================
# Building a result by hand, for the tests that are about the CHANNEL and
# not about the engine. It is the cheapest honest fixture: the channel's
# job is to render what the loops put in ``notes``, and driving it directly
# is what lets the groupings below be asserted without a search.
def _result(*with_samples):
    from ogr_core.statistics import SampleStatistics
    from ogr_core.statistics.probabilistic import (
        MethodProbabilisticResult, ProbabilisticResult,
    )
    res = ProbabilisticResult()
    for mid in with_samples:
        m = MethodProbabilisticResult(method_id=mid)
        m.statistics = SampleStatistics(values=[1.1, 1.2, 0.9])
        res.by_method[mid] = m
    return res


def _lose(res, mid, sentence):
    res.notes[mid] = sentence
    return mid


def _refusal():
    """A real refusal sentence, from the real guard."""
    from ogr_core.statistics.probabilistic import _cannot_reevaluate
    return _cannot_reevaluate(object(), {"type": "composite"})


def _no_samples(n=10):
    from ogr_core.statistics.probabilistic import _STEM_GM, _no_sample_note
    return _no_sample_note(n, _STEM_GM, {"zero_driving": n})


def _publish(res, lost):
    from ogr_core.statistics.probabilistic import _publish_method_losses
    _publish_method_losses(res, lost)
    return res


def _groups(lines):
    """The groups the real notes panel would file these lines under."""
    from ogr_gui.dialogs.analysis_notes_panel import _split
    return [_split(n)[0] for n in lines]


# ----------------------------------------------------------------------
# DOOR TWO: the real path, with nothing patched. On the notched model of
# v1154 the published circle cuts the ground four times, so with Composite
# Surfaces ON the critical surface is a ``composite`` and with it OFF it is
# a plain ``circle`` -- measured, both methods, 1.382281/3.358489 for Bishop
# and 1.380774/3.399257 for Spencer. Handing the samples a project with the
# option OFF therefore refuses the composite one and accepts the circle:
# a partial loss that no test double produced.
def _real_partial():
    import test_statistical_rebuild_v1154 as V

    on = V._notched()
    off = V._without_the_option(on)
    det = {_LOST: V._deterministic(on, _LOST),
           _KEPT: V._deterministic(off, _KEPT)}
    return off, det, V


def _run_real_partial(num_samples=2):
    from ogr_core.statistics import SamplingMethod as SM, run_global_minimum

    off, det, V = _real_partial()
    return run_global_minimum(off, det, [V._cohesion_var(off)],
                              num_samples=num_samples, sampling=SM.MONTE_CARLO,
                              seed=7, num_slices=V._SLICES)


@contextlib.contextmanager
def _refusing(first_only=True):
    """DOOR ONE: the ficha's own recipe, ``_cannot_reevaluate`` patched.

    It isolates the channel from whatever the guard happens to decide, and
    it is the reason door two exists next to it: a channel measured only
    through a test double has not been shown to be reachable.
    """
    import ogr_core.statistics.probabilistic as P

    state = {"n": 0}

    def _refuse(_project, _sd):
        state["n"] += 1
        if first_only and state["n"] > 1:
            return None
        return "engineered refusal"

    with _instead_of(P, "_cannot_reevaluate", _refuse):
        yield state


# ======================================================================
class TestThePrefixIsPutOnceAndOnlyOnce:
    """Case B, and the rule that makes it impossible again."""

    def test_the_store_keeps_the_bare_sentence(self):
        """``notes[mid]`` is the FACT, never the presentation.

        ``StatisticsWindow`` shows it under a combo that already names the
        method, so a stored prefix would have to be parsed off there.
        """
        res = _result(_SPENCER)
        _publish(res, [_lose(res, _MID, _no_samples())])
        assert not res.notes[_MID].startswith(_MID), res.notes[_MID]
        assert res.notes[_MID].startswith("all 10 samples")

    def test_the_refusal_is_named_instead_of_filed_under_the_model(self):
        """THE DEFECT. Before this version the refusal carried no prefix,
        so the panel filed it under "Model" and the user read "this method
        was skipped" with no way of telling which one."""
        res = _result(_SPENCER)
        _publish(res, [_lose(res, _MID, _refusal())])
        assert _groups(res.note_lines) == [_MID], res.note_lines
        assert res.note_lines[0].startswith(_MID + ": ")

    def test_the_name_is_not_put_on_twice(self):
        """The prefix moved out of ``_no_sample_note``; if it had been left
        there as well the line would read "bishop: bishop: ...", which is
        the shape a second writer of the same invariant produces."""
        res = _result(_SPENCER)
        _publish(res, [_lose(res, _MID, _no_samples())])
        line = res.note_lines[0]
        assert line.count(_MID + ": ") == 1, line

    def test_both_ways_of_losing_a_method_look_the_same_to_the_panel(self):
        """The IDENTITY this version buys: the channel does not care which
        of the two faults happened, which is what makes it survive D88
        changing the wording of one of them."""
        a = _result(_SPENCER)
        _publish(a, [_lose(a, _MID, _no_samples())])
        b = _result(_SPENCER)
        _publish(b, [_lose(b, _MID, _refusal())])
        assert _groups(a.note_lines) == _groups(b.note_lines) == [_MID]


# ======================================================================
class TestOneLinePerLostMethod:
    """Case C: a joined string hangs entirely off the first prefix."""

    def _two(self):
        res = _result(_SPENCER)
        lost = [_lose(res, _MID, _no_samples()),
                _lose(res, "janbu_simplified", _refusal())]
        return _publish(res, lost)

    def test_two_lost_methods_are_two_lines(self):
        assert len(self._two().note_lines) == 2

    def test_the_panel_groups_them_apart(self):
        res = self._two()
        groups = _groups(res.note_lines)
        assert groups == [_MID, "janbu_simplified"], groups
        assert "Model" not in groups

    def test_the_joined_string_still_names_both(self):
        """CONSERVATION: the status bar takes one string, and
        ``test_the_lost_method_is_named_in_the_warning`` of v1169 requires
        the method's name to be in it."""
        said = self._two().notes["warning"]
        assert _MID in said and "janbu_simplified" in said

    def test_a_previous_warning_is_concatenated_and_not_overwritten(self):
        """The D91 sentence may already own that key. Overwriting it would
        close one silence by opening the one before it."""
        res = _result(_SPENCER)
        res.notes["warning"] = "a stale variable was not sampled"
        _publish(res, [_lose(res, _MID, _no_samples())])
        assert res.notes["warning"].startswith("a stale variable")
        assert _MID in res.notes["warning"]


# ======================================================================
class TestTheRealPathWithNothingPatched:
    """DOOR TWO. A channel only ever measured through a test double has
    not been shown to be reachable."""

    def test_a_composite_critical_is_refused_while_a_circle_answers(self):
        res = _run_real_partial()
        assert res.ok, res.notes
        assert _LOST not in res.by_method
        assert _KEPT in res.by_method

    def test_the_lost_method_is_named_on_its_own_line(self):
        res = _run_real_partial()
        assert _groups(res.note_lines) == [_LOST], res.note_lines
        assert "Composite Surfaces" in res.note_lines[0]

    def test_the_surviving_method_still_reports_a_number(self):
        """CONSERVATION: a partial run is still a run."""
        res = _run_real_partial()
        assert res.reported is not None
        assert isinstance(res.reported.probability_of_failure, float)

    def test_the_patched_door_agrees_with_the_real_one(self):
        """The two doors have to produce the same SHAPE, or one of them is
        measuring something else."""
        from ogr_core.statistics import (
            SamplingMethod as SM, run_global_minimum,
        )
        p = _ej1()
        det = _det(p, (_MID, _OTHER))
        with _refusing():
            res = run_global_minimum(p, det, _vars(p), num_samples=2,
                                     sampling=SM.MONTE_CARLO, seed=7,
                                     num_slices=14)
        assert res.ok
        assert len(res.note_lines) == 1
        assert _groups(res.note_lines) == [_MID]


# ======================================================================
class TestSensitivityHasThePartialRollUpAtLast:
    """The half v0.1.169 left open: ``run_sensitivity`` published a
    per-method refusal ONLY when no method survived at all."""

    def _partial(self):
        from ogr_core.statistics import run_sensitivity

        off, det, V = _real_partial()
        return run_sensitivity(off, det, [V._cohesion_var(off)], intervals=2,
                               num_slices=V._SLICES)

    def test_a_partial_sensitivity_run_says_which_method_it_lost(self):
        res = self._partial()
        assert res.ok, res.notes
        assert _LOST not in res.by_method
        assert _LOST in res.notes.get("warning", ""), res.notes

    def test_the_line_reaches_the_channel_too(self):
        res = self._partial()
        assert _groups(res.note_lines) == [_LOST], res.note_lines

    def test_a_healthy_sensitivity_run_says_nothing(self):
        """Regla 7's twin: the channel must stay quiet with nothing to
        say, or every sound run grows a warning."""
        from ogr_core.statistics import run_sensitivity

        import test_statistical_rebuild_v1154 as V
        off = V._without_the_option(V._notched())
        det = {_MID: V._deterministic(off, _MID)}
        res = run_sensitivity(off, det, [V._cohesion_var(off)], intervals=2,
                              num_slices=V._SLICES)
        assert res.ok
        assert res.note_lines == [], res.note_lines
        assert "warning" not in res.notes and "error" not in res.notes

    def test_the_total_refusal_still_rises_to_error(self):
        """CONSERVATION of the v0.1.154 roll-up that this version
        replaced: with nothing surviving, the reason has to reach the one
        key the interface prints."""
        from ogr_core.statistics import run_sensitivity

        import test_statistical_rebuild_v1154 as V
        on = V._notched()
        off = V._without_the_option(on)
        det = {_MID: V._deterministic(on, _MID)}
        res = run_sensitivity(off, det, [V._cohesion_var(off)], intervals=2,
                              num_slices=V._SLICES)
        assert not res.by_method
        assert "Composite Surfaces" in res.notes.get("error", "")
        assert "variable ranges" not in res.notes.get("error", "")


# ======================================================================
class TestTheChannelAndTheStringAreTheSameContent:
    """This is what stands in for a fallback branch in the interface.

    ``_compute_statistics`` feeds the panel from ``note_lines`` ALONE. If a
    sentence could reach ``notes`` without reaching ``note_lines`` the
    panel would lose it, so the invariant is pinned here rather than
    guarded there -- a branch that cannot fire is dead code, and dead code
    is regla 7 with its sign changed.
    """

    def _runs(self):
        from ogr_core.statistics import (
            SamplingMethod as SM, run_global_minimum, run_overall_slope,
            run_sensitivity,
        )
        import test_statistical_rebuild_v1154 as V

        on = V._notched()
        off = V._without_the_option(on)
        var = V._cohesion_var(off)
        det_bad = {_MID: V._deterministic(on, _MID)}
        out = []
        # no random variable at all
        out.append(run_global_minimum(off, det_bad, [], num_samples=2,
                                      sampling=SM.MONTE_CARLO, seed=1,
                                      num_slices=V._SLICES))
        # no deterministic result at all
        out.append(run_global_minimum(off, {}, [var], num_samples=2,
                                      sampling=SM.MONTE_CARLO, seed=1,
                                      num_slices=V._SLICES))
        # every method refused
        out.append(run_global_minimum(off, det_bad, [var], num_samples=2,
                                      sampling=SM.MONTE_CARLO, seed=1,
                                      num_slices=V._SLICES))
        # the sensitivity twin of the last one
        out.append(run_sensitivity(off, det_bad, [var], intervals=2,
                                   num_slices=V._SLICES))
        # no method selected
        out.append(run_overall_slope(off, lambda _m: None, [var], [],
                                     num_samples=2, sampling=SM.MONTE_CARLO,
                                     seed=1))
        # the partial one
        out.append(_run_real_partial())
        return out

    def test_a_sentence_in_notes_always_has_a_line(self):
        for res in self._runs():
            said = res.notes.get("error") or res.notes.get("warning")
            if said:
                assert res.note_lines, (said, res.notes)

    def test_every_line_is_part_of_what_notes_says(self):
        """The two are the same content, so a line the string never
        mentions would mean the status bar and the panel disagree."""
        for res in self._runs():
            whole = " ".join(str(v) for v in res.notes.values())
            for line in res.note_lines:
                head = line.split(": ", 1)[-1][:40]
                assert head in whole, (line, res.notes)


# ======================================================================
class TestTheThirdSilentRouteSaysSomething:
    """``if method is None or det is None: continue`` was a bare
    ``continue`` -- a third route to the same defect, and a reachable one:
    ``build_method`` answers ``None`` for a method id that is not in the
    registry, which is how "Janbu Corrected" could be ticked and produce
    nothing whatsoever."""

    def _run(self, det):
        from ogr_core.statistics import (
            SamplingMethod as SM, run_global_minimum,
        )
        import test_statistical_rebuild_v1154 as V
        off = V._without_the_option(V._notched())
        return run_global_minimum(off, det, [V._cohesion_var(off)],
                                  num_samples=2, sampling=SM.MONTE_CARLO,
                                  seed=1, num_slices=V._SLICES)

    def _det_for(self, mid):
        import test_statistical_rebuild_v1154 as V
        off = V._without_the_option(V._notched())
        return V._deterministic(off, _MID)

    def test_an_unregistered_method_is_named_instead_of_vanishing(self):
        res = self._run({"no_such_method": self._det_for(_MID)})
        assert not res.ok
        assert "no_such_method" in res.notes.get("error", ""), res.notes
        assert _groups(res.note_lines) == ["no_such_method"]

    def test_it_reuses_the_words_the_deterministic_path_already_uses(self):
        """v0.1.77 published a sentence for this precondition on the
        deterministic path. A second sentence for the same precondition is
        how two texts start to contradict each other."""
        from ogr_core.statistics.probabilistic import _NO_METHOD
        src = (Path(__file__).parent.parent / "ogr_slip2d"
               / "analysis_runner.py").read_text(encoding="utf-8")
        assert "is not a registered analysis method, so it was " in src
        assert _NO_METHOD.startswith("not a registered analysis method")

    def test_a_missing_deterministic_is_a_different_sentence(self):
        """Two causes, two sentences -- the same reason ``_sample_failure``
        tells an exception apart from a declared failure."""
        from ogr_core.statistics.probabilistic import (
            _NO_DETERMINISTIC, _NO_METHOD,
        )
        res = self._run({_MID: None})
        assert res.notes.get(_MID) == _NO_DETERMINISTIC
        assert _NO_DETERMINISTIC != _NO_METHOD


# ======================================================================
class TestTheTwentyPercentWarningReachesThePanel:
    """``mres.notes`` was read by nobody in the program."""

    def _five_of_twenty(self):
        from test_probabilistic_all_failed_v1169 import _boom
        return _run_gm(_ej1(), _fails_first(5, _boom))

    def test_the_surviving_method_warning_is_published(self):
        res = self._five_of_twenty()
        assert res.ok
        assert any(_TWENTY_PERCENT in n for n in res.note_lines), \
            res.note_lines

    def test_the_sentence_itself_did_not_move(self):
        """CONSERVATION, word for word. This version opens the channel; it
        does not rewrite the note, and v1169 pins the text exactly."""
        res = self._five_of_twenty()
        assert res.by_method[_MID].notes["warning"] == _TWENTY_PERCENT

    def test_it_does_not_become_a_headline(self):
        """CONTROL, and the fence around the change above.

        The warning goes to ``note_lines`` and NOWHERE else: ``notes`` is
        the status bar's single line and a per-method detail is not a
        headline. Green on 0.1.169 too, where nothing published it at all,
        so it measures no defect -- what it pins is that opening the
        channel did not quietly change what ``notes`` answers on a
        partly-failed run, which every older assertion depends on.
        """
        res = self._five_of_twenty()
        assert "warning" not in res.notes and "error" not in res.notes

    def test_surfaces_tracked_is_not_published(self):
        """Measured: a healthy Overall Slope run carries
        ``surfaces_tracked`` on every method, so surfacing ``mres.notes``
        wholesale would put a diagnostic count on every sound run."""
        from ogr_core.statistics.probabilistic import (
            _publish_method_warnings,
        )
        res = _result(_MID)
        res.by_method[_MID].notes["surfaces_tracked"] = 115
        _publish_method_warnings(res)
        assert res.note_lines == []

    def test_a_lost_method_is_not_named_twice(self):
        """A method that lost everything KEEPS its entry in Overall Slope
        and already has a line from the losses; without the ``n > 0``
        filter it would be named twice for one fault."""
        from ogr_core.statistics.probabilistic import (
            _publish_method_warnings,
        )
        res = _result()            # no method has a sample
        from ogr_core.statistics import SampleStatistics
        from ogr_core.statistics.probabilistic import (
            MethodProbabilisticResult,
        )
        m = MethodProbabilisticResult(method_id=_MID)
        m.statistics = SampleStatistics(values=[])
        m.notes["warning"] = "20 of 20 searches produced no valid surface."
        res.by_method[_MID] = m
        _publish_method_warnings(res)
        assert res.note_lines == []


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


def _window():
    from test_statistics_gui_v138 import _define_vars, _project, _window as _w
    QApplication.instance() or QApplication([])
    p = _project(n=6)
    _define_vars(p)
    return _w(p)


@_requires_qt
class TestTheInterfaceShowsWhoIsMissing:

    def test_the_lost_method_reaches_the_notes_panel(self):
        """A note nobody can still read is a note that does not exist: the
        status bar keeps one message and drops it after twelve seconds."""
        w = _window()
        try:
            with _refusing():
                w._compute_statistics()
            assert w._prob_result is not None and w._prob_result.ok
            assert any(n.startswith(_MID + ": ")
                       for n in w.last_statistics_notes), \
                w.last_statistics_notes
        finally:
            w.close()

    def test_the_status_bar_still_reports_the_survivor(self):
        """CONSERVATION: a partial run still publishes its number."""
        w = _window()
        try:
            with _refusing():
                w._compute_statistics()
            said = w.ogr_status.currentMessage()
            assert "PF = " in said and "nan" not in said, said
        finally:
            w.close()

    def test_the_sentence_is_not_said_twice(self):
        """CONTROL: green before and after, and that is said out loud.

        ``notes["warning"]`` CONTAINS the per-method lines, so feeding the
        panel from BOTH would repeat them -- which is what implementing the
        ficha's step 1 as worded, on top of the append that was already
        there, would have produced. 0.1.169 does not duplicate either, so
        this measures no defect; it guards this design against a mistake it
        is able to make, which is a different job and worth keeping.
        """
        w = _window()
        try:
            with _refusing():
                w._compute_statistics()
            lines = w.last_statistics_notes
            assert len(lines) == len(set(lines)), lines
            assert sum(1 for n in lines if "engineered refusal" in n) == 1
        finally:
            w.close()

    def test_a_healthy_run_leaves_the_channel_empty(self):
        """CONSERVATION of v1164's own fence."""
        w = _window()
        try:
            w._compute_statistics()
            assert w._prob_result is not None and w._prob_result.ok
            assert w.last_statistics_notes == [], w.last_statistics_notes
        finally:
            w.close()


@_requires_qt
class TestTheStatisticsWindowSaysWhoIsMissing:

    def _shown(self, refuse):
        from ogr_gui.statistics_window import StatisticsWindow
        w = _window()
        try:
            if refuse:
                with _refusing():
                    w._compute_statistics()
            else:
                w._compute_statistics()
            return w, StatisticsWindow(w.project, w._prob_result,
                                       w._sens_result, None)
        except Exception:                                    # noqa: BLE001
            w.close()
            raise

    def test_the_label_is_hidden_on_a_sound_run(self):
        """Regla 7 in interface form: with nothing to say the window is
        the one it has always been."""
        w, sw = self._shown(False)
        try:
            assert sw.lbl_run_notes.isVisibleTo(sw) is False
            assert sw.lbl_run_notes.text() == ""
        finally:
            sw.close()
            w.close()

    def test_the_label_names_the_method_missing_from_the_selector(self):
        """THE DEFECT, in the window: in Global Minimum the refused method
        is not in ``by_method``, so it is not even in the combo -- the user
        saw two methods where three were asked for."""
        w, sw = self._shown(True)
        try:
            ids = [sw.cbo_method.itemText(i)
                   for i in range(sw.cbo_method.count())]
            assert _MID not in ids, ids
            assert _MID in sw.lbl_run_notes.text(), sw.lbl_run_notes.text()
            assert sw.lbl_run_notes.isVisibleTo(sw) is True
        finally:
            sw.close()
            w.close()

    def test_redrawing_does_not_erase_it(self):
        """It is a widget of its own precisely because ``self.status`` is
        rewritten on every redraw."""
        w, sw = self._shown(True)
        try:
            before = sw.lbl_run_notes.text()
            for i in range(sw.cbo_plot.count()):
                sw.cbo_plot.setCurrentIndex(i)
                sw._redraw()
            assert sw.lbl_run_notes.text() == before
        finally:
            sw.close()
            w.close()

    def test_a_method_with_no_result_says_why(self):
        """The generic sentence is true and useless on its own. This is the
        Overall Slope shape, where the lost method KEEPS its entry and is
        therefore selectable."""
        from ogr_gui.statistics_window import StatisticsWindow
        res = _result(_SPENCER)
        _publish(res, [_lose(res, _MID, _refusal())])
        # The selector is driven by ``by_method``; put the lost method back
        # in it the way Overall Slope does, with no samples behind it.
        from ogr_core.statistics import SampleStatistics
        from ogr_core.statistics.probabilistic import (
            MethodProbabilisticResult,
        )
        m = MethodProbabilisticResult(method_id=_MID)
        m.statistics = SampleStatistics(values=[])
        res.by_method[_MID] = m
        QApplication.instance() or QApplication([])
        sw = StatisticsWindow(_ej1(), res, None, None)
        try:
            sw.cbo_method.setCurrentIndex(
                [sw.cbo_method.itemText(i)
                 for i in range(sw.cbo_method.count())].index(_MID))
            sw._redraw()
            said = sw.status.text()
            assert "Composite Surfaces" in said, said
        finally:
            sw.close()
