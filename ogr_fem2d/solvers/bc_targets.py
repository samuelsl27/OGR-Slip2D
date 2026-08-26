# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Where a seepage boundary condition goes — geometric targets on the mesh
boundary.

Until v0.1.125 a condition could only be applied to one of four whole
sides (left edge, right edge, bottom edge, and *the entire ground
surface*). That is enough for a slope with one water level and not enough
for anything with a reservoir: prescribing "total head = 24.41" on the
whole ground surface puts the reservoir on the crest and on the far side
of the dam as well. The reference lets the user pick individual boundary
segments or nodes with the mouse; this module is the same freedom
expressed as geometry, so a script can state it too.

The central idea is the **wetted perimeter**. A reservoir is not a set of
node ids, it is one number — a level — plus the side it stands on. Walking
the boundary inward from that side and taking nodes while the ground stays
at or below the level yields exactly the submerged part of the boundary,
and the drawdown is the same call with a lower level. That is why this is
a function of ``(level, side)`` and not a picking tool: the thing that
changes between the stages of a drawdown is one number.

Everything here is pure: a mesh in, node ids out. No project, no Qt, no
solver state.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Iterable

#: Which end of the model a reservoir stands on.
SIDE_LEFT = "left"
SIDE_RIGHT = "right"


# ----------------------------------------------------------------------
def boundary_cycle(mesh) -> list[int]:
    """The boundary node ids in order, walked as a closed loop.

    ``Mesh.boundary_edges`` returns an unordered set of edges; a run
    along the boundary is only well defined once they are chained. The
    walk starts at the lowest-numbered node of the loop containing it and
    follows unvisited edges.

    Returns an empty list when the boundary is not a single simple loop
    (a node with other than two boundary edges — a pinch point, or a mesh
    with a hole). Refusing is deliberate: a half-walked boundary would
    silently apply a reservoir to part of a face.
    """
    edges = mesh.boundary_edges()
    if not edges:
        return []
    nbr: dict[int, list[int]] = {}
    for u, v in edges:
        nbr.setdefault(u, []).append(v)
        nbr.setdefault(v, []).append(u)
    if any(len(v) != 2 for v in nbr.values()):
        return []

    start = min(nbr)
    order = [start]
    prev, cur = None, start
    while True:
        a, b = nbr[cur]
        nxt = a if a != prev else b
        if nxt == start:
            break
        order.append(nxt)
        prev, cur = cur, nxt
        if len(order) > len(nbr):       # pragma: no cover - guarded above
            return []
    if len(order) != len(nbr):
        return []
    return order


# ----------------------------------------------------------------------
def _side_nodes(mesh, cycle: list[int], side: str) -> set:
    """The nodes of the vertical edge at one end of the model."""
    xs = [mesh.nodes[i].x for i in cycle]
    x_target = min(xs) if side == SIDE_LEFT else max(xs)
    tol = max(1e-9, 1e-6 * ((max(xs) - min(xs)) or 1.0))
    return {i for i in cycle if abs(mesh.nodes[i].x - x_target) <= tol}


def _impassable(mesh, cycle: list[int], side: str) -> set:
    """Boundary nodes a reservoir's wetted perimeter may never cross.

    The base of the model and the FAR end of it. Both are stops, and the
    reason is the same: water resting on the slope touches the ground
    surface, and the base is not ground surface — it is the impermeable
    cut the model was drawn on.

    Until this was written the only thing keeping the walk off the base
    was that it usually met a node above the water first. That holds for
    a reservoir well below the crest and fails in two ordinary cases,
    both measured: a level that reaches the highest point of the ground
    between the two ends (the walk crosses the crest, comes down the far
    face, runs the whole base and returns — 174 of 174 nodes), and a
    model whose extreme is a single vertex instead of a vertical cut, so
    that both directions are open and one of them IS the base (66 of 130
    nodes, 63 of them on the foundation). In both, ``apply_reservoir``
    then prescribed total head along an impermeable boundary.
    """
    ys = [mesh.nodes[i].y for i in cycle]
    xs = [mesh.nodes[i].x for i in cycle]
    y_min = min(ys)
    tol_y = max(1e-9, 1e-6 * ((max(ys) - y_min) or 1.0))
    tol_x = max(1e-9, 1e-6 * ((max(xs) - min(xs)) or 1.0))
    x_far = max(xs) if side == SIDE_LEFT else min(xs)
    return {i for i in cycle
            if abs(mesh.nodes[i].y - y_min) <= tol_y
            or abs(mesh.nodes[i].x - x_far) <= tol_x}


