# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D424 (v0.1.447) — the «Global Minimums» block of the report identifies each
method's critical surface, whatever its shape.

The invariant
-------------
A polyline (a non-circular search's, or one the user drew) wrote its factor
and its area alone: nothing said which surface it was. Now, as the
reference's report does, its block gives

* «Axis Location», the point its moments were taken about, only when the
  method keeps one (``details["moment_axis"]``: Bishop and the Ordinary;
  Janbu has no axis, and Spencer and GLE do not keep their reference
  point), the owner's decision;
* its two ends, the first and last vertex
  (``ogr_core.geometry.surface_ends``, the rule the engine's
  ``slope_intercepts`` and the block of the other shapes now ask too);

and a section «Global Minimum Coordinates» lists each method's vertices,
with the page rules of D351. A circle, a composite and a weak-layer clip
write their block as before, character for character (``_V1446``, measured
with v0.1.446 = 80bf5c6, not by this code), and have no such section.

The review of 0.1.447 found that a heading kept with its table went into
one KeepTogether with all of it: a table that did not fit went to the next
page whole (a page with only its foot before the vertices; 450 to 640 pt
empty under Slice Data's first method since D351). The tables' headings no
longer keep with them, and a ``CondPageBreak`` keeps them off a page's
foot (``TestThePageRules``). Its sweeps lay out 16 reports, which is most of
the 5 s this file takes: each position is one where a heading meets a
page's foot, measured, and a coarser sweep proved nothing.

The reference (rule 1)
----------------------
The reference's report of the polyline drawn by hand on the worked example
Ej_1 (``Slide2d_Ej_1_Block_Search.htm``; the model of
``test_slide_validation_ej1`` and the surface of
``test_noncircular_validation_v192``, imported untouched) gives, for every
method: Axis Location 82.500, 72.500; Left Slip Surface Endpoint 40.000,
50.000; Right Slip Surface Endpoint 75.000, 25.000; Total Slice Area 225 m²;
and the six vertices (40, 50) (45, 45) (50, 40) (55, 35) (60, 30) (75, 25).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: The reference's report on Ej_1's hand-drawn polyline, written out.
_REFERENCE = {
    "axis": "(82.500, 72.500)",
    "left": "(40.000, 50.000)",
    "right": "(75.000, 25.000)",
    "area": "225.000 m²",
    "vertices": [("40.000", "50.000"), ("45.000", "45.000"),
                 ("50.000", "40.000"), ("55.000", "35.000"),
                 ("60.000", "30.000"), ("75.000", "25.000")],
}

#: The blocks of the other shapes, measured with 0.1.446 (80bf5c6), not by
#: this code (``medir_d424.py`` of the bank, cases 1, 4 and 6): they may not
#: move by a character.
_V1446 = {
    "circle": ["Method: Bishop Simplified", "Factor of Safety (FS)", "1.1081",
               "Centre", "(40.000, 37.000)", "Radius", "22.390",
               "Left Slip Surface Endpoint", "(21.097, 25.000)",
               "Right Slip Surface Endpoint", "(34.771, 15.229)",
               "Total Slice Area", "37.492 m²"],
    "weak_layer": ["Method: Bishop Simplified", "Factor of Safety (FS)",
                   "1.5185", "Left Slip Surface Endpoint", "(2.496, 2.496)",
                   "Right Slip Surface Endpoint", "(16.731, 10.000)",
                   "Total Slice Area", "49.172 m²"],
    "composite": ["Method: Bishop Simplified", "Factor of Safety (FS)",
                  "1.3435", "Centre", "(125.000, 90.000)", "Radius", "87.366",
                  "Left Slip Surface Endpoint", "(42.946, 60.000)",
                  "Right Slip Surface Endpoint", "(177.277, 20.000)",
                  "Total Slice Area", "2289.573 m²"],
}

_CACHE: dict = {}


def _capture(project, results, translate=None):
    """What the report writes from «Global Minimums» up to the next section
    that is not this version's: ``[("p", text) | ("t", rows)]``, the
    paragraphs with their bold taken off and the plain-text tables."""
    import ogr_core.report.report_generator as RG
    said = []
    real_p, real_t = RG.Paragraph, RG.Table

    class Par(real_p):
        def __init__(self, text, *a, **k):
            said.append(("p", str(text).replace("<b>", "").replace("</b>",
                                                                  "")))
            super().__init__(text, *a, **k)

    class Tab(real_t):
        def __init__(self, data, *a, **k):
            if all(isinstance(c, str) for row in data for c in row):
                said.append(("t", [list(row) for row in data]))
            super().__init__(data, *a, **k)

    RG.Paragraph, RG.Table = Par, Tab
    try:
        with tempfile.TemporaryDirectory() as d:
            RG.generate_report(project, results, os.path.join(d, "r.pdf"),
                               translate=translate)
    finally:
        RG.Paragraph, RG.Table = real_p, real_t
    texts = [v for k, v in said if k == "p"]
    first = said.index(("p", texts[texts.index(
        "Global Minimums" if translate is None else "Mínimos globales")]))
    last = next(i for i, (k, v) in enumerate(said)
                if k == "p" and v in ("Valid / Invalid Surfaces",
                                      "Superficies válidas / inválidas"))
    return said[first + 1:last]


def _paragraphs(part) -> list:
    return [v for k, v in part if k == "p"]


def _block(part, method_heading) -> list:
    """The rows of one method's block: its heading and what follows, up to
    the next heading or section."""
    texts = _paragraphs(part)
    i = texts.index(method_heading)
    out = [texts[i]]
    for t in texts[i + 1:]:
        if t.startswith(("Method: ", "Método: ")) or t in (
                "Global Minimum Coordinates",
                "Coordenadas de los mínimos globales"):
            break
        out.append(t)
    return out


def _ej1():
    """Ej_1 with its hand-drawn polyline, Bishop, Janbu and Spencer, once."""
    if "ej1" not in _CACHE:
        from test_noncircular_validation_v192 import EJ1_SURFACE
        from test_slide_validation_ej1 import _ej1_project

        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.analysis_runner import run_analysis
        p = _ej1_project()
        s = p.settings.search
        s.surface_type, s.search_method, s.path_num_surfaces = (
            "non_circular", "path", 5)
        p.settings.methods.num_slices = 25
        p.user_polylines = [UserPolylineSurface.from_points(EJ1_SURFACE)]
        out = run_analysis(p, ["ordinary_fellenius", "bishop_simplified",
                               "janbu_simplified", "spencer"])
        _CACHE["ej1"] = (p, out.results)
    return _CACHE["ej1"]


def _long():
    """Ej_1 with its hand-drawn polyline cut into 51 vertices on the same
    five segments, Bishop, 100 slices, once."""
    if "long" not in _CACHE:
        from test_noncircular_validation_v192 import EJ1_SURFACE
        from test_slide_validation_ej1 import _ej1_project

        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.analysis_runner import run_analysis
        pts = [(x0 + k / 10 * (x1 - x0), y0 + k / 10 * (y1 - y0))
               for (x0, y0), (x1, y1) in zip(EJ1_SURFACE, EJ1_SURFACE[1:])
               for k in range(10)] + [EJ1_SURFACE[-1]]
        p = _ej1_project()
        s = p.settings.search
        s.surface_type, s.search_method, s.path_num_surfaces = (
            "non_circular", "path", 5)
        p.settings.methods.num_slices = 100
        p.user_polylines = [UserPolylineSurface.from_points(pts)]
        _CACHE["long"] = (p, run_analysis(p, ["bishop_simplified"]).results)
    return _CACHE["long"]

def _run(p, methods=("bishop_simplified",)):
    from ogr_slip2d.analysis_runner import run_analysis
    return run_analysis(p, list(methods)).results


def _circle():
    if "circle" not in _CACHE:
        from examples.quick_slope import build_demo_slope
        p = build_demo_slope()
        s = p.settings.search
        s.grid_nx, s.grid_ny, s.radius_increment = 5, 5, 6
        _CACHE["circle"] = (p, _run(p))
    return _CACHE["circle"]


def _path():
    """The demo slope by Path Search, 5 surfaces: a 13-vertex critical."""
    if "path" not in _CACHE:
        from examples.quick_slope import build_demo_slope
        p = build_demo_slope()
        s = p.settings.search
        s.surface_type, s.search_method, s.path_num_surfaces = (
            "non_circular", "path", 5)
        _CACHE["path"] = (p, _run(p))
    return _CACHE["path"]


def _weak_layer():
    if "weak" not in _CACHE:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        p = Project("weak layer")
        p.boundaries.append(Boundary(polyline=Polyline([Vertex(*v) for v in (
            (0.0, 0.0), (40.0, 0.0), (40.0, 10.0), (10.0, 10.0))],
            closed=True), btype=BoundaryType.EXTERNAL))
        p.materials.append(Material(
            name="Soil", unit_weight=20.0,
            strength=MohrCoulomb(cohesion=20.0, friction_angle=30.0)))
        jm = Material(name="Joint", unit_weight=20.0,
                      strength=MohrCoulomb(cohesion=5.0, friction_angle=20.0))
        p.materials.append(jm)
        p.boundaries.append(Boundary(
            polyline=Polyline([Vertex(2.0, 2.0), Vertex(30.0, 10.0)]),
            btype=BoundaryType.WEAK_LAYER, material_id=jm.id))
        s = p.settings.search
        s.grid_x_min, s.grid_x_max, s.grid_y_min, s.grid_y_max = (
            5.0, 25.0, 15.0, 35.0)
        s.grid_nx = s.grid_ny = 3
        s.radius_increment = 3
        _CACHE["weak"] = (p, _run(p))
    return _CACHE["weak"]


def _composite():
    """Problem 22 (Fredlund and Krahn 1977) with Composite Surfaces."""
    if "composite" not in _CACHE:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        from ogr_core.project.units import FailureDirection
        p = Project("composite")
        ext = Polyline(vertices=[Vertex(x, y) for x, y in (
            (0, 15), (180, 15), (180, 16), (180, 20), (140, 20), (60, 60),
            (0, 60), (0, 16))], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 16.0), Vertex(180, 16.0)], closed=False),
            btype=BoundaryType.MATERIAL))
        up = Material(name="Upper soil", unit_weight=120.0,
                      sat_unit_weight=120.0,
                      strength=MohrCoulomb(cohesion=600.0,
                                           friction_angle=20.0))
        wk = Material(name="Weak layer", unit_weight=120.0,
                      sat_unit_weight=120.0,
                      strength=MohrCoulomb(cohesion=0.0, friction_angle=10.0))
        p.materials = [up, wk]
        p.resolve_regions()
        p.assign_material_at(90.0, 30.0, up.id)
        p.assign_material_at(90.0, 15.5, wk.id)
        p.settings.units.system_id = "imperial_psf"
        p.settings.methods.num_slices = 30
        p.settings.search.composite_surfaces = True
        p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
        s = p.settings.search
        s.grid_x_min, s.grid_x_max, s.grid_y_min, s.grid_y_max = (
            115.0, 125.0, 85.0, 95.0)
        s.grid_nx = s.grid_ny = 2
        s.radius_increment = 2
        _CACHE["composite"] = (p, _run(p))
    return _CACHE["composite"]


