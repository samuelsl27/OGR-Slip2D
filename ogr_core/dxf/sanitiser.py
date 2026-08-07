# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Geometry sanitiser for DXF import — Phase D1.

A DXF arrives in worse shape than anything drawn in the editor: lines that
*look* joined but end 0.3 mm apart, polylines with hundreds of digitised
vertices, an external boundary left open, crossings with no shared node.
Any one of those produces **open regions**, and an open region means
materials cannot be assigned and the model is useless.

So the importer is not a reader, it is a **repairer**. The pipeline, in
the order the steps must run:

1. **Vertex merging** — coincident-within-tolerance points collapse to a
   single location.
2. **Endpoint welding onto segments** — an endpoint lying near the
   *interior* of another segment is projected onto it **and a node is
   inserted in that segment**. This is the step that decides whether
   regions close: welding endpoint-to-endpoint only is not enough, and
   getting it wrong is exactly what once left material regions
   undetected in the editor. It is done unconditionally rather than
   depending on the order the entities happen to arrive in.
3. **Splitting at crossings** — every pair of polylines is intersected
   and both are split at the crossing, so no intersection is left without
   a shared node.
4. **Closing the external boundary** if it arrived open.
5. **Extending** material boundaries and water surfaces that fall short
   of the external boundary.
6. **Douglas-Peucker simplification**, last, so it can never undo the
   welding done above.

All tolerances are **relative to the model diagonal**, because the same
absolute tolerance behaves completely differently on a drawing in
millimetres and one in metres. The percentage is a user parameter.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .reader import DxfEntityKind, DxfPolyline

# Defaults, as fractions of the model diagonal. The welding default is
# deliberately generous: a CAD drawing with visually joined lines is
# routinely off by a few parts in ten thousand, and failing to weld costs
# far more (an unusable model) than welding slightly too eagerly (a
# vertex moved imperceptibly).
DEFAULT_WELD_PCT = 0.05        # 0.05 % of the diagonal
DEFAULT_SIMPLIFY_PCT = 0.02    # 0.02 % of the diagonal
WELD_PCT_RANGE = (0.005, 0.5)  # recommended range shown in the dialog


@dataclass
class SanitiseReport:
    """What the sanitiser did and what it could not fix."""

    merged_vertices: int = 0
    welded_endpoints: int = 0
    nodes_inserted: int = 0
    crossings_split: int = 0
    closed_boundaries: int = 0
    extended_ends: int = 0
    vertices_before: int = 0
    vertices_after: int = 0
    problems: list = field(default_factory=list)
    notes: dict = field(default_factory=dict)

    def add_problem(self, kind: str, message: str, x=None, y=None):
        """Record something the user must look at, with a location so the
        dialog can centre the view on it."""
        self.problems.append({"kind": kind, "message": message,
                              "x": x, "y": y})

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def vertices_removed(self) -> int:
        return max(0, self.vertices_before - self.vertices_after)

    def summary(self) -> str:
        return (
            f"{self.merged_vertices} vertices merged, "
            f"{self.welded_endpoints} endpoints welded "
            f"({self.nodes_inserted} nodes inserted), "
            f"{self.crossings_split} crossings split, "
            f"{self.closed_boundaries} boundaries closed, "
            f"{self.extended_ends} ends extended; "
            f"{self.vertices_before} → {self.vertices_after} vertices"
        )


# ======================================================================
# Geometry primitives
# ======================================================================
def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _point_segment(p, a, b):
    """Closest point on segment ab to p, as ``(distance, t, point)``.

    ``t`` is the normalised position along the segment, so the caller can
    tell an endpoint contact (t near 0 or 1) from an interior one — the
    distinction that decides whether a node must be inserted.
    """
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-30:
        return _dist(p, a), 0.0, a
    t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2
    t = max(0.0, min(1.0, t))
    q = (ax + t * dx, ay + t * dy)
    return _dist(p, q), t, q


