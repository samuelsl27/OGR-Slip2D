# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Long calculations off the window's thread (v0.1.365, D348), and stopped when
the user cancels them (v0.1.366, D362).

*Compute* has run on its own thread since its first version, and the
drawdown sweep since v0.1.70, whose comment already said why: on a real model
a calculation on the window's thread leaves the window "simply not
responding for minutes". Compute Statistics, Compute Groundwater (steady and
transient), the back analysis and Optimize Surfaces still ran there. The
fifth interface test (0.1.355) measured it: a two-stage transient with
factors held the window for about seven minutes and the statistics for about
forty seconds, while Windows painted a dark window over it and the agent's
calls timed out.

:func:`run_task` keeps the handlers as they were — it RETURNS the result, so
the code after the calculation, the undo step around it included, reads
exactly as before — and keeps the window's event loop running meanwhile: the
calculation runs on a ``QThread`` and the window waits in a local event loop
with a modal progress dialog in front. The modal dialog is what keeps the
model still: the user cannot edit it while it is being read on another
thread.

**Cancel (v0.1.366, D362).** *Compute*'s Cancel closed its dialog and set a
flag nobody read: the thread went on, published its result over a model the
user could by then have edited, and a second Compute started on top of it
aborted the process when the first thread lost its last reference. Now the
button asks the calculation to stop, the dialog says "Cancelling…" and
stays until the thread has returned, and :class:`TaskCancelled` reaches the
handler, which publishes nothing. The stop is raised from the progress
callback the calculation already calls, and from the checkpoints of
``ogr_core.progress`` in the loops that have none: no signature of the
engine changes, and a run that is not cancelled computes what it always did.

Without a display (the tests, which build real windows on the "offscreen"
platform, and the bank's checks) the calculation runs inline, as it always
did: the fifty-odd tests that call these handlers and read the result on the
next line keep working unchanged, and a modal dialog is never opened where
nobody can close it. ``window._tasks_threaded = True`` forces the thread, for
the tests of this module.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from PySide6.QtCore import QEventLoop, QThread, Signal
from PySide6.QtWidgets import QApplication


class TaskCancelled(BaseException):
    """The user cancelled the calculation (v0.1.366, D362).

    A ``BaseException`` on purpose, as ``KeyboardInterrupt`` is: the engine
    catches ``Exception`` around a surface it cannot evaluate, a search that
    fails, a pool that cannot start — and a stop must go through all of
    them, not be counted as one more failed surface."""


class _TaskWorker(QThread):
    """Runs ``fn(progress_cb)`` and keeps what it returned or raised."""

    progress = Signal(int, int, str)

    def __init__(self, fn: Callable) -> None:
        super().__init__()
        self._fn = fn
        self.result = None
        self.error: Optional[BaseException] = None
        #: Set by the window's Cancel; read by the calculation's thread.
        self.stop = threading.Event()
        #: The (percent, total, phase) the dialog was last sent.
        self._last_sent = None

    def run(self) -> None:                       # noqa: D102
        from ogr_core.progress import watching
        try:
            with watching(self._check):
                self.result = self._fn(self._progress)
        except BaseException as exc:  # noqa: BLE001 - raised again in the window
            self.error = exc

    def _check(self) -> None:
        if self.stop.is_set():
            raise TaskCancelled()

    def _progress(self, done, total) -> None:
        self._check()
        from ogr_core.progress import phase
        now = phase() or ""
        # v0.1.386 — one signal per percent, not one per call. A Grid Search
        # run in-process calls back once per centre, and every signal queues
        # a Python slot on the window's thread, which has to win the GIL back
        # from this one: on a focused grid of 200 x 200 centres the window
        # froze for up to 7 s, and a Cancel was read after the run had ended,
        # so its result was published. The dialog shows a percentage, and a
        # done/total nobody reads at that rate; the stop flag above is still
        # read on every call.
        sent = (int(100 * done / total) if total > 0 else None,
                int(total), now)
        if sent == self._last_sent:
            return
        self._last_sent = sent
        self.progress.emit(int(done), int(total), now)


def runs_inline(window) -> bool:
    """Whether ``window`` computes on its own thread: without a display,
    unless ``window._tasks_threaded`` says otherwise."""
    forced = getattr(window, "_tasks_threaded", None)
    if forced is not None:
        return not forced
    app = QApplication.instance()
    return app is None or app.platformName() == "offscreen"


def run_task(window, fn: Callable, title: str = ""):
    """``fn(progress_cb)``, computed off the window's thread; its result, or
    its exception raised again here — :class:`TaskCancelled` when the user
    cancelled it.

    ``progress_cb`` is ``(done, total)`` for the progress dialog, or None
    when the calculation runs inline — which is the call the window made
    before, argument for argument. While it runs, ``window.task_worker`` is
    the thread, so the agent's bridge answers Busy to an edit.
    """
    if runs_inline(window):
        return fn(None)
    from ogr_gui.dialogs.misc_dialogs import TaskProgressDialog

    worker = _TaskWorker(fn)
    prog = TaskProgressDialog(window, title, on_cancel=worker.stop.set)
    worker.progress.connect(prog.update_progress)
    loop = QEventLoop()
    # Queued to this thread: the loop quits when the calculation has
    # returned, whatever it returned, and a signal emitted before exec()
    # waits for it.
    worker.finished.connect(loop.quit)
    window.task_worker = worker
    try:
        worker.start()
        prog.show()
        loop.exec()
        # The thread keeps its last reference until it has returned: a
        # QThread destroyed while it runs aborts the process (D362).
        worker.wait()
    finally:
        prog.finish()
        window.task_worker = None
    if worker.error is not None:
        raise worker.error
    return worker.result
