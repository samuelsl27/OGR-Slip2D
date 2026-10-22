# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The messages of the project's rules and settings, with stable codes
(v0.1.347, D335).

``rules.py`` and ``settings.py`` write sentences the interface shows: why a
run cannot start, why a Block Search object cannot be searched, what the
projection angles were read as, which region lost its material, what a
setting migrated from an old file could not carry. They were English with
their values baked in; each is a code here, with its English template and
the very format specs the f-string used, so the sentence is the one the
core wrote before and the interface translates the template.

A sentence assembled from English words ("left" / "right", "lower" /
"upper", one reason or another) is one whole template per variant.

The coarse ``Refusal.code`` stays what it was -- a program branches on it --
and the message carries this finer code.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

NO_BOUNDARIES = "rule.no_boundaries"
NO_MATERIALS = "rule.no_materials"
BLOCK_OBJECT_EMPTY = "rule.block_object_empty"
BLOCK_POINT_VERTICES = "rule.block_point_vertices"
BLOCK_LINE_VERTICES = "rule.block_line_vertices"
BLOCK_WINDOW_OPEN = "rule.block_window_open"
BLOCK_POLYLINE_SHAPE = "rule.block_polyline_shape"
BLOCK_POLYLINE_NOT_MONOTONE = "rule.block_polyline_not_monotone"
BLOCK_POLYLINE_SEGMENT_MODE = "rule.block_polyline_segment_mode"
BLOCK_ANGLE_REREAD_LEFT = "rule.block_angle_reread_left"
BLOCK_ANGLE_REREAD_RIGHT = "rule.block_angle_reread_right"
BLOCK_ANGLE_OUT_LEFT_LEFT_FACING = "rule.block_angle_out_left_left_facing"
BLOCK_ANGLE_OUT_LEFT_RIGHT_FACING = "rule.block_angle_out_left_right_facing"
BLOCK_ANGLE_OUT_RIGHT_LEFT_FACING = "rule.block_angle_out_right_left_facing"
BLOCK_ANGLE_OUT_RIGHT_RIGHT_FACING = "rule.block_angle_out_right_right_facing"
ORPHAN_REGION = "rule.orphan_region"
MIGRATION_COOLING = "rule.migration_cooling"
MIGRATION_FRAME = "rule.migration_frame"
MIGRATION_TOE_ANGLE_LOWER = "rule.migration_toe_angle_lower"
MIGRATION_TOE_ANGLE_UPPER = "rule.migration_toe_angle_upper"
MIGRATION_PATH_OPTIMIZE = "rule.migration_path_optimize"

_REREAD = (
    "The {label} projection angles are written from {start:g}° to {end:g}°, "
    "and the reference measures them counter-clockwise from the positive x "
    "axis with the Start Angle less than the End Angle. They were read as "
    "{lo:g}° to {hi:g}°: the arc between the two that avoids {forbidden}°, a "
    "direction no {label} projection can take.")
_OUT = (
    "The {label} projection angles, {lo:g}° to {hi:g}°, go outside "
    "{limit_lo:g}° to {limit_hi:g}°, the range the reference gives for "
    "kinematically valid surfaces on a {facing}-facing slope. The search uses "
    "them as given; a projection that cannot reach the ground leaves its "
    "surface invalid.")
_MIGRATION = ("This model carries {shadow} = {old}, removed in v0.1.103: "
              "{why} {survivor}. The stored value was NOT converted.")
_TOE_ANGLE = (
    "This model was saved before v0.1.103, and its Path Search {side} "
    "Initial Angle at Toe is ON at {angle}°. That number was read in the "
    "search's own toe-to-crest frame then and is read as ABSOLUTE now — "
    "counter-clockwise from the +x axis — so it does not describe the same "
    "limit. It was NOT converted: doing so needs the failure direction, "
    "which is not part of this block. Check "
    "path_initial_angle_at_toe_{side}_deg before trusting this run.")


def _fill(template: str, **words) -> str:
    """``template`` with some of its fields written in: the words that make
    one variant of a sentence, leaving the values as fields."""
    for k, v in words.items():
        template = template.replace("{%s}" % k, str(v))
    return template


