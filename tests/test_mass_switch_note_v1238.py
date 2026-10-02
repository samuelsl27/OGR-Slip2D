# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D89 — a sample that answers for ANOTHER sliding mass of the deterministic
circle is counted and said, and no number moves.

**The invariant.** Since v0.1.131 (D36) every sample re-evaluates the
deterministic circle WITHOUT its endpoints, so that it resolves its own
sliding mass, and the engine keeps the mass with the lower factor. That is
right, and it was silent: on a circle with two masses, a sampled parameter
that crosses the point where the critical mass changes makes those samples
answer for the other one. Measured in v0.1.237 on the notched slope of
``test_statistical_rebuild_v1154`` (Fredlund and Krahn 1977, problem 22,
with a notch in its crest; Composite Surfaces on in both runs), with the
cohesion of the upper soil uniform between 50 and 450 psf: 11 of 40 samples
answered for the notch (x from 45.84 to 49.70) instead of the clipped deep
mass (56.05 to 158.73), and the 10 samples below 1 were all of them among
those — the probability of failure belonged entirely to the other mass —
with ``notes`` and ``note_lines`` empty.

What each class pins, and against what
--------------------------------------
1. The two helpers read the mass and the circle of a surface, as an object
   or as its dictionary, and a different circle is never a change of mass.
2. Global Minimum: the count is the one an independent replay of the
   samples finds, the sentence names both masses and how many of the
   samples below 1 are among them, it reaches ``note_lines`` and not the
   headline, and the factors are the replay's, bit for bit (counting moves
   no number). Narrow cohesion: nothing. A deterministic surface with no
   extent: nothing to compare, nothing said.
3. Overall Slope, with a search that evaluates only the circle: the same.
4. Sensitivity: the points of the sweep that answer for the other mass are
   the replay's, one line says so, and the variable keeps its rank (a
   ``note`` would have taken it out).

No assertion fixes a factor of safety; the counts are compared with a
replay, never written down.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MID = "bishop_simplified"
_N = 40


def _model():
    import test_statistical_rebuild_v1154 as V
    return V._notched(), V


def _evaluator(p):
    from ogr_slip2d.analysis_runner import build_evaluator
    import test_statistical_rebuild_v1154 as V
    return build_evaluator(p, _MID, num_slices=V._SLICES)


def _deterministic():
    p, V = _model()
    return _evaluator(p).evaluate_circle(p, V._circle())


