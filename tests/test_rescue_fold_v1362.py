# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.362 (D367) — the rescue follows the continuation's path of solutions
across a fold that sits on a kink of a permeability curve.

The defect
----------
Dam 2 of Bowles (1984), with the toe drain of Chapuis et al. (2001), solved
with the groundwater door's settings (w = 0.4, 200 passes, tolerance 1e-5),
came out unconverged on the generator's 3691- and 3886-element meshes:
the loop cycles, Anderson fails at both depths, and the continuation in
the steepness t of the curves stops on its smallest step. D366 measured
why (the bank's ``_auditoria/P6_0360``). The continuation's path of
solutions turns back at a fold. The fold sits on the kink at 9.8 kPa where
the drain's curve meets its floor ``kr_min``, so det J changes sign by
jumping the kink, and no one-sided Jacobian turns singular. Continuation in
t cannot cross it, however its steps are searched.

The fix (the owner's decision)
------------------------------
``RESCUE_PIECEWISE_PATH``: where the continuation stops on its smallest
step, ``_piecewise_path`` follows the path on from there by its arc length,
piece by piece across the kinks (Allgower & Georg 1990). Its orientation
gives sign(tau_t) = sign(det J), so the path goes back in t where det J < 0.
It has no Newton budget of its own, and it runs only when every material
has a User Defined curve; with any other model the rescue says so. Measured
on the bank (``_auditoria/P6_0362``), the path is a Z with three folds on
the drain's kink and one smooth fold, and it ends where the answer already
known is.

The invariants
--------------
* the pieces of a User Defined curve ARE the curve: ln kr on each piece is
  the line through the table, the floor and the ceiling, and it reproduces
  ``relative_permeability`` everywhere; the drain's kinks are 6.9 and
  9.8 kPa (identity). Other models have no pieces;
* on a state where every element is on its piece, the residual of the cell
  is the problem's own, ``_NewtonSystem.residual`` (identity);
* the sign of det J from the LU is that of the determinant (identity,
  against ``numpy.linalg.slogdet``);
* at t = 0 the problem is linear and the path leaves towards t > 0: the
  tangent's t component is positive (Allgower & Georg's orientation, with
  J = K0 positive definite);
* on both meshes the continuation stops on its smallest step, and the
  piecewise path from where it stopped converges. The face is the one
  node of the drain, settled, and the discharge is the published one,
  4.23e-6 m3/(min m) (Chapuis et al. 2001), within 3 %: the criterion of
  D367 (measured -1.44 % and -1.39 % in the bank). Rule 1, an external
  value;
* rule 7: switched off, the rescue that the continuation left at its
  smallest step fails, as in 0.1.361; switched on, it converges by the
  piecewise path. With a model that is not User Defined, the path does not
  run, and the warning and the notes say so.

Cost: about 3 min. Each fine mesh needs one continuation (about 60 s) and
one path (about 30 s), shared by every test on it. Every test restores the
switch it touches (rule 5).
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402

from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel  # noqa: E402
from ogr_fem2d.solvers import seepage  # noqa: E402
from ogr_fem2d.solvers.seepage import (  # noqa: E402
    BCType,
    SeepageSolver,
    UnsaturatedSeepageSolver,
)
from ogr_slip2d.transient_stability import (  # noqa: E402
    STEADY_MAX_ITERATIONS,
    STEADY_RELAXATION,
    STEADY_TOLERANCE,
)

GAMMA_W = 9.81
_CACHE: dict = {}
#: target elements of the generator -> T3 the bank measured
MESHES = {3800: 3691, 4000: 3886}


def _module(name):
    """Another test module of this suite, for its cases (a copy of its own,
    so nothing set here reaches the module the runner runs)."""
    if name not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "t1362_" + name, Path(__file__).parent / (name + ".py"))
        t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(t)
        _CACHE[name] = t
    return _CACHE[name]


def _dam2(target):
    """Dam 2 of ``test_picard_loop_face_v1358`` on a finer mesh."""
    key = ("dam2", target)
    if key not in _CACHE:
        t = _module("test_picard_loop_face_v1358")
        old = t.ELEMENTS
        try:
            t.ELEMENTS = target
            t._CACHE.pop("dam2", None)
            _CACHE[key] = t._dam2()
        finally:
            t.ELEMENTS = old
            t._CACHE.pop("dam2", None)
    return _CACHE[key]


def _start(target):
    """The door's solver on that mesh and what the rescue starts from:
    (solver, bcs, saturated heads, face nodes, p_tol, q_tol)."""
    key = ("start", target)
    if key not in _CACHE:
        mesh, props, bcs = _dam2(target)
        s = UnsaturatedSeepageSolver(
            mesh, props, gamma_w=GAMMA_W, relaxation=STEADY_RELAXATION,
            max_iterations=STEADY_MAX_ITERATIONS, tolerance=STEADY_TOLERANCE)
        first = SeepageSolver.solve(s, bcs)
        unknown = sorted({b.node_id for b in bcs.nodes
                          if b.bc_type == BCType.UNKNOWN or b.seepage_face})
        _CACHE[key] = (s, bcs, first.total_head, unknown, s._face_p_tol(),
                       s._face_q_tol(max(abs(q) for q in first.reactions)))
    return _CACHE[key]


