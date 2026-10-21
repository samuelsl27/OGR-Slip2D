# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.348 (D335, second part) — the notes about one method's reported
surface carry stable codes, and the Analysis Notes panel files them under
the method's NAME and says them in Spanish.

``run_analysis`` writes, once per method, ``"<method id>: <note>"``: the
inter-slice inclination that was the closest sample and not a root, a
daylight too steep for the slicing, a near-zero m-alpha, slices with no
strength, a centre on the edge of the grid, the seismic modes, a reversed
support, the supports that put no force. They were English sentences glued
from pieces. Each is a code now (``ogr_slip2d.method_note_messages``), the
line a ``method_note`` carrying the method and the nested note.

The invariants:

* **the English is v0.1.347's, byte for byte**: for every code, with a
  sample, the line equals the one v0.1.347 wrote with the same values --
  its old expression, taken from that version's source and evaluated,
  frozen below (``_V1347``). A clause (the four of the m-alpha sentence, the
  reasons a support lists) is built here with the NEW catalogue, so the
  comparison covers its template too;
* every code is sampled, in both numbers where it has two, nested or not;
* **every code says itself in Spanish**, with the template's fields;
* the reasons of the catalogue are the engine's ``SUPPORT_*`` values, in the
  order the engine lists them;
* **no sentence of these functions is built without its code** (AST
  census), but for two pieces of data named below;
