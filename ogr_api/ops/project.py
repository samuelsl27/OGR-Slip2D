# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Opening, saving, describing and checking a model.

``project_summary`` is the operation a caller should reach for first and
most often: it says what the model contains, which material each region
resolves to — including the ones that get the FIRST material by default,
which is invisible otherwise — and whether the model can be analysed.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..errors import InvalidArgument
from ..results import json_safe
from ..snapshot import document_hash, model_hash
from . import operation


def _r(x, nd=4):
    return None if x is None else round(float(x), nd)


def _point_in(x, y, vertices) -> bool:
    from ogr_core.project.project import _point_in_polygon_verts
    return _point_in_polygon_verts(x, y, vertices)


# ----------------------------------------------------------------------
def boundary_info(b, *, with_vertices: bool) -> dict:
    out = {"id": b.id, "type": b.btype.name.lower(),
           "name": b.name or b.btype.display_name,
           "closed": bool(b.polyline.closed),
           "n_vertices": len(b.polyline.vertices)}
    if b.material_id:
        out["material_id"] = b.material_id
    if with_vertices:
        out["vertices"] = [[_r(v.x), _r(v.y)] for v in b.polyline.vertices]
    return out


def material_info(m) -> dict:
    strength = m.strength.to_dict()
    out = {"id": m.id, "name": m.name,
           "strength": {"model": strength.pop("model_id"),
                        "params": json_safe(strength.pop("params")),
                        **json_safe(strength)},
           "unit_weight": m.unit_weight,
           "pore_pressure": m.pore_pressure.value,
           "color": m.color}
    if m.use_sat_unit_weight:
        out["sat_unit_weight"] = m.sat_unit_weight
    if m.water_surface_id:
        out["water_surface_id"] = m.water_surface_id
    if m.pore_pressure.value == "ru":
        out["ru"] = m.ru
    if m.pore_pressure.value == "constant":
        out["constant_u"] = m.constant_u
    for key in ("hu", "phi_b", "air_entry_value", "b_bar",
                "anisotropic_surface_id"):
        v = getattr(m, key)
        if v not in (None, 0.0):
            out[key] = v
    if m.undrained_behaviour:
        out["undrained_behaviour"] = True
    return out


def regions_info(project) -> list[dict]:
    """Every region with the material it RESOLVES to, and how."""
    out = []
    default = project.materials[0] if project.materials else None
    for r in project.resolve_regions():
        mid = getattr(r, "material_id", None)
        mat = project.material_by_id(mid) if mid else default
        cx, cy = r.centroid()
        clicked = any(_point_in(a["x"], a["y"], r.polygon.vertices)
                      for a in project.region_assignments)
        out.append({
            "index": r.region_index,
            "material_id": mat.id if mat else None,
            "material": mat.name if mat else None,
            "how": ("assigned" if clicked else
                    "inherited" if mid and default and mid != default.id
                    else "default_first_material"),
            "centroid": [_r(cx), _r(cy)],
            "area": _r(r.area, 3),
        })
    return out


def settings_highlights(settings) -> dict:
    s = settings
    return {
        "methods": list(s.methods.enabled_methods),
        "num_slices": s.methods.num_slices,
        "tolerance": s.methods.tolerance,
        "surface_type": s.search.surface_type,
        "search_method": s.search.search_method,
        "grid": ("auto" if s.search.grid_x_min is None
                 and s.search.grid_y_min is None else
                 {"x": [s.search.grid_x_min, s.search.grid_x_max],
                  "y": [s.search.grid_y_min, s.search.grid_y_max],
                  "nx": s.search.grid_nx, "ny": s.search.grid_ny}),
        "failure_direction": s.units.failure_direction.value,
        "groundwater_method": s.groundwater.method,
        "groundwater_advanced": s.groundwater.advanced_option(),
        "design_standard": (s.design_standard.standard
                            if s.design_standard.enabled else "off"),
        "seismic_analysis": s.seismic.objective(),
        "units": s.units.system_id,
    }


