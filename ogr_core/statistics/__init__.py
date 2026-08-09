# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Statistical distributions and sampling for probabilistic analysis."""
from .distributions import (  # noqa: F401
    Distribution,
    DistributionType,
    SampleStatistics,
    SamplingMethod,
    correlate_pair,
    sample_variables,
    uniform_samples,
)

from .random_variables import (  # noqa: F401
    RandomVariable,
    VariableKind,
    apply_sample,
    available_variables,
    clone_project,
    get_value,
    sample_project_variables,
    set_value,
)

from .probabilistic import (  # noqa: F401
    MethodProbabilisticResult,
    ProbabilisticResult,
    ProbabilisticType,
    run_global_minimum,
    run_overall_slope,
    OverallSlopeResult,
    SurfaceProbability,
)

from .sensitivity import (  # noqa: F401
    SensitivityResult,
    VariableSensitivity,
    run_sensitivity,
)

from .drawdown_sweep import (  # noqa: F401
    DrawdownSweepResult,
    MethodSweep,
    default_levels,
    run_drawdown_sweep,
)

__all__ = [
    "SensitivityResult", "VariableSensitivity", "run_sensitivity",
    "ProbabilisticResult", "MethodProbabilisticResult",
    "ProbabilisticType", "run_global_minimum", "run_overall_slope",
    "OverallSlopeResult", "SurfaceProbability",
    "RandomVariable", "VariableKind", "available_variables",
    "get_value", "set_value", "clone_project", "apply_sample",
    "sample_project_variables",
    "Distribution", "DistributionType", "SamplingMethod",
    "SampleStatistics", "uniform_samples", "sample_variables",
    "correlate_pair",
]
