# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.267 (D190) — the Simple permeability model is a declared OGR
convention, and the solver applies exactly the convention declared.

What this protects, and what it does NOT
----------------------------------------
The reference describes its Simple model only in words and publishes no
function, and no verification case of the groundwater bank tells one
reading of it from another (measured in v0.1.267: the mesh moves those
answers as much as the reading does). So no test here can say the curve is
the reference's. What a test CAN pin down is that the curve OGR declares
(``permeability_models.kr_simple``: kr = 10^(-d min(1, psi/psi_ref)), psi in
kPa, the pairs of ``_SIMPLE_PARAMS``, no Ks) is the one the solver uses —
so that a change of a pair, of the suction unit (D121) or a dependence on
Ks cannot slip in unannounced.

The external anchor is Gardner's (1958) closed form for steady
infiltration through a column over a water table. Below psi_ref the
convention IS Gardner's exponential, k = Ks exp(-a h) with h the suction
head and

    a = d ln(10) gamma_w / psi_ref    [1/m],

and with a downward flux q = r Ks the pressure head is

    P(z) = (1/a) ln[ r + (1 - r) exp(-a z) ],

valid while the deepest suction stays below psi_ref (r > 10^-d). Each soil
type gets its own column, in units of its own decay length 1/a, so every
one is resolved alike (a dz = 0.05) and every one reaches its far-field
value. The readings this tells apart: suction in metres instead of kPa (a
9.81 times smaller), a range scaled with Ks, or a changed pair, all move P
by far more than the tolerance.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import (  # noqa: E402
    HydraulicProperties,
    PermeabilityModel,
    SimpleSoilType,
)
from ogr_fem2d.mesh.mesh import Element, Mesh, Node  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    UnsaturatedSeepageSolver,
)

GAMMA_W = 9.81
KS = 1.0e-5
#: The declared convention: (psi_ref kPa, decades). Written out here on
#: purpose — the test reads the documented numbers, not the module's dict,
#: so a silent change of the dict fails it.
CONVENTION = {
    SimpleSoilType.GENERAL: (100.0, 1.0),
    SimpleSoilType.SAND: (10.0, 4.0),
    SimpleSoilType.SILT: (50.0, 3.0),
    SimpleSoilType.LOAM: (100.0, 3.0),
    SimpleSoilType.CLAY: (1500.0, 2.0),
}
#: Infiltration ratio per type, inside each one's exponential range.
RATIO = {
    SimpleSoilType.GENERAL: 0.5,
    SimpleSoilType.SAND: 0.01,
    SimpleSoilType.SILT: 0.01,
    SimpleSoilType.LOAM: 0.01,
    SimpleSoilType.CLAY: 0.5,
}


def _a(soil):
    psi_ref, d = CONVENTION[soil]
    return d * math.log(10.0) * GAMMA_W / psi_ref


def _closed_form(soil, z):
    a, r = _a(soil), RATIO[soil]
    return math.log(r + (1.0 - r) * math.exp(-a * z)) / a


def _column(soil, ks=KS):
    a = _a(soil)
    dz = 0.05 / a
    rows = 160                       # 8 decay lengths
    width = dz
    nodes = []
    for j in range(rows + 1):
        nodes.append(Node(2 * j, 0.0, j * dz))
        nodes.append(Node(2 * j + 1, width, j * dz))
    elements = []
    for j in range(rows):
        p0, p1, p2, p3 = 2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2
        elements.append(Element(len(elements), (p0, p1, p2), "m"))
        elements.append(Element(len(elements), (p0, p2, p3), "m"))
    mesh = Mesh(nodes=nodes, elements=elements, target_size=dz)
    props = {"m": HydraulicProperties(ks=ks, model=PermeabilityModel.SIMPLE,
                                      simple_soil_type=soil)}
    bcs = SeepageBoundaryConditions()
    bcs.add_node(0, BCType.TOTAL_HEAD, 0.0)
    bcs.add_node(1, BCType.TOTAL_HEAD, 0.0)
    bcs.add_segment(2 * rows, 2 * rows + 1, RATIO[soil] * ks)
    s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W,
                                 relaxation=0.5, max_iterations=400,
                                 tolerance=1e-9)
    return mesh, s.solve_unsaturated(bcs)


def _worst(soil, ks=KS):
    mesh, r = _column(soil, ks)
    assert r.converged, (soil, r.notes)
    p_far = abs(math.log(RATIO[soil]) / _a(soil))
    return max(abs(r.total_head[i] - mesh.nodes[i].y
                   - _closed_form(soil, mesh.nodes[i].y))
               for i in range(mesh.node_count)) / p_far


class TestTheConventionIsWhatTheSolverUses:
    """The FE column against Gardner's closed form, per soil type, to
    0.5 % of the far-field pressure head."""

    def test_general(self):
        assert _worst(SimpleSoilType.GENERAL) < 5e-3

    def test_sand(self):
        assert _worst(SimpleSoilType.SAND) < 5e-3

    def test_silt(self):
        assert _worst(SimpleSoilType.SILT) < 5e-3

    def test_loam(self):
        assert _worst(SimpleSoilType.LOAM) < 5e-3

    def test_clay(self):
        assert _worst(SimpleSoilType.CLAY) < 5e-3


class TestWhatTheConventionDoesNotDo:
    def test_ks_does_not_shape_the_curve(self):
        """The reference says its curve depends on the magnitude of Ks;
        OGR's does not, and says so. Same profile for Ks a million times
        apart (the flux scales with Ks, so the heads are identical)."""
        m1, r1 = _column(SimpleSoilType.GENERAL, ks=1.0e-3)
        m2, r2 = _column(SimpleSoilType.GENERAL, ks=1.0e-9)
        assert r1.converged and r2.converged
        d = max(abs(a - b) for a, b in zip(r1.total_head, r2.total_head))
        assert d < 1e-6, d

    def test_the_suction_is_read_in_kpa(self):
        """With the suction read in metres (the bug of D121) the far field
        would sit 9.81 times deeper; the column says kPa."""
        mesh, r = _column(SimpleSoilType.GENERAL)
        top = max(range(mesh.node_count), key=lambda i: mesh.nodes[i].y)
        p_top = r.total_head[top] - mesh.nodes[top].y
        kpa = math.log(RATIO[SimpleSoilType.GENERAL]) / _a(SimpleSoilType.GENERAL)
        assert abs(p_top / kpa - 1.0) < 0.01, (p_top, kpa)
