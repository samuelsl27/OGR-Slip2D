# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.349 (D335, third part) — the notes a search writes about its own run,
and those of Optimize Surfaces, carry stable codes, and the window says them
in Spanish.

A search says what it threw away and why (surfaces the slicer refused, ends
off the ground, bases in the air, a run that found nothing, the surfaces the
user drew, what Optimize Surfaces could not use, a pool that fell back to
one process) and why a given surface was not analysed. They were English
sentences glued from pieces; each is a code now
(``ogr_slip2d.search_note_messages``), and the reason a surface has no
factor of safety is nested with the code D314 gave it.

The invariants:

* **the English is v0.1.348's, byte for byte**: for every code, with a
  sample, the sentence equals the one v0.1.348 wrote with the same values --
  its old expression, taken from that version's source and evaluated, frozen
  below (``_V1348``); the clauses and the reasons a run lists are built here
  with the NEW catalogue;
* every code is sampled, in both numbers where it has two;
* **every code says itself in Spanish**, with the template's fields;
* **one sentence for each refusal a search records**, and the old table is
  gone;
* **no sentence of these functions is built without its code** (AST
  census), but for two windows "[a, b]", which are data;
* **in the window, in Spanish**: a real run's note about a circle the user
  drew, in the panel under the method's name; the optimisation box and the
  status bar read the report through ``note_text``.
