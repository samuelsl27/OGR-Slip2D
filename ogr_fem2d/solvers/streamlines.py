# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Streamlines of the Darcy velocity on a mesh of linear triangles
(v0.1.332, D329b).

In a T3 element the head is linear, so the Darcy velocity is CONSTANT
inside it: ``SeepageResult.velocity`` holds one vector per element. A
streamline is therefore straight inside each element, and it can be traced
exactly, with no step size: from a point, along the element's velocity, to
the edge where the ray leaves the triangle, and on into the element across
that edge. The only approximation is the field's own, constant by element;
the tracing adds none.

The tracer is checked against a closed-form flow (``tests/
test_streamlines_v1332.py``): the stagnation-point flow of the potential
phi = x^2 - y^2, whose velocity -grad(phi) is (-2x, 2y). Its stream
function is psi = 2xy, the harmonic conjugate of phi by the Cauchy-Riemann
equations (phi and psi are the real and imaginary parts of w = z^2), so its
streamlines are the hyperbolas x*y = constant. A uniform field gives
straight lines.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional


def _min_barycentric(coords, point) -> float:
    """The smallest barycentric coordinate of ``point`` in the triangle
    ``coords``: >= 0 inside or on it, negative outside, by how much."""
    (x1, y1), (x2, y2), (x3, y3) = coords
    px, py = point
    det = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if det == 0.0:
        return -math.inf
    l1 = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / det
    l2 = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / det
    return min(l1, l2, 1.0 - l1 - l2)


def _inside(coords, point, tol=1e-12) -> bool:
    """Whether ``point`` is in the triangle ``coords``, its edges included."""
    return _min_barycentric(coords, point) >= -tol


def _locate(mesh, point) -> Optional[int]:
    """The id of an element containing ``point`` (its edge included)."""
    for e in mesh.elements:
        if _inside(e.coords(mesh), point):
            return e.id
    return None


def _entered(mesh, by_id, point, direction, candidates, size):
    """Of ``candidates``, the element a ray from ``point`` along
    ``direction`` goes into: the one holding best a point a hair's breadth
    along it, by its smallest barycentric coordinate, and holding it.

    Used where the ray leaves through a VERTEX, which several elements
    share, and where the element across the edge it left by is not the one
    it goes on into. Through the inside of an edge the tracer takes the
    element across it, and asks nothing of the geometry: the first version
    probed there too, and a ray leaving almost along its edge put the probe
    a hair inside the element it had left, by rounding (5.7e-8 in, 5.4e-8
    out: 21 of the 22 ends of the first worked example's streamlines).
    """
    dx, dy = direction
    norm = math.hypot(dx, dy)
    if norm <= 0.0:
        return None
    step = 1e-7 * size / norm
    probe = (point[0] + step * dx, point[1] + step * dy)
    best, best_min = None, 0.0
    for i in candidates:
        m = _min_barycentric(by_id[i].coords(mesh), probe)
        if m > best_min:
            best, best_min = i, m
    return best


def _exit(coords, point, v, entry_edge, eps):
    """Where the ray ``point + t*v`` leaves the triangle ``coords``: the
    smallest t > eps over the edges other than ``entry_edge`` (an index
    0..2), as ``(t, edge_index, s)`` with ``s`` the place along the edge
    (0 at its first node, 1 at its second), or None."""
    px, py = point
    vx, vy = v
    best = None
    for k in range(3):
        if k == entry_edge:
            continue
        (ax, ay), (bx, by) = coords[k], coords[(k + 1) % 3]
        ex, ey = bx - ax, by - ay
        denom = vx * ey - vy * ex
        if denom == 0.0:
            continue          # parallel to the edge
        # point + t v = a + s e
        t = ((ax - px) * ey - (ay - py) * ex) / denom
        s = ((ax - px) * vy - (ay - py) * vx) / denom
        if t > eps and -1e-9 <= s <= 1.0 + 1e-9:
            if best is None or t < best[0]:
                best = (t, k, s)
    return best


def _node_elements(mesh) -> dict:
    out: dict = {}
    for e in mesh.elements:
        for n in e.nodes:
            out.setdefault(n, []).append(e.id)
    return out


def _deepest(mesh, by_id, velocity, point, sign, candidates, size):
    """Of ``candidates`` (elements holding ``point``), the one its own
    velocity goes deepest into from there, or None if it leaves them all.

    Strictly into: the probe moves some 1e-7 of an element, so a tolerance
    on the barycentric coordinate as large as that would call a velocity
    that leaves the element one that enters it (the first version did, with
    -1e-6, and never slid along an edge).
    """
    best, deepest = None, 0.0
    for i in candidates:
        vx, vy = velocity[i]
        norm = math.hypot(vx, vy)
        if norm <= 0.0:
            continue
        step = 1e-7 * size / norm
        probe = (point[0] + step * sign * vx, point[1] + step * sign * vy)
        m = _min_barycentric(by_id[i].coords(mesh), probe)
        if m > deepest:
            best, deepest = i, m
    return best


