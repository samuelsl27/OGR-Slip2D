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
      vertical;
    * ``"bad_vertex_data"`` (v0.1.465): a datum of Sarma's method per vertex
      that :func:`checked_vertex_data` refuses. Its ``reason`` says which
      rule (:data:`VERTEX_DATA_REASONS`) and ``where`` the vertex it names,
      ``(x, y)`` or None, so a window says it in its own language (the
      review of v0.1.465: the table showed this English sentence).
    """

    def __init__(self, kind: str, message: str, reason: str = None,
                 where: tuple = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.reason = reason
        self.where = where


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


#: v0.1.465 (D357) -- the keys of one vertex's data for Sarma's method.
VERTEX_KEYS = ("angle", "c", "phi")

#: v0.1.465 -- a face closer than this to horizontal [rad] is no face. THE
#: threshold: ``ogr_slip2d.sarma.angles.upward`` reads it from here, so an
#: angle this rule lets through is never one the method refuses (the review
#: of v0.1.465: the rule refused only an exact 0 or 180).
HORIZONTAL_FACE_RAD = 1e-12

#: The reasons a per-vertex datum is refused (``NotASurface.reason``):
#: ``not_rows``, the data are not a list of rows; ``no_vertex``, a row
#: without the x and y of its vertex; ``not_a_vertex``, a point that is no
#: interior vertex; ``twice``, two data for one vertex; ``angle``, an angle
#: that is not a number, not finite or horizontal; ``pair``, a c without its
#: φ or the reverse; ``strength``, a c or φ that is not a number or out of
#: range.
VERTEX_DATA_REASONS = ("not_rows", "no_vertex", "not_a_vertex", "twice",
                       "angle", "pair", "strength")


def _number(value) -> float:
    """``value`` as a float, or ValueError: a bool is not a number here
    (``True`` would be a face at 1°; the review of v0.1.465)."""
    if isinstance(value, bool):
        raise ValueError(value)
    return float(value)


def is_face_angle(angle_deg: float) -> bool:
    """Whether ``angle_deg`` (degrees, any value) is a face: finite and
    not within :data:`HORIZONTAL_FACE_RAD` of horizontal."""
    if not math.isfinite(angle_deg):
        return False
    t = math.radians(angle_deg % 180.0)
    return HORIZONTAL_FACE_RAD <= t <= math.pi - HORIZONTAL_FACE_RAD


def checked_vertex_data(points, data) -> dict:
    """``data`` as the per-vertex data of Sarma's method on the polyline
    ``points`` (already :func:`checked_points`), or :class:`NotASurface`
    with ``kind = "bad_vertex_data"`` and the reason (v0.1.465, D357): the
    first datum :func:`split_vertex_data` refuses.

    THE one rule, asked by the API, the window, the file's reader and the
    run, so a datum is valid or not in the same words everywhere.

    ``data`` is ``{(x, y): {"angle": θ, "c": c, "phi": φ}}`` or a list of
    ``{"x", "y", "angle", "c", "phi"}``. Each point must be an INTERIOR
    vertex of the polyline (an end has no face): matched within a
    billionth of the polyline's width and stored at the vertex's own
    coordinates. Then:

    * ``angle`` [degrees, counter-clockwise from +x, any value: only the
      line counts], finite and not horizontal, or None;
    * ``c`` [kPa] >= 0 and ``phi`` [degrees] in [0, 90), finite, and the two
      TOGETHER (the owner's decision, 2026-11-16: a face never mixes the c
      of one source with the φ of another), or both None.

    A vertex with no datum left is dropped. Returns
    ``{(x, y): {"angle": θ | None, "c": c | None, "phi": φ | None}}``.
    """
    good, refused = split_vertex_data(points, data)
    if refused:
        raise refused[0]
    return good


def split_vertex_data(points, data) -> tuple:
    """``(good, refused)``: the data of ``data`` the rule of
    :func:`checked_vertex_data` accepts, as it returns them, and a
    :class:`NotASurface` for each one it refuses, in order.

    The lenient form, for what reads data nobody checked (a hand-edited
    file): the run, the design report and the canvas take the good ones and
    say the others, so one bad row no longer costs the polyline for every
    method (the review of v0.1.465). A first refusal of two data for one
    vertex keeps the first.
    """
    refused = []

    def bad(reason, message, where=None):
        refused.append(NotASurface("bad_vertex_data", message,
                                   reason=reason, where=where))

    if data is None or (hasattr(data, "__len__") and not isinstance(
            data, (str, bytes)) and len(data) == 0):
        return {}, refused
    if isinstance(data, dict):
        try:
            rows = [dict(v, x=k[0], y=k[1]) for k, v in data.items()]
        except (TypeError, ValueError, LookupError):
            bad("not_rows", "The per-vertex data are not a list of rows.")
            return {}, refused
    elif isinstance(data, (list, tuple)):
        rows = list(data)
    else:
        bad("not_rows", "The per-vertex data are not a list of rows.")
        return {}, refused
    interior = list(points[1:-1])
    xs = [x for x, _y in points]
    tol = 1e-9 * max(max(xs) - min(xs), 1e-300) if xs else 0.0
    out = {}
    for row in rows:
        try:
            x, y = _number(row["x"]), _number(row["y"])
        except (TypeError, ValueError, KeyError, LookupError):
            bad("no_vertex", "A vertex datum needs the x and y of its vertex.")
            continue
        vertex = next((v for v in interior
                       if abs(v[0] - x) <= tol and abs(v[1] - y) <= tol), None)
        if vertex is None:
            bad("not_a_vertex", "(%g, %g) is not an interior vertex of the "
                "surface." % (x, y), (x, y))
            continue
        if vertex in out:
            bad("twice", "Two data for the vertex (%g, %g)." % vertex, vertex)
            continue
        angle, c, phi = (row.get(k) for k in VERTEX_KEYS)
        if angle is not None:
            try:
                angle = _number(angle)
            except (TypeError, ValueError):
                angle = math.nan
            if not is_face_angle(angle):
                bad("angle", "The angle at (%g, %g) must be a finite number "
                    "and not horizontal." % vertex, vertex)
                continue
        if (c is None) != (phi is None):
            bad("pair", "The face cohesion and friction angle at (%g, %g) go "
                "together." % vertex, vertex)
            continue
        if c is not None:
            try:
                c, phi = _number(c), _number(phi)
            except (TypeError, ValueError):
                c = phi = math.nan
            if not (math.isfinite(c) and math.isfinite(phi)) or c < 0.0 \
                    or not 0.0 <= phi < 90.0:
                bad("strength", "The face strength at (%g, %g) needs numbers "
                    "with c >= 0 and 0 <= phi < 90." % vertex, vertex)
                continue
        if angle is None and c is None:
            continue
        out[vertex] = {"angle": angle, "c": c, "phi": phi}
    return out, refused


def with_vertex_angle(points, data, vertex, angle) -> dict:
    """The per-vertex data ``data`` (a dict as ``vertex_data`` holds it) with
    the face angle at the interior vertex ``vertex`` set to ``angle``
    [degrees], or taken away with None, and everything else as it was
    (v0.1.469, D357, the angle tool and the vertex's context menu).

    The c and φ of that vertex stay: the angle and the strength of a face
    are separate data, and the tool edits only the angle. The edited row is
    checked by the rule of :func:`checked_vertex_data`, and its refusal is
    raised (:class:`NotASurface`, ``bad_vertex_data``); the rows of the
    other vertices are left exactly as they are, a bad one of a hand-edited
    file too, which the run already reports: an edit of one vertex is not a
    verdict on the others. A vertex left with no datum is dropped, and two
    stored keys for the vertex (a hand-edited file) become its one row.

    ``points`` are already :func:`checked_points`; ``vertex`` is matched as
    the rule matches, within a billionth of the polyline's width, and the
    row is stored at the vertex's own coordinates.
    """
    interior = list(points[1:-1])
    xs = [x for x, _y in points]
    tol = 1e-9 * max(max(xs) - min(xs), 1e-300) if xs else 0.0
    vx, vy = vertex
    match = next((v for v in interior
                  if abs(v[0] - vx) <= tol and abs(v[1] - vy) <= tol), None)
    if match is None:
        raise NotASurface("bad_vertex_data", "(%g, %g) is not an interior "
                          "vertex of the surface." % (vx, vy),
                          reason="not_a_vertex", where=(vx, vy))
    row = {"angle": None, "c": None, "phi": None}
    out = {}
    found = False
    for key, datum in (data or {}).items():
        try:
            same = (abs(float(key[0]) - match[0]) <= tol
                    and abs(float(key[1]) - match[1]) <= tol)
        except (TypeError, ValueError, LookupError):
            same = False
        if same:
            if not found and isinstance(datum, dict):
                row = {k: datum.get(k) for k in VERTEX_KEYS}
                found = True
            continue
        out[key] = datum
    row["angle"] = angle
    out.update(checked_vertex_data(points, {match: row}))
    return out


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
    #: v0.1.465 (D357) -- Sarma's data per interior vertex, by its exact
    #: coordinates: ``{(x, y): {"angle": θ°, "c": kPa, "phi": °}}``, each
    #: None where not given (:func:`checked_vertex_data`). By coordinates
    #: and not by index, so it survives the polyline being turned left to
    #: right, its ends moved onto the ground and a crack cutting it.
    vertex_data: dict = field(default_factory=dict)

    @classmethod
    def from_points(cls, points, *, id: str = None,
                    vertex_data=None) -> "UserPolylineSurface":
        """The surface through ``points``, checked by :func:`checked_points`
        (:class:`NotASurface` with the reason when it is not a surface),
        with the per-vertex data checked by :func:`checked_vertex_data`."""
        kw = {} if id is None else {"id": id}
        pts = checked_points(points)
        return cls(points=pts, vertex_data=checked_vertex_data(
            pts, vertex_data), **kw)

    def to_dict(self) -> dict:
        out = {"type": "polyline", "id": self.id,
               "points": [[x, y] for x, y in self.points]}
        # v0.1.465 (D357) -- only when there is a datum, so the file and the
        # fingerprint of a polyline without any do not move
        if self.vertex_data:
            out["sarma"] = [dict({"x": x, "y": y}, **{
                k: v.get(k) for k in VERTEX_KEYS})
                for (x, y), v in sorted(self.vertex_data.items())]
        return out

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
        # v0.1.465 (D357) -- the per-vertex data, read as written; the run
        # checks it with the geometry (``split_vertex_data``). Anything but
        # a list of rows is no data (``"sarma": 5`` raised a TypeError that
        # cost the whole file; the review of v0.1.465)
        rows = data.get("sarma")
        for row in rows if isinstance(rows, list) else ():
            if not isinstance(row, dict):
                continue
            try:
                key = (float(row["x"]), float(row["y"]))
            except (TypeError, ValueError, KeyError, LookupError):
                continue
            surface.vertex_data[key] = {k: row.get(k) for k in VERTEX_KEYS}
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
