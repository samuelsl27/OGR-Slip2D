# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.398 (D382) — a calculation run through ``ogr_gui.background.run_task``
leaves nothing of itself alive once its exception has been handled or its
result dropped.

The finding (the interface test of 0.1.397, FALLO 1; measured with
``_auditoria/P8_interfaz/d382_cancel_retiene.py``): Cancel a big Compute and
the window stayed at 3.3 GB with nothing on screen. ``_TaskWorker`` kept the
exception; its traceback held the frame of ``run`` (whose ``self`` is the
worker) and of ``run_task`` (which held the worker), and the frames of the
calculation it carries held what had been computed. That is a cycle, which
only the cyclic collector frees, and an idle window never runs a full
collection. On 0.1.397, 1002 LEMResult were alive after the ``except``; with
the cycle broken, none.

What these tests protect. Automatic collection is off between the
calculation and the check, so that no collection frees a cycle behind the
test's back, and is restored afterwards:

* a cancelled calculation: what its frames held is gone once the handler has
  run. This is checked with a marker object, and with a real Compute
  cancelled in its second method, which leaves no LEMResult behind;
* a failed one, the same, and its message is unchanged;
* a successful one still returns its result, and nothing else keeps it.
"""
from __future__ import annotations

import gc
import sys
import weakref
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _parent():
    """A plain widget for the progress dialog, with the thread forced on
    (without a display ``run_task`` runs inline)."""
    from PySide6.QtWidgets import QWidget
    _app()
    w = QWidget()
    w._tasks_threaded = True
    return w


class _Marker:
    """Something a calculation computed (weakly referenceable)."""


@contextmanager
def _collector_off():
    was = gc.isenabled()
    gc.collect()
    gc.disable()
    try:
        yield
    finally:
        if was:
            gc.enable()


def _alive(cls) -> int:
    return sum(1 for o in gc.get_objects() if type(o) is cls)


class TestNothingOutlivesItsTask:

    def test_a_cancelled_task(self):
        from ogr_gui.background import TaskCancelled, run_task
        w = _parent()
        refs = []

        def fn(cb):
            computed = _Marker()
            refs.append(weakref.ref(computed))
            w.task_worker.stop.set()
            cb(1, 2)            # the window's check raises here
            return computed

        with _collector_off():
            try:
                run_task(w, fn, "Compute")
            except TaskCancelled:
                pass
            else:
                raise AssertionError("the task was not cancelled")
            assert w.task_worker is None
            assert refs[0]() is None, (
                "what the cancelled calculation computed is still alive")

    def test_a_failed_task(self):
        from ogr_gui.background import run_task
        w = _parent()
        refs = []

        def fn(cb):
            computed = _Marker()
            refs.append(weakref.ref(computed))
            raise ValueError("bad model")

        with _collector_off():
            try:
                run_task(w, fn, "Compute")
            except ValueError as exc:
                assert str(exc) == "bad model"
            else:
                raise AssertionError("the failure did not reach the caller")
            assert refs[0]() is None, (
                "what the failed calculation computed is still alive")

    def test_a_successful_task(self):
        from ogr_gui.background import run_task
        w = _parent()
        refs = []

        def fn(cb):
            computed = _Marker()
            refs.append(weakref.ref(computed))
            return computed

        with _collector_off():
            got = run_task(w, fn, "Compute")
            assert refs[0]() is got
            del got
            assert refs[0]() is None, "something kept the returned result"

    def test_a_compute_cancelled_in_its_second_method(self):
        """The case of the interface test, small: the first method's
        evaluations are in the frames of ``run_analysis`` when the stop
        comes."""
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.background import TaskCancelled, run_task
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.methods.base import LEMResult
        p = build_demo_project()
        s = p.settings.search
        s.grid_nx = s.grid_ny = 2           # 9 centres
        s.radius_increment = 2              # 3 radii each
        p.settings.advanced.parallel_search = False
        methods = ["bishop_simplified", "janbu_simplified"]
        w = _parent()
        calls = [0]

        def fn(cb):
            def counted(done, total):
                calls[0] += 1
                if calls[0] == 12:          # 9 centres per method
                    w.task_worker.stop.set()
                cb(done, total)
            return run_analysis(p, methods, progress_cb=counted)

        with _collector_off():
            before = _alive(LEMResult)
            try:
                run_task(w, fn, "Compute")
            except TaskCancelled:
                pass
            else:
                raise AssertionError("the Compute was not cancelled")
            assert calls[0] == 12
            left = _alive(LEMResult) - before
            assert left == 0, (
                "%d surface results of the cancelled Compute are alive" % left)
