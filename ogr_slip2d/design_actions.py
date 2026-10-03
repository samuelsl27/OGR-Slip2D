# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The permanent-action factor of a design standard, applied to the weight of
each slice.

v0.1.242 (D226a). Under Eurocode 7 the weight of the soil is a permanent
action: γG multiplies it where it is unfavourable and γG,fav where it is
favourable (EN 1997-1:2004, Annex A, Table A.3: 1.35 and 1.0 in set A1, 1.0
and 1.0 in A2). In a slope, which slices are which depends on the dip of
their base: a slice whose base drives the sliding is unfavourable, one whose
base climbs against it is favourable (the reference's documentation draws
the split at the dashed line through the lowest point of the surface). Its
single source option applies γG to every slice instead — the soil is one
action from one source (Bond et al. 2013) — and that is the default.

Until v0.1.241 the permanent factor was read and never applied: on the
reference's Eurocode 7 tutorial (Smith 2006, example 5.12) the preset
DA1-C1 gave the characteristic 1.36 where the tutorial publishes 1.207.

What is factored is the SOIL part of the weight (``Slice.soil_weight``):
the vertical component of the loads, which the slicer adds to ``weight``,
and the ponded water (``water_weight``) and the water in a tension crack,
which it keeps apart, are not. Everything that reads the weight follows:
the pseudo-static seismic force acts on ``soil_weight``, and the models that
read the vertical stress at the base (Vertical Stress Ratio, SHANSEP) take
it from ``weight``: one weight per slice feeds every term, as in the
reference.

v0.1.243 (D226b): the LOADS as well. Each load is one action from one
source, so it is classed whole — favourable or unfavourable by what it does
on balance to the sliding of the surface — and multiplied by the factor of
its action: γG or γG,fav if it is permanent, γQ or γQ,fav if it is variable
(γQ,fav = 0 in EN 1997-1, Table A.3: a variable load that would help is left
out). See :func:`load_factors`.

Frank, R. et al. (2004). Designers' Guide to EN 1997-1. Thomas Telford,
§11.5: with the whole weight multiplied by γG, the over-design factor of an
undrained slope is F/(γG·γR;e).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math


def sliding_sense(slices) -> float:
    """+1 or −1: the sign of Σ W·sin α over the UNFACTORED slices.

    The sense the weight drives the mass in, which is what decides whether
    the weight of one slice helps or resists. It is Bishop's own reading of
    the sense of sliding with no seismic coefficient
    (``methods.bishop.slide_sense(slices, 0)``), asked before any slice is
    factored so the factors cannot decide the sense they depend on.
    """
    from .methods.bishop import slide_sense
    return slide_sense(slices, 0.0)


def apply_action_factors(project, slices) -> None:
    """Multiply the soil weight of each slice by its permanent-action factor,
    and each load by the factor of its action.

    Reads ``project.action_factors`` (``ogr_core.loads.actions``), which only
    the analysis copy of a project with a design standard carries; without
    it, or with factors that change nothing, the slices are left exactly as
    they are. Each slice records the factor its soil took in
    ``weight_factor``, and the set the sense it was decided with in
    ``design_sense`` and how each load was classed in ``load_factors``.
    """
    actions = getattr(project, "action_factors", None)
    if actions is None or actions.is_identity():
        return
    sense = sliding_sense(slices.slices)
    if not actions.weight_is_identity():
        for s in slices.slices:
            drives = sense * math.sin(s.base_angle) > 0.0
            xi = actions.factor_for(drives)
            soil = s.soil_weight if s.soil_weight is not None else s.weight
            s.weight += (xi - 1.0) * soil
            s.soil_weight = soil * xi
            s.weight_factor = xi
    if not actions.loads_are_identity():
        factors = load_factors(actions, slices.slices, sense)
        for s in slices.slices:
            for load_id, _action, f_v, f_h, y in s.load_parts:
                xi = factors[load_id][2]
                if xi == 1.0:
                    continue
                # What the slicer added for this load, scaled: the vertical
                # part sits in the weight (not in the soil weight, so the
                # seismic coefficients still do not reach it) and the
                # horizontal one in the external channel, moment included.
                s.weight += (xi - 1.0) * f_v
                if f_h:
                    s.add_water_force(f_h=(xi - 1.0) * f_h, y=y)
        # With the load's name, so whatever shows the result can say which
        # load it was without the project in hand.
        names = {ld.id: (ld.name or ld.id) for ld in (
            list(getattr(project, "distributed_loads", None) or [])
            + list(getattr(project, "line_loads", None) or []))}
        slices.load_factors = {
            load_id: (action, drives, xi, names.get(load_id, load_id))
            for load_id, (action, drives, xi) in factors.items()} or None
    slices.design_sense = sense


def load_factors(actions, slices, sense: float) -> dict:
    """``{load_id: (action, drives, factor)}`` for every load on ``slices``.

    v0.1.243 (D226b). A load is classed AS A WHOLE, as one action from one
    source: it drives the sliding when the component of all it puts on the
    mass along the direction of sliding is positive,

        Σ_i s·(f_v,i·sin α_i − f_h,i·cos α_i) > 0,

    with s the sense of sliding (+1 when Σ W·sin α > 0, the mass moving to
    −x), f_v the downward and f_h the +x force it puts on slice i, and α_i
    the base angle — the same reading of "drives" the soil weight gets slice
    by slice. A load that straddles the lowest point of a circle is
    therefore unfavourable or favourable whole, by what it does on balance.
    With the bound of ``rules.design_action_factors_refusal`` (the
    unfavourable factor ≥ 1 ≥ the favourable one ≥ 0) factoring can only
    make that balance larger, so the sense of sliding cannot change.
    """
    driving: dict = {}
    action_of: dict = {}
    for s in slices:
        sin_a, cos_a = math.sin(s.base_angle), math.cos(s.base_angle)
        for load_id, action, f_v, f_h, _y in s.load_parts:
            driving[load_id] = driving.get(load_id, 0.0) + sense * (
                f_v * sin_a - f_h * cos_a)
            action_of[load_id] = action
    out = {}
    for load_id, d in driving.items():
        drives = d > 0.0
        out[load_id] = (action_of[load_id], drives,
                        actions.load_factor_for(action_of[load_id], drives))
    return out
