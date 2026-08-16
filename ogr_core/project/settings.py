# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Project-level analysis settings.

Mirrors the hierarchical configuration tree: General → Methods →
Groundwater → Transient → Statistics → Random Numbers → Design Standard
→ Advanced → Project Summary.

Every setting is serializable. The ProjectSettings is saved alongside
the geometry in the .ogr JSON file.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional

from .units import Units


# ----------------------------------------------------------------------
class LEMMethod(Enum):
    """Limit Equilibrium Methods available."""
    BISHOP_SIMPLIFIED = "bishop_simplified"
    JANBU_SIMPLIFIED = "janbu_simplified"
    JANBU_CORRECTED = "janbu_corrected"
    ORDINARY_FELLENIUS = "ordinary_fellenius"
    SPENCER = "spencer"
    GLE_MORGENSTERN_PRICE = "gle_morgenstern_price"
    CORPS_OF_ENGINEERS_1 = "corps_engineers_1"
    CORPS_OF_ENGINEERS_2 = "corps_engineers_2"
    LOWE_KARAFIATH = "lowe_karafiath"


class GroundwaterMethod(Enum):
    NONE = "none"
    WATER_TABLE = "water_table"
    PIEZO_LINE = "piezo_line"
    RU_COEFFICIENT = "ru"
    # v0.1.23 — Water Pressure Grid methods (Phase 0 of the groundwater
    # plan): pore pressure interpolated from a grid of data points.
    GRID_TOTAL_HEAD = "grid_total_head"
    GRID_PRESSURE_HEAD = "grid_pressure_head"
    GRID_PORE_PRESSURE = "grid_pore_pressure"
    FEA_STEADY = "fea_steady"
    FEA_TRANSIENT = "fea_transient"


class SurfaceType(Enum):
    CIRCULAR = "circular"
    NON_CIRCULAR = "non_circular"


class SearchMethod(Enum):
    # Circular-only
    GRID_SEARCH = "grid"
    SLOPE_SEARCH = "slope"
    # Both surface types
    AUTO_REFINE = "auto_refine"
    # Non-circular-only (v0.1.10)
    BLOCK_SEARCH = "block"
    PATH_SEARCH = "path"
    SIMULATED_ANNEALING = "simulated_annealing"


# Methods compatible with each surface type (Slide convention)
CIRCULAR_METHODS = {
    SearchMethod.GRID_SEARCH,
    SearchMethod.SLOPE_SEARCH,
    SearchMethod.AUTO_REFINE,
}
NON_CIRCULAR_METHODS = {
    SearchMethod.BLOCK_SEARCH,
    SearchMethod.PATH_SEARCH,
    SearchMethod.SIMULATED_ANNEALING,
    SearchMethod.AUTO_REFINE,
}


# ----------------------------------------------------------------------
@dataclass
class MethodsSettings:
    """Algorithm & convergence settings."""
    enabled_methods: list[str] = field(
        default_factory=lambda: [
            LEMMethod.BISHOP_SIMPLIFIED.value,
            LEMMethod.JANBU_SIMPLIFIED.value,
        ]
    )
    num_slices: int = 25
    tolerance: float = 0.005
    max_iterations: int = 50
    # v0.1.74 — the interslice force function GLE / Morgenstern-Price
    # uses. The method has accepted one since it was written; nothing had
    # ever passed a different one, so the half sine was not a default but
    # the only possibility. Ids come from
    # ``ogr_slip2d.methods.gle.INTERSLICE_FUNCTIONS``.
    interslice_function: str = "half_sine"


