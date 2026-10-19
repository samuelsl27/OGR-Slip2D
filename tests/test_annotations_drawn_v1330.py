# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.330 (D332) — the annotation layer is drawn.

The defect, found planning D329a: the annotations (lines, arrows, text,
dimensions, axes, images…) were stored, saved in the ``.ogr``, edited in
Manage Annotations and by an agent, measured, shown and hidden — and no
canvas drew them. Measured on the demo: 352 scene items with three
annotations and 352 without; in ``ogr_gui`` only ``main_window`` read the
layer, to store and edit it. *Show / Hide All Annotations* changed nothing
that could be seen (rule 7).

What these tests protect, on the demo in a shown window:

* every one of the thirteen kinds adds something to the scene, and hiding
  the layer through the window's own action takes it away again;
* what is drawn is what the model says: a dimension shows its measured
  value or its own text, an angle its degrees, axes their coordinates at
  round steps, an image covers the rectangle of its two corners;
* text, arrow heads and ticks keep their size on screen at any zoom;
* Interpret, whose canvas is the same class, draws them too;
* axes take two corners, as the reference draws them, in the window and in
  the API (by decision of the owner); one saved with a single point is a
  cross with no coordinates.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402
from PySide6.QtWidgets import (QApplication, QGraphicsItem,  # noqa: E402
                               QGraphicsPixmapItem, QGraphicsSimpleTextItem)

_WINDOWS: list = []


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.resize(1200, 800)
    w.show()
    QApplication.processEvents()
    _WINDOWS.append(w)
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()


def _add(w, kind, points, text=""):
    from ogr_core.annotations import Annotation
    w.project.annotations.add(Annotation(kind=kind, points=points, text=text))
    w.canvas.refresh_scene()


def _texts(canvas):
    return [i.text() for i in canvas.scene().items()
            if isinstance(i, QGraphicsSimpleTextItem)]


def _png(width=4, height=2):
    from PySide6.QtGui import QColor, QImage
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor("#3070c0"))
    path = os.path.join(tempfile.mkdtemp(prefix="ogr_test_img_"), "map.png")
    assert image.save(path)
    return path


# ----------------------------------------------------------------------
class TestEveryKindIsDrawnAndHidden:
    def test_the_thirteen_kinds(self):
        from ogr_core.annotations import AnnotationKind as K
        cases = {
            K.LINE: ([(1, 1), (10, 2)], ""),
            K.ARROW: ([(1, 1), (10, 2)], ""),
            K.POLYLINE: ([(1, 1), (5, 3), (9, 1)], ""),
            K.POLYGON: ([(1, 1), (5, 3), (9, 1)], ""),
            K.RECTANGLE: ([(1, 1), (8, 4)], ""),
            K.CIRCLE: ([(5, 5), (8, 5)], ""),
            K.TEXT: ([(10, 20)], "a note"),
            K.DIMENSION_LENGTH: ([(5, 5), (20, 5)], ""),
            K.DIMENSION_ANGLE: ([(10, 0), (0, 0), (0, 10)], ""),
            K.DIMENSION_X: ([(0, 0), (12, 3)], ""),
            K.DIMENSION_Y: ([(0, 0), (12, 3)], ""),
            K.AXES: ([(0, 0), (50, 25)], ""),
            K.IMAGE: ([(0, 0), (20, 10)], _png()),
        }
        assert set(cases) == set(K), "a kind with no case"
        w = _window()
        try:
            scene = w.canvas.scene
            base = len(scene().items())
            for kind, (points, text) in cases.items():
                w.project.annotations.clear()
                _add(w, kind, points, text)
                drawn = len(scene().items())
                assert drawn > base, kind
                # the window's own action, the one the menu runs
                w._set_annotations_visible(False)
                assert len(scene().items()) == base, kind
                w._set_annotations_visible(True)
                assert len(scene().items()) == drawn, kind
        finally:
            _done(w)


