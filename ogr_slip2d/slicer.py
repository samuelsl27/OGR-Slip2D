# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slicer — divides the potential failure mass into vertical slices.

This is the geometric bridge between the slip surface and the LEM
solver. Each slice carries all the scalars the solver needs:

    - geometry:    x_centre, width, base_length, base_angle α
    - physics:     weight W, pore pressure u, base cohesion/φ
    - loads:       surface distributed pressure q, line loads, seismic

v0.1.63 — the weight of a slice is obtained by integrating its VERTICAL
COLUMN: the column is cut at every material boundary and at the water
table, and each band contributes ``γ_band · Δh · dx``. Until then the
whole slice was classified by its base midpoint and given a single γ over
its full height, so a slice spanning two layers weighed as if it were made
entirely of the material under its base, and one straddling the water
table got either γ or γsat for all of it.

The slice BOUNDARIES are still a uniform division of the failure width;
splitting them at the layer crossings is a separate change.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator, Optional

from ogr_core.geometry import (
    Boundary, BoundaryType, Polyline, Vertex, distance_to_profile,
    envelope_y_at, ground_surface,
)
from ogr_core.geometry.anisotropic_surface import anisotropy_angle_at
from ogr_core.hydraulic.excess_pore_pressure import (
    excess_at,
    is_enabled as excess_is_enabled,
)
from ogr_core.hydraulic.ponded_water import ponded_depth_at
from ogr_core.hydraulic.pore_pressure import pore_pressure_at, _interp_y_on_polyline
from ogr_core.hydraulic.water_surfaces import (
    water_surface_defined_at,
    water_table_y_at,
)
from ogr_core.materials import Material
from ogr_core.project import Project

from .surface import (CompositeSurface, SlipCircle, SlipSurface,
                      SurfaceProtocol, WeakLayerSurface)


@dataclass
class Slice:
    """One vertical slice of the failure mass."""

    index: int
    x_centre: float
    width: float
    # Base (on the slip surface)
    base_x_left: float
    base_x_right: float
    base_y_left: float
    base_y_right: float
    base_angle: float      # α, rad. Positive = rises to the right.
    base_length: float
    # Top (ground surface)
    top_y_left: float
    top_y_right: float
    # v0.1.96 — MEAN ground elevation over the slice, integrated exactly.
    # It differs from ``top_y_mid`` only when a profile VERTEX falls inside
    # the slice, and there the chord between the two corners cuts the corner
    # off. ``height`` reads this one so that the weight, the height and the
    # reported area all describe the same column: with a single material,
    # ``weight == gamma * height * width`` has to stay exactly true, and it
    # is a test. None falls back to the chord midpoint.
    top_y_mean: Optional[float] = None
    # v0.1.100 — moment arm of a VERTICAL load applied on this slice, about
    # the surface's moment axis, divided by R. The moment methods write the
    # driving term as ``Σ W·sin α``, which is that arm only while α is the
    # tangent AT the slice's own abscissa; since the base became the chord
    # (see ``slice_surface``) it no longer is, and on a circle the arm is
    # simply ``(x_centre − x_c)/R``, exactly.
    #
    # Getting this back exactly is not cosmetic. On an already-submerged
    # slope the added water weight and the added hydrostatic thrust must
    # cancel term for term, and the cancellation telescopes only when the
    # weight's arm is the true one: with ``sin α`` of the chord it held to
    # 2.4e-4 at 50 slices instead of to 1e-15, and two separate tests exist
    # in this project precisely to catch that.
    #
    # ``sin(base_angle)`` for anything that is not a circle, which is what
    # those methods used before and still their only arm there.
    weight_arm_ratio: float = 0.0
    # Derived scalars
    weight: float = 0.0          # kN/m (per unit out-of-plane width)
    pore_pressure: float = 0.0   # kPa (at the midpoint of the base)
    # v0.1.28 — extra cohesion from matric suction beyond the air entry
    # value (extended Mohr-Coulomb). Zero unless the material declares a
    # non-zero phi_b AND the pore pressure is negative.
    suction_cohesion: float = 0.0
    raw_pore_pressure: float = 0.0   # u before the unsaturated policy
    surface_pressure: float = 0.0  # kPa (distributed load on the top)
    # v0.1.61 — external water forces on the slice, kept OUTSIDE ``weight``
    # on purpose. Water has no shear strength, so the pseudo-static seismic
    # coefficients must not act on it; folding this into ``weight`` (as the
    # distributed-load surcharge is folded) would make kh and kv multiply
    # the water too.
    #   water_weight         vertical resultant, downward positive [kN/m]
    #   water_force_h        horizontal resultant, +x positive     [kN/m]
    #   water_force_h_moment Σ F_h · y about y = 0                 [kN]
    # The moment is stored about a FIXED reference rather than as an
    # application height because several water forces with OPPOSITE signs
    # can act on the same slice (ponded water pushing into the slope, water
    # in a tension crack pushing out of it), and a force-weighted mean
    # height is undefined in that case. About any centre y_c the moment is
    # ``y_c · water_force_h − water_force_h_moment``.
    water_weight: float = 0.0
    water_force_h: float = 0.0
    water_force_h_moment: float = 0.0
    material: Optional[Material] = None
    # v0.1.120 — geometry that only the SLICER can measure, kept here so
    # that every LEM method reads it through the one place that builds a
    # SliceContext. Both are None when nothing in the project asks for
    # them; a strength model that needs one must fall back rather than
    # invent a depth from the other.
    #
    #   layer_top_y     top of the material band the BASE sits in. Not the
    #                   ground surface: under an embankment on three
    #                   stacked clays each slice sees the top of its own.
    #   slope_distance  true distance from the base centre to the nearest
    #                   point of the ground profile. Under a slope face
    #                   that is the perpendicular, not the vertical drop.
    layer_top_y: Optional[float] = None
    slope_distance: Optional[float] = None
    # v0.1.126 — LOCAL bedding orientation at this base [deg from
    # horizontal], or None when the material names no anisotropic
    # surface. None and 0.0 are different answers and stay different:
    # 0.0 is a horizontal bedding, None is nobody having said.
    bedding_angle_deg: Optional[float] = None
    # v0.1.121 — the id of the weak-layer boundary this base runs along, or
    # None. It is what makes the substitution auditable: the strength of a
    # slice on a joint comes from the joint's material and not from the
    # region its midpoint falls in, and without this the two are
    # indistinguishable in the output.
    weak_layer_id: Optional[str] = None

    # ------------------------------------------------------------------
    @property
    def base_y_mid(self) -> float:
        return 0.5 * (self.base_y_left + self.base_y_right)

    @property
    def top_y_mid(self) -> float:
        return 0.5 * (self.top_y_left + self.top_y_right)

    @property
    def height(self) -> float:
        top = self.top_y_mid if self.top_y_mean is None else self.top_y_mean
        return top - self.base_y_mid

    @property
    def base_normal_force(self) -> float:
        """Simple static normal on the base (ignoring interslice forces)."""
        return self.weight * math.cos(self.base_angle)

    def water_moment_about(self, y_c: float) -> float:
        """Moment of the horizontal water forces about elevation ``y_c``.

        Positive when the force tends to rotate the mass about a centre at
        that elevation in the +x sense.
        """
        return y_c * self.water_force_h - self.water_force_h_moment

    def add_water_force(self, f_h: float, y: float, f_v: float = 0.0) -> None:
        """Accumulate an external water force applied at elevation ``y``."""
        self.water_force_h += f_h
        self.water_force_h_moment += f_h * y
        self.water_weight += f_v

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "x_centre": self.x_centre,
            "width": self.width,
            "base_x_left": self.base_x_left,
            "base_x_right": self.base_x_right,
            "base_y_left": self.base_y_left,
            "base_y_right": self.base_y_right,
            "base_angle_deg": math.degrees(self.base_angle),
            "base_length": self.base_length,
            "top_y_mean": self.top_y_mean,
            "height": self.height,
            "weight": self.weight,
            "pore_pressure": self.pore_pressure,
            "suction_cohesion": self.suction_cohesion,
            "raw_pore_pressure": self.raw_pore_pressure,
            "surface_pressure": self.surface_pressure,
            "water_weight": self.water_weight,
            "water_force_h": self.water_force_h,
            "material_id": self.material.id if self.material else None,
            "weak_layer_id": self.weak_layer_id,
        }


