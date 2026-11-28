# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D456 (v0.1.513) — in Interpret, the model's context menus offer no action
that does nothing.

The invariant
-------------
Interpret's canvas is a ``CanvasView``, and a right click in Select mode
opened the main window's menus over a vertex, a boundary, a support and a
load. Each of their actions only emits a signal (``vertex_action_requested``
and its three siblings), which the main window connects and Interpret does
not: measured on 0.1.485, 4 + 6 enabled actions on the demo slope, and
firing all of them left the project as it was. In a window that opens
saying «Post-processing — read-only view», «Delete Boundary» enabled is
worse than no menu (rule 7).

The owner's decision (2026-11-28): keep what makes sense in post-processing
and drop what does not. Every action of those menus EDITS the model, and
Interpret's results may be of an earlier model (D419), so none of them
stays. What stays is each menu's heading (the vertex's coordinates, the
boundary's type and name, the support's name, the load's magnitude), and
two actions that only read:

* the vertex: «Copy Coordinates», ``x<TAB>y`` at full precision;
* the support: «Support Force Diagram...», Interpret's own diagram with
  that support chosen.

The switch is ``CanvasView.model_edit_menus`` (the mould of
``user_surface_menu``, v0.1.469), off by default and on only on the main
window's canvas. Checked here:

* on Interpret's canvas, every enabled action of the four menus does
  something observable (the clipboard, a diagram window on the support
  that was clicked), no edit action is offered, and the project does not
  change;
* on the main window's canvas, the control: the same four menus still
  offer their edit actions, and their four signals are connected. They are
  not fired: several open modal dialogs.

