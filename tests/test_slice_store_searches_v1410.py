# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.410 (D383, V3) — every search spills its population, a rapid
drawdown's screen states go with their result, and a result that crosses a
process keeps its slices on disk.

WHAT INVARIANT THIS PROTECTS.

v0.1.408 and v0.1.409 spilled the grid only. Now every search keeps its
evaluations through one door (``BaseSearch._keep``) and says how many
surfaces it plans (``nominal_surfaces``), the measure of the owner's
threshold. The reference is the same search in memory, the path the bench
validates: the store may only change where the slices live.

1. **Every search reads back what it computed:** Slope, Auto Refine
   (circular and non-circular), Block, Path, Simulated Annealing and the
   particle swarm, with a store, equal the same search in memory, slice by
   slice, floats by their bits; the critical surface is in memory.
2. **The walk a search steered stays on disk:** a Slope Search's
   refinement walk (``steered``) is spilled and not brought back: only its
   identity is ever asked for.
3. **Every search says what it plans, and the threshold follows it
   (rule 7):** ``nominal_surfaces`` is each search's own count, and
   ``wants_store`` turns at the threshold.
4. **A rapid drawdown's screen states go with their result:** the state
   whose slices the result publishes shares its record, the other has its
   own; the verdict of the checks is the same spilled; back in memory,
   through a pool's batch and across a process, the sharing holds.
5. **A result that crosses a process stays on disk:** read ``arriving``,
   its spilled slices go to a store of the reading process, equal to what
   was computed; the API's ``Job.load_results`` reads so; outside it they
   come back as slices, as before.

The slope of ``test_block_search_v117`` (12 m, 31°), searches a few dozen
surfaces each; the Slope Search's walk, up to 8 x 120 steps, is most of the
file's time.
"""
from __future__ import annotations

import contextlib
import copy
import gc
import os
import pickle
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _makers():
    from ogr_slip2d import BishopSimplified, Spencer
    from ogr_slip2d import search as S
    from ogr_slip2d.particle_swarm import ParticleSwarmSearch
    return {
        "slope": lambda: S.SlopeSearch(
            method=BishopSimplified(), num_surfaces=40, num_slices=12, seed=7),
        "auto_refine": lambda: S.AutoRefineSearch(
            method=BishopSimplified(), divisions=4, circles_per_division=3,
            iterations=2, num_slices=20),
        "auto_refine_nc": lambda: S.AutoRefineNonCircularSearch(
            method=BishopSimplified(), num_vertices=6, divisions=4,
            circles_per_division=3, iterations=2, num_slices=20),
        "block": lambda: S.BlockSearch(
            method=BishopSimplified(), num_groups=3, num_surfaces=80,
            num_slices=20, min_area=2.0, seed=42),
        "path": lambda: S.PathSearch(
            method=BishopSimplified(), num_vertices=8, num_surfaces=80,
            num_slices=20, seed=5),
        "annealing": lambda: S.SimulatedAnnealingSearch(
            method=Spencer(), initial_vertices=6, generation_steps=30,
            num_slices=20, seed=1234),
        "swarm": lambda: ParticleSwarmSearch(
            method=BishopSimplified(), num_particles=8, num_iterations=6,
            num_slices=20, seed=3),
    }


def _slope():
    from test_block_search_v117 import _slope as slope
    return slope()[0]


_SHARED = {}


def _pairs():
    """Every search in memory and with a store, computed once."""
    if not _SHARED:
        from ogr_slip2d.slice_store import SliceStore
        for name, make in _makers().items():
            mem = make().run(_slope())
            s = make()
            s.slice_store = SliceStore()
            _SHARED[name] = (mem, s.run(_slope()))
    return _SHARED


@contextlib.contextmanager
def _threshold(value):
    from ogr_slip2d import slice_store
    old = slice_store.SPILL_MIN_CIRCLES
    slice_store.SPILL_MIN_CIRCLES = value
    try:
        yield
    finally:
        slice_store.SPILL_MIN_CIRCLES = old


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


def _spilled(evaluations):
    from ogr_slip2d.slice_store import SpilledSlices
    return [e for e in evaluations if type(e.slices) is SpilledSlices]


def _same(a, b):
    assert len(a) == len(b)
    for x, y in zip(a, b):
        assert repr(x.fos) == repr(y.fos)
        if x.slices is None:
            assert y.slices is None
            continue
        assert _slices_canon(x.slices) == _slices_canon(y.slices)


class TestEverySearchReadsBackWhatItComputed:

    def test_each_search(self):
        for name, (mem, disk) in _pairs().items():
            ev = disk.evaluations
            assert len(_spilled(ev)) >= len(ev) - 1 > 0, name
            _same(mem.evaluations, ev)
            assert disk.critical.fos.hex() == mem.critical.fos.hex(), name
            assert type(disk.critical.slices).__name__ == "Slices", name


class TestTheSteeredWalkStaysOnDisk:

    def test_the_slope_searchs_walk(self):
        mem, disk = _pairs()["slope"]
        assert len(disk.steered) > len(disk.evaluations) // 2
        assert len(_spilled(disk.steered)) >= len(disk.steered) - 1
        assert [id(e) for e in disk.steered
                if type(e.slices).__name__ == "Slices"] in (
                    [], [id(disk.critical)])


class TestEverySearchSaysWhatItPlans:

    def test_the_counts_and_the_threshold(self):
        from ogr_slip2d.search import AutoRefineSearch
        from ogr_slip2d.slice_store import wants_store
        planned = {"slope": 40 + 8 * 120,
                   "auto_refine": AutoRefineSearch.surfaces_generated(4, 3, 2),
                   "auto_refine_nc": AutoRefineSearch.surfaces_generated(4, 3, 2),
                   "block": 80, "path": 80, "annealing": 30, "swarm": 8 * 6}
        for name, make in _makers().items():
            s = make()
            n = s.nominal_surfaces()
            assert n == planned[name], (name, n)
            with _threshold(n):
                assert wants_store(s), name
            with _threshold(n + 1):
                assert not wants_store(s), name


def _with_states():
    """An evaluation in memory with a drawdown's two screen states, as the
    wrapper makes them for a cycling drained cap: the published slices are
    the last state's, the other state has its own (a copy here)."""
    mem, _disk = _pairs()["path"]
    src = next(e for e in mem.evaluations if e.slices is not None
               and e.is_valid)
    res = copy.copy(src)
    horn_a, horn_b = copy.copy(src), copy.copy(src)
    horn_a.slices = copy.deepcopy(src.slices)
    res.screen_states = (horn_a, horn_b)
    return res


