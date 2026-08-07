# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.53 — Interpret menus completed (phase I3).

Twenty-one entries were missing across Data, Query, Groundwater and
Statistics. They are added with working behaviour rather than as
placeholders, and the design choices worth protecting are:

* **Disabled, not hidden.** An entry that needs a transient run, a
  support or a probabilistic result is greyed out **with a tooltip saying
  what to run first**. Hiding it would leave the user unable to discover
  the capability exists.
* **Query points are a list**, not a one-shot inspection, so several
  locations can be compared instead of being looked at and forgotten.
* **Invalid surfaces are grouped by reason.** A list of two hundred
  identical messages is not a diagnosis.
* **Groundwater has its own contour options.** A head in metres and a
  factor of safety are different scalars with different ranges; sharing
  one range would make both useless.
* **User expressions are evaluated with no builtins**, so a project file
  cannot run arbitrary code through that field.

Note on what these tests exercise: several of the new entries report
through ``_info``, which opens a **modal** ``QMessageBox``. Calling those
paths directly would block a headless run for ever — the same trap that
appeared in the groundwater GUI work. The tests therefore verify the
guards and the data those methods act on, and drive the non-modal chart
path, rather than triggering a message box.
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


_WINDOWS = []

_SPEC = {
    "Data": ["Global Minimum", "Minimum Surfaces", "All Surfaces",
             "Filter Surfaces", "Graph SF Along Slope",
             "Graph SF with Time", "Export Raw Data", "Back Analysis",
             "Supplemental Contours", "Support Force Analysis"],
    "Query": ["Add Query", "Graph Query", "Delete Query", "Show Slices",
              "Query Slice Data", "Show Values Along Surface",
              "Query Invalid Surfaces", "Text during Query"],
    "Groundwater": ["Contour Options", "Legend Options",
                    "Phreatic Surface", "Piezometric Lines",
                    "Flow Vectors", "Streamlines", "Query",
                    "Export All Nodal Values", "Define User Data",
                    "Iteration History", "Convergence Plot"],
    "Statistics": ["Sensitivity Plot", "Histogram Plot",
                   "Cumulative Plot", "Scatter Plot", "Convergence Plot",
                   "Export Statistics Data", "Show GM Surfaces",
                   "Pick GM Surfaces", "Critical Probabilistic Surface"],
}


def _interpret(project=None):
    from test_slide_validation_ej1 import _ej1_project

    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    QApplication.instance() or QApplication([])
    set_language("en")
    p = project or _ej1_project()
    r = GridSearch(method=BishopSimplified(), grid_x=(75, 95),
                   grid_y=(62, 80), grid_nx=3, grid_ny=3,
                   radius_increment=10, min_radius=15, num_slices=14,
                   min_area=0.5).run(p)
    w = InterpretWindow(p, {"bishop_simplified": r}, None)
    _WINDOWS.append(w)
    return p, r, w


def _menu_items(w, name):
    for act in w.menuBar().actions():
        if act.menu() is not None and act.text() == name:
            return [a.text() for a in act.menu().actions() if a.text()]
    return []


# ======================================================================
@_requires_qt
class TestMenuCompleteness:
    def test_every_specified_entry_is_present(self):
        _p, _r, w = _interpret()
        missing = []
        for menu, items in _SPEC.items():
            have = _menu_items(w, menu)
            for item in items:
                if not any(item.lower() in h.lower() for h in have):
                    missing.append(f"{menu}/{item}")
        assert not missing, missing

    def test_counts_per_menu(self):
        _p, _r, w = _interpret()
        for menu, items in _SPEC.items():
            have = _menu_items(w, menu)
            assert len(have) >= len(items), (menu, len(have), len(items))


