# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.345 (D337, sixth part) — the linearisation of a strength envelope at a
stress is the core's.

``BishopSimplified._local_c_phi`` linearises the envelope of a material at
an effective normal stress: every limit-equilibrium method calls it, and so
does a support's equivalent c and phi (``ogr_core.support.bond.
equivalent_c_phi_at``), which imported the method class for it. Its body
and its docstring moved word for word to
``ogr_core.materials.strength_model.local_c_phi``, and the method's name is
BOUND to that function, not wrapped: a wrapper measured 0.25 us of about
4 us a call, some 3 % of a Bishop solve.

The invariants:

* **the core's function is the old body, digit for digit**: the body of
  ``_local_c_phi`` as v0.1.343 had it is copied literally below
  (``_reference``), and over every strength model that builds with its
  defaults, seven stresses (negative, zero, one-sided near zero, ordinary,
  large) and with and without a slice to read a context from, the two give
  the same ``(c, tan phi)`` or raise the same exception;
* **the methods still go through the method's name**: a spy that replaces
  ``BishopSimplified._local_c_phi`` sees every call a Bishop solve makes,
  which is what the bank's spies rely on; a support's equivalent c and phi
  no longer does (it calls the core directly), and that is said here;
* the support's equivalent c and phi is computed in a fresh interpreter
  without importing the engine;
* the census of ``test_core_layering_v1340`` loses the entry.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_SIGMAS = (-5.0, 0.0, 0.0004, 0.5, 10.0, 150.0, 2000.0)


def _reference(slice_, material, sigma_n_eff, sigma_v_probe=None):
    """``BishopSimplified._local_c_phi`` of v0.1.343, its body copied
    literally (only dedented): the reference the move is measured against."""
    from ogr_core.materials.strength_model import SliceContext  # noqa: F401
    if material is None:
        return 0.0, 0.0
    sn = max(sigma_n_eff, 0.0)
    strength = material.strength
    # v0.1.28 — matric suction beyond the air entry value acts as
    # extra cohesion (extended Mohr-Coulomb). Computed by the slicer
    # so every LEM method picks it up here, in one place.
    c_suction = getattr(slice_, "suction_cohesion", 0.0) or 0.0

    # v0.1.15 — build a context for models that need it. v0.1.230
    # (D219) — built by ``SliceContext.from_slice``, bit for bit what
    # was written here, so that Janbu's soil type reads the context
    # the solver reads.
    ctx = None
    if getattr(strength, "needs_context", False):
        from ogr_core.materials.strength_model import SliceContext
        ctx = SliceContext.from_slice(slice_, sn, sigma_v_probe)

    def _tau(s: float) -> float:
        if ctx is not None:
            return strength.shear_strength_ctx(s, ctx)
        return strength.shear_strength(s)

    tau_at_sn = _tau(sn)
    if not math.isfinite(tau_at_sn):
        return 1e12, 0.0  # InfiniteStrength

    # Analytical tangent only valid for the non-context models
    tan_phi = None
    if ctx is None:
        tangent_fn = getattr(strength, "tangent_slope", None)
        if tangent_fn is not None:
            try:
                tan_phi = tangent_fn(sn)
            except Exception:  # noqa: BLE001
                tan_phi = None

    if tan_phi is None:
        base_delta = max(0.001, 0.0001 * sn)
        delta = base_delta
        if sn - delta < 0:
            tau_hi = _tau(sn + delta)
            if not math.isfinite(tau_hi):
                return 1e12, 0.0
            tan_phi = (tau_hi - tau_at_sn) / delta
        else:
            tau_lo = _tau(sn - delta)
            tau_hi = _tau(sn + delta)
            if not (math.isfinite(tau_lo) and math.isfinite(tau_hi)):
                return 1e12, 0.0
            tan_phi = (tau_hi - tau_lo) / (2.0 * delta)

    tan_phi = max(0.0, tan_phi)
    c = tau_at_sn - sn * tan_phi
    c = max(0.0, c)
    return c + c_suction, tan_phi


def _models():
    """Every strength model of the program that builds with its defaults."""
    import inspect

    import ogr_core.materials.builtin_models as B
    from ogr_core.materials.strength_model import StrengthModel
    out = []
    for name, cls in sorted(vars(B).items()):
        if (not inspect.isclass(cls) or not issubclass(cls, StrengthModel)
                or name.startswith("_") or inspect.isabstract(cls)):
            continue
        try:
            model = cls()
            model.shear_strength(100.0)
        except Exception:  # noqa: BLE001 - one that needs its table
            continue
        out.append((name, model))
    return out


