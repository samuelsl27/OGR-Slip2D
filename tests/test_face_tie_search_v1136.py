# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Which ground segment is the slope face, when two of them are equally steep.

Four sites in the engine locate the slope face the same way: walk the
ground profile and keep the steepest segment. On a symmetric embankment,
a homogeneous dam, a dyke with two benches at the same batter, that
comparison separates nothing — and a strict ``>`` hands the decision to
iteration order, which is always left to right. Only Path Search broke
the tie (v0.1.73, from the declared Failure Direction). The three others
did not: ``slope_frame`` (which frames Slope Search AND Particle Swarm),
Block Search and Simulated Annealing. Rule 7, defect D34.

**The invariant this file protects, and it has two halves that pull in
opposite directions:**

1. where the geometry is ambiguous, the declaration decides — the same
   embankment searched left-to-right and right-to-left must give two
   DIFFERENT searches, in every search that locates a face;
2. where the geometry is not ambiguous, the declaration must be unable
   to touch anything. A face that is genuinely the steepest keeps
   winning; flat ground has no face at all. Both are asserted bit for
   bit (``rel_tol=1e-12``), because that is what keeps every validated
   case out of the reach of the change.

Half 2 is the one worth guarding. Wiring a setting into a question the
geometry already answers correctly makes results worse while leaving
them plausible, which is the failure mode nobody sees.

