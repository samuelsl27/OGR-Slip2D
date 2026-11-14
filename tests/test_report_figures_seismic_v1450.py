# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D423 (v0.1.450) — the figure of a seismic run marks the minimum of what it
draws.

The invariant
-------------
The report's figure contours, at each slip centre of a grid, the run's own
number, and its star «critical centre» is the centre of the critical
surface. On a run of factors that number is the lowest factor of the centre
and the star sits on the lowest of them (``test_report_figures_v1339``). On
a "Compute Ky" or a Newmark run the critical surface is the one with the
lowest Ky, and the figure still contoured the lowest FACTOR of each centre:
the star stood on no minimum of what was drawn (measured with 0.1.435 and
0.1.449 on the demo slope with c = 20 kPa and a 5x5x6 grid: the star at (40,
45), the lowest contoured factor at (34, 29)). By the owner's decision (a),
the figure now draws what the run minimises
(``ogr_slip2d.interpretation.critical_per_centre``):

* on a Ky run, the lowest Ky of each centre, under the scale «minimum Ky»;
* on a Newmark run, the largest Newmark displacement of each centre, in the
  project's unit and with the colour map reversed, so that red is still the
  critical end, under «maximum Newmark displacement [cm]»;
* on a run of factors, what it always drew, byte for byte.

Interpret's map of centres, Minimum Surfaces on the canvas and the API's
``minimum_per_centre`` view still read the factor: they are D438.

The reference (rule 1)
----------------------
An identity, as v1339's: what is contoured is recounted here from the
run's valid surfaces, centre by centre, without the code under test; its
minimum is the critical surface's Ky, and the star is on that surface's
centre. On a Newmark run, the largest displacement of each centre is
recounted the same way, and its maximum is the critical surface's
displacement: for a rigid block the displacement does not grow with the Ky
(Newmark 1965), so the surface of the lowest Ky is the one that moves the
most (not with upslope sliding allowed, D437; this run does not allow it).

The case, shared in the file: the demo slope with c = 20 kPa and without a
standard, a 3x3x6 grid (112 circles), Bishop: with Ky the star is at (40,
45) and the lowest factor at (40, 38.33). Not the 3x3x2 grid the plan named:
on it the lowest factor and the lowest Ky of each centre are the same
surface at every centre, and no centre has two displacements, so a mutant
that drew the factor's surface, or the smallest displacement, survived
(measured: 0 centres of 12; on 3x3x6, 1 and 1; 4x4x4 put the star on the
lowest factor). The premises below check that the case still tells them
apart. Measured cost: about 3 s, three runs of 112 circles computed once
and a dozen small figures.
"""
from __future__ import annotations

import contextlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_METHOD = "bishop_simplified"
_RUNS: dict = {}


#: ``mode`` -> (cohesion in kPa, seismic mode, amplitude of the sinusoid in
#: g). A sinusoid of 2 Hz for 4 s. "newmark" at 0.6 g, not the 0.3 g of
#: D408: on this grid 0.3 g moves one centre of twelve, and a mutant that
#: read the displacement of each centre's lowest factor survived (review of
#: 0.1.450); 0.6 g moves seven, and at one of them the surface of the lowest
#: factor is not the one that moves the most. "still": a record that moves
#: nothing. "few": strong enough that only two centres have a Ky.
_MODES = {"fos": (20.0, None, 0.0), "ky": (20.0, "ky", 0.3),
          "newmark": (20.0, "newmark", 0.6),
          "still": (20.0, "newmark", 0.01), "few": (72.0, "ky", 0.3)}


def _run(mode):
    """``(project, results)`` of the demo slope, a 3x3x6 grid and Bishop, in
    ``mode`` (``_MODES``)."""
    if mode not in _RUNS:
        from examples.quick_slope import build_demo_slope
        from ogr_core.loads.seismic_record import SeismicRecord
        from ogr_slip2d.analysis_runner import run_analysis
        cohesion, seismic, amplitude = _MODES[mode]
        p = build_demo_slope()
        p.materials[0].strength.params["cohesion"] = cohesion
        s = p.settings.search
        s.grid_nx, s.grid_ny, s.radius_increment = 3, 3, 6
        p.settings.methods.enabled_methods = [_METHOD]
        if seismic:
            rec = SeismicRecord(name="sine", dt=0.01, accelerations=[
                amplitude * math.sin(2 * math.pi * 2 * i * 0.01)
                for i in range(400)])
            p.seismic_records = [rec]
            cfg = p.settings.seismic
            cfg.compute_ky = seismic == "ky"
            cfg.newmark = seismic == "newmark"
            cfg.record_id = rec.id
        _RUNS[mode] = (p, run_analysis(p).results)
    return _RUNS[mode]


def _per_centre(sr, value, larger=False) -> dict:
    """``{centre: value}``, the lowest (or largest) ``value(r)`` of the valid
    surfaces of each slip centre, those without one left out: the recount,
    by the run's surfaces and not by the code under test."""
    from ogr_slip2d.interpretation import slip_centre
    out: dict = {}
    for r in sr.valid():
        c = slip_centre(r.surface.to_dict())
        v = value(r)
        if c is None or v is None or not math.isfinite(v):
            continue
        if c not in out or (v > out[c] if larger else v < out[c]):
            out[c] = v
    return out


