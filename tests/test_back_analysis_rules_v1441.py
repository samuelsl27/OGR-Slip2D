# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.441 (D418) — the two surfaces a back analysis does not analyse.

The invariant: the support force a back analysis publishes is the largest
among the surfaces that are BELOW the target factor and that the force
TOUCHES. Both conditions are the reference specification's (paraphrased:
only the slip surfaces below the specified factor are back-analysed, and a
surface whose mass the force is not in contact with is not). Until this
version every valid surface was priced, measured on the demo slope (crest at
elevation 25, toe at 15; 64-circle grid, target 1.5, kN/m):

    force at elevation 28 or 35, above the crest   Janbu 145.99; Bishop
                                                   228.25 and 547.80,
                                                   growing with the arm
    every surface already above the target (1.0)   0.00, on the first
                                                   surface of the list
                                                   (FS 5.25) as "governing"

Now neither publishes a force, and each says why.

What is anchored, and against what:

* **the contact, against its closed form.** The force acts where the slope
  is at its elevation, so it touches a mass when that elevation is within the
  range of the TOP of the mass (the owner's decision of 2026-11-12). The
  circle of centre (34, 30) through (31, 19) leaves the demo's face
  (y = 50 - x) at elevation 19 by construction and enters the crest at
  x = 34 - sqrt(105): its top runs from 19 to 25, the ends included. A ground
  vertex inside one slice counts (the slicer does not cut there), and at a
  vertical step the mass has the height of its own side.
* **the two identities of the back analysis** (Bishop 1955; Janbu 1954;
  D210): the force is zero at a surface's own factor, measured unclipped on
  the method's own sums to 1e-9 of its weight (the run itself no longer
  prices a surface AT the target: it needs nothing), and active equals
  passive at a target of 1.0, on the governing surface of the reference
  slope, whose critical factor is below 1.
