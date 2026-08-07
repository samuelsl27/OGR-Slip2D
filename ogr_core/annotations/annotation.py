# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Annotation layer — phase M3.

Drawing primitives (lines, arrows, polylines, polygons, rectangles,
circles, text and dimensions) that live **alongside** the physical model
but take no part in the analysis.

The separation is the whole point and is enforced structurally, not by
convention: annotations are stored in ``Project.annotations``, a list the
solver never reads. A rectangle sketched to mark a zone of interest can
therefore never be mistaken for a material boundary, and no analysis
result can change because someone drew on the model.

The **only** bridge is :func:`to_boundary_points`, used by *Convert Tool
to Boundary*. It is explicit, one-way and user-initiated: a shape becomes
geometry when the engineer says so, never by accident.

Kept free of Qt so the geometry, the serialisation and — most
importantly — the isolation from the model can be tested without a
display.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AnnotationKind(Enum):
    LINE = "line"
    ARROW = "arrow"
    POLYLINE = "polyline"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    TEXT = "text"
    DIMENSION_LENGTH = "dimension_length"
    DIMENSION_ANGLE = "dimension_angle"
    DIMENSION_X = "dimension_x"
    DIMENSION_Y = "dimension_y"
    AXES = "axes"
    IMAGE = "image"


# Shapes that close by definition, whatever the user's points say.
_CLOSED_KINDS = {AnnotationKind.POLYGON, AnnotationKind.RECTANGLE,
                 AnnotationKind.CIRCLE}

# Shapes that can meaningfully become model geometry. A dimension or a
# text label cannot: they annotate geometry, they are not geometry.
CONVERTIBLE_KINDS = {AnnotationKind.LINE, AnnotationKind.POLYLINE,
                     AnnotationKind.POLYGON, AnnotationKind.RECTANGLE,
                     AnnotationKind.CIRCLE}


@dataclass
class AnnotationStyle:
    """Appearance of an annotation."""

    colour: str = "#202020"
    line_width: float = 1.0
    line_style: str = "solid"      # solid | dash | dot | dashdot
    fill: Optional[str] = None     # None = no fill
    fill_opacity: float = 0.25
    font_size: float = 10.0
    visible: bool = True

    def to_dict(self) -> dict:
        return {"colour": self.colour, "line_width": self.line_width,
                "line_style": self.line_style, "fill": self.fill,
                "fill_opacity": self.fill_opacity,
                "font_size": self.font_size, "visible": self.visible}

    @classmethod
    def from_dict(cls, d: dict) -> "AnnotationStyle":
        return cls(colour=str(d.get("colour", "#202020")),
                   line_width=float(d.get("line_width", 1.0)),
                   line_style=str(d.get("line_style", "solid")),
                   fill=d.get("fill"),
                   fill_opacity=float(d.get("fill_opacity", 0.25)),
                   font_size=float(d.get("font_size", 10.0)),
                   visible=bool(d.get("visible", True)))


@dataclass
class Annotation:
    """One drawing object on the annotation layer."""

    kind: AnnotationKind = AnnotationKind.LINE
    points: list = field(default_factory=list)   # [(x, y), ...]
    text: str = ""
    style: AnnotationStyle = field(default_factory=AnnotationStyle)
    z_order: int = 0
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            import uuid
            self.id = uuid.uuid4().hex[:12]

    # ------------------------------------------------------------------
    @property
    def closed(self) -> bool:
        return self.kind in _CLOSED_KINDS

    @property
    def convertible(self) -> bool:
        """Whether *Convert Tool to Boundary* can act on this.

        A dimension or a text label annotates geometry; it is not
        geometry, and converting it would produce nonsense.
        """
        return self.kind in CONVERTIBLE_KINDS and len(self.points) >= 2

    def outline(self, segments: int = 48) -> list:
        """The shape as an explicit point list.

        Rectangles and circles are stored by their defining points — two
        corners, or a centre and a radius point — because that is what
        the user manipulates. They are expanded here, so everything
        downstream (drawing, export, conversion) sees one representation.
        """
        pts = list(self.points)
        if self.kind == AnnotationKind.RECTANGLE and len(pts) >= 2:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        if self.kind == AnnotationKind.CIRCLE and len(pts) >= 2:
            cx, cy = pts[0]
            r = math.dist(pts[0], pts[1])
            out = [(cx + r * math.cos(2 * math.pi * i / segments),
                    cy + r * math.sin(2 * math.pi * i / segments))
                   for i in range(segments)]
            out.append(out[0])
            return out
        if self.kind == AnnotationKind.POLYGON and len(pts) >= 3 \
                and pts[0] != pts[-1]:
            return pts + [pts[0]]
        return pts

    def length(self) -> float:
        pts = self.outline()
        return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))

    def measured_value(self) -> Optional[float]:
        """What a dimension annotation reports.

        Returned as a number rather than a formatted string so the caller
        controls units and precision, and so it can be tested exactly.
        """
        pts = self.points
        if self.kind == AnnotationKind.DIMENSION_LENGTH and len(pts) >= 2:
            return math.dist(pts[0], pts[1])
        if self.kind == AnnotationKind.DIMENSION_X and len(pts) >= 2:
            return abs(pts[1][0] - pts[0][0])
        if self.kind == AnnotationKind.DIMENSION_Y and len(pts) >= 2:
            return abs(pts[1][1] - pts[0][1])
        if self.kind == AnnotationKind.DIMENSION_ANGLE and len(pts) >= 3:
            # Angle at the MIDDLE point, which is the vertex the user
            # picked second — the convention every CAD program uses.
            (ax, ay), (bx, by), (cx, cy) = pts[0], pts[1], pts[2]
            v1 = (ax - bx, ay - by)
            v2 = (cx - bx, cy - by)
            n1 = math.hypot(*v1)
            n2 = math.hypot(*v2)
            if n1 < 1e-12 or n2 < 1e-12:
                return None
            cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
            return math.degrees(math.acos(min(max(cosang, -1.0), 1.0)))
        return None

    def bbox(self):
        pts = self.outline()
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def translate(self, dx: float, dy: float) -> None:
        self.points = [(x + dx, y + dy) for x, y in self.points]

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"kind": self.kind.value, "points": [list(p)
                                                    for p in self.points],
                "text": self.text, "style": self.style.to_dict(),
                "z_order": self.z_order, "id": self.id}

    @classmethod
    def from_dict(cls, d: dict) -> "Annotation":
        return cls(
            kind=AnnotationKind(d.get("kind", "line")),
            points=[tuple(p) for p in d.get("points", [])],
            text=str(d.get("text", "")),
            style=AnnotationStyle.from_dict(d.get("style", {})),
            z_order=int(d.get("z_order", 0)),
            id=str(d.get("id", "")),
        )


