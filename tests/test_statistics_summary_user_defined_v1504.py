# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D442, second half (v0.1.504) — the agent learns, as Interpret's status bar
does since v0.1.503, when the critical probabilistic surface is one the user
defined.

The invariant
-------------
``statistics_summary`` (what ``statistics_run`` hands an agent) carries, per
method, ``critical_probabilistic_user_defined``: ``True`` exactly when the
run's critical probabilistic surface is a polyline of the user
(``SurfaceProbability.user_defined``, set by the run), ``False`` for one of
the search, ``None`` when there is no such surface. Before v0.1.504 the key
did not exist: the agent saw the PF of the user's polyline and could not tell
it from a searched surface.

The case is D442's: the demo slope, Path Search of 5 without optimisation,
Janbu, one polyline of the user and a normal cohesion (30 %, range ±60 %),
20 Latin Hypercube samples, Overall Slope. There the polyline is the critical
probabilistic surface with PF 10 %; without it, the critical one is of the
search. No Qt: the rule lives in ``ogr_slip2d`` and ``ogr_api``. Each run is
computed once for the file (a few seconds).
"""
from __future__ import annotations

_POLY = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]
_CACHE: dict = {}


def _summary(with_user: bool) -> dict:
    if with_user in _CACHE:
        return _CACHE[with_user]
    from ogr_api.results import statistics_summary
    from ogr_core.project.demo import build_demo_project
    from ogr_core.project.settings import SurfaceType
    from ogr_core.statistics import SamplingMethod, available_variables
    from ogr_core.statistics.distributions import (Distribution,
                                                   DistributionType as T)
    from ogr_slip2d.analysis_runner import run_configured_statistics
    from ogr_slip2d.surface import UserPolylineSurface

    p = build_demo_project()
    s = p.settings.search
    s.surface_type = SurfaceType.NON_CIRCULAR.value
    s.search_method = "path"
    s.path_num_surfaces, s.optimize_enabled = 5, False
    p.settings.methods.enabled_methods = ["janbu_simplified"]
    if with_user:
        p.user_polylines = [UserPolylineSurface.from_points(_POLY)]
    rv = next(v for v in available_variables(p)
              if v.key.endswith(":cohesion"))
    m = rv.distribution.mean
    rv.distribution = Distribution(T.NORMAL, m, 0.3 * m, 0.6 * m, 0.6 * m)
    p.random_variables = [rv]
    st = p.settings.statistics
    st.probabilistic_analysis, st.sensitivity_analysis = True, False
    st.analysis_type, st.num_samples = "overall_slope", 20
    st.sampling_method = SamplingMethod.LATIN_HYPERCUBE.value
    out = statistics_summary(run_configured_statistics(p))
    _CACHE[with_user] = out
    return out


def _janbu(summary: dict) -> dict:
    methods = summary["probabilistic"]["methods"]
    rows = methods if isinstance(methods, list) else list(methods.values())
    return next(r for r in rows if r["method"] == "janbu_simplified")


class TestTheAgentSeesWhoseTheSurfaceIs:
    def test_the_users_polyline_is_said_to_be_the_users(self):
        row = _janbu(_summary(True))
        assert abs(row["critical_probabilistic_pf"] - 0.10) < 1e-12
        assert row["critical_probabilistic_user_defined"] is True

    def test_a_surface_of_the_search_is_not(self):
        row = _janbu(_summary(False))
        assert row["critical_probabilistic_pf"] is not None
        assert row["critical_probabilistic_user_defined"] is False

    def test_no_surface_no_answer(self):
        # ``None`` and not ``False``: with no critical probabilistic surface
        # there is nobody it could belong to (the D127 policy of its PF).
        from ogr_slip2d.probabilistic import OverallSlopeResult
        row = OverallSlopeResult(method_id="janbu_simplified").summary()
        assert row["critical_probabilistic_pf"] is None
        assert row["critical_probabilistic_user_defined"] is None