# ======================================================================
class TestTheReferencePolyline:

    def test_the_premise_each_critical_is_the_users_polyline(self):
        _p, results = _ej1()
        for mid, r in results.items():
            c = r.critical
            assert r.is_user_surface(c), mid
            pts = [(v.x, v.y) for v in c.surface.polyline.vertices]
            assert len(pts) == 6, (mid, pts)

    def test_bishop_names_its_axis_and_its_ends(self):
        p, results = _ej1()
        block = _block(_capture(p, results), "Method: Bishop Simplified")
        assert block[1:3] == ["Factor of Safety (FS)", "0.9239"], block
        assert block[3:] == [
            "Axis Location", _REFERENCE["axis"],
            "Left Slip Surface Endpoint", _REFERENCE["left"],
            "Right Slip Surface Endpoint", _REFERENCE["right"],
            "Total Slice Area", _REFERENCE["area"]], block

    def test_the_ordinary_names_its_axis_too(self):
        """It keeps one, as Bishop does, and the reference gives it."""
        p, results = _ej1()
        block = _block(_capture(p, results), "Method: Ordinary / Fellenius")
        assert block[3:5] == ["Axis Location", _REFERENCE["axis"]], block

    def test_janbu_and_spencer_name_their_ends_and_no_axis(self):
        """The owner's decision: the row comes with the axis the method
        used, and these two keep none."""
        p, results = _ej1()
        part = _capture(p, results)
        for heading in ("Method: Janbu Simplified", "Method: Spencer"):
            block = _block(part, heading)
            assert "Axis Location" not in block, (heading, block)
            assert block[3:] == [
                "Left Slip Surface Endpoint", _REFERENCE["left"],
                "Right Slip Surface Endpoint", _REFERENCE["right"],
                "Total Slice Area", _REFERENCE["area"]], (heading, block)

    def test_the_coordinates_list_the_six_vertices_of_each_method(self):
        p, results = _ej1()
        part = _capture(p, results)
        texts = _paragraphs(part)
        i = texts.index("Global Minimum Coordinates")
        assert texts[i + 1:i + 5] == ["Method: Ordinary / Fellenius",
                                      "Method: Bishop Simplified",
                                      "Method: Janbu Simplified",
                                      "Method: Spencer"], texts[i:]
        tables = [rows for k, rows in part if k == "t"
                  and rows and rows[0] == ["Vertex", "X", "Y"]]
        assert len(tables) == 4, tables
        want = [[str(k), x, y]
                for k, (x, y) in enumerate(_REFERENCE["vertices"], 1)]
        for rows in tables:
            assert rows[1:] == want, rows

    def test_in_spanish(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        p, results = _ej1()
        before = current_language()
        set_language("es")
        try:
            part = _capture(p, results, translate=note_text)
        finally:
            set_language(before)
        texts = _paragraphs(part)
        # the menu's term: «Definir eje de momentos» (the owner's choice)
        assert "Posición del eje de momentos" in texts, texts
        assert "Coordenadas de los mínimos globales" in texts, texts
        assert any(k == "t" and rows[0][0] == "Vértice"
                   for k, rows in part), part


# ======================================================================
class TestASearchPolyline:
    """A polyline the search generated (Path Search, 13 vertices) is
    identified too: the block names its ends and the axis Bishop kept, and
    the section lists its 13 vertices."""

    def test_its_block_and_its_vertices(self):
        p, results = _path()
        c = results["bishop_simplified"].critical
        pts = [(v.x, v.y) for v in c.surface.polyline.vertices]
        assert len(pts) == 13 and not results[
            "bishop_simplified"].is_user_surface(c)
        part = _capture(p, results)
        block = _block(part, "Method: Bishop Simplified")
        assert block[3] == "Axis Location", block
        assert block[5:9] == [
            "Left Slip Surface Endpoint",
            "(%.3f, %.3f)" % pts[0], "Right Slip Surface Endpoint",
            "(%.3f, %.3f)" % pts[-1]], block
        rows, = [rows for k, rows in part if k == "t"
                 and rows and rows[0] == ["Vertex", "X", "Y"]]
        assert len(rows) == 14, rows


# ======================================================================
class TestEachMethodItsOwn:
    """Path Search with three methods: the vertices the section lists under
    each method are those of that method's critical polyline."""

    def test_the_vertices_of_each(self):
        from examples.quick_slope import build_demo_slope
        if "path3" not in _CACHE:
            p = build_demo_slope()
            s = p.settings.search
            s.surface_type, s.search_method, s.path_num_surfaces = (
                "non_circular", "path", 5)
            _CACHE["path3"] = (p, _run(p, ("bishop_simplified",
                                           "janbu_simplified", "spencer")))
        p, results = _CACHE["path3"]
        own = [[(v.x, v.y) for v in results[m].critical.surface.polyline
                .vertices] for m in ("bishop_simplified", "janbu_simplified",
                                     "spencer")]
        # the premise: Spencer's (6 vertices) is not Bishop's and Janbu's
        # (13), so the first method's vertices listed for all would fail
        assert len({tuple(v) for v in own}) >= 2, [len(v) for v in own]
        tables = [rows for k, rows in _capture(p, results) if k == "t"
                  and rows and rows[0] == ["Vertex", "X", "Y"]]
        assert [[(float(x), float(y)) for _k, x, y in rows[1:]]
                for rows in tables] == [
            [(float("%.3f" % x), float("%.3f" % y)) for x, y in pts]
            for pts in own]


# ======================================================================
class TestTheOtherShapesDoNotMove:

    def _first_block(self, case):
        p, results = case()
        part = _capture(p, results)
        return part, _block(part, "Method: Bishop Simplified")

    def test_a_circle(self):
        part, block = self._first_block(_circle)
        assert block == _V1446["circle"], block
        assert "Global Minimum Coordinates" not in _paragraphs(part)

    def test_a_weak_layer_clip(self):
        """It keeps its axis (``moment_axis``) and gets no row for it: the
        owner's decision is for a polyline only."""
        part, block = self._first_block(_weak_layer)
        p, results = _weak_layer()
        assert (results["bishop_simplified"].critical.details
                .get("moment_axis")) is not None
        assert block == _V1446["weak_layer"], block
        assert "Global Minimum Coordinates" not in _paragraphs(part)

    def test_a_composite(self):
        part, block = self._first_block(_composite)
        assert block == _V1446["composite"], block
        assert "Global Minimum Coordinates" not in _paragraphs(part)


# ======================================================================
class TestTheEnds:
    """One rule, in the core, which the engine asks too."""

    def test_slope_intercepts_asks_the_core(self):
        from ogr_core.geometry.surface_ends import surface_x_ends
        from ogr_slip2d.interpretation import slope_intercepts
        for case in (_circle, _weak_layer, _composite, _path):
            _p, results = case()
            c = results["bishop_simplified"].critical
            assert slope_intercepts(c) == surface_x_ends(c.surface)

    def test_a_polyline_drawn_right_to_left_gives_the_same_ends(self):
        from ogr_core.geometry.surface_ends import surface_ends
        from ogr_slip2d.surface import SlipSurface
        from ogr_core.geometry import Polyline, Vertex
        pts = [(40.0, 50.0), (45.0, 45.0), (75.0, 25.0)]
        fwd = SlipSurface(polyline=Polyline([Vertex(*v) for v in pts]))
        back = SlipSurface(polyline=Polyline([Vertex(*v) for v in pts[::-1]]))
        assert surface_ends(fwd) == surface_ends(back) == (
            (40.0, 50.0), (75.0, 25.0))

    def test_the_report_and_the_engine_ask_the_core(self):
        """Counted, not compared: a copy of the rule giving the same numbers
        would pass a comparison."""
        import ogr_core.geometry.surface_ends as SE
        import ogr_core.report.report_generator as RG
        from ogr_slip2d.interpretation import slope_intercepts
        calls = []
        real_x, real_e = SE.surface_x_ends, RG.surface_ends

        def spy_x(surface):
            calls.append("x")
            return real_x(surface)

        def spy_e(surface):
            calls.append("e")
            return real_e(surface)

        SE.surface_x_ends, RG.surface_ends = spy_x, spy_e
        try:
            p, results = _circle()
            slope_intercepts(results["bishop_simplified"].critical)
            assert calls == ["x"], calls
            del calls[:]
            _capture(p, results)
            assert calls[:2] == ["e", "x"], calls
        finally:
            SE.surface_x_ends, RG.surface_ends = real_x, real_e

    def test_the_other_shapes_ends_are_the_blocks(self):
        """For a circle, a composite and a weak-layer clip the core's rule
        gives the ends the block writes, bit for bit."""
        from ogr_core.geometry.surface_ends import surface_ends
        for case in (_circle, _weak_layer, _composite):
            _p, results = case()
            s = results["bishop_simplified"].critical.surface
            assert surface_ends(s) == ((s.x_left, s.base_y_at(s.x_left)),
                                       (s.x_right, s.base_y_at(s.x_right)))


# ======================================================================
class TestThePageRules:
    """D351's, with tables long enough to break a page. Two cases:

    * Ej_1's hand-drawn polyline cut into 51 vertices on the same five
      segments (100 slices, so its vertices fit), over a fine sweep of the
      summary's comments: the table of its vertices breaks in two;
    * Ej_1 by its grid, two methods, 60 slices: Slice Data's second table.

    The defect the review of 0.1.447 found: a heading that kept with its
    table went into one KeepTogether WITH it, and a table that did not fit
    went to the next page whole. With 3 lines of comments page 2 held its
    foot alone; Slice Data's second method left 450 pt empty under the
    first since D351. Now no page holds only its foot, a table's heading
    starts a new page only when less than its room is left, no heading is
    the last thing on its page, and a table breaks with its header row and
    fits the frame."""

    def _laid_out(self, p, results):
        """``([(page, flowable, y, frame bottom)], pages' text)``."""
        import io

        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtWidgets import QApplication
        from reportlab.platypus import SimpleDocTemplate

        import ogr_core.report.report_generator as RG
        seen = []
        real = SimpleDocTemplate.afterFlowable

        def after(self, flowable):
            fr = self.frame
            seen.append((self.page, flowable,
                         None if fr is None else fr._y,
                         None if fr is None else fr._y1))
            return real(self, flowable)

        SimpleDocTemplate.afterFlowable = after
        buf = io.BytesIO()
        try:
            RG.generate_report(p, results, buf)
        finally:
            SimpleDocTemplate.afterFlowable = real
        QApplication.instance() or QApplication([])
        data = QBuffer()
        data.setData(QByteArray(buf.getvalue()))
        data.open(QIODevice.ReadOnly)
        doc = QPdfDocument()
        doc.load(data)
        texts = [doc.getAllText(i).text() for i in range(doc.pageCount())]
        doc.close()
        return seen, texts

    def _sweep(self):
        if "sweep" not in _CACHE:
            import copy
            p, results = _long()
            q = copy.copy(p)
            q.settings = copy.deepcopy(p.settings)
            out = {}
            # 0-4: the blank page of the review came at 3; 52-60: the
            # section's heading walks over the foot of page 2 (measured)
            for n in (0, 1, 2, 3, 4) + tuple(range(52, 61)):
                q.settings.summary.comments = ["line %d" % i
                                               for i in range(n)]
                out[n] = self._laid_out(q, results)
            _CACHE["sweep"] = out
        return _CACHE["sweep"]

    def _slice_data(self, slices=60):
        """Ej_1 by its grid, two methods: with 60 slices the second table
        went whole to the next page (450 pt empty, since D351); with 82
        the first table ends ~50 pt above the foot, where the second
        heading fits and its table does not (measured)."""
        key = ("slice_data", slices)
        if key not in _CACHE:
            from test_slide_validation_ej1 import _ej1_project
            p = _ej1_project()
            s = p.settings.search
            s.grid_nx = s.grid_ny = s.radius_increment = 3
            p.settings.methods.num_slices = slices
            _CACHE[key] = self._laid_out(
                p, _run(p, ("bishop_simplified", "janbu_simplified")))
        return _CACHE[key]

    def _all(self):
        return list(self._sweep().items()) + [
            ("slice data, %d" % k, self._slice_data(k)) for k in (60, 82)]

    @staticmethod
    def _table_headings(seen) -> list:
        """``[(index, page)]`` of the methods' headings under the two
        sections of long tables, by the section they are in and not by
        their style (the defect was in the style)."""
        from reportlab.platypus import Paragraph
        out, inside = [], False
        for i, (page, f, _y, _y1) in enumerate(seen):
            if not isinstance(f, Paragraph):
                continue
            name = getattr(f.style, "name", "")
            if name == "OGRSection":
                inside = f.getPlainText() in (
                    "Global Minimum Coordinates",
                    "Slice Data (Global Minimum Query)")
            elif inside and name == "OGRMethod":
                out.append((i, page))
        return out

    #: Flowables that take no room of their own: breaks, spacers, and the
    #: zero-height actions a KeepTogether or a split table leaves (in
    #: v0.1.446 an ``LCActionFlowable`` opened the page before Slice Data's
    #: second heading).
    _NOT_CONTENT = ("CondPageBreak", "Spacer", "LCActionFlowable",
                    "_FrameBreak", "PageBreak", "HRFlowable")

    @classmethod
    def _opens_its_page(cls, seen, i, page) -> bool:
        return not any(r[0] == page and r[2] is not None
                       and type(r[1]).__name__ not in cls._NOT_CONTENT
                       for r in seen[:i])

    @staticmethod
    def _is_vertex_table(f) -> bool:
        return (type(f).__name__ == "Table"
                and getattr(f, "_cellvalues", [[None]])[0][:1] == ["Vertex"])

    def test_no_page_holds_only_its_foot(self):
        empty = {}
        for n, (_seen, texts) in self._all():
            only = [k + 1 for k, t in enumerate(texts)
                    if len(" ".join(t.split())) < 120]
            if only:
                empty[n] = only
        assert not empty, empty

    def test_a_table_heading_leaves_no_room_behind(self):
        """When a table's heading starts a new page, the page before had
        less than its room left (``table_room``, 35 mm)."""
        from reportlab.lib.units import mm
        left = {}
        for n, (seen, _texts) in self._all():
            for i, page in self._table_headings(seen):
                if not self._opens_its_page(seen, i, page):
                    continue
                before = [r for r in seen[:i] if r[0] == page - 1
                          and r[2] is not None
                          and type(r[1]).__name__ != "LCActionFlowable"]
                if before:
                    free = before[-1][2] - before[-1][3]
                    if free >= 35 * mm:
                        left.setdefault(n, []).append(round(free, 1))
        assert not left, left

    def test_the_premise_both_sections_have_their_headings(self):
        """Slice Data's second heading is under the end of the first table,
        on its page (in v0.1.446 it opened the next one), and the sweep
        meets the section of vertices every time."""
        seen, _texts = self._slice_data()
        heads = self._table_headings(seen)
        assert len(heads) == 2, heads
        assert not self._opens_its_page(seen, *heads[1])
        for n, (seen, _t) in self._sweep().items():
            assert self._table_headings(seen), n

    def test_no_heading_left_at_a_pages_foot(self):
        from reportlab.platypus import Paragraph
        alone = {}
        for n, (seen, _texts) in self._all():
            for i, (page, f, _y, _y1) in enumerate(seen):
                if not (isinstance(f, Paragraph) and getattr(
                        f.style, "name", "") in ("OGRSection", "OGRMethod")):
                    continue
                nxt = next((pg for pg, g, _a, _b in seen[i + 1:]
                            if type(g).__name__ not in self._NOT_CONTENT),
                           None)
                if nxt is not None and nxt != page:
                    alone.setdefault(n, []).append(f.getPlainText())
        assert not alone, alone

    def test_the_table_breaks_with_its_header_and_fits_the_frame(self):
        from ogr_core.report.report_generator import project_width
        p, _results = _long()
        width = project_width(p)
        for n, (seen, _texts) in self._sweep().items():
            parts = [f for _pg, f, _y, _y1 in seen if self._is_vertex_table(f)]
            assert len(parts) == 2, (n, len(parts))
            assert sum(len(f._cellvalues) - 1 for f in parts) == 51, n
            for f in parts:
                assert sum(f._colWidths) <= width + 1e-6
