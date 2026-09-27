# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.213 — Bishop publishes its per-slice columns on every surface, not only
on a circle, and the base normal it publishes keeps the sign of m_alpha
(defect D81).

THE INVARIANTS.

1. ``BishopSimplified._general_moment_fos`` serves every surface that is not
   a ``SlipCircle`` (composite, polyline, weak layer). It fills
   ``base_normal_force``, ``base_shear_force`` and ``base_shear_strength``,
   one finite value per slice. Checked on the published circle of Baker
   (2003) example 2 with Composite Surfaces on, the case of the ficha, and on
   a polyline. It is also checked for all nine methods on both, the count
   ``test_janbu_base_forces_v1107`` only made on a circle.
2. What the column MEANS on a straight base. Fed back into Bishop's own
   moment balance about the surface's axis, the published normals and
   strengths return the factor of safety Bishop published, to 1e-10
   relative. That balance includes the Sigma N*f term of Fredlund and Krahn
   (1977), the moment of a base normal that does not pass through the axis.
   With N = W*cos(alpha) in their place the same balance misses by 7.7 % and
   8.5 % (measured), so the identity SEES the normal.
3. Consistency with a validated path (rule 1). A polyline inscribed in a
   circle drives the multi-stage drawdown through the general branch. Its
   stage-1 factor matches the arc's to 1e-4, and its drawdown factor matches
   to within 0.5 %. The circular path is the one validated on Pilarcitos
   (Duncan, Wright & Wong 1990) in ``test_rapid_drawdown_v168``. The band is
   what the ARC itself moves with the number of slices: +0.11 % at 200
   slices and -0.05 % at 400 against the 192- and 384-chord polylines, whose
   own factor holds to 1e-4. The difference is stage 2's discretisation, not
   a bias of either branch.
4. Bishop with a multi-stage drawdown on a composite surface and on a
   polyline is VALID, and its factor is not stage 1's (rule 7: the undrained
   stage is applied). Until now ``rapid_drawdown._stage1_state`` refused the
   empty column (since v0.1.108), and every such surface came back invalid
   as "drawdown_not_applicable", -111 in the export.
5. m_alpha < 0. On a steep toe exit, the normal ``base_forces_no_interslice_
   shear`` publishes is the one ``checks.base_effective_stresses`` rebuilds
   with the SIGNED m_alpha, on the two slices where m_alpha < 0 as well.
   Until now it divided by ``abs(m_alpha)`` and flipped their sign.

WHY NOT JUST THE VERTICAL EQUILIBRIUM OF EACH SLICE. That is anchor 1 of
v1107, and it is kept here (case b) because it would catch an error in the
column's arithmetic. But it holds BY CONSTRUCTION for the formula that fills
the column, on any surface, so it cannot tell a right normal from a wrong one
on a straight base. The ficha asked for it as the proof, and alone it would
not have been one.

WHY THE MOMENT IDENTITY IS NOT CHECKED ON THE COMPOSITE OF THE FICHA. There
the straight part is the flat floor. With alpha = 0 Bishop's N is exactly W,
and on the arc every chord normal passes through the axis, so ANY normal
gives the same balance: W*cos(alpha) did, to 13 figures (measured). Nor with
the power curve. The published strength is the envelope re-read at the
converged stress, while the solver resisted with the envelope linearised at
the Fellenius estimate (the convention of D84). The balance then misses by
-4.5e-4, which is that convention and not this column.

WHY THE m_alpha WITNESS IS A POLYLINE. Over 1473 circles on a 45-degree
slope with phi' up to 45 degrees, none of the 1285 that converged has a
slice with m_alpha < 0; 98 more ended with a non-physical factor and 90 with
no driving moment. Janbu answers the toe polyline below with a non-physical
factor as well, so Bishop's general branch is the one converged witness.
Case 5 calls the shared function on it directly, because on v0.1.212 that
branch published no column at all.

