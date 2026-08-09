# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The B-bar rapid-drawdown model, validated against Morgenstern (1963).

Until v0.1.69 this model had **no external validation at all**: the only
tests were of its own arithmetic, which is the snapshot test rule 1
exists to forbid. What that hid, measured on the Pilarcitos geometry with
a 729-circle grid:

    reservoir full, no drawdown ......... FS = 2.5044
    B-bar drawdown, B̄ = 1.0 ............. FS = 2.5044   <- the same number
    B-bar drawdown, B̄ = 0.5 ............. FS = 4.9324   <- higher still
    drained material, B̄ = 0 ............. FS = 6.3407

Four defects stacked up and, at B̄ = 1, cancelled: the levels were
swapped, Δσ_v was measured between the two water surfaces instead of
between the two ponded water columns, the ponded load kept the FULL
reservoir, and the excess was applied behind the suction short circuit so
it never reached anything above the lower level. The answer being
reported for "rapid drawdown" was the factor of safety from BEFORE it.

The reference: a simple slope, Morgenstern (1963)
-------------------------------------------------
Morgenstern, N. (1963). "Stability charts for earth slopes during rapid
drawdown". Géotechnique 13(2), 121-131.

A homogeneous 3:1 slope 100 ft high on a rigid base, γ = 124.8 pcf,
c' = 312 psf, φ' = 30°, B̄ = 1, reservoir initially level with the crest:

    complete drawdown, 100 -> 0 ft ...... FS = 1.20
    partial drawdown, 100 -> 50 ft ...... FS = 1.41

Bishop's simplified method, because that is the method Morgenstern's
charts were computed with.

The identity that pins the model
--------------------------------
With B̄ = 1 and a COMPLETE drawdown the model has a closed form. At a
point P whose ground surface directly above sits at y_g:

    u_initial = γ_w·(100 − y_P)
    Δσ_v      = −γ_w·(100 − y_g)          the ponded column removed
    u_final   = u_initial + B̄·Δσ_v = γ_w·(y_g − y_P)

which is γ_w times the vertical depth below the ground surface — that is,
exactly ``r_u = γ_w/γ = 62.4/124.8 = 0.5``. So the whole model has to
agree, surface by surface, with an r_u analysis that shares none of its
code. ``test_complete_drawdown_is_the_ru_identity`` checks that on a fixed
circle, and it is the strongest statement in this file: it does not
depend on a search, on a grid, or on anybody's published number.
"""
from __future__ import annotations

import math

GAMMA_W = 62.4          # pcf
GAMMA = 124.8           # pcf — exactly 2·γ_w, so r_u comes out at 0.5

# The two published cases, keyed by the final reservoir level.
PUBLISHED = {0.0: 1.20, 50.0: 1.41}

# The grid these tests can afford: 2310 candidates, about 2 s per case.
# ONE grid for both cases on purpose, wide enough to contain each of the
# two critical circles rather than centred on either — the two are not
# close, because water still standing at 50 ft holds down the lower slope
# and pushes the critical surface up it:
#
#     complete drawdown ... (60, 380) r = 380, a deep toe circle
#     drawdown to 50 ft ... (180, 220) r = 180, shallower and higher
#
# A coarser 40-ft grid was tried first and landed 5.3 % high on the
# complete case, which is the resolution of the grid speaking, not the
# model.
XS = range(20, 221, 20)
YS = range(180, 441, 20)
RS = range(160, 441, 20)

# The surface the grid finds critical for the complete drawdown, reused
# by the property tests so they do not each pay for a search.
_FIXED = dict(centre_x=60.0, centre_y=380.0, radius=380.0)


# ======================================================================
def _slope(final_y=0.0, b_bar=1.0, undrained=True, with_drawdown=True,
           initial_y=100.0):
    """The Morgenstern slope, with the reservoir level(s) drawn on it.

    The water table is the INITIAL level and the drawdown line the FINAL,
    lower one — the convention of the reference and of every published
    case. Before v0.1.69 the B-bar model demanded the opposite.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(373, 0), Vertex(373, 100), Vertex(300, 100),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("Morgenstern 1963")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, initial_y),
                                    Vertex(378, initial_y)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    if with_drawdown:
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(-5, final_y),
                                        Vertex(378, final_y)], closed=False),
            btype=BoundaryType.DRAWDOWN))
    m = Material(
        name="Slope", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=312.0, friction_angle=30.0),
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    m.undrained_behaviour = undrained
    m.b_bar = b_bar
    p.materials = [m]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.settings.groundwater.set_advanced_option("rapid_drawdown")
    p.settings.groundwater.rapid_drawdown_method = "b_bar"
    return p


