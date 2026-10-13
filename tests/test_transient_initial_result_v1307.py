# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.307 (D295) — the state a transient starts from (t = 0) is stored apart
from the stages, and *Interpret Groundwater* offers it first.

The defect, from the GUI test of 0.1.284 (H12): with a drawdown of one stage
the selector of *Interpret Groundwater* had only "1: t = 86400 [BC]", so the
window could not show where the field started from. The field existed — the
steady analysis of the initial conditions is solved by every transient, D268
publishes whether it converged and D277 made it the steady door's to the
bit — but ``TransientSeepageSolver.solve_transient`` kept it in a local.

The reference shows the initial state first in its Interpret, and it is not
one of its stages. Putting it in ``project.transient_results`` would have
moved every stage index that the API, the agent and the pairing of
``run_transient_stability`` read by number, so it is kept apart
(``project.transient_initial_result``, the owner's decision of 2026-10-13),
and the agent reads it with ``stage="initial"``.

What these tests protect:

* the initial state IS the steady analysis of the initial conditions, to the
  bit (consistency with a validated door, rule 1), on the rectangular
  Gardner dam of ``test_initial_steady_v1281``; and it differs from stage 1,
  which evolved;
* read through the API it is a closed form: in the aquifer of
  ``test_groundwater_ops_v1200`` (validated against the erfc step response)
  both sides start at H0, so the initial field is H = H0 at every node;
  ``stage=0`` is still the first stage, and the stage rows did not grow;
* the window: the first entry is "0: t = 0 (initial state)" — "estado
  inicial" in Spanish — choosing it shows that field, the last stage is still
  the one shown on opening, and ``_on_stage(i)`` is still stage i;
* it is saved and reopened, and only when there is one: a project without a
  transient writes no key (its file and its fingerprint do not change), and a
  file from before this version opens without it and without the entry;
* a new mesh and a steady analysis drop it, and undoing a computation gives
  it back.
"""
from __future__ import annotations

import atexit
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

L, H, H1, H2, H1_LOW = 20.0, 12.0, 10.0, 2.0, 6.0
K = 1.0e-5


def _dam(h_left):
    """The rectangular Gardner dam of ``test_initial_steady_v1281``, meshed,
    with ``h_left`` upstream and H2 downstream (each with its seepage face
    above). Returns (project, conditions)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.settings import GroundwaterMethod
    from ogr_fem2d.mesh import generate_mesh_for_project
    from ogr_fem2d.solvers.seepage import BCType, SeepageBoundaryConditions
    p = Project("D295")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(L, 0), Vertex(L, H),
                             Vertex(0, H)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="dam", unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(
        ks=K, model=PermeabilityModel.GARDNER, gardner_a=1.0, gardner_n=3.0,
        wc_alpha=3.6, specific_storage=1e-4)
    p.materials = [m]
    p.fem_mesh = generate_mesh_for_project(p, target_size=0.7)
    mesh = p.fem_mesh
    b = SeepageBoundaryConditions()
    tol = 1e-6 * L
    for nid in sorted(mesh.boundary_node_ids()):
        x, y = mesh.nodes[nid].x, mesh.nodes[nid].y
        if abs(x) < tol:
            b.add_node(nid, BCType.TOTAL_HEAD if y <= h_left + tol
                       else BCType.UNKNOWN, h_left)
        elif abs(x - L) < tol:
            b.add_node(nid, BCType.TOTAL_HEAD if y <= H2 + tol
                       else BCType.UNKNOWN, H2)
        elif abs(y - H) < tol:
            b.add_node(nid, BCType.UNKNOWN)
    p.seepage_bcs = b
    p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
    return p, b


def _drawdown():
    """The dam starting full (H1 upstream) and drawn down to H1_LOW over
    one hour: the initial conditions are the full ones, the current (and
    the stage's) the low ones."""
    p, low = _dam(H1_LOW)
    _q, full = _dam(H1)
    gw = p.settings.groundwater
    gw.set_transient(True, [{"time": 3600.0, "label": "1 h"}], time_steps=2)
    gw.transient_initial_bcs = full.to_dict()
    p.seepage_bcs = low
    return p


class TestTheInitialStateIsTheSteadyAnalysis:
    def test_to_the_bit(self):
        from ogr_slip2d.transient_stability import solve_project_groundwater
        steady_p, _full = _dam(H1)
        steady = solve_project_groundwater(steady_p)
        assert steady.converged
        p = _drawdown()
        stages = solve_project_groundwater(p)
        start = p.transient_initial_result
        assert start is not None
        assert start.total_head == steady.total_head
        assert start.notes["time"] == 0.0 and start.notes["initial_state"]
        # control: the stage evolved away from it
        assert stages[0].total_head != start.total_head
        assert len(p.transient_results) == 1

    def test_a_steady_analysis_drops_it(self):
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = _drawdown()
        solve_project_groundwater(p)
        assert p.transient_initial_result is not None
        p.settings.groundwater.set_transient(False, [])
        solve_project_groundwater(p)
        assert p.transient_initial_result is None

    def test_a_new_mesh_drops_it_and_says_so(self):
        from ogr_core.project.rules import set_fem_mesh
        from ogr_fem2d.mesh import generate_mesh_for_project
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = _drawdown()
        solve_project_groundwater(p)
        dropped = set_fem_mesh(p, generate_mesh_for_project(
            p, target_size=1.0))
        assert "initial state of the transient" in dropped
        assert p.transient_initial_result is None


class TestTheFile:
    def test_saved_and_reopened(self):
        from ogr_core.project import Project
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = _drawdown()
        solve_project_groundwater(p)
        d = json.loads(json.dumps(p.to_dict()))
        assert "transient_initial_result" in d
        back = Project.from_dict(d)
        start = back.transient_initial_result
        assert start is not None
        assert start.to_dict() == p.transient_initial_result.to_dict()
        assert max(abs(a - b) for a, b in zip(
            start.total_head, p.transient_initial_result.total_head)) < 1e-6
        assert start.pore_pressure          # rebuilt by restore_derived

    def test_written_only_when_there_is_one(self):
        """A key always present would change the file and the model's
        fingerprint of every project without a transient."""
        from ogr_core.project import Project
        from ogr_slip2d.transient_stability import solve_project_groundwater
        assert "transient_initial_result" not in Project("x").to_dict()
        p, _b = _dam(H1)
        solve_project_groundwater(p)
        assert "transient_initial_result" not in p.to_dict()

    def test_a_file_from_before_opens_without_it(self):
        from ogr_core.project import Project
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = _drawdown()
        solve_project_groundwater(p)
        d = json.loads(json.dumps(p.to_dict()))
        del d["transient_initial_result"]
        back = Project.from_dict(d)
        assert back.transient_initial_result is None
        assert len(back.transient_results) == 1


# ----------------------------------------------------------------------
def _interpret(p, w=None):
    import matplotlib
    matplotlib.use("Agg")
    from ogr_gui.interpret_groundwater_window import (
        InterpretGroundwaterWindow)
    return InterpretGroundwaterWindow(p, p.seepage_result,
                                      w._gw_solver if w else None, None)


class TestTheWindow:
    def _computed(self):
        """The drawdown of ``test_transient_v130`` through the window's own
        Compute Groundwater."""
        from test_transient_v130 import TestStageFactorsOfSafety
        QApplication.instance() or QApplication([])
        return TestStageFactorsOfSafety()._drawdown(times=(1e4, 1e6),
                                                    calc_sf=False)

    def test_the_first_entry_is_the_initial_state(self):
        p, w = self._computed()
        iw = None
        try:
            start = p.transient_initial_result
            assert start is not None
            iw = _interpret(p, w)
            cbo = iw.cbo_stage
            assert cbo.count() == len(p.transient_results) + 1
            assert cbo.itemText(0) == "0: t = 0 (initial state)"
            assert cbo.itemText(1).startswith("1: t = 10000")
            # opening still shows the last stage
            assert cbo.currentIndex() == cbo.count() - 1
            assert iw.result is p.transient_results[-1]
            cbo.setCurrentIndex(0)
            assert iw.result is start
            assert "t = 0" in iw.status.text()
            assert "initial state" in iw.status.text()
            cbo.setCurrentIndex(1)
            assert iw.result is p.transient_results[0]
            # _on_stage(i) is still stage i
            iw._on_stage(0)
            assert iw.result is p.transient_results[0]
        finally:
            if iw is not None:
                iw.close()
            p.is_dirty = False
            w.close()

    def test_in_spanish(self):
        from ogr_gui.i18n import current_language, set_language
        p, w = self._computed()
        before = current_language()
        set_language("es")
        iw = None
        try:
            iw = _interpret(p, w)
            assert iw.cbo_stage.itemText(0) == "0: t = 0 (estado inicial)"
            iw.cbo_stage.setCurrentIndex(0)
            assert "estado inicial" in iw.status.text()
        finally:
            set_language(before)
            if iw is not None:
                iw.close()
            p.is_dirty = False
            w.close()

    def test_no_entry_without_it(self):
        """A transient computed before this version never stored it."""
        p, w = self._computed()
        iw = None
        try:
            p.transient_initial_result = None
            iw = _interpret(p, w)
            assert iw.cbo_stage.count() == len(p.transient_results)
            assert iw.cbo_stage.itemText(0).startswith("1: ")
        finally:
            if iw is not None:
                iw.close()
            p.is_dirty = False
            w.close()

    def test_undo_gives_it_back(self):
        p, w = self._computed()
        try:
            start = json.dumps(p.transient_initial_result.to_dict(),
                               sort_keys=True)
            p.settings.groundwater.set_transient(False, [])
            w._compute_groundwater()
            assert p.transient_initial_result is None
            assert w.command_stack.history()[0][-1] == "Compute groundwater"
            w.act_undo()
            assert p.transient_initial_result is not None
            assert json.dumps(p.transient_initial_result.to_dict(),
                              sort_keys=True) == start
        finally:
            p.is_dirty = False
            w.close()


# ----------------------------------------------------------------------
L_AQ, H_AQ, K_AQ, SS_AQ = 50.0, 5.0, 1.0e-4, 1.0e-3
H0, H1_AQ = 100.0, 110.0
_WS: list = []
_CACHE: dict = {}
_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 5.0, "friction_angle": 30.0}}


