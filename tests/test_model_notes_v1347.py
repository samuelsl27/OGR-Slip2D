# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.347 (D335, first part) — the notes about the model and the project
rules carry stable codes, and the interface says them in Spanish.

``settings_warnings`` and its helper modules, the project rules
(``compute_blockers``, ``block_object_refusal``, the Block Search angles, the
orphan region) and the settings migrated from old files wrote English
sentences with their values baked in, and the Analysis Notes panel, the
status bar and the refusal boxes showed them in English. Each one is a code
now (``ogr_slip2d.note_messages``, ``ogr_core.project.messages``), carried by
a ``Coded`` string that IS the old sentence.

The invariants:

* **the English is v0.1.346's, byte for byte**: for every code, with a
  sample, the sentence equals the one v0.1.346 wrote with the same values --
  its old expression, taken from that version's source and evaluated, frozen
  below (``_V1346``); the ~32 test files that read these sentences are the
  rest of the guard;
* **a Coded note is its sentence**: equality, ``in``, JSON, pickle (the API's
  jobs come back from a subprocess); a concatenation drops the code, which
  is why notes are built with ``coded``; the singular is a template of its
  own;
* **every code says itself in Spanish**, with the template's fields, and
  differs from the English;
* **no sentence of these functions is built without its code** (AST census);
* **in the window, in Spanish**: the Analysis Notes panel and the status bar
  show a real run's notes translated; the Compute refusal and a Block Search
  object's refusal too;
* the API lists ``warning_codes`` beside the warnings when there are coded
  ones, and nothing when there are not.
