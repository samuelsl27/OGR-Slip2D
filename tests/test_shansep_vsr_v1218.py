# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.218 — SHANSEP and Vertical Stress Ratio are the formulations the
reference documents (defect D207 of the verification bank).

THREE DEFECTS OF ONE FAMILY, the vertical effective stress the two models
read:

1. SHANSEP took ``max(σ'v·S·OCR^m, su_min)``; the published formula is
   ``τ = A + σ'v·S·(OCR)^m`` with A, "the minimum undrained shear strength",
   ADDED. Now ``A`` is a parameter of its own, added, and ``su_min`` stays the
   floor it was (decision of the owner): an existing project keeps its number.
2. With σ'v ≤ 0 (an artesian column) SHANSEP switched in silence to
   ``su(σ'ₙ)``, a frictional soil with tan φ = S·OCR^m. Now the formula is
   evaluated at zero: τ = max(A, su_min).
3. Vertical Stress Ratio asked for no context and multiplied K by σ'ₙ, so it
   was a frictional soil through the origin (and φ-only for Janbu's b1). The
   reference computes the stress "from the total weight of each slice, and
   the pore pressure acting at the center of the base"; now it reads the
   context's σ'v, as SHANSEP does, and Janbu classes it as c-only.

THE REFERENCES (rule 1):

* the published formula, written by hand;
* an identity: on a slope where every base has σ'v ≤ 0, SHANSEP with A is
  the published formula at zero, τ = A, which IS an undrained soil with
  cu = A: the nine methods must return that soil's factor;
* an identity: with B-bar = 1 an undrained load leaves σ'v where it was
  (Skempton 1954; the reference's own excess-pore-pressure example keeps
  σ'v at 1872 before and after a drawdown), so SHANSEP must see the same
  σ'v under the load as without it;
* Terzaghi under a reservoir, σ'v = γ'·h, for Vertical Stress Ratio as
  v0.1.214 (D166) pinned it for SHANSEP;
* Janbu (1973): f0 = 1 + 0.69·[(d/L) − 1.4(d/L)²] for a c-only soil.

What does NOT move: every model without SHANSEP or Vertical Stress Ratio,
and SHANSEP with A = 0 and σ'v > 0, bit for bit; the verification bank,
which has neither model (0 of 7995 .ogr).
"""
from __future__ import annotations

import math

S_RATIO, M_EXP = 0.25, 0.8
GAMMA, GAMMA_W = 20.0, 9.81

_CACHE: dict = {}


# ======================================================================
def _ctx(sigma_v):
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(sigma_v_eff=sigma_v)


def _shansep(**kw):
    from ogr_core.materials.builtin_models import SHANSEP
    p = dict(S=S_RATIO, m=M_EXP, OCR=1.0)
    p.update(kw)
    return SHANSEP(**p)


def _vsr(**kw):
    from ogr_core.materials.builtin_models import VerticalStressRatio
    return VerticalStressRatio(**kw)


def _slope(strength, ru=None):
    """A 1V:1.67H slope, 12 m high, on a 10 m foundation; dry, or with a
    pore-pressure coefficient everywhere."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("d207")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="clay", unit_weight=GAMMA, sat_unit_weight=GAMMA,
                   strength=strength)
    if ru is not None:
        mat.pore_pressure = PorePressureType.RU_COEFFICIENT
        mat.ru = ru
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30


def _slices(project):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    sl = slice_surface(project, SlipCircle(*CIRCLE), num_slices=N_SLICES)
    assert sl is not None
    return sl


def _solve(key, strength, method_id, ru=None):
    k = (key, method_id, ru)
    if k not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.surface import SlipCircle
        p = _slope(strength, ru)
        _CACHE[k] = method_registry()[method_id]().compute_fos(
            p, SlipCircle(*CIRCLE), _slices(p))
    return _CACHE[k]


def _nine():
    from ogr_slip2d.methods import method_registry
    ids = sorted(method_registry())
    assert len(ids) == 9, ids
    return ids


# ======================================================================
class TestTheSHANSEPFormula:

    def test_A_is_added(self):
        """τ = A + σ'v·S·OCR^m, the published formula, by hand."""
        m = _shansep(OCR=4.0, A=12.0)
        want = 12.0 + 100.0 * S_RATIO * 4.0 ** M_EXP
        got = m.shear_strength_ctx(0.0, _ctx(100.0))
        assert math.isclose(got, want, rel_tol=1e-12), (got, want)

    def test_su_min_is_still_the_floor(self):
        m = _shansep(A=3.0, su_min=10.0)
        assert m.shear_strength_ctx(0.0, _ctx(1.0)) == 10.0
        assert math.isclose(m.shear_strength_ctx(0.0, _ctx(200.0)),
                            3.0 + 200.0 * S_RATIO, rel_tol=1e-12)

    def test_A_zero_is_the_old_formula_bit_for_bit(self):
        m = _shansep(OCR=2.0, su_min=4.0)
        for sv in (0.5, 7.0, 31.4159, 250.0):
            old = max(max(sv, 0.0) * S_RATIO * (max(2.0, 1e-6) ** M_EXP),
                      4.0)
            assert m.shear_strength_ctx(0.0, _ctx(sv)) == old, sv

    def test_A_moves_the_factor(self):
        """Rule 7, A on its own."""
        for mid in ("bishop_simplified", "spencer"):
            a = _solve("A0", _shansep(), mid).fos
            b = _solve("A20", _shansep(A=20.0), mid).fos
            assert b > a * 1.01, (mid, a, b)

    def test_su_min_moves_the_factor(self):
        """Rule 7, the floor on its own: near the toe and the crest the
        column is short and σ'v·S falls under 15 kPa."""
        a = _solve("A0", _shansep(), "bishop_simplified").fos
        b = _solve("floor15", _shansep(su_min=15.0),
                   "bishop_simplified").fos
        assert b > a * 1.001, (a, b)


class TestAnArtesianColumn:
    """ru = 1.2 everywhere: u > σv at every base, the context clips σ'v at
    zero, and the published formula there is τ = A."""

    RU = 1.2

    def test_every_base_is_artesian(self):
        sl = _slices(_slope(_shansep(A=20.0), ru=self.RU))
        for s in sl.slices:
            assert s.pore_pressure > s.weight / s.width, s.index

    def test_the_strength_is_A_and_not_friction(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        sl = _slices(_slope(_shansep(A=20.0), ru=self.RU))
        for s in sl.slices:
            c, tan_phi = BishopSimplified._local_c_phi(s, s.material, 30.0)
            assert c == 20.0 and tan_phi == 0.0, (s.index, c, tan_phi)

    def test_it_is_an_undrained_soil_of_cu_A_in_the_nine_methods(self):
        """Identity: SHANSEP at σ'v = 0 is τ = A, a φ = 0 soil."""
        from ogr_core.materials import Undrained
        bad = []
        for mid in _nine():
            a = _solve("artesian", _shansep(A=20.0), mid, ru=self.RU).fos
            b = _solve("cu20", Undrained(cohesion=20.0), mid,
                       ru=self.RU).fos
            if a is None or b is None or not math.isclose(a, b,
                                                          rel_tol=1e-12):
                bad.append((mid, a, b))
        assert not bad, bad

    def test_with_nothing_to_add_the_slice_is_reported(self):
        """A = su_min = 0 leaves no strength at all; the zero-strength note
        has to say so. It probes the vertical stress too, since varying
        σ'ₙ cannot show that the soil has strength elsewhere."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        sl = _slices(_slope(_shansep(), ru=self.RU))
        flagged = 0
        for s in sl.slices:
            c, tan_phi = BishopSimplified._local_c_phi(s, s.material, 0.0)
            assert c == 0.0 and tan_phi == 0.0, (s.index, c, tan_phi)
            flagged += BishopSimplified._zero_strength(s, -1.0, c, tan_phi)
        assert flagged == len(sl.slices), flagged

    def test_with_A_nothing_is_reported(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        sl = _slices(_slope(_shansep(A=5.0), ru=self.RU))
        for s in sl.slices:
            c, tan_phi = BishopSimplified._local_c_phi(s, s.material, 0.0)
            assert not BishopSimplified._zero_strength(s, -1.0, c, tan_phi)


class TestAnUndrainedLoadDoesNotConsolidate:
    """B-bar = 1: a vertical load raises σv and u by the same q, so the
    σ'v SHANSEP reads under it is the σ'v without it."""

    Q = 50.0

    def _block(self, loaded, b_bar):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.loads import DistributedLoad
        from ogr_core.loads.loads import LoadOrientation
        from ogr_core.materials import Material
        from ogr_core.project import Project
        ext = Polyline(vertices=[Vertex(0, 0), Vertex(100, 0),
                                 Vertex(100, 30), Vertex(0, 30)], closed=True)
        ext.ensure_ccw()
        p = Project("column")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        m = Material(name="clay", unit_weight=GAMMA, strength=_shansep())
        m.b_bar = b_bar
        p.materials = [m]
        p.settings.groundwater.set_advanced_option("excess_pore_pressure")
        if loaded:
            p.distributed_loads.append(DistributedLoad(
                start=Vertex(10.0, 30.0), end=Vertex(90.0, 30.0),
                magnitude_1=self.Q, orientation=LoadOrientation.VERTICAL,
                creates_excess_pore_pressure=True))
        return p

    def _sigma_v(self, project):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        sl = slice_surface(project, SlipCircle(centre_x=35.0, centre_y=42.0,
                                               radius=35.0), num_slices=25)
        out = []
        for s in sl.slices:
            c, _t = BishopSimplified._local_c_phi(s, s.material, 30.0)
            out.append((s.x_centre, c / S_RATIO))
        return out

    def test_the_load_leaves_sigma_v_where_it_was(self):
        bare = self._sigma_v(self._block(False, 1.0))
        loaded = self._sigma_v(self._block(True, 1.0))
        under = 0
        for (x, a), (_x, b) in zip(bare, loaded):
            if 10.0 < x < 90.0:
                under += 1
            assert math.isclose(a, b, rel_tol=1e-12), (x, a, b)
        assert under >= 10, under

    def test_drained_it_adds_q(self):
        """Control: with B-bar = 0 the same load consolidates fully."""
        bare = self._sigma_v(self._block(False, 0.0))
        loaded = self._sigma_v(self._block(True, 0.0))
        for (x, a), (_x, b) in zip(bare, loaded):
            if 10.0 < x < 90.0:
                assert math.isclose(b - a, self.Q, rel_tol=1e-9), (x, a, b)


# ======================================================================
class TestVerticalStressRatioReadsSigmaV:

    K = 0.3

    def test_it_asks_for_a_context(self):
        assert _vsr().needs_context is True

    def test_the_strength_does_not_depend_on_sigma_n(self):
        m = _vsr(K=self.K)
        a = m.shear_strength_ctx(10.0, _ctx(80.0))
        b = m.shear_strength_ctx(300.0, _ctx(80.0))
        assert a == b == self.K * 80.0, (a, b)

    def test_min_strength_is_a_floor(self):
        m = _vsr(K=self.K, min_strength=30.0)
        assert m.shear_strength_ctx(0.0, _ctx(50.0)) == 30.0
        assert m.shear_strength_ctx(0.0, _ctx(-5.0)) == 30.0

    def test_on_a_slice_it_is_a_cohesion_of_K_times_sigma_v(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        sl = _slices(_slope(_vsr(K=self.K)))
        for s in sl.slices:
            c, tan_phi = BishopSimplified._local_c_phi(s, s.material, 40.0)
            want = self.K * max(s.weight / max(s.width, 1e-9), 0.0)
            assert tan_phi == 0.0, (s.index, tan_phi)
            assert math.isclose(c, want, rel_tol=1e-12, abs_tol=1e-12), (
                s.index, c, want)

    def test_under_a_reservoir_it_reads_the_buoyant_column(self):
        """Terzaghi, as D166 pinned it for SHANSEP: the dam face of
        ``test_sigma_v_ponded_v1214`` under 72 m of water."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, PorePressureType
        from ogr_core.project import Project
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        ext = Polyline(vertices=[Vertex(0, 0), Vertex(260, 0),
                                 Vertex(260, 78), Vertex(205, 78),
                                 Vertex(145, 58)], closed=True)
        ext.ensure_ccw()
        p = Project("ponded-vsr")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(-5, 72.0), Vertex(265, 72.0)], closed=False),
            btype=BoundaryType.WATER_TABLE))
        p.materials = [Material(
            name="clay", unit_weight=GAMMA, sat_unit_weight=GAMMA,
            strength=_vsr(K=self.K),
            pore_pressure=PorePressureType.WATER_TABLE)]
        p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
        sl = slice_surface(p, SlipCircle(centre_x=52.0, centre_y=186.0,
                                         radius=158.2), num_slices=25)
        seen = 0
        for s in sl.slices:
            mid = 0.5 * (s.top_y_left + s.top_y_right)
            straight = s.top_y_mean is None or abs(s.top_y_mean - mid) < 1e-9
            if not (max(s.top_y_left, s.top_y_right) < 72.0 and straight):
                continue
            seen += 1
            c, _t = BishopSimplified._local_c_phi(s, s.material, 50.0)
            want = (GAMMA - GAMMA_W) * s.height
            assert math.isclose(c / self.K, want, rel_tol=1e-9), (
                s.index, c / self.K, want)
        assert seen >= 5, seen

    def test_the_context_moves_the_factor(self):
        """Rule 7: until v0.1.218 the model WAS Mohr-Coulomb with c = 0 and
        tan φ = K; reading σ'v it is a different soil."""
        from ogr_core.materials import MohrCoulomb
        for mid in ("bishop_simplified", "spencer"):
            a = _solve("vsr", _vsr(K=self.K), mid).fos
            b = _solve("old-vsr", MohrCoulomb(
                cohesion=0.0, friction_angle=math.degrees(math.atan(self.K))),
                mid).fos
            assert abs(a - b) > 1e-3 * b, (mid, a, b)

    def test_a_support_reads_it_as_a_cohesion_too(self):
        """``bond.equivalent_c_phi_at`` (Ito-Matsui piles, helical plates)
        linearises at σ'v: the pair is (K·σ'v, 0) now, not (0, atan K)."""
        from ogr_core.support.bond import equivalent_c_phi_at
        p = _slope(_vsr(K=self.K))
        c, tan_phi = equivalent_c_phi_at(p, 40.0, -5.0, sigma_v_eff=80.0)
        assert math.isclose(c, self.K * 80.0, rel_tol=1e-12), c
        assert tan_phi == 0.0, tan_phi