def _cohesion(dist):
    from ogr_core.statistics import available_variables
    p, _V = _model()
    mat = p.materials[0]
    v = [x for x in available_variables(p)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = dist
    return v


def _wide():
    from ogr_core.statistics import Distribution, DistributionType
    return _cohesion(Distribution(DistributionType.UNIFORM, mean=250.0,
                                  rel_min=200.0, rel_max=200.0))


def _narrow():
    from ogr_core.statistics import Distribution, DistributionType
    return _cohesion(Distribution(DistributionType.NORMAL, mean=600.0,
                                  std_dev=30.0, rel_min=90.0, rel_max=90.0))


def _global_minimum(var, det=None):
    from ogr_core.statistics import SamplingMethod, run_global_minimum
    p, V = _model()
    det = det if det is not None else _deterministic()
    return run_global_minimum(p, {_MID: det}, [var], num_samples=_N,
                              sampling=SamplingMethod.LATIN_HYPERCUBE,
                              seed=3, num_slices=V._SLICES)


def _replay(res, var):
    """Every counted sample again, outside the engine: ``[(fos, extent)]``."""
    from ogr_core.project import prepare_analysis_project
    from ogr_core.statistics.probabilistic import (_rebuild_surface,
                                                   counts_as_sample)
    from ogr_core.statistics.random_variables import (apply_sample,
                                                      clone_project)
    p, _V = _model()
    ev = _evaluator(p)
    seed = _rebuild_surface(_deterministic().surface.to_dict())
    out = []
    for i in range(_N):
        c = clone_project(p)
        apply_sample(c, [var], {k: v[i] for k, v in res.samples.items()})
        r = ev.evaluate_circle(prepare_analysis_project(c)[0], seed)
        if counts_as_sample(r):
            out.append((r.fos, (r.surface.x_left, r.surface.x_right)))
    return out


def _home():
    s = _deterministic().surface
    return (s.x_left, s.x_right)


# ======================================================================
class TestTheHelpers:

    def test_the_premise_the_notched_circle_changes_mass(self):
        import copy

        from ogr_core.materials.builtin_models import MohrCoulomb
        p, V = _model()
        det = _deterministic()
        assert type(det.surface).__name__ == "CompositeSurface"
        weak = copy.deepcopy(p)
        weak.materials[0].strength = MohrCoulomb(cohesion=100.0,
                                                 friction_angle=20.0)
        r = _evaluator(weak).evaluate_circle(weak, V._circle())
        assert type(r.surface).__name__ == "SlipCircle"
        assert r.surface.x_right < det.surface.x_left      # disjoint

    def test_extent_and_circle_read_objects_and_dictionaries(self):
        from ogr_core.statistics.probabilistic import _circle_of, _extent
        s = _deterministic().surface
        d = s.to_dict()
        assert _extent(s) == _extent(d) == (s.x_left, s.x_right)
        assert _circle_of(s) == _circle_of(d) == (120.0, 90.0, 80.0)
        poly = {"type": "polyline", "polyline": {"vertices": [[0, 0], [1, 1]]}}
        assert _circle_of(poly) is None and _extent(poly) is None
        bare = {"centre_x": 1.0, "centre_y": 2.0, "radius": 3.0}
        assert _circle_of(bare) == (1.0, 2.0, 3.0) and _extent(bare) is None

    def test_another_circle_is_not_a_change_of_mass(self):
        from ogr_core.statistics.probabilistic import _MassSwitches
        sw = _MassSwitches(_deterministic().surface)
        other = types.SimpleNamespace(
            fos=0.5, surface=types.SimpleNamespace(
                centre_x=121.0, centre_y=90.0, radius=80.0,
                x_left=1.0, x_right=2.0))
        same = types.SimpleNamespace(
            fos=0.5, surface=types.SimpleNamespace(
                centre_x=120.0, centre_y=90.0, radius=80.0,
                x_left=1.0, x_right=2.0))
        assert sw.see(other) is False and sw.count == 0
        assert sw.see(same) is True and sw.count == 1 and sw.below_one == 1


# ======================================================================
class TestGlobalMinimumSaysIt:

    def test_the_count_is_the_replay_s(self):
        var = _wide()
        res = _global_minimum(var)
        m = res.by_method[_MID]
        home = _home()
        replay = _replay(res, var)
        switched = [f for f, ext in replay if ext != home]
        assert switched, "premise: the wide cohesion crosses the switch"
        assert m.mass_switches == len(switched)
        assert m.summary()["mass_switches"] == len(switched)

    def test_no_number_moves(self):
        var = _wide()
        res = _global_minimum(var)
        replay = _replay(res, var)
        assert res.by_method[_MID].statistics.values == [f for f, _ in replay]

    def test_the_sentence_names_both_masses_and_the_failures(self):
        var = _wide()
        res = _global_minimum(var)
        m = res.by_method[_MID]
        replay = _replay(res, var)
        home = _home()
        below = [ext != home for f, ext in replay if f < 1.0]
        note = m.notes["mass_switch"]
        assert "x from 45.84 to 49.70" in note, note
        assert "not for its own (x from 56.05 to 158.73)" in note, note
        assert "%d of %d samples" % (m.mass_switches, len(replay)) in note
        assert "%d of the %d with a factor below 1" % (sum(below),
                                                       len(below)) in note

    def test_it_reaches_the_panel_and_not_the_headline(self):
        res = _global_minimum(_wide())
        line = "%s: %s" % (_MID, res.by_method[_MID].notes["mass_switch"])
        assert res.note_lines == [line], res.note_lines
        assert "warning" not in res.notes and "error" not in res.notes

    def test_a_narrow_cohesion_says_nothing(self):
        res = _global_minimum(_narrow())
        m = res.by_method[_MID]
        assert m.mass_switches == 0
        assert "mass_switch" not in m.notes
        assert res.note_lines == []

    def test_a_deterministic_surface_without_extent_is_not_watched(self):
        """The bare-dictionary contract of ``run_global_minimum``: a circle
        with no extent names no mass, so there is nothing to compare."""
        det = _deterministic()
        bare = types.SimpleNamespace(
            fos=det.fos, surface={"centre_x": 120.0, "centre_y": 90.0,
                                  "radius": 80.0})
        res = _global_minimum(_wide(), det=bare)
        m = res.by_method[_MID]
        assert m.statistics.n == _N
        assert m.mass_switches == 0 and "mass_switch" not in m.notes


# ======================================================================
class _OnlyTheCircle:
    """A search that evaluates the deterministic circle and nothing else,
    so the critical surface of every sample is that circle's answer."""

    SAME_SURFACES_EVERY_SAMPLE = True

    def run(self, project):
        p, V = _model()
        r = _evaluator(p).evaluate_circle(project, V._circle())
        return types.SimpleNamespace(critical=r, evaluations=[r],
                                     objective="fos", optimized=None,
                                     steered=[])


class TestOverallSlopeSaysIt:

    def _run(self, var):
        from ogr_core.statistics import SamplingMethod, run_overall_slope
        p, _V = _model()
        return run_overall_slope(p, lambda mid: _OnlyTheCircle(), [var],
                                 [_MID], num_samples=_N,
                                 sampling=SamplingMethod.LATIN_HYPERCUBE,
                                 seed=3, deterministic={_MID: _deterministic()})

    def test_the_count_and_the_sentence(self):
        var = _wide()
        res = self._run(var)
        o = res.by_method[_MID]
        home = _home()
        switched = [f for f, ext in _replay(res, var) if ext != home]
        assert switched and o.mass_switches == len(switched)
        assert o.summary()["mass_switches"] == len(switched)
        assert "x from 45.84 to 49.70" in o.notes["mass_switch"]
        assert ("%s: %s" % (_MID, o.notes["mass_switch"])) in res.note_lines

    def test_a_narrow_cohesion_says_nothing(self):
        res = self._run(_narrow())
        o = res.by_method[_MID]
        assert o.mass_switches == 0 and "mass_switch" not in o.notes
        assert res.note_lines == []


# ======================================================================
class TestTheSweepSaysIt:

    def _sweep(self, var):
        from ogr_core.statistics import run_sensitivity
        p, V = _model()
        return run_sensitivity(p, {_MID: _deterministic()}, [var],
                               num_slices=V._SLICES)

    def test_the_points_are_the_replay_s_and_the_variable_keeps_its_rank(self):
        from ogr_core.project import prepare_analysis_project
        from ogr_core.statistics.probabilistic import _rebuild_surface
        from ogr_core.statistics.random_variables import clone_project
        from ogr_core.statistics.sensitivity import set_value
        var = _wide()
        res = self._sweep(var)
        vs = res.by_method[_MID][var.key]
        p, _V = _model()
        ev = _evaluator(p)
        seed = _rebuild_surface(_deterministic().surface.to_dict())
        home, other = _home(), []
        for x in vs.values:
            c = clone_project(p)
            set_value(c, var, x)
            r = ev.evaluate_circle(prepare_analysis_project(c)[0], seed)
            if (r.surface.x_left, r.surface.x_right) != home:
                other.append(x)
        assert other and vs.mass_switch_values == other
        assert vs.note == ""
        assert var.key in [k for k, _l, _s in res.ranking(_MID)]
        lines = [ln for ln in res.note_lines if "The sweep of" in ln]
        assert len(lines) == 1, res.note_lines
        assert lines[0].startswith(_MID + ": The sweep of ")
        assert "at %d of %d points" % (len(other), vs.n) in lines[0]
        assert "x from 45.84 to 49.70" in lines[0]

    def test_a_narrow_sweep_says_nothing(self):
        var = _narrow()
        res = self._sweep(var)
        assert res.by_method[_MID][var.key].mass_switch_values == []
        assert res.note_lines == []
