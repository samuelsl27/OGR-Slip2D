# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.22 — Interslice-force / line-of-thrust post-processor tests.

Validates ``ogr_slip2d.postprocess.compute_interslice_state`` on the
reference validation case:

    * Force-equilibrium methods (Spencer, GLE, Lowe-Karafiath, Janbu)
      must close the E-march (|E_n| / max|E| below 1 %).
    * Per-slice horizontal AND vertical equilibrium must hold exactly
      for every slice of the march (residuals ~ 0).
    * Free-end boundary conditions: E_0 = X_0 = 0.
    * The line of thrust must lie mostly within the slice heights.
    * Moment-only methods (Bishop) are allowed a non-zero closure but
      the state must still be marked ok and finite.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_slip2d import (  # noqa: E402
    BishopSimplified,
    GLEMorgensternPrice,
    LoweKarafiath,
    Spencer,
)
from ogr_slip2d.postprocess import compute_interslice_state  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

_REF_CIRCLE = dict(centre_x=88.0, centre_y=70.5, radius=47.212)


def _state_for(method):
    p = _ej1_project()
    ev = GridSearch(method=method, num_slices=25, min_area=0.0)
    res = ev.evaluate_circle(p, SlipCircle(**_REF_CIRCLE))
    assert res is not None and res.is_valid
    return res, compute_interslice_state(res)


class TestInterSliceClosure:
    def test_spencer_closes(self):
        _, st = _state_for(Spencer())
        assert st.ok
        assert st.relative_closure < 0.01, st.relative_closure

    def test_gle_closes(self):
        _, st = _state_for(GLEMorgensternPrice())
        assert st.ok
        assert st.relative_closure < 0.01, st.relative_closure

    def test_lowe_karafiath_closes(self):
        _, st = _state_for(LoweKarafiath())
        assert st.ok
        assert st.relative_closure < 0.01, st.relative_closure

    def test_bishop_state_ok_with_expected_nonclosure(self):
        _, st = _state_for(BishopSimplified())
        assert st.ok
        # Bishop does not satisfy horizontal equilibrium: closure is
        # non-zero, finite and reported (not hidden).
        assert math.isfinite(st.closure)
        assert st.e_max > 0


class TestInterSliceEquilibrium:
    def test_per_slice_equilibrium_exact(self):
        res, st = _state_for(Spencer())
        slist = list(res.slices)
        F = res.fos
        from ogr_slip2d.methods.bishop import BishopSimplified as B
        # Recompute residuals of both equations for every slice
        drive = sum(-s.weight * math.sin(s.base_angle) for s in slist)
        s_dir = -1.0 if drive > 0 else 1.0
        for i, s in enumerate(slist):
            alpha = s.base_angle
            l = s.base_length
            u = s.pore_pressure
            W = s.weight
            sigma_est = max(0.0, W * math.cos(alpha) - u * l) / max(l, 1e-9)
            c_loc, tan_phi = B._local_c_phi(s, s.material, sigma_est)
            S = (c_loc * l + (st.N[i] - u * l) * tan_phi) / F * s_dir
            tx, ty = math.cos(alpha), math.sin(alpha)
            nx, ny = -ty, tx
            rx = st.N[i] * nx + S * tx + st.E[i] - st.E[i + 1]
            ry = st.N[i] * ny + S * ty + st.X[i] - st.X[i + 1] - W
            scale = max(abs(W), 1.0)
            assert abs(rx) / scale < 1e-6, (i, rx)
            assert abs(ry) / scale < 1e-6, (i, ry)

    def test_free_end_boundary_conditions(self):
        _, st = _state_for(LoweKarafiath())
        assert st.E[0] == 0.0 and st.X[0] == 0.0

    def test_thrust_mostly_within_slices(self):
        res, st = _state_for(Spencer())
        slist = list(res.slices)
        inside = total = 0
        for i in range(1, len(slist)):
            if abs(st.E[i]) < 1e-6:
                continue
            total += 1
            yb = slist[i].base_y_left
            yt = slist[i].top_y_left
            if yb - 0.5 <= st.y_thrust[i] <= yt + 0.5:
                inside += 1
        assert total > 0
        assert inside / total > 0.8, (inside, total)


