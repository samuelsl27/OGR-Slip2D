# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A support that cannot be priced costs ITSELF, says so, and nothing else.

Defect D94, opened on 2026-09-11 out of implementing D62 and fixed here.
``resolve_support_terms`` answered ANY exception raised while computing
the supports with ``_EMPTY_TERMS``, which is the answer to "this model
carries no reinforcement". The two are indistinguishable to every one of
the nine methods, so what came back was the factor of safety of the bare
slope — valid, admissible, and with ``error_message`` and
``admissibility_note`` both empty.

Three invariants, and none of them is a captured value:

  * **it costs itself.** A model with two supports, one of which raises
    :class:`~ogr_core.support.SupportEvaluationError`, gives the factor of
    the same model with THAT support deleted — digit for digit — and not
    the factor of the model with BOTH deleted, which is what came out
    until this version. The anchor is an identity between two runs of the
    real solver, so it cannot consecrate a bug;
  * **it says so.** That same run carries ``details["support_failure"]``
    and the note repeats it. The distinction is the point: a model with no
    supports at all has no such key, so "no reinforcement" and "the
    reinforcement was lost" are two different answers and not one;
  * **anything else still raises.** A plugin whose ``force_at`` raises a
    plain ``RuntimeError`` is NOT swallowed: it reaches the caller. That
    is the policy the rest of the solve path already states — ``_analyse``
    catches ``ArithmeticError`` and not ``Exception`` because a TypeError
    is a defect in the code, and ``rapid_drawdown`` raises rather than
    "quietly analyse something else".

Plus one guard against the fix itself moving a number: the published
circle of the reference's verification problem 91 — fifteen sheets, the
densest reinforcement in the bank — must give exactly what it gave at
0.1.160. Those two digits are the whole "cero dígitos movidos" claim of
this version, written down where a test can fail on them.

The plugin types are reached by IDENTITY through ``type_ref``, so neither
the registry nor any module-level state is touched (rule 5) — the pattern
``test_support_silence_v1155.py`` set.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_supports_all_methods_v164 import (  # noqa: E402
    _circle, _fos, _project,
)

import pytest  # noqa: E402


# ======================================================================
# Fixtures
# ======================================================================
def _instance(type_id, head, tail, **kw):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id=type_id, head=Vertex(*head), tail=Vertex(*tail),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP, **kw)


# The fixture circle leaves the ground at x = 40.2 and x = 52.3. A is the
# horizontal axis the other support tests use, crossing at x = 46.714
# (slice 13); B dips across the toe end and crosses at x = 42.819
# (slice 5). Two axes rather than one because the whole question here is
# whether the SURVIVOR still counts when its neighbour cannot be priced,
# and two DIFFERENT slices so that a fix which merely kept the slice
# bookkeeping intact would not pass by accident.
_AXIS_A = ((43.5, 8.0), (54.0, 8.0))
_AXIS_B = ((42.0, 7.0), (52.0, 2.0))


def _nail_type(capacity=30.0):
    from ogr_core.support import SoilNail
    return SoilNail(tensile_capacity=capacity, plate_capacity=20,
                    bond_strength=8, out_of_plane_spacing=3.0)


def _blown_type(exc_factory):
    """A support type whose axial capacity refuses to be computed.

    Subclasses a REGISTERED type instead of registering a new one: the
    registry is module-level state and a test that writes to it leaks into
    every other test of the run (rule 5).
    """
    from ogr_core.support import SoilNail

    class _Exploding(SoilNail):
        def force_at(self, d, L, bond=None):
            raise exc_factory(self.id)

    return _Exploding(tensile_capacity=30, plate_capacity=20,
                      bond_strength=8, out_of_plane_spacing=3.0)


def _model(types, supports):
    """The fixture slope carrying an arbitrary set of support types."""
    p = _project(None)
    p.support_types = list(types)
    p.supports = list(supports)
    return p


def _evaluation_error(sid):
    from ogr_core.support import SupportEvaluationError
    return SupportEvaluationError(sid, "the demo type refuses to price")


def _runtime_error(_sid):
    return RuntimeError("boom")


def _both(exc_factory):
    """One sound support and one that cannot be priced, on two axes."""
    good, bad = _nail_type(), _blown_type(exc_factory)
    return _model([good, bad],
                  [_instance("soil_nail", *_AXIS_A, type_ref=good.id),
                   _instance("soil_nail", *_AXIS_B, type_ref=bad.id)])


def _only_the_good():
    """The same model with the unpriceable support DELETED."""
    good = _nail_type()
    return _model([good],
                  [_instance("soil_nail", *_AXIS_A, type_ref=good.id)])


def _neither():
    """The same slope with no reinforcement at all."""
    return _model([_nail_type()], [])


def _bishop(p):
    from ogr_slip2d.methods.bishop import BishopSimplified
    return _fos(BishopSimplified, p)


