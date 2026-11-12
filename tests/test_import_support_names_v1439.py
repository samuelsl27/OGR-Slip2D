# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.439 (D421) -- Import Properties numbers a support type whose name the
model already has, as it always numbered a material, and the agent finds
every set by its name again.

Invariants protected here:

* **Finding by the name undoes naming.** After an import, for each support
  set, ``find_type(project, its name)`` is that same set, and the names are
  distinct under the comparison ``find_type`` uses (``name_key``). That is
  the reference: an identity, not a captured text. Until this version the
  imported «Type 1» kept its name beside the model's «type 1 », and the agent
  found neither (``medir_d421.py`` of the bank, with 0.1.435 and 0.1.438).
* **One rule for both:** a material and a support type of one name are
  numbered by the same function (``ogr_core.naming.numbered_name``) to the
  same name, «Type 1 (2)»; a set with no clash keeps what it had, its
  class's name included (no ``_display_name`` added); each set gets a new
  id and keeps its parameters, and a support hooked to it by id resolves to
  it (the engine resolves by ``type_ref``, never by the name: no number
  moves).
* **What the agent reads outside the decided changes is 0.1.438's.**
  ``_V1438`` was written by 0.1.438 (773b246), measured by running
  :func:`_capture` on a ``git archive`` of that tree
  (``_auditoria/P10_herramientas/capture_d421.py``). What moves, by the
  owner's decisions of 2026-11-11, is written here: the imported names, a
  name two sets share said as ambiguous (``E_CONFLICT`` with their ids) and
  not as unknown, and a rename to a name another set has refused as creating
  one is.
* **The window says what happened:** the status bar counts the names
  numbered, only when there were, and the set reads «Tipo 1 (2)» in Spanish
  (the label of D415).

