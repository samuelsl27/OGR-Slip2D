# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
How the calculation processes are started (v0.1.329, D326).

On Windows a process with no console that starts ``python.exe`` children
gives each of them a console window of its own. The window started from a
shortcut or detached put three or four terminals in front of the program
when it computed, one of them maximised in the statistics, stealing the
focus (the third GUI test, H11). It is not the window's alone: the jobs of
the API start their worker with ``CREATE_NO_WINDOW`` (measured:
``GetConsoleWindow()`` is 0 in it), and an MCP server started by a desktop
client may have none either. ``pythonw.exe``, next to ``python.exe``, is the
same interpreter without a console, so the search points multiprocessing at
it just before it creates its pool, whoever started it.

With a console (a terminal, the test runner) the children share it and
nothing changes; neither on another system, nor in a frozen build, whose
workers start through the executable itself (``freeze_support``). The
numbers cannot move: the split of a search reproduces the sequential one bit
for bit (``tests/test_parallel_search_v197.py``).

v0.1.396 (V17 of the compute audit) -- and how a calculation that runs
several searches keeps ONE pool for all of them (:class:`pool_scope`).

v0.1.399 (D384) -- and how a pool's workers stop when the run is cancelled
(:func:`stoppable_pool`).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import os
import sys
import threading
from typing import Optional


class BatchStopped(BaseException):
    """A pool's worker stopped its batch because the run was cancelled
    (v0.1.399, D384). A ``BaseException``, as the window's ``TaskCancelled``
    is: the engine catches ``Exception`` around a surface it cannot
    evaluate, and a stop must not be counted as one more failed surface."""


#: In a pool's worker, the event its pool sets when the run is stopped
#: (v0.1.399, D384); None in every other process, so that a batch run in
#: this one (a test's executor) computes exactly as before.
_stop = None


def _install_stop(event) -> None:
    """The initializer of a :func:`stoppable_pool`: runs once in each
    worker process, as it starts."""
    global _stop
    _stop = event


def stop_check() -> None:
    """The watcher of a pool's worker (``ogr_core.progress.watching``):
    raises :class:`BatchStopped` once its pool's event is set."""
    if _stop is not None and _stop.is_set():
        raise BatchStopped()


def stoppable_pool(workers: int):
    """A process pool and the event that stops its batches, ``(pool,
    event)`` (v0.1.399, D384).

    The interface test of 0.1.397 measured a Cancel of a split grid at about
    34 s: the workers had no point at which to stop, so the run waited for
    every batch already handed to one, each 1/32 of a method's grid. Each
    worker now receives the event as it starts (an initializer, the only way
    a ``multiprocessing.Event`` reaches a pool's worker), and its batch
    checks it between grid centres (``search._grid_batch``). Whoever drops
    the pool sets the event first."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    windowless_children()
    stop = multiprocessing.Event()
    pool = ProcessPoolExecutor(max_workers=workers, initializer=_install_stop,
                               initargs=(stop,))
    return pool, stop


def child_executable(platform: Optional[str] = None,
                     executable: Optional[str] = None,
                     console: Optional[int] = None,
                     frozen: Optional[bool] = None) -> Optional[str]:
    """The interpreter the calculation processes should start with, or None
    to leave multiprocessing its own. The arguments are for the tests; by
    default they are read from this process."""
    platform = sys.platform if platform is None else platform
    if platform != "win32":
        return None
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        return None
    if console is None:
        import ctypes
        console = ctypes.windll.kernel32.GetConsoleWindow()
    if console:
        return None
    executable = sys.executable if executable is None else executable
    candidate = os.path.join(os.path.dirname(executable), "pythonw.exe")
    return candidate if os.path.isfile(candidate) else None


def windowless_children(**kwargs) -> Optional[str]:
    """Point multiprocessing at :func:`child_executable` when it names one,
    and return it; None when nothing changed. Cheap, and the same every
    time, so it is called before every pool rather than once at a start
    that some callers never go through."""
    exe = child_executable(**kwargs)
    if exe is not None:
        import multiprocessing
        multiprocessing.set_executable(exe)
    return exe


_local = threading.local()


class pool_scope:
    """``with pool_scope(): ...`` — the grid searches this thread runs
    while inside borrow one process pool, made by the first that splits
    and closed when the scope ends, however it ends (v0.1.396, V17 of the
    compute audit; the owner's decision: a scope per thread, in the
    pattern of ``ogr_core.progress``).

    Starting a pool of four workers costs about half a second, and every
    grid search started its own: a Compute with four methods paid it four
    times, a drawdown sweep once per level, Overall Slope once per sample.
    The calculations that run several searches — ``run_analysis``, the
    sweep's door, the statistics' door, ``run_transient_stability`` — open a
    scope; a scope opened inside another shares the outer one's pool, and
    only the outermost closes it. With no scope, which is every search a
    script, a test or the API runs on its own, a search makes and closes
    its pool as before. The workers of a borrowed pool stay alive and idle
    between searches, and between the stages of a transient while the
    seepage solver runs here (the owner accepted it).

    Nothing is cached in the pool: each search sends its project and its
    search with every batch, as before, so a borrowed pool computes what a
    new one would (``tests/test_shared_pool_v1396.py``)."""

    def __enter__(self):
        self._outer = getattr(_local, "scope", None)
        if self._outer is None:
            self._pool = None
            self._workers = None
            self._stop = None
            _local.scope = self
        return self

    def __exit__(self, *exc) -> bool:
        if self._outer is None:
            try:
                self.discard()
            finally:
                _local.scope = None
        return False

    def borrow(self, workers: int):
        """The pool, made now if there is none or it has another size
        (the size a search asks for depends only on the project's settings,
        so within one calculation it does not change)."""
        if self._pool is not None and self._workers != workers:
            self.discard()
        if self._pool is None:
            self._pool, self._stop = stoppable_pool(workers)
            self._workers = workers
        return self._pool

    def discard(self) -> None:
        """Close the pool, dropping what is queued and waiting for what
        runs. Idempotent: a stopped search and the scope's own end both
        come here, and so does a failed search before falling back.

        v0.1.399 (D384) — the pool's event is set first, so a batch that is
        running ends at its next grid centre instead of being waited for to
        its end. At the scope's own end no batch runs, and it changes
        nothing."""
        pool, stop = self._pool, self._stop
        self._pool, self._workers, self._stop = None, None, None
        if pool is not None:
            stop.set()
            pool.shutdown(wait=True, cancel_futures=True)


def current_pool_scope() -> Optional[pool_scope]:
    """The outermost :class:`pool_scope` open on this thread, or None."""
    return getattr(_local, "scope", None)


def pooled(fn):
    """Run ``fn`` inside a :class:`pool_scope` (v0.1.396, V17): the mark of
    a calculation that runs several searches. Name, docstring and signature
    are ``fn``'s."""
    import functools

    @functools.wraps(fn)
    def run_pooled(*args, **kwargs):
        with pool_scope():
            return fn(*args, **kwargs)
    return run_pooled
