# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.332 (D329b) — the four water layers of Interpret draw what they say.

The defect (D329, found planning P8i): *Groundwater → Phreatic Surface /
Piezometric Lines / Flow Vectors / Streamlines* were check boxes with
nothing connected; ticking them changed nothing (rule 7). Streamlines
existed nowhere.

What these tests protect, on the first worked example with a water table
and a piezometric line added, and — for the finite-element layers — with
the seepage field of ``test_interpret_i3_v153`` solved on it:

* each box moves the drawing, on and off;
* the phreatic surface is the free surface of the finite-element result
  (the same points the solver's own method gives: the method now calls a
  function of the mesh and the result), or, without a result, the model's
  water table;
* the piezometric lines are the model's;
* the vectors are one per element drawn, along its Darcy velocity;
* the streamlines are those of ``ogr_fem2d.solvers.streamlines``, validated
  in ``test_streamlines_v1332``;
* without a finite-element result the two layers that need one are
  disabled, and say why.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_WINDOWS: list = []


def _with_water(project):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    xs = [v.x for v in project.external_boundary().vertices]
    x0, x1 = min(xs), max(xs)
    for btype, y in ((BoundaryType.WATER_TABLE, 30.0),
                     (BoundaryType.PIEZOMETRIC, 35.0)):
        project.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(x0, y), Vertex(x1, y)]),
            btype=btype))
    return project


def _window(seepage):
    import test_interpret_i3_v153 as i3
    from test_slide_validation_ej1 import _ej1_project
    p = i3.TestGroundwaterEntries()._with_seepage() if seepage \
        else _ej1_project()
    _with_water(p)
    _p, _r, w = i3._interpret(p)
    _WINDOWS.append(w)
    # no canvas.refresh_scene() here: on Interpret's canvas it drops the
    # surfaces of the result, which the next redraw of a layer puts back,
    # and every count after it would differ by them
    QApplication.processEvents()
    return w


def _count(w):
    QApplication.processEvents()
    return len(w.canvas.scene().items())


class TestEveryLayerMovesTheDrawing:
    def test_with_a_finite_element_result(self):
        w = _window(seepage=True)
        try:
            for act, starts_on in ((w._act_gw_phreatic, True),
                                   (w._act_gw_piezo, True),
                                   (w._act_gw_vectors, False),
                                   (w._act_gw_streams, False)):
                assert act.isEnabled(), act.text()
                assert act.isChecked() is starts_on, act.text()
                before = _count(w)
                act.setChecked(not starts_on)
                after = _count(w)
                assert after != before, act.text()
                act.setChecked(starts_on)
                assert _count(w) == before, act.text()
        finally:
            w.close()

    def test_without_one(self):
        w = _window(seepage=False)
        try:
            for act in (w._act_gw_phreatic, w._act_gw_piezo):
                before = _count(w)
                act.setChecked(not act.isChecked())
                assert _count(w) != before, act.text()
                act.setChecked(not act.isChecked())
                assert _count(w) == before, act.text()
            # no field to draw: the two that need one say so
            for act in (w._act_gw_vectors, w._act_gw_streams):
                assert not act.isEnabled(), act.text()
                assert act.statusTip().startswith("Requires"), act.text()
        finally:
            w.close()


class TestWhatTheyDraw:
    def test_the_phreatic_surface_is_the_results(self):
        from ogr_fem2d.solvers import UnsaturatedSeepageSolver
        from ogr_fem2d.solvers.seepage import free_surface_points
        from ogr_core.annotations import AnnotationKind
        w = _window(seepage=True)
        try:
            mesh, result = w._seepage_field()
            props = {m.id: m.hydraulic for m in w.project.materials}
            solver = UnsaturatedSeepageSolver(mesh, props)
            points = free_surface_points(mesh, result)
            assert len(points) >= 2
            # the method and the function are one computation
            assert solver.free_surface_points(result) == points
            drawn = [a for a in w._water_overlays()
                     if a.kind == AnnotationKind.POLYLINE
                     and a.style.line_style == "dash"]
            assert len(drawn) == 1 and drawn[0].points == list(points)
        finally:
            w.close()

    def test_the_vectors_follow_the_element_velocity(self):
        from ogr_core.annotations import AnnotationKind
        w = _window(seepage=True)
        try:
            w._act_gw_vectors.setChecked(True)
            mesh, result = w._seepage_field()
            arrows = [a for a in w._water_overlays()
                      if a.kind == AnnotationKind.ARROW]
            assert arrows
            centroids = {e.centroid(mesh): e.id for e in mesh.elements}
            for a in arrows:
                (cx, cy), (tx, ty) = a.points
                vx, vy = result.velocity[centroids[(cx, cy)]]
                dx, dy = tx - cx, ty - cy
                sine = abs(dx * vy - dy * vx) / (math.hypot(dx, dy)
                                                 * math.hypot(vx, vy))
                assert sine < 1e-9 and dx * vx + dy * vy > 0
        finally:
            w.close()

    def test_the_streamlines_are_the_tracers(self):
        from ogr_core.annotations import AnnotationKind
        from ogr_fem2d.solvers.streamlines import streamlines
        w = _window(seepage=True)
        try:
            w._act_gw_streams.setChecked(True)
            mesh, result = w._seepage_field()
            expected = streamlines(mesh, result.velocity, count=12)
            assert expected
            drawn = [a.points for a in w._water_overlays()
                     if a.kind == AnnotationKind.POLYLINE
                     and a.style.line_style != "dash"]
            assert drawn == expected
        finally:
            w.close()
