# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.342 (D337, third part) — the finite-element data the project stores
is the core's.

``Project.from_dict`` rebuilt the mesh, the seepage boundary conditions and
the seepage results by importing them from ``ogr_fem2d``: three of the
twenty imports of the engine D337 counted in the core. They are data and
the closed-form identities that rebuild a result's derived fields, so they
moved, whole, to ``ogr_core.fem``, and ``ogr_fem2d`` re-exports them.

The invariants:

* **one class, at both paths**: every name imported from its old place
  (``ogr_fem2d.mesh``, ``ogr_fem2d.mesh.mesh``, ``ogr_fem2d.solvers``,
  ``ogr_fem2d.solvers.seepage``) is the very object of ``ogr_core.fem``, so
  ``isinstance`` and every existing import keep working;
* **the solver's fluxes are the core's function**: on a solved unsaturated
  field, ``SeepageSolver._element_fluxes`` and ``element_fluxes`` give the
  same numbers, exactly, and so does the field the solver produced;
* **a model with a mesh, a seepage field and transient stages loads without
  the engine**: in a fresh interpreter ``Project.load`` brings neither
  ``ogr_fem2d`` nor ``ogr_slip2d`` into ``sys.modules``, and the velocities
  it rebuilds are the solver's own fluxes over the saved heads and kr,
  digit for digit. (Not the field in memory: the file keeps nine
  significant figures, by design, and measured on this field that moves a
  velocity by up to 5.8e-7 relative, in v0.1.341 exactly as now.)
* a pickled mesh and a pickled result come back as the same classes (the
  analysis jobs travel to a subprocess by pickle);
* the census of ``test_core_layering_v1340`` loses the loader's three
  imports of ``ogr_fem2d``.
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_CACHE: dict = {}


def _project():
    """A small unsaturated seepage field on the Ej_1 slope, solved once."""
    if "p" not in _CACHE:
        from test_coupling_v128 import _seepage_project
        _CACHE["p"] = _seepage_project(elements=300)
    return _CACHE["p"]


# ======================================================================
class TestOneClassAtBothPaths:

    def test_every_old_name_is_the_core_object(self):
        import ogr_core.fem as core
        import ogr_fem2d.mesh as mesh_pkg
        import ogr_fem2d.mesh.mesh as mesh_mod
        import ogr_fem2d.solvers as solvers_pkg
        import ogr_fem2d.solvers.seepage as seepage_mod
        for name in ("Mesh", "Node", "Element"):
            assert getattr(mesh_pkg, name) is getattr(core, name), name
            assert getattr(mesh_mod, name) is getattr(core, name), name
        for name in ("DEGENERATE_SHAPE_RATIO", "triangle_shape_ratio"):
            assert getattr(mesh_mod, name) is getattr(core, name), name
        for name in ("BCType", "NodeBC", "SegmentBC",
                     "SeepageBoundaryConditions", "SeepageResult",
                     "hydraulic_props_of", "restore_derived"):
            assert getattr(solvers_pkg, name) is getattr(core, name), name
            assert getattr(seepage_mod, name) is getattr(core, name), name
        assert seepage_mod.element_fluxes is core.element_fluxes
        assert core.Mesh.__module__ == "ogr_core.fem.mesh"
        assert core.SeepageResult.__module__ == "ogr_core.fem.seepage_data"

    def test_a_pickled_mesh_and_result_come_back_as_the_same_classes(self):
        import ogr_core.fem as core
        p = _project()
        mesh = pickle.loads(pickle.dumps(p.fem_mesh))
        res = pickle.loads(pickle.dumps(p.seepage_result))
        assert type(mesh) is core.Mesh and type(res) is core.SeepageResult
        assert res.total_head == p.seepage_result.total_head


# ======================================================================
class TestTheSolversFluxesAreTheCoresFunction:

    def test_same_numbers_exactly(self):
        from ogr_core.fem import element_fluxes, hydraulic_props_of
        from ogr_fem2d.solvers import SeepageSolver
        p = _project()
        r = p.seepage_result
        assert r.velocity and r.kr is not None
        solver = SeepageSolver(p.fem_mesh, hydraulic_props_of(p))
        via_solver = solver._element_fluxes(r.total_head, r.kr)
        via_core = element_fluxes(p.fem_mesh, solver.props_for,
                                  r.total_head, r.kr)
        assert via_solver == via_core
        assert via_core[0] == r.velocity


# ======================================================================
class TestAModelLoadsWithoutTheEngine:

    def test_in_a_fresh_interpreter(self):
        p = _project()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_fem_"))
        path = tmp / "seepage.ogr"
        saved = list(p.transient_results)
        try:
            p.transient_results = [p.seepage_result, p.seepage_result]
            p.save(path)
        finally:
            p.transient_results = saved
        script = (
            "import json, sys\n"
            "from ogr_core.project import Project\n"
            "q = Project.load(sys.argv[1])\n"
            "print(json.dumps({\n"
            "    'engine': sorted(m for m in sys.modules\n"
            "                     if m.split('.')[0] in ('ogr_fem2d', 'ogr_slip2d')),\n"
            "    'velocity': [list(v) for v in q.seepage_result.velocity],\n"
            "    'stages': [[list(v) for v in r.velocity]\n"
            "               for r in q.transient_results],\n"
            "    'mesh': type(q.fem_mesh).__module__}))\n")
        env = dict(os.environ, PYTHONPATH=str(_ROOT),
                   QT_QPA_PLATFORM="offscreen")
        try:
            out = subprocess.run([sys.executable, "-c", script, str(path)],
                                 cwd=str(_ROOT), env=env,
                                 capture_output=True, text=True, timeout=300)
            from ogr_core.project import Project
            here = Project.load(path)
        finally:
            path.unlink(missing_ok=True)
            tmp.rmdir()
        assert out.returncode == 0, out.stderr
        got = json.loads(out.stdout)
        assert got["engine"] == [], got["engine"]
        assert got["mesh"] == "ogr_core.fem.mesh"
        # the solver's own fluxes over what was SAVED: the heads and kr go to
        # nine significant figures (``SeepageResult._round``), so this, and
        # not the field in memory, is what a load can give back exactly
        from ogr_core.fem import hydraulic_props_of
        from ogr_fem2d.solvers import SeepageSolver
        r = here.seepage_result
        solver = SeepageSolver(here.fem_mesh, hydraulic_props_of(here))
        expected = [list(v) for v in
                    solver._element_fluxes(r.total_head, r.kr)[0]]
        assert got["velocity"] == expected
        assert got["stages"] == [expected, expected]


# ======================================================================
class TestTheCensusLosesTheLoadersFemImports:

    def test_no_entry_for_ogr_fem2d_in_the_loader(self):
        import test_core_layering_v1340 as L
        found = L.census_of(_ROOT / "ogr_core" / "project" / "project.py",
                            _ROOT)
        assert not any(k[2] == "ogr_fem2d" for k in found), found
        assert not any(k[0] == "ogr_core/project/project.py"
                       and k[2] == "ogr_fem2d" for k in L.ALLOWED)
