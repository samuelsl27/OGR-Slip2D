# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The analysis notes, with stable codes (v0.1.347, D335).

``settings_warnings`` and the run itself write notes that the Analysis Notes
panel and the status bar show: what a setting could not honour, what a run
decided. They were English sentences with their values baked in by an
f-string, and the interface could only show them in English. Each one is a
code here, with its English template and the very format specs the f-string
used, so the sentence it renders is the one the engine wrote before -- the
tests and the bank read it -- and the interface translates the template.

A sentence the engine assembled from English pieces ("1 weak layer" /
"N weak layers", "above" / "below", a clause appended or not) is one WHOLE
template per variant here, with its singular through ``MessageSpec.one``:
pieces glued in English translate into nothing.

Codes are ``model.*``: about the model as posed, said before any method runs.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import Coded, MessageSpec, coded

# --- the search and its settings --------------------------------------------
SEISMIC_STATISTICS = "model.seismic_statistics"
SLOPE_SEARCH_LIMITS = "model.slope_search_limits"
SLOPE_LIMITS_ONE_SIDE = "model.slope_limits_one_side"
SLOPE_LIMITS_SECOND_ALONE = "model.slope_limits_second_alone"
SLOPE_LIMITS_NESTED = "model.slope_limits_nested"
SLOPE_LIMITS_NESTED_PATH = "model.slope_limits_nested_path"
MAX_ITERATIONS_FLOORED = "model.max_iterations_floored"
MAX_ITERATIONS_RAISED = "model.max_iterations_raised"
STEFFENSEN_NOTHING = "model.steffensen_nothing"
STEFFENSEN_NOTHING_BISHOP = "model.steffensen_nothing_bishop"
BLOCK_NO_OBJECT = "model.block_no_object"
BLOCK_MULTIPLE_NO_OBJECT = "model.block_multiple_no_object"
BLOCK_BANDS_IGNORED = "model.block_bands_ignored"
BLOCK_ONE_GROUP = "model.block_one_group"
BASE_ANGLE_NO_CEILING = "model.base_angle_no_ceiling"
BASE_ANGLE_SCOPE_WEAK = "model.base_angle_scope_weak"
BASE_ANGLE_SCOPE_NO_WEAK = "model.base_angle_scope_no_weak"
M_ALPHA_CLAUSE_OFF = "model.m_alpha_clause_off"
M_ALPHA_CLAUSE_UNSCREENED = "model.m_alpha_clause_unscreened"
M_ALPHA_CLAUSE_ON = "model.m_alpha_clause_on"
M_ALPHA_CLAUSE_ON_PARTIAL = "model.m_alpha_clause_on_partial"
BASE_GOVERNS_NONE = "model.base_governs_none"
BASE_GOVERNS_M_ALPHA = "model.base_governs_m_alpha"
BASE_GOVERNS_SETTING = "model.base_governs_setting"
FOCUS_GUIDED = "model.focus_guided"
INTERSLICE_PONDED = "model.interslice_ponded"
UNDRAINED_ZERO_ABOVE = "model.undrained_zero_above"
UNDRAINED_ZERO_BELOW = "model.undrained_zero_below"
UNDRAINED_ZERO_DEPTH = "model.undrained_zero_depth"
SURFACE_TYPE_MISMATCH = "model.surface_type_mismatch"
AUTO_REFINE_VERTICES = "model.auto_refine_vertices"
PSO_MINIMA_UNOPTIMISED = "model.pso_minima_unoptimised"
OPTIMIZE_NOT_APPLICABLE = "model.optimize_not_applicable"
OPTIMIZE_ALL_WALK = "model.optimize_all_walk"
OPTIMIZE_ALL_ALTERATION = "model.optimize_all_alteration"
SURFACE_ALTERING_IGNORES = "model.surface_altering_ignores"
FAILURE_DIRECTION_R2L = "model.failure_direction_r2l"
FAILURE_DIRECTION_L2R = "model.failure_direction_l2r"

_SLOPE_NESTED = (
    "One set of Slope Limits, [{inner_lo:g}, {inner_hi:g}], lies inside the "
    "other, [{outer_lo:g}, {outer_hi:g}]. The two sets are the ranges where "
    "the ends of a surface may daylight, so the inner one admits no end the "
    "outer one does not: as a filter it does nothing.")
