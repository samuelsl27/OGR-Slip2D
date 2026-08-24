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

from ogr_core.geometry import Polyline, Vertex, envelope_y_at


# ----------------------------------------------------------------------
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

    # v0.1.111 — the two questions the slicer used to answer for itself with
    # ``isinstance`` and a peek at ``.polyline``. A surface knows where it
    # bends and how deep it goes; the slicer does not, and a third geometry
    # made that gap a defect rather than a wart (see ``CompositeSurface``).
    def kinks(self, x_l: Optional[float] = None,
              x_r: Optional[float] = None) -> list[float]: ...
    def y_span(self, x_l: float,
               x_r: float) -> Optional[tuple[float, float]]: ...


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
    # v0.1.109 — see :class:`SlipCircle`. Error code −119 of the
    # reference exists precisely because a non-circular surface meets a
    # tension crack the same way a circular one does.
    tension_cracks: list = field(default_factory=list)
    tension_crack_wall: Optional[tuple] = None

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

    # ------------------------------------------------------------------
    def kinks(self, x_l: Optional[float] = None,
              x_r: Optional[float] = None) -> list[float]:
        """Its own vertices, strictly inside the span.

        Every one is a mandatory slice cut: a slice base belongs to one
        segment of the surface or to another, never to a blend, and a slice
        straddling a vertex gets a base angle that is neither of the two
        real ones. What that cost is recorded in ``_slice_boundaries``: a
        0.14 m near-vertical step invisible inside a 1.26 m slice, and
        Block Search returning 0.821 on a slope whose circular minimum is
        1.124.

        The 1e-9 margin is ABSOLUTE, which the project's own rule says it
        should not be. It is kept exactly as it was because this method was
        extracted from the slicer, not rewritten: changing the margin here
        changes which surfaces are cut and therefore every non-circular
        number in the suite.
        """
        lo = -math.inf if x_l is None else x_l + 1e-9
        hi = math.inf if x_r is None else x_r - 1e-9
        return [v.x for v in self.polyline.vertices if lo < v.x < hi]

    def y_span(self, x_l: float,
               x_r: float) -> Optional[tuple[float, float]]:
        """Exact ``(y_min, y_max)`` over ``[x_l, x_r]``.

        A polyline is not convex, so its interior vertices can sit outside
        the envelope of the two ends and all of them have to be looked at.
        """
        ys = [self.base_y_at(x_l), self.base_y_at(x_r)]
        ys = [y for y in ys if y is not None]
        if not ys:
            return None
        lo, hi = min(ys), max(ys)
        for v in self.polyline.vertices:
            if x_l <= v.x <= x_r:
                lo = min(lo, v.y)
                hi = max(hi, v.y)
        return lo, hi

    def to_dict(self) -> dict:
        return {
            "type": "polyline",
            "id": self.id,
            "polyline": self.polyline.to_dict(),
            # v0.1.109 — the vertical wall a tension crack leaves. The
            # polyline itself is already truncated, so without this the
            # drawing would stop in mid-air.
            "tension_cracks": [list(t) for t in self.tension_cracks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SlipSurface":
        s = cls(polyline=Polyline.from_dict(data["polyline"]))
        if "id" in data:
            s.id = data["id"]
        s.tension_cracks = [tuple(t) for t in data.get("tension_cracks", [])]
        return s


# ----------------------------------------------------------------------
@dataclass
class CompositeSurface:
    """A circular arc clipped to the FLOOR of the model.

    Composite Surfaces, in the words of the reference program's own help: a
    circular surface that "extends past the lower limits of the External
    Boundary" is not discarded but made to "conform to the shape of the
    External Boundary, between the two circle intersection points along the
    lower edge". Which is to say the surface is, at every abscissa, the
    higher of the arc and the floor::

        base_y(x) = max(arc(x), floor(x))

    Written as a maximum rather than as "arc, then floor, then arc" on
    purpose: that phrasing needs the arc to dip below exactly once, and a
    shaped bedrock horizon — which is the whole reason the option exists —
    can be crossed any number of times. The maximum reduces to the
    documented three-piece surface when there is one dip, generalises with
    no special cases, and states the mechanics directly: the floor
    constrains the surface from BELOW and nowhere else, so where the arc
    comes back up into the soil the arc is the surface again.

    NOT a subclass of :class:`SlipCircle`, and that is the design decision
    of the whole class. The four moment methods dispatch on
    ``isinstance(surface, SlipCircle)`` to the classical circular formula,
    which divides the radius out of every term because every base normal
    points at the centre. On the linear stretches it does not: the normal
    is offset from the centre and has a moment of its own — the ``Σ N·f``
    term of Fredlund and Krahn (1977), which is exactly the term their
    general formulation carries so that composite surfaces can be solved at
    all. A composite therefore takes the general moment balance of
    :mod:`ogr_slip2d.moment_balance`, about the centre of its own circle;
    :func:`moment_axis` is what hands it that centre.

    Measured on the composite surface of verification problem 22 — Fredlund
    and Krahn (1977), a 1 ft weak layer along the floor of the model and a
    published circle that dips 5 ft below it — 40 slices, dry case, against
    what that manual publishes::

        moment axis            Ordinary  Bishop   Spencer   GLE
        polyline auto-axis      -0.31 %  -1.84 %  +0.13 %  +0.13 %
        centre of the circle    +0.23 %  +0.08 %  +0.10 %  +0.11 %

    ``bedrock`` is the LOWER envelope of the external boundary
    (:func:`ogr_core.geometry.bedrock_surface`), never a material boundary:
    the option is defined against the External Boundary alone, and a
    bedrock horizon is modelled by shaping its lower edge.
    """

    circle: SlipCircle
    bedrock: Polyline
    x_left: Optional[float] = None
    x_right: Optional[float] = None
    id: str = field(default_factory=lambda: str(uuid4()))
    # Both inherited from the circle the composite was built from: the
    # reverse-curvature crack and the user's Tension Crack wall are decided
    # before the clipping and are not changed by it.
    tension_cracks: list = field(default_factory=list)
    tension_crack_wall: Optional[tuple] = None

    # ------------------------------------------------------------------
    # The circle's own geometry, readable straight off the composite. It is
    # what the reported centre and radius of the surface are, and what the
    # moment axis is; the arc itself is always evaluated THROUGH ``circle``
    # so that the one-ulp handling of ``_lower_arc_disc`` (v0.1.100) stays
    # in a single place.
    @property
    def centre_x(self) -> float:
        return self.circle.centre_x

    @property
    def centre_y(self) -> float:
        return self.circle.centre_y

    @property
    def radius(self) -> float:
        return self.circle.radius

    # ------------------------------------------------------------------
    def _tol(self) -> float:
        """Elevation tolerance, RELATIVE to the circle it was built from."""
        return 1e-12 * max(self.radius, 1e-300)

    def _bedrock_y_at(self, x: float) -> Optional[float]:
        # The FLOOR of the model, so a vertical step there is worth its
        # bottom end and not its top.
        return ground_y_at(self.bedrock, x, upper=False)

    def follows_bedrock_at(self, x: float) -> bool:
        """True where the FLOOR is the slip surface and not the arc."""
        arc = self.circle.base_y_at(x)
        floor = self._bedrock_y_at(x)
        if floor is None:
            return False
        if arc is None:
            return True
        return floor > arc + self._tol()

    # ------------------------------------------------------------------
    def base_y_at(self, x: float) -> Optional[float]:
        """``max(arc, floor)`` — see the class docstring."""
        arc = self.circle.base_y_at(x)
        floor = self._bedrock_y_at(x)
        if arc is None:
            return floor
        if floor is None:
            return arc
        return floor if floor > arc else arc

    def base_angle_at(self, x: float) -> float:
        """Inclination of whichever branch is the surface at ``x`` [rad].

        The arc wins ties, and that matters at one place worth naming: the
        two endpoints are GROUND crossings, so the arc is the surface
        there, and ``daylight_tangent_note`` reads the angle there to
        decide whether the surface leaves the ground too steeply for a
        fixed slice count to resolve.
        """
        if not self.follows_bedrock_at(x):
            return self.circle.base_angle_at(x)
        verts = self.bedrock.vertices
        for p1, p2 in zip(verts[:-1], verts[1:]):
            if p1.x <= x <= p2.x and abs(p2.x - p1.x) > 1e-12:
                return math.atan((p2.y - p1.y) / (p2.x - p1.x))
        return 0.0

    def x_range(self) -> tuple[float, float]:
        if self.x_left is not None and self.x_right is not None:
            return (self.x_left, self.x_right)
        return self.circle.x_range()

    # ------------------------------------------------------------------
    def _transitions(self) -> list[float]:
        """Abscissae where the arc meets the floor, i.e. where it changes.

        Solved segment by segment against the circle rather than sampled: a
        transition is a MANDATORY slice cut, and a cut found by sampling
        moves when the sampling does.
        """
        out: list[float] = []
        verts = self.bedrock.vertices
        cx, cy, r = self.centre_x, self.centre_y, self.radius
        tol = 1e-9 * max(r, 1e-300)
        for p1, p2 in zip(verts[:-1], verts[1:]):
            dx, dy = p2.x - p1.x, p2.y - p1.y
            a = dx * dx + dy * dy
            if a < 1e-14 or abs(dx) < 1e-12:
                continue          # a vertical step is not a crossing
            b = 2 * ((p1.x - cx) * dx + (p1.y - cy) * dy)
            c = (p1.x - cx) ** 2 + (p1.y - cy) ** 2 - r * r
            disc = b * b - 4 * a * c
            if disc < 0.0:
                continue
            sq = math.sqrt(disc)
            for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
                if not (-1e-9 <= t <= 1 + 1e-9):
                    continue
                x = p1.x + t * dx
                y = p1.y + t * dy
                arc_y = self.circle.base_y_at(x)
                # The UPPER arc can cut the floor too, and it is not the
                # slip surface: only the lower one is.
                if arc_y is None or abs(y - arc_y) > tol:
                    continue
                out.append(x)
        return out

    def _bedrock_bends(self) -> list[float]:
        """Abscissae where the FLOOR itself changes slope.

        Not every vertex of ``bedrock`` is one. The envelope is emitted at
        every breakpoint of the boundary, so a flat floor under a slope with
        three kinks arrives as four collinear vertices; on problem 22 that
        is a vertex at x = 140 in the middle of a straight stretch at
        y = 15. Passing it on as a mandatory cut would spend a slice on a
        bend that does not exist — and the slicer's budget is finite, which
        is exactly the failure this class is careful about.

        The test is the cross product of the two adjacent segments,
        RELATIVE to their lengths, so it reads the same in millimetres and
        in metres.
        """
        verts = self.bedrock.vertices
        out: list[float] = []
        for a, b, c in zip(verts[:-2], verts[1:-1], verts[2:]):
            ux, uy = b.x - a.x, b.y - a.y
            vx, vy = c.x - b.x, c.y - b.y
            scale = math.hypot(ux, uy) * math.hypot(vx, vy)
            if scale > 0.0 and abs(ux * vy - uy * vx) > 1e-9 * scale:
                out.append(b.x)
        return out

    def kinks(self, x_l: Optional[float] = None,
              x_r: Optional[float] = None) -> list[float]:
        """Abscissae where this surface changes slope, strictly inside.

        Two kinds, and both are mandatory slice cuts: the arc-to-floor
        transitions, and the floor's own bends in the stretches where the
        floor IS the surface. A floor bend under a stretch the arc wins is
        not a kink of the surface and must not spend a slice.

        On the composite of verification problem 22 this returns exactly
        two abscissae, which is why the surface can be described at all
        without running into the slicer's "more mandatory cuts than slices"
        refusal — the trap a hand-built polyline of the same surface falls
        into as soon as the arc is described finely.
        """
        lo, hi = self.x_range() if x_l is None or x_r is None else (x_l, x_r)
        if lo is None or hi is None or hi <= lo:
            return []
        tol = 1e-9 * (hi - lo)
        marks = [x for x in self._transitions() if lo + tol < x < hi - tol]
        marks += [x for x in self._bedrock_bends()
                  if lo + tol < x < hi - tol and self.follows_bedrock_at(x)]
        marks.sort()
        out: list[float] = []
        for x in marks:
            if not out or x - out[-1] > tol:
                out.append(x)
        return out

    def clips_the_arc(self) -> bool:
        """True when this composite differs from the circle it came from.

        The sign of ``floor - arc`` is CONSTANT between two consecutive
        breakpoints: over such an interval the floor is one straight
        segment and the arc one smooth piece, and every place the two swap
        is by definition a transition, which is a breakpoint. Sampling one
        midpoint per interval therefore decides the whole interval, and the
        question is answered exactly with a handful of evaluations.

        Not derived from :meth:`kinks` being non-empty, which is the
        tempting shortcut: a transition falling exactly ON an endpoint is
        not an interior cut and would not appear there, and the arc would
        then be handed back unclipped — the very defect this class exists
        to fix, surviving in the corner where the ground meets the floor.
        """
        x_l, x_r = self.x_range()
        if x_l is None or x_r is None or x_r <= x_l:
            return False
        marks = sorted({x_l, x_r, *self.kinks(x_l, x_r)})
        return any(self.follows_bedrock_at(0.5 * (a + b))
                   for a, b in zip(marks[:-1], marks[1:]))

    def y_span(self, x_l: float, x_r: float) -> Optional[tuple[float, float]]:
        """Exact ``(y_min, y_max)`` of the surface over ``[x_l, x_r]``.

        Exact and not sampled, and this is the one that bites. Between two
        consecutive breakpoints the surface is either a straight floor
        segment — extremes at its ends — or a piece of arc, whose only
        interior extreme is the bottom of the circle. Evaluating the ends,
        the kinks and that bottom therefore covers every case.

        The slicer uses this span to throw away material boundaries that
        cannot cut the surface. Answer it the way a plain arc would and
        problem 22 reports (20, 60) for a surface that runs along y = 15:
        the weak layer at y = 16 falls outside, is culled by bounding box,
        and stops being a mandatory cut — silently, which is the worst way
        to lose a layer.
        """
        xs = [x_l, x_r] + self.kinks(x_l, x_r)
        if x_l <= self.centre_x <= x_r and not self.follows_bedrock_at(
                self.centre_x):
            xs.append(self.centre_x)
        ys = [y for y in (self.base_y_at(x) for x in xs) if y is not None]
        if not ys:
            return None
        return min(ys), max(ys)

    # ------------------------------------------------------------------
    def drawing_vertices(self, samples: int = 60) -> list[tuple[float, float]]:
        """The surface as a polyline, for drawing and for export.

        The kinks are included exactly; the arc stretches between them are
        sampled. This is a PICTURE of the surface, never the surface the
        slicer works on — that one keeps its arc exact.
        """
        x_l, x_r = self.x_range()
        if x_l is None or x_r is None or x_r <= x_l:
            return []
        xs = [x_l + (x_r - x_l) * i / samples for i in range(samples + 1)]
        xs += self.kinks(x_l, x_r)
        xs.sort()
        out: list[tuple[float, float]] = []
        for x in xs:
            y = self.base_y_at(x)
            if y is None:
                continue
            if out and x - out[-1][0] <= 1e-12 * (x_r - x_l):
                continue
            out.append((x, y))
        return out

    def to_dict(self) -> dict:
        """Serialised form.

        Carries the circle it came from AND the polyline it became. The
        circle, because that is what a composite is reported by — it has a
        centre and a radius and is picked off the slip-centre grid by them
        — and because it is enough to rebuild the surface: re-clipping the
        same circle against the same model gives the same composite, which
        is what the probabilistic sampler relies on. The polyline, because
        a drawing of the arc alone would be a picture of a surface that was
        never analysed.
        """
        return {
            "type": "composite",
            "id": self.id,
            "centre_x": self.centre_x,
            "centre_y": self.centre_y,
            "radius": self.radius,
            "x_left": self.x_left,
            "x_right": self.x_right,
            "vertices": [list(p) for p in self.drawing_vertices()],
            "tension_cracks": [list(t) for t in self.tension_cracks],
        }


# ----------------------------------------------------------------------
def compose_with_bedrock(circle: SlipCircle, external):
    """Clip ``circle`` to the floor of the model, if it dips below it.

    Returns the circle UNCHANGED when its arc stays inside the soil, and
    that is not an optimisation: it is what keeps every model without
    escaping surfaces answering exactly as it did before the option
    existed. A composite is built only where the alternative — with the
    option off — is for the surface to be discarded outright, which is the
    trade the reference documents and its dialog illustrates.

    ``circle`` must already carry its endpoints. The caller resolves them,
    together with reverse curvature and the user's tension crack, before
    the clipping, so that the surface which gets clipped is the surface
    that gets analysed.
    """
    from ogr_core.geometry import bedrock_surface

    if circle.x_left is None or circle.x_right is None:
        return circle
    bedrock = bedrock_surface(external)
    if len(bedrock.vertices) < 2:
        return circle

    composite = CompositeSurface(
        circle=circle, bedrock=bedrock,
        x_left=circle.x_left, x_right=circle.x_right,
        tension_cracks=list(circle.tension_cracks or []),
        tension_crack_wall=getattr(circle, "tension_crack_wall", None),
    )
    if not composite.clips_the_arc():
        return circle
    return composite


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

    v0.1.111 — a COMPOSITE surface is answered before the override is even
    read, and for the same reason a circle is: it has a real centre of
    rotation, the one its arc was drawn about, and a constructed axis would
    be a worse answer than the true one. It is not a preference. Measured on
    the composite of verification problem 22, 40 slices, dry: with the
    constructed axis Bishop comes out at -1.84 % of the published value and
    with the circle's own centre at +0.08 %.
    """
    if isinstance(surface, CompositeSurface):
        return surface.centre_x, surface.centre_y
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


# ----------------------------------------------------------------------
def lowest_elevation(surface) -> Optional[float]:
    """The lowest y the surface actually reaches, or None if unanswerable.

    "Actually reaches" is the whole point: it is the minimum over the part
    of the surface that is analysed, not over the geometry it was built
    from. On a circle those are different things, and confusing them is
    easy — :meth:`SlipCircle.x_range` answers with the extent of the WHOLE
    circle, ``xc ± R``, while the surface runs only between ``x_left`` and
    ``x_right``, endpoints that a reverse-curvature tension crack may
    already have moved.

    Exact geometry rather than a minimum sampled over the slices, and that
    is deliberate: a sampled minimum would make the Minimum Elevation
    filter depend on the number of slices, which is the class of defect
    v0.1.100 and D05 were spent on. On a 46 m radius sliced 50 ways the
    sampling error is only ~4 mm, but a filter whose answer moves when the
    slicing changes has no defensible value at all.

    Used by the Minimum Elevation surface filter, whose rule is that a
    surface dipping below the user's elevation is discarded, not trimmed.

    v0.1.111 — a COMPOSITE has to be asked, not derived: the bottom of its
    circle is exactly the point the clipping removed, so answering with
    ``centre_y - radius`` would filter it on an elevation it never reaches.
    On problem 22 that is 10.0 against the 15.0 the surface actually runs
    along, and Minimum Elevation would discard the very surface the option
    exists to build.
    """
    if isinstance(surface, CompositeSurface):
        x_l, x_r = surface.x_range()
        span = surface.y_span(x_l, x_r)
        return span[0] if span else None
    if isinstance(surface, SlipCircle):
        x_l, x_r = surface.x_left, surface.x_right
        if x_l is None or x_r is None:
            x_l, x_r = surface.x_range()
        if x_l > x_r:
            x_l, x_r = x_r, x_l
        # The arc's own lowest point is the bottom of the circle, and it
        # belongs to the surface only when the centre's abscissa is inside
        # the span; otherwise the arc is monotone and an endpoint wins.
        if x_l <= surface.centre_x <= x_r:
            return surface.centre_y - surface.radius
        ends = [surface.base_y_at(x_l), surface.base_y_at(x_r)]
        ends = [y for y in ends if y is not None]
        return min(ends) if ends else None

    verts = list(getattr(getattr(surface, "polyline", None), "vertices", ()))
    if verts:
        return min(v.y for v in verts)
    return None
