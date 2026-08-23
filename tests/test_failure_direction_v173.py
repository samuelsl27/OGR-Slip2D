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
def _crack_project(crack_base=((0.0, 19.2), (13.0, 27.0))):
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
    is the one that names the left-hand (true crest) end of the zone.

    v0.1.109 — the zone starts at x = 0 rather than x = 3. The fixture
    circle daylights at x = 2.12 and the zone began at 3, so the CREST of
    the surface was outside the crack zone by nine tenths of a metre. The
    reference truncates nothing in that case and applies no thrust
    either, and now neither does OGR, so the old zone left every test
    below with nothing to measure. It is the same trap this fixture's own
    docstring warns about two paragraphs up, and the same one v0.1.61
    found: a crack the surface never reaches makes the assertion vacuous.
    The left end is dropped to y = 19.2 so the base keeps the same slope.
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
    """v0.1.109 — the name of this class is finally true.

    From v0.1.7 to v0.1.108 nothing was truncated at all: the crack only
    chose which slice received the water thrust, and the three tests that
    used to live here pinned that choice to the DECLARED failure
    direction, as v0.1.73 had decided.

    That decision is reversed here, and the reason is a change of scale
    rather than a change of opinion. Choosing the wrong end used to cost
    a percent; it now decides which half of the arc survives, worth
    twenty per cent on verification problem 12, and always on the unsafe
    side. So the end is read off the surface's own geometry — the higher
    ground wins — and the declaration is kept for the tie, which is the
    role the module docstring reserves for it. The reference agrees
    twice: its help says a failure direction does not affect modelling
    options, and it states the tension-crack rule in terms of "the crest
    of a slip surface", a property of the surface, not of the project.

    What the retired tests were worth is kept below, inverted: the case
    they could not see is exactly the one that now has to work.
    """

    def _ends(self, project):
        """(x_left, x_right, wall) of the surface as finally analysed."""
        from ogr_slip2d import slice_surface

        c = _circle()
        sl = slice_surface(project, c, num_slices=40)
        assert sl is not None, "the fixture surface must be sliceable"
        return c.x_left, c.x_right, c.tension_crack_wall

    def test_the_crest_end_is_the_one_that_moves(self):
        """The fixture's crest is on the LEFT, so the left end truncates.

        And it lands ON the crack line rather than on the ground. That
        geometric identity is stronger than any factor of safety: it is
        checked against the crack boundary of the model itself, not
        against a number somebody published.
        """
        from ogr_core.geometry import BoundaryType
        from ogr_core.hydraulic.water_surfaces import interp_y_on_polyline

        p = _l2r(_crack_project())
        tc = next(b for b in p.boundaries
                  if b.btype == BoundaryType.TENSION_CRACK)
        x_l, x_r, wall = self._ends(p)
        assert wall is not None, "the crest is inside the zone; it must cut"
        # The untruncated arc daylights at x = 2.12; the crack pulls the
        # crest end in, and leaves the far end exactly where it was.
        assert x_l > 3.0, x_l
        assert math.isclose(x_r, 49.18, abs_tol=0.2), x_r
        assert math.isclose(x_l, wall[0], rel_tol=1e-12)
        y_line = interp_y_on_polyline(tc.polyline, x_l)
        assert math.isclose(_circle().base_y_at(x_l), y_line, abs_tol=1e-6)

    def test_a_contradictory_declaration_no_longer_moves_the_arc(self):
        """The reason for the change, in one test.

        This fixture's crest is on the left, so LEFT_TO_RIGHT is the
        truthful declaration. Declaring RIGHT_TO_LEFT is a lie about the
        model — and D03d found nineteen benchmark models telling exactly
        that lie. Under v0.1.73 the lie picked the other end of the zone;
        now it picks nothing, because the geometry answers first. Both
        declarations must analyse the same mass, digit for digit.
        """
        truthful = self._ends(_l2r(_crack_project()))
        lying = self._ends(_r2l(_crack_project()))
        assert truthful == lying, (truthful, lying)
        assert math.isclose(_fos(_l2r(_crack_project())),
                            _fos(_r2l(_crack_project())), rel_tol=1e-12)

    def test_the_declaration_still_breaks_a_genuine_tie(self):
        """It is a tiebreak now, and a tie is not hypothetical.

        Two ends at the SAME ground elevation — a crack cut into level
        ground — leave the geometry with nothing to answer, and an end
        still has to be picked. That is the declaration, and this is the
        one case where changing it changes the arc.
        """
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.geometry.tension_crack import (
            TensionCrackProperties, WaterLevelMode,
        )
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d import SlipCircle, slice_surface

        def _level():
            p = Project("tie")
            ext = Polyline(vertices=[
                Vertex(0, 0), Vertex(100, 0),
                Vertex(100, 30), Vertex(0, 30)], closed=True)
            ext.ensure_ccw()
            p.add_boundary(Boundary(polyline=ext,
                                    btype=BoundaryType.EXTERNAL))
            p.add_boundary(Boundary(polyline=Polyline(
                vertices=[Vertex(0, 25), Vertex(100, 25)], closed=False),
                btype=BoundaryType.TENSION_CRACK))
            p.materials = [Material(
                name="S",
                strength=MohrCoulomb(cohesion=10, friction_angle=25))]
            p.tension_crack_properties = TensionCrackProperties(
                mode=WaterLevelMode.DRY)
            return p

        def _ends(project):
            c = SlipCircle(centre_x=50, centre_y=50, radius=40)
            assert slice_surface(project, c, num_slices=20) is not None
            return round(c.x_left, 6), round(c.x_right, 6)

        left = _ends(_l2r(_level()))
        right = _ends(_r2l(_level()))
        assert left != right, (left, right)
        # Mirror images of each other about the circle's own centre.
        assert math.isclose(50.0 - left[0], right[1] - 50.0, abs_tol=1e-6)

    def test_a_horizontal_crack_can_no_longer_hide_the_choice(self):
        """The inverse of the test this replaces, and the same lesson.

        The retired ``test_a_horizontal_crack_hides_the_choice_entirely``
        recorded why a wrong assumption survived from v0.1.7 to v0.1.73:
        the thrust reaches every method as a horizontal force whose
        moment depends only on its magnitude and on the height of its
        line of action, so with a HORIZONTAL crack base both ends of the
        zone gave factors identical to the last bit. Nothing could see
        the mistake.

        Truncation cannot hide that way — cutting one end or the other
        removes a different piece of arc — which is what makes the choice
        testable at all, and is part of why it was worth moving onto the
        geometry.
        """
        flat = ((0.0, 24.0), (13.0, 24.0))
        f_l2r = _fos(_l2r(_crack_project(flat)))
        f_r2l = _fos(_r2l(_crack_project(flat)))
        # The same answer, because the geometry decides and the geometry
        # is the same. The declaration is no longer part of the question.
        assert math.isclose(f_l2r, f_r2l, rel_tol=1e-12)
        # And the crack IS doing something: without the boundary the
        # untruncated arc gives a different, higher factor (rule 7).
        bare = _crack_project(flat)
        bare.boundaries = [b for b in bare.boundaries
                           if b.btype.name != "TENSION_CRACK"]
        assert _fos(bare) > f_l2r * 1.01, (_fos(bare), f_l2r)


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
                        num_slices=20, seed=seed)
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