* **where the force touches the mass and the factor is below the target,
  nothing moves:** the governing force with the screens is the one without
  them to the last bit (the module's switch, in the same process), and the
  one measured on 0.1.440 to 1e-9.
* **the counts**, measured on 0.1.435 by the bench's ``medir_d418.py`` and
  ``medir_d418_criterios.py`` before the rule was written: 41 of 52 surfaces
  above 1.5 with Janbu and 42 with Bishop; at elevation 16, 8 of the ones
  below the target untouched.
* a surface already at the target is counted and NOT said while there is a
  force to publish (a run with nothing to warn of leaves no note, D340); the
  ones below the target that the force does not touch are always said: the
  force does nothing for them.
* Interpret prices the critical surface by the same rule, the agent gets the
  reason and the two counts, and the modeller's box says the reason once.

From the review of 0.1.441: the face of a vertical cut is the top of the
mass that leaves the ground through it; with several reasons for no force,
the one that says no force is needed comes before the one Bishop cannot
price; the range a note gives is said to be a hull; and the progress is
reported for the surfaces left out.

Cost: eighteen back analyses of a 64-circle grid (0.15 s each), one of the
reference slope, two jobs of the agent in a child process, five Interpret
windows and a main window; about six seconds.
"""
from __future__ import annotations

import math
import os
from contextlib import contextmanager
from types import SimpleNamespace as NS

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_TOL_W = 1e-9
#: The governing force at elevation 20 for a target of 1.5, MEASURED on
#: 0.1.439 (38f0cae) and unchanged in 0.1.440: the ``_V1439`` of
#: ``test_interpret_back_analysis_v1440`` (145.99 and 136.95 kN/m).
_V1440 = {"janbu_simplified": "0x1.23fa9a025658cp+7",
          "bishop_simplified": "0x1.11e62c305393cp+7"}
#: Measured on 0.1.435 (the ficha's table): surfaces above a target of 1.5.
_ABOVE = {"janbu_simplified": 41, "bishop_simplified": 42}
_MESSAGE_1440 = (
    "Required support force for FS = 1.5\n\nactive: 97.33\n"
    "passive: 145.99\n\nThe passive value is the larger and therefore the "
    "conservative one for design.")


@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    kept = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(kept)


@contextmanager
def _swapped(owner, name, value):
    own = vars(owner) if not isinstance(owner, type) else None
    had = own is None or name in own
    kept = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if had:
            setattr(owner, name, kept)
        else:
            delattr(owner, name)


@contextmanager
def _screens(on):
    """The module's switch, for the block. On a tree that has none (before
    0.1.441) there is nothing to switch and the back analysis is the one
    without screens: the tests then fail by the force it publishes, not by
    a missing name."""
    import ogr_slip2d.back_analysis as BA
    if not hasattr(BA, "REFERENCE_SCREENS"):
        yield
        return
    with _swapped(BA, "REFERENCE_SCREENS", on):
        yield


def _demo(mid="janbu_simplified"):
    """The 64-circle grid of the ficha on the demo slope."""
    from examples.quick_slope import build_demo_slope
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "circular", "grid"
    s.grid_x_min, s.grid_x_max = 30.0, 45.0
    s.grid_y_min, s.grid_y_max = 40.0, 55.0
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 3
    p.settings.methods.enabled_methods = [mid]
    return p


_BACK: dict = {}


def _back(mid, target, elevation, screens=True):
    """One back analysis of the demo grid, once per configuration."""
    key = (mid, target, elevation, screens)
    if key not in _BACK:
        from ogr_slip2d.analysis_runner import run_configured_back_analysis
        with _screens(screens):
            _BACK[key] = run_configured_back_analysis(
                _demo(mid), target_fos=target, elevation=elevation,
                method_id=mid)[0]
    return _BACK[key]


def _is(value, measured_hex) -> bool:
    """To 1e-9: the literal was measured on another machine (see
    ``test_interpret_back_analysis_v1440._is``)."""
    ref = float.fromhex(measured_hex)
    return abs(value - ref) <= 1e-9 * abs(ref)


# The circle whose top is known in closed form: centre (34, 30), through the
# point (31, 19) of the face y = 50 - x.
_R2 = (34.0 - 31.0) ** 2 + (30.0 - 19.0) ** 2            # 130
_X_IN = 34.0 - math.sqrt(_R2 - (30.0 - 25.0) ** 2)       # on the crest
_ONE: dict = {}


def _one(mid="janbu_simplified"):
    """``(project, evaluation)`` of that circle, solved to 1e-12."""
    if mid not in _ONE:
        from examples.quick_slope import build_demo_slope
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.surface import SlipCircle
        p = build_demo_slope()
        p.settings.methods.enabled_methods = [mid]
        # for the identity: with the default tolerance (0.005) the factor
        # is converged only to it, and the force at "its own factor" is
        # 6e-5 of the weight
        p.settings.methods.tolerance = 1e-12
        p.settings.methods.max_iterations = 400
        ev = build_search(p, mid).evaluate_circle(
            p, SlipCircle(centre_x=34.0, centre_y=30.0,
                          radius=math.sqrt(_R2)))
        assert ev.is_valid and getattr(ev, "admissible", True)
        _ONE[mid] = (p, ev)
    return _ONE[mid]


def _drive(project, evaluations, target, elevation, mid="janbu_simplified"):
    """The driver over a search that returns just these evaluations."""
    from ogr_slip2d.back_analysis import run_back_analysis
    search = NS(run=lambda _p: NS(evaluations=list(evaluations)),
                slice_store=None)
    return run_back_analysis(project, search, target, elevation, mid)


# ======================================================================
class TestTheTopOfTheMass:

    def test_the_circle_of_the_closed_form(self):
        from ogr_slip2d.back_analysis import ground_of, mass_top_range
        for mid in ("janbu_simplified", "bishop_simplified"):
            p, ev = _one(mid)
            sl = list(ev.slices)
            assert abs(sl[0].base_x_left - _X_IN) < 1e-9
            assert abs(sl[-1].base_x_right - 31.0) < 1e-9
            lo, hi = mass_top_range(ev.slices, ground_of(p))
            assert abs(lo - 19.0) < 1e-9 and abs(hi - 25.0) < 1e-9, (lo, hi)

    def test_a_ground_vertex_inside_a_slice_counts(self):
        """Two slices under a berm whose crest falls inside the first: the
        slice edges alone say 10 to 12, and the top reaches 15."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.back_analysis import mass_top_range
        slices = [NS(base_x_left=0.0, top_y_left=10.0,
                     base_x_right=4.0, top_y_right=12.0),
                  NS(base_x_left=4.0, top_y_left=12.0,
                     base_x_right=8.0, top_y_right=11.0)]
        ground = Polyline(vertices=[Vertex(-5.0, 10.0), Vertex(0.0, 10.0),
                                    Vertex(2.0, 15.0), Vertex(4.0, 12.0),
                                    Vertex(8.0, 11.0), Vertex(12.0, 9.0)])
        assert mass_top_range(slices) == (10.0, 12.0)
        assert mass_top_range(slices, ground) == (10.0, 15.0)
        assert mass_top_range([]) is None

    def test_at_a_step_the_mass_has_the_height_of_its_own_side(self):
        """A mass that ends at the foot of a wall: the wall's crest, at the
        same abscissa, is not on its top."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.back_analysis import mass_top_range
        slices = [NS(base_x_left=10.0, top_y_left=20.0,
                     base_x_right=14.0, top_y_right=20.0)]
        ground = Polyline(vertices=[Vertex(0.0, 30.0), Vertex(10.0, 30.0),
                                    Vertex(10.0, 20.0), Vertex(20.0, 20.0)])
        assert mass_top_range(slices, ground) == (20.0, 20.0)

    def test_the_face_of_a_vertical_cut_is_the_top_of_its_mass(self):
        """A 10 m vertical cut at x = 10 and the circle of centre (12, 14),
        R² = 125: it leaves the ground THROUGH the wall, at elevation 3
        ((10-12)² + (3-14)² = 125), and enters the crest at
        x = 12 + sqrt(109). The stretch of the wall from 3 to 10 is the
        free face of that mass, and the two vertices of the step share its
        end's abscissa: read from the slice tops and the vertices between
        the ends alone, its top was 10 to 10, and a force on the face of
        the cut touched no mass (the review of 0.1.441)."""
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.back_analysis import ground_of, mass_top_range
        from ogr_slip2d.surface import SlipCircle
        p = Project(name="Vertical cut")
        ext = Polyline(vertices=[Vertex(0.0, -10.0), Vertex(30.0, -10.0),
                                 Vertex(30.0, 10.0), Vertex(10.0, 10.0),
                                 Vertex(10.0, 0.0), Vertex(0.0, 0.0)],
                       closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_material(Material(
            name="Soil", strength=MohrCoulomb(cohesion=10.0,
                                              friction_angle=25.0),
            unit_weight=19.0))
        p.settings.methods.enabled_methods = ["janbu_simplified"]
        ev = build_search(p, "janbu_simplified").evaluate_circle(
            p, SlipCircle(centre_x=12.0, centre_y=14.0,
                          radius=math.sqrt(125.0)))
        assert ev is not None and ev.is_valid
        sl = list(ev.slices)
        assert abs(sl[0].base_x_left - 10.0) < 1e-9
        assert abs(sl[-1].base_x_right - (12.0 + math.sqrt(109.0))) < 1e-9
        assert mass_top_range(ev.slices) == (10.0, 10.0)
        lo, hi = mass_top_range(ev.slices, ground_of(p))
        assert abs(lo - 3.0) < 1e-9 and hi == 10.0, (lo, hi)
        target = 1.2 * ev.fos
        assert _drive(p, [ev], target, 5.0).critical is not None
        assert _drive(p, [ev], target, 2.9).surfaces_untouched == 1
        assert _drive(p, [ev], target, 10.1).surfaces_untouched == 1

    def test_the_bottom_of_a_tension_crack_is_not_on_the_top(self):
        """A mass that ends at a crack: its base stops at the bottom of the
        crack, below a ground that has one height there. That point is not
        on the ground, and the top is the ground alone."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.back_analysis import mass_top_range
        slices = [NS(base_x_left=10.0, top_y_left=25.0, base_y_left=5.0,
                     base_x_right=14.0, top_y_right=20.0, base_y_right=8.0),
                  NS(base_x_left=14.0, top_y_left=20.0, base_y_left=8.0,
                     base_x_right=18.0, top_y_right=20.0, base_y_right=20.0)]
        ground = Polyline(vertices=[Vertex(0.0, 25.0), Vertex(10.0, 25.0),
                                    Vertex(14.0, 20.0), Vertex(30.0, 20.0)])
        assert mass_top_range(slices, ground) == (20.0, 25.0)

    def test_the_ends_are_in_and_the_tolerance_is_relative(self):
        from ogr_slip2d.back_analysis import force_touches
        assert force_touches((19.0, 25.0), 19.0)
        assert force_touches((19.0, 25.0), 25.0)
        assert force_touches((19.0, 25.0), 22.0)
        assert not force_touches((19.0, 25.0), 18.999)
        assert not force_touches((19.0, 25.0), 25.001)
        # the last bits of an interpolated height, at any scale
        assert force_touches((1900.0, 2500.0), 1900.0 - 1e-9)
        assert not force_touches((1900.0, 2500.0), 1899.99)
        assert force_touches((20.0, 20.0), 20.0)


