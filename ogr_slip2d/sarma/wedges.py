# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Sarma's wedges: the sliding mass cut by inclined faces, with the loads on
each wedge (spec 009, D357, v0.1.463).

WHAT IS BUILT, AND ON WHAT

The wedges are built on a surface the slicer has already RESOLVED and
judged: :func:`build_wedges` takes the vertical slices of
:func:`ogr_slip2d.slicer.slice_surface` on that surface, so the ends, the
tension crack, the refusals and the filters are the ones every vertical
method sees (spec 009, «Rebanar en vertical primero»).

* **Boundaries** on the surface: its own vertices, the points where it
  crosses the water table or a material contact (this one with
  ``boundaries_at_materials``, on by default), which are the slicer's
  mandatory cuts (``slicer._crossing_cuts``), and uniform divisions until
  there are ``num_wedges``, which is a MINIMUM: a surface with more
  vertices has more wedges.
* **Faces**: from each interior boundary, at the angle given for that
  vertex or the one of the policy (:mod:`ogr_slip2d.sarma.angles`), up to
  where the ray leaves the soil (``ray_ground_exit``). The two end faces
  are vertical and carry nothing: at a toe on the ground they have no
  length; at a tension crack the head face is the crack's wall and its
  water the thrust on it.
* **The weight**, exact by material: each wedge polygon is cut along the
  material contacts as drawn, each piece takes the material of a point
  inside it (the regions are asked only that, as the slicer asks them for
  its bands), and the part below the water table takes the saturated unit
  weight, as in ``overburden._column_weight``.
* **U on a base and PW on a face**, ∫u dl by Gauss–Legendre with two points
  on each stretch between the points where u can bend (the crossings of
  the segment with the material contacts, the water table, the
  piezometric lines and the ground, and the abscissas of their vertices).
  u is the slicer's at every point (``slicer._base_pore_pressure``, cut-off
  and unsaturated policy included), so the integral is exact wherever u is
  piecewise linear, which a water table, a piezometric line and Ru are
  (the crossings of those lines with each other are stretch ends too). A
  pore pressure grid or a seepage field is integrated on 16 equal
  sub-stretches of each, and that is an approximation, declared.
* **What acts on the top**, stretch by stretch of the ground between the
  tops of the two faces: the distributed loads (their pressure is linear
  along each load, so the midpoint of each stretch they cover is exact; a
  pressure on a vertical face of the ground by height, on the part of it
  that is this wedge's top), the line loads by where their point is
  (:func:`_line_load_shares`: along the ground, half on the top of an
  interior face; inside the soil, the wedge that holds it), and the ponded
  water as a pressure γw·d normal to the ground, Gauss–Legendre on each
  stretch where its depth is linear. None of them is spread over a column:
  a wedge carries what lies on its own top.
* **The design standard's action factors**, by the slicer's own function
  (``design_actions.apply_action_factors``): a wedge drives when
  sense·sin α > 0, read on the unfactored wedges, and a load is classed
  whole. Ru is read again with the factor, along the bases and faces.
* **The strength of a base** is read off its material at the Fellenius
  estimate of the effective normal stress on the base,
  max(0, W cos α − U)/l, where Janbu's method reads it, through the same
  function every method reads it through (``local_c_phi``). A strength
  model that reads more than that stress (SHANSEP, a vertical-stress ratio,
  an anisotropy, a depth below the top of its layer) reads it off a
  COLUMN: the vertical slice that stands on the wedge's base, cut by the
  slicer itself at the base's two ends (``slice_surface(cuts=...)``), so it
  is measured exactly as a vertical method's slice is (owner's decision,
  2026-11-15, paso 0). The base's material is that column's too: the
  weaker one where the base runs along a contact (D447), a weak layer's
  where it runs along one.
* **The strength of a face**: the one given for its vertex, else the one
  given for every face, else the mean of the materials it crosses
  weighted by length (c and tan φ), each of which must then be
  Mohr–Coulomb or undrained (c = cu, φ = 0: its envelope at any stress;
  v0.1.464); or none.

Conventions are the solver's (:mod:`ogr_slip2d.sarma.solver`): lists in
increasing x, faces from 1 at the left end to n + 1 at the right one in
every code. A wedge IS a :class:`~ogr_slip2d.slicer.Slice` (owner's
decision, 2026-11-15): its base fields are the wedge's base, its
``weight``, ``soil_weight``, ``water_weight`` and ``water_force_h`` are the
wedge's, ``pore_pressure`` is U/l (the mean over the base, so that u·l of
any reader is the solver's U), and ``width·height`` is its area.

Author: Samuel Sáez López (UPCT)

References:
    Sarma, S. K. (1979). Stability analysis of embankments and slopes.
        J. Geotech. Eng. Div. ASCE 105(GT12), 1511–1524. NOT consulted.
    Janbu, N. (1973). Slope stability computations. In Embankment-Dam
        Engineering (Casagrande volume), Wiley, 47–86: the stress the
        strength of a base is read at.
    Fellenius, W. (1936). Calculation of the stability of earth dams.
        Trans. 2nd Congress on Large Dams, Washington, vol. 4, 445–462.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import NamedTuple, Optional

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from ogr_core.geometry import BoundaryType
from ogr_core.geometry.ground import (distance_to_profile, envelope_y_at,
                                      ray_ground_exit)
from ogr_core.hydraulic.excess_pore_pressure import (
    is_enabled as excess_is_enabled)
from ogr_core.hydraulic.ponded_water import ponded_depth_at
from ogr_core.loads.overburden import (_line_load_components,
                                       _surface_pressures_at)
from ogr_core.materials.builtin_models import MohrCoulomb, Undrained
from ogr_core.materials.material import PorePressureType
from ogr_core.materials.strength_model import local_c_phi

from ogr_slip2d import messages as msg
from ogr_slip2d import slicer as _slicer
from ogr_slip2d.external_forces import seismic_soil_part, slice_forces
from ogr_slip2d.methods.janbu import slide_sense
from ogr_slip2d.sarma import angles as _angles
from ogr_slip2d.sarma.angles import VERTICAL
from ogr_slip2d.sarma.solver import FIXED, Base, Face, SarmaSolution, solve
from ogr_slip2d.slicer import Slice, Slices

#: The ``angle_source`` of a face of the policy made vertical because it did
#: not reach the ground or crossed a neighbour (v0.1.464).
VERTICALIZED = "verticalized"

#: Where the strength of a face comes from when no vertex gives it one.
MATERIALS = "materials"
NO_STRENGTH = "none"
FACE_STRENGTHS = (MATERIALS, NO_STRENGTH)

#: Gauss–Legendre with two points on [0, 1]: exact for a linear integrand
#: (Abramowitz and Stegun 1964, 25.4.29), which is what u is between two
#: of the points where it can bend.
_GL = (0.5 - 0.5 / math.sqrt(3.0), 0.5 + 0.5 / math.sqrt(3.0))
#: Sub-stretches of each stretch where u is a field (a grid, a seepage
#: analysis) and not piecewise linear: an approximation, declared.
_FIELD_PIECES = 16
#: A part of a wedge in no region with a material, over its area, past
#: which the wedge is refused: the regions and the external boundary are
#: the same polygon to rounding, and a real hole is far above this.
_OUTSIDE = 1e-6


