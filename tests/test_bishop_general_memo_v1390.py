# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The passes of Bishop on a non-circular surface share what does not read F.

WHAT INVARIANT THIS PROTECTS.

V11 of the compute audit (v0.1.390). ``BishopSimplified._general_moment_fos``
iterates the factor of safety on a surface with no centre, and every pass
recomputed every slice: its loads, the envelope's linearisation, the
trigonometry, the support's load, the whole moment sum. Only m_alpha, Q and
the base normal read F. Tutorial 20 made 59 510 passes in 6573 calls, 31.9 s
of a 57.5 s run, its linearisation through a Generalized Anisotropic model
each time. Now the first pass keeps what does not read F, per slice, and
later passes form only those three, with the moment sum's geometry built
once (``moment_balance.moment_geometry``, v0.1.389). Tutorial 20 went from
58.9-60.9 s to 35.3-36.3 s (one fresh process per run, ABBA), every
evaluation identical. Class A: the same operations in the same order.

1. **A solve is v0.1.389's, to the bit.** That version's method is written
   out below, comments dropped, and both solve the same surfaces: dry, under
   a water table, with an earthquake, with an active and a passive support
   (the passive slices are computed whole every pass), with a curved
   envelope that the self-consistent passes re-linearise, with a Generalized
   Anisotropic material, and stopped by its pass budget. The factor, the
   counters, the reason, the three published columns and every detail are
   compared.
2. **The work is counted:** the envelope is linearised once per slice per
   solve, plus once per extra pass for each slice a passive support
   crosses; the moment geometry is built once per solve.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math


def _old_general_moment_fos(self, project, surface, slices, s_list, kh, kv,
                            slide_sign, sup):
    """``BishopSimplified._general_moment_fos`` of v0.1.389, comments
    dropped."""
    from ogr_slip2d import messages as msg
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.methods.base import (LEMResult, REASON_M_ALPHA_COLLAPSED,
                                         REASON_NON_PHYSICAL_FOS,
                                         REASON_NOT_CONVERGED,
                                         REASON_ZERO_DRIVING)
    from ogr_slip2d.methods.bishop import base_forces_no_interslice_shear
    from ogr_slip2d.moment_balance import axis_for, moment_terms
    from ogr_slip2d.support_integration import (support_failure_details,
                                                support_force_on_slice,
                                                support_moments,
                                                support_vertical_load)

    axis = axis_for(project, surface)
    fos = max(0.05, self.initial_fos)
    converged = False
    iterations = 0
    sigma_load = None
    support_force = None
    zero = []
    for it in range(1, self.max_iterations + 1):
        iterations = it
        forces = []
        weights = []
        resisting = []
        normals = []
        tangential = [0.0] * len(s_list) if sup.present else None
        tangential_passive = [0.0] * len(s_list) if sup.present else None
        sigma_load = [0.0] * len(s_list) if sup.present else None
        support_force = [None] * len(s_list) if sup.present else None
        zero = []
        for i_s, s in enumerate(s_list):
            f = slice_forces(s, kh, kv)
            w = f.w_total
            alpha = slide_sign * s.base_angle
            w_n = w
            if sup.present:
                load = support_vertical_load(
                    sup, i_s, s.base_angle, slide_sign, fos)
                w_n += load
                sigma_load[i_s] = load
                support_force[i_s] = list(support_force_on_slice(
                    sup, i_s, s.base_angle, slide_sign, fos))
            n_est = w_n * math.cos(s.base_angle)
            raw = n_est - s.pore_pressure * s.base_length
            sigma = max(0.0, raw)
            sigma /= max(s.base_length, 1e-9)
            imposed = self._imposed_stress(i_s)
            if imposed is not None:
                raw, sigma = imposed, max(0.0, imposed)
            c, tan_phi = self._local_c_phi(s, s.material, sigma)
            if raw < 0.0 and self._zero_strength(s, raw, c, tan_phi):
                zero.append(i_s)
            m_alpha = math.cos(alpha) + math.sin(alpha) * tan_phi / fos
            if abs(m_alpha) < 1e-6:
                return LEMResult(
                    fos=None, converged=False, iterations=iterations,
                    method_id=self.METHOD_ID, surface=surface,
                    slices=slices,
                    **msg.failure(msg.M_ALPHA_COLLAPSED, value=m_alpha,
                                  slice=s.index),
                    reason=REASON_M_ALPHA_COLLAPSED)
            q = (c * s.width
                 + (w_n - s.pore_pressure * s.width) * tan_phi) / m_alpha
            normal = ((w_n - (q / fos) * math.sin(alpha))
                      / max(math.cos(alpha), 1e-9))
            forces.append(f)
            weights.append(w)
            resisting.append(q)
            normals.append(normal)
            if tangential is not None:
                tangential[i_s] = sup.t_active[i_s]
                tangential_passive[i_s] = sup.t_passive[i_s]
        terms = moment_terms(
            axis, s_list, weights, resisting, normals, kh=kh, kv=kv,
            sup=sup if sup.present else None,
            tangential=tangential, tangential_passive=tangential_passive,
            forces=forces,
            couple=sup.couple if sup.present else 0.0)
        if abs(terms.driving) < 1e-9:
            return LEMResult(
                fos=None, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                **msg.failure(msg.ZERO_DRIVING_MOMENT),
                reason=REASON_ZERO_DRIVING)
        new_fos = -terms.shear / terms.driving
        if not math.isfinite(new_fos) or new_fos <= 0.0:
            return LEMResult(
                fos=None, converged=False, iterations=iterations,
                method_id=self.METHOD_ID, surface=surface, slices=slices,
                **msg.failure(msg.NON_PHYSICAL_FOS),
                reason=REASON_NON_PHYSICAL_FOS)
        if it > 1 and abs(new_fos - fos) < self.tolerance:
            fos = new_fos
            converged = True
            break
        fos = 0.5 * fos + 0.5 * new_fos
    pub_normals, pub_shears, pub_strengths = (
        base_forces_no_interslice_shear(
            s_list, kh, kv, slide_sign, fos,
            envelope_stress=self._envelope_stress,
            support_load=sigma_load))
    return LEMResult(
        fos=fos, converged=converged, iterations=iterations,
        method_id=self.METHOD_ID, surface=surface, slices=slices,
        base_normal_force=pub_normals,
        base_shear_force=pub_shears,
        base_shear_strength=pub_strengths,
        details=support_failure_details(sup, {
            "moment_axis": axis,
            "slide_sign": slide_sign,
            "m_alpha_sign": slide_sign,
            "kh": kh,
            "kv": kv,
            "sigma_support_load": sigma_load,
            "support_force": support_force,
            "support_moment": support_moments(sup, s_list),
            "zero_strength_slices": zero,
        }),
        **({} if converged else msg.failure(msg.NOT_CONVERGED)),
        reason="" if converged else REASON_NOT_CONVERGED,
    )


