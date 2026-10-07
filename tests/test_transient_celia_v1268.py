# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.268 (D191) — the transient solver against the infiltration problem
of Celia, Bouloutas & Zarba (1990), the paper its modified Picard
iteration comes from.

Why this test exists: the solver's docstring has cited Celia et al. since
v0.1.30, and the long prompts of D121 and D124 listed "the Celia et al.
1990 tests" among what could not move — but no such test existed. This is
it, with the van Genuchten retention the transient reads.

The case, Celia et al. (1990), data (13), Fig. 6: a 100 cm column of a
van Genuchten–Mualem soil (alpha = 0.0335 1/cm, theta_s = 0.368,
theta_r = 0.102, n = 2, m = 0.5, Ks = 0.00922 cm/s), initially at a
pressure head of -1000 cm, the base held there and the top raised to
-75 cm; the profile after one day.

What is checked:

* **The front, against the paper's dense-grid solution** (Fig. 6a,
  rasterized and digitized with the scan's skew corrected): the depth at
  which h crosses -200, -500 and -900 cm is 53.5, 56.6 and 57.4 cm. The
  tolerance, 1 cm, is the digitization's; OGR gives 53.5, 56.3 and
  57.7 cm with 1 cm elements and 12 min steps (measured).
* **The mass balance ratio is 1** — the change of stored water over the
  net inflow through the boundary. The paper's point is that the mixed
  form makes it "always unity"; the lumped-mass finite elements of this
  solver keep that identity, so it is checked to 1e-6.

The column is a strip one element wide, the material's kr floor lowered to
1e-12 so that kr at -10 m (3.4e-8) is not clipped by the default 1e-6, and
the relaxation is 1, so that the heads returned are those the reactions
were computed with.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.mesh.mesh import Element, Mesh, Node  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageBoundaryConditions,
    TransientSeepageSolver,
)

L = 1.0                  # m
DZ = 0.01                # m
DT = 12 * 60.0           # s
DAY = 86400.0
#: Celia et al. (1990) Fig. 6a, dense grid: depth [m] of h = -2, -5, -9 m.
DENSE_GRID = {-2.0: 0.535, -5.0: 0.566, -9.0: 0.574}
DIGITIZATION = 0.01      # m


def _run():
    rows = int(round(L / DZ))
    nodes = [Node(2 * j + k, k * DZ, j * DZ)
             for j in range(rows + 1) for k in (0, 1)]
    elements = []
    for j in range(rows):
        a, b, c, d = 2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2
        elements.append(Element(len(elements), (a, b, c), "m"))
        elements.append(Element(len(elements), (a, c, d), "m"))
    mesh = Mesh(nodes=nodes, elements=elements, target_size=DZ)
    soil = HydraulicProperties(
        ks=9.22e-5, model=PermeabilityModel.VAN_GENUCHTEN,
        vg_alpha=3.35, vg_n=2.0, wc_sat=0.368, wc_res=0.102,
        kr_min=1e-12, specific_storage=0.0)
    bcs = SeepageBoundaryConditions()
    for nid in (0, 1):
        bcs.add_node(nid, BCType.PRESSURE_HEAD, -10.0)
    top = (2 * rows, 2 * rows + 1)
    for nid in top:
        bcs.add_node(nid, BCType.PRESSURE_HEAD, -0.75)
    s = TransientSeepageSolver(mesh, {"m": soil}, gamma_w=9.81,
                               relaxation=1.0, tolerance=1e-7,
                               max_picard=300)
    H = [nd.y - 10.0 for nd in mesh.nodes]
    stored0 = s.stored_water(H)
    inflow = 0.0
    all_ok = True
    for _ in range(int(round(DAY / DT))):
        H, _act, ok, _it, r = s.step(bcs, H, DT, set())
        all_ok = all_ok and ok
        inflow += DT * sum(r.reactions[i] for i in (0, 1) + top)
    profile = sorted((L - nd.y, H[i] - nd.y)
                     for i, nd in enumerate(mesh.nodes) if nd.x == 0.0)
    return all_ok, profile, (s.stored_water(H) - stored0) / inflow


def _depth_of(profile, h):
    for (d0, h0), (d1, h1) in zip(profile, profile[1:]):
        if (h0 - h) * (h1 - h) <= 0.0 and h0 != h1:
            return d0 + (h - h0) * (d1 - d0) / (h1 - h0)
    return None


class TestCeliaInfiltration:
    _cache: dict = {}

    def _result(self):
        if "r" not in self._cache:
            self._cache["r"] = _run()
        return self._cache["r"]

    def test_every_step_converges(self):
        ok, _p, _mb = self._result()
        assert ok

    def test_the_front_is_where_the_dense_grid_puts_it(self):
        _ok, profile, _mb = self._result()
        for h, depth in DENSE_GRID.items():
            got = _depth_of(profile, h)
            assert got is not None, h
            assert abs(got - depth) <= DIGITIZATION, (h, got, depth)

    def test_the_mass_balance_ratio_is_one(self):
        _ok, _p, mb = self._result()
        assert abs(mb - 1.0) < 1e-6, mb
