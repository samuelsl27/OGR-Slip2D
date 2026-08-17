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
def ground_y_at(ground: Polyline, x: float) -> Optional[float]:
    """Elevation of a ground polyline at ``x``, or None outside its span."""
    for q1, q2 in zip(ground.vertices[:-1], ground.vertices[1:]):
        if (q1.x <= x <= q2.x) or (q2.x <= x <= q1.x):
            if abs(q2.x - q1.x) < 1e-12:
                return 0.5 * (q1.y + q2.y)
            t = (x - q1.x) / (q2.x - q1.x)
            return q1.y + t * (q2.y - q1.y)
    return None


# ----------------------------------------------------------------------
def leaves_soil_region(circle: "SlipCircle", external_vertices: list,
                       x_l: float, x_r: float) -> bool:
    """True when the arc between ``x_l`` and ``x_r`` leaves the soil.

    The reference states the rule plainly under *Grid Search*: "if a
    circular surface extends past the lower limits of the External
    Boundary, the surface is discarded, and is not analyzed", and its
    report counts those surfaces under error code −103 — "two surface /
    slope intersections, but one or more surface / nonslope external
    polygon intersections lie between them. This usually occurs when the
    slip surface extends past the bottom of the soil region."

    ``x_l`` and ``x_r`` are consecutive GROUND crossings, so by
    construction the arc meets no ground between them. Any further
    intersection of the *lower* arc with the external polygon strictly
    inside the chord is therefore an intersection with a non-ground part
    of the boundary — the floor or a side — and the mass it would enclose
    is not made of soil.

    Only the lower arc is tested: the upper arc is not the slip surface.
    Disabled by the caller when Composite Surfaces is on, which is exactly
    what that option means — the surface then follows the boundary instead
    of being rejected by it.
    """
    from ogr_core.geometry.ground import upper_y_at

    n = len(external_vertices)
    if n < 3 or x_r - x_l < 1e-9:
        return False
    # Relative to the chord: the same model in millimetres and in metres
    # must reject and accept the same surfaces.
    span = x_r - x_l
    tol = 1e-6 * max(span, circle.radius)

    for i in range(n):
        p1 = external_vertices[i]
        p2 = external_vertices[(i + 1) % n]
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        a = dx * dx + dy * dy
        if a < 1e-14:
            continue
        b = 2 * ((p1.x - circle.centre_x) * dx + (p1.y - circle.centre_y) * dy)
        c = ((p1.x - circle.centre_x) ** 2
             + (p1.y - circle.centre_y) ** 2
             - circle.radius ** 2)
        disc = b * b - 4 * a * c
        if disc < 0:
            continue
        sq = math.sqrt(disc)
        for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
            if not (-1e-9 <= t <= 1 + 1e-9):
                continue
            x = p1.x + t * dx
            if x <= x_l + tol or x >= x_r - tol:
                continue
            y = p1.y + t * dy
            arc_y = circle.base_y_at(x)
            if arc_y is None or abs(y - arc_y) > tol:
                continue          # meets the UPPER arc, not the surface
            gy = upper_y_at(external_vertices, x)
            if gy is not None and abs(gy - y) <= tol:
                continue          # a ground crossing after all
            return True
    return False


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
    # v0.1.82 — reverse-curvature tension cracks. Empty unless
    # ``apply_reverse_curvature`` has moved an endpoint to the vertical
    # tangent; each entry is (x, y_bottom, y_top) of a vertical crack.
    tension_cracks: list = field(default_factory=list)

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
    def candidate_chords(self, ground: Polyline) -> list[tuple[float, float]]:
        """Every sliding mass this circle defines against ``ground``.

        The LEM solver uses only the *lower* arc of the circle, so a mass
        exists between two consecutive ground crossings whenever the arc
        between them runs BELOW the ground surface. A circle that crosses
        the ground more than twice therefore defines several **disjoint**
        masses, and they are all returned here, left to right.

        Consecutive pairs only, never the extreme pair: on a benched or
        footed slope the circle dips under the toe bench and crosses the
        flat ground again much further right, and joining the first
        crossing to the last would span a stretch where the arc is out in
        the open air.
        """
        roots: list[float] = []
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
                    roots.append(round(p1.x + t * dx, 6))

        roots = sorted(set(roots))
        out: list[tuple[float, float]] = []
        for k in range(len(roots) - 1):
            xa, xb = roots[k], roots[k + 1]
            if xb - xa < 1e-6:
                continue
            x_mid = 0.5 * (xa + xb)
            arc_y = self.base_y_at(x_mid)
            gy = ground_y_at(ground, x_mid)
            if arc_y is None or gy is None:
                continue
            if arc_y <= gy + 1e-6:
                out.append((xa, xb))
        return out

    def intersect_with_ground(self, ground: Polyline) -> tuple[float, float] | None:
        """Resolve the circle onto its FIRST sliding mass, left to right.

        Kept as the default single-chord resolution for callers that only
        want a surface to draw or to slice. A search must not use this on
        its own: when a circle defines more than one mass the first one is
        not necessarily the critical one — see
        :meth:`BaseSearch.evaluate_circle`, which evaluates them all.

        Returns (x_left, x_right) or None if no valid chord is found.
        """
        chords = self.candidate_chords(ground)
        if not chords:
            return None
        self.x_left, self.x_right = chords[0]
        return self.x_left, self.x_right

    # ------------------------------------------------------------------
    def apply_reverse_curvature(
        self, ground: Polyline, mode: str = "tension_crack"
    ) -> bool:
        """Resolve a *reverse curvature* circle. Returns False to discard.

        A circle whose ground entry (or exit) point lies **above its own
        centre** has part of its arc above the centre elevation, so the
        arc reverses direction: travelling along it from that point the
        x-coordinate first DECREASES to ``x_c − R`` and then increases
        again. Such a surface overhangs, and cannot exist.

        The reference program (Grid Search documentation, "Reverse
        Curvature Surfaces") offers exactly two treatments, and this
        method implements both:

        ``"tension_crack"``
            A **vertical tension crack** is created where the surface
            begins to reverse, i.e. where the surface elevation equals
            the centre elevation. On a circle that is the point of
            vertical tangency, ``x = x_c ∓ R`` — which is why the arc
            appears to run all the way to the boundary at 90°. The
            endpoint is moved there and the crack recorded.

        ``"discard"``
            The surface is rejected (returns False).

        The crack created here is **always dry**: it is a geometric
        consequence of the search, not a modelled feature, so no
        hydrostatic thrust is applied to it. A crack the user wants to
        fill with water is a Tension Crack *boundary*, handled by
        :func:`ogr_slip2d.slicer._apply_tension_crack`.

        Both ends are tested independently, so the treatment does not
        depend on the declared failure direction: whichever end of the
        chord daylights above ``centre_y`` is the one that reverses.
        """
        self.tension_cracks = []
        if self.x_left is None or self.x_right is None:
            return True
        # Necessary condition from the reference: the centre must lie
        # below the highest ground point, otherwise no part of the arc
        # can be above it. Cheap, and it skips the common case.
        try:
            if self.centre_y >= max(v.y for v in ground.vertices):
                return True
        except ValueError:
            return True

        reversed_any = False
        for end in ("left", "right"):
            x_end = self.x_left if end == "left" else self.x_right
            gy = ground_y_at(ground, x_end)
            if gy is None or gy <= self.centre_y + 1e-9:
                continue
            reversed_any = True
            if mode != "tension_crack":
                return False
            x_crack = (self.centre_x - self.radius if end == "left"
                       else self.centre_x + self.radius)
            top = ground_y_at(ground, x_crack)
            if top is None or top <= self.centre_y + 1e-9:
                # The vertical-tangency point is outside the ground
                # profile (or below it): there is nowhere to put the
                # crack, so the surface is not usable either way.
                return False
            if end == "left":
                self.x_left = x_crack
            else:
                self.x_right = x_crack
            self.tension_cracks.append((x_crack, self.centre_y, top))

        if reversed_any and self.x_right - self.x_left < 1e-6:
            return False
        return True

    @property
    def reverse_curvature(self) -> bool:
        """True when a reverse-curvature tension crack was created."""
        return bool(self.tension_cracks)

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
            # v0.1.82 — the canvas needs the crack to draw the vertical
            # segment, and Export Raw Data needs it to be honest about
            # where the surface really starts.
            "tension_cracks": [list(t) for t in self.tension_cracks],
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
        c.tension_cracks = [tuple(t) for t in data.get("tension_cracks", [])]
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


