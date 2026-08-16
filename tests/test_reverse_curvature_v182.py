# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.82 — Reverse-curvature circles and their vertical tension crack.

**The invariant.** A circular slip surface whose ground entry point lies
ABOVE its own centre has part of its arc above the centre elevation, so
the arc reverses direction and the surface overhangs. Such a surface
cannot exist. The reference program resolves it in one of two documented
ways, selected by *Create tension crack for reverse curvature*:

* checked — a **vertical tension crack** is created where the surface
  elevation equals the centre elevation, which on a circle is the point
  of vertical tangency, ``x = x_c ∓ R``;
* unchecked — the surface is **discarded**.

**Why this file exists.** ``create_tension_crack_reverse_curvature`` was
stored in the project, editable in the Surface Options dialog, and read by
NO code in ``ogr_slip2d`` (project rule 7: a setting that does nothing is
worse than no setting, because the user believes the analysis honours it).
Meanwhile the endpoint was taken at the true ground crossing, which sits
in the upper quadrant of the circle, while the base was drawn on the LOWER
arc — for the circle below, 16 m beneath the ground surface.

**The reference values** come from the same Slide run as the rest of the
Ej_1 benchmark (``referencias/Ejemplos/Ej_1/``), read off two Add Query
screenshots of that model:

    c = (68.000, 34.500)  R = 13.519  →  FS = 1.588
    c = (72.000, 34.500)  R = 10.803  →  FS = 1.330

Before the fix the first of those came out at 2.0757 — **30.7 % high**.
On the reference 20×20 grid, 522 of the 4851 circles are affected.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.slicer import (  # noqa: E402
    _ground_surface_from_external,
    slice_surface,
)
from ogr_slip2d.surface import SlipCircle  # noqa: E402

# (centre_x, centre_y, radius, reference FS)
_REVERSED = [
    (68.0, 34.5, 13.519, 1.588),
    (72.0, 34.5, 10.803, 1.330),
]
# A circle high above the model: no reverse curvature, and its reference
# value is the control that says the fix did not disturb ordinary circles.
_NORMAL = (40.0, 120.0, 80.091, 6.397)


def _fos(project, cx, cy, r, num_slices=25):
    ev = GridSearch(method=BishopSimplified(), num_slices=num_slices,
                    min_area=0.0)
    return ev.evaluate_circle(project, SlipCircle(centre_x=cx, centre_y=cy,
                                                  radius=r))


# ======================================================================
class TestReverseCurvatureGeometry:
    def test_crack_sits_at_the_vertical_tangent(self):
        """``x = x_c − R`` exactly — the point where the tangent is
        vertical, i.e. where the surface elevation equals the centre
        elevation. This is the geometric content of the reference's
        wording, and getting it a metre wrong is what the old code did."""
        p = _ej1_project()
        ground = _ground_surface_from_external(p.external_boundary())
        c = SlipCircle(centre_x=68.0, centre_y=34.5, radius=13.519)
        assert c.intersect_with_ground(ground) is not None
        # The raw crossing is on the UPPER arc, 8.2 m above the centre.
        assert abs(c.x_left - 57.2727) < 1e-3, c.x_left
        assert c.apply_reverse_curvature(ground, "tension_crack") is True
        assert abs(c.x_left - (68.0 - 13.519)) < 1e-9, c.x_left
        assert c.reverse_curvature is True
        (x, y_bot, y_top), = c.tension_cracks
        assert abs(x - 54.481) < 1e-9
        assert abs(y_bot - 34.5) < 1e-9
        # The slope face is y = 100 − x between (50, 50) and (75, 25).
        assert abs(y_top - (100.0 - 54.481)) < 1e-6, y_top

    def test_ordinary_circle_is_untouched(self):
        p = _ej1_project()
        ground = _ground_surface_from_external(p.external_boundary())
        cx, cy, r, _ref = _NORMAL
        c = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
        c.intersect_with_ground(ground)
        before = (c.x_left, c.x_right)
        assert c.apply_reverse_curvature(ground, "tension_crack") is True
        assert (c.x_left, c.x_right) == before
        assert c.reverse_curvature is False
        assert c.tension_cracks == []

    def test_crack_survives_serialisation(self):
        """The canvas draws the vertical segment from the dict, so the
        crack has to travel with it."""
        p = _ej1_project()
        ground = _ground_surface_from_external(p.external_boundary())
        c = SlipCircle(centre_x=68.0, centre_y=34.5, radius=13.519)
        c.intersect_with_ground(ground)
        c.apply_reverse_curvature(ground, "tension_crack")
        back = SlipCircle.from_dict(c.to_dict())
        assert back.reverse_curvature is True
        assert back.tension_cracks == c.tension_cracks
        assert abs(back.x_left - c.x_left) < 1e-12


# ======================================================================
class TestReverseCurvatureAgainstTheReference:
    def test_reference_factors_of_safety(self):
        """Rule 1: validated against an external value, not a snapshot of
        what this code prints today."""
        p = _ej1_project()
        for cx, cy, r, ref in _REVERSED:
            res = _fos(p, cx, cy, r)
            assert res is not None, (cx, cy, r)
            err = abs(res.fos - ref) / ref * 100
            assert err < 2.0, f"c=({cx},{cy}) R={r}: {res.fos:.4f} vs {ref} ({err:.2f} %)"

    def test_the_error_it_removes_is_large(self):
        """Pins the size of the defect, so a regression that silently
        restores the old endpoint cannot hide inside a loose tolerance:
        the first circle used to be 30.7 % high."""
        p = _ej1_project()
        res = _fos(p, 68.0, 34.5, 13.519)
        assert res.fos < 1.7, res.fos          # old value was 2.0757

    def test_ordinary_circle_still_matches(self):
        p = _ej1_project()
        cx, cy, r, ref = _NORMAL
        res = _fos(p, cx, cy, r)
        assert abs(res.fos - ref) / ref < 0.01, res.fos


