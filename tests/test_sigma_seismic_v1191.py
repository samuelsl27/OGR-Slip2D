# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.191 — the two admissibility checks estimate the base load with the
vertical seismic coefficient the METHOD applied, and they learn it from the
method rather than working it out again.

THE INVARIANT. ``checks._base_load_and_sigma`` gives the tensile check and
the m-alpha check the load on a slice base, and the stress they linearise
the envelope at. v0.1.188 (D113) made it ONE function so the two could not
drift apart, and took the load from ``slice_forces`` — but called it with
the default ``kv = 0.0`` while every method calls
``slice_forces(s, kh, kv)``. With a vertical earthquake the check judged
each slice under a load the solver never applied (defect D167). The
coefficient now travels in ``LEMResult.details["kv"]``, written by every
method from the same local it hands the solver, which is the road
``m_alpha_sign`` already takes (D112).

WHAT THE DEFECT REPORT GOT WRONG, executed here rather than argued:
* its 2x2 said only a sigma-dependent envelope moves. That holds for
  ``m_alpha``, and even there Mohr-Coulomb moves by about 1e-12 (it has
  no analytic tangent, so its secant carries rounding). For the tensile
  check it is false outright: the load enters the normal force directly,
  so the effective stress moves with EVERY envelope, Undrained included.
* ``kh`` is not carried, because ``w_total`` does not depend on it; a key
  nobody reads would be rule 7 in miniature. That is what keeps the seven
  bank models with a horizontal earthquake bit-identical.

WHAT THIS FILE DOES NOT CLAIM. Not the sign convention of kv (D170: the
reference documents a positive coefficient as DOWNWARDS and ``slice_forces``
applies it upwards; the check calls ``slice_forces``, so it will follow
whichever way that is settled). Not that the check's stress is the solver's
for every method: with supports, and for the Ordinary Method, it is not,
kv or no kv (D172).

WHAT THIS FILE DISCRIMINATES against the v0.1.190 tree. MEASURED, by
copying this file into a ``git worktree`` at that commit and running it
there — not predicted. Of the 16 cases, **8 fail and 8 pass**:

  fail  under_a_vertical_earthquake                        (behaviour: the
                                          identity, 0.32 off on that tree)
        m_alpha_moves_where_the_envelope_depends_on_sigma  (behaviour)
        the_effective_stress_moves_with_every_envelope     (behaviour)
        every_method_publishes_the_kv_it_applied           (WEAK: a key)
        a_disabled_earthquake_publishes_zero_...           (WEAK: a key)
        the_multistage_drawdown_wrapper_carries_it         (WEAK: a key)
        and_carries_it_when_no_pass_produced_the_answer    (WEAK: a key)
        the_base_load_takes_kv_by_name_and_without_...     (WEAK: a
                                                    parameter that is not)

  pass  and_without_one_it_was_already_exact               (guard)
        m_alpha_barely_moves_on_a_straight_line_...        (guard)
        kv_zero_is_the_same_number_as_no_key               (null control)
        a_horizontal_earthquake_alone_moves_nothing        (null control)
        a_result_without_details_reads_as_no_earthquake    (null control)
        the_checks_never_read_the_project                  (guard)
        the_vertical_coefficient_moves_the_factor_...      (fixture guard)
        the_power_curve_tangent_depends_on_sigma           (fixture guard)

Five of the eight failures are weak, and saying so is the point of this
list: they fail because a key or a parameter is absent, and they would all
pass on a tree whose methods published the key while the checks went on
ignoring it — which is the defect. The three that fail on a number are the
ones that carry the claim, and the identity is the strongest of them,
because it ties the check to the solver and not to this file.

THE ANCHORS ARE IDENTITIES, NOT SNAPSHOTS.
* The solver's OWN normal force: for Bishop and both Janbus the check's
  effective stress must be ``N/l - u`` from ``res.base_normal_force``.
  Measured on this fixture before the fix: EXACTLY 0.0 at kv = 0 and about
  0.32 relative at kv = 0.2 — an identity, not a tolerance. Comparing with
  ``slice_forces`` instead would be a tautology, since the check calls it.
* The 2x2 is taken on ONE converged result per envelope, changing only
  ``details["kv"]``. Solving each arm separately would change the factor of
  safety with kv, and then the old tree would "move" too.
