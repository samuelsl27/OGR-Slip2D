# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A shear capacity that cannot be computed costs the shear, and says so.

Defect D98, opened out of auditing the silences of D62 and fixed here.
``compute_support_effects`` wrapped ``shear_at`` in a blanket
``except Exception`` that set ``V = 0.0`` and recorded NOTHING. A type
declaring ``SUPPORTS_SHEAR`` whose ``shear_at`` raised therefore lost half
of its declared capacity and KEPT CONTRIBUTING with the axial half, which
is precisely why the D62 note could not mention it: that note counts
supports that put NO force on the surface, and this one puts some.

The result is a factor of safety computed with less reinforcement than the
model carries, indistinguishable from a correct answer — the same shape of
defect as D94 one step down, and the reason it needs a seventh reason with
a sentence of its own rather than a seventh entry in the table of six.

Four invariants, none of them a captured value:

  * **the shear is worth something.** With ``shear_at`` sound the factor is
    strictly higher than with ``SUPPORTS_SHEAR`` off. Without this the
    three below would pass on a quantity that was zero anyway (rule 7);
  * **breaking it costs exactly the shear.** With ``shear_at`` raising, the
    factor is BIT FOR BIT the one with ``SUPPORTS_SHEAR`` off — not
    "close": an identity between two runs of the real solver — while the
    support is still in the equilibrium with its axial force;
  * **and now it says so.** The reason reaches ``reasons`` naming the
    exception class, the note repeats it, and it is kept OUT of the count
    of supports that put no force: a lone support that lost only its shear
    must never produce "The only support placed puts no force";
  * **the written contract holds for BOTH halves.** ``docs/plugins.md``
    says ``force_at`` *and* ``shear_at`` may raise
    :class:`~ogr_core.support.SupportEvaluationError` and that it is the
    only exception the engine catches. That was false for ``shear_at``:
    this guard sat INSIDE the per-support ``try`` D94 added, so it caught
    the typed exception first and discarded it. A plugin honouring the
    contract to the letter got the one answer the contract rules out.

The plugin types are reached by IDENTITY through ``type_ref``, so neither
the registry nor any module-level state is touched (rule 5) — the pattern
``test_support_silence_v1155.py`` set and ``test_support_failure_v1161.py``
followed.
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
# The fixture circle leaves the ground at x = 40.2 and x = 52.3; this is
# the horizontal axis the other support tests use, crossing at x = 46.714.
_AXIS = ((43.5, 8.0), (54.0, 8.0))


def _instance(type_ref):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id="soil_nail", head=Vertex(*_AXIS[0]), tail=Vertex(*_AXIS[1]),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP, type_ref=type_ref)


def _kw(shear):
    return dict(tensile_capacity=30.0, plate_capacity=20.0,
                bond_strength=8.0, out_of_plane_spacing=3.0,
                shear_capacity=shear)


#: Big enough that losing it is unmistakable, and the whole point of the
#: first block is that this test does not have to trust that sentence.
_SHEAR = 90.0


def _sound():
    """A nail whose shear capacity is declared AND computable."""
    from ogr_core.support import SoilNail
    return SoilNail(**_kw(_SHEAR))


def _no_shear():
    """The same nail with the gate closed: the axial half alone."""
    from ogr_core.support import SoilNail

    class _Axial(SoilNail):
        SUPPORTS_SHEAR = False

    return _Axial(**_kw(_SHEAR))


def _blown_shear(exc_factory):
    """The same nail whose ``shear_at`` refuses to be computed.

    Subclasses a REGISTERED type instead of registering a new one: the
    registry is module-level state and a test that writes to it leaks into
    every other test of the run (rule 5). ``force_at`` is untouched on
    purpose — the defect is that the AXIAL half went on counting.
    """
    from ogr_core.support import SoilNail

    class _ExplodingShear(SoilNail):
        def shear_at(self, d, L):
            raise exc_factory(self.id)

    return _ExplodingShear(**_kw(_SHEAR))


def _model(stype):
    p = _project(None)
    p.support_types = [stype]
    p.supports = [_instance(stype.id)]
    return p


def _type_error(_sid):
    return TypeError("the demo type cannot multiply those")


def _evaluation_error(sid):
    from ogr_core.support import SupportEvaluationError
    return SupportEvaluationError(sid, "the demo type refuses to price shear")


