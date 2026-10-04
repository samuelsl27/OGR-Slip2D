# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A surface that runs along a weak layer is drawn, exported, picked, named and
summarised like any other — and Add Query picks away from the grid again.

WHAT INVARIANT THIS PROTECTS (D251). Every consumer that dispatches on the
serialised ``type`` of a slip surface must know ``weak_layer`` (and, in the
API, ``composite``), or the surface the engine analysed disappears from the
place that reads it:

* the canvas drew it as an EMPTY path since v0.1.121 — the critical surface
  of a model with a weak layer was not on the screen;
* the DXF export raised ``AttributeError`` on its missing ``polyline``
  before ``saveas``, so no file was written at all;
* the interpretation window could not pick it on the grid that generated it,
  ``minimum_per_centre`` treated it as having no centre, and its row said
  "non-circular surface";
* the API answered ``{"type": ...}`` for it and for a composite, with no
  geometry;
* optimisation refused it as "a circle".

AND (D252) Add Query picks away from a grid centre: since v0.1.201 the window
called ``_distance_point_to_surface``, which that version had moved to
``ogr_slip2d.interpretation``, and every such pick raised.

WHY THESE ANCHORS. The planar joint of ``test_weak_layer_v1121`` runs along
the straight line y = 2 + (8/28)(x - 2) from (2, 2) to (30, 10): a surface
clipped onto it IS that line, so every drawn point has to lie on it, which is
geometry rather than a printed number. The rest are identities: the drawing
vertices the surface itself publishes, the base's centre, the engine's own
priced path.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

try:
    import ezdxf  # noqa: F401
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


_WINDOWS = []
_SLICES = 40
_CX, _CY, _R = 18.0, 28.0, 20.0


def _on_the_joint(x, y):
    return abs(y - (2.0 + (8.0 / 28.0) * (x - 2.0))) < 1e-9


def _planar():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("weak layer drawing")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(0, 0), Vertex(40, 0), Vertex(40, 10),
                           Vertex(10, 10)], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(name="Soil", unit_weight=20.0,
                                strength=MohrCoulomb(cohesion=20.0,
                                                     friction_angle=30.0)))
    joint = Material(name="Joint", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=5.0, friction_angle=20.0))
    p.materials.append(joint)
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(2, 2), Vertex(30, 10)]),
        btype=BoundaryType.WEAK_LAYER, material_id=joint.id))
    p.settings.methods.num_slices = _SLICES
    return p


def _planar_critical():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.analysis_runner import build_evaluator
    from ogr_slip2d.surface import SlipSurface

    p = _planar()
    ev = build_evaluator(p, "ordinary_fellenius", num_slices=_SLICES)
    with p.regions_frozen():
        r = ev.evaluate_surface(p, SlipSurface(polyline=Polyline(
            [Vertex(2, 2), Vertex(16, 1), Vertex(30, 10)])))
    return p, r


def _circle_model():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("weak layer drawing, circle")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(0, 0), Vertex(40, 0), Vertex(40, 20),
                           Vertex(25, 20), Vertex(10, 10), Vertex(0, 10)],
                          closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(name="Soil", unit_weight=20.0,
                                strength=MohrCoulomb(cohesion=20.0,
                                                     friction_angle=30.0)))
    joint = Material(name="Joint", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=1.0, friction_angle=5.0))
    p.materials.append(joint)
    d = math.sqrt(_R ** 2 - (_CY - 9.0) ** 2)
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(_CX - d, 9.0), Vertex(_CX + d, 9.0)]),
        btype=BoundaryType.WEAK_LAYER, material_id=joint.id))
    p.settings.methods.num_slices = _SLICES
    return p


def _circle_critical():
    from ogr_slip2d.analysis_runner import build_evaluator
    from ogr_slip2d.surface import SlipCircle

    p = _circle_model()
    ev = build_evaluator(p, "bishop_simplified", num_slices=_SLICES)
    with p.regions_frozen():
        r = ev.evaluate_circle(p, SlipCircle(_CX, _CY, _R))
    return p, r


def _path_points(item):
    path = item.path()
    return [(path.elementAt(i).x, path.elementAt(i).y)
            for i in range(path.elementCount())]


# ======================================================================
class TestThePremise:

    def test_the_two_criticals_run_along_their_joints(self):
        _p, r = _planar_critical()
        assert type(r.surface).__name__ == "WeakLayerSurface"
        assert all(_on_the_joint(x, y) for x, y in r.surface.drawing_vertices())
        _p, c = _circle_critical()
        assert type(c.surface).__name__ == "WeakLayerSurface"
        assert c.surface.to_dict()["base"]["type"] == "circle"


