# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.437 (D414) -- Import Properties says what it changed, and Open says in
the reader's language what a file holds that this build does not know.

Invariants protected here:

* **The agent's English is 0.1.436's.** ``_V1436`` was written by 0.1.436
  (5d36030), measured by CALLING its functions on a ``git archive`` of that
  tree with THIS file's inputs (``_auditoria/P10_herramientas/capture_d414.py``
  of the bank runs :func:`_capture` there) -- not printed by this code: the
  type and the text of every refusal of the readers (an unknown support
  type, strength model or parameter -- of a model with parameters and of one
  without any --, boundary type, and a value of each of the twenty
  enumerations a ``.ogr`` holds, unknown, a number or null), the notes of
  Import Properties (a name with an apostrophe among them), and
  ``project_open`` / ``properties_import`` as the agent reads them. For a
  change of text the reference is what the old program said. Since 0.1.438
  (D422) the two operations have one reader, and a refusal of
  ``properties_import`` is the one ``project_open`` gave. The
  temporary folder is masked as ``<tmp>/`` whatever the system's separator:
  the CI runs on Linux.
* **Each code says it in Spanish**, with the fields of its English, and a
  value of the file as the file holds it: between «», ``null`` for null.
* **The window says it**, by its real handlers, with the file dialog, the
  item dialog and the message boxes replaced and put back: Import
  Properties puts its notes in Analysis Notes (read from the panel itself)
  and counts them in the status bar (the owner's decision, 2026-11-11: a
  material that used the other project's water table arrives dry, which
  moves the factor of safety, and the window said nothing); the notes of
  the imports of a project ADD UP, and undoing an import takes its own away
  (the owner's decision in the review of 0.1.437); at the limit of
  materials, the note says why none came; Open and Import name what a file
  holds that this build does not know, without the quotes of a
  ``KeyError``'s repr -- in Spanish, and in English by the same rules, which
  is a declared change of the window's English (the agent's does not move).
* **The censuses see the paths:** no note of ``properties_import.py`` is a
  sentence built in place, and every call of an enumeration in a reader of
  ``ogr_core`` / ``ogr_fem2d`` / ``ogr_slip2d`` -- the enumerations found by
  the census itself, not listed here -- goes through ``read_enum`` or says
  its code; the readers that put a default in place of a value they do not
  know are the known ones, left to D429. Each census checks itself on a
  source of its own.

One main window for the whole file, given a fresh project by each test that
changes it; no search, no modal dialog left open.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import re
import string
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _HAS_QT = True
except Exception:  # pragma: no cover
    _HAS_QT = False


def _requires_qt(obj):
    """A class (or a method) that needs Qt; without it, nothing to run."""
    if _HAS_QT:
        return obj
    return type(obj.__name__, (), {}) if isinstance(obj, type) else None


class _Language:
    """The interface in ``code`` for the block, and back after it (rule 5)."""

    def __init__(self, code):
        self.code = code

    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language(self.code)

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


