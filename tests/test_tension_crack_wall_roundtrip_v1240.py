# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D90 — the wall of a tension crack is DEDUCED from the model the surface is
sliced on, never carried from another one, and never stored.

**The invariant.** A tension-crack wall is the vertical face of the mass at
its crest, from the crack line up to the ground, and the water in the crack
pushes on it with ½·γw·h² (Duncan, Wright and Brandon 2014, §14.3.2;
Terzaghi 1943). Both ends depend on the model as it is NOW. So:

1. The dictionary of a surface does not carry the wall, and a polyline
   rebuilt from it gets the same wall and the same factor from the model
   (``CRACK_WALL_ON_LINE``, v0.1.208) — also through the statistical rebuild,
   end to end: a Global Minimum run whose samples do not move the slope
   reproduces the deterministic factor to 1e-12, and loses the thrust, on the
   unsafe side, with the switch off (rule 7).
2. A surface that already carries a wall from one model and is sliced again
   on another — the crack lowered, the ground raised — gets the wall of the
   NEW model, and the factor of the same surface evaluated anew there. Until
   v0.1.239 the slicer trusted the old wall on its abscissa alone; measured
   on the phi = 0 slope of ``test_tension_crack_truncation_v1109`` with the
   crack filled: +1.19 % with the crack lowered from 34 to 32, +2.39 % with
   the upper flat raised from 40 to 41, both on the unsafe side, through the
   public ``slice_surface``. The stale wall leaves the drawing too.
3. On an unchanged model the wall the surface carries is kept, with the
   same factor, and drawn once.

Comparisons are relative (1e-12), never ``==`` on doubles.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MID = "bishop_simplified"
_SLICES = 60


def _slope(crack_y=34.0, flat=40.0, extra_material=False):
    """The phi = 0 slope of v1109 (0..100 x 0..40), the crack FILLED, with
    the upper flat at ``flat``; optionally a second material that no region
    uses, to give a statistical run a variable that moves nothing."""
    import test_tension_crack_truncation_v1109 as U
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                 WaterLevelMode)
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(100, 0), Vertex(100, flat),
                             Vertex(60, flat), Vertex(30, 20), Vertex(0, 20)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("phi0 crack")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, crack_y), Vertex(100, crack_y)], closed=False),
        btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(name="Clay", unit_weight=U._GAMMA,
                            strength=MohrCoulomb(cohesion=U._C,
                                                 friction_angle=0.0))]
    if extra_material:
        p.materials.append(Material(name="Unused", unit_weight=18.0,
                                    strength=MohrCoulomb(cohesion=10.0,
                                                         friction_angle=30.0)))
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode.FILLED)
    p.settings.methods.num_slices = _SLICES
    return p


def _arc():
    """The fixture circle of v1109 as a polyline, ground to ground on the
    slope WITHOUT the crack, in 60 chords (the arc of v1208, written out so
    this file also runs on trees older than that test)."""
    import test_tension_crack_truncation_v1109 as U
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    c, sl = U._analysed(U._phi0_slope(crack_y=None), num_slices=60)
    assert sl is not None
    cx, cy, r = (U._CIRCLE["centre_x"], U._CIRCLE["centre_y"],
                 U._CIRCLE["radius"])
    xa, xb = c.x_left, c.x_right
    xs = [xa + (xb - xa) * i / 60.0 for i in range(61)]
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(x, cy - math.sqrt(max(r * r - (x - cx) ** 2, 0.0)))
        for x in xs], closed=False))


def _fos(project, surface):
    """``(factor, wall, thrust)`` of ``surface`` sliced on ``project``."""
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=_SLICES)
    assert sl is not None
    f = float(get_method(_MID)(tolerance=1e-10)
              .compute_fos(project, surface, sl).fos)
    return f, surface.tension_crack_wall, sl.tension_crack_force


def _close(a, b):
    return math.isclose(a, b, rel_tol=1e-12)


def _same_wall(a, b):
    return (a is not None and b is not None
            and all(math.isclose(p, q, rel_tol=1e-12, abs_tol=1e-12)
                    for p, q in zip(a, b)))


# ======================================================================
class TestTheWallIsNotStored:

    def test_no_surface_type_serialises_it(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import (CompositeSurface, SlipCircle,
                                        SlipSurface, WeakLayerSurface)
        wall = (50.0, 30.0, 40.0)
        circle = SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0)
        circle.x_left, circle.x_right = 30.0, 80.0
        bed = Polyline(vertices=[Vertex(0.0, 0.0), Vertex(100.0, 0.0)])
        surfaces = [circle, SlipSurface(polyline=Polyline(vertices=[
                        Vertex(30.0, 20.0), Vertex(80.0, 40.0)])),
                    CompositeSurface(circle=circle, bedrock=bed,
                                     x_left=30.0, x_right=80.0),
                    WeakLayerSurface(base=circle, bands=())]
        for s in surfaces:
            s.tension_crack_wall = wall
            assert "tension_crack_wall" not in s.to_dict(), type(s).__name__

    def test_a_rebuilt_polyline_gets_its_wall_from_the_model(self):
        from ogr_slip2d.surface import SlipSurface
        p = _slope()
        s = _arc()
        f, w, t = _fos(p, s)
        r = SlipSurface.from_dict(s.to_dict())
        assert r.tension_crack_wall is None          # nothing carried
        fr, wr, tr = _fos(p, r)
        assert _same_wall(wr, w) and _close(tr, t) and _close(fr, f)