def _continuation(target):
    key = ("continuation", target)
    if key not in _CACHE:
        s, bcs, H_sat, unknown, p_tol, q_tol = _start(target)
        _CACHE[key] = s._continuation_newton(bcs, H_sat, unknown, p_tol,
                                             q_tol)
    return _CACHE[key]


def _path(target):
    key = ("path", target)
    if key not in _CACHE:
        s, bcs, _H, unknown, p_tol, q_tol = _start(target)
        _CACHE[key] = s._piecewise_path(bcs, _continuation(target)["last"],
                                        unknown, p_tol, q_tol)
    return _CACHE[key]


def _discharge(target, r):
    s, bcs, _H, _u, _p, _q = _start(target)
    res = s._picard_map(bcs, np.asarray(r["head"]), r["active"])
    return _module("test_picard_loop_face_v1358")._discharge(s, res)


# ======================================================================
# The pieces and the cell: identities
# ======================================================================
def _user(curve):
    t = _module("test_picard_loop_face_v1358")
    k = [(s, v / t.PER_MINUTE) for s, v in curve]
    return HydraulicProperties(ks=k[0][1], model=PermeabilityModel.USER_DEFINED,
                               user_curve=k)


class TestThePiecesAreTheCurve:
    def test_they_reproduce_the_curve(self):
        t = _module("test_picard_loop_face_v1358")
        for curve in (t.DRAIN, t.CORE):
            p = _user(curve)
            kinks, a, b = p.log_kr_pieces()
            for s in np.linspace(-20.0, 400.0, 4201):
                j = int(np.searchsorted(kinks, s))
                exact = math.log(p.relative_permeability(float(s)))
                assert abs(a[j] + b[j] * s - exact) < 1e-9 * max(1.0, abs(exact)), s

    def test_the_drains_kinks(self):
        """Flat to 6.9 kPa, six decades down to its floor at 9.8 (1e-10 over
        1e-4 is kr_min = 1e-6), flat after: two kinks, no more."""
        t = _module("test_picard_loop_face_v1358")
        kinks, _a, b = _user(t.DRAIN).log_kr_pieces()
        assert len(kinks) == 2
        assert abs(kinks[0] - 6.9) < 1e-12 and abs(kinks[1] - 9.8) < 1e-12
        assert abs(b[1] + 6.0 * math.log(10.0) / 2.9) < 1e-9
        assert abs(b[0]) < 1e-15 and abs(b[2]) < 1e-15

    def test_other_models_have_none(self):
        for model in (PermeabilityModel.VAN_GENUCHTEN, PermeabilityModel.GARDNER,
                      PermeabilityModel.BROOKS_COREY, PermeabilityModel.CONSTANT):
            assert HydraulicProperties(model=model).log_kr_pieces() is None


class TestTheCellIsTheProblem:
    def test_residual_and_orientation(self):
        """On the continuation's last state every element sits on a piece:
        the cell's residual is the problem's. And at t = 0 the path leaves
        towards t > 0."""
        s, bcs, H_sat, _u, _p, _q = _start(3800)
        t_star, H, face = _continuation(3800)["last"][:3]
        system = seepage._NewtonSystem(s, bcs)
        cells = seepage._PiecewiseSystem(system, face, GAMMA_W)
        assert cells.applicable
        H = np.asarray(H, dtype=float).copy()
        H[cells.fix_i] = cells.fix_v
        cells.assign(H)
        assert cells.outside(cells.suction(H)).size == 0
        R, J, _Rt = cells.residual(H, t_star)
        own = system.residual(H, t_star)
        # the scale of the nodal fluxes, sum kr K0 H (no flux is applied)
        scale = float(np.max(np.abs(own + system.q)))
        assert float(np.max(np.abs(R - own[cells.free]))) < 1e-12 * scale
        # the sign of det J from the LU is that of the determinant
        sign, _logdet = np.linalg.slogdet(J.toarray())
        assert seepage._det_sign(seepage._splu(J)) == int(sign)
        # at t = 0, J = K0 on the free nodes
        H0, ok, _k = system.newton(H_sat, face, 0.0, s.tolerance, 5)
        assert ok
        cells.assign(H0)
        assert s._path_tangent(cells, H0, 0.0)[-1] > 0.0

    def test_det_sign_of_small_matrices(self):
        from scipy.sparse import csc_matrix
        rng = np.random.default_rng(1362)
        for _ in range(40):
            A = rng.normal(size=(7, 7))
            sign, _l = np.linalg.slogdet(A)
            assert seepage._det_sign(seepage._splu(csc_matrix(A))) == int(sign)


