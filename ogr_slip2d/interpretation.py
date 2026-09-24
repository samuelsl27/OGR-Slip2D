# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the Interpret window asks of a search result, without the window.

v0.1.201 (spec 008, F3b). These questions were answered inside
``ogr_gui/interpret_window.py`` and ``ogr_gui/canvas/canvas_view.py``, so
an agent could not ask them and a script had to re-derive them. They move
here, and the interface asks here:

* :func:`error_code` — the negative code the reference writes in place of
  a factor of safety (-120, -112, -111, -101); one mapping for the raw-data
  export, the census and the agent;
* :func:`raw_data_rows`, :func:`invalid_summary`;
* :func:`surfaces_through_point` — measured to the surface the engine
  PRICED (the base of its slices), not to the whole circle: a point below
  the ground on the far side of a circle is not on its slip surface;
* :func:`minimum_per_centre`, :func:`sf_along_slope`;
* :func:`slice_rows` — the per-slice numbers OF THE METHOD. The interface's
  "Show Values Along Surface" recomputed the effective normal stress as
  W cos(alpha) / b - u, which is none of the nine methods' answer and not
  even the Ordinary method's (that divides by the base length l = b /
  cos(alpha), so it was off by 1/cos(alpha) for it too);
* :func:`surface_area`.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

#: The codes the reference writes in place of a factor of safety.
ERROR_TENSILE = -120
ERROR_M_ALPHA = -112
ERROR_NOT_CONVERGED = -111
ERROR_OTHER = -101
ERROR_CODES = {
    ERROR_TENSILE: "tensile stress at a slice base (Tensile Stress Check)",
    ERROR_M_ALPHA: "m-alpha below its limit (the m-alpha screen)",
    ERROR_NOT_CONVERGED: "no converged factor of safety",
    ERROR_OTHER: "any other rejection",
}


# ----------------------------------------------------------------------
# Codes and the census
# ----------------------------------------------------------------------
def error_code(res) -> Optional[int]:
    """The reference's negative code for a rejected evaluation; None for a
    valid, admissible one.

    -120 for the Tensile Stress Check, -112 for the m-alpha screen, -111
    for a factor of safety that did not converge, -101 for anything else.
    The tensile screen goes first because the screen tests tension first,
    so a surface failing both is a tensile rejection (v0.1.192, D177). The
    m-alpha branch also accepts the note, so a result built before
    ``admissibility_reason`` existed maps as it always did.
    """
    from .methods.base import SCREEN_M_ALPHA, SCREEN_TENSILE_STRESS

    if res.is_valid and getattr(res, "admissible", True):
        return None
    why = getattr(res, "admissibility_reason", "") or ""
    note = (getattr(res, "admissibility_note", "") or
            getattr(res, "error_message", "") or "")
    if why == SCREEN_TENSILE_STRESS:
        return ERROR_TENSILE
    if why == SCREEN_M_ALPHA or "m_alpha" in note:
        return ERROR_M_ALPHA
    if not res.converged:
        return ERROR_NOT_CONVERGED
    return ERROR_OTHER


def invalid_reason(res) -> Optional[str]:
    """Why an evaluation was rejected, in words, or None if it was not.

    The text groups the census and feeds the interface's error-code
    filter; the CODE is :func:`error_code`.
    """
    if res.is_valid and getattr(res, "admissible", True):
        return None
    return (getattr(res, "error_message", None)
            or getattr(res, "admissibility_note", None)
            or "did not converge")


def raw_data_rows(search_result) -> list:
    """One row per surface analysed, valid or not: ``[centre_x, centre_y,
    radius, x_left, x_right, fos or error code]`` as strings — the
    reference's *Export Raw Data*. A surface rejected before it was sliced
    has no result and no row."""
    rows = []
    for r in getattr(search_result, "evaluations", []) or []:
        sd = r.surface.to_dict()
        code = error_code(r)
        rows.append([
            f"{sd.get('centre_x', '')}", f"{sd.get('centre_y', '')}",
            f"{sd.get('radius', '')}",
            f"{sd.get('x_left', '')}", f"{sd.get('x_right', '')}",
            f"{r.fos:.6f}" if code is None else f"{code}",
        ])
    return rows