class TestTheStatisticalRebuildKeepsTheThrust:
    """End to end through ``run_global_minimum``: the variable is the
    cohesion of a material no region uses, so every sample is the
    deterministic model and must give the deterministic factor."""

    def _run(self):
        from ogr_core.statistics import (Distribution, DistributionType,
                                         SamplingMethod, available_variables,
                                         run_global_minimum)
        from ogr_slip2d.analysis_runner import build_search
        p = _slope(extra_material=True)
        det = build_search(p, _MID).evaluate_surface(p, _arc())
        assert det is not None and det.surface.tension_crack_wall is not None
        unused = p.materials[1]
        v = [x for x in available_variables(p)
             if x.param == "cohesion" and x.target_id == unused.id][0]
        v.distribution = Distribution(DistributionType.NORMAL, mean=10.0,
                                      std_dev=2.0, rel_min=6.0, rel_max=6.0)
        res = run_global_minimum(p, {_MID: det}, [v], num_samples=5,
                                 sampling=SamplingMethod.LATIN_HYPERCUBE,
                                 seed=2, num_slices=_SLICES)
        return det, res.by_method[_MID]

    def test_every_sample_is_the_deterministic_factor(self):
        det, m = self._run()
        assert m.statistics.n == 5
        assert all(_close(f, det.fos) for f in m.statistics.values), (
            det.fos, m.statistics.values)

    def test_without_the_wall_on_the_line_the_samples_lose_the_thrust(self):
        import ogr_slip2d.slicer as S
        S.CRACK_WALL_ON_LINE = False
        try:
            det, m = self._run()
        finally:
            S.CRACK_WALL_ON_LINE = True
        assert all(f > det.fos * (1 + 1e-6) for f in m.statistics.values)


# ======================================================================
class TestADraggedWallDoesNotDecide:

    def _dragged(self, new_model):
        """The arc sliced on the original model (crack at 34, flat at 40),
        then handed, the same object, to ``new_model``; and the uncut arc
        evaluated anew there."""
        s = _arc()
        old_f, old_wall, _t = _fos(_slope(), s)
        dragged = _fos(new_model, s)
        fresh = _fos(new_model, _arc())
        return s, old_wall, dragged, fresh

    def test_the_crack_lowered(self):
        s, old_wall, (f, w, t), (ff, wf, tf) = self._dragged(_slope(crack_y=32.0))
        assert w[1] == 32.0 and not _same_wall(w, old_wall)
        assert _same_wall(w, wf) and _close(t, tf) and _close(f, ff), (f, ff)

    def test_the_ground_raised(self):
        s, old_wall, (f, w, t), (ff, wf, tf) = self._dragged(_slope(flat=41.0))
        assert w[2] == 41.0 and not _same_wall(w, old_wall)
        assert _same_wall(w, wf) and _close(t, tf) and _close(f, ff), (f, ff)

    def test_the_stale_wall_leaves_the_drawing(self):
        s, old_wall, (_f, w, _t), _fresh = self._dragged(_slope(crack_y=32.0))
        assert tuple(old_wall) not in s.tension_cracks, s.tension_cracks
        assert tuple(w) in s.tension_cracks

    def test_the_test_of_the_model_s_wall(self):
        from ogr_slip2d.slicer import (_wall_is_the_models,
                                       tension_crack_boundary)
        from ogr_core.geometry import ground_surface
        p = _slope()
        ground = ground_surface(p.external_boundary())
        tc = tension_crack_boundary(p)
        s = _arc()
        _f, wall, _t = _fos(p, s)
        assert _wall_is_the_models(p, tc, ground, wall)
        assert not _wall_is_the_models(p, tc, ground,
                                       (wall[0], wall[1] - 1e-3, wall[2]))
        assert not _wall_is_the_models(p, tc, ground,
                                       (wall[0], wall[1], wall[2] + 1e-3))


class TestAnUnchangedModelKeepsIt:

    def test_the_same_wall_and_factor_to_the_last_bit_drawn_once(self):
        p = _slope()
        s = _arc()
        first = _fos(p, s)
        again = _fos(p, s)
        assert _same_wall(again[1], first[1]) and _close(again[0], first[0]), (
            first, again)
        assert len(s.tension_cracks) == 1, s.tension_cracks
