# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.125 — the transient unsaturated seepage field, coupled to the
limit-equilibrium engine, on the earth dam of verification problem 102.

What these tests protect
------------------------

**The geometry, before any factor of safety.** The manual's figure
labels the dam's vertices rounded to whole metres, and the rounding is a
trap: six result figures publish the critical circle as centre, radius
and both endpoints, and every one of them has its left endpoint at
y = 28.600 and its right at y = 7.300 — with a different x each time. On
a sloping face a fixed elevation forces a fixed abscissa, so a varying x
at a fixed y can only mean those endpoints lie on HORIZONTAL stretches.
The crest is therefore at 28.6 and the downstream apron at 7.3, where the
labels read 29 and 7. ``TestTheGeometryIsOverdetermined`` checks the
twelve endpoint equations in closed form, with no analysis involved.

**Four published factors of safety that do not depend on the
permeability.** The manual publishes 26 of them and no hydraulic
properties whatsoever, and the paper it takes them from is paywalled. But
a steady state does not depend on k_s — only on the shape of k(psi), and
in equilibrium the unsaturated zone is essentially hydrostatic — so the
dry case, the initial steady state (for both phi_b) and the drained final
state ARE fully determined by what is published. Those four are the
closing criterion. The remaining 22 are a measurement, not a validation,
and are not tested here.

**Why the fifth is not a fifth.** At 1500 h with phi_b = 37 the manual
gives 2.612, and it is tempting to treat that as the drained steady state
too. It is not: the reference's own legend for that figure declares a
maximum suction of 9.1 m where the steady state requires 21.3, so the
positive pore pressures have converged and the suctions have not. The
test states the inequality that follows and nothing stronger.

**Three defects this version closes**, each with the measurement that
found it:

* the prescribed reservoir was extrapolated past the last submerged node,
  so a dam with water on one side reported seventeen metres of standing
  water on the other — a factor of safety of 5.83 where the answer is
  1.72;
* the seepage-face switch budget froze 47 of 77 exit nodes and the run
  still called itself converged, leaving the free surface 4.5 m too high;
* a transient stage was analysed with its own pore pressures and the
  boundary conditions of whatever stage happened to be current, which on
  a drawdown means the weight of a reservoir that has already been
  emptied.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402

from ogr_core.geometry import (  # noqa: E402
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
)
from ogr_core.hydraulic import HydraulicProperties  # noqa: E402
from ogr_core.hydraulic.permeability_models import (  # noqa: E402
    PermeabilityModel,
)
from ogr_core.hydraulic.ponded_water import (  # noqa: E402
    ponded_water_level_at,
)
from ogr_core.materials import (  # noqa: E402
    Material,
    MohrCoulomb,
    PorePressureType,
)
from ogr_core.project import Project  # noqa: E402
from ogr_core.project.settings import GroundwaterMethod  # noqa: E402
from ogr_fem2d.mesh import generate_mesh_for_project  # noqa: E402
from ogr_fem2d.solvers import (  # noqa: E402
    BCType,
    SIDE_LEFT,
    SIDE_RIGHT,
    UnsaturatedSeepageSolver,
    apply_reservoir,
    boundary_cycle,
    default_boundary_conditions,
    wetted_nodes,
)
from ogr_slip2d.methods import method_registry  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication  # noqa: E402
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


# ======================================================================
# The dam, as the published circles pin it down.
#
# The abscissae come from the vertex labels of figure 102.1; the two
# elevations that matter come from the endpoints of the six published
# circles, NOT from the labels. The toe is the one abscissa the labels
# get wrong in a way that shows: the label says 158, and a right endpoint
# published at x = 157.908 with y = 7.300 must already be on the apron,
# so the toe is at or before it.
CREST_Y = 28.600
APRON_Y = 7.300
TOE_X = 157.908
DAM = [(0.0, 0.0), (0.0, APRON_Y), (34.0, APRON_Y), (87.0, 24.41),
       (100.0, CREST_Y), (107.0, CREST_Y), (TOE_X, APRON_Y),
       (191.0, APRON_Y), (191.0, 0.0)]

RESERVOIR = 24.41          # total head on the wetted perimeter, fig. 102.3
TAILWATER = APRON_Y

#: (centre_x, centre_y, radius, x_left, x_right) of every circle the
#: manual publishes for this problem, figure by figure.
PUBLISHED_CIRCLES = {
    "dry":            (151.922, 69.595, 62.582, 104.636, 157.908),
    "initial":        (146.657, 50.211, 46.166, 105.861, 163.686),
    "b0_80h":         (147.115, 50.481, 46.589, 105.984, 164.605),
    "b0_300h":        (147.669, 51.756, 48.598, 104.943, 167.300),
    "b0_1500h":       (148.171, 52.492, 49.767, 104.514, 169.015),
    "b37_80h":        (146.127, 51.505, 48.199, 103.718, 165.340),
    "b37_300h":       (147.455, 53.610, 51.558, 102.370, 170.117),
    "b37_1500h":      (148.109, 54.119, 52.376, 102.370, 171.587),
}

