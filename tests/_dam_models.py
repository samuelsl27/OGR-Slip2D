# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.473 (spec 010) — the two seepage dams that six tests of this suite
build their cases on, kept here now that the tests they came from live in
OGR-Core.

``test_unsaturated_v127`` and ``test_rescue_face_v1356`` moved to OGR-Core
with the seepage solver, and six tests that stay (``test_picard_history_v1269``,
``test_transient_initial_state_v1270``, ``test_user_curve_dialog_v1275``,
``test_retention_alpha_v1278``, ``test_picard_loop_face_v1358``,
``test_rescue_fold_v1362``) loaded them by path for their dams. What they take
is copied here unchanged, value for value: only the imports point at
``ogr_core.fem``, as they did in those two files since this version. This
duplicates the building of two models, not any test: the tests of the dams
themselves (the Charnyi/Dupuit convergence, the rescue of the face) run in
OGR-Core.

Not a test file: the runner collects ``test_*.py`` only.
"""
from __future__ import annotations

from ogr_core.fem.generator import generate_mesh
from ogr_core.fem.seepage import BCType, SeepageBoundaryConditions
from ogr_core.geometry import Polyline, Vertex
from ogr_core.geometry.regions import MaterialRegion
from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel


# ======================================================================
# The rectangular dam on an impervious base (from test_unsaturated_v127)
# ======================================================================
L_DAM, H_DAM, K_DAM = 20.0, 12.0, 1.0e-5
H1, H2 = 10.0, 2.0


def _dam_mesh(h=0.6):
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(L_DAM, 0),
                              Vertex(L_DAM, H_DAM), Vertex(0, H_DAM)],
                    closed=True)
    return generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=h)


def _dam_bcs(mesh):
    """Upstream head H1, downstream head H2, impervious base, and
    Unknown (potential seepage face) on the crest and above the water
    levels on both faces."""
    b = SeepageBoundaryConditions()
    for nid in sorted(mesh.boundary_node_ids()):
        nd = mesh.nodes[nid]
        if abs(nd.x) < 1e-9:
            if nd.y <= H1 + 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, H1)
            else:
                b.add_node(nid, BCType.UNKNOWN)
        elif abs(nd.x - L_DAM) < 1e-9:
            if nd.y <= H2 + 1e-9:
                b.add_node(nid, BCType.TOTAL_HEAD, H2)
            else:
                b.add_node(nid, BCType.UNKNOWN)
        elif abs(nd.y - H_DAM) < 1e-9:
            b.add_node(nid, BCType.UNKNOWN)
        else:
            b.add_node(nid, BCType.NODAL_FLOW, 0.0)
    return b


# ======================================================================
# The toe-drain dam (from test_rescue_face_v1356)
# ======================================================================
GAMMA_W = 9.81
KS = 1.0e-5
#: six decades over 0.5 kPa (kPa, as every user curve since v0.1.200)
CURVE = [(0.0, KS), (0.5, KS * 1.0e-6)]
FOCUS = (22.0, 0.0)
OUTLINE = [(0.0, 0.0), FOCUS, (23.5, 1.5), (12.5, 5.0), (10.0, 5.0)]
HEAD = 4.0
W, TOL = 0.4, 1.0e-6
ELEMENTS, T3 = 2400, 2307


def _project():
    from shapely.geometry import Polygon

    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    p = Project("toe-drain dam")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in OUTLINE], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="Dam", unit_weight=20.0, sat_unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(
        ks=KS, model=PermeabilityModel.USER_DEFINED, user_curve=list(CURVE))
    p.materials = [m]
    for reg in p.resolve_regions():
        pt = Polygon([(v.x, v.y) for v in reg.polygon.vertices]
                     ).representative_point()
        p.assign_material_at(pt.x, pt.y, m.id)
    return p


def _bcs(mesh):
    """Head 4 on the upstream face up to y = 4 and 0 at the focus; the
    upstream face above the water, the crest, the downstream slope and the
    drain face free to seep; the base impervious."""
    b = SeepageBoundaryConditions()
    for i in mesh.boundary_node_ids():
        x, y = mesh.nodes[i].x, mesh.nodes[i].y
        if abs(x - FOCUS[0]) < 1e-6 and abs(y - FOCUS[1]) < 1e-6:
            b.add_node(i, BCType.TOTAL_HEAD, 0.0)
        elif x <= 10.0 + 1e-6 and abs(y - 0.5 * x) < 1e-4:
            if y <= HEAD + 1e-6:
                b.add_node(i, BCType.TOTAL_HEAD, HEAD)
            else:
                b.add_node(i, BCType.UNKNOWN)
        elif abs(y) < 1e-9:
            continue
        else:
            b.add_node(i, BCType.UNKNOWN)
    return b


_CACHE: dict = {}


def _case():
    if "case" not in _CACHE:
        from ogr_core.fem.generator import generate_mesh_for_project
        p = _project()
        mesh = generate_mesh_for_project(p, target_elements=ELEMENTS)
        props = {m.id: m.hydraulic for m in p.materials}
        _CACHE["case"] = (mesh, props, _bcs(mesh))
    return _CACHE["case"]