# ======================================================================
class TestOneSurface:
    """The driver over the one circle whose top is known."""

    def test_it_is_analysed_where_the_force_touches_it(self):
        from ogr_slip2d import run_messages as RM
        from ogr_slip2d.back_analysis import required_force
        p, ev = _one()
        target = 1.2 * ev.fos
        for elevation, touched in ((19.0, True), (19.05, True),
                                   (25.0, True), (18.95, False),
                                   (25.05, False), (0.0, False),
                                   (35.0, False)):
            res = _drive(p, [ev], target, elevation)
            if touched:
                own = required_force(ev.slices, ev.surface, target,
                                     "janbu_simplified", elevation,
                                     project=p)
                assert res.required_force == own.governing_force > 0.0
                assert (res.surfaces_analysed, res.surfaces_untouched) == (
                    1, 0)
                assert not res.notes, res.notes
            else:
                assert res.critical is None and math.isnan(
                    res.required_force), elevation
                assert (res.surfaces_analysed, res.surfaces_untouched) == (
                    0, 1)
                note = res.notes["error"]
                assert note is res.notes["untouched_skipped"]
                assert note.code == RM.BACK_NONE_UNTOUCHED
                assert note.args["n"] == 1 and note.args["y"] == elevation
                assert abs(note.args["lo"] - 19.0) < 1e-9
                assert abs(note.args["hi"] - 25.0) < 1e-9

    def test_at_or_above_the_target_it_is_not_analysed(self):
        """"Below" is the reference's word: a surface exactly at the target
        needs nothing either."""
        from ogr_slip2d import run_messages as RM
        p, ev = _one()
        for target in (ev.fos, 0.9 * ev.fos, 1.0):
            res = _drive(p, [ev], target, 22.0)
            assert res.critical is None and math.isnan(res.required_force)
            assert (res.surfaces_analysed, res.surfaces_above_target,
                    res.surfaces_untouched) == (0, 1, 0)
            note = res.notes["error"]
            assert note.code == RM.BACK_NONE_ABOVE_TARGET
            assert set(res.notes) == {"error", "above_target"}
        res = _drive(p, [ev], ev.fos * (1.0 + 1e-9), 22.0)
        assert res.critical is not None and res.surfaces_above_target == 0

    def test_zero_at_its_own_factor(self):
        """The identity, unclipped, on a surface the back analysis analyses
        (Bishop 1955; Janbu 1954): priced with the method's own two sums at
        its own factor, to 1e-9 of its weight."""
        import ogr_slip2d.back_analysis as BA
        for mid in ("janbu_simplified", "bishop_simplified"):
            p, ev = _one(mid)
            sl = list(ev.slices)
            resisting, driving, arm = BA._sums_at_fixed_fos(
                sl, ev.surface, ev.fos, 0.0, 0.0, 22.0, mid,
                stress_fos=ev.fos, project=p)
            passive = (ev.fos * driving - resisting) / arm
            weight = sum(s.weight for s in sl)
            assert abs(passive) <= _TOL_W * weight, (mid, passive / weight)

    def test_a_crest_inside_a_slice_is_on_the_top_of_the_run_too(self):
        """An embankment whose crest is one vertex, (25, 20): a circle that
        enters on the flat behind it (elevation 15) and leaves on the front
        face passes under the crest, and the slice edges on either side of
        it are below 20. A force just under the crest touches that mass;
        read off the slice edges alone it would not."""
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.back_analysis import ground_of, mass_top_range
        from ogr_slip2d.surface import SlipCircle
        p = Project(name="Embankment")
        ext = Polyline(vertices=[Vertex(0.0, 0.0), Vertex(60.0, 0.0),
                                 Vertex(60.0, 10.0), Vertex(45.0, 10.0),
                                 Vertex(25.0, 20.0), Vertex(20.0, 15.0),
                                 Vertex(0.0, 15.0)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_material(Material(
            name="Fill", strength=MohrCoulomb(cohesion=10.0,
                                              friction_angle=25.0),
            unit_weight=19.0))
        p.settings.methods.enabled_methods = ["janbu_simplified"]
        ev = build_search(p, "janbu_simplified").evaluate_circle(
            p, SlipCircle(centre_x=32.0, centre_y=32.0,
                          radius=math.hypot(17.0, 17.0)))
        assert ev is not None and ev.is_valid
        edges = mass_top_range(ev.slices)
        lo, hi = mass_top_range(ev.slices, ground_of(p))
        assert hi == 20.0 and edges[1] < 19.95, (edges, lo, hi)
        assert abs(lo - edges[0]) < 1e-9, (edges, lo)
        target = 1.2 * ev.fos
        res = _drive(p, [ev], target, 19.95)
        assert res.critical is not None and res.surfaces_untouched == 0
        assert _drive(p, [ev], target, 20.05).surfaces_untouched == 1

    def test_which_reason_is_said_when_several_hold(self):
        """A run with one surface above the target and one the force does
        not touch says the one that stays below it. And with Bishop, every
        circle at the target and a surface that is not a circle, it says
        that no force is needed, with the note of the surface Bishop cannot
        price beside it -- that note alone was given as the reason (the
        review of 0.1.441); it IS the reason when there is nothing else."""
        from ogr_slip2d import run_messages as RM
        p, ev = _one()
        low = NS(**{k: getattr(ev, k) for k in (
            "is_valid", "slices", "surface", "admissible", "details")},
            fos=1.0)
        res = _drive(p, [ev, low], 1.2, 35.0)
        assert res.notes["error"].code == RM.BACK_NONE_UNTOUCHED
        assert (res.surfaces_above_target, res.surfaces_untouched) == (1, 1)
        assert "above_target" not in res.notes

        p, circle = _one("bishop_simplified")
        polyline = NS(is_valid=True, slices=circle.slices, surface=NS(),
                      admissible=True, details={}, fos=1.0)
        res = _drive(p, [circle, polyline], 1.2, 22.0, "bishop_simplified")
        assert res.notes["error"].code == RM.BACK_NONE_ABOVE_TARGET
        assert res.notes["error"] is res.notes["above_target"]
        assert res.notes["not_circular_skipped"].args == {"n": 1}
        res = _drive(p, [polyline], 1.2, 22.0, "bishop_simplified")
        assert res.notes["error"] is res.notes["not_circular_skipped"]
        assert res.surfaces_above_target == 0

    def test_the_range_given_is_the_hull_and_says_so(self):
        """Two masses the force passes between: neither is touched, and the
        range the note gives is the hull of their tops, which holds the
        force's elevation. The sentence says "over part of" that range."""
        from ogr_slip2d import run_messages as RM
        p, _ev = _one()

        def mass(lo, hi, x):
            return NS(is_valid=True, admissible=True, details={}, fos=1.0,
                      surface=NS(), slices=[NS(
                          base_x_left=x, top_y_left=hi,
                          base_x_right=x + 1.0, top_y_right=lo)])
        res = _drive(p, [mass(15.0, 18.0, 1.0), mass(22.0, 25.0, 3.0)],
                     1.2, 20.0)
        note = res.notes["error"]
        assert note.code == RM.BACK_NONE_UNTOUCHED
        assert note.args == {"y": 20.0, "n": 2, "lo": 15.0, "hi": 25.0}
        assert str(note).endswith("each of those masses meets the ground "
                                  "over part of the range of elevations "
                                  "15.00 to 25.00.")

    def test_the_progress_is_reported_for_the_surfaces_left_out(self):
        """It was the last line of the loop, which a surface left out never
        reaches: with all of them left out the bar stood still, and Cancel
        comes in through that call."""
        from ogr_slip2d.back_analysis import run_back_analysis
        p, ev = _one()
        seen = []
        search = NS(run=lambda _p: NS(evaluations=[ev] * 45),
                    slice_store=None)
        res = run_back_analysis(p, search, 0.9 * ev.fos, 22.0,
                                "janbu_simplified",
                                progress_cb=lambda d, t: seen.append((d, t)))
        assert res.surfaces_above_target == 45
        assert seen == [(0, 45), (20, 45), (40, 45), (45, 45)], seen


# ======================================================================
class TestTheRun:
    """The 64-circle grid of the ficha."""

    def test_above_the_crest_there_is_no_force_and_it_says_why(self):
        from ogr_slip2d import run_messages as RM
        for mid, without in (("janbu_simplified", (145.99, 145.99)),
                             ("bishop_simplified", (228.25, 547.80))):
            for elevation, was in zip((28.0, 35.0), without):
                res = _back(mid, 1.5, elevation)
                assert res.critical is None and math.isnan(
                    res.required_force)
                note = res.notes["error"]
                assert note is res.notes["untouched_skipped"]
                assert note.code == RM.BACK_NONE_UNTOUCHED
                n = 52 - _ABOVE[mid]
                assert note.args == {"y": elevation, "n": n,
                                     "lo": note.args["lo"], "hi": 25.0}
                assert 15.0 <= note.args["lo"] < 25.0
                assert (res.surfaces_analysed, res.surfaces_above_target,
                        res.surfaces_untouched) == (0, _ABOVE[mid], n)
                # and the screens are what changed it: without them, the
                # force 0.1.440 published
                old = _back(mid, 1.5, elevation, screens=False)
                assert "%.2f" % old.required_force == "%.2f" % was
                assert old.surfaces_analysed == 52

    def test_with_every_surface_above_the_target_it_says_so(self):
        from ogr_slip2d import run_messages as RM
        res = _back("janbu_simplified", 1.0, 20.0)
        assert res.critical is None
        assert res.notes["error"].code == RM.BACK_NONE_ABOVE_TARGET
        assert (res.surfaces_analysed, res.surfaces_above_target,
                res.surfaces_untouched) == (0, 52, 0)
        old = _back("janbu_simplified", 1.0, 20.0, screens=False)
        assert old.required_force == 0.0
        assert "%.4f" % old.critical.unsupported_fos == "5.2543"

    def test_where_it_touches_and_is_below_nothing_moves(self):
        for mid in ("janbu_simplified", "bishop_simplified"):
            res = _back(mid, 1.5, 20.0)
            old = _back(mid, 1.5, 20.0, screens=False)
            assert res.required_force == old.required_force

            def geometry(c):            # each run gives its surfaces an id
                return {k: v for k, v in c.surface.items() if k != "id"}
            assert geometry(res.critical) == geometry(old.critical)
            assert res.critical.unsupported_fos == \
                old.critical.unsupported_fos
            assert _is(res.required_force, _V1440[mid])
            assert (res.surfaces_analysed, res.surfaces_above_target,
                    res.surfaces_untouched) == (52 - _ABOVE[mid],
                                                _ABOVE[mid], 0)
            # nothing to warn of, no note (D340)
            assert not res.notes, res.notes
            assert not old.notes and old.surfaces_above_target == 0

    def test_a_local_surface_left_out_is_said(self):
        """At elevation 16 the force touches only the masses that leave the
        ground at or below it: 8 of the ones below the target do not, and
        the force found does nothing for them."""
        from ogr_slip2d import run_messages as RM
        for mid, shown in (("janbu_simplified", "145.99"),
                           ("bishop_simplified", "114.12")):
            res = _back(mid, 1.5, 16.0)
            assert "%.2f" % res.required_force == shown
            assert res.required_force == _back(
                mid, 1.5, 16.0, screens=False).required_force
            assert set(res.notes) == {"untouched_skipped"}
            note = res.notes["untouched_skipped"]
            assert note.code == RM.BACK_UNTOUCHED_LEFT_OUT
            assert note.args == {"n": 8, "y": 16.0}
            assert res.surfaces_untouched == 8

    def test_active_equals_passive_at_a_target_of_one(self):
        """On the reference slope, whose critical factor is below 1.0: the
        governing surface is one the back analysis analyses, and at F = 1
        the two assumptions are the same sum."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from test_slide_validation_ej1 import _ej1_project
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.back_analysis import run_back_analysis
        from ogr_slip2d.search import GridSearch
        search = GridSearch(method=BishopSimplified(), grid_x=(70, 100),
                            grid_y=(60, 85), grid_nx=4, grid_ny=4,
                            radius_increment=8, min_radius=15,
                            num_slices=18, min_area=0.5)
        res = run_back_analysis(_ej1_project(), search, target_fos=1.0,
                                elevation=30.0)
        c = res.critical
        assert c is not None and res.surfaces_analysed > 0
        assert c.unsupported_fos < 1.0 and c.active_force > 0.0
        assert abs(c.active_force - c.passive_force) < 1e-6
        assert res.surfaces_above_target > 0


# ======================================================================
class TestTheDoors:

    def _interpret(self, target, elevation):
        from PySide6.QtWidgets import QApplication, QInputDialog
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_slip2d.analysis_runner import run_analysis
        QApplication.instance() or QApplication([])
        if "run" not in _ONE:
            p = _demo()
            _ONE["run"] = (p, run_analysis(p))
        p, outcome = _ONE["run"]
        w = InterpretWindow(p, dict(outcome.results), None,
                            factor_report=outcome.factor_report)
        answers = iter([(target, True), (elevation, True)])
        said = []
        try:
            with _swapped(QInputDialog, "getDouble",
                          staticmethod(lambda *a, **k: next(answers))), \
                    _swapped(w, "_info", lambda text, *a: said.append(text)):
                w._back_analysis_report()
        finally:
            w.close()
            w.deleteLater()
        return said, outcome.results["janbu_simplified"].critical

    def test_interpret_says_them_of_the_critical_surface(self):
        with _language("en"):
            said, crit = self._interpret(1.0, 20.0)
            assert said == ["This surface already reaches the target factor "
                            "(%.4g): it needs no support force." % crit.fos]
            said, _c = self._interpret(1.5, 28.0)
            assert len(said) == 1 and said[0].startswith(
                "The force at elevation 28 does not touch the sliding mass "
                "of this surface, which meets the ground between elevations "
                "15.74 and 25.00: no support force is reported."), said
            # below the target, with the force on its face: as in 0.1.440.
            # v0.1.443 (D401) -- changed on purpose: a line more, after the
            # first, says which surface was priced (the owner's decision)
            said, _c = self._interpret(1.5, 20.0)
            first, rest = _MESSAGE_1440.split("\n", 1)
            assert said == [first + "\nBack-analysed on the critical surface "
                            "of the run (Janbu Simplified).\n" + rest]
        with _language("es"):
            said, crit = self._interpret(1.0, 20.0)
            assert said == ["Esta superficie ya alcanza el factor objetivo "
                            "(%.4g): no necesita fuerza de soporte."
                            % crit.fos]
            said, _c = self._interpret(1.5, 28.0)
            assert said[0].startswith("La fuerza a la cota 28 no toca la "
                                      "masa deslizante de esta superficie")

    def test_the_agent_gets_the_reason_and_the_counts(self):
        import json
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = ws.add(_demo()).id
            out = call(ws, "back_analysis_run", project_id=pid,
                       target_fos=1.5, elevation=35.0,
                       method_id="janbu_simplified", wait_seconds=300)
            s = out["summary"]
            json.dumps(s)
            assert s["required_force"] is None and s["surfaces"] == 0
            assert (s["surfaces_above_target"], s["surfaces_untouched"]) == (
                41, 11)
            assert s["notes"]["error"].startswith(
                "The force at elevation 35 does not touch the sliding mass "
                "of any of the 11 surface(s) below the target factor")
            out = call(ws, "back_analysis_run", project_id=pid,
                       target_fos=1.5, elevation=20.0,
                       method_id="janbu_simplified", wait_seconds=300)
            s = out["summary"]
            assert _is(s["required_force"], _V1440["janbu_simplified"])
            assert (s["surfaces"], s["surfaces_above_target"],
                    s["surfaces_untouched"]) == (11, 41, 0)
            assert s["notes"] == {}
        finally:
            ws.shutdown()

    def test_the_modellers_box_says_the_reason_once(self):
        """The window says the error and then every other note of the run:
        the count that IS the reason is the same object under both keys."""
        from PySide6.QtWidgets import QApplication, QDialog
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        with _language("es"):
            w = MainWindow()
            try:
                w._attach_project(_demo())
                said = []
                for elevation in (35.0, 16.0):
                    w._back_analysis_last = {
                        "target_fos": 1.5, "elevation": elevation,
                        "method_id": "janbu_simplified"}
                    with _swapped(QDialog, "exec",
                                  lambda self: QDialog.DialogCode.Accepted), \
                            _swapped(w, "_info",
                                     lambda text, *a: said.append(text)):
                        w._back_analysis()
                assert len(said) == 1, said
                assert said[0].count("La fuerza a la cota 35 no toca") == 1
                assert "\n" not in said[0]
                # at 16 there is a force, and the note of the 8 left out
                bar = w.statusBar().currentMessage()
                assert bar.startswith("Retroanálisis (Janbu simplificado): "
                                      "fuerza necesaria 146.0 kN/m"), bar
                notes = [str(n) for _t, ns in w.last_task_notes[
                    "back_analysis"] for n in ns]
                # its own note, beside the run's warnings (this model's
                # failure direction, D426)
                own = [n for n in notes if n.startswith(
                    "8 surface(s) below the target factor were left out")]
                assert len(own) == 1, notes
                assert "[%d nota(s)" % len(notes) in bar, bar
            finally:
                w.project.is_dirty = False
                w.close()
                w.deleteLater()
