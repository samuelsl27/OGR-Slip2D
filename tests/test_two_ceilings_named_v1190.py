# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.190 — there are TWO ceilings on a slice base angle, and the program
has to name both wherever it offers one.

THE INVARIANT. ``max_base_angle_deg`` has a name, a spin box, a default
of 80 and a tooltip, and ``search._base_angle_ok`` applies it ONLY to
surfaces a weak layer has clipped. Under ``phi = 0`` the m-alpha check
degenerates into a bare ceiling of ``acos(0.2) = 78.5`` deg over EVERY
surface of the methods ``checks.M_ALPHA_SCREENED`` covers, and it has no
control over its number. So the one with a name reaches less than the one
without, someone who types 45 still has 78.5 over everything else, and
someone who types 85 over a weak layer has 78.5 there too. That is rule
7: a control that does not do what its name says. Defect D110.

WHAT THIS FILE DOES NOT CLAIM. It does not say either ceiling is the
right one, and it does not widen ``_base_angle_ok`` — measured in
v0.1.121 to move models with no weak layer at all, including the
validated cases. Whether the two should be unified is D61, decided in
this same version by NOT unifying them, and fixed by
``test_phi_zero_ceiling_decision_v1190.py``.

WHAT THIS FILE DISCRIMINATES against the v0.1.189 tree. MEASURED, by
copying this file into a ``git worktree`` at that commit and running it
there — not predicted. Of the 18 cases, **10 fail and 8 pass**:

  fail  a_weak_layer_model_gets_the_scope_note_at_any_value
        the_note_says_which_of_the_two_is_the_tighter_one
        a_model_with_no_weak_layer_and_a_changed_value_is_told_so
        with_the_m_alpha_check_off_the_note_says_nothing_caps_it
        the_note_is_exact_about_which_methods_are_screened
        the_tooltip_says_which_surfaces_the_control_reaches
        the_dynamic_label_names_the_other_ceiling_at_every_value
        the_m_alpha_checkbox_says_it_is_a_base_angle_ceiling
        the_literal_in_the_dialog_is_the_computed_ceiling
        every_new_string_has_spanish

  pass  the_m_alpha_ceiling_is_the_arccosine_of_the_limit   (premise)
        the_named_ceiling_reaches_only_weak_layer_clips     (guard)
        and_the_other_one_reaches_it                        (guard)
        the_default_on_a_model_with_no_weak_layer_stays_silent (guard)
        the_partition_is_read_from_the_engine_and_not_typed (guard)
        the_d106_sentence_belongs_to_exactly_one_note       (TRIPWIRE)
        the_notes_do_not_move_the_analysis                  (guard)
        no_note_carries_the_substrings_the_bank_reserves    (guard)

Every failing case fails on behaviour or on a string a user reads, not on
the absence of a symbol — there is no weak discrimination here. The eight
that pass are labelled in their own docstrings as what they are, and one
of them is not a discriminator at all: the TRIPWIRE is what holds up the
sharpened helper in ``test_base_angle_ceiling_v1158.py``, whose filter
used to select on the topic and now selects on D106's own sentence.

THE ANCHORS ARE NOT SNAPSHOTS. The ceiling is ``acos(M_ALPHA_LIMIT)``
imported from the engine, so moving the limit moves the test; the set of
screened methods is read from ``M_ALPHA_SCREENED`` and checked against
the method registry rather than typed; the default is read from the
dataclass field; and the scope of ``_base_angle_ok`` is measured by
RUNNING a surface through it, not by reading its source.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_slip2d.checks import (  # noqa: E402
    M_ALPHA_LIMIT,
    M_ALPHA_SCREENED,
    base_m_alphas,
    check_surface,
)

CEILING = math.degrees(math.acos(M_ALPHA_LIMIT))

#: Kept alive so Qt does not delete an unparented widget the moment
#: Python drops it — the same reason ``test_base_angle_ceiling_v1158``
#: keeps its own list.
_PAGES: list = []


