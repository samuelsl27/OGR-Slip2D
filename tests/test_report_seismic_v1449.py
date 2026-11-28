# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D408 (v0.1.449) — the PDF report of a Ky or a Newmark run says what each
number is.

The invariant
-------------
On a "Compute Ky" or a Newmark run the critical surface is the one with the
lowest Ky (``surface_score``), and its factor need not be the lowest. The
report did not ask what the run minimised: its «Global Minimums» block wrote
``critical.fos`` under the caption of the standard, as the minimum, and
neither the Ky nor the displacement anywhere (measured with 0.1.448 on the
demo slope with c = 20 kPa and a standard of 1.05: «Over-design Factor
1.5463», where the lowest admissible factor is 1.4559, 6 % lower). Now each
door that wrote ``crit.fos`` asks ``reported_caption`` of its method -- the
rule moved to the core for it (``ogr_core.project.reported``), and the
engine re-exports it:

* the block heads with the displacement (Newmark, in the project's unit)
  and the critical seismic coefficient, says the surface is the one with
  the lowest Ky of its method, and gives its factor «of this surface», at
  the kh it was computed at when the project applies one;
* the headings of Slice Data and the captions of the figures name the Ky or
  the displacement;
* with a design standard, the sentence the window's notes panel prints
  says the Ky and the displacement carry the partial factors (the owner's
  decision), for the run (``run_caption``) and only when some method has a
  critical surface;
* with upslope sliding allowed (v0.1.505, OGR Core 0.2.13, D437) the
  critical surface is «the one with the largest net Newmark displacement
  of this method», in English and in Spanish, and one-way it stays the
  lowest Ky;
* without Ky or Newmark the report is the one it was (``_V1354`` of
  ``test_report_spanish_v1355`` is the text-for-text control).

The reference (rule 1)
----------------------
Newmark (1965), on the plane of ``test_newmark_user_surfaces_v1429`` (the
user's two-vertex plane of dry sand at 30 degrees, made the critical surface
by a focus point that rejects the search): the yield acceleration of a rigid
block on a plane, Ky = tan(φ − β), with tan φd = tan φ / 1.25 under the
custom standard (0.155628); the displacement of the single rectangular pulse
of 0.5 g for 1 s, u = V²/(2gN)·(1 − N/A) (542.4997 cm with the standard);
and the factor of the wedge, F(k) = [c·L + W·(cos β − k·sin β)·tan φ] /
[W·(sin β + k·cos β)] (Kramer 1996, §10.6.1.1; at k = 0 and c = 0, tan φ /
tan β). For «it does not call it the minimum», two planes of the user on the
same slope with c = 5 kPa, both rigid wedges in closed form: A (4, 4)–(38,
10), with Ky 0.458506 and F 3.862921, is the critical one; B (4, 4)–(11,
10), with Ky 0.489749 and F 1.854131, has the lowest factor. The report
gives A's Ky and A's factor as A's, and B's factor nowhere.

Tolerances: the printed values against the closed forms at
``_close_enough`` of ``test_cli_reported_caption_v1430`` (half a unit of the
last decimal printed and 1e-5 relative); the two wedges with the method's
tolerance at 1e-8, where Janbu meets them to 6e-11 and 9e-10 relative in
the factor and 3e-9 in the Ky (measured by the review of 0.1.449).

Measured cost: about 4 s on the development laptop: nine small runs of a
60-slice plane (a few tenths each, computed once for the file), about
twenty reports and one figure.
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_METHOD = "janbu_simplified"
_HEAD = "Method: Janbu Simplified"
#: The two planes of «it does not call it the minimum»: (x0, y0) on the
#: face, (x1, 10) on the crest.
_A = ((4.0, 4.0), (38.0, 10.0))
_B = ((4.0, 4.0), (11.0, 10.0))
_COHESION = 5.0

_RUNS: dict = {}


def _wedge(plane, cohesion=0.0, kh=0.0):
    """``(F(kh), Ky)`` of the rigid wedge of dry sand above ``plane``, which
    runs from the 45 degree face to the crest at y = 10 (Newmark 1965;
    Kramer 1996, §10.6.1.1)."""
    from test_newmark_user_surfaces_v1429 import _PHI
    (x0, y0), (x1, y1) = plane
    # the triangle under the ground and over the plane: the face meets the
    # crest at (10, 10)
    area = 0.5 * abs(x0 * (10.0 - y1) + 10.0 * (y1 - y0) + x1 * (y0 - 10.0))
    w = 20.0 * area
    length = math.hypot(x1 - x0, y1 - y0)
    b, t = math.atan2(y1 - y0, x1 - x0), math.tan(math.radians(_PHI))
    f = ((cohesion * length + w * (math.cos(b) - kh * math.sin(b)) * t)
         / (w * (math.sin(b) + kh * math.cos(b))))
    ky = ((cohesion * length + w * math.cos(b) * t - w * math.sin(b))
          / (w * (math.cos(b) + math.sin(b) * t)))
    return f, ky


def _run(key):
    """The plane of 0.1.429 in ``key``: ("ky" | "newmark" | "fos",
    standard), "two" (the two wedges, Ky) or "kh" (Ky with the project's kh
    at 0.10). ``(project, results, factor_report)``, once."""
    if key not in _RUNS:
        from test_cli_reported_caption_v1430 import _plane

        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.surface import UserPolylineSurface
        if key == "two":
            from test_newmark_user_surfaces_v1429 import _plane_project
            p = _plane_project(cohesion=_COHESION)
            p.settings.seismic.newmark = False
            p.settings.seismic.compute_ky = True
            p.settings.methods.tolerance = 1e-8
            p.user_polylines = [UserPolylineSurface.from_points(list(pl))
                                for pl in (_A, _B)]
        elif key == "kh":
            p = _plane("ky", standard=False)
            p.seismic.kh = 0.10
        elif key in ("several", "strong"):
            from test_cli_reported_caption_v1430 import _FACTOR
            from test_newmark_user_surfaces_v1429 import (_STRONG_C,
                                                          _plane_project)
            if key == "several":
                p = _plane_project(("corps_engineers_1", "janbu_simplified"))
            else:
                p = _plane_project(cohesion=_STRONG_C)
                p.settings.seismic.newmark = False
                p.settings.seismic.compute_ky = True
            ds = p.settings.design_standard
            ds.enabled, ds.standard = True, "custom"
            ds.factor_cohesion = ds.factor_friction = _FACTOR
        elif key == "upslope":
            # OGR Core 0.2.13 (D437): Newmark with upslope sliding allowed,
            # where the run publishes the surface that moves most, net
            p = _plane("newmark", standard=True)
            p.settings.seismic.allow_upslope = True
        else:
            p = _plane(*key)
        out = run_analysis(p)
        _RUNS[key] = (p, out.results, out.factor_report)
    return _RUNS[key]


def _figures(p, results, factor_report):
    from ogr_api.report_figures import method_figures
    return method_figures(p, results, width=200, height=150,
                          factored=bool(getattr(factor_report, "applied",
                                                False)))


def _capture(p, results, factor_report, **kw):
    """The paragraphs the report writes, bold taken off, in order."""
    import ogr_core.report.report_generator as RG
    said = []
    real = RG.Paragraph

    class Par(real):
        def __init__(self, text, *a, **k):
            said.append(str(text).replace("<b>", "").replace("</b>", ""))
            super().__init__(text, *a, **k)

    RG.Paragraph = Par
    try:
        with tempfile.TemporaryDirectory() as d:
            RG.generate_report(p, results, os.path.join(d, "r.pdf"),
                               factor_report=factor_report, **kw)
    finally:
        RG.Paragraph = real
    return said


def _block(said, heading=_HEAD):
    """One method's rows in «Global Minimums»."""
    start = next(i for i, t in enumerate(said)
                 if t in ("Global Minimums", "Mínimos globales"))
    i = said.index(heading, start)
    out = [said[i]]
    for t in said[i + 1:]:
        if t.startswith(("Method: ", "Método: ")) or t in (
                "Global Minimum Coordinates",
                "Coordenadas de los mínimos globales",
                "Valid / Invalid Surfaces",
                "Superficies válidas / inválidas"):
            break
        out.append(t)
    return out


def _after(block, label) -> str:
    """The value written after ``label`` in a block."""
    return block[block.index(label) + 1]


def _number(text) -> float:
    return float(text.split()[0])


def _close(printed, expected, decimals):
    from test_cli_reported_caption_v1430 import _close_enough
    return _close_enough(printed, expected, decimals)


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

    def test_with_a_standard_the_block_heads_with_the_ky(self):
        from test_cli_reported_caption_v1430 import _closed
        p, results, rep = _run(("ky", True))
        block = _block(_capture(p, results, rep))
        assert block[1] == "Critical seismic coefficient", block
        assert _close(_number(block[2]), _closed("ky", True), 4), block
        assert "%.6f" % _closed("ky", True) == "0.155628"
        assert _after(block, "Critical surface") == \
            "the one with the lowest Ky of this method", block
        fos = _after(block, "Over-design Factor of this surface")
        assert _close(_number(fos), _closed("fos", True), 4), block
        assert "Over-design Factor" not in block, block

    def test_without_one_it_is_a_factor_of_safety_of_this_surface(self):
        from test_cli_reported_caption_v1430 import _closed
        p, results, rep = _run(("ky", False))
        said = _capture(p, results, rep)
        block = _block(said)
        assert _close(_number(block[2]), _closed("ky", False), 4), block
        fos = _after(block, "Factor of Safety (FS) of this surface")
        assert _close(_number(fos), _closed("fos", False), 4), block
        assert not any("Design standard applied" in t for t in said)

    def test_slice_data_and_the_figure_name_the_ky(self):
        p, results, rep = _run(("ky", True))
        said = _capture(p, results, rep,
                        figures=_figures(p, results, rep))
        ky = results[_METHOD].critical.details["ky"]
        heading = "%s — Ky = %.4f" % (_HEAD, ky)
        # once over the figure, once over the slice table
        assert said.count(heading) == 2, [t for t in said if "—" in t]
        assert not any(t.startswith(_HEAD + " — ODF") for t in said)

    def test_with_a_standard_it_says_the_ky_carries_the_factors(self):
        from ogr_slip2d.reported import KY, standard_note
        p, results, rep = _run(("ky", True))
        said = _capture(p, results, rep)
        want = str(standard_note(KY, rep, shows_factor=True))
        assert "critical seismic coefficient is computed with the " \
            "partial factors applied" in want
        assert any(t.endswith(want) for t in said), want


class TestANewmarkRun:

    def test_the_block_heads_with_the_displacement(self):
        from test_cli_reported_caption_v1430 import _closed
        p, results, rep = _run(("newmark", True))
        block = _block(_capture(p, results, rep))
        assert block[1] == "Newmark displacement", block
        assert block[2].endswith(" cm"), block
        assert _close(_number(block[2]), _closed("newmark", True), 3), block
        assert "%.4f" % _closed("newmark", True) == "542.4997"
        assert _close(_number(_after(block, "Critical seismic coefficient")),
                      _closed("ky", True), 4), block
        assert _after(block, "Critical surface") == \
            "the one with the lowest Ky of this method", block
        assert "Over-design Factor of this surface" in block, block

    def test_without_a_standard(self):
        from test_cli_reported_caption_v1430 import _closed
        p, results, rep = _run(("newmark", False))
        block = _block(_capture(p, results, rep))
        assert _close(_number(block[2]), _closed("newmark", False), 3), block
        assert "Factor of Safety (FS) of this surface" in block, block

    def test_slice_data_names_the_displacement(self):
        p, results, rep = _run(("newmark", True))
        said = _capture(p, results, rep)
        metres = results[_METHOD].critical.details["newmark_displacement"]
        assert "%s — Newmark displacement = %.3f cm" % (
            _HEAD, 100.0 * metres) in said, [t for t in said if "—" in t]

    def test_with_a_standard_it_says_both_carry_the_factors(self):
        from ogr_slip2d.reported import NEWMARK, standard_note
        p, results, rep = _run(("newmark", True))
        said = _capture(p, results, rep)
        want = str(standard_note(NEWMARK, rep, shows_factor=True))
        assert any(t.endswith(want) for t in said), want

    def test_in_the_projects_unit_as_interpret_prints_it(self):
        """One rule for the unit (``displacement_in_units``): an imperial
        project reads inches in the report and in Interpret alike."""
        from ogr_gui.interpret_window import _reported_value
        p, results, rep = _run(("newmark", True))
        units = p.settings.units
        before = units.system_id
        units.system_id = "imperial_psf"
        try:
            block = _block(_capture(p, results, rep))
            crit = results[_METHOD].critical
            shown, _tip = _reported_value(results[_METHOD], crit, p, rep)
        finally:
            units.system_id = before
        metres = crit.details["newmark_displacement"]
        assert block[2] == shown == "%.3f in" % (metres / 0.0254), (
            block, shown)


class TestANetNewmarkRun:
    """OGR Core 0.2.13 (D437 of v0.1.499): with upslope sliding allowed the
    critical surface is the one with the largest NET displacement
    (``SearchResult.net_newmark``), and the report says so, not «the one
    with the lowest Ky». The displacement it prints is the critical
    surface's own; the other rows do not change."""

    def test_the_premise_the_run_is_a_net_one(self):
        _p, results, _rep = _run("upslope")
        sr = results[_METHOD]
        assert sr.net_newmark is True
        assert "newmark_displacement" in sr.critical.details

    def test_the_block_says_the_largest_net_displacement(self):
        p, results, rep = _run("upslope")
        block = _block(_capture(p, results, rep))
        assert block[1] == "Newmark displacement", block
        metres = results[_METHOD].critical.details["newmark_displacement"]
        assert block[2] == "%.3f cm" % (100.0 * metres), block
        assert _after(block, "Critical surface") == (
            "the one with the largest net Newmark displacement of this "
            "method"), block
        assert "the one with the lowest Ky of this method" not in block

    def test_one_way_the_row_is_the_lowest_ky(self):
        """The control: the same plane without upslope sliding."""
        _p, results, _rep = _run(("newmark", True))
        assert not getattr(results[_METHOD], "net_newmark", False)

    def test_in_spanish(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import method_name
        p, results, rep = _run("upslope")
        with _Spanish():
            said = _capture(p, results, rep, translate=note_text,
                            method_name=method_name)
            # the heading in Spanish too, as TestInSpanish takes it
            head = "Método: " + method_name(_METHOD)
        block = _block(said, head)
        assert _after(block, "Superficie crítica") == (
            "la de mayor desplazamiento neto de Newmark de este método"), block


class TestItDoesNotCallItTheMinimum:

    def test_the_premise_two_wedges_in_closed_form(self):
        _p, results, _rep = _run("two")
        sr = results[_METHOD]
        by_end = {round(e.surface.polyline.vertices[-1].x, 6): e
                  for e in sr.user_evaluations}
        a, b = by_end[_A[1][0]], by_end[_B[1][0]]
        fa, kya = _wedge(_A, _COHESION)
        fb, kyb = _wedge(_B, _COHESION)
        assert ("%.6f %.6f %.6f %.6f" % (fa, kya, fb, kyb)
                == "3.862921 0.458506 1.854131 0.489749")
        for ev, f, ky in ((a, fa, kya), (b, fb, kyb)):
            assert abs(ev.fos - f) < 1e-6 * f, (ev.fos, f)
            assert abs(ev.details["ky"] - ky) < 1e-5, (ev.details["ky"], ky)
        assert sr.critical is a, "A, of the lower Ky, is the critical one"
        assert b.fos < a.fos, "and B has the lower factor"

    def test_the_report_gives_as_critical_a_and_nothing_of_b(self):
        p, results, rep = _run("two")
        sr = results[_METHOD]
        a = sr.critical
        b = next(e for e in sr.user_evaluations if e is not a)
        said = _capture(p, results, rep)
        block = _block(said)
        assert block[2] == "%.4f" % a.details["ky"], block
        assert _after(block, "Factor of Safety (FS) of this surface") == \
            "%.4f" % a.fos, block
        assert ["Surface", "Defined by the user"] == block[5:7], block
        assert not any("%.4f" % b.fos in t for t in said), "%.4f" % b.fos


class TestTheFactorAtTheProjectsKh:
    """With a kh of its own, the factor of the surface is the one at that
    kh, said, and not the factor without earthquake; the Ky beside it is
    solved over kh from zero, so it does not change (D409's rule)."""

    def test_the_label_says_the_kh_and_the_number_is_the_wedge_at_it(self):
        from test_newmark_user_surfaces_v1429 import _PLANE
        p, results, rep = _run("kh")
        block = _block(_capture(p, results, rep))
        at = _after(block, "Factor of Safety (FS) of this surface, kh = 0.1")
        f010, ky = _wedge(_PLANE, 0.0, kh=0.10)
        f000, _ = _wedge(_PLANE, 0.0, kh=0.0)
        assert "%.6f %.6f" % (f010, f000) == "1.454067 2.020726"
        assert _close(_number(at), f010, 4), block
        assert _close(_number(block[2]), ky, 4), block

    def test_asked_of_the_result_and_not_of_the_project(self):
        """The v0.1.127 rule: the project can change after the run, what
        the run did cannot."""
        p, results, rep = _run("kh")
        before = p.seismic.kh
        p.seismic.kh = 0.25
        try:
            block = _block(_capture(p, results, rep))
        finally:
            p.seismic.kh = before
        assert "Factor of Safety (FS) of this surface, kh = 0.1" in block, \
            block


class TestTheSentenceIsTheRuns:
    """The standard's sentence speaks for the run (``run_caption``): a
    Newmark displacement of ANY method makes it a Newmark run (D397), and
    with no critical surface at all there is nothing for it to qualify (the
    review of 0.1.449 found both: a mutant that read the first method alone
    survived, and the sentence spoke of a Ky the report did not show)."""

    def test_a_first_method_without_a_critical_does_not_hide_newmark(self):
        import copy

        from ogr_slip2d.reported import KY, NEWMARK, standard_note
        p, results, rep = _run("several")
        first = copy.copy(results["corps_engineers_1"])
        # by hand, as test_newmark_user_surfaces_v1429 does: Spencer and
        # GLE leave a method so on a plane with kh (D143), and the test
        # should not hang on a defect staying open
        first.evaluations, first.user_evaluations = [], []
        assert first.critical is None
        two = {"corps_engineers_1": first,
               "janbu_simplified": results["janbu_simplified"]}
        said = _capture(p, two, rep)
        assert any(t.endswith(str(standard_note(NEWMARK, rep,
                                                shows_factor=True)))
                   for t in said)
        assert not any(t.endswith(str(standard_note(KY, rep,
                                                    shows_factor=True)))
                       for t in said)
        assert _block(said, "Method: Corps of Engineers #1")[1:] == [
            "No valid critical surface found."]
        assert _block(said)[1] == "Newmark displacement"

    def test_no_critical_surface_no_sentence(self):
        p, results, rep = _run("strong")
        assert results[_METHOD].critical is None      # the premise
        assert results[_METHOD].objective == "ky" and rep.applied
        said = _capture(p, results, rep)
        assert _block(said)[1:] == ["No valid critical surface found."]
        assert not any("Design standard applied" in t for t in said)


class TestInSpanish:

    def _said(self, key, **kw):
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import method_name
        p, results, rep = _run(key)
        with _Spanish():
            said = _capture(p, results, rep, translate=note_text,
                            method_name=method_name, **kw)
            head = "Método: " + method_name(_METHOD)
        return said, head, rep

    def test_a_ky_run(self):
        from ogr_slip2d.reported import KY, standard_note
        from ogr_gui.core_messages import note_text
        said, head, rep = self._said(("ky", True))
        block = _block(said, head)
        assert block[1] == "Coeficiente sísmico crítico", block
        assert _after(block, "Superficie crítica") == \
            "la de menor Ky de este método", block
        assert "Factor de sobredimensionamiento de esta superficie" in \
            block, block
        assert any(t.startswith(head + " — Ky = ") for t in said)
        with _Spanish():
            want = note_text(standard_note(KY, rep, shows_factor=True))
        assert any(t.endswith(want) for t in said), want

    def test_a_newmark_run(self):
        said, head, _rep = self._said(("newmark", True))
        block = _block(said, head)
        assert block[1] == "Desplazamiento de Newmark", block
        assert _after(block, "Superficie crítica") == \
            "la de menor Ky de este método", block
        assert any(t.startswith(head + " — Desplazamiento de Newmark = ")
                   for t in said)

    def test_the_kh_of_the_project(self):
        said, head, _rep = self._said("kh")
        assert "Factor de seguridad (FS) de esta superficie, kh = 0.1" in \
            _block(said, head)

    def test_every_new_text_has_its_spanish(self):
        from ogr_gui.core_messages import note_text
        new = ["the one with the lowest Ky of this method",
               "the one with the largest net Newmark displacement of this "
               "method",
               "{0} of this surface", "{0} of this surface, kh = {1:g}"]
        with _Spanish():
            assert all(note_text(t) != t for t in new), \
                [t for t in new if note_text(t) == t]


class TestWithoutKyNothingMoves:

    def test_a_factor_run_heads_with_its_factor(self):
        p, results, rep = _run(("fos", True))
        said = _capture(p, results, rep)
        block = _block(said)
        crit = results[_METHOD].critical
        assert block[1:3] == ["Over-design Factor", "%.4f" % crit.fos], block
        assert not any("of this surface" in t
                       or t == "Critical seismic coefficient" for t in said)
        assert "%s — ODF = %.4f" % (_HEAD, crit.fos) in said
        # the standard is said as it always was, in its table: no sentence
        assert not any("Design standard applied" in t for t in said)


class TestOneRule:

    def test_the_engine_hands_out_the_cores_rule(self):
        import ogr_core.project.reported as core
        import ogr_slip2d.reported as engine
        for name in ("reported_caption", "run_caption", "standard_note",
                     "factor_kh", "displacement_in_units", "REPORTED_NOTES"):
            assert getattr(engine, name) is getattr(core, name), name
