# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Material region engine (v0.1.3).

Given an external boundary and a set of material boundaries (open
polylines or closed polygons drawn *inside* the external), this module
builds the set of *regions* that result from the planar subdivision.
Each region has:
    - a closed polygon describing its boundary
    - a material_id (possibly None if the user hasn't assigned one)

Implementation strategy (shapely-based):
    1. Build a shapely Polygon from the external boundary.
    2. For every material boundary: if it's a closed polygon, it becomes
       a splitting polygon; if it's an open polyline, we treat it as a
       splitting line that cuts the external.
    3. Use shapely's ``polygonize`` + ``unary_union`` pipeline to obtain
       the individual face polygons of the planar subdivision.
    4. For each face, classify which material it belongs to by:
         - preferring any closed material boundary that contains it
         - otherwise inheriting from the "side" of the cutting line that
           the user assigned (first assigned material wins)
         - otherwise None (unassigned)

Shapely is a soft dependency. If not installed, ``build_regions``
returns an empty list and ``regions_available`` returns False, so the
rest of the application keeps working.

Reference: https://shapely.readthedocs.io/en/stable/manual.html

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from .boundary import Boundary
from .boundary_type import BoundaryType
from .primitives import Polyline, Vertex

if TYPE_CHECKING:
    pass


# ----------------------------------------------------------------------
def regions_available() -> bool:
    """True iff shapely is importable — needed by the region engine."""
    try:
        import shapely  # noqa: F401
        return True
    except ImportError:
        return False


# ----------------------------------------------------------------------
@dataclass
class MaterialRegion:
    """A closed polygonal region resulting from planar subdivision."""

    polygon: Polyline  # always closed, CCW
    material_id: Optional[str] = None
    parent_boundary_ids: List[str] = field(default_factory=list)
    """IDs of the boundaries that form the edges of this region."""

    @property
    def area(self) -> float:
        """Signed area via the shoelace formula."""
        verts = self.polygon.vertices
        n = len(verts)
        if n < 3:
            return 0.0
        s = 0.0
        for i in range(n):
            j = (i + 1) % n
            s += verts[i].x * verts[j].y - verts[j].x * verts[i].y
        return abs(s) / 2.0

    def centroid(self) -> Tuple[float, float]:
        """Polygon centroid (area-weighted)."""
        verts = self.polygon.vertices
        n = len(verts)
        if n < 3:
            if verts:
                return (verts[0].x, verts[0].y)
            return (0.0, 0.0)
        cx = cy = 0.0
        a_sum = 0.0
        for i in range(n):
            j = (i + 1) % n
            cross = verts[i].x * verts[j].y - verts[j].x * verts[i].y
            cx += (verts[i].x + verts[j].x) * cross
            cy += (verts[i].y + verts[j].y) * cross
            a_sum += cross
        if abs(a_sum) < 1e-12:
            xs = [v.x for v in verts]
            ys = [v.y for v in verts]
            return (sum(xs) / n, sum(ys) / n)
        cx /= (3.0 * a_sum)
        cy /= (3.0 * a_sum)
        return (cx, cy)


# ----------------------------------------------------------------------
def build_regions(
    external: Boundary,
    material_boundaries: List[Boundary],
    *,
    tolerance: float = 1e-6,
) -> List[MaterialRegion]:
    """Compute the planar subdivision of ``external`` by the
    ``material_boundaries``.

    If shapely is available, uses the rigorous planar-subdivision
    algorithm. If not, falls back to a pure-Python implementation that
    handles the common case of one or more simple polylines that each
    cross the External cleanly (no intersections between material
    boundaries themselves). The fallback produces the correct result
    for the vast majority of slope-stability models.
    """
    if external.btype != BoundaryType.EXTERNAL or not external.polyline.closed:
        return []

    if regions_available():
        return _build_regions_shapely(external, material_boundaries, tolerance)
    return _build_regions_pure(external, material_boundaries, tolerance)


def _build_regions_shapely(
    external: Boundary,
    material_boundaries: List[Boundary],
    tolerance: float,
) -> List[MaterialRegion]:
    """Planar subdivision via shapely.

    v0.1.15 — completely rewritten with the **extend-then-clip-faces**
    algorithm used by AutoCAD, QGIS and other industrial CAD systems.

    Previous versions clipped each material boundary to the External
    polygon BEFORE the union. This created endpoints on the slope face
    with sub-millimetre floating-point error that prevented
    ``polygonize()`` from recognising them as shared nodes with the
    External boundary, dropping ALL the resulting faces.

    New algorithm:
        1. Compute the External polygon (with its exterior LineString).
        2. For each material boundary, **extend it beyond the External
           bounding box** so endpoints land far outside the polygon.
        3. ``unary_union`` of (ext_boundary + extended cuts) — this
           automatically nodes ALL intersections (including with the
           External edges), producing a fully-noded planar graph.
        4. ``polygonize`` produces all bounded faces.
        5. Keep only faces whose ``representative_point`` lies inside
           the External polygon. Faces outside are the "extension
           waste" and are discarded.
        6. Inherit ``material_id`` from any closed material boundary
           that contains the face centroid.
    """
    try:
        from shapely.geometry import (  # type: ignore[import-not-found]
            LineString,
            MultiLineString,
            Point,
            Polygon,
        )
        from shapely.ops import polygonize, unary_union  # type: ignore[import-not-found]
    except ImportError:
        return []

    # Build external polygon
    ext_coords = [(v.x, v.y) for v in external.polyline.vertices]
    if len(ext_coords) < 3:
        return []
    if ext_coords[0] == ext_coords[-1]:
        ext_coords = ext_coords[:-1]
    try:
        ext_poly = Polygon(ext_coords)
        if not ext_poly.is_valid:
            ext_poly = ext_poly.buffer(0)
        if ext_poly.is_empty:
            return []
    except Exception:  # noqa: BLE001
        return []

    minx, miny, maxx, maxy = ext_poly.bounds
    diag = math.hypot(maxx - minx, maxy - miny)
    # Length to extend material boundaries past the External — large
    # enough that no precision issue puts the endpoint inside.
    EXTEND = 10.0 * (diag + 1.0)

    def _extend_line(coords: list) -> "LineString":
        """Smart extension: extend only the endpoints that lie STRICTLY
        INSIDE the External polygon AND NOT on another cut. Endpoints
        on the External boundary, outside it, or on another cut are
        left alone — touching is enough to be noded by unary_union.
        """
        if len(coords) < 2:
            return LineString(coords)
        ext_ring_buf = ext_poly.boundary.buffer(snap_tol_local)
        x0, y0 = coords[0]
        xn, yn = coords[-1]
        start_outside = not ext_poly.buffer(snap_tol_local).contains(Point(x0, y0))
        start_on_boundary = ext_ring_buf.contains(Point(x0, y0))
        start_on_other_cut = _endpoint_on_other_cut(x0, y0, coords)
        end_outside = not ext_poly.buffer(snap_tol_local).contains(Point(xn, yn))
        end_on_boundary = ext_ring_buf.contains(Point(xn, yn))
        end_on_other_cut = _endpoint_on_other_cut(xn, yn, coords)

        start_needs_extension = (
            not start_outside
            and not start_on_boundary
            and not start_on_other_cut
        )
        end_needs_extension = (
            not end_outside
            and not end_on_boundary
            and not end_on_other_cut
        )

        prefix = []
        suffix = []
        if start_needs_extension:
            x1, y1 = coords[1]
            dx, dy = x0 - x1, y0 - y1
            L = math.hypot(dx, dy)
            if L > 1e-12:
                ux, uy = dx / L, dy / L
                prefix = [(x0 + EXTEND * ux, y0 + EXTEND * uy)]
        if end_needs_extension:
            xm, ym = coords[-2]
            dx, dy = xn - xm, yn - ym
            L = math.hypot(dx, dy)
            if L > 1e-12:
                ux, uy = dx / L, dy / L
                suffix = [(xn + EXTEND * ux, yn + EXTEND * uy)]
        return LineString(prefix + list(coords) + suffix)

    # Local snap tolerance for the helper above
    snap_tol_local = max(tolerance * diag, 1e-7)

    # Pre-collect coordinate lists of the OPEN material boundaries for
    # T-junction detection: an endpoint that lies on another cut should
    # NOT be extended (touching is enough to be noded by unary_union).
    open_cut_coords: list = []
    for mb in material_boundaries:
        if (mb.btype == BoundaryType.MATERIAL
                and not mb.polyline.closed
                and len(mb.polyline.vertices) >= 2):
            open_cut_coords.append([(v.x, v.y) for v in mb.polyline.vertices])

    # ------------------------------------------------------------------
    # v0.1.17 — ENDPOINT WELDING WITH NODE INSERTION on the raw
    # coordinates, BEFORE any extension. This reverse-engineers Slide's
    # documented behaviour: "whenever boundaries are drawn such that
    # they cross or intersect existing boundaries, new vertices will be
    # inserted at all intersection points" (Automatic Boundary
    # Intersection), combined with the Geometry-Cleanup snapping
    # tolerance and the GIS rule "snap-to-vertex has priority over
    # snap-to-segment".
    #
    # For each endpoint of each open material boundary that lies within
    # ``weld_tol`` of another boundary (mouse imprecision):
    #   1. If a VERTEX of the target is within weld_tol → move the
    #      endpoint EXACTLY onto that vertex (same float tuple).
    #   2. Otherwise project onto the nearest SEGMENT, move the
    #      endpoint to the projection, and INSERT the projection as a
    #      new vertex of the target line. Both lines then share the
    #      node with identical floats, so unary_union's noding is
    #      deterministic — relying on an endpoint merely "touching" the
    #      interior of a segment is fragile at the 1e-16 level and was
    #      the root cause of regions silently merging.
    # Endpoints farther than weld_tol from everything are genuine
    # danglings and keep the extend-past-External behaviour.
    weld_tol = diag * 8e-3  # ~0.8% of model diagonal (Slide-like ratio)
    ext_ring_coords: list = list(ext_poly.exterior.coords)  # closed ring

    def _nearest_on_polyline(pt, coords, closed):
        """Return (dist, kind, index, proj) where kind is 'vertex' or
        'segment'. Vertex matches within weld_tol take priority."""
        bx, by = pt
        best_v = (float("inf"), None)
        n = len(coords)
        last = n if closed else n  # ring repeats first at end already
        for i in range(n):
            vx, vy = coords[i]
            d = math.hypot(bx - vx, by - vy)
            if d < best_v[0]:
                best_v = (d, i)
        best_s = (float("inf"), None, None)
        for i in range(n - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            if L2 < 1e-24:
                continue
            t = ((bx - x1) * dx + (by - y1) * dy) / L2
            t = max(0.0, min(1.0, t))
            px, py = x1 + t * dx, y1 + t * dy
            d = math.hypot(bx - px, by - py)
            if d < best_s[0]:
                best_s = (d, i, (px, py))
        if best_v[0] <= weld_tol:
            return (best_v[0], "vertex", best_v[1], coords[best_v[1]])
        if best_s[0] <= weld_tol:
            return (best_s[0], "segment", best_s[1], best_s[2])
        return (float("inf"), None, None, None)

    try:
        for _pass in range(3):
            moved = False
            for ci, cc in enumerate(open_cut_coords):
                if len(cc) < 2:
                    continue
                for end_idx in (0, -1):
                    ept = cc[end_idx]
                    # candidate targets: every OTHER open cut + ext ring
                    best = (float("inf"), None, None, None, None)
                    for cj, c2 in enumerate(open_cut_coords):
                        if cj == ci or len(c2) < 2:
                            continue
                        d, kind, idx, proj = _nearest_on_polyline(
                            ept, c2, False)
                        if d < best[0]:
                            best = (d, kind, idx, proj, ("cut", cj))
                    d, kind, idx, proj = _nearest_on_polyline(
                        ept, ext_ring_coords, True)
                    if d < best[0]:
                        best = (d, kind, idx, proj, ("ext", None))
                    dbest, kind, idx, proj, tgt = best
                    if kind is None:
                        continue  # nothing within weld_tol
                    if kind == "vertex" and dbest <= 1e-12:
                        continue  # already EXACTLY a shared vertex — safe
                    if kind == "vertex":
                        # Snap-to-vertex: share the exact float tuple
                        cc[end_idx] = tuple(proj)
                        moved = True
                    else:
                        # Snap-to-segment + NODE INSERTION in the target.
                        # CRITICAL: this runs even when dbest ≈ 0 (e.g.
                        # the canvas snap-to-line placed the endpoint
                        # exactly on the segment interior). Relying on
                        # GEOS to node an endpoint that merely touches a
                        # segment interior is non-deterministic at the
                        # 1e-16 level; inserting the shared vertex makes
                        # the cut unconditional.
                        node_pt = (proj[0], proj[1])
                        if tgt[0] == "cut":
                            tgt_coords = open_cut_coords[tgt[1]]
                        else:
                            tgt_coords = ext_ring_coords
                        # Degenerate guard: if the projection coincides
                        # with one of the segment's end vertices, snap to
                        # that vertex instead of inserting a duplicate.
                        sx0, sy0 = tgt_coords[idx]
                        sx1, sy1 = tgt_coords[idx + 1]
                        if math.hypot(node_pt[0] - sx0,
                                      node_pt[1] - sy0) <= 1e-12:
                            cc[end_idx] = (sx0, sy0)
                        elif math.hypot(node_pt[0] - sx1,
                                        node_pt[1] - sy1) <= 1e-12:
                            cc[end_idx] = (sx1, sy1)
                        else:
                            cc[end_idx] = node_pt
                            tgt_coords.insert(idx + 1, node_pt)
                        moved = True
            if not moved:
                break
    except Exception:  # noqa: BLE001
        pass

    def _endpoint_on_other_cut(
        x: float, y: float, own_coords: list,
    ) -> bool:
        """Return True if (x, y) lies on the interior of some other open
        cut's polyline (not own_coords).

        v0.1.15 fix — compare cuts by VALUE, not identity. The
        ``coords`` list passed in by the caller is a fresh list, so
        ``cc is own_coords`` was never True and a cut was being
        compared against ITSELF (endpoint trivially on its own
        segment → always True → never extended). We now skip any cut
        whose coordinate sequence equals own_coords.
        """
        for cc in open_cut_coords:
            if cc == own_coords:
                continue
            for i in range(len(cc) - 1):
                x1, y1 = cc[i]
                x2, y2 = cc[i + 1]
                # Distance point-to-segment
                dx, dy = x2 - x1, y2 - y1
                L2 = dx * dx + dy * dy
                if L2 < 1e-18:
                    continue
                t = ((x - x1) * dx + (y - y1) * dy) / L2
                if t < -1e-6 or t > 1.0 + 1e-6:
                    continue
                px = x1 + t * dx
                py = y1 + t * dy
                if math.hypot(x - px, y - py) < snap_tol_local * 1000.0:
                    return True
        return False

    # Build (extended) material lines — open cuts take their WELDED
    # coordinates from open_cut_coords (same order as the filter above)
    cut_lines: list = []
    closed_polys_for_inheritance: list = []
    _open_i = 0
    for mb in material_boundaries:
        if mb.btype != BoundaryType.MATERIAL:
            continue
        if (not mb.polyline.closed
                and len(mb.polyline.vertices) >= 2):
            coords = [tuple(c) for c in open_cut_coords[_open_i]]
            _open_i += 1
        else:
            coords = [(v.x, v.y) for v in mb.polyline.vertices]
        if len(coords) < 2:
            continue
        if mb.polyline.closed and coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        if mb.polyline.closed:
            # Closed material boundary — used as inclusion (e.g. lens).
            # Don't extend; add as-is so its perimeter creates faces.
            try:
                cut_lines.append(LineString(coords))
                # Also record polygon for inheritance below
                try:
                    closed_p = Polygon(coords[:-1])
                    if not closed_p.is_valid:
                        closed_p = closed_p.buffer(0)
                    if not closed_p.is_empty:
                        closed_polys_for_inheritance.append(
                            (closed_p, mb.material_id, closed_p.area)
                        )
                except Exception:  # noqa: BLE001
                    pass
            except Exception:  # noqa: BLE001
                continue
        else:
            # Open material boundary — extend past External
            try:
                cut_lines.append(_extend_line(coords))
            except Exception:  # noqa: BLE001
                continue

    # Union & polygonize. Endpoint welding already happened on the raw
    # coordinates (see above), so here we only need the micro-scale
    # snap-rounding (set_precision) that welds near-coincident nodes at
    # T-/X-junctions, eliminating sliver polygons.
    try:
        ext_boundary = LineString(ext_ring_coords)
    except Exception:  # noqa: BLE001
        ext_boundary = LineString(list(ext_poly.exterior.coords))
    all_lines = [ext_boundary] + cut_lines
    grid_size = max(diag * 1e-8, 1e-12)
    try:
        from shapely import set_precision  # type: ignore[import-not-found]
        merged = unary_union(all_lines)
        merged = set_precision(merged, grid_size)
        raw_faces = list(polygonize(merged))
    except Exception:  # noqa: BLE001
        try:
            merged = unary_union(all_lines)
            raw_faces = list(polygonize(merged))
        except Exception:  # noqa: BLE001
            return []

    # Filter: keep faces inside External and discard slivers
    snap_tol = max(tolerance * diag, 1e-7)
    min_area = (diag * diag) * 1e-6  # epsilon area filter (sliver removal)
    faces: list = []
    for f in raw_faces:
        if not f.is_valid or f.is_empty:
            continue
        if f.area < min_area:
            continue  # sliver — digitisation artefact, discard
        c = f.representative_point()
        if ext_poly.buffer(snap_tol).contains(c):
            faces.append(f)

    # Inheritance from closed material boundaries (smallest first → inner wins)
    closed_polys_for_inheritance.sort(key=lambda t: t[2])

    regions: list[MaterialRegion] = []
    for f in faces:
        mat_id: Optional[str] = None
        c = f.representative_point()
        for p, mid, _ in closed_polys_for_inheritance:
            if p.contains(c) or p.buffer(tolerance).contains(c):
                mat_id = mid
        ext_ring = list(f.exterior.coords)
        if ext_ring and ext_ring[0] == ext_ring[-1]:
            ext_ring = ext_ring[:-1]
        verts = [Vertex(x, y) for (x, y) in ext_ring]
        poly = Polyline(vertices=verts, closed=True)
        try:
            poly.ensure_ccw()
        except Exception:  # noqa: BLE001
            pass
        regions.append(MaterialRegion(polygon=poly, material_id=mat_id))

    return regions


def _extend_dangling_endpoints(
    cut_lines, ext_poly, tol, LineString, Point, MultiLineString,
):
    """For each cut line, check if either endpoint is "dangling"
    (not on the External boundary AND not touching another cut). If
    so, extend that endpoint along the line direction until it hits
    the nearest line or the External — without this, polygonize()
    drops the cut entirely and adjacent regions get merged."""
    if not cut_lines:
        return cut_lines

    ext_boundary = ext_poly.exterior

    def _is_endpoint_dangling(pt, this_line, others):
        """True if pt is not on the External AND not within tol of
        any other cut line."""
        # On External?
        if ext_boundary.distance(Point(pt)) < tol:
            return False
        # Touching another cut?
        for other in others:
            if other is this_line:
                continue
            if other.distance(Point(pt)) < tol:
                return False
        return True

    extended: list = []
    for ls in cut_lines:
        coords = list(ls.coords)
        if len(coords) < 2:
            extended.append(ls)
            continue
        # Check first endpoint
        p0 = coords[0]
        if _is_endpoint_dangling(p0, ls, cut_lines):
            # Extend along the direction (p0 ← p1) outward by a large
            # multiple — then re-clip to ext_poly so we stop at perimeter
            x0, y0 = p0
            x1, y1 = coords[1]
            dx, dy = x0 - x1, y0 - y1
            length = (dx * dx + dy * dy) ** 0.5
            if length > tol:
                ux, uy = dx / length, dy / length
                far_x = x0 + ux * (ext_poly.bounds[2] - ext_poly.bounds[0])
                far_y = y0 + uy * (ext_poly.bounds[3] - ext_poly.bounds[1])
                ray = LineString([(x0, y0), (far_x, far_y)])
                clipped = ray.intersection(ext_poly)
                if clipped.geom_type == "LineString" and clipped.length > tol:
                    new_p0 = list(clipped.coords)[-1]
                    coords = [new_p0] + coords
        # Check last endpoint
        p1 = coords[-1]
        if _is_endpoint_dangling(p1, ls, cut_lines):
            xn1, yn1 = coords[-1]
            xn2, yn2 = coords[-2]
            dx, dy = xn1 - xn2, yn1 - yn2
            length = (dx * dx + dy * dy) ** 0.5
            if length > tol:
                ux, uy = dx / length, dy / length
                far_x = xn1 + ux * (ext_poly.bounds[2] - ext_poly.bounds[0])
                far_y = yn1 + uy * (ext_poly.bounds[3] - ext_poly.bounds[1])
                ray = LineString([(xn1, yn1), (far_x, far_y)])
                clipped = ray.intersection(ext_poly)
                if clipped.geom_type == "LineString" and clipped.length > tol:
                    new_p1 = list(clipped.coords)[-1]
                    coords = coords + [new_p1]
        try:
            extended.append(LineString(coords))
        except Exception:  # noqa: BLE001
            extended.append(ls)
    return extended


# ----------------------------------------------------------------------
def region_at_point(
    regions: List[MaterialRegion],
    x: float,
    y: float,
) -> Optional[MaterialRegion]:
    """Return the region containing (x, y), or None.

    v0.1.10: pure-Python ray-casting fallback when shapely is missing.
    """
    # Try shapely first (faster + handles edge cases more robustly)
    try:
        from shapely.geometry import Point, Polygon  # type: ignore[import-not-found]
        pt = Point(x, y)
        for r in regions:
            coords = [(v.x, v.y) for v in r.polygon.vertices]
            if len(coords) < 3:
                continue
            p = Polygon(coords)
            if p.contains(pt):
                return r
        return None
    except ImportError:
        pass

    # Pure-Python ray-casting fallback (v0.1.10)
    for r in regions:
        verts = r.polygon.vertices
        if len(verts) < 3:
            continue
        if _point_in_polygon_xy(x, y, verts):
            return r
    return None


def _point_in_polygon_xy(x: float, y: float, verts) -> bool:
    """Standard ray-casting test. ``verts`` is a list of objects with .x/.y."""
    n = len(verts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = verts[i].x, verts[i].y
        xj, yj = verts[j].x, verts[j].y
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-20) + xi
        ):
            inside = not inside
        j = i
    return inside


# ======================================================================
# Pure-Python fallback for environments without shapely
# ======================================================================
def _build_regions_pure(
    external: Boundary,
    material_boundaries: List[Boundary],
    tolerance: float,
) -> List[MaterialRegion]:
    """Pure-Python planar subdivision of the External by N Material
    Boundaries. Robust to arbitrary numbers of cutting lines.

    Strategy: for each Material Boundary segment, intersect it with the
    perimeter of every existing region. If the segment crosses a region
    twice, split that region along the chord. Iterate until no more
    splits occur.

    Works correctly for:
      • horizontal lines stacked vertically (3+ materials → 4+ regions)
      • diagonal cuts
      • zig-zag material boundaries (2-segment polylines)
      • multiple boundaries that cross each other
    """
    ext_verts = list(external.polyline.vertices)
    if len(ext_verts) < 3:
        return []
    if ext_verts[0] == ext_verts[-1]:
        ext_verts = ext_verts[:-1]
    if _signed_area_pure(ext_verts) < 0:
        ext_verts = list(reversed(ext_verts))

    # Collect every Material Boundary as a list of segments (its polyline)
    cut_polylines: list[list[Vertex]] = []
    for mb in material_boundaries:
        if mb.btype != BoundaryType.MATERIAL:
            continue
        verts = list(mb.polyline.vertices)
        if len(verts) < 2:
            continue
        if mb.polyline.closed and verts[0] != verts[-1]:
            verts = verts + [verts[0]]
        cut_polylines.append(verts)

    bbox_dx = max(v.x for v in ext_verts) - min(v.x for v in ext_verts)
    bbox_dy = max(v.y for v in ext_verts) - min(v.y for v in ext_verts)
    abs_tol = max(tolerance * max(bbox_dx, bbox_dy, 1.0), 1e-9)

    # v0.1.9 — use a global planar-graph subdivision rather than the
    # iterative single-cut clipping that v0.1.8 used. This handles
    # crossing cuts (e.g. an X) and partial cuts that meet other cuts
    # in the interior.
    regions_polys = _subdivide_planar(ext_verts, cut_polylines, abs_tol)

    # Build MaterialRegion objects
    result: list[MaterialRegion] = []
    for verts in regions_polys:
        if len(verts) < 3:
            continue
        if _signed_area_pure(verts) < 0:
            verts = list(reversed(verts))
        pline = Polyline(vertices=list(verts), closed=True)
        result.append(MaterialRegion(polygon=pline, material_id=None))
    return result



def _pre_split_cuts_at_mutual_crossings(
    cuts: list[list[Vertex]], tol: float,
) -> list[list[Vertex]]:
    """[Deprecated in v0.1.9] kept for back-compat — see _subdivide_planar."""
    return cuts


def _extend_dangling_endpoints_pure(
    ext_verts: list[Vertex],
    cut_polylines: list[list[Vertex]],
    tol: float,
) -> list[list[Vertex]]:
    """For each cut polyline, if either endpoint is a "dangling" point
    (not on External perimeter, not coincident with another cut, not
    crossing another cut nearby), extend that endpoint along the cut's
    tangent until it hits the External perimeter — so the face traversal
    in :func:`_subdivide_planar` can close the region.

    v0.1.12 — fix for the bug where cuts whose endpoints lie inside
    the External produce dropped regions.
    """
    if not cut_polylines:
        return cut_polylines

    n = len(ext_verts)
    ext_segs = [(ext_verts[i], ext_verts[(i + 1) % n]) for i in range(n)]

    # Compute model bbox for ray length
    xs = [v.x for v in ext_verts]
    ys = [v.y for v in ext_verts]
    bbox_diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5

    def _on_ext_perimeter(p: Vertex) -> bool:
        for a, b in ext_segs:
            # Distance from p to segment ab
            dx, dy = b.x - a.x, b.y - a.y
            L2 = dx * dx + dy * dy
            if L2 < tol * tol:
                continue
            t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2))
            qx = a.x + t * dx
            qy = a.y + t * dy
            if (p.x - qx) ** 2 + (p.y - qy) ** 2 < tol * tol:
                return True
        return False

    def _near_other_cut(p: Vertex, this_idx: int) -> bool:
        for k, other in enumerate(cut_polylines):
            if k == this_idx:
                continue
            for i in range(len(other) - 1):
                a, b = other[i], other[i + 1]
                dx, dy = b.x - a.x, b.y - a.y
                L2 = dx * dx + dy * dy
                if L2 < tol * tol:
                    continue
                t = max(0.0, min(1.0,
                    ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2))
                qx = a.x + t * dx
                qy = a.y + t * dy
                if (p.x - qx) ** 2 + (p.y - qy) ** 2 < tol * tol:
                    return True
        return False

    def _extend_to_ext(p: Vertex, prev: Vertex) -> Optional[Vertex]:
        """Cast a ray from p along (p - prev) direction; return the
        first intersection with the External boundary."""
        ddx, ddy = p.x - prev.x, p.y - prev.y
        L = (ddx * ddx + ddy * ddy) ** 0.5
        if L < tol:
            return None
        ux, uy = ddx / L, ddy / L
        # Far point in the direction
        far_x = p.x + ux * bbox_diag * 2
        far_y = p.y + uy * bbox_diag * 2
        best = None
        best_d2 = float("inf")
        for a, b in ext_segs:
            inter = _segment_segment_intersection(
                p.x, p.y, far_x, far_y,
                a.x, a.y, b.x, b.y, tol,
            )
            if inter is None:
                continue
            ix, iy = inter[0], inter[1]
            d2 = (ix - p.x) ** 2 + (iy - p.y) ** 2
            if d2 > tol * tol and d2 < best_d2:
                best = Vertex(ix, iy)
                best_d2 = d2
        return best

    extended: list[list[Vertex]] = []
    for idx, cut in enumerate(cut_polylines):
        if len(cut) < 2:
            extended.append(cut)
            continue
        new_cut = list(cut)
        # First endpoint
        p0, p1 = new_cut[0], new_cut[1]
        if not _on_ext_perimeter(p0) and not _near_other_cut(p0, idx):
            ext_p = _extend_to_ext(p0, p1)
            if ext_p is not None:
                new_cut = [ext_p] + new_cut
        # Last endpoint
        pn, pm = new_cut[-1], new_cut[-2]
        if not _on_ext_perimeter(pn) and not _near_other_cut(pn, idx):
            ext_p = _extend_to_ext(pn, pm)
            if ext_p is not None:
                new_cut = new_cut + [ext_p]
        extended.append(new_cut)
    return extended


