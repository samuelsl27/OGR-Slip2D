# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The annotation layer, drawn (v0.1.330, D332).

The layer (``ogr_core.annotations``) was stored, saved in the ``.ogr``,
edited in Manage Annotations and by an agent, measured and shown or hidden
— and no canvas drew it. Measured on the demo: 352 scene items with three
annotations and 352 without. This module turns each annotation into
graphics items; the canvas adds them over the model.

v0.1.337 — the geometry is no longer computed here. It is
``ogr_core.annotations.drawing``, the one the DXF export and the PNG draw
from too: this module turns its primitives into Qt items, and keeps only
what Qt needs to know (pens, fonts, the flipped y of the screen). What has a
size on SCREEN — text, arrow heads, the ticks of a dimension, the arc of an
angle, the cross of a one-point axes — ignores the view's transformation,
so it reads the same at every zoom (the project's rule: screen sizes in
pixels).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QPainterPath, QPen,
                           QPixmap, QTransform)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPathItem,
                               QGraphicsPixmapItem, QGraphicsSimpleTextItem)

from ogr_core.annotations import Annotation, AnnotationKind
from ogr_core.annotations import drawing as d
from ogr_core.annotations.drawing import (ARC_PX, ARROW_PX,  # noqa: F401
                                          CROSS_PX, TICK_PX)

#: Above everything the model draws: an annotation annotates the model.
Z_ANNOTATION = 20.0
#: An image is a backdrop: under the model, which is drawn over it.
Z_IMAGE = -5.0

_LINE_STYLES = {"solid": Qt.SolidLine, "dash": Qt.DashLine,
                "dot": Qt.DotLine, "dashdot": Qt.DashDotLine}


def annotation_items(annotation: Annotation) -> list:
    """The graphics items that draw ``annotation``, in model coordinates;
    none when it is hidden or has too few points to draw."""
    items = []
    for prim in d.primitives(annotation):
        items += _ITEMS[type(prim)](prim, annotation)
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


def _screen(angle: float) -> float:
    """A model angle on SCREEN: the view flips y, and an item that ignores
    its transformation does not."""
    return -angle


def _screen_item(item, at) -> QGraphicsItem:
    """``item`` drawn in screen units at the model point ``at``."""
    item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
    item.setPos(QPointF(*at))
    return item


def _stroke(s: d.Stroke, annotation: Annotation) -> list:
    path = QPainterPath()
    path.moveTo(*s.points[0])
    for p in s.points[1:]:
        path.lineTo(*p)
    if s.closed:
        path.closeSubpath()
    item = QGraphicsPathItem(path)
    pen = _pen(annotation)
    if s.dashed:
        pen.setStyle(Qt.DashLine)
    item.setPen(pen)
    style = annotation.style
    if s.filled and style.fill:
        fill = QColor(style.fill)
        fill.setAlphaF(max(0.0, min(1.0, float(style.fill_opacity))))
        item.setBrush(QBrush(fill))
    else:
        item.setBrush(Qt.NoBrush)
    return [item]


def _mark(m: d.Mark, annotation: Annotation) -> list:
    path = QPainterPath()
    pen = _pen(annotation)
    pen.setStyle(Qt.SolidLine)
    brush = Qt.NoBrush
    rotation = 0.0
    if m.kind == "arrow":
        path.moveTo(0.0, 0.0)
        path.lineTo(-ARROW_PX, -ARROW_PX / 2.5)
        path.lineTo(-ARROW_PX, ARROW_PX / 2.5)
        path.closeSubpath()
        brush = QBrush(QColor(annotation.style.colour))
        rotation = _screen(m.angle)
    elif m.kind == "tick":
        path.moveTo(0.0, -TICK_PX)
        path.lineTo(0.0, TICK_PX)
        rotation = _screen(m.angle)
    elif m.kind == "arc":
        rect = QRectF(-ARC_PX, -ARC_PX, 2 * ARC_PX, 2 * ARC_PX)
        # QPainterPath angles are counter-clockwise from +x with y DOWN,
        # which on the flipped screen is the model's own sense
        path.arcMoveTo(rect, m.angle)
        path.arcTo(rect, m.angle, m.sweep)
    elif m.kind == "cross":
        path.moveTo(-CROSS_PX, 0.0)
        path.lineTo(CROSS_PX, 0.0)
        path.moveTo(0.0, -CROSS_PX)
        path.lineTo(0.0, CROSS_PX)
        pen = _pen(annotation)
    else:
        return []
    item = QGraphicsPathItem(path)
    item.setPen(pen)
    item.setBrush(brush)
    item.setRotation(rotation)
    return [_screen_item(item, m.at)]


def _label(lab: d.Label, annotation: Annotation) -> list:
    item = QGraphicsSimpleTextItem(lab.text)
    font = QFont()
    font.setPointSizeF(max(float(annotation.style.font_size), 1.0))
    item.setFont(font)
    item.setBrush(QBrush(QColor(annotation.style.colour)))
    r = item.boundingRect()
    w, h = r.width(), r.height()
    offsets = {"at": None,
               "above": (-w / 2, -h),
               "below": (-w / 2, TICK_PX),
               "left": (-w - TICK_PX, -h / 2),
               "beside": (TICK_PX, -h / 2)}
    offset = offsets.get(lab.place)
    if offset is not None:
        item.setTransform(QTransform.fromTranslate(*offset))
    return [_screen_item(item, lab.at)]


def _picture(pic: d.Picture, annotation: Annotation) -> list:
    """The picture stretched over its rectangle; one Qt cannot load is the
    fallback frame with the file's name."""
    x0, y0, x1, y1 = pic.corners
    pix = QPixmap(pic.path)
    if pix.isNull():
        items = []
        for prim in d.picture_fallback(pic):
            items += _ITEMS[type(prim)](prim, annotation)
        return items
    item = QGraphicsPixmapItem(pix)
    # the picture's own y runs down; the model's runs up, and the view
    # flips it back: its top-left corner goes at (x0, y1)
    item.setTransform(QTransform.fromScale((x1 - x0) / pix.width(),
                                           -(y1 - y0) / pix.height()))
    item.setPos(QPointF(x0, y1))
    item.setTransformationMode(Qt.SmoothTransformation)
    return [item]


_ITEMS = {d.Stroke: _stroke, d.Mark: _mark, d.Label: _label,
          d.Picture: _picture}
