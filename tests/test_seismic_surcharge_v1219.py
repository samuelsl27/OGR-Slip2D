# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.219 — the pseudo-static seismic force acts on the SOIL of each slice,
not on the surcharge the slicer folds into its weight (defect D206 of the
verification bank); and ``kh`` is a magnitude, applied the same way by every
method and refused below zero (entered in D206, same class).

THE DEFECT. The slicer adds to each slice's ``weight`` the distributed
surcharge and the vertical component of line loads, and ``slice_forces``
applied ``W·(1 + kv)`` and ``kh·W`` to that sum, so a surcharge was
accelerated like soil. The reference documentation defines the seismic force
as "Seismic Coefficient × area of slice × Unit Weight of slice material" and
its distributed loads as tractions; Duncan, Wright & Brandon (2014, §10.1)
put the force at the centre of gravity of the sliding SOIL mass (Terzaghi
1950); and OGR's own ``seismic_delta_sigma_v`` said the surcharge was not
accelerated, "with the same convention ``slice_forces`` uses". Decision of
the owner (2026-09-28): soil only, no per-load attribute; a fill with mass is
drawn as a material.

And kh < 0: the moment sums on a circle of Bishop and of Spencer/GLE skipped
a negative coefficient (``if kh > 0``) while every force sum applied it, and
the shared rule let one in. kh is the MAGNITUDE of a force that every method
applies in the sliding sense of its surface ("always POSITIVE" in the
reference; ``0.5·α·S`` in EN 1998-5, which gives both signs to the vertical
coefficient only), so the input refuses it, and the engine applies whatever
reaches it the same way everywhere.

THE REFERENCES (rule 1):

* the closed-form pseudo-static wedge on a plane (Kramer 1996, §10.6.1) with
  a vertical surcharge Q on the crest that carries no inertia:

      F = [c·L + ((W(1+kv) + Q)·cos β − kh·W·sin β)·tan φ]
          / [(W(1+kv) + Q)·sin β + kh·W·cos β],

  which the four methods that close force equilibrium on a plane reproduce
  (the wedge of ``test_seismic_convention_v1214``);
* an identity: on a circle through an undrained soil every term that carries
  kh is linear in it and nothing else does, so 1/F(kh) + 1/F(−kh) = 2/F(0)
  for any method whose factor is the moment balance (Bishop, the Ordinary
  Method, Spencer, GLE) and for Janbu's force balance.

What does NOT move: a model without loads or without earthquake, bit for bit
(``kv = 0`` gives the weight itself; no load gives ``soil_weight == weight``);
the verification bank, where none of the seven models with the earthquake on
carries a load and none has kh < 0.
"""
from __future__ import annotations

import math

H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
BETA = 40.0
NSLICES = 50
Q_KPA = 25.0
WEDGE_METHODS = ("janbu_simplified", "corps_engineers_1",
                 "corps_engineers_2", "lowe_karafiath")
WEDGE_TOL = {"janbu_simplified": 1e-11}
WEDGE_TOL_DEFAULT = 1e-8
SHAKES = ((0.0, 0.2), (0.0, -0.2), (0.15, 0.1), (0.15, -0.1), (0.1, 0.0))

OUTLINE_21 = ((0, 0), (120, 0), (120, 40), (70, 40), (30, 20), (0, 20))
CIRCLE_21 = (55.0, 62.0, 48.0)

_CACHE: dict = {}


# ======================================================================
def _daylight_x():
    return TOE + H / math.tan(math.radians(BETA))


def _wedge_project(kh, kv, q=Q_KPA):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.loads import DistributedLoad
    from ogr_core.loads.loads import LoadOrientation
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("surcharged wedge")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    if q:
        p.distributed_loads.append(DistributedLoad(
            start=Vertex(CREST, H), end=Vertex(60.0, H), magnitude_1=q,
            orientation=LoadOrientation.VERTICAL))
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh, p.seismic.kv = kh, kv
    return p


def _plane():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(), H)]))


def _slices(project, surface, n=NSLICES):
    from ogr_slip2d.slicer import slice_surface
    return slice_surface(project, surface, num_slices=n)


def _surcharge_on_the_wedge():
    """Q as the slicer applied it: ``surface_pressure·width`` per slice,
    a field every version has, so the closed form is exact wherever the
    load's edge falls."""
    sl = _slices(_wedge_project(0.0, 0.0), _plane())
    return sum(s.surface_pressure * s.width for s in sl.slices)


def _closed_wedge(kh, kv, q_force, inertial_load=False):
    """The pseudo-static Coulomb wedge with a vertical surcharge.

    ``inertial_load`` accelerates the surcharge like soil: the convention
    before v0.1.219, and the switch-off path."""
    w = GAMMA * 0.5 * H * (_daylight_x() - CREST)
    length = math.hypot(_daylight_x() - TOE, H)
    b = math.radians(BETA)
    t = math.tan(math.radians(PHI))
    if inertial_load:
        w, q_force = w + q_force, 0.0
    v = w * (1.0 + kv) + q_force
    return ((COH * length + (v * math.cos(b) - kh * w * math.sin(b)) * t)
            / (v * math.sin(b) + kh * w * math.cos(b)))


