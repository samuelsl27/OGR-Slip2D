# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.124 — the helical anchor, and what it is anchored to.

The invariant this file protects is that the capacity of a helical anchor
is DEDUCED and not entered: seven capacities computed from the soil around
it compete at every point, and the applied force is the smallest. That
makes it the kind of thing a snapshot test would happily consecrate wrong,
so nothing here compares against what this program printed yesterday.

What it compares against instead:

  * a **published hand calculation** with all five intermediates and a
    table of eleven positions by seven capacities. Seventy-seven numbers
    from outside this project, none of them produced by it;
  * **closed forms**: N_c -> 2 + pi as phi -> 0 (Prandtl 1921), N_q(0) = 1;
  * **analytical identities** that hold whatever the numbers are: one
    helix makes cylindrical shear and individual bearing equal exactly; a
    shaft as wide as the helix leaves no bearing area; no plate beyond the
    cut means no pullout at all; and ``force_at`` is the minimum of the
    modes for every registered type, which is what stops two writings of
    the same formula from drifting apart.

Three of those seventy-seven numbers do real work on their own: the rows
where a plate sits EXACTLY on the slip surface. They are what says the
plate counts on neither side, and nothing else in the published material
says it.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

import math

# Published in the reference's verification problem 111, all of it from
# the hand calculation and its Table 111.1.
PUB_TAU = 78.0187          # kPa, soil shear strength along the shaft
PUB_AREA = 0.023562        # m2, equivalent projected area of one helix
PUB_NQ = 33.2961
PUB_NC = 46.1236
PUB_PERIM_TAU = 49.0206    # kN/m, pi * D * tau
PUB_BEARING = 91.7987      # kN, one plate
PUB_APPLIED = 73.5309      # kN/m of slope, at 3.5 m from the head

# Table 111.1: distance from head -> (pullout shallow, pullout individual
# bearing, pullout cylindrical shear, stripping shallow, stripping
# individual bearing, stripping cylindrical shear, applied).
PUB_TABLE = {
    0.0: (245.1029, 275.3961, 189.8399, 80.0, 80.0, 80.0, 80.0),
    0.5: (220.5926, 275.3961, 189.8399, 80.0, 80.0, 80.0, 80.0),
    1.0: (196.0823, 275.3961, 189.8399, 80.0, 80.0, 80.0, 80.0),
    1.5: (171.5720, 275.3961, 189.8399, 80.0, 80.0, 80.0, 80.0),
    2.0: (147.0617, 275.3961, 189.8399, 80.0, 80.0, 80.0, 80.0),
    2.5: (122.5515, 275.3961, 189.8399, 80.0, 80.0, 80.0, 80.0),
    3.0: (98.0412, 183.5974, 140.8193, 80.0, 80.0, 80.0, 80.0),
    3.5: (73.5309, 183.5974, 140.8193, 104.5103, 171.7987, 171.7987,
          73.5309),
    4.0: (49.0206, 91.7987, 91.7987, 129.0206, 171.7987, 171.7987,
          49.0206),
    4.5: (24.5103, 91.7987, 91.7987, 153.5309, 263.5974, 220.8193,
          24.5103),
    5.0: (0.0, 0.0, 0.0, 178.0412, 263.5974, 220.8193, 0.0),
}

# The model of figure 111.1, labelled point by point.
EXTERNAL = [(0.0, 0.0), (15.0, 0.0), (15.0, 12.0),
            (7.5, 12.0), (7.5, 5.0), (0.0, 5.0)]
SOIL = dict(gamma=20.0, c=15.0, phi=35.0)
HEAD = (7.5, 7.5)
TAIL = (12.5, 7.5)
SURFACE = [(7.5, 5.0), (11.0, 7.5), (12.4, 12.0)]


def _anchor(**kw):
    """The support type of figure 111.1."""
    from ogr_core.support import HelicalAnchor
    args = dict(tensile_capacity=85.0, head_assembly_capacity=80.0,
                shear_capacity=0.0, out_of_plane_spacing=1.0,
                shaft_type="round", shaft_width=0.1, number_of_helices=3,
                average_helix_diameter=0.2, helix_spacing=1.0)
    args.update(kw)
    return HelicalAnchor(**args)


def _project(orientation="tangent_to_slip", with_anchor=True, **kw):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)

    p = Project("verification 111 - helical anchor")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in EXTERNAL], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="Soil", unit_weight=SOIL["gamma"],
                   sat_unit_weight=SOIL["gamma"],
                   strength=MohrCoulomb(cohesion=SOIL["c"],
                                        friction_angle=SOIL["phi"]),
                   pore_pressure=PorePressureType.NONE)
    p.materials = [mat]
    for reg in p.resolve_regions():
        v = reg.polygon.vertices
        p.assign_material_at(sum(q.x for q in v) / len(v),
                             sum(q.y for q in v) / len(v), mat.id)
    p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
    p.settings.methods.num_slices = 50
    if with_anchor:
        stype = _anchor(**kw)
        p.support_types = [stype]
        p.supports.append(SupportInstance(
            type_id=stype.TYPE_ID,
            head=Vertex(*HEAD), tail=Vertex(*TAIL),
            orientation=ForceOrientation(orientation),
            force_application=ForceApplication.ACTIVE))
    return p


