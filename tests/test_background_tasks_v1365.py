# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.365 (D348) — Compute Statistics, Compute Groundwater (steady and
transient), the back analysis and Optimize Surfaces run off the window's
thread, and the window keeps processing events while they do.

The finding (the fifth interface test, 0.1.355, H4): a two-stage transient
with factors held the window for about seven minutes, and the statistics with
fifty samples for about forty seconds, while Windows painted a dark window
over it and the agent's calls timed out. Read: those handlers called the
calculation directly, on the window's thread; only *Compute* and the drawdown
sweep had a thread, and the sweep's own comment said why the others needed
one.

``ogr_gui.background.run_task`` keeps each handler's shape — it returns the
result, so the code after the calculation, the undo step around it included,
reads as before — and keeps the event loop running with a window-modal
progress dialog in front. Without a display the calculation runs inline, as
before (the tests and the bank call these handlers and read the result on
the next line); ``window._tasks_threaded = True`` forces the thread, which is
what these tests do.

What they protect, for each of the five calculations:

* through the thread, the result is the result of the inline run, to the bit
  (the field, the factors per stage, the probability of failure and every
  sample, the required force, the optimised surface);
* while it runs, the window processes events, the progress dialog is the
  modal widget, and the agent's bridge answers Busy to an edit;

  measured by a HANDSHAKE, not by counting ticks of a timer: at its start the
  calculation posts an event to the window and waits (up to 3 s) for the
  window to dispatch it. On the old code the calculation runs on the
  window's own thread, the event cannot be dispatched, and the test fails.
  A timer was tried first and is not a measure here: on the "offscreen"
  platform, once a Statistics window has been shown in the process, the
  window's thread gets no turn of the GIL while a pure-Python calculation
  runs on another thread (0 ticks in 1.5 s; measured, 2026-10-25), although
  on the real desktop the same two runs in a row tick 2314 and 2301 times
  with the window never "Not Responding". The handshake asks only what the
  ticket asks — that the window's loop runs during the calculation — and the
  calculation waiting releases the GIL;
* the groundwater is still ONE undo step that marks the project modified,
  and the field it leaves on the project is the one computed on the copy;
* a refusal raised on the thread reaches the window's own handling.