# ======================================================================
# v0.1.9 — Correct planar subdivision via half-edge face traversal.
# ======================================================================
import math as _math


def _subdivide_planar(
    ext_verts: list[Vertex],
    cut_polylines: list[list[Vertex]],
    tol: float,
) -> list[list[Vertex]]:
    """Compute the planar subdivision of an External polygon by N
    Material Boundary polylines (each may be a polyline of any length;
    they may cross each other; their endpoints may lie inside the
    polygon, on its perimeter, or even outside — though for OGR the
    common case is endpoints on the perimeter).

    v0.1.12 — extended to handle dangling endpoints by ray-casting
    from each dangling endpoint outward along the cut's tangent until
    it intersects another segment. This makes faces close around the
    cut so polygonize() (or our half-edge walk) can find them.
    """
    # v0.1.12 — pre-process: extend dangling endpoints
    cut_polylines = _extend_dangling_endpoints_pure(
        ext_verts, cut_polylines, tol,
    )

    """Algorithm continues:
      1. Collect every segment (External edges + every cut segment)
      2. Find all pairwise intersections; split every segment at every
         intersection point into sub-segments.
      3. Build a planar graph: nodes are unique points (with tolerance
         dedup); edges are sub-segments. Each undirected edge becomes
         two directed half-edges.
      4. Walk the half-edge graph turning RIGHT at each vertex
         (clockwise) — this enumerates the bounded faces. Drop the
         face whose orientation is CCW (that's the outer face).
      5. Each remaining face whose **interior** is inside the External
         polygon is a region. (Faces created by free-floating cuts
         outside the External are dropped.)

    For polylines whose endpoints don't reach the External perimeter,
    the resulting "dangling" edges produce no face and are simply
    ignored — the rest of the subdivision still works correctly.
    """
    # Build segment list
    segs: list[tuple[Vertex, Vertex]] = []
    n = len(ext_verts)
    for i in range(n):
        segs.append((ext_verts[i], ext_verts[(i + 1) % n]))
    for cut in cut_polylines:
        for i in range(len(cut) - 1):
            segs.append((cut[i], cut[i + 1]))

    # v0.1.13 — explicit noding for endpoints that lie ON other
    # segments. Without this, cuts whose first/last vertex sits exactly
    # on another cut (the "T-junction" case Samuel reports) leave the
    # receiving segment unsplit and the planar graph misses a node →
    # adjacent regions don't close.
    segs = _node_endpoints_on_segments(segs, tol)

    # Find intersections and split every segment at each intersection
    sub_segs = _split_all_at_crossings(segs, tol)

    # Build graph: dedupe nodes
    points: list[tuple[float, float]] = []
    point_index: dict[tuple[float, float], int] = {}

    def _idx_of(v: Vertex) -> int:
        # Snap to existing nearby point if within tolerance
        for k, (x, y) in enumerate(points):
            if abs(x - v.x) < tol and abs(y - v.y) < tol:
                return k
        points.append((v.x, v.y))
        return len(points) - 1

    edges: set[tuple[int, int]] = set()
    for a, b in sub_segs:
        ia, ib = _idx_of(a), _idx_of(b)
        if ia == ib:
            continue
        edges.add((ia, ib))
        edges.add((ib, ia))

    # adjacency: node → list of neighbour nodes
    adj: dict[int, list[int]] = {}
    for u, v in edges:
        adj.setdefault(u, []).append(v)

    # Sort each adjacency list by angle (CCW) — needed for face walk
    def _angle(u: int, v: int) -> float:
        ux, uy = points[u]
        vx, vy = points[v]
        return _math.atan2(vy - uy, vx - ux)

    for u in adj:
        adj[u].sort(key=lambda v: _angle(u, v))

    # Face traversal: for each directed edge, the next edge of the
    # same face is the "previous CCW neighbour" of the incoming edge.
    # i.e. arriving u→v, next is v→w where w is the neighbour of v
    # that comes BEFORE u in v's CCW-sorted adjacency.
    visited: set[tuple[int, int]] = set()
    faces: list[list[int]] = []

    for start_u, start_v in edges:
        if (start_u, start_v) in visited:
            continue
        face: list[int] = [start_u]
        u, v = start_u, start_v
        safety = 0
        while safety < 100000:
            visited.add((u, v))
            face.append(v)
            # Next edge: at v, find the neighbour of v that immediately
            # precedes u in v's CCW order → that gives a CW face walk
            neigh = adj.get(v, [])
            if not neigh or u not in neigh:
                face = []
                break
            ui = neigh.index(u)
            next_w = neigh[(ui - 1) % len(neigh)]
            u, v = v, next_w
            if (u, v) == (start_u, start_v):
                break
            safety += 1
        if face and len(face) >= 4:
            faces.append(face)

    # Convert each face (list of node indices) to a list of Vertex; drop
    # duplicate first/last and CCW outer face.
    result: list[list[Vertex]] = []
    for f in faces:
        if f[0] == f[-1]:
            f = f[:-1]
        if len(f) < 3:
            continue
        verts = [Vertex(*points[i]) for i in f]
        sa = _signed_area_pure(verts)
        # Outer face is CW (sa < 0); inner faces are CCW (sa > 0)
        if sa <= 0:
            continue
        # Dedupe near-duplicate consecutive vertices
        clean: list[Vertex] = []
        for v in verts:
            if clean and abs(clean[-1].x - v.x) < tol and abs(clean[-1].y - v.y) < tol:
                continue
            clean.append(v)
        if len(clean) < 3:
            continue
        result.append(clean)

    # If no inner face was found (e.g. no cuts), fall back to the
    # External itself
    if not result:
        result = [list(ext_verts)]

    return result


