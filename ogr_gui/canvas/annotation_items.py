# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The annotation layer, drawn (v0.1.330, D332).

The layer (``ogr_core.annotations``) was stored, saved in the ``.ogr``,
edited in Manage Annotations and by an agent, measured and shown or hidden
— and no canvas drew it. Measured on the demo: 352 scene items with three
annotations and 352 without. This module turns each annotation into
graphics items; the canvas adds them over the model.

Geometry comes from the model: ``Annotation.outline()`` is the single
representation of a shape (a rectangle by two corners, a circle by a centre
and a point on it) and ``measured_value()`` the number a dimension reports.
What has a size on SCREEN — text, arrow heads, the ticks of a dimension, the
arc of an angle, the labels of the axes — ignores the view's transformation,
so it reads the same at every zoom (the project's rule: screen sizes in
pixels).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QPainterPath, QPen,
                           QPixmap, QPolygonF, QTransform)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPathItem,
                               QGraphicsPixmapItem, QGraphicsSimpleTextItem)

from ogr_core.annotations import Annotation, AnnotationKind

#: Above everything the model draws: an annotation annotates the model.
Z_ANNOTATION = 20.0
#: An image is a backdrop: under the model, which is drawn over it.
Z_IMAGE = -5.0
#: Screen sizes, in pixels.
ARROW_PX = 10.0
TICK_PX = 6.0
ARC_PX = 22.0
CROSS_PX = 8.0

_LINE_STYLES = {"solid": Qt.SolidLine, "dash": Qt.DashLine,
                "dot": Qt.DotLine, "dashdot": Qt.DashDotLine}


def annotation_items(annotation: Annotation) -> list:
    """The graphics items that draw ``annotation``, in model coordinates;
    none when it is hidden or has too few points to draw."""
    if not annotation.style.visible or not annotation.points:
        return []
    draw = _DRAWERS.get(annotation.kind)
    items = draw(annotation) if draw is not None else []
    z = Z_IMAGE if annotation.kind == AnnotationKind.IMAGE else Z_ANNOTATION
    for item in items:
        # z_order keeps the layer's own stacking among annotations
        item.setZValue(z + 1e-3 * annotation.z_order)
    return items


# ----------------------------------------------------------------------
def _pen(annotation: Annotation) -> QPen:
    style = annotation.style
    pen = QPen(QColor(style.colour), max(float(style.line_width), 0.0))
    pen.setStyle(_LINE_STYLES.get(style.line_style, Qt.SolidLine))
    pen.setCosmetic(True)
    return pen


def _path_item(points, annotation, closed=False) -> QGraphicsPathItem:
    path = QPainterPath()
    path.moveTo(*points[0])
    for p in points[1:]:
        path.lineTo(*p)
    if closed:
        path.closeSubpath()
    item = QGraphicsPathItem(path)
    item.setPen(_pen(annotation))
    style = annotation.style
    if closed and style.fill:
        fill = QColor(style.fill)
        fill.setAlphaF(max(0.0, min(1.0, float(style.fill_opacity))))
        item.setBrush(QBrush(fill))
    else:
        item.setBrush(Qt.NoBrush)
    return item


def _screen_item(item, at) -> QGraphicsItem:
    """``item`` drawn in screen units at the model point ``at``."""
    item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
    item.setPos(QPointF(*at))
    return item


def _text(text, at, annotation, centred=False) -> QGraphicsSimpleTextItem:
    item = QGraphicsSimpleTextItem(text)
    font = QFont()
    font.setPointSizeF(max(float(annotation.style.font_size), 1.0))
    item.setFont(font)
    item.setBrush(QBrush(QColor(annotation.style.colour)))
    if centred:
        r = item.boundingRect()
        item.setTransform(QTransform.fromTranslate(-r.width() / 2,
                                                   -r.height()))
    return _screen_item(item, at)


def _screen_angle(a, b) -> float:
    """The direction from ``a`` to ``b`` on SCREEN, in degrees: the view
    flips y, and an item that ignores its transformation does not."""
    return math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))