# ======================================================================
# 0.1.436's English, measured on its tree (see the module docstring)
# ======================================================================
_V1436 = {'agent project_open boundary type': ['InvalidArgument',
                                      '[E_INVALID_ARGUMENT] <tmp>/bad '
                                      'boundary type.ogr is not a readable '
                                      ".ogr file: KeyError: 'FUTURE'"],
 'agent project_open parameter': ['InvalidArgument',
                                  '[E_INVALID_ARGUMENT] <tmp>/bad '
                                  'parameter.ogr is not a readable .ogr file: '
                                  'ValueError: mohr_coulomb: unknown '
                                  "parameter 'future_param'. Valid: "
                                  "['cohesion', 'friction_angle']"],
 'agent project_open pore pressure': ['InvalidArgument',
                                      '[E_INVALID_ARGUMENT] <tmp>/bad pore '
                                      'pressure.ogr is not a readable .ogr '
                                      "file: ValueError: 'future_value' is "
                                      'not a valid PorePressureType'],
 'agent project_open strength model': ['InvalidArgument',
                                       '[E_INVALID_ARGUMENT] <tmp>/bad '
                                       'strength model.ogr is not a readable '
                                       '.ogr file: KeyError: "Unknown '
                                       "strength model: 'future_model'. "
                                       "Available: ['mohr_coulomb', "
                                       "'undrained', 'infinite_strength', "
                                       "'no_strength', 'hoek_brown', "
                                       "'hoek_brown_classic', 'power_curve', "
                                       "'hyperbolic', "
                                       "'vertical_stress_ratio', "
                                       "'barton_bandis', 'drained_undrained', "
                                       "'anisotropic_linear', "
                                       "'shear_normal_function', "
                                       "'step_function', 'discrete_function', "
                                       "'c_phi_function', 'shansep', "
                                       "'anisotropic_strength_function', "
                                       "'generalized_anisotropic', "
                                       "'snowden_anisotropic_linear', "
                                       "'undrained_depth_layer', "
                                       "'undrained_depth_datum', "
                                       '\'undrained_slope_distance\']"'],
 'agent project_open support type': ['InvalidArgument',
                                     '[E_INVALID_ARGUMENT] <tmp>/bad support '
                                     'type.ogr is not a readable .ogr file: '
                                     "KeyError: 'Unknown support type: "
                                     "future_nail'"],
 'agent properties_import': ['json',
                             '{"materials": ["Silty clay (2)", "O\'Neil", '
                             '"Sand", "Lost", "Ranges", "Joints"], "notes": '
                             '["\'Silty clay (2)\' used a water surface of '
                             'the other project; assign one of this model to '
                             'it.", "\\"O\'Neil\\" lost its anisotropic '
                             'surface, which belonged to the other '
                             'project."], "skipped": [], "support_types": '
                             '[]}'],
 'agent properties_import boundary type': ['InvalidArgument',
                                           '[E_INVALID_ARGUMENT] <tmp>/bad '
                                           'boundary type.ogr is not a '
                                           "readable .ogr file: 'FUTURE'"],
 'agent properties_import parameter': ['InvalidArgument',
                                       '[E_INVALID_ARGUMENT] <tmp>/bad '
                                       'parameter.ogr is not a readable .ogr '
                                       'file: mohr_coulomb: unknown parameter '
                                       "'future_param'. Valid: ['cohesion', "
                                       "'friction_angle']"],
 'agent properties_import pore pressure': ['InvalidArgument',
                                           '[E_INVALID_ARGUMENT] <tmp>/bad '
                                           'pore pressure.ogr is not a '
                                           'readable .ogr file: '
                                           "'future_value' is not a valid "
                                           'PorePressureType'],
 'agent properties_import strength model': ['InvalidArgument',
                                            '[E_INVALID_ARGUMENT] <tmp>/bad '
                                            'strength model.ogr is not a '
                                            'readable .ogr file: "Unknown '
                                            "strength model: 'future_model'. "
                                            "Available: ['mohr_coulomb', "
                                            "'undrained', "
                                            "'infinite_strength', "
                                            "'no_strength', 'hoek_brown', "
                                            "'hoek_brown_classic', "
                                            "'power_curve', 'hyperbolic', "
                                            "'vertical_stress_ratio', "
                                            "'barton_bandis', "
                                            "'drained_undrained', "
                                            "'anisotropic_linear', "
                                            "'shear_normal_function', "
                                            "'step_function', "
                                            "'discrete_function', "
                                            "'c_phi_function', 'shansep', "
                                            "'anisotropic_strength_function', "
                                            "'generalized_anisotropic', "
                                            "'snowden_anisotropic_linear', "
                                            "'undrained_depth_layer', "
                                            "'undrained_depth_datum', "
                                            '\'undrained_slope_distance\']"'],
 'agent properties_import support type': ['InvalidArgument',
                                          '[E_INVALID_ARGUMENT] <tmp>/bad '
                                          'support type.ogr is not a readable '
                                          ".ogr file: 'Unknown support type: "
                                          "future_nail'"],
 'import at the maximum': ['json',
                           '{"materials": [], "notes": ["6 material(s) not '
                           'imported: the model already has the maximum of '
                           '1."], "skipped": ["Silty clay", "O\'Neil", '
                           '"Sand", "Lost", "Ranges", "Joints"], '
                           '"support_types": []}'],
 'import note 0': ['note',
                   "'Silty clay' used a water surface of the other project; "
                   'assign one of this model to it.'],
 'import note 1': ['note',
                   '"O\'Neil" lost its anisotropic surface, which belonged to '
                   'the other project.'],
 'import note 2': ['note',
                   "'Ranges': range 2 now takes the strength of 'sand', the "
                   'material of that name in this model.'],
 'import note 3': ['note',
                   "'Ranges': range 3 linked a material this model cannot "
                   'link; it keeps the strength it had, unlinked.'],
 'import note 4': ['note',
                   "'Joints': the base now takes the strength of 'sand', the "
                   'material of that name in this model.'],
 'import note 5': ['note',
                   "'Joints': joint 1 linked a material this model cannot "
                   'link; it keeps the strength it had, unlinked.'],
 'read AnnotationKind null': ['ValueError',
                              'None is not a valid AnnotationKind'],
 'read AnnotationKind number': ['ValueError',
                                '7 is not a valid AnnotationKind'],
 'read AnnotationKind unknown': ['ValueError',
                                 "'future_value' is not a valid "
                                 'AnnotationKind'],
 'read BCType null': ['ValueError', 'None is not a valid BCType'],
 'read BCType number': ['ValueError', '7 is not a valid BCType'],
 'read BCType unknown': ['ValueError', "'future_value' is not a valid BCType"],
 'read BlockObjectKind null': ['ValueError',
                               'None is not a valid BlockObjectKind'],
 'read BlockObjectKind number': ['ValueError',
                                 '7 is not a valid BlockObjectKind'],
 'read BlockObjectKind unknown': ['ValueError',
                                  "'future_value' is not a valid "
                                  'BlockObjectKind'],
 'read BoundaryType null': ['KeyError', 'None'],
 'read BoundaryType number': ['KeyError', '7'],
 'read BoundaryType unknown': ['KeyError', "'future_value'"],
 'read DistributionType null': ['ValueError',
                                'None is not a valid DistributionType'],
 'read DistributionType number': ['ValueError',
                                  '7 is not a valid DistributionType'],
 'read DistributionType unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'DistributionType'],
 'read FailureDirection null': ['ValueError',
                                'None is not a valid FailureDirection'],
 'read FailureDirection number': ['ValueError',
                                  '7 is not a valid FailureDirection'],
 'read FailureDirection unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'FailureDirection'],
 'read FocusKind null': ['ValueError', 'None is not a valid FocusKind'],
 'read FocusKind number': ['ValueError', '7 is not a valid FocusKind'],
 'read FocusKind unknown': ['ValueError',
                            "'future_value' is not a valid FocusKind"],
 'read ForceApplication null': ['NOT RAISED', ''],
 'read ForceApplication number': ['ValueError',
                                  '7 is not a valid ForceApplication'],
 'read ForceApplication unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'ForceApplication'],
 'read ForceOrientation null': ['NOT RAISED', ''],
 'read ForceOrientation number': ['ValueError',
                                  '7 is not a valid ForceOrientation'],
 'read ForceOrientation unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'ForceOrientation'],
 'read GridValueType null': ['NOT RAISED', ''],
 'read GridValueType number': ['ValueError', '7 is not a valid GridValueType'],
 'read GridValueType unknown': ['ValueError',
                                "'future_value' is not a valid GridValueType"],
 'read LoadAction null': ['ValueError', 'None is not a valid LoadAction'],
 'read LoadAction number': ['ValueError', '7 is not a valid LoadAction'],
 'read LoadAction unknown': ['ValueError',
                             "'future_value' is not a valid LoadAction"],
 'read LoadAction(line) null': ['ValueError',
                                'None is not a valid LoadAction'],
 'read LoadAction(line) number': ['ValueError', '7 is not a valid LoadAction'],
 'read LoadAction(line) unknown': ['ValueError',
                                   "'future_value' is not a valid LoadAction"],
 'read LoadDistribution null': ['ValueError',
                                'None is not a valid LoadDistribution'],
 'read LoadDistribution number': ['ValueError',
                                  '7 is not a valid LoadDistribution'],
 'read LoadDistribution unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'LoadDistribution'],
 'read LoadOrientation null': ['ValueError',
                               'None is not a valid LoadOrientation'],
 'read LoadOrientation number': ['ValueError',
                                 '7 is not a valid LoadOrientation'],
 'read LoadOrientation unknown': ['ValueError',
                                  "'future_value' is not a valid "
                                  'LoadOrientation'],
 'read LoadOrientation(line) null': ['ValueError',
                                     'None is not a valid LoadOrientation'],
 'read LoadOrientation(line) number': ['ValueError',
                                       '7 is not a valid LoadOrientation'],
 'read LoadOrientation(line) unknown': ['ValueError',
                                        "'future_value' is not a valid "
                                        'LoadOrientation'],
 'read PermeabilityUnit null': ['ValueError',
                                'None is not a valid PermeabilityUnit'],
 'read PermeabilityUnit number': ['ValueError',
                                  '7 is not a valid PermeabilityUnit'],
 'read PermeabilityUnit unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'PermeabilityUnit'],
 'read PolylinePointMode null': ['ValueError',
                                 'None is not a valid PolylinePointMode'],
 'read PolylinePointMode number': ['ValueError',
                                   '7 is not a valid PolylinePointMode'],
 'read PolylinePointMode unknown': ['ValueError',
                                    "'future_value' is not a valid "
                                    'PolylinePointMode'],
 'read PorePressureType null': ['ValueError',
                                'None is not a valid PorePressureType'],
 'read PorePressureType number': ['ValueError',
                                  '7 is not a valid PorePressureType'],
 'read PorePressureType unknown': ['ValueError',
                                   "'future_value' is not a valid "
                                   'PorePressureType'],
 'read SimpleSoilType null': ['ValueError',
                              'None is not a valid SimpleSoilType'],
 'read SimpleSoilType number': ['ValueError',
                                '7 is not a valid SimpleSoilType'],
 'read SimpleSoilType unknown': ['ValueError',
                                 "'future_value' is not a valid "
                                 'SimpleSoilType'],
 'read StrengthModel null': ['KeyError',
                             '"Unknown strength model: \'None\'. Available: '
                             "['mohr_coulomb', 'undrained', "
                             "'infinite_strength', 'no_strength', "
                             "'hoek_brown', 'hoek_brown_classic', "
                             "'power_curve', 'hyperbolic', "
                             "'vertical_stress_ratio', 'barton_bandis', "
                             "'drained_undrained', 'anisotropic_linear', "
                             "'shear_normal_function', 'step_function', "
                             "'discrete_function', 'c_phi_function', "
                             "'shansep', 'anisotropic_strength_function', "
                             "'generalized_anisotropic', "
                             "'snowden_anisotropic_linear', "
                             "'undrained_depth_layer', "
                             "'undrained_depth_datum', "
                             '\'undrained_slope_distance\']"'],
 'read StrengthModel number': ['KeyError',
                               '"Unknown strength model: \'7\'. Available: '
                               "['mohr_coulomb', 'undrained', "
                               "'infinite_strength', 'no_strength', "
                               "'hoek_brown', 'hoek_brown_classic', "
                               "'power_curve', 'hyperbolic', "
                               "'vertical_stress_ratio', 'barton_bandis', "
                               "'drained_undrained', 'anisotropic_linear', "
                               "'shear_normal_function', 'step_function', "
                               "'discrete_function', 'c_phi_function', "
                               "'shansep', 'anisotropic_strength_function', "
                               "'generalized_anisotropic', "
                               "'snowden_anisotropic_linear', "
                               "'undrained_depth_layer', "
                               "'undrained_depth_datum', "
                               '\'undrained_slope_distance\']"'],
 'read StrengthModel unknown': ['KeyError',
                                '"Unknown strength model: \'future_value\'. '
                                "Available: ['mohr_coulomb', 'undrained', "
                                "'infinite_strength', 'no_strength', "
                                "'hoek_brown', 'hoek_brown_classic', "
                                "'power_curve', 'hyperbolic', "
                                "'vertical_stress_ratio', 'barton_bandis', "
                                "'drained_undrained', 'anisotropic_linear', "
                                "'shear_normal_function', 'step_function', "
                                "'discrete_function', 'c_phi_function', "
                                "'shansep', 'anisotropic_strength_function', "
                                "'generalized_anisotropic', "
                                "'snowden_anisotropic_linear', "
                                "'undrained_depth_layer', "
                                "'undrained_depth_datum', "
                                '\'undrained_slope_distance\']"'],
 'read SupportType null': ['KeyError', "'Unknown support type: None'"],
 'read SupportType number': ['KeyError', "'Unknown support type: 7'"],
 'read SupportType unknown': ['KeyError',
                              "'Unknown support type: future_value'"],
 'read TimeUnit null': ['ValueError', 'None is not a valid TimeUnit'],
 'read TimeUnit number': ['ValueError', '7 is not a valid TimeUnit'],
 'read TimeUnit unknown': ['ValueError',
                           "'future_value' is not a valid TimeUnit"],
 'read UnitSystem null': ['ValueError', 'None is not a valid UnitSystem'],
 'read UnitSystem number': ['ValueError', '7 is not a valid UnitSystem'],
 'read UnitSystem unknown': ['ValueError',
                             "'future_value' is not a valid UnitSystem"],
 'read VariableKind null': ['ValueError', 'None is not a valid VariableKind'],
 'read VariableKind number': ['ValueError', '7 is not a valid VariableKind'],
 'read VariableKind unknown': ['ValueError',
                               "'future_value' is not a valid VariableKind"],
 'read WaterLevelMode null': ['ValueError',
                              'None is not a valid WaterLevelMode'],
 'read WaterLevelMode number': ['ValueError',
                                '7 is not a valid WaterLevelMode'],
 'read WaterLevelMode unknown': ['ValueError',
                                 "'future_value' is not a valid "
                                 'WaterLevelMode'],
 'read unknown parameter': ['ValueError',
                            "mohr_coulomb: unknown parameter 'future_param'. "
                            "Valid: ['cohesion', 'friction_angle']"],
 'read unknown parameter of a model without any': ['ValueError',
                                                   'infinite_strength: '
                                                   'unknown parameter '
                                                   "'future_param'. Valid: "
                                                   '[]']}

