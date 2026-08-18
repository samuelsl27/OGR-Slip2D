# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Water surfaces — the shared vocabulary for "which water level applies here".

A water surface is not a class of its own: it is a ``Boundary`` whose type
is ``WATER_TABLE``, ``PIEZOMETRIC`` or ``DRAWDOWN``. This module is the one
place that knows how to *enumerate*, *name* and *resolve* them, so that the
slicer, the pore-pressure model, the ponding load and the canvas all agree
on the answer instead of each re-deriving it.

**Three different criteria for "which water surface" coexist, and all three
are correct in their own place.** They looked like an inconsistency and are
not; writing them down here is cheaper than rediscovering it a third time:

1. *Pore pressure* uses **the one assigned to the material**
   (``Material.water_surface_id``). Two piezometric lines can describe two
   different aquifers, so u must come from the one the user picked — never
   from whichever happens to be first in the project.
2. *Saturated unit weight* asks whether **any water table** stands above
   the point. γsat is a property of the soil being submerged, not of a
   pressure measurement, so it does not matter which one — only that one
   does. Piezometric lines are excluded on purpose (see ``ponded_water``).
3. *Ponding load* uses **the highest surface over the abscissa**, across
   water tables and drawdown lines together. Free-standing water stacks:
   the load is set by the top of the water body, not by the first polyline
   the loop happens to reach.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..geometry import Boundary, BoundaryType, Polyline

# The boundary types that define a level of water. DRAWDOWN is included
# because it *is* a water level (the reservoir before the drawdown), even
# though it is never the target of a per-material assignment.
WATER_SURFACE_TYPES = (
    BoundaryType.WATER_TABLE,
    BoundaryType.PIEZOMETRIC,
    BoundaryType.DRAWDOWN,
)

# The subset a material may be assigned to as its pore-pressure source.
ASSIGNABLE_WATER_SURFACE_TYPES = (
    BoundaryType.WATER_TABLE,
    BoundaryType.PIEZOMETRIC,
)


# ----------------------------------------------------------------------
def interp_y_on_polyline(polyline: Polyline, x: float) -> Optional[float]:
    """Return y(x) by linear interpolation along a non-closed polyline.

    Returns None if x is outside the x-range of the polyline or the
    polyline is degenerate.

    This lives here rather than in ``pore_pressure`` because four packages
    need it (slicer, ponding, pore pressure, canvas) and importing a
    private name across package boundaries had already forced one lazy
    import to break an import cycle.
    """
    pts = polyline.vertices
    if len(pts) < 2:
        return None
    # Assume roughly left-to-right ordering; handle both directions
    for p1, p2 in zip(pts[:-1], pts[1:]):
        if (p1.x <= x <= p2.x) or (p2.x <= x <= p1.x):
            if abs(p2.x - p1.x) < 1e-12:
                return (p1.y + p2.y) / 2.0
            t = (x - p1.x) / (p2.x - p1.x)
            return p1.y + t * (p2.y - p1.y)
    return None


# ----------------------------------------------------------------------
def water_surfaces(project) -> list[Boundary]:
    """Every water surface a material may be assigned to.

    Water tables first, then piezometric lines, each group in project
    order. The order is what gives piezometric lines their stable
    user-visible number, so it must not depend on a set or a dict.
    """
    out: list[Boundary] = []
    for btype in ASSIGNABLE_WATER_SURFACE_TYPES:
        out.extend(project.boundaries_of(btype))
    return out


def water_surface_index(project, boundary: Boundary) -> int:
    """1-based number of ``boundary`` among the surfaces of its own type.

    Piezometric lines are identified by this number in the interface, so
    it must be derived from project order and nothing else.
    """
    same = project.boundaries_of(boundary.btype)
    for i, b in enumerate(same):
        if b.id == boundary.id:
            return i + 1
    return 0