@dataclass
class GroundwaterSettings:
    method: str = GroundwaterMethod.WATER_TABLE.value
    pore_fluid_unit_weight: float = 9.81  # kN/m³

    # v0.1.7 — Advanced options (Slide-style):
    # excess_pore_pressure: enables B-bar method on undrained materials
    # rapid_drawdown: enables Drawdown Line + drawdown-method analysis
    # rapid_drawdown_method: which Slide-recognised method to apply
    excess_pore_pressure: bool = False
    rapid_drawdown: bool = False
    # v0.1.30 — Transient groundwater. The reference groups these three
    # under an "Advanced" section and allows only ONE at a time; that
    # exclusivity is enforced by ``set_advanced_option``.
    transient: bool = False
    # Stages: [{"time": float, "calculate_sf": bool, "label": str}, ...]
    transient_stages: list = field(default_factory=list)
    # Transient FEA options (same meaning as the steady-state ones);
    # time_steps = 0 means the compute engine chooses automatically.
    transient_tolerance: float = 1.0e-5
    transient_max_iterations: int = 30
    transient_time_steps: int = 0
    # Boundary conditions defining the INITIAL state (before stage 1).
    # None → the currently defined conditions are used, which means the
    # model starts already in equilibrium with them.
    transient_initial_bcs: Optional[dict] = None
    rapid_drawdown_method: str = "b_bar"  # b_bar | duncan_wright | corps_2 | lowe_karafiath
    # Hu coefficient default (per material can override). 1.0 = full
    # hydrostatic pressure under a horizontal water table.
    default_hu: float = 1.0
    auto_hu: bool = False  # auto-compute Hu from water-surface slope

    # ------------------------------------------------------------------
    def set_advanced_option(self, option: Optional[str]) -> None:
        """Select at most ONE advanced groundwater option.

        The reference states explicitly that these are mutually
        exclusive: transient, excess pore pressure and rapid drawdown
        cannot run simultaneously. ``option`` is one of ``"transient"``,
        ``"excess_pore_pressure"``, ``"rapid_drawdown"`` or None.
        """
        self.transient = (option == "transient")
        self.excess_pore_pressure = (option == "excess_pore_pressure")
        self.rapid_drawdown = (option == "rapid_drawdown")

    def advanced_option(self) -> Optional[str]:
        if self.transient:
            return "transient"
        if self.excess_pore_pressure:
            return "excess_pore_pressure"
        if self.rapid_drawdown:
            return "rapid_drawdown"
        return None

    def stage_times(self) -> list:
        return [float(st.get("time", 0.0)) for st in self.transient_stages]

    def sf_stages(self) -> list:
        """Indices of the stages flagged to also compute a factor of
        safety (the reference's per-stage 'Calculate SF' checkbox)."""
        return [i for i, st in enumerate(self.transient_stages)
                if st.get("calculate_sf")]