def status_of(project) -> dict:
    """Refusals and warnings, from the same checks a run makes."""
    from ogr_core.project.rules import compute_blockers
    from ogr_core.geometry import BoundaryType
    from ogr_core.geometry.cleanup import has_self_intersections

    from ..settings_schema import settings_diagnostics

    blockers = [r.message for r in compute_blockers(project)]
    diag = settings_diagnostics(project)
    notes = []
    if project.boundaries and project.external_boundary() is None:
        notes.append("There is no External boundary, so there are no "
                     "regions and no surface can be analysed.")
    for b in project.boundaries:
        if len(b.polyline.vertices) >= 4 and has_self_intersections(
                b.polyline):
            notes.append(f"Boundary {b.id} ({b.btype.name.lower()}) "
                         f"crosses itself.")
    water = [b for b in project.boundaries
             if b.btype in (BoundaryType.WATER_TABLE,
                            BoundaryType.PIEZOMETRIC)]
    for w in water:
        if not any(m.water_surface_id == w.id for m in project.materials):
            notes.append(
                f"{w.btype.display_name} {w.id} is assigned to no material, "
                f"so it produces no pore pressure. Assign it with "
                f"material_set(water_surface_id=...) or boundary_add("
                f"assign_to=...).")
    used = {r.get("material_id") for r in regions_info(project)}
    for m in project.materials:
        if m.id not in used and not any(
                b.material_id == m.id for b in project.boundaries):
            notes.append(f"Material {m.name!r} is used by no region.")
    return {"can_run": not blockers and not diag["problems"],
            "blockers": blockers + diag["problems"],
            "warnings": diag["warnings"], "model_notes": notes}


def summary_of(handle, detail: str = "normal") -> dict:
    p = handle.project
    full = detail == "full"
    undo, redo = handle.stack.history()
    bbox = p.bounding_box() if p.boundaries else None
    out = {
        "project_id": handle.id,
        "name": p.name,
        "path": str(handle.path) if handle.path else None,
        "unsaved_changes": handle.saved_hash != document_hash(p),
        "bounding_box": [_r(v) for v in bbox] if bbox else None,
        "boundaries": [boundary_info(
            b, with_vertices=full or len(b.polyline.vertices) <= 40)
            for b in p.boundaries],
        "materials": [material_info(m) for m in p.materials],
        "regions": regions_info(p),
        "loads": {"distributed": len(p.distributed_loads),
                  "line": len(p.line_loads),
                  "seismic": {"enabled": bool(p.seismic.enabled),
                              "kh": p.seismic.kh, "kv": p.seismic.kv}},
        "supports": len(p.supports),
        "settings": settings_highlights(p.settings),
        "status": status_of(p),
        "history": {"undo": undo[-5:], "redo": redo[-5:]},
        "results": [{"result_id": r.id, "kind": r.kind,
                     "stale": r.model_hash != model_hash(p)}
                    for r in handle.results.values()],
    }
    return out


# ----------------------------------------------------------------------
@operation("project_new", toolset="core")
def project_new(ws, name: Optional[str] = None,
                template: str = "empty") -> dict:
    """Create a model (empty, or the demo slope) and return its
    project_id."""
    from ogr_core.project import Project

    if template not in ("empty", "demo"):
        raise InvalidArgument("template is 'empty' or 'demo'.")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise InvalidArgument("name must be a non-empty string.")
    if template == "demo":
        # The one demo the interface and the command line load too
        # (ogr_core.project.demo, v0.1.196).
        from ogr_core.project.demo import build_demo_project
        project = build_demo_project(name.strip() if name else
                                     "Demo slope")
    else:
        project = Project(name=(name or "Untitled").strip())
    handle = ws.add(project)
    return {"project_id": handle.id, "name": handle.project.name,
            "template": template}


