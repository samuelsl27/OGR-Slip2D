# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the program says — and does NOT refuse — about total inter-slice forces.

WHAT INVARIANT THIS PROTECTS.

v0.1.144 made TOTAL the default inter-slice convention for the three
methods that PRESCRIBE the inter-slice inclination — see
``test_interslice_split_v1117.py`` for the evidence and
``docs/PENDIENTES.md`` §7 for the decision. That convention has one price,
and it is not a defect: where water STANDS on the slope, raising the water
adds a purely horizontal force to every vertical face, so an assumption
that ties the resultant to a prescribed θ cannot leave the factor of
safety alone. Two things follow, and this file pins both.

**One: the program says so.** ``settings_warnings`` carries a model-level
note whenever a prescribed-inclination method meets water standing over
the ground. The control that gives it meaning is the one that must NOT
fire: a water table INSIDE the slope is the case total forces exist for,
and a note that appeared there too would be telling every wet model the
same thing and therefore nothing.

**Two: it does NOT refuse the answer, and that is a measured decision.**
On the submerged slope of Duncan and Wright (2005) figure 6.27 — bank
problem 70 — with the water 60 ft above the crest, the march converges,
quietly, on F = 0.22 where every other method says 1.60, and a whole grid
search of that model returns 0.2001. Four criteria for rejecting such a
root were measured, and all four failed:

* the **residual** — it is a genuine zero, |Z_n|/max|Z_i| = 9e-12, so the
  pole guard inside ``_march`` cannot see it;
* the **net inter-slice thrust**, which is how Spencer and GLE reject
  their spurious roots (``interslice.thrust_is_admissible``) — the sum
  comes out compressive in the good root AND in the spurious one;
* **counting slice bases in tension** — bank problem 51 has legitimate
  roots with 1 and 2 of 95 in tension, 0.75 of the way up from the toe,
  so a threshold of one eats good answers and a threshold of three misses
  this one, which has one;
* the **thrust reversal** below, which separates them cleanly on the
  published circles (below 3 % against 28 %) and NOT in a real search
  population: over 22 000 surfaces of nine bank models, a cut at 5 % would
  mark 1087 of the 4605 surfaces of problem 55, and in problems 59 and 60
  the 99th percentile is 1.0 in EFFECTIVE forces — the setting validated
  against the reference. A veto there would change which surface is
  reported as critical on models that are not in any trouble.

So the reversal ships as a DIAGNOSTIC in ``details["thrust_reversal"]``
and the warning ships as the note above. What this file pins is that the
two populations really are different animals on the circles where a
published value exists, so the diagnostic keeps meaning something, and
that nothing silently started vetoing on it.

Reference for the idea of rejecting a root by the sign of the inter-slice
forces, which is where the reversal comes from:

    Ching, R.K.H. & Fredlund, D.G. (1983). "Some difficulties associated
    with the limit equilibrium method of slices." Can. Geotech. J. 20(4),
    661-672.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material, PorePressureType
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project import Project
from ogr_slip2d.analysis_runner import build_method, settings_warnings
from ogr_slip2d.search import GridSearch
from ogr_slip2d.surface import SlipCircle

PRESCRIBED = ("lowe_karafiath", "corps_engineers_1", "corps_engineers_2")

#: A fragment of the note, chosen so it cannot match any other warning.
NOTE_MARK = "water standing over the ground"


# ======================================================================
# Duncan and Wright (2005), figure 6.27 — bank problem 70. Submerged.
# ======================================================================
P70_EXTERNAL = [(0, 0), (140, 0), (140, 45), (105, 45), (30, 15), (0, 15)]
P70_CIRCLE = dict(centre_x=49.42, centre_y=88.56, radius=76.08)
P70_SLICES = 50


def _p70(water_y: float) -> Project:
    p = Project("Duncan and Wright 2005 fig. 6.27, ponded at %g" % water_y)
    ext = Polyline(vertices=[Vertex(x, y) for x, y in P70_EXTERNAL],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(-10, water_y), Vertex(150, water_y)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    soil = Material(name="Soil", unit_weight=128.0, sat_unit_weight=128.0,
                    use_sat_unit_weight=True,
                    strength=MohrCoulomb(cohesion=100.0, friction_angle=20.0),
                    pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [soil]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), soil.id)
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    return p


# ======================================================================
# Pockoski and Duncan (2000), test slope 1 — bank problem 55. The water
# table runs INSIDE the slope and daylights at the toe: the case total
# forces are the right convention for, and the control for the note.
# ======================================================================
P55_EXTERNAL = [(-75, 75), (170, 75), (170, 150), (100, 150), (0, 100),
                (-75, 100)]
P55_WATER_TABLE = [(-75, 100), (0, 100), (100, 140), (170, 140)]


def _p55() -> Project:
    p = Project("Pockoski and Duncan 2000, test slope 1")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in P55_EXTERNAL],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in P55_WATER_TABLE], closed=False),
        btype=BoundaryType.WATER_TABLE))
    soil = Material(name="sandy clay", unit_weight=120.0,
                    sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=300.0, friction_angle=30.0),
                    pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [soil]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), soil.id)
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    return p


def _has_note(project, method_ids) -> bool:
    return any(NOTE_MARK in w for w in settings_warnings(project, method_ids))