def _drawn(grid) -> list:
    """What the figure contours, under whichever key the grid carries it:
    the run's own number (``values``) or, before 0.1.450, the factor."""
    return grid["values"] if "values" in grid else grid["fos"]


def _ky(r):
    return (r.details or {}).get("ky")


def _cm(r):
    d = (r.details or {}).get("newmark_displacement")
    return None if d is None else 100.0 * d


def _centre_of(r):
    s = r.surface
    return (s.centre_x, s.centre_y)


@contextlib.contextmanager
def _spy(cls, name, record):
    original = getattr(cls, name)

    def wrapper(self, *a, **k):
        record.append((self, a, k))
        return original(self, *a, **k)
    setattr(cls, name, wrapper)
    try:
        yield record
    finally:
        setattr(cls, name, original)


# --- what 0.1.449 (8b3ce6d) had, copied for the byte-for-byte control --
def _grid_data_0449(search_result, project=None):
    from ogr_slip2d.interpretation import minimum_per_centre, slip_centre
    xs, ys, fos = [], [], []
    for r in minimum_per_centre(search_result):
        centre = slip_centre(r.surface.to_dict())
        if centre is None or r.fos is None:
            continue
        xs.append(float(centre[0]))
        ys.append(float(centre[1]))
        fos.append(float(r.fos))
    if len(xs) < 3:
        return None
    crit = getattr(search_result, "critical", None)
    critical = (slip_centre(crit.surface.to_dict())
                if crit is not None else None)
    return {"x": xs, "y": ys, "fos": fos, "critical": critical}


def _draw_grid_0449(fig, ax, grid) -> None:
    xs, ys, fos = grid["x"], grid["y"], grid["fos"]
    try:
        from matplotlib.tri import Triangulation
        tri = Triangulation(xs, ys)
        cs = ax.tricontourf(tri, fos, levels=12, cmap="RdYlBu", alpha=0.85,
                            zorder=3)
        fig.colorbar(cs, ax=ax, shrink=0.8,
                     label=grid.get("label", "minimum factor of safety"))
    except Exception:  # noqa: BLE001
        pass
    ax.plot(xs, ys, ".", color="#333333", markersize=2, zorder=4)
    crit = grid.get("critical")
    if crit is not None:
        ax.plot([crit[0]], [crit[1]], "*", color="#000000", markersize=11,
                zorder=10, label=grid.get("critical_label",
                                          "critical centre"))


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


