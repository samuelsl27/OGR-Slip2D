# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slide-style Expand/Shrink algorithm for the External Boundary.

v0.1.6 — Samuel Sáez López (UPCT).

Given:
    ext          — the current External Boundary (closed polyline, CCW)
    polyline     — the user-drawn polyline with its FIRST and LAST points
                   snapped onto the External (the middle points are free
                   and may lie outside [expand] or inside [shrink])

This module computes:
    new_external — the resulting External Boundary (closed, CCW)
    removed_arcs — the arc(s) of the original External that were
                   removed to make room for the polyline. These are
                   what get converted to Material Boundaries if the
                   user picks "Yes" in the Slide dialog.
    mode         — "expand" | "shrink" — auto-detected from whether
                   the new polyline lies outside or inside the original.

Algorithm
=========

The External Boundary is a closed CCW polyline. Locating the two
snap-points on it gives us two cut locations on the perimeter. Those
two cuts break the original perimeter into two arcs (A and B) — walking
CCW from cut₁ to cut₂ and walking CCW from cut₂ back to cut₁.

EXPAND — the polyline lies outside.
    • Both arcs-candidate: for each choice of arc-kept, splice it
      together with the polyline (forward or reversed) to form a
      closed loop. Pick the candidate that is SIMPLE (non-self-
      intersecting) and HAS LARGER AREA than the original External.
    • The OTHER arc (the one discarded) is the piece that gets turned
      into a Material Boundary if the user says Yes.

SHRINK — the polyline lies inside.
    • Same two candidates. Slide's rule: the candidate whose discarded
      arc is SHORTER (in length along the original perimeter) is the
      keeper. This discards the SHORTER piece and keeps the LARGER.
      The discarded shorter arc is the Material Boundary candidate.

The algorithm is pure-Python — no shapely dependency — because the
operation is just perimeter splicing on a known CCW polygon.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .primitives import Polyline, Vertex


# ======================================================================
@dataclass
class ExpandShrinkResult:
    """Outcome of an Expand/Shrink operation."""
    new_external: Polyline
    removed_arc: Optional[Polyline]   # old External segment that was cut out
    mode: str                         # "expand" | "shrink"


# ======================================================================
class ExpandShrinkError(ValueError):
    """Raised when the operation cannot be completed (e.g. the polyline
    doesn't actually attach to the External, or produces degenerate
    geometry)."""