DISCRIMINATION against the v0.1.212 tree. MEASURED, by copying this file into
a tree of 87127cb extracted with ``git archive``, not predicted. Of the 14
cases, **11 fail and 3 pass**, all eleven by BEHAVIOUR:

  fail  the three counts                          (Bishop: 0 normals)
        both drawdown cases                       (drawdown_not_applicable)
        the_inscribed_polyline_follows_the_validated_arc  (RapidDrawdownError)
        the_published_column_is_that_normal       (empty column)
        the_shared_function_keeps_the_sign        (slice 0: +78.53 kPa where
                                                   the check reads -78.53)
        the moment identity and its control       (no strengths to feed it)
        the_vertical_equilibrium_of_each_slice    (empty column)

  pass  the_witness_is_real and the two controls of TestWhatDoesNotMove.

The first version of two of these passed VACUOUSLY on v0.1.212: ``zip`` over
an empty column does not iterate. Each now asserts the length first.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

N_BAKER = 30
N_POLY = 30
N_DD = 25            # Pilarcitos, as in test_rapid_drawdown_v168
DW = "duncan_wright"

#: A polyline on the dry slope of ``test_janbu_base_forces_v1107._slope``
#: whose straight bases do not point at its axis. Both ends lie ON the
#: ground, which is what the slicer requires of a polyline.
POLY = [(6.0, 10.0), (14.0, 7.0), (32.0, 9.0), (45.0, 20.0)]
#: A steep toe exit on the same slope, phi' = 35 deg: slices 0 and 1 have
#: m_alpha < 0 at Bishop's converged factor of safety.
TOE = [(6.0, 10.0), (9.0, 2.0), (30.0, 5.0), (45.0, 20.0)]
#: A Pilarcitos circle clear of the upstream face. The one the drawdown
#: tests use is tangent to it at x = 100, where an inscribed polyline
#: cannot follow the arc.
DD_CIRCLE = (150.0, 160.0, 110.0)
#: A Pilarcitos circle that dips below the model floor (y = 0), so Composite
#: Surfaces clips it into a flat bottom.
DD_COMPOSITE = (140.0, 105.0, 120.0)

_CACHE: dict = {}


# ======================================================================
def _tight(method):
    """The method with its fixed point pinned far below any identity here:
    the published columns are formed at the F returned, and the balance
    below reproduces F only to the iteration's own tolerance."""
    method.tolerance = 1e-12
    method.max_iterations = 5000
    return method


def _baker2(model_id: str, method_id: str = "bishop_simplified"):
    """Baker (2003) example 2 on the circle ITS OWN panel publishes, through
    ``evaluate_circle`` so Composite Surfaces clips it (as in v1107)."""
    key = ("baker2", model_id, method_id)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb, PowerCurve
    from ogr_core.project import Project
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle
    from test_janbu_base_forces_v1107 import (BAKER2, BAKER2_GAMMA,
                                              BAKER2_OUTLINE)

    ext = Polyline(vertices=[Vertex(x, y) for x, y in BAKER2_OUTLINE],
                   closed=True)
    ext.ensure_ccw()
    p = Project("Baker 2003 example 2")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    strength = (PowerCurve(a=1.107, b=0.86, c=0.0, d=0.0, waviness=0.0)
                if model_id == "power_curve"
                else MohrCoulomb(cohesion=11.64, friction_angle=24.7))
    clay = Material(name="clay", unit_weight=BAKER2_GAMMA,
                    sat_unit_weight=BAKER2_GAMMA, strength=strength)
    p.materials = [clay]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), clay.id)
    p.settings.search.composite_surfaces = True

    (cx, cy, r), _sigma, _fos = BAKER2[model_id]
    method = build_method(p, method_id, N_BAKER)
    res = GridSearch(method=method, num_slices=N_BAKER,
                     min_area=0.0).evaluate_circle(
        p, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
    assert res is not None and res.is_valid, (model_id, method_id)
    _CACHE[key] = (p, res)
    return _CACHE[key]


def _polyline(vertices):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in vertices], closed=False))


