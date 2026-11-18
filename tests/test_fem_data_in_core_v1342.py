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

Spec 009 (F1) — the solvers followed the data. The mesh generator, the
seepage solvers, the streamlines and the ``seepage.*`` codes moved from
``ogr_fem2d`` to ``ogr_core.fem`` too, and ``ogr_fem2d`` left this
repository: its name is the finite-element program's (OGR FEM2D), and a
re-export left behind under it would keep that name taken. So "one class,
at both paths" became one class at ONE path.

The invariants:

* **one class, at one path**: there is no ``ogr_fem2d`` in this tree; the
  data classes are ``ogr_core.fem``'s, and the names the solver module
  re-exports are the very same objects, so ``isinstance`` holds wherever a
  name is imported from;
* **the solver's fluxes are the core's function**: on a solved unsaturated
  field, ``SeepageSolver._element_fluxes`` and ``element_fluxes`` give the
  same numbers, exactly, and so does the field the solver produced;
* **a model with a mesh, a seepage field and transient stages loads without
  the solver**: in a fresh interpreter ``Project.load`` brings neither the
  solver (``ogr_core.fem.seepage``) nor the mesh generator
  (``ogr_core.fem.generator``) nor ``ogr_slip2d`` into ``sys.modules`` —
  nor ``ogr_fem2d``, which the core must never import — and the velocities
  it rebuilds are the solver's own fluxes over the saved heads and kr,
  digit for digit. (Not the field in memory: the file keeps nine
  significant figures, by design, and measured on this field that moves a
  velocity by up to 5.8e-7 relative, in v0.1.341 exactly as now.)
* a pickled mesh and a pickled result come back as the same classes (the
  analysis jobs travel to a subprocess by pickle);
* the census of ``test_core_layering_v1340`` loses the loader's three
  imports of ``ogr_fem2d``.

v0.1.473 (spec 010) -- the core's sources are read in the tree of the
``ogr_core`` that is imported (``tests/_sources.py``), which fails
rather than find nothing: the core left this repository for OGR-Core.
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
import _sources as S  # noqa: E402
_CACHE: dict = {}


def _project():
    """A small unsaturated seepage field on the Ej_1 slope, solved once."""
    if "p" not in _CACHE:
        from test_coupling_v128 import _seepage_project
        _CACHE["p"] = _seepage_project(elements=300)
    return _CACHE["p"]


# ======================================================================
class TestOneClassAtOnePath:

    def test_there_is_no_ogr_fem2d_in_this_tree(self):
        """Read from the tree and not asked of the import system: on a
        machine where another checkout is installed in editable mode,
        ``ogr_fem2d`` can still resolve — to THAT tree, which is the
        v0.1.84 trap the runner's ``tree:`` line exists for."""
        assert not (_ROOT / "ogr_fem2d").exists()

    def test_every_name_is_the_core_object(self):
        import ogr_core.fem as core
        import ogr_core.fem.generator as generator
        import ogr_core.fem.seepage as seepage_mod
        for name in ("Mesh", "Node", "Element", "DEGENERATE_SHAPE_RATIO"):
            assert getattr(generator, name) is getattr(core, name), name
        for name in ("BCType", "NodeBC", "SegmentBC",
                     "SeepageBoundaryConditions", "SeepageResult",
                     "hydraulic_props_of", "restore_derived"):
            assert getattr(seepage_mod, name) is getattr(core, name), name
        assert seepage_mod.element_fluxes is core.element_fluxes
        assert core.Mesh.__module__ == "ogr_core.fem.mesh"
        assert core.SeepageResult.__module__ == "ogr_core.fem.seepage_data"
        assert seepage_mod.SeepageSolver.__module__ == "ogr_core.fem.seepage"

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
        from ogr_core.fem.seepage import SeepageSolver
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
            "                     if m.split('.')[0] in ('ogr_fem2d', 'ogr_slip2d')\n"
            "                     or m in ('ogr_core.fem.seepage',\n"
            "                              'ogr_core.fem.generator')),\n"
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
        from ogr_core.fem.seepage import SeepageSolver
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
        found = L.census_of(S.source("ogr_core/project/project.py"),
                            S.core_root())
        assert not any(k[2] == "ogr_fem2d" for k in found), found
        assert not any(k[0] == "ogr_core/project/project.py"
                       and k[2] == "ogr_fem2d" for k in L.ALLOWED)