_STEFFENSEN = (
    "Accelerate convergence (Steffensen) is on, and not one of the methods "
    "this run uses has an iteration it can accelerate, so the setting "
    "reached nothing and the results are the same as they would be with it "
    "off. The methods that ran are {methods}.{bishop} Aitken extrapolation "
    "speeds up a fixed point on the factor of safety, and only Bishop "
    "simplified (on circular surfaces) and both Janbu solve one. Spencer and "
    "GLE/Morgenstern-Price solve for the factor and the inter-slice force "
    "together, and extrapolating the factor alone leaves the force behind. "
    "Lowe-Karafiath and Corps of Engineers #1 and #2 iterate on the factor "
    "but are not wired to it. Ordinary/Fellenius has no iteration at all.")
_BISHOP_POLYLINES = (
    " Bishop simplified is in this run and does accelerate, but only on its "
    "circular branch, and this search returns polylines.")
_BANDS_TAIL = (
    " and the Implicit Region Bands setting — {bands} here — configures "
    "nothing. That count only divides the region OGR falls back to when no "
    "Block Search object is drawn.")
_NO_CEILING = (
    "Maximum slice base angle is set to {limit:g} deg, which does not raise "
    "the ceiling on the base of a slice — it removes it. This model draws "
    "{what}, and no surface a weak layer clips will be discarded for the "
    "steepness of its base, however close to vertical the drop at the end of "
    "a layer leaves it. Any value strictly between 0 and 90 applies the "
    "ceiling.")
_SCOPE_WEAK = (
    "This model draws {what}, so the Maximum base angle setting ({limit:g} "
    "deg) reaches the surfaces they clip and nothing else. {clause} "
    "{governs}")
_M_ALPHA_ON = (
    "The m-alpha check is on, and where phi = 0 its {m_alpha_limit:g} limit "
    "is a bare ceiling of {ceiling:.1f} deg on every surface it screens "
    "({named}).")
_UNDRAINED_ZONE = (
    "Material '{name}': its undrained profile reaches zero at elevation "
    "{y0:.4g}, and the material extends {where} that ({y_min:.4g} to "
    "{y_max:.4g}). The soil {where} it has no shear strength at all, so any "
    "surface that goes there has a factor of safety of zero. The Cutoff "
    "cannot bound this side of the line.")
_OPTIMIZE_ALL = (
    "Optimize Surfaces is set to optimise ALL surfaces, so {walk} runs once "
    "per surface the search generates rather than once on the critical one. "
    "The answer is the same kind of answer; the run takes far longer.")
_FAILURE_DIRECTION = (
    "The Failure Direction is set to {declared}, which puts the crest on the "
    "{lower}, but the ground surface is higher on the {higher} (y = "
    "{y_left:g} at the left end against y = {y_right:g} at the right end). "
    "Tension-crack water thrust, support force direction and the Path Search "
    "starting face all read this setting.")

# --- weak layers and supports (the helper modules of settings_warnings) -------
WEAK_LAYER_NO_MATERIAL = "model.weak_layer_no_material"
WEAK_LAYER_ABOVE_GROUND = "model.weak_layer_above_ground"
WALLS_HORIZONTAL = "model.walls_horizontal"
PILES_TOUCH = "model.piles_touch"
PILES_LEANING = "model.piles_leaning"
PILES_UNCHECKED_WATER = "model.piles_unchecked_water"
PILES_UNCHECKED_NEGATIVE = "model.piles_unchecked_negative"
PILES_WATER = "model.piles_water"
PILES_NEGATIVE = "model.piles_negative"
HELICAL_NO_PLATE = "model.helical_no_plate"
HELICAL_RESPACED = "model.helical_respaced"
HELICAL_SPACING_RATIO = "model.helical_spacing_ratio"
SUPPORT_AMBIGUOUS_SET = "model.support_ambiguous_set"
SUPPORT_ORPHAN_REPLACED = "model.support_orphan_replaced"
SUPPORT_ORPHAN_DROPPED = "model.support_orphan_dropped"
SUPPORT_INFINITE_LENGTH = "model.support_infinite_length"
SUPPORT_INFINITE_PLATES = "model.support_infinite_plates"
SUPPORT_INFINITE_BOTH = "model.support_infinite_both"
FORCE_AT_CENTROID_BLIND = "model.force_at_centroid_blind"
FORCE_AT_CENTROID = "model.force_at_centroid"

