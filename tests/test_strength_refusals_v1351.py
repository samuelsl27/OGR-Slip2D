# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.351 (D335, fifth part) — why a material's strength model cannot be
computed with carries stable codes, and the material dialog says it in
Spanish WITH its values.

The rules refuse the tables of the function models (points, discrete, C/Phi,
anisotropic), Snowden and its two functions, the Anisotropic Linear A and B,
the Generalized Anisotropic rules, its Angle or Surface input, its links and
its surfaces, and three models saved by older versions. They were English
f-strings; the dialog translated them through ``_TABLE_REFUSALS``, a table of
fixed sentences keyed by the refusal's code and without its values ("the
cohesion must be zero or more", but not which row or what it was). Each is a
code now (``ogr_core.project.messages.STRENGTH_REFUSALS``), the frame
"Material 'x', <model>: <why>" with the model shown through its translation
and the refusal nested, and the dialog says the refusal through its code.

The invariants:

* **the English is v0.1.350's, byte for byte, and so is the refusal's own
  code**: every input below was run through the rules of v0.1.350 and the
  sentence it gave is frozen (``_V1350``); the rules of this tree give the
  same sentence for the same input -- the whole function compared, not a
  template;
* every code is reached, nested ones included, and the labels of a
  Generalized Anisotropic child are the model's own words;
* every code says itself in Spanish with its fields;
* **no sentence of these functions is built without its code** (AST
  census), but for the exception names, which are data;
* **in the dialog, in Spanish**: a refusal shown with its values, the
  dialog's own table of fixed sentences gone.
