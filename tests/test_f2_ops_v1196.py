# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.196 (spec 008, F2) — the operations that give an agent loads,
supports, search objects, annotations, files and the geometry transforms.

Invariants protected:

* **Rule 1, against a closed form.** A model built ENTIRELY through the
  operations — geometry, material, a support type and a placed anchor —
  gives the Coulomb wedge (Coulomb 1776; Duncan & Wright 2005 §6) on the
  planes where the engine reaches it, with the closed form of
  ``test_anchored_wedge_root_v1177.py`` imported, not rewritten. That the
  support the operations build is the fixture's own is checked on its own:
  the closed form evaluated on the API's project equals the fixture's to
  the last bit. With a surcharge the engine samples the load once per slice
  at its mid-point and does not put a slice edge at the load's end, so the
  closed form holds within the band that rule allows (half a slice of
  load), which is asserted rather than a tolerance picked to pass.
* **Rule 7, at the door.** Every setting these operations accept moves the
  number the engine computes (orientation, magnitude, distribution, angle,
  kh, the crack's water, the anchor's capacity), and every combination the
  engine would NOT read is refused with the reason instead of being stored
  — a line load normal to the boundary (the engine applies it vertically),
  ``angle_deg`` with a vertical load, ``magnitude_end`` on a constant load,
  a focus tolerance on a window, ``user_angle_deg`` without the user-defined
  orientation. A refused edit leaves the model byte-identical.
* The geometry transforms against their closed forms: a 90° rotation, a
  scale about a pivot, a mitred offset of a rectangle, a fill whose area is
  the triangle drawn.
* Files: a DXF round trip keeps the model (and its factor of safety), a
  properties import never brings the other project's ids or water, and a
  PDF report comes out of an analysis result and not out of a single
  evaluated surface.

What this file does NOT assert: that a DXF import leaves no duplicate
vertex. In v0.1.196 it left one — the reader repeats a closed polyline's
first point — and a test that pinned either answer would have consecrated
a behaviour nobody had decided on. The owner decided, and v0.1.197 asserts
it in ``test_closing_vertex_v1197.py``.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_anchored_wedge_root_v1177 as W  # noqa: E402

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}
_SLOPE = [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25], [20, 25]]
#: A circle through the crest of ``_SLOPE``: its FoS moves with anything
#: that acts on the crest, which is where the loads and the crack are put.
_CIRCLE = {"type": "circle", "centre_x": 42.0, "centre_y": 48.0,
           "radius": 26.0}
_REL = 2e-6       # a factor of safety is reported to 6 decimals


def _raised(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"{exc_type.__name__} was not raised")


def _state(ws, pid) -> str:
    return json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                      default=str)


def _slope(ws, **settings):
    from ogr_api import call
    pid = call(ws, "project_new", name="F2")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": _SLOPE,
        "materials": [{"name": "Soil", "unit_weight": 20.0,
                       "strength": _SOIL}],
        "settings": {"methods.tolerance": 1e-7,
                     "methods.max_iterations": 500, **settings}})
    return pid


def _fos(ws, pid, surface=_CIRCLE, method="bishop_simplified"):
    from ogr_api import call
    out = call(ws, "surface_evaluate", project_id=pid, surface=surface,
               methods=[method])
    return out["methods"][method]["fos"]


def _ws():
    from ogr_api import Workspace
    return Workspace()


# ======================================================================
# Rule 1 — the wedge, built through the operations
# ======================================================================
def _wedge(ws, num_slices=W.NSLICES):
    from ogr_api import call
    pid = call(ws, "project_new", name="Wedge")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, -10], [60, -10], [60, W.H], [W.CREST, W.H],
                     [W.TOE, 0], [0, 0]],
        "materials": [{"name": "S", "unit_weight": W.GAMMA, "strength": {
            "model": "mohr_coulomb",
            "params": {"cohesion": W.COH, "friction_angle": W.PHI}}}],
        "settings": {"methods.num_slices": num_slices,
                     "methods.tolerance": W.TIGHT,
                     "methods.max_iterations": W.MAX_IT}})
    return pid


def _anchor(ws, pid, application, capacity=120.0):
    from ogr_api import call
    call(ws, "support_type_set", project_id=pid, type_class="end_anchored",
         name="Anchor", params={"anchor_capacity": capacity,
                                "out_of_plane_spacing": 1.0})
    call(ws, "support_set", project_id=pid, support_type="Anchor",
         head=[34, 6], tail=[48, 11], force_application=application,
         orientation="user_defined", user_angle_deg=15.0)


def _plane(beta):
    return {"type": "polyline",
            "points": [[W.TOE, 0.0], [W._daylight_x(beta), W.H]]}


