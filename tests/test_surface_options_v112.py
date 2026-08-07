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
class TestLegacyFieldsPreserved:
    """Backward compatibility: the v0.1.10/v0.1.11 fields used by the
    search algorithms in ogr_slip2d/search.py must still exist with
    sensible defaults."""

    def test_legacy_fields_exist(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # These are read by the solver classes
        assert hasattr(s, "auto_refine_divisions")
        assert hasattr(s, "auto_refine_iterations")
        assert hasattr(s, "auto_refine_factor")
        assert hasattr(s, "sa_temperature_factor")
        assert hasattr(s, "path_num_paths")
        assert hasattr(s, "path_segment_length")
        assert hasattr(s, "path_min_angle_deg")
        assert hasattr(s, "path_max_angle_deg")
        assert hasattr(s, "block_num_groups")
        assert hasattr(s, "block_left_proj_angle_deg")
        assert hasattr(s, "block_right_proj_angle_deg")
        assert hasattr(s, "initial_angle_lower_deg")
        assert hasattr(s, "initial_angle_upper_deg")