def _surface():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in SURFACE]))


def _bond(project):
    from ogr_core.support import build_bond_profile
    return build_bond_profile(project, project.supports[0],
                              project.support_types[0])


def _uniform_bond(tau=PUB_TAU, length=5.0, bearing=PUB_BEARING,
                  plates=(3.0, 4.0, 5.0)):
    """A profile with the published values, and no project behind it."""
    from ogr_core.support import BondProfile
    return BondProfile.from_samples(
        (tau,), length, tuple((d, bearing) for d in plates))


def _fos(method_id, project, surface=None, num_slices=50):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    surface = surface or _surface()
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None and sl.slices
    return method_registry()[method_id]().compute_fos(
        project, surface, sl).fos


def _method_ids():
    from ogr_slip2d.methods.base import method_registry
    return sorted(method_registry())


# ======================================================================
class TestTheBearingFactors:
    """Prandtl (1921) and Reissner (1924), and their limit at zero."""

    def test_the_published_pair(self):
        from ogr_core.support import bearing_factors
        n_q, n_c = bearing_factors(math.radians(35.0))
        assert abs(n_q - PUB_NQ) < 5e-5, n_q
        assert abs(n_c - PUB_NC) < 5e-5, n_c

    def test_it_agrees_with_the_literal_form_where_that_is_safe(self):
        """Away from zero the rewriting must change nothing at all.

        The point of ``expm1``/``log1p`` is the neighbourhood of zero; if
        it moved the answer anywhere else it would be a different formula
        rather than a better evaluation of the same one.
        """
        from ogr_core.support import bearing_factors
        for deg in (5, 10, 20, 30, 35, 40, 45):
            phi = math.radians(deg)
            naive_q = (math.exp(math.pi * math.tan(phi))
                       * math.tan(math.radians(45.0 + deg / 2.0)) ** 2)
            naive_c = (naive_q - 1.0) / math.tan(phi)
            n_q, n_c = bearing_factors(phi)
            assert abs(n_q - naive_q) < 1e-11 * naive_q, (deg, n_q, naive_q)
            assert abs(n_c - naive_c) < 1e-11 * naive_c, (deg, n_c, naive_c)

    def test_nc_reaches_two_plus_pi_without_a_threshold(self):
        """The closed form of Prandtl (1921) at phi = 0, by continuity.

        The convergence is FIRST ORDER, so what is checked is that the
        gap divided by phi settles on a constant and stays there for ten
        decades. That is what tells converging from wandering: the literal
        ``(N_q - 1) cot phi`` loses every digit down here, and a version
        that had not been rewritten would drift, blow up, or simply stop
        improving somewhere in this range. It does none of the three.
        """
        from ogr_core.support import NC_AT_ZERO_FRICTION, bearing_factors
        assert abs(NC_AT_ZERO_FRICTION - (2.0 + math.pi)) < 1e-15
        slopes = []
        previous = None
        for exponent in range(2, 13):
            phi = 10.0 ** -exponent
            _, n_c = bearing_factors(phi)
            gap = abs(n_c - NC_AT_ZERO_FRICTION)
            assert gap < 20.0 * phi, (exponent, n_c)
            if previous is not None:
                assert gap < previous, (exponent, gap, previous)
            previous = gap
            slopes.append(gap / phi)
        # Settled on a constant, which is the derivative of N_c at zero:
        # first-order convergence, ten decades of it, no threshold.
        assert abs(slopes[-1] - slopes[-4]) < 1e-3, slopes
        assert 13.0 < slopes[-1] < 13.5, slopes[-1]
        assert bearing_factors(0.0) == (1.0, NC_AT_ZERO_FRICTION)

    def test_nq_is_one_and_both_grow_with_friction(self):
        from ogr_core.support import bearing_factors
        assert bearing_factors(0.0)[0] == 1.0
        last = (0.0, 0.0)
        for deg in range(0, 50, 5):
            pair = bearing_factors(math.radians(deg))
            assert pair[0] > last[0] and pair[1] > last[1], deg
            last = pair

    def test_a_friction_angle_of_ninety_degrees_is_refused(self):
        """Not clamped: there is no sensible answer, and inventing one is
        how an impossible input becomes a plausible number."""
        from ogr_core.support import bearing_factors
        for bad in (0.5 * math.pi, 2.0, float("nan"), float("inf")):
            try:
                bearing_factors(bad)
            except ValueError:
                continue
            raise AssertionError(f"accepted {bad}")


