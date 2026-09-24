# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — what an agent reads back: a real PNG and plain JSON.

Invariants protected:

* **The render is a PNG of the size asked for**, read from its own IHDR
  header rather than trusted, and the critical surface appears in it ONLY
  when there is a result: the surface colour is counted in the pixels, and
  a render without a result must have none. A picture that always showed
  a surface would be a picture that could show the wrong one.
* **Summaries are strict JSON.** ``json.dumps(..., allow_nan=False)`` on
  everything an operation returns — the check ``LEMResult.to_dict`` has
  been held to since v0.1.152, because NaN is not JSON and Python writes
  it anyway.
* **The headline says what the number IS, and says it as the interface
  does.** ``ogr_slip2d.reported.reported_caption`` is the one decision;
  the interface's ``reported_quantity`` now asks it, and the four cases
  (factor of safety, over-design factor, Ky, Newmark) must map to the same
  captions in both.
* **The counts carry their identities**: total = valid + invalid, and a
  grid attempts (nx+1)(ny+1)(r+1).
"""
from __future__ import annotations

import io
import json
import struct

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}
_CIRCLE = {"type": "circle", "centre_x": 29.07, "centre_y": 55.495,
           "radius": 30.495637}


def _ws():
    from ogr_api import Workspace, call
    ws = Workspace()
    pid = call(ws, "project_new", name="Render")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                     [20, 25]],
        "materials": [{"name": "Soil", "unit_weight": 20.0,
                       "strength": _SOIL, "color": "#c8b89a"}]})
    return ws, pid


def _ihdr(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png[12:16] == b"IHDR"
    return struct.unpack(">II", png[16:24])


def _surface_pixels(png: bytes) -> int:
    """Pixels within 0.06 of the first surface colour, #d62728."""
    import numpy as np
    from matplotlib.image import imread

    img = imread(io.BytesIO(png), format="png")[..., :3]
    target = np.array([0xd6, 0x27, 0x28]) / 255.0
    return int((np.abs(img - target).max(axis=2) < 0.06).sum())


class TestTheRender:
    def test_it_is_a_png_of_the_requested_size(self):
        from ogr_api import call
        ws, pid = _ws()
        try:
            for w, h in ((640, 400), (1000, 700)):
                out = call(ws, "model_render", project_id=pid, width=w,
                           height=h)
                assert _ihdr(out["png"]) == (w, h)
        finally:
            ws.shutdown()

    def test_the_surface_is_drawn_only_when_there_is_a_result(self):
        from ogr_api import call
        ws, pid = _ws()
        try:
            bare = call(ws, "model_render", project_id=pid)["png"]
            rid = call(ws, "surface_evaluate", project_id=pid,
                       surface=_CIRCLE,
                       methods=["bishop_simplified"])["result_id"]
            drawn = call(ws, "model_render", result_id=rid)
            assert _surface_pixels(bare) == 0
            assert _surface_pixels(drawn["png"]) > 200
            assert len(drawn["surfaces"]) == 1
            assert drawn["surfaces"][0].startswith("bishop_simplified: ")
        finally:
            ws.shutdown()

    def test_it_can_be_saved_for_a_client_without_images(self, tmp_path):
        from ogr_api import Conflict, Workspace, call
        import pytest
        ws, pid = _ws()
        try:
            ws.workdir = tmp_path
            out = call(ws, "model_render", project_id=pid,
                       save_path="model")
            saved = tmp_path / "model.png"
            assert out["saved_to"] == str(saved.resolve())
            assert saved.read_bytes() == out["png"]
            with pytest.raises(Conflict):
                call(ws, "model_render", project_id=pid, save_path="model")
        finally:
            ws.shutdown()


