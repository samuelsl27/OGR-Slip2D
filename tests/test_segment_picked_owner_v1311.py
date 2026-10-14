# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.311 (D308) — the canvas' ``segment_picked`` has one owner, and what an
action armed for its next pick goes when its mode does.

Five two-click modes share the signal: Add Distributed Load, the grid
rectangle of Add Grid, Add Support, Add Support Pattern and Stretch Support.
Each action connected its own handler around a pick and disconnected only
its own. Add Support reconnected itself after every support and nothing
disconnected it on Esc, so after using it, the two clicks of a distributed
load placed a support as well. A grid pick abandoned with Esc stayed armed,
and the load and the pattern of an action left with Esc waited for a later
pick.

Now the window connects the signal once and hands each pick to the mode both
clicks were made in. Leaving a mode drops what its action armed.

The invariants, through the real canvas (mouse events, Esc):

* the reproduction: Add Support and two clicks, Esc, Add Distributed Load
  and two clicks — one support and one load;
* each two-click gesture of the five actions, chained with Esc, writes ONE
  thing and leaves one undo step (the grid rectangle goes to the open
  dialog, not the model); two clicks after Esc write nothing;
* the canvas signal has exactly one receiver after every action;
* Esc and a change of tool forget the pending load and pattern;
* an abandoned grid pick does not take the clicks of Add Support, which
  keeps its mode;
* Add Support still places several supports in a row without leaving its
  mode (QUÉ NO SE PUEDE MOVER).
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


@contextlib.contextmanager
def _no_modals():
    """A modal dialog or message box fails the test instead of waiting for
    ever without a screen. The dialogs a test answers are swapped on their
    own class, which wins over this."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


def _ready():
    from ogr_core.support import EndAnchored
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.support_types = [
        EndAnchored(anchor_capacity=120.0, out_of_plane_spacing=1.0)]
    c = w.canvas
    # a real size, and no snapping: inside a window that is not shown the
    # canvas is 98 x 28 px, its 12 px vertex tolerance is some 17 m, and
    # every click lands on a vertex (as test_add_surface_three_points_v1168
    # sets it up)
    c.resize(900, 600)
    c.show()
    c.snap_settings.snap = False
    c.zoom_all()
    w.command_stack.clear()
    w.project.is_dirty = False
    return w, c


def _done(w):
    for dlg in [getattr(w, "_active_grid_dialog", None)]:
        if dlg is not None:
            dlg.reject()
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


def _box(w):
    xs = [v.x for b in w.project.boundaries for v in b.polyline.vertices]
    ys = [v.y for b in w.project.boundaries for v in b.polyline.vertices]
    return min(xs), max(xs), min(ys), max(ys)


def _click(c, x, y):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    vp = QPointF(c.mapFromScene(QPointF(x, y)))
    g = c.viewport().mapToGlobal(vp.toPoint())
    c.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, vp, g,
                                  Qt.LeftButton, Qt.LeftButton,
                                  Qt.NoModifier))
    c.mouseReleaseEvent(QMouseEvent(QEvent.MouseButtonRelease, vp, g,
                                    Qt.LeftButton, Qt.NoButton,
                                    Qt.NoModifier))


def _two(w, c, a, b):
    """Two clicks at fractions (fx, fy) of the model's bounding box."""
    x0, x1, y0, y1 = _box(w)
    for fx, fy in (a, b):
        _click(c, x0 + fx * (x1 - x0), y0 + fy * (y1 - y0))


def _esc(c):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    c.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))


def _receivers(c):
    from PySide6.QtCore import SIGNAL
    return c.receivers(SIGNAL("segment_picked(double,double,double,double)"))


def _counts(w):
    return len(w.project.supports), len(w.project.distributed_loads)


def _steps(w):
    return list(w.command_stack.history()[0])


@contextlib.contextmanager
def _answered():
    """The two dialogs that open before a pick, accepted as they come."""
    from ogr_gui.dialogs import load_dialogs
    from ogr_gui.dialogs.support_pattern_dialog import (
        AddSupportPatternDialog)

    def accept(self):
        self.accept()
        return 1

    with _no_modals(), \
            _swap(load_dialogs.DistributedLoadDialog, "exec",
                  lambda self: 1), \
            _swap(AddSupportPatternDialog, "exec", accept):
        yield


