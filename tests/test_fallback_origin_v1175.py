# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A constant with no derivation has to say so, and say where it came from.

WHAT INVARIANT THIS PROTECTS. ``interslice.FALLBACK_RESIDUAL_LIMIT`` decides
whether the "no lambda-bracket" fallback of Spencer and GLE calls its answer
converged, and ``converged`` feeds ``LEMResult.is_valid``, which
``search.surface_score`` scores at infinity. So this one number decides
whether a surface COMPETES for the global minimum at all. v0.1.159 gave it a
name and measured why it must not be tied to the caller's tolerance; where the
0.02 itself came from, it could not say. That is defect D120.

v0.1.175 answers it, and the answer is that there is no derivation — which is
a result and not a shrug, because the alternative was to keep an unexplained
number in the one place where an unexplained number changes which surfaces
exist. The history: the first Spencer this project had wrote the threshold
inline as 0.01 with no comment, in ``spencer.py`` and ``gle.py`` alike;
v0.1.13 rewrote both methods from scratch against Fredlund and Krahn (1977)
and DOUBLED it to 0.02 in both files at once; and that rewrite's changelog
documents four named bugs and never mentions the threshold. The reference
formulation publishes no acceptable residual either, and has no error code for
"no lambda root" at all — the fallback is a third state it does not have.

So this file enforces two things at once. **The origin must stay written**,
because a comment is the only place this fact can live and the next person to
meet the number will read exactly what is above it; and **the boundary must
stay off the tolerance**, which is the repair v0.1.159 measured to be worse
than the defect (+181 % on the reported critical of the Ej_1 block search).

WHY THE BLOCK ATTRIBUTION IS TESTED AT ALL, which looks like typography and
is not. Until v0.1.175 the ``#:`` block of ``STALL_PATIENCE`` sat immediately
above ``FALLBACK_RESIDUAL_LIMIT`` because one blank line was missing, so the
documented reason for one constant was attached to the other and
``STALL_PATIENCE`` had no comment at all. It was reported in v0.1.173 and not
fixed. Writing the origin of the 0.02 into a block that lands on the wrong
constant would have been writing it nowhere, so the two go together.

WHICH CASES MEASURE THE DEFECT AND WHICH ARE CONTROL, counted rather than
asserted. Against the tree of 0.1.174, with only this file added, 7 of the 15
FAIL and 8 PASS, and the 8 are exactly the ones that should: the four of
``TestTheBoundaryIsStillNotTheTolerance`` and ``TestTheKeysTheBankCounts``
listed below, plus three conservation cases that pin what must NOT move —
the Ej_1 reason that has held this number since v0.1.159, the ``MAX_PASSES``
block that the reordering could have taken with it, and the pair of keys the
census reads. ``TestTheBoundaryIsStillNotTheTolerance`` and
``TestTheKeysTheBankCounts`` are declared CONTROL: they are green on both
trees BY CONSTRUCTION, because they guard against the error THIS change could
commit — buying a written origin by moving the number it explains, or renaming
the keys the census reads — and not against the defect it removes. A test
whose docstring does not say which of the two it is will be read as the one it
is not.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a change delivers is what cost this project two versions in v0.1.82-84:

  * that the fallback is a good way to answer. It is not judged here at all.
    The bank census of v0.1.175 measured that 41 of 229 Spencer/GLE rows
    publish a minimum found down this path, every one of them under the limit
    and therefore reported as converged, with residuals up to 200 times the
    tolerance the run asked for. That census lives in the verification bank,
    outside this repository, and is checked by ``d120()``, not here.
  * that the decision to let those surfaces compete is re-derived here.
    ``TestTheFallbackStillCompetesForTheMinimum`` in
    ``test_interslice_budget_v1159.py`` already owns it, and duplicating it
    would give the two files two chances to disagree.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import ast
import io
import math
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

#: The plane wedge fixture, built here rather than imported: geometry in
#: code, never read from ``referencias/``, so the suite runs on a machine
#: that does not have the verification bank.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50

#: The angle whose lambda search finds NO bracket, so both methods take the
#: fallback. Measured over 35, 40, 45, 50, 55, 60, 65 and 70 degrees at
#: three tolerances: 55 is the only one that falls back, and it does so at
#: every one of them (residual 0.264 for Spencer, 0.294 for GLE).
FALLBACK_BETA = 55.0

#: An angle whose search DOES bracket its root, for the other side of the
#: contract: there the two keys must say so rather than be absent.
BRACKET_BETA = 35.0


def _bare():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    return p


def _plane(beta_deg):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface

    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0),
        Vertex(TOE + H / math.tan(math.radians(beta_deg)), H)]))


def _details(method_id, beta_deg, tolerance=1e-6):
    """``details`` of the plane, down the real path and with nothing mocked."""
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface

    project, surface = _bare(), _plane(beta_deg)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    r = method_registry()[method_id](
        tolerance=tolerance, max_iterations=400).compute_fos(
            project, surface, sl)
    return r, (r.details or {})


