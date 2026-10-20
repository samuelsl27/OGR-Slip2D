# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.337 — the annotation layer in the DXF export, as native entities; and
the import dialog offers every geometry kind (D333).

Until this version ``export_dxf`` never read ``project.annotations``: what
the user drew stayed out of the drawing. It is written now on a layer of its
own, ``OGR_X_DRAWING``, with a box of its own in the dialog, the API and the
MCP (decision of the owner), from the primitives of
``ogr_core.annotations.drawing`` — the geometry the canvas draws, which the
canvas now draws from too.

The invariants:

* each kind becomes the entity a CAD program has for it: LWPOLYLINE (with a
  HATCH for a fill), a SOLID arrow head, TEXT, DIMENSION, an IMAGE linked
  to its file;
* **a DIMENSION measures what the annotation measures** — the CAD program's
  own ``get_measurement()`` times the drawing's unit equals
  ``measured_value()`` (the reference is the geometry, rule 1), in metres
  and in millimetres; and an angle the same whichever way its arms were
  picked (ezdxf measures counter-clockwise from the first to the second);
* the axes carry the coordinates the canvas writes, and the line-type scale
  follows the model, not the unit;
* the image's size in pixels is read from its header, as Qt reads it, for
  PNG, JPEG and BMP; one that cannot be read is its frame, and said;
* the box moves the output (rule 7); the layer is proposed as "ignore" on
  re-import, and re-importing makes no boundary of it;
* the canvas draws what it drew before (``test_annotations_drawn_v1330``
  runs unchanged against the new adapter);
* D333: the import dialog's kinds cover every kind the reader proposes, and
  a model's weak layer and anisotropic surface come back with their
  vertices. Until now ``findData`` gave -1 and the row fell to "(ignore)".
