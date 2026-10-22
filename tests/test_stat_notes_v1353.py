# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.353 (D335, seventh part) — what the statistical runs, the design
standard and the strength models' factoring say carries stable codes, and
the window says it in Spanish.

The probabilistic analysis (Global Minimum, Overall Slope) and the
sensitivity sweep refuse, lose methods, count why samples failed and say
what the samples answered for; the design standard says what it did to the
copy an analysis computes on, and each strength model what it could not
factor. They were English sentences with their values baked in, joined with
"; " into headlines and prefixed with the method id by hand, and the status
bar, the notes panel and the Statistics window showed them as they came
("they arrive in English and stay in English"). Each is a code now
(``ogr_slip2d.stat_messages``, ``ogr_core.project.design_messages``, the
``factoring.*`` of ``ogr_core.materials.messages``); a joined headline is a
list of its sentences, a line about one method is ``method_note``, a switch
sentence nests its head and its stretches, and a counted cause is a label
with its own code.

The invariants:

* **the English is v0.1.352's, byte for byte** (``_V1352``: that version's
  expressions and definitions, read from its source and run on the inputs
  below);
* every code is sampled and says itself in Spanish with its fields;
* **no sentence of these functions is built without its code** (AST
  census; the keys of a dictionary of changes are data);
* **in the window, in Spanish**: a real partial run (one method refused, one
  sampled) in the notes panel's line, in the status bar's headline and in
  the Statistics window; a run with no random variable; the lines a design
  standard adds, deterministic and statistical;
