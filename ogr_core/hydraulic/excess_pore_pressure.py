# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Excess pore pressure from undrained loading — the B-bar method.

A soil of low permeability loaded faster than it can drain responds with
a rise in pore pressure. Skempton (1954) writes the change as
proportional to the change in vertical stress:

    Δu = B̄ · Δσv

and the final pore pressure used in the stability calculation is the
initial one — whatever the groundwater method and the material's water
parameters give — **plus** this excess.

**The stress model is one-dimensional and does not spread.** Δσv at a
point is the vertical stress added directly above it, transmitted
straight down, undiminished with depth. That is not a simplification
chosen here: it is what the B-bar method assumes, and the reference
states it explicitly — a load "will create excess pore pressure in any
material *underneath the load*". No elastic distribution, no Boussinesq
bulb. Mixing an elastic spread into one term while the soil-weight term
stayed oedometric would be two different theories inside one sum.

Three sources contribute, and each is opt-in:

* **material weight** — a material whose ``weight_creates_excess`` is on
  loads everything beneath it. Note this is a different question from
  whether that material develops excess *itself*, which is ``b_bar``: an
  embankment over a clay foundation usually has the first on and B̄ = 0,
  loading the clay without generating excess within itself;
* **external loads** — distributed and line loads whose
  ``creates_excess_pore_pressure`` is on, vertical component only;
* **vertical seismic** — the ``kv`` coefficient only. The horizontal one
  never contributes, whatever the flag says, because it changes no
  vertical stress.

**Excess is only computed where B̄ > 0.** A material with B̄ = 0 is
free-draining by definition and develops none, however much load arrives.

A caveat that belongs next to the formula rather than in a changelog: a
**line load is a concentrated force**, so the vertical *stress* it
produces depends on the width it is smeared over. Here that width is the
slice, which makes its contribution mesh-dependent — refine the slicing
and Δu under the load grows. That is inherent to a concentrated load
with no spreading, not an artefact of this implementation (the elastic
solution is singular under a point load too), but it means a distributed
load is the better way to model a surcharge whose excess pore pressure
matters.

Reference:
    Skempton, A. W. (1954). "The pore-pressure coefficients A and B".
    Géotechnique, 4(4), 143-147.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ogr_core.project import Project


def is_enabled(project: "Project") -> bool:
    """True when the project asks for the B-bar excess pore pressure."""
    try:
        return bool(project.settings.groundwater.excess_pore_pressure)
    except Exception:  # noqa: BLE001
        return False


# ----------------------------------------------------------------------
def soil_delta_sigma_v(project: "Project", x: float, y: float,
                       ground_surface_y: float) -> float:
    """Vertical stress at (x, y) from the material bands marked as loading.

    Only the bands between ``y`` and the ground surface count, and only
    those whose material has ``weight_creates_excess`` set. The column is
    cut at material boundaries and at the water table exactly the way the
    slice weight is cut, so a band is weighed with the same unit weight
    the analysis gives it — reusing the slicer's decomposition rather
    than duplicating it, because two versions of "what is above this
    point" would eventually disagree.

    Returns kPa (a stress, not a force): the slice width cancels.
    """
    if ground_surface_y <= y:
        return 0.0
    total = 0.0
    for band_gamma, thickness in _loading_bands(project, x, y,
                                                ground_surface_y):
        total += band_gamma * thickness
    return total


def _loading_bands(project: "Project", x: float, y_bottom: float,
                   y_top: float):
    """(unit weight, thickness) of each band above ``y_bottom`` that loads.

    Mirrors the band decomposition of ``ogr_slip2d.slicer._column_weight``
    — same cuts, same saturated/unsaturated rule — and then keeps only
    the bands whose material declares that its weight creates excess.
    """
    from ogr_core.geometry import BoundaryType
    from ogr_slip2d.slicer import _polyline_crossings_at_x

    from .water_surfaces import water_table_y_at

    if y_top <= y_bottom:
        return []

    cuts = {y_bottom, y_top}
    for b in project.boundaries:
        if b.btype not in (BoundaryType.MATERIAL, BoundaryType.WATER_TABLE):
            continue
        for yc in _polyline_crossings_at_x(b.polyline, x):
            if y_bottom < yc < y_top:
                cuts.add(yc)

    wt_y = water_table_y_at(project, x)
    ys = sorted(cuts)
    bands = [(lo, hi) for lo, hi in zip(ys[:-1], ys[1:]) if hi > lo]
    if not bands:
        return []

    mids = [(x, 0.5 * (lo + hi)) for lo, hi in bands]
    if len(project.materials) == 1:
        mats = [project.materials[0]] * len(bands)
    else:
        mats = project.materials_at(mids)

    out = []
    for (lo, hi), mat, (_mx, y_mid) in zip(bands, mats, mids):
        if mat is None:
            mat = project.materials[0] if project.materials else None
        if mat is None or not getattr(mat, "weight_creates_excess", False):
            continue
        below_water = wt_y is not None and wt_y > y_mid
        out.append((mat.gamma_at(below_water), hi - lo))
    return out