# ======================================================================
class TestTheEquivalentProjectedArea:
    def test_the_published_area(self):
        from ogr_core.support import equivalent_projected_area
        a = equivalent_projected_area(0.2, 0.1, "round")
        assert abs(a - PUB_AREA) < 5e-7, a
        assert abs(a - math.pi / 4.0 * (0.2 ** 2 - 0.1 ** 2)) < 1e-15

    def test_a_square_shaft_eats_more_of_the_plate(self):
        from ogr_core.support import equivalent_projected_area
        round_ = equivalent_projected_area(0.2, 0.1, "round")
        square = equivalent_projected_area(0.2, 0.1, "square")
        assert square < round_
        assert abs(square - (math.pi / 4.0 * 0.04 - 0.01)) < 1e-15

    def test_a_shaft_as_wide_as_the_helix_leaves_no_plate(self):
        """Exact, and it is the sharpest check on the two areas: any slip
        in either coefficient and the difference stops vanishing."""
        from ogr_core.support import equivalent_projected_area
        assert equivalent_projected_area(0.3, 0.3, "round") == 0.0
        assert equivalent_projected_area(0.3, 0.4, "round") == 0.0
        # A square shaft inscribed in the helix circle leaves a real plate;
        # one whose SIDE equals the diameter swallows it.
        assert equivalent_projected_area(0.3, 0.3, "square") == 0.0
        assert equivalent_projected_area(0.3, 0.2, "square") > 0.0


# ======================================================================
class TestThePublishedHandCalculation:
    """Problem 111, number by number, with nothing from this project."""

    def test_the_shear_strength_and_the_plate_bearing(self):
        from ogr_core.support import plate_bearing
        phi = math.radians(SOIL["phi"])
        sigma_v = SOIL["gamma"] * (12.0 - 7.5)
        assert abs(sigma_v - 90.0) < 1e-12
        tau = SOIL["c"] + sigma_v * math.tan(phi)
        assert abs(tau - PUB_TAU) < 5e-5, tau
        assert abs(math.pi * 0.2 * tau - PUB_PERIM_TAU) < 5e-5
        q = plate_bearing(PUB_AREA, SOIL["c"], phi, sigma_v)
        assert abs(q - PUB_BEARING) < 2e-3, q

    def test_the_worked_point_at_three_and_a_half_metres(self):
        """The six capacities the manual writes out longhand."""
        stype = _anchor()
        modes = stype.capacity_modes(3.5, 5.0, _uniform_bond())
        assert abs(modes["pullout_shallow"] - 73.5309) < 1e-3
        assert abs(modes["pullout_cylindrical"] - 140.8193) < 1e-3
        assert abs(modes["pullout_bearing"] - 183.5974) < 1e-3
        assert abs(modes["stripping_shallow"] - 104.5103) < 1e-3
        assert abs(modes["stripping_cylindrical"] - 171.7987) < 1e-3
        assert abs(modes["stripping_bearing"] - 171.7987) < 1e-3
        assert abs(modes["tensile"] - 85.0) < 1e-12

    def test_the_whole_of_table_111_1(self):
        """Seventy-seven published numbers, and none of them ours."""
        stype = _anchor()
        bond = _uniform_bond()
        for d, row in PUB_TABLE.items():
            m = stype.capacity_modes(d, 5.0, bond)
            got = (m["pullout_shallow"], m["pullout_bearing"],
                   m["pullout_cylindrical"], m["stripping_shallow"],
                   m["stripping_bearing"], m["stripping_cylindrical"],
                   stype.force_at(d, 5.0, bond))
            for name, a, b in zip(
                    ("p-shallow", "p-bearing", "p-cyl", "s-shallow",
                     "s-bearing", "s-cyl", "applied"), got, row):
                assert abs(a - b) < 1e-3, (d, name, a, b)

    def test_the_published_force_diagram_every_tenth_of_a_metre(self):
        """The second published anchor, and the one the table misses.

        The reference draws the diagram with a value every 0.1 m, and
        between the first plate and 3.266 m the governing mode changes
        TWICE — stripping, then the tendon, then pullout — inside a
        stretch no row of Table 111.1 falls in. Without these the tensile
        mode could be dropped entirely and all seventy-seven numbers of
        the table would still pass.
        """
        stype = _anchor()
        bond = _uniform_bond()
        published = {
            3.1: 84.9021, 3.3: 83.3350, 3.4: 78.4329, 3.5: 73.5309,
            3.6: 68.6288, 3.7: 63.7268, 3.8: 58.8247, 3.9: 53.9226,
            4.0: 49.0206, 4.1: 44.1185, 4.2: 39.2165, 4.3: 34.3144,
            4.4: 29.4123, 4.5: 24.5103, 4.6: 19.6082, 4.9: 4.9021,
        }
        for d, value in published.items():
            got = stype.force_at(d, 5.0, bond)
            assert abs(got - value) < 1e-3, (d, got, value)
        for d in (0.0, 1.0, 2.0, 3.0):
            assert abs(stype.force_at(d, 5.0, bond) - 80.0) < 1e-9, d
        # the plateau at the tendon, and the two crossings that bound it
        assert abs(stype.force_at(3.2, 5.0, bond) - 85.0) < 1e-9
        assert abs((3.0 + (85.0 - 80.0) / PUB_PERIM_TAU) - 3.102) < 1e-3
        assert abs((5.0 - 85.0 / PUB_PERIM_TAU) - 3.266) < 1e-3

    def test_the_published_colours_say_which_mode_governs(self):
        """The diagram is drawn mode by mode — cyan for stripping, red for
        the tendon, green for pullout — so WHICH capacity wins is
        published as well as its value. Nothing else pins the competition
        itself, and the competition is the whole model."""
        stype = _anchor()
        bond = _uniform_bond()

        def governing(d):
            modes = stype.capacity_modes(d, 5.0, bond)
            return min(modes, key=lambda k: modes[k]).split("_")[0]
        assert governing(1.0) == "stripping"
        assert governing(3.05) == "stripping"
        assert governing(3.2) == "tensile"
        assert governing(3.5) == "pullout"
        assert governing(4.9) == "pullout"


