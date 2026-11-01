# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.399 (D384) — Cancel stops a grid split across processes within about a
second, not when the batches already handed out have finished.

WHAT INVARIANT THIS PROTECTS.

The interface test of 0.1.397 (FALLO 2) measured a Cancel of a split grid at
~34 s: the workers stayed alive and the window grew 700 MB meanwhile. The
code had two waits (D384):

* the parent waited in ``as_completed`` with no limit, so the stop was read
  only in the callback after the next batch had finished;
* then it waited for every batch already handed to a worker (D362/D368),
  and the workers had no point at which to stop: each batch, 1/32 of a
  method's grid, ran to its end.

Measured with ``_auditoria/P8_interfaz/d384_latencia_cancelar.py`` on K03 of
the compute bench (51 x 51 x 12, Bishop and Janbu corrected, with the pool),
one run per process. Asked at 15, 25 and 35 s, 0.1.397 stopped 9.8, 11.6 and
12.3 s later; this version stopped 0.7, 1.4 and 1.4 s later.

1. **The parent reads the stop while it waits** (``_run_batches``): with a
   batch that never finishes, a watcher's stop comes through the wait, the
   batch is cancelled and the pool dropped.
2. **A worker's batch stops between centres** (``_grid_batch``, in a process
   where a pool installed its event). Set before the batch, no centre is
   evaluated; set after k centres, exactly the circles of those k are.
3. **Whoever drops a pool sets its event first,** both the pool a search
   makes for itself and the one a scope lends (``pool_scope.discard``).
4. **Outside a pool's worker nothing changes:** with no event installed a
   batch runs whole and gives the evaluations of the sequential run.

No clock decides anything. The fail-safe timer of (1) finishes the batch
only if the stop never comes, so that the old tree fails instead of hanging.
"""
from __future__ import annotations

import contextlib
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MISSING = object()


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = getattr(owner, name, _MISSING)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


class _Stop(BaseException):
    """What the window's Cancel raises: not an ``Exception``."""


def _stop_at_first_checkpoint():
    calls = []

    def check():
        calls.append(1)
        raise _Stop()
    return check, calls


def _grid(nx=4, ri=2):
    from ogr_core.project.demo import build_demo_project
    from ogr_slip2d.analysis_runner import build_search
    p = build_demo_project()
    s = p.settings.search
    s.grid_nx = s.grid_ny = nx
    s.radius_increment = ri
    search = build_search(p, "bishop_simplified")
    search.progress_cb = None
    return p, search, search._centres(p)


def _record_circles(search):
    """``evaluate_circle`` replaced by a recorder (on this instance only)."""
    seen = []
    search.evaluate_circle = lambda _p, c: seen.append(
        (c.centre_x, c.centre_y)) or None
    return seen


class _Recorder:
    """A process pool that runs nothing and records, at each shutdown,
    whether the stop event it was made with was set."""

    made: list = []

    def __init__(self, max_workers=None, initializer=None, initargs=()):
        self.stop = initargs[0] if initargs else None
        self.seen = []
        self.futures = []
        _Recorder.made.append(self)

    def submit(self, fn, *args):
        from concurrent.futures import Future
        f = Future()
        self.futures.append(f)
        return f

    def shutdown(self, wait=True, cancel_futures=False):
        self.seen.append(None if self.stop is None else self.stop.is_set())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.shutdown(wait=True)
        return False


# ======================================================================
class TestTheParentReadsTheStopWhileItWaits:
    """Invariant 1."""

    def test_a_batch_that_never_finishes(self):
        from concurrent.futures import Future
        from ogr_core.progress import watching
        import ogr_slip2d.search as S

        class Pool:
            def __init__(self):
                self.futures = []

            def submit(self, fn, *args):
                f = Future()
                self.futures.append(f)
                return f

        pool, dropped = Pool(), []
        check, calls = _stop_at_first_checkpoint()
        payloads = [(None, None, [(0.0, 0.0)], 0, 1)]

        def finish():          # fail-safe: only if the stop never comes
            for f in pool.futures:
                if not f.done():
                    f.set_result(None)
        fail_safe = threading.Timer(5.0, finish)
        fail_safe.start()
        try:
            with _swap(S, "_STOP_POLL_S", 0.01), watching(check):
                try:
                    S._run_batches(pool, payloads, 1, None, {"cb_error": None},
                                   lambda: dropped.append(True))
                except _Stop:
                    stopped = True
                else:
                    stopped = False
        finally:
            fail_safe.cancel()
        assert stopped, "the stop did not come through the wait"
        assert calls == [1]
        assert pool.futures[0].cancelled(), "the batch was not cancelled"
        assert dropped == [True], "the pool was not dropped"