RULES = {s.code: s for s in (
    MessageSpec(NO_BOUNDARIES,
                "No model to compute. Add an external boundary first."),
    MessageSpec(NO_MATERIALS, "No materials defined."),
    MessageSpec(BLOCK_OBJECT_EMPTY,
                "A Block Search object needs at least one vertex."),
    MessageSpec(BLOCK_POINT_VERTICES,
                "A Block Search Point is a single point; this one has {n} "
                "vertices."),
    MessageSpec(BLOCK_LINE_VERTICES,
                "A Block Search Line is one segment given by two points; "
                "this one has {n} vertices. A path of several segments that "
                "the surface should follow is a Block Search Polyline."),
    MessageSpec(BLOCK_WINDOW_OPEN,
                "A Block Search Window is a closed polygon of at least three "
                "vertices."),
    MessageSpec(BLOCK_POLYLINE_SHAPE,
                "A Block Search Polyline is an open line of at least two "
                "vertices."),
    MessageSpec(BLOCK_POLYLINE_NOT_MONOTONE,
                "A Block Search Polyline has to advance in x from one end to "
                "the other: the trial surface follows it between its two "
                "points, and a polyline that doubles back (or has a vertical "
                "segment) would give a surface that reverses direction."),
    MessageSpec(BLOCK_POLYLINE_SEGMENT_MODE,
                "The Left / Right Line Segment option places its point on the "
                "end segment of that side, which needs a polyline of at least "
                "two segments; this one has one. Use Any Line Segment or End "
                "Point."),
    MessageSpec(BLOCK_ANGLE_REREAD_LEFT,
                _fill(_REREAD, label="left", forbidden=0)),
    MessageSpec(BLOCK_ANGLE_REREAD_RIGHT,
                _fill(_REREAD, label="right", forbidden=180)),
    MessageSpec(BLOCK_ANGLE_OUT_LEFT_LEFT_FACING,
                _fill(_OUT, label="left", facing="left")),
    MessageSpec(BLOCK_ANGLE_OUT_LEFT_RIGHT_FACING,
                _fill(_OUT, label="left", facing="right")),
    MessageSpec(BLOCK_ANGLE_OUT_RIGHT_LEFT_FACING,
                _fill(_OUT, label="right", facing="left")),
    MessageSpec(BLOCK_ANGLE_OUT_RIGHT_RIGHT_FACING,
                _fill(_OUT, label="right", facing="right")),
    MessageSpec(ORPHAN_REGION,
                "The region at ({x:.2f}, {y:.2f}) is assigned a material that "
                "no longer exists. Assign it another material (Properties > "
                "Assign Materials); a surface through it cannot be analysed."),
    MessageSpec(MIGRATION_COOLING,
                _fill(_MIGRATION,
                      why="it held a geometric cooling rate that no analysis "
                          "ever read; the coefficient the schedule does use "
                          "is")),
    MessageSpec(MIGRATION_FRAME,
                _fill(_MIGRATION,
                      why="it held an angle in the search's own toe-to-crest "
                          "frame and the field replacing it is absolute, so "
                          "converting it needs the failure direction, which "
                          "is not part of this block. The field to set is")),
    MessageSpec(MIGRATION_TOE_ANGLE_LOWER, _fill(_TOE_ANGLE, side="lower")),
    MessageSpec(MIGRATION_TOE_ANGLE_UPPER, _fill(_TOE_ANGLE, side="upper")),
    MessageSpec(MIGRATION_PATH_OPTIMIZE,
                "This model carries path_optimize = True, removed in v0.1.104. "
                "Path Search used to optimise its best surfaces whether or not "
                "anything asked it to, because that field defaulted to True "
                "and the interface never showed it. The optimisation is now "
                "the Optimize Surfaces checkbox, which is UNTICKED here, so "
                "this run does not optimise. Tick it to get the old "
                "behaviour."),
)}


