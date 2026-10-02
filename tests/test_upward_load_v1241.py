# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D232 — a distributed load that points UP pulls the ground: its vertical
component takes weight off the slices beneath it, as the horizontal component,
the vertical-segment case and every line load already did.

**The invariant.** The vertical component of a distributed load enters the
slice weight DOWNWARD POSITIVE AND SIGNED. Until v0.1.240
``slicer._surface_pressure_at`` added ``abs(p·dy)``, so a load pointing up
was applied down: on the phi = 0 slope of ``test_tension_crack_truncation_v1109``,
20 kPa over 16 m of the crest pointing up gave 1.0295, the same as pointing
down, where the equivalent line load gives 1.2069 — and the operations
layer, creating such a load, already said "it pulls the ground".

What each class pins, and against what
--------------------------------------
1. An identity, in the nine methods: slice by slice, the load pointing up
   takes off exactly the weight the same load pointing down puts on (by the
   slicer's own rule, which the identity does not assume), and every method
   gives the same factor on those slices as on the unloaded ones with that
   weight taken off by hand (1e-12).
2. The mirror: a load normal to a flat boundary drawn left to right presses,
   drawn right to left pulls, by the same amount.
3. The other two readers of the same pressure: the vertical stress that
   generates excess pore pressure, and the overburden a support's bond reads
   (clipped at zero, as it always was).
4. Rule 7: with ``SIGNED_SURFACE_PRESSURE`` off, the v0.1.240 behaviour.
5. The operations layer's note on a load drawn right to left is now true.

Comparisons are relative (1e-12), never ``==`` on doubles of different
computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_Q = 20.0                   # kPa
_A, _B = 62.0, 78.0         # the loaded stretch of the crest, at y = 40
_SLICES = 160


def _slope(load=None):
    import test_tension_crack_truncation_v1109 as U
    p = U._phi0_slope(crack_y=None)
    if load is not None:
        p.distributed_loads = [load]
    return p


def _load(direction):
    """20 kPa over the crest: ``up``/``down`` normal to the flat boundary
    (right to left pulls, left to right presses), or ``angle`` degrees."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads.loads import DistributedLoad, LoadOrientation
    a, b = Vertex(_A, 40.0), Vertex(_B, 40.0)
    if direction == "down":
        return DistributedLoad(start=a, end=b, magnitude_1=_Q,
                               orientation=LoadOrientation.NORMAL_TO_BOUNDARY)
    if direction == "up":
        return DistributedLoad(start=b, end=a, magnitude_1=_Q,
                               orientation=LoadOrientation.NORMAL_TO_BOUNDARY)
    return DistributedLoad(start=a, end=b, magnitude_1=_Q,
                           orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL,
                           angle_deg=float(direction))


def _sliced(project):
    import test_tension_crack_truncation_v1109 as U
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    c = SlipCircle(**U._CIRCLE)
    sl = slice_surface(project, c, num_slices=_SLICES)
    assert sl is not None
    return c, sl


def _pressed():
    """What the DOWNWARD load adds to each slice, by the slicer's own rule
    (whatever it is: the identities below do not assume one)."""
    _c, down = _sliced(_slope(_load("down")))
    _c, none = _sliced(_slope())
    return [a.weight - b.weight for a, b in zip(down.slices, none.slices)]


def _close(a, b, rel=1e-12):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


# ======================================================================
class TestAnUpwardLoadTakesWeightOff:

    def test_slice_by_slice_it_takes_off_what_down_puts_on(self):
        _c, up = _sliced(_slope(_load("up")))
        _c, none = _sliced(_slope())
        pressed = _pressed()
        assert len(up.slices) == len(none.slices) == len(pressed)
        assert sum(1 for d in pressed if d > 0.0) > 10, (
            "premise: the load is over the sliding mass")
        for a, b, d in zip(up.slices, none.slices, pressed):
            assert _close(a.weight, b.weight - d), (a.x_centre, a.weight,
                                                     b.weight, d)

    def test_the_nine_methods_give_the_reduced_model_s_factor(self):
        from ogr_slip2d.methods import get_method, method_registry
        p = _slope(_load("up"))
        c, up = _sliced(p)
        _c0, none = _sliced(_slope())
        reduced = copy.deepcopy(none)
        for s, d in zip(reduced.slices, _pressed()):
            s.weight -= d
        names = sorted(method_registry())
        assert len(names) == 9, names
        for name in names:
            m = get_method(name)(tolerance=1e-10)
            fa = m.compute_fos(p, c, up)
            fb = get_method(name)(tolerance=1e-10).compute_fos(p, c, reduced)
            assert fa.is_valid and fb.is_valid, name
            assert _close(fa.fos, fb.fos), (name, fa.fos, fb.fos)

    def test_up_is_the_exact_opposite_of_down(self):
        _c, up = _sliced(_slope(_load("up")))
        _c, down = _sliced(_slope(_load("down")))
        _c, none = _sliced(_slope())
        w0 = sum(s.weight for s in none.slices)
        d_up = sum(s.weight for s in up.slices) - w0
        d_down = sum(s.weight for s in down.slices) - w0
        assert d_down > 300.0 and _close(d_up, -d_down), (d_up, d_down)

    def test_the_physics_ranks_the_three(self):
        """Over the driving side of the mass, a load that presses lowers
        the factor and one that pulls raises it."""
        from ogr_slip2d.methods import get_method

        def fos(p):
            c, sl = _sliced(p)
            return get_method("bishop_simplified")(tolerance=1e-10) \
                .compute_fos(p, c, sl).fos

        assert fos(_slope(_load("down"))) < fos(_slope()) < fos(
            _slope(_load("up")))

    def test_an_inclined_load_keeps_both_signs(self):
        """At 45 degrees up and to the right the weight goes DOWN by
        q·dx·sin 45 — until v0.1.240 it went up by that much."""
        _c, inc = _sliced(_slope(_load(45.0)))
        _c, none = _sliced(_slope())
        s45 = math.sin(math.radians(45.0))
        for a, b, d in zip(inc.slices, none.slices, _pressed()):
            assert _close(a.weight, b.weight - d * s45)


# ======================================================================
class TestTheOtherReadersAgree:

    def test_the_vertical_stress_that_makes_excess_pore_pressure(self):
        from ogr_core.hydraulic.excess_pore_pressure import load_delta_sigma_v
        for direction, sign in (("down", 1.0), ("up", -1.0)):
            ld = _load(direction)
            ld.creates_excess_pore_pressure = True
            p = _slope(ld)
            assert _close(load_delta_sigma_v(p, 70.0), sign * _Q)

    def test_the_overburden_a_support_reads(self):
        """Clipped at zero as it always was: a pull larger than the soil
        above cannot make the bond negative."""
        from ogr_core.support.bond import sigma_v_effective_at
        s_none = sigma_v_effective_at(_slope(), 70.0, 38.0)[0]
        s_down = sigma_v_effective_at(_slope(_load("down")), 70.0, 38.0)[0]
        s_up = sigma_v_effective_at(_slope(_load("up")), 70.0, 38.0)[0]
        assert _close(s_down - s_none, _Q) and _close(s_none - s_up, _Q)
        shallow = sigma_v_effective_at(_slope(_load("up")), 70.0, 39.9)[0]
        assert shallow == 0.0


# ======================================================================
class TestTheSwitch:

    def test_off_an_upward_load_presses_again(self):
        import ogr_slip2d.slicer as S
        _c, down = _sliced(_slope(_load("down")))
        S.SIGNED_SURFACE_PRESSURE = False
        try:
            _c, up = _sliced(_slope(_load("up")))
        finally:
            S.SIGNED_SURFACE_PRESSURE = True
        for a, b in zip(up.slices, down.slices):
            assert _close(a.weight, b.weight)


class TestTheOperationsNoteIsTrue:

    def test_a_load_drawn_right_to_left_is_said_to_pull_and_does(self):
        from ogr_api import Workspace, call
        from ogr_slip2d.slicer import _surface_pressure_at
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="pull")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [100, 0], [100, 40], [60, 40],
                             [30, 20], [0, 20]],
                "materials": [{"name": "Clay", "unit_weight": 19.0,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {
                                                "cohesion": 40.0,
                                                "friction_angle": 0.0}}}]})
            out = call(ws, "load_set", project_id=pid, kind="distributed",
                       start=[_B, 40], end=[_A, 40], magnitude=_Q)
            assert any("UPWARD" in n for n in out["notes"]), out["notes"]
            project = ws.get(pid).project
            assert _close(_surface_pressure_at(project, 70.0), -_Q)
        finally:
            ws.shutdown()
