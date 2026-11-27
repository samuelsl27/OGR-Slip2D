# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The circles of a grid centre with no valid radius are the reference's
-1000 (v0.1.495, D434).

THE INVARIANT THIS FILE PROTECTS is that the census codes a circle the grid
emits at a centre with no valid radius as -1000, "no valid slip surface is
generated", whatever refused it, and moves nothing else: not a factor of
safety, not a count of valid surfaces, not the population.

THE REFERENCE IS EXTERNAL: the error-code table of Ej_1 published in the
reference's report (``EJ1`` of ``test_m_alpha_screening_v1189``), 231 -1000 in
each of its seven methods and no -101. On Ej_1's reference grid (4851 circles)
those 231 are the column of centres x = 120, the right end of the profile: 21
centres, each with its 11 identical radii (the distance down to the ground at
elevation 25). Until this version the census filed them as -101 circles that
"do not cut the ground twice".

A centre has no valid radius in two ways (``search._NoValidRadius``): with
one window of Slope Limits when the nearest point of the slope surface is a
limit point (d_min = d_max), and with two when no radius is valid or the two
ends of the range cross. The second is measured on the bank's wall grid (its
problem 87): 43 centres, 2623 circles, all refused, which is what the
reference documents for its own grid; it is not here because the bank is not
part of the repository. Here, D77's wall of ``test_slope_limit_refusals_v1261``.

Cost: Ej_1's grid in series twice (the run and the run with the census of
0.1.494), about 8 s: it is the reference's grid, and its population is the
invariant. The wall, under a second.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_RUNS: dict = {}


def _ej1(old_census=False):
    """Ej_1's reference grid, Ordinary, in series; with ``old_census`` the
    circles of a centre with no valid radius go through ``evaluate_circle``
    as they did until this version (the census of 0.1.494)."""
    if old_census not in _RUNS:
        from test_slide_validation_ej1 import _GRID, _ej1_project
        import ogr_slip2d.search as S
        from ogr_slip2d.methods import get_method
        p = _ej1_project()
        p.settings.advanced.parallel_search = False
        kept = S.GridSearch._evaluate_without_radius
        if old_census:
            S.GridSearch._evaluate_without_radius = S.GridSearch.evaluate_circle
        try:
            search = S.GridSearch(method=get_method("ordinary_fellenius")(),
                                  **_GRID)
            _RUNS[old_census] = search.run(p), search, p
        finally:
            S.GridSearch._evaluate_without_radius = kept
    return _RUNS[old_census]


class TestEj1PublishesThem:

    def test_231_under_1000_as_the_reference(self):
        from test_m_alpha_screening_v1189 import EJ1
        from ogr_slip2d.interpretation import ERROR_NO_SURFACE, invalid_summary
        published = {row[-1][-1000] for row in EJ1.values()}
        assert published == {231}, published
        sr, _s, _p = _ej1()
        census = invalid_summary(sr)
        assert ERROR_NO_SURFACE == -1000
        assert census["by_code"].get(-1000) == 231, census["by_code"]
        assert sr.no_valid_radius == 231 and sr.misses_ground == 0

    def test_they_are_the_centres_with_no_valid_radius(self):
        """The 231 are the 21 centres of x = 120, the right end of the
        profile, with their eleven radii each, and every one of those
        centres is marked."""
        from ogr_slip2d.search import _NoValidRadius
        _sr, search, p = _ej1()
        pts = search._slope_surface(p)
        xs = [40.0 + 4.0 * i for i in range(21)]
        ys = [30.0 + 4.5 * j for j in range(21)]
        marked = [(x, y) for x in xs for y in ys
                  if type(search._radius_bracket(x, y, pts)) is _NoValidRadius]
        assert len(marked) == 21 and {x for x, _ in marked} == {120.0}, marked
        for x, y in marked:
            r_min, r_max = search._radius_bracket(x, y, pts)
            assert r_min == r_max and abs(r_min - (y - 25.0)) < 1e-9, (x, y)

    def test_they_left_the_101_and_nothing_else_moved(self):
        """Against the census of 0.1.494, in the same process: the -101
        loses exactly the 231 the -1000 gains, and the population, the
        valid surfaces and the critical factor are the same to the bit."""
        new, _s, _p = _ej1()
        old, _s2, _p2 = _ej1(old_census=True)
        from ogr_slip2d.interpretation import invalid_summary
        a, b = invalid_summary(new)["by_code"], invalid_summary(old)["by_code"]
        assert old.misses_ground == 231 and old.no_valid_radius == 0
        assert b.get(-101, 0) - a.get(-101, 0) == 231, (a, b)
        assert {k: v for k, v in a.items() if k not in (-101, -1000)} == {
            k: v for k, v in b.items() if k != -101}
        assert new.total_count == old.total_count == 4851
        assert new.valid_count == old.valid_count
        assert new.critical.fos == old.critical.fos


class TestTheWallOfTwoWindows:
    """D77's wall: centres with no valid radius under two windows."""

    def test_every_circle_of_a_marked_centre_is_refused_and_counted(self):
        from test_slope_limit_refusals_v1261 import _ENTRY, _EXIT, _grid, _wall
        from ogr_slip2d.interpretation import invalid_summary
        r = _grid((_EXIT, _ENTRY), grid_x=(-24.0, -22.1), grid_y=(15.0, 16.8),
                  grid_nx=2, grid_ny=2, radius_increment=2,
                  min_area=2.0).run(_wall())
        assert r.total_count == 27 and r.valid_count == 0
        assert r.no_valid_radius == 27
        assert invalid_summary(r)["by_code"] == {-1000: 27}

    def test_the_view_of_the_agent_lists_the_code(self):
        from ogr_slip2d.interpretation import ERROR_CODES
        assert -1000 in ERROR_CODES
        assert "no valid slip surface" in ERROR_CODES[-1000]