def rule_message(code: str, **args) -> Coded:
    """The message ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(RULES, code, **args)


# ======================================================================
# The refusals of the settings and the model (v0.1.350, D335)
# ======================================================================
#: A table of its own and not in ``RULES``: the refusals the analysis and
#: every door that writes a setting ask (optimisation technique, Slope
#: Limit windows, Block Search objects, seismic coefficients, partial
#: factors, boundary-relative line loads).
OPTIMIZE_TECHNIQUE_UNKNOWN = "rule.optimize_technique_unknown"
SLOPE_LIMIT_WINDOWS_OVERLAP = "rule.slope_limit_windows_overlap"
BLOCK_OBJECT_NAMED = "rule.block_object_named"
BLOCK_LABEL_NAMED = "rule.block_label_named"
BLOCK_LABEL_KIND = "rule.block_label_kind"
BLOCK_POLYLINE_OVERLAP = "rule.block_polyline_overlap"
BLOCK_OVERLAP_GROUP = "rule.block_overlap_group"
BLOCK_OVERLAP_WAY_GROUPED = "rule.block_overlap_way_grouped"
BLOCK_OVERLAP_WAY_UNGROUPED = "rule.block_overlap_way_ungrouped"
SEISMIC_NOT_A_NUMBER = "rule.seismic_not_a_number"
SEISMIC_OUT_OF_RANGE = "rule.seismic_out_of_range"
SEISMIC_KH_NEGATIVE = "rule.seismic_kh_negative"
#: One code per partial factor that is not a number: its name is a phrase
#: of the sentence, not a value.
DESIGN_NOT_A_NUMBER = "rule.design_not_a_number."
DESIGN_PERMANENT_BELOW_ONE = "rule.design_permanent_below_one"
DESIGN_PERMANENT_FAVOURABLE_ABOVE_ONE = "rule.design_permanent_favourable_above_one"
DESIGN_PERMANENT_FAVOURABLE_NOT_POSITIVE = (
    "rule.design_permanent_favourable_not_positive")
DESIGN_VARIABLE_BELOW_ONE = "rule.design_variable_below_one"
DESIGN_VARIABLE_FAVOURABLE_ABOVE_ONE = "rule.design_variable_favourable_above_one"
DESIGN_VARIABLE_FAVOURABLE_NEGATIVE = "rule.design_variable_favourable_negative"
LINE_LOAD_NEEDS_GROUND = "rule.line_load_needs_ground"
LINE_LOAD_OFF_GROUND = "rule.line_load_off_ground"

#: ``(attribute, the phrase that names it)``, as ``design_action_factors_
#: refusal`` reads them.
DESIGN_FACTORS = (
    ("factor_permanent", "permanent actions, unfavourable"),
    ("factor_permanent_favourable", "permanent actions, favourable"),
    ("factor_variable", "variable actions, unfavourable"),
    ("factor_variable_favourable", "variable actions, favourable"),
)

_OVERLAP_DETAIL = (
    "With two sets, a Grid Search generates the circles that run from one "
    "window to the other, a rule measured on separate windows only: on the "
    "stretch two windows share it gives every crossing to the window that "
    "starts further left, which nothing measured supports, and with a window "
    "inside one that starts further left it generates no circle at all. Make "
    "the two windows separate, or use a single set.")

REFUSALS = {s.code: s for s in (
    MessageSpec(OPTIMIZE_TECHNIQUE_UNKNOWN,
                "Unknown optimisation technique {value!r}: it has to be one of "
                "{allowed}."),
    MessageSpec(SLOPE_LIMIT_WINDOWS_OVERLAP,
                "The two sets of Slope Limits overlap ([{a0:g}, {a1:g}] and "
                "[{b0:g}, {b1:g}]). " + _OVERLAP_DETAIL),
    MessageSpec(BLOCK_OBJECT_NAMED, "{label}: {why}"),
    MessageSpec(BLOCK_LABEL_NAMED, "{name} #{n}"),
    MessageSpec(BLOCK_LABEL_KIND, "{kind} #{n}", kinds=(("kind", "label"),)),
    MessageSpec(BLOCK_POLYLINE_OVERLAP,
                "{other} overlaps the lateral extent of the Block Search "
                "Polyline {polyline} (x from {lo:g} to {hi:g}){where}. This is "
                "not allowed: the trial surface follows the polyline between "
                "its two points, and a vertex of another object inside that "
                "range would cut the stretch.{way_out}"),
    MessageSpec(BLOCK_OVERLAP_GROUP, " (both in Group ID {group})"),
    MessageSpec(BLOCK_OVERLAP_WAY_GROUPED,
                " Give them different Group IDs to search them separately."),
    MessageSpec(BLOCK_OVERLAP_WAY_UNGROUPED,
                " To search them separately, turn Multiple Groups on and give "
                "them different Group IDs."),
    MessageSpec(SEISMIC_NOT_A_NUMBER, "{name} must be a number, got {value!r}."),
    MessageSpec(SEISMIC_OUT_OF_RANGE,
                "|{name}| must be below 1 (a fraction of g), got {value}."),
    MessageSpec(SEISMIC_KH_NEGATIVE,
                "kh must not be negative, got {value}. It is the magnitude of "
                "the horizontal seismic force, which always acts in the "
                "sliding direction of each surface, out of the slope; its sign "
                "does not choose a direction."),
    MessageSpec(DESIGN_PERMANENT_BELOW_ONE,
                "The partial factor on unfavourable permanent actions must be "
                "at least 1, got {value}: below 1 it would make the driving "
                "weight lighter than the characteristic one."),
    MessageSpec(DESIGN_PERMANENT_FAVOURABLE_ABOVE_ONE,
                "The partial factor on favourable permanent actions must be at "
                "most 1, got {value}: above 1 it would make the resisting "
                "weight heavier than the characteristic one."),
    MessageSpec(DESIGN_PERMANENT_FAVOURABLE_NOT_POSITIVE,
                "The partial factor on favourable permanent actions must be "
                "above 0, got {value}: a permanent action keeps its sign, and "
                "at 0 the slices that resist would have no weight."),
    MessageSpec(DESIGN_VARIABLE_BELOW_ONE,
                "The partial factor on unfavourable variable actions must be at "
                "least 1, got {value}: below 1 it would make a load that drives "
                "the sliding lighter than its characteristic value."),
    MessageSpec(DESIGN_VARIABLE_FAVOURABLE_ABOVE_ONE,
                "The partial factor on favourable variable actions must be at "
                "most 1, got {value}: above 1 it would make a load that resists "
                "the sliding heavier than its characteristic value."),
    MessageSpec(DESIGN_VARIABLE_FAVOURABLE_NEGATIVE,
                "The partial factor on favourable variable actions must not be "
                "negative, got {value}: at 0 the load is left out, which is the "
                "most a favourable variable action can be discounted."),
    MessageSpec(LINE_LOAD_NEEDS_GROUND,
                "Line load {name}: an orientation relative to the boundary "
                "needs the ground surface."),
    MessageSpec(LINE_LOAD_OFF_GROUND,
                "Line load {name} at ({x:g}, {y:g}) is not on the ground "
                "surface, so it has no boundary to be normal to."),
) + tuple(MessageSpec(DESIGN_NOT_A_NUMBER + attr,
                      "The partial factor on " + phrase + " must be a finite "
                      "number, got {raw!r}.")
          for attr, phrase in DESIGN_FACTORS)}


def refusal_message(code: str, **args) -> Coded:
    """A refusal of the settings or the model, ``code`` with ``args``: its
    English sentence, carrying the code and the values (v0.1.350)."""
    return coded(REFUSALS, code, **args)


def nested_refusal(code: str, **args) -> dict:
    """One of these refusals as the value of another message's field."""
    from ..messages import as_nested
    return as_nested(refusal_message(code, **args))


