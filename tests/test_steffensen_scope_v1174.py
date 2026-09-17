# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A switch saved to the file as applied must be applied, or say where it is not.

WHAT INVARIANT THIS PROTECTS. ``Accelerate convergence (Steffensen)`` is one
checkbox, it ships ON, it is written into every ``.ogr``, and ``build_method``
hands it to all nine methods through ``lem_kwargs()``. THREE of them read it.
The other six take it, store it in ``self.iterate_steffensen`` and never
consult the attribute again. That is defect D115, and it is rule 7 in the form
that gives the user no way to notice: not a control that does nothing — the
control works perfectly in Bishop and both Janbu — but a FILE that states
something the analysis did not do, on 204 of the 204 models of the reference
bank.

So this file enforces two things at once. **The scope must be told** — on the
control, where Project Settings shows it without an analysis having to be run,
and in a note when a run turns out to have honoured it nowhere — and **the six
that ignore it must keep ignoring it**, which is rule 7 read backwards: a
setting that does not arrive CANNOT move the number, and the day one of them
starts moving, the sentence on screen becomes false.

WHY IT IS NOT WIRED, because the obvious fix is the one somebody will propose.
Measured in v0.1.159: Bishop's pattern copied literally makes the branch WORSE
— lambda = 1.2269 at 1e-10 goes from 171 passes to 430 — and at lambda = 2.0 it
kills it outright, because the state of ``solve_branch`` is not F but the pair
(F, X) and extrapolating F leaves X behind. Extrapolating the pair together
buys 1.4 to 1.6x and moves 8 of 8 numbers at the shipped tolerance. The note
and the label are the close; the wiring is its own version.

WHAT THE MEASUREMENT SAYS AND THE FICHA DOES NOT. The ficha names Spencer and
GLE as the methods that ignore the switch and proposes the label "(Bishop,
Janbu)". Both are short of what an A/B over the nine methods returns, and the
test below is written against the measurement:

  * SIX methods ignore it, not two. Lowe-Karafiath and the two Corps of
    Engineers iterate on the factor of safety — 20 and 21 passes on the fixture
    below — and were simply never wired; Ordinary/Fellenius has no iteration at
    all. Saying "Spencer and GLE" would leave four methods carrying the same
    false promise, which is the trap D117 walked into with "seven of the nine".
  * Bishop honours it on CIRCULAR surfaces only. ``_general_moment_fos``, the
    branch a polyline takes, relaxes at 50 % and has never mentioned Steffensen
    — measured, 24 passes with the switch on and 24 with it off, bit for bit. So
    the label the ficha proposes says something about Bishop that only holds on
    circles, and the note has to ask what the search returns.

HOW THE RULE 7 GATE WAS BUILT, because a test of a defect that cannot see the
defect is the trap this project has now walked into ten times (D101, D103,
D118, D127, D129). The gate is NOT "the note fires when Spencer or GLE are
active", which is what the ficha asks: the switch defaults to ON and the bank
carries it in all 204 models, so that condition is true in 82 of the 91 models
that name their methods, and a note that fires on nine runs in ten is a note
nobody reads — ``test_efp_wall_v1122`` asserts exactly that with ``quiet == []``.
The gate is the narrower fact: the run honoured it NOWHERE. That is 8 of 91.

WHICH CASES MEASURE THE DEFECT AND WHICH ARE CONTROL, counted rather than
asserted. Against the tree of 0.1.173, with only this file added, 16 of the 34
FAIL and 18 PASS, and the 18 are exactly the ones that should: the five of
``TestTheSixThatIgnoreItReturnBitForBitTheSame`` and the four of
``TestTheThreeThatHonourItStillDo``, which pin the measurement the new sentence
RESTS on and are green on both trees by construction; the two of
``TestTheCensusCannotDriftFromTheEngine`` that ask the registry rather than the
new tuple; the six that assert SILENCE, which cannot discriminate on a tree
where nothing ever speaks; and the one that checks the checkbox still writes
the setting. None of those nine-plus-nine detect D115, and a test whose
docstring does not say which of the two it is will be read as the one it is not.

