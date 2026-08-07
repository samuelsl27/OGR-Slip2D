# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Project-level data model, settings and serialization."""
from .project import FILE_FORMAT_VERSION, Project
from .results_io import RESULTS_FORMAT_VERSION, load_summary, save_results
from .settings import (
    AdvancedSettings,
    GroundwaterMethod,
    GroundwaterSettings,
    LEMMethod,
    MethodsSettings,
    ProjectSettings,
    ProjectSummary,
    SearchMethod,
    SearchSettings,
    StatisticsSettings,
    SurfaceType,
)
from .units import (
    FailureDirection,
    PermeabilityUnit,
    TimeUnit,
    Units,
    UnitSystem,
)

__all__ = [
    "Project",
    "FILE_FORMAT_VERSION",
    "RESULTS_FORMAT_VERSION",
    "save_results",
    "load_summary",
    "ProjectSettings",
    "ProjectSummary",
    "MethodsSettings",
    "GroundwaterSettings",
    "SearchSettings",
    "StatisticsSettings",
    "AdvancedSettings",
    "LEMMethod",
    "GroundwaterMethod",
    "SearchMethod",
    "SurfaceType",
    "Units",
    "UnitSystem",
    "TimeUnit",
    "PermeabilityUnit",
    "FailureDirection",
]

from .design_factors import (  # noqa: E402,F401
    FactorReport,
    apply_design_factors,
    factor_friction_angle,
)
