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
    Boundary, BoundaryType, Polyline, Vertex, ground_surface,
)
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

from .surface import SlipCircle, SlipSurface, SurfaceProtocol


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
        prev_x, prev_g = None, None
        for k in range(sub + 1):
            x = lo + step * k
            gx = g(x, p1, p2)
            if gx is None:
                prev_x, prev_g = None, None
                continue
            if prev_g is not None and prev_g * gx < 0.0:
                a, b, ga = prev_x, x, prev_g
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
            elif gx == 0.0:
                out.append(x)
            prev_x, prev_g = x, gx
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

    # The y-range the slip surface spans. For a circle the lower arc is
    # convex, so its extremes are the lowest point and the two ends —
    # exact, and three evaluations. Used to throw away whole boundaries
    # before scanning them: a layer that runs well below the failure mass
    # cannot cut it, and checking that costs two comparisons instead of
    # eight evaluations per segment. Without it, this search ran in full
    # for every trial surface of a grid search and cost 20 %.
    y_ends = [surface.base_y_at(x_l), surface.base_y_at(x_r)]
    y_ends = [v for v in y_ends if v is not None]
    if isinstance(surface, SlipCircle) and x_l <= surface.centre_x <= x_r:
        v = surface.base_y_at(surface.centre_x)
        if v is not None:
            y_ends.append(v)
    if not y_ends:
        return None
    s_lo, s_hi = min(y_ends), max(y_ends)
    if not isinstance(surface, SlipCircle):
        # A polyline surface is not convex: its interior vertices can sit
        # outside the envelope of the two ends.
        for v in getattr(getattr(surface, "polyline", None), "vertices", ()):
            if x_l <= v.x <= x_r:
                s_lo = min(s_lo, v.y)
                s_hi = max(s_hi, v.y)

    cuts: set = set()

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
    # Circles have no vertices, so this is inert for every circular search
    # — the validated Ej_1 and Ej_2 benchmarks cannot move.
    if not isinstance(surface, SlipCircle):
        for v in getattr(getattr(surface, "polyline", None), "vertices", ()):
            if x_l + 1e-9 < v.x < x_r - 1e-9:
                cuts.add(v.x)

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
        ya = _interp_y_on_polyline(polyline, a)
        yb = _interp_y_on_polyline(polyline, b)
        if ya is None or yb is None:
            return None
        area += 0.5 * (ya + yb) * (b - a)
    return area / (x_r - x_l)


def _column_weight(
    project: Project,
    x: float,
    y_bottom: float,
    y_top: float,
    dx: float,
) -> float:
    """Weight per unit width of the soil column at ``x``, in kN/m.

    The column is cut at every material boundary and at every water table
    crossing it, and each band is weighed with the unit weight of the
    material that occupies it, saturated or not according to whether it
    sits below the free water surface.

    With a single material and no water table crossing the column this
    reduces to ``γ · (y_top − y_bottom) · dx``, which is what the previous
    implementation computed — so a one-layer model keeps its factor of
    safety to the last bit.
    """
    height = y_top - y_bottom
    if height <= 0.0:
        return 0.0

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
        return 0.0

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

    total = 0.0
    for (lo, hi), mat, (_mx, y_mid) in zip(bands, mats, mids):
        if mat is None:
            mat = project.materials[0] if project.materials else None
        below_water = wt_y is not None and wt_y > y_mid
        gamma = mat.gamma_at(below_water) if mat else 20.0
        total += gamma * (hi - lo) * dx
    return total


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


def _surface_pressure_at(project: Project, x: float) -> float:
    """Sum of distributed-load pressures acting at x (vertical component)."""
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


