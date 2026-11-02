# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.409 (D383, V2) — a grid split across a process pool spills too, and
an agent's job that is killed leaves no slice store behind.

WHAT INVARIANT THIS PROTECTS.

v0.1.408 spilled only a grid evaluated in this process; the window splits
its grids across a pool by default, and there the workers kept every slice
and the parent unpickled them all. Now the store shipped with the search is
a store in the worker's memory for its batch, the batch comes back as
records and the batch's table of materials, and the parent writes the
records to its own file as each batch arrives. The reference is the same
run in series and in memory, the path the bench validates.

1. **What a pool's run reads back is what was computed:** every evaluation
   of a spilled run split across a pool equals the same grid in series in
   memory, slice by slice, floats by their bits, materials by name.
2. **A batch comes back as records,** and only when the search has a store:
   with one, every evaluation with slices arrives as a record with the
   batch's table; without, as slices, as before.
3. **Each batch's records name its own table:** the slices read back use the
   materials of their batch, and the batches' positions in the store's
   table differ (``_base``).
4. **The same with a real pool:** ``run_analysis`` on a grid the pool takes.
5. **A job that is cancelled, or crashes, leaves no store folder:** its
   process is killed and never runs its finalizers, so the parent removes
   the folders its process number names: the one ``Popen`` knows and the
   one the worker wrote in its folder. Another process's stay.

