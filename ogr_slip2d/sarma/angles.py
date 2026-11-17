# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The inclination of the faces between Sarma's wedges.

A face rises from a point of the slip surface into the mass. Its angle θ is
measured counter-clockwise from +x, in degrees from 0 to 360 as the user
gives it (90 is vertical), and only its LINE matters: θ and θ + 180° are the
same face, and the face is the half of the line that rises from the
surface, so θ is brought to (0°, 180°). A horizontal line is no face.

Three policies give θ where nobody gave it, from the two bases that meet at
the point (angles α₁ toward the toe and α₂ toward the head, positive rising
toward +x, lengths l₁ and l₂):

* ``vertical``: θ = 90°, the slices of the vertical methods;
* ``bisector``: the bisector of the angle the two bases make at the point,
  θ = (α₁ + α₂)/2 + 90°; on a straight stretch, the normal to it;
* ``mean_normal``: the direction of l₁·n₁ + l₂·n₂, the two normals
  n = (−sin α, cos α) weighted by the lengths of their bases; the
  bisector when the two are equally long.

None of the three comes from a source: they are geometric choices for
where no angle is given, the vertical one being the vertical methods'
(Sarma 1979, which describes inclined faces, was not consulted). What the
published cases fix is given by vertex, and that is what decides their
numbers (spec 009). Since v0.1.471 the faces can also be optimised
(``OPTIMIZED_MODES``, :mod:`ogr_slip2d.sarma.optimize_angles`).

The solver (:mod:`ogr_slip2d.sarma.solver`) takes δ, the angle from the
vertical, positive when the top of the face leans toward +x: δ = 90° − θ.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

VERTICAL = "vertical"
BISECTOR = "bisector"
MEAN_NORMAL = "mean_normal"
POLICIES = (VERTICAL, BISECTOR, MEAN_NORMAL)

#: v0.1.471 (D357) -- the two values of ``settings.sarma.slice_angles``
#: that optimise the faces instead of taking one policy
#: (:mod:`ogr_slip2d.sarma.optimize_angles`): every surface computed with
#: the bisector and the critical one optimised afterwards, or every surface
#: optimised. The documentation of the reference program describes the
#: two; neither is a policy :func:`policy_angle` knows, so ``build_wedges``
#: still takes only ``POLICIES``.
OPTIMIZED_GLOBAL = "optimized_global"
OPTIMIZED_ALL = "optimized_all"
OPTIMIZED_MODES = (OPTIMIZED_GLOBAL, OPTIMIZED_ALL)
#: Every value ``settings.sarma.slice_angles`` takes.
ANGLE_SETTINGS = POLICIES + OPTIMIZED_MODES

#: A line closer than this to horizontal [rad] is no face: the core's,
#: which the rule of the per-vertex data asks too (v0.1.465).
from ogr_core.geometry.user_polyline import \
    HORIZONTAL_FACE_RAD as _HORIZONTAL  # noqa: E402


def upward(theta_deg: float) -> Optional[float]:
    """The face given at ``theta_deg`` (degrees counter-clockwise from +x,
    any value) as the angle in radians, in (0, π), of its half that rises;
    None for a horizontal line or a non-finite angle."""
    if not math.isfinite(theta_deg):
        return None
    t = math.radians(theta_deg % 180.0)
    if t < _HORIZONTAL or math.pi - t < _HORIZONTAL:
        return None
    return t


def upward_degrees(dx: float, dy: float, decimals: int = 1) -> Optional[float]:
    """θ in degrees, in (0°, 180°), of the face whose line passes through
    the origin and ``(dx, dy)``, rounded to ``decimals``: the angle a face
    is given by pointing at it (v0.1.469, D357, the angle tool of the
    window), whichever side of the vertex the pointer is on. None for a
    horizontal line (after the rounding) or for the origin itself.

    The rounding is what is shown and what is stored: a pointer cannot be
    placed to more than a tenth of a degree, and an angle of fourteen
    digits read off a pixel would claim a precision nobody gave."""
    if not (math.isfinite(dx) and math.isfinite(dy)) or (dx == 0.0
                                                          and dy == 0.0):
        return None
    theta = round(math.degrees(math.atan2(dy, dx)) % 180.0, decimals)
    if theta >= 180.0 or upward(theta) is None:
        return None
    return theta


def policy_angle(policy: str, alpha_toe: float, alpha_head: float,
                 len_toe: float = 1.0, len_head: float = 1.0) -> float:
    """θ in radians, in (0, π), of the face that ``policy`` puts between a
    base of angle ``alpha_toe`` (rad, the one toward −x) and one of angle
    ``alpha_head`` (toward +x), of lengths ``len_toe`` and ``len_head``.

    Raises ValueError on an unknown policy.
    """
    if policy == VERTICAL:
        return 0.5 * math.pi
    if policy == BISECTOR:
        return 0.5 * (alpha_toe + alpha_head) + 0.5 * math.pi
    if policy == MEAN_NORMAL:
        nx = -len_toe * math.sin(alpha_toe) - len_head * math.sin(alpha_head)
        ny = len_toe * math.cos(alpha_toe) + len_head * math.cos(alpha_head)
        return math.atan2(ny, nx)
    raise ValueError("angle policy must be one of %s, not %r"
                     % (POLICIES, policy))


def delta_of(theta: float) -> float:
    """δ of the solver [rad] for the face at θ [rad]: from the vertical,
    positive when its top leans toward +x."""
    return 0.5 * math.pi - theta