@dataclass
class Wedge(Slice):
    """One wedge, as a :class:`~ogr_slip2d.slicer.Slice` (see the module)."""

    #: The polygon, counter-clockwise, as ``((x, y), ...)``.
    polygon: tuple = ()
    area: float = 0.0
    #: U = ∫u dl over the base [kN/m].
    pore_force: float = 0.0
    #: The vertical slice standing on the base, cut by the slicer: what a
    #: strength model that reads the column reads.
    column: Optional[Slice] = None


@dataclass
class WedgeFace:
    """A face between two wedges, or at an end of the mass."""

    index: int
    x_base: float
    y_base: float
    x_top: float
    y_top: float
    #: θ [rad], counter-clockwise from +x, in (0, π).
    theta: float
    length: float
    #: PW = ∫u dl over the face [kN/m]; 0 on the end faces.
    water_force: float = 0.0
    #: c̄ [kPa] and tan φ̄, before the reduction by F.
    cohesion: float = 0.0
    tan_phi: float = 0.0
    #: Where the angle came from: ``end``, ``vertex``, the policy, or
    #: ``verticalized`` (a policy face made vertical, v0.1.464).
    angle_source: str = ""
    #: Where the strength came from: ``end``, ``vertex``, ``given``,
    #: ``materials`` or ``none``.
    strength_source: str = ""

    @property
    def delta(self) -> float:
        """δ of the solver [rad] (:func:`angles.delta_of`)."""
        return _angles.delta_of(self.theta)


@dataclass
class Wedges(Slices):
    """The wedges of one surface (``slices``), with their faces."""

    #: The n + 1 faces in increasing x.
    faces: list = field(default_factory=list)
    #: The slicer's vertical slices of the same surface, which the mass's
    #: sense of sliding is read off.
    vertical: Optional[Slices] = None
    #: The abscissas of the boundaries on the surface.
    boundaries: tuple = ()
    angle_policy: str = ""
    #: Per-vertex data no boundary took, as ``(kind, (x, y))``.
    unused_vertex_data: list = field(default_factory=list)
    #: How many faces of the policy were made vertical (v0.1.464).
    verticalized: int = 0

    @property
    def wedge_fields(self) -> dict:
        """The fields of a ``Wedges`` that ``Slices`` has not, for
        ``slice_store`` to give back the class it spilled (v0.1.464)."""
        return {"faces": self.faces, "vertical": self.vertical,
                "boundaries": self.boundaries,
                "angle_policy": self.angle_policy,
                "unused_vertex_data": self.unused_vertex_data,
                "verticalized": self.verticalized}


class SolverInput(NamedTuple):
    """What :func:`ogr_slip2d.sarma.solver.solve` takes for ``wedges``."""

    bases: tuple
    faces: tuple
    head_thrust: float
    slide_sign: int


# ------------------------------------------------------------- geometry
def _segment_hits(p, q, pts, tol):
    """The parameters t in (0, 1) of segment p→q where it meets the
    polyline ``pts`` (a list of (x, y)), ends of collinear runs included."""
    out = []
    dx, dy = q[0] - p[0], q[1] - p[1]
    for a, b in zip(pts[:-1], pts[1:]):
        sx, sy = b[0] - a[0], b[1] - a[1]
        den = dx * sy - dy * sx
        wx, wy = a[0] - p[0], a[1] - p[1]
        if abs(den) <= 1e-14 * (abs(dx * sy) + abs(dy * sx) + 1e-300):
            if abs(wx * dy - wy * dx) <= tol * math.hypot(dx, dy):
                n2 = dx * dx + dy * dy
                for e in (a, b):
                    out.append(((e[0] - p[0]) * dx + (e[1] - p[1]) * dy)
                               / n2)
            continue
        t = (wx * sy - wy * sx) / den
        u = (wx * dy - wy * dx) / den
        if -1e-12 <= u <= 1.0 + 1e-12:
            out.append(t)
    return [t for t in out if 0.0 < t < 1.0]


def _stretches(p, q, lines, xs, field_water):
    """The parameters splitting p→q into stretches where u is linear: its
    crossings with ``lines`` and the abscissas ``xs`` (see the module)."""
    ts = {0.0, 1.0}
    length = math.hypot(q[0] - p[0], q[1] - p[1])
    if length <= 0.0:
        return [0.0, 1.0]
    tol = 1e-12 * length
    for pts in lines:
        ts.update(_segment_hits(p, q, pts, tol))
    dx = q[0] - p[0]
    if abs(dx) > 1e-12 * length:
        for x in xs:
            t = (x - p[0]) / dx
            if 0.0 < t < 1.0:
                ts.add(t)
    out = sorted(ts)
    out = [out[0]] + [b for a, b in zip(out[:-1], out[1:])
                      if b - a > 1e-12]
    if out[-1] != 1.0:
        out[-1] = 1.0
    if field_water:
        fine = [0.0]
        for a, b in zip(out[:-1], out[1:]):
            fine.extend(a + (b - a) * k / _FIELD_PIECES
                        for k in range(1, _FIELD_PIECES + 1))
        out = fine
    return out


def _gauss_points(p, q, ts):
    """``[(x, y, weight)]`` of two-point Gauss–Legendre on each stretch."""
    length = math.hypot(q[0] - p[0], q[1] - p[1])
    out = []
    for a, b in zip(ts[:-1], ts[1:]):
        w = 0.5 * (b - a) * length
        for g in _GL:
            t = a + (b - a) * g
            out.append((p[0] + t * (q[0] - p[0]),
                        p[1] + t * (q[1] - p[1]), w))
    return out


def _path_position(gpts, x, y):
    """Where (x, y), on the ground polyline ``gpts``, lies along it:
    segment index + parameter, so a vertex has one position whichever of
    its two segments it is read on."""
    best = None
    for k, (a, b) in enumerate(zip(gpts[:-1], gpts[1:])):
        sx, sy = b[0] - a[0], b[1] - a[1]
        span = sx * sx + sy * sy
        t = 0.0 if span <= 0.0 else ((x - a[0]) * sx + (y - a[1]) * sy) / span
        t = min(1.0, max(0.0, t))
        d = math.hypot(x - (a[0] + t * sx), y - (a[1] + t * sy))
        if best is None or d < best[0]:
            best = (d, k + t)
    return best[1]


def _path_between(gpts, pa, a, pb, b):
    """The ground from point ``a`` at position ``pa`` to ``b`` at ``pb``,
    with the vertices strictly between."""
    out = [a]
    for j in range(len(gpts)):
        if pa < j < pb:
            out.append(gpts[j])
    out.append(b)
    return out


def _clean(ring):
    """``ring`` without consecutive repeated points."""
    out = []
    for p in ring:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.0:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


