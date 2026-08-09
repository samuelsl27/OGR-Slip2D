# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The drawdown level sweep: the total drawdown is not always the worst.

The invariant
-------------
A rapid-drawdown analysis run only at total drawdown can be **on the
unsafe side**, and the reference documentation contains both behaviours,
which is what makes this a fact about slopes rather than a preference:

* **Homogeneous slope** — Morgenstern (1963), verification problems #100
  and #101: worst when the reservoir is emptied completely, FoS 1.20
  against 1.41 at half drawdown.
* **Zoned dam with a freely draining upstream shell** — the reference
  states it outright: *"For this example, the minimum safety factor at
  partial drawdown is lower than the minimum safety factor at full
  drawdown […] For this particular model, a minimum safety factor
  therefore exists at some intermediate drawdown level."* The mechanism
  it gives is that the granular shell drains to zero pore pressure only
  when the reservoir is gone entirely; a partial drawdown leaves a water
  table standing in it near the toe.

Both are exercised below. The homogeneous case is the one with published
numbers, so it anchors the sweep against something external; the zoned
case reproduces the documented mechanism and measures what it costs to
ignore it — about 12 % on the unsafe side.

Why the search is repeated at every level
-----------------------------------------
``run_sensitivity`` already sweeps a parameter and collects factors of
safety, and using it here would be a trap: it **fixes the critical
surface**. The critical surface MOVES with the reservoir level, so held
fixed the sweep reports a factor of safety that is too high and can miss
the intermediate minimum altogether.
``test_a_fixed_surface_would_miss_the_minimum`` is the guard against
somebody "simplifying" this module into that one.

Cost
----
A sweep is one full search per level, so this file is the expensive kind.
The grid is deliberately the coarsest that still resolves the
intermediate minimum (3 x 4 centres, 70 ft radius steps, 18 slices), and
each sweep is computed ONCE and shared by every test that reads it — the
same trick that took a seepage file from 48 s to 12 s. Around 20 s total.
"""
from __future__ import annotations

import math

GAMMA_W = 62.4

# Published minima for the homogeneous slope, from problems #100/#101.
MORGENSTERN_TOTAL = 1.20
MORGENSTERN_HALF = 1.41

# The search these tests can afford. Declared, not tuned per test.
GRID = dict(grid_nx=3, grid_ny=4, radius_increment=70.0, min_radius=140.0)
N_SLICES = 18
N_LEVELS = 4

_CACHE: dict = {}


# ======================================================================
def _base_project(name):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(373, 0), Vertex(373, 100), Vertex(300, 100),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, 100), Vertex(378, 100)],
                          closed=False),
        btype=BoundaryType.WATER_TABLE))
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.settings.groundwater.set_advanced_option("rapid_drawdown")
    p.settings.groundwater.rapid_drawdown_method = "b_bar"
    return p


def _homogeneous():
    """Morgenstern's slope. Total drawdown is the critical case here."""
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType

    p = _base_project("Morgenstern 1963")
    m = Material(
        name="Slope", unit_weight=124.8, sat_unit_weight=124.8,
        strength=MohrCoulomb(cohesion=312.0, friction_angle=30.0),
        pore_pressure=PorePressureType.WATER_TABLE)
    m.undrained_behaviour = True
    m.b_bar = 1.0
    p.materials = [m]
    return p


def _zoned():
    """A core plus a freely draining upstream shell — Tutorial 13's dam.

    The shell is what creates the intermediate minimum: with the
    reservoir gone it drains to zero pore pressure, but a partial
    drawdown leaves a water table inside it near the toe.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType

    p = _base_project("Zoned dam")
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(120, 0), Vertex(300, 100)],
                          closed=False),
        btype=BoundaryType.MATERIAL))
    core = Material(
        name="Core", unit_weight=124.8, sat_unit_weight=124.8,
        strength=MohrCoulomb(cohesion=312.0, friction_angle=30.0),
        pore_pressure=PorePressureType.WATER_TABLE)
    core.undrained_behaviour = True
    core.b_bar = 1.0
    shell = Material(
        name="Shell", unit_weight=130.0, sat_unit_weight=130.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=34.0),
        pore_pressure=PorePressureType.WATER_TABLE)
    shell.undrained_behaviour = False
    shell.b_bar = 0.0
    p.materials = [shell, core]
    for r in p.resolve_regions():
        cx, cy = r.centroid()
        p.assign_material_at(
            cx, cy, (shell if cx < 120 + 1.8 * cy else core).id)
    return p


def _factory(project):
    """The configured search, as the application would build it."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
    from ogr_slip2d.search import GridSearch

    def make(_method_id):
        return GridSearch(
            wrap_for_drawdown(BishopSimplified(), project,
                              num_slices=N_SLICES),
            grid_x=(60, 240), grid_y=(160, 420),
            num_slices=N_SLICES, **GRID)
    return make


