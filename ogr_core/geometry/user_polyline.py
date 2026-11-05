# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A non-circular slip surface the user defines by hand.

v0.1.427 (D357, first step) -- until this version a hand-made slip surface
could only be a circle (``SlipCircle``, ``Project.user_surfaces``): the
loader built every stored entry as one, the operations layer refused
anything else, and the window had no tool to draw a polyline. A given
polyline could only be evaluated once, through ``surface_evaluate``, and
was forgotten afterwards. The non-vertical slice method needs a polyline
that STAYS -- its interface angles and strengths are data of the surface's
vertices -- so the surface comes first, on its own.

The class is data, and deliberately nothing else: the points the user gave,
and an id. Its engine twin, ``ogr_slip2d.surface.SlipSurface``, is built
fresh for every evaluation (``ogr_slip2d.surface.slip_surface_of``), because
the engine writes on the surface it is handed -- the tension-crack
truncation moves its last vertex -- and a stored surface the analysis
modified would be a picture of a different surface the next time.

The points are stored as given except for the drawing direction: a polyline
drawn from right to left is the same surface, and is kept left to right.
What is refused is a polyline that is not a function of x, because the
engine slices in x: a step back in x, or a vertical segment. The rule is
:func:`checked_points`, and every door that takes a hand-made polyline asks
it (see there).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from uuid import uuid4

#: The fewest points a non-circular slip surface is made of.
MIN_POINTS = 2


class NotASurface(ValueError):
    """A polyline that is not a slip surface the engine can slice.

    A ValueError, so every caller that caught one before still does; and it
    says WHICH rule failed in ``kind``, so an interface can give the reason
    in its own words and language instead of this English sentence:

    * ``"not_points"``: not a list of pairs of numbers;
    * ``"not_finite"``: a coordinate that is not a finite number;
    * ``"too_few"``: fewer than :data:`MIN_POINTS` points;
    * ``"not_advancing"``: run left to right, x steps back or a segment is
      vertical.
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def _points_of(raw) -> list:
    """``raw`` as a list of (float, float), or :class:`NotASurface`.

    Exactly two coordinates per point: a third one, a mapping or a lone
    number is refused here with the rest, rather than passing the rule and
    breaking whoever unpacks the pair afterwards.
    """
    try:
        items = list(raw)
    except TypeError:
        raise NotASurface("not_points", "A non-circular surface is a list "
                          "of (x, y) points; got %r." % (raw,)) from None
    out = []
    for p in items:
        try:
            if len(p) != 2:
                raise ValueError
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, LookupError):
            raise NotASurface("not_points", "A non-circular surface is a "
                              "list of (x, y) pairs of numbers; got %r."
                              % (p,)) from None
        if not (math.isfinite(x) and math.isfinite(y)):
            raise NotASurface("not_finite", "A non-circular surface needs "
                              "finite coordinates; got (%r, %r)."
                              % (p[0], p[1]))
        out.append((x, y))
    return out


def checked_points(points) -> list:
    """``points`` as a slip surface the engine can slice: pairs of floats,
    left to right. Raises :class:`NotASurface` (a ValueError), with the
    reason in words and its ``kind``, otherwise.

    The ONE rule for a hand-made non-circular surface (v0.1.427, D357),
    asked by every door that takes one, because two doors with two rules
    give two answers:

    * the window and ``user_surface_add``, when the surface is made
      (:meth:`UserPolylineSurface.from_points`), and the canvas before it
      lets a drawing go;
    * ``surface_evaluate``, for a polyline priced once
      (``ogr_api.ops.analysis.surface_from_spec``);
    * the run, for a STORED one, which is not re-checked when the file is
      read (:meth:`UserPolylineSurface.from_dict` says why): the engine
      builds its surface from what this returns
      (``ogr_slip2d.surface.slip_surface_of``).

    Without it the engine answers for ANOTHER surface without a word:
    ``SlipSurface`` sorts its vertices by x when it is built, so a polyline
    that steps back in x is analysed sorted. Measured at v0.1.427:
    [(19, 25), (31, 14.5), (25, 18), (37, 15)] on the demo slope gave
    exactly the factor of [(19, 25), (25, 18), (31, 14.5), (37, 15)].

    Refused: fewer than :data:`MIN_POINTS` points, a point that is not a
    pair of numbers, a coordinate that is not a finite number, and a
    polyline that, run left to right, steps back in x or has a vertical
    segment. A polyline drawn from right to left is accepted and returned
    left to right: it is the same surface.
    """
    pts = _points_of(points)
    if len(pts) < MIN_POINTS:
        raise NotASurface("too_few", "A non-circular surface needs at least "
                          "%d points; got %d." % (MIN_POINTS, len(pts)))
    # A surface drawn from right to left is the same surface.
    if pts[0][0] > pts[-1][0]:
        pts.reverse()
    for (x0, _y0), (x1, _y1) in zip(pts, pts[1:]):
        if not x1 > x0:
            raise NotASurface(
                "not_advancing",
                "A non-circular surface has to advance in x from one end to "
                "the other: x goes from %g to %g, which is a step back or a "
                "vertical segment." % (x0, x1))
    return pts


def _end(p) -> tuple:
    try:
        return float(p[0]), float(p[1])
    except (TypeError, ValueError, LookupError):
        return math.nan, math.nan


@dataclass
class UserPolylineSurface:
    """A polyline slip surface given by the user, left to right."""

    points: list = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def from_points(cls, points, *, id: str = None) -> "UserPolylineSurface":
        """The surface through ``points``, checked by :func:`checked_points`
        (:class:`NotASurface` with the reason when it is not a surface)."""
        kw = {} if id is None else {"id": id}
        return cls(points=checked_points(points), **kw)

    def to_dict(self) -> dict:
        return {"type": "polyline", "id": self.id,
                "points": [[x, y] for x, y in self.points]}

    @classmethod
    def from_dict(cls, data: dict) -> "UserPolylineSurface":
        """Read back what :meth:`to_dict` wrote.

        The GEOMETRY is not re-checked: it was checked when it was made, and
        a file the project cannot open because one hand-edited surface steps
        back in x would cost the user the whole model for one surface. The
        run asks :func:`checked_points` again before analysing it, and a
        surface that fails is not analysed and is said so, with its own
        note (``search.user_polyline_not_a_surface``): fewer than two
        points, a coordinate that is not finite, a step back in x.

        A point that is not a pair of numbers at all is a file the loader
        cannot read, here as in every other entity of the .ogr (a vertex of
        a boundary is read the same way).
        """
        surface = cls(points=[(float(x), float(y))
                              for x, y in data.get("points", [])])
        if "id" in data:
            surface.id = data["id"]
        return surface

    def ends(self) -> tuple:
        """``((x0, y0), (x1, y1))`` as floats, NaN for an end that is not a
        pair of numbers: what a note or a list can always print, even for a
        surface a script stored badly and the run is about to refuse. ``len``
        and not truth: the points may come from a script as an array."""
        try:
            n = len(self.points)
        except TypeError:
            n = 0
        if not n:
            return (math.nan, math.nan), (math.nan, math.nan)
        return _end(self.points[0]), _end(self.points[-1])

    @property
    def first(self) -> tuple:
        return self.ends()[0]

    @property
    def last(self) -> tuple:
        return self.ends()[1]

    def vertex_count(self) -> int:
        """How many points it was given, whatever they are (0 if not a
        list): with :meth:`ends`, what tells two surfaces apart in a note."""
        try:
            return len(self.points)
        except TypeError:
            return 0
