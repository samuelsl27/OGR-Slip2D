# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.256, defect D237 — a Block Search projection-angle pair means one set
of directions, and what the search does with it is said.

Invariants protected:

1. **A pair is the arc it denotes on its own side, in either order.** A
   projection angle is a direction (315° and −45° are one ray), and of the
   two arcs between two directions exactly one avoids the direction that
   side's ray can never take: 0° for the left ray, 180° for the right one.
   So «45 to −45» on the right is [−45, 45], written backwards or not, and
   «315 to 45» is the same arc. Until v0.1.255 the search took
   ``min``/``max`` of the raw numbers, which got the first right and turned
   the second into 45..315 — rays pointing back across the surface.
2. **A pair inside its side's window draws exactly what it drew.** Every
   Block Search model of the verification bank (twelve) has its angles
   inside the windows, so its surfaces are unchanged bit for bit; the draw
   is still one number per side and candidate.
3. **What is not the reference's convention is SAID, not refused** (the
   owner's decision of 2026-10-04). The reference measures the angles
   counter-clockwise with "the Start Angle … LESS than the End Angle", and
   gives 95..175 on the left and 5..85 on the right, extended to 265 on
   the left of a left-facing slope and to −85 on the right of a
   right-facing one, and only there. A reversed pair and an angle outside
   those limits reach the analysis warnings and the API. Which side is the
   face is read from the two ends of the ground, so a vertical face — the
   case the reference draws for the 265° limit — is read right.
4. **Opening Surface Options and pressing OK does not edit the model.**
   The boxes clipped to 0..360 with one decimal: verification problem 109
   came back with its −45 saved as 0, and an angle set through the API
   with more decimals came back rounded.

The limit checks go through ``settings_warnings`` rather than the new rule
function, so that against v0.1.255 they fail by behaviour (no such line)
and not by an import.

COST. Four small Block Search runs of 80 candidates and one dialog. A few
seconds.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_SEED = 3


def _slope(crest_right: bool = True, vertical: bool = False):
    """A 20 m slope, its face inclined at 45° or vertical.

    The crest is on the right as built; ``crest_right=False`` mirrors it
    about x = 30, so the same face looks the other way.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    top_of_face = 20.0 if vertical else 40.0
    pts = [(0.0, 0.0), (60.0, 0.0), (60.0, 30.0), (top_of_face, 30.0),
           (20.0, 10.0), (0.0, 10.0)]
    if not crest_right:
        pts = [(60.0 - x, y) for x, y in pts]
    p = Project("D237")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=20.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    s = p.settings.search
    s.search_method = "block"
    s.surface_type = "non_circular"
    return p


def _set_angles(p, left=None, right=None):
    s = p.settings.search
    if left is not None:
        s.block_left_start_angle_deg, s.block_left_end_angle_deg = left
    if right is not None:
        s.block_right_start_angle_deg, s.block_right_end_angle_deg = right
    return p


def _angle_lines(p):
    from ogr_slip2d.analysis_runner import settings_warnings

    return [w for w in settings_warnings(p, ["bishop_simplified"])
            if "projection angles" in w]


def _outside(p, side):
    return [w for w in _angle_lines(p)
            if w.startswith(f"The {side} projection angles,")
            and "go outside" in w]


def _block_run(left, right, crest_right=True):
    """A small Block Search on the implicit region, as a fingerprint."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.search import BlockSearch

    p = _slope(crest_right)
    s = BlockSearch(method=BishopSimplified(), num_slices=12,
                    num_surfaces=80, seed=_SEED,
                    left_start_angle_deg=left[0], left_end_angle_deg=left[1],
                    right_start_angle_deg=right[0],
                    right_end_angle_deg=right[1])
    r = s.run(p)
    return (r.valid_count, r.invalid_count, r.attempts,
            [(repr(e.fos), [(repr(v.x), repr(v.y))
                            for v in e.surface.polyline.vertices])
             for e in r.evaluations])