# ======================================================================
# 4. The declaration, checked against the ground (v0.1.98)
# ======================================================================
# Everything above pins what the setting DOES. Nothing above noticed that
# it can simply be declared wrong, and for three years of model-building
# nothing did: auditing a bank of 138 models found 19 that declared right
# to left with the crest plainly on the left.
#
# Not one of them had a wrong factor of safety, which is exactly why they
# survived — none had a support, and the only one with a tension crack
# had it dry. The one that mattered was waiting: with the crack wet, the
# contradictory declaration sends the thrust to the down-slope end of the
# zone, where the ground has already dropped to the base of the crack, so
# it is never applied at all and the factor of safety comes out 22.6 %
# too high, on the unsafe side. Fixing the crack would have looked like
# it changed nothing.
def _fd_notes(project):
    """Just the failure-direction lines of ``settings_warnings``."""
    from ogr_slip2d.analysis_runner import settings_warnings

    return [n for n in settings_warnings(project) if "Failure Direction" in n]


def _mirrored(project, axis: float = 30.0):
    """The same model reflected about a vertical line.

    Reflecting rather than hand-writing a second fixture: the two models
    are then provably the same problem, so an asymmetry a test finds is
    in the code and not in two sets of coordinates that merely look
    alike.
    """
    from ogr_core.geometry import Polyline, Vertex

    for b in project.boundaries:
        vs = [Vertex(2.0 * axis - v.x, v.y)
              for v in reversed(b.polyline.vertices)]
        b.polyline = Polyline(vertices=vs, closed=b.polyline.closed)
        if b.polyline.closed:
            b.polyline.ensure_ccw()
    return project