def _solve(method_id, project, surface, n, tolerance=1e-12):
    from ogr_slip2d.methods import method_registry
    sl = _slices(project, surface, n)
    m = method_registry()[method_id]()
    m.tolerance = tolerance
    res = m.compute_fos(project, surface, sl)
    assert res.fos is not None, (method_id, res.reason, res.error_message)
    return res


def _wedge_fos(method_id, kh, kv):
    key = ("wedge", method_id, kh, kv)
    if key not in _CACHE:
        _CACHE[key] = _solve(method_id, _wedge_project(kh, kv), _plane(),
                             NSLICES).fos
    return _CACHE[key]


class _Switch:
    """``external_forces.SEISMIC_SOIL_ONLY`` for one block, restored even if
    the block fails (the runner does not run teardown methods)."""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        from ogr_slip2d import external_forces
        self.old = external_forces.SEISMIC_SOIL_ONLY
        external_forces.SEISMIC_SOIL_ONLY = self.value
        return self

    def __exit__(self, *exc):
        from ogr_slip2d import external_forces
        external_forces.SEISMIC_SOIL_ONLY = self.old
        return False


# ======================================================================
class TestTheSurchargedWedge:
    """Anchor 1: the closed-form wedge with a surcharge that has no mass."""

    def test_the_fixture_carries_the_load(self):
        """The surcharge is on the wedge, and about the size of the strip
        it covers. Not equal to it: the slicer reads the load at each
        slice's centre, which moves Q by 0.14 % here, and that is why the
        closed form above is fed the Q the slicer applied."""
        q = _surcharge_on_the_wedge()
        expected = Q_KPA * (_daylight_x() - CREST)
        assert q > 0.0 and math.isclose(q, expected, rel_tol=1e-2), (
            q, expected)

    def test_no_shaking_is_the_static_surcharged_wedge(self):
        expected = _closed_wedge(0.0, 0.0, _surcharge_on_the_wedge())
        for mid in WEDGE_METHODS:
            got = _wedge_fos(mid, 0.0, 0.0)
            tol = WEDGE_TOL.get(mid, WEDGE_TOL_DEFAULT)
            assert abs(got / expected - 1.0) < tol, (mid, got, expected)

    def test_the_earthquake_moves_the_soil_and_not_the_load(self):
        q = _surcharge_on_the_wedge()
        bad = []
        for kh, kv in SHAKES:
            expected = _closed_wedge(kh, kv, q)
            for mid in WEDGE_METHODS:
                got = _wedge_fos(mid, kh, kv)
                tol = WEDGE_TOL.get(mid, WEDGE_TOL_DEFAULT)
                if abs(got / expected - 1.0) >= tol:
                    bad.append((mid, kh, kv, got / expected - 1.0))
        assert not bad, bad

    def test_the_switch_off_accelerates_the_load(self):
        """Rule 7, and the old convention as an identity: off, the wedge is
        the one whose surcharge is soil."""
        q = _surcharge_on_the_wedge()
        kh, kv = 0.15, 0.1
        with _Switch(False):
            off = _solve("janbu_simplified", _wedge_project(kh, kv),
                         _plane(), NSLICES).fos
        on = _wedge_fos("janbu_simplified", kh, kv)
        old = _closed_wedge(kh, kv, q, inertial_load=True)
        assert abs(off / old - 1.0) < 1e-11, (off, old)
        assert abs(on - off) > 1e-3 * on, (on, off)


class TestTheSliceForces:

    def test_the_soil_is_kept_apart(self):
        from ogr_slip2d.external_forces import slice_forces
        sl = _slices(_wedge_project(0.15, 0.1), _plane())
        loaded = 0
        for s in sl.slices:
            load = s.surface_pressure * s.width
            assert math.isclose(s.weight - s.soil_weight, load,
                                rel_tol=1e-9, abs_tol=1e-9), s.index
            f = slice_forces(s, 0.15, 0.1)
            assert f.h_seismic == 0.15 * s.soil_weight, s.index
            assert math.isclose(f.w_soil, s.soil_weight * 1.1 + load,
                                rel_tol=1e-12), s.index
            loaded += load > 0.0
        assert loaded >= 5, loaded

    def test_with_kv_zero_the_weight_is_untouched(self):
        from ogr_slip2d.external_forces import slice_forces
        sl = _slices(_wedge_project(0.15, 0.0), _plane())
        for s in sl.slices:
            assert slice_forces(s, 0.15, 0.0).w_soil == s.weight, s.index

    def test_without_a_load_it_is_the_old_formula_bit_for_bit(self):
        from ogr_slip2d.external_forces import slice_forces
        sl = _slices(_wedge_project(0.15, 0.1, q=0.0), _plane())
        for s in sl.slices:
            f = slice_forces(s, 0.15, 0.1)
            assert s.soil_weight == s.weight, s.index
            assert f.w_soil == s.weight * (1.0 + 0.1), s.index
            assert f.h_seismic == 0.15 * s.weight, s.index

    def test_a_slice_built_by_hand_is_all_soil(self):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.slicer import Slice
        s = Slice(index=0, x_centre=0.5, width=1.0, base_x_left=0.0,
                  base_x_right=1.0, base_y_left=0.0, base_y_right=0.0,
                  base_angle=0.0, base_length=1.0, top_y_left=2.0,
                  top_y_right=2.0)
        s.weight = 40.0
        f = slice_forces(s, 0.2, 0.1)
        assert f.h_seismic == 0.2 * 40.0 and f.w_soil == 40.0 * 1.1


