# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A placed support that contributes nothing may not vanish without saying so.

Defect D62, opened on 2026-08-31 while closing D40 and still open at
0.1.154. ``compute_support_effects`` had five ways to leave a support out
of the equilibrium equations and not one of them left a trace. (v0.1.161
added a sixth, ``not_priceable``, closing the exception silence this file
diagnosed and did not fix; see ``TestTheSwallowedException`` below and
``tests/test_support_failure_v1161.py``.) The
invariant this file protects is not a number — it is that the analysis
NAMES what it left out.

Why that is worth a test file of its own: a reinforcement dropped in
silence lowers no number and raises none. What comes out is the factor of
safety of the model WITHOUT that support, which is conservative,
plausible, and indistinguishable from a correct answer. No existing test
could fail, and no comparison against the verification bank could move,
which is exactly why the defect survived from August.

The anchors here are identities, never captured values:

  * each of the five reasons is triggered by a model built to trigger
    that one and no other, and the assertion is on the reason list being
    EXACTLY one pair — a note that fires for the right count by the wrong
    route would pass a looser check;
  * the note is reporting only, so a project with a silent support gives
    the same factor of safety, digit for digit, as the same project with
    that support deleted. That identity is the proof the note describes a
    real zero and adds no term to any equation;
  * asking for the reasons does not change what the function returns:
    ``reasons=None`` and ``reasons=[]`` yield the same effects.

Assertions match on SUBSTRINGS, never on whole sentences, so the wording
stays editable — the rule ``test_support_reversed_v1138.py`` set for the
D40 note.

One test deliberately builds a slice list the real slicer cannot produce.
It is marked as such where it appears: reason ``no_slice`` is unreachable
through any model, because ``_slip_polyline`` is drawn from the same
slice list that is then searched for the index. The guard is real and
kept, so it is pinned here rather than left to rot untested.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

from test_supports_all_methods_v164 import (  # noqa: E402
    _circle, _fos, _nail, _project,
)

# The face runs (30, 0) → (50, 12) and the fixture circle cuts the ground
# at x = 40.2 and x = 52.3, so a horizontal support at y = 8 spanning
# 43.5 → 54.0 crosses it once, cleanly. Every "it crosses but ..." model
# below reuses that axis and changes only the property set, so the reason
# under test is the only thing that differs from the contributing case.
_ACROSS = ((43.5, 8.0), (54.0, 8.0))
_NOWHERE_NEAR = ((2.0, 1.0), (12.0, 1.0))


def _reasons(project, slices=None):
    """The ``(support id, reason)`` pairs for the fixture circle."""
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects

    if slices is None:
        slices = slice_surface(project, _circle(), num_slices=25)
        assert slices is not None
    out: list = []
    compute_support_effects(project, _circle(), slices, reasons=out)
    return out


def _notes(project, result):
    from ogr_slip2d.support_integration import uncontributing_support_notes
    return uncontributing_support_notes(project, result)


