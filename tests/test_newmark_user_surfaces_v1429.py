# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.429 (D397) — the Newmark displacement of a run covers every surface it
analysed, the ones the user drew by hand included.

The invariant: with "Compute Ky" and Newmark on, every analysed surface with
a yield acceleration gets its displacement, the headline reports the
displacement of the critical surface (the lowest Ky) whoever drew it, and
the count of surfaces left without a Ky counts the user's too. Until this
version only the search population got one, so a hand-drawn surface
reported as critical had none: the headline fell back to Ky without a word,
and the surfaces of the run showed 8.95 cm as the largest movement while the
critical one would move 34.8 cm (the demo slope, a Path Search of 5
surfaces, Bishop, the polyline [(19, 25), (25, 18), (31, 14.5), (37, 15)]
and a 0.3 g sinusoid of 2 Hz for 4 s at dt 0.01 s: the bench's d397).

The command line had two faults of its own, one test each. It decided
"Newmark is on" from the FIRST method's critical alone, so a first method
left without a critical surface put the whole column under "Critical Ky"
and hid every other method's displacement; and a critical surface without
one -- the user's, before this version -- raised KeyError in its row, which
aborted the command before it printed the table or saved any result.

The reference is external, Newmark (1965), three times, on a plane:

* the yield acceleration of a cohesionless plane is ``k_y = tan(φ − β)``,
  the closed form ``tests/test_yield_acceleration_v1127.py`` checks with the
  same model, here on the plane given as the user's polyline (Janbu, which
  reproduces it because on a plane in cohesionless soil every slice is at
  the same factor, whatever its weight);
* the displacement under a single rectangular pulse is
  ``u = V²/(2 g N)·(1 − N/A)``, the closed form
  ``tests/test_newmark_v1127.py`` checks on the integrator alone: here it is
  checked on what the RUN attaches to the user's surface;
* the yield acceleration of the wedge as a rigid block with cohesion, in
  closed form, which puts the plane in a 500 kPa soil far above the ceiling
  the solver searches below: the premise of the count's test.

The user's plane is made the critical surface the honest way: a focus point
far outside the model rejects every surface the search generates, and focus
objects do not apply to the user's surfaces (v0.1.157, D58).