def _trace_one_way(mesh, velocity, start, sign, by_id, around, size,
                   max_segments, edges=None) -> list:
    """The points of the streamline from ``start`` following ``sign *
    velocity``, up to the mesh boundary or a stagnation.

    Where the flow of two elements meets head-on across their edge (the
    normal component of a velocity constant by element is not continuous),
    the line runs ALONG that edge, in the sense of the tangential component
    of the two velocities' mean, to its end, and goes on from that vertex
    into the element its own velocity goes deepest into. Measured on the
    first worked example: without it 19 of the 22 ends of its streamlines
    stopped at such an edge, bouncing between the two elements. A smooth
    field (the tests' closed-form flows) has no such edge.
    """
    points = [start]
    edges = mesh.edge_map() if edges is None else edges
    holding = [e.id for e in mesh.elements if _inside(e.coords(mesh), start)]
    element = _deepest(mesh, by_id, velocity, start, sign, holding, size)
    if element is None:
        return points
    point = start
    eps = 1e-12 * size
    crossed, slid = set(), set()
    for _ in range(max_segments):
        vx, vy = velocity[element]
        vx, vy = sign * vx, sign * vy
        if math.hypot(vx, vy) <= 0.0:
            break             # stagnant: the line ends here
        e = by_id[element]
        hit = _exit(e.coords(mesh), point, (vx, vy), None, eps)
        if hit is None:
            break
        t, k, along_edge = hit
        point = (point[0] + t * vx, point[1] + t * vy)
        points.append(point)
        a, b = e.nodes[k], e.nodes[(k + 1) % 3]
        near = (set(around.get(a, ())) | set(around.get(b, ()))) - {element}
        if 1e-9 < along_edge < 1.0 - 1e-9:
            # out through the inside of an edge: the element across it,
            # or none on the boundary
            key = (a, b) if a < b else (b, a)
            across = [i for i in edges.get(key, ()) if i != element]
            nxt = across[0] if across else None
        else:
            # out through a vertex: the element around it the ray goes into
            node = a if along_edge <= 0.5 else b
            nxt = _entered(mesh, by_id, point, (vx, vy),
                           sorted(set(around.get(node, ())) - {element}),
                           size)
        if nxt is None:
            break             # out through the boundary
        if (element, nxt) in crossed:
            break             # a cycle
        crossed.add((element, nxt))
        if _deepest(mesh, by_id, velocity, point, sign, [nxt],
                    size) is not None:
            element = nxt
            continue
        # through a vertex, rounding can pick a neighbour the line does not
        # go on into: any element holding the point that takes it will do
        holding = [i for i in near
                   if _inside(by_id[i].coords(mesh), point, tol=1e-9)]
        other = _deepest(mesh, by_id, velocity, point, sign, holding, size)
        if other is not None:
            element = other
            continue
        # the next element's flow sends it straight back: slide along the
        # edge they share, to the end its mean flow points to
        key = (a, b) if a < b else (b, a)
        if key in slid:
            break
        slid.add(key)
        (ax, ay), (bx, by) = ((mesh.nodes[a].x, mesh.nodes[a].y),
                              (mesh.nodes[b].x, mesh.nodes[b].y))
        nvx, nvy = velocity[nxt]
        mx, my = (vx + sign * nvx) / 2.0, (vy + sign * nvy) / 2.0
        along = mx * (bx - ax) + my * (by - ay)
        if along == 0.0:
            break             # no flow along it either: a stagnation
        node = b if along > 0.0 else a
        target = (mesh.nodes[node].x, mesh.nodes[node].y)
        if target == point:
            break             # already at that end, and nothing takes it
        point = target
        points.append(point)
        element = _deepest(mesh, by_id, velocity, point, sign,
                           around.get(node, ()), size)
        if element is None:
            break
    return points


def trace_streamline(mesh, velocity, start, *, max_segments: int = 20000,
                     edges=None) -> list:
    """The streamline through ``start``, upstream to downstream, as a list
    of points: one per element crossed, plus its two ends. Empty when
    ``start`` is outside the mesh. (``edges`` is kept for callers that
    built the edge map; the tracer works from the elements around each
    node, which also carries a line through a vertex.)"""
    if _locate(mesh, start) is None:
        return []
    by_id = {e.id: e for e in mesh.elements}
    around = _node_elements(mesh)
    size = math.sqrt(max(mesh.total_area(), 0.0)
                     / max(len(mesh.elements), 1))
    edges = mesh.edge_map() if edges is None else edges
    down = _trace_one_way(mesh, velocity, start, 1.0, by_id, around, size,
                          max_segments, edges)
    up = _trace_one_way(mesh, velocity, start, -1.0, by_id, around, size,
                        max_segments, edges)
    return list(reversed(up[1:])) + down


def seed_points(mesh, velocity, count: int = 10) -> list:
    """Where to start ``count`` streamlines: along the line through the
    mesh's centroid perpendicular to its mean flow, evenly over the mesh's
    extent across that flow, keeping the points inside the mesh."""
    sx = sy = area = cx = cy = 0.0
    for e in mesh.elements:
        a = e.area(mesh)
        vx, vy = velocity[e.id]
        sx += a * vx
        sy += a * vy
        ex, ey = e.centroid(mesh)
        cx += a * ex
        cy += a * ey
        area += a
    norm = math.hypot(sx, sy)
    if area <= 0.0 or norm <= 0.0 or count < 1:
        return []
    cx, cy = cx / area, cy / area
    nx, ny = -sy / norm, sx / norm        # across the mean flow
    across = [(n.x - cx) * nx + (n.y - cy) * ny for n in mesh.nodes]
    lo, hi = min(across), max(across)
    out = []
    for i in range(count):
        s = lo + (i + 0.5) * (hi - lo) / count
        p = (cx + s * nx, cy + s * ny)
        if _locate(mesh, p) is not None:
            out.append(p)
    return out


def streamlines(mesh, velocity, count: int = 10) -> list:
    """``count`` streamlines of the field, at most, as point lists."""
    edges = mesh.edge_map()
    out = []
    for p in seed_points(mesh, velocity, count):
        line = trace_streamline(mesh, velocity, p, edges=edges)
        if len(line) >= 2:
            out.append(line)
    return out
