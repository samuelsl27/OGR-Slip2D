# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.120 — undrained shear strength that VARIES LINEARLY WITH DEPTH.

Until this version the registry had eighteen strength models and not one
of them could express ``cu = cu_top + Δc·z``: ``Undrained`` is a constant,
and ``VerticalStressRatio`` and ``SHANSEP`` vary with σ'v, which is not the
same thing as depth inside a layer. That gap kept six problems of the
verification manual out of the comparison, and made the one that did get
published (Low 1989) an approximation by four horizontal bands.

Three models close it, differing ONLY in where the depth is measured from:

    undrained_depth_layer      from the top of the layer local to the slice
    undrained_depth_datum      from a horizontal datum the user fixes
    undrained_slope_distance   the true distance to the nearest point of
                               the slope

WHAT EACH GROUP OF TESTS PROTECTS

* ``TestIdentityWithConstantUndrained`` — with Δc = 0 the three must give
  EXACTLY what ``Undrained`` gives, at the model level and through a whole
  factor of safety. It is the cheapest check there is, and it is the one
  that would catch a sign error in the depth or a reference elevation read
  off the wrong field.

* ``TestIdentityBetweenSubtypes`` — the layer-top and distance-to-slope
  models have no published case in the manual to be validated against, so
  they are pinned by analytic identities instead: over a horizontal layer
  top the layer form must equal the datum form digit for digit, and under
  level ground the distance form must equal the layer form. Both would
  break the instant the slicer measured the wrong thing.

* ``TestEverySettingMovesTheNumber`` — rule 7 of the project. The rate,
  the datum and the cutoff each have to change a factor of safety; a
  configurable control that does not reach the analysis is worse than no
  control, because the user believes it was respected.

* ``TestCutoffIsAsymmetric`` — the cutoff is a MAXIMUM, except that with a
  negative rate the same value is a MINIMUM. That asymmetry is the stated
  rule, not an interpretation, and it is the part most likely to be
  "tidied up" by someone who has not read it.

* ``TestSerialisation`` — ``cutoff_enabled`` is a boolean and PARAMETERS
  only holds floats, so it travels beside them. v0.1.60 records what
  happens when such state is dropped on reload: the user's data silently
  becomes the built-in default.

* ``TestRapidDrawdownIsRefused`` — a material whose strength is undrained
  by construction has no drained envelope for the drawdown procedure to
  rewrite. The refusal must be explicit, not a number.

* ``TestDuncanWright1984`` — the external validation (rule 1): the four
  undrained profiles of verification problem 84, Duncan and Wright (2005)
  figure 15.9, each on its own published circle. Profile I has cz = 0 and
  therefore does NOT exercise the new law: it is the control that says
  whether a discrepancy is the geometry or the strength.
"""
from __future__ import annotations

import math

import pytest


# ======================================================================
# Shared fixtures: an embankment on a two-layer foundation, in the
# geometry of verification problem 84 (Duncan and Wright 2005, fig 15.9).
# ======================================================================
_EXTERNAL = [(0, 0), (140, 0), (140, 40), (90, 40), (40, 20), (0, 20)]
_CONTACT = [(0, 20), (140, 20)]
_Y_CONTACT = 20.0          # top of the foundation, and its datum
_CU0 = 300.0               # psf at the top of the foundation
_GAMMA_EMB, _GAMMA_FOUND = 125.0, 100.0     # pcf
_PHI_EMB = 35.0

# Published circles, read off the panels of figures 84.2 to 84.5.
_CIRCLES = {
    "I":   (64.001, 54.710, 54.640),
    "II":  (64.473, 54.666, 54.499),
    "III": (64.904, 52.774, 48.488),
    "IV":  (64.721, 51.598, 44.774),
}
_CZ = {"I": 0.0, "II": 5.0, "III": 10.0, "IV": 15.0}

# Tables 84.3 to 84.6, the CIRCULAR column.
_PUBLISHED = {
    "I":   {"bishop_simplified": 0.761, "spencer": 0.756,
            "gle_morgenstern_price": 0.762},
    "II":  {"bishop_simplified": 0.909, "spencer": 0.898,
            "gle_morgenstern_price": 0.908},
    "III": {"bishop_simplified": 1.045, "spencer": 1.032,
            "gle_morgenstern_price": 1.034},
    "IV":  {"bishop_simplified": 1.154, "spencer": 1.134,
            "gle_morgenstern_price": 1.138},
}


def _embankment(foundation_strength, external=None, contact=None):
    """Embankment over a foundation with the given strength model."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("undrained depth profile")
    ext = Polyline(vertices=[Vertex(x, y)
                             for x, y in (external or _EXTERNAL)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in (contact or _CONTACT)],
        closed=False), btype=BoundaryType.MATERIAL))

    top = Material(name="Embankment", unit_weight=_GAMMA_EMB,
                   sat_unit_weight=_GAMMA_EMB,
                   strength=MohrCoulomb(cohesion=0.0,
                                        friction_angle=_PHI_EMB))
    bottom = Material(name="Foundation", unit_weight=_GAMMA_FOUND,
                      sat_unit_weight=_GAMMA_FOUND,
                      strength=foundation_strength)
    p.materials = [top, bottom]
    p.resolve_regions()
    p.assign_material_at(100.0, 30.0, top.id)
    p.assign_material_at(70.0, 10.0, bottom.id)
    return p


