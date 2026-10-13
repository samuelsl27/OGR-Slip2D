# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Cyclic garbage found on a worker thread is released on the main thread.

v0.1.302 (D310). Python's cyclic collector runs on whichever thread happens
to allocate when a threshold trips: the compute thread, a process pool's
feeder and manager threads, any other. When the garbage it finds holds Qt
objects, shiboken cannot delete them from that thread, so it queues their
deletion for the main thread (``BindingManager::runDeletionInMainThread``,
run as a Python pending call). Measured in the test suite, that deferred
deletion aborted the process: the native stack of the abort is
``Py_HandlePending -> runDeletionInMainThread -> QObject::~QObject ->
purecall -> abort``, with no message from Qt or Python, about one run in
two, when a grid opened its process pool after earlier tests had left
matplotlib canvases and settings widgets as cyclic garbage.

The guard keeps every collection that starts off the main thread from
freeing anything (``gc.DEBUG_SAVEALL`` for that collection only) and holds
what it found until :func:`release`, called on the main thread, lets a
main-thread collection free it — where Qt objects are deleted directly, in
the order the collector chooses, with no deferral. The window calls
:func:`release` from a timer; the test runner after every test file.

Nothing here imports Qt: the runner installs the guard before any test.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import gc
import threading

_kept: list = []
_lock = threading.Lock()
#: The debug flags in force before the collection that set DEBUG_SAVEALL,
#: per collection (a collection never nests inside another).
_saved_flags: list = []


def _callback(phase: str, info: dict) -> None:
    if threading.current_thread() is threading.main_thread():
        return
    if phase == "start":
        flags = gc.get_debug()
        _saved_flags.append(flags)
        gc.set_debug(flags | gc.DEBUG_SAVEALL)
        return
    gc.set_debug(_saved_flags.pop() if _saved_flags else 0)
    if gc.garbage:
        with _lock:
            _kept.append(list(gc.garbage))
        del gc.garbage[:]


def install() -> None:
    """Install the guard (once per process)."""
    if _callback not in gc.callbacks:
        gc.callbacks.append(_callback)


def uninstall() -> None:
    """Remove the guard and release what it holds (for tests: rule 5)."""
    while _callback in gc.callbacks:
        gc.callbacks.remove(_callback)
    release()


def installed() -> bool:
    return _callback in gc.callbacks


def kept() -> int:
    """How many objects the guard is holding for the main thread."""
    with _lock:
        return sum(len(batch) for batch in _kept)


def release() -> int:
    """On the MAIN thread: let a collection here free what worker-thread
    collections found. Returns how many objects were held. Called
    anywhere else, it does nothing."""
    if threading.current_thread() is not threading.main_thread():
        return 0
    with _lock:
        batches = _kept[:]
        del _kept[:]
    n = sum(len(batch) for batch in batches)
    if n:
        del batches
        gc.collect()
    return n
