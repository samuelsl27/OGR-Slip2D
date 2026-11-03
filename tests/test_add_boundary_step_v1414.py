# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.414 (D349) — the undo step of an added boundary says what was added.

The finding (the fifth interface test, 0.1.355, H14): after adding a Block
Search point, Edit offered «Deshacer «Añadir contorno»». Every command that
adds a boundary was called the same — ``AddBoundaryCommand.description`` was
the constant "Add Boundary" — whatever the boundary: a material boundary, a
weak layer, a Block Search object. The agent's ``boundary_add`` and Convert
Tool to Boundary already named the type (``f"Add {display_name}"``), so the
same object had two names in ``project_history`` depending on who drew it.
The name is now the command's own, built in ``ogr_core`` from the type
(``add_boundary_step_name``), and every caller gets it.

What these tests protect:

* drawn on the real canvas — shown, snapping off, real mouse events — each
  drawing mode leaves the step named by its type, in English in the stack
  (what ``project_history`` reads) and in Spanish in the Edit menu;
* the four Block Search modes all say «Añadir objeto de búsqueda por
  bloques»;
* copying a boundary names the copy's type;
* undo and redo give back exactly the project (D307–D309);
* the window, the API and Convert Tool to Boundary ask the same function.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QKeyEvent, QMouseEvent, QTransform
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS: list = []


@contextlib.contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


def _window(project):
    """The window on ``project``, its canvas shown at a known zoom with
    snapping off (memory of 0.1.311: a canvas not shown is 98 × 28 px and
    every click snaps to one vertex)."""
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    w = MainWindow()
    w.PROMPT_ASSIGN_ON_DRAW = False
    w._attach_project(project)
    _WINDOWS.append(w)
    c = w.canvas
    c.resize(900, 700)
    c.show()
    QApplication.processEvents()
    c.snap_settings.snap = False
    c.snap_settings.ortho = False
    c.snap_settings.osnap = False
    c.setTransform(QTransform().scale(20.0, -20.0))
    c.centerOn(25.0, 12.5)
    return w, c


def _done(w):
    w.project.is_dirty = False
    w.close()


def _click(c, x, y):
    p = c.mapFromScene(QPointF(x, y))
    c.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, QPointF(p.x(), p.y()),
        c.mapToGlobal(QPoint(p.x(), p.y())), Qt.LeftButton, Qt.LeftButton,
        Qt.NoModifier))


def _enter(c):
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))


def _state(project):
    return json.dumps(project.to_dict(), sort_keys=True, default=str)


def _draw(w, c, mode, points):
    """Draw with the mouse in ``mode``; Enter when the mode does not end by
    itself. Returns the project before."""
    before = _state(w.project)
    c.set_tool_mode(mode)
    for x, y in points:
        _click(c, x, y)
    if c.tool_mode == mode:          # not finished by its own count
        _enter(c)
    QApplication.processEvents()
    # A Block Search Polyline opens its (non-modal) options: close them
    for d in QApplication.topLevelWidgets():
        if d is not w and d.isVisible() and d.isWindow() \
                and d.windowTitle() and "Block" in d.windowTitle():
            d.close()
    return before


#: The open polylines drawn on the demo, away from its vertices.
_OPEN = [(5.0, 10.0), (20.0, 11.0), (40.0, 12.0)]


def _modes():
    from ogr_core.geometry import BoundaryType
    from ogr_gui.canvas.tool_mode import ToolMode as T
    B = BoundaryType
    return [
        (T.DRAW_MATERIAL, B.MATERIAL, _OPEN),
        (T.DRAW_WATER_TABLE, B.WATER_TABLE, _OPEN),
        (T.DRAW_DRAWDOWN, B.DRAWDOWN, _OPEN),
        (T.DRAW_PIEZOMETRIC, B.PIEZOMETRIC, _OPEN),
        (T.DRAW_TENSION_CRACK, B.TENSION_CRACK, [(30.0, 21.0), (30.0, 17.0)]),
        (T.DRAW_WEAK_LAYER, B.WEAK_LAYER, _OPEN),
        (T.DRAW_ANISOTROPIC_SURFACE, B.ANISOTROPIC_SURFACE, _OPEN),
        (T.DRAW_BLOCK_SEARCH, B.BLOCK_SEARCH_OBJECT,
         [(10.0, 5.0), (20.0, 5.0), (20.0, 10.0), (10.0, 10.0)]),
        (T.DRAW_BLOCK_LINE, B.BLOCK_SEARCH_OBJECT, [(10.0, 6.0), (20.0, 7.0)]),
        (T.DRAW_BLOCK_POINT, B.BLOCK_SEARCH_OBJECT, [(15.0, 6.0)]),
        (T.DRAW_BLOCK_POLYLINE, B.BLOCK_SEARCH_OBJECT,
         [(8.0, 6.0), (18.0, 4.0), (28.0, 7.0)]),
    ]


