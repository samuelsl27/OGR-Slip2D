# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.213 — a slice that enters its solver with NO shear strength, because
the stress its envelope was read at is negative and was clipped, is declared
instead of silent (defect D84).

WHAT IS DECLARED. Every method reads the strength envelope once per slice at
an effective normal stress and clips a negative one to zero. With
Mohr-Coulomb the point does not matter. With an envelope through the origin
(a power curve with ``c = d = 0``) the tangent at zero is zero, and the slice
resists nothing. Each method publishes those slices in
``details["zero_strength_slices"]``, and ``analysis_runner.zero_strength_note``
says so.

WHICH STRESS, AND WHY THE FILE HAS TWO HALVES. In the same version D84
stopped reading a curved envelope at the Fellenius estimate: it is now read
at the stress each method resolves, iterated to the fixed point
(``methods.base.self_consistent_envelope``, switch
``ENVELOPE_AT_OWN_STRESS``).

* With the switch OFF, the stress is the Fellenius estimate, and that is
  where the ficha found the defect: on problem 41 four slices entered with
  nothing while the method's own solution put +30 to +215 kPa on them. The
  identity below pins that path.
* With the switch ON, a flagged slice is a base in TENSION at the solution
  itself. Problem 41 flags none; the same surface at ru = 0.8 under Spencer
  flags the four head slices, whose own stress is -1.6 to -12.2 kPa.

THE IDENTITY (rule 1), switch off. With the pore pressure given by a
coefficient ru, ``u = ru*gamma*h`` at the base midpoint, and the weight of a
trapezoidal slice of a homogeneous soil is ``gamma*b*h``. So

    W*cos(alpha) - u*l = gamma*b*h*(cos(alpha) - ru/cos(alpha)),

