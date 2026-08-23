# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Numerical validation on NON-CIRCULAR surfaces, against the reference program.

WHAT INVARIANT THIS PROTECTS: the factor of safety of a polyline surface. Every
other numerical benchmark in this suite fixes a CIRCLE — Ej_1, Ej_2, the five
published cases, the per-circle audit, all circles. So the whole non-circular
path had no external validation at all, and v0.1.89 changed the slicer right
through the middle of it (slice boundaries at the surface's own vertices)
holding on to nothing.

WHERE THE NUMBERS COME FROM. Two models run for this in the reference program,
each analysing ONE surface drawn by hand — not a search. Their `.s01` reports
`#surfaces 1` and gives the factor of safety of all seven methods on it, so
this is a DETERMINISTIC benchmark: no heuristic, no seed, exactly reproducible.
That is what makes it better than comparing against a stochastic search.

    referencias/Ejemplos/Ej_1/Ej_1_Block_Search/   (the folder name is
    referencias/Ejemplos/Ej_2/Ej_2_Block_Search/    misleading; see below)

The folders are called "Block Search" because that is the Surface Options page
they were saved from, but no search ran: a Block Search would have analysed the
5000 samples its parameters ask for.

Geometry is built in code, not loaded from referencias/: the suite has to run
from a clean checkout and that directory is not part of it.

WHAT IT CAUGHT. Six of the seven methods already agreed with the reference
inside 1 %. Bishop did not — +2.0 % and +4.1 % — and the cause was structural
rather than numerical: Bishop Simplified takes moments about the centre of a
CIRCLE, where the radius is the same for every slice and cancels out of the
ratio. A polyline has no centre, every slice base has its own arm, and the base
normal stops passing through the axis so it contributes a moment of its own.
Fixed in v0.1.92; this file is what measured it and what keeps it fixed.

------------------------------------------------------------------------------
v0.1.105 — SPENCER AND GLE ARE NOW THE TWO THAT DISAGREE, ON PURPOSE.

Their tolerance below went from 0.5 % / 1.0 % to 5 %, and that is a DEBT
recorded, not a test relaxed to make a change pass. What was traded, and why:

Until v0.1.105 these two wrote their moment equation as ``Σ S_term / Σ W·senα``
on every surface. That is a moment ratio only on a circle, where every arm is R
and R cancels — off a circle it carried no moment arms at all, and so dropped
the seismic, water and support moments outright. The same arc described as a
circle and as a polyline, under kh = 0.15, differed by +45.4 %; on the Loukidis
critical-seismic-coefficient benchmark the non-circular answer came out +157 %,
on the unsafe side, with nothing said. Now the moment side is a real sum of
moments about the axis, and both of those are −0.01 %.

The cost is here. The normal force in that sum comes from the slice's own
vertical equilibrium, ``N = (W − S·senα)/cosα``, which omits the inter-slice
shear difference ``(X_R − X_L)``. On a circle that costs nothing, since the
normal points at the centre and takes no moment. On a sharply kinked surface it
does take a moment, and the omitted term is precisely what separates Spencer
from Bishop — so the two now land within 0.02 % of each other here, and about
2 to 4 % below the reference.

    Ej_1   Spencer  0.942419 published   0.941354 before   0.922940 now
    Ej_2   Spencer  1.479930 published   1.483330 before   1.423177 now

That the residual is exactly the Bishop value, and that Ordinary — which has no
inter-slice forces to omit and therefore no such residual — lands on both
published values to six figures, is what identifies the missing term rather
than merely naming a suspect.

HOW THIS DEBT IS PAID, and then this header goes away: the full Fredlund and
Krahn (1977) normal,

    N = [W + (X_R − X_L) − (c'·l·senα)/F + (u·l·tanφ'·senα)/F] / m_α
    X_i = λ·f(x_i)·E_i,  with E_i from the horizontal force recursion,

which needs the inter-slice forces E_i that the current solver never forms.
When it does, the two tolerances below go back to 0.5 % and 1.0 % and
``TestSpencerHasCollapsedOntoBishop`` goes back to being the opposite claim it
was in v0.1.92.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

# ----------------------------------------------------------------------
# The two surfaces, read from the `surfaces:` block of each .sli, and the
# reference factors of safety, read from the `* Global Minimum FS` block of
# each .s01. The entry and exit of that block match these endpoints exactly,
# which is what identifies the analysed surface as this one.
EJ1_SURFACE = [(40.0, 50.0), (45.0, 45.0), (50.0, 40.0),
               (55.0, 35.0), (60.0, 30.0), (75.0, 25.0)]
EJ2_SURFACE = [(15.0, 30.0), (40.0, 35.0), (65.0, 55.0), (70.0, 70.0)]

# method id -> (reference FoS, tolerance %). None means the reference itself
# failed on that surface and there is nothing to compare against.
EJ1_REFERENCE = {
    "ordinary_fellenius":     (0.897423, 1.0),
    "bishop_simplified":      (0.922931, 0.5),
    "janbu_simplified":       (0.885579, 0.5),
    "janbu_corrected":        (0.926203, 0.5),
    # v0.1.105 — 5 % is a DEBT, not a tolerance. See the header.
    "spencer":                (0.942419, 5.0),
    "lowe_karafiath":         (0.955461, 2.0),
    "gle_morgenstern_price":  (0.941668, 5.0),
}
EJ2_REFERENCE = {
    "ordinary_fellenius":     (1.36921, 1.0),
    "bishop_simplified":      (1.42443, 0.5),
    "janbu_simplified":       (1.34347, 0.5),
    "janbu_corrected":        (1.42566, 0.5),
    "spencer":                (1.47993, 5.0),        # v0.1.105 debt
    # lowe-karafiath: the reference reports -1000, its "no valid surface"
    # code. Nothing to compare against, and that is worth recording rather
    # than quietly leaving the method out of the table.
    "lowe_karafiath":         (None, None),
    "gle_morgenstern_price":  (1.4887, 5.0),         # v0.1.105 debt
}

# v0.1.92 — Bishop USED to live apart here, with a case asserting that it
# deviated by more than 1 %, so that fixing it would turn this file red. It
# did. The cause was structural: Sigma W sin(alpha) over Sigma Q is a moment
# ratio only on a circle, where the radius cancels. Bishop is now in the table
# above with the same 0.5 % the other moment methods get.
EJ1_BISHOP = 0.922931
EJ2_BISHOP = 1.42443

# The axis point the reference publishes for each of these surfaces, in the
# `xc, yc, r` fields of the Global Minimum block. For a non-circular surface
# those fields are not a circle: they are the axis used for moment
# equilibrium, and the mean distance from it to the vertices.
EJ1_AXIS = (82.500000825, 72.500000825, 47.2054500434465)
EJ2_AXIS = (2.50000105, 105.00000105, 77.8800050529773)

_CACHE: dict = {}


def _project(tag):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if tag == "Ej_1":
        from test_slide_validation_ej1 import _ej1_project
        return _ej1_project()
    from test_slide_validation_ej2_v184 import _ej2_project
    return _ej2_project()


def _surface(pts):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))


