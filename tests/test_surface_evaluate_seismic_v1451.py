# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D406 (v0.1.451) — the door for one surface gives what the run gives for it
under the seismic modes.

The invariant
-------------
``evaluate_surfaces`` (the door of ``surface_evaluate`` in the API and the
MCP server) says in its docstring that it goes through exactly what
``run_analysis`` goes through. Under "Compute Ky" and Newmark it computed the
Ky (``_solve_ky``) and stopped: no Newmark displacement, and none of the
five notes the run gives (no record chosen, a record that cannot be
integrated, an unknown polarity, a kh the Ky replaces, a surface with no
Ky). Measured with 0.1.450 on the demo slope with a user's polyline and a
0.3 g sinusoid: the run gave 0.3475 m and the door nothing; with kh = 0.10
and no record, the run said both things and the door neither. Now both doors
ask one rule (``analysis_runner._seismic_lines``), so for the same surface
they give the same Ky and the same displacement, to the last bit, and the
same notes.

The reference (rule 1)
----------------------
Newmark (1965), on the plane of ``test_newmark_user_surfaces_v1429`` (the
user's two-vertex plane of dry sand at 30 degrees, Janbu): the Ky of a rigid
block on a plane, tan(φ − β), and the displacement of the single rectangular
pulse of 0.5 g for 1 s at that Ky, u = V²/(2gN)·(1 − N/A), both to 1e-6 (the
residue measured by the prompt: 2.4e-8 on the displacement). The two doors
against each other are an identity, compared with ``float.hex`` in the
engine; the API's JSON rounds to six decimals (``ogr_api.results._r``), so
there the comparison is to that rounding.

Measured cost: about 2 s, a few runs of a 60-slice plane, each computed once
for the file.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_METHOD = "janbu_simplified"
_RUNS: dict = {}


def _project(case):
    """The plane of 0.1.429 in ``case``: "pulse" (Newmark with the pulse),
    "no_record", "kh" (kh = 0.10 and no record), "strong" (c = 500 kPa: no
    Ky below the ceiling) or "static" (no seismic mode)."""
    from test_newmark_user_surfaces_v1429 import _STRONG_C, _plane_project
    p = _plane_project(cohesion=_STRONG_C if case == "strong" else 0.0)
    if case in ("no_record", "kh"):
        # v0.1.497 (D440) -- through the program's rule, which clears the
        # choice: emptying the list by hand left ``record_id`` pointing at a
        # record no longer there, which is D440's case and has its own note
        from ogr_core.project.rules import set_seismic_records
        set_seismic_records(p, [])
    if case == "kh":
        p.seismic.enabled, p.seismic.kh = True, 0.10
    if case == "static":
        p.settings.seismic.newmark = False
        p.settings.seismic.compute_ky = False
        p.seismic.enabled = False
    return p


def _surface():
    """The plane as the API builds it from its JSON spec."""
    from test_newmark_user_surfaces_v1429 import _PLANE

    from ogr_api.ops.analysis import surface_from_spec
    return surface_from_spec({"type": "polyline", "points": list(_PLANE)})


def _doors(case):
    """``(run outcome, evaluate_surfaces outcome)`` of ``case``, once."""
    if case not in _RUNS:
        from ogr_slip2d.analysis_runner import evaluate_surfaces, run_analysis
        run = run_analysis(_project(case))
        one = evaluate_surfaces(_project(case), _surface(), [_METHOD])
        _RUNS[case] = (run, one)
    return _RUNS[case]


def _codes(warnings) -> list:
    """The codes of the method notes among ``warnings``, in order."""
    from ogr_api.results import with_warning_codes
    out = []
    # the key is there only when some warning carries a code
    for c in with_warning_codes({"warnings": list(warnings)}).get(
            "warning_codes", []):
        if c["code"] == "note.method":
            out.append(c["args"]["note"]["code"])
    return out


_SEISMIC = ("method.newmark_no_record", "method.newmark_unusable",
            "method.newmark_polarity", "method.seismic_kh_replaced",
            "method.seismic_no_ky")


# ======================================================================
class TestTheDisplacement:

    def test_the_premise_the_runs_critical_is_the_plane(self):
        run, _one = _doors("pulse")
        sr = run.results[_METHOD]
        assert sr.is_user_surface(sr.critical)

    def test_both_doors_give_the_same_ky_and_displacement_to_the_bit(self):
        run, one = _doors("pulse")
        crit, given = run.results[_METHOD].critical, one.results[_METHOD]
        assert float.hex(given.details["ky"]) == \
            float.hex(crit.details["ky"])
        assert "newmark_displacement" in given.details, given.details
        assert float.hex(given.details["newmark_displacement"]) == \
            float.hex(crit.details["newmark_displacement"])

    def test_against_newmark_1965(self):
        from test_newmark_user_surfaces_v1429 import (_A, _KY_EXACT, _T0,
                                                      _closed_form)
        _run, one = _doors("pulse")
        given = one.results[_METHOD]
        ky = given.details["ky"]
        assert abs(ky - _KY_EXACT) <= 1e-6, (ky, _KY_EXACT)
        u = _closed_form(_A, ky, _T0)
        moved = given.details.get("newmark_displacement")
        assert moved is not None and abs(moved - u) <= 1e-6 * u, (moved, u)

    def test_the_api_returns_it(self):
        from ogr_api import Workspace, call
        from test_newmark_user_surfaces_v1429 import _PLANE
        run, _one = _doors("pulse")
        engine = run.results[_METHOD].critical.details[
            "newmark_displacement"]
        ws = Workspace()
        try:
            pid = ws.add(_project("pulse")).id
            out = call(ws, "surface_evaluate", project_id=pid, surface={
                "type": "polyline", "points": [list(v) for v in _PLANE]},
                methods=[_METHOD])
        finally:
            ws.shutdown()
        d = out["methods"][_METHOD]["details"]
        assert d.get("newmark_displacement") == round(engine, 6), (d, engine)


class TestTheNotes:

    def test_without_a_record(self):
        run, one = _doors("no_record")
        assert "method.newmark_no_record" in _codes(one.warnings)
        assert [c for c in _codes(one.warnings) if c in _SEISMIC] == \
            [c for c in _codes(run.warnings) if c in _SEISMIC]
        assert "newmark_displacement" not in one.results[_METHOD].details

    def test_a_kh_the_ky_replaces(self):
        run, one = _doors("kh")
        assert "method.seismic_kh_replaced" in _codes(one.warnings)
        assert [c for c in _codes(one.warnings) if c in _SEISMIC] == \
            [c for c in _codes(run.warnings) if c in _SEISMIC]

    def test_a_surface_without_a_ky_is_said_as_one_surface(self):
        """Not the run's sentence about a population («1 of 1 surfaces
        have … excluded from the ranking»): this door ranks nothing (review
        of 0.1.451)."""
        from ogr_api.results import with_warning_codes
        run, one = _doors("strong")
        assert one.results[_METHOD] is not None
        assert one.results[_METHOD].details.get("ky") is None or \
            not math.isfinite(one.results[_METHOD].details["ky"])
        notes = [c["args"]["note"] for c in with_warning_codes(
            {"warnings": list(one.warnings)}).get("warning_codes", [])
            if c["code"] == "note.method"]
        mine = [n for n in notes if n["code"] == "method.seismic_no_ky_given"]
        assert mine and mine[0]["args"] == {"k_max": 1.0}, notes
        assert "method.seismic_no_ky" not in [n["code"] for n in notes]
        # the run keeps its own sentence
        assert "method.seismic_no_ky" in _codes(run.warnings)

    def test_a_refused_surface_says_only_why(self):
        """A method without a result says why it has none, and nothing
        seismic: ``surface_evaluate`` takes every note of a refused method as
        the reason it was refused (review of 0.1.451: no case covered it, and
        a mutant giving the notes to a refusal survived)."""
        from ogr_api import Workspace, call

        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import SlipCircle
        far = SlipCircle(centre_x=500.0, centre_y=500.0, radius=3.0)
        out = evaluate_surfaces(_project("kh"), far, [_METHOD])
        assert out.results[_METHOD] is None              # the premise
        assert not [c for c in _codes(out.warnings) if c in _SEISMIC]
        ws = Workspace()
        try:
            pid = ws.add(_project("kh")).id
            js = call(ws, "surface_evaluate", project_id=pid, surface={
                "type": "circle", "centre_x": 500.0, "centre_y": 500.0,
                "radius": 3.0}, methods=[_METHOD])
        finally:
            ws.shutdown()
        assert js["notes"] and not any(
            "Newmark" in n or "seismic coefficient" in n
            for n in js["notes"]), js["notes"]

    def test_the_api_carries_them_with_their_codes(self):
        from ogr_api import Workspace, call
        from test_newmark_user_surfaces_v1429 import _PLANE
        ws = Workspace()
        try:
            pid = ws.add(_project("kh")).id
            out = call(ws, "surface_evaluate", project_id=pid, surface={
                "type": "polyline", "points": [list(v) for v in _PLANE]},
                methods=[_METHOD])
        finally:
            ws.shutdown()
        codes = [c["args"]["note"]["code"] for c in out.get("warning_codes", [])
                 if c["code"] == "note.method"]
        assert "method.seismic_kh_replaced" in codes, codes
        assert "method.newmark_no_record" in codes, codes


class TestWithoutTheSeismicModes:

    def test_nothing_seismic_is_said_or_attached(self):
        _run, one = _doors("static")
        given = one.results[_METHOD]
        assert not [c for c in _codes(one.warnings) if c in _SEISMIC]
        assert "newmark_displacement" not in (given.details or {})
        assert "ky" not in (given.details or {})


class TestOneRule:

    def test_the_run_and_the_door_ask_the_same_function(self):
        """``_seismic_notes`` is ``_seismic_lines`` of every surface the run
        analysed; ``evaluate_surfaces`` asks it for its one surface. Both
        measured (review of 0.1.451: with the door alone, a run keeping its
        own copy of the rule passed)."""
        import ogr_slip2d.analysis_runner as AR
        from ogr_slip2d.search import all_evaluations_of
        seen, real = [], AR._seismic_lines

        def spy(project, method_id, evaluations, **kw):
            seen.append(len(list(evaluations)))
            return real(project, method_id, evaluations, **kw)
        AR._seismic_lines = spy
        try:
            run = AR.run_analysis(_project("pulse"))
            AR.evaluate_surfaces(_project("pulse"), _surface(), [_METHOD])
        finally:
            AR._seismic_lines = real
        every = len(all_evaluations_of(run.results[_METHOD]))
        assert seen == [every, 1], (seen, every)
