# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A method never hands out a number that is not one, nor a failure without a reason.

WHAT INVARIANT THIS PROTECTS, and why nothing weaker would do.

A limit equilibrium method can reach a quotient with no answer — a driving
moment that vanishes, an iteration that does not converge — and until
v0.1.152 the answer to that was ``math.nan`` or ``math.inf`` sitting in the
``fos`` field of a ``LEMResult``. The failure WAS declared alongside it:
every one of those fourteen return paths also set ``converged=False`` and an
``error_message``. What was missing is that nothing obliged a reader to look.

That is not a hypothetical. Measured chain, problem 79 of the verification
bench between 0.1.130 and 0.1.147: method → ``resultados_modelo_2.json`` →
the comparison generator → the comparison table → the problem sheet.
Seventeen versions, one row turned from REVIEW into DISCREPANCY, and what
stopped it was a human auditor wondering why one case said ``nan`` and the
other did not. The reader that let it through evaluated a published circle
and wrote ``round(float(r.fos), 6)`` without asking ``is_valid``.

A ``nan`` is the worst possible shape for that value. It survives
``float()`` and ``round()``; it compares False against every bound, so a
range check reads it as "out of range" and a sort puts it wherever the
algorithm happens to look first; and it prints as a short lowercase word
that looks like a label. ``None`` raises where the mistake is made.

WHAT EACH GROUP OF TESTS PINS

