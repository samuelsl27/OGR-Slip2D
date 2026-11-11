# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.436 (D415) -- the names the program gives: each set named once, in the
reader's language, and a load by the magnitude it has.

Invariants protected here:

* **The agent's English is 0.1.435's.** ``_V1435`` was written by 0.1.435
  (c080aa0), measured by CALLING its functions on a ``git archive`` of that
  tree (``_auditoria/P10_herramientas/capture_d415.py`` of the bank, the
  same inputs as :func:`_capture`) -- not printed by this code. For a change
  of text the reference is what the old program said: the notes that name a
  set, a support, a record or a load, the two line-load refusals, and the
  agent's JSON (``support_type_set``, ``seismic_record_set``, ``load_set``
  without a name and with another magnitude, ``project_get``, the warnings
  and the load factors of a run), with the ids masked: 39 entries.
* **Define Support names each new set once.** «Type N» takes the smallest
  free N and a copy «X (copy)», then «X (copy) (2)»: it counted the rows,
  and deleting the second of three and adding gave a second «Type 3». The
  reference is the agent's own rule: for every set, ``find_type`` by its
  name finds THAT set (naming, then finding by the name, is the identity).
* **A name the program gave reads in the reader's language** -- «Tipo 3»,
  «Anclado en el extremo (copia)», «Registro» -- and a class's name by the
  class the set has now, the dictionary's own word for it. The stored name,
  the ``.ogr`` and the edit fields do not change, also when a dialog is
  accepted in Spanish. «Type 01» is the user's: the program never writes it.
* **A load is named by its magnitude NOW,** as the canvas's context menu
  has always named it (the reference); a line load in kN/m, not kPa. A name
  the user gave is data. The results panel and the window's PDF name an
  unnamed load by the magnitude of the RUN (the owner's decision,
  2026-11-11): changing the load after the run does not change them.
* **The notes declare their kinds:** «User Defined» in the masculine of a
  support type, a set by the class it has now, the quotes of the reader's
  language, the line-load notes between «» and by the load's magnitude
  alone, a support that could not be priced by its name. An unnamed support
  reads by its class and its head, «Bulón de suelo en (54.00, 8.00)», in
  both languages of the window (the owner's decision in the review of
  0.1.436: by its set, the orphan's note was circular and a pattern's
  supports read alike), and never by its id or «soil_nail».
