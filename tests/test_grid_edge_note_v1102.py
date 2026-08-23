# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A minimum on the edge of the grid has to say so.

WHAT INVARIANT THIS PROTECTS. A Grid Search returns the lowest factor of
safety among the centres it swept. When the winning centre sits ON the
perimeter of that grid, the answer is not a minimum: it is the best of what
was looked at, and the true one may well lie outside. Nothing said so, and
the cost of not being told is measured, not supposed — verification problem
77 of the reference bank, one and the same model:

    grid ending at x = 900   minimum AT x = 900    1.757   (+11 %)
    grid widened to 1400     minimum at x = 1019   1.587   (+0.2 %)

Eleven per cent, on the unsafe side of nothing: the run looked converged.
The back-analysis problem 37 does the same on its left edge.

This is a REPORTING note, like the daylight-tangent one: nothing in the
analysis changes on either side of it, and no factor of safety is asserted
here. What is asserted is that the note appears exactly when the geometry
says it should and stays quiet otherwise — a warning that fires on every run
teaches the reader to skip warnings.

THE ABSTENTION MATTERS AS MUCH AS THE NOTE. A grid with no extent on one
axis puts every centre on that perimeter by construction, so a check that
spoke there would be reporting its own arithmetic rather than anything about
the model.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: Where the minimum of this model lands with a grid wide enough not to
#: clip it. Not asserted as a value — it is only used to place a grid edge
#: exactly on it, which is what makes the note fire.
_MINIMUM_AT_X = 30.0


def _slope(grid_x, grid_y):
    """The same 12 m slope on 10 m of foundation the filter tests use."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    H = 12.0
    beta = math.radians(30.96)
    toe = 30.0
    crest = toe + H / math.tan(beta)
    base = -10.0
    ext = Polyline(vertices=[
        Vertex(0, base), Vertex(60, base), Vertex(60, H),
        Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("grid edge")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    s = p.settings.search
    s.search_method = "grid"
    s.grid_x_min, s.grid_x_max = grid_x
    s.grid_y_min, s.grid_y_max = grid_y
    s.grid_nx = s.grid_ny = 8
    s.radius_increment = 8
    p.settings.methods.num_slices = 20
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    return p


_CACHE: dict = {}


def _warnings(grid_x, grid_y):
    key = (grid_x, grid_y)
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import run_analysis
        out = run_analysis(_slope(grid_x, grid_y), ["bishop_simplified"])
        notes = [w for w in out.warnings if "edge of the search grid" in w]
        _CACHE[key] = (out, notes)
    return _CACHE[key]


# ======================================================================
class TestTheNoteFiresWhenItShould:

    def test_a_grid_clipped_at_its_own_minimum_is_reported(self):
        """The grid starts exactly where the wide-grid minimum sits, so
        the answer has nowhere further left to go."""
        _out, notes = _warnings((_MINIMUM_AT_X, 60.0), (15.0, 40.0))
        assert notes, "the minimum came off the grid edge and nothing said so"
        assert "x = 30" in notes[0], notes[0]

    def test_the_note_names_the_grid_it_is_talking_about(self):
        """A note the reader cannot act on is half a note: it has to say
        which grid, or widening it is guesswork."""
        _out, notes = _warnings((_MINIMUM_AT_X, 60.0), (15.0, 40.0))
        assert "30 to 60" in notes[0], notes[0]
        assert "15 to 40" in notes[0], notes[0]

    def test_it_is_attributed_to_the_method_that_produced_it(self):
        _out, notes = _warnings((_MINIMUM_AT_X, 60.0), (15.0, 40.0))
        assert notes[0].startswith("bishop_simplified: "), notes[0]


# ======================================================================
class TestTheNoteStaysQuietWhenItShould:

    def test_a_grid_wide_enough_says_nothing(self):
        """Same model, same everything, 10 m more grid on the left."""
        _out, notes = _warnings((20.0, 60.0), (15.0, 40.0))
        assert not notes, notes

    def test_the_wide_grid_really_did_find_its_minimum_inside(self):
        """Otherwise the test above would be passing on a broken check
        rather than on a grid that contains its answer."""
        out, _notes = _warnings((20.0, 60.0), (15.0, 40.0))
        crit = out.results["bishop_simplified"].critical
        assert 20.0 < crit.surface.centre_x < 60.0
        assert 15.0 < crit.surface.centre_y < 40.0

    def test_a_grid_with_no_extent_on_one_axis_abstains(self):
        """Every centre of a single-row grid is on its own perimeter, so
        speaking there would be a note about arithmetic, not about the
        model — and one that fired on every such run."""
        _out, notes = _warnings((20.0, 60.0), (27.5, 27.5))
        assert not notes, notes


# ======================================================================
class TestOtherSearchesAreNotAffected:

    def test_a_search_with_no_grid_produces_no_note(self):
        """Only a Grid Search has a perimeter to fall off. The note reads
        an attribute the other five never set, and must answer nothing
        rather than raise."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.analysis_runner import grid_edge_note
        from ogr_slip2d.search import SlopeSearch
        p = _slope((20.0, 60.0), (15.0, 40.0))
        search = SlopeSearch(method=BishopSimplified(), num_surfaces=120,
                             num_slices=20, seed=42)
        result = search.run(p)
        assert grid_edge_note(search, result) == []

    def test_a_grid_search_that_has_not_run_yet_produces_no_note(self):
        """The grid actually swept is only known after the run: with no
        user grid it comes from the model's own bounding box."""
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.analysis_runner import grid_edge_note
        search = GridSearch(method=BishopSimplified())
        assert search.grid_x_used is None
        assert grid_edge_note(search, None) == []