# ======================================================================
class TestTheSettingMovesTheNumber:
    """Rule 7. Both branches of the checkbox must be observable."""

    def test_unchecked_discards_the_surface(self):
        p = _ej1_project()
        p.settings.search.create_tension_crack_reverse_curvature = False
        c = SlipCircle(centre_x=68.0, centre_y=34.5, radius=13.519)
        assert slice_surface(p, c, num_slices=25) is None

    def test_checked_analyses_it(self):
        p = _ej1_project()
        p.settings.search.create_tension_crack_reverse_curvature = True
        c = SlipCircle(centre_x=68.0, centre_y=34.5, radius=13.519)
        sl = slice_surface(p, c, num_slices=25)
        assert sl is not None
        assert len(sl) == 25

    def test_the_two_branches_disagree_on_the_grid(self):
        """A coarse grid over the reverse-curvature region: switching the
        option off must remove surfaces, not merely change a flag."""
        p = _ej1_project()
        kw = dict(grid_x=(60, 90), grid_y=(30, 45), grid_nx=4, grid_ny=4,
                  radius_increment=6, min_radius=2.0, num_slices=18,
                  min_area=0.5)
        p.settings.search.create_tension_crack_reverse_curvature = True
        on = GridSearch(method=BishopSimplified(), **kw).run(p)
        p.settings.search.create_tension_crack_reverse_curvature = False
        off = GridSearch(method=BishopSimplified(), **kw).run(p)
        assert on.valid_count > off.valid_count, (on.valid_count,
                                                  off.valid_count)


# ======================================================================
class TestTheCountAddsUp:
    """v0.1.83 — every circle the search GENERATES has to appear in the
    totals, valid or not.

    ``GridSearch.run`` used to skip the counters entirely when a circle
    could not be analysed, so 1697 of the 4851 circles of this grid simply
    vanished: the window reported "2966 / 3154" for a population of 4851.
    Worse, the denominator MOVED when a search option changed — 2633 with
    reverse curvature switched off — which is the one thing a number the
    user compares between runs must never do.

    The reference documents the population as an exact identity (*Grid
    Search*): (X intervals + 1) × (Y intervals + 1) × (Radius Increment +
    1). That is what is asserted here — rule 1, an identity from the
    reference, not a snapshot of what the code prints.
    """

    # 21 × 21 × 11, the reference's own arithmetic for this grid.
    _GENERATED = 21 * 21 * 11          # = 4851

    @staticmethod
    def _run(project):
        return GridSearch(method=BishopSimplified(), grid_x=(40, 120),
                          grid_y=(30, 120), grid_nx=20, grid_ny=20,
                          radius_increment=10, min_radius=2.0,
                          num_slices=25, min_area=0.5).run(project)

    def test_valid_plus_invalid_is_every_circle_generated(self):
        p = _ej1_project()
        r = self._run(p)
        assert r.total_count == self._GENERATED, (
            r.valid_count, r.invalid_count, r.total_count)

    def test_the_denominator_does_not_move_with_the_setting(self):
        """The property that makes the number comparable at all."""
        p = _ej1_project()
        p.settings.search.create_tension_crack_reverse_curvature = True
        on = self._run(p)
        p.settings.search.create_tension_crack_reverse_curvature = False
        off = self._run(p)
        assert on.total_count == off.total_count == self._GENERATED
        # The split moves, which is the setting doing its job...
        assert on.valid_count > off.valid_count
        # ...and every surface it removes is accounted for on the other
        # side rather than disappearing.
        assert (off.invalid_count - on.invalid_count
                == on.valid_count - off.valid_count)

    def test_evaluations_is_not_the_denominator(self):
        """Pins why ``total_count`` had to exist: a surface with no
        LEMResult is still a surface that was generated."""
        p = _ej1_project()
        r = self._run(p)
        assert len(r.evaluations) < r.total_count


# ======================================================================
class TestGlobalMinimumUnaffected:
    """The regression that matters: the reference critical circle enters
    the ground BELOW its own centre (45.470, 50.0 against y_c = 70.5), so
    it is not a reverse-curvature surface and nothing about it may move."""

    def test_reference_critical_circle_unchanged(self):
        p = _ej1_project()
        res = _fos(p, 88.0, 70.5, 47.212)
        assert abs(res.fos - 0.882889) / 0.882889 < 0.005, res.fos

    def test_grid_search_still_finds_it(self):
        p = _ej1_project()
        gs = GridSearch(method=BishopSimplified(), grid_x=(40, 120),
                        grid_y=(30, 120), grid_nx=20, grid_ny=20,
                        radius_increment=10, min_radius=2.0,
                        num_slices=25, min_area=0.5)
        r = gs.run(p)
        sd = r.critical.surface.to_dict()
        assert abs(sd["centre_x"] - 88.0) < 1e-6, sd["centre_x"]
        assert abs(sd["centre_y"] - 70.5) < 1e-6, sd["centre_y"]
        assert abs(r.critical.fos - 0.882889) / 0.882889 < 0.01, \
            r.critical.fos
        assert r.critical.surface.reverse_curvature is False
