# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.133 — the Auto Refine panel publishes the population the
Auto Refine search actually generates.

**The invariant**: the number the interface announces before the run and
the number the generator produces are the SAME number, and they are the
same number because they come from the SAME place.

Defect D07c(c). The panel multiplied ``divisions x circles x iterations``
— 1000 with the default 10/10/10 — while the generator walks the PAIRS of
divisions, ``C(d,2) x circles`` per iteration, which is 4500. A factor of
4.5, and it grows: at 20 divisions the panel said 2000 for a search that
generates 19000. Nothing numerical moved, but a user who sizes a search by
that figure sizes it 4.5 times short.

**The external anchor.** The reference publishes both formulae —
``y·x(x-1)/2`` circles per iteration and ``z·(y·x(x-1)/2)`` in total — and
states that the default 10/10/10 "generates 4500 circles", noting that the
count is proportional to the SQUARE of the divisions along the slope. The
values asserted below are that published arithmetic, not a snapshot of
what OGR prints today.

**Why two sets of values and not one.** At 10/10/10 a wrong reading can
still land on a believable number; at 20/10/10 the readings separate
(2000 against 19000), so one set alone could pass a formula that is still
wrong.

**Generated is not analysed, and these tests say so out loud.** A pair and
tangent angle whose construction has no valid centre, and a circle a focus
object rejects, are skipped without ever reaching the solver: verification
problem 14 generates 4500 and analyses 3300. So the published number is an
upper bound; ``SearchResult.attempts`` is what the generator attempted and
``SearchResult.total_count`` is what was analysed — the ``generadas`` of
the verification bank. Confusing the two is the next version of this
defect, which is why the last class here pins the inequality.
"""
from __future__ import annotations
import math
import re


def _slope(name: str = "auto-refine-count"):
    """A small slope, deliberately cheap: the loop is quadratic in the
    divisions, so every case below keeps them in single figures."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 10.0
    beta = math.radians(35.0)
    toe = 20.0
    crest = toe + H / math.tan(beta)
    ext = Polyline(vertices=[
        Vertex(0, -8.0), Vertex(45, -8.0), Vertex(45, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=19,
                            strength=MohrCoulomb(cohesion=10,
                                                 friction_angle=25))]
    p.settings.methods.num_slices = 25
    return p


def _project(divisions, circles, iterations, surface_type="circular",
             optimize=False):
    p = _slope("ar-%d-%d-%d-%s" % (divisions, circles, iterations,
                                   surface_type))
    s = p.settings.search
    s.surface_type = surface_type
    s.search_method = "auto_refine"
    s.auto_refine_divisions_along_slope = divisions
    s.auto_refine_circles_per_division = circles
    s.auto_refine_num_iterations = iterations
    s.auto_refine_num_vertices_along_surface = 8
    # Explicit: the optimisation is ON by default for the non-circular
    # pair, and it appends evaluations that have nothing to do with the
    # generation being counted here.
    s.optimize_enabled = optimize
    return p


def _run(divisions, circles, iterations, surface_type="circular"):
    from ogr_slip2d.analysis_runner import build_search
    p = _project(divisions, circles, iterations, surface_type)
    return build_search(p, "bishop_simplified").run(p)


# ======================================================================
class TestThePublishedArithmetic:
    """The formulae the reference publishes, evaluated at the panel for
    which it publishes a value: 10/10/10 generates 4500 circles."""

    def test_the_default_panel_generates_four_thousand_five_hundred(self):
        from ogr_slip2d.search import AutoRefineSearch
        assert AutoRefineSearch.surfaces_per_iteration(10, 10) == 450
        assert AutoRefineSearch.surfaces_generated(10, 10, 10) == 4500

    def test_it_is_quadratic_in_the_divisions(self):
        """The property the reference states in words — proportional to
        the SQUARE of the divisions — and the one the discarded formula
        did not have: doubling the divisions must nearly quadruple the
        count, not double it."""
        from ogr_slip2d.search import AutoRefineSearch
        assert AutoRefineSearch.surfaces_generated(20, 10, 10) == 19000
        ten = AutoRefineSearch.surfaces_generated(10, 10, 10)
        twenty = AutoRefineSearch.surfaces_generated(20, 10, 10)
        assert twenty > 4 * ten - 1000, (ten, twenty)

    def test_the_count_is_pairs_and_not_divisions(self):
        """The defect in one assertion: the discarded formula gave 1000
        and 2000 for these two panels."""
        from ogr_slip2d.search import AutoRefineSearch
        for d, c, it in ((10, 10, 10), (20, 10, 10)):
            assert (AutoRefineSearch.surfaces_generated(d, c, it)
                    == math.comb(d, 2) * c * it)
            assert AutoRefineSearch.surfaces_generated(d, c, it) != d * c * it

    def test_out_of_range_values_answer_for_the_search_built(self):
        """``__init__`` clamps the divisions to >= 2 and the other two to
        >= 1, so the published number has to clamp the same way or it
        answers for a search nobody can build."""
        from ogr_slip2d.search import AutoRefineSearch
        assert AutoRefineSearch.surfaces_generated(0, 0, 0) == 1
        s = AutoRefineSearch(method=None, divisions=0,
                             circles_per_division=0, iterations=0)
        assert (AutoRefineSearch.surfaces_generated(0, 0, 0)
                == math.comb(s.divisions, 2) * s.circles_per_division
                * s.iterations)


# ======================================================================
class TestItIsWhatTheSearchGenerates:
    """The published number against a real run, twice. This is the half
    that cannot rot: change the generator and the counts diverge here."""

    def test_first_set_of_values(self):
        from ogr_slip2d.search import AutoRefineSearch
        r = _run(4, 3, 2)
        assert r.attempts == AutoRefineSearch.surfaces_generated(4, 3, 2)
        assert r.attempts == 36, r.attempts

    def test_second_set_of_values(self):
        from ogr_slip2d.search import AutoRefineSearch
        r = _run(6, 2, 3)
        assert r.attempts == AutoRefineSearch.surfaces_generated(6, 2, 3)
        assert r.attempts == 90, r.attempts

    def test_the_non_circular_variant_generates_the_same_population(self):
        """It subclasses the generation and changes only what reaches the
        solver, so the count it publishes has to be the same one."""
        from ogr_slip2d.search import AutoRefineSearch
        r = _run(4, 3, 2, surface_type="non_circular")
        assert r.attempts == AutoRefineSearch.surfaces_generated(4, 3, 2)


# ======================================================================
class TestTheLabelSaysTheSameNumber:
    """The two ends of the defect, in the same assertion."""

    @staticmethod
    def _app():
        """One QApplication for the process; building a widget without one
        does not raise, it takes the interpreter down."""
        from PySide6.QtWidgets import QApplication
        return QApplication.instance() or QApplication([])

    def _dialog(self, project):
        from ogr_gui.dialogs import SurfaceOptionsDialog
        self._app()
        return SurfaceOptionsDialog(project)

    @staticmethod
    def _numbers(dialog):
        """The figures the label carries, read language-independently."""
        return [int(n) for n in re.findall(r"[0-9]+",
                                           dialog._ar_total_label.text())]

    def test_the_label_carries_the_engine_numbers(self):
        from ogr_slip2d.search import AutoRefineSearch
        d = self._dialog(_project(10, 10, 10))
        # Two sets of values on the SAME dialog: the label used to be
        # written once, when the panel was built, so this also pins that
        # it now follows what the user types.
        for div, cir, nit in ((10, 10, 10), (20, 10, 10)):
            d._ar_div_slope.setValue(div)
            d._ar_circles_per_div.setValue(cir)
            d._ar_num_iter.setValue(nit)
            assert self._numbers(d) == [
                AutoRefineSearch.surfaces_generated(div, cir, nit),
                AutoRefineSearch.surfaces_per_iteration(div, cir),
            ], (div, cir, nit, d._ar_total_label.text())

    def test_it_opens_showing_the_project_values(self):
        from ogr_slip2d.search import AutoRefineSearch
        d = self._dialog(_project(20, 10, 10))
        assert self._numbers(d)[0] == 19000
        d._ar_div_slope.setValue(4)
        d._ar_circles_per_div.setValue(3)
        d._ar_num_iter.setValue(2)
        assert self._numbers(d)[0] == AutoRefineSearch.surfaces_generated(
            4, 3, 2)

    def test_the_label_answers_for_the_search_the_dialog_builds(self):
        """Dialog -> settings -> search, closing the loop the defect
        opened: the panel is only honest if the search built from the
        values it shows generates what it said it would."""
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import AutoRefineSearch
        p = _project(10, 10, 10)
        d = self._dialog(p)
        d._ar_div_slope.setValue(7)
        d._ar_circles_per_div.setValue(4)
        d._ar_num_iter.setValue(3)
        published = self._numbers(d)[0]
        d.apply()
        search = build_search(p, "bishop_simplified")
        assert published == AutoRefineSearch.surfaces_generated(
            search.divisions, search.circles_per_division, search.iterations)
        assert published == math.comb(7, 2) * 4 * 3


# ======================================================================
class TestGeneratedIsNotAnalysed:
    """So that nobody 'fixes' the label into the analysed population,
    which is not knowable before the run."""

    def test_the_published_count_is_an_upper_bound(self):
        from ogr_slip2d.search import AutoRefineSearch
        r = _run(6, 2, 3)
        assert r.total_count <= r.attempts
        assert r.attempts == AutoRefineSearch.surfaces_generated(6, 2, 3)

    def test_the_bank_population_is_the_analysed_one(self):
        """``SearchResult.total_count`` — what the verification bank
        records as ``generadas`` — counts what was analysed: valid plus
        invalid, and neither counts a candidate that never got built."""
        r = _run(6, 2, 3)
        assert r.total_count == r.valid_count + r.invalid_count
