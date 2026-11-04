# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.426 (D377) — Simulated Annealing and the Particle Swarm evaluate a
candidate once per run, and count their effort as the other searches do.

WHAT INVARIANTS THIS PROTECTS
-----------------------------
Measured with the compute audit's probe S8 (0.1.377):

* Simulated Annealing on validation case 002 (Spencer, seed 1234, 300
  steps, with the walk): 540 evaluations, 438 distinct, 102 exact repeats.
  At the ends of the surface ``_lmc`` moves x alone, so three of its eight
  directions give the same candidate and two give the current surface;
* the swarm of bank problem 104: 31 repeats, and ``attempts -
  total_count`` = 2500 - 2535 = -35 with nothing outside the focus,
  because the final report evaluated every particle's best again and
  counted it.

The owner's decisions (2026-11-04):

* A — a repeat is not evaluated again: its recorded result is kept again
  and what the evaluation did to the run state is done again. NO number
  may move: the population, every counter, the notes and the critical
  surface are those of evaluating it twice. Checked by an A/B in the same
  process (``_REUSE_DUPLICATES`` off and on), evaluation by evaluation,
  and the evaluations saved are exactly the repeats, counted from the run
  with the reuse off;
* C — ``attempts - total_count == focus_rejected`` in the swarm and in the
  annealing, with a focus and without one. For the annealing that retires
  the v0.1.187 rule ("the population is K x Ngen"): on case 002 those were
  117 inner steps while 661 candidates were evaluated. ``attempts`` is now
  every candidate, which is also checked against a count made from outside.

THIS IS NOT A SNAPSHOT TEST
---------------------------
No factor and no count is pinned: each run is compared with its twin, and
each counter with a count made from outside the code under test.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_search_effort_focus_v1187 import _slope, _tangent  # noqa: E402

from ogr_slip2d import search as S  # noqa: E402
from ogr_slip2d.methods.base import method_registry  # noqa: E402
from ogr_slip2d.particle_swarm import ParticleSwarmSearch  # noqa: E402

_CASE_002 = (Path(__file__).resolve().parent.parent / "validacion" / "casos"
             / "002-yamagami-ueta-1988" / "modelo.ogr")


# ----------------------------------------------------------------------
# The fingerprint of a run, as ``test_slice_share_v1397`` takes it, and
# down to the vertices: a polyline compares with ``==`` and carries an id
# of its own, so two runs would never agree on a non-circular surface.
def _hexed(v):
    if isinstance(v, float):
        return v.hex()
    if isinstance(v, (list, tuple)):
        return [_hexed(x) for x in v]
    if isinstance(v, dict):
        return sorted((k, _hexed(x)) for k, x in v.items())
    if hasattr(v, "vertices"):
        return ("polyline", [_hexed(x) for x in v.vertices],
                getattr(v, "closed", None))
    if hasattr(v, "x") and hasattr(v, "y"):
        return ("vertex", _hexed(float(v.x)), _hexed(float(v.y)),
                type(v.x).__name__, type(v.y).__name__)
    return v


def _evaluation(e):
    surface = sorted((k, _hexed(v)) for k, v in vars(e.surface).items()
                     if k != "id")
    slices = e.slices
    return (_hexed(e.fos), e.converged, e.iterations, e.is_valid,
            e.admissible, e.error_message, surface,
            None if slices is None else [
                sorted((k, _hexed(v)) for k, v in vars(s).items()
                       if k not in ("material", "water_material"))
                for s in slices.slices])


def _result(r):
    crit = r.critical
    return ([_evaluation(e) for e in r.evaluations], r.valid_count,
            r.invalid_count, r.attempts, r.focus_rejected,
            sorted(getattr(r, "notes", None) or []),
            None if crit is None else _evaluation(crit))


class _Reuse:
    """``_REUSE_DUPLICATES`` set for the block, and put back."""

    def __init__(self, on):
        self.on = on

    def __enter__(self):
        # read with a default, so that in a tree without the switch the
        # cases fail by what the search does and not by a missing name
        self._had = "_REUSE_DUPLICATES" in vars(S.BaseSearch)
        self._before = getattr(S.BaseSearch, "_REUSE_DUPLICATES", None)
        S.BaseSearch._REUSE_DUPLICATES = self.on

    def __exit__(self, *_exc):
        if self._had:
            S.BaseSearch._REUSE_DUPLICATES = self._before
        else:
            del S.BaseSearch._REUSE_DUPLICATES


class _Count:
    """Count the real evaluations of ``owner.name``, and the keys asked."""

    def __init__(self, owner, name, key):
        self.owner, self.name, self.key = owner, name, key
        self.keys = []

    def __enter__(self):
        self._orig = getattr(self.owner, self.name)
        orig, keys, key = self._orig, self.keys, self.key

        def counted(this, *args):
            keys.append(key(*args))
            return orig(this, *args)
        setattr(self.owner, self.name, counted)
        return self

    def __exit__(self, *_exc):
        setattr(self.owner, self.name, self._orig)


def _key(values):
    """The test's own key, bits and types (not the engine's ``_bits_key``,
    so the tree before the fix fails by behaviour, not by a missing
    name)."""
    import struct
    values = list(values)
    return (struct.pack("<%dd" % len(values), *values),
            tuple(map(type, values)))


def _sa_key(_project, verts):
    return _key(c for v in verts for c in (v.x, v.y))