* the API and the command line still read English.
"""
from __future__ import annotations

import ast
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``{cat, code, args, english}``: the sentence v0.1.352 wrote. ``cat`` is
#: the catalogue (``strength`` only for the nested labels of a Generalized
#: Anisotropic child); a nested value is ``{"$code", "$cat", "$args"}``, an
#: uncoded one ``{"$raw": text}``.
_V1352 = [{'cat': 'stat',
  'code': 'stat.enable_statistics',
  'english': 'Enable a probabilistic or sensitivity analysis in Project '
             'Settings first.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.define_variable',
  'english': 'Define at least one random variable first.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_deterministic_critical',
  'english': 'The deterministic analysis produced no critical surface. Check '
             'the model and the search settings.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.factored_copy',
  'english': 'The project handed to this statistical run is the '
             'design-factored copy an analysis computes on, not the model: '
             'its samples would overwrite factored values with unfactored '
             'ones and be factored a second time. Pass the model itself; '
             'every sample is prepared like the analysis.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_variables',
  'english': 'No random variables defined. At least one model input parameter '
             'must be given a statistical distribution.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_variables',
  'english': 'No random variables defined. At least one model input parameter '
             'must be given a statistical distribution.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_deterministic_result',
  'english': 'No deterministic result: run the regular analysis first so the '
             'global minimum surface is known.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_deterministic_result',
  'english': 'No deterministic result: run the regular analysis first so the '
             'global minimum surface is known.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_method_selected',
  'english': 'No analysis method selected.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_range',
  'english': 'No variable has a range: enter a relative minimum and maximum '
             'for at least one parameter.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.vars_none',
  'english': 'none of the 3 random variables matches the model: '
             'material:a1:cohesion, seismic:kh',
  'args': {'n': 3, 'keys': 'material:a1:cohesion, seismic:kh'}},
 {'cat': 'stat',
  'code': 'stat.vars_none',
  'english': 'none of the 2 random variables matches the model: '
             'load:q1:magnitude',
  'args': {'n': 2, 'keys': 'load:q1:magnitude'}},
 {'cat': 'stat',
  'code': 'stat.vars_not_sampled',
  'english': '1 of the 3 random variables no longer match the model and were '
             'not sampled: seismic:kh',
  'args': {'n': 1, 'total': 3, 'keys': 'seismic:kh'}},
 {'cat': 'stat',
  'code': 'stat.vars_not_swept',
  'english': '2 of the 3 random variables no longer match the model and were '
             'not swept: seismic:kh, x',
  'args': {'n': 2, 'total': 3, 'keys': 'seismic:kh, x'}},
 {'cat': 'stat',
  'code': 'stat.var_orphan',
  'english': 'no longer matches the model: material:a1:cohesion',
  'args': {'key': 'material:a1:cohesion'}},
 {'cat': 'stat',
  'code': 'stat.no_method',
  'english': 'not a registered analysis method, so it was not computed.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_deterministic',
  'english': 'the deterministic run left no critical surface for this method, '
             'so there is nothing to re-evaluate.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_surface',
  'english': 'The deterministic result carries no serialised surface, so '
             'there is nothing to re-evaluate.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.weak_composite_off',
  'english': 'The deterministic critical surface runs along a weak layer from '
             'a composite one, and Composite Surfaces is off in the project '
             'the samples run on, so that surface cannot be formed again; '
             'this method was skipped.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.composite_off',
  'english': 'The deterministic critical surface is a composite one, and '
             'Composite Surfaces is off in the project the samples run on, so '
             'that surface cannot be formed again; this method was skipped.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.type_weak',
  'english': "The deterministic critical surface is of type 'weak_layer' on a "
             "base of type 'polyline', which a statistical run cannot "
             're-evaluate; this method was skipped.',
  'args': {'stype': 'weak_layer', 'btype': 'polyline'}},
 {'cat': 'stat',
  'code': 'stat.type',
  'english': "The deterministic critical surface is of type 'block', which a "
             'statistical run cannot re-evaluate; this method was skipped.',
  'args': {'stype': 'block'}},
 {'cat': 'stat',
  'code': 'stat.not_itself',
  'english': 'The deterministic critical surface does not re-evaluate to '
             'itself on the project the samples run on (it answers for x from '
             '10.00 to 40.50, circular, instead of x from 12.25 to 41.00, '
             'composite); a setting that decides the sliding mass, such as '
             'Composite Surfaces or a surface filter, differs between the two '
             'runs, so this method was skipped.',
  'args': {'x0': 10.0,
           'x1': 40.5,
           'there_type': 'circular',
           'hx0': 12.25,
           'hx1': 41.0,
           'home_type': 'composite'}},
 {'cat': 'stat',
  'code': 'stat.case_text_none',
  'english': 'a circular on no weak layer',
  'args': {'stype': 'circular'}},
 {'cat': 'stat',
  'code': 'stat.case_text_layers',
  'english': 'a weak_layer along weak layers over x from 12.00 to 18.50, x '
             'from 22.25 to 30.00',
  'args': {'stype': 'weak_layer',
           'spans': [{'$code': 'stat.span',
                      '$cat': 'stat',
                      '$args': {'x0': 12.0, 'x1': 18.5}},
                     {'$code': 'stat.span',
                      '$cat': 'stat',
                      '$args': {'x0': 22.25, 'x1': 30.0}}]}},
 {'cat': 'stat',
  'code': 'stat.not_itself_case',
  'english': 'The deterministic critical surface does not re-evaluate to '
             'itself on the project the samples run on (it answers for the '
             'same mass as a weak_layer along weak layers over x from 12.00 '
             'to 18.50, x from 22.25 to 30.00, instead of a weak_layer on no '
             'weak layer); a setting that decides the weak-layer case, such '
             'as the weak-layer handling or a suppressed weak layer, differs '
             'between the two runs, so this method was skipped.',
  'args': {'there': {'$code': 'stat.case_text_layers',
                     '$cat': 'stat',
                     '$args': {'stype': 'weak_layer',
                               'spans': [{'$code': 'stat.span',
                                          '$cat': 'stat',
                                          '$args': {'x0': 12.0, 'x1': 18.5}},
                                         {'$code': 'stat.span',
                                          '$cat': 'stat',
                                          '$args': {'x0': 22.25,
                                                    'x1': 30.0}}]}},
           'home': {'$code': 'stat.case_text_none',
                    '$cat': 'stat',
                    '$args': {'stype': 'weak_layer'}}}},
 {'cat': 'stat',
  'code': 'stat.raised',
  'english': 'raised ValueError',
  'args': {'exc': 'ValueError'}},
 {'cat': 'stat', 'code': 'stat.no_result', 'english': 'no result', 'args': {}},
 {'cat': 'stat', 'code': 'stat.no_result', 'english': 'no result', 'args': {}},
 {'cat': 'stat',
  'code': 'stat.code_120',
  'english': '-120 tensile stress',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.code_112',
  'english': '-112 m-alpha',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.code_101',
  'english': 'inadmissible (-101)',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.inadmissible',
  'english': 'inadmissible',
  'args': {}},
 {'cat': 'stat', 'code': 'stat.unstated', 'english': 'unstated', 'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_admissible',
  'english': 'no admissible surface',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.no_critical',
  'english': 'no critical surface',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.counted',
  'english': 'zero_driving x 17',
  'args': {'label': {'$raw': 'zero_driving'}, 'n': 17}},
 {'cat': 'stat',
  'code': 'stat.reasons',
  'english': 'zero_driving x 17, raised ValueError x 3',
  'args': {'reasons': [{'$code': 'stat.counted',
                        '$cat': 'stat',
                        '$args': {'label': {'$raw': 'zero_driving'}, 'n': 17}},
                       {'$code': 'stat.counted',
                        '$cat': 'stat',
                        '$args': {'label': {'$code': 'stat.raised',
                                            '$cat': 'stat',
                                            '$args': {'exc': 'ValueError'}},
                                  'n': 3}}]}},
 {'cat': 'stat',
  'code': 'stat.no_sample',
  'english': 'no sample was drawn, so this method has no probability of '
             'failure.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.all_failed_gm',
  'english': 'all 40 samples failed on the deterministic critical surface, so '
             'this method has no probability of failure. Reasons: '
             'zero_driving x 17, raised ValueError x 3.',
  'args': {'n': 40,
           'reasons': {'$code': 'stat.reasons',
                       '$cat': 'stat',
                       '$args': {'reasons': [{'$code': 'stat.counted',
                                              '$cat': 'stat',
                                              '$args': {'label': {'$raw': 'zero_driving'},
                                                        'n': 17}},
                                             {'$code': 'stat.counted',
                                              '$cat': 'stat',
                                              '$args': {'label': {'$code': 'stat.raised',
                                                                  '$cat': 'stat',
                                                                  '$args': {'exc': 'ValueError'}},
                                                        'n': 3}}]}}}},
 {'cat': 'stat',
  'code': 'stat.all_failed_os',
  'english': 'all 40 samples produced no valid surface, so this method has no '
             'probability of failure. Reasons: no critical surface x 40.',
  'args': {'n': 40,
           'reasons': {'$code': 'stat.reasons',
                       '$cat': 'stat',
                       '$args': {'reasons': [{'$code': 'stat.counted',
                                              '$cat': 'stat',
                                              '$args': {'label': {'$code': 'stat.no_critical',
                                                                  '$cat': 'stat',
                                                                  '$args': {}},
                                                        'n': 40}}]}}}},
 {'cat': 'stat',
  'code': 'stat.gm_failed',
  'english': '12 of 40 samples could not be evaluated; check the variable '
             'ranges.',
  'args': {'failed': 12, 'n': 40}},
 {'cat': 'stat',
  'code': 'stat.os_failed',
  'english': '5 of 40 searches produced no valid surface.',
  'args': {'failed': 5, 'n': 40}},
 {'cat': 'stat',
  'code': 'stat.cps_steered',
  'english': 'No critical probabilistic surface: this search steers on the '
             'factors of safety it computes, so it analyses different '
             'surfaces in every sample and none of them has a probability of '
             'failure of its own. It is computed for the Grid, Slope, Path '
             'and Block searches.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.cps_ky',
  'english': 'No critical probabilistic surface: the search minimised the '
             'critical seismic coefficient Ky, and the critical probabilistic '
             'surface is defined on the factor of safety.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.cps_too_few',
  'english': 'No critical probabilistic surface: too few valid samples to '
             'estimate one.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.cps_not_in_every_sample',
  'english': 'No critical probabilistic surface: no surface of the search had '
             'a factor of safety in every sample, and a probability of '
             'failure counted over some of the samples only is not comparable '
             'with the others.',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.head_gm_mass',
  'english': '4 of 36 samples answered for another sliding mass of the '
             'deterministic circle',
  'args': {'n': 4, 'total': 36}},
 {'cat': 'stat',
  'code': 'stat.head_gm_case',
  'english': '2 of 36 samples answered for another weak-layer case of the '
             'deterministic surface',
  'args': {'n': 2, 'total': 36}},
 {'cat': 'stat',
  'code': 'stat.head_os_mass',
  'english': '3 of 40 samples had the deterministic circle as their critical '
             'surface, answering for another sliding mass',
  'args': {'n': 3, 'total': 40}},
 {'cat': 'stat',
  'code': 'stat.head_sens_mass',
  'english': 'The sweep of Clay — cohesion answered for another sliding mass '
             'of the deterministic circle at 3 of 11 points, from 2 to 5',
  'args': {'label': 'Clay — cohesion',
           'n': 3,
           'total': 11,
           'lo': 2.0,
           'hi': 5.0}},
 {'cat': 'stat',
  'code': 'stat.head_sens_case',
  'english': 'The sweep of Clay — cohesion answered for another weak-layer '
             'case of the deterministic surface at 3 of 11 points, from 2 to '
             '5',
  'args': {'label': 'Clay — cohesion',
           'n': 3,
           'total': 11,
           'lo': 2.0,
           'hi': 5.0}},
 {'cat': 'stat',
  'code': 'stat.span',
  'english': 'x from 12.25 to 41.00',
  'args': {'x0': 12.25, 'x1': 41.0}},
 {'cat': 'stat',
  'code': 'stat.switch_mass',
  'english': '4 of 36 samples answered for another sliding mass of the '
             'deterministic circle (x from 12.25 to 41.00), not for its own '
             '(x from 10.00 to 40.50).',
  'args': {'head': {'$code': 'stat.head_gm_mass',
                    '$cat': 'stat',
                    '$args': {'n': 4, 'total': 36}},
           'where': {'$code': 'stat.span',
                     '$cat': 'stat',
                     '$args': {'x0': 12.25, 'x1': 41.0}},
           'x0': 10.0,
           'x1': 40.5}},
 {'cat': 'stat',
  'code': 'stat.switch_mass_below',
  'english': '4 of 36 samples answered for another sliding mass of the '
             'deterministic circle (x from 12.25 to 41.00), not for its own '
             '(x from 10.00 to 40.50); 3 of the 7 with a factor below 1 are '
             'among them, and the probability of failure counts them.',
  'args': {'head': {'$code': 'stat.head_gm_mass',
                    '$cat': 'stat',
                    '$args': {'n': 4, 'total': 36}},
           'where': {'$code': 'stat.span',
                     '$cat': 'stat',
                     '$args': {'x0': 12.25, 'x1': 41.0}},
           'x0': 10.0,
           'x1': 40.5,
           'below': 3,
           'total': 7}},
 {'cat': 'stat',
  'code': 'stat.span_in',
  'english': 'x from 8.00 to 39.75 in 1',
  'args': {'x0': 8.0, 'x1': 39.75, 'n': 1}},
 {'cat': 'stat',
  'code': 'stat.joined',
  'english': 'x from 8.00 to 39.75 in 1; x from 12.25 to 41.00 in 3',
  'args': {'items': [{'$code': 'stat.span_in',
                      '$cat': 'stat',
                      '$args': {'x0': 8.0, 'x1': 39.75, 'n': 1}},
                     {'$code': 'stat.span_in',
                      '$cat': 'stat',
                      '$args': {'x0': 12.25, 'x1': 41.0, 'n': 3}}]}},
 {'cat': 'stat',
  'code': 'stat.case_none',
  'english': 'on no weak layer',
  'args': {}},
 {'cat': 'stat',
  'code': 'stat.switch_case',
  'english': '2 of 36 samples answered for another weak-layer case of the '
             'deterministic surface (on no weak layer), not for its own '
             '(along weak layers over x from 12.00 to 18.50, x from 22.25 to '
             '30.00).',
  'args': {'head': {'$code': 'stat.head_gm_case',
                    '$cat': 'stat',
                    '$args': {'n': 2, 'total': 36}},
           'where': {'$code': 'stat.case_none', '$cat': 'stat', '$args': {}},
           'own': {'$code': 'stat.case_layers',
                   '$cat': 'stat',
                   '$args': {'spans': [{'$code': 'stat.span',
                                        '$cat': 'stat',
                                        '$args': {'x0': 12.0, 'x1': 18.5}},
                                       {'$code': 'stat.span',
                                        '$cat': 'stat',
                                        '$args': {'x0': 22.25,
                                                  'x1': 30.0}}]}}}},
 {'cat': 'stat',
  'code': 'stat.switch_case_below',
  'english': '2 of 36 samples answered for another weak-layer case of the '
             'deterministic surface (on no weak layer), not for its own '
             '(along weak layers over x from 12.00 to 18.50, x from 22.25 to '
             '30.00); 1 of the 5 with a factor below 1 are among them, and '
             'the probability of failure counts them.',
  'args': {'head': {'$code': 'stat.head_gm_case',
                    '$cat': 'stat',
                    '$args': {'n': 2, 'total': 36}},
           'where': {'$code': 'stat.case_none', '$cat': 'stat', '$args': {}},
           'own': {'$code': 'stat.case_layers',
                   '$cat': 'stat',
                   '$args': {'spans': [{'$code': 'stat.span',
                                        '$cat': 'stat',
                                        '$args': {'x0': 12.0, 'x1': 18.5}},
                                       {'$code': 'stat.span',
                                        '$cat': 'stat',
                                        '$args': {'x0': 22.25, 'x1': 30.0}}]}},
           'below': 1,
           'total': 5}},
 {'cat': 'stat',
  'code': 'stat.case_layers',
  'english': 'along weak layers over x from 12.00 to 18.50',
  'args': {'spans': [{'$code': 'stat.span',
                      '$cat': 'stat',
                      '$args': {'x0': 12.0, 'x1': 18.5}}]}},
 {'cat': 'stat',
  'code': 'stat.case_in',
  'english': 'on no weak layer in 1',
  'args': {'case': {'$code': 'stat.case_none', '$cat': 'stat', '$args': {}},
           'n': 1}},
 {'cat': 'stat',
  'code': 'stat.joined',
  'english': 'along weak layers over x from 12.00 to 18.50 in 1; on no weak '
             'layer in 1',
  'args': {'items': [{'$code': 'stat.case_in',
                      '$cat': 'stat',
                      '$args': {'case': {'$code': 'stat.case_layers',
                                         '$cat': 'stat',
                                         '$args': {'spans': [{'$code': 'stat.span',
                                                              '$cat': 'stat',
                                                              '$args': {'x0': 12.0,
                                                                        'x1': 18.5}}]}},
                                'n': 1}},
                     {'$code': 'stat.case_in',
                      '$cat': 'stat',
                      '$args': {'case': {'$code': 'stat.case_none',
                                         '$cat': 'stat',
                                         '$args': {}},
                                'n': 1}}]}},
 {'cat': 'stat',
  'code': 'stat.joined',
  'english': 'first sentence; second sentence',
  'args': {'items': [{'$raw': 'first sentence'},
                     {'$raw': 'second sentence'}]}},
 {'cat': 'factoring',
  'code': 'factoring.no_factor',
  'english': 'Plugin Model: this strength model declares no partial factor, '
             'so it was NOT factored.',
  'args': {'model': 'Plugin Model'}},
 {'cat': 'factoring',
  'code': 'factoring.legacy_points',
  'english': 'a table saved as points before 0.1.218 is refused by the '
             'analysis, so it was not factored',
  'args': {}},
 {'cat': 'factoring',
  'code': 'factoring.legacy_snowden',
  'english': 'a material saved before 0.1.229 is refused by the analysis, so '
             'it was not factored',
  'args': {}},
 {'cat': 'factoring',
  'code': 'factoring.child_unbuilt',
  'english': 'rule 2: its model cannot be built, so it was not factored',
  'args': {'label': {'$code': 'strength.child.rules',
                     '$cat': 'strength',
                     '$args': {'n': 2}}}},
 {'cat': 'factoring',
  'code': 'factoring.child_note',
  'english': 'joint 1: a table saved as points before 0.1.218 is refused by '
             'the analysis, so it was not factored',
  'args': {'label': {'$code': 'strength.child.joints',
                     '$cat': 'strength',
                     '$args': {'n': 1}},
           'note': {'$code': 'factoring.legacy_points',
                    '$cat': 'factoring',
                    '$args': {}}}},
 {'cat': 'factoring',
  'code': 'factoring.joined',
  'english': 'one; two',
  'args': {'items': [{'$raw': 'one'}, {'$raw': 'two'}]}},
 {'cat': 'factoring',
  'code': 'factoring.snowden_unbuilt.bedding',
  'english': 'its bedding function cannot be built, so it was not factored',
  'args': {}},
 {'cat': 'factoring',
  'code': 'factoring.snowden_note.bedding',
  'english': 'bedding: Plugin Model: this strength model declares no partial '
             'factor, so it was NOT factored.',
  'args': {'note': {'$code': 'factoring.no_factor',
                    '$cat': 'factoring',
                    '$args': {'model': 'Plugin Model'}}}},
 {'cat': 'factoring',
  'code': 'factoring.snowden_unbuilt.rock_mass',
  'english': 'its rock mass function cannot be built, so it was not factored',
  'args': {}},
 {'cat': 'factoring',
  'code': 'factoring.snowden_note.rock_mass',
  'english': 'rock mass: Plugin Model: this strength model declares no '
             'partial factor, so it was NOT factored.',
  'args': {'note': {'$code': 'factoring.no_factor',
                    '$cat': 'factoring',
                    '$args': {'model': 'Plugin Model'}}}},
 {'cat': 'design',
  'code': 'design.none',
  'english': 'no partial factors applied',
  'args': {}},
 {'cat': 'design',
  'code': 'design.summary',
  'english': 'eurocode_7_da1_c2: 2 material(s) and 1 load(s) factored',
  'args': {'standard': 'eurocode_7_da1_c2', 'materials': 2, 'loads': 1}},
 {'cat': 'design',
  'code': 'design.material',
  'english': "Material 'Clay': Plugin Model: this strength model declares no "
             'partial factor, so it was NOT factored..',
  'args': {'name': 'Clay',
           'note': {'$code': 'factoring.no_factor',
                    '$cat': 'factoring',
                    '$args': {'model': 'Plugin Model'}}}},
 {'cat': 'design',
  'code': 'design.seismic_not_applied',
  'english': 'Seismic: the factor 1.1 is not applied — the run seeks the '
             'critical seismic coefficient, so there is no coefficient to '
             'factor.',
  'args': {'factor': 1.1}},
 {'cat': 'design',
  'code': 'design.seismic',
  'english': 'Seismic: kh and kv multiplied by 1.1.',
  'args': {'factor': 1.1}},
 {'cat': 'design',
  'code': 'design.weight_single',
  'english': 'Soil weight: the permanent-action factor 1.35 multiplies the '
             'weight of every slice (single source assumption).',
  'args': {'factor': 1.35}},
 {'cat': 'design',
  'code': 'design.weight',
  'english': 'Soil weight: the permanent-action factor 1.35 multiplies the '
             'weight of the slices whose base drives the sliding, and 1 that '
             'of the others.',
  'args': {'unfavourable': 1.35, 'favourable': 1.0}},
 {'cat': 'design',
  'code': 'design.loads_by_action',
  'english': 'Loads: each one is factored as a whole, by its action and by '
             'whether it drives the sliding of the surface: a permanent load '
             'by 1.35 or 1, a variable one by 1.5 or 0.',
  'args': {'pu': 1.35, 'pf': 1.0, 'vu': 1.5, 'vf': 0.0}},
 {'cat': 'design',
  'code': 'design.loads_variable',
  'english': 'Every load takes the variable-action factor (1.3): a load '
             'carries no action type in this version.',
  'args': {'factor': 1.3}},
 {'cat': 'design',
  'code': 'design.identity',
  'english': 'The standard is enabled but every factor is 1.0, so nothing '
             'changed.',
  'args': {}}]


def _cat(name):
    if name == "stat":
        from ogr_slip2d.stat_messages import STAT_NOTES
        return STAT_NOTES
    if name == "design":
        from ogr_core.project.design_messages import DESIGN_NOTES
        return DESIGN_NOTES
    if name == "factoring":
        from ogr_core.materials.messages import FACTORING_NOTES
        return FACTORING_NOTES
    from ogr_core.project.messages import STRENGTH_REFUSALS
    return STRENGTH_REFUSALS


_CATS = ("stat", "design", "factoring")


def _resolve(v):
    from ogr_core.messages import as_nested, coded, nested
    if isinstance(v, dict) and "$raw" in v:
        return nested("", {}, v["$raw"])
    if isinstance(v, dict) and "$code" in v:
        return as_nested(coded(_cat(v["$cat"]), v["$code"],
                               **_resolve(v["$args"])))
    if isinstance(v, list):
        return [_resolve(x) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(x) for k, x in v.items()}
    return v


def _message(case):
    from ogr_core.messages import coded
    return coded(_cat(case["cat"]), case["code"], **_resolve(case["args"]))


def _nested_codes(v):
    if isinstance(v, dict) and "$code" in v:
        yield v["$code"]
        yield from _nested_codes(v["$args"])
    elif isinstance(v, list):
        for x in v:
            yield from _nested_codes(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _nested_codes(x)


_F = string.Formatter()


def _fields(t):
    return sorted({f for _t, f, _s, _c in _F.parse(t) if f})


def _wordless(t):
    return not any(ch.isalpha() for lit, _f, _s, _c in _F.parse(t)
                   for ch in lit)


def _has_raw(v):
    if isinstance(v, dict) and "$raw" in v:
        return True
    if isinstance(v, dict):
        return any(_has_raw(x) for x in v.values())
    if isinstance(v, list):
        return any(_has_raw(x) for x in v)
    return False


#: A template field left unfilled (a value may itself hold braces).
_UNFILLED = re.compile(r"\{[a-z_]+(?:[:!][^}]*)?\}")


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


# ======================================================================
class TestTheEnglishIsTheOldOne:

    def test_every_code_with_its_sample(self):
        for case in _V1352:
            assert _message(case) == case["english"], case["code"]

    def test_the_samples_cover_every_code(self):
        seen = set()
        for case in _V1352:
            seen.add(case["code"])
            seen.update(_nested_codes(case["args"]))
        every = set()
        for name in _CATS:
            every |= set(_cat(name))
        assert seen - set(_cat("strength")) == every, every ^ seen

    def test_the_catalogues_are_the_windows(self):
        from ogr_gui.core_messages import _catalogue
        for name in _CATS:
            assert set(_cat(name)) <= set(_catalogue()), name


class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for name in _CATS:
            for code, spec in _cat(name).items():
                if _wordless(spec.english):
                    continue
                assert spec.english in es, (code, spec.english[:60])
                assert _fields(es[spec.english]) == _fields(spec.english), code
                assert es[spec.english] != spec.english, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_gui.core_messages import note_text
        with _Spanish():
            for case in _V1352:
                said = note_text(_message(case))
                spec = _cat(case["cat"])[case["code"]]
                if not (_wordless(spec.english) and _has_raw(case["args"])):
                    assert said and said != case["english"], case["code"]
                assert not _UNFILLED.search(said), (case["code"], said)


# ======================================================================
_CODED = {
    "ogr_slip2d/probabilistic.py": (
        "_cannot_reevaluate", "_type_refusal", "_publish_note",
        "_stale_variables_stop", "_MassSwitches.where",
        "_MassSwitches.sentence", "_case_text", "_spans", "_case",
        "_CaseSwitches.where", "_CaseSwitches.sentence",
        "_does_not_reevaluate_to_itself", "_sample_failure",
        "_search_failure", "_counted_reasons", "_no_sample_note",
        "_method_lines", "_publish_method_losses",
        "_publish_method_warnings", "run_global_minimum",
        "run_overall_slope"),
    "ogr_slip2d/sensitivity.py": ("run_sensitivity",),
    "ogr_slip2d/analysis_runner.py": ("run_configured_statistics",),
    "ogr_core/project/design_factors.py": ("FactorReport.summary",
                                           "apply_design_factors"),
    "ogr_core/materials/strength_model.py": (
        "StrengthModel.design_factored",),
    "ogr_core/materials/builtin_models.py": (
        "AnisotropicStrengthFunction.design_factored",
        "GeneralizedAnisotropic.design_factored",
        "SnowdenModifiedAnisotropicLinear.design_factored"),
}


def _function(tree, name):
    if "." in name:
        cls, meth = name.split(".")
        owners = [n for n in tree.body
                  if isinstance(n, ast.ClassDef) and n.name == cls]
        assert len(owners) == 1, name
        found = [n for n in owners[0].body
                 if isinstance(n, ast.FunctionDef) and n.name == meth]
    else:
        found = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(found) == 1, name
    return found[0]


class TestNoSentenceWithoutItsCode:

    def test_census(self):
        found = []
        for rel, names in _CODED.items():
            src = (_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for name in names:
                fn = _function(tree, name)
                # every docstring in it, a nested function's too
                docs = {d.body[0].value for d in ast.walk(fn)
                        if isinstance(d, (ast.FunctionDef, ast.ClassDef))
                        and d.body and isinstance(d.body[0], ast.Expr)
                        and isinstance(d.body[0].value, ast.Constant)}
                parents = {}
                for n in ast.walk(fn):
                    for c in ast.iter_child_nodes(n):
                        parents[c] = n
                for n in ast.walk(fn):
                    if n in docs:
                        continue
                    # the key of a dictionary of changes is data
                    up = parents.get(n)
                    if isinstance(up, ast.Subscript) and up.slice is n:
                        continue
                    if isinstance(n, ast.JoinedStr):
                        found.append((rel, name, n.lineno, "f-string"))
                    elif (isinstance(n, ast.BinOp)
                          and isinstance(n.op, ast.Mod)
                          and isinstance(n.left, ast.Constant)
                          and isinstance(n.left.value, str)):
                        found.append((rel, name, n.lineno, "% format"))
                    elif (isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute)
                          and n.func.attr == "join"
                          and isinstance(n.func.value, ast.Constant)
                          and n.func.value.value == "; "):
                        found.append((rel, name, n.lineno, "joined by hand"))
                    elif (isinstance(n, ast.Constant)
                          and isinstance(n.value, str)
                          and len(n.value) > 40 and " " in n.value):
                        found.append((rel, name, n.lineno, "sentence"))
        assert not found, found

    def test_the_module_constants_carry_their_codes(self):
        from ogr_slip2d import probabilistic as P
        for name in ("_FACTORED_COPY", "_NO_METHOD", "_NO_DETERMINISTIC",
                     "_CPS_STEERED", "_CPS_KY", "_CPS_TOO_FEW",
                     "_CPS_NOT_IN_EVERY_SAMPLE"):
            assert getattr(P, name).code.startswith("stat."), name
        for code in P._CODE_LABELS.values():
            assert code.code.startswith("stat.code_"), code

    def test_the_probe_head_is_the_templates(self):
        """The bank and three tests read the head of ``_NOT_ITSELF``: it is
        the catalogue's template, with the same head as before."""
        from ogr_slip2d import probabilistic as P
        from ogr_slip2d.stat_messages import (NOT_ITSELF, NOT_ITSELF_CASE,
                                              STAT_NOTES)
        assert P._NOT_ITSELF == STAT_NOTES[NOT_ITSELF].english
        assert P._NOT_ITSELF_CASE == STAT_NOTES[NOT_ITSELF_CASE].english
        assert P._NOT_ITSELF.split(" (", 1)[0] == (
            "The deterministic critical surface does not re-evaluate to "
            "itself on the project the samples run on")