_TMP = tempfile.mkdtemp(prefix="ogr_d414_")
_UUID = re.compile(r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?"
                   r"[0-9a-f]{12}")
_HANDLE = re.compile(r"\b([pr])_[0-9a-f]{10}\b")


def _scrub(text):
    """Ids, handles and the temporary folder masked; the folder with a
    forward slash, so the table is the same on Windows and on Linux."""
    text = text.replace(_TMP + os.sep, "<tmp>/").replace(_TMP, "<tmp>")
    return _HANDLE.sub(r"\1_<h>", _UUID.sub("<id>", text))


def _rich():
    """The demo with what the readers read: a set and a support, two loads,
    a record, a focus point, a random variable, the hydraulic properties of
    a material, a seepage boundary condition, a pore pressure grid, an
    annotation and a block search polyline (the last boundary)."""
    from ogr_core.annotations.annotation import Annotation, AnnotationKind
    from ogr_core.fem.seepage_data import BCType, SeepageBoundaryConditions
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.geometry.block_object import (BlockObjectKind,
                                                BlockObjectSpec,
                                                PolylinePointMode)
    from ogr_core.geometry.boundary import Boundary, BoundaryType
    from ogr_core.geometry.focus import FocusObject
    from ogr_core.hydraulic.hydraulic_properties import HydraulicProperties
    from ogr_core.hydraulic.water_pressure_grid import WaterPressureGrid
    from ogr_core.loads.loads import DistributedLoad, LineLoad
    from ogr_core.loads.seismic_record import SeismicRecord
    from ogr_core.project.demo import build_demo_project
    from ogr_core.statistics import available_variables
    from ogr_core.support import GroutedTieback, SupportInstance
    p = build_demo_project()
    g = GroutedTieback()
    p.support_types = [g]
    p.supports = [SupportInstance(type_id="grouted_tieback", type_ref=g.id,
                                  name="S1", head=Vertex(30, 20),
                                  tail=Vertex(20, 15))]
    p.add_distributed_load(DistributedLoad(start=Vertex(5, 25),
                                           end=Vertex(20, 25),
                                           magnitude_1=20.0, name="Dist"))
    p.add_line_load(LineLoad(point=Vertex(10, 25), magnitude=50.0))
    p.seismic_records = [SeismicRecord(name="Rec", dt=0.01,
                                       accelerations=[0.0, 0.1, 0.0])]
    p.focus_objects = [FocusObject(points=[(20.0, 20.0)])]
    rv = next(v for v in available_variables(p) if v.param == "cohesion")
    p.random_variables = [rv]
    p.materials[0].hydraulic = HydraulicProperties()
    p.seepage_bcs = SeepageBoundaryConditions()
    p.seepage_bcs.add_node(0, BCType.TOTAL_HEAD, 10.0)
    p.water_pressure_grid = WaterPressureGrid(points=[(10.0, 10.0, 5.0)])
    p.annotations.add(Annotation(kind=AnnotationKind.LINE,
                                 points=[(0.0, 0.0), (5.0, 5.0)]))
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(10, 20), Vertex(20, 22), Vertex(30, 21)]),
        btype=BoundaryType.BLOCK_SEARCH_OBJECT,
        block_object=BlockObjectSpec(kind=BlockObjectKind.POLYLINE,
                                     left_point=PolylinePointMode.SEGMENT)))
    return p.to_dict()


