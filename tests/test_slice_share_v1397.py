# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The methods of one Compute slice a serial grid once.

WHAT INVARIANT THIS PROTECTS.

V18 of the compute audit (v0.1.397). Every method of a Compute ran its grid
over the same circles and sliced every one again: in series slicing is half
of a grid (bank 001 at 51 x 51 x 12, Bishop and Janbu Corrected: 32.7 and
34.0 s of 52.3 and 58.8, the same 32 053 surfaces). Now ``run_analysis``
gives its grid searches a ``search.SliceShare``: the first method records,
per exact state of a trial surface, a clean copy of its slices, the
slicer's reasons and the surface's state after slicing, and each later
method takes a copy of its own instead of slicing (the owner's decisions:
a copy per method, grid searches only). Class B: the same function's
output for the same input.

The model is ACADS 1(b) (Giam & Donald 1989) with its water-filled tension
crack (test_tension_crack_truncation_v1109), on a 150-circle grid, in
series: the slicer moves the circles' ends and leaves their crack walls on
them, which is the state a later method must find.

1. **Each method answers as if it had sliced alone:** Bishop, Janbu
   Simplified and the Ordinary method, in one Compute and each on its own:
   every evaluation (factor, convergence, validity, the surface's whole
   state but its id, every slice), the counters, the notes and the
   critical surface, floats as hex.
2. **The later methods do not slice:** counted on ``slice_surface``, the
   Compute of three methods slices what one method alone slices.
3. **Their slices are their own:** no ``Slices``, ``Slice`` or list object
   is shared between two methods' results, nor any material (each run
   detaches its own, D381).
4. **The key is exact:** 0.0 and -0.0, 1 and 1.0, a crack tuple with
   either zero, give different keys; an attribute that is an object gives
   none (that surface is sliced as always). And the fast shallow copy is
   ``copy.copy``'s, guarded: ``Slice`` and ``Slices`` keep a plain
   ``__dict__`` and no copy hooks.
5. **A share pickles as None,** so a pool's workers slice for themselves,
   and **a record is released at its last use.**

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import importlib
import pickle

METHODS = ["bishop_simplified", "janbu_simplified", "ordinary_fellenius"]


def _model():
    p, _z = importlib.import_module(
        "test_tension_crack_truncation_v1109")._acads_1b()
    s = p.settings.search
    s.grid_nx = s.grid_ny = 4
    s.radius_increment = 5
    p.settings.methods.num_slices = 20
    p.settings.advanced.parallel_search = False
    return p


def _hexed(v):
    if isinstance(v, float):
        return v.hex()
    if isinstance(v, (list, tuple)):
        return [_hexed(x) for x in v]
    if isinstance(v, dict):
        return sorted((k, _hexed(x)) for k, x in v.items())
    return v


def _slice_numbers(s):
    return [(k, _hexed(v)) for k, v in vars(s).items()
            if k not in ("material", "water_material")]


def _evaluation(e):
    surface = sorted((k, _hexed(v)) for k, v in vars(e.surface).items()
                     if k != "id")
    slices = e.slices
    return (_hexed(e.fos), e.converged, e.iterations, e.is_valid,
            e.admissible, e.error_message, surface,
            None if slices is None else (
                [_slice_numbers(s) for s in slices.slices],
                _hexed(slices.tension_crack_force),
                _hexed(slices.tension_crack_wall),
                slices.design_sense))


def _result(r):
    crit = r.critical
    return ([_evaluation(e) for e in r.evaluations], r.valid_count,
            r.invalid_count, r.attempts, r.focus_rejected,
            sorted(getattr(r, "notes", None) or []),
            None if crit is None else _evaluation(crit))


@contextlib.contextmanager
def _counting_slices():
    import ogr_slip2d.search as S
    real = S.slice_surface
    calls = [0]

    def counting(*a, **k):
        calls[0] += 1
        return real(*a, **k)

    S.slice_surface = counting
    try:
        yield calls
    finally:
        S.slice_surface = real


_CACHE: dict = {}