Two cases in the first draft of this file passed against 0.1.173 for the WRONG
reason, and both were caught by running it that way rather than by reading it.
``test_it_does_not_invent_a_method_in_the_notes_panel`` looped over the notes
and asserted the group of each, which on a tree with no note is an empty loop
and a green tick — it now counts the notes it filed. And
``test_both_new_strings_are_translated`` asserted that there were two Steffensen
keys and both were translated, which the RETIRED pair also satisfied; it now
identifies the two by the words this version introduced.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a change delivers is what cost this project two versions in v0.1.82-84:

  * that the switch was made to work anywhere it did not work before. Nothing
    in the engine changed. Six methods ignore it after this version exactly as
    they ignored it before, and the classes below that assert so are CONTROL,
    not coverage.
  * that the Particle Swarm is decided. It is in both surface families because
    its particles ARE circles and the polyline is what the optimisation makes
    of the winners, so on a non-circular swarm run Bishop still has circles to
    accelerate and the note deliberately stays quiet. That is a choice to avoid
    a FALSE note, not a measurement of the swarm.
  * that the note reaches the report. It does not: ``iterate_steffensen`` never
    reaches ``report_generator`` or ``ogr_cli`` at all, so the false promise
    lives in the dialog and in the ``.ogr``, and only those two are answered.
"""
from __future__ import annotations


# ======================================================================
# Fixtures
# ======================================================================
#: A fragment of the note, chosen so it cannot match any other warning.
NOTE_MARK = "Accelerate convergence (Steffensen) is on"

#: The six the switch never reaches, and the three it does. Spelled out
#: here rather than imported so that the day somebody edits the engine's
#: tuple, THIS file is what disagrees with it — see the AST census below.
IGNORE = ("spencer", "gle_morgenstern_price", "lowe_karafiath",
          "corps_engineers_1", "corps_engineers_2", "ordinary_fellenius")
HONOUR = ("bishop_simplified", "janbu_simplified", "janbu_corrected")


def _slope():
    """An ordinary slope, sliceable and with a sensible factor of safety."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("steffensen")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=10, friction_angle=25))]
    return p


def _circle():
    from ogr_slip2d import SlipCircle
    return SlipCircle(centre_x=35, centre_y=42, radius=35)


def _polyline():
    """A non-circular surface through the same slope."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(8.0, 26.0), Vertex(18.0, 7.5),
        Vertex(34.0, 5.0), Vertex(47.0, 10.0)]))


def _sliced(surface):
    from ogr_slip2d import slice_surface
    p = _slope()
    sl = slice_surface(p, surface, num_slices=25)
    assert sl is not None
    return p, sl


def _project(search="grid", surface_type="circular", steffensen=True):
    p = _slope()
    p.settings.advanced.iterate_steffensen = steffensen
    p.settings.search.search_method = search
    p.settings.search.surface_type = surface_type
    return p


def _notes(method_ids, **kw):
    """Only this defect's note, so another warning cannot answer for it."""
    from ogr_slip2d.analysis_runner import settings_warnings

    return [n for n in settings_warnings(_project(**kw), method_ids)
            if NOTE_MARK in n]


def _pair(method_id, surface):
    """The same method on the same surface, switch off and switch on."""
    from ogr_slip2d.methods.base import method_registry

    p, sl = _sliced(surface)
    cls = method_registry()[method_id]
    kw = dict(tolerance=1e-8, max_iterations=200, initial_fos=1.0)
    plain = cls(**kw, iterate_steffensen=False).compute_fos(p, surface, sl)
    fast = cls(**kw, iterate_steffensen=True).compute_fos(p, surface, sl)
    return plain, fast


