# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D444 (v0.1.508) — the three paths of the window that added boundaries
without the rule of their type ask the core's rule, as the agent does.

The invariant
-------------
Measured with 0.1.455 by the bench's
``_auditoria/P10_D443_D444/medir_d443_d444.py`` on the demo slope:

* Convert Tool to Boundary added a second water table, a second (open)
  External and a second tension crack, where the agent refused each;
* importing a DXF without Replace wrote a second External, which the region
  builder never reads, where the agent refused it;
* Convert Boundary made a polyline that crosses itself a piezometric line or
  a weak layer, where the agent refused it.

Now the window asks OGR Core 0.2.14's rules -- ``boundary_refusal`` with the
polyline, ``import_refusal`` before writing (the owner's decision: the WHOLE
import is refused) and ``conversion_refusal``, which asks the geometry of the
converted polyline -- and the status bar gives the reason; the model is left
as it was. The controls: a material boundary is added, and an import with
Replace is written. The agent asks the same rules (its own two checks are
gone) and says the same sentences; a second water table in a DXF, which it
let through, is refused too.

The cost: one MainWindow for the file, a DXF of one polyline per case.
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_W: list = []
_BOW = [(10, 2), (20, 6), (20, 2), (10, 6)]       # crosses itself


def _window():
    if not _W:
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w.PROMPT_ASSIGN_ON_DRAW = False
        # kept to the end of the process, as every MainWindow of the suite is
        _W.append(w)
    return _W[0]


def _attach(p):
    w = _window()
    w._attach_project(p)
    w.command_stack.clear()
    w.statusBar().clearMessage()
    w.ogr_status.clearMessage()
    return w


def _demo_with_annotation(points):
    from ogr_core.annotations import Annotation, AnnotationKind
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    a = p.annotations.add(Annotation(kind=AnnotationKind.POLYLINE,
                                     points=list(points)))
    return p, a


def _kinds(p):
    return [b.btype.name for b in p.boundaries]


def _dxf(tmp, layers):
    """A DXF with one closed or open polyline per layer: {layer: (pts,
    closed)}."""
    import ezdxf
    path = os.path.join(tmp, "d444.dxf")
    doc = ezdxf.new()
    for layer, (pts, closed) in layers.items():
        doc.modelspace().add_lwpolyline(pts, close=closed,
                                        dxfattribs={"layer": layer})
    doc.saveas(path)
    return path


_GROUND = ([(0, 0), (60, 0), (60, 20), (0, 30)], True)
_WATER = ([(0, 15), (60, 12)], False)


class TestConvertToolToBoundary:

    def _convert(self, btype, points=((0, 12), (25, 11), (50, 10))):
        p, a = _demo_with_annotation(points)
        w = _attach(p)
        before = _kinds(w.project)
        added = w._convert_annotation(a, btype, btype.display_name)
        return w, before, added

    def test_a_second_water_table_is_refused_and_said(self):
        from ogr_core.geometry import BoundaryType as BT
        w, before, added = self._convert(BT.WATER_TABLE)
        assert not added and _kinds(w.project) == before
        msg = w.statusBar().currentMessage()
        assert msg.startswith("Only one Water Table is allowed."), msg
        assert msg.endswith("The boundary was not added."), msg

    def test_a_second_external_is_refused(self):
        from ogr_core.geometry import BoundaryType as BT
        w, before, added = self._convert(BT.EXTERNAL)
        assert not added and _kinds(w.project) == before
        assert "External" in w.statusBar().currentMessage()

    def test_a_polyline_that_crosses_itself_is_refused(self):
        from ogr_core.geometry import BoundaryType as BT
        w, before, added = self._convert(BT.MATERIAL, _BOW)
        assert not added and _kinds(w.project) == before
        assert w.statusBar().currentMessage().startswith(
            "The edit makes the boundary cross itself."), \
            w.statusBar().currentMessage()

    def test_the_control_a_material_boundary_is_added(self):
        from ogr_core.geometry import BoundaryType as BT
        w, before, added = self._convert(BT.MATERIAL)
        assert added and _kinds(w.project) == before + ["MATERIAL"]