* The null controls are bit for bit: ``x * (1.0 - 0.0)`` is ``x``.
"""
from __future__ import annotations

import ast
import copy
import inspect
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: A power curve with b < 1, so the tangent falls as sigma grows — the only
#: reason the estimate matters to m_alpha. With the default b = 1.0 the
#: envelope is a straight line and the sigma-dependent arm tests nothing.
POWER = dict(a=3.4, b=0.6, c=0.0, d=0.15, waviness=0.0)
KV = 0.2
N_SLICES = 25

_CACHE: dict = {}


def _strength(envelope: str):
    from ogr_core.materials import MohrCoulomb, Undrained
    from ogr_core.materials.builtin_models import PowerCurve
    if envelope == "power":
        return PowerCurve(**POWER)
    if envelope == "mc":
        return MohrCoulomb(cohesion=12.0, friction_angle=28.0)
    return Undrained(cohesion=40.0)


def _project(envelope: str, kv: float = 0.0, kh: float = 0.0,
             enabled: bool = True):
    """A dry 2:1 slope. The earthquake goes on ``p.seismic``, which is what
    the methods read. NOT on ``p.settings.seismic``: that object holds the
    Ky and Newmark options and has no ``kh``, ``kv`` or ``enabled``, so
    writing them there creates attributes nobody reads — the helper of
    ``test_slide_sign_by_method_v1189.py`` does exactly that, harmlessly
    only because it is never called with an earthquake."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(120, 0), Vertex(120, 40),
        Vertex(70, 40), Vertex(30, 20), Vertex(0, 20),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("seismic-sigma")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="fill", unit_weight=20.0,
                            sat_unit_weight=20.0,
                            strength=_strength(envelope))]
    p.seismic.enabled = enabled
    p.seismic.kh = kh
    p.seismic.kv = kv
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=55.0, centre_y=62.0, radius=48.0)


def _solve(method_id: str, envelope: str = "mc", kv: float = 0.0,
           kh: float = 0.0, enabled: bool = True):
    """One converged result per case, shared. Never mutated: every test
    that changes ``details`` does it on a copy."""
    key = (method_id, envelope, kv, kh, enabled)
    if key not in _CACHE:
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        p = _project(envelope, kv=kv, kh=kh, enabled=enabled)
        sl = slice_surface(p, _circle(), num_slices=N_SLICES)
        assert sl is not None, key
        res = get_method(method_id)().compute_fos(p, _circle(), sl)
        assert res.is_valid, (key, res.error_message)
        _CACHE[key] = res
    return _CACHE[key]


def _with_details(res, **over):
    """A copy with other ``details``. ``copy.copy`` SHARES the dict, so a
    new one is assigned: otherwise the next call would rewrite this one."""
    out = copy.copy(res)
    d = dict(getattr(res, "details", None) or {})
    for k, v in over.items():
        if v is None:
            d.pop(k, None)
        else:
            d[k] = v
    out.details = d
    return out


def _identity_residual(res) -> float:
    """Largest relative gap between the check's effective stress and the
    one the solver's own normal force implies."""
    from ogr_slip2d.checks import base_effective_stresses
    check = base_effective_stresses(res)
    solver = [n / max(s.base_length, 1e-12) - s.pore_pressure
              for n, s in zip(res.base_normal_force, res.slices)]
    assert check and len(check) == len(solver)
    return max(abs(a - b) / max(1.0, abs(b)) for a, b in zip(check, solver))


