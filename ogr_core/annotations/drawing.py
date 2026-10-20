# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The annotation layer as drawing primitives (v0.1.337).

One geometry for every place that draws the layer: the canvas
(``ogr_gui.canvas.annotation_items``, since v0.1.330), the DXF export
(``ogr_core.dxf.exporter``) and the PNG an agent renders. What a dimension
measures, where the ticks of the axes fall, which way an arrow points and
where a label goes are written once, here, and each adapter turns the
primitives into its own entities. Until this version the canvas computed
them itself, and the DXF did not draw the layer at all.

Coordinates are the model's (metres, y up). What has a size on SCREEN — an
arrow head, the tick of a dimension, the arc of an angle, the cross of a
one-point axes, the text — is a :class:`Mark` or a :class:`Label` with its
size in pixels: the canvas keeps it at that size at every zoom, and an
adapter with no screen (DXF, a PNG) converts pixels to model units at a
scale of its own.

Angles are in degrees, counter-clockwise from +x in MODEL coordinates. The
canvas, whose screen y runs down, turns them round.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Optional

from ogr_core.numbers import nice_step

from .annotation import Annotation, AnnotationKind

#: Screen sizes, in pixels.
ARROW_PX = 10.0
TICK_PX = 6.0
ARC_PX = 22.0
CROSS_PX = 8.0


@dataclass(frozen=True)
class Stroke:
    """A polyline in model coordinates, in the annotation's colour and line
    style. ``dashed`` draws it dashed whatever that style is (the extension
    lines of a dimension, the frame of a missing picture); ``filled`` gives
    it the annotation's fill, when it has one."""
    points: tuple
    closed: bool = False
    dashed: bool = False
    filled: bool = False


@dataclass(frozen=True)
class Mark:
    """A symbol with a size on SCREEN at a model point: ``"arrow"`` (its tip
    at ``at``, pointing along ``angle``), ``"tick"`` (a short stroke across
    a line of direction ``angle``), ``"arc"`` (radius ``ARC_PX``, from
    ``angle`` through ``sweep`` degrees) or ``"cross"``."""
    kind: str
    at: tuple
    angle: float = 0.0
    sweep: float = 0.0


@dataclass(frozen=True)
class Label:
    """Text at a model point. ``place`` says where it goes from the point:
    ``"at"`` (its top-left corner there), ``"above"`` (centred over it),
    ``"below"`` (centred under it, clear of a tick), ``"left"`` (to its left,
    centred in height) or ``"beside"`` (to its right, centred in height)."""
    text: str
    at: tuple
    place: str = "at"


@dataclass(frozen=True)
class Picture:
    """An image file stretched over a rectangle, under the model."""
    path: str
    corners: tuple          # (x0, y0, x1, y1), with x0 < x1 and y0 < y1


@dataclass(frozen=True)
class Dimension:
    """What a dimension annotation measures, for an adapter with a
    dimension entity of its own (DXF): ``"aligned"`` from the first point
    to the second, ``"horizontal"`` or ``"vertical"`` (the line at the first
    point's ordinate or abscissa), or ``"angle"`` at the MIDDLE point.
    ``text`` is the annotation's own, which replaces the measured value."""
    kind: str
    points: tuple
    text: str = ""


def angle_of(a, b) -> float:
    """The direction from ``a`` to ``b``, in model degrees."""
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def dimension_text(annotation: Annotation) -> str:
    """What a length dimension shows: its own text, or its value to the
    millimetre."""
    if annotation.text:
        return annotation.text
    value = annotation.measured_value()
    return "" if value is None else "%.3f" % value


def angle_text(annotation: Annotation) -> str:
    """What an angle dimension shows: its own text, or its degrees."""
    if annotation.text:
        return annotation.text
    value = annotation.measured_value()
    return "" if value is None else "%.1f°" % value


def axes_ticks(lo: float, hi: float) -> list:
    """Where the ticks of an axis from ``lo`` to ``hi`` fall: round steps
    (``nice_step`` of a fifth of the span), inside the span."""
    span = hi - lo
    if span <= 0:
        return []
    step = nice_step(span / 5.0)
    out = []
    k = math.ceil(lo / step - 1e-9)
    while k * step <= hi + 1e-9 * span:
        out.append(k * step)
        k += 1
    return out


def axes_label(value: float) -> str:
    return "%g" % round(value, 10)


def dimension(annotation: Annotation) -> Optional[Dimension]:
    """The dimension an annotation is, or None when it is not one (or has
    too few points)."""
    pts = tuple(tuple(p) for p in annotation.points)
    kinds = {AnnotationKind.DIMENSION_LENGTH: ("aligned", 2),
             AnnotationKind.DIMENSION_X: ("horizontal", 2),
             AnnotationKind.DIMENSION_Y: ("vertical", 2),
             AnnotationKind.DIMENSION_ANGLE: ("angle", 3)}
    kind = kinds.get(annotation.kind)
    if kind is None or len(pts) < kind[1]:
        return None
    return Dimension(kind[0], pts[:kind[1]], annotation.text)


def picture_fallback(picture: Picture) -> list:
    """What stands for a picture whose file cannot be shown: a dashed frame
    over its rectangle and the file's name at its top-left corner."""
    x0, y0, x1, y1 = picture.corners
    out = [Stroke(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), closed=True,
                  dashed=True)]
    name = os.path.basename(picture.path or "")
    if name:
        out.append(Label(name, (x0, y1)))
    return out


