# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Triangular mesh generator (Phase 1 of the groundwater plan).

Builds a conforming T3 mesh over the material regions produced by
``ogr_core.geometry.regions.build_regions``.

Algorithm
---------
1. **Boundary discretisation.** Every region edge is split into segments
   of approximately ``target_size``. All boundary vertices go through a
   single **shared node registry** keyed by quantised coordinates, so an
   edge shared by two regions yields the *same* node ids in both — this
   is what makes the mesh conforming across material interfaces without
   any stitching pass afterwards.

2. **Per-region triangulation.** Each region is triangulated separately
   from its own boundary nodes plus interior points seeded on a
   staggered (equilateral-ish) lattice. A Delaunay triangulation of that
   point set is computed and the triangles whose centroid falls outside
   the region polygon are discarded. Triangulating region by region
   guarantees that no element straddles a material interface, so the
   material assignment is exact rather than approximate.

3. **Quality refinement.** Triangles whose minimum angle is below
   ``min_angle`` get their circumcentre inserted as a new interior point
   (Chew / Ruppert style Delaunay refinement) and the region is
   re-triangulated. Repeated up to ``refine_passes`` times. Insertion is
   skipped for circumcentres that fall outside the region or too close
   to an existing node, which is what keeps the process terminating.

Why Delaunay from SciPy
-----------------------
``scipy.spatial.Delaunay`` (Qhull, BSD-licensed) is used because SciPy
is already a core dependency of the suite, so this phase adds **no new
dependency**. The obvious alternative, Shewchuk's *Triangle* (and its
``triangle`` Python wrapper), is deliberately **not** used: its licence
forbids commercial use, which is incompatible with this project's
GPL-3.0 licence. A pure-Python Bowyer–Watson triangulator is provided
as a fallback so meshing still works in a SciPy-less environment.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

from .mesh import Element, Mesh, Node

try:
    from scipy.spatial import Delaunay as _SciDelaunay
except ImportError:  # pragma: no cover
    _SciDelaunay = None


# ======================================================================
# Geometry helpers
# ======================================================================
def _poly_xy(polygon) -> list[tuple[float, float]]:
    """Region polygon as a list of (x, y), open (no repeated last point)."""
    verts = polygon.vertices
    pts = [(v.x, v.y) for v in verts]
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-12 \
            and abs(pts[0][1] - pts[-1][1]) < 1e-12:
        pts = pts[:-1]
    return pts


def _point_in_poly(x: float, y: float,
                   poly: Sequence[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            t = (y - y1) / (y2 - y1) if abs(y2 - y1) > 1e-300 else 0.0
            if x < x1 + t * (x2 - x1):
                inside = not inside
    return inside


def _dist_to_poly(x: float, y: float,
                  poly: Sequence[tuple[float, float]]) -> float:
    """Shortest distance from (x, y) to the polygon outline."""
    best = float("inf")
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-300:
            d = math.hypot(x - x1, y - y1)
        else:
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
            d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
        best = min(best, d)
    return best


def _circumcentre(p1, p2, p3):
    ax, ay = p1
    bx, by = p2
    cx, cy = p3
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-14:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy)
          + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx)
          + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy)


