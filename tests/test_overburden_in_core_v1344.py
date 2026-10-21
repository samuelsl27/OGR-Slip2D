# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.344 (D337, fifth part) — the soil column and the pressure of the loads
are the core's, and their switch has one home.

The slice weight, the effective stress along a support
(``ogr_core.support.bond``) and the excess pore pressure of B-bar loading
(``ogr_core.hydraulic.excess_pore_pressure``) read one decomposition of the
soil column, and the two in the core imported the slicer for it — six of the
engine imports D337 counted. The functions moved word for word to
``ogr_core.loads.overburden``, and the slicer imports them back. The switch
``SIGNED_SURFACE_PRESSURE`` (v0.1.241, D232: an upward load takes weight
off) moved with the function that reads it.

The invariants:

* **the slicer's names are the core's objects**, so its own callers and the
  four test files that import them from the slicer keep working;
* **the switch has ONE home** and the slicer keeps no copy: a copy set to
  False would change nothing, which is worse than no switch (rule 7);
* **the one switch moves all three readers** (rule 7): with it off, an
  upward load presses again on the slice weight, on the vertical stress of
  B-bar loading and on the effective stress along a support — the v0.1.240
  behaviour — and with it on each one takes the load off;
* **no switch of the engine or the core is defined in two modules**, so a
  measurement that turns one off cannot turn off a copy nobody reads;
* in a fresh interpreter the stress along a support and the stress of the
  loads are computed without importing the engine;
* the census of ``test_core_layering_v1340`` loses the six entries.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent


def _V():
    import test_upward_load_v1241 as V
    return V


# ======================================================================
class TestTheSlicersNamesAreTheCores:

    def test_same_objects(self):
        import ogr_core.loads.overburden as ov
        import ogr_slip2d.slicer as sl
        for name in ("_column_weight", "_material_key",
                     "_polyline_crossings_at_x", "_line_load_components",
                     "_surface_pressure_at", "_surface_pressures_at",
                     "_summed"):
            assert getattr(sl, name) is getattr(ov, name), name

    def test_the_switch_has_one_home(self):
        import ogr_core.loads.overburden as ov
        import ogr_slip2d.slicer as sl
        assert ov.SIGNED_SURFACE_PRESSURE is True
        assert not hasattr(sl, "SIGNED_SURFACE_PRESSURE")


# ======================================================================
class TestTheOneSwitchMovesTheThreeReaders:

    def _three(self, direction):
        """Slice weights, the vertical stress of the loads at x = 70 and
        the effective stress at (70, 38) along a support."""
        from ogr_core.hydraulic.excess_pore_pressure import load_delta_sigma_v
        from ogr_core.support.bond import sigma_v_effective_at
        V = _V()
        p = V._slope(V._load(direction))
        for load in p.distributed_loads:
            load.creates_excess_pore_pressure = True
        _c, sliced = V._sliced(p)
        return ([s.weight for s in sliced.slices],
                load_delta_sigma_v(p, 70.0),
                sigma_v_effective_at(p, 70.0, 38.0)[0])

    def test_on_an_upward_load_takes_off_and_off_it_presses(self):
        import ogr_core.loads.overburden as ov
        down = self._three("down")
        up_on = self._three("up")
        ov.SIGNED_SURFACE_PRESSURE = False
        try:
            up_off = self._three("up")
        finally:
            ov.SIGNED_SURFACE_PRESSURE = True
        V = _V()
        # off: the v0.1.240 behaviour, the upward load presses like the
        # downward one, in every reader
        assert all(V._close(a, b) for a, b in zip(up_off[0], down[0]))
        assert V._close(up_off[1], down[1]) and V._close(up_off[2], down[2])
        # on: it takes off, in every reader
        assert V._close(up_on[1], -down[1]) and down[1] > 0.0
        assert up_on[2] < down[2]
        assert sum(a for a in up_on[0]) < sum(b for b in down[0])


# ======================================================================
def _switches():
    """``{NAME: [modules]}`` for every top-level ``NAME = True/False`` of the
    engine and the core."""
    found = defaultdict(list)
    for pkg in ("ogr_core", "ogr_slip2d", "ogr_fem2d"):
        for path in sorted((_ROOT / pkg).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if (isinstance(node, ast.Assign)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, bool)):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id.isupper():
                            found[t.id].append(
                                path.relative_to(_ROOT).as_posix())
    return found


class TestNoSwitchIsDefinedTwice:

    def test_one_module_per_switch(self):
        found = _switches()
        assert len(found) > 20, "premise: the census sees the switches"
        twice = {k: v for k, v in found.items() if len(v) > 1}
        assert not twice, twice
        assert found["SIGNED_SURFACE_PRESSURE"] == [
            "ogr_core/loads/overburden.py"]


# ======================================================================
class TestTheCoreComputesTheStressWithoutTheEngine:

    def test_in_a_fresh_interpreter(self):
        script = (
            "import sys\n"
            "from ogr_core.geometry import Vertex\n"
            "from ogr_core.loads.loads import DistributedLoad, LoadOrientation\n"
            "from ogr_core.project.demo import build_demo_project\n"
            "from ogr_core.hydraulic.excess_pore_pressure import load_delta_sigma_v\n"
            "from ogr_core.support.bond import sigma_v_effective_at\n"
            "p = build_demo_project()\n"
            "xmin, ymin, xmax, ymax = p.bounding_box()\n"
            "x = 0.5 * (xmin + xmax)\n"
            "load = DistributedLoad(start=Vertex(xmin, ymax), end=Vertex(xmax, ymax),\n"
            "                       magnitude_1=10.0,\n"
            "                       orientation=LoadOrientation.VERTICAL)\n"
            "load.creates_excess_pore_pressure = True\n"
            "p.distributed_loads = [load]\n"
            "load_delta_sigma_v(p, x)\n"
            "sigma_v_effective_at(p, x, ymin + 0.25 * (ymax - ymin))\n"
            "print(sorted(m for m in sys.modules\n"
            "             if m.split('.')[0] in ('ogr_slip2d', 'ogr_fem2d')))\n")
        env = dict(os.environ, PYTHONPATH=str(_ROOT),
                   QT_QPA_PLATFORM="offscreen")
        out = subprocess.run([sys.executable, "-c", script], cwd=str(_ROOT),
                             env=env, capture_output=True, text=True,
                             timeout=300)
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == "[]", out.stdout


# ======================================================================
class TestTheCensusLosesTheSix:

    def test_no_entry_for_the_column_or_the_loads(self):
        import test_core_layering_v1340 as L
        for rel in ("ogr_core/hydraulic/excess_pore_pressure.py",):
            assert not L.census_of(_ROOT / rel, _ROOT), rel
        bond = L.census_of(_ROOT / "ogr_core" / "support" / "bond.py", _ROOT)
        assert set(k[1] for k in bond) <= {"equivalent_c_phi_at"}, bond
