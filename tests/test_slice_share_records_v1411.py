# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.411 (D393) — the SliceShare of a large grid keeps its clean copies as
records, and each later method reads its own.

WHAT INVARIANT THIS PROTECTS.

V18 (v0.1.397) slices a serial grid once for every method of a Compute: the
first method keeps a clean copy of each surface's slices for the methods
after it. Those copies grew to cover the whole grid while the first method
ran and made the run's peak: 2.8 GB for the 0.8 GB the interface test of
0.1.397 keeps (51 x 51 x 12, four methods; measured in the verification
bench with ``_auditoria/P8_interfaz/d393_medir.py``). Now a leader that
plans a population worth spilling (``slice_store.wants_store``, the owner's
decision) keeps each copy as a record (``slice_store.SliceRecords``), and
each later method reads its own. The reference is V18's (Class B: the same
function's output for the same input): each method as if it had sliced
alone.

The model and the comparisons are test_slice_share_v1397's: ACADS 1(b)
(Giam & Donald 1989) with its water-filled tension crack, a 150-circle grid,
in series. ``SPILL_MIN_CIRCLES`` is set to 0 to put this small grid over the
threshold, and restored.

1. **Each method answers as if it had sliced alone, through records:**
   Bishop, Janbu Simplified and the Ordinary method in one Compute and each
   on its own, every evaluation, counter, note and the critical surface,
   floats as hex; and the later methods do not slice.
