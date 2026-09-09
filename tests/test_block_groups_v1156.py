# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.156 — the Block Search group count reaches the analysis from
the stored model, and the boolean that pretended to gate it is gone.
Defect D07c(b), the last of the four.

**The invariant**: a `.ogr` describes its own run. Every field the file
carries has to reach the analysis, or not be in the file. ``block_num_groups``
reached it; ``block_multiple_groups`` did not, and it was written to every
model ever saved. So a file could say

    "block_multiple_groups": false,
    "block_num_groups": 7

and run SEVEN groups, because the boolean had no reader outside the dialog
that wrote it (`ogr_slip2d/` did not mention it once). Measured through
``build_search`` on the four-layer dyke below, 200 candidates, seed 20260825:

    multiple_groups   num_groups   engine   minimum        valid
    False             7            7        2.070178713    14
    True              7            7        2.070178713    14
    False             3            3        1.318449610    109
    True              3            3        1.318449610    109

The boolean moves nothing at all, and the number it was supposed to govern
moves by 57 %.

**Why it was retired and not wired up**, which is the part that decided the
shape of this file. The obvious repair is ``num_groups = 3 when the boolean is
false``, mirroring the dialog. It was rejected on two counts:

* the name is borrowed and the meaning is not. What the reference calls
  Multiple Groups is a Group ID assigned to each search object THE USER DRAWS,
  with the search run once per group and Number of Surfaces divided equally
  between them. The count is never typed; it emerges from the objects. There
  is no "Number of Groups" field, no published default, and no three anywhere.
  OGR implements none of this: ``BLOCK_SEARCH_OBJECT`` carries no group id and
  every drawn object contributes one vertex to one surface, which is the
  reference's behaviour with NO groups. So "off" has no documented meaning to
  be honoured, and a three would have been invented;
* and it would have replaced the defect with a worse one. Setting
  ``block_num_groups = 7`` from a script is the only way to reach that control
  without a dialog — it is how the reference bank writes its block settings —
  and gating it would have made that assignment a silent no-op unless the
  script also set an undocumented boolean.

So the field is deleted and registered in ``_SHADOW_FIELDS``, where two other
block fields that died the same way already live, and the count it never
governed is asserted here against the engine instead.

**What this file does NOT claim**: that more groups find a lower minimum. That
was measured and is false in both directions; see
``tests/test_block_population_v1135.py``, which owns the identity reused below
— k groups puts exactly k free vertices between the two projected ends, so a
candidate carries k+2. What is new here is the anchor at the settings→engine
boundary, which is where the defect lived and where nothing looked.

COST. Three Block Searches of 150 candidates on a small slope, plus a handful
of note calls that run no search at all. Around four seconds.
"""
from __future__ import annotations
import re
import sys
from dataclasses import asdict, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_search_inequality_v1118 import _layered_slope  # noqa: E402

_NAME = "block_multiple_groups"
_CACHE: dict = {}


def _block_project(groups: int, objects=()):
    """The dyke, told to run a Block Search with this many groups.

    ``objects`` are Block Search objects to draw, as lists of (x, y). One
    drawn object is enough to take the implicit region out of play.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

    p = _layered_slope()
    s = p.settings.search
    s.surface_type = "non_circular"
    s.search_method = "block"
    s.block_num_surfaces = 150
    s.block_num_groups = groups
    for pts in objects:
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(x, y) for x, y in pts],
                              closed=False),
            btype=BoundaryType.BLOCK_SEARCH_OBJECT))
    return p


def _run(groups: int):
    """One search built the way an analysis builds it: from the settings."""
    if groups not in _CACHE:
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.methods.bishop import BishopSimplified

        p = _block_project(groups)
        search = build_search(p, BishopSimplified.METHOD_ID)
        _CACHE[groups] = (search, search.run(p))
    return _CACHE[groups]


# ======================================================================
class TestTheFieldIsGoneAndTheRegistrySaysSo:
    """Retiring a name in this project means three things at once: the
    dataclass loses it, ``_SHADOW_FIELDS`` gains it, and an analysis that
    is handed it anyway refuses instead of ignoring it."""

    def test_it_is_no_longer_a_field(self):
        from ogr_core.project.settings import SearchSettings
        assert _NAME not in {f.name for f in fields(SearchSettings)}

    def test_a_saved_model_stops_carrying_it(self):
        """``to_dict`` is a bare ``asdict``, so the file mirrors the
        dataclass. This is what stops the lie being written again."""
        from ogr_core.project.settings import SearchSettings
        assert _NAME not in asdict(SearchSettings())

    def test_the_registry_holds_it_with_its_own_version(self):
        from ogr_core.project.settings import _SHADOW_FIELDS
        assert _SHADOW_FIELDS[_NAME] == (False, None, "v0.1.156")

    def test_every_entry_carries_a_version(self):
        """The reason the tuple grew: the refusal used to date every
        removal to v0.1.103, which was already wrong for ``path_optimize``.
        """
        from ogr_core.project.settings import _SHADOW_FIELDS
        for name, entry in _SHADOW_FIELDS.items():
            assert len(entry) == 3, (name, entry)
            assert re.fullmatch(r"v\d+\.\d+\.\d+", entry[2]), (name, entry)
        assert _SHADOW_FIELDS["path_optimize"][2] == "v0.1.104"

    def test_an_old_file_loads_and_keeps_the_count_it_declared(self):
        """The point of the whole defect, as a round trip: the boolean
        never governed the number, so dropping it must not touch it."""
        from ogr_core.project.settings import SearchSettings

        s = SearchSettings.from_dict({
            "search_method": "block",
            _NAME: True,
            "block_num_groups": 7,
            "block_num_surfaces": 4321,
        })
        assert not hasattr(s, _NAME)
        assert s.block_num_groups == 7
        assert s.block_num_surfaces == 4321

    def test_the_false_and_seven_combination_is_not_reconciled_either(self):
        """The file the defect described. It ran seven groups before and
        it runs seven groups now — the change removes the contradiction by
        removing the half of it that said nothing, not by moving a number.
        """
        from ogr_core.project.settings import SearchSettings

        s = SearchSettings.from_dict({_NAME: False, "block_num_groups": 7})
        assert s.block_num_groups == 7

    def test_setting_it_from_a_script_refuses_the_analysis(self):
        from ogr_slip2d.analysis_runner import _shadow_setting_problems

        p = _block_project(3)
        assert _shadow_setting_problems(p) == []
        setattr(p.settings.search, _NAME, True)
        problems = _shadow_setting_problems(p)
        assert len(problems) == 1, problems
        assert _NAME in problems[0]
        assert "v0.1.156" in problems[0], problems[0]


