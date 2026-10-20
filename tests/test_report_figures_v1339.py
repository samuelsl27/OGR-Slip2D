# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.339 (D336, second part) — the PDF report carries one figure per method.

The report was tables and text, with no drawing of the model at all. By
decision of the owner it carries, for each method, a figure of the model
with that method's critical surface, the annotation layer and, when the
search had a grid of slip centres, the contours of the minimum factor of
safety at each centre with the critical centre marked; framed on the model
or on the model and the whole area the grid searched. A dialog asks for it
before the file name, and ``report_generate`` takes the same three options.

The invariants:

* **one image per method in the PDF**, and none with the figures off (rule
  7), through the core, the operation and the window's action;
* **the contours are the minimum at each centre**: the values drawn are the
  lowest factor of the valid surfaces of each centre, computed here
  independently from the search's evaluations; the lowest of them is the
  critical factor and the star sits on the critical centre;
* **the framing moves the frame** (rule 7): the search-area frame contains
  every centre the search evaluated, valid or not, in the picture as drawn;
  the model frame is the model's box with its margin, and leaves the upper
  centres of this grid out;
* without a grid of centres there are no contours, and the dialog greys the
  search-area frame and says why;
* the annotations change the picture;
* a held frame leaves no warning: since v0.1.338 matplotlib warned on every
  PNG that it was widening a fixed limit for the equal aspect.