def _dry_slope(cohesion=10.0, phi=30.0):
    """The dry slope of v1107's ``_slope``, with the envelope a parameter."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(60, 0), Vertex(60, 20),
                             Vertex(35, 20), Vertex(15, 10), Vertex(0, 10)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("dry slope")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", unit_weight=19.0, sat_unit_weight=20.0,
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=phi),
        pore_pressure=PorePressureType.NONE)]
    return p


def _on_polyline(vertices, method_id="bishop_simplified", tight=False,
                 cohesion=10.0, phi=30.0):
    key = ("poly", tuple(vertices), method_id, tight, cohesion, phi)
    if key in _CACHE:
        return _CACHE[key]
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    p = _dry_slope(cohesion, phi)
    surf = _polyline(vertices)
    slices = slice_surface(p, surf, num_slices=N_POLY)
    assert slices is not None, vertices
    method = method_registry()[method_id]()
    if tight:
        _tight(method)
    res = method.compute_fos(p, surf, slices)
    _CACHE[key] = (p, res)
    return _CACHE[key]


def _balance(project, res, normals):
    """Bishop's moment balance about the surface's axis, rebuilt from the
    PUBLISHED strengths and the given normals: the factor it returns."""
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.moment_balance import axis_for, moment_terms
    s_list = res.slices.slices
    weights = [slice_forces(s).w_total for s in s_list]
    terms = moment_terms(axis_for(project, res.surface), s_list, weights,
                         res.base_shear_strength, normals)
    return -terms.shear / terms.driving


def _m_alphas(res):
    """m_alpha per slice, in the sense the method formed it, at its F."""
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.methods.bishop import BishopSimplified
    sgn = res.details["m_alpha_sign"]
    out = []
    for s in res.slices.slices:
        w = slice_forces(s).w_total
        l = max(s.base_length, 1e-9)
        sigma = max(0.0, w * math.cos(s.base_angle) - s.pore_pressure * l) / l
        _c, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma)
        out.append(math.cos(s.base_angle)
                   + sgn * math.sin(s.base_angle) * tan_phi / res.fos)
    return out


def _pilarcitos_with_axis(centre):
    """Pilarcitos with the moment axis on the circle's centre, so the
    inscribed polyline is taken about the same point as the arc (see
    ``test_moment_axis_v1126``: the automatic axis of a polyline is built
    from its chord, and that convention is measured there, not here)."""
    from test_rapid_drawdown_v168 import _pilarcitos
    p = _pilarcitos()
    p.settings.search.axis_x, p.settings.search.axis_y = centre
    return p


def _inscribed(circle_def, x_left, x_right, n_chords):
    from test_moment_axis_v1126 import _inscribed as inscribed
    return inscribed(circle_def, x_left, x_right, n_chords)


def _drawdown(project, surface, n):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
    return rapid_drawdown_fos(project, surface, BishopSimplified(),
                              num_slices=n, procedure=DW)


def _wrapped_surface(project, surface, n=N_DD):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
    from ogr_slip2d.slicer import slice_surface
    return MultiStageDrawdownMethod(BishopSimplified(), DW,
                                    num_slices=n).compute_fos(
        project, surface, slice_surface(project, surface, num_slices=n))


def _stage1_factor(project, surface, n=N_DD):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import level_project
    from ogr_slip2d.slicer import slice_surface
    p1 = level_project(project, use_drawdown=False)
    return BishopSimplified().compute_fos(
        p1, surface, slice_surface(p1, surface, num_slices=n)).fos


# ======================================================================
class TestTheColumnsAreThere:
    """(a) and (g): the gap this version closes, stated as a count."""

    def test_bishop_on_the_composite_of_the_ficha(self):
        from ogr_slip2d.surface import CompositeSurface
        for model_id in ("power_curve", "mohr_coulomb"):
            _p, res = _baker2(model_id)
            assert isinstance(res.surface, CompositeSurface), model_id
            n = len(res.slices.slices)
            assert n == N_BAKER
            for name in ("base_normal_force", "base_shear_force",
                         "base_shear_strength"):
                col = getattr(res, name)
                assert len(col) == n, (model_id, name, len(col))
                assert all(math.isfinite(v) for v in col), (model_id, name)

    def test_all_nine_fill_the_three_arrays_on_a_polyline(self):
        from test_janbu_base_forces_v1107 import ALL_METHODS
        for mid in ALL_METHODS:
            _p, res = _on_polyline(POLY, mid)
            assert res.is_valid, (mid, res.fos, res.error_message)
            n = len(res.slices.slices)
            for name in ("base_normal_force", "base_shear_force",
                         "base_shear_strength"):
                col = getattr(res, name)
                assert len(col) == n, (mid, name, len(col))
                assert all(math.isfinite(v) for v in col), (mid, name)

    def test_all_nine_fill_the_three_arrays_on_a_composite(self):
        from ogr_slip2d.surface import CompositeSurface
        from test_janbu_base_forces_v1107 import ALL_METHODS
        for mid in ALL_METHODS:
            _p, res = _baker2("mohr_coulomb", mid)
            assert isinstance(res.surface, CompositeSurface), mid
            n = len(res.slices.slices)
            for name in ("base_normal_force", "base_shear_force",
                         "base_shear_strength"):
                col = getattr(res, name)
                assert len(col) == n, (mid, name, len(col))
                assert all(math.isfinite(v) for v in col), (mid, name)


# ======================================================================
class TestWhatTheNormalMeans:

    def test_vertical_equilibrium_of_each_slice(self):
        """(b) Anchor 1 of v1107 on a straight-based surface. Tautological
        for the formula, kept for its arithmetic: see the module docstring."""
        from ogr_slip2d.external_forces import slice_forces
        _p, res = _on_polyline(POLY)
        sgn = res.details["m_alpha_sign"]
        s_list = res.slices.slices
        # Not vacuous: ``zip`` over an empty column would pass untouched.
        assert len(res.base_normal_force) == len(s_list)
        mean_w = sum(slice_forces(s).w_total for s in s_list) / len(s_list)
        for s, n_i, t_i in zip(s_list, res.base_normal_force,
                               res.base_shear_strength):
            lhs = (n_i * math.cos(s.base_angle)
                   + sgn * (t_i / res.fos) * math.sin(s.base_angle))
            rhs = slice_forces(s).w_total
            assert abs(lhs - rhs) <= 1e-6 * max(abs(rhs), mean_w), (
                s.index, lhs, rhs)

    def test_the_published_columns_close_bishops_own_moment_balance(self):
        """(c) The discriminating identity: Sigma N*f included."""
        for verts in (POLY, [(4.0, 10.0), (10.0, 5.0), (20.0, 6.0),
                             (38.0, 12.0), (50.0, 20.0)]):
            p, res = _on_polyline(verts, tight=True)
            assert res.converged
            got = _balance(p, res, res.base_normal_force)
            assert abs(got - res.fos) <= 1e-10 * res.fos, (verts, got,
                                                           res.fos)

    def test_the_identity_sees_the_normal(self):
        """The control: with the Fellenius normal the balance does NOT
        close, so passing above is not a coincidence of the geometry."""
        from ogr_slip2d.external_forces import slice_forces
        p, res = _on_polyline(POLY, tight=True)
        fellenius = [slice_forces(s).w_total * math.cos(s.base_angle)
                     for s in res.slices.slices]
        got = _balance(p, res, fellenius)
        assert abs(got - res.fos) > 0.01 * res.fos, (got, res.fos)


# ======================================================================
class TestTheDrawdownRunsOnEverySurface:

    def test_a_polyline_is_valid_and_applies_the_undrained_stage(self):
        """(e) on a polyline inscribed in a Pilarcitos circle."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = DD_CIRCLE
        p = _pilarcitos_with_axis((cx, cy))
        arc = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        sl = slice_surface(p, arc, num_slices=N_DD)
        surf = _inscribed(DD_CIRCLE, sl.slices[0].base_x_left,
                          sl.slices[-1].base_x_right, 24)
        res = _wrapped_surface(p, surf)
        assert res.is_valid, (res.fos, res.reason, res.error_message)
        assert res.reason != "drawdown_not_applicable"
        f1 = _stage1_factor(p, surf)
        assert abs(res.fos - f1) > 0.1 * f1, (res.fos, f1)

    def test_a_composite_is_valid_and_applies_the_undrained_stage(self):
        """(e) on a Pilarcitos circle clipped by the model floor."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import CompositeSurface, SlipCircle
        from test_rapid_drawdown_v168 import _pilarcitos
        p = _pilarcitos()
        p.settings.search.composite_surfaces = True
        cx, cy, r = DD_COMPOSITE
        ev = GridSearch(method=MultiStageDrawdownMethod(
            BishopSimplified(), DW, num_slices=N_DD),
            num_slices=N_DD, min_area=0.0)
        res = ev.evaluate_circle(p, SlipCircle(centre_x=cx, centre_y=cy,
                                               radius=r))
        assert isinstance(res.surface, CompositeSurface)
        assert res.is_valid, (res.fos, res.reason, res.error_message)
        f1 = _stage1_factor(p, res.surface)
        assert abs(res.fos - f1) > 0.1 * f1, (res.fos, f1)

    def test_the_inscribed_polyline_follows_the_validated_arc(self):
        """(d) Consistency with the circular path, stage by stage."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = DD_CIRCLE
        n = 100
        p = _pilarcitos_with_axis((cx, cy))
        arc = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        sl = slice_surface(p, arc, num_slices=n)
        a = _drawdown(p, arc, n)
        poly = _drawdown(p, _inscribed(DD_CIRCLE, sl.slices[0].base_x_left,
                                       sl.slices[-1].base_x_right, 96), n)
        rel1 = (poly.fos_stage1 - a.fos_stage1) / a.fos_stage1
        rel = (poly.fos - a.fos) / a.fos
        assert abs(rel1) < 1e-4, (poly.fos_stage1, a.fos_stage1)
        assert abs(rel) < 0.005, (poly.fos, a.fos)


