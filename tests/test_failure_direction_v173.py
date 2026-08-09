# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Failure Direction: what it decides, and — just as important — what it does not.

Until v0.1.73 this setting was very nearly decorative. It was read in
exactly two places: the angle of a support's force
(``support_integration``) and one line of the PDF report. Every analysis
method derives the sense of sliding from the geometry of each individual
surface (``slide_sign``, from the sign of ``Σ W·sin α``), so in a model
without supports, flipping the setting moved no number at all. That is
rule 7 in its purest form: a control the user believes the analysis
respects, which the analysis ignores.

The fix was NOT to route the calculation through the setting. The
per-surface geometric derivation is both more robust and finer-grained
than a project-wide switch, and the reference agrees — it states that
Path Search always starts at the toe *regardless of* the Failure
Direction. Wiring a setting into a question the geometry already answers
correctly would make results worse, not more honest.

What the setting is for is the handful of places where the geometry is
genuinely **ambiguous**, and this file pins each of them:

1. **The tension crack** forms at the crest, so which end of the crack
   zone is up-slope is a statement about direction, not about geometry.
   The old code assumed "the right", in a comment that admitted it was an
   assumption.

2. **A symmetric embankment** has two faces of identical inclination.
   Path Search picked one with a strict ``>`` over the segments, so the
   left face won by iteration order and nothing else.

3. **A support force** resists the movement, so its direction is the
   reverse of one that no geometry can supply.

The convention, fixed in ``ogr_slip2d.failure_direction`` and asserted
below: RIGHT_TO_LEFT means the mass moves towards decreasing x — crest on
the right, toe on the left. It is the default, and both new wirings
reduce to the previous behaviour under it, so no stored project can
change its factor of safety by being reopened.
"""
from __future__ import annotations

import math


def _l2r(project):
    from ogr_core.project.units import FailureDirection
    project.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    return project


def _r2l(project):
    from ogr_core.project.units import FailureDirection
    project.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
    return project


# ======================================================================
# The convention itself
# ======================================================================
class TestTheConventionIsStatedInOnePlace:

    def test_right_to_left_is_the_default(self):
        from ogr_core.project import Project
        from ogr_slip2d.failure_direction import (
            crest_is_on_the_right, is_left_to_right,
        )
        p = Project("default")
        assert is_left_to_right(p) is False
        assert crest_is_on_the_right(p) is True

    def test_left_to_right_puts_the_crest_on_the_left(self):
        from ogr_core.project import Project
        from ogr_slip2d.failure_direction import (
            crest_is_on_the_right, is_left_to_right,
        )
        p = _l2r(Project("l2r"))
        assert is_left_to_right(p) is True
        assert crest_is_on_the_right(p) is False

    def test_it_agrees_with_the_support_module_that_predates_it(self):
        """``support_integration`` has said since v0.1.64 that a
        right-to-left slide is resisted by a force pointing +x. The new
        helper must mean the same thing by the same words, or two parts
        of the engine would disagree about which way is downhill."""
        from ogr_core.geometry import Vertex
        from ogr_core.support import ForceOrientation, SupportInstance
        from ogr_slip2d.support_integration import _support_force_angle

        support = SupportInstance(
            type_id="end_anchored", head=Vertex(0.0, 0.0),
            tail=Vertex(5.0, -5.0),
            orientation=ForceOrientation.HORIZONTAL)
        # is_left_to_right_failure=False → right-to-left → resists to +x.
        assert _support_force_angle(support, 0.0, False) == 0.0
        assert _support_force_angle(support, 0.0, True) == math.pi

    def test_a_project_without_settings_falls_back_to_the_default(self):
        """The same defensive fallback support_integration already used:
        a half-built object in a test must not raise from here."""
        from ogr_slip2d.failure_direction import is_left_to_right

        class _Bare:
            pass
        assert is_left_to_right(_Bare()) is False


# ======================================================================
# 1. The tension crack
# ======================================================================
def _crack_project(crack_base=((3.0, 21.0), (13.0, 27.0))):
    """A slope whose crest is on the LEFT, with a WIDE crack zone on it.

    Two properties of this fixture are deliberate, and neither is
    incidental:

    * The zone spans several slices. If only one slice fell inside it,
      both ends would select the same slice and the choice under test
      would be invisible — the same trap v0.1.61 found in the original
      tension-crack test, where the circle never reached the crack and
      the assertion was vacuous.

    * The crack BASE slopes. See
      ``test_a_horizontal_crack_hides_the_choice_entirely`` for why that
      matters: with a horizontal base the choice of slice changes no
      number at all, which is how a wrong assumption survived in this
      code from v0.1.7 to v0.1.73 without anyone noticing.

    The ground is high on the left, so the mass really slides towards
    increasing x: LEFT_TO_RIGHT is the correct declaration here, and it
    is the one that picks the left-hand (true crest) end of the zone.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.geometry.tension_crack import (
        TensionCrackProperties, WaterLevelMode,
    )
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("TC direction")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    (x0, y0), (x1, y1) = crack_base
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(x0, y0), Vertex(x1, y1)],
                          closed=False),
        btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=10, friction_angle=25))]
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode.FILLED)
    return p


