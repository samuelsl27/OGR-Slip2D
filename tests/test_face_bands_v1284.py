# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.284 (D280) — the hysteresis bands of the seepage-face switching are
ten times narrower, so the converged face no longer depends on the
relaxation.

The defect: a free node is held at P = 0 only when its pressure exceeds
``p_tol`` and a held node is released only when its inflow exceeds
``q_tol``. With p_tol = 0.02 h and q_tol = 1e-3 of the largest nodal flux,
more than one face set satisfied both, and w or the path (loop or rescue)
picked one: 4 of the 53 unsaturated steady rows of the verification bank
landed 1 to 24 mm apart at another w (D266). The case here is the first of
them, rain on a block between two rivers (Harr 1990; groundwater manual 05,
problem 1, on its 225-element mesh): with w = 0.2 the node of the right
bank just above the river is on the face, with w >= 0.4 it is left free
with a positive pressure below 0.02 h, and the heads differ by 1 cm.

What these tests protect:

* the bands are 0.002 h and 1e-4 of the largest nodal flux of the first
  solve; an explicit ``switch_pressure_tol`` is still honoured;
* with them the block gives one face for w = 0.2, 0.4 and 0.8, and heads
  within two tolerances of each other — a converged fixed point does not
  depend on the relaxation that reached it (the reference is that identity,
  not a snapshot: rule 1);
* every transient step uses the same bands (one rule since D269);
* switched off, the old bands and the w-dependent face come back (rule 7).

Charnyi's discharge through the rectangular dam, the external anchor of
the face (``test_unsaturated_v127``), is unchanged by the narrow bands
(1.772 % before and after, ``_auditoria/P6_0284`` of the bank). The switch
is restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_core.geometry.regions import MaterialRegion  # noqa: E402
from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.mesh import generate_mesh  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    TransientSeepageSolver,
    TransientStage,
    UnsaturatedSeepageSolver,
)

# Harr (1990), as in groundwater manual 05, problem 1: a 10 x 5 m block,
# rivers at 3.75 and 3.0 m, rain 2.5e-6 m/s on the crest, k = 1e-5 m/s.
L, H, H1, H2, RAIN, K = 10.0, 5.0, 3.75, 3.0, 2.5e-6, 1.0e-5
TOL = 1e-6
_CACHE: dict = {}


def _block():
    if "block" not in _CACHE:
        poly = Polyline(vertices=[Vertex(0, 0), Vertex(L, 0), Vertex(L, H),
                                  Vertex(0, H)], closed=True)
        mesh = generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                             target_elements=225)
        props = {"m": HydraulicProperties(ks=K,
                                          model=PermeabilityModel.SIMPLE)}
        _CACHE["block"] = mesh, props
    return _CACHE["block"]


def _bcs(h2=H2):
    """Both banks a potential seepage face above their river; rain on the
    crest."""
    mesh, _ = _block()
    eps = 1e-6 * L
    b = SeepageBoundaryConditions()
    ids = sorted(mesh.boundary_node_ids())
    for nid in ids:
        nd = mesh.nodes[nid]
        for x, h in ((0.0, H1), (L, h2)):
            if abs(nd.x - x) < eps:
                if nd.y <= h + eps:
                    b.add_node(nid, BCType.TOTAL_HEAD, h)
                else:
                    b.add_node(nid, BCType.UNKNOWN)
    crest = sorted((i for i in ids if abs(mesh.nodes[i].y - H) < eps),
                   key=lambda i: mesh.nodes[i].x)
    for a, c in zip(crest, crest[1:]):
        b.add_segment(a, c, RAIN)
    return b


def _solve(w, tight=True):
    key = (w, tight)
    if key not in _CACHE:
        mesh, props = _block()
        old = seepage.FACE_BANDS_TIGHT
        try:
            seepage.FACE_BANDS_TIGHT = tight
            _CACHE[key] = UnsaturatedSeepageSolver(
                mesh, props, relaxation=w, max_iterations=400,
                tolerance=TOL).solve_unsaturated(_bcs())
        finally:
            seepage.FACE_BANDS_TIGHT = old
    return _CACHE[key]


