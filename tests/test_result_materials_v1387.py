# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A result keeps the materials it was solved with, not the project's own.

WHAT INVARIANT THIS PROTECTS.

D381, found by the review of v0.1.386. The slicer hands each slice the
``Material`` object of the project it analyses — the user's own one when no
design standard or Generalized Anisotropic link made a copy — and a result
solved in this process kept it, where a result back from the pool holds an
unpickled copy. An edit in place after the run (an agent's ``material_set``
through the window, a script) changed what the stored result showed:
Interpret's slice table and the interslice forces it recomputes, next to the
old factor of safety. Undo, which puts deep copies back, then cleared the
stale mark while the result still read the edited object. Reproduced before
the fix: a cohesion of 8 edited to 2 after the run changed the rows from
('clay', 8.0) to ('edited after the run', 2.0), and they stayed so after an
undo-like restore.

1. **No slice of a result points at an object of ``project.materials``,**
   at any door: a search's run (its evaluations, the user's surfaces, the
   optimised surface), ``run_analysis``, the Optimize Surfaces of the menu
   (``run_configured_optimization``) and ``evaluate_surfaces``.
2. **What the result shows does not move after an edit in place,** nor
   after an undo-like restore: the slice rows and the interslice state,
   to the bit.
3. **The copies are what was solved:** equal to the material at the run,
   with its ``id``, and one copy per material shared by every slice.
