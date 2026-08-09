# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.77 — the command line runs the analysis the project describes.

Invariant protected: ``ogr-slip2d-cli compute`` and the graphical
interface, given the same ``.ogr``, produce the same number.

Why this file exists. ``ogr_cli`` had **no tests at all** — not one file
in this suite imported it — and ``compute`` read nothing whatsoever from
``project.settings``. It deserialised the geometry and the materials and
then built its own search out of command-line defaults. Three of those
omissions failed silently and on the unsafe side:

- rapid drawdown was never applied (noted as pending in the changelogs of
  v0.1.72, v0.1.74 and v0.1.75), so a terminal run reported the ORDINARY
  factor of safety of a drawdown project;
- the design-standard partial factors were never applied, so the run used
  unfactored c', φ' and γ;
- the finite-element seepage field is not stored in the ``.ogr``, and the
  pore-pressure lookup answers 0.0 when it is missing, so the run
  reported a dry slope.

These are not snapshot tests. Where a number is asserted, the reference
is either an externally validated case (Morgenstern 1963, through
``ogr_slip2d``'s own validated drawdown model) or the value produced by
the interface path — the one that has been validated against published
cases since v0.1.59. Where a setting is asserted, the test shows the
setting MOVES the result, because a wiring test that does not move the
number cannot tell a wired control from an ignored one (rule 7).
"""
from __future__ import annotations

import math
from pathlib import Path

GAMMA_W = 62.4
GAMMA = 124.8


# ======================================================================
# Models
# ======================================================================
def _small_slope(name="cli"):
    """A homogeneous slope small enough to search several times over.

    The grid is deliberately tiny (3 x 3 centres, 3 radii): these tests
    measure WHICH analysis ran, never how good the minimum is, so paying
    for a fine grid would buy nothing and cost seconds per test.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
        Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_material(Material(
        name="Silty clay", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0)))
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.methods.num_slices = 25
    p.settings.search.grid_nx = 3
    p.settings.search.grid_ny = 3
    p.settings.search.radius_increment = 2
    return p


def _morgenstern_drawdown(b_bar=1.0):
    """The Morgenstern (1963) slope with a complete B-bar drawdown.

    Same geometry as ``test_drawdown_bbar_v169``, which validates the
    model itself against the published FS = 1.20. Here it is only the
    vehicle: what is being tested is whether the command line applies the
    model at all, so the grid is coarse on purpose.

    Morgenstern, N. (1963). "Stability charts for earth slopes during
    rapid drawdown". Géotechnique 13(2), 121-131.
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
        polyline=Polyline(vertices=[Vertex(-5, 100), Vertex(378, 100)]),
        btype=BoundaryType.WATER_TABLE))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, 0), Vertex(378, 0)]),
        btype=BoundaryType.DRAWDOWN))
    m = Material(
        name="Slope", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=312.0, friction_angle=30.0),
        pore_pressure=PorePressureType.WATER_TABLE)
    m.undrained_behaviour = True
    m.b_bar = b_bar
    p.materials = [m]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    p.settings.groundwater.set_advanced_option("rapid_drawdown")
    p.settings.groundwater.rapid_drawdown_method = "b_bar"
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    # One centre, one radius: a fixed surface, so the two entry points are
    # compared on the same circle rather than on whatever each search
    # happens to find.
    p.settings.search.grid_x_min = 60.0
    p.settings.search.grid_x_max = 60.0
    p.settings.search.grid_y_min = 380.0
    p.settings.search.grid_y_max = 380.0
    p.settings.search.grid_nx = 2
    p.settings.search.grid_ny = 2
    p.settings.search.radius_increment = 1
    return p


# ======================================================================
# Entry points
# ======================================================================
def _run_cli(args):
    """Invoke the real Typer application. Returns the click Result."""
    from typer.testing import CliRunner
    from ogr_cli.__main__ import app
    return CliRunner().invoke(app, args)


def _cli_fos(tmp_path, project, extra=(), name="p.ogr"):
    """Save ``project``, run ``compute`` on it, read the FS back.

    Deliberately end to end: through ``Project.save``, through the Typer
    command, through ``save_results``, and back out of the HDF5 file.
    Every one of those is part of what a terminal user gets.
    """
    from ogr_core.project import load_summary

    path = Path(tmp_path) / name
    project.save(path)
    out = Path(tmp_path) / "r.h5"
    res = _run_cli(["compute", str(path), "--output", str(out), *extra])
    assert res.exit_code == 0, res.output
    summary = load_summary(out)
    fos = [f for f in summary["fos_array"] if f > 0 and math.isfinite(f)]
    return (min(fos) if fos else None), res


def _gui_fos(project, method_ids=None):
    """The same analysis through the interface's compute worker."""
    from ogr_gui.main_window import _ComputeWorker

    worker = _ComputeWorker(project, method_ids or ["bishop_simplified"])
    errors = []
    worker.failed.connect(errors.append)
    worker.run()
    assert not errors, errors
    result = next(iter(worker.results.values()))
    return result.critical.fos if result.critical else None


