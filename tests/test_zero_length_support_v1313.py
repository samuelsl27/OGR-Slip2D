# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.313 (D313) — a support with no length is refused at every door, and the
analysis names it.

Only ``support_set`` refused a support whose head and tail coincide, with an
exact comparison, since spec 008. The window placed one with two clicks on
the same point (Add Support), by stretching one end onto the other (Stretch
Support) or by typing the same coordinates (the support properties dialog),
and the core had no rule to ask. The analysis then gave it no force, which
is right, and said it "does not cross the surface", which sends the user to
fix the wrong thing. Measured with ``_auditoria/P8_interfaz/repro_d313.py``:
FS 1.091433 on the demo, the same as without the support.

The invariants:

* the rule lives in ``ogr_core.project.rules`` and is RELATIVE to the size
  of the model: the same model in millimetres and in metres gets the same
  verdict (AGENTS: geometric tolerances follow the model);
* the three doors of the window refuse it, through the real canvas (shown,
  without snapping): nothing is written, no undo step is left, the status
  bar or the dialog says why in Spanish; Add Support keeps its tool (D308)
  and a proper support still goes in (control);
* ``support_set`` still refuses, with the same words;
* ``project_validate`` names one that comes in a file or a script;
* the analysis reports it with its own reason, ``no_length``, and the factor
  of safety is the one without the support, digit for digit (the identity
  of D62); the note does not carry the pair the bank reserves for D40.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from test_support_silence_v1155 import (  # noqa: E402
    _instance, _model, _nail_type, _notes, _reasons, _result,
)

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


