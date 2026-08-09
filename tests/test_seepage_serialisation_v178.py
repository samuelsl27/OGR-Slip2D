# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The finite-element seepage field must survive a save.

**The invariant**: for a project whose materials take u from the FE
field, the factor of safety computed after save+load equals the one
computed before, exactly. Not "approximately", and above all not the
dry-slope value.

Why this file exists. Until v0.1.78 ``Project.to_dict`` wrote ``fem_mesh``
and not ``seepage_result``. ``pore_pressure.py`` answers 0.0 when the
field is missing, so reopening a solved FEM project and pressing Compute
reported **a dry slope, in silence** — and a dry slope is stronger, so
the number came out reassuringly high. On the fixture below the two
differ by 5 %: 0.8398 wet against 0.8831 dry. v0.1.77 caught the case and
refused to compute; this is the other half.

The tests are built so they cannot pass by accident:

* the round-trip test compares against an **analytical identity**,
  u = gamma_w * (H - y), not against a stored copy of the output;
* the end-to-end test asserts the reloaded factor of safety equals the
  original AND differs from the dry one, so a regression that silently
  drops the field again fails on the second assertion even if the first
  were somehow satisfied;
* the size test exists because "store only what cannot be derived" is an
  intention until something measures it. Storing every field verbatim
  would be ~7x larger, and the .ogr is a text format users open.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_coupling_v128 import _seepage_project  # noqa: E402

from ogr_core.project import Project  # noqa: E402
from ogr_slip2d import BishopSimplified  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

# The reference-validated circle of the Ej_1 model the fixture is built
# on, so the factors of safety below are comparable with the numbers in
# test_slide_validation_ej1.py.
_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)

# Solving seepage and meshing are the expensive part of the suite, so the
# project is built once and shared. Every test treats it as read-only
# except through a saved copy (rule 5: no state leaks between tests).
_CACHE: dict = {}


def _project():
    if "p" not in _CACHE:
        _CACHE["p"] = _seepage_project(elements=700)
    return _CACHE["p"]


def _fos(project) -> float:
    ev = GridSearch(method=BishopSimplified(), num_slices=25, min_area=0.0)
    res = ev.evaluate_circle(project, _CIRCLE)
    assert res is not None
    return res.fos


def _saved_copy(project):
    """Save to a temporary .ogr, load it back, return (project, bytes)."""
    path = Path(tempfile.gettempdir()) / "ogr_seepage_roundtrip.ogr"
    try:
        project.save(path)
        size = os.path.getsize(path)
        return Project.load(path), size
    finally:
        if path.exists():
            os.remove(path)


class TestTheFieldSurvivesTheRoundTrip:
    def test_a_field_is_written_at_all(self):
        d = _project().to_dict()
        assert d.get("seepage_result"), "no seepage_result key in the .ogr"
        assert d["seepage_result"]["total_head"], "no heads written"

    def test_pore_pressure_is_the_analytical_identity(self):
        """u = gamma_w * (H - y) at every node.

        This is the reason the derived fields are not stored: they are
        not independent data. Asserting the identity — rather than
        comparing with a saved copy of the original list — is what makes
        this a validation instead of a snapshot.
        """
        q, _ = _saved_copy(_project())
        r = q.seepage_result
        mesh = q.fem_mesh
        assert r is not None and r.pore_pressure
        for i, u in enumerate(r.pore_pressure):
            expected = r.gamma_w * (r.total_head[i] - mesh.nodes[i].y)
            assert abs(u - expected) < 1e-9, (i, u, expected)

    def test_heads_and_derived_fields_match_the_original(self):
        """Within the declared rounding (9 significant figures on heads
        of order 40 m, i.e. ~1e-7 m absolute)."""
        p = _project()
        q, _ = _saved_copy(p)
        r0, r1 = p.seepage_result, q.seepage_result
        assert len(r1.total_head) == len(r0.total_head)
        assert max(abs(a - b) for a, b in
                   zip(r0.total_head, r1.total_head)) < 1e-6
        assert max(abs(a - b) for a, b in
                   zip(r0.pore_pressure, r1.pore_pressure)) < 1e-5
        # Velocities are rebuilt from the STORED kr, not from a kr
        # recomputed off the final heads, so they come back essentially
        # to machine precision. If someone "simplifies" that away, the
        # Picard lag turns this into a visible difference.
        assert len(r1.velocity) == len(r0.velocity)
        assert max(max(abs(a[0] - b[0]), abs(a[1] - b[1]))
                   for a, b in zip(r0.velocity, r1.velocity)) < 1e-9

    def test_flags_and_notes_survive(self):
        p = _project()
        q, _ = _saved_copy(p)
        assert q.seepage_result.converged is p.seepage_result.converged
        assert q.seepage_result.iterations == p.seepage_result.iterations
        assert q.seepage_result.seepage_nodes == \
            p.seepage_result.seepage_nodes

    def test_the_stored_form_is_json(self):
        """The .ogr is JSON; a note holding an object json cannot write
        must not make save() raise on a project the user just spent
        minutes computing."""
        p = _project()
        p.seepage_result.notes["not_serialisable"] = object()
        try:
            json.dumps(p.seepage_result.to_dict())
        finally:
            p.seepage_result.notes.pop("not_serialisable")