Cost: about a second the file (1.08 s measured alone). Four small runs of a
60-slice plane, each computed once and shared: the focused one and the
strong one, a few hundredths of a second; the open one and the two-method
one the command-line tests share, under half a second each. And two
command-line invocations, a few hundredths each.
"""
from __future__ import annotations

import math
import os

_PHI = 30.0
_PLANE = ((2.0, 2.0), (30.0, 10.0))
_BETA = math.degrees(math.atan2(_PLANE[1][1] - _PLANE[0][1],
                                _PLANE[1][0] - _PLANE[0][0]))
_KY_EXACT = math.tan(math.radians(_PHI - _BETA))
_A, _T0, _DT = 0.5, 1.0, 0.000625      # the pulse: 0.5 g for 1 s
_STRONG_C = 500.0                      # kPa: no Ky below the ceiling


def _block_ky(cohesion):
    """Newmark (1965): the yield acceleration of the wedge above the plane
    as a rigid block, ``F(k) = 1`` solved in closed form for
    ``F = (c L + W (cos b - k sin b) tan phi) / (W (sin b + k cos b))``.
    The wedge is the triangle (2, 2), (10, 10), (30, 10) of dry sand."""
    (x0, y0), (x1, y1) = _PLANE
    length = math.hypot(x1 - x0, y1 - y0)
    area = 0.5 * abs((10.0 - x0) * (y1 - y0) - (x1 - x0) * (10.0 - y0))
    w = 20.0 * area
    b, t = math.radians(_BETA), math.tan(math.radians(_PHI))
    return ((cohesion * length + w * math.cos(b) * t - w * math.sin(b))
            / (w * (math.cos(b) + math.sin(b) * t)))


def _closed_form(amplitude_g, critical_g, duration_s):
    """Newmark (1965), single rectangular pulse. Metres."""
    from ogr_core.loads.seismic_record import STANDARD_GRAVITY_CM_S2
    g = STANDARD_GRAVITY_CM_S2 / 100.0
    v = amplitude_g * g * duration_s
    return v * v / (2.0 * g * critical_g) * (1.0 - critical_g / amplitude_g)


def _record():
    """The pulse, then quiet ground long enough for the block to stop: it
    slides until ``(A/N)·t0``, and a tail chosen without that arithmetic
    truncates the answer (tests/test_newmark_v1127.py, 26 %)."""
    from ogr_core.loads.seismic_record import SeismicRecord
    stop = (_A / _KY_EXACT) * _T0
    return SeismicRecord(
        name="pulse", dt=_DT,
        accelerations=([_A] * int(round(_T0 / _DT))
                       + [0.0] * int(round((1.5 * stop + 1.0) / _DT))))


def _plane_project(methods=("janbu_simplified",), focus=True, cohesion=0.0):
    """A 45 degree face over flat ground, dry sand, the plane as the user's
    polyline, Ky and Newmark on with the pulse."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.geometry.focus import FocusKind, FocusObject
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import UserPolylineSurface
    p = Project("plane")
    p.boundaries.append(Boundary(
        polyline=Polyline([Vertex(0, 0), Vertex(40, 0), Vertex(40, 10),
                           Vertex(10, 10)], closed=True),
        btype=BoundaryType.EXTERNAL))
    p.materials.append(Material(
        name="Sand", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=_PHI)))
    p.seismic.enabled = True
    p.seismic.kh = 0.0
    p.seismic.kv = 0.0
    s = p.settings.search
    s.surface_type, s.search_method = "non_circular", "path"
    s.path_num_surfaces = 5
    s.optimize_enabled = False
    p.settings.methods.enabled_methods = list(methods)
    # 60 as in tests/test_yield_acceleration_v1127.py. Until v0.1.458 it had
    # to be: with 25 the slicer refused this two-vertex plane without a reason
    # (D407, test_slice_last_cut_v1458). Kept at 60 so that no number of this
    # file moves (the owner's decision, 2026-11-15).
    p.settings.methods.num_slices = 60
    if focus:
        p.focus_objects = [FocusObject(kind=FocusKind.POINT,
                                       points=[(45.0, -40.0)],
                                       tolerance=0.01)]
    p.user_polylines = [UserPolylineSurface.from_points(list(_PLANE))]
    record = _record()
    p.seismic_records = [record]
    cfg = p.settings.seismic
    cfg.newmark = True
    cfg.record_id = record.id
    return p


# v0.1.429 -- the runs these tests only read, computed once. File-local
# (tests/test_shared_test_caches_v1378.py fails if another file reaches it).
_SHARED: dict = {}


def _outcome(name):
    if name not in _SHARED:
        from ogr_slip2d.analysis_runner import run_analysis
        project = {"focus": lambda: _plane_project(),
                   "open": lambda: _plane_project(focus=False),
                   "strong": lambda: _plane_project(cohesion=_STRONG_C),
                   "two": lambda: _plane_project(
                       ("corps_engineers_1", "janbu_simplified")),
                   }[name]()
        _SHARED[name] = (project, run_analysis(project))
    return _SHARED[name]