* ``TestSymmetricMassHasNoFactor`` — the geometric case, on all nine
  methods. A circle whose sliding mass is symmetric about the vertical
  through its centre has a driving moment of zero, so there is genuinely no
  factor of safety. Measured on this fixture at 0.1.151: Σ W·sin α =
  1.49e-13 against a largest single term of 51.1, a relative residual of
  2.9e-15 — twelve orders of magnitude inside the 1e-9 guard, so the case
  is reached deterministically and not by luck of rounding.
  On 0.1.151 the nine methods answered it six different ways: ``inf``
  (Bishop, both Janbus, Fellenius), ``nan`` (Spencer, GLE) and ``5.0``
  (Corps #1, Corps #2, Lowe-Karafiath).
* ``TestAMethodCannotHandOutANonNumber`` — the structural half, with no
  geometry: the three things ``LEMResult.__post_init__`` refuses.
* ``TestNoWriterSerialisesANonNumber`` — the writers. ``json.dumps`` emits
  bare ``NaN`` and ``Infinity`` unless told not to, and neither is valid
  JSON, so a results file written that way parses in Python and nowhere
  else. ``allow_nan=False`` is the external, objective check.
* ``TestEveryMethodSaysWhy`` — the reason is a named constant, not a loose
  string, so a run can count surfaces by reason and the next reason cannot
  be born as free text.

The 5.0 of the three prescribed-inclination methods deserves its own note,
because it is the worst of the three answers and it was NOT in the report
that opened this defect. It is the TOP OF THEIR OWN SAMPLING GRID
(``modified_swedish.py``, ``grid = [0.2 … 5.0]``), returned by the
nearest-residual fallback when no orientation brackets a root, and it came
out with ``converged=False`` and an EMPTY ``error_message``. A ``nan`` at
least looks wrong. A 5.0 looks like a slope with a factor of safety of five.
It is the shape of defect D20 — a fallback wearing the clothes of a result —
appearing a third time, with the same number.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import json
import math

import pytest

# ======================================================================
# The fixture: flat ground, one material, and a circle centred on it.
#
# Flat and symmetric on purpose. With the centre at mid-span of a level
# ground surface, every slice pairs with its mirror: equal weight, opposite
# base angle. Σ W·sin α therefore cancels, and there is no driving moment
# for a factor of safety to be the ratio of.
# ======================================================================
GROUND_Y = 30.0
CENTRE_X = 50.0
#: Above the ground, so the arc dips into the soil and comes back out of it
#: symmetrically. The mass is a lens, and its own weight has nowhere to go.
CENTRE_Y = GROUND_Y + 10.0
RADIUS = 20.0
NUM_SLICES = 50

#: Σ W·sin α over the fixture at 0.1.151, and the largest single term it is
#: made of. Recorded because the guard it has to cross is ABSOLUTE
#: (``abs(denominator) < 1e-9``), so the margin — not the residual alone —
#: is what says the case is reached on purpose.
MEASURED_RESIDUAL = 1.49e-13
MEASURED_LARGEST_TERM = 51.1


def _flat_block(name="D56"):
    """A rectangular block of one material, ground at ``GROUND_Y``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0),
        Vertex(100, GROUND_Y), Vertex(0, GROUND_Y),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    # Real strength, and that matters: with c = 0 and phi = 0 the surface
    # would be caught by ``surface_has_no_shear_strength`` instead, which is
    # a different condition with a different answer (F = 0 exactly).
    p.materials = [Material(
        name="Soil", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=20.0, friction_angle=25.0))]
    return p


_CACHE: dict = {}


def _symmetric_results() -> dict:
    """``{method_id: LEMResult}`` for every registered method.

    Cached: nine methods over fifty slices is the expensive part of this
    file, and every group below asks the same question of the same objects.
    """
    if "results" not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle

        project = _flat_block()
        out = {}
        for mid, cls in method_registry().items():
            search = GridSearch(method=cls(), num_slices=NUM_SLICES,
                                min_area=0.0)
            out[mid] = search.evaluate_circle(
                project,
                SlipCircle(centre_x=CENTRE_X, centre_y=CENTRE_Y,
                           radius=RADIUS))
        _CACHE["results"] = out
    return _CACHE["results"]


def _one_result():
    """Any single result from the sweep, for the writer tests."""
    for res in _symmetric_results().values():
        if res is not None:
            return res
    raise AssertionError("the fixture produced no result at all")


# ======================================================================
class TestSymmetricMassHasNoFactor:
    """The driving moment vanishes, so there is no factor of safety."""

    def test_the_driving_moment_really_does_vanish(self):
        """Without this the rest of the file could pass for the wrong reason.

        If the geometry stopped being symmetric — a change in the slicer, a
        different endpoint resolution — the methods would go on returning
        ordinary factors of safety and every assertion below would be
        measuring nothing at all.
        """
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        slices = slice_surface(
            _flat_block(),
            SlipCircle(centre_x=CENTRE_X, centre_y=CENTRE_Y, radius=RADIUS),
            NUM_SLICES)
        assert slices is not None and len(slices.slices) == NUM_SLICES

        terms = [s.weight * math.sin(s.base_angle) for s in slices.slices]
        residual = abs(sum(terms))
        largest = max(abs(t) for t in terms)

        assert largest > 0.5 * MEASURED_LARGEST_TERM, (
            "the mass has all but disappeared: largest slice term %.4g, "
            "measured %.4g when this test was written"
            % (largest, MEASURED_LARGEST_TERM))
        # The guard the methods apply is ``abs(driving) < 1e-9``, absolute.
        # Two orders of margin below it is what makes this deterministic.
        assert residual < 1e-11, (
            "the driving moment no longer cancels: %.4g against a largest "
            "term of %.4g. This fixture is not a symmetric mass any more, "
            "so it is not testing D56." % (residual, largest))

    def test_no_method_returns_a_number_that_is_not_one(self):
        """The headline. On 0.1.151 six of the nine failed this."""
        for mid, res in sorted(_symmetric_results().items()):
            assert res is not None, mid
            assert res.fos is None or math.isfinite(res.fos), (
                "%s answered %r on a mass with no driving moment. A "
                "calculation with no answer is reported with fos=None and a "
                "reason, never with a non-number." % (mid, res.fos))

    def test_every_method_declares_the_failure(self):
        for mid, res in sorted(_symmetric_results().items()):
            assert not res.converged, mid
            assert not res.is_valid, mid

    def test_every_failure_carries_its_reason(self):
        """The Corps trio failed this on 0.1.151 with an empty message."""
        for mid, res in sorted(_symmetric_results().items()):
            assert res.error_message or res.admissibility_note, (
                "%s failed to converge without saying why, and answered "
                "%r while doing it. A number with no explanation beside it "
                "is read as an answer." % (mid, res.fos))

    def test_the_search_reports_no_critical_surface(self):
        """The whole chain, not just the method.

        A search over surfaces that all failed has no answer to give, and
        has to say so rather than hand back the best of nothing.
        """
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.search import SearchResult

        results = _symmetric_results()
        for mid in sorted(method_registry()):
            search = SearchResult(method_id=mid,
                                  evaluations=[results[mid]],
                                  valid_count=0, invalid_count=1)
            assert search.critical is None, mid
            assert math.isinf(search.min_fos), mid


# ======================================================================
class TestAMethodCannotHandOutANonNumber:
    """The three things ``LEMResult.__post_init__`` refuses.

    No geometry: these are about the contract itself, so they hold for a
    method that has not been written yet.
    """

    @staticmethod
    def _kwargs(**over):
        base = dict(fos=1.0, converged=True, iterations=1,
                    method_id="test", surface=None, slices=None)
        base.update(over)
        return base

    def test_a_nan_cannot_be_stored(self):
        from ogr_slip2d.methods.base import LEMResult
        with pytest.raises(ValueError):
            LEMResult(**self._kwargs(fos=math.nan, converged=False,
                                     error_message="whatever"))

    def test_an_infinity_cannot_be_stored(self):
        """``inf`` is refused too, and that is the reference's own choice.

        A vanishing driving moment does have a defined limit — the mass does
        not slide — so ``inf`` is arithmetically defensible in a way ``nan``
        is not. The reference still does not report it: it gives the
        condition a code of its own, whose published description says it
        exists to keep extremely high factors from being calculated when the
        driving force is very small. A factor of safety of infinity is not
        an engineering answer, and it poisons a minimum just as quietly.
        """
        from ogr_slip2d.methods.base import LEMResult
        with pytest.raises(ValueError):
            LEMResult(**self._kwargs(fos=math.inf, converged=False,
                                     error_message="whatever"))

    def test_no_factor_and_converged_is_a_contradiction(self):
        from ogr_slip2d.methods.base import LEMResult
        with pytest.raises(ValueError):
            LEMResult(**self._kwargs(fos=None, converged=True))

    def test_a_failure_must_say_why(self):
        """The 5.0 of the Corps methods is what this one is for."""
        from ogr_slip2d.methods.base import LEMResult
        with pytest.raises(ValueError):
            LEMResult(**self._kwargs(fos=5.0, converged=False))

    def test_a_declared_failure_is_perfectly_constructible(self):
        """The guard must not have made the honest case impossible."""
        from ogr_slip2d.methods.base import LEMResult, REASON_ZERO_DRIVING
        res = LEMResult(**self._kwargs(
            fos=None, converged=False,
            error_message="Zero driving moment — surface does not slide",
            reason=REASON_ZERO_DRIVING))
        assert res.fos is None
        assert not res.is_valid
        assert res.reason == REASON_ZERO_DRIVING


# ======================================================================
class TestNoWriterSerialisesANonNumber:
    """No results file leaves this program carrying a non-number."""

    def test_the_dict_is_valid_json(self):
        """``allow_nan=False`` is the whole test.

        Python's encoder writes bare ``NaN`` and ``Infinity`` by default.
        Both are outside the JSON grammar, so the file round-trips in Python
        and fails in anything else — which is how a non-number reaches a
        report without ever looking wrong on the way.
        """
        text = json.dumps(_one_result().to_dict(), allow_nan=False)
        assert '"fos": null' in text or '"fos":' in text

    def test_every_failed_result_serialises(self):
        for mid, res in sorted(_symmetric_results().items()):
            try:
                json.dumps(res.to_dict(), allow_nan=False)
            except ValueError as exc:  # noqa: PERF203
                raise AssertionError(
                    "%s produced a result that is not valid JSON: %s"
                    % (mid, exc)) from exc

    def test_the_dict_carries_the_reason_beside_the_missing_factor(self):
        """A missing number with no reason beside it is the unreadable row."""
        for mid, res in sorted(_symmetric_results().items()):
            d = res.to_dict()
            assert "reason" in d and "admissible" in d, mid
            if d["fos"] is None:
                assert d["reason"] or d["error"], mid

    def test_the_hdf5_writer_omits_the_factor_it_does_not_have(self):
        """The reference writes a code where the safety factor would go.

        Returns without asserting when h5py is absent — it is the optional
        half of the hybrid project format, and the JSON test above is the
        one that has to run everywhere. The runner has no skip mechanism, so
        this says so by returning rather than by pretending to pass.
        """
        import tempfile
        from pathlib import Path

        try:
            import h5py
        except ImportError:  # pragma: no cover - h5py is optional
            return
        from ogr_core.project.results_io import save_results
        from ogr_slip2d.search import SearchResult

        results = _symmetric_results()
        mid = sorted(results)[0]
        search = SearchResult(method_id=mid, evaluations=[results[mid]],
                              valid_count=0, invalid_count=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d56.h5"
            save_results(path, search, project_id="d56")
            with h5py.File(path, "r") as f:
                sg = f["surfaces"]["surface_00000"]
                assert "fos" not in sg.attrs, (
                    "a surface with no factor of safety was still given a "
                    "`fos` attribute, so a reader gets a number back")
                assert sg.attrs["reason"] or sg.attrs["error"]


# ======================================================================
class TestEveryMethodSaysWhy:
    """The reason is a named constant, so a run can count by it."""

    def test_the_reason_comes_from_the_declared_set(self):
        from ogr_slip2d.methods.base import ALL_REASONS

        for mid, res in sorted(_symmetric_results().items()):
            if not res.reason:
                continue
            assert res.reason in ALL_REASONS, (
                "%s reported the reason %r, which is not one of the declared "
                "constants. A reason born as a loose string cannot be "
                "grouped, and grouping is the point." % (mid, res.reason))

    def test_a_surface_that_solves_has_no_reason(self):
        """Rule 7 in miniature: the field has to mean something.

        A ``reason`` set on every result, successful ones included, would
        carry no information at all.
        """
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project

        # An ordinary slope, so an ordinary answer comes back.
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(60, 0), Vertex(60, 20),
            Vertex(30, 20), Vertex(10, 0),
        ], closed=True)
        ext.ensure_ccw()
        p = Project("slope")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(
            name="Soil", unit_weight=19.0,
            strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))]

        method = method_registry()["bishop_simplified"]()
        res = GridSearch(method=method, num_slices=30,
                         min_area=0.0).evaluate_circle(
            p, SlipCircle(centre_x=25.0, centre_y=30.0, radius=25.0))
        assert res is not None and res.is_valid, (
            "the control slope stopped solving, so this test measures "
            "nothing")
        assert res.reason == ""
        assert res.fos is not None and math.isfinite(res.fos)