def _full_reservoir(level=100.0):
    """The same slope before any drawdown: one water table, no analysis.

    ``_slope(with_drawdown=False)`` is NOT this — an undrawn final level
    means TOTAL drawdown, which is the severest case rather than the
    reference one. Getting those two confused is easy enough that this
    helper exists to keep them apart.
    """
    p = _slope(final_y=0.0, with_drawdown=False, initial_y=level)
    p.settings.groundwater.rapid_drawdown = False
    return p


def _ru_twin():
    """The same slope with no water at all and r_u = γ_w/γ = 0.5.

    Shares no code with the drawdown model: a different branch of
    ``pore_pressure_at``, no water surface, no ponding. That is the point.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(373, 0), Vertex(373, 100), Vertex(300, 100),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ru twin")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(
        name="Slope", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=312.0, friction_angle=30.0),
        pore_pressure=PorePressureType.RU_COEFFICIENT,
    )
    m.ru = GAMMA_W / GAMMA
    p.materials = [m]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


def _method(project, n=30):
    """Bishop, wrapped exactly as the application wraps it."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
    return wrap_for_drawdown(BishopSimplified(), project, num_slices=n)


def _circle(**kw):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**{**_FIXED, **kw})


def _fos(project, surface=None, n=30):
    from ogr_slip2d.slicer import slice_surface
    surface = surface or _circle()
    sl = slice_surface(project, surface, num_slices=n)
    if sl is None:
        return math.nan
    return _method(project, n).compute_fos(project, surface, sl).fos


def _critical(project, n=30):
    """Lowest factor of safety over the declared grid of circles."""
    from ogr_slip2d.surface import SlipCircle

    best = None
    for cx in XS:
        for cy in YS:
            for r in RS:
                c = SlipCircle(centre_x=float(cx), centre_y=float(cy),
                               radius=float(r))
                f = _fos(project, c, n)
                if not (math.isfinite(f) and 0.2 < f < 20.0):
                    continue
                if best is None or f < best[0]:
                    best = (f, (cx, cy, r))
    return best


# ======================================================================
class TestMorgenstern:
    """Rule 1: the numbers are Morgenstern's, not ours."""

    def test_complete_drawdown_reproduces_the_published_value(self):
        best = _critical(_slope(final_y=0.0))
        assert best is not None, "no valid surface on the grid"
        fos = best[0]
        assert math.isclose(fos, PUBLISHED[0.0], rel_tol=0.03), (
            f"complete drawdown: {fos:.4f} vs published "
            f"{PUBLISHED[0.0]} (circle {best[1]})")

    def test_partial_drawdown_reproduces_the_published_value(self):
        best = _critical(_slope(final_y=50.0))
        assert best is not None, "no valid surface on the grid"
        fos = best[0]
        assert math.isclose(fos, PUBLISHED[50.0], rel_tol=0.03), (
            f"drawdown to 50 ft: {fos:.4f} vs published "
            f"{PUBLISHED[50.0]} (circle {best[1]})")

    def test_a_partial_drawdown_is_safer_than_a_complete_one(self):
        """The ordering, independent of either published number."""
        complete = _fos(_slope(final_y=0.0))
        partial = _fos(_slope(final_y=50.0))
        assert math.isfinite(complete) and math.isfinite(partial)
        assert partial > complete