# ======================================================================
# The refusals of the strength models (v0.1.351, D335)
# ======================================================================
#: Why a material's strength model cannot be computed with: the tables of
#: the function models, Snowden, the anisotropic models and the links of a
#: Generalized Anisotropic one. A value the old f-string wrote with ``!r``
#: of an object that is not a plain string (a row, a list) travels as its
#: ``repr`` already made, so the sentence is the same in the window, in the
#: API's JSON and after a pickle.
from ..materials.builtin_models import (  # noqa: E402
    ANISOTROPIC_FUNCTION_LEGACY_NOTE as _ANISO_LEGACY,
    GENERALIZED_SURFACE_NOTE as _GEN_SURFACE_LEGACY,
    SNOWDEN_LEGACY_NOTE as _SNOWDEN_LEGACY)

S_MATERIAL = "strength.material"
S_POINT_NOT_FINITE = "strength.point_not_finite"
S_ROW_NOT_FINITE = "strength.row_not_finite"
S_ROW_STRENGTH = "strength.row_strength"
S_LAST_RANGE_END = "strength.last_range_end"
S_POINTS_NOT_LIST = "strength.points.not_list"
S_POINTS_EMPTY = "strength.points.empty"
S_POINTS_NOT_TWO = "strength.points.not_two"
S_POINTS_NEGATIVE = "strength.points.negative"
S_POINTS_ORDER = "strength.points.order"
S_DISCRETE_TYPE = "strength.discrete.type"
S_DISCRETE_METHOD = "strength.discrete.method"
S_DISCRETE_NOT_LIST = "strength.discrete.not_list"
S_DISCRETE_EMPTY = "strength.discrete.empty"
S_DISCRETE_NOT_POINT = "strength.discrete.not_point"
S_DISCRETE_COHESION = "strength.discrete.cohesion"
S_DISCRETE_ANGLE = "strength.discrete.angle"
S_DISCRETE_REPEATED = "strength.discrete.repeated"
S_CPHI_NOT_LIST = "strength.cphi.not_list"
S_CPHI_EMPTY = "strength.cphi.empty"
S_CPHI_NOT_THREE = "strength.cphi.not_three"
S_CPHI_ORDER = "strength.cphi.order"
S_ANISO_NOT_LIST = "strength.aniso.not_list"
S_ANISO_EMPTY = "strength.aniso.empty"
S_ANISO_NOT_THREE = "strength.aniso.not_three"
S_ANISO_START = "strength.aniso.start"
S_ANISO_ORDER = "strength.aniso.order"
S_ANISO_LEGACY = "strength.aniso.legacy"
S_SNOWDEN_AB = "strength.snowden.ab"
S_SNOWDEN_FUNCTION = "strength.snowden.function."
S_SNOWDEN_FUNCTION_ERROR = "strength.snowden.function_error."
S_SNOWDEN_NOT_FUNCTION = "strength.snowden.not_function"
#: Why Snowden could not build one of its two functions
#: (``IncompleteSnowden``), one code per role.
S_SNOWDEN_NOT_A_FUNCTION = "strength.snowden.not_a_function."
S_SNOWDEN_CANNOT_BUILD = "strength.snowden.cannot_build."
S_SNOWDEN_LEGACY = "strength.snowden.legacy"
S_ANISO_LINEAR_AB = "strength.aniso_linear.ab"
S_GEN_NOT_LIST = "strength.gen.not_list"
S_GEN_EMPTY = "strength.gen.empty"
S_GEN_NOT_RULE = "strength.gen.not_rule"
S_GEN_ANGLES_NAN = "strength.gen.angles_nan"
S_GEN_ANGLES = "strength.gen.angles"
S_GEN_START = "strength.gen.start"
S_GEN_GAP = "strength.gen.gap"
S_GEN_OVERLAP = "strength.gen.overlap"
S_GEN_NO_MODEL = "strength.gen.no_model"
S_GEN_MODEL_ERROR = "strength.gen.model_error"
S_GEN_INPUT_TYPE = "strength.gen.input_type"
S_GEN_PARENT_WATER = "strength.gen.parent_water"
S_GEN_SURFACE_LEGACY = "strength.gen.surface_legacy"
S_AOS_DEFINITION = "strength.aos.definition"
S_AOS_MAPPING = "strength.aos.mapping"
S_AOS_SELECTION = "strength.aos.selection"
S_AOS_BASE_IF_WEAKER = "strength.aos.base_if_weaker"
S_AOS_BASE = "strength.aos.base"
S_AOS_JOINTS = "strength.aos.joints"
S_AOS_JOINT_MODEL = "strength.aos.joint_model"
S_AOS_JOINT_SURFACE = "strength.aos.joint_surface"
S_AOS_JOINT_ANGLE = "strength.aos.joint_angle"
S_AOS_AB = "strength.aos.ab"
S_AOS_MODEL_ERROR = "strength.aos.model_error"
S_AOS_NESTED = "strength.aos.nested"
#: ``rule 2``, ``the base``, ``joint 1`` -- and capitalised -- as a fragment.
S_CHILD = "strength.child."
S_CHILD_CAP = "strength.child_cap."
S_LINK_MISSING = "strength.link.missing"
S_LINK_SELF = "strength.link.self"
S_LINK_GENERALIZED = "strength.link.generalized"
S_SURFACE_MISSING = "strength.surface_missing"
S_SURFACE_IN_USE = "strength.surface_in_use"