@contextlib.contextmanager
def _no_modals():
    """A modal dialog or message box fails the test instead of waiting for
    ever without a screen."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


@contextlib.contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


def _ready():
    from ogr_core.support import EndAnchored
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.support_types = [
        EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)]
    c = w.canvas
    # shown and without snapping: hidden, the canvas is 98 x 28 px and
    # every click lands on a vertex (see test_segment_picked_owner_v1311)
    c.resize(900, 600)
    c.show()
    c.snap_settings.snap = False
    c.zoom_all()
    w.command_stack.clear()
    w.project.is_dirty = False
    return w, c


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _click(c, x, y):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    vp = QPointF(c.mapFromScene(QPointF(x, y)))
    g = c.viewport().mapToGlobal(vp.toPoint())
    c.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, vp, g,
                                  Qt.LeftButton, Qt.LeftButton,
                                  Qt.NoModifier))
    c.mouseReleaseEvent(QMouseEvent(QEvent.MouseButtonRelease, vp, g,
                                    Qt.LeftButton, Qt.NoButton,
                                    Qt.NoModifier))


def _said(w):
    from ogr_core.project.rules import SUPPORT_NO_LENGTH
    from ogr_gui.i18n import tr
    msg = w.ogr_status.currentMessage()
    return msg == tr(SUPPORT_NO_LENGTH) and "coinciden" in msg


# ----------------------------------------------------------------------
class TestTheRule:
    def test_it_is_relative_to_the_size_of_the_model(self):
        """The same model in metres and in millimetres: a support a
        micrometre long has length, one a hundred-thousandth of that does
        not, at both scales."""
        from ogr_core.geometry import Vertex
        from ogr_core.geometry import scale as g_scale
        from ogr_core.project.rules import support_has_no_length
        from test_supports_all_methods_v164 import _nail, _project
        for k in (1.0, 1000.0):
            p = _project(_nail())
            p.boundaries[:] = [g_scale(b, Vertex(0.0, 0.0), k, k)
                               for b in p.boundaries]
            head = (40.0 * k, 8.0 * k)
            for length, none in ((1e-6, False), (1e-11, True), (0.0, True)):
                tail = (head[0] + length * k, head[1])
                assert support_has_no_length(p, head, tail) is none, (
                    k, length)

    def test_it_reads_vertices_and_pairs_alike(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project import Project
        from ogr_core.project.rules import support_has_no_length
        p = Project("empty")
        assert support_has_no_length(p, Vertex(1.0, 2.0), (1.0, 2.0))
        assert not support_has_no_length(p, Vertex(1.0, 2.0), (3.0, 2.0))


# ----------------------------------------------------------------------
class TestTheWindowRefusesIt:
    def test_add_support_with_two_clicks_on_one_point(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            before = _json(w.project)
            with _no_modals(), _spanish():
                w.act_add_support()
                _click(c, 30.0, 20.0)
                _click(c, 30.0, 20.0)
                assert _json(w.project) == before
                assert w.command_stack.history() == ([], [])
                assert _said(w)
            assert c.tool_mode is ToolMode.ADD_SUPPORT
            # control: two different points still place one
            _click(c, 30.0, 20.0)
            _click(c, 36.0, 17.0)
            assert len(w.project.supports) == 1
            assert w.command_stack.history() == (["Set support"], [])
        finally:
            _done(w)

    def test_stretch_support_onto_its_other_end(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            with _no_modals():
                w.act_add_support()
                _click(c, 30.0, 20.0)
                _click(c, 36.0, 17.0)
            s = w.project.supports[0]
            head = (s.head.x, s.head.y)
            w.command_stack.clear()
            before = _json(w.project)
            with _no_modals(), _spanish():
                w.act_stretch_support_mode()
                _click(c, s.tail.x, s.tail.y)
                _click(c, *head)
                assert _json(w.project) == before
                assert w.command_stack.history() == ([], [])
                assert _said(w)
            assert c.tool_mode is ToolMode.SELECT
            # control: stretched somewhere else, it moves
            with _no_modals():
                w.act_stretch_support_mode()
                _click(c, s.tail.x, s.tail.y)
                _click(c, 38.0, 16.0)
            assert _json(w.project) != before
            assert w.command_stack.history() == (["Stretch support"], [])
        finally:
            _done(w)

    def test_the_properties_dialog_with_the_same_coordinates(self):
        from PySide6.QtWidgets import QDialog
        from ogr_gui.dialogs.support_properties_dialog import (
            SupportInstancePropertiesDialog)
        from ogr_gui.i18n import tr
        w, c = _ready()
        try:
            with _no_modals():
                w.act_add_support()
                _click(c, 30.0, 20.0)
                _click(c, 36.0, 17.0)
            s = w.project.supports[0]
            before = _json(w.project)
            with _no_modals(), _spanish():
                d = SupportInstancePropertiesDialog(s, w.project, w)
                d.spn_tail_x.setValue(d.spn_head_x.value())
                d.spn_tail_y.setValue(d.spn_head_y.value())
                d.ed_name.setText("renamed")
                d.accept()
                assert d.result() != QDialog.DialogCode.Accepted
                # nothing written, not even the name typed before OK
                assert _json(w.project) == before
                from ogr_core.project.rules import SUPPORT_NO_LENGTH
                assert not d.lbl_problem.isHidden()
                assert d.lbl_problem.text() == tr(SUPPORT_NO_LENGTH)
                assert "coinciden" in d.lbl_problem.text()
            with _no_modals():
                d.spn_tail_x.setValue(d.spn_head_x.value() + 4.0)
                d.accept()
            assert d.result() == QDialog.DialogCode.Accepted
            assert s.name == "renamed" and s.length() > 1.0
            d.deleteLater()
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestTheApiAndValidate:
    def test_support_set_still_refuses_with_the_same_words(self):
        import atexit
        from ogr_api import Workspace, call
        from ogr_core.support.support import support_registry
        ws = Workspace()
        atexit.register(ws.shutdown)
        soil = {"model": "mohr_coulomb",
                "params": {"cohesion": 5.0, "friction_angle": 30.0}}
        pid = call(ws, "project_new", name="d313")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
            "materials": [{"name": "A", "unit_weight": 20,
                           "strength": soil}]})
        cls = next(k for k in support_registry() if "end" in k.lower())
        call(ws, "support_type_set", project_id=pid, type_class=cls,
             name="T")
        for kw in ({"head": [5.0, 10.0], "tail": [5.0, 10.0]},):
            try:
                call(ws, "support_set", project_id=pid, support_type="T",
                     **kw)
            except Exception as e:  # noqa: BLE001
                assert type(e).__name__ == "InvalidArgument"
                assert "head and tail coincide." in str(e)
            else:  # pragma: no cover
                raise AssertionError("a support with no length went in")
        sid = call(ws, "support_set", project_id=pid, support_type="T",
                   head=[5.0, 10.0], tail=[9.0, 7.0])["support"]["id"]
        try:
            call(ws, "support_set", project_id=pid, support=sid,
                 tail=[5.0, 10.0])
        except Exception as e:  # noqa: BLE001
            assert "head and tail coincide." in str(e)
        else:  # pragma: no cover
            raise AssertionError("an edit to no length went in")

    def test_project_validate_names_one_from_a_file(self):
        from ogr_api.ops.project import status_of
        zero = _model([_nail_type()],
                      [_instance("soil_nail", ((43.5, 8.0), (43.5, 8.0)),
                                 name="Nail 1")])
        notes = status_of(zero)["model_notes"]
        assert any("Nail 1" in n and "no length" in n for n in notes), notes
        fine = _model([_nail_type()],
                      [_instance("soil_nail", ((43.5, 8.0), (54.0, 8.0)))])
        assert not any("no length" in n
                       for n in status_of(fine)["model_notes"])


# ----------------------------------------------------------------------
class TestTheAnalysisNamesIt:
    _POINT = ((43.5, 8.0), (43.5, 8.0))

    def test_its_own_reason_and_no_other(self):
        from ogr_slip2d.support_integration import (SUPPORT_NO_CROSSING,
                                                    SUPPORT_NO_LENGTH)
        p = _model([_nail_type()], [_instance("soil_nail", self._POINT)])
        assert _reasons(p) == [(p.supports[0].id, SUPPORT_NO_LENGTH)]
        # control: a real support that misses the surface keeps its reason
        q = _model([_nail_type()],
                   [_instance("soil_nail", ((2.0, 1.0), (12.0, 1.0)))])
        assert _reasons(q) == [(q.supports[0].id, SUPPORT_NO_CROSSING)]

    def test_the_factor_is_the_one_without_the_support(self):
        p = _model([_nail_type()], [_instance("soil_nail", self._POINT)])
        bare = _model([_nail_type()], [])
        assert _result(p).fos == _result(bare).fos

    def test_the_note_says_it_and_keeps_clear_of_the_d40_pair(self):
        p = _model([_nail_type()], [_instance("soil_nail", self._POINT)])
        notes = _notes(p, _result(p))
        assert len(notes) == 1, notes
        assert "no length" in notes[0] and "coincide" in notes[0]
        assert "does not cross" not in notes[0]
        assert not ("stable" in notes[0] and "head" in notes[0])