def _mirrored_circle(axis: float = 30.0):
    from ogr_slip2d import SlipCircle

    c = _circle()
    return SlipCircle(centre_x=2.0 * axis - c.centre_x,
                      centre_y=c.centre_y, radius=c.radius)


def _loaded_slice_x_at(project, circle):
    """``_loaded_slice_x`` on a surface other than the fixture circle.

    The mirrored model needs the mirrored circle: reusing the original
    would compare two different surfaces and call the difference an
    asymmetry.
    """
    from ogr_slip2d import slice_surface

    sl = slice_surface(project, circle, num_slices=40)
    assert sl is not None, "the fixture surface must be sliceable"
    loaded = [s for s in sl.slices if abs(s.water_force_h) > 1e-12]
    assert len(loaded) <= 1, "the thrust goes on exactly one slice"
    return (loaded[0].x_centre if loaded else None), sl


def _fos_at(project, circle):
    from ogr_slip2d import slice_surface
    from ogr_slip2d.methods import BishopSimplified

    sl = slice_surface(project, circle, num_slices=40)
    return BishopSimplified().compute_fos(project, circle, sl).fos


class TestTheDeclaredDirectionIsCheckedAgainstTheGround:

    def test_a_crest_on_the_left_declared_right_to_left_is_reported(self):
        """The shape of all nineteen: ground high on the left, R2L."""
        notes = _fd_notes(_r2l(_crack_project()))
        assert len(notes) == 1, notes
        # The message has to name the contradiction, not merely exist:
        # a note that says "check your settings" sends nobody anywhere.
        assert "Right to Left" in notes[0]
        assert "higher on the left" in notes[0]

    def test_the_matching_declaration_is_silent(self):
        """Both ways round, so the check is not simply biased to L2R."""
        assert _fd_notes(_l2r(_crack_project())) == []
        assert _fd_notes(_r2l(_mirrored(_crack_project()))) == []

    def test_the_contradiction_is_caught_in_the_mirror_too(self):
        assert len(_fd_notes(_l2r(_mirrored(_crack_project())))) == 1

    def test_a_symmetric_embankment_gets_no_verdict(self):
        """The check abstains where the geometry genuinely does not say.

        Both ends of this ground surface are at y = 5, so neither side is
        up-slope and only the figure in the source decides. A check that
        guessed here would be worse than no check: it would file the one
        real answer under the same heading as its own coin-flip.
        """
        assert _fd_notes(_r2l(_embankment())) == []
        assert _fd_notes(_l2r(_embankment())) == []

    def test_the_steepest_face_rule_would_have_been_wrong_here(self):
        """Why the check compares the two ENDS and not the steepest face.

        Locating the slope face as the steepest ground segment is what
        the searches do, so reusing that rule here is the obvious move.
        It gives false positives. An embankment dam has a face on each
        side and they are rarely cut to the same batter; the steeper one
        is a statement about riprap and drawdown, not about which side
        the crest is on. This fixture is that shape — both toes at y = 0,
        upstream 3H:1V and downstream 2H:1V — the two rules disagree:
        the steepest-face rule names the downstream side, while the ends
        tie and the check keeps quiet.

        Not hypothetical. On the bank the steepest-face rule contradicts
        five dam models that are declared correctly.
        """
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.geometry import ground_surface
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project

        ext = Polyline(vertices=[
            Vertex(0, -10), Vertex(180, -10), Vertex(180, 0),
            Vertex(120, 30), Vertex(90, 30), Vertex(0, 0),
        ], closed=True)
        ext.ensure_ccw()
        p = Project("dam")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(
            name="Fill", strength=MohrCoulomb(cohesion=20, friction_angle=32))]

        top = list(ground_surface(p.external_boundary()).vertices)
        assert top[0].y == top[-1].y, top          # the ends really tie
        faces = {abs((b.y - a.y) / (b.x - a.x)): (a.x, b.x)
                 for a, b in zip(top, top[1:]) if abs(b.x - a.x) > 1e-9}
        batters = sorted(k for k in faces if k > 0)
        assert len(batters) == 2, faces
        assert math.isclose(batters[0], 1 / 3, rel_tol=1e-9), faces
        assert math.isclose(batters[1], 0.5, rel_tol=1e-9), faces
        # One face IS steeper, so the steepest-face rule would answer —
        # and it would answer about the downstream side, on the right.
        assert faces[batters[1]][0] > 100.0, faces

        # The rule this check actually uses says nothing at all.
        assert _fd_notes(_r2l(p)) == []
        assert _fd_notes(_l2r(p)) == []

    def test_the_note_reaches_the_analysis_outcome(self):
        """Reachability, not plumbing taste.

        A check nobody can see is the same defect as a setting nobody
        reads. This is the path the graphical interface, the terminal and
        the verification bank all take.
        """
        from ogr_slip2d.analysis_runner import run_analysis

        outcome = run_analysis(_r2l(_crack_project()), ["bishop_simplified"])
        assert any("Failure Direction" in w for w in outcome.warnings)


