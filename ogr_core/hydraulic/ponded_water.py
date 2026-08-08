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


# Boundary types whose polyline defines a free water surface. The
# drawdown line is the reservoir level BEFORE the drawdown, which was
# genuinely loading the slope, so it ponds too.
PONDING_BOUNDARY_TYPES = (BoundaryType.WATER_TABLE, BoundaryType.DRAWDOWN)


# Groundwater methods whose water level is defined by the seepage
# boundary conditions rather than by a drawn polyline.
_FEA_METHODS = ("fea_steady", "fea_transient")


def _fea_ponding_polyline(project) -> list:
    """(x, H) for every Dirichlet boundary node standing above its own y.

    v0.1.65 — with a finite-element seepage analysis the reservoir is not
    drawn, it is *prescribed*: there is standing water wherever the total
    head applied to the boundary exceeds the elevation of the boundary
    itself. Reading it from the boundary conditions is the only way for
    the stability analysis to see the same reservoir the seepage analysis
    was solved with; drawing a water table on top would be a second,
    independent statement of the same fact, free to disagree with it.

    The boundary condition stores a node id, so this needs the mesh too.
    Both are serialised with the project, so it survives a save.

    ``bc_type`` is compared by its string value on purpose: ``ogr_core``
    must not import ``ogr_fem2d``, and the existing coupling (the FEM
    pore-pressure field) is duck-typed for the same reason.
    """
    bcs = getattr(project, "seepage_bcs", None)
    mesh = getattr(project, "fem_mesh", None)
    if bcs is None or mesh is None:
        return []
    nodes = getattr(mesh, "nodes", None)
    bc_nodes = getattr(bcs, "nodes", None)
    if not nodes or not bc_nodes:
        return []

    # Cheap signature: the mesh and the conditions are rebuilt wholesale
    # when either changes, so their sizes and identities pin the pair.
    key = (id(bcs), len(bc_nodes), id(mesh), len(nodes))
    cached = getattr(project, "_fea_ponding_cache", None)
    if cached is not None and cached[0] == key:
        return cached[1]

    pts: list = []
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
            pts.append((nd.x, head))
    pts.sort()
    project._fea_ponding_cache = (key, pts)
    return pts


def _fea_level_at(project, x: float) -> Optional[float]:
    """Prescribed water level at ``x``, interpolated between wet nodes.

    Between two reservoirs at different levels — headwater and tailwater
    across a dam — this ramps from one to the other, which is not a real
    water surface. It does not matter: the ground between them stands
    above both, and ``ponded_depth_at`` clips the depth at zero there.
    """
    pts = _fea_ponding_polyline(project)
    if not pts:
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x1, h1), (x2, h2) in zip(pts[:-1], pts[1:]):
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
