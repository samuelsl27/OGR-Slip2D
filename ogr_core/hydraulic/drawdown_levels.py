# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The two reservoir levels of a rapid drawdown, and which line is which.

**The water table is the INITIAL (full reservoir) level and the drawdown
line is the FINAL, lower one.** That is the convention of the reference
and of every published case — Pilarcitos runs from y = 72 down to 37,
Morgenstern's slope from 100 down to 50 or 0, the Corps' Appendix G
example from 103 down to 24.

This module exists because the convention was stated in two places and
they disagreed. Until v0.1.69 the B-bar model required the drawdown line
to sit ABOVE the water table, while the multi-stage procedures required
the opposite; at B̄ = 1 the mismatch cancelled against three other defects
and returned the factor of safety from BEFORE the drawdown. Now every
procedure asks the same function which level is which, so there is only
one answer to keep right.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
from typing import Optional

from ..geometry import BoundaryType
from .water_surfaces import interp_y_on_polyline


def drawdown_boundary(project):
    """The drawdown line, or None. At most one is allowed per model."""
    for b in project.boundaries:
        if b.btype == BoundaryType.DRAWDOWN:
            return b
    return None


def level_project(project, use_drawdown: bool):
    """A copy of the project whose water table is one of the two levels.

    The user's project is never touched: the procedures need to analyse
    the same geometry at two different reservoir levels, and both the pore
    pressures and the ponding load follow the water table.

    ``use_drawdown=False`` gives the initial state and simply drops the
    drawdown line, which must not pond in it. ``True`` gives the final
    one: the drawdown line is promoted to water table and the original
    water table removed, so everything downstream — pore pressure, ponded
    load, saturated unit weight, mandatory slice cuts — sees the reservoir
    where it ended up, with no second surface free to disagree.

    No drawdown line at all means TOTAL drawdown: no water left, which is
    the reference's convention for an undefined final level.
    """
    p = copy.copy(project)
    p.boundaries = list(project.boundaries)
    if not use_drawdown:
        p.boundaries = [b for b in p.boundaries
                        if b.btype != BoundaryType.DRAWDOWN]
        return p

    drawdown = drawdown_boundary(project)
    kept = [b for b in p.boundaries
            if b.btype not in (BoundaryType.WATER_TABLE,
                               BoundaryType.DRAWDOWN)]
    if drawdown is not None:
        moved = copy.copy(drawdown)
        moved.btype = BoundaryType.WATER_TABLE
        kept.append(moved)
    p.boundaries = kept
    return p


def levels_at(project, x: float) -> tuple[Optional[float], Optional[float]]:
    """(initial, final) reservoir elevation at ``x``, either may be None.

    The final level is None when there is no drawdown line, which the
    caller must read as total drawdown rather than as "unknown" — see
    :func:`level_project`.
    """
    initial = None
    for b in project.boundaries:
        if b.btype != BoundaryType.WATER_TABLE:
            continue
        y = interp_y_on_polyline(b.polyline, x)
        # Several water tables can coexist (materials may be assigned to
        # different ones); the reservoir is the highest of them, which is
        # the same rule the ponding load uses.
        if y is not None and (initial is None or y > initial):
            initial = y
    dd = drawdown_boundary(project)
    final = interp_y_on_polyline(dd.polyline, x) if dd is not None else None
    return initial, final


def drawdown_line_is_inverted(project) -> bool:
    """True when the drawdown line sits above the water table.

    Sampled at the drawdown line's own vertices rather than at one point,
    because the two surfaces can cross: a model where they do is not a
    drawdown model at all, and answering "inverted" for it would send the
    v0.1.69 migration to swap two lines that mean neither level.
    """
    dd = drawdown_boundary(project)
    if dd is None:
        return False
    above = below = 0
    for v in dd.polyline.vertices:
        initial, final = levels_at(project, v.x)
        if initial is None or final is None:
            continue
        if final > initial + 1e-9:
            above += 1
        elif final < initial - 1e-9:
            below += 1
    return above > 0 and below == 0