class TestTheOriginalBugIsGone:
    def test_the_factor_of_safety_survives_a_save(self):
        """The bug itself, end to end.

        ``fos_dry`` is the number the program used to report after
        reopening: not an error, not a warning, just a different and
        higher factor of safety.
        """
        p = _project()
        fos_before = _fos(p)
        q, _ = _saved_copy(p)
        fos_after = _fos(q)

        q.seepage_result = None
        fos_dry = _fos(q)

        assert abs(fos_after - fos_before) < 1e-9, (fos_before, fos_after)
        assert abs(fos_dry - fos_before) > 0.01, (
            "the fixture no longer distinguishes wet from dry, so this "
            f"test proves nothing: wet={fos_before:.4f} dry={fos_dry:.4f}")

    def test_the_guard_no_longer_fires_on_a_reopened_project(self):
        """v0.1.77's refusal was correct and is now unnecessary here."""
        from ogr_slip2d.analysis_runner import check_analysis_settings
        q, _ = _saved_copy(_project())
        assert check_analysis_settings(q) == []

    def test_the_guard_still_fires_without_a_field(self):
        """The other half: a project that was never solved must still be
        refused, or v0.1.77's fix has been undone."""
        from ogr_slip2d.analysis_runner import check_analysis_settings
        q, _ = _saved_copy(_project())
        q.seepage_result = None
        problems = check_analysis_settings(q)
        assert problems and "seepage" in problems[0].lower()

    def test_a_field_that_does_not_match_the_mesh_is_refused(self):
        """A field whose node count differs from the mesh is not a field
        for that mesh. Interpolating it would be arithmetic on unrelated
        numbers, so it is dropped and the guard reports it."""
        from ogr_fem2d.solvers import (SeepageResult, restore_derived,
                                       hydraulic_props_of)
        p = _project()
        d = p.seepage_result.to_dict()
        d["total_head"] = d["total_head"][:-3]      # mesh changed since
        r = restore_derived(SeepageResult.from_dict(d), p.fem_mesh,
                            hydraulic_props_of(p))
        assert not r.pore_pressure
        assert "restore_error" in r.notes


class TestOnlyTheIrreducibleDataIsStored:
    def test_the_derived_fields_are_not_in_the_file(self):
        """Storing them would store the same numbers up to four times."""
        d = _project().to_dict()["seepage_result"]
        for key in ("pressure_head", "pore_pressure", "velocity",
                    "gradient", "reactions"):
            assert key not in d, f"{key} is derivable and must not be stored"

    def test_the_field_costs_less_than_the_mesh_it_belongs_to(self):
        """A budget, in the spirit of the i18n one: the exact number will
        drift with the mesh, but the field growing past the mesh means
        something stopped being derived."""
        d = _project().to_dict()
        mesh_kb = len(json.dumps(d["fem_mesh"], indent=2)) / 1024
        field_kb = len(json.dumps(d["seepage_result"], indent=2)) / 1024
        assert field_kb < mesh_kb, (field_kb, mesh_kb)

    def test_it_is_much_smaller_than_storing_everything(self):
        """The measurement behind the decision, kept executable.

        On this fixture the compact form is ~13.5 KB against ~99 KB for
        every field written verbatim.
        """
        r = _project().seepage_result
        compact = len(json.dumps(r.to_dict(), indent=2))
        verbatim = len(json.dumps({
            "total_head": r.total_head, "pressure_head": r.pressure_head,
            "pore_pressure": r.pore_pressure, "velocity": r.velocity,
            "gradient": r.gradient, "reactions": r.reactions,
        }, indent=2))
        assert verbatim > 4 * compact, (compact, verbatim)


class TestTransientStagesTravelToo:
    def test_every_stage_round_trips(self):
        """``transient_results`` had the same hole as ``seepage_result``:
        one field per stage, none of them saved."""
        p = _project()
        # Two stages sharing the steady field is enough to prove the list
        # is written and restored; solving a real transient here would
        # cost more than it demonstrates.
        p.transient_results = [p.seepage_result, p.seepage_result]
        try:
            q, _ = _saved_copy(p)
        finally:
            p.transient_results = []
        assert len(q.transient_results) == 2
        for r in q.transient_results:
            assert r.pore_pressure, "a stage came back with no field"
            assert max(abs(a - b) for a, b in
                       zip(r.pore_pressure,
                           p.seepage_result.pore_pressure)) < 1e-5

    def test_no_stages_means_no_key_bloat(self):
        p = _project()
        assert p.to_dict()["transient_results"] == []
