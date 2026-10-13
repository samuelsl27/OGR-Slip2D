# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.305 (D292, D306) — the last family of the window's edits are undo
steps, and Cancel cancels.

Third family of D292: settings and search, statistics, surfaces and focus,
annotations, Import DXF and the terminal, 23 methods. With them the
inventory of ``test_window_undo_v1301`` is down to the two halves of a
vertex drag, which record the whole drag as one step.

D306 — four dialogs wrote into the model while open, and Cancel left it
written:

* *Project Settings* after Apply or Restore Defaults;
* the Optimize Settings inside *Surface Options*;
* the grid rectangle picked on the canvas for *Add Grid*, before OK;
* *Annotations*, which edits the layer live and had only OK (Esc kept it).

Each is now one undo step from opening to closing, and Cancel puts back
what the dialog wrote (the owner's decision: Apply included). Apply tells
the window, which refreshes the menus that depend on the settings. *Add
Grid* writes the picked rectangle on OK, no longer when it is picked, and a
pick still armed after Cancel writes nothing. *Annotations* gained Cancel.

Also here:

* *Back Analysis* no longer writes ``settings.back_analysis`` (the owner's
  decision, as ``back_analysis_run``): the values go to the run, and the
  last ones typed come back next time for this project;
* a terminal command that changes the model is one step, "Python script",
  as ``python_exec``; one that calls a step of the window is still one;
* undoing a change of the statistics settings refreshes the Statistics
  menu, as D281 did for the groundwater one.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()


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


def _answers(*values):
    it = iter(values)
    return staticmethod(lambda *a, **k: next(it))


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


def _accepted(w, name, act):
    before = _json(w.project)
    act()
    after = _json(w.project)
    assert after != before, name
    assert w.command_stack.history() == ([name], []), \
        w.command_stack.history()
    assert w.project.is_dirty, name
    w.act_undo()
    assert _json(w.project) == before, name
    w.act_redo()
    assert _json(w.project) == after, name


def _cancelled(w, act):
    before = _json(w.project)
    act()
    assert _json(w.project) == before
    assert w.command_stack.history() == ([], [])
    assert not w.project.is_dirty


def _a_line_annotation(w):
    from ogr_core.annotations import Annotation, AnnotationKind
    w.project.annotations.add(Annotation(kind=AnnotationKind.LINE,
                                         points=[(2.0, 2.0), (12.0, 8.0)]))
    w.project.annotations.add(Annotation(kind=AnnotationKind.TEXT,
                                         points=[(5.0, 30.0)], text="Note"))


# ----------------------------------------------------------------------
# D306: Cancel cancels
# ----------------------------------------------------------------------
class TestCancelCancels:
    def test_project_settings_cancel_after_apply_restores(self):
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        seen = {}

        def apply_then_cancel(self):
            # what Apply does: write into the live settings and say so
            self.settings.statistics.probabilistic_analysis = True
            self.settings.methods.num_slices = 77
            self.settings_applied.emit()
            seen["stat_vars"] = self.parent()._actions["stat_vars"].isEnabled()
            return 0

        def restore_then_cancel(self):
            self._defaults()
            return 0

        def apply_then_ok(self):
            self.settings.methods.num_slices = 77
            return 1

        w = _window()
        try:
            assert not w._actions["stat_vars"].isEnabled()
            with _swap(ProjectSettingsDialog, "exec", apply_then_cancel):
                _cancelled(w, w.act_project_settings)
            # Apply reached the window while the dialog was open, and
            # Cancel took it back
            assert seen["stat_vars"] is True
            assert not w._actions["stat_vars"].isEnabled()
            with _swap(ProjectSettingsDialog, "exec", restore_then_cancel):
                _cancelled(w, w.act_project_settings)
            with _swap(ProjectSettingsDialog, "exec", apply_then_ok):
                _accepted(w, "Change settings", w.act_project_settings)
        finally:
            _done(w)

    def test_surface_options_cancel_drops_optimize_settings(self):
        from ogr_gui.dialogs.grid_dialogs import SurfaceOptionsDialog
        from ogr_gui.dialogs.optimize_settings_dialog import (
            OptimizeSettingsDialog)

        def optimize_then(result):
            def run(self):
                self._on_optimize_settings()
                return result
            return run

        def write_123(self):
            self.project.settings.search.optimize_max_iterations = 123

        w = _window()
        try:
            assert w.project.settings.search.optimize_max_iterations != 123
            with _swap(OptimizeSettingsDialog, "exec", lambda self: 1), \
                    _swap(OptimizeSettingsDialog, "apply", write_123):
                with _swap(SurfaceOptionsDialog, "exec", optimize_then(0)):
                    _cancelled(w, w.act_surface_options)
                with _swap(SurfaceOptionsDialog, "exec", optimize_then(1)):
                    _accepted(w, "Change settings", w.act_surface_options)
            assert w.project.settings.search.optimize_max_iterations == 123
        finally:
            _done(w)

    def test_add_grid_cancel_drops_the_picked_rectangle(self):
        w = _window()
        try:
            before = _json(w.project)
            w.act_add_grid()
            dlg = w._active_grid_dialog
            w._begin_grid_pick()
            w._on_grid_picked(5.0, 30.0, 20.0, 40.0)
            # into the dialog, not the model
            assert _json(w.project) == before
            assert dlg.sb_xmin.value() == 5.0
            dlg.reject()
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            # a pick armed when the dialog was cancelled writes nothing
            w.act_add_grid()
            w._begin_grid_pick()
            w._active_grid_dialog.reject()
            w.canvas.segment_picked.emit(1.0, 26.0, 9.0, 36.0)
            assert _json(w.project) == before
            assert not w.project.is_dirty

            def pick_and_ok():
                w.act_add_grid()
                w._begin_grid_pick()
                w._on_grid_picked(5.0, 30.0, 20.0, 40.0)
                w._active_grid_dialog.accept()
            _accepted(w, "Change settings", pick_and_ok)
            s = w.project.settings.search
            assert (s.grid_x_min, s.grid_x_max, s.grid_y_min,
                    s.grid_y_max) == (5.0, 20.0, 30.0, 40.0)
        finally:
            _done(w)

    def test_annotations_cancel_restores_the_layer(self):
        from PySide6.QtWidgets import QDialogButtonBox
        from ogr_gui.dialogs.annotations_dialog import AnnotationsDialog

        def delete_first(result):
            def run(self):
                self.table.selectRow(0)
                self._delete()
                self._duplicate()
                return result
            return run

        w = _window()
        try:
            _a_line_annotation(w)
            _clean(w)
            dlg = AnnotationsDialog(w.project.annotations, w)
            box = dlg.findChild(QDialogButtonBox)
            assert box.button(QDialogButtonBox.Cancel) is not None
            dlg.setParent(None)
            with _swap(AnnotationsDialog, "exec", delete_first(0)):
                _cancelled(w, w._manage_annotations)
            with _swap(AnnotationsDialog, "exec", delete_first(1)):
                _accepted(w, "Edit annotations", w._manage_annotations)
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestSettingsAndSearch:
    def test_auto_grid_limits_and_axis(self):
        from PySide6.QtWidgets import QInputDialog
        from ogr_gui.dialogs.slope_limits_dialog import SlopeLimitsDialog
        w = _window()
        try:
            s = w.project.settings.search
            s.grid_x_min, s.grid_x_max = 5.0, 20.0
            s.grid_y_min, s.grid_y_max = 30.0, 40.0
            _clean(w)
            _accepted(w, "Change settings", w.act_auto_grid)
            _clean(w)
            with _swap(SlopeLimitsDialog, "exec", lambda self: 0):
                _cancelled(w, w._move_slope_limits)
            with _swap(SlopeLimitsDialog, "exec",
                       lambda self: SlopeLimitsDialog.Accepted), \
                    _swap(SlopeLimitsDialog, "validate", lambda self: ""), \
                    _swap(SlopeLimitsDialog, "values",
                          lambda self: (1.0, 45.0, None, None)):
                _accepted(w, "Change settings", w._move_slope_limits)
            _clean(w)
            _accepted(w, "Change settings", w._reset_slope_limits)
            _clean(w)
            with _swap(QInputDialog, "getDouble",
                       _answers((20.0, True), (0.0, False))):
                _cancelled(w, w._define_moment_axis)
            with _swap(QInputDialog, "getDouble",
                       _answers((20.0, True), (30.0, True))):
                _accepted(w, "Change settings", w._define_moment_axis)
            _clean(w)
            _accepted(w, "Change settings", w._reset_moment_axis)
        finally:
            _done(w)

    def test_define_limits_accepted_does_not_raise(self):
        """Found by the test above: ``_move_slope_limits`` compared the
        answer with ``dlg.Accepted``, and with PySide6 6.11 the enum
        shortcut exists on the class and NOT on an instance, so accepting
        Define Limits raised AttributeError every time. No test reached
        that line before."""
        from ogr_gui.dialogs.slope_limits_dialog import SlopeLimitsDialog
        w = _window()
        try:
            with _swap(SlopeLimitsDialog, "exec", lambda self: 1), \
                    _swap(SlopeLimitsDialog, "validate", lambda self: ""), \
                    _swap(SlopeLimitsDialog, "values",
                          lambda self: (2.0, 40.0, None, None)):
                w._move_slope_limits()
            s = w.project.settings.search
            assert (s.slope_limit_left, s.slope_limit_right) == (2.0, 40.0)
        finally:
            _done(w)

    def test_back_analysis_writes_no_setting_and_uses_what_was_typed(self):
        from PySide6.QtWidgets import QDialog, QDoubleSpinBox
        import ogr_slip2d.analysis_runner as runner
        calls, shown = [], []

        def fake_run(project, **kw):
            calls.append(kw)
            raise runner.AnalysisNotConfigured(["stop here"])

        def type_target(self):
            boxes = self.findChildren(QDoubleSpinBox)
            shown.append(boxes[0].value())
            boxes[0].setValue(1.7)
            return QDialog.DialogCode.Accepted

        w = _window()
        try:
            before = _json(w.project)
            with _swap(runner, "run_configured_back_analysis", fake_run), \
                    _swap(QDialog, "exec", type_target), \
                    _swap(w, "_info", lambda *a: None):
                w._back_analysis()
                w._back_analysis()
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            assert not w.project.is_dirty
            # rule 7: what is typed reaches the run
            assert calls[0]["target_fos"] == 1.7, calls
            # and comes back the next time
            assert shown == [w.project.settings.back_analysis.target_fos,
                             1.7], shown
        finally:
            _done(w)

    def test_random_variables(self):
        from ogr_core.statistics.random_variables import RandomVariable
        import ogr_gui.dialogs.random_variables_dialog as rvd

        class _Fake:
            result = 1

            def __init__(self, project, parent=None):
                self.project = project

            def exec(self):
                if self.result:
                    mid = self.project.materials[0].id
                    self.project.random_variables = [RandomVariable(
                        target_id=mid, param="cohesion")]
                return self.result

        class _No(_Fake):
            result = 0

        w = _window()
        try:
            with _swap(rvd, "RandomVariablesDialog", _No):
                _cancelled(w, w._edit_random_variables)
            with _swap(rvd, "RandomVariablesDialog", _Fake):
                _accepted(w, "Random variables", w._edit_random_variables)
        finally:
            _done(w)

    def test_undoing_a_statistics_setting_refreshes_its_menu(self):
        w = _window()
        try:
            def on():
                w.project.settings.statistics.probabilistic_analysis = True
            w._model_step("Change settings", on)
            assert w._actions["stat_vars"].isEnabled()
            w.act_undo()
            assert not w._actions["stat_vars"].isEnabled()
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestSurfacesAndFocus:
    def test_focus(self):
        from PySide6.QtWidgets import QInputDialog
        from ogr_slip2d.focus import FocusKind
        w = _window()
        try:
            with _swap(w, "_read_points", lambda title, n: [(20.0, 22.0)]), \
                    _swap(QInputDialog, "getDouble",
                          _answers((0.5, True))):
                _accepted(w, "Set focus object",
                          lambda: w._add_focus(FocusKind.POINT))
            _clean(w)
            # the first object, then its first action: Enable / disable
            with _swap(QInputDialog, "getItem",
                       staticmethod(lambda *a, **k: (a[3][0], True))):
                _accepted(w, "Set focus object", w._manage_focus)
            _clean(w)
            with _swap(QInputDialog, "getItem",
                       _answers(("(delete all)", True))):
                _accepted(w, "Delete focus objects", w._manage_focus)
        finally:
            _done(w)

    def test_user_surfaces(self):
        from PySide6.QtWidgets import QInputDialog
        w = _window()
        try:
            with _swap(w, "_read_points", lambda title, n: [(30.0, 40.0)]), \
                    _swap(QInputDialog, "getDouble",
                          _answers((25.0, True))):
                _accepted(w, "Add user surface",
                          w._add_surface_centre_radius)
            _clean(w)
            _accepted(w, "Add user surface",
                      lambda: w._on_surface_3pt_picked(20.0, 25.0, 30.0,
                                                       18.0, 40.0, 15.0))
            _clean(w)
            with _swap(QInputDialog, "getItem",
                       _answers(("(delete all)", True))):
                _accepted(w, "Delete user surfaces", w._manage_user_surfaces)
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestAnnotations:
    def test_draw_image_visibility_and_delete_all(self):
        from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
        from ogr_core.annotations import AnnotationKind
        w = _window()
        try:
            with _swap(QInputDialog, "getText",
                       _answers(("", False))):
                _cancelled(w, lambda: w._start_annotation(
                    AnnotationKind.LINE))
            with _swap(QInputDialog, "getText",
                       _answers(("0,0 10,10", True))):
                _accepted(w, "Set annotation",
                          lambda: w._start_annotation(AnnotationKind.LINE))
            _clean(w)
            with _swap(QFileDialog, "getOpenFileName",
                       staticmethod(lambda *a, **k: ("photo.png", ""))):
                _accepted(w, "Set annotation", w._add_image)
            _clean(w)
            _accepted(w, "Set annotation",
                      lambda: w._set_annotations_visible(False))
            _clean(w)
            with _swap(QMessageBox, "question",
                       staticmethod(lambda *a, **k: QMessageBox.No)):
                _cancelled(w, w._delete_all_annotations)
            with _swap(QMessageBox, "question",
                       staticmethod(lambda *a, **k: QMessageBox.Yes)):
                _accepted(w, "Delete annotations", w._delete_all_annotations)
        finally:
            _done(w)

    def test_convert_tool_to_boundary(self):
        from PySide6.QtWidgets import QInputDialog
        w = _window()
        try:
            _a_line_annotation(w)
            _clean(w)
            pick = staticmethod(lambda *a, **k: (
                a[3][0] if a[2] == "Annotation:" else "Material Boundary",
                True))
            with _swap(QInputDialog, "getItem", pick):
                _accepted(w, "Add Material Boundary",
                          w._convert_tool_to_boundary)
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestImportAndTerminal:
    def test_import_dxf(self):
        from types import SimpleNamespace

        from PySide6.QtWidgets import QFileDialog
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        import ogr_core.dxf as dxf
        import ogr_gui.dialogs.dxf_import_dialog as did

        class _Dlg:
            result = 1

            def __init__(self, path, parent=None):
                self.result_preview = SimpleNamespace(
                    ok=True, report=None, regions=0, external_area=0.0,
                    area_matches=True, error="")
                self.options = None

            def exec(self):
                return self.result

        class _No(_Dlg):
            result = 0

        def apply(project, pv, options):
            project.add_boundary(Boundary(
                btype=BoundaryType.MATERIAL,
                polyline=Polyline(vertices=[Vertex(0.0, 5.0),
                                            Vertex(50.0, 5.0)],
                                  closed=False)))
            return {"material": 1}

        w = _window()
        try:
            with _swap(QFileDialog, "getOpenFileName",
                       staticmethod(lambda *a, **k: ("model.dxf", ""))), \
                    _swap(dxf, "apply_to_project", apply):
                with _swap(did, "DxfImportDialog", _No):
                    _cancelled(w, w.act_import_dxf)
                with _swap(did, "DxfImportDialog", _Dlg):
                    _accepted(w, "Import DXF", w.act_import_dxf)
        finally:
            _done(w)

    def test_a_terminal_command_is_one_step(self):
        w = _window()
        try:
            term = w.terminal_dock.terminal
            term._execute("x = len(project.materials)")
            assert w.command_stack.history() == ([], [])
            _accepted(w, "Python script", lambda: term._execute(
                "project.materials[0].unit_weight = 21.5"))
            _clean(w)
            # a step of the window called from the terminal is part of it
            s = w.project.settings.search
            s.grid_x_min, s.grid_x_max = 5.0, 20.0
            _clean(w)
            _accepted(w, "Python script", lambda: term._execute(
                "mainwindow.act_auto_grid()"))
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestWithAnAgent:
    def test_settings_dialog_and_agent_steps_undo_in_order(self):
        from ogr_api import call
        from ogr_gui.agent_bridge import AgentBridge
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)

        def ok_77(self):
            self.settings.methods.num_slices = 77
            return 1

        w = _window()
        br = AgentBridge(w)
        try:
            _a_line_annotation(w)
            _clean(w)
            s0 = _json(w.project)
            w._set_annotations_visible(False)
            s1 = _json(w.project)
            call(br.ws, "load_set", kind="distributed", start=[2, 25],
                 end=[10, 25], magnitude=20.0, orientation="vertical")
            s2 = _json(w.project)
            with _swap(ProjectSettingsDialog, "exec", ok_77):
                w.act_project_settings()
            s3 = _json(w.project)
            assert w.command_stack.history()[0] == [
                "Set annotation", "Set load", "Change settings"]
            for expected in (s2, s1, s0):
                w.act_undo()
                assert _json(w.project) == expected
            for expected in (s1, s2, s3):
                w.act_redo()
                assert _json(w.project) == expected
        finally:
            br.ws.shutdown()
            _done(w)
