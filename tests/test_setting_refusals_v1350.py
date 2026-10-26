# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.350 (D335, fourth part) — why a project cannot be analysed as
configured carries stable codes, and the window's refusal boxes say it in
Spanish.

``check_analysis_settings`` refuses a run rather than compute a plausible
number from settings that were dropped; the core's rules refuse an
optimisation technique, overlapping Slope Limit windows, a Block Search
object, a seismic coefficient, a partial factor, a line load off the ground;
the drawdown refuses a run it would not perform. They were English
sentences with their values baked in, shown through ``tr()`` -- which found
nothing, because the key had the values in it. Each is a code now
(``ogr_core.project.messages.REFUSALS``, ``ogr_slip2d.setting_messages``),
and the two run-level drawdown refusals carry theirs too: the exception
``test_core_messages_v1333`` kept for them is empty.

The invariants:

* **the English is v0.1.349's, byte for byte** (``_V1349``, from that
  version's source, evaluated); the nested labels and refusals are built
  with the NEW catalogues;
* every code is sampled and says itself in Spanish with its fields;
* **no sentence of these functions is built without its code** (AST
  census);
* **in the window, in Spanish**: the Compute box on a model whose seismic
  coefficient a file left negative, and every refusal box reads the codes;
* the API still answers in English.
"""
from __future__ import annotations

import ast
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``{cat, code, args, english}``: the sentence v0.1.349 wrote. ``cat`` is
#: the catalogue (``core``, ``engine``, or ``rules`` for a refusal of
#: v0.1.347 nested in one of these); a nested value is
#: ``{"$code", "$cat", "$args"}``, an uncoded one ``{"$raw": text}``.
_V1349 = [{'cat': 'core',
  'code': 'rule.optimize_technique_unknown',
  'english': "Unknown optimisation technique 'anneal': it has to be one of "
             'monte_carlo, surface_altering.',
  'args': {'value': 'anneal', 'allowed': 'monte_carlo, surface_altering'}},
 {'cat': 'core',
  'code': 'rule.slope_limit_windows_overlap',
  'english': 'The two sets of Slope Limits overlap ([10, 40.5] and [30, '
             '80]). With two sets, a Grid Search generates the circles that '
             'run from one window to the other, a rule measured on separate '
             'windows only: on the stretch two windows share it gives every '
             'crossing to the window that starts further left, which nothing '
             'measured supports, and with a window inside one that starts '
             'further left it generates no circle at all. Make the two '
             'windows separate, or use a single set.',
  'args': {'a0': 10.0, 'a1': 40.5, 'b0': 30.0, 'b1': 80.0}},
 {'cat': 'core',
  'code': 'rule.block_object_named',
  'english': 'Weak seam #2: A Block Search object needs at least one vertex.',
  'args': {'label': {'$code': 'rule.block_label_named',
                     '$cat': 'core',
                     '$args': {'name': 'Weak seam', 'n': 2}},
           'why': {'$code': 'rule.block_object_empty',
                   '$cat': 'rules',
                   '$args': {}}}},
 {'cat': 'core',
  'code': 'rule.block_polyline_overlap',
  'english': 'Block Search Object #1 overlaps the lateral extent of the '
             'Block Search Polyline Weak seam #2 (x from 12.5 to 48). This '
             'is not allowed: the trial surface follows the polyline between '
             'its two points, and a vertex of another object inside that '
             'range would cut the stretch. To search them separately, turn '
             'Multiple Groups on and give them different Group IDs.',
  'args': {'other': {'$code': 'rule.block_label_kind',
                     '$cat': 'core',
                     '$args': {'kind': 'Block Search Object', 'n': 1}},
           'polyline': {'$code': 'rule.block_label_named',
                        '$cat': 'core',
                        '$args': {'name': 'Weak seam', 'n': 2}},
           'lo': 12.5,
           'hi': 48.0,
           'where': {'$nothing': True},
           'way_out': {'$code': 'rule.block_overlap_way_ungrouped',
                       '$cat': 'core',
                       '$args': {}}}},
 {'cat': 'core',
  'code': 'rule.block_polyline_overlap',
  'english': 'Block Search Object #1 overlaps the lateral extent of the '
             'Block Search Polyline Weak seam #2 (x from 12.5 to 48) (both '
             'in Group ID 3). This is not allowed: the trial surface follows '
             'the polyline between its two points, and a vertex of another '
             'object inside that range would cut the stretch. Give them '
             'different Group IDs to search them separately.',
  'args': {'other': {'$code': 'rule.block_label_kind',
                     '$cat': 'core',
                     '$args': {'kind': 'Block Search Object', 'n': 1}},
           'polyline': {'$code': 'rule.block_label_named',
                        '$cat': 'core',
                        '$args': {'name': 'Weak seam', 'n': 2}},
           'lo': 12.5,
           'hi': 48.0,
           'where': {'$code': 'rule.block_overlap_group',
                     '$cat': 'core',
                     '$args': {'group': 3}},
           'way_out': {'$code': 'rule.block_overlap_way_grouped',
                       '$cat': 'core',
                       '$args': {}}}},
 {'cat': 'core',
  'code': 'rule.seismic_not_a_number',
  'english': "kv must be a number, got '0.1g'.",
  'args': {'name': 'kv', 'value': '0.1g'}},
 {'cat': 'core',
  'code': 'rule.seismic_out_of_range',
  'english': '|kh| must be below 1 (a fraction of g), got 1.25.',
  'args': {'name': 'kh', 'value': 1.25}},
 {'cat': 'core',
  'code': 'rule.seismic_kh_negative',
  'english': 'kh must not be negative, got -0.1. It is the magnitude of the '
             'horizontal seismic force, which always acts in the sliding '
             'direction of each surface, out of the slope; its sign does not '
             'choose a direction.',
  'args': {'value': -0.1}},
 {'cat': 'core',
  'code': 'rule.design_not_a_number.factor_permanent',
  'english': 'The partial factor on permanent actions, unfavourable must be '
             "a finite number, got 'x1.35'.",
  'args': {'raw': 'x1.35'}},
 {'cat': 'core',
  'code': 'rule.design_not_a_number.factor_permanent_favourable',
  'english': 'The partial factor on permanent actions, favourable must be a '
             "finite number, got 'x1.35'.",
  'args': {'raw': 'x1.35'}},
 {'cat': 'core',
  'code': 'rule.design_not_a_number.factor_variable',
  'english': 'The partial factor on variable actions, unfavourable must be a '
             "finite number, got 'x1.35'.",
  'args': {'raw': 'x1.35'}},
 {'cat': 'core',
  'code': 'rule.design_not_a_number.factor_variable_favourable',
  'english': 'The partial factor on variable actions, favourable must be a '
             "finite number, got 'x1.35'.",
  'args': {'raw': 'x1.35'}},
 {'cat': 'core',
  'code': 'rule.design_permanent_below_one',
  'english': 'The partial factor on unfavourable permanent actions must be '
             'at least 1, got 0.95: below 1 it would make the driving weight '
             'lighter than the characteristic one.',
  'args': {'value': 0.95}},
 {'cat': 'core',
  'code': 'rule.design_permanent_favourable_above_one',
  'english': 'The partial factor on favourable permanent actions must be at '
             'most 1, got 1.1: above 1 it would make the resisting weight '
             'heavier than the characteristic one.',
  'args': {'value': 1.1}},
 {'cat': 'core',
  'code': 'rule.design_permanent_favourable_not_positive',
  'english': 'The partial factor on favourable permanent actions must be '
             'above 0, got 0.0: a permanent action keeps its sign, and at 0 '
             'the slices that resist would have no weight.',
  'args': {'value': 0.0}},
 {'cat': 'core',
  'code': 'rule.design_variable_below_one',
  'english': 'The partial factor on unfavourable variable actions must be at '
             'least 1, got 0.8: below 1 it would make a load that drives the '
             'sliding lighter than its characteristic value.',
  'args': {'value': 0.8}},
 {'cat': 'core',
  'code': 'rule.design_variable_favourable_above_one',
  'english': 'The partial factor on favourable variable actions must be at '
             'most 1, got 1.2: above 1 it would make a load that resists the '
             'sliding heavier than its characteristic value.',
  'args': {'value': 1.2}},
 {'cat': 'core',
  'code': 'rule.design_variable_favourable_negative',
  'english': 'The partial factor on favourable variable actions must not be '
             'negative, got -0.5: at 0 the load is left out, which is the '
             'most a favourable variable action can be discounted.',
  'args': {'value': -0.5}},
 {'cat': 'core',
  'code': 'rule.line_load_needs_ground',
  'english': 'Line load Truck: an orientation relative to the boundary needs '
             'the ground surface.',
  'args': {'name': 'Truck'}},
 {'cat': 'core',
  'code': 'rule.line_load_off_ground',
  'english': 'Line load L7 at (31.5, 40.25) is not on the ground surface, so '
             'it has no boundary to be normal to.',
  'args': {'name': 'L7', 'x': 31.5, 'y': 40.25}},
 {'cat': 'engine',
  'code': 'setting.grid_type_mismatch.total_head',
  'english': 'The water pressure grid was built as total head values, but '
             'the groundwater method is grid_pore_pressure. The method '
             'decides how the grid is read: set it to grid_total_head, or '
             'build the grid without a type.',
  'args': {'method': 'grid_pore_pressure', 'wanted': 'grid_total_head'}},
 {'cat': 'engine',
  'code': 'setting.grid_type_mismatch.pressure_head',
  'english': 'The water pressure grid was built as pressure head values, but '
             'the groundwater method is grid_total_head. The method decides '
             'how the grid is read: set it to grid_pressure_head, or build '
             'the grid without a type.',
  'args': {'method': 'grid_total_head', 'wanted': 'grid_pressure_head'}},
 {'cat': 'engine',
  'code': 'setting.grid_type_mismatch.pore_pressure',
  'english': 'The water pressure grid was built as pore pressure values, but '
             'the groundwater method is grid_total_head. The method decides '
             'how the grid is read: set it to grid_pore_pressure, or build '
             'the grid without a type.',
  'args': {'method': 'grid_total_head', 'wanted': 'grid_pore_pressure'}},
 {'cat': 'engine',
  'code': 'setting.line_load_move',
  'english': 'Line load L7 at (31.5, 40.25) is not on the ground surface, so '
             'it has no boundary to be normal to. Move it onto the ground '
             'surface or give it an absolute orientation.',
  'args': {'reason': {'$code': 'rule.line_load_off_ground',
                      '$cat': 'core',
                      '$args': {'name': 'L7', 'x': 31.5, 'y': 40.25}}}},
 {'cat': 'engine',
  'code': 'setting.fem_field_missing',
  'english': 'These materials take their pore pressure from a finite-element '
             'seepage field, and this project has no computed field: Clay, '
             'Silt. Run the groundwater analysis first — computing now would '
             'report u = 0 everywhere, which looks like a dry slope.',
  'args': {'materials': 'Clay, Silt'}},
 {'cat': 'engine',
  'code': 'setting.design_seismic',
  'english': "With the design standard's seismic factor 1.25: |kh| must be "
             'below 1 (a fraction of g), got 1.0625.',
  'args': {'factor': 1.25,
           'reason': {'$code': 'rule.seismic_out_of_range',
                      '$cat': 'core',
                      '$args': {'name': 'kh', 'value': 1.0625}}}},
 {'cat': 'engine',
  'code': 'setting.shadow_removed',
  'english': 'This project sets grid_refine = True. That setting was removed '
             'in v0.1.103: no analysis ever read it, and it has no '
             'replacement.',
  'args': {'name': 'grid_refine', 'value': 'True', 'version': 'v0.1.103'}},
 {'cat': 'engine',
  'code': 'setting.shadow_renamed',
  'english': 'This project sets path_num_paths = 300. That name was removed '
             'in v0.1.103 because the interface never showed it; set '
             'path_num_surfaces instead. Computing now would ignore the '
             'value and report a plausible number.',
  'args': {'name': 'path_num_paths',
           'value': '300',
           'version': 'v0.1.103',
           'survivor': 'path_num_surfaces'}},
 {'cat': 'engine',
  'code': 'setting.drawdown_unknown',
  'english': "'corps' is not a rapid-drawdown procedure, so the analysis "
             'would ignore the drawdown entirely. Available: '
             'duncan_wright_wong, lowe_karafiath, b_bar.',
  'args': {'method': 'corps',
           'available': 'duncan_wright_wong, lowe_karafiath, b_bar'}},
 {'cat': 'engine',
  'code': 'setting.drawdown_needs_surfaces',
  'english': 'Rapid drawdown defines both reservoir levels with water '
             "surfaces, so it cannot run with groundwater method 'ru'. "
             'Choose Water Surfaces.',
  'args': {'method': 'ru'}},
 {'cat': 'engine',
  'code': 'setting.drawdown_no_undrained',
  'english': 'No material is marked as having undrained behaviour, so the '
             'drawdown would not change any strength. Tick Undrained '
             'Behaviour on the low-permeability materials.',
  'args': {}},
 {'cat': 'engine',
  'code': 'setting.drawdown_line_above',
  'english': 'The Drawdown Line lies ABOVE the Water Table. The water table '
             'is the initial reservoir level and the drawdown line the '
             'final, lower one; swap them.',
  'args': {}},
 {'cat': 'engine',
  'code': 'setting.drawdown_gap',
  'english': "This project asks for a rapid drawdown ('duncan_wright_wong'), "
             "and the method 'spencer' does not perform one, so the factor "
             'of safety would be the ordinary DRAINED one at the lowered '
             'water level. Build the method with '
             'ogr_slip2d.analysis_runner.build_method(project, method_id), '
             'which is the one place that applies the drawdown wrapper.',
  'args': {'drawdown': 'duncan_wright_wong', 'method': 'spencer'}}]


def _cat(name):
    from ogr_core.project.messages import REFUSALS, RULES
    from ogr_slip2d.setting_messages import SETTING_NOTES
    return {"core": REFUSALS, "engine": SETTING_NOTES, "rules": RULES}[name]


def _resolve(v):
    from ogr_core.messages import as_nested, coded, nested
    if isinstance(v, dict) and "$nothing" in v:
        return nested("", {}, "")
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


# ======================================================================
class TestTheEnglishIsTheOldOne:

    def test_every_code_with_its_sample(self):
        for case in _V1349:
            assert _message(case) == case["english"], case["code"]

    def test_the_samples_cover_every_code(self):
        seen = set()
        for case in _V1349:
            seen.add(case["code"])
            seen.update(_nested_codes(case["args"]))
        every = set(_cat("core")) | set(_cat("engine"))
        assert seen - set(_cat("rules")) == every, every ^ seen


class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for name in ("core", "engine"):
            for code, spec in _cat(name).items():
                if _wordless(spec.english):
                    continue
                assert spec.english in es, (code, spec.english[:60])
                assert _fields(es[spec.english]) == _fields(spec.english), code
                assert es[spec.english] != spec.english, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            for case in _V1349:
                said = note_text(_message(case))
                assert said and said != case["english"], case["code"]
                assert "{" not in said, (case["code"], said)
        finally:
            set_language(before)


# ======================================================================
_CODED = {
    "ogr_slip2d/analysis_runner.py": ("check_analysis_settings",
                                      "_shadow_setting_problems"),
    "ogr_slip2d/rapid_drawdown.py": ("check_drawdown_settings",
                                     "drawdown_gap", "wrap_for_drawdown"),
    "ogr_core/project/rules.py": (
        "optimize_technique_refusal", "slope_limit_windows_refusal",
        "block_objects_refusal", "_block_label",
        "seismic_coefficient_refusal", "design_action_factors_refusal"),
    "ogr_core/loads/loads.py": ("ground_frame",),
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
                for n in ast.walk(fn):
                    if n is doc:
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
                        # a Refusal's own code is an identifier, not words
                        found.append((rel, name, n.lineno, "sentence"))
        assert not found, found

    def test_the_run_level_drawdown_refusal_has_its_code(self):
        from types import SimpleNamespace as NS

        from ogr_slip2d.rapid_drawdown import (RapidDrawdownError,
                                               wrap_for_drawdown)
        gw = NS(rapid_drawdown=True, rapid_drawdown_method="no_such_one",
                method="water_table")
        project = NS(settings=NS(groundwater=gw), materials=[])
        try:
            wrap_for_drawdown(object(), project)
        except RapidDrawdownError as exc:
            assert exc.code == "setting.drawdown_unknown", exc.code
            assert exc.values["method"] == "no_such_one"
        else:
            raise AssertionError("not refused")

    def test_every_refusal_box_of_the_window_reads_the_codes(self):
        src = (_ROOT / "ogr_gui" / "main_window.py").read_text(
            encoding="utf-8")
        assert "tr(p) for p in exc.problems" not in src
        assert '"  ".join(exc.problems)' not in src
        assert '"\\n\\n".join(_why)' not in src
        flat = " ".join(src.split())
        # v0.1.366 (D362): six — the drawdown sweep's refusal is said by the
        # window, which runs it through ``run_task``, and its worker's own
        # ``run`` keeps the one it had
        assert flat.count("note_text(p) for p in exc.problems") == 6
        assert "note_text(p) for p in _why" in flat


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


def _negative_kh_project():
    """The slope of v1347 with a pseudo-static coefficient a file left
    negative: no dialog writes it, so only Compute refuses it."""
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Refusals")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 3.0,
                                                   "friction_angle": 19.6}}}]})
        p = ws.get(pid).project
    finally:
        ws.shutdown()
    p.seismic.enabled = True
    p.seismic.kh = -0.1
    return p


_KH_ES = ("kh no puede ser negativo; vale -0.1. Es la magnitud de la fuerza "
          "sísmica horizontal")


class TestTheWindowSaysThemInSpanish:

    def test_the_compute_box(self):
        import ogr_gui.main_window as mw
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
                w = _window(_negative_kh_project())
                w.act_compute()
        finally:
            mw.QMessageBox = saved
        assert len(said) == 1 and said[0].startswith(_KH_ES), said

    def test_the_api_still_answers_in_english(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        problems = check_analysis_settings(_negative_kh_project())
        assert [p.code for p in problems] == ["rule.seismic_kh_negative"]
        assert problems[0].startswith("kh must not be negative, got -0.1.")
