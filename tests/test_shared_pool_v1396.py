# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A calculation that runs several searches lends them one process pool.

WHAT INVARIANT THIS PROTECTS.

V17 of the compute audit (v0.1.396). Starting a pool of four workers costs
about half a second, and every grid search started its own: a Compute with
four methods paid it four times (bank 001 at 7 x 7 x 11: 4 pools in 4.3 s),
a drawdown sweep once per level, Overall Slope once per sample (bank 036:
8 pools). Now ``run_analysis``, the sweep's and the statistics' doors and
``run_transient_stability`` open a ``processes.pool_scope`` (the owner's
decisions: a scope per thread, those four, idle workers accepted), and the
grid searches inside borrow its pool. With no scope a search makes and
closes its own, as before. Class A: the same batches to the same function.

The pools here are an executor that runs each batch at once, in this
process, on a pickled copy of what a worker would receive, and hands back a
pickled copy of its part: what a process pool does, without the processes,
counted.

1. **The same evaluations, one pool:** a Compute with two methods gives,
   evaluation for evaluation, what it gave with a pool per method (that a
   split grid is the sequential one is test_parallel_search_v197's); one
   pool is made instead of two, and it is closed when the Compute
   returns.
2. **Scopes:** a nested scope shares the outer one's pool and only the
   outermost closes it; an exception leaves no scope behind and the pool
   closed; ``discard`` is idempotent; a pool of another size is made anew.
3. **A borrowed pool found broken is made anew once,** and the search
   splits as it would have (no fallback note); broken again, it falls back
   to the sequential answer and says so, as before. After any other
   failure, which falls back as before, the next search makes a new pool.
4. **A stop inside the grid discards the borrowed pool** (dropping what is
   queued, as the Cancel of D362/D368 does) and the next search makes a new
   one; a stop outside a grid closes it on the way out.
5. **Without a scope each search makes and closes its own pool.**
6. **The four conductors open a scope.**

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import pickle


@contextlib.contextmanager
def _inline_pools(broken=0, failing=0):
    """``concurrent.futures.ProcessPoolExecutor`` replaced by an executor
    that runs each task at once on a pickled copy; the first ``broken``
    pools made are broken (``submit`` raises ``BrokenProcessPool``), and
    the first ``failing`` fail otherwise (``OSError``) without being
    broken. Yields the pools made."""
    import concurrent.futures as cf
    from concurrent.futures.process import BrokenProcessPool
    real = cf.ProcessPoolExecutor
    made = []

    class Inline:
        def __init__(self, max_workers=None):
            self.max_workers = max_workers
            self.shutdowns = []
            self.broken = len(made) < broken
            self.failing = len(made) < failing
            made.append(self)

        def submit(self, fn, *args):
            if self.broken:
                raise BrokenProcessPool("a worker died")
            if self.failing:
                raise OSError("no pipe today")
            f = cf.Future()
            try:
                part = fn(*pickle.loads(pickle.dumps(args)))
                f.set_result(pickle.loads(pickle.dumps(part)))
            except Exception as exc:  # noqa: BLE001 - handed to the future
                f.set_exception(exc)
            return f

        def shutdown(self, wait=True, cancel_futures=False):
            self.shutdowns.append((wait, cancel_futures))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.shutdown(wait=True)
            return False

    cf.ProcessPoolExecutor = Inline
    try:
        yield made
    finally:
        cf.ProcessPoolExecutor = real


@contextlib.contextmanager
def _no_scope_lent():
    """As in v0.1.395: no search ever finds a scope."""
    import ogr_slip2d.processes as P
    real = P.current_pool_scope
    P.current_pool_scope = lambda: None
    try:
        yield
    finally:
        P.current_pool_scope = real


@contextlib.contextmanager
def _small_grids_split():
    """A grid of 96 circles opens a pool, as one of 400 does: the point here
    is how a pool is lent, not at what size a grid splits (the threshold of
    v0.1.97, given back on exit)."""
    import ogr_slip2d.search as S
    real = S._PARALLEL_MIN_CIRCLES
    S._PARALLEL_MIN_CIRCLES = 40
    try:
        yield
    finally:
        S._PARALLEL_MIN_CIRCLES = real


def _project(parallel=True):
    """The Ej_2 geometry of test_parallel_search_v197, dry, with a 3 x 3
    grid and 6 radii: 96 circles."""
    import importlib
    p = importlib.import_module("test_parallel_search_v197")._project()
    s = p.settings.search
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 5
    p.settings.methods.num_slices = 8
    adv = p.settings.advanced
    adv.parallel_search = parallel
    adv.parallel_cpu_percent = 100
    return p


def _search(p):
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    return GridSearch(method=get_method("ordinary_fellenius")(),
                      grid_x=(-40.0, 70.0), grid_y=(35.0, 135.0),
                      grid_nx=3, grid_ny=3, radius_increment=5,
                      min_radius=0.0, num_slices=8, min_area=1.0)


def _fingerprint(result):
    import importlib
    return importlib.import_module(
        "test_parallel_search_v197")._fingerprint(result)


def _sequential():
    p = _project(parallel=False)
    return _fingerprint(_search(p).run(p))


METHODS = ["ordinary_fellenius", "janbu_simplified"]


# ======================================================================
class TestTheSameEvaluationsOnePool:
    """Invariant 1."""

    def test_a_compute_with_two_methods(self):
        import os
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.processes import current_pool_scope
        if (os.cpu_count() or 1) < 2:
            return          # one processor: no search splits
        with _small_grids_split():
            with _inline_pools() as made:
                new = run_analysis(_project(), METHODS)
                assert current_pool_scope() is None
            with _inline_pools() as made_old, _no_scope_lent():
                old = run_analysis(_project(), METHODS)
        assert sorted(new.results) == sorted(METHODS)
        assert len(made) == 1
        assert made[0].shutdowns == [(True, True)], "closed on return"
        assert len(made_old) == 2
        got = {m: _fingerprint(r) for m, r in new.results.items()}
        assert got == {m: _fingerprint(r) for m, r in old.results.items()}
        assert all(got.values())


# ======================================================================
class TestScopes:
    """Invariant 2."""

    def test_nested_scopes_share_and_the_outermost_closes(self):
        from ogr_slip2d.processes import current_pool_scope, pool_scope
        with _inline_pools() as made:
            with pool_scope() as outer:
                pool = current_pool_scope().borrow(2)
                with pool_scope():
                    assert current_pool_scope() is outer
                    assert current_pool_scope().borrow(2) is pool
                assert made[0].shutdowns == []
            assert made[0].shutdowns == [(True, True)]
            assert current_pool_scope() is None
        assert len(made) == 1

    def test_an_exception_leaves_no_scope(self):
        from ogr_slip2d.processes import current_pool_scope, pool_scope
        with _inline_pools() as made:
            try:
                with pool_scope():
                    current_pool_scope().borrow(2)
                    raise ValueError("a calculation that failed")
            except ValueError:
                pass
            assert current_pool_scope() is None
        assert made[0].shutdowns == [(True, True)]

    def test_discard_and_another_size(self):
        from ogr_slip2d.processes import pool_scope
        with _inline_pools() as made:
            with pool_scope() as scope:
                a = scope.borrow(2)
                assert scope.borrow(2) is a
                b = scope.borrow(3)
                assert b is not a and a.shutdowns == [(True, True)]
                scope.discard()
                scope.discard()
                assert b.shutdowns == [(True, True)]
            assert b.shutdowns == [(True, True)], "discarded once"
        assert [m.max_workers for m in made] == [2, 3]


# ======================================================================
class TestABrokenBorrowedPool:
    """Invariant 3."""

    def _run(self, broken):
        import os
        from ogr_slip2d.processes import pool_scope
        if (os.cpu_count() or 1) < 2:
            return None, None, None
        p = _project()
        search = _search(p)
        with _small_grids_split(), _inline_pools(broken=broken) as made,                 pool_scope():
            got = search.run(p)
        return got, made, " ".join(getattr(got, "notes", ()) or ())

    def test_made_anew_once(self):
        got, made, notes = self._run(broken=1)
        if got is None:
            return
        assert len(made) == 2
        assert "BrokenProcessPool" not in notes
        assert _fingerprint(got) == _sequential()

    def test_broken_again_falls_back_and_says_so(self):
        got, made, notes = self._run(broken=2)
        if got is None:
            return
        assert len(made) == 2
        assert "BrokenProcessPool" in notes
        assert _fingerprint(got) == _sequential()


    def test_after_another_failure_the_next_search_starts_afresh(self):
        """A failure that does not break the pool falls back, as before,
        and what that search used is not lent to the next one."""
        import os
        from ogr_slip2d.processes import pool_scope
        if (os.cpu_count() or 1) < 2:
            return
        p = _project()
        with _small_grids_split(), _inline_pools(failing=1) as made,                 pool_scope():
            first = _search(p).run(p)
            second = _search(p).run(p)
        assert "OSError" in " ".join(first.notes or ())
        assert "OSError" not in " ".join(second.notes or ())
        assert len(made) == 2
        assert _fingerprint(first) == _fingerprint(second) == _sequential()


# ======================================================================
class _Stop(BaseException):
    """What the window's Cancel raises: not an ``Exception``."""


class TestAStop:
    """Invariant 4."""

    def test_inside_the_grid(self):
        import os
        from ogr_slip2d.processes import current_pool_scope, pool_scope
        if (os.cpu_count() or 1) < 2:
            return
        p = _project()
        search = _search(p)

        def stop(_done, _total):
            raise _Stop()

        search.progress_cb = stop
        with _small_grids_split(), _inline_pools() as made:
            with pool_scope():
                try:
                    search.run(p)
                except _Stop:
                    pass
                else:
                    raise AssertionError("the stop did not reach the caller")
                assert made[0].shutdowns == [(True, True)], "discarded"
                again = current_pool_scope().borrow(2)
                assert again is not made[0]
        assert search.progress_cb is stop
        assert made[1].shutdowns == [(True, True)]

    def test_outside_a_grid(self):
        from ogr_slip2d.processes import current_pool_scope, pool_scope
        with _inline_pools() as made:
            try:
                with pool_scope():
                    current_pool_scope().borrow(2)
                    raise _Stop()
            except _Stop:
                pass
        assert made[0].shutdowns == [(True, True)]


# ======================================================================
class TestWithoutAScope:
    """Invariant 5."""

    def test_each_search_its_own_pool(self):
        import os
        if (os.cpu_count() or 1) < 2:
            return
        p = _project()
        with _small_grids_split(), _inline_pools() as made:
            for _ in range(2):
                _search(p).run(p)
        assert len(made) == 2
        assert all(m.shutdowns and m.shutdowns[-1] == (True, False)
                   for m in made), "each closed by its own with"


# ======================================================================
class TestTheConductors:
    """Invariant 6."""

    def test_the_four_open_a_scope(self):
        from ogr_slip2d import analysis_runner as A
        from ogr_slip2d import transient_stability as T
        for fn in (A.run_analysis, A.run_configured_drawdown_sweep,
                   A.run_configured_statistics, T.run_transient_stability):
            assert fn.__code__.co_name == "run_pooled", fn.__name__
            assert fn.__wrapped__.__name__ == fn.__name__
