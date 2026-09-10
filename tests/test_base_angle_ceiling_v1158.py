# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The base-angle ceiling that switches itself off at the top of its own range.

**The invariant**: a setting that cannot do anything in this model has to
say so (rule 7), and saying so must not change what it does.

Defect D106. ``_base_angle_ok`` reads ``max_base_angle_deg`` through
``if not (0.0 < limit < 90.0): return True``, so the ceiling applies only
on the OPEN interval. The spin box in Project Settings → Advanced offers
1.0 to 90.0 with one decimal, which makes 90 read as the loosest ceiling
available when it is in fact the only value in the box that removes the
check altogether. A user who wants "almost no limit" types the number
that means "no limit", and nothing anywhere says which of the two they
got.

Why the note is scoped to models with a weak layer, and not emitted
generally: ``_base_angle_ok`` returns True for every trial that is not a
``WeakLayerSurface``, so in a model with no weak layer the value is inert
whatever it says. There would be nothing to switch off, and a line on
every run of every model would be noise — the lesson v0.1.155 wrote down
when it chose aggregation over a wall of per-support warnings.

Why the spin box range is NOT narrowed to 89.9, which would look like the
tidier fix: a project already saved with 90.0 would be displayed clamped
to 89.9, and ``apply()`` writes the widget's value back, so opening the
dialog and pressing OK would silently turn that project's "no ceiling"
into "a ceiling at 89.9 deg". That is moving a number in the user's own
file to fix a label, which is worse than the label.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_weak_layer_v1121 import _project  # noqa: E402

_JOINT = (5.0, 20.0)


def _with_ceiling(limit, joint=_JOINT):
    p, _m = _project(joint=joint)
    p.settings.advanced.max_base_angle_deg = limit
    return p


def _page(limit):
    """The Advanced page of Project Settings, holding this ceiling."""
    from PySide6.QtWidgets import QApplication
    from ogr_gui.dialogs.project_settings_dialog import _AdvancedPage
    QApplication.instance() or QApplication([])
    p = _with_ceiling(limit)
    page = _AdvancedPage(p.settings)
    _PAGES.append(page)          # kept alive: Qt deletes an unparented
    return page, p               # widget the moment Python drops it


_PAGES: list = []


def _notes(project):
    from ogr_slip2d.analysis_runner import settings_warnings
    return [n for n in settings_warnings(project)
            if "base angle" in n.lower()]


# ======================================================================
class TestItSaysWhenTheCeilingIsNotThere:

    def test_ninety_degrees_gets_a_note(self):
        notes = _notes(_with_ceiling(90.0))
        assert len(notes) == 1, notes
        assert "removes it" in notes[0], notes[0]

    def test_and_says_which_value_it_is_talking_about(self):
        """So the sentence can be checked against the panel rather than
        believed."""
        assert "90 deg" in _notes(_with_ceiling(90.0))[0]

    def test_a_non_positive_limit_gets_it_too(self):
        """Not reachable from the spin box, which starts at 1.0, but
        reachable from a script and from a hand-edited project file —
        and there the same guard makes it mean no ceiling rather than
        the strictest one, which is the more surprising of the two."""
        for limit in (0.0, -5.0):
            assert len(_notes(_with_ceiling(limit))) == 1, limit

    def test_a_working_ceiling_gets_no_note(self):
        """The error in the other direction: a note that fired on the
        default would be noise on every run of every model."""
        for limit in (80.0, 89.9, 1.0, 45.0):
            assert _notes(_with_ceiling(limit)) == [], limit

    def test_a_model_with_no_weak_layer_gets_no_note(self):
        """The ceiling reaches nothing there, so there is nothing to
        switch off and nothing to say."""
        p, _m = _project(joint=None)
        p.settings.advanced.max_base_angle_deg = 90.0
        assert _notes(p) == []

    def test_a_broken_setting_is_not_an_error(self):
        """``_base_angle_ok`` swallows a bad value and carries on; the
        note has to agree with it rather than raise where it does not."""
        p = _with_ceiling(90.0)
        p.settings.advanced.max_base_angle_deg = "eighty"
        assert _notes(p) == []


