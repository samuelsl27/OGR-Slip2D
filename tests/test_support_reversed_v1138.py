# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A reinforcement drawn back-to-front must not pass in silence.

``head`` is the end at the slope FACE and ``tail`` the anchored one, and
until v0.1.138 nothing anywhere checked it. THREE separate things read
that convention:

  * ``GroutedTieback.capacity_modes`` and ``SoilNail.capacity_modes``
    measure the stripping length ``L_i`` from the head;
  * the same two measure the pullout length ``L_o`` from the tail;
  * since v0.1.112 ``_support_force_angle`` points the force head to tail
    under ``parallel_to_support`` and ``bisector``.

*Add Support* is first click, second click. Drawing the bolt the other
way round therefore reverses all three AT ONCE, which is exactly why the
result does not look wrong: it looks like a different, plausible number.

Measured on verification problem 59 of the reference bank with OGR
0.1.137, on the circle its figure 59.2 publishes — the same tieback, the
same surface, only the two ends swapped:

    as drawn      Bishop 0.756987    Spencer 0.764945
    ends swapped  Bishop 0.407783    Spencer 0.495522

The DIRECTION of that move is not what makes this a defect, and the note
does not predict it. A bolt read as anchoring into the stable ground when
it really anchors inside the sliding mass reports the HIGHER number,
which is the unsafe half and the one nobody goes back to question.

What this file protects:

1. **The note fires on the reversed sense** — the same bolt, the same
   surface, only the two ends swapped. This is the closure criterion of
   defect D40 of the bank, and it is what fails if the note is ever
   withdrawn.
2. **It stays quiet on the correct sense**, on a bolt that never crosses,
   on a project with no supports, and on a result with no slices. A
   warning that fires on every run teaches the reader to skip warnings —
   the doctrine of ``test_grid_edge_note_v1102.py``.
3. **It reaches ``run_analysis().warnings``** attributed to the method
   that produced the surface, which is the channel ``resultados.json``
   reads under ``avisos``.
4. **It changes no number.** The note is a diagnosis, not a force.
5. **It abstains on a bolt that crosses the surface TWICE**, which is the
   false positive this check shipped with for one afternoon and the part
   worth remembering. The first version read the FIRST crossing and
   compared both ends against the tangent there — and on verification
   problem 85 that extrapolated one tangent straight past a second
   crossing and reported a correctly drawn tieback as reversed. The
   premise the whole rule rests on, *one crossing, one end on each side*,
   was simply never checked. Two crossings put both ends OUTSIDE the
   sliding mass: the bolt is a chord through the mass, not an anchor
   reaching past it. The tripwire in
   ``TestTheFirstCrossingIsNotEnoughOnItsOwn`` re-runs the old
   arithmetic and asserts it still gives the wrong answer, so reverting
   to it cannot pass quietly.

Assertions match on SUBSTRINGS, never on the whole sentence, so the
wording can be improved without breaking the test; what is pinned is the
actionable content — that the head is named, and which side it is on.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

from test_supports_all_methods_v164 import (  # noqa: E402
    _circle, _fos, _nail, _project,
)

# The fixture nail runs from (43.5, 8.0) on the slope face to (54.0, 8.0)
# inside the slope; the fixture circle is centred (38, 26) with r = 20, so
# the head sits 18.82 from the centre (inside the arc, in the sliding
# mass) and the tail 24.08 (outside it, in the stable ground). Swapping
# the two ends leaves the SEGMENT untouched — same crossing, same length,
# same everything the geometry can see. Only the labels move, which is the
# whole point of the check.
_HEAD = (43.5, 8.0)
_TAIL = (54.0, 8.0)


def _notes(project, result):
    from ogr_slip2d.support_integration import reversed_support_notes
    return reversed_support_notes(project, result)


