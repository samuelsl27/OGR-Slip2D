# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.190 — the decision on the ``phi = 0`` base-angle ceiling is to KEEP
it, and a decision to change nothing only stays decided if a test can
tell it apart from having forgotten.

THE INVARIANT. Under ``phi = 0`` the m-alpha check degenerates into a
bare ceiling of ``acos(0.2) = 78.463`` deg (defect D61, measured
2026-08-31). A search MINIMISES the factor and the factor is minimised by
pushing ``m_alpha`` towards the limit, so the surface a search reports is
systematically the one where its method is least valid. The question the
defect left open was whether 0.2 is the right number there. The answer in
this version is: **it stays**, because the search for a published case to
decide it against ended negative in v0.1.158 across four sources, and
moving a validity limit with no external contrast is the thing rule 1
exists to prevent.

So this file has to demonstrate two different things, and neither alone
would do:

1. **that nothing moved** — the limit is still 0.2, it still bites where
   it bit, the reference-validated critical circle still clears it, and
   ``_base_angle_ok`` was not widened. Without this, "documentary
   closure" is a free pass;
2. **that the reasons are written where the code is read** — including
   the ABSENCE of the sentence that said the defect was open, which no
   positive grep can see.

WHAT THIS FILE DOES NOT CLAIM. Not that 0.2 is correct. The measurement
in ``test_phi_zero_general_branch_v1190.py`` says the ceiling still
screens something real on the general branch, which is a reason to keep
it, not proof that its value is right. And the closing class below
measures what clearing 0.2 does NOT buy — on surfaces that all pass, the
nine methods disagree by factors of 6.8, 34.9 and 1501.

WHAT THIS FILE DISCRIMINATES against the v0.1.189 tree. MEASURED by
copying it into a ``git worktree`` at that commit: **5 of 13 fail**, all
five in ``TestTheDecisionIsWrittenWhereTheCheckIsRead``. The strongest is
``test_the_docstring_no_longer_says_the_defect_is_open``, because an
ABSENCE is what a grep-shaped closure criterion cannot check — and the
criterion written for D61 in the bank was exactly that shape: it asked
for "78.46" and "Ching" in ``checks.py``, and BOTH were already there in
v0.1.189. The other four are literal sets carrying numbers, which is
weak on its own and is labelled so; ``d61()`` does not rest on them.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_slip2d.checks import (  # noqa: E402
    M_ALPHA_LIMIT,
    base_m_alphas,
    check_surface,
)

CEILING = math.degrees(math.acos(M_ALPHA_LIMIT))


def _doc() -> str:
    """The module docstring with its whitespace normalised.

    NOT a careful choice of short substrings: that trap has caught this
    project three times, most recently inside the very check written to
    catch it. A reflow to 79 columns must not be able to break this.
    """
    import re

    import ogr_slip2d.checks as checks
    return re.sub(r"\s+", " ", checks.__doc__ or "")


def _scarp(beta_deg: float, drop: float = 36.0):
    dx = drop / math.tan(math.radians(beta_deg))
    return [(20.0, 30.0), (20.0 + dx, 30.0 - drop),
            (35.0 + dx, 28.0 - drop), (100.0, 10.0)]


def _evaluate(points, phi: float = 0.0, num_slices: int = 30, method=None):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.search import BlockSearch
    from ogr_slip2d.surface import SlipSurface
    from test_block_population_v1135 import _cohesive_slope

    s = BlockSearch(method=method or BishopSimplified(),
                    num_slices=num_slices)
    poly = Polyline(vertices=[Vertex(x, y) for x, y in points], closed=False)
    return s.evaluate_surface(_cohesive_slope(phi), SlipSurface(polyline=poly))


