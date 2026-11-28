# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D445 (v0.1.509) — a ``.ogr`` with repeated ids opens saying so, at the
window and at the agent, and Delete takes away the boundary picked, one.

The invariant
-------------
Until OGR Core 0.2.14 ``Project.from_dict`` accepted without a word two
boundaries with one ``Boundary.id``, two with one ``Polyline.id`` (every
file with a Copy Boundary saved between 0.1.59 and 0.1.455, D425) and two
user surfaces with one id; and Delete in the window took away both
boundaries of an id, Undo giving back one (measured with 0.1.485 by the
bench's ``_auditoria/P10_D445/medir_d445.py``: 0 of 2 left, 1 of 2 back).
The core now notes them on reading (``Project.read_notes``), renews the
repeated polyline id, and removes by identity. Here, the program's half:

* opening such a file in the window says what the reading noted, on the
  status bar, and the file still opens (never a refusal);
* the agent's ``project_open`` returns them as ``read_notes``, with their
  codes, and ``project_validate`` warns of the boundary ids still shared
  (``rule.duplicate_boundary_id``: they are NOT renewed, the links read
  them);
* the window's Delete on one of two boundaries sharing an id leaves the
  other, and Undo gives it back in its place;
* the control: the demo slope, saved and opened, says nothing of ids.

The cost: one MainWindow for the file, two small files in a temporary folder.
"""
from __future__ import annotations

import copy
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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


def _twins():
    """The demo slope with a material boundary copied the way 0.1.59-0.1.455
    copied it: both ids kept (``Boundary.id`` and ``Polyline.id``)."""
    from ogr_core.geometry import Boundary, BoundaryType as BT
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    a = Boundary(btype=BT.MATERIAL, polyline=Polyline(
        [Vertex(0.0, 5.0), Vertex(30.0, 5.0)]))
    p.add_boundary(a)
    b = copy.deepcopy(a)
    b.polyline.vertices = [Vertex(v.x, v.y + 2.0) for v in b.polyline.vertices]
    p.add_boundary(b)
    return p, a


def _saved(p, tmp) -> Path:
    path = Path(tmp) / "twins.ogr"
    p.save(path)
    return path


class TestOpeningAtTheWindow:

    def test_the_bar_says_what_the_reading_noted(self):
        p, a = _twins()
        w = _window()
        with tempfile.TemporaryDirectory() as tmp:
            w._open_path(_saved(p, tmp))
        msg = w.statusBar().currentMessage()
        assert "share the id '%s'" % a.id in msg, msg
        assert "shared the polyline id '%s'" % a.polyline.id in msg, msg
        mats = [b for b in w.project.boundaries if b.id == a.id]
        assert len(mats) == 2, "it opens, both boundaries kept"
        assert mats[0].polyline.id != mats[1].polyline.id, "renewed"

    def test_the_control_the_demo_says_nothing_of_ids(self):
        from ogr_core.project.demo import build_demo_project
        w = _window()
        with tempfile.TemporaryDirectory() as tmp:
            w._open_path(_saved(build_demo_project(), tmp))
        assert w.project.read_notes == []
        assert "id" not in w.statusBar().currentMessage()


class TestDeleteAtTheWindow:

    def test_one_of_two_and_undo_gives_it_back_in_its_place(self):
        p, a = _twins()
        w = _window()
        w._attach_project(p)
        w.command_stack.clear()
        twins = [b for b in w.project.boundaries if b.id == a.id]
        second = twins[1]
        at = w.project.boundaries.index(second)
        w._do_delete_boundary(at)
        left = [b for b in w.project.boundaries if b.id == a.id]
        assert left == [twins[0]] and left[0] is twins[0]
        w.command_stack.undo(w.project)
        assert w.project.boundaries[at] is second
        assert len([b for b in w.project.boundaries if b.id == a.id]) == 2


class TestAtTheAgent:

    def test_project_open_and_validate(self):
        from ogr_api import Workspace, call
        p, a = _twins()
        ws = Workspace()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = _saved(p, tmp)
                out = call(ws, "project_open", path=str(path))
            codes = [c["code"] for c in out.get("warning_codes", [])]
            assert "rule.duplicate_boundary_id" in codes, out
            assert "rule.polyline_id_renewed" in codes, out
            assert any(a.id in n for n in out["read_notes"])
            v = call(ws, "project_validate", project_id=out["project_id"])
            vcodes = [c["code"] for c in v.get("warning_codes", [])]
            assert "rule.duplicate_boundary_id" in vcodes, v
            # renewed on reading: nothing left to say of the polyline id
            assert "rule.polyline_id_renewed" not in vcodes, v
        finally:
            ws.shutdown()