# ----------------------------------------------------------------------
@dataclass
class Slices:
    """Ordered collection of slices belonging to one slip surface."""

    slices: list[Slice] = field(default_factory=list)
    # v0.1.7 — hydrostatic force from water in the Tension Crack zone,
    # applied as a horizontal force on the vertical face of the
    # uppermost slice (acting in the failure-direction sense).
    # Computed by ``slice_surface`` when the slip surface intersects
    # a Tension Crack boundary.
    tension_crack_force: float = 0.0   # kN/m, horizontal
    tension_crack_arm: float = 0.0     # vertical distance from the
                                        # crack base to the centroid of
                                        # the water column (for moment)

    def __len__(self) -> int:
        return len(self.slices)

    def __iter__(self) -> Iterator[Slice]:
        return iter(self.slices)

    def __getitem__(self, i: int) -> Slice:
        return self.slices[i]

    def total_weight(self) -> float:
        return sum(s.weight for s in self.slices)

    def to_list(self) -> list[dict]:
        return [s.to_dict() for s in self.slices]


# ----------------------------------------------------------------------
def _point_in_polygon(x: float, y: float, polygon: Polyline) -> bool:
    """Ray-casting point-in-polygon test. Polygon must be closed."""
    verts = polygon.vertices
    n = len(verts)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = verts[i].x, verts[i].y
        xj, yj = verts[j].x, verts[j].y
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-20) + xi
        ):
            inside = not inside
        j = i
    return inside


def _ground_surface_from_external(external: Boundary) -> Polyline:
    """Upper envelope (ground surface) of the external boundary.

    v0.1.84 — delegates to :func:`ogr_core.geometry.ground_surface`, which
    walks the polygon EDGES. This function used to bucket the boundary
    VERTICES by x and keep the highest y of each bucket, which silently
    published any bottom-edge vertex whose x no top vertex shared as if it
    were ground. On the Ej_2 reference model the vertex ``(0, 0)`` on the
    bottom edge turned the flat terrain at y = 30 into a 30 m ravine, and
    the critical circle came out at FoS = 0.79 against a reference of
    1.156 — daylighting on the floor of the model instead of on the slope.
    """
    return ground_surface(external)


def _apply_ponded_water(project: Project, s: "Slice") -> None:
    """Apply the ponded-water load to one slice, in place.

    Still water resting on the ground exerts a pressure NORMAL to the
    ground surface of magnitude ``p = γ_w · d``, with ``d`` the depth below
    the free water surface (hydrostatics). For a slice of width ``dx``
    whose top has slope ``m = dy/dx``, the top face is ``dl = dx·√(1+m²)``
    long and its inward unit normal is ``(m, −1)/√(1+m²)``, so the
    resultant is

        F = p · dl · (m, −1)/√(1+m²) = γ_w · d · dx · (m, −1)

    i.e. a downward component ``γ_w · d · dx`` — exactly the weight of the
    water column standing on the slice — and a horizontal component
    ``γ_w · d · dx · m``. The "weight of the water on the slope" and the
    "horizontal hydrostatic force on the slope" are therefore the two
    components of ONE normal pressure, not two separate actions. Summing
    the horizontal components over the whole submerged face recovers the
    classical ½·γ_w·h² thrust on its vertical projection.

    The resultant is applied at the midpoint of the slice top, which shares
    its x with the slice centre; the vertical component therefore has the
    same moment arm as the slice weight.
    """
    top = s.top_y_mid
    depth = ponded_depth_at(project, s.x_centre, top)
    if depth <= 0.0:
        return
    gamma_w = project.settings.groundwater.pore_fluid_unit_weight
    dx = s.width
    if dx <= 0.0:
        return
    slope = (s.top_y_right - s.top_y_left) / dx
    column = gamma_w * depth * dx        # kN/m, the water column weight
    s.add_water_force(f_h=column * slope, y=top, f_v=column)


def _anisotropic_surfaces(project: Project) -> dict:
    """``{material id: polyline}`` for the materials that name one.

    v0.1.126. Empty when no material points at an anisotropic surface,
    which is every project until somebody draws one — so the per-slice
    cost of the feature is a dictionary lookup that finds nothing.

    A material naming a surface that has been DELETED is left out rather
    than made to fail: the strength model then falls back on its own
    global bedding angle, which is what it did before the surface
    existed. Silently ignoring a dangling id would be wrong if it changed
    an answer, and it cannot: the fallback is the documented behaviour of
    a material with no surface.
    """
    wanted = {getattr(m, "anisotropic_surface_id", None): None
              for m in project.materials}
    wanted.pop(None, None)
    if not wanted:
        return {}
    by_id = {b.id: b.polyline for b in project.boundaries
             if b.btype == BoundaryType.ANISOTROPIC_SURFACE}
    out = {}
    for m in project.materials:
        sid = getattr(m, "anisotropic_surface_id", None)
        pl = by_id.get(sid) if sid else None
        if pl is not None:
            out[m.id] = pl
    return out


def _material_at(project: Project, point: Vertex) -> Optional[Material]:
    """Return the material occupying ``point`` in the project.

    v0.1.6: uses :meth:`Project.material_at` which resolves regions from
    the planar subdivision of ``External ∪ MaterialBoundaries`` and
    applies the user's click history (last winning assignment). Falls
    back to the first material of the project if no assignment covers
    the point (Slide default behaviour).
    """
    mat = project.material_at(point.x, point.y)
    if mat is not None:
        return mat
    return project.materials[0] if project.materials else None


# ----------------------------------------------------------------------
def _weak_layer_at(spans, x: float):
    """``(material, boundary_id)`` of the weak layer covering ``x``, or None.

    ``spans`` comes from :meth:`~ogr_slip2d.surface.WeakLayerSurface.spans`
    and is already sorted and non-overlapping, so a linear scan over a handful
    of stretches is the whole cost. The test is closed at both ends because
    the ends of every stretch are MANDATORY slice cuts: what falls on one is a
    slice boundary, never a slice centre, so the ambiguity cannot decide
    anything.
    """
    for a, b, mat, bid in spans:
        if a <= x <= b:
            return mat, bid
    return None


def _polyline_crossings_at_x(polyline: Polyline, x: float) -> list[float]:
    """Every y at which ``polyline`` crosses the vertical line at ``x``.

    Unlike ``interp_y_on_polyline``, which stops at the first hit because
    a water surface is single-valued in x, a material boundary may fold
    back and cross the same column twice — a lens or a wedge does exactly
    that, and taking only the first crossing would drop a band.
    """
    out: list[float] = []
    pts = polyline.vertices
    if len(pts) < 2:
        return out
    segments = list(zip(pts[:-1], pts[1:]))
    if getattr(polyline, "closed", False):
        segments.append((pts[-1], pts[0]))
    for p1, p2 in segments:
        lo, hi = (p1.x, p2.x) if p1.x <= p2.x else (p2.x, p1.x)
        if not (lo <= x <= hi):
            continue
        if abs(p2.x - p1.x) < 1e-12:
            # Vertical segment: it does not CUT the column, it lies along
            # it. Contributing its endpoints would invent bands of zero
            # thickness at best and a spurious cut at worst.
            continue
        t = (x - p1.x) / (p2.x - p1.x)
        out.append(p1.y + t * (p2.y - p1.y))
    return out


def _surface_crossings(
    surface: SurfaceProtocol,
    polyline: Polyline,
    x_l: float,
    x_r: float,
) -> list[float]:
    """Abscissas where the slip surface crosses ``polyline``.

    Both the slip surface and a boundary segment are single-valued in x,
    so the crossing is a sign change of ``g(x) = base_y(x) − line_y(x)``.
    Each boundary SEGMENT is scanned in a few sub-intervals rather than
    the whole range in many: a circular arc can cut one straight segment
    twice, and the sub-intervals separate the two roots, but a boundary
    has few segments so the total number of evaluations stays small.

    Sampling the whole range densely would have been simpler and much
    more expensive — this runs for every trial surface of a search.

    v0.1.111 — a surface that RUNS ALONG a boundary is not crossing it, and
    the two look identical to a sign test because both give ``g = 0``. The
    distinction is whether the zero is isolated: a crossing touches the
    line at a point, a coincident stretch gives zeros at consecutive
    samples. Composite Surfaces makes this reachable in an ordinary model —
    the slip surface then follows the floor of the External Boundary
    exactly, and a material boundary drawn along that same floor is what the
    reference tutorial for the option produces before asking the user to
    delete it. Without the distinction one such stretch emits about eight
    spurious cuts per segment, and the surface is refused whole for having
    more mandatory cuts than slices, saying nothing about why.
    """
    pts = polyline.vertices
    if len(pts) < 2:
        return []
    out: list[float] = []
    sub = 8  # sub-intervals per boundary segment

    def g(x: float, p1, p2) -> Optional[float]:
        by = surface.base_y_at(x)
        if by is None:
            return None
        t = (x - p1.x) / (p2.x - p1.x)
        return by - (p1.y + t * (p2.y - p1.y))

    for p1, p2 in zip(pts[:-1], pts[1:]):
        if abs(p2.x - p1.x) < 1e-12:
            continue  # vertical segment: no single-valued crossing
        lo = max(x_l, min(p1.x, p2.x))
        hi = min(x_r, max(p1.x, p2.x))
        if hi - lo <= 0.0:
            continue
        step = (hi - lo) / sub
        vals = [(lo + step * k, g(lo + step * k, p1, p2))
                for k in range(sub + 1)]
        for k in range(1, len(vals)):
            (xa, ga), (xb, gb) = vals[k - 1], vals[k]
            if ga is None or gb is None:
                continue
            if ga * gb < 0.0:
                a, b = xa, xb
                for _ in range(50):
                    m = 0.5 * (a + b)
                    gm = g(m, p1, p2)
                    if gm is None:
                        break
                    if ga * gm <= 0.0:
                        b = m
                    else:
                        a, ga = m, gm
                out.append(0.5 * (a + b))
        for k, (x, gx) in enumerate(vals):
            if gx != 0.0:
                continue
            neighbours = [vals[j][1] for j in (k - 1, k + 1)
                          if 0 <= j < len(vals)]
            if any(v == 0.0 for v in neighbours):
                continue          # a coincident stretch, not a crossing
            out.append(x)
    return out