# ======================================================================
class TestTheSignOfMAlpha:
    """(f) On the steep toe exit, where m_alpha < 0 on two slices."""

    def _toe(self):
        return _on_polyline(TOE, cohesion=5.0, phi=35.0)

    def test_the_witness_is_real(self):
        """Guard: without negative m_alpha on a converged solution the
        cases below prove nothing."""
        _p, res = self._toe()
        assert res.is_valid and res.converged, (res.fos, res.reason)
        negative = [i for i, m in enumerate(_m_alphas(res)) if m < 0.0]
        assert negative == [0, 1], negative

    def test_the_shared_function_keeps_the_sign(self):
        """The function, on the witness: what the Tensile Stress Check
        rebuilds with the signed m_alpha, slice by slice."""
        from ogr_slip2d.checks import base_effective_stresses
        from ogr_slip2d.methods.bishop import base_forces_no_interslice_shear
        _p, res = self._toe()
        s_list = res.slices.slices
        normals, _sh, _st = base_forces_no_interslice_shear(
            s_list, 0.0, res.details["kv"], res.details["m_alpha_sign"],
            res.fos)
        want = base_effective_stresses(res)
        for k, (n_k, s) in enumerate(zip(normals, s_list)):
            got = n_k / s.base_length - s.pore_pressure
            assert abs(got - want[k]) <= 1e-9 * max(1.0, abs(want[k])), (
                k, got, want[k])

    def test_the_published_column_is_that_normal(self):
        from ogr_slip2d.checks import base_effective_stresses
        _p, res = self._toe()
        want = base_effective_stresses(res)
        assert len(res.base_normal_force) == len(want) > 0
        for k, (n_k, s) in enumerate(zip(res.base_normal_force,
                                         res.slices.slices)):
            got = n_k / s.base_length - s.pore_pressure
            assert abs(got - want[k]) <= 1e-9 * max(1.0, abs(want[k])), (
                k, got, want[k])


# ======================================================================
class TestWhatDoesNotMove:
    """Controls: the factor of safety is not recomputed by any of this."""

    def test_a_circle_still_takes_the_circular_path(self):
        from test_janbu_base_forces_v1107 import _slope
        from ogr_slip2d.methods.bishop import BishopSimplified
        p, circle, slices = _slope()
        res = BishopSimplified().compute_fos(p, circle, slices)
        assert "moment_axis" not in res.details
        assert len(res.base_normal_force) == len(slices.slices)

    def test_the_guard_in_stage_one_still_refuses_a_short_column(self):
        """``_stage1_state`` still fails loudly on a method that forgets
        the column: what changed is that Bishop no longer forgets it."""
        from ogr_slip2d.methods.base import LEMResult
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError, _stage1_state
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = DD_CIRCLE
        p = _pilarcitos_with_axis((cx, cy))
        arc = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        sl = slice_surface(p, arc, num_slices=N_DD)
        short = LEMResult(fos=1.5, converged=True, iterations=1,
                          method_id="forgetful", surface=arc, slices=sl)
        try:
            _stage1_state(p, arc, sl, short)
        except RapidDrawdownError as exc:
            assert "cannot be recovered" in str(exc)
            return
        raise AssertionError("an empty column was accepted")
