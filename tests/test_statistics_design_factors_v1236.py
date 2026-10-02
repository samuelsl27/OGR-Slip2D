# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D93 — a statistical run samples the model the analysis computes on, and says
so.

**The invariant**: with a design standard on, every sample is factored like
the deterministic surface it re-evaluates — whoever starts the run. The
analysis door (``run_configured_statistics``) has done it since v0.1.201 by
passing ``prepare``; the three public functions did NOT when called
directly: ``prepare=None`` left each clone unfactored, next to a factored
deterministic surface. Measured on v0.1.235 on the slope below with EC7
DA1-C2 (c = 10 ± 2 kPa between 4 and 16): the door 0.9071 / PF 0.850 /
β −1.041, the same function called directly 1.1333 / PF 0.120 / β 1.194,
and the same split in Overall Slope (PF 0.850 against 0.125) and in the
sensitivity sweep (0.6365–1.1779 against 0.7952–1.4726). Since v0.1.236
``prepare=None`` means the analysis preparation, as v0.1.108 made the
configured method and v0.1.235 the configured evaluator the defaults.

And the interface says what the numbers are: with a standard the statistics
are of the OVER-DESIGN factor, and until this version the window, the notes
and the status bar called them "FoS" — ``out.factor_report`` was read by
nobody.

What each class pins, and against what
--------------------------------------
1. A direct call is the door: the same samples give the same factors, to
   1e-12, in Global Minimum, Overall Slope and the sensitivity sweep.
2. Rule 7: the old behaviour, asked for explicitly (``prepare`` = the
   identity), gives other numbers — the default is what moves them.
3. Without a standard and without links the default is the identity, so a
   run without either reads exactly as before (equal lists).
4. The half of the preparation that is not the standard: a Generalized
   range that links a material follows that material's sample.
5. The design-factored copy is refused, and the flag that tells it apart is
   set on the copy only, survives the copies a run makes, and is not saved.
6. The interface: notes, status bar, the statistics window and the two
   statistics plots of Interpret name the over-design factor with a
   standard and the factor of safety without one.

No assertion fixes a factor of safety: everything is an identity between
two ways of computing the same thing, or a difference that has to exist.

Regla 5: windows are kept in a module list, the language is never changed,
and ``_info`` (a modal) is recorded on the instance instead of shown.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import matplotlib
    matplotlib.use("Agg")
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_MID = "bishop_simplified"
_SAME = 1e-12
_WINDOWS: list = []
_CACHE: dict = {}


def _app():
    return QApplication.instance() or QApplication([])