"""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import ezdxf
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


LAYER = "OGR_X_DRAWING"


def _project(*annotations):
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    for a in annotations:
        p.annotations.add(a)
    return p


def _ann(kind, points, text="", **style):
    from ogr_core.annotations import Annotation, AnnotationStyle
    return Annotation(kind=kind, points=points, text=text,
                      style=AnnotationStyle(**style))


def _export(project, unit="m", **options):
    from ogr_core.dxf.exporter import ExportOptions, export_dxf
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / ("a_%s.dxf" % unit)
    rep = export_dxf(project, path, ExportOptions(unit=unit, **options))
    assert rep.ok, rep.error
    return ezdxf.readfile(str(path)), rep, path


def _types(doc):
    out = {}
    for e in doc.modelspace().query('*[layer=="%s"]' % LAYER):
        out[e.dxftype()] = out.get(e.dxftype(), 0) + 1
    return out


def _kinds():
    from ogr_core.annotations import AnnotationKind as K
    return K


# ======================================================================
@_requires(_HAS_EZDXF)
class TestEachKindIsItsEntity:

    def test_the_entity_of_each_kind(self):
        K = _kinds()
        cases = [
            (K.LINE, [(1, 1), (10, 2)], {}, {"LWPOLYLINE"}),
            (K.POLYLINE, [(1, 1), (5, 4), (10, 2)], {}, {"LWPOLYLINE"}),
            (K.POLYGON, [(30, 30), (40, 30), (35, 35)], {"fill": "#ff0000"},
             {"LWPOLYLINE", "HATCH"}),
            (K.RECTANGLE, [(42, 28), (48, 32)], {}, {"LWPOLYLINE"}),
            (K.CIRCLE, [(5, 40), (8, 40)], {}, {"LWPOLYLINE"}),
            (K.ARROW, [(2, 30), (10, 28)], {}, {"LWPOLYLINE", "SOLID"}),
            (K.DIMENSION_LENGTH, [(0, 0), (50, 0)], {}, {"DIMENSION"}),
            (K.DIMENSION_X, [(25, 25), (35, 15)], {}, {"DIMENSION"}),
            (K.DIMENSION_Y, [(50, 0), (50, 15)], {}, {"DIMENSION"}),
            (K.DIMENSION_ANGLE, [(35, 15), (25, 25), (0, 25)], {},
             {"DIMENSION"}),
            (K.AXES, [(0, 0), (50, 25)], {}, {"LWPOLYLINE", "LINE", "TEXT"}),
        ]
        for kind, pts, style, want in cases:
            doc, _rep, _p = _export(_project(_ann(kind, pts, **style)))
            assert set(_types(doc)) == want, (kind, _types(doc))
        doc, _rep, _p = _export(_project(_ann(K.TEXT, [(10, 35)], "nota")))
        texts = [e.dxf.text for e in doc.modelspace().query("TEXT")
                 if e.dxf.layer == LAYER]
        assert texts == ["nota"]

    def test_each_entity_carries_its_colour(self):
        K = _kinds()
        doc, _rep, _p = _export(_project(_ann(K.LINE, [(1, 1), (10, 2)],
                                              colour="#12ab34")))
        line = next(iter(doc.modelspace().query('LWPOLYLINE[layer=="%s"]'
                                                % LAYER)))
        assert line.rgb == (0x12, 0xab, 0x34)

    def test_a_hidden_annotation_is_not_written(self):
        K = _kinds()
        doc, rep, _p = _export(_project(_ann(K.LINE, [(1, 1), (10, 2)],
                                             visible=False)))
        assert _types(doc) == {} and LAYER not in rep.entities


@_requires(_HAS_EZDXF)
class TestADimensionMeasuresWhatTheAnnotationMeasures:

    def _dims(self, annotation, unit):
        from ogr_core.dxf.reader import UNIT_FACTORS
        doc, _rep, _p = _export(_project(annotation), unit=unit)
        dims = [e for e in doc.modelspace().query("DIMENSION")
                if e.dxf.layer == LAYER]
        assert len(dims) == 1
        return dims[0].get_measurement(), UNIT_FACTORS[unit]

    def test_lengths_in_metres_and_in_millimetres(self):
        K = _kinds()
        for kind, pts in ((K.DIMENSION_LENGTH, [(3, 4), (33, 44)]),
                          (K.DIMENSION_X, [(25, 25), (35.5, 15)]),
                          (K.DIMENSION_Y, [(50, 0.25), (40, 15)])):
            a = _ann(kind, pts)
            for unit in ("m", "mm"):
                measured, factor = self._dims(a, unit)
                assert abs(measured * factor - a.measured_value()) \
                    < 1e-9 * a.measured_value(), (kind, unit, measured)

    def test_an_angle_whichever_way_it_was_picked(self):
        K = _kinds()
        for pts in ([(35, 15), (25, 25), (0, 25)],
                    [(0, 25), (25, 25), (35, 15)]):
            a = _ann(K.DIMENSION_ANGLE, pts)
            measured, _f = self._dims(a, "m")
            assert abs(measured - a.measured_value()) < 1e-9, (pts, measured)
            assert abs(a.measured_value() - 135.0) < 1e-9

    def test_the_decimals_keep_the_millimetre(self):
        from ogr_core.dxf.annotation_export import dimension_decimals
        from ogr_core.dxf.reader import UNIT_FACTORS
        want = {"m": 3, "cm": 1, "mm": 0, "km": 6, "ft": 3, "in": 2}
        assert {u: dimension_decimals(UNIT_FACTORS[u]) for u in want} == want


@_requires(_HAS_EZDXF and _QT)
class TestTheAxesAreTheCanvasAxes:

    def test_the_coordinates_are_the_canvas_coordinates(self):
        from PySide6.QtWidgets import QApplication, QGraphicsSimpleTextItem
        from ogr_gui.canvas.annotation_items import annotation_items
        QApplication.instance() or QApplication([])
        K = _kinds()
        a = _ann(K.AXES, [(0, 0), (50, 25)])
        canvas = sorted(it.text() for it in annotation_items(a)
                        if isinstance(it, QGraphicsSimpleTextItem))
        doc, _rep, _p = _export(_project(a))
        written = sorted(e.dxf.text for e in doc.modelspace().query("TEXT")
                         if e.dxf.layer == LAYER)
        assert written == canvas and len(canvas) >= 8, (written, canvas)

    def test_the_line_type_scale_follows_the_model(self):
        from ogr_core.dxf.reader import UNIT_FACTORS
        K = _kinds()
        p = _project(_ann(K.LINE, [(1, 1), (10, 2)], line_style="dash"))
        ratios = []
        for unit in ("m", "mm"):
            doc, _rep, _p = _export(p, unit=unit)
            ratios.append(doc.header["$LTSCALE"] * UNIT_FACTORS[unit])
        assert abs(ratios[0] - ratios[1]) < 1e-9 * ratios[0]


@_requires(_HAS_EZDXF and _QT)
class TestTheImage:

    def _write(self, folder, fmt):
        from PySide6.QtGui import QImage
        img = QImage(37, 19, QImage.Format_RGB32)
        img.fill(0xff336699)
        path = str(Path(folder) / ("pic." + fmt))
        assert img.save(path, fmt.upper())
        return path

    def test_its_size_is_read_as_qt_reads_it(self):
        from PySide6.QtGui import QImageReader
        from ogr_core.annotations.image_size import pixel_size
        with tempfile.TemporaryDirectory() as tmp:
            for fmt in ("png", "jpg", "bmp"):
                path = self._write(tmp, fmt)
                size = QImageReader(path).size()
                assert pixel_size(path) == (size.width(), size.height()), fmt

    def test_it_is_an_image_entity_under_the_model(self):
        K = _kinds()
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "png")
            doc, rep, _p = _export(_project(_ann(K.IMAGE, [(0, 0), (10, 5)],
                                                 path)), unit="mm")
            images = list(doc.modelspace().query("IMAGE"))
            assert len(images) == 1
            img = images[0]
            assert img.image_def.dxf.filename == path
            assert tuple(img.image_def.dxf.image_size)[:2] == (37, 19)
            order = [e.dxftype() + ":" + e.dxf.layer
                     for e in doc.modelspace()]
            assert order.index("IMAGE:" + LAYER) < order.index(
                "LWPOLYLINE:OGR_EXTERNAL")

    def test_a_missing_file_is_its_frame_and_said(self):
        K = _kinds()
        doc, rep, _p = _export(_project(_ann(K.IMAGE, [(0, 0), (10, 5)],
                                             "C:/no/such/picture.png")))
        assert set(_types(doc)) == {"LWPOLYLINE", "TEXT"}
        assert any("picture.png" in s for s in rep.skipped), rep.skipped


@_requires(_HAS_EZDXF)
class TestTheBoxAndTheLayer:

    def test_the_box_moves_the_output(self):
        K = _kinds()
        p = _project(_ann(K.LINE, [(1, 1), (10, 2)]))
        on, rep_on, _p = _export(p)
        off, rep_off, _p = _export(p, annotation_layer=False)
        assert _types(on) and not _types(off)
        # the labels box is another thing: the title is still there
        assert rep_off.entities.get("OGR_X_ANNOTATION")

    def test_the_layer_is_ignored_on_reimport(self):
        from ogr_core.dxf import ImportOptions, preview
        from ogr_core.dxf.reader import DxfEntityKind, guess_kind
        K = _kinds()
        assert guess_kind(LAYER) == DxfEntityKind.IGNORE
        p = _project(_ann(K.POLYGON, [(30, 30), (40, 30), (35, 35)]),
                     _ann(K.DIMENSION_LENGTH, [(0, 0), (50, 0)]))
        _doc, _rep, path = _export(p)
        pv = preview(path, ImportOptions(unit="m"))
        assert pv.ok, pv.error
        lay = next(x for x in pv.catalogue.layers if x.name == LAYER)
        assert lay.proposed_kind == DxfEntityKind.IGNORE
        assert sum(pv.boundaries.values()) == len(p.boundaries)

    def test_the_api_and_the_mcp_take_the_box(self):
        import inspect
        from ogr_api.ops.files import dxf_export
        params = inspect.signature(dxf_export).parameters
        assert params["annotation_layer"].default is True
        src = (Path(__file__).resolve().parents[1] / "ogr_mcp"
               / "server.py").read_text(encoding="utf-8")
        assert "annotation_layer=annotation_layer" in src


@_requires(_HAS_EZDXF and _QT)
class TestTheExportDialog:

    def test_the_box_says_why_when_there_is_nothing(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.dxf_export_dialog import DxfExportDialog
        QApplication.instance() or QApplication([])
        K = _kinds()
        empty = DxfExportDialog(_project())
        assert not empty.chk_annotation_layer.isEnabled()
        assert empty.chk_annotation_layer.toolTip()
        assert empty._collect().annotation_layer is False
        full = DxfExportDialog(_project(_ann(K.LINE, [(1, 1), (10, 2)])))
        assert full.chk_annotation_layer.isEnabled()
        full.chk_annotation_layer.setChecked(False)
        assert full._collect().annotation_layer is False
        full.chk_annotation_layer.setChecked(True)
        assert full._collect().annotation_layer is True


@_requires(_HAS_EZDXF)
class TestAFarAnnotationDoesNotLoosenTheReimport:
    """The sanitiser's tolerances are a percentage of the drawing's
    diagonal, and the catalogue measured it over EVERY layer. Measured while
    this was written: an annotation line to (1000, 1000) took the demo's
    diagonal from 55.9 to 1414, and a material end 2 or 5 m short of the
    External, reported dangling without it, was extended to the External
    with no warning. The exporter's own read-only layers (OGR_X_) no longer
    count (decision of the owner); a third party's layers still do."""

    def _reimport(self, gap, far):
        from ogr_core.dxf import ImportOptions, preview, read_dxf
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        K = _kinds()
        p = _project()
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(0.0, 12.0), Vertex(50.0 - gap, 12.0)]),
            btype=BoundaryType.MATERIAL))
        if far:
            p.annotations.add(_ann(K.LINE, [(0, 0), (far, far)]))
        _doc, _rep, path = _export(p)
        pv = preview(path, ImportOptions(unit="m"))
        kinds = [q["kind"] for q in pv.report.problems]
        return read_dxf(path).diagonal(), kinds

    def test_the_diagonal_is_the_model_s(self):
        d0, _k = self._reimport(5.0, 0)
        d1, _k = self._reimport(5.0, 1000.0)
        assert abs(d1 - d0) < 1e-9 * d0, (d0, d1)

    def test_a_short_end_is_still_reported(self):
        for gap in (2.0, 5.0):
            _d, without = self._reimport(gap, 0)
            _d, with_far = self._reimport(gap, 1000.0)
            assert "dangling_end" in without, (gap, without)
            assert with_far == without, (gap, with_far, without)

    def test_a_drawing_of_only_export_layers_still_has_a_size(self):
        from ogr_core.dxf.reader import (DxfCatalogue, DxfLayerInfo,
                                         DxfPolyline)
        cat = DxfCatalogue(unit_factor=1.0)
        cat.layers.append(DxfLayerInfo(name="OGR_X_DRAWING", polylines=[
            DxfPolyline(points=[(0.0, 0.0), (3.0, 4.0)])]))
        assert abs(cat.diagonal() - 5.0) < 1e-12


