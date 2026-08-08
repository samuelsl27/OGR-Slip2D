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


def _interp_y(polyline, x: float) -> Optional[float]:
    # Imported lazily to avoid a circular import at module load time.
    from .pore_pressure import _interp_y_on_polyline

    return _interp_y_on_polyline(polyline, x)


# Boundary types whose polyline defines a free water surface. The
# drawdown line is the reservoir level BEFORE the drawdown, which was
# genuinely loading the slope, so it ponds too.
PONDING_BOUNDARY_TYPES = (BoundaryType.WATER_TABLE, BoundaryType.DRAWDOWN)


def ponded_water_level_at(project, x: float) -> Optional[float]:
    """Elevation of the free water surface above ``x``, or None.

    Returns the highest ponding surface defined at that abscissa,
    regardless of whether it lies above or below the ground — the caller
    decides that, since it is the one that knows the ground elevation
    there. Returns None when no ponding surface spans ``x``.
    """
    best: Optional[float] = None
    for btype in PONDING_BOUNDARY_TYPES:
        for wb in project.boundaries_of(btype):
            wy = _interp_y(wb.polyline, x)
            if wy is not None and (best is None or wy > best):
                best = wy
    return best


def ponded_depth_at(project, x: float, ground_y: float) -> float:
    """Depth of ponded water over the ground at ``x``. Zero if none."""
    level = ponded_water_level_at(project, x)
    if level is None:
        return 0.0
    return max(0.0, level - ground_y)