# ======================================================================
@_requires(_QT)
class TestTheCanvasDrawsIt:

    def test_the_path_is_the_surface_drawing_vertices(self):
        from ogr_gui.canvas.graphics_items import SlipSurfaceItem
        QApplication.instance() or QApplication([])
        _p, r = _planar_critical()
        sd = r.surface.to_dict()
        pts = _path_points(SlipSurfaceItem(sd, r.fos, is_critical=True))
        assert len(pts) == len(sd["vertices"]) >= 2
        assert pts == [tuple(v) for v in sd["vertices"]]
        assert all(_on_the_joint(x, y) for x, y in pts)

    def test_the_other_types_are_drawn_as_before(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_gui.canvas.graphics_items import SlipSurfaceItem
        from ogr_slip2d.surface import SlipSurface
        QApplication.instance() or QApplication([])
        poly = SlipSurface(polyline=Polyline(
            [Vertex(2, 2), Vertex(16, 1), Vertex(30, 10)])).to_dict()
        assert _path_points(SlipSurfaceItem(poly, 1.0)) == [
            (2.0, 2.0), (16.0, 1.0), (30.0, 10.0)]
        _p, c = _circle_critical()
        base = c.surface.to_dict()["base"]
        assert len(_path_points(SlipSurfaceItem(base, c.fos))) > 2

    def test_its_radii_come_from_its_base_circle(self):
        from ogr_gui.canvas.graphics_items import SlipRadiiItem
        QApplication.instance() or QApplication([])
        _p, c = _circle_critical()
        sd = c.surface.to_dict()
        pts = _path_points(SlipRadiiItem(sd))
        assert len(pts) == 4
        assert pts[0] == (_CX, _CY) and pts[2] == (_CX, _CY)
        for (x, y), end in ((pts[1], sd["x_left"]), (pts[3], sd["x_right"])):
            assert x == end
            assert abs(math.hypot(x - _CX, y - _CY) - _R) < 1e-9


# ======================================================================
@_requires(_HAS_EZDXF)
class TestTheDxfExportWritesIt:

    def test_the_polyline_is_its_drawing_vertices(self):
        import ezdxf as _ezdxf

        from ogr_core.dxf.exporter import ExportOptions, export_dxf
        p, r = _planar_critical()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "weak.dxf"
            rep = export_dxf(p, out, ExportOptions(unit="m"),
                             {"ordinary_fellenius": SimpleNamespace(critical=r)})
            assert out.exists(), rep.error
            assert rep.entities.get("OGR_X_SLIP_SURFACE") == 1
            doc = _ezdxf.readfile(str(out))
            pl = [e for e in doc.modelspace()
                  if e.dxf.layer == "OGR_X_SLIP_SURFACE"][0]
            pts = [(x, y) for x, y, *_ in pl.get_points()]
        expected = r.surface.drawing_vertices()
        assert len(pts) == len(expected)
        for (x, y), (ex, ey) in zip(pts, expected):
            assert abs(x - ex) < 1e-9 and abs(y - ey) < 1e-9

    def test_an_unknown_surface_is_left_out_and_said(self):
        from ogr_core.dxf.exporter import ExportOptions, export_dxf
        p, r = _planar_critical()
        odd = SimpleNamespace(critical=SimpleNamespace(
            surface=SimpleNamespace(), fos=1.0))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "odd.dxf"
            rep = export_dxf(p, out, ExportOptions(unit="m"),
                             {"odd_method": odd})
            assert out.exists(), rep.error
        assert any("odd_method" in s for s in rep.skipped), rep.skipped


# ======================================================================
class TestInterpretationKnowsIt:

    def test_its_slip_centre_is_its_base_circles(self):
        from ogr_slip2d.interpretation import slip_centre
        _p, c = _circle_critical()
        assert slip_centre(c.surface.to_dict()) == (_CX, _CY)
        _p, r = _planar_critical()
        assert slip_centre(r.surface.to_dict()) is None   # polyline base

    def test_minimum_per_centre_files_it_under_that_centre(self):
        """Two weak-layer surfaces clipped from circles of ONE centre are
        one grid point: only the lower factor is kept. Filed as surfaces
        without a centre, as until v0.1.252, both were."""
        from ogr_slip2d.interpretation import minimum_per_centre
        _p, c = _circle_critical()
        sd = c.surface.to_dict()
        other = dict(sd, id="another", base=dict(sd["base"], radius=_R - 1.0))
        lower = SimpleNamespace(surface=SimpleNamespace(to_dict=lambda: sd),
                                fos=1.10)
        higher = SimpleNamespace(
            surface=SimpleNamespace(to_dict=lambda: other), fos=1.30)
        res = SimpleNamespace(valid=lambda: [higher, lower])
        assert minimum_per_centre(res) == [lower]


@_requires(_QT)
class TestItsRowNamesIt:

    def test_its_row_names_it(self):
        from ogr_gui.i18n import set_language
        from ogr_gui.interpret_window import minimum_row_text
        QApplication.instance() or QApplication([])
        set_language("en")
        _p, c = _circle_critical()
        sd = c.surface.to_dict()
        assert minimum_row_text(3, sd) == (
            "3: weak-layer surface, x from %.2f to %.2f"
            % (sd["x_left"], sd["x_right"]))


# ======================================================================
class TestTheApiSummarisesIt:

    def test_a_weak_layer_surface_carries_its_geometry(self):
        from ogr_api.results import surface_summary
        _p, c = _circle_critical()
        s = surface_summary(c.surface)
        assert s["type"] == "weak_layer"
        assert s["base"]["type"] == "circle"
        assert (s["base"]["centre_x"], s["base"]["centre_y"]) == (_CX, _CY)
        assert s["weak_layers"] and all(
            {"x0", "x1", "material_id", "boundary_id"} <= set(w)
            for w in s["weak_layers"])
        assert len(s["vertices"]) == len(c.surface.drawing_vertices())

    def test_a_composite_carries_its_circle_and_vertices(self):
        from ogr_api.results import surface_summary
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import CompositeSurface, SlipCircle
        circle = SlipCircle(centre_x=120.0, centre_y=90.0, radius=80.0)
        circle.x_left, circle.x_right = 45.0, 158.0
        comp = CompositeSurface(
            circle=circle,
            bedrock=Polyline(vertices=[Vertex(0.0, 15.0),
                                       Vertex(180.0, 15.0)]),
            x_left=45.0, x_right=158.0)
        s = surface_summary(comp)
        assert s["type"] == "composite" and s["radius"] == 80.0
        assert len(s["vertices"]) == len(comp.to_dict()["vertices"]) > 2

    def test_circle_and_polyline_are_summarised_as_before(self):
        from ogr_api.results import surface_summary
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        c = SlipCircle(centre_x=1.0, centre_y=2.0, radius=3.0)
        assert set(surface_summary(c)) == {"type", "centre_x", "centre_y",
                                           "radius", "x_left", "x_right"}
        s = surface_summary(SlipSurface(polyline=Polyline(
            [Vertex(0, 0), Vertex(1, 1)])))
        assert s == {"type": "polyline", "vertices": [[0.0, 0.0],
                                                      [1.0, 1.0]]}


# ======================================================================
class TestOptimisationSaysWhatItIs:

    def test_the_refusal_tells_a_weak_layer_from_a_circle(self):
        from ogr_slip2d.optimize import (OPTIMISE_A_CIRCLE,
                                         OPTIMISE_A_WEAK_LAYER,
                                         optimisation_refusal)
        _p, r = _planar_critical()
        _p, c = _circle_critical()
        assert optimisation_refusal(r.surface) == OPTIMISE_A_WEAK_LAYER
        assert optimisation_refusal(c.surface.base) == OPTIMISE_A_CIRCLE
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipSurface
        assert optimisation_refusal(SlipSurface(polyline=Polyline(
            [Vertex(0, 0), Vertex(1, 1), Vertex(2, 0)]))) is None

    def test_both_doors_ask_it(self):
        import inspect

        from ogr_api.ops import statistics as api_stats
        from ogr_gui import main_window
        assert "optimisation_refusal" in inspect.getsource(api_stats)
        assert "optimisation_refusal" in inspect.getsource(
            main_window.MainWindow)


# ======================================================================
@_requires(_QT)
class TestAddQueryPicksAwayFromTheGrid:
    """D252."""

    def _window(self):
        from test_slide_validation_ej1 import _ej1_project

        from ogr_gui.i18n import set_language
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch

        QApplication.instance() or QApplication([])
        set_language("en")
        p = _ej1_project()
        res = {"bishop_simplified": GridSearch(
            method=BishopSimplified(), grid_x=(70, 100), grid_y=(60, 85),
            grid_nx=3, grid_ny=3, radius_increment=10, min_radius=15,
            num_slices=16, min_area=0.5).run(p)}
        w = InterpretWindow(p, res, None)
        _WINDOWS.append(w)
        return w, res["bishop_simplified"]

    def test_a_pick_on_a_surface_away_from_the_grid_returns_it(self):
        from ogr_slip2d.interpretation import distance_to_path, surface_path
        w, sr = self._window()
        crit = sr.critical
        path = surface_path(crit)
        x, y = path[len(path) // 2]
        hit = w._surface_at(x, y)
        assert hit is not None
        assert distance_to_path(x, y, surface_path(hit)) < 1e-9

    def test_the_hover_preview_does_not_raise(self):
        w, sr = self._window()
        x, y = sr.critical.slices[0].base_x_left + 0.5, 30.0
        w._hover_for_query(x, y)          # raised AttributeError until 0.1.252