#: Table 102.2 and 102.3, and the two figures that carry a factor of
#: safety of their own. Only the four marked here are used as criteria —
#: see the module docstring for why the rest are not.
PUB_DRY = 2.455
PUB_INITIAL = {0.0: 1.745, 37.0: 1.815}
PUB_1500 = {0.0: 2.376, 37.0: 2.612}
#: Huang and Jia's own column, which stops moving for phi_b = 0 (2.374 at
#: both 1000 and 1500 h) and is still climbing for phi_b = 37 (2.804 then
#: 2.813). That is the published evidence that only one of the two has
#: reached its steady state.
PUB_HJ_1000_1500 = {0.0: (2.374, 2.374), 37.0: (2.804, 2.813)}

_CACHE: dict = {}


def _dam_project(*, fem=True, phi_b=0.0, elements=3000, cutoff=None):
    p = Project()
    p.boundaries.append(Boundary(
        btype=BoundaryType.EXTERNAL,
        polyline=Polyline([Vertex(x, y) for x, y in DAM], closed=True)))
    m = Material(name="dam", unit_weight=18.2,
                 strength=MohrCoulomb(cohesion=13.8, friction_angle=37.0))
    m.phi_b = phi_b
    m.hydraulic = HydraulicProperties(
        ks=1e-6, model=PermeabilityModel.VAN_GENUCHTEN)
    m.pore_pressure = (PorePressureType.FEM_SEEPAGE if fem
                       else PorePressureType.NONE)
    p.materials.append(m)
    p.settings.groundwater.method = GroundwaterMethod.FEA_STEADY.value
    p.settings.groundwater.negative_pore_pressure_cutoff = cutoff
    if fem:
        p.fem_mesh = generate_mesh_for_project(p, target_elements=elements)
    return p, m


def _solve(p, m, level, *, tail=True, switches=None):
    mesh = p.fem_mesh
    bcs = default_boundary_conditions(mesh)
    apply_reservoir(bcs, mesh, level, SIDE_LEFT)
    if tail:
        apply_reservoir(bcs, mesh, TAILWATER, SIDE_RIGHT)
    p.seepage_bcs = bcs
    p._fea_ponding_cache = None
    kw = {} if switches is None else {"max_node_switches": switches}
    solver = UnsaturatedSeepageSolver(
        mesh, {m.id: m.hydraulic}, gamma_w=9.81, relaxation=0.4,
        max_iterations=400, tolerance=1e-5, **kw)
    p.seepage_result = solver.solve_unsaturated(bcs)
    return solver


