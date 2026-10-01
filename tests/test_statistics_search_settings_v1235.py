# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A statistical run evaluates every sample with the search the PROJECT
configures, not with a bare one.

WHAT INVARIANT THIS PROTECTS. A probabilistic or sensitivity run takes the
deterministic critical surface of each method and evaluates it again on every
sampled copy of the model. Until v0.1.235 that second evaluation went through a
``GridSearch`` built by hand in ``probabilistic.py`` and ``sensitivity.py``:
the configured method and the admissibility screens, but none of the rest of
what ``analysis_runner.build_search`` hands every search — the Surface Filters
(Minimum Elevation, Minimum Depth), the Slope Limits, the focus objects, the
seismic mode and the Minimum Area. Defect D92. It is the third door of a fault
already closed twice: v0.1.74 for the searches, v0.1.108 for the methods.

WHY IT MATTERS AND NOT ONLY IN PRINCIPLE. A circle can cut the ground more than
twice and define more than one sliding mass; the engine answers for the lowest
mass that its filters allow. On the notched model below the deterministic run
honours a Minimum Elevation of 30 ft and answers for the SHALLOW mass, and the
bare search answered every sample for the DEEP one, the very mass the filter
removed: 1.38202 against 3.35931 on the same circle, measured with 0.1.234.
The histogram and the probability of failure were those of another mechanism,
and nothing said so.

THE FIX IS ONE DOOR. ``analysis_runner.build_evaluator`` builds the
re-evaluation search from the same arguments ``build_search`` gives every
search. This file checks it four ways, and none of them pins a number this
program printed:

* an IDENTITY: every sample, and every point of a sensitivity sweep, equals
  ``build_search(...).evaluate_circle`` on its own sampled copy, to 1e-12;
* RULE 7: the Minimum Elevation moves the sampled number, because the bare
  search on the same copy answers a different mass;
* the defaults move NOTHING: without filters, the sample is the bare search's
  number, so models that never used a filter keep their results;
* the evaluator carries EVERY setting the search carries, attribute by
  attribute, and no ``GridSearch(`` is left in ``ogr_core/statistics``.

WHY THIS GEOMETRY. The notched variant of verification problem 22 — Fredlund
and Krahn (1977), the paper that introduced the general limit-equilibrium
formulation — built exactly as ``test_statistical_rebuild_v1154.py`` builds it
and for the same reason: its published circle (xc = 120, yc = 90, R = 80)
cuts the notched ground four times, so the choice between two masses becomes
visible. The notch is SYNTHETIC; no published number belongs to it, which is
why everything asserted on it is an identity or a relation.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

_MID = "bishop_simplified"
_SLICES = 30
_Y_WEAK_TOP = 16.0
_EXTERNAL = [(0, 15), (180, 15), (180, 16), (180, 20), (140, 20),
             (60, 60), (0, 60), (0, 16)]
_NOTCHED = [(0, 15), (180, 15), (180, 16), (180, 20), (140, 20),
            (60, 60), (56.5, 60), (56, 40), (50, 40), (49.5, 60),
            (0, 60), (0, 16)]
_XC, _YC, _R = 120.0, 90.0, 80.0
#: The Minimum Elevation that removes the deep mass of the notched circle and
#: keeps the shallow one: the deep mass runs on the weak layer at y = 16 and
#: the shallow one stays inside the notch, above y = 40.
_MIN_ELEVATION = 30.0
#: Relative agreement asked of two evaluations that must be the same one.
_SAME = 1e-12

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _build(vertices):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection

    p = Project("statistics with the configured search — D92")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in vertices], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, _Y_WEAK_TOP), Vertex(180, _Y_WEAK_TOP)], closed=False),
        btype=BoundaryType.MATERIAL))
    upper = Material(name="Upper soil", unit_weight=120.0,
                     sat_unit_weight=120.0,
                     strength=MohrCoulomb(cohesion=600.0, friction_angle=20.0),
                     pore_pressure=PorePressureType.NONE)
    weak = Material(name="Weak layer", unit_weight=120.0,
                    sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=10.0),
                    pore_pressure=PorePressureType.NONE)
    p.materials = [upper, weak]
    p.resolve_regions()
    p.assign_material_at(90.0, 30.0, upper.id)
    p.assign_material_at(90.0, 15.5, weak.id)
    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.methods.num_slices = _SLICES
    p.settings.methods.interslice_function = "half_sine"
    p.settings.search.composite_surfaces = True
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    return p


def _model(key: str):
    """A fresh deep copy every call: the classes below change settings, and a
    shared fixture is state (rule 5)."""
    if key not in _CACHE:
        if key == "notched":
            p = _build(_NOTCHED)
            p.settings.search.min_elevation = _MIN_ELEVATION
        else:
            p = _build(_EXTERNAL)
        _CACHE[key] = p
    return copy.deepcopy(_CACHE[key])


