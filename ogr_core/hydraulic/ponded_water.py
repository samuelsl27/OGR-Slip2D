# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Ponded water — free-standing water resting on the slope.

When a water surface is drawn ABOVE the external boundary, the region
between the two is a body of still water sitting on the ground. It is not
a pore-pressure device: it is a load, and it acts on the slope in two ways
that are really one, because both are components of the same hydrostatic
pressure normal to the ground surface (see
``ogr_slip2d.slicer._apply_ponded_water`` for the decomposition).

**Only the water table and the rapid-drawdown line create it.** A
piezometric line drawn above the ground does not, and that is deliberate
rather than an oversight: a piezometric line records a pressure head
measured somewhere in the ground, so drawing it above the surface says
nothing about water standing there. This is one of the three documented
differences between the two entities — the others being that only a water
table allows a separate saturated unit weight, and that only a water table
combines with a pore-pressure grid.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..geometry import BoundaryType
from .water_surfaces import interp_y_on_polyline as _interp_y


# Boundary types whose polyline defines a free water surface.
#
# v0.1.69 — the drawdown line is NOT one of them, and it used to be. It
# is the reservoir level AFTER the drawdown, so letting it pond alongside
# the water table and keeping the highest of the two meant the
# post-drawdown analysis carried the weight of the reservoir it had just
# emptied. When the drawdown level does pond — and it does, whenever it
# still stands above the slope — it is because
# ``drawdown_levels.level_project`` has made it the water table for that
# stage. One surface states the reservoir at a time.
PONDING_BOUNDARY_TYPES = (BoundaryType.WATER_TABLE,)


# Groundwater methods whose water level is defined by the seepage
# boundary conditions rather than by a drawn polyline.
_FEA_METHODS = ("fea_steady", "fea_transient")


def _fea_ponding_runs(project) -> list:
    """The prescribed water bodies, one list of ``(x, H)`` per body.

    v0.1.65 — with a finite-element seepage analysis the reservoir is not
    drawn, it is *prescribed*: there is standing water wherever the total
    head applied to the boundary exceeds the elevation of the boundary
    itself. Reading it from the boundary conditions is the only way for
    the stability analysis to see the same reservoir the seepage analysis
    was solved with; drawing a water table on top would be a second,
    independent statement of the same fact, free to disagree with it.

    v0.1.125 — grouped into **contiguous runs of the mesh boundary**
    instead of one globally sorted list. A single sorted list cannot tell
    a reservoir from a tailwater on the far side of a dam, and the code
    that consumed it then ramped from one to the other straight across
    the downstream face. See :func:`_fea_level_at` for what that cost.

    The boundary condition stores a node id, so this needs the mesh too.
    Both are serialised with the project, so it survives a save.

    ``bc_type`` and ``boundary_edges`` are duck-typed on purpose:
    ``ogr_core`` must not import ``ogr_fem2d``, and the existing coupling
    (the FEM pore-pressure field) is duck-typed for the same reason.
    """
    bcs = getattr(project, "seepage_bcs", None)
    mesh = getattr(project, "fem_mesh", None)
    if bcs is None or mesh is None:
        return []
    nodes = getattr(mesh, "nodes", None)
    bc_nodes = getattr(bcs, "nodes", None)
    if not nodes or not bc_nodes:
        return []

    # v0.1.125 — the signature has to include the VALUES, not just the
    # sizes. It used to be ``(id(bcs), len(bc_nodes), id(mesh),
    # len(nodes))``, on the argument that "the mesh and the conditions
    # are rebuilt wholesale when either changes". They are not:
    # ``add_node`` replaces one entry inside the SAME list of the SAME
    # object, so lowering a reservoir over the same nodes changes neither
    # an id nor a length. Measured: prescribing 24.41 and then 12.0 on
    # the same two nodes kept answering 24.41 — twelve metres of water
    # column too much, on the unsafe side and in silence. And that is not
    # a corner case: a drawdown IS "the same target with a lower level".
    #
    # A tuple over the conditions is O(number of conditions) once per
    # call, against a solve that is orders of magnitude dearer; and the
    # runs it protects cost a pass over the boundary edges.
    key = (id(mesh), len(nodes),
           tuple((b.node_id, getattr(b.bc_type, "value", b.bc_type),
                  b.value) for b in bc_nodes))
    cached = getattr(project, "_fea_ponding_cache", None)
    if cached is not None and cached[0] == key:
        return cached[1]

    wet: dict = {}
    n_nodes = len(nodes)
    for b in bc_nodes:
        i = b.node_id
        if i < 0 or i >= n_nodes:
            continue
        nd = nodes[i]
        t = getattr(b.bc_type, "value", b.bc_type)
        if t == "total_head":
            head = b.value
        elif t == "pressure_head":
            head = nd.y + b.value
        elif t == "zero_pressure":
            head = nd.y
        else:
            continue  # Neumann and seepage faces prescribe no level
        if head > nd.y:
            wet[i] = head

    runs = [[(nodes[i].x, wet[i]) for i in group]
            for group in _connected_runs(mesh, wet)]
    for r in runs:
        r.sort()
    project._fea_ponding_cache = (key, runs)
    return runs