def _fos(project, circle_key, method="spencer", slices=50):
    cx, cy, r, _xl, _xr = PUBLISHED_CIRCLES[circle_key]
    search = GridSearch(method=method_registry()[method](),
                        num_slices=slices, min_area=0.0)
    res = search.evaluate_circle(
        project, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
    assert res is not None, f"circle {circle_key} was rejected"
    return res.fos


def _steady(level, phi_b, *, cutoff=None):
    """One solved dam per (level, cutoff), shared across the tests.

    The seepage solve is the expensive part of this file and it does not
    depend on phi_b — the strength does. Sharing it is what keeps the
    published-number tests to a couple of seconds instead of a dozen.
    """
    key = (level, cutoff)
    if key not in _CACHE:
        p, m = _dam_project(cutoff=cutoff)
        _solve(p, m, level)
        _CACHE[key] = (p, m)
    p, m = _CACHE[key]
    m.phi_b = phi_b
    return p, m


def _ground_y(x: float) -> float:
    """Elevation of the dam surface at ``x`` — the closed-form profile."""
    top = [(0.0, APRON_Y), (34.0, APRON_Y), (87.0, 24.41),
           (100.0, CREST_Y), (107.0, CREST_Y), (TOE_X, APRON_Y),
           (191.0, APRON_Y)]
    for (x1, y1), (x2, y2) in zip(top[:-1], top[1:]):
        if x1 <= x <= x2:
            if x2 == x1:
                return max(y1, y2)
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    raise AssertionError(f"x = {x} is outside the dam")


# ======================================================================
class TestTheGeometryIsOverdetermined:
    """The published circles derive the dam, and no factor of safety is
    involved in the derivation."""

    def test_every_published_endpoint_lies_on_its_own_circle(self):
        """Sixteen closed-form equations, to the printed precision.

        The tolerance is not a preference: the manual prints centre,
        radius and endpoint to three decimals, so a reconstructed
        elevation carries about a millimetre of their rounding. Two
        millimetres is that, doubled; the worst of the sixteen is 1.4 mm.
        """
        worst = 0.0
        for key, (cx, cy, r, xl, xr) in PUBLISHED_CIRCLES.items():
            for x in (xl, xr):
                dy = math.sqrt(max(r * r - (x - cx) ** 2, 0.0))
                y = cy - dy
                expected = CREST_Y if x < 130 else APRON_Y
                assert abs(y - expected) < 2e-3, (key, x, y, expected)
                worst = max(worst, abs(y - expected))
        assert worst < 2e-3
        assert worst > 1e-4, ("a residual this small would mean the "
                              "elevations were read off, not derived")

    def test_every_left_endpoint_lands_on_the_crest(self):
        """A fixed elevation with a varying abscissa can only be a
        horizontal stretch, and this is what puts the crest at 28.6."""
        xs = [c[3] for c in PUBLISHED_CIRCLES.values()]
        assert min(xs) >= 100.0 and max(xs) <= 107.0
        assert max(xs) - min(xs) > 2.0, "they would not pin a plateau"
        for x in xs:
            assert _ground_y(x) == pytest.approx(CREST_Y, abs=1e-9)

    def test_every_right_endpoint_lands_on_the_apron(self):
        xs = [c[4] for c in PUBLISHED_CIRCLES.values()]
        assert max(xs) - min(xs) > 10.0
        for x in xs:
            assert _ground_y(x) == pytest.approx(APRON_Y, abs=1e-9)

    def test_the_label_of_the_toe_cannot_be_taken_literally(self):
        """The figure says 158 and the published data forbids it.

        A right endpoint at x = 157.908 with y = 7.300 is on the apron, so
        the apron starts at or before 157.908. Reading the label as an
        exact 158 puts that endpoint on the downstream FACE, 0.04 m above
        where the manual says it is.
        """
        assert TOE_X <= min(c[4] for c in PUBLISHED_CIRCLES.values())
        face = 28.6 - (157.908 - 107.0) * (28.6 - 7.3) / (158.0 - 107.0)
        assert abs(face - APRON_Y) > 0.03


# ======================================================================
class TestThePublishedFactors:
    """The four values that do not depend on the permeability."""

    def test_the_dry_case(self):
        p, _m = _dam_project(fem=False)
        v = _fos(p, "dry")
        assert v == pytest.approx(PUB_DRY, rel=0.01), v

    def test_the_initial_steady_state_for_both_phi_b(self):
        for phi_b, pub in PUB_INITIAL.items():
            p, _m = _steady(RESERVOIR, phi_b)
            v = _fos(p, "initial")
            assert v == pytest.approx(pub, rel=0.02), (phi_b, v, pub)

    def test_the_suction_term_alone(self):
        """The ratio of the two initial factors is the effect of phi_b
        with the bias common to both divided out — which is the part this
        problem exists to verify."""
        p, _m = _steady(RESERVOIR, 0.0)
        a = _fos(p, "initial")
        p, _m = _steady(RESERVOIR, 37.0)
        b = _fos(p, "initial")
        published = PUB_INITIAL[37.0] / PUB_INITIAL[0.0]
        assert b / a == pytest.approx(published, rel=0.01), (b / a, published)

    def test_the_drained_final_state(self):
        p, _m = _steady(TAILWATER, 0.0)
        v = _fos(p, "b0_1500h")
        assert v == pytest.approx(PUB_1500[0.0], rel=0.02), v

    def test_the_reservoir_lowers_the_factor(self):
        """The contrast that says the water is doing something at all."""
        dry, _ = _dam_project(fem=False)
        full, _ = _steady(RESERVOIR, 0.0)
        assert _fos(full, "dry") < _fos(dry, "dry")


# ======================================================================
class TestTheFifthValueIsNotASteadyState:
    """Why 2.612 is not used as a criterion, said with the published
    evidence rather than with an excuse."""

    def test_the_reference_says_its_own_suctions_have_not_settled(self):
        """Huang and Jia's column stops moving for phi_b = 0 and is still
        climbing for phi_b = 37 between 1000 h and 1500 h."""
        a, b = PUB_HJ_1000_1500[0.0]
        assert abs(b - a) < 0.005
        a, b = PUB_HJ_1000_1500[37.0]
        assert b - a > 0.005

    def test_the_steady_state_overshoots_the_published_1500_hours(self):
        """Draining further can only add suction, so the true steady
        state must sit ABOVE a run that has not finished draining."""
        p, _m = _steady(TAILWATER, 37.0)
        v = _fos(p, "b37_1500h")
        assert v > PUB_1500[37.0], v
        # and by a margin the published series makes plausible, not by an
        # arbitrary amount: phi_b = 0 is settled and stays within 2 %.
        p, _m = _steady(TAILWATER, 0.0)
        assert _fos(p, "b0_1500h") == pytest.approx(PUB_1500[0.0], rel=0.02)


# ======================================================================
class TestTheWettedPerimeter:
    """Where a reservoir is, stated as a level and a side."""

    @staticmethod
    def _mesh():
        if "mesh" not in _CACHE:
            p, _m = _dam_project(elements=1200)
            _CACHE["mesh"] = p.fem_mesh
        return _CACHE["mesh"]

    def test_the_boundary_walks_as_one_loop(self):
        mesh = self._mesh()
        cycle = boundary_cycle(mesh)
        assert len(cycle) == len(mesh.boundary_node_ids())
        assert len(set(cycle)) == len(cycle)

    def test_the_walk_never_enters_the_base_of_the_model(self):
        """The failure that made this function necessary: walking both
        ways from the bottom corner runs along the impermeable base, up
        the far end and back over the downstream face."""
        mesh = self._mesh()
        ids = wetted_nodes(mesh, RESERVOIR, SIDE_LEFT)
        assert ids, "the reservoir reached nothing"
        assert max(mesh.nodes[i].x for i in ids) <= 87.0 + 1e-6
        assert len(ids) < 0.5 * len(mesh.boundary_node_ids())

    def test_the_walk_stops_at_the_first_rise(self):
        mesh = self._mesh()
        ids = wetted_nodes(mesh, RESERVOIR, SIDE_LEFT)
        for i in ids:
            assert mesh.nodes[i].y <= RESERVOIR + 1e-6

    def test_a_pond_at_the_same_height_on_the_far_side_is_not_swept_in(self):
        """The apron is at 7.3 on BOTH sides, so a level of 7.3 on the
        left must not select the right one as well."""
        mesh = self._mesh()
        left = wetted_nodes(mesh, TAILWATER, SIDE_LEFT)
        right = wetted_nodes(mesh, TAILWATER, SIDE_RIGHT)
        assert left and right
        assert not (set(left) & set(right))

    def test_a_drawdown_is_the_same_call_with_a_lower_level(self):
        mesh = self._mesh()
        high = set(wetted_nodes(mesh, RESERVOIR, SIDE_LEFT))
        low = set(wetted_nodes(mesh, TAILWATER, SIDE_LEFT))
        assert low < high, "lowering the level must submerge fewer nodes"

    def test_a_level_below_the_model_wets_nothing(self):
        mesh = self._mesh()
        assert wetted_nodes(mesh, -10.0, SIDE_LEFT) == []

    def test_the_walk_never_enters_the_base_even_at_crest_level(self):
        """The stop at the base has to be SAID, not left to the first
        node above the water.

        A level that reaches the highest ground between the two ends
        leaves no such node: the walk crossed the crest, came down the
        far face, ran the whole impermeable base and returned — 174 of
        174 boundary nodes, 83 of them on the foundation, all of them
        prescribed total head along a no-flow boundary.
        """
        mesh = self._mesh()
        ys = [nd.y for nd in mesh.nodes]
        y_base = min(ys)
        for level in (RESERVOIR, CREST_Y, CREST_Y + 5.0):
            ids = wetted_nodes(mesh, level, SIDE_LEFT)
            on_base = [i for i in ids
                       if abs(mesh.nodes[i].y - y_base) < 1e-6]
            # only the bottom corner of the vertical cut itself
            assert len(on_base) <= 1, (level, len(on_base))

    def test_an_end_that_is_a_single_vertex_does_not_open_the_base(self):
        """The other half of the same failure: with no vertical cut at
        the end, BOTH directions are open and one of them is the base.
        Measured before the stop existed: 66 of 130 nodes, 63 on the
        foundation, for a reservoir six metres deep."""
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.project import Project

        pts = [(0, 0), (200, 0), (200, 10), (140, 10), (110, 25),
               (90, 25), (60, 10), (10, 10)]
        p = Project()
        p.boundaries.append(Boundary(
            btype=BoundaryType.EXTERNAL,
            polyline=Polyline([Vertex(x, y) for x, y in pts], closed=True)))
        p.materials.append(Material(
            name="s", unit_weight=18.2,
            strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0)))
        mesh = generate_mesh_for_project(p, target_elements=1200)
        ids = wetted_nodes(mesh, 6.0, SIDE_LEFT)
        assert ids
        assert max(mesh.nodes[i].x for i in ids) < 20.0
        on_base = [i for i in ids if abs(mesh.nodes[i].y) < 1e-6]
        assert len(on_base) <= 1

    def test_the_side_edge_is_a_declared_choice(self):
        """Prescribing the vertical cut or not gives different sets, so
        the flag is not decoration."""
        mesh = self._mesh()
        with_edge = wetted_nodes(mesh, RESERVOIR, SIDE_LEFT)
        without = wetted_nodes(mesh, RESERVOIR, SIDE_LEFT,
                               include_side_edge=False)
        assert len(with_edge) > len(without)
        assert min(mesh.nodes[i].y for i in without) >= APRON_Y - 1e-6