class TestJanbuReadsItAsCOnly:

    def _shape_term(self, slices):
        """``(d/L) − 1.4·(d/L)²`` from the base vertices, written out."""
        s_list = list(slices)
        x0, y0 = s_list[0].base_x_left, s_list[0].base_y_left
        x1, y1 = s_list[-1].base_x_right, s_list[-1].base_y_right
        length = math.hypot(x1 - x0, y1 - y0)
        pts = [(x0, y0)] + [(s.base_x_right, s.base_y_right) for s in s_list]
        d = max(abs((y1 - y0) * (px - x0) - (x1 - x0) * (py - y0)) / length
                for px, py in pts)
        r = d / length
        return r - 1.4 * r * r

    def test_the_type_is_c(self):
        from ogr_core.materials import Material
        from ogr_slip2d.methods.janbu import base_soil_type
        assert base_soil_type(Material(name="v", strength=_vsr())) == "c"
        assert base_soil_type(Material(name="s", strength=_shansep())) == "c"

    def test_corrected_is_simplified_times_f0_of_c(self):
        simp = _solve("vsr", _vsr(K=0.3), "janbu_simplified")
        corr = _solve("vsr", _vsr(K=0.3), "janbu_corrected")
        f0 = 1.0 + 0.69 * self._shape_term(corr.slices)
        assert (corr.details or {}).get("janbu_b1") == 0.69
        assert math.isclose(corr.fos, simp.fos * f0, rel_tol=1e-12), (
            corr.fos, simp.fos, f0)
