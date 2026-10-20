# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.341 (D337, second part) — the DXF exporter draws plain geometry.

``export_dxf`` took the search results and asked the engine's surface
classes (``CompositeSurface``, ``SlipCircle``, ``WeakLayerSurface``) which
kind each critical surface was: the core imported the engine. The rule that
turns a result into points moved up, word for word, to
``ogr_slip2d.interpretation`` (``drawing_points``, ``critical_drawings``),
and the exporter draws the ``(label, points, fos)`` it is given.

The invariants:

* **the exporter draws what it is given**: a polyline of exactly those
  points on the surface layer and the label with its factor, and a drawing
  without points is left out and said, with the layer still made — the
  report and the layers are those of v0.1.340;
* **the core exports without the engine**: in a fresh interpreter, a model
  is written with a critical surface and neither ``ogr_slip2d`` nor
  ``ogr_fem2d`` is ever imported;
* **the rule is the old one, recomputed here from its definition**: a
  circle is the left end of every slice base and the right end of the last
  (not :func:`surface_path`, which differs when the slices are not
  contiguous), a weak-layer surface its drawing vertices, a polyline its
  vertices, an unknown class nothing with its class name;
* a mapping of results passed where the drawings go is refused with its
  remedy, rather than drawn as nothing;
* the census of ``test_core_layering_v1340`` loses the exporter's entry.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

try:
    import ezdxf  # noqa: F401
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False


def _requires(flag):
    def deco(cls):
        return cls if flag else type(cls.__name__, (), {})
    return deco


def _entities(path):
    import ezdxf as _ezdxf
    doc = _ezdxf.readfile(str(path))
    polylines = [[(x, y) for x, y, *_ in e.get_points()]
                 for e in doc.modelspace()
                 if e.dxf.layer == "OGR_X_SLIP_SURFACE"]
    texts = [e.dxf.text for e in doc.modelspace() if e.dxftype() == "TEXT"]
    layers = {layer.dxf.name for layer in doc.layers}
    return polylines, texts, layers


# ======================================================================
@_requires(_HAS_EZDXF)
class TestTheExporterDrawsWhatItIsGiven:

    def test_points_label_and_a_surface_it_cannot_draw(self):
        from ogr_core.dxf.exporter import ExportOptions, export_dxf
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        pts = [(5.0, 10.0), (12.5, 6.25), (20.0, 8.0), (30.0, 14.0)]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "d.dxf"
            rep = export_dxf(p, out, ExportOptions(unit="m"), [
                ("method_a", pts, 1.23456),
                ("method_b", None, 1.5, "OddSurface")])
            polylines, texts, layers = _entities(out)
        assert polylines == [pts]
        assert "method_a  FS = 1.2346" in texts
        assert rep.skipped == ["method_b critical surface (OddSurface)"]
        assert rep.entities.get("OGR_X_SLIP_SURFACE") == 1
        assert "OGR_X_SLIP_SURFACE" in layers

    def test_a_mapping_of_results_is_refused_with_its_remedy(self):
        from ogr_core.dxf.exporter import ExportOptions, export_dxf
        from ogr_core.project.demo import build_demo_project
        with tempfile.TemporaryDirectory() as tmp:
            try:
                export_dxf(build_demo_project(), Path(tmp) / "x.dxf",
                           ExportOptions(unit="m"),
                           {"bishop_simplified": SimpleNamespace()})
            except TypeError as exc:
                assert "critical_drawings" in str(exc)
            else:
                raise AssertionError("a mapping of results was accepted")


# ======================================================================
@_requires(_HAS_EZDXF)
class TestTheCoreExportsWithoutTheEngine:

    def test_in_a_fresh_interpreter(self):
        script = (
            "import sys, tempfile, pathlib\n"
            "from ogr_core.project.demo import build_demo_project\n"
            "from ogr_core.dxf.exporter import ExportOptions, export_dxf\n"
            "out = pathlib.Path(tempfile.mkdtemp()) / 'x.dxf'\n"
            "rep = export_dxf(build_demo_project(), out,\n"
            "                 ExportOptions(unit='m'),\n"
            "                 [('m', [(0.0, 0.0), (10.0, -2.0)], 1.1)])\n"
            "assert rep.ok and out.exists(), rep.error\n"
            "print(sorted(m for m in sys.modules\n"
            "             if m.split('.')[0] in ('ogr_slip2d', 'ogr_fem2d')))\n")
        env = dict(os.environ, PYTHONPATH=str(_ROOT),
                   QT_QPA_PLATFORM="offscreen")
        out = subprocess.run([sys.executable, "-c", script], cwd=str(_ROOT),
                             env=env, capture_output=True, text=True,
                             timeout=300)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "[]", out.stdout


# ======================================================================
def _grid_result():
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    import test_dxf_export_v148 as V148
    p = V148._model()
    r = GridSearch(method=BishopSimplified(), grid_x=(70, 100),
                   grid_y=(60, 85), grid_nx=4, grid_ny=4,
                   radius_increment=8, min_radius=15, num_slices=18,
                   min_area=0.5).run(p)
    return p, r


class TestTheRuleIsTheOldOne:

    def test_a_circle_is_the_left_end_of_each_base_and_the_last_right(self):
        from ogr_slip2d.interpretation import drawing_points
        _p, r = _grid_result()
        crit = r.critical
        sl = list(crit.slices)
        expected = ([(s.base_x_left, s.base_y_left) for s in sl]
                    + [(sl[-1].base_x_right, sl[-1].base_y_right)])
        assert drawing_points(crit) == expected

    def test_a_weak_layer_surface_is_its_drawing_vertices(self):
        import test_weak_layer_drawing_v1252 as V1252
        from ogr_slip2d.interpretation import drawing_points
        _p, r = V1252._planar_critical()
        assert drawing_points(r) == r.surface.drawing_vertices()

    def test_a_polyline_is_its_vertices(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.interpretation import drawing_points
        from ogr_slip2d.surface import SlipSurface
        verts = [Vertex(0.0, 10.0), Vertex(8.0, 4.0), Vertex(20.0, 9.0)]
        res = SimpleNamespace(surface=SlipSurface(
            polyline=Polyline(vertices=verts)))
        assert drawing_points(res) == [(0.0, 10.0), (8.0, 4.0), (20.0, 9.0)]

    def test_an_unknown_class_is_none_and_keeps_its_name(self):
        from ogr_slip2d.interpretation import critical_drawings
        odd = SimpleNamespace(critical=SimpleNamespace(
            surface=SimpleNamespace(), fos=1.25))
        none = SimpleNamespace(critical=None)
        assert critical_drawings({"odd": odd, "none": none}) == [
            ("odd", None, 1.25, "SimpleNamespace")]

    def test_the_drawings_of_a_search_are_its_critical_surface(self):
        from ogr_slip2d.interpretation import critical_drawings, drawing_points
        _p, r = _grid_result()
        assert critical_drawings({"bishop_simplified": r}) == [
            ("bishop_simplified", drawing_points(r.critical), r.critical.fos)]


# ======================================================================
class TestTheCensusLosesTheExporter:

    def test_the_exporter_imports_nothing_above(self):
        from collections import Counter

        import test_core_layering_v1340 as L
        found = L.census_of(_ROOT / "ogr_core" / "dxf" / "exporter.py", _ROOT)
        assert found == Counter()
        assert not any(k[0] == "ogr_core/dxf/exporter.py" for k in L.ALLOWED)
