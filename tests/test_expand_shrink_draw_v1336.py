# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.336 (D334) — Expand / Shrink by a drawn polyline, through the canvas.

*Expand / Shrink → Draw polyline* entered ``DRAW_EXPAND_SHRINK`` and
rerouted ``boundary_drawn`` from the model to its own slot. But the mode had
no boundary type, so ``_finish_drawing`` cancelled the drawing in silence and
never emitted anything: the polyline was never applied, and the reroute
stayed in place, so the NEXT boundary the user drew went to expand/shrink
instead of into the model. Like that since v0.1.59; the only test
(``test_f2_rules_v1196``) called the slot directly and never saw it.
Measured on 0.1.335 with the clicks of the cases below, before it was fixed
(rule 6).

The polyline now has a signal of its own, connected once. The cases draw it
with real clicks, snapping on so that the two ends land ON the External's
vertices, and check:

* the External grows by exactly the triangle the polyline adds — base 20
  from (50, 35) to (70, 35), apex at the middle click, the identity of
  ``test_f2_rules_v1196`` (area +20 at (60, 37));
* a material boundary drawn afterwards goes into the model, also after an
  Esc in the middle of the polyline.

Message boxes are replaced by fakes that never block, so that on the old
tree a case fails instead of hanging the run.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _pick():
    import test_scale_rotate_pick_v1336 as pick
    return pick


@contextlib.contextmanager
def _quiet():
    """``QMessageBox`` of the window replaced: the question about the removed
    arc answers No, and a warning is recorded instead of shown."""
    import ogr_gui.main_window as mw
    from PySide6.QtWidgets import QMessageBox
    shown = []

    class _Box:
        Yes, No = QMessageBox.Yes, QMessageBox.No

        @staticmethod
        def question(*_a, **_k):
            return QMessageBox.No

        @staticmethod
        def warning(*a, **_k):
            shown.append(a[2:])

        critical = information = warning

    saved = mw.QMessageBox
    mw.QMessageBox = _Box
    try:
        yield shown
    finally:
        mw.QMessageBox = saved


def _ready():
    pick = _pick()
    w, c = pick._ready()
    c.snap_settings.snap = True       # the ends must land ON the External
    return w, c


def _click(c, x, y):
    pick = _pick()
    px, py = pick._pixel(c, x, y)
    pick._press(c, px, py)
    return c._draw_points[-1] if c._draw_points else None


def _area(project):
    return _pick()._f2()._area(project.external_boundary().polyline)


def _draw_expand(w, c):
    """The polyline (50, 35) → (60, 37) → (70, 35), drawn in the mode the
    menu enters, and finished with Enter. Returns the middle point as the
    canvas placed it."""
    from ogr_gui.canvas.tool_mode import ToolMode
    idx = w.project.boundaries.index(w.project.external_boundary())
    w._expand_shrink_draw_mode(idx)
    assert c.tool_mode == ToolMode.DRAW_EXPAND_SHRINK
    a = _click(c, 50.0, 35.0)
    m = _click(c, 60.0, 37.0)
    b = _click(c, 70.0, 35.0)
    assert a == (50.0, 35.0) and b == (70.0, 35.0), (a, b)
    _pick()._key(c, Qt.Key_Return)
    return m


def _draw_material(w, c):
    """A material boundary from the External's left side to its toe."""
    from ogr_gui.canvas.tool_mode import ToolMode
    c.set_tool_mode(ToolMode.DRAW_MATERIAL)
    _click(c, 20.0, 22.0)
    _click(c, 45.0, 22.0)
    _click(c, 70.0, 22.0)
    _pick()._key(c, Qt.Key_Return)


def _materials(w):
    from ogr_core.geometry import BoundaryType
    return [b for b in w.project.boundaries
            if b.btype == BoundaryType.MATERIAL]


# ======================================================================
@_requires_qt
class TestThePolylineIsApplied:

    def test_the_external_grows_by_the_triangle(self):
        w, c = _ready()
        area0 = _area(w.project)
        with _quiet() as shown:
            mx, my = _draw_expand(w, c)
        assert shown == [], shown
        # the triangle of base 20 on y = 35 with its apex at the middle click
        assert abs(_area(w.project) - area0 - 10.0 * (my - 35.0)) < 1e-9
        assert my > 35.0

    def test_it_is_one_undo_step(self):
        w, c = _ready()
        area0 = _area(w.project)
        with _quiet():
            _draw_expand(w, c)
        w.command_stack.undo(w.project)
        assert abs(_area(w.project) - area0) < 1e-9


@_requires_qt
class TestTheNextBoundaryGoesIntoTheModel:

    def test_after_the_polyline(self):
        w, c = _ready()
        with _quiet() as shown:
            _draw_expand(w, c)
            before = len(_materials(w))
            _draw_material(w, c)
        assert shown == [], shown
        assert len(_materials(w)) == before + 1

    def test_after_an_escape_in_the_middle_of_it(self):
        w, c = _ready()
        idx = w.project.boundaries.index(w.project.external_boundary())
        area0 = _area(w.project)
        with _quiet() as shown:
            w._expand_shrink_draw_mode(idx)
            _click(c, 50.0, 35.0)
            _click(c, 60.0, 37.0)
            _pick()._key(c, Qt.Key_Escape)        # the points
            _pick()._key(c, Qt.Key_Escape)        # the tool
            before = len(_materials(w))
            _draw_material(w, c)
        assert shown == [], shown
        assert len(_materials(w)) == before + 1
        assert abs(_area(w.project) - area0) < 1e-9
