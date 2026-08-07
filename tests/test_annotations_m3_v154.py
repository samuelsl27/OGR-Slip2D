# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.54 — Annotation layer and Tools menu (phase M3).

The defining property, and the one most worth protecting, is
**isolation**: annotations live in ``Project.annotations``, a list the
solver never reads. A rectangle sketched to mark a zone of interest
cannot be mistaken for a material boundary, and no analysis result can
change because someone drew on the model.

The **only** bridge is ``to_boundary_points``, used by *Convert Tool to
Boundary*: explicit, one-way and user-initiated.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.annotations import (  # noqa: E402
    CONVERTIBLE_KINDS,
    Annotation,
    AnnotationKind as K,
    AnnotationLayer,
    AnnotationStyle,
    to_boundary_points,
)
from ogr_core.project import Project  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []


# ======================================================================
class TestShapes:
    def test_rectangle_expands_to_five_points(self):
        """Stored by two corners — what the user manipulates — expanded
        so everything downstream sees one representation."""
        a = Annotation(kind=K.RECTANGLE, points=[(0, 0), (10, 5)])
        out = a.outline()
        assert len(out) == 5
        assert out[0] == out[-1]
        assert abs(a.length() - 30.0) < 1e-9

    def test_circle_perimeter_approaches_the_exact_value(self):
        a = Annotation(kind=K.CIRCLE, points=[(20, 20), (25, 20)])
        assert abs(a.length() - 2 * math.pi * 5) / (2 * math.pi * 5) < 0.01

    def test_polygon_closes_itself(self):
        a = Annotation(kind=K.POLYGON, points=[(0, 0), (10, 0), (5, 8)])
        assert a.outline()[-1] == a.outline()[0]
        assert a.closed is True

    def test_open_shapes_are_not_closed(self):
        for kind in (K.LINE, K.ARROW, K.POLYLINE, K.TEXT):
            assert Annotation(kind=kind,
                              points=[(0, 0), (1, 1)]).closed is False

    def test_bbox_and_translate(self):
        a = Annotation(kind=K.RECTANGLE, points=[(0, 0), (10, 5)])
        assert a.bbox() == (0, 0, 10, 5)
        a.translate(2.0, 3.0)
        assert a.bbox() == (2, 3, 12, 8)


class TestDimensions:
    def test_length(self):
        a = Annotation(kind=K.DIMENSION_LENGTH,
                       points=[(0, 0), (3, 4)])
        assert abs(a.measured_value() - 5.0) < 1e-12

    def test_x_and_y_projections(self):
        pts = [(1, 2), (7, 10)]
        assert abs(Annotation(kind=K.DIMENSION_X, points=pts
                              ).measured_value() - 6.0) < 1e-12
        assert abs(Annotation(kind=K.DIMENSION_Y, points=pts
                              ).measured_value() - 8.0) < 1e-12

    def test_angle_is_measured_at_the_middle_point(self):
        """The vertex the user picked second — the convention every CAD
        program uses."""
        a = Annotation(kind=K.DIMENSION_ANGLE,
                       points=[(10, 0), (0, 0), (0, 10)])
        assert abs(a.measured_value() - 90.0) < 1e-9

    def test_degenerate_angle_returns_none(self):
        a = Annotation(kind=K.DIMENSION_ANGLE,
                       points=[(0, 0), (0, 0), (1, 1)])
        assert a.measured_value() is None

    def test_non_dimensions_measure_nothing(self):
        assert Annotation(kind=K.RECTANGLE,
                          points=[(0, 0), (1, 1)]).measured_value() is None


class TestIsolationFromTheModel:
    def test_annotations_are_not_boundaries(self):
        """The property the whole layer exists for."""
        p = Project(name="x")
        p.annotations.add(Annotation(kind=K.RECTANGLE,
                                     points=[(0, 0), (10, 5)]))
        p.annotations.add(Annotation(kind=K.CIRCLE,
                                     points=[(3, 3), (4, 3)]))
        assert len(p.annotations) == 2
        assert len(p.boundaries) == 0

    def test_annotations_survive_serialisation_separately(self):
        p = Project(name="x")
        p.annotations.add(Annotation(kind=K.TEXT, points=[(1, 2)],
                                     text="note"))
        p2 = Project.from_dict(p.to_dict())
        assert len(p2.annotations) == 1
        assert p2.annotations.ordered()[0].text == "note"
        assert len(p2.boundaries) == 0

    def test_a_project_without_annotations_loads(self):
        p2 = Project.from_dict(Project(name="x").to_dict())
        assert len(p2.annotations) == 0