def _arrow_head(at, angle, annotation) -> QGraphicsPathItem:
    path = QPainterPath()
    path.moveTo(0.0, 0.0)
    path.lineTo(-ARROW_PX, -ARROW_PX / 2.5)
    path.lineTo(-ARROW_PX, ARROW_PX / 2.5)
    path.closeSubpath()
    item = QGraphicsPathItem(path)
    pen = _pen(annotation)
    pen.setStyle(Qt.SolidLine)
    item.setPen(pen)
    item.setBrush(QBrush(QColor(annotation.style.colour)))
    item.setRotation(angle)
    return _screen_item(item, at)


def _tick(at, angle, annotation) -> QGraphicsPathItem:
    """A short stroke across a dimension line at one of its ends."""
    path = QPainterPath()
    path.moveTo(0.0, -TICK_PX)
    path.lineTo(0.0, TICK_PX)
    item = QGraphicsPathItem(path)
    pen = _pen(annotation)
    pen.setStyle(Qt.SolidLine)
    item.setPen(pen)
    item.setRotation(angle)
    return _screen_item(item, at)


def _label(annotation, value, unit="") -> str:
    """A dimension shows its own text when it has one, else its value."""
    if annotation.text:
        return annotation.text
    return "" if value is None else ("%.3f" % value) + unit


# ---- the kinds ---------------------------------------------------------
def _shape(annotation):
    pts = annotation.outline()
    if len(pts) < 2:
        return []
    return [_path_item(pts, annotation, closed=annotation.closed)]


def _arrow(annotation):
    pts = annotation.outline()
    if len(pts) < 2:
        return []
    return [_path_item(pts, annotation),
            _arrow_head(pts[-1], _screen_angle(pts[-2], pts[-1]),
                        annotation)]


def _text_kind(annotation):
    if not annotation.text:
        return []
    return [_text(annotation.text, annotation.points[0], annotation)]


def _dimension(annotation, a, b, extensions=()):
    """A dimension line from ``a`` to ``b``, a tick at each end, its label
    over the middle, and dashed extension lines back to the points."""
    angle = _screen_angle(a, b)
    items = [_path_item([a, b], annotation),
             _tick(a, angle, annotation), _tick(b, angle, annotation)]
    for p, q in extensions:
        if p != q:
            ext = _path_item([p, q], annotation)
            pen = ext.pen()
            pen.setStyle(Qt.DashLine)
            ext.setPen(pen)
            items.append(ext)
    middle = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    text = _label(annotation, annotation.measured_value())
    if text:
        label = _text(text, middle, annotation, centred=True)
        if 45.0 < abs(angle) < 135.0:
            # a steep line: beside it, not over it
            label.setTransform(QTransform.fromTranslate(
                TICK_PX, -label.boundingRect().height() / 2))
        items.append(label)
    return items


def _dimension_length(annotation):
    if len(annotation.points) < 2:
        return []
    return _dimension(annotation, annotation.points[0], annotation.points[1])


def _dimension_x(annotation):
    """Horizontal, at the height of the first point; the second point is
    joined to the end of the line by an extension."""
    if len(annotation.points) < 2:
        return []
    (x0, y0), (x1, y1) = annotation.points[0], annotation.points[1]
    return _dimension(annotation, (x0, y0), (x1, y0),
                      extensions=[((x1, y0), (x1, y1))])


def _dimension_y(annotation):
    """Vertical, at the abscissa of the first point."""
    if len(annotation.points) < 2:
        return []
    (x0, y0), (x1, y1) = annotation.points[0], annotation.points[1]
    return _dimension(annotation, (x0, y0), (x0, y1),
                      extensions=[((x0, y1), (x1, y1))])


def _dimension_angle(annotation):
    """The angle at the MIDDLE point, as ``measured_value`` measures it:
    its two arms, an arc of ``ARC_PX`` and the value in degrees."""
    if len(annotation.points) < 3:
        return []
    a, v, b = annotation.points[:3]
    items = [_path_item([a, v, b], annotation)]
    start, end = _screen_angle(v, a), _screen_angle(v, b)
    sweep = (end - start + 540.0) % 360.0 - 180.0
    path = QPainterPath()
    rect = QRectF(-ARC_PX, -ARC_PX, 2 * ARC_PX, 2 * ARC_PX)
    # QPainterPath angles are counter-clockwise from +x with y DOWN
    path.arcMoveTo(rect, -start)
    path.arcTo(rect, -start, -sweep)
    arc = QGraphicsPathItem(path)
    pen = _pen(annotation)
    pen.setStyle(Qt.SolidLine)
    arc.setPen(pen)
    items.append(_screen_item(arc, v))
    value = annotation.measured_value()
    text = annotation.text or ("" if value is None else "%.1f°" % value)
    if text:
        items.append(_text(text, v, annotation))
    return items