# ======================================================================
# A. The note, and the two things it must not do
# ======================================================================
class TestTheRunSaysWhenTheSwitchReachedNothing:
    """It must speak where the setting did nothing, and nowhere else.

    "Nowhere else" is the load-bearing half. The switch ships ON and every
    model of the reference bank carries it, so a note keyed on "Spencer or
    GLE are active" — the ficha's wording — would arrive on 82 of the 91
    models that name their methods. The condition here is the rule 7 one:
    not one method of this run honoured it.
    """

    def test_it_speaks_when_no_method_honours_it(self):
        notes = _notes(["spencer", "gle_morgenstern_price"])
        assert len(notes) == 1, notes

    def test_it_speaks_for_the_four_the_ficha_does_not_name(self):
        """Lowe-Karafiath, both Corps, and Ordinary/Fellenius."""
        for mid in ("lowe_karafiath", "corps_engineers_1",
                    "corps_engineers_2", "ordinary_fellenius"):
            assert len(_notes([mid])) == 1, mid

    def test_it_is_silent_when_one_method_does_honour_it(self):
        """A mixed run is the common case and it is not a defect."""
        assert _notes(["spencer", "bishop_simplified"]) == []
        assert _notes(["gle_morgenstern_price", "janbu_corrected"]) == []

    def test_it_is_silent_with_the_switch_off(self):
        """Nothing is being promised, so nothing is owed."""
        assert _notes(["spencer"], steffensen=False) == []
        assert _notes(IGNORE, steffensen=False) == []

    def test_it_is_silent_with_no_methods_at_all(self):
        assert _notes([]) == []
        assert _notes(()) == []

    def test_it_names_the_methods_that_actually_ran(self):
        """Built from ``method_ids``, never a sentence written by hand."""
        note = _notes(["spencer", "lowe_karafiath"])[0]
        assert "spencer" in note and "lowe_karafiath" in note, note
        assert "corps_engineers_1" not in note, note

    def test_it_does_not_invent_a_method_in_the_notes_panel(self):
        """Run through the panel's REAL splitter, not a copy of its rule.

        ``_split`` files a note under the first token before a colon when
        that token has no spaces, so a sentence opening "Spencer/GLE: ..."
        — which is the wording the ficha proposes — lands under a method
        group that does not exist. That is D129, closed in v0.1.170.
        """
        from ogr_gui.dialogs.analysis_notes_panel import _split

        seen = 0
        for mids in (["spencer"], ["ordinary_fellenius"], list(IGNORE)):
            for note in _notes(mids):
                seen += 1
                group, _sentence = _split(note)
                assert group == "Model", (group, note)
        # Without this the loop is empty on a tree that has no note yet and
        # the case passes having filed nothing, which is a test that cannot
        # see the defect it is named for.
        assert seen == 3, seen

    def test_it_says_the_results_are_unchanged_rather_than_wrong(self):
        """The analysis is valid; only the file's claim was not."""
        note = _notes(["spencer"])[0]
        assert "reached nothing" in note, note
        assert "same as they would be with it off" in note, note


# ======================================================================
# B. The surface type is part of the question
# ======================================================================
class TestBishopOnlyAcceleratesItsCircularBranch:
    """The half of the census the ficha does not have.

    ``BishopSimplified.compute_fos`` dispatches a non-circular surface to
    ``_general_moment_fos``, which relaxes at 50 % and never mentions
    Steffensen. So on a Block or Path search the three methods that honour
    the switch are two, and a run with Bishop alone honoured it NOWHERE.
    """

    def test_a_polyline_search_with_bishop_alone_gets_the_note(self):
        notes = _notes(["bishop_simplified"],
                       search="block", surface_type="non_circular")
        assert len(notes) == 1, notes
        assert "only on its circular branch" in notes[0], notes[0]

    def test_the_same_run_on_a_grid_search_does_not(self):
        assert _notes(["bishop_simplified"]) == []

    def test_every_polyline_only_search_answers_the_same(self):
        for search in ("block", "path", "simulated_annealing"):
            notes = _notes(["bishop_simplified"],
                           search=search, surface_type="non_circular")
            assert len(notes) == 1, search

    def test_the_non_circular_auto_refine_counts_as_one(self):
        """Auto Refine is in both families, so it is the PAIR that answers.

        Asked through ``is_auto_refine_non_circular``, which v0.1.128 wrote
        precisely so the next place to ask could not answer differently.
        """
        assert len(_notes(["bishop_simplified"], search="auto_refine",
                          surface_type="non_circular")) == 1
        assert _notes(["bishop_simplified"], search="auto_refine") == []

    def test_the_swarm_stays_quiet_and_that_is_a_choice(self):
        """Its particles ARE circles; the polyline comes from the optimiser.

        So Bishop has circles to accelerate on that run and a note would be
        FALSE. Declared here rather than left to be discovered, because the
        swarm sits in both families exactly like Auto Refine and the two are
        treated differently on purpose.
        """
        assert _notes(["bishop_simplified"], search="particle_swarm",
                      surface_type="non_circular") == []

    def test_janbu_is_not_affected_by_the_surface_type(self):
        """Janbu has one ``compute_fos`` and accelerates in both families."""
        for search, stype in (("block", "non_circular"), ("grid", "circular")):
            assert _notes(["janbu_simplified"],
                          search=search, surface_type=stype) == []
            assert _notes(["janbu_corrected"],
                          search=search, surface_type=stype) == []


