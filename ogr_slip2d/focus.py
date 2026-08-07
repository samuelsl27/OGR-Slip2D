# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Focus objects — phase M4.

A grid search generates circles from the slope limits and the radius
increment, which means most of them sweep regions the engineer already
knows are irrelevant. A **focus object** narrows the set: only circles
that interact with it are kept.

Four kinds, following the reference:

``WINDOW``   an arbitrary quadrilateral; a circle must pass through it.
``LINE``     a segment; a circle must cross it.
``POINT``    a single point; a circle must pass within a tolerance of it.
``TANGENT``  a segment; a circle must be **tangent** to it — a different
             condition from crossing, and the one that lets a user aim at
             a known weak layer.

Kept free of Qt so the geometry can be tested exactly.

Design note: filtering happens **before** the factor of safety is
computed, not after. Rejecting a circle costs a couple of distance
calculations; evaluating one costs a full slicing and iteration, so the
order is what makes focusing worth using rather than merely tidy.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FocusKind(Enum):
    WINDOW = "window"
    LINE = "line"
    POINT = "point"
    TANGENT = "tangent"


def _seg_circle_crosses(p1, p2, cx, cy, r) -> bool:
    """Whether a segment crosses a circle's circumference.

    Not "intersects the disc": a segment entirely inside the circle never
    crosses the arc, and a slip surface that never reaches the segment is
    not focused on it.
    """
    d1 = math.dist(p1, (cx, cy))
    d2 = math.dist(p2, (cx, cy))
    if (d1 - r) * (d2 - r) < 0:
        return True                      # one end in, one end out
    # Both outside: the segment may still cut a chord
    if d1 > r and d2 > r:
        return _closest_distance(p1, p2, cx, cy) < r
    return False


def _closest_distance(p1, p2, cx, cy) -> float:
    ax, ay = p1
    bx, by = p2
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-30:
        return math.dist(p1, (cx, cy))
    t = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / L2))
    return math.dist((ax + t * dx, ay + t * dy), (cx, cy))


def _point_in_polygon(x, y, pts) -> bool:
    inside = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xint = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xint:
                inside = not inside
    return inside


@dataclass
class FocusObject:
    """A region, line, point or tangent the search must respect."""

    kind: FocusKind = FocusKind.POINT
    points: list = field(default_factory=list)
    # Capture tolerance for POINT and TANGENT, in model units. Zero would
    # accept nothing, since an exact tangency never happens in a
    # discretised search.
    tolerance: float = 0.5
    enabled: bool = True
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            import uuid
            self.id = uuid.uuid4().hex[:12]

    # ------------------------------------------------------------------
    @property
    def valid(self) -> bool:
        need = {FocusKind.WINDOW: 3, FocusKind.LINE: 2,
                FocusKind.POINT: 1, FocusKind.TANGENT: 2}[self.kind]
        return len(self.points) >= need

    def accepts_circle(self, cx: float, cy: float, r: float) -> bool:
        """Whether a slip circle interacts with this focus object."""
        if not self.enabled or not self.valid or r <= 0:
            return True          # a disabled or malformed object filters
            #                      nothing, rather than silently rejecting
            #                      every surface

        if self.kind == FocusKind.POINT:
            px, py = self.points[0]
            return abs(math.dist((px, py), (cx, cy)) - r) <= self.tolerance

        if self.kind == FocusKind.LINE:
            return _seg_circle_crosses(self.points[0], self.points[1],
                                       cx, cy, r)

        if self.kind == FocusKind.TANGENT:
            # Tangency: the perpendicular distance from the centre to the
            # LINE equals the radius. The infinite line is used, not the
            # segment, because a circle tangent to the line beyond the
            # drawn extent is still tangent to that plane — which is what
            # a weak layer represents.
            d = _distance_point_line(cx, cy, self.points[0],
                                     self.points[1])
            return abs(d - r) <= self.tolerance

        # WINDOW: the circle must pass through the quadrilateral, i.e.
        # some point of the circumference lies inside it.
        pts = list(self.points)
        for i in range(72):
            a = 2.0 * math.pi * i / 72
            if _point_in_polygon(cx + r * math.cos(a),
                                 cy + r * math.sin(a), pts):
                return True
        return False

    def bbox(self):
        if not self.points:
            return None
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def to_dict(self) -> dict:
        return {"kind": self.kind.value,
                "points": [list(p) for p in self.points],
                "tolerance": self.tolerance, "enabled": self.enabled,
                "id": self.id}

    @classmethod
    def from_dict(cls, d: dict) -> "FocusObject":
        return cls(kind=FocusKind(d.get("kind", "point")),
                   points=[tuple(p) for p in d.get("points", [])],
                   tolerance=float(d.get("tolerance", 0.5)),
                   enabled=bool(d.get("enabled", True)),
                   id=str(d.get("id", "")))


def _distance_point_line(px, py, a, b) -> float:
    """Perpendicular distance to the INFINITE line through a and b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    if n < 1e-12:
        return math.dist((px, py), a)
    return abs(dy * (px - ax) - dx * (py - ay)) / n


# ======================================================================
def accepts(focus_objects, cx: float, cy: float, r: float) -> bool:
    """Whether a circle satisfies EVERY enabled focus object.

    Conjunction, not disjunction: adding a second object narrows the
    search further, which is what "focus" means. An empty list accepts
    everything, so the feature costs nothing when unused.
    """
    for fo in focus_objects or ():
        if not fo.accepts_circle(cx, cy, r):
            return False
    return True


def filter_circles(focus_objects, circles):
    """Keep the circles that satisfy the focus objects.

    ``circles`` is any iterable of objects with ``centre_x``,
    ``centre_y`` and ``radius``.
    """
    return [c for c in circles
            if accepts(focus_objects, c.centre_x, c.centre_y, c.radius)]
