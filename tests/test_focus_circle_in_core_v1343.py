# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.343 (D337, fourth part) — the focus objects and the slip circle the
project stores are the core's, and the project loads without the engine.

``Project.from_dict`` rebuilt the focus objects from ``ogr_slip2d.focus``
and the user's circles from ``ogr_slip2d.surface``: the last two imports of
the engine in the loader. The focus module never needed the engine and
moved whole to ``ogr_core.geometry.focus``; ``SlipCircle`` and the one
function of its module it used (``ground_y_at``) moved to
``ogr_core.geometry.slip_circle``. The engine re-exports every name.

The invariants:

* **one object at both paths**: every name the old focus module defined
  (the private helpers too) and ``SlipCircle`` / ``ground_y_at`` are the
  very objects of the core, so ``isinstance`` and every import keep
  working; the composite surface, which is built from a circle, still is;
* **a project with focus objects, user circles, a mesh and a seepage field
  loads in a fresh interpreter with no engine module at all**, and gives
  back what was saved, ``to_dict`` for ``to_dict``;
* a pickled circle and a pickled focus object come back as the same class;
* **the loader imports nothing above the core any more**: its census is
  empty, and ``test_core_layering_v1340`` has no entry for it.
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent


def _project():
    from ogr_core.geometry.focus import FocusKind, FocusObject
    from ogr_core.geometry.slip_circle import SlipCircle
    from test_coupling_v128 import _seepage_project
    p = _seepage_project(elements=300)
    p.focus_objects = [
        FocusObject(kind=FocusKind.POINT, points=[(60.0, 30.0)],
                    tolerance=1.5),
        FocusObject(kind=FocusKind.LINE, points=[(50.0, 25.0), (70.0, 28.0)])]
    p.user_surfaces = [SlipCircle(centre_x=88.0, centre_y=70.5,
                                  radius=47.212)]
    return p


# ======================================================================
class TestOneObjectAtBothPaths:

    def test_every_name_of_the_old_modules_is_the_core_object(self):
        import ogr_core.geometry.focus as core_focus
        import ogr_core.geometry.slip_circle as core_circle
        import ogr_slip2d
        import ogr_slip2d.focus as old_focus
        import ogr_slip2d.surface as old_surface
        names = [n for n in vars(core_focus)
                 if not n.startswith("__") and n not in (
                     "annotations", "math", "dataclass", "field", "Enum",
                     "Optional")]
        assert {"FocusObject", "FocusKind", "accepts", "accepts_surface",
                "filter_circles", "_point_in_polygon"} <= set(names)
        for n in names:
            assert getattr(old_focus, n) is getattr(core_focus, n), n
        assert old_surface.SlipCircle is core_circle.SlipCircle
        assert old_surface.ground_y_at is core_circle.ground_y_at
        assert ogr_slip2d.SlipCircle is core_circle.SlipCircle
        assert core_circle.SlipCircle.__module__ == \
            "ogr_core.geometry.slip_circle"

    def test_a_composite_is_still_built_from_the_same_circle(self):
        from ogr_core.geometry.slip_circle import SlipCircle
        from ogr_slip2d.surface import compose_with_bedrock
        import inspect
        assert "SlipCircle" in str(inspect.signature(compose_with_bedrock))
        c = SlipCircle(centre_x=10.0, centre_y=20.0, radius=15.0)
        assert isinstance(pickle.loads(pickle.dumps(c)), SlipCircle)

    def test_pickles_come_back_as_the_same_classes(self):
        from ogr_core.geometry.focus import FocusObject
        from ogr_core.geometry.slip_circle import SlipCircle
        p = _project()
        f = pickle.loads(pickle.dumps(p.focus_objects[0]))
        c = pickle.loads(pickle.dumps(p.user_surfaces[0]))
        assert type(f) is FocusObject and type(c) is SlipCircle
        assert f.to_dict() == p.focus_objects[0].to_dict()
        assert c.to_dict() == p.user_surfaces[0].to_dict()


# ======================================================================
class TestTheProjectLoadsWithoutTheEngine:

    def test_in_a_fresh_interpreter(self):
        p = _project()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_focus_"))
        path = tmp / "model.ogr"
        try:
            p.save(path)
            saved = json.loads(path.read_text(encoding="utf-8"))
            script = (
                "import json, sys\n"
                "from ogr_core.project import Project\n"
                "q = Project.load(sys.argv[1])\n"
                "print(json.dumps({\n"
                "    'engine': sorted(m for m in sys.modules\n"
                "                     if m.split('.')[0] in ('ogr_fem2d',\n"
                "                                            'ogr_slip2d')),\n"
                "    'focus': [f.to_dict() for f in q.focus_objects],\n"
                "    'circles': [s.to_dict() for s in q.user_surfaces],\n"
                "    'types': [type(q.focus_objects[0]).__module__,\n"
                "              type(q.user_surfaces[0]).__module__]}))\n")
            env = dict(os.environ, PYTHONPATH=str(_ROOT),
                       QT_QPA_PLATFORM="offscreen")
            out = subprocess.run([sys.executable, "-c", script, str(path)],
                                 cwd=str(_ROOT), env=env,
                                 capture_output=True, text=True, timeout=300)
        finally:
            path.unlink(missing_ok=True)
            tmp.rmdir()
        assert out.returncode == 0, out.stderr
        got = json.loads(out.stdout)
        assert got["engine"] == [], got["engine"]
        assert got["types"] == ["ogr_core.geometry.focus",
                                "ogr_core.geometry.slip_circle"]
        assert got["focus"] == saved["focus_objects"]
        assert got["circles"] == saved["user_surfaces"]


# ======================================================================
class TestTheLoaderImportsNothingAbove:

    def test_its_census_is_empty(self):
        import test_core_layering_v1340 as L
        found = L.census_of(_ROOT / "ogr_core" / "project" / "project.py",
                            _ROOT)
        assert found == Counter(), found
        assert not any(k[0] == "ogr_core/project/project.py"
                       for k in L.ALLOWED)