class TestConversionBridge:
    def test_convertible_kinds(self):
        assert CONVERTIBLE_KINDS == {K.LINE, K.POLYLINE, K.POLYGON,
                                     K.RECTANGLE, K.CIRCLE}

    def test_dimensions_and_text_cannot_convert(self):
        """They annotate geometry; they are not geometry, and converting
        them would produce nonsense."""
        for kind in (K.TEXT, K.DIMENSION_LENGTH, K.DIMENSION_ANGLE,
                     K.DIMENSION_X, K.DIMENSION_Y, K.AXES, K.IMAGE):
            a = Annotation(kind=kind, points=[(0, 0), (1, 1), (2, 2)])
            assert a.convertible is False, kind
            assert to_boundary_points(a) is None, kind

    def test_rectangle_converts_to_a_closed_outline(self):
        a = Annotation(kind=K.RECTANGLE, points=[(0, 0), (10, 5)])
        pts = to_boundary_points(a)
        assert pts is not None
        assert len(pts) == 5
        assert pts[0] == pts[-1]

    def test_duplicate_points_are_dropped(self):
        """They carry no shape and would produce zero-length segments in
        the model."""
        a = Annotation(kind=K.POLYLINE,
                       points=[(0, 0), (0, 0), (5, 0), (5, 0), (10, 0)])
        assert len(to_boundary_points(a)) == 3

    def test_degenerate_shape_does_not_convert(self):
        a = Annotation(kind=K.LINE, points=[(3, 3), (3, 3)])
        assert to_boundary_points(a) is None

    def test_conversion_is_one_way(self):
        """The module offers no reverse bridge: geometry never turns
        itself back into an annotation behind the user's back."""
        import ogr_core.annotations as mod
        assert not any("from_boundary" in n or "to_annotation" in n
                       for n in dir(mod))


class TestLayerOperations:
    def _layer(self):
        L = AnnotationLayer()
        a = L.add(Annotation(kind=K.LINE, points=[(0, 0), (1, 1)]))
        b = L.add(Annotation(kind=K.CIRCLE, points=[(5, 5), (6, 5)]))
        return L, a, b

    def test_z_order_increments_on_add(self):
        _L, a, b = self._layer()
        assert b.z_order > a.z_order

    def test_ordered_puts_lowest_first(self):
        """Later items must paint on top."""
        L, a, b = self._layer()
        assert L.ordered() == [a, b]
        L.send_to_back(b.id)
        assert L.ordered()[0] is b

    def test_bring_to_front(self):
        L, a, b = self._layer()
        L.bring_to_front(a.id)
        assert L.ordered()[-1] is a

    def test_remove_and_get(self):
        L, a, _b = self._layer()
        assert L.get(a.id) is a
        assert L.remove(a.id) is True
        assert L.get(a.id) is None
        assert L.remove("nope") is False

    def test_visibility_in_bulk(self):
        L, _a, _b = self._layer()
        L.set_all_visible(False)
        assert L.visible_items() == []
        L.set_all_visible(True)
        assert len(L.visible_items()) == 2

    def test_duplicate_offsets_and_gets_a_new_id(self):
        L, a, _b = self._layer()
        clone = L.duplicate(a.id, 5.0, 0.0)
        assert clone.id != a.id
        assert clone.points[0] == (a.points[0][0] + 5.0, a.points[0][1])
        assert len(L) == 3

    def test_copy_style(self):
        L, a, b = self._layer()
        a.style = AnnotationStyle(colour="#ff0000", line_width=3.0)
        assert L.copy_style(a.id, [b.id]) == 1
        assert b.style.colour == "#ff0000"
        assert b.style is not a.style      # a copy, not a shared object

    def test_clear(self):
        L, _a, _b = self._layer()
        L.clear()
        assert len(L) == 0

    def test_round_trip(self):
        L, a, _b = self._layer()
        a.style.colour = "#00ff00"
        L2 = AnnotationLayer.from_list(L.to_list())
        assert len(L2) == 2
        assert L2.get(a.id).style.colour == "#00ff00"


