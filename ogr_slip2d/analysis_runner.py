# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The one place an analysis is configured from a project.

v0.1.77. Everything here used to live inside ``_ComputeWorker`` in
``ogr_gui/main_window.py``, which meant it lived inside a ``QThread`` —
so the only way to run a project *as the user configured it* was through
the graphical interface. ``ogr_cli.compute`` therefore read nothing from
``project.settings`` at all: it deserialised the geometry and the
materials and built its own search from command-line defaults.

That failed silently and on the unsafe side in three separate ways:

- **rapid drawdown** was never applied, so a terminal run of a drawdown
  project reported the ordinary factor of safety (noted as pending in the
  changelogs of v0.1.72, v0.1.74 and v0.1.75);
- **design-standard partial factors** were never applied, so the analysis
  used unfactored c', φ' and γ;
- a **finite-element seepage field** is not serialised into the ``.ogr``,
  and the pore-pressure lookup falls back to ``u = 0``, so the run
  reported a dry slope.

Plus everything that merely gave a *different* answer: four of the six
search strategies unreachable, the convergence settings, the seed, the
admissibility checks, and the number of slices.

The design rule this module exists to enforce is the one
``rapid_drawdown.wrap_for_drawdown`` already stated about itself: a
method must be instantiated in exactly ONE place, because a second place
that forgets a wrapper reports a different number without saying so. This
module is that place; the GUI worker and the CLI are both callers.