def _result(project):
    """A LEMResult on the fixture circle, from the real solver."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    return _fos(BishopSimplified, project)


def _model(types, supports):
    """The fixture slope carrying an arbitrary set of support types.

    ``_project`` hard-codes a single ``SoilNail`` set, and three of the
    five reasons need a different type to be reachable at all, so the
    geometry is reused and only the supports are replaced.
    """
    p = _project(_nail())
    p.support_types = list(types)
    p.supports = list(supports)
    return p


def _instance(type_id, ends, **kw):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    head, tail = ends
    return SupportInstance(
        type_id=type_id, head=Vertex(*head), tail=Vertex(*tail),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP, **kw)


def _nail_type():
    from ogr_core.support import SoilNail
    return SoilNail(tensile_capacity=30, plate_capacity=20,
                    bond_strength=8, out_of_plane_spacing=3.0)


# ======================================================================
class TestEachReasonFiresOnItsOwn:
    """Part 1 — the closure criterion of D62, one model per reason.

    Each asserts the WHOLE reason list, so a model that triggers its
    reason by way of another would fail rather than pass quietly.
    """

    def test_a_support_that_never_reaches_the_surface(self):
        from ogr_slip2d.support_integration import SUPPORT_NO_CROSSING

        p = _model([_nail_type()], [_instance("soil_nail", _NOWHERE_NEAR)])
        assert _reasons(p) == [(p.supports[0].id, SUPPORT_NO_CROSSING)]

    def test_a_support_whose_class_this_build_does_not_have(self):
        """Since D66 (v0.1.149) this one never enters the loop at all:
        ``support_type_pairs`` drops it. The silence is the same.
        """
        from ogr_slip2d.support_integration import SUPPORT_UNKNOWN_TYPE

        p = _model([_nail_type()],
                   [_instance("no_such_support_type", _ACROSS)])
        assert _reasons(p) == [(p.supports[0].id, SUPPORT_UNKNOWN_TYPE)]

    def test_a_level_support_whose_type_measures_from_the_crest(self):
        from ogr_core.support import PileMicropile
        from ogr_slip2d.support_integration import SUPPORT_NO_CREST

        # Ito-Matsui mode is what turns MEASURED_FROM_TOP on for a pile;
        # the default shear mode does not, so this pins the mode too.
        p = _model([PileMicropile(failure_mode="ito_matsui")],
                   [_instance("pile_micropile", _ACROSS)])
        assert _reasons(p) == [(p.supports[0].id, SUPPORT_NO_CREST)]

    def test_a_support_that_develops_no_capacity_where_it_crosses(self):
        from ogr_core.support import UserDefined
        from ogr_slip2d.support_integration import SUPPORT_NO_CAPACITY

        # A single point at zero: the type is well formed and its
        # capacity really is nothing, which is a legal, if pointless,
        # design — the reason exists to say so, not to refuse it.
        p = _model([UserDefined(points=[(0.0, 0.0)],
                                out_of_plane_spacing=1.0)],
                   [_instance("user_defined", _ACROSS)])
        assert _reasons(p) == [(p.supports[0].id, SUPPORT_NO_CAPACITY)]

    def test_a_crossing_that_falls_in_no_slice(self):
        """NO model reaches this: ``_slip_polyline`` is built from the
        same slice list the index search then scans, and the slicer
        refuses any interval of non-positive width, so the slices are
        contiguous and monotonic in x. The list below is holed BY HAND to
        pin a guard that is real and would otherwise go untested.
        """
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import SUPPORT_NO_SLICE

        p = _model([_nail_type()], [])
        full = slice_surface(p, _circle(), num_slices=25)
        assert full is not None
        holed = SimpleNamespace(slices=full.slices[:6] + full.slices[14:])
        x_gap = 0.5 * (full.slices[5].base_x_right
                       + full.slices[14].base_x_left)
        p.supports = [_instance("soil_nail", ((x_gap, 0.0), (x_gap, 20.0)))]
        assert _reasons(p, holed) == [(p.supports[0].id, SUPPORT_NO_SLICE)]


# ======================================================================
class TestItStaysQuietWhenItShould:
    """A note that fires on everything is noise, so silence is part of
    the invariant — the doctrine ``test_grid_edge_note_v1102.py`` set.
    """

    def test_a_support_that_contributes_says_nothing(self):
        p = _project(_nail())
        assert _reasons(p) == []
        assert _notes(p, _result(p)) == []

    def test_a_project_with_no_supports_says_nothing(self):
        p = _project()
        assert _notes(p, _result(p)) == []

    def test_a_result_with_no_slices_says_nothing(self):
        p = _model([_nail_type()], [_instance("soil_nail", _NOWHERE_NEAR)])
        assert _notes(p, SimpleNamespace(surface=_circle(),
                                         slices=None)) == []
        assert _notes(p, SimpleNamespace(surface=None, slices=None)) == []


# ======================================================================
class TestTheSentenceItWrites:
    """One aggregated line, and it counts what it says it counts."""

    def test_it_names_the_count_and_the_reason(self):
        p = _model([_nail_type()],
                   [_instance("soil_nail", _ACROSS),
                    _instance("soil_nail", _NOWHERE_NEAR)])
        notes = _notes(p, _result(p))
        assert len(notes) == 1, notes
        assert "1 of the 2 supports placed" in notes[0], notes[0]
        assert "do not cross it" in notes[0] or \
               "does not cross it" in notes[0], notes[0]

    def test_two_reasons_are_one_line_not_two(self):
        """The aggregation IS the threshold D62 asked for: a line per
        support would be the wall of warnings the defect warned about.
        """
        from ogr_core.support import UserDefined

        p = _model([_nail_type(),
                    UserDefined(points=[(0.0, 0.0)],
                                out_of_plane_spacing=1.0)],
                   [_instance("soil_nail", _ACROSS),
                    _instance("soil_nail", _NOWHERE_NEAR),
                    _instance("user_defined", _ACROSS)])
        notes = _notes(p, _result(p))
        assert len(notes) == 1, notes
        assert "2 of the 3 supports placed" in notes[0], notes[0]
        assert "develops no capacity" in notes[0], notes[0]
        assert "does not cross it" in notes[0], notes[0]

    def test_when_none_of_them_contributes_it_says_so_differently(self):
        """The case that actually misleads: the run reports the
        unreinforced slope while the canvas shows reinforcement.
        """
        p = _model([_nail_type()],
                   [_instance("soil_nail", _NOWHERE_NEAR),
                    _instance("soil_nail", ((2.0, 2.0), (12.0, 2.0)))])
        note = _notes(p, _result(p))[0]
        assert "None of the 2 supports placed" in note, note
        assert "no reinforcement at all" in note, note

    def test_a_lone_support_is_not_described_as_a_plural(self):
        p = _model([_nail_type()], [_instance("soil_nail", _NOWHERE_NEAR)])
        note = _notes(p, _result(p))[0]
        assert "The only support placed" in note, note
        assert "the 1 supports" not in note, note


# ======================================================================
class TestItReachesTheWarningsOfAFullRun:
    """The channel the verification bank reads as ``avisos``."""

    def test_the_note_arrives_prefixed_with_its_method(self):
        from ogr_slip2d.analysis_runner import run_analysis

        p = _project(_nail(head=(2.0, 1.0), tail=(12.0, 1.0)))
        out = run_analysis(p, ["bishop_simplified"])
        hits = [w for w in out.warnings
                if "no force on the reported surface" in w]
        assert hits, out.warnings
        assert hits[0].startswith("bishop_simplified: "), hits[0]


# ======================================================================
class TestNothingMoves:
    """Rule 7 in reverse: this control must NOT move the number.

    Both anchors are identities computed in the test, not values captured
    from a previous run — a snapshot here would enshrine whatever the
    code does today, which is what rule 1 forbids.
    """

    def test_a_silent_support_prices_exactly_as_no_support_at_all(self):
        """The numerical proof that the note describes a REAL zero: if
        the ignored support contributed anything, these two would differ.
        """
        silent = _model([_nail_type()],
                        [_instance("soil_nail", _NOWHERE_NEAR)])
        deleted = _model([_nail_type()], [])
        assert _result(silent).fos == _result(deleted).fos

    def test_asking_for_the_reasons_changes_no_effect(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import compute_support_effects

        p = _project(_nail())
        sl = slice_surface(p, _circle(), num_slices=25)
        quiet = compute_support_effects(p, _circle(), sl)
        asked = compute_support_effects(p, _circle(), sl, reasons=[])
        assert len(quiet) == len(asked) == 1
        assert quiet[0].force_magnitude == asked[0].force_magnitude
        assert quiet[0].force_angle_rad == asked[0].force_angle_rad

    def test_asking_twice_does_not_double_count(self):
        """Rule 5: nothing accumulates between calls."""
        p = _model([_nail_type()], [_instance("soil_nail", _NOWHERE_NEAR)])
        assert len(_reasons(p)) == len(_reasons(p)) == 1


# ======================================================================
class TestItCannotBeMistakenForTheD40Note:
    """The bank decides whether D40 still holds by SUBSTRING.

    ``_tools/verificar_cierres.py`` accepts an aviso as the D40 note when
    it contains "stable" and "head" at once. A D62 note carrying both
    would turn a green closure into RE-ENUNCIADO with nothing in the
    engine having changed, so the two channels are kept distinguishable
    here rather than in a document nobody re-reads. "unstable" and
    "ahead" are banned too: the bank's test is a plain substring, so they
    would match just as well.
    """

    def _every_note(self):
        from ogr_core.support import UserDefined

        out = []
        for types, sups in (
            ([_nail_type()], [_instance("soil_nail", _NOWHERE_NEAR)]),
            ([_nail_type()], [_instance("soil_nail", _ACROSS),
                              _instance("soil_nail", _NOWHERE_NEAR)]),
            ([_nail_type()], [_instance("no_such_support_type", _ACROSS)]),
            ([UserDefined(points=[(0.0, 0.0)], out_of_plane_spacing=1.0)],
             [_instance("user_defined", _ACROSS)]),
        ):
            p = _model(types, sups)
            out.extend(_notes(p, _result(p)))
        assert len(out) == 4, out
        return out

    def test_no_note_carries_the_pair_the_bank_reserves_for_d40(self):
        for note in self._every_note():
            assert not ("stable" in note and "head" in note), note

    def test_no_note_carries_the_other_two_reserved_phrases(self):
        for note in self._every_note():
            assert "edge of the search grid" not in note, note
            assert "path_optimize" not in note, note

    def test_the_d40_note_still_carries_both_so_the_two_stay_apart(self):
        """The converse tripwire: if D40's wording ever lost the pair,
        the bank would stop recognising it and this file would be the
        only place that noticed.
        """
        from ogr_slip2d.support_integration import reversed_support_notes

        p = _project(_nail(head=(54.0, 8.0), tail=(43.5, 8.0)))
        notes = reversed_support_notes(p, _result(p))
        assert notes, "the reversed bolt stopped being reported"
        assert "stable" in notes[0] and "head" in notes[0], notes[0]


# ======================================================================
class TestTheSwallowedException:
    """The sixth silence, and the widest — closed in v0.1.161 (D94).

    This class used to pin the defect rather than the invariant.
    ``resolve_support_terms`` answered ANY exception with an empty set of
    terms, so every support disappeared at once and the surface came back
    priced unreinforced; the three tests here asserted exactly that, with
    a docstring saying "diagnosed here, not fixed: narrowing that
    ``except`` is a separate defect and D62 may not move a number".

    That separate defect is D94 and it is fixed, so what is pinned here is
    now the other half of the same rule: a support that cannot be priced
    is answered, the others still count, and anything that is NOT a
    modelling refusal goes on raising. The plugin below therefore raises
    ``SupportEvaluationError`` where it used to raise ``RuntimeError``,
    and the ``RuntimeError`` case is kept as the test that the handler
    really is narrow.

    The arithmetic of D62 is untouched: every other class in this file
    asserts what it asserted, digit for digit. The full set of D94
    invariants lives in ``tests/test_support_failure_v1161.py``; what
    stays here is the link between the two defects, so that a reader of
    D62 is not left believing the silence is still there.
    """

    def _exploding_model(self, exc=None):
        from ogr_core.support import SupportEvaluationError, UserDefined

        class _Exploding(UserDefined):
            def force_at(self, d, L, bond=None):
                raise (exc(self.id) if exc is not None
                       else SupportEvaluationError(self.id, "boom"))

        blown = _Exploding(points=[(0.0, 10.0)], out_of_plane_spacing=1.0)
        # Reached by identity through ``type_ref``, so neither the
        # registry nor any module-level state is touched (rule 5).
        return _model([blown],
                      [_instance("user_defined", _ACROSS,
                                 type_ref=blown.id)])

    def test_the_note_says_the_support_was_lost_and_names_the_reason(self):
        p = self._exploding_model()
        note = _notes(p, _result(p))[0]
        assert "could not price" in note, note
        assert "boom" in note, note

    def test_the_solver_says_so_on_the_result(self):
        p = self._exploding_model()
        det = _result(p).details or {}
        # The whole point of D94: until v0.1.161 this key did not exist and
        # the result was indistinguishable from an unreinforced model's.
        assert "boom" in det.get("support_failure", ""), det

    def test_and_the_factor_is_the_unreinforced_one(self):
        # Still true, and now for a stated reason rather than in silence:
        # this model has ONE support and it is the one that cannot be
        # priced, so the slope really is bare. With a second, sound
        # support the two factors differ — that is the identity
        # ``test_support_failure_v1161.py`` anchors on.
        p = self._exploding_model()
        bare = _model([_nail_type()], [])
        assert _result(p).fos == _result(bare).fos

    def test_but_a_plain_runtime_error_is_not_swallowed(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms

        p = self._exploding_model(lambda _sid: RuntimeError("boom"))
        sl = slice_surface(p, _circle(), num_slices=25)
        # +1 is the right-to-left sense the fixture slope slides in; the
        # assertion does not depend on it, since the raise happens before
        # any sign is used.
        try:
            resolve_support_terms(p, _circle(), sl, 1.0)
        except RuntimeError:
            return
        raise AssertionError("the blanket handler is back")


# ======================================================================
try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except Exception:  # noqa: BLE001 - pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS: list = []   # Qt destroys the widgets with the owning window


@_requires_qt
class TestTheNotesAreReadableInTheInterface:
    """A note nobody can read is the same silence in a longer sentence.

    The engine side of D62 is only half of it: the window kept every note
    in ``last_compute_warnings`` and showed ``[0]`` in the status bar, so
    which note survived was decided by append order. These pin the panel
    that shows all of them.
    """

    def test_the_panel_lists_every_note_and_not_only_the_first(self):
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel

        QApplication.instance() or QApplication([])
        notes = ["bishop_simplified: first thing",
                 "bishop_simplified: second thing",
                 "spencer: third thing",
                 "a model-wide fourth thing"]
        panel = AnalysisNotesPanel(notes)
        _WINDOWS.append(panel)
        assert panel.notes == notes
        # Three groups: two methods and the model-wide one.
        assert panel.tree.topLevelItemCount() == 3, panel.tree
        shown = []
        for i in range(panel.tree.topLevelItemCount()):
            top = panel.tree.topLevelItem(i)
            for j in range(top.childCount()):
                shown.append(top.child(j).text(0))
        assert len(shown) == 4, shown
        assert "second thing" in shown, shown

    def test_an_empty_run_says_so_rather_than_showing_an_empty_box(self):
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel

        QApplication.instance() or QApplication([])
        panel = AnalysisNotesPanel([])
        _WINDOWS.append(panel)
        assert panel.tree.topLevelItemCount() == 0
        assert "no notes" in panel.lbl_head.text()

    def test_the_panel_is_not_modal(self):
        """A modal dialog blocks forever without a display, which is what
        the suite runs in — the rule the project writes as 'informative
        graphics go non-modal'.
        """
        from ogr_gui.dialogs.analysis_notes_panel import AnalysisNotesPanel

        QApplication.instance() or QApplication([])
        panel = AnalysisNotesPanel(["x: y"])
        _WINDOWS.append(panel)
        assert panel.isModal() is False

    def test_the_window_carries_the_notes_before_anything_is_computed(self):
        """Until v0.1.155 the attribute did not exist until the first
        compute, so asking early raised AttributeError.
        """
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.main_window import MainWindow

        w = MainWindow()
        _WINDOWS.append(w)
        assert w.last_compute_warnings == []
        assert "analysis_notes" in w._actions

    def test_opening_it_twice_reuses_the_same_panel(self):
        QApplication.instance() or QApplication([])
        from ogr_gui.i18n import set_language
        set_language("en")
        from ogr_gui.main_window import MainWindow

        w = MainWindow()
        _WINDOWS.append(w)
        w.last_compute_warnings = ["bishop_simplified: something"]
        w.act_analysis_notes()
        first = w._analysis_notes_panel
        w.act_analysis_notes()
        assert w._analysis_notes_panel is first