which is negative EXACTLY where cos^2(alpha) < ru. The eight methods that
start from that estimate must flag exactly those slices. The Ordinary
Method's own effective normal, ``W*cos(alpha) - u*l*cos^2(alpha)`` (Turnbull
& Hvorslev 1967), is ``gamma*b*h*cos(alpha)*(1 - ru)``, never negative for
ru < 1, so it must flag none. Checked on the critical surface of
verification problem 41 (Jiang, Baker & Yamagami 2003, tau = 1.4*sigma'^0.8)
at five values of ru.

THE IDENTITY, switch on. A flagged slice is exactly one whose published
``envelope_stress`` (the stress the solve was read at) is negative.

DISCRIMINATION against the v0.1.212 tree: see the changelog of v0.1.213
(measured on the first version of this file, which pinned the switch-off
half only: 11 of 13 failed).
"""
from __future__ import annotations

import math

EIGHT = ("bishop_simplified", "janbu_simplified", "janbu_corrected",
         "spencer", "gle_morgenstern_price", "lowe_karafiath",
         "corps_engineers_1", "corps_engineers_2")
ORDINARY = "ordinary_fellenius"

#: Verification problem 41: outline and the critical Path Search surface the
#: bench archives for Bishop and Janbu (the same polyline for both).
OUTLINE_41 = [(0, 0), (93, 0), (93, 10), (85, 10), (5, 30), (0, 30)]
SURFACE_41 = [(13.7554, 27.8112), (16.6576, 22.8278), (19.6772, 17.6429),
              (22.6967, 12.4581), (25.7162, 7.2733), (30.6765, 3.8975),
              (36.1935, 1.539), (42.1071, 0.5244), (48.1009, 0.251),
              (54.0447, 1.0699), (59.9575, 2.0891), (65.6032, 4.1204),
              (71.1937, 6.299), (76.7842, 8.4777), (82.3747, 10.6563)]
N_41 = 30
#: Verification problem 40: the surface its statement gives, in five slices.
OUTLINE_40 = [(0, 53), (4, 53), (105, 3), (115, 3), (115, -10), (0, -10)]
SURFACE_40 = [(4, 53), (20, 16), (40, 8), (60, 4), (80, 1), (105, 3)]
N_40 = 5
#: The ru values of the identity. Chosen so no base of the surface lies
#: within 1e-3 of the threshold cos^2(alpha) = ru (asserted below).
RU_VALUES = (0.2, 0.3, 0.4, 0.5, 0.6)
#: The ru at which Spencer's own solution puts the head slices in tension.
RU_TENSION = 0.8

_CACHE: dict = {}


# ======================================================================
def _project(outline, strength, ru=None):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in outline], closed=True)
    ext.ensure_ccw()
    p = Project("zero strength")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    kw = {}
    if ru is not None:
        kw = dict(pore_pressure=PorePressureType.RU_COEFFICIENT, ru=ru)
    mat = Material(name="soil", unit_weight=20.0, sat_unit_weight=20.0,
                   strength=strength, **kw)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _power(a=1.4, b=0.8, c=0.0, d=0.0):
    from ogr_core.materials.builtin_models import PowerCurve
    return PowerCurve(a=a, b=b, c=c, d=d, waviness=0.0)


def _surface(vertices):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in vertices], closed=False))


def _run(key, project, vertices, n, method_id, own_stress):
    """One solve, with the switch set as asked and PUT BACK: the runner has
    no teardown, and a switch left off would change every later file."""
    k = (key, method_id, own_stress)
    if k in _CACHE:
        return _CACHE[k]
    from ogr_slip2d.methods import base, method_registry
    from ogr_slip2d.slicer import slice_surface
    surf = _surface(vertices)
    slices = slice_surface(project, surf, num_slices=n)
    assert slices is not None
    # ``getattr``: on a tree without the switch this sets a name nobody
    # reads, which is the old reading, so the cases fail on behaviour.
    old = getattr(base, "ENVELOPE_AT_OWN_STRESS", None)
    base.ENVELOPE_AT_OWN_STRESS = own_stress
    try:
        res = method_registry()[method_id]().compute_fos(project, surf,
                                                         slices)
    finally:
        if old is None:
            vars(base).pop("ENVELOPE_AT_OWN_STRESS", None)
        else:
            base.ENVELOPE_AT_OWN_STRESS = old
    _CACHE[k] = res
    return res


def _problem_41(ru=0.3, strength=None, method_id="bishop_simplified",
                own_stress=False):
    key = ("41", ru, repr(strength and strength.params))
    p = _project(OUTLINE_41, strength or _power(), ru=ru)
    return _run(key, p, SURFACE_41, N_41, method_id, own_stress)


def _problem_40(method_id, own_stress):
    p = _project(OUTLINE_40, _power(a=2.0, b=0.7))
    return _run("40", p, SURFACE_40, N_40, method_id, own_stress)


def _flagged(res):
    assert res.fos is not None, (res.method_id, res.reason,
                                 res.error_message)
    return list(res.details.get("zero_strength_slices"))


def _below_threshold(res, ru):
    return [i for i, s in enumerate(res.slices.slices)
            if math.cos(s.base_angle) ** 2 < ru]


# ======================================================================
class TestTheIdentityAtTheFelleniusEstimate:
    """Switch off: cos^2(alpha) < ru, slice for slice, in every method."""

    def test_the_threshold_is_well_clear_of_every_base(self):
        """Guard: a base within float noise of cos^2(alpha) = ru would make
        the identity a coin toss."""
        res = _problem_41()
        for ru in RU_VALUES:
            gap = min(abs(math.cos(s.base_angle) ** 2 - ru)
                      for s in res.slices.slices)
            assert gap > 1e-3, (ru, gap)

    def test_the_eight_flag_exactly_the_bases_below_it(self):
        for ru in RU_VALUES:
            for mid in EIGHT:
                res = _problem_41(ru=ru, method_id=mid)
                want = _below_threshold(res, ru)
                assert _flagged(res) == want, (ru, mid, _flagged(res), want)

    def test_the_witness_has_something_to_flag(self):
        """Guard: at ru = 0.3 the identity is not satisfied vacuously."""
        assert _below_threshold(_problem_41(), 0.3) == [0, 1, 2, 3]

    def test_the_ordinary_method_flags_none(self):
        """Its own effective normal is gamma*b*h*cos(a)*(1 - ru) >= 0."""
        for ru in RU_VALUES:
            res = _problem_41(ru=ru, method_id=ORDINARY)
            assert _flagged(res) == [], (ru, _flagged(res))

    def test_without_water_nothing_is_flagged(self):
        for mid in EIGHT + (ORDINARY,):
            res = _problem_41(ru=0.0, method_id=mid)
            assert _flagged(res) == [], (mid, _flagged(res))


class TestAtTheMethodsOwnStress:
    """Switch on, the default: a flagged slice is a base in tension."""

    def test_problem_41_flags_none(self):
        for mid in EIGHT + (ORDINARY,):
            res = _problem_41(method_id=mid, own_stress=True)
            assert res.converged, (mid, res.reason)
            assert _flagged(res) == [], (mid, _flagged(res))

    def test_a_base_in_tension_at_the_solution_is_flagged(self):
        res = _problem_41(ru=RU_TENSION, method_id="spencer",
                          own_stress=True)
        env = res.details["envelope_stress"]
        in_tension = [i for i, v in enumerate(env) if v is not None and v < 0]
        assert in_tension == [0, 1, 2, 3], in_tension
        assert _flagged(res) == in_tension


class TestOnlyAStrengthlessTangentIsFlagged:
    """A clipped stress is not enough: the envelope has to have nothing at
    zero. Same surface, same ru = 0.3, at the Fellenius estimate."""

    def test_mohr_coulomb_without_cohesion(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        for mid in EIGHT:
            res = _problem_41(strength=MohrCoulomb(cohesion=0.0,
                                                   friction_angle=30.0),
                              method_id=mid)
            assert _flagged(res) == [], (mid, _flagged(res))

    def test_a_power_curve_with_an_intercept(self):
        for strength in (_power(c=2.0), _power(d=5.0)):
            res = _problem_41(strength=strength)
            assert _flagged(res) == [], (strength.params, _flagged(res))

    def test_a_soil_with_no_strength_at_all_is_not_flagged(self):
        """That soil did not LOSE its strength to the stress it was read at."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        p = _project(OUTLINE_41, _power(a=0.0), ru=0.3)
        sl = slice_surface(p, _surface(SURFACE_41), num_slices=N_41)
        s = sl.slices[0]
        assert BishopSimplified._zero_strength(s, -1.0, 0.0, 0.0) is False


class TestTheNote:

    def test_it_fires_on_problem_41_at_the_fellenius_estimate(self):
        from ogr_slip2d.analysis_runner import zero_strength_note
        notes = zero_strength_note(_problem_41())
        assert len(notes) == 1, notes
        assert notes[0].startswith(
            "4 slices entered with zero shear strength (slices 1, 2, 3, 4)")

    def test_it_is_silent_on_problem_41_at_the_methods_own_stress(self):
        from ogr_slip2d.analysis_runner import zero_strength_note
        assert zero_strength_note(_problem_41(own_stress=True)) == []

    def test_it_is_silent_on_problem_40(self):
        from ogr_slip2d.analysis_runner import zero_strength_note
        for own in (False, True):
            for mid in EIGHT + (ORDINARY,):
                res = _problem_40(mid, own)
                assert _flagged(res) == [], (mid, own, _flagged(res))
                assert zero_strength_note(res) == [], (mid, own)

    def test_it_reaches_the_analysis_notes(self):
        """Through ``run_analysis``, so the note is where the interface, the
        command line and the MCP server read it. A Path Search of twenty
        surfaces on problem 41 (0.1 s), switch off, reports a critical
        surface with steep head slices of its own."""
        from ogr_core.project.units import FailureDirection
        from ogr_slip2d.analysis_runner import run_analysis, zero_strength_note
        from ogr_slip2d.methods import base
        p = _project(OUTLINE_41, _power(), ru=0.3)
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        p.settings.methods.num_slices = N_41
        s = p.settings.search
        s.search_method = "path"
        s.surface_type = "non_circular"
        s.path_num_surfaces = 20
        p.settings.statistics.seed = 1
        p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
        p.settings.advanced.parallel_search = False
        old = getattr(base, "ENVELOPE_AT_OWN_STRESS", None)
        base.ENVELOPE_AT_OWN_STRESS = False
        try:
            out = run_analysis(p)
        finally:
            if old is None:
                vars(base).pop("ENVELOPE_AT_OWN_STRESS", None)
            else:
                base.ENVELOPE_AT_OWN_STRESS = old
        crit = out.results["bishop_simplified"].critical
        # Guard: the search has to report a surface with something to say.
        assert _flagged(crit), crit.details.get("zero_strength_slices")
        note = zero_strength_note(crit)[0]
        assert "bishop_simplified: " + note in out.warnings, out.warnings

    def test_the_api_publishes_the_slices(self):
        from ogr_api.results import lem_summary
        summary = lem_summary(_problem_41())
        assert summary["details"]["zero_strength_slices"] == [0, 1, 2, 3]
        quiet = lem_summary(_problem_41(ru=0.0))
        assert "zero_strength_slices" not in (quiet.get("details") or {})


class TestNothingMoves:
    """The flag is a reading of what the solver did, not a change to it."""

    def test_a_flagged_slice_is_linearised_to_nothing(self):
        """Switch off, problem 41: the four flagged slices contribute c = 0
        and tan(phi) = 0 at zero stress, which is what the flag says."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        res = _problem_41()
        for i in _flagged(res):
            s = res.slices.slices[i]
            assert BishopSimplified._local_c_phi(s, s.material, 0.0) == (
                0.0, 0.0), i
