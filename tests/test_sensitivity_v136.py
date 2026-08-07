# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.36 — Sensitivity analysis (Phase P4).

Follows the reference specification: the range between the actual
minimum and maximum (derived from the RELATIVE values) is divided into
50 equal intervals, the factor of safety is recomputed on the global
minimum surface at each value, and **all other variables are held at
their mean** while one is swept.

The decisive check is the last of those: when the swept variable passes
through its own mean, the whole model is back at its deterministic state,
so the computed factor of safety must equal the deterministic one. Any
leakage between variables would break that identity.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    VariableKind as VK,
    available_variables,
    run_sensitivity,
)
from ogr_slip2d import BishopSimplified, Spencer  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402


def _deterministic(project, methods=("bishop_simplified",)):
    factory = {"bishop_simplified": BishopSimplified, "spencer": Spencer}
    out = {}
    for mid in methods:
        out[mid] = GridSearch(
            method=factory[mid](), grid_x=(70, 100), grid_y=(60, 85),
            grid_nx=4, grid_ny=4, radius_increment=6, min_radius=15,
            num_slices=18, min_area=0.5).run(project).critical
    return out


def _var(project, param, kind, mean, rel_min, rel_max):
    mat = project.materials[0]
    for v in available_variables(project):
        if v.param != param or v.kind != kind:
            continue
        if kind != VK.SEISMIC and v.target_id != mat.id:
            continue
        v.distribution = Distribution(DT.UNIFORM, mean=mean,
                                      rel_min=rel_min, rel_max=rel_max)
        return v
    raise AssertionError(param)


class TestSweepMechanics:
    def test_fifty_intervals_by_default(self):
        p = _ej1_project()
        res = run_sensitivity(
            p, _deterministic(p),
            [_var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 8.0, 8.0)],
            num_slices=18)
        assert res.intervals == 50
        vs = next(iter(res.by_method["bishop_simplified"].values()))
        assert vs.n == 51

    def test_custom_interval_count(self):
        p = _ej1_project()
        res = run_sensitivity(
            p, _deterministic(p),
            [_var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 8.0, 8.0)],
            intervals=10, num_slices=18)
        vs = next(iter(res.by_method["bishop_simplified"].values()))
        assert vs.n == 11

    def test_range_matches_relative_limits(self):
        """actual min = mean - rel_min, actual max = mean + rel_max."""
        p = _ej1_project()
        v = _var(p, "friction_angle", VK.MATERIAL_STRENGTH, 25.0, 10.0,
                 10.0)
        res = run_sensitivity(p, _deterministic(p), [v], intervals=20,
                              num_slices=18)
        vs = res.by_method["bishop_simplified"][v.key]
        assert abs(vs.values[0] - 15.0) < 1e-9
        assert abs(vs.values[-1] - 35.0) < 1e-9

    def test_asymmetric_range(self):
        p = _ej1_project()
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 5.0, 12.0)
        res = run_sensitivity(p, _deterministic(p), [v], intervals=10,
                              num_slices=18)
        vs = res.by_method["bishop_simplified"][v.key]
        assert abs(vs.values[0] - 10.0) < 1e-9
        assert abs(vs.values[-1] - 27.0) < 1e-9

    def test_values_are_evenly_spaced(self):
        p = _ej1_project()
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 6.0, 6.0)
        res = run_sensitivity(p, _deterministic(p), [v], intervals=12,
                              num_slices=18)
        vs = res.by_method["bishop_simplified"][v.key]
        steps = [b - a for a, b in zip(vs.values, vs.values[1:])]
        assert max(steps) - min(steps) < 1e-9


class TestOtherVariablesHeldAtMean:
    def test_midpoint_reproduces_the_deterministic_factor(self):
        """THE key check: at its own mean the model is back to the
        deterministic state, so the factor of safety must match."""
        p = _ej1_project()
        det = _deterministic(p)
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 6.0, 6.0)
        res = run_sensitivity(p, det, [v], intervals=10, num_slices=18)
        vs = res.by_method["bishop_simplified"][v.key]
        mid = vs.n // 2
        assert abs(vs.values[mid] - 15.0) < 1e-9
        assert abs(vs.fos[mid] - det["bishop_simplified"].fos) < 1e-6

    def test_sweeping_one_variable_does_not_move_the_others(self):
        """With several variables selected, each sweep must still pass
        through the deterministic factor at its own mean — impossible if
        the sweeps leaked into one another."""
        p = _ej1_project()
        det = _deterministic(p)
        variables = [
            _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 6.0, 6.0),
            _var(p, "friction_angle", VK.MATERIAL_STRENGTH, 25.0, 8.0,
                 8.0),
            _var(p, "unit_weight", VK.MATERIAL, 20.0, 3.0, 3.0),
        ]
        res = run_sensitivity(p, det, variables, intervals=10,
                              num_slices=18)
        f_det = det["bishop_simplified"].fos
        for vs in res.by_method["bishop_simplified"].values():
            mid = vs.n // 2
            assert abs(vs.fos[mid] - f_det) < 1e-6, vs.label

    def test_project_is_not_modified(self):
        p = _ej1_project()
        before = p.to_dict()
        run_sensitivity(
            p, _deterministic(p),
            [_var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 6.0, 6.0)],
            intervals=10, num_slices=18)
        assert p.to_dict() == before


