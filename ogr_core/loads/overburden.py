# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The soil column above a point, and the vertical pressure of the loads on
the ground: what a slice weighs and what a support feels.

v0.1.344 (D337) -- moved word for word from ``ogr_slip2d/slicer.py``. The
slice weight, the effective stress along a support (``ogr_core.support.
bond``) and the excess pore pressure of B-bar loading (``ogr_core.
hydraulic.excess_pore_pressure``) all read this one decomposition, and the
two in the core imported the slicer to reach it: the core reached up into
the engine. The slicer imports these names back, unchanged.

The switch :data:`SIGNED_SURFACE_PRESSURE` moved with the function that
reads it, and lives only here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..geometry import BoundaryType, Polyline
from ..hydraulic.water_surfaces import water_table_y_at

if TYPE_CHECKING:
    from ..project import Project


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

    # v0.1.143 — a band that no region covers used to become the FIRST
    # material of the project, the same silent substitution D48 left behind
    # in ``_material_at``. It happens here for a different reason, and one
    # this function creates itself: ``y_top`` is the MEAN ground elevation
    # over the slice (v0.1.96), so where the ground rises across the slice
    # the topmost band reaches above the ground at ``x`` and its midpoint
    # is in the air. Measured on the first four problems of the bank: 1 024
    # such bands, all of them above the ground, none below the floor.
    #
    # The sliver is real — the mean elevation is deliberate and the column
    # is that tall — so what is missing is only its material, and the
    # honest answer is the material of the band BELOW it, the topmost one
    # that is really soil. Reaching for ``materials[0]`` instead weighed
    # the top of the column with a layer that need not be anywhere near it.
    mats = list(mats)
    for i, m in enumerate(mats):
        if m is not None:
            continue
        below = next((mats[j] for j in range(i - 1, -1, -1)
                      if mats[j] is not None), None)
        if below is None:
            below = next((mats[j] for j in range(i + 1, len(mats))
                          if mats[j] is not None), None)
        mats[i] = below

    total = 0.0
    for (lo, hi), mat, (_mx, y_mid) in zip(bands, mats, mids):
        if mat is None:
            # v0.1.143 — a project with no materials at all. This used to
            # weigh the band at 20.0 kN/m3, a number belonging to nothing
            # in the model and indistinguishable from a real unit weight;
            # with no material there is no soil, and no soil weighs
            # nothing. Unreachable from the slicer since the base query
            # above refuses such a surface, and kept correct anyway
            # because this function is called from elsewhere.
            continue
        below_water = wt_y is not None and wt_y > y_mid
        total += mat.gamma_at(below_water) * (hi - lo) * dx

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

def _line_load_components(load, project=None) -> tuple[float, float]:
    """(downward, +x) components of a line load, in kN/m.

    ``direction_vector`` points the way the load pushes, with -y meaning
    downwards, so the vertical component is negated to give a downward
    positive number — the same sign convention ``weight`` uses.

    v0.1.199 — with ``project``, through ``line_load_direction``, which
    resolves a load normal (or at an angle) to the boundary against the
    model's ground surface; both fell through to vertical before.
    """
    if project is not None:
        from ogr_core.loads.loads import line_load_direction
        dx, dy = line_load_direction(project, load)
    else:
        dx, dy = load.direction_vector()
    return -load.magnitude * dy, load.magnitude * dx

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

    v0.1.241 (D232) — DOWNWARD positive and SIGNED, the convention of the
    slice weight and of :func:`_line_load_components`: a load that points
    up pulls the ground and takes weight off. See
    :data:`SIGNED_SURFACE_PRESSURE`.
    """
    return _summed(_surface_pressures_at(project, x))


def _surface_pressures_at(project: Project, x: float) -> list:
    """``(load, p)`` for each distributed load acting at x: the vertical
    component of its pressure, in kPa, downward positive and signed (see
    :func:`_surface_pressure_at`, which is their sum).

    v0.1.243 (D226b) — split out so that a design standard can factor each
    load by itself; the order is the order of ``project.distributed_loads``,
    and :func:`_summed` adds them in it, so the total is the one this
    function's caller always had, bit for bit.
    """
    signed = SIGNED_SURFACE_PRESSURE
    out = []
    for load in project.distributed_loads:
        x1, x2 = load.start.x, load.end.x
        lo, hi = min(x1, x2), max(x1, x2)
        if lo <= x <= hi:
            t = 0.0 if abs(x2 - x1) < 1e-12 else (x - x1) / (x2 - x1)
            t = max(0.0, min(1.0, t))
            p = load.pressure_at(t)
            # Vertical component of the pressure, downward positive
            _, dy = load.direction_vector()
            out.append((load, -p * dy if signed else abs(p * dy)))  # kPa
    return out


def _summed(parts) -> float:
    """The total of ``(load, p)`` pairs, added in their order from 0.0."""
    total = 0.0
    for _load, p in parts:
        total += p
    return total

#: v0.1.241 (D232) — the vertical component of a distributed load keeps its
#: SIGN.
#:
#: Until v0.1.240 it was added as ``abs(p·dy)``: a load pointing UP was
#: applied DOWN, while its horizontal component (:func:`distributed_loads_on`),
#: the vertical-segment case and every line load (:func:`_line_load_components`)
#: kept theirs — so the claim below that a line load of P kN/m and a
#: distributed load whose integral is P give the same slice weight was false
#: for any load pointing up, and the API's own note on such a load ("it
#: pulls the ground") described something the engine did not do. Measured on
#: the phi = 0 slope of ``test_tension_crack_truncation_v1109``, 20 kPa over
#: 16 m of the crest pointing up: 1.0295, the same as pointing down, where
#: the equivalent line load gives 1.2069. A net upward resultant on a slice
#: is a net negative weight, which the methods already handle.
#:
#: Read at call time by :func:`_surface_pressures_at` (the slice weight and
#: the effective stress along a support) and by
#: ``ogr_core.hydraulic.excess_pore_pressure.load_delta_sigma_v``. Off, the
#: v0.1.240 behaviour.
#:
#: v0.1.344 (D337) -- its one home is this module, and the slicer keeps no
#: copy: a copy set to False would change nothing, which is worse than no
#: switch (rule 7). Before this version it lived in ``ogr_slip2d.slicer``. No model of the verification bank has a distributed
#: load pointing up (230 models, 11 such loads, all straight down).
SIGNED_SURFACE_PRESSURE = True