class TestTheWedgeThroughTheOperations:
    # The cells the engine reaches with every method. 45° Passive (Spencer)
    # and 50° are the cells ``test_anchored_wedge_root_v1177`` documents
    # (D119/D148); they measure the branch solver, not this layer.
    CELLS = [("active", 35.0), ("active", 40.0), ("passive", 35.0),
             ("passive", 40.0), ("active", 45.0)]

    def test_the_anchored_wedge_is_coulomb(self):
        from ogr_api import call
        from ogr_core.support import ForceApplication
        ws = _ws()
        try:
            for app, beta in self.CELLS:
                pid = _wedge(ws)
                _anchor(ws, pid, app)
                ref = W._closed_form(W._anchored(ForceApplication(app)),
                                     beta)
                out = call(ws, "surface_evaluate", project_id=pid,
                           surface=_plane(beta),
                           methods=["spencer", "gle_morgenstern_price",
                                    "janbu_simplified"])
                for mid, m in out["methods"].items():
                    assert abs(m["fos"] / ref - 1) < _REL, \
                        (app, beta, mid, m["fos"], ref)
        finally:
            ws.shutdown()

    def test_the_operations_build_the_fixtures_support(self):
        # The closed form reads the model's OWN support terms, so it agrees
        # with any engine that builds a wrong support. Evaluating it on the
        # project the operations built and on the fixture built by hand is
        # what shows the operations built the same anchor.
        from ogr_core.support import ForceApplication
        ws = _ws()
        try:
            for app in ("active", "passive"):
                pid = _wedge(ws)
                _anchor(ws, pid, app)
                for beta in (35.0, 40.0, 45.0, 50.0):
                    mine = W._closed_form(ws.get(pid).project, beta)
                    ref = W._closed_form(
                        W._anchored(ForceApplication(app)), beta)
                    assert mine == ref, (app, beta, mine, ref)
        finally:
            ws.shutdown()

    def test_janbu_reaches_it_on_every_plane(self):
        # Force equilibrium alone: no lambda to find, so no cell is spared.
        from ogr_api import call
        from ogr_core.support import ForceApplication
        ws = _ws()
        try:
            for app in ("active", "passive"):
                pid = _wedge(ws)
                _anchor(ws, pid, app)
                for beta in (35.0, 40.0, 45.0, 50.0):
                    ref = W._closed_form(
                        W._anchored(ForceApplication(app)), beta)
                    f = call(ws, "surface_evaluate", project_id=pid,
                             surface=_plane(beta),
                             methods=["janbu_simplified"])[
                        "methods"]["janbu_simplified"]["fos"]
                    assert abs(f / ref - 1) < _REL, (app, beta, f, ref)
        finally:
            ws.shutdown()

    def test_the_capacity_moves_the_number_as_the_closed_form_says(self):
        from ogr_api import call
        ws = _ws()
        try:
            got = {}
            for cap in (60.0, 240.0):
                pid = _wedge(ws)
                _anchor(ws, pid, "active", capacity=cap)
                ref = W._closed_form(ws.get(pid).project, 40.0)
                f = call(ws, "surface_evaluate", project_id=pid,
                         surface=_plane(40.0), methods=["spencer"])[
                    "methods"]["spencer"]["fos"]
                assert abs(f / ref - 1) < _REL, (cap, f, ref)
                got[cap] = f
            assert got[240.0] > got[60.0] + 0.1, got
        finally:
            ws.shutdown()

    def test_a_surcharge_is_coulomb_within_half_a_slice_of_load(self):
        # The engine samples a distributed load at each slice's mid-point
        # and puts no slice edge at the load's end, so the load the wedge
        # carries differs from q*(x_day - crest) by at most q*b/2 (b the
        # slice width; the other end is the exit, always an edge). F falls
        # as W grows, so the band is [F(Q + qb/2), F(Q - qb/2)]. Slice
        # counts that are NOT multiples of one another on purpose: 50, 100
        # ... 800 all put an edge at the same x and read as a constant
        # offset, which is how this looked like an engine error at first.
        from ogr_api import call
        beta, q = 40.0, 20.0
        xd = W._daylight_x(beta)
        a = math.radians(beta)
        length = math.hypot(xd - W.TOE, W.H)
        soil = W.GAMMA * 0.5 * W.H * (xd - W.CREST)
        tan_phi = math.tan(math.radians(W.PHI))

        def closed(load):
            w = soil + load
            return (W.COH * length + w * math.cos(a) * tan_phi) / (
                w * math.sin(a))

        exact = q * (xd - W.CREST)
        ws = _ws()
        try:
            for n in (50, 51, 73, 997):
                pid = _wedge(ws, num_slices=n)
                call(ws, "load_set", project_id=pid, kind="distributed",
                     start=[W.CREST, W.H], end=[xd, W.H], magnitude=q,
                     orientation="vertical")
                half = q * (xd - W.TOE) / n / 2
                lo, hi = closed(exact + half), closed(exact - half)
                for mid in ("spencer", "janbu_simplified"):
                    f = call(ws, "surface_evaluate", project_id=pid,
                             surface=_plane(beta), methods=[mid])[
                        "methods"][mid]["fos"]
                    assert lo * (1 - _REL) <= f <= hi * (1 + _REL), \
                        (n, mid, f, lo, hi)
        finally:
            ws.shutdown()