ACADS 1(a) (validation case 001) at 9 x 9 x 4: 500 circles, over the
pool's floor of 400. Cases 1–3 run the pool in this process (each batch and
each part go through pickle, the boundary that matters), so they cost no
worker start; case 4 starts a pool of two, once.
"""
from __future__ import annotations

import concurrent.futures
import contextlib
import gc
import os
import pickle
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_MODEL = _ROOT / "validacion" / "casos" / "001-acads-1a" / "modelo.ogr"
_METHOD = "bishop_simplified"


def _project(parallel):
    from ogr_core.project import Project
    p = Project.load(str(_MODEL))
    s = p.settings.search
    s.grid_nx = s.grid_ny = 8
    s.radius_increment = 4
    p.settings.advanced.parallel_search = parallel
    p.settings.advanced.parallel_cpu_percent = 50
    return p


@contextlib.contextmanager
def _threshold(value):
    from ogr_slip2d import slice_store
    old = slice_store.SPILL_MIN_CIRCLES
    slice_store.SPILL_MIN_CIRCLES = value
    try:
        yield
    finally:
        slice_store.SPILL_MIN_CIRCLES = old


class _InProcessPool:
    """The pool's protocol in this process: each payload and each part go
    through pickle, as across a process, and what arrives is recorded."""

    def __init__(self, arrived):
        self.arrived = arrived

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, payload):
        fut = concurrent.futures.Future()
        part = pickle.loads(pickle.dumps(fn(pickle.loads(pickle.dumps(payload)))))
        self.arrived.append((type(part).__name__,
                             [type(e.slices).__name__ for e in part.evaluations
                              if e.slices is not None and len(e.slices)],
                             getattr(part, "_worker_table", None) is not None))
        fut.set_result(part)
        return fut

    def shutdown(self, *a, **kw):
        pass


def _search_run(store):
    """A grid search split across the in-process pool; what arrived."""
    from ogr_slip2d import processes
    from ogr_slip2d import search as S
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.slice_store import SliceStore
    arrived = []
    raw_pool, raw_count = processes.stoppable_pool, S._worker_count
    processes.stoppable_pool = lambda workers: (_InProcessPool(arrived),
                                                threading.Event())
    # four "workers" whatever this machine has: 32 batches
    S._worker_count = lambda project, n: 4
    try:
        p = _project(parallel=True)
        search = build_search(p, _METHOD)
        if store:
            search.slice_store = SliceStore()
        result = search.run(p)
    finally:
        processes.stoppable_pool, S._worker_count = raw_pool, raw_count
    return result, arrived


_SHARED = {}


def _shared():
    if not _SHARED:
        from ogr_slip2d.analysis_runner import build_search
        p = _project(parallel=False)
        _SHARED["mem"] = build_search(p, _METHOD).run(p)
        _SHARED["pool"], _SHARED["arrived"] = _search_run(store=True)
        _SHARED["pool_mem"], _SHARED["arrived_mem"] = _search_run(store=False)
    return _SHARED


def _canon(v):
    from ogr_core.materials import Material
    if type(v) is float:
        return ("f", v.hex())
    if isinstance(v, Material):
        return ("M", v.name)
    if isinstance(v, (list, tuple)):
        return (type(v).__name__, tuple(_canon(x) for x in v))
    if isinstance(v, dict):
        return ("d", tuple((repr(k), _canon(x)) for k, x in v.items()))
    return (type(v).__name__, repr(v))


def _slices_canon(sl):
    from ogr_slip2d.slice_store import SpilledSlices
    if type(sl) is SpilledSlices:
        sl = sl.materialize()
    scalars = tuple(_canon(getattr(sl, k)) for k in (
        "tension_crack_force", "tension_crack_arm", "tension_crack_wall",
        "design_sense", "load_factors"))
    return scalars, tuple(tuple((k, _canon(v)) for k, v in vars(s).items())
                          for s in sl)


def _same_population(a, b):
    assert len(a.evaluations) == len(b.evaluations)
    for x, y in zip(a.evaluations, b.evaluations):
        assert repr(x.fos) == repr(y.fos)
        if x.slices is None:
            assert y.slices is None
            continue
        assert _slices_canon(x.slices) == _slices_canon(y.slices)


def _spilled(result):
    from ogr_slip2d.slice_store import SpilledSlices
    return [e for e in result.evaluations if type(e.slices) is SpilledSlices]


class TestWhatAPoolsRunReadsBackIsWhatWasComputed:

    def test_every_slice_of_every_evaluation(self):
        s = _shared()
        assert len(s["arrived"]) > 1, "the grid was not split"
        assert len(_spilled(s["pool"])) > 0.9 * len(s["pool"].evaluations)
        _same_population(s["mem"], s["pool"])
        assert s["pool"].critical.fos.hex() == s["mem"].critical.fos.hex()
        assert type(s["pool"].critical.slices).__name__ == "Slices"


class TestABatchComesBackAsRecords:

    def test_with_a_store_records_and_the_table(self):
        for kind, types, has_table in _shared()["arrived"]:
            assert kind == "SearchResult" and has_table
            assert types and set(types) == {"_Pending"}

    def test_without_one_slices_as_before(self):
        s = _shared()
        for _kind, types, has_table in s["arrived_mem"]:
            assert not has_table and set(types) == {"Slices"}
        assert not _spilled(s["pool_mem"])
        _same_population(s["mem"], s["pool_mem"])


class TestEachBatchNamesItsOwnTable:

    def test_bases_differ_and_materials_are_the_batchs(self):
        sp = _spilled(_shared()["pool"])
        store = sp[0].slices.store
        by_base = {}
        for e in sp:
            by_base.setdefault(e.slices._base, []).append(e)
        assert len(by_base) == len(_shared()["arrived"])
        bases = sorted(by_base)
        for k, base in enumerate(bases):
            end = bases[k + 1] if k + 1 < len(bases) else len(store.table)
            own = {id(m) for m in store.table[base:end]}
            for e in by_base[base][:5]:
                for sl in e.slices:
                    assert id(sl.material) in own


class TestTheSameWithARealPool:

    def test_run_analysis_split_across_two_workers(self):
        from ogr_slip2d.analysis_runner import run_analysis
        p = _project(parallel=True)
        p.settings.advanced.parallel_cpu_percent = max(
            1, -(-200 // (os.cpu_count() or 1)))       # two workers
        with _threshold(0):
            out = run_analysis(p, [_METHOD])
        sr = out.results[_METHOD]
        sp = _spilled(sr)
        assert len(sp) > 0.9 * len(sr.evaluations)
        assert len({e.slices._base for e in sp}) > 1, "the grid was not split"
        _same_population(_shared()["mem"], sr)
        path = sp[0].slices.store.path
        del out, sr, sp
        gc.collect()
        assert not os.path.exists(path)


class TestAKilledJobLeavesNoFolder:

    def test_the_folders_its_process_numbers_name_go(self):
        from ogr_api.jobs import Job
        from ogr_slip2d.slice_store import FOLDER
        root = Path(tempfile.gettempdir()) / FOLDER
        root.mkdir(exist_ok=True)
        proc = subprocess.Popen([sys.executable, "-c",
                                 "import time; time.sleep(60)"])
        worker_pid = proc.pid * 10 + 7          # as a venv's launcher's child
        made = [root / f"{proc.pid}_t", root / f"{worker_pid}_t",
                root / f"{proc.pid}0_t"]        # another process's: stays
        try:
            for d in made:
                d.mkdir()
                (d / "slices.bin").write_bytes(b"x")
            with tempfile.TemporaryDirectory() as folder:
                (Path(folder) / "pid").write_text(str(worker_pid),
                                                  encoding="ascii")
                job = Job("j_test", "analysis", "p1", Path(folder), proc,
                          "hash", {})
                assert job.cancel()["state"] == "cancelled"
            assert not made[0].exists() and not made[1].exists()
            assert made[2].is_dir()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            for d in made:
                if d.exists():
                    for f in d.iterdir():
                        f.unlink()
                    d.rmdir()