def _notes(project, result):
    from ogr_slip2d.support_integration import uncontributing_support_notes
    return uncontributing_support_notes(project, result)


# ======================================================================
class TestItCostsItselfAndNotTheOthers:
    """Part 1 — the closure criterion of D94, and rule 7 with a number.

    Until v0.1.161 all three models below gave ONE factor, because the
    exception took every support with it. Three different answers is the
    whole fix; two of them being equal is what says the surviving support
    really is still in the equations.
    """

    def test_the_factor_is_the_one_with_that_support_deleted(self):
        blown = _bishop(_both(_evaluation_error))
        assert blown.fos == _bishop(_only_the_good()).fos

    def test_and_not_the_one_with_every_support_deleted(self):
        # The defect. Without this assertion the test above passes on the
        # old code too, because there both models collapse to the bare
        # slope.
        blown = _bishop(_both(_evaluation_error))
        assert blown.fos != _bishop(_neither()).fos

    def test_the_survivor_really_is_carrying_load(self):
        # An identity, not a captured value: reinforcement can only raise
        # the factor of this slope, so the ordering is forced.
        assert _bishop(_neither()).fos < _bishop(_both(_evaluation_error)).fos

    def test_the_terms_still_say_there_is_reinforcement_here(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms

        p = _both(_evaluation_error)
        sl = slice_surface(p, _circle(), num_slices=25)
        terms = resolve_support_terms(p, _circle(), sl, 1.0)
        # ``present`` is what every consumer guards on. On the old code
        # this was False, which is precisely how the reinforcement left
        # the equations without a trace.
        assert terms.present is True
        assert terms.failure


# ======================================================================
class TestItSaysSo:
    """Part 2 — the reason reaches the RESULT, not just a note.

    It has to travel on the result because the note is only ever asked on
    the critical surface of a search: a surface evaluated by hand, by the
    CLI or by the verification bank went through none of that.
    """

    def test_the_result_carries_the_reason(self):
        det = _bishop(_both(_evaluation_error)).details or {}
        assert "support_failure" in det
        assert "refuses to price" in det["support_failure"], det

    def test_a_model_with_no_supports_carries_no_such_key(self):
        # "There is no reinforcement" and "the reinforcement was lost" are
        # two answers, and telling them apart is the defect.
        assert "support_failure" not in (_bishop(_neither()).details or {})

    def test_a_model_whose_supports_all_price_carries_no_such_key(self):
        assert "support_failure" not in (_bishop(_only_the_good()).details
                                         or {})

    def test_the_note_repeats_it_without_recomputing(self):
        p = _both(_evaluation_error)
        r = _bishop(p)
        notes = _notes(p, r)
        assert notes and "could not price" in notes[0], notes
        assert "refuses to price" in notes[0], notes

    def test_the_note_comes_from_the_field_and_not_a_second_run(self):
        # Blank the key and the sentence goes away, even though the model
        # would still raise if asked again. That is what says the note is
        # reading the result rather than re-deriving it.
        p = _both(_evaluation_error)
        r = _bishop(p)
        r.details.pop("support_failure")
        assert not any("could not price" in n for n in _notes(p, r))

    def test_every_method_carries_it(self):
        from test_supports_all_methods_v164 import _methods

        p = _both(_evaluation_error)
        for mid, cls in _methods():
            det = _fos(cls, p).details or {}
            assert "support_failure" in det, mid


# ======================================================================
class TestAnythingElseStillRaises:
    """Part 3 — the half of the fix that is about what is NOT caught.

    A blanket handler here is what let the defect live: it cannot tell a
    modelling refusal from a bug in the code, so it hid both. This pins
    that only the first one is answered.
    """

    def test_a_plain_runtime_error_reaches_the_caller(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms

        p = _both(_runtime_error)
        sl = slice_surface(p, _circle(), num_slices=25)
        with pytest.raises(RuntimeError):
            resolve_support_terms(p, _circle(), sl, 1.0)

    def test_and_it_reaches_it_through_the_solver_too(self):
        with pytest.raises(RuntimeError):
            _bishop(_both(_runtime_error))

    def test_the_narrow_handler_is_the_one_in_the_source(self):
        """The shape D94 closes on cannot come back through a refactor.

        Comments are stripped before looking: the handler that used to be
        here is QUOTED in the comment that replaced it, which is the whole
        point of that comment, and a check that cannot tell the two apart
        would be measuring the prose.
        """
        import inspect

        from ogr_slip2d import support_integration as si
        src = inspect.getsource(si.resolve_support_terms)
        codigo = [l.split("#")[0].rstrip() for l in src.splitlines()]
        codigo = [l for l in codigo if l.strip()]
        assert not any("except Exception" in l for l in codigo), codigo
        assert any("except SupportEvaluationError" in l for l in codigo)
        # And that the two lines the criterion greps for as a PAIR are not
        # adjacent any more: a blanket handler answering with the "no
        # reinforcement" terms is the defect itself.
        for a, b in zip(codigo, codigo[1:]):
            assert not ("except Exception" in a
                        and "return _EMPTY_TERMS" in b), (a, b)


# ======================================================================
class TestTheReasonIsCountedAsASilence:
    """Part 4 — it joins the five reasons D62 already counts.

    A support that could not be priced is a support that put no force on
    the surface, so it belongs in the same tally; it is listed FIRST
    because the other five describe what the model IS and this one
    describes what could not be read.
    """

    def test_the_reason_list_names_it(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import (SUPPORT_NOT_PRICEABLE,
                                                    compute_support_effects)

        p = _both(_evaluation_error)
        sl = slice_surface(p, _circle(), num_slices=25)
        out: list = []
        compute_support_effects(p, _circle(), sl, reasons=out)
        assert [why for _sid, why in out] == [SUPPORT_NOT_PRICEABLE], out

    def test_asking_for_the_reasons_does_not_change_the_effects(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import compute_support_effects

        p = _both(_evaluation_error)
        sl = slice_surface(p, _circle(), num_slices=25)
        quiet = compute_support_effects(p, _circle(), sl)
        asked = compute_support_effects(p, _circle(), sl, reasons=[])
        assert len(quiet) == len(asked) == 1
        assert quiet[0].force_magnitude == asked[0].force_magnitude


# ======================================================================
class TestNothingMoved:
    """Part 5 — the published circle of the densest reinforced model.

    Verification problem 91 of the reference's bank: fifteen geosynthetic
    sheets on the circle the manual publishes (centre 4.658, 15.000,
    R 10.934), 30 slices. These were the digits OGR 0.1.160 gives, measured
    on 2026-09-12 before a line of v0.1.161 was written, and that version
    could not move them.

    Anchored to a published MODEL rather than to a fixture because the
    claim being made is about the verification bank: "cero dígitos
    movidos" in a changelog is worth what the test that can fail on it is
    worth. Which is why v0.1.172 UPDATED one of the two rather than
    quietly widening the comparison — this case is the instrument, and an
    instrument that is relaxed the first time it reads something stops
    being one.

    WHAT MOVED IN v0.1.172 (D116) AND WHY IT IS DECLARED HERE. Spencer
    goes 0.9641449174231770 -> 0.9641378773625315, seven parts in a
    million. The cause is the contraction test: a branch is no longer
    declared converged on a single step that fell under the tolerance in
    the oscillating transient. Bishop does not move by one digit, and it
    cannot — it never enters ``interslice.py``, which only Spencer and GLE
    do — and that is half of what says the cause is the one claimed.

    The other half is the DIRECTION, measured on this very circle by
    tightening the tolerance until the answer stops moving:

        1e-10   0.9640803604041095      <- the converged answer
        1e-08   0.9640803660734361
        1e-06   0.9640806409312945
        1e-04   0.9641378773625315      <- what this case now pins

    The model asks for 1e-4. At that tolerance v0.1.171 sat 6.455e-5 from
    the converged answer and v0.1.172 sits 5.751e-5: the digit moved
    TOWARDS it, by a tenth of the tolerance that was requested. And at
    1e-6 and below the two versions agree to nine figures and more, which
    is the statement that there was never anything wrong where the
    tolerance was tight enough to see it.
    """

    BANCO = Path(r"C:/Samuel/OpenGeoRock_Slip2d/referencias/Ejemplos"
                 r"/RS2_Verification Manuals"
                 r"/02_Slide2_Slope_Stability_Verification_Manual"
                 r"/02_Slide2_Problema091")
    CIRCULO = (4.658, 15.0, 10.934)
    #: Bishop is the CONTROL and has not moved since 0.1.160. Spencer was
    #: 0.9641449174231770 until v0.1.172; see the class docstring for the
    #: measurement that authorised the change.
    ESPERADO = {"bishop_simplified": 0.9835740303049271,
                "spencer": 0.9641378773625315}

    def _skip_if_absent(self):
        # The bank lives outside this repository (and outside git), so the
        # test has to be able to say "not measurable here" rather than
        # fail on a machine that does not have it.
        if not (self.BANCO / "modelo.ogr").exists():
            pytest.skip("the verification bank is not on this machine")

    def test_the_fifteen_sheets_give_what_they_gave(self):
        self._skip_if_absent()
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle

        p = Project.load(str(self.BANCO / "modelo.ogr"))
        cx, cy, r = self.CIRCULO
        surf = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        for mid, esperado in self.ESPERADO.items():
            ev = GridSearch(method=build_method(p, mid, 30),
                            num_slices=30, min_area=0.0)
            got = ev.evaluate_circle(p, surf).fos
            assert got == esperado, "%s: %r" % (mid, got)