def _aquifer():
    """The aquifer of ``test_groundwater_ops_v1200`` (validated against the
    erfc step response): H0 on both sides at t = 0, then H1 on the left."""
    if "aquifer" not in _CACHE:
        from ogr_api import Workspace, call
        ws = Workspace()
        atexit.register(ws.shutdown)
        pid = call(ws, "project_new", name="D295")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [L_AQ, 0], [L_AQ, H_AQ], [0, H_AQ]],
            "materials": [{"name": "Soil", "unit_weight": 20,
                           "strength": _SOIL}]})
        call(ws, "hydraulic_set", project_id=pid, material="Soil",
             properties={"ks": K_AQ, "specific_storage": SS_AQ})
        call(ws, "mesh_generate", project_id=pid, target_size=1.0)
        _set = dict(project_id=pid, bc_type="total_head")
        call(ws, "seepage_bc_set", side="left", value=H1_AQ, **_set)
        call(ws, "seepage_bc_set", side="right", value=H0, **_set)
        call(ws, "seepage_bc_set", project_id=pid, bc_type="nodal_flow",
             side="ground", value=0.0)
        call(ws, "transient_set", project_id=pid,
             stages=[{"time": 200.0, "label": "t0"},
                     {"time": 1000.0, "label": "t1"}],
             initial={"base": "current", "assign": [
                 {"bc_type": "total_head", "side": "left", "value": H0}]},
             time_steps=20)
        run = call(ws, "groundwater_run", project_id=pid, wait_seconds=300)
        assert run["written_back"], run
        _CACHE["aquifer"] = (ws, pid, run)
    return _CACHE["aquifer"]


