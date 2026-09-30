# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.228 — a Generalized Anisotropic range takes the strength of a MATERIAL,
and the material dialog edits the ranges (defect D218 of the verification
bank, its second half, D218b).

THE DEFECT. v0.1.225 made the model honest -- no strength of zero in
silence -- but left it without an editor: the dialog showed nothing for its
ranges and said "this version defines them through the API or a script",
and every range carried its OWN copy of a strength model. The reference's
"Angle Range" input assigns "a material to each range": a range is the
strength of a material of the project, so editing that material, sampling
it in a probabilistic run or factoring it for a design standard reaches the
range. With copies, none of the three did.

THE DECISIONS.

* A rule keeps its ``model`` (the format of every earlier version) and may
  carry a ``material_id``. The analysis resolves the link on ITS copy of the
  project (``prepare_analysis_project``), after the design factors: the
  number comes from the material's strength as it is when the analysis
  runs, factored once, through the material. The copy a rule keeps is
  refreshed for display (the dialog's OK, ``material_set``) and never
  decides a number; the user's project is not modified by a calculation.
* A link names a material of the project that is neither the Generalized
  material itself nor another Generalized one
  (``rules.generalized_links_refusal``): a range takes a plain strength, so
  there are no cycles. The dialog, the API and the analysis ask it.
* The dialog edits each range as (angle to, material): "angle from" is the
  end of the range before, -90 for the first, the structure the reference
  gives this input. A rule with its own model (a file, the API, a script) is
  shown and kept, and what the user did not edit does not move (D217).
* The API links by name (``"material": "Clay"``); ``material_delete``
  counts a linked range as a use; ``properties_import`` relinks to the copy
  imported alongside or to the material of the same name.

THE REFERENCES (rule 1): identities. A Generalized material whose ranges
link Mohr-Coulomb materials is, in the nine methods and through the
analysis door, the Anisotropic Strength Function with those materials' rows
(the identity of v0.1.225) -- even when the copies its rules keep are
stale, which is what shows that the material decides; and a design factor
reaches a linked range exactly once (c/γ, tan φ/γ).

DISCRIMINATION, measured on the v0.1.227 tree: see the changelog of
v0.1.228.
"""
from __future__ import annotations

import copy
import math

#: The documented example of the Anisotropic Strength Function (as in
#: ``test_generalized_anisotropic_honest_v1225``): (angle to, c, φ).
DOC_ROWS = [(-30.0, 10.0, 35.0), (0.0, 1.0, 20.0), (90.0, 5.0, 10.0)]
#: A dry circle whose bases run from about -18 to +62 degrees.
CIRCLE = (38.0, 22.0, 23.0)
#: The copy a stale rule keeps: a strength no row has.
STALE = {"model_id": "mohr_coulomb",
         "params": {"cohesion": 99.0, "friction_angle": 1.0}}


def _mc(c, phi):
    from ogr_core.materials import MohrCoulomb
    return MohrCoulomb(cohesion=c, friction_angle=phi)


def _slope(name="links"):
    """The dry slope of ``test_anisotropic_function_ranges_v1218``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    return p


def _paint(p, m):
    p.assign_material_at(*p.resolve_regions()[0].centroid(), m.id)


def _linked_project(rows=DOC_ROWS, stale=True):
    """The slope, its one region a Generalized material whose ranges link
    one Mohr-Coulomb material each. The linked materials weigh 5 kN/m³ and
    are in no region: the weight is the parent's. The copies the rules keep
    are STALE unless ``stale`` is False."""
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    p = _slope()
    children = [Material(name=f"row{i}", unit_weight=5.0,
                         strength=_mc(c, phi))
                for i, (_hi, c, phi) in enumerate(rows)]
    rules, lo = [], -90.0
    for m, (hi, _c, _phi) in zip(children, rows):
        rules.append({"angle_min": lo, "angle_max": hi, "material_id": m.id,
                      "model": (copy.deepcopy(STALE) if stale
                                else m.strength.to_dict())})
        lo = hi
    g = Material(name="bedded", unit_weight=20.0,
                 strength=GeneralizedAnisotropic(rules=rules))
    p.materials = [g] + children
    _paint(p, g)
    return p, g, children


def _asf_project(rows=DOC_ROWS):
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import AnisotropicStrengthFunction
    p = _slope()
    m = Material(name="bedded", unit_weight=20.0,
                 strength=AnisotropicStrengthFunction(rows=rows))
    p.materials = [m]
    _paint(p, m)
    return p


def _evaluate(project, method_ids):
    """F of the circle for each method, through the analysis door."""
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    from ogr_slip2d.surface import SlipCircle
    out = evaluate_surfaces(project, SlipCircle(*CIRCLE), list(method_ids),
                            allow_unconfigured=True)
    return {mid: (r.fos if r is not None else None)
            for mid, r in out.results.items()}


def _raises(fn, *exc_types):
    try:
        fn()
    except exc_types as exc:
        return exc
    raise AssertionError(f"{fn} did not raise {exc_types}")


# ======================================================================
class TestTheAnalysisTakesTheMaterial:
    """The link is resolved on the analysis copy, from the material as it
    is when the analysis runs."""

    def test_stale_copies_do_not_decide_the_number(self):
        """Rule 1: in the nine methods, the Anisotropic Strength Function
        with the linked materials' rows -- not with the stale copies."""
        from ogr_slip2d.methods import method_registry
        mids = sorted(method_registry())
        linked, _g, _c = _linked_project()
        a = _evaluate(linked, mids)
        b = _evaluate(_asf_project(), mids)
        assert len(mids) == 9, mids
        for mid in mids:
            assert a[mid] is not None and b[mid] is not None, (mid, a, b)
            assert math.isclose(a[mid], b[mid], rel_tol=1e-12), (
                mid, a[mid], b[mid])

    def test_editing_the_material_moves_the_number(self):
        """Rule 7: the material decides, so editing it moves F -- to what
        the function with the edited row gives."""
        mid = "bishop_simplified"
        linked, _g, children = _linked_project(stale=False)
        before = _evaluate(linked, [mid])[mid]
        children[1].strength = _mc(3.0, 20.0)
        after = _evaluate(linked, [mid])[mid]
        rows = list(DOC_ROWS)
        rows[1] = (0.0, 3.0, 20.0)
        expected = _evaluate(_asf_project(rows), [mid])[mid]
        assert after > before * (1.0 + 1e-6), (before, after)
        assert math.isclose(after, expected, rel_tol=1e-12), (after,
                                                              expected)

    def test_the_project_keeps_what_it_had(self):
        """No calculation modifies the user's project: the stale copies
        are still there after the analysis resolved them on its copy."""
        linked, g, _c = _linked_project()
        before = copy.deepcopy(g.strength.rules)
        _evaluate(linked, ["bishop_simplified"])
        assert g.strength.rules == before

    def test_no_link_no_copy(self):
        """Without a link or a standard the analysis computes on the
        project itself, as it always did."""
        from ogr_core.project import prepare_analysis_project
        plain = _asf_project()
        assert prepare_analysis_project(plain)[0] is plain
        linked, _g, _c = _linked_project()
        assert prepare_analysis_project(linked)[0] is not linked

    def test_a_link_does_not_migrate_the_model(self):
        """The copy is not a round trip through the loader, which reads a
        max_lambda of 1.5 as a file saved before v0.1.90 and makes it 6.0
        (D182): the analysis of a model with a link computes with the
        settings the user chose."""
        from ogr_core.project import prepare_analysis_project
        linked, _g, _c = _linked_project()
        linked.settings.advanced.max_lambda = 1.5
        ready = prepare_analysis_project(linked)[0]
        assert ready.settings.advanced.max_lambda == 1.5

    def test_a_sample_of_the_material_reaches_the_range(self):
        """A probabilistic run samples the MATERIAL; each sample is then
        prepared like the analysis (``run_configured_statistics``)."""
        from ogr_core.project import prepare_analysis_project
        from ogr_core.statistics.random_variables import (
            RandomVariable, VariableKind, apply_sample, clone_project)
        linked, g, children = _linked_project(stale=False)
        rv = RandomVariable(kind=VariableKind.MATERIAL_STRENGTH,
                            target_id=children[1].id, param="cohesion")
        clone = clone_project(linked)
        assert apply_sample(clone, [rv], {rv.key: 7.5}) == 1
        ready = prepare_analysis_project(clone)[0]
        rule = ready.material_by_id(g.id).strength.rules[1]
        assert rule["model"]["params"]["cohesion"] == 7.5
        assert g.strength.rules[1]["model"]["params"]["cohesion"] == 1.0

    def test_the_statistics_prepare_each_sample_like_the_analysis(self):
        import ast
        import inspect

        from ogr_slip2d import analysis_runner
        tree = ast.parse(inspect.getsource(
            analysis_runner.run_configured_statistics))
        prepare = next(n for n in ast.walk(tree)
                       if isinstance(n, ast.FunctionDef)
                       and n.name == "prepare")
        called = {n.func.id for n in ast.walk(prepare)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "prepare_analysis_project" in called, called


class TestTheDesignFactorsReachARangeOnce:

    def _factored(self, project):
        from ogr_core.project import prepare_analysis_project
        ds = project.settings.design_standard
        ds.enabled = True
        ds.standard = "custom"
        ds.factor_cohesion = 1.25
        ds.factor_friction = 1.25
        return prepare_analysis_project(project)[0]

    @staticmethod
    def _assert_factored_once(params, c, phi):
        assert math.isclose(params["cohesion"], c / 1.25, rel_tol=1e-15), (
            params, c)
        assert math.isclose(math.tan(math.radians(params["friction_angle"])),
                            math.tan(math.radians(phi)) / 1.25,
                            rel_tol=1e-12), (params, phi)

    def test_a_linked_range_takes_the_factored_material(self):
        linked, g, _c = _linked_project()
        ready = self._factored(linked)
        rules = ready.material_by_id(g.id).strength.rules
        for rule, (_hi, c, phi) in zip(rules, DOC_ROWS):
            self._assert_factored_once(rule["model"]["params"], c, phi)

    def test_a_range_with_its_own_model_is_factored_once_too(self):
        linked, g, _c = _linked_project(stale=False)
        g.strength.rules[1].pop("material_id")
        ready = self._factored(linked)
        rules = ready.material_by_id(g.id).strength.rules
        for rule, (_hi, c, phi) in zip(rules, DOC_ROWS):
            self._assert_factored_once(rule["model"]["params"], c, phi)


# ======================================================================
class TestTheRule:

    def _refusal(self, project, g):
        from ogr_core.project.rules import generalized_links_refusal
        return generalized_links_refusal(g, project.materials)

    def test_links_to_materials_of_the_project(self):
        linked, g, _c = _linked_project()
        assert self._refusal(linked, g) is None

    def test_a_link_to_nothing(self):
        linked, g, _c = _linked_project()
        g.strength.rules[0]["material_id"] = "not-a-material"
        assert self._refusal(linked, g).code == "generalized_link_missing"

    def test_a_link_to_itself(self):
        linked, g, _c = _linked_project()
        g.strength.rules[2]["material_id"] = g.id
        assert self._refusal(linked, g).code == "generalized_link_self"

    def test_a_link_to_another_generalized_material(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        linked, g, _c = _linked_project()
        other = Material(name="other", strength=GeneralizedAnisotropic(
            rules=copy.deepcopy(g.strength.rules)))
        linked.materials.append(other)
        g.strength.rules[1]["material_id"] = other.id
        assert self._refusal(linked, g).code == \
            "generalized_link_generalized"

    def test_the_analysis_refuses_it_by_name(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        linked, g, _c = _linked_project()
        g.strength.rules[0]["material_id"] = "not-a-material"
        problems = check_analysis_settings(linked)
        assert any("'bedded'" in s and "not in the project" in s
                   for s in problems), problems

    def test_a_bad_link_is_left_for_the_rule_to_refuse(self):
        from ogr_core.project import resolve_generalized_links
        linked, g, _c = _linked_project()
        g.strength.rules[0]["material_id"] = "not-a-material"
        g.strength.rules[2]["material_id"] = g.id
        before = copy.deepcopy(g.strength.rules)
        resolve_generalized_links(linked.materials)
        assert g.strength.rules[0] == before[0]
        assert g.strength.rules[2] == before[2]
        assert g.strength.rules[1]["model"] == \
            linked.materials[2].strength.to_dict()


# ======================================================================
_CLAY = {"model": "mohr_coulomb",
         "params": {"cohesion": 5.0, "friction_angle": 30.0}}
_SAND = {"model": "mohr_coulomb",
         "params": {"cohesion": 0.0, "friction_angle": 35.0}}


class TestTheApi:

    def _ws(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="Links")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, -10], [60, -10], [60, 12], [50, 12], [30, 0],
                         [0, 0]],
            "materials": [
                {"name": "Clay", "unit_weight": 20.0, "strength": _CLAY},
                {"name": "Sand", "unit_weight": 20.0, "strength": _SAND},
                {"name": "Bedded", "unit_weight": 20.0, "strength": {
                    "model": "generalized_anisotropic", "rules": [
                        {"angle_min": -90, "angle_max": 0,
                         "material": "clay"},
                        {"angle_min": 0, "angle_max": 90,
                         "material": "Sand"}]}}]})
        return ws, pid

    @staticmethod
    def _named(ws, pid, name):
        return next(m for m in ws.get(pid).project.materials
                    if m.name == name)

    def test_model_define_links_by_name(self):
        ws, pid = self._ws()
        clay, sand = self._named(ws, pid, "Clay"), self._named(ws, pid, "Sand")
        rules = self._named(ws, pid, "Bedded").strength.rules
        assert [r["material_id"] for r in rules] == [clay.id, sand.id]
        assert rules[0]["model"] == clay.strength.to_dict()
        assert "material" not in rules[0]

    def test_a_material_not_yet_defined_cannot_be_linked(self):
        from ogr_api import call
        from ogr_api.errors import InvalidArgument
        ws, pid = self._ws()
        exc = _raises(lambda: call(
            ws, "material_set", project_id=pid, name="Later", strength={
                "model": "generalized_anisotropic", "rules": [
                    {"angle_min": -90, "angle_max": 90,
                     "material": "Gravel"}]}), InvalidArgument)
        assert "Gravel" in exc.message and exc.hint

    def test_a_range_cannot_link_its_own_material(self):
        from ogr_api import call
        from ogr_api.errors import InvalidArgument
        ws, pid = self._ws()
        _raises(lambda: call(
            ws, "material_set", project_id=pid, material="Bedded",
            strength={"model": "generalized_anisotropic", "rules": [
                {"angle_min": -90, "angle_max": 90,
                 "material": "Bedded"}]}), InvalidArgument)

    def test_editing_the_material_refreshes_the_copy(self):
        from ogr_api import call
        ws, pid = self._ws()
        call(ws, "material_set", project_id=pid, material="Clay",
             strength={"model": "mohr_coulomb",
                       "params": {"cohesion": 8.0, "friction_angle": 30.0}})
        rule = self._named(ws, pid, "Bedded").strength.rules[0]
        assert rule["model"]["params"]["cohesion"] == 8.0

    def test_deleting_a_linked_material_is_a_conflict(self):
        from ogr_api import call
        from ogr_api.errors import Conflict
        ws, pid = self._ws()
        exc = _raises(lambda: call(ws, "material_delete", project_id=pid,
                                   material="Clay"), Conflict)
        assert "1 Generalized Anisotropic range" in exc.message, exc.message
        assert self._named(ws, pid, "Clay") is not None

    def test_reassigning_moves_the_link(self):
        from ogr_api import call
        ws, pid = self._ws()
        call(ws, "material_delete", project_id=pid, material="Clay",
             reassign_to="Sand")
        sand = self._named(ws, pid, "Sand")
        rule = self._named(ws, pid, "Bedded").strength.rules[0]
        assert rule["material_id"] == sand.id
        assert rule["model"] == sand.strength.to_dict()

    def test_forcing_keeps_the_strength_unlinked(self):
        from ogr_api import call
        ws, pid = self._ws()
        call(ws, "material_delete", project_id=pid, material="Clay",
             force=True)
        rule = self._named(ws, pid, "Bedded").strength.rules[0]
        assert "material_id" not in rule
        assert rule["model"]["params"] == _CLAY["params"]

    def test_a_generalized_material_cannot_take_the_ranges(self):
        from ogr_api import call
        from ogr_api.errors import Conflict
        ws, pid = self._ws()
        call(ws, "material_set", project_id=pid, name="Other", strength={
            "model": "generalized_anisotropic", "rules": [
                {"angle_min": -90, "angle_max": 90, "material": "Sand"}]})
        _raises(lambda: call(ws, "material_delete", project_id=pid,
                             material="Clay", reassign_to="Other"), Conflict)