def water_surface_label(project, boundary: Boundary) -> str:
    """English label for a water surface — for the CLI, logs and DXF.

    The GUI does NOT use this: it composes the translated equivalent from
    ``water_surface_index`` so that every visible string goes through
    ``tr()``.
    """
    n = water_surface_index(project, boundary)
    if boundary.btype == BoundaryType.WATER_TABLE:
        total = len(project.boundaries_of(BoundaryType.WATER_TABLE))
        return "Water Table" if total <= 1 else f"Water Table {n}"
    if boundary.btype == BoundaryType.PIEZOMETRIC:
        return f"Piezometric Line {n}"
    if boundary.btype == BoundaryType.DRAWDOWN:
        return "Drawdown Line"
    return boundary.btype.name


# ----------------------------------------------------------------------
def resolve_water_surface(
    project,
    water_surface_id: Optional[str],
    target_type: BoundaryType,
) -> Optional[Boundary]:
    """Find the water surface a material refers to.

    Falls back to the first surface of ``target_type`` when the material
    carries no assignment. That fallback is a legacy convenience, not a
    model decision: with two or more surfaces of the same type it makes
    the result depend on project order, which is why the interface now
    lets the user assign one explicitly.
    """
    if water_surface_id:
        for b in project.boundaries:
            if b.id == water_surface_id and b.btype == target_type:
                return b
    for b in project.boundaries:
        if b.btype == target_type:
            return b
    return None


def water_surface_y_at(
    project,
    water_surface_id: Optional[str],
    target_type: BoundaryType,
    x: float,
) -> Optional[float]:
    """Elevation of the resolved water surface at ``x``, or None."""
    b = resolve_water_surface(project, water_surface_id, target_type)
    if b is None:
        return None
    return interp_y_on_polyline(b.polyline, x)


def water_surface_defined_at(project, material, x: float) -> bool:
    """Is the water surface this material uses defined over ``x``?

    v0.1.96. ``interp_y_on_polyline`` answers None outside the x-range of a
    polyline, and ``pore_pressure_at`` turned that into ``u = 0`` — a DRY
    slope, silently, on the unsafe side. The reference does the opposite and
    says so twice in its documentation, under both Add Water Table and Add
    Piezometric Surface:

        "the analysis will not be able to calculate the pore pressure for
        slip surfaces where the [surface] is not defined, and a safety
        factor will NOT BE CALCULATED"

    So the two answers have to be told apart: "u = 0 because the water is
    below this point" is a result, and "there is no water surface over this
    abscissa" is a refusal. This function is the second question; the
    slicer asks it per slice and discards the whole surface when it fails.

    Returns True — analysable — when the material does not use a water
    surface at all (Ru, a constant, a finite-element field or none), since
    the question does not arise there.

    A material whose model IS a water surface but which resolves to no
    boundary at all also returns True: that is a project with a model set
    and nothing drawn, which already yields u = 0 everywhere and is a
    different problem from a surface that exists but stops short.
    """
    from ..materials import PorePressureType

    ppt = getattr(material, "pore_pressure", None)
    if ppt == PorePressureType.WATER_TABLE:
        target = BoundaryType.WATER_TABLE
    elif ppt == PorePressureType.PIEZO_LINE:
        target = BoundaryType.PIEZOMETRIC
    else:
        return True

    b = resolve_water_surface(project, getattr(material, "water_surface_id",
                                               None), target)
    if b is None:
        return True
    return interp_y_on_polyline(b.polyline, x) is not None


# ----------------------------------------------------------------------
def water_table_y_at(project, x: float) -> Optional[float]:
    """Elevation of the highest WATER TABLE at ``x``, or None.

    Used where the question is "is this point below the free water
    surface?" rather than "what pressure applies here": the saturated unit
    weight, and the clipping of a pore-pressure grid. Piezometric lines
    are deliberately excluded from both.
    """
    best: Optional[float] = None
    for wb in project.boundaries_of(BoundaryType.WATER_TABLE):
        wy = interp_y_on_polyline(wb.polyline, x)
        if wy is not None and (best is None or wy > best):
            best = wy
    return best
