# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The circular slip surface: an arc of a circle of centre and radius.

v0.1.343 (D337) -- moved word for word from ``ogr_slip2d/surface.py``,
with :func:`ground_y_at`, the one name of that module it used. The project
stores the user's circles and the core rebuilds them on load, so the class
is the core's; ``ogr_slip2d.surface`` re-exports both names, the same
objects, and the other surfaces (composite, polyline, weak layer) stay in
the engine.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from ogr_core.geometry import Polyline, Vertex, envelope_y_at


def ground_y_at(ground: Polyline, x: float,
                upper: bool = True) -> Optional[float]:
    """Elevation of a ground polyline at ``x``, or None outside its span.

    v0.1.114 — delegates to :func:`ogr_core.geometry.envelope_y_at`, because
    a ground profile is no longer strictly increasing in x: a vertical face
    is carried as two vertices sharing an abscissa. This function used to
    return on the FIRST segment spanning ``x`` and to answer the MIDPOINT of
    a vertical one — at the foot of the wall of verification problem 59 that
    is 10 ft between the bench (0) and the crest (20), and neither of them
    is the ground. Pass ``upper=False`` for a profile that came from
    :func:`bedrock_surface`, where a step is worth its bottom end.
    """
    return envelope_y_at(ground, x, upper)


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
    #
    # v0.1.109 — a truncation against the user's Tension Crack BOUNDARY
    # also lands here, because this list is what the canvas draws and the
    # two cracks look identical on screen. What separates them is
    # ``tension_crack_wall`` below: only the modelled one can hold water.
    tension_cracks: list = field(default_factory=list)
    # v0.1.109 — the wall left by the user's Tension Crack boundary,
    # (x, y_bottom, y_top), or None. Kept apart from ``tension_cracks``
    # because the hydrostatic thrust is computed on THIS wall and a
    # reverse-curvature crack is always dry.
    tension_crack_wall: Optional[tuple] = None

    # ------------------------------------------------------------------
    # v0.1.100 — how far ``R² − (x−xc)²`` may go negative and still
    # count as "on the arc". RELATIVE to R², so the same circle in
    # millimetres and in metres answers the same question the same way.
    #
    # It exists because the arc's own extremes, |x − xc| = R, are ordinary
    # places for a ground crossing to fall — a circle whose centre sits at
    # the crest elevation daylights exactly there, with a VERTICAL tangent —
    # and no floating-point x lands on them exactly. On the reference circle
    # of verification problem 23 (Low 1989), centre (18.001, 16.000),
    # R = 15.556, the exit is x = 33.557 and ``33.557 − 18.001`` evaluates to
    # 15.556000000000001: one ulp past R, hence disc = −5.7e−14, hence "not
    # on the circle". The slicer dropped the last slice for that, silently,
    # and Bishop came out 25 % low. See tests/test_tangent_surface_v1100.py.
    _ARC_EPS = 1e-12

    def _lower_arc_disc(self, x: float) -> Optional[float]:
        """``R² − (x−xc)²``, clamped at the extremes. None if outside."""
        dx = x - self.centre_x
        disc = self.radius ** 2 - dx * dx
        if disc < 0.0:
            if disc > -self._ARC_EPS * self.radius ** 2:
                return 0.0
            return None
        return disc

    def base_y_at(self, x: float) -> Optional[float]:
        """Return the y-coordinate of the circle at x (lower arc)."""
        disc = self._lower_arc_disc(x)
        if disc is None:
            return None
        return self.centre_y - math.sqrt(disc)

    def base_angle_at(self, x: float) -> float:
        """Inclination of the base at x [rad].

        Positive angles: base rises to the right (dy/dx > 0).

        v0.1.100 — at the arc's extreme the tangent is VERTICAL, and this
        returned 0.0, i.e. horizontal: the one answer that is not merely
        imprecise but backwards. The old guard was also an ABSOLUTE
        ``disc <= 1e-12``, against the project's rule that geometric
        tolerances scale with the model.
        """
        dx = x - self.centre_x
        disc = self._lower_arc_disc(x)
        if disc is None or disc <= 0.0:
            return math.copysign(math.pi / 2.0, dx) if dx else 0.0
        # y = yc - sqrt(R² - (x-xc)²)  →  dy/dx = (x-xc)/sqrt(...)
        dy_dx = dx / math.sqrt(disc)
        return math.atan(dy_dx)

    def x_range(self) -> tuple[float, float]:
        """Total x-extent of the circle (before ground clipping)."""
        return (self.centre_x - self.radius, self.centre_x + self.radius)

    # ------------------------------------------------------------------
    def kinks(self, x_l: Optional[float] = None,
              x_r: Optional[float] = None) -> list[float]:
        """None: an arc is smooth everywhere, so no cut is mandatory."""
        return []

    def y_span(self, x_l: float,
               x_r: float) -> Optional[tuple[float, float]]:
        """Exact ``(y_min, y_max)`` of the lower arc over ``[x_l, x_r]``.

        The lower arc is convex, so its extremes are the two ends and — when
        the centre's abscissa falls inside the span — the bottom of the
        circle. Three evaluations, exact, no sampling.
        """
        ys = [self.base_y_at(x_l), self.base_y_at(x_r)]
        if x_l <= self.centre_x <= x_r:
            ys.append(self.base_y_at(self.centre_x))
        ys = [y for y in ys if y is not None]
        if not ys:
            return None
        return min(ys), max(ys)

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
                    roots.append(p1.x + t * dx)

        # v0.1.100 — the roots used to be rounded to six decimals so that
        # ``set()`` would collapse the one a shared profile vertex produces
        # twice. Six decimals is plenty of x — but not plenty of y: where the
        # arc is nearly vertical dy/dx runs into the thousands, so 5e−7 of x
        # became 3.4e−4 of y, enough to place the endpoint ABOVE the ground
        # and have the slicer throw the last slice away. Measured on the
        # problem-23 profile with the centre at (18.001, 16.010): one slice
        # lost, FoS 0.93 with 30 slices against 1.19.
        #
        # Duplicates are merged with a tolerance RELATIVE to the circle
        # instead, which collapses the same pairs without spending precision.
        roots.sort()
        merged: list[float] = []
        r_tol = 1e-9 * self.radius
        for x in roots:
            if not merged or x - merged[-1] > r_tol:
                merged.append(x)
        roots = merged
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
