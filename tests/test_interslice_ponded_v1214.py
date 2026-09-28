# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.214 — the interslice march of the interpretation carries the loads the
solver carried: the ponded water, and the earthquake it was run with
(defect D173 of the verification bank).

THE DEFECT. ``postprocess._march`` rebuilt each slice's load by hand as
``W·(1 − kv)`` with ``H = kh·W·(1 − kv)``: no ponded water (``water_weight``)
and no horizontal water force (``water_force_h``), the lineage of v0.1.61 and
D113 in a fourth place. Measured on the reservoir of
``test_m_alpha_ponded_v1188`` — about four times the soil weight in water on
the upstream face — the march returned EXACTLY the same N and E with the
water as without it. And the slice-data panel of the interpretation window
called it with no earthquake at all, while the line of thrust and the slice
plot passed the project's.

THE ANCHORS, identities of the march's own equations (none captured):

1. VERTICAL EQUILIBRIUM of each slice. With the inter-slice shear at zero —
   Bishop publishes no ``boundary_ratios`` — the march's N and S must hold the
   vertical load the solver applied:

       N·cos a + S·sin a = w_total      (S signed along the chord)

   with ``w_total`` from ``slice_forces``, soil and water, the same function
   every method calls.

2. HORIZONTAL EQUILIBRIUM of each slice: ``E_R − E_L = −N·sin a + S·cos a + H``
   with ``H`` the signed seismic force plus the horizontal water force.

3. Taking the water off the SAME slices moves N — the check the D173 record
   asked for, and the one that returned "identical" before.

4. The earthquake reaches the march from the RESULT: ``details["kh"]`` and
   ``details["kv"]`` are what the method applied, so a caller that has no
   project — the slice-data panel — still gets the right loads.
"""
from __future__ import annotations

import copy
import math

GAMMA_W = 9.81
GAMMA = 20.0
WATER_Y = 72.0
CIRCLE = dict(centre_x=52.0, centre_y=186.0, radius=158.2)
N_SLICES = 25

_CACHE: dict = {}


def _project(ponded=True, kh=0.0, kv=0.0):
    """The dam face of ``test_m_alpha_ponded_v1188``, Mohr-Coulomb c = 0."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(260, 0), Vertex(260, 78),
        Vertex(205, 78), Vertex(145, 58),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ponded-march")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if ponded:
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(-5, WATER_Y),
                                        Vertex(265, WATER_Y)], closed=False),
            btype=BoundaryType.WATER_TABLE))
    p.materials = [Material(
        name="fill", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0),
        pore_pressure=(PorePressureType.WATER_TABLE if ponded
                       else PorePressureType.NONE))]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.seismic.enabled = bool(kh or kv)
    p.seismic.kh = kh
    p.seismic.kv = kv
    return p


def _result(method_id="bishop_simplified", kh=0.0, kv=0.0):
    key = (method_id, kh, kv)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _project(True, kh, kv)
        surf = SlipCircle(**CIRCLE)
        sl = slice_surface(p, surf, num_slices=N_SLICES)
        res = method_registry()[method_id]().compute_fos(p, surf, sl)
        assert res.fos is not None, (method_id, res.error_message)
        _CACHE[key] = res
    return _CACHE[key]


def _signed_h(res, s, kh, kv):
    """The horizontal load of one slice as the march must apply it: the
    seismic force out of the slope plus the (already signed) water force."""
    from ogr_slip2d.external_forces import slice_forces
    f = slice_forces(s, kh, kv)
    drive = sum(-t.weight * math.sin(t.base_angle) for t in res.slices)
    h_dir = 1.0 if drive > 0 else -1.0
    return h_dir * f.h_seismic + f.h_water


