# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D425 (v0.1.456) — a copied boundary carries two ids of its own.

The invariant
-------------
A boundary carries two ids: its own (``Boundary.id``, what materials, undo
and the agent resolve) and its polyline's (``Polyline.id``, written to the
``.ogr``). Each names one object of the model, so no id repeats after a
copy. The window's Copy Boundary renewed only ``Boundary.id`` (since
v0.1.59): measured with v0.1.455 on the demo slope with a material lens and
a piezometric line added (the water table and the External are not copied
since D410), copying the two left 6 boundaries with 6 ``Boundary.id`` and 4
``Polyline.id``, and saving and opening kept them. The agent's copy renewed
both (since v0.1.196, ``tests/test_f2_ops_v1196.py``). Nothing resolves a
boundary by its ``Polyline.id``: it is written to the file and so enters the
document's hash (the stale result, the unsaved changes, the undo check
shared with the agent), and before this version two lines of the source set
it on an edit, both keeping it. So no number moves: it is an invariant
broken, two objects with one id.

Now both ask the core's copy, ``ogr_core.geometry.transforms.copy_boundary``:
``translate`` plus the two ids new. Each keeps its own offset (the window
2, 2; the agent its ``dx`` and ``dy``).

The reference (rule 1)
----------------------
An identity: ``len(set(ids)) == len(ids)`` for both ids, in the model and
after ``to_dict`` and ``from_dict``, also after copying one boundary twice
and copying a copy. The control: the copy is the original shifted vertex by
vertex and equal in every other field, the original untouched, undo takes
it away, and a move (``translate``), which is the same boundary moved, keeps
both ids.

One window for the file, no dialog executed. Measured: about 2 s for the
file in the runner, most of it building the window.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except ImportError:  # pragma: no cover
    _HAS_QT = False

_WINDOW: list = []


def _window(project):
    """The file's one window, on ``project`` (a fresh one per case)."""
    if not _WINDOW:
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        w.PROMPT_ASSIGN_ON_DRAW = False
        _WINDOW.append(w)
    w = _WINDOW[0]
    w._attach_project(project)
    w.command_stack.clear()
    w.ogr_status.clearMessage()
    return w


