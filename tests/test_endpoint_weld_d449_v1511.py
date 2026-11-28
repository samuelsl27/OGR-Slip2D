# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D449 (v0.1.511) — a thin layer between two contacts is a region again, and
when the weld still joins two contacts the window and the agent say so.

The invariant
-------------
Until OGR Core 0.2.14 the region builder's endpoint weld jumped an end that
was already ON a segment of the External to a vertex within its tolerance
(0.8 % of the model's diagonal), and two contacts drawn almost parallel
lost the layer between them without a word: in a block of 100 × 30, any
layer under 0.9 m (measured with 0.1.462 by the bench's
``_auditoria/P10_D449/reproducir_d449.py``; with 0.1.503 the census of the
bench, ``medir_regla_a.py``, found it in the Talbingo dam, 02/005 and 006,
whose filter of 497.35 m² was lost). The core keeps such an end where it is
(rule A) and notes the contacts it still joins (rule C,
``rules.contacts_welded``): an end on nothing, a contact drawn past the
External. Here, through this program:

* the block with its two contacts ending ON the External keeps the thin
  layer: three regions, the layer's area 100 × 0.5 = 50 m² (the closed form,
  to 1e-5 relative: the core's faces do not tile the External to the last
  bit, its changelog says), and nothing is said;
* drawn past the External, the layer is joined away, and the window's status
  bar says which two boundaries were joined and where, once for the same
  joins; ``project_validate`` warns with ``rule.contacts_welded``;
* a boundary edit starts the check (the debounce timer), so it is said at
  the edit and not only at opening.

Cost: arithmetic and a few region builds of a two-contact block, and one
MainWindow for the file.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_W: list = []
_SEP = 0.5


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


def _block(past: bool):
    """The ficha's block: 100 × 30, two contacts 0.5 m apart at y = 10,
    ending on the External (``past=False``) or 5 m past it."""
    from ogr_core.geometry import Boundary, BoundaryType as BT
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("D449")
    e = Polyline(vertices=[Vertex(0, 0), Vertex(100, 0), Vertex(100, 30),
                           Vertex(0, 30)], closed=True)
    e.ensure_ccw()
    p.add_boundary(Boundary(polyline=e, btype=BT.EXTERNAL))
    p.materials = [Material(name=n, unit_weight=20.0, strength=MohrCoulomb(
        cohesion=5.0, friction_angle=30.0)) for n in ("Thin", "Upper", "Lower")]
    x0, x1 = (-5.0, 105.0) if past else (0.0, 100.0)
    for y in (10.0, 10.0 - _SEP):
        p.add_boundary(Boundary(btype=BT.MATERIAL, polyline=Polyline(
            vertices=[Vertex(x0, y), Vertex(x1, y)])))
    return p


def _areas(p):
    from ogr_core.geometry.regions import _ring_centroid
    return sorted(abs(_ring_centroid(r.polygon.vertices)[2])
                  for r in p.resolve_regions())


def _attach(p):
    w = _window()
    w._attach_project(p)
    w.command_stack.clear()
    w.statusBar().clearMessage()
    w._welds_said = ()
    return w


def _validate_codes(p):
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        h = ws.add(p)
        v = call(ws, "project_validate", project_id=h.id)
    finally:
        ws.shutdown()
    return [c["code"] for c in v.get("warning_codes", [])]


class TestEndingOnTheExternal:

    def test_the_thin_layer_is_a_region(self):
        areas = _areas(_block(past=False))
        assert len(areas) == 3, areas
        want = 100.0 * _SEP
        assert abs(areas[0] - want) <= 1e-5 * want, areas

    def test_nothing_is_said(self):
        p = _block(past=False)
        w = _attach(p)
        assert not w._say_welded_contacts()
        assert w.statusBar().currentMessage() == ""
        assert "rule.contacts_welded" not in _validate_codes(_block(False))


class TestDrawnPastTheExternal:

    def test_the_premise_the_layer_is_joined_away(self):
        assert len(_areas(_block(past=True))) == 2

    def test_the_bar_says_which_two_and_only_once(self):
        w = _attach(_block(past=True))
        assert w._say_welded_contacts()
        msg = w.statusBar().currentMessage()
        assert msg.startswith("The material boundaries Material Boundary #1 "
                              "and Material Boundary #2 end 0.500 m apart"), \
            msg
        w.statusBar().clearMessage()
        assert not w._say_welded_contacts(), "said once for the same joins"

    def test_project_validate_warns(self):
        assert "rule.contacts_welded" in _validate_codes(_block(past=True))


class TestAnEditStartsTheCheck:

    def test_adding_a_boundary_starts_the_timer(self):
        from ogr_core.geometry import Boundary, BoundaryType as BT
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.project.commands import AddBoundaryCommand
        w = _attach(_block(past=False))
        w._weld_timer.stop()
        w.command_stack.do(w.project, AddBoundaryCommand(boundary=Boundary(
            btype=BT.MATERIAL, polyline=Polyline(
                vertices=[Vertex(0, 20), Vertex(100, 20)]))))
        try:
            assert w._weld_timer.isActive()
        finally:
            w._weld_timer.stop()