# ======================================================================
class TestPropertiesImport:

    def _source(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.project import Project
        src = Project("source")
        clay = Material(name="Clay", strength=_mc(5.0, 30.0))
        sand = Material(name="Sand", strength=_mc(0.0, 35.0))
        silt = Material(name="Silt", strength=_mc(2.0, 25.0))
        g = Material(name="G", strength=GeneralizedAnisotropic(rules=[
            {"angle_min": -90.0, "angle_max": -30.0, "material_id": clay.id,
             "model": clay.strength.to_dict()},
            {"angle_min": -30.0, "angle_max": 30.0, "material_id": sand.id,
             "model": sand.strength.to_dict()},
            {"angle_min": 30.0, "angle_max": 90.0, "material_id": silt.id,
             "model": silt.strength.to_dict()}]))
        src.materials = [clay, sand, silt, g]
        return src, g

    def test_each_link_finds_a_material_of_this_model(self):
        from ogr_core.materials import Material
        from ogr_core.project import Project
        from ogr_core.project.properties_import import import_properties
        src, g = self._source()
        before = copy.deepcopy(g.strength.rules)
        dst = Project("destination")
        dst.materials = [Material(name="sand", strength=_mc(1.0, 33.0))]
        out = import_properties(dst, src, support_types=False,
                                names=["G", "Clay"])
        by_name = {m.name: m for m in dst.materials}
        rules = by_name["G"].strength.rules
        # Imported alongside: the copy.
        assert rules[0]["material_id"] == by_name["Clay"].id
        # Not imported, but here by name: that one, and its strength.
        assert rules[1]["material_id"] == by_name["sand"].id
        assert rules[1]["model"]["params"] == {"cohesion": 1.0,
                                               "friction_angle": 33.0}
        # Nowhere: unlinked, with the strength it had.
        assert "material_id" not in rules[2]
        assert rules[2]["model"] == before[2]["model"]
        assert any("range 2" in n and "'sand'" in n for n in out["notes"])
        assert any("range 3" in n and "unlinked" in n for n in out["notes"])
        # The other project is not touched.
        assert g.strength.rules == before


# ======================================================================
class TestTheDialog:
    """The editor of the ranges: (angle to, material)."""

    def _materials(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        clay = Material(name="Clay", strength=_mc(5.0, 30.0))
        sand = Material(name="Sand", strength=_mc(0.0, 35.0))
        g = Material(name="G", strength=GeneralizedAnisotropic(rules=[
            {"angle_min": -90.0, "angle_max": -10.0, "material_id": clay.id,
             "model": clay.strength.to_dict()},
            {"angle_min": -10.0, "angle_max": 10.0,
             "model": _mc(2.0, 20.0).to_dict()},
            {"angle_min": 10.0, "angle_max": 90.0, "material_id": sand.id,
             "model": sand.strength.to_dict()}]))
        return [clay, sand, g]

    def _dialog(self, materials, row):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        dlg = MaterialPropertiesDialog(materials)
        dlg.list.setCurrentRow(row)
        dlg.accepted_calls = []
        dlg.accept = lambda: dlg.accepted_calls.append(True)
        return dlg

    @staticmethod
    def _choose(table, row, material):
        combo = table.cellWidget(row, 1)
        combo.setCurrentIndex(combo.findData(f"material:{material.id}"))

    @staticmethod
    def _type(table, row, text):
        from PySide6.QtWidgets import QTableWidgetItem
        table.setItem(row, 0, QTableWidgetItem(text))

    def test_the_ranges_are_shown_as_angle_to_and_material(self):
        dlg = self._dialog(self._materials(), 2)
        panel = dlg.param_panel
        tbl = panel._table
        assert panel.table_headers() == ["Angle to (°)", "Material"]
        assert [tbl.item(r, 0).text() for r in range(3)] == [
            "-10", "10", "90"]
        shown = [tbl.cellWidget(r, 1).currentText() for r in range(3)]
        assert shown == ["Clay", "(own model: Mohr-Coulomb)", "Sand"], shown
        assert dlg.lbl_strength_problem.isHidden()

    def test_the_choices_leave_out_the_material_and_the_generalized(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        mats = self._materials()
        mats.append(Material(name="Other", strength=GeneralizedAnisotropic(
            rules=copy.deepcopy(mats[2].strength.rules))))
        dlg = self._dialog(mats, 2)
        combo = dlg.param_panel._table.cellWidget(0, 1)
        assert [combo.itemText(i) for i in range(combo.count())] == [
            "Clay", "Sand"]

    def test_ok_without_touching_keeps_every_rule(self):
        mats = self._materials()
        before = copy.deepcopy(mats[2].strength.rules)
        dlg = self._dialog(mats, 2)
        dlg._ok()
        assert dlg.accepted_calls == [True]
        assert dlg.result_materials()[2].strength.rules == before

    def test_an_edit_builds_contiguous_linked_ranges(self):
        mats = self._materials()
        clay, sand = mats[0], mats[1]
        dlg = self._dialog(mats, 2)
        tbl = dlg.param_panel._table
        self._choose(tbl, 1, clay)
        self._type(tbl, 0, "-20")
        dlg._ok()
        assert dlg.accepted_calls == [True]
        rules = dlg.result_materials()[2].strength.rules
        assert [(r["angle_min"], r["angle_max"]) for r in rules] == [
            (-90.0, -20.0), (-20.0, 10.0), (10.0, 90.0)]
        assert [r.get("material_id") for r in rules] == [
            clay.id, clay.id, sand.id]
        assert rules[1]["model"] == clay.strength.to_dict()

    def test_an_own_model_is_kept_when_another_row_is_edited(self):
        mats = self._materials()
        own = copy.deepcopy(mats[2].strength.rules[1]["model"])
        dlg = self._dialog(mats, 2)
        self._type(dlg.param_panel._table, 0, "-5")
        dlg._ok()
        rule = dlg.result_materials()[2].strength.rules[1]
        assert (rule["angle_min"], rule["angle_max"]) == (-5.0, 10.0)
        assert rule["model"] == own and "material_id" not in rule

    def test_a_new_row_offers_the_materials(self):
        from PySide6.QtWidgets import QPushButton
        dlg = self._dialog(self._materials(), 2)
        panel = dlg.param_panel
        # The last one: the panel's earlier tables are only deleteLater()'d.
        add = [b for b in panel.findChildren(QPushButton)
               if b.text() == "+ Row"][-1]
        add.click()
        combo = panel._table.cellWidget(3, 1)
        assert [combo.itemText(i) for i in range(combo.count())] == [
            "Clay", "Sand"]
        assert combo.currentText() == "Clay"

    def test_an_angle_that_is_not_a_number_is_refused(self):
        dlg = self._dialog(self._materials(), 2)
        self._type(dlg.param_panel._table, 1, "ten")
        dlg._ok()
        assert dlg.accepted_calls == []
        assert "Row 2" in dlg.lbl_strength_problem.text()
        assert "angle to" in dlg.lbl_strength_problem.text()

    def test_a_linked_material_cannot_be_removed(self):
        dlg = self._dialog(self._materials(), 0)
        dlg._remove_material()
        assert [m.name for m in dlg.materials] == ["Clay", "Sand", "G"]
        text = dlg.lbl_strength_problem.text()
        assert "Clay" in text and "G" in text, text

    def test_editing_the_material_refreshes_the_copy_at_ok(self):
        dlg = self._dialog(self._materials(), 0)
        dlg.param_panel._editors["cohesion"].setValue(8.0)
        dlg._ok()
        assert dlg.accepted_calls == [True]
        rule = dlg.result_materials()[2].strength.rules[0]
        assert rule["model"]["params"]["cohesion"] == 8.0

    def test_a_linked_material_turned_generalized_is_refused(self):
        """The Generalized material was not touched, but the material its
        range takes was: it is judged, and refused."""
        dlg = self._dialog(self._materials(), 0)
        dlg.cbo_strength.setCurrentIndex(
            dlg.cbo_strength.findData("generalized_anisotropic"))
        dlg._ok()
        assert dlg.accepted_calls == []
        assert "another Generalized" in dlg.lbl_strength_problem.text()

    def test_a_new_selection_takes_the_first_material(self):
        # Clay and Sand only: in the full set G links Sand, which could then
        # not become Generalized (the case above).
        dlg = self._dialog(self._materials()[:2], 1)
        dlg.cbo_strength.setCurrentIndex(
            dlg.cbo_strength.findData("generalized_anisotropic"))
        dlg._ok()
        assert dlg.accepted_calls == [True]
        rules = dlg.result_materials()[1].strength.rules
        assert [(r["angle_min"], r["angle_max"]) for r in rules] == [
            (-90.0, 90.0)]
        assert rules[0]["material_id"] == dlg.materials[0].id

    def test_the_captions_have_their_spanish(self):
        """Translated through a variable, which the coverage test cannot
        see."""
        from ogr_gui.dialogs.material_properties_dialog import (
            _StrengthParamPanel)
        from ogr_gui.i18n import _DICTS
        missing = [t for t in _StrengthParamPanel._TABLE_CAPTIONS.values()
                   if t not in _DICTS["es"]]
        assert not missing, missing
