# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.306 (D294) — a transient with no stages can be saved, and it is not
computed in silence.

The defect, from the GUI test of 0.1.284 (H10): ticking the transient
analysis, pressing *Capture as initial state* and OK answered "Define at
least one stage, or switch the transient analysis off". The natural order
of work — capture the initial state, close, change the boundary conditions
in their own dialog, come back and add the stage — needed a placeholder
stage. The refusal lived in ``GroundwaterSettings.set_transient``, shared
with the agent's ``transient_set``.

And the other half, found while measuring: a transient with no stages was
ALREADY reachable (the radio button of Project Settings, ``settings_set``,
a file, a script), and the three doors that compute the groundwater fell
back to a STEADY solve with the current conditions — ignoring the initial
state — without a word.

The owner's decision (2026-10-13, after reading what the reference does: its
initial state is not a stage, and a transient is that state plus the
instants at which it is observed): the dialog accepts it and the doors
refuse to compute it, saying why (``rules.transient_without_stages``).
Computing the initial state alone was rejected: it would become the field
the stability analysis reads, weighted with the water of the CURRENT
conditions.

What these tests protect:

* the H10 order of work through the real window: capture, OK with no stage,
  change the conditions, come back and add the stage — one step each, the
  captured initial state kept and the stage with the new conditions;
* the dialog says which initial state it will store, and that there is no
  stage yet; Clear initial state is written on OK, and Cancel writes
  nothing; without a mesh the capture buttons are off (no modal box);
* the three doors refuse, say why and write nothing — the window (status
  bar, also in Spanish), ``solve_project_groundwater`` and the API's
  ``groundwater_run``, whose ``project_validate`` says it beforehand — also
  when the transient was switched on by Project Settings or ``settings_set``;