# ======================================================================
class TestTheIdentityThatPinsTheModel:
    """No search, no grid, no published number — just algebra."""

    def test_complete_drawdown_is_the_ru_identity(self):
        """B̄ = 1 with the reservoir fully emptied *is* r_u = γ_w/γ.

        See the module docstring for the two-line derivation. The r_u
        branch of ``pore_pressure_at`` shares no code with the drawdown
        one, so agreement here cannot come from a common mistake.
        """
        for kw in (dict(), dict(centre_x=40.0), dict(centre_x=100.0),
                   dict(centre_y=400.0, radius=400.0)):
            surface = _circle(**kw)
            bbar = _fos(_slope(final_y=0.0), surface)
            ru = _fos(_ru_twin(), surface)
            assert math.isfinite(bbar) and math.isfinite(ru)
            assert math.isclose(bbar, ru, rel_tol=1e-6), (
                f"{kw or 'base circle'}: B-bar {bbar:.6f} vs r_u {ru:.6f}")

    def test_a_mass_that_stays_submerged_is_untouched(self):
        """Buoyancy: a sliding mass entirely below both levels does not
        care where the water is, so the drawdown cannot move its factor
        of safety at all.

        A circle tangent to the base at x = 40 tops out at y = 30, under
        both 100 and 50. Its factor of safety is the same at the full
        reservoir, at the drawn-down steady state, and after the
        drawdown — to six figures, because with a hydrostatic field the
        water load and the uplift cancel and only the buoyant weight is
        left.

        This is also why the pre-v0.1.69 defect was so hard to see: the
        critical circle of the Pilarcitos case sits in exactly this
        regime, where the broken answer and the right one coincide. It
        took a mass that emerges to tell them apart.
        """
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        surface = SlipCircle(centre_x=40.0, centre_y=60.0, radius=60.0)

        def steady(level):
            p = _full_reservoir(level)
            sl = slice_surface(p, surface, num_slices=30)
            assert sl is not None
            return BishopSimplified().compute_fos(p, surface, sl).fos

        after = _fos(_slope(final_y=50.0), surface)
        assert math.isclose(after, steady(100.0), rel_tol=1e-6)
        assert math.isclose(after, steady(50.0), rel_tol=1e-6)

    def test_an_undrawn_final_level_means_total_drawdown(self):
        """No drawdown line is the reference's way of saying "emptied"."""
        drawn = _fos(_slope(final_y=0.0, with_drawdown=True))
        undrawn = _fos(_slope(with_drawdown=False))
        assert math.isfinite(drawn) and math.isfinite(undrawn)
        assert math.isclose(drawn, undrawn, rel_tol=1e-6)


# ======================================================================
class TestBBarMovesTheNumber:
    """Rule 7, which is precisely what this model failed before v0.1.69."""

    def test_two_values_of_b_bar_give_two_factors_of_safety(self):
        """And in the direction an UNLOADING problem requires.

        Δu = B̄·Δσ_v with Δσ_v < 0, so a larger B̄ sheds more pore
        pressure and leaves the soil stronger. B̄ = 1 — a saturated soil
        whose pore pressure follows the removed water load completely —
        is therefore the LEAST conservative of the two, which is the
        opposite of the intuition carried over from loading problems.
        """
        full = _fos(_slope(final_y=50.0, b_bar=1.0))
        half = _fos(_slope(final_y=50.0, b_bar=0.5))
        assert math.isfinite(full) and math.isfinite(half)
        assert abs(full - half) > 1e-3, (
            f"B̄ = 1.0 and B̄ = 0.5 both give {full:.6f}")
        assert full > half

    def test_the_drawdown_lowers_the_factor_of_safety(self):
        """Every B̄ must land below the full-reservoir value.

        Before v0.1.69 B̄ = 0.5 came out ABOVE it, because the analysis
        kept the whole stabilising weight of the reservoir it had just
        emptied.
        """
        reservoir_full = _fos(_full_reservoir())
        for b in (1.0, 0.5, 0.25):
            after = _fos(_slope(final_y=50.0, b_bar=b))
            assert math.isfinite(after)
            assert after < reservoir_full, (
                f"B̄ = {b}: {after:.4f} is not below the full reservoir "
                f"{reservoir_full:.4f}")

    def test_a_freely_draining_material_retains_no_excess(self):
        """Without the flag, the pore pressure is the final level's."""
        undrained = _fos(_slope(final_y=50.0, b_bar=1.0, undrained=True))
        draining = _fos(_slope(final_y=50.0, b_bar=1.0, undrained=False))
        assert math.isfinite(undrained) and math.isfinite(draining)
        assert draining > undrained


# ======================================================================
class TestTheConventionIsTheReferenceOne:
    """The drawdown line is the FINAL level. Stated, and enforced."""

    def test_a_drawdown_line_above_the_water_table_is_refused(self):
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings

        p = _slope(final_y=0.0)
        # Swap the two levels: the pre-v0.1.69 convention.
        from ogr_core.geometry import BoundaryType
        for b in p.boundaries:
            if b.btype == BoundaryType.WATER_TABLE:
                b.btype = BoundaryType.DRAWDOWN
            elif b.btype == BoundaryType.DRAWDOWN:
                b.btype = BoundaryType.WATER_TABLE
        msg = check_drawdown_settings(p)
        assert msg is not None and "drawdown" in msg.lower()

    def test_b_bar_needs_an_undrained_material(self):
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings

        p = _slope(final_y=0.0, undrained=False)
        assert check_drawdown_settings(p) is not None
