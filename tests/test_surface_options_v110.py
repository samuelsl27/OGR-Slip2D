# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.10 Surface Options refactor.

Verifies:
    - SearchSettings has all new per-method parameter blocks with
      sensible defaults
    - methods_for_surface_type() returns the correct restricted list
    - The new search-method enum values are present
    - The four new solver classes (AutoRefine, Block, Path, SA) are
      importable and accept their constructor parameters
"""
from __future__ import annotations


# ======================================================================
class TestSearchSettingsExtended:
    def test_default_grid_is_12_by_12(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        assert s.grid_nx == 12
        assert s.grid_ny == 12

    def test_all_per_method_blocks_have_defaults(self):
        from ogr_core.project.settings import SearchSettings
        s = SearchSettings()
        # Grid
        assert s.radius_increment > 0
        assert s.composite_surfaces is False
        # v0.1.12: Slide PDF shows this CHECKED by default
        assert s.create_tension_crack_reverse_curvature is True
        # Slope
        assert s.num_surfaces > 0
        assert s.initial_angle_lower_deg < s.initial_angle_upper_deg
        # Auto Refine (legacy fields preserved for back-compat)
        assert s.auto_refine_divisions >= 2
        assert s.auto_refine_iterations >= 1
        assert 0.0 < s.auto_refine_factor < 1.0
        # SA
        assert s.sa_initial_vertices >= 3
        assert s.sa_generation_steps > 0
        assert s.sa_tolerance > 0
        assert 0.0 < s.sa_temperature_factor < 1.0
        # Path (legacy fields)
        assert s.path_segment_length > 0
        assert s.path_min_angle_deg < s.path_max_angle_deg
        assert s.path_num_paths > 0
        # Block (legacy fields)
        assert s.block_num_groups > 0
        assert s.block_left_proj_angle_deg > 0
        assert s.block_right_proj_angle_deg > 0


# ======================================================================
class TestMethodsForSurfaceType:
    def test_circular_methods(self):
        from ogr_core.project.settings import (
            CIRCULAR_METHODS, SearchMethod,
        )
        assert SearchMethod.GRID_SEARCH in CIRCULAR_METHODS
        assert SearchMethod.SLOPE_SEARCH in CIRCULAR_METHODS
        assert SearchMethod.AUTO_REFINE in CIRCULAR_METHODS
        # Non-circular methods should NOT be in the circular set
        assert SearchMethod.BLOCK_SEARCH not in CIRCULAR_METHODS
        assert SearchMethod.PATH_SEARCH not in CIRCULAR_METHODS
        assert SearchMethod.SIMULATED_ANNEALING not in CIRCULAR_METHODS

    def test_non_circular_methods(self):
        from ogr_core.project.settings import (
            NON_CIRCULAR_METHODS, SearchMethod,
        )
        assert SearchMethod.BLOCK_SEARCH in NON_CIRCULAR_METHODS
        assert SearchMethod.PATH_SEARCH in NON_CIRCULAR_METHODS
        assert SearchMethod.SIMULATED_ANNEALING in NON_CIRCULAR_METHODS
        assert SearchMethod.AUTO_REFINE in NON_CIRCULAR_METHODS  # in both
        # Pure-circular methods NOT in this set
        assert SearchMethod.GRID_SEARCH not in NON_CIRCULAR_METHODS
        assert SearchMethod.SLOPE_SEARCH not in NON_CIRCULAR_METHODS

    def test_settings_methods_for_surface_type(self):
        from ogr_core.project.settings import (
            SearchMethod, SearchSettings, SurfaceType,
        )
        s = SearchSettings()
        s.surface_type = SurfaceType.CIRCULAR.value
        circ = s.methods_for_surface_type()
        assert SearchMethod.GRID_SEARCH in circ
        assert SearchMethod.BLOCK_SEARCH not in circ

        s.surface_type = SurfaceType.NON_CIRCULAR.value
        nonc = s.methods_for_surface_type()
        assert SearchMethod.SIMULATED_ANNEALING in nonc
        assert SearchMethod.GRID_SEARCH not in nonc


# ======================================================================
class TestNewSolverClasses:
    """The four new search classes must be importable and constructible."""

    def test_auto_refine_search_constructible(self):
        from ogr_slip2d import AutoRefineSearch, BishopSimplified
        s = AutoRefineSearch(
            method=BishopSimplified(),
            divisions=5,
            iterations=2,
            factor=0.5,
        )
        assert s.divisions == 5

    def test_block_search_constructible(self):
        from ogr_slip2d import BishopSimplified, BlockSearch
        s = BlockSearch(
            method=BishopSimplified(),
            num_groups=3,
            left_proj_angle_deg=120.0,
            right_proj_angle_deg=60.0,
        )
        assert s.num_groups == 3

    def test_path_search_constructible(self):
        from ogr_slip2d import BishopSimplified, PathSearch
        s = PathSearch(
            method=BishopSimplified(),
            segment_length=4.0,
            min_angle_deg=-30.0,
            max_angle_deg=30.0,
            num_paths=100,
        )
        assert s.segment_length == 4.0

    def test_simulated_annealing_constructible(self):
        from ogr_slip2d import BishopSimplified, SimulatedAnnealingSearch
        s = SimulatedAnnealingSearch(
            method=BishopSimplified(),
            initial_vertices=8,
            generation_steps=100,
            tolerance=1e-3,
            temperature_factor=0.95,
        )
        assert s.initial_vertices == 8


# ======================================================================
class TestSearchSettingsRoundtripV110:
    """Verify all the new fields survive the asdict roundtrip used by the
    project save/load cycle."""

    def test_full_roundtrip(self):
        from dataclasses import asdict
        from ogr_core.project.settings import SearchSettings

        s = SearchSettings()
        # Tweak one field per panel
        s.radius_increment = 0.75
        s.num_surfaces = 5000
        s.auto_refine_divisions = 25
        s.sa_temperature_factor = 0.92
        s.path_segment_length = 7.5
        s.block_num_groups = 5
        s.create_tension_crack_reverse_curvature = True
        s.sa_convex_only = True

        d = asdict(s)
        s2 = SearchSettings(**d)
        assert s2.radius_increment == 0.75
        assert s2.num_surfaces == 5000
        assert s2.auto_refine_divisions == 25
        assert s2.sa_temperature_factor == 0.92
        assert s2.path_segment_length == 7.5
        assert s2.block_num_groups == 5
        assert s2.create_tension_crack_reverse_curvature is True
        assert s2.sa_convex_only is True