# ======================================================================
@_requires_qt
class TestEachDrawnTypeNamesItsStep:

    def test_every_drawing_mode_on_the_demo(self):
        from ogr_core.project.demo import build_demo_project
        w, c = _window(build_demo_project())
        try:
            for mode, btype, pts in _modes():
                w.command_stack.clear()
                n = len(w.project.boundaries)
                before = _state(w.project)
                _draw(w, c, mode, pts)
                assert len(w.project.boundaries) == n + 1, mode
                added = w.project.boundaries[-1]
                assert added.btype == btype, (mode, added.btype)
                undo, redo = w.command_stack.history()
                want = "Add " + btype.display_name
                assert undo == [want] and redo == [], (mode, undo)
                after = _state(w.project)
                w.act_undo()
                assert _state(w.project) == before, mode
                w.act_redo()
                assert _state(w.project) == after, mode
        finally:
            _done(w)

    def test_the_external_boundary_on_an_empty_model(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _window(Project("empty"))
        try:
            w.command_stack.clear()
            _draw(w, c, ToolMode.DRAW_EXTERNAL,
                  [(0.0, 0.0), (40.0, 0.0), (40.0, 20.0), (0.0, 20.0)])
            assert [b.btype for b in w.project.boundaries] == [
                BoundaryType.EXTERNAL]
            assert w.command_stack.history() == (
                ["Add External Boundary"], [])
        finally:
            _done(w)

    def test_the_edit_menu_says_it_in_spanish(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _window(build_demo_project())
        try:
            said = {}
            for mode, pts in ((ToolMode.DRAW_BLOCK_POINT, [(15.0, 6.0)]),
                              (ToolMode.DRAW_WEAK_LAYER, _OPEN),
                              (ToolMode.DRAW_MATERIAL, _OPEN)):
                w.command_stack.clear()
                _draw(w, c, mode, pts)
                with _spanish():
                    w._refresh_undo_actions()
                    said[mode] = w._actions["undo"].text()
            w._refresh_undo_actions()
            assert said == {
                ToolMode.DRAW_BLOCK_POINT:
                    "Deshacer «Añadir objeto de búsqueda por bloques»",
                ToolMode.DRAW_WEAK_LAYER: "Deshacer «Añadir capa débil»",
                ToolMode.DRAW_MATERIAL:
                    "Deshacer «Añadir contorno de material»",
            }, said
        finally:
            _done(w)


@_requires_qt
class TestTheOtherWaysOfAdding:

    def test_a_copy_names_its_type(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.project.demo import build_demo_project
        w, _c = _window(build_demo_project())
        try:
            idx = next(i for i, b in enumerate(w.project.boundaries)
                       if b.btype == BoundaryType.WATER_TABLE)
            w.command_stack.clear()
            w._do_copy_boundary(idx)
            assert w.command_stack.history() == (["Add Water Table"], [])
        finally:
            _done(w)

    def test_the_rule_lives_in_the_core_and_everyone_asks_it(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.project.commands import (AddBoundaryCommand,
                                               add_boundary_step_name)
        for btype in BoundaryType:
            b = Boundary(polyline=Polyline(vertices=[Vertex(0, 0),
                                                     Vertex(1, 1)]),
                         btype=btype)
            assert AddBoundaryCommand(boundary=b).description == \
                add_boundary_step_name(btype) == "Add " + btype.display_name
        # an explicit name is still the caller's
        assert AddBoundaryCommand(boundary=b, description="X").description \
            == "X"
        root = Path(__file__).resolve().parents[1]
        for rel in ("ogr_api/ops/model.py", "ogr_gui/main_window.py"):
            src = (root / rel).read_text(encoding="utf-8")
            assert 'f"Add {btype.display_name}"' not in src, rel
            assert "add_boundary_step_name" in src, rel

    def test_the_api_names_it_the_same(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="t")["project_id"]
        call(ws, "boundary_add", project_id=pid, type="external",
             points=[[0, 0], [40, 0], [40, 20], [0, 20]])
        call(ws, "boundary_add", project_id=pid, type="water_table",
             points=[[0, 10], [40, 10]])
        undo = call(ws, "project_history", project_id=pid)["undo"]
        assert undo[-2:] == ["Add External Boundary",
                             "Add Water Table"], undo