def _max_dh(a, b):
    return max(abs(x - y) for x, y in zip(a.total_head, b.total_head))


class TestTheBands:
    def test_they_are_a_tenth_of_the_old_ones(self):
        mesh, props = _block()
        s = UnsaturatedSeepageSolver(mesh, props)
        h = mesh.target_size
        assert abs(s._face_p_tol() - 0.002 * h) < 1e-15
        assert abs(s._face_q_tol(3.0) - 3e-4) < 1e-18
        assert s._face_q_tol(0.0) == 1e-14

    def test_an_explicit_pressure_band_is_honoured(self):
        mesh, props = _block()
        s = UnsaturatedSeepageSolver(mesh, props, switch_pressure_tol=0.05)
        assert s._face_p_tol() == 0.05

    def test_switched_off_they_are_the_old_ones(self):
        mesh, props = _block()
        s = UnsaturatedSeepageSolver(mesh, props)
        old = seepage.FACE_BANDS_TIGHT
        try:
            seepage.FACE_BANDS_TIGHT = False
            assert abs(s._face_p_tol() - 0.02 * mesh.target_size) < 1e-15
            assert abs(s._face_q_tol(3.0) - 3e-3) < 1e-18
        finally:
            seepage.FACE_BANDS_TIGHT = old


class TestOneFaceForEveryW:
    def test_the_block_has_the_manuals_mesh(self):
        mesh, _ = _block()
        assert len(mesh.elements) == 230 and mesh.node_count == 137

    def test_the_face_and_the_heads_do_not_depend_on_w(self):
        ref = _solve(0.4)
        assert ref.converged and ref.seepage_nodes
        for w in (0.2, 0.8):
            r = _solve(w)
            assert r.converged, w
            assert sorted(r.seepage_nodes) == sorted(ref.seepage_nodes), w
            assert _max_dh(r, ref) < 2 * TOL, (w, _max_dh(r, ref))

    def test_switched_off_the_face_depends_on_w(self):
        a, b = _solve(0.2, tight=False), _solve(0.4, tight=False)
        assert a.converged and b.converged
        assert sorted(a.seepage_nodes or []) != sorted(b.seepage_nodes or [])
        assert _max_dh(a, b) > 5e-3

    def test_the_old_band_left_a_wet_node_free(self):
        """What the narrow band removes: with w = 0.4 the old bands leave
        free the bank node the narrow ones hold, at a positive pressure
        above the new band and below the old one."""
        mesh, _ = _block()
        held = set(_solve(0.4).seepage_nodes)
        old = _solve(0.4, tight=False)
        h = mesh.target_size
        wet = [n for n in held - set(old.seepage_nodes or [])
               if 0.002 * h < old.total_head[n] - mesh.nodes[n].y < 0.02 * h]
        assert wet, held


class TestTheTransientStep:
    def _bands_seen(self, tight):
        mesh, props = _block()
        seen = []

        class Spy(TransientSeepageSolver):
            def _switch_seepage_face(self, active, switches, unknown, H,
                                     reactions, p_tol, q_tol):
                seen.append((p_tol, q_tol))
                return super()._switch_seepage_face(
                    active, switches, unknown, H, reactions, p_tol, q_tol)

        old = seepage.FACE_BANDS_TIGHT
        try:
            seepage.FACE_BANDS_TIGHT = tight
            s = Spy(mesh, props, relaxation=0.5, tolerance=TOL,
                    time_steps=2, max_picard=60)
            s.solve_transient([TransientStage(time=3600.0, bcs=_bcs(2.8))],
                              initial_bcs=_bcs())
        finally:
            seepage.FACE_BANDS_TIGHT = old
        return seen, mesh.target_size

    def test_uses_the_same_bands(self):
        first = {}
        for tight, fp in ((True, 0.002), (False, 0.02)):
            seen, h = self._bands_seen(tight)
            assert seen, tight
            assert {p for p, _ in seen} == {fp * h}, tight
            first[tight] = seen[0][1]
        # the first band of the run comes from the same linear solve in
        # both, so it is exactly a tenth
        assert abs(first[True] / first[False] - 0.1) < 1e-12