# ---------------------------------------------------------------- water
def _water_lines(project):
    """The polylines where u, the unit weight or the column above can
    bend, and their vertices' abscissas."""
    kinds = (BoundaryType.MATERIAL, BoundaryType.WATER_TABLE,
             BoundaryType.PIEZOMETRIC)
    lines = []
    for b in project.boundaries:
        if b.btype in kinds or b.btype == BoundaryType.EXTERNAL:
            lines.append([(v.x, v.y) for v in b.polyline.vertices]
                         + ([(b.polyline.vertices[0].x,
                              b.polyline.vertices[0].y)]
                            if b.polyline.closed else []))
    xs = {x for pts in lines for x, _y in pts}
    # And where two of them cross: there the highest water table changes,
    # or the ponding level meets the ground, and u (or Ru's overburden)
    # bends at an abscissa that is no vertex of either (v0.1.463, the
    # adversarial review: Ru under ponded water was 4.6e-3 off on a base).
    geoms = [LineString(pts) for pts in lines if len(pts) >= 2]
    for i, g1 in enumerate(geoms):
        for g2 in geoms[i + 1:]:
            hit = g1.intersection(g2)
            if not hit.is_empty:
                xs.update(c[0] for c in _coords(hit))
    return lines, sorted(xs)


def _coords(geom):
    """The coordinates of every point of a Shapely geometry."""
    if hasattr(geom, "geoms"):
        return [c for g in geom.geoms for c in _coords(g)]
    return list(geom.coords)


def _field_water(project) -> bool:
    """Whether some pore pressure here is a field and not piecewise
    linear: a pore pressure grid, or a seepage analysis."""
    if getattr(project, "water_pressure_grid", None) is not None:
        return True
    return any(getattr(m, "pore_pressure", None)
               == PorePressureType.FEM_SEEPAGE for m in project.materials)


class _Water:
    """The pore pressure along segments, read point by point as the
    slicer reads it at a base (``_base_pore_pressure``)."""

    def __init__(self, project, ground):
        self.project = project
        self.ground = ground
        self.cutoff = _slicer.negative_pore_pressure_cutoff(project)
        self.lines, self.xs = _water_lines(project)
        self.field = _field_water(project)

    def top_at(self, x):
        y = envelope_y_at(self.ground, x)
        return y

    def integral(self, p, q, material_at, angle, weight_factor=1.0):
        """``(∫u dl, ∫u_raw dl, ∫c_suction dl)`` along p→q.
        ``material_at(x, y)`` gives ``(water material, soil material)``."""
        ts = _stretches(p, q, self.lines, self.xs, self.field)
        u_sum = raw_sum = cs_sum = 0.0
        for x, y, w in _gauss_points(p, q, ts):
            wmat, mat = material_at(x, y)
            top = self.top_at(x)
            u, u_raw, c_s = _slicer._base_pore_pressure(
                self.project, wmat, x, y, y if top is None else top, 0.0,
                self.cutoff, weight_factor=weight_factor,
                weight_material=mat if wmat is not mat else None)
            u_sum += u * w
            raw_sum += u_raw * w
            cs_sum += c_s * w
        return u_sum, raw_sum, cs_sum


# --------------------------------------------------------------- refusal
def _refuse(reasons, code, **args):
    if reasons is not None:
        reasons.append((code, args))
    return None


def _by_vertex(data, points, tol):
    """``{interior index: value}`` of the per-vertex ``data`` (a mapping
    ``{(x, y): value}``) matched to ``points`` (the interior boundary
    points) within ``tol``, and the keys nobody took.

    Two keys within ``tol`` of one point: the NEARER one is taken and the
    other goes with the unused, which the run says. The rule of the data
    matches at a billionth of the width and this at the model's grid, so two
    vertices a grid cell apart each carry a valid datum that lands here on
    one point; a ValueError aborted the whole run (the review of v0.1.465).
    Ties go to the first key in sorted order, so the answer does not hang on
    the order of a dictionary."""
    best, unused = {}, []
    for (x, y), value in sorted((data or {}).items()):
        k = next((i for i, (px, py) in points.items()
                  if abs(px - x) <= tol and abs(py - y) <= tol), None)
        if k is None:
            unused.append((x, y))
            continue
        d = math.hypot(points[k][0] - x, points[k][1] - y)
        if k in best:
            if d < best[k][0]:
                unused.append(best[k][1])
            else:
                unused.append((x, y))
                continue
        best[k] = (d, (x, y), value)
    return {k: v[2] for k, v in best.items()}, unused


def _strength(value) -> tuple:
    """``(c, tan φ)`` of a given face strength ``(c, φ°)``; a ValueError
    unless c >= 0 and 0 <= φ < 90, finite."""
    try:
        c, phi = (float(v) for v in value)
    except (TypeError, ValueError):
        raise ValueError("a face strength is (c, phi), not %r" % (value,))
    if not (math.isfinite(c) and math.isfinite(phi)) or c < 0.0 \
            or not 0.0 <= phi < 90.0:
        raise ValueError("a face strength is (c >= 0, 0 <= phi < 90), "
                         "not %r" % (value,))
    return c, math.tan(math.radians(phi))


# ----------------------------------------------------------------- build
def boundaries_on(project, surface, x_l: float, x_r: float, num_wedges: int,
                  at_materials: bool = True) -> list:
    """The abscissas of the wedge boundaries on ``surface`` over
    ``[x_l, x_r]`` (see the module): its vertices, its crossings with the
    water table and, if ``at_materials``, with the material contacts, and
    uniform divisions up to ``num_wedges``, a minimum.

    With ``at_materials`` they are the slicer's own cuts for
    ``num_slices = num_wedges`` (``slicer._slice_boundaries``, by the same
    functions), whenever those need no more slices than that: vertical
    faces on them are the slicer's slices, and Sarma's method with no
    strength on them is Janbu's on the slices every vertical method reads.
    A crossing of the water table is a boundary for that reason only: U is
    integrated exactly either way."""
    if num_wedges < 1:
        raise ValueError("num_wedges must be at least 1, not %r"
                         % (num_wedges,))
    grid_tol = _slicer._model_grid_tol(project)
    cuts = set(surface.kinks(x_l, x_r))
    span = surface.y_span(x_l, x_r)
    if span is not None:
        cuts.update(_slicer._crossing_cuts(
            project, surface, x_l, x_r, span,
            ((BoundaryType.MATERIAL, BoundaryType.WATER_TABLE)
             if at_materials else (BoundaryType.WATER_TABLE,)), grid_tol))
    segments = (_slicer._merged_segments(cuts, x_l, x_r) if cuts
                else [(x_l, x_r)])
    if len(segments) >= num_wedges:
        return [segments[0][0]] + [b for _a, b in segments]
    return _slicer._share_out(segments, num_wedges, x_l, x_r)


def _mandatory(project, surface, x_l, x_r, at_materials) -> list:
    """The interior boundaries :func:`boundaries_on` must keep: the
    vertices of the surface and its crossings with the water table and the
    contacts. The others are uniform divisions, there only to make up the
    least number (v0.1.464)."""
    xs = boundaries_on(project, surface, x_l, x_r, 1, at_materials)
    return xs[1:-1]


