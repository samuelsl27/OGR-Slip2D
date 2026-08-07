# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.48 — DXF export.

Built as the mirror of the importer, and validated the same way: with an
invariant rather than a snapshot. Here the invariant is the **round
trip** — a model exported and re-imported must come back as the same
geometry.

Stating that precisely matters. The returned drawing is NOT
vertex-for-vertex identical, and it should not be: the importer's
sanitiser splits boundaries at their crossings, so the external boundary
legitimately gains nodes where a material boundary meets it. What must
hold is that the **shape** is unchanged:

* the enclosed area is identical;
* every original vertex is still present;
* every added vertex lies ON an original segment.

That formulation is stronger than "identical lists" would be, because it
would still catch a coordinate being moved, dropped or rounded.

The other design point under test is the **layer contract**: model
geometry goes to layers the importer recognises, results go to ``OGR_X_``
layers it ignores, so re-importing cannot turn a load arrow into a
material boundary.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import ezdxf
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.dxf import (  # noqa: E402
    BOUNDARY_TO_LAYER,
    ExportOptions,
    ImportOptions,
    export_dxf,
    import_dxf,
)
from ogr_core.geometry import (  # noqa: E402
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
)
from ogr_core.project import Project  # noqa: E402

_OUT = Path("/tmp/ogr_export_test.dxf")


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


def _model():
    p = _ej1_project()
    p.add_boundary(Boundary(
        btype=BoundaryType.WATER_TABLE,
        polyline=Polyline(vertices=[Vertex(0, 32), Vertex(120, 22)],
                          closed=False)))
    return p


def _area(vertices) -> float:
    a = 0.0
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i].x, vertices[i].y
        x2, y2 = vertices[(i + 1) % n].x, vertices[(i + 1) % n].y
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def _dist_to_segment(p, a, b) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-30:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def _boundaries(project, btype):
    return [b for b in project.boundaries if b.btype == btype]


# ======================================================================
@_requires(_HAS_EZDXF)
class TestRoundTrip:
    def _round_trip(self, weld=0.05):
        src = _model()
        rep = export_dxf(src, _OUT, ExportOptions(unit="m"))
        assert rep.ok, rep.error
        back = Project(name="back")
        import_dxf(back, _OUT, ImportOptions(unit="m", weld_pct=weld,
                                             simplify=False))
        return src, back

    def test_same_boundary_types_and_counts(self):
        src, back = self._round_trip()
        for bt in (BoundaryType.EXTERNAL, BoundaryType.MATERIAL,
                   BoundaryType.WATER_TABLE):
            assert len(_boundaries(back, bt)) == len(_boundaries(src, bt)), bt

    def test_enclosed_area_is_identical(self):
        """The strongest single check: the shape did not change."""
        src, back = self._round_trip()
        a0 = _area(_boundaries(src, BoundaryType.EXTERNAL)[0]
                   .polyline.vertices)
        a1 = _area(_boundaries(back, BoundaryType.EXTERNAL)[0]
                   .polyline.vertices)
        assert abs(a1 - a0) / a0 < 1e-9, (a0, a1)

    def test_every_original_vertex_survives(self):
        src, back = self._round_trip()
        orig = {(round(v.x, 6), round(v.y, 6))
                for v in _boundaries(src, BoundaryType.EXTERNAL)[0]
                .polyline.vertices}
        ret = {(round(float(v.x), 6), round(float(v.y), 6))
               for v in _boundaries(back, BoundaryType.EXTERNAL)[0]
               .polyline.vertices}
        assert orig <= ret, orig - ret

    def test_added_vertices_lie_on_original_segments(self):
        """Extra nodes are legitimate — the sanitiser splits boundaries at
        their crossings — but only if they sit exactly on the original
        outline. A node off the line would mean the shape moved."""
        src, back = self._round_trip()
        orig_pts = [(v.x, v.y) for v in
                    _boundaries(src, BoundaryType.EXTERNAL)[0]
                    .polyline.vertices]
        segs = list(zip(orig_pts, orig_pts[1:]))
        orig_set = {(round(x, 6), round(y, 6)) for x, y in orig_pts}
        for v in _boundaries(back, BoundaryType.EXTERNAL)[0] \
                .polyline.vertices:
            pt = (float(v.x), float(v.y))
            if (round(pt[0], 6), round(pt[1], 6)) in orig_set:
                continue
            d = min(_dist_to_segment(pt, a, b) for a, b in segs)
            assert d < 1e-6, (pt, d)

    def test_material_boundaries_come_back_unchanged(self):
        """These have no crossings to split, so they must be exact."""
        src, back = self._round_trip()
        def key(bs):
            return sorted(tuple((round(float(v.x), 9),
                                 round(float(v.y), 9))
                                for v in b.polyline.vertices) for b in bs)
        assert key(_boundaries(back, BoundaryType.MATERIAL)) == \
            key(_boundaries(src, BoundaryType.MATERIAL))

    def test_closed_flag_survives(self):
        src, back = self._round_trip()
        assert _boundaries(back, BoundaryType.EXTERNAL)[0] \
            .polyline.closed is True
        assert _boundaries(back, BoundaryType.MATERIAL)[0] \
            .polyline.closed is False

    def test_round_trip_in_millimetres(self):
        """Exporting in mm and importing in mm must return the same model:
        the conversion has to be symmetric."""
        src = _model()
        export_dxf(src, _OUT, ExportOptions(unit="mm"))
        back = Project(name="back")
        import_dxf(back, _OUT, ImportOptions(unit="mm", weld_pct=0.05,
                                             simplify=False))
        a0 = _area(_boundaries(src, BoundaryType.EXTERNAL)[0]
                   .polyline.vertices)
        a1 = _area(_boundaries(back, BoundaryType.EXTERNAL)[0]
                   .polyline.vertices)
        assert abs(a1 - a0) / a0 < 1e-9, (a0, a1)

    def test_regions_still_build_after_the_trip(self):
        from ogr_core.geometry.regions import build_regions
        _src, back = self._round_trip()
        ext = _boundaries(back, BoundaryType.EXTERNAL)[0]
        mats = _boundaries(back, BoundaryType.MATERIAL)
        assert len(build_regions(ext, mats)) >= 2