# ======================================================================
class TestNewmarkOnTheUsersPlane:
    """The plane is the user's polyline and the critical surface."""

    def _critical(self):
        _p, out = _outcome("focus")
        res = out.results["janbu_simplified"]
        return res, res.critical

    def test_the_critical_surface_is_the_users(self):
        res, crit = self._critical()
        assert res.evaluations == []          # the focus rejected them all
        assert crit is not None and res.is_user_surface(crit)
        assert res.objective == "ky"

    def test_its_yield_acceleration_is_the_closed_form(self):
        _res, crit = self._critical()
        ky = crit.details["ky"]
        assert abs(ky - _KY_EXACT) / _KY_EXACT < 1e-6, (ky, _KY_EXACT)

    def test_its_displacement_is_newmarks_closed_form(self):
        """At the run's own Ky, so the comparison is of the displacement
        alone; the residue left is the integrator's, where the block stops
        between two samples (measured 2.4e-8 at this step)."""
        _res, crit = self._critical()
        ky = crit.details["ky"]
        moved = crit.details["newmark_displacement"]
        expected = _closed_form(_A, ky, _T0)
        assert abs(moved - expected) / expected < 1e-6, (moved, expected)

    def test_it_is_the_integrators_answer_for_its_ky(self):
        from ogr_slip2d.newmark import displacement_for_record
        project, _out = _outcome("focus")
        _res, crit = self._critical()
        record = project.seismic_records[0]
        alone = displacement_for_record(record, float(crit.details["ky"]))
        assert crit.details["newmark_displacement"] == alone.displacement

    def test_the_headline_is_its_displacement(self):
        from ogr_api.results import headline
        from ogr_slip2d.reported import NEWMARK, reported_caption
        _p, out = _outcome("focus")
        res, crit = self._critical()
        assert reported_caption(res) == NEWMARK
        head = headline(res, out.factor_report)
        assert head["caption"] == "newmark" and head["unit"] == "m", head
        assert abs(head["value"] - crit.details["newmark_displacement"]) \
            < 1e-6, head


# ======================================================================
class TestEverySurfaceWithAKyGetsADisplacement:

    def test_the_searchs_and_the_users(self):
        _p, out = _outcome("open")
        res = out.results["janbu_simplified"]
        assert res.evaluations and res.user_evaluations
        missing = []
        for r in list(res.evaluations) + list(res.user_evaluations):
            ky = (r.details or {}).get("ky") if r.is_valid else None
            if ky is not None and math.isfinite(ky):
                if "newmark_displacement" not in r.details:
                    missing.append(r)
        assert not missing, len(missing)


# ======================================================================
class TestTheSurfacesWithoutAKyCountTheUsers:
    """The note that counts the surfaces left without a Ky counts the user's.

    The plane in a soil with c = 500 kPa: as a rigid block its yield
    acceleration is about 8.4 by Newmark's closed form, eight times the
    ceiling of 1 the solver searches below, so no method finds one. The
    focus leaves it the only surface of the run. Before this version the
    count read the search alone, said nothing, and the run was left without
    a critical surface with no word of why."""

    def test_the_closed_form_puts_its_ky_above_the_ceiling(self):
        from ogr_slip2d.yield_acceleration import DEFAULT_K_MAX
        # the same formula with no cohesion is the sand's tan(phi - beta)
        assert abs(_block_ky(0.0) - _KY_EXACT) < 1e-12
        assert _block_ky(_STRONG_C) > 8.0 * DEFAULT_K_MAX

    def test_the_note_counts_it(self):
        from ogr_core.messages import METHOD_NOTE
        from ogr_slip2d.yield_acceleration import DEFAULT_K_MAX
        _p, out = _outcome("strong")
        res = out.results["janbu_simplified"]
        assert res.evaluations == [] and len(res.user_evaluations) == 1
        assert res.user_evaluations[0].is_valid
        assert res.critical is None
        hits = [w for w in out.warnings
                if getattr(w, "code", "") == METHOD_NOTE
                and w.args["note"]["code"] == "method.seismic_no_ky"]
        assert len(hits) == 1, out.warnings
        assert hits[0].args["note"]["args"] == {
            "unanswered": 1, "valid": 1, "k_max": DEFAULT_K_MAX}, hits[0]


