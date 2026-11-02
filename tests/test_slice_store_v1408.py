# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.408 (D383) — the slices of a large grid's population wait on disk.

WHAT INVARIANT THIS PROTECTS.

Every evaluation kept its slices in memory: 57 kB per surface, 7.1 GB for
one result of the interface test of 0.1.397. A grid of
``slice_store.SPILL_MIN_CIRCLES`` nominal circles or more now hands the
slices of every evaluation it keeps to a ``SliceStore`` (one file in a
private folder) and keeps a ``SpilledSlices`` in their place. The
reference is the same run in memory, the path the bench validates: the
store may only change where the slices live.

1. **What is read back is what was computed:** every evaluation of a spilled
   run equals the same run in memory, slice by slice, every field, floats by
   their bits (``float.hex``), materials by name; and the factors.
2. **The base and the area kept in memory are those of the slices:**
   ``surface_path`` and ``surface_area`` give the same floats.
3. **Nothing reads the file by accident:** length, truth, ``surface_path``,
   ``surface_area``, ``surfaces_through_point``, ``lem_summary``, and the
   Interpret slice pick, which compared results with ``==`` (field by
   field, slices included) and now compares them by identity.
4. **A pickled result carries its slices:** read back after its store is
   gone, they are the computed ones.
5. **The store goes with its results:** the folder exists while a result
   names it and is removed when the last one dies. The critical surface
   keeps real slices; the slices read back hold the run's copies of the
   materials, not the project's (D381), the same ones as the critical.
6. **The threshold moves the number (rule 7):** below it nothing is
   spilled; at it, the memory per evaluation drops.
7. **A folder a dead session left is removed when a store is made;** a
   recent one, and the store's own, are not.
8. **The back analysis is the same spilled or not,** and it does spill.

