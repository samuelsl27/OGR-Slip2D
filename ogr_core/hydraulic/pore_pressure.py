# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Pore-pressure computation at an arbitrary point in the model.

Implements the different pore-pressure models used by the LEM solver:
    - NONE              → u = 0
    - WATER_TABLE       → u = γw · h  (h = head above the point)
    - PIEZO_LINE        → u = γw · (piezo_elevation - point.y)
    - RU_COEFFICIENT    → u = Ru · γ · z  (z = depth below surface)
    - CONSTANT          → u = constant

All returns are in kPa.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from typing import Optional

from ..geometry import Boundary, BoundaryType, Polyline, Vertex
from ..materials import Material, PorePressureType
from ..project import Project

GAMMA_WATER_DEFAULT = 9.81  # kN/m³


# ----------------------------------------------------------------------
def _interp_y_on_polyline(polyline: Polyline, x: float) -> Optional[float]:
    """Return y(x) by linear interpolation along a non-closed polyline.

    Returns None if x is outside the x-range of the polyline or the
    polyline is degenerate.
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


def _auto_hu_at(polyline: Polyline, x: float) -> float:
    """Compute the Auto Hu coefficient for a Water Surface at column x.

    Per Slide's Water_Parameters.htm: Hu = cos²(α), where α is the
    inclination of the water-surface segment above the slice base.
    For a horizontal water table α = 0 → Hu = 1.0.

    Returns Hu ∈ [0, 1]. Returns 1.0 if α cannot be determined.
    """
    import math
    pts = polyline.vertices
    if len(pts) < 2:
        return 1.0
    for p1, p2 in zip(pts[:-1], pts[1:]):
        if (p1.x <= x <= p2.x) or (p2.x <= x <= p1.x):
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            if abs(dx) < 1e-12:
                return 0.0  # vertical segment, α = 90°
            alpha = math.atan2(dy, dx)
            cos_a = math.cos(alpha)
            return max(0.0, min(1.0, cos_a * cos_a))
    return 1.0


# ----------------------------------------------------------------------
def pore_pressure_at(
    project: Project,
    point: Vertex,
    material: Optional[Material],
    ground_surface_y: Optional[float] = None,
) -> float:
    """Compute pore pressure u [kPa] at `point` for `material`.

    Args:
        project: the parent project (provides water surfaces).
        point: location where u is sought.
        material: the material containing that point (None → 0).
        ground_surface_y: y-coordinate of the ground above `point`;
            required only for the Ru model.

    Returns:
        Pore pressure in kPa (always ≥ 0; suction is clamped to zero).
    """
    if material is None:
        return 0.0

    gamma_w = project.settings.groundwater.pore_fluid_unit_weight
    ppt = material.pore_pressure

    # v0.1.23 — Water Pressure Grid (Phase 0 of the groundwater plan).
    # When the project-level groundwater method is one of the GRID_*
    # types and a grid is defined, the grid governs the pore pressure
    # by default for every material — including those left at the NONE
    # default — mirroring the reference behaviour where selecting a
    # grid method makes the grid the global water source. Materials
    # with an explicit per-material override (CONSTANT or RU) keep it.
    _gw_method = project.settings.groundwater.method
    if (
        _gw_method in ("grid_total_head", "grid_pressure_head",
                       "grid_pore_pressure")
        and getattr(project, "water_pressure_grid", None) is not None
        and ppt not in (PorePressureType.CONSTANT,
                        PorePressureType.RU_COEFFICIENT)
    ):
        u = project.water_pressure_grid.pore_pressure_at(
            point.x, point.y, gamma_w)
        if u is not None:
            return u
        return 0.0

    if ppt == PorePressureType.NONE:
        return 0.0

    if ppt == PorePressureType.CONSTANT:
        return max(0.0, material.constant_u)

    if ppt == PorePressureType.RU_COEFFICIENT:
        if ground_surface_y is None:
            return 0.0
        depth = max(0.0, ground_surface_y - point.y)
        # u = ru · γ · z, where γ is the total unit weight of the
        # overburden. v0.1.60 — this goes through ``gamma_at`` rather than
        # reading ``sat_unit_weight`` directly so that a material which has
        # NOT opted into a saturated unit weight cannot have that unused
        # number change its pore pressure through a back door.
        return material.ru * material.gamma_at(True) * depth

    if ppt in (PorePressureType.WATER_TABLE, PorePressureType.PIEZO_LINE):
        # Find the referenced water surface
        wid = material.water_surface_id
        target_type = (
            BoundaryType.WATER_TABLE
            if ppt == PorePressureType.WATER_TABLE
            else BoundaryType.PIEZOMETRIC
        )
        water_boundary: Optional[Boundary] = None

        if wid:
            for b in project.boundaries:
                if b.id == wid and b.btype == target_type:
                    water_boundary = b
                    break

        # Fallback: pick the first matching water surface in the project
        if water_boundary is None:
            for b in project.boundaries:
                if b.btype == target_type:
                    water_boundary = b
                    break

        if water_boundary is None:
            return 0.0

        water_y = _interp_y_on_polyline(water_boundary.polyline, point.x)
        if water_y is None:
            return 0.0
        h = water_y - point.y
        if h <= 0:
            return 0.0  # water below the point → suction → zero

        # v0.1.7 — Hu coefficient (per Slide Water_Parameters.htm).
        # By default the material's own Hu is used; if Auto Hu is on
        # at the project level OR the material requests Auto, we
        # compute Hu = cos²(α), where α is the inclination of the
        # water-surface segment above the point.
        gw_settings = project.settings.groundwater
        material_hu = getattr(material, "hu", None)
        material_auto_hu = getattr(material, "auto_hu", False)
        use_auto = material_auto_hu or gw_settings.auto_hu
        if use_auto:
            hu = _auto_hu_at(water_boundary.polyline, point.x)
        elif material_hu is not None:
            hu = float(material_hu)
        else:
            hu = gw_settings.default_hu

        hu = max(0.0, min(1.0, hu))
        u_steady = gamma_w * hu * h

        # v0.1.8 — Rapid Drawdown excess pore pressure (B-bar method).
        # If Rapid Drawdown is enabled in Project Settings and a
        # Drawdown Line exists, compute:
        #     Δu = B̄ · γ_w · (y_drawdown - y_wt)
        # added to u_steady. Only adds positive excess (drawdown
        # lowers the water → effective stress increases → +Δu).
        if (gw_settings.rapid_drawdown
                and gw_settings.rapid_drawdown_method == "b_bar"):
            b_bar = getattr(material, "b_bar", None)
            if b_bar is None:
                b_bar = 1.0  # full transfer (conservative default)
            drawdown = None
            for b in project.boundaries:
                if b.btype == BoundaryType.DRAWDOWN:
                    drawdown = b
                    break
            if drawdown is not None and b_bar > 0:
                y_dd = _interp_y_on_polyline(drawdown.polyline, point.x)
                if y_dd is not None and y_dd > water_y:
                    delta_u = b_bar * gamma_w * (y_dd - water_y)
                    return u_steady + delta_u

        return u_steady

    # v0.1.28 — FEM_SEEPAGE: interpolate the pore pressure from the
    # converged seepage field. The result is stored on the project by
    # the groundwater run; the T3 shape functions give the value at the
    # slice base midpoint (Mesh.interpolate is exact for linear fields).
    # Negative values (matric suction) are returned AS IS here — the
    # unsaturated policy (phi_b / air entry value) is applied by the
    # slicer, so it stays in one place for all LEM methods.
    if ppt == PorePressureType.FEM_SEEPAGE:
        mesh = getattr(project, "fem_mesh", None)
        result = getattr(project, "seepage_result", None)
        if mesh is None or result is None:
            return 0.0
        vals = getattr(result, "pore_pressure", None)
        if not vals:
            return 0.0
        u = mesh.interpolate(vals, point.x, point.y)
        if u is None or not math.isfinite(u):
            # Outside the mesh (e.g. a slice base just off the domain):
            # fall back to dry rather than to a wrong extrapolation.
            return 0.0
        return u

    return 0.0
