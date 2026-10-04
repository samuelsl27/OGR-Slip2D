# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A support type measured from its crest is read from the higher end, decided
to a relative tolerance, by the engine and by the interface alike (D97).

WHAT INVARIANT THIS PROTECTS. A retaining wall's pressure diagram and an
Ito–Matsui pile's soil pressure are defined from the CREST of the support
(``MEASURED_FROM_TOP``), so which end is the crest is geometry, not drawing
order — and a level support has no crest and is refused (``no_crest``). Until
v0.1.254 that rule was broken four ways:

* level was decided by ``tail.y == head.y``, EXACTLY: a wall 1e-12 of its
  length off level skipped the refusal and was measured from whichever end
  rounding made higher — the number the refusal exists to prevent;
* a pile drawn bottom to top was handed a distance from the crest but
  integrated its profile from the head, i.e. from its TIP: on the case of
  Cai and Ugai (2000), 810.45 kN/m against 152.59 kN/m drawn top to bottom,
  and Bishop 3.034 against 1.507, on the unsafe side;
* the canvas tooltip and the support force diagram read from the head
  whatever the type, so their numbers were not the engine's for a support
  drawn bottom to top, and they gave numbers for a level support the
  analysis leaves out;
* the EFP wall note asked ``head.y == tail.y`` again, and its singular
  sentence had no verb.

WHY THESE ANCHORS. None of the numbers below is a value this code printed.

* THE IDENTITY: a support drawn bottom to top is the same support. Force,
  point of application and factor of safety equal to 1e-12 (the samples of
  the profile sit at symmetric midpoints, so the equality is one of
  rounding).
* THE CLOSED FORM of ``test_ito_matsui_pile_v1123``: in one material the
  pressure is linear in depth, so the force to the cut is
  ``(q0 d + (q1 - q0) d^2 / 2) / D1`` from Ito and Matsui's equation, with d
  measured from the top of the pile — for the pile drawn either way.
* RULE 7 the other way round: the tolerance must not swallow a real tilt.
  1e-3 of the length off level is a crest, priced from the higher end in
  both drawing orders, and the wall then moves the factor.

The near-level wall here is placed where the circle CUTS it. The horizontal
wall of ``test_efp_wall_v1122`` (41.5 to 45.5 at y = 8.1) is never crossed by
its circle, which meets y = 8.1 at x = 46.92, so its refusal is never asked:
the premise is asserted here instead of assumed.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# --- the slope of test_efp_wall_v1122 ---------------------------------
H, TOE, CREST = 12.0, 30.0, 50.0
XW = 43.5
YW_TOP = (XW - TOE) * H / (CREST - TOE)     # 8.1, the ground at the wall
LW, EFP = 5.0, 6.0
_WALL_SLICES = 25
# A near-level wall under the face, crossed by the circle (38, 26, 20) at
# x = 38 + sqrt(111) = 48.54, 6.46 from its right end.
_LX0, _LX1, _LY = 45.5, 55.0, 9.0

# --- Cai and Ugai (2000), as test_ito_matsui_pile_v1123 ----------------
GAMMA, COH, PHI_DEG = 20.0, 10.0, 20.0
DIAM = 0.8
PILE_X, PILE_TOP, PILE_BOT = 17.5, 15.0, 0.0
EXTERNAL = [(0.0, 0.0), (35.0, 0.0), (35.0, 20.0), (25.0, 20.0),
            (10.0, 10.0), (0.0, 10.0)]
_PILE_SLICES = 40


def _close(a, b, tol=1e-12):
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


# ======================================================================
# The wall
# ======================================================================
def _wall_circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)


def _wall_project(head=None, tail=None, flip=False, with_wall=True):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  RetainingWallEFP, SupportInstance)
    p = Project("efp")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="S", unit_weight=18,
        strength=MohrCoulomb(cohesion=8.0, friction_angle=20.0))]
    if not with_wall:
        return p
    p.support_types = [RetainingWallEFP(profile_type="triangular", efp=EFP,
                                        force_location="intersection")]
    if head is None:
        top, bot = Vertex(XW, YW_TOP), Vertex(XW, YW_TOP - LW)
        head, tail = (bot, top) if flip else (top, bot)
    p.supports = [SupportInstance(
        type_id="retaining_wall_efp", head=head, tail=tail,
        force_application=ForceApplication.ACTIVE,
        orientation=ForceOrientation.HORIZONTAL)]
    return p


def _near_level(offset, right_end_higher=True, reverse=False):
    """The wall of ``_LX0``..``_LX1`` at ``_LY``, one end ``offset`` of the
    length higher, drawn left to right or (``reverse``) right to left."""
    from ogr_core.geometry import Vertex
    d = offset * (_LX1 - _LX0)
    left = Vertex(_LX0, _LY + (0.0 if right_end_higher else d))
    right = Vertex(_LX1, _LY + (d if right_end_higher else 0.0))
    head, tail = (right, left) if reverse else (left, right)
    return _wall_project(head=head, tail=tail)


