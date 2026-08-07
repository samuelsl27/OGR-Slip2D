# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.34 — Random variables (Phase P1 of the probabilistic plan).

Checks that a random-variable definition:

* enumerates every parameter the reference allows to be randomised;
* reads and writes the RIGHT parameter of the RIGHT object, across the
  different storage conventions in the model (strength parameters live
  in a dict, material and support parameters are attributes, loads are
  dataclasses);
* is applied to a COPY, never to the user's project;
* actually changes the computed factor of safety, in the physically
  expected direction;
* honours the declared c-phi correlation while preserving marginals;
* survives serialisation.
"""
from __future__ import annotations

import statistics as pystat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    RandomVariable,
    SamplingMethod as SM,
    VariableKind as VK,
    apply_sample,
    available_variables,
    clone_project,
    get_value,
    sample_project_variables,
    set_value,
)
from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)


def _ev(project):
    return GridSearch(method=BishopSimplified(), num_slices=20,
                      min_area=0.0).evaluate_circle(project, _CIRCLE)


def _var(project, kind, param, mat_index=0):
    target = (project.materials[mat_index].id
              if kind in (VK.MATERIAL_STRENGTH, VK.MATERIAL,
                          VK.HYDRAULIC) else "")
    for v in available_variables(project):
        if v.kind == kind and v.param == param and v.target_id == target:
            return v
    raise AssertionError(f"variable not found: {kind} {param}")


class TestEnumeration:
    def test_finds_strength_material_and_seismic(self):
        p = _ej1_project()
        kinds = {v.kind for v in available_variables(p)}
        assert VK.MATERIAL_STRENGTH in kinds
        assert VK.MATERIAL in kinds
        assert VK.SEISMIC in kinds

    def test_cohesion_and_friction_present_per_material(self):
        p = _ej1_project()
        av = available_variables(p)
        for m in p.materials:
            params = {v.param for v in av
                      if v.kind == VK.MATERIAL_STRENGTH
                      and v.target_id == m.id}
            assert "cohesion" in params and "friction_angle" in params

    def test_mean_preset_to_current_value(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        assert abs(v.distribution.mean
                   - p.materials[0].strength.params["cohesion"]) < 1e-12

    def test_labels_are_human_readable(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        assert p.materials[0].name in v.label

    def test_hydraulic_only_when_defined(self):
        from ogr_core.hydraulic import HydraulicProperties
        p = _ej1_project()
        assert not any(v.kind == VK.HYDRAULIC
                       for v in available_variables(p))
        p.materials[0].hydraulic = HydraulicProperties(ks=1e-5)
        assert any(v.kind == VK.HYDRAULIC and v.param == "ks"
                   for v in available_variables(p))

    def test_water_table_offset_when_present(self):
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        p = _ej1_project()
        p.boundaries.append(Boundary(
            btype=BoundaryType.WATER_TABLE,
            polyline=Polyline(vertices=[Vertex(0, 30), Vertex(120, 20)],
                              closed=False)))
        assert any(v.kind == VK.WATER_TABLE
                   for v in available_variables(p))


class TestReadWrite:
    def test_strength_parameter(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        assert set_value(p, v, 33.0)
        assert abs(p.materials[0].strength.params["cohesion"] - 33.0) < 1e-9
        assert abs(get_value(p, v) - 33.0) < 1e-9

    def test_material_attribute(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL, "unit_weight")
        assert set_value(p, v, 21.5)
        assert abs(p.materials[0].unit_weight - 21.5) < 1e-9

    def test_seismic_enables_itself(self):
        """Setting a non-zero coefficient must also switch the seismic
        load on, otherwise the sample would be silently ignored."""
        p = _ej1_project()
        v = _var(p, VK.SEISMIC, "kh")
        assert p.seismic.enabled is False
        assert set_value(p, v, 0.15)
        assert abs(p.seismic.kh - 0.15) < 1e-9
        assert p.seismic.enabled is True

    def test_hydraulic_parameter(self):
        from ogr_core.hydraulic import HydraulicProperties
        p = _ej1_project()
        p.materials[0].hydraulic = HydraulicProperties(ks=1e-5)
        v = _var(p, VK.HYDRAULIC, "ks")
        assert set_value(p, v, 3e-6)
        assert abs(p.materials[0].hydraulic.ks - 3e-6) < 1e-18

    def test_water_table_offset_shifts_every_vertex(self):
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        p = _ej1_project()
        p.boundaries.append(Boundary(
            btype=BoundaryType.WATER_TABLE,
            polyline=Polyline(vertices=[Vertex(0, 30), Vertex(120, 20)],
                              closed=False)))
        v = _var(p, VK.WATER_TABLE, "offset")
        assert set_value(p, v, -2.5)
        wt = [b for b in p.boundaries
              if b.btype == BoundaryType.WATER_TABLE][0]
        ys = [q.y for q in wt.polyline.vertices]
        assert abs(ys[0] - 27.5) < 1e-9 and abs(ys[1] - 17.5) < 1e-9

    def test_missing_target_returns_false(self):
        p = _ej1_project()
        rv = RandomVariable(kind=VK.MATERIAL_STRENGTH,
                            target_id="does-not-exist", param="cohesion")
        assert get_value(p, rv) is None
        assert set_value(p, rv, 1.0) is False

    def test_unknown_parameter_returns_false(self):
        p = _ej1_project()
        rv = RandomVariable(kind=VK.MATERIAL,
                            target_id=p.materials[0].id, param="nonsense")
        assert set_value(p, rv, 1.0) is False


class TestIsolationAndEffect:
    def test_apply_sample_does_not_touch_the_original(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        before = p.materials[0].strength.params["cohesion"]
        clone = clone_project(p)
        assert apply_sample(clone, [v], {v.key: before + 10.0}) == 1
        assert abs(clone.materials[0].strength.params["cohesion"]
                   - (before + 10.0)) < 1e-9
        assert abs(p.materials[0].strength.params["cohesion"]
                   - before) < 1e-12

    def test_cohesion_raises_the_factor_of_safety(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        fos = []
        for c in (6.0, 15.0, 24.0):
            clone = clone_project(p)
            set_value(clone, v, c)
            fos.append(_ev(clone).fos)
        assert fos[0] < fos[1] < fos[2], fos

    def test_seismic_lowers_the_factor_of_safety(self):
        p = _ej1_project()
        v = _var(p, VK.SEISMIC, "kh")
        fos = []
        for kh in (0.0, 0.1, 0.2):
            clone = clone_project(p)
            set_value(clone, v, kh)
            fos.append(_ev(clone).fos)
        assert fos[0] > fos[1] > fos[2], fos

    def test_apply_sample_counts_written_parameters(self):
        p = _ej1_project()
        good = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        bad = RandomVariable(kind=VK.MATERIAL_STRENGTH,
                             target_id="ghost", param="cohesion")
        clone = clone_project(p)
        n = apply_sample(clone, [good, bad],
                         {good.key: 12.0, bad.key: 5.0})
        assert n == 1


class TestSamplingWithCorrelation:
    def _pair(self, rho=-0.6, n=2000):
        p = _ej1_project()
        c = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        f = _var(p, VK.MATERIAL_STRENGTH, "friction_angle")
        c.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=2.0,
                                      rel_min=5.0, rel_max=5.0)
        f.distribution = Distribution(DT.NORMAL, mean=25.0, std_dev=3.0,
                                      rel_min=8.0, rel_max=8.0)
        f.correlated_with = c.key
        f.correlation = rho
        return c, f, sample_project_variables(
            [c, f], n, SM.LATIN_HYPERCUBE, seed=5)

    def test_correlation_is_applied(self):
        c, f, s = self._pair(-0.6)
        got = pystat.correlation(s[c.key], s[f.key])
        assert abs(got + 0.6) < 0.05, got

    def test_marginals_are_preserved(self):
        c, f, s = self._pair(-0.6)
        assert abs(pystat.mean(s[c.key]) - 15.0) < 0.1
        assert abs(pystat.mean(s[f.key]) - 25.0) < 0.15
        assert abs(pystat.stdev(s[f.key]) - 3.0) < 0.2

    def test_uncorrelated_by_default(self):
        _c, _f, s = self._pair(0.0, n=1500)
        keys = list(s)
        assert abs(pystat.correlation(s[keys[0]], s[keys[1]])) < 0.1

    def test_deterministic_variables_are_skipped(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        v.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=2.0,
                                      rel_min=0.0, rel_max=0.0)
        assert sample_project_variables([v], 10, SM.MONTE_CARLO,
                                        seed=1) == {}

    def test_sample_count(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        v.distribution = Distribution(DT.UNIFORM, mean=15.0, rel_min=5.0,
                                      rel_max=5.0)
        s = sample_project_variables([v], 250, SM.LATIN_HYPERCUBE, seed=2)
        assert len(s[v.key]) == 250


class TestSerialisation:
    def test_round_trip(self):
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        v.distribution = Distribution(DT.LOGNORMAL, mean=15.0,
                                      std_dev=2.0, rel_min=6.0,
                                      rel_max=9.0)
        v.correlated_with = "other"
        v.correlation = -0.5
        v2 = RandomVariable.from_dict(v.to_dict())
        assert v2.key == v.key
        assert v2.kind == VK.MATERIAL_STRENGTH
        assert v2.distribution.dist_type == DT.LOGNORMAL
        assert abs(v2.correlation + 0.5) < 1e-12
        assert v2.correlated_with == "other"

    def test_key_is_unique_per_target_and_param(self):
        p = _ej1_project()
        keys = {v.key for v in available_variables(p)}
        assert len(keys) == len(available_variables(p))

    def test_project_round_trip(self):
        from ogr_core.project import Project
        p = _ej1_project()
        v = _var(p, VK.MATERIAL_STRENGTH, "cohesion")
        v.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=2.0,
                                      rel_min=5.0, rel_max=5.0)
        p.random_variables = [v]
        p2 = Project.from_dict(p.to_dict())
        assert len(p2.random_variables) == 1
        assert p2.random_variables[0].key == v.key
        assert abs(p2.random_variables[0].distribution.std_dev - 2.0) < 1e-12

    def test_project_without_variables(self):
        from ogr_core.project import Project
        assert Project.from_dict(Project(name="x").to_dict()
                                 ).random_variables == []