def _slice_boundaries(
    project: Project,
    surface: SurfaceProtocol,
    x_l: float,
    x_r: float,
    num_slices: int,
) -> Optional[list[float]]:
    """Abscissas delimiting the slices, cuts at layer crossings included.

    v0.1.66 — until now this was a uniform division of the failure width
    and nothing else, so a slice could straddle a material boundary and
    have to pick ONE material for its base. Where the slip surface enters
    a different layer is a mandatory cut: the base of a slice belongs to
    one material or to another, never to a blend.

    The requested ``num_slices`` is shared among the resulting segments in
    proportion to their width, with at least one slice each. Returns None
    if there are more mandatory cuts than slices to spend on them, which
    is a real modelling error and not something to paper over: the answer
    is to ask for more slices.
    """
    width = x_r - x_l
    if width <= 0.0:
        return None

    # The y-range the slip surface spans. Used to throw away whole
    # boundaries before scanning them: a layer that runs well below the
    # failure mass cannot cut it, and checking that costs two comparisons
    # instead of eight evaluations per segment. Without it, this search ran
    # in full for every trial surface of a grid search and cost 20 %.
    #
    # v0.1.111 — ASKED OF THE SURFACE instead of worked out here. It used to
    # be an ``isinstance`` plus a peek at ``.polyline``, which is a rule
    # about two geometries written where a third could not be seen: a
    # composite surface has no ``.polyline``, so it would have answered with
    # the envelope of its two ENDS alone. On problem 22 that is (20, 60) for
    # a surface running along y = 15, and the weak layer at y = 16 — the
    # layer the whole problem is about — would have been culled by bounding
    # box and stopped being a mandatory cut, without a word.
    span = surface.y_span(x_l, x_r)
    if span is None:
        return None
    s_lo, s_hi = span

    # v0.1.89 — the slip surface's OWN kinks are mandatory cuts too, and
    # for the same reason as the layer crossings below: a slice base
    # belongs to one segment of the surface or to another, never to a
    # blend. A slice straddling a kink gets a base angle that is neither of
    # the two real ones.
    #
    # What that cost, found when nine test models stopped being degenerate
    # and non-circular searches could finally dive: Block Search returned
    # FoS 0.821 on a stable slope whose circular minimum is 1.124, on a
    # surface containing a NEARLY VERTICAL STEP 0.14 m wide — while the
    # slices were 1.26 m wide. The step fell inside a single slice, so no
    # slice base was steep, so the m-alpha check saw nothing to reject:
    # min m_alpha was 0.50 against a limit of 0.2. The geometry was not
    # wrong, it was invisible.
    #
    # Circles have no kinks, so this stays inert for every circular search
    # — the validated Ej_1 and Ej_2 benchmarks cannot move.
    cuts: set = set(surface.kinks(x_l, x_r))

    for b in project.boundaries:
        if b.btype not in (BoundaryType.MATERIAL, BoundaryType.WATER_TABLE):
            continue
        bx0, by0, bx1, by1 = b.bounding_box()
        if bx1 < x_l or bx0 > x_r or by1 < s_lo or by0 > s_hi:
            continue
        for x in _surface_crossings(surface, b.polyline, x_l, x_r):
            # Ignore a crossing that merely grazes an end: it would make a
            # sliver slice without separating anything.
            if x_l + 1e-9 < x < x_r - 1e-9:
                cuts.add(x)

    if not cuts:
        step = width / num_slices
        return [x_l + step * i for i in range(num_slices + 1)]

    marks = sorted(cuts)
    # Merge cuts closer together than a thousandth of the failure width:
    # two layers pinching out at nearly the same point are one cut, and
    # the tolerance is RELATIVE so it behaves the same in mm and in m.
    tol = 1e-3 * width
    merged = [marks[0]]
    for x in marks[1:]:
        if x - merged[-1] > tol:
            merged.append(x)
    segments = list(zip([x_l] + merged, merged + [x_r]))
    if len(segments) > num_slices:
        return None

    # Largest-remainder apportionment, so the slice count is exactly the
    # one asked for and the widths stay as even as the cuts allow.
    raw = [num_slices * (b - a) / width for a, b in segments]
    counts = [max(1, int(r)) for r in raw]
    while sum(counts) > num_slices:
        i = max(range(len(counts)),
                key=lambda k: (counts[k] - raw[k], counts[k]))
        if counts[i] <= 1:
            break
        counts[i] -= 1
    while sum(counts) < num_slices:
        i = max(range(len(counts)), key=lambda k: raw[k] - counts[k])
        counts[i] += 1

    bounds = [x_l]
    for (a, b), n in zip(segments, counts):
        step = (b - a) / n
        bounds.extend(a + step * k for k in range(1, n + 1))
    bounds[-1] = x_r
    return bounds


def _mean_polyline_y(polyline: Polyline, x_l: float, x_r: float) -> Optional[float]:
    """Mean elevation of a piecewise-linear profile over ``[x_l, x_r]``.

    v0.1.96 — the reason this is not ``½(y(x_l) + y(x_r))``: a profile
    VERTEX falling inside the interval is a kink, and the chord between the
    two ends cuts the corner. On the Ej_2 reference model the crest vertex
    at x = 40 lands inside slice 23, whose weight came out 137.192 against
    the reference's 138.072 — every other slice of the 25 agreeing to 1e-5.

    The integral is exact rather than sampled: the profile is linear
    between breakpoints, so splitting at every breakpoint inside the
    interval and summing trapezia leaves no error at all.

    v0.1.114 — the two ends of each sub-interval are read off the SEGMENT
    that spans it rather than by interpolating the profile at an abscissa.
    The profile is an envelope now, and an envelope steps at a vertical
    face: asking for "y at x" exactly on the step is ambiguous — the bench
    at the foot of a wall and the crest above it share that abscissa — while
    "y at the two ends of this segment" never is. Integrating a step
    function this way is exact, which is what the docstring above promises.

    Returns None when the profile does not span the interval.
    """
    if x_r <= x_l:
        return None
    xs = {x_l, x_r}
    for v in polyline.vertices:
        if x_l < v.x < x_r:
            xs.add(v.x)
    marks = sorted(xs)
    area = 0.0
    for a, b in zip(marks[:-1], marks[1:]):
        pair = _segment_y_pair(polyline, a, b)
        if pair is None:
            return None
        area += 0.5 * (pair[0] + pair[1]) * (b - a)
    return area / (x_r - x_l)


def _segment_y_pair(polyline: Polyline, a: float, b: float):
    """``(y(a), y(b))`` on the profile segment that spans ``[a, b]``.

    ``a`` and ``b`` are consecutive marks, so exactly one non-degenerate
    segment covers the interval; the vertical segments an envelope uses for
    its jumps span no interval and are skipped. Returns None when nothing
    covers it, which is how :func:`_mean_polyline_y` reports a profile that
    falls short of the slice.
    """
    if b <= a:
        return None
    for p1, p2 in zip(polyline.vertices[:-1], polyline.vertices[1:]):
        lo, hi = (p1.x, p2.x) if p1.x <= p2.x else (p2.x, p1.x)
        if hi - lo < 1e-12 or a < lo - 1e-12 or b > hi + 1e-12:
            continue
        t = (p2.y - p1.y) / (p2.x - p1.x)
        return (p1.y + (a - p1.x) * t, p1.y + (b - p1.x) * t)
    return None