# ======================================================================
@_requires(_HAS_EZDXF)
class TestLayerContract:
    def test_geometry_uses_importer_layers(self):
        """The contract that makes the round trip possible."""
        export_dxf(_model(), _OUT, ExportOptions(unit="m"))
        doc = ezdxf.readfile(str(_OUT))
        used = {e.dxf.layer for e in doc.modelspace()}
        for layer in ("OGR_EXTERNAL", "OGR_MATERIAL", "OGR_WATER_TABLE"):
            assert layer in used, layer

    def test_mapping_is_derived_from_the_importer(self):
        """Export and import must not be able to drift apart."""
        from ogr_core.dxf.importer import KIND_TO_BOUNDARY
        for _kind, btype in KIND_TO_BOUNDARY.items():
            assert btype in BOUNDARY_TO_LAYER, btype

    def test_results_go_to_ignored_layers(self):
        """A load arrow re-imported as a material boundary would be a
        silent corruption, so results live on OGR_X_ layers."""
        from ogr_core.dxf import guess_kind
        from ogr_core.dxf.reader import DxfEntityKind
        for layer in ("OGR_X_LOADS", "OGR_X_MESH", "OGR_X_SLIP_SURFACE",
                      "OGR_X_ANNOTATION"):
            assert guess_kind(layer) == DxfEntityKind.IGNORE, layer

    def test_reimport_ignores_result_layers(self):
        p = _model()
        p.add_boundary(Boundary(
            btype=BoundaryType.TENSION_CRACK,
            polyline=Polyline(vertices=[Vertex(40, 50), Vertex(40, 44)],
                              closed=False)))
        export_dxf(p, _OUT, ExportOptions(unit="m"))
        back = Project(name="back")
        pv, _created = import_dxf(back, _OUT,
                                  ImportOptions(unit="m", weld_pct=0.05))
        # Annotations were written but must not have become geometry
        assert all(b.btype in BOUNDARY_TO_LAYER for b in back.boundaries)

    def test_layers_are_coloured(self):
        export_dxf(_model(), _OUT, ExportOptions(unit="m"))
        doc = ezdxf.readfile(str(_OUT))
        colours = {l.dxf.name: l.dxf.color for l in doc.layers
                   if l.dxf.name.startswith("OGR")}
        assert len(set(colours.values())) > 1, colours

    def test_units_recorded_in_the_header(self):
        for unit, code in (("m", 6), ("mm", 4), ("ft", 2)):
            export_dxf(_model(), _OUT, ExportOptions(unit=unit))
            doc = ezdxf.readfile(str(_OUT))
            assert doc.header.get("$INSUNITS") == code, unit