def _with_resolved_ends(surface, vertical):
    """``surface`` with its two ends where the slicing of ``vertical``
    resolved them, for cutting the wedges (v0.1.466, D451).

    The slicer puts the base of an end slice on the ground when the end
    vertex of a polyline is above it by no more than
    ``slicer.ABOVE_GROUND_REL`` of the width (``y_base = y_top``), which is
    right for vertical slices. The wedges' boundaries inside that end
    stretch were cut on the ORIGINAL line, so a straight stretch came out
    bent at each of them, and the solver's exact cancellation of a straight
    base cut by a face (``solver._pairs``) missed the bend: the saturated
    problem 4 of manual 03, whose published end (128; 67.6737) is 3.3e-5
    above the ground, gave 0.9004 with 25 wedges (a root next to a pole,
    with forces of 6.5e5 times the vertical load) instead of 0.4347, and the
    dry one moved by 2.3e-7. On the copy the end vertex sits where the
    slicing put it, so every boundary of the stretch lies on its chord.

    For a polyline (``SlipSurface``), and for a weak-layer clip whose base
    is one (a non-circular search with weak layers, a user's polyline): its
    BASE gets the ends (the review of v0.1.466: the saturated problem 4
    with a weak joint still gave the root by the pole). Only within the
    slicer's own tolerance: an end a weak layer lifts is no end the slicer
    put on the ground, and moving the base's vertex there would move the
    base. The bases of a circle or a composite are chords of an arc, bent
    by construction, and are cut as they were. The copy has lists of its
    own: the slicer appends a crack's wall to ``tension_cracks``. A copy
    can also come from the last digit of ``base_y_at`` at an end, which is
    harmless: it is the same surface."""
    from ogr_slip2d.surface import SlipSurface, WeakLayerSurface
    cols = list(vertical)
    if not cols:
        return surface
    if type(surface) is WeakLayerSurface and type(surface.base) is SlipSurface:
        base = _with_resolved_ends(surface.base, cols)
        if base is surface.base:
            return surface
        return replace(surface, base=base,
                       tension_cracks=list(surface.tension_cracks or []))
    if type(surface) is not SlipSurface:
        return surface
    verts = list(surface.polyline.vertices)
    if len(verts) < 2:
        return surface
    tol = _slicer.ABOVE_GROUND_REL * (cols[-1].base_x_right
                                      - cols[0].base_x_left)
    new = list(verts)
    for k, x, y in ((0, cols[0].base_x_left, cols[0].base_y_left),
                    (-1, cols[-1].base_x_right, cols[-1].base_y_right)):
        if verts[k].x == x and verts[k].y != y and abs(verts[k].y - y) <= tol:
            new[k] = replace(verts[k], y=y)
    if new == verts:
        return surface
    return replace(surface, polyline=replace(surface.polyline, vertices=new),
                   tension_cracks=list(surface.tension_cracks or []))