def _result(project):
    """A LEMResult on the fixture circle, from the real solver."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    return _fos(BishopSimplified, project)


def _sliced(project):
    """Surface + slices only, for cases the solver need not price."""
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, _circle(), num_slices=25)
    assert sl is not None
    return SimpleNamespace(surface=_circle(), slices=sl)


# ======================================================================
class TestTheNoteFiresWhenItShould:
    """Part 1 — the closure criterion of D40."""

    def test_the_reversed_sense_is_reported(self):
        """The same bolt, the same surface, the ends swapped."""
        p = _project(_nail(head=_TAIL, tail=_HEAD))
        notes = _notes(p, _result(p))
        assert notes, ("the bolt was drawn head-first into the stable "
                       "ground and nothing said so")
        assert len(notes) == 1, notes

    def test_the_note_names_the_head_and_the_side_it_is_on(self):
        p = _project(_nail(head=_TAIL, tail=_HEAD))
        note = _notes(p, _result(p))[0]
        assert "head at (54.00, 8.00)" in note, note
        assert "stable side" in note, note
        assert "tail at (43.50, 8.00)" in note, note
        assert "sliding mass" in note, note

    def test_it_reaches_the_warnings_of_a_full_run(self):
        """The channel ``resultados.json`` reads under ``avisos``."""
        from ogr_slip2d.analysis_runner import run_analysis
        p = _project(_nail(head=_TAIL, tail=_HEAD))
        out = run_analysis(p, ["bishop_simplified"])
        hits = [w for w in out.warnings if "stable side" in w]
        assert hits, out.warnings
        assert hits[0].startswith("bishop_simplified: "), hits[0]

    def test_a_pile_measured_from_the_top_is_reported_too(self):
        """Even where the numbers provably do not move.

        A ``PileMicropile`` is ``MEASURED_FROM_TOP``, so
        ``compute_support_effects`` re-derives its crest from the two y
        values and the capacity comes out the same either way; with
        ``tangent_to_slip`` the force direction ignores the axis as well.
        The model is still drawn wrong, the convention is documented for
        every type, and the orientation is a setting the user can change
        afterwards — so the check does not carve out an exception it
        would then have to keep in step with the types.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      SupportInstance)
        upside_down = SupportInstance(
            type_id="pile_micropile",
            head=Vertex(43.0, 0.0), tail=Vertex(43.0, 10.0),
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.TANGENT_TO_SLIP,
        )
        p = _project(upside_down)
        assert _notes(p, _sliced(p)), "an upside-down pile said nothing"


# ======================================================================
class TestTheNoteStaysQuietWhenItShould:
    """Part 2 — the abstentions, each with a reason."""

    def test_the_correct_sense_says_nothing(self):
        p = _project(_nail(head=_HEAD, tail=_TAIL))
        assert _notes(p, _result(p)) == []

    def test_a_bolt_that_never_crosses_says_nothing(self):
        """It contributes no force at all — a different defect, not this
        one, and one this note must not start claiming."""
        p = _project(_nail(head=(2.0, 1.0), tail=(12.0, 1.0)))
        assert _notes(p, _result(p)) == []

    def test_a_project_with_no_supports_says_nothing(self):
        p = _project()
        assert _notes(p, _result(p)) == []

    def test_a_result_with_no_slices_says_nothing(self):
        p = _project(_nail(head=_TAIL, tail=_HEAD))
        assert _notes(p, SimpleNamespace(surface=_circle(), slices=None)) == []
        assert _notes(p, SimpleNamespace(surface=None, slices=None)) == []

    def test_an_end_lying_on_the_surface_has_no_side(self):
        """A bolt whose head sits ON the slip surface is not reversed; it
        is degenerate, and the note has no side to name."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.support_integration import (_slip_polyline,
                                                    reversed_support_notes)
        p = _project(_nail(head=_TAIL, tail=_HEAD))
        r = _result(p)
        cut = p.supports[0].intersection_with_polyline(
            _slip_polyline(r.surface, r.slices))
        assert cut is not None
        p.supports[0].head = Vertex(cut[0], cut[1])
        assert reversed_support_notes(p, r) == []


# ======================================================================
class TestNothingElseMoves:
    """Part 3 — a diagnosis, not a force."""

    def test_the_factor_of_safety_is_untouched_by_asking(self):
        """Computed twice on the same project, with the note asked in
        between. Compared against the value this same process produced,
        never against a captured constant."""
        p = _project(_nail(head=_HEAD, tail=_TAIL))
        before = _result(p).fos
        _notes(p, _result(p))
        after = _result(p).fos
        assert before == after, (before, after)
        assert math.isfinite(before)

    def test_the_reversed_bolt_still_computes_a_factor(self):
        """The note is not a rejection: the geometry stays legal and the
        analysis still returns a number."""
        p = _project(_nail(head=_TAIL, tail=_HEAD))
        r = _result(p)
        assert r.is_valid and math.isfinite(r.fos), r
        assert _notes(p, r), "and it is still reported"

# ======================================================================
def _chord_project(head, tail):
    """The shape of verification problem 85: a bolt that crosses TWICE.

    Boundary, bolt and circle are the ones measured in the bank, so the
    case is a real one and not a construction: external boundary
    (15,10)-(57,10)-(57,30)-(25,30) closed, whose closing edge from
    (25,30) back to (15,10) IS the slope face; a horizontal tieback whose
    head sits exactly on that face at (20, 20); and the shallow surface
    Bishop reports there, centred (42.5556, 32.7222) with R 12.8064,
    which dips only to y = 19.92 and so cuts the bolt at x = 41.10 and
    x = 44.02.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance, UserDefined)
    ext = Polyline(vertices=[Vertex(15, 10), Vertex(57, 10),
                             Vertex(57, 30), Vertex(25, 30)], closed=True)
    ext.ensure_ccw()
    p = Project("chord")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    p.support_types = [UserDefined(points=[(0.0, 9000.0)],
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="user_defined",
        head=Vertex(*head), tail=Vertex(*tail),
        force_application=ForceApplication.ACTIVE,
        orientation=ForceOrientation.HORIZONTAL)]
    return p