def _runs():
    """The Compute of three methods and each method alone, with the
    slicings each made; computed once for the file."""
    if not _CACHE:
        from ogr_slip2d.analysis_runner import run_analysis
        with _counting_slices() as calls:
            together = run_analysis(_model(), METHODS)
        _CACHE["together"] = (together, calls[0])
        for mid in METHODS:
            with _counting_slices() as calls:
                alone = run_analysis(_model(), [mid])
            _CACHE[mid] = (alone, calls[0])
    return _CACHE


# ======================================================================
class TestEachMethodAsIfAlone:
    """Invariant 1."""

    def test_three_methods(self):
        runs = _runs()
        together = runs["together"][0]
        assert sorted(together.results) == sorted(METHODS)
        walls = 0
        for mid in METHODS:
            got = _result(together.results[mid])
            assert got == _result(runs[mid][0].results[mid]), mid
            assert len(got[0]) > 50, mid
            walls += sum(1 for e in together.results[mid].evaluations
                         if getattr(e.surface, "tension_crack_wall", None))
        assert walls > 0, "the crack left walls the later methods must find"


# ======================================================================
class TestTheLaterMethodsDoNotSlice:
    """Invariant 2."""

    def test_counted(self):
        runs = _runs()
        alone = {mid: runs[mid][1] for mid in METHODS}
        assert len(set(alone.values())) == 1, alone
        assert runs["together"][1] == alone[METHODS[0]]


# ======================================================================
class TestTheirSlicesAreTheirOwn:
    """Invariant 3."""

    def test_no_object_shared(self):
        together = _runs()["together"][0]
        seen: dict = {}
        for mid in METHODS:
            for e in together.results[mid].evaluations:
                cracks = getattr(e.surface, "tension_cracks", None)
                if cracks is not None:
                    owner = seen.setdefault(id(cracks), (mid, cracks))
                    assert owner[0] == mid, (mid, owner[0], "tension_cracks")
                if e.slices is None:
                    continue
                objs = [e.slices, e.slices.slices]
                for s in e.slices.slices:
                    objs += [s, s.load_parts]
                    if s.surface_angles is not None:
                        objs.append(s.surface_angles)
                    if s.material is not None:
                        objs.append(s.material)
                for o in objs:
                    owner = seen.setdefault(id(o), (mid, o))
                    assert owner[0] == mid, (mid, owner[0], type(o))


# ======================================================================
class TestTheKeyIsExact:
    """Invariant 4."""

    def test_zeros_ints_tuples_and_objects(self):
        from ogr_slip2d.search import _state_key
        from ogr_slip2d.surface import SlipCircle

        def key(**kw):
            c = SlipCircle(centre_x=kw.pop("cx", 10.0), centre_y=20.0,
                           radius=5.0)
            for k, v in kw.items():
                setattr(c, k, v)
            return _state_key(c, 20)

        assert key() == key()
        assert key(cx=0.0) != key(cx=-0.0)
        assert key(cx=1.0) != key(cx=1)
        assert key(flag=1) != key(flag=True)
        assert key(tension_crack_wall=(3.0, 0.0, 4.0)) != key(
            tension_crack_wall=(3.0, -0.0, 4.0))
        assert key(tension_cracks=[(1.0, 2.0, 3.0)]) != key(
            tension_cracks=[(1.0, 2.0, -3.0)])
        assert key(extra=object()) is None
        c = SlipCircle(centre_x=1.0, centre_y=2.0, radius=3.0)
        assert _state_key(c, 20) != _state_key(c, 21)


    def test_a_shallow_copy_is_copy_copy(self):
        """``_shallow`` stands for ``copy.copy`` on ``Slice`` and
        ``Slices``: that holds while they have a plain ``__dict__`` and no
        copy hooks, which this guards."""
        import copy
        from ogr_slip2d.search import _shallow
        from ogr_slip2d.slicer import Slice, Slices
        for cls in (Slice, Slices):
            for hook in ("__slots__", "__copy__", "__deepcopy__",
                         "__reduce__", "__reduce_ex__", "__getstate__",
                         "__setstate__", "__new__", "__init_subclass__"):
                assert hook not in vars(cls), (cls.__name__, hook)
        sl = _runs()["together"][0].results[METHODS[0]].evaluations[0].slices
        for obj in (sl, sl.slices[0]):
            a, b = _shallow(obj), copy.copy(obj)
            assert type(a) is type(b) and a is not obj
            assert list(vars(a).items()) == list(vars(b).items())


