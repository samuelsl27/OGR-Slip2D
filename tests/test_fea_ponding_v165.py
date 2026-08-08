# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
With a finite-element seepage analysis the reservoir is prescribed, not
drawn.

Until v0.1.65 the ponding load came only from a drawn water table or
drawdown line. Under a seepage analysis that is the wrong source: the
reservoir the solver was given lives in the boundary conditions, as a
total head applied to the boundary. There is standing water wherever that
head exceeds the elevation of the boundary it is applied to, and asking
the user to draw a water table on top of it would be a second, independent
statement of the same fact — free to disagree with the analysis actually
solved.

The anchor is an IDENTITY between two paths that must agree, not a
captured number: a boundary condition of total head H over a piece of
ground at elevation y must produce exactly the same vertical load and the
same horizontal thrust as a water table drawn at H over the same ground.
Both end up as ``γw · depth · dx``; if the two disagree, one of them is
wrong, and the drawn path is the one already validated (verification #70,
v0.1.61).

The other invariants:

  * without a seepage method selected the boundary conditions must be
    inert, so a project that also draws a water table is unaffected;
  * a total head BELOW the boundary elevation is a groundwater level, not
    a reservoir, and must pond nothing;
  * the three Dirichlet types have to agree on what "the head is" —
    ``pressure_head`` of 5 at y = 10 is the same reservoir as
    ``total_head`` of 15;
  * Neumann conditions and seepage faces prescribe no level at all.
"""
from __future__ import annotations

GAMMA_W = 9.81
GROUND_Y = 10.0


# ======================================================================
def _flat_project(method="fea_steady"):
    """A block whose top is flat at y = 10, so 'depth' is unambiguous."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, GROUND_Y), Vertex(0, GROUND_Y),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("fea")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=19,
                            strength=MohrCoulomb(cohesion=10,
                                                 friction_angle=25))]
    p.settings.groundwater.method = method
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


class _Node:
    """Minimal stand-in for ogr_fem2d.mesh.Node.

    A real mesh would work as well and cost a triangulation; the coupling
    is duck-typed on ``.x``/``.y`` precisely so ogr_core never has to
    import ogr_fem2d.
    """

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)


class _Mesh:
    def __init__(self, nodes):
        self.nodes = nodes


class _BC:
    def __init__(self, node_id, bc_type, value=0.0):
        self.node_id = node_id
        self.bc_type = bc_type      # plain string: compared by value
        self.value = float(value)


class _BCSet:
    def __init__(self, nodes):
        self.nodes = nodes


def _with_bcs(p, head, bc_type="total_head", xs=(0.0, 30.0, 60.0),
              node_y=GROUND_Y):
    """Apply ``head`` along the top boundary at the given abscissas."""
    p.fem_mesh = _Mesh([_Node(x, node_y) for x in xs])
    p.seepage_bcs = _BCSet([_BC(i, bc_type, head) for i in range(len(xs))])
    return p


def _water_table(p, y):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, y), Vertex(65, y)],
                          closed=False),
        btype=BoundaryType.WATER_TABLE))
    return p