def _node_endpoints_on_segments(
    segs: list[tuple[Vertex, Vertex]], tol: float,
) -> list[tuple[Vertex, Vertex]]:
    """Insert split nodes at "T-junctions" — where an endpoint of one
    segment lies on the interior of another segment.

    v0.1.13 — fix for the P1 bug: when a Material Boundary starts from
    another Material Boundary (its endpoint sits exactly on another
    cut), the planar-graph build was missing a node at that point so
    adjacent regions failed to close.

    The standard segment–segment crossing split rejects ``t = 0`` or
    ``t = 1`` (endpoints) by design because we don't want consecutive
    segments of the External polygon to register fake intersections at
    their shared vertex. So we handle T-junctions explicitly here:

        - For each segment endpoint p in ``segs``,
        - Scan all OTHER segments;
        - If p lies on the interior of segment k (parameter
          ``s ∈ (tol, 1−tol)``), split segment k at p.
    """
    if not segs:
        return segs

    # Collect every distinct endpoint
    endpoints: list[tuple[float, float]] = []
    seen: set[tuple[int, int]] = set()
    grid_tol = max(tol, 1e-9)

    def _key(x: float, y: float) -> tuple[int, int]:
        return (round(x / grid_tol), round(y / grid_tol))

    for a, b in segs:
        for v in (a, b):
            k = _key(v.x, v.y)
            if k in seen:
                continue
            seen.add(k)
            endpoints.append((v.x, v.y))

    # For each segment, find every endpoint that lies on its interior
    splits: list[list[tuple[float, float, float]]] = [[] for _ in segs]
    for k, (a, b) in enumerate(segs):
        ax, ay, bx, by = a.x, a.y, b.x, b.y
        d1x, d1y = bx - ax, by - ay
        L2 = d1x * d1x + d1y * d1y
        if L2 < tol * tol:
            continue
        for px, py in endpoints:
            # Skip the segment's own endpoints
            if (abs(px - ax) < tol and abs(py - ay) < tol) or \
               (abs(px - bx) < tol and abs(py - by) < tol):
                continue
            # Project p onto segment k
            s = ((px - ax) * d1x + (py - ay) * d1y) / L2
            if s <= tol or s >= 1.0 - tol:
                continue
            # Check perpendicular distance
            qx = ax + s * d1x
            qy = ay + s * d1y
            d2 = (px - qx) ** 2 + (py - qy) ** 2
            if d2 > tol * tol:
                continue
            # Found T-junction at parameter s
            splits[k].append((s, px, py))

    # Apply splits
    out: list[tuple[Vertex, Vertex]] = []
    for k, (a, b) in enumerate(segs):
        if not splits[k]:
            out.append((a, b))
            continue
        ts = sorted(splits[k], key=lambda p: p[0])
        prev = a
        for s, x, y in ts:
            v = Vertex(x, y)
            if abs(v.x - prev.x) > tol or abs(v.y - prev.y) > tol:
                out.append((prev, v))
            prev = v
        if abs(b.x - prev.x) > tol or abs(b.y - prev.y) > tol:
            out.append((prev, b))
    return out