# ======================================================================
@_requires_qt
class TestToolsMenu:
    def _window(self):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language("en")
        p = _ej1_project()
        w = MainWindow()
        w.canvas.set_project(p)
        w.project = p
        _WINDOWS.append(w)
        return p, w

    def _tools_texts(self, w):
        out = []
        for act in w.menuBar().actions():
            if act.menu() is None or act.text() != "Tools":
                continue
            for entry in act.menu().actions():
                sub = entry.menu()
                if sub is not None:
                    out.extend(x.text() for x in sub.actions() if x.text())
                elif entry.text():
                    out.append(entry.text())
        return out

    def test_all_primitives_present(self):
        _p, w = self._window()
        texts = self._tools_texts(w)
        for name in ("Line", "Arrow", "Polyline", "Polygon", "Rectangle",
                     "Circle", "Add Text"):
            assert name in texts, name

    def test_dimensions_present(self):
        _p, w = self._window()
        texts = self._tools_texts(w)
        for name in ("Dimension Length", "Dimension Angle",
                     "Dimension X", "Dimension Y"):
            assert name in texts, name

    def test_property_tables_present(self):
        _p, w = self._window()
        texts = self._tools_texts(w)
        for name in ("Material Properties Table",
                     "Support Properties Table",
                     "Hydraulic Properties Table"):
            assert name in texts, name

    def test_conversion_and_management_present(self):
        _p, w = self._window()
        texts = self._tools_texts(w)
        assert any("Convert Tool to Boundary" in t for t in texts)
        for name in ("Manage Annotations...", "Show All Annotations",
                     "Hide All Annotations", "Delete All Annotations"):
            assert name in texts, name

    def test_axes_and_image(self):
        _p, w = self._window()
        texts = self._tools_texts(w)
        assert "Add Axes" in texts
        assert "Add Image..." in texts

    def test_bulk_visibility_from_the_window(self):
        p, w = self._window()
        p.annotations.add(Annotation(kind=K.LINE, points=[(0, 0), (1, 1)]))
        w._set_annotations_visible(False)
        assert p.annotations.visible_items() == []
        w._set_annotations_visible(True)
        assert len(p.annotations.visible_items()) == 1


@_requires_qt
class TestPropertyTables:
    def _dlg(self, what):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_gui.dialogs.properties_table_dialog import (
            PropertiesTableDialog,
        )
        from ogr_gui.i18n import set_language
        QApplication.instance() or QApplication([])
        set_language("en")
        p = _ej1_project()
        return p, PropertiesTableDialog(p, what, None)

    def test_materials_table_has_a_row_per_material(self):
        p, d = self._dlg("materials")
        assert d.is_empty is False
        assert d.table.rowCount() == len(p.materials)

    def test_materials_table_is_read_only(self):
        """Editing lives in the dedicated dialogs, where the validation
        is; a second editing path is a second place to forget it."""
        from PySide6.QtWidgets import QTableWidget
        _p, d = self._dlg("materials")
        assert d.table.editTriggers() == QTableWidget.NoEditTriggers

    def test_materials_table_is_sortable(self):
        """Comparison is what a table is for."""
        _p, d = self._dlg("materials")
        assert d.table.isSortingEnabled() is True

    def test_columns_union_every_strength_parameter(self):
        """Materials with different strength models must still line up
        in one comparable grid."""
        _p, d = self._dlg("materials")
        headers = [d.table.horizontalHeaderItem(c).text()
                   for c in range(d.table.columnCount())]
        assert "cohesion" in headers
        assert "friction angle" in headers

    def test_empty_tables_explain_themselves(self):
        _p, d = self._dlg("supports")
        assert d.is_empty is True
        assert "support" in d.empty_message.lower()
        _p2, d2 = self._dlg("hydraulic")
        assert d2.is_empty is True
        assert "hydraulic" in d2.empty_message.lower()

    def test_text_export_is_tab_separated(self):
        _p, d = self._dlg("materials")
        text = d.as_text()
        assert "\t" in text
        assert len(text.split("\n")) == d.table.rowCount() + 1


@_requires_qt
class TestAnnotationsDialog:
    def _dlg(self):
        from ogr_gui.dialogs.annotations_dialog import AnnotationsDialog
        from ogr_gui.i18n import set_language
        QApplication.instance() or QApplication([])
        set_language("en")
        L = AnnotationLayer()
        L.add(Annotation(kind=K.LINE, points=[(0, 0), (1, 1)]))
        L.add(Annotation(kind=K.RECTANGLE, points=[(0, 0), (4, 2)]))
        return L, AnnotationsDialog(L, None)

    def test_lists_every_annotation(self):
        L, d = self._dlg()
        assert d.table.rowCount() == len(L)

    def test_rows_are_in_drawing_order(self):
        """Qt.UserRole is 256, not 32 — the numeric literal that works
        for a QTreeWidget column does not carry over here."""
        from PySide6.QtCore import Qt
        L, d = self._dlg()
        first_id = d.table.item(0, 0).data(Qt.UserRole)
        assert first_id == L.ordered()[0].id

    def test_toggle_visibility(self):
        L, d = self._dlg()
        d.table.setCurrentCell(0, 0)
        before = L.ordered()[0].style.visible
        d._toggle()
        assert L.ordered()[0].style.visible is not before

    def test_delete_removes_from_the_layer(self):
        L, d = self._dlg()
        d.table.setCurrentCell(0, 0)
        d._delete()
        assert len(L) == 1

    def test_duplicate_adds_an_offset_copy(self):
        L, d = self._dlg()
        d.table.setCurrentCell(0, 0)
        d._duplicate()
        assert len(L) == 3

    def test_z_order_buttons(self):
        L, d = self._dlg()
        d.table.setCurrentCell(0, 0)
        first = L.ordered()[0].id
        d._front()
        assert L.ordered()[-1].id == first