No Qt anywhere in this file — that is what makes it shareable.
"""
from __future__ import annotations

from typing import Callable, Optional

from .methods import method_registry
from .methods.gle import interslice_function
from .rapid_drawdown import check_drawdown_settings, wrap_for_drawdown

__all__ = [
    "AnalysisOutcome",
    "build_method",
    "build_search",
    "check_analysis_settings",
    "run_analysis",
    "settings_warnings",
]

# Methods that take an interslice force function and a λ bracket. Keyed
# by METHOD_ID rather than by class so the mapping survives a rename, and
# so the registry stays the single list of what exists.
_LAMBDA_METHODS = ("spencer", "gle_morgenstern_price")
_INTERSLICE_METHODS = ("gle_morgenstern_price",)

# Searches that enumerate rather than draw at random. Seeding them would
# mean handing an argument they can only ignore.
_DETERMINISTIC_SEARCHES = ("grid", "auto_refine")


class AnalysisOutcome:
    """What one call to :func:`run_analysis` produced.

    ``results`` maps method id to :class:`~ogr_slip2d.search.SearchResult`.
    ``factor_report`` is the design-standard report (empty when the
    standard is disabled). ``warnings`` collects anything the run decided
    to carry on through — an unknown method id, mostly. It exists because
    the code this replaced answered an unknown id with a bare
    ``continue``, and the method simply vanished from the results with no
    trace at all.
    """

    __slots__ = ("results", "factor_report", "warnings", "project")

    def __init__(self, results, factor_report, warnings, project) -> None:
        self.results = results
        self.factor_report = factor_report
        self.warnings = warnings
        #: The FACTORED copy actually analysed — never the caller's
        #: project, which must come out of an analysis untouched.
        self.project = project

    def __iter__(self):
        """So ``results, report = run_analysis(...)`` keeps working."""
        return iter((self.results, self.factor_report))


# ======================================================================
def check_analysis_settings(project) -> list[str]:
    """Every reason ``project`` cannot be analysed as configured.

    Empty list when it can. Refusing beats returning a plausible number
    computed from settings that were quietly dropped — that is the whole
    argument of ``check_drawdown_settings``, generalised.
    """
    problems: list[str] = []

    why = check_drawdown_settings(project)
    if why:
        problems.append(why)

    # v0.1.77 — the finite-element seepage field is NOT serialised into
    # the .ogr (``Project.to_dict`` writes ``fem_mesh`` and not
    # ``seepage_result``), while ``pore_pressure`` answers 0.0 when it is
    # missing. So a saved FEM project reopened and computed without
    # re-solving the seepage reports a dry slope. This affects the GUI
    # too, not only the CLI: within one session the field is in memory,
    # and the moment the file is reopened it is gone.
    from ogr_core.materials import PorePressureType
    uses_fem = [m.name for m in project.materials
                if getattr(m, "pore_pressure", None) == PorePressureType.FEM_SEEPAGE]
    if uses_fem and getattr(project, "seepage_result", None) is None:
        problems.append(
            "These materials take their pore pressure from a "
            "finite-element seepage field, and no field is loaded: "
            f"{', '.join(uses_fem)}. The field is not stored in the .ogr "
            "file, so it has to be recomputed after opening the project. "
            "Run the groundwater analysis first — computing now would "
            "report u = 0 everywhere, which looks like a dry slope.")

    return problems


def settings_warnings(project) -> list[str]:
    """Settings this project sets that the chosen analysis will not read.

    Not a refusal: the analysis is valid, it just does less than the
    Project Settings pages suggest. Saying so is the minimum rule 7 asks
    when a control cannot be honoured.
    """
    notes: list[str] = []
    s_search = project.settings.search
    if (s_search.search_method == "slope"
            and s_search.slope_limit_left is not None
            and s_search.slope_limit_right is not None):
        notes.append(
            "Slope Search derives its entry and exit window from the "
            "ground profile and does not read the Slope Limits you set; "
            "they apply to Grid Search. The limits were ignored.")
    return notes


# ======================================================================
def build_method(project, method_id: str, num_slices: Optional[int] = None):
    """The configured LEM method object for ``method_id``, or None.

    THE single instantiation point. Two things are attached here and
    nowhere else:

    - the convergence settings the user configured (``lem_kwargs``);
      v0.1.74 found that every method had accepted ``tolerance``,
      ``max_iterations`` and ``initial_fos`` since it was written and
      every call site had instantiated them with no arguments at all;
    - the rapid-drawdown wrapper, applied unconditionally because it is a
      no-op when the project does not ask for one.

    The method table is derived from ``method_registry()`` instead of
    being written out by hand. The hand-written version is what let
    ``janbu_corrected`` be tickable in Project Settings while producing
    no result at all, and let the GUI and the CLI support two different
    subsets of the seven registered methods.
    """
    cls = method_registry().get(method_id)
    if cls is None:
        return None

    s = project.settings
    kwargs = dict(s.lem_kwargs())
    if method_id in _LAMBDA_METHODS:
        kwargs["min_lambda"] = s.advanced.min_lambda
        kwargs["max_lambda"] = s.advanced.max_lambda
    if method_id in _INTERSLICE_METHODS:
        kwargs["interslice_func"] = interslice_function(
            s.methods.interslice_function)

    method = cls(**kwargs)

    # v0.1.68 — a rapid drawdown replaces what "the factor of safety of
    # this surface" means, so it is applied where methods are made. A
    # second place that forgot would silently report the ordinary factor
    # of safety instead; from v0.1.72 to v0.1.76, ogr_cli was that place.
    if num_slices is None:
        num_slices = s.methods.num_slices
    return wrap_for_drawdown(method, project, num_slices=int(num_slices))


# ======================================================================
def build_search(project, method_id: str, progress_cb: Optional[Callable] = None):
    """The search object for ``method_id``, configured from the project.

    Exposed so the Overall Slope probabilistic analysis and Optimize
    Surfaces can rebuild EXACTLY the same search once per sample rather
    than duplicating this dispatch. Returns None when ``method_id`` is
    not registered.
    """
    method = build_method(project, method_id)
    if method is None:
        return None

    s = project.settings
    s_search = s.search
    num_slices = s.methods.num_slices
    admissibility = s.admissibility_kwargs()
    search_method = s_search.search_method

    def _seed_kw() -> dict:
        """The project's seed, for the searches that draw at random.

        v0.1.74 — the Random Numbers page promised a pseudo-random run
        "will give exactly the same results", and no search had ever been
        told which seed to use.
        """
        if search_method in _DETERMINISTIC_SEARCHES:
            return {}
        return {"seed": s.analysis_seed()}

    common = dict(
        method=method,
        num_slices=num_slices,
        progress_cb=progress_cb,
        **admissibility,
        **_seed_kw(),
    )

    if search_method == "slope":
        from .search import SlopeSearch
        _up_en = getattr(s_search, "initial_angle_at_toe_upper_enabled", False)
        # ``slope_limits`` is deliberately NOT passed. SlopeSearch.run
        # derives the entry/exit window from the ground profile itself
        # and has no code that reads a user-supplied limit, so handing it
        # one would be an argument that changes nothing — see the warning
        # raised in ``check_analysis_settings``.
        return SlopeSearch(
            num_surfaces=s_search.num_surfaces,
            min_area=s_search.min_area or 1.0,
            initial_angle_lower_deg=getattr(
                s_search, "initial_angle_at_toe_lower_deg", -45.0),
            initial_angle_upper_deg=(
                getattr(s_search, "initial_angle_at_toe_upper_deg", None)
                if _up_en else None),
            **common,
        )

    if search_method == "auto_refine":
        from .search import AutoRefineSearch
        return AutoRefineSearch(
            divisions=getattr(s_search, "auto_refine_divisions_along_slope",
                              s_search.auto_refine_divisions),
            circles_per_division=getattr(
                s_search, "auto_refine_circles_per_division", 10),
            iterations=s_search.auto_refine_iterations,
            next_iter_fraction=getattr(
                s_search, "auto_refine_divisions_to_use_pct", 50.0),
            min_area=s_search.min_area or 0.5,
            **common,
        )

    if search_method == "block":
        from .search import BlockSearch
        return BlockSearch(
            num_groups=s_search.block_num_groups,
            left_start_angle_deg=s_search.block_left_start_angle_deg,
            left_end_angle_deg=s_search.block_left_end_angle_deg,
            right_start_angle_deg=s_search.block_right_start_angle_deg,
            right_end_angle_deg=s_search.block_right_end_angle_deg,
            num_surfaces=s_search.block_num_surfaces,
            min_area=s_search.min_area or 2.0,
            convex_only=s_search.block_convex_only,
            **common,
        )

    if search_method == "path":
        from .search import PathSearch
        _seg = s_search.path_segment_length
        return PathSearch(
            # 0 means "auto", which the search reads as 0.3 H.
            segment_length=(_seg if _seg and _seg > 0 else None),
            initial_angle_lower_deg=s_search.path_min_angle_deg,
            initial_angle_upper_deg=(
                s_search.path_max_angle_deg
                if getattr(s_search, "path_upper_angle_enabled", False)
                else None),
            num_paths=s_search.path_num_paths,
            optimize=getattr(s_search, "path_optimize", True),
            convex_only=getattr(s_search, "path_convex_only", False),
            **common,
        )

    if search_method == "simulated_annealing":
        from .search import SimulatedAnnealingSearch
        return SimulatedAnnealingSearch(
            initial_vertices=s_search.sa_initial_vertices,
            generation_steps=s_search.sa_generation_steps,
            tolerance=s_search.sa_tolerance,
            temperature_factor=s_search.sa_temperature_factor,
            convex_only=s_search.sa_convex_only,
            min_area=s_search.min_area or 1.0,
            **common,
        )

    # Default = Grid Search.
    from .search import GridSearch
    return GridSearch(
        slope_limits=_slope_limits(s_search),
        focus_objects=[f for f in getattr(project, "focus_objects", [])
                       if f.enabled and f.valid],
        grid_x=_grid_range(s_search.grid_x_min, s_search.grid_x_max),
        grid_y=_grid_range(s_search.grid_y_min, s_search.grid_y_max),
        grid_nx=s_search.grid_nx,
        grid_ny=s_search.grid_ny,
        radius_increment=s_search.radius_increment or 1.5,
        min_radius=3.0,
        min_area=s_search.min_area or 1.0,
        **common,
    )


def _grid_range(lo, hi):
    """A user-defined grid extent, or None for automatic."""
    if lo is None or hi is None:
        return None
    return (lo, hi)


def _slope_limits(s_search):
    """Explicit slope limits, or None.

    v0.1.55 — None means automatic: derived from the ground surface,
    which is what keeps a model portable between geometries.
    """
    if (s_search.slope_limit_left is None
            or s_search.slope_limit_right is None):
        return None
    return (s_search.slope_limit_left, s_search.slope_limit_right)


# ======================================================================
def run_analysis(project, method_ids=None,
                 progress_cb: Optional[Callable] = None) -> AnalysisOutcome:
    """Run one configured search per method and return every result.

    ``progress_cb(done, total)`` is called across the whole run, not per
    method, so a caller driving a progress bar needs no arithmetic.

    v0.1.57 — the design-standard partial factors are applied HERE, once,
    by substituting a factored **copy** of the project. Every analysis
    path downstream then reads the factored values without knowing the
    feature exists, and the caller's project is never modified.
    """
    from ogr_core.project import apply_design_factors
    project, factor_report = apply_design_factors(project)

    if method_ids is None:
        method_ids = list(project.settings.methods.enabled_methods)
    method_ids = list(method_ids) or ["bishop_simplified"]

    known = method_registry()
    warnings: list[str] = settings_warnings(project)
    results: dict = {}
    n_methods = len(method_ids)

    for i, mid in enumerate(method_ids):
        if mid not in known:
            # v0.1.77 — this used to be a bare ``continue``, and that is
            # how "Janbu Corrected" could be ticked in Project Settings
            # and produce nothing whatsoever. An unrunnable method now
            # leaves a trace.
            warnings.append(
                f"'{mid}' is not a registered analysis method, so it was "
                f"not computed. Available: {', '.join(sorted(known))}.")
            continue

        def _progress(done, total, _i=i, _n=n_methods):
            if progress_cb is not None:
                progress_cb(_i * total + done, _n * total)

        search = build_search(project, mid, progress_cb=_progress)
        if search is None:  # pragma: no cover - guarded by the check above
            continue
        results[mid] = search.run(project)

    return AnalysisOutcome(results, factor_report, warnings, project)