* **A load that varies along it is named by its two ends** («10.0–30.0
  kN/m²», the owner's decision in the review), in the context menu too.
* **A name that is not text** (``"name": 5`` in a hand-edited file) reaches
  the agent's JSON as that value: wrapping it made it ``"5"``.
* **The window says the notes against its project,** without which the
  rules fall back on the id or on the magnitude a load was born with; and a
  run keeps ONE ``LoadName`` per load, not one per surface.
* **The census strips only what the user typed** (``_data_names`` of
  ``test_labels_spanish_v1321``): «Type 3» passed for a name.

One process-wide Qt application; no main window, no search of 400 circles
or more, no modal dialog.
"""
from __future__ import annotations

import json
import pickle
import re
import sys
from pathlib import Path
from types import SimpleNamespace

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


def _app():
    return QApplication.instance() or QApplication([])


class _Language:
    """The interface in ``code`` for the block, and back after it (rule 5:
    a test that left Spanish on failed unrelated menu tests)."""

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
# 0.1.435's English, measured on its tree (see the module docstring)
# ======================================================================
_V1435 = {'ambiguous_given': "2 supports of class 'Grouted Tieback' name no "
                    'property set and the project defines 2 sets of that '
                    "class ('Tie A', 'Tie B'). The first, 'Tie A', is "
                    'used. Assign each support its set in Support '
                    'Properties if that is not the one meant.',
 'ambiguous_unnamed': "1 support of class 'Grouted Tieback' name no "
                      'property set and the project defines 2 sets of that '
                      "class ('Grouted Tieback', 'Grouted Tieback'). The "
                      "first, 'Grouted Tieback', is used. Assign each "
                      'support its set in Support Properties if that is '
                      'not the one meant.',
 'ambiguous_user_defined': "1 support of class 'User Defined' name no "
                           'property set and the project defines 2 sets of '
                           "that class ('User Defined', 'User Defined "
                           "(2)'). The first, 'User Defined', is used. "
                           'Assign each support its set in Support '
                           'Properties if that is not the one meant.',
 'critical_load_factors': '{"bishop_simplified": [{"action": "permanent", '
                          '"drives": true, "factor": 1.35, "load": "<id>", '
                          '"name": "Dist 15.0 kN/m\\u00b2"}]}',
 'failure_many': '2 supports could not be priced: <id> (reason a); <id> '
                 '(reason b)',
 'failure_one': 'support <id> could not be priced: the soil around it '
                'cannot be read',
 'helical_0': "The shaft of support 'plateless' is not narrower than its "
              'helices, so the plates have no bearing area and the anchor '
              'carries nothing in pullout.',
 'helical_1': "The shaft of support 'Helical Anchor' is not narrower than "
              'its helices, so the plates have no bearing area and the '
              'anchor carries nothing in pullout.',
 'helical_2': "The 3 helices of support 'Type 2' do not fit at 0.90 m: the "
              'spacing used is 0.60 m, the anchor length divided by the '
              'number of gaps.',
 'helical_3': "The helix spacing of support 'Type 2' is 2.40 times the "
              'average helix diameter. Design guides recommend 5 to 12.',
 'infinite_type_n': "Support 'Type 4' (Type 4) has about 28 % of its "
                    "length in 'bedrock', whose strength is not finite "
                    '(Infinite Strength): the soil around it is read as '
                    'zero there. Rigid bedrock is a modelling device, not '
                    'a promise that a support cannot be pulled out of it, '
                    'and letting the infinity through would drop its '
                    'pull-out or bearing from the minimum.',
 'infinite_unnamed_set': "Support 'N1' (Geosynthetic) has about 28 % of "
                         "its length in 'bedrock', whose strength is not "
                         'finite (Infinite Strength): the soil around it '
                         'is read as zero there. Rigid bedrock is a '
                         'modelling device, not a promise that a support '
                         'cannot be pulled out of it, and letting the '
                         'infinity through would drop its pull-out or '
                         'bearing from the minimum.',
 'infinite_unnamed_support': "Support '<id>' (Geosynthetic) has about 28 % "
                             "of its length in 'bedrock', whose strength "
                             'is not finite (Infinite Strength): the soil '
                             'around it is read as zero there. Rigid '
                             'bedrock is a modelling device, not a promise '
                             'that a support cannot be pulled out of it, '
                             'and letting the infinity through would drop '
                             'its pull-out or bearing from the minimum.',
 'line_needs_ground': ['ValueError',
                       'Line load Line 50.0 kN/m: an orientation relative '
                       'to the boundary needs the ground surface.'],
 'line_off_ground': ['ValueError',
                     'Line load Line 50.0 kN/m at (10, 99) is not on the '
                     'ground surface, so it has no boundary to be normal '
                     'to.'],
 'line_off_ground_unnamed': ['ValueError',
                             'Line load <id> at (10, 99) is not on the '
                             'ground surface, so it has no boundary to be '
                             'normal to.'],
 'load_crest': '{"created": true, "load": {"action": "permanent", '
               '"angle_deg": 0.0, "creates_excess_pore_pressure": false, '
               '"distribution": "constant", "end": [24.5, 25.0], "id": '
               '"<id>", "kind": "distributed", "magnitude_1": 15.0, '
               '"magnitude_2": null, "name": "Dist 15.0 kN/m\\u00b2", '
               '"orientation": "normal_to_boundary", "start": [21.0, '
               '25.0]}, "notes": ["action is only read with a design '
               'standard enabled (settings_set '
               '\'design_standard.enabled\')."]}',
 'load_dist': '{"created": true, "load": {"action": "variable", '
              '"angle_deg": 0.0, "creates_excess_pore_pressure": false, '
              '"distribution": "constant", "end": [20.0, 25.0], "id": '
              '"<id>", "kind": "distributed", "magnitude_1": 20.0, '
              '"magnitude_2": null, "name": "Dist 20.0 kN/m\\u00b2", '
              '"orientation": "normal_to_boundary", "start": [5.0, 25.0]}, '
              '"notes": []}',
 'load_dist_35': '{"created": false, "load": {"action": "variable", '
                 '"angle_deg": 0.0, "creates_excess_pore_pressure": false, '
                 '"distribution": "constant", "end": [20.0, 25.0], "id": '
                 '"<id>", "kind": "distributed", "magnitude_1": 35.0, '
                 '"magnitude_2": null, "name": "Dist 20.0 kN/m\\u00b2", '
                 '"orientation": "normal_to_boundary", "start": [5.0, '
                 '25.0]}, "notes": []}',
 'load_line': '{"created": true, "load": {"action": "variable", '
              '"angle_deg": 0.0, "creates_excess_pore_pressure": false, '
              '"id": "<id>", "kind": "line", "magnitude": 50.0, "name": '
              '"Line 50.0 kN/m", "orientation": "vertical", "point": '
              '[10.0, 25.0]}, "notes": []}',
 'newmark_given': "bishop_simplified: the seismic record 'El Centro' "
                  'cannot be integrated (it needs at least two samples and '
                  'a positive time interval), so no displacement was '
                  'computed.',
 'newmark_record': "bishop_simplified: the seismic record 'Record' cannot "
                   'be integrated (it needs at least two samples and a '
                   'positive time interval), so no displacement was '
                   'computed.',
 'orphan_0': "Support 'S7' refers to a property set that is no longer in "
             "the project; 'Type 3' is used instead, chosen by class.",
 'orphan_1': "Support '<id>' refers to a property set that is no longer in "
             "the project; 'Soil Nail' is used instead, chosen by class.",
 'project_get_distributed_loads': '{"data": [{"action": "variable", '
                                  '"angle_deg": 0.0, '
                                  '"creates_excess_pore_pressure": false, '
                                  '"distribution": "constant", "end": '
                                  '[20.0, 25.0], "id": "<id>", '
                                  '"magnitude_1": 35.0, "magnitude_2": '
                                  'null, "name": "Dist 20.0 kN/m\\u00b2", '
                                  '"orientation": "normal_to_boundary", '
                                  '"start": [5.0, 25.0], "type": '
                                  '"distributed"}], "project_id": "p_<h>", '
                                  '"section": "distributed_loads"}',
 'project_get_line_loads': '{"data": [{"action": "variable", "angle_deg": '
                           '0.0, "creates_excess_pore_pressure": false, '
                           '"id": "<id>", "magnitude": 50.0, "name": "Line '
                           '50.0 kN/m", "orientation": "vertical", '
                           '"point": [10.0, 25.0], "type": "line"}], '
                           '"project_id": "p_<h>", "section": '
                           '"line_loads"}',
 'project_get_seismic_records': '{"data": [{"accelerations_g": [0.1, 0.2, '
                                '0.0], "dt": 0.02, "id": "<id>", "name": '
                                '"Record", "source_file": "", '
                                '"source_unit": "g"}], "project_id": '
                                '"p_<h>", "section": "seismic_records"}',
 'project_get_support_types': '{"data": [{"_extras": {"_color": "#4b0082", '
                              '"_display_name": "User Defined", '
                              '"_force_application": "active", '
                              '"_orientation": "parallel_to_support", '
                              '"_user_angle_deg": 0.0}, "id": "<id>", '
                              '"out_of_plane_spacing": 1.0, "points": '
                              '[[0.0, 100.0], [5.0, 200.0], [10.0, '
                              '100.0]], "type_id": "user_defined"}, '
                              '{"_extras": {"_color": "#4b0082", '
                              '"_display_name": "User Defined (2)", '
                              '"_force_application": "active", '
                              '"_orientation": "parallel_to_support", '
                              '"_user_angle_deg": 0.0}, "id": "<id>", '
                              '"out_of_plane_spacing": 1.0, "points": '
                              '[[0.0, 100.0], [5.0, 200.0], [10.0, '
                              '100.0]], "type_id": "user_defined"}], '
                              '"project_id": "p_<h>", "section": '
                              '"support_types"}',
 'project_get_supports': '{"data": [{"color": "#4b0082", '
                         '"force_application": "active", "head": [30.0, '
                         '20.0], "id": "<id>", "name": "User Defined", '
                         '"orientation": "parallel_to_support", "tail": '
                         '[20.0, 15.0], "type_id": "user_defined", '
                         '"type_ref": "<id>", "user_angle_deg": 0.0}], '
                         '"project_id": "p_<h>", "section": "supports"}',
 'record_set': '{"notes": [], "record": {"dt": 0.02, "id": "<id>", "name": '
               '"Record", "pga_g": 0.2, "samples": 3, "usable": true}}',
 'reversed_given': "Support 'Bolt 'B' 1' has its head at (54.00, 8.00), on "
                   'the stable side of the reported surface, and its tail '
                   'at (43.50, 8.00), inside the sliding mass. The head is '
                   'the end at the slope FACE: the stripping length L_i is '
                   'measured from it, the pullout length L_o from the '
                   "tail, and the force under 'tangent_to_slip' is placed "
                   'from the axis read head to tail. Drawn this way round '
                   'all three are reversed. Check which end was clicked '
                   'first before quoting this factor.',
 'reversed_type_n': "Support 'Type 2' has its head at (54.00, 8.00), on "
                    'the stable side of the reported surface, and its tail '
                    'at (43.50, 8.00), inside the sliding mass. The head '
                    'is the end at the slope FACE: the stripping length '
                    'L_i is measured from it, the pullout length L_o from '
                    "the tail, and the force under 'tangent_to_slip' is "
                    'placed from the axis read head to tail. Drawn this '
                    'way round all three are reversed. Check which end was '
                    'clicked first before quoting this factor.',
 'reversed_unnamed': "Support 'soil_nail' has its head at (54.00, 8.00), "
                     'on the stable side of the reported surface, and its '
                     'tail at (43.50, 8.00), inside the sliding mass. The '
                     'head is the end at the slope FACE: the stripping '
                     'length L_i is measured from it, the pullout length '
                     'L_o from the tail, and the force under '
                     "'tangent_to_slip' is placed from the axis read head "
                     'to tail. Drawn this way round all three are '
                     'reversed. Check which end was clicked first before '
                     'quoting this factor.',
 'run_warnings': '{"kind": "analysis", "project_id": "p_<h>", "result_id": '
                 '"r_<h>", "stale": false, "warning_codes": [{"args": '
                 '{"method_id": "bishop_simplified", "note": {"args": '
                 '{"edges": "x = 40", "x0": 10.0, "x1": 40.0, "y0": 25, '
                 '"y1": 45.0}, "code": "method.grid_edge", "text": "The '
                 'critical centre lies on the edge of the search grid (x = '
                 '40; grid x 10 to 40, y 25 to 45). A minimum on the '
                 'boundary is the best of what was searched, not '
                 'necessarily the lowest one: widen the grid on that side '
                 'and re-run before quoting it."}}, "code": "note.method", '
                 '"index": 0}], "warnings": ["bishop_simplified: The '
                 'critical centre lies on the edge of the search grid (x = '
                 '40; grid x 10 to 40, y 25 to 45). A minimum on the '
                 'boundary is the best of what was searched, not '
                 'necessarily the lowest one: widen the grid on that side '
                 'and re-run before quoting it."]}',
 'slope_angle_0': '3 load(s) were on the old face and were not moved: Dist '
                  '20.0 kN/m², <id>, Fence, east.',
 'slope_angle_support_0': '1 support(s) had their head on the old face and '
                          'were not moved: <id>.',
 'support_set': '{"created": true, "notes": [], "support": {"class": '
                '"user_defined", "force_application": "active", "head": '
                '[30.0, 20.0], "id": "<id>", "length": 11.18034, "name": '
                '"User Defined", "orientation": "parallel_to_support", '
                '"pattern_id": null, "support_type": "<id>", "tail": '
                '[20.0, 15.0], "user_angle_deg": 0.0}}',
 'type_set_1': '{"created": true, "support_type": {"allows_pattern": true, '
               '"class": "user_defined", "color": "#4b0082", '
               '"force_application": "active", "id": "<id>", "name": "User '
               'Defined", "orientation": "parallel_to_support", "params": '
               '{"out_of_plane_spacing": 1.0, "points": [[0.0, 100.0], '
               '[5.0, 200.0], [10.0, 100.0]]}, "user_angle_deg": 0.0}, '
               '"supports_retyped": 0}',
 'type_set_2': '{"created": true, "support_type": {"allows_pattern": true, '
               '"class": "user_defined", "color": "#4b0082", '
               '"force_application": "active", "id": "<id>", "name": "User '
               'Defined (2)", "orientation": "parallel_to_support", '
               '"params": {"out_of_plane_spacing": 1.0, "points": [[0.0, '
               '100.0], [5.0, 200.0], [10.0, 100.0]]}, "user_angle_deg": '
               '0.0}, "supports_retyped": 0}'}

_UUID = re.compile(r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?"
                   r"[0-9a-f]{12}")
_HANDLE = re.compile(r"\b([pr])_[0-9a-f]{10}\b")


def _scrub(text):
    return _HANDLE.sub(r"\1_<h>", _UUID.sub("<id>", text))


# ----------------------------------------------------------------------
# The models the capture used, built once
# ----------------------------------------------------------------------
_H, _TOE, _CREST = 12.0, 30.0, 50.0


def _slope():
    """The slope of ``test_supports_all_methods_v164``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(0, -10.0), Vertex(60, -10.0),
                             Vertex(60, _H), Vertex(_CREST, _H),
                             Vertex(_TOE, 0), Vertex(0, 0)], closed=True)
    ext.ensure_ccw()
    q = Project("sup")
    q.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    q.materials = [Material(name="S", unit_weight=18, strength=MohrCoulomb(
        cohesion=8, friction_angle=20))]
    return q


