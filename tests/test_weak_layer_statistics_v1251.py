# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A critical surface that runs along a weak layer has statistics, and every
sample answers for the weak layer of its own project.

WHAT INVARIANT THIS PROTECTS. Until v0.1.251 a statistical run REFUSED a
deterministic surface of type ``weak_layer`` by name (v0.1.154, D59/D85): a
model whose critical surface runs along a joint, a geomembrane or a bedding
plane had no probability of failure at all. Now the surface is seeded from
its BASE and every sample clips that base against the weak layers of its own
project again, as a composite is clipped against the floor again from its
circle. Three things have to hold at once, and each is a different way of
getting it wrong:

* every sample is the weak-layer surface of its own project, and its factor
  is the factor of THAT surface — not of the bare base, not of the
  deterministic surface frozen;
* a project whose weak layers decide a different case than the deterministic
  surface's — another handling, a suppressed layer — is refused instead of
  answered: a weak-layer surface keeps the ends of its mass, so type and
  extent alone (the probe of v0.1.239) cannot see it;
* a sample that answers for another weak-layer case of the same mass is
  counted and said, as D89 says a change of mass, and no number moves.

WHY THESE ANCHORS. None of the numbers below is a value this code printed.

* THE CLOSED FORM, from ``test_weak_layer_v1121``: over a planar joint in one
  material with no water the Ordinary method is exactly
  ``F = (c L + W cos(a) tan(phi)) / (W sin(a))``, with W = gamma * 80 by
  hand-integrated area. Sampling the joint's own c and phi makes every sample
  a closed-form number, and the probability of failure the closed-form count.
* THE REPLAY: on a circle base, each sample equals the base circle evaluated
  directly on that sample's project — two routes to one number.
* RULE 7 has nothing to bite on: no setting is added.

The planar surface needs at least 30 slices (25 refuse it: more mandatory
cuts than slices), so every run here passes 40 explicitly; the direct-call
default of 25 is D248.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_SLICES = 40

# --- The planar joint of test_weak_layer_v1121 ------------------------
_EXT = [(0.0, 0.0), (40.0, 0.0), (40.0, 10.0), (10.0, 10.0)]
_GAMMA = 20.0
_JX0, _JY0, _JX1, _JY1 = 2.0, 2.0, 30.0, 10.0
_AREA = 80.0                                   # hand-integrated in v1121
_L = math.hypot(_JX1 - _JX0, _JY1 - _JY0)
_ALPHA = math.atan2(_JY1 - _JY0, _JX1 - _JX0)

# --- The circle of v1121's TestRuleSeven ------------------------------
_CX, _CY, _R = 18.0, 28.0, 20.0
_EXT3 = [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (25.0, 20.0),
         (10.0, 10.0), (0.0, 10.0)]

_ORD = "ordinary_fellenius"
_BISHOP = "bishop_simplified"


def _closed_form(c, phi_deg):
    w = _GAMMA * _AREA
    return ((c * _L + w * math.cos(_ALPHA) * math.tan(math.radians(phi_deg)))
            / (w * math.sin(_ALPHA)))


def _planar(c=5.0, phi=20.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("weak layer statistics")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(*v) for v in _EXT], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Soil", unit_weight=_GAMMA,
        strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0)))
    joint = Material(name="Joint", unit_weight=_GAMMA,
                     strength=MohrCoulomb(cohesion=c, friction_angle=phi))
    p.materials.append(joint)
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(_JX0, _JY0), Vertex(_JX1, _JY1)]),
        btype=BoundaryType.WEAK_LAYER, material_id=joint.id))
    p.settings.methods.num_slices = _SLICES
    return p


def _below_the_joint():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface

    return SlipSurface(polyline=Polyline([
        Vertex(_JX0, _JY0), Vertex(16.0, 1.0), Vertex(_JX1, _JY1)]))


def _arc_x(y):
    d = math.sqrt(_R ** 2 - (_CY - y) ** 2)
    return _CX - d, _CX + d


