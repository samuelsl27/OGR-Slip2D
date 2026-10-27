# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.372 (D368) — cancelling a grid split over processes drops its queue,
whatever the pool's manager thread is doing at that moment.

The finding. D362 (0.1.366) made Cancel stop a parallel grid with
``pool.shutdown(wait=False, cancel_futures=True)`` inside the
``with ProcessPoolExecutor(...)`` block. That call only leaves a flag for
the pool's manager thread and forgets the thread; the ``with`` exit that
follows calls ``shutdown(wait=True)``, which sets the flag back to False and
has no thread left to wait for (CPython's ``ProcessPoolExecutor.shutdown``).
When the exit got there before the manager thread read the flag, nothing was
cancelled and the workers ran the rest of the grid in the background, and the
process could not exit until they finished. ``test_cancel_v1366`` passed in
six full suites and failed three times out of three with another suite
loading the machine, eight workers alive after 30 s.

What these tests protect, with the race FORCED: the manager thread waits a
little each time it is about to act on a shutdown, which is what a loaded
machine did by chance. With the code of 0.1.366–0.1.371 the outcome is then
always the bad one.

* every batch not yet handed to a worker is cancelled: at most the ones
  running and the ones the pool keeps queued for its workers are run;
* when ``run`` returns, no worker is left: the cancel waits for the batches
  running, and only for them.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

#: How long the manager thread is held back before it acts on a shutdown.
_DELAY = 0.3


def _cancel_with_a_late_manager():
    """``(futures, run, workers_left, max_workers)`` of a grid cancelled at
    its first finished batch, the manager thread held back."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    from concurrent.futures import process as pool_module

    import pytest
    import test_window_grid_parallel_v1262 as gp
    from test_cancel_v1366 import _swap

    from ogr_slip2d.analysis_runner import build_search
    p = gp._model()
    gp._needs_a_pool(p)
    futures, sizes = [], []
    real_submit = ProcessPoolExecutor.submit
    manager = pool_module._ExecutorManagerThread
    real_flag = manager.flag_executor_shutting_down

    def submit(self, fn, /, *args, **kwargs):
        sizes.append(self._max_workers)
        future = real_submit(self, fn, *args, **kwargs)
        futures.append(future)
        return future

    def late_flag(self):
        time.sleep(_DELAY)
        return real_flag(self)

    class Stop(BaseException):
        pass

    def stop(_done, _total):
        raise Stop()
    search = build_search(p, "bishop_simplified", progress_cb=stop)
    try:
        with _swap(ProcessPoolExecutor, "submit", submit), \
                _swap(manager, "flag_executor_shutting_down", late_flag):
            with pytest.raises(Stop):
                search.run(p)
            left = multiprocessing.active_children()
            run = [f for f in futures if not f.cancelled()]
    finally:
        # the tree before this version leaves the grid running: let it end
        # here rather than in the next test, or at exit
        end = time.time() + 300
        while multiprocessing.active_children() and time.time() < end:
            time.sleep(0.2)
    assert futures and len(set(sizes)) == 1, sizes
    return futures, run, left, sizes[0]


class TestCancelDropsTheQueueWhateverTheManagerDoes:

    def test_only_the_batches_handed_out_are_run(self):
        futures, run, _left, workers = _cancel_with_a_late_manager()
        # running (one per worker) + queued for them (one per worker plus
        # one) + those finished by the time the cancel arrives
        assert len(run) <= 3 * workers + 2, (len(run), len(futures), workers)
        assert len(run) < len(futures), (len(run), len(futures))

    def test_no_worker_is_left_when_run_returns(self):
        _futures, _run, left, _workers = _cancel_with_a_late_manager()
        assert not left, [c.name for c in left]
