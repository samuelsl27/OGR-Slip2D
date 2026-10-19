# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.327 (D322, D323, D330) — the canvas: what takes the pointer, what is
drawn again after a redraw, and a result of the agent marked stale.

The defects, seen in the third test of the interface or found planning it:

* **D322.** Inside the slope, the tooltip was always the external
  boundary's, never the region's, and a click inside selected the external
  boundary. ``BoundaryItem`` is a ``QGraphicsPathItem`` with a closed path,
  whose shape is its whole interior, brush or none; it sits above the
  regions. Its shape is now its line, widened by ``PICK_PX`` screen pixels
  converted to model units at each zoom (the project's rule for screen
  tolerances).
* **D323.** After computing, moving the toe and undoing, the results panel
  showed the result as current again but the canvas drew no surfaces: every
  project event redraws the scene, results included. Display Options and
  the annotations, which leave the result current, cleared it too. The
  canvas now draws its last result again while the window says it is still
  of this model (the fingerprint of D304). And the snap marker stayed where
  a vertex was dropped, even after File > New.
* **D330.** ``agent_bridge.show_analysis`` did not remember the model of
  the result it showed, so an edit after an agent's analysis never marked
  it stale.
* **D331**, found measuring D322. The data tip (``data_tips.tip_at``, on
  at its maximum by default) is the view's own tooltip, and Qt shows the
  tooltip of the item under the pointer first: regions, loads and supports
  cover the model, so switching it on or off changed nothing on screen
  (rule 7). By decision of the owner the data tip wins; off, the items
  speak as before, and on a boundary's line the boundary keeps its own.

The window's real compute path drives the results (``_ComputeWorker.run`` +
``_on_compute_done``), on the small slope of ``test_results_stale_v1297``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def _shown_window(computed=True):
    """The slope in a shown window, its canvas zoomed to it: a canvas that
    is never shown keeps a 98 × 28 px viewport and an unusable scale."""
    import test_results_stale_v1297 as stale
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w._attach_project(stale._slope())
    w.resize(1200, 800)
    w.show()
    QApplication.processEvents()
    w.canvas.zoom_all()
    QApplication.processEvents()
    if computed:
        stale._compute(w)
    return w


def _move_toe(w):
    """The toe moved as in test_results_stale_v1297, and announced as a real
    edit announces it: that edit mutates the vertices in place, and it is
    the project's notice that redraws the canvas."""
    import test_results_stale_v1297 as stale
    stale._move_toe(w)
    w.project._notify("boundary_modified")


def _done(w):
    w.project.is_dirty = False
    w.close()


def _boundaries_at(canvas, x, y):
    from ogr_gui.canvas.graphics_items import BoundaryItem
    return [i for i in canvas.scene().items(QPointF(x, y))
            if isinstance(i, BoundaryItem)]


def _tooltip_at(canvas, x, y):
    """The tooltip Qt shows over (x, y): the topmost item that has one."""
    for item in canvas.scene().items(QPointF(x, y)):
        if item.toolTip():
            return item.toolTip()
    return ""


# ----------------------------------------------------------------------
class TestTheBoundaryTakesItsLineOnly:
    """The slope runs (0, 0) – (50, 0) – (50, 15) – (35, 15) – (25, 25) –
    (0, 25); its bottom edge is y = 0."""

    def test_inside_the_slope_the_tooltip_is_the_regions(self):
        w = _shown_window(computed=False)
        try:
            assert _boundaries_at(w.canvas, 10.0, 10.0) == []
            assert "Region" in _tooltip_at(w.canvas, 10.0, 10.0), \
                _tooltip_at(w.canvas, 10.0, 10.0)
        finally:
            _done(w)

    def test_on_its_line_it_is_the_boundarys(self):
        w = _shown_window(computed=False)
        try:
            assert _boundaries_at(w.canvas, 25.0, 0.0)
            assert "External" in _tooltip_at(w.canvas, 25.0, 0.0)
        finally:
            _done(w)

    def test_the_tolerance_is_in_pixels_at_every_zoom(self):
        from ogr_gui.canvas.graphics_items import BoundaryItem
        w = _shown_window(computed=False)
        try:
            for factor in (1.0, 4.0, 0.25):
                w.canvas.zoom_by(factor)
                QApplication.processEvents()
                ppu = w.canvas._pixels_per_unit()
                near = 0.5 * BoundaryItem.PICK_PX / ppu
                far = 3.0 * BoundaryItem.PICK_PX / ppu
                assert _boundaries_at(w.canvas, 25.0, near), (factor, ppu)
                assert not _boundaries_at(w.canvas, 25.0, far), (factor, ppu)
        finally:
            _done(w)

    def test_a_click_inside_selects_no_boundary(self):
        from PySide6.QtTest import QTest
        from ogr_gui.canvas.graphics_items import BoundaryItem
        w = _shown_window(computed=False)
        try:
            pos = w.canvas.mapFromScene(QPointF(10.0, 10.0))
            QTest.mouseClick(w.canvas.viewport(), Qt.LeftButton,
                             Qt.NoModifier, pos)
            QApplication.processEvents()
            chosen = [i for i in w.canvas.scene().selectedItems()
                      if isinstance(i, BoundaryItem)]
            assert chosen == []
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestTheResultIsDrawnAgainWhileCurrent:
    def test_undo_gives_the_surfaces_back(self):
        w = _shown_window()
        try:
            assert w.canvas._result_items
            _move_toe(w)
            # control: a result of an earlier model is not drawn
            assert w.canvas._result_items == []
            w.command_stack.undo(w.project)
            assert w.canvas._result_items
        finally:
            _done(w)

    def test_display_options_and_annotations_keep_them(self):
        from ogr_core.annotations import Annotation, AnnotationKind
        w = _shown_window()
        try:
            w.canvas.set_display_options(w.canvas.display_options)
            assert w.canvas._result_items
            w.project.annotations.add(Annotation(
                kind=AnnotationKind.LINE, points=[(1.0, 1.0), (5.0, 2.0)]))
            w.project._notify("annotation_added")
            assert w.canvas._result_items
        finally:
            _done(w)

    def test_a_new_project_draws_none_of_the_old(self):
        from ogr_core.project import Project
        w = _shown_window()
        try:
            w._attach_project(Project("empty"))
            w.canvas.refresh_scene()
            assert w.canvas._result_items == []
            assert w.canvas._shown_result is None
        finally:
            _done(w)