# ----------------------------------------------------------------------
def _slope(strength=None, water=False, supports=None):
    """A clay slope (optionally under a water table and with two
    tiebacks, the second of force application ``supports``) and a polyline
    surface through it."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, GroutedTiebackFriction,
                                  SupportInstance)
    from ogr_slip2d.surface import SlipSurface
    p = Project(name="bishop general memo")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                             Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay",
                 strength=strength or MohrCoulomb(cohesion=8.0,
                                                  friction_angle=24.0),
                 unit_weight=19.0, sat_unit_weight=20.5,
                 pore_pressure=(PorePressureType.WATER_TABLE if water
                                else PorePressureType.NONE))
    p.add_material(m)
    if water:
        wt = Boundary(polyline=Polyline(vertices=[Vertex(0, 14),
                                                  Vertex(50, 9)]),
                      btype=BoundaryType.WATER_TABLE)
        p.add_boundary(wt)
        m.water_surface_id = wt.id
    if supports is not None:
        st = GroutedTiebackFriction(
            adhesion=10.0, friction_angle_bond=30.0,
            bond_length_percent=60.0, grout_diameter=0.15,
            out_of_plane_spacing=1.5, tensile_capacity=1.0e3,
            plate_capacity=1.0e3)
        p.support_types.append(st)
        for k, (head, tail) in enumerate((((30.0, 20.0), (14.0, 14.0)),
                                          ((33.0, 17.0), (19.0, 11.0)))):
            p.supports.append(SupportInstance(
                type_id=st.TYPE_ID, head=Vertex(*head), tail=Vertex(*tail),
                force_application=(ForceApplication.ACTIVE if k == 0
                                   else supports)))
    surface = SlipSurface(polyline=Polyline(vertices=[
        Vertex(10.0, 25.0), Vertex(16.0, 15.0), Vertex(26.0, 9.5),
        Vertex(36.0, 10.5), Vertex(43.0, 15.0)], closed=False))
    return p, surface


def _anisotropic():
    from ogr_core.materials.builtin_models import (GeneralizedAnisotropic,
                                                   MohrCoulomb)
    soil = MohrCoulomb(cohesion=5.0, friction_angle=30.0).to_dict()
    bed = MohrCoulomb(cohesion=0.0, friction_angle=20.0).to_dict()
    return GeneralizedAnisotropic(rules=[
        {"model": soil, "angle_min": -90.0, "angle_max": -10.0},
        {"model": bed, "angle_min": -10.0, "angle_max": 10.0},
        {"model": dict(soil), "angle_min": 10.0, "angle_max": 90.0}])


def _published(res):
    def h(v):
        if isinstance(v, float):
            return v.hex()
        if isinstance(v, (list, tuple)):
            return tuple(h(x) for x in v)
        if isinstance(v, dict):
            return tuple((k, h(x)) for k, x in sorted(v.items()))
        return repr(v)
    return (h(res.fos), res.converged, res.iterations, res.reason,
            res.error_message, h(res.base_normal_force),
            h(res.base_shear_force), h(res.base_shear_strength),
            h(res.details or {}))


def _solve(p, surface, old=False, max_iterations=None):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, surface, num_slices=24)
    method = BishopSimplified()
    if max_iterations is not None:
        method.max_iterations = max_iterations
    real = BishopSimplified.__dict__["_general_moment_fos"]
    if old:
        BishopSimplified._general_moment_fos = _old_general_moment_fos
    try:
        return _published(method.compute_fos(p, surface, sl))
    finally:
        BishopSimplified._general_moment_fos = real


# ======================================================================
class TestASolveIsV0_1_389s:
    """Invariant 1."""

    def _same(self, p, surface, **kw):
        new = _solve(p, surface, **kw)
        old = _solve(p, surface, old=True, **kw)
        assert new == old
        return new

    def test_dry(self):
        got = self._same(*_slope())
        assert got[1] and got[2] > 2, "converged after several passes"

    def test_under_a_water_table_with_an_earthquake(self):
        p, surface = _slope(water=True)
        p.seismic.enabled = True
        p.seismic.kh = 0.12
        self._same(p, surface)

    def test_with_an_active_and_a_passive_support(self):
        from ogr_core.support import ForceApplication
        got = self._same(*_slope(water=True,
                                 supports=ForceApplication.PASSIVE))
        assert got[1]

    def test_with_two_active_supports(self):
        from ogr_core.support import ForceApplication
        self._same(*_slope(supports=ForceApplication.ACTIVE))

    def test_with_a_curved_envelope(self):
        """A power curve: the self-consistent passes re-linearise it at the
        solver's own stresses (``_imposed_stress``)."""
        from ogr_core.materials.builtin_models import PowerCurve
        self._same(*_slope(strength=PowerCurve(a=1.6, b=0.7, c=2.0, d=0.0,
                                               waviness=0.0), water=True))

    def test_with_a_generalized_anisotropic_material(self):
        self._same(*_slope(strength=_anisotropic()))

    def test_with_slices_entering_with_no_strength(self):
        """A power curve through the origin with a flat tangent there
        (c = d = 0, b > 1) and the water above the crest: the steep bases
        estimate a negative effective normal, are linearised at zero and
        enter with no strength (``zero_strength_slices``), a flag the memo
        has to repeat. Called directly, on the Fellenius estimate: the
        self-consistent passes re-linearise these bases where the solution
        puts them, which is not in tension here."""
        from ogr_core.geometry import BoundaryType, Polyline, Vertex
        from ogr_core.materials.builtin_models import PowerCurve
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms
        p, surface = _slope(strength=PowerCurve(a=0.05, b=1.5, c=0.0, d=0.0,
                                                waviness=0.0), water=True)
        wt = next(b for b in p.boundaries
                  if b.btype == BoundaryType.WATER_TABLE)
        wt.polyline = Polyline(vertices=[Vertex(0, 26.0), Vertex(50, 16.0)])
        sl = slice_surface(p, surface, num_slices=24)
        sup = resolve_support_terms(p, surface, sl, 1.0)
        args = (p, surface, sl, list(sl.slices), 0.0, 0.0, 1.0, sup)
        method = BishopSimplified()
        new = _published(method._general_moment_fos(*args))
        old = _published(_old_general_moment_fos(method, *args))
        assert new == old
        assert len(dict(new[8])["zero_strength_slices"]) > 1
        assert new[1] and new[2] > 2

    def test_every_slice_at_every_pass(self):
        """What each pass hands the moment sum, slice by slice: a factor of
        safety can swallow a last bit that moved in one slice (v0.1.384's
        lesson), so the resistances and normals of every pass are compared
        themselves, as hex, the old sum's arguments against the new one's."""
        import ogr_slip2d.moment_balance as MB
        p, surface = _slope(water=True)
        p.seismic.enabled = True
        p.seismic.kh = 0.12
        seen = {"old": [], "new": []}
        inside_old = []
        real_terms, real_at = MB.moment_terms, MB.moment_terms_at

        def terms(axis, s_list, weights, resisting, normals, **kw):
            seen["old"].append([(q.hex(), n.hex())
                                for q, n in zip(resisting, normals)])
            # the whole sum goes through ``moment_terms_at`` itself: not a
            # call of the new path, so not recorded as one
            inside_old.append(True)
            try:
                return real_terms(axis, s_list, weights, resisting, normals,
                                  **kw)
            finally:
                inside_old.pop()

        def at(geometry, resisting, normals):
            if not inside_old:
                seen["new"].append([(q.hex(), n.hex())
                                    for q, n in zip(resisting, normals)])
            return real_at(geometry, resisting, normals)

        MB.moment_terms, MB.moment_terms_at = terms, at
        try:
            _solve(p, surface)
            _solve(p, surface, old=True)
        finally:
            MB.moment_terms, MB.moment_terms_at = real_terms, real_at
        assert len(seen["new"]) > 3
        assert seen["new"] == seen["old"]

    def test_stopped_by_its_pass_budget(self):
        got = self._same(*_slope(water=True), max_iterations=3)
        assert not got[1] and got[2] == 3


