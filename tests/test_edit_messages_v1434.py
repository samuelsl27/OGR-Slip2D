# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.434 (D412) -- the core's messages and the undo step names in the
reader's language, with the agent's English unchanged byte for byte.

Invariants protected here:

* **The agent's English is 0.1.433's.** ``_V1433`` and ``_STEPS_1433`` were
  written by 0.1.433 (73c6d33), measured by CALLING its functions on a
  ``git archive`` of that tree (Change Slope Angle, Simplify, Expand /
  Shrink, the offset, the strong-motion reader, and ``project_history``
  after the agent's four edits) -- not printed by this code. For a change of
  text the reference is what the old program said, and the change is
  defined as not moving it: ``str(exc)``, the notes and the step names are
  those literals, and the exception types are the same.
* **The window says them in Spanish**, through their codes (``error_text``,
  ``note_text``): the status bar, the warning boxes, the Edit menu and its
  status line, the notes panel, the window's PDF, the Seismic Records
  dialog -- each by the real handler, its dialogs replaced and put back.
* **A random variable is named by its label, never by its key with a
  UUID**, also in an undo step whose variable was deleted since (the
  owner's decision, 2026-11-09): the step's capture names it.
* **The censuses see the paths:** an exception's text on screen goes through
  ``error_text`` and, when the handler catches more than the core's
  refusals, inside a translated frame; an undo step's name is a literal or a
  step-name function, never built in place; the functions this version
  coded write no sentence without its code. Each census checks itself on
  sources of its own, and each rule removed makes its check fail.

One main window with the demo for the whole file; no search, no modal
dialog.

v0.1.473 (spec 010) -- the core's sources are read in the tree of the
``ogr_core`` that is imported (``tests/_sources.py``), which fails
rather than find nothing: the core left this repository for OGR-Core.
"""
from __future__ import annotations

import sys

import ast
import json
import os
import re
import string
import tempfile
from contextlib import contextmanager
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
import _sources as S  # noqa: E402

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


# ======================================================================
# The English of 0.1.433, measured (see the header). Rows (code, args, text).
_V1433 = [
    ("geometry.vertex_ref", {}, "A vertex is an index or an [x, y] point."),
    ("geometry.vertex_out_of_range", {"ref": 99, "last": 5},
     "Vertex index 99 is outside 0..5."),
    ("geometry.not_a_vertex", {"x": 1.5, "y": 2.5},
     "(1.5, 2.5) is not a vertex of the External boundary."),
    ("geometry.toe_is_crest", {}, "The toe and the crest are the same vertex."),
    ("geometry.toe_not_lower", {}, "The toe must be lower than the crest."),
    ("geometry.face_not_on_ground", {},
     "The toe and the crest are not joined by the ground surface."),
    ("geometry.slope_mode_unknown",
     {"modes": "('horizontal', 'vertical', 'rotate')"},
     "mode is one of ('horizontal', 'vertical', 'rotate')."),
    ("geometry.angle_out_of_range", {},
     "The new overall angle must be between 0° and 90°."),
    ("geometry.at_toe_elevation", {},
     "A face vertex at the toe's elevation cannot be projected horizontally."),
    ("geometry.vertical_face", {},
     "A vertical face cannot be projected vertically."),
    ("geometry.above_toe", {},
     "A face vertex above the toe cannot be projected vertically."),
    ("geometry.no_external", {}, "The model has no External boundary."),
    ("geometry.keep_benches_rotate", {},
     "keep_benches is only read by the horizontal and vertical projections, "
     "not by 'rotate'."),
    ("geometry.change_or_target", {},
     "Give exactly one of change_deg or target_deg."),
    ("geometry.face_runs_into", {},
     "At that angle the face runs into the rest of the External boundary "
     "(past the next vertex of the crest or the toe)."),
    ("geometry.supports_not_moved", {"n": 2, "names": "Anchor A, End Anchored"},
     "2 support(s) had their head on the old face and were not moved: "
     "Anchor A, End Anchored."),
    ("geometry.loads_not_moved", {"n": 1, "names": "Pile"},
     "1 load(s) were on the old face and were not moved: Pile."),
    ("geometry.tolerance_not_positive", {},
     "the simplification tolerance must be positive"),
    ("geometry.tolerance_too_coarse", {"epsilon": 1000.0, "n": 2, "need": 3},
     "a tolerance of 1000 leaves 2 vertices; this boundary needs at least 3"),
    ("geometry.external_not_closed", {}, "External must be a closed polyline."),
    ("geometry.external_too_few", {}, "External has too few vertices."),
    ("geometry.polyline_too_few", {}, "Polyline needs at least 2 vertices."),
    ("geometry.endpoints_off_external", {},
     "Both endpoints of the polyline must lie on the External Boundary (use "
     "snap — green cross)."),
    ("geometry.expand_smaller", {},
     "Expand produced a smaller polygon — intermediate points are probably "
     "INSIDE the External. Use Shrink, or redraw with points outside."),
    ("geometry.offset_needs_polygon", {},
     "offset_polygon requires a closed polygon with ≥3 vertices"),
    ("seismic.no_numeric_data", {}, "no numeric data"),
    ("seismic.too_few_samples", {}, "fewer than two samples"),
    ("seismic.time_not_increasing", {}, "non-increasing time column"),
    ("seismic.step_not_constant", {}, "time step is not constant"),
    ("seismic.needs_interval", {}, "single-column file needs a time interval"),
    ("step.paint_material", {"x": 10.0, "y": 5.0},
     "Paint material at (10.00, 5.00)"),
    ("step.offset_external", {"distance": 1.0}, "Offset External (+1.00 m)"),
    ("step.expand_external", {}, "Expand/Shrink (expand)"),
    ("step.shrink_external", {}, "Expand/Shrink (shrink)"),
    ("step.edit_boundary", {"op": "translate"}, "Edit boundary (translate)"),
    ("step.hydraulic", {"material": "Silty clay"},
     "Hydraulic properties of Silty clay"),
    ("step.random_variable", {"key": "material_strength:m1:cohesion"},
     "Random variable material_strength:m1:cohesion"),
    ("step.delete_random_variable", {"key": "material_strength:m1:cohesion"},
     "Delete random variable material_strength:m1:cohesion"),
    ("step.delete_all_random_variables", {}, "Delete random variable all"),
]

#: What 0.1.433's ``project_history`` gave after the agent's edits of
#: ``_agent_history`` ({ID} the demo material's id, {KEY} the cohesion's key).
_STEPS_1433 = [
    "Edit boundary (translate)", "Edit boundary (set_vertices)",
    "Hydraulic properties of Silty clay", "Hydraulic properties of {ID}",
    "Random variable {KEY}", "Delete random variable {KEY}",
    "Random variable {KEY}", "Delete random variable all",
]

#: 0.1.433's Offset External and Expand/Shrink names, its f-strings
#: (``main_window.py``) with the values the tests use.
_WINDOW_STEPS_1433 = {
    "offset": "Offset External (+1.00 m)",
    "expand": "Expand/Shrink (expand)", "shrink": "Expand/Shrink (shrink)",
}

#: The args the engine passes to the notes whose kinds this version
#: declared, with identifiers as they are stored (a standard's id, a
#: variable's three-part key): the samples the F1 census of
#: ``test_spanish_paths_v1433`` reads. Its samples elsewhere held no
#: standard, and keys of two parts its predicate does not take (review of
#: 0.1.434), so it could not see a kind taken away.
_V1434_KINDS = [
    ("design.summary",
     {"standard": "eurocode7_da1c2", "materials": 2, "loads": 0}),
    ("stat.vars_none",
     {"n": 1, "keys": "material_strength:3f0c2b9e-6a1d-4c8e-9b7a-1d2e3f4a5b6c:cohesion"}),
    ("stat.vars_not_sampled",
     {"n": 1, "total": 2,
      "keys": "material_strength:3f0c2b9e-6a1d-4c8e-9b7a-1d2e3f4a5b6c:cohesion"}),
    ("stat.vars_not_swept",
     {"n": 1, "total": 2, "keys": "seismic::kh"}),
    ("stat.var_orphan",
     {"key": "material_strength:3f0c2b9e-6a1d-4c8e-9b7a-1d2e3f4a5b6c:cohesion"}),
    ("stat.vars_hydraulic_only",
     {"keys": "hydraulic:3f0c2b9e-6a1d-4c8e-9b7a-1d2e3f4a5b6c:ks"}),
    ("stat.vars_hydraulic",
     {"n": 1, "total": 2, "keys": "hydraulic:3f0c2b9e-6a1d-4c8e-9b7a-1d2e3f4a5b6c:ks"}),
    ("stat.var_hydraulic",
     {"key": "hydraulic:3f0c2b9e-6a1d-4c8e-9b7a-1d2e3f4a5b6c:ks"}),
    ("step.edit_boundary", {"op": "set_vertices"}),
]


# ======================================================================
@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(before)


@contextmanager
def _swapped(owner, name, value):
    """``owner.name`` replaced for the block and put back exactly."""
    raw = owner.__dict__.get(name) if hasattr(owner, "__dict__") else None
    had = hasattr(owner, "__dict__") and name in owner.__dict__
    setattr(owner, name, value)
    try:
        yield
    finally:
        if had:
            setattr(owner, name, raw)
        else:
            delattr(owner, name)


_WINDOW: list = []
_KEPT: list = []


def _window():
    """The main window, built once, with the demo loaded."""
    if not _WINDOW:
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        w.project.is_dirty = False
        w.act_load_demo()
        w.project.is_dirty = False
        _WINDOW.append(w)
    return _WINDOW[0]


def _raised(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        return exc
    raise AssertionError("nothing was raised")


def _demo():
    from ogr_core.project.demo import build_demo_project
    return build_demo_project()


def _fields(template):
    return {f for _t, f, _s, _c in string.Formatter().parse(template) if f}


# ======================================================================
class TestTheEnglishIs0433s:
    """The catalogues write 0.1.433's English, and the core raises it."""

    def test_every_code_writes_its_english(self):
        from ogr_core.geometry.messages import GEOMETRY_MESSAGES
        from ogr_core.loads.messages import SEISMIC_NOTES
        from ogr_core.messages import english
        from ogr_core.project.step_names import STEP_NAMES
        cat = {**GEOMETRY_MESSAGES, **SEISMIC_NOTES, **STEP_NAMES}
        for code, args, text in _V1433:
            assert english(cat, code, args) == text, code
        # every code of the three catalogues has its sample
        assert {c for c, _a, _t in _V1433} == set(cat)

    def test_the_core_raises_it(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry import expand_shrink as ES
        from ogr_core.geometry import slope_angle as SA
        from ogr_core.geometry.cleanup import simplify_boundary
        from ogr_core.geometry.transforms import offset_polygon
        from ogr_core.project import Project

        def V(x, y):
            return Vertex(float(x), float(y))
        ext = _demo().external_boundary()
        sq = Polyline(vertices=[V(0, 0), V(10, 0), V(10, 10), V(0, 10)],
                      closed=True)
        calls = {
            "geometry.vertex_ref": lambda: SA.vertex_index(ext, True),
            "geometry.vertex_out_of_range": lambda: SA.vertex_index(ext, 99),
            "geometry.not_a_vertex": lambda: SA.vertex_index(ext, (1.5, 2.5)),
            "geometry.toe_is_crest": lambda: SA.change_slope_angle(
                _demo(), 3, 3, target_deg=30.0),
            "geometry.toe_not_lower": lambda: SA.change_slope_angle(
                _demo(), (25, 25), (35, 15), target_deg=30.0),
            "geometry.face_not_on_ground": lambda: SA.change_slope_angle(
                _demo(), (0, 0), (0, 25), target_deg=30.0),
            "geometry.slope_mode_unknown": lambda: SA.change_slope_angle(
                _demo(), (35, 15), (25, 25), target_deg=30.0, mode="x"),
            "geometry.angle_out_of_range": lambda: SA.change_slope_angle(
                _demo(), (35, 15), (25, 25), target_deg=90.0),
            "geometry.at_toe_elevation": lambda: SA.new_face(
                [V(0, 0), V(2, 0), V(5, 5), V(9, 5)], [0, 1, 2], 45.0,
                "horizontal", False),
            "geometry.vertical_face": lambda: SA.new_face(
                [V(0, 0), V(0, 5), V(5, 5)], [0, 1], 45.0, "vertical", True),
            "geometry.above_toe": lambda: SA.new_face(
                [V(0, 0), V(0, 2), V(5, 5), V(9, 5)], [0, 1, 2], 45.0,
                "vertical", False),
            "geometry.no_external": lambda: SA.change_slope_angle(
                Project(), 0, 1, target_deg=30.0),
            "geometry.keep_benches_rotate": lambda: SA.change_slope_angle(
                _demo(), (35, 15), (25, 25), target_deg=30.0, mode="rotate",
                keep_benches=True),
            "geometry.change_or_target": lambda: SA.change_slope_angle(
                _demo(), (35, 15), (25, 25), target_deg=30.0, change_deg=5.0),
            "geometry.face_runs_into": lambda: SA.change_slope_angle(
                _demo(), (35, 15), (25, 25), target_deg=5.0),
            "geometry.tolerance_not_positive": lambda: simplify_boundary(
                ext, 0.0),
            "geometry.tolerance_too_coarse": lambda: simplify_boundary(
                ext, 1000.0),
            "geometry.external_not_closed": lambda: ES.expand_shrink_external(
                Polyline(vertices=[V(0, 0), V(10, 0), V(10, 10)]),
                Polyline(vertices=[V(0, 5), V(5, 5)])),
            "geometry.external_too_few": lambda: ES.expand_shrink_external(
                Polyline(vertices=[V(0, 0), V(10, 0)], closed=True),
                Polyline(vertices=[V(0, 5), V(5, 5)])),
            "geometry.polyline_too_few": lambda: ES.expand_shrink_external(
                sq, Polyline(vertices=[V(0, 5)])),
            "geometry.endpoints_off_external": lambda: ES.expand_shrink_external(
                sq, Polyline(vertices=[V(3, 3), V(4, 12), V(7, 7)])),
            "geometry.expand_smaller": lambda: ES.expand_shrink_external(
                sq, Polyline(vertices=[V(0, 5), V(5, -1), V(10, 5)])),
            "geometry.offset_needs_polygon": lambda: offset_polygon(
                Polyline(vertices=[V(0, 0), V(10, 0), V(10, 10)]), 1.0),
        }
        old = {c: t for c, _a, t in _V1433}
        for code, fn in calls.items():
            exc = _raised(fn)
            assert str(exc) == old[code], code
            assert exc.args[0].code == code, code
            assert isinstance(exc, ValueError), code      # the type stays
        for fn in (lambda: ES.apply_expand_shrink(
                       Project(), Polyline(vertices=[V(0, 5), V(5, 5)])),
                   lambda: ES.apply_external_offset(Project(), 1.0)):
            exc = _raised(fn)
            assert type(exc).__name__ == "ExpandShrinkError"
            assert str(exc) == old["geometry.no_external"]

    def test_the_notes_and_the_seismic_reader(self):
        from ogr_core.geometry import Vertex
        from ogr_core.geometry.slope_angle import change_slope_angle
        from ogr_core.loads import LineLoad
        from ogr_core.loads.seismic_record import (AccelerationUnit,
                                                   parse_record_text)
        from ogr_core.support import SupportInstance
        p = _demo()
        p.supports = [
            SupportInstance(head=Vertex(30.0, 20.0), tail=Vertex(24.0, 14.0),
                            type_id="end_anchored", name="Anchor A"),
            SupportInstance(head=Vertex(32.0, 18.0), tail=Vertex(26.0, 12.0),
                            type_id="end_anchored", name="End Anchored")]
        p.line_loads = [LineLoad(point=Vertex(30.0, 20.0), magnitude=10.0,
                                 name="Pile")]
        notes = change_slope_angle(p, (35, 15), (25, 25),
                                   target_deg=30.0)["notes"]
        old = {c: t for c, _a, t in _V1433}
        assert notes == [old["geometry.supports_not_moved"],
                         old["geometry.loads_not_moved"]]
        assert [n.code for n in notes] == ["geometry.supports_not_moved",
                                           "geometry.loads_not_moved"]
        unit = list(AccelerationUnit)[0]
        for text, code in (("a b\n", "seismic.no_numeric_data"),
                           ("0 1\n", "seismic.too_few_samples"),
                           ("0 1\n0 2\n", "seismic.time_not_increasing"),
                           ("0 1\n0.1 2\n0.3 3\n", "seismic.step_not_constant"),
                           ("1\n2\n3\n", "seismic.needs_interval")):
            note = parse_record_text(text, unit)[2]
            assert note == old[code] and note.code == code, code
        fine = parse_record_text("0 1\n0.1 2\n0.2 3\n", unit)[2]
        assert fine == "" and type(fine) is str      # D412: "" stays ""


class TestTheAgentReadsTheSame:
    """Through ``ogr_api``: the refusals and the history, byte for byte."""

    def _agent_history(self):
        from ogr_api import Workspace, call
        from ogr_core.statistics import available_variables
        ws = Workspace()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            p = ws.get(pid).project
            mat, ext = p.materials[0], p.external_boundary()
            call(ws, "boundary_edit", project_id=pid, boundary=ext.id,
                 op="translate", dx=1.0, dy=0.0)
            call(ws, "boundary_edit", project_id=pid, boundary=ext.id,
                 op="set_vertices",
                 points=[[v.x, v.y] for v in ext.polyline.vertices])
            call(ws, "hydraulic_set", project_id=pid, material=mat.name,
                 properties={"ks": 1e-6})
            call(ws, "hydraulic_set", project_id=pid, material=mat.id,
                 properties={"ks": 2e-6})
            key = next(v.key for v in available_variables(p)
                       if v.param == "cohesion")
            call(ws, "random_variable_set", project_id=pid, key=key,
                 std_dev=1.0)
            call(ws, "random_variable_delete", project_id=pid, key=key)
            call(ws, "random_variable_set", project_id=pid, key=key,
                 std_dev=1.0)
            call(ws, "random_variable_delete", project_id=pid, key="all")
            hist = call(ws, "project_history", project_id=pid)
            stack = ws.get(pid).stack
            return hist, mat.id, key, stack.history()[0]
        finally:
            ws.shutdown()

    def test_the_history(self):
        hist, mid, key, names = self._agent_history()
        want = [s.replace("{ID}", mid).replace("{KEY}", key)
                for s in _STEPS_1433]
        assert hist["undo"][-8:] == want
        assert json.dumps(hist["undo"][-8:]) == json.dumps(want)
        # and the stack keeps the codes the window reads
        assert [getattr(n, "code", "") for n in names[-8:]] == [
            "step.edit_boundary", "step.edit_boundary", "step.hydraulic",
            "step.hydraulic", "step.random_variable",
            "step.delete_random_variable", "step.random_variable",
            "step.delete_all_random_variables"]

    def test_the_refusals(self):
        from ogr_api import InvalidArgument, Workspace, call
        old = {c: t for c, _a, t in _V1433}
        ws = Workspace()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            for op, kw, code in (
                    ("slope_angle_change", dict(toe=[25, 25], crest=[35, 15],
                                                target_deg=30.0),
                     "geometry.toe_not_lower"),
                    ("external_reshape", dict(points_xy=[[3, 3], [4, 40],
                                                         [7, 7]]),
                     "geometry.endpoints_off_external")):
                try:
                    call(ws, op, project_id=pid, **kw)
                except InvalidArgument as exc:
                    assert old[code] in str(exc), (op, str(exc))
                else:
                    raise AssertionError(op)
            try:
                call(ws, "seismic_record_set", project_id=pid, text="a b\n")
            except InvalidArgument as exc:
                assert "Nothing was read: no numeric data" in str(exc)
            else:
                raise AssertionError("seismic_record_set")
        finally:
            ws.shutdown()


# ======================================================================
class TestEveryCodeSaysItselfInSpanish:

    def test_the_three_catalogues(self):
        from ogr_core.geometry.messages import GEOMETRY_MESSAGES
        from ogr_core.loads.messages import SEISMIC_NOTES
        from ogr_core.project.step_names import STEP_NAMES
        from ogr_gui.core_messages import _catalogue
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        window = _catalogue()
        for spec in (*GEOMETRY_MESSAGES.values(), *SEISMIC_NOTES.values(),
                     *STEP_NAMES.values()):
            assert spec.code in window, spec.code
            said = es.get(spec.english)
            assert said and said != spec.english, spec.code
            assert _fields(said) == _fields(spec.english), spec.code

    def test_each_sample_in_spanish(self):
        from ogr_core.messages import coded
        from ogr_gui.core_messages import _catalogue, note_text
        cat = _catalogue()
        with _language("es"):
            for code, args, text in _V1433:
                said = note_text(coded(cat, code, **args))
                assert said != text and "{" not in said, (code, said)
            # the F1 samples are the args their templates take
            for code, args in _V1434_KINDS:
                said = note_text(coded(cat, code, **args))
                assert "{" not in said and "eurocode7" not in said, said

    def test_a_refusal_without_a_code(self):
        """``error_text``'s last rule: a sentence without a code is its
        translation, or itself. The transient stages' refusals («Stage times
        must be positive.») reach the window only by it (review of
        0.1.434)."""
        from ogr_gui.core_messages import error_text
        with _language("es"):
            known = error_text(ValueError("Stage times must be positive."))
            unknown = error_text(ValueError("no such sentence 4711"))
        assert known == "Los tiempos de las etapas deben ser positivos.", known
        assert unknown == "no such sentence 4711"

    def test_a_support_by_its_set_and_never_split(self):
        """The note of Change Slope Angle names each support as the rest of
        the window does: a default name by the class its set has NOW, and a
        name the user gave, commas and all, as it is (both found by the
        review of 0.1.434). The English is the joined text it was."""
        from ogr_core.geometry import Vertex
        from ogr_core.geometry.slope_angle import change_slope_angle
        from ogr_core.support import SupportInstance
        from ogr_core.support.support import support_registry
        from ogr_gui.core_messages import note_text
        p = _demo()
        moved = support_registry()["grouted_tieback"]()
        moved._display_name = "End Anchored (2)"     # born End Anchored
        p.support_types = [moved]
        p.supports = [
            SupportInstance(head=Vertex(30.0, 20.0), tail=Vertex(24.0, 14.0),
                            type_id="end_anchored",
                            name="End Anchored, top row"),
            SupportInstance(head=Vertex(32.0, 18.0), tail=Vertex(26.0, 12.0),
                            type_id="grouted_tieback", type_ref=moved.id,
                            name="End Anchored (2)")]
        note = change_slope_angle(p, (35, 15), (25, 25),
                                  target_deg=30.0)["notes"][0]
        assert str(note) == ("2 support(s) had their head on the old face and "
                             "were not moved: End Anchored, top row, End "
                             "Anchored (2).")
        with _language("es"):
            said = note_text(note, project=p)
            alone = note_text(note)
        assert said.endswith(": End Anchored, top row, Anclaje inyectado "
                             "(2)."), said
        # without the project, each by the class its name says, never split
        assert alone.endswith(": End Anchored, top row, Anclado en el "
                              "extremo (2)."), alone

    def test_the_kinds_with_and_without_a_project(self):
        from ogr_core.messages import Joined, coded
        from ogr_core.statistics import available_variables
        from ogr_gui.core_messages import _catalogue, note_text
        from ogr_gui.labels import random_variable_label
        cat = _catalogue()
        p = _demo()
        rv = next(v for v in available_variables(p) if v.param == "cohesion")
        p.random_variables = [rv]
        mat = p.materials[0]
        notes = {
            "edit": coded(cat, "step.edit_boundary", op="set_vertices"),
            "hydraulic": coded(cat, "step.hydraulic", material=mat.id),
            "variable": coded(cat, "step.random_variable", key=rv.key),
            "keys": coded(cat, "stat.vars_hydraulic", n=1, total=2,
                          keys=rv.key),
            "label": coded(cat, "stat.head_sens_mass", label=rv.label, n=3,
                           total=9, lo=1.0, hi=2.0),
            "standard": coded(cat, "design.summary",
                              standard="eurocode7_da1c2", materials=2,
                              loads=0),
            "names": coded(cat, "geometry.supports_not_moved", n=2,
                           names=Joined(["Anchor A", "End Anchored"])),
            # v0.1.434 (review) -- the kinds no test read
            "not_sampled": coded(cat, "stat.vars_not_sampled", n=1, total=2,
                                 keys=rv.key),
            "not_swept": coded(cat, "stat.vars_not_swept", n=1, total=2,
                               keys=rv.key),
            "case": coded(cat, "stat.head_sens_case", label=rv.label, n=3,
                          total=9, lo=1.0, hi=2.0),
        }
        with _language("es"):
            label = random_variable_label(rv)
            on = {k: note_text(n, project=p) for k, n in notes.items()}
            off = {k: note_text(n) for k, n in notes.items()}
        assert on["edit"] == "Editar contorno (fijar vértices)", on["edit"]
        assert on["hydraulic"] == "Propiedades hidráulicas de %s" % mat.name
        assert on["variable"] == "Variable aleatoria %s" % label, on
        assert label in on["keys"] and rv.key not in on["keys"], on["keys"]
        assert label in on["label"] and rv.label not in on["label"]
        for k in ("not_sampled", "not_swept"):
            assert label in on[k] and rv.key not in on[k], on[k]
        assert label in on["case"] and rv.label not in on["case"], on["case"]
        assert on["standard"].startswith("Eurocódigo 7 — DA1 Combinación 2: ")
        assert on["names"].endswith(": Anchor A, Anclado en el extremo."), \
            on["names"]
        # without the project, what only it knows reads as it is stored
        assert rv.key in off["variable"] and mat.id in off["hydraulic"]
        assert off["standard"] == on["standard"]
        # the agent's English is untouched by the kinds
        assert str(notes["variable"]) == "Random variable %s" % rv.key
        assert str(notes["standard"]).startswith("eurocode7_da1c2: ")


class TestTheTablesMatchWhatTheyName:

    def test_the_label_tables(self):
        from ogr_api.ops.model import _EDIT_OPS
        from ogr_core.project.commands import HEAVY_ATTRS, LIGHT_ATTRS
        from ogr_core.project.settings import DesignStandardSettings
        from ogr_gui import labels as L
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        assert set(L.BOUNDARY_EDIT_OP) == set(_EDIT_OPS)
        assert set(L.DESIGN_STANDARD) == (set(DesignStandardSettings.PRESETS)
                                          | {"custom"})
        assert set(L.PROJECT_PART) == set(LIGHT_ATTRS) | set(HEAVY_ATTRS)
        for table in (L.BOUNDARY_EDIT_OP, L.DESIGN_STANDARD, L.PROJECT_PART):
            for value in table.values():
                assert es.get(value), value

    @_requires_qt
    def test_the_combo_is_the_tables(self):
        from PySide6.QtWidgets import QComboBox
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        from ogr_gui.labels import DESIGN_STANDARD
        QApplication.instance() or QApplication([])
        p = _demo()
        with _language("es"):
            d = ProjectSettingsDialog(p.settings, None, project=p)
            _KEPT.append(d)
            boxes = [b for b in d.findChildren(QComboBox)
                     if b.findData("eurocode7_da1c2") >= 0]
            assert len(boxes) == 1
            items = {boxes[0].itemData(i): boxes[0].itemText(i)
                     for i in range(boxes[0].count())}
            from PySide6.QtWidgets import QLabel
            hints = [lb.text() for lb in d.findChildren(QLabel)
                     if "para introducir los tuyos" in lb.text()]
        # the page's hint names the entry as the combo does (review)
        assert len(hints) == 1 and "elige Norma personalizada para" in hints[0], \
            hints
        assert list(items) == list(DESIGN_STANDARD)      # in its order
        assert items["none"] == "Ninguna"                 # v0.1.325 (D318)
        assert items["custom"] == "Norma personalizada"   # the owner's

    def test_the_report_units_cover_the_enums(self):
        from ogr_core.project.units import PermeabilityUnit, TimeUnit
        from ogr_core.report import report_generator as RG
        from ogr_gui.i18n import _DICTS
        assert set(RG.TIME_UNIT_WORDS) == {u.value for u in TimeUnit}
        assert set(RG.PERMEABILITY_UNIT_WORDS) == {u.value
                                                   for u in PermeabilityUnit}
        for word in (*RG.TIME_UNIT_WORDS.values(),
                     *RG.PERMEABILITY_UNIT_WORDS.values()):
            assert _DICTS["es"].get(word), word
        # the defaults read as they did (_V1354 of test_report_spanish_v1355)
        assert RG.TIME_UNIT_WORDS["d"] == "days"
        assert RG.PERMEABILITY_UNIT_WORDS["m/s"] == "meters/second"

    def test_the_agents_pdf_names_every_unit(self):
        """The agent's PDF (``generate_report`` with no translator, as
        ``report_generate`` calls it) also names the units the tables did
        not have: 0.1.433 printed the member's name title-cased, «M Day»,
        «Mm Hour», «Minutes». The owner's decision in the review of
        0.1.434: the agent reads the new words too. One PDF by the agent's
        path, and every unit by the rule it prints."""
        import ogr_core.report.report_generator as RG
        from ogr_core.project.units import PermeabilityUnit, TimeUnit
        said = []

        class Par(RG.Paragraph):
            def __init__(self, text, *a, **k):
                said.append(re.sub(r"<[^>]+>", "", str(text)))
                super().__init__(text, *a, **k)

        class _Some(dict):               # a run, with no method to draw
            def __bool__(self):
                return True
        p = _demo()
        p.settings.units.time = TimeUnit("min")
        p.settings.units.permeability = PermeabilityUnit("m/day")
        with tempfile.TemporaryDirectory() as tmp, \
                _swapped(RG, "Paragraph", Par):
            RG.generate_report(p, _Some(), os.path.join(tmp, "r.pdf"))
        pairs = dict(zip(said, said[1:]))
        assert pairs.get("Time Units") == "minutes", said[:40]
        assert pairs.get("Permeability Units") == "meters/day", said[:40]
        assert [RG._unit_label(u, RG.TIME_UNIT_WORDS) for u in TimeUnit] == [
            "seconds", "minutes", "hours", "days", "months", "years"]
        assert [RG._unit_label(u, RG.PERMEABILITY_UNIT_WORDS)
                for u in PermeabilityUnit] == [
            "meters/second", "meters/day", "meters/year", "cm/second",
            "mm/hour"]


# ======================================================================
@_requires_qt
class TestTheWindowSaysItInSpanish:

    def test_change_slope_angle(self):
        import ogr_gui.main_window as MW
        from ogr_core.geometry import Vertex
        from ogr_core.loads import LineLoad
        from ogr_core.support import SupportInstance
        w = _window()
        ext = w.project.external_boundary()
        xy = [(v.x, v.y) for v in ext.polyline.vertices]
        toe, crest = xy.index((35.0, 15.0)), xy.index((25.0, 25.0))

        class _Dialog:
            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 1

            def parameters(self):
                return {"target_deg": 30.0}
        kept_sup, kept_loads = w.project.supports, w.project.line_loads
        w.project.supports = [SupportInstance(
            head=Vertex(30.0, 20.0), tail=Vertex(24.0, 14.0),
            type_id="end_anchored", name="End Anchored")]
        w.project.line_loads = [LineLoad(point=Vertex(30.0, 20.0),
                                         magnitude=10.0, name="Pile")]
        try:
            with _language("es"), _swapped(MW, "ChangeSlopeAngleDialog",
                                           _Dialog):
                w._on_slope_vertices_picked(crest, toe)
                refused = w.ogr_status.currentMessage()
                w._on_slope_vertices_picked(toe, crest)
                done = w.ogr_status.currentMessage()
                w.command_stack.undo(w.project)
        finally:
            w.project.supports, w.project.line_loads = kept_sup, kept_loads
            w.project.is_dirty = False
        assert refused == "El pie tiene que estar más bajo que la coronación.", \
            refused
        assert ("Soportes con la cabeza en la cara anterior que no se han "
                "movido (1): Anclado en el extremo.") in done, done
        assert ("Cargas sobre la cara anterior que no se han movido (1): "
                "Pile.") in done, done

    def test_simplify_and_expand_shrink(self):
        import ogr_gui.main_window as MW
        from ogr_core.geometry import Polyline, Vertex
        from PySide6.QtWidgets import QMessageBox
        w = _window()
        idx = next(i for i, b in enumerate(w.project.boundaries)
                   if b is w.project.external_boundary())

        class _Simplify:
            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 1

            def tolerance(self):
                return 1000.0
        said = []
        with _language("es"), \
                _swapped(MW, "SimplifyBoundaryDialog", _Simplify), \
                _swapped(w, "_ask_boundary_index", lambda *a, **k: idx):
            w.act_simplify_boundary()
            simplified = w.ogr_status.currentMessage()
        w._expand_shrink_target_idx = idx
        try:
            with _language("es"), _swapped(
                    MW, "QMessageBox", type("Q", (), {
                        "warning": staticmethod(
                            lambda _p, _t, text, *a, **k: said.append(text)),
                        "critical": QMessageBox.critical,
                        "question": QMessageBox.question,
                        "Yes": QMessageBox.Yes, "No": QMessageBox.No})):
                w._on_expand_shrink_polyline_drawn(Polyline(vertices=[
                    Vertex(3.0, 3.0), Vertex(4.0, 40.0), Vertex(7.0, 7.0)]))
        finally:
            w._expand_shrink_target_idx = None
        assert simplified == ("una tolerancia de 1000 deja 2 vértices; este "
                              "contorno necesita al menos 3"), simplified
        assert said == ["Los dos extremos de la polilínea tienen que estar "
                        "sobre el contorno exterior (usa el forzado: cruz "
                        "verde)."], said

    def test_the_edit_menu_and_its_status_line(self):
        import ogr_gui.main_window as MW
        from ogr_core.project.commands import PaintRegionCommand
        w = _window()
        idx = next(i for i, b in enumerate(w.project.boundaries)
                   if b is w.project.external_boundary())

        class _Offset:
            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 1

            def distance(self):
                return 1.0
        mid = w.project.materials[0].id
        with _language("es"):
            w.command_stack.do(w.project, PaintRegionCommand(
                x=10.0, y=5.0, material_id=mid))
            w._refresh_undo_actions()
            paint = w._actions["undo"].text()
            w.act_undo()
            undone = w.ogr_status.currentMessage()
            w._refresh_undo_actions()
            redo = w._actions["redo"].text()
            with _swapped(MW, "ExpandShrinkDialog", _Offset):
                w._expand_shrink_numeric(idx)
            w._refresh_undo_actions()
            offset = w._actions["undo"].text()
            name = w.command_stack.history()[0][-1]
            w.act_undo()
        w.project.is_dirty = False
        assert paint == "Deshacer «Pintar material en (10.00, 5.00)»", paint
        assert undone.startswith("Deshecho: Pintar material en (10.00, "
                                 "5.00)"), undone
        assert redo == "Rehacer «Pintar material en (10.00, 5.00)»", redo
        assert offset == "Deshacer «Desplazar contorno exterior (+1.00 m)»", \
            offset
        assert name == _WINDOW_STEPS_1433["offset"]          # the agent's

    def test_a_deleted_variable_is_named_by_its_label(self):
        from ogr_core.project.commands import SnapshotCommand
        from ogr_core.project.step_names import (
            RANDOM_VARIABLE, delete_random_variable_step_name, step_name)
        from ogr_core.statistics import available_variables
        from ogr_gui.labels import random_variable_label
        w = _window()
        rv = next(v for v in available_variables(w.project)
                  if v.param == "cohesion")
        kept = list(w.project.random_variables)

        def add(project, _rv=rv):
            project.random_variables = list(project.random_variables) + [_rv]

        def drop(project, _k=rv.key):
            project.random_variables = [v for v in project.random_variables
                                        if v.key != _k]
        try:
            with _language("es"):
                label = random_variable_label(rv)
                w.command_stack.do(w.project, SnapshotCommand(
                    step_name(RANDOM_VARIABLE, key=rv.key), add))
                w._refresh_undo_actions()
                added = w._actions["undo"].text()
                w.command_stack.do(w.project, SnapshotCommand(
                    delete_random_variable_step_name(rv.key), drop))
                w._refresh_undo_actions()
                deleted = w._actions["undo"].text()
                assert rv.key not in {v.key for v in
                                      w.project.random_variables}
                w.command_stack.undo(w.project)
                w.command_stack.undo(w.project)
        finally:
            w.project.random_variables = kept
            w.project.is_dirty = False
        assert added == "Deshacer «Variable aleatoria %s»" % label, added
        # the project no longer has it: the step's capture names it
        assert deleted == "Deshacer «Eliminar variable aleatoria %s»" % label, \
            deleted
        assert "material_strength:" not in added + deleted

    def test_kept_names_the_parts(self):
        from types import SimpleNamespace as NS
        w = _window()
        cmd = NS(description="Set material", kept=["materials", "settings"])
        with _language("es"):
            w._report_history_step(cmd, "Deshecho: {0}")
            said = w.ogr_status.currentMessage()
        assert said == ("Deshecho: Definir material  (se conserva lo "
                        "cambiado después: materiales, ajustes)"), said

    def test_the_notes_panel_names_a_variable(self):
        from ogr_core.messages import coded
        from ogr_core.statistics import available_variables
        from ogr_gui.core_messages import _catalogue
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        from ogr_gui.labels import random_variable_label
        w = _window()
        rv = next(v for v in available_variables(w.project)
                  if v.param == "cohesion")
        kept = list(w.project.random_variables)
        w.project.random_variables = [rv]
        try:
            note = coded(_catalogue(), "stat.vars_hydraulic", n=1, total=2,
                         keys=rv.key)
            with _language("es"):
                panel = AnalysisNotesPanel([note], w)
                _KEPT.append(panel)
                label = random_variable_label(rv)
                top = panel.tree.topLevelItem(0)
                shown = [top.child(i).text(0) for i in range(top.childCount())]
        finally:
            w.project.random_variables = kept
        assert any(t.endswith(": " + label) for t in shown), shown
        assert not any(rv.key in t for t in shown), shown

    def test_the_statistics_notes_after_the_variable_is_deleted(self):
        """The statistics notes name a variable by its label also after the
        user deleted it: the window keeps the run's variables
        (``notes_scope``), as an undo step keeps its capture (the owner's
        decision in the review of 0.1.434). The status bar, the notes panel
        and its Copy all, and the Statistics window, each by its real path
        (the run replaced by its outcome); and the design standard's notes
        in that window through their codes, which it showed in English."""
        import ogr_gui.background as BG
        from types import SimpleNamespace as NS
        from ogr_core.messages import coded
        from ogr_core.project.design_factors import apply_design_factors
        from ogr_core.statistics import available_variables
        from ogr_gui.core_messages import _catalogue
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel
        from ogr_gui.labels import random_variable_label
        from ogr_gui.statistics_window import StatisticsWindow
        w = _window()
        p = w.project
        rv = next(v for v in available_variables(p) if v.param == "cohesion")
        note = coded(_catalogue(), "stat.vars_not_sampled", n=1, total=2,
                     keys=rv.key)
        q = _demo()
        q.settings.design_standard.enabled = True
        q.settings.design_standard.apply_preset("eurocode7_da1c1")
        _copy, report = apply_design_factors(q)
        assert report.notes                       # the standard says some
        prob = NS(ok=False, notes={"error": note}, note_lines=[note],
                  switch_lines=[])
        out = NS(deterministic=True, factor_report=None, warnings=[],
                 probabilistic=prob, sensitivity=None)
        kept = {k: getattr(w, k, None) for k in (
            "last_statistics_notes", "last_statistics_variables",
            "last_statistics_factor_report", "_prob_result", "_sens_result")}
        kept_rv = list(p.random_variables)
        clip = QApplication.clipboard()
        kept_clip = clip.text()
        try:
            p.random_variables = [rv]
            with _language("es"), _swapped(BG, "run_task",
                                           lambda *a, **k: out):
                w._compute_statistics()
                bar = w.statusBar().currentMessage()
                p.random_variables = []               # the user deletes it
                label = random_variable_label(rv)
                panel = AnalysisNotesPanel([note], w)
                _KEPT.append(panel)
                top = panel.tree.topLevelItem(0)
                shown = [top.child(i).text(0) for i in range(top.childCount())]
                panel._copy_all()
                copied = clip.text()
                sw = StatisticsWindow(p, prob, None, w, factor_report=report)
                _KEPT.append(sw)
                run_notes = sw.lbl_run_notes.text()
                factor = sw.lbl_factor_report.text()
        finally:
            p.random_variables = kept_rv
            for k, v in kept.items():
                setattr(w, k, v)
            clip.setText(kept_clip)
            p.is_dirty = False
        for said in (bar, " | ".join(shown), copied, run_notes):
            assert label in said and rv.key not in said, said
        lines = factor.split("\n")
        assert lines[0].startswith("Norma de diseño aplicada a cada muestra: "
                                   "Eurocódigo 7 — DA1 Combinación 1"), lines
        assert len(lines) == 1 + len(report.notes), lines
        assert not {str(n) for n in report.notes} & set(lines), lines

    def test_the_windows_report(self):
        import reportlab.platypus as platypus
        import ogr_core.report.report_generator as RG
        import ogr_gui.dialogs.report_dialog as RD
        import ogr_gui.main_window as MW
        from ogr_core.project.design_factors import apply_design_factors
        from ogr_core.project.units import TimeUnit
        from PySide6.QtWidgets import QMessageBox
        w = _window()
        p = w.project
        ds = p.settings.design_standard
        kept_ds = (ds.enabled, ds.standard)
        kept_time = p.settings.units.time
        ds.enabled, ds.standard = True, "eurocode7_da1c2"
        p.settings.units.time = TimeUnit("min")
        _copy, report = apply_design_factors(p)

        class _Dialog:
            options = {"figures": False, "framing": "model",
                       "annotations": False}

            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 1

        class _Some(dict):               # a run, with no method to draw
            def __bool__(self):
                return True
        said, tables = [], []
        real_par, real_tab = platypus.Paragraph, platypus.Table

        class Par(real_par):
            def __init__(self, text, *a, **k):
                said.append(str(text))
                super().__init__(text, *a, **k)

        class Tab(real_tab):
            def __init__(self, data, *a, **k):
                tables.extend(tuple(str(c) for c in row) for row in data)
                super().__init__(data, *a, **k)
        kept = (getattr(w, "last_search_results", None),
                getattr(w, "last_factor_report", None))
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "r.pdf")
                w.last_search_results, w.last_factor_report = _Some(), report
                with _language("es"), \
                        _swapped(RD, "ReportDialog", _Dialog), \
                        _swapped(MW, "get_save_file_name",
                                 lambda *a, **k: (out, "")), \
                        _swapped(RG, "Paragraph", Par), \
                        _swapped(RG, "Table", Tab), \
                        _swapped(QMessageBox, "information", staticmethod(
                            lambda *a, **k: None)), \
                        _swapped(QMessageBox, "critical", staticmethod(
                            lambda *a, **k: said.append(a[2]))):
                    w.act_generate_report()
                assert os.path.exists(out), said
        finally:
            w.last_search_results, w.last_factor_report = kept
            ds.enabled, ds.standard = kept_ds
            p.settings.units.time = kept_time
            p.is_dirty = False
        # the cells are paragraphs: each row is two of them, label and value
        plain = [re.sub(r"<[^>]+>", "", t) for t in said]
        pairs = dict(zip(plain, plain[1:]))
        assert pairs.get("Norma") == "Eurocódigo 7 — DA1 Combinación 2", \
            plain[:60]
        assert pairs.get("Coeficientes aplicados", "").startswith(
            "Eurocódigo 7 — DA1 Combinación 2: "), plain[:60]
        assert pairs.get("Unidades de tiempo") == "minutos", plain[:60]
        assert not any("eurocode7" in t for t in plain)
        del tables

    def test_save_says_it_in_a_frame(self):
        import ogr_gui.main_window as MW
        w = _window()
        said = []
        kept = w.project.file_path
        with tempfile.TemporaryDirectory() as tmp:
            w.project.file_path = Path(tmp)            # a folder: it fails
            try:
                with _language("es"), _swapped(
                        MW, "QMessageBox", type("Q", (), {"critical": staticmethod(
                            lambda _p, _t, text, *a, **k: said.append(text))})):
                    w.act_save()
            finally:
                w.project.file_path = kept
                w.project.is_dirty = False
        assert said and said[0].startswith("No se pudo guardar el proyecto:\n"), \
            said

    def test_the_seismic_dialog(self):
        """Both ways out of Import: nothing read, and a record read with
        the reader's note (the review of 0.1.434 found only the first
        tested). The dialog edits a copy: the project is not touched."""
        import ogr_gui.dialogs.seismic_records_dialog as SD
        w = _window()
        said = []
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "record.txt")

            class _Files:
                @staticmethod
                def getOpenFileName(*a, **k):
                    return path, ""
            for text in ("a b\nc d\n", "0 1\n0.1 2\n0.3 3\n"):
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                with _language("es"), _swapped(SD, "QFileDialog", _Files):
                    d = SD.SeismicRecordsDialog(w.project, w)
                    _KEPT.append(d)
                    d._import()
                    said.append((d.lbl_note.text(), len(d.records)))
        before = len(getattr(w.project, "seismic_records", []))
        assert said[0][0] == "No se importó nada: no hay datos numéricos", said
        assert said[1] == ("el paso de tiempo no es constante", before + 1), \
            said


# ======================================================================
def _gui_sources():
    for p in sorted((_ROOT / "ogr_gui").rglob("*.py")):
        if "i18n" in p.parts:
            continue
        yield p, p.read_text(encoding="utf-8")


#: The handlers that catch only the core's own refusals: there the core's
#: sentence is shown alone, through ``error_text``.
_CORE_REFUSALS = {"ValueError", "ExpandShrinkError", "RuntimeError",
                  "NotASurface", "DxfReadError"}
_VISIBLE = {"critical", "warning", "information", "_info", "showMessage",
            "setText", "emit"}
#: Readers of an exception that say it in the reader's language.
_READERS = {"error_text", "user_surface_refusal_text", "error_to_dict"}
#: An exception's attributes that ARE its text: read as the exception
#: itself (``exc.args[0]`` is the core's ``Coded``; review of 0.1.434).
_TEXT_ATTRS = {"args", "message", "strerror", "msg"}


def _exception_text_census(src, rel=""):
    """``[(rel, line, why)]``: an exception's text shown as it is, or alone
    when the handler catches more than the core's refusals."""
    tree = ast.parse(src)
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    found = []
    for h in ast.walk(tree):
        if not (isinstance(h, ast.ExceptHandler) and h.name):
            continue
        caught = h.type
        names = ({e.id if isinstance(e, ast.Name) else getattr(e, "attr", "")
                  for e in (caught.elts if isinstance(caught, ast.Tuple)
                            else [caught])} if caught is not None else set())
        narrow = bool(names) and names <= _CORE_REFUSALS
        for node in (n for stmt in h.body for n in ast.walk(stmt)):
            if not (isinstance(node, ast.Name) and node.id == h.name
                    and isinstance(node.ctx, ast.Load)):
                continue
            up = parent.get(node)
            if isinstance(up, ast.Attribute):
                if up.attr not in _TEXT_ATTRS:
                    continue                    # exc.code, exc.problems...
                # exc.args[0], exc.strerror: the text, read as it is
                node = up
                if isinstance(parent.get(up), ast.Subscript):
                    node = parent[up]
                up = parent.get(node)
                if isinstance(up, (ast.Raise, ast.Assign, ast.Return)):
                    continue
                found.append((rel, node.lineno, "its text as it is"))
                continue
            if (isinstance(up, ast.Call) and node in up.args
                    and getattr(up.func, "id", getattr(up.func, "attr", ""))
                    in _READERS | {"type", "isinstance", "getattr", "hasattr"}):
                fn = getattr(up.func, "id", getattr(up.func, "attr", ""))
                if fn in _READERS and not narrow:
                    # alone in a visible call: it needs a translated frame
                    outer = parent.get(up)
                    if (isinstance(outer, ast.Call) and up in outer.args
                            and getattr(outer.func, "attr",
                                        getattr(outer.func, "id", ""))
                            in _VISIBLE):
                        found.append((rel, node.lineno, "alone"))
                continue
            if isinstance(up, (ast.Raise, ast.Assign, ast.Return)):
                continue                        # kept, raised again
            found.append((rel, node.lineno, "as it is"))
    return found


#: Step names given in a variable, each with every value it can hold: the
#: census reads them where they are set.
_STEP_NAME_FUNCS = {"step_name", "expand_shrink_step_name",
                    "delete_random_variable_step_name",
                    "add_boundary_step_name"}


def _step_name_census(src, rel=""):
    """``[(rel, line, what)]``: an undo step named by something else than a
    literal, a choice of literals, or a step-name function. Its literals are
    returned too, as ``(rel, line, "literal:<text>")``."""
    tree = ast.parse(src)
    found = []
    # a name is read where it is set: in the function of the call
    scope = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(fn):
                scope.setdefault(node, fn)

    def assigns_in(fn):
        out = {}
        for node in (ast.walk(fn) if fn is not None else ()):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        out.setdefault(t.id, []).append(node.value)
        return out
    assigns = {}
    # a name passed on by a step wrapper is checked where the wrapper is
    # called: a parameter of the wrapper that holds the call, never of
    # another function of the file (review of 0.1.434)
    wrappers = ("_model_step", "undo_step", "mutate", "__init__", "_locked")
    params = set()

    def ok(value, depth=0):
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            found.append((rel, value.lineno, "literal:" + value.value))
            return True
        if isinstance(value, ast.IfExp):
            return ok(value.body, depth) and ok(value.orelse, depth)
        if isinstance(value, ast.Call):
            fn = getattr(value.func, "id", getattr(value.func, "attr", ""))
            if fn in _STEP_NAME_FUNCS:
                return True
            if fn == "get" and isinstance(value.func.value, ast.Dict):
                return all(ok(v, depth) for v in value.func.value.values)
            return False
        if isinstance(value, ast.Subscript) and isinstance(value.value,
                                                           ast.Dict):
            return all(ok(v, depth) for v in value.value.values)
        if isinstance(value, ast.Name) and depth < 3:
            if value.id in params:
                return True
            vals = assigns.get(value.id)
            return bool(vals) and all(ok(v, depth + 1) for v in vals)
        return False
    holders = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(fn):
                holders.setdefault(node, []).append(fn)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = getattr(node.func, "id", getattr(node.func, "attr", ""))
        arg = None
        # by position or by keyword: ``mutate(pid, description=…, fn=…)``
        # is the form the census did not read (review of 0.1.434)
        named = next((k.value for k in node.keywords
                      if k.arg == "description"), None)
        if fn in ("_model_step", "undo_step", "SnapshotCommand"):
            arg = node.args[0] if node.args else named
        elif fn == "mutate":
            arg = node.args[1] if len(node.args) > 1 else named
        elif fn.endswith("Command"):
            arg = named
        if arg is None:
            continue
        assigns.clear()
        assigns.update(assigns_in(scope.get(node, tree)))
        params.clear()
        for f in holders.get(node, ()):
            if f.name in wrappers:
                params.update(a.arg for a in f.args.args + f.args.kwonlyargs)
        if not ok(arg):
            found.append((rel, node.lineno, ast.dump(arg)[:60]))
    return found


class TestTheCensuses:

    def test_an_exceptions_text_goes_through_its_reader(self):
        found = []
        for p, src in _gui_sources():
            found += _exception_text_census(src, p.relative_to(_ROOT).as_posix())
        assert not found, found

    def test_the_exception_census_checks_itself(self):
        census = _exception_text_census
        for src in ('try:\n    f()\nexcept ValueError as exc:\n'
                    '    w.showMessage(str(exc))\n',
                    'try:\n    f()\nexcept OSError as e:\n'
                    '    box.critical(p, t, f"{e}")\n',
                    'try:\n    f()\nexcept Exception as e:\n'
                    '    box.critical(p, t, tr("A: {0}").format(e))\n',
                    'try:\n    f()\nexcept OSError as e:\n'
                    '    box.critical(p, t, error_text(e))\n',
                    # review of 0.1.434: the text by its attribute
                    'try:\n    f()\nexcept ValueError as exc:\n'
                    '    box.critical(p, t, exc.args[0])\n',
                    'try:\n    f()\nexcept OSError as e:\n'
                    '    w.showMessage(e.strerror)\n'):
            assert census(src), src
        # each visible call needs the frame after a broad handler, and no
        # broad handler counts as the core's refusals (review of 0.1.434:
        # either rule could go without a check failing). Written out here,
        # not read from the sets the census uses
        for visible in ("critical", "warning", "information", "_info",
                        "showMessage", "setText", "emit"):
            for caught in ("Exception", "OSError", "KeyError"):
                src = ('try:\n    f()\nexcept %s as e:\n    w.%s(error_text(e))\n'
                       % (caught, visible))
                assert census(src), src
        for caught in ("ValueError", "ExpandShrinkError", "RuntimeError",
                       "NotASurface", "DxfReadError"):
            src = ('try:\n    f()\nexcept %s as e:\n    w.showMessage(error_text(e))\n'
                   % caught)
            assert not census(src), src
        for src in ('try:\n    f()\nexcept ValueError as exc:\n'
                    '    w.showMessage(error_text(exc))\n',
                    'try:\n    f()\nexcept ValueError as exc:\n'
                    '    self.error = exc.args[0]\n',
                    'try:\n    f()\nexcept OSError as e:\n'
                    '    box.critical(p, t, tr("A: {0}").format(error_text(e)))\n',
                    'try:\n    f()\nexcept Exception as e:\n'
                    '    self.error = e\n',
                    'try:\n    f()\nexcept Exception as e:\n'
                    '    w.say(note_text(p) for p in e.problems)\n'):
            assert not census(src), src

    def test_an_undo_steps_name_is_a_literal_or_a_function(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        loose, missing = [], []
        files = [_ROOT / "ogr_gui" / "main_window.py",
                 S.source("ogr_core/project/commands.py"),
                 *sorted((_ROOT / "ogr_api" / "ops").glob("*.py"))]
        for p in files:
            rel = S.relative(p)
            for row in _step_name_census(p.read_text(encoding="utf-8"), rel):
                if row[2].startswith("literal:"):
                    if row[2][8:] not in es:
                        missing.append(row)
                else:
                    loose.append(row)
        assert not loose, loose
        assert not missing, missing

    def test_the_step_census_checks_itself(self):
        census = _step_name_census
        bad = ['s.do(p, SnapshotCommand(f"Offset ({d:+.2f} m)", fn))\n',
               'ws.mutate(pid, f"Edit boundary ({op})", edit)\n',
               'ws.mutate(pid, "Edit " + op, edit)\n',
               'x = f"Paint {a}"\ns.do(p, SnapshotCommand(x, fn))\n',
               # review of 0.1.434: each form the census reads, each a rule
               '@undo_step(f"Paint {a}")\ndef act(self):\n    pass\n',
               'self._model_step(f"Offset ({d})", fn)\n',
               'c = MoveCommand(description=f"Move {n}")\n',
               's.do(p, SnapshotCommand({"a": f"A {x}"}[k], f))\n',
               'ws.mutate(pid, description=f"Random variable {key}", fn=e)\n',
               'self._model_step(description=f"Offset ({d})", fn=f)\n',
               '@undo_step(description=f"Paint {a}")\ndef act(self):\n'
               '    pass\n',
               # a wrapper's parameter is one only inside that wrapper, and
               # another function's parameter is never one
               'def undo_step(description):\n    pass\n'
               'def act(self, d):\n    description = f"Offset ({d})"\n'
               '    s.do(p, SnapshotCommand(description, fn))\n',
               'def act(self, description):\n'
               '    s.do(p, SnapshotCommand(description, fn))\n']
        for src in bad:
            assert [r for r in census(src) if not r[2].startswith("literal:")
                    ], src
        good = ['ws.mutate(pid, step_name(EDIT_BOUNDARY, op=op), edit)\n',
                's.do(p, SnapshotCommand("Change slope angle", fn))\n',
                'name = "A" if x else "B"\ns.do(p, SnapshotCommand(name, f))\n',
                's.do(p, SnapshotCommand({"a": "A"}.get(k), f))\n',
                's.do(p, SnapshotCommand({"a": "A", "b": "B"}[k], f))\n',
                'def undo_step(description):\n    def deco(fn):\n'
                '        s.do(p, SnapshotCommand(description, fn))\n']
        for src in good:
            assert not [r for r in census(src)
                        if not r[2].startswith("literal:")], src
        # the literals come back, to be checked against the Spanish
        for src in ('@undo_step("Zzz never said")\ndef act(self):\n    pass\n',
                    'self._model_step("Zzz never said", fn)\n',
                    'c = MoveCommand(description="Zzz never said")\n'):
            assert ("", 1, "literal:Zzz never said") in census(src), src

    def test_no_sentence_without_its_code(self):
        coded = {
            "ogr_core/geometry/slope_angle.py": (
                "vertex_index", "slope_face", "new_face",
                "change_slope_angle"),
            "ogr_core/geometry/cleanup.py": ("simplify_boundary",),
            "ogr_core/geometry/expand_shrink.py": (
                "expand_shrink_external", "apply_expand_shrink",
                "apply_external_offset"),
            "ogr_core/geometry/transforms.py": ("offset_polygon",),
            "ogr_core/loads/seismic_record.py": ("parse_record_text",),
            # the paint step's name, a method with an f-string until 0.1.434:
            # no call site names it, so the step census cannot see it
            "ogr_core/project/commands.py": ("description",),
        }
        found = []
        for rel, names in coded.items():
            src = S.source(rel).read_text(encoding="utf-8")
            found += _uncoded(src, names, rel)
        assert not found, found

    def test_the_code_census_checks_itself(self):
        for src in ('def f(x):\n    raise ValueError("No external.")\n',
                    'def f(x):\n    raise ValueError(f"Vertex {x}.")\n',
                    'def f(x):\n    return [], 0.0, "no numeric data"\n',
                    'def f(x):\n    notes.append(f"{x} support(s) ...")\n',
                    # review of 0.1.434: each rule with a case of its own
                    'def f(x):\n    notes.append("on %s" % x)\n',
                    'def f(x):\n    notes.append("A sentence of more than '
                    'forty characters, alone.")\n',
                    'def f(x):\n    note = "time step is not constant"\n',
                    'def f(x):\n    raise ValueError("Toe: " + str(x))\n'):
            assert _uncoded(src, ("f",)), src
        for src in ('def f(x):\n    raise ValueError(M.geometry_message(C))\n',
                    'def f(x):\n    return [], 0.0, ""\n',
                    'def f(x):\n    note = ""\n    return x, note\n',
                    'def f(x):\n    mode = "horizontal"\n'):
            assert not _uncoded(src, ("f",)), src


def _uncoded(src, names, rel=""):
    """The rules of ``test_model_notes_v1347`` (no f-string, no ``%``
    formatting, no long literal) plus three: no ``raise X("…")`` (nor
    ``X("…" + x)``), no non-empty string in a ``return``, and no sentence
    (a literal with a space) assigned to a name."""
    tree = ast.parse(src)
    funcs = {n.name: n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef)}
    found = []
    for name in names:
        fn = funcs[name]
        doc = (fn.body[0].value if fn.body and isinstance(fn.body[0], ast.Expr)
               else None)
        for n in ast.walk(fn):
            if n is doc:
                continue
            if isinstance(n, ast.JoinedStr) and any(
                    isinstance(v, ast.Constant) and re.search(r"[A-Za-z]{3}",
                                                              v.value)
                    for v in n.values):
                found.append((rel, name, n.lineno, "f-string"))
            elif (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod)
                  and isinstance(n.left, ast.Constant)
                  and isinstance(n.left.value, str)):
                found.append((rel, name, n.lineno, "% format"))
            elif isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) \
                    and any(isinstance(a, (ast.Constant, ast.JoinedStr))
                            or (isinstance(a, ast.BinOp) and any(
                                isinstance(c, ast.Constant)
                                and isinstance(c.value, str)
                                for c in ast.walk(a)))
                            for a in n.exc.args):
                found.append((rel, name, n.lineno, "raise with a sentence"))
            elif (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                  and isinstance(n.value.value, str) and " " in n.value.value
                  and re.search(r"[A-Za-z]{3}", n.value.value)):
                # «note = "time step is not constant"», 0.1.433's form of
                # one of these notes (review of 0.1.434)
                found.append((rel, name, n.lineno, "a sentence assigned"))
            elif isinstance(n, ast.Return) and n.value is not None:
                values = (n.value.elts if isinstance(n.value, ast.Tuple)
                          else [n.value])
                if any(isinstance(v, ast.Constant) and isinstance(v.value, str)
                       and v.value for v in values):
                    found.append((rel, name, n.lineno, "returns a sentence"))
            elif (isinstance(n, ast.Constant) and isinstance(n.value, str)
                  and len(n.value) > 40):
                found.append((rel, name, n.lineno, "sentence"))
    return found
