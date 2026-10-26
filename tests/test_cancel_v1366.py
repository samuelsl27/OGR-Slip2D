# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.366 (D362) — Cancel stops the calculation, publishes nothing, and a
Compute after it does not break anything; the result of a run is stamped
with the model it started from; the bar moves while the critical surface is
optimised, and the dialog says that is what it is doing.

The finding (the sixth interface test, 0.1.357, H12 and H11; measured with
``_auditoria/P8_interfaz/repro_d362.py``):

* Cancel closed the dialog and set ``cancelled = True``, which nothing read.
  The thread went on, and published its result — stamped as current over a
  model edited while it ran (FS 1.154 on a surface that the edited model put
  at 1.071);
* Compute again after a Cancel replaced ``self.worker`` while the first
  thread still ran: when that QThread lost its last reference the process
  aborted ("QThread: Destroyed while thread is still running", 0xC0000409)
  and everything unsaved was lost;
* with one surface to optimise (Global Minimum, the default) the walk
  reported nothing: the bar stood at 100 % for minutes.

The owner's decision (2026-10-26): the stop is ``TaskCancelled``, a
``BaseException`` raised from the progress callback the calculation already
calls and from the checkpoints of ``ogr_core.progress`` in the loops that
call none (Picard, its rescue); the engine changes no signature. And the
dialog names the optimisation phase.

What these tests protect:

* **the two scenes of repro_d362**, through the real window with its thread:
  Cancel pressed while the search runs stops it, nothing is published, the
  dialog says "Cancelling..." and stays until the thread has returned, the
  model and the undo history are untouched; and a Compute right after it
  runs to the end and gives the factor of a fresh run (rule 7: the button
  moves the outcome);
* the fingerprint is the model's as the run STARTED: an edit that gets in
  while it runs leaves the result stale, not current;
* the other six calculations (statistics, steady and transient groundwater,
  back analysis, optimisation, drawdown sweep) stop the same way and keep
  nothing;
* a parallel grid drops its queued batches instead of finishing the grid
  the user cancelled, and leaves no worker behind;
* the progress of the optimisation: with one surface the walk reports its
  evaluations, in the OPTIMIZE phase, and the dialog says so (in Spanish);
* **no number moves**: with a callback that never stops them, the search,
  the walk, the steady and transient seepage, the statistics, the back
  analysis and the sweep give exactly what they give without one.

The cancellations are driven by a HANDSHAKE, not a timer (see
``test_background_tasks_v1365``): the calculation posts an event to the
window and waits; the window, dispatching it, presses Cancel on the real
dialog.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


_MISSING = object()


@contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


def _window(project=None):
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    if project is None:
        w.act_load_demo()
    else:
        w._attach_project(project)
    w._update_statistics_actions()
    w._tasks_threaded = True
    w.project.is_dirty = False
    w.command_stack.clear()
    return w


def _done(w):
    for name in ("_stats_window", "_analysis_notes_panel"):
        other = getattr(w, name, None)
        if other is not None:
            other.close()
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


def _state(w):
    return (json.dumps(w.project.to_dict(), sort_keys=True, default=str),
            w.command_stack.history(), w.project.is_dirty)


class _Handshake:
    """Wraps ``module.name``. The first time the wrapped calculation is
    called — or, with ``at_progress``, the first time it reports progress —
    it posts an event to the window's thread and waits for it; the window,
    dispatching it, runs ``on_window(dialog)`` with the modal dialog that is
    in front. Then the calculation goes on."""

    def __init__(self, module, name, on_window, at_progress=False):
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QApplication
        self.done = threading.Event()
        self.answered = None
        self.seen = {}
        outer = self

        class Probe(QObject):
            def event(self, ev):
                if ev.type() == QEvent.User:
                    try:
                        on_window(QApplication.activeModalWidget(), outer.seen)
                    finally:
                        outer.done.set()
                    return True
                return super().event(ev)
        self.probe = Probe()
        self.module, self.name = module, name
        self.real = getattr(module, name)

        def knock():
            from PySide6.QtCore import QCoreApplication
            if outer.answered is None:
                QCoreApplication.postEvent(outer.probe, QEvent(QEvent.User))
                outer.answered = outer.done.wait(10.0)

        def inner(*a, **k):
            if at_progress:
                cb = k.get("progress_cb")

                def first(done, total):
                    knock()
                    if cb is not None:
                        cb(done, total)
                k["progress_cb"] = first
            else:
                knock()
            return outer.real(*a, **k)
        setattr(module, name, inner)

    def restore(self):
        setattr(self.module, self.name, self.real)


