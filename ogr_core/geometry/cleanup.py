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
from typing import Iterable, Optional

from .boundary import Boundary
from .primitives import Polyline, Vertex, segments_of

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


def closing_tolerance(polyline: Polyline, rel: float = 1e-6) -> float:
    """``rel`` times the diagonal of ``polyline``'s own bounding box — the
    project's relative tolerance (see :func:`model_tolerance`), for a
    question that only concerns one polyline."""
    vs = polyline.vertices
    if not vs:
        return DEFAULT_TOL
    xs = [v.x for v in vs]
    ys = [v.y for v in vs]
    return max(rel * math.hypot(max(xs) - min(xs), max(ys) - min(ys)),
               1e-12)


def drop_closing_vertex(polyline: Polyline,
                        tol: Optional[float] = None) -> int:
    """A CLOSED polyline stores each vertex once; drop a last vertex that
    repeats the first. Returns how many were dropped.

    v0.1.197 — the closing edge of a closed polyline is implicit
    (``segments_of``, the region builder, the canvas), so a stored copy of
    the first vertex is a zero-length closing edge. The DXF reader put one
    on every imported closed polyline (since v0.1.59), and it was not
    harmless: moving vertex 0 left the copy behind and cut a notch into the
    model (575 m² for 580), a parallel offset turned the zero-length edge
    into a spike, and the canvas drew two handles on one point.

    The tolerance is relative to the polyline (:func:`closing_tolerance`),
    the same one the inspection uses to call a vertex a duplicate. Never
    leaves fewer than three vertices: a ring that would have to go below
    that is left as it is for the caller's own validation to refuse.
    """
    if not polyline.closed:
        return 0
    vs = polyline.vertices
    if tol is None:
        tol = closing_tolerance(polyline)
    dropped = 0
    while len(vs) > 3 and vs[0].distance_to(vs[-1]) <= tol:
        vs.pop()
        dropped += 1
    return dropped


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
    """Find all proper intersection points between two polylines.

    v0.1.197 — the closing edge of a CLOSED polyline counts: it was
    skipped, so a line crossing the External only there was never
    reported (the DXF import's repeated closing vertex happened to hide
    this for imported models).
    """
    result: list[Vertex] = []
    seg_b = list(segments_of(b))
    for p1, p2 in segments_of(a):
        for q1, q2 in seg_b:
            p = _segment_intersection(p1, p2, q1, q2)
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
def model_tolerance(boundaries: Iterable[Boundary], rel: float = 1e-6
                    ) -> float:
    """``rel`` times the diagonal of the boundaries' bounding box.

    v0.1.196 — the project's convention (AGENTS.md): a geometric tolerance
    is RELATIVE to the model, because 1e-6 means something different in a
    model drawn in millimetres and one drawn in metres. The same factor as
    the region snapping in ``regions.py``.
    """
    xs, ys = [], []
    for b in boundaries:
        for v in b.polyline.vertices:
            xs.append(v.x)
            ys.append(v.y)
    if not xs:
        return DEFAULT_TOL
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    return max(rel * diag, 1e-12)


def inspect_boundaries(boundaries: Iterable[Boundary],
                       tol: float | None = None) -> dict:
    """What is wrong with the geometry, WITHOUT changing it.

    v0.1.196 (spec 008, F2). The interface's Geometry Cleanup called
    ``find_intersections`` with one argument (a TypeError it swallowed, so
    crossings were never reported), then ran :func:`cleanup_boundaries` on
    the LIVE boundaries — removing vertices with no undo — and reported
    ``len()`` of the report dictionary as the number of boundaries left,
    which is always 3. This is the read-only half; :func:`cleanup_boundaries`
    stays the one that edits, and the caller wraps it in an undo step.

    ``tol`` defaults to :func:`model_tolerance`.
    """
    boundaries = list(boundaries)
    if tol is None:
        tol = model_tolerance(boundaries)
    rows = []
    for b in boundaries:
        probe = Polyline(vertices=list(b.polyline.vertices),
                         closed=b.polyline.closed)
        dups = remove_duplicate_vertices(probe, tol)
        rows.append({
            "id": b.id,
            "type": b.btype.name.lower(),
            "name": b.name,
            "n_vertices": len(b.polyline.vertices),
            "duplicate_vertices": dups,
            "self_intersects": has_self_intersections(b.polyline),
            "open_external": (b.btype.name == "EXTERNAL"
                              and not b.polyline.closed),
        })
    crossings = []
    for i, a in enumerate(boundaries):
        for c in boundaries[i + 1:]:
            pts = find_intersections(a.polyline, c.polyline)
            if pts:
                crossings.append({"a": a.id, "b": c.id, "count": len(pts)})
    return {"tolerance": tol, "boundaries": rows,
            "cross_intersections": crossings}


def simplify_boundary(b: Boundary, epsilon: float) -> Boundary:
    """A copy of ``b`` simplified by Ramer-Douglas-Peucker (Douglas and
    Peucker, 1973), keeping its ids.

    v0.1.196 — the interface passed a list of tuples to :func:`simplify_rdp`,
    which takes a ``Polyline``, so *Simplify Boundary* raised on every use.
    Refuses (``ValueError``) to leave a closed boundary with fewer than
    three vertices or an open one with fewer than two.
    """
    import dataclasses

    if not epsilon > 0:
        raise ValueError("the simplification tolerance must be positive")
    simplified = simplify_rdp(b.polyline, epsilon)
    need = 3 if b.polyline.closed else 2
    if len(simplified.vertices) < need:
        raise ValueError(
            f"a tolerance of {epsilon:g} leaves {len(simplified.vertices)} "
            f"vertices; this boundary needs at least {need}")
    poly = dataclasses.replace(b.polyline,
                               vertices=list(simplified.vertices))
    return dataclasses.replace(b, polyline=poly)


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