def _column_weight(
    project: Project,
    x: float,
    y_bottom: float,
    y_top: float,
    dx: float,
) -> tuple[float, float]:
    """Weight per unit width of the soil column at ``x`` (kN/m), and the
    top of the material band the BOTTOM of the column sits in.

    The column is cut at every material boundary and at every water table
    crossing it, and each band is weighed with the unit weight of the
    material that occupies it, saturated or not according to whether it
    sits below the free water surface.

    With a single material and no water table crossing the column this
    reduces to ``γ · (y_top − y_bottom) · dx``, which is what the previous
    implementation computed — so a one-layer model keeps its factor of
    safety to the last bit.

    v0.1.120 — the LAYER TOP comes back with the weight because it is the
    same measurement: the bands and the material of each are already
    resolved here, so finding where the bottom one ends costs a handful of
    comparisons on work that was already paid for. Computing it separately
    would have meant a second pass over the same boundaries and a second
    region lookup, per slice, on every trial surface of a search.
    """
    height = y_top - y_bottom
    if height <= 0.0:
        return 0.0, y_top

    # Candidate cuts: where the material can change, and where saturation
    # can change. Piezometric and drawdown lines are NOT included — they
    # do not decide the unit weight (see ``ogr_core.hydraulic``).
    cuts = {y_bottom, y_top}
    for b in project.boundaries:
        if b.btype not in (BoundaryType.MATERIAL, BoundaryType.WATER_TABLE):
            continue
        for y in _polyline_crossings_at_x(b.polyline, x):
            if y_bottom < y < y_top:
                cuts.add(y)

    wt_y = water_table_y_at(project, x)
    ys = sorted(cuts)

    # A cut landing on top of another produces a zero-thickness band;
    # skipping it is cheaper than de-duplicating with a tolerance that
    # would have to scale with the model.
    bands = [(lo, hi) for lo, hi in zip(ys[:-1], ys[1:]) if hi > lo]
    if not bands:
        return 0.0, y_top

    mids = [(x, 0.5 * (lo + hi)) for lo, hi in bands]
    if len(project.materials) == 1:
        # With a single material every region resolves to it, and so does
        # the no-region fallback, so the planar subdivision cannot change
        # the answer. Worth special-casing because the region lookup is
        # dominated by validating its own cache, not by the geometry.
        mats = [project.materials[0]] * len(bands)
    else:
        # One regions lookup for the whole column, not one per band: the
        # cache validation inside ``resolve_regions`` costs more than the
        # point-in-polygon scan it protects.
        mats = project.materials_at(mids)

    fallback = project.materials[0] if project.materials else None
    mats = [fallback if m is None else m for m in mats]

    total = 0.0
    for (lo, hi), mat, (_mx, y_mid) in zip(bands, mats, mids):
        below_water = wt_y is not None and wt_y > y_mid
        gamma = mat.gamma_at(below_water) if mat else 20.0
        total += gamma * (hi - lo) * dx

    # The layer top: walk up from the bottom band and stop at the first
    # band made of a DIFFERENT material. Identity is compared through the
    # material id, because a water table crossing splits a band without
    # changing what fills it, and two consecutive bands of the same layer
    # must not be mistaken for a contact. Reaching the top of the column
    # without a change means the layer runs to the ground surface.
    base_key = _material_key(mats[0])
    layer_top = y_top
    for (lo, _hi), mat in zip(bands, mats):
        if _material_key(mat) != base_key:
            layer_top = lo
            break
    return total, layer_top


def _material_key(material) -> Optional[str]:
    """Identity of a material for band comparison; None if there is none."""
    return getattr(material, "id", None) if material is not None else None


# ----------------------------------------------------------------------
def line_loads_on(project: Project, x_left: float, x_right: float):
    """Line loads whose point of application falls in ``[x_left, x_right)``.

    v0.1.75 — until this version the limit-equilibrium engine contained
    **no reference at all** to line loads. They could be drawn, saved,
    exported to DXF and factored by a design standard, and the analysis
    never read them: a line load of 5000 kN/m moved the factor of safety
    by exactly zero, on the unsafe side, because the user believes the
    slope has been loaded.

    The half-open interval matters. A load sitting exactly on a slice
    boundary must be counted once, not twice or never, and the last
    slice needs its right edge closed so a load at the very end of the
    surface is not silently dropped.
    """
    out = []
    loads = getattr(project, "line_loads", None) or []
    for load in loads:
        x = load.point.x
        if x_left - 1e-12 <= x < x_right - 1e-12:
            out.append(load)
    return out


def _line_load_components(load) -> tuple[float, float]:
    """(downward, +x) components of a line load, in kN/m.

    ``direction_vector`` points the way the load pushes, with -y meaning
    downwards, so the vertical component is negated to give a downward
    positive number — the same sign convention ``weight`` uses.
    """
    dx, dy = load.direction_vector()
    return -load.magnitude * dy, load.magnitude * dx


#: A load segment narrower than this in x has no horizontal extent to
#: spread a pressure over, and is treated as a line load of the integrated
#: magnitude — see :func:`distributed_loads_on`. Relative to the model, not
#: absolute: the same tolerance must not mean different things in metres
#: and in millimetres.
_VERTICAL_SEGMENT_FRACTION = 1e-9


def _is_vertical_segment(load, span: float) -> bool:
    """Whether a load segment is vertical, to within the model size."""
    return abs(load.end.x - load.start.x) <= _VERTICAL_SEGMENT_FRACTION * span


def _surface_pressure_at(project: Project, x: float) -> float:
    """Sum of distributed-load pressures acting at x (vertical component).

    In kPa, and per unit HORIZONTAL length: the caller multiplies by the
    slice width. That is the convention the whole engine has used since
    the class existed, and v0.1.122 did not change it — it only completed
    it, by giving the horizontal component of the same load the channel it
    never had (:func:`distributed_loads_on`). The two together make the
    resultant on a slice ``p·dx``, so ``p`` is a pressure over the
    horizontal projection of the loaded boundary.

    A load whose segment is VERTICAL has no horizontal projection at all,
    so it cannot be expressed here and is handled by
    :func:`distributed_loads_on` instead. Before v0.1.122 such a load
    contributed nothing anywhere, silently.
    """
    total = 0.0
    for load in project.distributed_loads:
        x1, x2 = load.start.x, load.end.x
        lo, hi = min(x1, x2), max(x1, x2)
        if lo <= x <= hi:
            t = 0.0 if abs(x2 - x1) < 1e-12 else (x - x1) / (x2 - x1)
            t = max(0.0, min(1.0, t))
            p = load.pressure_at(t)
            # Vertical component of the pressure
            _, dy = load.direction_vector()
            total += abs(p * dy)  # kPa
    return total


def distributed_loads_on(project: Project, x_left: float, x_right: float,
                         span: float):
    """Distributed-load forces on the slice ``[x_left, x_right)``.

    Yields ``(f_h, f_v_extra, y)``: the HORIZONTAL force in kN/m signed in
    +x, an EXTRA downward force for the vertical-segment case only, and the
    elevation the horizontal force acts at.

    v0.1.122 — until this version the horizontal component of a distributed
    load was **discarded entirely**. :func:`_surface_pressure_at` kept
    ``abs(p·dy)`` and nothing else, so a load declared ``HORIZONTAL`` moved
    the factor of safety by exactly zero: a configurable orientation that
    could not change the result. It also meant a pressure on a vertical
    face — a wall back, a cut face — did nothing at all, and that is the
    shape of the published verification this feature was written for.

    Two cases, and the second is the one that could not be expressed at all:

    * **A segment with horizontal extent.** The force on the part of the
      segment inside this slice is ``p·dx`` in the load's own direction,
      the same convention :func:`_surface_pressure_at` uses for the
      vertical half. The vertical half is NOT repeated here — the slicer
      has already put it in the slice weight — so only the horizontal one
      comes back, at the elevation of the loaded boundary.

    * **A vertical segment.** There is no horizontal extent to spread a
      pressure over, so the pressure is taken per unit length of the
      segment, integrated over the whole of it, and applied at the
      CENTROID of the resulting diagram to the slice that contains its
      abscissa. That is a line load of the integrated magnitude, which is
      what a pressure on a face of zero width is. Here the vertical part
      does come back, because ``_surface_pressure_at`` could not see it.

    The half-open interval is the one :func:`line_loads_on` uses, and for
    the same reason: a load sitting exactly on a slice boundary must be
    counted once, not twice and not never.
    """
    out = []
    for load in getattr(project, "distributed_loads", None) or []:
        dxu, dyu = load.direction_vector()
        x1, x2 = load.start.x, load.end.x
        if _is_vertical_segment(load, span):
            x = 0.5 * (x1 + x2)
            if not (x_left - 1e-12 <= x < x_right - 1e-12):
                continue
            y1, y2 = load.start.y, load.end.y
            L = abs(y2 - y1)
            if L <= 0.0:
                continue
            # ∫p ds and its first moment, exact for the linear ramp
            # ``pressure_at`` describes: p(t) = p1 + (p2 − p1)·t.
            p1, p2 = load.pressure_at(0.0), load.pressure_at(1.0)
            total = 0.5 * (p1 + p2) * L
            if not total:
                continue
            # Centroid of a trapezium along the segment, measured from the
            # start end. Reduces to L/2 for a uniform load and to 2L/3 for
            # a triangle growing towards the far end, as it must.
            denom = p1 + p2
            t_c = ((p1 + 2.0 * p2) / (3.0 * denom)) if denom else 0.5
            y_c = y1 + (y2 - y1) * t_c
            out.append((total * dxu, -total * dyu, y_c))
            continue

        lo, hi = min(x1, x2), max(x1, x2)
        a, b = max(lo, x_left), min(hi, x_right)
        if b <= a:
            continue
        if not dxu:
            continue
        xm = 0.5 * (a + b)
        t = max(0.0, min(1.0, (xm - x1) / (x2 - x1)))
        p = load.pressure_at(t)
        if not p:
            continue
        y = load.start.y + (load.end.y - load.start.y) * t
        out.append((p * dxu * (b - a), 0.0, y))
    return out