One main window for the file, with the file dialog and the item dialog
replaced and put back; the language restored (rule 5).
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

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
# 0.1.438's answers, measured on its tree (see the module docstring)
# ======================================================================
_V1438 = {'agent an unknown name': ['NotFound',
                           "[E_NOT_FOUND] Unknown support type 'Nope'. Hint: "
                           'Known: .'],
 'agent create Malla': ['OK',
                        '{"created": true, "support_type": {"allows_pattern": '
                        'true, "class": "soil_nail", "color": "#4b0082", '
                        '"force_application": "passive", "id": "<id>", '
                        '"name": "Malla", "orientation": '
                        '"parallel_to_support", "params": {"bond_strength": '
                        '30.0, "out_of_plane_spacing": 1.5, "plate_capacity": '
                        '50.0, "shear_capacity": 0.0, "tensile_capacity": '
                        '100.0}, "user_angle_deg": 0.0}, "supports_retyped": '
                        '0}'],
 'agent create Type 1': ['OK',
                         '{"created": true, "support_type": '
                         '{"allows_pattern": true, "class": "end_anchored", '
                         '"color": "#4b0082", "force_application": "active", '
                         '"id": "<id>", "name": "Type 1", "orientation": '
                         '"parallel_to_support", "params": '
                         '{"anchor_capacity": 200.0, "out_of_plane_spacing": '
                         '1.5}, "user_angle_deg": 0.0}, "supports_retyped": '
                         '0}'],
 'agent create another Type 1': ['Conflict',
                                 "[E_CONFLICT] A support type named 'Type 1' "
                                 "exists. Hint: Pass support_type='Type 1' to "
                                 'change it.'],
 'agent create unnamed': ['OK',
                          '{"created": true, "support_type": '
                          '{"allows_pattern": true, "class": "soil_nail", '
                          '"color": "#4b0082", "force_application": '
                          '"passive", "id": "<id>", "name": "Soil Nail", '
                          '"orientation": "parallel_to_support", "params": '
                          '{"bond_strength": 30.0, "out_of_plane_spacing": '
                          '1.5, "plate_capacity": 50.0, "shear_capacity": '
                          '0.0, "tensile_capacity": 100.0}, "user_angle_deg": '
                          '0.0}, "supports_retyped": 0}'],
 'agent import': ['OK',
                  '{"materials": ["Silty clay (2)"], "notes": ["\'Silty clay '
                  "(2)' used a water surface of the other project; assign one "
                  'of this model to it."], "skipped": [], "support_types": '
                  '["Type 1"]}'],
 'agent import without a clash': ['OK',
                                  '{"materials": ["Silty clay (2)"], "notes": '
                                  '["\'Silty clay (2)\' used a water surface '
                                  'of the other project; assign one of this '
                                  'model to it."], "skipped": [], '
                                  '"support_types": ["Type 1"]}'],
 'agent rename Malla to Type 1': ['NotFound',
                                  '[E_NOT_FOUND] Unknown support type '
                                  "'MALLA'. Hint: Known: '<id> (Type 1)', "
                                  "'<id> (Type 1)', '<id> (MALLA)', '<id> "
                                  "(Malla)'."],
 'agent rename Malla to its own name': ['OK',
                                        '{"created": false, "support_type": '
                                        '{"allows_pattern": true, "class": '
                                        '"soil_nail", "color": "#4b0082", '
                                        '"force_application": "passive", '
                                        '"id": "<id>", "name": "MALLA", '
                                        '"orientation": '
                                        '"parallel_to_support", "params": '
                                        '{"bond_strength": 30.0, '
                                        '"out_of_plane_spacing": 1.5, '
                                        '"plate_capacity": 50.0, '
                                        '"shear_capacity": 0.0, '
                                        '"tensile_capacity": 100.0}, '
                                        '"user_angle_deg": 0.0}, '
                                        '"supports_retyped": 0}'],
 'agent rename Soil Nail to Type 1': ['OK',
                                      '{"created": false, "support_type": '
                                      '{"allows_pattern": true, "class": '
                                      '"soil_nail", "color": "#4b0082", '
                                      '"force_application": "passive", "id": '
                                      '"<id>", "name": "Type 1", '
                                      '"orientation": "parallel_to_support", '
                                      '"params": {"bond_strength": 30.0, '
                                      '"out_of_plane_spacing": 1.5, '
                                      '"plate_capacity": 50.0, '
                                      '"shear_capacity": 0.0, '
                                      '"tensile_capacity": 100.0}, '
                                      '"user_angle_deg": 0.0}, '
                                      '"supports_retyped": 0}'],
 'agent support_set by the name': ['NotFound',
                                   "[E_NOT_FOUND] Unknown support type 'Type "
                                   "1'. Hint: Known: '<id> (Type 1)', '<id> "
                                   "(Type 1)'."],
 'agent two of one name': ['NotFound',
                           "[E_NOT_FOUND] Unknown support type 'Grouted "
                           "Tieback'. Hint: Known: '<id> (Grouted Tieback)', "
                           "'<id> (Grouted Tieback)'."],
 'core import': ['OK',
                 '{"materials": ["Silty clay (2)"], "notes": ["\'Silty clay '
                 "(2)' used a water surface of the other project; assign one "
                 'of this model to it."], "skipped": [], "support_types": '
                 '["Type 1"]}'],
 'core import again': ['OK',
                       '{"materials": ["Silty clay (3)"], "notes": ["\'Silty '
                       "clay (3)' used a water surface of the other project; "
                       'assign one of this model to it."], "skipped": [], '
                       '"support_types": ["Type 1"]}'],
 'core import without a clash': ['OK',
                                 '{"materials": ["Silty clay (2)"], "notes": '
                                 '["\'Silty clay (2)\' used a water surface '
                                 'of the other project; assign one of this '
                                 'model to it."], "skipped": [], '
                                 '"support_types": ["Type 1"]}'],
 'core names': ['names',
                '[" SILTY CLAY ", "Silty clay (2)", "Silty clay (3)", "type 1 '
                '", "Type 1", "Type 1"]']}

_TMP = tempfile.mkdtemp(prefix="ogr_d421_")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                   r"[0-9a-f]{12}")
_HANDLE = re.compile(r"\b([pr])_[0-9a-f]{10}\b")


def _scrub(text):
    """Ids, handles and the temporary folder masked."""
    text = str(text).replace(_TMP + os.sep, "<tmp>/").replace(_TMP, "<tmp>")
    return _HANDLE.sub(r"\1_<h>", _UUID.sub("<id>", text))


def _label(st):
    return getattr(st, "_display_name", None) or st.DISPLAY_NAME


def _set(cls, name=None, **params):
    st = cls(**params)
    if name is not None:
        st._display_name = name
    return st


