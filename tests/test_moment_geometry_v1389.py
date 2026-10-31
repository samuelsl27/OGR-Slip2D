# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The moment sum about an axis is built from a geometry summed once.

WHAT INVARIANT THIS PROTECTS.

V10 of the compute audit (v0.1.389). ``moment_balance.moment_terms`` sums
every moment about the axis of a surface with no centre: the arm of each
base, the weight, the normals, the shear and the external forces. The
moment branch of Spencer and GLE calls it at every pass of every lambda,
and only the normals and the resistance change between calls: bank 104
(Spencer, particle swarm) made 704 399 calls, 34.7 s of 115.5. Now
``moment_geometry`` sums what the iterate does not move, once per system,
and ``moment_terms_at`` adds the two sums that read it. Bank 104 went from
115.8-117.4 s to 93.6-94.6 s (one fresh process per run, ABBA), every
evaluation identical. Class A: the same products in the same order.

1. **The sum is v0.1.388's, to the bit.** That version's ``moment_terms``
   is written out below. Against it, ``moment_terms`` and
   ``moment_terms_at(moment_geometry(...))`` give the same five sums for
   slices of every orientation, with water, an earthquake, a support's
   normal part and couples, active and passive tangential forces (zeros
   among them), the rotation given or not, the forces given or not.
2. **A Spencer and a GLE solve on a polyline are v0.1.388's:** each method
   run once on the new path and once with the full sum on every call (the
   reference, patched in and given back), on a slope with water, an
   earthquake and an active and a passive support; the factor, lambda,
   iterations and every detail compared.
3. **The geometry is summed once per solve,** and the sum at the iterate
   many times.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from types import SimpleNamespace


def _old_moment_terms(axis, s_list, weights, resisting, normals, kh=0.0,
                      kv=0.0, sup=None, tangential=None,
                      tangential_passive=None, rotation=None, forces=None,
                      couple=0.0):
    """``moment_balance.moment_terms`` of v0.1.388, copied."""
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.moment_balance import (MomentTerms, base_frame,
                                           rotation_sense, slice_cg_y)
    ox, oy = axis
    if rotation is None:
        rotation = rotation_sense(axis, s_list, weights)

    def moment(px, py, fx, fy):
        return (px - ox) * fy - (py - oy) * fx

    m_weight = m_normal = m_shear = m_extra = 0.0
    for i, s in enumerate(s_list):
        xm, ym, tx, ty, nx, ny = base_frame(axis, s)
        w = weights[i]
        m_weight += moment(xm, ym, 0.0, -w)
        m_normal += moment(xm, ym, normals[i] * nx, normals[i] * ny)
        vx, vy = -rotation * (ym - oy), rotation * (xm - ox)
        shear_sign = -1.0 if (vx * tx + vy * ty) >= 0.0 else 1.0
        q = resisting[i]
        m_shear += moment(xm, ym, shear_sign * q * tx, shear_sign * q * ty)
        if tangential is not None and tangential[i]:
            t_extra = tangential[i]
            m_extra += moment(xm, ym, shear_sign * t_extra * tx,
                              shear_sign * t_extra * ty)
        if tangential_passive is not None and tangential_passive[i]:
            t_pas = tangential_passive[i]
            m_shear += moment(xm, ym, shear_sign * t_pas * tx,
                              shear_sign * t_pas * ty)
        f = slice_forces(s, kh, kv) if forces is None else forces[i]
        if f.h_seismic:
            m_extra += moment(xm, slice_cg_y(s), rotation * f.h_seismic, 0.0)
        if f.h_water:
            m_extra += moment(xm, f.m_water_ref0 / f.h_water, f.h_water, 0.0)
        if sup is not None and sup.present and (sup.nf_h[i] or sup.nf_v[i]):
            m_extra += moment(sup.x_app[i], sup.y_app[i],
                              sup.nf_h[i], sup.nf_v[i])
        if sup is not None and sup.present:
            nc = getattr(sup, "normal_couple", None)
            if nc and nc[i]:
                m_extra += nc[i]
    m_extra += couple
    return MomentTerms(axis=(ox, oy), rotation=rotation, weight=m_weight,
                       normal=m_normal, external=m_extra, shear=m_shear)


def _hex(terms):
    return (tuple(v.hex() for v in terms.axis), terms.rotation.hex(),
            terms.weight.hex(), terms.normal.hex(), terms.external.hex(),
            terms.shear.hex())