@dataclass
class SearchSettings:
    """Search options.

    ``slope_limit_left`` / ``slope_limit_right`` are ``None`` by default,
    meaning **automatic**: the limits are derived from the ground
    surface. Storing an explicit pair only when the user sets one keeps a
    model portable — hard-coded limits from one geometry would be wrong
    for another.
    """

    """Search settings — aligned with Slide's Surface Options dialog
    (Surface_Options.pdf). Each search method has its own parameters;
    the GUI shows only those relevant to the current method."""

    slope_limit_left: Optional[float] = None
    slope_limit_right: Optional[float] = None
    surface_type: str = SurfaceType.CIRCULAR.value
    search_method: str = SearchMethod.GRID_SEARCH.value

    # ---------- Grid Search (circular) ----------
    radius_increment: int = 10  # number of radius increments per centre (PDF default)
    composite_surfaces: bool = False
    create_tension_crack_reverse_curvature: bool = True

    # ---------- Slope Search (circular) ----------
    num_surfaces: int = 5000
    initial_angle_at_toe_upper_enabled: bool = False
    initial_angle_at_toe_upper_deg: float = -45.0
    initial_angle_at_toe_lower_enabled: bool = False
    initial_angle_at_toe_lower_deg: float = -45.0
    # Legacy compatibility
    initial_angle_lower_deg: float = 0.0
    initial_angle_upper_deg: float = 90.0

    # ---------- Auto Refine Search (circular & non-circular) ----------
    auto_refine_divisions_along_slope: int = 10
    auto_refine_circles_per_division: int = 10
    auto_refine_num_iterations: int = 10
    auto_refine_divisions_to_use_pct: float = 50.0  # %
    auto_refine_num_vertices_along_surface: int = 12  # only non-circular
    # Legacy
    auto_refine_divisions: int = 10
    auto_refine_iterations: int = 5
    auto_refine_factor: float = 0.5

    # ---------- Simulated Annealing (non-circular) ----------
    sa_initial_vertices: int = 8
    sa_generation_steps: int = 1000
    # Number of consecutive FoS values that must lie within tolerance
    # before the search stops (Slide spec). PDF default 5.
    sa_num_fos_compared_before_stopping: int = 5
    sa_tolerance: float = 1e-4
    # Temperature reduction coefficient — c in T_k = T_0 · exp(-c · k^(1/n))
    # Slide default 8.0 (Su 2009 paper Section 2.1.5)
    sa_temperature_coefficient: float = 8.0
    # Legacy field (was the cooling rate)
    sa_temperature_factor: float = 0.97
    sa_convex_only: bool = False

    # ---------- Path Search (non-circular) ----------
    path_num_surfaces: int = 5000
    path_initial_angle_at_toe_upper_enabled: bool = False
    path_initial_angle_at_toe_upper_deg: float = 45.0
    path_initial_angle_at_toe_lower_enabled: bool = False
    path_initial_angle_at_toe_lower_deg: float = 45.0
    path_segment_length_manual: bool = False
    path_segment_length_value: float = 7.142857
    path_convex_only: bool = False
    # v0.1.17 — XSTABL Path Search controls
    path_optimize: bool = True
    path_upper_angle_enabled: bool = False
    # Legacy fields
    path_segment_length: float = 5.0
    path_min_angle_deg: float = -45.0
    path_max_angle_deg: float = 45.0
    path_num_paths: int = 500

    # ---------- Block Search (non-circular) ----------
    block_num_surfaces: int = 5000
    block_multiple_groups: bool = False
    block_left_start_angle_deg: float = 135.0
    block_left_end_angle_deg: float = 135.0
    block_right_start_angle_deg: float = 45.0
    block_right_end_angle_deg: float = 45.0
    block_convex_only: bool = False
    # Legacy
    block_num_groups: int = 3
    block_left_proj_angle_deg: float = 135.0
    block_right_proj_angle_deg: float = 45.0

    # ---------- Optimize Surfaces (post-processing, non-circular) ----------
    optimize_enabled: bool = False
    optimize_target: str = "global_minimum"  # global_minimum | all | fos_less_than
    optimize_fos_threshold: float = 1.5
    optimize_tolerance: float = 1e-9
    optimize_max_iterations: int = 4000
    optimize_step_reduction_factor: float = 0.5
    optimize_max_concave_angle_enabled: bool = True
    optimize_max_concave_angle_deg: float = 5.0
    optimize_explore_all_vertices: bool = False
    optimize_snap_shallow_to_slope: bool = True
    optimize_snap_specify_distance: bool = False
    optimize_snap_distance: float = 0.01
    optimize_use_depth_elevation_concave_checks: bool = True

    # ---------- User-defined Grid (Grid Search) ----------
    grid_x_min: Optional[float] = None
    grid_x_max: Optional[float] = None
    grid_y_min: Optional[float] = None
    grid_y_max: Optional[float] = None
    grid_nx: int = 12
    grid_ny: int = 12

    # ---------- Surface Filters ----------
    # PDF shows only Min Elevation + Min Depth.
    # Min Area kept as user-requested extension to filter degenerate surfaces.
    min_elevation: Optional[float] = None
    min_depth: Optional[float] = None
    min_area: Optional[float] = None

    def methods_for_surface_type(self) -> list[SearchMethod]:
        """Returns the list of search methods compatible with the
        current surface_type."""
        if self.surface_type == SurfaceType.CIRCULAR.value:
            return list(CIRCULAR_METHODS)
        return list(NON_CIRCULAR_METHODS)

    def uses_grid(self) -> bool:
        """True if the current search method uses a centre grid.
        Used by the GUI to grey-out Auto Grid / Add Grid actions when
        a non-grid method is selected. Only Grid Search uses a grid in
        Slide."""
        return self.search_method == SearchMethod.GRID_SEARCH.value