def _source(rel):
    return io.open(_REPO / rel, encoding="utf-8").read()


def _block_above(name):
    """The ``#:`` block Sphinx attaches to a module constant.

    Walks UP from the assignment collecting contiguous ``#:`` lines and
    stops at the first line that is not one, which is exactly the rule a
    blank line broke before v0.1.175. Written as a walk rather than as a
    slice between two known markers on purpose: a slice would still find
    the text after somebody reintroduced the blank line, and finding the
    text is not the question — which constant it lands on is.
    """
    lines = _source("ogr_slip2d/interslice.py").split("\n")
    hit = [i for i, ln in enumerate(lines) if ln.startswith(name + " = ")]
    assert len(hit) == 1, "%s assigned %d times" % (name, len(hit))
    out = []
    i = hit[0] - 1
    while i >= 0 and lines[i].startswith("#:"):
        out.append(lines[i][2:].strip())
        i -= 1
    return "\n".join(reversed(out))


# ======================================================================
# A. The origin, which is the whole of D120's first half
# ======================================================================
class TestTheOriginIsWrittenDown:
    """COVERAGE. Four of these five fail against 0.1.174, where the block
    said why the number could not be the tolerance and never said where it
    came from.

    The fifth, ``test_the_measured_boundary_is_still_the_reason_it_stays``,
    is green on both trees by construction and that is deliberate: the
    Ej_1 measurement is what has held this number in place since v0.1.159,
    and the job of the origin is to be added BESIDE it, not to replace it.
    It is a conservation case living in a coverage class, and saying so
    here is cheaper than a class of its own for one assertion.
    """

    def test_it_names_the_version_that_doubled_it(self):
        """The one fact a ``git log -S`` in this repository cannot reach:
        the change predates the first public commit, so the trail ends
        before the change it is looking for.

        The phrase and not the bare version string, because ``v0.1.13`` is
        a SUBSTRING of ``v0.1.130`` — which the old block already carried,
        citing the defect D37/C1 fix. Written as ``"v0.1.13" in block``
        this case passed against 0.1.174 for a reason that had nothing to
        do with what it claims to check.
        """
        block = _block_above("FALLBACK_RESIDUAL_LIMIT")
        assert "v0.1.13 rewrote" in block, block[:400]
        assert "DOUBLED" in block, block[:400]

    def test_it_says_what_the_number_was_before(self):
        block = _block_above("FALLBACK_RESIDUAL_LIMIT")
        assert "0.01" in block, block[:400]

    def test_it_says_in_so_many_words_that_there_is_no_derivation(self):
        """Because the next person to meet this number will want to know
        whether looking harder would find one. It has been looked for."""
        block = _block_above("FALLBACK_RESIDUAL_LIMIT").lower()
        assert "no derivation" in block, block[:400]

    def test_it_says_the_reference_publishes_no_such_residual(self):
        """The other half of the search: there is no published value to
        adopt either, so the boundary cannot be sourced from outside."""
        block = _block_above("FALLBACK_RESIDUAL_LIMIT").lower()
        assert "residual" in block
        assert "whitman and bailey" in block, block[:400]

    def test_the_measured_boundary_is_still_the_reason_it_stays(self):
        """v0.1.159's measurement is what holds the number in place, and
        the origin does not replace it."""
        block = _block_above("FALLBACK_RESIDUAL_LIMIT")
        assert "Ej_1" in block, block[:400]


# ======================================================================
# B. Where the block lands, which decides whether any of A is written
#    anywhere at all
# ======================================================================
class TestEachBlockSitsOnItsOwnConstant:
    """COVERAGE. Fails against 0.1.174: one missing blank line put the
    ``STALL_PATIENCE`` block on ``FALLBACK_RESIDUAL_LIMIT`` and left
    ``STALL_PATIENCE`` with no comment at all. Reported in v0.1.173."""

    def test_the_fallback_block_is_about_the_fallback(self):
        block = _block_above("FALLBACK_RESIDUAL_LIMIT")
        assert block.startswith("The residual"), block[:120]

    def test_stall_patience_has_a_block_of_its_own_again(self):
        block = _block_above("STALL_PATIENCE")
        assert block, "STALL_PATIENCE is documented nowhere"
        assert block.startswith("How many consecutive passes"), block[:120]

    def test_neither_block_carries_the_other_one_subject(self):
        """The failure mode is not an empty block, it is a block that
        reads perfectly well while describing the constant next door."""
        fall = _block_above("FALLBACK_RESIDUAL_LIMIT")
        stall = _block_above("STALL_PATIENCE")
        assert "consecutive passes" not in fall, fall[:200]
        assert "no lambda-bracket" not in stall, stall[:200]

    def test_the_backstop_block_did_not_move_either(self):
        """Reordering two constants is the sort of edit that takes a third
        one with it, so the neighbour is pinned."""
        block = _block_above("MAX_PASSES")
        assert block.startswith("Backstop for a branch"), block[:120]


