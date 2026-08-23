# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The per-slice base forces: every method reports them, and they mean one thing.

WHAT INVARIANT THIS PROTECTS.

``LEMResult`` declares three per-slice arrays and the two Janbu methods left
them EMPTY until v0.1.107. That was not a cosmetic gap:
``rapid_drawdown._stage1_state`` reads the base normal to recover the stage-1
consolidation state, so with an empty list the two-stage drawdown applied
undrained strength to ZERO slices and quietly became a re-run of stage 1.
Measured on a two-stage benchmark whose accepted answer is 1.347: Janbu gave
1.7625 with nothing undrained and gives 1.2177 with all fifty.

Three anchors, none of them a snapshot of what the code prints:

1. **Vertical equilibrium of each slice** — an analytic identity. Janbu
   (1954) neglects the inter-slice shear exactly as Bishop (1955) does, so
   every slice satisfies ``N*cos(a) + s*S*sin(a) = W`` with
   ``S = [c'*l + (N - u*l)*tan(phi')] / F``. The reported normal is a
   rearrangement of that equation, so it has to hold on the values reported.

2. **Global horizontal equilibrium** — the equation Janbu's method IS, and
   the one that discriminates. ``sum(S*cos(a) - s*N*sin(a))`` must vanish on
   a dry slope with no seismic load. It does for Janbu Simplified and it does
   NOT for Bishop, which satisfies moments instead; that contrast is what
   makes the first anchor more than a tautology, because a normal borrowed
   from a moment method would fail it.

3. **The published maximum effective normal stress** of Baker's (2003) third
   example, which a verification manual reproduces: 36.33 kPa with a power
   curve envelope and 30.05 kPa with Mohr-Coulomb, both for Janbu Simplified
   on the published critical circle.

   The tolerance is +-3 %, not the +-1 % that would look tidier, and the
   reason is worth writing down: on that same circle the FACTOR OF SAFETY
   already lands -1.4 % and -2.5 % from the published value, so sigma' cannot
   be expected to do better. Measured: -1.9 % and +1.2 %. Tightening the band
   would be pinning a discrepancy this test did not cause.

   Note the published value for SPENCER on the same circle is 31.21, not
   36.33 — the inter-slice shear moves the peak — so it is a different
   comparison and does not belong here.

And two definitions this file also pins:

* **``base_shear_force`` is the DRIVING force** ``s*W*sin(a)`` in all nine
  methods. Until v0.1.107 it was that in Bishop, Janbu and Ordinary and the
  MOBILISED shear in Corps #1, Corps #2, Lowe-Karafiath, Spencer and GLE —
  2.58 against 41.0 on the same slice, printed under an interface row that
  reads "Driving shear W*sin(alpha)". The mobilised shear is not lost: it is
  ``base_shear_strength / fos``, which is what the panel already divides.

* **Ordinary / Fellenius is the documented exception** to the vertical
  identity. It takes ``N = W*cos(a)`` by construction — it resolves the
  external forces normal to the base and never writes the vertical
  equilibrium of the slice — so the identity misses by several per cent
  there. It is asserted to FAIL, so that a change which quietly made
  Fellenius satisfy it would be noticed rather than welcomed.

References: Bishop, A.W. (1955), Geotechnique 5(1), 7-17; Janbu, N. (1954,
1973); Fellenius, W. (1927); Baker, R. (2003).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Baker (2003) example 3, as a verification manual reproduces it.
BAKER3_OUTLINE = [(0, 0), (20, 0), (20, 6), (6, 6)]
BAKER3_GAMMA = 18.0
BAKER3_SLICES = 50
#: (centre_x, centre_y, radius) of the published critical circle, and the
#: published maximum effective normal stress for Janbu Simplified on it.
BAKER3 = {
    "power_curve": ((-0.977, 9.501, 9.551), 36.33),
    "mohr_coulomb": ((-1.665, 9.968, 10.106), 30.05),
}

ALL_METHODS = ["bishop_simplified", "janbu_simplified", "janbu_corrected",
               "ordinary_fellenius", "spencer", "gle_morgenstern_price",
               "lowe_karafiath", "corps_engineers_1", "corps_engineers_2"]