def _axes(annotation):
    """Horizontal and vertical axes with their coordinates, from one corner
    to the other (the reference's Axes). With a single point — one saved
    before v0.1.330, when one was accepted — a cross marks where they
    start, with no coordinates."""
    if len(annotation.points) < 2:
        cross = QPainterPath()
        cross.moveTo(-CROSS_PX, 0.0)
        cross.lineTo(CROSS_PX, 0.0)
        cross.moveTo(0.0, -CROSS_PX)
        cross.lineTo(0.0, CROSS_PX)
        item = QGraphicsPathItem(cross)
        item.setPen(_pen(annotation))
        return [_screen_item(item, annotation.points[0])]
    from .snap_engine import nice_step
    (xa, ya), (xb, yb) = annotation.points[0], annotation.points[1]
    x0, x1 = sorted((xa, xb))
    y0, y1 = sorted((ya, yb))
    items = [_path_item([(x0, y0), (x1, y0)], annotation),
             _path_item([(x0, y0), (x0, y1)], annotation)]
    for lo, hi, horizontal in ((x0, x1, True), (y0, y1, False)):
        span = hi - lo
        if span <= 0:
            continue
        step = nice_step(span / 5.0)
        k = math.ceil(lo / step - 1e-9)
        while k * step <= hi + 1e-9 * span:
            t = k * step
            at = (t, y0) if horizontal else (x0, t)
            items.append(_tick(at, 0.0 if horizontal else 90.0, annotation))
            label = _text("%g" % round(t, 10), at, annotation,
                          centred=horizontal)
            if horizontal:
                # under the axis: the centred label sits above its point
                label.setTransform(label.transform().translate(
                    0.0, label.boundingRect().height() + TICK_PX))
            else:
                label.setTransform(QTransform.fromTranslate(
                    -label.boundingRect().width() - TICK_PX,
                    -label.boundingRect().height() / 2))
            items.append(label)
            k += 1
    return items


def _image(annotation):
    """The picture stretched over the rectangle of its two points, under
    the model; a missing file is a dashed frame with its name."""
    if len(annotation.points) < 2:
        return []
    (xa, ya), (xb, yb) = annotation.points[0], annotation.points[1]
    x0, x1 = sorted((xa, xb))
    y0, y1 = sorted((ya, yb))
    pix = QPixmap(annotation.text) if annotation.text else QPixmap()
    if pix.isNull() or x1 <= x0 or y1 <= y0:
        frame = _path_item([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                           annotation, closed=True)
        pen = frame.pen()
        pen.setStyle(Qt.DashLine)
        frame.setPen(pen)
        frame.setBrush(Qt.NoBrush)
        import os
        name = os.path.basename(annotation.text or "")
        return [frame] + ([_text(name, (x0, y1), annotation)] if name else [])
    item = QGraphicsPixmapItem(pix)
    # the picture's own y runs down; the model's runs up, and the view
    # flips it back: its top-left corner goes at (x0, y1)
    item.setTransform(QTransform.fromScale((x1 - x0) / pix.width(),
                                           -(y1 - y0) / pix.height()))
    item.setPos(QPointF(x0, y1))
    item.setTransformationMode(Qt.SmoothTransformation)
    return [item]


_DRAWERS = {
    AnnotationKind.LINE: _shape,
    AnnotationKind.POLYLINE: _shape,
    AnnotationKind.POLYGON: _shape,
    AnnotationKind.RECTANGLE: _shape,
    AnnotationKind.CIRCLE: _shape,
    AnnotationKind.ARROW: _arrow,
    AnnotationKind.TEXT: _text_kind,
    AnnotationKind.DIMENSION_LENGTH: _dimension_length,
    AnnotationKind.DIMENSION_X: _dimension_x,
    AnnotationKind.DIMENSION_Y: _dimension_y,
    AnnotationKind.DIMENSION_ANGLE: _dimension_angle,
    AnnotationKind.AXES: _axes,
    AnnotationKind.IMAGE: _image,
}