# ======================================================================
class TestTheReservoirIsStatedOnlyWhereItIs:
    """The extrapolation defect, and the identity that replaces it."""

    @staticmethod
    def _dam_with_reservoir():
        if "ponding" not in _CACHE:
            p, m = _dam_project(elements=1200)
            mesh = p.fem_mesh
            bcs = default_boundary_conditions(mesh)
            apply_reservoir(bcs, mesh, RESERVOIR, SIDE_LEFT)
            p.seepage_bcs = bcs
            p._fea_ponding_cache = None
            _CACHE["ponding"] = p
        return _CACHE["ponding"]

    def test_no_water_stands_beyond_the_last_submerged_node(self):
        """The measurement that found it: the level was reported as
        24.41 at x = 180, seventeen metres above the ground there."""
        p = self._dam_with_reservoir()
        for x in (95.0, 110.0, 130.0, 158.0, 180.0, 190.0):
            assert ponded_water_level_at(p, x) is None, x

    def test_water_still_stands_where_it_was_prescribed(self):
        p = self._dam_with_reservoir()
        for x in (1.0, 20.0, 60.0, 85.0):
            level = ponded_water_level_at(p, x)
            assert level == pytest.approx(RESERVOIR, abs=0.05), (x, level)

    def test_lowering_the_level_in_place_is_seen(self):
        """The cache used to key on sizes and identities only, so a
        drawdown over the SAME nodes of the SAME object changed nothing
        it could notice. Measured: 24.41 prescribed, then 12.0 on the
        same nodes, and it kept answering 24.41 — twelve metres of water
        column too much, on the unsafe side.

        And a drawdown IS "the same target with a lower level", which is
        what makes this the ordinary case rather than a corner one.
        """
        p, _m = _dam_project(elements=1200)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, RESERVOIR, SIDE_LEFT)
        p.seepage_bcs = bcs
        p._fea_ponding_cache = None
        assert ponded_water_level_at(p, 20.0) == pytest.approx(RESERVOIR,
                                                               abs=0.05)
        # NOT clearing the cache by hand: that is the whole point.
        apply_reservoir(bcs, mesh, 12.0, SIDE_LEFT)
        assert ponded_water_level_at(p, 20.0) == pytest.approx(12.0,
                                                               abs=0.05)

    def test_the_two_routes_now_answer_the_same_question(self):
        """A drawn water surface has always returned None outside its own
        x-range; the prescribed one used to answer with its end value.
        That disagreement WAS the defect."""
        from ogr_core.hydraulic.water_surfaces import interp_y_on_polyline

        line = Polyline([Vertex(0.0, RESERVOIR), Vertex(87.0, RESERVOIR)])
        p = self._dam_with_reservoir()
        for x in (110.0, 150.0, 190.0):
            assert interp_y_on_polyline(line, x) is None
            assert ponded_water_level_at(p, x) is None

    def test_two_bodies_of_water_do_not_ramp_into_each_other(self):
        """Headwater on one side and tailwater on the other are two
        reservoirs, and the ground between them is dry."""
        p, _m = _dam_project(elements=1200)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, RESERVOIR, SIDE_LEFT)
        apply_reservoir(bcs, mesh, TAILWATER, SIDE_RIGHT)
        p.seepage_bcs = bcs
        p._fea_ponding_cache = None
        for x in (110.0, 130.0, 150.0):
            assert ponded_water_level_at(p, x) is None, x


