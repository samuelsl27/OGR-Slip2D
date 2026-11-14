# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D409 (v0.1.452) — the factor Interpret writes beside the Ky says the kh it
was computed at.

The invariant
-------------
On a "Compute Ky" run Interpret writes, beside the critical seismic
coefficient, the factor of the critical surface: «FS(0) = …», and «ODF(0) =
…» under a design standard (``_reported_value``, shown in italics by the
summary). «(0)» says «without earthquake». But that factor is the one at the
PROJECT's horizontal coefficient, which is zero only when the project
applies none: with kh = 0.10 it wrote «FS(0) = 1.454» of the wedge at 0.10,
whose factor at 0 is 2.021 (measured with 0.1.435, 0.1.447 and 0.1.451). By the
owner's decision the caption now says the kh: «FS(kh = 0.1) = 1.454»,
«ODF(kh = 0.1)» («FSD(kh = 0.1)» in Spanish), read of the result
(``details["kh"]`` through ``ogr_slip2d.reported.factor_kh``, the rule the
PDF report asks since D408) and never of the open project. With kh = 0, and
for a result that does not keep its kh, the text of always, byte for byte.
«(0)» means kh = 0 with the project's kv: the Ky solver keeps the vertical
coefficient (``yield_acceleration``), so that is what it calls FS(0) too.

The reference (rule 1)
----------------------
The pseudo-static Coulomb wedge (Kramer 1996, §10.6.1.1), on the plane of
``test_newmark_user_surfaces_v1429`` (dry sand at 30 degrees, c = 0, so the
weight cancels): F(kh) = (cos β − kh·sin β)·tan φ / (sin β + kh·cos β), with
tan φd = tan φ / 1.25 under the custom standard of
``test_cli_reported_caption_v1430``. At kh = 0.10: 1.454067 and 1.163254;
at 0: 2.020726 and 1.616581. The Ky beside it, tan(φ − β), does not move.

Tolerance: the method's tolerance is set to 1e-8, where Janbu meets the
wedge to about 3e-13 (measured by the prompt), and the engine's factor is
compared with it to 1e-9 relative. The printed number is then compared with
the result's own factor, to the character: it IS that factor, rounded. With
the project's tolerance (0.005) Janbu departs from the wedge by 3.3e-6 and
2.0e-4 (absolute; the review of 0.1.452 measured them), and a band of half
the third decimal could not tell that residue from the rounding.

The kh as written: «%g», so 0.075 is not «0.07» or «0.1» and 0.1 + 0.05 is
not «0.15000000000000002». Interpret and the PDF report (D408) write it each
in its own sentence, and one case runs a kh of 0.075 through both (the
review found four formats a mutant could put there, all surviving).

Measured cost: about 1.5 s, five runs of a 60-slice plane computed once, a
report and a summary dock.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_METHOD = "janbu_simplified"
_RUNS: dict = {}
#: the docks the summary test builds, kept alive for the process
_DOCKS: list = []


def _run(kh, standard):
    """The plane of 0.1.429 with Compute Ky, the project's kh, and the custom
    standard of v1430 or none: ``(project, result, factor_report)``."""
    key = (kh, standard)
    if key not in _RUNS:
        from test_cli_reported_caption_v1430 import _plane

        from ogr_slip2d.analysis_runner import run_analysis
        p = _plane("ky", standard=standard)
        p.seismic.kh = kh
        # the wedge to the last digits: the printed number is compared with
        # the result's factor, and this with the closed form
        p.settings.methods.tolerance = 1e-8
        out = run_analysis(p)
        _RUNS[key] = (p, out.results[_METHOD], out.factor_report)
    return _RUNS[key]


def _wedge(kh, standard):
    """Kramer (1996), §10.6.1.1, with c = 0: F(kh) of the wedge."""
    from test_cli_reported_caption_v1430 import _FACTOR
    from test_newmark_user_surfaces_v1429 import _BETA, _PHI
    b = math.radians(_BETA)
    t = math.tan(math.radians(_PHI)) / (_FACTOR if standard else 1.0)
    return (math.cos(b) - kh * math.sin(b)) * t / (math.sin(b)
                                                   + kh * math.cos(b))


def _shown(kh, standard):
    from ogr_gui.interpret_window import _reported_value
    p, res, rep = _run(kh, standard)
    return _reported_value(res, res.critical, p, rep)


def _number(tip) -> float:
    return float(tip.rsplit("=", 1)[1])


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


class _English(_Spanish):
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("en")


# ======================================================================
class TestTheWedgeInClosedForm:

    def test_the_four_values(self):
        assert ["%.6f" % _wedge(kh, std) for kh, std in (
            (0.10, False), (0.10, True), (0.0, False), (0.0, True))] == [
            "1.454067", "1.163254", "2.020726", "1.616581"]

    def test_the_premise_the_result_keeps_its_kh(self):
        for std in (False, True):
            _p, res, _rep = _run(0.10, std)
            assert res.critical.details["kh"] == 0.10