def _circle():
    from ogr_slip2d.surface import SlipCircle

    return SlipCircle(centre_x=_XC, centre_y=_YC, radius=_R)


def _configured(project):
    """The search the deterministic run uses: the oracle of this file."""
    from ogr_slip2d.analysis_runner import build_search

    return build_search(project, _MID)


def _bare(project):
    """The search the sampler built until v0.1.235 (D92)."""
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch

    return GridSearch(method=build_method(project, _MID, _SLICES),
                      num_slices=_SLICES, min_area=0.0,
                      **project.settings.admissibility_kwargs())


def _cohesion_var(project):
    """The cohesion of the upper soil, the material both masses cut."""
    from ogr_core.statistics import Distribution, DistributionType as DT
    from ogr_core.statistics import available_variables

    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"],
        std_dev=60.0, rel_min=180.0, rel_max=180.0)
    return v


def _lowest_base(result) -> float:
    return min(min(s.base_y_left, s.base_y_right) for s in result.slices)


def _close(a: float, b: float, rel: float = _SAME) -> bool:
    return abs(a - b) <= rel * max(abs(a), abs(b))


def _run_samples(project, n: int = 5, seed: int = 7):
    from ogr_core.statistics import SamplingMethod, run_global_minimum

    det = _configured(project).evaluate_circle(project, _circle())
    var = _cohesion_var(project)
    res = run_global_minimum(project, {_MID: det}, [var], num_samples=n,
                             sampling=SamplingMethod.MONTE_CARLO, seed=seed,
                             num_slices=_SLICES)
    return det, var, res


def _replay(project, var, res, i: int, search):
    """Sample ``i`` evaluated again, by hand, with ``search``."""
    from ogr_core.statistics import apply_sample, clone_project
    from ogr_core.statistics.probabilistic import (
        _evaluate_on, _rebuild_surface,
    )

    clone = clone_project(project)
    apply_sample(clone, [var], {k: v[i] for k, v in res.samples.items()})
    sd = res.by_method[_MID].surface
    return _evaluate_on(clone, search, _rebuild_surface(sd))


# ======================================================================
class TestThePremiseTheFilterChoosesTheMass:
    """Without these the rest of the file could pass for the wrong reason."""

    def test_the_notched_circle_defines_two_masses(self):
        from ogr_core.geometry import ground_surface

        p = _model("notched")
        chords = _circle().candidate_chords(
            ground_surface(p.external_boundary()))
        assert len(chords) == 2, chords

    def test_with_the_filter_the_answer_stays_above_it(self):
        p = _model("notched")
        r = _configured(p).evaluate_circle(p, _circle())
        assert r is not None and r.is_valid, r
        assert _lowest_base(r) >= _MIN_ELEVATION - 1e-9, _lowest_base(r)

    def test_without_the_filter_the_answer_is_the_mass_it_removes(self):
        p = _model("notched")
        r = _bare(p).evaluate_circle(p, _circle())
        assert r is not None and r.is_valid, r
        assert _lowest_base(r) < _MIN_ELEVATION, _lowest_base(r)


# ======================================================================
class TestEverySampleIsTheConfiguredEvaluation:
    """The identity, and the rule-7 relation that makes it bite."""

    def test_each_sample_equals_the_configured_search_on_its_own_copy(self):
        p = _model("notched")
        _det, var, res = _run_samples(p)
        mres = res.by_method[_MID]
        assert mres.failed_samples == 0, mres.failed_samples
        assert len(mres.sample_index) == 5, mres.sample_index
        for value, i in zip(mres.statistics.values, mres.sample_index):
            r = _replay(p, var, res, i, _configured(p))
            assert r is not None and r.is_valid, (i, r)
            assert _close(value, r.fos), (i, value, r.fos)

    def test_no_sample_is_the_number_of_the_removed_mass(self):
        """Rule 7: the filter has to move the sampled number. The bare
        search on the SAME copy answers another mass, so a sampler that
        ignored the filter would fail here and not only above."""
        p = _model("notched")
        _det, var, res = _run_samples(p)
        mres = res.by_method[_MID]
        for value, i in zip(mres.statistics.values, mres.sample_index):
            bare = _replay(p, var, res, i, _bare(p))
            assert bare is not None and bare.is_valid, (i, bare)
            assert not _close(value, bare.fos, 1e-6), (i, value, bare.fos)