# ======================================================================
class TestAKyRun:

    def test_the_premise_the_star_is_not_on_the_lowest_factor(self):
        _p, results = _run("ky")
        sr = results[_METHOD]
        lowest = _per_centre(sr, lambda r: r.fos)
        at = min(lowest, key=lowest.get)
        assert _centre_of(sr.critical) != at, (_centre_of(sr.critical), at)

    def test_the_premise_the_case_tells_the_rules_apart(self):
        """At some centre the surface of the lowest factor is not the one of
        the lowest Ky, and some centre has two different displacements."""
        from ogr_slip2d.interpretation import slip_centre
        by: dict = {}
        _p, results = _run("ky")
        for r in results[_METHOD].valid():
            by.setdefault(slip_centre(r.surface.to_dict()), []).append(r)
        apart = 0
        for rs in by.values():
            with_ky = [r for r in rs if _ky(r) is not None
                       and math.isfinite(_ky(r))]
            if with_ky and min(rs, key=lambda r: r.fos) is not min(
                    with_ky, key=_ky):
                apart += 1
        assert apart >= 1, apart
        _p, moved = _run("newmark")
        by = {}
        for r in moved[_METHOD].valid():
            by.setdefault(slip_centre(r.surface.to_dict()), []).append(r)
        counts = {c: {_cm(r) for r in rs if _cm(r) is not None}
                  for c, rs in by.items()}
        assert any(len(v) >= 2 for v in counts.values()), counts
        # and on the Newmark run, at some centre the surface of the lowest
        # factor is not the one that moves the most
        assert any(v and _cm(min(by[c], key=lambda r: r.fos)) != max(v)
                   for c, v in counts.items()), counts

    def test_it_contours_the_lowest_ky_of_each_centre(self):
        from ogr_api.report_figures import grid_data
        p, results = _run("ky")
        sr = results[_METHOD]
        grid = grid_data(sr)
        drawn = dict(zip(zip(grid["x"], grid["y"]), _drawn(grid)))
        assert drawn == _per_centre(sr, _ky), drawn
        assert grid["quantity"] == "ky" and "fos" not in grid
        assert len(drawn) >= 3

    def test_its_minimum_is_the_critical_ky_and_the_star_sits_on_it(self):
        from ogr_api.report_figures import grid_data
        p, results = _run("ky")
        sr = results[_METHOD]
        grid = grid_data(sr)
        assert min(_drawn(grid)) == sr.critical.details["ky"]
        assert grid["critical"] == _centre_of(sr.critical)
        at = dict(zip(zip(grid["x"], grid["y"]), _drawn(grid)))
        assert at[grid["critical"]] == min(_drawn(grid))

    def test_the_picture_draws_those_values_and_the_scale_names_them(self):
        from matplotlib.axes import Axes
        from matplotlib.figure import Figure

        from ogr_api.report_figures import grid_data, method_figures
        p, results = _run("ky")
        grid = grid_data(results[_METHOD])
        contours, bars = [], []
        with _spy(Axes, "tricontourf", contours), \
                _spy(Figure, "colorbar", bars):
            method_figures(p, results, width=300, height=200)
        (_ax, a, k), = contours
        assert list(a[1]) == _drawn(grid)
        assert k["cmap"] == "RdYlBu"           # low Ky, the critical, red
        assert bars[0][2]["label"] == "minimum Ky"