4. **A slice whose material is not one of the project's own is left as
   it is** (a pooled result, the drawdown's stage-2 materials).
5. **No number moves:** every evaluation is the same with the copies and
   without them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy

MID = "bishop_simplified"


def _model():
    """A clay slope under a water table with a friction tieback, solved in
    this process on a small grid."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_core.support import GroutedTiebackFriction, SupportInstance
    p = Project(name="d381")
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
                             Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay", strength=MohrCoulomb(cohesion=8.0,
                                                   friction_angle=24.0),
                 unit_weight=19.0, sat_unit_weight=20.5,
                 pore_pressure=PorePressureType.WATER_TABLE)
    p.add_material(m)
    wt = Boundary(polyline=Polyline(vertices=[Vertex(0, 14), Vertex(50, 9)]),
                  btype=BoundaryType.WATER_TABLE)
    p.add_boundary(wt)
    m.water_surface_id = wt.id
    st = GroutedTiebackFriction(adhesion=10.0, friction_angle_bond=30.0,
                                bond_length_percent=60.0, grout_diameter=0.15,
                                out_of_plane_spacing=1.5,
                                tensile_capacity=1.0e3, plate_capacity=1.0e3)
    p.support_types.append(st)
    p.supports.append(SupportInstance(type_id=st.TYPE_ID,
                                      head=Vertex(30.0, 20.0),
                                      tail=Vertex(14.0, 14.0)))
    s = p.settings.search
    s.search_method, s.surface_type = "grid", "circular"
    s.grid_x_min, s.grid_x_max = 20.0, 40.0
    s.grid_y_min, s.grid_y_max = 28.0, 45.0
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 3
    p.settings.methods.num_slices = 20
    p.settings.advanced.parallel_search = False
    return p


def _circle():
    from ogr_core.geometry.slip_circle import SlipCircle
    return SlipCircle(centre_x=30.0, centre_y=35.0, radius=21.0)


def _live_slices(project, results):
    """How many slices of ``results`` point at an object of the project."""
    live = {id(m) for m in project.materials}
    return sum(1 for r in results if r is not None and r.slices
               for s in r.slices if id(s.material) in live)


def _shown(result):
    """What Interpret shows of a result: its slice rows and the interslice
    forces it recomputes, every float as hex."""
    from ogr_slip2d.interpretation import slice_rows
    from ogr_slip2d.postprocess import compute_interslice_state

    def h(v):
        return v.hex() if isinstance(v, float) else v

    rows = [tuple((k, h(v)) for k, v in sorted(r.items()))
            for r in slice_rows(result)]
    st = compute_interslice_state(result)
    return rows, [h(float(e)) for e in st.E], [h(float(x)) for x in st.X]


def _edit_in_place(project):
    m = project.materials[0]
    m.name = "edited after the run"
    m.strength.params["cohesion"] = 2.0
    m.unit_weight = 25.0


_RUN = {}


def _run():
    """One search run of the model, shared by the readers of this file;
    each test that edits builds its own."""
    if "r" not in _RUN:
        from ogr_slip2d.analysis_runner import run_analysis
        p = _model()
        p.user_surfaces = [_circle()]
        _RUN["r"] = (p, run_analysis(p, [MID]).results[MID])
    return _RUN["r"]


# ======================================================================
class TestNoSliceKeepsTheProjectsMaterial:
    """Invariant 1."""

    def test_a_search_run(self):
        p, res = _run()
        assert res.evaluations and res.user_evaluations
        assert _live_slices(p, res.all_evaluations()) == 0

    def test_the_optimised_surface_of_a_search(self):
        from ogr_slip2d.analysis_runner import run_analysis
        p = _model()
        p.settings.search.optimize_enabled = True
        p.settings.search.optimize_max_iterations = 40
        res = run_analysis(p, [MID]).results[MID]
        extra = list(res.steered) + ([res.optimized] if res.optimized else [])
        assert _live_slices(p, res.all_evaluations() + extra) == 0

    def test_optimize_surfaces_from_the_menu(self):
        """The walk moves polylines: the circle, resolved onto the ground by
        an evaluation, sampled as the search does."""
        from ogr_slip2d.analysis_runner import (evaluate_surfaces,
                                                run_configured_optimization)
        from ogr_slip2d.search import BaseSearch
        p = _model()
        resolved = evaluate_surfaces(p, _circle(), [MID]).results[MID].surface
        start = BaseSearch._as_optimisable(resolved, 20)
        assert start is not None
        _best, res, _rep, _report, _w = run_configured_optimization(
            p, MID, start, max_iterations=40)
        assert res is not None and res.slices
        assert _live_slices(p, [res]) == 0

    def test_evaluate_surfaces(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        p = _model()
        res = evaluate_surfaces(p, _circle(), [MID]).results[MID]
        assert res is not None and res.slices
        assert _live_slices(p, [res]) == 0


# ======================================================================
class TestWhatTheResultShowsDoesNotMove:
    """Invariant 2. Fails on v0.1.386: the rows went from ('clay', 8.0) to
    ('edited after the run', 2.0)."""

    def _solved(self):
        from ogr_slip2d.analysis_runner import run_analysis
        p = _model()
        crit = run_analysis(p, [MID]).results[MID].critical
        return p, crit, _shown(crit)

    def test_after_an_edit_in_place(self):
        p, crit, before = self._solved()
        _edit_in_place(p)
        assert _shown(crit) == before

    def test_after_an_undo_like_restore(self):
        """Undo writes deep copies back to ``project.materials``; the model
        then matches the result's fingerprint again, so nothing marks the
        result stale, and it has to show what was solved."""
        p, crit, before = self._solved()
        saved = copy.deepcopy(p.materials)
        _edit_in_place(p)
        p.materials = saved
        assert _shown(crit) == before


# ======================================================================
class TestTheCopiesAreWhatWasSolved:
    """Invariant 3."""

    def test_equal_to_the_material_at_the_run_with_its_id(self):
        p, res = _run()
        live = p.materials[0]
        mats = {id(s.material): s.material for r in res.all_evaluations()
                if r.slices for s in r.slices}
        assert len(mats) == 1, "one copy per material, shared by every slice"
        (copy_,) = mats.values()
        assert copy_ is not live
        assert copy_.id == live.id
        assert copy_.to_dict() == live.to_dict()


# ======================================================================
class TestForeignMaterialsAreLeftAlone:
    """Invariant 4, on the helper itself."""

    def test_a_slice_with_another_material(self):
        """A run of its own: it rewrites the slices it looks at."""
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.search import detach_materials
        p = _model()
        crit = evaluate_surfaces(p, _circle(), [MID]).results[MID]
        foreign = copy.deepcopy(p.materials[0])
        for s in crit.slices:
            s.material = foreign
        detach_materials(p, [crit])
        assert all(s.material is foreign for s in crit.slices)

    def test_without_materials_or_slices(self):
        from ogr_core.project import Project
        from ogr_slip2d.search import detach_materials
        detach_materials(Project("empty"), [None, object()])


# ======================================================================
class TestNoNumberMoves:
    """Invariant 5: the run with the copies against the same run with the
    helper replaced by a no-op (and given back)."""

    def _fingerprint(self, res):
        out = []
        for e in res.all_evaluations():
            out.append((repr(e.fos), e.converged, e.iterations, e.is_valid,
                        e.admissible,
                        tuple(repr(s.weight) for s in e.slices)
                        if e.slices else ()))
        return out, repr(res.critical.fos)

    def test_with_and_without_the_copies(self):
        import ogr_slip2d.search as S
        from ogr_slip2d.analysis_runner import run_analysis
        real = S.detach_materials
        S.detach_materials = lambda project, results: None
        try:
            p = _model()
            without = run_analysis(p, [MID]).results[MID]
        finally:
            S.detach_materials = real
        assert _live_slices(p, without.all_evaluations()) > 0, \
            "the no-op did not take: the comparison would prove nothing"
        q = _model()
        with_copies = run_analysis(q, [MID]).results[MID]
        assert self._fingerprint(with_copies) == self._fingerprint(without)