class TestDetailsField:
    def test_rigorous_methods_store_boundary_ratios(self):
        for m in (Spencer(), GLEMorgensternPrice(), LoweKarafiath()):
            res, _ = _state_for(m)
            ratios = res.details.get("boundary_ratios")
            assert ratios is not None
            assert len(ratios) == len(list(res.slices)) + 1

    def test_no_ratios_defaults_to_zero_x(self):
        _, st = _state_for(BishopSimplified())
        # Bishop assumes X = 0 → every X value must be exactly zero.
        assert all(x == 0.0 for x in st.X)


class TestTensileAdmissibilityFilter:
    """v0.1.24 — the optional interslice-tension filter (anomaly A3).

    A physically acceptable mechanism needs COMPRESSIVE interslice
    forces. The degenerate surface below (a deep wedge closed by a
    near-vertical +73.6 deg rising segment, found by Block Search on the
    reference model) reports FoS ~0.68 with every method, yet its force
    field requires large interslice tension, so it is not a feasible
    mechanism.
    """

    _DEGENERATE = [(29.1, 50.0), (47.5, 31.9), (69.8, 8.1),
                   (72.8, 18.4), (79.5, 25.0)]
    _HEALTHY = [(32.6, 50.0), (50.2, 32.6), (59.3, 23.9),
                (74.3, 15.9), (83.5, 25.0)]

    def _eval(self, pts, **kw):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d import Spencer
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipSurface
        p = _ej1_project()
        surf = SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False))
        ev = GridSearch(method=Spencer(), num_slices=18, min_area=0.0, **kw)
        return ev.evaluate_surface(p, surf)

    def test_degenerate_surface_requires_tension(self):
        res = self._eval(self._DEGENERATE)
        assert res is not None
        st = compute_interslice_state(res)
        interior = st.E[1:-1]
        assert min(interior) < -0.05 * st.e_max, min(interior)

    def test_healthy_surface_essentially_compressive(self):
        res = self._eval(self._HEALTHY)
        st = compute_interslice_state(res)
        interior = st.E[1:-1]
        assert min(interior) >= -0.05 * st.e_max, min(interior)

    def test_filter_rejects_degenerate_keeps_healthy(self):
        """v0.1.32 — the admissibility filter became a POST-filter: the
        surface keeps its converged factor of safety and stays in the
        evaluation list, but is flagged ``admissible = False`` so it is
        never reported as the critical surface. It is therefore no longer
        correct to expect ``None`` here.

        The interslice-tension criterion of v0.1.24 was also superseded
        by the reference's own checks (base tensile stress and m_alpha);
        the degenerate surface is caught by the latter, so this test now
        exercises the m_alpha route.
        """
        deg = self._eval(self._DEGENERATE, check_m_alpha=True)
        healthy = self._eval(self._HEALTHY, check_m_alpha=True)
        assert deg is not None and deg.admissible is False
        assert healthy is not None and healthy.admissible is True

    def test_filter_off_by_default(self):
        from ogr_slip2d import Spencer
        from ogr_slip2d.search import BlockSearch, GridSearch
        assert GridSearch(method=Spencer()).reject_tensile is False
        assert BlockSearch(method=Spencer()).reject_tensile is False

    def test_filter_forwarded_by_all_searches(self):
        from ogr_slip2d import Spencer
        from ogr_slip2d.search import (
            BlockSearch, GridSearch, PathSearch, SimulatedAnnealingSearch,
        )
        for cls in (GridSearch, BlockSearch, PathSearch,
                    SimulatedAnnealingSearch):
            s = cls(method=Spencer(), reject_tensile=True)
            assert s.reject_tensile is True, cls.__name__