# ----------------------------------------------------------------------
def load_delta_sigma_v(project: "Project", x: float,
                       slice_width: Optional[float] = None) -> float:
    """Vertical stress at abscissa ``x`` from the external loads that load.

    Distributed loads contribute their vertical pressure component
    directly. Line loads contribute their vertical force divided by
    ``slice_width`` — see the module docstring for why that is
    mesh-dependent and what to do about it. Without a width, line loads
    are skipped rather than guessed at.
    """
    from ogr_slip2d.slicer import _line_load_components

    total = 0.0
    for load in getattr(project, "distributed_loads", None) or []:
        if not getattr(load, "creates_excess_pore_pressure", False):
            continue
        x1, x2 = load.start.x, load.end.x
        lo, hi = min(x1, x2), max(x1, x2)
        if not (lo <= x <= hi):
            continue
        t = 0.0 if abs(x2 - x1) < 1e-12 else (x - x1) / (x2 - x1)
        t = max(0.0, min(1.0, t))
        _dx, dy = load.direction_vector()
        total += abs(load.pressure_at(t) * dy)

    if slice_width and slice_width > 0.0:
        half = 0.5 * slice_width
        for load in getattr(project, "line_loads", None) or []:
            if not getattr(load, "creates_excess_pore_pressure", False):
                continue
            if abs(load.point.x - x) <= half + 1e-12:
                total += _line_load_components(load)[0] / slice_width
    return total


def seismic_delta_sigma_v(project: "Project", soil_sigma_v: float) -> float:
    """Vertical stress added by the VERTICAL seismic coefficient.

    ``kv`` scales the weight of the soil above, so it acts on the same
    stress the material bands contribute — and on nothing else, since a
    surcharge is not part of the accelerated mass in this formulation,
    the same convention ``slice_forces`` already uses for ``kh``.

    The horizontal coefficient is deliberately absent: it changes no
    vertical stress, so it can generate no excess pore pressure.
    """
    seismic = getattr(project, "seismic", None)
    if seismic is None or not getattr(seismic, "enabled", False):
        return 0.0
    if not getattr(seismic, "creates_excess_pore_pressure", False):
        return 0.0
    return float(getattr(seismic, "kv", 0.0)) * soil_sigma_v


# ----------------------------------------------------------------------
def delta_sigma_v_at(project: "Project", x: float, y: float,
                     ground_surface_y: float,
                     slice_width: Optional[float] = None) -> float:
    """Total change in vertical stress at (x, y), in kPa."""
    soil = soil_delta_sigma_v(project, x, y, ground_surface_y)
    loads = load_delta_sigma_v(project, x, slice_width)
    return soil + loads + seismic_delta_sigma_v(project, soil)


def excess_at(project: "Project", material, x: float, y: float,
              ground_surface_y: float,
              slice_width: Optional[float] = None) -> float:
    """Δu = B̄ · Δσv for one point, in kPa. Zero when B̄ = 0.

    The gate is ``b_bar > 0`` alone, as the reference states: a material
    with B̄ = 0 is free-draining by definition. Note this differs from
    the rapid-drawdown path, whose gate is ``undrained_behaviour``,
    because there the coefficient describes how much of an UNLOADING the
    pore water follows and B̄ = 0 has a meaning of its own.
    """
    if material is None or not is_enabled(project):
        return 0.0
    b_bar = float(getattr(material, "b_bar", 0.0) or 0.0)
    if b_bar <= 0.0:
        return 0.0
    return b_bar * delta_sigma_v_at(project, x, y, ground_surface_y,
                                    slice_width)