@dataclass
class StatisticsSettings:
    sensitivity_analysis: bool = False
    probabilistic_analysis: bool = False
    sampling_method: str = "monte_carlo"   # monte_carlo | latin_hypercube
    num_samples: int = 1000
    # v0.1.38 — probabilistic analysis type:
    #   global_minimum — the deterministic critical surface is reused for
    #                    every sample (fast, the common choice)
    #   overall_slope  — the ENTIRE search is repeated per sample
    #                    (substantially slower, does not assume a fixed
    #                    location for the global minimum)
    analysis_type: str = "global_minimum"
    # Sensitivity: number of equal intervals across each variable range
    sensitivity_intervals: int = 50
    # Random seed for reproducible runs (None = non-deterministic).
    #
    # v0.1.74 — this is NO LONGER the place the seed is chosen. There
    # were two seeds in the model: this one, which the analysis used and
    # which had no widget anywhere, and ``RandomNumberSettings.seed``,
    # which had a whole page of the settings dialog and which nothing
    # read. ``ProjectSettings.analysis_seed()`` is now the single answer,
    # and the Random Numbers page is what feeds it. Kept here so files
    # that set it keep working, and because an explicit value still wins.
    seed: Optional[int] = None


@dataclass
class RandomNumberSettings:
    """Random number generation for the probabilistic analysis.

    A **pseudo-random** stream is reproducible: the same seed gives the
    same answer, which is what makes a probabilistic result defensible in
    a report and comparable between runs. A **random** stream takes its
    seed from the clock, so successive runs explore differently — useful
    to check that a conclusion is not an artefact of one seed.
    """

    method: str = "pseudo_random"      # pseudo_random | random
    seed: int = 10116
    # Latin Hypercube can be told to keep its stratification identical
    # across variables, which the reference exposes separately.
    lhs_correlate: bool = False

    def effective_seed(self):
        """The seed to hand the sampler, or None for a clock-seeded run."""
        return int(self.seed) if self.method == "pseudo_random" else None