@operation("project_open", toolset="core")
def project_open(ws, path: str) -> dict:
    """Open a .ogr file and return its project_id and a summary."""
    from ogr_core.project import Project

    p = ws.resolve_path(path, suffix=".ogr")
    try:
        project = Project.load(p)
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidArgument(f"{p} is not a readable .ogr file: "
                              f"{type(exc).__name__}: {exc}") from None
    handle = ws.add(project, path=p)
    notes = list(getattr(project.settings.search, "_migration_notes", [])
                 or [])
    out = {"project_id": handle.id, "summary": summary_of(handle)}
    if notes:
        out["migration_notes"] = notes
    return out


@operation("project_save", toolset="core")
def project_save(ws, project_id: Optional[str] = None,
                 path: Optional[str] = None,
                 overwrite: bool = False) -> dict:
    """Save the model as .ogr (to its own file, or to path)."""
    handle = ws.get(project_id)
    with ws.reading(handle.id, "project_save") as project:
        if path is None:
            if handle.path is None:
                raise InvalidArgument(
                    "This model has never been saved; give a path.")
            target = handle.path
        else:
            target = ws.resolve_path(path, for_write=True,
                                     overwrite=overwrite, suffix=".ogr",
                                     own_file=handle.path)
        project.save(target)
        handle.path = target
        handle.saved_hash = document_hash(project)
    return {"project_id": handle.id, "path": str(target)}


@operation("project_close", toolset="core")
def project_close(ws, project_id: Optional[str] = None,
                  discard_changes: bool = False) -> dict:
    """Close a model, refusing to lose unsaved changes unless told to."""
    from ..errors import Conflict

    handle = ws.get(project_id)
    dirty = handle.saved_hash != document_hash(handle.project)
    if dirty and not discard_changes:
        raise Conflict(f"Model {handle.id} has unsaved changes.",
                       hint="Save it with project_save, or pass "
                            "discard_changes=true.")
    ws.close(handle.id)
    return {"closed": handle.id, "discarded_changes": bool(dirty)}


@operation("project_list", toolset="core")
def project_list(ws) -> dict:
    """Every open model."""
    return {"projects": [
        {"project_id": h.id, "name": h.project.name,
         "path": str(h.path) if h.path else None,
         "unsaved_changes": h.saved_hash != document_hash(h.project)}
        for h in ws.projects.values()]}


@operation("project_summary", toolset="core")
def project_summary(ws, project_id: Optional[str] = None,
                    detail: str = "normal") -> dict:
    """What the model contains, what each region resolves to, and whether
    it can run."""
    if detail not in ("normal", "full"):
        raise InvalidArgument("detail must be 'normal' or 'full'.")
    handle = ws.get(project_id)
    with ws.reading(handle.id, "project_summary"):
        return summary_of(handle, detail)


@operation("project_validate", toolset="core")
def project_validate(ws, project_id: Optional[str] = None) -> dict:
    """The checks a run would make, without running."""
    handle = ws.get(project_id)
    with ws.reading(handle.id, "project_validate") as project:
        return {"project_id": handle.id, **status_of(project)}


@operation("project_get", toolset="core")
def project_get(ws, project_id: Optional[str] = None,
                section: str = "materials") -> dict:
    """One section of the model exactly as the .ogr file stores it."""
    from ..errors import unknown

    handle = ws.get(project_id)
    with ws.reading(handle.id, "project_get") as project:
        data = project.to_dict()
    if section not in data:
        raise unknown("section", section, sorted(data))
    return {"project_id": handle.id, "section": section,
            "data": json_safe(data[section])}


@operation("catalog", toolset="core")
def catalog_op(ws, kind: str) -> dict:
    """What the program offers: strength models, methods, searches..."""
    from ..catalog import catalog

    project = None
    if len(ws.projects) == 1:
        project = next(iter(ws.projects.values())).project
    return {"kind": kind, "entries": catalog(kind, project)}