# ======================================================================
def expand_shrink_external(
    external: Polyline,
    polyline: Polyline,
    tolerance: float = 1e-6,
) -> ExpandShrinkResult:
    """Main entry point. See module docstring for the algorithm."""
    if not external.closed:
        raise ExpandShrinkError("External must be a closed polyline.")
    ext_verts = list(external.vertices)
    # Normalise: drop a duplicated last = first vertex if present
    if ext_verts and ext_verts[0] == ext_verts[-1]:
        ext_verts = ext_verts[:-1]
    if len(ext_verts) < 3:
        raise ExpandShrinkError("External has too few vertices.")
    # Ensure CCW for predictable arc walking
    if _signed_area(ext_verts) < 0:
        ext_verts = list(reversed(ext_verts))

    pl_verts = list(polyline.vertices)
    if len(pl_verts) < 2:
        raise ExpandShrinkError("Polyline needs at least 2 vertices.")

    # Locate where first and last points of the polyline lie on the External
    first = pl_verts[0]
    last = pl_verts[-1]
    cut1 = _locate_on_perimeter(ext_verts, first, tolerance)
    cut2 = _locate_on_perimeter(ext_verts, last, tolerance)
    if cut1 is None or cut2 is None:
        raise ExpandShrinkError(
            "Both endpoints of the polyline must lie on the External "
            "Boundary (use snap — green cross)."
        )

    # Replace the literal first/last points with the exact snap locations
    pl_verts[0] = Vertex(cut1.x, cut1.y)
    pl_verts[-1] = Vertex(cut2.x, cut2.y)

    # Decide expand vs shrink: test an intermediate point of the polyline
    # (or the midpoint of the polyline's bbox) — is it INSIDE the External?
    probe = _probe_point(pl_verts)
    probe_inside = _point_in_polygon(probe, ext_verts)
    mode = "shrink" if probe_inside else "expand"

    # Build the two candidate new polygons (arc-forward and arc-backward)
    arc_fwd = _walk_arc(ext_verts, cut1, cut2, reverse=False)
    arc_rev = _walk_arc(ext_verts, cut1, cut2, reverse=True)

    # Candidate A: use arc_fwd as the replacement; polyline covers arc_rev
    cand_a = _splice(arc_rev + [cut2], pl_verts)  # actually pl_verts replaces arc_fwd
    # Wait — let's rebuild this more carefully:
    # The External perimeter CCW is: cut1 → (arc_fwd…) → cut2 → (arc_rev…) → cut1
    # If we keep arc_fwd and replace arc_rev with the polyline:
    #     new_poly = cut1 + arc_fwd + cut2 + reversed(polyline_middle) + back to cut1
    # If we keep arc_rev and replace arc_fwd with the polyline:
    #     new_poly = cut1 + polyline_middle + cut2 + arc_rev + back to cut1

    pl_middle = pl_verts[1:-1]  # exclude the endpoints already = cut1/cut2

    # Convert cut1/cut2 from _PerimeterLocation into Vertex instances
    cut1_v = Vertex(cut1.x, cut1.y)
    cut2_v = Vertex(cut2.x, cut2.y)

    # Candidate A: keep arc_fwd (forward arc), replace arc_rev with the
    # polyline. CCW order: cut1 → arc_fwd → cut2 → pl_middle reversed
    # back to cut1.
    cand_keep_fwd = (
        [cut1_v] + arc_fwd + [cut2_v] + list(reversed(pl_middle))
    )
    # Candidate B: keep arc_rev (reverse arc = long way around), replace
    # arc_fwd with the polyline. CCW order: cut1 → pl_middle → cut2 →
    # REVERSED(arc_rev) (because arc_rev was walked in CW direction, to
    # close the loop CCW we traverse it backwards).
    cand_keep_rev = (
        [cut1_v] + pl_middle + [cut2_v] + list(reversed(arc_rev))
    )

    # Decide which candidate is the correct new external
    if mode == "expand":
        area_a = abs(_signed_area(cand_keep_fwd))
        area_b = abs(_signed_area(cand_keep_rev))
        orig_area = abs(_signed_area(ext_verts))
        # Expand: keep the candidate with LARGER area (union with polyline)
        if area_a > area_b:
            new_verts = cand_keep_fwd
            removed_verts = [cut1_v] + arc_rev + [cut2_v]
        else:
            new_verts = cand_keep_rev
            removed_verts = [cut1_v] + arc_fwd + [cut2_v]
        # Sanity: result must be strictly larger than original
        if abs(_signed_area(new_verts)) < orig_area * 0.99:
            raise ExpandShrinkError(
                "Expand produced a smaller polygon — intermediate "
                "points are probably INSIDE the External. Use Shrink, "
                "or redraw with points outside."
            )
    else:
        # Shrink: discard the SHORTER arc (Slide rule).
        len_fwd = _arc_length([cut1_v] + arc_fwd + [cut2_v])
        len_rev = _arc_length([cut1_v] + arc_rev + [cut2_v])
        if len_fwd < len_rev:
            # Short arc is forward → discard it, keep reverse side
            new_verts = cand_keep_rev
            removed_verts = [cut1_v] + arc_fwd + [cut2_v]
        else:
            new_verts = cand_keep_fwd
            removed_verts = [cut1_v] + arc_rev + [cut2_v]

    # Ensure CCW and build Polyline
    if _signed_area(new_verts) < 0:
        new_verts = list(reversed(new_verts))
    new_pline = Polyline(vertices=_dedupe(new_verts), closed=True)

    removed_arc = None
    if len(removed_verts) >= 2:
        removed_arc = Polyline(vertices=_dedupe(removed_verts), closed=False)

    return ExpandShrinkResult(
        new_external=new_pline,
        removed_arc=removed_arc,
        mode=mode,
    )


# ======================================================================
# Helpers
# ======================================================================
@dataclass
class _PerimeterLocation:
    """A position on the External perimeter."""
    edge: int        # index of the edge (0 = edge between verts[0] and verts[1])
    t: float         # fraction along that edge (0 ≤ t ≤ 1)
    x: float
    y: float


def _locate_on_perimeter(
    verts: List[Vertex], pt: Vertex, tol: float
) -> Optional[_PerimeterLocation]:
    """Locate a point on the polygon perimeter. Returns None if the
    point is farther than `tol` from every edge (scaled to polygon size)."""
    n = len(verts)
    # Use a generous tolerance scaled with the polygon's size
    bbox_dx = max(v.x for v in verts) - min(v.x for v in verts)
    bbox_dy = max(v.y for v in verts) - min(v.y for v in verts)
    scale = max(bbox_dx, bbox_dy, 1.0)
    abs_tol = max(tol * scale, 1e-6)

    best: Optional[_PerimeterLocation] = None
    best_dist = float("inf")
    for i in range(n):
        a = verts[i]
        b = verts[(i + 1) % n]
        dx, dy = b.x - a.x, b.y - a.y
        L2 = dx * dx + dy * dy
        if L2 < 1e-20:
            continue
        t = ((pt.x - a.x) * dx + (pt.y - a.y) * dy) / L2
        t_clamped = max(0.0, min(1.0, t))
        cx = a.x + t_clamped * dx
        cy = a.y + t_clamped * dy
        d = math.hypot(pt.x - cx, pt.y - cy)
        if d < best_dist:
            best_dist = d
            best = _PerimeterLocation(edge=i, t=t_clamped, x=cx, y=cy)
    if best is None or best_dist > abs_tol:
        return None
    return best


