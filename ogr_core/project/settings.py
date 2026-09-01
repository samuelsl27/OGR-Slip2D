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
from dataclasses import fields as dataclass_fields
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


class WeakLayerHandling(Enum):
    """Policy for clipping a trial surface against several weak layers.

    v0.1.121. See ``SearchSettings.weak_layer_handling`` for what each one
    costs and when it is the right answer.
    """

    HIGHEST = "highest"
    AUTO_CASES = "auto_cases"


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
    PARTICLE_SWARM = "particle_swarm"        # v0.1.126


# Methods compatible with each surface type (Slide convention)
CIRCULAR_METHODS = {
    SearchMethod.GRID_SEARCH,
    SearchMethod.SLOPE_SEARCH,
    SearchMethod.AUTO_REFINE,
    SearchMethod.PARTICLE_SWARM,
}
NON_CIRCULAR_METHODS = {
    SearchMethod.BLOCK_SEARCH,
    SearchMethod.PATH_SEARCH,
    SearchMethod.SIMULATED_ANNEALING,
    SearchMethod.AUTO_REFINE,
    # v0.1.126 — the swarm is in BOTH lists, as Auto Refine already is,
    # and for a reason the reference states about its own: the particles
    # are circles, and the non-circular surface is what the optimisation
    # makes of the winners afterwards. Offering it only under
    # Non-Circular would hide a perfectly good circular search; offering
    # it only under Circular would take the optimisation away from it.
    SearchMethod.PARTICLE_SWARM,
}


def is_auto_refine_non_circular(search: "SearchSettings") -> bool:
    """Whether this project runs the NON-CIRCULAR Auto Refine.

    v0.1.128, defect D32. Auto Refine is in both families, so the answer
    is a property of the PAIR and never of the method alone — and every
    place that asked the method alone got it wrong: the search that was
    built, the Optimize Surfaces default, and the note that said the
    option had been ignored. Written once, here, so the next place to ask
    cannot answer differently.
    """
    return (search.search_method == SearchMethod.AUTO_REFINE.value
            and search.surface_type == SurfaceType.NON_CIRCULAR.value)


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
    # v0.1.98 — for the three methods that PRESCRIBE the inter-slice
    # inclination (Lowe-Karafiath, Corps of Engineers #1 and #2), whether
    # the resultant whose inclination is prescribed is the EFFECTIVE
    # inter-slice force — the water pressure on the vertical faces taken
    # out and applied as its own horizontal load — or the TOTAL one.
    #
    # USACE (2003), EM 1110-2-1902 §C-4a treats both as legitimate and
    # states that the computed factor of safety differs between them.
    # Values: "effective" | "total".
    #
    # v0.1.144 — the default is TOTAL, and it was a decision and not a
    # measurement: neither value satisfies both external anchors, and that
    # is a property of the assumption rather than a defect. With water
    # present, TOTAL is what reproduces every published factor of safety
    # for this family — EM §G-5a states its own worked example is in total
    # forces, and it is the one this engine reproduces slice by slice;
    # Pockoski and Duncan (2000) and Zhu (2003) agree, as does UTEXAS4.
    # What it gives up is a slope with water standing over it: raising a
    # pond adds a purely horizontal force to every vertical face, so an
    # assumption tying X to E·tanθ cannot leave the factor of safety
    # unchanged, and on Duncan and Wright (2005) fig. 6.27 the march loses
    # its root altogether. EFFECTIVE is the only value that survives that
    # case and it stays one click away, because the standard that defines
    # these methods considers both legitimate.
    #
    # Changing this moves NEW projects only. Every file saved since
    # v0.1.98 carries the field (``to_dict`` writes the whole dataclass),
    # so a stored project keeps whatever it was analysed with.
    # See docs/PENDIENTES.md §7 and tests/test_interslice_split_v1117.py.
    interslice_forces: str = "total"


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
    # v0.1.125 — the largest matric suction allowed to reach the strength
    # calculation, in kPa. ``None`` means no limit, which is both the
    # reference default and what this program did until this version.
    #
    # It bites wherever a material declares Unsaturated Shear Strength
    # parameters, and EITHER of the two is enough: phi_b makes it bound
    # the extra cohesion, and an air entry value makes it bound the
    # negative pore pressure itself, because below the air entry value
    # the real suction is kept and credited to the saturated friction
    # angle. Only a material with BOTH at zero is unaffected — measured:
    # with phi_b = 0 and AEV = 50, a suction of 90 kPa reaches the
    # strength as -50 without a cap and as -20 with a cap of 20.
    #
    # Where it bites it matters a great deal — a slope drained for a long
    # time develops suction all the way to its crest. The sign is
    # ignored: the absolute value is used, as the reference states.
    negative_pore_pressure_cutoff: Optional[float] = None
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