# ======================================================================
class TestRapidDrawdownReachesTheCommandLine:
    """The pending item of v0.1.72, v0.1.74 and v0.1.75."""

    def test_the_command_line_applies_the_drawdown(self, tmp_path):
        """A terminal run must not report the pre-drawdown factor.

        The failure this replaces was silent: the same command printed a
        higher, ordinary factor of safety and said nothing about the
        rapid drawdown it had been asked for.
        """
        p = _morgenstern_drawdown()
        drawn, _ = _cli_fos(tmp_path, p)

        ordinary = _morgenstern_drawdown()
        ordinary.settings.groundwater.rapid_drawdown = False
        plain, _ = _cli_fos(tmp_path, ordinary, name="q.ogr")

        assert drawn is not None and plain is not None
        assert abs(drawn - plain) > 1e-3, (
            f"the drawdown changed nothing: {drawn} vs {plain} — the "
            f"command line is reporting the ordinary factor of safety")

    def test_both_entry_points_agree_on_the_drawdown_number(self, tmp_path):
        """Same project, same circle, same number, either way in."""
        cli, _ = _cli_fos(tmp_path, _morgenstern_drawdown())
        gui = _gui_fos(_morgenstern_drawdown())
        assert cli is not None and gui is not None
        assert abs(cli - gui) < 1e-6, (cli, gui)

    def test_a_drawdown_it_cannot_run_is_refused(self, tmp_path):
        """Rapid drawdown needs water surfaces, so r_u must be rejected.

        Refusing beats computing: an analysis that quietly ignores the
        groundwater method the user chose looks exactly like a successful
        one.
        """
        from ogr_core.materials import PorePressureType

        p = _morgenstern_drawdown()
        p.settings.groundwater.method = "ru"
        p.materials[0].pore_pressure = PorePressureType.RU_COEFFICIENT
        p.materials[0].ru = 0.5
        path = Path(tmp_path) / "ru.ogr"
        p.save(path)
        res = _run_cli(["compute", str(path)])
        assert res.exit_code == 3, res.output
        assert "water surfaces" in res.output.lower(), res.output