def build_wedges(project, surface, vertical: Slices, num_wedges: int = 25, *,
                 angles: str = _angles.BISECTOR,
                 vertex_angles: Optional[dict] = None,
                 face_strength=MATERIALS,
                 vertex_strength: Optional[dict] = None,
                 boundaries_at_materials: bool = True,
                 reasons: Optional[list] = None) -> Optional[Wedges]:
    """The wedges of ``surface``, resolved and judged by the slicer.

    Args:
        project: the model.
        surface: the slip surface ``vertical`` was sliced from (resolved in
            place by that slicing).
        vertical: ``slice_surface(project, surface, ...)``, not None.
        num_wedges: the least number of wedges.
        angles: the policy of the faces nobody gives an angle
            (``angles.POLICIES``).
        vertex_angles: ``{(x, y): θ in degrees}`` for the faces rising from
            those vertices of the surface (counter-clockwise from +x, any
            value: only the line counts).
        face_strength: ``MATERIALS``, ``NO_STRENGTH`` or ``(c, φ°)`` for
            every face no vertex gives one.
        vertex_strength: ``{(x, y): (c, φ°)}`` for the faces rising from
            those vertices.
        boundaries_at_materials: cut at the material contacts.
        reasons: a list that receives why there are no wedges: the
            slicer's strings when the columns are refused, or
            ``(code, args)`` with a code of :mod:`ogr_slip2d.messages`.

    Returns:
        A :class:`Wedges`, or None with the reason in ``reasons``.

    Raises:
        ValueError: on a malformed call (no vertical slices, an unknown
            policy or strength, a non-finite datum).
    """
    if vertical is None or not len(vertical):
        raise ValueError("build_wedges needs the vertical slices of the "
                         "surface")
    if angles not in _angles.POLICIES:
        raise ValueError("angle policy must be one of %s, not %r"
                         % (_angles.POLICIES, angles))
    given = None
    if not isinstance(face_strength, str):
        given = _strength(face_strength)
    elif face_strength not in FACE_STRENGTHS:
        raise ValueError("face strength must be one of %s or (c, phi), "
                         "not %r" % (FACE_STRENGTHS, face_strength))
    for value in (vertex_angles or {}).values():
        if not math.isfinite(float(value)):
            raise ValueError("a face angle is a finite number of degrees, "
                             "not %r" % (value,))
    vertex_strength = {k: _strength(v)
                       for k, v in (vertex_strength or {}).items()}
    if excess_is_enabled(project):
        return _refuse(reasons, msg.SARMA_EXCESS_PORE_PRESSURE)

    s_list = list(vertical)
    x_l, x_r = s_list[0].base_x_left, s_list[-1].base_x_right
    grid_tol = _slicer._model_grid_tol(project)
    xs = boundaries_on(project, surface, x_l, x_r, num_wedges,
                       boundaries_at_materials)
    marks = _mandatory(project, surface, x_l, x_r, boundaries_at_materials)
    mark_tol = 1e-9 * (x_r - x_l)

    def plain(x):
        """A uniform division, not a vertex, contact or water-table cut."""
        return all(abs(x - m) > mark_tol for m in marks)

    external = project.external_boundary()
    ground = _slicer._ground_surface_from_external(external)
    gpts = [(v.x, v.y) for v in ground.vertices]

    # v0.1.464 (owner's decisions, 2026-11-16, after the adversarial
    # review): a face of the policy that crosses its neighbour, or does not
    # reach the ground, is
    #
    # * dropped with its boundary when it is a uniform division: two wedges
    #   on one straight base of one material add up to the wedge they split
    #   (``TestFacesOnAStraightStretch`` of v1463), so the factor does not
    #   move, and the count stays a minimum the divisions try to meet;
    # * made vertical, ONE of the pair (the further from vertical), at a
    #   vertex, a contact or a water-table cut, which two vertical faces
    #   never cross (the surface is single-valued in x).
    #
    # Making every crossing face vertical, as the first version did,
    # chained: a vertical face at a concave vertex crosses the next normal
    # face, and so on. On the slope of the test F went 2.5431 (1 to 20
    # wedges), 2.6740 (25, twelve faces made vertical) and 2.6971 (100).
    # A face given at a vertex is never moved: if it crosses, the surface
    # is refused. Each pass drops a boundary or makes a face vertical, so
    # it ends.
    # v0.1.466 (D451) -- cut on the ends the vertical slicing resolved, so a
    # straight end stretch stays straight (``_with_resolved_ends``)
    cut_surface = _with_resolved_ends(surface, s_list)
    while True:
        columns = _slicer.slice_surface(project, cut_surface, cuts=xs,
                                        reasons=reasons)
        if columns is None:
            return None
        cols = list(columns)
        n = len(cols)
        V = [(c.base_x_left, c.base_y_left) for c in cols]
        V.append((cols[-1].base_x_right, cols[-1].base_y_right))
        alpha = [c.base_angle for c in cols]
        lengths = [c.base_length for c in cols]

        # The faces: angle, top, position of the top along the ground.
        interior = {k: V[k] for k in range(1, n)}
        ang_by, unused_a = _by_vertex(vertex_angles, interior, grid_tol)
        str_by, unused_s = _by_vertex(vertex_strength, interior, grid_tol)
        tops = [(x_l, cols[0].top_y_left)]
        thetas = [0.5 * math.pi]
        sources = ["end"]
        drop = None
        for k in range(1, n):
            if k in ang_by:
                theta = _angles.upward(float(ang_by[k]))
                if theta is None:
                    return _refuse(reasons, msg.SARMA_FACE_HORIZONTAL,
                                   face=k + 1, angle=float(ang_by[k]))
                sources.append("vertex")
            else:
                theta = _angles.policy_angle(angles, alpha[k - 1], alpha[k],
                                             lengths[k - 1], lengths[k])
                sources.append(angles)
            top = ray_ground_exit(ground, V[k][0], V[k][1], theta, grid_tol)
            if top is None and sources[-1] != "vertex":
                if plain(xs[k]):
                    drop = k
                    break
                theta, sources[-1] = 0.5 * math.pi, VERTICALIZED
                top = ray_ground_exit(ground, V[k][0], V[k][1], theta,
                                      grid_tol)
            if top is None:
                return _refuse(reasons, msg.SARMA_FACE_NO_EXIT, face=k + 1,
                               angle=math.degrees(theta))
            tops.append((float(top[0]), float(top[1])))
            thetas.append(theta)
        if drop is not None:
            xs = xs[:drop] + xs[drop + 1:]
            continue
        tops.append((x_r, cols[-1].top_y_right))
        thetas.append(0.5 * math.pi)
        sources.append("end")
        pos = [_path_position(gpts, x, y) for x, y in tops]
        while True:
            k = next((k for k in range(n) if not pos[k] < pos[k + 1]), None)
            if k is None:
                break
            policy = [j for j in (k, k + 1)
                      if sources[j] not in ("end", "vertex", VERTICALIZED)]
            plains = [j for j in policy if plain(xs[j])]
            if plains:
                drop = plains[-1]
                break
            if not policy:
                return _refuse(reasons, msg.SARMA_FACES_CROSS, face=k + 1,
                               next=k + 2)
            j = max(policy, key=lambda j: abs(thetas[j] - 0.5 * math.pi))
            top = ray_ground_exit(ground, V[j][0], V[j][1], 0.5 * math.pi,
                                  grid_tol)
            if top is None:
                return _refuse(reasons, msg.SARMA_FACE_NO_EXIT, face=j + 1,
                               angle=90.0)
            thetas[j], sources[j] = 0.5 * math.pi, VERTICALIZED
            tops[j] = (float(top[0]), float(top[1]))
            pos[j] = _path_position(gpts, *tops[j])
        if drop is not None:
            xs = xs[:drop] + xs[drop + 1:]
            continue
        break

    # The polygons, and that they tile the mass.
    polys = []
    for i in range(n):
        ring = ([V[i], V[i + 1]]
                + list(reversed(_path_between(gpts, pos[i], tops[i],
                                              pos[i + 1], tops[i + 1]))))
        ring = _clean(ring)
        # the count first: Shapely raises on a ring of fewer than three
        # points (one wedge, the review of v0.1.465)
        if len(ring) < 3:
            return _refuse(reasons, msg.SARMA_WEDGE_INVALID, wedge=i + 1)
        poly = Polygon(ring)
        if not poly.is_valid or poly.area <= 0.0:
            return _refuse(reasons, msg.SARMA_WEDGE_INVALID, wedge=i + 1)
        if ring and Polygon(ring).exterior.is_ccw is False:
            ring = list(reversed(ring))
        polys.append((tuple(ring), poly))
    mass = _clean(V + list(reversed(_path_between(gpts, pos[0], tops[0],
                                                  pos[-1], tops[-1]))))
    mass_area = Polygon(mass).area
    if abs(sum(p.area for _r, p in polys) - mass_area) > 1e-9 * mass_area \
            or unary_union([p for _r, p in polys]).area < (1 - 1e-9) * mass_area:
        bad = next((i for i in range(n)
                    if any(polys[i][1].intersection(polys[j][1]).area
                           > 1e-9 * mass_area for j in range(n) if j != i)),
                   0)
        return _refuse(reasons, msg.SARMA_WEDGE_INVALID, wedge=bad + 1)

    # The weights, exact by material: each wedge cut along the material
    # contacts as drawn, and each piece weighed with the material of a
    # point inside it. Not intersected with the region polygons: the
    # region builder snaps their vertices (to ~1e-7 of the model, measured
    # in v0.1.463), so a wedge drawn on the true ground would stick out of
    # its region by a sliver that weighed nothing (1.7e-7 of a toe wedge's
    # weight). The slicer does the same: it cuts its bands at the true
    # contacts and asks the regions only which material a band is.
    contacts = [LineString([(v.x, v.y) for v in b.polyline.vertices]
                           + ([(b.polyline.vertices[0].x,
                                b.polyline.vertices[0].y)]
                              if b.polyline.closed else []))
                for b in project.boundaries
                if b.btype == BoundaryType.MATERIAL
                and len(b.polyline.vertices) >= 2]
    wet = _below_water_table(project)
    water = _Water(project, ground)

    share_tol = _share_tol(grid_tol, tops)
    line_shares = _line_load_shares(project, gpts, ground, polys, V, tops,
                                    pos, share_tol)
    wedges = []
    for i in range(n):
        ring, poly = polys[i]
        col = cols[i]
        pieces = _pieces(poly, contacts)
        inside = [pc.representative_point() for pc in pieces]
        soil = outside = 0.0
        for pc, mat in zip(pieces, project.materials_at(
                [(pt.x, pt.y) for pt in inside])):
            a = pc.area
            if mat is None:
                outside += a
                continue
            a_wet = pc.intersection(wet).area if wet is not None else 0.0
            soil += (mat.gamma_at(False) * (a - a_wet)
                     + mat.gamma_at(True) * a_wet)
        if outside > _OUTSIDE * poly.area:
            return _refuse(reasons, msg.SARMA_WEDGE_OUTSIDE, wedge=i + 1)
        mat = col.material
        wmat = _slicer.water_material_of(col)
        U, U_raw, CS = water.integral(V[i], V[i + 1],
                                      lambda _x, _y: (wmat, mat), alpha[i])
        l = lengths[i]
        dx = V[i + 1][0] - V[i][0]
        w = Wedge(
            index=i, x_centre=0.5 * (V[i][0] + V[i + 1][0]), width=dx,
            base_x_left=V[i][0], base_x_right=V[i + 1][0],
            base_y_left=V[i][1], base_y_right=V[i + 1][1],
            base_angle=alpha[i], base_length=l,
            weight_arm_ratio=math.sin(alpha[i]),
            top_y_left=col.top_y_left, top_y_right=col.top_y_right,
            top_y_mean=0.5 * (V[i][1] + V[i + 1][1]) + poly.area / dx,
            weight=soil, soil_weight=soil,
            pore_pressure=U / l, raw_pore_pressure=U_raw / l,
            suction_cohesion=CS / l, material=mat,
            layer_top_y=col.layer_top_y, slope_distance=col.slope_distance,
            bedding_angle_deg=col.bedding_angle_deg,
            weak_layer_id=col.weak_layer_id,
            water_material=col.water_material,
            surface_angles=col.surface_angles,
            polygon=ring, area=poly.area, pore_force=U, column=col)
        _top_actions(project, w, gpts, pos[i], tops[i], pos[i + 1],
                     tops[i + 1], first=i == 0, last=i == n - 1,
                     base_left=V[0][1], base_right=V[-1][1],
                     share_tol=share_tol, span=x_r - x_l,
                     line_shares=line_shares.get(i, []))
        wedges.append(w)

    faces = []
    for k in range(n + 1):
        (xb, yb), (xt, yt) = V[k], tops[k]
        face = WedgeFace(index=k, x_base=xb, y_base=yb, x_top=xt, y_top=yt,
                         theta=thetas[k], length=math.hypot(xt - xb, yt - yb),
                         angle_source=sources[k])
        if k in (0, n):
            face.strength_source = "end"
        else:
            refusal = _face_strength(project, face, str_by.get(k), given,
                                     face_strength, water, reasons)
            if refusal:
                return None
        faces.append(face)

    out = Wedges(slices=wedges, faces=faces, vertical=vertical,
                 boundaries=tuple(xs), angle_policy=angles,
                 unused_vertex_data=([("angle", p) for p in unused_a]
                                     + [("strength", p) for p in unused_s]),
                 verticalized=sum(1 for f in faces
                                  if f.angle_source == VERTICALIZED))
    if _slicer.DESIGN_WEIGHT_FACTORS:
        from ogr_slip2d.design_actions import apply_action_factors
        apply_action_factors(project, out,
                             refresh=lambda pr, ws: _refresh_water(
                                 pr, ws, water))
    out.tension_crack_wall = vertical.tension_crack_wall
    out.tension_crack_force = vertical.tension_crack_force
    out.tension_crack_arm = vertical.tension_crack_arm
    return out