# ======================================================================
@_requires(_HAS_EZDXF)
class TestContents:
    def _with_results(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        p = _model()
        r = GridSearch(method=BishopSimplified(), grid_x=(70, 100),
                       grid_y=(60, 85), grid_nx=4, grid_ny=4,
                       radius_increment=8, min_radius=15, num_slices=18,
                       min_area=0.5).run(p)
        return p, {"bishop_simplified": r}

    def test_slip_surface_written(self):
        p, res = self._with_results()
        rep = export_dxf(p, _OUT, ExportOptions(unit="m"), res)
        assert rep.entities.get("OGR_X_SLIP_SURFACE") == 1

    def test_slip_surface_follows_the_analysed_slices(self):
        """Drawing the whole circle would be misleading; only the arc
        actually analysed is the failure surface."""
        p, res = self._with_results()
        export_dxf(p, _OUT, ExportOptions(unit="m"), res)
        doc = ezdxf.readfile(str(_OUT))
        pl = [e for e in doc.modelspace()
              if e.dxf.layer == "OGR_X_SLIP_SURFACE"][0]
        pts = [(x, y) for x, y, *_ in pl.get_points()]
        crit = res["bishop_simplified"].critical
        assert abs(pts[0][0] - crit.slices[0].base_x_left) < 1e-6
        assert abs(pts[-1][0] - crit.slices[-1].base_x_right) < 1e-6

    def test_factor_of_safety_annotated(self):
        p, res = self._with_results()
        export_dxf(p, _OUT, ExportOptions(unit="m"), res)
        doc = ezdxf.readfile(str(_OUT))
        texts = [e.dxf.text for e in doc.modelspace()
                 if e.dxftype() == "TEXT"]
        assert any("FS =" in t for t in texts), texts

    def test_options_switch_content_off(self):
        p, res = self._with_results()
        rep = export_dxf(p, _OUT, ExportOptions(
            unit="m", slip_surface=False, annotations=False), res)
        assert "OGR_X_SLIP_SURFACE" not in rep.entities
        assert "OGR_X_ANNOTATION" not in rep.entities

    def test_boundaries_can_be_excluded(self):
        rep = export_dxf(_model(), _OUT,
                         ExportOptions(unit="m", boundaries=False))
        assert "OGR_EXTERNAL" not in rep.entities

    def test_mesh_off_by_default(self):
        opts = ExportOptions()
        assert opts.mesh is False

    def test_mesh_written_when_requested(self):
        from ogr_fem2d.mesh import generate_mesh_for_project
        p = _model()
        p.fem_mesh = generate_mesh_for_project(p, target_elements=60)
        rep = export_dxf(p, _OUT, ExportOptions(unit="m", mesh=True))
        assert rep.entities.get("OGR_X_MESH", 0) > 10

    def test_report_counts_and_summary(self):
        rep = export_dxf(_model(), _OUT, ExportOptions(unit="m"))
        assert rep.ok
        assert rep.total == sum(rep.entities.values())
        assert "entities" in rep.summary()

    def test_project_is_not_modified(self):
        p = _model()
        before = p.to_dict()
        export_dxf(p, _OUT, ExportOptions(unit="m"))
        assert p.to_dict() == before

    def test_unwritable_path_reports_cleanly(self):
        rep = export_dxf(_model(), "/nonexistent-dir/x.dxf",
                         ExportOptions(unit="m"))
        assert not rep.ok
        assert rep.error


# ======================================================================
@_requires(_HAS_EZDXF and _QT)
class TestDialog:
    def _dlg(self, project=None, has_results=False):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.dialogs.dxf_export_dialog import DxfExportDialog
        return DxfExportDialog(project or _model(), has_results, None)

    def test_unavailable_content_is_disabled(self):
        """Nothing should be offered that the model cannot provide."""
        d = self._dlg()
        assert d.chk_boundaries.isEnabled() is True
        assert d.chk_mesh.isEnabled() is False
        assert d.chk_surface.isEnabled() is False
        assert d.chk_mesh.isChecked() is False

    def test_surface_enabled_with_results(self):
        d = self._dlg(has_results=True)
        assert d.chk_surface.isEnabled() is True

    def test_mesh_enabled_when_present(self):
        from ogr_fem2d.mesh import generate_mesh_for_project
        p = _model()
        p.fem_mesh = generate_mesh_for_project(p, target_elements=60)
        d = self._dlg(p)
        assert d.chk_mesh.isEnabled() is True

    def test_options_reflect_the_controls(self):
        d = self._dlg(has_results=True)
        d.cbo_unit.setCurrentIndex(d.cbo_unit.findData("mm"))
        d.chk_annotations.setChecked(False)
        d.sp_arrow.setValue(5.0)
        d._accept()
        assert d.options.unit == "mm"
        assert d.options.annotations is False
        assert abs(d.options.arrow_pct - 5.0) < 1e-9

    def test_layer_contract_is_explained(self):
        """The user must be told why some layers come back and others do
        not, rather than having to discover it."""
        from PySide6.QtWidgets import QLabel
        d = self._dlg()
        text = " ".join(" ".join(w.text().split())
                        for w in d.findChildren(QLabel))
        assert "OGR_X_" in text
        assert "imported back" in text

    def test_menu_action_is_wired(self):
        QApplication.instance() or QApplication([])
        src = Path(__file__).resolve().parent.parent / "ogr_gui" \
            / "main_window.py"
        assert "DXF export planned" not in src.read_text(encoding="utf-8")