def _effects(project, surface, num_slices):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(project, surface, num_slices=num_slices)
    reasons = []
    eff = compute_support_effects(project, surface, sl, reasons=reasons)
    return eff, reasons, sl


def _fos(project, surface, num_slices, method="bishop_simplified"):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None and sl.slices
    return method_registry()[method]().compute_fos(project, surface, sl).fos


# ======================================================================
# The pile
# ======================================================================
def _pile_project(reverse=False, location="intersection"):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  PileMicropile, SupportInstance)
    p = Project("ito-matsui")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in EXTERNAL], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", unit_weight=GAMMA, sat_unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=COH, friction_angle=PHI_DEG),
        pore_pressure=PorePressureType.NONE)]
    p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
    p.support_types = [PileMicropile(
        failure_mode="ito_matsui", out_of_plane_spacing=3.0 * DIAM,
        pile_diameter=DIAM, force_location=location)]
    top, bot = Vertex(PILE_X, PILE_TOP), Vertex(PILE_X, PILE_BOT)
    head, tail = (bot, top) if reverse else (top, bot)
    p.supports = [SupportInstance(
        type_id="pile_micropile", head=head, tail=tail,
        orientation=ForceOrientation.PERPENDICULAR_TO_PILE,
        force_application=ForceApplication.PASSIVE)]
    return p


def _pile_circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=10.5, centre_y=29.0, radius=19.0)


def _app():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class _Crit:
    pass


def _critical(project, surface, num_slices):
    from ogr_slip2d.slicer import slice_surface
    c = _Crit()
    c.surface = surface
    c.slices = slice_surface(project, surface, num_slices=num_slices)
    return c


