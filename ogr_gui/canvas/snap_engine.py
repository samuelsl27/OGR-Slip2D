# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Snap / Ortho / OSnap engine for the 2D canvas (v0.1.3).

Converts raw cursor positions (model coordinates) into *snapped* positions
according to the user-enabled constraints. Based on the Slide-style UX
described in the specification:

    SNAP (F9) — snap to vertices, line segments, grid points, and OSnap
                extension lines.
    ORTHO (F8) — while drawing, constrain the in-progress segment to
                exactly horizontal or vertical relative to the reference
                (last-drawn) point.
    OSNAP (F3) — generate temporary extension lines at vertices and edges
                of nearby entities. If SNAP is also on, you can snap to
                these extension lines.

The engine returns not only a snapped point but a :class:`SnapResult`
whose ``kind`` tells the canvas what visual cue to show (circle for
vertex-snap, X for line-snap, dot for grid-snap). It also returns the
osnap extension lines so the canvas can render them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional, Tuple

from ogr_core.geometry import Boundary, Vertex


# ----------------------------------------------------------------------
class SnapKind(Enum):
    """Visual cue to display for a snap hit."""
    NONE = "none"
    VERTEX = "vertex"           # circle around vertex
    LINE = "line"               # X on line segment
    GRID = "grid"               # small circle at grid node
    ENDPOINT = "endpoint"       # square at endpoint
    EXTENSION = "extension"     # along an osnap extension line
    ORTHO_H = "ortho_h"
    ORTHO_V = "ortho_v"


@dataclass
class SnapResult:
    """The outcome of resolving the cursor against the snap engine."""
    point: Vertex
    kind: SnapKind = SnapKind.NONE
    # For OSNAP: list of (p1, p2) extension lines to render as dashed guides
    extension_lines: List[Tuple[Vertex, Vertex]] = field(default_factory=list)
    # True if ortho was active — the canvas can show a corner glyph
    ortho_active: bool = False


# ----------------------------------------------------------------------
@dataclass
class SnapSettings:
    snap: bool = True
    ortho: bool = False
    osnap: bool = False

    # Tolerances in pixels (converted to world units via pixels_per_unit)
    vertex_tolerance_px: float = 12.0
    line_tolerance_px: float = 10.0
    grid_tolerance_px: float = 8.0
    extension_tolerance_px: float = 8.0
    ortho_snap_angle_deg: float = 5.0
    """ORTHO snaps to axis when within ±this many degrees of H/V."""

    # Grid spacing — auto-updated by the canvas from the visible scale
    grid_h: float = 1.0
    grid_v: float = 1.0