**What the benchmark bank could contribute: nothing, and it is worth
writing down why.** All six of its Block Search models carry user-drawn
Block Search objects, and with those present the automatic-window branch
— the only consumer of the chosen face in that search — is never
reached. No model uses Slope Search or Simulated Annealing at all, and
none of its Particle Swarm models has tied faces. So the bank cannot
move a digit either way, and the evidence for this defect lives here.
"""
import math

from ogr_slip2d.failure_direction import steepest_face_index


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
def _project(name, vertices, cohesion=15.0, phi=30.0):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[Vertex(x, y) for x, y in vertices], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Fill",
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=phi))]
    return p


def _embankment():
    """Two faces of IDENTICAL inclination — the tie the setting breaks.

    Left face 20 → 40 rising 5 → 25, right face 60 → 80 falling 25 → 5:
    both at exactly 45°, so no comparison of steepness can separate them.
    The same shape ``test_failure_direction_v173`` uses for Path Search,
    on purpose: the other three sites have to answer it the same way.
    """
    return _project("embankment", [
        (0, 0), (100, 0), (100, 5), (80, 5),
        (60, 25), (40, 25), (20, 5), (0, 5)])


def _one_face():
    """An ordinary slope: one face, and it is genuinely the steepest."""
    return _project("one face", [
        (0, 0), (60, 0), (60, 10), (35, 10), (15, 30), (0, 30)],
        cohesion=10.0, phi=25.0)


def _l2r(project):
    from ogr_core.project.units import FailureDirection
    project.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    return project


def _r2l(project):
    from ogr_core.project.units import FailureDirection
    project.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
    return project


# ----------------------------------------------------------------------
# The searches that locate a face, kept deliberately small: this file
# measures WHERE they look, not how well they converge.
# ----------------------------------------------------------------------
def _searches():
    from ogr_slip2d import PathSearch
    from ogr_slip2d.methods import BishopSimplified
    from ogr_slip2d.particle_swarm import ParticleSwarmSearch
    from ogr_slip2d.search import (BlockSearch, SimulatedAnnealingSearch,
                                   SlopeSearch)

    def m():
        return BishopSimplified()

    return {
        # slope_frame() — ONE site, two searches reading it.
        "SlopeSearch": lambda: SlopeSearch(
            method=m(), num_surfaces=200, num_slices=20, seed=7),
        "ParticleSwarmSearch": lambda: ParticleSwarmSearch(
            method=m(), num_particles=12, num_iterations=8,
            num_slices=20, seed=7),
        "BlockSearch": lambda: BlockSearch(
            method=m(), num_surfaces=200, num_slices=20, seed=7),
        "SimulatedAnnealingSearch": lambda: SimulatedAnnealingSearch(
            method=m(), generation_steps=30, num_slices=20, seed=7),
        # Already covered by test_failure_direction_v173; included so the
        # extraction of its tie-break is shown to be an extraction.
        "PathSearch": lambda: PathSearch(
            method=m(), num_paths=12, num_slices=20, seed=7),
    }


def _mean_surface_x(result):
    """Where the search looked, averaged over every surface it evaluated.

    Read off the surfaces rather than out of the search's internals: the
    defect is that the face decides where the search goes, and a test
    that inspected the chosen index would pass on a face that was chosen
    and then ignored. Circles are placed by their centre, polylines by
    the mean abscissa of their vertices.
    """
    xs = []
    for r in result.evaluations:
        surface = r.surface
        polyline = getattr(surface, "polyline", None)
        vertices = getattr(polyline, "vertices", None)
        if vertices:
            xs.append(sum(v.x for v in vertices) / len(vertices))
        elif getattr(surface, "centre_x", None) is not None:
            xs.append(surface.centre_x)
    assert xs, "the search produced no surface to look at"
    return sum(xs) / len(xs)


class TestTheFixturesSayWhatTheyClaim:

    def test_the_two_faces_of_the_embankment_are_equally_steep(self):
        """Without this the tests below would be measuring the steepness
        comparison instead of the tie-break."""
        top = _embankment().external_boundary().polyline.vertices
        slopes = [abs((b.y - a.y) / (b.x - a.x))
                  for a, b in zip(top, top[1:]) if abs(b.x - a.x) > 1e-9]
        assert slopes.count(max(slopes)) >= 2, slopes

    def test_the_one_face_slope_does_not_tie(self):
        top = _one_face().external_boundary().polyline.vertices
        slopes = [abs((b.y - a.y) / (b.x - a.x))
                  for a, b in zip(top, top[1:]) if abs(b.x - a.x) > 1e-9]
        assert slopes.count(max(slopes)) == 1, slopes


class TestEverySearchBreaksTheTie:
    """Half 1: where the geometry is ambiguous, the declaration decides."""

    def test_each_direction_starts_from_its_own_side(self):
        for name, make in _searches().items():
            x_r2l = _mean_surface_x(make().run(_r2l(_embankment())))
            x_l2r = _mean_surface_x(make().run(_l2r(_embankment())))
            # The mass exits at the toe, so a right-to-left failure works
            # the left-hand face and looks at smaller x than a
            # left-to-right one does. Before v0.1.136 these two numbers
            # were equal in every search but Path Search.
            assert x_r2l < x_l2r, (name, x_r2l, x_l2r)

    def test_the_default_keeps_the_face_the_old_code_chose(self):
        """No stored project may change its answer by being reopened.

        The old strict ``>`` always kept the FIRST steepest segment, i.e.
        the left-hand face; right-to-left is the default and picks that
        same one, so the default is unchanged.
        """
        for name, make in _searches().items():
            plain = _mean_surface_x(make().run(_embankment()))
            r2l = _mean_surface_x(make().run(_r2l(_embankment())))
            assert math.isclose(plain, r2l, rel_tol=1e-12), (name, plain, r2l)


class TestAFaceThatWinsKeepsWinning:
    """Half 2: the trap. Where the geometry answers, the setting cannot."""

    def test_a_single_face_slope_is_untouched_by_the_setting(self):
        for name, make in _searches().items():
            x_r2l = _mean_surface_x(make().run(_r2l(_one_face())))
            x_l2r = _mean_surface_x(make().run(_l2r(_one_face())))
            assert math.isclose(x_r2l, x_l2r, rel_tol=1e-12), (
                name, x_r2l, x_l2r)


class TestTheRuleItself:
    """The shared function, where every edge is cheap to state exactly."""

    class _V:
        def __init__(self, x, y):
            self.x = float(x)
            self.y = float(y)

    def _profile(self, pts):
        return [self._V(x, y) for x, y in pts]

    def _strict(self, top):
        """The pre-v0.1.136 rule, written out so the test compares
        against it rather than against a remembered number."""
        best_i, best = 0, -1.0
        for i in range(len(top) - 1):
            dx = top[i + 1].x - top[i].x
            if abs(dx) < 1e-9:
                continue
            s = abs((top[i + 1].y - top[i].y) / dx)
            if s > best:
                best, best_i = s, i
        return best_i

    def _tied(self):
        return self._profile([(0, 5), (20, 5), (40, 25), (60, 25),
                              (80, 5), (100, 5)])

    def test_a_tie_goes_to_the_declared_direction(self):
        top = self._tied()
        assert steepest_face_index(top, _r2l(_embankment())) == 1
        assert steepest_face_index(top, _l2r(_embankment())) == 3

    def test_right_to_left_reproduces_the_strict_comparison(self):
        top = self._tied()
        assert (steepest_face_index(top, _r2l(_embankment()))
                == self._strict(top))

    def test_a_genuinely_steeper_face_ignores_the_direction(self):
        """Two faces at 0.5 and 0.4995 — a thousand times outside the
        1e-6 band, so the geometry answers and the setting may not."""
        top = self._profile([(0, 0), (20, 10), (40, 10),
                             (60, 10 - 10 * (1 - 1e-3))])
        assert steepest_face_index(top, _r2l(_embankment())) == 0
        assert steepest_face_index(top, _l2r(_embankment())) == 0

    def test_the_near_tie_band_is_relative(self):
        """A face steeper by one part in 1e9 is still a tie, and the same
        geometry answers the same question in metres and in millimetres."""
        for scale in (1.0, 1000.0):
            rise = 10 * scale
            top = self._profile([(0, 0), (20 * scale, rise),
                                 (40 * scale, rise),
                                 (60 * scale, rise - rise * (1 - 1e-9))])
            assert steepest_face_index(top, _r2l(_embankment())) == 0, scale
            assert steepest_face_index(top, _l2r(_embankment())) == 2, scale

    def test_flat_ground_has_no_face_for_the_direction_to_choose(self):
        """With every segment horizontal the near-tie band would swallow
        all of them, and a horizontal segment is not a face. Twenty-three
        benchmark models are shaped like that: a vertical wall whose
        upper envelope is entirely flat."""
        top = self._profile([(0, 10), (20, 10), (40, 10), (60, 10)])
        assert steepest_face_index(top, _r2l(_embankment())) == 0
        assert steepest_face_index(top, _l2r(_embankment())) == 0
        assert (steepest_face_index(top, _l2r(_embankment()))
                == self._strict(top))

    def test_a_profile_with_no_usable_segment_answers_zero(self):
        top = self._profile([(0, 0), (0, 10)])
        assert steepest_face_index(top, _r2l(_embankment())) == 0
        assert steepest_face_index(top, _l2r(_embankment())) == 0