# ======================================================================
class TestTheSeepageFaceSettles:
    """The anti-chatter budget used to manufacture convergence."""

    def test_a_starved_budget_is_reported_and_not_called_converged(self):
        p, m = _dam_project(elements=1200)
        _solve(p, m, RESERVOIR, tail=False, switches=1)
        notes = p.seepage_result.notes
        assert notes.get("frozen_nodes", 0) > 0
        assert notes.get("unsettled_nodes", 0) > 0
        assert p.seepage_result.converged is False
        assert "seepage face never settled" in notes.get("warning", "")

    def test_the_default_budget_settles_this_dam(self):
        p, m = _dam_project(elements=1200)
        _solve(p, m, RESERVOIR, tail=False)
        notes = p.seepage_result.notes
        assert notes["frozen_nodes"] == 0
        assert notes["unsettled_nodes"] == 0
        assert p.seepage_result.converged

    def test_a_seepage_face_and_a_head_at_the_same_elevation_agree(self):
        """They are the same physical condition, so the answer must not
        depend on which one is written. It used to, by 8 %, and that was
        the frozen switching and not the boundary condition."""
        p1, m1 = _dam_project(elements=1500)
        _solve(p1, m1, RESERVOIR, tail=False)
        p2, m2 = _dam_project(elements=1500)
        _solve(p2, m2, RESERVOIR, tail=True)
        assert _fos(p1, "initial") == pytest.approx(_fos(p2, "initial"),
                                                    rel=2e-3)


# ======================================================================
class TestEachStageCarriesItsOwnWater:
    """A stage is analysed with its own field AND its own reservoir."""

    def test_the_context_manager_installs_and_restores_both(self):
        from ogr_slip2d.transient_stability import with_stage_water

        p, m = _dam_project(elements=800)
        _solve(p, m, RESERVOIR)
        before_result = p.seepage_result
        before_bcs = p.seepage_bcs
        other = default_boundary_conditions(p.fem_mesh)
        with with_stage_water(p, None, other):
            assert p.seepage_bcs is other
            assert p.seepage_result is None
        assert p.seepage_result is before_result
        assert p.seepage_bcs is before_bcs

    def test_it_restores_even_when_the_body_raises(self):
        from ogr_slip2d.transient_stability import with_stage_water

        p, m = _dam_project(elements=800)
        _solve(p, m, RESERVOIR)
        saved = p.seepage_bcs
        try:
            with with_stage_water(p, None, default_boundary_conditions(
                    p.fem_mesh)):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert p.seepage_bcs is saved

    def test_a_drawdown_loses_the_weight_of_the_reservoir(self):
        """Swapping only the field keeps the emptied reservoir standing on
        the slope. The check is on the ponding, which is where that weight
        comes from, so it fails the moment the conditions stop travelling
        with the stage."""
        from ogr_slip2d.transient_stability import with_stage_water

        p, m = _dam_project(elements=1200)
        _solve(p, m, RESERVOIR)
        full = p.seepage_bcs
        assert ponded_water_level_at(p, 20.0) == pytest.approx(RESERVOIR,
                                                               abs=0.05)
        empty = default_boundary_conditions(p.fem_mesh)
        apply_reservoir(empty, p.fem_mesh, TAILWATER, SIDE_LEFT)
        with with_stage_water(p, p.seepage_result, empty):
            level = ponded_water_level_at(p, 20.0)
            assert level is None or level <= TAILWATER + 1e-6
        assert p.seepage_bcs is full


