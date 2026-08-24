# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Reinforcement reaches every limit-equilibrium method, and it does so with
a sign.

Until v0.1.64 only Bishop integrated supports. The other six reported a
factor of safety with no reinforcement at all and said nothing about it,
while the interface happily let the user enable several methods at once —
so one column of the results table accounted for the nails and the rest
silently did not.

Worse than the omission was how the one implementation that existed did
it. Measured on the fixture below, before the change:

  * **The orientation could not hurt.** ``numerator += abs(proj_tangent)``
    made the factor of safety exactly symmetric under a 180° flip of the
    support force: pointing the bolt downhill gave 2.496110 and pointing
    it uphill gave 2.496110, the same digits. A support could never lower
    the factor of safety, whatever direction it pulled in.
  * **The normal component was dropped.** A bolt perpendicular to the slip
    surface, carrying 133 kN/m, moved the factor of safety by +0.003 %.
    Its whole contribution is ``T_N·tanφ'``, and that term did not exist.
  * **Active and Passive were the same number**, bit for bit, when the
    published equations make Passive ≤ Active always:
        F_act = (R + T_N·tanφ') / (D − T_S)
        F_pas = (R + T_N·tanφ' + T_S) / D
    v0.1.64 fixed that for the RATIO methods only. The three that solve
    complete equilibrium kept answering one number for both settings until
    v0.1.115, and this file asserted it — see
    ``TestPassiveNeverBeatsActive`` below.

The anchors here are analytic identities and cross-method consistency,
never captured values:

  * For Ordinary/Fellenius the factor of safety is a plain ratio of sums,
    so a PASSIVE tangential support of known magnitude must move it to
    exactly ``(ΣR + T_S)/ΣD`` — computable from the unreinforced run,
    which reports both sums per slice.
  * Passive ≤ Active follows from the two equations above and must hold
    for every ratio method.
  * The three methods that satisfy full equilibrium (Spencer, GLE,
    Lowe-Karafiath) resolve the support's NORMAL part inside the slice
    equilibrium and must therefore agree with each other, as they already
    do without reinforcement. They are each other's reference.
  * A support that does not cross the slip surface must change nothing,
    in every method — the cheapest way to catch a term added on the wrong
    side of an equation.
"""
from __future__ import annotations

import math

H = 12.0
TOE = 30.0
CREST = 50.0     # slope face from (30, 0) to (50, 12)


def _methods():
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.methods.gle import GLEMorgensternPrice
    from ogr_slip2d.methods.janbu import JanbuCorrected, JanbuSimplified
    from ogr_slip2d.methods.lowe_karafiath import LoweKarafiath
    from ogr_slip2d.methods.ordinary import OrdinaryFellenius
    from ogr_slip2d.methods.spencer import Spencer
    return [
        ("ordinary_fellenius", OrdinaryFellenius),
        ("bishop_simplified", BishopSimplified),
        ("janbu_simplified", JanbuSimplified),
        ("janbu_corrected", JanbuCorrected),
        ("spencer", Spencer),
        ("gle_morgenstern_price", GLEMorgensternPrice),
        ("lowe_karafiath", LoweKarafiath),
    ]


def _rigorous():
    from ogr_slip2d.methods.gle import GLEMorgensternPrice
    from ogr_slip2d.methods.lowe_karafiath import LoweKarafiath
    from ogr_slip2d.methods.spencer import Spencer
    return [("spencer", Spencer),
            ("gle", GLEMorgensternPrice),
            ("lowe_karafiath", LoweKarafiath)]


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)


def _project(support=None):
    """A homogeneous slope, optionally with one nail through its face.

    ``support`` is a ready ``SupportInstance`` so each test can choose the
    orientation and the Active/Passive flag without a pile of arguments.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import SoilNail

    # v0.1.89 — 10 m of foundation. Without it the stretch from x = 0 to
    # the toe encloses no soil: the closing edge runs back along the bottom
    # one. Not listed among the five in docs/PENDIENTES.md — the inventory
    # there was made by hand and had gone stale.
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("sup")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    if support is not None:
        # A modest nail. A capacity comparable to the driving force makes
        # the Active denominator (D − T_S) nearly vanish and the factor of
        # safety explode — arithmetically right, physically meaningless,
        # and useless as a test fixture.
        p.support_types = [SoilNail(tensile_capacity=30, plate_capacity=20,
                                    bond_strength=8, out_of_plane_spacing=3.0)]
        p.supports = [support]
    return p


def _nail(orientation=None, angle_deg=0.0, application=None,
          head=(43.5, 8.0), tail=(54.0, 8.0)):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id="soil_nail",
        head=Vertex(*head), tail=Vertex(*tail),
        force_application=application or ForceApplication.PASSIVE,
        orientation=orientation or ForceOrientation.TANGENT_TO_SLIP,
        user_angle_deg=angle_deg,
    )


def _fos(cls, p):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, _circle(), num_slices=25)
    assert sl is not None
    return cls().compute_fos(p, _circle(), sl)