# ======================================================================
# C. CONTROL — what a written origin must NOT have been bought with
# ======================================================================
class TestTheBoundaryIsStillNotTheTolerance:
    """Declared CONTROL: green before this version and green after it.

    These guard against the error THIS change could commit rather than
    against the defect it removes. Explaining a number is exactly the
    occasion on which somebody decides to tidy it, and v0.1.159 measured
    where that leads: the reported critical of the Ej_1 block search moved
    from 0.654746 to 1.841807, a 181 % move on the unsafe side, and the
    m-alpha filter silently stopped having anything to flag.
    """

    def test_the_constant_did_not_move(self):
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT
        assert FALLBACK_RESIDUAL_LIMIT == 0.02

    def test_both_methods_still_compare_against_the_constant(self):
        """By AST and by symbol name. A grep would be satisfied by the
        comment that mentions the constant, which is the one thing this
        must not accept."""
        for rel in ("ogr_slip2d/methods/spencer.py",
                    "ogr_slip2d/methods/gle.py"):
            found = []
            for node in ast.walk(ast.parse(_source(rel))):
                if not isinstance(node, ast.Assign):
                    continue
                if not any(isinstance(t, ast.Name) and t.id == "settled"
                           for t in node.targets):
                    continue
                cmp_ = node.value
                assert isinstance(cmp_, ast.Compare), (rel, ast.dump(cmp_))
                right = cmp_.comparators[0]
                assert isinstance(right, ast.Name), (rel, ast.dump(right))
                found.append(right.id)
            assert found == ["FALLBACK_RESIDUAL_LIMIT"], (rel, found)

    def test_it_is_looser_than_the_tolerance_the_program_ships(self):
        """The property the whole comment exists to explain: the boundary
        is deliberately NOT the tolerance, and it is the looser of the
        two. The default is read from the field, never written here."""
        from dataclasses import fields as dataclass_fields

        from ogr_core.project.settings import MethodsSettings
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT

        shipped = next(f.default for f in dataclass_fields(MethodsSettings)
                       if f.name == "tolerance")
        assert FALLBACK_RESIDUAL_LIMIT > shipped, (FALLBACK_RESIDUAL_LIMIT,
                                                   shipped)


# ======================================================================
# D. CONTROL — the contract the bank census reads through
# ======================================================================
class TestTheKeysTheBankCounts:
    """Declared CONTROL. The census that answers the second half of D120
    lives in the verification bank and counts these two keys by name. If
    the engine renames either one, the bank's new column goes quietly
    empty and the count becomes a row of blanks that reads like a zero —
    which is the failure this class exists to make loud instead.
    """

    def test_the_fallback_publishes_both_keys_by_name(self):
        for mid in ("spencer", "gle_morgenstern_price"):
            _r, det = _details(mid, FALLBACK_BETA)
            assert det.get("lambda_search_fell_back") is True, (mid, det)
            assert det.get("lambda_residual") is not None, (mid, det)
            assert det.get("lambda_tolerance") is not None, (mid, det)

    def test_the_two_keys_v0_1_182_added_are_there_by_name_too(self):
        """Same contract, two keys later. ``lambda_edge_recovered`` and
        ``lambdas_lost_to_thrust_tension`` (D149) travel on BOTH exits and on
        every surface, so a census can count them without first asking which
        branch produced the row — and the second one exists because
        ``n_thrust_rejected`` is not the number anybody wants: it increments
        outside the ``strict`` test, so the all-or-nothing sweep doubles it.
        """
        for mid in ("spencer", "gle_morgenstern_price"):
            for beta in (FALLBACK_BETA, BRACKET_BETA):
                _r, det = _details(mid, beta)
                assert "lambda_edge_recovered" in det, (mid, beta, det)
                assert "lambdas_lost_to_thrust_tension" in det, (mid, beta)
                assert det["lambda_edge_recovered"] == 0, (mid, beta, det)

    def test_the_bracket_path_says_false_rather_than_saying_nothing(self):
        """``False`` and a missing key are not the same answer, and the
        census distinguishes them: a method with no such branch leaves
        both at ``None``, a search that found its root says ``False``."""
        for mid in ("spencer", "gle_morgenstern_price"):
            _r, det = _details(mid, BRACKET_BETA)
            assert det.get("lambda_search_fell_back") is False, (mid, det)
            assert det.get("lambda_residual") is None, (mid, det)

    def test_a_residual_past_the_boundary_is_a_refusal_and_says_why(self):
        """The fixture above is over the limit, so it also pins the half
        of the rule that vetoes: past 0.02 the answer is not published as
        converged and carries its reason."""
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT
        for mid in ("spencer", "gle_morgenstern_price"):
            r, det = _details(mid, FALLBACK_BETA)
            assert det["lambda_residual"] >= FALLBACK_RESIDUAL_LIMIT, det
            assert r.converged is False, mid
            assert r.error_message, "a refusal with no reason is the defect"