# ======================================================================
class TestThePlateExactlyOnTheCut:
    """Three rows of the published table, and what only they can say."""

    def test_a_plate_on_the_surface_counts_on_neither_side(self):
        stype = _anchor()
        bond = _uniform_bond()
        # At 4.0 m the middle plate is exactly on the cut: pullout sees
        # ONE plate beyond (91.7987, not 183.5974) and stripping sees ONE
        # behind (171.7987, not 263.5974).
        m = stype.capacity_modes(4.0, 5.0, bond)
        assert abs(m["pullout_bearing"] - PUB_BEARING) < 1e-3
        assert abs(m["stripping_bearing"] - (PUB_BEARING + 80.0)) < 1e-3
        # And at the tip the anchor has no pullout capacity left at all.
        m = stype.capacity_modes(5.0, 5.0, bond)
        assert m["pullout_bearing"] == 0.0
        assert m["pullout_shallow"] == 0.0
        assert m["pullout_cylindrical"] == 0.0

    def test_shallow_failure_is_continuous_across_a_plate(self):
        """The counting convention cannot be seen in this branch, which is
        why the bearing branches are the ones that pin it."""
        stype = _anchor()
        bond = _uniform_bond()
        for d in (3.0, 4.0):
            before = stype.capacity_modes(d - 1e-7, 5.0, bond)
            after = stype.capacity_modes(d + 1e-7, 5.0, bond)
            here = stype.capacity_modes(d, 5.0, bond)
            for key in ("pullout_shallow", "stripping_shallow"):
                assert abs(before[key] - here[key]) < 1e-3, (d, key)
                assert abs(after[key] - here[key]) < 1e-3, (d, key)

    def test_individual_bearing_steps_there(self):
        """And the step is a whole plate, which is what the reference's
        force diagram draws as a riser."""
        stype = _anchor()
        bond = _uniform_bond()
        before = stype.capacity_modes(3.0 - 1e-7, 5.0, bond)
        after = stype.capacity_modes(3.0 + 1e-7, 5.0, bond)
        jump = before["pullout_bearing"] - after["pullout_bearing"]
        assert abs(jump - PUB_BEARING) < 1e-3, jump


