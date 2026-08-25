# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
DXF import driver — the bridge from sanitised geometry to the model.

Phase D0 reads, Phase D1 repairs, and this module applies the result to a
:class:`Project`. It is kept separate from the dialog so the whole import
can be exercised — and scripted — without a GUI.

Two decisions worth stating:

* **The preview is computed with the real pipeline.** ``preview()`` runs
  exactly the same read-and-sanitise path as the import, so the vertex
  counts and problem list the user sees before confirming are the ones
  that will actually apply. A preview computed by a cheaper approximation
  would be worse than none.
* **Import proceeds even with unresolved problems**, as agreed: the user
  corrects in the editor afterwards. What must never happen is a *silent*
  problem, so everything the sanitiser could not fix is reported.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

from .reader import DxfEntityKind, read_dxf
from .sanitiser import (
    DEFAULT_SIMPLIFY_PCT,
    DEFAULT_WELD_PCT,
    GeometrySanitiser,
)

# Which model boundary type each DXF kind becomes.
KIND_TO_BOUNDARY = {
    DxfEntityKind.EXTERNAL: BoundaryType.EXTERNAL,
    DxfEntityKind.MATERIAL: BoundaryType.MATERIAL,
    DxfEntityKind.WATER_TABLE: BoundaryType.WATER_TABLE,
    DxfEntityKind.PIEZO: BoundaryType.PIEZOMETRIC,
    DxfEntityKind.DRAWDOWN: BoundaryType.DRAWDOWN,
    DxfEntityKind.TENSION_CRACK: BoundaryType.TENSION_CRACK,
    DxfEntityKind.WEAK_LAYER: BoundaryType.WEAK_LAYER,
}


@dataclass
class ImportOptions:
    """Everything the dialog collects."""

    unit: str = "m"
    segments_per_circle: int = 64
    weld_pct: float = DEFAULT_WELD_PCT
    simplify: bool = True
    simplify_pct: float = DEFAULT_SIMPLIFY_PCT
    replace_model: bool = True
    # layer name -> DxfEntityKind, overriding the automatic proposal
    layer_kinds: dict = field(default_factory=dict)


@dataclass
class ImportPreview:
    """Result of a dry run, shown before the user confirms."""

    catalogue: Optional[object] = None
    sanitised: dict = field(default_factory=dict)
    report: Optional[object] = None
    regions: int = 0
    region_area: float = 0.0
    external_area: float = 0.0
    boundaries: dict = field(default_factory=dict)   # kind -> count
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def area_matches(self) -> bool:
        """Whether the regions tile the external boundary.

        This is the single strongest indicator that the geometry is
        usable — the same invariant used to validate the FE mesh. If it
        fails, some region did not close.
        """
        if self.external_area <= 0:
            return False
        return (abs(self.region_area - self.external_area)
                / self.external_area) < 1e-4

    def summary(self) -> str:
        if not self.ok:
            return self.error or "failed"
        rep = self.report
        bits = [f"{sum(self.boundaries.values())} boundaries"]
        if rep is not None:
            bits.append(f"{rep.vertices_before} → {rep.vertices_after} "
                        f"vertices")
        bits.append(f"{self.regions} region(s)")
        if self.external_area > 0:
            bits.append("areas match" if self.area_matches
                        else "AREAS DO NOT MATCH")
        return "   |   ".join(bits)


# ======================================================================
def _to_boundary(poly, btype) -> Boundary:
    return Boundary(
        btype=btype,
        polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in poly.points],
            closed=poly.closed))


def _polygon_area(points) -> float:
    a = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def preview(path, options: ImportOptions) -> ImportPreview:
    """Read, sanitise and evaluate a DXF **without touching the model**.

    Runs the real pipeline, so what the user sees is what will be applied.
    """
    pv = ImportPreview()
    try:
        cat = read_dxf(path, unit=options.unit,
                       segments_per_circle=options.segments_per_circle)
    except RuntimeError as exc:
        pv.error = str(exc)
        return pv
    pv.catalogue = cat

    # Apply the user's layer mapping over the automatic proposal
    for lay in cat.layers:
        if lay.name in options.layer_kinds:
            lay.kind = options.layer_kinds[lay.name]

    by_kind: dict = {}
    for lay in cat.layers:
        if lay.kind != DxfEntityKind.IGNORE:
            by_kind.setdefault(lay.kind, []).extend(lay.polylines)
    if not by_kind:
        pv.error = ("No layer has been assigned a geometry type. Use the "
                    "table to say what each layer represents.")
        return pv

    san = GeometrySanitiser(cat.diagonal(), weld_pct=options.weld_pct,
                            simplify_pct=options.simplify_pct,
                            simplify=options.simplify)
    pv.sanitised = san.run(by_kind)
    pv.report = san.report
    pv.boundaries = {k.value: len(v) for k, v in pv.sanitised.items()}

    # Region check: the decisive quality indicator
    ext = pv.sanitised.get(DxfEntityKind.EXTERNAL, [])
    if ext:
        pv.external_area = _polygon_area(ext[0].points)
        try:
            from ogr_core.geometry.regions import build_regions
            regions = build_regions(
                _to_boundary(ext[0], BoundaryType.EXTERNAL),
                [_to_boundary(p, BoundaryType.MATERIAL)
                 for p in pv.sanitised.get(DxfEntityKind.MATERIAL, [])])
            pv.regions = len(regions)
            pv.region_area = sum(r.area for r in regions)
        except Exception as exc:  # noqa: BLE001
            san.report.add_problem(
                "regions", f"Regions could not be built: {exc}")
    return pv


# ======================================================================
def apply_to_project(project, pv: ImportPreview,
                     options: ImportOptions) -> dict:
    """Write a preview's geometry into ``project``.

    Returns a count of the boundaries created per type. Nothing is written
    when the preview failed, so a broken read cannot half-populate a
    model.
    """
    if not pv.ok or not pv.sanitised:
        return {}

    if options.replace_model:
        # Keep only what the DXF does not define, so an import cannot
        # leave a stale external boundary behind the new one.
        replaced = {KIND_TO_BOUNDARY[k] for k in pv.sanitised
                    if k in KIND_TO_BOUNDARY}
        project.boundaries = [b for b in project.boundaries
                              if b.btype not in replaced]

    created: dict = {}
    for kind, polys in pv.sanitised.items():
        btype = KIND_TO_BOUNDARY.get(kind)
        if btype is None:
            continue          # supports are handled separately (D3)
        for p in polys:
            if len(p.points) < 2:
                continue
            project.add_boundary(_to_boundary(p, btype))
            created[btype.name] = created.get(btype.name, 0) + 1

    project.is_dirty = True
    return created


def import_dxf(project, path, options: Optional[ImportOptions] = None):
    """Convenience one-shot import. Returns ``(preview, created)``."""
    options = options or ImportOptions()
    pv = preview(path, options)
    created = apply_to_project(project, pv, options) if pv.ok else {}
    return pv, created
