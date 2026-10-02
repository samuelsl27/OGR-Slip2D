# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D88 — a statistical run refuses a method whose deterministic surface does not
re-evaluate to ITSELF on the project the samples run on, in either direction.

**The invariant.** The guard of v0.1.154 (``_cannot_reevaluate``) refuses a
composite deterministic surface whose samples run with Composite Surfaces
off, and only that: it cannot know the settings the deterministic surface
came from, because they do not travel with it. The other direction passed.
Measured in v0.1.238 on the notched slope of ``test_statistical_rebuild_v1154``
(Fredlund and Krahn 1977, problem 22, with a notch in its crest): with the
deterministic circle from a run with the option OFF (the notch, x from 45.84
to 49.70, F = 3.3585) and the samples with it ON, the samples answer for the
clipped deep mass and the result reported 3.3585 over a mean of 1.378
(−59 %); a Minimum Elevation set only on the samples' project gave +141 %.
Since v0.1.238 (D89) the panel says that every sample changed mass, but the
method was still published.

The question is now asked of the MECHANISM: the seed of the deterministic
surface, evaluated once on the samples' project prepared as they are and with
no sample applied, by their own evaluator, must come back with the same type
and the same extent. It is symmetric by construction and covers any setting
that decides the sliding mass.

What each class pins
--------------------
1. The two directions and the filter: refused, with the reason in
   ``notes[mid]`` and on the panel, and nothing in ``by_method``; in Global
   Minimum and in the sensitivity. The direction the old guard knew keeps its
   more specific sentence.
2. The probe changes nothing it should not: with the same project in both
   runs, the samples are the ones a run without the probe gives, bit for
   bit; the probe does not go through ``_evaluate_on`` (tests patch it to
   count samples); an exception in the probe refuses nothing; a
   deterministic surface without an extent is not probed.

No assertion fixes a factor of safety.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MID = "bishop_simplified"


def _projects():
    import test_statistical_rebuild_v1154 as V
    on = V._notched()
    off = V._without_the_option(on)
    filtered = copy.deepcopy(on)
    filtered.settings.search.min_elevation = 30.0
    return V, on, off, filtered


def _gm(samples_project, det, **kw):
    import test_statistical_rebuild_v1154 as V
    from ogr_core.statistics import SamplingMethod, run_global_minimum
    return run_global_minimum(samples_project, {_MID: det},
                              [V._cohesion_var(samples_project)],
                              num_samples=6,
                              sampling=SamplingMethod.LATIN_HYPERCUBE, seed=1,
                              num_slices=V._SLICES, **kw)


def _sweep(samples_project, det):
    import test_statistical_rebuild_v1154 as V
    from ogr_core.statistics import run_sensitivity
    return run_sensitivity(samples_project, {_MID: det},
                           [V._cohesion_var(samples_project)], intervals=2,
                           num_slices=V._SLICES)


def _refused_by_the_probe(res):
    """Behaviour first: a published method is the defect, whatever the
    sentence; only then is the sentence asked to be the probe's."""
    reason = res.notes.get(_MID, "")
    if _MID in res.by_method or not reason:
        return False
    from ogr_core.statistics.probabilistic import _NOT_ITSELF
    head = _NOT_ITSELF.split(" (", 1)[0]
    return (reason.startswith(head)
            and ("%s: %s" % (_MID, reason)) in res.note_lines)


# ======================================================================
class TestBothDirectionsAreRefused:

    def test_the_premise_the_old_guard_lets_this_direction_through(self):
        from ogr_core.statistics.probabilistic import _cannot_reevaluate
        V, on, off, _f = _projects()
        det = V._deterministic(off, _MID)
        assert type(det.surface).__name__ == "SlipCircle"
        assert _cannot_reevaluate(on, det.surface.to_dict()) is None

    def test_option_off_then_on_is_refused(self):
        V, on, off, _f = _projects()
        res = _gm(on, V._deterministic(off, _MID))
        assert _refused_by_the_probe(res), (res.notes, res.note_lines)
        reason = res.notes[_MID]
        assert "x from 56.05 to 158.73, composite" in reason, reason
        assert "instead of x from 45.84 to 49.70, circle" in reason, reason

    def test_option_on_then_off_keeps_the_specific_sentence(self):
        V, on, off, _f = _projects()
        res = _gm(off, V._deterministic(on, _MID))
        assert _MID not in res.by_method
        assert "Composite Surfaces is off" in res.notes[_MID], res.notes

    def test_a_filter_only_on_the_samples_is_refused(self):
        V, on, _off, filtered = _projects()
        res = _gm(filtered, V._deterministic(on, _MID))
        assert _refused_by_the_probe(res), (res.notes, res.note_lines)
        assert "x from 45.84 to 49.70, circle" in res.notes[_MID]

    def test_the_sensitivity_refuses_the_same_two(self):
        V, on, off, filtered = _projects()
        assert _refused_by_the_probe(_sweep(on, V._deterministic(off, _MID)))
        assert _refused_by_the_probe(
            _sweep(filtered, V._deterministic(on, _MID)))

    def test_the_reason_has_no_inner_separator(self):
        """The panel groups a line by its first ": ", which the method id
        brings; one inside the reason would be harmless today and a trap the
        day someone splits on the last one."""
        from ogr_core.statistics.probabilistic import _NOT_ITSELF
        assert ": " not in _NOT_ITSELF


# ======================================================================
class TestTheProbeChangesNothingElse:

    def test_the_same_project_gives_the_samples_a_run_without_it_gives(self):
        import ogr_core.statistics.probabilistic as P
        V, on, _off, _f = _projects()
        det = V._deterministic(on, _MID)
        with_probe = _gm(on, det)
        saved = P._does_not_reevaluate_to_itself
        P._does_not_reevaluate_to_itself = lambda *a, **k: None
        try:
            without = _gm(on, det)
        finally:
            P._does_not_reevaluate_to_itself = saved
        assert with_probe.ok and with_probe.notes == {}
        assert (with_probe.by_method[_MID].statistics.values
                == without.by_method[_MID].statistics.values)

    def test_it_does_not_go_through_evaluate_on(self):
        import ogr_core.statistics.probabilistic as P
        V, on, _off, _f = _projects()
        det = V._deterministic(on, _MID)
        calls = []
        saved = P._evaluate_on

        def counting(*a, **k):
            calls.append(1)
            return saved(*a, **k)

        P._evaluate_on = counting
        try:
            res = _gm(on, det)
        finally:
            P._evaluate_on = saved
        assert res.ok and len(calls) == 6, len(calls)

    def test_an_exception_in_the_probe_refuses_nothing(self):
        """``prepare`` raises on its first call, which is the probe's; the
        six samples run as always."""
        from ogr_core.project import prepare_analysis_project
        V, on, _off, _f = _projects()
        det = V._deterministic(on, _MID)
        seen = []

        def prepare(clone):
            seen.append(1)
            if len(seen) == 1:
                raise RuntimeError("the probe's own trouble")
            return prepare_analysis_project(clone)[0]

        res = _gm(on, det, prepare=prepare)
        assert res.ok and _MID in res.by_method, res.notes
        assert res.by_method[_MID].statistics.n == 6
        assert len(seen) == 7

    def test_a_deterministic_surface_without_extent_is_not_probed(self):
        V, on, off, _f = _projects()
        det = V._deterministic(off, _MID)
        bare = types.SimpleNamespace(
            fos=det.fos, surface={"centre_x": V._XC, "centre_y": V._YC,
                                  "radius": V._R})
        res = _gm(on, bare)
        assert res.ok and _MID in res.by_method, res.notes