def _scope_notes(project, method_ids=("bishop_simplified",)):
    """Only the note D110 adds, selected by its own opening.

    The lesson this file is built around: a filter that selects on the
    TOPIC selects both notes. Each helper names the sentence it means.
    """
    from ogr_slip2d.analysis_runner import settings_warnings
    return [n for n in settings_warnings(project, method_ids)
            if "Maximum base angle setting" in n]


def _d106_notes(project, method_ids=("bishop_simplified",)):
    from ogr_slip2d.analysis_runner import settings_warnings
    return [n for n in settings_warnings(project, method_ids)
            if "Maximum slice base angle is set to" in n]


def _weak_layer_project(limit: float):
    """A model that DOES draw a weak layer: ``_project`` takes none by
    default, and the joint is what puts the named ceiling in scope."""
    from test_base_angle_ceiling_v1158 import _JOINT
    from test_weak_layer_v1121 import _project
    p, _m = _project(joint=_JOINT)
    p.settings.advanced.max_base_angle_deg = limit
    return p


#: A scarp steeper than BOTH ceilings, built from the angle rather than
#: from a pair of coordinates: ``_STEEP`` of
#: ``test_block_population_v1135`` turns at 74.5 deg, which is BELOW
#: ``acos(0.2)`` on purpose — it is the fixture for "accepted and
#: dividing by a quarter". To show the two scopes disagreeing, the base
#: has to be past 78.463, so it is derived here.
def _scarp(beta_deg: float, drop: float = 36.0):
    """A polyline whose back scarp falls at ``beta_deg``."""
    dx = drop / math.tan(math.radians(beta_deg))
    return [(20.0, 30.0), (20.0 + dx, 30.0 - drop),
            (35.0 + dx, 28.0 - drop), (78.0, 10.0)]


def _plain_project(limit: float, phi: float = 0.0):
    """A slope with no weak layer at all, so the named ceiling is inert."""
    from test_block_population_v1135 import _cohesive_slope
    p = _cohesive_slope(phi)
    p.settings.advanced.max_base_angle_deg = limit
    return p


def _default_limit() -> float:
    """The factory value, read from the field and never typed.

    If it is typed here, moving the default turns the silent case below
    into a note on every run of every model and nothing says so.
    """
    from ogr_core.project.settings import AdvancedSettings
    return float(
        AdvancedSettings.__dataclass_fields__["max_base_angle_deg"].default)


def _page(limit: float):
    """The Advanced page, built in ENGLISH whatever the suite left behind.

    Rule 5, applied to this file rather than assumed of the others. The
    widget strings are fixed at construction time, so the language has to
    be English THEN, and it is restored with try/finally because the
    project's runner does not execute ``teardown_method`` — a teardown
    here would be decorative. Measured while writing this: running the
    suite with ``i18n_coverage`` ahead of this file leaves the active
    language as Spanish (``test_i18n_coverage_v141`` line 233 switches
    and does not switch back, and its ``teardown_method`` never runs), so
    the tooltips came back translated and three cases failed on a
    difference that has nothing to do with what they check.
    """
    from PySide6.QtWidgets import QApplication

    from ogr_gui.dialogs.project_settings_dialog import _AdvancedPage
    from ogr_gui.i18n import current_language, set_language
    QApplication.instance() or QApplication([])
    p = _weak_layer_project(limit)
    was = current_language()
    try:
        set_language("en")
        page = _AdvancedPage(p.settings)
    finally:
        set_language(was)
    _PAGES.append(page)
    return page