Grids of 5 x 5 x 4 on ACADS 1(a) (validation case 001): small enough for a
second, and the threshold is set to 0 to spill them, then put back.
"""
from __future__ import annotations

import contextlib
import copy
import gc
import os
import pickle
import sys
import tempfile
import time
import weakref
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_MODEL = _ROOT / "validacion" / "casos" / "001-acads-1a" / "modelo.ogr"
_METHODS = ["bishop_simplified", "janbu_corrected"]


def _project(n=4, ri=4):
    from ogr_core.project import Project
    p = Project.load(str(_MODEL))
    s = p.settings.search
    s.grid_nx = s.grid_ny = n
    s.radius_increment = ri
    p.settings.advanced.parallel_search = False
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


def _run(spill, methods=_METHODS, **kw):
    from ogr_slip2d.analysis_runner import run_analysis
    with _threshold(0 if spill else 10 ** 9):
        return run_analysis(_project(**kw), methods)


_SHARED = {}


def _pair():
    """The same run in memory and spilled, computed once for the file."""
    if not _SHARED:
        _SHARED["mem"] = _run(False)
        _SHARED["disk"] = _run(True)
    return _SHARED["mem"], _SHARED["disk"]


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


def _spilled(result):
    from ogr_slip2d.slice_store import SpilledSlices
    return [e for e in result.evaluations if type(e.slices) is SpilledSlices]


class TestWhatIsReadBackIsWhatWasComputed:

    def test_every_slice_of_every_evaluation(self):
        mem, disk = _pair()
        for mid in _METHODS:
            a, b = mem.results[mid].evaluations, disk.results[mid].evaluations
            assert len(a) == len(b) and len(_spilled(disk.results[mid])) > 0.9 * len(b)
            for x, y in zip(a, b):
                assert repr(x.fos) == repr(y.fos)
                if x.slices is None:
                    assert y.slices is None
                    continue
                assert _slices_canon(x.slices) == _slices_canon(y.slices)

    def test_the_critical_is_the_same_and_in_memory(self):
        from ogr_slip2d.slicer import Slices
        mem, disk = _pair()
        for mid in _METHODS:
            a, b = mem.results[mid].critical, disk.results[mid].critical
            assert a.fos.hex() == b.fos.hex()
            assert type(b.slices) is Slices
            assert _slices_canon(a.slices) == _slices_canon(b.slices)


class TestTheBaseAndTheAreaKeptInMemory:

    def test_surface_path_and_surface_area(self):
        from ogr_slip2d.interpretation import surface_area, surface_path
        mem, disk = _pair()
        for mid in _METHODS:
            for x, y in zip(mem.results[mid].evaluations, disk.results[mid].evaluations):
                if x.slices is None:
                    continue
                assert ([(p.hex(), q.hex()) for p, q in surface_path(x)]
                        == [(p.hex(), q.hex()) for p, q in surface_path(y)])
                assert surface_area(x).hex() == surface_area(y).hex()
                assert len(x.slices) == len(y.slices)


class _Raises:
    """Slices that fail a test if anyone compares them."""

    def __eq__(self, other):
        raise AssertionError("two results compared by value")

    __hash__ = None

    def __len__(self):
        return 0

    def __iter__(self):
        return iter(())


class TestNothingReadsTheFileByAccident:

    def test_length_truth_trace_area_and_summaries(self):
        from ogr_api.results import lem_summary
        from ogr_slip2d.interpretation import (surface_area, surface_path,
                                               surfaces_through_point)
        _mem, disk = _pair()
        sr = disk.results["bishop_simplified"]
        store = _spilled(sr)[0].slices.store
        before = store.loads
        for e in _spilled(sr):
            assert len(e.slices) > 0 and bool(e.slices)
            surface_path(e)
            surface_area(e)
            lem_summary(e)
        x, y = surface_path(_spilled(sr)[0])[3]
        assert surfaces_through_point(sr, x, y, 0.5)
        assert store.loads == before

    def test_the_interpret_slice_pick_compares_by_identity(self):
        from ogr_gui.interpret_window import InterpretWindow
        _mem, disk = _pair()
        target = _spilled(disk.results["bishop_simplified"])[0]
        twin = copy.copy(target)          # equal up to the slices
        twin.slices = _Raises()
        shown = []

        class _Bar:
            def showMessage(self, *a):
                shown.append(a)

        class _Dock:
            def show_slice(self, *a):
                pass

            def raise_(self):
                pass

        class _Window:
            _query_slice_target = target
            slice_dock = _Dock()

            def _slice_surfaces(self):
                return [twin]

            def statusBar(self):
                return _Bar()

            def _highlight_slice(self, *a):
                pass

        s = target.slices[len(target.slices) // 2]
        InterpretWindow._on_canvas_click_for_query(
            _Window(), 0.5 * (s.base_x_left + s.base_x_right), s.base_y_left)
        assert shown, "no slice was picked"


class TestAPickledResultCarriesItsSlices:

    def test_read_back_after_the_store_is_gone(self):
        mem, _disk = _pair()
        out = _run(True, methods=["bishop_simplified"])
        sr = out.results["bishop_simplified"]
        path = _spilled(sr)[0].slices.store.path
        data = pickle.dumps(sr, pickle.HIGHEST_PROTOCOL)
        del out, sr
        gc.collect()
        assert not os.path.exists(path), "the store outlived its result"
        back = pickle.loads(data)
        for x, y in zip(mem.results["bishop_simplified"].evaluations, back.evaluations):
            if x.slices is not None:
                assert _slices_canon(x.slices) == _slices_canon(y.slices)


class TestTheStoreGoesWithItsResults:

    def test_the_folder_lives_while_a_result_names_it(self):
        out = _run(True)
        sr = out.results["bishop_simplified"]
        store = _spilled(sr)[0].slices.store
        path, ref = store.path, weakref.ref(store)
        # never its file to a worker: since v0.1.409 (V2) a store in the
        # worker's memory, without a folder
        shipped = pickle.loads(pickle.dumps(store))
        assert shipped is not store and shipped.path is None
        del shipped
        assert os.path.isdir(path)
        del store, sr
        gc.collect()
        assert os.path.isdir(path), "removed while the run still names it"
        del out
        gc.collect()
        assert ref() is None
        assert not os.path.exists(path)

    def test_read_back_slices_hold_the_runs_copies_of_the_materials(self):
        _mem, disk = _pair()
        live = {id(m) for m in disk.project.materials}
        sr = disk.results["bishop_simplified"]
        crit_materials = {id(s.material) for s in sr.critical.slices}
        for e in _spilled(sr)[:20]:
            for s in e.slices:
                assert id(s.material) not in live
                assert id(s.material) in crit_materials


class TestTheThresholdMovesTheNumber:

    def test_below_it_nothing_is_spilled(self):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.slice_store import wants_store
        search = build_search(_project(), "bishop_simplified")
        n = search.nominal_circles()
        assert n == 5 * 5 * 5
        with _threshold(n):
            assert wants_store(search)
        with _threshold(n + 1):
            assert not wants_store(search)
        mem, _disk = _pair()
        assert not _spilled(mem.results["bishop_simplified"])

    def test_the_memory_per_evaluation_drops(self):
        import tracemalloc
        _pair()      # both paths imported and warmed before measuring
        held = {}
        for spill in (False, True):
            gc.collect()
            tracemalloc.start()
            try:
                base = tracemalloc.get_traced_memory()[0]
                out = _run(spill, methods=["bishop_simplified"], n=3, ri=3)
                gc.collect()
                n = len(out.results["bishop_simplified"].evaluations)
                held[spill] = (tracemalloc.get_traced_memory()[0] - base) / n
            finally:
                tracemalloc.stop()
            del out
        assert held[True] < held[False] / 3, held


class TestOrphanFolders:

    def test_old_ones_go_recent_ones_stay(self):
        from ogr_slip2d.slice_store import remove_orphans
        with tempfile.TemporaryDirectory() as root:
            old, new, mine = (os.path.join(root, n) for n in ("1_old", "2_new", "3_mine"))
            for d in (old, new, mine):
                os.makedirs(d)
                Path(d, "slices.bin").write_bytes(b"x")
            hours_ago = time.time() - 7200
            os.utime(old, (hours_ago, hours_ago))
            os.utime(mine, (hours_ago, hours_ago))
            assert remove_orphans(root, age_s=3600, keep=mine) == 1
            assert not os.path.exists(old)
            assert os.path.isdir(new) and os.path.isdir(mine)


class TestTheBackAnalysisSpilledOrNot:

    def test_the_same_answer_and_it_spills(self):
        from ogr_slip2d.analysis_runner import run_configured_back_analysis
        from ogr_slip2d.slice_store import SliceStore
        spilled = []
        raw = SliceStore.spill

        def counting(self, res):
            spilled.append(1)
            return raw(self, res)
        answers = []
        SliceStore.spill = counting
        try:
            for spill in (False, True):
                with _threshold(0 if spill else 10 ** 9):
                    ba, _rep, _w = run_configured_back_analysis(
                        _project(), target_fos=1.3, method_id="bishop_simplified")
                c = ba.critical
                answers.append((ba.surfaces_analysed, c.governing_force.hex(),
                                c.active_force.hex(), c.passive_force.hex(),
                                c.unsupported_fos.hex(),
                                repr({k: v for k, v in c.surface.items() if k != "id"})))
        finally:
            SliceStore.spill = raw
        assert answers[0] == answers[1]
        assert spilled, "the back analysis did not spill"