def _press_cancel(dialog, seen):
    """What the user does: Cancel, on the dialog in front."""
    seen["dialog"] = type(dialog).__name__ if dialog is not None else None
    dialog.btn_cancel.click()
    seen["label"] = dialog.lbl_status.text()
    seen["still_open"] = not dialog.isHidden()
    seen["button"] = dialog.btn_cancel.isEnabled()


def _cancel_through(w, module, name, run, at_progress=False):
    """``run(w)`` with Cancel pressed by the handshake on ``module.name``;
    returns what the dialog showed and how long the run took."""
    shake = _Handshake(module, name, _press_cancel, at_progress=at_progress)
    t = time.perf_counter()
    try:
        run(w)
    finally:
        shake.restore()
    seen = dict(shake.seen)
    seen["answered"] = shake.answered
    seen["seconds"] = time.perf_counter() - t
    return seen


def _assert_cancelled(w, seen, before, what):
    assert seen.get("answered"), "the window dispatched nothing while computing"
    assert seen.get("dialog") == "TaskProgressDialog", seen
    assert seen.get("label") == "Cancelling...", seen
    assert seen.get("still_open") is True, "the dialog closed with the thread running"
    assert seen.get("button") is False, seen
    assert w.task_worker is None, "the thread is still there"
    assert _state(w) == before, "the cancelled run changed the model or the history"
    bar = w.statusBar().currentMessage()
    assert bar == "%s cancelled: nothing was changed." % what, bar


# ======================================================================
class TestTheTwoScenesOfTheReproduction:
    """repro_d362.py, ``cancel`` and ``again``."""

    def test_cancel_stops_the_search_and_publishes_nothing(self):
        import ogr_slip2d.analysis_runner as runner
        w = _window()
        try:
            before = _state(w)
            seen = _cancel_through(w, runner, "run_analysis",
                                   lambda w: w.act_compute(), at_progress=True)
            _assert_cancelled(w, seen, before, "Compute")
            assert w.last_search_results == {} and w.last_search_result is None
            assert w._results_model_hash is None
        finally:
            _done(w)

    def test_compute_again_after_cancel_runs_to_the_end(self):
        import ogr_slip2d.analysis_runner as runner
        from ogr_gui.main_window import _ComputeWorker
        w = _window()
        try:
            _cancel_through(w, runner, "run_analysis",
                            lambda w: w.act_compute(), at_progress=True)
            w.act_compute()                       # nothing pressed this time
            got = w.last_search_results["bishop_simplified"].critical.fos
            fresh = _ComputeWorker(w.project, ["bishop_simplified"])
            fresh.run()
            want = fresh.results["bishop_simplified"].critical.fos
            # rule 7: Cancel changed the outcome (nothing), the run after it
            # gives the factor of a fresh one
            assert got == want, (got, want)
            assert w._results_are_current()
        finally:
            _done(w)


class TestTheFingerprintIsTakenAtTheStart:

    def test_an_edit_while_it_runs_leaves_the_result_stale(self):
        """The window's edit gets in at the search's first progress, after
        the run took its (factored) copy: the result is of the model as it
        was, and must not read as current."""
        import ogr_slip2d.analysis_runner as runner

        def edit(_dialog, seen):
            mat = w.project.materials[0]
            mat.unit_weight = mat.unit_weight + 5.0
            seen["edited"] = True
        w = _window()
        try:
            shake = _Handshake(runner, "run_analysis", edit, at_progress=True)
            try:
                w.act_compute()
            finally:
                shake.restore()
            assert shake.seen.get("edited")
            assert w.last_search_result is not None
            assert not w._results_are_current(), \
                "a result of the old model is stamped as current"
        finally:
            _done(w)