# ======================================================================
def _circle_project(kh):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, Undrained
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in OUTLINE_21],
                   closed=True)
    ext.ensure_ccw()
    p = Project("undrained-21")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="clay", unit_weight=20.0,
                            sat_unit_weight=20.0,
                            strength=Undrained(cohesion=40.0))]
    # Set on the model directly, past the rule: the engine has to apply
    # whatever reaches it the same way in every method.
    p.seismic.enabled = bool(kh)
    p.seismic.kh = kh
    return p


def _circle_fos(method_id, kh):
    key = ("circle", method_id, kh)
    if key not in _CACHE:
        from ogr_slip2d.surface import SlipCircle
        _CACHE[key] = _solve(method_id, _circle_project(kh),
                             SlipCircle(*CIRCLE_21), 25).fos
    return _CACHE[key]


class TestKhIsAMagnitude:

    KH = 0.1

    def test_the_rule_refuses_a_negative_kh_and_not_a_negative_kv(self):
        from ogr_core.project.rules import seismic_coefficient_refusal
        why = seismic_coefficient_refusal("kh", -0.1)
        assert why is not None and why.code == "seismic_kh_negative", why
        assert seismic_coefficient_refusal("kh", 0.0) is None
        assert seismic_coefficient_refusal("kv", -0.1) is None

    def test_the_api_refuses_it(self):
        from ogr_api import Workspace, call
        from ogr_api.errors import InvalidArgument
        ws = Workspace()
        pid = call(ws, "project_new", name="kh sign")["project_id"]
        try:
            call(ws, "seismic_set", project_id=pid, enabled=True, kh=-0.1)
        except InvalidArgument as exc:
            assert "must not be negative" in str(exc), str(exc)
        else:
            raise AssertionError("kh = -0.1 was accepted")

    def test_the_analysis_refuses_a_model_that_holds_one(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        problems = check_analysis_settings(_circle_project(-0.1))
        assert any("kh must not be negative" in s for s in problems), (
            problems)
        assert not any("kh" in s for s in check_analysis_settings(
            _circle_project(0.1))), "a positive kh was refused"

    def test_the_dialog_starts_at_zero_and_says_what_it_found(self):
        from PySide6.QtWidgets import QApplication, QLabel
        from ogr_core.loads import SeismicLoad
        from ogr_gui.dialogs.seismic_dialog import SeismicLoadDialog
        QApplication.instance() or QApplication([])
        dlg = SeismicLoadDialog(SeismicLoad(kh=-0.15, enabled=True))
        try:
            assert dlg.sb_kh.minimum() == 0.0
            texts = [w.text() for w in dlg.findChildren(QLabel)]
            assert any("-0.15" in t for t in texts), texts
        finally:
            dlg.deleteLater()

    def test_every_method_applies_a_negative_one_the_same_way(self):
        """1/F(kh) + 1/F(-kh) = 2/F(0) on an undrained circle: the kh terms
        are linear and nothing else depends on them. Until v0.1.219 Bishop
        and Spencer/GLE skipped a negative kh in the moment sum (F(-kh)
        came out as F(0)) while Janbu and the Ordinary Method applied it."""
        bad = []
        for mid, tol in (("bishop_simplified", 1e-12),
                         ("ordinary_fellenius", 1e-12),
                         ("janbu_simplified", 1e-12),
                         ("spencer", 1e-9), ("gle_morgenstern_price", 1e-9)):
            f0 = _circle_fos(mid, 0.0)
            fp, fm = _circle_fos(mid, self.KH), _circle_fos(mid, -self.KH)
            gap = (1.0 / fp + 1.0 / fm) * f0 / 2.0 - 1.0
            if not abs(gap) < tol or not fm > f0 > fp:
                bad.append((mid, fp, f0, fm, gap))
        assert not bad, bad