The grid is the one of ``test_f2_ops_v1196`` (4 x 4 centres above the
slope, three radii), run once for the whole file.
"""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}
_SLOPE = [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25], [20, 25]]
_SETTINGS = {
    "methods.enabled_methods": ["bishop_simplified", "janbu_simplified"],
    "search.grid_x_min": 22.8, "search.grid_x_max": 43.7,
    "search.grid_y_min": 42.3, "search.grid_y_max": 62.6,
    "search.grid_nx": 3, "search.grid_ny": 3,
    "search.radius_increment": 2}
_METHODS = ("bishop_simplified", "janbu_simplified")
GREEN = "#00ff7f"
GREEN_RGB = (0.0, 1.0, 127 / 255.0)
_CACHE: dict = {}


def _project():
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Figures")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": _SLOPE,
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": _SOIL}],
            "settings": dict(_SETTINGS)})
        return ws.get(pid).project
    finally:
        ws.shutdown()


def _run():
    """``(project, results)`` of the grid search, computed once."""
    if "run" not in _CACHE:
        from ogr_slip2d.analysis_runner import run_analysis
        project = _project()
        _CACHE["run"] = (project, run_analysis(project).results)
    return _CACHE["run"]


def _green_rectangle():
    from ogr_core.annotations import (Annotation, AnnotationKind,
                                      AnnotationStyle)
    # inside the slope, under the grid, so the model frame shows it
    return Annotation(kind=AnnotationKind.RECTANGLE,
                      points=[(52.0, 22.0), (66.0, 32.0)],
                      style=AnnotationStyle(colour=GREEN, fill=GREEN,
                                            fill_opacity=1.0))


def _pixels_of(png: bytes, rgb, tol=0.02) -> int:
    import matplotlib.image as mpimg
    import numpy as np
    img = mpimg.imread(io.BytesIO(png))[..., :3]
    return int(np.all(np.abs(img - np.array(rgb)) < tol, axis=-1).sum())


def _images_in(pdf: bytes) -> int:
    """The pictures of a PDF: its image objects less their soft masks. A
    PNG with an alpha channel is written as an image and its mask, and
    reportlab writes one mask for identical alphas."""
    import re
    masks = set(re.findall(rb"/SMask (\d+) 0 R", pdf))
    return pdf.count(b"/Subtype /Image") - len(masks)


def _page_text(pdf: bytes) -> bytes:
    """The content streams of a PDF, decoded: reportlab writes them as
    ASCII85 over Flate."""
    import base64
    import re
    import zlib
    out = b""
    for m in re.finditer(rb"<<(.{0,400}?)>>\s*stream\r?\n(.*?)endstream", pdf,
                         re.S):
        head, body = m.group(1), m.group(2).strip()
        if b"/Image" in head:
            continue
        try:
            if b"ASCII85Decode" in head:
                # reportlab ends the data with ``~>`` and does not open it
                body = body.removeprefix(b"<~").removesuffix(b"~>")
                body = base64.a85decode(body)
            if b"FlateDecode" in head:
                body = zlib.decompress(body)
        except (ValueError, zlib.error):
            continue
        out += body
    return out


def _centres(sr, valid_only: bool):
    from ogr_slip2d.interpretation import slip_centre
    pool = sr.valid() if valid_only else sr.all_evaluations()
    out = []
    for r in pool:
        c = slip_centre(r.surface.to_dict())
        if c is not None:
            out.append((r, c))
    return out


@contextlib.contextmanager
def _spy(cls, name, record):
    """``cls.name`` wrapped to record its calls, restored afterwards."""
    original = getattr(cls, name)

    def wrapper(self, *a, **k):
        out = original(self, *a, **k)
        record.append((self, a, k))
        return out
    setattr(cls, name, wrapper)
    try:
        yield record
    finally:
        setattr(cls, name, original)


def _drawn_frame(**kwargs):
    """The axes' limits as matplotlib drew them, after the equal aspect
    adjusted them: ``(xmin, xmax, ymin, ymax)``. At the size and with the
    grid of the report's figures: without the data limits set to the frame,
    this one was cut to y 24.1-58.5 and left 20 of the 64 centres out."""
    from matplotlib.figure import Figure

    from ogr_api.report_figures import grid_data
    from ogr_api.render import render_png
    project, results = _run()
    sr = results["bishop_simplified"]
    calls = []
    with _spy(Figure, "savefig", calls):
        render_png(project, surfaces=[("c", sr.critical)], width=1400,
                   height=900, grid=grid_data(sr), **kwargs)
    ax = calls[-1][0].axes[0]
    return (*ax.get_xlim(), *ax.get_ylim())


# ======================================================================
class TestOneFigurePerMethod:

    def test_the_core_embeds_one_image_per_method(self):
        from ogr_api.report_figures import method_figures
        from ogr_core.report.report_generator import generate_report
        project, results = _run()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_fig_"))
        try:
            figures = method_figures(project, results)
            assert [mid for mid, _png in figures] == list(_METHODS)
            generate_report(project, results, str(tmp / "with.pdf"),
                            figures=figures)
            generate_report(project, results, str(tmp / "without.pdf"))
            assert _images_in((tmp / "with.pdf").read_bytes()) == 2
            assert _images_in((tmp / "without.pdf").read_bytes()) == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_each_figure_has_its_caption(self):
        """The caption -- the method and the factor it found, as the
        report's other per-method headings write it -- once more with the
        figures than without them, for each method; and the section."""
        from ogr_api.report_figures import method_figures
        from ogr_core.report.report_generator import (_method_name,
                                                      generate_report)
        project, results = _run()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_fig_"))
        try:
            generate_report(project, results, str(tmp / "with.pdf"),
                            figures=method_figures(project, results))
            generate_report(project, results, str(tmp / "without.pdf"))
            on = _page_text((tmp / "with.pdf").read_bytes())
            off = _page_text((tmp / "without.pdf").read_bytes())
            for mid in _METHODS:
                name, fos = _method_name(mid), results[mid].critical.fos
                # the dash is octal 227 in the font's encoding
                caption = ("(Method: %s \\227 FS = %.4f)"
                           % (name, fos)).encode()
                assert on.count(caption) == off.count(caption) + 1, mid
            assert b"(Critical Surface by Method)" in on
            assert b"(Critical Surface by Method)" not in off
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_operation_asks_for_them(self):
        from ogr_api import NotFound, Workspace, call
        ws = Workspace()
        tmp = Path(tempfile.mkdtemp(prefix="ogr_fig_"))
        try:
            pid = call(ws, "project_new", name="F")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": _SLOPE,
                "materials": [{"name": "Soil", "unit_weight": 20.0,
                               "strength": _SOIL}],
                "settings": dict(_SETTINGS)})
            run = call(ws, "analysis_run", project_id=pid, wait_seconds=180)
            assert run["state"] == "done", run
            rid = run["result_id"]
            call(ws, "report_generate", path=str(tmp / "a.pdf"),
                 result_id=rid, framing="search_area")
            call(ws, "report_generate", path=str(tmp / "b.pdf"),
                 result_id=rid, figures=False)
            assert _images_in((tmp / "a.pdf").read_bytes()) == 2
            assert _images_in((tmp / "b.pdf").read_bytes()) == 0
            try:
                call(ws, "report_generate", path=str(tmp / "c.pdf"),
                     result_id=rid, framing="everything")
            except NotFound as exc:      # as an unknown ``what`` is
                assert "framing" in str(exc)
            else:
                raise AssertionError("an unknown framing was accepted")
        finally:
            ws.shutdown()
            shutil.rmtree(tmp, ignore_errors=True)


# ======================================================================
class TestTheContoursAreTheMinimumAtEachCentre:

    def test_the_values_are_the_lowest_valid_factor_of_each_centre(self):
        from ogr_api.report_figures import grid_data
        _project_, results = _run()
        for mid in _METHODS:
            sr = results[mid]
            lowest: dict = {}
            for r, c in _centres(sr, valid_only=True):
                lowest[c] = min(lowest.get(c, float("inf")), r.fos)
            grid = grid_data(sr)
            drawn = dict(zip(zip(grid["x"], grid["y"]), grid["fos"]))
            assert drawn == lowest, mid
            assert len(drawn) >= 3

    def test_the_lowest_is_the_critical_and_the_star_sits_on_it(self):
        from ogr_api.report_figures import grid_data
        _project_, results = _run()
        for mid in _METHODS:
            sr = results[mid]
            grid = grid_data(sr)
            assert min(grid["fos"]) == sr.critical.fos, mid
            s = sr.critical.surface
            assert grid["critical"] == (s.centre_x, s.centre_y), mid

    def test_the_picture_draws_those_values(self):
        from matplotlib.axes import Axes

        from ogr_api.report_figures import grid_data
        from ogr_api.render import render_png
        project, results = _run()
        sr = results["bishop_simplified"]
        grid = grid_data(sr)
        contours, plots = [], []
        with _spy(Axes, "tricontourf", contours), \
                _spy(Axes, "plot", plots):
            render_png(project, surfaces=[("c", sr.critical)], grid=grid)
        assert len(contours) == 1
        tri, z = contours[0][1][0], contours[0][1][1]
        assert list(tri.x) == grid["x"] and list(tri.y) == grid["y"]
        assert list(z) == grid["fos"]
        stars = [a for _ax, a, _k in plots if len(a) == 3 and a[2] == "*"]
        assert stars == [([grid["critical"][0]], [grid["critical"][1]],
                          "*")]


    def test_the_scale_says_what_the_number_is(self):
        """With partial factors on the inputs the number is an over-design
        factor, and the report says so; the scale of the contours too."""
        from matplotlib.figure import Figure

        from ogr_api.report_figures import method_figures
        project, results = _run()
        labels = {}
        for factored in (False, True):
            calls = []
            with _spy(Figure, "colorbar", calls):
                method_figures(project, {"bishop_simplified":
                                         results["bishop_simplified"]},
                               factored=factored)
            labels[factored] = [k.get("label") for _f, _a, k in calls]
        assert labels == {False: ["minimum factor of safety"],
                          True: ["minimum over-design factor"]}


# ======================================================================
class TestTheFramingMovesTheFrame:

    def test_the_search_area_holds_every_evaluated_centre(self):
        from ogr_api.report_figures import figure_extent
        project, results = _run()
        extent = figure_extent(project, results, "search_area")
        every = [c for sr in results.values()
                 for _r, c in _centres(sr, valid_only=False)]
        assert len(every) == sum(len(sr.all_evaluations())
                                 for sr in results.values())
        x0, x1, y0, y1 = _drawn_frame(extent=extent)
        for frame in (extent, (x0, x1, y0, y1)):
            for cx, cy in every:
                assert frame[0] < cx < frame[1], (cx, frame)
                assert frame[2] < cy < frame[3], (cy, frame)

    def test_an_invalid_centre_is_framed_and_not_contoured(self):
        """Every surface of this grid is valid, so one that is not is put
        far from it: the search-area frame holds it, and the contours,
        which are of the valid surfaces, leave it out."""
        import copy

        from ogr_api.report_figures import figure_extent, grid_data
        from ogr_slip2d.surface import SlipCircle
        project, results = _run()
        sr = results["bishop_simplified"]
        bad = copy.copy(sr.evaluations[0])
        bad.surface = SlipCircle(centre_x=120.0, centre_y=95.0, radius=80.0)
        bad.converged = False
        assert not bad.is_valid
        sr2 = copy.copy(sr)
        sr2.evaluations = list(sr.evaluations) + [bad]
        x0, x1, y0, y1 = figure_extent(project, {"b": sr2}, "search_area")
        assert x0 < 120.0 < x1 and y0 < 95.0 < y1
        assert grid_data(sr2) == grid_data(sr)

    def test_the_model_frame_is_the_box_with_its_margin(self):
        from ogr_api.report_figures import MARGIN, figure_extent
        project, results = _run()
        xmin, ymin, xmax, ymax = project.bounding_box()
        pad = MARGIN * max(xmax - xmin, ymax - ymin)
        assert figure_extent(project, results, "model") == (
            xmin - pad, xmax + pad, ymin - pad, ymax + pad)

    def test_the_two_frames_differ_as_drawn(self):
        from ogr_api.report_figures import figure_extent
        project, results = _run()
        top = max(c[1] for sr in results.values()
                  for _r, c in _centres(sr, valid_only=False))
        model = _drawn_frame(extent=figure_extent(project, results,
                                                  "model"))
        area = _drawn_frame(extent=figure_extent(project, results,
                                                 "search_area"))
        assert model[3] < top < area[3]

    def test_an_unknown_framing_is_refused(self):
        from ogr_api.report_figures import figure_extent
        project, results = _run()
        try:
            figure_extent(project, results, "everything")
        except ValueError:
            return
        raise AssertionError("an unknown framing was accepted")


# ======================================================================
class _NoCentre:
    """A search whose surfaces have no slip centre, as a non-circular one."""

    class _R:
        fos = 1.4
        is_valid = True

        class surface:
            @staticmethod
            def to_dict():
                return {"type": "polyline"}

    evaluations = [_R(), _R(), _R()]
    critical = _R()

    def valid(self):
        return list(self.evaluations)


class TestWithoutAGrid:

    def test_no_grid_and_no_contours(self):
        from matplotlib.axes import Axes

        from ogr_api.report_figures import grid_data, has_centres
        from ogr_api.render import render_png
        assert grid_data(_NoCentre()) is None
        assert has_centres({"x": _NoCentre()}) is False
        project, results = _run()
        assert has_centres(results) is True
        contours = []
        with _spy(Axes, "tricontourf", contours):
            render_png(project, grid=grid_data(_NoCentre()))
        assert contours == []


# ======================================================================
class TestNoAspectWarning:
    """v0.1.338 fixed the axes' limits around the annotation layer, which
    turns autoscaling off, and matplotlib then warned on every PNG that it
    was widening one of them for the equal aspect: 26 times in the suite of
    0.1.338, none in 0.1.337's. The limits are held without it."""

    def _warnings(self, **kwargs) -> list:
        import logging

        from ogr_api.render import render_png
        project, results = _run()
        seen = []

        class _Catch(logging.Handler):
            def emit(self, record):
                seen.append(record.getMessage())

        log = logging.getLogger("matplotlib.axes._base")
        handler = _Catch(level=logging.WARNING)
        log.addHandler(handler)
        try:
            render_png(project, surfaces=[
                ("c", results["bishop_simplified"].critical)], **kwargs)
        finally:
            log.removeHandler(handler)
        return seen

    def test_with_the_annotation_layer(self):
        assert self._warnings() == []

    def test_with_a_frame(self):
        from ogr_api.report_figures import figure_extent
        project, results = _run()
        for framing in ("model", "search_area"):
            extent = figure_extent(project, results, framing)
            assert self._warnings(extent=extent) == [], framing