_NS_ST = "(normal stress, shear strength)"
_NS_C_PHI = "(normal stress, cohesion, friction angle)"
_INCREASE = "The normal stresses must increase strictly: "
_TO_C_PHI = "(angle to, c, phi)"
_ROLES = (("bedding", "bedding"), ("rock_mass", "rock mass"))

STRENGTH_REFUSALS = {s.code: s for s in (
    MessageSpec(S_MATERIAL, "Material {name!r}, {model}: {why}",
                kinds=(("model", "label"),)),
    MessageSpec(S_POINT_NOT_FINITE, "Point {i} holds a value that is not finite."),
    MessageSpec(S_ROW_NOT_FINITE, "Row {i} holds a value that is not finite."),
    MessageSpec(S_ROW_STRENGTH,
                "Row {i}: the cohesion must be ≥ 0 and the friction angle in "
                "[0, 90), got c = {c:g}, phi = {phi:g}."),
    MessageSpec(S_LAST_RANGE_END,
                "The last range must end at +90 degrees; it ends at {end:g}."),
    MessageSpec(S_POINTS_NOT_LIST,
                "The table must be a list of " + _NS_ST + " points."),
    MessageSpec(S_POINTS_EMPTY,
                "The table has no points: at least one " + _NS_ST + " point is "
                "needed."),
    MessageSpec(S_POINTS_NOT_TWO,
                "Point {i} is not two numbers " + _NS_ST + ": {point}."),
    MessageSpec(S_POINTS_NEGATIVE,
                "Point {i}: the shear strength must be zero or more, got "
                "{tau:g}."),
    MessageSpec(S_POINTS_ORDER,
                _INCREASE + "point {next} ({s_next:g}) does not exceed point "
                "{i} ({s_i:g})."),
    MessageSpec(S_DISCRETE_TYPE,
                "The function type must be one of {choices}, got {value}."),
    MessageSpec(S_DISCRETE_METHOD,
                "The interpolation method must be one of {choices}, got "
                "{value}."),
    MessageSpec(S_DISCRETE_NOT_LIST, "The table must be a list of {what} points."),
    MessageSpec(S_DISCRETE_EMPTY,
                "The table has no points: at least one {what} point is "
                "needed."),
    MessageSpec(S_DISCRETE_NOT_POINT, "Point {i} is not {what}: {point}."),
    MessageSpec(S_DISCRETE_COHESION,
                "Point {i}: the cohesion must be zero or more, got {c:g}."),
    MessageSpec(S_DISCRETE_ANGLE,
                "Point {i}: the friction angle must be in [0, 90), got "
                "{phi:g}."),
    MessageSpec(S_DISCRETE_REPEATED,
                "Point {i} repeats the place ({x:g}, {y:g}): two strengths for "
                "one point."),
    MessageSpec(S_CPHI_NOT_LIST,
                "The table must be a list of " + _NS_C_PHI + " rows."),
    MessageSpec(S_CPHI_EMPTY,
                "The table has no rows: at least one " + _NS_C_PHI + " row is "
                "needed."),
    MessageSpec(S_CPHI_NOT_THREE,
                "Row {i} is not three numbers " + _NS_C_PHI + ": {row}."),
    MessageSpec(S_CPHI_ORDER,
                _INCREASE + "row {next} ({s_next:g}) does not exceed row {i} "
                "({s_i:g})."),
    MessageSpec(S_ANISO_NOT_LIST,
                "The table must be a list of " + _TO_C_PHI + " rows."),
    MessageSpec(S_ANISO_EMPTY,
                "The table has no rows: at least one range, ending at +90 "
                "degrees, is needed."),
    MessageSpec(S_ANISO_NOT_THREE,
                "Row {i} is not three numbers " + _TO_C_PHI + ": {row}."),
    MessageSpec(S_ANISO_START,
                "The first range starts at -90 degrees, so its 'angle to' must "
                "be above -90; got {first:g}."),
    MessageSpec(S_ANISO_ORDER,
                "The ranges must be ordered counter-clockwise: row {next} ends "
                "at {end_next:g} degrees, not after row {i} ({end_i:g})."),
    MessageSpec(S_ANISO_LEGACY, _ANISO_LEGACY),
    MessageSpec(S_SNOWDEN_AB,
                "A{side} and B{side} must satisfy 0 <= A{side} <= B{side} <= 90 "
                "degrees; got A{side} = {a:g}, B{side} = {b:g}."),
    MessageSpec(S_SNOWDEN_NOT_FUNCTION,
                "{model} is not a shear-normal or a C/Phi function.",
                kinds=(("model", "label"),)),
    MessageSpec(S_SNOWDEN_LEGACY, _SNOWDEN_LEGACY),
    MessageSpec(S_ANISO_LINEAR_AB,
                "A and B must satisfy 0 <= A <= B degrees; got A = {a:g}, B = "
                "{b:g}."),
    MessageSpec(S_GEN_NOT_LIST,
                "The rules must be a list of {{angle_min, angle_max, model}} "
                "objects."),
    MessageSpec(S_GEN_EMPTY,
                "There are no rules: at least one range, from -90 to +90 "
                "degrees, with its strength model, is needed."),
    MessageSpec(S_GEN_NOT_RULE,
                "Rule {i} is not an {{angle_min, angle_max, model}} object: "
                "{rule}."),
    MessageSpec(S_GEN_ANGLES_NAN, "The angles of rule {i} are not numbers."),
    MessageSpec(S_GEN_ANGLES,
                "Rule {i} must go from a lower to a higher angle within [-90, "
                "90] degrees; it goes from {amin:g} to {amax:g}."),
    MessageSpec(S_GEN_START,
                "The first range starts at -90 degrees; it starts at "
                "{first:g}."),
    MessageSpec(S_GEN_GAP,
                "Rule {next} must start where rule {i} ends ({end:g} degrees); "
                "it starts at {start:g}, which leaves the angles between "
                "{end:g} and {start:g} degrees with no strength."),
    MessageSpec(S_GEN_OVERLAP,
                "Rule {next} must start where rule {i} ends ({end:g} degrees); "
                "it starts at {start:g}, which overlaps it, so part of a range "
                "can never be reached."),
    MessageSpec(S_GEN_NO_MODEL, "Rule {i} has no strength model."),
    MessageSpec(S_GEN_MODEL_ERROR,
                "The strength model of rule {i} cannot be built: {error}"),
    MessageSpec(S_GEN_INPUT_TYPE, "the input is one of {choices}, not {value}."),
    MessageSpec(S_GEN_PARENT_WATER,
                "use_parent_water must be true or false, not {value}."),
    MessageSpec(S_GEN_SURFACE_LEGACY, _GEN_SURFACE_LEGACY),
    MessageSpec(S_AOS_DEFINITION,
                "The anisotropy is defined by 'angle' or 'surface', not "
                "{value}."),
    MessageSpec(S_AOS_MAPPING, "The mapping function is one of {choices}, not "
                               "{value}."),
    MessageSpec(S_AOS_SELECTION,
                "The joint selection is one of {choices}, not {value}."),
    MessageSpec(S_AOS_BASE_IF_WEAKER,
                "use_base_if_weaker must be true or false, not {value}."),
    MessageSpec(S_AOS_BASE,
                "The base needs a strength: a material or a model of its own."),
    MessageSpec(S_AOS_JOINTS,
                "At least one joint is needed, with its angle and its "
                "strength."),
    MessageSpec(S_AOS_JOINT_MODEL,
                "Joint {j} needs a strength: a material or a model of its own."),
    MessageSpec(S_AOS_JOINT_SURFACE, "Joint {j} must name its anisotropic surface."),
    MessageSpec(S_AOS_JOINT_ANGLE,
                "The angle of joint {j} must be a number of degrees."),
    MessageSpec(S_AOS_AB,
                "Joint {j}: A and B must satisfy 0 <= A <= B <= 90 degrees; got "
                "A = {a}, B = {b}."),
    MessageSpec(S_AOS_MODEL_ERROR,
                "The strength model of {child} cannot be built: {error}"),
    MessageSpec(S_AOS_NESTED,
                "{child} holds a Generalized Anisotropic model; it takes a "
                "plain strength."),
    MessageSpec(S_CHILD + "rules", "rule {n}"),
    MessageSpec(S_CHILD + "base", "the base"),
    MessageSpec(S_CHILD + "joints", "joint {n}"),
    MessageSpec(S_CHILD_CAP + "rules", "Rule {n}"),
    MessageSpec(S_CHILD_CAP + "base", "The base"),
    MessageSpec(S_CHILD_CAP + "joints", "Joint {n}"),
    MessageSpec(S_LINK_MISSING, "{who} links a material that is not in the "
                                "project."),
    MessageSpec(S_LINK_SELF, "{who} links the material itself."),
    MessageSpec(S_LINK_GENERALIZED,
                "{who} links {other}, another Generalized Anisotropic material; "
                "a range takes a plain strength model."),
    MessageSpec(S_SURFACE_MISSING,
                "joint {j} names an anisotropic surface that is not in the "
                "model."),
    MessageSpec(S_SURFACE_IN_USE,
                "The anisotropic surface is read by the joints of {users}; "
                "change them first."),
) + tuple(MessageSpec(S_SNOWDEN_FUNCTION + role,
                      "The " + label + " strength function: {why}")
          for role, label in _ROLES)
  + tuple(MessageSpec(S_SNOWDEN_FUNCTION_ERROR + role,
                      "The " + label + " strength function: {error}.")
          for role, label in _ROLES)
  + tuple(MessageSpec(S_SNOWDEN_NOT_A_FUNCTION + role,
                      "the " + label + " function must be a Shear/Normal "
                      "Function or a C/Phi Function, got {data}")
          for role, label in _ROLES)
  + tuple(MessageSpec(S_SNOWDEN_CANNOT_BUILD + role,
                      "the " + label + " function cannot be built: {error}")
          for role, label in _ROLES)}


def strength_refusal(code: str, **args) -> Coded:
    """A refusal of a strength model, ``code`` with ``args``: its English
    sentence, carrying the code and the values (v0.1.351)."""
    return coded(STRENGTH_REFUSALS, code, **args)


def nested_strength(code: str, **args) -> dict:
    """One of these refusals as the value of another message's field."""
    from ..messages import as_nested
    return as_nested(strength_refusal(code, **args))


def child_label(key, capital: bool = False) -> dict:
    """``rule 2``, ``the base`` or ``joint 1`` of a Generalized Anisotropic
    child, nested (``GeneralizedAnisotropic.child_label``'s words)."""
    kind, i = key
    code = (S_CHILD_CAP if capital else S_CHILD) + kind
    return (nested_strength(code) if kind == "base"
            else nested_strength(code, n=i + 1))