# ======================================================================
def to_boundary_points(annotation: Annotation) -> Optional[list]:
    """The **only** bridge from the annotation layer to the model.

    Used by *Convert Tool to Boundary*. Returns the point list a boundary
    should be built from, or None when the shape cannot become geometry.

    Deliberately one-way and explicit: nothing converts itself. A sketch
    becomes part of the model when the engineer says so, which is what
    keeps an analysis result from changing because someone drew on the
    drawing.
    """
    if not annotation.convertible:
        return None
    pts = annotation.outline()
    # Drop consecutive duplicates: they carry no shape and would produce
    # zero-length segments in the model.
    clean = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, clean[-1]) > 1e-12:
            clean.append(p)
    if len(clean) < 2:
        return None
    return clean


# ======================================================================
class AnnotationLayer:
    """The collection of annotations of a project.

    A thin wrapper rather than a bare list, because Z-order, bulk
    visibility and "delete all" are operations the interface needs and
    that would otherwise be reimplemented at each call site.
    """

    def __init__(self, items=None) -> None:
        self.items: list = list(items or [])

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def add(self, annotation: Annotation) -> Annotation:
        if annotation.z_order == 0:
            annotation.z_order = self.next_z()
        self.items.append(annotation)
        return annotation

    def remove(self, annotation_id: str) -> bool:
        before = len(self.items)
        self.items = [a for a in self.items if a.id != annotation_id]
        return len(self.items) != before

    def clear(self) -> None:
        self.items = []

    def get(self, annotation_id: str) -> Optional[Annotation]:
        for a in self.items:
            if a.id == annotation_id:
                return a
        return None

    # ------------------------------------------------------------------
    def next_z(self) -> int:
        return max((a.z_order for a in self.items), default=0) + 1

    def bring_to_front(self, annotation_id: str) -> bool:
        a = self.get(annotation_id)
        if a is None:
            return False
        a.z_order = self.next_z()
        return True

    def send_to_back(self, annotation_id: str) -> bool:
        a = self.get(annotation_id)
        if a is None:
            return False
        a.z_order = min((x.z_order for x in self.items), default=1) - 1
        return True

    def ordered(self) -> list:
        """Items in drawing order: lowest Z first, so later items paint
        on top."""
        return sorted(self.items, key=lambda a: a.z_order)

    def set_all_visible(self, visible: bool) -> None:
        for a in self.items:
            a.style.visible = bool(visible)

    def visible_items(self) -> list:
        return [a for a in self.ordered() if a.style.visible]

    def copy_style(self, source_id: str, target_ids) -> int:
        """Paste one annotation's appearance onto others."""
        src = self.get(source_id)
        if src is None:
            return 0
        n = 0
        for tid in target_ids:
            tgt = self.get(tid)
            if tgt is None or tgt is src:
                continue
            tgt.style = AnnotationStyle.from_dict(src.style.to_dict())
            n += 1
        return n

    def duplicate(self, annotation_id: str, dx: float = 0.0,
                  dy: float = 0.0) -> Optional[Annotation]:
        src = self.get(annotation_id)
        if src is None:
            return None
        clone = Annotation.from_dict(src.to_dict())
        clone.id = ""
        clone.__post_init__()
        clone.translate(dx, dy)
        clone.z_order = self.next_z()
        self.items.append(clone)
        return clone

    # ------------------------------------------------------------------
    def to_list(self) -> list:
        return [a.to_dict() for a in self.items]

    @classmethod
    def from_list(cls, data) -> "AnnotationLayer":
        return cls([Annotation.from_dict(d) for d in (data or [])])
