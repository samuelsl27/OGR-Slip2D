# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The TANGENTIAL half of a support's line load, measured against a slope the
reference publishes TWICE — with the pile and without it.

WHAT INVARIANT THIS PROTECTS

A support force is a line load on the slice it crosses, so it joins that
slice's VERTICAL equilibrium — the one ``m_α`` is what remains of (Bishop
1955) — and its frictional share reaches the base divided by ``m_α``.
:func:`ogr_slip2d.support_integration.support_vertical_load` writes that
load as two terms:

    down = T_N·cos α  −  slide_sign·sin α·(T_S,active + T_S,passive/F)
           [ NORMAL ]     [            TANGENTIAL                    ]

``test_support_normal_v1137`` covers the first. Its fixture is
*deliberately* a purely normal support — ``_purely_normal_angle()`` makes
``T_S`` zero BY CONSTRUCTION — so deleting the second term outright would
leave every assertion in that file green. This file is the other half, and
it is the half that closed defect D42: a support whose force is TANGENT to
the slip surface has ``T_N ≡ 0``, so there the first term is the one that
vanishes and only the second can do anything at all.

The mechanism is worth stating because it is easy to get backwards. The
pile resists UP the slope along the base; its reaction therefore LIFTS the
slice off that base, ``W_eff`` falls, and the friction
``(W_eff − u·b)·tan φ'`` falls with it. A support that helps in the
tangential balance gives a little back in the normal one. From v0.1.64 to
v0.1.136 Bishop collected the help and none of the cost.

WHY THIS SLOPE, AND NOT A FIXTURE

Yamagami (2000), verification problem 54: a homogeneous slope with one row
of micropiles, published with a critical circle **and a factor of safety
for each of the two cases** — with reinforcement and without it, on two
different circles, one per figure.

That pair is what turns the case into a measurement instead of a
comparison. The unreinforced twin has no support to cross it, so **it
cannot move** when the reinforcement term changes: it holds the soil term
at −0.08 % while the reinforced case measures the reinforcement term
alone. One reinforced case on its own cannot separate the two, which is
why for seventy-two versions this error read as a 1.6 % disagreement about
geometry.

The two clay anchors of the same family measure nothing here, and saying
so is the point: verification problems 60 and 85 have φ = 0, where
``tan φ' ≡ 0`` makes the whole branch identically zero. This slope has
φ = 10°.

Geometry is built in code rather than loaded from ``referencias/``, like
every other benchmark in this suite: the tests have to run without the
reference bank on disk.

WHAT WOULD MAKE THIS A SNAPSHOT, AND WHY IT IS NOT ONE

