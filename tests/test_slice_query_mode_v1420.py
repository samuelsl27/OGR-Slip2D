# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.420 (D360) — Query Slice Data is one mode with one owner of the clicks,
and the slices are numbered from 1 wherever the reader sees a number.

The sixth GUI test (H1, H2 of ``INFORME_prueba_GUI_0.1.357.md``) and
``repro_d360.py`` (Hammah et al. 2005, example 1, Bishop, a 6 x 6 grid with
4 radius increments, 50 slices) measured:

* a click right of the exit said «outside the slice range» while the panel
  showed slice 0 of ANOTHER surface, which became the selected one: the
  default click handler (pick the grid cell's best surface) and the query's
  were both connected to ``scene_clicked``;
* of the 50 slices clicked at their centre, 11 also moved the selection;
* Esc did not leave the query, though the bar said «(Esc to exit)»: it only
  left Add Query, and only from the window — the canvas takes Esc when it
  has the focus;
* the last slice read «Slice 49 of 50»: from 0 in the panel, the bar and
  the free-body diagram, from 1 in the graph and the PDF.

By the owner's decision (2026-11-03) the numbers are from 1 on screen; the
engine's ``index``, the API and the CSV of the window stay from 0.

The invariants, measured on the real window, shown:

* with the query on, a click outside every slice changes neither the panel
  nor the selection; a click on any slice never moves the selection;
* Esc sent to the canvas leaves the mode and unticks its menu entry, and a
  click on the grid afterwards picks that cell's surface, untouched by the
  query; the entry itself, and another query, leave it too;
* the last slice is «Slice 50 of 50», and «50» in the panel's first row;
  the free-body diagram asks for a slice from 1 to 50.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_RUN = {}
_WINDOWS = []


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _model(n=50):
    """Hammah, Yacoub, Corkum & Curran (2005), example 1, as
    ``repro_d360.py`` builds it."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import GeneralizedHoekBrown, Material
    from ogr_core.project import Project
    f, left, right = 8.0, 15.0, 15.0
    length = left + 10.0 + right
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(length, 0),
                             Vertex(length, f + 10), Vertex(left + 10, f + 10),
                             Vertex(left, f), Vertex(0, f)], closed=True)
    ext.ensure_ccw()
    p = Project("Hammah et al. 2005, ej. 1")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    rock = Material(name="roca", unit_weight=25.0,
                    strength=GeneralizedHoekBrown(sigci=30000.0, mb=0.067,
                                                  s=2.5e-5, a=0.619))
    p.materials = [rock]
    for reg in p.resolve_regions():
        cx, cy = reg.centroid()
        p.assign_material_at(cx, cy, rock.id)
    p.settings.methods.num_slices = n
    ss = p.settings.search
    ss.grid_nx = ss.grid_ny = 6
    ss.radius_increment = 4
    return p


def _results():
    if "run" not in _RUN:
        from ogr_slip2d.analysis_runner import run_analysis
        p = _model()
        _RUN["run"] = (p, run_analysis(p, ["bishop_simplified"]).results)
    return _RUN["run"]


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    app = _app()
    set_language("en")
    p, results = _results()
    w = InterpretWindow(p, results, None)
    w.resize(1200, 800)
    w.show()
    app.processEvents()
    _WINDOWS.append(w)
    return w


def _done(w):
    w.close()


def _click(w, x, y):
    w.canvas.scene_clicked.emit(float(x), float(y))
    _app().processEvents()


def _middle(s):
    return (s.x_centre, 0.5 * (min(s.base_y_left, s.base_y_right)
                               + max(s.top_y_left, s.top_y_right)))


def _enter(w):
    """Query Slice Data from its menu entry (a tickable one since
    v0.1.420); in a tree without it, as its old entry called it."""
    act = getattr(w, "_act_query_slice", None)
    if act is not None:
        act.setChecked(True)
    else:
        w._query_slice()
    _app().processEvents()


def _slice_number_cell(w):
    t = w.slice_dock.table
    for row in range(t.rowCount()):
        if t.item(row, 0) and t.item(row, 0).text() == "Slice Number":
            return t.item(row, 1).text()
    raise AssertionError("no Slice Number row")


# ======================================================================
class TestOneOwnerOfTheClicks:

    def test_outside_the_slices_nothing_changes(self):
        w = _window()
        try:
            _enter(w)
            target = w._query_slice_target
            first = target.slices[0]
            _click(w, *_middle(first))
            shown, selected = w.slice_dock._slice, w._selected_result
            assert shown is first
            _click(w, target.slices[-1].base_x_right + 0.03, 18.0)
            assert "outside" in w.statusBar().currentMessage()
            assert w.slice_dock._slice is shown
            assert w._selected_result is selected
        finally:
            _done(w)

    def test_no_click_on_a_slice_moves_the_selection(self):
        w = _window()
        try:
            _enter(w)
            target = w._query_slice_target
            moved = []
            for s in target.slices:
                w._selected_result = target
                _click(w, *_middle(s))
                if w._selected_result is not target:
                    moved.append(s.index + 1)
                assert w.slice_dock._slice is s
            assert moved == [], moved
        finally:
            _done(w)


class TestEscLeavesTheMode:

    def test_from_the_canvas_then_the_grid_picks_again(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w = _window()
        try:
            _enter(w)
            target = w._query_slice_target
            w.canvas.setFocus()
            QTest.keyClick(w.canvas, Qt.Key_Escape)
            _app().processEvents()
            # left: a click on a slice is no longer a query of it
            w.statusBar().clearMessage()
            _click(w, *_middle(target.slices[len(target.slices) // 2]))
            said = w.statusBar().currentMessage()
            assert not said.startswith("Slice "), said
            assert not w._slice_query_active
            assert not w._act_query_slice.isChecked()
            # a grid centre whose best surface is another one
            sr = w.search_result
            hit = None
            for r in sr.valid():
                sd = r.surface.to_dict()
                best = w._best_at_grid_centre(sd["centre_x"], sd["centre_y"])
                if best is not None and best is not target:
                    hit = (sd["centre_x"], sd["centre_y"], best)
                    break
            assert hit is not None
            _click(w, hit[0], hit[1])
            assert w._selected_result is hit[2]
            assert not w.statusBar().currentMessage().startswith("Slice ")
        finally:
            _done(w)

    def test_its_menu_entry_and_another_query(self):
        w = _window()
        try:
            w._act_query_slice.setChecked(True)
            assert w._slice_query_active
            w._act_query_slice.setChecked(False)
            assert not w._slice_query_active
            assert "ended" in w.statusBar().currentMessage()
            w._act_query_slice.setChecked(True)
            w._add_query()
            assert not w._slice_query_active
            assert not w._act_query_slice.isChecked()
            w._query_pick_mode = False
        finally:
            _done(w)


class TestSlicesFromOne:

    def test_the_last_one_is_fifty_of_fifty(self):
        w = _window()
        try:
            _enter(w)
            target = w._query_slice_target
            assert len(target.slices) == 50
            _click(w, *_middle(target.slices[-1]))
            assert w.statusBar().currentMessage().startswith(
                "Slice 50 of 50"), w.statusBar().currentMessage()
            assert _slice_number_cell(w) == "50"
            _click(w, *_middle(target.slices[0]))
            assert _slice_number_cell(w) == "1"
            assert target.slices[0].index == 0      # the engine's, from 0
        finally:
            _done(w)

    def test_the_free_body_diagram_asks_from_one(self):
        from PySide6.QtWidgets import QInputDialog
        w = _window()
        asked = []
        raw = QInputDialog.__dict__.get("getInt")
        QInputDialog.getInt = staticmethod(
            lambda parent, title, label, value, lo, hi, *a, **k:
            (asked.append((label, value, lo, hi)), (value, False))[1])
        try:
            w._free_body_diagram()
            n = len(w.search_result.critical.slices)
            assert asked and asked[0][2:] == (1, n), asked
            assert 1 <= asked[0][1] <= n
        finally:
            if raw is None:
                del QInputDialog.getInt
            else:
                QInputDialog.getInt = raw
            _done(w)
