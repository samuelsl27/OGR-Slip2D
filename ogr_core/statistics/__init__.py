# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Statistical distributions and sampling for probabilistic analysis.

v0.1.346 (D337) -- the runners (``run_global_minimum``, ``run_overall_slope``,
``run_sensitivity`` and their results) are the engine's:
``ogr_slip2d.probabilistic`` and ``ogr_slip2d.sensitivity``.
"""
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
    unwritable_variables,
)

from .drawdown_sweep import (  # noqa: F401
    DrawdownSweepResult,
    MethodSweep,
    default_levels,
    run_drawdown_sweep,
)

#: v0.1.346 (D337) -- the statistical runners run the engine and moved up
#: to ``ogr_slip2d.probabilistic`` and ``ogr_slip2d.sensitivity``. Asked for
#: here, a name of theirs raises an ``ImportError`` that says where it went
#: (PEP 562), rather than an ``AttributeError`` that says nothing.
_MOVED = {
    "MethodProbabilisticResult": "probabilistic",
    "ProbabilisticResult": "probabilistic",
    "ProbabilisticType": "probabilistic",
    "run_global_minimum": "probabilistic",
    "run_overall_slope": "probabilistic",
    "sample_pairs": "probabilistic",
    "OverallSlopeResult": "probabilistic",
    "SurfaceProbability": "probabilistic",
    "SensitivityResult": "sensitivity",
    "VariableSensitivity": "sensitivity",
    "run_sensitivity": "sensitivity",
}


def __getattr__(name):
    where = _MOVED.get(name)
    if where is not None:
        raise ImportError(
            "%s moved from ogr_core.statistics to ogr_slip2d.%s in v0.1.346 "
            "(D337): import it from there." % (name, where))
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


__all__ = [
    "RandomVariable", "VariableKind", "available_variables",
    "get_value", "set_value", "clone_project", "apply_sample",
    "sample_project_variables", "unwritable_variables",
    "Distribution", "DistributionType", "SamplingMethod",
    "SampleStatistics", "uniform_samples", "sample_variables",
    "correlate_pair",
]
