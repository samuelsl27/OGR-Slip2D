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
    """Multiply the soil weight of each slice by its permanent-action factor.

    Reads ``project.action_factors`` (``ogr_core.loads.actions``), which only
    the analysis copy of a project with a design standard carries; without
    it, or with factors that change nothing, the slices are left exactly as
    they are. Each slice records the factor it took in ``weight_factor``,
    and the set the sense it was decided with in ``design_sense``.
    """
    actions = getattr(project, "action_factors", None)
    if actions is None or actions.is_identity():
        return
    sense = sliding_sense(slices.slices)
    for s in slices.slices:
        drives = sense * math.sin(s.base_angle) > 0.0
        xi = actions.factor_for(drives)
        soil = s.soil_weight if s.soil_weight is not None else s.weight
        s.weight += (xi - 1.0) * soil
        s.soil_weight = soil * xi
        s.weight_factor = xi
    slices.design_sense = sense
