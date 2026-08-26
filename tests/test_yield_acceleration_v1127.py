# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.127 — the critical seismic coefficient, and what a search minimises.

Two things are protected here and they are different in kind.

The number: Ky against a closed form and a published value
----------------------------------------------------------

``Ky`` is the horizontal pseudo-static coefficient that brings a surface to
a target factor of safety. Two anchors, neither of them a snapshot of what
this program prints:

* **Newmark (1965)**: a block on a plane inclined at β, cohesionless, dry,
  yields at ``k_y = tan(φ − β)``. Exact. Measured here at 2.7e-8 relative
  for the three methods whose assumptions coincide with a single wedge on
  a plane — the two Corps of Engineers and Lowe-Karafiath — and 3.9e-8 for
  Janbu simplified.

  Ordinary and Bishop do **not** reproduce it, by +6.2 % and +7.1 %, and
  that is measured rather than tolerated: on a NON-circular surface a
  moment-only method depends on where moments are taken, which is the
  anomaly ``tests/test_moment_axis_v1126.py`` measures on the factor of
  safety itself. Here it shows up in Ky, on the same surface, with the
  same sign. It is recorded, not asserted away.

* **Loukidis, Bandini and Salgado (2003), example 1**, which publishes the
  critical seismic coefficient itself: 0.432 for the dry slope and 0.132
  with ``ru = 0.5``. Until now this program could only check that
  publishing value *backwards* — plug it in, see whether the factor comes
  out at 1. Now it computes it forwards, which is the direction it is
  used in. Spencer gives 0.4330 (+0.23 %) and 0.13297 (+0.73 %).

The search: what "critical" means when the question changes
-----------------------------------------------------------

Asked for the critical seismic coefficient, the reference reports "the
surface which requires the LOWEST value of Ky", and warns that it is
"quite different from the critical surface". So the objective a search
minimises stops being the factor of safety, and that had to become a
single function instead of the ``a.fos < b.fos`` comparisons spread across
the seven searches, ``SearchResult`` and the optimisation walk.

The guarantee that the change is safe is stated as a test rather than as
a claim: with the seismic modes off, a search given the settings object
must produce output **bit for bit identical** to one that never heard of
it.

