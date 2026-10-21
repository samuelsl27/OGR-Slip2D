# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.333 (D314) — the engine's per-surface messages carry a stable code.

Why a surface has no factor of safety (``LEMResult.error_message``) and why a
converged one is inadmissible (``admissibility_note``) reached the screen in
English. They were sentences with their values baked in by an f-string, so
the interface could neither translate them nor group them by condition. The
engine now writes each one through ``ogr_slip2d.messages``: a code, its
values, and the sentence it renders. The interface translates by code
(``ogr_gui.core_messages``).

The invariants:

* **the English does not move.** About ninety tests, the verification bank
  and the raw-data export (``"m_alpha" in note``) read those sentences. Every
  code's template, filled with a sample, is compared with the 0.1.332
  expression that wrote it, COPIED HERE LITERALLY: the reference is the old
  code, not what the new one prints;
* **every code has its Spanish**, with the same fields, and a sample that
  formats it. A code added without one fails here;
* **the engine writes its codes**: on real results (the nine methods on a
  symmetric mass, a rapid drawdown whose stage fails, the two screens, an
  arithmetic failure) the code's sentence IS the sentence the result
  carries;
* **no site writes a sentence without its code.** An AST census of
  ``ogr_slip2d`` refuses a literal ``error_message=`` or
  ``admissibility_note=``, an assignment to either outside ``set_error`` and
  ``set_note``, and a ``RapidDrawdownError`` without ``code=`` outside the
  run-level refusals (D335);
* **in Spanish the interface says them in Spanish**, and groups them by
  condition: three m-alpha rejections at different slice counts are one
  group (three before). Measured on the second worked example with Bishop
  and the reference grid: 49 groups by sentence, 3 by code. A message
  without a code is shown as written.
