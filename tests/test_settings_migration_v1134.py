# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.134 — reopening a pre-v0.1.103 model says which angle
changed meaning, and says it about the field the engine actually reads.

**The invariant**: v0.1.103 moved the Path Search *Initial Angle at Toe*
from the search's own toe-to-crest frame to ABSOLUTE degrees measured
counter-clockwise from +x. The value is deliberately NOT converted — the
conversion needs the failure direction, which is a property of the
project and not of the settings block — so the only honest thing left is
to say so. This file pins WHEN that is said.

Why it needed its own version: the note added in v0.1.103 watched the
RETIRED twin (``path_min_angle_deg``), and that is the wrong field. The
pre-v0.1.103 dialog wrote BOTH names from one spin box — the survivor got
the typed value ``v``, the twin got ``-abs(v)`` — so

  * the twin holds no information the survivor lacks, and the number that
    reaches the engine today is the survivor's, written in the old frame
    and read in the new one;
  * the twin's own default is −45, the mirror of the box's default 45, so
    a user who ticked the box and left it alone stored the twin at exactly
    its default and got NO warning at all. That is the case this file
    exists for, and it is the commonest one.

Measured while writing it, on ``02_Slide2_Problema079/modelo_1_path.ogr``
(Path Search, Bishop simplified, crest on the right): reading the stored
45° as absolute yields ZERO valid surfaces, while the converted −45°
reproduces the run digit for digit (FS 1.252165634249679, 391 valid).
The failure is loud rather than silent on that model, but "no result at
all" is still not what the file asked for.

Rule 7 in the reverse direction: a setting that no longer means what it
meant must not go on being applied without a word.
"""
from __future__ import annotations


def _s(**stored):
    """A settings block as it comes out of a stored .ogr file."""
    from ogr_core.project.settings import SearchSettings
    return SearchSettings.from_dict(dict(search_method="path", **stored))


def _pre_v1103(typed, enabled=True, side="lower"):
    """What the v0.1.102 dialog wrote for one Initial Angle at Toe.

    Verbatim from ``grid_dialogs.py`` at that version: the survivor takes
    the spin box value, and the retired twin takes ``-abs(...)`` for the
    lower angle and ``+abs(...)`` for the upper one, written only when the
    box was ticked.
    """
    stored = {
        f"path_initial_angle_at_toe_{side}_deg": typed,
        f"path_initial_angle_at_toe_{side}_enabled": enabled,
    }
    if enabled:
        if side == "lower":
            stored["path_min_angle_deg"] = -abs(typed)
        else:
            stored["path_max_angle_deg"] = abs(typed)
    else:
        # The file still carries the twin at its default: every model ever
        # saved before v0.1.103 has the key, ticked or not.
        stored["path_min_angle_deg"] = -45.0
    return stored


def _angle_notes(settings):
    return [n for n in settings._migration_notes
            if "Initial Angle at Toe" in n]


class TestThePreV1103FileIsRecognisedByItsKeys:
    """The marker is the PRESENCE of a retired name, never its value."""

    def test_the_commonest_case_used_to_pass_in_silence(self):
        """Ticked the box, left it at its own default 45.

        The twin then lands on −45, which IS its default, so the v0.1.103
        note never fired — while the engine went on reading 45 in a frame
        that had changed underneath it. This is the whole reason for the
        version.
        """
        s = _s(**_pre_v1103(45.0))
        notes = _angle_notes(s)
        assert len(notes) == 1
        assert "45" in notes[0]
        assert "ABSOLUTE" in notes[0]

    def test_a_value_that_departs_from_the_default_also_speaks(self):
        s = _s(**_pre_v1103(30.0))
        assert len(_angle_notes(s)) == 1

    def test_exactly_one_note_per_angle_not_two(self):
        """The retired twin adds nothing once the survivor is switched on:
        its number is just the mirror of the survivor's. Saying it twice
        would train the reader to skip both."""
        s = _s(**_pre_v1103(30.0))
        assert len(s._migration_notes) == 1
        # And it is the one that talks about the field the engine reads,
        # not the one that talks about the discarded twin.
        assert "Initial Angle at Toe" in s._migration_notes[0]

    def test_an_angle_that_was_never_switched_on_says_nothing(self):
        """Nothing is applied, so there is nothing to mistrust."""
        s = _s(**_pre_v1103(45.0, enabled=False))
        assert s._migration_notes == []

    def test_the_upper_angle_gets_its_own_note(self):
        s = _s(**_pre_v1103(20.0, side="upper"))
        notes = _angle_notes(s)
        assert len(notes) == 1
        assert "upper" in notes[0]

    def test_a_file_written_after_v1103_never_warns(self):
        """No retired key, so the stored number is already absolute and
        means exactly what it says. Warning here would be noise on every
        project the user has."""
        s = _s(path_initial_angle_at_toe_lower_deg=30.0,
               path_initial_angle_at_toe_lower_enabled=True)
        assert s._migration_notes == []


class TestTheWarningDoesNotBecomeAConversion:
    """v0.1.103 decided not to guess, and this version does not undo it."""

    def test_the_stored_value_is_left_exactly_as_it_was(self):
        s = _s(**_pre_v1103(30.0))
        assert s.path_initial_angle_at_toe_lower_deg == 30.0
        assert s.path_initial_angle_at_toe_lower_enabled is True

    def test_the_retired_name_never_travels_back_out(self):
        from dataclasses import asdict
        s = _s(**_pre_v1103(30.0))
        assert "path_min_angle_deg" not in asdict(s)
        assert "_migration_notes" not in asdict(s)

    def test_the_two_frames_really_do_disagree(self):
        """The reason a warning is owed at all.

        The reference states the equivalence as a user-facing rule — an
        angle for a right-to-left slope equals 180 minus it for a
        left-to-right one — and ``toe_frame_angle_deg`` is that rule. What
        matters here is only that the old stored number and the new
        reading of it are NOT the same limit, whichever way the slope
        faces; if they were, the note would be noise.
        """
        from ogr_slip2d.search import toe_frame_angle_deg
        for to_right in (True, False):
            for typed in (5.0, 30.0, 45.0, 60.0):
                now = toe_frame_angle_deg(typed, to_right)
                then = -abs(typed)          # what v0.1.102 fed the generator
                assert now != then


class TestTheModelsKeptInTheRepository:
    """Every stored model carries the retired keys at their defaults with
    both angles switched off, so none of them can warn and none of them
    can move. If one ever does, the comparison bank moves with it."""

    def test_no_stored_model_triggers_the_new_note(self):
        from pathlib import Path

        from ogr_core.project import Project
        root = Path(__file__).resolve().parent.parent / "validacion" / "casos"
        models = sorted(root.glob("*/modelo.ogr"))
        assert models, "no stored models to check the migration against"
        for m in models:
            project = Project.load(str(m))
            assert _angle_notes(project.settings.search) == [], m.name