# ======================================================================
class TestRuleSeven:
    """Every control added here moves the number, and says where."""

    def test_the_suction_cutoff_moves_the_factor(self):
        p_free, _ = _steady(TAILWATER, 37.0)
        free = _fos(p_free, "b37_1500h")
        p_cut, _ = _steady(TAILWATER, 37.0, cutoff=20.0)
        capped = _fos(p_cut, "b37_1500h")
        assert capped < free, (capped, free)

    def test_the_cutoff_is_invisible_without_phi_b(self):
        """It caps the suction, and with phi_b = 0 the suction already
        contributes nothing. A control that moved the number here would
        be moving it for the wrong reason."""
        p_free, _ = _steady(TAILWATER, 0.0)
        p_cut, _ = _steady(TAILWATER, 0.0, cutoff=20.0)
        assert _fos(p_cut, "b0_1500h") == pytest.approx(
            _fos(p_free, "b0_1500h"), rel=1e-12)

    def test_the_cutoff_bites_through_the_air_entry_value_too(self):
        """"Invisible with phi_b = 0" is only true with an air entry
        value of zero as well, and saying otherwise was wrong.

        Below the air entry value the real negative pore pressure is
        KEPT and credited to the saturated friction angle, so a cap on it
        changes the effective stress even with no phi_b at all. Measured:
        a suction of 90 kPa with AEV = 50 reaches the strength as -50
        uncapped and as -20 with a cap of 20.
        """
        from ogr_slip2d.slicer import apply_unsaturated_policy

        m = Material(name="s", strength=MohrCoulomb(cohesion=1.0,
                                                    friction_angle=30.0))
        m.phi_b = 0.0
        m.air_entry_value = 50.0
        assert apply_unsaturated_policy(-90.0, m, None) == (-50.0, 0.0)
        assert apply_unsaturated_policy(-90.0, m, 20.0) == (-20.0, 0.0)
        # and with both at zero it really is invisible
        m.air_entry_value = 0.0
        assert (apply_unsaturated_policy(-90.0, m, None)
                == apply_unsaturated_policy(-90.0, m, 20.0))

    def test_the_sign_of_the_cutoff_does_not_change_its_meaning(self):
        from ogr_slip2d.slicer import apply_unsaturated_policy

        m = Material(name="s", strength=MohrCoulomb(cohesion=1.0,
                                                    friction_angle=30.0))
        m.phi_b = 20.0
        assert (apply_unsaturated_policy(-90.0, m, 30.0)
                == apply_unsaturated_policy(-90.0, m, -30.0))

    def test_the_reservoir_level_moves_the_factor(self):
        high, _ = _steady(RESERVOIR, 0.0)
        low, _ = _steady(TAILWATER, 0.0)
        assert _fos(high, "initial") < _fos(low, "initial")


