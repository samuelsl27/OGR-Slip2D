# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.46 — DXF import driver and dialog (Phase D2).

The driver joins Phases D0 and D1 to the project model; the dialog lets
the user map layers and see what will happen before committing.

Points the tests pin down:

* **The preview runs the real pipeline.** A preview computed by a cheaper
  approximation would be worse than none, so importing must produce
  exactly what the preview reported.
* **Any layer is mappable**, including one called ``0`` whose name matches
  nothing — that was an explicit requirement.
* **The area invariant is surfaced to the user**: whether the region areas
  add up to the external boundary is the single strongest indicator that
  the geometry closed, and the dialog says so in words.
* **Import is never blocked** by unresolved problems, but nothing is
  written when the *read* failed, so a broken file cannot half-populate a
  model.
"""
from __future__ import annotations

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

from ogr_core.dxf import (  # noqa: E402
    DxfEntityKind as K,
    ImportOptions,
    apply_to_project,
    import_dxf,
    preview,
)
from ogr_core.geometry import BoundaryType  # noqa: E402
from ogr_core.project import Project  # noqa: E402

_DXF = Path("/tmp/ogr_import_test.dxf")


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


def _make_dxf(path=_DXF):
    """A realistic drawing: open external boundary, material lines that
    fall slightly short, and a useful layer named ``0``."""
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for name in ("OGR_EXTERNAL", "OGR_MATERIAL", "0"):
        if name not in doc.layers:
            doc.layers.add(name)
    msp.add_lwpolyline(
        [(0, 0), (120, 0), (120, 25), (75, 25), (50, 50), (0, 50)],
        dxfattribs={"layer": "OGR_EXTERNAL"})
    msp.add_line((0.3, 30), (74.8, 25.1),
                 dxfattribs={"layer": "OGR_MATERIAL"})
    msp.add_line((0.2, 20), (119.7, 10),
                 dxfattribs={"layer": "OGR_MATERIAL"})
    msp.add_lwpolyline([(0, 35), (60, 32), (120, 30)],
                       dxfattribs={"layer": "0"})
    doc.saveas(str(path))
    return path


def _opts(**kw):
    base = dict(unit="m", weld_pct=0.5)
    base.update(kw)
    return ImportOptions(**base)


# ======================================================================
@_requires(_HAS_EZDXF)
class TestPreview:
    def test_repairs_and_closes_regions(self):
        pv = preview(_make_dxf(), _opts())
        assert pv.ok, pv.error
        assert pv.regions >= 2
        assert pv.area_matches, (pv.region_area, pv.external_area)

    def test_area_invariant_is_exposed(self):
        """The dialog needs this to tell the user whether the geometry
        closed; it is the same check that validated the FE mesh."""
        pv = preview(_make_dxf(), _opts())
        assert pv.external_area > 0
        assert abs(pv.region_area - pv.external_area) \
            / pv.external_area < 1e-4

    def test_open_boundary_is_closed_and_reported(self):
        pv = preview(_make_dxf(), _opts())
        assert pv.report.closed_boundaries == 1
        assert any(p["kind"] == "external_gap"
                   for p in pv.report.problems)

    def test_layer_zero_can_be_mapped(self):
        """An explicit requirement: a layer whose name matches nothing
        must still be assignable."""
        without = preview(_make_dxf(), _opts())
        withwt = preview(_make_dxf(),
                         _opts(layer_kinds={"0": K.WATER_TABLE}))
        assert "water_table" not in without.boundaries
        assert withwt.boundaries.get("water_table") == 1

    def test_user_mapping_overrides_the_proposal(self):
        """Mapping a recognised layer to something else must be honoured:
        the automatic guess is a proposal, not a decision."""
        pv = preview(_make_dxf(),
                     _opts(layer_kinds={"OGR_MATERIAL": K.IGNORE}))
        assert "material" not in pv.boundaries

    def test_no_mapping_at_all_is_an_error(self):
        pv = preview(_make_dxf(), _opts(layer_kinds={
            "OGR_EXTERNAL": K.IGNORE, "OGR_MATERIAL": K.IGNORE,
            "0": K.IGNORE}))
        assert not pv.ok
        assert "geometry type" in pv.error

    def test_missing_file_reports_cleanly(self):
        pv = preview("/tmp/definitely_absent.dxf", _opts())
        assert not pv.ok
        assert pv.error

    def test_simplification_reduces_vertices(self):
        plain = preview(_make_dxf(), _opts(simplify=False))
        simp = preview(_make_dxf(),
                       _opts(simplify=True, simplify_pct=0.1))
        assert simp.report.vertices_after <= plain.report.vertices_after

    def test_summary_is_human_readable(self):
        text = preview(_make_dxf(), _opts()).summary()
        assert "region" in text and "vertices" in text

    def test_units_change_the_scale(self):
        in_m = preview(_make_dxf(), _opts(unit="m"))
        in_mm = preview(_make_dxf(), _opts(unit="mm"))
        assert in_mm.external_area < in_m.external_area


# ======================================================================
@_requires(_HAS_EZDXF)
class TestApplyToProject:
    def test_boundaries_created(self):
        p = Project(name="dxf")
        pv, created = import_dxf(p, _make_dxf(),
                                 _opts(layer_kinds={"0": K.WATER_TABLE}))
        assert pv.ok
        assert created.get("EXTERNAL") == 1
        assert created.get("MATERIAL") == 2
        assert created.get("WATER_TABLE") == 1
        assert len(p.boundaries) == 4

    def test_import_matches_the_preview(self):
        """What is applied must be exactly what the preview reported."""
        opts = _opts(layer_kinds={"0": K.WATER_TABLE})
        pv = preview(_make_dxf(), opts)
        p = Project(name="dxf")
        created = apply_to_project(p, pv, opts)
        assert sum(created.values()) == sum(pv.boundaries.values())

    def test_replace_removes_only_the_imported_types(self):
        """A stale external boundary must not survive behind the new one,
        but boundaries of types the drawing does not define should."""
        from ogr_core.geometry import Boundary, Polyline, Vertex
        p = Project(name="dxf")
        p.add_boundary(Boundary(
            btype=BoundaryType.EXTERNAL,
            polyline=Polyline(vertices=[Vertex(0, 0), Vertex(1, 0),
                                        Vertex(1, 1), Vertex(0, 0)],
                              closed=True)))
        p.add_boundary(Boundary(
            btype=BoundaryType.TENSION_CRACK,
            polyline=Polyline(vertices=[Vertex(5, 5), Vertex(5, 6)],
                              closed=False)))
        import_dxf(p, _make_dxf(), _opts(replace_model=True))
        externals = [b for b in p.boundaries
                     if b.btype == BoundaryType.EXTERNAL]
        cracks = [b for b in p.boundaries
                  if b.btype == BoundaryType.TENSION_CRACK]
        assert len(externals) == 1          # the old one is gone
        assert len(cracks) == 1             # untouched

    def test_no_replace_keeps_existing(self):
        from ogr_core.geometry import Boundary, Polyline, Vertex
        p = Project(name="dxf")
        p.add_boundary(Boundary(
            btype=BoundaryType.EXTERNAL,
            polyline=Polyline(vertices=[Vertex(0, 0), Vertex(1, 0),
                                        Vertex(1, 1), Vertex(0, 0)],
                              closed=True)))
        import_dxf(p, _make_dxf(), _opts(replace_model=False))
        externals = [b for b in p.boundaries
                     if b.btype == BoundaryType.EXTERNAL]
        assert len(externals) == 2

    def test_failed_read_writes_nothing(self):
        """A broken file must not half-populate the model."""
        p = Project(name="dxf")
        before = len(p.boundaries)
        pv, created = import_dxf(p, "/tmp/absent.dxf", _opts())
        assert not pv.ok
        assert created == {}
        assert len(p.boundaries) == before

    def test_project_marked_dirty(self):
        p = Project(name="dxf")
        import_dxf(p, _make_dxf(), _opts())
        assert p.is_dirty is True

    def test_imported_geometry_builds_regions(self):
        """End to end: after importing, the model must define regions."""
        from ogr_core.geometry.regions import build_regions
        p = Project(name="dxf")
        import_dxf(p, _make_dxf(), _opts())
        ext = [b for b in p.boundaries
               if b.btype == BoundaryType.EXTERNAL][0]
        mats = [b for b in p.boundaries
                if b.btype == BoundaryType.MATERIAL]
        regions = build_regions(ext, mats)
        assert len(regions) >= 2


# ======================================================================
@_requires(_HAS_EZDXF and _QT)
class TestDialog:
    def _dlg(self):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.dialogs.dxf_import_dialog import DxfImportDialog
        return DxfImportDialog(str(_make_dxf()), None)

    def test_every_layer_gets_a_row_and_a_dropdown(self):
        d = self._dlg()
        assert d.table.rowCount() == 3
        for r in range(3):
            assert d.table.cellWidget(r, 3) is not None

    def test_recognised_layers_are_preselected(self):
        d = self._dlg()
        seen = {}
        for r in range(d.table.rowCount()):
            seen[d.table.item(r, 0).text()] = \
                d.table.cellWidget(r, 3).currentData()
        assert seen["OGR_EXTERNAL"] == K.EXTERNAL
        assert seen["OGR_MATERIAL"] == K.MATERIAL
        assert seen["0"] == K.IGNORE      # left to the user

    def test_dropdown_offers_every_geometry_type(self):
        d = self._dlg()
        cbo = d.table.cellWidget(0, 3)
        offered = {cbo.itemData(i) for i in range(cbo.count())}
        for kind in (K.IGNORE, K.EXTERNAL, K.MATERIAL, K.WATER_TABLE,
                     K.PIEZO, K.DRAWDOWN, K.TENSION_CRACK, K.SUPPORT):
            assert kind in offered, kind

    def test_unit_suggestion_is_shown_as_a_hint(self):
        d = self._dlg()
        assert d.cbo_unit.currentData() in ("m", "mm", "cm", "km",
                                            "ft", "in")
        assert "hint" in d.lbl_suggest.text().lower()

    def test_preview_reports_closure(self):
        d = self._dlg()
        d.sp_weld.setValue(0.5)
        d._preview()
        text = d.lbl_preview.text()
        assert "regions" in text
        assert "geometry closes" in text

    def test_preview_lists_problems_with_coordinates(self):
        d = self._dlg()
        d.sp_weld.setValue(0.5)
        d._preview()
        assert d.list_problems.count() >= 1
        from PySide6.QtCore import Qt
        found = False
        for i in range(d.list_problems.count()):
            data = d.list_problems.item(i).data(Qt.UserRole)
            if data and data[0] is not None:
                found = True
        assert found, "no problem carried coordinates"

    def test_simplify_checkbox_gates_its_tolerance(self):
        d = self._dlg()
        d.chk_simplify.setChecked(False)
        assert d.sp_simplify.isEnabled() is False
        d.chk_simplify.setChecked(True)
        assert d.sp_simplify.isEnabled() is True

    def test_collected_options_reflect_the_table(self):
        d = self._dlg()
        for r in range(d.table.rowCount()):
            if d.table.item(r, 0).text() == "0":
                cbo = d.table.cellWidget(r, 3)
                cbo.setCurrentIndex(cbo.findData(K.WATER_TABLE))
        opts = d._collect()
        assert opts.layer_kinds["0"] == K.WATER_TABLE

    def test_accept_recomputes_the_preview(self):
        """Options may have changed after the last Preview, so accepting
        must run the pipeline again rather than reuse a stale result."""
        d = self._dlg()
        d._preview()
        for r in range(d.table.rowCount()):
            if d.table.item(r, 0).text() == "0":
                cbo = d.table.cellWidget(r, 3)
                cbo.setCurrentIndex(cbo.findData(K.WATER_TABLE))
        d._accept()
        assert d.result_preview.boundaries.get("water_table") == 1

    def test_recommended_range_is_shown(self):
        d = self._dlg()
        # The recommended tolerance range must be visible somewhere
        from PySide6.QtWidgets import QLabel
        texts = " ".join(w.text() for w in d.findChildren(QLabel))
        assert "Recommended" in texts

    def test_menu_action_is_wired(self):
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        act = w._actions.get("import_dxf")
        assert act is not None
        # No longer the "planned for v0.2.0" stub
        src = Path(__file__).resolve().parent.parent / "ogr_gui" \
            / "main_window.py"
        assert "DXF import planned" not in src.read_text(encoding="utf-8")
