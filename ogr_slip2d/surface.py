# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slip-surface geometry.

A slip surface is the potential failure path whose Factor of Safety
we evaluate. OGR Slip2D supports two geometric families:

    - :class:`SlipCircle`  — arc defined by centre + radius
    - :class:`SlipSurface` — arbitrary polyline (non-circular)

Both produce the same public API (``intersect_with_ground``,
``base_y_at``, ``base_angle_at``) so the slicer can treat them uniformly.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Protocol
from uuid import uuid4

from ogr_core.geometry import Polyline, Vertex


# ----------------------------------------------------------------------
class SurfaceProtocol(Protocol):
    """Minimum interface every slip geometry must satisfy."""

    def base_y_at(self, x: float) -> Optional[float]: ...
    def base_angle_at(self, x: float) -> float: ...
    def x_range(self) -> tuple[float, float]: ...
    def to_dict(self) -> dict: ...


# ----------------------------------------------------------------------
@dataclass
class SlipCircle:
    """Circular slip surface: arc of circle (centre_x, centre_y, R).

    Only the lower half of the circle is used (y = yc - sqrt(R² - (x-xc)²))
    because failure surfaces in slope problems always open upward.
    """

    centre_x: float
    centre_y: float
    radius: float
    x_left: Optional[float] = None    # intersection with ground surface (left)
    x_right: Optional[float] = None   # intersection with ground surface (right)
    id: str = field(default_factory=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    def base_y_at(self, x: float) -> Optional[float]:
        """Return the y-coordinate of the circle at x (lower arc)."""
        dx = x - self.centre_x
        disc = self.radius ** 2 - dx ** 2
        if disc < 0:
            return None
        return self.centre_y - math.sqrt(disc)

    def base_angle_at(self, x: float) -> float:
        """Inclination of the base at x [rad].

        Positive angles: base rises to the right (dy/dx > 0).
        """
        dx = x - self.centre_x
        disc = self.radius ** 2 - dx ** 2
        if disc <= 1e-12:
            return 0.0
        # y = yc - sqrt(R² - (x-xc)²)  →  dy/dx = (x-xc)/sqrt(...)
        dy_dx = dx / math.sqrt(disc)
        return math.atan(dy_dx)

    def x_range(self) -> tuple[float, float]:
        """Total x-extent of the circle (before ground clipping)."""
        return (self.centre_x - self.radius, self.centre_x + self.radius)

    # ------------------------------------------------------------------
    def intersect_with_ground(self, ground: Polyline) -> tuple[float, float] | None:
        """Find the two intersection x-coordinates with the ground polyline.

        The LEM solver uses only the *lower* arc of the circle as the
        failure surface; hence we require the chord between the two
        intersection points to span a region where the lower arc lies
        *below* the ground surface.

        Returns (x_left, x_right) or None if no valid chord is found.
        """
        roots: list[tuple[float, float]] = []  # (x, y) pairs
        for p1, p2 in zip(ground.vertices[:-1], ground.vertices[1:]):
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            a = dx * dx + dy * dy
            if a < 1e-14:
                continue
            b = 2 * ((p1.x - self.centre_x) * dx + (p1.y - self.centre_y) * dy)
            c = (
                (p1.x - self.centre_x) ** 2
                + (p1.y - self.centre_y) ** 2
                - self.radius ** 2
            )
            disc = b * b - 4 * a * c
            if disc < 0:
                continue
            sq = math.sqrt(disc)
            for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
                if -1e-9 <= t <= 1 + 1e-9:
                    x = p1.x + t * dx
                    y = p1.y + t * dy
                    roots.append((x, y))

        if len(roots) < 2:
            return None
        # Deduplicate on x and sort left→right
        roots_sorted = sorted(set((round(x, 6), round(y, 6))
                                  for x, y in roots))
        if len(roots_sorted) < 2:
            return None

        # v0.1.18 — pick the FIRST consecutive pair of crossings whose
        # interior arc lies below the ground. The previous code took the
        # extreme pair (first, last), which is only correct for
        # "composite" surfaces. With non-composite circular surfaces
        # (Slide "Composite Surfaces: Disabled"), the slip surface must
        # daylight at the FIRST re-emergence. On a benched/footed slope
        # the circle can dip below the toe bench and cross the flat
        # ground again much further right (x≈100 instead of the true
        # exit x≈74.8); taking the extreme pair grossly overestimates
        # the sliding mass and the FoS.
        def _ground_y(xq: float):
            for q1, q2 in zip(ground.vertices[:-1], ground.vertices[1:]):
                if (q1.x <= xq <= q2.x) or (q2.x <= xq <= q1.x):
                    if abs(q2.x - q1.x) < 1e-12:
                        return 0.5 * (q1.y + q2.y)
                    t = (xq - q1.x) / (q2.x - q1.x)
                    return q1.y + t * (q2.y - q1.y)
            return None

        chosen = None
        for k in range(len(roots_sorted) - 1):
            xa = roots_sorted[k][0]
            xb = roots_sorted[k + 1][0]
            if xb - xa < 1e-6:
                continue
            x_mid = 0.5 * (xa + xb)
            arc_y = self.base_y_at(x_mid)
            gy = _ground_y(x_mid)
            if arc_y is None or gy is None:
                continue
            if arc_y <= gy + 1e-6:
                chosen = (xa, xb)
                break
        if chosen is None:
            return None
        x_l, x_r = chosen

        self.x_left, self.x_right = x_l, x_r
        return self.x_left, self.x_right

    def _legacy_intersect_tail(self, ground, x_l, x_r):
        # (retained for reference; no longer used)
        x_mid = 0.5 * (x_l + x_r)
        arc_y = self.base_y_at(x_mid)
        if arc_y is None:
            return None
        ground_y_mid = None
        for q1, q2 in zip(ground.vertices[:-1], ground.vertices[1:]):
            if (q1.x <= x_mid <= q2.x) or (q2.x <= x_mid <= q1.x):
                if abs(q2.x - q1.x) < 1e-12:
                    ground_y_mid = 0.5 * (q1.y + q2.y)
                else:
                    t = (x_mid - q1.x) / (q2.x - q1.x)
                    ground_y_mid = q1.y + t * (q2.y - q1.y)
                break
        if ground_y_mid is None or arc_y > ground_y_mid + 1e-6:
            return None

        self.x_left, self.x_right = x_l, x_r
        return self.x_left, self.x_right

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "type": "circle",
            "id": self.id,
            "centre_x": self.centre_x,
            "centre_y": self.centre_y,
            "radius": self.radius,
            "x_left": self.x_left,
            "x_right": self.x_right,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlipCircle":
        c = cls(
            centre_x=data["centre_x"],
            centre_y=data["centre_y"],
            radius=data["radius"],
            x_left=data.get("x_left"),
            x_right=data.get("x_right"),
        )
        if "id" in data:
            c.id = data["id"]
        return c

    @classmethod
    def from_three_points(cls, a: Vertex, b: Vertex, c: Vertex) -> "SlipCircle":
        """Build the unique circle passing through three non-collinear points."""
        ax, ay = a.x, a.y
        bx, by = b.x, b.y
        cx, cy = c.x, c.y
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-14:
            raise ValueError("Three points are collinear; no unique circle")
        ux = (
            (ax ** 2 + ay ** 2) * (by - cy)
            + (bx ** 2 + by ** 2) * (cy - ay)
            + (cx ** 2 + cy ** 2) * (ay - by)
        ) / d
        uy = (
            (ax ** 2 + ay ** 2) * (cx - bx)
            + (bx ** 2 + by ** 2) * (ax - cx)
            + (cx ** 2 + cy ** 2) * (bx - ax)
        ) / d
        r = math.hypot(ax - ux, ay - uy)
        return cls(centre_x=ux, centre_y=uy, radius=r)


# ----------------------------------------------------------------------
@dataclass
class SlipSurface:
    """Arbitrary (non-circular) slip surface.

    Represented as a polyline sorted by ascending x. The solver assumes
    the surface is single-valued in y(x) — a reasonable restriction for
    real slope-failure geometries.
    """

    polyline: Polyline
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        # Enforce left-to-right ordering
        self.polyline.vertices.sort(key=lambda v: v.x)

    def base_y_at(self, x: float) -> Optional[float]:
        verts = self.polyline.vertices
        if not verts or x < verts[0].x or x > verts[-1].x:
            return None
        for p1, p2 in zip(verts[:-1], verts[1:]):
            if p1.x <= x <= p2.x:
                if abs(p2.x - p1.x) < 1e-12:
                    return (p1.y + p2.y) / 2.0
                t = (x - p1.x) / (p2.x - p1.x)
                return p1.y + t * (p2.y - p1.y)
        return None

    def base_angle_at(self, x: float) -> float:
        verts = self.polyline.vertices
        for p1, p2 in zip(verts[:-1], verts[1:]):
            if p1.x <= x <= p2.x:
                if abs(p2.x - p1.x) < 1e-12:
                    return math.pi / 2
                return math.atan((p2.y - p1.y) / (p2.x - p1.x))
        return 0.0

    def x_range(self) -> tuple[float, float]:
        verts = self.polyline.vertices
        return (verts[0].x, verts[-1].x) if verts else (0.0, 0.0)

    def to_dict(self) -> dict:
        return {
            "type": "polyline",
            "id": self.id,
            "polyline": self.polyline.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlipSurface":
        s = cls(polyline=Polyline.from_dict(data["polyline"]))
        if "id" in data:
            s.id = data["id"]
        return s
