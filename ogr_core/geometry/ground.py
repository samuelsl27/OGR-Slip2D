# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The ground surface of an external boundary — ONE definition, for everybody.

The ground surface is the upper envelope of the closed external polygon:
for each x inside the model, the highest point of the boundary above it.
Every slip surface must daylight on it, the slicer measures slice heights
from it, and the canvas draws tension-crack zones against it.

Until v0.1.84 this concept had **three** independent implementations and
two of them were wrong:

* ``slicer._ground_surface_from_external`` grouped the boundary VERTICES
  by x and kept the highest y of each group. That is only correct when
  every x of a bottom vertex is also the x of a top vertex. On the Ej_2
  reference model the bottom edge carries a vertex at ``(0, 0)`` that no
  top vertex shares, so ``(0, 0)`` was published as ground and the flat
  terrain at y = 30 acquired a 30 m ravine. The critical circle then
  "daylighted" at x ≈ 0.39 on the floor of the model and came out at
  FoS = 0.79 instead of ≈ 1.16.
* ``canvas_view._ground_polyline`` kept the vertices with
  ``y >= (y_min + y_max) / 2``. On the same model that drops every vertex
  of the lower half of the slope and returns only the right-hand quarter
  of the profile.
* ``PathSearch._ground_profile`` walked the EDGES and was right; it is the
  one this module generalises.

Sampling at vertex abscissae alone is not enough either: where two edges
overlap in projection the upper envelope can change edge at an x that is
nobody's vertex (a re-entrant or overhanging boundary). Those crossing
abscissae are added here, so the returned polyline is the exact envelope
for any simple polygon, not just for monotone slope profiles.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Optional

from .primitives import Polyline, Vertex

# Two abscissae closer than this are the same breakpoint. Relative to the
# horizontal extent of the model, never absolute: the same boundary
# expressed in millimetres and in metres must produce the same envelope.
_X_MERGE_REL = 1e-9


def _edges(vertices: list[Vertex]) -> list[tuple[Vertex, Vertex]]:
    """The closed polygon's edges, wrapping the last vertex to the first."""
    n = len(vertices)
    return [(vertices[i], vertices[(i + 1) % n]) for i in range(n)]


def _y_on_edge(a: Vertex, b: Vertex, x: float, tol: float) -> Optional[float]:
    """Height of edge ``a→b`` above ``x``, or None if it does not span x.

    A vertical edge contributes its top end, which is what makes a vertical
    cut face part of the ground surface at that single abscissa.
    """
    if a.x == b.x:
        return max(a.y, b.y) if abs(x - a.x) <= tol else None
    lo, hi = (a.x, b.x) if a.x < b.x else (b.x, a.x)
    if x < lo - tol or x > hi + tol:
        return None
    t = (x - a.x) / (b.x - a.x)
    return a.y + t * (b.y - a.y)


def upper_y_at(vertices: list[Vertex], x: float,
               tol: float = 0.0) -> Optional[float]:
    """Highest point of the closed polygon above ``x``, or None.

    This is the primitive the whole module is built on: the envelope is
    the pointwise maximum over the edges, which is what makes it immune to
    where the user happened to place vertices on the bottom edge.
    """
    best: Optional[float] = None
    for a, b in _edges(vertices):
        y = _y_on_edge(a, b, x, tol)
        if y is None:
            continue
        best = y if best is None else max(best, y)
    return best


def _breakpoints(vertices: list[Vertex], tol: float) -> list[float]:
    """Every abscissa where the upper envelope can change slope.

    Vertex abscissae, plus the abscissae where two edges cross in
    projection. Without the latter an overhanging or re-entrant boundary
    is joined by a straight line across a corner the envelope actually
    turns at.
    """
    xs = [v.x for v in vertices]

    edges = _edges(vertices)
    for i in range(len(edges)):
        a1, b1 = edges[i]
        if a1.x == b1.x:
            continue
        m1 = (b1.y - a1.y) / (b1.x - a1.x)
        c1 = a1.y - m1 * a1.x
        for j in range(i + 1, len(edges)):
            a2, b2 = edges[j]
            if a2.x == b2.x:
                continue
            m2 = (b2.y - a2.y) / (b2.x - a2.x)
            if abs(m1 - m2) < 1e-12:
                continue
            c2 = a2.y - m2 * a2.x
            x = (c2 - c1) / (m1 - m2)
            lo1, hi1 = (a1.x, b1.x) if a1.x < b1.x else (b1.x, a1.x)
            lo2, hi2 = (a2.x, b2.x) if a2.x < b2.x else (b2.x, a2.x)
            if lo1 - tol <= x <= hi1 + tol and lo2 - tol <= x <= hi2 + tol:
                xs.append(x)

    xs.sort()
    out: list[float] = []
    for x in xs:
        if not out or x - out[-1] > tol:
            out.append(x)
    return out


@lru_cache(maxsize=64)
def _envelope(key: tuple[tuple[float, float], ...]
              ) -> tuple[tuple[float, float], ...]:
    """The envelope of an immutable vertex tuple, memoised.

    The slicer asks for the ground surface once per slip surface, so a
    Grid Search asks for it thousands of times for one unchanging
    boundary. Computing it every time is affordable for the nine vertices
    of a hand-drawn slope (100 us) and is not for a surveyed or
    DXF-imported profile: the edge-crossing scan is quadratic in the
    vertex count, so a 101-vertex boundary costs 10.5 ms a call — 51 s
    over the 4840 circles of the reference grid, spent entirely on
    recomputing the same answer.

    Keyed on the coordinates rather than on the object, because the
    boundary is edited in place by the modeller and an identity key would
    hand back a stale profile after every vertex drag.
    """
    vertices = [Vertex(x, y) for x, y in key]
    xs_all = [v.x for v in vertices]
    span = max(xs_all) - min(xs_all)
    tol = _X_MERGE_REL * span if span > 0 else _X_MERGE_REL

    out: list[tuple[float, float]] = []
    for x in _breakpoints(vertices, tol):
        y = upper_y_at(vertices, x, tol)
        if y is not None:
            out.append((x, y))
    return tuple(out)


def ground_surface(external) -> Polyline:
    """Upper envelope of an external boundary, left to right.

    ``external`` may be a :class:`~ogr_core.geometry.Boundary`, a
    :class:`~ogr_core.geometry.Polyline`, or a plain sequence of
    vertices — the three forms all occur at the call sites this replaces.

    Returns an open polyline. An external boundary with fewer than three
    vertices has no interior and yields its own vertices sorted by x.
    """
    vertices = _as_vertices(external)
    if len(vertices) < 3:
        return Polyline(vertices=sorted(vertices, key=lambda v: v.x))
    key = tuple((v.x, v.y) for v in vertices)
    return Polyline(vertices=[Vertex(x, y) for x, y in _envelope(key)])


def _as_vertices(external) -> list[Vertex]:
    """Accept a Boundary, a Polyline or a raw vertex sequence."""
    polyline = getattr(external, "polyline", None)
    if polyline is not None:
        return list(polyline.vertices)
    verts = getattr(external, "vertices", None)
    if verts is not None:
        return list(verts)
    if isinstance(external, Iterable):
        return list(external)
    return []