# ======================================================================
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


_RUN = {}


def _partial():
    """The real partial run of v1170: on the notched slope with Composite
    Surfaces off, Janbu's composite critical surface is refused and
    Bishop's circle is sampled. Run once for the class."""
    if "run" not in _RUN:
        from ogr_core.statistics import SamplingMethod
        from ogr_slip2d.probabilistic import run_global_minimum
        import test_partial_method_loss_v1170 as T
        off, det, V = T._real_partial()
        res = run_global_minimum(off, det, [V._cohesion_var(off)],
                                 num_samples=2,
                                 sampling=SamplingMethod.MONTE_CARLO,
                                 seed=7, num_slices=V._SLICES)
        _RUN["run"] = (off, res, T._LOST)
    return _RUN["run"]


_REFUSED_ES = ("La superficie crítica determinista es compuesta, y Superficies "
               "compuestas está desactivada")


class TestTheWindowSaysThemInSpanish:

    def test_the_line_of_a_lost_method(self):
        from ogr_gui.core_messages import note_line
        from ogr_gui.labels import method_name
        _p, res, lost = _partial()
        assert res.ok and len(res.note_lines) == 1, res.note_lines
        with _Spanish():
            line = note_line(res.note_lines[0])
            name = method_name(lost)
        assert line.startswith(name + ": " + _REFUSED_ES), line

    def test_the_headline_of_the_status_bar(self):
        from ogr_gui.core_messages import note_text
        _p, res, _lost = _partial()
        with _Spanish():
            said = note_text(res.notes["warning"])
        assert _REFUSED_ES in said, said
        assert "The deterministic" not in said, said

    def test_the_statistics_window(self):
        from ogr_gui.statistics_window import StatisticsWindow
        p, res, _lost = _partial()
        _app()
        with _Spanish():
            w = StatisticsWindow(p, prob_result=res)
            try:
                text = w.lbl_run_notes.text()
            finally:
                w.close()
        assert _REFUSED_ES in text, text

    def test_a_run_with_no_random_variable(self):
        from ogr_core.project import Project
        from ogr_gui.core_messages import note_text
        from ogr_slip2d.probabilistic import run_global_minimum
        res = run_global_minimum(Project(), {"bishop_simplified": None}, [])
        assert res.notes["error"].code == "stat.no_variables"
        with _Spanish():
            said = note_text(res.notes["error"])
        assert said.startswith("No hay variables aleatorias definidas"), said

    def _report(self):
        from ogr_core.project import apply_design_factors
        import test_design_factor_report_gui_v1165 as T
        p = T._with_standard(T._slope(), "eurocode7_da1c1")
        return apply_design_factors(p)[1]

    def test_what_the_design_standard_did(self):
        from ogr_gui.core_messages import note_line
        from ogr_gui.main_window import MainWindow
        rep = self._report()
        with _Spanish():
            lines = MainWindow._factor_report_notes(rep)
            said = [note_line(n) for n in lines]
        assert "eurocode7_da1c1: 0 material(es) y 0 carga(s)" in said[0], said
        assert said[1].startswith("Peso del terreno: el coeficiente de las "
                                  "acciones permanentes 1.35"), said

    def test_and_on_every_sample(self):
        from ogr_gui.core_messages import note_line
        from ogr_gui.reported_quantity import statistics_factor_lines
        rep = self._report()
        with _Spanish():
            said = [note_line(n) for n in statistics_factor_lines(rep)]
        assert "eurocode7_da1c1: 0 material(es)" in said[0], said
        assert said[1].startswith("Peso del terreno"), said


class TestTheApiReadsEnglish:

    def test_the_run_and_the_report(self):
        import json
        _p, res, lost = _partial()
        said = json.loads(json.dumps(res.notes["warning"]))
        assert said.startswith(lost + ": The deterministic critical "
                               "surface is a composite one"), said
        rep = TestTheWindowSaysThemInSpanish()._report()
        assert rep.summary() == ("eurocode7_da1c1: 0 material(s) and 0 "
                                 "load(s) factored")