@dataclass
class DesignStandardSettings:
    """Partial factors applied to the analysis.

    Off by default: applying partial factors silently would change every
    factor of safety the user has ever compared against, so it must be an
    explicit choice.
    """

    enabled: bool = False
    standard: str = "none"     # none | eurocode7_da1c1 | eurocode7_da1c2 |
    #                            eurocode7_da2 | eurocode7_da3 | custom
    # Partial factors on actions and on material properties
    factor_permanent: float = 1.0
    factor_variable: float = 1.0
    factor_cohesion: float = 1.0
    factor_friction: float = 1.0
    factor_unit_weight: float = 1.0
    factor_resistance: float = 1.0

    # Named presets. Values follow the Eurocode 7 design approaches; the
    # user can still pick "custom" and enter their own.
    PRESETS = {
        "none": (1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        "eurocode7_da1c1": (1.35, 1.5, 1.0, 1.0, 1.0, 1.0),
        "eurocode7_da1c2": (1.0, 1.3, 1.25, 1.25, 1.0, 1.0),
        "eurocode7_da2": (1.35, 1.5, 1.0, 1.0, 1.0, 1.1),
        "eurocode7_da3": (1.35, 1.5, 1.25, 1.25, 1.0, 1.0),
    }

    def apply_preset(self, name: str) -> bool:
        """Load a named set of partial factors. Returns False if unknown
        (``custom`` deliberately leaves the values alone)."""
        vals = self.PRESETS.get(name)
        self.standard = name
        if vals is None:
            return False
        (self.factor_permanent, self.factor_variable, self.factor_cohesion,
         self.factor_friction, self.factor_unit_weight,
         self.factor_resistance) = vals
        return True


@dataclass
class BackAnalysisSettings:
    """Back analysis of the required support force.

    Deliberately independent of the main analysis: the reference states
    that the computed force is NOT included in, and does not affect, the
    stability results in any way.
    """

    enabled: bool = False              # "compute reinforcement load"
    target_fos: float = 1.3
    elevation: float = 0.0             # y of the horizontal force
    method_id: str = "bishop_simplified"


@dataclass
class AdvancedSettings:
    """Convergence and admissibility options for the limit-equilibrium run.

    Every field here was stored, edited from the interface, and read by
    nobody until v0.1.74. Wiring them turned up two defaults that were
    wrong precisely BECAUSE they had never been applied, and both are
    corrected below rather than carried forward:

    * ``check_tensile_stresses`` defaulted to True while the reference
      has the Tensile Stress Check **off** — tensile stresses are allowed
      unless the user asks. Nobody noticed because switching it changed
      nothing. Turning it on for every stored project as a side effect of
      wiring it would have been a silent change of results, so the
      default is now False and ``from_dict`` migrates the stored True.

    * ``min_lambda`` / ``max_lambda`` were ±1.25, while the λ grid that
      Spencer and GLE actually search is ±1.5. That is not a rounding
      difference: on the reference-validated circle, GLE converges at
      **λ = 1.4919**, outside ±1.25. Wiring the stored range would have
      clipped the search below what a validated case needs.

    ``tensile_percent`` is the companion the page never had, although the
    engine has accepted it since v0.1.32.
    """

    # Off, as in the reference: tensile stresses are permitted unless the
    # user asks for the check.
    check_tensile_stresses: bool = False
    # Percentage of slices, counted FROM THE TOE, over which the tensile
    # check applies. The reference default is 95 %.
    tensile_percent: float = 95.0
    # The m-alpha check (Whitman & Bailey 1967).
    #
    # v0.1.74 turned it OFF by default and recorded the reason: on the
    # Ej_1 case the reference-validated critical circle came out with a
    # minimum m-alpha of -0.0100, so the check rejected the very surface
    # the project validates against a published value.
    #
    # v0.1.82 found that measurement to be the bug, not the criterion.
    # ``m_alpha`` is not symmetric in alpha, so it only means anything
    # evaluated with the same sense of sliding the solver used; with the
    # sign restored that circle's minimum m-alpha is **+0.928**.
    #
    # v0.1.84 turns it ON, because the justification for keeping it off
    # was the other half of the same mistake. The reference's own reports
    # for both worked examples screen surfaces with it by default and
    # count them under error code -112: 97 surfaces in Ej_1 bishop, 225 in
    # Ej_2 bishop, and likewise for janbu, spencer and GLE. It was never a
    # divergence the reference asked for. Measured after the flip: the
    # Ej_1 critical circle is untouched (0.884517, centre (88, 70.5)) and
    # 64 surfaces are screened out, against the reference's 97.
    check_m_alpha: bool = True
    # First trial value of the factor of safety. Named ``min_initial_fs``
    # until v0.1.74, which was a misnomer: it is a starting point, not a
    # floor. ``from_dict`` still reads the old key.
    initial_fos: float = 1.0
    # Range searched for the interslice force scaling factor. See the
    # note above for why these are ±1.5 and not ±1.25.
    min_lambda: float = -1.5
    max_lambda: float = 1.5
    iterate_steffensen: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AdvancedSettings":
        """Read a stored block, migrating the two mistaken defaults.

        A file written before v0.1.74 carries values that never reached a
        calculation, so they express no intent to preserve — which is
        exactly what makes rewriting them safe, and what would make
        honouring them unsafe.
        """
        data = dict(data or {})
        # ``min_initial_fs`` → ``initial_fos``
        if "min_initial_fs" in data and "initial_fos" not in data:
            data["initial_fos"] = data.pop("min_initial_fs")
        data.pop("min_initial_fs", None)
        # The two migrations. Both are conditional on the value being the
        # old default: a user who deliberately typed something else keeps
        # it, because from v0.1.74 on it means something.
        if data.get("check_tensile_stresses") is True:
            data["check_tensile_stresses"] = False
        for key, old, new in (("min_lambda", -1.25, -1.5),
                              ("max_lambda", 1.25, 1.5)):
            if key in data and abs(float(data[key]) - old) < 1e-12:
                data[key] = new
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ProjectSummary:
    title: str = "Untitled Project"
    analysis: str = ""
    author: str = "Samuel Sáez López"
    company: str = "UPCT"
    date_created: str = ""
    comments: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------
@dataclass
class ProjectSettings:
    """Root configuration object."""
    units: Units = field(default_factory=Units)
    methods: MethodsSettings = field(default_factory=MethodsSettings)
    groundwater: GroundwaterSettings = field(default_factory=GroundwaterSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    statistics: StatisticsSettings = field(default_factory=StatisticsSettings)
    back_analysis: BackAnalysisSettings = field(
        default_factory=BackAnalysisSettings)
    random_numbers: RandomNumberSettings = field(
        default_factory=RandomNumberSettings)
    design_standard: DesignStandardSettings = field(
        default_factory=DesignStandardSettings)
    advanced: AdvancedSettings = field(default_factory=AdvancedSettings)
    summary: ProjectSummary = field(default_factory=ProjectSummary)

    max_materials: int = 20
    max_supports: int = 20

    # ------------------------------------------------------------------
    def analysis_seed(self):
        """The seed every random-driven analysis takes, or None.

        v0.1.74 — the single answer to a question the model used to give
        two of. ``RandomNumberSettings`` is the page the user sees, so it
        is the page that decides; ``statistics.seed`` stays as an
        explicit override for files that set it, because honouring a
        value someone deliberately wrote is cheaper than surprising them.

        Applies to the probabilistic and sensitivity runs and to the
        random surface searches (Slope, Block and Path), which is exactly
        the scope the reference gives its Random Numbers page.
        """
        if self.statistics.seed is not None:
            return int(self.statistics.seed)
        return self.random_numbers.effective_seed()

    def lem_kwargs(self) -> dict:
        """Convergence arguments shared by every limit-equilibrium method.

        One place, because the alternative is what v0.1.74 found: the
        methods accepted ``tolerance``, ``max_iterations`` and
        ``initial_fos`` from the start, and every call site instantiated
        them with no arguments at all, so three settings on two pages
        were decoration.
        """
        return {
            "tolerance": float(self.methods.tolerance),
            "max_iterations": int(self.methods.max_iterations),
            "initial_fos": float(self.advanced.initial_fos),
            "iterate_steffensen": bool(self.advanced.iterate_steffensen),
        }

    def admissibility_kwargs(self) -> dict:
        """Post-analysis check arguments shared by every search object."""
        return {
            "reject_tensile": bool(self.advanced.check_tensile_stresses),
            "tensile_percent": float(self.advanced.tensile_percent),
            "check_m_alpha": bool(self.advanced.check_m_alpha),
        }

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "units": self.units.to_dict(),
            "methods": asdict(self.methods),
            "groundwater": asdict(self.groundwater),
            "search": asdict(self.search),
            "statistics": asdict(self.statistics),
            "back_analysis": asdict(self.back_analysis),
            "random_numbers": asdict(self.random_numbers),
            "design_standard": {
                k: v for k, v in asdict(self.design_standard).items()
                if k != "PRESETS"},
            "advanced": asdict(self.advanced),
            "summary": asdict(self.summary),
            "max_materials": self.max_materials,
            "max_supports": self.max_supports,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectSettings":
        return cls(
            units=Units.from_dict(data.get("units", {})),
            methods=MethodsSettings(**data.get("methods", {})),
            groundwater=GroundwaterSettings(**data.get("groundwater", {})),
            search=SearchSettings(**data.get("search", {})),
            statistics=StatisticsSettings(**data.get("statistics", {})),
            back_analysis=BackAnalysisSettings(
                **data.get("back_analysis", {})),
            random_numbers=RandomNumberSettings(
                **data.get("random_numbers", {})),
            design_standard=DesignStandardSettings(
                **{k: v for k, v in
                   (data.get("design_standard") or {}).items()
                   if k != "PRESETS"}),
            advanced=AdvancedSettings.from_dict(data.get("advanced", {})),
            summary=ProjectSummary(**data.get("summary", {})),
            max_materials=data.get("max_materials", 20),
            max_supports=data.get("max_supports", 20),
        )