#: The settings that used to be stored TWICE, under two names: the one the
#: interface showed and serialised, and the one the engine actually read.
#:
#: The interface wrote both from the same widget, so from the interface they
#: agreed; a model built by a script, or saved by an older version, kept the
#: name that was NOT consumed and the analysis silently ran on the other
#: one's default. Two of them differed by a factor of ten and of two:
#: "Number of Surfaces" declared 5000 and the Path Search generated 500;
#: "Number of Iterations" declared 10 and the Auto Refine ran 5.
#:
#: Maps each retired name to its old default and to the field that replaced
#: it (``None`` where nothing read it at all, so nothing replaces it).
_SHADOW_FIELDS: dict = {
    # Same quantity under two names — the value migrates straight across.
    "path_num_paths": (500, "path_num_surfaces"),
    "auto_refine_iterations": (5, "auto_refine_num_iterations"),
    "auto_refine_divisions": (10, "auto_refine_divisions_along_slope"),
    # Different shape: 0 meant "automatic", anything else a fixed length.
    "path_segment_length": (5.0, "path_segment_length_manual"),
    # Different frame: these were angles in the search's toe-to-crest frame,
    # the survivors are absolute and counter-clockwise from +x.
    "path_min_angle_deg": (-45.0, "path_initial_angle_at_toe_lower_deg"),
    "path_max_angle_deg": (45.0, "path_initial_angle_at_toe_upper_deg"),
    "path_upper_angle_enabled": (False,
                                 "path_initial_angle_at_toe_upper_enabled"),
    # Different quantity: a geometric cooling rate against the c of
    # T_k = T_0 exp(-c k^(1/n)). The rate was never read by anything.
    "sa_temperature_factor": (0.97, "sa_temperature_coefficient"),
    # Same quantity, opposite visibility: the engine read ``path_optimize``
    # and the interface showed ``optimize_enabled``. The value is NOT
    # migrated — a field that defaulted to True in every model ever saved
    # expresses no intent, and carrying it across would tick a box the user
    # never ticked. See v0.1.104.
    "path_optimize": (True, "optimize_enabled"),
    # Read by nobody, ever. The interface wrote them and there they died.
    "initial_angle_lower_deg": (0.0, None),
    "initial_angle_upper_deg": (90.0, None),
    "auto_refine_factor": (0.5, None),
    "block_left_proj_angle_deg": (135.0, None),
    "block_right_proj_angle_deg": (45.0, None),
}


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
    # v0.1.92 — the moment axis for NON-CIRCULAR surfaces, None by default
    # meaning automatic: each surface gets its own, built from its entry-exit
    # chord. A circle needs none, having a centre already.
    #
    # It exists because a moment method has to take moments about SOMETHING,
    # and a polyline offers no natural point. The reference carries the same
    # control and describes it the same way: "a single axis point, which will
    # be used for moment equilibrium calculations, for ALL surfaces generated
    # by a Block Search or a Path Search".
    #
    # Both or neither: one coordinate alone does not define a point, and
    # silently pairing it with an automatic other half would be a setting
    # that half-applies.
    axis_x: Optional[float] = None
    axis_y: Optional[float] = None
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

    # ---------- Auto Refine Search (circular & non-circular) ----------
    auto_refine_divisions_along_slope: int = 10
    auto_refine_circles_per_division: int = 10
    # 10 and not 5: it is what the reference's own panel shows next to
    # "Number of Iterations", and what this field has always displayed.
    # A second field held 5, and it was the one the engine read — see the
    # note on ``_SHADOW_FIELDS`` below.
    auto_refine_num_iterations: int = 10
    auto_refine_divisions_to_use_pct: float = 50.0  # %
    auto_refine_num_vertices_along_surface: int = 12  # only non-circular

    # ---------- Simulated Annealing (non-circular) ----------
    sa_initial_vertices: int = 8
    sa_generation_steps: int = 1000
    # Number of consecutive FoS values that must lie within tolerance
    # before the search stops (Slide spec). PDF default 5.
    sa_num_fos_compared_before_stopping: int = 5
    sa_tolerance: float = 1e-4
    # Temperature reduction coefficient — c in T_k = T_0 · exp(-c · k^(1/n)),
    # Su (2009) "Global Optimization of General Failure Surfaces in Slope
    # Analysis by Hybrid Simulated Annealing", section 2.1.6, eqs. (10)-(11).
    # c = 8.0 is the value that work adopted; 1 to 10 are all adequate.
    #
    # (The note here used to cite section 2.1.5, which is the acceptance
    # function, not the schedule.)
    sa_temperature_coefficient: float = 8.0
    sa_convex_only: bool = False

    # ---------- Particle Swarm (v0.1.126) ----------
    # Defaults are the reference's own where it publishes them: 50
    # particles, and a niching radius of 10 % of the span of the search
    # space, which its help calls the recommended value. The iteration
    # count it does not publish ("a finite number of iterations"); 50 is
    # this program's own, chosen so a default run costs about what a
    # default Slope Search costs.
    pso_num_particles: int = 50
    pso_num_iterations: int = 50
    #: One minimum or several. The whole point of the search, and off by
    #: default because it changes what the result MEANS: with it on the
    #: answer is a list of mechanisms, not a number.
    pso_multiple_minima: bool = False
    pso_niche_radius_pct: float = 10.0
    # *Use enhanced PSO algorithm* is NOT here: the reference places it in
    # the Advanced project settings, next to the other search-wide
    # switches, and ``AdvancedSettings.pso_enhanced`` is where it lives.

    # ---------- Path Search (non-circular) ----------
    # "Number of Surfaces" counts VALID surfaces: the generator discards the
    # invalid ones and they do not count towards the total. That is what the
    # search's own loop does, so the number means the same on both sides.
    path_num_surfaces: int = 5000
    # Initial Angle at Toe. The angles are ABSOLUTE, measured
    # counter-clockwise from the positive x axis — the convention the user
    # sees, and therefore the one a stored model has to keep; the search
    # works in a toe-to-crest frame and the conversion happens in one place,
    # ``analysis_runner._path_toe_angles``. Both are ``None``-like when
    # disabled: the upper limit then defaults to (β − 5)° at the initiation
    # point and the lower one to 45° below the horizontal.
    path_initial_angle_at_toe_upper_enabled: bool = False
    path_initial_angle_at_toe_upper_deg: float = 45.0
    path_initial_angle_at_toe_lower_enabled: bool = False
    path_initial_angle_at_toe_lower_deg: float = 45.0
    # Segment Length. Unticked means AUTOMATIC (~0.3·H), which is the normal
    # way to run a Path Search; the value is only read when ticked. The
    # default value is the one the reference's own panel happens to show for
    # its model — it means nothing until the box is ticked.
    path_segment_length_manual: bool = False
    path_segment_length_value: float = 7.142857
    path_convex_only: bool = False
    # ``path_optimize`` used to sit here, True by default and read by
    # ``build_search``, while the checkbox the Path Search panel actually
    # shows wrote ``optimize_enabled`` — which no analysis read. Visible
    # name dead, hidden name live: the shape of D07b, found while closing
    # D08. Retired in v0.1.104; see ``_SHADOW_FIELDS``.

    # ---------- Block Search (non-circular) ----------
    block_num_surfaces: int = 5000
    block_multiple_groups: bool = False
    block_left_start_angle_deg: float = 135.0
    block_left_end_angle_deg: float = 135.0
    block_right_start_angle_deg: float = 45.0
    block_right_end_angle_deg: float = 45.0
    block_convex_only: bool = False
    # Read by the search, unlike the two projection angles that used to sit
    # here. What the interface derives it from does not match what the
    # reference calls Multiple Groups — see D07c.
    block_num_groups: int = 3

    # ---------- Optimize Surfaces (post-processing, non-circular) ----------
    # v0.1.119 — THREE states, and the third one is the default. ``None``
    # means AUTOMATIC: on for Simulated Annealing, off for the others, which
    # is what the reference documents ("By default the Optimize Surfaces
    # option is enabled for Simulated Annealing [...] It is recommended that
    # this option is always enabled"). ``True`` and ``False`` are the user's
    # own answer and always win, so unticking it for an annealing run really
    # unticks it.
    #
    # It is a tri-state rather than a plain ``True`` default because the two
    # are not the same statement: a stored ``false`` written by a model saved
    # before this version is a default nobody chose, and flipping it under
    # those models would change their answers without anyone asking. See
    # ``optimize_enabled_for``.
    optimize_enabled: Optional[bool] = None
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

    # ---------- Weak Layer Handling (v0.1.121) ----------
    # How a trial surface is clipped when it touches more than one weak
    # layer. Two deterministic policies, both documented by the reference
    # interface:
    #
    #   "highest"    every weak layer the surface touches clips it, and the
    #                clipped surface follows the HIGHEST of them. One
    #                evaluation per surface, and the right choice when only
    #                the top joint is of concern.
    #   "auto_cases" every combination of the touched layers being on or
    #                off is evaluated and the WORST is kept. Rigorous, and
    #                2**n evaluations of one surface.
    #
    # The reference has a third, heuristic, policy. It is an extension of
    # Particle Swarm Optimization and exists only on top of it; with no PSO
    # in this program it would have nothing to attach to, so it is left out
    # rather than approximated.
    weak_layer_handling: str = WeakLayerHandling.HIGHEST.value
    # Ceiling on how many weak layers one surface may be cut by under
    # "auto_cases". Eight layers is 256 evaluations of a single surface;
    # past this the search reverts to "highest" FOR THAT SURFACE and says
    # so in the warnings, because a silently truncated case set reads
    # exactly like full coverage.
    weak_layer_max_cases_log2: int = 6

    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "SearchSettings":
        """Read a stored block, migrating the settings that lived twice.

        Until v0.1.103 this was a bare ``SearchSettings(**data)``, so a
        stored key that is no longer a field would raise ``TypeError`` and
        every model ever saved carries several. Unknown keys are now
        ignored, which is what a format that has to survive its own history
        needs.

        **Which of the two wins when a file carries both and they
        disagree**: the one that departs from its own default, because it
        is the only one of the two that shows intent. A model built by a
        script set ONE of the names on purpose and left the other at
        whatever the dataclass gave it; a model saved from the interface
        has them equal, so the question does not arise. Same reasoning as
        ``AdvancedSettings.from_dict``, read the other way round: a value
        that never reached a calculation expresses no intent to preserve,
        and one that differs from its default does.
        """
        data = dict(data or {})
        names = {f.name for f in dataclass_fields(cls)}
        defaults = {f.name: f.default for f in dataclass_fields(cls)}
        notes: list[str] = []

        def _resolve(survivor: str, old, old_default) -> None:
            """Store ``old`` under ``survivor`` if it is the one with intent."""
            if survivor not in data:
                data[survivor] = old          # older format: only the one name
                return
            if data[survivor] == old:
                return                         # written from the interface
            if old != old_default and data[survivor] == defaults[survivor]:
                data[survivor] = old

        # ---- same quantity, two names: the value migrates straight across
        for shadow in ("path_num_paths", "auto_refine_iterations",
                       "auto_refine_divisions"):
            if shadow in data:
                old_default, survivor = _SHADOW_FIELDS[shadow]
                _resolve(survivor, data.pop(shadow), old_default)

        # ---- segment length: 0 used to mean "automatic", which is now the
        # unticked checkbox. Only migrates when the old field shows intent
        # AND the pair that replaced it is still untouched.
        if "path_segment_length" in data:
            old = data.pop("path_segment_length")
            old_default = _SHADOW_FIELDS["path_segment_length"][0]
            untouched = (
                data.get("path_segment_length_manual",
                         defaults["path_segment_length_manual"])
                == defaults["path_segment_length_manual"]
                and data.get("path_segment_length_value",
                             defaults["path_segment_length_value"])
                == defaults["path_segment_length_value"])
            if old != old_default and untouched:
                try:
                    old = float(old)
                except (TypeError, ValueError):
                    old = old_default
                data["path_segment_length_manual"] = old > 0.0
                if old > 0.0:
                    data["path_segment_length_value"] = old

        # ---- the toe angles CANNOT be migrated here and are not guessed.
        # They were stored in the search's toe-to-crest frame; the fields
        # that replaced them are absolute, which means the conversion needs
        # the failure direction — a property of the project, not of this
        # block. Dropping them silently would be the same fault this whole
        # change is about, so a value that carried intent is reported.
        #
        # ``pre_v1103`` is the marker that this FILE predates the change of
        # frame, and it is the PRESENCE of a retired twin, never its value.
        # See the block below for why the value cannot be the marker.
        pre_v1103 = any(k in data for k in ("path_min_angle_deg",
                                            "path_max_angle_deg",
                                            "path_upper_angle_enabled"))
        for shadow in ("path_min_angle_deg", "path_max_angle_deg",
                       "path_upper_angle_enabled", "sa_temperature_factor"):
            if shadow not in data:
                continue
            old = data.pop(shadow)
            old_default, survivor = _SHADOW_FIELDS[shadow]
            if old == old_default:
                continue
            # When the surviving angle is switched ON, the twin says nothing
            # the block below does not say better: the old dialog wrote the
            # twin as -abs(the very value the survivor holds), so its number
            # is redundant and only the survivor reaches a calculation.
            if survivor is not None and survivor.startswith("path_initial"):
                side = "upper" if "upper" in survivor else "lower"
                if data.get(f"path_initial_angle_at_toe_{side}_enabled",
                            defaults[f"path_initial_angle_at_toe_{side}_enabled"]):
                    continue
            if shadow == "sa_temperature_factor":
                why = ("it held a geometric cooling rate that no analysis "
                       "ever read; the coefficient the schedule does use is")
            else:
                why = ("it held an angle in the search's own toe-to-crest "
                       "frame and the field replacing it is absolute, so "
                       "converting it needs the failure direction, which is "
                       "not part of this block. The field to set is")
            notes.append(
                f"This model carries {shadow} = {old}, removed in v0.1.103: "
                f"{why} {survivor}. The stored value was NOT converted.")

        # ---- v0.1.134 — the note above fires on the RETIRED twin, and for
        # the Initial Angle at Toe that is the wrong field to watch.
        #
        # The pre-v0.1.103 dialog wrote BOTH names from one spin box: the
        # survivor got the typed value ``v`` and the twin got ``-abs(v)``.
        # So the twin carries no information the survivor lacks, and the
        # number the engine reads today — the survivor — was written in the
        # OLD frame and is being read in the new one. Two consequences the
        # note above cannot cover:
        #
        #   * its trigger is "the twin differs from ITS default", and the
        #     twin is the negated mirror of the box, whose own default is
        #     45. A user who ticked the box and left it at 45 stored the
        #     twin at exactly -45, its default, and got NO note at all;
        #   * it says "the stored value was NOT converted", which is true of
        #     the twin and beside the point for the survivor.
        #
        # And the twin does not survive ``asdict``, so the first save drops
        # it and nothing can ever warn again. Hence: warn on the presence of
        # the twin, whatever its value, whenever the surviving angle is
        # switched on. Still no conversion — the failure direction is not
        # here, and that part of the v0.1.103 decision stands.
        if pre_v1103:
            for side in ("lower", "upper"):
                enabled = f"path_initial_angle_at_toe_{side}_enabled"
                value = f"path_initial_angle_at_toe_{side}_deg"
                if not data.get(enabled, defaults[enabled]):
                    continue
                notes.append(
                    f"This model was saved before v0.1.103, and its Path "
                    f"Search {side} Initial Angle at Toe is ON at "
                    f"{data.get(value, defaults[value])}°. That number was "
                    f"read in the search's own toe-to-crest frame then and "
                    f"is read as ABSOLUTE now — counter-clockwise from the "
                    f"+x axis — so it does not describe the same limit. It "
                    f"was NOT converted: doing so needs the failure "
                    f"direction, which is not part of this block. Check "
                    f"{value} before trusting this run.")

        # ---- path_optimize: the ONLY shadow whose note fires on the value
        # that EQUALS its old default, and the reason is that this one is
        # the reverse of the others. Every model ever saved carries
        # ``path_optimize = True`` because nothing could set it to anything
        # else — the interface never showed it — and True is the value that
        # made Path Search optimise. Dropping it therefore CHANGES the
        # number for exactly the models that never chose it, which is the
        # one case worth saying out loud. ``False`` needs no note: the
        # replacement is unticked by default, so the behaviour is the same.
        if "path_optimize" in data:
            old = data.pop("path_optimize")
            if old and not data.get("optimize_enabled",
                                    defaults["optimize_enabled"]):
                notes.append(
                    "This model carries path_optimize = True, removed in "
                    "v0.1.104. Path Search used to optimise its best "
                    "surfaces whether or not anything asked it to, because "
                    "that field defaulted to True and the interface never "
                    "showed it. The optimisation is now the Optimize "
                    "Surfaces checkbox, which is UNTICKED here, so this run "
                    "does not optimise. Tick it to get the old behaviour.")

        # ---- read by nobody, ever: dropped without a word, because a value
        # that never reached a calculation has nothing to say.
        for shadow, (_old_default, survivor) in _SHADOW_FIELDS.items():
            if survivor is None:
                data.pop(shadow, None)

        obj = cls(**{k: v for k, v in data.items() if k in names})
        # Not a field: it must not travel back out through ``asdict``.
        obj._migration_notes = notes
        return obj

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