class TestWhatIsDrawnIsTheModels:
    def test_a_dimension_shows_its_value_or_its_text(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        try:
            _add(w, K.DIMENSION_LENGTH, [(5, 5), (20, 5)])
            assert "15.000" in _texts(w.canvas)
            w.project.annotations.clear()
            _add(w, K.DIMENSION_LENGTH, [(5, 5), (20, 5)], text="L")
            assert "L" in _texts(w.canvas)
            assert "15.000" not in _texts(w.canvas)
            w.project.annotations.clear()
            _add(w, K.DIMENSION_X, [(0, 0), (12, 3)])
            _add(w, K.DIMENSION_Y, [(0, 0), (12, 3)])
            _add(w, K.DIMENSION_ANGLE, [(10, 0), (0, 0), (0, 10)])
            texts = _texts(w.canvas)
            assert "12.000" in texts and "3.000" in texts, texts
            assert "90.0°" in texts, texts
        finally:
            _done(w)

    def test_axes_carry_their_coordinates_at_round_steps(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        try:
            _add(w, K.AXES, [(0, 0), (50, 25)])
            texts = set(_texts(w.canvas))
            # x every 10 (nice step of 50 / 5), y every 5 (of 25 / 5)
            for label in ("0", "10", "20", "30", "40", "50", "5", "15",
                          "25"):
                assert label in texts, (label, sorted(texts))
        finally:
            _done(w)

    def test_axes_with_one_point_are_a_cross(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        try:
            base_texts = len(_texts(w.canvas))
            base = len(w.canvas.scene().items())
            _add(w, K.AXES, [(10, 10)])
            assert len(w.canvas.scene().items()) == base + 1
            assert len(_texts(w.canvas)) == base_texts
        finally:
            _done(w)

    def test_an_image_covers_its_rectangle(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        try:
            _add(w, K.IMAGE, [(0, 0), (20, 10)], _png())
            pix = [i for i in w.canvas.scene().items()
                   if isinstance(i, QGraphicsPixmapItem)]
            assert len(pix) == 1
            r = pix[0].sceneBoundingRect().normalized()
            for got, want in ((r.left(), 0.0), (r.right(), 20.0),
                              (r.top(), 0.0), (r.bottom(), 10.0)):
                assert abs(got - want) < 1e-6, (r, got, want)
            # under the model: the slope is drawn over a backdrop
            assert pix[0].zValue() < 0
        finally:
            _done(w)

    def test_a_missing_image_is_a_frame_with_its_name(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        try:
            _add(w, K.IMAGE, [(0, 0), (20, 10)],
                 os.path.join(tempfile.gettempdir(), "no_such_map.png"))
            assert not [i for i in w.canvas.scene().items()
                        if isinstance(i, QGraphicsPixmapItem)]
            assert "no_such_map.png" in _texts(w.canvas)
        finally:
            _done(w)


class TestScreenSizesStayOnScreen:
    def test_text_and_arrow_heads_ignore_the_zoom(self):
        from ogr_core.annotations import AnnotationKind as K
        w = _window()
        try:
            from ogr_gui.canvas.annotation_items import Z_ANNOTATION
            _add(w, K.TEXT, [(10, 20)], "a note")
            _add(w, K.ARROW, [(1, 1), (10, 2)])
            # the annotations' own band: the model has screen labels of its
            # own (the W of the water table sits at z 21)
            ours = [i for i in w.canvas.scene().items()
                    if abs(i.zValue() - Z_ANNOTATION) < 0.5]
            screen = [i for i in ours if i.flags()
                      & QGraphicsItem.ItemIgnoresTransformations]
            # the text, and the head of the arrow
            assert len(screen) == 2, screen
            text = next(i for i in screen
                        if isinstance(i, QGraphicsSimpleTextItem))
            shaft = next(i for i in ours if not (
                i.flags() & QGraphicsItem.ItemIgnoresTransformations))

            def on_screen(item):
                return item.deviceTransform(
                    w.canvas.viewportTransform()).mapRect(
                        item.boundingRect()).width()

            text_before, shaft_before = on_screen(text), on_screen(shaft)
            w.canvas.zoom_by(4.0)
            QApplication.processEvents()
            assert abs(on_screen(text) - text_before) < 1.0
            # control: what is drawn in model units grows with the zoom
            assert on_screen(shaft) > 3.0 * shaft_before
        finally:
            _done(w)


class TestInterpretDrawsThemToo:
    def test_its_canvas(self):
        import test_interpret_reasons_status_v1328 as interp
        from ogr_core.annotations import Annotation, AnnotationKind as K
        w = interp._interpret()
        w.project.annotations.add(
            Annotation(kind=K.TEXT, points=[(80.0, 70.0)], text="in Interpret"))
        w.canvas.refresh_scene()
        assert "in Interpret" in _texts(w.canvas)


class TestAxesTakeTwoCorners:
    def test_the_api_refuses_one(self):
        from ogr_api import Workspace, call
        from ogr_api.errors import InvalidArgument
        ws = Workspace()
        pid = call(ws, "project_new", name="Axes")["project_id"]
        with pytest.raises(InvalidArgument):
            call(ws, "annotation_set", project_id=pid, kind="axes",
                 points_xy=[[0, 0]])
        call(ws, "annotation_set", project_id=pid, kind="axes",
             points_xy=[[0, 0], [50, 25]])

    def test_the_window_asks_for_two(self):
        from PySide6.QtWidgets import QInputDialog
        from ogr_core.annotations import AnnotationKind as K
        asked = []
        raw = QInputDialog.__dict__.get("getText")
        w = _window()
        try:
            QInputDialog.getText = staticmethod(
                lambda _p, _t, prompt, *a, **k: (asked.append(prompt),
                                                 ("", False))[1])
            w._start_annotation(K.AXES)
        finally:
            if raw is None:
                del QInputDialog.getText
            else:
                QInputDialog.getText = raw
            _done(w)
        assert asked and "2" in asked[0], asked