def _lens(q, name="bedrock"):
    """A lens of Infinite Strength rock behind the circle, which the support's
    tail runs through (``test_support_soil_failure_v1231``)."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import InfiniteStrength
    pl = Polyline(vertices=[Vertex(51, 6), Vertex(58, 6), Vertex(58, 10),
                            Vertex(51, 10)], closed=True)
    pl.ensure_ccw()
    q.add_boundary(Boundary(polyline=pl, btype=BoundaryType.MATERIAL))
    lens = Material(name=name, unit_weight=18.0, strength=InfiniteStrength())
    q.materials.append(lens)
    q.invalidate_regions_cache()
    assert q.assign_material_at(54.5, 8.0, lens.id)
    return q


_MODELS: dict = {}
_AGENT: dict = {}


def _note_models() -> dict:
    """``{case: (project, [notes])}`` -- the projects the notes were
    measured on, kept so that the Spanish is read against the same one."""
    if _MODELS:
        return _MODELS
    from ogr_core.geometry import Vertex
    from ogr_core.geometry import slope_angle as SA
    from ogr_core.loads.loads import DistributedLoad, LineLoad
    from ogr_core.loads.seismic_record import SeismicRecord
    from ogr_core.project import Project
    from ogr_core.project.demo import build_demo_project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  Geosynthetic, GroutedTieback, HelicalAnchor,
                                  SoilNail, SupportInstance, UserDefined)
    from ogr_slip2d.analysis_runner import _seismic_notes
    from ogr_slip2d.helical_anchor_notes import helical_anchor_notes
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import (_failure_text,
                                                reversed_support_notes)
    from ogr_slip2d.support_notes import (infinite_strength_notes,
                                          support_identity_notes)
    from ogr_slip2d.surface import SlipCircle

    def ambiguous(sets, n_sups=1):
        p = Project("amb")
        p.support_types = sets
        p.supports = [SupportInstance(type_id=sets[0].TYPE_ID, name="",
                                      head=Vertex(0, i), tail=Vertex(5, i))
                      for i in range(n_sups)]
        return p, support_identity_notes(p)

    a, b = UserDefined(), UserDefined()
    a._display_name, b._display_name = "User Defined", "User Defined (2)"
    _MODELS["ambiguous_user_defined"] = ambiguous([a, b])
    t1, t2 = GroutedTieback(), GroutedTieback()
    t1._display_name, t2._display_name = "Tie A", "Tie B"
    _MODELS["ambiguous_given"] = ambiguous([t1, t2], 2)
    _MODELS["ambiguous_unnamed"] = ambiguous([GroutedTieback(),
                                              GroutedTieback()])

    p = Project("orph")
    kept = GroutedTieback()
    kept._display_name = "Type 3"
    p.support_types = [kept]
    p.supports = [SupportInstance(type_id="grouted_tieback", name="S7",
                                  type_ref="gone", head=Vertex(0, 0),
                                  tail=Vertex(5, 0)),
                  SupportInstance(type_id="soil_nail", name="",
                                  type_ref="gone2", head=Vertex(0, 1),
                                  tail=Vertex(5, 1))]
    _MODELS["orphan"] = (p, support_identity_notes(p))

    plateless = HelicalAnchor(shaft_width=0.25, average_helix_diameter=0.25)
    plateless._display_name = "Type 1 (copy)"
    spaced = HelicalAnchor(shaft_width=0.1, average_helix_diameter=0.25,
                           number_of_helices=3, helix_spacing=0.9)
    p = Project("hel")
    p.support_types = [plateless, spaced]
    p.supports = [
        SupportInstance(type_id="helical_anchor", type_ref=plateless.id,
                        name="plateless", head=Vertex(0, 0),
                        tail=Vertex(5, 0)),
        SupportInstance(type_id="helical_anchor", type_ref=plateless.id,
                        name="Helical Anchor", head=Vertex(0, 1),
                        tail=Vertex(5, 1)),
        SupportInstance(type_id="helical_anchor", type_ref=spaced.id,
                        name="Type 2", head=Vertex(0, 2),
                        tail=Vertex(1.2, 2)),
    ]
    _MODELS["helical"] = (p, helical_anchor_notes(p))

    for label, given, sname in (("infinite_unnamed_set", None, "N1"),
                                ("infinite_type_n", "Type 4", "Type 4"),
                                ("infinite_unnamed_support", None, "")):
        q = _lens(_slope())
        geo = Geosynthetic(tensile_capacity=50.0, pullout_mode="coefficient",
                           coefficient_of_interaction=0.8,
                           connection_strength=25.0)
        if given:
            geo._display_name = given
        q.support_types = [geo]
        q.supports = [SupportInstance(
            type_id="geosynthetic", head=Vertex(43.5, 8.0),
            tail=Vertex(54.0, 8.0), name=sname,
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.TANGENT_TO_SLIP, type_ref=geo.id)]
        _MODELS[label] = (q, infinite_strength_notes(q))

    circle = SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)
    for label, sname in (("reversed_unnamed", ""),
                         ("reversed_type_n", "Type 2"),
                         ("reversed_given", "Bolt 'B' 1")):
        q = _slope()
        q.support_types = [SoilNail(tensile_capacity=30, plate_capacity=20,
                                    bond_strength=8,
                                    out_of_plane_spacing=3.0)]
        q.supports = [SupportInstance(
            type_id="soil_nail", head=Vertex(54.0, 8.0),
            tail=Vertex(43.5, 8.0), name=sname,
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.TANGENT_TO_SLIP)]
        res = BishopSimplified().compute_fos(
            q, circle, slice_surface(q, circle, num_slices=25))
        _MODELS[label] = (q, reversed_support_notes(q, res))

    # a support that could not be priced, one and several
    q = Project("fail")
    q.support_types = [SoilNail()]
    fa = SupportInstance(type_id="soil_nail", name="Nail A",
                         head=Vertex(30, 20), tail=Vertex(20, 15))
    fb = SupportInstance(type_id="soil_nail", name="", head=Vertex(31, 19),
                         tail=Vertex(21, 14))
    q.supports = [fa, fb]
    _MODELS["failure"] = (q, [
        _failure_text([(fa.id, "the soil around it cannot be read")]),
        _failure_text([(fa.id, "reason a"), (fb.id, "reason b")])])

    for label, rname in (("newmark_record", "Record"),
                         ("newmark_given", "El Centro")):
        q = build_demo_project()
        rec = SeismicRecord(name=rname, dt=0.01, accelerations=[0.1])
        q.seismic_records = [rec]
        q.settings.seismic.newmark = True
        q.settings.seismic.record_id = rec.id
        notes = _seismic_notes(q, "bishop_simplified", SimpleNamespace(
            evaluations=[], user_evaluations=[]))
        _MODELS[label] = (q, notes[-1:])

    q = build_demo_project()
    q.add_distributed_load(DistributedLoad(
        start=Vertex(27, 23), end=Vertex(33, 17), magnitude_1=20.0,
        name="Dist 20.0 kN/m²"))
    q.add_line_load(LineLoad(point=Vertex(30, 20), magnitude=50.0, name=""))
    q.add_line_load(LineLoad(point=Vertex(32, 18), magnitude=5.0,
                             name="Fence, east"))
    out = SA.change_slope_angle(q, (35, 15), (25, 25), target_deg=30.0)
    _MODELS["slope_angle"] = (q, list(out.get("notes") or []))

    q = build_demo_project()
    q.supports = [SupportInstance(type_id="soil_nail", name="",
                                  head=Vertex(30, 20), tail=Vertex(40, 18))]
    out = SA.change_slope_angle(q, (35, 15), (25, 25), target_deg=30.0)
    _MODELS["slope_angle_support"] = (q, list(out.get("notes") or []))

    refusals = []
    ground = build_demo_project().external_boundary().polyline
    for name, ll, gr in (
            ("line_needs_ground", LineLoad(point=Vertex(10, 99),
                                           magnitude=50.0,
                                           name="Line 50.0 kN/m"), None),
            ("line_off_ground", LineLoad(point=Vertex(10, 99),
                                         magnitude=50.0,
                                         name="Line 50.0 kN/m"), ground),
            ("line_off_ground_unnamed", LineLoad(point=Vertex(10, 99),
                                                 magnitude=50.0, name=""),
             ground)):
        try:
            ll.ground_frame(gr)
        except ValueError as exc:
            refusals.append((name, ll, exc))
    _MODELS["line_refusals"] = refusals
    return _MODELS


def _agent() -> dict:
    """The agent's answers the capture recorded, ids masked. A cache of its
    own: the note models' is filled whole or not at all."""
    if _AGENT:
        return _AGENT
    from ogr_api import Workspace, call
    out = {}

    def j(name, value):
        out[name] = _scrub(json.dumps(value, sort_keys=True, default=str))

    ws = Workspace()
    try:
        pid = call(ws, "project_new", template="demo")["project_id"]
        j("type_set_1", call(ws, "support_type_set", project_id=pid,
                             type_class="user_defined"))
        j("type_set_2", call(ws, "support_type_set", project_id=pid,
                             type_class="user_defined"))
        proj = ws.get(pid).project
        j("support_set", call(ws, "support_set", project_id=pid,
                              support_type=proj.support_types[0].id,
                              head=[30, 20], tail=[20, 15]))
        j("record_set", call(ws, "seismic_record_set", project_id=pid,
                             text="0 0.1\n0.02 0.2\n0.04 0.0\n"))
        j("load_dist", call(ws, "load_set", project_id=pid,
                            kind="distributed", start=[5, 25], end=[20, 25],
                            magnitude=20))
        j("load_dist_35", call(ws, "load_set", project_id=pid,
                               load=proj.distributed_loads[0].id,
                               magnitude=35))
        j("load_line", call(ws, "load_set", project_id=pid, kind="line",
                            point_xy=[10, 25], magnitude=50))
        for sec in ("distributed_loads", "line_loads", "support_types",
                    "supports", "seismic_records"):
            j("project_get_" + sec, call(ws, "project_get", project_id=pid,
                                         section=sec))
        j("load_crest", call(ws, "load_set", project_id=pid,
                             kind="distributed", start=[21, 25],
                             end=[24.5, 25], magnitude=15,
                             action="permanent"))
        call(ws, "analysis_configure", project_id=pid,
             methods=["bishop_simplified"], grid={"nx": 3, "ny": 3},
             radius_increment=3, design_standard="eurocode7_da1c1")
        run = call(ws, "analysis_run", project_id=pid, wait_seconds=120)
        rid = run.get("result_id")
        j("run_warnings", call(ws, "results_get", result_id=rid,
                               view="warnings"))
        crit = call(ws, "results_get", result_id=rid, view="critical")
        j("critical_load_factors", {
            m: v.get("load_factors")
            for m, v in crit.get("critical", {}).items()})
    finally:
        ws.shutdown()
    _AGENT.update(out)
    return _AGENT