# ======================================================================
# C. Rule 7 read backwards: a setting that does not arrive cannot move
#    the number
# ======================================================================
class TestTheSixThatIgnoreItReturnBitForBitTheSame:
    """The measurement the label rests on.

    Every sentence written on screen by this version is a claim about these
    six methods. If one of them starts responding to the switch, the screen
    starts lying — so the assertion is equality of BOTH the factor and the
    pass count, not a tolerance: an accelerated sequence that landed on the
    same root would still have taken a different number of passes.
    """

    def test_the_factor_does_not_move(self):
        for mid in IGNORE:
            plain, fast = _pair(mid, _circle())
            assert plain.fos == fast.fos, (mid, plain.fos, fast.fos)

    def test_and_neither_does_the_pass_count(self):
        for mid in IGNORE:
            plain, fast = _pair(mid, _circle())
            assert plain.iterations == fast.iterations, (
                mid, plain.iterations, fast.iterations)

    def test_the_three_that_do_iterate_are_genuinely_iterating(self):
        """Otherwise the two assertions above would pass for the wrong reason.

        Lowe-Karafiath and the two Corps run a fixed point on the factor of
        safety that Steffensen COULD accelerate and is simply not wired to;
        they are the interesting half of the six, and a fixture on which they
        converged in one pass would make this whole class vacuous.
        """
        for mid in ("lowe_karafiath", "corps_engineers_1",
                    "corps_engineers_2"):
            plain, _fast = _pair(mid, _circle())
            assert plain.iterations > 1, (mid, plain.iterations)

    def test_ordinary_fellenius_does_not_iterate_at_all(self):
        """Its own reason for ignoring the switch, and a different one."""
        plain, fast = _pair("ordinary_fellenius", _circle())
        assert plain.iterations == fast.iterations == 1

    def test_bishop_ignores_it_on_a_non_circular_surface(self):
        """The finding this version adds to the ficha, as a measurement."""
        plain, fast = _pair("bishop_simplified", _polyline())
        assert plain.fos == fast.fos, (plain.fos, fast.fos)
        assert plain.iterations == fast.iterations


# ======================================================================
# D. CONTROL — what this change must NOT have bought the label with
# ======================================================================
class TestTheThreeThatHonourItStillDo:
    """CONTROL, green before and after this version, and that is the point.

    This class does not cover the defect: it guards against the error THIS
    design could make, which is buying an honest label by quietly turning
    the acceleration off, or by narrowing it until the sentence is true. A
    test whose docstring does not say which of the two it is will be read
    as the one it is not.
    """

    def test_they_reach_the_same_root_in_fewer_passes(self):
        for mid in HONOUR:
            plain, fast = _pair(mid, _circle())
            assert plain.converged and fast.converged, mid
            assert fast.iterations < plain.iterations, (
                mid, plain.iterations, fast.iterations)
            assert abs(plain.fos - fast.fos) < 1e-7, (mid, plain.fos, fast.fos)

    def test_janbu_accelerates_on_a_polyline_too(self):
        """Which is why the note asks the surface type only about Bishop."""
        for mid in ("janbu_simplified", "janbu_corrected"):
            plain, fast = _pair(mid, _polyline())
            assert fast.iterations < plain.iterations, mid

    def test_the_switch_still_ships_on(self):
        """The label describes the shipped state, so the state is pinned.

        Read from the dataclass field: a ``True`` written here is a sentence
        that starts lying the day the default moves.
        """
        from dataclasses import fields as dataclass_fields

        from ogr_core.project.settings import AdvancedSettings
        default = next(f.default for f in dataclass_fields(AdvancedSettings)
                       if f.name == "iterate_steffensen")
        assert default is True

    def test_it_still_reaches_every_method_from_the_project(self):
        """``lem_kwargs`` is unchanged: the close is a sentence, not a rewire."""
        from ogr_core.project import ProjectSettings

        assert ProjectSettings().lem_kwargs()["iterate_steffensen"] is True


