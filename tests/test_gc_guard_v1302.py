# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.302 (D310) — Qt objects found as garbage on a worker thread are freed
on the main thread.

The defect: the whole suite aborted about one run in two (exit 127 in Git
Bash = 0xC0000409, abort), always when ``test_a_shared_seed_is_denounced``
opened the process pool of a 441-circle grid. The native stack, taken with a
C-level SIGABRT handler: ``Py_HandlePending -> shiboken6
BindingManager::runDeletionInMainThread -> QObject::~QObject -> purecall ->
abort``. The cyclic collector had run on one of the pool's threads, found
Qt objects earlier tests left as cyclic garbage (matplotlib canvases,
settings widgets), and shiboken, which cannot delete them off the main
thread, queued their deletion as a pending call; the main thread ran it
and aborted. The same can happen in the program: the compute thread runs
Python, and a chart window the user closed can be cyclic garbage.

``ogr_gui.gc_guard`` keeps a collection that starts off the main thread from
freeing anything and holds what it found until ``release()`` lets a
collection on the main thread free it. What these tests protect:

* with the guard, a dialog in a reference cycle, collected on a worker
  thread, is NOT destroyed — not even after the main thread has run Python
  (when shiboken's pending calls run) — until ``release()``, and then on
  the main thread;
* the window's release timer, run by the event loop, does that release:
  found in the full suite, where a window left alive by an earlier test
  freed the dialog the first version of these tests expected to stay;
* without it (the control), the worker's collection destroys the dialog
  on the worker thread itself, which Qt forbids for a widget (measured
  while writing this: the spy counts the destruction before the main
  thread does anything). The deferred deletion in the abort's stack is
  the other way shiboken handles it; the guard keeps both from happening;
* ``release()`` off the main thread does nothing;
* the window installs the guard and releases from a timer; the test runner
  installs it and releases before every test file.

The abort itself could not be reproduced on demand (six synthetic
attempts: memory ballast, 300 leaked windows, the files that leave Qt
garbage collected on a thread); the clean runs of the suite are in the
changelog.
"""
from __future__ import annotations

import gc
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QObject, Slot  # noqa: E402
from PySide6.QtTest import QSignalSpy  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

_RUNNER = Path(__file__).resolve().parent / "_runner.py"


class _CyclicDialog(QDialog):
    pass


class _Watcher(QObject):
    """Lives on: records the thread its slot runs on. A slot of a living
    receiver runs directly when the signal is emitted on the receiver's
    thread, and is QUEUED when it is emitted on another one."""

    def __init__(self):
        super().__init__()
        self.threads = []

    @Slot()
    def hit(self):
        self.threads.append(threading.current_thread().name)


def _garbage_dialog(watcher):
    """A Python-owned dialog that only the cyclic collector can free; a spy
    counts its destruction (``destroyed`` is emitted by ~QObject)."""
    QApplication.instance() or QApplication([])
    d = _CyclicDialog()
    d.me = d
    d.destroyed.connect(watcher.hit)
    spy = QSignalSpy(d.destroyed)
    del d
    return spy


def _collect_on_a_worker():
    t = threading.Thread(target=gc.collect, name="worker")
    t.start()
    t.join()


def _main_thread_runs_python():
    """What gives queued Python pending calls (shiboken's deferred
    deletions) their turn: the main thread running bytecode."""
    for i in range(200000):
        _ = [i]


class TestTheGuard:
    def test_worker_garbage_waits_for_the_main_thread(self):
        from ogr_gui import gc_guard
        was_on, was_installed = gc.isenabled(), gc_guard.installed()
        gc_guard.install()
        gc.disable()                # no collection on the main thread
        watcher = _Watcher()
        try:
            spy = _garbage_dialog(watcher)
            _collect_on_a_worker()
            # No events processed here: a window left alive by an earlier
            # test has its release timer, which would free it (rightly, on
            # this thread) before release() is called.
            _main_thread_runs_python()
            assert spy.count() == 0, "destroyed before the main thread let it"
            assert gc_guard.kept() > 0
            gc_guard.release()
            assert spy.count() == 1
            # destroyed on the main thread: the slot ran at once, directly
            assert watcher.threads == ["MainThread"], watcher.threads
            assert gc_guard.kept() == 0
        finally:
            if was_on:
                gc.enable()
            if not was_installed:
                gc_guard.uninstall()

    def test_the_windows_timer_frees_it_on_the_main_thread(self):
        """What the window relies on: its release timer, run by the event
        loop, lets the main thread free what a worker found."""
        import time

        from ogr_gui import gc_guard
        from ogr_gui.main_window import MainWindow
        was_on, was_installed = gc.isenabled(), gc_guard.installed()
        QApplication.instance() or QApplication([])
        w = MainWindow()
        gc.disable()
        watcher = _Watcher()
        try:
            spy = _garbage_dialog(watcher)
            _collect_on_a_worker()
            assert spy.count() == 0 and gc_guard.kept() > 0
            deadline = time.monotonic() + 10.0
            while spy.count() == 0 and time.monotonic() < deadline:
                QApplication.processEvents()
                time.sleep(0.05)
            assert spy.count() == 1, "the timer never released it"
            assert watcher.threads == ["MainThread"], watcher.threads
        finally:
            if was_on:
                gc.enable()
            w.project.is_dirty = False
            w.close()
            if not was_installed:
                gc_guard.uninstall()

    def test_without_it_the_worker_destroys_it(self):
        """The control: without the guard the worker thread's collection
        destroys the dialog THERE (Qt forbids destroying a widget off the
        GUI thread), and the receiver on the main thread only hears of it
        through a queued call."""
        from ogr_gui import gc_guard
        was_on, was_installed = gc.isenabled(), gc_guard.installed()
        gc_guard.release()
        while gc_guard._callback in gc.callbacks:
            gc.callbacks.remove(gc_guard._callback)
        gc.disable()
        watcher = _Watcher()
        try:
            spy = _garbage_dialog(watcher)
            _collect_on_a_worker()
            assert spy.count() == 1          # already destroyed...
            assert watcher.threads == []     # ...somewhere else: queued
            QApplication.processEvents()
            assert watcher.threads == ["MainThread"]
            assert gc_guard.kept() == 0
        finally:
            if was_on:
                gc.enable()
            if was_installed:
                gc_guard.install()

    def test_release_off_the_main_thread_does_nothing(self):
        from ogr_gui import gc_guard
        was_on, was_installed = gc.isenabled(), gc_guard.installed()
        gc_guard.install()
        gc.disable()
        watcher = _Watcher()
        try:
            spy = _garbage_dialog(watcher)
            _collect_on_a_worker()
            held = gc_guard.kept()
            assert held > 0
            out = []
            t = threading.Thread(target=lambda: out.append(
                gc_guard.release()))
            t.start()
            t.join()
            assert out == [0] and gc_guard.kept() == held
            assert spy.count() == 0
            gc_guard.release()
            assert spy.count() == 1
        finally:
            if was_on:
                gc.enable()
            if not was_installed:
                gc_guard.uninstall()


class TestWhoInstallsIt:
    def test_the_window_installs_it_and_releases_from_a_timer(self):
        from ogr_gui import gc_guard
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        was_installed = gc_guard.installed()
        gc_guard.uninstall()
        try:
            w = MainWindow()
            try:
                assert gc_guard.installed()
                assert w._gc_release_timer.isActive()
                assert w._gc_release_timer.interval() == 2000
            finally:
                w.close()
        finally:
            if not was_installed:
                gc_guard.uninstall()

    def test_the_runner_installs_it_and_releases_before_every_file(self):
        from ogr_gui import gc_guard
        # this test runs under the runner
        assert gc_guard.installed()
        src = _RUNNER.read_text(encoding="utf-8")
        loop = src[src.index("for i_file, f in enumerate(test_files, 1):"):]
        loop = loop[:loop.index('print(f"\\n=== {f.name}')]
        assert "gc_guard.release()" in loop and "gc.collect()" in loop