class TestAWorkersBatchStopsBetweenCentres:
    """Invariant 2."""

    def test_set_before_the_batch_no_centre_is_evaluated(self):
        import threading as _t
        import ogr_slip2d.processes as P
        from ogr_slip2d.search import _grid_batch
        p, search, centres = _grid()
        seen = _record_circles(search)
        ev = _t.Event()
        ev.set()
        with _swap(P, "_stop", ev):
            try:
                _grid_batch((search, p, centres, 0, len(centres)))
            except P.BatchStopped:
                stopped = True
            else:
                stopped = False
        assert stopped, "the batch ran to its end"
        assert seen == [], "%d circles were evaluated" % len(seen)

    def test_set_after_k_centres_exactly_their_circles(self):
        import ogr_slip2d.processes as P
        from ogr_slip2d.search import _grid_batch
        p, search, centres = _grid()
        k = 7
        full = _record_circles(search)
        search._run_centres(p, centres, 0, len(centres))
        expected = [c for c in full if c in set(centres[:k])]
        assert expected and len(expected) < len(full)

        class AfterK:
            def __init__(self):
                self.calls = 0

            def is_set(self):
                self.calls += 1
                return self.calls > k

        p, search, centres = _grid()
        seen = _record_circles(search)
        ev = AfterK()
        with _swap(P, "_stop", ev):
            try:
                _grid_batch((search, p, centres, 0, len(centres)))
            except P.BatchStopped:
                pass
            else:
                raise AssertionError("the batch ran to its end")
        assert seen == expected
        assert ev.calls == k + 1, "one check per centre"


class TestWhoeverDropsAPoolSetsItsEventFirst:
    """Invariant 3."""

    def test_the_pool_a_search_makes_for_itself(self):
        import concurrent.futures as cf
        from ogr_core.progress import watching
        import ogr_slip2d.search as S
        from ogr_slip2d.processes import current_pool_scope
        assert current_pool_scope() is None
        p, search, centres = _grid()
        _Recorder.made = []
        check, _calls = _stop_at_first_checkpoint()

        def finish():          # fail-safe: only if the stop never comes
            for pool in _Recorder.made:
                for f in pool.futures:
                    if not f.done():
                        f.set_result(None)
        fail_safe = threading.Timer(5.0, finish)
        fail_safe.start()
        try:
            with _swap(cf, "ProcessPoolExecutor", _Recorder), \
                    _swap(S, "_STOP_POLL_S", 0.01), watching(check):
                try:
                    S._parallel_grid_run(search, p, centres, 2)
                except _Stop:
                    pass
                else:
                    raise AssertionError("the stop did not reach the caller")
        finally:
            fail_safe.cancel()
        assert len(_Recorder.made) == 1
        seen = _Recorder.made[0].seen
        assert seen and seen[0] is True, (
            "the pool was shut down before its event was set: %r" % seen)

    def test_the_pool_a_scope_lends(self):
        import concurrent.futures as cf
        from ogr_slip2d.processes import pool_scope
        _Recorder.made = []
        with _swap(cf, "ProcessPoolExecutor", _Recorder):
            with pool_scope() as scope:
                scope.borrow(2)
                scope.discard()
                scope.discard()            # idempotent
        assert len(_Recorder.made) == 1
        assert _Recorder.made[0].seen == [True]


class TestOutsideAWorkerNothingChanges:
    """Invariant 4."""

    def test_a_batch_without_an_event_is_the_sequential_run(self):
        import ogr_slip2d.processes as P
        from ogr_slip2d.search import _grid_batch
        assert P._stop is None
        p, search, centres = _grid(nx=2, ri=1)
        ref = search._run_centres(p, centres, 0, len(centres))
        p, search, centres = _grid(nx=2, ri=1)
        part = _grid_batch((search, p, centres, 0, len(centres)))

        def key(res):
            return [(e.fos.hex() if e.fos is not None else None, e.is_valid)
                    for e in res.evaluations]
        assert key(part) == key(ref)
        assert len(part.evaluations) == len(ref.evaluations) > 0
