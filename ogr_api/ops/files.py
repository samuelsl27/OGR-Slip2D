# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Files in and out: DXF geometry, the PDF report, properties from another
project.

A DXF import goes in two steps, as in the interface: ``dxf_inspect`` reads
the file and says which layers it found and what each looks like (touching
nothing), and ``dxf_import`` applies it with the caller's mapping of layers
to boundary types — as ONE undo step, which the interface's import is not.
After applying, references the import left dangling (a material pointing at
a water table the import replaced) are cleared and reported, and a model
left with two External boundaries is refused rather than kept.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

from ..coerce import coerce_enum, coerce_value
from ..errors import Conflict, InvalidArgument, unknown
from ..results import json_safe
from . import operation


def _preview(path, unit, layer_kinds, weld_pct, simplify, simplify_pct,
             replace_model):
    from ogr_core.dxf.importer import ImportOptions, preview
    from ogr_core.dxf.reader import DxfEntityKind

    kinds = {}
    for layer, kind in (layer_kinds or {}).items():
        kinds[str(layer)] = coerce_enum(kind, DxfEntityKind,
                                        f"layer_kinds[{layer!r}]")
    opts = ImportOptions(
        unit=str(unit), weld_pct=coerce_value(weld_pct, float, "weld_pct"),
        simplify=coerce_value(simplify, bool, "simplify"),
        simplify_pct=coerce_value(simplify_pct, float, "simplify_pct"),
        replace_model=coerce_value(replace_model, bool, "replace_model"),
        layer_kinds=kinds)
    return opts, preview(str(path), opts)


def _preview_info(pv) -> dict:
    cat = pv.catalogue
    rep = pv.report
    out = {"ok": pv.ok, "summary": pv.summary(), "error": pv.error,
           "boundaries": dict(pv.boundaries), "regions": pv.regions,
           "areas_match": bool(pv.area_matches)}
    if cat is not None:
        out["suggested_unit"] = cat.suggested_unit()
        out["layers"] = [{"name": lay.name,
                          "entities": lay.entity_count,
                          "vertices": lay.vertex_count,
                          "proposed_kind": lay.proposed_kind.value,
                          "kind": lay.kind.value}
                         for lay in cat.layers]
    if rep is not None:
        out["problems"] = list(getattr(rep, "problems", []) or [])
        out["notes"] = list(getattr(rep, "notes", []) or [])
    return json_safe(out)


@operation("dxf_inspect", toolset="files")
def dxf_inspect(ws, path: str, unit: str = "m",
                layer_kinds: Optional[dict] = None) -> dict:
    """Read a DXF without importing: its layers, the geometry type proposed
    for each, the unit it suggests and the problems found."""
    p = ws.resolve_path(path, suffix=".dxf")
    _opts, pv = _preview(p, unit, layer_kinds, 0.05, True, 0.02, True)
    return {"path": str(p), **_preview_info(pv)}


@operation("dxf_import", toolset="files", mutates=True)
def dxf_import(ws, path: str, project_id: Optional[str] = None,
               unit: str = "m", layer_kinds: Optional[dict] = None,
               weld_pct: float = 0.05, simplify: bool = True,
               simplify_pct: float = 0.02,
               replace_model: bool = True) -> dict:
    """Import DXF geometry into the model (layers mapped to boundary types
    with layer_kinds, e.g. {'TERRENO': 'external'})."""
    from ogr_core.dxf.importer import apply_to_project
    from ogr_core.geometry import BoundaryType

    p = ws.resolve_path(path, suffix=".dxf")
    opts, pv = _preview(p, unit, layer_kinds, weld_pct, simplify,
                        simplify_pct, replace_model)
    if not pv.ok:
        raise InvalidArgument(f"The DXF cannot be imported: {pv.error}",
                              hint="dxf_inspect shows its layers; map them "
                                   "with layer_kinds.")

    def edit(project):
        created = apply_to_project(project, pv, opts)
        if len(project.boundaries_of(BoundaryType.EXTERNAL)) > 1:
            raise Conflict("The import leaves two External boundaries.",
                           hint="Use replace_model=true, or map only one "
                                "layer to 'external'.")
        notes = []
        alive = {b.id for b in project.boundaries}
        for m in project.materials:
            if m.water_surface_id and m.water_surface_id not in alive:
                from ogr_core.project.rules import assign_water_surface
                assign_water_surface(project, m.water_surface_id, [],
                                     [m.id])
                notes.append(f"{m.name!r} pointed at a water surface the "
                             f"import replaced; assign the new one.")
            if m.anisotropic_surface_id and \
                    m.anisotropic_surface_id not in alive:
                m.anisotropic_surface_id = None
                notes.append(f"{m.name!r} lost its anisotropic surface.")
        # Duplicate vertices the drawing itself had. (Until v0.1.197 every
        # imported closed polyline also repeated its first point — the DXF
        # package's ring format leaking into the model; the importer now
        # drops it, so what is counted here is the drawing's own.)
        from ogr_core.geometry.cleanup import inspect_boundaries
        dups = sum(r["duplicate_vertices"] for r in
                   inspect_boundaries(project.boundaries)["boundaries"])
        if dups:
            notes.append(f"{dups} duplicate vertex/vertices in the "
                         f"imported geometry; geometry_cleanup(apply=true) "
                         f"removes them.")
        project.invalidate_regions_cache()
        project._notify("geometry_changed")
        return {"created": created, "regions": len(project.resolve_regions()),
                "notes": notes, "preview": _preview_info(pv)}

    return ws.mutate(project_id, "Import DXF", edit)


