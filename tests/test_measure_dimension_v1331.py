# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.331 (D329a) — Measure measures, in both windows, and Dimension Length
leaves a dimension in Interpret without touching the model.

The defects:

* in Interpret, *Tools → Measure* and *Tools → Dimension Length* were
  QActions with nothing connected (rule 7; D329, found planning P8i);
* in the main window, *Measure* asked for typed coordinates and stored a
  dimension in the model, exactly as *Dimension Length* does: two entries
  for one thing, and a measurement that edited the project (found planning
  this version, D332);
* ``ToolMode.MEASURE`` existed with its cursor and its hint («Measure: click
  two points, Esc to finish»), and the canvas never read it.

By decision of the owner, Measure is two clicks on the canvas in both
windows, with the distance and its two components on the status bar and
nothing written; Dimension Length keeps storing its dimension in the main
window, and in Interpret it leaves one on the canvas, drawn as the model's
are (D332), which goes with the window.

The clicks are real mouse clicks on a shown canvas with snapping off (a
canvas never shown has a 98 × 28 px viewport, and snapping moves a click
onto a vertex), and the expected distance is computed from the scene
points those pixels map to.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtWidgets import (QApplication, QGraphicsSimpleTextItem,  # noqa: E402
                               QInputDialog)

_WINDOWS: list = []


def _no_snap(canvas):
    s = canvas.snap_settings
    s.snap = s.ortho = s.osnap = False


def _click(canvas, pos):
    from PySide6.QtTest import QTest
    QTest.mouseClick(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, pos)
    QApplication.processEvents()


def _expected(canvas, a, b):
    from ogr_gui.labels import measurement_text
    pa, pb = canvas.mapToScene(a), canvas.mapToScene(b)
    return measurement_text(pa.x(), pa.y(), pb.x(), pb.y()), math.dist(
        (pa.x(), pa.y()), (pb.x(), pb.y()))


class _NoTypedPoints:
    """Before this version Measure opened a modal box for typed points; a
    test on that tree must fail, not hang."""

    def __enter__(self):
        self.raw = QInputDialog.__dict__.get("getText")
        QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
        return self

    def __exit__(self, *exc):
        if self.raw is None:
            del QInputDialog.getText
        else:
            QInputDialog.getText = self.raw
        return False


# ----------------------------------------------------------------------
class TestMeasureInTheMainWindow:
    def test_two_clicks_give_the_distance_and_write_nothing(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        w = MainWindow()
        _WINDOWS.append(w)
        w.act_load_demo()
        w.resize(1200, 800)
        w.show()
        QApplication.processEvents()
        w.canvas.zoom_all()
        _no_snap(w.canvas)
        try:
            n_annotations = len(w.project.annotations)
            undo_before = w.command_stack.history()
            with _NoTypedPoints():
                w._actions["measure"].trigger()
            assert w.canvas.tool_mode is ToolMode.MEASURE
            a, b = QPoint(300, 300), QPoint(700, 420)
            text, distance = _expected(w.canvas, a, b)
            _click(w.canvas, a)
            _click(w.canvas, b)
            assert w.ogr_status.currentMessage() == text, (
                w.ogr_status.currentMessage(), text)
            assert distance > 1.0
            # nothing of it in the model
            assert len(w.project.annotations) == n_annotations
            assert w.command_stack.history() == undo_before
            assert w.project.is_dirty is False
            # the mode stays for the next pair, until Esc
            assert w.canvas.tool_mode is ToolMode.MEASURE
        finally:
            w.project.is_dirty = False
            w.close()


# ----------------------------------------------------------------------
def _interpret():
    import test_interpret_reasons_status_v1328 as interp
    w = interp._interpret()
    w.resize(1200, 800)
    w.show()
    QApplication.processEvents()
    w.canvas.zoom_all()
    _no_snap(w.canvas)
    return w


def _tools(w, name):
    for top in w.menuBar().actions():
        if top.text() == "Tools":
            for act in top.menu().actions():
                if act.text() == name:
                    return act
    raise AssertionError(name)


class TestInterpretMeasuresAndDimensions:
    def test_measure(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _interpret()
        try:
            _tools(w, "Measure").trigger()
            assert w.canvas.tool_mode is ToolMode.MEASURE
            a, b = QPoint(300, 300), QPoint(650, 380)
            text, _d = _expected(w.canvas, a, b)
            _click(w.canvas, a)
            _click(w.canvas, b)
            assert w.statusBar().currentMessage() == text
            assert w.canvas.overlay_annotations == []
        finally:
            w.close()

    def test_dimension_length_stays_on_the_window_only(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _interpret()
        try:
            n_annotations = len(w.project.annotations)
            dirty = w.project.is_dirty
            _tools(w, "Dimension Length").trigger()
            assert w.canvas.tool_mode is ToolMode.PICK_DIMENSION
            a, b = QPoint(300, 300), QPoint(650, 380)
            text, distance = _expected(w.canvas, a, b)
            _click(w.canvas, a)
            _click(w.canvas, b)
            assert w.statusBar().currentMessage().startswith(text)
            # on the canvas, drawn with its value
            assert len(w.canvas.overlay_annotations) == 1
            label = "%.3f" % distance
            drawn = [i.text() for i in w.canvas.scene().items()
                     if isinstance(i, QGraphicsSimpleTextItem)]
            assert label in drawn, (label, drawn)
            # and not in the model
            assert len(w.project.annotations) == n_annotations
            assert w.project.is_dirty == dirty
            # a redraw of the model keeps it
            w.canvas.refresh_scene()
            drawn = [i.text() for i in w.canvas.scene().items()
                     if isinstance(i, QGraphicsSimpleTextItem)]
            assert label in drawn
        finally:
            w.close()

    def test_esc_gives_the_clicks_back_to_the_surfaces(self):
        from PySide6.QtTest import QTest
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _interpret()
        try:
            _tools(w, "Measure").trigger()
            assert w.canvas.tool_mode is ToolMode.MEASURE
            QTest.keyClick(w.canvas, Qt.Key_Escape)
            QApplication.processEvents()
            assert w.canvas.tool_mode is ToolMode.SELECT
        finally:
            w.close()
