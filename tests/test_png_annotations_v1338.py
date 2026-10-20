# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.338 (D336, first part) — the PNG an agent renders draws the annotation
layer.

``render_png`` (the ``model_render`` tool) drew the model and its surfaces,
and not what the user had drawn on it. It draws the layer now, from the
primitives the canvas and the DXF export draw from
(``ogr_core.annotations.drawing``), through ``ogr_api.render_annotations``.

The invariants:

* **a filled shape appears in its pixels**: a rectangle of a colour no other
  thing on the picture has, filled solid, covers pixels of that colour, and
  none with the layer off or the rectangle hidden (rule 7: the option moves
  the picture), through ``render_png`` and through the ``model_render``
  operation;
* the labels are the primitives' labels — a dimension's value, the axes'
  coordinates;
* a mark keeps its size in pixels (an arrow head is ``ARROW_PX`` whatever
  the figure's extent), as on the canvas;
* **the picture keeps the model's framing**: an annotation far outside it
  leaves the PNG byte for byte the PNG without annotations;
* an image is drawn, and one whose file is missing is its frame;
* no adapter computes geometry of its own: none of the three (canvas, DXF,
  PNG) calls ``outline``, ``measured_value`` or ``nice_step``.
"""
from __future__ import annotations

import ast
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[1]
GREEN = "#00ff7f"
GREEN_RGB = (0.0, 1.0, 127 / 255.0)


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


def _K():
    from ogr_core.annotations import AnnotationKind
    return AnnotationKind


def _pixels_of(png: bytes, rgb, tol=0.02) -> int:
    import matplotlib.image as mpimg
    import numpy as np
    img = mpimg.imread(io.BytesIO(png))[..., :3]
    return int(np.all(np.abs(img - np.array(rgb)) < tol, axis=-1).sum())


def _green_rectangle(**style):
    # inside the slope, which the picture frames
    return _ann(_K().RECTANGLE, [(2.0, 2.0), (12.0, 8.0)],
                colour=GREEN, fill=GREEN, fill_opacity=1.0, **style)


# ======================================================================
class TestAFilledShapeAppears:

    def test_in_render_png(self):
        from ogr_api.render import render_png
        png = render_png(_project(_green_rectangle()))
        assert _pixels_of(png, GREEN_RGB) > 500

    def test_not_with_the_layer_off(self):
        from ogr_api.render import render_png
        png = render_png(_project(_green_rectangle()), annotations=False)
        assert _pixels_of(png, GREEN_RGB) == 0

    def test_not_when_hidden(self):
        from ogr_api.render import render_png
        png = render_png(_project(_green_rectangle(visible=False)))
        assert _pixels_of(png, GREEN_RGB) == 0

    def test_through_the_operation(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="png")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [50, 0], [50, 15], [35, 15], [25, 25],
                             [0, 25]],
                "materials": [{"name": "Soil", "unit_weight": 20.0,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {"cohesion": 5.0,
                                                       "friction_angle":
                                                           30.0}}}]})
            call(ws, "annotation_set", project_id=pid, kind="rectangle",
                 points_xy=[[2, 2], [12, 8]],
                 style={"colour": GREEN, "fill": GREEN, "fill_opacity": 1.0})
            on = call(ws, "model_render", project_id=pid)["png"]
            off = call(ws, "model_render", project_id=pid,
                       annotations=False)["png"]
        finally:
            ws.shutdown()
        assert _pixels_of(on, GREEN_RGB) > 500
        assert _pixels_of(off, GREEN_RGB) == 0


class TestTheLabelsAndMarks:

    def _drawn(self, *annotations):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from ogr_api.render_annotations import draw_annotations
        fig = Figure(figsize=(9, 6), dpi=100)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        ax.set_xlim(-5, 60)
        ax.set_ylim(-5, 45)
        return ax, draw_annotations(ax, _project(*annotations))

    def test_the_labels_are_the_primitives_labels(self):
        from matplotlib.text import Text
        from ogr_core.annotations import drawing as d
        K = _K()
        dims = _ann(K.DIMENSION_LENGTH, [(0, 0), (50, 0)])
        axes = _ann(K.AXES, [(0, 0), (50, 25)])
        _ax, artists = self._drawn(dims, axes)
        drawn = sorted(a.get_text() for a in artists if isinstance(a, Text))
        want = sorted(p.text for a in (dims, axes) for p in d.primitives(a)
                      if isinstance(p, d.Label))
        assert drawn == want and "50.000" in drawn

    def test_an_arrow_head_keeps_its_size_in_pixels(self):
        from matplotlib.patches import PathPatch
        from ogr_core.annotations.drawing import ARROW_PX
        ax, artists = self._drawn(_ann(_K().ARROW, [(2, 30), (40, 30)]))
        heads = [a for a in artists if isinstance(a, PathPatch)]
        assert len(heads) == 1
        ext = heads[0].get_path().get_extents()
        want = ARROW_PX * ax.figure.dpi / 96.0
        assert abs(ext.width - want) < 1e-9, (ext.width, want)


class TestTheFraming:

    def test_a_far_annotation_leaves_the_picture_as_it_was(self):
        from ogr_api.render import render_png
        far = _ann(_K().LINE, [(900.0, 900.0), (1000.0, 1000.0)])
        with_far = render_png(_project(far))
        without = render_png(_project(), annotations=False)
        assert with_far == without


class TestTheImage:

    def test_an_image_is_drawn(self):
        import matplotlib.image as mpimg
        import numpy as np
        from ogr_api.render import render_png
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "pic.png")
            mpimg.imsave(path, np.full((20, 30, 3), GREEN_RGB))
            # in the air over the toe, inside the frame: nothing covers it
            png = render_png(_project(_ann(_K().IMAGE, [(36, 16), (48, 24)],
                                           path)))
        assert _pixels_of(png, GREEN_RGB, tol=0.03) > 500

    def test_a_missing_image_is_its_frame(self):
        from matplotlib.text import Text
        ax, artists = TestTheLabelsAndMarks()._drawn(
            _ann(_K().IMAGE, [(0, 0), (10, 10)], "C:/no/such/picture.png"))
        assert [a.get_text() for a in artists
                if isinstance(a, Text)] == ["picture.png"]


class TestNoAdapterComputesGeometry:

    def test_none_calls_the_geometry_itself(self):
        adapters = ("ogr_gui/canvas/annotation_items.py",
                    "ogr_core/dxf/annotation_export.py",
                    "ogr_api/render_annotations.py")
        bad = []
        for rel in adapters:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            for n in ast.walk(tree):
                if isinstance(n, ast.Call):
                    f = n.func
                    name = f.attr if isinstance(f, ast.Attribute) \
                        else getattr(f, "id", "")
                    if name in ("outline", "measured_value", "nice_step"):
                        bad.append((rel, n.lineno, name))
        assert bad == [], bad
