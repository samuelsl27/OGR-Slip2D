# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The rapid drawdown reaches every method, and no door lets it be skipped.

WHAT INVARIANT THIS PROTECTS.

A rapid drawdown replaces what "the factor of safety of this surface"
means. Two ways of losing it entirely have been measured in this program,
and both returned a plausible number rather than an error:

1. **It only worked with two of the nine methods.** ``_stage1_state``
   recovers the stage-1 consolidation state from the base normal force,
   and until v0.1.107 only Bishop and Fellenius reported that column. With
   any other method the list arrived empty, a ``break`` ended the loop on
   the first pass, and the two-stage procedure quietly became a re-run of
   stage 1 at the lowered reservoir — undrained strength on ZERO slices.
   Measured on the circle below: Spencer 2.0773 against a published 1.347,
   **+54 % on the unsafe side**. Closed by v0.1.107; this file is what
   keeps it closed, and the guard is now an explicit refusal rather than a
   truncation, so a tenth method that forgets the column fails loudly.

2. **``build_method`` is the only place that applies the wrapper**, so
   handing a class out of ``method_registry()`` to a search returned an
   ordinary DRAINED analysis with no exception and no warning (anomaly
   A98-1). Measured on the same circle with Spencer: 2.2017 by the short
   path against 1.3498 by the wrapped one, **+63 %**. Verification problem
   98 is what that looks like from outside — three different drawdown
   procedures agreeing to six decimal places.

The reference: EM 1110-2-1902 Appendix G
----------------------------------------
One circle, given, no search: centre (169.5, 210), radius 210 ft on the
homogeneous embankment of the appendix, reservoir 103 to 24 ft. The SAME
circle carries two published factors of safety by two procedures — Corps
of Engineers 2-stage **1.35** and Duncan-Wright-Wong 3-stage **1.44** —
which is why ``test_drawdown_usace_v169`` uses it for Bishop. This file
asks the harder question that file could not: whether the OTHER EIGHT
methods reach the same published answers, or merely return something.

Why only four methods are compared against the published value
--------------------------------------------------------------
Bishop, Spencer, GLE and Lowe-Karafiath all satisfy moment equilibrium
with a genuine normal-force distribution, and all four land within 1.3 %
of both published values. Fellenius and Janbu Simplified do not, and
demanding that they should would be demanding that they stop being what
they are:

* the Ordinary Method of Slices neglects the interslice forces entirely
  and underestimates the factor of safety on circular surfaces with high
  pore pressures — the classical result (Whitman and Bailey 1967; Duncan
  and Wright 2005). Measured here: -15 % and -23 %.
* Janbu Simplified is Janbu's force-equilibrium method **without** the
  correction factor f0 that Janbu (1973) introduced for exactly this
  deficit. Measured: -10.4 % and -11.5 %, and Janbu Corrected — the same
  method with f0 — closes to -3.5 % and -3.9 %.

So what is pinned for those is the ORDERING and the direction, both of
which are statements about the methods rather than about this model. A
test that demanded 1.35 from Fellenius would be a test that had to be
"fixed" by breaking Fellenius.

Where the consolidation state comes from
----------------------------------------
From the method the user chose, run at the full reservoir — not from a
separate drained analysis. That is the source's own arrangement:
EM 1110-2-1902 (2003) section G-7 solves this same example with Spencer
and tabulates a DIFFERENT interslice force inclination for each of the
three stages (6.0, 12.2 and 13.7 degrees), and G-7a notes that the
stage-1 quantities match the Corps 1970 ones "except for differences
resulting from the assumed interslice force inclination". Each stage is
solved with the procedure of slices in use; stage 1 differing between
methods is a consequence the source names, not a defect.

Cost: about 5 s. Every (procedure, method) pair is solved once and cached.

References:
    Corps of Engineers (1970). *Stability of Earth and Rock Fill Dams*,
        EM 1110-2-1902.
    Corps of Engineers (2003). *Slope Stability*, EM 1110-2-1902,
        Appendix G: Procedures and Examples for Rapid Drawdown.
    Duncan, J. M., Wright, S. G. y Wong, K. S. (1990). "Slope Stability
        during Rapid Drawdown". H. Bolton Seed Memorial Symposium,
        vol. 2, pp. 253-272.
    Duncan, J. M. y Wright, S. G. (2005). *Soil Strength and Slope
        Stability*. Wiley.
    Janbu, N. (1973). "Slope stability computations". In *Embankment Dam
        Engineering, Casagrande Volume*, pp. 47-86.
    Lowe, J. y Karafiath, L. (1960). "Stability of Earth Dams upon
        Drawdown". 1st PanAmerican Conf. SMFE, Mexico D.F., vol. 2.
    Whitman, R. V. y Bailey, W. A. (1967). "Use of computers for slope
        stability analysis". J. Soil Mech. Found. Div. ASCE 93(SM4).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

