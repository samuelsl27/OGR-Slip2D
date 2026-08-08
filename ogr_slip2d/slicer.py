# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slicer — divides the potential failure mass into vertical slices.

This is the geometric bridge between the slip surface and the LEM
solver. Each slice carries all the scalars the solver needs:

    - geometry:    x_centre, width, base_length, base_angle α
    - physics:     weight W, pore pressure u, base cohesion/φ
    - loads:       surface distributed pressure q, line loads, seismic

The slicer handles multi-layer materials by intersecting each slice with
every material boundary and composing the weights accordingly.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator, Optional

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.hydraulic.ponded_water import ponded_depth_at
from ogr_core.hydraulic.pore_pressure import pore_pressure_at, _interp_y_on_polyline
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
        return self.top_y_mid - self.base_y_mid

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
    """Extract the upper envelope (ground surface) from the external boundary.

    We take the vertices with the highest y for each unique x — a simple
    but robust heuristic for slope models where the external boundary is
    a closed polygon.
    """
    verts = external.polyline.vertices
    if not verts:
        return Polyline()
    # Group by rounded x, keep the max y per bucket
    buckets: dict[float, float] = {}
    for v in verts:
        key = round(v.x, 6)
        if key not in buckets or v.y > buckets[key]:
            buckets[key] = v.y
    xs = sorted(buckets.keys())
    return Polyline(vertices=[Vertex(x, buckets[x]) for x in xs])


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
        x_l, x_r = surface.x_left, surface.x_right
    else:
        x_l, x_r = surface.x_range()
        ground = _ground_surface_from_external(external)

    if x_l is None or x_r is None or x_r - x_l < 1e-6:
        return None

    dx = (x_r - x_l) / num_slices
    result = Slices()

    for i in range(num_slices):
        xl = x_l + i * dx
        xr = x_l + (i + 1) * dx
        xc = 0.5 * (xl + xr)

        y_base_l = surface.base_y_at(xl)
        y_base_r = surface.base_y_at(xr)
        if y_base_l is None or y_base_r is None:
            continue

        y_top_l = _interp_y_on_polyline(ground, xl)
        y_top_r = _interp_y_on_polyline(ground, xr)
        if y_top_l is None or y_top_r is None:
            continue

        # v0.1.18 — at the slip-surface endpoints the circular arc can
        # sit a few 1e-6 ABOVE the ground purely from root-finding
        # round-off. Clamp the base to the ground there instead of
        # dropping the slice; dropping it lost the first/last slice and
        # produced 24 slices where Slide builds 25, biasing the FoS by
        # ~1%. Only a genuine overshoot (> a small tolerance) is treated
        # as degenerate.
        tol = 1e-4
        if y_base_l > y_top_l:
            if y_base_l - y_top_l <= tol:
                y_base_l = y_top_l
            else:
                continue
        if y_base_r > y_top_r:
            if y_base_r - y_top_r <= tol:
                y_base_r = y_top_r
            else:
                continue

        alpha = surface.base_angle_at(xc)
        base_len = dx / math.cos(alpha) if abs(math.cos(alpha)) > 1e-9 else dx

        # Average height (trapezoidal) — for weight computation
        h_mid = 0.5 * ((y_top_l - y_base_l) + (y_top_r - y_base_r))

        # Material at the base midpoint
        base_y_mid = 0.5 * (y_base_l + y_base_r)
        mat = _material_at(project, Vertex(xc, base_y_mid + 0.01))

        # Unit weight: use saturated weight if a water table exists above
        # the base midpoint, else dry/bulk. Known simplification: the slice
        # is classified WHOLE by the position of its base midpoint, so one
        # straddling the water table gets a single γ over its full height
        # instead of γ_sat on the wet part and γ on the dry part.
        below_water = False
        for wb in project.boundaries_of(BoundaryType.WATER_TABLE):
            wy = _interp_y_on_polyline(wb.polyline, xc)
            if wy is not None and wy > base_y_mid:
                below_water = True
                break

        gamma = mat.gamma_at(below_water) if mat else 20.0
        weight = gamma * h_mid * dx  # kN/m

        # Pore pressure at the midpoint of the base
        u = pore_pressure_at(
            project,
            Vertex(xc, base_y_mid),
            mat,
            ground_surface_y=0.5 * (y_top_l + y_top_r),
        )
        # v0.1.28 — unsaturated policy (extended Mohr-Coulomb). Only a
        # seepage analysis can return u < 0; everything else already
        # clamps at zero, so this is a no-op for those methods.
        u_raw = u
        u, c_suction = apply_unsaturated_policy(u, mat)

        q = _surface_pressure_at(project, xc)
        weight += q * dx  # add the distributed-load surcharge

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
            top_y_left=y_top_l,
            top_y_right=y_top_r,
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

    # Determine failure direction (right vs left) — assume rightward
    # since OGR Slip2D uses CCW external. The "uphill" end of the slip
    # is on the right for a typical slope.
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
    tc_xs = sorted([v.x for v in tc_verts])
    tc_xmin, tc_xmax = tc_xs[0], tc_xs[-1]
    upslope_slice = None
    for s in reversed(slices.slices):  # right side = up-slope
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