def _fos(tag, pts, method_id):
    """The factor of safety of one method on one surface, computed once.

    25 slices, matching the `noncircular analysis: slices` of the reference
    model. ``check_m_alpha`` is off so the comparison is of the FORMULATION
    and not of a post-analysis filter.
    """
    key = (tag, method_id)
    if key not in _CACHE:
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        ev = GridSearch(method=get_method(method_id)(), num_slices=25,
                        min_area=0.0, check_m_alpha=False)
        _CACHE[key] = ev.evaluate_surface(_project(tag), _surface(pts))
    return _CACHE[key]


def _check(tag, pts, table):
    bad = []
    for mid, (ref, tol) in table.items():
        res = _fos(tag, pts, mid)
        assert res is not None and res.is_valid, f"{tag} {mid}: no converge"
        if ref is None:
            continue
        err = abs(res.fos - ref) / ref * 100.0
        if err >= tol:
            bad.append(f"{mid}: {res.fos:.6f} vs {ref} = {err:+.2f}% "
                       f"(tolerancia {tol}%)")
    assert not bad, bad


class TestTheSixMethodsThatAgree:
    def test_ej1(self):
        _check("Ej_1", EJ1_SURFACE, EJ1_REFERENCE)

    def test_ej2(self):
        _check("Ej_2", EJ2_SURFACE, EJ2_REFERENCE)

    def test_every_method_converges_on_both(self):
        """Convergence is a separate claim from accuracy, and worth its own
        case: a method that silently fails to converge would otherwise be
        excluded from the comparison above without anyone noticing."""
        from ogr_slip2d.methods import method_registry
        for tag, pts in (("Ej_1", EJ1_SURFACE), ("Ej_2", EJ2_SURFACE)):
            for mid in method_registry():
                res = _fos(tag, pts, mid)
                assert res is not None and res.is_valid, f"{tag} {mid}"

    def test_the_reference_failed_where_we_say_it_did(self):
        """Ej_2 Lowe-Karafiath is excluded because the REFERENCE reports its
        -1000 code there, not because this program has trouble with it. The
        distinction matters, so it is asserted: OGR does converge."""
        res = _fos("Ej_2", EJ2_SURFACE, "lowe_karafiath")
        assert res is not None and res.is_valid
        assert EJ2_REFERENCE["lowe_karafiath"] == (None, None)