def _capture() -> dict:
    """What :data:`_V1435` recorded, measured on this tree."""
    out = {}
    models = _note_models()
    for key in ("ambiguous_user_defined", "ambiguous_given",
                "ambiguous_unnamed", "infinite_unnamed_set",
                "infinite_type_n", "infinite_unnamed_support",
                "reversed_unnamed", "reversed_type_n", "reversed_given",
                "newmark_record", "newmark_given"):
        notes = models[key][1]
        out[key] = _scrub(str(notes[0])) if notes else "NO NOTE"
    for key, prefix in (("orphan", "orphan_"), ("helical", "helical_"),
                        ("slope_angle", "slope_angle_"),
                        ("slope_angle_support", "slope_angle_support_")):
        for i, n in enumerate(models[key][1]):
            out[prefix + str(i)] = _scrub(str(n))
    one, many = models["failure"][1]
    out["failure_one"], out["failure_many"] = _scrub(one), _scrub(many)
    for name, _ll, exc in models["line_refusals"]:
        out[name] = [type(exc).__name__, _scrub(str(exc))]
    out.update(_agent())
    return out


def _es(key, i=0):
    """Note ``i`` of a case, in Spanish, against its own project."""
    from ogr_gui.core_messages import note_text
    q, notes = _note_models()[key]
    with _Language("es"):
        return note_text(notes[i], project=q)


def _en(key, i=0):
    from ogr_gui.core_messages import note_text
    q, notes = _note_models()[key]
    with _Language("en"):
        return note_text(notes[i], project=q)


