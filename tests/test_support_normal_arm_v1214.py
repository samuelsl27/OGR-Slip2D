# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — on a surface with no centre, the NORMAL part of the reinforcement
takes its moment support by support, each at its own crossing (defect D150 of
the verification bank).

THE DEFECT. ``moment_terms`` took the moment of the normal part of every
support crossing a slice at ``(x_app, y_app)``, the crossings' mean weighted
by |F|. The arm of a sum of forces is not the sum of the arms unless the
weights are the moments themselves, so with two supports of different
orientation on one slice of a polyline the moment was taken where no force
acts. D144 (v0.1.178) had already made the CIRCULAR path exact per effect;
this is the non-circular half, the only one left.

What is NOT touched, and why it is exact already: the TANGENTIAL part. The
base of a polyline slice is a straight segment, the support crosses it ON
that segment and the tangential force is directed along it, so moving it
from the crossing to the base midpoint slides it along its own line of
action and does not change its moment about any axis.

THE INVARIANTS.

1. An IDENTITY: the moment of the normal parts about the axis of
   ``axis_for`` equals the sum, support by support, of
   ``(P_j − O) × n_j`` with ``n_j`` the normal part of support ``j`` at its
   crossing ``P_j`` — to 1e-12, on every mesh that puts two supports on one
   slice.
2. The CONTROL that makes it a measurement: the moment from the mean point
   does NOT satisfy it.
3. One support per slice — every critical surface of the verification bank —
   is bit for bit what it was.
4. Rule 7: with ``NORMAL_PART_PER_EFFECT`` off the mean point is back.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _switch(on):
    from ogr_slip2d import support_integration as si
    old = getattr(si, "NORMAL_PART_PER_EFFECT", None)
    si.NORMAL_PART_PER_EFFECT = on
    return old


def _restore(old):
    from ogr_slip2d import support_integration as si
    if old is None:
        vars(si).pop("NORMAL_PART_PER_EFFECT", None)
    else:
        si.NORMAL_PART_PER_EFFECT = old


def _normal_moment(project, surface, sl, on):
    """``moment_terms`` with everything but the support's normal part at
    zero, so ``external`` IS that moment."""
    from ogr_slip2d.moment_balance import axis_for, moment_terms
    from ogr_slip2d.support_integration import resolve_support_terms
    s_list = sl.slices
    sign = 1.0 if sum(s.weight * math.sin(s.base_angle)
                      for s in s_list) >= 0 else -1.0
    old = _switch(on)
    try:
        sup = resolve_support_terms(project, surface, sl, sign)
        axis = axis_for(project, surface)
        zeros = [0.0] * len(s_list)
        mt = moment_terms(axis, s_list, zeros, zeros, zeros, sup=sup)
    finally:
        _restore(old)
    return axis, sup, mt.external


def _per_effect(project, surface, sl, axis):
    """Σ (P_j − O) × n_j, written out from the effects."""
    from ogr_slip2d.support_integration import compute_support_effects
    ox, oy = axis
    total = 0.0
    for e in compute_support_effects(project, surface, sl):
        a = sl.slices[e.slice_index].base_angle
        t_n = e.force_h * math.sin(a) - e.force_v * math.cos(a)
        fx, fy = t_n * math.sin(a), -t_n * math.cos(a)
        total += (e.intersection_x - ox) * fy - (e.intersection_y - oy) * fx
    return total


def _pair():
    """Two anchors of ``test_support_arm_v1178`` (capacity 120 each), one
    horizontal and one at 25°, with heads 0.6 m apart so that they cross the
    SAME segment of the polyline of ``test_support_noncircular_v1140``
    (at x = 48.10 and 48.64). That module's own pair, heads 2 m apart, is
    split by the polyline vertex at x = 49.87 on every mesh."""
    from ogr_core.support import ForceOrientation
    from test_support_arm_v1178 import _anchor, _project
    return _project([_anchor(41.0, ForceOrientation.HORIZONTAL),
                     _anchor(41.6, ForceOrientation.USER_DEFINED,
                             angle=25.0)])


def _meshes(shared):
    """(project, surface, slices) for the meshes of the polyline that put
    the two anchors on one slice (``shared``) or on two."""
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    from test_support_noncircular_v1140 import _polyline
    p, surf = _pair(), _polyline()
    out = []
    for n in range(5, 40):
        sl = slice_surface(p, surf, num_slices=n)
        if sl is None or not sl.slices:
            continue
        effs = compute_support_effects(p, surf, sl)
        if len(effs) != 2:
            continue
        if (effs[0].slice_index == effs[1].slice_index) == shared:
            out.append((p, surf, sl))
    return out


def _shared_meshes():
    out = _meshes(True)
    # Every case below loops over these: an empty list would pass them all.
    assert len(out) >= 5, len(out)
    return out


# ======================================================================
class TestTheNormalPartIsSummedPerEffect:

    def test_there_are_meshes_that_share_a_slice(self):
        assert len(_shared_meshes()) >= 2

    def test_the_moment_is_the_sum_of_the_moments(self):
        for p, surf, sl in _shared_meshes():
            axis, _sup, got = _normal_moment(p, surf, sl, True)
            exact = _per_effect(p, surf, sl, axis)
            assert abs(got - exact) <= 1e-12 * max(1.0, abs(exact)), (
                len(sl.slices), got, exact)

    def test_and_the_mean_point_is_not(self):
        """The control: from ``(x_app, y_app)`` the moment differs, so the
        identity above measured something."""
        for p, surf, sl in _shared_meshes():
            axis, sup, _got = _normal_moment(p, surf, sl, True)
            ox, oy = axis
            i = next(k for k, v in enumerate(sup.n_press) if v)
            mean = ((sup.x_app[i] - ox) * sup.nf_v[i]
                    - (sup.y_app[i] - oy) * sup.nf_h[i])
            exact = _per_effect(p, surf, sl, axis)
            assert abs(mean - exact) > 1e-6 * abs(exact), (mean, exact)


class TestOneSupportPerSliceDoesNotMove:

    def test_bit_for_bit(self):
        split = _meshes(False)
        assert len(split) >= 5, len(split)
        for p, surf, sl in split:
            _a, _s, on = _normal_moment(p, surf, sl, True)
            _a, _s, off = _normal_moment(p, surf, sl, False)
            assert on == off, (len(sl.slices), on, off)


class TestRuleSeven:

    def test_off_the_mean_point_is_back(self):
        for p, surf, sl in _shared_meshes():
            axis, sup, off = _normal_moment(p, surf, sl, False)
            ox, oy = axis
            mean = sum((sup.x_app[i] - ox) * sup.nf_v[i]
                       - (sup.y_app[i] - oy) * sup.nf_h[i]
                       for i in range(len(sl.slices))
                       if sup.nf_h[i] or sup.nf_v[i])
            assert abs(off - mean) <= 1e-12 * max(1.0, abs(mean)), (off, mean)
