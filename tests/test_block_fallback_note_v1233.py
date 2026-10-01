# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.233 — a Block Search with no object drawn says that its
sampling region is the program's choice. Defect D100; and the two
situations in which Multiple Groups does nothing, which rule 7 asks to be
said (D99).

**The invariant**: a run whose geometry was decided by the program, not by
the model, says so. The reference is explicit that «a Block Search requires
at least one Block Search Object to be defined by the user» and offers no
fallback. OGR does have one — a box over the slope face tiled into
``block_num_groups`` vertical bands, one random vertex in each — and its
four fractions cannot be calibrated against anything, since the reference
has no counterpart. Until v0.1.233 the panel showed that count as «Number
of Groups», the reference's name for a different feature, and a run with no
objects said nothing at all; 0.1.156 had written only the other half of the
note (objects drawn: the count does nothing), because that was all D07c(b)
asked for.

What is asserted:

* (a) no object drawn → one note, naming the program's choice, the band
  count of this model and the reference's requirement;
* (b) objects drawn → the 0.1.156 note instead, under the count's new label;
* (c) Multiple Groups on with no object, or with every object in one group
  → a note that the box does nothing here; with distinct ids → no such note;
* (d) none of the notes carries a substring the bank reserves for its own
  closure checks («stable» together with «head», «edge of the search grid»,
  «path_optimize»);
* (e) the panel shows the count as «Implicit Region Bands», with a tooltip
  that says it only acts with nothing drawn.

COST. No search is run: only ``settings_warnings`` on small models, and one
dialog.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _model(objects=(), multiple=False, ids=None, bands=3):
    """A small slope with a Block Search and these objects (lists of x, y)."""
    from ogr_core.geometry import (BlockObjectKind, BlockObjectSpec, Boundary,
                                   BoundaryType, Polyline, Vertex)
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("D100")
    ext = Polyline(vertices=[Vertex(*v) for v in (
        (0, 0), (100, 0), (100, 30), (60, 30), (40, 20), (0, 20))],
        closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="soil", unit_weight=19.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    for k, pts in enumerate(objects):
        b = Boundary(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False),
            btype=BoundaryType.BLOCK_SEARCH_OBJECT)
        if ids is not None:
            b.block_object = BlockObjectSpec(BlockObjectKind.LINE,
                                             group_id=ids[k])
        p.add_boundary(b)
    s = p.settings.search
    s.surface_type = "non_circular"
    s.search_method = "block"
    s.block_num_groups = bands
    s.block_multiple_groups = multiple
    return p


def _notes(project):
    from ogr_slip2d.analysis_runner import settings_warnings
    return settings_warnings(project, ("bishop_simplified",))


_LINE_A = ((20.0, 10.0), (35.0, 10.0))
_LINE_B = ((50.0, 12.0), (70.0, 12.0))


# ======================================================================
class TestNoObjectSaysTheRegionIsTheProgramsChoice:

    def test_the_note_fires_once(self):
        notes = [n for n in _notes(_model(bands=5))
                 if "No Block Search object is drawn" in n]
        assert len(notes) == 1, notes

    def test_it_names_the_choice_the_count_and_the_reference(self):
        note = next(n for n in _notes(_model(bands=5))
                    if "No Block Search object is drawn" in n)
        assert "chosen by the program" in note, note
        assert "5 vertical band(s)" in note, note
        assert "Implicit Region Bands" in note, note
        assert "requires at least one Block Search object" in note, note

    def test_it_does_not_say_the_count_does_nothing(self):
        """Here the count DOES configure the run: the opposite claim would
        be the opposite error."""
        for n in _notes(_model()):
            assert "configures nothing" not in n, n

    def test_another_search_method_gets_no_note(self):
        p = _model()
        p.settings.search.search_method = "path"
        assert not [n for n in _notes(p) if "Block Search" in n]


class TestWithObjectsTheOtherHalf:

    def test_the_0_1_156_note_under_the_new_label(self):
        notes = [n for n in _notes(_model([_LINE_A]))
                 if "Implicit Region Bands" in n]
        assert len(notes) == 1, notes
        assert "configures nothing" in notes[0], notes[0]
        assert not [n for n in _notes(_model([_LINE_A]))
                    if "No Block Search object is drawn" in n]


class TestWhenMultipleGroupsDoesNothing:

    @staticmethod
    def _group_notes(p):
        return [n for n in _notes(p) if "Multiple Groups is on" in n]

    def test_on_with_no_object(self):
        notes = self._group_notes(_model(multiple=True))
        assert len(notes) == 1 and "no Block Search object" in notes[0], notes

    def test_on_with_one_group(self):
        notes = self._group_notes(_model([_LINE_A, _LINE_B], multiple=True,
                                         ids=(6, 6)))
        assert len(notes) == 1 and "Group ID 6" in notes[0], notes

    def test_on_with_two_groups_says_nothing(self):
        assert self._group_notes(_model([_LINE_A, _LINE_B], multiple=True,
                                        ids=(1, 2))) == []

    def test_off_says_nothing(self):
        assert self._group_notes(_model([_LINE_A, _LINE_B],
                                        ids=(1, 2))) == []


class TestTheNotesDoNotTripTheBanksClosureChecks:
    """The bank reads the text of these notes to decide some closures, so
    three substrings are reserved: «stable» with «head» («unstable» and
    «ahead» count), «edge of the search grid» and «path_optimize»."""

    def _every_note(self):
        out = []
        for p in (_model(), _model(multiple=True), _model([_LINE_A]),
                  _model([_LINE_A, _LINE_B], multiple=True, ids=(6, 6)),
                  _model([_LINE_A, _LINE_B], multiple=True, ids=(1, 2))):
            out.extend(_notes(p))
        assert out
        return out

    def test_no_reserved_pair(self):
        for note in self._every_note():
            assert not ("stable" in note and "head" in note), note

    def test_no_other_reserved_phrase(self):
        for note in self._every_note():
            assert "edge of the search grid" not in note, note
            assert "path_optimize" not in note, note


@_requires_qt
class TestThePanelSaysWhatTheCountIs:

    def test_the_label_and_the_tooltip(self):
        """Read in English, set here and put back on the way out: the
        language is global, and rule 5 forbids both depending on what an
        earlier test left and leaving something for a later one."""
        from ogr_gui.i18n import current_language, set_language
        prev = current_language()
        set_language("en")
        try:
            self._check()
        finally:
            set_language(prev)

    @staticmethod
    def _check():
        from PySide6.QtWidgets import QFormLayout, QLabel
        from ogr_gui.dialogs import SurfaceOptionsDialog
        QApplication.instance() or QApplication([])
        d = SurfaceOptionsDialog(_model())
        labels = []
        for form in d.findChildren(QFormLayout):
            for row in range(form.rowCount()):
                item = form.itemAt(row, QFormLayout.LabelRole)
                field = form.itemAt(row, QFormLayout.FieldRole)
                if (item is not None and isinstance(item.widget(), QLabel)
                        and field is not None
                        and field.widget() is d._b_groups):
                    labels.append(item.widget().text())
        assert labels == ["Implicit Region Bands:"], labels
        tip = d._b_groups.toolTip()
        assert "no Block Search object is drawn" in tip, tip
        assert "Number of Groups" not in tip, tip
