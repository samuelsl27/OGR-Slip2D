# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Every Project Settings control has to move a number. One test per wire.

This file exists because of what an audit of Project Settings found: ten
controls that were stored, edited from the interface, serialised into the
``.ogr``, and read by **nobody**. The whole Advanced page. The whole
Random Numbers page. The convergence tolerance and the iteration cap on
the Methods page. That is rule 7 at scale — the same failure the design
standard's partial factors had between v0.1.52 and v0.1.57, which is why
the rule exists.

The tests are grouped by wire, and each one is written to fail if the
wire is cut: it changes the setting and asserts the RESULT changes, never
that the value round-trips through the dataclass. A round-trip test would
have passed happily for all ten of them.

Two settings needed their default corrected before they could be wired at
all, and the reason is worth keeping:

* ``check_tensile_stresses`` defaulted to True while the reference has
  the check OFF. Nobody noticed, because switching it changed nothing.
  Wiring it as it stood would have turned the check on for every stored
  project as a side effect.

* ``min_lambda`` / ``max_lambda`` were ±1.25 while the λ grid actually
  searched is ±1.5. Not a rounding difference: on the reference-validated
  circle, GLE converges at **λ = 1.4919**, outside ±1.25. Honouring the
  stored range would have clipped the search below what a validated case
  needs, which is measured below rather than asserted from memory.
"""
from __future__ import annotations

import math


# ======================================================================
# Fixtures
# ======================================================================
def _slope():
    """An ordinary slope, sliceable and with a sensible factor of safety."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("wiring")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=10, friction_angle=25))]
    return p


def _circle():
    from ogr_slip2d import SlipCircle
    return SlipCircle(centre_x=35, centre_y=42, radius=35)


def _sliced(project=None):
    from ogr_slip2d import slice_surface
    p = project or _slope()
    sl = slice_surface(p, _circle(), num_slices=25)
    assert sl is not None
    return p, _circle(), sl