def _split_all_at_crossings(
    segs: list[tuple[Vertex, Vertex]], tol: float,
) -> list[tuple[Vertex, Vertex]]:
    """For every pairwise intersection of segments, split both segments
    at the intersection point. Returns the new segment list.
    """
    # Collect intersection points per segment
    breaks: list[list[tuple[float, float, float]]] = [[] for _ in segs]
    for i in range(len(segs)):
        ax, ay = segs[i][0].x, segs[i][0].y
        bx, by = segs[i][1].x, segs[i][1].y
        for j in range(i + 1, len(segs)):
            cx, cy = segs[j][0].x, segs[j][0].y
            dx, dy = segs[j][1].x, segs[j][1].y
            inter = _segment_segment_intersection(
                ax, ay, bx, by, cx, cy, dx, dy, tol,
            )
            if inter is None:
                continue
            x, y, t_i, t_j = inter
            breaks[i].append((t_i, x, y))
            breaks[j].append((t_j, x, y))

    out: list[tuple[Vertex, Vertex]] = []
    for k, (a, b) in enumerate(segs):
        ts = sorted(breaks[k], key=lambda p: p[0])
        prev = a
        for t, x, y in ts:
            v = Vertex(x, y)
            if abs(v.x - prev.x) > tol or abs(v.y - prev.y) > tol:
                out.append((prev, v))
            prev = v
        if abs(b.x - prev.x) > tol or abs(b.y - prev.y) > tol:
            out.append((prev, b))
    return out