# ======================================================================
class TestTheLimitIsUnchangedAndStillBites:
    """Half one of a decision not to change anything: show it did not."""

    def test_the_limit_is_still_two_tenths(self):
        assert M_ALPHA_LIMIT == 0.2
        assert abs(CEILING - 78.463) < 1e-3, CEILING

    def test_the_validated_critical_circle_still_passes(self):
        """``if a change to the ceiling touches these, STOP`` — made
        executable rather than left in the prompt.

        This is the circle v0.1.82 measured at min ``m_alpha`` +0.93
        after fifty versions of a sign being read in the mirror, and
        v0.1.84 turned the check on by default on the strength of it.
        """
        from test_checks_v132 import _eval_ref_circle

        res = _eval_ref_circle()
        assert res is not None and res.fos is not None
        assert min(base_m_alphas(res)) > 0.9, min(base_m_alphas(res))
        ok, _why = check_surface(res, tensile=False, m_alpha=True)
        assert ok

    def test_a_base_just_inside_the_ceiling_is_still_accepted(self):
        """The ceiling has to still be WHERE it was, not merely still
        exist. Measured by behaviour on both sides of it rather than by
        reading ``acos``."""
        res = _evaluate(_scarp(77.5))
        assert res is not None
        worst = min(base_m_alphas(res))
        assert worst > M_ALPHA_LIMIT, worst
        ok, _why = check_surface(res, tensile=False, m_alpha=True)
        assert ok

    def test_and_one_just_outside_is_still_rejected(self):
        res = _evaluate(_scarp(82.0))
        assert res is not None
        worst = min(base_m_alphas(res))
        assert worst < M_ALPHA_LIMIT, worst
        ok, _why = check_surface(res, tensile=False, m_alpha=True)
        assert not ok

    def test_the_named_ceiling_was_not_widened(self):
        """Branch (b) of the decision — letting ``max_base_angle_deg``
        reach every surface in cohesive soil — was NOT taken, and this is
        what would catch it being taken quietly. Measured by running a
        surface steeper than the typed value through the real door."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.search import BlockSearch
        from ogr_slip2d.surface import SlipSurface
        from test_block_population_v1135 import _cohesive_slope

        p = _cohesive_slope(0.0)
        p.settings.advanced.max_base_angle_deg = 45.0
        p.settings.advanced.check_m_alpha = False
        s = BlockSearch(method=BishopSimplified(), num_slices=30)
        poly = Polyline(vertices=[Vertex(x, y) for x, y in _scarp(70.0)],
                        closed=False)
        res = s.evaluate_surface(p, SlipSurface(polyline=poly))
        assert res is not None and res.fos is not None
        steepest = math.degrees(max(abs(sl.base_angle) for sl in res.slices))
        assert steepest > 45.0, steepest


# ======================================================================
class TestTheNoteIsTheDefence:
    """With the limit kept, the reporting note of v0.1.135 is what the
    decision leans on, so it has to fire in the band the defect lives
    in: accepted by the check, and resting on a quarter of a normal."""

    def test_a_base_at_seventy_seven_degrees_is_accepted_and_reported(self):
        from ogr_slip2d.analysis_runner import m_alpha_margin_note

        res = _evaluate(_scarp(77.0))
        assert res is not None
        worst = min(base_m_alphas(res))
        # The identity that makes the band meaningful: under phi = 0 the
        # worst m_alpha IS the cosine of the steepest base.
        steep = max(abs(sl.base_angle) for sl in res.slices)
        assert abs(worst - math.cos(steep)) < 1e-9, (worst, math.cos(steep))
        assert M_ALPHA_LIMIT < worst < 0.5, worst
        notes = m_alpha_margin_note(res)
        assert notes, worst
        assert "m_alpha" in notes[0], notes[0]


# ======================================================================
class TestTheDecisionIsWrittenWhereTheCheckIsRead:
    """Half two. Five cases, and the first is the only one a positive
    grep cannot imitate."""

    def test_the_docstring_no_longer_says_the_defect_is_open(self):
        """FAILS on v0.1.189, and it is the strongest case in the file.

        An ABSENCE is invisible to the closure criterion the bank had
        written for D61 — grep "78.46" and grep "Ching" over
        ``checks.py`` — which BOTH already passed on v0.1.189, the first
        since v0.1.158 and the second since v0.1.158 as well. A criterion
        its own previous state satisfies is not a criterion.
        """
        doc = _doc()
        assert "Defect D61 of the verification bank is open on it" not in doc
        assert "nothing external to decide the limit against" not in doc

    def test_it_names_the_four_sources_the_search_covered(self):
        """Weak on its own — a literal set — and labelled as such. It
        carries NUMBERS rather than adjectives, so a rewrite that drops
        the evidence drops the test with it."""
        doc = _doc()
        for tok in ("EM 1110-2-1902", "G-9", "61 deg", "43.7 deg",
                    "44.17 deg", "43.4 deg", "James Bay", "7.29",
                    "Ching & Fredlund (1983)"):
            assert tok in doc, tok

    def test_it_says_the_search_ended_negative_and_the_limit_is_kept(self):
        doc = _doc()
        assert "ended negative" in doc
        assert "No published case discriminates." in doc
        assert "the limit stays at 0.2" in doc.lower()

    def test_it_marks_the_doctrine_as_doctrine_and_not_as_a_case(self):
        """Duncan, Wright & Brandon §14.4 would settle it if doctrine
        counted as evidence here. It does not, and the docstring has to
        say which of the two it is holding — otherwise the next reader
        finds a quotation that recommends 45 deg and no note that
        applying it moves the validated cases."""
        doc = _doc()
        assert "45 degrees or less" in doc
        assert "Jumikis" in doc
        assert "doctrine and not as a case" in doc
        assert "move the validated cases" in doc
        assert "cited and not applied" in doc

    def test_it_cites_the_measurement_as_the_reason_it_stands(self):
        doc = _doc()
        assert "m_alpha_check" in doc
        assert "general branch" in doc

    def test_and_it_keeps_the_warning_that_the_second_source_was_not_read(
            self):
        """Deliberately duplicated from
        ``test_m_alpha_notes_v1158.py``, and said out loud. Rewriting the
        D61 paragraph must not be able to take the paywall warning with
        it: a source held second-hand is not evidence, and hiding that is
        how a false sentence earns a footnote."""
        doc = _doc()
        assert "not** because it has been read" in doc
        assert "behind a paywall" in doc


# ======================================================================
class TestWhatClearingTheLimitDoesNotBuy:
    """The decision is to keep the limit, NOT to claim it certifies
    anything. On surfaces that all clear 0.2, the methods disagree by
    orders of magnitude — the original defect report put this spread at
    44 %, and that was the mild end."""

    def test_the_methods_disagree_wildly_on_surfaces_the_check_admits(self):
        from ogr_slip2d.methods import method_registry

        reg = method_registry()
        res = _evaluate(_scarp(75.0))
        assert res is not None
        worst = min(base_m_alphas(res))
        assert worst > M_ALPHA_LIMIT, worst

        values = []
        for mid in sorted(reg):
            r = _evaluate(_scarp(75.0), method=reg[mid]())
            if r is None or r.fos is None or not r.converged:
                continue
            ok, _why = check_surface(r, tensile=False, m_alpha=True)
            assert ok, mid          # every one of them is ADMITTED
            values.append((mid, float(r.fos)))
        assert len(values) >= 7, values
        lo = min(v for _m, v in values)
        hi = max(v for _m, v in values)
        assert hi / lo > 10.0, values
