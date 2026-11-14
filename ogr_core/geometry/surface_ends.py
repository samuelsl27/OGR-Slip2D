# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Where a slip surface meets the ground, in one place (v0.1.447, D424).

Two readers need it: the report's «Global Minimums» block, in the core, and
``ogr_slip2d.interpretation.slope_intercepts``, in the engine, which the
core may not import. The rule lived in the engine alone, so the report
could not ask it and a polyline's ends were never written there. It moved
here word for word, and the engine asks it; one rule, so the two cannot
name different ends.

Only what every surface carries is asked: ``to_dict()`` and ``x_range()``
(the engine's ``SurfaceProtocol``), ``base_y_at`` and, for a polyline, its
vertices.
"""
from __future__ import annotations

from typing import Optional


def surface_x_ends(surface) -> tuple:
    """``(x_left, x_right)`` where ``surface`` meets the ground: its own
    ``x_left`` / ``x_right`` when it records them (a circle, a composite, a
    weak-layer clip), otherwise its ``x_range()``.

    v0.1.201 — ``to_dict().get("x_left") or x_range()`` treated an
    intercept at x = 0.0 as missing and fell back to the circle's centre
    minus its radius; hence the ``is not None``.
    """
    xl, xr = surface.x_range()
    sd = surface.to_dict()
    if sd.get("x_left") is not None:
        xl = sd["x_left"]
    if sd.get("x_right") is not None:
        xr = sd["x_right"]
    return xl, xr


def polyline_points(surface) -> Optional[list]:
    """The vertices ``[(x, y), ...]`` of a polyline surface, in its own
    order, or None for a surface that is not one: a circle, a composite and
    a weak-layer clip carry no ``polyline``."""
    vertices = getattr(getattr(surface, "polyline", None), "vertices", None)
    if not vertices:
        return None
    return [(v.x, v.y) for v in vertices]


def surface_ends(surface) -> tuple:
    """``((x, y), (x, y))``, the left end and the right one.

    A polyline's are its first and last vertex: the engine's polyline
    surface keeps its vertices sorted by x (``SlipSurface.__post_init__``),
    and no door makes a vertical segment (``checked_points`` refuses one),
    so they are the ends of its x range and the vertices on the ground.
    Any other surface: the x of :func:`surface_x_ends` and ``base_y_at``
    there, which is what the report's block always wrote for them.
    """
    pts = polyline_points(surface)
    if pts:
        return pts[0], pts[-1]
    xl, xr = surface_x_ends(surface)
    return (xl, surface.base_y_at(xl)), (xr, surface.base_y_at(xr))
