# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.462 (D447) — a slice base that runs ALONG a contact between two
materials takes the WEAKER of the two.

WHAT WAS WRONG

Until v0.1.461 such a base took the material ABOVE the contact: the slicer
asks for the base's material 0.01 above its midpoint (D48r), and nothing
else looked at the other side. On the spoil heap on a sheared floor of
Coulthard (1979) and Hoek (1987) — problem 4 of the bank's manual of
non-vertical slices — the published surface runs on the floor from (0, 0)
to (108, 6.4), and all 25 toe bases read the spoil (c = 100, φ = 42°)
instead of the floor (c = 10, φ = 6°): Bishop 3.768 against the published
1.198. With the floor it is 1.199.

THE RULE, AND WHY

The three published cases of the bank whose surface runs on a contact ask
for the weaker material, and no one-sided rule meets them all: Duncan,
Wright and Brandon (2014, §7.7.6, Fig. 7.29) give the flat run of the James
Bay dyke on the till the lacustrine clay ABOVE; problem 4 needs the floor
BELOW; a spoil heap on rock of the same manual needs the spoil above. The
weaker is the one with the lower τ = c + σ′ tan φ at the base's static
Fellenius effective stress (Fellenius 1936), each material with its own
water (``slicer._contact_strength``). A base takes part only if it RUNS
along the contact: its ends and middle within the model's resolution of
one material boundary. Measured on the whole bank (D447,
``_auditoria/P9_D447``, an A/B of 812 surfaces): only the 8 published
surfaces of problem 4 move. ``slicer.BASE_ON_CONTACT = "above"`` gives
v0.1.461 back, bit for bit; rapid drawdown keeps "above" (see below).

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The published problem 4** (Coulthard 1979; Hoek 1987), built here
   from its published geometry: the toe bases read the sheared floor, dry
   and saturated, and dry Bishop gives the published 1.198 within 1 %
   (measured +0.07 %). Saturated the vertical slices give about 0.21
   against the published 0.434, which is the method and is not tested
   here (Sarma's wedges give 0.4347 on the same mass,
   test_sarma_solver_v1461). With the old rule, 3.77: the switch moves the
   number (rule 7).
2. **James Bay** (Duncan, Wright and Brandon 2014): a flat run on the
   contact of the lacustrine clay (su = 31.5 kPa) and the "very strong"
   till reads the clay above, under both rules.
3. **The weaker, by hand:** on a two-layer block, a base on the contact
   reads the material of lower c + σ′ tan φ, with σ′ written here from the
   slice's own weight and pore pressure (the two envelopes cross at
   211 kPa): the upper one when the contact is shallow, the lower one when
   it is deep; each with its own water; the ponded water counted in σ′;
   σ′ clipped at zero under an artesian head; a tie keeps the one above.
4. **Only a base that runs along it:** a base within the model's
   resolution of the contact is on it; one 5 mm above it (along a water
   table drawn there), one that spans a 5 mm dip of the contact, and the
   bottom of a circle tangent to it keep their material, every field to
   the last bit.
5. **The resolution is the model's:** a 1/50 copy and a 1000× copy of a
   model with a thin layer under the contact read that layer and give the
   same factor (Bishop, forces and c scaled, γ kept).