* control (rule 7 the other way round): with one stage, all of them compute.
"""
from __future__ import annotations

import atexit
import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()
_KEY = "has no stages"


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


@contextlib.contextmanager
def _no_modals():
    """Without a screen nothing may be modal: a message box fails the test
    instead of waiting for ever — which is what the code of 0.1.305 did
    here, answering OK with no stage with a modal warning."""
    from PySide6.QtWidgets import QMessageBox

    def modal(*a, **k):
        raise AssertionError(f"a modal box: {a[1:3]!r}")

    with contextlib.ExitStack() as stack:
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.is_dirty = False
    return w


def _clean(w):
    w.command_stack.clear()
    w.project.is_dirty = False


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _with_mesh(w, elements=80):
    from PySide6.QtWidgets import QInputDialog
    with _swap(QInputDialog, "getInt",
               staticmethod(lambda *a, **k: (elements, True))):
        w._generate_fem_mesh()
    assert w.project.fem_mesh is not None


def _heads(w, h_left, h_right):
    """Total heads on the two vertical edges of the demo slope (x = 0 is
    25 m high, x = 50 is 15 m), as Set Boundary Conditions would store
    them."""
    from ogr_fem2d.solvers import BCType
    from ogr_gui.dialogs.boundary_conditions_dialog import boundary_sides
    bcs = w._seepage_bcs()
    sides = boundary_sides(w.project.fem_mesh)
    for nid in sides["Left edge"]:
        bcs.add_node(nid, BCType.TOTAL_HEAD, h_left)
    for nid in sides["Right edge"]:
        bcs.add_node(nid, BCType.TOTAL_HEAD, h_right)
    w.project.seepage_bcs = bcs
    return bcs


def _bcs(head):
    from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
    b = SeepageBoundaryConditions()
    b.add_node(0, BCType.TOTAL_HEAD, head)
    return b


# ----------------------------------------------------------------------
class TestTheDialog:
    def test_it_accepts_no_stages_and_keeps_the_capture(self):
        from ogr_core.project.settings import GroundwaterSettings
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        QApplication.instance() or QApplication([])
        gw = GroundwaterSettings()
        with _no_modals():
            dlg = TransientStagesDialog(gw, current_bcs=_bcs(9.0))
            dlg.chk_enabled.setChecked(True)
            dlg._capture_initial()
            dlg._accept()
        assert dlg.result() == 1
        assert gw.transient is True and gw.transient_stages == []
        assert gw.transient_initial_bcs == _bcs(9.0).to_dict()

    def test_clear_is_written_on_ok_and_cancel_writes_nothing(self):
        from ogr_core.project.settings import GroundwaterSettings
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        QApplication.instance() or QApplication([])
        gw = GroundwaterSettings()
        gw.transient_initial_bcs = _bcs(9.0).to_dict()
        with _no_modals():
            dlg = TransientStagesDialog(gw, current_bcs=_bcs(4.0))
            dlg._clear_initial()
            dlg.reject()
            assert gw.transient_initial_bcs == _bcs(9.0).to_dict()
            dlg = TransientStagesDialog(gw, current_bcs=_bcs(4.0))
            assert dlg.b_clear_initial.isEnabled()
            dlg._clear_initial()
            assert not dlg.b_clear_initial.isEnabled()
            dlg._accept()
        assert gw.transient_initial_bcs is None

    def test_it_says_which_initial_state_and_that_there_is_no_stage(self):
        from ogr_core.project.settings import GroundwaterSettings
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        from ogr_gui.i18n import current_language, set_language
        QApplication.instance() or QApplication([])
        before = current_language()
        set_language("en")
        try:
            dlg = TransientStagesDialog(GroundwaterSettings(),
                                        current_bcs=_bcs(9.0))
            assert "current boundary conditions" in dlg.lbl_initial.text()
            assert dlg.lbl_no_stages.text() == ""
            dlg.chk_enabled.setChecked(True)
            assert "No stages yet" in dlg.lbl_no_stages.text()
            dlg._capture_initial()
            assert "captured" in dlg.lbl_initial.text()
            assert "1 nodes" in dlg.lbl_initial.text()
            dlg._add_row(10.0, False, "")
            assert dlg.lbl_no_stages.text() == ""
            dlg.table.selectRow(0)
            dlg._delete()
            assert "No stages yet" in dlg.lbl_no_stages.text()
            set_language("es")
            dlg = TransientStagesDialog(GroundwaterSettings(),
                                        current_bcs=_bcs(9.0))
            dlg.chk_enabled.setChecked(True)
            assert "Aún no hay etapas" in dlg.lbl_no_stages.text()
            assert "Estado inicial" in dlg.lbl_initial.text()
        finally:
            set_language(before)

    def test_without_a_mesh_there_is_nothing_to_capture(self):
        from PySide6.QtWidgets import QPushButton

        from ogr_core.project.settings import GroundwaterSettings
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        from ogr_gui.i18n import tr
        QApplication.instance() or QApplication([])
        with _no_modals():
            dlg = TransientStagesDialog(GroundwaterSettings())
            buttons = {b.text(): b for b in dlg.findChildren(QPushButton)}
            for name in ("Capture current BCs", "Capture as initial state"):
                assert not buttons[tr(name)].isEnabled(), name
            dlg._capture_initial()
            dlg._capture()
        assert dlg._initial_bcs is None


# ----------------------------------------------------------------------
class TestTheOrderOfWork:
    def test_initial_state_first_then_the_stage(self):
        """H10 through the real window: each visit one step."""
        import ogr_gui.dialogs.transient_stages_dialog as tsd
        real = tsd.TransientStagesDialog

        def first_visit(self):
            self.chk_enabled.setChecked(True)
            self._capture_initial()
            self._accept()
            return self.result()

        def second_visit(self):
            self._add_row(86400.0, False, "drawdown")
            self.table.setCurrentCell(0, 0)
            self._capture()
            self._accept()
            return self.result()

        w = _window()
        try:
            _with_mesh(w)
            captured = _heads(w, 22.0, 12.0).to_dict()
            _clean(w)
            gw = w.project.settings.groundwater
            with _swap(real, "exec", first_visit), _no_modals():
                w._edit_transient_stages()
            assert w.command_stack.history() == (
                ["Transient groundwater"], [])
            assert gw.transient is True and gw.transient_stages == []
            assert gw.transient_initial_bcs == captured
            # the conditions change in their own dialog ...
            lowered = _heads(w, 15.0, 12.0).to_dict()
            assert lowered != captured
            # ... and the stage comes afterwards
            with _swap(real, "exec", second_visit), _no_modals():
                w._edit_transient_stages()
            assert gw.transient_initial_bcs == captured
            assert [s["time"] for s in gw.transient_stages] == [86400.0]
            assert gw.transient_stages[0]["bcs"] == lowered
            assert w.command_stack.history()[0][-1] == "Transient groundwater"
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestTheWindowRefuses:
    def test_nothing_is_computed_and_it_says_why(self):
        from ogr_gui.i18n import set_language
        w = _window()
        try:
            _with_mesh(w)
            _heads(w, 22.0, 12.0)
            w.project.settings.groundwater.set_advanced_option("transient")
            _clean(w)
            before = _json(w.project)
            with _no_modals():
                w._compute_groundwater()
            assert _KEY in w.statusBar().currentMessage()
            assert w.project.seepage_result is None
            assert w.project.transient_results == []
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            set_language("es")
            try:
                with _no_modals():
                    w._compute_groundwater()
                assert "no tiene etapas" in w.statusBar().currentMessage()
            finally:
                set_language("en")
        finally:
            _done(w)

    def test_switched_on_in_project_settings(self):
        """The radio button of Project Settings switches the transient on
        and adds no stage: that reached the steady solve before."""
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)

        def transient_ok(self):
            page = next(p for p in self.pages if hasattr(p, "rb_transient"))
            page.rb_transient.setChecked(True)
            self._ok()
            return self.result()

        w = _window()
        try:
            _with_mesh(w)
            _heads(w, 22.0, 12.0)
            _clean(w)
            with _swap(ProjectSettingsDialog, "exec", transient_ok), \
                    _no_modals():
                w.act_project_settings()
            gw = w.project.settings.groundwater
            assert gw.transient is True and gw.transient_stages == []
            with _no_modals():
                w._compute_groundwater()
            assert _KEY in w.statusBar().currentMessage()
            assert w.project.seepage_result is None
        finally:
            _done(w)

    def test_control_with_one_stage_it_computes(self):
        w = _window()
        try:
            _with_mesh(w)
            _heads(w, 22.0, 12.0)
            gw = w.project.settings.groundwater
            gw.set_transient(True, [{"time": 3600.0}], time_steps=2)
            _clean(w)
            with _no_modals():
                w._compute_groundwater()
            assert _KEY not in w.statusBar().currentMessage()
            assert len(w.project.transient_results) == 1
            assert w.project.seepage_result is w.project.transient_results[-1]
            assert w.command_stack.history() == (["Compute groundwater"], [])
        finally:
            _done(w)


# ----------------------------------------------------------------------
_WS = []
SOIL = {"model": "mohr_coulomb",
        "params": {"cohesion": 5.0, "friction_angle": 30.0}}


def _ws():
    if not _WS:
        from ogr_api import Workspace
        ws = Workspace()
        atexit.register(ws.shutdown)
        _WS.append(ws)
    return _WS[0]


def _meshed(name="D294"):
    """A 20 x 10 box, meshed, with heads 8 m and 2 m on its sides."""
    from ogr_api import call
    ws = _ws()
    pid = call(ws, "project_new", name=name)["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
        "materials": [{"name": "Soil", "unit_weight": 20,
                       "strength": SOIL}]})
    call(ws, "hydraulic_set", project_id=pid, material="Soil",
         properties={"ks": 1e-5, "specific_storage": 1e-4})
    call(ws, "mesh_generate", project_id=pid, target_size=2.0)
    for side, head in (("left", 8.0), ("right", 2.0)):
        call(ws, "seepage_bc_set", project_id=pid, bc_type="total_head",
             side=side, value=head)
    return ws, pid


def _state(ws, pid):
    return json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                      default=str)


def _refused(ws, pid):
    from ogr_api import NotConfigured, call
    before = _state(ws, pid)
    try:
        call(ws, "groundwater_run", project_id=pid)
    except NotConfigured as e:
        assert _KEY in str(e), str(e)
    else:
        raise AssertionError("groundwater_run computed a transient with no "
                             "stages")
    assert _state(ws, pid) == before


class TestTheEngineAndTheAgentRefuse:
    def test_the_engine(self):
        from ogr_core.project.rules import TRANSIENT_WITHOUT_STAGES
        from ogr_slip2d.analysis_runner import AnalysisNotConfigured
        from ogr_slip2d.transient_stability import solve_project_groundwater
        ws, pid = _meshed()
        p = ws.get(pid).project
        p.settings.groundwater.set_transient(True, [])
        try:
            solve_project_groundwater(p)
        except AnalysisNotConfigured as e:
            assert e.problems == [TRANSIENT_WITHOUT_STAGES]
        else:
            raise AssertionError("solve_project_groundwater solved it")
        assert p.seepage_result is None and p.transient_results == []

    def test_transient_set_accepts_it_and_groundwater_run_refuses(self):
        from ogr_api import call
        ws, pid = _meshed()
        out = call(ws, "transient_set", project_id=pid, stages=[],
                   initial={"base": "current", "assign": [
                       {"bc_type": "total_head", "side": "left",
                        "value": 2.0}]})
        assert out["transient"] is True and out["stages"] == []
        assert out["initial"] == "own conditions"
        assert any(_KEY in n for n in out["notes"]), out["notes"]
        notes = call(ws, "project_validate", project_id=pid)["model_notes"]
        assert any(_KEY in n for n in notes), notes
        _refused(ws, pid)

    def test_switched_on_by_settings_set(self):
        from ogr_api import call
        ws, pid = _meshed()
        call(ws, "settings_set", project_id=pid,
             changes={"groundwater.advanced_option": "transient"})
        _refused(ws, pid)

    def test_control_with_one_stage_they_compute(self):
        from ogr_api import call
        from ogr_slip2d.transient_stability import solve_project_groundwater
        ws, pid = _meshed()
        call(ws, "transient_set", project_id=pid,
             stages=[{"time": 3600.0}], time_steps=2)
        notes = call(ws, "project_validate", project_id=pid)["model_notes"]
        assert not any(_KEY in n for n in notes), notes
        run = call(ws, "groundwater_run", project_id=pid, wait_seconds=120)
        assert run["state"] == "done" and run["written_back"], run
        assert len(ws.get(pid).project.transient_results) == 1
        ws2, pid2 = _meshed("D294 engine")
        p = ws2.get(pid2).project
        p.settings.groundwater.set_transient(True, [{"time": 3600.0}],
                                             time_steps=2)
        assert len(solve_project_groundwater(p)) == 1