2. **What a later method reads is its own, with the materials that were
   written:** a new graph at every read, the last one too; the same numbers
   as the leader's slices, and the very ``Material`` objects of the project
   the leader sliced (the records' table is their own: ``detach_materials``
   rebinds a store's, never theirs). The record is released at its last use.
3. **The share keeps no slice between methods:** with automatic collection
   off, when the second method starts, the share's records hold no ``Slice``
   or ``Slices`` and the whole process holds fewer slices than the grid has
   surfaces; with the copies of a small grid it holds one ``Slices`` per
   recorded surface.
4. **The threshold decides, and moves the number (rule 7):** over it, the
   share holds records and no slices; under it, copies.
"""
from __future__ import annotations

import contextlib
import gc
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

V18 = importlib.import_module("test_slice_share_v1397")
METHODS = V18.METHODS


@contextlib.contextmanager
def _threshold(value):
    from ogr_slip2d import slice_store
    old = slice_store.SPILL_MIN_CIRCLES
    slice_store.SPILL_MIN_CIRCLES = value
    try:
        yield
    finally:
        slice_store.SPILL_MIN_CIRCLES = old


_CACHE: dict = {}


def _runs():
    """The Compute of three methods and each method alone, every one over
    the threshold, with the slicings each made; computed once."""
    if not _CACHE:
        from ogr_slip2d.analysis_runner import run_analysis
        with _threshold(0):
            with V18._counting_slices() as calls:
                together = run_analysis(V18._model(), METHODS)
            _CACHE["together"] = (together, calls[0])
            for mid in METHODS:
                with V18._counting_slices() as calls:
                    alone = run_analysis(V18._model(), [mid])
                _CACHE[mid] = (alone, calls[0])
    return _CACHE


def _rehydrated(result):
    """``V18._result`` reads ``slices.slices``: the spilled population back
    in memory, a copy of the result's list."""
    import copy
    from ogr_slip2d.slice_store import SpilledSlices
    out = copy.copy(result)
    out.evaluations = []
    for e in result.evaluations:
        if type(e.slices) is SpilledSlices:
            e = copy.copy(e)
            e.slices = e.slices.materialize()
        out.evaluations.append(e)
    return out


def _slices_held(share) -> int:
    """``Slice`` and ``Slices`` objects reachable from the share's records
    through its containers."""
    from ogr_slip2d.slicer import Slice, Slices
    seen, stack, found = set(), [share._records], 0
    while stack:
        o = stack.pop()
        if id(o) in seen:
            continue
        seen.add(id(o))
        if isinstance(o, (Slice, Slices)):
            found += 1
            stack.extend(gc.get_referents(o))
        elif isinstance(o, (dict, list, tuple)):
            stack.extend(gc.get_referents(o))
    return found


def _at_the_second_method(threshold):
    """A Compute of two methods with automatic collection off; when the
    second method first slices: the share's records, the slices they hold,
    and every ``Slices`` alive in the process."""
    import ogr_slip2d.search as S
    from ogr_slip2d.analysis_runner import run_analysis
    from ogr_slip2d.slicer import Slices
    seen = {}
    real = S.SliceShare.slice

    def watching(self, search, project, trial, num_slices, reasons):
        if (not seen and self.leader is not None
                and search is not self.leader):
            seen["records"] = len(self._records)
            seen["bytes"] = sum(type(r[1]) is bytes
                                for r in self._records.values())
            seen["held"] = _slices_held(self)
            seen["alive"] = sum(1 for o in gc.get_objects()
                                if type(o) is Slices)
            seen["serialized"] = getattr(self, "serialized", None)
        return real(self, search, project, trial, num_slices, reasons)

    was = gc.isenabled()
    gc.collect()
    gc.disable()
    S.SliceShare.slice = watching
    try:
        with _threshold(threshold):
            out = run_analysis(V18._model(), METHODS[:2])
    finally:
        S.SliceShare.slice = real
        if was:
            gc.enable()
    surfaces = len(out.results[METHODS[0]].evaluations)
    del out
    gc.collect()
    return seen, surfaces


class _Plans:
    """A leader that plans a population: ``wants_store`` asks this."""

    def nominal_surfaces(self):
        return 1


# ======================================================================
class TestEachMethodAsIfAloneThroughRecords:
    """Invariant 1."""

    def test_three_methods(self):
        runs = _runs()
        together = runs["together"][0]
        assert sorted(together.results) == sorted(METHODS)
        for mid in METHODS:
            got = V18._result(_rehydrated(together.results[mid]))
            assert got == V18._result(_rehydrated(runs[mid][0].results[mid])), mid
            assert len(got[0]) > 50, mid

    def test_the_later_methods_do_not_slice(self):
        runs = _runs()
        alone = {mid: runs[mid][1] for mid in METHODS}
        assert len(set(alone.values())) == 1, alone
        assert runs["together"][1] == alone[METHODS[0]]


# ======================================================================
class TestWhatALaterMethodReads:
    """Invariant 2."""

    def test_its_own_graph_with_the_written_materials(self):
        from ogr_slip2d.search import SliceShare
        from ogr_slip2d.surface import SlipCircle
        p = V18._model()
        share = SliceShare(followers=2)
        leader, f1, f2 = _Plans(), object(), object()

        def circle():
            return SlipCircle(centre_x=40.0, centre_y=45.0, radius=18.0)

        with _threshold(0):
            first = share.slice(leader, p, circle(), 20, [])
        assert first is not None and len(share._records) == 1
        record = next(iter(share._records.values()))
        assert type(record[1]) is bytes
        a = share.slice(f1, p, circle(), 20, [])
        assert len(share._records) == 1
        b = share.slice(f2, p, circle(), 20, [])
        assert share._records == {}, "released at its last use"
        numbers = [V18._slice_numbers(s) for s in first.slices]
        objs = {}
        for who, got in (("first", first), ("a", a), ("b", b)):
            assert [V18._slice_numbers(s) for s in got.slices] == numbers, who
            assert got.tension_crack_wall == first.tension_crack_wall, who
            mine = [got, got.slices]
            for s in got.slices:
                mine += [s, s.load_parts]
            for o in mine:
                assert objs.setdefault(id(o), who) == who, (who, type(o))
        for x, y, z in zip(first.slices, a.slices, b.slices):
            assert x.material is y.material is z.material
            assert x.material in p.materials


# ======================================================================
class TestTheShareKeepsNoSlicesBetweenMethods:
    """Invariants 3 and 4."""

    def test_over_the_threshold_records(self):
        seen, surfaces = _at_the_second_method(0)
        assert seen["records"] > 50
        assert seen["held"] == 0, seen
        assert seen["bytes"] == seen["records"]
        assert seen["alive"] < surfaces, seen
        assert seen["serialized"] is not None

    def test_under_it_copies(self):
        seen, surfaces = _at_the_second_method(10 ** 9)
        assert seen["serialized"] is None
        assert seen["bytes"] == 0
        assert seen["held"] >= 2 * seen["records"] > 100
        assert seen["alive"] > surfaces, seen
