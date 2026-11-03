# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.415 (D353) — Scale, Rotate and Expand / Shrink behave alike: no marker
left on the pivot, both results readable on the status bar, the same note
in both dialogs, and no straight vertex left by Expand.

The finding (the fifth interface test, 0.1.355, H14), each point measured:

* after Scale or Rotate by clicks an orange circle stayed on the pivot: the
  snap marker of the pivot click, which the mode never moves again and
  nothing cleared (the class of D323);
* Scale left no message and Rotate did. Measured with the real window:
  nothing overwrote it — both lasted 2 s and both were cut where the
  status-bar indicators begin, the result first («External Boundary
  escalado…», «External Boundary rotado 9…»);
* the Rotate dialog lacked the note about the pivot that Scale has;
* Expand by a polyline kept the two cut points as vertices where they are
  no corner: (50, 15) and (50, 0) when the demo grows to the right.

What these tests protect, on the real canvas (shown, at a known zoom):

* the snap marker is gone after Scale, after Rotate, after Esc with a
  boundary picked, and after an Expand drawing is cancelled;
* both messages have one form, the result first and the boundary's name in
  the interface's language, readable at the window's width, for 6 s;
* both dialogs carry the same note about the pivot, in Spanish;
* the demo expanded to the right keeps its area (1200 m²) with six
  vertices and no straight one, a vertex of the user's that is straight is
  kept, and the regions and their materials are those of the same expand
  without the clean-up; undo and redo are exact.

Every dialog is replaced by a fake that never blocks.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _pick():
    import test_scale_rotate_pick_v1336 as pick
    return pick


@contextlib.contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


def _ready():
    """The window of test_scale_rotate_pick_v1336, wide as the fifth test
    saw it, with snapping ON so the pivot click leaves a marker."""
    w, c = _pick()._ready()
    w.resize(1200, 800)
    w.show()
    QApplication.processEvents()
    c.snap_settings.snap = True
    return w, c


def _dump(project):
    return json.dumps(project.to_dict(), sort_keys=True, default=str)