# ======================================================================
class TestAPairIsTheArcItDenotes:
    """Invariant 1, on the search itself."""

    def test_315_is_minus_45_on_the_right(self):
        """«315 to 45» and «−45 to 45» are the same rays, so the same run.

        Fails on v0.1.255, which drew from 45..315: rays from straight up
        round to down-right, most of them pointing back over the surface.
        """
        a = _block_run((135.0, 155.0), (315.0, 45.0))
        b = _block_run((135.0, 155.0), (-45.0, 45.0))
        assert a == b

    def test_225_is_minus_135_on_the_left(self):
        """The same on the left: −135° is the ray 225° is."""
        a = _block_run((-135.0, 135.0), (45.0, 45.0))
        b = _block_run((135.0, 225.0), (45.0, 45.0))
        assert a == b

    def test_a_reversed_pair_draws_what_the_straight_one_draws(self):
        """Control (passes on v0.1.255 too): the order never mattered for
        two angles inside their windows, and still does not."""
        a = _block_run((155.0, 135.0), (65.0, 45.0))
        b = _block_run((135.0, 155.0), (45.0, 65.0))
        assert a == b

    def test_the_fingerprint_can_tell_two_ranges_apart(self):
        """Without this the equalities above would pass on a search that
        ignored the angles."""
        a = _block_run((135.0, 155.0), (45.0, 65.0))
        b = _block_run((135.0, 155.0), (25.0, 45.0))
        assert a != b


class TestInsideItsWindowAPairIsUntouched:
    """Invariant 2: ``(min, max)``, exactly, for every pair the bank holds
    and for every pair inside the closed windows."""

    def test_identity_inside_the_windows(self):
        from ogr_core.project.rules import block_projection_range

        lefts = [0.0, 0.5, 95.0, 135.0, 155.0, 175.0, 180.0, 225.0, 265.0,
                 300.0, 359.9, 360.0]
        rights = [-180.0, -85.0, -45.0, -0.1, 0.0, 5.0, 25.0, 45.0, 65.0,
                  85.0, 179.9, 180.0]
        for side, values in (("left", lefts), ("right", rights)):
            for a in values:
                for b in values:
                    assert block_projection_range(a, b, side) == (
                        min(a, b), max(a, b)), (side, a, b)

    def test_the_window_is_closed(self):
        """[0, 360] on the left: 300..360 stays 300..360. A half-open
        window would read 360 as 0 and give 0..300, the opposite arc."""
        from ogr_core.project.rules import block_projection_range

        assert block_projection_range(300.0, 360.0, "left") == (300.0, 360.0)
        assert block_projection_range(-180.0, 180.0, "right") == (
            -180.0, 180.0)

    def test_outside_the_window_only_whole_turns_move(self):
        from ogr_core.project.rules import block_projection_range

        assert block_projection_range(45.0, -45.0, "right") == (-45.0, 45.0)
        assert block_projection_range(315.0, 45.0, "right") == (-45.0, 45.0)
        assert block_projection_range(275.0, 85.0, "right") == (-85.0, 85.0)
        assert block_projection_range(-135.0, 135.0, "left") == (
            135.0, 225.0)
        assert block_projection_range(495.0, 135.0, "left") == (
            135.0, 135.0)


# ======================================================================
class TestTheLimitsAreSaid:
    """Invariant 3, each limit on each side of it, both orientations, an
    inclined and a vertical face."""

    def test_a_reversed_pair_is_said_and_read(self):
        p = _set_angles(_slope(), right=(45.0, -45.0))
        lines = _angle_lines(p)
        reread = [w for w in lines if "were read as -45° to 45°" in w]
        assert len(reread) == 1, lines

    def test_a_straight_pair_inside_the_limits_says_nothing(self):
        """The bank's 007: 135..155 and 45..65 on a left-facing slope."""
        p = _set_angles(_slope(), left=(135.0, 155.0), right=(45.0, 65.0))
        assert _angle_lines(p) == []

    def test_the_downward_left_extension_belongs_to_a_left_facing_slope(self):
        for vertical in (False, True):
            facing_left = _slope(crest_right=True, vertical=vertical)
            facing_right = _slope(crest_right=False, vertical=vertical)
            for p in (facing_left, facing_right):
                _set_angles(p, right=(45.0, 45.0))
            _set_angles(facing_left, left=(135.0, 265.0))
            assert _outside(facing_left, "left") == [], vertical
            _set_angles(facing_left, left=(135.0, 265.1))
            assert len(_outside(facing_left, "left")) == 1, vertical
            _set_angles(facing_right, left=(135.0, 175.0))
            assert _outside(facing_right, "left") == [], vertical
            _set_angles(facing_right, left=(135.0, 175.1))
            assert len(_outside(facing_right, "left")) == 1, vertical

    def test_the_downward_right_extension_belongs_to_a_right_facing_slope(self):
        for vertical in (False, True):
            facing_left = _slope(crest_right=True, vertical=vertical)
            facing_right = _slope(crest_right=False, vertical=vertical)
            for p in (facing_left, facing_right):
                _set_angles(p, left=(135.0, 135.0))
            _set_angles(facing_right, right=(-85.0, 45.0))
            assert _outside(facing_right, "right") == [], vertical
            _set_angles(facing_right, right=(-85.1, 45.0))
            assert len(_outside(facing_right, "right")) == 1, vertical
            _set_angles(facing_left, right=(5.0, 45.0))
            assert _outside(facing_left, "right") == [], vertical
            _set_angles(facing_left, right=(4.9, 45.0))
            assert len(_outside(facing_left, "right")) == 1, vertical

    def test_the_limits_away_from_the_horizontal(self):
        """95 on the left and 85 on the right, for both orientations."""
        for crest_right in (True, False):
            p = _set_angles(_slope(crest_right), left=(95.0, 135.0),
                            right=(45.0, 85.0))
            assert _angle_lines(p) == [], crest_right
            _set_angles(p, left=(94.9, 135.0), right=(45.0, 85.1))
            assert len(_outside(p, "left")) == 1, crest_right
            assert len(_outside(p, "right")) == 1, crest_right

    def test_only_a_block_search_is_told(self):
        p = _set_angles(_slope(), right=(45.0, -45.0))
        p.settings.search.search_method = "path"
        assert _angle_lines(p) == []