#: Spencer and GLE get a looser band than the rest because their answer ends
#: a root search in lambda, so an identity can only close to that search's
#: own tolerance.
VERTICAL_TOL = {"spencer": 1e-3, "gle_morgenstern_price": 1e-3}
VERTICAL_DEFAULT = 1e-6

_CACHE: dict = {}


# ======================================================================
def _slope():
    """A dry homogeneous Mohr-Coulomb slope, sliced once and reused.

    Dry and linear on purpose: with no pore water the identities below are
    exact, and with a straight envelope the linearisation the methods take at
    the first-pass stress is the same one they report at the final stress. A
    curved envelope has its own test further down.
    """
    if "slope" in _CACHE:
        return _CACHE["slope"]
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle

    ext = Polyline(vertices=[Vertex(0, 0), Vertex(60, 0), Vertex(60, 20),
                             Vertex(35, 20), Vertex(15, 10), Vertex(0, 10)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("dry slope")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", unit_weight=19.0, sat_unit_weight=20.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=30.0),
        pore_pressure=PorePressureType.NONE)]
    circle = SlipCircle(centre_x=28.0, centre_y=36.0, radius=28.0)
    slices = slice_surface(p, circle, num_slices=30)
    assert slices is not None and len(slices.slices) == 30
    _CACHE["slope"] = (p, circle, slices)
    return _CACHE["slope"]


def _baker3(model_id: str):
    """Baker's third example with one of its two envelopes."""
    key = "baker3:" + model_id
    if key in _CACHE:
        return _CACHE[key]
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb, PowerCurve
    from ogr_core.project import Project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle

    ext = Polyline(vertices=[Vertex(x, y) for x, y in BAKER3_OUTLINE],
                   closed=True)
    ext.ensure_ccw()
    p = Project("Baker 2003 example 3")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    # The power curve is Baker's own tau/Pa = A*(sigma_n/Pa + T)**n with
    # A = 0.535, n = 0.6, T = 0.0015 and Pa = 101.325 kPa, rewritten in the
    # tau = a*(sigma_n + d)**b + c form the material model takes.
    strength = (PowerCurve(a=3.39344, b=0.6, c=0.0, d=0.1520, waviness=0.0)
                if model_id == "power_curve"
                else MohrCoulomb(cohesion=6.0, friction_angle=32.0))
    clay = Material(name="clay", unit_weight=BAKER3_GAMMA,
                    sat_unit_weight=BAKER3_GAMMA, strength=strength)
    p.materials = [clay]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), clay.id)

    (cx, cy, r), published = BAKER3[model_id]
    circle = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
    slices = slice_surface(p, circle, num_slices=BAKER3_SLICES)
    assert slices is not None
    _CACHE[key] = (p, circle, slices, published)
    return _CACHE[key]


def _run(method_id, fixture=None):
    from ogr_slip2d.methods.base import method_registry
    p, circle, slices = fixture or _slope()
    res = method_registry()[method_id]().compute_fos(p, circle, slices)
    assert res.is_valid, (method_id, res.fos, res.error_message)
    return res


def _slide_sign(slices) -> float:
    """The sense of sliding, as every solver in the package derives it."""
    driving = sum(s.weight * math.sin(s.base_angle) for s in slices)
    return 1.0 if driving >= 0 else -1.0


def _mobilised(res):
    """``tau_f*l / F``, the shear force equilibrium actually mobilises."""
    return [t / res.fos for t in res.base_shear_strength]


def _total_weight(slices, kh=0.0, kv=0.0):
    from ogr_slip2d.external_forces import slice_forces
    return sum(slice_forces(s, kh, kv).w_total for s in slices)


def _vertical_sum(res, slices):
    """``sum(N*cos(a) + s*S*sin(a))`` over the mass."""
    sgn = _slide_sign(slices)
    return sum(
        n_i * math.cos(s.base_angle) + sgn * s_mob * math.sin(s.base_angle)
        for s, n_i, s_mob in zip(slices.slices, res.base_normal_force,
                                 _mobilised(res)))