def _fos(project, circle, method_id="bishop_simplified", n=50):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle

    cx, cy, r = circle
    surface = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
    slices = slice_surface(project, surface, num_slices=n)
    assert slices is not None, "the slicer refused the reference circle"
    return method_registry()[method_id]().compute_fos(
        project, surface, slices).fos


def _datum(cz, c0=_CU0, **kw):
    from ogr_core.materials.builtin_models import UndrainedDepthFromDatum
    return UndrainedDepthFromDatum(cohesion_datum=c0, cohesion_change=cz,
                                   datum=_Y_CONTACT, **kw)


def _layer(cz, c0=_CU0, **kw):
    from ogr_core.materials.builtin_models import UndrainedDepthFromLayerTop
    return UndrainedDepthFromLayerTop(cohesion_top=c0, cohesion_change=cz,
                                      **kw)


def _slope(cz, c0=_CU0, **kw):
    from ogr_core.materials.builtin_models import UndrainedDistanceToSlope
    return UndrainedDistanceToSlope(cohesion_top=c0, cohesion_change=cz, **kw)


# ======================================================================
class TestRegistry:
    def test_the_three_models_are_registered(self):
        from ogr_core.materials.registry import REGISTRY
        models = REGISTRY.all()
        for mid in ("undrained_depth_layer", "undrained_depth_datum",
                    "undrained_slope_distance"):
            assert mid in models, f"Missing model: {mid}"

    def test_constant_undrained_is_untouched(self):
        """The model every existing project uses keeps its one parameter."""
        from ogr_core.materials.builtin_models import Undrained
        assert list(Undrained.PARAMETERS) == ["cohesion"]
        assert Undrained().needs_context is False

    def test_only_the_slope_model_asks_for_the_expensive_field(self):
        """The distance to the slope costs a pass over the whole ground
        profile per slice. Nothing else may switch it on."""
        from ogr_core.materials.registry import REGISTRY
        asking = [mid for mid, cls in REGISTRY.all().items()
                  if getattr(cls, "NEEDS_SLOPE_DISTANCE", False)]
        assert asking == ["undrained_slope_distance"]


# ======================================================================
class TestIdentityWithConstantUndrained:
    """Δc = 0 must reproduce ``Undrained`` exactly — not approximately."""

    def test_model_level(self):
        from ogr_core.materials.builtin_models import Undrained
        from ogr_core.materials.strength_model import SliceContext
        flat = Undrained(cohesion=137.0)
        for model in (_datum(0.0, 137.0), _layer(0.0, 137.0),
                      _slope(0.0, 137.0)):
            for y in (-50.0, 0.0, 20.0, 137.0):
                ctx = SliceContext(y_base=y, layer_top_y=20.0,
                                   slope_distance=abs(20.0 - y))
                for sigma in (0.0, 10.0, 5000.0):
                    assert (model.shear_strength_ctx(sigma, ctx)
                            == flat.shear_strength(sigma))

    def test_through_a_whole_factor_of_safety(self):
        from ogr_core.materials.builtin_models import Undrained
        circle = _CIRCLES["I"]
        reference = _fos(_embankment(Undrained(cohesion=_CU0)), circle)
        for model in (_datum(0.0), _layer(0.0), _slope(0.0)):
            assert _fos(_embankment(model), circle) == reference

    def test_and_the_reference_value_is_not_accidentally_zero(self):
        """Guards the identity above: it would also pass if every model
        returned zero strength."""
        from ogr_core.materials.builtin_models import Undrained
        assert 0.5 < _fos(_embankment(Undrained(cohesion=_CU0)),
                          _CIRCLES["I"]) < 1.0