def _result(p):
    """A LEMResult on the fixture circle, from the real solver."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    return _fos(BishopSimplified, p)


def _bishop(p):
    return _result(p).fos


def _reasons(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(p, _circle(), num_slices=25)
    out: list = []
    compute_support_effects(p, _circle(), sl, reasons=out)
    return out


def _effects(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(p, _circle(), num_slices=25)
    return compute_support_effects(p, _circle(), sl)


def _notes(project, result):
    from ogr_slip2d.support_integration import uncontributing_support_notes
    return uncontributing_support_notes(project, result)


# ======================================================================
class TestTheShearIsWorthSomething:
    """Rule 7, and the anchor the other three blocks stand on.

    Measuring "breaking the shear changes nothing" proves nothing if the
    shear was zero to begin with — which is exactly the state of the only
    reinforced model of the verification bank that declares shear at all
    (problem 50: fourteen nails, ``shear_capacity = 0.0``).
    """

    def test_a_computable_shear_raises_the_factor_of_safety(self):
        assert _bishop(_model(_sound())) > _bishop(_model(_no_shear()))

    def test_and_it_is_the_second_vector_and_not_a_bigger_axial_one(self):
        """The difference between the two runs is one vector of modulus V.

        NOT ``hypot(axial, shear)``: with ``TANGENT_TO_SLIP`` the axial
        force follows the slip tangent while the shear is perpendicular to
        the SUPPORT AXIS, so the two are not perpendicular to each other
        and no Pythagoras holds between them. What does hold is that the
        only thing the shear adds is ``V`` along that perpendicular, and
        ``V = shear_capacity / out_of_plane_spacing`` by the type's own
        formula -- which is the reference's "a SECOND vector, not a bigger
        axial one" stated as arithmetic.
        """
        import math

        a = _effects(_model(_no_shear()))[0]
        b = _effects(_model(_sound()))[0]
        delta = math.hypot(b.force_h - a.force_h, b.force_v - a.force_v)
        assert delta == pytest.approx(_SHEAR / 3.0, rel=1e-12)


# ======================================================================
class TestBreakingItCostsExactlyTheShear:
    """The defect's numerical claim, as an identity between two runs."""

    def test_the_factor_is_the_one_with_the_shear_gate_closed(self):
        blown = _bishop(_model(_blown_shear(_type_error)))
        assert blown == _bishop(_model(_no_shear()))

    def test_and_not_the_one_with_no_support_at_all(self):
        """It costs the shear and NOT the support: the axial still counts.

        Without this the test above would also pass for a fix that threw
        the whole support away, which is the D94 answer and the wrong one
        here.
        """
        bare = _project(None)
        bare.support_types, bare.supports = [], []
        assert _bishop(_model(_blown_shear(_type_error))) > _bishop(bare)

    def test_the_support_is_still_in_the_equilibrium(self):
        e = _effects(_model(_blown_shear(_type_error)))
        assert len(e) == 1
        assert e[0].force_magnitude > 0


# ======================================================================
class TestAndNowItSaysSo:
    """The defect itself: all of the above was already true in silence."""

    def test_the_reason_names_the_exception_class(self):
        from ogr_slip2d.support_integration import SUPPORT_SHEAR_FAILED

        p = _model(_blown_shear(_type_error))
        assert _reasons(p) == [(p.supports[0].id,
                                SUPPORT_SHEAR_FAILED + ":TypeError")]

    def test_a_sound_shear_records_nothing(self):
        assert _reasons(_model(_sound())) == []

    def test_the_note_says_the_shear_was_not_counted(self):
        p = _model(_blown_shear(_type_error))
        note = " ".join(_notes(p, _result(p)))
        assert "only its axial capacity" in note, note
        assert "shear_at raised TypeError" in note, note

    def test_and_it_is_not_counted_among_the_ones_that_put_no_force(self):
        """The trap this defect is made of.

        The support DOES put force on the surface. Filing its reason with
        the other six would have produced "The only support placed puts no
        force on the reported surface", which is false, or — once the
        reason is filtered out but the tail still runs — "0 of the 1
        supports placed put no force", which is worse, because it is a
        sentence about nothing at all.
        """
        p = _model(_blown_shear(_type_error))
        notes = _notes(p, _result(p))
        assert len(notes) == 1, notes
        assert "puts no force" not in notes[0], notes
        assert "put no force" not in notes[0], notes

    def test_a_model_with_a_sound_support_stays_quiet(self):
        p = _model(_sound())
        assert _notes(p, _result(p)) == []

    def test_the_sentence_avoids_the_substrings_the_bank_reserves(self):
        """Three closures of the verification bank grep whole runs.

        ``d40()`` fires on "stable" AND "head" appearing in any warning,
        ``d69()`` on "edge of the search grid" and ``d71()`` on
        "path_optimize". A new sentence carrying one of them would break a
        closure that has nothing to do with this defect.
        """
        p = _model(_blown_shear(_type_error))
        note = _notes(p, _result(p))[0]
        assert not ("stable" in note and "head" in note), note
        assert "edge of the search grid" not in note, note
        assert "path_optimize" not in note, note