# ----------------------------------------------------------------------
class TestOneOwner:
    def test_the_reproduction(self):
        w, c = _ready()
        try:
            with _answered():
                w.act_add_support()
                _two(w, c, (0.6, 0.5), (0.8, 0.6))
                assert _counts(w) == (1, 0)
                _esc(c)
                w.act_add_distributed_load()
                _two(w, c, (0.1, 1.0), (0.3, 1.0))
            assert _counts(w) == (1, 1)
        finally:
            _done(w)

    def test_each_gesture_writes_one_thing_and_leaves_one_step(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            assert _receivers(c) == 1
            with _answered():
                # Add Support
                w.act_add_support()
                _two(w, c, (0.6, 0.5), (0.8, 0.6))
                assert _counts(w) == (1, 0)
                assert _steps(w) == ["Set support"]
                assert _receivers(c) == 1
                # two distinct clicks, not one point snapped twice
                s = w.project.supports[0]
                assert (s.head.x, s.head.y) != (s.tail.x, s.tail.y)
                _esc(c)
                before = _json(w.project)
                _two(w, c, (0.5, 0.5), (0.7, 0.5))
                assert _json(w.project) == before
                assert len(_steps(w)) == 1

                # Add Distributed Load
                w.act_add_distributed_load()
                assert _receivers(c) == 1
                _two(w, c, (0.1, 1.0), (0.3, 1.0))
                assert _counts(w) == (1, 1)
                assert _steps(w)[-1] == "Set load"
                assert len(_steps(w)) == 2
                assert c.tool_mode is ToolMode.SELECT
                _esc(c)

                # Add Support Pattern
                w.act_add_support_pattern()
                assert _receivers(c) == 1
                _two(w, c, (0.05, 1.0), (0.35, 1.0))
                n_supports, n_loads = _counts(w)
                assert n_supports > 1 and n_loads == 1
                assert _steps(w)[-1] == "Add support pattern"
                assert len(_steps(w)) == 3
                _esc(c)

                # Stretch Support
                w.act_stretch_support_mode()
                assert _receivers(c) == 1
                before = _json(w.project)
                _two(w, c, (0.6, 0.5), (0.65, 0.45))
                assert _counts(w) == (n_supports, 1)
                assert _json(w.project) != before
                assert _steps(w)[-1] == "Stretch support"
                assert len(_steps(w)) == 4
                _esc(c)

                # the grid rectangle: into the open dialog, not the model
                w.act_add_grid()
                dlg = w._active_grid_dialog
                w._begin_grid_pick()
                assert _receivers(c) == 1
                before = _json(w.project)
                shown = (dlg.sb_xmin.value(), dlg.sb_xmax.value())
                _two(w, c, (0.2, 0.7), (0.5, 0.9))
                assert _json(w.project) == before
                assert len(_steps(w)) == 4
                assert (dlg.sb_xmin.value(), dlg.sb_xmax.value()) != shown
                assert c.tool_mode is ToolMode.SELECT
                dlg.reject()
            assert _receivers(c) == 1
        finally:
            _done(w)


class TestLeavingAModeForgetsItsPick:
    def test_esc_forgets_the_load_and_the_pattern(self):
        w, c = _ready()
        try:
            with _answered():
                w.act_add_distributed_load()
                assert w._pending_dist_load is not None
                _esc(c)
                assert w._pending_dist_load is None
                _two(w, c, (0.1, 1.0), (0.3, 1.0))
                assert _counts(w) == (0, 0)

                w.act_add_support_pattern()
                assert w._active_pattern is not None
                _esc(c)
                assert w._active_pattern is None
                _two(w, c, (0.05, 1.0), (0.35, 1.0))
                assert _counts(w) == (0, 0)
            assert _steps(w) == []
        finally:
            _done(w)

    def test_another_tool_forgets_them_too(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            with _answered():
                w.act_add_distributed_load()
                w._set_tool(ToolMode.PAN)
                assert w._pending_dist_load is None
                w.act_add_support_pattern()
                w.act_add_support()
                assert w._active_pattern is None
        finally:
            _done(w)

    def test_an_abandoned_grid_pick_does_not_take_add_supports_clicks(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            with _answered():
                w.act_add_grid()
                dlg = w._active_grid_dialog
                w._begin_grid_pick()
                _esc(c)
                bounds = (dlg.sb_xmin.value(), dlg.sb_xmax.value(),
                          dlg.sb_ymin.value(), dlg.sb_ymax.value())
                w.act_add_support()
                _two(w, c, (0.6, 0.5), (0.8, 0.6))
                assert _counts(w) == (1, 0)
                assert (dlg.sb_xmin.value(), dlg.sb_xmax.value(),
                        dlg.sb_ymin.value(), dlg.sb_ymax.value()) == bounds
                assert c.tool_mode is ToolMode.ADD_SUPPORT
                dlg.reject()
        finally:
            _done(w)


class TestAddSupportStaysInItsMode:
    def test_three_supports_in_a_row(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        w, c = _ready()
        try:
            with _answered():
                w.act_add_support()
                for k, fy in enumerate((0.4, 0.5, 0.6)):
                    _two(w, c, (0.6, fy), (0.8, fy + 0.05))
                    assert c.tool_mode is ToolMode.ADD_SUPPORT
                    assert _counts(w) == (k + 1, 0)
            assert _steps(w) == ["Set support"] * 3
            assert _receivers(c) == 1
        finally:
            _done(w)