#: where each enumeration (and the three refusals') is read, in ``_rich()``
_ENUMS = {
    "UnitSystem": ("settings", "units", "system"),
    "TimeUnit": ("settings", "units", "time"),
    "PermeabilityUnit": ("settings", "units", "permeability"),
    "FailureDirection": ("settings", "units", "failure_direction"),
    "PorePressureType": ("materials", 0, "pore_pressure"),
    "ForceApplication": ("supports", 0, "force_application"),
    "ForceOrientation": ("supports", 0, "orientation"),
    "WaterLevelMode": ("tension_crack_properties", "mode"),
    "LoadOrientation": ("distributed_loads", 0, "orientation"),
    "LoadAction": ("distributed_loads", 0, "action"),
    "LoadDistribution": ("distributed_loads", 0, "distribution"),
    "LoadOrientation(line)": ("line_loads", 0, "orientation"),
    "LoadAction(line)": ("line_loads", 0, "action"),
    "VariableKind": ("random_variables", 0, "kind"),
    "DistributionType": ("random_variables", 0, "distribution", "dist_type"),
    "FocusKind": ("focus_objects", 0, "kind"),
    "SimpleSoilType": ("materials", 0, "hydraulic", "simple_soil_type"),
    "BCType": ("seepage_bcs", "nodes", 0, "bc_type"),
    "GridValueType": ("water_pressure_grid", "value_type"),
    "AnnotationKind": ("annotations", 0, "kind"),
    "BlockObjectKind": ("boundaries", -1, "block_object", "kind"),
    "PolylinePointMode": ("boundaries", -1, "block_object", "left_point"),
    "BoundaryType": ("boundaries", 0, "type"),
    "SupportType": ("support_types", 0, "type_id"),
    "StrengthModel": ("materials", 0, "strength", "model_id"),
}
#: the three of ``_ENUMS`` that are not an enumeration read by ``read_enum``
_NOT_READ_ENUM = {"BoundaryType", "SupportType", "StrengthModel"}

_BASE: dict = {}


def _base():
    if not _BASE:
        _BASE.update(_rich())
    return _BASE


def _mutated(path, value):
    d = copy.deepcopy(_base())
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    return d


def _with_unknown_parameter(model=None):
    """``future_param`` in the strength of the first material; with
    ``model``, a strength of that model and no parameter of its own."""
    d = copy.deepcopy(_base())
    if model is not None:
        d["materials"][0]["strength"] = {"model_id": model, "params": {}}
    d["materials"][0]["strength"]["params"]["future_param"] = 1.0
    return d


def _source_with_everything():
    """A source for Import Properties with every note it writes: a material
    on a water table, one on an anisotropic surface (named with an
    apostrophe), a range relinked by name and one unlinked, a base relinked
    and a joint unlinked."""
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    from ogr_core.project.demo import build_demo_project
    src = build_demo_project()               # «Silty clay» uses its table
    clay = src.materials[0]
    oneil = Material(name="O'Neil", strength=MohrCoulomb(
        cohesion=1.0, friction_angle=30.0))
    oneil.anisotropic_surface_id = "gone"
    sand = Material(name="Sand", strength=MohrCoulomb(cohesion=0.0,
                                                      friction_angle=35.0))
    lost = Material(name="Lost", strength=MohrCoulomb(cohesion=2.0,
                                                      friction_angle=20.0))

    def link(m, **kw):
        return {"material_id": m.id, "model": m.strength.to_dict(), **kw}
    ranges = Material(name="Ranges", strength=GeneralizedAnisotropic(rules=[
        link(clay, angle_min=-90.0, angle_max=-10.0),
        link(sand, angle_min=-10.0, angle_max=10.0),
        link(lost, angle_min=10.0, angle_max=90.0)]))
    aos = Material(name="Joints", strength=GeneralizedAnisotropic(
        input_type="angle_or_surface", base=link(sand),
        joints=[link(lost, angle=0.0, A=10.0, B=10.0)], mapping="ab"))
    src.materials += [oneil, sand, lost, ranges, aos]
    return src


def _sand_destination():
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    dst = Project("destination")
    dst.materials = [Material(name="sand", strength=MohrCoulomb(
        cohesion=1.0, friction_angle=33.0))]
    return dst


_CAPTURED: dict = {}