# ======================================================================
class TestAnalyticalIdentities:
    """True whatever the numbers are, so no snapshot can hide in them."""

    def test_one_helix_makes_the_two_deep_modes_equal(self):
        """No soil is mobilised between plates when there is one plate, so
        cylindrical shear IS individual bearing. Exact, and the reference
        states it in words for any anchor."""
        stype = _anchor(number_of_helices=1)
        bond = _uniform_bond(plates=(5.0,))
        for d in (0.0, 1.0, 2.5, 4.9):
            m = stype.capacity_modes(d, 5.0, bond)
            assert m["pullout_cylindrical"] == m["pullout_bearing"], d
        # and on the stripping side, once the plate is behind the cut
        stype2 = _anchor(number_of_helices=1)
        bond2 = _uniform_bond(plates=(2.0,))
        m = stype2.capacity_modes(3.0, 5.0, bond2)
        assert m["stripping_cylindrical"] == m["stripping_bearing"]

    def test_the_cylinder_reaches_the_farthest_plate(self):
        """``h + (n-1)s`` is the distance from the cut to the last plate,
        so the shallow branch is the shaft shear over exactly that."""
        stype = _anchor()
        bond = _uniform_bond()
        for d in (0.0, 1.7, 3.5, 4.2):
            m = stype.capacity_modes(d, 5.0, bond)
            expected = math.pi * 0.2 * PUB_TAU * (5.0 - d)
            assert abs(m["pullout_shallow"] - expected) < 1e-9, d

    def test_no_plate_beyond_the_cut_means_no_force_at_all(self):
        stype = _anchor()
        bond = _uniform_bond()
        assert stype.force_at(5.0, 5.0, bond) == 0.0
        # even with a tendon that could carry a hundred times more
        rich = _anchor(tensile_capacity=8500.0,
                       head_assembly_capacity=8000.0)
        assert rich.force_at(5.0, 5.0, bond) == 0.0

    def test_the_head_assembly_alone_holds_the_stripping_side(self):
        """With no plate in the moving mass the three stripping capacities
        are the head capacity. The reference's prose says otherwise and
        its own table, equations and figure all say this."""
        stype = _anchor()
        m = stype.capacity_modes(1.0, 5.0, _uniform_bond())
        assert m["stripping_shallow"] == 80.0
        assert m["stripping_cylindrical"] == 80.0
        assert m["stripping_bearing"] == 80.0

    def test_force_at_is_the_minimum_of_the_modes_for_every_type(self):
        """The identity that keeps one formula from being written twice."""
        from ogr_core.support import support_registry
        for type_id, cls in sorted(support_registry().items()):
            stype = cls()
            for d in (0.0, 1.0, 2.5, 4.0, 5.0):
                modes = stype.capacity_modes(d, 5.0, None)
                if not modes:
                    continue
                expected = max(0.0, min(modes.values()))
                got = stype.force_at(d, 5.0, None)
                assert abs(got - expected) < 1e-12, (type_id, d, got,
                                                     expected)


# ======================================================================
class TestTheEquivalentEnvelopeIsATangent:
    """Why the choice of where tau comes from turned out not to be one.

    The formulation needs ``c`` and ``phi`` separately, for N_c and N_q,
    and it needs ``tau`` on the cylinder. Those could have been two
    different opinions about the same soil at the same point. They are
    not: ``_local_c_phi`` builds a TANGENT, so ``c + sigma tan phi`` IS
    ``tau(sigma)`` by construction, for every constitutive model. This
    test is what says so, and what would notice if the linearisation ever
    stopped being a tangent.
    """

    def _pair(self, strength, sigma=90.0):
        from ogr_core.materials.strength_model import SliceContext
        from ogr_core.support.bond import _PointAsSlice
        from ogr_slip2d.methods.bishop import BishopSimplified

        class _Mat:
            def __init__(self, st):
                self.strength = st

        sl = _PointAsSlice(7.5, sigma, 0.0, 4.5, 0.0, None, None)
        c, tan_phi = BishopSimplified._local_c_phi(sl, _Mat(strength), sigma)
        if getattr(strength, "needs_context", False):
            ctx = SliceContext(base_angle_rad=0.0, sigma_v_eff=sigma,
                               depth=4.5, pore_pressure=0.0, y_base=7.5,
                               layer_top_y=None, slope_distance=None)
            tau = strength.shear_strength_ctx(sigma, ctx)
        else:
            tau = strength.shear_strength(sigma)
        return c + sigma * tan_phi, tau

    def test_the_two_agree_for_every_model_this_can_reach(self):
        from ogr_core.materials import builtin_models as B
        models = [
            ("MohrCoulomb", B.MohrCoulomb(cohesion=15.0,
                                          friction_angle=35.0)),
            ("Undrained", B.Undrained(cohesion=60.0)),
            ("PowerCurve", B.PowerCurve()),
            ("Hyperbolic", B.Hyperbolic()),
            ("VerticalStressRatio", B.VerticalStressRatio()),
            ("GeneralizedHoekBrown", B.GeneralizedHoekBrown()),
            ("HoekBrown", B.HoekBrown()),
            ("BartonBandis", B.BartonBandis()),
            ("DrainedUndrained", B.DrainedUndrained()),
            ("AnisotropicLinear", B.AnisotropicLinear()),
            ("SHANSEP", B.SHANSEP()),
            ("ShearNormalFunction", B.ShearNormalFunction()),
            ("DiscreteFunction", B.DiscreteFunction()),
        ]
        for name, strength in models:
            linear, tau = self._pair(strength)
            assert abs(linear - tau) <= 1e-9 * max(1.0, abs(tau)), (
                name, linear, tau)