# ======================================================================
class TestEveryCalculationStops:

    def test_statistics(self):
        import test_statistics_gui_v138 as sg
        import ogr_slip2d.analysis_runner as runner
        p = sg._project(n=12)
        sg._define_vars(p)
        w = _window(p)
        try:
            before = _state(w)
            seen = _cancel_through(w, runner, "run_configured_statistics",
                                   lambda w: w._compute_statistics())
            _assert_cancelled(w, seen, before, "Compute Statistics")
            assert w._prob_result is None
        finally:
            _done(w)

    def test_steady_groundwater(self):
        import test_background_tasks_v1365 as bt
        from ogr_slip2d import transient_stability as ts
        w = _window(bt._seepage_project())
        try:
            before = _state(w)
            seen = _cancel_through(w, ts, "solve_project_groundwater",
                                   lambda w: w._compute_groundwater())
            _assert_cancelled(w, seen, before, "Compute Groundwater")
            assert w.project.seepage_result is None
        finally:
            _done(w)

    def test_transient_groundwater(self):
        import test_initial_factor_v1309 as tf
        from ogr_slip2d import transient_stability as ts
        p, _full = tf._drawdown()
        w = _window(p)
        try:
            before = _state(w)
            seen = _cancel_through(w, ts, "run_transient_stability",
                                   lambda w: w._compute_groundwater())
            _assert_cancelled(w, seen, before, "Compute Groundwater")
            assert not w.project.transient_results
        finally:
            _done(w)

    def test_back_analysis(self):
        import ogr_slip2d.analysis_runner as runner
        from PySide6.QtWidgets import QDialog
        w = _window()
        try:
            before = _state(w)

            def run(w):
                with _swap(QDialog, "exec",
                           lambda self: QDialog.DialogCode.Accepted):
                    w._back_analysis()
            seen = _cancel_through(w, runner, "run_configured_back_analysis",
                                   run)
            _assert_cancelled(w, seen, before,
                              "Back Analysis of Support Force")
            assert w._back_analysis_result is None
        finally:
            _done(w)

    def test_optimisation(self):
        import test_optimize_wiring_v1104 as ow
        import ogr_slip2d.analysis_runner as runner
        from PySide6.QtWidgets import QInputDialog
        p = ow._slope()
        sr = runner.build_search(p, "bishop_simplified").run(p)
        w = _window(p)
        try:
            w.last_search_results = {"bishop_simplified": sr}
            w.last_search_result = sr
            before = _state(w)

            def run(w):
                with _swap(QInputDialog, "getInt", staticmethod(
                        lambda *a, **k: (ow._MAX_ITERATIONS, True))):
                    w._optimize_surfaces()
            seen = _cancel_through(w, runner, "run_configured_optimization",
                                   run)
            _assert_cancelled(w, seen, before, "Optimize Surfaces")
            assert w.last_search_results["bishop_simplified"] is sr
            assert sr.optimized is None
        finally:
            _done(w)

    def test_drawdown_sweep(self):
        import test_drawdown_sweep_v170 as dd
        import test_groundwater_ops_v1200 as go
        import ogr_slip2d.analysis_runner as runner
        from ogr_api import call
        from PySide6.QtWidgets import QDialog
        ws = go._ws()
        pid = ws.add(dd._homogeneous()).id
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], surface_type="circular",
             search_method="grid", num_slices=18,
             grid={"x_min": 60, "x_max": 240, "y_min": 160, "y_max": 420,
                   "nx": 3, "ny": 4},
             radius_increment=6, failure_direction="right_to_left")
        w = _window(ws.get(pid).project)
        try:
            before = _state(w)

            def run(w):
                with _swap(QDialog, "exec",
                           lambda self: QDialog.DialogCode.Accepted):
                    w._drawdown_sweep()
            seen = _cancel_through(w, runner,
                                   "run_configured_drawdown_sweep", run)
            _assert_cancelled(w, seen, before, "Drawdown Level Sweep")
            assert getattr(w, "last_drawdown_sweep", None) is None
        finally:
            _done(w)