def _source():
    """The project imported from: the demo («Silty clay») and a soil nail
    set «Type 1» of 99 kN."""
    from ogr_core.project.demo import build_demo_project
    from ogr_core.support import SoilNail
    q = build_demo_project()
    q.support_types = [_set(SoilNail, "Type 1", tensile_capacity=99.0)]
    return q


def _destination():
    """A model that already has both names, as another writes them: the
    material « SILTY CLAY » and an end anchored set «type 1 »."""
    from ogr_core.project.demo import build_demo_project
    from ogr_core.support import EndAnchored
    p = build_demo_project()
    p.materials[0].name = " SILTY CLAY "
    p.support_types = [_set(EndAnchored, "type 1 ")]
    return p


def _source_file():
    f = os.path.join(_TMP, "source.ogr")
    if not os.path.exists(f):
        _source().save(f)
    return f


def _twice_named():
    """A model with two sets of one name, as the bank's 049 holds them: two
    grouted tiebacks named by their class."""
    from ogr_core.project.demo import build_demo_project
    from ogr_core.support import GroutedTieback
    p = build_demo_project()
    p.support_types = [GroutedTieback(), GroutedTieback()]
    f = os.path.join(_TMP, "twice.ogr")
    p.save(f)
    return f, [st.id for st in p.support_types]


_CAPTURED: dict = {}


def _capture() -> dict:
    """What :data:`_V1438` recorded, measured on this tree."""
    if _CAPTURED:
        return _CAPTURED
    from ogr_api import Workspace, call
    from ogr_core.project.properties_import import import_properties
    out = {}

    def said(name, fn):
        try:
            got = fn()
        except Exception as exc:  # noqa: BLE001
            out[name] = [type(exc).__name__, _scrub(exc)]
            return None
        out[name] = ["OK", _scrub(json.dumps(got, sort_keys=True,
                                             default=str))]
        return got

    # the core
    dst = _destination()
    said("core import", lambda: import_properties(dst, _source()))
    said("core import again", lambda: import_properties(dst, _source()))
    out["core names"] = ["names", json.dumps(
        [m.name for m in dst.materials] + [_label(t)
                                           for t in dst.support_types])]
    from ogr_core.project.demo import build_demo_project
    clear = build_demo_project()
    said("core import without a clash", lambda: import_properties(
        clear, _source()))
    # the agent
    ws = Workspace()
    try:
        pid = call(ws, "project_new", template="demo")["project_id"]
        said("agent create Type 1", lambda: call(
            ws, "support_type_set", project_id=pid, type_class="end_anchored",
            name="Type 1"))
        said("agent import", lambda: call(
            ws, "properties_import", project_id=pid, path=_source_file()))
        said("agent support_set by the name", lambda: call(
            ws, "support_set", project_id=pid, support_type="Type 1",
            head=[30.0, 20.0], tail=[20.0, 15.0]))
        said("agent create another Type 1", lambda: call(
            ws, "support_type_set", project_id=pid, type_class="soil_nail",
            name="Type 1"))
        said("agent create unnamed", lambda: call(
            ws, "support_type_set", project_id=pid, type_class="soil_nail"))
        said("agent rename Soil Nail to Type 1", lambda: call(
            ws, "support_type_set", project_id=pid, support_type="Soil Nail",
            name="Type 1"))
        said("agent create Malla", lambda: call(
            ws, "support_type_set", project_id=pid, type_class="soil_nail",
            name="Malla"))
        # its own name first: 0.1.438 accepts the next one, which renames it
        said("agent rename Malla to its own name", lambda: call(
            ws, "support_type_set", project_id=pid, support_type="Malla",
            name="MALLA"))
        said("agent rename Malla to Type 1", lambda: call(
            ws, "support_type_set", project_id=pid, support_type="MALLA",
            name="Type 1"))
        # on a model with no sets: the known ones would be the imported names
        pid2 = call(ws, "project_new", template="demo")["project_id"]
        said("agent an unknown name", lambda: call(
            ws, "support_type_set", project_id=pid2, support_type="Nope",
            params={}))
        said("agent import without a clash", lambda: call(
            ws, "properties_import", project_id=pid2, path=_source_file()))
        f, _ids = _twice_named()
        twice = call(ws, "project_open", path=f)["project_id"]
        said("agent two of one name", lambda: call(
            ws, "support_type_set", project_id=twice,
            support_type="Grouted Tieback", params={}))
    finally:
        ws.shutdown()
    _CAPTURED.update(out)
    return _CAPTURED