# ======================================================================
# Dam 2 on the two meshes that failed
# ======================================================================
class TestTheFoldIsCrossed:
    def test_the_meshes_are_the_ones_measured(self):
        for target, t3 in MESHES.items():
            assert _dam2(target)[0].element_count == t3, target

    def test_the_continuation_stops_on_its_smallest_step(self):
        for target in MESHES:
            r = _continuation(target)
            assert r["converged"] is False
            assert r["stopped"] == "min_step", target
            assert r["last"][0] < 1.0

    def test_the_path_reaches_the_published_discharge(self):
        for target in MESHES:
            s = _start(target)[0]
            r = _path(target)
            assert r["converged"], (target, r["residual"])
            assert r["residual"] < s.tolerance
            assert "unsettled" not in r
            assert len(r["active"]) == 1          # the drain's one face node
            q = _discharge(target, r)
            t = _module("test_picard_loop_face_v1358")
            assert abs(q / t.Q_PUBLISHED - 1.0) < 0.03, (target, q)


class TestTheSwitchMovesTheNumber:
    """The rescue from the state the continuation left, the roads before it
    replaced by what they returned (Anderson fails on this dam)."""

    def _rescue(self, on, target=3800):
        s, bcs, H_sat, unknown, p_tol, q_tol = _start(target)
        cont = _continuation(target)
        path = _path(target)
        s._anderson = lambda *a, **k: {"converged": False, "iterations": 0,
                                       "residual": float("nan"),
                                       "history": []}
        s._continuation_newton = lambda *a, **k: dict(cont)
        s._piecewise_path = lambda *a, **k: dict(path)
        old = seepage.RESCUE_PIECEWISE_PATH
        try:
            seepage.RESCUE_PIECEWISE_PATH = on
            return s._rescue(bcs, H_sat, H_sat, set(), unknown, p_tol, q_tol,
                             H_sat)
        finally:
            seepage.RESCUE_PIECEWISE_PATH = old
            for name in ("_anderson", "_continuation_newton",
                         "_piecewise_path"):
                s.__dict__.pop(name, None)

    def test_switched_off_it_fails_as_before(self):
        r = self._rescue(False)
        assert r["converged"] is False and r["method"] == "failed"
        assert "piecewise" not in r

    def test_switched_on_it_converges_by_the_path(self):
        r = self._rescue(True)
        assert r["converged"] and r["method"] == "continuation-piecewise"
        assert [x[0] for x in r["segments"]] == ["continuation-piecewise"]


class TestOtherModelsAreTold:
    """A Gardner dam, the continuation made to stop on its smallest step:
    the path does not run, and the run says why. Ten passes leave the loop
    unconverged (its last change 0.03 m) with the face settled; with two
    the face is still unsettled, and that warning comes first."""

    def _run(self, on):
        t = _module("test_unsaturated_v127")
        mesh = t._dam_mesh(0.7)
        props = {"m": HydraulicProperties(
            ks=t.K_DAM, model=PermeabilityModel.GARDNER, gardner_a=1.0,
            gardner_n=3.0)}
        bcs = t._dam_bcs(mesh)
        s = UnsaturatedSeepageSolver(mesh, props, gamma_w=GAMMA_W,
                                     relaxation=0.4, max_iterations=10,
                                     tolerance=1e-5)
        stopped = {"converged": False, "iterations": 0,
                   "residual": float("nan"), "head": [], "active": set(),
                   "switches": {}, "stopped": "min_step",
                   "last": (0.5, [0.0] * mesh.node_count, set(), {}, 0.25,
                            [0.0] * mesh.node_count)}
        s._anderson = lambda *a, **k: {"converged": False, "iterations": 0,
                                       "residual": float("nan"),
                                       "history": []}
        s._continuation_newton = lambda *a, **k: dict(stopped)
        old = seepage.RESCUE_PIECEWISE_PATH
        try:
            seepage.RESCUE_PIECEWISE_PATH = on
            return s.solve_unsaturated(bcs)
        finally:
            seepage.RESCUE_PIECEWISE_PATH = old

    def test_the_path_says_it_cannot_run(self):
        r = self._run(True)
        assert r.converged is False and r.notes["unsettled_nodes"] == 0
        assert r.notes["rescue"] == "failed"
        assert r.notes["rescue_piecewise"] == "not applicable"
        assert r.notes["warning"].code == "seepage.picard_rescue_piecewise_na"

    def test_switched_off_the_warning_is_the_old_one(self):
        r = self._run(False)
        assert "rescue_piecewise" not in r.notes
        assert r.notes["warning"].code == "seepage.picard_rescue_failed"
