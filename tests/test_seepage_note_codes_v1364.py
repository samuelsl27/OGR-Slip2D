# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.364 (D342) — a saved groundwater field keeps the codes of its notes, so
*Interpret Groundwater* says them in Spanish after the file is opened, as it
does for the field just computed.

The finding (2026-10-21, while making 0.1.352): since that version the
solver's notes carry a code (``ogr_fem2d/messages.py``), but
``SeepageResult.to_dict`` wrote each one as its English sentence and
``from_dict`` read it back as a ``str``. Measured: a ``seepage.stage_steps``
note with ``k = 1``, through ``to_dict`` → JSON → ``from_dict``, came back as
``str`` with no code, and ``note_text`` in Spanish gave the English.

The format (the ticket's step 4): the sentence stays where it was, in
``notes``, because older versions, the API, the tests and the bank read it;
the code and the values go beside it, in ``note_codes``, and ONLY when a note
has a code. A key written always would change the fingerprint of every saved
field (``model_hash`` hashes ``to_dict``, and the bank's ``modelo_huella``
hashes the ``.ogr``).

What these tests protect:

* the reproduction of the ticket comes back as a ``Coded`` with its code and
  its values, and the English in the file is the English of before;
* a nested reason (``initial_failed_why``) and a non-finite value come back
  too, the latter as a float, so the Spanish template formats it;
* a field without coded notes is written exactly as before, with no new key,
  and a dictionary without the key (an older file) reads as it always did;
* the transient's stages and its initial state keep theirs, through
  ``Project.to_dict``/``from_dict``;
* through ``Project.save``/``load`` and ``InterpretGroundwaterWindow._summary``,
  the notes are said in Spanish after opening the file.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


def _round_trip(result):
    from ogr_fem2d.solvers import SeepageResult
    return SeepageResult.from_dict(json.loads(json.dumps(result.to_dict())))


def _result(**notes):
    from ogr_fem2d.solvers import SeepageResult
    r = SeepageResult()
    r.total_head = [1.0]
    r.notes.update(notes)
    return r


# ======================================================================
class TestTheCodeComesBack:

    def test_the_reproduction_of_the_ticket(self):
        from ogr_core.messages import Coded
        from ogr_fem2d import messages as M
        note = M.seepage_note(M.STAGE_STEPS, k=1)
        back = _round_trip(_result(warning=note)).notes["warning"]
        assert isinstance(back, Coded), type(back)
        assert back.code == "seepage.stage_steps"
        assert back.args == {"k": 1}
        assert back == note

    def test_the_english_in_the_file_is_the_english_of_before(self):
        from ogr_fem2d import messages as M
        note = M.seepage_note(M.STAGE_STEPS, k=1)
        d = _result(warning=note).to_dict()
        assert d["notes"]["warning"] == (
            "stage 1: some time steps did not converge; try more time steps "
            "or more Picard iterations per step")
        assert type(json.loads(json.dumps(d))["notes"]["warning"]) is str
        assert d["note_codes"] == {"warning": {"code": "seepage.stage_steps",
                                               "args": {"k": 1}}}

    def test_a_nested_reason(self):
        from ogr_core.messages import as_nested
        from ogr_fem2d import messages as M
        from ogr_gui.core_messages import note_text
        note = M.seepage_note(M.INITIAL_FAILED_WHY,
                              why=as_nested(M.seepage_note(M.NO_DIRICHLET)))
        back = _round_trip(_result(error=note)).notes["error"]
        assert back.code == note.code and back.args == note.args
        with _Spanish():
            said, was = note_text(back), note_text(note)
        assert said == was and said != str(note), said
        assert "Dirichlet" in said and said.startswith("falló"), said

    def test_a_value_that_is_not_finite(self):
        """json_args writes NaN as "nan"; read back as a string, the
        template's ``{change:.3e}`` would not format it and the note would
        fall back on its English."""
        from ogr_fem2d import messages as M
        from ogr_gui.core_messages import note_text
        note = M.seepage_note(M.PICARD_NO_RESCUE, steps=200,
                              change=float("nan"))
        d = _result(warning=note).to_dict()
        assert d["note_codes"]["warning"]["args"]["change"] == "nan"
        json.dumps(d, allow_nan=False)          # the .ogr stays pure JSON
        back = _round_trip(_result(warning=note)).notes["warning"]
        assert math.isnan(back.args["change"])
        with _Spanish():
            said, was = note_text(back), note_text(note)
        assert said == was and said != str(note), said

    def test_the_inverse_of_json_args(self):
        from ogr_core.messages import args_from_json, json_args
        args = {"a": math.inf, "b": -math.inf, "c": 2.5, "d": "text",
                "e": {"code": "x", "args": {"f": math.inf}, "text": "t"},
                "g": [1, math.inf]}
        back = args_from_json(json.loads(json.dumps(json_args(args))))
        assert back["a"] == math.inf and back["b"] == -math.inf
        assert back["c"] == 2.5 and back["d"] == "text"
        assert back["e"]["args"]["f"] == math.inf
        assert back["g"] == [1, math.inf]


# ======================================================================
class TestWhatDoesNotChange:

    def test_a_field_without_coded_notes_writes_no_new_key(self):
        """The fingerprints of every field saved so far stay as they were."""
        d = _result(time=3600.0, label="1 h", warning="a plain note").to_dict()
        assert "note_codes" not in d, d

    def test_an_older_file_reads_as_it_always_did(self):
        from ogr_fem2d.solvers import SeepageResult
        d = {"schema": 1, "total_head": [1.0], "gamma_w": 9.81,
             "seepage_nodes": [], "converged": True, "iterations": 3,
             "notes": {"warning": "stage 1: some time steps did not "
                                  "converge; try more time steps or more "
                                  "Picard iterations per step"}}
        r = SeepageResult.from_dict(d)
        assert type(r.notes["warning"]) is str
        assert r.notes == d["notes"]
        assert r.converged and r.iterations == 3

    def test_a_code_for_a_note_the_file_does_not_have_is_ignored(self):
        from ogr_fem2d.solvers import SeepageResult
        r = SeepageResult.from_dict({
            "total_head": [1.0], "notes": {},
            "note_codes": {"warning": {"code": "seepage.stage_steps",
                                       "args": {"k": 1}}}})
        assert r.notes == {}


# ======================================================================
def _seepage_project():
    """The rectangle of ``test_seepage_run_notes_v1352``, solved, with heads
    on its two sides."""
    import test_seepage_run_notes_v1352 as srn
    from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
    p = srn._seepage_project(transient=False)
    bcs = SeepageBoundaryConditions()
    for nid in sorted(p.fem_mesh.boundary_node_ids()):
        nd = p.fem_mesh.nodes[nid]
        if abs(nd.x) < 1e-9:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 6.0)
        elif abs(nd.x - srn._W) < 1e-9:
            bcs.add_node(nid, BCType.TOTAL_HEAD, 3.0)
    p.seepage_bcs = bcs
    return p


