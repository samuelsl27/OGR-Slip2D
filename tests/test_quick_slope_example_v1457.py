# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D426 (v0.1.457) — the slope of ``examples/quick_slope.py`` declares the
failure direction its ground gives.

The invariant
-------------
``build_demo_slope`` built by hand (since v0.1.59) a second copy of the demo
slope, with the default direction, Right to Left, while its ground is higher
on the left (y = 25 at x = 0 against y = 15 at x = 50). Every run of it
through the analysis gate (``run_analysis``, what the window, the agent and
the tests run), and ``project_validate``, carried
``model.failure_direction_r2l``: «puts the crest on the right, but the
ground surface is higher on the left» (the example's own ``main()`` calls
``GridSearch.run``, which never said it). Measured
with v0.1.456: ``RIGHT_TO_LEFT 0x1.4f3678903d37fp+0`` and the warning (a
Path Search of 5 with Janbu). The demo of the core, ``build_demo_project``,
declares Left to Right since v0.1.329 (D328). By the owner's decision the
example now IS that demo under its own name: one demo slope.

The reference (rule 1)
----------------------
Two identities. The declaration is the one the ground gives, read here from
the external boundary's two ends and not from the engine's rule, and that
rule (``_failure_direction_note``) then says nothing. And the one of D328:
every surface the search analysed, factor and geometry, is the same bit for
bit under both declarations, in one process, because none of the readers of
the declaration is in this slope: a tension crack (its water thrust and the
end it cuts), a support's sense, and, when two faces tie, the starting face
of Path Search and the angle limits of Block Search. The control: the rule
still warns when the declaration is flipped, and the example is the demo
field by field.

And, by the owner's decision in the review, the line ``main()`` prints about
the population adds up: generated, valid and invalid, as the engine's census
counts them (``TestWhatMainPrints``).

No window. The D328 case runs a small grid (16 centres, 64 circles) in about
half a second; the one of ``main()`` runs the example itself, in a temporary
folder, in about one; the others take nothing.
"""
from __future__ import annotations

import json
import re

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
                   r"[0-9a-f]{12}")


def _ends_of_the_ground(project):
    """The external boundary's highest point at its left end and at its
    right end: the two heights that say which way the slope faces."""
    vs = project.external_boundary().polyline.vertices
    left, right = min(v.x for v in vs), max(v.x for v in vs)
    return (max(v.y for v in vs if v.x == left),
            max(v.y for v in vs if v.x == right))


def _masked(project):
    """``to_dict`` as the file writes it, with every id and the creation
    date masked: what two builds of one slope share."""
    d = project.to_dict()
    d["settings"]["summary"].pop("date_created", None)
    return _UUID.sub("ID", json.dumps(d, sort_keys=True))


# ======================================================================
class TestTheDeclaration:

    def test_it_is_the_direction_its_ground_gives(self):
        from examples.quick_slope import build_demo_slope
        from ogr_core.project.units import FailureDirection
        p = build_demo_slope()
        high_left, high_right = _ends_of_the_ground(p)
        assert (high_left, high_right) == (25, 15)
        # higher on the left: the mass moves towards increasing x
        assert p.settings.units.failure_direction == \
            FailureDirection.LEFT_TO_RIGHT

    def test_the_rule_says_nothing_and_still_warns_when_flipped(self):
        from examples.quick_slope import build_demo_slope
        from ogr_core.project.units import FailureDirection
        from ogr_slip2d.analysis_runner import _failure_direction_note
        p = build_demo_slope()
        assert _failure_direction_note(p) == []
        p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
        notes = _failure_direction_note(p)
        assert [getattr(n, "code", None) for n in notes] == \
            ["model.failure_direction_r2l"], notes


# ======================================================================
class TestTheFactor:

    def test_it_is_the_same_under_both_declarations(self):
        """The identity of D328, on the example: one process, bit for bit,
        every surface the search analysed and not only the critical one (the
        review of 0.1.457: a declaration that moved only the others passed)."""
        from examples.quick_slope import build_demo_slope
        from ogr_core.project.units import FailureDirection
        from ogr_slip2d.analysis_runner import run_analysis
        got = {}
        for direction in (FailureDirection.LEFT_TO_RIGHT,
                          FailureDirection.RIGHT_TO_LEFT):
            p = build_demo_slope()
            p.settings.units.failure_direction = direction
            s = p.settings.search
            s.grid_nx = s.grid_ny = 3          # 16 centres: no process pool
            s.radius_increment = 3             # 4 radii each: 64 circles
            p.settings.methods.enabled_methods = ["bishop_simplified",
                                                  "janbu_simplified"]
            results = run_analysis(p).results
            got[direction] = {
                mid: (r.critical.fos.hex(),
                      [(None if e.fos is None else e.fos.hex(),
                        _UUID.sub("ID", json.dumps(e.surface.to_dict(),
                                                   sort_keys=True)))
                       for e in r.evaluations])
                for mid, r in results.items()}
        populations = got[FailureDirection.LEFT_TO_RIGHT]
        assert len(populations) == 2
        assert all(len(evals) > 10 for _crit, evals in populations.values())
        assert populations == got[FailureDirection.RIGHT_TO_LEFT]


# ======================================================================
class TestWhatMainPrints:
    """By the owner's decision in the review of 0.1.457: ``main()`` printed
    «Evaluated 118 surfaces (valid: 90, invalid: 57)», whose parts did not add
    up to the whole (118 were the surfaces sliced; the invalid count includes
    the 29 rejected before slicing). The reference is the engine's census
    (``interpretation.invalid_summary``): generated, valid and rejected."""

    def test_the_counts_add_up_to_what_the_search_generated(self):
        import contextlib
        import io
        import os
        import tempfile

        from examples import quick_slope
        from ogr_slip2d.interpretation import invalid_summary
        out = io.StringIO()
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)               # main() writes its .h5 where it runs
            try:
                with contextlib.redirect_stdout(out):
                    result = quick_slope.main()
            finally:
                os.chdir(here)
        text = out.getvalue()
        m = re.search(r"(\d+) surfaces \(valid: (\d+), invalid: (\d+)\)",
                      text)
        assert m, text
        n, valid, invalid = map(int, m.groups())
        assert valid + invalid == n, text
        census = invalid_summary(result)
        assert (n, valid, invalid) == (census["generated"],
                                       census["analysed"],
                                       census["rejected"])
        # the premise: in this case the surfaces sliced are not the whole
        assert len(result.evaluations) != n

    def test_a_surface_screened_by_a_check_is_invalid(self):
        # In the demo every converged surface passes the checks, so
        # ``valid_count`` and ``analysed_count`` are both 90 there. A surface
        # screened out (m-alpha, tension) converged and is counted valid by
        # ``valid_count``, but it can never be critical, and the reference
        # lists it among the invalid ones (``SearchResult.analysed_count``).
        from types import SimpleNamespace

        from examples.quick_slope import surface_counts
        result = SimpleNamespace(total_count=10, valid_count=8,
                                 analysed_count=6, invalid_count=2,
                                 evaluations=[None] * 9)
        assert surface_counts(result) == \
            "Generated 10 surfaces (valid: 6, invalid: 4)"


# ======================================================================
class TestOneDemoSlope:

    def test_the_example_is_the_demo_under_its_name(self):
        from examples.quick_slope import build_demo_slope
        from ogr_core.project.demo import build_demo_project
        a = build_demo_slope()
        assert a.name == "Demo homogeneous slope"
        b = build_demo_project(name=a.name)
        assert _masked(a) == _masked(b)
        assert a.is_dirty is False
