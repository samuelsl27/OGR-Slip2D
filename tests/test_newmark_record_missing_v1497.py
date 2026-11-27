# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.497 (D440) — a Newmark run whose chosen record is not in the project
says so, with the id, and does not say that no record is chosen.

The invariant: the seismic notes of a run (``_seismic_lines``, the rule of
``run_analysis`` and of ``evaluate_surfaces``, D406) tell apart the two ways
of having no record to integrate:

* ``record_id`` empty — nothing is chosen: ``method.newmark_no_record``, as
  since v0.1.127, its English unchanged;
* ``record_id`` set and the project has no record with it —
  ``method.newmark_record_missing``, which names the id. Until this version
  both gave the first sentence, «no seismic record is selected», for a
  selection that was there (measured with 0.1.485 and 0.1.496 on the plane
  of ``test_newmark_user_surfaces_v1429`` with ``record_id = "nope"``: the
  bench's ``medir_d439_d440.py``).

And the id moves the note (rule 7): with the project's own record neither
note is said, and the plane gets its displacement. No number changes: with
a missing record nothing is integrated, as before.

Only a hand-edited ``.ogr`` reaches the missing case: deleting a record in
the window or with ``seismic_record_delete`` clears the choice
(``ogr_core.project.rules.set_seismic_records``), and ``settings_set``
refuses an id the project does not have. Measured with 0.1.496 too, and left
as it is: ``project_validate`` says nothing of it, and the Project Settings
window shows «(none)» and writes the empty id back on OK.

Cost: six runs of the 60-slice plane of v1429, a few hundredths each.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_METHOD = "janbu_simplified"
_MISSING = "method.newmark_record_missing"
_NONE = "method.newmark_no_record"
_RUNS: dict = {}


def _project(record_id):
    """The plane of v1429 with its record, and ``record_id`` as given
    (``None``: the record's own id)."""
    from test_newmark_user_surfaces_v1429 import _plane_project
    p = _plane_project()
    if record_id is not None:
        p.settings.seismic.record_id = record_id
    return p


def _doors(record_id):
    """``(run outcome, evaluate_surfaces outcome)`` for ``record_id``."""
    if record_id not in _RUNS:
        from test_surface_evaluate_seismic_v1451 import _surface

        from ogr_slip2d.analysis_runner import evaluate_surfaces, run_analysis
        _RUNS[record_id] = (
            run_analysis(_project(record_id)),
            evaluate_surfaces(_project(record_id), _surface(), [_METHOD]))
    return _RUNS[record_id]


def _notes(warnings) -> list:
    """``(code, args)`` of the method notes among ``warnings``."""
    from ogr_core.messages import parts
    out = []
    for w in warnings:
        code, args, _english = parts(w)
        if code == "note.method":
            note = args.get("note") or {}
            out.append((note.get("code"), note.get("args") or {}))
    return out


def _codes(warnings) -> list:
    return [c for c, _a in _notes(warnings)]


class TestARecordThatIsNotThere:

    def test_the_run_names_the_missing_id(self):
        run, _one = _doors("nope")
        notes = dict(_notes(run.warnings))
        assert _MISSING in notes, _codes(run.warnings)
        assert notes[_MISSING]["record_id"] == "nope"
        assert _NONE not in notes
        text = [str(w) for w in run.warnings if "nope" in str(w)]
        assert text, run.warnings

    def test_evaluate_surfaces_says_the_same(self):
        _run, one = _doors("nope")
        codes = _codes(one.warnings)
        assert _MISSING in codes and _NONE not in codes, codes

    def test_nothing_is_integrated(self):
        run, one = _doors("nope")
        for res in (run.results[_METHOD].critical, one.results[_METHOD]):
            assert res is not None
            assert "newmark_displacement" not in (res.details or {})
            assert res.details["ky"] is not None


class TestTheOtherTwoCases:

    def test_an_empty_id_is_none_selected(self):
        run, one = _doors("")
        for out in (run, one):
            codes = _codes(out.warnings)
            assert _NONE in codes and _MISSING not in codes, codes

    def test_the_projects_own_record_gives_neither(self):
        """Rule 7: the id moves the note, and with the right one the plane
        moves."""
        run, one = _doors(None)
        for out in (run, one):
            codes = _codes(out.warnings)
            assert _NONE not in codes and _MISSING not in codes, codes
        crit = run.results[_METHOD].critical
        assert crit.details["newmark_displacement"] > 0.0

    def test_the_missing_note_says_itself_in_spanish(self):
        from ogr_gui.core_messages import note_line
        from ogr_gui.i18n import current_language, set_language
        run, _one = _doors("nope")
        line = next(w for w in run.warnings
                    if _MISSING in _codes([w]))
        before = current_language()
        try:
            set_language("es")
            text = note_line(line)
        finally:
            set_language(before)
        assert "«nope»" in text and "no tiene ningún registro" in text, text