# ----------------------------------------------------------------------
def moment_axis(surface, override=None) -> tuple[float, float]:
    """The point about which moment equilibrium is taken.

    A circle has one by definition: its centre. A polyline does not, and a
    moment method needs one anyway — which is why the reference program
    carries an explicit *Add Axis* option, described in its documentation as
    "a single axis point, which will be used for moment equilibrium
    calculations", and calculates one automatically per surface when the user
    has not placed it.

    ``override`` is that user-placed point, and wins for every surface.

    The automatic construction was NOT documented anywhere; it was measured
    from the reference's own output. A non-circular result reports ``xc, yc,
    r`` in its Global Minimum block, and those fields are the axis:

        chord = exit - entry
        axis  = midpoint(chord) + rot90(chord)        rot90: (x, y) -> (-y, x)

    Checked against the two reference surfaces (v0.1.92):

        Ej_1  built (82.5, 72.5)   reported (82.500000825, 72.500000825)
        Ej_2  built (2.5, 105.0)   reported (2.50000105, 105.00000105)

    to 1.2e-6 and 1.5e-6. The residual is the SAME shift in x and y in both
    cases, about 6.3e-9 of the model diagonal — noise from its own geometry
    code, not a different construction.

    The ``r`` it reports alongside is the MEAN distance from the axis to the
    surface vertices, which is a display value: it is not the distance to the
    endpoints (48.09 against the reported 47.21 in Ej_1), so it is not the
    radius of any circle through them.
    """
    if override is not None:
        return float(override[0]), float(override[1])
    if isinstance(surface, SlipCircle):
        return surface.centre_x, surface.centre_y
    verts = list(getattr(getattr(surface, "polyline", None), "vertices", ()))
    if len(verts) < 2:
        return 0.0, 0.0
    x0, y0 = verts[0].x, verts[0].y
    x1, y1 = verts[-1].x, verts[-1].y
    dx, dy = x1 - x0, y1 - y0
    return 0.5 * (x0 + x1) - dy, 0.5 * (y0 + y1) + dx