def _min_angle_deg(p1, p2, p3) -> float:
    pts = (p1, p2, p3)
    worst = 180.0
    for i in range(3):
        a, b, c = pts[i], pts[(i + 1) % 3], pts[(i + 2) % 3]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - a[0], c[1] - a[1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 < 1e-15 or n2 < 1e-15:
            return 0.0
        cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
        worst = min(worst, math.degrees(
            math.acos(max(-1.0, min(1.0, cosang)))))
    return worst


# ======================================================================
# Node registry — the key to inter-region conformity
# ======================================================================
class _NodeRegistry:
    """Deduplicates nodes by quantised coordinates so that regions
    sharing an edge reference identical node ids."""

    def __init__(self, tol: float = 1e-6) -> None:
        self.tol = tol
        self._map: dict[tuple[int, int], int] = {}
        self.nodes: list[Node] = []

    def _key(self, x: float, y: float) -> tuple[int, int]:
        q = 1.0 / self.tol
        return (int(round(x * q)), int(round(y * q)))

    def add(self, x: float, y: float) -> int:
        k = self._key(x, y)
        if k in self._map:
            return self._map[k]
        nid = len(self.nodes)
        self.nodes.append(Node(nid, x, y))
        self._map[k] = nid
        return nid


# ======================================================================
# Triangulation back-ends
# ======================================================================
def _delaunay(points: list[tuple[float, float]]):
    """Return a list of index triples triangulating ``points``."""
    if len(points) < 3:
        return []
    if _SciDelaunay is not None:
        try:
            tri = _SciDelaunay(points)
            return [tuple(int(i) for i in s) for s in tri.simplices]
        except Exception:  # noqa: BLE001 — degenerate/collinear input
            return _bowyer_watson(points)
    return _bowyer_watson(points)


def _bowyer_watson(points: list[tuple[float, float]]):
    """Pure-Python incremental Delaunay (fallback when SciPy is absent).

    Standard Bowyer–Watson with a super-triangle; O(n²) but perfectly
    adequate for the mesh sizes involved and dependency-free.
    """
    n = len(points)
    if n < 3:
        return []
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    dx = max(xs) - min(xs) or 1.0
    dy = max(ys) - min(ys) or 1.0
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    big = 20.0 * max(dx, dy)
    pts = list(points) + [
        (mx - big, my - big), (mx + big, my - big), (mx, my + big),
    ]
    tris = [(n, n + 1, n + 2)]

    def in_circum(t, p):
        a, b, c = pts[t[0]], pts[t[1]], pts[t[2]]
        cc = _circumcentre(a, b, c)
        if cc is None:
            return False
        r2 = (a[0] - cc[0]) ** 2 + (a[1] - cc[1]) ** 2
        return (p[0] - cc[0]) ** 2 + (p[1] - cc[1]) ** 2 <= r2 * (1 + 1e-12)

    for i in range(n):
        p = pts[i]
        bad = [t for t in tris if in_circum(t, p)]
        if not bad:
            continue
        edge_count: dict[tuple[int, int], int] = {}
        for t in bad:
            for u, v in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = (u, v) if u < v else (v, u)
                edge_count[k] = edge_count.get(k, 0) + 1
        boundary = [k for k, c in edge_count.items() if c == 1]
        tris = [t for t in tris if t not in bad]
        for u, v in boundary:
            tris.append((u, v, i))

    return [t for t in tris if all(idx < n for idx in t)]


# ======================================================================
# Interior point seeding
# ======================================================================
def _lattice_points(poly, h: float, margin: float
                    ) -> list[tuple[float, float]]:
    """Staggered (near-equilateral) lattice of interior points, kept at
    least ``margin`` away from the outline so they don't crowd the
    boundary discretisation."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    dy = h * math.sqrt(3.0) / 2.0
    out: list[tuple[float, float]] = []
    j = 0
    y = y0 + dy * 0.5
    while y < y1:
        offset = 0.0 if j % 2 == 0 else h * 0.5
        x = x0 + offset + h * 0.5
        while x < x1:
            if _point_in_poly(x, y, poly) and \
                    _dist_to_poly(x, y, poly) > margin:
                out.append((x, y))
            x += h
        y += dy
        j += 1
    return out


# ======================================================================
# Public API
# ======================================================================
def discretize_edges(registry: _NodeRegistry, poly, h: float) -> list[int]:
    """Split every polygon edge into ~``h`` long pieces, registering the
    nodes. Returns the ordered node ids around the outline."""
    ids: list[int] = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        L = math.hypot(x2 - x1, y2 - y1)
        nseg = max(1, int(round(L / h))) if h > 0 else 1
        for k in range(nseg):
            t = k / nseg
            ids.append(registry.add(x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
    return ids


def generate_mesh(
    regions,
    *,
    target_size: Optional[float] = None,
    target_elements: Optional[int] = None,
    min_angle: float = 25.0,
    refine_passes: int = 3,
    tolerance: float = 1e-6,
) -> Mesh:
    """Generate a conforming T3 mesh over ``regions``.

    Args:
        regions: sequence of ``MaterialRegion`` (from ``build_regions``).
        target_size: desired element edge length. If omitted it is
            derived from ``target_elements``, or defaults to a size that
            yields roughly 1000 elements over the total area.
        target_elements: approximate element count, used when
            ``target_size`` is not given.
        min_angle: quality floor (degrees) driving the refinement passes.
        refine_passes: maximum number of refinement iterations.
        tolerance: coordinate quantisation for node deduplication.

    Returns:
        A :class:`Mesh`. Empty if ``regions`` is empty or degenerate.
    """
    polys = []
    for idx, r in enumerate(regions):
        pts = _poly_xy(r.polygon)
        if len(pts) >= 3 and r.area > 0:
            polys.append((idx, r, pts))
    if not polys:
        return Mesh()

    total_area = sum(r.area for _i, r, _p in polys)
    if target_size is None or target_size <= 0:
        n_target = target_elements if target_elements else 1000
        n_target = max(8, int(n_target))
        # Area of an equilateral triangle of side h is h²·√3/4
        target_size = math.sqrt(4.0 * total_area
                                / (n_target * math.sqrt(3.0)))
    h = float(target_size)

    registry = _NodeRegistry(tolerance)
    elements: list[Element] = []

    for region_index, region, poly in polys:
        boundary_ids = discretize_edges(registry, poly, h)
        interior = _lattice_points(poly, h, margin=0.45 * h)

        for _pass in range(max(1, refine_passes + 1)):
            pts_idx = list(dict.fromkeys(boundary_ids))
            coords = [(registry.nodes[i].x, registry.nodes[i].y)
                      for i in pts_idx]
            extra_start = len(coords)
            coords += interior
            tris = _delaunay(coords)

            kept = []
            for t in tris:
                p = [coords[i] for i in t]
                cx = sum(q[0] for q in p) / 3.0
                cy = sum(q[1] for q in p) / 3.0
                if not _point_in_poly(cx, cy, poly):
                    continue
                kept.append(t)

            # Quality check → collect circumcentres of bad triangles
            bad_cc: list[tuple[float, float]] = []
            for t in kept:
                p = [coords[i] for i in t]
                if _min_angle_deg(*p) < min_angle:
                    cc = _circumcentre(*p)
                    if cc is None:
                        continue
                    if not _point_in_poly(cc[0], cc[1], poly):
                        continue
                    if _dist_to_poly(cc[0], cc[1], poly) < 0.35 * h:
                        continue
                    if any(math.hypot(cc[0] - q[0], cc[1] - q[1])
                           < 0.45 * h for q in coords):
                        continue
                    bad_cc.append(cc)

            if not bad_cc or _pass >= refine_passes:
                # Materialise the elements of this region
                for t in kept:
                    nids = []
                    for i in t:
                        if i < extra_start:
                            nids.append(pts_idx[i])
                        else:
                            cx, cy = coords[i]
                            nids.append(registry.add(cx, cy))
                    a, b, c = nids
                    # Enforce CCW orientation
                    (x1, y1) = (registry.nodes[a].x, registry.nodes[a].y)
                    (x2, y2) = (registry.nodes[b].x, registry.nodes[b].y)
                    (x3, y3) = (registry.nodes[c].x, registry.nodes[c].y)
                    if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) < 0:
                        b, c = c, b
                    elements.append(Element(
                        id=len(elements), nodes=(a, b, c),
                        material_id=getattr(region, "material_id", None),
                        region_index=region_index,
                    ))
                break
            # Otherwise seed the new points and try again
            interior = interior + bad_cc

    mesh = Mesh(nodes=list(registry.nodes), elements=elements,
                target_size=h)
    mesh.notes["regions"] = len(polys)
    mesh.notes["region_area"] = total_area
    return mesh


# ----------------------------------------------------------------------
def generate_mesh_for_project(project, **kwargs) -> Mesh:
    """Convenience wrapper: build the regions of ``project`` and mesh
    them. Returns an empty mesh when the project has no External."""
    from ogr_core.geometry import BoundaryType
    from ogr_core.geometry.regions import build_regions

    external = None
    for b in project.boundaries:
        if b.btype == BoundaryType.EXTERNAL:
            external = b
            break
    if external is None:
        return Mesh()
    mats = [b for b in project.boundaries
            if b.btype == BoundaryType.MATERIAL]
    regions = build_regions(external, mats)

    # ``build_regions`` leaves ``material_id`` unset unless the project
    # carries explicit region assignments. The hydraulic properties in
    # Phase 2/3 are per material, so resolve each region's material the
    # same way the LEM slicer does: query the project at the region
    # centroid.
    for r in regions:
        if getattr(r, "material_id", None):
            continue
        try:
            cx, cy = r.centroid()
            mat = project.material_at(cx, cy)
        except Exception:  # noqa: BLE001
            mat = None
        if mat is not None:
            r.material_id = getattr(mat, "id", None) or getattr(
                mat, "name", None)
    return generate_mesh(regions, **kwargs)