# ======================================================================
# E. The census in the code is the census on the screen
# ======================================================================
class TestTheCensusCannotDriftFromTheEngine:
    """If somebody wires a seventh method, this file goes red.

    Measured over the method registry and the class bodies rather than over
    a list, because the list is the thing that would be forgotten. The base
    class is excluded on purpose: ``LEMMethod.__init__`` STORES the flag for
    all nine, and storing it is exactly the defect.
    """

    def _readers(self):
        import inspect

        from ogr_slip2d.methods.base import LEMMethod, method_registry

        out = set()
        for mid, cls in method_registry().items():
            for klass in cls.__mro__:
                if klass in (LEMMethod, object):
                    continue
                try:
                    src = inspect.getsource(klass)
                except (OSError, TypeError):        # pragma: no cover
                    continue
                if "self.iterate_steffensen" in src:
                    out.add(mid)
                    break
        return out

    def test_exactly_three_methods_consult_the_flag(self):
        assert self._readers() == set(HONOUR), sorted(self._readers())

    def test_the_registry_still_holds_nine(self):
        """The sentence on screen enumerates nine; a tenth would orphan it."""
        from ogr_slip2d.methods.base import method_registry

        assert len(method_registry()) == 9, sorted(method_registry())

    def test_the_engine_tuple_agrees_with_this_file(self):
        from ogr_slip2d.analysis_runner import (_STEFFENSEN_CIRCULAR_ONLY,
                                                _STEFFENSEN_METHODS)
        assert set(_STEFFENSEN_METHODS) == set(HONOUR)
        assert set(_STEFFENSEN_CIRCULAR_ONLY) == {"bishop_simplified"}

    def test_the_reach_helper_is_the_one_the_note_uses(self):
        """One rule, one owner: the note must not carry a second copy."""
        from ogr_slip2d.analysis_runner import _steffensen_honouring

        circular = _project()
        assert _steffensen_honouring(circular, IGNORE) == ()
        assert set(_steffensen_honouring(circular, HONOUR)) == set(HONOUR)
        polyline = _project(search="block", surface_type="non_circular")
        assert set(_steffensen_honouring(polyline, HONOUR)) == {
            "janbu_simplified", "janbu_corrected"}


# ======================================================================
# F. The control on screen
# ======================================================================
def _dialog_tr_keys():
    """Every literal the settings dialog hands to ``tr()``, by AST.

    Same technique as ``test_i18n_coverage_v141._wrapped_keys``, and for
    the same reason: Python's implicit concatenation defeats a regex, and
    a key read wrong is a key that silently falls back to English.
    """
    import ast
    import io

    src = io.open("ogr_gui/dialogs/project_settings_dialog.py",
                  encoding="utf-8").read()
    out = []
    for node in ast.walk(ast.parse(src)):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "tr" and node.args):
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                out.append(arg.value)
    return out