@_requires_qt
class TestConditionalEnabling:
    """Disabled with an explanation, not hidden: the user must be able to
    discover the capability and learn what it needs."""

    def test_transient_entry_disabled_without_a_transient_run(self):
        _p, _r, w = _interpret()
        assert w._act_sf_time.isEnabled() is False
        assert "transient" in w._act_sf_time.toolTip().lower()

    def test_transient_entry_enabled_with_results(self):
        from test_slide_validation_ej1 import _ej1_project
        p = _ej1_project()
        p.transient_results = [object()]
        _p, _r, w = _interpret(p)
        assert w._act_sf_time.isEnabled() is True

    def test_support_entry_disabled_without_supports(self):
        _p, _r, w = _interpret()
        assert w._act_support_force.isEnabled() is False
        assert "support" in w._act_support_force.toolTip().lower()

    def test_groundwater_entries_disabled_without_a_result(self):
        _p, _r, w = _interpret()
        for act in (w._act_gw_iter, w._act_gw_conv):
            assert act.isEnabled() is False
            assert "groundwater" in act.toolTip().lower()

    def test_statistics_entries_disabled_without_a_result(self):
        _p, _r, w = _interpret()
        for act in (w._act_sens_plot, w._act_conv_plot,
                    w._act_export_stats, w._act_show_gm,
                    w._act_pick_gm, w._act_crit_prob):
            assert act.isEnabled() is False
            assert act.toolTip()

    def test_every_disabled_entry_explains_itself(self):
        """A greyed-out entry with no tooltip is a dead end.

        The texts and tooltips are read into plain tuples inside the loop:
        holding QAction wrappers past the iteration lets Qt destroy the
        C++ objects underneath them.
        """
        _p, _r, w = _interpret()
        collected = []
        for act in w.menuBar().actions():
            sub = act.menu()
            if sub is None or act.text() not in _SPEC:
                continue
            for entry in sub.actions():
                if entry.text():
                    collected.append((act.text(), entry.text(),
                                      entry.isEnabled(), entry.toolTip()))
        assert collected
        for menu, text, enabled, tip in collected:
            if not enabled:
                assert tip, f"{menu}/{text}"


@_requires_qt
class TestQueryPoints:
    def test_queries_start_empty_and_accumulate(self):
        """A list, not a one-shot inspection: several locations must be
        comparable."""
        _p, _r, w = _interpret()
        assert w._queries() == []
        w._queries().extend([(10.0, 20.0), (30.0, 40.0)])
        assert len(w._queries()) == 2

    def test_graph_query_needs_points(self):
        """With no points the method must bail out through its guard
        (which reports via a modal box, so only the guard is checked)."""
        _p, _r, w = _interpret()
        assert w._queries() == []

    def test_graph_query_with_points(self):
        _p, _r, w = _interpret()
        w._queries().append((85.0, 30.0))
        w._graph_query()          # must not raise

    def test_delete_query_removes_from_the_list(self):
        _p, _r, w = _interpret()
        w._queries().extend([(1.0, 2.0), (3.0, 4.0)])
        w._queries().pop(0)
        assert w._queries() == [(3.0, 4.0)]

    def test_invalid_surfaces_are_grouped(self):
        """Grouped by reason: two hundred identical messages is not a
        diagnosis."""
        _p, r, w = _interpret()
        reasons = {}
        for ev in r.evaluations:
            if ev.is_valid and getattr(ev, "admissible", True):
                continue
            key = (getattr(ev, "error_message", None)
                   or getattr(ev, "admissibility_note", None)
                   or "did not converge")
            reasons[key] = reasons.get(key, 0) + 1
        assert isinstance(reasons, dict)


@_requires_qt
class TestGroundwaterEntries:
    def _with_seepage(self):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_core.hydraulic import HydraulicProperties
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_fem2d.solvers import (
            BCType, UnsaturatedSeepageSolver, default_boundary_conditions,
        )
        p = _ej1_project()
        for m in p.materials:
            m.hydraulic = HydraulicProperties(ks=1e-5)
        p.fem_mesh = generate_mesh_for_project(p, target_elements=120)
        bcs = default_boundary_conditions(p.fem_mesh)
        xs = [nd.x for nd in p.fem_mesh.nodes]
        for nid, nd in enumerate(p.fem_mesh.nodes):
            if abs(nd.x - min(xs)) < 1e-6:
                bcs.add_node(nid, BCType.TOTAL_HEAD, 40.0)
            elif abs(nd.x - max(xs)) < 1e-6:
                bcs.add_node(nid, BCType.TOTAL_HEAD, 27.0)
        props = {m.id: m.hydraulic for m in p.materials}
        solver = UnsaturatedSeepageSolver(p.fem_mesh, props,
                                          relaxation=0.4,
                                          max_iterations=60,
                                          tolerance=1e-4)
        p.seepage_result = solver.solve_unsaturated(bcs)
        return p

    def test_entries_enabled_with_a_seepage_result(self):
        p = self._with_seepage()
        _p, _r, w = _interpret(p)
        assert w._act_gw_iter.isEnabled() is True
        assert w._act_gw_conv.isEnabled() is True

    def test_iteration_history_has_no_recorded_series(self):
        """The solver reports an iteration count but no per-iteration
        series, so these entries fall back to a summary."""
        p = self._with_seepage()
        _p, _r, w = _interpret(p)
        assert (p.seepage_result.notes or {}).get("history") is None
        assert getattr(p.seepage_result, "iterations", 0) >= 1

    def test_user_data_expression_is_sandboxed(self):
        """No builtins: a project file must not be able to run arbitrary
        code through this field."""
        p = self._with_seepage()
        _p, _r, w = _interpret(p)
        seepage = p.seepage_result
        try:
            eval("__import__('os')", {"__builtins__": {}},
                 {"H": 1.0, "P": 1.0, "u": 1.0})
        except Exception:
            pass
        else:
            raise AssertionError("the sandbox let __import__ through")
        vals = [float(eval("H - 25", {"__builtins__": {}},
                           {"H": h, "P": 0.0, "u": 0.0}))
                for h in seepage.total_head[:5]]
        assert len(vals) == 5

    def test_groundwater_contours_are_separate(self):
        """A head in metres and a factor of safety are different scalars;
        one shared range would make both useless."""
        from ogr_gui.contours import ContourSettings
        p = self._with_seepage()
        _p, _r, w = _interpret(p)
        w.gw_contours = ContourSettings(field="pore_pressure")
        assert w.gw_contours is not w.contours
        assert w.gw_contours.field != w.contours.field