# ======================================================================
class TestThroughTheEngine:
    """Not the formula: the model, the profile and the intersection."""

    def test_the_profile_measures_the_published_soil(self):
        p = _project()
        bond = _bond(p)
        assert abs(bond.mean_tau() - PUB_TAU) < 5e-5, bond.mean_tau()
        assert len(bond.stations) == 3
        for d, q in bond.stations:
            assert abs(q - PUB_BEARING) < 2e-3, (d, q)
        assert [round(d, 6) for d, _ in bond.stations] == [3.0, 4.0, 5.0]

    def test_the_applied_force_at_the_published_point(self):
        """73.5309 kN/m at (11, 7.5), through the whole chain."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import compute_support_effects
        p = _project()
        surface = _surface()
        sl = slice_surface(p, surface, num_slices=50)
        effects = compute_support_effects(p, surface, sl)
        assert len(effects) == 1
        e = effects[0]
        assert abs(e.intersection_x - 11.0) < 1e-9
        assert abs(e.intersection_y - 7.5) < 1e-9
        assert abs(e.force_magnitude - PUB_APPLIED) < 1e-4 * PUB_APPLIED

    def test_the_anchor_raises_the_factor_of_safety(self):
        bare = _fos("bishop_simplified", _project(with_anchor=False))
        held = _fos("bishop_simplified", _project())
        assert held > bare + 0.3, (bare, held)

    def test_the_head_sits_on_a_vertical_face_and_the_stress_is_right(self):
        """The anchor head is ON the vertical cut, where the ground
        surface is discontinuous. Reading 90 kPa all along the shaft is
        what says the envelope takes the HIGH side there."""
        from ogr_core.support import sigma_v_effective_at
        p = _project()
        for x in (7.5, 8.0, 10.0, 12.5):
            sigma_v, u, depth = sigma_v_effective_at(p, x, 7.5)
            assert abs(sigma_v - 90.0) < 1e-6, (x, sigma_v)
            assert u == 0.0 and abs(depth - 4.5) < 1e-9


# ======================================================================
class TestRuleSeven:
    """Every setting moves the number, and the one that cannot says so."""

    def _applied(self, **kw):
        p = _project(**kw)
        return p.support_types[0].force_at(3.5, 5.0, _bond(p))

    def _envelope(self, **kw):
        """The whole diagram, not one point of it.

        The applied force is a MINIMUM, so a setting can be invisible at
        one position and decisive at another; measuring one point would be
        measuring the minimum rather than the setting.
        """
        p = _project(**kw)
        bond = _bond(p)
        stype = p.support_types[0]
        return [stype.force_at(0.1 * i, 5.0, bond) for i in range(51)]

    def test_every_parameter_moves_the_published_diagram(self):
        """Six of the eight, on the model exactly as published."""
        base = self._envelope()
        assert abs(base[35] - PUB_APPLIED) < 1e-3
        for name, value in (("tensile_capacity", 40.0),
                            ("head_assembly_capacity", 10.0),
                            ("out_of_plane_spacing", 2.0),
                            ("average_helix_diameter", 0.4),
                            ("helix_spacing", 0.5),
                            ("number_of_helices", 2)):
            got = self._envelope(**{name: value})
            gap = max(abs(a - b) for a, b in zip(base, got))
            assert gap > 1e-6, (name, gap)

    def test_the_shaft_moves_it_wherever_a_deep_mode_can_win(self):
        """The other two, and why they need a different model to be seen.

        The shaft enters ONLY through the area it takes from the plate, so
        it can only move a bearing term — and on the published model no
        bearing term ever wins: the shallow branch is smaller everywhere
        and the head assembly caps what is left. Raise the head and the
        tendon so a deep mode can govern and both move the diagram at
        once. That is rule 7 satisfied and located, which is worth more
        than rule 7 asserted at whichever point happened to work.
        """
        caps = dict(tensile_capacity=500.0, head_assembly_capacity=500.0)
        base = self._envelope(**caps)
        for name, value in (("shaft_type", "square"),
                            ("shaft_width", 0.18)):
            got = self._envelope(**dict(caps, **{name: value}))
            gap = max(abs(a - b) for a, b in zip(base, got))
            assert gap > 1e-6, (name, gap)
        # and on the published model they are invisible, which is a fact
        # about that model: its deep modes never win.
        assert self._envelope() == self._envelope(shaft_type="square")

    def test_where_the_number_of_helices_can_be_seen_and_where_it_cannot(self):
        """It moves the diagram, and it is worth knowing where it does not.

        On the published model the count changes the answer at three
        of fifty-one sampled positions — between the first plate and the
        point where pullout drops back under the head capacity — and
        NOWHERE else. Two things hide it: the shallow branch, which
        governs pullout here and depends only on the distance to the
        FARTHEST plate (the tip, whatever the count), and the head
        assembly, which caps everything to its left. Raise the head and
        the tendon so a deep mode can win, and the count separates the
        three diagrams over their whole length.

        Written down because the obvious rule-7 check — one point, one
        parameter — would have called this setting inert at 34 of the 51
        positions and decisive at one.
        """
        published = [self._envelope(number_of_helices=n) for n in (1, 2, 3)]
        differing = [i for i in range(51)
                     if published[0][i] != published[2][i]]
        assert differing, "the count changed nothing anywhere"
        assert [round(0.1 * i, 1) for i in differing] == [3.1, 3.2, 3.3]
        assert published[0] == published[1]

        rich = [self._envelope(number_of_helices=n, tensile_capacity=500.0,
                               head_assembly_capacity=500.0)
                for n in (1, 2, 3)]
        assert rich[0][0] < rich[1][0] < rich[2][0]
        assert abs(rich[2][0] - 189.8399) < 1e-3, rich[2][0]

    def test_the_helix_spacing_cannot_move_a_single_helix(self):
        """The half that is easy not to state. With one plate there is
        nothing to space, which is why the dialog greys the field."""
        one = dict(number_of_helices=1)
        a = self._applied(helix_spacing=1.0, **one)
        b = self._applied(helix_spacing=4.0, **one)
        assert a == b
        assert a > 0.0

    def test_the_spacing_divides_the_force_exactly(self):
        base = self._applied()
        assert abs(self._applied(out_of_plane_spacing=2.0) - base / 2.0) \
            < 1e-9


# ======================================================================
class TestTheShearCapacityReachesTheEngine:
    """The defect this version closes: declared, editable, serialised and
    read by nobody in three types since v0.1.14."""

    def test_zero_shear_changes_nothing_at_all(self):
        """Bit for bit. This is what protects every model validated
        before this version, because all of them leave it at zero."""
        for method_id in _method_ids():
            a = _fos(method_id, _project(shear_capacity=0.0))
            b = _fos(method_id, _project())
            assert a == b, method_id

    def test_shear_moves_the_number_in_every_method(self):
        for method_id in _method_ids():
            without = _fos(method_id, _project(shear_capacity=0.0))
            with_ = _fos(method_id, _project(shear_capacity=60.0))
            assert with_ > without, (method_id, without, with_)

    def test_it_also_reaches_the_three_older_types(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import (GroutedTieback, SoilNail,
                                      SupportInstance)
        for cls in (GroutedTieback, SoilNail):
            base = _project(with_anchor=False)
            plain = cls(out_of_plane_spacing=1.0, shear_capacity=0.0)
            base.support_types = [plain]
            base.supports.append(SupportInstance(
                type_id=plain.TYPE_ID,
                head=Vertex(*HEAD), tail=Vertex(*TAIL)))
            f0 = _fos("bishop_simplified", base)
            base.support_types[0].shear_capacity = 90.0
            f1 = _fos("bishop_simplified", base)
            assert f1 > f0, (cls.__name__, f0, f1)

    def test_the_resultant_is_the_hypotenuse(self):
        """The shear is PERPENDICULAR to the anchor and the axial force is
        along it when the orientation is parallel, so the two compose
        exactly. An identity, not a tolerance."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import compute_support_effects
        surface = _surface()
        p = _project(orientation="parallel_to_support", shear_capacity=60.0)
        sl = slice_surface(p, surface, num_slices=50)
        e = compute_support_effects(p, surface, sl)[0]
        axial = p.support_types[0].force_at(3.5, 5.0, _bond(p))
        shear = 60.0 / 1.0
        assert abs(axial - PUB_APPLIED) < 1e-3
        assert abs(e.force_magnitude - math.hypot(axial, shear)) < 1e-9

    def test_a_type_that_does_not_declare_shear_gets_none(self):
        """``SUPPORTS_SHEAR`` is the gate, and now it has a reader."""
        from ogr_core.support import EndAnchored, support_registry
        assert not EndAnchored.SUPPORTS_SHEAR
        declared = {t for t, c in support_registry().items()
                    if c.SUPPORTS_SHEAR}
        assert declared == {"grouted_tieback", "grouted_tieback_friction",
                            "soil_nail", "helical_anchor"}