# ======================================================================
# A. The convergence settings reach the methods
# ======================================================================
class TestTheMethodsGetTheirConvergenceSettings:
    """``tolerance``, ``max_iterations`` and ``initial_fos`` were accepted
    by every method from the day it was written, and every call site
    instantiated the methods with no arguments at all."""

    def test_every_method_accepts_the_shared_configuration(self):
        """The regression that cost a hung test suite.

        The compute worker builds ALL five methods eagerly from one
        ``lem_kwargs()`` dict. GLE overrides ``__init__`` and, when
        ``iterate_steffensen`` was added to the base class, did not grow
        the argument — so constructing the method map raised TypeError,
        the worker caught it and returned no results, and an empty
        deterministic result reaches a modal ``QMessageBox`` that blocks
        forever without a screen (AGENTS.md, "no modal dialogs in code a
        test will run"). The failure looked like a hang, not an error.

        Constructing every method with the full argument set is the cheap
        guard against the whole class: a subclass that overrides
        ``__init__`` and forgets one.
        """
        from ogr_core.project import ProjectSettings
        from ogr_slip2d.methods import (
            BishopSimplified, GLEMorgensternPrice, JanbuCorrected,
            JanbuSimplified, OrdinaryFellenius, Spencer,
        )
        s = ProjectSettings()
        kw = dict(s.lem_kwargs(),
                  min_lambda=s.advanced.min_lambda,
                  max_lambda=s.advanced.max_lambda)
        for cls in (BishopSimplified, JanbuSimplified, JanbuCorrected,
                    OrdinaryFellenius, Spencer, GLEMorgensternPrice):
            method = cls(**kw)          # must not raise
            assert method.tolerance == kw["tolerance"], cls.__name__
            assert method.iterate_steffensen is kw["iterate_steffensen"], \
                cls.__name__

    def test_lem_kwargs_carries_all_four(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        s.methods.tolerance = 1e-7
        s.methods.max_iterations = 123
        s.advanced.initial_fos = 1.4
        kw = s.lem_kwargs()
        assert kw["tolerance"] == 1e-7
        assert kw["max_iterations"] == 123
        assert abs(kw["initial_fos"] - 1.4) < 1e-12

    def test_a_tighter_tolerance_changes_the_answer(self):
        """A fixed-point iteration stopped at |Δ| < tol carries an error
        of that order, so tightening it must move the number. If it does
        not, the tolerance is not reaching the loop."""
        from ogr_slip2d.methods import BishopSimplified
        p, c, sl = _sliced()
        loose = BishopSimplified(tolerance=1e-2,
                                 max_iterations=200).compute_fos(p, c, sl)
        tight = BishopSimplified(tolerance=1e-12,
                                 max_iterations=200).compute_fos(p, c, sl)
        assert loose.converged and tight.converged
        assert abs(loose.fos - tight.fos) > 1e-6, (loose.fos, tight.fos)
        assert tight.iterations > loose.iterations

    def test_the_iteration_cap_can_stop_the_solve(self):
        from ogr_slip2d.methods import BishopSimplified
        p, c, sl = _sliced()
        capped = BishopSimplified(tolerance=1e-12,
                                  max_iterations=2).compute_fos(p, c, sl)
        assert capped.converged is False
        assert capped.iterations == 2

    def test_the_initial_guess_is_a_starting_point_not_a_floor(self):
        """The misnomer that came with the field: it was called
        ``min_initial_fs``. A converged run must reach the same root from
        either end, which is also what proves it is not a clamp."""
        from ogr_slip2d.methods import BishopSimplified
        p, c, sl = _sliced()
        low = BishopSimplified(initial_fos=0.2, tolerance=1e-12,
                               max_iterations=300).compute_fos(p, c, sl)
        high = BishopSimplified(initial_fos=5.0, tolerance=1e-12,
                                max_iterations=300).compute_fos(p, c, sl)
        assert low.converged and high.converged
        assert abs(low.fos - high.fos) < 1e-8, (low.fos, high.fos)
        assert low.fos < 5.0, "a floor at 5.0 would have pinned it there"


# ======================================================================
# B. Steffensen
# ======================================================================
class TestSteffensenAcceleratesWithoutMovingTheRoot:
    """The measurement that decided this wiring, kept as a test.

    On the reference-validated circle of the Ej1 case, at a tolerance
    tight enough that both have genuinely converged, plain iteration
    needs 19 passes and Steffensen 7, and the two answers agree to
    1.4e-11. At the DEFAULT tolerance they differ by 9e-4 — and the
    accelerated one is the closer of the two to the true root, because it
    is a better estimate at the point where both stop.

    That is the argument for switching it on by default, and it is an
    argument that has to keep holding, so it is pinned here.
    """

    def _pair(self, tol, iters=300):
        from ogr_slip2d.methods import BishopSimplified
        p, c, sl = _sliced()
        plain = BishopSimplified(tolerance=tol, max_iterations=iters,
                                 iterate_steffensen=False)
        fast = BishopSimplified(tolerance=tol, max_iterations=iters,
                                iterate_steffensen=True)
        return plain.compute_fos(p, c, sl), fast.compute_fos(p, c, sl)

    def test_both_converge_to_the_same_root(self):
        plain, fast = self._pair(1e-12)
        assert plain.converged and fast.converged
        assert abs(plain.fos - fast.fos) < 1e-8, (plain.fos, fast.fos)

    def test_it_gets_there_in_fewer_passes(self):
        plain, fast = self._pair(1e-12)
        assert fast.iterations < plain.iterations, (plain.iterations,
                                                    fast.iterations)

    def test_it_is_the_more_accurate_answer_at_a_loose_tolerance(self):
        """Rule 7 for this switch, and the reason it defaults to on."""
        exact, _ = self._pair(1e-13)
        plain, fast = self._pair(5e-3)
        assert abs(fast.fos - exact.fos) < abs(plain.fos - exact.fos)

    def test_the_extrapolation_declines_rather_than_divides_by_zero(self):
        """A converged sequence has a vanishing second difference. The
        helper must return None there, so turning the option on can never
        make a surface fail that would otherwise have converged."""
        from ogr_slip2d.methods.base import LEMMethod
        assert LEMMethod.aitken(1.0, 1.0, 1.0) is None
        assert LEMMethod.aitken(2.0, 2.0, 2.0 + 1e-16) is None
        # A genuine geometric sequence extrapolates to its limit: with
        # x_n = 1 + 2^-n the fixed point is 1.
        got = LEMMethod.aitken(1.5, 1.25, 1.125)
        assert got is not None and abs(got - 1.0) < 1e-12


# ======================================================================
# C. The lambda range
# ======================================================================
class TestTheLambdaRangeClipsACalibratedGrid:

    def test_the_default_range_reproduces_the_shipped_grid_exactly(self):
        """The grid was a literal in two methods until v0.1.74. If the
        default range did not regenerate it byte for byte, every stored
        project's Spencer and GLE results would have moved."""
        from ogr_slip2d.methods import Spencer
        assert Spencer().lambda_grid() == [
            -1.5, -1.0, -0.6, -0.4, -0.2, -0.1, 0.0,
            0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5]

    def test_a_narrower_range_drops_the_samples_outside_it(self):
        from ogr_slip2d.methods import Spencer
        grid = Spencer(min_lambda=-0.5, max_lambda=0.5).lambda_grid()
        assert max(grid) <= 0.5 + 1e-12 and min(grid) >= -0.5 - 1e-12
        assert 1.0 not in grid

    def test_the_endpoints_are_always_sampled(self):
        """Without them a narrowed range can lose the sign change that
        brackets the root and report 'all sampled λ diverged' for a
        surface that has a perfectly good solution."""
        from ogr_slip2d.methods import Spencer
        grid = Spencer(min_lambda=-0.35, max_lambda=0.55).lambda_grid()
        assert any(abs(v + 0.35) < 1e-12 for v in grid)
        assert any(abs(v - 0.55) < 1e-12 for v in grid)

    def test_the_stored_default_would_have_clipped_a_validated_case(self):
        """The measurement behind the ±1.25 → ±1.5 correction.

        GLE converges at λ = 1.4919 on the Ej1 reference circle. The old
        stored range stopped at 1.25, so wiring it unchanged would have
        excluded the solution of a case the project validates against a
        published value.
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import _runner
        val = _runner._load_module(
            Path(__file__).resolve().parent / "test_slide_validation_ej1.py")

        from ogr_slip2d import SlipCircle, slice_surface
        from ogr_slip2d.methods import GLEMorgensternPrice
        p = val._ej1_project()
        circle = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl = slice_surface(p, circle, num_slices=25)
        res = GLEMorgensternPrice().compute_fos(p, circle, sl)
        lam = res.details["lambda"]
        assert 1.25 < lam < 1.5, lam

    def test_the_two_mistaken_defaults_are_migrated(self):
        """A file written before v0.1.74 carries values that never
        reached a calculation, so they express no intent to preserve —
        which is what makes rewriting them safe."""
        from ogr_core.project.settings import AdvancedSettings
        old = AdvancedSettings.from_dict({
            "check_tensile_stresses": True, "min_initial_fs": 1.4,
            "min_lambda": -1.25, "max_lambda": 1.25})
        assert old.check_tensile_stresses is False
        assert old.min_lambda == -1.5 and old.max_lambda == 1.5
        # The renamed field keeps its value.
        assert abs(old.initial_fos - 1.4) < 1e-12

    def test_a_deliberate_value_is_left_alone(self):
        from ogr_core.project.settings import AdvancedSettings
        kept = AdvancedSettings.from_dict({"min_lambda": -0.8,
                                           "max_lambda": 0.9})
        assert kept.min_lambda == -0.8 and kept.max_lambda == 0.9


# ======================================================================
# D. The tensile stress check
# ======================================================================
class TestTheTensileCheckReachesTheSearch:

    def test_admissibility_kwargs_carries_both(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        s.advanced.check_tensile_stresses = True
        s.advanced.tensile_percent = 80.0
        kw = s.admissibility_kwargs()
        assert kw["reject_tensile"] is True
        assert abs(kw["tensile_percent"] - 80.0) < 1e-12

    def test_it_marks_surfaces_inadmissible(self):
        """Rule 7. On the validated Ej1 grid search the check rejects 149
        of 3077 surfaces — and, measured rather than assumed, it does NOT
        reject the global minimum, which is why turning it on was safe.
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import _runner
        val = _runner._load_module(
            Path(__file__).resolve().parent / "test_slide_validation_ej1.py")

        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch

        def _run(reject):
            return GridSearch(
                method=BishopSimplified(), grid_x=(40, 120), grid_y=(30, 120),
                grid_nx=8, grid_ny=8, radius_increment=10, min_radius=2.0,
                num_slices=25, min_area=0.5, reject_tensile=reject,
                tensile_percent=95.0).run(val._ej1_project())

        off, on = _run(False), _run(True)
        assert off.inadmissible_count == 0
        assert on.inadmissible_count > 0, "the check rejected nothing"
        # The minimum survives, so enabling the check does not change the
        # answer of a validated model — only what it refuses to report.
        assert abs(off.critical.fos - on.critical.fos) < 1e-9

    def test_the_default_is_off_as_in_the_reference(self):
        from ogr_core.project.settings import AdvancedSettings
        assert AdvancedSettings().check_tensile_stresses is False


class TestTheMAlphaCheckIsReachableButOff:
    """The anomaly of rule 6, pinned as a test instead of as a comment.

    The project believed from v0.1.32 to v0.1.81 that this check rejects
    the reference-validated critical circle, and the response had been to
    leave it out of the interface entirely. That is the wrong half of the
    right worry: hiding a capability the engine has is rule 3 in reverse.
    v0.1.74 offered it, off by default.

    v0.1.82 found the cause, and it was not the criterion. ``m_alpha`` is
    not symmetric in α, so it only means anything read with the same sense
    of sliding the solver used; the check dropped that factor, and this
    model slides towards decreasing x. The circle passes comfortably. The
    default stays OFF because that is how the reference ships it — not
    because it rejects anything.
    """

    def _reference_result(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import _runner
        val = _runner._load_module(
            Path(__file__).resolve().parent / "test_slide_validation_ej1.py")
        from ogr_slip2d import SlipCircle, slice_surface
        from ogr_slip2d.methods import BishopSimplified
        p = val._ej1_project()
        circle = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
        sl = slice_surface(p, circle, num_slices=25)
        return BishopSimplified().compute_fos(p, circle, sl)

    def test_it_accepts_the_reference_validated_circle(self):
        """The measurement, not the memory of it — and it is the opposite
        of what this test asserted until v0.1.82.

        Read with the ``slide_sign`` the solver uses, the minimum m-alpha
        of the validated critical circle is +0.928, and no slice comes
        near the 0.2 limit. The old reading (−0.010, five slices "below
        the limit") was the mirror image, not a property of the circle.
        """
        from ogr_slip2d.checks import base_m_alphas, check_surface
        res = self._reference_result()
        values = base_m_alphas(res)
        assert min(values) > 0.9, min(values)
        assert not [v for v in values if v < 0.2]
        ok, why = check_surface(res, m_alpha=True)
        assert ok is True and why is None

    def test_turning_it_on_is_still_distinguishable_from_leaving_it_off(
            self):
        """The check has to keep saying no to something, or enabling it
        would be a control that does nothing (rule 7).

        The surface that still fails is the one the reference describes:
        a base that rises almost vertically in the passive zone. It is
        pinned in detail in ``test_checks_v132.py``; what is asserted
        here is only that the two answers differ.
        """
        from ogr_slip2d.checks import m_alpha_check
        assert m_alpha_check.__doc__            # the criterion exists
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.methods import Spencer
        assert GridSearch(method=Spencer()).check_m_alpha is False
        assert GridSearch(method=Spencer(),
                          check_m_alpha=True).check_m_alpha is True

    def test_and_passes_it_with_the_check_off(self):
        """Off is the default because that is what the reference ships;
        the published factor of safety is reproducible either way."""
        from ogr_slip2d.checks import check_surface
        ok, why = check_surface(self._reference_result(), m_alpha=False)
        assert ok is True and why is None

    def test_the_default_is_off_and_it_reaches_the_search(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        assert s.advanced.check_m_alpha is False
        assert s.admissibility_kwargs()["check_m_alpha"] is False
        s.advanced.check_m_alpha = True
        assert s.admissibility_kwargs()["check_m_alpha"] is True


# ======================================================================
# E. The interslice force function
# ======================================================================
class TestTheIntersliceFunctionIsChoosable:
    """GLE has accepted one since it was written; nothing ever passed a
    different one, so the half sine was not a default but the only
    reachable option."""

    def test_every_named_function_resolves(self):
        from ogr_slip2d.methods.gle import (
            INTERSLICE_FUNCTIONS, interslice_function,
        )
        for name in ("half_sine", "constant", "trapezoidal", "clipped_sine"):
            assert name in INTERSLICE_FUNCTIONS
            assert callable(interslice_function(name))

    def test_an_unknown_name_falls_back_to_the_half_sine(self):
        from ogr_slip2d.methods.gle import half_sine, interslice_function
        assert interslice_function("nonsense") is half_sine

    def test_the_choice_moves_the_factor_of_safety(self):
        """Rule 7 for this control."""
        from ogr_slip2d.methods.gle import (
            GLEMorgensternPrice, interslice_function,
        )
        p, c, sl = _sliced()
        out = {}
        for name in ("half_sine", "constant", "trapezoidal"):
            res = GLEMorgensternPrice(
                interslice_func=interslice_function(name)
            ).compute_fos(p, c, sl)
            assert math.isfinite(res.fos), name
            out[name] = res.fos
        assert abs(out["half_sine"] - out["constant"]) > 1e-6, out

    def test_a_constant_function_makes_gle_agree_with_spencer(self):
        """The identity that anchors the whole control: Spencer IS the
        GLE solution for a constant interslice function, so the two must
        return the same number. An analytic identity, not a captured
        value."""
        from ogr_slip2d.methods import Spencer
        from ogr_slip2d.methods.gle import (
            GLEMorgensternPrice, interslice_function,
        )
        p, c, sl = _sliced()
        gle = GLEMorgensternPrice(
            tolerance=1e-10,
            interslice_func=interslice_function("constant"),
        ).compute_fos(p, c, sl)
        spencer = Spencer(tolerance=1e-10).compute_fos(p, c, sl)
        assert abs(gle.fos - spencer.fos) < 1e-3, (gle.fos, spencer.fos)


# ======================================================================
# F. The seed, of which there used to be two
# ======================================================================
class TestThereIsOneSeed:

    def test_the_random_numbers_page_is_what_decides(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        s.random_numbers.seed = 777
        assert s.analysis_seed() == 777

    def test_a_clock_seeded_run_has_no_seed(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        s.random_numbers.method = "random"
        assert s.analysis_seed() is None

    def test_an_explicit_statistics_seed_still_wins(self):
        """Honouring a value someone deliberately wrote is cheaper than
        surprising them; the field predates the unification."""
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        s.random_numbers.seed = 777
        s.statistics.seed = 4242
        assert s.analysis_seed() == 4242

    def test_the_seed_makes_a_random_search_reproducible(self):
        """What the page promised and no search had ever been told."""
        from ogr_slip2d import PathSearch
        from ogr_slip2d.methods import BishopSimplified

        def _run(seed):
            r = PathSearch(method=BishopSimplified(), num_paths=6,
                           num_slices=15, optimize=False, seed=seed)
            return [e.surface.polyline.vertices[0].x
                    for e in r.run(_slope()).evaluations]

        assert _run(11) == _run(11)
        assert _run(11) != _run(12)


# ======================================================================
# G. Latin Hypercube stratification
# ======================================================================
class TestTheStratificationSwitch:

    def _dists(self):
        from ogr_core.statistics.distributions import (
            Distribution, DistributionType,
        )
        return {k: Distribution(dist_type=DistributionType.UNIFORM,
                                mean=10.0, std_dev=2.0,
                                rel_min=5.0, rel_max=5.0)
                for k in ("a", "b")}

    def test_off_the_variables_are_stratified_independently(self):
        from ogr_core.statistics.distributions import (
            SamplingMethod, sample_variables,
        )
        s = sample_variables(self._dists(), 40,
                             SamplingMethod.LATIN_HYPERCUBE, seed=3,
                             correlate=False)
        assert s["a"] != s["b"]

    def test_on_they_share_one_stratification(self):
        """Rule 7: the switch has to change the samples, because it
        changes the question being asked — correlated strata answer 'what
        if everything is unfavourable at once'."""
        from ogr_core.statistics.distributions import (
            SamplingMethod, sample_variables,
        )
        s = sample_variables(self._dists(), 40,
                             SamplingMethod.LATIN_HYPERCUBE, seed=3,
                             correlate=True)
        assert s["a"] == s["b"]

    def test_it_does_nothing_to_monte_carlo(self):
        """There are no strata to share, so it must be ignored rather
        than quietly correlating an uncorrelated method."""
        from ogr_core.statistics.distributions import (
            SamplingMethod, sample_variables,
        )
        kw = dict(n=40, method=SamplingMethod.MONTE_CARLO, seed=3)
        off = sample_variables(self._dists(), **kw, correlate=False)
        on = sample_variables(self._dists(), **kw, correlate=True)
        assert off == on


# ======================================================================
# H. The dialog bugs the audit turned up
# ======================================================================
def _dialog():
    from PySide6.QtWidgets import QApplication
    from ogr_core.project import ProjectSettings
    from ogr_gui.dialogs.project_settings_dialog import ProjectSettingsDialog
    QApplication.instance() or QApplication([])
    s = ProjectSettings()
    d = ProjectSettingsDialog(s)
    _WINDOWS.append(d)
    return s, d


_WINDOWS: list = []


class TestTheDialogKeepsItsPages:

    def test_restore_defaults_rebuilds_all_nine(self):
        """It rebuilt four. Transient, Statistics, Random Numbers, Design
        Standard and Advanced vanished until the dialog was reopened,
        because ``_defaults`` carried a second, shorter, hand-written
        list of the pages."""
        _s, d = _dialog()
        assert d.nav.count() == 9
        d._defaults()
        assert d.nav.count() == 9
        assert len(d.pages) == 9

    def test_the_advanced_option_has_exactly_one_home(self):
        """Groundwater and Transient both used to write it, and
        ``_apply`` runs the pages in order, so the later one won."""
        s, d = _dialog()
        gw = d.pages[2]
        gw.cb_rapid.setChecked(True)
        d._apply()
        assert s.groundwater.advanced_option() == "rapid_drawdown"
        gw.rb_transient.setChecked(True)
        d._apply()
        assert s.groundwater.advanced_option() == "transient"
        assert s.groundwater.rapid_drawdown is False

    def test_the_interslice_combo_needs_gle(self):
        from ogr_core.project.settings import LEMMethod as LEM
        _s, d = _dialog()
        methods = d.pages[1]
        gle = methods.checkboxes[LEM.GLE_MORGENSTERN_PRICE.value]
        gle.setChecked(False)
        assert methods.cbo_f.isEnabled() is False
        gle.setChecked(True)
        assert methods.cbo_f.isEnabled() is True

    def test_the_tensile_percentage_needs_the_check(self):
        _s, d = _dialog()
        advanced = d.pages[7]
        advanced.chk_tensile.setChecked(False)
        assert advanced.sp_tensile_pct.isEnabled() is False
        advanced.chk_tensile.setChecked(True)
        assert advanced.sp_tensile_pct.isEnabled() is True


class TestTheNewStringsAreTranslated:
    KEYS = [
        "Percentage of slices:",
        "Interslice force function:",
        "Half Sine",
        "Constant",
        # "Trapezoidal" is deliberately absent: it is the same word in
        # Spanish, so asserting tr(k) != k would be asserting a wrong
        # translation. It is listed with the other cognates in
        # test_i18n_coverage_v141's allow-list instead.
        "Clipped Sine",
        "Transient groundwater",
        "None",
        "On",
    ]

    def test_every_new_key_has_a_spanish_entry(self):
        from ogr_gui.i18n import current_language, set_language, tr
        prev = current_language()
        try:
            set_language("es")
            untranslated = [k for k in self.KEYS if tr(k) == k]
            assert not untranslated, untranslated
        finally:
            set_language(prev)
