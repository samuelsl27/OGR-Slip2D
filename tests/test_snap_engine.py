# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for the snap engine (ogr_gui.canvas.snap_engine).

The snap engine is pure-Python (no Qt deps), so we can load it via
importlib and test it in isolation without Qt being installed.
"""
from __future__ import annotations

import importlib.util
import sys
import types


def _load_snap_engine():
    """Load the snap engine without triggering ogr_gui.canvas.__init__.py."""
    spec = importlib.util.spec_from_file_location(
        "ogr_snap_engine_test",
        "ogr_gui/canvas/snap_engine.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ogr_snap_engine_test"] = mod
    spec.loader.exec_module(mod)
    return mod


_se = _load_snap_engine()
SnapEngine = _se.SnapEngine
SnapSettings = _se.SnapSettings
SnapKind = _se.SnapKind


from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex


def _square_boundary() -> Boundary:
    pl = Polyline(
        vertices=[Vertex(0, 0), Vertex(10, 0), Vertex(10, 10), Vertex(0, 10)],
        closed=True,
    )
    return Boundary(polyline=pl, btype=BoundaryType.EXTERNAL)


# ======================================================================
class TestVertexSnap:
    def test_snaps_to_nearby_vertex(self):
        b = _square_boundary()
        eng = SnapEngine(SnapSettings(snap=True))
        # Cursor near vertex (0,0) — well within tolerance at ppu=50
        result = eng.resolve(Vertex(0.15, 0.05), [b], pixels_per_unit=50.0)
        assert result.kind == SnapKind.VERTEX
        assert result.point.x == 0.0
        assert result.point.y == 0.0

    def test_no_snap_when_disabled(self):
        b = _square_boundary()
        eng = SnapEngine(SnapSettings(snap=False))
        result = eng.resolve(Vertex(0.15, 0.05), [b], pixels_per_unit=50.0)
        assert result.kind == SnapKind.NONE
        assert result.point.x == 0.15

    def test_does_not_snap_when_far_away(self):
        b = _square_boundary()
        eng = SnapEngine(SnapSettings(snap=True))
        # At ppu=50, tolerance in world units ~ 12/50 = 0.24
        result = eng.resolve(Vertex(5.0, 5.0), [b], pixels_per_unit=50.0)
        assert result.kind != SnapKind.VERTEX


# ======================================================================
class TestLineSnap:
    def test_snaps_to_nearest_point_on_segment(self):
        b = _square_boundary()
        eng = SnapEngine(SnapSettings(snap=True))
        # Cursor at (5.0, 0.1) — close to the bottom edge y=0
        result = eng.resolve(Vertex(5.0, 0.1), [b], pixels_per_unit=50.0)
        assert result.kind == SnapKind.LINE
        assert abs(result.point.x - 5.0) < 1e-9
        assert abs(result.point.y - 0.0) < 1e-9


# ======================================================================
class TestOrtho:
    def test_ortho_locks_to_horizontal(self):
        eng = SnapEngine(SnapSettings(snap=False, ortho=True))
        eng.set_reference(Vertex(0, 0))
        # Cursor at (5, 1) — horizontal component bigger → lock to y=0
        r = eng.resolve(Vertex(5.0, 1.0), [], pixels_per_unit=50.0)
        assert abs(r.point.y) < 1e-9
        assert r.ortho_active

    def test_ortho_locks_to_vertical(self):
        eng = SnapEngine(SnapSettings(snap=False, ortho=True))
        eng.set_reference(Vertex(0, 0))
        r = eng.resolve(Vertex(1.0, 5.0), [], pixels_per_unit=50.0)
        assert abs(r.point.x) < 1e-9

    def test_ortho_without_reference_is_no_op(self):
        eng = SnapEngine(SnapSettings(snap=False, ortho=True))
        eng.set_reference(None)
        r = eng.resolve(Vertex(5.0, 3.0), [], pixels_per_unit=50.0)
        assert abs(r.point.x - 5.0) < 1e-9
        assert abs(r.point.y - 3.0) < 1e-9


# ======================================================================
class TestNiceStep:
    def test_returns_1_2_5_10_steps(self):
        from ogr_snap_engine_test import nice_step
        # Various scales should produce 1, 2, 5, or 10 × 10^n
        for target in [0.03, 0.05, 0.2, 0.4, 1.2, 3.8, 7.0, 25.0, 60.0, 150.0]:
            s = nice_step(target)
            # Normalise to the decade
            import math
            mag = 10 ** math.floor(math.log10(s))
            normalised = s / mag
            assert normalised in (1.0, 2.0, 5.0, 10.0), \
                f"step {s} for target {target} has normalised {normalised}"