class TestScreenStatesGoWithTheirResult:

    def test_spilled_shared_and_judged_the_same(self):
        from ogr_slip2d.checks import screen_surface
        from ogr_slip2d.slice_store import SliceStore, rehydrate
        res = _with_states()
        before = [_slices_canon(s.slices) for s in (res, *res.screen_states)]
        verdict = tuple(screen_surface(res, tensile=True, m_alpha=True))
        store = SliceStore()
        published = res.slices
        store.spill(res)
        a, b = res.screen_states
        assert type(res.slices).__name__ == "SpilledSlices"
        assert b.slices is res.slices and a.slices is not res.slices
        assert type(a.slices).__name__ == "SpilledSlices"
        assert store.records == 2
        assert tuple(screen_surface(res, tensile=True, m_alpha=True)) == verdict
        rehydrate(res)
        assert type(res.slices).__name__ == "Slices"
        assert b.slices is res.slices and a.slices is not res.slices
        assert [_slices_canon(s.slices) for s in (res, a, b)] == before
        assert published is not res.slices          # read back, not kept

    def test_through_a_batch_and_across_a_process(self):
        from ogr_slip2d.search import SearchResult
        from ogr_slip2d.slice_store import SliceStore, _BatchStore, arriving
        res = _with_states()
        before = [_slices_canon(s.slices) for s in (res, *res.screen_states)]
        batch = _BatchStore()
        batch.spill(res)
        part = SearchResult(method_id="x")
        part.evaluations.append(res)
        part._worker_table = batch.table
        part = pickle.loads(pickle.dumps(part))
        parent = SliceStore()
        parent.adopt_part(part)
        got = part.evaluations[0]
        a, b = got.screen_states
        assert b.slices is got.slices and a.slices is not got.slices
        assert parent.records == 2
        assert [_slices_canon(s.slices) for s in (got, a, b)] == before
        data = pickle.dumps(got)
        with arriving():
            back = pickle.loads(data)
        a, b = back.screen_states
        assert type(back.slices).__name__ == "SpilledSlices"
        assert back.slices.store is not parent
        assert b.slices is back.slices and a.slices is not back.slices
        assert [_slices_canon(s.slices) for s in (back, a, b)] == before


class TestAResultThatCrossesAProcessStaysOnDisk:

    def test_read_arriving_and_not(self):
        from ogr_slip2d.slice_store import arriving
        mem, disk = _pairs()["path"]
        data = pickle.dumps(disk, pickle.HIGHEST_PROTOCOL)
        with arriving():
            back = pickle.loads(data)
        sp = _spilled(back.evaluations)
        assert len(sp) == len(_spilled(disk.evaluations)) > 0
        store = sp[0].slices.store
        assert store is not _spilled(disk.evaluations)[0].slices.store
        assert os.path.basename(store.path).startswith("%d_" % os.getpid())
        assert {id(e.slices.store) for e in sp} == {id(store)}
        assert type(back.critical.slices).__name__ == "Slices"
        _same(mem.evaluations, back.evaluations)
        path = store.path
        del back, sp, store
        gc.collect()
        assert not os.path.exists(path)
        plain = pickle.loads(data)
        assert not _spilled(plain.evaluations)

    def test_the_api_reads_a_jobs_result_arriving(self):
        from ogr_api.jobs import Job
        _mem, disk = _pairs()["path"]
        with tempfile.TemporaryDirectory() as folder:
            with open(Path(folder) / "result.pkl", "wb") as fh:
                pickle.dump({"results": {"x": disk}}, fh,
                            protocol=pickle.HIGHEST_PROTOCOL)
            job = Job("j_test", "analysis", "p1", Path(folder), None, "h", {})
            got = job.load_results()["results"]["x"]
        assert len(_spilled(got.evaluations)) == len(
            _spilled(disk.evaluations)) > 0
        del got
        gc.collect()