# ======================================================================
class TestIdentityBetweenSubtypes:
    """The two subtypes with no published case are pinned by identities."""

    def test_layer_top_equals_datum_over_a_horizontal_contact(self):
        """The foundation top is flat at y = 20, so "below the layer top"
        and "below the datum at 20" are the same distance. Digit for
        digit: anything else means the slicer measured a different top."""
        for cz in (5.0, 15.0, -4.0):
            for method in ("bishop_simplified", "spencer"):
                a = _fos(_embankment(_datum(cz)), _CIRCLES["II"], method)
                b = _fos(_embankment(_layer(cz)), _CIRCLES["II"], method)
                assert a == b, f"cz={cz} {method}: {a!r} != {b!r}"

    def test_distance_to_slope_equals_layer_top_under_level_ground(self):
        """On a flat-topped block the nearest point of the profile is the
        one straight above, so the true distance is the vertical drop."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        block = [(0, 0), (100, 0), (100, 30), (0, 30)]
        contact = [(0, 20), (100, 20)]
        circle = (50.0, 40.0, 24.0)
        for cz in (6.0, -3.0):
            a = _fos(_embankment(_layer(cz), block, contact), circle)
            b = _fos(_embankment(_slope(cz), block, contact), circle)
            assert a == b, f"cz={cz}: {a!r} != {b!r}"
        assert MohrCoulomb  # keeps the import honest about what is built

    def test_and_under_a_slope_face_the_two_differ(self):
        """The identity above must not hold by accident: on the sloping
        geometry the perpendicular distance is shorter than the drop, so
        the distance model must give a DIFFERENT number."""
        a = _fos(_embankment(_layer(15.0)), _CIRCLES["IV"])
        b = _fos(_embankment(_slope(15.0)), _CIRCLES["IV"])
        assert abs(a - b) > 1e-4, (
            f"the two ways of measuring depth agree ({a!r}), so one of "
            f"them is not being measured at all")


# ======================================================================
class TestEverySettingMovesTheNumber:
    """Rule 7: a control that does not reach the analysis is worse than
    no control, because the user believes the analysis respected it."""

    def test_the_rate_of_change_moves_it(self):
        base = _fos(_embankment(_datum(0.0)), _CIRCLES["IV"])
        more = _fos(_embankment(_datum(15.0)), _CIRCLES["IV"])
        assert more > base + 0.05, (base, more)

    def test_the_datum_moves_it(self):
        from ogr_core.materials.builtin_models import UndrainedDepthFromDatum
        low = UndrainedDepthFromDatum(cohesion_datum=_CU0,
                                      cohesion_change=15.0, datum=20.0)
        high = UndrainedDepthFromDatum(cohesion_datum=_CU0,
                                       cohesion_change=15.0, datum=40.0)
        a = _fos(_embankment(low), _CIRCLES["IV"])
        b = _fos(_embankment(high), _CIRCLES["IV"])
        assert b > a + 0.05, (a, b)

    def test_the_cutoff_moves_it(self):
        loose = _fos(_embankment(_datum(15.0)), _CIRCLES["IV"])
        capped = _fos(_embankment(_datum(15.0, cutoff=400.0,
                                         cutoff_enabled=True)),
                      _CIRCLES["IV"])
        assert capped < loose - 0.02, (loose, capped)

    def test_the_cutoff_checkbox_itself_moves_it(self):
        """The value and the switch are two settings, and both have to
        do something: the same cutoff left disabled must change nothing."""
        off = _fos(_embankment(_datum(15.0, cutoff=400.0)), _CIRCLES["IV"])
        none = _fos(_embankment(_datum(15.0)), _CIRCLES["IV"])
        on = _fos(_embankment(_datum(15.0, cutoff=400.0,
                                     cutoff_enabled=True)), _CIRCLES["IV"])
        assert off == none
        assert on < off - 0.02

    def test_the_slope_model_reads_a_distance_and_not_a_placeholder(self):
        base = _fos(_embankment(_slope(0.0)), _CIRCLES["IV"])
        steep = _fos(_embankment(_slope(15.0)), _CIRCLES["IV"])
        assert steep > base + 0.05, (base, steep)


# ======================================================================
class TestCutoffIsAsymmetric:
    """Enabled, the value is a maximum — unless the rate is negative, in
    which case the SAME value is a minimum."""

    def test_positive_rate_the_cutoff_is_a_cap(self):
        m = _datum(10.0, 100.0, cutoff=150.0, cutoff_enabled=True)
        assert m.cohesion_at(0.0) == 100.0
        assert m.cohesion_at(4.0) == 140.0
        assert m.cohesion_at(10.0) == 150.0          # capped, not 200
        assert m.cohesion_at(1000.0) == 150.0

    def test_negative_rate_the_cutoff_is_a_floor(self):
        m = _datum(-10.0, 100.0, cutoff=50.0, cutoff_enabled=True)
        assert m.cohesion_at(0.0) == 100.0
        assert m.cohesion_at(4.0) == 60.0
        assert m.cohesion_at(10.0) == 50.0           # floored, not 0
        assert m.cohesion_at(1000.0) == 50.0

    def test_disabled_the_line_is_unbounded_in_both_directions(self):
        m = _datum(10.0, 100.0, cutoff=150.0)
        assert m.cohesion_at(1000.0) == 100.0 + 10.0 * 1000.0
        # And ABOVE the datum it keeps falling, sign included. Nothing in
        # the documented law stops it, so nothing here does either.
        assert m.cohesion_at(-100.0) == 100.0 - 10.0 * 100.0


# ======================================================================
class TestDepthIsMeasuredFromTheRightPlace:
    def test_the_slicer_fills_the_layer_top_with_the_contact(self):
        """Not the ground surface: the slice base sits in the foundation,
        whose top is the contact at y = 20 even where 20 ft of embankment
        stands above it."""
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        p = _embankment(_layer(5.0))
        cx, cy, r = _CIRCLES["II"]
        slices = slice_surface(p, SlipCircle(centre_x=cx, centre_y=cy,
                                             radius=r), num_slices=50)
        under_crest = [s for s in slices if 60.0 < s.x_centre < 85.0]
        assert under_crest
        for s in under_crest:
            assert s.layer_top_y == 20.0, (s.x_centre, s.layer_top_y)
            assert s.top_y_mean > 25.0     # there really is fill above

    def test_the_slope_distance_is_only_measured_when_asked_for(self):
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        cx, cy, r = _CIRCLES["II"]
        surface = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        quiet = slice_surface(_embankment(_datum(5.0)), surface, num_slices=20)
        assert all(s.slope_distance is None for s in quiet)
        asked = slice_surface(_embankment(_slope(5.0)), surface,
                              num_slices=20)
        assert all(s.slope_distance is not None for s in asked)

    def test_a_model_handed_no_layer_top_falls_back_instead_of_inventing(self):
        from ogr_core.materials.strength_model import SliceContext
        m = _layer(5.0, 100.0)
        empty = SliceContext(y_base=-30.0)      # nobody filled it in
        assert m.shear_strength_ctx(0.0, empty) == 100.0
        assert m.shear_strength_ctx(0.0, None) == 100.0


# ======================================================================
class TestSerialisation:
    def test_round_trip_keeps_the_cutoff_switch(self):
        from ogr_core.materials.strength_model import StrengthModel
        for model in (_datum(3.0, cutoff=7.0, cutoff_enabled=True),
                      _layer(-3.0, cutoff=7.0, cutoff_enabled=True),
                      _slope(3.0, cutoff=7.0)):
            back = StrengthModel.from_dict(model.to_dict())
            assert type(back) is type(model)
            assert back.params == model.params
            assert back.cutoff_enabled == model.cutoff_enabled

    def test_round_trip_through_a_project_file(self, tmp_path):
        from ogr_core.project import Project
        p = _embankment(_datum(15.0, cutoff=520.0, cutoff_enabled=True))
        path = tmp_path / "depth.ogr"
        p.save(path)
        back = Project.load(path)
        strength = back.materials[1].strength
        assert strength.MODEL_ID == "undrained_depth_datum"
        assert strength.params["cohesion_change"] == 15.0
        assert strength.params["datum"] == _Y_CONTACT
        assert strength.cutoff_enabled is True

    def test_a_reloaded_project_gives_the_same_number(self, tmp_path):
        from ogr_core.project import Project
        p = _embankment(_datum(15.0))
        path = tmp_path / "same.ogr"
        p.save(path)
        assert (_fos(Project.load(path), _CIRCLES["IV"])
                == _fos(p, _CIRCLES["IV"]))


# ======================================================================
class TestRapidDrawdownIsRefused:
    """A material that is undrained by construction has no drained
    envelope for the drawdown procedure to rewrite slice by slice. The
    answer has to be an explicit refusal, not a factor of safety."""

    def test_refused_with_a_message_that_names_the_model(self):
        from ogr_core.materials import Material
        from ogr_slip2d.rapid_drawdown import (RapidDrawdownError,
                                               _effective_c_phi)
        mat = Material(name="Bay mud", unit_weight=17.0,
                       strength=_datum(9.8, 100.0))
        try:
            _effective_c_phi(mat)
        except RapidDrawdownError as exc:
            assert "undrained_depth_datum" in str(exc)
        else:
            raise AssertionError("rapid drawdown accepted a depth profile")


# ======================================================================
class TestDuncanWright1984:
    """External validation (rule 1) — verification problem 84.

    Duncan, J.M. and Wright, S.G. (2005), *Soil Strength and Slope
    Stability*, figure 15.9 p. 244: an embankment on a foundation whose
    undrained strength is cu = 300 + cz·z psf, for cz = 0, 5, 10 and 15
    psf/ft. Each profile is evaluated on the circle the manual publishes
    for it, so this measures the strength law and not a search.

    Profile I is cz = 0 — a constant undrained strength, which this
    version could already do. It is here as the CONTROL: if it fails, the
    geometry or the weights are wrong, and nothing can be concluded about
    the other three.
    """

    TOLERANCE = 0.02      # 2 %, the closure criterion for this gap

    def _check(self, profile):
        project = _embankment(_datum(_CZ[profile]))
        circle = _CIRCLES[profile]
        for method, published in _PUBLISHED[profile].items():
            got = _fos(project, circle, method)
            error = abs(got - published) / published
            assert error <= self.TOLERANCE, (
                f"profile {profile} {method}: {got:.4f} vs published "
                f"{published:.3f} ({100 * error:+.2f} %)")

    def test_profile_I_the_control_cz_zero(self):
        self._check("I")

    def test_profile_II_cz_5(self):
        self._check("II")

    def test_profile_III_cz_10(self):
        self._check("III")

    def test_profile_IV_cz_15(self):
        self._check("IV")

    def test_the_four_profiles_are_ordered_as_published(self):
        """cz only ever adds strength below the datum, so the factor has
        to rise with it. Catches a sign error that the per-profile
        tolerance alone could absorb."""
        values = [_fos(_embankment(_datum(_CZ[p])), _CIRCLES["I"])
                  for p in ("I", "II", "III", "IV")]
        assert values == sorted(values), values
        assert values[-1] > values[0] * 1.4, values

    def test_the_published_circles_are_not_interchangeable(self):
        """Guards the four cases above: they would all pass on a single
        circle if the profiles barely differed. Profile IV on its own
        circle must beat profile IV on profile I's."""
        own = _fos(_embankment(_datum(_CZ["IV"])), _CIRCLES["IV"])
        borrowed = _fos(_embankment(_datum(_CZ["IV"])), _CIRCLES["I"])
        assert own < borrowed, (own, borrowed)
        assert math.isfinite(own) and math.isfinite(borrowed)