class TestWithTheProjectsKh:

    def _check(self, std, head):
        _p, res, _rep = _run(0.10, std)
        fos = res.critical.fos
        # the engine's factor is the wedge at 0.10, not at 0
        assert abs(fos - _wedge(0.10, std)) <= 1e-9 * fos, fos
        assert abs(fos - _wedge(0.0, std)) > 0.1, fos
        with _English():
            _ky, tip = _shown(0.10, std)
        # and the caption says the kh and prints that factor
        assert tip == "%s(kh = 0.1) = %.3f" % (head, fos), tip

    def test_without_a_standard_the_caption_says_the_kh(self):
        self._check(False, "FS")

    def test_with_a_standard_it_is_an_over_design_factor_at_that_kh(self):
        self._check(True, "ODF")

    def test_the_ky_beside_it_does_not_move(self):
        from test_cli_reported_caption_v1430 import _closed
        for std in (False, True):
            ky, _tip = _shown(0.10, std)
            assert _close(float(ky), _closed("ky", std), 4), (std, ky)
            assert ky == _shown(0.0, std)[0], std

    def test_in_spanish(self):
        with _Spanish():
            _ky, tip = _shown(0.10, True)
            _ky, plain = _shown(0.10, False)
        assert tip.startswith("FSD(kh = 0.1) = "), tip
        assert plain.startswith("FS(kh = 0.1) = "), plain

    def test_asked_of_the_result_and_not_of_the_project(self):
        """The v0.1.127 rule: the project can change after the run."""
        from ogr_gui.interpret_window import _reported_value
        p, res, rep = _run(0.10, False)
        before = p.seismic.kh
        p.seismic.kh = 0.0
        try:
            with _English():
                _ky, tip = _reported_value(res, res.critical, p, rep)
        finally:
            p.seismic.kh = before
        assert tip.startswith("FS(kh = 0.1) = "), tip

    def test_the_summary_shows_it(self):
        """By the real summary of Interpret, which since D401 shows the
        user's critical surface (the plane is the user's)."""
        from PySide6.QtWidgets import QApplication

        from ogr_gui.interpret_window import _SummaryDock
        QApplication.instance() or QApplication([])
        p, res, rep = _run(0.10, False)
        with _English():
            dock = _SummaryDock()
            _DOCKS.append(dock)
            dock.show_result(res, p, rep)
            text = dock.label.text()
        assert "<i>FS(kh = 0.1) = %.3f</i>" % res.critical.fos in text, text


class TestTheKhAsWritten:
    """«%g»: the review of 0.1.452 put «%.1f», «%s», «%g» of the kh rounded
    to one decimal and «%.2g» there, and every case read kh = 0.1, so all
    four survived."""

    def test_the_format(self):
        from types import SimpleNamespace

        from ogr_gui.interpret_window import _reported_value
        p, res, rep = _run(0.10, False)
        for kh, text in ((0.075, "0.075"), (0.125, "0.125"),
                         (0.1 + 0.05, "0.15")):
            crit = SimpleNamespace(fos=res.critical.fos, details=dict(
                res.critical.details, kh=kh))
            with _English():
                _ky, tip = _reported_value(res, crit, p, rep)
            assert tip.startswith("FS(kh = %s) = " % text), (kh, tip)

    def test_interpret_and_the_report_write_the_same_kh(self):
        """Each door writes it in its own sentence (the report's «… of this
        surface, kh = 0.075», D408): a run with kh = 0.075 through both."""
        import os
        import tempfile

        import ogr_core.report.report_generator as RG
        p, res, rep = _run(0.075, False)
        with _English():
            _ky, tip = _shown(0.075, False)
        assert tip.startswith("FS(kh = 0.075) = "), tip
        said, real = [], RG.Paragraph

        class Par(real):
            def __init__(self, text, *a, **k):
                said.append(str(text).replace("<b>", "").replace("</b>", ""))
                super().__init__(text, *a, **k)

        RG.Paragraph = Par
        try:
            with tempfile.TemporaryDirectory() as d:
                RG.generate_report(p, {_METHOD: res}, os.path.join(d, "r.pdf"),
                                   factor_report=rep)
        finally:
            RG.Paragraph = real
        assert "Factor of Safety (FS) of this surface, kh = 0.075" in said, [
            t for t in said if "surface" in t]


class TestWithoutAKhNothingMoves:

    def test_the_text_of_always(self):
        with _English():
            for std, head in ((False, "FS"), (True, "ODF")):
                _p, res, _rep = _run(0.0, std)
                _ky, tip = _shown(0.0, std)
                assert tip == "%s(0) = %.3f" % (head, res.critical.fos), tip
                assert _close(_number(tip), _wedge(0.0, std), 3), tip

    def test_a_result_that_does_not_keep_its_kh(self):
        """A stand-in without ``details["kh"]`` (as the double of
        test_seismic_interface_v1127) reads as kh = 0."""
        from types import SimpleNamespace

        from ogr_gui.interpret_window import _reported_value
        p, res, rep = _run(0.10, False)
        crit = SimpleNamespace(fos=res.critical.fos, details={
            k: v for k, v in res.critical.details.items() if k != "kh"})
        with _English():
            _ky, tip = _reported_value(res, crit, p, rep)
        assert tip == "FS(0) = %.3f" % res.critical.fos, tip
