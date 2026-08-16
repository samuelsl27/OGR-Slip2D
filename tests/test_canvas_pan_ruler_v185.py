# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Navigation invariants: the canvas can always be scrolled, and the ruler
belongs to the window rather than to the drawing.

WHAT INVARIANT THIS PROTECTS.

Panning moves the scroll bars, and scroll bars cannot travel outside the
view's scene rect. Until v0.1.85 that rect was fixed — the model bounding
box plus half of itself, or a hard-coded (-5, -5, 60, 40) with nothing
open — so:

* with no file open BOTH scroll ranges were exactly zero and the drawing
  could not be moved at all, which is the first thing anyone does on a
  blank canvas;
* at the zoom level that fits the model, the level the program opens at,
  the ranges were exhausted and the drag stopped dead.

Zooming in produced range and hid the problem, which is why it read as
"it only lets me move when I am zoomed in".

The second invariant is the ruler. It is painted in VIEWPORT coordinates,
so it must be painted as an overlay, after the scene, over the whole
viewport. Painted from ``drawBackground`` (the scene layer) with
``MinimalViewportUpdate``, Qt scrolls the already-painted pixels and
repaints only the newly exposed strip: the labels travel with the drawing
and stale copies survive, which is the stacked, shifted columns of numbers
in the report.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def _view(with_model: bool = False, w: int = 900, h: int = 600):
    from PySide6.QtWidgets import QApplication
    from ogr_gui.canvas.canvas_view import CanvasView
    QApplication.instance() or QApplication([])
    v = CanvasView()
    if with_model:
        v.project = _model()
    v.resize(w, h)
    v.show()
    if with_model:
        v.refresh_scene()
    v.zoom_all()
    return v


def _model():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 70), Vertex(70, 70),
        Vertex(55, 55), Vertex(40, 55), Vertex(15, 30), Vertex(-50, 30),
        Vertex(-50, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("pan")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="M", unit_weight=20,
                            strength=MohrCoulomb(cohesion=20,
                                                 friction_angle=35))]
    return p


def _ranges(v):
    h, vb = v.horizontalScrollBar(), v.verticalScrollBar()
    return (h.maximum() - h.minimum(), vb.maximum() - vb.minimum())


def _centre(v):
    return v.mapToScene(v.viewport().rect()).boundingRect().center()


def _drag(v, dx, dy, steps=8):
    """A middle-button drag of (dx, dy) viewport pixels."""
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QPointF, QEvent
    start = QPointF(400, 300)
    v._start_pan(start)
    for i in range(1, steps + 1):
        pos = QPointF(start.x() + dx * i / steps, start.y() + dy * i / steps)
        v.mouseMoveEvent(QMouseEvent(
            QEvent.MouseMove, pos, v.mapToGlobal(pos),
            Qt.NoButton, Qt.MiddleButton, Qt.NoModifier))
    v._end_pan()


class TestTheCanvasCanAlwaysBeScrolled:
    def test_with_nothing_open(self):
        """Both ranges were exactly zero here."""
        v = _view(with_model=False)
        hr, vr = _ranges(v)
        assert hr > 0 and vr > 0, (hr, vr)

    def test_at_the_zoom_that_fits_the_model(self):
        """The zoom level the program opens a file at."""
        v = _view(with_model=True)
        hr, vr = _ranges(v)
        assert hr > 0 and vr > 0, (hr, vr)

    def test_a_drag_moves_the_view_with_nothing_open(self):
        v = _view(with_model=False)
        before = _centre(v)
        _drag(v, -250, -150)
        after = _centre(v)
        assert abs(after.x() - before.x()) > 1e-6
        assert abs(after.y() - before.y()) > 1e-6

    def test_dragging_the_same_way_keeps_working(self):
        """Not just the first drag: the canvas is unbounded in practice.

        Each drag must advance by the same amount. A rect that merely
        got bigger once would let the first drag through and stop the
        third, which is the failure mode being guarded.
        """
        v = _view(with_model=True)
        steps = []
        prev = _centre(v)
        for _ in range(5):
            _drag(v, -300, -200)
            cur = _centre(v)
            steps.append((cur.x() - prev.x(), cur.y() - prev.y()))
            prev = cur
        first = steps[0]
        assert abs(first[0]) > 1e-6 and abs(first[1]) > 1e-6, first
        for s in steps[1:]:
            assert abs(s[0] - first[0]) < 1e-6, steps
            assert abs(s[1] - first[1]) < 1e-6, steps

    def test_panning_is_reversible(self):
        """Out and back returns to where it started."""
        v = _view(with_model=True)
        start = _centre(v)
        for _ in range(3):
            _drag(v, -300, -200)
        for _ in range(3):
            _drag(v, 300, 200)
        end = _centre(v)
        assert abs(end.x() - start.x()) < 1e-6, (start, end)
        assert abs(end.y() - start.y()) < 1e-6, (start, end)

    def test_zoom_all_brings_the_view_back(self):
        """And shrinks the rect again, so the bars stay meaningful.

        The scene rect grows as the user wanders; without a way back it
        would only ever grow, and the scroll bars would end up describing
        a region nobody is looking at.
        """
        v = _view(with_model=True)
        home = _centre(v)
        wide = v.sceneRect().width()
        for _ in range(6):
            _drag(v, -300, -200)
        assert v.sceneRect().width() > wide
        v.zoom_all()
        back = _centre(v)
        assert abs(back.x() - home.x()) < 0.5, (home, back)
        assert abs(back.y() - home.y()) < 0.5, (home, back)
        assert abs(v.sceneRect().width() - wide) < 1e-6

    def test_the_model_stays_reachable_after_a_redraw(self):
        """A refresh must not yank the view back over the model."""
        v = _view(with_model=True)
        for _ in range(3):
            _drag(v, -300, -200)
        moved = _centre(v)
        v.refresh_scene()
        after = _centre(v)
        assert abs(after.x() - moved.x()) < 0.5, (moved, after)
        assert abs(after.y() - moved.y()) < 0.5, (moved, after)


class TestTheRulerIsAnOverlay:
    def test_the_viewport_repaints_whole(self):
        """Partial repaints are what smeared the labels across the model."""
        from PySide6.QtWidgets import QGraphicsView
        v = _view(with_model=True)
        assert v.viewportUpdateMode() == QGraphicsView.FullViewportUpdate

    def test_the_ruler_is_not_drawn_in_the_scene_layer(self):
        """drawBackground paints into the layer Qt scrolls."""
        import inspect
        from ogr_gui.canvas.canvas_view import CanvasView
        src = inspect.getsource(CanvasView.drawBackground)
        assert "_draw_ruler" not in src, src

    def test_the_ruler_takes_no_scene_rect(self):
        """Its coordinates are the window's; a scene rect is the trap."""
        import inspect
        from ogr_gui.canvas.canvas_view import CanvasView
        params = list(inspect.signature(CanvasView._draw_ruler).parameters)
        assert params == ["self", "painter"], params

    def test_painting_after_a_pan_does_not_raise(self):
        """The overlay runs on a real paint, at a real pan offset."""
        from PySide6.QtGui import QPixmap
        v = _view(with_model=True)
        _drag(v, -300, -200)
        pm = QPixmap(v.viewport().size())
        pm.fill()
        v.viewport().render(pm)

    def test_it_can_be_switched_off(self):
        v = _view(with_model=True)
        v.display_options.show_ruler = False
        from PySide6.QtGui import QPixmap
        pm = QPixmap(v.viewport().size()); pm.fill()
        v.viewport().render(pm)