def _sweep(kind):
    """The sweep for ``kind``, computed once and shared."""
    from ogr_core.statistics import run_drawdown_sweep

    if kind not in _CACHE:
        project = _homogeneous() if kind == "homogeneous" else _zoned()
        res = run_drawdown_sweep(
            project, _factory(project), ["bishop_simplified"],
            n_levels=N_LEVELS, include_total=True)
        _CACHE[kind] = (project, res.by_method["bishop_simplified"])
    return _CACHE[kind]


# ======================================================================
class TestTheHomogeneousSlopeIsWorstEmptied:
    """The case with published numbers, so the sweep has an anchor."""

    def test_the_critical_level_is_the_total_drawdown(self):
        _p, sweep = _sweep("homogeneous")
        level, fos, _s = sweep.critical()
        # Level 0 and "total drawdown" are the same state here: the toe
        # sits at y = 0, so a reservoir at 0 ponds nothing.
        assert level is None or abs(level) < 1e-9, (level, fos)

    def test_it_agrees_with_the_published_minimum(self):
        _p, sweep = _sweep("homogeneous")
        _lv, fos, _s = sweep.critical()
        assert math.isclose(fos, MORGENSTERN_TOTAL, rel_tol=0.06), (
            f"{fos:.4f} vs published {MORGENSTERN_TOTAL}")

    def test_half_drawdown_is_safer_than_total(self):
        """#101 (1.41) above #100 (1.20), the ordering the sweep must
        reproduce for the anchor to mean anything."""
        _p, sweep = _sweep("homogeneous")
        by_level = {lv: f for lv, f, _s in sweep.valid if lv is not None}
        half = min(by_level, key=lambda lv: abs(lv - 50.0))
        total = sweep.at_total_drawdown()[1]
        assert by_level[half] > total, (half, by_level[half], total)

    def test_nothing_is_gained_by_sweeping_here(self):
        """The reassuring answer: no unsafe margin on a homogeneous
        slope. A sweep that reported one would be inventing it."""
        _p, sweep = _sweep("homogeneous")
        assert sweep.unsafe_margin() < 0.01, sweep.unsafe_margin()


# ======================================================================
class TestTheZonedDamIsWorstPartlyEmptied:
    """The documented mechanism, and what ignoring it costs."""

    def test_the_critical_level_is_intermediate(self):
        _p, sweep = _sweep("zoned")
        level, _fos, _s = sweep.critical()
        assert level is not None, "total drawdown came out critical"
        assert 0.0 < level < 100.0, level

    def test_the_total_drawdown_overstates_the_factor_of_safety(self):
        """The number that justifies the whole feature."""
        _p, sweep = _sweep("zoned")
        margin = sweep.unsafe_margin()
        assert margin > 0.05, (
            f"the total drawdown is only {100 * margin:.1f} % above the "
            f"worst level; the zoned mechanism is not being reproduced")

    def test_the_critical_surface_moves_with_the_level(self):
        """Which is exactly why the search cannot be done once."""
        _p, sweep = _sweep("zoned")
        _lv, _f, s_crit = sweep.critical()
        _tl, _tf, s_total = sweep.at_total_drawdown()
        assert s_crit is not None and s_total is not None
        assert s_crit != s_total, s_crit


# ======================================================================
class TestAFixedSurfaceWouldMissIt:
    """Rule 7, aimed at a refactor that has not happened yet.

    ``run_sensitivity`` holds the critical surface fixed and only
    re-evaluates it. Measured on the zoned dam, holding the
    total-drawdown surface fixed overstates the factor of safety at every
    other level, and by a lot where the reservoir is still high:

        level 100 ... 2.0248 swept, 2.6539 held    +31.1 %
        level  67 ... 1.5505 swept, 1.8072 held    +16.6 %
        level  33 ... 1.3244 swept, 1.3452 held     +1.6 %
        total ...... 1.4887 swept, 1.4887 held      +0.0 %

    Which is what makes it insidious: the error vanishes exactly where
    the surface was found, so the one level a user would sanity-check
    agrees perfectly. This test exists so that turning the sweep into a
    sensitivity variable cannot be done quietly.
    """

    def _held(self):
        from ogr_core.hydraulic.drawdown_levels import project_at_level
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        project, sweep = _sweep("zoned")
        _tl, _tf, s_total = sweep.at_total_drawdown()
        assert s_total is not None
        fixed = SlipCircle(centre_x=s_total["centre_x"],
                           centre_y=s_total["centre_y"],
                           radius=s_total["radius"])
        out = []
        for level, swept, _s in sweep.valid:
            at = project_at_level(project, level)
            method = wrap_for_drawdown(BishopSimplified(), at,
                                       num_slices=N_SLICES)
            sl = slice_surface(at, fixed, num_slices=N_SLICES)
            if sl is None:
                continue
            f = method.compute_fos(at, fixed, sl).fos
            if math.isfinite(f):
                out.append((level, swept, f))
        assert out, "the total-drawdown surface never sliced"
        return sweep, out

    def test_a_fixed_surface_is_never_below_the_swept_one(self):
        """Structural: the sweep minimises over a set that contains it."""
        _sw, held = self._held()
        for level, swept, fixed in held:
            assert fixed > swept - 1e-6, (level, swept, fixed)

    def test_and_it_is_badly_high_where_the_reservoir_is_full(self):
        _sw, held = self._held()
        worst = max((fixed / swept - 1.0) for _lv, swept, fixed in held)
        assert worst > 0.15, (
            f"holding the surface fixed only costs {100 * worst:.1f} % at "
            f"its worst; if that is really all it costs, the re-search "
            f"has stopped earning its price and this test should be "
            f"rewritten rather than deleted")

    def test_so_it_reports_a_higher_minimum(self):
        sweep, held = self._held()
        assert min(f for _lv, _s, f in held) > sweep.critical()[1] * 1.01