# ======================================================================
class TestTheContractHoldsForBothHalves:
    """``SupportEvaluationError`` from ``shear_at`` reaches D94's handler.

    ``docs/plugins.md`` states that both ``force_at`` and ``shear_at``
    answer with a number or raise it, and that it is the ONLY exception
    the engine catches. Until this version that was false for ``shear_at``
    in both directions at once: the typed exception was swallowed by a
    handler that was never meant to see it, and an untyped one was
    swallowed too.
    """

    def test_the_support_is_dropped_whole_and_not_just_its_shear(self):
        from ogr_slip2d.support_integration import SUPPORT_NOT_PRICEABLE

        p = _model(_blown_shear(_evaluation_error))
        assert _reasons(p) == [(p.supports[0].id, SUPPORT_NOT_PRICEABLE)]
        assert _effects(p) == []

    def test_the_reason_travels_on_the_result(self):
        p = _model(_blown_shear(_evaluation_error))
        det = _result(p).details or {}
        assert "refuses to price shear" in det.get("support_failure", ""), det

    def test_and_the_note_says_it_could_not_be_priced(self):
        p = _model(_blown_shear(_evaluation_error))
        note = _notes(p, _result(p))[0]
        assert "could not price" in note, note

    def test_a_plain_bug_is_still_not_allowed_to_kill_the_run(self):
        """The half of the policy that does NOT change.

        "A plugin must not kill a run" stays for ``shear_at``: what
        changes is the silence, not the survival. This is the asymmetry
        with ``force_at``, where a plain exception propagates, and it is
        deliberate — losing one vector is recoverable and saying so costs
        nothing, losing the axial capacity is not.
        """
        assert _bishop(_model(_blown_shear(_type_error))) > 0


# ======================================================================
class TestTheShapeInTheSource:
    """The shape D98 closes on cannot come back through a refactor.

    Comments are stripped before looking, for the reason
    ``test_support_failure_v1161.py`` gives: the comment that explains this
    handler QUOTES what it replaced and names the defect, and a check that
    cannot tell code from prose would be measuring the prose.
    """

    def _code(self, fn):
        import inspect

        src = inspect.getsource(fn)
        lines = [l.split("#")[0].rstrip() for l in src.splitlines()]
        return [l for l in lines if l.strip()]

    def _shear_handler(self):
        """The eight lines that follow the call to ``shear_at``.

        Anchored on the CALL and not on "the only ``except Exception``":
        there is a second one in this function, the guard that reads the
        failure direction, and it is a reported anomaly of its own rather
        than something this test may assume away.
        """
        from ogr_slip2d import support_integration as si

        code = self._code(si.compute_support_effects)
        call = [i for i, l in enumerate(code) if "stype.shear_at(" in l]
        assert len(call) == 1, code
        return code[call[0]:call[0] + 8]

    def test_the_swallowing_handler_records_the_reason(self):
        block = self._shear_handler()
        wide = [i for i, l in enumerate(block) if "except Exception" in l]
        assert wide, block
        assert any("SUPPORT_SHEAR_FAILED" in l for l in block[wide[0]:]), block

    def test_the_typed_exception_is_let_through_first(self):
        block = self._shear_handler()
        typed = [i for i, l in enumerate(block)
                 if "except SupportEvaluationError" in l]
        wide = [i for i, l in enumerate(block) if "except Exception" in l]
        assert typed and wide, block
        # Order is the whole fix: Python takes the first matching clause,
        # and ``SupportEvaluationError`` is a ``RuntimeError``, so a wide
        # handler placed first would swallow it exactly as before.
        assert typed[0] < wide[0], block

    def test_the_note_reads_the_same_constant_that_writes_it(self):
        from ogr_slip2d import support_integration as si

        code = self._code(si.uncontributing_support_notes)
        assert any("SUPPORT_SHEAR_FAILED" in l for l in code), code