def invalid_summary(search_result) -> dict:
    """The census of rejected surfaces: by code, by reason, and the ones
    that were never sliced or a focus object removed."""
    by_code: dict = {}
    by_reason: dict = {}
    for ev in getattr(search_result, "evaluations", []) or []:
        code = error_code(ev)
        if code is None:
            continue
        by_code[code] = by_code.get(code, 0) + 1
        why = invalid_reason(ev)
        by_reason[why] = by_reason.get(why, 0) + 1
    generated = getattr(search_result, "total_count",
                        len(getattr(search_result, "evaluations", [])))
    analysed = getattr(search_result, "analysed_count",
                       getattr(search_result, "valid_count", 0))
    with_code = sum(by_code.values())
    return {
        "generated": generated,
        "analysed": analysed,
        "rejected": generated - analysed,
        "by_code": dict(sorted(by_code.items())),
        "by_reason": dict(sorted(by_reason.items(),
                                 key=lambda kv: -kv[1])),
        # Rejected before slicing: counted in the total, with no result.
        "not_sliced": max(0, (generated - analysed) - with_code),
        "focus_removed": getattr(search_result, "focus_rejected", 0),
    }


# ----------------------------------------------------------------------
# Geometry of a priced surface
# ----------------------------------------------------------------------
def surface_path(res) -> list:
    """The base of the slices, left to right, as ``[(x, y), ...]``: the
    surface the engine priced, tension-crack truncation and composite
    segments included. Empty when the result has no slices."""
    slices = getattr(res, "slices", None)
    if not slices or len(slices) == 0:
        return []
    pts = [(slices[0].base_x_left, slices[0].base_y_left)]
    for s in slices:
        pts.append((s.base_x_right, s.base_y_right))
    return pts