# ======================================================================
class TestTheMarchCarriesTheWater:

    def test_there_is_water_to_carry(self):
        """The fixture is not dry: the water on the face outweighs the soil
        on the slices it covers, which is what makes the cases below able
        to see it."""
        res = _result()
        water = sum(s.water_weight for s in res.slices)
        soil = sum(s.weight for s in res.slices)
        assert water > soil, (water, soil)

    def test_vertical_equilibrium_holds_the_total_load(self):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.postprocess import compute_interslice_state
        res = _result()
        st = compute_interslice_state(res)
        assert st.ok
        bad = []
        for i, s in enumerate(res.slices):
            a = s.base_angle
            carried = st.N[i] * math.cos(a) + st.S[i] * math.sin(a)
            w = slice_forces(s).w_total
            if abs(carried - w) > 1e-9 * max(1.0, w):
                bad.append((i, carried, w, s.water_weight))
        assert not bad, bad[:3]

    def test_horizontal_equilibrium_holds_the_water_thrust(self):
        from ogr_slip2d.postprocess import compute_interslice_state
        res = _result()
        st = compute_interslice_state(res)
        bad = []
        for i, s in enumerate(res.slices):
            a = s.base_angle
            lhs = st.E[i + 1] - st.E[i]
            rhs = (-st.N[i] * math.sin(a) + st.S[i] * math.cos(a)
                   + _signed_h(res, s, 0.0, 0.0))
            if abs(lhs - rhs) > 1e-9 * max(1.0, abs(st.N[i])):
                bad.append((i, lhs, rhs))
        assert not bad, bad[:3]

    def test_taking_the_water_off_moves_the_normal(self):
        from ogr_slip2d.postprocess import compute_interslice_state
        res = _result()
        dry = copy.copy(res)
        dry_slices = copy.copy(res.slices)
        dry_slices.slices = []
        for s in res.slices:
            t = copy.copy(s)
            t.water_weight = 0.0
            t.water_force_h = 0.0
            t.water_force_h_moment = 0.0
            dry_slices.slices.append(t)
        dry.slices = dry_slices
        wet = compute_interslice_state(res)
        without = compute_interslice_state(dry)
        moved = [i for i, s in enumerate(res.slices)
                 if s.water_weight > 0.0
                 and abs(wet.N[i] - without.N[i]) > 1e-3 * abs(wet.N[i])]
        covered = [i for i, s in enumerate(res.slices) if s.water_weight > 0]
        assert covered and moved == covered, (moved, covered)


class TestTheEarthquakeComesFromTheResult:

    KH, KV = 0.1, 0.05

    def test_the_methods_publish_both_coefficients(self):
        for mid in ("bishop_simplified", "spencer"):
            d = _result(mid, self.KH, self.KV).details
            assert d.get("kh") == self.KH and d.get("kv") == self.KV, (mid, d)

    def test_a_caller_without_the_project_gets_the_applied_loads(self):
        from ogr_slip2d.postprocess import compute_interslice_state
        res = _result("bishop_simplified", self.KH, self.KV)
        implicit = compute_interslice_state(res)
        explicit = compute_interslice_state(res, kh=self.KH, kv=self.KV)
        assert implicit.ok and explicit.ok
        assert implicit.N == explicit.N and implicit.E == explicit.E

    def test_and_the_march_holds_them(self):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.postprocess import compute_interslice_state
        res = _result("bishop_simplified", self.KH, self.KV)
        st = compute_interslice_state(res)
        bad = []
        for i, s in enumerate(res.slices):
            a = s.base_angle
            carried = st.N[i] * math.cos(a) + st.S[i] * math.sin(a)
            w = slice_forces(s, self.KH, self.KV).w_total
            if abs(carried - w) > 1e-9 * max(1.0, w):
                bad.append((i, carried, w))
            lhs = st.E[i + 1] - st.E[i]
            rhs = (-st.N[i] * math.sin(a) + st.S[i] * math.cos(a)
                   + _signed_h(res, s, self.KH, self.KV))
            if abs(lhs - rhs) > 1e-9 * max(1.0, abs(st.N[i])):
                bad.append((i, "E", lhs, rhs))
        assert not bad, bad[:3]

    def test_the_slice_panel_reads_the_same_state(self):
        """The panel of the interpretation window has no project: it must
        get the earthquake the solver applied, not zero."""
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d.postprocess import compute_interslice_state
        res = copy.copy(_result("spencer", self.KH, self.KV))
        if hasattr(res, "_ogr_interslice_state"):
            del res._ogr_interslice_state
        panel = _SliceDataDock._inter_state(res)
        explicit = compute_interslice_state(res, kh=self.KH, kv=self.KV)
        assert panel is not None and panel.E == explicit.E, (
            panel and panel.E[:3], explicit.E[:3])