def _pieces(poly, contacts):
    """``poly`` cut along the contact lines: the faces of the network the
    contacts and its outline make (``polygonize``) that lie inside it, so a
    closed contact wholly inside it is a piece too, as a crossing one is.

    The WHOLE lines go into the network, not their parts inside ``poly``:
    the ends of ``line.intersection(poly)`` land some 1e-16 off the outline
    of an inclined face, the union does not node them, and the cut came
    out a loose end, with the wedge left whole and weighed with one
    material (measured in v0.1.463 by its adversarial review: −1.3 % on two
    wedges of the test's own model, up to 8 % elsewhere)."""
    crossing = [line for line in contacts if line.intersects(poly)]
    if not crossing:
        return [poly]
    return [g for g in polygonize(unary_union([poly.exterior] + crossing))
            if g.area > 0.0 and poly.contains(g.representative_point())]


def _below_water_table(project):
    """The part of the plane below the highest water table, where the
    saturated unit weight counts (``water_table_y_at``), or None."""
    parts = []
    for wb in project.boundaries_of(BoundaryType.WATER_TABLE):
        pts = [(v.x, v.y) for v in wb.polyline.vertices]
        pts.sort()
        if len(pts) < 2:
            continue
        low = min(y for _x, y in pts) - 1e6
        parts.append(Polygon([(pts[0][0], low)] + pts + [(pts[-1][0], low)])
                     .buffer(0))
    return unary_union(parts) if parts else None


def _share_tol(grid_tol, tops):
    """The edge tolerance of the loads (the slicer's ``share_tol``): the
    model's, never over a quarter of the narrowest top."""
    widths = [b[0] - a[0] for a, b in zip(tops[:-1], tops[1:])
              if b[0] - a[0] > 0.0]
    return min([grid_tol] + [0.25 * w for w in widths])


def _on_segment(pt, a, b, tol) -> bool:
    """Whether ``pt`` is within ``tol`` of the segment a–b."""
    return LineString([a, b]).distance(Point(pt)) <= tol


def _line_load_shares(project, gpts, ground, polys, V, tops, pos, tol):
    """``{wedge index: [(load, share)]}``: the part of each line load each
    wedge carries, by where its point IS and not by its abscissa alone
    (which is what the slicer's ``edge_share`` reads, and the same thing on
    vertical faces).

    * On the ground (within ``tol``), or above it (taken down to it): by
      its position ALONG the ground, so a load on a vertical step goes to
      the wedge whose top that part of the step is. Half to each wedge on
      the top of an interior face; whole on the top of an end face; none
      off the mass's top.
    * Inside the soil (a stand-in for a support at the slip surface, which
      ``edge_share`` keeps whole on purpose): to the wedge that contains
      it, half to each on an interior face, none outside the mass.

    v0.1.463: the first version went by the x of the top of each wedge, and
    the adversarial review measured a load at the corner of a step split
    half and half (F 3.4 % off a load 1 mm beside it) and a buried load on
    the wrong wedge (+7.9 %).
    """
    n = len(polys)
    out = {}
    for load in getattr(project, "line_loads", None) or []:
        x, y = load.point.x, load.point.y
        g = envelope_y_at(ground, x)
        shares = {}
        on_ground = g is not None and (
            y >= g - tol or distance_to_profile(ground, x, y) <= tol)
        if on_ground:
            pt = (x, g) if y > g else (x, y)
            k = next((k for k in range(n + 1)
                      if math.hypot(pt[0] - tops[k][0], pt[1] - tops[k][1])
                      <= tol), None)
            if k is not None:
                shares = ({0: 1.0} if k == 0 else {n - 1: 1.0} if k == n
                          else {k - 1: 0.5, k: 0.5})
            else:
                s = _path_position(gpts, *pt)
                i = next((i for i in range(n) if pos[i] < s < pos[i + 1]),
                         None)
                if i is not None:
                    shares = {i: 1.0}
        else:
            k = next((k for k in range(1, n)
                      if _on_segment((x, y), V[k], tops[k], tol)), None)
            if k is not None:
                shares = {k - 1: 0.5, k: 0.5}
            else:
                i = next((i for i in range(n)
                          if polys[i][1].distance(Point(x, y)) <= tol), None)
                if i is not None:
                    shares = {i: 1.0}
        for i, share in shares.items():
            out.setdefault(i, []).append((load, share))
    return out