_WALLS = (" drawn horizontally. A wall's pressure profile is defined from the "
          "crest downwards and a horizontal wall has no crest, so it is "
          "excluded from the analysis rather than analysed with a profile that "
          "would depend on which end was drawn first.")
_LEANING = (" more than {tolerance:.3g}° off vertical (up to {tilt:.1f}°). Ito "
            "and Matsui (1975) derive the pressure for a vertical row, so the "
            "force is integrated ALONG THE SHAFT rather than over depth. The "
            "theory does not say which is right, and projecting one onto the "
            "other here would be this program deciding.")
_AMBIGUOUS = (" of class '{cls}' name no property set and the project "
              "defines {n_sets} sets of that class ({sets}). The first, "
              "'{first}', is used. Assign each support its set in Support "
              "Properties if that is not the one meant.")
_INFINITE = (
    "Support '{name}' ({type_name}) has {where} in {materials}, whose strength "
    "is not finite (Infinite Strength): the soil around it is read as zero "
    "there. Rigid bedrock is a modelling device, not a promise that a support "
    "cannot be pulled out of it, and letting the infinity through would drop "
    "its pull-out or bearing from the minimum.")
_ALONG = "about {percent:.0f} % of its length"
_PLATES = "{hit_plates} of its {n_plates} plates"

#: The kind of a value the interface shows in the reader's language: a list
#: of method ids written ", "-joined, as the engine always wrote it.
METHODS = (("methods", "method_list"),)

