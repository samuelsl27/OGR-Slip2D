# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.352 (D335, sixth part; D341) — what the seepage solver, the transient
driver, the back analysis, the drawdown level sweep and the Hoek-Brown
calculator say carries stable codes, and the window says it in Spanish; a
transient whose initial state fails no longer raises inside its Qt slot.

The solver's ``notes["error"]``/``["warning"]``/``["mesh_warning"]`` and the
initial-state notes, the transient's warnings, the back analysis' and the
sweep's ``notes["error"]``, the runner's "Could not build the search for" and
the calculator's notes were English sentences, most with their values baked
in, shown through ``tr()`` -- which found nothing for those. Each is a code
now (``ogr_fem2d.messages``, ``ogr_slip2d.run_messages``,
``ogr_core.statistics.messages``, ``ogr_core.materials.messages``); a reason
that follows another (an initial state that failed because there is no
prescribed head) is nested with its own code.

D341: when the steady state a transient starts from cannot be solved, the
solver returns one result with no field and the reason in its notes, and the
window took the minimum of that empty field -- ``ValueError`` inside the
slot, and the reason reached nobody. It says the reason now.

The invariants:

* **the English is v0.1.351's, byte for byte** (``_V1351``: that version's
  expressions, read from its source and evaluated on the values below);
* every code is sampled and says itself in Spanish with its fields;
* **no sentence of these functions is built without its code** (AST
  census), and the two module constants carry theirs;
* **in the window, in Spanish**: Compute groundwater on a steady model with
  no prescribed head, and on a transient whose initial state has none
  (D341: it must not raise); the sweep's refusal box; the Interpret
  groundwater summary; the Hoek-Brown calculator;
