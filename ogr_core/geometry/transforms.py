# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Affine transformations & advanced geometric operations on boundaries.

Adds the following to the geometry core:
    - translate(b, dx, dy)
    - rotate(b, pivot, angle_deg)
    - scale(b, pivot, sx, sy)
    - offset_polygon(polyline, distance)   (expand/shrink)
    - convert_boundary(b, new_type)

All transformations return a *new* Boundary (never mutate in place),
making them safe to feed into the Command/Undo stack.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from copy import deepcopy
from typing import Iterable

from .boundary import Boundary
from .boundary_type import BoundaryType
from .primitives import Polyline, Vertex


# ----------------------------------------------------------------------
# Basic affine transformations
# ----------------------------------------------------------------------
def translate(b: Boundary, dx: float, dy: float) -> Boundary:
    """Return a copy of ``b`` shifted by (dx, dy)."""
    new = deepcopy(b)
    new.polyline.vertices = [Vertex(v.x + dx, v.y + dy) for v in b.polyline.vertices]
    return new


def rotate(b: Boundary, pivot: Vertex, angle_deg: float) -> Boundary:
    """Return a copy of ``b`` rotated CCW by ``angle_deg`` around ``pivot``."""
    new = deepcopy(b)
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    new.polyline.vertices = [
        Vertex(
            pivot.x + (v.x - pivot.x) * c - (v.y - pivot.y) * s,
            pivot.y + (v.x - pivot.x) * s + (v.y - pivot.y) * c,
        )
        for v in b.polyline.vertices
    ]
    return new


def scale(b: Boundary, pivot: Vertex, sx: float, sy: float | None = None) -> Boundary:
    """Return a copy of ``b`` scaled about ``pivot``.

    If ``sy`` is omitted, uniform scaling (sy = sx) is applied.
    """
    if sy is None:
        sy = sx
    new = deepcopy(b)
    new.polyline.vertices = [
        Vertex(
            pivot.x + (v.x - pivot.x) * sx,
            pivot.y + (v.y - pivot.y) * sy,
        )
        for v in b.polyline.vertices
    ]
    return new


# ----------------------------------------------------------------------
# Polygon offset (expand / shrink)
# ----------------------------------------------------------------------
def offset_polygon(polyline: Polyline, distance: float) -> Polyline:
    """Inward (negative ``distance``) or outward (positive) polygon offset.

    Implementation: compute the inward/outward unit normal at each edge,
    then intersect consecutive offset edges. Works for convex and mildly
    concave CCW polygons — complex cases may self-intersect and should
    be filtered by Geometry Cleanup afterwards.
    """
    if not polyline.closed or len(polyline) < 3:
        raise ValueError("offset_polygon requires a closed polygon with ≥3 vertices")

    verts = list(polyline.vertices)
    # Enforce CCW so that "outward" (positive distance) means expanding
    poly = Polyline(vertices=verts, closed=True)
    poly.ensure_ccw()
    verts = poly.vertices

    n = len(verts)
    # Edges with outward normals (CCW → normal points to the right of edge direction)
    normals: list[tuple[float, float]] = []
    for i in range(n):
        a = verts[i]
        b = verts[(i + 1) % n]
        dx, dy = b.x - a.x, b.y - a.y
        L = math.hypot(dx, dy) or 1.0
        # For CCW, "outward" (left of travel direction when walking the boundary)
        # is (-dy/L, dx/L). But for standard "expand", we want the normal to
        # point *away* from the interior — that's (-dy/L, dx/L) for CCW polygons.
        # Since the interior is on the LEFT for CCW, outward is RIGHT = (dy, -dx).
        normals.append((dy / L, -dx / L))

    # Offset each edge by distance along its outward normal
    offset_lines: list[tuple[Vertex, Vertex]] = []
    for i in range(n):
        a = verts[i]
        b = verts[(i + 1) % n]
        nx, ny = normals[i]
        offset_lines.append((
            Vertex(a.x + distance * nx, a.y + distance * ny),
            Vertex(b.x + distance * nx, b.y + distance * ny),
        ))

    # Intersect consecutive offset edges to reconstruct vertices
    new_verts: list[Vertex] = []
    for i in range(n):
        p1, p2 = offset_lines[i]
        p3, p4 = offset_lines[(i + 1) % n]
        inter = _line_intersection(p1, p2, p3, p4)
        if inter is None:
            # Parallel → keep the endpoint
            new_verts.append(p2)
        else:
            new_verts.append(inter)

    return Polyline(vertices=new_verts, closed=True)


def _line_intersection(
    p1: Vertex, p2: Vertex, p3: Vertex, p4: Vertex
) -> Vertex | None:
    """Infinite-line intersection (unbounded). Returns None if parallel."""
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    x3, y3 = p3.x, p3.y
    x4, y4 = p4.x, p4.y
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-14:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return Vertex(x1 + t * (x2 - x1), y1 + t * (y2 - y1))


# ----------------------------------------------------------------------
# Change slope angle — v0.1.198: moved to ``slope_angle.change_slope_angle``.
# The function that lived here rotated the WHOLE boundary about a pivot
# (the base and the crest tilted with the face) and its sense depended on
# which way the slope faced; it is gone rather than kept beside the new one.
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Convert boundary type
# ----------------------------------------------------------------------
def convert_boundary(boundary: Boundary, new_type: BoundaryType) -> Boundary:
    """Return a copy of ``boundary`` with a new :class:`BoundaryType`.

    Resets the type-dependent colour to the new type's default if the
    current colour matched the old default (so user-picked colours are
    preserved).
    """
    new = deepcopy(boundary)
    old_default = boundary.btype.default_color
    if boundary.color == old_default:
        new.color = new_type.default_color
    new.btype = new_type
    # If switching away from a closed polygon type, respect the new type
    if new_type in (BoundaryType.WATER_TABLE, BoundaryType.PIEZOMETRIC,
                    BoundaryType.DRAWDOWN, BoundaryType.TENSION_CRACK):
        new.polyline.closed = False
        new.material_id = None
    elif new_type is BoundaryType.ANISOTROPIC_SURFACE:
        # v0.1.126 — open, and the material is DROPPED. A weak layer keeps
        # its material because that is where its strength comes from; an
        # anisotropic surface has no strength, and the material that reads
        # it points AT it rather than the other way round, so carrying one
        # here would be a link in the wrong direction.
        new.polyline.closed = False
        new.material_id = None
    elif new_type is BoundaryType.WEAK_LAYER:
        # v0.1.121 — open like the hydraulic lines, but the material is KEPT:
        # it is where a weak layer's strength comes from, so converting a
        # material boundary into a joint hands it a sensible one instead of
        # silently making it strengthless.
        new.polyline.closed = False
    elif new_type == BoundaryType.MATERIAL:
        # v0.1.197 — a material boundary is open (a layer edge) OR closed
        # (a lens, a hole of the region around it); the polyline keeps what
        # it was. This used to force ``closed = True``, so converting an
        # open water table into a material boundary joined its two ends
        # with a chord across the model.
        pass
    new.name = new_type.display_name
    return new


# ----------------------------------------------------------------------
# Batch apply (for selection-based tools)
# ----------------------------------------------------------------------
def apply_to_many(
    boundaries: Iterable[Boundary],
    transform,
    *args,
    **kwargs,
) -> list[Boundary]:
    """Apply the same transform to a list of boundaries."""
    return [transform(b, *args, **kwargs) for b in boundaries]