class TestTheDoorsSayIt:
    """Invariant 3 at the doors: the analysis and the API."""

    def test_the_analysis_warnings_carry_it(self):
        from ogr_slip2d.analysis_runner import run_analysis

        p = _set_angles(_slope(), right=(45.0, -45.0))
        s = p.settings.search
        s.block_num_surfaces = 20
        p.settings.methods.num_slices = 12
        out = run_analysis(p, ["bishop_simplified"])
        assert any("were read as -45° to 45°" in w for w in out.warnings)

    def test_the_api_returns_it_without_refusing(self):
        from ogr_api import Workspace, call

        ws = Workspace()
        pid = call(ws, "project_new", name="D237")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb", "params": {
                               "cohesion": 3.0, "friction_angle": 19.6}}}]})
        out = call(ws, "settings_set", project_id=pid, changes={
            "search.surface_type": "non_circular",
            "search.search_method": "block",
            "search.block_right_start_angle_deg": 45.0,
            "search.block_right_end_angle_deg": -45.0})
        assert any("were read as -45° to 45°" in w
                   for w in out["warnings"]), out["warnings"]
        assert any("go outside 5° to 85°" in w for w in out["warnings"])
        s = ws.get(pid).project.settings.search
        assert (s.block_right_start_angle_deg,
                s.block_right_end_angle_deg) == (45.0, -45.0)


# ======================================================================
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestThePanelDoesNotRewriteTheModel:
    """Invariant 4. No ``exec()``: the dialog is built and ``apply`` is
    called, which is what OK does."""

    def _dialog(self, p):
        from ogr_gui.dialogs.grid_dialogs import SurfaceOptionsDialog
        _app()
        return SurfaceOptionsDialog(p)

    def test_ok_keeps_the_109_angles_and_an_api_decimal(self):
        """Fails on v0.1.255: −45 came back 0, and 225.25 rounded."""
        p = _set_angles(_slope(), left=(135.0, 225.25), right=(45.0, -45.0))
        d = self._dialog(p)
        d.apply()
        s = p.settings.search
        assert (s.block_left_start_angle_deg, s.block_left_end_angle_deg,
                s.block_right_start_angle_deg,
                s.block_right_end_angle_deg) == (135.0, 225.25, 45.0, -45.0)

    def test_a_touched_box_is_written(self):
        """Control: what the user types still lands."""
        p = _set_angles(_slope(), right=(45.0, -45.0))
        d = self._dialog(p)
        d._b_right_end.setValue(5.0)
        d.apply()
        assert p.settings.search.block_right_end_angle_deg == 5.0

    def test_the_panel_says_it_under_the_boxes(self):
        p = _set_angles(_slope(), right=(45.0, -45.0))
        d = self._dialog(p)
        text = d._b_angle_note.text()
        assert "read as -45° to 45°" in text
        assert "goes outside 5° to 85°" in text
        d._b_right_start.setValue(5.0)
        d._b_right_end.setValue(45.0)
        assert d._b_angle_note.text() == ""

    def test_the_panel_says_it_in_spanish(self):
        from ogr_gui import i18n

        before = i18n.current_language()
        try:
            i18n.set_language("es")
            p = _set_angles(_slope(), right=(45.0, -45.0))
            d = self._dialog(p)
            text = d._b_angle_note.text()
            assert "Proyección derecha" in text
            assert "leída como -45° a 45°" in text
        finally:
            i18n.set_language(before)
