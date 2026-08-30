# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
OGR Slip2D — 2D slope-stability analysis via Limit Equilibrium Methods.

This is the numerical solver of the suite. It is pure-Python + NumPy,
with no dependencies on Qt or any GUI framework.

Public API:
    from ogr_slip2d import (
        SlipCircle, SlipSurface, Slice, Slices,
        BishopSimplified, JanbuSimplified, OrdinaryFellenius,
        GridSearch, SlopeSearch,
        compute,
    )

Author: Samuel Sáez López — PhD Student, UPCT
"""
__version__ = "0.1.133"

from .methods import (
    BishopSimplified,
    CorpsOfEngineers1,
    CorpsOfEngineers2,
    GLEMorgensternPrice,
    JanbuCorrected,
    JanbuSimplified,
    LEMResult,
    LoweKarafiath,
    OrdinaryFellenius,
    Spencer,
    method_registry,
)
from .methods.gle import constant, half_sine, trapezoidal
from .search import (
    AutoRefineSearch,
    BlockSearch,
    GridSearch,
    PathSearch,
    SearchResult,
    SimulatedAnnealingSearch,
    SlopeSearch,
)
from .slicer import Slice, Slices, slice_surface
from .surface import SlipCircle, SlipSurface

__all__ = [
    "SlipCircle",
    "SlipSurface",
    "Slice",
    "Slices",
    "slice_surface",
    "BishopSimplified",
    "JanbuSimplified",
    "JanbuCorrected",
    "OrdinaryFellenius",
    "Spencer",
    "GLEMorgensternPrice",
    "LoweKarafiath",
    "CorpsOfEngineers1",
    "CorpsOfEngineers2",
    "constant",
    "half_sine",
    "trapezoidal",
    "LEMResult",
    "method_registry",
    "GridSearch",
    "SlopeSearch",
    "AutoRefineSearch",
    "BlockSearch",
    "PathSearch",
    "SimulatedAnnealingSearch",
    "SearchResult",
]

from .focus import (  # noqa: E402,F401
    FocusKind,
    FocusObject,
    accepts,
    accepts_surface,
    filter_circles,
)
from .optimize import (  # noqa: E402,F401
    OptimizeReport,
    OptimizeSettings,
    optimize_surface,
)