# ======================================================================
class TestTheTwoCeilingsAreDifferentNumbersWithDifferentScopes:
    """The fact the defect is about, established by measurement before
    anything is asserted about what the program says."""

    def test_the_m_alpha_ceiling_is_the_arccosine_of_the_limit(self):
        """Closed form, and the identity underneath it.

        With ``tan phi = 0`` the friction term of
        ``m_alpha = cos a + s sin a tan phi / F`` vanishes and the
        denominator is ``cos a`` exactly, so rejecting ``m_alpha < 0.2``
        IS rejecting ``|a| > acos(0.2)``. Passes on v0.1.189 too: it is
        the premise, not the change.
        """
        from test_block_population_v1135 import _STEEP, _evaluate

        assert abs(CEILING - 78.463) < 1e-3, CEILING
        res = _evaluate(_plain_project(80.0), _STEEP)
        assert res is not None and res.fos is not None
        for v, sl in zip(base_m_alphas(res), res.slices):
            assert abs(v - math.cos(sl.base_angle)) < 1e-12

    def test_the_named_ceiling_reaches_only_weak_layer_clips(self):
        """MEASURED by running the surface, not by reading the guard.

        A polyline whose steepest base is past 45 deg, on a model with no
        weak layer and the ceiling typed down to 45: it survives. That is
        the scope the defect is about, and it is a guard here — this
        version does not widen it, and if a later one does, this fails.
        """
        from test_block_population_v1135 import _evaluate

        p = _plain_project(45.0)
        p.settings.advanced.check_m_alpha = False
        res = _evaluate(p, _scarp(82.0))
        assert res is not None and res.fos is not None
        steepest = math.degrees(max(abs(s.base_angle) for s in res.slices))
        assert steepest > CEILING, steepest

    def test_and_the_other_one_reaches_it(self):
        """The same surface, the same model, the other ceiling: rejected.

        Two ceilings, one surface, opposite verdicts — which is the
        defect stated as an experiment rather than as a sentence.
        """
        from test_block_population_v1135 import _evaluate

        p = _plain_project(45.0)
        res = _evaluate(p, _scarp(82.0))
        assert res is not None
        worst = min(base_m_alphas(res))
        assert worst < M_ALPHA_LIMIT, worst
        ok, _why = check_surface(res, tensile=False, m_alpha=True)
        assert not ok