# ======================================================================
class TestTheAnnotationsChangeTheFigure:

    def test_green_with_them_and_none_without(self):
        import copy

        from ogr_api.report_figures import method_figures
        project, results = _run()
        project = copy.deepcopy(project)
        project.annotations.add(_green_rectangle())
        on = dict(method_figures(project, results, annotations=True))
        off = dict(method_figures(project, results, annotations=False))
        for mid in _METHODS:
            assert _pixels_of(on[mid], GREEN_RGB) > 500, mid
            assert _pixels_of(off[mid], GREEN_RGB) == 0, mid


# ======================================================================
def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@_requires_qt
class TestTheDialog:

    def test_defaults_with_a_grid_and_no_annotation(self):
        from ogr_gui.dialogs.report_dialog import ReportDialog
        from ogr_gui.i18n import tr
        _app()
        project, results = _run()
        dlg = ReportDialog(project, results)
        assert dlg.options == {"figures": True, "framing": "model",
                               "annotations": False}
        assert dlg.rb_search_area.isEnabled()
        assert not dlg.chk_annotations.isEnabled()
        assert dlg.chk_annotations.toolTip() == tr(
            "The model has no visible annotation.")
        dlg.rb_search_area.setChecked(True)
        assert dlg.options["framing"] == "search_area"

    def test_without_centres_the_search_area_is_greyed_with_its_reason(self):
        import copy

        from ogr_gui.dialogs.report_dialog import ReportDialog
        from ogr_gui.i18n import tr
        _app()
        project, _results = _run()
        project = copy.deepcopy(project)
        project.annotations.add(_green_rectangle())
        dlg = ReportDialog(project, {"x": _NoCentre()})
        assert not dlg.rb_search_area.isEnabled()
        assert dlg.rb_search_area.toolTip() == tr(
            "No search of this run has a grid of slip centres.")
        assert dlg.chk_annotations.isEnabled()
        assert dlg.options["annotations"] is True

    def test_figures_off_greys_their_options(self):
        import copy

        from ogr_gui.dialogs.report_dialog import ReportDialog
        _app()
        project, results = _run()
        project = copy.deepcopy(project)
        project.annotations.add(_green_rectangle())
        dlg = ReportDialog(project, results)
        dlg.chk_figures.setChecked(False)
        assert not dlg.gb_framing.isEnabled()
        assert not dlg.chk_annotations.isEnabled()
        assert dlg.options["figures"] is False
        dlg.chk_figures.setChecked(True)
        assert dlg.gb_framing.isEnabled()
        assert dlg.chk_annotations.isEnabled()

    def test_in_spanish(self):
        from ogr_gui.dialogs.report_dialog import ReportDialog
        from ogr_gui.i18n import current_language, set_language
        _app()
        project, _results = _run()
        before = current_language()
        set_language("es")
        try:
            dlg = ReportDialog(project, {"x": _NoCentre()})
            assert dlg.gb_framing.title() == "Encuadre"
            assert dlg.rb_search_area.text() == "Modelo y área de búsqueda"
            assert dlg.chk_figures.text() == \
                "Superficie crítica de cada método"
            assert dlg.rb_search_area.toolTip() == (
                "Ninguna búsqueda de este cálculo tiene una rejilla de "
                "centros.")
        finally:
            set_language(before)