def _split_polygon_by_polyline(
    poly: list[Vertex], cut: list[Vertex], tol: float,
) -> list[list[Vertex]] | None:
    """Split a closed CCW polygon by a polyline that enters and exits.

    The cut polyline can have any number of segments. We find:
      • First crossing of any cut segment with any polygon edge
      • Last crossing of any cut segment with any polygon edge

    If exactly two distinct crossings exist (entry + exit), we split
    the polygon into two new polygons:
      A: chord_entry → walk perimeter forward → chord_exit → walk
         the cut polyline backwards from exit to entry
      B: chord_exit → walk perimeter forward → chord_entry → walk
         the cut polyline forwards from entry to exit

    Returns None if the cut doesn't cleanly enter and exit.
    """
    n = len(poly)
    if n < 3 or len(cut) < 2:
        return None

    # Collect ALL crossings between cut segments and polygon edges
    # Each crossing = (seg_idx_in_cut, s_along_cut_segment,
    #                  edge_idx_in_poly, t_along_edge, x, y)
    crossings = []
    for si in range(len(cut) - 1):
        cax, cay = cut[si].x, cut[si].y
        cbx, cby = cut[si + 1].x, cut[si + 1].y
        for ei in range(n):
            pax, pay = poly[ei].x, poly[ei].y
            pbx, pby = poly[(ei + 1) % n].x, poly[(ei + 1) % n].y
            inter = _segment_segment_intersection(
                pax, pay, pbx, pby,
                cax, cay, cbx, cby,
                tol,
            )
            if inter is None:
                continue
            x, y, t_edge, s_seg = inter
            crossings.append((si, s_seg, ei, t_edge, x, y))

    if not crossings:
        return None

    # Order along the cut polyline: first by segment index, then by s
    crossings.sort(key=lambda c: (c[0], c[1]))

    # Dedupe near-coincident crossings
    deduped = []
    for c in crossings:
        if deduped:
            last = deduped[-1]
            if abs(c[4] - last[4]) < tol and abs(c[5] - last[5]) < tol:
                continue
        deduped.append(c)
    if len(deduped) < 2:
        return None

    # Use the FIRST and LAST crossings (entry and exit)
    entry = deduped[0]
    exit_ = deduped[-1]
    si_in, s_in, ei_in, t_in, xin, yin = entry
    si_out, s_out, ei_out, t_out, xout, yout = exit_

    cut_in = Vertex(xin, yin)
    cut_out = Vertex(xout, yout)

    # Build the chord polyline (the part of the cut between entry and exit)
    # entry is at cut[si_in]→cut[si_in+1] at param s_in
    # exit at cut[si_out]→cut[si_out+1] at param s_out
    # The "interior" of the cut between entry and exit goes:
    #     cut_in → cut[si_in+1] → cut[si_in+2] → ... → cut[si_out] → cut_out
    chord: list[Vertex] = [cut_in]
    for k in range(si_in + 1, si_out + 1):
        chord.append(cut[k])
    chord.append(cut_out)

    # Polygon A: walk perimeter forward from cut_in's edge to cut_out's
    # edge, then close via chord backwards
    poly_a: list[Vertex] = [cut_in]
    i = (ei_in + 1) % n
    safety = 0
    same_edge = (ei_in == ei_out)
    if same_edge and t_in <= t_out:
        # Forward side has no perimeter vertices between cuts
        pass
    else:
        while safety < n + 2:
            if i == (ei_out + 1) % n:
                break
            poly_a.append(poly[i])
            i = (i + 1) % n
            safety += 1
    poly_a.append(cut_out)
    poly_a.extend(reversed(chord[1:-1]))

    # Polygon B: from cut_out forward around perimeter back to cut_in,
    # then chord forward
    poly_b: list[Vertex] = [cut_out]
    i = (ei_out + 1) % n
    safety = 0
    if same_edge and t_in <= t_out:
        # The "other side" requires walking ALL polygon vertices
        while safety < n + 2:
            if i == (ei_in + 1) % n:
                break
            poly_b.append(poly[i])
            i = (i + 1) % n
            safety += 1
    else:
        while safety < n + 2:
            if i == (ei_in + 1) % n:
                break
            poly_b.append(poly[i])
            i = (i + 1) % n
            safety += 1
    poly_b.append(cut_in)
    poly_b.extend(chord[1:-1])

    if len(poly_a) < 3 or len(poly_b) < 3:
        return None
    if abs(_signed_area_pure(poly_a)) < tol * tol:
        return None
    if abs(_signed_area_pure(poly_b)) < tol * tol:
        return None
    return [poly_a, poly_b]