# ======================================================================
class TestTheParallelGridDropsItsQueue:

    def test_the_queue_is_cancelled_and_no_worker_is_left(self):
        import pytest
        import psutil
        import test_window_grid_parallel_v1262 as gp
        from concurrent.futures import ProcessPoolExecutor

        from ogr_slip2d.analysis_runner import build_search
        p = gp._model()
        gp._needs_a_pool(p)
        calls = []
        real = ProcessPoolExecutor.shutdown

        def spy(self, wait=True, *, cancel_futures=False):
            calls.append((wait, cancel_futures))
            return real(self, wait=wait, cancel_futures=cancel_futures)

        class Stop(BaseException):
            pass

        def stop(_done, _total):
            raise Stop()
        search = build_search(p, "bishop_simplified", progress_cb=stop)
        with _swap(ProcessPoolExecutor, "shutdown", spy):
            with pytest.raises(Stop):
                search.run(p)
        assert (False, True) in calls, calls
        me = psutil.Process()
        end = time.time() + 30
        while me.children() and time.time() < end:
            time.sleep(0.2)
        assert not me.children(), [c.name() for c in me.children()]


# ======================================================================
class TestTheOptimisationReportsItsProgress:

    def test_one_surface_walks_with_the_bar_and_the_phase(self):
        """H11: with one surface to optimise the bar stood still."""
        import test_optimize_wiring_v1104 as ow

        from ogr_core.progress import OPTIMIZE, phase
        from ogr_slip2d.analysis_runner import build_search
        p = ow._slope()
        p.settings.search.optimize_enabled = True
        seen = []
        search = build_search(
            p, "bishop_simplified",
            progress_cb=lambda d, t: seen.append((phase(), d, t)))
        res = search.run(p)
        assert res.optimized is not None, "no walk ran"
        walk = [(d, t) for ph, d, t in seen if ph == OPTIMIZE]
        assert len(walk) > 10, seen[-5:]
        assert walk[-1][1] == p.settings.search.optimize_max_iterations
        assert [d for d, _t in walk] == sorted(d for d, _t in walk)

    def test_the_dialog_names_the_phase_in_spanish(self):
        from ogr_core.progress import OPTIMIZE
        from ogr_gui.dialogs.misc_dialogs import TaskProgressDialog
        from ogr_gui.i18n import current_language, set_language
        _app()
        was = current_language()
        set_language("es")
        d = TaskProgressDialog(None, "x", on_cancel=lambda: None)
        try:
            d.update_progress(5, 10, OPTIMIZE)
            assert d.lbl_status.text() == \
                "Optimizando la superficie crítica... 5/10"
            d.update_progress(5, 10, "")
            assert d.lbl_status.text() == "Calculando... 5/10"
            assert not d.btn_cancel.isHidden()
            d.reject()                             # Esc
            assert d.lbl_status.text() == "Cancelando..."
        finally:
            set_language(was)
            d.finish()

    def test_optimize_surfaces_through_the_window(self):
        import test_optimize_wiring_v1104 as ow
        import ogr_gui.dialogs.misc_dialogs as md
        from PySide6.QtWidgets import QInputDialog

        from ogr_core.progress import OPTIMIZE
        from ogr_slip2d.analysis_runner import build_search
        p = ow._slope()
        sr = build_search(p, "bishop_simplified").run(p)
        w = _window(p)
        got = []
        real = md.TaskProgressDialog.update_progress

        def spy(self, done, total, phase=""):
            got.append((phase, done, total))
            return real(self, done, total, phase)
        try:
            w.last_search_results = {"bishop_simplified": sr}
            w.last_search_result = sr
            with _swap(md.TaskProgressDialog, "update_progress", spy), \
                    _swap(QInputDialog, "getInt", staticmethod(
                        lambda *a, **k: (ow._MAX_ITERATIONS, True))):
                w._optimize_surfaces()
            assert w.last_search_results["bishop_simplified"].optimized
            assert got and all(ph == OPTIMIZE for ph, _d, _t in got), got[:5]
        finally:
            _done(w)