def _chord_result(project):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    circle = SlipCircle(centre_x=42.555556, centre_y=32.722222,
                        radius=12.806436)
    sl = slice_surface(project, circle, num_slices=50)
    assert sl is not None
    return SimpleNamespace(surface=circle, slices=sl)


class TestABoltThatCrossesTwice:
    """Part 4 — the false positive this check was born with.

    The first version of the note read the FIRST crossing and compared
    both ends against the tangent there. On problem 85 that extrapolated
    one tangent straight past a SECOND crossing and reported a correctly
    drawn tieback as reversed. The premise the whole rule rests on — one
    crossing, one end on each side — was never being checked.

    Both ends of a bolt that crosses twice are OUTSIDE the sliding mass:
    it is a chord through the mass, not an anchor reaching past it, and
    there is no head/tail asymmetry to read. Abstaining is the honest
    answer, and it is not the same as agreeing the bolt is right.
    """

    def test_the_bolt_really_does_cross_twice(self):
        """The premise of the other two tests, measured and not assumed."""
        from ogr_slip2d.support_integration import _slip_polyline
        p = _chord_project((20.0, 20.0), (57.0, 20.0))
        r = _chord_result(p)
        cuts = p.supports[0].intersections_with_polyline(
            _slip_polyline(r.surface, r.slices))
        assert len(cuts) == 2, cuts
        assert 41.0 < cuts[0][0] < 41.2, cuts
        assert 43.9 < cuts[1][0] < 44.1, cuts

    def test_a_correctly_drawn_bolt_is_not_called_reversed(self):
        """The head at (20, 20) lies ON the slope face, which is where a
        head belongs. Nothing may be said about it."""
        p = _chord_project((20.0, 20.0), (57.0, 20.0))
        assert _notes(p, _chord_result(p)) == []

    def test_and_neither_is_the_reversed_one(self):
        """The check ABSTAINS, it does not switch sides: with two
        crossings it cannot tell, and it must not pretend to."""
        p = _chord_project((57.0, 20.0), (20.0, 20.0))
        assert _notes(p, _chord_result(p)) == []


class TestTheFirstCrossingIsNotEnoughOnItsOwn:
    """The exact arithmetic that produced the false positive, kept as a
    tripwire: if someone reverts to reading ``intersection_with_polyline``
    the old answer comes straight back, and this says so."""

    def test_the_old_single_crossing_rule_would_have_fired(self):
        from ogr_slip2d.support_integration import (_side_of_slip,
                                                    _slip_polyline,
                                                    _slip_tangent_at_x)
        p = _chord_project((20.0, 20.0), (57.0, 20.0))
        r = _chord_result(p)
        sup = p.supports[0]
        ix, iy, _d = sup.intersection_with_polyline(
            _slip_polyline(r.surface, r.slices))
        slope = _slip_tangent_at_x(r.slices, ix)
        head = _side_of_slip(sup.head.x, sup.head.y, ix, iy, slope)
        tail = _side_of_slip(sup.tail.x, sup.tail.y, ix, iy, slope)
        assert head < 0 and tail > 0, (head, tail)
        assert _notes(p, r) == [], "and the crossing count is what stops it"