* the API still reads English, and a note survives the pickle of a job.
"""
from __future__ import annotations

import ast
import pickle
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``{cat, code, args, english}``: the sentence v0.1.351 wrote. ``cat`` is
#: the catalogue; a nested value is ``{"$code", "$cat", "$args"}``, an uncoded
#: one ``{"$raw": text}``.
_V1351 = [{'cat': 'seepage',
  'code': 'seepage.mesh_flat',
  'english': 'the mesh has 3 flat element(s) (three collinear nodes): nodes '
             'under them do not count as boundary and the conductivity matrix '
             'is badly conditioned. Regenerate the mesh.',
  'args': {'n': 3}},
 {'cat': 'seepage',
  'code': 'seepage.empty_mesh',
  'english': 'empty mesh',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.empty_mesh',
  'english': 'empty mesh',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.no_dirichlet',
  'english': 'no Dirichlet (head) boundary condition: the problem is '
             'singular. Prescribe Total Head, Pressure Head or Zero Pressure '
             'somewhere on the boundary.',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.linear_failed',
  'english': 'linear solve failed',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.picard_linear_failed',
  'english': 'linear solve failed at Picard iteration 17',
  'args': {'it': 17}},
 {'cat': 'seepage',
  'code': 'seepage.final_failed',
  'english': 'final solve failed',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.face_unsettled',
  'english': 'the seepage face never settled: 2 boundary node(s) still want '
             "to switch between 'P = 0' and 'no flow' (1 were frozen by the "
             'switch budget of 6). The free surface this reports is not the '
             'converged one.',
  'args': {'unsettled': 2, 'frozen': 1, 'budget': 6}},
 {'cat': 'seepage',
  'code': 'seepage.picard_no_rescue',
  'english': 'Picard iteration did not converge in 200 steps (last change '
             '1.235e-02 m), and the rescue is switched off.',
  'args': {'steps': 200, 'change': 0.0123456}},
 {'cat': 'seepage',
  'code': 'seepage.picard_rescue_failed',
  'english': 'Picard iteration did not converge in 200 steps (last change '
             '1.235e-02 m), and neither did the rescue (Anderson '
             "acceleration, then continuation with Newton's method; last "
             'change 3.500e-04 m). A permeability function that drops many '
             'decades over a short suction range is the usual cause: check '
             'the curves of the materials near the water table.',
  'args': {'steps': 200, 'change': 0.0123456, 'rescue_change': 0.00035}},
 {'cat': 'seepage',
  'code': 'seepage.initial_failed',
  'english': 'initial steady state failed',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.initial_failed_why',
  'english': 'initial steady state failed: no Dirichlet (head) boundary '
             'condition: the problem is singular. Prescribe Total Head, '
             'Pressure Head or Zero Pressure somewhere on the boundary.',
  'args': {'why': {'$code': 'seepage.no_dirichlet',
                   '$cat': 'seepage',
                   '$args': {}}}},
 {'cat': 'seepage',
  'code': 'seepage.initial_failed_why',
  'english': "initial steady state failed: a plugin's own reason",
  'args': {'why': {'$raw': "a plugin's own reason"}}},
 {'cat': 'seepage',
  'code': 'seepage.no_time_step',
  'english': 'no time step computed',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.stage_steps',
  'english': 'stage 2: some time steps did not converge; try more time steps '
             'or more Picard iterations per step',
  'args': {'k': 2}},
 {'cat': 'seepage',
  'code': 'seepage.initial_not_converged',
  'english': 'the initial steady state did not converge',
  'args': {}},
 {'cat': 'seepage',
  'code': 'seepage.initial_not_converged_why',
  'english': 'the initial steady state did not converge: Picard iteration did '
             'not converge in 200 steps (last change 1.235e-02 m), and '
             'neither did the rescue (Anderson acceleration, then '
             "continuation with Newton's method; last change 3.500e-04 m). A "
             'permeability function that drops many decades over a short '
             'suction range is the usual cause: check the curves of the '
             'materials near the water table.',
  'args': {'why': {'$code': 'seepage.picard_rescue_failed',
                   '$cat': 'seepage',
                   '$args': {'steps': 200,
                             'change': 0.0123456,
                             'rescue_change': 0.00035}}}},
 {'cat': 'run',
  'code': 'run.transient_no_stages',
  'english': 'This project has no transient groundwater stages, so there is '
             'no factor-of-safety history to compute. Turn on Transient '
             'Groundwater and define the stages first.',
  'args': {}},
 {'cat': 'run',
  'code': 'run.transient_no_field',
  'english': 'The groundwater analysis produced no field: no Dirichlet (head) '
             'boundary condition: the problem is singular. Prescribe Total '
             'Head, Pressure Head or Zero Pressure somewhere on the boundary.',
  'args': {'why': {'$code': 'seepage.no_dirichlet',
                   '$cat': 'seepage',
                   '$args': {}}}},
 {'cat': 'run',
  'code': 'run.transient_initial_not_converged',
  'english': 'The initial steady state of the transient analysis did not '
             'converge, so every stage starts from an unconverged field (see '
             "each stage's initial-state warning).",
  'args': {}},
 {'cat': 'run',
  'code': 'run.transient_no_coupling',
  'english': 'No material takes its pore pressure from the finite-element '
             'seepage field, so the stage factors of safety would ignore the '
             'computed water pressures entirely.',
  'args': {}},
 {'cat': 'run',
  'code': 'run.back_only_for',
  'english': 'Back analysis is only available for bishop_simplified, '
             'janbu_simplified, janbu_corrected.',
  'args': {'methods': 'bishop_simplified, janbu_simplified, janbu_corrected'}},
 {'cat': 'run',
  'code': 'run.back_target_positive',
  'english': 'The target factor of safety must be positive.',
  'args': {}},
 {'cat': 'run',
  'code': 'run.back_search_failed',
  'english': 'search failed: no surface in the slope limits',
  'args': {'error': 'no surface in the slope limits'}},
 {'cat': 'run',
  'code': 'run.back_none',
  'english': 'No surface could be back-analysed. Check the target factor of '
             'safety and the search settings.',
  'args': {}},
 {'cat': 'run',
  'code': 'run.back_envelope',
  'english': 'The strength envelope depends on the normal stress, and on at '
             'least one slice the stress it is read at did not settle on the '
             'stress the method resolves at the target factor of safety; the '
             'surface was left out rather than back-analysed at a point the '
             'method does not use.',
  'args': {}},
 {'cat': 'run',
  'code': 'run.back_envelope_left_out',
  'english': '4 surface(s) were left out: The strength envelope depends on '
             'the normal stress, and on at least one slice the stress it is '
             'read at did not settle on the stress the method resolves at the '
             'target factor of safety; the surface was left out rather than '
             'back-analysed at a point the method does not use.',
  'args': {'n': 4}},
 {'cat': 'run',
  'code': 'run.back_composite_left_out',
  'english': '2 composite surface(s) were left out: back analysis is written '
             'in the circular form of the method, which does not hold on the '
             'straight stretches of a composite. Turn Composite Surfaces off '
             'to back-analyse this model, and read the result as being about '
             'circular surfaces only.',
  'args': {'n': 2}},
 {'cat': 'run',
  'code': 'run.search_not_built',
  'english': 'Could not build the search for: spencer, gle',
  'args': {'methods': 'spencer, gle'}},
 {'cat': 'run',
  'code': 'run.search_not_built',
  'english': 'Could not build the search for: bishop_simplified',
  'args': {'methods': 'bishop_simplified'}},
 {'cat': 'run',
  'code': 'run.search_not_built',
  'english': 'Could not build the search for: janbu_corrected',
  'args': {'methods': 'janbu_corrected'}},
 {'cat': 'run',
  'code': 'run.sweep_enable_drawdown',
  'english': 'Enable Rapid Drawdown analysis in Project Settings > '
             'Groundwater > Advanced first.',
  'args': {}},
 {'cat': 'run',
  'code': 'run.back_supports',
  'english': 'The back analysis supports bishop_simplified, janbu_simplified, '
             'janbu_corrected, not spencer.',
  'args': {'methods': 'bishop_simplified, janbu_simplified, janbu_corrected',
           'method': 'spencer'}},
 {'cat': 'run',
  'code': 'run.back_target_positive',
  'english': 'The target factor of safety must be positive.',
  'args': {}},
 {'cat': 'sweep',
  'code': 'sweep.no_method',
  'english': 'No analysis method selected.',
  'args': {}},
 {'cat': 'sweep',
  'code': 'sweep.needs_drawdown',
  'english': 'The drawdown level sweep needs a Rapid Drawdown analysis: '
             'enable it in Project Settings > Groundwater > Advanced.',
  'args': {}},
 {'cat': 'calc',
  'code': 'calc.d_clamped',
  'english': 'D = 2 makes mb undefined (28 − 14 D = 0); it has been clamped '
             'to 1.999.',
  'args': {}},
 {'cat': 'calc',
  'code': 'calc.gsi_clamped',
  'english': 'GSI was clamped to the range 0 to 100.',
  'args': {}}]

#: Codes born after v0.1.351, with the sentence of the version that added
#: them (same form as ``_V1351``).
_LATER = [
 # v0.1.362 (D367): the continuation stopped at a turn of its path that the
 # piecewise path cannot follow with this model's curves
 {'cat': 'seepage',
  'code': 'seepage.picard_rescue_piecewise_na',
  'english': 'Picard iteration did not converge in 200 steps (last change '
             '1.235e-02 m), and neither did the rescue (Anderson '
             "acceleration, then continuation with Newton's method; last "
             'change 3.500e-04 m). The continuation stopped where its path of '
             'solutions turns back; the road that follows the path across '
             'such turns works only when every material has a User Defined '
             'permeability curve, and this model has others.',
  'args': {'steps': 200, 'change': 0.0123456, 'rescue_change': 0.00035}}]


def _cat(name):
    if name == "seepage":
        from ogr_fem2d.messages import SEEPAGE_NOTES
        return SEEPAGE_NOTES
    if name == "run":
        from ogr_slip2d.run_messages import RUN_NOTES
        return RUN_NOTES
    if name == "sweep":
        from ogr_core.statistics.messages import SWEEP_NOTES
        return SWEEP_NOTES
    from ogr_core.materials.messages import CALCULATOR_NOTES
    return CALCULATOR_NOTES


_CATS = ("seepage", "run", "sweep", "calc")


def _resolve(v):
    from ogr_core.messages import as_nested, coded, nested
    if isinstance(v, dict) and "$raw" in v:
        return nested("", {}, v["$raw"])
    if isinstance(v, dict) and "$code" in v:
        return as_nested(coded(_cat(v["$cat"]), v["$code"],
                               **_resolve(v["$args"])))
    if isinstance(v, dict):
        return {k: _resolve(x) for k, x in v.items()}
    return v


def _message(case):
    from ogr_core.messages import coded
    return coded(_cat(case["cat"]), case["code"], **_resolve(case["args"]))


_F = string.Formatter()


def _fields(t):
    return sorted({f for _t, f, _s, _c in _F.parse(t) if f})


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
        for case in _V1351 + _LATER:
            assert _message(case) == case["english"], case["code"]

    def test_the_samples_cover_every_code(self):
        seen = {case["code"] for case in _V1351 + _LATER}
        every = set()
        for name in _CATS:
            every |= set(_cat(name))
        assert seen == every, every ^ seen

    def test_the_catalogues_do_not_collide(self):
        from ogr_gui.core_messages import _catalogue
        total = sum(len(_cat(name)) for name in _CATS)
        mine = set()
        for name in _CATS:
            mine |= set(_cat(name))
        assert len(mine) == total
        assert mine <= set(_catalogue())


class TestEveryCodeSaysItselfInSpanish:

    def test_the_entries_have_the_fields(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for name in _CATS:
            for code, spec in _cat(name).items():
                assert spec.english in es, (code, spec.english[:60])
                assert _fields(es[spec.english]) == _fields(spec.english), code
                assert es[spec.english] != spec.english, code

    def test_each_sample_renders_in_spanish(self):
        from ogr_gui.core_messages import note_text
        with _Spanish():
            for case in _V1351 + _LATER:
                said = note_text(_message(case))
                assert said and said != case["english"], case["code"]
                assert "{" not in said, (case["code"], said)

    def test_a_nested_reason_is_said_in_spanish_too(self):
        from ogr_fem2d import messages as M
        from ogr_core.messages import as_nested
        from ogr_gui.core_messages import note_text
        note = M.seepage_note(M.INITIAL_FAILED_WHY,
                              why=as_nested(M.seepage_note(M.NO_DIRICHLET)))
        with _Spanish():
            said = note_text(note)
        assert said.startswith("falló el estado permanente inicial: no hay "
                               "ninguna condición de contorno de altura"), said

    def test_the_fallbacks_go_through_tr(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        for key in ("Back analysis failed.", "sensitivity run failed",
                    "did not converge"):
            assert key in es, key
        src = (_ROOT / "ogr_gui" / "main_window.py").read_text(
            encoding="utf-8")
        flat = " ".join(src.split())
        assert '"Back analysis failed.")' not in flat.replace(
            'tr("Back analysis failed.")', "")
        assert 'tr("sensitivity run failed")' in flat
        assert '"warning", "did not converge")' not in flat
        assert 'note_text(res.notes.get("error") or tr("Back analysis ' \
            'failed."))' in flat


# ======================================================================
_CODED = {
    "ogr_fem2d/solvers/seepage.py": ("_note_degenerate", "solve",
                                     "solve_unsaturated", "solve_transient"),
    "ogr_slip2d/transient_stability.py": ("run_transient_stability",),
    "ogr_slip2d/back_analysis.py": ("run_back_analysis", "required_force"),
    "ogr_core/statistics/drawdown_sweep.py": ("run_drawdown_sweep",),
    "ogr_core/materials/parameter_calculator.py": ("calculate_hoek_brown",),
    "ogr_slip2d/analysis_runner.py": ("run_configured_drawdown_sweep",
                                      "run_configured_back_analysis",
                                      "run_configured_optimization"),
}


class TestNoSentenceWithoutItsCode:

    def test_census(self):
        found = []
        for rel, names in _CODED.items():
            src = (_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            # a module-level function first (``required_force`` is also a
            # property of the result), else the one method of that name
            top = {n.name: n for n in tree.body
                   if isinstance(n, ast.FunctionDef)}
            funcs = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.FunctionDef):
                    funcs.setdefault(n.name, []).append(n)
            for name in names:
                if name in top:
                    fn = top[name]
                else:
                    assert len(funcs.get(name, [])) == 1, (rel, name)
                    fn = funcs[name][0]
                # every docstring in it, a nested function's too
                docs = {d.body[0].value for d in ast.walk(fn)
                        if isinstance(d, (ast.FunctionDef, ast.ClassDef))
                        and d.body and isinstance(d.body[0], ast.Expr)
                        and isinstance(d.body[0].value, ast.Constant)}
                for n in ast.walk(fn):
                    if n in docs:
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

    def test_the_module_constants_carry_their_codes(self):
        from ogr_slip2d.back_analysis import ENVELOPE_NOT_SETTLED_NOTE
        from ogr_slip2d.transient_stability import (
            INITIAL_STATE_NOT_CONVERGED)
        assert INITIAL_STATE_NOT_CONVERGED.code == \
            "run.transient_initial_not_converged"
        assert ENVELOPE_NOT_SETTLED_NOTE.code == "run.back_envelope"

    def test_the_calculator_notes(self):
        from ogr_core.materials.parameter_calculator import (
            calculate_hoek_brown)
        r = calculate_hoek_brown(120.0, 10.0, 2.0)
        assert [n.code for n in r.notes] == ["calc.d_clamped",
                                             "calc.gsi_clamped"]


# ======================================================================
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


_W, _H = 20.0, 8.0


def _seepage_project(transient: bool):
    """A rectangle of one material on a fine-enough mesh, with heads on its
    two sides; ``transient`` adds two stages and an initial state with no
    prescribed head at all, which the steady solve it starts from cannot
    be solved with."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.hydraulic.hydraulic_properties import HydraulicProperties
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.geometry.regions import MaterialRegion
    from ogr_fem2d.mesh import generate_mesh
    from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(_W, 0), Vertex(_W, _H),
                              Vertex(0, _H)], closed=True)
    mesh = generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=2.0)
    p = Project()
    mat = Material(name="m", strength=MohrCoulomb(cohesion=10.0,
                                                  friction_angle=30.0))
    mat.id = "m"
    mat.hydraulic = HydraulicProperties(ks=1e-6)
    mat.pore_pressure = PorePressureType.FEM_SEEPAGE
    p.materials = [mat]
    p.fem_mesh = mesh
    bcs = SeepageBoundaryConditions()
    for nid in sorted(mesh.boundary_node_ids()):
        nd = mesh.nodes[nid]
        if abs(nd.x) < 1e-9:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 6.0)
        elif abs(nd.x - _W) < 1e-9:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 3.0)
    gw = p.settings.groundwater
    if transient:
        p.seepage_bcs = bcs
        gw.set_advanced_option("transient")
        gw.transient_stages = [{"time": 0.0, "label": "t = 0"},
                               {"time": 3600.0, "label": "1 h"}]
        gw.transient_initial_bcs = SeepageBoundaryConditions().to_dict()
    else:
        # no prescribed head anywhere: the steady problem is singular
        p.seepage_bcs = SeepageBoundaryConditions()
    return p