#: Search methods for which Optimize Surfaces is on unless the user says
#: otherwise. A set rather than a comparison because the reference states
#: the default per method and nothing says the list cannot grow — and in
#: v0.1.126 it grew.
#:
#: The swarm joins it because the reference says so in as many words:
#: optimisation is "strongly recommended with PSO, particularly in the
#: case of multiple mins", since without it a multimodal search hunts
#: local minima and can miss the global one. Measured on verification
#: problem 103, ratio 1.4: 1.3329 without and 1.2538 with.
_OPTIMIZE_ON_BY_DEFAULT = frozenset({
    SearchMethod.SIMULATED_ANNEALING.value,
    SearchMethod.PARTICLE_SWARM.value,
})


def optimize_enabled_for(search: "SearchSettings") -> bool:
    """Resolve the tri-state ``optimize_enabled`` for this search method.

    v0.1.119. ``None`` — the default, and what a model written from now on
    carries when nobody touched the box — means AUTOMATIC: on for Simulated
    Annealing, off for the rest, which is the default the reference
    documents. ``True`` and ``False`` are the user's answer and win.

    Why the annealing needs it, measured on the v0.1.17 test slope over
    seven seeds with the two v0.1.119 engine fixes in place: with this off
    the worst seed lands at 1.2054 against a circular minimum of 1.1135;
    with it on, at 1.1232, and six of the seven fall BELOW the circle. The
    reference does not merely default it on for this search, it recommends
    never turning it off.

    v0.1.128 — and the non-circular Auto Refine, which the reference also
    defaults ON ("automatically ON by default for the Auto Refine
    (Non-Circular) search method"). It cannot join
    ``_OPTIMIZE_ON_BY_DEFAULT``, which is keyed by method: the CIRCULAR
    Auto Refine shares that method id and has nothing to optimise, so
    turning it on there would only produce the note that says it was
    ignored.
    """
    declared = getattr(search, "optimize_enabled", None)
    if declared is None:
        return (search.search_method in _OPTIMIZE_ON_BY_DEFAULT
                or is_auto_refine_non_circular(search))
    return bool(declared)


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
class SeismicAnalysisSettings:
    """What a seismic run reports, beyond the factor of safety.

    Two analyses, and the second needs the first. ``compute_ky`` asks for
    the critical seismic coefficient of every surface — the coefficient
    that brings the factor down to ``ky_target_fos`` — and reports the
    surface that needs the LOWEST one. ``newmark`` asks for the permanent
    displacement, which is the double integral of whatever a record does
    above that coefficient, and reports the surface that moves the MOST.

    They share a search objective and that is not a shortcut: the
    displacement of a rigid block is non-increasing in the critical
    acceleration, so the surface that moves most is the surface with the
    lowest Ky. Turning on ``newmark`` therefore turns on the Ky solve too,
    and :meth:`objective` says so in one place instead of two.

    v0.1.127.
    """

    # Critical seismic coefficient for every surface.
    compute_ky: bool = False
    # The factor Ky is solved to reach. The reference defaults to 1.0 and
    # lets the user ask for another; so does this.
    ky_target_fos: float = 1.0

    # Newmark permanent displacement.
    newmark: bool = False
    # Which record, by id. Empty means "none chosen", which is an error
    # the run reports rather than a zero it invents.
    record_id: str = ""
    # Polarity of the record: see ogr_slip2d.newmark.Polarity. The
    # reference default is the larger of the two polarities.
    polarity: str = "maximum"
    # Newmark assumption 4: the upslope resistance is infinite, so the
    # block only moves downslope. Off means the symmetric two-sided block.
    allow_upslope: bool = False
    # The reference offers "do not scale" or "scale by a factor of".
    # A factor of 1.0 is the first of those, so one field says both.
    scale: float = 1.0

    # ------------------------------------------------------------------
    @property
    def needs_ky(self) -> bool:
        """Whether a run has to solve Ky for every surface."""
        return bool(self.compute_ky or self.newmark)

    def objective(self) -> str:
        """The quantity the search minimises: ``"fos"`` or ``"ky"``."""
        return "ky" if self.needs_ky else "fos"


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
    # Range searched for the interslice force scaling factor.
    #
    # v0.1.106 — was −1.5, and that lower end was never justified by
    # anything. The widening of v0.1.74 (±1.25 → ±1.5) was driven by the
    # Ej_1 circle needing λ = 1.4919, which is the POSITIVE side; the
    # negative tail came along as symmetry. The reference's own models
    # carry ``min_lambda: -0.1``, and that is now the default here too.
    #
    # It stopped being harmless in this version. λ is the inclination of
    # the inter-slice force, X/E = tan θ, so λ = −1.5 is a resultant
    # inclined 56° downward-BACKWARD on a mass sliding forward. Until
    # v0.1.106 no such λ could win, because ``F_m`` did not depend on λ at
    # all and ``F_f − F_m`` had exactly one crossing. Now it can have
    # several, and on the Duncan and Wright buoyant polyline the crossing
    # at λ = −1.5 returned 1.051 where the answer is 1.60 — the first
    # crossing in ascending λ, so the outer search took it.
    #
    # A user who wants the old reach still has it: the range is a setting,
    # and ``lambda_grid`` intersects the calibrated shape with it.
    min_lambda: float = -0.1
    # v0.1.90 — was 1.5. The reference's own models carry max_lambda 6
    # with enforcement off; clipping at 1.5 left Spencer and GLE unable to
    # bracket surfaces whose root sits beyond it. Sampling past the
    # calibrated shape is lazy, so this widens what CAN be reached without
    # adding a single evaluation to a surface that already converges.
    max_lambda: float = 6.0
    iterate_steffensen: bool = True
    # v0.1.97 — parallel surface search.
    #
    # Processes and not threads: every inner loop of the solver is pure
    # Python, so the GIL would serialise them straight back. This cannot
    # change a single number by construction — the circles of a grid are
    # independent, and ``regions_frozen`` guarantees the project does not
    # move while it is analysed — which is why the test that guards it
    # demands BIT-IDENTICAL output rather than agreement to a tolerance.
    parallel_search: bool = True
    # Share of the machine's logical processors the search may occupy.
    #
    # 50 % and not 100 %, and the reason is measured rather than polite:
    # on the Ej_2 reference grid the speed-up is flat from two workers
    # upwards (1.3x to 1.5x across 2, 3, 4, 6 and 7 processes, against a
    # 15 % drift between two identical control runs). The bottleneck is
    # not the number of cores, so taking the whole machine buys nothing
    # and costs the user every other program they have open.
    parallel_cpu_percent: int = 50
    # v0.1.121 — ceiling on the inclination of a slice base, in degrees.
    #
    # A near-vertical base makes the limit-equilibrium equations numerically
    # unstable: m_alpha = cos(a)(1 + tan(a) tan(phi)/F) collapses towards
    # zero as the base approaches the vertical, and the normal force it
    # divides blows up with it. Every classical formulation assumes the base
    # is a shear plane, and a vertical one is not.
    #
    # It exists because weak layers can produce such bases where nothing
    # else in this program could: a surface that snaps onto a steep joint
    # inherits its inclination. The reference carries the same control, in
    # its Advanced project settings, with the same default of 80 degrees,
    # and reports the surfaces it rejects rather than analysing them.
    #
    # 80 degrees and not 90: at 80 degrees with phi = 30 and F = 1 the
    # factor m_alpha is already down to 0.235, so the last ten degrees are
    # where the conditioning is lost, not where it ends.
    max_base_angle_deg: float = 80.0

    # v0.1.126 — *Use enhanced PSO algorithm*. Here rather than beside the
    # other swarm settings because that is where the reference puts it,
    # and because it belongs with the other switches that change HOW a
    # search runs rather than what it searches — ``max_base_angle_deg``
    # above is here for the same reason. On by default, as documented.
    pso_enhanced: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AdvancedSettings":
        """Read a stored block, migrating the two mistaken defaults.

        A file written before v0.1.74 carries values that never reached a
        calculation, so they express no intent to preserve — which is
        exactly what makes rewriting them safe, and what would make
        honouring them unsafe.
        """
        data = dict(data or {})
        # v0.1.97 briefly stored a raw process count before the setting was
        # expressed as a share of the machine. Nothing shipped with it, but
        # a project saved mid-development would otherwise carry a key no
        # longer read, silently losing the choice it recorded.
        if "num_processes" in data:
            n = data.pop("num_processes")
            try:
                n = int(n)
            except (TypeError, ValueError):
                n = 0
            if n == 1:
                data.setdefault("parallel_search", False)
            elif n > 1:
                import os
                total = os.cpu_count() or 1
                data.setdefault("parallel_cpu_percent",
                                max(1, min(100, round(100 * n / total))))
        # ``min_initial_fs`` → ``initial_fos``
        if "min_initial_fs" in data and "initial_fos" not in data:
            data["initial_fos"] = data.pop("min_initial_fs")
        data.pop("min_initial_fs", None)
        # The two migrations. Both are conditional on the value being the
        # old default: a user who deliberately typed something else keeps
        # it, because from v0.1.74 on it means something.
        if data.get("check_tensile_stresses") is True:
            data["check_tensile_stresses"] = False
        # Applied in order, and they CHAIN on purpose: a project stored
        # under v0.1.73 carries max_lambda 1.25, which v0.1.74 mapped to
        # 1.5 and v0.1.90 maps on to 6.0. Landing such a project on an
        # intermediate default nobody uses would be worse than either.
        for key, old, new in (("min_lambda", -1.25, -1.5),
                              ("min_lambda", -1.5, -0.1),
                              ("max_lambda", 1.25, 1.5),
                              ("max_lambda", 1.5, 6.0)):
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
    seismic: SeismicAnalysisSettings = field(
        default_factory=SeismicAnalysisSettings)
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

    def surface_filter_kwargs(self) -> dict:
        """Surface Filter arguments shared by every search object.

        v0.1.102 — the same reason ``admissibility_kwargs`` exists: one
        place that turns settings into search arguments. Until now these
        two were declared, editable, saved to the .ogr and read by nobody
        (anomaly A37-1), which is rule 7 exactly.

        ``None`` means OFF and is passed through as such. ``min_area`` is
        deliberately NOT here: it has a different per-search default when
        unset (``or 1.0``, ``or 0.5``, ``or 2.0``), so it cannot travel in
        a dict that every branch expands the same way.
        """
        s = self.search
        return {
            "min_elevation": (None if s.min_elevation is None
                              else float(s.min_elevation)),
            "min_depth": (None if s.min_depth is None
                          else float(s.min_depth)),
        }

    def optimize_kwargs(self) -> dict:
        """Optimize Surfaces arguments, for the NON-CIRCULAR searches.

        v0.1.104 — the third of the same family as ``admissibility_kwargs``
        and ``surface_filter_kwargs``, and it exists for the same reason
        the other two do: thirteen fields were editable, saved to the .ogr
        and read by nobody at all (defect D08, anomaly A9-1). Ticking
        "Optimize Surfaces" on a Block Search stored the tick, showed it
        again on reopening and changed nothing.

        Returns ``{"optimize": None}`` when the box is unticked, so a
        search built from an unticked model is the search it always was,
        argument for argument.

        v0.1.119 — "unticked" is now a question for
        :func:`optimize_enabled_for`, because the setting has three states
        and the default is the third: ``None`` reads on for Simulated
        Annealing and off for the rest, which is the per-method default the
        reference documents.

        Unlike its two siblings this one does NOT travel in ``common``:
        the reference offers the option only for Surface Type =
        Non-Circular, so handing it to Grid, Slope or the CIRCULAR Auto
        Refine would be an argument they can only ignore.

        v0.1.128 — "the circular Auto Refine", because the non-circular
        one now exists and takes this like the other non-circular
        searches. Which of the two is being built is a question about the
        pair, not the method: see ``is_auto_refine_non_circular``.
        """
        from ogr_slip2d.optimize import OptimizeSettings

        s = self.search
        if not optimize_enabled_for(s):
            return {"optimize": None}
        return {"optimize": OptimizeSettings(
            enabled=True,
            target=str(s.optimize_target),
            fos_threshold=float(s.optimize_fos_threshold),
            max_iterations=int(s.optimize_max_iterations),
            tolerance=float(s.optimize_tolerance),
            step_reduction_factor=float(s.optimize_step_reduction_factor),
            # Unticked means "concave angles will not be allowed", which is
            # a limit of zero — not "no limit". Reading the unticked box as
            # unconstrained would invert the option.
            max_concave_angle_deg=(
                float(s.optimize_max_concave_angle_deg)
                if s.optimize_max_concave_angle_enabled else 0.0),
            explore_all_vertices=bool(s.optimize_explore_all_vertices),
            snap_shallow_to_slope=bool(s.optimize_snap_shallow_to_slope),
            # Unticked Specify Distance means AUTOMATIC, and the value the
            # box shows means nothing until it is ticked.
            snap_distance=(float(s.optimize_snap_distance)
                           if (s.optimize_snap_shallow_to_slope
                               and s.optimize_snap_specify_distance)
                           else None),
            use_surface_checks=bool(
                s.optimize_use_depth_elevation_concave_checks),
        )}

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
            "seismic": asdict(self.seismic),
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
            search=SearchSettings.from_dict(data.get("search", {})),
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
            seismic=SeismicAnalysisSettings(**data.get("seismic", {})),
            summary=ProjectSummary(**data.get("summary", {})),
            max_materials=data.get("max_materials", 20),
            max_supports=data.get("max_supports", 20),
        )
