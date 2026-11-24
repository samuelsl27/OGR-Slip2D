# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.488 (D454) — the number of wedges of Sarma's method is a number ASKED
FOR, and a uniform division whose face would cross a neighbour or not reach
the ground is dropped only where dropping it cannot move the factor.

THE DEFECT
    v0.1.464 dropped every such uniform division with its boundary. On a
    straight stretch of one Mohr-Coulomb material that is exact: the two
    wedges add up to the one they split (``TestFacesOnAStraightStretch`` of
    ``test_sarma_wedges_v1463``). On a circle it is not: its bases are the
    chords between the divisions, and the cascade took a circle asked for 25
    wedges down to 2 chords, ANOTHER surface. The bank's 002 (03 manual):
    F 2.21 with the bisector against 4.19 with 25 vertical faces and 4.37 by
    Spencer, on the unsafe side (``_auditoria/P9_D454/censo_cunas_d454.py``:
    554 circles of the 03 searches lost wedges, 20 of them 23 of 25). And
    the setting was called «Least number of wedges», which it never was:
    the published surface of problem 4 saturated asked for 25 has 19.

THE INVARIANTS
    * Off a straight stretch the face is made vertical, and the count and
      the surface are kept: the bases of a circle asked for 25 wedges are
      the 25 chords between its uniform divisions, by their total length
      computed here from the circle alone (geometry, rule 1). With the rule
      of v0.1.487 (``wedges.DROP_ONLY_ON_STRAIGHT = False``, restored) the
      same circle has 2 wedges and another factor (rule 7).
    * On a straight stretch the division is still dropped, and the factor is
      the one of the wedges it would have split: problem 4 saturated (Hoek
      1987, published 0.434) asked for 25 has 19 wedges and 0.434662, as with
      2 (the identity of the straight stretch).
    * No visible name of the setting says «least» or «mínimo»: the Methods
      page (label and tooltip, in English and Spanish) and the command line.
      The report's row is OGR-Core's (``_sarma_settings_rows``): its English
      is «Number of Wedges Asked For» since its 0.2.10 (pinned in v0.1.489;
      «Least Number of Wedges» before), its Spanish, ours, «Número de cuñas
      pedido»; the old key is gone from the translations.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import test_sarma_wedges_v1463 as W63  # noqa: E402

#: The circle of the test: centre inside the slope of ``W63._external``,
#: where the bisectors point toward the centre and cross under the ground.
_CENTRE, _RADIUS = (30.0, 16.0), 10.0


def _circle_project():
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("v1488 circle")
    W63._external(p, ((0, 0), (80, 0), (80, 20), (40, 20), (20, 10), (0, 10)))
    p.materials = [Material(name="soil", unit_weight=18.0,
                            strength=MohrCoulomb(cohesion=5.0,
                                                 friction_angle=30.0))]
    p.settings.sarma.num_slices = 25
    p.settings.sarma.slice_angles = "bisector"
    p.settings.sarma.tolerance = 1e-9
    return p


def _circle_result(only_straight=True):
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    from ogr_slip2d.sarma import wedges as WD
    from ogr_slip2d.surface import SlipCircle
    kept = WD.DROP_ONLY_ON_STRAIGHT
    WD.DROP_ONLY_ON_STRAIGHT = only_straight
    try:
        return evaluate_surfaces(
            _circle_project(),
            SlipCircle(centre_x=_CENTRE[0], centre_y=_CENTRE[1],
                       radius=_RADIUS), ["sarma"]).results["sarma"]
    finally:
        WD.DROP_ONLY_ON_STRAIGHT = kept


class TestACircleKeepsItsWedges:

    def test_the_count_and_the_chords(self):
        r = _circle_result()
        assert r.fos is not None and len(r.slices) == 25, (r.fos, len(r.slices))
        xs = r.slices.boundaries
        assert len(xs) == 26
        # the uniform divisions are equal in x between the two ends of the
        # arc; the chords between the points of the circle at them
        cx, cy = _CENTRE

        def y(x):
            return cy - math.sqrt(_RADIUS ** 2 - (x - cx) ** 2)
        step = (xs[-1] - xs[0]) / 25.0
        for k, x in enumerate(xs):
            assert abs(x - (xs[0] + k * step)) < 1e-6 * _RADIUS, (k, x)
        chords = sum(math.hypot(b - a, y(b) - y(a))
                     for a, b in zip(xs, xs[1:]))
        from ogr_slip2d.sarma.wedges import to_solver
        bases = sum(b.length for b in to_solver(r.slices, 0.0, 0.0).bases)
        assert abs(bases - chords) < 1e-6 * chords, (bases, chords)
        made_vertical = sum(1 for f in r.slices.faces
                            if f.angle_source == "verticalized")
        assert made_vertical >= 1

    def test_the_rule_of_before_moves_the_number(self):
        new, old = _circle_result(), _circle_result(only_straight=False)
        assert len(old.slices) < 5, len(old.slices)
        assert abs(new.fos / old.fos - 1.0) > 0.1, (new.fos, old.fos)


class TestAStraightStretchStillDrops:
    """Problem 4 saturated (Hoek 1987, published 0.434), its published
    surface with Hoek's face at the kink: asked for 25, 19 wedges, and the
    factor of 2."""

    def test_problem_4_saturated(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import attach_vertex_data
        out = {}
        for n in (2, 25):
            p, s, angles = W63._problem4(True)
            p.settings.sarma.tolerance = 1e-12
            p.settings.sarma.num_slices = n
            attach_vertex_data(s, {k: {"angle": a, "c": None, "phi": None}
                                   for k, a in angles.items()})
            out[n] = evaluate_surfaces(p, s, ["sarma"]).results["sarma"]
        assert len(out[25].slices) == 19, len(out[25].slices)
        assert abs(out[25].fos - out[2].fos) < 1e-9 * out[2].fos
        assert abs(out[2].fos - W63._TOOL4[True]) < 1e-6, out[2].fos


class TestTheNameSaysWhatItDoes:

    @staticmethod
    def _page_texts():
        from PySide6.QtWidgets import QApplication
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import _MethodsPage
        QApplication.instance() or QApplication([])
        page = _MethodsPage(ProjectSettings())
        try:
            spn = page.spn_sarma_n
            form = spn.parentWidget().layout()
            return form.labelForField(spn).text(), spn.toolTip()
        finally:
            page.deleteLater()

    def test_the_methods_page(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        texts = {}
        try:
            for lang in ("en", "es"):
                set_language(lang)
                texts[lang] = self._page_texts()
        finally:
            set_language(before)
        assert texts["en"][0] == "Number of wedges asked for:", texts["en"]
        assert texts["es"][0] == "Número de cuñas pedido:", texts["es"]
        for lang, (label, tip) in texts.items():
            for word in ("least", "mínimo", "minimum"):
                assert word not in label.lower(), (lang, label)
                assert word not in tip.lower(), (lang, tip)
        assert "more wedges than asked" in texts["en"][1]
        assert "fewer" in texts["en"][1]

    def test_the_command_line(self):
        import inspect
        from ogr_cli.__main__ import compute
        opt = inspect.signature(compute).parameters["sarma_slices"].default
        text = opt.help.lower()
        assert "asked for" in text and "least" not in text, opt.help

    def test_the_report_row_in_spanish(self):
        from ogr_gui.i18n import current_language, set_language, tr
        before = current_language()
        set_language("es")
        try:
            es = tr("Number of Wedges Asked For")
        finally:
            set_language(before)
        assert es == "Número de cuñas pedido", es
        from ogr_gui.i18n import _DICTS
        assert "Least Number of Wedges" not in _DICTS["es"]