NOTES = {s.code: s for s in (
    MessageSpec(SEISMIC_STATISTICS,
                "A seismic analysis mode is on, so the critical surface is the "
                "one with the lowest critical seismic coefficient. The "
                "probabilistic and sensitivity statistics are taken on the "
                "factor of safety OF THAT SURFACE, which is not the lowest "
                "factor of safety of the sample."),
    MessageSpec(SLOPE_SEARCH_LIMITS,
                "Slope Search derives its entry and exit window from the "
                "ground profile, so the Slope Limits you set did not steer "
                "where it looked. They were still applied as a filter, as "
                "they are for every search."),
    MessageSpec(SLOPE_LIMITS_ONE_SIDE,
                "The second set of Slope Limits has only one side set, so it "
                "describes no window and was ignored. Set both the left and "
                "the right limit, or clear them both."),
    MessageSpec(SLOPE_LIMITS_SECOND_ALONE,
                "A second set of Slope Limits is defined but the first is "
                "automatic, and the second set is meant to be added to the "
                "first, not to replace it. It was ignored; set the first set "
                "as well."),
    MessageSpec(SLOPE_LIMITS_NESTED, _SLOPE_NESTED),
    MessageSpec(SLOPE_LIMITS_NESTED_PATH,
                _SLOPE_NESTED + " A Path Search still starts its surfaces in "
                "the set nearer the toe, so there it can change where they "
                "begin."),
    MessageSpec(MAX_ITERATIONS_FLOORED,
                "Maximum iterations is set to {value}, and for Spencer and "
                "GLE/Morgenstern-Price that bounds the outer search for the "
                "inter-slice inclination alone. The fixed point those two "
                "methods solve inside every sample of that search keeps its "
                "own budget of {passes} passes, which this setting raises "
                "only once it is above {passes}; at or below that the inner "
                "iteration is untouched. The methods that iterate on the "
                "factor of safety directly — Bishop and both Janbu — do take "
                "the value as written."),
    MessageSpec(MAX_ITERATIONS_RAISED,
                "Maximum iterations is set to {value}, so for Spencer and "
                "GLE/Morgenstern-Price it now bounds two loops and not one: "
                "the outer search for the inter-slice inclination, and the "
                "fixed point solved inside every sample of it, whose budget "
                "rises from {passes} passes to {budget}. The extra room "
                "changes an answer only where a branch was being cut off "
                "while it was still converging, which takes a convergence "
                "tolerance far tighter than the default one."),
    MessageSpec(STEFFENSEN_NOTHING, _STEFFENSEN.replace("{bishop}", ""),
                kinds=METHODS),
    MessageSpec(STEFFENSEN_NOTHING_BISHOP,
                _STEFFENSEN.replace("{bishop}", _BISHOP_POLYLINES),
                kinds=METHODS),
    MessageSpec(BLOCK_NO_OBJECT,
                "No Block Search object is drawn, so the sampling region is "
                "chosen by the program and not by the model: a box over the "
                "slope face tiled into {bands} vertical band(s) (Implicit "
                "Region Bands), one random vertex in each. The reference "
                "requires at least one Block Search object (window, line, "
                "point or polyline); draw one to search where the model says "
                "the slip surface can run."),
    MessageSpec(BLOCK_MULTIPLE_NO_OBJECT,
                "Multiple Groups is on, but no Block Search object is drawn, "
                "so there are no Group IDs to split the search by: the "
                "setting does nothing here."),
    MessageSpec(BLOCK_BANDS_IGNORED,
                "This model draws {drawn} Block Search objects, so the trial "
                "surfaces are built from them" + _BANDS_TAIL,
                one="This model draws 1 Block Search object, so the trial "
                    "surfaces are built from it" + _BANDS_TAIL,
                count="drawn"),
    MessageSpec(BLOCK_ONE_GROUP,
                "Multiple Groups is on, but every Block Search object has "
                "Group ID {group_id}: that is one group, and the search is "
                "the same as with the setting off. Give the objects "
                "different Group IDs to search them separately."),
    MessageSpec(BASE_ANGLE_NO_CEILING,
                _NO_CEILING.replace("{what}", "{n} weak layers"),
                one=_NO_CEILING.replace("{what}", "1 weak layer"),
                count="n"),
    MessageSpec(BASE_ANGLE_SCOPE_WEAK,
                _SCOPE_WEAK.replace("{what}", "{n} weak layers"),
                one=_SCOPE_WEAK.replace("{what}", "1 weak layer"),
                count="n", group_by=("clause", "governs")),
    MessageSpec(BASE_ANGLE_SCOPE_NO_WEAK,
                "No weak layer is drawn in this model, so the Maximum base "
                "angle setting ({limit:g} deg) reached nothing: it applies "
                "only to surfaces a weak layer has clipped. {clause}",
                group_by=("clause",)),
    MessageSpec(M_ALPHA_CLAUSE_OFF,
                "The m-alpha check is off, so nothing else caps how steeply a "
                "base may run."),
    MessageSpec(M_ALPHA_CLAUSE_UNSCREENED,
                "The m-alpha check is on, but no method in this run is "
                "screened by it ({methods}), so it caps nothing here.",
                kinds=METHODS),
    MessageSpec(M_ALPHA_CLAUSE_ON, _M_ALPHA_ON,
                kinds=(("named", "method_list"),)),
    MessageSpec(M_ALPHA_CLAUSE_ON_PARTIAL,
                _M_ALPHA_ON + " It does not screen {methods}.",
                kinds=(("named", "method_list"), ("methods", "method_list"))),
    MessageSpec(BASE_GOVERNS_NONE,
                "A surface no weak layer clips therefore has no ceiling on "
                "the inclination of its base at all in this run."),
    MessageSpec(BASE_GOVERNS_M_ALPHA,
                "On a weak-layer clip in purely cohesive material the "
                "{ceiling:.1f} deg ceiling therefore governs, and the "
                "{limit:g} deg set here never applies."),
    MessageSpec(BASE_GOVERNS_SETTING,
                "On a weak-layer clip the {limit:g} deg set here is therefore "
                "the tighter of the two, and {ceiling:.1f} deg governs "
                "everywhere else."),
    MessageSpec(FOCUS_GUIDED,
                "This search steers from one candidate surface to the next, "
                "so a focus object narrows the path it walks as well as the "
                "answer it returns. A narrow focus can leave it with NO "
                "surface at all even when surfaces satisfying the focus "
                "exist; that is a limit of the search, not a statement about "
                "the slope. A Grid, Path or Block Search reaches a tightly "
                "focused region more reliably."),
    MessageSpec(INTERSLICE_PONDED,
                "This model has water standing over the ground, and the "
                "prescribed-inclination methods (Lowe-Karafiath, Corps of "
                "Engineers #1 and #2) are set to TOTAL inter-slice forces. "
                "That is the convention the published values of these "
                "methods are in, but it does not hold where water stands on "
                "the slope: the factor of safety then depends on the depth "
                "of the water, the force balance can fail to close, and it "
                "can also close on a root that is not a factor of safety at "
                "all — measured on a fully submerged slope, the search "
                "returned 0.20 where every other method gives 1.61. Treat "
                "these three methods' numbers on this model as unreliable. "
                "Use buoyant unit weights with no water surface (Duncan and "
                "Wright 2005), or set Interslice forces = Effective in "
                "Project Settings."),
    MessageSpec(UNDRAINED_ZERO_ABOVE,
                _UNDRAINED_ZONE.replace("{where}", "above"),
                group_by=("name",)),
    MessageSpec(UNDRAINED_ZERO_BELOW,
                _UNDRAINED_ZONE.replace("{where}", "below"),
                group_by=("name",)),
    MessageSpec(UNDRAINED_ZERO_DEPTH,
                "Material '{name}': its undrained profile reaches zero "
                "{d0:.4g} below its reference, and the material is "
                "{depth:.4g} deep. Below that it has no shear strength and "
                "any surface reaching it has a factor of safety of zero.",
                group_by=("name",)),
    MessageSpec(SURFACE_TYPE_MISMATCH,
                "The Surface Type is set to '{surface_type}' and the Search "
                "Method to '{search_method}', which does not search for that "
                "kind of surface. The method is what runs, so the surfaces "
                "this analysis returns are the ones it generates, whatever "
                "the Surface Type says."),
    MessageSpec(AUTO_REFINE_VERTICES,
                "The search converts each circle into {n_vert:d} vertices, "
                "which is {segments:d} straight segments, and the analysis "
                "uses {n_slices:d} slices. Every vertex is a mandatory slice "
                "boundary, so a surface with more segments than slices is "
                "refused whole: this run would return no surfaces at all. "
                "Raise the number of slices to at least {segments:d}, or "
                "lower the vertices."),
    MessageSpec(PSO_MINIMA_UNOPTIMISED,
                "The Particle Swarm search is reporting several minima with "
                "Optimize Surfaces OFF. It is then looking for LOCAL minima, "
                "and the lowest of them need not be the global minimum of "
                "the slope."),
    MessageSpec(OPTIMIZE_NOT_APPLICABLE,
                "Optimize Surfaces applies to non-circular surfaces, which "
                "are the ones with vertices to move; this project searches "
                "with '{search_method}'. The setting was ignored."),
    MessageSpec(OPTIMIZE_ALL_WALK,
                _OPTIMIZE_ALL.replace("{walk}", "the random walk")),
    MessageSpec(OPTIMIZE_ALL_ALTERATION,
                _OPTIMIZE_ALL.replace("{walk}", "the alteration")),
    MessageSpec(SURFACE_ALTERING_IGNORES,
                "Surface Altering does not read Step Reduction Factor or "
                "Explore All Vertices: they configure the Monte Carlo "
                "technique, and were ignored."),
    MessageSpec(FAILURE_DIRECTION_R2L,
                _FAILURE_DIRECTION.replace("{declared}", "Right to Left")
                .replace("{lower}", "right").replace("{higher}", "left")),
    MessageSpec(FAILURE_DIRECTION_L2R,
                _FAILURE_DIRECTION.replace("{declared}", "Left to Right")
                .replace("{lower}", "left").replace("{higher}", "right")),
    MessageSpec(WEAK_LAYER_NO_MATERIAL,
                "Weak layer {name} has no material assigned, so it carries no "
                "strength of its own and would only change the geometry of "
                "the surfaces it clips. Assign it a material or suppress it."),
    MessageSpec(WEAK_LAYER_ABOVE_GROUND,
                "Weak layer {name} lies entirely above the ground surface, so "
                "any surface it clips is pushed out of the soil and "
                "discarded. Suppress it or move it into the model."),
    MessageSpec(WALLS_HORIZONTAL, "{n} retaining walls are" + _WALLS,
                one="1 retaining wall is" + _WALLS, count="n"),
    MessageSpec(PILES_TOUCH,
                "The pile diameter ({diameter:.3g}) is not smaller than the "
                "out-of-plane spacing ({spacing:.3g}), so there is no opening "
                "between piles. Ito and Matsui (1975) describe soil squeezing "
                "THROUGH that opening and their equation diverges when it "
                "closes, so the row applies no force at all. A continuous "
                "barrier is a wall, not a pile row."),
    MessageSpec(PILES_LEANING, "{n} piles are" + _LEANING,
                one="1 pile is" + _LEANING, count="n"),
    MessageSpec(PILES_UNCHECKED_WATER,
                "It could not be checked whether there is pore pressure along "
                "an Ito-Matsui pile ({error}: {detail})."),
    MessageSpec(PILES_UNCHECKED_NEGATIVE,
                "It could not be checked whether the Ito-Matsui pressure goes "
                "negative near the surface ({error}: {detail})."),
    MessageSpec(PILES_WATER,
                "There is pore pressure along an Ito-Matsui pile. The "
                "published equation is written on the total overburden "
                "because there is no water anywhere in the paper it comes "
                "from; with effective strength parameters this program feeds "
                "it the EFFECTIVE vertical stress, which is the consistent "
                "reading and the conservative one. The theory itself is "
                "silent."),
    MessageSpec(PILES_NEGATIVE,
                "The Ito-Matsui pressure comes out negative over part of the "
                "pile, near the surface, where the cohesion terms outweigh "
                "the overburden: the theory is saying no plastic pressure "
                "develops there. It is integrated as published, so that "
                "stretch reduces the total instead of being quietly set to "
                "zero."),
    MessageSpec(HELICAL_NO_PLATE,
                "The shaft of support '{name}' is not narrower than its "
                "helices, so the plates have no bearing area and the anchor "
                "carries nothing in pullout."),
    MessageSpec(HELICAL_RESPACED,
                "The {n:d} helices of support '{name}' do not fit at "
                "{spacing:.2f} m: the spacing used is {used:.2f} m, the "
                "anchor length divided by the number of gaps."),
    MessageSpec(HELICAL_SPACING_RATIO,
                "The helix spacing of support '{name}' is {ratio:.2f} times "
                "the average helix diameter. Design guides recommend 5 to "
                "12."),
    MessageSpec(SUPPORT_AMBIGUOUS_SET, "{n} supports" + _AMBIGUOUS,
                one="1 support" + _AMBIGUOUS, count="n",
                kinds=(("cls", "label"),)),
    MessageSpec(SUPPORT_ORPHAN_REPLACED,
                "Support '{name}' refers to a property set that is no longer "
                "in the project; '{used}' is used instead, chosen by class."),
    MessageSpec(SUPPORT_ORPHAN_DROPPED,
                "Support '{name}' refers to a property set that is no longer "
                "in the project; it is left out of the analysis."),
    MessageSpec(SUPPORT_INFINITE_LENGTH,
                _INFINITE.replace("{where}", _ALONG),
                kinds=(("type_name", "label"),)),
    MessageSpec(SUPPORT_INFINITE_PLATES,
                _INFINITE.replace("{where}", _PLATES),
                kinds=(("type_name", "label"),)),
    MessageSpec(SUPPORT_INFINITE_BOTH,
                _INFINITE.replace("{where}", _ALONG + " and " + _PLATES),
                kinds=(("type_name", "label"),)),
    MessageSpec(FORCE_AT_CENTROID_BLIND,
                "The support force is set to act at the centroid of its "
                "pressure diagram, and {methods} cannot tell that from acting "
                "at the slip surface: moving a force leaves a couple, and a "
                "couple has nowhere to go in a method that writes force "
                "equilibrium alone. The four methods with a moment equation — "
                "Ordinary, Bishop, Spencer and GLE — do honour it.",
                kinds=METHODS),
    MessageSpec(FORCE_AT_CENTROID,
                "The support force is set to act at the centroid of its "
                "pressure diagram. Only the four methods with a moment "
                "equation — Ordinary, Bishop, Spencer and GLE — can tell that "
                "apart from acting at the slip surface."),
)}


def note(code: str, **args) -> Coded:
    """The note ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(NOTES, code, **args)


def nested_note(code: str, **args) -> dict:
    """A note as the value of another one's field (a clause of a sentence)."""
    from ogr_core.messages import as_nested
    return as_nested(note(code, **args))