# ======================================================================
class TestNegativeCohesionNeverResists:
    """A straight line crosses zero, and the datum form has nothing below
    it: with a RISING profile the Cutoff is a maximum, so it cannot bound
    that side. What was measured — on verification problem 29, the one
    published case whose material reaches well above its own datum — is
    that the negative branch never reaches the equilibrium: the solver
    floors the local cohesion at zero for EVERY model, in
    ``BishopSimplified._local_c_phi``, and has done so since long before
    this version.

    So no floor was added to the law. These tests pin the two halves of
    that: the law says what it says, and the solver never resists with a
    negative number.
    """

    def test_the_law_itself_is_literal(self):
        m = _datum(9.8, 100.0)
        m.params["datum"] = -20.0
        # 100 + 9.8·(−20 − y) = 0 at y = −9.7959…
        assert m.cohesion_at(-20.0 - (-9.795918367346939)) == pytest.approx(
            0.0, abs=1e-9)
        assert m.cohesion_at(-20.0 - 22.0) == pytest.approx(-311.6, abs=1e-9)

    def test_but_the_solver_floors_it_at_zero(self):
        from ogr_core.materials import Material
        from ogr_core.materials.strength_model import SliceContext
        from ogr_slip2d.methods.bishop import BishopSimplified

        class _Slice:                    # only what _local_c_phi reads
            width = 1.0
            weight = 2000.0
            pore_pressure = 0.0
            base_angle = 0.0
            top_y_left = top_y_right = 30.0
            base_y_left = base_y_right = 22.0
            layer_top_y = None
            slope_distance = None
            suction_cohesion = 0.0

        mat = Material(name="mud", unit_weight=100.0,
                       strength=_datum(9.8, 100.0))
        mat.strength.params["datum"] = -20.0
        assert mat.strength.shear_strength_ctx(
            0.0, SliceContext(y_base=22.0)) < -300.0
        c, tan_phi = BishopSimplified._local_c_phi(_Slice(), mat, 500.0)
        assert c == 0.0, c
        assert tan_phi == 0.0

    def test_a_surface_in_the_dead_zone_gives_zero_not_a_negative_factor(self):
        """Zero strength is an honest zero. A NEGATIVE factor of safety
        would be a resisting force that pushes, and a search would rank it
        below everything real."""
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material
        from ogr_core.project import Project
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle

        p = Project("dead zone")
        ext = Polyline(vertices=[Vertex(*v) for v in
                                 ((0, 0), (100, 0), (100, 40), (60, 40),
                                  (30, 10), (0, 10))], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        st = _datum(10.0, 100.0)
        st.params["datum"] = 0.0        # c = 0 at y = 10, negative above
        p.materials = [Material(name="mud", unit_weight=100.0, strength=st)]
        r = GridSearch(method=get_method("bishop_simplified")(),
                       num_slices=30, min_area=0.0).evaluate_circle(
            p, SlipCircle(centre_x=50.0, centre_y=45.0, radius=22.0))
        assert r is not None
        assert r.fos == 0.0, r.fos


# ======================================================================
class TestTheProfileWarnsWhenItReachesZero:
    """Where the line crosses zero the soil has NO strength, and a search
    that looks there reports a factor of zero as its minimum. That is what
    the law says rather than a defect — but the elevation it happens at is
    not visible in the three numbers the dialog shows, so the run says so.
    Measured on verification problem 29.
    """

    @staticmethod
    def _project(datum, rate, c0, external, contact=None, second=None):
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project

        p = Project("profile note")
        ext = Polyline(vertices=[Vertex(*v) for v in external], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        st = _datum(rate, c0)
        st.params["datum"] = datum
        mats = [Material(name="mud", unit_weight=100.0, strength=st)]
        if contact is not None:
            p.add_boundary(Boundary(polyline=Polyline(
                vertices=[Vertex(*v) for v in contact], closed=False),
                btype=BoundaryType.MATERIAL))
            mats.insert(0, Material(
                name="fill", unit_weight=125.0,
                strength=MohrCoulomb(cohesion=0.0, friction_angle=35.0)))
        p.materials = mats
        if contact is not None:
            p.resolve_regions()
            p.assign_material_at(second[0], second[1], mats[1].id)
        return p

    def _notes(self, project):
        from ogr_slip2d.analysis_runner import settings_warnings
        return [n for n in settings_warnings(project)
                if "undrained profile" in n]

    def test_it_warns_when_the_material_reaches_above_the_zero_crossing(self):
        p = self._project(datum=-20.0, rate=9.8, c0=100.0,
                          external=((0, -40), (100, -40), (100, 22),
                                    (60, 22), (30, -10), (0, -10)))
        notes = self._notes(p)
        assert len(notes) == 1, notes
        assert "-9.796" in notes[0], notes[0]

    def test_it_stays_quiet_when_the_material_stops_below_it(self):
        """Verification problem 84 in miniature: the profile's zero
        crossing is up at the crest of the EMBANKMENT, and the foundation
        that carries the profile ends twenty feet lower. Measuring against
        the model's own range instead of the material's would have made
        this warn about soil that is not there."""
        p = self._project(datum=20.0, rate=15.0, c0=300.0,
                          external=((0, 0), (140, 0), (140, 40), (90, 40),
                                    (40, 20), (0, 20)),
                          contact=((0, 20), (140, 20)),
                          second=(70.0, 10.0))
        assert self._notes(p) == []

    def test_a_falling_profile_warns_downwards(self):
        p = self._project(datum=0.0, rate=-2.0, c0=20.0,
                          external=((0, -40), (100, -40), (100, 10),
                                    (60, 10), (30, 0), (0, 0)))
        notes = self._notes(p)
        assert len(notes) == 1, notes
        assert "10" in notes[0], notes[0]

    def test_an_enabled_cutoff_on_the_falling_side_silences_it(self):
        """Rule 7 from the other end: the Cutoff DOES bound the side the
        line falls towards, and when it does there is nothing to warn
        about."""
        p = self._project(datum=0.0, rate=-2.0, c0=20.0,
                          external=((0, -40), (100, -40), (100, 10),
                                    (60, 10), (30, 0), (0, 0)))
        st = p.materials[0].strength
        st.params["cutoff"] = 5.0
        st.cutoff_enabled = True
        assert self._notes(p) == []

    def test_a_constant_profile_never_warns(self):
        p = self._project(datum=-20.0, rate=0.0, c0=100.0,
                          external=((0, -40), (100, -40), (100, 22),
                                    (60, 22), (30, -10), (0, -10)))
        assert self._notes(p) == []


def _perfil():
    """cu = 20 + 3*(30 - y): un perfil que crece 3 kPa por metro bajo la
    cota 30, elegido para que la superficie de ensayo lo recorra entero."""
    from ogr_core.materials.builtin_models import UndrainedDepthFromDatum
    return UndrainedDepthFromDatum(cohesion_datum=20.0, cohesion_change=3.0,
                                   datum=30.0)


# ======================================================================
class TestOrdinaryReadsTheEnvelopeLikeEveryoneElse:
    """Ordinary/Fellenius was the only method that asked the strength
    model for τ WITHOUT a SliceContext (``LEMMethod._shear_strength``,
    removed in v0.1.120). Through that one line it ignored the eight
    models whose strength depends on more than σ'ₙ — SHANSEP, the four
    anisotropic ones and the three depth profiles — and the matric-suction
    cohesion as well.

    It surfaced here: when verification problem 23 stopped approximating
    its depth profile with four constant bands, Fellenius fell from 1.3674
    to 1.1710 against a published 1.370 while Bishop moved 0.3 %. The
    bands were plain ``undrained`` and needed no context, so the defect had
    been invisible since v0.1.15.

    The invariant these tests pin is an IDENTITY, not a recorded number:
    for a φ = 0 material with no water and no support, Fellenius and
    Bishop are the same equation. Bishop's m_α collapses to cos α, so its
    numerator Σ c·b/cos α is Σ c·l, which is Fellenius's numerator; and
    both divide by Σ W·sin α. Any difference at all means one of the two
    is not reading the same envelope.
    """

    @staticmethod
    def _slope(strength):
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material
        from ogr_core.project import Project

        p = Project("ordinary vs bishop")
        ext = Polyline(vertices=[Vertex(*v) for v in
                                 ((0, 0), (100, 0), (100, 40), (60, 40),
                                  (30, 10), (0, 10))], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="m", unit_weight=20.0,
                                strength=strength)]
        return p

    @staticmethod
    def _pair(project, circle=(52.0, 52.0, 45.0), n=50):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle

        cx, cy, r = circle
        out = []
        for mid in ("ordinary_fellenius", "bishop_simplified"):
            res = GridSearch(method=get_method(mid)(), num_slices=n,
                             min_area=0.0).evaluate_circle(
                project, SlipCircle(centre_x=cx, centre_y=cy, radius=r))
            assert res is not None, mid
            out.append(float(res.fos))
        return out

    def test_phi_zero_depth_profile_the_two_methods_are_one_equation(self):
        ordinary, bishop = self._pair(self._slope(
            _perfil()))
        assert ordinary == pytest.approx(bishop, rel=1e-9), (
            f"Fellenius {ordinary!r} vs Bishop {bishop!r}: with phi = 0 "
            f"they are the same sum, so a gap means one of them is not "
            f"reading the depth profile")

    def test_and_the_number_is_not_the_no_context_fallback(self):
        """Guards the identity above, which two WRONG readings would also
        satisfy. Without a context the datum model answers its value at
        the reference elevation — a constant — so the depth profile must
        differ from the constant it degrades to."""
        from ogr_core.materials.builtin_models import Undrained
        varying, _ = self._pair(self._slope(_perfil()))
        flat, _ = self._pair(self._slope(Undrained(cohesion=20.0)))
        assert varying > flat * 1.5, (varying, flat)

    def test_shansep_too(self):
        from ogr_core.materials.builtin_models import SHANSEP
        ordinary, bishop = self._pair(
            self._slope(SHANSEP(S=0.25, m=0.8, OCR=2.0)))
        assert ordinary == pytest.approx(bishop, rel=1e-9), (ordinary, bishop)

    def test_mohr_coulomb_is_untouched(self):
        """The 100-odd cases of the verification bank run on Mohr-Coulomb,
        and the linearisation is exact for a straight envelope: the change
        must not have moved them by a digit. Fellenius stays the
        conservative member of the family, which is what this gap is."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        ordinary, bishop = self._pair(
            self._slope(MohrCoulomb(cohesion=20.0, friction_angle=20.0)))
        assert ordinary < bishop
        assert 0.85 < ordinary / bishop < 0.95, (ordinary, bishop)

    def test_the_suction_cohesion_reaches_it(self):
        """v0.1.28 says the suction cohesion is added in ``_local_c_phi``
        so that "the seven LEM methods pick it up without touching any of
        them". Of Ordinary that was not true: it never went through
        ``_local_c_phi`` for the strength.

        Written on the slices directly, which is where the slicer leaves
        it, so the test does not need a converged seepage field to make a
        negative pore pressure."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        p = self._slope(MohrCoulomb(cohesion=5.0, friction_angle=20.0))
        surface = SlipCircle(centre_x=52.0, centre_y=52.0, radius=45.0)
        method = get_method("ordinary_fellenius")()

        dry = slice_surface(p, surface, num_slices=50)
        base = method.compute_fos(p, surface, dry).fos
        wet = slice_surface(p, surface, num_slices=50)
        for s in wet:
            s.suction_cohesion = 15.0
        with_suction = method.compute_fos(p, surface, wet).fos
        assert with_suction > base * 1.10, (base, with_suction)

        # And by the same proportion as the method that always saw it:
        # both now read the envelope through the one linearisation.
        bishop = get_method("bishop_simplified")()
        b_dry = bishop.compute_fos(p, surface, dry).fos
        b_wet = bishop.compute_fos(p, surface, wet).fos
        assert (with_suction / base) == pytest.approx(b_wet / b_dry,
                                                      rel=0.02)
