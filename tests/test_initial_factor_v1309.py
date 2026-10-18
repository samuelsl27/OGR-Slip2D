# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.309 (D312) — the factor of safety of a transient's initial state
(t = 0), computed whenever a stage asks for factors.

The finding, while investigating D294: the reference shows the initial state
with its factor of safety ("the slope is quite stable at this time", its
tutorial on transient groundwater with slope stability), and the
verification bank publishes it (02-102: 1.745 and 1.815 for the initial
steady state, which its script reproduces by slipping a stage at t = 0 past
``set_transient``). Neither the window nor an agent could ask for it:
``set_transient`` wants stage times above zero, and the initial state is not
a stage. The engine already knew how — a zero-span stage with *Calculate SF*,
with the water of the initial conditions.

The owner's decision (2026-10-13): automatic, with no new setting — when a
stage asks for factors, the initial state gets them too, on
``outcome.initial`` and on the notes of ``project.transient_initial_result``
(saved with it, D295). No stage index moves.

What these tests protect:

* consistency with paths already validated (rule 1): the factor of the
  initial state IS, to the bit, the factor of a zero-span stage at t = 0 in
  the same run, and the factor of the steady analysis of the initial
  conditions through the steady door (D277 for the field, the same search
  for the factor);
* control: with no stage flagged, or nothing coupled, it is not computed;
* the stage factors are those of a run without it (the one more search
  leaves them alone);
* it reaches the history (``fos_history`` starts at t = 0), the Interpret
  Groundwater entry "0:" and the agent's ``initial_state``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

METHODS = ["bishop_simplified"]


def _drawdown(stages=(1e4,), calc_sf=True, t0_stage=False):
    """The drawdown of ``test_transient_v130``: full (45 / 30 m) at t = 0,
    the stages at 28 / 26 m. ``t0_stage`` adds a zero-span stage at t = 0
    flagged Calculate SF, written directly as the bank's 02-102 does."""
    from test_slide_validation_ej1 import _ej1_project
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
    from ogr_core.materials import PorePressureType
    from ogr_core.project.settings import GroundwaterMethod
    from ogr_fem2d.mesh import generate_mesh_for_project
    from ogr_fem2d.solvers import BCType, default_boundary_conditions
    from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
    p = _ej1_project()
    gw = p.settings.groundwater
    gw.method = GroundwaterMethod.FEA_STEADY.value
    gw.set_advanced_option("transient")
    gw.transient_time_steps = 3
    for m in p.materials:
        m.hydraulic = HydraulicProperties(
            ks=1e-5, model=PermeabilityModel.GARDNER,
            gardner_a=1.0, gardner_n=3.0, specific_storage=1e-4)
        m.pore_pressure = PorePressureType.FEM_SEEPAGE
    p.fem_mesh = generate_mesh_for_project(p, target_elements=150)
    p.settings.search.grid_nx = 4
    p.settings.search.grid_ny = 4
    mesh = p.fem_mesh
    sides = boundary_sides(mesh)

    def mk(hl, hr):
        b = default_boundary_conditions(mesh)
        for n in sides["Left edge"]:
            b.add_node(n, BCType.TOTAL_HEAD, hl)
        for n in sides["Right edge"]:
            b.add_node(n, BCType.TOTAL_HEAD, hr)
        return b

    full = mk(45.0, 30.0)
    low = mk(28.0, 26.0)
    gw.transient_initial_bcs = full.to_dict()
    gw.transient_stages = (
        ([{"time": 0.0, "calculate_sf": True, "label": "t = 0"}]
         if t0_stage else [])
        + [{"time": t, "calculate_sf": calc_sf, "bcs": low.to_dict()}
           for t in stages])
    p.seepage_bcs = low
    return p, full


class TestTheInitialFactorIsAFactorAlreadyValidated:
    def test_it_is_the_zero_span_stage_at_t_zero(self):
        from ogr_slip2d.transient_stability import run_transient_stability
        p, _full = _drawdown(t0_stage=True)
        out = run_transient_stability(p, METHODS)
        assert out.stages[0].result.notes["time_steps"] == 0
        assert out.initial is not None
        assert out.initial.factors, out.warnings
        assert out.initial.factors == out.stages[0].factors
        start = p.transient_initial_result
        assert start.notes["fos"] == out.initial.factors
        assert start.notes["fos_min"] == min(out.initial.factors.values())

    def test_it_is_the_steady_analysis_of_the_initial_conditions(self):
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.transient_stability import (run_transient_stability,
                                                    solve_project_groundwater)
        p, _full = _drawdown()
        out = run_transient_stability(p, METHODS)
        q, full = _drawdown()
        q.settings.groundwater.set_transient(False, [])
        q.seepage_bcs = full
        steady = solve_project_groundwater(q)
        assert steady.total_head == p.transient_initial_result.total_head
        crit = run_analysis(q, METHODS).results["bishop_simplified"].critical
        assert out.initial.factors == {"bishop_simplified": crit.fos}
        # NOT asserted: that the stage is lower. Here the water drops BEHIND
        # the crest (45 -> 28 m on the left edge, the crest side), not in a
        # reservoir against the face, and the factor rises: 0.862 at t = 0,
        # 0.889 and 0.904 at the two stages (measured, v0.1.309).


class TestOnlyWhenAsked:
    def test_no_stage_asks_for_factors(self):
        from ogr_slip2d.transient_stability import run_transient_stability
        p, _full = _drawdown(calc_sf=False)
        out = run_transient_stability(p, METHODS)
        assert out.initial is None
        assert "fos" not in p.transient_initial_result.notes

    def test_nothing_couples(self):
        from ogr_core.materials import PorePressureType
        from ogr_slip2d.transient_stability import run_transient_stability
        p, _full = _drawdown()
        for m in p.materials:
            m.pore_pressure = PorePressureType.NONE
        out = run_transient_stability(p, METHODS)
        assert out.initial is None
        assert "fos" not in p.transient_initial_result.notes


class TestItReachesTheHistory:
    def test_history_window_and_agent(self):
        from PySide6.QtWidgets import QApplication

        from ogr_api.results import groundwater_summary
        from ogr_slip2d.transient_stability import (fos_history,
                                                    run_transient_stability)
        p, _full = _drawdown(stages=(1e4, 1e6))
        out = run_transient_stability(p, METHODS)
        f0 = out.initial.factors["bishop_simplified"]
        series = fos_history(p.transient_results, p.transient_initial_result)
        assert series[0][1][0] == 0.0 and series[0][2][0] == f0
        assert series[0][1][1:] == [1e4, 1e6]
        summary = groundwater_summary(p)
        given = summary["initial_state"]["notes"]["fos"]["bishop_simplified"]
        assert abs(given - f0) < 1e-9, (given, f0)
        assert [r["stage"] for r in summary["stages"]] == [0, 1]
        QApplication.instance() or QApplication([])
        import matplotlib
        matplotlib.use("Agg")
        from ogr_gui.interpret_groundwater_window import (
            InterpretGroundwaterWindow)
        iw = InterpretGroundwaterWindow(p, p.seepage_result, None, None)
        try:
            iw.cbo_stage.setCurrentIndex(0)
            # v0.1.324 (D315) — the method by its name
            assert "FoS Bishop Simplified=" in iw.status.text()
        finally:
            iw.close()