def _slices(n=9, mirror=False):
    """Bases of a concave polyline, some rising and some falling; the
    tops follow the ground. Mirrored, the block turns the other way."""
    out = []
    for i in range(n):
        x0, x1 = 3.0 * i, 3.0 * (i + 1)
        y0 = 0.08 * (x0 - 12.0) ** 2 + (0.37 if i % 3 == 0 else 0.0)
        y1 = 0.08 * (x1 - 12.0) ** 2
        if mirror:
            x0, x1 = -x1, -x0
            y0, y1 = y1, y0
        out.append(SimpleNamespace(base_x_left=x0, base_y_left=y0,
                                   base_x_right=x1, base_y_right=y1,
                                   top_y_left=30.0 - 0.4 * i,
                                   top_y_right=29.6 - 0.4 * i))
    return out


def _forces(n):
    return [SimpleNamespace(h_seismic=(0.0 if i % 4 == 1 else 3.1 + i),
                            h_water=(0.0 if i % 3 else -4.2 + i),
                            m_water_ref0=7.7 * (i + 1)) for i in range(n)]


def _sup(n):
    return SimpleNamespace(
        present=True,
        nf_h=[(0.0 if i % 2 else 1.3 * i) for i in range(n)],
        nf_v=[(0.0 if i % 3 else -0.7 * i) for i in range(n)],
        x_app=[3.0 * i + 1.1 for i in range(n)],
        y_app=[0.5 * i for i in range(n)],
        normal_couple=[(0.0 if i % 4 else 2.5) for i in range(n)],
        couple=0.0)


# ======================================================================
class TestTheSumIsV0_1_388s:
    """Invariant 1."""

    def _cases(self):
        n = 9
        weights = [40.0 + 7.0 * i for i in range(n)]
        normals = [35.0 - 2.0 * i for i in range(n)]
        resisting = [12.0 + 0.5 * i if i != 4 else 0.0 for i in range(n)]
        act = [(0.0 if i % 2 else 5.0 + i) for i in range(n)]
        pas = [(0.0 if i % 3 else 2.0 + i) for i in range(n)]
        for mirror in (False, True):
            s_list = _slices(n, mirror)
            axis = (-2.0 if mirror else 14.0, 41.0)
            yield dict(axis=axis, s_list=s_list, weights=weights,
                       resisting=resisting, normals=normals,
                       forces=_forces(n))
            yield dict(axis=axis, s_list=s_list, weights=weights,
                       resisting=resisting, normals=normals,
                       forces=_forces(n), kh=0.15, sup=_sup(n),
                       tangential=act, tangential_passive=pas, couple=-9.5)
            yield dict(axis=axis, s_list=s_list, weights=weights,
                       resisting=resisting, normals=normals,
                       forces=_forces(n), tangential=act,
                       tangential_passive=pas, rotation=-1.0)

    def test_moment_terms(self):
        from ogr_slip2d.moment_balance import moment_terms
        for case in self._cases():
            assert _hex(moment_terms(**case)) == _hex(_old_moment_terms(**case))

    def test_the_two_halves(self):
        from ogr_slip2d.moment_balance import moment_geometry, moment_terms_at
        for case in self._cases():
            resisting = case.pop("resisting")
            normals = case.pop("normals")
            geom = moment_geometry(**case)
            old = _old_moment_terms(resisting=resisting, normals=normals,
                                    **case)
            assert _hex(moment_terms_at(geom, resisting, normals)) == _hex(old)
            # and the same geometry again, at another iterate
            other = [2.0 * v for v in normals]
            assert (_hex(moment_terms_at(geom, resisting, other))
                    == _hex(_old_moment_terms(resisting=resisting,
                                              normals=other, **case)))

    def test_the_passive_term_follows_its_own_shear(self):
        """Floating addition is not associative, so the ORDER is part of the
        identity: v0.1.388 added each slice's passive term right after that
        slice's shear. A geometry built by hand, whose arms make each shear
        moment equal to its resistance: 1 + 2**-53 rounds back to 1, and
        the passive -1 then gives 0; the other way round it gives 2**-53."""
        from ogr_slip2d.moment_balance import MomentGeometry, moment_terms_at
        frame = (1.0, 0.0, 0.0, 1.0, -1.0, 0.0, 1.0)
        geom = MomentGeometry(axis=(0.0, 0.0), rotation=1.0,
                              frames=(frame, frame), passive=(None, -1.0),
                              weight=0.0, external=0.0)
        terms = moment_terms_at(geom, [1.0, 2.0 ** -53], [0.0, 0.0])
        assert terms.shear == 0.0
        assert (1.0 - 1.0) + 2.0 ** -53 != 0.0     # the other order

    def test_without_forces_given(self):
        """``forces=None`` resolves each slice's loads, as before: real
        slices of a wet slope with an earthquake."""
        from ogr_slip2d.moment_balance import axis_for, moment_terms
        from ogr_slip2d.slicer import slice_surface
        p, surface = _wet_slope()
        sl = slice_surface(p, surface, num_slices=15)
        s_list = list(sl.slices)
        axis = axis_for(p, surface)
        n = len(s_list)
        case = dict(axis=axis, s_list=s_list,
                    weights=[s.weight for s in s_list],
                    resisting=[10.0 + i for i in range(n)],
                    normals=[50.0 - i for i in range(n)], kh=0.12, kv=0.04)
        assert any(s.pore_pressure for s in s_list)
        assert _hex(moment_terms(**case)) == _hex(_old_moment_terms(**case))


