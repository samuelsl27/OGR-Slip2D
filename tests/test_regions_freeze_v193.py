# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The regions cache may be trusted during a run — and only during a run.

WHAT INVARIANT THIS PROTECTS. ``Project.resolve_regions`` validates its
cache by rebuilding a signature over every vertex of every external and
material boundary. That signature is not decoration: the canvas edits
boundaries IN PLACE — ``project.boundaries[bi] = new_b``, vertex drags —
without going through ``_notify``, so a cheaper revision counter would hand
back a stale material map after an ordinary edit. The signature is what
makes editing safe.

It is also expensive, and it was being paid about twice per slice: on the
Ej_2 reference grid, 41 % of the whole search went into rebuilding a
signature for a model that had not moved. ``regions_frozen()`` suspends the
revalidation for the duration of a block, and ``BaseSearch.run`` wraps every
search in one — legitimate because an analysis must not modify the user's
project (design coefficients are applied to a *copy*).

So there are two halves to protect, and the second matters more than the
first:

1. inside the block the signature is NOT rebuilt (the speedup is real);
2. outside it, an in-place edit still invalidates (the guarantee survives),
   and an exception inside the block does not leave a project pinned to a
   stale subdivision.

A cache that stops invalidating is worse than no cache, because the answer
stays plausible.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def _project():
    """Two materials over a slope, so region resolution actually decides."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 12), Vertex(30, 12),
        Vertex(20, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("freeze")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m1 = Material(name="Top", unit_weight=19, sat_unit_weight=20,
                  strength=MohrCoulomb(cohesion=10, friction_angle=28))
    m2 = Material(name="Bottom", unit_weight=20, sat_unit_weight=21,
                  strength=MohrCoulomb(cohesion=25, friction_angle=32))
    p.materials = [m1, m2]
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 6), Vertex(60, 6)], closed=False),
        btype=BoundaryType.MATERIAL))
    return p


def _move_material_boundary(project, y):
    """Edit a boundary IN PLACE, without notifying anybody.

    A list-slice assignment, not attribute assignment: ``Vertex`` is a
    frozen dataclass, so an edit replaces vertices rather than mutating
    them. This is the shape of the real thing —
    ``project.boundaries[bi] = new_b`` in ``ogr_gui/main_window.py`` — and
    it is precisely what ``_notify`` never hears about.
    """
    from ogr_core.geometry import BoundaryType, Vertex
    mb = [b for b in project.boundaries
          if b.btype == BoundaryType.MATERIAL][0]
    mb.polyline.vertices[:] = [Vertex(0, y), Vertex(60, y)]


class TestRegionsFreeze:
    def test_signature_not_rebuilt_inside_the_block(self):
        p = _project()
        p.resolve_regions()                 # warm, as regions_frozen() does
        calls = {"n": 0}
        real = type(p)._regions_cache_key

        def counted():
            calls["n"] += 1
            return real(p)

        p._regions_cache_key = counted
        with p.regions_frozen():
            # Entering resolves once on purpose, with the signature still
            # live, so what the block trusts is current. What must cost
            # nothing is everything AFTER that.
            calls["n"] = 0
            for _ in range(50):
                p.resolve_regions()
                p.bounding_box()
        assert calls["n"] == 0, (
            "the frozen block rebuilt the signature %d times" % calls["n"])

    def test_same_regions_object_inside_the_block(self):
        p = _project()
        with p.regions_frozen():
            first = p.resolve_regions()
            assert p.resolve_regions() is first

    def test_entering_populates_the_caches(self):
        """A frozen block must never serve a cache that started empty."""
        p = _project()
        p.invalidate_regions_cache()
        assert p._regions_cache is None
        with p.regions_frozen():
            assert p._regions_cache is not None
            assert p._bbox_cache is not None
            assert len(p.resolve_regions()) >= 2

    def test_nesting_is_reentrant(self):
        p = _project()
        with p.regions_frozen():
            assert p._regions_freeze_depth == 1
            with p.regions_frozen():
                assert p._regions_freeze_depth == 2
            assert p._regions_freeze_depth == 1
        assert p._regions_freeze_depth == 0

    def test_exception_releases_the_freeze(self):
        p = _project()
        try:
            with p.regions_frozen():
                raise RuntimeError("analysis blew up")
        except RuntimeError:
            pass
        assert p._regions_freeze_depth == 0

    def test_in_place_edit_still_invalidates_outside(self):
        """The guarantee the signature exists for, unchanged.

        This is the half that matters: the canvas moves a vertex without
        notifying anybody, and the next lookup has to see the new geometry.
        """
        p = _project()
        with p.regions_frozen():
            p.resolve_regions()
        before = [r.centroid() for r in p.resolve_regions()]
        _move_material_boundary(p, 9.0)
        after = [r.centroid() for r in p.resolve_regions()]
        assert before != after, (
            "an in-place vertex edit went unnoticed after a frozen block")

    def test_edit_during_a_freeze_is_seen_by_the_next_block(self):
        """Freezing is scoped: the NEXT block re-resolves on entry."""
        p = _project()
        with p.regions_frozen():
            snapshot = [r.centroid() for r in p.resolve_regions()]
            _move_material_boundary(p, 3.0)
            assert [r.centroid() for r in p.resolve_regions()] == snapshot
        with p.regions_frozen():
            assert [r.centroid() for r in p.resolve_regions()] != snapshot


class TestSearchRunsFrozen:
    def test_run_freezes_and_releases(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch

        p = _project()
        seen = {"depth": 0}
        gs = GridSearch(method=get_method("bishop_simplified")(),
                        grid_x=(20, 45), grid_y=(14, 30), grid_nx=3,
                        grid_ny=3, radius_increment=2, min_radius=0.0,
                        num_slices=12, min_area=0.5)
        real_run = GridSearch._run

        def spy(self, project):
            seen["depth"] = project._regions_freeze_depth
            return real_run(self, project)

        GridSearch._run = spy
        try:
            gs.run(p)
        finally:
            GridSearch._run = real_run
        assert seen["depth"] == 1, "the search body did not run frozen"
        assert p._regions_freeze_depth == 0, "the freeze leaked out of run()"

    def test_freezing_does_not_move_the_factor_of_safety(self):
        """The whole point: it is a speedup, not a modelling change.

        Compared against the same search with the freeze neutralised, so
        this is an identity between two code paths of the same version
        rather than a snapshot of what today's build prints.
        """
        import contextlib

        from ogr_core.project import Project
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch

        kw = dict(grid_x=(20, 45), grid_y=(14, 30), grid_nx=4, grid_ny=4,
                  radius_increment=3, min_radius=0.0, num_slices=15,
                  min_area=0.5)

        frozen = GridSearch(method=get_method("bishop_simplified")(),
                            **kw).run(_project())

        real = Project.regions_frozen

        @contextlib.contextmanager
        def no_freeze(self):
            yield self

        Project.regions_frozen = no_freeze
        try:
            thawed = GridSearch(method=get_method("bishop_simplified")(),
                                **kw).run(_project())
        finally:
            Project.regions_frozen = real

        assert frozen.valid_count == thawed.valid_count
        assert frozen.total_count == thawed.total_count
        # Bit-identical, not approximate: the freeze changes no arithmetic.
        assert frozen.critical.fos == thawed.critical.fos