# ======================================================================
class SnapEngine:
    """Resolves a cursor position under the active constraints.

    Usage from the canvas:

        engine = SnapEngine(settings)
        engine.set_reference(last_vertex)   # for ORTHO lock
        result = engine.resolve(cursor, boundaries, pixels_per_unit)
        # result.point → snapped coordinate
        # result.kind  → what glyph to render
        # result.extension_lines → OSNAP dashed lines
    """

    def __init__(self, settings: Optional[SnapSettings] = None) -> None:
        self.settings = settings or SnapSettings()
        self.reference: Optional[Vertex] = None

    # ------------------------------------------------------------------
    def set_reference(self, v: Optional[Vertex]) -> None:
        self.reference = v

    # ------------------------------------------------------------------
    def resolve(
        self,
        cursor: Vertex,
        boundaries: Iterable[Boundary] = (),
        pixels_per_unit: float = 1.0,
    ) -> SnapResult:
        """Apply the active constraints and return a :class:`SnapResult`."""
        s = self.settings
        ppu = max(pixels_per_unit, 1e-9)
        boundaries = list(boundaries)

        # 1. OSNAP extension lines are always computed if enabled (for
        #    the visual cue), but only used for snapping when SNAP is on.
        extension_lines: List[Tuple[Vertex, Vertex]] = []
        if s.osnap and boundaries:
            extension_lines = self._compute_extensions(cursor, boundaries,
                                                       s.extension_tolerance_px / ppu)

        # 2. Vertex snap (highest precedence)
        if s.snap:
            tol = s.vertex_tolerance_px / ppu
            vx = self._nearest_vertex(cursor, boundaries, tol)
            if vx is not None:
                p = vx
                if s.ortho and self.reference is not None:
                    p = self._apply_ortho(p)
                return SnapResult(point=p, kind=SnapKind.VERTEX,
                                  extension_lines=extension_lines,
                                  ortho_active=s.ortho)

        # 3. Extension-line snap (OSNAP + SNAP)
        if s.snap and extension_lines:
            tol = s.line_tolerance_px / ppu
            proj = self._nearest_on_extensions(cursor, extension_lines, tol)
            if proj is not None:
                return SnapResult(point=proj, kind=SnapKind.EXTENSION,
                                  extension_lines=extension_lines,
                                  ortho_active=s.ortho)

        # 4. Line-segment snap
        if s.snap:
            tol = s.line_tolerance_px / ppu
            proj = self._nearest_on_segment(cursor, boundaries, tol)
            if proj is not None:
                p = proj
                if s.ortho and self.reference is not None:
                    # Intersection of ortho axis with the segment, if any
                    p2 = self._ortho_then_project(cursor, boundaries, tol)
                    if p2 is not None:
                        p = p2
                return SnapResult(point=p, kind=SnapKind.LINE,
                                  extension_lines=extension_lines,
                                  ortho_active=s.ortho)

        # 5. Grid snap
        if s.snap:
            tol = s.grid_tolerance_px / ppu
            gx = s.grid_h if s.grid_h > 0 else 1.0
            gy = s.grid_v if s.grid_v > 0 else 1.0
            rx = round(cursor.x / gx) * gx
            ry = round(cursor.y / gy) * gy
            d = math.hypot(cursor.x - rx, cursor.y - ry)
            if d < tol:
                p = Vertex(rx, ry)
                if s.ortho and self.reference is not None:
                    p = self._apply_ortho(p)
                return SnapResult(point=p, kind=SnapKind.GRID,
                                  extension_lines=extension_lines,
                                  ortho_active=s.ortho)

        # 6. No snap. Still apply ortho if active.
        if s.ortho and self.reference is not None:
            snapped = self._apply_ortho(cursor)
            kind = (SnapKind.ORTHO_H if snapped.y == self.reference.y
                    else SnapKind.ORTHO_V)
            return SnapResult(point=snapped, kind=kind,
                              extension_lines=extension_lines,
                              ortho_active=True)

        return SnapResult(point=cursor, kind=SnapKind.NONE,
                          extension_lines=extension_lines)

    # ==================================================================
    # Internal helpers
    # ==================================================================
    def _apply_ortho(self, p: Vertex) -> Vertex:
        """Snap ``p`` to the horizontal or vertical axis through the
        reference point, whichever is closer."""
        if self.reference is None:
            return p
        dx = abs(p.x - self.reference.x)
        dy = abs(p.y - self.reference.y)
        if dx >= dy:
            return Vertex(p.x, self.reference.y)
        return Vertex(self.reference.x, p.y)

    def _ortho_then_project(
        self, cursor: Vertex, boundaries: Iterable[Boundary], tol: float
    ) -> Optional[Vertex]:
        """Try to find a line segment that intersects the ortho axis;
        snap exactly to that intersection."""
        if self.reference is None:
            return None
        r = self.reference
        # Candidate axis: horizontal or vertical
        dx = abs(cursor.x - r.x)
        dy = abs(cursor.y - r.y)
        horizontal = dx >= dy
        axis_y = r.y
        axis_x = r.x

        best: Optional[Vertex] = None
        best_dist = tol
        for b in boundaries:
            verts = b.polyline.vertices
            n = len(verts)
            if n < 2:
                continue
            seg_count = n if b.polyline.closed else n - 1
            for i in range(seg_count):
                a = verts[i]
                c = verts[(i + 1) % n]
                if horizontal:
                    # Axis is y = axis_y. Intersect with segment a→c
                    if (a.y - axis_y) * (c.y - axis_y) > 0:
                        continue
                    if abs(c.y - a.y) < 1e-12:
                        continue
                    t = (axis_y - a.y) / (c.y - a.y)
                    x = a.x + t * (c.x - a.x)
                    d = abs(cursor.x - x)
                    if d < best_dist:
                        best_dist = d
                        best = Vertex(x, axis_y)
                else:
                    if (a.x - axis_x) * (c.x - axis_x) > 0:
                        continue
                    if abs(c.x - a.x) < 1e-12:
                        continue
                    t = (axis_x - a.x) / (c.x - a.x)
                    y = a.y + t * (c.y - a.y)
                    d = abs(cursor.y - y)
                    if d < best_dist:
                        best_dist = d
                        best = Vertex(axis_x, y)
        return best

    def _nearest_vertex(
        self, cursor: Vertex, boundaries: Iterable[Boundary], tol: float
    ) -> Optional[Vertex]:
        best: Optional[Vertex] = None
        best_d = tol
        for b in boundaries:
            for v in b.polyline.vertices:
                d = math.hypot(v.x - cursor.x, v.y - cursor.y)
                if d < best_d:
                    best_d = d
                    best = v
        return best

    def _nearest_on_segment(
        self, cursor: Vertex, boundaries: Iterable[Boundary], tol: float
    ) -> Optional[Vertex]:
        best: Optional[Vertex] = None
        best_d = tol
        for b in boundaries:
            verts = b.polyline.vertices
            n = len(verts)
            if n < 2:
                continue
            seg_count = n if b.polyline.closed else n - 1
            for i in range(seg_count):
                a = verts[i]
                c = verts[(i + 1) % n]
                proj, d = _point_to_segment(cursor, a, c)
                if d < best_d:
                    best_d = d
                    best = proj
        return best

    def _compute_extensions(
        self, cursor: Vertex, boundaries: Iterable[Boundary], near_tol: float
    ) -> List[Tuple[Vertex, Vertex]]:
        """Build OSNAP extension lines (horizontal and vertical) at any
        vertex near the cursor.

        We only build extensions if the cursor is within ``near_tol``
        units of a vertex (so the screen isn't cluttered).
        """
        lines: List[Tuple[Vertex, Vertex]] = []
        seen: set[Tuple[float, float]] = set()
        LENGTH = 1e6  # effectively infinite relative to the model
        for b in boundaries:
            for v in b.polyline.vertices:
                d = math.hypot(v.x - cursor.x, v.y - cursor.y)
                if d > near_tol * 3:
                    continue
                key = (round(v.x, 6), round(v.y, 6))
                if key in seen:
                    continue
                seen.add(key)
                # Horizontal extension
                lines.append((Vertex(v.x - LENGTH, v.y),
                              Vertex(v.x + LENGTH, v.y)))
                # Vertical extension
                lines.append((Vertex(v.x, v.y - LENGTH),
                              Vertex(v.x, v.y + LENGTH)))
        return lines

    def _nearest_on_extensions(
        self,
        cursor: Vertex,
        lines: List[Tuple[Vertex, Vertex]],
        tol: float,
    ) -> Optional[Vertex]:
        best: Optional[Vertex] = None
        best_d = tol
        for a, c in lines:
            proj, d = _point_to_segment(cursor, a, c)
            if d < best_d:
                best_d = d
                best = proj
        return best


# ----------------------------------------------------------------------
def _point_to_segment(p: Vertex, a: Vertex, b: Vertex) -> Tuple[Vertex, float]:
    """Project ``p`` onto segment a→b; return (projection, distance)."""
    dx, dy = b.x - a.x, b.y - a.y
    if dx == 0 and dy == 0:
        return a, math.hypot(p.x - a.x, p.y - a.y)
    t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj = Vertex(a.x + t * dx, a.y + t * dy)
    return proj, math.hypot(p.x - proj.x, p.y - proj.y)


# ----------------------------------------------------------------------
def nice_step(target_world: float) -> float:
    """Round to a 1-2-5-10 decade step (for ruler / grid auto-spacing)."""
    if target_world <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(target_world))
    normalized = target_world / mag
    if normalized < 1.5:
        step = 1.0
    elif normalized < 3.5:
        step = 2.0
    elif normalized < 7.5:
        step = 5.0
    else:
        step = 10.0
    return step * mag