def _terms(p):
    """The support terms the solvers see, for the analytic anchors."""
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import resolve_support_terms
    sl = slice_surface(p, _circle(), num_slices=25)
    return resolve_support_terms(p, _circle(), sl, 1.0), sl


# ======================================================================
class TestEveryMethodSeesTheSupport:
    """The omission itself: six methods ignored reinforcement entirely."""

    def test_a_nail_raises_the_factor_of_safety_everywhere(self):
        bare = _project()
        for name, cls in _methods():
            f0 = _fos(cls, bare).fos
            f1 = _fos(cls, _project(_nail())).fos
            assert math.isfinite(f0) and math.isfinite(f1), name
            assert f1 > f0, f"{name}: {f0:.5f} -> {f1:.5f}"
            # Big enough not to be iteration noise.
            assert (f1 - f0) / f0 > 0.01, f"{name}: only {100*(f1-f0)/f0:.3f} %"

    def test_a_nail_that_misses_the_surface_changes_nothing(self):
        """The cheapest check that a term landed on the right side: a
        support that never intersects the slip surface must be inert."""
        bare = _project()
        # Far below the failure mass, inside the block but nowhere near
        # the arc, which spans roughly x = 40..52 above y = 6.
        miss = _nail(head=(2.0, 1.0), tail=(12.0, 1.0))
        for name, cls in _methods():
            f0 = _fos(cls, bare).fos
            f1 = _fos(cls, _project(miss)).fos
            assert abs(f1 - f0) < 1e-9, f"{name}: {f0!r} vs {f1!r}"


