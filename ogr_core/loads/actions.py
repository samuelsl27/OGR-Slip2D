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
    """The permanent-action factors of one analysis.

    ``permanent_unfavourable`` (γG) multiplies the weight of a slice whose
    base drives the sliding, ``permanent_favourable`` (γG,fav) the weight of
    one whose base resists it; with ``single_source_weight`` every slice takes
    γG, the weight of the soil being one action from one source.
    """

    permanent_unfavourable: float = 1.0
    permanent_favourable: float = 1.0
    single_source_weight: bool = True

    def is_identity(self) -> bool:
        """Whether applying these changes no slice weight."""
        if self.single_source_weight:
            return self.permanent_unfavourable == 1.0
        return (self.permanent_unfavourable == 1.0
                and self.permanent_favourable == 1.0)

    def factor_for(self, drives: bool) -> float:
        """γG for a slice whose base drives the sliding (``drives``), γG,fav
        for one that resists it — or γG for both under the single source
        assumption."""
        if self.single_source_weight or drives:
            return self.permanent_unfavourable
        return self.permanent_favourable

    @classmethod
    def from_settings(cls, ds) -> "ActionFactors":
        """From a ``DesignStandardSettings``. Read as they are: the values are
        checked before an analysis by ``rules.design_action_factors_refusal``,
        and an unchecked 0 must not become a silent 1."""
        return cls(
            permanent_unfavourable=float(getattr(ds, "factor_permanent", 1.0)),
            permanent_favourable=float(
                getattr(ds, "factor_permanent_favourable", 1.0)),
            single_source_weight=bool(getattr(ds, "single_source_weight",
                                              True)))
