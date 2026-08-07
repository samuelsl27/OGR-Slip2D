# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.38 — Statistics interface (Phase P5, the last of the probabilistic
plan).

Checks the interface rules rather than the pixels:

* the Statistics options only become available once a probabilistic or a
  sensitivity analysis is enabled in Project Settings, and Compute only
  once at least one random variable exists;
* the dialog offers the full catalogue of randomisable parameters,
  presents the RELATIVE limits and reports the resulting actual range,
  and Cancel really cancels;
* Compute routes to Global Minimum or Overall Slope according to the
  configured analysis type;
* every plot in the results window renders without raising, and the
  scatter data pairs sampled values with the matching factors of safety.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import matplotlib
    matplotlib.use("Agg")
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _app():
    return QApplication.instance() or QApplication([])


def _project(prob=True, sens=False, n=20, atype="global_minimum"):
    from test_slide_validation_ej1 import _ej1_project
    p = _ej1_project()
    st = p.settings.statistics
    st.probabilistic_analysis = prob
    st.sensitivity_analysis = sens
    st.num_samples = n
    st.sampling_method = "latin_hypercube"
    st.seed = 7
    st.analysis_type = atype
    st.sensitivity_intervals = 8
    p.settings.search.grid_nx = 3
    p.settings.search.grid_ny = 3
    return p


def _window(project):
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.canvas.set_project(project)
    w.project = project
    w._update_statistics_actions()
    return w


def _define_vars(project, names=("cohesion", "friction_angle")):
    from ogr_core.statistics import (
        Distribution, DistributionType as DT, available_variables,
    )
    mat = project.materials[0]
    out = []
    for rv in available_variables(project):
        if rv.param in names and rv.target_id == mat.id:
            rv.distribution = Distribution(
                DT.NORMAL, mean=rv.distribution.mean,
                std_dev=0.15 * abs(rv.distribution.mean) or 1.0,
                rel_min=0.3 * abs(rv.distribution.mean) or 1.0,
                rel_max=0.3 * abs(rv.distribution.mean) or 1.0)
            out.append(rv)
    project.random_variables = out
    return out


# ======================================================================
@_requires_qt
class TestMenuAvailability:
    def _state(self, w):
        return {k: w._actions[k].isEnabled()
                for k in ("stat_vars", "stat_compute", "stat_show")}

    def test_disabled_when_no_analysis_enabled(self):
        _app()
        w = _window(_project(prob=False, sens=False))
        st = self._state(w)
        assert st["stat_vars"] is False
        assert st["stat_compute"] is False

    def test_variables_enabled_but_compute_needs_variables(self):
        _app()
        w = _window(_project())
        st = self._state(w)
        assert st["stat_vars"] is True
        assert st["stat_compute"] is False
        assert st["stat_show"] is False

    def test_compute_enabled_once_variables_exist(self):
        _app()
        p = _project()
        _define_vars(p)
        w = _window(p)
        assert w._actions["stat_compute"].isEnabled() is True

    def test_sensitivity_alone_also_enables(self):
        _app()
        w = _window(_project(prob=False, sens=True))
        assert w._actions["stat_vars"].isEnabled() is True


# ======================================================================
@_requires_qt
class TestRandomVariablesDialog:
    def _dlg(self, project=None):
        _app()
        from ogr_gui.dialogs.random_variables_dialog import (
            RandomVariablesDialog,
        )
        p = project or _project()
        return p, RandomVariablesDialog(p, None)

    def test_catalogue_is_offered(self):
        from ogr_core.statistics import available_variables
        p, d = self._dlg()
        assert d.list_available.count() == len(available_variables(p))
        assert d.list_available.count() > 10

    def test_add_and_remove(self):
        _p, d = self._dlg()
        d.list_available.setCurrentRow(0)
        d._add()
        assert d.list_defined.count() == 1
        d.list_defined.setCurrentRow(0)
        d._remove()
        assert d.list_defined.count() == 0

    def test_adding_twice_is_a_no_op(self):
        _p, d = self._dlg()
        d.list_available.setCurrentRow(0)
        d._add()
        d._add()
        assert d.list_defined.count() == 1

    def test_actual_range_from_relative_limits(self):
        """The dialog takes RELATIVE limits and must report the actual
        range as mean - rel_min .. mean + rel_max."""
        _p, d = self._dlg()
        d.list_available.setCurrentRow(0)
        d._add()
        d.list_defined.setCurrentRow(0)
        mean = d.sp_mean.value()
        d.sp_rmin.setValue(2.0)
        d.sp_rmax.setValue(3.0)
        key = d._current_key
        dist = d.defined[key].distribution
        assert abs(dist.low - (mean - 2.0)) < 1e-9
        assert abs(dist.high - (mean + 3.0)) < 1e-9
        assert f"{dist.low:g}" in d.lbl_actual.text()

    def test_standard_deviation_only_where_used(self):
        from ogr_core.statistics import DistributionType as DT
        _p, d = self._dlg()
        d.list_available.setCurrentRow(0)
        d._add()
        d.list_defined.setCurrentRow(0)
        for t, expected in ((DT.NORMAL, True), (DT.UNIFORM, False),
                            (DT.TRIANGULAR, False), (DT.LOGNORMAL, True)):
            d.cbo_dist.setCurrentIndex(d.cbo_dist.findData(t))
            assert d.sp_std.isEnabled() is expected, t

    def test_correlation_offers_the_other_variables(self):
        _p, d = self._dlg()
        for row in (0, 1):
            d.list_available.setCurrentRow(row)
            d._add()
        d.list_defined.setCurrentRow(0)
        # "(none)" plus the other defined variable
        assert d.cbo_corr_with.count() == 2

    def test_accept_saves_to_project(self):
        p, d = self._dlg()
        d.list_available.setCurrentRow(0)
        d._add()
        d._accept()
        assert len(p.random_variables) == 1

    def test_cancel_does_not_save(self):
        p, d = self._dlg()
        before = list(getattr(p, "random_variables", []))
        d.list_available.setCurrentRow(0)
        d._add()
        d.reject()
        assert list(p.random_variables) == before

    def test_removing_clears_dangling_correlation(self):
        _p, d = self._dlg()
        for row in (0, 1):
            d.list_available.setCurrentRow(row)
            d._add()
        keys = list(d.defined)
        d.defined[keys[1]].correlated_with = keys[0]
        d.defined[keys[1]].correlation = -0.5
        d.list_defined.setCurrentRow(0)
        d._remove()
        remaining = next(iter(d.defined.values()))
        assert remaining.correlated_with is None