@_requires_qt
class TestTheWindowAction:

    def _act(self, accept: bool, framing: str = "search_area"):
        """``act_generate_report`` with the dialog answered, the file name
        given and the message boxes recorded: ``(asked, pdf bytes)``."""
        import ogr_gui.main_window as mw
        from ogr_gui.dialogs.report_dialog import ReportDialog
        from test_f2_rules_v1196 import _window
        _app()
        project, results = _run()
        w = _window(project)
        w.last_search_results = results
        tmp = Path(tempfile.mkdtemp(prefix="ogr_fig_"))
        asked = []

        def _exec(dlg):
            asked.append("options")
            if framing == "search_area":
                dlg.rb_search_area.setChecked(True)
            return int(accept)

        class _Files:
            @staticmethod
            def getSaveFileName(*_a, **_k):
                asked.append("file")
                return str(tmp / "r.pdf"), ""

        class _Box:
            @staticmethod
            def information(*a, **_k):
                asked.append("information")

            warning = critical = information

        saved = (ReportDialog.exec, mw.QFileDialog, mw.QMessageBox)
        ReportDialog.exec = _exec
        mw.QFileDialog, mw.QMessageBox = _Files, _Box
        try:
            w.act_generate_report()
            pdf = tmp / "r.pdf"
            return asked, (pdf.read_bytes() if pdf.exists() else None)
        finally:
            ReportDialog.exec, mw.QFileDialog, mw.QMessageBox = saved
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_options_come_first_and_the_figures_follow(self):
        asked, pdf = self._act(accept=True)
        assert asked == ["options", "file", "information"]
        assert _images_in(pdf) == 2

    def test_cancelling_the_options_asks_nothing_else(self):
        asked, pdf = self._act(accept=False)
        assert asked == ["options"]
        assert pdf is None