# ======================================================================
class TestTheFixtureAppliesTheEarthquake:
    """GUARDS. Everything below is vacuous if the earthquake never reaches
    the solver, or if the envelope does not depend on sigma."""

    def test_the_vertical_coefficient_moves_the_factor_of_safety(self):
        still = _solve("bishop_simplified", "mc", kv=0.0)
        shaken = _solve("bishop_simplified", "mc", kv=KV)
        assert abs(shaken.fos - still.fos) / still.fos > 1e-3, (
            still.fos, shaken.fos)

    def test_the_power_curve_tangent_depends_on_sigma(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _solve("bishop_simplified", "power", kv=0.0)
        s = list(res.slices)[N_SLICES // 2]
        _c1, t1 = BishopSimplified._local_c_phi(s, s.material, 20.0)
        _c2, t2 = BishopSimplified._local_c_phi(s, s.material, 200.0)
        assert t1 > t2 * 1.2, (t1, t2)


# ======================================================================
class TestTheMethodSaysWhichKvItApplied:
    """The carrier. Each case fails on v0.1.190 by the ABSENCE of a key,
    which is weak discrimination; the behaviour is in the next classes."""

    def test_every_method_publishes_the_kv_it_applied(self):
        from ogr_slip2d.methods import method_registry
        for mid in method_registry():
            res = _solve(mid, "mc", kv=0.15)
            assert res.details["kv"] == 0.15, (mid, res.details.get("kv"))

    def test_a_disabled_earthquake_publishes_zero_whatever_is_stored(self):
        """The coefficient APPLIED, not the one stored: a disabled
        earthquake with kv = 0.15 on file is kv = 0 to every method."""
        from ogr_slip2d.methods import method_registry
        for mid in method_registry():
            res = _solve(mid, "mc", kv=0.15, enabled=False)
            assert res.details["kv"] == 0.0, (mid, res.details.get("kv"))

    def test_the_multistage_drawdown_wrapper_carries_it(self):
        """It builds its ``details`` as a literal, which dropped every inner
        key; ``kv`` is now copied from the pass that produced the answer."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface
        from test_rapid_drawdown_v168 import _circle as _dd_circle
        from test_rapid_drawdown_v168 import _pilarcitos

        p = _pilarcitos()
        p.seismic.enabled = True
        p.seismic.kv = 0.05
        sl = slice_surface(p, _dd_circle(), num_slices=N_SLICES)
        res = wrap_for_drawdown(BishopSimplified(), p,
                                num_slices=N_SLICES).compute_fos(
            p, _dd_circle(), sl)
        # Guard first: an invalid result (RapidDrawdownError) carries no
        # details at all, and a .get() with a default would pass on it.
        assert res.is_valid, res.error_message
        assert res.details["kv"] == 0.05, res.details

    def test_and_carries_it_when_no_pass_produced_the_answer(self):
        """The cycling drained cap reports the midpoint of two passes and
        no per-slice forces, so ``final_result`` is None. The coefficient
        then comes from the project, which every stage shared:
        ``level_project`` is a shallow copy with the same SeismicLoad.

        Reached by patching, restored in ``finally`` — the runner has no
        teardown, and a module-level patch left behind would leak into
        every later file."""
        import ogr_slip2d.rapid_drawdown as rd
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from test_rapid_drawdown_v168 import _circle as _dd_circle
        from test_rapid_drawdown_v168 import _pilarcitos

        original = rd.rapid_drawdown_fos

        def _no_final(*args, **kwargs):
            out = original(*args, **kwargs)
            out.final_result = None
            return out

        p = _pilarcitos()
        p.seismic.enabled = True
        p.seismic.kv = -0.05
        sl = slice_surface(p, _dd_circle(), num_slices=N_SLICES)
        rd.rapid_drawdown_fos = _no_final
        try:
            res = rd.wrap_for_drawdown(BishopSimplified(), p,
                                       num_slices=N_SLICES).compute_fos(
                p, _dd_circle(), sl)
        finally:
            rd.rapid_drawdown_fos = original
        assert res.is_valid, res.error_message
        assert res.base_normal_force == []          # the branch was reached
        assert res.details["kv"] == -0.05, res.details


# ======================================================================
class TestTheCheckEvaluatesTheSolversStress:
    """The identity. This is what D167 is, stated as an equation."""

    METHODS = ("bishop_simplified", "janbu_simplified", "janbu_corrected")

    def test_under_a_vertical_earthquake(self):
        for mid in self.METHODS:
            for env in ("power", "mc"):
                r = _identity_residual(_solve(mid, env, kv=KV))
                assert r <= 1e-9, (mid, env, r)

    def test_and_without_one_it_was_already_exact(self):
        """GUARD: at kv = 0 the identity held before this version too, to
        the last bit. That is what makes the kv = 0.2 residual attributable
        to kv and to nothing else."""
        for mid in self.METHODS:
            for env in ("power", "mc"):
                assert _identity_residual(_solve(mid, env, kv=0.0)) == 0.0


# ======================================================================
class TestOnlyTheCoefficientMoves:
    """The 2x2, on ONE converged result per envelope: the factor of safety,
    the slices and the sign are the same in both columns, and the only
    thing that differs is ``details["kv"]``."""

    def _pair(self, envelope):
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        res = _solve("bishop_simplified", envelope, kv=KV)
        blind = _with_details(res, kv=0.0)
        return ((base_m_alphas(res), base_m_alphas(blind)),
                (base_effective_stresses(res), base_effective_stresses(blind)))

    def test_m_alpha_moves_where_the_envelope_depends_on_sigma(self):
        (m_kv, m_blind), _s = self._pair("power")
        assert max(abs(a - b) for a, b in zip(m_kv, m_blind)) > 1e-3

    def test_m_alpha_barely_moves_on_a_straight_line_and_not_at_all_flat(
            self):
        """GUARD, and the precise form of the report's claim: Mohr-Coulomb
        moves by rounding only (no analytic tangent), Undrained not at all
        (tan phi is exactly 0 at every stress)."""
        (m_kv, m_blind), _s = self._pair("mc")
        assert max(abs(a - b) for a, b in zip(m_kv, m_blind)) < 1e-9
        (u_kv, u_blind), _s = self._pair("undrained")
        assert u_kv == u_blind

    def test_the_effective_stress_moves_with_every_envelope(self):
        """The report's 2x2 was wrong here: the load is IN the normal
        force, so the tensile check moves whatever the envelope."""
        for env in ("power", "mc", "undrained"):
            _m, (s_kv, s_blind) = self._pair(env)
            gap = max(abs(a - b) / max(1.0, abs(b))
                      for a, b in zip(s_kv, s_blind))
            assert gap > 1e-3, (env, gap)


# ======================================================================
class TestTheNullControls:
    """GUARDS, all bit for bit."""

    def test_kv_zero_is_the_same_number_as_no_key(self):
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        res = _solve("bishop_simplified", "power", kv=0.0)
        zero = _with_details(res, kv=0.0)
        none = _with_details(res, kv=None)
        assert base_m_alphas(zero) == base_m_alphas(none)
        assert base_effective_stresses(zero) == base_effective_stresses(none)

    def test_a_horizontal_earthquake_alone_moves_nothing(self):
        """What keeps the seven bank models with kh != 0 and kv = 0 where
        they are: kh does not enter the base load."""
        from ogr_slip2d.checks import base_effective_stresses, base_m_alphas
        res = _solve("bishop_simplified", "power", kv=0.0, kh=0.15)
        none = _with_details(res, kv=None)
        assert base_m_alphas(res) == base_m_alphas(none)
        assert base_effective_stresses(res) == base_effective_stresses(none)

    def test_a_result_without_details_reads_as_no_earthquake(self):
        from ogr_slip2d.checks import base_m_alphas
        res = _solve("bishop_simplified", "power", kv=0.0)
        bare = copy.copy(res)
        bare.details = {}
        assert base_m_alphas(bare) == base_m_alphas(res)


# ======================================================================
class TestThereIsOneRoad:
    """Structural. The first case fails on v0.1.190 by the absence of a
    parameter (weak); the second is a GUARD that holds on both trees."""

    def test_the_base_load_takes_kv_by_name_and_without_a_default(self):
        """A default of 0.0 would recreate the defect for the next caller
        that forgets it — which is how D113's own function came to miss
        kv in the first place."""
        from ogr_slip2d.checks import _base_load_and_sigma
        par = inspect.signature(_base_load_and_sigma).parameters.get("kv")
        assert par is not None
        assert par.kind is inspect.Parameter.KEYWORD_ONLY
        assert par.default is inspect.Parameter.empty

    def test_the_checks_never_read_the_project(self):
        """No second copy: the coefficient reaches the check through the
        result and through nothing else."""
        tree = ast.parse(io.open(_ROOT / "ogr_slip2d" / "checks.py",
                                 encoding="utf-8").read())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        attrs = {n.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute)}
        assert "project" not in names
        assert "seismic" not in attrs
