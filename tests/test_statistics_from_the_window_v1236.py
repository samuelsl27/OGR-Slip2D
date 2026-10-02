# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D246 — a statistical run can be started on the project the window holds.

**The invariant**: the statistical engine copies the model once per sample
(``clone_project``), and that copy must not drag along whoever is watching
the model. A project bound to the main window carries the window's own
method among its listeners (``MainWindow._attach_project`` adds
``self._on_project_event``), and ``copy.deepcopy`` copies a bound method by
deep-copying the object it is bound to — the window, which does not copy.
Measured on v0.1.235 untouched: Compute Statistics, from the menu, on any
project the window had attached (new, opened or the demo), raised
``TypeError: cannot pickle 'MainWindow' object`` out of the menu action,
and the window said nothing. Both pieces date from v0.1.59.

**Why the suite never saw it**: every statistics test of the interface
hands the window a project by ASSIGNMENT (``w.project = p``), and the only
listener that leaves behind is the canvas's lambda, which ``deepcopy``
shares instead of copying. The window builds its projects through
``_attach_project``, so that is how these tests build theirs.

Nothing here fixes a factor of safety: what is pinned is that the run
happens, that the copy keeps the model and drops the watchers, and that the
operations layer's copy is the same recipe.

Regla 5: the windows are kept in a module list (Qt destroys the children of
a collected window) and nothing global is changed.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
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


_WINDOWS: list = []


def _app():
    return QApplication.instance() or QApplication([])


def _slope(name="d246"):
    """The small homogeneous slope of ``test_design_factor_report_gui_v1165``
    with a random cohesion and a Global Minimum run of 20 samples."""
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
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    p.add_material(Material(
        name="Silty clay", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0)))
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.methods.num_slices = 25
    p.settings.search.grid_nx = 3
    p.settings.search.grid_ny = 3
    p.settings.search.radius_increment = 2
    v = [x for x in available_variables(p) if x.param == "cohesion"][0]
    v.distribution = Distribution(DistributionType.NORMAL, mean=10.0,
                                  std_dev=2.0, rel_min=6.0, rel_max=6.0)
    p.random_variables = [v]
    st = p.settings.statistics
    st.probabilistic_analysis = True
    st.num_samples = 20
    st.sampling_method = "latin_hypercube"
    return p


def _attached(project=None):
    """A window holding ``project`` the way the application holds one."""
    from ogr_gui.main_window import MainWindow

    _app()
    w = MainWindow()
    _WINDOWS.append(w)
    w._attach_project(project if project is not None else _slope())
    # ``_info`` is a modal message box; recorded instead, so a refusal
    # cannot block the suite without a display.
    w.shown_info = []
    w._info = lambda *a, **_k: w.shown_info.append(a)
    return w


# ======================================================================
@_requires_qt
class TestThePremise:
    """Why the old copy could not work, pinned rather than narrated."""

    def test_the_window_watches_its_project_with_its_own_method(self):
        w = _attached()
        owners = [getattr(cb, "__self__", None) for cb in w.project._listeners]
        assert w in owners, w.project._listeners

    def test_a_bare_deepcopy_of_that_project_drags_the_window_along(self):
        w = _attached()
        try:
            copy.deepcopy(w.project)
        except TypeError as exc:
            assert "MainWindow" in str(exc), exc
        else:                                       # pragma: no cover
            raise AssertionError("the premise is gone: deepcopy copied a "
                                 "project watched by the window")


# ======================================================================
@_requires_qt
class TestTheEngineCopiesTheModelNotTheWatchers:

    def test_clone_project_copies_a_window_project(self):
        from ogr_core.statistics.random_variables import clone_project
        w = _attached()
        clone = clone_project(w.project)
        assert clone is not w.project
        assert clone._listeners == []
        assert clone.to_dict() == w.project.to_dict()

    def test_the_clone_shares_nothing_with_the_model(self):
        from ogr_core.statistics.random_variables import clone_project
        w = _attached()
        clone = clone_project(w.project)
        clone.materials[0].strength.params["cohesion"] = 99.0
        assert w.project.materials[0].strength.params["cohesion"] == 10.0
        # And the window still watches the MODEL, not the copy.
        owners = [getattr(cb, "__self__", None) for cb in w.project._listeners]
        assert w in owners

    def test_a_sample_keeps_the_region_cache_and_a_job_copy_drops_it(self):
        """The two contracts of the one recipe: a sample is copied warm,
        as the bare ``deepcopy`` copied it, and the operations layer's copy
        cold, as it always was."""
        from ogr_api.snapshot import detached_copy as api_copy
        from ogr_core.statistics.random_variables import clone_project
        w = _attached()
        w.project.resolve_regions()
        assert w.project._regions_cache is not None
        assert clone_project(w.project)._regions_cache is not None
        assert api_copy(w.project)._regions_cache is None

    def test_the_copy_pickles(self):
        """What a copy handed to another process needs; the model itself
        does not pickle while the window watches it."""
        from ogr_core.statistics.random_variables import clone_project
        w = _attached()
        again = pickle.loads(pickle.dumps(clone_project(w.project)))
        assert again.to_dict() == w.project.to_dict()


# ======================================================================
@_requires_qt
class TestComputeStatisticsRunsFromTheWindow:

    def test_the_menu_action_produces_a_probabilistic_result(self):
        w = _attached()
        w._compute_statistics()
        assert not w.shown_info, w.shown_info
        res = w._prob_result
        assert res is not None and res.ok, getattr(res, "notes", None)
        assert res.reported.statistics.n == 20
        assert "PF = " in w.statusBar().currentMessage()

    def test_a_sensitivity_run_too(self):
        p = _slope()
        p.settings.statistics.probabilistic_analysis = False
        p.settings.statistics.sensitivity_analysis = True
        p.settings.statistics.sensitivity_intervals = 4
        w = _attached(p)
        w._compute_statistics()
        assert not w.shown_info, w.shown_info
        assert w._sens_result is not None and w._sens_result.ok

    def test_the_model_is_not_modified(self):
        w = _attached()
        before = w.project.to_dict()
        w._compute_statistics()
        assert w.project.to_dict() == before
