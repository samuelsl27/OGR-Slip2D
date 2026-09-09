# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A serialised surface is read by its TYPE, never by the shape of its
dictionary — and a statistical run either answers for the deterministic
surface or says why it will not.

WHAT INVARIANT THIS PROTECTS. ``_rebuild_surface`` dispatched on the shape of
the dictionary — ``surface_dict.get("type") == "circle" or "radius" in
surface_dict`` — instead of on the ``type`` field that all four ``to_dict`` of
:mod:`ogr_slip2d.surface` write. Two of the four are misread that way:
``CompositeSurface.to_dict`` carries ``radius``, so a composite took the circle
branch; and ``WeakLayerSurface.to_dict`` carries neither ``radius`` nor
``polyline``, so it fell through to ``SlipSurface.from_dict`` and raised
``KeyError('polyline')`` from OUTSIDE the sample loop, losing every method and
both analyses at once and printing nothing anywhere. Defect D59, and the same
root cause in ``_surface_key``, which read ``v["x"]`` off vertices that
``Polyline.to_dict`` has always written as ``[x, y]`` and so raised
``TypeError`` on the first valid evaluation of any non-circular search, taking
``run_overall_slope`` down by its public door.

WHAT IS AND IS NOT A DEFECT HERE, measured before anything was written:

* seeding the re-evaluation from the CIRCLE of a composite is RIGHT, and the
  fix keeps it: the engine resolves the mass again and clips it again, and over
  the composite models of the verification bank the re-evaluated surface is the
  deterministic one to all seventeen digits. Rebuilding the ``CompositeSurface``
  object from its dictionary is WORSE: the dictionary does not carry
  ``tension_crack_wall`` and the endpoints arrive already truncated, so a filled
  tension crack loses its water thrust — +0.35 % on the UNSAFE side on the
  composite model of problem 57 (measured there, not here);
* what IS lost is the CONDITION. A composite seeded from its circle is only
  composite again while Composite Surfaces stays on in the project the samples
  run on. With it off, the same circle is either refused whole — ten samples of
  ten lost, under a warning that blames the variable ranges, which are innocent
  — or, when the circle defines more than one sliding mass, the OTHER mass
  answers: +142.97 % on one evaluation, no failed sample and no note at all.

WHAT THIS FILE DOES NOT CLAIM. The refusal covers a lost OPTION, not a changed
mechanism. With the option on in both runs a sample can still answer for
another mass of the same circle purely because its own strength fell — that is
``_best_of_masses`` keeping the lowest factor, and v0.1.131 (D36) dropping the
endpoints on purpose. It is reported as a defect of its own; asserting it here
would be asserting something the code does not do.

WHY THIS GEOMETRY. Verification problem 22 — Fredlund and Krahn (1977), the
paper that introduced the general limit-equilibrium formulation so composite
surfaces could be solved — publishes its surface instead of searching for it
(xc = 120, yc = 90, R = 80), and that arc reaches y = 10 against a floor at
y = 15. It is built here rather than imported from another test module, because
the two files that already use it build it independently too, and because a
class below has to flip Composite Surfaces on a project of its own.

THIS IS NOT A SNAPSHOT TEST. Every assertion is either a statement about an
object (a type, a key, the text of a refusal), an identity (the deterministic
surface and the sampled one give the same digits), or a value anchored to
Fredlund and Krahn (1977) table 22.3 — 1.377 Bishop, 1.373 Spencer. No number
this program printed is pinned anywhere.

ONE HONEST LIMIT OF THE IDENTITY. The deterministic side below is computed with
the same bare ``GridSearch(min_area=0.0)`` the sampler builds, and NOT with
``analysis_runner.build_search``, which the program uses and which also passes
surface filters, slope limits and focus objects. So the identity isolates the
round trip of the surface, not the configuration of the search. The anchor that
bites is the published one.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy

import pytest


# ----------------------------------------------------------------------
# Problem 22, figure 22.1, vertex by vertex (feet). The floor of the model
# is y = 15 and the top of the weak layer is y = 16.
_Y_WEAK_TOP = 16.0
_EXTERNAL = [(0, 15), (180, 15), (180, 16), (180, 20), (140, 20),
             (60, 60), (0, 60), (0, 16)]

#: The same geometry with a NOTCH cut into the crest. SYNTHETIC — no
#: published number belongs to it. Its only job is to make the published
#: circle cut the ground four times, so it defines two disjoint sliding
#: masses and the choice between them becomes visible.
_NOTCHED = [(0, 15), (180, 15), (180, 16), (180, 20), (140, 20),
            (60, 60), (56.5, 60), (56, 40), (50, 40), (49.5, 60),
            (0, 60), (0, 16)]