# ======================================================================
class TestTheNoteNamesWhichOneGoverns:
    """Rule 7's minimum: if a control reaches less than its name says,
    the program has to say so where the user will read it."""

    def test_a_weak_layer_model_gets_the_scope_note_at_any_value(self):
        """FAILS on v0.1.189 — there was no such note at any value."""
        for limit in (45.0, 80.0, 85.0, 90.0):
            notes = _scope_notes(_weak_layer_project(limit))
            assert len(notes) == 1, (limit, notes)
            assert f"{CEILING:.1f} deg" in notes[0], notes[0]
            assert "m-alpha" in notes[0], notes[0]

    def test_the_note_says_which_of_the_two_is_the_tighter_one(self):
        """FAILS on v0.1.189. The sentence flips at the computed ceiling
        and not at a typed number, so moving the limit moves the claim."""
        loose = _scope_notes(_weak_layer_project(85.0))[0]
        assert "85 deg set here never applies" in loose, loose

        tight = _scope_notes(_weak_layer_project(45.0))[0]
        assert "tighter of the two" in tight, tight
        assert f"{CEILING:.1f} deg governs everywhere else" in tight, tight

    def test_a_model_with_no_weak_layer_and_a_changed_value_is_told_so(self):
        """FAILS on v0.1.189. Typing a value into a control that reaches
        nothing in THIS model is the half of D110 the user cannot see at
        all: the analysis simply ignores it."""
        notes = _scope_notes(_plain_project(45.0))
        assert len(notes) == 1, notes
        assert "No weak layer is drawn" in notes[0], notes[0]
        assert "reached nothing" in notes[0], notes[0]

    def test_the_default_on_a_model_with_no_weak_layer_stays_silent(self):
        """Passes today because there is no note at all; it is a GUARD,
        and it is the one that keeps the new note from becoming noise.

        A note on the factory value of a setting nobody touched would
        arrive on every run of every model — the error D106 was scoped
        against — and would break the published-model files that assert
        ``settings_warnings(...) == []``.
        """
        assert _scope_notes(_plain_project(_default_limit())) == []

    def test_with_the_m_alpha_check_off_the_note_says_nothing_caps_it(self):
        """FAILS on v0.1.189. A note that claimed 78.5 with the check
        switched off would be false in exactly the configuration where a
        user most needs it to be true."""
        p = _weak_layer_project(85.0)
        p.settings.advanced.check_m_alpha = False
        note = _scope_notes(p)[0]
        assert "m-alpha check is off" in note, note
        assert f"{CEILING:.1f}" not in note, note
        assert "no ceiling on the inclination of its base" in note, note

    def test_the_note_is_exact_about_which_methods_are_screened(self):
        """FAILS on v0.1.189.

        Since v0.1.189 the screen does NOT reach every method, so a note
        saying "every surface" would be aimed at the wrong family — the
        shape of the defect D104 closed. The members are read from the
        imported set, never typed here.
        """
        assert "bishop_simplified" in M_ALPHA_SCREENED
        assert "ordinary_fellenius" not in M_ALPHA_SCREENED

        only_out = _scope_notes(_weak_layer_project(85.0),
                                ("ordinary_fellenius",))[0]
        assert "no method in this run is screened by it" in only_out
        assert "ordinary_fellenius" in only_out

        mixed = _scope_notes(_weak_layer_project(85.0),
                             ("bishop_simplified", "ordinary_fellenius"))[0]
        assert "(bishop_simplified)" in mixed, mixed
        assert "does not screen ordinary_fellenius" in mixed, mixed

        # Called with no method ids at all — which is how
        # ``settings_warnings`` is reached from several callers — it must
        # name the set without claiming anything about what ran.
        blind = _scope_notes(_weak_layer_project(85.0), ())[0]
        for mid in M_ALPHA_SCREENED:
            assert mid in blind, (mid, blind)

    def test_the_partition_is_read_from_the_engine_and_not_typed(self):
        """The set the note names is the set the check uses, and both are
        a subset of the methods that exist. Measured against the registry
        so a method born tomorrow cannot fall between the two."""
        from ogr_slip2d.methods import method_registry

        known = set(method_registry())
        assert M_ALPHA_SCREENED <= known, M_ALPHA_SCREENED - known


# ======================================================================
class TestTheTwoNotesStayTellingApart:
    """Not a discriminator — a TRIPWIRE, and it is load-bearing.

    ``test_base_angle_ceiling_v1158._notes`` used to select every note
    containing "base angle"; v0.1.190 sharpened it to D106's own
    sentence. That sharpening is only safe while exactly one note carries
    that sentence, and nothing else in the suite checks it.
    """

    def test_the_d106_sentence_belongs_to_exactly_one_note(self):
        for limit in (0.0, -5.0, 1.0, 45.0, 80.0, 85.0, 89.9, 90.0):
            for build in (_weak_layer_project, _plain_project):
                p = build(limit)
                d106 = _d106_notes(p)
                assert len(d106) <= 1, (limit, build.__name__, d106)
                if d106:
                    assert "removes it" in d106[0]
                    assert not (0.0 < limit < 90.0), limit
                for n in _scope_notes(p):
                    assert "Maximum slice base angle is set to" not in n, n