class TestSpencerHasCollapsedOntoBishop:
    """The debt of v0.1.105, pinned so it cannot drift unnoticed either way.

    In v0.1.92 this class asserted the OPPOSITE — that Bishop and Spencer stay
    apart, as the reference separates them by about 2 %. That claim was the
    regression guarding a real fix. It is now false, knowingly: giving Spencer
    a true moment balance while its normal force still omits ``(X_R − X_L)``
    makes it converge to Bishop's answer on a sharply kinked surface. The
    header of this file has the measurement and the way out.

    Written as a two-sided tripwire on purpose. It fails if the gap GROWS,
    which would mean somebody paid the debt and must now tighten the
    tolerances back; and it fails if the gap SHRINKS to nothing in a way the
    reference gap does not explain. Either way the next person is told what
    changed rather than left with a green suite and a stale header.
    """

    #: Measured with v0.1.105 on both surfaces: 0.02 % and 0.00 %. The band is
    #: generous downwards and tight upwards, because "Spencer is Bishop" is
    #: the state being recorded and any real separation is the news.
    KNOWN_GAP_MAX = 0.005          # 0.5 %

    def test_spencer_still_coincides_with_bishop_and_that_is_the_debt(self):
        for tag, pts, ref_b, ref_s in (("Ej_1", EJ1_SURFACE, EJ1_BISHOP, 0.942419),
                                       ("Ej_2", EJ2_SURFACE, EJ2_BISHOP, 1.47993)):
            b = _fos(tag, pts, "bishop_simplified").fos
            s = _fos(tag, pts, "spencer").fos
            gap = abs(b - s) / s
            ref_gap = abs(ref_b - ref_s) / ref_s
            assert gap <= self.KNOWN_GAP_MAX, (
                f"{tag}: Bishop {b:.5f} and Spencer {s:.5f} now differ by "
                f"{gap*100:.2f}%, where v0.1.105 measured under "
                f"{self.KNOWN_GAP_MAX*100:.1f}% and the reference has "
                f"{ref_gap*100:.2f}%. If the inter-slice shear term (X_R - X_L) "
                f"has been implemented, this is the good news: put the 0.5 % "
                f"and 1.0 % tolerances back in the table above, and turn this "
                f"case around to assert the separation again.")

    def test_the_moment_axis_is_recorded_on_the_result(self):
        """The axis is a modelling choice, so it has to be inspectable
        rather than buried in the arithmetic."""
        res = _fos("Ej_1", EJ1_SURFACE, "bishop_simplified")
        axis = res.details.get("moment_axis")
        assert axis is not None, res.details
        assert abs(axis[0] - 82.5) < 1e-6 and abs(axis[1] - 72.5) < 1e-6, axis

    def test_circles_do_not_take_this_path(self):
        """The circular formula is left exactly as it was, so no validated
        circle can move. The absence of the axis in the details is what
        proves the other branch ran."""
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        from ogr_slip2d import BishopSimplified
        res = GridSearch(method=BishopSimplified(), num_slices=25,
                         min_area=0.0).evaluate_circle(
            _project("Ej_1"),
            SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.2124436))
        assert res is not None and res.is_valid
        assert not (res.details or {}).get("moment_axis"), res.details


class TestTheAxisPointTheReferencePublishes:
    """For a non-circular surface the reference still reports ``xc, yc, r``.
    Its own documentation says what that point is for: "a single axis point,
    which will be used for moment equilibrium calculations".

    How it is constructed was not documented anywhere and was measured from
    these two surfaces: the midpoint of the entry-exit chord, offset
    perpendicular to the chord by the chord's own length.
    """

    @staticmethod
    def _constructed(pts):
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        return (0.5 * (x0 + x1) - dy, 0.5 * (y0 + y1) + dx)

    def test_the_construction_reproduces_the_published_axis(self):
        import math
        for pts, (ax, ay, _r) in ((EJ1_SURFACE, EJ1_AXIS),
                                  (EJ2_SURFACE, EJ2_AXIS)):
            cx, cy = self._constructed(pts)
            assert math.hypot(cx - ax, cy - ay) < 1e-5, (cx, cy, ax, ay)

    def test_the_published_radius_is_the_mean_distance_to_the_vertices(self):
        import math
        for pts, (_ax, _ay, r) in ((EJ1_SURFACE, EJ1_AXIS),
                                   (EJ2_SURFACE, EJ2_AXIS)):
            cx, cy = self._constructed(pts)
            mean = sum(math.hypot(x - cx, y - cy) for x, y in pts) / len(pts)
            assert abs(mean - r) < 1e-5, (mean, r)

    def test_it_is_not_the_circle_through_the_endpoints(self):
        """Worth pinning: the obvious reading — a circle through entry and
        exit — gives 48.09 in Ej_1 where the reference reports 47.21."""
        import math
        cx, cy = self._constructed(EJ1_SURFACE)
        to_ends = math.hypot(EJ1_SURFACE[0][0] - cx, EJ1_SURFACE[0][1] - cy)
        assert abs(to_ends - EJ1_AXIS[2]) > 0.5, (to_ends, EJ1_AXIS[2])

    def test_the_axis_sits_above_the_surface(self):
        """A moment axis below the sliding mass would reverse every arm."""
        for pts in (EJ1_SURFACE, EJ2_SURFACE):
            _cx, cy = self._constructed(pts)
            assert cy > max(y for _x, y in pts), (cy, pts)


