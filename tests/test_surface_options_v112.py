# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.12 Surface Options refactor + UX fixes.

Verifies:
    - SearchSettings has all PDF-aligned fields with correct defaults
    - uses_grid() returns True only for GRID_SEARCH
    - Roundtrip preserves all new fields via dataclass.asdict
    - Sliding/PDF parameter mappings are coherent
"""
from __future__ import annotations


# ======================================================================
class TestSlidePDFAlignment:
    """The new SearchSettings fields must match the parameters shown
    in the Surface Options dialog screenshots from Surface_Options.pdf."""

    def test_grid_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF shows Radius Increment=10, Composite=unchecked,
        # Create tension crack=CHECKED
        assert s.radius_increment == 10
        assert s.composite_surfaces is False
        assert s.create_tension_crack_reverse_curvature is True

    def test_slope_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF shows Number of Surfaces=5000, both angle checkboxes
        # unchecked, both default values=-45
        assert s.num_surfaces == 5000
        assert s.initial_angle_at_toe_upper_enabled is False
        assert s.initial_angle_at_toe_upper_deg == -45.0
        assert s.initial_angle_at_toe_lower_enabled is False
        assert s.initial_angle_at_toe_lower_deg == -45.0

    def test_auto_refine_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF: Divisions along slope=10, Circles per division=10,
        # Iterations=10, Divisions to use in next iteration=50%
        assert s.auto_refine_divisions_along_slope == 10
        assert s.auto_refine_circles_per_division == 10
        assert s.auto_refine_num_iterations == 10
        assert s.auto_refine_divisions_to_use_pct == 50.0
        # Non-circular extra: Number of vertices along surface=12
        assert s.auto_refine_num_vertices_along_surface == 12

    def test_sa_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF: Initial vertices=8, Generation steps=1000,
        # FoS compared before stopping=5, Tolerance=0.0001, Coef=8
        assert s.sa_initial_vertices == 8
        assert s.sa_generation_steps == 1000
        assert s.sa_num_fos_compared_before_stopping == 5
        assert s.sa_tolerance == 1e-4
        assert s.sa_temperature_coefficient == 8.0

    def test_path_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF: Number of Surfaces=5000, both angle checkboxes off,
        # default angles=45, Segment length manual=False
        assert s.path_num_surfaces == 5000
        assert s.path_initial_angle_at_toe_upper_enabled is False
        assert s.path_initial_angle_at_toe_upper_deg == 45.0
        assert s.path_initial_angle_at_toe_lower_enabled is False
        assert s.path_initial_angle_at_toe_lower_deg == 45.0
        assert s.path_segment_length_manual is False

    def test_block_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF: Number of Surfaces=5000, Multiple Groups unchecked,
        # Left=135-135, Right=45-45
        assert s.block_num_surfaces == 5000
        assert s.block_multiple_groups is False
        assert s.block_left_start_angle_deg == 135.0
        assert s.block_left_end_angle_deg == 135.0
        assert s.block_right_start_angle_deg == 45.0
        assert s.block_right_end_angle_deg == 45.0


# ======================================================================
class TestUsesGrid:
    def test_grid_search_uses_grid(self):
        from ogr_core.project.settings import (
            SearchMethod, SearchSettings,
        )
        s = SearchSettings()
        s.search_method = SearchMethod.GRID_SEARCH.value
        assert s.uses_grid() is True

    def test_other_methods_do_not_use_grid(self):
        from ogr_core.project.settings import (
            SearchMethod, SearchSettings,
        )
        s = SearchSettings()
        for m in (
            SearchMethod.SLOPE_SEARCH,
            SearchMethod.AUTO_REFINE,
            SearchMethod.BLOCK_SEARCH,
            SearchMethod.PATH_SEARCH,
            SearchMethod.SIMULATED_ANNEALING,
        ):
            s.search_method = m.value
            assert s.uses_grid() is False, f"{m} should not use grid"


# ======================================================================
class TestOptimizeSurfaces:
    def test_optimize_defaults_match_pdf(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # PDF Optimize Surfaces Settings dialog shows:
        # Tolerance=1e-9, Max iter=4000, Step reduction=0.5,
        # Max concave angle=5, Snap shallow=checked, distance=0.01
        assert s.optimize_enabled is False  # disabled by default
        assert s.optimize_tolerance == 1e-9
        assert s.optimize_max_iterations == 4000
        assert s.optimize_step_reduction_factor == 0.5
        assert s.optimize_max_concave_angle_deg == 5.0
        assert s.optimize_snap_shallow_to_slope is True
        assert s.optimize_snap_distance == 0.01


# ======================================================================
class TestRoundtripV112:
    def test_full_asdict_roundtrip_preserves_new_fields(self):
        from dataclasses import asdict
        from ogr_core.project.settings import SearchSettings

        s = SearchSettings()
        # Tweak some new fields
        s.radius_increment = 25
        s.sa_temperature_coefficient = 12.5
        s.sa_num_fos_compared_before_stopping = 8
        s.path_segment_length_value = 3.14
        s.path_segment_length_manual = True
        s.block_left_start_angle_deg = 150.0
        s.block_right_end_angle_deg = 30.0
        s.optimize_enabled = True
        s.optimize_max_iterations = 2000

        d = asdict(s)
        s2 = SearchSettings(**d)
        assert s2.radius_increment == 25
        assert s2.sa_temperature_coefficient == 12.5
        assert s2.sa_num_fos_compared_before_stopping == 8
        assert s2.path_segment_length_value == 3.14
        assert s2.path_segment_length_manual is True
        assert s2.block_left_start_angle_deg == 150.0
        assert s2.block_right_end_angle_deg == 30.0
        assert s2.optimize_enabled is True
        assert s2.optimize_max_iterations == 2000


# ======================================================================
class TestShadowFieldsAreGone:
    """v0.1.103 — this class used to be ``TestLegacyFieldsPreserved`` and
    it REQUIRED every one of these names to exist, on the grounds that
    "these are read by the solver classes". That was true, and it was the
    defect: they were read by the solver while the interface showed and
    saved a different field of the same meaning, so a project built by a
    script declared 5000 surfaces and searched 500.

    The invariant now runs the other way. If one of these names comes
    back, so does the fault."""

    def test_shadow_names_are_not_fields(self):
        from dataclasses import fields
        from ogr_core.project.settings import SearchSettings
        names = {f.name for f in fields(SearchSettings)}
        for gone in ("auto_refine_divisions", "auto_refine_iterations",
                     "auto_refine_factor", "sa_temperature_factor",
                     "path_num_paths", "path_segment_length",
                     "path_min_angle_deg", "path_max_angle_deg",
                     "path_upper_angle_enabled",
                     "block_left_proj_angle_deg",
                     "block_right_proj_angle_deg",
                     "initial_angle_lower_deg", "initial_angle_upper_deg"):
            assert gone not in names, gone

    def test_every_retired_name_is_registered_with_its_survivor(self):
        """The registry is what the migration and the refusal both read,
        so a name retired without an entry would go back to being
        silent."""
        from dataclasses import fields
        from ogr_core.project.settings import (
            _SHADOW_FIELDS, SearchSettings,
        )
        names = {f.name for f in fields(SearchSettings)}
        for gone, (_default, survivor) in _SHADOW_FIELDS.items():
            assert gone not in names, gone
            if survivor is not None:
                assert survivor in names, survivor