# ----------------------------------------------------------------------
def negative_pore_pressure_cutoff(project) -> Optional[float]:
    """The project's cap on matric suction, or None when there is none.

    Defensive on purpose: a project built in a test without full settings
    gets the documented default, which is no cap at all.
    """
    try:
        v = project.settings.groundwater.negative_pore_pressure_cutoff
    except AttributeError:
        return None
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return abs(v) if math.isfinite(v) else None


def apply_unsaturated_policy(u: float, material,
                             cutoff: Optional[float] = None
                             ) -> tuple[float, float]:
    """Apply the extended Mohr-Coulomb treatment of matric suction.

    A seepage analysis returns NEGATIVE pore pressures above the water
    table (matric suction). Feeding them straight into the effective
    stress would credit the full saturated friction angle to the suction
    all the way up, which overestimates strength. The reference instead
    uses the extended Mohr-Coulomb envelope of Fredlund et al. (1978),
    controlled by two per-material parameters:

        phi_b            unsaturated shear strength angle
        air_entry_value  suction below which the soil is still
                         effectively saturated

    giving a BILINEAR envelope:

        u >= 0                  ->  u unchanged, no extra cohesion
        0 < suction <= AEV      ->  u unchanged (saturated phi' governs)
        suction > AEV           ->  u capped at -AEV, and the excess
                                    suction contributes an extra
                                    cohesion (suction - AEV)*tan(phi_b)

    With the defaults phi_b = 0 and AEV = 0 (the reference defaults) any
    negative pore pressure is clamped to zero and contributes nothing:
    exactly the conservative "truncate u at 0" behaviour, obtained as a
    special case rather than as a separate switch.

    ``cutoff`` is the project's **negative pore pressure cutoff**: the
    largest suction allowed to reach the strength calculation, applied
    BEFORE the envelope because what it bounds is the pressure, not the
    cohesion derived from it. ``None`` means no limit, which is the
    reference default and what this function did until v0.1.125 — and
    also the reason it exists: with no limit, a slope that has drained
    for a long time develops suction all the way to the crest, and
    ``(suction - AEV)*tan(phi_b)`` then hands it a cohesion that no
    laboratory ever measured.

    Returns ``(u_effective, extra_cohesion)``.
    """
    if u >= 0.0 or material is None:
        return u, 0.0
    if cutoff is not None:
        # The reference states it takes the negative of the absolute
        # value, so the sign the user typed cannot change the meaning.
        u = max(u, -abs(float(cutoff)))
    suction = -u
    aev = max(getattr(material, "air_entry_value", 0.0) or 0.0, 0.0)
    if suction <= aev:
        # Still effectively saturated: the real negative u is kept and
        # the saturated friction angle credits the suction.
        return u, 0.0
    phi_b = getattr(material, "phi_b", 0.0) or 0.0
    extra_c = (suction - aev) * math.tan(math.radians(phi_b))
    return -aev, max(0.0, extra_c)


def _reverse_curvature_mode(project: Project) -> str:
    """Which treatment the project asks for on reverse-curvature circles.

    Defensive on purpose: a project built in a test without full settings
    gets the documented default, which is to create the tension crack.
    """
    try:
        on = project.settings.search.create_tension_crack_reverse_curvature
    except AttributeError:
        return "tension_crack"
    return "tension_crack" if on else "discard"


def tension_crack_boundary(project: Project):
    """The project's Tension Crack boundary, or None.

    Only one can exist by construction (the interface disables *Add
    Tension Crack* once there is one), but the engine has never enforced
    it, so the first is taken and the rest ignored — the same rule the
    code has followed since v0.1.7.
    """
    for b in project.boundaries:
        if b.btype == BoundaryType.TENSION_CRACK:
            return b
    return None


def apply_tension_crack_truncation(
    project: Project,
    surface: SurfaceProtocol,
    ground: Polyline,
    x_left: float,
    x_right: float,
):
    """Truncate ``surface`` where it meets the Tension Crack boundary.

    Returns ``(x_l, x_r)`` for the surface as it must be analysed, or
    ``None`` to DISCARD it. The wall it leaves is recorded on the surface
    as ``tension_crack_wall`` and appended to ``tension_cracks`` so the
    canvas draws it.

    What a tension crack does
    -------------------------
    A tension crack terminates the slip surface: the soil above the crack
    cannot carry tension, so no shear resistance may be counted along it.
    Where the surface reaches the crack boundary the failure mass is
    closed by a VERTICAL wall running up to the ground surface, and the
    soil between that wall and the arc keeps every bit of its weight —
    it is driving weight with no base of its own. This is the treatment
    described by Duncan & Wright (2005), *Soil Strength and Slope
    Stability*, chapter 14, and the one the classical formulations assume
    when they shorten the arc and leave the wedge in the weight.

    Three rules, and each has a source
    ----------------------------------
    * **Only the crest end is truncated.** The crack forms at the head of
      the slide, where the interslice forces go into tension; the toe is
      in compression. Soil in the crack zone at the TOE end therefore
      keeps its strength. (Measured: on ACADS 1(b) five of twenty-five
      slices have their base inside the crack zone on the toe side, and
      the published factor is only reproduced with them resisting.)
    * **The crest must be inside the crack zone**, or nothing happens —
      which is also what makes this idempotent, since after truncation
      the crest sits ON the crack line rather than above it.
    * **The first crossing from the crest wins** when the surface enters
      and leaves the zone more than once.

    A surface whose crest is inside the zone and which never reaches the
    crack boundary lies ENTIRELY inside a region that cannot resist. It
    is discarded rather than answered: a factor of safety computed on it
    would be arithmetic about a mechanism that has no shear surface. The
    reference reports the same case as its own error code.
    """
    from .failure_direction import crest_end_is_on_the_right

    def _remember(wall) -> None:
        """Record the wall, defensively.

        ``SurfaceProtocol`` is a protocol, not a base class, so a caller
        may hand in something of its own that has no such field — the
        same reason ``_reverse_curvature_mode`` is written defensively.
        Nothing downstream needs the wall except the water thrust, and a
        surface that cannot carry one cannot be pushed on either.
        """
        try:
            surface.tension_crack_wall = wall
        except AttributeError:  # pragma: no cover - foreign surface type
            pass

    tc = tension_crack_boundary(project)
    if tc is None or len(tc.polyline.vertices) < 2:
        # Cleared, not merely skipped: the same surface object may have
        # been analysed against a project that HAD a crack, and a wall
        # left behind would push on a mass that has none.
        _remember(None)
        return (x_left, x_right)

    crest_right = crest_end_is_on_the_right(project, ground, x_left, x_right)
    x_crest = x_right if crest_right else x_left

    # Already truncated at this very end — the search resolves its own
    # chords and cuts them before the slicer ever sees them, and a caller
    # may hand the same surface back for a second pass. Re-entering must
    # neither cut again nor forget the wall it cut last time.
    prev = getattr(surface, "tension_crack_wall", None)
    if prev is not None and abs(prev[0] - x_crest) <= 1e-9 * max(
            x_right - x_left, 1.0):
        return (x_left, x_right)
    _remember(None)

    # Is the crest of the SURFACE inside the crack zone? The zone is the
    # region above the crack boundary; outside the boundary's own x range
    # there is no zone at all, and ``_interp_y_on_polyline`` says so by
    # returning None.
    y_crack_at_crest = _interp_y_on_polyline(tc.polyline, x_crest)
    if y_crack_at_crest is None:
        return (x_left, x_right)
    y_surface_at_crest = surface.base_y_at(x_crest)
    if y_surface_at_crest is None:
        return (x_left, x_right)
    # Tolerance relative to the surface's own extent, which is the length
    # scale this question has — so the same slope answers it the same way
    # in millimetres and in metres. A crest sitting ON the line is NOT
    # inside the zone, and that is what stops a second pass from
    # truncating an already-truncated surface.
    tol = 1e-9 * max(x_right - x_left, 1.0)
    if y_surface_at_crest <= y_crack_at_crest + tol:
        return (x_left, x_right)

    crossings = _surface_crossings(surface, tc.polyline, x_left, x_right)
    if not crossings:
        # Entirely within the tension crack zone.
        return None
    x_wall = max(crossings) if crest_right else min(crossings)
    if abs(x_wall - (x_left if crest_right else x_right)) < 1e-9 * max(
            x_right - x_left, 1.0):
        # Truncating would leave no mass at all.
        return None

    y_bottom = _interp_y_on_polyline(tc.polyline, x_wall)
    y_top = envelope_y_at(ground, x_wall)
    if y_bottom is None or y_top is None or y_top <= y_bottom:
        return (x_left, x_right)

    wall = (x_wall, y_bottom, y_top)
    _remember(wall)
    try:
        surface.tension_cracks.append(wall)
    except AttributeError:      # a surface type without the channel
        pass

    if crest_right:
        return (x_left, x_wall)
    return (x_wall, x_right)