class TestANewmarkRun:

    def test_it_contours_the_largest_displacement_of_each_centre(self):
        from ogr_api.report_figures import grid_data
        p, results = _run("newmark")
        sr = results[_METHOD]
        grid = grid_data(sr)
        drawn = dict(zip(zip(grid["x"], grid["y"]), _drawn(grid)))
        want = _per_centre(sr, _cm, larger=True)
        assert drawn.keys() == want.keys()
        assert all(abs(drawn[c] - want[c]) <= 1e-12 * max(1.0, want[c])
                   for c in want), (drawn, want)
        assert grid["quantity"] == "newmark" and grid["unit"] == "cm"

    def test_its_maximum_is_the_critical_displacement_and_the_star_on_it(self):
        from ogr_api.report_figures import grid_data
        p, results = _run("newmark")
        sr = results[_METHOD]
        grid = grid_data(sr)
        assert abs(max(_drawn(grid)) - _cm(sr.critical)) <= 1e-12
        assert grid["critical"] == _centre_of(sr.critical)

    def test_red_is_still_the_critical_end_and_the_scale_names_it(self):
        from matplotlib.axes import Axes
        from matplotlib.figure import Figure

        from ogr_api.report_figures import method_figures
        p, results = _run("newmark")
        contours, bars = [], []
        with _spy(Axes, "tricontourf", contours), \
                _spy(Figure, "colorbar", bars):
            method_figures(p, results, width=300, height=200)
        assert contours[0][2]["cmap"] == "RdYlBu_r"
        assert bars[0][2]["label"] == "maximum Newmark displacement [cm]"

    def test_in_the_projects_unit(self):
        """The unit is the project's, which ``method_figures`` hands over:
        neither call gained an argument (the window's, the API's)."""
        import ogr_api.render as R
        from ogr_api.report_figures import method_figures
        p, results = _run("newmark")
        sr = results[_METHOD]
        units = p.settings.units
        before = units.system_id
        seen, real = [], R.render_png

        def spy(project, **kw):
            seen.append(kw["grid"])
            return real(project, **kw)
        units.system_id = "imperial_psf"
        R.render_png = spy
        try:
            method_figures(p, results, width=200, height=150)
        finally:
            R.render_png = real
            units.system_id = before
        grid, = seen
        assert grid.get("unit") == "in", grid.get("label")
        assert abs(max(_drawn(grid)) - _cm(sr.critical) / 2.54) <= 1e-9
        assert grid["label"] == "maximum Newmark displacement [in]"


class TestWithoutKyNothingMoves:
    """A run of factors draws what 0.1.449 drew: the dictionary and the
    bytes of the PNG, against the functions of 0.1.449 substituted in the
    same process."""

    def test_the_grid_is_the_one_of_before(self):
        from ogr_api.report_figures import grid_data
        p, results = _run("fos")
        sr = results[_METHOD]
        assert grid_data(sr) == _grid_data_0449(sr)

    def test_the_png_is_the_one_of_before(self):
        import ogr_api.render as R
        import ogr_api.report_figures as RF
        p, results = _run("fos")
        new = RF.method_figures(p, results, width=300, height=200)
        old_grid, old_draw = RF.grid_data, R._draw_grid
        RF.grid_data, R._draw_grid = _grid_data_0449, _draw_grid_0449
        try:
            old = RF.method_figures(p, results, width=300, height=200)
        finally:
            RF.grid_data, R._draw_grid = old_grid, old_draw
        assert [png for _m, png in new] == [png for _m, png in old]


class TestTheWordsOfTheScale:

    def _labels(self, mode):
        import ogr_api.render as R
        from ogr_api.report_figures import method_figures
        from ogr_gui.core_messages import note_text
        p, results = _run(mode)
        seen, real = [], R.render_png

        def spy(project, **kw):
            seen.append(kw)
            return real(project, **kw)
        R.render_png = spy
        try:
            with _Spanish():
                method_figures(p, results, width=200, height=150,
                               translate=note_text)
        finally:
            R.render_png = real
        return [(kw["grid"]["label"], kw["grid"]["critical_label"])
                for kw in seen]

    def test_in_spanish(self):
        assert self._labels("ky") == [("Ky mínimo", "centro crítico")]
        assert self._labels("newmark") == [
            ("desplazamiento de Newmark máximo [cm]", "centro crítico")]
        assert self._labels("fos") == [("factor de seguridad mínimo",
                                        "centro crítico")]