# ======================================================================
class TestLevelIsATolerance:

    def test_the_premise_the_circle_cuts_the_near_level_wall(self):
        eff, reasons, _sl = _effects(_near_level(1e-3), _wall_circle(),
                                     _WALL_SLICES)
        assert len(eff) == 1 and eff[0].force_magnitude > 50.0, (eff, reasons)

    def test_1e_12_of_the_length_is_level_in_both_senses(self):
        """Refused with ``no_crest`` whichever end is higher and whichever
        way it is drawn, and the factor is the one of the wall drawn
        EXACTLY level — the refusal every version agrees on."""
        from ogr_slip2d.support_integration import SUPPORT_NO_CREST
        bare = _fos(_near_level(0.0), _wall_circle(), _WALL_SLICES)
        assert _close(bare, _fos(_wall_project(with_wall=False),
                                 _wall_circle(), _WALL_SLICES))
        for right_higher in (True, False):
            for reverse in (False, True):
                p = _near_level(1e-12, right_higher, reverse)
                eff, reasons, _sl = _effects(p, _wall_circle(), _WALL_SLICES)
                assert eff == [], (right_higher, reverse, eff)
                assert any(r == SUPPORT_NO_CREST for _sid, r in reasons), (
                    right_higher, reverse, reasons)
                f = _fos(p, _wall_circle(), _WALL_SLICES)
                assert _close(f, bare), (right_higher, reverse, f, bare)

    def test_1e_3_of_the_length_is_a_crest_and_moves_the_number(self):
        """Priced from the higher end in both drawing orders — the same
        force — and the wall then changes the factor."""
        bare = _fos(_wall_project(with_wall=False), _wall_circle(),
                    _WALL_SLICES)
        forces, factors = [], []
        for reverse in (False, True):
            p = _near_level(1e-3, True, reverse)
            eff, reasons, _sl = _effects(p, _wall_circle(), _WALL_SLICES)
            assert len(eff) == 1, (reverse, reasons)
            forces.append(eff[0].force_magnitude)
            factors.append(_fos(p, _wall_circle(), _WALL_SLICES))
        assert _close(forces[0], forces[1]), forces
        assert _close(factors[0], factors[1]), factors
        assert not _close(factors[0], bare, 1e-6), (factors, bare)

    def test_the_tolerance_is_relative_to_the_length(self):
        """The same drawing in metres and in millimetres: the same answer."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import SupportInstance
        for scale in (1.0, 1000.0):
            for off, level in ((1e-12, True), (1e-3, False)):
                s = SupportInstance(
                    type_id="retaining_wall_efp",
                    head=Vertex(0.0, 0.0),
                    tail=Vertex(10.0 * scale, 10.0 * scale * off))
                assert s.is_level() is level, (scale, off)


class TestTheNoteAsksTheSamePredicate:

    def test_the_note_names_exactly_what_the_engine_refuses(self):
        from ogr_slip2d.retaining_wall_notes import retaining_wall_notes
        notes = retaining_wall_notes(_near_level(1e-12))
        assert len(notes) == 1, notes
        assert notes[0].startswith(
            "1 retaining wall is drawn horizontally."), notes[0]
        assert retaining_wall_notes(_near_level(1e-3)) == []


class TestAPileDrawnBottomToTop:

    def test_it_is_the_same_pile(self):
        """Force, factor and point of application, to rounding."""
        for location in ("intersection", "centroid"):
            up = _pile_project(False, location)
            down = _pile_project(True, location)
            e_up = _effects(up, _pile_circle(), _PILE_SLICES)[0]
            e_down = _effects(down, _pile_circle(), _PILE_SLICES)[0]
            assert len(e_up) == 1 and len(e_down) == 1, location
            a, b = e_up[0], e_down[0]
            assert _close(a.force_magnitude, b.force_magnitude), (
                location, a.force_magnitude, b.force_magnitude)
            assert _close(a.application_x, b.application_x)
            assert _close(a.application_y, b.application_y), (
                location, a.application_y, b.application_y)
            f_up = _fos(up, _pile_circle(), _PILE_SLICES)
            f_down = _fos(down, _pile_circle(), _PILE_SLICES)
            assert _close(f_up, f_down), (location, f_up, f_down)

    def test_it_is_the_closed_form_integrated_from_the_top(self):
        from ogr_core.support import clear_spacing, lateral_force
        p = _pile_project(True)
        eff = _effects(p, _pile_circle(), _PILE_SLICES)[0][0]
        d = PILE_TOP - eff.intersection_y
        assert d > 1.0
        phi = math.radians(PHI_DEG)
        d1 = p.support_types[0].out_of_plane_spacing
        d2 = clear_spacing(d1, DIAM)
        q0 = lateral_force(COH, phi, 0.0, d1, d2)
        q1 = lateral_force(COH, phi, GAMMA, d1, d2)
        expected = (q0 * d + (q1 - q0) * d * d / 2.0) / d1
        assert abs(eff.force_magnitude - expected) < 1e-3 * expected, (
            eff.force_magnitude, expected)

    def test_the_flipped_profile_is_the_mirror_image(self):
        from ogr_core.support import BondProfile
        bp = BondProfile.from_samples([1.0 + 3.0 * i * i for i in range(50)],
                                      10.0, stations=[(2.0, 7.0)])
        fp = bp.flipped()
        for k in range(0, 101):
            d = 10.0 * k / 100.0
            assert _close(fp.integral(0.0, d), bp.integral(10.0 - d, 10.0),
                          1e-12 * bp.total), d
        assert fp.stations == ((8.0, 7.0),)
        assert fp.flipped().tau == bp.tau
        assert bp.flipped() is fp                       # built once


class TestTheInterfaceReadsLikeTheEngine:

    def test_the_diagram_gives_the_engines_force(self):
        """A pile and a wall drawn bottom to top: the diagram's force at
        the slip surface is the engine's."""
        _app()
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)
        cases = ((_pile_project(True), _pile_circle(), _PILE_SLICES),
                 (_wall_project(flip=True), _wall_circle(), _WALL_SLICES))
        for p, surface, n in cases:
            eff = _effects(p, surface, n)[0]
            assert len(eff) == 1
            win = SupportForceDiagramWindow(p, _critical(p, surface, n))
            try:
                _series, applied, _cut = win.series()
                assert applied is not None and _close(
                    applied, eff[0].force_magnitude, 1e-9), (
                    applied, eff[0].force_magnitude)
            finally:
                win.deleteLater()

    def test_a_level_support_gets_no_number_and_says_why(self):
        _app()
        from ogr_gui.canvas.graphics_items import SupportItem
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)
        p = _near_level(1e-12)
        win = SupportForceDiagramWindow(
            p, _critical(p, _wall_circle(), _WALL_SLICES))
        try:
            series, applied, _cut = win.series()
            assert series == [] and applied is None, (series, applied)
            win.refresh()
            assert "is level" in win.note.text(), win.note.text()
        finally:
            win.deleteLater()
        tip = SupportItem(p.supports[0], "Wall", p.support_types[0], None,
                          p).toolTip()
        assert "is level" in tip and "Force at" not in tip, tip

    def test_the_tooltip_reads_the_pile_from_its_top(self):
        """The midpoint force integrates the UPPER half, drawn either way."""
        _app()
        from ogr_gui.canvas.graphics_items import SupportItem

        def forces(p):
            tip = SupportItem(p.supports[0], "Pile", p.support_types[0],
                              None, p).toolTip()
            return re.findall(r"Force at [a-z ]+:</i> ([0-9.]+)", tip)

        up, down = forces(_pile_project(False)), forces(_pile_project(True))
        assert len(up) == 2 and up == down, (up, down)