def _capture() -> dict:
    """What :data:`_V1436` recorded, measured on this tree."""
    if _CAPTURED:
        return _CAPTURED
    from ogr_api import Workspace, call
    from ogr_core.project import Project
    from ogr_core.project.demo import build_demo_project
    from ogr_core.project.properties_import import import_properties
    # the base outside ``said``: a model that cannot be built is a fault of
    # this file, not a refusal of the tree
    _base()
    out = {}

    def said(name, fn):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            out[name] = [type(exc).__name__, _scrub(str(exc))]
            return
        out[name] = ["NOT RAISED", ""]

    for name, path in _ENUMS.items():
        for label, value in (("unknown", "future_value"), ("number", 7),
                             ("null", None)):
            said("read %s %s" % (name, label),
                 lambda path=path, value=value: Project.from_dict(
                     _mutated(path, value)))
    said("read unknown parameter",
         lambda: Project.from_dict(_with_unknown_parameter()))
    said("read unknown parameter of a model without any",
         lambda: Project.from_dict(_with_unknown_parameter(
             "infinite_strength")))
    ws = Workspace()
    try:
        target = call(ws, "project_new", template="demo")["project_id"]
        for name, path, value in (
                ("support type", _ENUMS["SupportType"], "future_nail"),
                ("strength model", _ENUMS["StrengthModel"], "future_model"),
                ("boundary type", _ENUMS["BoundaryType"], "FUTURE"),
                ("pore pressure", _ENUMS["PorePressureType"],
                 "future_value"),
                ("parameter", None, None)):
            data = (_mutated(path, value) if path is not None
                    else _with_unknown_parameter())
            f = os.path.join(_TMP, "bad %s.ogr" % name)
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            for op, kw in (("project_open", {"path": f}),
                           ("properties_import", {"project_id": target,
                                                  "path": f})):
                said("agent %s %s" % (op, name), lambda op=op, kw=kw: call(
                    ws, op, **kw))
        f = os.path.join(_TMP, "source.ogr")
        _source_with_everything().save(f)
        out["agent properties_import"] = ["json", _scrub(json.dumps(call(
            ws, "properties_import", project_id=target, path=f),
            sort_keys=True))]
    finally:
        ws.shutdown()
    rep = import_properties(_sand_destination(), _source_with_everything(),
                            support_types=False,
                            names=["Silty clay", "O'Neil", "Ranges",
                                   "Joints"])
    for i, n in enumerate(rep["notes"]):
        out["import note %d" % i] = ["note", _scrub(str(n))]
    full = build_demo_project()
    full.settings.max_materials = 1
    rep = import_properties(full, _source_with_everything(),
                            support_types=False)
    out["import at the maximum"] = ["json", _scrub(json.dumps(
        rep, sort_keys=True))]
    _CAPTURED.update(out)
    return _CAPTURED


def _refused(data):
    """The exception ``Project.from_dict(data)`` raises; that it raises one
    is part of what is checked."""
    from ogr_core.project import Project
    try:
        Project.from_dict(data)
    except (KeyError, ValueError) as exc:
        return exc
    raise AssertionError("the file was read")


# ======================================================================
class TestTheEnglishIsThatOf0436:

    def test_every_refusal_note_and_answer(self):
        now = _capture()
        assert sorted(now) == sorted(_V1436), sorted(set(now) ^ set(_V1436))
        assert len(_V1436) == 95
        for key, want in _V1436.items():
            if (key.startswith("agent properties_import ")
                    and key != "agent properties_import"):
                # v0.1.438 (D422): one reader for the two operations, so a
                # refusal of properties_import says what project_open says,
                # with the exception's type (0.1.436 left it out)
                want = _V1436[key.replace("properties_import",
                                          "project_open")]
            assert now[key] == want, (key, now[key], want)

    def test_the_exceptions_carry_the_codes(self):
        """The core's three raise their exception with a ``Coded``, which IS
        the sentence (``str(KeyError(c))`` is its repr, as before, while
        ``Coded`` has no repr of its own); Python's keep their own exception
        and text and carry ``code`` and ``values`` -- every enumeration of
        :data:`_ENUMS`, by the name of its class."""
        from ogr_core.file_messages import (BOUNDARY_TYPE_UNKNOWN,
                                            ENUM_UNKNOWN,
                                            PARAMETER_UNKNOWN,
                                            STRENGTH_MODEL_UNKNOWN,
                                            SUPPORT_TYPE_UNKNOWN)
        from ogr_core.messages import Coded
        assert Coded.__repr__ is str.__repr__
        for name, code in (("SupportType", SUPPORT_TYPE_UNKNOWN),
                           ("StrengthModel", STRENGTH_MODEL_UNKNOWN)):
            exc = _refused(_mutated(_ENUMS[name], "future_value"))
            assert isinstance(exc, KeyError), name
            assert exc.args[0].code == code, name
            assert str(exc) == repr(str(exc.args[0])), name
        for data in (_with_unknown_parameter(),
                     _with_unknown_parameter("infinite_strength")):
            exc = _refused(data)
            assert isinstance(exc, ValueError)
            assert exc.args[0].code == PARAMETER_UNKNOWN
        exc = _refused(_mutated(_ENUMS["BoundaryType"], "future_value"))
        assert isinstance(exc, KeyError)
        assert exc.code == BOUNDARY_TYPE_UNKNOWN
        assert exc.values == {"value": "future_value"}
        for name, path in _ENUMS.items():
            if name in _NOT_READ_ENUM:
                continue
            exc = _refused(_mutated(path, "future_value"))
            assert isinstance(exc, ValueError), name
            assert exc.code == ENUM_UNKNOWN, name
            assert exc.values == {"value": "future_value",
                                  "enum": name.split("(")[0]}, name
            assert not getattr(exc.args[0], "code", ""), name


# ======================================================================
def _fields(template):
    return sorted({f for _t, f, _s, _c in string.Formatter().parse(template)
                   if f})