class TestWhatTheReviewFound:
    """The review of 0.1.450 measured five things the first draft did."""

    def test_the_runs_caption_is_asked_once_not_per_surface(self):
        """It reads ``critical``, which walks every surface: asked per
        surface the figure cost 8 s on a grid of 4746 surfaces (0.012 s
        asked once)."""
        import ogr_slip2d.reported as ER
        from ogr_api.report_figures import grid_data
        _p, results = _run("ky")
        sr = results[_METHOD]
        assert len(sr.valid()) > 50            # the premise: many surfaces
        calls, real = [], ER.reported_caption

        def counted(*a, **k):
            calls.append(1)
            return real(*a, **k)
        ER.reported_caption = counted
        try:
            grid_data(sr)
        finally:
            ER.reported_caption = real
        assert len(calls) == 1, len(calls)

    def test_with_two_centres_of_ky_the_grid_and_the_star_stay(self):
        """The search still had a grid: its dots, the star, and the frame of
        the search area offered by the report's dialog (``has_centres``)."""
        from matplotlib.axes import Axes

        from ogr_api.report_figures import grid_data, has_centres, \
            method_figures
        p, results = _run("few")
        sr = results[_METHOD]
        with_ky = _per_centre(sr, _ky)
        assert sr.critical is not None and len(with_ky) < 3, with_ky
        grid = grid_data(sr)
        assert grid is not None and has_centres(results)
        assert len(grid["centres"][0]) == 12, grid["centres"]
        plots = []
        with _spy(Axes, "plot", plots):
            method_figures(p, results, width=200, height=150)
        stars = [a for _ax, a, _k in plots if len(a) == 3 and a[2] == "*"]
        assert stars == [([_centre_of(sr.critical)[0]],
                          [_centre_of(sr.critical)[1]], "*")], stars

    def test_a_slope_the_record_does_not_move_is_not_contoured(self):
        from matplotlib.axes import Axes
        from matplotlib.figure import Figure

        from ogr_api.report_figures import grid_data, method_figures
        p, results = _run("still")
        grid = grid_data(results[_METHOD])
        assert grid is not None and set(_drawn(grid)) == {0.0}, grid
        contours, bars, plots = [], [], []
        with _spy(Axes, "tricontourf", contours), \
                _spy(Figure, "colorbar", bars), _spy(Axes, "plot", plots):
            method_figures(p, results, width=200, height=150)
        assert contours == [] and bars == []
        assert any(len(a) == 3 and a[2] == "*" for _ax, a, _k in plots)

    def test_every_evaluated_centre_has_its_dot(self):
        """A centre none of whose surfaces has a Ky is not contoured, and it
        keeps its dot: the dots say where the search looked."""
        from matplotlib.axes import Axes

        from ogr_api.report_figures import grid_data, method_figures
        from ogr_slip2d.interpretation import slip_centre
        p, results = _run("ky")
        sr = results[_METHOD]
        every = {slip_centre(r.surface.to_dict()) for r in sr.valid()}
        grid = grid_data(sr)
        assert len(grid["x"]) < len(every), "the premise"
        plots = []
        with _spy(Axes, "plot", plots):
            method_figures(p, results, width=200, height=150)
        dots, = [a for _ax, a, _k in plots if len(a) == 3 and a[2] == "."]
        assert set(zip(dots[0], dots[1])) == every

    def test_a_grid_drawn_without_a_label_names_its_number(self):
        from matplotlib.figure import Figure

        from ogr_api.report_figures import grid_data
        from ogr_api.render import render_png
        for mode, want in (("ky", "minimum Ky"),
                           ("newmark", "maximum Newmark displacement [cm]"),
                           ("fos", "minimum factor of safety")):
            p, results = _run(mode)
            sr = results[_METHOD]
            bars = []
            with _spy(Figure, "colorbar", bars):
                render_png(p, surfaces=[("c", sr.critical)], width=200,
                           height=150, grid=grid_data(sr))
            assert bars[0][2]["label"] == want, (mode, bars[0][2])


class TestTheRuleIsTheEngines:

    def test_minimum_per_centre_does_not_move(self):
        """Minimum Surfaces and the API's view read it, by the factor, on a
        Ky run too; they are D438."""
        from ogr_slip2d.interpretation import minimum_per_centre, slip_centre
        _p, results = _run("ky")
        sr = results[_METHOD]
        lowest = _per_centre(sr, lambda r: r.fos)
        got = {}
        for r in minimum_per_centre(sr):
            c = slip_centre(r.surface.to_dict())
            if c is not None:
                got[c] = r.fos
        assert got == lowest

    def test_on_a_run_of_factors_the_rule_is_minimum_per_centre(self):
        from ogr_slip2d.interpretation import (critical_per_centre,
                                               minimum_per_centre)
        _p, fos_results = _run("fos")
        f = fos_results[_METHOD]
        assert [id(r) for r in critical_per_centre(f)] == [
            id(r) for r in minimum_per_centre(f)]