The menus are real ``QMenu.exec()`` calls (replacing ``exec`` on the class
does not stop the popup in PySide6, D456's measured trap): a ``QTimer``
reads the open popup through ``QApplication.activePopupWidget()``, closes
it and then fires what it offered.

Cost: one main window and one Interpret window on the demo slope, with no
analysis (Interpret opens on an empty result set).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_STATE: dict = {}


def _windows():
    if _STATE:
        return _STATE
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ogr_core.geometry import Vertex
    from ogr_core.loads import LineLoad
    from ogr_core.support import EndAnchored, SupportInstance
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_gui.main_window import MainWindow

    w = MainWindow()
    w.project.is_dirty = False
    w.act_load_demo()
    p = w.project
    st = EndAnchored()
    p.support_types = [st]
    p.supports = [
        SupportInstance(type_id="end_anchored", type_ref=st.id, name="",
                        head=Vertex(30, 20), tail=Vertex(40, 15)),
        SupportInstance(type_id="end_anchored", type_ref=st.id, name="",
                        head=Vertex(32, 18), tail=Vertex(42, 13))]
    p.add_line_load(LineLoad(point=Vertex(55, 20), magnitude=50.0, name=""))
    iw = InterpretWindow(p, {}, w)
    iw.resize(1200, 800)
    iw.show()
    QApplication.processEvents()
    _STATE.update(w=w, iw=iw, p=p)
    return _STATE


def _snapshot(p) -> str:
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _open(call, fire=True):
    """Run ``call`` (which opens a menu), and from a timer read the popup:
    ``[(text, enabled)]`` of its actions; close it and, with ``fire``, fire
    the enabled ones."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    seen: list = []

    def grab():
        m = QApplication.activePopupWidget()
        if m is None:
            seen.append(None)
            return
        acts = [a for a in m.actions() if not a.isSeparator()]
        seen.append([(a.text(), a.isEnabled()) for a in acts])
        m.close()
        if fire:
            for a in acts:
                if a.isEnabled():
                    a.trigger()

    QTimer.singleShot(100, grab)
    call()
    QApplication.processEvents()
    assert seen and seen[0] is not None, "no menu opened"
    return seen[0]


def _external(p):
    return next(i for i, b in enumerate(p.boundaries)
                if b.btype.name == "EXTERNAL")


def _menus(c, p):
    """The four menus, as calls on canvas ``c``."""
    from PySide6.QtCore import QPoint
    bi = _external(p)
    return {
        "vertex": lambda: c._show_vertex_context_menu(QPoint(0, 0), (bi, 2)),
        "boundary": lambda: c._show_boundary_context_menu(QPoint(0, 0), bi),
        "support": lambda: c._show_support_context_menu(QPoint(0, 0), 1),
        "load": lambda: c._show_load_context_menu(QPoint(0, 0), ("line", 0)),
    }


def _enabled(items):
    return [t for t, on in items if on]


class TestInterpretMenus:
    def test_the_switch_is_off_in_interpret_and_on_in_the_main_window(self):
        s = _windows()
        assert s["iw"].canvas.model_edit_menus is False
        assert s["w"].canvas.model_edit_menus is True

    def test_vertex_menu_copies_the_coordinates(self):
        from PySide6.QtWidgets import QApplication
        s = _windows()
        p = s["p"]
        v = p.boundaries[_external(p)].polyline.vertices[2]
        clip = QApplication.clipboard()
        saved = clip.text()
        before = _snapshot(p)
        try:
            clip.setText("")
            items = _open(_menus(s["iw"].canvas, p)["vertex"])
            got = clip.text()
        finally:
            clip.setText(saved)
        assert _enabled(items) == ["Copy Coordinates"]
        assert got == f"{v.x!r}\t{v.y!r}"
        assert _snapshot(p) == before

    def test_boundary_and_load_menus_are_their_heading_alone(self):
        s = _windows()
        p = s["p"]
        before = _snapshot(p)
        for name in ("boundary", "load"):
            items = _open(_menus(s["iw"].canvas, p)[name])
            assert len(items) == 1, (name, items)
            assert _enabled(items) == [], (name, items)
        assert _snapshot(p) == before

    def test_support_menu_opens_the_diagram_on_that_support(self):
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)
        s = _windows()
        iw, p = s["iw"], s["p"]
        before = _snapshot(p)
        n0 = len(getattr(iw, "_chart_windows", []) or [])
        items = _open(_menus(iw.canvas, p)["support"])
        assert _enabled(items) == ["Support Force Diagram..."]
        kept = getattr(iw, "_chart_windows", []) or []
        assert len(kept) == n0 + 1
        dlg = kept[-1]
        try:
            assert isinstance(dlg, SupportForceDiagramWindow)
            assert dlg.cbo.currentIndex() == 1      # the one clicked
            assert not dlg.isModal()
        finally:
            dlg.close()
        assert _snapshot(p) == before

    def test_no_edit_action_in_interpret(self):
        s = _windows()
        p = s["p"]
        edit = {"Move Vertex", "Insert Vertex (after)", "Edit Coordinates…",
                "Delete Vertex", "Move Boundary", "Convert Boundary…",
                "Delete Boundary", "Expand / Shrink…", "Change Slope Angle…",
                "Properties…", "Stretch", "Modify Pattern…", "Delete",
                "Modify…"}
        for name, call in _menus(s["iw"].canvas, p).items():
            texts = {t for t, _on in _open(call, fire=False)}
            assert not texts & edit, (name, texts & edit)

    def test_control_the_main_window_keeps_its_edit_menus(self):
        s = _windows()
        c, p = s["w"].canvas, s["p"]
        want = {"vertex": ["Move Vertex", "Insert Vertex (after)",
                           "Edit Coordinates…", "Delete Vertex"],
                "boundary": ["Move Boundary", "Edit Coordinates…",
                             "Convert Boundary…", "Delete Boundary",
                             "Expand / Shrink…", "Change Slope Angle…"],
                "support": ["Properties…", "Stretch", "Modify Pattern…",
                            "Delete"],
                "load": ["Modify…", "Delete"]}
        for name, call in _menus(c, p).items():
            assert _enabled(_open(call, fire=False)) == want[name], name
        for sig in ("vertex_action_requested(QString,int,int)",
                    "boundary_action_requested(QString,int)",
                    "support_action_requested(QString,int)",
                    "load_action_requested(QString,QString,int)"):
            assert c.receivers("2" + sig) >= 1, sig