class TestPlainJson:
    def test_every_answer_is_strict_json(self):
        from ogr_api import call
        ws, pid = _ws()
        try:
            answers = [
                call(ws, "project_summary", project_id=pid, detail="full"),
                call(ws, "project_validate", project_id=pid),
                call(ws, "settings_get", project_id=pid),
                call(ws, "catalog", kind="strength_models"),
                call(ws, "surface_evaluate", project_id=pid,
                     surface=_CIRCLE),
                call(ws, "project_get", project_id=pid,
                     section="materials"),
            ]
            for a in answers:
                json.dumps(a, allow_nan=False)
        finally:
            ws.shutdown()

    def test_non_finite_numbers_become_null(self):
        from ogr_api.results import json_safe
        out = json_safe({"a": float("nan"), "b": [float("inf"), 1.5],
                         "c": (1, 2)})
        assert out == {"a": None, "b": [None, 1.5], "c": [1, 2]}
        json.dumps(out, allow_nan=False)

    def test_a_surface_that_does_not_cut_the_model_says_so(self):
        from ogr_api import call
        ws, pid = _ws()
        try:
            out = call(ws, "surface_evaluate", project_id=pid,
                       surface={"type": "circle", "centre_x": 500,
                                "centre_y": 500, "radius": 1})
            assert out["methods"]["bishop_simplified"] is None
            assert out["notes"]
            json.dumps(out, allow_nan=False)
        finally:
            ws.shutdown()


class _Crit:
    def __init__(self, details):
        self.details = details
        self.fos = 1.25


class _Res:
    def __init__(self, objective="fos", details=None):
        self.objective = objective
        self.critical = _Crit(details or {})


class _Report:
    def __init__(self, applied):
        self.applied = applied


class TestTheHeadline:
    _CASES = [
        (_Res(), _Report(False), "fos"),
        (_Res(), _Report(True), "overdesign"),
        (_Res("ky", {"ky": 0.14}), _Report(True), "ky"),
        (_Res("ky", {"ky": 0.14, "newmark_displacement": 0.03}),
         _Report(False), "newmark"),
    ]

    def test_the_caption_of_each_quantity(self):
        from ogr_api.results import headline
        for res, rep, caption in self._CASES:
            h = headline(res, rep)
            assert h["caption"] == caption, (caption, h)
        assert headline(*self._CASES[2][:2])["value"] == 0.14
        assert headline(*self._CASES[3][:2])["unit"] == "m"

    def test_the_interface_captions_follow_the_same_decision(self):
        try:
            from ogr_gui.reported_quantity import reported_quantity
        except ImportError:  # pragma: no cover - no Qt on this machine
            return
        want = {"fos": ("fos", "Factor of safety"),
                "overdesign": ("fos", "Over-design factor"),
                "ky": ("ky", "Critical seismic coefficient"),
                "newmark": ("newmark", "Newmark displacement")}
        # The captions are compared in English; the language is set and
        # PUT BACK here, because the runner never calls a teardown (rule 5).
        from ogr_gui.i18n import current_language, set_language
        saved = current_language()
        set_language("en")
        try:
            for res, rep, caption in self._CASES:
                assert reported_quantity(res, rep) == want[caption], caption
        finally:
            set_language(saved)

    def test_the_interface_asks_the_engine_module(self):
        """Delegation, not a second copy: replacing the decision in
        ``ogr_slip2d.reported`` changes what the interface prints."""
        try:
            from ogr_gui import reported_quantity as rq
        except ImportError:  # pragma: no cover
            return
        import ogr_slip2d.reported as rep
        saved = rep.reported_caption
        try:
            rep.reported_caption = lambda *_a, **_k: rep.KY
            assert rq.reported_quantity(_Res(), _Report(False))[0] == "ky"
        finally:
            rep.reported_caption = saved


class TestTheCounts:
    def test_the_identities_of_a_grid_run(self):
        from ogr_api import call
        ws, pid = _ws()
        try:
            call(ws, "settings_set", project_id=pid, changes={
                "methods.enabled_methods": ["bishop_simplified"],
                "search.grid_x_min": 22.8, "search.grid_x_max": 43.7,
                "search.grid_y_min": 42.3, "search.grid_y_max": 62.6,
                "search.grid_nx": 3, "search.grid_ny": 5,
                "search.radius_increment": 2})
            out = call(ws, "analysis_run", project_id=pid,
                       wait_seconds=120)
            c = out["summary"]["methods"][0]["counts"]
            assert c["attempted"] == (3 + 1) * (5 + 1) * (2 + 1)
            assert c["total"] == c["valid"] + c["invalid"]
            json.dumps(out, allow_nan=False)
        finally:
            ws.shutdown()