# ======================================================================
class TestTheWorkIsCounted:
    """Invariant 2, against v0.1.389 on the same solve: the memo removes
    exactly the repeated linearisations, those of every pass after the
    first for each slice no passive support crosses. The linearisations
    outside the loop (the published columns) are the same on both sides."""

    def _count(self, p, surface, old=False):
        import ogr_slip2d.moment_balance as MB
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        sl = slice_surface(p, surface, num_slices=24)
        calls = {"lin": 0, "geom": 0, "solves": 0, "passes": 0}
        real_lin = BishopSimplified.__dict__["_local_c_phi"]
        real_geom = MB.moment_geometry
        real_gen = BishopSimplified.__dict__["_general_moment_fos"]
        inner = _old_general_moment_fos if old else real_gen

        def lin(*a, **k):
            calls["lin"] += 1
            return real_lin.__func__(*a, **k)

        def geom(*a, **k):
            calls["geom"] += 1
            return real_geom(*a, **k)

        def gen(self, *a, **k):
            calls["solves"] += 1
            res = inner(self, *a, **k)
            calls["passes"] += res.iterations
            return res

        BishopSimplified._local_c_phi = staticmethod(lin)
        BishopSimplified._general_moment_fos = gen
        MB.moment_geometry = geom
        try:
            BishopSimplified().compute_fos(p, surface, sl)
        finally:
            BishopSimplified._local_c_phi = real_lin
            BishopSimplified._general_moment_fos = real_gen
            MB.moment_geometry = real_geom
        return len(sl.slices), calls, sl

    def _check(self, p, surface, passive):
        n, new, _sl = self._count(p, surface)
        _n, old, _sl = self._count(p, surface, old=True)
        assert new["passes"] == old["passes"] > new["solves"], (new, old)
        assert new["solves"] == old["solves"]
        extra = new["passes"] - new["solves"]
        assert old["lin"] - new["lin"] == extra * (n - passive), (new, old)
        assert new["geom"] == new["solves"], new

    def test_without_supports(self):
        self._check(*_slope(water=True), passive=0)

    def test_a_passive_slice_is_computed_every_pass(self):
        from ogr_core.support import ForceApplication
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import resolve_support_terms
        p, surface = _slope(water=True, supports=ForceApplication.PASSIVE)
        sl = slice_surface(p, surface, num_slices=24)
        sup = resolve_support_terms(p, surface, sl, 1.0)
        passive = sum(1 for t in sup.t_passive if t)
        assert passive > 0, "no slice is crossed by the passive support"
        self._check(p, surface, passive)