def _top_actions(project, w, gpts, pa, a, pb, b, *, first, last, base_left,
                 base_right, share_tol, span, line_shares):
    """The loads and the ponded water on the top of wedge ``w``: the
    ground from ``a`` (at position ``pa``) to ``b``; ``line_shares`` are
    the line loads it carries (:func:`_line_load_shares`)."""
    x0, x1 = a[0], b[0]
    parts = {}
    q_total = 0.0
    path = _path_between(gpts, pa, a, pb, b)
    if x1 > x0:
        # The vertical pressure of the distributed loads, by stretches
        # between their ends: linear along each load, so the midpoint of a
        # stretch is exact.
        cuts = {x0, x1}
        for load in project.distributed_loads:
            for x in (load.start.x, load.end.x):
                if x0 < x < x1:
                    cuts.add(x)
        cuts = sorted(cuts)
        for c0, c1 in zip(cuts[:-1], cuts[1:]):
            for load, p in _surface_pressures_at(project, 0.5 * (c0 + c1)):
                if p:
                    f = p * (c1 - c0)
                    parts.setdefault(load.id, [load, 0.0, 0.0, 0.0])
                    parts[load.id][1] += f
                    q_total += f
        for load_id, (load, f_v, _h, _y) in parts.items():
            w.weight += f_v
            w.load_parts.append((load_id, _slicer._action_of(load), f_v,
                                 0.0, 0.0))
        w.surface_pressure = q_total / (x1 - x0)
    for load, share in line_shares:
        fv, fh = (share * c for c in _line_load_components(load, project))
        w.weight += fv
        w.load_parts.append((load.id, _slicer._action_of(load), fv, fh,
                             load.point.y))
        if fh:
            w.add_water_force(f_h=fh, y=load.point.y)
    # The horizontal part of the distributed loads with horizontal extent,
    # by the slicer's own function over the top's abscissas.
    if x1 > x0:
        for fh, fv, y, load in _slicer.distributed_loads_on(
                project, x0, x1, span,
                edges=(base_left, base_right, first, last, share_tol,
                       a[1], b[1])):
            if _slicer._is_vertical_segment(load, span):
                continue
            w.weight += fv
            w.load_parts.append((load.id, _slicer._action_of(load), fv, fh,
                                 y))
            if fh:
                w.add_water_force(f_h=fh, y=y)
    # A pressure on a vertical face of the ground (a wall back, a step), on
    # the part of that face that is this wedge's top, by height: a face top
    # half way up a step splits the pressure there, not half and half.
    for load in getattr(project, "distributed_loads", None) or []:
        if not _slicer._is_vertical_segment(load, span):
            continue
        dxu, dyu = load.direction_vector()
        xl = 0.5 * (load.start.x + load.end.x)
        total = moment = 0.0
        for p, q in zip(path[:-1], path[1:]):
            if abs(p[0] - xl) > share_tol or abs(q[0] - xl) > share_tol:
                continue
            part = _slicer._face_between(load, min(p[1], q[1]),
                                         max(p[1], q[1]))
            if part is not None:
                total += part[0]
                moment += part[0] * part[1]
        if total:
            w.weight += -total * dyu
            w.load_parts.append((load.id, _slicer._action_of(load),
                                 -total * dyu, total * dxu, moment / total))
            w.add_water_force(f_h=total * dxu, y=moment / total)

    # The ponded water: γw·d normal to the ground, on each stretch where
    # its depth is linear.
    gamma_w = project.settings.groundwater.pore_fluid_unit_weight
    lines = [[(v.x, v.y) for v in wb.polyline.vertices]
             for wb in project.boundaries
             if wb.btype in (BoundaryType.WATER_TABLE,
                             BoundaryType.PIEZOMETRIC)]
    xs = sorted({x for pts in lines for x, _y in pts})
    for p, q in zip(path[:-1], path[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L <= 0.0:
            continue
        force = moment = 0.0
        for x, y, wt in _gauss_points(p, q, _stretches(p, q, lines, xs,
                                                       False)):
            d = ponded_depth_at(project, x, y)
            if d > 0.0:
                force += gamma_w * d * wt
                moment += gamma_w * d * wt * y
        if force:
            fx = force * (q[1] - p[1]) / L
            fy_down = force * (q[0] - p[0]) / L
            w.add_water_force(f_h=fx, y=moment / force, f_v=fy_down)
            w.pond_force_h += fx


def _face_water(project, face, water, weight_factor=1.0):
    """``(PW, ∫c_suction dl)`` on ``face``: u of the material at each point,
    with the water a Generalized Anisotropic material hands to the range of
    the face's own inclination (``slicer.water_material``)."""
    angle = (face.theta if face.theta <= 0.5 * math.pi
             else face.theta - math.pi)

    def materials(x, y):
        mat = project.material_at(x, y)
        return _slicer.water_material(project, mat, angle), mat

    PW, _raw, CS = water.integral((face.x_base, face.y_base),
                                  (face.x_top, face.y_top), materials, angle,
                                  weight_factor)
    return PW, CS


def _face_strength(project, face, by_vertex, given, policy, water, reasons):
    """Fill the strength and the water of an interior face; a refusal
    (with its reason in ``reasons``) returns True."""
    p, q = (face.x_base, face.y_base), (face.x_top, face.y_top)
    PW, CS = _face_water(project, face, water)
    face.water_force = PW
    if by_vertex is not None:
        face.cohesion, face.tan_phi = by_vertex
        face.strength_source = "vertex"
        return False
    if given is not None:
        face.cohesion, face.tan_phi = given
        face.strength_source = "given"
        return False
    if policy == NO_STRENGTH:
        face.strength_source = "none"
        return False
    # The mean of the materials it crosses, weighted by length.
    tol = 1e-12 * max(face.length, 1e-300)
    hits = set()
    for b in project.boundaries:
        if b.btype == BoundaryType.MATERIAL:
            pts = [(v.x, v.y) for v in b.polyline.vertices]
            if b.polyline.closed and pts:
                pts.append(pts[0])
            hits.update(_segment_hits(p, q, pts, tol))
    ts = [0.0] + sorted(hits) + [1.0]
    c_sum = t_sum = 0.0
    for a, b in zip(ts[:-1], ts[1:]):
        if b - a <= 0.0:
            continue
        t = 0.5 * (a + b)
        mat = project.material_at(p[0] + t * (q[0] - p[0]),
                                  p[1] + t * (q[1] - p[1]))
        strength = getattr(mat, "strength", None)
        if isinstance(strength, Undrained):
            # v0.1.464 (owner's decision, 2026-11-16): τ = cu at any stress,
            # so c̄ = cu and φ̄ = 0 is its envelope on a face too
            c_sum += strength.params["cohesion"] * (b - a)
            continue
        if not isinstance(strength, MohrCoulomb):
            _refuse(reasons, msg.SARMA_FACE_STRENGTH, face=face.index + 1,
                    material=getattr(mat, "name", None) or "-")
            return True
        c_sum += strength.params["cohesion"] * (b - a)
        t_sum += math.tan(math.radians(
            strength.params["friction_angle"])) * (b - a)
    face.cohesion = c_sum + (CS / face.length if face.length > 0.0 else 0.0)
    face.tan_phi = t_sum
    face.strength_source = "materials"
    return False


def _refresh_water(project, wedges, water):
    """Ru again along the bases and the faces, now that the soil has its
    factors (``design_actions.refresh_pore_pressures`` for slices). A
    face reads with the factor of the wedge it leans over
    (:func:`_face_factor`)."""
    ws = list(wedges)
    if all(w.weight_factor == 1.0 for w in ws):
        return
    for w in ws:
        wmat = _slicer.water_material_of(w)
        if not _slicer.reads_the_weight(project, wmat):
            continue
        p, q = (w.base_x_left, w.base_y_left), (w.base_x_right, w.base_y_right)
        U, U_raw, CS = water.integral(p, q, lambda _x, _y: (wmat, w.material),
                                      w.base_angle, w.weight_factor)
        w.pore_force = U
        w.pore_pressure = U / w.base_length
        w.raw_pore_pressure = U_raw / w.base_length
        w.suction_cohesion = CS / w.base_length
    if not any(_slicer.reads_the_weight(project, m)
               for m in project.materials):
        return
    for face in wedges.faces[1:-1]:
        k = face.index
        factor = _face_factor(face, ws[k - 1].weight_factor,
                              ws[k].weight_factor)
        if factor == 1.0:
            continue
        face.water_force = _face_water(project, face, water, factor)[0]


def _face_factor(face, toe_side: float, head_side: float) -> float:
    """The weight factor Ru's overburden takes at the points of ``face``:
    the one of the wedge the face leans over, because the column above any
    point of an inclined face lies in it (a face leaning toward +x has the
    wedge on its −x side above it); the mean of the two on a vertical face,
    whose column is the boundary between them. (v0.1.463: the first
    version took the mean everywhere, and the adversarial review measured
    PW 485 against 557 with γG and γG,fav apart.)"""
    if abs(face.theta - 0.5 * math.pi) <= 1e-12:
        return 0.5 * (toe_side + head_side)
    return toe_side if face.theta < 0.5 * math.pi else head_side


def vertical_faces(project, slices, face_strength=MATERIALS, reasons=None):
    """The faces of a set of VERTICAL slices (v0.1.464), with the strength
    and the water a face takes in :func:`build_wedges`: the n + 1 slice
    boundaries from the base to the top, the two ends carrying nothing.
    The registered method reads vertical slices it is handed this way
    (spec 009, the two entries of ``compute_fos``); with ``NO_STRENGTH``
    they are ``sarma.vertical``'s. None, with the reason, if a face
    crosses a material that is not Mohr–Coulomb."""
    given = None
    if not isinstance(face_strength, str):
        given = _strength(face_strength)
    elif face_strength not in FACE_STRENGTHS:
        raise ValueError("face strength must be one of %s or (c, phi), "
                         "not %r" % (FACE_STRENGTHS, face_strength))
    s_list = list(slices)
    n = len(s_list)
    edges = [(s_list[0].base_x_left, s_list[0].base_y_left,
              s_list[0].top_y_left)]
    edges += [(s.base_x_right, s.base_y_right, s.top_y_right)
              for s in s_list]
    if excess_is_enabled(project):
        _refuse(reasons, msg.SARMA_EXCESS_PORE_PRESSURE)
        return None
    external = project.external_boundary()
    water = _Water(project, _slicer._ground_surface_from_external(external))
    faces = []
    for k, (x, yb, yt) in enumerate(edges):
        face = WedgeFace(index=k, x_base=x, y_base=yb, x_top=x,
                         y_top=max(yb, yt), theta=0.5 * math.pi,
                         length=max(0.0, yt - yb), angle_source=VERTICAL)
        if k in (0, n) or face.length <= 0.0:
            face.strength_source = "end" if k in (0, n) else "none"
        elif _face_strength(project, face, None, given, face_strength,
                            water, reasons):
            return None
        elif (s_list[k - 1].weight_factor != 1.0
              or s_list[k].weight_factor != 1.0):
            # Ru with a design standard: the face between two slices reads
            # the mean of their factors (``_face_factor`` on a vertical face)
            face.water_force = _face_water(
                project, face, water, _face_factor(
                    face, s_list[k - 1].weight_factor,
                    s_list[k].weight_factor))[0]
        faces.append(face)
    return [Face(delta=0.0, length=f.length, water_force=f.water_force,
                 cohesion=f.cohesion, tan_phi=f.tan_phi) for f in faces]


# ---------------------------------------------------------------- solver
def to_solver(wedges: Wedges, kh: float = 0.0, kv: float = 0.0) -> SolverInput:
    """The bases and faces of ``wedges`` for
    :func:`ogr_slip2d.sarma.solver.solve`, with ``kh`` and ``kv``.

    Each base reads its loads through the functions every method reads a
    slice's through (``slice_forces``, ``seismic_soil_part``), and its c
    and tan φ at the Fellenius estimate max(0, W cos α − U)/l (Fellenius
    1936; where Janbu 1973 reads it, ``sarma.vertical``) through
    ``local_c_phi``, on the wedge's column with the wedge's suction. The
    sense of sliding is the vertical slices' (``janbu.slide_sense``): the
    same mass, read as every vertical method reads it. The water of a
    tension crack is the thrust on the head face; on a crack at the toe
    of the sliding sense it is the horizontal force on the wedge at the
    wall, as the slicer applies it.
    """
    ws = list(wedges)
    sign = int(slide_sense(list(wedges.vertical), kh, kv))
    bases = []
    for w in ws:
        f = slice_forces(w, kh, kv)
        a, length = w.base_angle, w.base_length
        raw = f.w_total * math.cos(a) - w.pore_force
        sigma = max(0.0, raw) / max(length, 1e-9)
        col = replace(w.column, suction_cohesion=w.suction_cohesion)
        c, tan_phi = local_c_phi(col, w.material, sigma)
        bases.append(Base(alpha=a, length=length, weight=f.w_total,
                          soil_weight=seismic_soil_part(w),
                          pore_force=w.pore_force, cohesion=c,
                          tan_phi=tan_phi, force_x=f.h_water))
    faces = [Face(delta=fc.delta, length=fc.length,
                  water_force=fc.water_force, cohesion=fc.cohesion,
                  tan_phi=fc.tan_phi) for fc in wedges.faces]
    head = 0.0
    wall = wedges.tension_crack_wall
    thrust = wedges.tension_crack_force
    if wall is not None and thrust:
        at_right = abs(wall[0] - ws[-1].base_x_right) <= abs(
            wall[0] - ws[0].base_x_left)
        if at_right == (sign > 0):
            head = thrust
        else:
            k = len(bases) - 1 if at_right else 0
            push = -thrust if at_right else thrust
            bases[k] = replace(bases[k], force_x=bases[k].force_x + push)
    return SolverInput(tuple(bases), tuple(faces), head, sign)


def solve_wedges(wedges: Wedges, kh: float = 0.0, kv: float = 0.0, *,
                 shear_sense: str = FIXED, tolerance: float = 1e-4,
                 max_iterations: int = 75) -> SarmaSolution:
    """Sarma's factor of ``wedges`` (:func:`to_solver` and
    :func:`ogr_slip2d.sarma.solver.solve`)."""
    s = to_solver(wedges, kh, kv)
    return solve(s.bases, s.faces, kh=kh, slide_sign=s.slide_sign,
                 shear_sense=shear_sense, head_thrust=s.head_thrust,
                 tolerance=tolerance, max_iterations=max_iterations)