class TestImportDxfWithoutReplace:

    def _import(self, layers, kinds, replace):
        from ogr_core.dxf.importer import ImportOptions, preview
        from ogr_core.project.demo import build_demo_project
        w = _attach(build_demo_project())
        before = _kinds(w.project)
        with tempfile.TemporaryDirectory() as tmp:
            opts = ImportOptions(replace_model=replace, layer_kinds=kinds)
            pv = preview(_dxf(tmp, layers), opts)
            written = w._apply_dxf_import(pv, opts)
        return w, before, written

    def test_a_second_external_writes_nothing_and_says_why(self):
        from ogr_core.dxf.reader import DxfEntityKind as K
        w, before, written = self._import({"TERRENO": _GROUND},
                                          {"TERRENO": K.EXTERNAL}, False)
        assert not written and _kinds(w.project) == before
        msg = w.statusBar().currentMessage()
        assert msg.startswith("The import leaves two External boundaries. "
                              "Nothing was imported."), msg

    def test_a_second_water_table_too(self):
        from ogr_core.dxf.reader import DxfEntityKind as K
        w, before, written = self._import({"AGUA": _WATER},
                                          {"AGUA": K.WATER_TABLE}, False)
        assert not written and _kinds(w.project) == before
        assert w.statusBar().currentMessage().startswith(
            "The import leaves two Water Tables.")

    def test_the_control_with_replace_it_is_written(self):
        from ogr_core.dxf.reader import DxfEntityKind as K
        w, _before, written = self._import({"TERRENO": _GROUND},
                                           {"TERRENO": K.EXTERNAL}, True)
        assert written
        assert _kinds(w.project).count("EXTERNAL") == 1


class TestConvertBoundaryOfACrossingPolyline:

    def test_the_window_refuses_it(self):
        from ogr_core.geometry import Boundary, BoundaryType as BT
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        bow = Boundary(btype=BT.MATERIAL, polyline=Polyline(
            [Vertex(x, y) for x, y in _BOW]))
        p.add_boundary(bow)
        w = _attach(p)
        w._apply_conversion(bow, BT.WEAK_LAYER)
        got = next(b for b in w.project.boundaries if b.id == bow.id)
        assert got.btype == BT.MATERIAL
        assert w.ogr_status.currentMessage().startswith(
            "The edit makes the boundary cross itself.")


class TestTheAgentAsksTheSameRules:

    def _call(self, p, name, **kw):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            h = ws.add(p)
            try:
                return call(ws, name, project_id=h.id, **kw), h.project
            except Exception as exc:  # noqa: BLE001
                return str(exc), h.project
        finally:
            ws.shutdown()

    def test_its_import_refusals_with_their_advice(self):
        from ogr_core.project.demo import build_demo_project
        with tempfile.TemporaryDirectory() as tmp:
            path = _dxf(tmp, {"AGUA": _WATER})
            out, p = self._call(build_demo_project(), "dxf_import",
                                path=path, replace_model=False,
                                layer_kinds={"AGUA": "water_table"})
        assert "The import leaves two Water Tables." in out, out
        assert "map only one layer to 'water_table'" in out, out
        assert _kinds(p).count("WATER_TABLE") == 1

    def test_the_crossing_conversion_says_the_same_sentence(self):
        from ogr_core.geometry import Boundary, BoundaryType as BT
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        bow = Boundary(btype=BT.MATERIAL, polyline=Polyline(
            [Vertex(x, y) for x, y in _BOW]))
        p.add_boundary(bow)
        out, q = self._call(p, "boundary_edit", boundary=bow.id,
                            op="change_type", new_type="weak_layer")
        assert "The edit makes the boundary cross itself." in out, out
        assert next(b for b in q.boundaries
                    if b.id == bow.id).btype == BT.MATERIAL


class TestInSpanish:

    def test_every_new_sentence_has_its_spanish(self):
        from ogr_core.project.rules import IMPORT_TWO, SELF_INTERSECTING
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for en in [SELF_INTERSECTING, *IMPORT_TWO.values(),
                   "Nothing was imported. Tick «Replace existing boundaries "
                   "of the imported types», or map only one layer to {0}."]:
            assert en in es and es[en] != en, en
