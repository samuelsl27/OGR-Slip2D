# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""DXF import: reader, layer catalogue and geometry sanitiser."""
from .reader import (  # noqa: F401
    INSUNITS_TO_METRES,
    LAYER_DEFAULTS,
    UNIT_FACTORS,
    DxfCatalogue,
    DxfEntityKind,
    DxfLayerInfo,
    DxfPolyline,
    guess_kind,
    read_dxf,
)

from .sanitiser import (  # noqa: F401
    DEFAULT_SIMPLIFY_PCT,
    DEFAULT_WELD_PCT,
    WELD_PCT_RANGE,
    GeometrySanitiser,
    SanitiseReport,
    douglas_peucker,
)

from .importer import (  # noqa: F401
    KIND_TO_BOUNDARY,
    ImportOptions,
    ImportPreview,
    apply_to_project,
    import_dxf,
    preview,
)

from .exporter import (  # noqa: F401
    BOUNDARY_TO_LAYER,
    ExportOptions,
    ExportReport,
    export_dxf,
)

__all__ = [
    "ExportOptions", "ExportReport", "export_dxf", "BOUNDARY_TO_LAYER",
    "ImportOptions", "ImportPreview", "preview", "apply_to_project",
    "import_dxf", "KIND_TO_BOUNDARY",
    "GeometrySanitiser", "SanitiseReport", "douglas_peucker",
    "DEFAULT_WELD_PCT", "DEFAULT_SIMPLIFY_PCT", "WELD_PCT_RANGE",
    "DxfEntityKind", "DxfPolyline", "DxfLayerInfo", "DxfCatalogue",
    "read_dxf", "guess_kind", "LAYER_DEFAULTS", "UNIT_FACTORS",
    "INSUNITS_TO_METRES",
]