class TestEachCodeSaysItInSpanish:

    def test_the_two_catalogues(self):
        from ogr_core.file_messages import FILE_MESSAGES
        from ogr_core.project.messages import IMPORT_NOTES
        from ogr_gui.core_messages import _catalogue
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for table in (FILE_MESSAGES, IMPORT_NOTES):
            for code, spec in table.items():
                assert code in _catalogue(), code
                assert spec.english in es, spec.english
                assert es[spec.english] != spec.english, code
                assert _fields(es[spec.english]) == _fields(spec.english), (
                    code)

    def test_the_notes_of_an_import(self):
        """The six notes the capture's import writes, in Spanish: a range by
        «el rango», the base and a joint by the words of the strength
        refusals, a name between «» and not between the quotes of its
        repr."""
        from ogr_core.project.properties_import import import_properties
        from ogr_gui.core_messages import note_text
        dst = _sand_destination()
        rep = import_properties(dst, _source_with_everything(),
                                support_types=False,
                                names=["Silty clay", "O'Neil", "Ranges",
                                       "Joints"])
        with _Language("es"):
            said = [note_text(n, project=dst) for n in rep["notes"]]
        assert said == [
            "«Silty clay» usaba una superficie de agua del otro proyecto; "
            "asígnale una de este modelo.",
            "«O'Neil» ha perdido su superficie anisótropa, que era del otro "
            "proyecto.",
            "«Ranges»: el rango 2 toma ahora la resistencia de «sand», el "
            "material de ese nombre en este modelo.",
            "«Ranges»: el rango 3 enlazaba un material que este modelo no "
            "puede enlazar; conserva la resistencia que tenía, sin enlace.",
            "«Joints»: la base toma ahora la resistencia de «sand», el "
            "material de ese nombre en este modelo.",
            "«Joints»: la junta 1 enlazaba un material que este modelo no "
            "puede enlazar; conserva la resistencia que tenía, sin "
            "enlace."], said

    def test_a_value_is_said_as_the_file_holds_it(self):
        """Between «» whatever it is, ``null`` for a null, and a model
        without parameters says it has none (review of 0.1.437: the Spanish
        took the three quotings of the English, and a null came out as
        Python's ``None``)."""
        from ogr_gui.core_messages import error_text
        cases = (
            (_mutated(_ENUMS["BoundaryType"], None),
             "Tipo de contorno desconocido: «null»"),
            (_mutated(_ENUMS["PorePressureType"], 7),
             "«7» no es un valor válido para el método de presión "
             "intersticial"),
            (_mutated(_ENUMS["FailureDirection"], None),
             "«null» no es un valor válido para la dirección de rotura"),
            (_mutated(_ENUMS["SupportType"], "future_nail"),
             "Tipo de soporte desconocido: «future_nail»"),
            (_with_unknown_parameter(),
             "Mohr-Coulomb: parámetro desconocido «future_param». Los que "
             "admite: cohesión (cohesion), ángulo de rozamiento "
             "(friction_angle)"),
            (_with_unknown_parameter("infinite_strength"),
             "Resistencia infinita: parámetro desconocido «future_param». "
             "Los que admite: ninguno"))
        with _Language("es"):
            said = [error_text(_refused(d)) for d, _w in cases]
        assert said == [w for _d, w in cases], said

    def test_every_enumeration_a_reader_takes_is_named(self):
        """Every one a ``.ogr`` holds has a name in the window, in Spanish;
        ``ENUM_NAMES`` is the table, read here apart from it."""
        from ogr_gui.i18n import _DICTS
        from ogr_gui.labels import ENUM_NAMES
        names = {k.split("(")[0] for k in _ENUMS} - _NOT_READ_ENUM
        assert names == set(ENUM_NAMES), names ^ set(ENUM_NAMES)
        assert len(names) == 20
        for english in ENUM_NAMES.values():
            assert _DICTS["es"].get(english, english) != english, english


# ======================================================================
_WINDOW: list = []


def _window():
    if not _WINDOW:
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        w = MainWindow()
        w.project.is_dirty = False
        _WINDOW.append(w)
    return _WINDOW[0]


def _fresh(w, **settings):
    """The window on a demo of its own, with no step to undo and no note
    of a test before."""
    from ogr_core.project.demo import build_demo_project
    p = build_demo_project()
    for key, value in settings.items():
        setattr(p.settings, key, value)
    w._attach_project(p)
    w.command_stack.clear()
    w.project.is_dirty = False
    return p


class _Dialogs:
    """The file dialog, the item dialog and the message boxes of the window,
    replaced for the block and put back after it."""

    def __init__(self, path, item=None):
        self.path, self.item = path, item
        self.boxes = []

    def __enter__(self):
        import ogr_gui.main_window as MW
        from PySide6.QtWidgets import QInputDialog
        self._saved = (MW.get_open_file_name, QInputDialog.getItem,
                       MW.QMessageBox.critical, MW.QMessageBox.information)
        MW.get_open_file_name = lambda *a, **k: (self.path, "")
        item = self.item
        QInputDialog.getItem = staticmethod(lambda *a, **k: (item(), True))
        boxes = self.boxes
        MW.QMessageBox.critical = staticmethod(
            lambda *a, **k: boxes.append(a[2] if len(a) > 2 else ""))
        MW.QMessageBox.information = staticmethod(
            lambda *a, **k: boxes.append(a[2] if len(a) > 2 else ""))
        return self

    def __exit__(self, *_exc):
        import ogr_gui.main_window as MW
        from PySide6.QtWidgets import QInputDialog
        (MW.get_open_file_name, getitem, MW.QMessageBox.critical,
         MW.QMessageBox.information) = self._saved
        QInputDialog.getItem = getitem


def _item(label):
    def pick():
        from ogr_gui.i18n import tr
        return tr(label)
    return pick


def _import(w, path, what="Both"):
    """Import Properties from ``path`` by the window's handler; what the
    status bar said."""
    with _Dialogs(path, _item(what)) as d:
        w._import_properties()
    assert d.boxes == [], d.boxes
    return w.statusBar().currentMessage()


def _shown(w):
    """The import notes Analysis Notes has now."""
    return [n for _s, ns in w.last_task_notes.get("import_properties", [])
            for n in ns]


def _source_file(name):
    f = os.path.join(_TMP, name)
    if not os.path.exists(f):
        _source_with_everything().save(f)
    return f


def _bad_file(name, data):
    f = os.path.join(_TMP, name)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return f


#: what Open and Import say of what a file holds that this build does not
#: know, in Spanish and in English (the window's, by the same rules)
_UNKNOWN = (
    ("SupportType", "future_nail",
     "Tipo de soporte desconocido: «future_nail»",
     "Unknown support type: future_nail"),
    ("StrengthModel", "future_model",
     "Modelo de resistencia desconocido: «future_model». Los que hay: "
     "Mohr-Coulomb; ",
     "Unknown strength model: 'future_model'. Available: Mohr-Coulomb; "),
    ("parameter", None,
     "Mohr-Coulomb: parámetro desconocido «future_param». Los que admite: "
     "cohesión (cohesion), ángulo de rozamiento (friction_angle)",
     "Mohr-Coulomb: unknown parameter 'future_param'. Valid: cohesion, "
     "friction angle (friction_angle)"),
    ("BoundaryType", "FUTURE",
     "Tipo de contorno desconocido: «FUTURE»",
     "Unknown boundary type: 'FUTURE'"),
    ("PorePressureType", "future_value",
     "«future_value» no es un valor válido para el método de presión "
     "intersticial",
     "'future_value' is not a valid value for the pore water pressure "
     "method"),
)


def _unknown_data(name, value):
    return (_with_unknown_parameter() if name == "parameter"
            else _mutated(_ENUMS[name], value))


