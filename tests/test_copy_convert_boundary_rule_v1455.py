# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D410 (v0.1.455) — Copy Boundary and Convert Boundary add only what the rule of
the core lets add, and say why not.

The invariant
-------------
The rule is ``ogr_core.project.rules.boundary_refusal``: one External, one
water table, one tension crack and one drawdown line; a drawdown line only
with rapid drawdown; Block Search objects only with that search. The greyed
menu entries ask it, the end of a drawing asks it since v0.1.431 (D398), and
the agent asks it when it copies and when it changes a type. The window's
Copy and its two Convert paths asked nothing. Measured with v0.1.452 on the
demo slope, with the dialog substituted:

* Copy the water table: two (the engine reads the higher one, and the
  number can move without a word); Copy the External: two (the regions read
  the first, the second does nothing — rule 7);
* Convert the water table into a drawdown line without rapid drawdown: it
  stays in the model; into the External, open as it is: two Externals, by
  both paths;
* Convert a lens into a water table with one in place: two, by both paths.

And the context menu's Convert did not do what the menu's does
(``convert_boundary``): it changed the type alone, so a lens made a water
table kept its name «Material Boundary», its closed ring, its material and
its colour (#8b4513, the material's, which the canvas paints).

Now Copy asks ``boundary_refusal`` of the original's type, and both Convert
paths take one step after their dialog (``MainWindow._apply_conversion``):
``rules.conversion_refusal`` (the rule of the new type without counting the
boundary converted, and an External only from a closed polyline: what the
agent's ``change_type`` wrote by hand, moved to the core), then, for a Block
Search object, ``rules.block_object_refusal`` of the converted boundary, as
the agent does after every edit (measured with v0.1.454: a polyline that
doubles back became a Block Search object the rule refuses, by both paths,
and the agent refused it). A refusal says its reason in the status bar, as
at the end of a drawing, and leaves the undo stack as it was. By the owner's
decision, converting into the External is refused as the agent refuses it,
not offered as a replacement, and the dialog is unchanged (the rule is asked
on accept).

The reference (rule 1)
----------------------
An identity: the window adds exactly what the core's rule lets add, the rule
the agent asks; the agent's answers, with its English of always, are the
control. And the converted boundary is ``convert_boundary``'s, field by
field, by either path.

One window for the file, the dialog substituted in both modules it is read
from and never executed (modal), the language restored. Measured: 1.9 s
for the file in the runner, most of it building the window.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except ImportError:  # pragma: no cover
    _HAS_QT = False

_WINDOW: list = []


class _Pick:
    """The Convert Boundary dialog, answered with ``target`` and never shown
    (modal). ``during`` runs while it would be open: an agent's edit."""
    target = None
    during = None

    def __init__(self, *_args, **_kw):
        pass

    def exec(self):
        if _Pick.during is not None:
            _Pick.during()
        return 1

    def new_type(self):
        return _Pick.target


@contextlib.contextmanager
def _dialog(target, during=None):
    """Both modules the two Convert paths read the dialog from."""
    import ogr_gui.dialogs as dialogs
    import ogr_gui.main_window as mw
    saved = (mw.ConvertBoundaryDialog, dialogs.ConvertBoundaryDialog)
    mw.ConvertBoundaryDialog = dialogs.ConvertBoundaryDialog = _Pick
    _Pick.target, _Pick.during = target, during
    try:
        yield
    finally:
        mw.ConvertBoundaryDialog, dialogs.ConvertBoundaryDialog = saved
        _Pick.during = None


@contextlib.contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


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
    # offscreen a message's timeout never fires: one path would read the
    # other's (the review of 0.1.455)
    w.ogr_status.clearMessage()
    return w


def _demo(**settings):
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    for key, value in settings.items():
        section, attr = key.split("__")
        setattr(getattr(p.settings, section), attr, value)
    return p


def _lens(project):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    b = Boundary(polyline=Polyline([Vertex(30, 2), Vertex(32, 2),
                                    Vertex(32, 3), Vertex(30, 3)],
                                   closed=True),
                 btype=BoundaryType.MATERIAL,
                 material_id=project.materials[0].id,
                 name="Material Boundary")
    project.add_boundary(b)
    return b


def _index(w, btype):
    return next(i for i, b in enumerate(w.project.boundaries)
                if b.btype == btype)


def _count(w, btype):
    return sum(1 for b in w.project.boundaries if b.btype == btype)


def _paths(w):
    """The two Convert paths: the Edit menu's and the context menu's."""
    return (("menu", w._do_convert_boundary),
            ("context", lambda i: w._on_boundary_action_requested("convert",
                                                                   i)))


def _snapshot(w):
    return ([(b.id, b.btype) for b in w.project.boundaries],
            w.command_stack.history())


# ======================================================================
class TestCopy:

    def test_the_one_of_its_kind_is_not_copied_and_the_bar_says_why(self):
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        w = _window(_demo())
        said = {}
        with _spanish():
            for btype in (BT.WATER_TABLE, BT.EXTERNAL):
                before = _snapshot(w)
                w._do_copy_boundary(_index(w, btype))
                assert _snapshot(w) == before, btype
                said[btype] = w.ogr_status.currentMessage()
        assert said == {
            BT.WATER_TABLE: "Solo se permite un nivel freático. El contorno "
                            "no se ha añadido.",
            BT.EXTERNAL: "Solo se permite un contorno exterior. El contorno "
                         "no se ha añadido."}, said

    def test_what_the_rule_lets_copy_is_copied(self):
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        p = _demo()
        lens = _lens(p)
        w = _window(p)
        w._do_copy_boundary(w.project.boundaries.index(lens))
        assert _count(w, BT.MATERIAL) == 2
        assert w.command_stack.history() == (["Add Material Boundary"], [])


# ======================================================================
class TestConvertRefusals:

    def _refused(self, project_factory, pick, target):
        """Each path: nothing changes, and the bar's sentence."""
        from ogr_core.geometry import BoundaryType  # noqa: F401
        said = {}
        for via, go in _paths(_window(project_factory())):
            w = _window(project_factory())
            go_now = dict(_paths(w))[via]
            index = pick(w)
            before = _snapshot(w)
            with _dialog(target), _spanish():
                go_now(index)
                said[via] = w.ogr_status.currentMessage()
            assert _snapshot(w) == before, (via, target)
        assert said["menu"] == said["context"], said
        return said["menu"]

    def test_a_drawdown_line_without_rapid_drawdown(self):
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        said = self._refused(_demo, lambda w: _index(w, BT.WATER_TABLE),
                             BT.DRAWDOWN)
        assert said.startswith("La línea de desembalse solo está disponible"
                               ), said
        assert said.endswith(" El contorno no se ha convertido."), said

    def test_a_second_water_table(self):
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT

        def project():
            p = _demo()
            _lens(p)
            return p
        said = self._refused(project, lambda w: len(w.project.boundaries) - 1,
                             BT.WATER_TABLE)
        assert said == ("Solo se permite un nivel freático. El contorno no "
                        "se ha convertido."), said

    def test_a_second_external(self):
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        said = self._refused(_demo, lambda w: _index(w, BT.WATER_TABLE),
                             BT.EXTERNAL)
        assert said == ("Solo se permite un contorno exterior. El contorno no "
                        "se ha convertido."), said

    def test_an_open_polyline_into_the_external(self):
        """With no External in the model: the open water table cannot be
        one."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT

        def project():
            p = _demo()
            p.boundaries[:] = [b for b in p.boundaries
                               if b.btype != BT.EXTERNAL]
            return p
        said = self._refused(project, lambda w: _index(w, BT.WATER_TABLE),
                             BT.EXTERNAL)
        assert said == ("Solo una polilínea cerrada puede convertirse en el "
                        "contorno exterior. El contorno no se ha convertido."
                        ), said

    def test_a_block_search_object_its_geometry_cannot_be(self):
        """A polyline that doubles back in x, with the Block Search on: the
        type is allowed and the geometry is not (``block_object_refusal``)."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import Boundary, BoundaryType as BT
        from ogr_core.geometry import Polyline, Vertex

        def project():
            p = _demo(search__surface_type="non_circular",
                      search__search_method="block")
            p.add_boundary(Boundary(btype=BT.MATERIAL, polyline=Polyline(
                [Vertex(10, 5), Vertex(30, 5), Vertex(20, 8)])))
            return p
        said = self._refused(project, lambda w: len(w.project.boundaries) - 1,
                             BT.BLOCK_SEARCH_OBJECT)
        assert said.endswith(" El contorno no se ha convertido."), said
        assert "Block Search" not in said, said        # said in Spanish

    def test_a_block_line_of_three_vertices(self):
        """A refusal whose sentence carries a value (the vertices of a Line):
        said in Spanish through its code (the review of 0.1.455: ``tr`` of
        the filled sentence found no entry and left it in English)."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import Boundary, BoundaryType as BT
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry.block_object import (BlockObjectKind,
                                                    BlockObjectSpec)

        def project():
            p = _demo(search__surface_type="non_circular",
                      search__search_method="block")
            p.add_boundary(Boundary(
                btype=BT.BLOCK_SEARCH_OBJECT,
                polyline=Polyline([Vertex(10, 5), Vertex(20, 5),
                                   Vertex(30, 6)]),
                block_object=BlockObjectSpec(kind=BlockObjectKind.LINE)))
            return p
        said = self._refused(project, lambda w: len(w.project.boundaries) - 1,
                             BT.BLOCK_SEARCH_OBJECT)
        assert said.endswith(" El contorno no se ha convertido."), said
        assert "Block Search" not in said and "vertices" not in said, said


# ======================================================================
class TestConvertDoes:

    def test_the_water_table_into_itself(self):
        """Not counted against itself; and, as nothing changes, no undo step
        (the review of 0.1.455)."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        for via, _go in _paths(_window(_demo())):
            w = _window(_demo())
            go = dict(_paths(w))[via]
            with _dialog(BT.WATER_TABLE), _spanish():
                go(_index(w, BT.WATER_TABLE))
                said = w.ogr_status.currentMessage()
            assert _count(w, BT.WATER_TABLE) == 1, via
            assert said == "Convertido en Nivel freático", (via, said)
            assert w.command_stack.history() == ([], []), via

    def test_a_name_left_by_an_older_version_is_a_default(self):
        """Any type's English name is a default, not only the boundary's
        own (D399): a water table an older context menu left named
        «Material Boundary» is shown as a water table, and converted it
        takes the new type's name (the second review of 0.1.455: no test
        held that once the context menu stopped leaving such names)."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        from ogr_gui.labels import boundary_label
        p = _demo()
        wt = p.boundaries[[b.btype for b in p.boundaries].index(
            BT.WATER_TABLE)]
        wt.name = "Material Boundary"
        w = _window(p)
        with _spanish():
            assert boundary_label(wt) == "Nivel freático"
        with _dialog(BT.PIEZOMETRIC):
            w._do_convert_boundary(_index(w, BT.WATER_TABLE))
        b = w.project.boundaries[_index(w, BT.PIEZOMETRIC)]
        assert b.name == "Piezometric Line", b.name

    def test_of_two_sharing_an_id_the_one_picked(self):
        """Only a hand-edited file has two boundaries with one id: the one
        picked is converted, not the first (the second review)."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import Boundary, BoundaryType as BT
        from ogr_core.geometry import Polyline, Vertex
        for via, _go in _paths(_window(_demo())):
            p = _demo()
            a = Boundary(btype=BT.MATERIAL, id="twin", polyline=Polyline(
                [Vertex(0, 3), Vertex(50, 3)]))
            b = Boundary(btype=BT.MATERIAL, id="twin", polyline=Polyline(
                [Vertex(0, 4), Vertex(50, 4)]))
            p.add_boundary(a)
            p.add_boundary(b)
            w = _window(p)
            go = dict(_paths(w))[via]
            with _dialog(BT.WEAK_LAYER):
                go(w.project.boundaries.index(b))
            got = [(x.polyline.vertices[0].y, x.btype) for x in
                   w.project.boundaries if x.id == "twin"]
            assert got == [(3, BT.MATERIAL), (4, BT.WEAK_LAYER)], (via, got)

    def test_a_name_that_is_not_text(self):
        """A hand-edited file can carry one: kept, never compared with the
        default names (a list cannot be: the agent's change_type raised a
        raw TypeError with the first draft)."""
        from ogr_core.geometry import BoundaryType as BT
        from ogr_core.geometry.boundary import boundary_has_given_name
        from ogr_core.geometry.transforms import convert_boundary
        p = _demo()
        lens = _lens(p)
        for odd in (["a"], {"x": 1}, 5):
            lens.name = odd
            assert boundary_has_given_name(lens), odd
            assert convert_boundary(lens, BT.WEAK_LAYER).name == odd, odd

    def test_a_name_the_user_gave_is_kept(self):
        """By the owner's decision in the review: a water table named by the
        user, converted into a piezometric line, keeps its name, by both
        paths of the window (the agent's, in ``TestOneRule``); a default
        name becomes the new type's."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        from ogr_core.geometry.transforms import convert_boundary
        for via, _go in _paths(_window(_demo())):
            p = _demo()
            wt = p.boundaries[[b.btype for b in p.boundaries].index(
                BT.WATER_TABLE)]
            wt.name = "Phreatic 2024"
            w = _window(p)
            go = dict(_paths(w))[via]
            with _dialog(BT.PIEZOMETRIC):
                go(_index(w, BT.WATER_TABLE))
            b = w.project.boundaries[_index(w, BT.PIEZOMETRIC)]
            assert b.name == "Phreatic 2024", (via, b.name)
        p = _demo()
        lens = _lens(p)
        assert convert_boundary(lens, BT.WEAK_LAYER).name == "Weak Layer"

    def test_an_agent_edit_while_the_dialog_is_open(self):
        """The boundary is found again by its id: an agent's move while the
        dialog is open is converted with its new vertices; a boundary the
        agent deleted is said, and nothing changes."""
        if not _HAS_QT:
            return
        import dataclasses

        from ogr_core.geometry import BoundaryType as BT, Vertex
        for via, _go in _paths(_window(_demo())):
            w = _window(_demo())
            go = dict(_paths(w))[via]
            i = _index(w, BT.WATER_TABLE)
            old = w.project.boundaries[i]

            def move():
                moved = dataclasses.replace(old, polyline=dataclasses.replace(
                    old.polyline, vertices=[Vertex(v.x, v.y + 1.0)
                                            for v in old.polyline.vertices]))
                w.project.boundaries[i] = moved
            with _dialog(BT.PIEZOMETRIC, during=move):
                go(i)
            b = w.project.boundaries[i]
            assert b.btype == BT.PIEZOMETRIC and b.id == old.id, via
            assert [v.y for v in b.polyline.vertices] == [9.0, 9.0], via

            w = _window(_demo())
            go = dict(_paths(w))[via]
            i = _index(w, BT.WATER_TABLE)

            def delete():
                del w.project.boundaries[i]
            before = len(w.project.boundaries) - 1
            with _dialog(BT.PIEZOMETRIC, during=delete), _spanish():
                go(i)
                said = w.ogr_status.currentMessage()
            assert len(w.project.boundaries) == before, via
            assert said == ("El contorno ya no está en el modelo: no se ha "
                            "convertido nada."), (via, said)

    def test_both_paths_give_convert_boundarys_boundary(self):
        """A lens into a water table, with none in place: by either path,
        the boundary ``convert_boundary`` gives — type, name, open ring, no
        material, the water table's colour."""
        if not _HAS_QT:
            return
        from ogr_core.geometry import BoundaryType as BT
        from ogr_core.geometry.transforms import convert_boundary
        got = {}
        for via, _go in _paths(_window(_demo())):
            p = _demo()
            p.boundaries[:] = [b for b in p.boundaries
                               if b.btype != BT.WATER_TABLE]
            lens = _lens(p)
            want = convert_boundary(lens, BT.WATER_TABLE)
            w = _window(p)
            go = dict(_paths(w))[via]
            with _dialog(BT.WATER_TABLE):
                go(w.project.boundaries.index(lens))
            b = w.project.boundaries[-1]
            got[via] = (b.btype, b.name, b.polyline.closed, b.material_id,
                        b.color, b.id == lens.id)
            assert got[via] == (want.btype, want.name, want.polyline.closed,
                                want.material_id, want.color, True), got
        assert got["menu"][4] == "#1e90ff", got


# ======================================================================
class TestOneRule:

    def test_the_window_and_the_agent_ask_conversion_refusal(self):
        """A spy on the core's rule sees both doors."""
        if not _HAS_QT:
            return
        import ogr_core.project.rules as rules
        from ogr_api import Workspace, call
        from ogr_core.geometry import BoundaryType as BT
        seen = []
        real = rules.conversion_refusal

        def spy(project, boundary, new_type):
            seen.append(new_type)
            return real(project, boundary, new_type)
        rules.conversion_refusal = spy
        ws = Workspace()
        try:
            w = _window(_demo())
            with _dialog(BT.WATER_TABLE):
                w._do_convert_boundary(_index(w, BT.WATER_TABLE))
            pid = call(ws, "project_new", name="D410")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [50, 0], [50, 15], [35, 15], [25, 25],
                             [0, 25]],
                "materials": [{"name": "Soil", "unit_weight": 19,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {"cohesion": 10,
                                                       "friction_angle": 25}}}]})
            bid = call(ws, "boundary_add", project_id=pid, type="material",
                       points=[[0, 5], [50, 5]])["boundary"]["id"]
            call(ws, "boundary_edit", project_id=pid, boundary=bid,
                 op="change_type", new_type="piezometric")
        finally:
            rules.conversion_refusal = real
            ws.shutdown()
        assert [t.name for t in seen] == ["WATER_TABLE", "PIEZOMETRIC"], seen

    def test_the_agent_says_what_it_said(self):
        """The control: the agent's refusals, with its English of always."""
        from ogr_api import Conflict, Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="D410")["project_id"]
            info = call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [50, 0], [50, 15], [35, 15], [25, 25],
                             [0, 25]],
                "materials": [{"name": "Soil", "unit_weight": 19,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {"cohesion": 10,
                                                       "friction_angle": 25}}}],
                "water_table": {"points": [[0, 8], [50, 8]],
                                "materials": ["Soil"]}})
            ids = {b["type"]: b["id"] for b in info["boundaries"]}
            said = {}
            for target in ("drawdown", "external"):
                try:
                    call(ws, "boundary_edit", project_id=pid,
                         boundary=ids["water_table"], op="change_type",
                         new_type=target)
                except Conflict as exc:
                    said[target] = str(exc)
            out = call(ws, "boundary_edit", project_id=pid,
                       boundary=ids["water_table"], op="change_type",
                       new_type="water_table")
            # the owner's decision in the review: a name given is kept by
            # the agent too, and a default one becomes the new type's
            call(ws, "boundary_edit", project_id=pid,
                 boundary=ids["water_table"], op="rename", name="Clay top")
            named = call(ws, "boundary_edit", project_id=pid,
                         boundary=ids["water_table"], op="change_type",
                         new_type="piezometric")
            plain = call(ws, "boundary_add", project_id=pid, type="material",
                         points=[[0, 5], [50, 5]])["boundary"]["id"]
            renamed = call(ws, "boundary_edit", project_id=pid,
                           boundary=plain, op="change_type",
                           new_type="weak_layer")
        finally:
            ws.shutdown()
        assert "only read by a rapid drawdown analysis" in said["drawdown"]
        assert "A model has exactly one External boundary" in said["external"]
        assert out["boundary"]["type"] == "water_table", out
        assert named["boundary"]["name"] == "Clay top", named
        assert renamed["boundary"]["name"] == "Weak Layer", renamed