"""
from __future__ import annotations

import ast
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``{case: [the refusal's code, the sentence v0.1.350 gave]}``.
_V1350 = {'aniso.empty': ['anisotropic_table_empty',
                 'The table has no rows: at least one range, ending at +90 '
                 'degrees, is needed.'],
 'aniso.end': ['anisotropic_table_end',
               'The last range must end at +90 degrees; it ends at 80.5.'],
 'aniso.not_finite': ['anisotropic_table_not_rows',
                      'Row 1 holds a value that is not finite.'],
 'aniso.not_list': ['anisotropic_table_not_rows',
                    'The table must be a list of (angle to, c, phi) rows.'],
 'aniso.not_three': ['anisotropic_table_not_rows',
                     'Row 1 is not three numbers (angle to, c, phi): (10, '
                     '5).'],
 'aniso.order': ['anisotropic_table_order',
                 'The ranges must be ordered counter-clockwise: row 2 ends '
                 'at 5 degrees, not after row 1 (10).'],
 'aniso.start': ['anisotropic_table_start',
                 "The first range starts at -90 degrees, so its 'angle to' "
                 'must be above -90; got -90.'],
 'aniso.strength': ['anisotropic_table_strength',
                    'Row 1: the cohesion must be ≥ 0 and the friction angle '
                    'in [0, 90), got c = 5, phi = 120.'],
 'aniso_linear.ab': ['anisotropic_linear_ab',
                     'A and B must satisfy 0 <= A <= B degrees; got A = 40, '
                     'B = 10.'],
 'aos.ab': ['generalized_aos_ab',
            'Joint 1: A and B must satisfy 0 <= A <= B <= 90 degrees; got A '
            "= 50, B = 'x'."],
 'aos.base': ['generalized_aos_base',
              'The base needs a strength: a material or a model of its own.'],
 'aos.base_if_weaker': ['generalized_aos_base_if_weaker',
                        'use_base_if_weaker must be true or false, not 1.'],
 'aos.definition': ['generalized_aos_definition',
                    "The anisotropy is defined by 'angle' or 'surface', not "
                    "'plane'."],
 'aos.joint_angle': ['generalized_aos_joint_angle',
                     'The angle of joint 1 must be a number of degrees.'],
 'aos.joint_model': ['generalized_aos_joint_model',
                     'Joint 1 needs a strength: a material or a model of its '
                     'own.'],
 'aos.joint_surface': ['generalized_aos_joint_surface',
                       'Joint 1 must name its anisotropic surface.'],
 'aos.joints': ['generalized_aos_joints',
                'At least one joint is needed, with its angle and its '
                'strength.'],
 'aos.mapping': ['generalized_aos_mapping',
                 "The mapping function is one of ['ab', 'cosine', 'linear'], "
                 "not 'tangent'."],
 'aos.model_error': ['generalized_aos_model',
                     'The strength model of joint 1 cannot be built: '
                     'KeyError: "Unknown strength model: \'no_such_model\'. '
                     "Available: ['mohr_coulomb', 'undrained', "
                     "'infinite_strength', 'no_strength', 'hoek_brown', "
                     "'hoek_brown_classic', 'power_curve', 'hyperbolic', "
                     "'vertical_stress_ratio', 'barton_bandis', "
                     "'drained_undrained', 'anisotropic_linear', "
                     "'shear_normal_function', 'step_function', "
                     "'discrete_function', 'c_phi_function', 'shansep', "
                     "'anisotropic_strength_function', "
                     "'generalized_anisotropic', "
                     "'snowden_anisotropic_linear', 'undrained_depth_layer', "
                     "'undrained_depth_datum', "
                     '\'undrained_slope_distance\']"'],
 'aos.model_error_base': ['generalized_aos_model',
                          'The strength model of the base cannot be built: '
                          'KeyError: "Unknown strength model: '
                          "'no_such_model'. Available: ['mohr_coulomb', "
                          "'undrained', 'infinite_strength', 'no_strength', "
                          "'hoek_brown', 'hoek_brown_classic', "
                          "'power_curve', 'hyperbolic', "
                          "'vertical_stress_ratio', 'barton_bandis', "
                          "'drained_undrained', 'anisotropic_linear', "
                          "'shear_normal_function', 'step_function', "
                          "'discrete_function', 'c_phi_function', 'shansep', "
                          "'anisotropic_strength_function', "
                          "'generalized_anisotropic', "
                          "'snowden_anisotropic_linear', "
                          "'undrained_depth_layer', 'undrained_depth_datum', "
                          '\'undrained_slope_distance\']"'],
 'aos.nested_base': ['generalized_aos_nested',
                     'The base holds a Generalized Anisotropic model; it '
                     'takes a plain strength.'],
 'aos.nested_joint': ['generalized_aos_nested',
                      'Joint 1 holds a Generalized Anisotropic model; it '
                      'takes a plain strength.'],
 'aos.selection': ['generalized_aos_selection',
                   "The joint selection is one of ['worst_case', 'closest'], "
                   "not 'any'."],
 'cphi.empty': ['c_phi_rows_empty',
                'The table has no rows: at least one (normal stress, '
                'cohesion, friction angle) row is needed.'],
 'cphi.not_finite': ['c_phi_rows_not_rows',
                     'Row 1 holds a value that is not finite.'],
 'cphi.not_list': ['c_phi_rows_not_rows',
                   'The table must be a list of (normal stress, cohesion, '
                   'friction angle) rows.'],
 'cphi.not_three': ['c_phi_rows_not_rows',
                    'Row 1 is not three numbers (normal stress, cohesion, '
                    'friction angle): (0, 1).'],
 'cphi.order': ['c_phi_rows_order',
                'The normal stresses must increase strictly: row 3 (90) does '
                'not exceed row 2 (100).'],
 'cphi.strength': ['c_phi_rows_strength',
                   'Row 1: the cohesion must be ≥ 0 and the friction angle '
                   'in [0, 90), got c = -2, phi = 30.'],
 'discrete.angle': ['discrete_function_angle',
                    'Point 1: the friction angle must be in [0, 90), got '
                    '95.'],
 'discrete.cohesion': ['discrete_function_strength',
                       'Point 1: the cohesion must be zero or more, got '
                       '-1.5.'],
 'discrete.empty': ['discrete_function_empty',
                    'The table has no points: at least one (x, y, c, phi) '
                    'point is needed.'],
 'discrete.empty_undrained': ['discrete_function_empty',
                              'The table has no points: at least one (x, y, '
                              'cu) point is needed.'],
 'discrete.method': ['discrete_function_method',
                     'The interpolation method must be one of '
                     "['inverse_distance', 'tin', 'thin_plate_spline', "
                     "'linear_by_elevation'], got 'spline'."],
 'discrete.not_finite': ['discrete_function_not_points',
                         'Point 1 holds a value that is not finite.'],
 'discrete.not_list': ['discrete_function_not_points',
                       'The table must be a list of (x, y, c, phi) points.'],
 'discrete.not_point': ['discrete_function_not_points',
                        'Point 1 is not (x, y, c, phi): (0, 0, 5).'],
 'discrete.repeated': ['discrete_function_repeated',
                       'Point 2 repeats the place (1.5, 2): two strengths '
                       'for one point.'],
 'discrete.type': ['discrete_function_type',
                   "The function type must be one of ['undrained', "
                   "'drained'], got 'wet'."],
 'frame.aniso_function': ['anisotropic_table_empty',
                          "Material 'Shale', Anisotropic Strength Function: "
                          'The table has no rows: at least one range, ending '
                          'at +90 degrees, is needed.'],
 'frame.aniso_legacy': ['anisotropic_table_legacy',
                        "The Anisotropic Strength Function of material 'Old "
                        "shale' was saved as interpolated points by a "
                        'version before 0.1.218. Its table is now a list of '
                        'angular RANGES (angle to, c, phi), as the reference '
                        'documents this strength type, so the same rows '
                        'would mean something else. Open the material, '
                        'review the table as ranges and accept it.'],
 'frame.aniso_linear': ['anisotropic_linear_ab',
                        "Material 'Slate', Anisotropic Linear: A and B must "
                        'satisfy 0 <= A <= B degrees; got A = 40, B = 10.'],
 'frame.c_phi': ['c_phi_rows_empty',
                 "Material 'Marl', C/Phi Function: The table has no rows: at "
                 'least one (normal stress, cohesion, friction angle) row is '
                 'needed.'],
 'frame.discrete': ['discrete_function_empty',
                    "Material 'Fill', Discrete Function: The table has no "
                    'points: at least one (x, y, cu) point is needed.'],
 'frame.generalized_aos': ['generalized_aos_joints',
                           "Material 'Jointed rock', Generalized "
                           'Anisotropic: At least one joint is needed, with '
                           'its angle and its strength.'],
 'frame.generalized_input': ['generalized_input_type',
                             "Material 'Rock', Generalized Anisotropic: the "
                             "input is one of ['angle_range', "
                             "'angle_or_surface'], not 'sideways'."],
 'frame.generalized_rules': ['generalized_rules_empty',
                             "Material 'Rock', Generalized Anisotropic: "
                             'There are no rules: at least one range, from '
                             '-90 to +90 degrees, with its strength model, '
                             'is needed.'],
 'frame.generalized_water': ['generalized_parent_water',
                             "Material 'Rock', Generalized Anisotropic: "
                             'use_parent_water must be true or false, not '
                             "'yes'."],
 'frame.shear_normal': ['function_points_empty',
                        "Material 'Clay', Shear/Normal Function: The table "
                        'has no points: at least one (normal stress, shear '
                        'strength) point is needed.'],
 'frame.snowden_ab': ['snowden_ab',
                      "Material 'Schist', Snowden Modified Anisotropic "
                      'Linear: A1 and B1 must satisfy 0 <= A1 <= B1 <= 90 '
                      'degrees; got A1 = 30, B1 = 10.'],
 'frame.snowden_legacy': ['snowden_legacy',
                          'The Snowden Modified Anisotropic Linear material '
                          "'Old schist' was saved by a version before "
                          '0.1.229, with c1, phi1, c2, phi2 and a single B '
                          'and a cosine transition of the friction ANGLE. '
                          'The model is now the one the reference documents: '
                          'a linear transition of the shear strength between '
                          'a bedding and a rock mass strength function, with '
                          'A1, B1, A2 and B2. The material shows the nearest '
                          'such form (A1 = A2 = 0, B1 = B2 = B, one C/Phi '
                          'row per function), whose numbers are not the old '
                          'ones: review it and accept it.'],
 'frame.step': ['function_points_order',
                "Material 'Silt', Step Function (σ′ₙ): The normal stresses "
                'must increase strictly: point 2 (0) does not exceed point 1 '
                '(0).'],
 'gen.angles': ['generalized_rules_angles',
                'Rule 1 must go from a lower to a higher angle within [-90, '
                '90] degrees; it goes from -90 to -95.5.'],
 'gen.angles_nan': ['generalized_rules_not_rules',
                    'The angles of rule 1 are not numbers.'],
 'gen.empty': ['generalized_rules_empty',
               'There are no rules: at least one range, from -90 to +90 '
               'degrees, with its strength model, is needed.'],
 'gen.end': ['generalized_rules_end',
             'The last range must end at +90 degrees; it ends at 45.'],
 'gen.gap': ['generalized_rules_order',
             'Rule 2 must start where rule 1 ends (0 degrees); it starts at '
             '10.5, which leaves the angles between 0 and 10.5 degrees with '
             'no strength.'],
 'gen.model_error': ['generalized_rules_model',
                     'The strength model of rule 1 cannot be built: '
                     'KeyError: "Unknown strength model: \'no_such_model\'. '
                     "Available: ['mohr_coulomb', 'undrained', "
                     "'infinite_strength', 'no_strength', 'hoek_brown', "
                     "'hoek_brown_classic', 'power_curve', 'hyperbolic', "
                     "'vertical_stress_ratio', 'barton_bandis', "
                     "'drained_undrained', 'anisotropic_linear', "
                     "'shear_normal_function', 'step_function', "
                     "'discrete_function', 'c_phi_function', 'shansep', "
                     "'anisotropic_strength_function', "
                     "'generalized_anisotropic', "
                     "'snowden_anisotropic_linear', 'undrained_depth_layer', "
                     "'undrained_depth_datum', "
                     '\'undrained_slope_distance\']"'],
 'gen.no_model': ['generalized_rules_model', 'Rule 1 has no strength model.'],
 'gen.not_list': ['generalized_rules_not_rules',
                  'The rules must be a list of {angle_min, angle_max, model} '
                  'objects.'],
 'gen.not_rule': ['generalized_rules_not_rules',
                  'Rule 2 is not an {angle_min, angle_max, model} object: '
                  "'rule'."],
 'gen.overlap': ['generalized_rules_order',
                 'Rule 2 must start where rule 1 ends (20 degrees); it '
                 'starts at 10, which overlaps it, so part of a range can '
                 'never be reached.'],
 'gen.start': ['generalized_rules_start',
               'The first range starts at -90 degrees; it starts at -80.'],
 'link.generalized': ['generalized_link_generalized',
                      "Material 'Bedded rock', Generalized Anisotropic: rule "
                      "2 links 'Other rock', another Generalized Anisotropic "
                      'material; a range takes a plain strength model.'],
 'link.missing': ['generalized_link_missing',
                  "Material 'Bedded rock', Generalized Anisotropic: rule 2 "
                  'links a material that is not in the project.'],
 'link.self': ['generalized_link_self',
               "Material 'Bedded rock', Generalized Anisotropic: rule 2 "
               'links the material itself.'],
 'points.empty': ['function_points_empty',
                  'The table has no points: at least one (normal stress, '
                  'shear strength) point is needed.'],
 'points.negative': ['function_points_strength',
                     'Point 2: the shear strength must be zero or more, got '
                     '-2.5.'],
 'points.not_finite': ['function_points_not_points',
                       'Point 1 holds a value that is not finite.'],
 'points.not_list': ['function_points_not_points',
                     'The table must be a list of (normal stress, shear '
                     'strength) points.'],
 'points.not_two': ['function_points_not_points',
                    'Point 2 is not two numbers (normal stress, shear '
                    'strength): (1, 2, 3).'],
 'points.order': ['function_points_order',
                  'The normal stresses must increase strictly: point 3 (40) '
                  'does not exceed point 2 (50).'],
 'snowden.ab': ['snowden_ab',
                'A1 and B1 must satisfy 0 <= A1 <= B1 <= 90 degrees; got A1 '
                '= 30, B1 = 10.'],
 'snowden.ab2': ['snowden_ab',
                 'A2 and B2 must satisfy 0 <= A2 <= B2 <= 90 degrees; got A2 '
                 '= -5, B2 = 10.'],
 'snowden.bedding_table': ['snowden_bedding',
                           'The bedding strength function: The table has no '
                           'rows: at least one (normal stress, cohesion, '
                           'friction angle) row is needed.'],
 'snowden.cannot_build': ['snowden_rock_mass',
                          'The rock mass strength function: the rock mass '
                          'function cannot be built: ValueError: not enough '
                          'values to unpack (expected 3, got 1).'],
 'snowden.cannot_build_bedding': ['snowden_bedding',
                                  'The bedding strength function: the '
                                  'bedding function cannot be built: '
                                  "TypeError: 'int' object is not iterable."],
 'snowden.not_a_function': ['snowden_bedding',
                            'The bedding strength function: the bedding '
                            'function must be a Shear/Normal Function or a '
                            "C/Phi Function, got {'model_id': "
                            "'mohr_coulomb', 'params': {}}."],
 'snowden.not_a_function_rock': ['snowden_rock_mass',
                                 'The rock mass strength function: the rock '
                                 'mass function must be a Shear/Normal '
                                 "Function or a C/Phi Function, got 'no "
                                 "function'."],
 'snowden.not_function': ['snowden_bedding',
                          'The bedding strength function: Mohr-Coulomb is '
                          'not a shear-normal or a C/Phi function.'],
 'snowden.rock_mass_table': ['snowden_rock_mass',
                             'The rock mass strength function: Point 1: the '
                             'shear strength must be zero or more, got -1.'],
 'surface.in_use': ['surface_in_use',
                    'The anisotropic surface is read by the joints of '
                    "'Jointed rock'; change them first."],
 'surface.legacy': ['generalized_surface_legacy',
                    "The Generalized Anisotropic material 'Old bedded rock' "
                    'links an anisotropic surface. Its angle ranges are '
                    'ABSOLUTE slice base inclinations, measured from the '
                    'horizontal, as the reference defines this input; until '
                    "0.1.225 OGR subtracted the surface's bedding from the "
                    'base angle first, so the same ranges would now select '
                    'other rules. Open the material, review the ranges as '
                    'absolute inclinations and accept it: the link is '
                    'removed.'],
 'surface.missing': ['generalized_surface_missing',
                     "Material 'Jointed rock', Generalized Anisotropic: "
                     'joint 1 names an anisotropic surface that is not in '
                     'the model.']}

# ======================================================================
# The inputs: each case calls one rule on one bad input.
# ======================================================================
from types import SimpleNamespace as _NS


def _rules():
    import ogr_core.project.rules as R
    return R


def _model(model_id, **attrs):
    """A real strength model of ``model_id`` with ``attrs`` set on it."""
    from ogr_core.materials import REGISTRY
    m = REGISTRY.get(model_id)()
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


def _discrete(**attrs):
    base = dict(function_type="drained", method="tin", points=[])
    base.update(attrs)
    from ogr_core.materials.builtin_models import DiscreteFunction
    return _NS(FUNCTION_TYPES=DiscreteFunction.FUNCTION_TYPES,
               METHODS=DiscreteFunction.METHODS, **base)


def _gen(**attrs):
    """A Generalized Anisotropic model by Angle or Surface."""
    m = _model("generalized_anisotropic")
    m.input_type = "angle_or_surface"
    m.definition = "angle"
    m.mapping = "ab"
    m.joint_selection = m.JOINT_SELECTIONS[0]
    m.use_base_if_weaker = False
    m.base = {"model": {"model_id": "mohr_coulomb",
                        "params": {"cohesion": 5.0, "friction_angle": 30.0}}}
    m.joints = [{"angle": 30.0, "A": 5.0, "B": 20.0,
                 "model": {"model_id": "mohr_coulomb",
                           "params": {"cohesion": 1.0,
                                      "friction_angle": 20.0}}}]
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


_MC = {"model_id": "mohr_coulomb",
       "params": {"cohesion": 5.0, "friction_angle": 30.0}}


def _rule(a, b, model=_MC):
    return {"angle_min": a, "angle_max": b, "model": model}


def _snowden_with(**functions):
    m = _model("snowden_anisotropic_linear")
    for k, v in functions.items():
        setattr(m, k, v)
    return m


def _materials():
    """Three materials: a plain one, a Generalized Anisotropic one whose
    rules link the others, and a second Generalized one."""
    from ogr_core.materials import Material
    plain = Material(name="Sand", strength=_model("mohr_coulomb"))
    gen = Material(name="Bedded rock", strength=_model(
        "generalized_anisotropic", rules=[_rule(-90, 0), _rule(0, 90)]))
    other = Material(name="Other rock", strength=_model(
        "generalized_anisotropic", rules=[_rule(-90, 90)]))
    return plain, gen, other


def _link(target):
    plain, gen, other = _materials()
    gen.strength.rules[1]["material_id"] = {"plain": plain, "self": gen,
                                            "other": other,
                                            "missing": None}[target] \
        .id if target != "missing" else "no-such-id"
    return gen, [plain, gen, other]


def _surfaces():
    from ogr_core.materials import Material
    return Material(name="Jointed rock", strength=_gen(
        definition="surface",
        joints=[{"surface_id": "s-gone", "A": 1, "B": 2, "model": _MC}]))


def _snowden(**params):
    m = _model("snowden_anisotropic_linear")
    m.params.update(params)
    return m


CASES = [
    # --- the points of a shear-normal or step function -----------------------
    ("points.not_list", lambda: _rules().function_points_refusal(5)),
    ("points.empty", lambda: _rules().function_points_refusal([])),
    ("points.not_two", lambda: _rules().function_points_refusal(
        [(0, 1), (1, 2, 3)])),
    ("points.not_finite", lambda: _rules().function_points_refusal(
        [(0, float("nan"))])),
    ("points.negative", lambda: _rules().function_points_refusal(
        [(0, 1), (10, -2.5)])),
    ("points.order", lambda: _rules().function_points_refusal(
        [(0, 1), (50, 20), (40, 30)])),
    # --- the discrete function ----------------------------------------------------
    ("discrete.type", lambda: _rules().discrete_function_refusal(
        _discrete(function_type="wet"))),
    ("discrete.method", lambda: _rules().discrete_function_refusal(
        _discrete(method="spline"))),
    ("discrete.not_list", lambda: _rules().discrete_function_refusal(
        _discrete(points=7))),
    ("discrete.empty", lambda: _rules().discrete_function_refusal(
        _discrete(points=[]))),
    ("discrete.empty_undrained", lambda: _rules().discrete_function_refusal(
        _discrete(function_type="undrained", points=[]))),
    ("discrete.not_point", lambda: _rules().discrete_function_refusal(
        _discrete(points=[(0, 0, 5)]))),
    ("discrete.not_finite", lambda: _rules().discrete_function_refusal(
        _discrete(points=[(0, 0, float("inf"), 30)]))),
    ("discrete.cohesion", lambda: _rules().discrete_function_refusal(
        _discrete(points=[(0, 0, -1.5, 30)]))),
    ("discrete.angle", lambda: _rules().discrete_function_refusal(
        _discrete(points=[(0, 0, 5, 95)]))),
    ("discrete.repeated", lambda: _rules().discrete_function_refusal(
        _discrete(points=[(1.5, 2, 5, 30), (1.5, 2, 6, 31)]))),
    # --- the C/Phi function ----------------------------------------------------------
    ("cphi.not_list", lambda: _rules().c_phi_rows_refusal(3)),
    ("cphi.empty", lambda: _rules().c_phi_rows_refusal([])),
    ("cphi.not_three", lambda: _rules().c_phi_rows_refusal([(0, 1)])),
    ("cphi.not_finite", lambda: _rules().c_phi_rows_refusal(
        [(0, float("nan"), 30)])),
    ("cphi.strength", lambda: _rules().c_phi_rows_refusal([(0, -2, 30)])),
    ("cphi.order", lambda: _rules().c_phi_rows_refusal(
        [(0, 5, 30), (100, 6, 31), (90, 7, 32)])),
    # --- the anisotropic strength function ---------------------------------------------
    ("aniso.not_list", lambda: _rules().anisotropic_function_rows_refusal(4)),
    ("aniso.empty", lambda: _rules().anisotropic_function_rows_refusal([])),
    ("aniso.not_three", lambda: _rules().anisotropic_function_rows_refusal(
        [(10, 5)])),
    ("aniso.not_finite", lambda: _rules().anisotropic_function_rows_refusal(
        [(10, float("nan"), 30)])),
    ("aniso.strength", lambda: _rules().anisotropic_function_rows_refusal(
        [(90, 5, 120)])),
    ("aniso.start", lambda: _rules().anisotropic_function_rows_refusal(
        [(-90, 5, 30), (90, 5, 30)])),
    ("aniso.order", lambda: _rules().anisotropic_function_rows_refusal(
        [(10, 5, 30), (5, 5, 30), (90, 5, 30)])),
    ("aniso.end", lambda: _rules().anisotropic_function_rows_refusal(
        [(10, 5, 30), (80.5, 5, 30)])),
    # --- Snowden ----------------------------------------------------------------------------
    ("snowden.ab", lambda: _rules().snowden_refusal(_snowden(A1=30, B1=10))),
    ("snowden.ab2", lambda: _rules().snowden_refusal(_snowden(A2=-5, B2=10))),
    ("snowden.bedding_table", lambda: _rules().snowden_refusal(_snowden_with(
        bedding={"model_id": "c_phi_function", "params": {}, "rows": []}))),
    ("snowden.rock_mass_table", lambda: _rules().snowden_refusal(_snowden_with(
        rock_mass={"model_id": "shear_normal_function", "params": {},
                   "points": [[0.0, -1.0]]}))),
    ("snowden.not_a_function", lambda: _rules().snowden_refusal(_snowden_with(
        bedding={"model_id": "mohr_coulomb", "params": {}}))),
    ("snowden.not_a_function_rock", lambda: _rules().snowden_refusal(
        _snowden_with(rock_mass="no function"))),
    ("snowden.cannot_build_bedding", lambda: _rules().snowden_refusal(
        _snowden_with(bedding={"model_id": "shear_normal_function",
                               "params": {}, "points": 4}))),
    ("snowden.not_function", lambda: _rules().snowden_refusal(_NS(
        params={"A1": 0.0, "B1": 10.0, "A2": 0.0, "B2": 10.0},
        function=lambda which: _NS(DISPLAY_NAME="Mohr-Coulomb")))),
    ("snowden.cannot_build", lambda: _rules().snowden_refusal(_snowden_with(
        rock_mass={"model_id": "c_phi_function", "params": {},
                   "rows": "not rows"}))),
    # --- the linear anisotropic model ----------------------------------------------------------
    ("aniso_linear.ab", lambda: _rules().anisotropic_linear_refusal(
        _NS(params={"A": 40.0, "B": 10.0}))),
    # --- the Generalized Anisotropic rules ---------------------------------------------------------
    ("gen.not_list", lambda: _rules().generalized_anisotropic_rules_refusal(9)),
    ("gen.empty", lambda: _rules().generalized_anisotropic_rules_refusal([])),
    ("gen.not_rule", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, 0), "rule"])),
    ("gen.angles_nan", lambda: _rules().generalized_anisotropic_rules_refusal(
        [{"angle_min": "a", "angle_max": 90, "model": _MC}])),
    ("gen.angles", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, -95.5)])),
    ("gen.start", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-80, 90)])),
    ("gen.gap", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, 0), _rule(10.5, 90)])),
    ("gen.overlap", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, 20), _rule(10, 90)])),
    ("gen.end", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, 45)])),
    ("gen.no_model", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, 90, model=None)])),
    ("gen.model_error", lambda: _rules().generalized_anisotropic_rules_refusal(
        [_rule(-90, 90, model={"model_id": "no_such_model"})])),
    # --- by Angle or Surface ----------------------------------------------------------------------------
    ("aos.definition", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(definition="plane"))),
    ("aos.mapping", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(mapping="tangent"))),
    ("aos.selection", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joint_selection="any"))),
    ("aos.base_if_weaker", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(use_base_if_weaker=1))),
    ("aos.base", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(base={}))),
    ("aos.joints", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joints=[]))),
    ("aos.joint_model", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joints=[{"angle": 30.0}]))),
    ("aos.joint_surface", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(definition="surface", joints=[{"model": _MC}]))),
    ("aos.joint_angle", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joints=[{"angle": "steep", "A": 1, "B": 2, "model": _MC}]))),
    ("aos.ab", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joints=[{"angle": 10.0, "A": 50, "B": "x", "model": _MC}]))),
    ("aos.model_error_base",
     lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(base={"model": {"model_id": "no_such_model"}}))),
    ("aos.model_error", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joints=[{"angle": 10.0, "A": 1, "B": 2,
                      "model": {"model_id": "no_such_model"}}]))),
    ("aos.nested_base", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(base={"model": {"model_id": "generalized_anisotropic"}}))),
    ("aos.nested_joint", lambda: _rules().generalized_angle_or_surface_refusal(
        _gen(joints=[{"angle": 10.0, "A": 1, "B": 2,
                      "model": {"model_id": "generalized_anisotropic"}}]))),
    # --- the links and the surfaces of a Generalized Anisotropic material ------
    ("link.missing", lambda: _rules().generalized_links_refusal(*_link("missing"))),
    ("link.self", lambda: _rules().generalized_links_refusal(*_link("self"))),
    ("link.generalized", lambda: _rules().generalized_links_refusal(
        *_link("other"))),
    ("surface.missing", lambda: _rules().generalized_surfaces_refusal(
        _surfaces(), _NS(boundaries=[]))),
    ("surface.in_use", lambda: _rules().surface_in_use_refusal(
        _NS(materials=[_surfaces()]), "s-gone")),
    ("surface.legacy", lambda: _rules().material_surface_refusal(_NS(
        name="Old bedded rock", anisotropic_surface_id="s1",
        strength=_model("generalized_anisotropic")))),
    # --- the frame, through strength_model_refusal ----------------------------------------------------------
    ("frame.shear_normal", lambda: _rules().strength_model_refusal(
        _model("shear_normal_function", points=[]), "Clay")),
    ("frame.step", lambda: _rules().strength_model_refusal(
        _model("step_function", points=[(0, 1), (0, 2)]), "Silt")),
    ("frame.discrete", lambda: _rules().strength_model_refusal(
        _model("discrete_function", points=[]), "Fill")),
    ("frame.c_phi", lambda: _rules().strength_model_refusal(
        _model("c_phi_function", rows=[]), "Marl")),
    ("frame.aniso_function", lambda: _rules().strength_model_refusal(
        _model("anisotropic_strength_function", rows=[]), "Shale")),
    ("frame.aniso_legacy", lambda: _rules().strength_model_refusal(
        _model("anisotropic_strength_function", legacy_points=[(0, 1)]),
        "Old shale")),
    ("frame.aniso_linear", lambda: _rules().strength_model_refusal(
        _model("anisotropic_linear", params={"A": 40.0, "B": 10.0}),
        "Slate")),
    ("frame.snowden_legacy", lambda: _rules().strength_model_refusal(
        _model("snowden_anisotropic_linear", legacy_params={"c1": 1.0}),
        "Old schist")),
    ("frame.snowden_ab", lambda: _rules().strength_model_refusal(
        _snowden(A1=30, B1=10), "Schist")),
    ("frame.generalized_rules", lambda: _rules().strength_model_refusal(
        _model("generalized_anisotropic", rules=[]), "Rock")),
    ("frame.generalized_input", lambda: _rules().strength_model_refusal(
        _model("generalized_anisotropic", input_type="sideways"), "Rock")),
    ("frame.generalized_water", lambda: _rules().strength_model_refusal(
        _model("generalized_anisotropic",
               rules=[_rule(-90, 90)], use_parent_water="yes"), "Rock")),
    ("frame.generalized_aos", lambda: _rules().strength_model_refusal(
        _gen(joints=[]), "Jointed rock")),
]


def _walk(code, args, seen):
    seen.add(code)
    for v in (args or {}).values():
        if isinstance(v, dict) and v.get("code") and "args" in v:
            _walk(v["code"], v["args"], seen)


_F = string.Formatter()


def _fields(t):
    return sorted({f for _t, f, _s, _c in _F.parse(t) if f})


# ======================================================================
class TestTheEnglishIsTheOldOne:

    def test_every_input_gives_the_v0_1_350_sentence(self):
        assert sorted(dict(CASES)) == sorted(_V1350)
        for cid, fn in CASES:
            why = fn()
            code, sentence = _V1350[cid]
            assert why is not None, cid
            assert why.code == code, (cid, why.code)
            assert why.message == sentence, cid
            assert getattr(why.message, "code", ""), cid

    def test_every_code_is_reached(self):
        from ogr_core.project.messages import STRENGTH_REFUSALS
        seen = set()
        for _cid, fn in CASES:
            m = fn().message
            _walk(m.code, m.args, seen)
        # "Rule n" capitalised: the check by Angle or Surface walks the base
        # and the joints only, so no input reaches it; the labels are held
        # to the model's own words below
        missing = set(STRENGTH_REFUSALS) - seen
        assert missing == {"strength.child_cap.rules"}, missing

    def test_the_labels_are_the_models_words(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.project.messages import child_label
        for key in (("rules", 1), ("base", None), ("joints", 0)):
            words = GeneralizedAnisotropic.child_label(key)
            assert child_label(key)["text"] == words, key
            assert child_label(key, capital=True)["text"] == \
                words.capitalize(), key


#: A template field left unfilled. Not any brace: a refused value may be a
#: dict, and its repr is part of the sentence in both languages.
_UNFILLED = re.compile(r"\{[a-z_]+(?:[:!][^}]*)?\}")


class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_core.project.messages import STRENGTH_REFUSALS
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for code, spec in STRENGTH_REFUSALS.items():
            assert spec.english in es, (code, spec.english[:60])
            assert _fields(es[spec.english]) == _fields(spec.english), code
            assert es[spec.english] != spec.english, code

    def test_each_input_is_refused_in_spanish(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            for cid, fn in CASES:
                said = note_text(fn().message)
                assert said and said != _V1350[cid][1], cid
                # a field left unfilled, not a brace: a value may be a dict
                assert not _UNFILLED.search(said), (cid, said)
        finally:
            set_language(before)


# ======================================================================
_CODED = {
    "ogr_core/project/rules.py": (
        "anisotropic_function_rows_refusal", "function_points_refusal",
        "discrete_function_refusal", "c_phi_rows_refusal", "snowden_refusal",
        "generalized_anisotropic_rules_refusal",
        "generalized_angle_or_surface_refusal", "anisotropic_linear_refusal",
        "strength_model_refusal", "generalized_links_refusal",
        "generalized_surfaces_refusal", "surface_in_use_refusal",
        "material_surface_refusal"),
    "ogr_core/materials/builtin_models.py": ("function",),
}
#: The exception that a model raised, "TypeError: ...": data.
_DATA = '"%s: %s" % (type(exc).__name__, exc)'


class TestNoSentenceWithoutItsCode:

    def test_census(self):
        found = []
        for rel, names in _CODED.items():
            src = (_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            funcs = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.FunctionDef):
                    funcs.setdefault(n.name, n)
            for name in names:
                fn = funcs[name]
                if name == "function":
                    fn = next(n for n in ast.walk(tree)
                              if isinstance(n, ast.ClassDef)
                              and n.name == "SnowdenModifiedAnisotropicLinear")
                    fn = next(n for n in fn.body
                              if isinstance(n, ast.FunctionDef)
                              and n.name == "function")
                doc = (fn.body[0].value if isinstance(fn.body[0], ast.Expr)
                       else None)
                skip = set()
                for n in ast.walk(fn):
                    if n is not fn and isinstance(n, ast.FunctionDef):
                        skip.update(ast.walk(n))
                for n in ast.walk(fn):
                    if n is doc or n in skip:
                        continue
                    if ast.get_source_segment(src, n) == _DATA:
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
                          and len(n.value) > 40 and " " in n.value):
                        found.append((rel, name, n.lineno, "sentence"))
        assert not found, found


# ======================================================================
class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


class TestTheDialogSaysThemInSpanish:

    def test_its_table_of_fixed_sentences_is_gone(self):
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        assert not hasattr(MaterialPropertiesDialog, "_TABLE_REFUSALS")

    def test_a_refusal_with_its_values(self):
        from test_generalized_links_v1228 import TestTheDialog
        t = TestTheDialog()
        with _Spanish():
            dlg = t._dialog(t._materials(), 0)
            dlg.cbo_strength.setCurrentIndex(
                dlg.cbo_strength.findData("generalized_anisotropic"))
            dlg._ok()
            text = dlg.lbl_strength_problem.text()
        assert dlg.accepted_calls == []
        assert text.startswith("En el material G: la regla 1 enlaza "
                               "'Clay', otro material anisótropo "
                               "generalizado"), text
        assert "Generalized" not in text