Every number asserted is published: 1.193 and 1.102 from the manual's own
Table 54.2 (with Yamagami's own 1.20 and 1.10 beside them), and the pile's
10.7 kN at 1 m spacing from the problem statement. The tolerances are
D42's closure criterion — ±1 % — and not the error that happens to be
measured today, which is +0.19 %.

The last class is stronger still: it rebuilds Bishop's equation term by
term at the factor the solver converged to, in BOTH candidate forms, and
only one of them closes. That assertion would still discriminate if every
coordinate in this file changed.
"""
from __future__ import annotations

import math

# --- Yamagami (2000) / verification problem 54 -----------------------
EXTERNAL = [(-6.0, -5.0), (12.0, -5.0), (12.0, 4.0),
            (8.0, 4.0), (0.0, 0.0), (-6.0, 0.0)]
COH = 4.9          # kPa
PHI = 10.0         # deg — NOT zero, which is what lets this case measure
GAMMA = 15.68      # kN/m3

#: A single row of micropiles, vertical, near the crest.
PILE_X = 8.98
PILE_HEAD_Y = 4.0      # on the crest segment (12,4)-(8,4): the slope face
PILE_TAIL_Y = -1.92
PILE_SHEAR = 10.7      # kN per pile
PILE_SPACING = 1.0     # m, out of plane

NSLICES = 50

#: The two published circles, one per figure. Keeping them apart is what
#: made the soil term measurable: with only the reinforced circle on file,
#: the unreinforced case was being compared against the WRONG surface.
CIRCLE_WITH_PILE = (2.674, 7.376, 8.102)     # figure 54.3
CIRCLE_NO_PILE = (2.674, 7.573, 8.031)       # figure 54.2

PUBLISHED_WITH_PILE = 1.193     # Table 54.2 (Yamagami's own: 1.20)
PUBLISHED_NO_PILE = 1.102       # Table 54.2 (Yamagami's own: 1.10)

#: Sum of W·sin α on the reinforced circle, kN/m. Used only to turn a gain
#: in factor of safety back into a force, for the bracket below.
DRIVING_WITH_PILE = 109.54

#: D42's closure criterion, verbatim, and the tolerance for the twin that
#: carries no support at all and therefore has no excuse.
TOL_REINFORCED = 0.01
TOL_BARE = 0.005


def _circle(c):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=c[0], centre_y=c[1], radius=c[2])


def _project(with_pile: bool = True):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import PileMicropile, SupportInstance

    ext = Polyline(vertices=[Vertex(x, y) for x, y in EXTERNAL], closed=True)
    ext.ensure_ccw()
    p = Project("yamagami-54" + ("" if with_pile else "-bare"))
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    soil = Material(name="Material 1", unit_weight=GAMMA,
                    sat_unit_weight=GAMMA,
                    strength=MohrCoulomb(cohesion=COH, friction_angle=PHI))
    p.materials = [soil]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), soil.id)
    if with_pile:
        p.support_types = [PileMicropile(
            pile_shear_strength=PILE_SHEAR,
            out_of_plane_spacing=PILE_SPACING)]
        # Orientation and application are left as ``None`` ON PURPOSE, so
        # they resolve against the type's own declaration. Setting them by
        # hand would let the shipped defaults drift while this file stayed
        # green — and those defaults are exactly what D42's criterion is
        # about: the documented orientation, not the one that fits best.
        p.supports = [SupportInstance(
            type_id="pile_micropile",
            head=Vertex(PILE_X, PILE_HEAD_Y),
            tail=Vertex(PILE_X, PILE_TAIL_Y),
            name="micropile")]
    return p


def _slices(p, circle, n=NSLICES):
    from ogr_slip2d.slicer import slice_surface
    return slice_surface(p, _circle(circle), num_slices=n)


def _fos(p, circle, n=NSLICES):
    from ogr_slip2d.methods.bishop import BishopSimplified
    res = BishopSimplified().compute_fos(p, _circle(circle),
                                         _slices(p, circle, n))
    assert res.converged, res.error_message
    return res.fos


def _slide_sign(s_list):
    """The sense the method derives, from the same expression it uses.

    There is no seismic loading anywhere in this problem, so the
    ``(1 − kv)`` factor of the original is 1.
    """
    return 1.0 if math.fsum(s.weight * math.sin(s.base_angle)
                            for s in s_list) >= 0 else -1.0


def _resolved(p, circle, n=NSLICES):
    """Slices, support terms and the converged factor, in one pass."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.support_integration import resolve_support_terms
    sl = _slices(p, circle, n)
    res = BishopSimplified().compute_fos(p, _circle(circle), sl)
    assert res.converged, res.error_message
    sign = _slide_sign(sl.slices)
    return (sl, resolve_support_terms(p, _circle(circle), sl, sign),
            res.fos, sign)


# ======================================================================
class TestTheUnreinforcedTwinPinsTheSoilTerm:
    """The control, and the half the bank did not have until v0.1.113.

    Nothing in this class can be moved by any change to the reinforcement:
    there is no support in the model. That is what makes it a control
    rather than a second measurement.
    """

    def test_the_bare_slope_reproduces_its_own_published_circle(self):
        f = _fos(_project(with_pile=False), CIRCLE_NO_PILE)
        assert abs(f / PUBLISHED_NO_PILE - 1.0) < TOL_BARE, f

    def test_the_two_published_circles_are_not_the_same_surface(self):
        """Guards the mistake this case was diagnosed through.

        Comparing the unreinforced result against the REINFORCED circle is
        what hid the soil term: it mixes a difference of surfaces into what
        is supposed to be a difference of models. The manual publishes one
        circle per figure and they are not the same one.
        """
        bare = _project(with_pile=False)
        on_own = _fos(bare, CIRCLE_NO_PILE)
        on_other = _fos(bare, CIRCLE_WITH_PILE)
        assert abs(on_own - on_other) > 1e-3, (on_own, on_other)


# ======================================================================
class TestThePublishedPairWithTheDocumentedOrientation:
    """D42's closure criterion, as a test.

    The orientation is asserted, not chosen. Picking the one that fits is
    retroanalysis, and this bank paid for that once already: the
    perpendicular option lands closer on THIS problem (−1.6 % against
    +0.19 %) and is still not what the documentation declares for a pile,
    which fails in shear THROUGH its section on the slip plane.
    """

    def test_the_pile_declares_the_documented_orientation(self):
        from ogr_core.support import (ForceApplication, ForceOrientation,
                                      PileMicropile)
        assert (PileMicropile.DEFAULT_ORIENTATION
                is ForceOrientation.TANGENT_TO_SLIP)
        sup = _project().supports[0]
        assert sup.orientation is ForceOrientation.TANGENT_TO_SLIP
        assert sup.force_application is ForceApplication.PASSIVE

    def test_the_reinforced_slope_reproduces_its_published_circle(self):
        f = _fos(_project(), CIRCLE_WITH_PILE)
        assert abs(f / PUBLISHED_WITH_PILE - 1.0) < TOL_REINFORCED, f

    def test_the_pile_helps_and_by_about_what_it_is_worth(self):
        """The reinforcement raises the factor, and by a credible amount.

        Bracketed rather than pinned. The declared shear is 10.7 kN/m and
        the mobilised part of it reaches the factor through ``m_α``, so the
        effective gain is neither zero nor the whole of it. Without this,
        removing the support altogether would still pass the assertion
        above on a slope whose bare factor on that circle is 1.108.
        """
        bare = _fos(_project(with_pile=False), CIRCLE_WITH_PILE)
        piled = _fos(_project(), CIRCLE_WITH_PILE)
        assert piled > bare, (bare, piled)
        gain = (piled - bare) * DRIVING_WITH_PILE
        assert 0.5 * PILE_SHEAR < gain < PILE_SHEAR, gain


# ======================================================================
class TestTheTangentialLoadIsWhatCarriesIt:
    """Which of the two branches does the work here — measured, not argued.

    ``support_vertical_load`` has a normal term and a tangential one. On
    this model the normal one is identically zero, so if the tangential
    term were removed the whole function would return nothing and Bishop
    would be back to its v0.1.136 arithmetic.
    """

    def test_the_normal_branch_is_identically_zero_on_this_model(self):
        """A force tangent to the slip surface has no normal component.

        Asserted rather than assumed: it is what makes the tests below a
        measurement OF THE TANGENTIAL TERM and not of the other one.
        """
        _sl, sup, _f, _sign = _resolved(_project(), CIRCLE_WITH_PILE)
        assert sup.present
        worst = max(abs(v) for v in sup.n_press)
        assert worst < 1e-9, worst

    def test_the_crossed_slice_carries_the_declared_shear(self):
        """One slice, and it carries shear / spacing exactly."""
        _sl, sup, _f, _sign = _resolved(_project(), CIRCLE_WITH_PILE)
        crossed = [t for t in sup.t_passive if abs(t) > 1e-12]
        assert len(crossed) == 1, crossed
        assert abs(crossed[0] - PILE_SHEAR / PILE_SPACING) < 1e-9, crossed
        # Passive, so nothing came off the driving side.
        assert sup.total_active_t() == 0.0

    def test_the_reaction_lifts_the_slice_it_crosses(self):
        """The sign, which is the half that is easy to get backwards.

        A resisting force pointing up the slope has an UPWARD component on
        a base that dips downslope, so it unloads the base rather than
        pressing on it. If this ever comes back positive, the support is
        being credited twice: once in the tangential balance and again as
        extra friction.
        """
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.support_integration import support_vertical_load
        sl, sup, fos, sign = _resolved(_project(), CIRCLE_WITH_PILE)
        i = next(k for k, t in enumerate(sup.t_passive) if abs(t) > 1e-12)
        s = sl.slices[i]
        down = support_vertical_load(sup, i, s.base_angle, sign, fos)
        assert down < 0.0, down
        # And not a negligible fraction of that slice's own weight, or the
        # assertion above would pass on a rounding error.
        w = slice_forces(s, 0.0, 0.0).w_total
        assert abs(down) > 0.05 * w, (down, w)

    def test_only_the_form_with_the_tangential_load_closes_the_equation(self):
        """Bishop's equation rebuilt at the factor it converged to.

        Not a captured number: the two candidate numerators are written out
        at the SAME factor of safety, and one of them satisfies
        ``numerator / denominator = F`` while the other misses by two
        orders of magnitude more. It would still discriminate if every
        coordinate in this file changed.
        """
        from ogr_slip2d.external_forces import slice_forces
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.support_integration import support_vertical_load

        sl, sup, fos, sign = _resolved(_project(), CIRCLE_WITH_PILE)
        s_list = sl.slices

        # No seismic, no ponded water and no tension crack in this problem,
        # so the driving moment is the gravity term alone.
        den = math.fsum(sign * slice_forces(s, 0.0, 0.0).w_total
                        * s.weight_arm_ratio for s in s_list)
        den -= sup.total_active_t()

        def numerator(with_tangential: bool) -> float:
            total = 0.0
            for i, s in enumerate(s_list):
                w = slice_forces(s, 0.0, 0.0).w_total
                w += (support_vertical_load(sup, i, s.base_angle, sign, fos)
                      if with_tangential
                      else sup.n_press[i] * math.cos(s.base_angle))
                n_est = w * math.cos(s.base_angle)
                sigma = max(0.0, n_est - s.pore_pressure * s.base_length)
                sigma /= max(s.base_length, 1e-9)
                c, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                           sigma)
                m_alpha = (math.cos(s.base_angle)
                           + sign * math.sin(s.base_angle) * tan_phi / fos)
                total += (c * s.width
                          + (w - s.pore_pressure * s.width) * tan_phi
                          ) / m_alpha
            return total + sup.total_passive_t()

        closes = numerator(True) / den - fos
        raw = numerator(False) / den - fos
        assert abs(closes) < 1e-3, closes
        assert abs(raw) > 1e-2, raw
        assert abs(raw) > 100.0 * abs(closes), (closes, raw)