def _stand_in():
    from ogr_core.support.bond import _PointAsSlice
    return _PointAsSlice(12.0, 80.0, 15.0, 6.0, 0.3, 14.0, 3.5,
                         bedding_angle_deg=20.0, x=7.0)


def _outcome(fn, *args):
    try:
        return ("value", fn(*args))
    except Exception as exc:  # noqa: BLE001
        return ("raises", type(exc).__name__)


# ======================================================================
class TestTheCoresFunctionIsTheOldBody:

    def test_every_model_every_stress_with_and_without_a_slice(self):
        from ogr_core.materials import Material
        from ogr_core.materials.strength_model import local_c_phi
        models = _models()
        assert len(models) >= 10, [n for n, _m in models]
        compared = 0
        for name, model in models:
            mat = Material(name=name, strength=model)
            for slice_ in (None, _stand_in()):
                if slice_ is None and getattr(model, "needs_context", False):
                    continue
                for sigma in _SIGMAS:
                    for probe in (None, 55.0):
                        got = _outcome(local_c_phi, slice_, mat, sigma, probe)
                        ref = _outcome(_reference, slice_, mat, sigma, probe)
                        assert got == ref, (name, sigma, probe, got, ref)
                        compared += 1
        assert _outcome(local_c_phi, None, None, 10.0) == ("value", (0.0, 0.0))
        assert compared > 200, compared

    def test_the_method_s_name_is_the_core_s_function(self):
        import ast

        from ogr_core.materials import HoekBrown, Material
        from ogr_core.materials.strength_model import local_c_phi
        from ogr_slip2d.methods.bishop import BishopSimplified
        assert BishopSimplified.__dict__["_local_c_phi"].__func__ \
            is local_c_phi
        m = Material(name="rock",
                     strength=HoekBrown(sigci=15000, m=0.357, s=0.0017))
        assert BishopSimplified._local_c_phi(None, m, 100.0) == \
            local_c_phi(None, m, 100.0)
        # the docstring went with the body: where the methods linearise
        # (D84) and the figures the bank reads
        tree = ast.parse((_ROOT / "ogr_core" / "materials"
                          / "strength_model.py").read_text(encoding="utf-8"))
        doc = next(ast.get_docstring(n) for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef)
                   and n.name == "local_c_phi")
        for needle in ("Perry", "0.944", "D84"):
            assert needle in doc, needle


# ======================================================================
class TestTheSpiesStillSeeTheMethods:

    def test_a_spy_on_the_method_sees_a_bishop_solve_and_not_a_support(self):
        import test_upward_load_v1241 as V
        from ogr_core.support.bond import equivalent_c_phi_at
        from ogr_slip2d.methods.bishop import BishopSimplified as B
        p = V._slope()
        circle, sliced = V._sliced(p)
        seen = []
        desc = B.__dict__["_local_c_phi"]
        real = desc.__func__

        def spy(*a, **k):
            seen.append(a[2] if len(a) > 2 else None)
            return real(*a, **k)

        B._local_c_phi = staticmethod(spy)
        try:
            B(tolerance=1e-8).compute_fos(p, circle, sliced)
            during_solve = len(seen)
            equivalent_c_phi_at(p, 70.0, 38.0, 50.0, depth=2.0)
        finally:
            B._local_c_phi = desc
        assert during_solve > 0
        assert len(seen) == during_solve, \
            "a support's linearisation goes to the core, not to the method"


# ======================================================================
class TestTheSupportReadsTheEnvelopeWithoutTheEngine:

    def test_in_a_fresh_interpreter(self):
        script = (
            "import sys\n"
            "from ogr_core.project.demo import build_demo_project\n"
            "from ogr_core.support.bond import equivalent_c_phi_at\n"
            "p = build_demo_project()\n"
            "xmin, ymin, xmax, ymax = p.bounding_box()\n"
            "c, t = equivalent_c_phi_at(p, 0.5 * (xmin + xmax),\n"
            "                           ymin + 0.25 * (ymax - ymin), 60.0)\n"
            "assert c >= 0.0 and t >= 0.0\n"
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
class TestTheCensusLosesTheEntry:

    def test_bond_imports_nothing_above(self):
        from collections import Counter

        import test_core_layering_v1340 as L
        found = L.census_of(_ROOT / "ogr_core" / "support" / "bond.py", _ROOT)
        assert found == Counter(), found