class TestTheSnapMarkerGoesWithItsMode:
    def test_leaving_the_mode_clears_it(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _shown_window(computed=False)
        try:
            w.canvas.set_tool_mode(ToolMode.MOVE_VERTEX)
            w.canvas._snap_point(QPointF(35.0, 15.0))
            assert w.canvas._last_snap is not None
            w.canvas.set_tool_mode(ToolMode.SELECT)
            assert w.canvas._last_snap is None
        finally:
            _done(w)

    def test_a_new_project_clears_it(self):
        from ogr_core.project import Project
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _shown_window(computed=False)
        try:
            w.canvas.set_tool_mode(ToolMode.MOVE_VERTEX)
            w.canvas._snap_point(QPointF(35.0, 15.0))
            # the mode is kept: only the project changes
            w.canvas.set_project(Project("empty"))
            assert w.canvas._last_snap is None
        finally:
            w.canvas.set_tool_mode(ToolMode.SELECT)
            _done(w)


# ----------------------------------------------------------------------
class TestAnAgentsResultIsMarkedStale:
    def _agent_window(self):
        from ogr_gui.agent_bridge import WindowHost
        from ogr_gui.main_window import _ComputeWorker
        w = _shown_window(computed=False)
        errors = []
        worker = _ComputeWorker(w.project, ["bishop_simplified"])
        worker.failed.connect(errors.append)
        worker.run()
        assert not errors, errors
        WindowHost(w).show_analysis(worker.results)
        return w

    def test_an_edit_after_it_marks_it(self):
        w = self._agent_window()
        try:
            w._check_results_stale()
            # control: just shown, it is current
            assert w.results_dock.is_stale() is False
            _move_toe(w)
            w._check_results_stale()
            assert w.results_dock.is_stale() is True
            w.command_stack.undo(w.project)
            w._check_results_stale()
            assert w.results_dock.is_stale() is False
            assert w.canvas._result_items
        finally:
            _done(w)


# ----------------------------------------------------------------------
class TestTheDataTipIsSeen:
    """D331 — the setting moves what is shown (rule 7)."""

    def _decided(self, w, x, y, mode):
        w.data_tip_mode = mode
        w._on_canvas_hover(x, y)
        return w.canvas._data_tip_for(w.canvas.mapFromScene(QPointF(x, y)))

    def test_on_it_shows_inside_the_slope_and_off_the_region_speaks(self):
        from ogr_gui.data_tips import DataTipMode
        w = _shown_window(computed=False)
        try:
            on = self._decided(w, 10.0, 10.0, DataTipMode.MAXIMUM)
            assert "Silty clay" in on and "Mohr" in on, on
            off = self._decided(w, 10.0, 10.0, DataTipMode.NONE)
            assert off == ""
            assert "Region" in _tooltip_at(w.canvas, 10.0, 10.0)
        finally:
            _done(w)

    def test_the_minimum_is_the_name_alone(self):
        from ogr_gui.data_tips import DataTipMode
        w = _shown_window(computed=False)
        try:
            name = self._decided(w, 10.0, 10.0, DataTipMode.MINIMUM)
            assert name == "Silty clay", name
        finally:
            _done(w)

    def test_on_a_boundary_line_the_boundary_keeps_its_own(self):
        from ogr_gui.data_tips import DataTipMode
        w = _shown_window(computed=False)
        try:
            assert self._decided(w, 25.0, 0.0, DataTipMode.MAXIMUM) == ""
            assert "External" in _tooltip_at(w.canvas, 25.0, 0.0)
        finally:
            _done(w)

    def test_it_reaches_the_screen(self):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QHelpEvent
        from PySide6.QtWidgets import QToolTip
        from ogr_gui.data_tips import DataTipMode
        w = _shown_window(computed=False)
        try:
            self._decided(w, 10.0, 10.0, DataTipMode.MAXIMUM)
            vp = w.canvas.mapFromScene(QPointF(10.0, 10.0))
            event = QHelpEvent(QEvent.ToolTip, vp,
                               w.canvas.viewport().mapToGlobal(vp))
            assert w.canvas.viewportEvent(event) is True
            assert QToolTip.text() == w.canvas.toolTip()
        finally:
            from PySide6.QtWidgets import QToolTip
            QToolTip.hideText()
            _done(w)