# ======================================================================
class TestSerialisation:
    def test_the_type_round_trips_through_a_project_file(self, tmp_path=None):
        import json
        import tempfile
        from pathlib import Path

        from ogr_core.project import Project
        p = _project(shear_capacity=12.0)
        d = Path(tempfile.mkdtemp())
        f = d / "helical.ogr"
        p.save(f)
        assert json.loads(f.read_text(encoding="utf-8"))
        back = Project.load(f)
        st = back.support_types[0]
        assert st.TYPE_ID == "helical_anchor"
        assert st.number_of_helices == 3
        assert isinstance(st.number_of_helices, int)
        assert st.shaft_type == "round"
        assert abs(st.shear_capacity - 12.0) < 1e-12
        assert abs(st.force_at(3.5, 5.0, _bond(back)) - PUB_APPLIED) < 1e-3

    def test_a_fractional_helix_count_is_refused_quietly(self):
        """JSON and spin boxes both hand back 3.0. Two and a half plates
        would move every plate without saying so."""
        from ogr_core.support import HelicalAnchor
        assert HelicalAnchor(number_of_helices=3.0).number_of_helices == 3
        assert HelicalAnchor(number_of_helices=2.4).number_of_helices == 2
        assert HelicalAnchor(number_of_helices=0).number_of_helices == 1