# ======================================================================
class TestTheKnobsMoveTheNumber:
    """Rule 7 for the two controls the dialog exposes."""

    def test_more_levels_resolve_a_lower_minimum(self):
        """A coarser sweep can only miss the dip, never invent one."""
        from ogr_core.statistics import run_drawdown_sweep

        project = _zoned()
        make = _factory(project)
        coarse = run_drawdown_sweep(project, make, ["bishop_simplified"],
                                    n_levels=2, include_total=False)
        _p, fine = _sweep("zoned")
        c = coarse.by_method["bishop_simplified"].critical()
        assert c is not None
        assert fine.critical()[1] <= c[1] + 1e-9, (fine.critical()[1], c[1])

    def test_include_total_adds_the_total_drawdown_point(self):
        from ogr_core.statistics import run_drawdown_sweep

        project = _homogeneous()
        make = _factory(project)
        without = run_drawdown_sweep(project, make, ["bishop_simplified"],
                                     n_levels=2, include_total=False)
        with_ = run_drawdown_sweep(project, make, ["bishop_simplified"],
                                   n_levels=2, include_total=True)
        a = without.by_method["bishop_simplified"]
        b = with_.by_method["bishop_simplified"]
        assert a.at_total_drawdown() is None
        assert b.at_total_drawdown() is not None
        assert len(b.levels) == len(a.levels) + 1


# ======================================================================
class TestTheSweepRefusesWhatItCannotDo:
    """Explicit refusals, not silent empty results."""

    def test_without_rapid_drawdown_it_says_so(self):
        from ogr_core.statistics import run_drawdown_sweep

        project = _homogeneous()
        project.settings.groundwater.rapid_drawdown = False
        res = run_drawdown_sweep(project, _factory(project),
                                 ["bishop_simplified"], n_levels=2)
        assert "error" in res.notes
        assert not res.by_method

    def test_without_a_method_it_says_so(self):
        from ogr_core.statistics import run_drawdown_sweep

        project = _homogeneous()
        res = run_drawdown_sweep(project, _factory(project), [], n_levels=2)
        assert "error" in res.notes


# ======================================================================
class TestMovingTheLevelKeepsTheGeometry:
    """``project_at_level`` translates the line; it does not flatten it."""

    def test_a_sloped_drawdown_line_keeps_its_shape(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.hydraulic.drawdown_levels import (
            drawdown_boundary, project_at_level,
        )

        p = _homogeneous()
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(0, 30), Vertex(373, 50)],
                              closed=False),
            btype=BoundaryType.DRAWDOWN))
        moved = drawdown_boundary(project_at_level(p, 60.0)).polyline.vertices
        assert math.isclose(moved[1].y - moved[0].y, 20.0)      # same slope
        assert math.isclose(0.5 * (moved[0].y + moved[1].y), 60.0)

    def test_the_users_project_is_not_touched(self):
        from ogr_core.hydraulic.drawdown_levels import project_at_level

        p = _homogeneous()
        before = len(p.boundaries)
        project_at_level(p, 40.0)
        project_at_level(p, None)
        assert len(p.boundaries) == before

    def test_no_drawdown_line_gets_one_synthesised(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.hydraulic.drawdown_levels import (
            drawdown_boundary, project_at_level,
        )

        p = _homogeneous()
        assert drawdown_boundary(p) is None
        at = project_at_level(p, 40.0)
        line = drawdown_boundary(at)
        assert line is not None and line.btype == BoundaryType.DRAWDOWN
        assert all(math.isclose(v.y, 40.0) for v in line.polyline.vertices)
        # It must span the model, or the outermost slices lose their water.
        xs = [v.x for v in line.polyline.vertices]
        assert min(xs) < 0.0 and max(xs) > 373.0

    def test_total_drawdown_removes_the_line(self):
        from ogr_core.hydraulic.drawdown_levels import (
            drawdown_boundary, project_at_level,
        )

        p = _homogeneous()
        assert drawdown_boundary(project_at_level(p, None)) is None