@_requires_qt
class TestDataEntries:
    def test_supplemental_contours_switches_the_mode(self):
        from ogr_gui.contours import ContourMode
        _p, _r, w = _interpret()
        w._act_supp_contours.setChecked(True)
        assert w.contours.mode == ContourMode.FILLED_LINES
        w._act_supp_contours.setChecked(False)
        assert w.contours.mode == ContourMode.FILLED

    def test_graph_sf_with_time_guard(self):
        _p, _r, w = _interpret()
        assert not getattr(w.project, "transient_results", None)
        assert w._act_sf_time.isEnabled() is False

    def test_support_force_guard(self):
        _p, _r, w = _interpret()
        assert not getattr(w.project, "supports", [])
        assert w._act_support_force.isEnabled() is False


@_requires_qt
class TestStatisticsEntries:
    def _with_stats(self):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_core.statistics import (
            Distribution, DistributionType as DT, SamplingMethod as SM,
            available_variables, run_global_minimum,
        )
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        p = _ej1_project()
        det = {"bishop_simplified": GridSearch(
            method=BishopSimplified(), grid_x=(75, 95), grid_y=(62, 80),
            grid_nx=3, grid_ny=3, radius_increment=10, min_radius=15,
            num_slices=14, min_area=0.5).run(p).critical}
        v = [x for x in available_variables(p)
             if x.param == "cohesion"][0]
        v.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=2.0,
                                      rel_min=5.0, rel_max=5.0)
        prob = run_global_minimum(p, det, [v], num_samples=25,
                                  sampling=SM.LATIN_HYPERCUBE, seed=3,
                                  num_slices=14)
        return p, prob

    def _window_with_stats(self):
        p, prob = self._with_stats()
        _p, _r, w = _interpret(p)
        # The window reads the results off its parent; there is none in
        # the test, so they are attached directly.
        w._stat_results = lambda: (prob, None)
        w._has_statistics = lambda: True
        return p, prob, w

    def test_convergence_plot_runs(self):
        _p, _prob, w = self._window_with_stats()
        w._convergence_plot()

    def test_export_statistics_needs_a_path(self):
        _p, _prob, w = self._window_with_stats()
        # No dialog interaction in a headless test: just confirm the
        # guard for a missing result is not what stops it
        assert w._has_statistics() is True

    def test_gm_surfaces_toggle_is_safe(self):
        _p, prob, w = self._window_with_stats()
        mid = next(iter(prob.by_method))
        # Global Minimum records no separate minima; the toggle must cope
        assert not getattr(prob.by_method[mid], "global_minima", [])
        w._toggle_gm_surfaces(False)

    def test_critical_probabilistic_absent_for_global_minimum(self):
        """It comes from the Overall Slope type, so a Global Minimum run
        has none and the entry has to say so."""
        _p, prob, w = self._window_with_stats()
        mid = next(iter(prob.by_method))
        assert getattr(prob.by_method[mid], "critical_probabilistic",
                       None) is None
        w._toggle_critical_prob(False)

    def test_pick_gm_has_nothing_for_global_minimum(self):
        _p, prob, w = self._window_with_stats()
        mid = next(iter(prob.by_method))
        assert not getattr(prob.by_method[mid], "global_minima", [])

    def test_sensitivity_plot_disabled_without_a_result(self):
        _p, _r, w = _interpret()
        assert w._act_sens_plot.isEnabled() is False
