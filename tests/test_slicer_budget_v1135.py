# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.135 — a search that drops surfaces because it cannot slice
them has to say so, and it must not manufacture them in the first place.
Defect D21b, points (3) and (4). The two are one mechanism seen from its
two ends.

**The mechanism.** Every vertex of a surface is a mandatory slice
boundary, and material boundaries and the water table take cuts of their
own, so ``_slice_boundaries`` refuses a surface WHOLE when the segments
outnumber the slices. The refusal returns ``None``, every search counts
that as one invalid surface, and nothing distinguished it from a
degenerate mass or a failed filter.

**Point (3) — the note existed and reached one search of seven.** Since
v0.1.128 the non-circular Auto Refine counted the refusals and reported
them; nothing else did. It is Block and Path that need it most, because
their surfaces carry a vertex per generated point on top of every layer
crossing, while a circle has no kinks at all and the whole rule stays
inert for circular searches. The counting now lives in
``_best_of_masses``, the one door every search reaches the slicer
through — the same argument v0.1.102 used for the Surface Filters — and
the wording is a method any search may sharpen.

How badly it bites, measured on verification problem 19 (a 260 by 100
model at 30 slices) with a MANUAL Path segment length:

    segment length   generated   refused by the slicer   valid
    automatic (0.3H)       309                       0     300
    5.0 m                  572                     258     300
    2.0 m                 5098                    5077      20
    1.0 m                 5082                    5082       0
    0.5 m                 5050                    5050       0

A user who asks for one-metre segments gets no surfaces and no reason.

**Point (4) — and the cap is why the generator can even try.** The ficha
called ``max_segments`` a class constant; it is the default of an
argument ``build_search`` never passed, so it was 30 always. It is a
GUARD and not a resolution control, and the measurement says so: opened
to 500, the longest surface four bank models produced was 15 segments
(median 8-9) against a cap of 30, and the slicer refused none of them.
So tying it to the slice count outright — which is what the reference
does — would move 25 bank models through nothing but the drift of the
random stream, since a walk that exhausts its budget returns ``None``
after consuming a different number of draws. ``min`` instead of ``=``
keeps every bank model exactly where it is (they declare 30, 40 or 50
slices, so the cap stays 30) while a project with fewer slices than
segments stops manufacturing guaranteed rejects.

COST. Small searches only; no test here needs a converged minimum.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_search_inequality_v1118 import _layered_slope  # noqa: E402


def _bishop():
    from ogr_slip2d.methods.bishop import BishopSimplified
    return BishopSimplified()


def _block_run(groups: int, num_slices: int, num_surfaces: int = 120):
    from ogr_slip2d.search import BlockSearch

    p = _layered_slope()
    s = BlockSearch(method=_bishop(), num_slices=num_slices,
                    num_groups=groups, num_surfaces=num_surfaces, seed=5)
    return s.run(p)


_SAID_IT = "could not be sliced"


# ======================================================================
class TestABlockRunThatLosesSurfacesSaysSo:
    """Point (3). The note now reaches the search that needed it most."""

    def test_a_run_that_loses_surfaces_says_so(self):
        """Eight groups is ten vertices, which is nine segments, and the
        three material boundaries of this model add cuts of their own —
        against six slices to spend. Until v0.1.135 the surfaces went and
        the run said nothing."""
        r = _block_run(groups=8, num_slices=6)
        assert any(_SAID_IT in n for n in r.notes), r.notes

    def test_the_note_counts_what_was_lost(self):
        """A count, not an adjective: the user has to be able to tell one
        dropped surface from a search that lost almost everything."""
        r = _block_run(groups=8, num_slices=6)
        note = next(n for n in r.notes if _SAID_IT in n)
        assert str(r.valid_count) in note or "of the" in note, note
        assert "6" in note, note

    def test_a_run_within_the_budget_says_nothing(self):
        """A note that fires on everything is noise. Three groups is five
        vertices against thirty slices, with room for every crossing."""
        r = _block_run(groups=3, num_slices=30)
        assert not any(_SAID_IT in n for n in r.notes), r.notes

    def test_the_surfaces_are_really_lost_and_not_merely_reported(self):
        """Rule 7 applied to a note: it has to be describing something
        that happened. The tight run has to come back with fewer valid
        surfaces out of the same generated population."""
        tight = _block_run(groups=8, num_slices=6)
        roomy = _block_run(groups=8, num_slices=30)
        assert tight.total_count == roomy.total_count
        assert tight.valid_count < roomy.valid_count, (
            tight.valid_count, roomy.valid_count)


# ======================================================================
class TestTheSegmentCapIsAGuardAndNotAResolutionControl:
    """Point (4), and the shape it ended up in after two rejected fixes.

    ``max_segments`` bounds a walk that never re-emerges. It is NOT tied
    to the project's slice count, and this class pins the reasoning so the
    coupling is not re-attempted a third time.

    ``= num_slices`` — what the reference does — moves 25 bank models
    through the drift of the random stream alone: a walk that exhausts its
    budget returns ``None`` after consuming a different number of draws,
    so everything downstream shifts. ``min(max_segments, num_slices)``
    looked safer and is worse: on verification problem 19 at a one-metre
    manual segment length, where the slicer refuses all 5082 surfaces
    generated, the model declares 30 slices and the min changes nothing,
    while on the Ej_1 fixture at 14 slices, where no surface exceeds 7
    segments and the slicer refuses none, it moved Spencer from 1.147928
    to 1.161636 and changed the reported surface. Inert where the problem
    is, active where it is not.

    What the slicer refuses is SAID instead, by the class above.
    """

    @staticmethod
    def _cap(num_slices: int, max_segments: int = 30):
        from ogr_slip2d.search import PathSearch
        return PathSearch(method=_bishop(), num_slices=num_slices,
                          max_segments=max_segments).max_segments

    def test_the_cap_does_not_depend_on_the_slice_count(self):
        """The property the two rejected couplings would each have broken,
        and the reason it is asserted rather than assumed: both looked
        obviously right until they were measured."""
        assert {self._cap(n) for n in (10, 14, 20, 30, 40, 50)} == {30}

    def test_the_floor_of_five_survives(self):
        """A walk of fewer than five segments is not the search the user
        asked for."""
        assert self._cap(10, max_segments=2) == 5
        assert self._cap(10, max_segments=0) == 5

    def test_an_explicit_cap_is_honoured(self):
        """It is reachable in code even though ``build_search`` does not
        pass it — which is the whole of what its ficha called a class
        constant."""
        assert self._cap(30, max_segments=12) == 12
        assert self._cap(30, max_segments=100) == 100

    def test_no_walk_exceeds_the_cap(self):
        """The invariant the cap exists for, checked on the generated
        surfaces rather than on the attribute: a walk of N segments makes
        a polyline of at most N+1 vertices."""
        from ogr_slip2d.search import PathSearch

        p = _layered_slope()
        s = PathSearch(method=_bishop(), num_slices=30, num_surfaces=40,
                       seed=5, max_segments=6)
        r = s.run(p)
        assert r.evaluations
        for e in r.evaluations:
            assert len(e.surface.polyline.vertices) <= 7, (
                len(e.surface.polyline.vertices))