def _truncate_polyline_surface(surface, x_l: float, x_r: float) -> None:
    """Cut a non-circular slip surface down to ``[x_l, x_r]``, in place.

    The vertices outside the range go, and the exact cut point is added
    so the polyline still ends where the tension crack does — dropping
    the vertices alone would leave the end at the last SURVIVING vertex,
    short of the crack by up to one segment.
    """
    verts = surface.polyline.vertices
    y_l = surface.base_y_at(x_l)
    y_r = surface.base_y_at(x_r)
    if y_l is None or y_r is None:
        return
    kept = [v for v in verts if x_l < v.x < x_r]
    surface.polyline.vertices = (
        [Vertex(x_l, y_l)] + kept + [Vertex(x_r, y_r)])


def slice_surface(
    project: Project,
    surface: SurfaceProtocol,
    num_slices: int = 50,
) -> Optional[Slices]:
    """Build the list of slices for a given slip surface.

    Returns None if the surface does not intersect the ground twice, the
    failure mass is degenerate, or — since v0.1.109 — the surface lies
    entirely inside a Tension Crack zone and so has no shear plane to
    write an equilibrium on.

    The surface is resolved onto the mass that is actually analysed
    before slicing: ground crossings, reverse curvature, and the user's
    tension crack. It is left carrying that resolution, because a drawing
    of the untruncated surface next to the number of the truncated one
    would be a picture of a different problem.
    """
    external = project.external_boundary()
    if external is None:
        return None

    # For circles, compute ground intersections if not cached.
    #
    # v0.1.111 — and for COMPOSITE surfaces, which are resolved the same
    # way: their endpoints are ground crossings of the arc they were built
    # from, the search hands them over already resolved, and a tension
    # crack truncates them by moving an abscissa exactly as it does on a
    # circle. What they must NOT take is the polyline branch below, which
    # would try to cut a ``.polyline`` they do not have.
    # v0.1.121 — a WEAK-LAYER surface joins the two that arrive already
    # resolved. Its endpoints come from the surface it was clipped from,
    # and the tension crack that may have moved them ran BEFORE the
    # clipping: what it must not take is the polyline branch below, which
    # would try to cut a .polyline it does not have.
    if isinstance(surface, (SlipCircle, CompositeSurface, WeakLayerSurface)):
        ground = _ground_surface_from_external(external)
        if surface.x_left is None or surface.x_right is None:
            if surface.intersect_with_ground(ground) is None:
                return None
            # v0.1.82 — reverse curvature. Until now
            # ``create_tension_crack_reverse_curvature`` was stored in the
            # project, edited in the dialog and read by nobody, so a circle
            # whose entry point sits above its own centre was sliced from
            # the true ground crossing while its base was drawn on the
            # LOWER arc, metres below the ground. On the reference model
            # 522 of 4851 grid circles (16 %) were affected, and one of
            # them came out 31 % high. Applied only on a fresh
            # intersection so a cached (x_left, x_right) is never
            # re-cracked.
            if not surface.apply_reverse_curvature(
                    ground, mode=_reverse_curvature_mode(project)):
                return None
        # v0.1.109 — the user's Tension Crack boundary. UNLIKE reverse
        # curvature this runs whether or not the endpoints were cached,
        # because a cached pair is not evidence that anything truncated
        # it: a search hands over chords it resolved itself, and so does
        # any caller that picked a mass by hand. Applying it only on a
        # fresh resolution left verification problem 27 untruncated while
        # problem 2 worked, which is the least useful kind of bug.
        # ``apply_tension_crack_truncation`` recognises its own work, so a
        # second pass over an already-cut surface changes nothing.
        _lim = apply_tension_crack_truncation(
            project, surface, ground, surface.x_left, surface.x_right)
        if _lim is None:
            return None
        surface.x_left, surface.x_right = _lim
        x_l, x_r = surface.x_left, surface.x_right
    else:
        ground = _ground_surface_from_external(external)
        x_l, x_r = surface.x_range()
        if x_l is None or x_r is None or x_r - x_l < 1e-6:
            return None
        # A polyline carries no cached endpoints, so the truncation is
        # applied to the polyline ITSELF. That keeps ``x_range`` the one
        # source of truth, makes a second pass a no-op, and — the reason
        # it is done here rather than locally — leaves the drawn surface
        # and the computed number describing the same mass.
        _lim = apply_tension_crack_truncation(
            project, surface, ground, x_l, x_r)
        if _lim is None:
            return None
        if _lim != (x_l, x_r):
            _truncate_polyline_surface(surface, *_lim)
        x_l, x_r = surface.x_range()

    if x_l is None or x_r is None or x_r - x_l < 1e-6:
        return None

    bounds = _slice_boundaries(project, surface, x_l, x_r, num_slices)
    if bounds is None:
        # More mandatory cuts than slices to spend: the reference reports
        # this as an error and asks for more slices, and so do we, rather
        # than silently dropping layer crossings.
        return None
    # A mean slice narrower than a ten-thousandth of the model is a
    # numerical hazard, not a finer answer. Relative to the failure width,
    # so the check reads the same whatever the units of the model.
    if (x_r - x_l) / max(len(bounds) - 1, 1) < 1e-4 * (x_r - x_l):
        return None

    result = Slices()

    # v0.1.125 — the project's negative pore pressure cutoff, read ONCE
    # for the same reason as the line below: it cannot change while a
    # surface is being sliced, and a per-slice lookup would ask the same
    # question a thousand times per surface.
    _u_cutoff = negative_pore_pressure_cutoff(project)

    # v0.1.120 — asked ONCE, of the project, not once per slice: whether
    # any material's strength model reads the distance to the slope face.
    wants_slope_distance = any(
        getattr(getattr(m, "strength", None), "NEEDS_SLOPE_DISTANCE", False)
        for m in project.materials)

    # v0.1.126 — the anisotropic surfaces the materials of THIS project
    # point at, resolved once. Not once per slice: the lookup walks the
    # boundary list, and the mapping cannot change while a surface is
    # being sliced. Empty for every model that has none, which is all of
    # them until somebody draws one, so the cost is one ``any()``.
    aniso_by_material = _anisotropic_surfaces(project)

    # v0.1.121 — the stretches where a weak layer IS the surface, resolved to
    # materials once instead of once per slice. Empty for every surface that
    # no joint clips, which is every surface of every model without weak
    # layers: the loop below then pays one truth test per slice.
    #
    # A stretch whose layer has no material assigned is dropped rather than
    # given a null one. The layer still shapes the surface — that is geometry,
    # and the user drew it — but a base with no material would take the
    # fallback material of the project without a word, and a joint silently
    # made of the surrounding soil is worse than one that was never there.
    # ``weak_layer_model_warnings`` says so once, at the start of the run.
    weak_spans: tuple = ()
    if isinstance(surface, WeakLayerSurface):
        weak_spans = tuple(
            (a, b, project.material_by_id(band.material_id), band.boundary_id)
            for a, b, band in surface.spans()
            if band.material_id
            and project.material_by_id(band.material_id) is not None
        )

    # v0.1.100 — THE SLICER BUILDS ONE SLICE PER INTERVAL, OR NONE AT ALL.
    #
    # Every branch below that used to ``continue`` now abandons the surface.
    # Skipping one interval does not produce a coarser answer, it produces an
    # answer for a DIFFERENT, shorter surface, and says nothing about it —
    # which is anomaly A23-1: on the reference circle of verification problem
    # 23 the last slice was dropped for a one-ulp geometric round-off and
    # Bishop came out at 0.897 against a published 1.192, with the deficit
    # shrinking only as 1/sqrt(n) so that refining looked like convergence.
    # The precedent is right above: ``_slice_boundaries`` returning None
    # already discards the surface rather than swallow a layer crossing.
    #
    # The last boundary is the last index of ``bounds``, needed below to tell
    # the two chord ENDS from the interior cuts.
    last_i = len(bounds) - 2

    # Overshoot tolerance, RELATIVE to the failure width, replacing an
    # absolute 1e-4 that meant something different in millimetres and in
    # metres. Sized to the same order that absolute value had on the models
    # it was chosen for, because what it forgives is unchanged: root-finding
    # round-off, "a few 1e-6" by the v0.1.18 note.
    tol = 1e-6 * (x_r - x_l)

    # Whether the two extreme boundaries can be clamped without asking. On a
    # CIRCLE they can: ``candidate_chords`` returns crossings of the arc with
    # the ground, so the base is the ground there by construction and any
    # difference is the root-finder's own error — which a vertical tangent
    # multiplies by dy/dx, 1600 on the problem-23 circle, so no tolerance on
    # y survives it. A polyline's endpoints are just its first and last
    # vertices and carry no such guarantee, so they stay judged.
    ends_are_ground_crossings = isinstance(
        surface, (SlipCircle, CompositeSurface))

    for i, (xl, xr) in enumerate(zip(bounds[:-1], bounds[1:])):
        dx = xr - xl
        if dx <= 0.0:
            return None
        xc = 0.5 * (xl + xr)

        y_base_l = surface.base_y_at(xl)
        y_base_r = surface.base_y_at(xr)
        if y_base_l is None or y_base_r is None:
            return None

        # v0.1.114 — one-sided, and it has to be. A slice corner landing
        # exactly on a step of the envelope — the foot of a wall, where the
        # bench in front and the crest behind share an abscissa — must take
        # the branch this slice's own body sits on: the right-hand branch at
        # its left corner and the left-hand branch at its right one. Asking
        # for "the ground at that x" answers with the crest for both, and
        # the slice in front of the wall then reports 20 ft of soil that is
        # not above it. ``side=0`` is the fallback at the two ends of the
        # profile, where one of the branches does not exist.
        y_top_l = envelope_y_at(ground, xl, side=1)
        if y_top_l is None:
            y_top_l = envelope_y_at(ground, xl)
        y_top_r = envelope_y_at(ground, xr, side=-1)
        if y_top_r is None:
            y_top_r = envelope_y_at(ground, xr)
        if y_top_l is None or y_top_r is None:
            return None

        # v0.1.18 — at the slip-surface endpoints the circular arc can
        # sit a few 1e-6 ABOVE the ground purely from root-finding
        # round-off. Clamp the base to the ground there instead of
        # dropping the slice; dropping it lost the first/last slice and
        # produced 24 slices where Slide builds 25, biasing the FoS by
        # ~1%.
        #
        # v0.1.100 — on a circle the two ENDS are not a tolerance question
        # at all; see ``ends_are_ground_crossings`` above. Everything else
        # is judged, against a tolerance relative to the model.
        if y_base_l > y_top_l:
            if ((i == 0 and ends_are_ground_crossings)
                    or y_base_l - y_top_l <= tol):
                y_base_l = y_top_l
            else:
                return None
        if y_base_r > y_top_r:
            if ((i == last_i and ends_are_ground_crossings)
                    or y_base_r - y_top_r <= tol):
                y_base_r = y_top_r
            else:
                return None

        # v0.1.100 — THE BASE OF A SLICE IS THE CHORD between its two
        # endpoints, not the tangent at its midpoint.
        #
        # Both the derivation of Bishop (1955) and those of the other eight
        # methods treat a slice base as a STRAIGHT segment, and write its
        # horizontal projection as ``b = l·cos α``. Taking α from the
        # tangent at the midpoint and then l from ``b/cos α`` satisfies that
        # identity too, but it measures the arc with a secant of the
        # midpoint slope, and where the arc turns quickly inside one slice
        # that secant is far too short: at a vertical tangent it converges
        # to 1/sqrt(2) of the true arc, however fine the slicing.
        #
        # Measured against a CLOSED FORM — a homogeneous phi = 0 slope,
        # where moment equilibrium gives F = c·L_arc·R/M exactly — on a
        # circle whose exit is tangent:
        #
        #     n      midpoint tangent      chord
        #     30        -2.63 %           +1.41 %
        #     120       -1.90 %           +0.20 %
        #     3840      -0.37 %            +0.00 %   (O(1/sqrt(n)) vs O(1/n))
        #
        # And on the two published circles of verification problem 23, with
        # the slice counts of the problem itself:
        #
        #     Bishop   (published 1.192)   30 slices   1.19204   +0.00 %
        #     Ordinary (published 1.370)   30 slices   1.36835   -0.12 %
        #
        # against -4.34 % and -0.75 % with the midpoint tangent. Away from a
        # vertical tangent the two agree to a few 1e-4: on the validated
        # benchmarks the change is -0.014 % (Ej_1 Bishop), -0.018 % (Ej_1
        # Janbu), -0.015 % (Ej_1 Spencer) and -0.043 % (Ej_2 Bishop).
        #
        # It also makes the circular and non-circular paths describe the same
        # base: ``_general_moment_fos`` has taken the chord since v0.1.92.
        dy = y_base_r - y_base_l
        alpha = math.atan2(dy, dx)
        base_len = math.hypot(dx, dy)

        # See ``Slice.weight_arm_ratio``: the chord's own angle is no longer
        # the tangent at ``xc``, so the moment arm is taken from the geometry
        # instead of from the angle.
        #
        # v0.1.111 — asked for a CENTRE rather than for a class. The arm of
        # a vertical force about a point depends only on its abscissa, so
        # ``(xc - centre_x)/R`` is the true normalised arm on every surface
        # that has a centre — including a composite, whose straight
        # stretches are no exception. Answering ``sin(alpha)`` there would
        # write a number into the slice that is not the arm of anything.
        _centre_x = getattr(surface, "centre_x", None)
        _radius = getattr(surface, "radius", 0.0) or 0.0
        if _centre_x is not None and _radius > 0.0:
            arm_ratio = (xc - _centre_x) / _radius
        else:
            arm_ratio = math.sin(alpha)

        # Material at the base midpoint. This one stays a single query:
        # the base is where the shear strength and the pore pressure are
        # evaluated, and both belong to the material the base cuts.
        base_y_mid = 0.5 * (y_base_l + y_base_r)
        top_y_mid = 0.5 * (y_top_l + y_top_r)
        mat = _material_at(project, Vertex(xc, base_y_mid + 0.01))

        # v0.1.121 — where the base runs ALONG a weak layer, the strength is
        # the joint's and not the region's. Only the material is swapped, and
        # deliberately not the weight: a joint has no thickness, so there is
        # nothing of it to weigh, and ``_column_weight`` below keeps
        # integrating the column band by band out of the regions the model
        # really has.
        #
        # The pore pressure follows the joint's material too, because
        # ``pore_pressure_at`` is asked with it. That is a decision and not an
        # oversight: a weak layer is declared as a material, with its own
        # water surface and its own Ru, so a joint drained differently from
        # the soil around it is expressible. With the same water surface on
        # both — every model of the verification bank — it changes nothing.
        weak_layer_id = None
        if weak_spans:
            hit = _weak_layer_at(weak_spans, xc)
            if hit is not None:
                mat, weak_layer_id = hit

        # v0.1.96 — the TOP used for the weight is the mean ground
        # elevation over the slice, not the midpoint of the chord joining
        # its two corners. They differ only where a profile vertex falls
        # INSIDE a slice, and there the chord cuts the corner off. See
        # ``_mean_polyline_y``. ``top_y_mid`` itself is left alone: it is
        # the geometric midpoint the rest of the slice reports.
        top_y_w = _mean_polyline_y(ground, xl, xr)
        if top_y_w is None:
            top_y_w = top_y_mid

        # v0.1.63 — the weight comes from integrating the column, so a
        # slice spanning several layers, or straddling the water table,
        # is weighed band by band instead of being classified whole by
        # its base midpoint.
        weight, layer_top_y = _column_weight(
            project, xc, base_y_mid, top_y_w, dx)

        # v0.1.120 — the true distance to the slope is the one measurement
        # here that nothing else needs, and it costs a pass over the whole
        # ground profile. Asked for only when a material's strength model
        # declares it reads it, so a search that does not use it pays
        # nothing at all.
        slope_distance = (
            distance_to_profile(ground, xc, base_y_mid)
            if wants_slope_distance else None)

        # v0.1.126 — the bedding orientation where THIS base sits. Read at
        # the CLOSEST point of the polyline, not the one vertically above:
        # that is what an anisotropic surface means and what separates it
        # from a water surface.
        bedding_angle_deg = None
        if aniso_by_material:
            pl = aniso_by_material.get(getattr(mat, "id", None))
            if pl is not None:
                bedding_angle_deg = anisotropy_angle_at(pl, xc, base_y_mid)

        # v0.1.96 — a water surface that does not reach this abscissa is
        # a REFUSAL, not zero pore pressure. ``pore_pressure_at`` cannot
        # tell the caller which of the two it is returning, so the question
        # is asked separately; the reference discards the whole slip
        # surface in this case and writes an error rather than reporting a
        # dry slope, which is the unsafe side to be wrong on.
        if not water_surface_defined_at(project, mat, xc):
            return None

        # Pore pressure at the midpoint of the base
        u = pore_pressure_at(
            project,
            Vertex(xc, base_y_mid),
            mat,
            ground_surface_y=top_y_mid,
        )
        # v0.1.28 — unsaturated policy (extended Mohr-Coulomb). Only a
        # seepage analysis can return u < 0; everything else already
        # clamps at zero, so this is a no-op for those methods.
        u_raw = u
        u, c_suction = apply_unsaturated_policy(u, mat, _u_cutoff)

        # v0.1.75 — excess pore pressure from undrained loading, added to
        # the INITIAL pore pressure the groundwater method just produced,
        # which is the order Skempton's formulation and the reference
        # both state. After the unsaturated policy on purpose: the excess
        # is a positive addition and cannot turn into suction cohesion,
        # and running the policy on the sum would let a loaded slice
        # silently lose the suction term it had earned.
        if excess_is_enabled(project):
            du = excess_at(project, mat, xc, base_y_mid, top_y_mid,
                           slice_width=dx)
            if du:
                u += du

        q = _surface_pressure_at(project, xc)
        weight += q * dx  # add the distributed-load surcharge

        # v0.1.75 — line loads. The vertical component joins ``weight``,
        # which is exactly how the distributed surcharge above is
        # treated, so the two kinds of load are consistent with each
        # other: a line load of P kN/m and a distributed load whose
        # integral is P produce the same slice weight. The horizontal
        # component needs a moment arm and goes through the external
        # force channel below, once the slice exists.
        _lines = line_loads_on(project, xl, xr)
        for _load in _lines:
            weight += _line_load_components(_load)[0]

        # v0.1.122 — the horizontal half of the distributed loads, which
        # until this version was thrown away. Only the VERTICAL-segment case
        # brings a vertical part back with it: for every other segment the
        # weight above already carries it, through ``_surface_pressure_at``.
        _dist = distributed_loads_on(project, xl, xr, x_r - x_l)
        for _fh, _fv, _y in _dist:
            weight += _fv

        sl = Slice(
            index=i,
            x_centre=xc,
            width=dx,
            base_x_left=xl,
            base_x_right=xr,
            base_y_left=y_base_l,
            base_y_right=y_base_r,
            base_angle=alpha,
            base_length=base_len,
            weight_arm_ratio=arm_ratio,
            top_y_left=y_top_l,
            top_y_right=y_top_r,
            top_y_mean=top_y_w,
            weight=weight,
            pore_pressure=u,
            raw_pore_pressure=u_raw,
            suction_cohesion=c_suction,
            surface_pressure=q,
            material=mat,
            layer_top_y=layer_top_y,
            slope_distance=slope_distance,
            bedding_angle_deg=bedding_angle_deg,
            weak_layer_id=weak_layer_id,
        )
        # v0.1.61 — free-standing water resting on this slice. Applied
        # after the slice exists because it needs the finished top
        # geometry, and kept out of ``weight`` so the seismic
        # coefficients cannot reach it.
        _apply_ponded_water(project, sl)
        # v0.1.75 — the horizontal component of any line load on this
        # slice, applied at the elevation of its point of application.
        # It shares the accumulator the water forces use because what
        # that channel models is "a horizontal force at a height", which
        # is precisely what this is; the accumulator stores the moment
        # about a fixed reference, so forces of opposite sign on the same
        # slice add up correctly.
        for _load in _lines:
            _fh = _line_load_components(_load)[1]
            if _fh:
                sl.add_water_force(f_h=_fh, y=_load.point.y)
        # v0.1.122 — and the same for the distributed loads, through the
        # same accumulator and for the same reason: what it models is a
        # horizontal force at a height.
        for _fh, _fv, _y in _dist:
            if _fh:
                sl.add_water_force(f_h=_fh, y=_y)
        result.slices.append(sl)

    if len(result) < 3:
        return None

    # v0.1.7 — Tension Crack hydrostatic force, on the wall the
    # truncation actually left.
    #
    # v0.1.109 — this used to be guarded by ``not ...is_dry()``, which
    # made a DRY crack do nothing at all: no thrust (right, there is no
    # water) and no truncation (wrong — truncating is the other half of
    # the model, and the half that works without water). The truncation
    # now happens up in ``slice_surface``, for every crack; what is left
    # here is only the water.
    #
    # And it is keyed on ``tension_crack_wall`` rather than on "is there
    # a crack boundary somewhere under this mass". The old question let a
    # surface that never reaches the crack receive the full-depth thrust:
    # on ACADS 1(b) a 1.58 m circle beside the crest, weighing 50 kN, was
    # handed 73.5 kN — more than its own weight — and the search dutifully
    # found that as its minimum.
    wall = getattr(surface, "tension_crack_wall", None)
    if wall is not None and not project.tension_crack_properties.is_dry():
        result = _apply_tension_crack(project, result, wall)

    return result