def _search_results(ws, result_id, project_id):
    handle, res = ws.find_result(result_id)
    if project_id is not None and project_id != handle.id:
        raise InvalidArgument(f"{result_id} belongs to {handle.id}.")
    if res.kind != "analysis":
        raise Conflict(f"{result_id} is a single evaluated surface, not an "
                       f"analysis.", hint="Use the result_id of "
                                          "analysis_run.")
    from ..snapshot import model_hash
    stale = model_hash(handle.project) != res.model_hash
    return handle, res.payload().get("results", {}), stale


@operation("dxf_export", toolset="files")
def dxf_export(ws, path: str, project_id: Optional[str] = None,
               result_id: Optional[str] = None, overwrite: bool = False,
               unit: str = "m", boundaries: bool = True,
               supports: bool = True, loads: bool = True,
               slip_surface: bool = True,
               annotations: bool = True) -> dict:
    """Export the model (and a result's critical surfaces) to DXF."""
    from ogr_core.dxf.exporter import ExportOptions, export_dxf

    results, stale = None, False
    if result_id is not None:
        handle, results, stale = _search_results(ws, result_id, project_id)
        project_id = handle.id
    target = ws.resolve_path(path, for_write=True, overwrite=overwrite,
                             suffix=".dxf")
    opts = ExportOptions(unit=str(unit), boundaries=bool(boundaries),
                         supports=bool(supports), loads=bool(loads),
                         slip_surface=bool(slip_surface) and bool(results),
                         annotations=bool(annotations))
    with ws.reading(project_id, "dxf_export") as project:
        rep = export_dxf(project, str(target), opts, results=results)
    if not rep.ok:
        raise InvalidArgument(f"DXF export failed: {rep.error}")
    out = {"path": str(target), "summary": rep.summary()}
    if stale:
        out["notes"] = ["The result is stale: the model changed after it "
                        "was computed."]
    return json_safe(out)


@operation("report_generate", toolset="files")
def report_generate(ws, path: str, result_id: str,
                    overwrite: bool = False,
                    author: Optional[str] = None,
                    company: Optional[str] = None,
                    title: Optional[str] = None) -> dict:
    """A PDF report of an analysis result."""
    from ogr_core.report.report_generator import generate_report

    handle, results, stale = _search_results(ws, result_id, None)
    target = ws.resolve_path(path, for_write=True, overwrite=overwrite,
                             suffix=".pdf")
    with ws.reading(handle.id, "report_generate") as project:
        try:
            written = generate_report(project, results, str(target),
                                      author=author, company=company,
                                      title=title)
        except RuntimeError as exc:  # reportlab missing
            raise Conflict(str(exc)) from None
    out = {"path": str(written)}
    if stale:
        out["notes"] = ["The result is stale: the model changed after it "
                        "was computed; the report shows the old numbers."]
    return out


@operation("properties_import", toolset="files", mutates=True)
def properties_import(ws, path: str, project_id: Optional[str] = None,
                      what: str = "both",
                      names: Optional[list] = None) -> dict:
    """Copy materials and/or support types from another .ogr file."""
    from ogr_core.project import Project
    from ogr_core.project.properties_import import import_properties

    kinds = ("materials", "support_types", "both")
    if what not in kinds:
        raise unknown("what", what, kinds)
    p = ws.resolve_path(path, suffix=".ogr")
    try:
        source = Project.load(p)
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidArgument(f"{p} is not a readable .ogr file: {exc}") \
            from None

    def edit(project):
        return import_properties(
            project, source, materials=what in ("materials", "both"),
            support_types=what in ("support_types", "both"),
            names=coerce_value(names, list[str], "names")
            if names is not None else None)

    return ws.mutate(project_id, "Import properties", edit)
