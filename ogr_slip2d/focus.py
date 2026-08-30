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

Kept free of Qt so the geometry can be tested exactly. It takes plain
``(x, y)`` tuples rather than engine types for the same reason.

Design note: filtering happens **before** the factor of safety is
computed, not after. Rejecting a circle costs a couple of distance
calculations; evaluating one costs a full slicing and iteration, so the
order is what makes focusing worth using rather than merely tidy.

Two families of predicate, and the difference is not cosmetic
-------------------------------------------------------------

:meth:`FocusObject.accepts_circle` answers about a centre and a radius;
:meth:`FocusObject.accepts_surface` answers about a piece-wise linear
surface. A search asks the one that matches what it GENERATES, and never
the other: a circle re-tested as its own chord approximation answers a
different question, which is the same argument v0.1.118 makes about
inscribed polylines not being the arc.

v0.1.129 — the surface family did not exist, so ``PathSearch``,
``BlockSearch`` and ``SimulatedAnnealingSearch`` could not have honoured
a focus object even once they were handed one (defect D33).

**Where this departs from the reference, said out loud.** The reference
documents focus objects for the Grid Search and the Slope Search, both
circular, and defines all four as rules for GENERATING the circle radii
at a slip centre — with a Focus Point or a Focus Tangent it generates
exactly ONE circle per centre and states that the Radius Increment stops
applying. This module has always implemented them as a FILTER over the
radii the slope limits produce instead, which is why ``tolerance`` exists
here and has no counterpart there. A filter is what generalises to a
polyline; a radius rule is not. So the surface predicates below are
faithful translations for POINT, LINE and WINDOW, and for TANGENT they
are OUR reading — see :meth:`accepts_surface`.

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


def _orient(a, b, c) -> float:
    """Twice the signed area of the triangle a-b-c."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p) -> bool:
    """Whether p, ALREADY KNOWN collinear with a-b, lies within it."""
    return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
            and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def _segments_cross(p1, p2, q1, q2) -> bool:
    """Whether two segments intersect, a bare touch included.

    A touch counts because a slip surface that grazes the focus segment
    has reached it, and the alternative would make acceptance depend on
    whether a vertex happened to land exactly on the line.
    """
    d1 = _orient(q1, q2, p1)
    d2 = _orient(q1, q2, p2)
    d3 = _orient(p1, p2, q1)
    d4 = _orient(p1, p2, q2)
    if ((d1 > 0.0) != (d2 > 0.0)) and ((d3 > 0.0) != (d4 > 0.0)):
        return True
    if d1 == 0.0 and _on_segment(q1, q2, p1):
        return True
    if d2 == 0.0 and _on_segment(q1, q2, p2):
        return True
    if d3 == 0.0 and _on_segment(p1, p2, q1):
        return True
    if d4 == 0.0 and _on_segment(p1, p2, q2):
        return True
    return False


def _polyline_point_distance(pts, q) -> float:
    """Shortest distance from a piece-wise linear surface to a point."""
    return min(_closest_distance(pts[i], pts[i + 1], q[0], q[1])
               for i in range(len(pts) - 1))


def _signed_distance_point_line(px, py, a, b) -> float:
    """Perpendicular distance to the INFINITE line, WITH a sign.

    The sign is what separates tangency from crossing: an unsigned
    distance cannot tell a surface that touches the line from one that
    goes through it and comes back.
    """
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    if n < 1e-12:
        return math.dist((px, py), a)
    return (dy * (px - ax) - dx * (py - ay)) / n


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

    def accepts_surface(self, points) -> bool:
        """Whether a piece-wise linear slip surface interacts with this.

        ``points`` is the surface's ``(x, y)`` vertices in order.

        v0.1.129, defect D33. Three of the four kinds translate from the
        circular predicate above without deciding anything: passing
        through a point, crossing a segment and passing through a window
        mean the same thing whatever shape the surface is, and the window
        case is literally how the reference words it — the focus window
        "guarantees that all slip surfaces will pass through" it.

        TANGENT is the one that had to be DEFINED, because the reference
        never applies a focus object to a non-circular search and so never
        says what tangency to a polyline is. The reading taken here is the
        one that keeps the circular meaning intact: a circle is tangent to
        a line when it TOUCHES the line WITHOUT CROSSING it, so a surface
        is taken as tangent when it reaches the infinite line to within
        the tolerance and does not pass through to the other side.

        What decided it is that every tangent focus in the reference bank
        is a HORIZONTAL line at the base of a stratum, and there this
        reduces to "the lowest point of the surface sits at that
        elevation" — which is word for word the statement of the case it
        models ("the surface is tangent to the bottom of the foundation").

        Note this is NOT the same question as ``min_elevation``. That
        filter says how deep a surface may go; this one says the surface
        must actually GET there. A shallow surface passes the filter and
        fails the focus, which is the whole point of the two cases.
        """
        if not self.enabled or not self.valid or len(points or ()) < 2:
            return True          # same contract as accepts_circle: a
            #                      disabled or malformed object filters
            #                      nothing rather than rejecting all

        pts = [(float(x), float(y)) for x, y in points]

        if self.kind == FocusKind.POINT:
            return _polyline_point_distance(
                pts, self.points[0]) <= self.tolerance

        if self.kind == FocusKind.LINE:
            a, b = self.points[0], self.points[1]
            return any(_segments_cross(pts[i], pts[i + 1], a, b)
                       for i in range(len(pts) - 1))

        if self.kind == FocusKind.TANGENT:
            a, b = self.points[0], self.points[1]
            # The INFINITE line, as in accepts_circle and for the same
            # reason: a surface tangent to the plane of a weak layer
            # beyond the drawn extent is still tangent to that plane.
            signed = [_signed_distance_point_line(x, y, a, b)
                      for (x, y) in pts]
            touches = min(abs(s) for s in signed) <= self.tolerance
            crosses = (max(signed) > self.tolerance
                       and min(signed) < -self.tolerance)
            return touches and not crosses

        # WINDOW: some part of the surface lies inside the polygon. Asked
        # exactly rather than by sampling along the segments: if a surface
        # enters the window then either one of its vertices is inside it
        # or one of its segments cuts an edge, so the two tests together
        # are complete and neither depends on a sampling step.
        poly = list(self.points)
        if any(_point_in_polygon(x, y, poly) for (x, y) in pts):
            return True
        n = len(poly)
        for i in range(len(pts) - 1):
            for j in range(n):
                if _segments_cross(pts[i], pts[i + 1],
                                   poly[j], poly[(j + 1) % n]):
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


def accepts_surface(focus_objects, points) -> bool:
    """Whether a piece-wise linear surface satisfies EVERY focus object.

    The surface-shaped twin of :func:`accepts`, and a conjunction for the
    same reason. ``points`` is the surface's ``(x, y)`` vertices in order.
    """
    for fo in focus_objects or ():
        if not fo.accepts_surface(points):
            return False
    return True


def filter_circles(focus_objects, circles):
    """Keep the circles that satisfy the focus objects.

    ``circles`` is any iterable of objects with ``centre_x``,
    ``centre_y`` and ``radius``.
    """
    return [c for c in circles
            if accepts(focus_objects, c.centre_x, c.centre_y, c.radius)]