# ======================================================================
class TestProjectSettingsReachTheCommandLine:
    """One test per control that the CLI used to ignore."""

    def test_the_design_standard_is_applied(self, tmp_path):
        """Partial factors must reduce c' and tan φ' before the analysis.

        Eurocode 7 factors the INPUTS, so the omission did not merely
        report a different number: it reported a factor of safety where
        the user had asked for an over-design factor.
        """
        plain, _ = _cli_fos(tmp_path, _small_slope(), name="a.ogr")

        p = _small_slope()
        ds = p.settings.design_standard
        ds.enabled = True
        ds.standard = "eurocode7_da1c2"
        ds.factor_cohesion = 1.25
        ds.factor_friction = 1.25
        factored, res = _cli_fos(tmp_path, p, name="b.ogr")

        assert plain is not None and factored is not None
        assert factored < plain - 1e-6, (
            f"the partial factors changed nothing: {factored} vs {plain}")
        assert "over-design factor" in res.output.lower(), res.output

    def test_the_users_file_is_not_modified_by_a_calculation(self, tmp_path):
        """The factored project must be a copy, on this path too."""
        p = _small_slope()
        p.settings.design_standard.enabled = True
        p.settings.design_standard.standard = "eurocode7_da1c2"
        p.settings.design_standard.factor_cohesion = 1.25
        p.settings.design_standard.factor_friction = 1.25
        path = Path(tmp_path) / "keep.ogr"
        p.save(path)
        before = path.read_text(encoding="utf-8")
        _run_cli(["compute", str(path), "--output",
                  str(Path(tmp_path) / "k.h5")])
        assert path.read_text(encoding="utf-8") == before

    def test_the_search_strategy_comes_from_the_project(self, tmp_path):
        """Four of the six strategies used to be unreachable by CLI."""
        grid, _ = _cli_fos(tmp_path, _small_slope(), name="g.ogr")

        p = _small_slope()
        p.settings.search.search_method = "block"
        p.settings.search.block_num_surfaces = 40
        block, _ = _cli_fos(tmp_path, p, name="bl.ogr")

        assert grid is not None and block is not None
        assert abs(grid - block) > 1e-6, (
            "grid and block search returned the same number, so the "
            "project's search_method was almost certainly ignored")

    def test_the_radius_increment_comes_from_the_project(self, tmp_path):
        """``radius_increment`` is a COUNT of intervals, not a length.

        The old CLI defaulted it to 1.5, which rounds to 2 intervals — 3
        radii per centre — while a project asking for 10 wants 11. The
        number of evaluated surfaces is the visible consequence.
        """
        from ogr_core.project import load_summary

        counts = {}
        for dr in (2, 10):
            p = _small_slope()
            p.settings.search.radius_increment = dr
            path = Path(tmp_path) / f"dr{dr}.ogr"
            p.save(path)
            out = Path(tmp_path) / f"dr{dr}.h5"
            res = _run_cli(["compute", str(path), "--output", str(out)])
            assert res.exit_code == 0, res.output
            counts[dr] = len(load_summary(out)["fos_array"])
        assert counts[10] > counts[2], counts

    def test_the_slice_count_comes_from_the_project(self, tmp_path):
        """25 slices in the project must not become the CLI's old 30."""
        coarse = _small_slope()
        coarse.settings.methods.num_slices = 6
        a, _ = _cli_fos(tmp_path, coarse, name="c6.ogr")

        fine = _small_slope()
        fine.settings.methods.num_slices = 60
        b, _ = _cli_fos(tmp_path, fine, name="c60.ogr")

        assert a is not None and b is not None
        assert abs(a - b) > 1e-6, (a, b)

    def test_an_option_still_overrides_the_project(self, tmp_path):
        """The project decides; a flag written on purpose still wins."""
        p = _small_slope()
        p.settings.methods.num_slices = 6
        default, _ = _cli_fos(tmp_path, p, name="o1.ogr")
        overridden, _ = _cli_fos(tmp_path, _small_slope(),
                                 extra=["--slices", "60"], name="o2.ogr")
        assert default is not None and overridden is not None
        assert abs(default - overridden) > 1e-6, (default, overridden)

    def test_a_random_search_is_reproducible(self, tmp_path):
        """The Random Numbers page promises exactly this."""
        p = _small_slope()
        p.settings.search.search_method = "slope"
        p.settings.search.num_surfaces = 40
        p.settings.random_numbers.seed = 12345
        p.settings.statistics.seed = 12345
        first, _ = _cli_fos(tmp_path, p, name="s1.ogr")
        second, _ = _cli_fos(tmp_path, p, name="s2.ogr")
        assert first is not None and second is not None
        assert first == second, (first, second)


# ======================================================================
class TestTheSeepageFieldIsNotSilentlyZero:
    """The field is not serialised, and u = 0 looks like a dry slope."""

    def test_a_fem_project_without_a_field_is_refused(self, tmp_path):
        from ogr_core.materials import PorePressureType

        p = _small_slope()
        p.materials[0].pore_pressure = PorePressureType.FEM_SEEPAGE
        path = Path(tmp_path) / "fem.ogr"
        p.save(path)
        res = _run_cli(["compute", str(path)])
        assert res.exit_code == 3, res.output
        assert "seepage" in res.output.lower(), res.output

    def test_the_same_guard_protects_the_interface(self):
        """This is not a CLI-only hole: a reopened FEM project loses the
        field in the interface too, and computed a dry slope."""
        from ogr_core.materials import PorePressureType
        from ogr_slip2d.analysis_runner import check_analysis_settings

        p = _small_slope()
        assert check_analysis_settings(p) == []
        p.materials[0].pore_pressure = PorePressureType.FEM_SEEPAGE
        problems = check_analysis_settings(p)
        assert problems and "seepage" in problems[0].lower()


# ======================================================================
class TestEveryRegisteredMethodIsReachable:
    """Seven methods are registered; the entry points reached 5 and 4."""

    def test_the_command_line_accepts_all_seven(self, tmp_path):
        from ogr_slip2d import method_registry

        p = _small_slope()
        path = Path(tmp_path) / "m.ogr"
        p.save(path)
        for mid in method_registry():
            res = _run_cli(["compute", str(path), "--method", mid,
                            "--output", str(Path(tmp_path) / f"{mid}.h5")])
            assert res.exit_code == 0, f"{mid}: {res.output}"

    def test_janbu_corrected_produces_a_result(self):
        """Regression: it was tickable in Project Settings and produced
        nothing at all, because the interface's hand-written method table
        had no entry for it and an unknown id was a bare ``continue``."""
        from ogr_slip2d.analysis_runner import run_analysis

        out = run_analysis(_small_slope(), ["janbu_corrected"])
        assert "janbu_corrected" in out.results
        assert out.results["janbu_corrected"].critical is not None

    def test_an_unrunnable_method_leaves_a_trace(self):
        """Vanishing from the results with no message is what rule 7
        forbids; a warning is the minimum."""
        from ogr_slip2d.analysis_runner import run_analysis

        out = run_analysis(_small_slope(), ["not_a_method"])
        assert out.results == {}
        assert any("not_a_method" in w for w in out.warnings), out.warnings

    def test_an_unknown_method_on_the_command_line_is_rejected(self, tmp_path):
        p = _small_slope()
        path = Path(tmp_path) / "u.ogr"
        p.save(path)
        res = _run_cli(["compute", str(path), "--method", "nope"])
        assert res.exit_code == 2, res.output