* a coded line pickles with its nested and listed clauses, and its codes go
  to JSON (the API's ``warning_codes``);
* **in the window, in Spanish**: a real run's support note in the panel,
  under "Bishop simplificado" and not ``bishop_simplified``.
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

#: ``{code, args, english[, prefix]}``: the line v0.1.347 wrote with those
#: values. A nested value is ``{"$code", "$args"}`` (``{"$nothing"}`` for a
#: clause left out), and ``prefix`` the method in front of the line.
_V1347 = [{'code': 'method.unregistered',
  'english': "'janbu_corected' is not a registered analysis method, so it "
             'was not computed. Available: bishop_simplified, spencer.',
  'args': {'method': 'janbu_corected',
           'available': 'bishop_simplified, spencer'}},
 {'code': 'method.unregistered',
  'english': "'janbu_corected' is not a registered analysis method, so it "
             'was not computed. Available: bishop_simplified, spencer.',
  'args': {'method': 'janbu_corected',
           'available': 'bishop_simplified, spencer'}},
 {'code': 'method.lambda_fallback',
  'english': 'no inclination of the inter-slice forces makes the force and '
             'the moment factors of safety agree, so the factor reported is '
             'the closest sampled inclination rather than a solved one: its '
             'two factors differ by 0.0123, against a convergence tolerance '
             'of 0.0001.',
  'args': {'residual': 0.012345, 'tolerance': 0.0001}},
 {'code': 'method.lambda_not_closed',
  'english': 'an inclination of the inter-slice forces where the force and '
             'the moment factors of safety cross WAS found, and refining it '
             'did not close the gap: the two factors still differ by 0.00032 '
             'against a convergence tolerance of 1e-06, with the interval '
             'narrowed to 0.00321. The factor reported is the one at that '
             'inclination, not a solved root.',
  'args': {'residual': 0.00032, 'tolerance': 1e-06, 'width': 0.00321}},
 {'code': 'method.lambda_lost_budget',
  'english': 'and 1 inclination was discarded because its inner iteration '
             'used its whole budget of passes while still improving, so the '
             'limit that decided this answer belongs to the solver rather '
             'than to the slope. A looser convergence tolerance spends fewer '
             'passes per inclination and may bracket it.',
  'args': {'n': 1}},
 {'code': 'method.lambda_lost_overflow',
  'english': 'and 1 inclination was discarded because the inter-slice thrust '
             'of its inner iteration ran past 10 times the total force the '
             'sliding mass has to work with, which is a runaway and not a '
             'solution of anything.',
  'args': {'n': 1, 'limit': 10.0}},
 {'code': 'method.lambda_lost_stall',
  'english': 'and 1 inclination was discarded because its inner iteration '
             'stopped improving for 80 passes, in its factor and in its '
             'inter-slice thrust alike, and the relaxation rescue could not '
             'settle it either, so the limit that decided this answer '
             'belongs to the solver rather than to the slope.',
  'args': {'n': 1, 'passes': 80}},
 {'code': 'method.lambda_lost_inadmissible',
  'english': 'and 1 inclination was discarded because one of its two '
             'equilibrium branches had no admissible solution there at all: '
             'the factor of safety it was iterating towards stopped being '
             'finite and positive, so that inclination could not be compared '
             'with its neighbours.',
  'args': {'n': 1}},
 {'code': 'method.lambda_refined',
  'english': 'The calibrated grid of inclinations bracketed nothing, so 1 '
             'further inclination was sampled between the last one that '
             'solved and the first one that did not, which is where a '
             'crossing hidden by a lost sample would be.',
  'args': {'n': 1}},
 {'code': 'method.lambda_recovered',
  'english': 'The calibrated grid bracketed nothing until 1 inclination was '
             'put back after being set aside for an inter-slice thrust in '
             'net tension: the crossing lay among them, so the factor '
             'reported is a solved root rather than the closest sampled '
             'inclination.',
  'args': {'n': 1}},
 {'code': 'method.lambda_lost_budget',
  'english': 'and 3 inclinations was discarded because its inner iteration '
             'used its whole budget of passes while still improving, so the '
             'limit that decided this answer belongs to the solver rather '
             'than to the slope. A looser convergence tolerance spends fewer '
             'passes per inclination and may bracket it.',
  'args': {'n': 3}},
 {'code': 'method.lambda_lost_overflow',
  'english': 'and 3 inclinations was discarded because the inter-slice '
             'thrust of its inner iteration ran past 10 times the total '
             'force the sliding mass has to work with, which is a runaway '
             'and not a solution of anything.',
  'args': {'n': 3, 'limit': 10.0}},
 {'code': 'method.lambda_lost_stall',
  'english': 'and 3 inclinations was discarded because its inner iteration '
             'stopped improving for 80 passes, in its factor and in its '
             'inter-slice thrust alike, and the relaxation rescue could not '
             'settle it either, so the limit that decided this answer '
             'belongs to the solver rather than to the slope.',
  'args': {'n': 3, 'passes': 80}},
 {'code': 'method.lambda_lost_inadmissible',
  'english': 'and 3 inclinations were discarded because one of its two '
             'equilibrium branches had no admissible solution there at all: '
             'the factor of safety it was iterating towards stopped being '
             'finite and positive, so that inclination could not be compared '
             'with its neighbours.',
  'args': {'n': 3}},
 {'code': 'method.lambda_refined',
  'english': 'The calibrated grid of inclinations bracketed nothing, so 3 '
             'further inclinations were sampled between the last one that '
             'solved and the first one that did not, which is where a '
             'crossing hidden by a lost sample would be.',
  'args': {'n': 3}},
 {'code': 'method.lambda_recovered',
  'english': 'The calibrated grid bracketed nothing until 3 inclinations '
             'were put back after being set aside for an inter-slice thrust '
             'in net tension: the crossing lay among them, so the factor '
             'reported is a solved root rather than the closest sampled '
             'inclination.',
  'args': {'n': 3}},
 {'code': 'method.daylight_steep',
  'english': 'The critical surface daylights at 87.3 deg from the '
             'horizontal, which is too steep for a fixed number of slices to '
             'resolve: its factor of safety depends on that number. It was '
             'computed with 50 slices. Re-run with more and compare before '
             'quoting it.',
  'args': {'steepest': 87.3456, 'num_slices': 50}},
 {'code': 'method.m_alpha_margin',
  'english': 'The reported surface has m_alpha down to 0.3456 on a base at '
             '61.3 deg, which clears the 0.2 limit by 0.1456. That divides '
             'the normal force on that base by 0.3456, inflating it '
             '2.9-fold. This method satisfies force AND moment equilibrium, '
             'so there is no more complete one to check it against; what a '
             'base this steep costs it is the conditioning of the base '
             'normal, not the equilibrium it solves. Vary the number of '
             'slices, and compare against the other complete-equilibrium '
             'method, which differs from it only in the interslice force '
             'function.',
  'args': {'worst': 0.3456,
           'where': {'$code': 'method.m_alpha_where',
                     '$args': {'angle': 61.27}},
           'tail': {'$code': 'method.m_alpha_clears',
                    '$args': {'limit': 0.2, 'margin': 0.1456}},
           'effect': {'$code': 'method.m_alpha_inflates',
                      '$args': {'worst': 0.3456,
                                'factor': 2.893518518518518}},
           'advice': {'$code': 'method.m_alpha_advice_complete',
                      '$args': {}}}},
 {'code': 'method.m_alpha_margin',
  'english': 'The reported surface has m_alpha down to 0.1234, below the 0.2 '
             'limit. That divides the normal force on that base by 0.1234, '
             'inflating it 8.1-fold. A force-equilibrium method is least '
             'reliable there, and this value is the Bishop denominator: the '
             'one this method actually divides by carries its own interslice '
             'inclination. Compare against a complete-equilibrium method — '
             'Spencer and GLE/Morgenstern-Price — before quoting it.',
  'args': {'worst': 0.1234,
           'where': {'$nothing': True},
           'tail': {'$code': 'method.m_alpha_below', '$args': {'limit': 0.2}},
           'effect': {'$code': 'method.m_alpha_inflates',
                      '$args': {'worst': 0.1234,
                                'factor': 8.103727714748784}},
           'advice': {'$code': 'method.m_alpha_advice_force', '$args': {}}}},
 {'code': 'method.m_alpha_margin',
  'english': 'The reported surface has m_alpha down to -0.0125 on a base at '
             '72.5 deg, below the 0.2 limit. That denominator is zero or '
             'negative, so the normal force on that base is meaningless '
             'rather than merely large. A method of moments is not reliable '
             'there. Compare against a complete-equilibrium method — Spencer '
             'and GLE/Morgenstern-Price — before quoting it.',
  'args': {'worst': -0.0125,
           'where': {'$code': 'method.m_alpha_where',
                     '$args': {'angle': 72.5}},
           'tail': {'$code': 'method.m_alpha_below', '$args': {'limit': 0.2}},
           'effect': {'$code': 'method.m_alpha_nonpositive', '$args': {}},
           'advice': {'$code': 'method.m_alpha_advice_moment', '$args': {}}}},
 {'code': 'method.m_alpha_margin',
  'english': 'The reported surface has m_alpha down to 0.4641 on a base at '
             '55.0 deg, which clears the 0.2 limit by 0.2641. That divides '
             'the normal force on that base by 0.4641, inflating it '
             '2.2-fold. Compare against a complete-equilibrium method — '
             'Spencer and GLE/Morgenstern-Price — before quoting it.',
  'args': {'worst': 0.4641,
           'where': {'$code': 'method.m_alpha_where',
                     '$args': {'angle': 55.0}},
           'tail': {'$code': 'method.m_alpha_clears',
                    '$args': {'limit': 0.2, 'margin': 0.2641}},
           'effect': {'$code': 'method.m_alpha_inflates',
                      '$args': {'worst': 0.4641,
                                'factor': 2.154708037060978}},
           'advice': {'$code': 'method.m_alpha_advice_unknown',
                      '$args': {}}}},
 {'code': 'method.zero_strength',
  'english': '1 slice entered with zero shear strength (slice 4): the '
             'effective normal stress the strength envelope was read at was '
             'negative, and the envelope has no strength at zero stress. The '
             'factor of safety counts no resistance on that base.',
  'args': {'n': 1, 'shown': '4'}},
 {'code': 'method.zero_strength',
  'english': '3 slices entered with zero shear strength (slices 2, 3, 4): '
             'the effective normal stress the strength envelope was read at '
             'was negative, and the envelope has no strength at zero stress. '
             'The factor of safety counts no resistance on those bases.',
  'args': {'n': 3, 'shown': '2, 3, 4'}},
 {'code': 'method.zero_strength',
  'english': '10 slices entered with zero shear strength (slices 1, 2, 3, 4, '
             '5, 6, 7, 8, ...): the effective normal stress the strength '
             'envelope was read at was negative, and the envelope has no '
             'strength at zero stress. The factor of safety counts no '
             'resistance on those bases.',
  'args': {'n': 10, 'shown': '1, 2, 3, 4, 5, 6, 7, 8, ...'}},
 {'code': 'method.grid_edge',
  'english': 'The critical centre lies on the edge of the search grid (x = '
             '900, y = 80.5; grid x 100 to 900, y 50 to 80.5). A minimum on '
             'the boundary is the best of what was searched, not necessarily '
             'the lowest one: widen the grid on that side and re-run before '
             'quoting it.',
  'args': {'edges': 'x = 900, y = 80.5',
           'x0': 100.0,
           'x1': 900.0,
           'y0': 50.0,
           'y1': 80.5}},
 {'code': 'method.seismic_kh_replaced',
  'english': 'bishop_simplified: the project applies a horizontal seismic '
             'coefficient of 0.15, and the critical coefficient replaces it '
             'rather than adding to it. Ky is solved over kh from zero.',
  'args': {'kh': 0.15},
  'prefix': 'bishop_simplified'},
 {'code': 'method.seismic_no_ky',
  'english': 'bishop_simplified: 3 of 40 surfaces have no critical seismic '
             'coefficient below 1; they are excluded from the ranking rather '
             'than treated as strong.',
  'args': {'unanswered': 3, 'valid': 40, 'k_max': 1.0},
  'prefix': 'bishop_simplified'},
 {'code': 'method.newmark_no_record',
  'english': 'bishop_simplified: Newmark displacements were requested but no '
             'seismic record is selected, so no displacement was computed.',
  'args': {},
  'prefix': 'bishop_simplified'},
 {'code': 'method.newmark_unusable',
  'english': "bishop_simplified: the seismic record 'El Centro 1940' cannot "
             'be integrated (it needs at least two samples and a positive '
             'time interval), so no displacement was computed.',
  'args': {'name': 'El Centro 1940'},
  'prefix': 'bishop_simplified'},
 {'code': 'method.newmark_polarity',
  'english': "bishop_simplified: 'sideways' is not a polarity this program "
             'knows, so the maximum of the two was used.',
  'args': {'polarity': 'sideways'},
  'prefix': 'bishop_simplified'},
 {'code': 'method.support_reversed',
  'english': "Support 'Bolt 1' has its head at (10.12, 20.46), on the stable "
             'side of the reported surface, and its tail at (15.50, 18.25), '
             'inside the sliding mass. The head is the end at the slope '
             'FACE: the stripping length L_i is measured from it, the '
             'pullout length L_o from the tail, and the force under '
             "'tangent_to_slip' is placed from the axis read head to tail. "
             'Drawn this way round all three are reversed. Check which end '
             'was clicked first before quoting this factor.',
  'args': {'name': 'Bolt 1',
           'hx': 10.1234,
           'hy': 20.4567,
           'tx': 15.5,
           'ty': 18.25,
           'orientation': 'tangent_to_slip'}},
 {'code': 'method.support_reversed_any',
  'english': "Support 'Bolt 1' has its head at (10.12, 20.46), on the stable "
             'side of the reported surface, and its tail at (15.50, 18.25), '
             'inside the sliding mass. The head is the end at the slope '
             'FACE: the stripping length L_i is measured from it, the '
             "pullout length L_o from the tail, and the force under 'the "
             "chosen orientation' is placed from the axis read head to tail. "
             'Drawn this way round all three are reversed. Check which end '
             'was clicked first before quoting this factor.',
  'args': {'name': 'Bolt 1',
           'hx': 10.1234,
           'hy': 20.4567,
           'tx': 15.5,
           'ty': 18.25}},
 {'code': 'method.support_failure_one',
  'english': 'support s1 could not be priced: boom',
  'args': {'sid': 's1', 'why': 'boom'}},
 {'code': 'method.support_failure_many',
  'english': '2 supports could not be priced: s1 (boom); ? (bang)',
  'args': {'n': 2, 'entries': 's1 (boom); ? (bang)'}},
 {'code': 'method.support_unpriced',
  'english': 'The analysis could not price the reinforcement on the reported '
             'surface: support s1 could not be priced: boom. A support left '
             'out lowers no number and raises none, so this factor of safety '
             'is the one for the slope without it.',
  'args': {'said': {'$code': 'method.support_failure_one',
                    '$args': {'sid': 's1', 'why': 'boom'}}}},
 {'code': 'method.support_none_reached',
  'english': 'None of the 3 supports placed reached the reported surface: no '
             'slip polyline. The analysis prices the surface with no '
             'reinforcement at all when that happens, so this factor of '
             'safety is the one for the slope without any of them.',
  'args': {'total': 3, 'error': 'no slip polyline'}},
 {'code': 'method.support_shear_failed',
  'english': '1 support contributed only its axial capacity: shear_at raised '
             'AttributeError, TypeError, so the shear it declares was not '
             'counted. That is a defect in the support type rather than a '
             'property of the model, and the factor of safety is the one for '
             'less reinforcement than the model carries.',
  'args': {'n': 1, 'errors': 'AttributeError, TypeError'}},
 {'code': 'method.support_shear_failed',
  'english': '2 supports contributed only their axial capacity: shear_at '
             'raised AttributeError, TypeError, so the shear they declare '
             'was not counted. That is a defect in the support type rather '
             'than a property of the model, and the factor of safety is the '
             'one for less reinforcement than the model carries.',
  'args': {'n': 2, 'errors': 'AttributeError, TypeError'}},
 {'code': 'method.support_bond_failed',
  'english': '1 support was priced off its zero-stress envelope: building '
             'its bond profile raised AttributeError, TypeError, so it '
             'carries less reinforcement than the model declares. That is a '
             'defect in the support type rather than a property of the '
             'model.',
  'args': {'n': 1, 'errors': 'AttributeError, TypeError'}},
 {'code': 'method.support_bond_failed',
  'english': '2 supports were priced off their zero-stress envelopes: '
             'building their bond profiles raised AttributeError, TypeError, '
             'so they carry less reinforcement than the model declares. That '
             'is a defect in the support type rather than a property of the '
             'model.',
  'args': {'n': 2, 'errors': 'AttributeError, TypeError'}},
 {'code': 'method.support_part.not_priceable',
  'english': '1 could not be priced at all',
  'args': {'n': 1}},
 {'code': 'method.support_part.not_priceable',
  'english': '4 could not be priced at all',
  'args': {'n': 4}},
 {'code': 'method.support_bare.not_priceable',
  'english': 'it could not be priced at all',
  'args': {}},
 {'code': 'method.support_part.bond_profile_no_force',
  'english': '1 could not be given a bond profile, and its type prices '
             'nothing without one',
  'args': {'n': 1}},
 {'code': 'method.support_part.bond_profile_no_force_raised',
  'english': '1 could not be given a bond profile, and its type prices '
             'nothing without one (building it raised TypeError, ValueError)',
  'args': {'n': 1, 'errors': 'TypeError, ValueError'}},
 {'code': 'method.support_part.bond_profile_no_force',
  'english': '4 could not be given a bond profile, and their type prices '
             'nothing without one',
  'args': {'n': 4}},
 {'code': 'method.support_part.bond_profile_no_force_raised',
  'english': '4 could not be given a bond profile, and their type prices '
             'nothing without one (building it raised TypeError, ValueError)',
  'args': {'n': 4, 'errors': 'TypeError, ValueError'}},
 {'code': 'method.support_bare.bond_profile_no_force',
  'english': 'it could not be given a bond profile, and its type prices '
             'nothing without one',
  'args': {}},
 {'code': 'method.support_bare.bond_profile_no_force_raised',
  'english': 'it could not be given a bond profile, and its type prices '
             'nothing without one (building it raised TypeError, ValueError)',
  'args': {'errors': 'TypeError, ValueError'}},
 {'code': 'method.support_part.unknown_type',
  'english': '1 names a support class this build does not have',
  'args': {'n': 1}},
 {'code': 'method.support_part.unknown_type',
  'english': '4 name a support class this build does not have',
  'args': {'n': 4}},
 {'code': 'method.support_bare.unknown_type',
  'english': 'it names a support class this build does not have',
  'args': {}},
 {'code': 'method.support_part.no_length',
  'english': '1 has no length: its head and tail coincide',
  'args': {'n': 1}},
 {'code': 'method.support_part.no_length',
  'english': '4 have no length: their head and tail coincide',
  'args': {'n': 4}},
 {'code': 'method.support_bare.no_length',
  'english': 'it has no length: its head and tail coincide',
  'args': {}},
 {'code': 'method.support_part.no_crest',
  'english': '1 is drawn with both ends at one elevation, and its type '
             'measures its diagram from the upper one',
  'args': {'n': 1}},
 {'code': 'method.support_part.no_crest',
  'english': '4 are drawn with both ends at one elevation, and their type '
             'measures its diagram from the upper one',
  'args': {'n': 4}},
 {'code': 'method.support_bare.no_crest',
  'english': 'it is drawn with both ends at one elevation, and its type '
             'measures its diagram from the upper one',
  'args': {}},
 {'code': 'method.support_part.no_capacity',
  'english': '1 develops no capacity where it crosses',
  'args': {'n': 1}},
 {'code': 'method.support_part.no_capacity',
  'english': '4 develop no capacity where they cross',
  'args': {'n': 4}},
 {'code': 'method.support_bare.no_capacity',
  'english': 'it develops no capacity where it crosses',
  'args': {}},
 {'code': 'method.support_part.no_slice',
  'english': '1 crosses it at a point that falls in no slice',
  'args': {'n': 1}},
 {'code': 'method.support_part.no_slice',
  'english': '4 cross it at a point that falls in no slice',
  'args': {'n': 4}},
 {'code': 'method.support_bare.no_slice',
  'english': 'it crosses that surface at a point that falls in no slice',
  'args': {}},
 {'code': 'method.support_part.no_crossing',
  'english': '1 does not cross it',
  'args': {'n': 1}},
 {'code': 'method.support_part.no_crossing',
  'english': '4 do not cross it',
  'args': {'n': 4}},
 {'code': 'method.support_bare.no_crossing',
  'english': 'it does not cross that surface',
  'args': {}},
 {'code': 'method.support_only_one_silent',
  'english': 'The only support placed puts no force on the reported surface: '
             'it does not cross that surface. This factor of safety is the '
             'one for the slope with no reinforcement at all.',
  'args': {'bare': {'$code': 'method.support_bare.no_crossing',
                    '$args': {}}}},
 {'code': 'method.support_only_one_silent',
  'english': 'The only support placed puts no force on the reported surface: '
             'it could not be given a bond profile, and its type prices '
             'nothing without one (building it raised TypeError, '
             'ValueError). This factor of safety is the one for the slope '
             'with no reinforcement at all.',
  'args': {'bare': {'$code': 'method.support_bare.bond_profile_no_force_raised',
                    '$args': {'errors': 'TypeError, ValueError'}}}},
 {'code': 'method.support_none_forced',
  'english': 'None of the 3 supports placed put any force on the reported '
             'surface: 1 has no length: its head and tail coincide, 2 do not '
             'cross it. This factor of safety is the one for the slope with '
             'no reinforcement at all.',
  'args': {'total': 3,
           'parts': [{'$code': 'method.support_part.no_length',
                      '$args': {'n': 1}},
                     {'$code': 'method.support_part.no_crossing',
                      '$args': {'n': 2}}]}},
 {'code': 'method.support_some_silent',
  'english': '3 of the 5 supports placed put no force on the reported '
             'surface: 1 has no length: its head and tail coincide, 2 do not '
             'cross it. A support left out lowers no number and raises none, '
             'so the factor of safety is the one for the model without it. '
             'Check that these are the ones meant to be left out.',
  'args': {'silent': 3,
           'total': 5,
           'parts': [{'$code': 'method.support_part.no_length',
                      '$args': {'n': 1}},
                     {'$code': 'method.support_part.no_crossing',
                      '$args': {'n': 2}}]}}]


def _resolve(v):
    from ogr_slip2d import method_note_messages as MN
    if isinstance(v, dict) and "$nothing" in v:
        return MN.NOTHING
    if isinstance(v, dict) and "$code" in v:
        return MN.nested_method_note(v["$code"], **_resolve(v["$args"]))
    if isinstance(v, list):
        return [_resolve(x) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(x) for k, x in v.items()}
    return v


def _line(case):
    from ogr_core.messages import method_note
    from ogr_slip2d import method_note_messages as MN
    note = MN.method_note_text(case["code"], **_resolve(case["args"]))
    return method_note(case["prefix"], note) if case.get("prefix") else note


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


def _fields(t):
    return sorted({f for _t, f, _s, _c in string.Formatter().parse(t) if f})


# ======================================================================
class TestTheEnglishIsTheOldOne:

    def test_every_code_with_its_sample(self):
        for case in _V1347:
            assert _line(case) == case["english"], case["code"]

    def test_the_samples_cover_every_code_and_both_numbers(self):
        from ogr_slip2d.method_note_messages import METHOD_NOTES
        seen = set()
        for case in _V1347:
            seen.add(case["code"])
            seen.update(_nested_codes(case["args"]))
        assert seen == set(METHOD_NOTES), set(METHOD_NOTES) ^ seen
        for code, spec in METHOD_NOTES.items():
            if spec.one:
                counts = {c["args"].get(spec.count) for c in _V1347
                          if c["code"] == code}
                assert 1 in counts and len(counts) > 1, code


# ======================================================================
class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.method_note_messages import METHOD_NOTES
        es = _DICTS["es"]
        for code, spec in METHOD_NOTES.items():
            for en in [spec.english] + ([spec.one] if spec.one else []):
                assert en in es, (code, en[:60])
                assert _fields(es[en]) == _fields(en), code
                assert es[en] != en, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_gui.core_messages import note_line
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            for case in _V1347:
                said = note_line(_line(case))
                assert said and said != case["english"], case["code"]
                assert "{" not in said, (case["code"], said)
        finally:
            set_language(before)


# ======================================================================
class TestTheReasonsAreTheEngines:

    def test_same_values_same_order(self):
        import ogr_slip2d.support_integration as SI
        from ogr_slip2d.method_note_messages import BOND_NO_FORCE, UNCONTRIBUTING
        assert [r for r, *_ in UNCONTRIBUTING] == [
            SI.SUPPORT_NOT_PRICEABLE, SI.SUPPORT_BOND_PROFILE_NO_FORCE,
            SI.SUPPORT_UNKNOWN_TYPE, SI.SUPPORT_NO_LENGTH,
            SI.SUPPORT_NO_CREST, SI.SUPPORT_NO_CAPACITY, SI.SUPPORT_NO_SLICE,
            SI.SUPPORT_NO_CROSSING]
        assert BOND_NO_FORCE == SI.SUPPORT_BOND_PROFILE_NO_FORCE


# ======================================================================
#: The functions whose notes are coded in this version.
_CODED = {
    "ogr_slip2d/analysis_runner.py": (
        "lambda_fallback_notes", "daylight_tangent_note",
        "m_alpha_margin_note", "zero_strength_note", "grid_edge_note",
        "_seismic_notes", "run_analysis", "evaluate_surfaces"),
    "ogr_slip2d/support_integration.py": (
        "reversed_support_notes", "uncontributing_support_notes",
        "_failure_text"),
}
#: Two formats left, both DATA and the same in every language: a grid
#: coordinate ("x = 900") and a support with the exception it raised
#: ("s1 (TypeError: ...)").
_DATA = {
    ("grid_edge_note", 'f"{name} = {value:g}"'),
    ("_failure_text", '"%s (%s)" % (sid or "?", why)'),
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
                    seg = ast.get_source_segment(src, n) or ""
                    if (name, seg) in _DATA:
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

    def test_the_phrase_tables_left_the_engine(self):
        import ogr_slip2d.support_integration as SI
        for name in ("_UNCONTRIBUTING_PHRASES", "_SHEAR_FAILED_PHRASE",
                     "_BOND_FAILED_PHRASE", "_BOND_RAISED"):
            assert not hasattr(SI, name), name


# ======================================================================
class TestACodedLineTravels:

    def test_pickle_and_json_keep_the_clauses(self):
        from ogr_api.results import warning_codes
        from ogr_core.messages import METHOD_NOTE, method_note
        line = method_note("bishop_simplified", _line(next(
            c for c in _V1347 if c["code"] == "method.support_some_silent")))
        back = pickle.loads(pickle.dumps(line))
        assert back == line and back.code == METHOD_NOTE
        inner = back.args["note"]
        assert inner["code"] == "method.support_some_silent"
        assert [p["code"] for p in inner["args"]["parts"]] == [
            "method.support_part.no_length", "method.support_part.no_crossing"]
        codes = warning_codes(["plain", back])
        assert codes[0]["index"] == 1
        json.dumps(codes)


# ======================================================================
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


#: The note of a run whose only support never reaches the surface, in
#: Spanish.
_SILENT_ES = ("El único soporte colocado no aporta fuerza a la superficie "
              "informada: no cruza esa superficie. Este factor de seguridad es "
              "el del talud sin ningún refuerzo.")


class TestARealRun:

    def _outcome(self):
        from test_supports_all_methods_v164 import _nail, _project
        from ogr_slip2d.analysis_runner import run_analysis
        p = _project(_nail(head=(2.0, 1.0), tail=(12.0, 1.0)))
        return run_analysis(p, ["bishop_simplified"])

    def test_the_note_carries_the_method_and_its_codes(self):
        from ogr_core.messages import METHOD_NOTE
        out = self._outcome()
        hits = [w for w in out.warnings
                if getattr(w, "code", "") == METHOD_NOTE
                and w.args["note"]["code"] == "method.support_only_one_silent"]
        assert len(hits) == 1, out.warnings
        assert hits[0].startswith("bishop_simplified: The only support "
                                  "placed puts no force"), hits[0]
        assert hits[0].args["method_id"] == "bishop_simplified"
        bare = hits[0].args["note"]["args"]["bare"]
        assert bare["code"] == "method.support_bare.no_crossing"

    def test_the_panel_files_it_under_the_method_name_in_spanish(self):
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        _app()
        out = self._outcome()
        with _Spanish():
            panel = AnalysisNotesPanel(out.warnings)
            groups = {panel.tree.topLevelItem(i).text(0):
                      [panel.tree.topLevelItem(i).child(j).text(0)
                       for j in range(panel.tree.topLevelItem(i).childCount())]
                      for i in range(panel.tree.topLevelItemCount())}
            panel.close()
        mine = [g for g in groups if g.startswith("Bishop simplificado (")]
        assert mine, groups
        assert _SILENT_ES in groups[mine[0]], groups[mine[0]]
        assert not any(g.startswith("bishop_simplified") for g in groups)