# ======================================================================
def _wet_slope(application=None):
    """A clay slope under a water table, a polyline surface, and two
    tiebacks, the second of the given force application."""
    from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                   Vertex)
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, GroutedTiebackFriction,
                                  SupportInstance)
    from ogr_slip2d.surface import SlipSurface
    p = Project(name="moment geometry")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                             Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay", strength=MohrCoulomb(cohesion=8.0,
                                                   friction_angle=24.0),
                 unit_weight=19.0, sat_unit_weight=20.5,
                 pore_pressure=PorePressureType.WATER_TABLE)
    p.add_material(m)
    wt = Boundary(polyline=Polyline(vertices=[Vertex(0, 14), Vertex(50, 9)]),
                  btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    m.water_surface_id = wt.id
    if application is not None:
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
                                   else application)))
    surface = SlipSurface(polyline=Polyline(vertices=[
        Vertex(10.0, 25.0), Vertex(16.0, 15.0), Vertex(26.0, 9.5),
        Vertex(36.0, 10.5), Vertex(43.0, 15.0)], closed=False))
    return p, surface


class _OldPath:
    """``moment_geometry`` and ``moment_terms_at`` replaced by the full
    v0.1.388 sum on every call, and given back on exit."""

    def __enter__(self):
        import ogr_slip2d.moment_balance as MB
        self._MB = MB
        self._saved = (MB.moment_geometry, MB.moment_terms_at)

        def geometry(axis, s_list, weights, **kw):
            return (axis, s_list, weights, kw)

        def at(g, resisting, normals):
            axis, s_list, weights, kw = g
            return _old_moment_terms(axis, s_list, weights, resisting,
                                     normals, **kw)

        MB.moment_geometry, MB.moment_terms_at = geometry, at
        return self

    def __exit__(self, *exc):
        self._MB.moment_geometry, self._MB.moment_terms_at = self._saved
        return False


def _solve(method_cls, p, surface):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, surface, num_slices=20)
    method = method_cls()
    res = method.compute_fos(p, surface, sl)
    details = {k: (v.hex() if isinstance(v, float) else repr(v))
               for k, v in sorted((res.details or {}).items())}
    return (repr(res.fos), res.converged, res.iterations, res.is_valid,
            details)


# ======================================================================
class TestASolveIsV0_1_388s:
    """Invariant 2."""

    def _both(self, method_cls):
        from ogr_core.support import ForceApplication
        p, surface = _wet_slope(ForceApplication.PASSIVE)
        p.seismic.enabled = True
        p.seismic.kh = 0.1
        new = _solve(method_cls, p, surface)
        with _OldPath():
            old = _solve(method_cls, p, surface)
        assert new == old
        assert new[3], "the solve did not give a factor"

    def test_spencer(self):
        from ogr_slip2d.methods.spencer import Spencer
        self._both(Spencer)

    def test_gle(self):
        from ogr_slip2d.methods.gle import GLEMorgensternPrice
        self._both(GLEMorgensternPrice)


# ======================================================================
class TestTheGeometryIsSummedOnce:
    """Invariant 3."""

    def test_once_per_solve(self):
        import ogr_slip2d.moment_balance as MB
        from ogr_slip2d.methods.spencer import Spencer
        p, surface = _wet_slope()
        counts = {"geometry": 0, "at": 0}
        real_g, real_at = MB.moment_geometry, MB.moment_terms_at

        def geometry(*a, **k):
            counts["geometry"] += 1
            return real_g(*a, **k)

        def at(*a, **k):
            counts["at"] += 1
            return real_at(*a, **k)

        MB.moment_geometry, MB.moment_terms_at = geometry, at
        try:
            fos = _solve(Spencer, p, surface)[0]
        finally:
            MB.moment_geometry, MB.moment_terms_at = real_g, real_at
        assert counts["geometry"] == 1, counts
        assert counts["at"] > 10, counts
        assert math.isfinite(float(fos))