"""
from __future__ import annotations

import ast
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[1]


def _nested_malpha():
    from ogr_core.messages import nested
    return nested("lem.m_alpha_collapsed", {"value": 3.2e-07, "slice": 4},
                  "mα collapsed to 3.2e-07 at slice 4")


def _samples() -> dict:
    """``{code: (args, sentence the 0.1.332 code wrote with them)}``.

    Each right-hand side is the 0.1.332 expression, copied from the line
    that produced it, with the sample values in place of its variables."""
    import ogr_slip2d.messages as m
    from ogr_core.messages import nested

    exc = ZeroDivisionError("float division by zero")
    why = _nested_malpha()
    no_why = nested(m.NO_REASON_GIVEN, {}, "no reason given")
    note = nested(m.RELAXED_THRUST, {"method": "GLE"},
                  "GLE: no λ leaves the inter-slice thrust in net "
                  "compression; the answer is reported with the criterion "
                  "relaxed")
    stage = nested(m.DRAWDOWN_STAGE1_INADMISSIBLE, {"why": note},
                   f"Stage 1 (full reservoir): {note['text']}")
    m_alpha, index, new_fos = 1.234567e-07, 12, -18.9312
    residual, lam_lo, lam_width, iterations = 0.0123456, 0.4567891, 3.1e-9, 42
    display = "Corps of Engineers #1"
    passes, fos = 1, 0.874321
    return {
        m.NO_SHEAR_STRENGTH: ({}, (
            "Zero shear strength on the whole slip surface — "
            "factor of safety is zero")),
        m.NOT_CONVERGED: ({}, (
            "The factor of safety iteration did not converge within the "
            "maximum number of iterations")),
        m.ENVELOPE_NOT_CONVERGED: ({}, (
            "The strength envelope depends on the normal stress, and the "
            "stress it was read at did not settle on the stress the method "
            "resolved within the maximum number of passes")),
        m.NO_SLICES: ({}, "No slices"),
        m.ARITHMETIC_FAILURE: ({"error": str(exc)},
                               f"Arithmetic failure: {exc}"),
        m.M_ALPHA_COLLAPSED: ({"value": m_alpha, "slice": index},
                              f"mα collapsed to {m_alpha:.4g} at slice "
                              f"{index}"),
        m.N_ALPHA_COLLAPSED: ({"slice": index},
                              f"nα collapsed at slice {index}"),
        m.ZERO_DRIVING_MOMENT: ({}, "Zero driving moment — surface does not "
                                    "slide"),
        m.ZERO_DRIVING_FORCE: ({}, "Zero driving force — surface does not "
                                   "slide"),
        m.NON_PHYSICAL_FOS: ({}, "Non-physical factor of safety"),
        m.NON_PHYSICAL_FOS_ITERATION: (
            {"value": new_fos},
            f"Non-physical factor of safety {new_fos:.4g} " f"in iteration"),
        m.NON_FINITE_FOS: ({}, "Non-finite FoS"),
        m.NON_FINITE_FOS_ITERATION: ({}, "Non-finite FoS in iteration"),
        m.ACTIVE_SUPPORT_EXCEEDS_MOMENT: ({}, (
            "Active support force exceeds the driving moment; "
            "the factor of safety is undefined for this surface")),
        m.ACTIVE_SUPPORT_EXCEEDS_FORCE: ({}, (
            "Active support force exceeds the driving force; "
            "the factor of safety is undefined for this surface")),
        m.ALL_LAMBDA_DIVERGED: ({"method": "Spencer"},
                                "Spencer: all sampled λ diverged"),
        m.NO_LAMBDA_BRACKET: (
            {"method": "GLE", "residual": residual},
            "GLE: no λ-bracket; the nearest λ leaves "
            "F_f − F_m at %.3g" % residual),
        m.RELAXED_THRUST: (
            {"method": "Spencer"},
            "Spencer: no λ leaves the inter-slice thrust in net compression; "
            "the answer is reported with the criterion relaxed"),
        m.DIVERGENT_AT_FINAL_LAMBDA: ({"method": "GLE"},
                                      "GLE: divergent at final λ"),
        m.LAMBDA_NOT_CLOSED: (
            {"method": "Spencer", "residual": residual, "lam": lam_lo,
             "width": lam_width, "iterations": iterations},
            "Spencer: the λ bracket did not close; "
            "F_f − F_m is %.3g at λ = %.6g, with the bracket "
            "at %.3g after %d iterations"
            % (residual, lam_lo, lam_width, iterations)),
        m.FORCE_BALANCE_DIVERGED: (
            {"method": display}, f"{display}: force balance diverged"),
        m.NO_FORCE_BRACKET: (
            {"method": display},
            f"{display}: no F-bracket; reporting "
            f"the sampled F of smallest residual"),
        m.SCREEN_TENSILE_STRESS: (
            {"count": 3}, f"tensile stress on {3} slice base(s) "
                          f"(error -120)"),
        m.SCREEN_M_ALPHA: (
            {"limit": 0.2, "count": 2}, f"m_alpha < {0.2} on {2} slice(s)"),
        m.SCREEN_ERROR: (
            {"error_type": type(exc).__name__, "error": str(exc)},
            f"admissibility checks could not be evaluated "
            f"({type(exc).__name__}: {exc})"),
        m.DRAWDOWN_CURVED_ENVELOPE: (
            {"material": "Clay", "model": "hoek_brown"},
            f"Rapid drawdown needs a linear effective envelope; material "
            f"'{'Clay'}' uses '{'hoek_brown'}'. A curved "
            f"envelope cannot be carried through a procedure that rewrites "
            f"c and phi on every slice."),
        m.DRAWDOWN_NO_ENVELOPE: (
            {"material": "Clay"},
            f"Material '{'Clay'}' is marked undrained "
            f"but has no R or Kc=1 envelope defined."),
        m.DRAWDOWN_STAGE1_NORMALS: (
            {"method": "spencer", "count": 3, "slices": 25},
            f"Method '{'spencer'}' reported "
            f"{3} base normal forces for {25} "
            f"slices, so the stage-1 consolidation state cannot be "
            f"recovered. Without it the procedure would apply no undrained "
            f"strength at all and report the drained factor of safety."),
        m.DRAWDOWN_CAP_NORMALS: (
            {"method": "spencer", "count": 3, "slices": 25},
            f"Method '{'spencer'}' reported "
            f"{3} base normal forces for "
            f"{25} slices, so the drained cap cannot be "
            f"evaluated on all of them."),
        m.DRAWDOWN_UNKNOWN_PROCEDURE: (
            {"procedure": "nope"}, f"Unknown drawdown procedure: {'nope'}"),
        m.DRAWDOWN_UNSLICEABLE_INITIAL: (
            {}, "The slip surface could not be sliced at the initial level"),
        m.DRAWDOWN_UNSLICEABLE_DRAWN_DOWN: (
            {}, "The slip surface could not be sliced at "
                "the drawn-down level"),
        m.DRAWDOWN_STAGE1_UNUSABLE: (
            {}, "Stage 1 did not produce a usable factor of safety"),
        m.DRAWDOWN_STAGE1_UNSTABLE: (
            {"factor": fos},
            f"Stage 1 factor of safety is {fos:.3f} < 1: the slope is "
            f"not stable with the reservoir full, and the rapid-drawdown "
            f"procedure does not apply to it"),
        m.DRAWDOWN_STAGE_FAILED: (
            {"stage": 2, "why": why},
            f"Stage {2}{''} produced no factor of safety: {why['text']}"),
        m.DRAWDOWN_STAGE_FAILED_CAP: (
            {"stage": 3, "cap_pass": passes + 1, "why": no_why},
            f"Stage {3}{f' (drained cap, pass {passes + 1})'} produced no "
            f"factor of safety: {'no reason given'}"),
        m.DRAWDOWN_STAGE_UNCONVERGED: (
            {"stage": 1, "factor": 5.0, "why": why},
            f"Stage {1} returned an unconverged factor of safety "
            f"(F = {5.0:.3f}, not a solution): {why['text']}"),
        m.DRAWDOWN_STAGE1_INADMISSIBLE: (
            {"why": note}, f"Stage 1 (full reservoir): {note['text']}"),
        m.DECLARED_INADMISSIBLE: (
            {}, "declared inadmissible by its own method"),
        m.NO_REASON_GIVEN: ({}, "no reason given"),
        m.JOIN: (
            {"first": stage, "second": why},
            f"{stage['text']}; {why['text']}"),
    }


def _fields(template):
    return sorted(f for _t, f, _s, _c in string.Formatter().parse(template)
                  if f)


# ======================================================================
class TestTheCatalogue:

    def test_every_code_has_a_sample(self):
        from ogr_slip2d.messages import MESSAGES
        missing = sorted(set(MESSAGES) - set(_samples()))
        assert missing == [], missing

    def test_the_english_is_the_sentence_written_before(self):
        from ogr_slip2d.messages import text
        wrong = []
        for code, (args, old) in _samples().items():
            new = text(code, **args)
            if new != old:
                wrong.append((code, new, old))
        assert wrong == [], wrong

    def test_every_code_has_its_spanish_with_the_same_fields(self):
        """A template with no words (the "first; second" that joins two
        notes) has nothing to translate, and the dictionary refuses an entry
        identical to its key (``test_i18n_coverage_v141``)."""
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.messages import MESSAGES
        es = _DICTS["es"]
        bad = []
        for code, spec in MESSAGES.items():
            words = "".join(t for t, _f, _s, _c
                            in string.Formatter().parse(spec.english))
            if not any(ch.isalpha() for ch in words):
                continue
            if spec.english not in es:
                bad.append(("no Spanish", code))
            elif _fields(es[spec.english]) != _fields(spec.english):
                bad.append(("fields", code))
        assert bad == [], bad

    def test_every_spanish_template_formats_its_sample(self):
        from ogr_gui import core_messages
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            for code, (args, old) in _samples().items():
                said = core_messages.text(code, args, old)
                # a template that does not format falls back on the English
                assert said != old or code == "join", (code, said)
        finally:
            set_language(before)

    def test_the_codes_are_not_the_census_reasons(self):
        """Finer on purpose: ``REASON_*`` groups D56's census and the
        verification bank counts it, so the two sets must not be confused."""
        from ogr_slip2d.messages import MESSAGES
        from ogr_slip2d.methods.base import ALL_REASONS, ALL_SCREENS
        assert not (set(MESSAGES) & (ALL_REASONS | ALL_SCREENS))


# ======================================================================
def _assert_coded(res, where):
    """The sentence a result carries is the sentence of its code."""
    from ogr_slip2d.messages import MESSAGES, text
    seen = 0
    for sentence, code, args in (
            (res.error_message, res.message_code, res.message_args),
            (res.admissibility_note, res.note_code, res.note_args)):
        if not sentence:
            continue
        assert code in MESSAGES, (where, code, sentence)
        assert text(code, **args) == sentence, (where, code, sentence)
        seen += 1
    return seen


class TestTheEngineWritesItsCodes:

    def test_the_nine_methods_on_a_symmetric_mass(self):
        import test_no_number_v1152 as nn
        seen = 0
        for mid, res in nn._symmetric_results().items():
            assert res is not None, mid
            seen += _assert_coded(res, mid)
        assert seen >= 9, seen

    def test_a_drawdown_stage_failure_nests_its_method_s_reason(self):
        import test_drawdown_stage_failure_v1211 as dd
        from ogr_slip2d.messages import (DRAWDOWN_STAGE_FAILED,
                                         DRAWDOWN_STAGE_FAILED_CAP)
        cap = dd._wrapped(3)
        assert _assert_coded(cap, "cap") == 1
        assert cap.message_code == DRAWDOWN_STAGE_FAILED_CAP
        assert cap.message_args["cap_pass"] == 1
        # the inner pass wrote "synthetic" with no code: it travels as text
        assert cap.message_args["why"]["text"] == "synthetic"
        one = dd._wrapped(1)
        assert one.message_code == DRAWDOWN_STAGE_FAILED
        assert _assert_coded(one, "stage 1") == 1

    def test_the_two_screens(self):
        import test_tensile_export_code_v1192 as tx
        from ogr_slip2d.messages import SCREEN_M_ALPHA, SCREEN_TENSILE_STRESS
        t = tx._tension_rejected()
        assert t.note_code == SCREEN_TENSILE_STRESS
        assert _assert_coded(t, "tension") == 1
        m = tx._m_alpha_rejected()
        assert m.note_code == SCREEN_M_ALPHA
        assert _assert_coded(m, "m-alpha") == 1
        assert m.note_args["count"] >= 1

    def test_a_screen_that_raises(self):
        import test_screen_error_v1211 as se
        from ogr_slip2d.checks import screen_verdict
        from ogr_slip2d.messages import SCREEN_ERROR, text
        v = screen_verdict(se._result(exc=RuntimeError("boom")),
                           m_alpha=True)
        assert not v.ok and v.code == SCREEN_ERROR
        assert v.note == text(v.code, **v.args)
        assert v.args == {"error_type": "RuntimeError", "error": "boom"}

    def test_an_arithmetic_failure(self):
        import test_robustez_sin_resistencia_v199 as ar
        from ogr_slip2d.messages import ARITHMETIC_FAILURE
        search = ar._search(ar._ExplodingMethod(),
                            grid_x=ar.TestSearchSurvives._GRID_X,
                            grid_y=ar.TestSearchSurvives._GRID_Y,
                            grid_nx=1, grid_ny=1, radius_increment=1)
        result = search.run(ar._two_layer_slope())
        blamed = [e for e in result.evaluations
                  if e.message_code == ARITHMETIC_FAILURE]
        assert blamed
        for e in blamed:
            _assert_coded(e, "arithmetic")

    def test_the_codes_travel_in_to_dict_and_the_api(self):
        import json
        import test_tensile_export_code_v1192 as tx
        from ogr_api.results import lem_summary
        res = tx._m_alpha_rejected()
        d = json.loads(json.dumps(res.to_dict(), allow_nan=False))
        assert d["note_code"] == res.note_code and d["note_args"]
        s = lem_summary(res)
        assert s["note_code"] == res.note_code
        assert "message_code" not in s     # it did not fail: nothing added


# ======================================================================
def _calls_and_assigns():
    """Every engine site that names one of the two sentences."""
    out = []
    for path in sorted((ROOT / "ogr_slip2d").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        out.append((path.relative_to(ROOT).as_posix(), tree, parents))
    return out


def _function_of(node, parents):
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return None


def _has_words(node) -> bool:
    """Whether an expression contains a sentence: a non-empty string
    literal or an f-string."""
    for n in ast.walk(node):
        if isinstance(n, ast.JoinedStr):
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                and n.value.strip():
            return True
    return False


_SENTENCES = ("error_message", "admissibility_note")
#: The refusals that are not about one surface, raised before a search runs
#: or for the whole run. They went to D335, and since v0.1.350 they carry
#: their codes too: the exception is empty.
_RUN_LEVEL_REFUSALS: set = set()


class TestNoSiteWritesASentenceWithoutItsCode:

    def test_no_literal_sentence_in_a_call(self):
        bad = []
        for rel, tree, _parents in _calls_and_assigns():
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for kw in node.keywords:
                    if kw.arg in _SENTENCES and _has_words(kw.value):
                        bad.append((rel, node.lineno, kw.arg))
        assert bad == [], bad

    def test_no_assignment_outside_set_error_and_set_note(self):
        bad = []
        for rel, tree, parents in _calls_and_assigns():
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AugAssign)):
                    continue
                targets = (node.targets if isinstance(node, ast.Assign)
                           else [node.target])
                for t in targets:
                    if not (isinstance(t, ast.Attribute)
                            and t.attr in _SENTENCES):
                        continue
                    if (isinstance(node.value, ast.Constant)
                            and node.value.value == ""):
                        continue          # __post_init__ normalising None
                    if _function_of(node, parents) in ("set_error",
                                                       "set_note"):
                        continue
                    bad.append((rel, node.lineno, t.attr))
        assert bad == [], bad

    def test_every_drawdown_refusal_carries_its_code(self):
        bad, seen = [], 0
        for rel, tree, parents in _calls_and_assigns():
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "RapidDrawdownError"):
                    continue
                seen += 1
                if any(kw.arg == "code" for kw in node.keywords):
                    continue
                if (rel, _function_of(node, parents)) in _RUN_LEVEL_REFUSALS:
                    continue
                bad.append((rel, node.lineno))
        assert seen >= 3, seen
        assert bad == [], bad

    def test_the_census_sees_the_sites(self):
        """Control: the census must find what it looks for, or its silence
        means nothing. ``failure`` and ``inadmissible`` are the doors."""
        calls = 0
        for _rel, tree, _parents in _calls_and_assigns():
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("failure", "inadmissible")):
                    calls += 1
        assert calls >= 40, calls


# ======================================================================
try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")
        return self

    def __exit__(self, *exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)
        return False


def _screened(count):
    """A converged result the m-alpha screen rejected on ``count`` slices."""
    from ogr_slip2d.messages import SCREEN_M_ALPHA
    from ogr_slip2d.methods.base import SCREEN_M_ALPHA as SCREEN, LEMResult
    res = LEMResult(fos=1.4, converged=True, iterations=3,
                    method_id="bishop_simplified", surface=None, slices=[],
                    admissible=False, admissibility_reason=SCREEN)
    res.set_note(SCREEN_M_ALPHA, limit=0.2, count=count)
    return res


@_requires_qt
class TestTheInterfaceSaysThemInSpanish:

    def test_one_condition_is_one_group(self):
        from ogr_gui.interpret_window import InterpretWindow
        with _Spanish():
            labels = {InterpretWindow.invalid_reason(_screened(n))
                      for n in (1, 2, 3)}
        assert labels == {"m_alpha < 0.2 en … dovela(s)"}, labels

    def test_each_surface_keeps_its_own_sentence(self):
        from ogr_gui.interpret_window import InterpretWindow
        with _Spanish():
            said = InterpretWindow.invalid_text(_screened(2))
        assert said == "m_alpha < 0.2 en 2 dovela(s)", said

    def test_a_failure_and_its_values(self):
        from ogr_gui.core_messages import invalid_text
        from ogr_slip2d.messages import M_ALPHA_COLLAPSED, failure
        from ogr_slip2d.methods.base import (REASON_M_ALPHA_COLLAPSED,
                                             LEMResult)
        res = LEMResult(fos=None, converged=False, iterations=1,
                        method_id="bishop_simplified", surface=None,
                        slices=[], reason=REASON_M_ALPHA_COLLAPSED,
                        **failure(M_ALPHA_COLLAPSED, value=3.2e-07, slice=4))
        with _Spanish():
            said = invalid_text(res)
        assert said == "mα cayó a 3.2e-07 en la dovela 4", said
        # and in English, the sentence as the engine wrote it
        assert invalid_text(res) == res.error_message

    def test_a_stage_failure_is_spanish_at_both_levels(self):
        import test_drawdown_stage_failure_v1211 as dd
        from ogr_gui.core_messages import invalid_text
        from ogr_slip2d.messages import M_ALPHA_COLLAPSED, failure
        from ogr_slip2d.methods.base import LEMResult
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod

        class _FailsCoded(BishopSimplified):
            calls = 0

            def compute_fos(self, project, surface, slices):
                self.calls += 1
                if self.calls == 2:
                    return LEMResult(
                        fos=None, converged=False, iterations=0,
                        method_id=self.METHOD_ID, surface=surface,
                        slices=slices, reason="m_alpha_collapsed",
                        **failure(M_ALPHA_COLLAPSED, value=1e-07, slice=9))
                return super().compute_fos(project, surface, slices)

        p, c, sl = dd._fixture()
        res = MultiStageDrawdownMethod(_FailsCoded(), dd.DW,
                                       num_slices=dd.N_SLICES
                                       ).compute_fos(p, c, sl)
        with _Spanish():
            said = invalid_text(res)
        assert said == ("La etapa 2 no dio factor de seguridad: "
                        "mα cayó a 1e-07 en la dovela 9"), said

    def test_a_message_without_a_code_is_shown_as_written(self):
        from ogr_gui.core_messages import invalid_text
        from ogr_slip2d.methods.base import LEMResult
        res = LEMResult(fos=None, converged=False, iterations=0,
                        method_id="plugin", surface=None, slices=[],
                        error_message="a plugin's own words",
                        reason="non_physical_fos")
        with _Spanish():
            assert invalid_text(res) == "a plugin's own words"

    def test_the_canvas_tooltip_is_the_surface_s_own(self):
        """The purple surfaces of one error code: each tooltip is that
        surface's reason, in Spanish, not the label of the group."""
        from types import SimpleNamespace
        from ogr_gui.canvas.canvas_view import CanvasView
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d.surface import SlipCircle
        from PySide6.QtWidgets import QApplication, QGraphicsScene
        from ogr_core.project import Project
        QApplication.instance() or QApplication([])
        evs = []
        for n in (1, 2):
            r = _screened(n)
            r.surface = SlipCircle(centre_x=0.0, centre_y=10.0, radius=10.0)
            r.surface.x_left, r.surface.x_right = -5.0, 5.0
            evs.append(r)
        with _Spanish():
            view = CanvasView(Project("D314"))
            try:
                scene = QGraphicsScene()
                group = InterpretWindow.invalid_reason(evs[0])
                view._draw_invalid_surfaces(
                    scene, SimpleNamespace(evaluations=evs), group,
                    InterpretWindow.invalid_reason)
                tips = sorted(it.toolTip() for it in scene.items()
                              if it.toolTip())
            finally:
                view.deleteLater()
        assert tips == ["m_alpha < 0.2 en 1 dovela(s)",
                        "m_alpha < 0.2 en 2 dovela(s)"], tips