And the reference's warning reproduces: on the three-layer ACADS slope the
lowest-Ky circle is centred 3.1 m above the lowest-factor one and has a
2.6 m larger radius.
"""
from __future__ import annotations

import copy
import math

import pytest

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.hydraulic.pore_pressure import PorePressureType
from ogr_core.materials import Material
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project import Project, SeismicAnalysisSettings
from ogr_slip2d.analysis_runner import build_search
from ogr_slip2d.methods import get_method
from ogr_slip2d.newmark import rigid_block_displacement
from ogr_slip2d.search import (
    OBJECTIVE_FOS,
    OBJECTIVE_KY,
    BaseSearch,
    surface_score,
)
from ogr_slip2d.slicer import slice_surface
from ogr_slip2d.surface import SlipCircle, SlipSurface
from ogr_slip2d.yield_acceleration import (
    critical_coefficient_from,
    critical_seismic_coefficient,
)

_CACHE: dict = {}


class _Probe(BaseSearch):
    """A search that never searches: only a door into the engine."""

    def _run(self, project):          # pragma: no cover - never called
        raise NotImplementedError


# ----------------------------------------------------------------------
# The plane, for the closed form of Newmark (1965)
# ----------------------------------------------------------------------
_PHI = 30.0
_PLANE = ((2.0, 2.0), (30.0, 10.0))
_BETA = math.degrees(math.atan2(_PLANE[1][1] - _PLANE[0][1],
                                _PLANE[1][0] - _PLANE[0][0]))
_KY_EXACT = math.tan(math.radians(_PHI - _BETA))


def _plane_project():
    """A 45° face over flat ground, one cohesionless soil, dry."""
    p = Project("plane")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(0, 0), Vertex(40, 0), Vertex(40, 10),
                           Vertex(10, 10)], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Sand", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=_PHI)))
    p.seismic.enabled = True
    p.seismic.kh = 0.0
    p.seismic.kv = 0.0
    return p


def _plane_surface():
    return SlipSurface(polyline=Polyline(
        [Vertex(*_PLANE[0]), Vertex(*_PLANE[1])]))


def _plane_ky(method_id: str, num_slices: int = 60):
    key = ("plane", method_id, num_slices)
    if key not in _CACHE:
        project = _plane_project()
        surface = _plane_surface()
        with project.regions_frozen():
            slices = slice_surface(project, surface, num_slices=num_slices)
            _CACHE[key] = critical_seismic_coefficient(
                get_method(method_id)(), project, surface, slices)
    return _CACHE[key]


# ----------------------------------------------------------------------
# Loukidis, Bandini and Salgado (2003), example 1
# ----------------------------------------------------------------------
_LOUKIDIS = {
    "dry": dict(published=0.432, ru=0.0,
                arc=dict(centre_x=16.5, centre_y=109.0, radius=110.28186)),
    "ru05": dict(published=0.132, ru=0.5,
                 arc=dict(centre_x=22.0, centre_y=82.75, radius=85.81)),
}


def _loukidis_project(ru: float):
    p = Project("loukidis")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in (
        (-50, -25), (150, -25), (150, 25), (75, 25), (0, 0), (-50, 0))],
        closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    material = Material(name="Clay", unit_weight=20.0, sat_unit_weight=20.0,
                        strength=MohrCoulomb(cohesion=25.0,
                                             friction_angle=30.0))
    if ru:
        material.pore_pressure = PorePressureType.RU_COEFFICIENT
        material.ru = ru
    p.materials = [material]
    p.assign_material_at(0.0, -10.0, material.id)
    p.seismic.enabled = True
    p.seismic.kh = 0.0
    p.seismic.kv = 0.0
    p.settings = copy.deepcopy(p.settings)
    return p


def _loukidis_ky(case: str, method_id: str):
    key = ("loukidis", case, method_id)
    if key not in _CACHE:
        spec = _LOUKIDIS[case]
        project = _loukidis_project(spec["ru"])
        circle = SlipCircle(**spec["arc"])
        with project.regions_frozen():
            slices = slice_surface(project, circle, num_slices=50)
            _CACHE[key] = critical_seismic_coefficient(
                get_method(method_id)(), project, circle, slices)
    return _CACHE[key]


# ----------------------------------------------------------------------
# The three-layer ACADS slope, for the search objective
# ----------------------------------------------------------------------
def _acads_project():
    """ACADS 1(c): the slope verification problems 3, 4 and 104 all use.

    Deliberately a small grid: what is being measured here is which
    surface a run REPORTS, not what its factor of safety is, and the two
    rankings already disagree on a few hundred circles.
    """
    p = Project("ACADS 1(c)")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in (
        (20, 20), (70, 20), (70, 24), (70, 31), (70, 35),
        (50, 35), (30, 25), (20, 25))], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    top = Material(name="Soil #1", unit_weight=19.5,
                   strength=MohrCoulomb(cohesion=0.0, friction_angle=38.0))
    mid = Material(name="Soil #2", unit_weight=19.5,
                   strength=MohrCoulomb(cohesion=5.3, friction_angle=23.0))
    low = Material(name="Soil #3", unit_weight=19.5,
                   strength=MohrCoulomb(cohesion=7.2, friction_angle=20.0))
    p.materials = [top, mid, low]
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(30, 25), Vertex(40, 27), Vertex(50, 29), Vertex(54, 31),
        Vertex(70, 31)], closed=False), btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(40, 27), Vertex(52, 24), Vertex(70, 24)], closed=False),
        btype=BoundaryType.MATERIAL))
    regions = p.resolve_regions()
    upper = max(regions, key=lambda r: r.centroid()[1])
    lower = min(regions, key=lambda r: r.centroid()[1])
    middle = [r for r in regions if r not in (upper, lower)][0]
    p.assign_material_at(*upper.centroid(), top.id)
    p.assign_material_at(*middle.centroid(), mid.id)
    p.assign_material_at(*lower.centroid(), low.id)
    p.seismic.enabled = True
    p.seismic.kh = 0.0
    p.seismic.kv = 0.0
    s = p.settings.methods
    s.enabled_methods = ["bishop_simplified"]
    s.num_slices = 20
    g = p.settings.search
    g.search_method = "grid"
    g.surface_type = "circular"
    g.composite_surfaces = False
    g.grid_x_min, g.grid_x_max = 30.0, 42.0
    g.grid_y_min, g.grid_y_max = 38.0, 50.0
    g.grid_nx = g.grid_ny = 4
    g.radius_increment = 3
    return p


def _acads_run(compute_ky: bool):
    key = ("acads", compute_ky)
    if key not in _CACHE:
        project = _acads_project()
        project.settings.seismic.compute_ky = compute_ky
        search = build_search(project, "bishop_simplified")
        with project.regions_frozen():
            _CACHE[key] = search.run(project)
    return _CACHE[key]


# ======================================================================
class TestTheClosedFormOfNewmark:
    """``k_y = tan(φ − β)`` on a plane. Newmark (1965)."""

    def test_the_wedge_methods_reproduce_it(self):
        """The three methods whose assumptions ARE the single wedge.

        Lowe-Karafiath and the two Corps of Engineers prescribe the
        inter-slice inclination, and on a uniform plane every slice is the
        same slice, so the whole equilibrium collapses onto the wedge the
        closed form describes. That is why they are the ones asked, and
        not a tolerance chosen to make a list pass.
        """
        bad = []
        for method_id in ("corps_engineers_1", "corps_engineers_2",
                          "lowe_karafiath", "janbu_simplified"):
            out = _plane_ky(method_id)
            assert out.found, method_id
            err = abs(out.ky - _KY_EXACT) / _KY_EXACT
            if err > 1e-6:
                bad.append(f"{method_id}: {out.ky:.8f} vs "
                           f"{_KY_EXACT:.8f} = {err:.2e}")
        assert not bad, bad

    def test_the_moment_only_methods_drift_and_that_is_the_axis(self):
        """A measurement, not a tolerance.

        Ordinary and Bishop take moments, and this surface has no centre
        of rotation, so their answer depends on the constructed axis —
        the anomaly measured in ``test_moment_axis_v1126.py``. What is
        asserted is that the drift is in the band measured in v0.1.127
        and that it is POSITIVE, both of which would change if the axis
        convention changed.
        """
        drifts = {}
        for method_id in ("ordinary_fellenius", "bishop_simplified"):
            out = _plane_ky(method_id)
            assert out.found, method_id
            drifts[method_id] = (out.ky - _KY_EXACT) / _KY_EXACT
        assert 0.04 < drifts["ordinary_fellenius"] < 0.09, drifts
        assert 0.05 < drifts["bishop_simplified"] < 0.10, drifts
        # Bishop drifts further than Ordinary, and the two are close: the
        # difference between them is the base normal, the same term that
        # separates them on the factor of safety.
        assert drifts["bishop_simplified"] > drifts["ordinary_fellenius"]


# ======================================================================
class TestThePublishedCriticalCoefficient:
    """Loukidis, Bandini and Salgado (2003), computed FORWARDS."""

    TOL_PCT = 1.0

    def test_the_dry_slope(self):
        bad = []
        for method_id in ("spencer", "gle_morgenstern_price"):
            out = _loukidis_ky("dry", method_id)
            assert out.found, method_id
            err = 100.0 * (out.ky - 0.432) / 0.432
            if abs(err) >= self.TOL_PCT:
                bad.append(f"{method_id}: {out.ky:.5f} vs 0.432 "
                           f"= {err:+.2f} %")
        assert not bad, bad

    def test_the_slope_with_ru(self):
        bad = []
        for method_id in ("spencer", "gle_morgenstern_price"):
            out = _loukidis_ky("ru05", method_id)
            assert out.found, method_id
            err = 100.0 * (out.ky - 0.132) / 0.132
            if abs(err) >= self.TOL_PCT:
                bad.append(f"{method_id}: {out.ky:.5f} vs 0.132 "
                           f"= {err:+.2f} %")
        assert not bad, bad

    def test_water_lowers_it_by_the_published_factor(self):
        """The ratio cancels whatever bias the two share.

        Published: 0.132 / 0.432 = 0.3056. It is a stronger statement than
        either absolute value, because a systematic error in the method
        would move both and leave this alone.
        """
        dry = _loukidis_ky("dry", "spencer").ky
        wet = _loukidis_ky("ru05", "spencer").ky
        assert wet / dry == pytest.approx(0.132 / 0.432, rel=0.01)


# ======================================================================
class TestTheReferenceOwnVerification:
    """Apply Ky and the factor must land on the target.

    This is the check the reference publishes about itself, next to a
    screenshot reading 1.000. Reproduced on this program's own models.
    """

    def test_the_factor_at_ky_is_the_target(self):
        bad = []
        for method_id in ("corps_engineers_1", "lowe_karafiath",
                          "janbu_simplified", "bishop_simplified",
                          "ordinary_fellenius"):
            out = _plane_ky(method_id)
            if abs(out.fos_at_ky - 1.0) > 1e-5:
                bad.append(f"{method_id}: {out.fos_at_ky:.8f}")
        assert not bad, bad

    def test_spencer_lands_close_but_not_exactly_and_that_is_lambda(self):
        """Measured, and reported rather than hidden.

        On the Loukidis circle, Spencer's factor of safety is not a
        continuous function of the seismic coefficient: between k = 0.4325
        and k = 0.4330 it steps from 1.001017 to 0.996266 while the
        converged λ jumps from 0.580 to 0.552 — the λ search changing
        which root it lands on. The bracket is still found and Ky is still
        right to a quarter of a percent, but the factor AT Ky misses the
        target by that step, and pretending otherwise would mean widening
        a tolerance until a discontinuity fitted inside it.
        """
        out = _loukidis_ky("dry", "spencer")
        assert out.found
        miss = abs(out.fos_at_ky - 1.0)
        assert miss > 1e-4, ("Spencer now lands on the target here; the "
                             "λ discontinuity this documents may be gone "
                             "— re-measure before relaxing the note")
        assert miss < 1e-2, out.fos_at_ky


# ======================================================================
class TestWhatItDoesWhenThereIsNoAnswer:
    """Three outcomes, and they are different answers."""

    def test_a_surface_already_at_the_target_yields_zero(self):
        out = critical_coefficient_from(lambda k: 0.8, target_fos=1.0)
        assert out.found and out.ky == 0.0
        assert out.evaluations == 1

    def test_no_crossing_gives_no_number_and_says_so(self):
        out = critical_coefficient_from(lambda k: 5.0 - 0.1 * k,
                                        target_fos=1.0)
        assert not out.found
        assert math.isnan(out.ky)
        assert "no coefficient below" in out.note

    def test_a_linear_factor_is_solved_exactly_and_cheaply(self):
        """FS = 2 − 4k crosses 1 at k = 0.25."""
        out = critical_coefficient_from(lambda k: 2.0 - 4.0 * k,
                                        target_fos=1.0)
        assert out.ky == pytest.approx(0.25, abs=1e-9)
        assert out.evaluations <= 8, out.evaluations

    def test_an_unsolvable_surface_is_not_a_coefficient_of_zero(self):
        out = critical_coefficient_from(lambda k: math.nan)
        assert not out.found

    def test_the_target_factor_moves_the_answer(self):
        """Rule 7 for the one number the Seismic page offers."""
        at_one = critical_coefficient_from(lambda k: 2.0 - 4.0 * k,
                                           target_fos=1.0).ky
        at_1_3 = critical_coefficient_from(lambda k: 2.0 - 4.0 * k,
                                           target_fos=1.3).ky
        assert at_1_3 == pytest.approx(0.175, abs=1e-9)
        assert at_1_3 < at_one


# ======================================================================
class TestTheSearchObjective:
    """What "critical" means, and that turning it off changes nothing."""

    def test_the_default_objective_is_the_factor_of_safety(self):
        assert SeismicAnalysisSettings().objective() == OBJECTIVE_FOS
        assert SeismicAnalysisSettings(compute_ky=True).objective() \
            == OBJECTIVE_KY
        # Newmark implies the Ky solve, because it needs the critical
        # acceleration and because it minimises the same thing.
        assert SeismicAnalysisSettings(newmark=True).objective() \
            == OBJECTIVE_KY
        assert SeismicAnalysisSettings(newmark=True).needs_ky

    def test_a_search_with_the_modes_off_is_bit_for_bit_the_old_one(self):
        """The guarantee that the objective could be introduced at all.

        Left: a search that never heard of the settings object, which is
        every search this program shipped before v0.1.127. Right: the same
        search handed one with both modes off. Not "agree to a tolerance":
        identical, because nothing in the path may depend on the argument
        being present.
        """
        project = _acads_project()
        surface = SlipCircle(centre_x=34.0, centre_y=44.0, radius=19.0)
        method_id = "bishop_simplified"
        with project.regions_frozen():
            plain = _Probe(method=get_method(method_id)(), num_slices=20)
            plain._weak_bands_cache = None
            plain._pending_notes = []
            a = plain.evaluate_circle(project, surface)

            told = _Probe(method=get_method(method_id)(), num_slices=20,
                          seismic_analysis=SeismicAnalysisSettings())
            told._weak_bands_cache = None
            told._pending_notes = []
            b = told.evaluate_circle(project, surface)
        assert a is not None and b is not None
        assert a.fos == b.fos
        assert a.base_normal_force == b.base_normal_force
        assert a.base_shear_force == b.base_shear_force
        assert a.base_shear_strength == b.base_shear_strength
        assert told.objective == OBJECTIVE_FOS
        assert "ky" not in (b.details or {})

    def test_build_search_only_passes_the_settings_when_they_are_on(self):
        off = _acads_project()
        assert build_search(off, "bishop_simplified").seismic_analysis is None
        on = _acads_project()
        on.settings.seismic.compute_ky = True
        assert build_search(on, "bishop_simplified").seismic_analysis \
            is not None

    def test_the_reported_surface_changes_with_the_objective(self):
        """The reference warns its Ky surface is "quite different from the
        critical surface". On this slope it is.
        """
        run = _acads_run(compute_ky=True)
        assert run.objective == OBJECTIVE_KY
        by_ky = run.critical
        valid = [r for r in run.evaluations if r.is_valid
                 and getattr(r, "admissible", True)]
        by_fos = min(valid, key=lambda r: r.fos)
        assert by_ky is not None
        assert by_ky is not by_fos
        # And each really is the best under its own measure.
        assert by_ky.details["ky"] < by_fos.details["ky"]
        assert by_fos.fos < by_ky.fos

    def test_the_population_is_the_same_either_way(self):
        """Changing what is reported must not change what was searched.

        The grid is deterministic, so the two runs evaluate the same
        circles; only the ranking differs. If this ever fails, the Ky
        solve has started to influence generation, which it must not.
        """
        with_ky = _acads_run(compute_ky=True)
        without = _acads_run(compute_ky=False)
        assert with_ky.valid_count == without.valid_count
        assert with_ky.invalid_count == without.invalid_count
        assert without.objective == OBJECTIVE_FOS
        a = sorted(r.fos for r in with_ky.evaluations if r.is_valid)
        b = sorted(r.fos for r in without.evaluations if r.is_valid)
        assert a == b

    def test_a_surface_without_a_coefficient_can_never_win(self):
        class _Fake:
            is_valid = True
            fos = 0.5
            details = {"ky": math.nan}
        assert surface_score(_Fake(), OBJECTIVE_KY) == math.inf
        assert surface_score(_Fake(), OBJECTIVE_FOS) == 0.5


# ======================================================================
class TestTheNewmarkObjectiveIsTheKyObjective:
    """Why the Newmark mode does not integrate inside the search."""

    def test_the_surface_that_moves_most_is_the_one_with_the_lowest_ky(self):
        """Over the whole population of a real run.

        The claim is an identity — the displacement is non-increasing in
        the critical acceleration — but the thing that matters is that it
        holds over the Ky values a search actually produces, which is what
        this checks.
        """
        import random
        rng = random.Random(11)
        record = [rng.uniform(-0.45, 0.45) for _ in range(1500)]
        run = _acads_run(compute_ky=True)
        pairs = []
        for r in run.evaluations:
            if not r.is_valid:
                continue
            ky = (r.details or {}).get("ky")
            if ky is None or not math.isfinite(ky):
                continue
            pairs.append((ky, rigid_block_displacement(record, 0.01, ky)))
        assert len(pairs) > 20
        lowest_ky = min(pairs)[0]
        largest_move = max(pairs, key=lambda t: t[1])[0]
        assert largest_move == pytest.approx(lowest_ky, abs=1e-12)

# ======================================================================
class TestTheWholeRunEndToEnd:
    """``run_analysis`` is the door a script and the interface share."""

    @staticmethod
    def _project(newmark: bool, with_record: bool):
        from ogr_core.loads.seismic_record import SeismicRecord
        project = _acads_project()
        project.settings.seismic.compute_ky = True
        project.settings.seismic.newmark = newmark
        if with_record:
            import random
            rng = random.Random(3)
            record = SeismicRecord(
                name="synthetic", dt=0.01,
                accelerations=[rng.uniform(-0.45, 0.45) for _ in range(600)])
            project.seismic_records.append(record)
            project.settings.seismic.record_id = record.id
        return project

    def test_the_run_attaches_a_coefficient_to_every_valid_surface(self):
        from ogr_slip2d.analysis_runner import run_analysis
        project = self._project(newmark=False, with_record=False)
        outcome = run_analysis(project, ["bishop_simplified"],
                               allow_unconfigured=True)
        result = outcome.results["bishop_simplified"]
        valid = [r for r in result.evaluations if r.is_valid]
        assert valid
        assert all("ky" in (r.details or {}) for r in valid)
        assert result.objective == OBJECTIVE_KY

    def test_newmark_without_a_record_says_so_and_invents_nothing(self):
        from ogr_slip2d.analysis_runner import run_analysis
        project = self._project(newmark=True, with_record=False)
        outcome = run_analysis(project, ["bishop_simplified"],
                               allow_unconfigured=True)
        result = outcome.results["bishop_simplified"]
        assert any("no seismic record is selected" in w
                   for w in outcome.warnings), outcome.warnings
        valid = [r for r in result.evaluations if r.is_valid]
        assert not any("newmark_displacement" in (r.details or {})
                       for r in valid)

    def test_newmark_with_a_record_attaches_displacements(self):
        from ogr_slip2d.analysis_runner import run_analysis
        project = self._project(newmark=True, with_record=True)
        outcome = run_analysis(project, ["bishop_simplified"],
                               allow_unconfigured=True)
        result = outcome.results["bishop_simplified"]
        critical = result.critical
        assert critical is not None
        details = critical.details or {}
        assert "newmark_displacement" in details
        assert details["newmark_displacement"] >= 0.0
        # The reported surface is the one that moves the most, which is
        # the one with the lowest Ky. Both statements checked together.
        moved = [(r.details["newmark_displacement"], r.details["ky"])
                 for r in result.evaluations
                 if r.is_valid and "newmark_displacement" in (r.details or {})]
        assert moved
        assert max(moved)[0] == pytest.approx(
            details["newmark_displacement"])

# ======================================================================
class TestAProjectThatAlreadyShakes:
    """A model carrying its own kh, asked for Ky as well.

    The defect this class exists to keep closed, found by re-reading the
    hook rather than by a failing test: the search hands the solver the
    factor of safety it just computed as the starting point of a scan over
    kh. That value is FS(0) only when the project applies no coefficient
    of its own. With kh = 0.15 stored, the scan would be anchored at the
    factor WITH the earthquake and then walk kh up from zero, and every
    bracket after that is a bracket on the wrong function.

    Ky replaces the stored coefficient rather than adding to it - which is
    what the reference does, since its Ky scenario is a scenario of its
    own - and the run says so.
    """

    @staticmethod
    def _ky_of(kh: float):
        project = _acads_project()
        project.seismic.kh = kh
        project.settings.seismic.compute_ky = True
        surface = SlipCircle(centre_x=34.0, centre_y=44.0, radius=19.0)
        search = build_search(project, "bishop_simplified")
        with project.regions_frozen():
            res = search.evaluate_circle(project, surface)
        return res

    def test_the_coefficient_does_not_depend_on_the_stored_one(self):
        quiet = self._ky_of(0.0)
        shaking = self._ky_of(0.15)
        assert quiet is not None and shaking is not None
        assert quiet.details["ky"] == pytest.approx(
            shaking.details["ky"], rel=1e-9)

    def test_and_the_stored_factor_of_safety_still_differs(self):
        """Otherwise the test above would pass on two identical runs."""
        assert self._ky_of(0.15).fos < self._ky_of(0.0).fos

    def test_the_run_says_the_coefficient_is_replaced(self):
        from ogr_slip2d.analysis_runner import run_analysis
        project = _acads_project()
        project.seismic.kh = 0.15
        project.settings.seismic.compute_ky = True
        outcome = run_analysis(project, ["bishop_simplified"],
                               allow_unconfigured=True)
        assert any("replaces it rather than adding" in w
                   for w in outcome.warnings), outcome.warnings

# ======================================================================
class TestItWarnsWhereTheAnswerChangesMeaning:
    """The seismic modes change which surface is "the" surface.

    Everything downstream that consumes "the critical surface" is then
    consuming a different one, and the case that matters is the
    probabilistic run: it takes statistics of ``critical.fos`` sample by
    sample, which under the Ky objective is the factor of the lowest-Ky
    surface. Defensible to want; terrible to get by accident.
    """

    def test_the_probabilistic_combination_is_reported(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        project = Project("probabilistic and seismic")
        project.settings.seismic.compute_ky = True
        project.settings.statistics.probabilistic_analysis = True
        assert any("lowest critical seismic coefficient" in w
                   for w in settings_warnings(project))

    def test_and_it_is_silent_when_either_half_is_off(self):
        from ogr_slip2d.analysis_runner import settings_warnings
        only_stats = Project("probabilistic only")
        only_stats.settings.statistics.probabilistic_analysis = True
        only_seismic = Project("seismic only")
        only_seismic.settings.seismic.compute_ky = True
        for project in (only_stats, only_seismic):
            assert not any("lowest critical seismic coefficient" in w
                           for w in settings_warnings(project))

# ======================================================================
class TestTheOptimisationDescendsTheSameThing:
    """The walk has to minimise what the run minimises.

    Found by reading rather than by a failure: ``optimize_surface``
    descended ``res.fos`` while the search around it was ranking by Ky, so
    with the seismic mode on the walk dragged vertices towards a low
    factor of safety and the run then reported the Ky of wherever they
    landed. An optimisation optimising something nobody asked for.

    The convergence history follows the objective for the same reason: a
    stopping rule that watches a different quantity from the one being
    descended can stop while that quantity is still falling.
    """

    def test_the_walk_reads_the_objective_off_the_evaluator(self):
        import io
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source = io.open(os.path.join(root, "ogr_slip2d", "optimize.py"),
                         encoding="utf-8").read()
        assert 'scorer = getattr(evaluator, "score", None)' in source
        assert "history.append(best_score)" in source

    def test_a_walk_under_the_two_objectives_takes_different_paths(self):
        """The measurable half: same seed, same start, different answers.

        If the walk still descended the factor of safety the two runs
        would be identical, because everything else about them is.
        """
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface

        def _walk(compute_ky):
            project = _acads_project()
            project.settings.seismic.compute_ky = compute_ky
            search = build_search(project, "bishop_simplified")
            start = SlipSurface(polyline=Polyline([
                Vertex(29.7, 25.0), Vertex(34.0, 23.0), Vertex(40.0, 22.6),
                Vertex(46.0, 24.5), Vertex(50.99, 35.0)]))
            opts = OptimizeSettings(enabled=True, max_iterations=200)
            with project.regions_frozen():
                surface, res, _rep = optimize_surface(
                    project, search, start, opts)
            return surface, res

        plain_surface, plain = _walk(False)
        ky_surface, ky = _walk(True)
        assert plain is not None and ky is not None
        plain_points = plain_surface.polyline.vertices
        ky_points = ky_surface.polyline.vertices
        moved = any(abs(a.x - b.x) > 1e-9 or abs(a.y - b.y) > 1e-9
                    for a, b in zip(plain_points, ky_points))
        assert moved, ("the two objectives walked to the same surface; the "
                       "walk may have stopped reading the objective")