# ======================================================================
class TestTheTwoEntryPointsAgree:
    def test_the_same_project_gives_the_same_number(self, tmp_path):
        """The claim the CLI docstring had been making since v0.1.59."""
        cli, _ = _cli_fos(tmp_path, _small_slope())
        gui = _gui_fos(_small_slope())
        assert cli is not None and gui is not None
        assert abs(cli - gui) < 1e-9, (cli, gui)

    def test_every_search_strategy_runs_from_both(self):
        """Slope Search raised a TypeError on the interface path for
        every release up to v0.1.76: it was the only search that did not
        accept the admissibility arguments the worker passes to all of
        them, and the blanket ``except Exception`` turned that into a
        generic error dialog with no results."""
        from ogr_slip2d.analysis_runner import run_analysis

        for strategy in ("grid", "slope", "auto_refine", "block", "path",
                         "simulated_annealing"):
            p = _small_slope()
            p.settings.search.search_method = strategy
            p.settings.search.num_surfaces = 30
            p.settings.search.block_num_surfaces = 30
            p.settings.search.path_num_paths = 30
            out = run_analysis(p, ["bishop_simplified"])
            assert "bishop_simplified" in out.results, strategy

    def test_slope_search_accepts_the_admissibility_settings(self):
        """The exact call that used to raise."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch

        s = SlopeSearch(method=BishopSimplified(), num_slices=25,
                        reject_tensile=True, tensile_percent=90.0,
                        check_m_alpha=True)
        assert s.reject_tensile is True
        assert s.check_m_alpha is True
        assert s.tensile_percent == 90.0


# ======================================================================
class TestTheCommandsThatDoNotCompute:
    """Nobody tests these, so nobody noticed one of them was broken."""

    def test_methods_lists_every_registered_method(self):
        """It crashed on a Windows console before v0.1.77.

        The ✓ and — in the table are not encodable in cp1252, which is
        what Python selects there, so ``ogr-slip2d-cli methods`` printed
        a traceback instead of a list — on the author's own platform,
        for every release. ``tests/_runner.py`` had already hit and
        documented the identical trap.
        """
        from ogr_slip2d import method_registry

        res = _run_cli(["methods"])
        assert res.exit_code == 0, res.output
        for mid in method_registry():
            assert mid in res.output, mid

    def test_strength_models_runs(self):
        res = _run_cli(["strength-models"])
        assert res.exit_code == 0, res.output

    def test_new_demo_writes_a_loadable_project(self, tmp_path):
        from ogr_core.project import Project

        path = Path(tmp_path) / "demo.ogr"
        res = _run_cli(["new-demo", str(path)])
        assert res.exit_code == 0, res.output
        assert Project.load(path).materials

    def test_info_runs_on_that_project(self, tmp_path):
        path = Path(tmp_path) / "demo.ogr"
        _run_cli(["new-demo", str(path)])
        res = _run_cli(["info", str(path)])
        assert res.exit_code == 0, res.output

    def test_a_missing_file_is_reported_not_crashed(self, tmp_path):
        res = _run_cli(["compute", str(Path(tmp_path) / "nope.ogr")])
        assert res.exit_code == 1, res.output


# ======================================================================
class TestSettingsThatCannotBeHonouredAreReported:
    def test_slope_search_says_it_ignores_the_slope_limits(self):
        """``SlopeSearch.run`` derives its own entry/exit window from the
        ground profile and reads no user limit. Saying so beats accepting
        an argument that changes nothing."""
        from ogr_slip2d.analysis_runner import settings_warnings

        p = _small_slope()
        p.settings.search.search_method = "slope"
        assert settings_warnings(p) == []
        p.settings.search.slope_limit_left = 5.0
        p.settings.search.slope_limit_right = 40.0
        notes = settings_warnings(p)
        assert notes and "slope limits" in notes[0].lower()

    def test_grid_search_does_not_warn(self):
        """Grid Search does read them, so there is nothing to say."""
        from ogr_slip2d.analysis_runner import settings_warnings

        p = _small_slope()
        p.settings.search.slope_limit_left = 5.0
        p.settings.search.slope_limit_right = 40.0
        assert settings_warnings(p) == []