@_requires_qt
class TestTheWindowSaysIt:

    def test_import_properties_puts_its_notes_in_the_panel(self):
        w = _window()
        _fresh(w)
        panel = None
        try:
            with _Language("es"):
                bar = _import(w, _source_file("window source.ogr"))
                w.act_analysis_notes()
                panel = w._analysis_notes_panel
                head = panel.lbl_head.text()
                tops = [panel.tree.topLevelItem(i)
                        for i in range(panel.tree.topLevelItemCount())]
                tree = [(t.text(0), [t.child(j).text(0)
                                     for j in range(t.childCount())])
                        for t in tops]
            # «Both»: every material comes, so every link finds its copy and
            # two notes are left, the water table's and the anisotropic one's
            assert bar.endswith("[2 nota(s) — Análisis > Notas del "
                                "análisis]"), bar
            assert tree == [("Importar propiedades (2)", [
                "«Silty clay (2)» usaba una superficie de agua del otro "
                "proyecto; asígnale una de este modelo.",
                "«O'Neil» ha perdido su superficie anisótropa, que era del "
                "otro proyecto."])], tree
            # the head does not say that none of them moves a factor
            assert head.startswith("2 nota(s). Las del último análisis"), head
            assert "Importar propiedades" in head, head
            # the material arrived dry, which is what the note says
            m = next(m for m in w.project.materials
                     if m.name == "Silty clay (2)")
            assert m.pore_pressure.name == "NONE"
        finally:
            if panel is not None:
                panel.close()
            w.project.is_dirty = False

    def test_the_notes_add_up_and_undo_takes_its_own(self):
        """Two imports, the notes of both; one of only supports leaves them;
        undo hides the last one's, redo brings them back, and a new step
        after an undo forgets them (the review of 0.1.437: each import
        replaced the notes of the one before, and an undone import left
        notes naming materials no longer there)."""
        w = _window()
        _fresh(w)
        src = _source_file("window source add up.ogr")
        try:
            with _Language("es"):
                _import(w, src, "Materials")
                first = list(_shown(w))
                _import(w, src, "Supports")
                assert _shown(w) == first, _shown(w)
                _import(w, src, "Materials")
                assert len(_shown(w)) == 4, _shown(w)
                assert _shown(w)[:2] == first
                second = _shown(w)[2:]
                w.act_undo()
                assert _shown(w) == first, _shown(w)
                w.act_redo()
                assert _shown(w) == first + second, _shown(w)
                w.act_undo()
                bar = _import(w, src, "Materials")
                third = _shown(w)[2:]
            assert len(first) == 2 and len(third) == 2, (first, third)
            assert _shown(w) == first + third
            assert [str(n) for n in third] == [str(n) for n in second]
            assert bar.endswith("[2 nota(s) — Análisis > Notas del "
                                "análisis]"), bar
        finally:
            w.project.is_dirty = False

    def test_at_the_limit_the_note_says_why(self):
        from ogr_gui.core_messages import note_text
        w = _window()
        _fresh(w, max_materials=1)
        try:
            with _Language("es"):
                bar = _import(w, _source_file("window source max.ogr"))
                said = [note_text(n, project=w.project) for n in _shown(w)]
            assert bar.startswith("Importados 0 material(es)"), bar
            assert said == ["Materiales no importados (6): el modelo ya "
                            "tiene el máximo de 1."], said
        finally:
            w.project.is_dirty = False

    def test_open_names_what_it_does_not_know(self):
        """The three of the ficha, without the quotes of the repr, and the
        two of Python the owner wanted said, in Spanish and in English;
        the window keeps its project."""
        w = _window()
        _fresh(w)
        before = w.project
        frame = {"es": "No se pudo abrir el proyecto:\n",
                 "en": "Could not open project:\n"}
        for i, (name, value, es, en) in enumerate(_UNKNOWN):
            f = _bad_file("open %d.ogr" % i, _unknown_data(name, value))
            for code, want in (("es", es), ("en", en)):
                w.project.is_dirty = False
                with _Language(code), _Dialogs(f) as d:
                    w.act_open()
                assert len(d.boxes) == 1, d.boxes
                said = d.boxes[0]
                assert said.startswith(frame[code] + want), (code, said)
                assert "'Unknown" not in said and '"Unknown' not in said, (
                    said)
                assert w.project is before

    def test_import_names_what_it_does_not_know(self):
        """The same sentences in the frame of Import Properties, which reads
        the file before asking what to bring."""
        w = _window()
        _fresh(w)
        for i, (name, value, es, _en) in enumerate(_UNKNOWN):
            f = _bad_file("import %d.ogr" % i, _unknown_data(name, value))
            with _Language("es"), _Dialogs(f, _item("Both")) as d:
                w._import_properties()
            assert len(d.boxes) == 1, d.boxes
            assert d.boxes[0].startswith(
                "No se ha podido leer el proyecto: " + es), d.boxes[0]
            assert _shown(w) == []
        # a refused file leaves no step to undo
        assert not w.command_stack.can_undo

    def test_a_missing_key_stays_as_python_wrote_it(self):
        """The rule of D412 for what is not the core's: as it is, inside
        the translated frame (the owner's decision on the census)."""
        w = _window()
        _fresh(w)
        data = copy.deepcopy(_base())
        del data["support_types"][0]["type_id"]
        f = _bad_file("missing key.ogr", data)
        w.project.is_dirty = False
        with _Language("es"), _Dialogs(f) as d:
            w.act_open()
        assert d.boxes == ["No se pudo abrir el proyecto:\n'type_id'"], (
            d.boxes)


# ======================================================================
#: the one function of ``properties_import.py`` that builds a text in
#: place: a name numbered «X (2)», which is a name and not a note (D421
#: moves it to ``ogr_core.naming``)
_NOT_A_NOTE = ("_unique",)
#: the packages whose readers the enumeration census reads
_PACKAGES = ("ogr_core", "ogr_fem2d", "ogr_slip2d")
#: readers that put a default in place of a value they do not know, said
#: nowhere: left to D429 (the owner's decision in the review of 0.1.437)
_TOLERANT = {
    ("ogr_core/hydraulic/hydraulic_properties.py", "_model_from_dict",
     "PermeabilityModel"),
    ("ogr_core/loads/seismic_record.py", "from_dict", "AccelerationUnit"),
}


def _sentences(src, skip=()):
    """Texts built in place in every function of ``src`` but ``skip``,
    outside their docstrings: f-strings, ``"…" % x``, ``"…" + x``,
    ``"…".format(...)`` and long constants."""
    tree = ast.parse(src)
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if fn.name in skip:
            continue
        doc = fn.body[0].value if isinstance(fn.body[0], ast.Expr) else None
        for n in ast.walk(fn):
            if n is doc:
                continue
            if isinstance(n, ast.JoinedStr):
                found.append((fn.name, n.lineno, "f-string"))
            elif (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod)
                  and isinstance(n.left, ast.Constant)
                  and isinstance(n.left.value, str)):
                found.append((fn.name, n.lineno, "% format"))
            elif (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add)
                  and any(isinstance(s, ast.Constant)
                          and isinstance(s.value, str)
                          for s in (n.left, n.right))):
                found.append((fn.name, n.lineno, "+ text"))
            elif (isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "format"
                  and isinstance(n.func.value, ast.Constant)):
                found.append((fn.name, n.lineno, ".format"))
            elif (isinstance(n, ast.Constant) and isinstance(n.value, str)
                  and len(n.value) > 40):
                found.append((fn.name, n.lineno, "sentence"))
    return found


def _enum_classes(sources):
    """The classes of ``sources`` that derive from an ``Enum``."""
    names = set()
    for src in sources:
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.ClassDef) and any(
                    "Enum" in (getattr(b, "id", "") or getattr(b, "attr", ""))
                    for b in n.bases):
                names.add(n.name)
    return names