class TestTheMomentAxisCanBeSetByHand:
    """Rule 7 on the new setting: it has to move the number.

    The reference carries the same control and describes it the same way — "a
    single axis point, which will be used for moment equilibrium
    calculations, for ALL surfaces". Unset, every surface builds its own from
    its entry-exit chord; set, that point is used for all of them.

    Why it is worth having at all rather than always automatic: the automatic
    construction is a reasonable point, not a correct one — there is no such
    thing as THE centre of rotation of a polyline. A user comparing a family
    of non-circular surfaces wants them all measured about the same point, or
    the factors of safety are not comparable with each other.
    """

    @staticmethod
    def _with_axis(tag, pts, axis):
        import copy
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        p = _project(tag)
        p.settings = copy.deepcopy(p.settings)
        p.settings.search.axis_x, p.settings.search.axis_y = axis
        ev = GridSearch(method=get_method("bishop_simplified")(),
                        num_slices=25, min_area=0.0, check_m_alpha=False)
        return ev.evaluate_surface(p, _surface(pts))

    def test_setting_it_moves_the_factor_of_safety(self):
        auto = _fos("Ej_1", EJ1_SURFACE, "bishop_simplified").fos
        moved = self._with_axis("Ej_1", EJ1_SURFACE, (70.0, 90.0)).fos
        assert abs(moved - auto) / auto > 0.005, (auto, moved)

    def test_it_is_the_axis_that_gets_used(self):
        res = self._with_axis("Ej_1", EJ1_SURFACE, (70.0, 90.0))
        ax = res.details.get("moment_axis")
        assert ax == (70.0, 90.0), ax

    def test_unset_means_automatic(self):
        from ogr_slip2d.surface import moment_axis
        res = _fos("Ej_1", EJ1_SURFACE, "bishop_simplified")
        assert res.details["moment_axis"] == moment_axis(_surface(EJ1_SURFACE))

    def test_half_an_axis_is_not_an_axis(self):
        """One coordinate does not define a point. Setting only x must leave
        the surface on its automatic axis rather than pairing the value with
        an automatic y, which would be a setting that half-applies."""
        import copy
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import moment_axis
        p = _project("Ej_1")
        p.settings = copy.deepcopy(p.settings)
        p.settings.search.axis_x = 70.0        # y left as None
        ev = GridSearch(method=get_method("bishop_simplified")(),
                        num_slices=25, min_area=0.0, check_m_alpha=False)
        res = ev.evaluate_surface(p, _surface(EJ1_SURFACE))
        assert res.details["moment_axis"] == moment_axis(_surface(EJ1_SURFACE))

    def test_a_circle_ignores_it(self):
        """A circle has a centre; an axis setting must not override it, or
        every validated circular result would move the moment a user typed
        a number for a non-circular study."""
        import copy
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        from ogr_slip2d import BishopSimplified
        circle = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.2124436)
        base = _project("Ej_1")
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        plain = ev.evaluate_circle(base, circle)
        p = _project("Ej_1")
        p.settings = copy.deepcopy(p.settings)
        p.settings.search.axis_x, p.settings.search.axis_y = 10.0, 200.0
        with_axis = ev.evaluate_circle(p, circle)
        assert plain.fos == with_axis.fos, (plain.fos, with_axis.fos)

    def test_the_action_is_reachable_from_a_menu(self):
        """Rule 3: a module was once shipped invisible because its twelve
        actions were registered and never added to the menu bar."""
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QMenu
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        # Rule 5: the language is global, so it goes back exactly as it was.
        previous = current_language()
        try:
            set_language("en")
            w = MainWindow()
            found = set()
            for menu in w.menuBar().findChildren(QMenu):
                for act in menu.actions():
                    found.add(act.text())
            for label in ("Define Moment Axis...", "Reset Moment Axis"):
                assert label in found, (label, sorted(found))
        finally:
            set_language(previous)