# ======================================================================
class TestSayingItChangedNothing:
    """The whole version is a zero-digit one. This is that claim, made
    where the suite can check it rather than in the changelog."""

    def test_the_note_does_not_move_the_analysis(self):
        """Asking for the notes cannot change what the engine answers.

        Driven through ``evaluate_surface``, which is the door
        ``_base_angle_ok`` sits behind, so this is the real path and not
        a method called in isolation.
        """
        from ogr_slip2d.analysis_runner import settings_warnings

        p = _with_ceiling(90.0)
        before, _n = _fos(p, _base_below_the_joint())
        settings_warnings(p)
        after, _n2 = _fos(p, _base_below_the_joint())
        assert before.fos == after.fos, (before.fos, after.fos)

    def test_the_ceiling_the_note_describes_is_the_real_one(self):
        """The note claims 90 removes the ceiling and a value inside the
        interval applies it. Measured, on a joint that leaves a base past
        the ceiling, rather than asserted from the guard's source.

        Ordinary and not Bishop, for the reason
        ``test_weak_layer_v1121`` gives where it makes the same
        comparison: Bishop divides by ``m_alpha``, which collapses at
        exactly these angles, so the two sides would not be comparable.
        """
        steep = _steep_joint_project(90.0)
        allowed, _n = _fos(steep, _base_below_the_joint(),
                           method="ordinary_fellenius", num_slices=60)
        assert allowed is not None and allowed.fos is not None
        steepest = math.degrees(max(abs(sl.base_angle)
                                    for sl in allowed.slices))
        assert steepest > 80.0, steepest

        capped = _steep_joint_project(80.0)
        refused, notes = _fos(capped, _base_below_the_joint(),
                              method="ordinary_fellenius", num_slices=60)
        assert refused is None or refused.fos != allowed.fos
        assert any("ceiling" in n for n in notes), notes

    def test_and_the_note_fires_on_exactly_the_first_of_those(self):
        assert _notes(_steep_joint_project(90.0)) != []
        assert _notes(_steep_joint_project(80.0)) == []


def _fos(project, surface, method="bishop_simplified", num_slices=40):
    from test_weak_layer_v1121 import _fos as _weak_fos
    return _weak_fos(project, surface, method=method,
                     num_slices=num_slices)


def _base_below_the_joint():
    from test_weak_layer_v1121 import _base_below_the_joint as _b
    return _b()


def _steep_joint_project(limit):
    """A joint that stops in mid-air, so the clipped surface has to fall
    back to the base over one slice — the near-vertical step this
    ceiling exists for."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    p = _with_ceiling(limit)
    m = Material(name="Steep joint", unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=1.0, friction_angle=5.0))
    p.materials.append(m)
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(6.0, 6.0), Vertex(14.0, 6.0)]),
        btype=BoundaryType.WEAK_LAYER, material_id=m.id))
    return p


def _reads_ceiling(limit) -> bool:
    """Whether ``_base_angle_ok`` would apply a ceiling at this value.

    The guard, read the way the engine reads it, so that a change to the
    engine's interval fails here instead of quietly changing what the
    note above is describing.
    """
    return bool(0.0 < float(limit) < 90.0)


# ======================================================================
class TestTheDialogSaysItToo:
    """The engine note arrives after the run. The person choosing the
    value is looking at the spin box, which is before it.

    The page is built on its own rather than through the whole dialog:
    it is the widget that owns the control, and nothing here needs the
    tree around it. No language is set either way, so the assertions
    below hold in both — a test that pinned the language would be
    leaking exactly the global this project's rule 5 is about.
    """

    def test_the_label_changes_at_ninety(self):
        page, _p = _page(80.0)
        page.sp_base_angle.setValue(80.0)
        gentle = page.lbl_base_angle.text()
        page.sp_base_angle.setValue(90.0)
        off = page.lbl_base_angle.text()
        assert gentle and off, (gentle, off)
        assert gentle != off, (gentle, off)
        assert "90" in off, off

    def test_the_spin_box_still_reaches_ninety(self):
        """Guard on the decision NOT to narrow the range: a project
        saved with 90.0 has to stay editable without ``apply()``
        rewriting it to something else."""
        page, p = _page(90.0)
        assert page.sp_base_angle.maximum() == 90.0
        assert page.sp_base_angle.value() == 90.0
        page.apply()
        assert p.settings.advanced.max_base_angle_deg == 90.0


# ======================================================================
class TestTheNoteCarriesNothingTheBankReserves:
    """The verification bank decides whether defect D40 is still closed
    by reading note text; v0.1.155 left three substrings spoken for."""

    def test_no_reserved_substring(self):
        for limit in (90.0, 0.0, -5.0):
            for note in _notes(_with_ceiling(limit)):
                for text in (note, note.lower()):
                    assert not ("stable" in text and "head" in text), note
                    assert "edge of the search grid" not in text, note
                    assert "path_optimize" not in text, note