def _circle():
    from ogr_slip2d import SlipCircle
    return SlipCircle(centre_x=35, centre_y=42, radius=35)


def _loaded_slice_x(project):
    """x of the slice the crack thrust was applied to (None if none was)."""
    from ogr_slip2d import slice_surface

    sl = slice_surface(project, _circle(), num_slices=40)
    assert sl is not None, "the fixture surface must be sliceable"
    loaded = [s for s in sl.slices if abs(s.water_force_h) > 1e-12]
    assert len(loaded) <= 1, "the thrust goes on exactly one slice"
    return (loaded[0].x_centre if loaded else None), sl


def _fos(project):
    from ogr_slip2d import slice_surface
    from ogr_slip2d.methods import BishopSimplified

    circle = _circle()
    sl = slice_surface(project, circle, num_slices=40)
    return BishopSimplified().compute_fos(project, circle, sl).fos


class TestTheCrackTruncatesTheUpSlopeEnd:

    def test_the_two_directions_pick_opposite_ends_of_the_zone(self):
        x_r2l, _ = _loaded_slice_x(_r2l(_crack_project()))
        x_l2r, _ = _loaded_slice_x(_l2r(_crack_project()))
        assert x_r2l is not None and x_l2r is not None
        # Right-to-left has its crest on the right, so it takes the
        # right-hand end of the zone; left-to-right takes the other.
        assert x_r2l > x_l2r, (x_r2l, x_l2r)

    def test_the_default_reproduces_the_old_hardcoded_assumption(self):
        """The retired comment said "assume rightward ... the up-slope end
        is on the right", which is exactly right-to-left. No stored
        project may change its factor of safety by being reopened."""
        x_default, _ = _loaded_slice_x(_crack_project())
        x_r2l, _ = _loaded_slice_x(_r2l(_crack_project()))
        assert x_default == x_r2l

    def test_it_moves_the_factor_of_safety(self):
        """Rule 7, and the reason the fixture's crack base slopes.

        A different slice sits over a different crack depth, so both the
        wet height and the line of action of the thrust move with it:
        ½·γw·hw² is about 61 kN/m at one end of this zone and 352 kN/m at
        the other. The factor of safety has to follow, or the setting is
        decoration again.
        """
        f_r2l = _fos(_r2l(_crack_project()))
        f_l2r = _fos(_l2r(_crack_project()))
        assert all(math.isfinite(f) for f in (f_r2l, f_l2r))
        # Sanity: both are ordinary factors of safety, not a runaway from
        # a degenerate fixture. A flat-topped block returns nonsense here
        # (its driving moment is ~0) and the comparison below would mean
        # nothing — which is how the first draft of this test failed.
        assert 0.5 < f_l2r < f_r2l < 3.0, (f_r2l, f_l2r)
        assert abs(f_r2l - f_l2r) > 1e-3, (f_r2l, f_l2r)

    def test_a_horizontal_crack_hides_the_choice_entirely(self):
        """Why the wrong assumption survived sixty-six versions.

        The thrust reaches every method as a horizontal force whose
        moment about the circle centre is ``y_c·F − F·y`` — a function of
        the force and the HEIGHT of its line of action, and of nothing
        else. With a horizontal crack base, ``F`` and ``y`` are identical
        at both ends of the zone, so which slice carries the thrust
        changes no number whatsoever. The assumption was wrong from
        v0.1.7 and invisible in every model that did not slope its crack.

        Pinned as a test rather than left as a remark, because it is also
        the honest boundary of what v0.1.73 fixed.
        """
        flat = ((3.0, 24.0), (13.0, 24.0))
        x_r2l, _ = _loaded_slice_x(_r2l(_crack_project(flat)))
        x_l2r, _ = _loaded_slice_x(_l2r(_crack_project(flat)))
        assert x_r2l != x_l2r, "the two ends must still be different slices"
        assert math.isclose(_fos(_r2l(_crack_project(flat))),
                            _fos(_l2r(_crack_project(flat))),
                            rel_tol=1e-12)