def _segment_intersection(p1, p2, p3, p4):
    """Proper crossing point of two segments, or None.

    Shared endpoints are NOT reported: they are already a common node and
    splitting there would only create duplicate vertices.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    den = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(den) < 1e-15:
        return None                     # parallel or collinear
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / den
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / den
    eps = 1e-9
    if not (eps < t < 1.0 - eps and eps < u < 1.0 - eps):
        return None
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def douglas_peucker(points, tol):
    """Simplify a polyline, keeping its endpoints.

    Run **after** welding, never before: removing a vertex that another
    polyline was welded to would silently reopen a region.
    """
    if len(points) < 3 or tol <= 0:
        return list(points)
    a, b = points[0], points[-1]
    worst_i, worst_d = 0, -1.0
    for i in range(1, len(points) - 1):
        d, _t, _q = _point_segment(points[i], a, b)
        if d > worst_d:
            worst_i, worst_d = i, d
    if worst_d <= tol:
        return [a, b]
    left = douglas_peucker(points[:worst_i + 1], tol)
    right = douglas_peucker(points[worst_i:], tol)
    return left[:-1] + right


# ======================================================================
class GeometrySanitiser:
    """Turns raw DXF polylines into geometry that closes into regions."""

    def __init__(self, diagonal: float, weld_pct: float = DEFAULT_WELD_PCT,
                 simplify_pct: float = DEFAULT_SIMPLIFY_PCT,
                 simplify: bool = True) -> None:
        self.diagonal = max(diagonal, 1e-9)
        self.weld_tol = self.diagonal * weld_pct / 100.0
        self.simplify_tol = self.diagonal * simplify_pct / 100.0
        self.simplify = simplify
        self.report = SanitiseReport()

    # ------------------------------------------------------------------
    def run(self, polylines_by_kind: dict) -> dict:
        """Sanitise a ``kind -> [DxfPolyline]`` mapping.

        Returns the repaired mapping; the report is on ``self.report``.
        """
        rep = self.report
        flat = [(k, p) for k, ps in polylines_by_kind.items() for p in ps]
        rep.vertices_before = sum(p.n for _k, p in flat)
        if not flat:
            rep.add_problem("empty", "No geometry was assigned to any "
                                     "layer.")
            return polylines_by_kind

        work = {k: [DxfPolyline(points=list(p.points), closed=p.closed,
                                layer=p.layer, source=p.source,
                                handle=p.handle) for p in ps]
                for k, ps in polylines_by_kind.items()}

        self._merge_vertices(work)
        self._close_external(work)
        self._weld_endpoints(work)
        self._split_crossings(work)
        self._extend_to_external(work)
        if self.simplify:
            self._simplify(work)
        self._validate(work)

        rep.vertices_after = sum(p.n for ps in work.values() for p in ps)
        return work

    # ------------------------------------------------------------------
    def _all(self, work):
        return [p for ps in work.values() for p in ps]

    def _merge_vertices(self, work):
        """Collapse points that coincide within tolerance onto one
        location, quantising to a grid so the result does not depend on
        the order the points are visited in."""
        tol = self.weld_tol
        if tol <= 0:
            return
        reps: dict = {}
        for p in self._all(work):
            for i, pt in enumerate(p.points):
                key = (round(pt[0] / tol), round(pt[1] / tol))
                if key in reps:
                    if _dist(pt, reps[key]) > 1e-15:
                        p.points[i] = reps[key]
                        self.report.merged_vertices += 1
                else:
                    reps[key] = pt
        # Drop the duplicates the merge may have created
        for p in self._all(work):
            clean = [p.points[0]]
            for pt in p.points[1:]:
                if _dist(pt, clean[-1]) > 1e-12:
                    clean.append(pt)
            p.points = clean

    # ------------------------------------------------------------------
    def _close_external(self, work):
        """The external boundary must be closed; if it arrived open, close
        it. This is a documented requirement of the model, not a guess."""
        for p in work.get(DxfEntityKind.EXTERNAL, []):
            if p.n < 3:
                self.report.add_problem(
                    "external", "The external boundary has fewer than "
                                "three vertices.",
                    p.points[0][0] if p.points else None,
                    p.points[0][1] if p.points else None)
                continue
            gap = _dist(p.points[0], p.points[-1])
            if gap > 1e-12:
                p.points.append(p.points[0])
                self.report.closed_boundaries += 1
                if gap > self.weld_tol * 20:
                    # Closing a large gap changes the shape, so say so
                    self.report.add_problem(
                        "external_gap",
                        f"The external boundary was open by {gap:.3f} "
                        f"units and has been closed with a straight "
                        f"segment; check the result.",
                        p.points[0][0], p.points[0][1])
            p.closed = True

    # ------------------------------------------------------------------
    def _weld_endpoints(self, work):
        """Weld free endpoints onto nearby geometry.

        The crucial part: when an endpoint lands near the **interior** of
        another segment it is projected onto it AND a node is inserted in
        that segment. Welding only endpoint-to-endpoint leaves T-junctions
        without a shared node, and those are precisely what stops regions
        from being detected.
        """
        tol = self.weld_tol
        targets = self._all(work)
        for p in self._all(work):
            if p.n < 2:
                continue
            for idx in (0, -1):
                if p.closed:
                    continue
                pt = p.points[idx]
                best = None
                for q in targets:
                    if q is p or q.n < 2:
                        continue
                    for j in range(q.n - 1):
                        a, b = q.points[j], q.points[j + 1]
                        d, t, proj = _point_segment(pt, a, b)
                        if d > tol:
                            continue
                        # NOTE: a distance of exactly zero must NOT be
                        # skipped. An earlier guard rejected d < 1e-15 to
                        # avoid self-contact, but that silently skipped
                        # the cleanest case of all — geometry drawn
                        # correctly in CAD, touching a segment interior
                        # exactly — leaving a T-junction with no shared
                        # node and a region that never closes. Self-
                        # contact is already excluded by ``q is p``.
                        if best is None or d < best[0]:
                            best = (d, q, j, t, proj)
                if best is None:
                    continue
                _d, q, j, t, proj = best
                a, b = q.points[j], q.points[j + 1]
                # Prefer an EXISTING vertex of the target when the
                # projection lands within tolerance of one. Inserting a
                # node a fraction of a unit away from a corner would
                # create a near-degenerate sliver segment, which is worse
                # geometry than snapping to the corner that is already
                # there.
                snap = None
                if _dist(proj, a) <= tol:
                    snap = a
                elif _dist(proj, b) <= tol:
                    snap = b
                if snap is not None:
                    p.points[idx] = snap
                    self.report.welded_endpoints += 1
                    continue
                p.points[idx] = proj
                self.report.welded_endpoints += 1
                # Interior contact -> the target needs a node there,
                # otherwise the junction is geometric only and the region
                # never closes.
                q.points.insert(j + 1, proj)
                self.report.nodes_inserted += 1

    # ------------------------------------------------------------------
    def _split_crossings(self, work):
        """Insert a shared node wherever two polylines properly cross."""
        polys = self._all(work)
        for i, p in enumerate(polys):
            for q in polys[i + 1:]:
                self._split_pair(p, q)

    def _split_pair(self, p, q):
        changed = True
        guard = 0
        while changed and guard < 50:
            changed = False
            guard += 1
            for i in range(p.n - 1):
                for j in range(q.n - 1):
                    x = _segment_intersection(p.points[i], p.points[i + 1],
                                              q.points[j], q.points[j + 1])
                    if x is None:
                        continue
                    p.points.insert(i + 1, x)
                    q.points.insert(j + 1, x)
                    self.report.crossings_split += 1
                    changed = True
                    break
                if changed:
                    break

    # ------------------------------------------------------------------
    def _extend_to_external(self, work):
        """Extend ends that fall just short of the external boundary.

        A material boundary stopping 5 cm before the external boundary
        leaves the region open, and the user cannot see the gap at normal
        zoom. Extension is limited so a genuinely internal feature is not
        dragged across the model.
        """
        ext = work.get(DxfEntityKind.EXTERNAL, [])
        if not ext:
            return
        limit = self.weld_tol * 40.0
        for kind in (DxfEntityKind.MATERIAL, DxfEntityKind.WATER_TABLE,
                     DxfEntityKind.PIEZO, DxfEntityKind.DRAWDOWN):
            for p in work.get(kind, []):
                if p.closed or p.n < 2:
                    continue
                for idx, nb in ((0, 1), (-1, -2)):
                    pt = p.points[idx]
                    on = min((_point_segment(pt, a, b)[0]
                              for e in ext
                              for a, b in zip(e.points, e.points[1:])),
                             default=math.inf)
                    if on <= self.weld_tol or on > limit:
                        continue
                    # Prolong along the end direction until the boundary
                    d = (pt[0] - p.points[nb][0], pt[1] - p.points[nb][1])
                    n = math.hypot(*d)
                    if n < 1e-12:
                        continue
                    step = (d[0] / n, d[1] / n)
                    hit = None
                    far = (pt[0] + step[0] * limit * 2.0,
                           pt[1] + step[1] * limit * 2.0)
                    for e in ext:
                        for a, b in zip(e.points, e.points[1:]):
                            x = _segment_intersection(pt, far, a, b)
                            if x is not None and (
                                    hit is None
                                    or _dist(pt, x) < _dist(pt, hit)):
                                hit = x
                    if hit is not None and _dist(pt, hit) <= limit:
                        p.points[idx] = hit
                        self.report.extended_ends += 1

    # ------------------------------------------------------------------
    def _simplify(self, work):
        """Douglas-Peucker, protecting every point shared with another
        polyline so simplification cannot undo the welding."""
        shared: set = set()
        seen: dict = {}
        q = 1e-9
        for p in self._all(work):
            for pt in p.points:
                key = (round(pt[0] / q), round(pt[1] / q))
                if key in seen and seen[key] is not p:
                    shared.add(key)
                seen[key] = p

        def protected(pt):
            return (round(pt[0] / q), round(pt[1] / q)) in shared

        for p in self._all(work):
            if p.n < 3:
                continue
            # Split the polyline at protected points and simplify each
            # run independently, so shared nodes always survive.
            runs, cur = [], [p.points[0]]
            for pt in p.points[1:]:
                cur.append(pt)
                if protected(pt):
                    runs.append(cur)
                    cur = [pt]
            if len(cur) > 1:
                runs.append(cur)
            out = []
            for run in runs:
                simp = douglas_peucker(run, self.simplify_tol)
                out.extend(simp if not out else simp[1:])
            if len(out) >= 2:
                p.points = out

    # ------------------------------------------------------------------
    def _validate(self, work):
        """Record what remains wrong, without blocking the import: the
        agreed behaviour is to import anyway and let the user correct in
        the editor."""
        rep = self.report
        ext = work.get(DxfEntityKind.EXTERNAL, [])
        if not ext:
            rep.add_problem("external_missing",
                            "No layer was assigned to the external "
                            "boundary; the model cannot define regions "
                            "without one.")
        elif len(ext) > 1:
            areas = [(abs(_signed_area(e.points)), e) for e in ext]
            areas.sort(reverse=True)
            rep.add_problem(
                "external_multiple",
                f"{len(ext)} external boundaries were found; the largest "
                f"will be used and the rest ignored.",
                areas[1][1].points[0][0], areas[1][1].points[0][1])
            work[DxfEntityKind.EXTERNAL] = [areas[0][1]]

        # Free ends left dangling inside the model keep regions open
        tol = self.weld_tol
        allp = self._all(work)
        for kind in (DxfEntityKind.MATERIAL,):
            for p in work.get(kind, []):
                if p.closed or p.n < 2:
                    continue
                for idx in (0, -1):
                    pt = p.points[idx]
                    touching = False
                    for q in allp:
                        if q is p:
                            continue
                        for a, b in zip(q.points, q.points[1:]):
                            if _point_segment(pt, a, b)[0] <= tol * 1.5:
                                touching = True
                                break
                        if touching:
                            break
                    if not touching:
                        rep.add_problem(
                            "dangling_end",
                            "A material boundary end does not reach any "
                            "other boundary, so the region will not "
                            "close.", pt[0], pt[1])


def _signed_area(points) -> float:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        a += x1 * y2 - x2 * y1
    return a / 2.0