And the dialog: it does not close (Esc, the title bar) until the calculation
has returned, because closing it would hand the window back with the thread
still running.
"""
from __future__ import annotations

import sys
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


def _window(project=None, threaded=False):
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    if project is None:
        w.act_load_demo()
    else:
        w.canvas.set_project(project)
        w.project = project
    w._update_statistics_actions()
    if threaded:
        w._tasks_threaded = True
    return w


def _done(w):
    for name in ("_stats_window", "_analysis_notes_panel"):
        other = getattr(w, name, None)
        if other is not None:
            other.close()
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


class _Handshake:
    """The calculation ``module.name``, wrapped: at its start it posts an
    event to the window's thread and waits for it to be dispatched, which is
    only possible while the window's event loop runs. The window's side
    records what is in front (the modal widget) and what the agent's bridge
    answers."""

    WAIT = 3.0

    def __init__(self, w, module, name):
        import threading

        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QApplication

        from ogr_gui.agent_bridge import WindowHost
        self.done = threading.Event()
        self.answered = None
        self.on_main = None
        self.modal = None
        self.busy = None
        host = WindowHost(w)
        outer = self

        class Probe(QObject):
            def event(self, ev):
                if ev.type() == QEvent.User:
                    m = QApplication.activeModalWidget()
                    outer.modal = type(m).__name__ if m is not None else None
                    outer.busy = bool(host.busy())
                    outer.done.set()
                    return True
                return super().event(ev)
        self.probe = Probe()
        self.module, self.name = module, name
        self.real = getattr(module, name)

        def inner(*a, **k):
            from PySide6.QtCore import QCoreApplication
            outer.on_main = (threading.current_thread()
                             is threading.main_thread())
            QCoreApplication.postEvent(outer.probe, QEvent(QEvent.User))
            outer.answered = outer.done.wait(outer.WAIT)
            return outer.real(*a, **k)
        setattr(module, name, inner)

    def restore(self):
        setattr(self.module, self.name, self.real)

    def check(self):
        assert self.on_main is False, "the calculation ran on the window's thread"
        assert self.answered, "the window dispatched no event while computing"
        assert self.modal == "TaskProgressDialog", self.modal
        assert self.busy is True, "the bridge would let an edit through"


def _same(threaded, inline):
    """Field by field, so a failure says which one moved."""
    assert len(threaded) == len(inline)
    moved = [(i, a, b) for i, (a, b) in enumerate(zip(threaded, inline))
             if a != b]
    assert not moved, "\n".join("field %d: thread %r / inline %r"
                                % (i, str(a)[:300], str(b)[:300])
                                for i, a, b in moved)


def _both(make, run, read, module, name):
    """``read(window)`` after ``run(window)``, inline and through the thread,
    each on a model of its own from ``make()``; through the thread, with the
    handshake on ``module.name``."""
    out = []
    for threaded in (False, True):
        w = _window(make(), threaded=threaded)
        try:
            shake = _Handshake(w, module, name) if threaded else None
            try:
                run(w)
            finally:
                if shake is not None:
                    shake.restore()
            if shake is not None:
                shake.check()
            out.append(read(w))
        finally:
            _done(w)
    return out


# ======================================================================
class TestStatistics:

    def test_the_same_run_through_the_thread(self):
        import test_statistics_gui_v138 as sg

        def make():
            p = sg._project(n=12)
            sg._define_vars(p)
            return p

        def read(w):
            res = w._prob_result
            assert res is not None
            return ({m: list(r.statistics.values)
                     for m, r in res.by_method.items()},
                    # the values, in the variables' order: the keys carry
                    # the material's id, new on every model built
                    [list(v) for v in res.samples.values()],
                    res.reported.probability_of_failure,
                    res.reported.reliability_index,
                    list(w.last_statistics_notes))
        import ogr_slip2d.analysis_runner as runner
        inline, threaded = _both(make, lambda w: w._compute_statistics(),
                                 read, runner, "run_configured_statistics")
        _same(threaded, inline)


# ======================================================================
def _seepage_project():
    import test_seepage_run_notes_v1352 as srn
    from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
    p = srn._seepage_project(transient=False)
    bcs = SeepageBoundaryConditions()
    for nid in sorted(p.fem_mesh.boundary_node_ids()):
        nd = p.fem_mesh.nodes[nid]
        if abs(nd.x) < 1e-9:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 6.0)
        elif abs(nd.x - srn._W) < 1e-9:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 3.0)
    p.seepage_bcs = bcs
    return p


class TestGroundwater:

    def _read(self, w):
        p = w.project
        steps = w.command_stack.history()[0]
        return (list(p.seepage_result.total_head),
                [(list(r.total_head), dict(r.notes.get("fos") or {}))
                 for r in (p.transient_results or [])],
                (list(p.transient_initial_result.total_head),
                 dict(p.transient_initial_result.notes.get("fos") or {}))
                if p.transient_initial_result is not None else None,
                p.is_dirty, list(steps),
                w._gw_solver is not None and w._gw_solver is p._gw_solver,
                w.statusBar().currentMessage())

    def test_the_steady_field_through_the_thread(self):
        from ogr_slip2d import transient_stability as ts
        inline, threaded = _both(_seepage_project,
                                 lambda w: w._compute_groundwater(),
                                 self._read, ts, "solve_project_groundwater")
        assert inline[0], "no field"
        assert inline[3] is True and inline[4] == ["Compute groundwater"]
        _same(threaded, inline)

    def test_the_transient_through_the_thread(self):
        import test_initial_factor_v1309 as tf

        def make():
            p, _full = tf._drawdown()
            p.settings.methods.enabled_methods = ["bishop_simplified"]
            return p
        from ogr_slip2d import transient_stability as ts
        inline, threaded = _both(make, lambda w: w._compute_groundwater(),
                                 self._read, ts, "run_transient_stability")
        assert inline[1] and all(fos for _h, fos in inline[1]), inline[1]
        assert inline[2] is not None and inline[2][1]
        _same(threaded, inline)

    def test_the_field_is_the_one_computed_on_the_copy(self):
        """And the live project is not the one the solve ran on."""
        from ogr_slip2d import transient_stability as ts
        seen = []
        real = ts.solve_project_groundwater

        def spy(project, **kw):
            seen.append(project)
            return real(project, **kw)
        w = _window(_seepage_project(), threaded=True)
        try:
            with _swap(ts, "solve_project_groundwater", spy):
                w._compute_groundwater()
            assert len(seen) == 1 and seen[0] is not w.project
            assert w.project.seepage_result is seen[0].seepage_result
            assert w.project._gw_solver is seen[0]._gw_solver
            assert w.project._fea_ponding_cache is None
        finally:
            _done(w)


# ======================================================================
class TestBackAnalysis:

    def _run(self, w):
        from PySide6.QtWidgets import QDialog
        with _swap(QDialog, "exec",
                   lambda self: QDialog.DialogCode.Accepted), \
                _swap(w, "_info", lambda *a: None):
            w._back_analysis()

    def test_the_same_force_through_the_thread(self):
        from ogr_core.project.demo import build_demo_project

        def read(w):
            res = w._back_analysis_result
            c = res.critical
            return (res.required_force, c.active_force, c.passive_force,
                    c.unsupported_fos, res.surfaces_analysed,
                    w.statusBar().currentMessage())
        import ogr_slip2d.analysis_runner as runner
        inline, threaded = _both(build_demo_project, self._run, read,
                                 runner, "run_configured_back_analysis")
        assert inline[0] == inline[0]          # a number, not NaN
        _same(threaded, inline)

    def test_a_refusal_on_the_thread_reaches_the_window(self):
        import ogr_slip2d.analysis_runner as runner
        from PySide6.QtWidgets import QDialog
        said = []

        def refuse(project, **kw):
            raise runner.AnalysisNotConfigured(["stop here"])
        w = _window(threaded=True)
        try:
            with _swap(runner, "run_configured_back_analysis", refuse), \
                    _swap(QDialog, "exec",
                          lambda self: QDialog.DialogCode.Accepted), \
                    _swap(w, "_info", lambda text, *a: said.append(text)):
                w._back_analysis()
            assert said == ["stop here"], said
            assert w.task_worker is None
        finally:
            _done(w)


# ======================================================================
class TestOptimisation:

    def test_the_same_surface_through_the_thread(self):
        import test_optimize_wiring_v1104 as ow
        from PySide6.QtWidgets import QInputDialog

        from ogr_slip2d.analysis_runner import build_search

        def run(w):
            sr = build_search(w.project, "bishop_simplified").run(w.project)
            w.last_search_results = {"bishop_simplified": sr}
            w.last_search_result = sr
            with _swap(QInputDialog, "getInt", staticmethod(
                    lambda *a, **k: (ow._MAX_ITERATIONS, True))), \
                    _swap(w, "_info", lambda *a: None):
                w._optimize_surfaces()

        def read(w):
            new = w.last_search_results["bishop_simplified"]
            opt = new.optimized
            assert opt is not None
            # the vertices: the surface's dictionary carries fresh ids
            return (opt.fos, opt.surface.to_dict()["polyline"]["vertices"],
                    len(new.evaluations),
                    w.statusBar().currentMessage())
        import ogr_slip2d.analysis_runner as runner
        inline, threaded = _both(ow._slope, run, read,
                                 runner, "run_configured_optimization")
        _same(threaded, inline)


# ======================================================================
class TestTheDialog:

    def test_it_does_not_close_before_the_calculation_returns(self):
        from ogr_gui.dialogs.misc_dialogs import TaskProgressDialog
        _app()
        d = TaskProgressDialog(None, "x")
        try:
            d.show()
            d.reject()
            assert not d.isHidden(), "Esc closed it with the thread running"
            d.close()
            assert not d.isHidden(), "the title bar closed it"
            assert d.btn_cancel.isHidden(), "a Cancel that cancels nothing"
            d.update_progress(3, 10)
            assert d.bar.value() == 30
            d.finish()
            assert d.isHidden()
        finally:
            d._finished = True
            d.close()

    def test_without_a_display_it_runs_inline(self):
        from ogr_gui.background import run_task, runs_inline
        w = _window()
        try:
            assert runs_inline(w)
            got = []
            assert run_task(w, lambda cb: got.append(cb) or 7) == 7
            assert got == [None]
            w._tasks_threaded = True
            assert not runs_inline(w)
        finally:
            _done(w)
