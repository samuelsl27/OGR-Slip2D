# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.202 — the fourth block of corrections.

Invariants protected
--------------------
**Opening a file forgets the previous project.** New and the demo cleared
the results by hand and Open cleared none of them, so the results panel,
Interpret and Optimize Surfaces went on working with the previous
project's surfaces over the model just opened. The clearing now lives in
one place, ``MainWindow._attach_project``.

**The back analysis agrees with its solver** (rule 1: consistency with a
validated path). At the factor of safety the solver gives a surface with
no support, the support needed is zero. Janbu's sums multiplied each
resisting term by cos(alpha) where the solver divides by it (n_alpha =
cos(alpha)·m_alpha), and Janbu Corrected ignored the f0 the solver applies
at the end: 217 and 269 kN/m "needed" on a 10 m slope that already stood
at the target.

**A sample needs a factor of safety to count.** The reference defines the
probability of failure over the VALID analyses ("numtotal = total number
of VALID analyses") and reports m_alpha < 0.2 as an INVALID surface
(-112). The engines counted such samples; now they go to
``failed_samples`` with their code, and switching the m-alpha check off in
the project brings them back (rule 7).

**The grid's type is the groundwater method's**, as in the reference
("Set the desired Water Pressure Grid type in the Project Settings
dialog"). A file that also carries the grid's own type keeps its meaning,
and a grid built with a type the method contradicts is refused, not read
one way in silence.
"""
from __future__ import annotations

import atexit
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 6.0, "friction_angle": 22.0}}


def _ws():
    from ogr_api import Workspace
    ws = Workspace()
    atexit.register(ws.shutdown)
    return ws


def _slope(ws, soil=_SOIL, water=False):
    from ogr_api import call
    pid = call(ws, "project_new", name="Slope")["project_id"]
    spec = {"external": [[0, 0], [60, 0], [60, 20], [40, 20], [20, 10],
                         [0, 10]],
            "materials": [{"name": "Soil", "unit_weight": 19,
                           "strength": soil}]}
    if water:
        spec["water_table"] = {"points": [[0, 10], [20, 10], [40, 19],
                                          [60, 19]], "materials": "all"}
    call(ws, "model_define", project_id=pid, spec=spec)
    return pid


def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


# ======================================================================
# 1. Open
# ======================================================================
class TestOpenForgetsThePreviousProject:
    def test_nothing_of_the_previous_project_survives(self):
        if _qt() is None:
            return
        import tempfile

        from PySide6.QtWidgets import QFileDialog

        from ogr_core.project import Project
        from ogr_gui.main_window import MainWindow
        folder = Path(tempfile.mkdtemp(prefix="ogr_open_"))
        path = folder / "other.ogr"
        Project("Other").save(path)
        w = MainWindow()
        raw = QFileDialog.getOpenFileName
        QFileDialog.getOpenFileName = staticmethod(
            lambda *a, **k: (str(path), ""))
        try:
            sentinel = object()
            w.last_search_result = sentinel
            w.last_search_results = {"bishop_simplified": sentinel}
            w.last_compute_warnings = ["old"]
            w.last_statistics_notes = ["old"]
            w.last_factor_report = sentinel
            w._gw_solver = sentinel
            w.last_drawdown_sweep = sentinel
            w.act_open()
            assert w.project.name == "Other"
            assert w.last_search_result is None
            assert w.last_search_results == {}
            assert w.last_compute_warnings == []
            assert w.last_statistics_notes == []
            assert w.last_factor_report is None
            assert w._gw_solver is None and w.last_drawdown_sweep is None
        finally:
            QFileDialog.getOpenFileName = raw
            w.close()
            w.deleteLater()


# ======================================================================
# 2. The back analysis agrees with its solver
# ======================================================================
class TestTheBackAnalysisAgreesWithTheSolver:
    CIRCLES = ((25.0, 35.0, 27.0), (28.0, 40.0, 33.0))

    def test_no_support_is_needed_at_the_unsupported_factor(self):
        """For the three methods: the force needed to reach the factor the
        solver gives the surface unsupported is zero (to a small fraction
        of the sliding weight; Bishop keeps a 0.2 kN/m residual from its
        normal-force estimate). The old Janbu sums said 217 kN/m."""
        from ogr_slip2d.back_analysis import required_force
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        ws = _ws()
        p = ws.get(_slope(ws)).project
        for mid in ("janbu_simplified", "janbu_corrected",
                    "bishop_simplified"):
            gs = GridSearch(method=get_method(mid)(), num_slices=30,
                            min_area=0.0)
            for cx, cy, r in self.CIRCLES:
                res = gs.evaluate_circle(p, SlipCircle(
                    centre_x=cx, centre_y=cy, radius=r))
                assert res.is_valid, (mid, r)
                w = sum(s.weight for s in res.slices)
                ba = required_force(res.slices, res.surface, res.fos, mid,
                                    5.0)
                assert ba.active_force < 1e-4 * w, (mid, r, ba.active_force)
                assert ba.passive_force < 2e-4 * w, (mid, r,
                                                     ba.passive_force)

    def test_above_the_unsupported_factor_a_force_is_needed(self):
        """And the force grows from zero as the target rises (a control:
        a formula that always answered zero would pass the test above)."""
        from ogr_slip2d.back_analysis import required_force
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        ws = _ws()
        p = ws.get(_slope(ws)).project
        for mid in ("janbu_simplified", "janbu_corrected"):
            res = GridSearch(method=get_method(mid)(), num_slices=30,
                             min_area=0.0).evaluate_circle(
                p, SlipCircle(centre_x=25.0, centre_y=35.0, radius=27.0))
            f = [required_force(res.slices, res.surface, res.fos * k, mid,
                                5.0).active_force for k in (1.1, 1.3)]
            assert 0 < f[0] < f[1], (mid, f)


# ======================================================================
# 3. Inadmissible samples
# ======================================================================
#: A circle whose toe exit makes m_alpha cross 0.2 as the cohesion goes
#: from 0 to 6 kPa (measured: X at c = 0 and 2, admissible from c = 5).
_CIRCLE = (26.0, 16.0, 15.0)


def _screen_case():
    from ogr_core.statistics import (Distribution, DistributionType,
                                     available_variables)
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle
    ws = _ws()
    p = ws.get(_slope(ws, soil={"model": "mohr_coulomb", "params": {
        "cohesion": 3.0, "friction_angle": 35.0}}, water=True)).project
    circle = SlipCircle(centre_x=_CIRCLE[0], centre_y=_CIRCLE[1],
                        radius=_CIRCLE[2])
    det = GridSearch(method=get_method("bishop_simplified")(),
                     num_slices=25, min_area=0.0).evaluate_circle(p, circle)
    rv = next(v for v in available_variables(p)
              if v.key.endswith(":cohesion"))
    rv.distribution = Distribution(dist_type=DistributionType.UNIFORM,
                                   mean=3.0, rel_min=3.0, rel_max=3.0)
    return p, {"bishop_simplified": det}, rv


class TestASampleNeedsAFactorOfSafety:
    N = 30

    def _run(self, p, det, rv):
        from ogr_core.statistics import SamplingMethod, run_global_minimum
        return run_global_minimum(p, det, [rv], num_samples=self.N,
                                  sampling=SamplingMethod.LATIN_HYPERCUBE,
                                  seed=11, num_slices=25)

    def test_screened_samples_are_not_counted(self):
        from ogr_core.statistics import sample_pairs
        p, det, rv = _screen_case()
        m = self._run(p, det, rv).by_method["bishop_simplified"]
        assert m.failed_samples > 0 and m.statistics.n > 0
        assert m.statistics.n + m.failed_samples == self.N
        assert "-112 m-alpha" in m.notes["lost_by_cause"]
        # numtotal is the admissible samples, and the PF is over them.
        pf = sum(f < 1.0 for f in m.statistics.values) / m.statistics.n
        assert m.probability_of_failure == pf
        # Every sample kept is one the screen admits: low cohesions only
        # among the lost ones.
        kept = [v for _i, v, _f in sample_pairs(
            self._run(p, det, rv), "bishop_simplified", rv.key)]
        assert min(kept) > 2.0, min(kept)

    def test_switching_the_screen_off_brings_them_back(self):
        """Rule 7: the project's m-alpha setting moves the number."""
        p, det, rv = _screen_case()
        p.settings.advanced.check_m_alpha = False
        m = self._run(p, det, rv).by_method["bishop_simplified"]
        assert m.statistics.n == self.N and m.failed_samples == 0

    def test_an_inadmissible_critical_is_a_lost_search(self):
        from types import SimpleNamespace

        from ogr_core.statistics.probabilistic import (_search_failure,
                                                       counts_as_sample)
        crit = SimpleNamespace(is_valid=True, admissible=False, fos=1.2)
        assert not counts_as_sample(crit)
        assert _search_failure(None, SimpleNamespace(critical=crit)) == \
            "no admissible surface"


# ======================================================================
# 4. The grid's type is the method's
# ======================================================================
def _grid_project(method):
    from ogr_core.hydraulic import WaterPressureGrid
    ws = _ws()
    p = ws.get(_slope(ws)).project
    p.settings.groundwater.method = method
    p.water_pressure_grid = WaterPressureGrid(
        points=[(x, y, 30.0) for x in (0.0, 30.0, 60.0)
                for y in (0.0, 10.0, 20.0)], interpolation="idw")
    return p


class TestTheGridTypeIsTheMethods:
    def test_the_method_decides_the_conversion(self):
        """30 read as a total head, a pressure head and a pore pressure,
        at (30, 5): gamma_w (30 - 5), gamma_w 30 and 30 kPa."""
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        for method, expect in (("grid_total_head", 9.81 * 25.0),
                               ("grid_pressure_head", 9.81 * 30.0),
                               ("grid_pore_pressure", 30.0)):
            p = _grid_project(method)
            u = pore_pressure_at(p, Vertex(30.0, 5.0), p.materials[0])
            assert abs(u - expect) < 1e-9, (method, u)

    def test_a_file_keeps_what_it_meant(self):
        from ogr_core.project import Project
        p = _grid_project("grid_pore_pressure")
        d = p.to_dict()
        assert "value_type" not in d["water_pressure_grid"]
        d["water_pressure_grid"]["value_type"] = "total_head"
        p2 = Project.from_dict(d)
        assert p2.settings.groundwater.method == "grid_total_head"
        assert p2.water_pressure_grid.declared_type is None

    def test_a_contradicted_type_is_refused(self):
        from ogr_core.hydraulic import GridValueType, WaterPressureGrid
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = _grid_project("grid_pore_pressure")
        p.water_pressure_grid = WaterPressureGrid(
            points=[(0.0, 0.0, 1.0)], value_type=GridValueType.TOTAL_HEAD)
        probs = check_analysis_settings(p)
        assert any("grid_total_head" in m for m in probs), probs
        p.settings.groundwater.method = "grid_total_head"
        assert not any("water pressure grid" in m
                       for m in check_analysis_settings(p))

    def test_the_agent_sets_the_method_in_one_step(self):
        from ogr_api import call
        ws = _ws()
        pid = _slope(ws)
        out = call(ws, "water_grid_set", project_id=pid,
                   points=[[0, 0, 5.0], [60, 0, 5.0], [30, 20, 5.0]],
                   value_type="pressure_head")
        assert out["method"] == "grid_pressure_head"
        project = ws.get(pid).project
        assert project.settings.groundwater.method == "grid_pressure_head"
        call(ws, "project_history", project_id=pid, action="undo")
        assert project.water_pressure_grid is None
        assert project.settings.groundwater.method == "water_table"

    def test_the_action_needs_a_grid_method(self):
        if _qt() is None:
            return
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        try:
            w.project.settings.groundwater.method = "water_table"
            w.refresh_action_availability()
            assert not w._actions["wp_grid"].isEnabled()
            w.project.settings.groundwater.method = "grid_pore_pressure"
            w.refresh_action_availability()
            assert w._actions["wp_grid"].isEnabled()
        finally:
            w.close()
            w.deleteLater()