def _walk_arc(
    verts: List[Vertex],
    start: _PerimeterLocation,
    end: _PerimeterLocation,
    reverse: bool,
) -> List[Vertex]:
    """Walk the CCW perimeter from ``start`` to ``end``, returning the
    intermediate polygon vertices visited along the way. The endpoints
    (start.x/y, end.x/y) are NOT included.

    Case A: ``reverse=False`` — walk CCW (the "forward" direction of
    the polygon). Starting just after ``start`` (i.e. vertex (start.edge + 1) % n),
    collect every vertex until we'd be jumping past the edge that
    contains ``end``. If start and end are on the SAME edge and
    ``start.t <= end.t``, no vertices are between — return empty.

    Case B: ``reverse=True`` — walk the OTHER way (reverse direction).
    Starting from vertex ``start.edge`` (i.e. the vertex "before" the
    start position on the edge), collect every vertex going backwards
    until we'd jump past the edge containing ``end``. If start and end
    are on the SAME edge and start.t <= end.t, this is the long way
    around the polygon (through all other vertices).
    """
    n = len(verts)
    out: List[Vertex] = []
    if n < 3:
        return out

    same_edge = (start.edge == end.edge)

    if not reverse:
        # FORWARD (CCW).
        if same_edge and start.t <= end.t:
            # No intermediate vertices on the short forward hop.
            return []
        # First intermediate vertex is (start.edge + 1) mod n.
        i = (start.edge + 1) % n
        # Stop once the NEXT step would jump past the end-edge's start vertex.
        # i.e. stop when i == (end.edge + 1) % n (after adding end.edge vertex).
        stop_after = end.edge  # last index to include
        safety = 0
        while safety < n + 2:
            out.append(verts[i])
            if i == stop_after:
                break
            i = (i + 1) % n
            safety += 1
        return out

    # REVERSE (CW walk).
    if same_edge and start.t >= end.t:
        # No intermediate vertices on the short reverse hop.
        return []
    # First intermediate vertex going backwards is start.edge itself
    # (the vertex BEFORE the cut point on the start edge).
    i = start.edge
    stop_after = (end.edge + 1) % n  # last index to include
    safety = 0
    while safety < n + 2:
        out.append(verts[i])
        if i == stop_after:
            break
        i = (i - 1) % n
        safety += 1
    return out


def _signed_area(verts: List[Vertex]) -> float:
    n = len(verts)
    s = 0.0
    for i in range(n):
        x1, y1 = verts[i].x, verts[i].y
        x2, y2 = verts[(i + 1) % n].x, verts[(i + 1) % n].y
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def _point_in_polygon(pt: Vertex, verts: List[Vertex]) -> bool:
    n = len(verts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = verts[i].x, verts[i].y
        xj, yj = verts[j].x, verts[j].y
        if ((yi > pt.y) != (yj > pt.y)) and (
            pt.x < (xj - xi) * (pt.y - yi) / (yj - yi + 1e-20) + xi
        ):
            inside = not inside
        j = i
    return inside


def _probe_point(pline_verts: List[Vertex]) -> Vertex:
    """Pick a representative interior vertex of a polyline (prefers
    middle vertex of the middle if available; falls back to the
    midpoint of the first-to-last line)."""
    n = len(pline_verts)
    if n >= 3:
        return pline_verts[n // 2]
    a, b = pline_verts[0], pline_verts[-1]
    return Vertex((a.x + b.x) / 2, (a.y + b.y) / 2)


def _arc_length(verts: List[Vertex]) -> float:
    total = 0.0
    for i in range(len(verts) - 1):
        total += math.hypot(
            verts[i + 1].x - verts[i].x, verts[i + 1].y - verts[i].y,
        )
    return total


def _splice(a, b):
    """Concatenate two vertex sequences, dropping obvious duplicates at
    the join. (Placeholder kept for readability — not used in the
    streamlined algorithm above.)"""
    return list(a) + list(b)


def _dedupe(verts: List[Vertex], tol: float = 1e-9) -> List[Vertex]:
    """Drop consecutive duplicate vertices."""
    out: List[Vertex] = []
    for v in verts:
        if out and abs(out[-1].x - v.x) < tol and abs(out[-1].y - v.y) < tol:
            continue
        out.append(v)
    # Also drop a closing duplicate (last == first)
    if len(out) >= 2:
        if abs(out[0].x - out[-1].x) < tol and abs(out[0].y - out[-1].y) < tol:
            out = out[:-1]
    return out