#: The surface the paper gives, rather than one this program searched for.
_XC, _YC, _R = 120.0, 90.0, 80.0

#: Table 22.3 — Fredlund and Krahn (1977), composite circular, dry case.
_FK_DRY = {"bishop_simplified": 1.377, "spencer": 1.373}

#: The same 2 % the composite file uses, and for the same reason the manual
#: gives: "the location of the weak layer is slightly different in all the
#: above references" and results "routinely vary in the second decimal place".
_TOL = 0.02

_SLICES = 30

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _build(vertices, composite: bool):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection

    p = Project("composite / weak layer — Fredlund & Krahn (1977)")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in vertices], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, _Y_WEAK_TOP), Vertex(180, _Y_WEAK_TOP)], closed=False),
        btype=BoundaryType.MATERIAL))

    upper = Material(name="Upper soil", unit_weight=120.0,
                     sat_unit_weight=120.0,
                     strength=MohrCoulomb(cohesion=600.0, friction_angle=20.0),
                     pore_pressure=PorePressureType.NONE)
    weak = Material(name="Weak layer", unit_weight=120.0,
                    sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=10.0),
                    pore_pressure=PorePressureType.NONE)
    p.materials = [upper, weak]
    p.resolve_regions()
    p.assign_material_at(90.0, 30.0, upper.id)
    p.assign_material_at(90.0, 15.5, weak.id)

    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.methods.num_slices = _SLICES
    p.settings.methods.interslice_function = "half_sine"
    p.settings.search.composite_surfaces = composite
    # The crest is on the LEFT (y = 60) and the toe on the right (y = 20).
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    return p


def _project():
    """The published problem-22 model, Composite Surfaces ON.

    Cached because building one costs more than evaluating on it. NEVER
    handed out to be mutated: the one class that needs the option flipped
    takes a deep copy first (rule 5 — a test may not leak state, and a
    shared fixture is state).
    """
    if "on" not in _CACHE:
        _CACHE["on"] = _build(_EXTERNAL, True)
    return _CACHE["on"]


def _notched():
    """The synthetic two-mass model, Composite Surfaces ON."""
    if "notched" not in _CACHE:
        _CACHE["notched"] = _build(_NOTCHED, True)
    return _CACHE["notched"]


def _without_the_option(project):
    """A copy of ``project`` whose ONLY difference is the option."""
    clone = copy.deepcopy(project)
    clone.settings.search.composite_surfaces = False
    return clone


def _search(method_id: str = "bishop_simplified"):
    """The bare GridSearch the sampler itself builds (probabilistic.py)."""
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.search import GridSearch

    return GridSearch(method=method_registry()[method_id](),
                      num_slices=_SLICES, min_area=0.0)


def _circle():
    from ogr_slip2d.surface import SlipCircle

    return SlipCircle(centre_x=_XC, centre_y=_YC, radius=_R)


def _deterministic(project, method_id="bishop_simplified"):
    """The published circle evaluated on ``project``."""
    return _search(method_id).evaluate_circle(project, _circle())


def _cohesion_var(project):
    """The cohesion of the upper soil, as a random variable."""
    from ogr_core.statistics import Distribution, DistributionType as DT
    from ogr_core.statistics import available_variables

    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"],
        std_dev=60.0, rel_min=180.0, rel_max=180.0)
    return v