6. **The candidate below is its own material:** its pore pressure by Ru
   (u = Ru·γ·z, Bishop and Morgenstern 1960), by the child of a
   Generalized Anisotropic material that does not take the parent's water
   (Ru times the parent's weight, D230), by B-bar under a line load on a
   cut (Δu = B̄·Δσv, Skempton 1954, the load counted once); its bedding and
   its joint surfaces where they are; and a water surface of its own that
   does not reach the base refuses the surface (as v0.1.96 does for the
   base's own material).
7. **A weak layer still wins:** a joint along the contact gives the joint's
   material, whatever the two sides are.
8. **Rapid drawdown keeps the material above:** its two levels would
   choose differently on the same base (owner's decision, 2026-11-16, until
   its own ficha), so its four procedures give the same factor under both
   rules, to the last bit.
9. **Nothing moves off a contact**, every field to the last bit; the mirror
   of problem 4 gives the same factor; a rule that is not one is an error.

Measured cost: about 0.5 s for the file (30 cases), 0.2 s of it the four
drawdown procedures twice.
"""
from __future__ import annotations

import contextlib
import math

_D = math.radians

# ----------------------------------------------------------------- problem 4
#: Problem 4 of the bank's manual of non-vertical slices (Coulthard 1979;
#: Hoek 1987), as the bank transcribes it (``construir_modelo.py`` of
#: ``03_Sarma_Problema004``): the external boundary, the contact between the
#: spoil heap and the sheared floor, the published surface, table 4.1 and
#: the water table on the spoil surface of the saturated case.
_EXT4 = ((-50.0, -20.0), (250.0, -20.0), (250.0, 14.9), (229.545, 13.6815),
         (111.4, 76.5), (0.0, 0.0), (-50.0, -2.97))
_CONTACT4 = ((0.0, 0.0), (108.0, 6.4), (229.545, 13.6815))
_WT4 = ((-50.0, -2.97), (0.0, 0.0), (111.4, 76.5), (229.545, 13.6815),
        (250.0, 14.9))
_SURFACE4 = ((0.0, 0.0), (108.0, 6.4), (128.0, 67.6737))
_PUBLISHED4 = 1.198


@contextlib.contextmanager
def _rule(rule):
    import ogr_slip2d.slicer as S
    old = S.BASE_ON_CONTACT
    S.BASE_ON_CONTACT = rule
    try:
        yield
    finally:
        S.BASE_ON_CONTACT = old


def _polyline(points, closed=False):
    from ogr_core.geometry import Polyline, Vertex
    return Polyline(vertices=[Vertex(x, y) for x, y in points], closed=closed)


def _problem4(wet=False, mirror=False):
    from ogr_core.geometry import Boundary, BoundaryType
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipSurface
    k = -1.0 if mirror else 1.0

    def m(pts):
        return sorted(((k * x, y) for x, y in pts), key=lambda v: v[0])
    p = Project("D447 problem 4")
    ext = _polyline([(k * x, y) for x, y in _EXT4], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=_polyline(m(_CONTACT4)),
                            btype=BoundaryType.MATERIAL))
    pp = PorePressureType.WATER_TABLE if wet else PorePressureType.NONE
    floor = Material(name="Sheared Floor", unit_weight=15.7, pore_pressure=pp,
                     strength=MohrCoulomb(cohesion=10.0, friction_angle=6.0))
    spoil = Material(name="Spoil", unit_weight=15.7, pore_pressure=pp,
                     strength=MohrCoulomb(cohesion=100.0, friction_angle=42.0))
    p.materials = [floor, spoil]
    p.assign_material_at(k * 100.0, 40.0, spoil.id)
    if wet:
        wt = Boundary(polyline=_polyline(m(_WT4)),
                      btype=BoundaryType.WATER_TABLE)
        p.add_boundary(wt)
        floor.water_surface_id = spoil.water_surface_id = wt.id
    return p, SlipSurface(polyline=_polyline(m(_SURFACE4)))


def _sliced(p, surface, n=30):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, surface, num_slices=n)
    assert sl is not None
    return sl


def _bishop(p, surface, sl):
    from ogr_slip2d.methods import method_registry
    m = method_registry()["bishop_simplified"]()
    m.tolerance = 1e-10
    return m.compute_fos(p, surface, sl).fos


def _toe(sl, mirror=False):
    """The slices whose base runs on the floor, from (0, 0) to (108, 6.4)."""
    if mirror:
        return [s for s in sl if s.base_x_left >= -108.0 - 1e-9]
    return [s for s in sl if s.base_x_right <= 108.0 + 1e-9]


def _same_slices(a, b):
    """Every field of every slice, floats to the last bit."""
    from dataclasses import fields
    assert len(a) == len(b), (len(a), len(b))
    for sa, sb in zip(a, b):
        for f in fields(sa):
            va, vb = getattr(sa, f.name), getattr(sb, f.name)
            if isinstance(va, float):
                assert va.hex() == vb.hex(), (sa.index, f.name, va, vb)
            else:
                assert va == vb or va is vb, (sa.index, f.name)


class TestTheSpoilHeapOnASheardFloor:

    def test_the_toe_reads_the_floor_and_gives_the_published_factor(self):
        p, surface = _problem4()
        sl = _sliced(p, surface)
        toe = _toe(sl)
        assert len(toe) == 25, len(toe)       # premise: the fixture's toe
        assert {s.material.name for s in toe} == {"Sheared Floor"}
        assert {s.material.name for s in sl if s not in toe} == {"Spoil"}
        F = _bishop(p, surface, sl)
        assert abs(F / _PUBLISHED4 - 1.0) <= 0.01, F

    def test_saturated_the_toe_reads_the_floor_too(self):
        p, surface = _problem4(wet=True)
        sl = _sliced(p, surface)
        assert {s.material.name for s in _toe(sl)} == {"Sheared Floor"}
        assert all(s.pore_pressure > 0.0 for s in _toe(sl)[1:])

    def test_the_old_rule_reads_the_spoil_and_moves_the_number(self):
        p, surface = _problem4()
        with _rule("above"):
            sl = _sliced(p, surface)
            assert {s.material.name for s in _toe(sl)} == {"Spoil"}
            old = _bishop(p, surface, sl)
        new = _bishop(p, surface, _sliced(p, surface))
        assert old > 3.0 and new < 1.3, (old, new)

    def test_the_mirror_gives_the_same_factor(self):
        p, surface = _problem4()
        pm, sm = _problem4(mirror=True)
        slm = _sliced(pm, sm)
        assert {s.material.name for s in _toe(slm, mirror=True)} == {
            "Sheared Floor"}
        a, b = _bishop(p, surface, _sliced(p, surface)), _bishop(pm, sm, slm)
        assert abs(a - b) <= 1e-9 * a, (a, b)


# ======================================================================
def _block(upper, lower, ground_y, split_y, wet=None, joint=None, *,
           water_y=None, piezometric=False, scale=1.0, bottom=None,
           slope=False):
    """A rectangular block of two layers, the lower one listed first.

    ``upper`` and ``lower`` are (c, φ, γ); ``wet`` names the layer
    ("upper", "lower" or "both") that reads a water table at ``water_y``
    (the ground by default; a piezometric line if ``piezometric``);
    ``joint`` (c, φ) adds a weak layer along the contact; ``bottom``
    (c, φ, γ, y) a third layer under y; ``scale`` multiplies every length;
    ``slope`` cuts the left part down to 4 above the contact, through a
    face from x = 30 to 50, so that a mass slides (see ``_slope_on``).
    """
    from ogr_core.geometry import Boundary, BoundaryType
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    k = scale
    p = Project("D447 block")
    low = (split_y + 4.0) * k
    ext = _polyline([(0, 0), (100 * k, 0), (100 * k, ground_y * k)]
                    + ([(50 * k, ground_y * k), (30 * k, low), (0, low)]
                       if slope else [(0, ground_y * k)]), closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    lo = Material(name="Lower", unit_weight=lower[2],
                  strength=MohrCoulomb(cohesion=lower[0],
                                       friction_angle=lower[1]))
    up = Material(name="Upper", unit_weight=upper[2],
                  strength=MohrCoulomb(cohesion=upper[0],
                                       friction_angle=upper[1]))
    p.materials = [lo, up]
    p.add_boundary(Boundary(polyline=_polyline([(-5 * k, split_y * k),
                                                (105 * k, split_y * k)]),
                            btype=BoundaryType.MATERIAL))
    if bottom is not None:
        bm = Material(name="Bottom", unit_weight=bottom[2],
                      strength=MohrCoulomb(cohesion=bottom[0],
                                           friction_angle=bottom[1]))
        p.materials.append(bm)
        # On the external boundary, not past it like the contact above. With
        # both ends past the model the 0.3 m layer vanished from the regions
        # (D449). v0.1.463: this said why (``regions.weld_tol``) without
        # having measured it, and it is not that alone: the layer vanishes
        # too with BOTH contacts' ends on the external boundary, below some
        # 0.9 m in a 100 × 30 block (measured on 0.1.462 by the bank's
        # ``_auditoria/P10_D449/reproducir_d449.py``). It survives here
        # because the contact above ends 5 m past the model; D449 holds the
        # cause, undiagnosed.
        p.add_boundary(Boundary(polyline=_polyline([(0.0, bottom[3] * k),
                                                    (100 * k, bottom[3] * k)]),
                                btype=BoundaryType.MATERIAL))
        p.assign_material_at(50.0 * k, 0.5 * bottom[3] * k, bm.id)
    p.assign_material_at(50.0 * k, 0.5 * (split_y + ground_y) * k, up.id)
    if wet:
        y = (ground_y if water_y is None else water_y) * k
        wt = Boundary(polyline=_polyline([(-5 * k, y), (105 * k, y)]),
                      btype=(BoundaryType.PIEZOMETRIC if piezometric
                             else BoundaryType.WATER_TABLE))
        p.add_boundary(wt)
        for m in {"upper": (up,), "lower": (lo,), "both": (up, lo)}[wet]:
            m.pore_pressure = (PorePressureType.PIEZO_LINE if piezometric
                               else PorePressureType.WATER_TABLE)
            m.water_surface_id = wt.id
    jm = None
    if joint is not None:
        jm = Material(name="Joint", unit_weight=lower[2],
                      strength=MohrCoulomb(cohesion=joint[0],
                                           friction_angle=joint[1]))
        p.materials.append(jm)
        p.add_boundary(Boundary(polyline=_polyline([(-5, split_y),
                                                    (105, split_y)]),
                                btype=BoundaryType.WEAK_LAYER,
                                material_id=jm.id))
    return p, jm


def _flat_on(ground_y, split_y, scale=1.0):
    """A polyline down to the contact, along it, and back up."""
    from ogr_slip2d.surface import SlipSurface
    k = scale
    return SlipSurface(polyline=_polyline([
        (10.0 * k, ground_y * k), (20.0 * k, split_y * k),
        (80.0 * k, split_y * k), (90.0 * k, ground_y * k)]))


def _slope_on(ground_y, split_y, scale=1.0):
    """On the ``slope`` block: in at the toe, along the contact from x = 20
    to 60, and out at the crest."""
    from ogr_slip2d.surface import SlipSurface
    k = scale
    return SlipSurface(polyline=_polyline([
        (15.0 * k, (split_y + 4.0) * k), (20.0 * k, split_y * k),
        (60.0 * k, split_y * k), (80.0 * k, ground_y * k)]))


def _on_contact(sl, split_y):
    return [s for s in sl if abs(s.base_y_mid - split_y) < 1e-9]


def _materials(p):
    return {m.name: m for m in p.materials}


def _tau(s, c, phi, u):
    """c + σ′ tan φ at the base's static Fellenius stress, written here."""
    sigma = max(0.0, (s.weight + s.water_weight) * math.cos(s.base_angle)
                - u * s.base_length) / s.base_length
    return c + sigma * math.tan(_D(phi))


UPPER, LOWER = (5.0, 30.0, 15.0), (50.0, 20.0, 21.0)
#: The two envelopes cross at σ′ = (50 − 5)/(tan 30° − tan 20°) = 211 kPa.
CROSS = (LOWER[0] - UPPER[0]) / (math.tan(_D(UPPER[1]))
                                  - math.tan(_D(LOWER[1])))


class TestTheWeakerByHand:

    def test_deep_the_lower_layer_is_the_weaker(self):
        """20 m of the upper layer: σ′ = 300 kPa > 211, the lower one."""
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on                                   # premise
        for s in on:
            tu, tl = _tau(s, *UPPER[:2], 0.0), _tau(s, *LOWER[:2], 0.0)
            assert tl < tu and s.material.name == "Lower", (tu, tl)
            assert s.layer_top_y == s.base_y_mid   # the top of its layer

    def test_shallow_the_upper_layer_is_the_weaker(self):
        """8 m of it: σ′ = 120 kPa < 211, the upper one."""
        p, _ = _block(UPPER, LOWER, 18.0, 10.0)
        on = _on_contact(_sliced(p, _flat_on(18.0, 10.0), 40), 10.0)
        assert on
        for s in on:
            tu, tl = _tau(s, *UPPER[:2], 0.0), _tau(s, *LOWER[:2], 0.0)
            assert tu < tl and s.material.name == "Upper", (tu, tl)
        assert (18.0 - 10.0) * UPPER[2] < CROSS < (30.0 - 10.0) * UPPER[2]

    def test_each_side_with_its_own_water(self):
        """Deep, where dry the lower one is the weaker: water on the upper
        one makes it the weaker (σ′ 104 kPa against 300), and water on the
        lower one keeps the lower one, now with its own u."""
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        for wet, want in (("upper", "Upper"), ("lower", "Lower")):
            p, _ = _block(UPPER, LOWER, 30.0, 10.0, wet=wet)
            mats = _materials(p)
            on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
            assert on
            for s in on:
                u = {n: pore_pressure_at(p, Vertex(s.x_centre, s.base_y_mid),
                                         mats[n], ground_surface_y=30.0)
                     for n in ("Upper", "Lower")}
                tu = _tau(s, *UPPER[:2], u["Upper"])
                tl = _tau(s, *LOWER[:2], u["Lower"])
                assert s.material.name == want, (wet, tu, tl)
                assert min(tu, tl) == (tu if want == "Upper" else tl)
                assert abs(s.pore_pressure - u[want]) <= 1e-9 * max(
                    1.0, u[want])

    def test_the_ponded_water_counts_in_the_stress(self):
        """Both layers under a water table 10 m above the ground: the pond
        weighs on the base as much as it adds to u, so σ′ = (γ − γw)·20 =
        224 kPa > 211 and the lower one is the weaker; without the pond in
        σ′ it would be 126 kPa and the upper one."""
        heavy = (UPPER[0], UPPER[1], 21.0)
        p, _ = _block(heavy, LOWER, 30.0, 10.0, wet="both", water_y=40.0)
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on
        for s in on:
            assert s.water_weight > 0.0                    # premise
            dry = (s.weight * math.cos(s.base_angle)
                   - s.pore_pressure * s.base_length) / s.base_length
            assert _tau(s, *heavy[:2], s.pore_pressure) > _tau(
                s, *LOWER[:2], s.pore_pressure)
            assert dry < CROSS, dry
            assert s.material.name == "Lower"

    def test_the_stress_is_clipped_at_zero_under_an_artesian_head(self):
        """The lower layer under a piezometric head 20 m above the base, 12
        above the ground: u = 196 kPa against 120 of overburden, σ′ = 0 and
        its τ is its c = 100 > 74 of the upper one. Unclipped, σ′ = −76
        and its τ would be 72, under the upper one."""
        strong_c = (100.0, LOWER[1], LOWER[2])
        p, _ = _block(UPPER, strong_c, 18.0, 10.0, wet="lower", water_y=30.0,
                      piezometric=True)
        on = _on_contact(_sliced(p, _flat_on(18.0, 10.0), 40), 10.0)
        assert on
        for s in on:
            assert s.water_weight == 0.0 and s.pore_pressure == 0.0
            u = 9.81 * 20.0
            raw = (s.weight * math.cos(s.base_angle)
                   - u * s.base_length) / s.base_length
            unclipped = strong_c[0] + raw * math.tan(_D(strong_c[1]))
            assert raw < 0.0 and unclipped < _tau(s, *UPPER[:2], 0.0)
            assert s.material.name == "Upper"

    def test_the_stress_is_fellenius_on_an_inclined_base_too(self):
        """On a base inclined 35°, σ′ = (W cos α − u·l)/l, written here: with
        W/b = 300 kPa it is 201 kPa, under the 211 at which the envelopes
        cross, so the upper layer is the weaker; read without the cosine it
        would be 246 and the lower one."""
        import ogr_slip2d.slicer as S
        from ogr_core.materials import Material, MohrCoulomb
        a = _D(35.0)
        b = 10.0
        s = S.Slice(index=0, x_centre=5.0, width=b, base_x_left=0.0,
                    base_x_right=b, base_y_left=0.0,
                    base_y_right=b * math.tan(a), base_angle=a,
                    base_length=b / math.cos(a), top_y_left=20.0,
                    top_y_right=20.0, weight=300.0 * b, soil_weight=300.0 * b,
                    pore_pressure=0.0)
        up = Material(name="Upper", unit_weight=UPPER[2],
                      strength=MohrCoulomb(cohesion=UPPER[0],
                                           friction_angle=UPPER[1]))
        lo = Material(name="Lower", unit_weight=LOWER[2],
                      strength=MohrCoulomb(cohesion=LOWER[0],
                                           friction_angle=LOWER[1]))
        sigma = 300.0 * b * math.cos(a) / s.base_length
        assert abs(sigma - 201.3) < 0.1 and sigma < CROSS
        for m, (c, phi, _g) in ((up, UPPER), (lo, LOWER)):
            want = c + sigma * math.tan(_D(phi))
            assert abs(S._contact_strength(s, m) - want) <= 1e-9 * want
        assert S._contact_strength(s, up) < S._contact_strength(s, lo)

    def test_a_tie_keeps_the_one_above(self):
        """The same c and φ below, heavier: the same τ, so the one above."""
        p, _ = _block(UPPER, (UPPER[0], UPPER[1], 21.0), 30.0, 10.0)
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on and {s.material.name for s in on} == {"Upper"}

    def test_the_old_rule_reads_the_upper_layer(self):
        import ogr_slip2d.slicer as S
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        with _rule("above"):
            on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on and {s.material.name for s in on} == {"Upper"}
        per_call = S.slice_surface(p, _flat_on(30.0, 10.0), num_slices=40,
                                   base_on_contact="above")
        assert {s.material.name for s in _on_contact(per_call, 10.0)} == {
            "Upper"}


class TestOnlyABaseThatRunsAlongIt:
    """The detection is the model's own resolution, ``_model_grid_tol``
    (1.1e-4 here): a base closer than that to the contact is ON it."""

    def test_within_the_resolution_it_is_on_the_contact(self):
        import ogr_slip2d.slicer as S
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        dy = 0.5 * S._model_grid_tol(p)
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0 + dy), 40),
                         10.0 + dy)
        assert on and {s.material.name for s in on} == {"Lower"}

    def test_five_millimetres_above_it_keeps_the_upper_layer(self):
        """Even along a line drawn there: a water table, which is no
        contact between materials."""
        from ogr_core.geometry import Boundary, BoundaryType
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        p.add_boundary(Boundary(polyline=_polyline([(-5.0, 10.005),
                                                    (105.0, 10.005)]),
                                btype=BoundaryType.WATER_TABLE))
        s = _flat_on(30.0, 10.005)
        a = _sliced(p, s, 40)
        with _rule("above"):
            b = _sliced(p, s, 40)
        assert {x.material.name for x in _on_contact(a, 10.005)} == {"Upper"}
        _same_slices(a, b)

    def test_a_base_over_a_dip_of_the_contact_keeps_its_material(self):
        """The contact dips 5 mm between x = 49 and 51, and the base from 49
        to 51 spans the dip: its ends are on the contact, its middle 5 mm
        above it, in the upper layer. Its neighbours run along the contact
        and take the weaker."""
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        p = Project("D447 dip")
        ext = _polyline([(0, 0), (100, 0), (100, 30), (0, 30)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        lo = Material(name="Lower", unit_weight=LOWER[2],
                      strength=MohrCoulomb(cohesion=LOWER[0],
                                           friction_angle=LOWER[1]))
        up = Material(name="Upper", unit_weight=UPPER[2],
                      strength=MohrCoulomb(cohesion=UPPER[0],
                                           friction_angle=UPPER[1]))
        p.materials = [lo, up]
        p.add_boundary(Boundary(polyline=_polyline([
            (-5, 10), (49.0, 10), (50.0, 9.995), (51.0, 10), (105, 10)]),
            btype=BoundaryType.MATERIAL))
        p.assign_material_at(50.0, 25.0, up.id)
        sl = _sliced(p, _flat_on(30.0, 10.0), 40)
        over = [s for s in sl if s.base_x_left == 49.0]
        assert len(over) == 1 and over[0].base_x_right == 51.0   # premise
        assert over[0].material is up
        beside = [s for s in sl if s.base_x_right == 49.0
                  or s.base_x_left == 51.0]
        assert len(beside) == 2 and all(s.material is lo for s in beside)

    def test_the_bottom_of_a_tangent_circle_keeps_its_material(self):
        """The circle (50, 35, R 25) touches the contact at (50, 10). The two
        bases beside the tangent point end on the contact and their middles
        are 2.5 mm above it, where the probe below already reads the lower
        layer: they cross no contact, and keep the upper one."""
        import ogr_slip2d.slicer as S
        from ogr_core.geometry.slip_circle import SlipCircle
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        c = SlipCircle(centre_x=50.0, centre_y=35.0, radius=25.0)
        a = S.slice_surface(p, c, num_slices=98)
        with _rule("above"):
            b = S.slice_surface(p, c, num_slices=98)
        below = S._BELOW_IN_GRID * S._model_grid_tol(p)
        reach = [s for s in a
                 if S._lift_and_below(p, s.x_centre, s.base_y_mid, below)[1]
                 is _materials(p)["Lower"]]
        assert len(reach) == 2, len(reach)                 # premise
        assert {s.material.name for s in a} == {"Upper"}
        _same_slices(a, b)


class TestTheResolutionIsTheModels:

    def test_a_thin_layer_under_the_contact_at_three_scales(self):
        """0.3 m of the lower layer over a strong bottom (1 % of the model's
        height), copied at 1/50 (6 mm) and at 1000×: the deep bases on the
        contact read the thin layer at every scale, and Bishop gives the
        same factor (lengths and c scaled, γ and φ kept: every force goes as
        k², every moment as k³ and F does not move)."""
        Fs, names = [], []
        for k in (1.0, 1.0 / 50.0, 1000.0):
            up = (UPPER[0] * k, UPPER[1], UPPER[2])
            lo = (LOWER[0] * k, LOWER[1], LOWER[2])
            p, _ = _block(up, lo, 30.0, 10.0, scale=k, slope=True,
                          bottom=(200.0 * k, 45.0, 21.0, 9.7))
            s = _slope_on(30.0, 10.0, scale=k)
            sl = _sliced(p, s, 40)
            on = _on_contact(sl, 10.0 * k)
            names.append([x.material.name for x in on])
            Fs.append(_bishop(p, s, sl))
        assert "Lower" in names[0] and names[1] == names[0] == names[2], names
        assert all(abs(F / Fs[0] - 1.0) <= 1e-9 for F in Fs), Fs


class TestTheCandidateReadsItsOwnMaterial:

    def test_its_ru(self):
        """u = Ru·γ·z of the lower material (Bishop and Morgenstern 1960):
        0.5 × 21 × 20 = 210 kPa."""
        from ogr_core.materials import PorePressureType
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        lo = _materials(p)["Lower"]
        lo.pore_pressure, lo.ru = PorePressureType.RU_COEFFICIENT, 0.5
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on
        for s in on:
            assert s.material is lo
            assert abs(s.pore_pressure - 0.5 * 21.0 * 20.0) <= 1e-9, \
                s.pore_pressure

    def test_the_water_of_a_generalized_child(self):
        """A Generalized Anisotropic lower material that does not take the
        parent's water reads its child's Ru, times the PARENT's weight
        (D230): 0.3 × 21 × 20 = 126 kPa, not 0.3 × 18 × 20; and says whose
        water it read."""
        from ogr_core.materials import Material, MohrCoulomb, PorePressureType
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        lo = _materials(p)["Lower"]
        child = Material(name="Child", unit_weight=18.0,
                         strength=MohrCoulomb(cohesion=LOWER[0],
                                              friction_angle=LOWER[1]),
                         pore_pressure=PorePressureType.RU_COEFFICIENT)
        child.ru = 0.3
        lo.strength = GeneralizedAnisotropic(rules=[{
            "angle_min": -90.0, "angle_max": 90.0,
            "model": child.strength.to_dict(), "material_id": child.id}],
            use_parent_water=False)
        p.materials.append(child)
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on
        for s in on:
            assert s.material is lo and s.water_material is child
            assert abs(s.pore_pressure - 0.3 * 21.0 * 20.0) <= 1e-9, \
                s.pore_pressure

    def test_its_suction(self):
        """Matric suction of the lower material (extended Mohr–Coulomb,
        Fredlund, Morgenstern and Widger 1978): with φb = 15° and no air
        entry value, a suction s = 49.05 kPa (a water table 5 m under the
        base) leaves u = 0 and adds s·tan φb = 13.14 kPa of cohesion. The
        field is linear and stands in for a seepage solution, whose T3
        interpolation is exact on it."""
        import types
        from ogr_core.materials import PorePressureType
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        lo = _materials(p)["Lower"]
        lo.pore_pressure, lo.phi_b = PorePressureType.FEM_SEEPAGE, 15.0
        p.fem_mesh = types.SimpleNamespace(
            interpolate=lambda vals, x, y: 9.81 * (5.0 - y))
        p.seepage_result = types.SimpleNamespace(pore_pressure=[0.0])
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on
        s_ = 9.81 * 5.0
        for s in on:
            assert s.material is lo and s.pore_pressure == 0.0
            assert abs(s.raw_pore_pressure + s_) <= 1e-9
            assert abs(s.suction_cohesion - s_ * math.tan(_D(15.0))) <= 1e-9

    def test_its_excess_under_a_line_load_on_a_cut(self):
        """B̄ = 1 below (Skempton 1954, Δu = B̄·Δσv): a line load on a cut
        between two bases on the contact loads each with half of itself,
        and Σ Δu·b over the slices is the load, once (D427)."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads import LineLoad, LoadOrientation
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        p.settings.groundwater.excess_pore_pressure = True
        _materials(p)["Lower"].b_bar = 1.0
        s = _flat_on(30.0, 10.0)
        cut = _on_contact(_sliced(p, s, 40), 10.0)[10].base_x_right
        P = 500.0
        ld = LineLoad(point=Vertex(cut, 30.0), magnitude=P,
                      orientation=LoadOrientation.VERTICAL, name="L")
        ld.creates_excess_pore_pressure = True
        p.line_loads = [ld]
        sl = _sliced(p, s, 40)
        loaded = [x for x in sl if x.pore_pressure > 0.0]
        assert len(loaded) == 2 and {x.material.name for x in loaded} == {
            "Lower"}, [(x.index, x.material.name) for x in loaded]
        got = math.fsum(x.pore_pressure * x.width for x in sl)
        assert abs(got - P) <= 1e-9 * P, got

    def test_its_bedding(self):
        """An anisotropic surface of the lower material, dipping
        atan(1/2) = 26.57°: the bases on the contact read it, the others
        (upper material) read none."""
        from ogr_core.geometry import Boundary, BoundaryType
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        b = Boundary(polyline=_polyline([(0.0, 0.0), (100.0, 50.0)]),
                     btype=BoundaryType.ANISOTROPIC_SURFACE)
        p.add_boundary(b)
        _materials(p)["Lower"].anisotropic_surface_id = b.id
        sl = _sliced(p, _flat_on(30.0, 10.0), 40)
        on = _on_contact(sl, 10.0)
        assert on and {s.material.name for s in on} == {"Lower"}
        want = math.degrees(math.atan2(50.0, 100.0))
        for s in on:
            assert abs(s.bedding_angle_deg - want) <= 1e-9, s.bedding_angle_deg
        assert all(s.bedding_angle_deg is None for s in sl if s not in on)

    def test_its_joint_surfaces(self):
        """A Generalized Anisotropic lower material whose joint is a
        horizontal anisotropic surface: the bases on the contact read its
        orientation, 0°."""
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import MohrCoulomb
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        b = Boundary(polyline=_polyline([(-5.0, 5.0), (105.0, 5.0)]),
                     btype=BoundaryType.ANISOTROPIC_SURFACE)
        p.add_boundary(b)
        mc = MohrCoulomb(cohesion=LOWER[0], friction_angle=LOWER[1])
        _materials(p)["Lower"].strength = GeneralizedAnisotropic(
            input_type="angle_or_surface", base={"model": mc.to_dict()},
            joints=[{"surface_id": b.id, "A": 10.0, "B": 10.0,
                     "model": mc.to_dict()}],
            definition="surface", mapping="ab")
        on = _on_contact(_sliced(p, _flat_on(30.0, 10.0), 40), 10.0)
        assert on and {s.material.name for s in on} == {"Lower"}
        for s in on:
            assert s.surface_angles == {b.id: 0.0}, s.surface_angles

    def test_its_water_must_reach_the_base(self):
        """The lower material's water table stops at x = 40, over the run on
        the contact (20 to 80): the surface is refused, as it is when the
        water of the base's own material does not reach it (v0.1.96). The
        old rule never asks the lower material, and slices it."""
        import ogr_slip2d.slicer as S
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import PorePressureType
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        wt = Boundary(polyline=_polyline([(-5.0, 30.0), (40.0, 30.0)]),
                      btype=BoundaryType.WATER_TABLE)
        p.add_boundary(wt)
        lo = _materials(p)["Lower"]
        lo.pore_pressure, lo.water_surface_id = (
            PorePressureType.WATER_TABLE, wt.id)
        s = _flat_on(30.0, 10.0)
        assert S.slice_surface(p, s, num_slices=40) is None
        with _rule("above"):
            assert S.slice_surface(p, s, num_slices=40) is not None


class TestJamesBay:
    """Duncan, Wright and Brandon (2014, §7.7.6, Figs. 7.24 and 7.29): the
    flat run of the critical surface lies on the top of the till, and its
    bases are the lacustrine clay above (su = 31.5 kPa, the figure's slices
    5–8). The till is "very strong": here su = 300 kPa, and any value above
    the clay's gives the same."""

    def test_the_flat_run_on_the_till_is_lacustrine(self):
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import Undrained
        from ogr_core.project import Project
        p = Project("D447 James Bay")
        ext = _polyline([(0, -30.0), (100, -30.0), (100, 0.0), (0, 0.0)],
                        closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        till = Material(name="Till", unit_weight=22.0,
                        strength=Undrained(cohesion=300.0))
        clay = Material(name="Lacustrine", unit_weight=20.3,
                        strength=Undrained(cohesion=31.5))
        p.materials = [till, clay]
        p.add_boundary(Boundary(polyline=_polyline([(-5, -18.5),
                                                    (105, -18.5)]),
                                btype=BoundaryType.MATERIAL))
        p.assign_material_at(50.0, -9.0, clay.id)
        for rule in ("weaker", "above"):
            with _rule(rule):
                on = _on_contact(_sliced(p, _flat_on(0.0, -18.5), 40), -18.5)
            assert on and {s.material.name for s in on} == {"Lacustrine"}, \
                rule


class TestAWeakLayerStillWins:

    def test_a_joint_on_the_contact_gives_the_joints_material(self):
        """The surface dips under the joint, which clips it onto itself (a
        surface that only grazes a joint does not take its strength, as in
        test_weak_layer_v1121): the clipped run lies on the contact. The
        joint is STRONGER than both layers, so it is the joint by rule and
        not by being the weakest."""
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipSurface
        p, jm = _block(UPPER, LOWER, 30.0, 10.0, joint=(200.0, 45.0))
        ev = GridSearch(method=build_method(p, "bishop_simplified", 40),
                        num_slices=40, min_area=0.0)
        under = SlipSurface(polyline=_polyline([(10.0, 30.0), (20.0, 8.0),
                                                (80.0, 8.0), (90.0, 30.0)]))
        with p.regions_frozen():
            res = ev.evaluate_surface(p, under)
        on = _on_contact(res.slices, 10.0)
        assert on and {s.material.id for s in on} == {jm.id}
        assert all(s.weak_layer_id for s in on)


class TestRapidDrawdownKeepsTheRuleAbove:
    """A slope under a reservoir at 40 drawn down to 5, both layers with
    the undrained envelopes of rapid drawdown, the upper one of γ = 21, and
    a surface that runs on the contact at 10. The lower layer is the weaker
    where σ′ passes 211 kPa: under the reservoir, σ′ = (γ − γw)·z, only at
    the deep end of the run; drawn down, σ′ = γ·z, along most of it. The
    two levels of one analysis would read different materials on the same
    base. Rapid drawdown asks the slicer for the one above (owner's
    decision, 2026-11-16, until its own ficha), so both rules give its four
    procedures the same factor, to the last bit."""

    @staticmethod
    def _slope():
        from ogr_core.geometry import Boundary, BoundaryType
        from ogr_core.materials import Material, MohrCoulomb, PorePressureType
        from ogr_core.materials.drawdown_envelopes import REnvelope
        from ogr_core.project import Project
        p = Project("D447 drawdown")
        ext = _polyline([(0, 0), (100, 0), (100, 30), (50, 30), (30, 14),
                         (0, 14)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        lo = Material(name="Lower", unit_weight=LOWER[2],
                      strength=MohrCoulomb(cohesion=LOWER[0],
                                           friction_angle=LOWER[1]))
        up = Material(name="Upper", unit_weight=21.0,
                      strength=MohrCoulomb(cohesion=UPPER[0],
                                           friction_angle=UPPER[1]))
        p.materials = [lo, up]
        p.add_boundary(Boundary(polyline=_polyline([(-5, 10), (105, 10)]),
                                btype=BoundaryType.MATERIAL))
        p.assign_material_at(50.0, 20.0, up.id)
        wt = Boundary(polyline=_polyline([(-5, 40), (105, 40)]),
                      btype=BoundaryType.WATER_TABLE)
        p.add_boundary(wt)
        p.add_boundary(Boundary(polyline=_polyline([(-5, 5), (105, 5)]),
                                btype=BoundaryType.DRAWDOWN))
        for m, env in ((up, REnvelope(c_r=5.0, phi_r_deg=20.0)),
                       (lo, REnvelope(c_r=40.0, phi_r_deg=14.0))):
            m.pore_pressure = PorePressureType.WATER_TABLE
            m.water_surface_id = wt.id
            m.undrained_behaviour = True
            m.b_bar = 1.0
            m.drawdown_envelope = env
        p.settings.groundwater.rapid_drawdown = True
        return p

    @staticmethod
    def _surface():
        from ogr_slip2d.surface import SlipSurface
        return SlipSurface(polyline=_polyline([(15.0, 14.0), (20.0, 10.0),
                                               (60.0, 10.0), (80.0, 30.0)]))

    def test_the_two_levels_would_choose_differently(self):
        from ogr_core.hydraulic.drawdown_levels import level_project
        p = self._slope()
        names = {}
        for use in (False, True):
            on = _on_contact(_sliced(level_project(p, use_drawdown=use),
                                     self._surface(), 40), 10.0)
            assert on
            names[use] = [s.material.name for s in on]
        lower = {u: names[u].count("Lower") for u in names}
        assert 0 < lower[False] < lower[True] < len(names[True]), names

    def test_its_four_procedures_do_not_depend_on_the_rule(self):
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch
        p = self._slope()
        for proc in ("b_bar", "duncan_wright", "corps_2", "lowe_karafiath"):
            p.settings.groundwater.rapid_drawdown_method = proc
            got = []
            for rule in ("weaker", "above"):
                with _rule(rule):
                    ev = GridSearch(method=build_method(p, "spencer", 40),
                                    num_slices=40, min_area=0.0)
                    got.append(ev.evaluate_surface(p, self._surface()).fos)
            assert got[0] is not None and got[0].hex() == got[1].hex(), (
                proc, got)


class TestNothingMovesOffAContact:

    def test_an_oblique_surface_slices_the_same_under_both_rules(self):
        from ogr_slip2d.surface import SlipSurface
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        oblique = SlipSurface(polyline=_polyline([(10.0, 30.0), (50.0, 5.0),
                                                  (90.0, 30.0)]))
        a = _sliced(p, oblique, 40)
        with _rule("above"):
            b = _sliced(p, oblique, 40)
        assert not _on_contact(a, 10.0)              # premise
        _same_slices(a, b)

    def test_a_rule_that_is_not_one_is_an_error(self):
        import ogr_slip2d.slicer as S
        p, _ = _block(UPPER, LOWER, 30.0, 10.0)
        for kwargs, module in (({"base_on_contact": "below"}, None),
                               ({}, "Below")):
            with _rule(module or S.BASE_ON_CONTACT):
                try:
                    S.slice_surface(p, _flat_on(30.0, 10.0), num_slices=40,
                                    **kwargs)
                except ValueError:
                    continue
            raise AssertionError((kwargs, module))