# ----------------------------------------------------------------------
def apply_unsaturated_policy(u: float, material) -> tuple[float, float]:
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

    Returns ``(u_effective, extra_cohesion)``.
    """
    if u >= 0.0 or material is None:
        return u, 0.0
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


def slice_surface(
    project: Project,
    surface: SurfaceProtocol,
    num_slices: int = 50,
) -> Optional[Slices]:
    """Build the list of slices for a given slip surface.

    Returns None if the surface does not intersect the ground twice or
    the failure mass is degenerate.
    """
    external = project.external_boundary()
    if external is None:
        return None

    # For circles, compute ground intersections if not cached
    if isinstance(surface, SlipCircle):
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
        x_l, x_r = surface.x_left, surface.x_right
    else:
        x_l, x_r = surface.x_range()
        ground = _ground_surface_from_external(external)

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
    ends_are_ground_crossings = isinstance(surface, SlipCircle)

    for i, (xl, xr) in enumerate(zip(bounds[:-1], bounds[1:])):
        dx = xr - xl
        if dx <= 0.0:
            return None
        xc = 0.5 * (xl + xr)

        y_base_l = surface.base_y_at(xl)
        y_base_r = surface.base_y_at(xr)
        if y_base_l is None or y_base_r is None:
            return None

        y_top_l = _interp_y_on_polyline(ground, xl)
        y_top_r = _interp_y_on_polyline(ground, xr)
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
        if isinstance(surface, SlipCircle) and surface.radius > 0.0:
            arm_ratio = (xc - surface.centre_x) / surface.radius
        else:
            arm_ratio = math.sin(alpha)

        # Material at the base midpoint. This one stays a single query:
        # the base is where the shear strength and the pore pressure are
        # evaluated, and both belong to the material the base cuts.
        base_y_mid = 0.5 * (y_base_l + y_base_r)
        top_y_mid = 0.5 * (y_top_l + y_top_r)
        mat = _material_at(project, Vertex(xc, base_y_mid + 0.01))

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
        weight = _column_weight(project, xc, base_y_mid, top_y_w, dx)

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
        u, c_suction = apply_unsaturated_policy(u, mat)

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
        result.slices.append(sl)

    if len(result) < 3:
        return None

    # v0.1.7 — Tension Crack hydrostatic force.
    # If the slip surface enters a Tension Crack zone (i.e. there is a
    # Tension Crack boundary in the project, and the surface intersects
    # the column where the crack is defined), the topmost slice is
    # truncated at the crack's vertical wall and a horizontal force is
    # applied on that wall, equal to the integral of the water column
    # pressure over the wet height of the crack.
    tc_boundaries = [
        b for b in project.boundaries
        if b.btype == BoundaryType.TENSION_CRACK
    ]
    if tc_boundaries and not project.tension_crack_properties.is_dry():
        result = _apply_tension_crack(project, result, tc_boundaries[0])

    return result


def _apply_tension_crack(project: Project, slices: Slices, tc_boundary):
    """Apply the Tension Crack hydrostatic force to ``slices`` in-place.

    Looks for the slice nearest to the failure-direction-side endpoint
    of the tension crack within the slice population. Computes the
    hydrostatic force as ½ γ_w h_w², acting horizontally, where h_w
    is the wet column height inside the crack.
    """
    if not slices.slices:
        return slices

    # v0.1.73 — which end of the crack zone is up-slope now comes from
    # the project's Failure Direction instead of being assumed. The old
    # comment said "assume rightward ... for a typical slope", and that
    # assumption happens to match the DEFAULT (right to left, crest on
    # the right), which is why nothing was visibly wrong; a left-to-right
    # model, though, had the crack truncating the slice at the wrong end
    # of the zone, and therefore applying the water thrust to the wrong
    # slice. Only the CHOICE of slice is decided here — the sense of the
    # thrust has been derived from the geometry since v0.1.61, below.
    # Find the column x where the tension crack meets the slip surface
    tc_verts = tc_boundary.polyline.vertices
    if len(tc_verts) < 2:
        return slices

    # The tension crack boundary defines the LOWER limit of the crack
    # zone. For each x where the boundary is defined, the crack base
    # y is given by linear interpolation; the crack TOP is the ground
    # surface.
    external = project.external_boundary()
    if external is None:
        return slices
    ground = _ground_surface_from_external(external)

    # Find the slice whose x_centre is at the up-slope side and within
    # the tension-crack-boundary's x range
    from .failure_direction import crest_is_on_the_right

    tc_xs = sorted([v.x for v in tc_verts])
    tc_xmin, tc_xmax = tc_xs[0], tc_xs[-1]
    upslope_slice = None
    ordered = (reversed(slices.slices) if crest_is_on_the_right(project)
               else iter(slices.slices))
    for s in ordered:
        if tc_xmin - 1e-6 <= s.x_centre <= tc_xmax + 1e-6:
            upslope_slice = s
            break
    if upslope_slice is None:
        return slices

    x = upslope_slice.x_centre
    crack_top_y = _interp_y_on_polyline(ground, x)
    crack_bottom_y = _interp_y_on_polyline(tc_boundary.polyline, x)
    if crack_top_y is None or crack_bottom_y is None:
        return slices
    if crack_top_y <= crack_bottom_y:
        return slices

    # Resolve the water level inside the crack (Slide modes)
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
    # Hydrostatic force: F = ½ γ_w h_w² (per unit out-of-plane width)
    F = 0.5 * gamma_w * h_w * h_w
    # Moment arm: centroid of the triangular pressure distribution
    # is at h_w/3 above the crack base
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
    xs = [s.x_centre for s in slices.slices]
    mass_centre = 0.5 * (min(xs) + max(xs))
    push_sign = 1.0 if mass_centre > x else -1.0
    upslope_slice.add_water_force(f_h=push_sign * F, y=arm)
    return slices