"""
from __future__ import annotations

import ast
import json
import pickle
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``(code, args, the sentence v0.1.346 wrote with those values)``.
_V1346 = [('model.seismic_statistics',
  {},
  'A seismic analysis mode is on, so the critical surface is the one with '
  'the lowest critical seismic coefficient. The probabilistic and '
  'sensitivity statistics are taken on the factor of safety OF THAT SURFACE, '
  'which is not the lowest factor of safety of the sample.'),
 ('model.slope_search_limits',
  {},
  'Slope Search derives its entry and exit window from the ground profile, '
  'so the Slope Limits you set did not steer where it looked. They were '
  'still applied as a filter, as they are for every search.'),
 ('model.slope_limits_one_side',
  {},
  'The second set of Slope Limits has only one side set, so it describes no '
  'window and was ignored. Set both the left and the right limit, or clear '
  'them both.'),
 ('model.slope_limits_second_alone',
  {},
  'A second set of Slope Limits is defined but the first is automatic, and '
  'the second set is meant to be added to the first, not to replace it. It '
  'was ignored; set the first set as well.'),
 ('model.slope_limits_nested',
  {'inner_hi': 7.0, 'inner_lo': 2.5, 'outer_hi': 9.25, 'outer_lo': 1.0},
  'One set of Slope Limits, [2.5, 7], lies inside the other, [1, 9.25]. The '
  'two sets are the ranges where the ends of a surface may daylight, so the '
  'inner one admits no end the outer one does not: as a filter it does '
  'nothing.'),
 ('model.slope_limits_nested_path',
  {'inner_hi': 7.0, 'inner_lo': 2.5, 'outer_hi': 9.25, 'outer_lo': 1.0},
  'One set of Slope Limits, [2.5, 7], lies inside the other, [1, 9.25]. The '
  'two sets are the ranges where the ends of a surface may daylight, so the '
  'inner one admits no end the outer one does not: as a filter it does '
  'nothing. A Path Search still starts its surfaces in the set nearer the '
  'toe, so there it can change where they begin.'),
 ('model.max_iterations_floored',
  {'passes': 50, 'value': 30},
  'Maximum iterations is set to 30, and for Spencer and '
  'GLE/Morgenstern-Price that bounds the outer search for the inter-slice '
  'inclination alone. The fixed point those two methods solve inside every '
  'sample of that search keeps its own budget of 50 passes, which this '
  'setting raises only once it is above 50; at or below that the inner '
  'iteration is untouched. The methods that iterate on the factor of safety '
  'directly — Bishop and both Janbu — do take the value as written.'),
 ('model.max_iterations_raised',
  {'budget': 200, 'passes': 50, 'value': 200},
  'Maximum iterations is set to 200, so for Spencer and '
  'GLE/Morgenstern-Price it now bounds two loops and not one: the outer '
  'search for the inter-slice inclination, and the fixed point solved inside '
  'every sample of it, whose budget rises from 50 passes to 200. The extra '
  'room changes an answer only where a branch was being cut off while it was '
  'still converging, which takes a convergence tolerance far tighter than '
  'the default one.'),
 ('model.steffensen_nothing',
  {'methods': 'spencer, gle'},
  'Accelerate convergence (Steffensen) is on, and not one of the methods '
  'this run uses has an iteration it can accelerate, so the setting reached '
  'nothing and the results are the same as they would be with it off. The '
  'methods that ran are spencer, gle. Aitken extrapolation speeds up a fixed '
  'point on the factor of safety, and only Bishop simplified (on circular '
  'surfaces) and both Janbu solve one. Spencer and GLE/Morgenstern-Price '
  'solve for the factor and the inter-slice force together, and '
  'extrapolating the factor alone leaves the force behind. Lowe-Karafiath '
  'and Corps of Engineers #1 and #2 iterate on the factor but are not wired '
  'to it. Ordinary/Fellenius has no iteration at all.'),
 ('model.steffensen_nothing_bishop',
  {'methods': 'bishop_simplified, spencer'},
  'Accelerate convergence (Steffensen) is on, and not one of the methods '
  'this run uses has an iteration it can accelerate, so the setting reached '
  'nothing and the results are the same as they would be with it off. The '
  'methods that ran are bishop_simplified, spencer. Bishop simplified is in '
  'this run and does accelerate, but only on its circular branch, and this '
  'search returns polylines. Aitken extrapolation speeds up a fixed point on '
  'the factor of safety, and only Bishop simplified (on circular surfaces) '
  'and both Janbu solve one. Spencer and GLE/Morgenstern-Price solve for the '
  'factor and the inter-slice force together, and extrapolating the factor '
  'alone leaves the force behind. Lowe-Karafiath and Corps of Engineers #1 '
  'and #2 iterate on the factor but are not wired to it. Ordinary/Fellenius '
  'has no iteration at all.'),
 ('model.block_no_object',
  {'bands': 3},
  'No Block Search object is drawn, so the sampling region is chosen by the '
  'program and not by the model: a box over the slope face tiled into 3 '
  'vertical band(s) (Implicit Region Bands), one random vertex in each. The '
  'reference requires at least one Block Search object (window, line, point '
  'or polyline); draw one to search where the model says the slip surface '
  'can run.'),
 ('model.block_multiple_no_object',
  {},
  'Multiple Groups is on, but no Block Search object is drawn, so there are '
  'no Group IDs to split the search by: the setting does nothing here.'),
 ('model.block_bands_ignored',
  {'bands': 5, 'drawn': 1},
  'This model draws 1 Block Search object, so the trial surfaces are built '
  'from it and the Implicit Region Bands setting — 5 here — configures '
  'nothing. That count only divides the region OGR falls back to when no '
  'Block Search object is drawn.'),
 ('model.block_bands_ignored',
  {'bands': 5, 'drawn': 4},
  'This model draws 4 Block Search objects, so the trial surfaces are built '
  'from them and the Implicit Region Bands setting — 5 here — configures '
  'nothing. That count only divides the region OGR falls back to when no '
  'Block Search object is drawn.'),
 ('model.block_one_group',
  {'group_id': 7},
  'Multiple Groups is on, but every Block Search object has Group ID 7: that '
  'is one group, and the search is the same as with the setting off. Give '
  'the objects different Group IDs to search them separately.'),
 ('model.base_angle_no_ceiling',
  {'limit': 90.0, 'n': 1},
  'Maximum slice base angle is set to 90 deg, which does not raise the '
  'ceiling on the base of a slice — it removes it. This model draws 1 weak '
  'layer, and no surface a weak layer clips will be discarded for the '
  'steepness of its base, however close to vertical the drop at the end of a '
  'layer leaves it. Any value strictly between 0 and 90 applies the '
  'ceiling.'),
 ('model.base_angle_no_ceiling',
  {'limit': 90.0, 'n': 3},
  'Maximum slice base angle is set to 90 deg, which does not raise the '
  'ceiling on the base of a slice — it removes it. This model draws 3 weak '
  'layers, and no surface a weak layer clips will be discarded for the '
  'steepness of its base, however close to vertical the drop at the end of a '
  'layer leaves it. Any value strictly between 0 and 90 applies the '
  'ceiling.'),
 ('model.m_alpha_clause_off',
  {},
  'The m-alpha check is off, so nothing else caps how steeply a base may '
  'run.'),
 ('model.base_governs_none',
  {},
  'A surface no weak layer clips therefore has no ceiling on the inclination '
  'of its base at all in this run.'),
 ('model.m_alpha_clause_unscreened',
  {'methods': 'janbu_simplified, ordinary_fellenius'},
  'The m-alpha check is on, but no method in this run is screened by it '
  '(janbu_simplified, ordinary_fellenius), so it caps nothing here.'),
 ('model.m_alpha_clause_on',
  {'ceiling': 78.463,
   'm_alpha_limit': 0.2,
   'named': 'bishop_simplified, spencer'},
  'The m-alpha check is on, and where phi = 0 its 0.2 limit is a bare '
  'ceiling of 78.5 deg on every surface it screens (bishop_simplified, '
  'spencer).'),
 ('model.m_alpha_clause_on_partial',
  {'ceiling': 78.463,
   'm_alpha_limit': 0.2,
   'methods': 'janbu_simplified',
   'named': 'bishop_simplified, spencer'},
  'The m-alpha check is on, and where phi = 0 its 0.2 limit is a bare '
  'ceiling of 78.5 deg on every surface it screens (bishop_simplified, '
  'spencer). It does not screen janbu_simplified.'),
 ('model.base_governs_m_alpha',
  {'ceiling': 78.463, 'limit': 80.0},
  'On a weak-layer clip in purely cohesive material the 78.5 deg ceiling '
  'therefore governs, and the 80 deg set here never applies.'),
 ('model.base_governs_setting',
  {'ceiling': 78.463, 'limit': 45.0},
  'On a weak-layer clip the 45 deg set here is therefore the tighter of the '
  'two, and 78.5 deg governs everywhere else.'),
 ('model.base_angle_scope_weak',
  {'clause': {'args': {'ceiling': 78.463,
                       'm_alpha_limit': 0.2,
                       'named': 'bishop_simplified, spencer'},
              'code': 'model.m_alpha_clause_on',
              'text': 'The m-alpha check is on, and where phi = 0 its 0.2 '
                      'limit is a bare ceiling of 78.5 deg on every surface '
                      'it screens (bishop_simplified, spencer).'},
   'governs': {'args': {'ceiling': 78.463, 'limit': 80.0},
               'code': 'model.base_governs_m_alpha',
               'text': 'On a weak-layer clip in purely cohesive material the '
                       '78.5 deg ceiling therefore governs, and the 80 deg '
                       'set here never applies.'},
   'limit': 80.0,
   'n': 1},
  'This model draws 1 weak layer, so the Maximum base angle setting (80 deg) '
  'reaches the surfaces they clip and nothing else. The m-alpha check is on, '
  'and where phi = 0 its 0.2 limit is a bare ceiling of 78.5 deg on every '
  'surface it screens (bishop_simplified, spencer). On a weak-layer clip in '
  'purely cohesive material the 78.5 deg ceiling therefore governs, and the '
  '80 deg set here never applies.'),
 ('model.base_angle_scope_weak',
  {'clause': {'args': {'ceiling': 78.463,
                       'm_alpha_limit': 0.2,
                       'named': 'bishop_simplified, spencer'},
              'code': 'model.m_alpha_clause_on',
              'text': 'The m-alpha check is on, and where phi = 0 its 0.2 '
                      'limit is a bare ceiling of 78.5 deg on every surface '
                      'it screens (bishop_simplified, spencer).'},
   'governs': {'args': {'ceiling': 78.463, 'limit': 80.0},
               'code': 'model.base_governs_m_alpha',
               'text': 'On a weak-layer clip in purely cohesive material the '
                       '78.5 deg ceiling therefore governs, and the 80 deg '
                       'set here never applies.'},
   'limit': 80.0,
   'n': 2},
  'This model draws 2 weak layers, so the Maximum base angle setting (80 '
  'deg) reaches the surfaces they clip and nothing else. The m-alpha check '
  'is on, and where phi = 0 its 0.2 limit is a bare ceiling of 78.5 deg on '
  'every surface it screens (bishop_simplified, spencer). On a weak-layer '
  'clip in purely cohesive material the 78.5 deg ceiling therefore governs, '
  'and the 80 deg set here never applies.'),
 ('model.base_angle_scope_no_weak',
  {'clause': {'args': {},
              'code': 'model.m_alpha_clause_off',
              'text': 'The m-alpha check is off, so nothing else caps how '
                      'steeply a base may run.'},
   'limit': 60.0},
  'No weak layer is drawn in this model, so the Maximum base angle setting '
  '(60 deg) reached nothing: it applies only to surfaces a weak layer has '
  'clipped. The m-alpha check is off, so nothing else caps how steeply a '
  'base may run.'),
 ('model.focus_guided',
  {},
  'This search steers from one candidate surface to the next, so a focus '
  'object narrows the path it walks as well as the answer it returns. A '
  'narrow focus can leave it with NO surface at all even when surfaces '
  'satisfying the focus exist; that is a limit of the search, not a '
  'statement about the slope. A Grid, Path or Block Search reaches a tightly '
  'focused region more reliably.'),
 ('model.interslice_ponded',
  {},
  'This model has water standing over the ground, and the '
  'prescribed-inclination methods (Lowe-Karafiath, Corps of Engineers #1 and '
  '#2) are set to TOTAL inter-slice forces. That is the convention the '
  'published values of these methods are in, but it does not hold where '
  'water stands on the slope: the factor of safety then depends on the depth '
  'of the water, the force balance can fail to close, and it can also close '
  'on a root that is not a factor of safety at all — measured on a fully '
  'submerged slope, the search returned 0.20 where every other method gives '
  "1.61. Treat these three methods' numbers on this model as unreliable. Use "
  'buoyant unit weights with no water surface (Duncan and Wright 2005), or '
  'set Interslice forces = Effective in Project Settings.'),
 ('model.undrained_zero_above',
  {'name': 'Clay', 'y0': -9.8, 'y_max': 22.0, 'y_min': -20.0},
  "Material 'Clay': its undrained profile reaches zero at elevation -9.8, "
  'and the material extends above that (-20 to 22). The soil above it has no '
  'shear strength at all, so any surface that goes there has a factor of '
  'safety of zero. The Cutoff cannot bound this side of the line.'),
 ('model.undrained_zero_below',
  {'name': 'Clay', 'y0': -9.8, 'y_max': 22.0, 'y_min': -20.0},
  "Material 'Clay': its undrained profile reaches zero at elevation -9.8, "
  'and the material extends below that (-20 to 22). The soil below it has no '
  'shear strength at all, so any surface that goes there has a factor of '
  'safety of zero. The Cutoff cannot bound this side of the line.'),
 ('model.undrained_zero_depth',
  {'d0': 3.25, 'depth': 12.5, 'name': 'Silt'},
  "Material 'Silt': its undrained profile reaches zero 3.25 below its "
  'reference, and the material is 12.5 deep. Below that it has no shear '
  'strength and any surface reaching it has a factor of safety of zero.'),
 ('model.surface_type_mismatch',
  {'search_method': 'grid', 'surface_type': 'non_circular'},
  "The Surface Type is set to 'non_circular' and the Search Method to "
  "'grid', which does not search for that kind of surface. The method is "
  'what runs, so the surfaces this analysis returns are the ones it '
  'generates, whatever the Surface Type says.'),
 ('model.auto_refine_vertices',
  {'n_slices': 25, 'n_vert': 40, 'segments': 39},
  'The search converts each circle into 40 vertices, which is 39 straight '
  'segments, and the analysis uses 25 slices. Every vertex is a mandatory '
  'slice boundary, so a surface with more segments than slices is refused '
  'whole: this run would return no surfaces at all. Raise the number of '
  'slices to at least 39, or lower the vertices.'),
 ('model.pso_minima_unoptimised',
  {},
  'The Particle Swarm search is reporting several minima with Optimize '
  'Surfaces OFF. It is then looking for LOCAL minima, and the lowest of them '
  'need not be the global minimum of the slope.'),
 ('model.optimize_not_applicable',
  {'search_method': 'grid'},
  'Optimize Surfaces applies to non-circular surfaces, which are the ones '
  "with vertices to move; this project searches with 'grid'. The setting was "
  'ignored.'),
 ('model.optimize_all_walk',
  {},
  'Optimize Surfaces is set to optimise ALL surfaces, so the random walk '
  'runs once per surface the search generates rather than once on the '
  'critical one. The answer is the same kind of answer; the run takes far '
  'longer.'),
 ('model.optimize_all_alteration',
  {},
  'Optimize Surfaces is set to optimise ALL surfaces, so the alteration runs '
  'once per surface the search generates rather than once on the critical '
  'one. The answer is the same kind of answer; the run takes far longer.'),
 ('model.surface_altering_ignores',
  {},
  'Surface Altering does not read Step Reduction Factor or Explore All '
  'Vertices: they configure the Monte Carlo technique, and were ignored.'),
 ('model.failure_direction_r2l',
  {'y_left': 30.0, 'y_right': 10.0},
  'The Failure Direction is set to Right to Left, which puts the crest on '
  'the right, but the ground surface is higher on the left (y = 30 at the '
  'left end against y = 10 at the right end). Tension-crack water thrust, '
  'support force direction and the Path Search starting face all read this '
  'setting.'),
 ('model.failure_direction_l2r',
  {'y_left': 10.0, 'y_right': 30.5},
  'The Failure Direction is set to Left to Right, which puts the crest on '
  'the left, but the ground surface is higher on the right (y = 10 at the '
  'left end against y = 30.5 at the right end). Tension-crack water thrust, '
  'support force direction and the Path Search starting face all read this '
  'setting.'),
 ('model.weak_layer_no_material',
  {'name': 'ab12cd34'},
  'Weak layer ab12cd34 has no material assigned, so it carries no strength '
  'of its own and would only change the geometry of the surfaces it clips. '
  'Assign it a material or suppress it.'),
 ('model.weak_layer_above_ground',
  {'name': 'ab12cd34'},
  'Weak layer ab12cd34 lies entirely above the ground surface, so any '
  'surface it clips is pushed out of the soil and discarded. Suppress it or '
  'move it into the model.'),
 ('model.walls_horizontal',
  {'n': 1},
  "1 retaining wall is drawn horizontally. A wall's pressure profile is "
  'defined from the crest downwards and a horizontal wall has no crest, so '
  'it is excluded from the analysis rather than analysed with a profile that '
  'would depend on which end was drawn first.'),
 ('model.walls_horizontal',
  {'n': 2},
  "2 retaining walls are drawn horizontally. A wall's pressure profile is "
  'defined from the crest downwards and a horizontal wall has no crest, so '
  'it is excluded from the analysis rather than analysed with a profile that '
  'would depend on which end was drawn first.'),
 ('model.piles_touch',
  {'diameter': 0.8, 'spacing': 0.75},
  'The pile diameter (0.8) is not smaller than the out-of-plane spacing '
  '(0.75), so there is no opening between piles. Ito and Matsui (1975) '
  'describe soil squeezing THROUGH that opening and their equation diverges '
  'when it closes, so the row applies no force at all. A continuous barrier '
  'is a wall, not a pile row.'),
 ('model.piles_leaning',
  {'n': 1, 'tilt': 12.25, 'tolerance': 5.0},
  '1 pile is more than 5° off vertical (up to 12.2°). Ito and Matsui (1975) '
  'derive the pressure for a vertical row, so the force is integrated ALONG '
  'THE SHAFT rather than over depth. The theory does not say which is right, '
  'and projecting one onto the other here would be this program deciding.'),
 ('model.piles_leaning',
  {'n': 3, 'tilt': 12.25, 'tolerance': 5.0},
  '3 piles are more than 5° off vertical (up to 12.2°). Ito and Matsui '
  '(1975) derive the pressure for a vertical row, so the force is integrated '
  'ALONG THE SHAFT rather than over depth. The theory does not say which is '
  'right, and projecting one onto the other here would be this program '
  'deciding.'),
 ('model.piles_unchecked_water',
  {'detail': 'bad axis', 'error': 'ValueError'},
  'It could not be checked whether there is pore pressure along an '
  'Ito-Matsui pile (ValueError: bad axis).'),
 ('model.piles_unchecked_negative',
  {'detail': 'float division by zero', 'error': 'ZeroDivisionError'},
  'It could not be checked whether the Ito-Matsui pressure goes negative '
  'near the surface (ZeroDivisionError: float division by zero).'),
 ('model.piles_water',
  {},
  'There is pore pressure along an Ito-Matsui pile. The published equation '
  'is written on the total overburden because there is no water anywhere in '
  'the paper it comes from; with effective strength parameters this program '
  'feeds it the EFFECTIVE vertical stress, which is the consistent reading '
  'and the conservative one. The theory itself is silent.'),
 ('model.piles_negative',
  {},
  'The Ito-Matsui pressure comes out negative over part of the pile, near '
  'the surface, where the cohesion terms outweigh the overburden: the theory '
  'is saying no plastic pressure develops there. It is integrated as '
  'published, so that stretch reduces the total instead of being quietly set '
  'to zero.'),
 ('model.helical_no_plate',
  {'name': 'H1'},
  "The shaft of support 'H1' is not narrower than its helices, so the plates "
  'have no bearing area and the anchor carries nothing in pullout.'),
 ('model.helical_respaced',
  {'n': 3, 'name': 'H1', 'spacing': 0.9, 'used': 0.825},
  "The 3 helices of support 'H1' do not fit at 0.90 m: the spacing used is "
  '0.82 m, the anchor length divided by the number of gaps.'),
 ('model.helical_spacing_ratio',
  {'name': 'H1', 'ratio': 3.4567},
  "The helix spacing of support 'H1' is 3.46 times the average helix "
  'diameter. Design guides recommend 5 to 12.'),
 ('model.support_ambiguous_set',
  {'cls': 'Grouted Tieback',
   'first': 'Tie A',
   'n': 1,
   'n_sets': 2,
   'sets': "'Tie A', 'Tie B'"},
  "1 support of class 'Grouted Tieback' name no property set and the project "
  "defines 2 sets of that class ('Tie A', 'Tie B'). The first, 'Tie A', is "
  'used. Assign each support its set in Support Properties if that is not '
  'the one meant.'),
 ('model.support_ambiguous_set',
  {'cls': 'Grouted Tieback',
   'first': 'Tie A',
   'n': 2,
   'n_sets': 2,
   'sets': "'Tie A', 'Tie B'"},
  "2 supports of class 'Grouted Tieback' name no property set and the "
  "project defines 2 sets of that class ('Tie A', 'Tie B'). The first, 'Tie "
  "A', is used. Assign each support its set in Support Properties if that is "
  'not the one meant.'),
 ('model.support_orphan_replaced',
  {'name': 'S7', 'used': 'Tie A'},
  "Support 'S7' refers to a property set that is no longer in the project; "
  "'Tie A' is used instead, chosen by class."),
 ('model.support_orphan_dropped',
  {'name': 'S8'},
  "Support 'S8' refers to a property set that is no longer in the project; "
  'it is left out of the analysis.'),
 ('model.support_infinite_length',
  {'hit_plates': 2,
   'materials': "'Rock'",
   'n_plates': 3,
   'name': 'N1',
   'percent': 35.0,
   'type_name': 'Tie A'},
  "Support 'N1' (Tie A) has about 35 % of its length in 'Rock', whose "
  'strength is not finite (Infinite Strength): the soil around it is read as '
  'zero there. Rigid bedrock is a modelling device, not a promise that a '
  'support cannot be pulled out of it, and letting the infinity through '
  'would drop its pull-out or bearing from the minimum.'),
 ('model.support_infinite_plates',
  {'hit_plates': 2,
   'materials': "'Rock'",
   'n_plates': 3,
   'name': 'N1',
   'percent': 35.0,
   'type_name': 'Tie A'},
  "Support 'N1' (Tie A) has 2 of its 3 plates in 'Rock', whose strength is "
  'not finite (Infinite Strength): the soil around it is read as zero there. '
  'Rigid bedrock is a modelling device, not a promise that a support cannot '
  'be pulled out of it, and letting the infinity through would drop its '
  'pull-out or bearing from the minimum.'),
 ('model.support_infinite_both',
  {'hit_plates': 2,
   'materials': "'Rock'",
   'n_plates': 3,
   'name': 'N1',
   'percent': 35.0,
   'type_name': 'Tie A'},
  "Support 'N1' (Tie A) has about 35 % of its length and 2 of its 3 plates "
  "in 'Rock', whose strength is not finite (Infinite Strength): the soil "
  'around it is read as zero there. Rigid bedrock is a modelling device, not '
  'a promise that a support cannot be pulled out of it, and letting the '
  'infinity through would drop its pull-out or bearing from the minimum.'),
 ('model.force_at_centroid_blind',
  {'methods': 'janbu_simplified, lowe_karafiath'},
  'The support force is set to act at the centroid of its pressure diagram, '
  'and janbu_simplified, lowe_karafiath cannot tell that from acting at the '
  'slip surface: moving a force leaves a couple, and a couple has nowhere to '
  'go in a method that writes force equilibrium alone. The four methods with '
  'a moment equation — Ordinary, Bishop, Spencer and GLE — do honour it.'),
 ('model.force_at_centroid',
  {},
  'The support force is set to act at the centroid of its pressure diagram. '
  'Only the four methods with a moment equation — Ordinary, Bishop, Spencer '
  'and GLE — can tell that apart from acting at the slip surface.'),
 ('rule.no_boundaries',
  {},
  'No model to compute. Add an external boundary first.'),
 ('rule.no_materials', {}, 'No materials defined.'),
 ('rule.block_object_empty',
  {},
  'A Block Search object needs at least one vertex.'),
 ('rule.block_point_vertices',
  {'n': 3},
  'A Block Search Point is a single point; this one has 3 vertices.'),
 ('rule.block_line_vertices',
  {'n': 4},
  'A Block Search Line is one segment given by two points; this one has 4 '
  'vertices. A path of several segments that the surface should follow is a '
  'Block Search Polyline.'),
 ('rule.block_window_open',
  {},
  'A Block Search Window is a closed polygon of at least three vertices.'),
 ('rule.block_polyline_shape',
  {},
  'A Block Search Polyline is an open line of at least two vertices.'),
 ('rule.block_polyline_not_monotone',
  {},
  'A Block Search Polyline has to advance in x from one end to the other: '
  'the trial surface follows it between its two points, and a polyline that '
  'doubles back (or has a vertical segment) would give a surface that '
  'reverses direction.'),
 ('rule.block_polyline_segment_mode',
  {},
  'The Left / Right Line Segment option places its point on the end segment '
  'of that side, which needs a polyline of at least two segments; this one '
  'has one. Use Any Line Segment or End Point.'),
 ('rule.block_angle_reread_left',
  {'end': 100.0, 'hi': 170.0, 'lo': 100.0, 'start': 170.0},
  'The left projection angles are written from 170° to 100°, and the '
  'reference measures them counter-clockwise from the positive x axis with '
  'the Start Angle less than the End Angle. They were read as 100° to 170°: '
  'the arc between the two that avoids 0°, a direction no left projection '
  'can take.'),
 ('rule.block_angle_reread_right',
  {'end': 100.0, 'hi': 170.0, 'lo': 100.0, 'start': 170.0},
  'The right projection angles are written from 170° to 100°, and the '
  'reference measures them counter-clockwise from the positive x axis with '
  'the Start Angle less than the End Angle. They were read as 100° to 170°: '
  'the arc between the two that avoids 180°, a direction no right projection '
  'can take.'),
 ('rule.block_angle_out_left_left_facing',
  {'hi': 190.5, 'limit_hi': 180.0, 'limit_lo': 90.0, 'lo': 100.0},
  'The left projection angles, 100° to 190.5°, go outside 90° to 180°, the '
  'range the reference gives for kinematically valid surfaces on a '
  'left-facing slope. The search uses them as given; a projection that '
  'cannot reach the ground leaves its surface invalid.'),
 ('rule.block_angle_out_left_right_facing',
  {'hi': 190.5, 'limit_hi': 180.0, 'limit_lo': 90.0, 'lo': 100.0},
  'The left projection angles, 100° to 190.5°, go outside 90° to 180°, the '
  'range the reference gives for kinematically valid surfaces on a '
  'right-facing slope. The search uses them as given; a projection that '
  'cannot reach the ground leaves its surface invalid.'),
 ('rule.block_angle_out_right_left_facing',
  {'hi': 190.5, 'limit_hi': 180.0, 'limit_lo': 90.0, 'lo': 100.0},
  'The right projection angles, 100° to 190.5°, go outside 90° to 180°, the '
  'range the reference gives for kinematically valid surfaces on a '
  'left-facing slope. The search uses them as given; a projection that '
  'cannot reach the ground leaves its surface invalid.'),
 ('rule.block_angle_out_right_right_facing',
  {'hi': 190.5, 'limit_hi': 180.0, 'limit_lo': 90.0, 'lo': 100.0},
  'The right projection angles, 100° to 190.5°, go outside 90° to 180°, the '
  'range the reference gives for kinematically valid surfaces on a '
  'right-facing slope. The search uses them as given; a projection that '
  'cannot reach the ground leaves its surface invalid.'),
 ('rule.orphan_region',
  {'x': 12.345, 'y': -3.0},
  'The region at (12.35, -3.00) is assigned a material that no longer '
  'exists. Assign it another material (Properties > Assign Materials); a '
  'surface through it cannot be analysed.'),
 ('rule.migration_cooling',
  {'old': 0.95,
   'shadow': 'sa_temperature_factor',
   'survivor': 'sa_cooling_coefficient'},
  'This model carries sa_temperature_factor = 0.95, removed in v0.1.103: it '
  'held a geometric cooling rate that no analysis ever read; the coefficient '
  'the schedule does use is sa_cooling_coefficient. The stored value was NOT '
  'converted.'),
 ('rule.migration_frame',
  {'old': 0.95,
   'shadow': 'path_initial_angle_at_toe_lower',
   'survivor': 'sa_cooling_coefficient'},
  'This model carries path_initial_angle_at_toe_lower = 0.95, removed in '
  "v0.1.103: it held an angle in the search's own toe-to-crest frame and the "
  'field replacing it is absolute, so converting it needs the failure '
  'direction, which is not part of this block. The field to set is '
  'sa_cooling_coefficient. The stored value was NOT converted.'),
 ('rule.migration_toe_angle_lower',
  {'angle': 35.0},
  'This model was saved before v0.1.103, and its Path Search lower Initial '
  "Angle at Toe is ON at 35.0°. That number was read in the search's own "
  'toe-to-crest frame then and is read as ABSOLUTE now — counter-clockwise '
  'from the +x axis — so it does not describe the same limit. It was NOT '
  'converted: doing so needs the failure direction, which is not part of '
  'this block. Check path_initial_angle_at_toe_lower_deg before trusting '
  'this run.'),
 ('rule.migration_toe_angle_upper',
  {'angle': 35.0},
  'This model was saved before v0.1.103, and its Path Search upper Initial '
  "Angle at Toe is ON at 35.0°. That number was read in the search's own "
  'toe-to-crest frame then and is read as ABSOLUTE now — counter-clockwise '
  'from the +x axis — so it does not describe the same limit. It was NOT '
  'converted: doing so needs the failure direction, which is not part of '
  'this block. Check path_initial_angle_at_toe_upper_deg before trusting '
  'this run.'),
 ('rule.migration_path_optimize',
  {},
  'This model carries path_optimize = True, removed in v0.1.104. Path Search '
  'used to optimise its best surfaces whether or not anything asked it to, '
  'because that field defaulted to True and the interface never showed it. '
  'The optimisation is now the Optimize Surfaces checkbox, which is UNTICKED '
  'here, so this run does not optimise. Tick it to get the old behaviour.')]


def _catalogue():
    from ogr_core.messages import CORE_MESSAGES
    from ogr_core.project.messages import RULES
    from ogr_slip2d.note_messages import NOTES
    return {**CORE_MESSAGES, **NOTES, **RULES}


def _fields(t):
    return sorted({f for _t, f, _s, _c in string.Formatter().parse(t) if f})


# ======================================================================
class TestTheEnglishIsTheOldOne:

    def test_every_code_with_its_sample(self):
        from ogr_core.messages import english
        cat = _catalogue()
        for code, args, old in _V1346:
            assert english(cat, code, args) == old, code

    def test_the_samples_cover_every_code_and_both_numbers(self):
        from ogr_core.project.messages import RULES
        from ogr_slip2d.note_messages import NOTES
        codes = set(NOTES) | set(RULES)
        assert {c for c, _a, _e in _V1346} == codes
        for code, spec in {**NOTES, **RULES}.items():
            if spec.one:
                counts = {a.get(spec.count) for c, a, _e in _V1346
                          if c == code}
                assert 1 in counts and len(counts) > 1, code


# ======================================================================
class TestACodedNoteIsItsSentence:

    def test_equality_json_pickle_and_the_singular(self):
        from ogr_core.messages import Coded, method_note
        from ogr_slip2d.note_messages import WALLS_HORIZONTAL, note
        one, two = note(WALLS_HORIZONTAL, n=1), note(WALLS_HORIZONTAL, n=2)
        assert isinstance(one, Coded) and isinstance(one, str)
        assert one.startswith("1 retaining wall is drawn horizontally.")
        assert two.startswith("2 retaining walls are drawn horizontally.")
        assert one == str(one) and one in [str(one)]
        assert json.loads(json.dumps([one])) == [str(one)]
        back = pickle.loads(pickle.dumps(two))
        assert back == two and back.code == WALLS_HORIZONTAL
        assert back.args == {"n": 2}
        joined = "x: " + one
        assert not hasattr(joined, "code")
        m = method_note("spencer", one)
        assert m == "spencer: " + one and m.code == "note.method"
        assert m.args["note"]["code"] == WALLS_HORIZONTAL


# ======================================================================
class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for code, spec in _catalogue().items():
            if code in ("join", "note.method"):
                continue
            for en in [spec.english] + ([spec.one] if spec.one else []):
                assert en in es, (code, en[:60])
                assert _fields(es[en]) == _fields(en), code
                assert es[en] != en, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_core.messages import render
        from ogr_gui.i18n import tr
        cat = _catalogue()
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            for code, args, old in _V1346:
                said = render(cat, code, args, old, translate=tr)
                assert said and said != old, code
        finally:
            set_language(before)


# ======================================================================
#: The functions whose notes are coded in this version.
_CODED = {
    "ogr_slip2d/analysis_runner.py": (
        "settings_warnings", "_max_iterations_scope_notes",
        "_steffensen_scope_notes", "_block_group_notes",
        "_base_angle_ceiling_notes", "_base_angle_scope_notes",
        "_optimize_notes", "_undrained_profile_notes", "_focus_notes",
        "_interslice_convention_notes", "_failure_direction_note",
        "_surface_type_notes", "_auto_refine_vertex_notes"),
    "ogr_slip2d/weak_layers.py": ("weak_layer_model_warnings",),
    "ogr_slip2d/retaining_wall_notes.py": ("retaining_wall_notes",),
    "ogr_slip2d/ito_matsui_notes.py": ("ito_matsui_notes",),
    "ogr_slip2d/helical_anchor_notes.py": ("helical_anchor_notes",),
    "ogr_slip2d/support_notes.py": (
        "support_identity_notes", "infinite_strength_notes",
        "force_location_notes"),
    "ogr_core/project/rules.py": (
        "compute_blockers", "block_object_refusal", "block_angle_notes",
        "orphan_assignment_messages"),
}
#: The formats left, all of them DATA and the same in every language: a
#: name in quotes, and the name of an attribute.
_DATA = {
    ("support_identity_notes", '"\'%s\'" % _name(st)'),
    ("infinite_strength_notes", '"\'%s\'" % n'),
    ("block_angle_notes", 'f"block_{side}_start_angle_deg"'),
    ("block_angle_notes", 'f"block_{side}_end_angle_deg"'),
}


class TestNoSentenceWithoutItsCode:

    def test_census(self):
        found = []
        for rel, names in _CODED.items():
            src = (_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            funcs = {n.name: n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef)}
            for name in names:
                fn = funcs[name]
                doc = (fn.body[0].value if isinstance(fn.body[0], ast.Expr)
                       else None)
                inner = set()
                for n in ast.walk(fn):
                    if n is doc or n in inner:
                        continue
                    if (name, ast.get_source_segment(src, n)) in _DATA:
                        inner.update(ast.walk(n))
                        continue
                    if isinstance(n, ast.JoinedStr):
                        found.append((rel, name, n.lineno, "f-string"))
                    elif (isinstance(n, ast.BinOp)
                          and isinstance(n.op, ast.Mod)
                          and isinstance(n.left, ast.Constant)
                          and isinstance(n.left.value, str)):
                        found.append((rel, name, n.lineno, "% format"))
                    elif (isinstance(n, ast.Constant)
                          and isinstance(n.value, str)
                          and len(n.value) > 40):
                        found.append((rel, name, n.lineno, "sentence"))
        assert not found, found


# ======================================================================
def _project(**settings):
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Notes")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 3.0,
                                                   "friction_angle": 19.6}}}],
            "settings": dict(settings)})
        return ws.get(pid).project
    finally:
        ws.shutdown()


def _block_project():
    """A Block Search with no object drawn and the crest declared on the
    wrong side: two model notes, each with its code."""
    return _project(**{"search.surface_type": "non_circular",
                       "search.search_method": "block",
                       "units.failure_direction": "L2R"})


def _wrong_crest_project():
    """A small circular grid, with the crest declared on the left of a
    slope that rises to the right: the run says so in a model note."""
    return _project(**{"units.failure_direction": "L2R",
                       "search.grid_nx": 2, "search.grid_ny": 2,
                       "search.radius_increment": 2})


#: That note in Spanish, with this slope's values.
_WRONG_CREST_ES = (
    "La dirección de rotura es de izquierda a derecha, lo que pone la "
    "coronación a la izquierda, pero el terreno está más alto a la derecha "
    "(y = 25 en el extremo izquierdo frente a y = 35 en el derecho).")


class TestARealRunsNotes:

    def test_they_carry_their_codes(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        notes = settings_warnings(_block_project(), ["bishop_simplified"])
        codes = {getattr(n, "code", "") for n in notes}
        assert "model.block_no_object" in codes, notes
        assert "model.failure_direction_l2r" in codes, notes

    def test_and_keep_them_through_the_run(self):
        from ogr_slip2d.analysis_runner import run_analysis
        outcome = run_analysis(_wrong_crest_project(), ["bishop_simplified"])
        codes = [getattr(n, "code", "") for n in outcome.warnings]
        assert "model.failure_direction_l2r" in codes, outcome.warnings


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


class TestTheWindowSaysThemInSpanish:

    def test_a_computed_run_in_the_status_bar_the_panel_and_copy_all(self):
        """Through the real completion path: the worker the Compute button
        starts, ``_on_compute_done`` and Analysis > Analysis Notes."""
        from PySide6.QtWidgets import QApplication

        from ogr_gui.core_messages import note_line
        from ogr_gui.main_window import _ComputeWorker
        from test_f2_rules_v1196 import _window
        _app()
        w = _window(_wrong_crest_project())
        errors: list = []
        w.worker = _ComputeWorker(w.project, ["bishop_simplified"])
        w.worker.failed.connect(errors.append)
        w.worker.run()
        assert not errors, errors
        copied = []

        class _Clip:
            @staticmethod
            def setText(text):  # noqa: N802 - Qt's name
                copied.append(text)

        saved = QApplication.clipboard
        panel = None
        # Every message the bar is given: the caption with the factor of
        # safety replaces the note a moment later (v0.1.165, D96 -- the bar
        # holds one), so what the bar shows at the end is not the note.
        shown = []
        show = w.ogr_status.showMessage
        w.ogr_status.showMessage = lambda text, *a: (shown.append(text),
                                                     show(text, *a))
        try:
            with _Spanish():
                w._on_compute_done(w.worker.results)
                w.act_analysis_notes()
                panel = w._analysis_notes_panel
                lines = [panel.tree.topLevelItem(i).child(j).text(0)
                         for i in range(panel.tree.topLevelItemCount())
                         for j in range(
                             panel.tree.topLevelItem(i).childCount())]
                QApplication.clipboard = staticmethod(lambda: _Clip)
                panel._copy_all()
                first = note_line(w.last_compute_warnings[0])
        finally:
            QApplication.clipboard = saved
            del w.ogr_status.showMessage
            if panel is not None:
                panel.close()
        assert any(s.startswith(_WRONG_CREST_ES) for s in lines), lines
        assert not any(s.startswith("The Failure Direction") for s in lines)
        assert shown and shown[0].startswith(first), (shown, first)
        assert first != str(w.last_compute_warnings[0])
        assert copied and _WRONG_CREST_ES in copied[0], copied
        assert "The Failure Direction" not in copied[0]

    def test_the_notes_of_a_block_search_in_the_panel(self):
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        from ogr_slip2d.analysis_runner import settings_warnings
        _app()
        notes = settings_warnings(_block_project(), ["bishop_simplified"])
        with _Spanish():
            panel = AnalysisNotesPanel(notes)
            top = panel.tree.topLevelItem(0)
            shown = [top.child(i).text(0) for i in range(top.childCount())]
            assert top.text(0).startswith("Modelo")
            assert any(s.startswith("No hay ningún objeto de búsqueda por "
                                    "bloques dibujado") for s in shown), shown
            assert not any(s.startswith("No Block Search object") for s in
                           shown)
            from ogr_gui.core_messages import note_line
            assert [note_line(n) for n in notes] == shown

    def test_a_note_about_one_method_goes_under_its_name(self):
        """The panel files through ``_split``, which three older tests call
        "the panel's REAL splitter": it has to stay the one door."""
        from ogr_core.messages import method_note
        from ogr_gui.dialogs.analysis_notes_panel import (AnalysisNotesPanel,
                                                          _split)
        from ogr_gui.labels import method_name
        from ogr_slip2d.note_messages import WALLS_HORIZONTAL, note
        _app()
        n = method_note("bishop_simplified", note(WALLS_HORIZONTAL, n=2))
        assert n == ("bishop_simplified: 2 retaining walls are drawn "
                     "horizontally." + n.split("horizontally.", 1)[1])
        with _Spanish():
            group, sentence = _split(n)
            assert group == method_name("bishop_simplified")
            assert group == "Bishop simplificado"
            assert sentence.startswith("2 muros de contención están "
                                       "dibujados horizontales."), sentence
            panel = AnalysisNotesPanel([n])
            top = panel.tree.topLevelItem(0)
            assert top.text(0) == "Bishop simplificado (1)"
            assert top.child(0).text(0) == sentence
        # an uncoded note keeps the old rule: the identifier is the group
        assert _split("spencer: did a thing.") == ("spencer", "did a thing.")
        assert _split("A sentence: with a colon.")[0] == "Model"

    def test_the_compute_refusal(self):
        import ogr_gui.main_window as mw
        from ogr_core.project import Project
        from test_f2_rules_v1196 import _window
        _app()
        said = []

        class _Box:
            @staticmethod
            def warning(*a, **_k):
                said.append(a[2])

            information = critical = warning

        saved = mw.QMessageBox
        mw.QMessageBox = _Box
        try:
            with _Spanish():
                w = _window(Project())
                w.act_compute()
        finally:
            mw.QMessageBox = saved
        assert said == ["No hay modelo que calcular. Añade primero un "
                        "contorno exterior."], said

    def test_a_block_object_refusal_in_the_status_bar(self):
        from ogr_core.geometry import (BlockObjectKind, BlockObjectSpec,
                                       Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.project import Project
        from test_f2_rules_v1196 import _window
        _app()
        w = _window(Project())
        obj = Boundary(polyline=Polyline(vertices=[
            Vertex(10, 5), Vertex(20, 6), Vertex(30, 6.5)]),
            btype=BoundaryType.BLOCK_SEARCH_OBJECT,
            block_object=BlockObjectSpec(BlockObjectKind.POLYLINE))
        w.project.boundaries.append(obj)
        with _Spanish():
            stored = w.apply_block_object_spec(
                obj.id, BlockObjectSpec(BlockObjectKind.LINE))
            shown = w.ogr_status.currentMessage()
        assert not stored
        assert shown.startswith("Una línea de búsqueda por bloques es un "
                                "segmento dado por dos puntos; esta tiene 3 "
                                "vértices."), shown


# ======================================================================
class TestTheApiListsTheCodes:

    def test_beside_the_warnings_and_only_when_there_are(self):
        from ogr_api.results import with_warning_codes
        from ogr_slip2d.note_messages import FOCUS_GUIDED, note
        coded = with_warning_codes({"warnings": ["plain", note(FOCUS_GUIDED)]})
        assert coded["warning_codes"] == [
            {"index": 1, "code": FOCUS_GUIDED, "args": {}}]
        plain = with_warning_codes({"warnings": ["plain"]})
        assert "warning_codes" not in plain
        json.dumps(coded)

    def test_the_warnings_view_of_a_result_keeps_them(self):
        from ogr_api import Workspace, call
        from ogr_api.results import with_warning_codes
        from ogr_api.snapshot import model_hash
        from ogr_slip2d.note_messages import FOCUS_GUIDED, note
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="W")["project_id"]
            handle = ws.get(pid)
            res = ws.store_result(
                handle, "surface",
                with_warning_codes({"warnings": [note(FOCUS_GUIDED)]}),
                model_hash=model_hash(handle.project), payload={})
            out = call(ws, "results_get", result_id=res.id,
                       view="warnings")
        finally:
            ws.shutdown()
        assert out["warnings"] == [str(note(FOCUS_GUIDED))]
        assert [c["code"] for c in out["warning_codes"]] == [FOCUS_GUIDED]

    def test_through_the_settings_operation(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="V")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[20, 20], [70, 20], [70, 35], [50, 35],
                             [30, 25], [20, 25]],
                "materials": [{"name": "Soil", "unit_weight": 20.0,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {"cohesion": 3.0,
                                                       "friction_angle": 19.6}}}],
                "settings": {"search.surface_type": "non_circular",
                             "search.search_method": "block"}})
            out = call(ws, "settings_get", project_id=pid)
        finally:
            ws.shutdown()
        codes = [c["code"] for c in out.get("warning_codes", [])]
        assert "model.block_no_object" in codes, out
