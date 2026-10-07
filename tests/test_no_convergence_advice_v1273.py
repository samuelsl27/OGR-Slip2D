# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.273 (D266) — the non-convergence warnings of the seepage solvers give
advice the user can follow, or none.

The defect
----------
The steady solver's warning (reached with the rescue switched off) said
"Try a smaller relaxation factor or a finer mesh", and a transient stage's
said "try more time steps or a smaller relaxation factor". The relaxation is
not a setting anywhere a user can reach — ``solve_project_groundwater`` fixes
it — and a finer mesh is what brings on the cycle the rescue of D124 exists
for. Measured on the 53 unsaturated steady rows of the verification bank
with w from 0.2 to 0.8, convergence never depends on w, so the advice was
never true there either; why the relaxation is not exposed is written in
``solve_project_groundwater`` (CIERRE DOCUMENTAL of the defect).

The invariants
--------------
* the steady warning with the rescue off names the cause and no impossible
  remedy;
* a transient stage that fails points at its own settings (time steps,
  Picard iterations per step), which the project settings do expose;
* no string the seepage module can put in a warning mentions a relaxation
  factor or a finer mesh (docstrings and comments may explain why not).

The rescue switch is restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    TransientSeepageSolver,
    TransientStage,
    UnsaturatedSeepageSolver,
)

_BAD = ("relaxation factor", "finer mesh")


def _dam():
    spec = importlib.util.spec_from_file_location(
        "t127_d266", Path(__file__).parent / "test_unsaturated_v127.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    mesh = t._dam_mesh(0.7)
    props = {"m": HydraulicProperties(
        ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
        gardner_n=3.0)}
    return mesh, props, t._dam_bcs(mesh)


def _vg_dam():
    """The reproduction of the defect's prompt: the coarse dam with a steep
    van Genuchten curve, which reaches the warning branch (two passes do
    not converge and the face does settle)."""
    spec = importlib.util.spec_from_file_location(
        "t127_d266b", Path(__file__).parent / "test_unsaturated_v127.py")
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    mesh = t._dam_mesh(1.2)
    props = {"m": HydraulicProperties(
        ks=t.K_DAM, model=PermeabilityModel.VAN_GENUCHTEN, vg_alpha=5.0,
        vg_n=3.0, kr_min=1e-12)}
    return mesh, props, t._dam_bcs(mesh)


class TestTheWarningsGiveFollowableAdvice:
    def test_the_steady_warning_with_the_rescue_off(self):
        mesh, props, bcs = _vg_dam()
        old = seepage.PICARD_RESCUE
        try:
            seepage.PICARD_RESCUE = False
            r = UnsaturatedSeepageSolver(
                mesh, props, relaxation=1.0, max_iterations=2,
                tolerance=1e-5).solve_unsaturated(bcs)
        finally:
            seepage.PICARD_RESCUE = old
        assert not r.converged
        w = r.notes["warning"]
        assert "did not converge" in w and "rescue is switched off" in w, w
        assert not any(b in w.lower() for b in _BAD), w

    def test_a_transient_stage_points_at_its_own_settings(self):
        mesh, props, bcs = _dam()
        s = TransientSeepageSolver(mesh, props, relaxation=0.5,
                                   tolerance=1e-12, time_steps=2,
                                   max_picard=1)
        st = s.solve_transient([TransientStage(time=3600.0, bcs=bcs)],
                               initial_bcs=bcs)[-1]
        assert not st.converged
        w = st.notes["warning"]
        assert "more time steps" in w and "Picard iterations per step" in w
        assert not any(b in w.lower() for b in _BAD), w


class TestNoWarningStringGivesTheOldAdvice:
    def test_the_seepage_module(self):
        """Every string literal of the module that is not a docstring —
        f-string parts included — is free of the two remedies."""
        src = Path(seepage.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = getattr(node, "body", [])
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0].value))
        offending = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings):
                if any(b in node.value.lower() for b in _BAD):
                    offending.append((node.lineno, node.value))
        assert not offending, offending