def _slope(standard=True, analysis_type="global_minimum", sens=False,
           n=40):
    """The small homogeneous slope of ``test_cli_wiring_v177`` with the
    cohesion random (10 ± 2 kPa, from 4 to 16) and, by default, EC7 DA1-C2."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.statistics import (Distribution, DistributionType,
                                     available_variables)

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
        Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("d93")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    p.add_material(Material(
        name="Silty clay", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0)))
    p.settings.methods.enabled_methods = [_MID]
    p.settings.methods.num_slices = 25
    p.settings.search.grid_nx = 3
    p.settings.search.grid_ny = 3
    p.settings.search.radius_increment = 2
    v = [x for x in available_variables(p) if x.param == "cohesion"][0]
    v.distribution = Distribution(DistributionType.NORMAL, mean=10.0,
                                  std_dev=2.0, rel_min=6.0, rel_max=6.0)
    p.random_variables = [v]
    st = p.settings.statistics
    st.probabilistic_analysis = analysis_type is not None
    if analysis_type is not None:
        st.analysis_type = analysis_type
    st.sensitivity_analysis = sens
    st.sensitivity_intervals = 4
    st.num_samples = n
    st.sampling_method = "latin_hypercube"
    if standard:
        ds = p.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da1c2")
    return p


def _deterministic(p):
    """The critical surfaces of the analysis door, as a caller of the
    public functions is told to obtain them."""
    from ogr_slip2d.analysis_runner import run_analysis
    return {mid: sr.critical
            for mid, sr in run_analysis(p, [_MID]).results.items()}


def _identity(clone):
    return clone


def _same_list(a, b):
    return (len(a) == len(b) and len(a) > 0
            and all(abs(x - y) <= _SAME * max(abs(y), 1.0)
                    for x, y in zip(a, b)))


def _gm(p, det, **kw):
    from ogr_core.statistics import SamplingMethod, run_global_minimum
    st = p.settings.statistics
    return run_global_minimum(
        p, det, list(p.random_variables), num_samples=st.num_samples,
        sampling=SamplingMethod(st.sampling_method),
        seed=p.settings.analysis_seed(),
        num_slices=p.settings.methods.num_slices, **kw)


def _os(p, det, **kw):
    from ogr_core.project import prepare_analysis_project
    from ogr_core.statistics import SamplingMethod, run_overall_slope
    from ogr_slip2d.analysis_runner import build_search
    st = p.settings.statistics
    ready = prepare_analysis_project(p)[0]
    return run_overall_slope(
        p, lambda mid: build_search(ready, mid), list(p.random_variables),
        [_MID], num_samples=st.num_samples,
        sampling=SamplingMethod(st.sampling_method),
        seed=p.settings.analysis_seed(), deterministic=det, **kw)


def _sens(p, det, **kw):
    from ogr_core.statistics import run_sensitivity
    return run_sensitivity(
        p, det, list(p.random_variables),
        intervals=p.settings.statistics.sensitivity_intervals,
        num_slices=p.settings.methods.num_slices, **kw)


def _values(res):
    return list(res.by_method[_MID].statistics.values)


def _sweep(res):
    return list(next(iter(res.by_method[_MID].values())).fos)


def _door(p):
    from ogr_slip2d.analysis_runner import run_configured_statistics
    return run_configured_statistics(p)


# ======================================================================
class TestADirectCallIsTheDoor:
    """With EC7 DA1-C2 on: the public functions, called with the door's own
    deterministic surfaces and nothing else, give the door's numbers."""

    def test_global_minimum(self):
        p = _slope()
        door = _door(p)
        direct = _gm(p, door.deterministic)
        assert _same_list(_values(direct), _values(door.probabilistic))

    def test_overall_slope(self):
        p = _slope(analysis_type="overall_slope", n=6)
        door = _door(p)
        direct = _os(p, door.deterministic)
        assert _same_list(_values(direct), _values(door.probabilistic))

    def test_the_sensitivity_sweep(self):
        p = _slope(analysis_type=None, sens=True)
        door = _door(p)
        direct = _sens(p, door.deterministic)
        assert _same_list(_sweep(direct), _sweep(door.sensitivity))


# ======================================================================
class TestTheDefaultIsWhatMovesTheNumber:
    """Rule 7: the behaviour of v0.1.235, asked for by passing the
    identity, answers for the unfactored model. The deterministic surface
    is the factored one in both, so only the samples differ."""

    def test_global_minimum(self):
        p = _slope()
        det = _deterministic(p)
        new = _gm(p, det).by_method[_MID].statistics.mean
        old = _gm(p, det, prepare=_identity).by_method[_MID].statistics.mean
        # Factored by 1.25 on c' and tan φ', the mean falls by about that.
        assert old / new - 1.0 > 0.10, (new, old)

    def test_overall_slope(self):
        p = _slope(analysis_type="overall_slope", n=6)
        det = _deterministic(p)
        new = _os(p, det).by_method[_MID].statistics.mean
        old = _os(p, det, prepare=_identity).by_method[_MID].statistics.mean
        assert old / new - 1.0 > 0.10, (new, old)

    def test_the_sensitivity_sweep(self):
        p = _slope(analysis_type=None, sens=True)
        det = _deterministic(p)
        new, old = _sweep(_sens(p, det)), _sweep(_sens(p, det,
                                                        prepare=_identity))
        assert all(o / f - 1.0 > 0.10 for f, o in zip(new, old)), (new, old)