GAMMA_W = 62.4          # pcf
NUM_SLICES = 50

#: The one slip surface the problem gives, and the two published answers.
#:
#: R = 209.9 and not the 210 of the prose, which is a rounding of it: the
#: solution panel of the reference prints 209.900. The distinction matters
#: HERE and not in ``test_drawdown_usace_v169``, which calls the procedure
#: directly: at exactly 210 the arc is tangent to the foundation at y = 0,
#: so floating point puts a piece of it a hair BELOW the external boundary
#: and ``leaves_soil_region`` discards the circle — correctly, since these
#: tests go in through the search, which is the door the defect lives on.
#: The two radii differ by 0.05 % and their factors of safety by 0.04 %.
CIRCLE = dict(centre_x=169.5, centre_y=210.0, radius=209.9)
PUBLISHED = {"corps_2": 1.35, "duncan_wright": 1.44}

INITIAL_Y = 103.0
FINAL_Y = 24.0

#: The methods whose factor of safety is compared against the published
#: value. See the module docstring for why the list is not all nine.
RIGOROUS = ("bishop_simplified", "spencer", "gle_morgenstern_price",
            "lowe_karafiath")
ALL_METHODS = ("bishop_simplified", "ordinary_fellenius", "spencer",
               "gle_morgenstern_price", "janbu_simplified",
               "janbu_corrected", "lowe_karafiath", "corps_engineers_1",
               "corps_engineers_2")

_CACHE: dict = {}


