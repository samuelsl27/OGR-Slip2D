# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.368 (D347) — no slip surface on the canvas starts at (0, 0): every arc
starts at its own left end.

The finding (the fifth interface test, 0.1.355, H13): after Compute on the
demo slope a straight segment ran from the vertex (0, 0) to about (20, 21)
among the valid surfaces. Measured (rule 6) through the real scene:
``SlipSurfaceItem`` drew each circle as 61 points from ``x_left`` to
``x_right`` and skipped any with ``R² − (x − xc)² < 0``. The demo's lowest
row of grid centres sits at the crest's elevation, so those circles meet the
crest with a vertical tangent and ``x_left`` lands a few ulps OUTSIDE the
circle (disc ≈ −1e−14). The first point was skipped, the path then began
with a ``lineTo`` — and a QPainterPath draws a first ``lineTo`` from its
origin, (0, 0). The core has always taken such an end as on the circle
(``SlipCircle._lower_arc_disc``, ``_ARC_EPS``, since the D23 tangent of
v0.1.100); the canvas did not. ``SlipRadiiItem`` had the same strict test
and dropped the radius to that end.

What these tests protect:

* on the demo, computed, in the "minimum" view and in the "all" view, no
  circle's path begins at the origin, and each begins at its left end, on
  the arc;
* the premise is exercised: some of the demo's surfaces do have their left
  end outside the circle by rounding (counted from the surfaces themselves);
* a circle whose end is one ulp outside starts there, and both its radii are
  drawn;
* the factor of safety of the demo is the one it always was.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_DEMO_FS = 1.0914331494631124


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _computed_demo():
    from ogr_gui.main_window import MainWindow, _ComputeWorker
    _app()
    w = MainWindow()
    w.act_load_demo()
    w.worker = _ComputeWorker(w.project, ["bishop_simplified"])
    w.worker.run()
    w._on_compute_done(w.worker.results)
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()
    w.deleteLater()


def _circles(w):
    from ogr_gui.canvas.graphics_items import SlipSurfaceItem
    return [it for it in w.canvas.scene().items()
            if isinstance(it, SlipSurfaceItem)
            and it.surface_dict.get("type", "circle") == "circle"
            and it.surface_dict.get("x_left") is not None]


def _first(item):
    p = item.path()
    assert p.elementCount() > 0
    e = p.elementAt(0)
    return e.x, e.y, e.isMoveTo()


def _check(items):
    """No path from the origin; every path from its own left end."""
    assert items, "no circle on the canvas"
    for it in items:
        d = it.surface_dict
        x, y, move = _first(it)
        r, xc, yc, xl = d["radius"], d["centre_x"], d["centre_y"], d["x_left"]
        assert move
        assert not (x == 0.0 and y == 0.0 and abs(xl) > 1e-6), d
        assert abs(x - xl) <= 1e-9 * r, (x, xl)
        on_arc = yc - math.sqrt(max(0.0, r * r - (xl - xc) ** 2))
        assert abs(y - on_arc) <= 1e-6 * r, (y, on_arc)


def _outside(items):
    """Surfaces whose left end is outside their circle by rounding."""
    n = 0
    for it in items:
        d = it.surface_dict
        if d["radius"] ** 2 - (d["x_left"] - d["centre_x"]) ** 2 < 0:
            n += 1
    return n


class TestTheDemoSlope:

    def test_the_minimum_view(self):
        w = _computed_demo()
        try:
            crit = w.last_search_result.critical
            assert crit.fos == _DEMO_FS, crit.fos
            _check(_circles(w))
        finally:
            _done(w)

    def test_the_all_view_with_the_premise(self):
        w = _computed_demo()
        try:
            w.canvas.display_search_result(w.last_search_result,
                                           surface_mode="all")
            items = _circles(w)
            assert _outside(items) > 0, \
                "no surface with its end outside by rounding: premise lost"
            _check(items)
        finally:
            _done(w)


class TestOneCircle:

    def test_an_end_one_ulp_outside(self):
        from ogr_gui.canvas.graphics_items import SlipRadiiItem, SlipSurfaceItem
        _app()
        xc, yc, r = 35.0, 25.0, 15.508
        xl = math.nextafter(xc - r, -math.inf)       # just past the circle
        assert r * r - (xl - xc) ** 2 < 0
        d = {"type": "circle", "centre_x": xc, "centre_y": yc, "radius": r,
             "x_left": xl, "x_right": 45.0}
        item = SlipSurfaceItem(d, 1.2)
        x, y, move = _first(item)
        assert move and x == xl and abs(y - yc) < 1e-6, (x, y)
        radii = SlipRadiiItem(d)
        moves = [radii.path().elementAt(i).isMoveTo()
                 for i in range(radii.path().elementCount())]
        assert moves.count(True) == 2, moves      # both radii drawn
