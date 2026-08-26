# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Anisotropic surface — a polyline that says which way the bedding runs.

An anisotropic strength model asks one question of the geometry: what is
the angle between the slice base and the bedding? When the bedding is a
single plane, one number answers it everywhere, and that is what
``AnisotropicLinear.bedding_angle`` and its relatives hold. When the
bedding is FOLDED, the answer changes with position, and a polyline
drawn along the fold is what supplies it.

**The rule, and it is not the rule of a water surface.** For a point in
the model, the bedding orientation is that of the polyline at the point
of the polyline CLOSEST to it — not the point vertically above or below.
That distinction is the whole content of the entity: a water surface is
read straight up, and reading a fold straight up would give the wrong
dip everywhere the fold is steep.

**And when the closest point is a vertex**, the orientation is that of
the segment drawn FIRST — the one earlier in the polyline — and not an
average of the two meeting there. Averaging is the obvious thing and it
is deliberately not done: the angle then belongs to a direction the user
actually drew rather than to one interpolated between two. The visible
consequence is that on a polyline with a sharp kink, drawing it the
other way round can change the answer. That is a property of the model,
not an accident of this implementation, so it is reproduced and tested
rather than smoothed away.

The surface is an independent modelling entity: it is never intersected
with other boundaries, never defines a material region and never reaches
the mesh. It exists only to be asked this question.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from .primitives import Polyline


def _closest_on_segment(px, py, ax, ay, bx, by):
    """Closest point of segment AB to P, as ``(t, qx, qy, d2)``.

    ``t`` is the parameter along AB clamped to [0, 1], so ``t == 0`` and
    ``t == 1`` are exactly the two endpoints — which is what lets the
    caller recognise a vertex hit without a second distance test.
    """
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den <= 0.0:
        return 0.0, ax, ay, (px - ax) ** 2 + (py - ay) ** 2
    t = ((px - ax) * dx + (py - ay) * dy) / den
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    qx, qy = ax + t * dx, ay + t * dy
    return t, qx, qy, (px - qx) ** 2 + (py - qy) ** 2


def closest_segment_index(polyline: Polyline, x: float,
                          y: float) -> Optional[int]:
    """Index of the segment whose closest point to ``(x, y)`` wins.

    Ties go to the LOWER index, which is what implements the
    drawn-first rule: when the closest point is a shared vertex both
    adjoining segments report the same distance, and the earlier one is
    the one the user drew first.

    The tie has to be recognised as a tie rather than left to floating
    point, because the two distances are computed by different
    arithmetic and can differ in the last bit. The tolerance is
    RELATIVE to the model's own size, by the project's rule that a
    geometric tolerance may not read differently in metres and in feet.

    Returns None when the polyline has fewer than two vertices.
    """
    verts = list(getattr(polyline, "vertices", ()) or ())
    if len(verts) < 2:
        return None

    span = max(
        max(v.x for v in verts) - min(v.x for v in verts),
        max(v.y for v in verts) - min(v.y for v in verts),
        1e-12,
    )
    tol2 = (1e-9 * span) ** 2

    best_i = 0
    best_d2 = None
    for i in range(len(verts) - 1):
        a, b = verts[i], verts[i + 1]
        _t, _qx, _qy, d2 = _closest_on_segment(x, y, a.x, a.y, b.x, b.y)
        if best_d2 is None or d2 < best_d2 - tol2:
            best_d2, best_i = d2, i
    return best_i


def segment_angle_deg(polyline: Polyline, index: int) -> float:
    """Orientation of one segment, in degrees, folded to (-90, 90].

    A bedding direction has no sense: dipping 30 degrees one way and 150
    the other are the same plane. The anisotropic models fold the
    difference to 0-90 anyway, but folding here too keeps the value the
    user sees in a report from flipping sign with the drawing order.
    """
    verts = list(getattr(polyline, "vertices", ()) or ())
    a, b = verts[index], verts[index + 1]
    ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
    while ang > 90.0:
        ang -= 180.0
    while ang <= -90.0:
        ang += 180.0
    return ang


def anisotropy_angle_at(polyline: Polyline, x: float,
                        y: float) -> Optional[float]:
    """Bedding orientation at ``(x, y)``, in degrees from horizontal.

    Returns None when the polyline cannot answer — fewer than two
    vertices — so the caller can fall back on the material's own global
    angle instead of silently using zero, which would be a dip nobody
    entered.
    """
    i = closest_segment_index(polyline, x, y)
    if i is None:
        return None
    return segment_angle_deg(polyline, i)