# ======================================================================
def _appendix_g(procedure="corps_2", *, undrained=True, drawdown=True,
                initial_y=INITIAL_Y, final_y=FINAL_Y):
    """The Appendix G slope, vertex by labelled vertex.

    A fresh project on every call: nothing here may leak into the next
    test (rule 5), and several tests below deliberately damage the
    settings.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.materials.drawdown_envelopes import REnvelope
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(380, 0), Vertex(380, 110),
        Vertex(350, 110), Vertex(330, 110), Vertex(312, 110),
        Vertex(296, 104), Vertex(268, 92), Vertex(246, 84),
        Vertex(222, 74), Vertex(201, 67), Vertex(170, 57),
        Vertex(135, 45), Vertex(105, 35),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("EM 1110-2-1902 Appendix G")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, initial_y),
                                    Vertex(385, initial_y)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, final_y),
                                    Vertex(385, final_y)], closed=False),
        btype=BoundaryType.DRAWDOWN))
    m = Material(
        name="Embankment", unit_weight=135.0, sat_unit_weight=135.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0),
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    m.undrained_behaviour = undrained
    m.drawdown_envelope = REnvelope(c_r=1200.0, phi_r_deg=16.0)
    p.materials = [m]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.settings.methods.num_slices = NUM_SLICES
    if drawdown:
        p.settings.groundwater.set_advanced_option("rapid_drawdown")
        p.settings.groundwater.rapid_drawdown_method = procedure
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**CIRCLE)


def _result(procedure, method_id):
    """The DrawdownResult of one (procedure, method) pair, computed once."""
    key = (procedure, method_id)
    if key not in _CACHE:
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        _CACHE[key] = rapid_drawdown_fos(
            _appendix_g(procedure), _circle(),
            method_registry()[method_id](),
            num_slices=NUM_SLICES, procedure=procedure)
    return _CACHE[key]


def _fos(procedure, method_id) -> float:
    return _result(procedure, method_id).fos


def _drained(method_id) -> float:
    """The same circle with no drawdown at all: the number to beat."""
    key = ("drained", method_id)
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch
        p = _appendix_g(drawdown=False)
        res = GridSearch(method=build_method(p, method_id, NUM_SLICES),
                         num_slices=NUM_SLICES,
                         min_area=0.0).evaluate_circle(p, _circle())
        assert res is not None and res.is_valid, method_id
        _CACHE[key] = res.fos
    return _CACHE[key]


# ======================================================================
class TestThePublishedValuesReachEveryRigorousMethod:
    """Rule 1: an external reference, on a surface we did not choose.

    Nine methods used to answer this and only two of them were running the
    procedure. Four are compared against the published number here; the
    other five are the subject of the next class.
    """

    def test_the_corps_two_stage(self):
        for mid in RIGOROUS:
            fos = _fos("corps_2", mid)
            assert math.isclose(fos, PUBLISHED["corps_2"], rel_tol=0.03), (
                f"{mid}: Corps 2-stage {fos:.4f} against the published "
                f"{PUBLISHED['corps_2']}")

    def test_duncan_wright_wong(self):
        for mid in RIGOROUS:
            fos = _fos("duncan_wright", mid)
            assert math.isclose(fos, PUBLISHED["duncan_wright"],
                                rel_tol=0.03), (
                f"{mid}: DWW 3-stage {fos:.4f} against the published "
                f"{PUBLISHED['duncan_wright']}")

    def test_the_gap_between_the_two_procedures_survives_the_method(self):
        """1.35/1.44 is nearly a direct reading of ``min(R, drained)``.

        Everything the two runs share — the slicing, the unit weights, the
        ponded load — cancels in the ratio, so what is left is the rule
        that separates the procedures. It has to come out the same
        whichever method carries it.
        """
        published = PUBLISHED["corps_2"] / PUBLISHED["duncan_wright"]
        for mid in RIGOROUS:
            ratio = _fos("corps_2", mid) / _fos("duncan_wright", mid)
            assert math.isclose(ratio, published, rel_tol=0.02), (
                f"{mid}: ratio {ratio:.4f} against the published "
                f"{published:.4f}")


# ======================================================================
class TestTheConservativeMethodsAreConservativeAndNotBroken:
    """The five not compared against 1.35, and what IS asked of them.

    Their distance from the published value is a property of the method,
    documented long before this program existed. What a test can demand is
    that the distance has the right sign and the right order.
    """

    def test_fellenius_and_janbu_simplified_fall_below(self):
        for procedure in PUBLISHED:
            rigorous = min(_fos(procedure, m) for m in RIGOROUS)
            for mid in ("ordinary_fellenius", "janbu_simplified"):
                assert _fos(procedure, mid) < rigorous, (
                    f"{mid} is not below the rigorous methods in "
                    f"{procedure}: {_fos(procedure, mid):.4f} against "
                    f"{rigorous:.4f}")

    def test_the_correction_factor_is_what_closes_janbus_gap(self):
        """f0 (Janbu 1973) has to move the answer TOWARDS the published one.

        The two methods differ by that factor alone, so this is the one
        comparison that isolates it.
        """
        for procedure, published in PUBLISHED.items():
            plain = _fos(procedure, "janbu_simplified")
            corrected = _fos(procedure, "janbu_corrected")
            assert plain < corrected, procedure
            assert abs(corrected - published) < abs(plain - published), (
                f"{procedure}: corrected {corrected:.4f} is no closer to "
                f"{published} than simplified {plain:.4f}")

    def test_the_two_corps_of_engineers_methods_sit_above_bishop(self):
        """A Modified Swedish procedure above Bishop, by the EM's own sums.

        Figure G-9 of the EM tabulates a phi = 0 second stage, so Bishop on
        those twelve published slices is sum(c*l)/sum(W*sin a) =
        601.3/472.3 = 1.2733 against the 1.35 the appendix reports for its
        Modified Swedish solution: **+6.0 %**. The separation is a fact
        about the two formulations, and it is why these two are not in
        ``RIGOROUS`` — they are not solving the same equations.
        """
        for procedure in PUBLISHED:
            bishop = _fos(procedure, "bishop_simplified")
            for mid in ("corps_engineers_1", "corps_engineers_2"):
                ratio = _fos(procedure, mid) / bishop
                assert 1.0 < ratio < 1.10, (
                    f"{procedure}/{mid}: {ratio:.4f} against the +6.0 % the "
                    f"EM's own Figure G-9 arithmetic gives")


# ======================================================================
class TestTheDrawdownMovesTheNumberInEveryMethod:
    """Rule 7, and the exact shape the defect had.

    Not "the option is honoured somewhere": it has to move the number in
    ALL NINE, and every slice of the mass has to be treated as undrained.
    What this guards against reported a perfectly convergent factor of
    safety computed with the strengths of a different analysis.
    """

    def test_every_method_treats_the_whole_mass_as_undrained(self):
        for procedure in ("corps_2", "duncan_wright", "lowe_karafiath"):
            for mid in ALL_METHODS:
                r = _result(procedure, mid)
                assert r.n_undrained_slices == NUM_SLICES, (
                    f"{procedure}/{mid}: {r.n_undrained_slices} undrained "
                    f"slices out of {NUM_SLICES}")

    def test_every_method_answers_lower_than_with_the_reservoir_full(self):
        for mid in ALL_METHODS:
            drained = _drained(mid)
            for procedure in PUBLISHED:
                fos = _fos(procedure, mid)
                assert fos < 0.9 * drained, (
                    f"{procedure}/{mid}: {fos:.4f} against {drained:.4f} "
                    f"with no drawdown — the procedure barely moved it")

    def test_stage_two_is_what_does_the_moving(self):
        """Stage 1 is an ordinary drained analysis and always worked.

        Which is how the defect was diagnosed: every method agreed on
        stage 1 to within a few per mille of its own drained answer while
        the final numbers disagreed by 54 %. So stage 1 is asserted to BE
        the drained analysis, and the drop to be stage 2's doing.
        """
        for mid in ALL_METHODS:
            r = _result("corps_2", mid)
            assert math.isclose(r.fos_stage1, _drained(mid), rel_tol=0.01), (
                f"{mid}: stage 1 {r.fos_stage1:.4f} against the drained "
                f"{_drained(mid):.4f}")
            assert r.fos_stage2 < r.fos_stage1


# ======================================================================
class TestTheProceduresOrderTheSameWayWhicheverMethodCarriesThem:
    """``FS_DWW <= FS_LK`` in all nine, and the Corps below both in most.

    Only the first of those is structural, and the distinction is worth
    keeping straight. Duncan-Wright-Wong IS Lowe-Karafiath with the drained
    cap switched on — one function, one flag — and the cap can only ever
    replace a strength by a smaller one, so the inequality is a property of
    the code. It is only a property of the code if it holds for every
    method, which is exactly what used to fail: with the procedure not
    running, all three gave the same number.

    Where the Corps sits is NOT structural. It reads an R envelope where
    the other two interpolate a K_c = 1 one, so which comes out lower
    depends on where the two envelopes cross — and that depends on the
    stage-1 stresses, which differ between methods. Measured here: the
    Corps is the lowest of the three in eight methods and the HIGHEST in
    Fellenius (1.1456 against 1.1098 and 1.1434), whose stage-1 factor is
    14 % below the others because it neglects the interslice forces
    altogether. Asserting a fixed order there would be pinning an accident.
    """

    def test_the_cap_only_ever_lowers_the_answer(self):
        for mid in ALL_METHODS:
            dww = _fos("duncan_wright", mid)
            lk = _fos("lowe_karafiath", mid)
            assert dww <= lk + 1e-9, (
                f"{mid}: DWW {dww:.4f} above Lowe-Karafiath {lk:.4f}, and "
                f"DWW is Lowe-Karafiath plus a cap that can only subtract")

    def test_the_corps_is_the_most_conservative_in_the_rigorous_family(self):
        for mid in RIGOROUS:
            corps = _fos("corps_2", mid)
            dww = _fos("duncan_wright", mid)
            assert corps < dww, (
                f"{mid}: corps {corps:.4f}, dww {dww:.4f}")

    def test_and_the_three_are_not_the_same_number(self):
        """The signature of a procedure that never ran (problem 98)."""
        for mid in ALL_METHODS:
            values = [_fos(p, mid) for p in
                      ("corps_2", "duncan_wright", "lowe_karafiath")]
            assert max(values) - min(values) > 1e-3, (
                f"{mid}: the three procedures agree to {values} — which is "
                f"what a drawdown that was never applied looks like")


# ======================================================================
class TestNoDoorReturnsADrainedNumberInSilence:
    """Anomaly A98-1: the search refuses a method that skips the drawdown."""

    def _raw(self, method_id="spencer"):
        from ogr_slip2d.methods import method_registry
        return method_registry()[method_id]()

    def _search(self, method):
        from ogr_slip2d.search import GridSearch
        return GridSearch(method=method, num_slices=NUM_SLICES, min_area=0.0)

    def test_evaluate_circle_raises_instead_of_answering(self):
        import pytest
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError

        p = _appendix_g("corps_2")
        with pytest.raises(RapidDrawdownError):
            self._search(self._raw()).evaluate_circle(p, _circle())

    def test_the_message_names_the_way_out(self):
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError

        p = _appendix_g("corps_2")
        try:
            self._search(self._raw()).evaluate_circle(p, _circle())
        except RapidDrawdownError as exc:
            assert "build_method" in str(exc)
            assert "spencer" in str(exc)
        else:
            raise AssertionError("it answered")

    def test_evaluate_surface_too(self):
        import pytest
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError
        from ogr_slip2d.surface import SlipSurface

        p = _appendix_g("corps_2")
        poly = SlipSurface(polyline=Polyline(
            vertices=[Vertex(72, 24), Vertex(170, 5), Vertex(300, 96)],
            closed=False))
        with pytest.raises(RapidDrawdownError):
            self._search(self._raw()).evaluate_surface(p, poly)

    def test_and_a_whole_search_run(self):
        import pytest
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError
        from ogr_slip2d.search import GridSearch

        p = _appendix_g("corps_2")
        with pytest.raises(RapidDrawdownError):
            GridSearch(method=self._raw(), grid_x=(150, 190),
                       grid_y=(200, 220), grid_nx=2, grid_ny=2,
                       radius_increment=40.0, num_slices=25).run(p)

    def test_the_configured_method_goes_through_and_gives_the_answer(self):
        """The other half: the guard must not block the good path."""
        from ogr_slip2d.analysis_runner import build_method

        p = _appendix_g("corps_2")
        res = self._search(
            build_method(p, "spencer", NUM_SLICES)).evaluate_circle(
                p, _circle())
        assert res is not None and res.is_valid
        assert math.isclose(res.fos, PUBLISHED["corps_2"], rel_tol=0.03)
        assert res.details.get("drawdown_procedure") == "corps_2"

    def test_a_project_without_a_drawdown_is_untouched(self):
        """The guard asks about the PAIR, so a raw method stays legitimate.

        Every test and every example in this repository builds a search by
        hand; the guard may not cost them anything.
        """
        p = _appendix_g(drawdown=False)
        res = self._search(self._raw()).evaluate_circle(p, _circle())
        assert res is not None and res.is_valid
        assert res.fos > 1.5


# ======================================================================
class TestTheSettingsAreCheckedWhereverTheMethodIsBuilt:
    """``check_drawdown_settings`` runs whenever the project asks for one.

    It has listed every reason a drawdown cannot run since v0.1.68, but
    only for a caller that thought to ask. ``build_method`` did not, so a
    model that could not run one got a number back instead of the reason.
    """

    def _build(self, project):
        from ogr_slip2d.analysis_runner import build_method
        return build_method(project, "bishop_simplified", NUM_SLICES)

    def test_no_undrained_material(self):
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError

        p = _appendix_g("corps_2", undrained=False)
        try:
            self._build(p)
        except RapidDrawdownError as exc:
            assert "Undrained Behaviour" in str(exc)
        else:
            raise AssertionError("it returned a method")

    def test_an_unknown_procedure_is_named_and_not_ignored(self):
        """v0.1.108 — this used to mean "no drawdown", silently.

        ``check_drawdown_settings`` returned None for an unrecognised name
        and ``wrap_for_drawdown`` returned the method unwrapped, so a
        procedure misspelt in a .ogr gave a drained analysis. A typo cost
        the same as anomaly A98-1.
        """
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError

        p = _appendix_g("corps_2")
        p.settings.groundwater.rapid_drawdown_method = "corps_3"
        try:
            self._build(p)
        except RapidDrawdownError as exc:
            assert "corps_3" in str(exc) and "corps_2" in str(exc)
        else:
            raise AssertionError("it returned a method")

    def test_the_two_levels_the_wrong_way_round(self):
        import pytest
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError

        p = _appendix_g("corps_2", initial_y=FINAL_Y, final_y=INITIAL_Y)
        with pytest.raises(RapidDrawdownError):
            self._build(p)

    def test_a_groundwater_method_that_has_no_second_level(self):
        import pytest
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError

        p = _appendix_g("corps_2")
        p.settings.groundwater.method = "ru"
        with pytest.raises(RapidDrawdownError):
            self._build(p)

    def test_a_project_that_asks_for_none_builds_as_it_always_did(self):
        p = _appendix_g(drawdown=False)
        method = self._build(p)
        assert method is not None
        assert not getattr(method, "PERFORMS_DRAWDOWN", False)


# ======================================================================
class TestTheStatisticsKeepTheDrawdown:
    """The third route by which the whole procedure was being dropped.

    ``run_global_minimum`` and ``run_sensitivity`` instantiated the method
    straight out of the registry unless handed a ``method_factory``, and
    nothing in this program ever handed them one — not the interface,
    which is what Statistics > Compute Statistics calls. So the statistics
    of a drawdown model were the statistics of a DRAINED model, and the
    convergence settings went with them (the v0.1.74 fault, still open on
    this path).

    Deliberately small: four samples of a variable with almost no spread.
    This is a wiring test, and the numbers it leans on are pinned above.
    """

    def _fixture(self):
        from ogr_core.statistics import (
            Distribution,
            DistributionType as DT,
            VariableKind as VK,
            available_variables,
        )
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch

        p = _appendix_g("corps_2")
        det = GridSearch(method=build_method(p, "bishop_simplified", 25),
                         num_slices=25,
                         min_area=0.0).evaluate_circle(p, _circle())
        assert det is not None and det.is_valid
        var = None
        for v in available_variables(p):
            if v.param == "unit_weight" and v.kind == VK.MATERIAL:
                v.distribution = Distribution(
                    DT.UNIFORM, mean=135.0, rel_min=0.5, rel_max=0.5)
                var = v
                break
        assert var is not None
        return p, {"bishop_simplified": det}, [var]

    def test_the_mean_is_the_drawdown_answer_and_not_the_drained_one(self):
        from ogr_core.statistics import SamplingMethod, run_global_minimum

        p, det, variables = self._fixture()
        res = run_global_minimum(p, det, variables, num_samples=4,
                                 sampling=SamplingMethod.MONTE_CARLO,
                                 seed=1, num_slices=25)
        assert res.ok, res.notes
        method_res = res.by_method["bishop_simplified"]
        assert method_res.failed_samples == 0
        mean = method_res.statistics.mean
        assert math.isclose(mean, det["bishop_simplified"].fos,
                            rel_tol=0.02), (
            f"mean {mean:.4f} against the deterministic drawdown "
            f"{det['bishop_simplified'].fos:.4f}")
        assert mean < 0.9 * _drained("bishop_simplified")

    def test_the_sensitivity_sweep_too(self):
        from ogr_core.statistics import run_sensitivity

        p, det, variables = self._fixture()
        res = run_sensitivity(p, det, variables, intervals=2, num_slices=25)
        assert res.ok, res.notes
        sweep = next(iter(res.by_method["bishop_simplified"].values()))
        values = [f for f in sweep.fos if f is not None and math.isfinite(f)]
        assert values, "the sweep produced no factor of safety at all"
        assert max(values) < 0.9 * _drained("bishop_simplified"), (
            f"{values} — a drained sweep of a drawdown model")


# ======================================================================
class TestTheSilentDegradationCannotComeBack:
    """A method that omits the base normal force must FAIL, not degrade.

    This is the shape of the original defect, kept as a test because the
    number it produced was convergent, plausible and 54 % wrong. The guard
    is not about the arithmetic — it is about what happens when a piece of
    it is missing.
    """

    class _Forgetful:
        """Solves correctly and reports no normal forces, as Janbu did."""

        METHOD_ID = "forgetful"
        DISPLAY_NAME = "Forgetful"

        def __init__(self):
            from ogr_slip2d.methods import method_registry
            self._inner = method_registry()["bishop_simplified"]()

        def compute_fos(self, project, surface, slices):
            res = self._inner.compute_fos(project, surface, slices)
            res.base_normal_force = []
            return res

    def test_it_raises_with_the_method_named(self):
        from ogr_slip2d.rapid_drawdown import (
            RapidDrawdownError,
            rapid_drawdown_fos,
        )

        try:
            rapid_drawdown_fos(_appendix_g("corps_2"), _circle(),
                               self._Forgetful(), num_slices=NUM_SLICES,
                               procedure="corps_2")
        except RapidDrawdownError as exc:
            assert "0 base normal forces" in str(exc)
            assert str(NUM_SLICES) in str(exc)
        else:
            raise AssertionError(
                "the procedure ran with no consolidation state, which is "
                "the defect this test exists for")

    def test_and_a_search_reports_it_rather_than_dying(self):
        """The wrapper turns it into an invalid surface with a reason.

        A search evaluates thousands of candidates, so a surface the
        procedure cannot handle has to be counted and explained, not fatal.
        """
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.search import GridSearch

        p = _appendix_g("corps_2")
        wrapped = MultiStageDrawdownMethod(
            self._Forgetful(), "corps_2", num_slices=NUM_SLICES)
        res = GridSearch(method=wrapped, num_slices=NUM_SLICES,
                         min_area=0.0).evaluate_circle(p, _circle())
        assert res is not None and not res.is_valid
        assert "base normal forces" in res.error_message