# ======================================================================
class TestNoNumberMoves:
    """A callback that never stops them: the same numbers as without one."""

    def test_the_search_and_its_walk(self):
        import test_optimize_wiring_v1104 as ow

        from ogr_slip2d.analysis_runner import build_search

        def run(cb):
            p = ow._slope()
            p.settings.search.optimize_enabled = True
            r = build_search(p, "bishop_simplified", progress_cb=cb).run(p)
            return ([repr(e.fos) for e in r.evaluations],
                    repr(r.critical.fos),
                    r.critical.surface.to_dict()["polyline"]["vertices"])
        assert run(lambda d, t: None) == run(None)

    def test_the_steady_and_transient_seepage(self):
        import test_background_tasks_v1365 as bt
        import test_initial_factor_v1309 as tf

        from ogr_core.progress import watching
        from ogr_slip2d.transient_stability import (run_transient_stability,
                                                    solve_project_groundwater)
        ticks = []
        a = solve_project_groundwater(bt._seepage_project())
        with watching(lambda: ticks.append(1)):
            b = solve_project_groundwater(bt._seepage_project())
        assert ticks, "no checkpoint in the Picard loop"
        assert a.total_head == b.total_head

        def transient(cb):
            p, _full = tf._drawdown()
            out = run_transient_stability(p, ["bishop_simplified"],
                                          progress_cb=cb)
            return ([r.total_head for r in out.results],
                    [s.factors for s in out.stages], out.initial.factors)
        n = []
        with watching(lambda: n.append(1)):
            got = transient(lambda d, t: None)
        assert n, "no checkpoint in the transient Picard loop"
        assert got == transient(None)

    def test_the_statistics_and_the_back_analysis(self):
        import test_statistics_gui_v138 as sg

        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import (run_configured_back_analysis,
                                                run_configured_statistics)

        def stats(cb):
            p = sg._project(n=12)
            sg._define_vars(p)
            out = run_configured_statistics(p, progress_cb=cb)
            res = out.probabilistic
            return ([list(r.statistics.values)
                     for r in res.by_method.values()],
                    {m: repr(c.fos) for m, c in out.deterministic.items()})
        assert stats(lambda d, t: None) == stats(None)

        def back(cb):
            res, _r, _w = run_configured_back_analysis(
                build_demo_project(), progress_cb=cb)
            return (repr(res.required_force), res.surfaces_analysed)
        assert back(lambda d, t: None) == back(None)

    def test_the_sweep(self):
        """Its level searches check for a stop now; the levels give the
        factors they gave with a search that did not."""
        import test_drawdown_sweep_v170 as dd
        import test_groundwater_ops_v1200 as go

        from ogr_api import call
        from ogr_core.statistics import run_drawdown_sweep
        from ogr_slip2d.analysis_runner import (build_search,
                                                run_configured_drawdown_sweep)
        ws = go._ws()
        pid = ws.add(dd._homogeneous()).id
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], surface_type="circular",
             search_method="grid", num_slices=18,
             grid={"x_min": 60, "x_max": 240, "y_min": 160, "y_max": 420,
                   "nx": 3, "ny": 4},
             radius_increment=6, failure_direction="right_to_left")
        p = ws.get(pid).project
        raw = run_drawdown_sweep(
            p, lambda mid: build_search(p, mid), ["bishop_simplified"],
            n_levels=2).by_method["bishop_simplified"].fos
        door, _rep, _w = run_configured_drawdown_sweep(p, n_levels=2)
        assert door.by_method["bishop_simplified"].fos == raw