# ======================================================================
def _with_first_changed(change):
    """The shared two-method run, its FIRST method's result replaced by a
    copy that ``change`` alters. The copy gets lists of its own, so the
    shared run is left as it was for the next test."""
    import copy

    from ogr_slip2d.analysis_runner import AnalysisOutcome
    project, out = _outcome("two")
    (first_id, first), (second_id, second) = out.results.items()
    altered = copy.copy(first)
    altered.evaluations = list(first.evaluations)
    altered.user_evaluations = list(first.user_evaluations)
    change(altered)
    shown = AnalysisOutcome({first_id: altered, second_id: second},
                            out.factor_report, list(out.warnings), out.project)
    return project, shown, first_id, second_id


def _compute(tmp_path, project, outcome):
    """``compute`` on the saved project, with the run replaced by
    ``outcome`` and put back afterwards."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from typer.testing import CliRunner

    import ogr_cli.__main__ as cli
    path = tmp_path / "plane.ogr"
    project.save(path)
    raw = cli.__dict__["run_analysis"]
    cli.run_analysis = lambda *a, **k: outcome
    try:
        # wide, or rich wraps the caption and cuts the method names
        return CliRunner().invoke(cli.app, ["compute", str(path)],
                                  env={"COLUMNS": "200"})
    finally:
        cli.run_analysis = raw


def _row(output, method_id):
    return next(line for line in output.splitlines()
                if method_id in line and "│" in line)


class TestTheCommandLine:
    """``compute`` with two methods, the FIRST one changed by hand.

    By hand because neither state is one this version's run leaves on the
    plane. A first method without a critical surface does happen -- Spencer
    and GLE find no Ky on a plane with kh, D143 -- but the test should not
    hang on a defect staying open. A critical surface without its
    displacement no longer happens: with a usable record the run now gives
    every one its displacement, and the dash is the guard if that breaks."""

    def test_a_first_method_without_a_critical_hides_nothing(self, tmp_path):
        def no_critical(result):
            result.evaluations, result.user_evaluations = [], []

        project, outcome, first_id, second_id = _with_first_changed(
            no_critical)
        assert outcome.results[first_id].critical is None
        result = _compute(tmp_path, project, outcome)
        assert result.exit_code == 0, (result.exit_code, result.output,
                                       result.exception)
        out = result.output
        # the old rule read the first method alone: "Critical Ky", and the
        # second method's Ky in place of its displacement
        assert "Newmark disp." in out and "Critical Ky" not in out, out
        assert "no valid surface" in _row(out, first_id), out
        moved = outcome.results[second_id].critical.details[
            "newmark_displacement"]
        assert "%.4f" % (moved * 100.0) in _row(out, second_id), out

    def test_a_critical_without_a_displacement_is_a_dash(self, tmp_path):
        import copy

        def bare(result):
            crit = result.critical
            stripped = copy.copy(crit)
            stripped.details = {k: v for k, v in crit.details.items()
                                if k != "newmark_displacement"}
            result.user_evaluations = [stripped if r is crit else r
                                       for r in result.user_evaluations]
            result.evaluations = [stripped if r is crit else r
                                  for r in result.evaluations]

        project, outcome, first_id, second_id = _with_first_changed(bare)
        crit = outcome.results[first_id].critical
        assert crit is not None
        assert "newmark_displacement" not in crit.details
        result = _compute(tmp_path, project, outcome)
        # indexing the displacement raised KeyError here: exit 1, no table
        # and no result saved
        assert result.exit_code == 0, (result.exit_code, result.output,
                                       result.exception)
        out = result.output
        assert "Newmark disp." in out, out
        assert "—" in _row(out, first_id), out
        moved = outcome.results[second_id].critical.details[
            "newmark_displacement"]
        assert "%.4f" % (moved * 100.0) in _row(out, second_id), out
        saved = sorted(p.name for p in tmp_path.glob("*.h5"))
        assert saved == sorted("plane_%s.h5" % m
                               for m in (first_id, second_id)), saved
