# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The window's progress dialog gets one signal per percent, not one per call.

WHAT INVARIANT THIS PROTECTS.

v0.1.386. ``run_task`` runs a calculation on its own thread and hands it
``_TaskWorker._progress`` as its progress callback, which emitted one queued
Qt signal per call. A Grid Search run in-process calls it once per centre,
and each signal is a Python slot on the window's thread that has to win the
GIL back from the calculation's. Measured by the review on a focused grid of
200 x 200 centres: the window froze for up to 7 s, and a Cancel pressed 20 s
in was read at 26 s, after the run had ended, so its result was published —
D362's contract is that a cancelled run publishes nothing. It already
happened with the parallel search switched off, on a machine of one to three
processors and when a pool failed; v0.1.386 also keeps in-process the focused
grids that leave fewer than 400 circles, bank 078 case 3b among them.

1. **At most one signal per percent of each (total, phase):** 101 for a run
   that goes from 0 to the end, however many calls it makes. The last one is
   the run's end, so the bar reaches 100 % and the label done = total.
2. **The stop flag is read on every call,** sent or not: a Cancel is
   honoured at the next call, as before.
3. **A new phase or a new total is always sent,** so the bar starting again
   over the optimisation, with the phase's name, is not swallowed.
4. **Through the real door:** ``run_task`` on its thread, with a calculation
   that calls back 1764 times (four methods of 441 centres, the size of bank
   078 case 3b), reaches the dialog 101 times and returns its result.

No number can move: the callback returns nothing to the calculation.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _worker():
    """A worker that is never started, and what its signal sends. Emitted
    on this thread, the signal reaches the recorder at once."""
    from ogr_gui.background import _TaskWorker
    _app()
    w = _TaskWorker(lambda cb: None)
    got = []
    w.progress.connect(lambda done, total, phase: got.append(
        (done, total, phase)))
    return w, got


# ======================================================================
class TestOneSignalPerPercent:
    """Invariants 1 to 3."""

    def test_a_run_of_442_calls_sends_101(self):
        w, got = _worker()
        for done in range(442):
            w._progress(done, 441)
        assert len(got) == 101
        assert [int(100 * d / t) for d, t, _ph in got] == list(range(101))
        assert got[0] == (0, 441, "")
        assert got[-1] == (441, 441, "")

    def test_the_stop_flag_is_read_on_every_call(self):
        import pytest
        from ogr_gui.background import TaskCancelled
        w, got = _worker()
        w._progress(5, 441)                       # 1 %: sent
        w.stop.set()
        with pytest.raises(TaskCancelled):
            w._progress(6, 441)                   # still 1 %: not sent, read
        assert len(got) == 1

    def test_a_new_phase_or_a_new_total_is_sent(self):
        from ogr_core.progress import OPTIMIZE, progress_phase
        w, got = _worker()
        w._progress(10, 100)                      # 10 %: sent
        w._progress(10, 100)                      # the same: not sent
        w._progress(20, 200)                      # 10 % of a new total: sent
        with progress_phase(OPTIMIZE):
            w._progress(20, 200)                  # 10 % of a new phase: sent
        assert got == [(10, 100, ""), (20, 200, ""), (20, 200, OPTIMIZE)]

    def test_a_run_without_a_total_is_sent_once(self):
        w, got = _worker()
        w._progress(0, 0)
        w._progress(0, 0)
        assert got == [(0, 0, "")]


# ======================================================================
class TestThroughTheRealDoor:
    """Invariant 4."""

    def test_run_task_on_its_thread(self):
        import ogr_gui.dialogs.misc_dialogs as md
        from PySide6.QtWidgets import QWidget
        from ogr_gui.background import run_task

        _app()
        window = QWidget()
        window._tasks_threaded = True
        calls = []
        real = md.TaskProgressDialog.__dict__["update_progress"]

        def spy(self, done, total, phase=""):
            calls.append((done, total))
            return real(self, done, total, phase)

        def calculation(cb):
            for done in range(1, 1765):
                cb(done, 1764)
            return "returned"

        md.TaskProgressDialog.update_progress = spy
        try:
            assert run_task(window, calculation) == "returned"
        finally:
            md.TaskProgressDialog.update_progress = real
            window.deleteLater()
        assert len(calls) == 101
        assert calls[-1] == (1764, 1764)