# ======================================================================
class TestTheEnglishIsThatOf0435:

    def test_every_note_and_every_answer(self):
        now = _capture()
        assert sorted(now) == sorted(_V1435), (
            sorted(set(now) ^ set(_V1435)))
        assert len(_V1435) == 39
        for key, want in _V1435.items():
            assert now[key] == want, (key, now[key], want)

    def test_a_kept_value_is_the_same_text(self):
        """What carries the kinds IS the text: equality, JSON and pickling
        see the English, and pickling keeps the rest (the pool of a
        search sends them back)."""
        from ogr_core.messages import Joined
        from ogr_core.naming import LoadName
        j = Joined(["A", "B, C"], refs=["1", "2"], quote="'")
        assert j == "'A', 'B, C'" and json.dumps(j) == '"\'A\', \'B, C\'"'
        back = pickle.loads(pickle.dumps(j))
        assert (back, back.items, back.refs, back.quote) == (
            j, ("A", "B, C"), ("1", "2"), "'")
        n = LoadName("Dist 20.0 kN/m²", kind="distributed", magnitude=35.0,
                     given=False, end_magnitude=40.0)
        assert n == "Dist 20.0 kN/m²" and json.loads(json.dumps(n)) == n
        back = pickle.loads(pickle.dumps(n))
        assert (back, back.kind, back.magnitude, back.given,
                back.end_magnitude) == (n, "distributed", 35.0, False, 40.0)

    def test_a_name_that_is_not_text_reaches_the_agent_as_it_came(self):
        """A hand-edited file may hold ``"name": 5``; the readers keep it,
        and the agent's JSON carried 5, not "5" (review of 0.1.436)."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import DistributedLoad, LineLoad
        from ogr_core.naming import LoadName
        from ogr_core.project import Project
        from ogr_core.support import HelicalAnchor, SupportInstance
        from ogr_slip2d.helical_anchor_notes import helical_anchor_notes
        ld = DistributedLoad(start=Vertex(0, 0), end=Vertex(1, 0),
                             magnitude_1=3.0, name=5)
        assert LoadName.of(ld) == 5 and type(LoadName.of(ld)) is int
        st = HelicalAnchor(shaft_width=0.25, average_helix_diameter=0.25)
        p = Project("raw")
        p.support_types = [st]
        p.supports = [SupportInstance(type_id="helical_anchor",
                                      type_ref=st.id, name=7,
                                      head=Vertex(0, 0), tail=Vertex(5, 0))]
        args = getattr(helical_anchor_notes(p)[0], "args", {})
        assert args["name"] == 7 and type(args["name"]) is int, args
        try:
            LineLoad(point=Vertex(0, 9), magnitude=1.0,
                     name=12).ground_frame(None)
        except ValueError as exc:
            said = exc.args[0].args["name"]
        assert said == 12 and type(said) is int, said


# ======================================================================
@_requires_qt
class TestDefineSupportNamesEachSetOnce:

    def test_the_rules_of_the_core(self):
        from ogr_core.naming import (COPY_SUFFIX, DEFAULT_RECORD_NAME,
                                     NEW_SET_NAME, copy_name,
                                     default_load_name, first_free_set_name,
                                     name_key, numbered_name,
                                     parse_default_load_name)
        assert NEW_SET_NAME.format(3) == "Type 3"
        assert (COPY_SUFFIX, DEFAULT_RECORD_NAME) == (" (copy)", "Record")
        assert first_free_set_name([]) == "Type 1"
        assert first_free_set_name(["Type 1", " type 3 "]) == "Type 2"
        assert copy_name("X", ["X"]) == "X (copy)"
        assert copy_name("X", ["X", "x (COPY)"]) == "X (copy) (2)"
        # the rule D421 gives the importer and the agent, with find_type's
        # comparison
        assert numbered_name("Clay", ["clay "]) == "Clay (2)"
        assert name_key("  Tie A ") == "tie a"
        # byte for byte the names the window and the agent wrote
        assert default_load_name("distributed", 20) == "Dist 20.0 kN/m²"
        assert default_load_name("line", 50.0) == "Line 50.0 kN/m"
        assert parse_default_load_name("Dist 20.0 kN/m²") == (
            "distributed", 20.0)
        assert parse_default_load_name("Line -5.0 kN/m") == ("line", -5.0)
        # only what «{:.1f}» writes is the program's (review of 0.1.436)
        for given in ("Fence", "Line 50.0 kN/m²", "Dist x kN/m²", "",
                      "Dist 20 kN/m²", "Dist 1e3 kN/m²", "Dist 20.00 kN/m²",
                      "Dist nan kN/m²", "Dist +3.0 kN/m²", "Dist ٣.٠ kN/m²"):
            assert parse_default_load_name(given) is None, given

    def test_add_delete_add_and_duplicate(self):
        """The ficha's case: add, add, delete the second, add, and duplicate
        the first twice. Each set is then the one the agent finds by its
        name -- naming and finding by the name undo each other. Accepted in
        Spanish: the list shows «Tipo 3» and the model keeps «Type 3»."""
        _app()
        from ogr_api.ops.supports import find_type
        from ogr_core.project import Project
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        p = Project("names")
        with _Language("es"):
            d = DefineSupportDialog(p)
            try:
                d._add_row()
                d._add_row()
                d.list_widget.setCurrentRow(1)
                d._delete_row()
                d._add_row()
                for _ in range(2):
                    d.list_widget.setCurrentRow(0)
                    d._duplicate_row()
                names = [r.name for r in d._rows]
                shown = d.list_widget.item(1).text()
                d.accept()
            finally:
                d.setParent(None)
        assert names == ["Type 1", "Type 3", "Type 2", "Type 1 (copy)",
                         "Type 1 (copy) (2)"], names
        assert shown == "Tipo 3  [Anclado en el extremo]", shown
        # find_type's comparison, written here and not imported
        assert len({n.strip().lower() for n in names}) == len(names)
        assert [st._display_name for st in p.support_types] == names
        for st in p.support_types:
            assert find_type(p, st._display_name) is st, st._display_name


# ======================================================================
@_requires_qt
class TestTheNamesReadInTheReadersLanguage:

    _SAMPLES = (
        # stored, the class the set has now, Spanish, English
        ("Type 3", "End Anchored", "Tipo 3", "Type 3"),
        ("Type 1 (2)", "End Anchored", "Tipo 1 (2)", "Type 1 (2)"),
        ("End Anchored (copy)", "End Anchored",
         "Anclado en el extremo (copia)", "End Anchored (copy)"),
        ("End Anchored (copy) (2)", "Grouted Tieback",
         "Anclaje inyectado (copia) (2)", "Grouted Tieback (copy) (2)"),
        ("Type 1 (copy) (copy)", "Soil Nail", "Tipo 1 (copia) (copia)",
         "Type 1 (copy) (copy)"),
        # in English too the window names the class by its own key (D411)
        ("User Defined (2)", "User Defined", "Definido por el usuario (2)",
         "User-defined (2)"),
        ("Norte (copy)", "End Anchored", "Norte (copia)", "Norte (copy)"),
        ("Norte", "End Anchored", "Norte", "Norte"),
        ("Muro (3)", "End Anchored", "Muro (3)", "Muro (3)"),
        ("Type x", "End Anchored", "Type x", "Type x"),
        # what first_free_set_name never writes is the user's (review)
        ("Type 01", "End Anchored", "Type 01", "Type 01"),
        ("Type 0", "End Anchored", "Type 0", "Type 0"),
    )

    def test_the_samples(self):
        """Written apart from the rule (the lesson of 0.1.434: a check that
        walks the rule's own set does not catch its mutant)."""
        from ogr_gui.labels import (is_program_set_name,
                                    set_name_names_its_class,
                                    support_set_name)
        for stored, current, es, en in self._SAMPLES:
            with _Language("es"):
                assert support_set_name(stored, current) == es, stored
            with _Language("en"):
                assert support_set_name(stored, current) == en, stored
        assert [is_program_set_name(s[0]) for s in self._SAMPLES] == [
            True, True, True, True, True, True, False, False, False, False,
            False, False]
        assert [set_name_names_its_class(s[0]) for s in self._SAMPLES] == [
            False, False, True, True, False, True, False, False, False,
            False, False, False]

    def test_a_copy_of_a_set_born_of_another_class(self):
        """A set named by its class reads by the class it has NOW: born End
        Anchored, retyped Grouted Tieback. The class's Spanish is the
        dictionary's own entry; the edit field shows what is stored."""
        _app()
        from ogr_core.project import Project
        from ogr_core.support import GroutedTieback
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        from ogr_gui.i18n import _DICTS
        grouted = _DICTS["es"]["Grouted Tieback"]
        st = GroutedTieback()
        st._display_name = "End Anchored (copy)"     # born End Anchored
        p = Project("combo")
        p.support_types = [st]
        with _Language("es"):
            d = DefineSupportDialog(p)
            try:
                combo = [d.cbo_type.itemText(i)
                         for i in range(d.cbo_type.count())]
                shown = d.list_widget.item(0).text()
                field = d.ed_name.text()
            finally:
                d.setParent(None)
        assert grouted in combo, combo
        assert shown == grouted + " (copia)", shown
        assert field == "End Anchored (copy)", field

    def test_the_list_the_pattern_combo_and_the_edit_field(self):
        _app()
        from ogr_core.project import Project
        from ogr_core.support import EndAnchored
        from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
        from ogr_gui.dialogs.support_pattern_dialog import (
            AddSupportPatternDialog)
        st = EndAnchored()
        st._display_name = "Type 3"
        p = Project("list")
        p.support_types = [st]
        for code, row, choice in (
                ("es", "Tipo 3  [Anclado en el extremo]", "Tipo 3"),
                ("en", "Type 3  [End Anchored]", "Type 3")):
            with _Language(code):
                d = DefineSupportDialog(p)
                pat = AddSupportPatternDialog(p)
                try:
                    assert d.list_widget.item(0).text() == row, code
                    assert d.ed_name.text() == "Type 3", code
                    assert pat.cbo_type.itemText(0) == choice, code
                    # accepted in the reader's language, the model keeps
                    # the stored name, not the label
                    d.accept()
                finally:
                    d.setParent(None)
                    pat.setParent(None)
            assert p.support_types[0]._display_name == "Type 3", code

    def test_the_force_diagram_names_the_class_once(self):
        """The bracket is decided by the name SHOWN: an unnamed support (a
        pattern's) shows its set's, which may say the class (review)."""
        _app()
        from ogr_core.geometry import Vertex
        from ogr_core.project import Project
        from ogr_core.support import EndAnchored, SupportInstance
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)
        copy_set, plain, typed = EndAnchored(), EndAnchored(), EndAnchored()
        copy_set._display_name = "End Anchored (copy)"
        typed._display_name = "Type 3"
        p = Project("diagram")
        p.support_types = [copy_set, plain, typed]
        p.supports = [
            SupportInstance(type_id="end_anchored", type_ref=copy_set.id,
                            name="", head=Vertex(0, 0), tail=Vertex(5, 0)),
            SupportInstance(type_id="end_anchored", type_ref=copy_set.id,
                            name="End Anchored (copy)", head=Vertex(0, 1),
                            tail=Vertex(5, 1)),
            SupportInstance(type_id="end_anchored", type_ref=plain.id,
                            name="", head=Vertex(0, 2), tail=Vertex(5, 2)),
            SupportInstance(type_id="end_anchored", type_ref=typed.id,
                            name="", head=Vertex(0, 3), tail=Vertex(5, 3))]
        with _Language("es"):
            w = SupportForceDiagramWindow(p)
            try:
                items = [w.cbo.itemText(i) for i in range(w.cbo.count())]
            finally:
                w.setParent(None)
        assert items == ["Anclado en el extremo (copia)",
                         "Anclado en el extremo (copia)",
                         "Anclado en el extremo",
                         "Tipo 3  [Anclado en el extremo]"], items