def _max_effective_normal(res) -> float:
    """max(N/l - u) over the slices: the stress, not the force."""
    return max(n / max(s.base_length, 1e-9) - s.pore_pressure
               for n, s in zip(res.base_normal_force, res.slices.slices))


# ======================================================================
class TestEveryMethodPublishesTheColumns:
    """The gap this version closes, stated as a count."""

    def test_all_nine_fill_the_three_arrays(self):
        _p, _c, slices = _slope()
        n = len(slices.slices)
        for mid in ALL_METHODS:
            res = _run(mid)
            for name in ("base_normal_force", "base_shear_force",
                         "base_shear_strength"):
                col = getattr(res, name)
                assert len(col) == n, (mid, name, len(col))
                assert all(math.isfinite(v) for v in col), (mid, name)

    def test_the_deprecated_alias_still_answers(self):
        """Scripts outside this repository ask for the old name."""
        res = _run("janbu_simplified")
        assert res.base_normal
        assert res.base_normal == res.base_normal_force


# ======================================================================
class TestVerticalEquilibriumOfEachSlice:
    """``N*cos(a) + s*S*sin(a) = W`` — what the reported normal MEANS.

    Exact for both Janbu variants: the correction factor scales F, and the
    forces are formed at whichever F is reported, so the identity closes
    either way.
    """

    def _check(self, method_id):
        from ogr_slip2d.external_forces import slice_forces
        _p, _c, slices = _slope()
        res = _run(method_id)
        sgn = _slide_sign(slices)
        mean_w = _total_weight(slices) / len(slices.slices)
        for s, n_i, s_mob in zip(slices.slices, res.base_normal_force,
                                 _mobilised(res)):
            lhs = (n_i * math.cos(s.base_angle)
                   + sgn * s_mob * math.sin(s.base_angle))
            rhs = slice_forces(s).w_total
            assert abs(lhs - rhs) <= 1e-6 * max(abs(rhs), mean_w), (
                method_id, s.index, lhs, rhs)

    def test_janbu_simplified(self):
        self._check("janbu_simplified")

    def test_janbu_corrected(self):
        self._check("janbu_corrected")

    def test_bishop_the_method_janbu_shares_the_assumption_with(self):
        self._check("bishop_simplified")


# ======================================================================
class TestJanbusOwnEquation:
    """Global horizontal equilibrium: ``sum(S*cos(a) - s*N*sin(a)) = 0``.

    This is the equation Janbu Simplified solves, so the forces it reports
    have to satisfy it. It is also what tells a Janbu normal from a Bishop
    one: the two share the zero-inter-slice-shear assumption and therefore
    the same ALGEBRA for N, but they evaluate it at different factors of
    safety, and only Janbu's closes the horizontal balance.
    """

    @staticmethod
    def _residual(res, slices):
        sgn = _slide_sign(slices)
        mob = _mobilised(res)
        scale = sum(abs(v) for v in mob) or 1.0
        total = sum(
            s_mob * math.cos(s.base_angle) - sgn * n_i * math.sin(s.base_angle)
            for s, n_i, s_mob in zip(slices.slices, res.base_normal_force,
                                     mob))
        return abs(total) / scale

    def test_janbu_simplified_closes_it(self):
        _p, _c, slices = _slope()
        r = self._residual(_run("janbu_simplified"), slices)
        assert r < 1e-3, r

    def test_bishop_does_not_and_that_is_the_point(self):
        """Guard the guard. Without this the test above would also pass for
        a normal copied straight out of the moment method."""
        _p, _c, slices = _slope()
        r = self._residual(_run("bishop_simplified"), slices)
        assert r > 0.01, r

    def test_janbu_corrected_does_not_either_which_is_the_correction(self):
        """f0 multiplies the factor of safety and comes from Janbu's (1973)
        comparison of the simplified and the rigorous solutions — it is not
        obtained by re-solving equilibrium, so the corrected state does not
        close the force balance. Reporting the forces at the CORRECTED F is
        a deliberate choice: they go with the number that is displayed."""
        _p, _c, slices = _slope()
        simplified = _run("janbu_simplified")
        corrected = _run("janbu_corrected")
        assert corrected.fos > simplified.fos, (corrected.fos, simplified.fos)
        assert self._residual(corrected, slices) > 0.01