def _pso_key(_project, circle):
    """The swarm is counted where it pays: ``evaluate_circle``."""
    return _key((circle.centre_x, circle.centre_y, circle.radius))


def _annealing(project=None, **kw):
    kw.setdefault("method", method_registry()["bishop_simplified"]())
    return S.SimulatedAnnealingSearch(initial_vertices=7,
                                      generation_steps=80, num_slices=15,
                                      seed=1234, **kw)


def _swarm(**kw):
    kw.setdefault("method", method_registry()["bishop_simplified"]())
    return ParticleSwarmSearch(num_particles=10, num_iterations=8,
                               num_slices=15, seed=7, **kw)


_SHARED: dict = {}


def _case_002():
    if "002" not in _SHARED:
        from ogr_core.project import Project
        _SHARED["002"] = Project.load(str(_CASE_002))
    return _SHARED["002"]


def _ab(build, project, owner, name, key):
    """The same run with the reuse off and on, and the real evaluations of
    each: ``(off, on, keys off, keys on)``."""
    with _Reuse(False), _Count(owner, name, key) as c_off:
        off = build().run(project)
    with _Reuse(True), _Count(owner, name, key) as c_on:
        on = build().run(project)
    return off, on, c_off.keys, c_on.keys


# ======================================================================
class TestARepeatIsNotEvaluatedAgain:

    def test_the_annealing(self):
        p = _case_002()
        off, on, k_off, k_on = _ab(_annealing, p, S.SimulatedAnnealingSearch,
                                   "_evaluate_polyline", _sa_key)
        repeats = len(k_off) - len(set(k_off))
        assert repeats > 0, "no repeat: nothing measured"
        assert len(k_on) == len(set(k_off))         # each one once
        assert _result(on) == _result(off)          # and nothing moved

    def test_the_swarm(self):
        p = _slope()
        off, on, k_off, k_on = _ab(_swarm, p, ParticleSwarmSearch,
                                   "evaluate_circle", _pso_key)
        repeats = len(k_off) - len(set(k_off))
        assert repeats > 0, "no repeat: nothing measured"
        assert len(k_on) == len(set(k_off))
        assert _result(on) == _result(off)
        assert [_evaluation(m) for m in on.minima] == \
            [_evaluation(m) for m in off.minima]

    def test_the_global_generator_is_not_touched(self):
        """Rule 5, which the annealing already kept (v0.1.119): the reuse
        draws nothing either."""
        import random
        state = random.getstate()
        _annealing().run(_case_002())
        _swarm().run(_slope())
        assert random.getstate() == state


# ======================================================================
class TestTheEffortIsAnIdentity:
    """``attempts - total_count == focus_rejected``, and ``attempts`` is
    every candidate, counted from outside with the reuse off."""

    def _check(self, run, candidates):
        assert run.attempts == candidates, (run.attempts, candidates)
        assert run.attempts - run.total_count == run.focus_rejected, (
            run.attempts, run.total_count, run.focus_rejected)

    def test_the_annealing_without_a_focus(self):
        p = _case_002()
        with _Reuse(False), _Count(S.SimulatedAnnealingSearch,
                                   "_evaluate_polyline", _sa_key) as c:
            run = _annealing().run(p)
        assert run.focus_rejected == 0
        self._check(run, len(c.keys))
        assert run.invalid_count > 0, "every candidate valid: no measure"

    def test_the_annealing_with_a_focus(self):
        p = _slope()
        with _Reuse(False), _Count(S.SimulatedAnnealingSearch,
                                   "_evaluate_polyline", _sa_key) as c:
            run = _annealing(focus_objects=[_tangent()]).run(p)
        assert run.focus_rejected > 0, "the focus rejected nothing"
        self._check(run, len(c.keys))

    def test_the_swarm_without_a_focus(self):
        run = _swarm().run(_slope())
        assert run.focus_rejected == 0
        self._check(run, 10 * 8)

    def test_the_swarm_with_a_focus(self):
        run = _swarm(focus_objects=[_tangent()]).run(_slope())
        assert run.focus_rejected > 0, "the focus rejected nothing"
        self._check(run, 10 * 8)


def _optimize():
    """Optimize Surfaces on, with a short walk: what is under test is the
    count of the surfaces it adds, not where it ends."""
    from ogr_slip2d.optimize import OptimizeSettings
    return OptimizeSettings(enabled=True, max_iterations=150)


class TestOptimizeCountsWhatItAdds:
    """Every surface Optimize adds is an attempt too (owner's decision,
    2026-11-04): counted as valid and not as tried, it left every search
    with Optimize one below the identity per surface it added (bank
    problem 104: -4 once the report was fixed; case 002: -1). Optimize is
    on by default for the annealing and the swarm."""

    def test_the_annealing(self):
        p = _case_002()
        s = _annealing(optimize=_optimize(), optimize_seed=13)
        with _Reuse(False), _Count(S.SimulatedAnnealingSearch,
                                   "_evaluate_polyline", _sa_key) as c:
            run = s.run(p)
        added = len(run.steered)
        assert added > 0, "Optimize added nothing: no measure"
        TestTheEffortIsAnIdentity()._check(run, len(c.keys) + added)

    def test_the_swarm(self):
        run = _swarm(optimize=_optimize(), optimize_seed=13).run(_slope())
        added = len(run.steered)
        assert added > 0, "Optimize added nothing: no measure"
        TestTheEffortIsAnIdentity()._check(run, 10 * 8 + added)