def wetted_nodes(mesh, level: float, side: str = SIDE_LEFT,
                 *, include_side_edge: bool = True) -> list[int]:
    """Boundary nodes submerged by a reservoir at ``level`` on ``side``.

    The wetted perimeter is the part of the boundary the water actually
    touches: the vertical cut at that end of the model, and the ground
    surface inward from it for as long as the ground stays at or below
    the level. **The walk stops at the first node above the level, at the
    base of the model and at its far end** — see :func:`_impassable` for
    why the last two have to be said explicitly rather than left to the
    first of them.

    ``include_side_edge`` prescribes the reservoir on the vertical cut as
    well. On by default because that face is genuinely under water — the
    model is a truncation of a wider reservoir — but a model that treats
    the cut as a no-flow symmetry boundary turns it off, and the two give
    different fields. **The corner where the cut meets the ground is kept
    either way**: it belongs to both, and dropping it would open a gap at
    the very start of the wetted run.

    A reservoir standing exactly at a vertex elevation includes that
    vertex, so a level set to the top of the upstream face reaches it.
    """
    cycle = boundary_cycle(mesh)
    if not cycle:
        return []
    lvl = float(level)
    tol = _elevation_tolerance(mesh)
    edge = _side_nodes(mesh, cycle, side)
    if not edge:
        return []
    blocked = _impassable(mesh, cycle, side) - edge
    submerged_edge = (sorted(i for i in edge
                             if mesh.nodes[i].y <= lvl + tol)
                      if include_side_edge else [])

    # Enter the ground surface at the TOP of the vertical cut, which is
    # the corner where the two meet. Starting at the bottom corner would
    # let the walk leave along the base of the model.
    entry = max(edge, key=lambda i: mesh.nodes[i].y)
    if mesh.nodes[entry].y > lvl + tol:
        # The reservoir does not reach the ground at this end: only the
        # submerged part of the cut itself is wet.
        return submerged_edge

    keep = set(submerged_edge)
    keep.add(entry)
    n = len(cycle)
    k0 = cycle.index(entry)
    for step in (1, -1):
        # Only the direction that leaves the vertical cut behind.
        if cycle[(k0 + step) % n] in edge:
            continue
        k = k0
        while True:
            k = (k + step) % n
            nid = cycle[k]
            if nid in edge or nid in keep or nid in blocked:
                break
            if mesh.nodes[nid].y > lvl + tol:
                break
            keep.add(nid)
    return sorted(keep)


def _elevation_tolerance(mesh) -> float:
    """Elevation tolerance, relative to the model — never absolute.

    The same number must not mean different things in metres and in
    millimetres, which is the convention the geometry side of this
    project has followed since v0.1.11.
    """
    ys = [nd.y for nd in mesh.nodes]
    if not ys:
        return 1e-9
    span = max(ys) - min(ys)
    return max(1e-12, 1e-9 * (span or 1.0))


# ----------------------------------------------------------------------
def apply_reservoir(bcs, mesh, level: float, side: str = SIDE_LEFT,
                    *, unknown_elsewhere: bool = False,
                    include_side_edge: bool = True) -> list[int]:
    """Prescribe a reservoir at ``level`` on ``side``: total head on the
    wetted perimeter.

    Returns the node ids that were assigned, so a caller can report how
    much of the boundary the level actually reached — a reservoir that
    silently touched two nodes is the failure this returns a list to
    prevent.

    With ``unknown_elsewhere`` the rest of the ground surface is set to
    ``UNKNOWN`` (the seepage face), which is what an exposed face is once
    the reservoir no longer covers it. Left off by default: overwriting
    conditions the user did not ask about is not this function's job.
    """
    from .seepage import BCType

    ids = wetted_nodes(mesh, level, side,
                       include_side_edge=include_side_edge)
    for nid in ids:
        bcs.add_node(nid, BCType.TOTAL_HEAD, float(level))
    if unknown_elsewhere:
        wet = set(ids)
        for nid in _ground_surface_nodes(mesh):
            if nid not in wet:
                bcs.add_node(nid, BCType.UNKNOWN, 0.0)
    return ids


def _ground_surface_nodes(mesh) -> Iterable[int]:
    """Boundary nodes that are not on the left, right or bottom edge —
    the same classification ``default_boundary_conditions`` uses, kept
    here rather than imported so this module stays free of the solver."""
    bnd = sorted(mesh.boundary_node_ids())
    if not bnd:
        return []
    xs = [mesh.nodes[i].x for i in bnd]
    ys = [mesh.nodes[i].y for i in bnd]
    x_min, x_max, y_min = min(xs), max(xs), min(ys)
    tol = max(1e-6, 1e-4 * max(x_max - x_min, 1.0))
    return [nid for nid in bnd
            if not (abs(mesh.nodes[nid].x - x_min) <= tol
                    or abs(mesh.nodes[nid].x - x_max) <= tol
                    or abs(mesh.nodes[nid].y - y_min) <= tol)]
