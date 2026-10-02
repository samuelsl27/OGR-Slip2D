# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D226a — the external anchor of the design standard's permanent-action
factor: the reference's Eurocode 7 tutorial, which is example 5.12 of Smith
(2006), *Smith's Elements of Soil Mechanics*, 8th ed.

An earth dam, (0, 0) (22, 0) (13.39, 5.1) (11.7, 6.1) (10.37, 6.1), γ = 19.2,
c′ = 12 kPa, φ′ = 20°, with the pore pressures of a steady finite-element
seepage under a total head of 5.1 m on the upstream face; the downstream
face slides, right to left, by Bishop's simplified method. Published:

====================  =========  ======================================
Design standard        Published  What it is
====================  =========  ======================================
none                   1.37       the factor of safety
EC7 DA1-C1             1.207      γG = 1.35 on the weight
EC7 DA1-C2             1.096      c′ and tan φ′ divided by 1.25
====================  =========  ======================================

**The invariant.** With DA1-C1 the weight of the slices is multiplied by
γG = 1.35. Until v0.1.241 it was not, and DA1-C1 gave the characteristic
1.36. The tutorial predates the single source option and its 1.207 is the
per-slice rule — 1.35 on the slices whose base drives the sliding, 1.0 on
the five at the toe whose base climbs against it — so it is anchored with
the option OFF; ON (the default, Bond et al. 2013) every weight is exactly
1.35 times the characteristic one and the factor is 1.232, which nothing
publishes and is pinned only through that identity.

**Where.** On the characteristic critical circle of OGR's own Auto Refine
search, (2.791294, 9.554412) R 9.553782, which is also where the DA1-C1
(per slice) and DA1-C2 searches end: a search costs a minute per standard,
and the published numbers are the minimum of each, which this circle is.
Measured on v0.1.242: 1.36028 (−0.71 %), 1.20419 (−0.23 %) and 1.08822
(−0.71 %); the one per cent below is the comparison of the bank's
verification problems. The method's tolerance is tightened to 1e-12: the
project's 0.005 stops Bishop at a value that depends on where its
iteration started, which is how the searches report 1.08802 for the same
circle.

Comparisons are relative, never ``==`` on doubles of different computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

_CIRCLE = dict(centre_x=2.791294, centre_y=9.554412, radius=9.553782)
_PUBLISHED = {"none": 1.37, "eurocode7_da1c1": 1.207,
              "eurocode7_da1c2": 1.096}

_STATE: dict = {}


def _dam():
    """The tutorial's model, built by the operations layer an agent drives,
    with its seepage solved; built once for the file."""
    if "project" in _STATE:
        return _STATE["project"]
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Tutorial 21")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [22, 0], [13.39, 5.1], [11.7, 6.1],
                         [10.37, 6.1]],
            "materials": [{"name": "Dam", "unit_weight": 19.2,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 12.0,
                                                   "friction_angle": 20.0}},
                           "pore_pressure": "fem"}],
            "settings": {"units.failure_direction": "right_to_left",
                         "groundwater.method": "fea_steady"}})
        call(ws, "mesh_generate", project_id=pid)
        call(ws, "seepage_bc_set", project_id=pid, bc_type="total_head",
             along=[[22, 0], [13.39, 5.1]], value=5.1)
        call(ws, "groundwater_run", project_id=pid)
        _STATE["project"] = ws.get(pid).project
    finally:
        ws.shutdown()
    return _STATE["project"]


def _evaluated(standard=None, single=True):
    """Bishop's factor on the circle, through the door every analysis
    takes, and the slices it computed on. The standard is set on the
    model and taken off again: the model is shared by the file."""
    from ogr_core.project.design_factors import prepare_analysis_project
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _dam()
    ds = p.settings.design_standard
    try:
        ds.enabled = standard is not None
        if standard is not None:
            ds.apply_preset(standard)
        ds.single_source_weight = single
        work, _rep = prepare_analysis_project(p)
        c = SlipCircle(**_CIRCLE)
        sl = slice_surface(work, c, num_slices=p.settings.methods.num_slices)
        r = get_method("bishop_simplified")(tolerance=1e-12).compute_fos(
            work, c, sl)
    finally:
        ds.enabled = False
        ds.apply_preset("none")
        ds.single_source_weight = True
    assert r.fos is not None, r
    return float(r.fos), sl


def _within_one_per_cent(got, standard):
    want = _PUBLISHED[standard]
    return abs(got / want - 1.0) < 0.01


class TestTheTutorial:

    def test_the_characteristic_factor(self):
        f, sl = _evaluated()
        assert _within_one_per_cent(f, "none"), f
        assert any(s.pore_pressure > 1.0 for s in sl.slices), (
            "premise: the seepage reaches the surface")

    def test_da1c1_slice_by_slice_is_the_published_one(self):
        f, sl = _evaluated("eurocode7_da1c1", single=False)
        assert _within_one_per_cent(f, "eurocode7_da1c1"), f
        # The five slices at the toe climb against the sliding.
        assert sum(1 for s in sl.slices if s.weight_factor == 1.0) == 5
        assert sum(1 for s in sl.slices if s.weight_factor == 1.35) == (
            len(sl.slices) - 5)

    def test_da1c1_under_the_single_source_assumption(self):
        """Every weight exactly 1.35 times; the factor is another number,
        more than the per-slice one and less than the characteristic."""
        f, sl = _evaluated("eurocode7_da1c1")
        f0, plain = _evaluated()
        per_slice, _sl = _evaluated("eurocode7_da1c1", single=False)
        for a, b in zip(sl.slices, plain.slices):
            assert math.isclose(a.weight, 1.35 * b.weight, rel_tol=1e-14), (
                a.x_centre, a.weight, b.weight)
            # The seepage is not factored. The analysis copy is made through
            # the file format (``Project.from_dict(project.to_dict())``),
            # which keeps the heads to nine significant figures on purpose
            # (``SeepageResult._round``): u = γw·(H − y) comes back within
            # a few 1e-7 kPa, not to the last bit.
            assert math.isclose(a.pore_pressure, b.pore_pressure,
                                rel_tol=0.0, abs_tol=1e-6), (
                a.x_centre, a.pore_pressure, b.pore_pressure)
        assert per_slice < f < f0, (per_slice, f, f0)

    def test_da1c2(self):
        """And it is F/1.25: c′ and tan φ′ divided by 1.25, the weight and
        the seepage untouched (strength reduction)."""
        f, _sl = _evaluated("eurocode7_da1c2")
        f0, _plain = _evaluated()
        assert _within_one_per_cent(f, "eurocode7_da1c2"), f
        assert math.isclose(f, f0 / 1.25, rel_tol=1e-9), (f, f0 / 1.25)

    def test_until_v0_1_241_da1c1_was_the_characteristic_number(self):
        """Rule 7, on the anchor: the factor the tutorial applies moves its
        number, and without it the preset gave back 1.36."""
        import ogr_slip2d.slicer as S
        f0, _plain = _evaluated()
        saved = S.DESIGN_WEIGHT_FACTORS
        try:
            S.DESIGN_WEIGHT_FACTORS = False
            off, _sl = _evaluated("eurocode7_da1c1", single=False)
        finally:
            S.DESIGN_WEIGHT_FACTORS = saved
        # 1e-9 and not less: the copy carries the seepage at file
        # precision (see the single source case above); 6.6e-11 measured.
        assert math.isclose(off, f0, rel_tol=1e-9), (off, f0)
        assert not _within_one_per_cent(off, "eurocode7_da1c1"), off