# ======================================================================
class TestWithoutAStandardNothingMoves:
    """The default costs nothing when there is nothing to prepare: the
    lists are EQUAL, not close."""

    def test_global_minimum(self):
        p = _slope(standard=False)
        det = _deterministic(p)
        assert _values(_gm(p, det)) == _values(_gm(p, det,
                                                   prepare=_identity))

    def test_overall_slope(self):
        p = _slope(standard=False, analysis_type="overall_slope", n=4)
        det = _deterministic(p)
        assert _values(_os(p, det)) == _values(_os(p, det,
                                                   prepare=_identity))

    def test_the_sensitivity_sweep(self):
        p = _slope(standard=False, analysis_type=None, sens=True)
        det = _deterministic(p)
        assert _sweep(_sens(p, det)) == _sweep(_sens(p, det,
                                                     prepare=_identity))

    def test_the_preparation_of_such_a_model_is_the_model(self):
        from ogr_core.project import prepare_analysis_project
        p = _slope(standard=False)
        assert prepare_analysis_project(p)[0] is p


# ======================================================================
class TestALinkedRangeFollowsItsMaterialsSample:
    """The other half of the preparation. A Generalized range that links a
    material reads that material as the analysis runs; sampling the
    material reaches the range only if each sample is prepared."""

    def _run(self, **kw):
        from test_generalized_links_v1228 import CIRCLE, _linked_project

        from ogr_core.statistics import (Distribution, DistributionType,
                                         RandomVariable, SamplingMethod,
                                         VariableKind, run_global_minimum)
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import SlipCircle

        p, _g, children = _linked_project(stale=False)
        det = evaluate_surfaces(p, SlipCircle(*CIRCLE), [_MID],
                                allow_unconfigured=True).results[_MID]
        rv = RandomVariable(kind=VariableKind.MATERIAL_STRENGTH,
                            target_id=children[1].id, param="cohesion")
        rv.distribution = Distribution(DistributionType.NORMAL, mean=1.0,
                                       std_dev=0.5, rel_min=0.9, rel_max=4.0)
        res = run_global_minimum(p, {_MID: det}, [rv], num_samples=8,
                                 sampling=SamplingMethod.LATIN_HYPERCUBE,
                                 seed=3, **kw)
        return res.by_method[_MID].statistics

    def test_by_default_the_samples_differ(self):
        st = self._run()
        assert st.n == 8 and st.std_dev > 0.0, st.values

    def test_unprepared_they_are_all_the_snapshot(self):
        """Rule 7: without the preparation every sample reads the copy the
        rule keeps, so the eight factors are one."""
        st = self._run(prepare=_identity)
        assert st.n == 8 and max(st.values) == min(st.values), st.values


# ======================================================================
class TestTheFactoredCopyIsToldApartAndRefused:

    def _copy(self):
        from ogr_core.project import apply_design_factors
        p = _slope()
        return p, apply_design_factors(p)[0]

    def test_the_flag_is_on_the_copy_and_never_on_the_model(self):
        p, f = self._copy()
        assert f.design_factored_copy is True
        assert p.design_factored_copy is False

    def test_without_a_standard_there_is_no_copy_to_flag(self):
        from ogr_core.project import apply_design_factors
        p = _slope(standard=False)
        out = apply_design_factors(p)[0]
        assert out is p and out.design_factored_copy is False

    def test_it_survives_the_copies_a_run_makes(self):
        from ogr_core.statistics.random_variables import clone_project
        _p, f = self._copy()
        assert copy.deepcopy(f).design_factored_copy is True
        assert clone_project(f).design_factored_copy is True
        assert pickle.loads(pickle.dumps(f)).design_factored_copy is True

    def test_it_is_not_saved(self):
        from ogr_core.project import Project
        _p, f = self._copy()
        d = f.to_dict()
        assert "design_factored_copy" not in str(sorted(d))
        assert Project.from_dict(d).design_factored_copy is False

    def test_the_three_runs_refuse_it(self):
        from ogr_slip2d.analysis_runner import run_analysis
        p = _slope(analysis_type="overall_slope", n=2)
        out = run_analysis(p, [_MID])
        f = out.project
        assert f.design_factored_copy is True
        det = {mid: sr.critical for mid, sr in out.results.items()}
        for res in (_gm(f, det), _os(f, det), _sens(f, det)):
            assert not res.by_method, res.notes
            assert "design-factored copy" in res.notes.get("error", ""), \
                res.notes