def _window(p):
    from ogr_gui.main_window import MainWindow
    _app()
    w = MainWindow()
    w.canvas.set_project(p)
    w.project = p
    said = []
    bar = w.statusBar()
    real = bar.showMessage

    def spy(text, *a):
        said.append(text)
        return real(text, *a)
    bar.showMessage = spy
    return w, said


_NO_HEAD_ES = "no hay ninguna condición de contorno de altura (Dirichlet)"


class TestTheWindowSaysThemInSpanish:

    def test_a_steady_model_with_no_prescribed_head(self):
        p = _seepage_project(transient=False)
        with _Spanish():
            w, said = _window(p)
            try:
                w._compute_groundwater()
            finally:
                w.close()
        assert said, "nothing on the status bar"
        assert said[-1].startswith("Análisis de filtración: " + _NO_HEAD_ES), \
            said[-1]

    def test_a_transient_whose_initial_state_fails(self):
        """D341: it raised ValueError (min of an empty field) in the slot."""
        p = _seepage_project(transient=True)
        with _Spanish():
            w, said = _window(p)
            try:
                w._compute_groundwater()
            finally:
                w.close()
        results = list(p.transient_results or [])
        assert len(results) == 1 and not results[0].pore_pressure
        assert results[0].notes["error"].code == "seepage.initial_failed_why"
        # the driver's warning, and the window's own line after it
        assert any(s.startswith(
            "El análisis de agua subterránea no dio ningún campo: falló el "
            "estado permanente inicial: " + _NO_HEAD_ES) for s in said), said
        assert said[-1].startswith(
            "Análisis de filtración: falló el estado permanente inicial: "
            + _NO_HEAD_ES), said[-1]

    def test_the_sweep_refusal_box(self):
        from ogr_core.project import Project
        from ogr_core.statistics.drawdown_sweep import run_drawdown_sweep
        import ogr_gui.main_window as mw
        result = run_drawdown_sweep(Project(), lambda mid: None, [])
        assert result.notes["error"] == "No analysis method selected."
        boxes = []
        real = mw.QMessageBox.warning
        mw.QMessageBox.warning = staticmethod(
            lambda parent, title, text, *a: boxes.append(text))
        try:
            with _Spanish():
                w, _said = _window(Project())
                try:
                    w._on_drawdown_sweep_done(result)
                finally:
                    w.close()
        finally:
            mw.QMessageBox.warning = real
        assert boxes == ["No hay ningún método de análisis seleccionado."], \
            boxes

    def test_the_interpret_groundwater_summary(self):
        from types import SimpleNamespace as NS

        from PySide6.QtWidgets import QLabel

        from ogr_fem2d import messages as M
        from ogr_fem2d.solvers import SeepageResult
        from ogr_gui.interpret_groundwater_window import (
            InterpretGroundwaterWindow)
        _app()
        r = SeepageResult()
        r.total_head = [5.0, 4.0]
        r.pore_pressure = [10.0, 0.0]
        r.converged = False
        r.notes["warning"] = M.seepage_note(M.STAGE_STEPS, k=1)
        r.notes["mesh_warning"] = M.seepage_note(M.MESH_FLAT, n=2)
        host = NS(result=r, status=QLabel())
        with _Spanish():
            InterpretGroundwaterWindow._summary(host)
        text = host.status.text()
        assert "etapa 1: algunos pasos de tiempo no convergieron" in text, text
        assert "la malla tiene 2 elemento(s) plano(s)" in text, text

    def test_the_hoek_brown_calculator(self):
        from ogr_gui.dialogs.parameter_calculator_dialog import (
            ParameterCalculatorDialog)
        _app()
        with _Spanish():
            dlg = ParameterCalculatorDialog()
            try:
                dlg.sp_d.setValue(2.0)
                dlg._recalculate()
                text = dlg.lbl_note.text()
            finally:
                dlg.close()
        assert text.startswith("Con D = 2, mb queda indefinido"), text


class TestTheApiReadsEnglish:

    def test_the_back_analysis_note(self):
        from ogr_core.project import Project
        from ogr_slip2d.back_analysis import run_back_analysis
        out = run_back_analysis(Project(), None, target_fos=0.0,
                                method_id="bishop_simplified")
        assert out.notes["error"] == (
            "The target factor of safety must be positive.")
        assert out.notes["error"].code == "run.back_target_positive"

    def test_a_note_survives_the_pickle_of_a_job(self):
        from ogr_fem2d import messages as M
        from ogr_core.messages import as_nested
        note = M.seepage_note(M.INITIAL_FAILED_WHY,
                              why=as_nested(M.seepage_note(M.NO_DIRICHLET)))
        back = pickle.loads(pickle.dumps(note))
        assert back == note and back.code == note.code
        assert back.args == note.args
