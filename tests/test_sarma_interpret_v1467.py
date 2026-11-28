# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.467 (D357) — Interpret with the wedges of Sarma's method.

WHAT THIS VERSION ADDS

Until v0.1.466 Interpret showed a result of Sarma's method as if its
wedges were vertical slices: the panel said the method does not resolve
the interslice forces (it does, on its inclined faces), a click above an
inclined face picked the neighbouring wedge, the zoom framed the column,
the arrows put W in the middle of the column, the free body diagram was a
message, and the line of thrust said "unavailable" with no reason. And
``base_shear_force`` held the mobilised shear, against the contract of
``LEMResult`` (the driving force s·W·sin α, v0.1.107), which the panel
printed under «Driving shear W·sinα».

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The forces of each wedge are an equilibrium**: on the published
   problem 4 of the verification manual (Hoek 1987), dry and saturated,
   with 2 and 25 wedges and mirrored, the forces
   ``solver.wedge_free_bodies`` gives sum to zero within 1e-9 of the load,
   with the base shear taken from the strength law and not from the rest of
   the balance; and on the saturated case with 2 wedges the effective
   normal on the scarp is the bank's tool's, −20 012.33 kN/m, at 1e-5.
2. **The contract**: Sarma's ``base_shear_force`` is
   ``bishop.driving_shear_forces`` to the bit, and the mobilised shear is in
   ``details["sarma_base_shear"]`` (strength / F).
3. **The window** (offscreen): a click inside the scarp's wedge beyond the
   x range of its base picks it; the zoom frames its polygon; the panel
   gives E, E′, X and θ of its two faces, equal to the method's details;
   the highlight draws one arrow per force; the free body diagram opens
   modeless with the wedge's title and the sum of its forces; the line of
   thrust says its reason; the new labels are in Spanish.
4. **Nothing else moves** (rule 7 both ways): Spencer's panel keeps the
   march's E and X and reports vertical faces.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_wedges_v1463 as W63  # noqa: E402
import test_sarma_pole_v1466 as T66  # noqa: E402

_CACHE: dict = {}


def _p4(wet, n=None, mirror=False):
    from ogr_slip2d.surface import attach_vertex_data
    p, s, angles = W63._problem4(wet, mirror=mirror)
    p.settings.sarma.tolerance = 1e-12
    if n is not None:
        p.settings.sarma.num_slices = n
    attach_vertex_data(s, {k: {"angle": a, "c": None, "phi": None}
                           for k, a in angles.items()})
    return p, s


def _sarma(wet, n=None, mirror=False):
    key = (wet, n, mirror)
    if key not in _CACHE:
        p, s = _p4(wet, n, mirror)
        r, _out = T66._door(p, s)
        _CACHE[key] = (p, r)
    return _CACHE[key]