# ======================================================================
# 2. The symmetric embankment
# ======================================================================
def _embankment():
    """Two faces of IDENTICAL inclination — the tie the setting breaks.

    Left face 20 → 40 rising 0 → 20, right face 60 → 80 falling 20 → 0:
    both at exactly 45°, so no comparison of steepness can separate them
    and the old strict ``>`` handed the decision to iteration order.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 5),
        Vertex(80, 5), Vertex(60, 25), Vertex(40, 25),
        Vertex(20, 5), Vertex(0, 5),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("embankment")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Fill", strength=MohrCoulomb(cohesion=15, friction_angle=30))]
    return p


def _mean_initiation_x(project, seed: int = 7):
    """Where Path Search starts its surfaces, averaged over a few paths."""
    from ogr_slip2d import PathSearch
    from ogr_slip2d.methods import BishopSimplified

    search = PathSearch(method=BishopSimplified(), num_paths=12,
                        num_slices=20, optimize=False, seed=seed)
    result = search.run(project)
    xs = []
    for r in result.evaluations:
        verts = getattr(getattr(r.surface, "polyline", None), "vertices", None)
        if verts:
            xs.append(verts[0].x)
    assert xs, "the search produced no surface to look at"
    return sum(xs) / len(xs)


class TestTheEmbankmentTieIsBrokenByTheSetting:

    def test_the_two_faces_really_are_equally_steep(self):
        """If they were not, the tie-break would never run and the tests
        below would be measuring the steepness comparison instead."""
        p = _embankment()
        top = [v for v in p.external_boundary().polyline.vertices]
        slopes = []
        for a, b in zip(top, top[1:]):
            if abs(b.x - a.x) > 1e-9:
                slopes.append(abs((b.y - a.y) / (b.x - a.x)))
        assert slopes.count(max(slopes)) >= 2, slopes

    def test_each_direction_starts_from_its_own_side(self):
        x_r2l = _mean_initiation_x(_r2l(_embankment()))
        x_l2r = _mean_initiation_x(_l2r(_embankment()))
        # Right-to-left exits at a toe on the left, so its surfaces begin
        # at smaller x than the left-to-right ones.
        assert x_r2l < x_l2r, (x_r2l, x_l2r)

    def test_the_default_keeps_the_face_the_old_code_chose(self):
        """The old strict ``>`` always kept the FIRST steepest segment,
        i.e. the left-hand face. Right-to-left must reproduce that."""
        assert math.isclose(_mean_initiation_x(_embankment()),
                            _mean_initiation_x(_r2l(_embankment())),
                            rel_tol=1e-12)

    def test_a_single_face_slope_is_untouched_by_the_setting(self):
        """No tie, no tie-break: an ordinary slope must give the same
        search whichever way the setting is pointed. This is what keeps
        the validated cases out of reach of this change."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project

        def _slope():
            ext = Polyline(vertices=[
                Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
                Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
            ], closed=True)
            ext.ensure_ccw()
            p = Project("one face")
            p.add_boundary(Boundary(polyline=ext,
                                    btype=BoundaryType.EXTERNAL))
            p.materials = [Material(
                name="Soil",
                strength=MohrCoulomb(cohesion=10, friction_angle=25))]
            return p

        assert math.isclose(_mean_initiation_x(_r2l(_slope())),
                            _mean_initiation_x(_l2r(_slope())),
                            rel_tol=1e-12)


# ======================================================================
# 3. The interface
# ======================================================================
class TestTheSelectorWritesTheSetting:
    """A picture is worth having only if it writes the same value the
    drop-down used to."""

    _WINDOWS: list = []

    def _page(self, settings=None):
        from PySide6.QtWidgets import QApplication
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog,
        )
        QApplication.instance() or QApplication([])
        s = settings or ProjectSettings()
        d = ProjectSettingsDialog(s)
        self._WINDOWS.append(d)
        return d.pages[0], s

    def test_it_opens_on_the_projects_current_direction(self):
        from ogr_core.project import ProjectSettings
        from ogr_core.project.units import FailureDirection
        s = ProjectSettings()
        s.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
        page, _ = self._page(s)
        assert page.sel_dir.rb_l2r.isChecked() is True
        assert page.sel_dir.value() == FailureDirection.LEFT_TO_RIGHT

    def test_choosing_the_other_option_writes_it_through(self):
        from ogr_core.project.units import FailureDirection
        page, s = self._page()
        assert s.units.failure_direction == FailureDirection.RIGHT_TO_LEFT
        page.sel_dir.rb_l2r.setChecked(True)
        page.apply()
        assert s.units.failure_direction == FailureDirection.LEFT_TO_RIGHT

    def test_the_sketch_paints_in_both_directions(self):
        """The drawing is code, not an asset, so it can fail at runtime in
        a way a PNG cannot. Rendering both states is the cheap guard."""
        from PySide6.QtGui import QPixmap
        from ogr_core.project.units import FailureDirection

        page, _ = self._page()
        for direction in (FailureDirection.RIGHT_TO_LEFT,
                          FailureDirection.LEFT_TO_RIGHT):
            page.sel_dir.set_value(direction)
            sketch = page.sel_dir._sketch
            pm = QPixmap(sketch.size())
            pm.fill()
            sketch.render(pm)
            assert not pm.isNull()

    def test_both_labels_are_translated(self):
        from ogr_gui.i18n import current_language, set_language, tr
        prev = current_language()
        try:
            set_language("es")
            for key in ("Right to Left", "Left to Right"):
                assert tr(key) != key, key
        finally:
            set_language(prev)