# ======================================================================
class TestTheDialogNamesBothToo:
    """The engine's note arrives AFTER the analysis; the person choosing
    the value is looking at the panel BEFORE it. Same argument v0.1.158
    used for the live label under the spin box."""

    def test_the_tooltip_says_which_surfaces_the_control_reaches(self):
        """FAILS on v0.1.189, whose tooltip said "Applies to surfaces a
        weak layer has clipped" without saying what happens to the rest."""
        tip = _page(80.0).sp_base_angle.toolTip()
        assert "ONLY" in tip, tip
        assert "weak layer" in tip, tip
        assert f"{CEILING:.1f} deg" in tip, tip
        assert "m-alpha" in tip, tip

    def test_the_dynamic_label_names_the_other_ceiling_at_every_value(self):
        """FAILS on v0.1.189, which had two branches and mentioned the
        other ceiling in neither."""
        texts = {}
        for limit in (45.0, 85.0, 90.0):
            page = _page(limit)
            texts[limit] = page.lbl_base_angle.text()
            assert texts[limit], limit
            assert "78.5" in texts[limit], (limit, texts[limit])
        # Three values, three different sentences: the middle band is the
        # one v0.1.189 could not express, because there the named ceiling
        # is LOOSER than the one already in force.
        assert len(set(texts.values())) == 3, texts
        assert "switched off" in texts[90.0]
        assert "never bites" in texts[85.0]
        assert "tighter of the two" in texts[45.0]

    def test_the_m_alpha_checkbox_says_it_is_a_base_angle_ceiling(self):
        """FAILS on v0.1.189. The control with no number was also the
        control with no explanation of what its number does."""
        tip = _page(80.0).chk_m_alpha.toolTip()
        assert f"{CEILING:.1f} deg" in tip, tip
        assert "cosine of the base angle" in tip, tip
        assert "Bishop" in tip and "Janbu" in tip and "Spencer" in tip
        assert "not screened" in tip, tip

    def test_the_literal_in_the_dialog_is_the_computed_ceiling(self):
        """FAILS on v0.1.189 (the strings do not exist yet).

        The dialog strings must carry the number as a LITERAL, because
        the translation extractor only sees constants. That is a real
        risk of divergence, so it is pinned: if someone moves
        ``M_ALPHA_LIMIT``, this fails and names the strings to fix.
        """
        assert f"{CEILING:.1f}" == "78.5", CEILING
        page = _page(80.0)
        assert "78.5" in page.sp_base_angle.toolTip()
        assert "78.5" in page.chk_m_alpha.toolTip()

    def test_every_new_string_has_spanish(self):
        """FAILS on v0.1.189. Rule 2, checked for these strings here as
        well as in the coverage file, because a key added without its
        entry is a key that silently shows English."""
        from ogr_gui.i18n import _DICTS

        page = _page(45.0)
        keys = [page.sp_base_angle.toolTip(), page.chk_m_alpha.toolTip(),
                page.lbl_base_angle.text(),
                _page(85.0).lbl_base_angle.text(),
                _page(90.0).lbl_base_angle.text(),
                "Maximum base angle on weak-layer clips:"]
        es = _DICTS["es"]
        for k in keys:
            assert k in es, k[:70]
            assert es[k] != k, k[:70]


# ======================================================================
class TestNoneOfThisMovedANumber:
    """The whole version is a zero-digit one. This is that claim, made
    where the suite can check it rather than in the changelog."""

    def test_the_notes_do_not_move_the_analysis(self):
        from test_block_population_v1135 import _STEEP, _evaluate

        p = _weak_layer_project(90.0)
        before = _evaluate(_plain_project(45.0), _STEEP)
        _scope_notes(p)
        _d106_notes(p)
        after = _evaluate(_plain_project(45.0), _STEEP)
        assert before.fos == after.fos, (before.fos, after.fos)

    def test_no_note_carries_the_substrings_the_bank_reserves(self):
        """The verification bank greps analysis notes for these, so a new
        sentence containing one would be read as a different finding."""
        for limit in (45.0, 85.0, 90.0):
            for build in (_weak_layer_project, _plain_project):
                for n in _scope_notes(build(limit)):
                    low = n.lower()
                    assert not ("stable" in low and "head" in low), n
                    assert "edge of the search grid" not in low, n
                    assert "path_optimize" not in low, n