class TestTheCrackThrustLandsOnTheCrestSlice:
    """The invariant the nineteen were hiding, in both directions.

    ``TestTheCrackTruncatesTheUpSlopeEnd`` above proves the two
    declarations pick OPPOSITE ends of the crack zone. It never proves
    which end is right, so it passes just as happily with the convention
    inverted. This does: with the direction declared to match the ground,
    the thrust must land on the crest side and the factor of safety must
    fall — mirrored, so neither answer can come from a hard-coded side.
    """

    def _dry(self, project):
        from ogr_core.geometry.tension_crack import WaterLevelMode

        project.tension_crack_properties.mode = WaterLevelMode.DRY
        return project

    def test_the_thrust_lands_on_the_crest_half_of_the_zone(self):
        x_l2r, _ = _loaded_slice_x(_l2r(_crack_project()))
        x_r2l, _ = _loaded_slice_x_at(_r2l(_mirrored(_crack_project())),
                                     _mirrored_circle())
        assert x_l2r is not None and x_r2l is not None
        # Zone 3 → 13 with the crest on the left; mirrored, 47 → 57 with
        # the crest on the right.
        assert x_l2r < 8.0, x_l2r
        assert x_r2l > 52.0, x_r2l

    def test_a_wet_crack_lowers_the_factor_of_safety_both_ways(self):
        """Rule 7 for the pairing of setting and geometry, not the setting
        alone: water in a crack can only ever push the mass out."""
        wet = _fos(_l2r(_crack_project()))
        dry = _fos(self._dry(_l2r(_crack_project())))
        assert 0.5 < wet < dry < 3.0, (wet, dry)

        m_wet = _fos_at(_r2l(_mirrored(_crack_project())), _mirrored_circle())
        m_dry = _fos_at(self._dry(_r2l(_mirrored(_crack_project()))),
                        _mirrored_circle())
        assert 0.5 < m_wet < m_dry < 3.0, (m_wet, m_dry)
        # Same problem, so the same numbers: any gap is an asymmetry in
        # the code, which is the whole point of testing it mirrored.
        assert math.isclose(wet, m_wet, rel_tol=1e-9), (wet, m_wet)
        assert math.isclose(dry, m_dry, rel_tol=1e-9), (dry, m_dry)