def distance_to_path(x: float, y: float, path) -> float:
    """Shortest distance from (x, y) to the polyline ``path``."""
    best = math.inf
    for (ax, ay), (bx, by) in zip(path[:-1], path[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 <= 0 else max(0.0, min(1.0, (
            (x - ax) * dx + (y - ay) * dy) / L2))
        best = min(best, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return best


def surfaces_through_point(search_result, x: float, y: float,
                           tolerance: float) -> list:
    """``[(distance, result)]`` of the valid surfaces whose PRICED base
    passes within ``tolerance`` of (x, y), lowest factor of safety first.

    v0.1.201 — the interface measured a circle to the WHOLE circle, so a
    point on the upper, unsliced side of a circle counted as crossing it,
    and a weak-layer surface (no radius, no polyline) never matched."""
    hits = []
    for r in search_result.valid():
        path = surface_path(r)
        if len(path) < 2:
            continue
        d = distance_to_path(x, y, path)
        if d <= tolerance:
            hits.append((d, r))
    hits.sort(key=lambda t: t[1].fos)
    return hits


def surface_area(res) -> float:
    """Area of the sliding mass, sum of width x mean height of the slices.

    v0.1.201 — the interface's result table divided each weight by a unit
    weight the slice does not have, so every row read 0.0."""
    return sum(s.width * s.height for s in (getattr(res, "slices", None)
                                            or []))


def minimum_per_centre(search_result) -> list:
    """The lowest-factor surface at each slip-centre grid point, plus every
    surface that has no centre (a non-circular search has no grid of
    centres, and the reference documents the option for a circular Grid
    Search only). Over the VALID surfaces, as the interface draws them."""
    best: dict = {}
    loose: list = []
    for r in search_result.valid():
        sd = r.surface.to_dict()
        cx, cy = sd.get("centre_x"), sd.get("centre_y")
        if cx is None or cy is None:
            loose.append(r)
            continue
        key = (round(cx, 6), round(cy, 6))
        if key not in best or r.fos < best[key].fos:
            best[key] = r
    return list(best.values()) + loose


def slope_intercepts(res) -> tuple:
    """``(x_left, x_right)`` where the surface meets the ground.

    v0.1.201 — ``to_dict().get("x_left") or x_range()`` treated an
    intercept at x = 0.0 as missing and fell back to the circle's centre
    minus its radius."""
    xl, xr = res.surface.x_range()
    sd = res.surface.to_dict()
    if sd.get("x_left") is not None:
        xl = sd["x_left"]
    if sd.get("x_right") is not None:
        xr = sd["x_right"]
    return xl, xr


def sf_along_slope(search_result, use_left: bool = True,
                   use_right: bool = True, bins: Optional[int] = None):
    """Factor of safety against position along the slope: every valid
    surface's factor at its two ground intercepts; with ``bins``, the
    MINIMUM within each of ``bins`` equal intervals. ``(xs, fos)``."""
    pts: list = []
    for ev in search_result.valid():
        try:
            xl, xr = slope_intercepts(ev)
        except Exception:  # noqa: BLE001 - a surface without a range
            continue
        if use_left and xl is not None:
            pts.append((float(xl), ev.fos))
        if use_right and xr is not None:
            pts.append((float(xr), ev.fos))
    if not pts:
        return [], []
    if not bins or bins < 1:
        pts.sort()
        return [p[0] for p in pts], [p[1] for p in pts]
    x_lo = min(p[0] for p in pts)
    x_hi = max(p[0] for p in pts)
    width = (x_hi - x_lo) or 1.0
    best: dict = {}
    for x, f in pts:
        i = min(bins - 1, int((x - x_lo) / width * bins))
        if i not in best or f < best[i][1]:
            best[i] = (x, f)
    ordered = [best[i] for i in sorted(best)]
    return [p[0] for p in ordered], [p[1] for p in ordered]


# ----------------------------------------------------------------------
# Per-slice numbers of the method
# ----------------------------------------------------------------------
def per_slice(result, name: str, index) -> Optional[float]:
    """One entry of a result's per-slice array (``base_normal_force``,
    ``base_shear_force``, ``base_shear_strength``), or None.

    Those are computed by the METHOD and live on the result, not on the
    slice: a reader handed only the slice cannot show them."""
    if result is None:
        return None
    arr = getattr(result, name, None)
    if not arr or index is None or not (0 <= index < len(arr)):
        return None
    v = arr[index]
    return v if isinstance(v, (int, float)) and math.isfinite(v) else None


def slice_stress(result, name: str, slice_) -> Optional[float]:
    """A per-slice force of the method divided by the base length: the
    stress the reference reports."""
    f = per_slice(result, name, getattr(slice_, "index", None))
    length = getattr(slice_, "base_length", 0.0) or 0.0
    if f is None or length <= 0:
        return None
    return f / length


def base_parameter(slice_, name: str):
    """A strength parameter of the material the slice base cuts, from
    ``strength.params``, where every registered model keeps them."""
    mat = getattr(slice_, "material", None)
    if mat is None or getattr(mat, "strength", None) is None:
        return None
    return mat.strength.params.get(name)


def slice_rows(result) -> list:
    """One dict per slice with the METHOD's numbers.

    Forces in kN/m and stresses in kPa: ``sigma_n = N / l`` with N the
    method's base normal force, ``sigma_n_eff = sigma_n - u``, ``tau_f``
    the shear strength per unit base length and ``tau_m = tau_f / F`` (the
    reference's "Shear Stress"; its Ej_2 table: 31.082 / 1.11442 =
    27.8907)."""
    rows = []
    fos = getattr(result, "fos", None)
    for s in getattr(result, "slices", None) or []:
        i = getattr(s, "index", None)
        sn = slice_stress(result, "base_normal_force", s)
        tf = slice_stress(result, "base_shear_strength", s)
        u = getattr(s, "pore_pressure", 0.0) or 0.0
        rows.append({
            "index": i,
            "x_centre": s.x_centre,
            "width": s.width,
            "base_length": s.base_length,
            "base_angle_deg": math.degrees(s.base_angle),
            "height": s.height,
            "weight": s.weight,
            "pore_pressure": u,
            "surface_pressure": getattr(s, "surface_pressure", 0.0),
            "base_normal_force": per_slice(result, "base_normal_force", i),
            "driving_shear": per_slice(result, "base_shear_force", i),
            "sigma_n": sn,
            "sigma_n_eff": None if sn is None else sn - u,
            "tau_f": tf,
            "tau_m": (tf / fos if tf is not None and fos else None),
            "material": (s.material.name if getattr(s, "material", None)
                         else None),
            "cohesion": base_parameter(s, "cohesion"),
            "friction_angle": base_parameter(s, "friction_angle"),
        })
    return rows
