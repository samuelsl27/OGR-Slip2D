# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Results as JSON a language model can read.

A ``SearchResult`` keeps every trial surface with all its slices — about
30 MB for the 4840 circles of the Ej_2 grid — so it is summarised, never
handed over whole. Everything here returns plain JSON: no NaN, no Infinity
(``json.dumps(..., allow_nan=False)`` is the check the tests run, the same
one ``LEMResult.to_dict`` has been held to since v0.1.152), no numpy
scalars, no enums.

What the headline number IS — factor of safety, over-design factor,
critical seismic coefficient or Newmark displacement — is asked of
``ogr_slip2d.reported``, the one place that decides it for the interface
too.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import enum
import math
from typing import Optional

#: Units of each caption's value, in the SI the engine works in.
_CAPTION_UNITS = {"fos": "-", "overdesign": "-", "ky": "-", "newmark": "m"}


def json_safe(obj):
    """``obj`` as plain JSON: non-finite floats become None."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, int):
        return obj
    if isinstance(obj, enum.Enum):
        return json_safe(obj.value)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [json_safe(v) for v in obj]
    # numpy scalars and arrays, without importing numpy here
    if hasattr(obj, "tolist") and callable(obj.tolist):
        return json_safe(obj.tolist())
    if hasattr(obj, "item") and callable(obj.item):
        try:
            return json_safe(obj.item())
        except (TypeError, ValueError):
            pass
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return json_safe(obj.to_dict())
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict
        return json_safe(asdict(obj))
    return str(obj)


def _r(x, nd: int = 6):
    """Round for reading; None stays None."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


# ----------------------------------------------------------------------
def surface_summary(surface) -> Optional[dict]:
    """The geometry of a slip surface, compactly."""
    if surface is None:
        return None
    d = surface.to_dict() if hasattr(surface, "to_dict") else {}
    kind = d.get("type")
    if kind == "circle":
        out = {"type": "circle",
               "centre_x": _r(d.get("centre_x")),
               "centre_y": _r(d.get("centre_y")),
               "radius": _r(d.get("radius")),
               "x_left": _r(d.get("x_left")),
               "x_right": _r(d.get("x_right"))}
    elif kind == "polyline":
        verts = d.get("polyline", {}).get("vertices", [])
        out = {"type": "polyline",
               "vertices": [[_r(v.get("x") if isinstance(v, dict) else v[0]),
                             _r(v.get("y") if isinstance(v, dict) else v[1])]
                            for v in verts]}
    else:
        out = {"type": kind or type(surface).__name__}
    if d.get("tension_cracks"):
        out["tension_cracks"] = json_safe(d["tension_cracks"])
    return out


def lem_summary(res, *, with_slices: bool = False) -> Optional[dict]:
    """One evaluated surface: factor, convergence, admissibility, geometry."""
    if res is None:
        return None
    details = getattr(res, "details", None) or {}
    out = {
        "fos": _r(res.fos),
        "converged": bool(res.converged),
        "iterations": int(res.iterations),
        "valid": bool(getattr(res, "is_valid", False)),
        "admissible": bool(getattr(res, "admissible", True)),
        "surface": surface_summary(res.surface),
        "n_slices": len(res.slices) if res.slices is not None else 0,
    }
    if res.error_message:
        out["error"] = res.error_message
    if getattr(res, "reason", ""):
        out["reason"] = res.reason
    note = getattr(res, "admissibility_note", "")
    if note:
        out["admissibility_note"] = note
    extras = {k: _r(details[k]) for k in ("lambda", "ky", "ky_fos",
                                         "newmark_displacement")
              if k in details and isinstance(details[k], (int, float))}
    if extras:
        out["details"] = extras
    if with_slices:
        out["slices"] = slice_table(res)
    return out


def slice_table(res) -> list[dict]:
    """Per-slice rows: geometry, weight, water and base forces.

    Forces are kN/m and stresses kPa. ``base_normal_force`` is a FORCE,
    not a stress (the v0.1.107 lesson): the effective normal stress is
    ``N/l - u``.
    """
    if res is None or res.slices is None:
        return []
    rows = []
    N = list(getattr(res, "base_normal_force", []) or [])
    S = list(getattr(res, "base_shear_force", []) or [])
    R = list(getattr(res, "base_shear_strength", []) or [])
    for i, s in enumerate(res.slices):
        d = s.to_dict()
        row = {k: _r(d.get(k), 4) for k in (
            "x_centre", "width", "base_x_left", "base_y_left",
            "base_x_right", "base_y_right", "base_angle_deg", "base_length",
            "height", "weight", "pore_pressure", "surface_pressure")}
        row["index"] = d.get("index", i)
        row["material_id"] = d.get("material_id")
        if i < len(N):
            row["base_normal_force"] = _r(N[i], 4)
        if i < len(S):
            row["base_shear_force"] = _r(S[i], 4)
        if i < len(R):
            row["base_shear_resistance"] = _r(R[i], 4)
        rows.append(row)
    return rows


def headline(search_result, factor_report=None) -> dict:
    """``{caption, value, unit}`` of a run's critical surface."""
    from ogr_slip2d.reported import reported_caption

    caption = reported_caption(search_result, factor_report)
    crit = getattr(search_result, "critical", None)
    value = None
    if crit is not None:
        details = crit.details or {}
        if caption == "newmark":
            value = details.get("newmark_displacement")
        elif caption == "ky":
            value = details.get("ky")
        else:
            value = crit.fos
    return {"caption": caption, "value": _r(value),
            "unit": _CAPTION_UNITS[caption]}


