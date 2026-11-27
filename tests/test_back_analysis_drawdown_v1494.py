# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""A back analysis under a rapid drawdown reads its supports at the level its
slices were computed at (v0.1.494, D432).

THE INVARIANT THIS FILE PROTECTS is that the model a back analysis hands to
the supports is the model of the slices it prices. Every drawdown procedure
publishes the slices of its drawn-down stage, computed with the supports read
on ``level_project(project, use_drawdown=True)``; until this version both
doors of the back analysis -- the run (``run_back_analysis``) and the window
(``required_force_of_result``) -- read them on the project at its INITIAL
level. A support whose capacity comes from the soil reads the effective
vertical stress, and with it the water, so it carried another force.

THE REFERENCE IS AN IDENTITY, not a snapshot (Bishop 1955; Janbu 1954; the
identity of v0.1.220, D210): at a surface's own factor of safety, with the
data it was computed with, the support force is zero. Measured UNCLIPPED --
``required_force`` reports a negative force as 0 -- to 1e-9 of the weight of
the mass, on models solved to 1e-12.

The model is the Pilarcitos embankment of ``test_rapid_drawdown_v168``
(level 72 -> 37, phi' = 45, R envelope c_r = 60, phi_r = 23) with a
geosynthetic in coefficient mode (Jewell 1996; 0.8, a tensile capacity of 1e8
so that the bond governs) at elevation 50, between the two levels. Measured
on 0.1.493: the identity is +0.173 of the weight with the model as drawn and
0 with the drawn-down one, under Duncan-Wright-Wong, Lowe-Karafiath, Corps 2
and B-bar, Janbu and Bishop alike. Without the sheet, or with it limited by
its tensile capacity (which reads no water), both models give 0: the defect
is only in what a support reads of the soil.

Cost: the fixed circle by the window's function under four procedures and
two methods, about a second; one grid run of nine circles per method by the
run's door, and one main-window-free Interpret window per method.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from types import SimpleNamespace as NS

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_TOL_W = 1e-9
_ELEV = 50.0
_METHODS = ("janbu_simplified", "bishop_simplified")
_PROCEDURES = ("duncan_wright", "lowe_karafiath", "corps_2", "b_bar")


def _pilarcitos(sheet="bond", procedure="duncan_wright"):
    """The embankment, solved to 1e-12, with a sheet whose capacity is its
    bond (``"bond"``), its tensile capacity (``"tension"``) or no sheet."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.materials.drawdown_envelopes import REnvelope
    from ogr_core.project import Project
    from ogr_core.support import Geosynthetic, SupportInstance
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(260, 0), Vertex(260, 78),
                             Vertex(205, 78), Vertex(145, 58)], closed=True)
    ext.ensure_ccw()
    p = Project("Pilarcitos")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(-5, 72), Vertex(265, 72)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(-5, 37), Vertex(265, 37)], closed=False),
        btype=BoundaryType.DRAWDOWN))
    m = Material(name="Embankment", unit_weight=135.0, sat_unit_weight=135.0,
                 strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0),
                 pore_pressure=PorePressureType.WATER_TABLE)
    m.undrained_behaviour = True
    m.drawdown_envelope = REnvelope(c_r=60.0, phi_r_deg=23.0)
    # B-bar's pore-pressure parameter; with 0 the fixed circle has no
    # physical factor under B-bar, with 1 it has one
    m.b_bar = 1.0
    p.materials = [m]
    gw = p.settings.groundwater
    gw.pore_fluid_unit_weight = 62.4
    gw.set_advanced_option("rapid_drawdown")
    gw.rapid_drawdown_method = procedure
    p.settings.methods.tolerance = 1e-12
    p.settings.methods.max_iterations = 400
    p.settings.methods.num_slices = 25
    if sheet is not None:
        capacity = 1.0e8 if sheet == "bond" else 5000.0
        p.support_types = [Geosynthetic(tensile_capacity=capacity,
                                        pullout_mode="coefficient",
                                        coefficient_of_interaction=0.8)]
        p.supports = [SupportInstance(type_id="geosynthetic",
                                      head=Vertex(125.0, 50.0),
                                      tail=Vertex(185.0, 50.0))]
    return p


def _fixed_circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=100.0, centre_y=200.0, radius=160.0)


def _solved(p, surface, mid):
    """The surface solved as the program solves it: ``evaluate_surfaces``,
    the door of one surface (the factored copy, the method wrapped for the
    drawdown, the project's tolerance)."""
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    res = evaluate_surfaces(p, surface, [mid]).results[mid]
    assert res is not None and res.is_valid, (mid, surface)
    return res


def _unclipped(slices, surface, fos, mid, project):
    """The passive force at ``fos`` WITHOUT the clip to zero, over the
    weight of the mass."""
    import ogr_slip2d.back_analysis as BA
    sl = list(getattr(slices, "slices", slices))
    resisting, driving, arm = BA._sums_at_fixed_fos(
        sl, surface, fos, 0.0, 0.0, _ELEV, mid, stress_fos=fos,
        project=project)
    return (fos * driving - resisting) / arm / sum(s.weight for s in sl)


def _crosses_sheet(surface):
    """Whether the circle crosses the sheet: its exit through elevation 50
    falls between the two ends of the sheet, x = 125 and 185."""
    import math
    dy = surface.centre_y - _ELEV
    if not surface.radius > abs(dy):
        return False
    x = surface.centre_x + math.sqrt(surface.radius ** 2 - dy ** 2)
    return 125.0 < x < 185.0


@contextmanager
def _spied():
    """Every call to ``required_force``, with what it was handed."""
    import ogr_slip2d.back_analysis as BA
    calls = []
    real = BA.required_force

    def spy(slices, surface, target_fos, method_id="bishop_simplified",
            elevation=0.0, kh=0.0, kv=0.0, project=None):
        calls.append(NS(slices=slices, surface=surface, project=project,
                        method_id=method_id))
        return real(slices, surface, target_fos, method_id, elevation, kh,
                    kv, project=project)

    BA.required_force = spy
    try:
        yield calls
    finally:
        BA.required_force = real


# ----------------------------------------------------------------------
class TestTheModelOfTheSlices:

    def test_the_drawn_down_model_under_a_drawdown_and_the_same_without(self):
        from ogr_core.geometry import BoundaryType
        from ogr_slip2d.back_analysis import model_of_slices
        p = _pilarcitos()
        m = model_of_slices(p)
        assert m is not p
        levels = {b.polyline.vertices[0].y for b in m.boundaries
                  if b.btype == BoundaryType.WATER_TABLE}
        assert levels == {37.0}, levels
        # the project handed over is not touched
        assert {b.polyline.vertices[0].y for b in p.boundaries
                if b.btype == BoundaryType.WATER_TABLE} == {72.0}
        p.settings.groundwater.set_advanced_option("none")
        assert not p.settings.groundwater.rapid_drawdown
        assert model_of_slices(p) is p


class TestTheIdentityByTheWindowsFunction:
    """``required_force_of_result``, which Interpret calls, on the fixed
    circle of the ficha under the four procedures."""

    def test_zero_at_its_own_factor_under_every_procedure(self):
        from ogr_core.project import prepare_analysis_project
        c = _fixed_circle()
        for procedure in _PROCEDURES:
            p = _pilarcitos(procedure=procedure)
            factored, _report = prepare_analysis_project(p)
            for mid in _METHODS:
                res = _solved(p, c, mid)
                with _spied() as calls:
                    import ogr_slip2d.back_analysis as BA
                    BA.required_force_of_result(res, res.fos, _ELEV,
                                                factored)
                call, = calls
                got = _unclipped(res.slices, c, res.fos, mid, call.project)
                assert abs(got) <= _TOL_W, (procedure, mid, got)
                # and the case is the one it claims to be: read as drawn,
                # the sheet carries another force
                drawn = _unclipped(res.slices, c, res.fos, mid, factored)
                assert drawn > 0.1, (procedure, mid, drawn)

    def test_supports_that_read_no_water_and_no_support_do_not_move(self):
        """The control of the ficha: with no sheet, or with it limited by
        its tensile capacity, the two models price alike."""
        from ogr_core.project import prepare_analysis_project
        from ogr_slip2d.back_analysis import model_of_slices
        c = _fixed_circle()
        for sheet in (None, "tension"):
            p = _pilarcitos(sheet)
            factored, _report = prepare_analysis_project(p)
            for mid in _METHODS:
                res = _solved(p, c, mid)
                a = _unclipped(res.slices, c, res.fos, mid, factored)
                b = _unclipped(res.slices, c, res.fos, mid,
                               model_of_slices(factored))
                assert abs(a) <= _TOL_W and abs(b) <= _TOL_W, (sheet, mid,
                                                               a, b)


class TestTheIdentityThroughTheRun:
    """``run_configured_back_analysis`` over a small grid around the fixed
    circle: every surface it prices, priced on the model of its slices."""

    def test_zero_at_each_surfaces_own_factor(self):
        p = _pilarcitos()
        s = p.settings.search
        s.search_method, s.surface_type = "grid", "circular"
        s.grid_x_min, s.grid_x_max = 90.0, 110.0
        s.grid_y_min, s.grid_y_max = 190.0, 210.0
        s.grid_nx = s.grid_ny = 2
        s.radius_increment = 3
        p.settings.advanced.parallel_search = False
        from ogr_core.project import prepare_analysis_project
        from ogr_slip2d.analysis_runner import run_configured_back_analysis
        factored, _report = prepare_analysis_project(p)
        for mid in _METHODS:
            with _spied() as calls:
                out, _rep, _w = run_configured_back_analysis(
                    p, target_fos=3.5, elevation=_ELEV, method_id=mid)
            assert out.notes.get("error") is None, out.notes
            # the circles the sheet crosses: the deeper ones pass under it
            crossing = [c for c in calls if _crosses_sheet(c.surface)]
            assert len(crossing) >= 2, len(crossing)
            checked = 0
            for call in crossing[:3]:
                res = _solved(p, call.surface, mid)
                got = _unclipped(res.slices, call.surface, res.fos, mid,
                                 call.project)
                assert abs(got) <= _TOL_W, (mid, call.surface, got)
                drawn = _unclipped(res.slices, call.surface, res.fos, mid,
                                   factored)
                # 0.03 to 0.06 of the weight on these circles (0.1.493)
                checked += drawn > 1e-3
            assert checked == len(crossing[:3]), checked


class TestTheIdentityThroughTheWindow:
    """Interpret's back analysis on the critical surface of a result, with
    its two inputs answered (the ``_ask`` of
    ``test_interpret_back_analysis_v1440``). The result holds the fixed
    circle alone, solved by the door of one surface: the critical surface of
    a grid around it passes under the sheet, and what is tested is what the
    window hands over, whatever produced the result."""

    def test_zero_at_the_critical_surfaces_own_factor(self):
        from test_interpret_back_analysis_v1440 import _app, _ask, _language
        from ogr_core.project import prepare_analysis_project
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d.search import SearchResult
        p = _pilarcitos()
        factored, _report = prepare_analysis_project(p)
        _app()
        for mid in _METHODS:
            res = _solved(p, _fixed_circle(), mid)
            run = SearchResult(method_id=mid, evaluations=[res],
                               valid_count=1)
            c = run.critical
            assert c is res
            w = InterpretWindow(p, {mid: run}, None)
            try:
                with _language("en"):
                    got = _ask(w, c.fos, _ELEV)
            finally:
                w.close()
            call, = got.calls
            sl = list(getattr(c.slices, "slices", c.slices))
            passive = _unclipped(sl, c.surface, c.fos, mid, call.project)
            assert abs(passive) <= _TOL_W, (mid, passive)
            drawn = _unclipped(sl, c.surface, c.fos, mid, factored)
            assert drawn > 0.1, (mid, drawn)