class TestTheAgent:
    def test_the_initial_state_is_h0_everywhere(self):
        """The closed form: both sides at H0 and no flow elsewhere."""
        from ogr_api import call
        ws, pid, _run = _aquifer()
        out = call(ws, "groundwater_results", project_id=pid,
                   stage="initial")
        assert out["field"] == "initial state (t = 0)"
        lo, hi = out["summary"]["total_head_m"]
        assert abs(lo - H0) < 1e-6 and abs(hi - H0) < 1e-6, (lo, hi)
        first = call(ws, "groundwater_results", project_id=pid, stage=0)
        assert first["field"].startswith("stage 0")
        assert first["summary"]["total_head_m"][1] > H0 + 5.0

    def test_the_stage_rows_did_not_grow(self):
        from ogr_api import call
        ws, pid, run = _aquifer()
        out = call(ws, "groundwater_results", project_id=pid, view="stages")
        assert [r["stage"] for r in out["stages"]] == [0, 1]
        assert out["initial_state"]["converged"] is True
        assert out["initial_state"]["notes"]["time"] == 0.0
        stored = call(ws, "groundwater_results", result_id=run["result_id"],
                      stage="initial", view="point", point_xy=[25.0, 2.5])
        assert abs(stored["at"]["total_head_m"] - H0) < 1e-6

    def test_model_render_draws_it(self):
        from ogr_api import call
        ws, pid, _run = _aquifer()
        out = call(ws, "model_render", project_id=pid, field="total_head",
                   stage="initial", width=400, height=300)
        assert out["png"][:8] == b"\x89PNG\r\n\x1a\n"

    def test_refusals(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws, pid, _run = _aquifer()
        try:
            call(ws, "groundwater_results", project_id=pid, stage="first")
        except InvalidArgument as e:
            assert "'initial'" in str(e), str(e)
        else:
            raise AssertionError("stage='first' was read")
        steady = call(ws, "project_new", name="steady")["project_id"]
        call(ws, "model_define", project_id=steady, spec={
            "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
            "materials": [{"name": "Soil", "unit_weight": 20,
                           "strength": _SOIL}]})
        call(ws, "mesh_generate", project_id=steady, target_size=2.0)
        call(ws, "seepage_bc_set", project_id=steady, bc_type="total_head",
             side="left", value=8.0)
        call(ws, "seepage_bc_set", project_id=steady, bc_type="total_head",
             side="right", value=2.0)
        call(ws, "groundwater_run", project_id=steady, wait_seconds=120)
        try:
            call(ws, "groundwater_results", project_id=steady,
                 stage="initial")
        except Conflict:
            pass
        else:
            raise AssertionError("a steady field has an initial state")
