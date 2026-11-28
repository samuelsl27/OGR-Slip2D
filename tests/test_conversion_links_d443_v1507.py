# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D443 (v0.1.507) — converting or deleting a boundary takes the links of the
materials with it, by the core's rule, at both doors, and says so.

The invariant
-------------
Until v0.1.506 ``convert_boundary`` kept the id and the materials kept their
``water_surface_id`` and ``anisotropic_surface_id``, while their readers
filter by type: the demo slope's water table made a piezometric line left u
at (25; 0.5) at 0 kPa, where it was 73.6, at the window and at the agent,
and nothing said so (measured with 0.1.455 by the bench's
``_auditoria/P10_D443_D444/medir_d443_d444.py``); the window's Delete left
the links pointing at a boundary that was gone. Now both doors ask the
core's rule (OGR Core 0.2.14, the owner's decision B):

* a water table into a piezometric line keeps the link and the material's
  pore-pressure model follows (``PIEZO_LINE``): u at (25; 0.5) is again the
  hydrostatic head under the horizontal line, γw·(8 − 0.5) = 73.6 kPa, the
  closed form of the core's own test; the bar and the agent's notes say the
  materials now read it as a Piezometric Line;
* a water table into a material boundary clears the link (no reader), as
  deleting it does, and says so with the deletion's sentence;
* the window's Delete clears the links and says so, in the same undo step:
  Undo gives back the boundary AND the material's link;
* ``project_validate`` warns of a link an old file brings to a boundary of a
  type that does not read it (``rule.stale_water_link``).

The cost: one MainWindow for the file, and arithmetic.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_GAMMA_W = 9.81
_POINT = (25.0, 0.5)
_W: list = []


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


def _demo():
    from ogr_core.geometry import BoundaryType as BT
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    wt = next(b for b in p.boundaries if b.btype == BT.WATER_TABLE)
    return p, wt


def _attach(p):
    w = _window()
    w._attach_project(p)
    w.command_stack.clear()
    w.ogr_status.clearMessage()
    return w


def _u(p):
    from ogr_core.geometry import Vertex
    from ogr_core.hydraulic.pore_pressure import pore_pressure_at
    return pore_pressure_at(p, Vertex(*_POINT), p.materials[0])


def _water_level(wt):
    ys = {round(v.y, 9) for v in wt.polyline.vertices}
    assert len(ys) == 1, "the premise: the demo's water table is level"
    return ys.pop()


def _agent(p, **kw):
    """``boundary_edit`` with ``kw`` on ``p``: (its output, the project)."""
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        h = ws.add(p)
        return call(ws, "boundary_edit", project_id=h.id, **kw), h.project
    finally:
        ws.shutdown()


def _validate(p) -> list:
    """The codes of ``project_validate``'s warnings on ``p``."""
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        h = ws.add(p)
        v = call(ws, "project_validate", project_id=h.id)
    finally:
        ws.shutdown()
    return [w.get("code") for w in v.get("warning_codes", [])]


class TestAWaterTableMadeAPiezometricLine:

    def test_the_premise_before_the_conversion(self):
        p, wt = _demo()
        level = _water_level(wt)
        assert abs(_u(p) - _GAMMA_W * (level - _POINT[1])) < 1e-9
        assert p.materials[0].water_surface_id == wt.id

    def test_at_the_window_the_pressure_follows_and_the_bar_says_it(self):
        from ogr_core.geometry import BoundaryType as BT
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        level = _water_level(wt)
        w = _attach(p)
        w._apply_conversion(wt, BT.PIEZOMETRIC)
        q = w.project
        m = q.materials[0]
        assert m.pore_pressure == PP.PIEZO_LINE
        assert m.water_surface_id == wt.id
        assert abs(_u(q) - _GAMMA_W * (level - _POINT[1])) < 1e-9, _u(q)
        msg = w.ogr_status.currentMessage()
        assert "now read it as a Piezometric Line: " + m.name in msg, msg

    def test_undo_gives_back_the_boundary_and_the_model(self):
        from ogr_core.geometry import BoundaryType as BT
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        before = _u(p)
        w = _attach(p)
        w._apply_conversion(wt, BT.PIEZOMETRIC)
        w.command_stack.undo(w.project)
        q = w.project
        assert q.materials[0].pore_pressure == PP.WATER_TABLE
        assert any(b.btype == BT.WATER_TABLE for b in q.boundaries)
        assert _u(q) == before

    def test_at_the_agent_the_same_and_its_note(self):
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        level = _water_level(wt)
        out, h = _agent(p, boundary=wt.id, op="change_type",
                        new_type="piezometric")
        q = h
        assert q.materials[0].pore_pressure == PP.PIEZO_LINE
        assert abs(_u(q) - _GAMMA_W * (level - _POINT[1])) < 1e-9
        assert any("now read it as a Piezometric Line" in n
                   for n in out["notes"]), out["notes"]


class TestAConversionWithNoReaderClearsTheLink:

    def test_at_the_window(self):
        from ogr_core.geometry import BoundaryType as BT
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        w = _attach(p)
        w._apply_conversion(wt, BT.MATERIAL)
        m = w.project.materials[0]
        assert m.pore_pressure == PP.NONE and m.water_surface_id is None
        assert _u(w.project) == 0.0
        assert ("Materials that used it now have no water surface: "
                + m.name) in w.ogr_status.currentMessage()

    def test_at_the_agent(self):
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        out, h = _agent(p, boundary=wt.id, op="change_type",
                        new_type="material")
        m = h.materials[0]
        assert m.pore_pressure == PP.NONE and m.water_surface_id is None
        assert out["notes"][-1] == (
            "Materials that used it now have no water surface: " + m.name)


class TestDeleteAtTheWindow:

    def test_it_clears_the_link_and_says_so(self):
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        w = _attach(p)
        w._do_delete_boundary(w.project.boundaries.index(wt))
        m = w.project.materials[0]
        assert wt not in w.project.boundaries
        assert m.water_surface_id is None and m.pore_pressure == PP.NONE
        msg = w.ogr_status.currentMessage()
        assert msg.endswith("now have no water surface: " + m.name), msg

    def test_one_undo_gives_back_both(self):
        from ogr_core.materials import PorePressureType as PP
        p, wt = _demo()
        before = _u(p)
        w = _attach(p)
        w._do_delete_boundary(w.project.boundaries.index(wt))
        w.command_stack.undo(w.project)
        q = w.project
        assert wt in q.boundaries
        assert q.materials[0].water_surface_id == wt.id
        assert q.materials[0].pore_pressure == PP.WATER_TABLE
        assert _u(q) == before
        assert not w.command_stack.can_undo     # ONE step

    def test_the_agents_delete_says_the_same(self):
        p, wt = _demo()
        out, h = _agent(p, boundary=wt.id, op="delete")
        assert out["notes"] == [
            "Materials that used it now have no water surface: "
            + h.materials[0].name]


class TestAnOldFileIsWarned:

    def test_project_validate(self):
        from ogr_core.geometry import BoundaryType as BT
        p, wt = _demo()
        # what a conversion before this version left: the type changed and
        # the link kept
        wt.btype = BT.MATERIAL
        assert "rule.stale_water_link" in _validate(p)

    def test_the_control_a_fresh_model_has_none(self):
        p, _wt = _demo()
        assert "rule.stale_water_link" not in _validate(p)