# ======================================================================
class TestTheSensitivitySweepToo:
    """``run_sensitivity`` re-evaluates the same way and had the same bare
    search; the same identity, point by point."""

    def test_each_point_equals_the_configured_search(self):
        from ogr_core.statistics import (
            clone_project, run_sensitivity, set_value,
        )
        from ogr_core.statistics.probabilistic import (
            _evaluate_on, _rebuild_surface,
        )

        p = _model("notched")
        det = _configured(p).evaluate_circle(p, _circle())
        var = _cohesion_var(p)
        res = run_sensitivity(p, {_MID: det}, [var], intervals=4,
                              num_slices=_SLICES)
        vs = res.by_method[_MID][var.key]
        assert len(vs.values) == 5, vs.values
        seed = _rebuild_surface(det.surface.to_dict())
        for x, f in zip(vs.values, vs.fos):
            clone = clone_project(p)
            assert set_value(clone, var, x)
            r = _evaluate_on(clone, _configured(p), seed)
            bare = _evaluate_on(clone, _bare(p), seed)
            assert _close(f, r.fos), (x, f, r.fos)
            assert not _close(f, bare.fos, 1e-6), (x, f, bare.fos)


# ======================================================================
class TestWithTheDefaultsNothingMoves:
    """A model that never set a filter keeps the digits it had: on the
    published problem-22 model the configured search and the bare one are
    the same evaluation, so the samples are too."""

    def test_the_samples_are_the_bare_search_numbers(self):
        p = _model("published")
        _det, var, res = _run_samples(p)
        mres = res.by_method[_MID]
        assert mres.failed_samples == 0, mres.failed_samples
        for value, i in zip(mres.statistics.values, mres.sample_index):
            bare = _replay(p, var, res, i, _bare(p))
            assert _close(value, bare.fos), (i, value, bare.fos)


# ======================================================================
class TestTheEvaluatorCarriesWhatTheSearchCarries:
    """Every project setting ``build_search`` gives a search reaches the
    evaluator, compared attribute by attribute rather than trusted."""

    _ATTRS = ("num_slices", "min_area", "min_elevation", "min_depth",
              "slope_limit_sets", "reject_tensile", "tensile_percent",
              "check_m_alpha", "seismic_analysis")

    def _loaded(self):
        p = _model("published")
        s = p.settings.search
        s.min_elevation = 18.0
        s.min_depth = 0.5
        s.slope_limit_left, s.slope_limit_right = 10.0, 70.0
        s.slope_limit_left_2, s.slope_limit_right_2 = 120.0, 170.0
        s.min_area = 7.5
        p.settings.advanced.check_tensile_stresses = True
        p.settings.advanced.tensile_percent = 80.0
        p.settings.advanced.check_m_alpha = False
        return p

    def test_every_setting_reaches_the_evaluator(self):
        from ogr_slip2d.analysis_runner import build_evaluator

        p = self._loaded()
        ev = build_evaluator(p, _MID)
        se = _configured(p)
        for name in self._ATTRS:
            assert getattr(ev, name) == getattr(se, name), (
                name, getattr(ev, name), getattr(se, name))
        assert ([id(f) for f in ev.focus_objects]
                == [id(f) for f in se.focus_objects])

    def test_the_settings_are_not_the_defaults(self):
        """Guards the test above against comparing two default objects."""
        from ogr_slip2d.analysis_runner import build_evaluator

        ev = build_evaluator(self._loaded(), _MID)
        assert ev.min_elevation == 18.0 and ev.min_depth == 0.5
        assert ev.slope_limit_sets == ((10.0, 70.0), (120.0, 170.0))
        assert ev.min_area == 7.5
        assert ev.reject_tensile is True and ev.check_m_alpha is False

    def test_a_method_handed_in_is_the_one_used(self):
        """The samplers pass the method built from the FACTORED project
        (``method_factory``); the evaluator must not build its own."""
        from ogr_slip2d.analysis_runner import build_evaluator, build_method

        p = _model("published")
        m = build_method(p, _MID, _SLICES)
        assert build_evaluator(p, _MID, method=m).method is m

    def test_an_unknown_method_gives_no_evaluator(self):
        from ogr_slip2d.analysis_runner import build_evaluator

        assert build_evaluator(_model("published"), "no_such_method") is None


# ======================================================================
class TestOneDoor:
    """No search is assembled by hand in the statistics package any more."""

    def test_no_GridSearch_is_called_in_ogr_core_statistics(self):
        import ogr_core.statistics as pkg

        calls = []
        for path in sorted(Path(pkg.__file__).parent.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                name = (f.id if isinstance(f, ast.Name) else
                        f.attr if isinstance(f, ast.Attribute) else None)
                if name == "GridSearch":
                    calls.append("%s:%d" % (path.name, node.lineno))
        assert calls == [], calls