# ======================================================================
@_requires_qt
class TestNoMarkerIsLeft:

    def test_after_scale(self):
        pick = _pick()
        w, c = _ready()
        with pick._dialogs(scale=((1.2, 1.2), None)):
            pick._pick_and_pivot(w, c, "scale_boundary", pivot=(20.0, 20.0))
        assert c._last_snap is None

    def test_after_rotate(self):
        pick = _pick()
        w, c = _ready()
        with pick._dialogs(rotate=((90.0,), None)):
            pick._pick_and_pivot(w, c, "rotate_boundary", pivot=(20.0, 20.0))
        assert c._last_snap is None

    def test_after_esc_with_a_boundary_picked(self):
        pick = _pick()
        w, c = _ready()
        w._actions["scale_boundary"].trigger()
        pick._press(c, *pick._pixel(c, 45.0, 20.0))
        c._snap_xy(c.mapToScene(*pick._pixel(c, 20.0, 20.0)))
        assert c._last_snap is not None            # the premise
        pick._key(c, Qt.Key_Escape)
        assert c._last_snap is None

    def test_after_an_expand_drawing_is_cancelled(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        pick = _pick()
        w, c = _ready()
        idx = w.project.boundaries.index(w.project.external_boundary())
        w._expand_shrink_draw_mode(idx)
        assert c.tool_mode == ToolMode.DRAW_EXPAND_SHRINK
        pick._press(c, *pick._pixel(c, 70.0, 20.0))
        assert c._last_snap is not None            # the premise
        pick._key(c, Qt.Key_Escape)
        assert c._last_snap is None


@_requires_qt
class TestBothMessagesAreRead:

    @staticmethod
    def _after(action, dialogs):
        import time
        pick = _pick()
        w, c = _ready()
        with _spanish(), pick._dialogs(**dialogs):
            pick._pick_and_pivot(w, c, action, pivot=(20.0, 20.0))
            bar = w.ogr_status
            left = bar._until - time.monotonic()
            return bar.currentMessage(), bar._shown, left

    def test_scale(self):
        full, shown, left = self._after("scale_boundary",
                                        {"scale": ((1.2, 1.2), None)})
        assert full == "Escalado ×1.2: Contorno exterior", full
        assert shown.startswith("Escalado ×1.2"), shown
        assert 5.0 < left <= 6.0, left

    def test_rotate(self):
        full, shown, left = self._after("rotate_boundary",
                                        {"rotate": ((90.0,), None)})
        assert full == "Rotado 90°: Contorno exterior", full
        assert shown.startswith("Rotado 90°"), shown
        assert 5.0 < left <= 6.0, left

    def test_a_scale_by_two_factors_says_both(self):
        full, _shown, _left = self._after("scale_boundary",
                                          {"scale": ((1.5, 0.5), None)})
        assert full == "Escalado ×(1.5, 0.5): Contorno exterior", full


@_requires_qt
class TestBothDialogsSayTheSame:

    def test_the_note_about_the_pivot(self):
        from ogr_gui.dialogs.boundary_dialogs import RotateDialog, ScaleDialog
        QApplication.instance() or QApplication([])
        notes = {}
        with _spanish():
            for cls in (ScaleDialog, RotateDialog):
                d = cls(pivot=(1.0, 2.0))
                try:
                    notes[cls.__name__] = [
                        lab.text() for lab in d.findChildren(QLabel)
                        if "pivote" in lab.text()]
                finally:
                    d.deleteLater()
        assert notes["ScaleDialog"] == notes["RotateDialog"] == [
            "<i>El pivote es el punto pulsado en el lienzo; escribe otro "
            "aquí si lo necesitas.</i>"], notes


# ======================================================================
def _ring(points):
    from ogr_core.geometry import Polyline, Vertex
    return Polyline(vertices=[Vertex(x, y) for x, y in points], closed=True)


def _line(points):
    from ogr_core.geometry import Polyline, Vertex
    return Polyline(vertices=[Vertex(x, y) for x, y in points], closed=False)


def _signed_area(verts):
    from ogr_core.geometry.expand_shrink import _signed_area as sa
    return sa(verts)


def _straight(verts):
    """Vertices on the segment of their two neighbours."""
    out = []
    n = len(verts)
    for i, v in enumerate(verts):
        a, b = verts[i - 1], verts[(i + 1) % n]
        cross = (v.x - a.x) * (b.y - a.y) - (v.y - a.y) * (b.x - a.x)
        if abs(cross) < 1e-9:
            out.append((v.x, v.y))
    return out


_DEMO = [(0, 0), (50, 0), (50, 15), (35, 15), (25, 25), (0, 25)]
_RIGHT = [(50, 0), (60, 0), (60, 15), (50, 15)]


class TestExpandLeavesNoStraightVertex:

    def test_the_fifth_tests_case(self):
        from ogr_core.geometry.expand_shrink import expand_shrink_external
        r = expand_shrink_external(_ring(_DEMO), _line(_RIGHT))
        verts = r.new_external.vertices
        assert _straight(verts) == [], [(v.x, v.y) for v in verts]
        assert sorted((v.x, v.y) for v in verts) == sorted(
            [(60, 0), (60, 15), (35, 15), (25, 25), (0, 25), (0, 0)])
        assert abs(abs(_signed_area(verts)) - 1200.0) < 1e-9
        # the removed arc is what it was (test_expand_shrink)
        assert [(v.x, v.y) for v in r.removed_arc.vertices] == [
            (50.0, 0.0), (50.0, 15.0)]

    def test_a_cut_point_that_is_a_corner_stays(self):
        """A polyline leaving the edge at an angle: its ends are corners."""
        from ogr_core.geometry.expand_shrink import expand_shrink_external
        r = expand_shrink_external(_ring(_DEMO),
                                   _line([(50, 5), (60, 8), (50, 12)]))
        pts = {(v.x, v.y) for v in r.new_external.vertices}
        assert {(50.0, 5.0), (50.0, 12.0)} <= pts, pts

    def test_a_straight_vertex_of_the_user_is_kept(self):
        """(25, 0) on the bottom edge is the user's: Expand cleans only
        what it made."""
        from ogr_core.geometry.expand_shrink import expand_shrink_external
        ring = [(0, 0), (25, 0)] + _DEMO[1:]
        r = expand_shrink_external(_ring(ring), _line(_RIGHT))
        pts = [(v.x, v.y) for v in r.new_external.vertices]
        assert (25, 0) in pts and (50, 0) not in pts, pts

    def test_the_regions_are_those_without_the_clean_up(self):
        """A material boundary ending ON a cut point that is dropped: the
        regions, their areas and their materials are those of the same
        expand with the clean-up switched off."""
        import ogr_core.geometry.expand_shrink as es
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project.demo import build_demo_project

        def regions(clean):
            p = build_demo_project()
            clay = Material(name="Clay", unit_weight=18.0,
                            strength=MohrCoulomb(cohesion=5.0,
                                                 friction_angle=20.0))
            p.materials.append(clay)
            p.add_boundary(Boundary(polyline=_line([(0, 10), (50, 0)]),
                                    btype=BoundaryType.MATERIAL))
            assert len(p.resolve_regions()) == 2          # the premise
            assert p.assign_material_at(5.0, 2.0, clay.id)
            real = es._drop_straight
            if not clean:
                es._drop_straight = lambda verts, _c: verts
            try:
                es.apply_expand_shrink(p, _line(_RIGHT))
            finally:
                es._drop_straight = real
            # by name: each run makes its materials, with ids of their own
            return sorted((round(abs(_signed_area(r.polygon.vertices)), 9),
                           (p.material_by_id(r.material_id)
                            or p.materials[0]).name)
                          for r in p.resolve_regions())

        got = regions(True)
        assert [name for _a, name in got] == ["Clay", "Silty clay"], got
        assert regions(True) == regions(False)

    def test_undo_and_redo_are_exact(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.project.demo import build_demo_project
        import test_expand_shrink_draw_v1336 as draw
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w._attach_project(build_demo_project())
        try:
            before = _dump(w.project)
            idx = w.project.boundaries.index(w.project.external_boundary())
            w._expand_shrink_draw_mode(idx)       # as the menu enters it
            w.canvas.set_tool_mode(w.canvas.tool_mode.__class__.SELECT)
            with draw._quiet():
                w._on_expand_shrink_polyline_drawn(_line(_RIGHT))
            ext = next(b for b in w.project.boundaries
                       if b.btype == BoundaryType.EXTERNAL)
            # it did expand (the demo's own External has six vertices too)
            verts = ext.polyline.vertices
            assert abs(abs(_signed_area(verts)) - 1200.0) < 1e-9
            assert (60, 0) in [(v.x, v.y) for v in verts]
            assert len(verts) == 6, [(v.x, v.y) for v in verts]
            after = _dump(w.project)
            w.act_undo()
            assert _dump(w.project) == before
            w.act_redo()
            assert _dump(w.project) == after
        finally:
            w.project.is_dirty = False
            w.close()
