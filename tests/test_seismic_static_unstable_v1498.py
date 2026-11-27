# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.498 (D439) — a Ky or Newmark run says which surfaces already have a
factor at kh = 0 at or below the Ky target: their Ky is 0, and a
displacement integrated from it is of a block that does not stand.

The invariant: when a valid surface has Ky = 0 because its factor at kh = 0
is already at or below the target (``critical_coefficient_from``: the
reference's answer, not a failure), the seismic notes of the run
(``_seismic_lines``, the rule of ``run_analysis`` and ``evaluate_surfaces``,
D406) say so with a code: ``method.seismic_static_unstable`` with the count,
``..._critical`` when the published critical surface is one of them (with
its factor), and ``..._given`` for the one surface a door was given. Until
this version nothing was said: on the plane below the run published Ky 0
and 22.04 m without a word (measured with 0.1.485 and 0.1.496, the bench's
``medir_d439_d440.py``).

Nothing else moves: the Ky stays 0 and the displacement stays the
integrator's at ky = 0 (the owner chose the note alone, option (a)).

The reference is external, a closed form (rule 1): on the plane of
``test_newmark_user_surfaces_v1429`` (dry sand, φ = 30°, the plane at β ≈
15.9°), with a custom standard dividing c and tan φ by 2.5, an infinite
slope gives F(0) = (tan φ / 2.5) / tan β = 0.808 < 1. Without the standard
F(0) = tan φ / tan β > 1, Ky > 0 and the note is not said (rule 7: the
standard moves the note).

Cost: five runs of the 60-slice plane, a few hundredths of a second each.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_METHOD = "janbu_simplified"
_FACTOR = 2.5
_CODES = ("method.seismic_static_unstable",
          "method.seismic_static_unstable_critical",
          "method.seismic_static_unstable_given")
_RUNS: dict = {}


def _project(case):
    """The plane of v1429: "factored" (c and tan phi / 2.5), "plain", or
    "ky_only" (factored, Newmark off)."""
    from test_newmark_user_surfaces_v1429 import _plane_project
    p = _plane_project()
    if case in ("factored", "ky_only"):
        ds = p.settings.design_standard
        ds.enabled, ds.standard = True, "custom"
        ds.factor_cohesion = ds.factor_friction = _FACTOR
    if case == "ky_only":
        p.settings.seismic.newmark = False
        p.settings.seismic.compute_ky = True
    return p


def _doors(case):
    """``(project, run outcome, evaluate_surfaces outcome)``, once."""
    if case not in _RUNS:
        from test_surface_evaluate_seismic_v1451 import _surface

        from ogr_slip2d.analysis_runner import evaluate_surfaces, run_analysis
        p = _project(case)
        _RUNS[case] = (p, run_analysis(p),
                       evaluate_surfaces(_project(case), _surface(), [_METHOD]))
    return _RUNS[case]


def _notes(warnings) -> dict:
    """``{code: args}`` of the method notes among ``warnings``."""
    from ogr_core.messages import parts
    out = {}
    for w in warnings:
        code, args, _english = parts(w)
        if code == "note.method":
            note = args.get("note") or {}
            out[note.get("code")] = note.get("args") or {}
    return out


def _f0_closed_form(factor):
    from test_newmark_user_surfaces_v1429 import _BETA, _PHI
    return (math.tan(math.radians(_PHI)) / factor
            / math.tan(math.radians(_BETA)))


class TestThePremise:

    def test_the_closed_form_is_below_the_target(self):
        assert _f0_closed_form(_FACTOR) < 1.0 < _f0_closed_form(1.0)

    def test_the_run_has_ky_zero_at_that_factor(self):
        _p, run, _one = _doors("factored")
        crit = run.results[_METHOD].critical
        f0 = _f0_closed_form(_FACTOR)
        # the plane as Janbu solves it: the closed form to 1e-4 (0.808357
        # against 0.808290, the slicing of the wedge's ends)
        assert abs(crit.fos - f0) / f0 < 1e-4, (crit.fos, f0)
        assert crit.details["ky"] == 0.0


class TestTheNoteIsSaid:

    def test_by_the_run_naming_the_critical_surface(self):
        _p, run, _one = _doors("factored")
        notes = _notes(run.warnings)
        args = notes.get("method.seismic_static_unstable_critical")
        assert args is not None, list(notes)
        crit = run.results[_METHOD].critical
        assert args["n"] == 1 and args["valid"] == 1
        assert args["factor"] == crit.fos and args["target"] == 1.0

    def test_by_evaluate_surfaces_as_one_surface(self):
        _p, _run, one = _doors("factored")
        notes = _notes(one.warnings)
        args = notes.get("method.seismic_static_unstable_given")
        assert args is not None, list(notes)
        assert args["factor"] == one.results[_METHOD].fos
        assert "method.seismic_static_unstable" not in notes

    def test_by_a_ky_run_without_newmark(self):
        _p, run, _one = _doors("ky_only")
        assert "method.seismic_static_unstable_critical" in _notes(
            run.warnings)

    def test_without_the_standard_it_is_not(self):
        """Rule 7: the standard moves the note."""
        _p, run, one = _doors("plain")
        assert run.results[_METHOD].critical.details["ky"] > 0.0
        for out in (run, one):
            said = set(_notes(out.warnings)) & set(_CODES)
            assert not said, said


class TestNothingElseMoves:

    def test_the_displacement_is_the_integrators_at_ky_zero(self):
        from ogr_slip2d.newmark import displacement_for_record
        p, run, one = _doors("factored")
        alone = displacement_for_record(p.seismic_records[0], 0.0)
        for res in (run.results[_METHOD].critical, one.results[_METHOD]):
            assert res.details["ky"] == 0.0
            assert res.details["newmark_displacement"] == alone.displacement