# ======================================================================
class TestTheForcesOfAWedge:

    def test_each_wedge_is_in_equilibrium(self):
        from ogr_slip2d.postprocess import sarma_wedge_forces
        for wet in (False, True):
            for n in (2, 25):
                for mirror in (False, True):
                    _p, r = _sarma(wet, n, mirror)
                    forces = sarma_wedge_forces(r)
                    assert forces is not None and len(forces) == len(r.slices)
                    load = sum(-f.fy for w in forces for f in w if f.name == "Wv")
                    for w in forces:
                        sx = sum(f.fx for f in w)
                        sy = sum(f.fy for f in w)
                        assert math.hypot(sx, sy) <= 1e-9 * load, (
                            wet, n, mirror, sx, sy)

    def test_and_with_every_force_the_solver_takes(self):
        """The review of v0.1.467: the four cases above have kh = 0, the
        fixed sense, no crack and no horizontal force. Here: a surcharge and
        ponded water, kh and kv, a filled tension crack at the head and
        mirrored (where ``to_solver`` makes it a force on the toe wedge of
        the frame), and problem 5 with the kinematic sense."""
        from ogr_slip2d.postprocess import sarma_wedge_forces
        from ogr_slip2d.surface import attach_vertex_data
        cases = []
        for kw in (dict(), dict(kh=0.15, kv=0.05), dict(crack=True),
                   dict(crack=True, mirror=True)):
            p, s = W63._slope(**kw)
            cases.append((repr(kw), p, s))
        p, s, angles, strengths = W63._problem5(1.0)
        p.settings.sarma.num_slices = 9
        p.settings.sarma.shear_sense = "kinematic"
        attach_vertex_data(s, {k: {"angle": angles[k], "c": strengths[k][0],
                                   "phi": strengths[k][1]} for k in angles})
        cases.append(("problem 5, kinematic", p, s))
        for label, p, s in cases:
            p.settings.sarma.tolerance = 1e-12
            r, _out = T66._door(p, s)
            assert r.fos is not None, label
            forces = sarma_wedge_forces(r)
            load = sum(-f.fy for w in forces for f in w if f.name == "Wv")
            for w in forces:
                sx = sum(f.fx for f in w)
                sy = sum(f.fy for f in w)
                assert math.hypot(sx, sy) <= 1e-9 * load, (label, sx, sy)

    def test_the_mirror_is_the_mirror_image(self):
        """The mirrored slope (sliding the other way, the solver reflects
        it) gives every force as the mirror image of the original's, on
        the mirrored wedge and face: the equilibrium alone cannot tell a
        reflection left undone."""
        from ogr_slip2d.postprocess import sarma_wedge_forces
        for wet in (False, True):
            fa = sarma_wedge_forces(_sarma(wet, 25)[1])
            fb = sarma_wedge_forces(_sarma(wet, 25, True)[1])
            n = len(fa)
            assert len(fb) == n
            load = sum(-f.fy for w in fa for f in w if f.name == "Wv")
            for i in range(n):
                assert {f.face for f in fa[i] if f.face is not None} == {i, i + 1}
                mirror = {(f.name, f.face): f for f in fb[n - 1 - i]}
                for f in fa[i]:
                    g = mirror[(f.name, None if f.face is None else n - f.face)]
                    assert abs(f.fx + g.fx) <= 1e-7 * load, (wet, i, f, g)
                    assert abs(f.fy - g.fy) <= 1e-7 * load, (wet, i, f, g)
                    assert abs(f.x + g.x) <= 1e-6 and abs(f.y - g.y) <= 1e-6

    def test_the_scarp_normal_is_the_tools(self):
        import test_sarma_solver_v1461 as S61
        from ogr_slip2d.postprocess import sarma_wedge_forces
        _p, r = _sarma(True, 2)
        scarp = sarma_wedge_forces(r)[-1]
        n = next(f for f in scarp if f.name == "N′")
        a = r.slices[-1].base_angle
        normal = n.fx * -math.sin(a) + n.fy * math.cos(a)
        assert abs(normal / S61._TOOL_SCARP_NORMAL - 1.0) <= 1e-5, normal

    def test_the_base_shear_is_the_driving_force(self):
        from ogr_slip2d.methods.bishop import driving_shear_forces
        for n in (2, 25):
            _p, r = _sarma(True, n)
            d = r.details
            assert r.base_shear_force == driving_shear_forces(
                list(r.slices), d["kh"], d["kv"], d["slide_sign"])
            assert d["sarma_base_shear"] == [
                t / r.fos for t in r.base_shear_strength]


# ======================================================================
_WINDOWS: list = []


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _window(result, project):
    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d.search import SearchResult
    app = _app()
    set_language("en")
    sr = SearchResult(method_id=result.method_id)
    sr.evaluations = [result]           # the critical is derived from it
    w = InterpretWindow(project, {result.method_id: sr}, None)
    w.resize(1200, 800)
    w.show()
    app.processEvents()
    _WINDOWS.append(w)
    return w


def _row(w, label):
    t = w.slice_dock.table
    for i in range(t.rowCount()):
        if t.item(i, 0) is not None and t.item(i, 0).text() == label:
            return t.item(i, 1).text()
    raise AssertionError("no row %r" % label)


def _inside_beyond_its_base(s):
    """A point inside the wedge's polygon with x left of its base."""
    from shapely.geometry import Point, Polygon
    P = Polygon(s.polygon)
    xmin, ymin, xmax, ymax = P.bounds
    for i in range(1, 60):
        for j in range(1, 60):
            x = xmin + (xmax - xmin) * i / 60.0
            y = ymin + (ymax - ymin) * j / 60.0
            if x < s.base_x_left - 0.05 and P.contains(Point(x, y)):
                return x, y
    raise AssertionError("no point of the wedge left of its base")