def _the_four_dicts():
    """One serialised dictionary of each of this program's surface types."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import (
        CompositeSurface, SlipCircle, SlipSurface, WeakLayerSurface,
    )

    circle = SlipCircle(centre_x=_XC, centre_y=_YC, radius=_R)
    circle.x_left, circle.x_right = 45.0, 158.0
    bedrock = Polyline(vertices=[Vertex(0.0, 15.0), Vertex(180.0, 15.0)])
    return {
        "circle": SlipCircle(centre_x=_XC, centre_y=_YC, radius=_R).to_dict(),
        "polyline": SlipSurface(polyline=Polyline(vertices=[
            Vertex(0.0, 0.0), Vertex(1.0, 1.0)])).to_dict(),
        "composite": CompositeSurface(
            circle=circle, bedrock=bedrock,
            x_left=circle.x_left, x_right=circle.x_right).to_dict(),
        "weak_layer": WeakLayerSurface(base=circle, bands=()).to_dict(),
    }


# ======================================================================
class TestThePremiseTheDictionaryDoesNotLookLikeItsType:
    """Closed-form facts about the four ``to_dict``, so the rest measures
    the dispatch and not itself."""

    def test_a_composite_says_composite_and_still_carries_a_radius(self):
        d = _the_four_dicts()["composite"]
        assert d["type"] == "composite"
        assert "radius" in d, (
            "the whole defect: the old condition read this key and never "
            "reached the type")

    def test_a_weak_layer_carries_neither_radius_nor_polyline(self):
        d = _the_four_dicts()["weak_layer"]
        assert d["type"] == "weak_layer"
        assert "radius" not in d
        assert "polyline" not in d, (
            "which is why SlipSurface.from_dict raised KeyError('polyline')")

    def test_vertices_are_pairs_and_never_mappings(self):
        """``_surface_key`` read ``v["x"]``; the writer has always written
        ``[x, y]``."""
        d = _the_four_dicts()
        for v in d["polyline"]["polyline"]["vertices"]:
            assert isinstance(v, (list, tuple)) and len(v) == 2, v
        for key in ("composite", "weak_layer"):
            for v in d[key]["vertices"]:
                assert isinstance(v, (list, tuple)) and len(v) == 2, (key, v)


# ======================================================================
class TestEveryTypeThisProgramSerialisesIsAccountedFor:
    """Each of the four either SEEDS or is REFUSED with a reason, and none
    of them raises."""

    def test_the_program_serialises_exactly_these_four(self):
        """A fence, not a bug: a fifth serialised type has to come here and
        decide whether a statistical run can seed it.

        Read off the module rather than off the list above, so that adding
        a surface class without deciding what a statistical run does with
        it fails HERE instead of somewhere downstream.
        """
        import inspect
        import re

        from ogr_slip2d import surface as S

        declared = set()
        for _, cls in inspect.getmembers(S, inspect.isclass):
            if cls.__module__ != S.__name__:
                continue
            # A Protocol only DECLARES ``to_dict``; it serialises nothing.
            if getattr(cls, "_is_protocol", False):
                continue
            fn = cls.__dict__.get("to_dict")
            if fn is None:
                continue
            found = re.search(r'"type":\s*"([a-z_]+)"',
                              inspect.getsource(fn))
            assert found, cls.__name__ + " serialises without a type"
            declared.add(found.group(1))

        assert declared == {"circle", "polyline", "composite", "weak_layer"}
        assert declared == set(_the_four_dicts())

    def test_none_of_them_raises(self):
        """The KeyError of D59, and the TypeError of its sibling, in one
        assertion."""
        from ogr_core.statistics.probabilistic import (
            _rebuild_surface, _surface_key,
        )

        for name, d in _the_four_dicts().items():
            _rebuild_surface(d)          # must not raise
            key = _surface_key(d)        # must not raise
            assert key, name

    def test_each_one_either_seeds_or_is_refused_by_name(self):
        from ogr_core.statistics.probabilistic import (
            _cannot_reevaluate, _rebuild_surface,
        )
        from ogr_slip2d.surface import SlipCircle, SlipSurface

        p = _project()
        seeds = {"circle": SlipCircle, "composite": SlipCircle,
                 "polyline": SlipSurface}
        for name, d in _the_four_dicts().items():
            seed = _rebuild_surface(d)
            refusal = _cannot_reevaluate(p, d)
            if name in seeds:
                assert isinstance(seed, seeds[name]), (name, seed)
                assert refusal is None, (name, refusal)
            else:
                assert seed is None, (name, seed)
                assert refusal and name in refusal, (name, refusal)

    def test_a_bare_dictionary_without_a_type_is_still_a_circle(self):
        """``run_global_minimum`` accepts a bare dict as ``det.surface``.
        Dropping that would be a side effect, not a decision."""
        from ogr_core.statistics.probabilistic import (
            _cannot_reevaluate, _rebuild_surface,
        )
        from ogr_slip2d.surface import SlipCircle

        bare = {"centre_x": _XC, "centre_y": _YC, "radius": _R}
        assert isinstance(_rebuild_surface(bare), SlipCircle)
        assert _cannot_reevaluate(_project(), bare) is None

    def test_an_empty_surface_is_refused_and_not_seeded(self):
        from ogr_core.statistics.probabilistic import (
            _cannot_reevaluate, _rebuild_surface,
        )

        for empty in (None, {}):
            assert _rebuild_surface(empty) is None
            assert _cannot_reevaluate(_project(), empty)


# ======================================================================
class TestTheSurfaceTheSampleAnalysesIsTheCompositeAgain:
    """The half of the closure criterion that says the fix costs nothing."""

    def test_the_deterministic_surface_is_a_clipped_one(self):
        """The premise. Without it the rest is about an ordinary circle."""
        from ogr_slip2d.surface import CompositeSurface

        det = _deterministic(_project())
        assert det is not None and det.is_valid
        assert isinstance(det.surface, CompositeSurface), type(det.surface)

    def test_the_seed_is_a_circle_without_endpoints(self):
        """v0.1.131 (D36) dropped them on purpose, and this fix keeps that:
        every sample resolves its own mass."""
        from ogr_core.statistics.probabilistic import _rebuild_surface
        from ogr_slip2d.surface import SlipCircle

        seed = _rebuild_surface(_deterministic(_project()).surface.to_dict())
        assert isinstance(seed, SlipCircle)
        assert seed.x_left is None and seed.x_right is None

    def test_the_sample_analyses_a_composite_and_the_same_digits(self):
        from ogr_core.statistics.probabilistic import (
            _evaluate_on, _rebuild_surface,
        )
        from ogr_core.statistics.random_variables import clone_project
        from ogr_slip2d.surface import CompositeSurface

        p = _project()
        for method_id in sorted(_FK_DRY):
            ev = _search(method_id)
            det = ev.evaluate_circle(p, _circle())
            seed = _rebuild_surface(det.surface.to_dict())
            r = _evaluate_on(clone_project(p), ev, seed)
            assert r is not None and r.is_valid, method_id
            assert isinstance(r.surface, CompositeSurface), (
                method_id, type(r.surface))
            assert r.fos == pytest.approx(det.fos, rel=1e-12), (
                method_id, det.fos, r.fos)
            assert r.fos == pytest.approx(_FK_DRY[method_id], rel=_TOL), (
                method_id, r.fos)


# ======================================================================
class TestWhenTheOptionIsGoneTheRunSaysSoInsteadOfAnswering:
    """The half that closes the defect. The reason has to be READABLE: a
    run that refuses without saying why leaves the user exactly as blind
    as one that answers wrongly."""

    def _refused(self, run):
        return [str(v) for v in run.notes.values()]

    def test_the_probabilistic_run_refuses_and_names_the_option(self):
        from ogr_core.statistics import SamplingMethod as SM
        from ogr_core.statistics import run_global_minimum

        p = _project()
        det = {"bishop_simplified": _deterministic(p)}
        off = _without_the_option(p)
        res = run_global_minimum(
            off, det, [_cohesion_var(off)], num_samples=4,
            sampling=SM.MONTE_CARLO, seed=7, num_slices=_SLICES)

        assert not res.by_method, "a number came back for a surface this "\
                                  "project cannot form"
        said = " ".join(self._refused(res))
        assert "Composite Surfaces" in said, said
        assert "variable ranges" not in said, (
            "the reason must not blame the ranges, which are innocent")

    def test_the_sensitivity_run_refuses_it_too(self):
        from ogr_core.statistics import run_sensitivity

        p = _project()
        det = {"bishop_simplified": _deterministic(p)}
        off = _without_the_option(p)
        res = run_sensitivity(off, det, [_cohesion_var(off)], intervals=2,
                              num_slices=_SLICES)

        assert not res.by_method
        said = " ".join(self._refused(res))
        assert "Composite Surfaces" in said, said

    def test_a_weak_layer_critical_no_longer_takes_the_run_down(self):
        """D59's loudest half: this used to raise KeyError('polyline') from
        outside the sample loop and lose every method and both analyses."""
        from ogr_core.statistics import SamplingMethod as SM
        from ogr_core.statistics import run_global_minimum, run_sensitivity
        from ogr_slip2d.surface import WeakLayerSurface

        p = _project()
        det = _deterministic(p)
        stand_in = copy.copy(det)
        stand_in.surface = WeakLayerSurface(base=_circle(), bands=())

        res = run_global_minimum(
            p, {"bishop_simplified": stand_in}, [_cohesion_var(p)],
            num_samples=2, sampling=SM.MONTE_CARLO, seed=7,
            num_slices=_SLICES)
        assert "weak_layer" in " ".join(self._refused(res))

        sen = run_sensitivity(p, {"bishop_simplified": stand_in},
                              [_cohesion_var(p)], intervals=2,
                              num_slices=_SLICES)
        assert "weak_layer" in " ".join(self._refused(sen))

    def test_the_reason_reaches_the_key_the_interface_prints(self):
        """``_compute_statistics`` looks at ``notes['error']`` and nowhere
        else. A note nobody shows is a note that does not exist."""
        from ogr_core.statistics import SamplingMethod as SM
        from ogr_core.statistics import run_global_minimum

        p = _project()
        off = _without_the_option(p)
        res = run_global_minimum(
            off, {"bishop_simplified": _deterministic(p)},
            [_cohesion_var(off)], num_samples=2, sampling=SM.MONTE_CARLO,
            seed=7, num_slices=_SLICES)
        assert "Composite Surfaces" in res.notes.get("error", "")


# ======================================================================
class TestTheOtherSlidingMassNeverBecomesTheAnswer:
    """What the refusal is FOR. On a circle with two disjoint masses the
    engine drops only the one that escapes and answers for the other,
    silently — measured +142.97 % against the deterministic it reports."""

    def test_the_premise_the_notched_model_gives_two_masses(self):
        from ogr_core.geometry import ground_surface

        p = _notched()
        chords = _circle().candidate_chords(
            ground_surface(p.external_boundary()))
        assert len(chords) == 2, chords

    def test_the_deterministic_mass_is_the_clipped_one(self):
        from ogr_slip2d.surface import CompositeSurface

        det = _deterministic(_notched())
        assert isinstance(det.surface, CompositeSurface), type(det.surface)

    def test_without_the_option_the_other_mass_is_refused_not_reported(self):
        """The identity that names the defect: the extent answered must be
        the extent the deterministic run found, or there must be no
        answer at all."""
        from ogr_core.statistics.probabilistic import (
            _cannot_reevaluate, _evaluate_on, _rebuild_surface,
        )
        from ogr_core.statistics.random_variables import clone_project

        p = _notched()
        det = _deterministic(p)
        sd = det.surface.to_dict()
        off = _without_the_option(p)

        assert _cannot_reevaluate(off, sd) is not None, (
            "the guard has to fire here; without it the answer below is "
            "another mass")

        # And what it is protecting against, shown rather than asserted
        # away: the seed still resolves onto the OTHER mass on that
        # project, which is why handing its number over would be wrong.
        seed = _rebuild_surface(sd)
        other = _evaluate_on(clone_project(off), _search(), seed)
        if other is not None and other.is_valid:
            assert (other.surface.x_left, other.surface.x_right) != (
                det.surface.x_left, det.surface.x_right), (
                "premise gone: the two masses no longer differ")


# ======================================================================
class TestOverallSlopeCanIndexASurfaceItAnalysed:
    """The sibling defect. ``_surface_key`` sits outside the ``try`` of
    ``run_overall_slope``, so raising there kills the public entry
    point."""

    def test_a_polyline_gets_a_key_instead_of_a_TypeError(self):
        from ogr_core.statistics.probabilistic import _surface_key

        key = _surface_key(_the_four_dicts()["polyline"])
        assert key.startswith("p:") and key != "p:", key

    def test_two_different_polylines_are_two_different_keys(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.statistics.probabilistic import _surface_key
        from ogr_slip2d.surface import SlipSurface

        a = SlipSurface(polyline=Polyline(vertices=[
            Vertex(0.0, 0.0), Vertex(10.0, 10.0)])).to_dict()
        b = SlipSurface(polyline=Polyline(vertices=[
            Vertex(0.0, 0.0), Vertex(10.0, 40.0)])).to_dict()
        assert _surface_key(a) != _surface_key(b)

    def test_weak_layer_surfaces_no_longer_collapse_onto_one_key(self):
        from ogr_core.statistics.probabilistic import _surface_key
        from ogr_slip2d.surface import SlipCircle, WeakLayerSurface

        def one(radius):
            c = SlipCircle(centre_x=_XC, centre_y=_YC, radius=radius)
            c.x_left, c.x_right = 45.0, 158.0
            return _surface_key(WeakLayerSurface(base=c, bands=()).to_dict())

        assert one(80.0) not in ("", "p:")
        assert one(80.0) != one(85.0)

    def test_a_circle_keeps_the_key_it_always_had(self):
        """The one thing that must NOT move: every circular model in the
        bank groups its samples by this string."""
        from ogr_core.statistics.probabilistic import _surface_key

        d = _the_four_dicts()
        assert _surface_key(d["circle"]) == "c:%d:%d:%d" % (
            round(_XC / 0.5), round(_YC / 0.5), round(_R / 0.5))
        assert _surface_key(d["composite"]) == _surface_key(d["circle"]), (
            "a composite has always been keyed by its circle, and this "
            "version does not change that")