# ======================================================================
@_requires_qt
class TestTheRecordName:

    def test_the_two_lists_and_the_edit_field(self):
        _app()
        from ogr_core.loads.seismic_record import SeismicRecord
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.dialogs.project_settings_dialog import _SeismicPage
        from ogr_gui.dialogs.seismic_records_dialog import SeismicRecordsDialog
        p = build_demo_project()
        p.seismic_records = [
            SeismicRecord(name="Record", dt=0.02,
                          accelerations=[0.0, 0.1, 0.0]),
            SeismicRecord(name="El Centro", dt=0.02,
                          accelerations=[0.0, 0.2, 0.0])]
        for code, word in (("es", "Registro"), ("en", "Record")):
            with _Language(code):
                d = SeismicRecordsDialog(p)
                page = _SeismicPage(p.settings, p)
                try:
                    assert [d.list.item(i).text() for i in range(2)] == [
                        word, "El Centro"], code
                    d.list.setCurrentRow(0)
                    assert d.ed_name.text() == "Record", code
                    assert page.cmb_record.itemText(1).startswith(
                        word + " — "), page.cmb_record.itemText(1)
                    assert page.cmb_record.itemText(2).startswith(
                        "El Centro — ")
                    # applied in the reader's language: the model keeps
                    # «Record», not the label
                    d.apply()
                finally:
                    d.setParent(None)
                    page.setParent(None)
            assert [r.name for r in p.seismic_records] == [
                "Record", "El Centro"], code

    def test_the_newmark_note(self):
        assert "«Registro»" in _es("newmark_record")
        assert "«El Centro»" in _es("newmark_given")