def _catches(handler, names):
    t = handler.type
    caught = (t.elts if isinstance(t, ast.Tuple) else [t]) if t else []
    return t is None or any(getattr(c, "id", "") in names for c in caught)


def _verdict(tries):
    """How the innermost ``try`` around a call of an enumeration treats a
    value the enumeration does not know: ``coded`` if its handler raises
    ``said_as(...)``, ``tolerant`` if it raises nothing, else ``bare``."""
    for t in reversed(tries):
        for h in t.handlers:
            if not _catches(h, {"ValueError", "KeyError", "Exception"}):
                continue
            raises = [r for r in ast.walk(h) if isinstance(r, ast.Raise)]
            if not raises:
                return "tolerant"
            if any(isinstance(r.exc, ast.Call)
                   and getattr(r.exc.func, "id", "") == "said_as"
                   for r in raises):
                return "coded"
            return "bare"
    return "bare"


def _enum_calls(src, enums):
    """Each ``Enum(value)`` or ``Enum[value]`` of ``enums`` in the readers
    of ``src`` (a function whose name holds ``from_``), with its verdict,
    and the first arguments of every ``read_enum`` there. Only the readers
    are walked with their ``try`` blocks: a function inside one is judged
    by its own name."""
    hits, read = [], []

    def visit(node, fn, tries):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            inner = (tries + [node] if isinstance(node, ast.Try)
                     and child in node.body else tries)
            if (isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)):
                if child.func.id in enums:
                    hits.append((fn, child.func.id, _verdict(inner)))
                elif child.func.id == "read_enum" and child.args:
                    read.append(getattr(child.args[0], "id", "?"))
            if (isinstance(child, ast.Subscript)
                    and isinstance(child.value, ast.Name)
                    and child.value.id in enums
                    and isinstance(child.ctx, ast.Load)):
                hits.append((fn, child.value.id, _verdict(inner)))
            visit(child, fn, inner)

    for fn in ast.walk(ast.parse(src)):
        if (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                and "from_" in fn.name):
            visit(fn, fn.name, [])
    return hits, read


#: what a file must hold to be parsed at all: the census reads three
#: packages, and parsing every file cost four seconds (AGENTS.md asks a new
#: test for less than one); each prefilter is checked on the census's own
#: source
_READER_DEF = re.compile(r"\bdef \w*from_\w*\s*\(")
_ENUM_DEF = re.compile(r"\bclass \w+\s*\([^)]*Enum")


def _package_sources():
    out = {}
    for pkg in _PACKAGES:
        for f in sorted((_ROOT / pkg).rglob("*.py")):
            if "__pycache__" not in f.parts:
                out[f.relative_to(_ROOT).as_posix()] = f.read_text(
                    encoding="utf-8")
    return out


class TestTheCensuses:

    def test_no_note_of_import_properties_is_built_in_place(self):
        src = (_ROOT / "ogr_core" / "project" / "properties_import.py"
               ).read_text(encoding="utf-8")
        assert _sentences(src, _NOT_A_NOTE) == []
        # and the one skipped is still there to be skipped
        assert any(isinstance(n, ast.FunctionDef) and n.name == "_unique"
                   for n in ast.walk(ast.parse(src)))

    def test_every_enumeration_a_reader_calls_says_its_code(self):
        from ogr_gui.labels import ENUM_NAMES
        sources = _package_sources()
        enums = _enum_classes(s for s in sources.values()
                              if _ENUM_DEF.search(s))
        assert {"PorePressureType", "BCType", "GridValueType"} <= enums
        bare, tolerant, coded, read = [], set(), [], set()
        for rel, src in sources.items():
            if not _READER_DEF.search(src):
                continue
            hits, names = _enum_calls(src, enums)
            read |= set(names)
            for fn, cls, verdict in hits:
                if verdict == "bare":
                    bare.append((rel, fn, cls))
                elif verdict == "tolerant":
                    tolerant.add((rel, fn, cls))
                else:
                    coded.append((rel, fn, cls))
        assert bare == [], bare
        assert tolerant == _TOLERANT, tolerant ^ _TOLERANT
        assert coded == [("ogr_core/geometry/boundary.py", "from_dict",
                          "BoundaryType")], coded
        # every enumeration read through ``read_enum`` has its name in the
        # window, and every name of the table is read somewhere
        assert read == set(ENUM_NAMES), read ^ set(ENUM_NAMES)

    def test_the_censuses_see_their_cases(self):
        """On sources of their own: each finds what it is for."""
        bad = ('def import_properties(p):\n'
               '    notes.append(f"{x!r} used a water surface")\n'
               '    notes.append("%r lost" % x)\n'
               '    notes.append(x + " came")\n'
               '    notes.append("{0} left".format(x))\n'
               'def _helper(p):\n'
               '    notes.append(f"{p} too")\n'
               'def _unique(p):\n'
               '    return f"{p} (2)"\n')
        assert _sentences(bad, _NOT_A_NOTE) == [
            ("import_properties", 2, "f-string"),
            ("import_properties", 3, "% format"),
            ("import_properties", 4, "+ text"),
            ("import_properties", 5, ".format"),
            ("_helper", 7, "f-string")]
        readers = ('class Kind(str, Enum):\n'
                   '    A = "a"\n'
                   'class Other(enum.Enum):\n'
                   '    B = "b"\n'
                   'def from_dict(d):\n'
                   '    a = Kind(d["k"])\n'
                   '    try:\n'
                   '        b = Other(d["o"])\n'
                   '    except ValueError:\n'
                   '        b = Other.B\n'
                   '    try:\n'
                   '        c = Kind[d["c"]]\n'
                   '    except KeyError as exc:\n'
                   '        raise said_as(exc, CODE, value=d["c"])\n'
                   '    try:\n'
                   '        e = Kind(d["e"])\n'
                   '    except ValueError:\n'
                   '        raise\n'
                   '    return read_enum(Other, a), Kind(d["z"]).value\n'
                   'def __post_init__(self, v):\n'
                   '    self.v = Kind(v)\n')
        enums = _enum_classes([readers])
        assert enums == {"Kind", "Other"}
        # the prefilters let through what the census reads, and no more
        assert len(_ENUM_DEF.findall(readers)) == 2
        assert [m.group(0) for m in _READER_DEF.finditer(readers)] == [
            "def from_dict("]
        assert _READER_DEF.search("def _model_from_dict (d):")
        hits, read = _enum_calls(readers, enums)
        assert hits == [("from_dict", "Kind", "bare"),
                        ("from_dict", "Other", "tolerant"),
                        ("from_dict", "Kind", "coded"),
                        ("from_dict", "Kind", "bare"),
                        ("from_dict", "Kind", "bare")], hits
        assert read == ["Other"]