# ======================================================================
class TestGlobalVerticalEquilibrium:
    """``sum(N*cos(a) + s*S*sin(a)) = W_total`` over the whole mass.

    The vertical components of the inter-slice forces telescope to zero
    between the two free ends, so this holds for every method that writes the
    vertical equilibrium of a slice — whatever it assumes about the
    inter-slice inclination.

    Note it is NOT ``sum(N*cos(a)) = W_total``, which misses by 4 to 5 %: the
    mobilised base shear carries a vertical component of its own everywhere
    the base is inclined.
    """

    def test_it_holds_for_the_eight_methods_that_write_it(self):
        _p, _c, slices = _slope()
        w = _total_weight(slices)
        for mid in ALL_METHODS:
            if mid == "ordinary_fellenius":
                continue
            total = _vertical_sum(_run(mid), slices)
            tol = VERTICAL_TOL.get(mid, VERTICAL_DEFAULT)
            assert abs(total - w) <= tol * w, (mid, total, w)

    def test_fellenius_is_the_documented_exception(self):
        """Fellenius (1927) resolves the external forces NORMAL to the base
        and takes ``N = W*cos(a)``; the slice's vertical equilibrium is never
        written, which is the classical reason the method is conservative.
        Asserted as a failure so that a change which quietly made it hold
        would show up as a broken test rather than as an improvement."""
        _p, _c, slices = _slope()
        w = _total_weight(slices)
        total = _vertical_sum(_run("ordinary_fellenius"), slices)
        assert abs(total - w) > 0.01 * w, (total, w)

    def test_the_plain_sum_of_normals_is_NOT_the_weight(self):
        """The identity that looks right and is not, kept so nobody
        re-derives it: the shear's vertical component is a few per cent of
        the weight on this surface and does not vanish."""
        _p, _c, slices = _slope()
        w = _total_weight(slices)
        res = _run("bishop_simplified")
        naive = sum(n_i * math.cos(s.base_angle)
                    for s, n_i in zip(slices.slices, res.base_normal_force))
        assert 0.02 < (w - naive) / w < 0.12, (naive, w)


# ======================================================================
class TestTheMaximumEffectiveNormalStress:
    """Baker (2003) example 3, against the published value.

    The quantity is a STRESS, ``N/l - u``, and the arrays hold FORCES.
    Reading ``max(base_normal_force)`` as if it were kPa gives a number about
    four times too small and plausible enough to pass unnoticed; this example
    is where that was caught, because it publishes the stress (force 7.69,
    stress 36.46, published 36.33).
    """

    @staticmethod
    def _measure(model_id):
        p, circle, slices, published = _baker3(model_id)
        res = _run("janbu_simplified", (p, circle, slices))
        return _max_effective_normal(res), published

    def test_power_curve(self):
        got, published = self._measure("power_curve")
        assert abs(got - published) <= 0.03 * published, (got, published)

    def test_mohr_coulomb(self):
        got, published = self._measure("mohr_coulomb")
        assert abs(got - published) <= 0.03 * published, (got, published)

    def test_it_is_a_stress_and_not_the_force(self):
        """The confusion the correction exists to prevent, pinned: the
        largest FORCE on this surface is nowhere near the published
        stress."""
        p, circle, slices, published = _baker3("power_curve")
        res = _run("janbu_simplified", (p, circle, slices))
        assert max(res.base_normal_force) < 0.5 * published, (
            max(res.base_normal_force), published)

    def test_a_curved_envelope_closes_the_identity_only_loosely(self):
        """With a non-linear envelope the identity stops being exact, and the
        reason is structural rather than a defect: N is derived with the
        envelope linearised at the first-pass stress and the strength is
        reported with the linearisation at the final one. Measured under
        0.2 %; pinned at 1 % so the two are known to be close and known not
        to be equal."""
        p, circle, slices, _pub = _baker3("power_curve")
        w = _total_weight(slices)
        for mid in ("janbu_simplified", "bishop_simplified", "spencer"):
            total = _vertical_sum(_run(mid, (p, circle, slices)), slices)
            assert abs(total - w) <= 0.01 * w, (mid, total, w)


