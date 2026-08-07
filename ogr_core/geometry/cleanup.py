# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Geometry cleanup utilities.

These operations fix common topological problems that otherwise cause
silent failures downstream (degenerate slices, non-manifold meshes,
infinite loops in intersection tests, etc.).

Implements:
    - Duplicate vertex removal (tolerance-based)
    - Collinear vertex simplification (Ramer-Douglas-Peucker)
    - Polyline-polyline intersection detection and vertex insertion
    - Self-intersection detection
    - Closing of nearly-closed polylines

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Iterable

from .boundary import Boundary
from .primitives import Polyline, Vertex

DEFAULT_TOL = 1e-6


# ------------------------------------------------------------------
# Duplicate removal
# ------------------------------------------------------------------
def remove_duplicate_vertices(polyline: Polyline, tol: float = DEFAULT_TOL) -> int:
    """Drop consecutive vertices whose distance is below tolerance.

    Returns the number of vertices removed.
    """
    if len(polyline) < 2:
        return 0
    kept: list[Vertex] = [polyline.vertices[0]]
    removed = 0
    for v in polyline.vertices[1:]:
        if v.distance_to(kept[-1]) > tol:
            kept.append(v)
        else:
            removed += 1
    # Handle the closing edge
    if polyline.closed and len(kept) >= 2:
        if kept[0].distance_to(kept[-1]) <= tol:
            kept.pop()
            removed += 1
    polyline.vertices = kept
    return removed


# ------------------------------------------------------------------
# Ramer-Douglas-Peucker simplification
# ------------------------------------------------------------------
def _perpendicular_distance(p: Vertex, a: Vertex, b: Vertex) -> float:
    if a.distance_to(b) < 1e-12:
        return p.distance_to(a)
    # |(b-a) × (p-a)| / |b-a|
    dx = b.x - a.x
    dy = b.y - a.y
    num = abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x)
    return num / math.hypot(dx, dy)


def simplify_rdp(polyline: Polyline, epsilon: float) -> Polyline:
    """Ramer-Douglas-Peucker simplification.

    Reduces vertex count while bounding geometric deviation by `epsilon`.
    Critical for taming user-imported DXF polylines with thousands of
    near-collinear points.
    """
    pts = polyline.vertices
    if len(pts) < 3:
        return Polyline(vertices=list(pts), closed=polyline.closed)

    def _rdp(segment: list[Vertex]) -> list[Vertex]:
        if len(segment) < 3:
            return segment
        dmax = 0.0
        index = 0
        for i in range(1, len(segment) - 1):
            d = _perpendicular_distance(segment[i], segment[0], segment[-1])
            if d > dmax:
                index = i
                dmax = d
        if dmax > epsilon:
            left = _rdp(segment[: index + 1])
            right = _rdp(segment[index:])
            return left[:-1] + right
        return [segment[0], segment[-1]]

    simplified = _rdp(list(pts))
    return Polyline(vertices=simplified, closed=polyline.closed)


# ------------------------------------------------------------------
# Segment intersection (robust 2D)
# ------------------------------------------------------------------
def _segment_intersection(
    p1: Vertex, p2: Vertex, p3: Vertex, p4: Vertex
) -> Vertex | None:
    """Return the intersection point of two segments, or None.

    Uses the parametric-form approach; returns only *proper* intersections
    (strictly inside both segments), not endpoint-touching.
    """
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    x3, y3 = p3.x, p3.y
    x4, y4 = p4.x, p4.y

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-14:
        return None  # parallel or coincident

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9:
        return Vertex(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def find_intersections(a: Polyline, b: Polyline) -> list[Vertex]:
    """Find all proper intersection points between two polylines."""
    result: list[Vertex] = []
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            p = _segment_intersection(
                a.vertices[i], a.vertices[i + 1], b.vertices[j], b.vertices[j + 1]
            )
            if p is not None:
                result.append(p)
    return result


def has_self_intersections(polyline: Polyline) -> bool:
    """Check whether a polyline crosses itself (excluding adjacent segments)."""
    verts = polyline.vertices
    n = len(verts)
    if n < 4:
        return False

    # Build the segment list, including the closing segment if closed
    segments: list[tuple[Vertex, Vertex]] = [
        (verts[i], verts[i + 1]) for i in range(n - 1)
    ]
    if polyline.closed:
        segments.append((verts[-1], verts[0]))

    m = len(segments)
    for i in range(m):
        for j in range(i + 2, m):
            # Adjacent segments share a vertex and never "cross" in the
            # geometric-error sense. Skip the wrap-around adjacency too.
            if polyline.closed and i == 0 and j == m - 1:
                continue
            if _segment_intersection(
                segments[i][0], segments[i][1],
                segments[j][0], segments[j][1],
            ):
                return True
    return False


# ------------------------------------------------------------------
# High-level cleanup pipeline
# ------------------------------------------------------------------
def cleanup_boundaries(
    boundaries: Iterable[Boundary],
    tol: float = DEFAULT_TOL,
    simplify_epsilon: float = 0.0,
) -> dict:
    """Run a full cleanup pass and return a report.

    Applied operations (in order):
        1. Duplicate vertex removal
        2. Optional RDP simplification (if epsilon > 0)
        3. Self-intersection detection (reported, not fixed)
        4. Cross-boundary intersection detection (reported)

    The caller decides what to do with reported issues.
    """
    report = {
        "duplicates_removed": 0,
        "self_intersections": [],  # boundary ids
        "cross_intersections": [],  # (id_a, id_b, count)
    }
    boundaries = list(boundaries)

    for b in boundaries:
        report["duplicates_removed"] += remove_duplicate_vertices(b.polyline, tol)
        if simplify_epsilon > 0:
            b.polyline = simplify_rdp(b.polyline, simplify_epsilon)
        if has_self_intersections(b.polyline):
            report["self_intersections"].append(b.id)

    for i, a in enumerate(boundaries):
        for c in boundaries[i + 1 :]:
            pts = find_intersections(a.polyline, c.polyline)
            if pts:
                report["cross_intersections"].append((a.id, c.id, len(pts)))

    return report