# ======================================================================
class TestTheNoteSaysWhenTheConventionCosts:

    def test_it_fires_on_a_submerged_slope(self):
        for mid in PRESCRIBED:
            assert _has_note(_p70(105.0), [mid]), mid

    def test_it_stays_quiet_when_the_water_is_inside_the_slope(self):
        """THE control. Bank problem 55 is wet from toe to crest and is
        exactly the case total forces reproduce to 0.25 %. A note that
        fired here as well would be a note about water, not about the
        assumption, and would train the user to ignore it."""
        for mid in PRESCRIBED:
            assert not _has_note(_p55(), [mid]), mid

    def test_it_stays_quiet_for_the_methods_that_cannot_read_the_setting(self):
        for mid in ("bishop_simplified", "spencer", "janbu_simplified",
                    "gle_morgenstern_price", "ordinary_fellenius"):
            assert not _has_note(_p70(105.0), [mid]), mid

    def test_it_stays_quiet_when_the_user_already_chose_effective(self):
        """The note names a consequence of TOTAL forces. Once the project
        asks for effective ones there is no consequence to name, and the
        way out it recommends has already been taken."""
        p = _p70(105.0)
        p.settings.methods.interslice_forces = "effective"
        assert not _has_note(p, list(PRESCRIBED))

    def test_it_names_the_way_out(self):
        """A warning that does not say what to do instead is a warning the
        user cannot act on. Duncan and Wright publish the alternative with
        the very case that needs it — buoyant unit weights, no water."""
        note = [w for w in settings_warnings(_p70(105.0), ["lowe_karafiath"])
                if NOTE_MARK in w][0]
        assert "buoyant" in note
        assert "Effective" in note

    def test_it_does_not_pretend_the_answer_was_refused(self):
        """The note is the whole of the protection, so it has to say the
        number is unreliable — it is not accompanied by a refusal, and a
        user who reads it as "slightly less accurate" has been misled."""
        note = [w for w in settings_warnings(_p70(105.0), ["lowe_karafiath"])
                if NOTE_MARK in w][0]
        assert "unreliable" in note

    def test_it_is_asked_once_per_analysis_and_not_once_per_surface(self):
        """Same shape as every other model-level note: it depends on the
        model and the methods, never on a trial surface. Pinned by the
        signature, because the cost of getting this wrong is thousands of
        copies of one sentence."""
        import inspect

        from ogr_slip2d.analysis_runner import _interslice_convention_notes
        params = list(inspect.signature(
            _interslice_convention_notes).parameters)
        assert params == ["project", "method_ids"]


# ======================================================================
class TestTheThrustReversalDiagnostic:
    """The number that separates the two roots where a published value
    exists — and the reason it is only a diagnostic.

    Every root below is on a circle the reference publishes a factor of
    safety for, so "legitimate" is an external claim and not our opinion.
    """

    #: The spurious root of bank problem 70 with total forces, and the
    #: published circle of bank problem 55, which reproduces Pockoski and
    #: Duncan (2000) 1.318 to 0.2 % in the same convention.
    P55_CIRCLE = dict(centre_x=23.333, centre_y=192.778, radius=98.2325)
    P55_SLICES = 30

    def _result(self, project, method_id, circle, num_slices):
        method = build_method(project, method_id, num_slices)
        assert method is not None, method_id
        r = GridSearch(method=method, num_slices=num_slices,
                       min_area=0.0).evaluate_circle(
            project, SlipCircle(**circle))
        assert r is not None and r.is_valid, method_id
        return r

    def test_every_published_root_keeps_its_thrust_in_one_sense(self):
        for mid in PRESCRIBED:
            r = self._result(_p55(), mid, self.P55_CIRCLE, self.P55_SLICES)
            rev = r.details["thrust_reversal"]
            assert rev < 0.03, (mid, rev)

    def test_the_spurious_root_turns_a_quarter_of_its_thrust_around(self):
        """And it is the same model, the same method and the same circle
        as the effective-forces root next door: only the convention
        differs. Two-sided, because a diagnostic that quietly stopped
        distinguishing them would leave the note as the only thing
        standing between the user and 0.22."""
        p = _p70(105.0)
        good = self._result(p, "lowe_karafiath", P70_CIRCLE, P70_SLICES)
        assert good.fos < 0.5, good.fos          # the spurious root itself
        assert good.details["thrust_reversal"] > 0.15, good.details

        p_eff = _p70(105.0)
        p_eff.settings.methods.interslice_forces = "effective"
        ok = self._result(p_eff, "lowe_karafiath", P70_CIRCLE, P70_SLICES)
        assert 1.5 < ok.fos < 1.7, ok.fos
        assert ok.details["thrust_reversal"] < 0.03, ok.details

    def test_it_is_published_and_nothing_vetoes_on_it(self):
        """Rule 7 read backwards. The reversal is NOT wired to
        ``admissible``, and that is deliberate — measured over 22 000
        surfaces of nine bank models, a cut at 5 % marks 1087 of the 4605
        surfaces of bank problem 55, whose critical circle is validated
        against a published value. If someone wires it up, this test is
        where they have to come and say what changed."""
        p = _p70(105.0)
        r = self._result(p, "lowe_karafiath", P70_CIRCLE, P70_SLICES)
        assert r.details["thrust_reversal"] > 0.15
        assert r.admissible is True
        assert r.admissibility_note == ""