class TestTheMarchSlidesWhereTheMethodSlid:
    """With no inter-slice shear the march solves the method's own vertical
    equilibrium at the method's F, so its N IS the ``base_normal_force``
    Bishop and Janbu publish — but only if the shear points where the
    method's did. The march used to guess that sense from ``Σ W·sin α``,
    which is Bishop's sum and not Janbu's (``Σ w_total·tan α``)."""

    def test_on_the_reservoir_the_normal_is_the_methods(self):
        from ogr_slip2d.postprocess import compute_interslice_state
        for mid in ("bishop_simplified", "janbu_simplified"):
            res = _result(mid)
            st = compute_interslice_state(res)
            assert len(res.base_normal_force) == len(st.N), mid
            for i, (a, b) in enumerate(zip(st.N, res.base_normal_force)):
                assert abs(a - b) <= 1e-9 * max(1.0, abs(b)), (mid, i, a, b)

    # (base angle deg, soil weight, ponded water weight): the witness of
    # ``test_slide_sign_by_method_v1189``, a steep passive base with water
    # standing on it, where the two sums disagree.
    ROWS = ((-70.0, 100.0, 400.0), (20.0, 500.0, 0.0), (20.0, 500.0, 0.0))

    def _witness(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.slicer import Slice, Slices
        from ogr_slip2d.surface import SlipSurface
        mat = Material(name="S", unit_weight=20.0,
                       strength=MohrCoulomb(cohesion=10.0,
                                            friction_angle=30.0))
        slices, x, y = [], 0.0, 0.0
        for i, (deg, w, ww) in enumerate(self.ROWS):
            a = math.radians(deg)
            b = 2.0 if i == 0 else 4.0
            x2, y2 = x + b, y + b * math.tan(a)
            s = Slice(index=i, x_centre=x + 0.5 * b, width=b,
                      base_x_left=x, base_x_right=x2, base_y_left=y,
                      base_y_right=y2, base_angle=a,
                      base_length=math.hypot(b, y2 - y),
                      top_y_left=max(y, y2) + 5.0,
                      top_y_right=max(y, y2) + 5.0)
            s.weight, s.water_weight, s.material = w, ww, mat
            slices.append(s)
            x, y = x2, y2
        verts = [Vertex(slices[0].base_x_left, slices[0].base_y_left)]
        verts += [Vertex(s.base_x_right, s.base_y_right) for s in slices]
        surf = SlipSurface(polyline=Polyline(vertices=verts))
        return Project("witness"), surf, Slices(slices=slices)

    def test_where_janbu_slides_the_other_way(self):
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.postprocess import compute_interslice_state
        p, surf, sl = self._witness()
        res = method_registry()["janbu_simplified"]().compute_fos(p, surf, sl)
        assert res.fos is not None and res.fos > 0, res.error_message
        soil = sum(s.weight * math.sin(s.base_angle) for s in sl.slices)
        janbu = sum(slice_forces(s).w_total * math.tan(s.base_angle)
                    for s in sl.slices)
        # Guard on the guard: the fixture really disagrees.
        assert soil > 0.0 > janbu, (soil, janbu)
        assert res.details["slide_sign"] == -1.0
        st = compute_interslice_state(res)
        for i, (a, b) in enumerate(zip(st.N, res.base_normal_force)):
            assert abs(a - b) <= 1e-9 * max(1.0, abs(b)), (i, a, b)