# ======================================================================
@_requires_qt
class TestComputeAndResults:
    def test_global_minimum_run(self):
        _app()
        p = _project(n=15)
        _define_vars(p)
        w = _window(p)
        w._compute_statistics()
        assert w._prob_result is not None
        assert w._prob_result.analysis_type == "global_minimum"
        assert w._actions["stat_show"].isEnabled() is True

    def test_overall_slope_run(self):
        _app()
        p = _project(n=6, atype="overall_slope")
        _define_vars(p, ("cohesion",))
        w = _window(p)
        w._compute_statistics()
        assert w._prob_result is not None
        assert w._prob_result.analysis_type == "overall_slope"

    def test_sensitivity_run(self):
        _app()
        p = _project(prob=False, sens=True)
        _define_vars(p)
        w = _window(p)
        w._compute_statistics()
        assert w._sens_result is not None
        assert w._sens_result.ranking()

    def test_both_analyses_together(self):
        _app()
        p = _project(prob=True, sens=True, n=12)
        _define_vars(p)
        w = _window(p)
        w._compute_statistics()
        assert w._prob_result is not None
        assert w._sens_result is not None

    def test_build_search_reuses_the_configured_search(self):
        """Overall Slope must rebuild EXACTLY the configured search."""
        _app()
        from ogr_gui.main_window import _ComputeWorker
        p = _project()
        s = _ComputeWorker(p, ["bishop_simplified"]).build_search(
            "bishop_simplified")
        assert s is not None
        assert s.method.METHOD_ID == "bishop_simplified"

    def test_project_untouched_by_the_run(self):
        _app()
        p = _project(n=10)
        _define_vars(p)
        before = p.to_dict()
        _window(p)._compute_statistics()
        assert p.to_dict() == before


# ======================================================================
@_requires_qt
class TestStatisticsWindow:
    def _run(self, prob=True, sens=True, n=12):
        _app()
        p = _project(prob=prob, sens=sens, n=n)
        _define_vars(p)
        w = _window(p)
        w._compute_statistics()
        from ogr_gui.statistics_window import StatisticsWindow
        return p, w, StatisticsWindow(p, w._prob_result, w._sens_result,
                                      None)

    def test_all_plots_render(self):
        _p, _w, sw = self._run()
        assert sw.cbo_plot.count() == 3
        for i in range(sw.cbo_plot.count()):
            sw.cbo_plot.setCurrentIndex(i)
            sw._redraw()          # must not raise
        assert sw.canvas is not None

    def test_histogram_status_reports_headline_numbers(self):
        _p, _w, sw = self._run(sens=False)
        sw.cbo_plot.setCurrentIndex(0)
        sw._redraw()
        txt = sw.status.text()
        assert "probability of failure" in txt
        assert "reliability index" in txt

    def test_only_available_plots_are_listed(self):
        _p, _w, sw = self._run(prob=True, sens=False)
        kinds = {sw.cbo_plot.itemData(i)
                 for i in range(sw.cbo_plot.count())}
        assert kinds == {"histogram", "convergence"}

    def test_sensitivity_only(self):
        _p, _w, sw = self._run(prob=False, sens=True)
        kinds = {sw.cbo_plot.itemData(i)
                 for i in range(sw.cbo_plot.count())}
        assert kinds == {"sensitivity"}

    def test_scatter_pairs_samples_with_factors(self):
        _p, w, sw = self._run(sens=False, n=15)
        key = w._prob_result.variables[0]
        pts = sw.scatter_data("bishop_simplified", key)
        st = w._prob_result.by_method["bishop_simplified"].statistics
        assert len(pts) == st.n
        assert [q[1] for q in pts] == st.values

    def test_scatter_unknown_variable(self):
        _p, _w, sw = self._run(sens=False, n=10)
        assert sw.scatter_data("bishop_simplified", "nope") == []

    def test_method_selector_lists_methods(self):
        _p, w, sw = self._run(n=10)
        assert sw.cbo_method.count() >= 1


# ======================================================================
class TestSettings:
    def test_new_fields_round_trip(self):
        from ogr_core.project import Project
        p = _project() if _QT else None
        if p is None:
            from test_slide_validation_ej1 import _ej1_project
            p = _ej1_project()
            p.settings.statistics.analysis_type = "overall_slope"
            p.settings.statistics.seed = 42
        p.settings.statistics.analysis_type = "overall_slope"
        p.settings.statistics.seed = 42
        p.settings.statistics.sensitivity_intervals = 25
        p2 = Project.from_dict(p.to_dict())
        st = p2.settings.statistics
        assert st.analysis_type == "overall_slope"
        assert st.seed == 42
        assert st.sensitivity_intervals == 25

    def test_defaults(self):
        from ogr_core.project.settings import StatisticsSettings
        st = StatisticsSettings()
        assert st.analysis_type == "global_minimum"
        assert st.num_samples == 1000
        assert st.sensitivity_intervals == 50
        assert st.seed is None