"""
from __future__ import annotations

import ast
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``{code, args, english}``: the sentence v0.1.348 wrote with those values.
#: A nested value is ``{"$code", "$args"}``, a reason without a code
#: ``{"$raw": text}``, a clause left out ``{"$nothing": True}``.
_V1348 = [{'code': 'search.unsliceable',
  'english': '3 of the 120 surfaces this search formed could not be sliced '
             'and were dropped. Every vertex of a surface is a mandatory '
             'slice boundary, so a surface needs at least as many slices as '
             'it has segments, and every material boundary and water table '
             'it crosses adds one more; this analysis uses 50. The surfaces '
             'lost are the ones that cross the most layers, so this is not '
             'an even thinning of the search. Use more slices, or fewer '
             'vertices per surface.',
  'args': {'n': 3, 'total': 120, 'num_slices': 50}},
 {'code': 'search.unsliceable_circle',
  'english': '5 of the 400 surfaces this search formed could not be sliced '
             'and were dropped. Each circle is converted into 40 vertices, '
             'which is 39 straight segments, and this analysis uses 30 '
             'slices; every vertex is a mandatory slice boundary, and '
             'material boundaries and the water table take slices of their '
             'own. The surfaces lost are the ones that cross the most '
             'layers, so this is not an even thinning of the search. Use '
             'fewer vertices or more slices.',
  'args': {'n': 5,
           'total': 400,
           'vertices': 40,
           'segments': 39,
           'num_slices': 30}},
 {'code': 'search.outside_model',
  'english': '1 surface were discarded because a slice base fell outside the '
             'External Boundary, where there is no soil to give it strength. '
             'This is not a slice-count problem: the surfaces left the '
             'model. Check the extent of the External Boundary against the '
             'search area.',
  'args': {'n': 1}},
 {'code': 'search.orphan_material',
  'english': '1 surface were discarded because a slice base fell in a region '
             'whose material no longer exists. Assign that region another '
             'material (Properties > Assign Materials).',
  'args': {'n': 1}},
 {'code': 'search.base_above_ground',
  'english': '1 surface were discarded because the base rose above the '
             'ground surface between the two ends, so part of the sliding '
             'mass would be in the air. This is not a slice-count problem: '
             'more slices cannot put the base back under the ground. It '
             'happens where a surface follows a line that lies on the '
             'ground, such as a weak layer or a Block Search polyline along '
             'an exposed bench, and the line sits a little above the ground '
             'there.',
  'args': {'n': 1}},
 {'code': 'search.on_model_edge',
  'english': '1 slice base sat on the edge of the model, within the '
             'resolution of its own geometry, and was taken as being inside '
             'it. Nothing was discarded for this. It happens where a slip '
             'surface daylights exactly on a vertex of the External '
             'Boundary.',
  'args': {'n': 1}},
 {'code': 'search.outside_model',
  'english': '3 surfaces were discarded because a slice base fell outside '
             'the External Boundary, where there is no soil to give it '
             'strength. This is not a slice-count problem: the surfaces left '
             'the model. Check the extent of the External Boundary against '
             'the search area.',
  'args': {'n': 3}},
 {'code': 'search.orphan_material',
  'english': '3 surfaces were discarded because a slice base fell in a '
             'region whose material no longer exists. Assign that region '
             'another material (Properties > Assign Materials).',
  'args': {'n': 3}},
 {'code': 'search.base_above_ground',
  'english': '3 surfaces were discarded because the base rose above the '
             'ground surface between the two ends, so part of the sliding '
             'mass would be in the air. This is not a slice-count problem: '
             'more slices cannot put the base back under the ground. It '
             'happens where a surface follows a line that lies on the '
             'ground, such as a weak layer or a Block Search polyline along '
             'an exposed bench, and the line sits a little above the ground '
             'there.',
  'args': {'n': 3}},
 {'code': 'search.on_model_edge',
  'english': '3 slice bases sat on the edge of the model, within the '
             'resolution of its own geometry, and were taken as being inside '
             'it. Nothing was discarded for this. It happens where a slip '
             'surface daylights exactly on a vertex of the External '
             'Boundary.',
  'args': {'n': 3}},
 {'code': 'search.end_off_ground',
  'english': '3 polyline surfaces were discarded because an end was not on '
             'the ground surface: 2 with an end below the ground, which '
             'would have given its end slice a vertical face with no '
             'strength (the reference calls such a surface -101: one '
             'intersection with the slope); 1 with an end above it. This is '
             'not a slice-count problem: the first and last vertices of a '
             'polyline have to lie on the ground.',
  'args': {'n': 3,
           'parts': [{'$code': 'search.end_below', '$args': {'n': 2}},
                     {'$code': 'search.end_above', '$args': {'n': 1}}]}},
 {'code': 'search.end_off_ground',
  'english': '1 polyline surface were discarded because an end was not on '
             'the ground surface: 1 with an end above it. This is not a '
             'slice-count problem: the first and last vertices of a polyline '
             'have to lie on the ground.',
  'args': {'n': 1,
           'parts': [{'$code': 'search.end_above', '$args': {'n': 1}}]}},
 {'code': 'search.weak_layer_steep',
  'english': 'A surface clipped by a weak layer was discarded: its steepest '
             'slice base is 80.2 deg, past the 75 deg ceiling in Project '
             'Settings > Advanced.',
  'args': {'angle': 80.21409131831524, 'limit': 75.0}},
 {'code': 'search.no_valid',
  'english': 'No trial surface gave a valid factor of safety (500 '
             'generated). Refused before pricing: 3 with an end outside the '
             'Slope Limits [10, 25.5] and [60, 80]; 1 circle that do not cut '
             'the ground twice; 2 that left the model; 4 removed by the '
             'focus objects. Anything else was refused before it could be '
             'priced, for reasons this search does not record.',
  'args': {'total': 500,
           'priced': {'$nothing': True},
           'refused': {'$code': 'search.no_valid_refused',
                       '$args': {'parts': [{'$code': 'search.refused.slope_limits_two',
                                            '$args': {'n': 3,
                                                      'lo1': 10.0,
                                                      'hi1': 25.5,
                                                      'lo2': 60.0,
                                                      'hi2': 80.0}},
                                           {'$code': 'search.refused.misses_ground',
                                            '$args': {'n': 1}},
                                           {'$code': 'search.refused.left_model',
                                            '$args': {'n': 2}},
                                           {'$code': 'search.refused.focus',
                                            '$args': {'n': 4}}]}}}},
 {'code': 'search.no_valid',
  'english': 'No trial surface gave a valid factor of safety (80 generated). '
             '1 was priced and gave none; the census of invalid surfaces has '
             'their codes. Anything else was refused before it could be '
             'priced, for reasons this search does not record.',
  'args': {'total': 80,
           'priced': {'$code': 'search.no_valid_priced', '$args': {'n': 1}},
           'refused': {'$nothing': True}}},
 {'code': 'search.no_valid',
  'english': 'No trial surface gave a valid factor of safety (1200 '
             'generated). 7 were priced and gave none; the census of invalid '
             'surfaces has their codes. Refused before pricing: 2 with an '
             'end outside the Slope Limits; 9 circles that do not cut the '
             'ground twice; 1 that crossed a region with no material; 5 that '
             'the slicer refused; 3 with an end off the ground; 1 with the '
             'base above the ground; 4 with an end outside the Slope Limits '
             '[1, 2]; 6 with an end outside the Slope Limits [1, 2] and [3, '
             '4] and [5, 6]. Anything else was refused before it could be '
             'priced, for reasons this search does not record.',
  'args': {'total': 1200,
           'priced': {'$code': 'search.no_valid_priced', '$args': {'n': 7}},
           'refused': {'$code': 'search.no_valid_refused',
                       '$args': {'parts': [{'$code': 'search.refused.slope_limits',
                                            '$args': {'n': 2}},
                                           {'$code': 'search.refused.misses_ground',
                                            '$args': {'n': 9}},
                                           {'$code': 'search.refused.orphan',
                                            '$args': {'n': 1}},
                                           {'$code': 'search.refused.unsliceable',
                                            '$args': {'n': 5}},
                                           {'$code': 'search.refused.end_off',
                                            '$args': {'n': 3}},
                                           {'$code': 'search.refused.base_above',
                                            '$args': {'n': 1}},
                                           {'$code': 'search.refused.slope_limits_one',
                                            '$args': {'n': 4,
                                                      'lo': 1.0,
                                                      'hi': 2.0}},
                                           {'$code': 'search.refused.slope_limits_many',
                                            '$args': {'n': 6,
                                                      'windows': '[1, 2] and '
                                                                 '[3, 4] and '
                                                                 '[5, '
                                                                 '6]'}}]}}}},
 {'code': 'search.user_circular_skipped',
  'english': '1 user-defined circular surface was not analysed: the Surface '
             'Type of this analysis is Non-Circular, and one analysis '
             'carries one Surface Type. Set Surface Options -> Surface Type '
             '= Circular to include it.',
  'args': {'n': 1}},
 {'code': 'search.user_circular_skipped',
  'english': '2 user-defined circular surfaces were not analysed: the '
             'Surface Type of this analysis is Non-Circular, and one '
             'analysis carries one Surface Type. Set Surface Options -> '
             'Surface Type = Circular to include them.',
  'args': {'n': 2}},
 {'code': 'search.user_no_result',
  'english': 'The user-defined surface at centre (31.23, 48.5) with radius '
             '22 produced no result, so it is not in the reported '
             'population. No surface filter is active on this run, so the '
             'circle does not meet the ground twice inside the External '
             'Boundary.',
  'args': {'x': 31.234567, 'y': 48.5, 'r': 22.0001}},
 {'code': 'search.user_no_result_filtered',
  'english': 'The user-defined surface at centre (31.23, 48.5) with radius '
             '22 produced no result, so it is not in the reported '
             'population. Filters active on this run that can remove it: '
             'Slope Limits [2, 5], [30, 40], Minimum Area 2.5, Minimum Depth '
             '1.25, Minimum Elevation -3.',
  'args': {'x': 31.234567,
           'y': 48.5,
           'r': 22.0001,
           'filters': [{'$code': 'search.filter.slope_limits',
                        '$args': {'windows': '[2, 5], [30, 40]'}},
                       {'$code': 'search.filter.min_area',
                        '$args': {'value': 2.5}},
                       {'$code': 'search.filter.min_depth',
                        '$args': {'value': 1.25}},
                       {'$code': 'search.filter.min_elevation',
                        '$args': {'value': -3.0}}]}},
 {'code': 'search.user_no_factor',
  'english': 'The user-defined surface at centre (31.23, 48.5) with radius '
             '22 has no factor of safety: no reason declared.',
  'args': {'x': 31.234567,
           'y': 48.5,
           'r': 22.0001,
           'reason': {'$code': 'search.no_reason_stop', '$args': {}}}},
 {'code': 'search.user_no_factor',
  'english': 'The user-defined surface at centre (31.23, 48.5) with radius '
             '22 has no factor of safety: the base normal collapsed',
  'args': {'x': 31.234567,
           'y': 48.5,
           'r': 22.0001,
           'reason': {'$raw': 'the base normal collapsed'}}},
 {'code': 'search.user_reported',
  'english': 'The surface reported for this method is one the user defined '
             'by hand (centre (12.5, 33.25), radius 19), not one the search '
             'generated.',
  'args': {'x': 12.5, 'y': 33.25, 'r': 19.0}},
 {'code': 'search.no_reason', 'english': 'no reason declared', 'args': {}},
 {'code': 'search.optimisation_lost',
  'english': 'Optimize Surfaces walked 12 surface(s) and 6 came back '
             'unusable: 2 could not evaluate the starting surface at all; 1 '
             'started from a surface the method has no factor of safety for '
             '(no reason declared); 3 ended on an inadmissible surface. '
             'Those walks contributed nothing, and what is reported is what '
             'the search itself found.',
  'args': {'walked': 12,
           'lost': 6,
           'parts': [{'$code': 'search.opt.no_result', '$args': {'n': 2}},
                     {'$code': 'search.opt.no_factor',
                      '$args': {'n': 1,
                                'reason': {'$code': 'search.no_reason',
                                           '$args': {}}}},
                     {'$code': 'search.opt.inadmissible',
                      '$args': {'n': 3}}]}},
 {'code': 'search.optimisation_lost',
  'english': 'Optimize Surfaces walked 1 surface(s) and 1 came back '
             'unusable: 1 started from a surface the method has no factor of '
             'safety for (m-alpha 0.12 below 0.2). Those walks contributed '
             'nothing, and what is reported is what the search itself found.',
  'args': {'walked': 1,
           'lost': 1,
           'parts': [{'$code': 'search.opt.no_factor',
                      '$args': {'n': 1,
                                'reason': {'$raw': 'm-alpha 0.12 below '
                                                   '0.2'}}}]}},
 {'code': 'search.opt.unknown_technique',
  'english': "Unknown optimisation technique 'bogus': it has to be one of "
             'monte_carlo, surface_altering.',
  'args': {'technique': 'bogus', 'choices': 'monte_carlo, surface_altering'}},
 {'code': 'search.opt.three_vertices',
  'english': 'Optimisation needs at least three vertices: there is nothing '
             'to move on a two-point surface.',
  'args': {}},
 {'code': 'search.opt.start_refused',
  'english': 'The starting surface could not be evaluated: the slicer '
             'refused it whole. A polyline that rises above the ground '
             'anywhere is refused entirely, so a vertex a ten-thousandth '
             'over the profile is enough.',
  'args': {}},
 {'code': 'search.opt.start_invalid',
  'english': 'The starting surface was evaluated and has no factor of '
             'safety: no reason declared. That is not missing data, it is '
             'the answer.',
  'args': {'reason': {'$code': 'search.no_reason', '$args': {}}}},
 {'code': 'search.opt.snap_failed',
  'english': 'The snapped surface could not be evaluated; the unsnapped one '
             'is reported.',
  'args': {}},
 {'code': 'search.opt.summary',
  'english': '1.2346 → 1.1111 (-0.1235) in 250 evaluations, 37 accepted',
  'args': {'initial': 1.2345678,
           'final': 1.1111,
           'improvement': -0.1234678,
           'iterations': 250,
           'accepted': 37}},
 {'code': 'search.parallel_fallback',
  'english': 'The Grid Search was to be split across 4 processes and ran in '
             'one, because the process pool failed (OSError: pipe closed by '
             'peer). The result is the same; only the time is not.',
  'args': {'workers': 4,
           'error_type': 'OSError',
           'error': 'pipe closed by peer'}},
 {'code': 'search.refused_surface.default',
  'english': 'the surface does not cut the model, so there is nothing to '
             'price.',
  'args': {}},
 {'code': 'search.refused_surface.end_below_ground',
  'english': 'the surface was not analysed: its first or last vertex is '
             'below the ground, so it meets the slope only once (the '
             "reference's error -101) and its end slice would have a "
             'vertical face with no strength. Put both ends on the ground '
             'surface.',
  'args': {}},
 {'code': 'search.refused_surface.end_above_ground',
  'english': 'the surface was not analysed: its first or last vertex is '
             'above the ground. Put both ends on the ground surface.',
  'args': {}},
 {'code': 'search.refused_surface.outside_model',
  'english': 'the surface was not analysed: a slice base fell outside the '
             'External Boundary, where there is no soil.',
  'args': {}},
 {'code': 'search.refused_surface.orphan_material',
  'english': 'the surface was not analysed: a slice base fell in a region '
             'whose material no longer exists.',
  'args': {}},
 {'code': 'search.refused_surface.base_above_ground',
  'english': 'the surface was not analysed: between its two ends its base '
             'rises above the ground surface, so part of the mass would be '
             'in the air.',
  'args': {}},
 {'code': 'search.refused_surface.leaves_soil',
  'english': 'the surface was not analysed: it dips below the External '
             'Boundary.',
  'args': {}},
 {'code': 'search.refused_surface.unsliceable',
  'english': 'the surface was not analysed: the slicer refused it (more '
             'mandatory cuts than slices, a degenerate width or a tension '
             'crack it could not place).',
  'args': {}},
 {'code': 'search.refused_surface.outside_slope_limits',
  'english': 'the surface was not analysed: an end daylights outside the '
             'Slope Limits.',
  'args': {}},
 {'code': 'search.refused_surface.misses_ground',
  'english': 'the surface was not analysed: the circle does not cut the '
             "ground surface twice (the reference's error -101).",
  'args': {}}]


def _resolve(v):
    from ogr_core.messages import nested
    from ogr_slip2d import search_note_messages as SN
    if isinstance(v, dict) and "$nothing" in v:
        return SN.NOTHING
    if isinstance(v, dict) and "$raw" in v:
        return nested("", {}, v["$raw"])
    if isinstance(v, dict) and "$code" in v:
        return SN.nested_search_note(v["$code"], **_resolve(v["$args"]))
    if isinstance(v, list):
        return [_resolve(x) for x in v]
    if isinstance(v, dict):
        return {k: _resolve(x) for k, x in v.items()}
    return v


def _note(case):
    from ogr_slip2d import search_note_messages as SN
    return SN.search_note(case["code"], **_resolve(case["args"]))


def _with_args(v):
    """Every ``(code, args)`` a sample holds, nested ones too."""
    if isinstance(v, dict) and "$code" in v:
        yield v["$code"], v["$args"]
        yield from _with_args(v["$args"])
    elif isinstance(v, list):
        for x in v:
            yield from _with_args(x)
    elif isinstance(v, dict):
        for x in v.values():
            yield from _with_args(x)


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
        for case in _V1348:
            assert _note(case) == case["english"], case["code"]

    def test_the_samples_cover_every_code_and_both_numbers(self):
        from ogr_slip2d.search_note_messages import SEARCH_NOTES
        seen = set()
        for case in _V1348:
            seen.add(case["code"])
            seen.update(_nested_codes(case["args"]))
        assert seen == set(SEARCH_NOTES), set(SEARCH_NOTES) ^ seen
        pairs = [(c["code"], c["args"]) for c in _V1348]
        for c in _V1348:
            pairs.extend(_with_args(c["args"]))
        for code, spec in SEARCH_NOTES.items():
            if spec.one:
                counts = {a.get(spec.count) for k, a in pairs if k == code}
                assert 1 in counts and len(counts) > 1, code


# ======================================================================
class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.search_note_messages import SEARCH_NOTES
        es = _DICTS["es"]
        for code, spec in SEARCH_NOTES.items():
            for en in [spec.english] + ([spec.one] if spec.one else []):
                assert en in es, (code, en[:60])
                assert _fields(es[en]) == _fields(en), code
                assert es[en] != en, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            for case in _V1348:
                said = note_text(_note(case))
                assert said and said != case["english"], case["code"]
                assert "{" not in said, (case["code"], said)
        finally:
            set_language(before)


# ======================================================================
class TestOneSentenceForEachRefusal:

    def test_every_refusal_a_search_records(self):
        import ogr_slip2d.search as S
        import ogr_slip2d.slicer as SL
        from ogr_slip2d.search_note_messages import (REFUSED, REFUSED_DEFAULT,
                                                     SEARCH_NOTES, refusal)
        recorded = {SL.REFUSED_OUTSIDE_MODEL, SL.REFUSED_ORPHAN_MATERIAL,
                    SL.REFUSED_END_BELOW_GROUND, SL.REFUSED_END_ABOVE_GROUND,
                    SL.REFUSED_BASE_ABOVE_GROUND,
                    S.REFUSED_OUTSIDE_SLOPE_LIMITS, S.REFUSED_MISSES_GROUND,
                    "leaves_soil", "unsliceable"}
        coded = {c[len(REFUSED):] for c in SEARCH_NOTES
                 if c.startswith(REFUSED) and c != REFUSED_DEFAULT}
        assert coded == recorded, coded ^ recorded
        for key in recorded:
            assert refusal(key).code == REFUSED + key
        assert refusal(None).code == REFUSED_DEFAULT
        assert refusal("a key from a newer version").code == REFUSED_DEFAULT
        assert not hasattr(S.BaseSearch, "_REFUSAL_TEXT")

    def test_the_search_answers_with_the_code(self):
        from types import SimpleNamespace

        from ogr_slip2d.search import BaseSearch
        from ogr_slip2d.search_note_messages import REFUSED
        # the method reads one attribute; BaseSearch is abstract
        holder = SimpleNamespace(_last_refusal="misses_ground")
        said = BaseSearch.refusal_text(holder)
        assert said.code == REFUSED + "misses_ground"
        assert said.startswith("the surface was not analysed: the circle")


# ======================================================================
#: The functions whose notes are coded in this version.
_CODED = {
    "ogr_slip2d/search.py": (
        "BaseSearch._unsliceable_note", "_outside_model_note",
        "_orphan_material_note", "_end_off_ground_note",
        "_base_above_ground_note", "_no_valid_surface_note",
        "_on_model_edge_note", "_base_angle_ok", "_user_surface_filters",
        "_evaluate_user_surfaces", "_optimisation_note", "_optimize_result",
        "_optimize_each_minimum", "_parallel_grid_run",
        "AutoRefineNonCircularSearch._unsliceable_note",
        "BaseSearch.refusal_text"),
    "ogr_slip2d/optimize.py": (
        "optimize_surface", "_finish", "OptimizeReport.summary"),
}
#: Two formats left, both DATA: a window of the Slope Limits, "[a, b]".
_DATA = {
    ("_no_valid_surface_note", '"[%g, %g]" % (lo, hi)'),
    ("_user_surface_filters", '"[%g, %g]" % (min(a, b), max(a, b))'),
}


def _function(tree, name):
    if "." in name:
        cls, meth = name.split(".")
        c = next(n for n in ast.walk(tree)
                 if isinstance(n, ast.ClassDef) and n.name == cls)
        return next(n for n in c.body
                    if isinstance(n, ast.FunctionDef) and n.name == meth)
    return next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == name)


class TestNoSentenceWithoutItsCode:

    def test_census(self):
        found = []
        for rel, names in _CODED.items():
            src = (_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for name in names:
                fn = _function(tree, name)
                short = name.split(".")[-1]
                doc = (fn.body[0].value if isinstance(fn.body[0], ast.Expr)
                       else None)
                skip = set()
                for n in ast.walk(fn):
                    if n is not fn and isinstance(n, ast.FunctionDef):
                        skip.update(ast.walk(n))     # censused on its own
                for n in ast.walk(fn):
                    if n is doc or n in skip:
                        continue
                    if (short, ast.get_source_segment(src, n)) in _DATA:
                        skip.update(ast.walk(n))
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

    def test_the_window_reads_the_report_through_its_code(self):
        src = (_ROOT / "ogr_gui" / "main_window.py").read_text(
            encoding="utf-8")
        fn = _function(ast.parse(src), "_optimize_surfaces")
        body = ast.get_source_segment(src, fn)
        assert 'note_text(rep.notes["error"])' in body
        assert body.count("note_text(rep.summary())") == 2
        assert "% rep.summary()" not in body


# ======================================================================
class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _project_with_a_stray_circle():
    """The slope of v1347, a small grid, and a circle the user drew far
    above the ground: the run says it produced no result."""
    from ogr_api import Workspace, call
    from ogr_slip2d.surface import SlipCircle
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Search notes")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 3.0,
                                                   "friction_angle": 19.6}}}],
            "settings": {"search.grid_nx": 2, "search.grid_ny": 2,
                         "search.radius_increment": 2}})
        p = ws.get(pid).project
    finally:
        ws.shutdown()
    p.user_surfaces = [SlipCircle(centre_x=45.0, centre_y=200.0, radius=5.0)]
    return p


#: Its note, in Spanish.
_STRAY_ES = ("La superficie definida por el usuario con centro en (45, 200) "
             "y radio 5 no dio ningún resultado, así que no está en la "
             "población informada.")


class TestARealRun:

    def test_the_note_of_a_stray_circle_has_its_code(self):
        from ogr_core.messages import METHOD_NOTE
        from ogr_slip2d.analysis_runner import run_analysis
        out = run_analysis(_project_with_a_stray_circle(),
                           ["bishop_simplified"])
        hits = [w for w in out.warnings
                if getattr(w, "code", "") == METHOD_NOTE
                and w.args["note"]["code"].startswith("search.user_no_result")]
        assert len(hits) == 1, out.warnings
        assert hits[0].startswith("bishop_simplified: The user-defined "
                                  "surface at centre (45, 200)"), hits[0]

    def test_the_panel_says_it_in_spanish(self):
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        from ogr_slip2d.analysis_runner import run_analysis
        _app()
        out = run_analysis(_project_with_a_stray_circle(),
                           ["bishop_simplified"])
        with _Spanish():
            panel = AnalysisNotesPanel(out.warnings)
            groups = {panel.tree.topLevelItem(i).text(0):
                      [panel.tree.topLevelItem(i).child(j).text(0)
                       for j in range(panel.tree.topLevelItem(i).childCount())]
                      for i in range(panel.tree.topLevelItemCount())}
            panel.close()
        mine = [g for g in groups if g.startswith("Bishop simplificado (")]
        assert mine, groups
        assert any(s.startswith(_STRAY_ES) for s in groups[mine[0]]), groups

    def test_an_optimisation_refusal_in_spanish(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_gui.core_messages import note_text
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        from ogr_slip2d.surface import SlipSurface
        line = SlipSurface(polyline=Polyline(vertices=[
            Vertex(30, 25), Vertex(45, 27), Vertex(60, 35)]))
        _surface, _res, rep = optimize_surface(
            None, None, line, OptimizeSettings(technique="bogus"))
        assert rep.notes["error"].code == "search.opt.unknown_technique"
        assert rep.notes["error"].startswith(
            "Unknown optimisation technique 'bogus'")
        with _Spanish():
            said = note_text(rep.notes["error"])
        assert said.startswith("Técnica de optimización desconocida "
                               "'bogus': tiene que ser una de"), said