# ---------------------------------------------------------------- the kinds
def primitives(annotation: Annotation) -> list:
    """The primitives that draw ``annotation``; none when it is hidden or
    has too few points. A dimension comes as its line, ticks, extension
    lines and label; :func:`dimension` gives the same dimension whole."""
    if not annotation.style.visible or not annotation.points:
        return []
    draw = _KINDS.get(annotation.kind)
    return draw(annotation) if draw is not None else []


def _shape(a: Annotation) -> list:
    pts = a.outline()
    if len(pts) < 2:
        return []
    return [Stroke(tuple(pts), closed=a.closed, filled=a.closed)]


def _arrow(a: Annotation) -> list:
    pts = a.outline()
    if len(pts) < 2:
        return []
    return [Stroke(tuple(pts)),
            Mark("arrow", tuple(pts[-1]), angle_of(pts[-2], pts[-1]))]


def _text(a: Annotation) -> list:
    if not a.text:
        return []
    return [Label(a.text, tuple(a.points[0]))]


def _dimension_parts(a: Annotation, p, q, extensions=()) -> list:
    """A dimension line from ``p`` to ``q``, a tick at each end, dashed
    extension lines back to the points and the label over the middle —
    beside the line when it is steep."""
    angle = angle_of(p, q)
    out = [Stroke((p, q)), Mark("tick", p, angle), Mark("tick", q, angle)]
    for e0, e1 in extensions:
        if e0 != e1:
            out.append(Stroke((e0, e1), dashed=True))
    text = dimension_text(a)
    if text:
        middle = ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)
        place = "beside" if 45.0 < abs(angle) < 135.0 else "above"
        out.append(Label(text, middle, place))
    return out


def _dimension_length(a: Annotation) -> list:
    if len(a.points) < 2:
        return []
    return _dimension_parts(a, tuple(a.points[0]), tuple(a.points[1]))


def _dimension_x(a: Annotation) -> list:
    """Horizontal, at the height of the first point; the second point is
    joined to the end of the line by an extension."""
    if len(a.points) < 2:
        return []
    (x0, y0), (x1, y1) = a.points[0], a.points[1]
    return _dimension_parts(a, (x0, y0), (x1, y0),
                            extensions=[((x1, y0), (x1, y1))])


def _dimension_y(a: Annotation) -> list:
    """Vertical, at the abscissa of the first point."""
    if len(a.points) < 2:
        return []
    (x0, y0), (x1, y1) = a.points[0], a.points[1]
    return _dimension_parts(a, (x0, y0), (x0, y1),
                            extensions=[((x0, y1), (x1, y1))])


def _dimension_angle(a: Annotation) -> list:
    """The angle at the MIDDLE point, as ``measured_value`` measures it: its
    two arms, an arc of ``ARC_PX`` the short way round, and the degrees."""
    if len(a.points) < 3:
        return []
    p, v, q = (tuple(x) for x in a.points[:3])
    start, end = angle_of(v, p), angle_of(v, q)
    sweep = (end - start + 540.0) % 360.0 - 180.0
    out = [Stroke((p, v, q)), Mark("arc", v, start, sweep)]
    text = angle_text(a)
    if text:
        out.append(Label(text, v))
    return out


def _axes(a: Annotation) -> list:
    """Horizontal and vertical axes from one corner to the other, with ticks
    and coordinates at round steps (the reference's Axes). With a single
    point — saved before v0.1.330, when one was accepted — a cross marks
    where they start, with no coordinates."""
    if len(a.points) < 2:
        return [Mark("cross", tuple(a.points[0]))]
    (xa, ya), (xb, yb) = a.points[0], a.points[1]
    x0, x1 = sorted((xa, xb))
    y0, y1 = sorted((ya, yb))
    out = [Stroke(((x0, y0), (x1, y0))), Stroke(((x0, y0), (x0, y1)))]
    for t in axes_ticks(x0, x1):
        out += [Mark("tick", (t, y0), 0.0),
                Label(axes_label(t), (t, y0), "below")]
    for t in axes_ticks(y0, y1):
        out += [Mark("tick", (x0, t), 90.0),
                Label(axes_label(t), (x0, t), "left")]
    return out


def _image(a: Annotation) -> list:
    """The picture over the rectangle of its two points; an empty rectangle
    or no file is the fallback frame at once."""
    if len(a.points) < 2:
        return []
    (xa, ya), (xb, yb) = a.points[0], a.points[1]
    x0, x1 = sorted((xa, xb))
    y0, y1 = sorted((ya, yb))
    pic = Picture(a.text or "", (x0, y0, x1, y1))
    if not a.text or x1 <= x0 or y1 <= y0:
        return picture_fallback(pic)
    return [pic]


_KINDS = {
    AnnotationKind.LINE: _shape,
    AnnotationKind.POLYLINE: _shape,
    AnnotationKind.POLYGON: _shape,
    AnnotationKind.RECTANGLE: _shape,
    AnnotationKind.CIRCLE: _shape,
    AnnotationKind.ARROW: _arrow,
    AnnotationKind.TEXT: _text,
    AnnotationKind.DIMENSION_LENGTH: _dimension_length,
    AnnotationKind.DIMENSION_X: _dimension_x,
    AnnotationKind.DIMENSION_Y: _dimension_y,
    AnnotationKind.DIMENSION_ANGLE: _dimension_angle,
    AnnotationKind.AXES: _axes,
    AnnotationKind.IMAGE: _image,
}
