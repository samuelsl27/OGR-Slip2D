# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Long calculations off the window's thread (v0.1.365, D348).

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
with a modal progress dialog in front, the way *Compute* waits in its
dialog's ``exec()``. The modal dialog is what keeps the model still: the user
cannot edit it while it is being read on another thread.

Without a display (the tests, which build real windows on the "offscreen"
platform, and the bank's checks) the calculation runs inline, as it always
did: the fifty-odd tests that call these handlers and read the result on the
next line keep working unchanged, and a modal dialog is never opened where
nobody can close it. ``window._tasks_threaded = True`` forces the thread, for
the tests of this module.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QEventLoop, QThread, Signal
from PySide6.QtWidgets import QApplication


class _TaskWorker(QThread):
    """Runs ``fn(progress_cb)`` and keeps what it returned or raised."""

    progress = Signal(int, int)

    def __init__(self, fn: Callable) -> None:
        super().__init__()
        self._fn = fn
        self.result = None
        self.error: Optional[BaseException] = None

    def run(self) -> None:                       # noqa: D102
        try:
            self.result = self._fn(self._progress)
        except BaseException as exc:  # noqa: BLE001 - raised again in the window
            self.error = exc

    def _progress(self, done, total) -> None:
        self.progress.emit(int(done), int(total))


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
    its exception raised again here.

    ``progress_cb`` is ``(done, total)`` for the progress dialog, or None
    when the calculation runs inline — which is the call the window made
    before, argument for argument. While it runs, ``window.task_worker`` is
    the thread, so the agent's bridge answers Busy to an edit.
    """
    if runs_inline(window):
        return fn(None)
    from ogr_gui.dialogs.misc_dialogs import TaskProgressDialog

    worker = _TaskWorker(fn)
    prog = TaskProgressDialog(window, title)
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
        worker.wait()
    finally:
        prog.finish()
        window.task_worker = None
    if worker.error is not None:
        raise worker.error
    return worker.result