def _circle_model(layers, handling):
    """``layers``: ``[(elevation, (c, phi))]``, as in v1121's rule seven."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("weak layer statistics, circle")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(*v) for v in _EXT3], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Soil", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0)))
    for y, (c, phi) in layers:
        m = Material(name=f"Joint {y}", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=c, friction_angle=phi))
        p.materials.append(m)
        x0, x1 = _arc_x(y)
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(x0, y), Vertex(x1, y)]),
            btype=BoundaryType.WEAK_LAYER, material_id=m.id))
    p.settings.search.weak_layer_handling = handling
    p.settings.methods.num_slices = _SLICES
    return p


def _two_joints(handling):
    # The pair of v1121: a strong upper joint and a weak lower one, so
    # "highest" snaps to the upper and automatic cases find the lower.
    return _circle_model([(9.0, (200.0, 45.0)), (8.5, (1.0, 5.0))],
                         handling)


def _det_surface(p, method, surface):
    from ogr_slip2d.analysis_runner import build_evaluator

    ev = build_evaluator(p, method, num_slices=_SLICES)
    with p.regions_frozen():
        return ev.evaluate_surface(p, surface)


def _det_circle(p, method=_BISHOP):
    from ogr_slip2d.surface import SlipCircle
    return _det_surface(p, method, SlipCircle(_CX, _CY, _R))


def _variable(p, material_index, param, mean, sd, below, above=None):
    """A normal variable on ``param`` of material ``material_index``, from
    ``mean - below`` to ``mean + above`` (``above`` defaults to ``below``)."""
    from ogr_core.statistics import Distribution, DistributionType as DT
    from ogr_core.statistics import available_variables

    target = p.materials[material_index].id
    v = [x for x in available_variables(p)
         if x.param == param and x.target_id == target][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mean, std_dev=sd, rel_min=below,
        rel_max=below if above is None else above)
    return v


class _Recorder:
    """Wraps ``_evaluate_on`` to keep every sample's result, restored in
    ``finally`` by ``_recording`` (rule 5: the runner has no teardown)."""

    def __init__(self, inner):
        self.inner = inner
        self.results = []

    def __call__(self, project, search, surface):
        r = self.inner(project, search, surface)
        self.results.append(r)
        return r


def _recording(action):
    import ogr_core.statistics.probabilistic as P

    saved = P._evaluate_on
    rec = _Recorder(saved)
    P._evaluate_on = rec
    try:
        return action(), rec.results
    finally:
        P._evaluate_on = saved


def _gm(p, det, variables, method, n, seed):
    from ogr_core.statistics import SamplingMethod as SM
    from ogr_core.statistics import run_global_minimum

    return run_global_minimum(p, {method: det}, variables, num_samples=n,
                              sampling=SM.LATIN_HYPERCUBE, seed=seed,
                              num_slices=_SLICES)


def _layers(surface):
    from ogr_core.statistics.probabilistic import _active_layers
    return _active_layers(surface)


# ======================================================================
class TestThePremise:

    def test_the_deterministic_surface_runs_along_the_joint(self):
        det = _det_surface(_planar(), _ORD, _below_the_joint())
        assert det is not None and det.is_valid
        assert type(det.surface).__name__ == "WeakLayerSurface"
        assert det.fos == _closed_form(5.0, 20.0) or abs(
            det.fos / _closed_form(5.0, 20.0) - 1.0) < 1e-12

    def test_it_is_seeded_from_its_base(self):
        from ogr_core.statistics.probabilistic import (_cannot_reevaluate,
                                                       _rebuild_surface)
        p = _planar()
        sd = _det_surface(p, _ORD, _below_the_joint()).surface.to_dict()
        assert _cannot_reevaluate(p, sd) is None
        seed = _rebuild_surface(sd)
        assert type(seed).__name__ == "SlipSurface"
        assert ([(v.x, v.y) for v in seed.polyline.vertices]
                == [(v.x, v.y) for v in _below_the_joint().polyline.vertices])


# ======================================================================
class TestTheClosedFormSampleBySample:

    def _run(self):
        p = _planar()
        det = _det_surface(p, _ORD, _below_the_joint())
        vc = _variable(p, 1, "cohesion", 5.0, 1.5, 4.5)
        vf = _variable(p, 1, "friction_angle", 20.0, 5.0, 15.0)
        res, seen = _recording(lambda: _gm(p, det, [vc, vf], _ORD, 40, 3))
        return p, det, vc, vf, res, seen

    def test_every_sample_is_the_closed_form_of_its_own_joint(self):
        _p, _det, vc, vf, res, _seen = self._run()
        assert res.ok, res.notes
        m = res.by_method[_ORD]
        assert m.statistics.n == 40 and m.failed_samples == 0
        for i, f in zip(m.sample_index, m.statistics.values):
            exact = _closed_form(res.samples[vc.key][i],
                                 res.samples[vf.key][i])
            assert abs(f / exact - 1.0) < 1e-12, (i, f, exact)

    def test_the_probability_of_failure_is_the_closed_form_count(self):
        _p, _det, vc, vf, res, _seen = self._run()
        m = res.by_method[_ORD]
        below = sum(1 for i in m.sample_index
                    if _closed_form(res.samples[vc.key][i],
                                    res.samples[vf.key][i]) < 1.0)
        assert below > 0, "the distributions must reach failure"
        assert m.probability_of_failure == below / m.statistics.n

    def test_every_sample_runs_along_the_deterministic_layers(self):
        _p, det, _vc, _vf, res, seen = self._run()
        home = _layers(det.surface)
        assert home, "the deterministic surface runs along the joint"
        assert len(seen) == 40
        for r in seen:
            assert type(r.surface).__name__ == "WeakLayerSurface"
            assert _layers(r.surface) == home
        m = res.by_method[_ORD]
        assert m.mass_switches == 0 and m.case_switches == 0
        assert m.summary()["case_switches"] == 0
        assert not res.notes and not res.note_lines

    def test_the_sensitivity_sweep_is_the_closed_form_too(self):
        from ogr_core.statistics import run_sensitivity
        p = _planar()
        det = _det_surface(p, _ORD, _below_the_joint())
        vc = _variable(p, 1, "cohesion", 5.0, 1.5, 4.5)
        sen = run_sensitivity(p, {_ORD: det}, [vc], intervals=2,
                              num_slices=_SLICES)
        vs = sen.by_method[_ORD][vc.key]
        assert vs.values == [0.5, 5.0, 9.5]
        assert vs.fos[1] == det.fos
        for c, f in zip(vs.values, vs.fos):
            assert abs(f / _closed_form(c, 20.0) - 1.0) < 1e-12, (c, f)


# ======================================================================
class TestACircleBaseResolvesItsOwnMass:

    def test_each_sample_is_the_base_circle_evaluated_on_its_project(self):
        from ogr_core.project.settings import WeakLayerHandling
        from ogr_core.statistics import apply_sample, clone_project
        from ogr_slip2d.analysis_runner import build_evaluator
        from ogr_slip2d.surface import SlipCircle

        p = _circle_model([(9.0, (1.0, 5.0))],
                          WeakLayerHandling.HIGHEST.value)
        det = _det_circle(p)
        assert type(det.surface).__name__ == "WeakLayerSurface"
        v = _variable(p, 1, "friction_angle", 5.0, 2.0, 4.5)
        res, seen = _recording(lambda: _gm(p, det, [v], _BISHOP, 20, 5))
        assert res.ok, res.notes
        m = res.by_method[_BISHOP]
        ev = build_evaluator(p, _BISHOP, num_slices=_SLICES)
        for i, f in zip(m.sample_index, m.statistics.values):
            clone = clone_project(p)
            apply_sample(clone, [v], {v.key: res.samples[v.key][i]})
            with clone.regions_frozen():
                direct = ev.evaluate_circle(clone, SlipCircle(_CX, _CY, _R))
            assert direct.fos == f, (i, direct.fos, f)
        for r in seen:
            assert type(r.surface).__name__ == "WeakLayerSurface"
            assert (r.surface.x_left, r.surface.x_right) == (
                det.surface.x_left, det.surface.x_right)
        assert m.mass_switches == 0 and m.case_switches == 0


# ======================================================================
class TestAnotherCaseIsRefusedNotAnswered:
    """The probe of v0.1.239, with the layers compared too."""

    def _refused_by_the_probe(self, res, method=_BISHOP):
        from ogr_core.statistics.probabilistic import _NOT_ITSELF
        head = _NOT_ITSELF.split(" (", 1)[0]
        reason = res.notes.get(method, "")
        return (method not in res.by_method and reason.startswith(head)
                and "weak-layer case" in reason
                and ("%s: %s" % (method, reason)) in res.note_lines)

    def test_highest_against_automatic_cases_both_ways(self):
        from ogr_core.project.settings import WeakLayerHandling as H
        for det_h, mu_h in ((H.HIGHEST.value, H.AUTO_CASES.value),
                            (H.AUTO_CASES.value, H.HIGHEST.value)):
            p_det, p_mu = _two_joints(det_h), _two_joints(det_h)
            p_mu.settings.search.weak_layer_handling = mu_h
            det = _det_circle(p_det)
            v = _variable(p_mu, 2, "friction_angle", 5.0, 1.0, 3.0)
            res = _gm(p_mu, det, [v], _BISHOP, 6, 1)
            assert self._refused_by_the_probe(res), (det_h, res.notes)

    def test_a_layer_suppressed_only_in_the_samples(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.project.settings import WeakLayerHandling as H
        p = _circle_model([(9.0, (1.0, 5.0))], H.HIGHEST.value)
        det = _det_circle(p)
        mu = copy.deepcopy(p)
        for b in mu.boundaries:
            if b.btype is BoundaryType.WEAK_LAYER:
                b.suppressed = True
        v = _variable(mu, 1, "friction_angle", 5.0, 1.0, 3.0)
        res = _gm(mu, det, [v], _BISHOP, 6, 1)
        assert self._refused_by_the_probe(res), res.notes

    def test_the_same_project_is_not_refused(self):
        from ogr_core.project.settings import WeakLayerHandling as H
        p = _two_joints(H.AUTO_CASES.value)
        det = _det_circle(p)
        v = _variable(p, 2, "friction_angle", 5.0, 1.0, 3.0)
        res = _gm(p, det, [v], _BISHOP, 6, 1)
        assert _BISHOP in res.by_method and not res.notes, res.notes

    def test_the_new_sentence_keeps_the_head_and_no_inner_separator(self):
        from ogr_core.statistics.probabilistic import (_NOT_ITSELF,
                                                       _NOT_ITSELF_CASE)
        assert (_NOT_ITSELF_CASE.split(" (", 1)[0]
                == _NOT_ITSELF.split(" (", 1)[0])
        assert ": " not in _NOT_ITSELF_CASE


# ======================================================================
class TestAChangeOfCaseIsSaidAndMovesNothing:

    def _run(self, sd):
        from ogr_core.project.settings import WeakLayerHandling as H
        p = _two_joints(H.AUTO_CASES.value)
        det = _det_circle(p)
        # Down to 0.5 deg and up to three deviations: wide enough, at
        # sd = 12, for the weak joint to stop being the weakest case.
        v = _variable(p, 2, "friction_angle", 5.0, sd, min(4.5, 3 * sd),
                      3 * sd)
        res, seen = _recording(lambda: _gm(p, det, [v], _BISHOP, 40, 5))
        return det, res, seen

    def test_the_count_is_the_replays_and_the_sentence_reaches_the_panel(self):
        det, res, seen = self._run(12.0)
        m = res.by_method[_BISHOP]
        home_ext = (det.surface.x_left, det.surface.x_right)
        home = _layers(det.surface)
        replay = sum(1 for r in seen
                     if (getattr(r.surface, "x_left", None),
                         getattr(r.surface, "x_right", None)) == home_ext
                     and _layers(r.surface) != home)
        assert replay > 0, "the premise: some sample changes case"
        assert m.case_switches == replay
        assert m.mass_switches == 0
        assert m.summary()["case_switches"] == replay
        said = m.notes.get("case_switch", "")
        assert said.startswith("%d of 40 samples answered for another "
                               "weak-layer case" % replay), said
        assert ": " not in said
        assert ("%s: %s" % (_BISHOP, said)) in res.note_lines

    def test_counting_moves_no_number(self):
        _det, res, seen = self._run(12.0)
        m = res.by_method[_BISHOP]
        assert m.statistics.values == [r.fos for r in seen]

    def test_a_narrow_distribution_says_nothing(self):
        _det, res, _seen = self._run(1.0)
        m = res.by_method[_BISHOP]
        assert m.case_switches == 0 and "case_switch" not in m.notes
        assert not res.note_lines

    def test_the_sensitivity_says_it_too(self):
        from ogr_core.project.settings import WeakLayerHandling as H
        from ogr_core.statistics import run_sensitivity
        p = _two_joints(H.AUTO_CASES.value)
        det = _det_circle(p)
        v = _variable(p, 2, "friction_angle", 5.0, 12.0, 4.5, 40.0)
        sen = run_sensitivity(p, {_BISHOP: det}, [v], intervals=8,
                              num_slices=_SLICES)
        vs = sen.by_method[_BISHOP][v.key]
        assert vs.case_switch_values, "the premise: the sweep changes case"
        assert not vs.mass_switch_values
        assert any("another weak-layer case" in line
                   for line in sen.note_lines), sen.note_lines


# ======================================================================
class TestWhatIsStillRefusedSaysWhy:

    def test_a_weak_layer_without_its_base(self):
        from ogr_core.statistics.probabilistic import (_cannot_reevaluate,
                                                       _rebuild_surface)
        sd = {"type": "weak_layer", "x_left": 2.0, "x_right": 30.0}
        assert _rebuild_surface(sd) is None
        said = _cannot_reevaluate(_planar(), sd)
        assert said and "'weak_layer'" in said and "'None'" in said

    def test_a_composite_base_needs_composite_surfaces(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.statistics.probabilistic import _cannot_reevaluate
        from ogr_slip2d.surface import (CompositeSurface, SlipCircle,
                                        WeakLayerSurface)
        circle = SlipCircle(centre_x=120.0, centre_y=90.0, radius=80.0)
        circle.x_left, circle.x_right = 45.0, 158.0
        comp = CompositeSurface(
            circle=circle,
            bedrock=Polyline(vertices=[Vertex(0.0, 15.0), Vertex(180.0, 15.0)]),
            x_left=45.0, x_right=158.0)
        sd = WeakLayerSurface(base=comp, bands=()).to_dict()
        off = _planar()
        off.settings.search.composite_surfaces = False
        said = _cannot_reevaluate(off, sd)
        assert said and "weak layer" in said and "Composite Surfaces" in said
        on = _planar()
        on.settings.search.composite_surfaces = True
        assert _cannot_reevaluate(on, sd) is None

    def test_a_seed_that_cannot_be_built_is_named_not_dropped(self):
        """The ``continue`` after ``_rebuild_surface`` used to drop the
        method without a word; reachable only when ``_cannot_reevaluate``
        is replaced, as here."""
        import ogr_core.statistics.probabilistic as P
        from ogr_core.statistics import run_sensitivity

        p = _planar()
        det = _det_surface(p, _ORD, _below_the_joint())
        orphan = copy.copy(det)
        orphan.surface = {"type": "weak_layer", "x_left": 2.0,
                          "x_right": 30.0}
        vc = _variable(p, 1, "cohesion", 5.0, 1.5, 4.5)
        saved = P._cannot_reevaluate
        P._cannot_reevaluate = lambda project, sd: None
        try:
            res = _gm(p, orphan, [vc], _ORD, 4, 1)
            sen = run_sensitivity(p, {_ORD: orphan}, [vc], intervals=2,
                                  num_slices=_SLICES)
        finally:
            P._cannot_reevaluate = saved
        for run in (res, sen):
            reason = run.notes.get(_ORD, "")
            assert _ORD not in run.by_method
            assert "'weak_layer'" in reason, reason
            assert ("%s: %s" % (_ORD, reason)) in run.note_lines