# ======================================================================
def _with_weak_and_aniso():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    p = _project()
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, 10), Vertex(50, 9)]), btype=BoundaryType.WEAK_LAYER))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, 5), Vertex(20, 6), Vertex(50, 4)]),
        btype=BoundaryType.ANISOTROPIC_SURFACE))
    return p


@_requires(_HAS_EZDXF and _QT)
class TestTheImportDialogOffersEveryKind:

    def test_its_kinds_are_the_readers_kinds(self):
        from ogr_core.dxf.reader import DxfEntityKind
        from ogr_gui.dialogs import dxf_import_dialog as dlg
        assert {k for k, _label in dlg._KIND_LABELS} == set(DxfEntityKind)

    def test_a_weak_layer_and_an_anisotropic_surface_come_back(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.dxf import apply_to_project, preview
        from ogr_core.dxf.reader import DxfEntityKind as K
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project
        from ogr_gui.dialogs.dxf_import_dialog import DxfImportDialog
        QApplication.instance() or QApplication([])
        p = _with_weak_and_aniso()
        _doc, _rep, path = _export(p)
        d = DxfImportDialog(path)
        try:
            proposed = {}
            for r in range(d.table.rowCount()):
                proposed[d.table.item(r, 0).text()] = \
                    d.table.cellWidget(r, 3).currentData()
            opts = d._collect()
        finally:
            d.deleteLater()
        assert proposed["OGR_WEAK_LAYER"] == K.WEAK_LAYER, proposed
        assert proposed["OGR_ANISO_SURFACE"] == K.ANISOTROPIC_SURFACE
        back = Project("back")
        apply_to_project(back, preview(path, opts), opts)
        for btype in (BoundaryType.WEAK_LAYER,
                      BoundaryType.ANISOTROPIC_SURFACE):
            want = [[(v.x, v.y) for v in b.polyline.vertices]
                    for b in p.boundaries if b.btype == btype]
            got = [[(v.x, v.y) for v in b.polyline.vertices]
                   for b in back.boundaries if b.btype == btype]
            assert len(got) == len(want) == 1, btype
            assert all(math.dist(a, b) < 1e-6
                       for a, b in zip(got[0], want[0])), (got, want)