class TestTheOrientationCanHurt:
    """Anomaly 1: ``abs()`` made the factor of safety blind to direction."""

    def _at_angle(self, deg, cls):
        from ogr_core.support import ForceOrientation
        return _fos(cls, _project(_nail(
            orientation=ForceOrientation.USER_DEFINED, angle_deg=deg))).fos

    def test_a_support_pushing_downhill_lowers_the_factor_of_safety(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        bare = _fos(BishopSimplified, _project()).fos
        # 0° points into the slope (resisting); 180° points out of it.
        uphill = self._at_angle(0.0, BishopSimplified)
        downhill = self._at_angle(180.0, BishopSimplified)
        assert uphill > bare
        assert downhill < bare, (bare, downhill)

    def test_flipping_the_support_is_not_a_symmetry(self):
        """The exact signature of the bug: before v0.1.64 these two were
        equal to every digit, for every angle."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        for deg in (0.0, 45.0, 90.0, 135.0):
            a = self._at_angle(deg, BishopSimplified)
            b = self._at_angle(deg + 180.0, BishopSimplified)
            assert abs(a - b) > 1e-6, f"{deg}°: {a!r} == {b!r}"


class TestTheNormalComponentDoesWork:
    """Anomaly 2: ``T_N·tanφ'`` was missing."""

    def _purely_normal(self, sign):
        """A support along the base normal of the slice it crosses.

        ``sign`` = +1 presses the slice onto its base, −1 lifts it off.
        The angle is derived from the slice geometry rather than guessed,
        so the tangential component is zero by construction and only the
        normal one is under test.
        """
        from ogr_core.support import ForceOrientation
        probe = _project(_nail())
        sup, sl = _terms(probe)
        i = next(i for i, v in enumerate(sup.f_h) if v or sup.f_v[i])
        a = sl.slices[i].base_angle
        # Inward normal n = (−sin α, cos α); pressing means −n.
        ang = math.degrees(math.atan2(-sign * math.cos(a),
                                      sign * math.sin(a)))
        return _project(_nail(orientation=ForceOrientation.USER_DEFINED,
                              angle_deg=ang)), sup, sl, i

    def test_pressing_helps_and_lifting_hurts(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        bare = _fos(BishopSimplified, _project()).fos
        press, _s, _sl, _i = self._purely_normal(+1)
        lift, _s2, _sl2, _i2 = self._purely_normal(-1)
        f_press = _fos(BishopSimplified, press).fos
        f_lift = _fos(BishopSimplified, lift).fos
        assert f_press > bare, (bare, f_press)
        assert f_lift < bare, (bare, f_lift)

    def test_ordinary_gains_exactly_t_n_times_tan_phi(self):
        """Closed form. Ordinary is a plain ratio ΣR/ΣD, and a purely
        normal support adds exactly ``T_N·tanφ'`` to ΣR and nothing to ΣD,
        so the new factor of safety is ``F₀·(1 + T_N·tanφ'/ΣR)``.
        """
        from ogr_slip2d.methods.ordinary import OrdinaryFellenius
        p, _s, _sl, _i = self._purely_normal(+1)
        res0 = _fos(OrdinaryFellenius, _project())
        sum_r = sum(res0.base_shear_strength)
        sup, _sl2 = _terms(p)
        t_n = sum(sup.n_press)
        tan_phi = math.tan(math.radians(20.0))
        expected = res0.fos * (1.0 + t_n * tan_phi / sum_r)
        got = _fos(OrdinaryFellenius, p).fos
        assert abs(got - expected) / expected < 1e-6, (got, expected)


class TestPassiveNeverBeatsActive:
    """Anomaly 3: the two were the same number."""

    def test_ratio_methods_order_them_correctly(self):
        from ogr_core.support import ForceApplication
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.janbu import JanbuSimplified
        from ogr_slip2d.methods.ordinary import OrdinaryFellenius
        for name, cls in (("ordinary", OrdinaryFellenius),
                          ("bishop", BishopSimplified),
                          ("janbu", JanbuSimplified)):
            fa = _fos(cls, _project(
                _nail(application=ForceApplication.ACTIVE))).fos
            fp = _fos(cls, _project(
                _nail(application=ForceApplication.PASSIVE))).fos
            assert fp < fa, f"{name}: passive {fp:.5f} >= active {fa:.5f}"

    def test_the_rigorous_methods_distinguish_them_too(self):
        """v0.1.115 — this test used to assert the OPPOSITE, that Spencer,
        GLE and Lowe-Karafiath answer the same number for both settings, and
        it carried a reason:

            *"Active vs Passive is an artefact of writing the factor of
            safety as a ratio. A method that solves equilibrium sees a
            force, and a force has no such flag."*

        The reason is false, and the reference says so on the page that
        defines the setting: it publishes FOUR equations, a pair for MOMENT
        equilibrium and a pair for FORCE equilibrium, and attributes them to
        Methods A and B of Duncan & Wright (2005). A complete-equilibrium
        method has a numerator and a denominator like any other. What a
        force genuinely has no flag for is the base normal — which is why
        the tangential part of a support is now outside the slice
        equilibrium in every method, and only its side of the fraction bar
        changes.

        See ``tests/test_support_active_passive_v1115.py`` for the closed
        forms that measure it.
        """
        from ogr_core.support import ForceApplication
        for name, cls in _rigorous():
            fa = _fos(cls, _project(
                _nail(application=ForceApplication.ACTIVE))).fos
            fp = _fos(cls, _project(
                _nail(application=ForceApplication.PASSIVE))).fos
            assert fp < fa, f"{name}: passive {fp:.6f} >= active {fa:.6f}"


class TestTheRigorousMethodsAgreeWithEachOther:
    """Cross-method consistency, the anchor available without a published
    reinforced case: three independent formulations of complete
    equilibrium must land on the same number, reinforced or not."""

    def test_they_agree_without_reinforcement(self):
        vals = [_fos(cls, _project()).fos for _n, cls in _rigorous()]
        assert max(vals) - min(vals) < 0.01 * min(vals), vals

    def test_they_still_agree_with_reinforcement(self):
        vals = [_fos(cls, _project(_nail())).fos for _n, cls in _rigorous()]
        assert max(vals) - min(vals) < 0.01 * min(vals), vals

    def test_the_gain_is_the_same_for_all_three(self):
        """v0.1.115 — the band went from 0.5 % to 1 %, and the reason is a
        real difference between two correct routes to the PASSIVE case,
        which is what ``_nail()`` defaults to.

        Spencer and GLE move the reinforcement term across the fraction bar,
        so it never touches the base normal. Lowe-Karafiath never forms a
        ratio: its factor of safety is the root of a marching recursion, and
        the only faithful way to mobilise reinforcement there is ``T_S/F`` on
        the base — where the recursion has already eliminated N analytically
        from BOTH projections, so it does reach the normal. There is no
        "outside the equilibrium" in a marching method to put it in.

        The residue is 0.61 % on the gain and 0.57 % on the factor of safety,
        against the 0.49 % these three already disagree by with no
        reinforcement at all. Tightening this back would be asserting that
        two different formulations of complete equilibrium agree better with
        a support than without one.
        """
        gains = []
        for _n, cls in _rigorous():
            f0 = _fos(cls, _project()).fos
            f1 = _fos(cls, _project(_nail())).fos
            gains.append((f1 - f0) / f0)
        assert max(gains) - min(gains) < 0.01, gains


class TestOverwhelmingActiveSupportIsInadmissible:
    """The instability the v0.1.15 convention avoided by discarding the
    sign. It is real; it is now diagnosed instead of hidden."""

    def _huge(self):
        from ogr_core.support import ForceApplication, SoilNail
        p = _project(_nail(application=ForceApplication.ACTIVE))
        p.support_types = [SoilNail(tensile_capacity=4000,
                                    plate_capacity=4000,
                                    bond_strength=2000,
                                    out_of_plane_spacing=1.0)]
        return p

    def test_the_surface_is_flagged_not_silently_wrong(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.methods.ordinary import OrdinaryFellenius
        p = self._huge()
        for name, cls in (("bishop", BishopSimplified),
                          ("ordinary", OrdinaryFellenius)):
            res = _fos(cls, p)
            assert res.admissible is False, f"{name}: {res.fos!r}"
            assert res.admissibility_note, name

    def test_a_modest_support_stays_admissible(self):
        from ogr_core.support import ForceApplication
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _fos(BishopSimplified,
                   _project(_nail(application=ForceApplication.ACTIVE)))
        assert res.admissible is True
        assert 0.0 < res.details.get("active_support_ratio", 0.0) < 1.0
