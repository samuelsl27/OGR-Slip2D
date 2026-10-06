# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.263, defect D248 — a statistical run called directly slices like the
project, as the analysis does.

Invariants protected:

1. **``run_global_minimum`` and ``run_sensitivity`` evaluate with the
   project's slices unless told otherwise.** Both had ``num_slices: int =
   25``: the analysis door (``run_configured_statistics``, used by the
   window, the API and the MCP) passes the project's count, but a direct
   call — a script, a test, ``python_exec`` — evaluated every sample with 25
   beside a deterministic run that had used the project's, and nothing said
   so. The default is None now, and None is the project's own, read off the
   project as the analysis prepares it, which is what ``build_method`` and
   ``build_evaluator`` already did with None. An explicit number still
   rules. The 25 also reached ``build_method`` and, through it, the rapid
   drawdown wrapper.
2. **``run_back_analysis`` no longer takes a ``num_slices`` it never read**
   (rule 7: a setting that does not reach the number is worse than none).
   Its slicing is the search's.

ANCHOR. Each sample of the probabilistic run is recomputed independently:
its values applied to a clone of the project and the deterministic circle
evaluated there with the project's slices. They must agree to 1e-12. The
sensitivity run's midpoint, the variable at its mean, must be the
deterministic factor itself. The project uses 51 slices, neither 25 nor a
multiple of it, so that the two counts cannot give the same slices; on this
circle 51 and 25 differ by 7.7e-4.

COST. One small slope, five samples and three sensitivity points. A second.
"""
from __future__ import annotations

_SLICES = 51
_TOL = 1e-12


def _project():
    """A 20 m slope (toe flat at y = 10, 45-degree face to (40, 30), crest
    at 30), one soil, 51 slices."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    pts = [(0.0, 0.0), (60.0, 0.0), (60.0, 30.0), (40.0, 30.0), (20.0, 10.0),
           (0.0, 10.0)]
    p = Project("D248")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=20.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    p.settings.methods.num_slices = _SLICES
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=25.0, centre_y=45.0, radius=33.0)


def _deterministic(p, num_slices=None):
    from ogr_slip2d.analysis_runner import build_evaluator
    return build_evaluator(p, "bishop_simplified",
                           num_slices=num_slices).evaluate_circle(p, _circle())


def _cohesion(p, std=1.0, spread=2.0):
    from ogr_core.statistics import Distribution, DistributionType as DT
    from ogr_core.statistics import available_variables
    v = [x for x in available_variables(p) if x.param == "cohesion"][0]
    v.distribution = Distribution(DT.NORMAL, mean=10.0, std_dev=std,
                                  rel_min=spread, rel_max=spread)
    return v


def _recomputed(p, v, sample):
    """The sample's factor computed on its own, with the project's
    slices."""
    from ogr_core.statistics.random_variables import apply_sample, clone_project
    c = clone_project(p)
    assert apply_sample(c, [v], sample) == 1
    return _deterministic(c).fos


def _sample(result, k):
    """Sample ``k`` of a run: ``result.samples`` is ``key -> values``."""
    return {key: vals[k] for key, vals in result.samples.items()}


def _global_minimum(p, v, **kw):
    from ogr_core.statistics import SamplingMethod as SM
    from ogr_core.statistics import run_global_minimum
    return run_global_minimum(p, {"bishop_simplified": _deterministic(p)}, [v],
                              num_samples=5, sampling=SM.LATIN_HYPERCUBE,
                              seed=3, **kw)


# ======================================================================
class TestADirectCallSlicesLikeTheProject:
    """Invariant 1."""

    def test_the_premise_51_and_25_slices_differ_here(self):
        p = _project()
        assert abs(_deterministic(p).fos
                   - _deterministic(p, num_slices=25).fos) > 1e-4

    def test_every_sample_is_its_own_recomputation(self):
        """Fails on v0.1.262, which evaluated every sample with 25."""
        p = _project()
        v = _cohesion(p)
        r = _global_minimum(p, v)
        m = r.by_method["bishop_simplified"]
        assert len(m.statistics.values) == 5, r.notes
        for fos, k in zip(m.statistics.values, m.sample_index):
            assert abs(fos - _recomputed(p, v, _sample(r, k))) <= _TOL

    def test_an_explicit_count_still_rules(self):
        """The control: with 25 asked for, the samples are NOT the
        project's recomputation."""
        p = _project()
        v = _cohesion(p)
        r = _global_minimum(p, v, num_slices=25)
        m = r.by_method["bishop_simplified"]
        worst = max(abs(fos - _recomputed(p, v, _sample(r, k)))
                    for fos, k in zip(m.statistics.values, m.sample_index))
        assert worst > 1e-5

    def test_the_sensitivity_midpoint_is_the_deterministic_factor(self):
        """Fails on v0.1.262: the midpoint was the 25-slice factor."""
        from ogr_core.statistics import run_sensitivity
        p = _project()
        v = _cohesion(p)
        det = _deterministic(p)
        s = run_sensitivity(p, {"bishop_simplified": det}, [v], intervals=2)
        vs = list(s.by_method["bishop_simplified"].values())[0]
        assert vs.values[1] == 10.0
        assert abs(vs.fos[1] - det.fos) <= _TOL

    def test_the_drawdown_wrapper_is_given_the_projects_count(self):
        """The method is made by ``build_method``, which hands its count to
        ``wrap_for_drawdown``. Fails on v0.1.262, which handed it 25."""
        import ogr_slip2d.analysis_runner as AR
        p = _project()
        v = _cohesion(p)
        seen = []
        real = AR.wrap_for_drawdown

        def spy(method, project, num_slices):
            seen.append(num_slices)
            return real(method, project, num_slices=num_slices)

        AR.wrap_for_drawdown = spy
        try:
            _global_minimum(p, v)
        finally:
            AR.wrap_for_drawdown = real
        assert seen and set(seen) == {_SLICES}, seen


# ======================================================================
class TestBackAnalysisTakesNoDeadSetting:
    """Invariant 2."""

    def test_num_slices_is_refused_not_ignored(self):
        """Fails on v0.1.262, which accepted it and never read it."""
        import inspect
        from ogr_slip2d.back_analysis import run_back_analysis
        assert "num_slices" not in inspect.signature(
            run_back_analysis).parameters
        try:
            run_back_analysis(_project(), None, num_slices=25)
            raise AssertionError("num_slices was accepted")
        except TypeError:
            pass