class TestThroughTheFile:

    def test_the_transient_stages_and_the_initial_state(self):
        from ogr_core.project import Project
        from ogr_fem2d import messages as M
        from ogr_fem2d.solvers import SeepageResult
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = _seepage_project()
        steady = solve_project_groundwater(p)
        assert steady.total_head
        stage = SeepageResult.from_dict(steady.to_dict())
        stage.notes["warning"] = M.seepage_note(M.STAGE_STEPS, k=2)
        stage.notes["fos_warning"] = RM.run_note(RM.TRANSIENT_NO_COUPLING)
        start = SeepageResult.from_dict(steady.to_dict())
        start.notes["initial_state_warning"] = M.seepage_note(
            M.INITIAL_NOT_CONVERGED)
        p.transient_results = [stage]
        p.transient_initial_result = start
        q = Project.from_dict(json.loads(json.dumps(p.to_dict())))
        got = q.transient_results[0].notes
        assert got["warning"].code == "seepage.stage_steps"
        assert got["warning"].args == {"k": 2}
        assert got["fos_warning"].code == "run.transient_no_coupling"
        init = q.transient_initial_result.notes["initial_state_warning"]
        assert init.code == "seepage.initial_not_converged"

    def test_interpret_groundwater_says_them_in_spanish_after_opening(self):
        from types import SimpleNamespace as NS

        from PySide6.QtWidgets import QLabel

        from ogr_core.project import Project
        from ogr_fem2d import messages as M
        from ogr_gui.interpret_groundwater_window import (
            InterpretGroundwaterWindow)
        from ogr_slip2d.transient_stability import solve_project_groundwater
        _app()
        p = _seepage_project()
        r = solve_project_groundwater(p)
        assert r.total_head
        r.notes["warning"] = M.seepage_note(M.STAGE_STEPS, k=1)
        r.notes["mesh_warning"] = M.seepage_note(M.MESH_FLAT, n=2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "campo.ogr"
            p.save(path)
            q = Project.load(path)
        host = NS(result=q.seepage_result, status=QLabel())
        with _Spanish():
            InterpretGroundwaterWindow._summary(host)
        text = host.status.text()
        assert "etapa 1: algunos pasos de tiempo no convergieron" in text, text
        assert "la malla tiene 2 elemento(s) plano(s)" in text, text
        assert "stage 1" not in text and "flat element" not in text, text