# ======================================================================
# Loads
# ======================================================================
class TestLoadsMoveTheNumber:
    def _with(self, ws, **load):
        from ogr_api import call
        pid = _slope(ws)
        call(ws, "load_set", project_id=pid, **load)
        return _fos(ws, pid)

    def test_each_setting_is_read(self):
        ws = _ws()
        try:
            bare = _fos(ws, _slope(ws))
            base = dict(kind="distributed", start=[50, 35], end=[60, 35],
                        magnitude=20.0, orientation="vertical")
            vert = self._with(ws, **base)
            assert vert < bare - 1e-3
            assert abs(self._with(ws, **{**base, "magnitude": 40.0})
                       - vert) > 1e-3
            assert abs(self._with(ws, **{**base, "orientation":
                                         "horizontal"}) - vert) > 1e-3
            tri = self._with(ws, **{**base, "magnitude": 0.0,
                                    "magnitude_end": 40.0,
                                    "distribution": "triangular"})
            assert abs(tri - vert) > 1e-3
            ang = self._with(ws, **{**base, "orientation":
                                    "angle_from_horizontal",
                                    "angle_deg": -60.0})
            assert abs(ang - vert) > 1e-3
        finally:
            ws.shutdown()

    def test_a_line_load_points_where_its_angle_says(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "load_set", project_id=pid, kind="line",
                 point_xy=[55, 35], magnitude=100.0,
                 orientation="angle_from_horizontal", angle_deg=-45.0)
            dx, dy = ws.get(pid).project.line_loads[0].direction_vector()
            assert abs(dx - math.cos(math.radians(-45))) < 1e-12
            assert abs(dy - math.sin(math.radians(-45))) < 1e-12
        finally:
            ws.shutdown()