def _connected_runs(mesh, wet: dict) -> list:
    """The wet node ids split into groups connected along the boundary.

    Two submerged nodes belong to the same body of water only if one can
    be reached from the other without leaving the wetted part of the
    boundary. Without the mesh topology there is no honest way to tell,
    so a mesh that cannot report its boundary edges falls back to a
    single group — which is what the code did before this existed, and
    is still safe because :func:`_fea_level_at` no longer extrapolates.
    """
    if not wet:
        return []
    edges_fn = getattr(mesh, "boundary_edges", None)
    if edges_fn is None:
        return [sorted(wet)]
    nbr: dict = {}
    for u, v in edges_fn():
        if u in wet and v in wet:
            nbr.setdefault(u, []).append(v)
            nbr.setdefault(v, []).append(u)
    seen: set = set()
    groups: list = []
    for start in sorted(wet):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        group = []
        while stack:
            cur = stack.pop()
            group.append(cur)
            for nxt in nbr.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        groups.append(sorted(group))
    return groups


def _fea_ponding_polyline(project) -> list:
    """All the prescribed wet points, sorted. Kept for callers that only
    want to know whether any water is prescribed at all."""
    out: list = []
    for run in _fea_ponding_runs(project):
        out.extend(run)
    out.sort()
    return out


def _fea_level_at(project, x: float) -> Optional[float]:
    """Prescribed water level at ``x``, or None where none is prescribed.

    **The level is never extrapolated past the ends of a water body, and
    never interpolated across the gap between two of them.** Until
    v0.1.125 it was both, and the argument in this docstring for why that
    was harmless —"between two reservoirs at different levels this ramps
    from one to the other, and it does not matter because the ground
    between them stands above both"— is true only for a dam with water on
    BOTH sides. As soon as one side is an exposed face the last wet node
    is partway up the upstream slope, and the old rule answered with the
    reservoir level for every abscissa beyond it: on the verification
    dam of problem 102 that put seventeen metres of standing water on the
    downstream slope and multiplied the factor of safety by 3.7, in the
    unsafe direction and in silence.

    The drawn water surfaces had always answered this correctly —
    ``interp_y_on_polyline`` returns None outside its own x-range — so
    the two routes disagreed about the same question and this was the one
    that was wrong. They now agree.
    """
    best: Optional[float] = None
    for run in _fea_ponding_runs(project):
        h = _level_in_run(run, x)
        if h is not None and (best is None or h > best):
            best = h
    return best


def _level_in_run(run: list, x: float) -> Optional[float]:
    """Water level at ``x`` inside one body of water, or None outside it."""
    if not run:
        return None
    if x < run[0][0] or x > run[-1][0]:
        return None
    if len(run) == 1:
        return run[0][1]
    for (x1, h1), (x2, h2) in zip(run[:-1], run[1:]):
        if x1 <= x <= x2:
            if abs(x2 - x1) < 1e-12:
                return max(h1, h2)
            t = (x - x1) / (x2 - x1)
            return h1 + t * (h2 - h1)
    return None


def ponded_water_level_at(project, x: float) -> Optional[float]:
    """Elevation of the free water surface above ``x``, or None.

    Returns the highest ponding surface defined at that abscissa,
    regardless of whether it lies above or below the ground — the caller
    decides that, since it is the one that knows the ground elevation
    there. Returns None when no ponding surface spans ``x``.
    """
    # One pass over the boundaries instead of one ``boundaries_of`` call
    # per ponding type: this runs once per slice, and each of those calls
    # built a fresh list only to iterate it once.
    best: Optional[float] = None
    for wb in project.boundaries:
        if wb.btype not in PONDING_BOUNDARY_TYPES:
            continue
        wy = _interp_y(wb.polyline, x)
        if wy is not None and (best is None or wy > best):
            best = wy

    # v0.1.65 — a seepage analysis prescribes its own reservoir. Combined
    # with the drawn surfaces by the same "highest wins" rule the loop
    # above uses, so a project that already had a water table drawn keeps
    # whatever ponding it had.
    if project.settings.groundwater.method in _FEA_METHODS:
        h = _fea_level_at(project, x)
        if h is not None and (best is None or h > best):
            best = h
    return best


def ponded_depth_at(project, x: float, ground_y: float) -> float:
    """Depth of ponded water over the ground at ``x``. Zero if none."""
    level = ponded_water_level_at(project, x)
    if level is None:
        return 0.0
    return max(0.0, level - ground_y)