def counts(search_result) -> dict:
    """The run's population, with the identities that make it checkable."""
    sr = search_result
    return {
        "attempted": int(getattr(sr, "attempts", 0)),
        "total": int(getattr(sr, "total_count", 0)),
        "valid": int(getattr(sr, "valid_count", 0)),
        "invalid": int(getattr(sr, "invalid_count", 0)),
        "inadmissible": int(getattr(sr, "inadmissible_count", 0)),
        "focus_rejected": int(getattr(sr, "focus_rejected", 0)),
        "user_surfaces": len(getattr(sr, "user_evaluations", []) or []),
    }


def search_summary(method_id: str, search_result, factor_report=None,
                   *, top: int = 0) -> dict:
    """What one method's search found."""
    crit = getattr(search_result, "critical", None)
    out = {
        "method_id": method_id,
        **headline(search_result, factor_report),
        "critical": lem_summary(crit),
        "counts": counts(search_result),
        "optimized": getattr(search_result, "optimized", None) is not None,
    }
    minima = getattr(search_result, "minima", None) or []
    if minima:
        out["minima"] = [lem_summary(m) for m in minima[:10]]
    notes = list(getattr(search_result, "notes", []) or [])
    if notes:
        out["notes"] = notes
    if top:
        out["top"] = [lem_summary(r) for r in search_result.top_n(top)]
    return out


def factor_report_summary(report) -> dict:
    if report is None:
        return {"applied": False}
    return json_safe({"applied": bool(getattr(report, "applied", False)),
                      "standard": getattr(report, "standard", "none"),
                      "summary": report.summary(),
                      "notes": list(getattr(report, "notes", []))})


def outcome_summary(results: dict, factor_report=None,
                    warnings=()) -> dict:
    """Every method of one run, plus the run-level report and warnings."""
    return {
        "methods": [search_summary(mid, sr, factor_report)
                    for mid, sr in results.items()],
        "factor_report": factor_report_summary(factor_report),
        "warnings": list(warnings),
    }


# ----------------------------------------------------------------------
# Groundwater and the drawdown sweep (v0.1.200, spec 008 F3a)
# ----------------------------------------------------------------------
def _span(values) -> Optional[list]:
    vals = [v for v in values if v is not None and math.isfinite(v)]
    return [_r(min(vals)), _r(max(vals))] if vals else None


def seepage_field_summary(r) -> Optional[dict]:
    """One seepage field: convergence and the range of each quantity.

    Heads in metres, pore pressure in kPa, velocity in the permeability's
    unit (Darcy flux).
    """
    if r is None:
        return None
    out = {"converged": bool(r.converged), "iterations": r.iterations}
    if r.total_head:
        out["total_head_m"] = _span(r.total_head)
        out["pressure_head_m"] = _span(r.pressure_head)
        out["pore_pressure_kpa"] = _span(r.pore_pressure)
        out["seepage_face_nodes"] = len(r.seepage_nodes or [])
        if r.velocity:
            out["max_velocity"] = _r(max(math.hypot(vx, vy)
                                         for vx, vy in r.velocity), 9)
    notes = {k: v for k, v in (r.notes or {}).items()
             if k in ("error", "warning", "time", "label", "calculate_sf",
                      "fos", "fos_min", "fos_warning")}
    if notes:
        out["notes"] = json_safe(notes)
    return out


def stage_rows(results) -> list:
    """The transient stages as rows: time, label, convergence, factors."""
    rows = []
    for i, r in enumerate(results or []):
        n = r.notes or {}
        rows.append(json_safe({
            "stage": i, "time": n.get("time"), "label": n.get("label", ""),
            "calculate_sf": bool(n.get("calculate_sf")),
            "converged": bool(r.converged), "iterations": r.iterations,
            "fos": n.get("fos"), "fos_min": n.get("fos_min"),
            "fos_warning": n.get("fos_warning"),
            "error": n.get("error")}))
    return rows


def groundwater_summary(project, warnings=()) -> dict:
    """What a groundwater job found, for ``summary.json``."""
    mesh = project.fem_mesh
    stages = list(project.transient_results or [])
    missing = [m.name for m in project.materials if m.hydraulic is None]
    out = {"analysis": "transient" if stages else "steady",
           "mesh": {"elements": mesh.element_count if mesh else 0,
                    "nodes": mesh.node_count if mesh else 0},
           "field": seepage_field_summary(project.seepage_result),
           "warnings": list(warnings)}
    if stages:
        out["stages"] = stage_rows(stages)
        out["field_is"] = "the last stage"
    if missing:
        out["default_hydraulic_properties"] = missing
    return out


def _level(lv):
    return "total drawdown" if lv is None else _r(lv)


def drawdown_sweep_summary(sweep, factor_report=None, warnings=()) -> dict:
    """The drawdown level sweep, per method: every level's factor, the
    worst level, and how much the total drawdown alone overstates it."""
    methods = []
    for mid, ms in sweep.by_method.items():
        crit = ms.critical()
        total = ms.at_total_drawdown()
        margin = ms.unsafe_margin()
        methods.append(json_safe({
            "method_id": mid,
            "levels": [_level(lv) for lv in ms.levels],
            "fos": [(_r(f) if f is not None else None) for f in ms.fos],
            "failed": ms.failed,
            "critical": ({"level": _level(crit[0]), "fos": _r(crit[1]),
                          "surface": crit[2]} if crit else None),
            "total_drawdown_fos": _r(total[1]) if total else None,
            "total_overstates_by": (_r(margin, 4) if margin is not None
                                    else None)}))
    worst = sweep.worst()
    return json_safe({
        "methods": methods,
        "worst": ({"method_id": worst[0], "level": _level(worst[1]),
                   "fos": _r(worst[2])} if worst else None),
        "notes": sweep.notes,
        "factor_report": factor_report_summary(factor_report),
        "warnings": list(warnings)})