def _segment_segment_intersection(
    ax, ay, bx, by, cx, cy, dx, dy, tol,
):
    """Intersection point of segment (a,b) with segment (c,d).

    Returns ``(x, y, t, s)`` where ``t`` is the parameter along (a,b)
    and ``s`` along (c,d), or ``None`` if the segments don't intersect
    in their interior. Both t and s must be in (tol, 1-tol).
    """
    d1x = bx - ax
    d1y = by - ay
    d2x = dx - cx
    d2y = dy - cy
    denom = d1x * d2y - d1y * d2x
    if abs(denom) < 1e-15:
        return None
    t = ((cx - ax) * d2y - (cy - ay) * d2x) / denom
    s = ((cx - ax) * d1y - (cy - ay) * d1x) / denom
    # Allow segment endpoints to land exactly on polygon edges
    # (s = 0 or s = 1 is fine; the segment's endpoints can be anywhere)
    # But we want t strictly inside the polygon edge to avoid
    # double-counting at polygon vertices.
    if t < 1e-9 or t > 1.0 - 1e-9:
        return None
    if s < -1e-9 or s > 1.0 + 1e-9:
        return None
    x = ax + t * d1x
    y = ay + t * d1y
    return (x, y, t, s)


def _signed_area_pure(verts: list[Vertex]) -> float:
    s = 0.0
    n = len(verts)
    for i in range(n):
        x1, y1 = verts[i].x, verts[i].y
        x2, y2 = verts[(i + 1) % n].x, verts[(i + 1) % n].y
        s += x1 * y2 - x2 * y1
    return 0.5 * s
