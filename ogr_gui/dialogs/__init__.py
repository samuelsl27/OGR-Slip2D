# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Modal dialog boxes used by the GUI."""
from .boundary_dialogs import (
    AssignMaterialDialog,
    ChangeSlopeAngleDialog,
    ConvertBoundaryDialog,
    EditCoordinatesDialog,
    ExpandShrinkDialog,
    GeometryCleanupDialog,
    RotateDialog,
    ScaleDialog,
    SelectionFilterDialog,
    SelectionFilterState,
    SimplifyBoundaryDialog,
)
from .display_options_dialog import DisplayOptionsDialog
from .drawdown_strength_dialog import DrawdownStrengthDialog
from .material_properties_dialog import MaterialPropertiesDialog
from .misc_dialogs import AboutDialog, ComputeProgressDialog
from .preferences_dialog import PreferencesDialog
from .project_settings_dialog import ProjectSettingsDialog
# v0.1.9 — old surface_options_dialog deprecated; full Slide-style
# version lives in grid_dialogs.
from .grid_dialogs import AddGridDialog, SurfaceOptionsDialog
from .optimize_settings_dialog import OptimizeSettingsDialog

__all__ = [
    "AboutDialog",
    "AssignMaterialDialog",
    "ChangeSlopeAngleDialog",
    "ComputeProgressDialog",
    "ConvertBoundaryDialog",
    "DisplayOptionsDialog",
    "DrawdownStrengthDialog",
    "EditCoordinatesDialog",
    "ExpandShrinkDialog",
    "GeometryCleanupDialog",
    "MaterialPropertiesDialog",
    "OptimizeSettingsDialog",
    "PreferencesDialog",
    "ProjectSettingsDialog",
    "RotateDialog",
    "ScaleDialog",
    "SelectionFilterDialog",
    "SelectionFilterState",
    "SimplifyBoundaryDialog",
    "SurfaceOptionsDialog",
]

# v0.1.3 — chart dialogs (matplotlib-based)
try:
    from .chart_dialogs import (
        CumulativeDialog,
        HistogramDialog,
        SFAlongSlopeDialog,
        ScatterDialog,
        SensitivityDialog,
    )
    __all__.extend([
        "CumulativeDialog",
        "HistogramDialog",
        "SFAlongSlopeDialog",
        "ScatterDialog",
        "SensitivityDialog",
    ])
except ImportError:
    # matplotlib not installed
    pass