# ======================================================================
class TestBaseShearForceMeansOneThing:
    """One field, one quantity, in all nine methods."""

    def test_it_is_the_driving_force_everywhere(self):
        from ogr_slip2d.external_forces import slice_forces
        _p, _c, slices = _slope()
        sgn = _slide_sign(slices)
        expected = [sgn * slice_forces(s).w_total * math.sin(s.base_angle)
                    for s in slices.slices]
        scale = max(abs(v) for v in expected)
        for mid in ALL_METHODS:
            res = _run(mid)
            worst = max(abs(a - b)
                        for a, b in zip(res.base_shear_force, expected))
            # Ordinary is the one method allowed a small gap: on a circle it
            # uses the GEOMETRIC moment arm (x_mid - x_centre)/R rather than
            # sin(alpha), because that is the arm its own factor of safety is
            # built from. The two agree to well under a per cent.
            tol = 0.01 * scale if mid == "ordinary_fellenius" else 1e-9
            assert worst <= tol, (mid, worst, scale)

    def test_it_is_not_the_mobilised_shear(self):
        """The two used to be mixed across methods and they are not close.

        Read on the FLATTEST slice, where the distinction is at its most
        physical: with the base almost horizontal nothing drives the slice,
        while the base still carries most of the shear it can. Measured
        there, the mobilised shear is about sixteen times the driving
        force, so a field holding one where the other is expected is not a
        rounding difference.
        """
        _p, _c, slices = _slope()
        i = min(range(len(slices.slices)),
                key=lambda k: abs(math.sin(slices.slices[k].base_angle)))
        for mid in ("spencer", "gle_morgenstern_price", "lowe_karafiath",
                    "corps_engineers_1", "corps_engineers_2"):
            res = _run(mid)
            mob = _mobilised(res)
            assert abs(mob[i]) > 5.0 * abs(res.base_shear_force[i]), (
                mid, mob[i], res.base_shear_force[i])

    def test_the_mobilised_shear_is_recoverable(self):
        """Nothing was lost by unifying the field: for the methods that form
        it, the mobilised shear is the strength divided by F."""
        for mid in ("lowe_karafiath", "corps_engineers_1"):
            res = _run(mid)
            for t, s_mob in zip(res.base_shear_strength, _mobilised(res)):
                assert abs(s_mob - t / res.fos) < 1e-9 * max(1.0, abs(t))


# ======================================================================
class TestTheDrawdownReadsTheNormal:
    """Rule 7: the array is not decoration, it decides an analysis.

    ``_stage1_state`` recovers the stage-1 consolidation state from the base
    normal. With an empty list the loop breaks on its first turn, the state
    comes back empty, and the two-stage procedure applies undrained strength
    to NO slice — a drained re-run of stage 1 wearing the name of a drawdown.
    """

    @staticmethod
    def _drawdown(method_id):
        from test_rapid_drawdown_v168 import _pilarcitos
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p = _pilarcitos()
        p.settings.groundwater.rapid_drawdown_method = "corps_2"
        circle = SlipCircle(centre_x=52.0, centre_y=186.0, radius=158.2)
        slices = slice_surface(p, circle, num_slices=20)
        method = build_method(p, method_id, num_slices=20)
        return method.compute_fos(p, circle, slices)

    def test_janbu_now_reaches_the_second_stage(self):
        res = self._drawdown("janbu_simplified")
        assert res.details["undrained_slices"] > 0, res.details
        assert res.details["fos_stage2"] < res.details["fos_stage1"], (
            res.details)

    def test_the_drawdown_result_carries_its_own_slices_and_columns(self):
        """The wrapper used to build a result with three empty arrays and the
        STAGE-1 slices, so a drawdown left the interpretation window blank
        with every method, Bishop included."""
        for mid in ("bishop_simplified", "janbu_simplified", "spencer"):
            res = self._drawdown(mid)
            n = len(res.slices.slices)
            assert n > 0, mid
            assert len(res.base_normal_force) == n, (mid, n)
            assert len(res.base_shear_force) == n, (mid, n)
            assert len(res.base_shear_strength) == n, (mid, n)