# ======================================================================
class TestTheCountReachesTheEngineFromTheSettings:
    """Rule 7 for the control that survives, asserted where the defect
    was: between the stored settings and the search object. Every test
    above this line is about a field that is gone; if the retirement had
    taken the live control with it, only this class would notice."""

    def test_build_search_hands_the_count_over_unchanged(self):
        for groups in (2, 3, 7):
            search, _ = _run(groups)
            assert search.num_groups == groups

    def test_the_count_shapes_the_candidates(self):
        """The identity of ``test_block_population_v1135``, re-anchored on
        searches built from a project rather than constructed by hand: k
        groups puts k free vertices between the two projected ends."""
        for groups in (2, 3, 7):
            _, r = _run(groups)
            counts = {len(e.surface.polyline.vertices) for e in r.evaluations}
            assert counts, groups
            assert max(counts) == groups + 2, (groups, sorted(counts))

    def test_the_count_moves_the_number(self):
        """And not "more groups is lower": the direction is
        model-dependent and was measured in both. All that is claimed is
        that the control does something, from the settings, with no dialog
        anywhere in the path."""
        mins = [round(_run(g)[1].min_fos, 9) for g in (2, 3, 7)]
        assert len(set(mins)) == len(mins), mins


# ======================================================================
class TestTheSilenceTheSurvivingControlStillHad:
    """``block_num_groups`` is read in one branch — the one that tiles
    OGR's implicit region — and that branch runs only when the model draws
    no search object. Which is the ONLY arrangement the reference
    supports, and what all five block models of its bank do. The panel
    therefore showed a live number describing nothing, and nothing said
    so."""

    _OBJ = ((20.0, 5.0), (110.0, 5.0))

    def _notes(self, project):
        from ogr_slip2d.analysis_runner import settings_warnings
        return [n for n in settings_warnings(project, ("bishop_simplified",))
                if "Number of Groups" in n]

    def test_a_drawn_object_gets_the_note(self):
        notes = self._notes(_block_project(3, objects=[self._OBJ]))
        assert len(notes) == 1, notes
        assert "1 Block Search object" in notes[0], notes[0]
        assert "3" in notes[0], notes[0]

    def test_the_note_counts_the_objects(self):
        notes = self._notes(_block_project(5, objects=[
            self._OBJ, ((30.0, 0.0), (100.0, 0.0))]))
        assert len(notes) == 1, notes
        assert "2 Block Search objects" in notes[0], notes[0]

    def test_the_default_count_gets_it_too(self):
        """A three is as much a claim by the panel as a seven, and the
        control is equally inert under both. Firing only on a non-default
        value would leave the bank's own models — every one of which
        stores three — with no word about it."""
        p = _block_project(3, objects=[self._OBJ])
        assert p.settings.search.block_num_groups == 3
        assert self._notes(p)

    def test_no_object_means_no_note(self):
        """Then the count really does configure the run, and saying it
        does nothing would be the opposite error."""
        assert self._notes(_block_project(3)) == []

    def test_another_search_method_gets_no_note(self):
        p = _block_project(3, objects=[self._OBJ])
        p.settings.search.search_method = "path"
        assert self._notes(p) == []


# ======================================================================
class TestTheNoteDoesNotTripTheBanksClosureChecks:
    """The bank decides whether D40 is still closed by reading the TEXT of
    the notes an analysis produces, so three substrings are reserved. The
    ban is wider than it looks: "unstable" contains "stable" and "ahead"
    contains "head". Same tripwire as
    ``tests/test_support_silence_v1155.py``."""

    def _every_note(self):
        from ogr_slip2d.analysis_runner import settings_warnings

        out = []
        for groups, objects in ((3, [TestTheSilenceTheSurvivingControlStillHad
                                     ._OBJ]),
                                (7, [((20.0, 5.0), (110.0, 5.0)),
                                     ((30.0, 0.0), (100.0, 0.0))])):
            out.extend(settings_warnings(_block_project(groups, objects),
                                         ("bishop_simplified",)))
        assert out, "the note stopped being produced"
        return out

    def test_no_note_carries_the_pair_the_bank_reserves_for_d40(self):
        for note in self._every_note():
            assert not ("stable" in note and "head" in note), note

    def test_no_note_carries_the_other_two_reserved_phrases(self):
        for note in self._every_note():
            assert "edge of the search grid" not in note, note
            assert "path_optimize" not in note, note