# ======================================================================
class TestTheGuard:
    """A script must not be able to get a dry slope by accident."""

    def test_run_analysis_refuses_a_field_that_was_never_computed(self):
        from ogr_slip2d.analysis_runner import (
            AnalysisNotConfigured,
            run_analysis,
        )

        p, _m = _dam_project(elements=400)
        p.seepage_result = None
        with pytest.raises(AnalysisNotConfigured):
            run_analysis(p, ["bishop_simplified"])

    def test_the_escape_hatch_is_explicit(self):
        from ogr_slip2d.analysis_runner import run_analysis

        p, _m = _dam_project(elements=400)
        p.seepage_result = None
        out = run_analysis(p, ["bishop_simplified"],
                           allow_unconfigured=True)
        assert out is not None

    def test_a_configured_project_is_not_refused(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings

        p, m = _dam_project(elements=800)
        _solve(p, m, RESERVOIR)
        assert check_analysis_settings(p) == []


# ======================================================================
class TestTheProgrammaticDoor:
    """The chain used to exist only inside the interface."""

    def test_the_steady_solve_is_reachable_without_qt(self):
        from ogr_slip2d.transient_stability import solve_project_groundwater

        p, m = _dam_project(elements=800)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, RESERVOIR, SIDE_LEFT)
        p.seepage_bcs = bcs
        result = solve_project_groundwater(p)
        assert result.converged and result.pore_pressure
        assert p.seepage_result is result

    def test_it_uses_the_unsaturated_solver_and_not_the_linear_one(self):
        """The saturated door cannot produce suction; this one must."""
        from ogr_slip2d.transient_stability import solve_project_groundwater

        p, m = _dam_project(elements=800)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, RESERVOIR, SIDE_LEFT)
        p.seepage_bcs = bcs
        result = solve_project_groundwater(p)
        assert min(result.pore_pressure) < 0.0
        assert result.notes.get("unsettled_nodes") == 0

    def test_a_transient_history_becomes_a_factor_history(self):
        from ogr_slip2d.transient_stability import run_transient_stability

        p, m = _dam_project(elements=700)
        mesh = p.fem_mesh
        full = default_boundary_conditions(mesh)
        apply_reservoir(full, mesh, RESERVOIR, SIDE_LEFT)
        apply_reservoir(full, mesh, TAILWATER, SIDE_RIGHT)
        p.seepage_bcs = full
        empty = default_boundary_conditions(mesh)
        apply_reservoir(empty, mesh, TAILWATER, SIDE_LEFT)
        apply_reservoir(empty, mesh, TAILWATER, SIDE_RIGHT)

        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_initial_bcs = full.to_dict()
        gw.transient_time_steps = 2
        gw.transient_stages = [
            {"time": 1.0e5, "calculate_sf": True, "label": "drawdown",
             "bcs": empty.to_dict()},
            {"time": 1.0e8, "calculate_sf": True, "label": "drained",
             "bcs": empty.to_dict()},
        ]
        p.settings.search.grid_nx = 3
        p.settings.search.grid_ny = 3
        out = run_transient_stability(p, ["bishop_simplified"])
        assert len(out.stages) == 2
        series = out.series("bishop_simplified")
        assert len(series) == 2
        # Draining can only help: the classic drawdown recovery.
        assert series[1][1] > series[0][1]
        # And it is stored where the Interpret chart reads it.
        assert p.transient_results[0].notes["fos"]

    def test_the_initial_instant_can_have_a_factor_too(self):
        """A stage at t = 0 spans no time, and until v0.1.125 the flag
        that asks for its factor of safety did not survive that: the
        zero-span branch built its notes without ``calculate_sf``, so the
        one stage that ALWAYS has zero span — the initial instant — could
        be ticked and quietly produce nothing."""
        from ogr_slip2d.transient_stability import run_transient_stability

        p, m = _dam_project(elements=700)
        mesh = p.fem_mesh
        full = default_boundary_conditions(mesh)
        apply_reservoir(full, mesh, RESERVOIR, SIDE_LEFT)
        apply_reservoir(full, mesh, TAILWATER, SIDE_RIGHT)
        p.seepage_bcs = full
        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_initial_bcs = full.to_dict()
        gw.transient_time_steps = 2
        gw.transient_stages = [
            {"time": 0.0, "calculate_sf": True, "label": "t = 0"},
            {"time": 1.0e5, "calculate_sf": True, "label": "later",
             "bcs": full.to_dict()},
        ]
        p.settings.search.grid_nx = 3
        p.settings.search.grid_ny = 3
        out = run_transient_stability(p, ["bishop_simplified"])
        assert out.stages[0].result.notes["time_steps"] == 0
        assert out.stages[0].factors, "the initial instant produced nothing"

    def test_it_says_so_when_nothing_would_couple(self):
        from ogr_slip2d.transient_stability import run_transient_stability

        p, m = _dam_project(elements=700)
        m.pore_pressure = PorePressureType.NONE
        mesh = p.fem_mesh
        # A reservoir, so that the ONLY thing wrong is the coupling. The
        # default conditions prescribe no head anywhere, which makes the
        # steady problem singular and the field fail for a completely
        # different reason — and this test would then pass its warning
        # check while proving nothing about coupling.
        bcs = default_boundary_conditions(mesh)
        apply_reservoir(bcs, mesh, RESERVOIR, SIDE_LEFT)
        apply_reservoir(bcs, mesh, TAILWATER, SIDE_RIGHT)
        p.seepage_bcs = bcs
        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_initial_bcs = bcs.to_dict()
        gw.transient_time_steps = 2
        gw.transient_stages = [{"time": 1.0e5, "calculate_sf": True,
                                "bcs": bcs.to_dict()}]
        out = run_transient_stability(p, ["bishop_simplified"])
        assert not any("produced no field" in w for w in out.warnings),             out.warnings
        assert any("ignore the computed water pressures" in w
                   for w in out.warnings)
        # And on the STAGE, which is where the Interpret groundwater
        # window reads it and where it survives a save. Extracting this
        # driver out of the interface dropped that half, and the suite
        # caught it: a warning returned only to the caller is a warning
        # taken off the screen it was written for.
        assert any(r.notes.get("fos_warning")
                   for r in p.transient_results)

    def test_it_says_so_when_the_field_itself_failed(self):
        """Conditions that prescribe no head anywhere make the steady
        problem singular, and the solver says exactly that. The driver
        used to swallow it and hand back stages with no factors and no
        reason — which is how a test of something else spent an
        afternoon passing for the wrong reason."""
        from ogr_slip2d.transient_stability import run_transient_stability

        p, m = _dam_project(elements=500)
        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_stages = [{"time": 1.0, "calculate_sf": True}]
        out = run_transient_stability(p, ["bishop_simplified"])
        assert any("produced no field" in w for w in out.warnings),             out.warnings
        assert any("singular" in w for w in out.warnings)

    def test_it_says_so_when_there_are_no_stages(self):
        from ogr_slip2d.transient_stability import run_transient_stability

        p, _m = _dam_project(elements=400)
        out = run_transient_stability(p, ["bishop_simplified"])
        assert out.stages == []
        assert any("no transient groundwater stages" in w
                   for w in out.warnings)


