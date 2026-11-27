# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""A surface refused because an end daylights outside the Slope Limits is the
reference's -113 (v0.1.496, D435).

THE INVARIANT THIS FILE PROTECTS is that the census files every surface the
Slope Limits refuse under -113, and nothing else there. The reference's help
(its summary of error codes) defines -113 as a slip surface that intersects
the External Boundary outside of the user-defined Slope Limits but within the
default ones, and -101 for one that does not intersect within the default
ones either. The default limits are the ends of the ground profile, and a
surface refused by the user's limits always cuts the ground within them: a
circle that cuts it nowhere is refused before, as one that misses the ground
(or, from a grid centre with no valid radius, as -1000, D434). So the rule is
the owner's option B: -113 for every refusal of the limits. The second test
checks that premise on every refused circle, geometrically.

Until this version these surfaces were -101, on the reading that the
reference does not code them; two comments said so, and are gone.

THE CASE: Ej_1's reference grid (4851 circles, Ordinary, in series) with
Slope Limits from 30 to 90 (the profile runs from 0 to 120). Measured on
0.1.495: 611 surfaces refused by the limits, of which 484 are circles of
centres with no valid radius (x >= 92: the nearest point of the slope
surface is then the limit point (90, y)), which D434 files under -1000; the
other 127 are this file's. By code: {-1000: 1254, -113: 127, -111: 261,
-103: 1}, and no -101 at all, where 0.1.485 gave -101: 1381.

Cost: the grid once, about 4 s; it is the reference's grid.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_LIMITS = (30.0, 90.0)
_RUN: dict = {}


def _ej1_with_limits():
    """``(result, refused)``: the run, and every circle whose evaluation
    recorded the refusal of the Slope Limits."""
    if not _RUN:
        from test_slide_validation_ej1 import _GRID, _ej1_project
        import ogr_slip2d.search as S
        from ogr_slip2d.methods import get_method
        p = _ej1_project()
        p.settings.advanced.parallel_search = False
        refused = []
        real = S.GridSearch.evaluate_circle

        def spy(self, project, circle):
            n = getattr(self, "_outside_slope_limits", 0) or 0
            out = real(self, project, circle)
            if (getattr(self, "_outside_slope_limits", 0) or 0) > n:
                refused.append(circle)
            return out

        S.GridSearch.evaluate_circle = spy
        try:
            sr = S.GridSearch(method=get_method("ordinary_fellenius")(),
                              slope_limits=_LIMITS, **_GRID).run(p)
        finally:
            S.GridSearch.evaluate_circle = real
        _RUN.update(sr=sr, refused=refused, project=p)
    return _RUN["sr"], _RUN["refused"], _RUN["project"]


class TestTheLimitsAre113:

    def test_every_refusal_of_the_limits_is_113(self):
        from ogr_slip2d.interpretation import (ERROR_SLOPE_LIMITS,
                                               invalid_summary)
        sr, _refused, _p = _ej1_with_limits()
        assert ERROR_SLOPE_LIMITS == -113
        assert sr.outside_slope_limits > 0
        by_code = invalid_summary(sr)["by_code"]
        assert by_code.get(-113) == sr.outside_slope_limits, by_code
        # and nothing of theirs is left under -101
        assert -101 not in by_code, by_code

    def test_the_premise_each_one_cuts_the_ground_within_the_profile(self):
        """Option B rests on it: inside the default limits, so -113 and
        never the -101 of a surface outside both. Every circle the limits
        refused, the grid's own included before D434 took some of them,
        crosses the ground twice and inside the profile. (Not necessarily
        outside the user's limits there: the limits judge the ends of the
        BASE of the mass, and a circle whose centre lies below the ground,
        such as (40, 30) R 20.12, crosses it at 37.8 and 42.2 while its base
        runs from 19.9 to 60.1 along the lower arc.)"""
        from ogr_core.geometry.ground import ground_surface
        _sr, refused, p = _ej1_with_limits()
        ground = ground_surface(p.external_boundary())
        lo = min(v.x for v in ground.vertices)
        hi = max(v.x for v in ground.vertices)
        assert len(refused) > 100, len(refused)
        for c in refused:
            chords = c.candidate_chords(ground)
            assert chords, c
            for x_l, x_r in chords:
                assert lo - 1e-9 <= x_l <= hi + 1e-9, c
                assert lo - 1e-9 <= x_r <= hi + 1e-9, c

    def test_the_view_of_the_agent_and_the_comments(self):
        from ogr_slip2d.interpretation import ERROR_CODES
        assert "Slope Limits" in ERROR_CODES[-113]
        root = Path(__file__).resolve().parent.parent / "ogr_slip2d"
        assert "has no code of its own there" not in (
            root / "search.py").read_text(encoding="utf-8")
