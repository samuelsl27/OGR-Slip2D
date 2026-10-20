# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The codes of the DXF import's messages (v0.1.334, D314).

What the sanitiser finds wrong with an imported drawing, and why a preview
fails, each as a code with its values beside the English sentence; the
mechanism is ``ogr_core.messages``, the same one the engine's per-surface
reasons use (``ogr_slip2d.messages``). A problem's code is ``dxf.`` plus its
``kind``, which the problems panel already grouped and explained by.

The sentences are the ones the importer wrote before this version, byte for
byte: ``tests/test_dxf_messages_v1334.py`` compares each template, filled
with a sample, with the 0.1.333 expression.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.messages import CORE_MESSAGES, MessageSpec, english

EMPTY = "dxf.empty"
EXTERNAL = "dxf.external"
EXTERNAL_GAP = "dxf.external_gap"
EXTERNAL_MISSING = "dxf.external_missing"
EXTERNAL_MULTIPLE = "dxf.external_multiple"
DANGLING_END = "dxf.dangling_end"
REGIONS = "dxf.regions"
AREA_MISMATCH = "dxf.area_mismatch"
UNREADABLE = "dxf.unreadable"
EZDXF_MISSING = "dxf.ezdxf_missing"
NO_LAYER_ASSIGNED = "dxf.no_layer_assigned"

MESSAGES: dict = dict(CORE_MESSAGES)
for _spec in (
    MessageSpec(EMPTY, "No geometry was assigned to any layer."),
    MessageSpec(EXTERNAL,
                "The external boundary has fewer than three vertices."),
    MessageSpec(EXTERNAL_GAP,
                "The external boundary was open by {gap:.3f} units and has "
                "been closed with a straight segment; check the result."),
    MessageSpec(EXTERNAL_MISSING,
                "No layer was assigned to the external boundary; the model "
                "cannot define regions without one."),
    MessageSpec(EXTERNAL_MULTIPLE,
                "{count} external boundaries were found; the largest will be "
                "used and the rest ignored."),
    MessageSpec(DANGLING_END,
                "A material boundary end does not reach any other boundary, "
                "so the region will not close."),
    MessageSpec(REGIONS, "Regions could not be built: {error}"),
    MessageSpec(AREA_MISMATCH,
                "The region areas ({regions:.2f}) do not add up to the "
                "external boundary ({external:.2f}): at least one region did "
                "not close."),
    MessageSpec(UNREADABLE, "Could not read the DXF file: {error}"),
    MessageSpec(EZDXF_MISSING,
                "The 'ezdxf' package is required to import DXF files."),
    MessageSpec(NO_LAYER_ASSIGNED,
                "No layer has been assigned a geometry type. Use the table "
                "to say what each layer represents."),
):
    MESSAGES[_spec.code] = _spec


def text(code: str, **args) -> str:
    """The English sentence of ``code`` with ``args``."""
    return english(MESSAGES, code, args)


def problem_code(kind: str) -> str:
    """The code of a sanitiser problem of ``kind``."""
    return "dxf." + kind


class DxfReadError(RuntimeError):
    """A DXF that cannot be read, with the code of its message and its
    values. A ``RuntimeError`` as before, so every caller that catches that
    keeps doing so."""

    def __init__(self, code: str, **values) -> None:
        super().__init__(text(code, **values))
        self.code = code
        self.values = dict(values)