# ======================================================================
class TestTheModelNotes:
    def _notes(self, **kw):
        from ogr_slip2d.analysis_runner import settings_warnings
        return settings_warnings(_project(**kw), ["bishop_simplified"])

    def test_the_published_model_says_nothing(self):
        assert self._notes() == []

    def test_a_spacing_outside_the_recommended_band_is_reported(self):
        assert any("5 to 12" in n
                   for n in self._notes(helix_spacing=0.4))

    def test_a_shaft_as_wide_as_the_helix_is_reported(self):
        assert any("no bearing area" in n
                   for n in self._notes(shaft_width=0.25))

    def test_a_group_that_does_not_fit_says_what_it_used(self):
        notes = self._notes(number_of_helices=8, helix_spacing=1.0)
        assert any("do not fit" in n and "0.71" in n for n in notes)


# ======================================================================
class TestTheInterface:
    """Offscreen, but the real widgets and the real menu bar."""

    def _app(self):
        from PySide6.QtWidgets import QApplication
        # A QWidget built with no QApplication takes the whole process
        # down with no traceback, which is how this file first exited 127.
        return QApplication.instance() or QApplication([])

    def test_a_count_gets_an_integer_editor_and_a_gate(self):
        from PySide6.QtWidgets import QSpinBox
        self._app()
        from ogr_gui.dialogs.define_support_dialog import _SupportParamPanel
        from ogr_core.support import HelicalAnchor
        panel = _SupportParamPanel()
        panel.set_type(HelicalAnchor)
        counter = panel._editors["number_of_helices"]
        assert isinstance(counter, QSpinBox)
        spacing = panel._editors["helix_spacing"]
        counter.setValue(1)
        assert not spacing.isEnabled()
        counter.setValue(3)
        assert spacing.isEnabled()
        assert panel.get_values()["number_of_helices"] == 3

    def test_the_other_types_keep_their_editors(self):
        from PySide6.QtWidgets import QDoubleSpinBox
        self._app()
        from ogr_gui.dialogs.define_support_dialog import _SupportParamPanel
        from ogr_core.support import support_registry
        for type_id, cls in sorted(support_registry().items()):
            if type_id == "helical_anchor":
                continue
            panel = _SupportParamPanel()
            panel.set_type(cls)
            for name, editor in panel._editors.items():
                default = cls.PARAMETERS.get(name, (0.0,))[0]
                if isinstance(default, (int, float)) and \
                        not isinstance(default, bool):
                    assert isinstance(editor, QDoubleSpinBox), (type_id,
                                                                name)

    def test_the_diagram_publishes_the_seven_modes_and_the_cut(self):
        self._app()
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow,
        )
        from ogr_slip2d.slicer import slice_surface

        class _Crit:
            pass
        p = _project()
        surface = _surface()
        crit = _Crit()
        crit.surface = surface
        crit.slices = slice_surface(p, surface, num_slices=50)
        win = SupportForceDiagramWindow(p, crit)
        series, applied, cut = win.series()
        assert len(series) == 8, [s[0] for s in series]
        assert abs(cut - 3.5) < 1e-6, cut
        assert abs(applied - PUB_APPLIED) < 1e-3, applied
        # the envelope is the last series and never exceeds any mode
        _label, xs, envelope = series[-1]
        for _lab, _xs, ys in series[:-1]:
            for a, b in zip(envelope, ys):
                assert a <= b + 1e-9
        win.deleteLater()

    def test_the_diagram_action_is_reachable_from_the_menu_bar(self):
        self._app()
        from ogr_gui.i18n import current_language, set_language
        previous = current_language()
        set_language("en")
        try:
            from ogr_gui.interpret_window import InterpretWindow
            win = InterpretWindow(_project(), None)
            found = set()

            def walk(menu):
                for act in menu.actions():
                    sub = act.menu()
                    if sub is not None:
                        walk(sub)
                    elif act.text():
                        found.add(act.text())
            for act in win.menuBar().actions():
                sub = act.menu()
                if sub is not None:
                    walk(sub)
            assert "Support Force Diagram..." in found, sorted(found)
            win.deleteLater()
        finally:
            # Rule 5: a test that leaves the language set breaks menu
            # tests it never heard of, and only in the full suite.
            set_language(previous)