class TestLoadsRefuseWhatTheEngineWouldNotRead:
    def test_refusals_leave_no_trace(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "load_set", project_id=pid, kind="line",
                 point_xy=[60, 35], magnitude=10.0, name="L1")
            before = _state(ws, pid)
            dist = dict(kind="distributed", start=[50, 35], end=[60, 35],
                        magnitude=20.0)
            attempts = [
                # the engine has no branch for these and acts vertically
                (Conflict, dict(kind="line", point_xy=[55, 35],
                                magnitude=5.0,
                                orientation="normal_to_boundary")),
                (Conflict, dict(kind="line", point_xy=[55, 35],
                                magnitude=5.0, angle_deg=10.0,
                                orientation="angle_to_boundary")),
                (Conflict, dict(**dist, orientation="vertical",
                                angle_deg=30.0)),
                (Conflict, dict(**dist, magnitude_end=5.0)),
                (Conflict, dict(**dist, distribution="triangular")),
                (InvalidArgument, dict(kind="distributed", start=[50, 35],
                                       end=[60, 35], magnitude=-1.0)),
                (InvalidArgument, dict(kind="line", point_xy=[55, 35],
                                       magnitude=5.0, start=[1, 1])),
                (Conflict, dict(load="L1", kind="distributed")),
            ]
            for exc_type, kwargs in attempts:
                _raised(exc_type, lambda kw=kwargs: call(
                    ws, "load_set", project_id=pid, **kw))
                assert _state(ws, pid) == before, kwargs
        finally:
            ws.shutdown()

    def test_notes_say_what_is_not_read(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            out = call(ws, "load_set", project_id=pid, kind="distributed",
                       start=[60, 35], end=[50, 35], magnitude=10.0,
                       creates_excess_pore_pressure=True)
            text = " ".join(out["notes"])
            assert "UPWARD" in text          # right to left pulls the ground
            assert "excess_pore_pressure" in text
            assert out["load"]["creates_excess_pore_pressure"] is True
            out = call(ws, "load_set", project_id=pid, kind="line",
                       point_xy=[45, 45], magnitude=10.0)
            assert any("not on the ground" in n for n in out["notes"])
        finally:
            ws.shutdown()

    def test_delete_by_name(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "load_set", project_id=pid, kind="line",
                 point_xy=[60, 35], magnitude=10.0, name="Crane")
            assert call(ws, "load_delete", project_id=pid,
                        loads=["crane"])["deleted"] == 1
            assert not ws.get(pid).project.line_loads
        finally:
            ws.shutdown()


class TestSeismic:
    def test_kh_is_read_only_when_enabled(self):
        from ogr_api import InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            bare = _fos(ws, pid)
            call(ws, "seismic_set", project_id=pid, enabled=True, kh=0.1)
            shaken = _fos(ws, pid)
            assert shaken < bare - 0.1, (bare, shaken)
            out = call(ws, "seismic_set", project_id=pid, enabled=False)
            assert out["notes"]              # kh kept but not read
            assert abs(_fos(ws, pid) - bare) < 1e-9
            _raised(InvalidArgument, lambda: call(
                ws, "seismic_set", project_id=pid, kh=1.2))
        finally:
            ws.shutdown()

    def test_record_units_are_standard_gravity(self):
        # 980.665 cm/s² and 9.80665 m/s² are exactly 1 g (the standard
        # gravity the Newmark integration uses, Jibson 1993).
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            for unit, peak in (("cm/s2", 980.665), ("m/s2", 9.80665),
                               ("g", 1.0)):
                out = call(ws, "seismic_record_set", project_id=pid,
                           name=unit, dt=0.01, unit=unit,
                           accelerations=[0.0, peak, 0.0])
                assert abs(out["record"]["pga_g"] - 1.0) < 1e-12, (unit, out)
                assert out["record"]["usable"] is True
        finally:
            ws.shutdown()

    def test_deleting_the_newmark_record_clears_the_selection(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            rid = call(ws, "seismic_record_set", project_id=pid, name="EQ",
                       dt=0.02, accelerations=[0, 0.2, 0])["record"]["id"]
            ws.get(pid).project.settings.seismic.record_id = rid
            out = call(ws, "seismic_record_delete", project_id=pid,
                       record="eq")
            assert out["notes"]
            assert ws.get(pid).project.settings.seismic.record_id == ""
        finally:
            ws.shutdown()


# ======================================================================
# Supports
# ======================================================================
class TestSupportTypes:
    def test_parameters_are_checked_against_the_class(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            before = _state(ws, pid)
            err = _raised(InvalidArgument, lambda: call(
                ws, "support_type_set", project_id=pid,
                type_class="end_anchored",
                params={"anchor_capacty": 100}))
            assert "anchor_capacity" in str(err)       # did you mean
            _raised(InvalidArgument, lambda: call(
                ws, "support_type_set", project_id=pid,
                type_class="pile_micropile",
                params={"failure_mode": "itomatsui"}))
            _raised(Conflict, lambda: call(
                ws, "support_type_set", project_id=pid,
                type_class="end_anchored", user_angle_deg=10.0))
            assert _state(ws, pid) == before
        finally:
            ws.shutdown()

    def test_defaults_come_from_the_class(self):
        # Three classes default to PASSIVE; the interface's fallback for a
        # set without stored defaults is ACTIVE for all of them.
        from ogr_api import call
        from ogr_core.support.support import support_registry
        ws = _ws()
        try:
            pid = _slope(ws)
            for key, cls in support_registry().items():
                st = call(ws, "support_type_set", project_id=pid,
                          type_class=key, name=key)["support_type"]
                assert st["force_application"] == \
                    cls.DEFAULT_APPLICATION.value, key
                assert st["orientation"] == cls.DEFAULT_ORIENTATION.value
                s = call(ws, "support_set", project_id=pid,
                         support_type=key, head=[40, 30],
                         tail=[48, 26])["support"]
                assert s["force_application"] == st["force_application"]
                assert s["orientation"] == st["orientation"]
                assert s["class"] == key and s["support_type"] == st["id"]
        finally:
            ws.shutdown()

    def test_a_used_type_is_not_deleted_silently(self):
        from ogr_api import Conflict, call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "support_type_set", project_id=pid,
                 type_class="end_anchored", name="A")
            nail = call(ws, "support_type_set", project_id=pid,
                        type_class="soil_nail", name="N")["support_type"]
            call(ws, "support_set", project_id=pid, support_type="A",
                 head=[40, 30], tail=[48, 26])
            _raised(Conflict, lambda: call(
                ws, "support_type_delete", project_id=pid,
                support_type="A"))
            out = call(ws, "support_type_delete", project_id=pid,
                       support_type="A", reassign_to="N")
            assert out["reassigned"] == 1
            s = ws.get(pid).project.supports[0]
            assert (s.type_ref, s.type_id) == (nail["id"], "soil_nail")
        finally:
            ws.shutdown()

    def test_changing_a_types_class_retypes_its_supports(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "support_type_set", project_id=pid,
                 type_class="end_anchored", name="A")
            call(ws, "support_set", project_id=pid, support_type="A",
                 head=[40, 30], tail=[48, 26])
            out = call(ws, "support_type_set", project_id=pid,
                       support_type="A", type_class="soil_nail")
            assert out["supports_retyped"] == 1
            assert out["support_type"]["force_application"] == "passive"
            assert ws.get(pid).project.supports[0].type_id == "soil_nail"
        finally:
            ws.shutdown()


class TestPatterns:
    def test_a_pattern_is_one_group_until_ungrouped(self):
        from ogr_api import Conflict, call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "support_type_set", project_id=pid,
                 type_class="soil_nail", name="N")
            start, end, spacing = [30, 25], [50, 35], 3.0
            out = call(ws, "support_pattern_add", project_id=pid,
                       support_type="N", start=start, end=end,
                       length=6.0, spacing=spacing)
            n = int(math.dist(start, end) // spacing) + 1
            assert out["added"] == n == 8
            pat = out["pattern_id"]
            p = ws.get(pid).project
            assert {s.pattern_id for s in p.supports} == {pat}
            call(ws, "support_set", project_id=pid, support_type="N",
                 head=[60, 35], tail=[60, 28])
            assert call(ws, "support_delete", project_id=pid,
                        pattern=pat)["deleted"] == n
            assert len(p.supports) == 1
            call(ws, "support_pattern_add", project_id=pid,
                 support_type="N", start=start, end=end, length=6.0,
                 spacing=spacing)
            assert call(ws, "support_ungroup",
                        project_id=pid)["ungrouped"] == n
            assert not any(s.pattern_id for s in p.supports)
            _raised(Conflict, lambda: call(ws, "support_ungroup",
                                           project_id=pid))
        finally:
            ws.shutdown()

    def test_a_retaining_wall_is_not_a_pattern(self):
        from ogr_api import Conflict, call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "support_type_set", project_id=pid,
                 type_class="retaining_wall_efp", name="Wall")
            _raised(Conflict, lambda: call(
                ws, "support_pattern_add", project_id=pid,
                support_type="Wall", start=[30, 25], end=[50, 35],
                length=6.0, spacing=3.0))
        finally:
            ws.shutdown()


# ======================================================================
# Search objects
# ======================================================================
class TestTensionCrack:
    def test_the_water_in_the_crack_is_read(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            _raised(Conflict, lambda: call(
                ws, "tension_crack_set", project_id=pid, mode="dry"))
            call(ws, "boundary_add", project_id=pid, type="tension_crack",
                 points=[[50, 32], [70, 32]])
            # A new crack is FILLED (the reference's default), so dry is
            # asked for explicitly.
            filled = _fos(ws, pid)
            call(ws, "tension_crack_set", project_id=pid, mode="dry")
            dry = _fos(ws, pid)
            got = {}
            for pct in (50.0, 100.0):
                call(ws, "tension_crack_set", project_id=pid,
                     mode="percent_filled", percent_filled=pct)
                got[pct] = _fos(ws, pid)
            assert got[100.0] < got[50.0] < dry - 1e-3, (dry, got)
            assert abs(got[100.0] - filled) < 1e-9     # 100 % is FILLED
            _raised(Conflict, lambda: call(
                ws, "tension_crack_set", project_id=pid,
                mode="percent_filled", depth=2.0))
            _raised(InvalidArgument, lambda: call(
                ws, "tension_crack_set", project_id=pid,
                mode="percent_filled", percent_filled=120.0))
            _raised(Conflict, lambda: call(
                ws, "tension_crack_set", project_id=pid,
                mode="use_water_table"))
        finally:
            ws.shutdown()


class TestFocusAndUserSurfaces:
    def test_focus_settings_are_the_kinds_own(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            _raised(Conflict, lambda: call(
                ws, "focus_set", project_id=pid, kind="window",
                points_xy=[[30, 25], [50, 25], [50, 35], [30, 35]],
                tolerance=1.0))
            _raised(InvalidArgument, lambda: call(
                ws, "focus_set", project_id=pid, kind="line",
                points_xy=[[30, 25], [40, 30], [50, 35]]))
            f = call(ws, "focus_set", project_id=pid, kind="point",
                     points_xy=[[40, 30]], tolerance=0.5)["focus"]
            assert f["tolerance"] == 0.5 and f["valid"]
            _raised(Conflict, lambda: call(
                ws, "focus_set", project_id=pid, focus=f["id"],
                kind="window"))
        finally:
            ws.shutdown()

    def test_user_surfaces_need_circular_surfaces(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws, **{"search.surface_type": "non_circular",
                                "search.search_method": "path"})
            before = _state(ws, pid)
            _raised(Conflict, lambda: call(
                ws, "user_surface_add", project_id=pid, surface=_CIRCLE))
            _raised(InvalidArgument, lambda: call(
                ws, "user_surface_add", project_id=pid,
                surface={"type": "polyline", "points": [[30, 25],
                                                        [50, 35]]}))
            assert _state(ws, pid) == before
        finally:
            ws.shutdown()


# ======================================================================
# Annotations
# ======================================================================
class TestAnnotations:
    def test_annotations_do_not_make_a_result_stale(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            call(ws, "surface_evaluate", project_id=pid, surface=_CIRCLE,
                 methods=["bishop_simplified"])
            call(ws, "project_save", project_id=pid, path=str(
                Path(tempfile.mkdtemp(prefix="ogr_f2_")) / "a.ogr"))
            call(ws, "annotation_set", project_id=pid, kind="text",
                 points_xy=[[30, 40]], text="crest")
            s = call(ws, "project_summary", project_id=pid)
            assert s["results"] and not s["results"][0]["stale"]
            assert s["unsaved_changes"] is True      # but it is unsaved
        finally:
            shutil.rmtree(Path(ws.get(pid).path).parent, ignore_errors=True)
            ws.shutdown()

    def test_the_bridge_to_geometry(self):
        from ogr_api import Conflict, call
        ws = _ws()
        try:
            pid = call(ws, "project_new", name="Bridge")["project_id"]
            rect = call(ws, "annotation_set", project_id=pid,
                        kind="rectangle",
                        points_xy=[[0, 0], [40, 20]])["annotation"]
            # v0.1.197 — a closed shape may become a material LENS now that
            # regions have holes (test_lens_regions_v1197); here the shape
            # becomes the External, and a closed shape as an open line
            # type is still refused.
            _raised(Conflict, lambda: call(
                ws, "annotation_to_boundary", project_id=pid,
                annotation=rect["id"], type="water_table"))
            out = call(ws, "annotation_to_boundary", project_id=pid,
                       annotation=rect["id"], type="external")
            # four corners: the outline's repeated first point is gone
            assert out["boundary"]["n_vertices"] == 4
            p = ws.get(pid).project
            assert len(p.annotations.ordered()) == 1     # it stays
            line = call(ws, "annotation_set", project_id=pid, kind="line",
                        points_xy=[[0, 8], [40, 8]])["annotation"]
            call(ws, "annotation_to_boundary", project_id=pid,
                 annotation=line["id"], type="water_table")
            assert len(p.boundaries) == 2
            _raised(Conflict, lambda: call(
                ws, "annotation_to_boundary", project_id=pid,
                annotation=rect["id"], type="external"))  # a second one
        finally:
            ws.shutdown()

    def test_what_a_kind_does_not_show_is_refused(self):
        from ogr_api import Conflict, InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            a = call(ws, "annotation_set", project_id=pid, kind="line",
                     points_xy=[[20, 30], [40, 30]])["annotation"]
            _raised(Conflict, lambda: call(
                ws, "annotation_set", project_id=pid, annotation=a["id"],
                text="label"))
            _raised(InvalidArgument, lambda: call(
                ws, "annotation_set", project_id=pid, annotation=a["id"],
                style={"line_widht": 2}))
            out = call(ws, "annotation_set", project_id=pid,
                       annotation="all", visible=False)
            assert out["count"] == 1
            assert not ws.get(pid).project.annotations.ordered()[
                0].style.visible
        finally:
            ws.shutdown()


# ======================================================================
# Geometry transforms
# ======================================================================
def _vertices(ws, pid, bid):
    b = next(x for x in ws.get(pid).project.boundaries if x.id == bid)
    return [(v.x, v.y) for v in b.polyline.vertices]


def _area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
                   in zip(pts, pts[1:] + pts[:1]))) / 2


class TestTransforms:
    def test_rotate_and_scale_about_a_pivot(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = _slope(ws)
            line = call(ws, "boundary_add", project_id=pid,
                        type="material",
                        points=[[20, 22], [70, 24]])["boundary"]["id"]
            call(ws, "boundary_edit", project_id=pid, boundary=line,
                 op="rotate", angle=90.0, pivot=[20, 22])
            got = _vertices(ws, pid, line)
            # (x, y) -> (px - (y - py), py + (x - px))
            want = [(20.0, 22.0), (18.0, 72.0)]
            assert all(math.dist(g, w) < 1e-9 for g, w in zip(got, want))
            call(ws, "boundary_edit", project_id=pid, boundary=line,
                 op="scale", sx=0.5, sy=2.0, pivot=[20, 22])
            got = _vertices(ws, pid, line)
            want = [(20.0, 22.0), (19.0, 122.0)]
            assert all(math.dist(g, w) < 1e-9 for g, w in zip(got, want))
        finally:
            ws.shutdown()

    def test_copy_gets_fresh_ids_and_the_rules(self):
        from ogr_api import Conflict, call
        ws = _ws()
        try:
            pid = _slope(ws)
            p = ws.get(pid).project
            line = call(ws, "boundary_add", project_id=pid,
                        type="material",
                        points=[[20, 22], [70, 24]])["boundary"]["id"]
            out = call(ws, "boundary_edit", project_id=pid, boundary=line,
                       op="copy", dy=0.5)["boundary"]
            assert out["id"] != line
            assert out["vertices"] == [[20.0, 22.5], [70.0, 24.5]]
            ids = [b.polyline.id for b in p.boundaries]
            assert len(ids) == len(set(ids))
            before = _state(ws, pid)
            _raised(Conflict, lambda: call(
                ws, "boundary_edit", project_id=pid,
                boundary=p.external_boundary().id, op="copy", dx=100.0))
            assert _state(ws, pid) == before
        finally:
            ws.shutdown()

    def test_simplify_removes_what_is_within_the_tolerance(self):
        from ogr_api import InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            line = call(ws, "boundary_add", project_id=pid,
                        type="material", points=[[20, 22], [45, 23.01],
                                                 [70, 24]])["boundary"]["id"]
            call(ws, "boundary_edit", project_id=pid, boundary=line,
                 op="simplify", tolerance=0.1)
            assert _vertices(ws, pid, line) == [(20, 22), (70, 24)]
            ext = ws.get(pid).project.external_boundary().id
            _raised(InvalidArgument, lambda: call(
                ws, "boundary_edit", project_id=pid, boundary=ext,
                op="simplify", tolerance=100.0))
        finally:
            ws.shutdown()

    def test_a_mitred_offset_of_a_rectangle(self):
        from ogr_api import call
        ws = _ws()
        try:
            pid = call(ws, "project_new", name="R")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [10, 0], [10, 5], [0, 5]],
                "materials": [{"name": "S", "strength": _SOIL}]})
            out = call(ws, "external_reshape", project_id=pid, offset=1.0)
            assert out["mode"] == "expand"
            v = [tuple(p) for p in out["external"]["vertices"]]
            assert abs(_area(v) - 12 * 7) < 1e-9
            out = call(ws, "external_reshape", project_id=pid, offset=-2.0)
            v = [tuple(p) for p in out["external"]["vertices"]]
            assert abs(_area(v) - 8 * 3) < 1e-9
        finally:
            ws.shutdown()

    def test_a_fill_adds_exactly_the_triangle_drawn(self):
        from ogr_api import InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            before = _area([tuple(p) for p in _SLOPE])
            out = call(ws, "external_reshape", project_id=pid,
                       points_xy=[[50, 35], [60, 37], [70, 35]])
            v = [tuple(p) for p in out["external"]["vertices"]]
            assert out["mode"] == "expand"
            assert abs(_area(v) - before - 0.5 * 20 * 2) < 1e-9
            _raised(InvalidArgument, lambda: call(
                ws, "external_reshape", project_id=pid, offset=1.0,
                points_xy=[[50, 35], [70, 35]]))
        finally:
            ws.shutdown()

    def test_cleanup_reports_then_removes_a_duplicate(self):
        import copy

        from ogr_api import InvalidArgument, call
        ws = _ws()
        try:
            pid = _slope(ws)
            ext = ws.get(pid).project.external_boundary()
            ext.polyline.vertices.insert(1, copy.copy(
                ext.polyline.vertices[1]))
            rep = call(ws, "geometry_cleanup", project_id=pid)
            assert rep["applied"] is False
            assert rep["boundaries"][0]["duplicate_vertices"] == 1
            assert len(ext.polyline.vertices) == 7      # reading changes nothing
            _raised(InvalidArgument, lambda: call(
                ws, "geometry_cleanup", project_id=pid,
                simplify_tolerance=0.1))
            out = call(ws, "geometry_cleanup", project_id=pid, apply=True)
            assert out["duplicates_removed"] == 1
            ext = ws.get(pid).project.external_boundary()
            assert len(ext.polyline.vertices) == 6
        finally:
            ws.shutdown()

    def test_an_open_material_ring_is_refused(self):
        # v0.1.196 refused every material ring: regions had no holes, so a
        # lens made the WHOLE model take the lens's material. v0.1.197
        # gives regions holes and accepts a CLOSED ring as a lens
        # (test_lens_regions_v1197); an OPEN line that returns to its start
        # is still refused — its two ends are extended as a cut.
        from ogr_api import Conflict, call
        ws = _ws()
        try:
            pid = _slope(ws)
            before = _state(ws, pid)
            ring = [[35, 22], [45, 22], [45, 24], [35, 24], [35, 22]]
            _raised(Conflict, lambda: call(
                ws, "boundary_add", project_id=pid, type="material",
                points=ring))
            assert _state(ws, pid) == before
            out = call(ws, "boundary_add", project_id=pid, type="material",
                       points=ring, closed=True)
            assert out["boundary"]["n_vertices"] == 4
        finally:
            ws.shutdown()


