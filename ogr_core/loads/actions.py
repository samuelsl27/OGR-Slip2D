# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The action factors an analysis copy carries, in terms the engine can read.

v0.1.242 (D226a). A design standard factors two kinds of thing. Its MATERIAL
factors change input values (strength parameters), so
``ogr_core.project.design_factors`` applies them to a copy of the project and
the engine never knows. Its ACTION factors cannot all be applied that way:
whether the weight of a slice is a favourable or an unfavourable permanent
action depends on the dip of that slice's base (EN 1997-1, Annex A, Table
A.3), unless the single source option makes it one action, and there is no
slice until a surface is sliced. So the copy is SEALED with these neutral
numbers and the slicer applies them (``ogr_slip2d.design_actions``): the
engine reads factors, never the name of a standard.

v0.1.243 (D226b). The loads too: whether a load helps or drives depends on
the surface it acts on, so each load is factored by the slicer, as a whole,
with the factors of its own action (``ogr_core.loads.LoadAction``).

The seal is not saved (a model read back is a model to factor again), and it
travels with every copy of the analysis project — ``deepcopy`` and pickle
keep instance attributes — which is how a parallel search or a statistical
sample gets it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionFactors:
    """The action factors of one analysis.

    ``permanent_unfavourable`` (γG) multiplies the weight of a slice whose
    base drives the sliding, ``permanent_favourable`` (γG,fav) the weight of
    one whose base resists it; with ``single_source_weight`` every slice takes
    γG, the weight of the soil being one action from one source.

    A load takes γG or γG,fav if it is permanent and ``variable_unfavourable``
    (γQ) or ``variable_favourable`` (γQ,fav) if it is variable, by whether it
    drives the sliding as a whole. ``factors_loads`` False means the loads
    were already multiplied in the copy, the way v0.1.242 did it
    (``design_factors.LOADS_BY_ACTION`` off), and the engine leaves them be.
    """

    permanent_unfavourable: float = 1.0
    permanent_favourable: float = 1.0
    single_source_weight: bool = True
    variable_unfavourable: float = 1.0
    variable_favourable: float = 1.0
    factors_loads: bool = True

    def weight_is_identity(self) -> bool:
        """Whether applying these changes no slice weight."""
        if self.single_source_weight:
            return self.permanent_unfavourable == 1.0
        return (self.permanent_unfavourable == 1.0
                and self.permanent_favourable == 1.0)

    def loads_are_identity(self) -> bool:
        """Whether applying these changes no load."""
        if not self.factors_loads:
            return True
        return (self.permanent_unfavourable == 1.0
                and self.permanent_favourable == 1.0
                and self.variable_unfavourable == 1.0
                and self.variable_favourable == 1.0)

    def is_identity(self) -> bool:
        """Whether applying these changes nothing at all."""
        return self.weight_is_identity() and self.loads_are_identity()

    def factor_for(self, drives: bool) -> float:
        """The factor on the SOIL weight of a slice: γG for one whose base
        drives the sliding (``drives``), γG,fav for one that resists it — or
        γG for both under the single source assumption."""
        if self.single_source_weight or drives:
            return self.permanent_unfavourable
        return self.permanent_favourable

    def load_factor_for(self, action, drives: bool) -> float:
        """The factor on a whole load of ``action`` (a ``LoadAction`` or its
        value) that drives the sliding (``drives``) or resists it. The
        single source assumption is about the soil and does not reach a
        load: each load is its own source."""
        if not self.factors_loads:
            return 1.0
        if getattr(action, "value", action) == "permanent":
            return (self.permanent_unfavourable if drives
                    else self.permanent_favourable)
        return (self.variable_unfavourable if drives
                else self.variable_favourable)

    @classmethod
    def from_settings(cls, ds, factors_loads: bool = True) -> "ActionFactors":
        """From a ``DesignStandardSettings``. Read as they are: the values are
        checked before an analysis by ``rules.design_action_factors_refusal``,
        and an unchecked 0 must not become a silent 1 — least of all γQ,fav,
        whose 0 is the Eurocode's own value."""
        return cls(
            permanent_unfavourable=float(getattr(ds, "factor_permanent", 1.0)),
            permanent_favourable=float(
                getattr(ds, "factor_permanent_favourable", 1.0)),
            single_source_weight=bool(getattr(ds, "single_source_weight",
                                              True)),
            variable_unfavourable=float(getattr(ds, "factor_variable", 1.0)),
            variable_favourable=float(
                getattr(ds, "factor_variable_favourable", 1.0)),
            factors_loads=bool(factors_loads))