# ======================================================================
class TestSerialisation:
    def test_the_cutoff_survives_a_round_trip(self):
        from ogr_core.project.settings import ProjectSettings

        s = ProjectSettings()
        s.groundwater.negative_pore_pressure_cutoff = 42.5
        back = ProjectSettings.from_dict(s.to_dict())
        assert back.groundwater.negative_pore_pressure_cutoff == 42.5

    def test_no_cutoff_is_the_default_and_survives(self):
        from ogr_core.project.settings import ProjectSettings

        s = ProjectSettings()
        assert s.groundwater.negative_pore_pressure_cutoff is None
        back = ProjectSettings.from_dict(s.to_dict())
        assert back.groundwater.negative_pore_pressure_cutoff is None


# ======================================================================
@_requires_qt
class TestTheInterface:
    def test_the_reservoir_target_is_offered_and_assigns(self):
        from ogr_gui.dialogs.boundary_conditions_dialog import (
            BoundaryConditionsDialog,
        )

        QApplication.instance() or QApplication([])
        p, _m = _dam_project(elements=800)
        mesh = p.fem_mesh
        bcs = default_boundary_conditions(mesh)
        dlg = BoundaryConditionsDialog(mesh, bcs)
        targets = [dlg.list_sides.item(i).data(32)
                   for i in range(dlg.list_sides.count())]
        assert "reservoir:left" in targets and "reservoir:right" in targets

        row = targets.index("reservoir:left")
        dlg.list_sides.setCurrentRow(row)
        dlg.sp_value.setValue(RESERVOIR)
        dlg._assign()
        heads = [b for b in bcs.nodes if b.bc_type == BCType.TOTAL_HEAD]
        assert heads
        assert all(b.value == pytest.approx(RESERVOIR) for b in heads)
        assert max(mesh.nodes[b.node_id].x for b in heads) <= 87.0 + 1e-6

    def test_a_level_that_reaches_nothing_says_so_and_does_not_assign(self):
        from ogr_gui.dialogs.boundary_conditions_dialog import (
            BoundaryConditionsDialog,
        )

        QApplication.instance() or QApplication([])
        p, _m = _dam_project(elements=800)
        bcs = default_boundary_conditions(p.fem_mesh)
        dlg = BoundaryConditionsDialog(p.fem_mesh, bcs)
        targets = [dlg.list_sides.item(i).data(32)
                   for i in range(dlg.list_sides.count())]
        dlg.list_sides.setCurrentRow(targets.index("reservoir:left"))
        dlg.sp_value.setValue(-50.0)
        dlg._assign()
        assert not [b for b in bcs.nodes
                    if b.bc_type == BCType.TOTAL_HEAD]
        assert "below that level" in dlg.lbl_summary.text().lower() or \
               "bajo esa cota" in dlg.lbl_summary.text().lower()

    def test_a_field_that_did_not_settle_is_reported_without_a_modal(self):
        """The message about a non-converged field goes to the status
        bar, never to a modal box.

        This path barely existed before v0.1.125, because the seepage
        face froze its nodes and called that convergence. Now that it
        reports honestly, it is easy to reach — and it used to end in
        ``QMessageBox.information``, which blocks for ever in any run
        without a screen. It was measured blocking: an automated run sat
        on it for an hour and fifty minutes with the process idle.
        """
        from ogr_gui.main_window import MainWindow

        QApplication.instance() or QApplication([])
        p, m = _dam_project(elements=700)
        _solve(p, m, RESERVOIR)
        # Force the report a starved switch budget would produce.
        p.seepage_result.converged = False
        p.seepage_result.notes["warning"] = "the seepage face never settled"

        w = MainWindow()
        w.canvas.set_project(p)
        w.project = p
        import ogr_slip2d.transient_stability as ts
        real = ts.solve_project_groundwater
        ts.solve_project_groundwater = lambda *a, **k: p.seepage_result
        try:
            w._compute_groundwater()          # must RETURN, not block
        finally:
            ts.solve_project_groundwater = real
        assert "never settled" in w.statusBar().currentMessage()

    def test_the_cutoff_is_editable_and_applies(self):
        from ogr_gui.dialogs.project_settings_dialog import _GroundwaterPage

        QApplication.instance() or QApplication([])
        p, _m = _dam_project(fem=False)
        page = _GroundwaterPage(p.settings)
        assert page.cb_ucut.isChecked() is False
        assert page.dsp_ucut.isEnabled() is False
        page.cb_ucut.setChecked(True)
        assert page.dsp_ucut.isEnabled() is True
        page.dsp_ucut.setValue(75.0)
        page.apply()
        assert p.settings.groundwater.negative_pore_pressure_cutoff == 75.0
        page.cb_ucut.setChecked(False)
        page.apply()
        assert p.settings.groundwater.negative_pore_pressure_cutoff is None