# ======================================================================
# Files
# ======================================================================
class TestFiles:
    def test_a_dxf_round_trip_keeps_the_model(self):
        from ogr_api import Conflict, call
        ws = _ws()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_f2_"))
        try:
            pid = _slope(ws)
            f0 = _fos(ws, pid)
            path = str(tmp / "slope.dxf")
            call(ws, "dxf_export", project_id=pid, path=path)
            seen = call(ws, "dxf_inspect", path=path)
            assert seen["ok"] and seen["boundaries"] == {"external": 1}
            out = call(ws, "dxf_import", project_id=pid, path=path)
            ext = ws.get(pid).project.external_boundary()
            got = {(float(v.x), float(v.y)) for v in ext.polyline.vertices}
            assert got == {tuple(map(float, p)) for p in _SLOPE}
            assert out["regions"] == 1
            assert abs(_fos(ws, pid) - f0) < 1e-9
            before = _state(ws, pid)
            _raised(Conflict, lambda: call(
                ws, "dxf_import", project_id=pid, path=path,
                replace_model=False))                    # two Externals
            assert _state(ws, pid) == before
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_properties_import_brings_no_foreign_ids_or_water(self):
        from ogr_api import call
        ws = _ws()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_f2_"))
        try:
            src = call(ws, "project_new", template="demo")["project_id"]
            path = str(tmp / "demo.ogr")
            call(ws, "project_save", project_id=src, path=path)
            source_ids = {m.id for m in ws.get(src).project.materials}
            pid = _slope(ws)
            call(ws, "material_set", project_id=pid, name="silty clay",
                 strength=_SOIL)
            out = call(ws, "properties_import", project_id=pid, path=path)
            assert out["materials"] == ["Silty clay (2)"]
            assert out["notes"]                          # the water
            m = ws.get(pid).project.materials[-1]
            assert m.id not in source_ids
            assert m.water_surface_id is None
            assert m.pore_pressure.value == "none"
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_report_and_a_dxf_from_an_analysis(self):
        from ogr_api import Conflict, call
        ws = _ws()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_f2_"))
        try:
            pid = _slope(ws, **{
                "methods.enabled_methods": ["bishop_simplified"],
                "search.grid_x_min": 22.8, "search.grid_x_max": 43.7,
                "search.grid_y_min": 42.3, "search.grid_y_max": 62.6,
                "search.grid_nx": 3, "search.grid_ny": 3,
                "search.radius_increment": 2})
            call(ws, "user_surface_add", project_id=pid, surface=_CIRCLE)
            run = call(ws, "analysis_run", project_id=pid,
                       wait_seconds=180)
            assert run["state"] == "done", run
            counts = run["summary"]["methods"][0]["counts"]
            assert counts["user_surfaces"] == 1       # the circle was read
            rid = run["result_id"]
            pdf = call(ws, "report_generate", path=str(tmp / "r.pdf"),
                       result_id=rid)
            assert Path(pdf["path"]).read_bytes()[:5] == b"%PDF-"
            call(ws, "dxf_export", project_id=pid, result_id=rid,
                 path=str(tmp / "r.dxf"))
            import ezdxf
            layers = {e.dxf.layer for e in
                      ezdxf.readfile(str(tmp / "r.dxf")).modelspace()}
            assert any("SLIP" in name.upper() for name in layers), layers
            one = call(ws, "surface_evaluate", project_id=pid,
                       surface=_CIRCLE, methods=["bishop_simplified"])
            _raised(Conflict, lambda: call(
                ws, "report_generate", path=str(tmp / "s.pdf"),
                result_id=one["result_id"]))
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)


class TestTheDemoTemplate:
    def test_it_is_the_canonical_demo(self):
        from ogr_api import InvalidArgument, call
        from ogr_core.project.demo import build_demo_project
        ws = _ws()
        try:
            pid = call(ws, "project_new", template="demo")["project_id"]
            p = ws.get(pid).project
            ref = build_demo_project()
            assert [(b.btype, [(v.x, v.y) for v in b.polyline.vertices])
                    for b in p.boundaries] == \
                [(b.btype, [(v.x, v.y) for v in b.polyline.vertices])
                 for b in ref.boundaries]
            mat = p.materials[0]
            assert mat.water_surface_id == p.boundaries[1].id
            assert mat.pore_pressure.value == "water_table"
            _raised(InvalidArgument, lambda: call(
                ws, "project_new", template="demos"))
        finally:
            ws.shutdown()