class TestTheControlOnScreen:
    """The standing fact belongs on the control, not only in a note.

    A note needs an analysis to have been run. The question "does this
    switch do anything for the methods I ticked?" is asked while ticking
    them, which is why the census lives in the tooltip and the scope in
    the label — the same division :func:`_max_iterations_scope_notes` made
    one version earlier.
    """

    def teardown_method(self, _m=None):
        """Kept for a real pytest, and NOT relied upon here.

        Rule 5 says a test may not leak global state, and the active
        language is the example the rule was written from. But
        ``tests/_runner.py`` does not implement ``teardown_method`` at all —
        measured, zero occurrences of the name — so a class that switches
        the language and trusts this hook leaves it switched for every file
        that runs after it. The restore that actually runs is the
        ``finally`` below.
        """
        from ogr_gui.i18n import set_language
        set_language("en")

    def _keys(self):
        return [k for k in _dialog_tr_keys()
                if "Steffensen" in k or "Aitken extrapolation" in k]

    def test_the_label_says_the_scope_differs(self):
        label = [k for k in self._keys() if k.startswith("Accelerate")]
        assert len(label) == 1, label
        assert "scope differs by method" in label[0], label[0]

    def test_the_tooltip_carries_the_whole_census(self):
        """All nine methods, in the four groups the measurement found."""
        tip = [k for k in self._keys() if k.startswith("Aitken")]
        assert len(tip) == 1, tip
        for name in ("Bishop simplified", "Janbu simplified",
                     "Janbu corrected", "Lowe-Karafiath",
                     "Corps of Engineers", "Ordinary/Fellenius", "Spencer",
                     "GLE/Morgenstern-Price"):
            assert name in tip[0], name

    def test_the_tooltip_says_where_bishop_stops(self):
        tip = [k for k in self._keys() if k.startswith("Aitken")][0]
        assert "circular surfaces" in tip, tip
        assert "non-circular branch" in tip, tip

    def test_the_old_promise_is_gone_and_not_merely_buried(self):
        """The retired tooltip stated a Bishop measurement as a property of
        the setting. Leaving it beside the new one would be two texts that
        eventually contradict each other, which is the lesson of v0.1.167."""
        assert not [k for k in _dialog_tr_keys()
                    if "Aitken extrapolation of the fixed-point" in k]

    def test_both_new_strings_are_translated(self):
        """A key without a Spanish entry falls back to English in silence,
        which is the ``"Add Grid"`` / ``"Add Grid..."`` defect of v0.1.166.

        The two keys are identified by the words THIS version introduced and
        not merely counted: the retired pair also numbered two and was also
        translated, so a count alone is green on both trees and answers a
        question nobody asked.
        """
        from ogr_gui.i18n import set_language, tr

        keys = [k for k in self._keys()
                if "scope differs by method" in k
                or "Not every method has one to accelerate" in k]
        assert len(keys) == 2, [k[:60] for k in keys]
        try:
            set_language("es")
            for key in keys:
                assert tr(key) != key, key[:60]
        finally:
            # The restore has to be here and not in ``teardown_method``: the
            # project runner never calls that hook, so without this the next
            # file runs in Spanish and asserts English text. Measured, that
            # is exactly what broke ``test_support_silence_v1155``.
            set_language("en")

    def test_the_retired_key_left_no_orphan_behind(self):
        """Asked of the dictionary, not of a grep: the comment that explains
        the rename spells the old key out, so a grep answers yes."""
        from ogr_gui.i18n import _DICTS

        assert "Accelerate convergence (Steffensen)" not in _DICTS["es"]
        live = [k for k in _DICTS["es"]
                if "Steffensen" in k or "Aitken" in k]
        assert len(live) == 2, [k[:50] for k in live]

    def _advanced_page(self, settings):
        """The Advanced page of a real dialog.

        The page is found through the ``_PAGES`` table rather than by an
        index written here: that table has grown twice, and a 7 spelled out
        in a test is a number that starts pointing at Seismic one day. The
        dialog is parked in ``_WINDOWS`` and never deleted, which is the
        shape ``test_max_iterations_scope_v1173`` settled on — a dialog
        collected while Qt still holds it takes the interpreter down with
        it, and without an event loop ``deleteLater`` never runs.
        """
        from PySide6.QtWidgets import QApplication

        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        QApplication.instance() or QApplication([])
        row = [i for i, (label, _cls) in enumerate(ProjectSettingsDialog._PAGES)
               if label == "Advanced"]
        assert len(row) == 1, ProjectSettingsDialog._PAGES
        dialog = ProjectSettingsDialog(settings)
        _WINDOWS.append(dialog)
        return dialog.pages[row[0]]

    def test_the_checkbox_is_built_and_still_writes_the_setting(self):
        """The label changed; what it controls did not."""
        from ogr_core.project import ProjectSettings

        s = ProjectSettings()
        page = self._advanced_page(s)
        assert hasattr(page, "chk_steffensen"), "not the Advanced page"
        assert page.chk_steffensen.toolTip(), "the control has no help"
        page.chk_steffensen.setChecked(False)
        page.apply()
        assert s.advanced.iterate_steffensen is False


#: Dialogs built by the tests above, kept alive on purpose. See
#: ``_advanced_page``.
_WINDOWS: list = []