def _project():
    """The demo slope with a material lens and a piezometric line: two
    boundaries the rule of their type lets copy (D410)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    lens = Boundary(polyline=Polyline([Vertex(30, 2), Vertex(32, 2),
                                       Vertex(32, 3), Vertex(30, 3)],
                                      closed=True),
                    btype=BoundaryType.MATERIAL,
                    material_id=p.materials[0].id)
    piezo = Boundary(polyline=Polyline([Vertex(0, 12), Vertex(50, 8)]),
                     btype=BoundaryType.PIEZOMETRIC)
    p.add_boundary(lens)
    p.add_boundary(piezo)
    return p, lens, piezo


def _copied(w, orig):
    """Copy ``orig`` in the window; the copy (the boundary added)."""
    before = {id(b) for b in w.project.boundaries}
    w._do_copy_boundary(w.project.boundaries.index(orig))
    new = [b for b in w.project.boundaries if id(b) not in before]
    assert len(new) == 1, (orig.btype, w.ogr_status.currentMessage())
    return new[0]


def _ids(project):
    return ([b.id for b in project.boundaries],
            [b.polyline.id for b in project.boundaries])


def _unique(project):
    bids, pids = _ids(project)
    return len(set(bids)) == len(bids), len(set(pids)) == len(pids)


def _without_ids(b):
    d = b.to_dict()
    d.pop("id")
    d["polyline"] = dict(d["polyline"])
    d["polyline"].pop("id")
    return d


# ======================================================================
class TestIds:

    def test_no_id_repeats_after_a_copy_in_the_model_or_the_file(self):
        if not _HAS_QT:
            return
        from ogr_core.project import Project
        p, lens, piezo = _project()
        w = _window(p)
        copies = [_copied(w, lens), _copied(w, piezo)]
        assert len(w.project.boundaries) == 6
        assert _unique(w.project) == (True, True), _ids(w.project)
        for orig, new in zip((lens, piezo), copies):
            assert new.id != orig.id and new.polyline.id != orig.polyline.id
        reread = Project.from_dict(w.project.to_dict())
        assert _ids(reread) == _ids(w.project)
        assert _unique(reread) == (True, True)

    def test_copying_twice_and_copying_a_copy_repeat_no_id(self):
        # the review of 0.1.456: an id DERIVED from the original's (its id
        # plus a suffix) passed every case above, and two copies of one
        # boundary then shared both ids
        if not _HAS_QT:
            return
        p, lens, _piezo = _project()
        w = _window(p)
        first = _copied(w, lens)
        _copied(w, lens)
        _copied(w, first)
        assert len(w.project.boundaries) == 7
        assert _unique(w.project) == (True, True), _ids(w.project)

    def test_the_agent_copy_has_ids_of_its_own_too(self):
        # the control of the agent's side: what test_f2_ops_v1196 fixes for a
        # line, here for the lens (twice) and the piezometric line, in the
        # model and in the file
        from ogr_api import Workspace, call
        from ogr_core.project import Project
        p, lens, piezo = _project()
        ws = Workspace()
        try:
            pid = ws.add(p).id
            for orig in (lens, lens, piezo):
                out = call(ws, "boundary_edit", project_id=pid,
                           boundary=orig.id, op="copy", dx=2.0,
                           dy=2.0)["boundary"]
                new = next(b for b in p.boundaries if b.id == out["id"])
                assert new.polyline.id != orig.polyline.id
            assert len(p.boundaries) == 7
            assert _unique(p) == (True, True), _ids(p)
            reread = Project.from_dict(p.to_dict())
            assert _ids(reread) == _ids(p)
        finally:
            ws.shutdown()


# ======================================================================
class TestTheCopy:

    def test_the_copy_is_the_original_moved_by_two_and_two(self):
        if not _HAS_QT:
            return
        p, lens, piezo = _project()
        lens.line_width, lens.visible = 2.5, False   # not the defaults
        w = _window(p)
        for orig in (lens, piezo):
            # read before copying, so a copy that touches the original is
            # seen (the review of 0.1.456)
            before = orig.to_dict()
            want = _without_ids(orig)
            want["polyline"]["vertices"] = [
                [x + 2.0, y + 2.0] for x, y in want["polyline"]["vertices"]]
            new = _copied(w, orig)
            assert orig.to_dict() == before
            assert [(v.x, v.y) for v in new.polyline.vertices] == [
                (v.x + 2.0, v.y + 2.0) for v in orig.polyline.vertices]
            assert _without_ids(new) == want

    def test_the_window_and_the_agent_make_the_same_copy(self):
        if not _HAS_QT:
            return
        from ogr_api import Workspace, call
        p, lens, _piezo = _project()
        w = _window(p)
        by_window = _copied(w, lens)
        q, lens_q, _ = _project()
        lens_q.material_id = lens.material_id = None   # the two projects'
        by_window.material_id = None                    # materials differ
        ws = Workspace()
        try:
            out = call(ws, "boundary_edit", project_id=ws.add(q).id,
                       boundary=lens_q.id, op="copy", dx=2.0,
                       dy=2.0)["boundary"]
            by_agent = next(b for b in q.boundaries if b.id == out["id"])
        finally:
            ws.shutdown()
        assert _without_ids(by_window) == _without_ids(by_agent)

    def test_undo_takes_the_copy_away_and_redo_brings_the_same_ids(self):
        if not _HAS_QT:
            return
        p, lens, _piezo = _project()
        w = _window(p)
        before = _ids(w.project)
        new = _copied(w, lens)
        after = _ids(w.project)
        assert w.command_stack.history() == (["Add Material Boundary"], [])
        w.command_stack.undo(w.project)
        assert _ids(w.project) == before
        w.command_stack.redo(w.project)
        assert _ids(w.project) == after
        assert new.polyline.id in after[1]
        assert _unique(w.project) == (True, True)


# ======================================================================
class TestAMoveIsNotACopy:
    """``translate`` is the same boundary moved: both ids stay, as in the
    window's Move and the agent's translate (the edits that keep the ids on
    purpose, which D425 must not move)."""

    def test_the_window_move_keeps_both_ids(self):
        if not _HAS_QT:
            return
        p, lens, _piezo = _project()
        w = _window(p)
        i = w.project.boundaries.index(lens)
        w._do_move_boundary(i, 1.0, 0.5)
        moved = w.project.boundaries[i]
        assert moved is not lens
        assert (moved.id, moved.polyline.id) == (lens.id, lens.polyline.id)
        assert moved.polyline.vertices[0].x == lens.polyline.vertices[0].x + 1.0

    def test_the_agent_translate_keeps_both_ids(self):
        from ogr_api import Workspace, call
        p, lens, _piezo = _project()
        ids = (lens.id, lens.polyline.id)
        ws = Workspace()
        try:
            call(ws, "boundary_edit", project_id=ws.add(p).id,
                 boundary=lens.id, op="translate", dx=1.0)
            moved = next(b for b in p.boundaries if b.id == lens.id)
            assert (moved.id, moved.polyline.id) == ids
        finally:
            ws.shutdown()

    def test_translate_itself_keeps_them(self):
        from ogr_core.geometry.transforms import translate
        _p, lens, _piezo = _project()
        moved = translate(lens, 3.0, -1.0)
        assert (moved.id, moved.polyline.id) == (lens.id, lens.polyline.id)


# ======================================================================
class TestOneRule:

    def test_both_gates_ask_the_core_copy(self):
        if not _HAS_QT:
            return
        import ogr_core.geometry.transforms as T
        from ogr_api import Workspace, call
        real = getattr(T, "copy_boundary", None)
        seen = []

        def spy(b, dx, dy):
            seen.append((b.id, dx, dy))
            return real(b, dx, dy)

        p, lens, _piezo = _project()
        w = _window(p)
        q, lens_q, _ = _project()
        ws = Workspace()
        T.copy_boundary = spy
        try:
            _copied(w, lens)
            call(ws, "boundary_edit", project_id=ws.add(q).id,
                 boundary=lens_q.id, op="copy", dx=0.5, dy=-1.5)
        finally:
            ws.shutdown()
            if real is None:
                del T.copy_boundary
            else:
                T.copy_boundary = real
        assert seen == [(lens.id, 2.0, 2.0), (lens_q.id, 0.5, -1.5)], seen

    def test_the_core_copy_is_a_new_boundary(self):
        from ogr_core.geometry.transforms import copy_boundary
        _p, lens, _piezo = _project()
        before = lens.to_dict()
        new = copy_boundary(lens, 2.0, 2.0)
        assert new is not lens and new.polyline is not lens.polyline
        assert new.polyline.vertices is not lens.polyline.vertices
        assert new.id != lens.id and new.polyline.id != lens.polyline.id
        assert lens.to_dict() == before          # the original is not touched

    def test_the_core_copy_shares_no_block_object(self):
        # a Block Search object's spec is mutable: shared, editing the copy's
        # would edit the original's (no case of the window reaches one: the
        # rule asks for the Block Search)
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.block_object import (BlockObjectKind,
                                                    BlockObjectSpec,
                                                    PolylinePointMode)
        from ogr_core.geometry.transforms import copy_boundary
        spec = BlockObjectSpec(kind=BlockObjectKind.POLYLINE,
                               left_point=PolylinePointMode.END_POINT,
                               group_id=2)
        obj = Boundary(polyline=Polyline([Vertex(10, 6), Vertex(20, 7)]),
                       btype=BoundaryType.BLOCK_SEARCH_OBJECT,
                       block_object=spec)
        new = copy_boundary(obj, 2.0, 2.0)
        assert new.block_object is not spec
        assert new.block_object.to_dict() == spec.to_dict()
        assert _without_ids(new)["block_object"] == spec.to_dict()