class TestTheWindow:

    def _picked(self):
        p, r = _sarma(True, 25)
        w = _window(r, p)
        w._query_slice()
        s = r.slices[-1]                       # the scarp's head wedge
        x, y = _inside_beyond_its_base(s)
        w.canvas.scene_clicked.emit(float(x), float(y))
        _app().processEvents()
        return w, r, s

    def test_a_click_beyond_an_inclined_face_picks_its_wedge(self):
        w, r, s = self._picked()
        try:
            got, res = w.slice_dock.current()
            assert got is not None and got.index == s.index, (
                getattr(got, "index", None), s.index)
            # the base column alone would have said the neighbour
            x, _y = _inside_beyond_its_base(s)
            col = [q for q in r.slices if q.base_x_left <= x <= q.base_x_right]
            assert col and col[0].index != s.index
        finally:
            w.close()

    def test_the_panel_gives_its_faces(self):
        w, r, s = self._picked()
        try:
            d = r.details
            i = s.index
            assert _row(w, "Resolved by this method") == "yes"
            # the rule of the datum (v0.1.91): Sarma publishes its faces'
            from ogr_gui.interpret_window import _SliceDataDock as D
            assert D.solves_interslice(r)
            for label, key, side in (
                    ("E left (kN/m)", "sarma_face_thrusts", 0),
                    ("E right (kN/m)", "sarma_face_thrusts", 1),
                    ("X left (kN/m)", "sarma_face_shears", 0),
                    ("X right (kN/m)", "sarma_face_shears", 1),
                    ("E′ left (kN/m)", "sarma_face_effective", 0),
                    ("E′ right (kN/m)", "sarma_face_effective", 1)):
                assert float(_row(w, label)) == round(d[key][i + side], 2), (
                    label, _row(w, label), d[key][i + side])
            faces = r.slices.faces
            for label, side in (("Face angle left θ (°)", 0),
                                ("Face angle right θ (°)", 1)):
                want = round(math.degrees(faces[i + side].theta), 2)
                assert float(_row(w, label)) == want, (label, want)
            want = round(r.base_shear_force[i], 2)
            assert float(_row(w, "Driving shear W·sinα (kN/m)")) == want
        finally:
            w.close()

    def test_the_zoom_and_the_arrows(self):
        from PySide6.QtWidgets import QGraphicsLineItem
        from ogr_slip2d.postprocess import sarma_wedge_forces
        w, r, s = self._picked()
        try:
            asked = []
            raw = w.canvas.zoom_to_point
            w.canvas.zoom_to_point = lambda x, y, half_width: asked.append(
                (x, y, half_width))
            try:
                w._zoom_to_current_slice()
            finally:
                w.canvas.zoom_to_point = raw
            xs = [q[0] for q in s.polygon]
            ys = [q[1] for q in s.polygon]
            x, y, _h = asked[-1]
            assert abs(x - 0.5 * (min(xs) + max(xs))) <= 1e-9
            assert abs(y - 0.5 * (min(ys) + max(ys))) <= 1e-9
            live = [f for f in sarma_wedge_forces(r)[s.index]
                    if math.hypot(f.fx, f.fy) > 1e-9]
            lines = [it for it in w.canvas.scene().items()
                     if getattr(it, "_is_slice_highlight", False)
                     and isinstance(it, QGraphicsLineItem)]
            assert len(lines) == 3 * len(live), (len(lines), len(live))
        finally:
            w.close()

    def test_the_free_body_diagram_and_the_line_of_thrust(self):
        from PySide6.QtWidgets import QInputDialog
        import test_interpret_charts_v1435 as C
        w, r, s = self._picked()
        try:
            with C._no_modals(), C._swapped(
                    QInputDialog, "getInt",
                    staticmethod(lambda *a, **k: (s.index + 1, True))):
                body = w._free_body_diagram()
            try:
                texts = C._texts_of_figure(body)
                assert any(t.startswith("Wedge %d:" % (s.index + 1))
                           for t in texts), texts
                assert any(t.startswith("Sum of the forces") for t in texts)
                assert not body.isModal()
            finally:
                body.close()
            w._thrust_visible = True
            w._redraw_thrust_line()
            assert "Sarma" in w.statusBar().currentMessage()
        finally:
            w.close()

    def test_a_click_just_above_the_ground_picks_the_nearest_wedge(self):
        """Outside every polygon, the nearest among those whose extent covers
        the click's x (the review of v0.1.467: the base's x range picked a
        wedge 35 m away)."""
        from shapely.geometry import LineString, Point, Polygon
        p, r = _sarma(True, 25)
        w = _window(r, p)
        try:
            w._query_slice()
            head = r.slices[-1]
            ring = Polygon(head.polygon)
            xmin, _ymin, xmax, ymax = ring.bounds
            for k in range(1, 6):
                x = xmin + (xmax - xmin) * k / 6.0
                top = ring.intersection(LineString([(x, -1e3), (x, 1e3)])).bounds[3]
                y = top + 0.5
                near = min(r.slices, key=lambda q: Polygon(q.polygon).distance(
                    Point(x, y)))
                w.canvas.scene_clicked.emit(float(x), float(y))
                _app().processEvents()
                got, _res = w.slice_dock.current()
                assert got.index == near.index, (x, got.index, near.index)
                assert Polygon(got.polygon).distance(Point(x, y)) <= 1.0
        finally:
            w.close()

    def test_the_diagram_writes_the_signs(self):
        """The scarp of the published saturated problem 4 is in effective
        tension (N′ = −20 012 kN/m), which is Sarma's (1973) physical
        acceptability to check: the label says it with its sign."""
        from PySide6.QtWidgets import QInputDialog
        import test_interpret_charts_v1435 as C
        p, r = _sarma(True, 2)
        w = _window(r, p)
        try:
            with C._no_modals(), C._swapped(
                    QInputDialog, "getInt",
                    staticmethod(lambda *a, **k: (2, True))):
                body = w._free_body_diagram()
            try:
                texts = C._texts_of_figure(body)
                assert "N′=-20012.3" in texts, texts
            finally:
                body.close()
        finally:
            w.close()

    def test_when_the_forces_cannot_be_recovered(self):
        """Said with the true reason, before the number is asked, and the
        highlight draws the polygon alone: never the arrows of a vertical
        slice on a wedge."""
        from PySide6.QtWidgets import QGraphicsLineItem, QInputDialog
        import ogr_gui.interpret_window as IW
        import test_interpret_charts_v1435 as C
        w, r, s = self._picked()
        try:
            def asked(*a, **k):
                raise AssertionError("the number was asked")
            with C._swapped(IW, "_wedge_forces", lambda result: None), \
                    C._swapped(QInputDialog, "getInt", staticmethod(asked)):
                assert w._free_body_diagram() is None
                assert "could not be recovered" in w.statusBar().currentMessage()
                w._highlight_slice(s, r)
                lines = [it for it in w.canvas.scene().items()
                         if getattr(it, "_is_slice_highlight", False)
                         and isinstance(it, QGraphicsLineItem)]
                assert lines == []
        finally:
            w.close()

    def test_the_new_labels_speak_spanish(self):
        from ogr_gui.i18n import _DICTS, current_language, set_language, tr
        es = _DICTS["es"]
        for label in ("E′ left (kN/m)", "E′ right (kN/m)", "Face angle left θ (°)",
                      "Face angle right θ (°)", "Wedge number:",
                      "Wedge %d of %d — x from %.2f to %.2f",
                      "Free Body Diagram — wedge {0} ({1})"):
            assert label in es and es[label] != label, label
        was = current_language()
        set_language("es")
        try:
            assert tr("Wedge {0}: α={1:.1f}°, FoS={2:.4f}").startswith("Cuña")
        finally:
            set_language(was)


# ======================================================================
class TestNothingElseMoves:

    def test_spencer_keeps_its_march(self):
        from ogr_gui.interpret_window import _SliceDataDock as D
        p, s = _p4(False, 2)
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        r = evaluate_surfaces(p, s, ["spencer"]).results["spencer"]
        sl = r.slices[len(r.slices) // 2]
        assert D._inter(r, sl, "E", 0) != "—"
        assert D._inter(r, sl, "E′", 0) == "—"
        assert D._face_angle(r, sl, 0) == 90.0
        assert not D._is_sarma(r)