def _apply_tension_crack(project: Project, slices: Slices, wall):
    """Apply the water thrust on a tension crack wall to ``slices``, in place.

    ``wall`` is ``(x, y_bottom, y_top)``: the vertical face the truncation
    left, from the crack boundary up to the ground surface. The thrust is
    the integral of the hydrostatic pressure over the WET part of it,

        F = ½ γ_w h_w²        acting horizontally,

    with its line of action at the centroid of the triangular pressure
    distribution, h_w/3 above the water's own base. Terzaghi (1943),
    *Theoretical Soil Mechanics*; the same expression Duncan & Wright
    (2005), chapter 14, use for a water-filled crack.

    v0.1.109 — the geometry now comes from the wall instead of from the
    centre of whichever slice happened to fall inside the crack's x
    range. Two consequences, and both were defects:

    * ``h_w`` is measured on the crack the surface actually reaches. It
      used to be the crack's full depth whatever the surface did, so
      three different circles on ACADS 1(b) — the Bishop critical one,
      the Janbu one, and a 1.58 m circle that never touches the crack
      base — all received exactly −73.46 kN;
    * a surface with no wall receives nothing, instead of a thrust on a
      crack it never opened.
    """
    if not slices.slices:
        return slices

    x, crack_bottom_y, crack_top_y = wall
    if crack_top_y <= crack_bottom_y:
        return slices

    # Resolve the water level inside the crack (the seven modes of
    # ``TensionCrackProperties``: dry, filled, percent, below elevation,
    # to depth, water table, piezometric line).
    wt = next(
        (b for b in project.boundaries
         if b.btype == BoundaryType.WATER_TABLE),
        None,
    )
    piezos = {
        b.id: b for b in project.boundaries
        if b.btype == BoundaryType.PIEZOMETRIC
    }
    water_y = project.tension_crack_properties.water_level_at(
        x=x,
        crack_top_y=crack_top_y,
        crack_bottom_y=crack_bottom_y,
        water_table=wt,
        piezos=piezos,
    )
    h_w = max(0.0, water_y - crack_bottom_y)
    if h_w <= 0:
        return slices

    gamma_w = project.settings.groundwater.pore_fluid_unit_weight
    F = 0.5 * gamma_w * h_w * h_w
    arm = crack_bottom_y + h_w / 3.0

    slices.tension_crack_force = F
    slices.tension_crack_arm = arm

    # v0.1.61 — until now the force stopped here: it was computed, stored,
    # and read by nobody, so water in a tension crack had NO effect on the
    # factor of safety, which came out too high — on the unsafe side. Push
    # it through the same per-slice channel as the ponded water so every
    # LEM method sees it.
    #
    # Direction: the water fills the crack behind the sliding mass and
    # pushes the mass away from the intact ground, i.e. from the crack
    # towards the rest of the mass. Deriving the sense from the geometry
    # avoids assuming which way the slope faces.
    #
    # v0.1.109 — the wall IS one end of the mass now, so the slice that
    # carries the thrust is simply the outermost one on that side. No
    # search for it, and no way to land on the wrong one.
    xs = [s.x_centre for s in slices.slices]
    mass_centre = 0.5 * (min(xs) + max(xs))
    if mass_centre > x:
        wall_slice = slices.slices[0]
        push_sign = 1.0
    else:
        wall_slice = slices.slices[-1]
        push_sign = -1.0
    wall_slice.add_water_force(f_h=push_sign * F, y=arm)
    return slices