# ======================================================================
class TestPicklingAndRelease:
    """Invariant 5."""

    def test_a_share_pickles_as_none(self):
        import copy
        from ogr_slip2d.search import SliceShare
        share = SliceShare(followers=2)
        assert pickle.loads(pickle.dumps(share)) is None
        assert copy.deepcopy({"s": share})["s"] is None

    def test_released_at_the_last_use(self):
        from ogr_slip2d.search import SliceShare
        from ogr_slip2d.surface import SlipCircle
        p = _model()
        share = SliceShare(followers=2)
        leader, f1, f2 = object(), object(), object()

        def circle():
            # not resolved: the slicer sets its ends, which the later
            # methods' circles must come out with
            c = SlipCircle(centre_x=40.0, centre_y=45.0, radius=18.0)
            assert c.x_left is None
            return c

        def state(c):
            return sorted((k, _hexed(v)) for k, v in vars(c).items()
                          if k != "id")

        cl, c1, c2 = circle(), circle(), circle()
        first = share.slice(leader, p, cl, 20, [])
        assert first is not None and len(share._records) == 1
        assert cl.x_left is not None
        record = next(iter(share._records.values()))
        a = share.slice(f1, p, c1, 20, [])
        assert a is not record[1] and len(share._records) == 1
        b = share.slice(f2, p, c2, 20, [])
        assert b is record[1], "the last user takes the clean copy itself"
        assert share._records == {}
        assert state(c1) == state(c2) == state(cl)
        assert c1.id != cl.id and c1.tension_cracks is not cl.tension_cracks
        assert ([_slice_numbers(s) for s in a.slices]
                == [_slice_numbers(s) for s in b.slices]
                == [_slice_numbers(s) for s in first.slices])

    def test_the_reasons_reach_the_later_methods(self):
        """What the slicer decided (a refusal, a tolerance used) is
        counted by each method from its reasons."""
        import ogr_slip2d.search as S
        from ogr_slip2d.search import SliceShare
        from ogr_slip2d.surface import SlipCircle
        real = S.slice_surface
        calls = [0]

        def refuses(project, surface, num_slices=50, reasons=None):
            calls[0] += 1
            reasons.append("refused_outside_model")
            return None

        share = SliceShare(followers=2)
        got = []
        S.slice_surface = refuses
        try:
            for who in (object(), object(), object()):
                why = ["already there"]
                out = share.slice(who, None, SlipCircle(
                    centre_x=1.0, centre_y=2.0, radius=3.0), 20, why)
                got.append((out, why))
        finally:
            S.slice_surface = real
        assert calls[0] == 1
        assert got == [(None, ["already there", "refused_outside_model"])] * 3

    def test_a_state_that_cannot_be_spelled_is_not_recorded(self):
        """A slicer that left an object on the surface: the later methods
        slice that surface themselves."""
        import ogr_slip2d.search as S
        from ogr_slip2d.search import SliceShare
        from ogr_slip2d.slicer import Slices
        from ogr_slip2d.surface import SlipCircle
        real = S.slice_surface
        calls = [0]

        def leaves_an_object(project, surface, num_slices=50, reasons=None):
            calls[0] += 1
            surface.helper = object()
            return Slices()

        share = SliceShare(followers=1)
        S.slice_surface = leaves_an_object
        try:
            for who in (object(), object()):
                share.slice(who, None,
                            SlipCircle(centre_x=1.0, centre_y=2.0,
                                       radius=3.0), 20, [])
        finally:
            S.slice_surface = real
        assert share._records == {} and calls[0] == 2