# ======================================================================
@_requires_qt
class TestALoadByItsMagnitudeNow:

    def _loads(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import (DistributedLoad, LineLoad,
                                          LoadDistribution)
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        born = DistributedLoad(start=Vertex(5, 25), end=Vertex(20, 25),
                               magnitude_1=20.0, name="Dist 20.0 kN/m²")
        born.magnitude_1 = 35.0                  # changed since
        p.add_distributed_load(born)
        p.add_distributed_load(DistributedLoad(
            start=Vertex(1, 25), end=Vertex(3, 25), magnitude_1=8.0))
        p.add_distributed_load(DistributedLoad(
            start=Vertex(3, 25), end=Vertex(4, 25), magnitude_1=10.0,
            magnitude_2=30.0, distribution=LoadDistribution.TRAPEZOIDAL))
        p.add_line_load(LineLoad(point=Vertex(10, 25), magnitude=50.0,
                                 name="Line 50.0 kN/m"))
        p.add_line_load(LineLoad(point=Vertex(12, 25), magnitude=5.0,
                                 name="Fence, east"))
        return p

    def test_the_context_menu_is_the_reference(self):
        """The canvas has always headed a load's menu by its kind and its
        magnitude now (a varying one by its two ends, the owner's decision
        in the review): an unnamed load reads the same everywhere."""
        _app()
        from PySide6.QtCore import QPoint
        from test_labels_spanish_v1321 import _menu_texts
        from ogr_gui.canvas import CanvasView
        from ogr_gui.labels import load_label
        p = self._loads()
        view = CanvasView(p)
        try:
            for code in ("es", "en"):
                with _Language(code):
                    heads = []
                    for kind, idx, load in (
                            ("distributed", 0, p.distributed_loads[0]),
                            ("distributed", 1, p.distributed_loads[1]),
                            ("distributed", 2, p.distributed_loads[2]),
                            ("line", 0, p.line_loads[0])):
                        head = _menu_texts(
                            lambda: view._show_load_context_menu(
                                QPoint(0, 0), (kind, idx)))[0]
                        assert load_label(load) == head, (code, head)
                        heads.append(head)
                    # a name the user gave is data
                    assert load_label(p.line_loads[1]) == "Fence, east"
                if code == "es":
                    assert heads == ["Carga distribuida — 35.0 kN/m²",
                                     "Carga distribuida — 8.0 kN/m²",
                                     "Carga distribuida — 10.0–30.0 kN/m²",
                                     "Carga lineal — 50.0 kN/m"], heads
        finally:
            view.setParent(None)
        assert p.distributed_loads[0].name == "Dist 20.0 kN/m²"

    def test_the_data_tip(self):
        from ogr_gui.data_tips import DataTipMode as M
        from ogr_gui.data_tips import load_tip
        p = self._loads()
        with _Language("es"):
            assert load_tip(p.distributed_loads[0], M.MINIMUM) == (
                "Carga distribuida — 35.0 kN/m²")
            assert load_tip(p.line_loads[0], M.MINIMUM) == (
                "Carga lineal — 50.0 kN/m")
            assert load_tip(p.line_loads[1], M.MINIMUM) == (
                "Fence, east: 5 kN/m")
            full = load_tip(p.line_loads[0], M.MAXIMUM).splitlines()
            assert full[:2] == ["Carga lineal — 50.0 kN/m",
                                "magnitud: 50 kN/m"], full
            full = load_tip(p.distributed_loads[0], M.MAXIMUM).splitlines()
            assert full[:2] == ["Carga distribuida — 35.0 kN/m²",
                                "magnitud 1: 35 kPa"], full
        with _Language("en"):
            assert load_tip(p.line_loads[1], M.MINIMUM) == (
                "Fence, east: 5 kN/m")
            assert load_tip(p.distributed_loads[0], M.MINIMUM) == (
                "Distributed Load — 35.0 kN/m²")

    def test_a_random_variable_is_headed_by_its_load(self):
        from ogr_core.statistics import available_variables
        from ogr_gui.labels import random_variable_label
        p = self._loads()
        rvs = {v.key: v for v in available_variables(p)}
        born, _bare, varying = p.distributed_loads[:3]
        rv = rvs["distributed_load:%s:magnitude_1" % born.id]
        assert rv.label == "Dist 20.0 kN/m² — magnitude_1"     # stored
        with _Language("es"):
            assert random_variable_label(rv, p) == (
                "Carga distribuida — 35.0 kN/m² — magnitud 1")
            # without the project, or with the load gone: the stored head
            assert random_variable_label(rv) == (
                "Carga distribuida — 20.0 kN/m² — magnitud 1")
            # a varying load by its two ends, for either magnitude
            for param, word in (("magnitude_1", "1"), ("magnitude_2", "2")):
                rv = rvs["distributed_load:%s:%s" % (varying.id, param)]
                assert random_variable_label(rv, p) == (
                    "Carga distribuida — 10.0–30.0 kN/m² — magnitud "
                    + word), param
        with _Language("en"):
            rv = rvs["distributed_load:%s:magnitude_1" % born.id]
            assert random_variable_label(rv, p) == (
                "Distributed Load — 35.0 kN/m² — magnitude 1")


# ======================================================================
_RUN: dict = {}


def _factored_run():
    """The demo with a permanent load on the crest the critical circle
    starts on, created at 15 kN/m², set to 25 for the run and to 40 after
    it, so the name, the run and the model say three different magnitudes."""
    if _RUN:
        return _RUN["run"]
    from ogr_core.geometry import Vertex
    from ogr_core.loads import DistributedLoad, LoadAction
    from ogr_core.project.demo import build_demo_project
    from ogr_slip2d.analysis_runner import run_analysis
    p = build_demo_project()
    load = DistributedLoad(start=Vertex(21, 25), end=Vertex(24.5, 25),
                           magnitude_1=15.0, action=LoadAction.PERMANENT,
                           name="Dist 15.0 kN/m²")     # as it was born
    load.magnitude_1 = 25.0
    p.add_distributed_load(load)
    s = p.settings
    s.methods.enabled_methods = ["bishop_simplified"]
    s.search.grid_nx = s.search.grid_ny = 3
    s.search.radius_increment = 3
    s.design_standard.enabled = True
    s.design_standard.apply_preset("eurocode7_da1c1")
    out = run_analysis(p)
    load.magnitude_1 = 40.0
    _RUN["run"] = (p, out)
    return _RUN["run"]


@_requires_qt
class TestTheRunsMagnitude:

    def test_the_results_panel(self):
        from ogr_gui.widgets.results_dock import load_factor_lines
        p, out = _factored_run()
        crit = out.results["bishop_simplified"].critical
        name = next(iter(crit.slices.load_factors.values()))[3]
        assert name == "Dist 15.0 kN/m²"       # the text the agent reads
        with _Language("es"):
            lines = load_factor_lines(crit)
        assert "Carga distribuida — 25.0 kN/m²: carga permanente" in lines, (
            lines)
        with _Language("en"):
            lines = load_factor_lines(crit)
        assert "Distributed Load — 25.0 kN/m²: permanent load" in lines, (
            lines)

    def test_one_name_per_load_for_the_whole_run(self):
        """The run keeps one ``LoadName`` per load, shared by every surface
        that carries it: a new one per surface cost about 160 bytes per load
        and per stored evaluation (review of 0.1.436)."""
        p, out = _factored_run()
        res = out.results["bishop_simplified"]
        names = {id(lf[3])
                 for r in (res.evaluations or [])
                 for lf in (getattr(getattr(r, "slices", None),
                                    "load_factors", None) or {}).values()}
        assert len(names) == 1, len(names)

    def test_the_window_s_pdf_and_the_agent_s(self):
        import os
        import tempfile

        import reportlab.platypus as platypus

        import ogr_core.report.report_generator as RG
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import load_name_label
        p, out = _factored_run()
        cells = []
        real = platypus.Paragraph

        class Spy(real):
            def __init__(self, text, *a, **k):
                cells.append(str(text))
                super().__init__(text, *a, **k)

        # both: the report imports it at the top, and its tables use it
        platypus.Paragraph = RG.Paragraph = Spy
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with _Language("es"):
                    RG.generate_report(p, out.results,
                                       os.path.join(tmp, "w.pdf"),
                                       factor_report=out.factor_report,
                                       translate=note_text,
                                       load_name=load_name_label)
                window = list(cells)
                cells.clear()
                RG.generate_report(p, out.results, os.path.join(tmp, "a.pdf"),
                                   factor_report=out.factor_report)
                agent = list(cells)
        finally:
            platypus.Paragraph = RG.Paragraph = real
        # an unnamed load by its heading alone, which already says «load»
        assert "<b>Carga distribuida — 25.0 kN/m²</b>" in window, [
            c for c in window if "Carga" in c]
        # the agent's report keeps the text the run kept
        assert "<b>Load 'Dist 15.0 kN/m²'</b>" in agent, [
            c for c in agent if "Load" in c]


# ======================================================================
@_requires_qt
class TestTheNotesNameByKind:

    def test_the_sets(self):
        said = _es("ambiguous_user_defined")
        assert ("clase «Definido por el usuario»" in said
                and "(«Definido por el usuario», «Definido por el usuario "
                    "(2)»)" in said
                and "el primero, «Definido por el usuario»" in said), said
        said = _es("ambiguous_given")
        assert "(«Tie A», «Tie B»)" in said and "«Tie A». " in said, said
        # English quotes in an English sentence (review of 0.1.436)
        said = _en("ambiguous_given")
        assert "('Tie A', 'Tie B'). The first, 'Tie A', is used." in said, (
            said)
        said = _es("orphan", 0)
        assert "«S7»" in said and "se usa «Tipo 3»" in said, said
        said = _es("infinite_unnamed_set")
        assert said.startswith("El soporte «N1» (Geosintético) "), said
        said = _es("infinite_type_n")
        assert said.startswith("El soporte «Tipo 4» (Tipo 4) "), said

    def test_an_unnamed_support_by_its_class_and_its_head(self):
        """The owner's decision in the review of 0.1.436: by its class and
        its head, so the orphan's note is not circular and the supports of a
        pattern, born unnamed, read apart. Never by its id."""
        said = _es("orphan", 1)
        assert said.startswith("El soporte «Bulón de suelo en (0.00, 1.00)» "
                               "se refiere"), said
        said = _en("orphan", 1)
        assert said.startswith("Support 'Soil Nail at (0.00, 1.00)' refers"), (
            said)
        said = _es("reversed_unnamed")
        assert said.startswith("El soporte «Bulón de suelo en (54.00, 8.00)» "
                               "tiene la cabeza"), said
        said = _es("infinite_unnamed_support")
        assert said.startswith("El soporte «Geosintético en (43.50, 8.00)» "
                               "(Geosintético) "), said
        said = _es("slope_angle_support")
        assert said.endswith(": Bulón de suelo en (30.00, 20.00)."), said
        # a class this build does not know: its identifier, never nothing
        from ogr_core.geometry import Vertex
        from ogr_core.project import Project
        from ogr_core.support import SupportInstance
        from ogr_gui.core_messages import note_text
        from ogr_slip2d.support_notes import support_identity_notes
        p = Project("future")
        p.supports = [SupportInstance(type_id="future_class", name="",
                                      type_ref="gone", head=Vertex(6, 7),
                                      tail=Vertex(9, 7))]
        with _Language("es"):
            said = note_text(support_identity_notes(p)[0], project=p)
        assert said.startswith("El soporte «future_class en (6.00, 7.00)» "), (
            said)

    def test_a_support_named_since_the_note(self):
        """The core wrote the id (or the class's identifier) for want of a
        name; given one since, the support reads by it, not by the id."""
        from ogr_core.messages import Joined
        from ogr_core.project import Project
        from ogr_core.support import SoilNail, SupportInstance
        from ogr_core.geometry import Vertex
        from ogr_gui.labels import support_names_label
        s = SupportInstance(type_id="soil_nail", name="Norte",
                            head=Vertex(0, 0), tail=Vertex(5, 0))
        p = Project("since")
        p.support_types = [SoilNail()]
        p.supports = [s]
        with _Language("es"):
            for written in (s.id, "soil_nail", "Norte"):
                assert support_names_label(
                    p, Joined([written], refs=[s.id])) == "Norte", written
            # a name the note was written with, the support named otherwise
            # now: the note's
            assert support_names_label(
                p, Joined(["Sur"], refs=[s.id])) == "Sur"

    def test_the_helical_and_reversed_names(self):
        assert "del soporte «plateless»" in _es("helical", 0)
        assert "del soporte «Anclaje helicoidal»" in _es("helical", 1)
        for i in (2, 3):
            assert "del soporte «Tipo 2»" in _es("helical", i)
        assert _es("reversed_type_n").startswith(
            "El soporte «Tipo 2» tiene la cabeza")
        assert _es("reversed_given").startswith(
            "El soporte «Bolt 'B' 1» tiene la cabeza")

    def test_a_support_that_could_not_be_priced(self):
        """It read «support <id> could not be priced» whatever its name. The
        id stays in the English (the agent's)."""
        assert _es("failure", 0) == (
            "el soporte Nail A no se pudo calcular: the soil around it "
            "cannot be read"), _es("failure", 0)
        assert _es("failure", 1) == (
            "2 soportes no se pudieron calcular: Nail A (reason a); Bulón de "
            "suelo en (31.00, 19.00) (reason b)"), _es("failure", 1)
        assert _en("failure", 1) == (
            "2 supports could not be priced: Nail A (reason a); Soil Nail at "
            "(31.00, 19.00) (reason b)"), _en("failure", 1)

    def test_the_loads(self):
        from ogr_gui.core_messages import error_text
        said = _es("slope_angle")
        # each by its own, joined by «; » on screen: «Fence, east» is one
        assert said.endswith(": Carga distribuida — 20.0 kN/m²; Carga "
                             "lineal — 50.0 kN/m; Fence, east."), said
        refusals = {name: (ll, exc) for name, ll, exc
                    in _note_models()["line_refusals"]}
        for name, es, en in (
                ("line_needs_ground", "Carga lineal «50.0 kN/m»: ",
                 "Line load 50.0 kN/m: "),
                ("line_off_ground",
                 "La carga lineal «50.0 kN/m» en (10, 99) ",
                 "Line load 50.0 kN/m at (10, 99) "),
                ("line_off_ground_unnamed",
                 "La carga lineal «50.0 kN/m» en (10, 99) ",
                 "Line load 50.0 kN/m at (10, 99) ")):
            ll, exc = refusals[name]
            scope = SimpleNamespace(line_loads=[ll], distributed_loads=[])
            for code, want in (("es", es), ("en", en)):
                with _Language(code):
                    said = error_text(exc, project=scope)
                assert said.startswith(want), (name, code, said)

    def test_compute_s_refusal_by_the_magnitude_now(self):
        """Compute's own check, as the window says it (against its project):
        a line load born at 50 and set to 80 reads 80, never 50 nor its id
        (review of 0.1.436)."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads.loads import LineLoad, LoadOrientation
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.core_messages import note_text
        from ogr_slip2d.analysis_runner import check_analysis_settings
        for name in ("Line 50.0 kN/m", ""):
            p = build_demo_project()
            ll = LineLoad(point=Vertex(10, 5), magnitude=50.0, name=name,
                          orientation=LoadOrientation.NORMAL_TO_BOUNDARY)
            ll.magnitude = 80.0
            p.add_line_load(ll)
            why = check_analysis_settings(p)
            with _Language("es"):
                said = [note_text(x, project=p) for x in why]
            assert any("La carga lineal «80.0 kN/m» en (10, 5)" in s
                       for s in said), (name, said)


# ======================================================================
class TestTheWindowSaysItAgainstTheProject:
    """The rules above need the project; a call that does not pass it shows
    the id, or the magnitude a load was born with (review of 0.1.436). The
    refusals of every task and the first note of Compute pass it."""

    _SITES = (
        "note_text(p, project=self.project) for p in exc.problems",
        "note_text(p, project=self.project)\n                    for p in "
        "exc.problems",
        "note_text(p, project=self.project)\n"
        "                                            for p in _why",
        "first = note_line(notes[0], project=self.notes_scope())",
        "first = note_line(self.last_compute_warnings[0],\n"
        "                              project=self.notes_scope())",
    )

    def test_the_calls(self):
        src = (_ROOT / "ogr_gui" / "main_window.py").read_text(
            encoding="utf-8")
        for site in self._SITES:
            assert site in src, site
        assert "note_text(p)" not in src
        assert "note_line(notes[0])" not in src
        assert "note_line(self.last_compute_warnings[0])" not in src


# ======================================================================
class TestTheCensusSeesTheProgramsNames:

    def test_the_data_names_are_only_the_users(self):
        from test_labels_spanish_v1321 import _data_names
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad, LineLoad
        from ogr_core.loads.seismic_record import SeismicRecord
        from ogr_core.project.demo import build_demo_project
        from ogr_core.support import EndAnchored
        p = build_demo_project()
        sets = []
        for given in ("Type 3", "End Anchored (copy)", "Norte",
                      "Norte (copy)"):
            st = EndAnchored()
            st._display_name = given
            sets.append(st)
        p.support_types = sets
        p.add_distributed_load(DistributedLoad(
            start=Vertex(1, 25), end=Vertex(3, 25), magnitude_1=8.0,
            name="Dist 8.0 kN/m²"))
        p.add_line_load(LineLoad(point=Vertex(5, 25), magnitude=5.0,
                                 name="Fence"))
        p.seismic_records = [SeismicRecord(name="Record"),
                             SeismicRecord(name="El Centro")]
        names = _data_names(p)
        for program in ("Type 3", "End Anchored (copy)", "Dist 8.0 kN/m²",
                        "Record"):
            assert program not in names, (program, names)
        for user in ("Norte", "Norte (copy)", "Fence", "El Centro"):
            assert user in names, (user, names)