# ======================================================================
@_requires_qt
class TestTheWindowSaysWhatTheNumbersAre:

    def _window(self, project):
        from ogr_gui.main_window import MainWindow
        _app()
        w = MainWindow()
        _WINDOWS.append(w)
        w._attach_project(project)
        w.shown_info = []
        w._info = lambda *a, **_k: w.shown_info.append(a)
        w._compute_statistics()
        assert not w.shown_info, w.shown_info
        _WINDOWS.append(w._stats_window)
        return w

    def _axes_labels(self, sw, kind):
        i = sw.cbo_plot.findData(kind)
        sw.cbo_plot.setCurrentIndex(i)
        ax = sw.canvas.figure.axes[0]
        return ax.get_xlabel(), ax.get_ylabel(), sw.cbo_plot.itemText(i)

    def test_with_a_standard(self):
        w = self._window(_slope(n=12))
        assert w.last_statistics_factor_report.applied
        assert w.last_statistics_notes[0].startswith(
            "Design standard applied to every sample: "), \
            w.last_statistics_notes
        assert w.statusBar().currentMessage().startswith(
            "Over-design factor: PF = ")
        sw = w._stats_window
        assert not sw.lbl_factor_report.isHidden()
        x, _y, item = self._axes_labels(sw, "histogram")
        assert x == "Over-design factor" and "over-design" in item
        _x, y, _item = self._axes_labels(sw, "convergence")
        assert y == "Mean over-design factor"

    def test_without_one_the_window_is_the_one_it_was(self):
        w = self._window(_slope(standard=False, n=12))
        assert not w.last_statistics_notes, w.last_statistics_notes
        assert w.statusBar().currentMessage().startswith("PF = ")
        sw = w._stats_window
        assert sw.lbl_factor_report.isHidden()
        x, _y, item = self._axes_labels(sw, "histogram")
        assert x == "Factor of safety" and item == "Histogram of FoS"
        _x, y, _item = self._axes_labels(sw, "convergence")
        assert y == "Mean factor of safety"

    def test_the_sensitivity_plot_too(self):
        w = self._window(_slope(analysis_type=None, sens=True))
        _x, y, _item = self._axes_labels(w._stats_window, "sensitivity")
        assert y == "Over-design factor"

    def test_interpret_asks_the_statistics_run_and_not_compute(self):
        """Interpret is opened on a deterministic run and keeps that run's
        report; its two statistics plots read the report of the run that
        produced the statistics, which the main window keeps."""
        from ogr_core.project import FactorReport
        from ogr_gui.interpret_window import InterpretWindow

        class _Parent:
            last_statistics_factor_report = None

        class _Window:
            def parent(self):
                return self._parent

        probe = _Window()
        probe._parent = _Parent()
        assert InterpretWindow._stat_factored(probe) is False
        probe._parent.last_statistics_factor_report = FactorReport(
            standard="eurocode7_da1c2", applied=True)
        assert InterpretWindow._stat_factored(probe) is True


# ======================================================================
class TestOneDoor:
    def test_the_default_preparation_is_the_analysis_one(self):
        """What the closure reads: the default ``prepare`` of the three
        runs is ``prepare_analysis_project``, by AST and not by name."""
        import ast
        import inspect

        from ogr_core.statistics import probabilistic
        tree = ast.parse(inspect.getsource(probabilistic._analysis_copy))
        called = {n.func.id for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "prepare_analysis_project" in called, called
        for fn in (probabilistic.run_global_minimum,
                   probabilistic.run_overall_slope):
            assert "_analysis_copy" in inspect.getsource(fn), fn.__name__
        from ogr_core.statistics import sensitivity
        assert "_analysis_copy" in inspect.getsource(
            sensitivity.run_sensitivity)

    def test_the_cohesion_factor_is_the_documented_one(self):
        """The premise of every ratio above, from the code's own table:
        DA1-C2 divides c' and tan φ' by 1.25 (EN 1997-1, Annex A)."""
        from ogr_core.project import apply_design_factors
        p = _slope()
        f = apply_design_factors(p)[0]
        c0 = p.materials[0].strength.params["cohesion"]
        c1 = f.materials[0].strength.params["cohesion"]
        assert math.isclose(c1, c0 / 1.25, rel_tol=1e-15)