# ======================================================================
class TestFindingByTheNameUndoesNaming:

    def test_every_set_is_found_by_its_name(self):
        from ogr_api.ops.supports import find_type
        from ogr_core.naming import name_key
        from ogr_core.project.properties_import import import_properties
        dst = _destination()
        for _ in range(3):
            import_properties(dst, _source())
        names = [_label(st) for st in dst.support_types]
        assert len({name_key(n) for n in names}) == len(names) == 4, names
        for st in dst.support_types:
            assert find_type(dst, _label(st)) is st, _label(st)

    def test_one_rule_for_a_material_and_a_set(self):
        from ogr_core.naming import numbered_name
        from ogr_core.project.properties_import import import_properties
        dst = _destination()
        renamed = []
        rep = import_properties(dst, _source(), renamed=renamed)
        assert rep["support_types"] == ["Type 1 (2)"], rep
        assert rep["materials"] == ["Silty clay (2)"], rep
        assert rep["support_types"][0] == numbered_name(
            "Type 1", ["type 1 "])
        assert rep["materials"][0] == numbered_name(
            "Silty clay", [" SILTY CLAY "])
        assert renamed == [("Silty clay", "Silty clay (2)"),
                           ("Type 1", "Type 1 (2)")], renamed
        assert _label(dst.support_types[-1]) == "Type 1 (2)"

    def test_two_of_one_name_in_the_same_file(self):
        """A file that brings two sets of one name (the bank's 049 shape) and
        two materials of one name, into a model with none of them: the
        second of each is numbered, and each set is found by its name (the
        review of 0.1.439; the owner's decision: no two sets of one name)."""
        from ogr_api.ops.supports import find_type
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_core.project.demo import build_demo_project
        from ogr_core.project.properties_import import import_properties
        from ogr_core.support import GroutedTieback
        src = build_demo_project()
        src.support_types = [GroutedTieback(), GroutedTieback()]
        src.materials = [Material(name="Sand", strength=MohrCoulomb(
            cohesion=0.0, friction_angle=35.0)) for _ in range(2)]
        dst = Project("empty")
        renamed = []
        rep = import_properties(dst, src, renamed=renamed)
        assert rep["support_types"] == ["Grouted Tieback",
                                        "Grouted Tieback (2)"], rep
        assert rep["materials"] == ["Sand", "Sand (2)"], rep
        assert renamed == [("Sand", "Sand (2)"),
                           ("Grouted Tieback", "Grouted Tieback (2)")]
        for st in dst.support_types:
            assert find_type(dst, _label(st)) is st, _label(st)

    def test_a_set_without_a_clash_keeps_what_it_had(self):
        """Its file is the source's but for the id, and a set named by its
        class gets no name of its own."""
        from ogr_core.project.demo import build_demo_project
        from ogr_core.project.properties_import import import_properties
        from ogr_core.support import GroutedTieback, SoilNail
        src = build_demo_project()
        src.support_types = [_set(SoilNail, "Malla", tensile_capacity=99.0),
                             GroutedTieback()]
        dst = build_demo_project()
        renamed = []
        rep = import_properties(dst, src, materials=False, renamed=renamed)
        assert rep["support_types"] == ["Malla", "Grouted Tieback"], rep
        assert renamed == []
        for a, b in zip(src.support_types, dst.support_types):
            da, db = a.to_dict(), b.to_dict()
            assert da.pop("id") != db.pop("id")
            assert da == db
            assert (hasattr(a, "_display_name")
                    == hasattr(b, "_display_name"))

    def test_new_ids_same_parameters_and_the_support_resolves(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project.properties_import import import_properties
        from ogr_core.support import SupportInstance, resolve_support_type
        src, dst = _source(), _destination()
        import_properties(dst, src)
        clone = dst.support_types[-1]
        assert clone.id != src.support_types[0].id
        assert clone.tensile_capacity == 99.0
        s = SupportInstance(type_id=clone.TYPE_ID, type_ref=clone.id,
                            head=Vertex(30, 20), tail=Vertex(20, 15))
        dst.supports.append(s)
        assert resolve_support_type(dst, s) is clone
        assert resolve_support_type(dst, s) is not dst.support_types[0]


# ======================================================================
#: what the agent reads and does not move, and what moves (the decisions)
_UNCHANGED = ("agent create Type 1", "agent create another Type 1",
              "agent create unnamed", "agent create Malla",
              "agent rename Malla to its own name", "agent an unknown name",
              "agent import without a clash", "core import without a clash")


class TestTheAgent:

    def test_what_does_not_move_is_0438(self):
        now = _capture()
        assert sorted(now) == sorted(_V1438), sorted(set(now) ^ set(_V1438))
        assert len(_V1438) == 16
        for key in _UNCHANGED:
            assert now[key] == _V1438[key], (key, now[key], _V1438[key])

    def test_what_moves(self):
        """The imported name, the set found by it, the rename refused and the
        name two sets share said as ambiguous; 0.1.438 said each the other
        way (asserted on its table)."""
        now = _capture()
        # the three imports: 0.1.438's answer with the numbered name in place
        # of the one it kept, and nothing else changed
        for key, old, new in (
                ("agent import", '"support_types": ["Type 1"]',
                 '"support_types": ["Type 1 (2)"]'),
                ("core import", '"support_types": ["Type 1"]',
                 '"support_types": ["Type 1 (2)"]'),
                ("core import again", '"support_types": ["Type 1"]',
                 '"support_types": ["Type 1 (3)"]')):
            assert _V1438[key][1].count(old) == 1, key
            assert now[key] == [_V1438[key][0], _V1438[key][1].replace(
                old, new)], (key, now[key])
        # the set the model had is found by its name, and the support hooks
        # to it
        kind, text = now["agent support_set by the name"]
        got = json.loads(text)
        assert kind == "OK" and got["created"] and got["notes"] == [], got
        sup = got["support"]
        assert sup["class"] == "end_anchored" and sup["name"] == "Type 1", got
        assert sup["support_type"] == "<id>", got
        assert _V1438["agent support_set by the name"][0] == "NotFound"
        refused = ["Conflict", "[E_CONFLICT] A support type named 'Type 1' "
                   "exists. Hint: Pass support_type='Type 1' to change it."]
        assert now["agent rename Soil Nail to Type 1"] == refused
        assert _V1438["agent rename Soil Nail to Type 1"][0] == "OK"
        assert now["agent rename Malla to Type 1"] == refused
        # 0.1.438 had renamed another set to «MALLA» one step before (an
        # equal dataclass replaced by list.index), so «MALLA» named two
        assert _V1438["agent rename Malla to Type 1"][0] == "NotFound"
        assert now["agent two of one name"][0] == "Conflict"
        assert now["agent two of one name"][1].startswith(
            "[E_CONFLICT] 2 support types are named 'Grouted Tieback'. "
            "Hint: Pass one of their ids: '<id>' (Grouted Tieback), '<id>' "
            "(Grouted Tieback)."), now["agent two of one name"]
        assert _V1438["agent two of one name"][0] == "NotFound"
        assert json.loads(now["core names"][1]) == [
            " SILTY CLAY ", "Silty clay (2)", "Silty clay (3)", "type 1 ",
            "Type 1 (2)", "Type 1 (3)"]
        assert json.loads(_V1438["core names"][1])[3:] == [
            "type 1 ", "Type 1", "Type 1"]

    def test_a_rename_changes_the_set_it_names(self):
        """Of two sets of one class with the same parameters, renaming the
        second renames the second: the first keeps its name and every id
        stays distinct (0.1.438 replaced the first, an equal dataclass, and
        left two sets of one id; the owner's decision in step 0)."""
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            first = call(ws, "support_type_set", project_id=pid,
                         type_class="soil_nail")["support_type"]
            second = call(ws, "support_type_set", project_id=pid,
                          type_class="soil_nail", name="Malla")
            second = second["support_type"]
            call(ws, "support_type_set", project_id=pid,
                 support_type="Malla", name="MALLA")
            sets = ws.get(pid).project.support_types
            got = [(st.id, _label(st)) for st in sets]
        finally:
            ws.shutdown()
        assert got == [(first["id"], "Soil Nail"),
                       (second["id"], "MALLA")], got

    def test_what_a_rename_refuses_and_what_it_does_not(self):
        """A name another set has is refused in any case; a set's own name,
        restated or in another case, is a rename, also in a model with two
        sets of that name (the 049 shape, by id); and an unknown class says
        it by its code while changing a set as while creating one (the
        review of 0.1.439)."""
        from ogr_api import Conflict, NotFound, Workspace, call
        f, ids = _twice_named()
        ws = Workspace()
        said = []
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            call(ws, "support_type_set", project_id=pid,
                 type_class="end_anchored", name="Type 1")
            call(ws, "support_type_set", project_id=pid,
                 type_class="soil_nail", name="Malla")
            try:
                call(ws, "support_type_set", project_id=pid,
                     support_type="Malla", name="TYPE 1")
            except Conflict as exc:
                said.append(str(exc))
            try:
                call(ws, "support_type_set", project_id=pid,
                     support_type="Malla", type_class="no_such_class")
            except NotFound as exc:
                said.append(str(exc).split(" Hint:")[0])
            twice = call(ws, "project_open", path=f)["project_id"]
            for name in ("Grouted Tieback", "GROUTED TIEBACK"):
                got = call(ws, "support_type_set", project_id=twice,
                           support_type=ids[0], name=name)
                said.append(got["support_type"]["name"])
        finally:
            ws.shutdown()
        assert said == [
            "[E_CONFLICT] A support type named 'TYPE 1' exists. Hint: Pass "
            "support_type='TYPE 1' to change it.",
            "[E_NOT_FOUND] Unknown support class 'no_such_class'.",
            "Grouted Tieback", "GROUTED TIEBACK"], said

    def test_the_ambiguous_name_gives_both_ids(self):
        from ogr_api import Conflict, Workspace, call
        f, ids = _twice_named()
        ws = Workspace()
        try:
            pid = call(ws, "project_open", path=f)["project_id"]
            try:
                call(ws, "support_type_delete", project_id=pid,
                     support_type="grouted tieback")
            except Conflict as exc:
                said = str(exc)
            else:
                raise AssertionError("one of the two was deleted")
            # by id, each is found
            for i in ids:
                got = call(ws, "support_type_set", project_id=pid,
                           support_type=i, params={})
                assert got["support_type"]["id"] == i
        finally:
            ws.shutdown()
        assert all(repr(i) in said for i in ids), said


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


def _import_in_window(w, code):
    """Import Properties «Both» from the source, by the window's handler,
    with the file dialog and the item dialog replaced and put back; what
    the status bar said."""
    import ogr_gui.main_window as MW
    from PySide6.QtWidgets import QInputDialog

    from ogr_gui.i18n import tr
    saved = (MW.get_open_file_name, QInputDialog.getItem)
    MW.get_open_file_name = lambda *a, **k: (_source_file(), "")
    try:
        with _Language(code):
            QInputDialog.getItem = staticmethod(
                lambda *a, **k: (tr("Both"), True))
            w._import_properties()
            return w.statusBar().currentMessage()
    finally:
        MW.get_open_file_name, QInputDialog.getItem = saved


@_requires_qt
class TestTheWindowSaysIt:

    def test_the_bar_counts_what_was_numbered(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_core.support import EndAnchored
        from ogr_gui.labels import support_type_label
        w = _window()
        try:
            p = build_demo_project()
            p.support_types = [_set(EndAnchored, "Type 1")]
            w._attach_project(p)
            w.command_stack.clear()
            w.project.is_dirty = False
            bar = _import_in_window(w, "es")
            with _Language("es"):
                labels = [support_type_label(t)
                          for t in w.project.support_types]
            # the material and the set
            assert "2 nombre(s) se han numerado para que no se repitan." in (
                bar), bar
            assert labels == ["Tipo 1", "Tipo 1 (2)"], labels
            # without a clash, the bar does not say it
            p = build_demo_project()
            p.materials = []
            w._attach_project(p)
            w.command_stack.clear()
            w.project.is_dirty = False
            bar = _import_in_window(w, "en")
            assert bar.startswith("Imported 1 material(s) and 1 support "
                                  "type(s)."), bar
            assert "numbered" not in bar, bar
        finally:
            w.project.is_dirty = False