class TestPhysicalDirections:
    def _sweep(self, param, kind, mean, lo, hi):
        p = _ej1_project()
        v = _var(p, param, kind, mean, lo, hi)
        res = run_sensitivity(p, _deterministic(p), [v], intervals=15,
                              num_slices=18)
        return res.by_method["bishop_simplified"][v.key]

    def test_cohesion_increases_the_factor(self):
        vs = self._sweep("cohesion", VK.MATERIAL_STRENGTH, 15.0, 10.0,
                         10.0)
        assert vs.is_increasing
        assert vs.fos[-1] > vs.fos[0]

    def test_friction_angle_increases_the_factor(self):
        vs = self._sweep("friction_angle", VK.MATERIAL_STRENGTH, 25.0,
                         10.0, 10.0)
        assert vs.is_increasing

    def test_seismic_decreases_the_factor(self):
        vs = self._sweep("kh", VK.SEISMIC, 0.05, 0.05, 0.15)
        assert not vs.is_increasing
        assert vs.fos[-1] < vs.fos[0]

    def test_monotone_response_for_strength(self):
        vs = self._sweep("cohesion", VK.MATERIAL_STRENGTH, 15.0, 10.0,
                         10.0)
        for a, b in zip(vs.fos, vs.fos[1:]):
            assert b >= a - 1e-9


class TestRankingAndDerived:
    def _run(self):
        p = _ej1_project()
        variables = [
            _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 10.0, 10.0),
            _var(p, "friction_angle", VK.MATERIAL_STRENGTH, 25.0, 10.0,
                 10.0),
            _var(p, "unit_weight", VK.MATERIAL, 20.0, 3.0, 3.0),
        ]
        return run_sensitivity(p, _deterministic(p), variables,
                               intervals=15, num_slices=18)

    def test_ranking_is_sorted_by_influence(self):
        res = self._run()
        rows = res.ranking()
        assert len(rows) == 3
        spans = [r[2] for r in rows]
        assert spans == sorted(spans, reverse=True)

    def test_ranking_matches_fos_range(self):
        res = self._run()
        sweeps = res.by_method["bishop_simplified"]
        for key, _label, span in res.ranking():
            assert abs(sweeps[key].fos_range - span) < 1e-12

    def test_unit_weight_is_least_influential_here(self):
        """A physically expected outcome for this model: strength
        parameters dominate over unit weight."""
        res = self._run()
        rows = res.ranking()
        assert "unit_weight" in rows[-1][1]

    def test_percent_of_range_spans_zero_to_hundred(self):
        res = self._run()
        vs = next(iter(res.by_method["bishop_simplified"].values()))
        pct = vs.percent_of_range()
        assert abs(pct[0]) < 1e-9
        assert abs(pct[-1] - 100.0) < 1e-9
        assert all(b >= a for a, b in zip(pct, pct[1:]))

    def test_crossing_interpolation(self):
        """The reported crossing value must actually bracket FS = 1."""
        p = _ej1_project()
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 12.0, 12.0)
        res = run_sensitivity(p, _deterministic(p), [v], intervals=30,
                              num_slices=18)
        vs = res.by_method["bishop_simplified"][v.key]
        x = vs.crossing(1.0)
        assert x is not None
        assert vs.values[0] <= x <= vs.values[-1]
        assert vs.min_fos < 1.0 < vs.max_fos

    def test_crossing_returns_none_when_never_reached(self):
        p = _ej1_project()
        v = _var(p, "unit_weight", VK.MATERIAL, 20.0, 1.0, 1.0)
        res = run_sensitivity(p, _deterministic(p), [v], intervals=8,
                              num_slices=18)
        vs = res.by_method["bishop_simplified"][v.key]
        assert vs.crossing(5.0) is None

    def test_multiple_methods(self):
        p = _ej1_project()
        det = _deterministic(p, ("bishop_simplified", "spencer"))
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 8.0, 8.0)
        res = run_sensitivity(p, det, [v], intervals=8, num_slices=18)
        assert set(res.by_method) == {"bishop_simplified", "spencer"}
        for mid in res.by_method:
            assert abs(res.by_method[mid][v.key].deterministic_fos
                       - det[mid].fos) < 1e-12


class TestErrorHandling:
    def test_no_variable_with_a_range(self):
        p = _ej1_project()
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 0.0, 0.0)
        res = run_sensitivity(p, _deterministic(p), [v], num_slices=18)
        assert not res.ok
        assert "range" in res.notes["error"].lower()

    def test_no_deterministic_result(self):
        p = _ej1_project()
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 5.0, 5.0)
        res = run_sensitivity(p, {}, [v], num_slices=18)
        assert not res.ok
        assert "deterministic" in res.notes["error"].lower()

    def test_progress_callback_completes(self):
        p = _ej1_project()
        v = _var(p, "cohesion", VK.MATERIAL_STRENGTH, 15.0, 5.0, 5.0)
        seen = []
        run_sensitivity(p, _deterministic(p), [v], intervals=10,
                        num_slices=18,
                        progress_cb=lambda d, t: seen.append((d, t)))
        assert seen and seen[-1][0] == seen[-1][1]

    def test_empty_sweep_is_safe(self):
        vs_cls = __import__(
            "ogr_core.statistics.sensitivity", fromlist=["x"]
        ).VariableSensitivity
        vs = vs_cls()
        assert vs.n == 0
        assert math.isnan(vs.min_fos)
        assert vs.fos_range == 0.0
        assert vs.crossing() is None