def _slices(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    # A shallow arc well inside the block, so every slice has ground above
    # it at exactly GROUND_Y and the ponding depth is uniform.
    sl = slice_surface(p, SlipCircle(centre_x=30.0, centre_y=14.0,
                                     radius=8.0), num_slices=20)
    assert sl is not None
    return sl


def _water_load(p):
    """(Σ vertical water load, Σ horizontal water force) over the slices."""
    sl = _slices(p)
    return (sum(s.water_weight for s in sl.slices),
            sum(s.water_force_h for s in sl.slices))


# ======================================================================
class TestTheTwoPathsAgree:
    """The identity: a prescribed head and a drawn table are one thing."""

    def test_same_vertical_load_as_a_drawn_water_table(self):
        head = GROUND_Y + 4.0
        drawn = _water_table(_flat_project(method="none"), head)
        prescribed = _with_bcs(_flat_project(), head)
        v_drawn, _h_drawn = _water_load(drawn)
        v_pres, _h_pres = _water_load(prescribed)
        assert v_drawn > 0.0
        assert abs(v_pres - v_drawn) < 1e-9, (v_pres, v_drawn)

    def test_same_horizontal_thrust_as_a_drawn_water_table(self):
        head = GROUND_Y + 4.0
        drawn = _water_table(_flat_project(method="none"), head)
        prescribed = _with_bcs(_flat_project(), head)
        _v1, h_drawn = _water_load(drawn)
        _v2, h_pres = _water_load(prescribed)
        assert abs(h_pres - h_drawn) < 1e-9

    def test_the_load_is_the_weight_of_the_water_column(self):
        """Closed form, so the identity above cannot be two equal wrongs:
        Σ W_water = γw · depth · (total width of the slices)."""
        depth = 4.0
        p = _with_bcs(_flat_project(), GROUND_Y + depth)
        sl = _slices(p)
        width = sum(s.width for s in sl.slices)
        expected = GAMMA_W * depth * width
        got = sum(s.water_weight for s in sl.slices)
        assert abs(got - expected) / expected < 1e-9, (got, expected)


class TestTheThreeDirichletTypesAgree:
    """They are three ways of writing the same reservoir."""

    def test_pressure_head_matches_the_equivalent_total_head(self):
        total = _with_bcs(_flat_project(), GROUND_Y + 5.0,
                          bc_type="total_head")
        press = _with_bcs(_flat_project(), 5.0, bc_type="pressure_head")
        assert abs(_water_load(total)[0] - _water_load(press)[0]) < 1e-9

    def test_zero_pressure_ponds_nothing(self):
        """H = y exactly: the water surface is AT the boundary, so there
        is no column standing on it."""
        p = _with_bcs(_flat_project(), 0.0, bc_type="zero_pressure")
        assert _water_load(p)[0] == 0.0


class TestWhatMustNotPond:
    def test_a_head_below_the_boundary_is_not_a_reservoir(self):
        p = _with_bcs(_flat_project(), GROUND_Y - 3.0)
        assert _water_load(p)[0] == 0.0

    def test_neumann_conditions_prescribe_no_level(self):
        for t in ("nodal_flow", "infiltration", "unknown"):
            p = _with_bcs(_flat_project(), GROUND_Y + 5.0, bc_type=t)
            assert _water_load(p)[0] == 0.0, t

    def test_without_a_seepage_method_the_conditions_are_inert(self):
        """The conditions can outlive a change of method; they must not
        act unless the analysis that owns them is the one selected."""
        p = _with_bcs(_flat_project(method="water_table"), GROUND_Y + 5.0)
        assert _water_load(p)[0] == 0.0

    def test_no_mesh_means_no_prescribed_reservoir(self):
        p = _flat_project()
        p.seepage_bcs = _BCSet([_BC(0, "total_head", GROUND_Y + 5.0)])
        p.fem_mesh = None
        assert _water_load(p)[0] == 0.0


class TestItCombinesWithADrawnSurface:
    def test_the_higher_of_the_two_wins(self):
        """Same rule the drawn surfaces already follow among themselves,
        so a project that had ponding keeps it."""
        p = _with_bcs(_water_table(_flat_project(), GROUND_Y + 2.0),
                      GROUND_Y + 6.0)
        deep = _with_bcs(_flat_project(), GROUND_Y + 6.0)
        assert abs(_water_load(p)[0] - _water_load(deep)[0]) < 1e-9

    def test_a_higher_drawn_table_still_wins(self):
        p = _with_bcs(_water_table(_flat_project(), GROUND_Y + 6.0),
                      GROUND_Y + 2.0)
        deep = _water_table(_flat_project(method="none"), GROUND_Y + 6.0)
        assert abs(_water_load(p)[0] - _water_load(deep)[0]) < 1e-9


class TestTheCanvasDrawsIt:
    """A load the user cannot see is a load the user cannot check.

    The canvas walked the ponding BOUNDARY polylines, so a reservoir that
    exists only in the boundary conditions would have loaded the slope
    invisibly — the exact shape of failure rule 7 is about.
    """

    def test_the_prescribed_reservoir_produces_pond_items(self):
        from PySide6.QtWidgets import QApplication, QGraphicsScene
        from ogr_gui.canvas.canvas_view import CanvasView

        QApplication.instance() or QApplication([])
        p = _with_bcs(_flat_project(), GROUND_Y + 4.0)
        view = CanvasView()
        view.project = p
        scene = QGraphicsScene()
        before = len(scene.items())
        view._draw_ponded_water(scene, view.display_options)
        assert len(scene.items()) > before

    def test_nothing_is_drawn_without_a_reservoir(self):
        from PySide6.QtWidgets import QApplication, QGraphicsScene
        from ogr_gui.canvas.canvas_view import CanvasView

        QApplication.instance() or QApplication([])
        p = _with_bcs(_flat_project(), GROUND_Y - 4.0)   # below the ground
        view = CanvasView()
        view.project = p
        scene = QGraphicsScene()
        before = len(scene.items())
        view._draw_ponded_water(scene, view.display_options)
        assert len(scene.items()) == before


class TestVaryingHead:
    def test_the_level_is_interpolated_between_wet_nodes(self):
        """A linearly varied total head gives a sloping water surface."""
        from ogr_core.hydraulic.ponded_water import ponded_water_level_at
        p = _flat_project()
        p.fem_mesh = _Mesh([_Node(0.0, GROUND_Y), _Node(60.0, GROUND_Y)])
        p.seepage_bcs = _BCSet([_BC(0, "total_head", GROUND_Y + 10.0),
                                _BC(1, "total_head", GROUND_Y + 20.0)])
        # Halfway along, exactly halfway between the two heads.
        assert abs(ponded_water_level_at(p, 30.0)
                   - (GROUND_Y + 15.0)) < 1e-9
        assert abs(ponded_water_level_at(p, 0.0)
                   - (GROUND_Y + 10.0)) < 1e-9

    def test_outside_the_wet_nodes_the_level_is_held(self):
        from ogr_core.hydraulic.ponded_water import ponded_water_level_at
        p = _with_bcs(_flat_project(), GROUND_Y + 5.0, xs=(20.0, 40.0))
        assert abs(ponded_water_level_at(p, 0.0)
                   - (GROUND_Y + 5.0)) < 1e-9
