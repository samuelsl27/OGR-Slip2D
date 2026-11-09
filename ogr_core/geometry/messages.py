# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The messages of the geometry editions, with stable codes (v0.1.434, D412).

Change Slope Angle (``slope_angle.py``), Simplify (``cleanup.py``), Expand /
Shrink (``expand_shrink.py``) and the offset of the External
(``transforms.py``) refused with English sentences written into the
exception, and Change Slope Angle returned English notes. The window showed
them as they were, ``str(exc)`` with no ``tr()``: with the interface in
Spanish, «The toe must be lower than the crest.» in the status bar.

Each is a code here, with its English template and the very format specs the
f-string used. The exception keeps its type (``ValueError``,
``ExpandShrinkError``: callers and tests catch by type) and takes the
:class:`~ogr_core.messages.Coded` as its argument, so ``str(exc)`` -- what
the agent's operations send as ``InvalidArgument(str(exc))`` -- is the
sentence the core always wrote, byte for byte, and the window reads the code
from ``exc.args[0]`` (``ogr_gui.core_messages.error_text``).

The two notes count with «(s)» on purpose: a singular variant would change
the English for one support or one load.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

G = "geometry."
VERTEX_REF = G + "vertex_ref"
VERTEX_OUT_OF_RANGE = G + "vertex_out_of_range"
NOT_A_VERTEX = G + "not_a_vertex"
TOE_IS_CREST = G + "toe_is_crest"
TOE_NOT_LOWER = G + "toe_not_lower"
FACE_NOT_ON_GROUND = G + "face_not_on_ground"
SLOPE_MODE_UNKNOWN = G + "slope_mode_unknown"
ANGLE_OUT_OF_RANGE = G + "angle_out_of_range"
AT_TOE_ELEVATION = G + "at_toe_elevation"
VERTICAL_FACE = G + "vertical_face"
ABOVE_TOE = G + "above_toe"
NO_EXTERNAL = G + "no_external"
KEEP_BENCHES_ROTATE = G + "keep_benches_rotate"
CHANGE_OR_TARGET = G + "change_or_target"
FACE_RUNS_INTO = G + "face_runs_into"
SUPPORTS_NOT_MOVED = G + "supports_not_moved"
LOADS_NOT_MOVED = G + "loads_not_moved"
TOLERANCE_NOT_POSITIVE = G + "tolerance_not_positive"
TOLERANCE_TOO_COARSE = G + "tolerance_too_coarse"
EXTERNAL_NOT_CLOSED = G + "external_not_closed"
EXTERNAL_TOO_FEW = G + "external_too_few"
POLYLINE_TOO_FEW = G + "polyline_too_few"
ENDPOINTS_OFF_EXTERNAL = G + "endpoints_off_external"
EXPAND_SMALLER = G + "expand_smaller"
OFFSET_NEEDS_POLYGON = G + "offset_needs_polygon"

GEOMETRY_MESSAGES = {s.code: s for s in (
    MessageSpec(VERTEX_REF, "A vertex is an index or an [x, y] point."),
    MessageSpec(VERTEX_OUT_OF_RANGE, "Vertex index {ref} is outside 0..{last}."),
    MessageSpec(NOT_A_VERTEX,
                "({x:g}, {y:g}) is not a vertex of the External boundary."),
    MessageSpec(TOE_IS_CREST, "The toe and the crest are the same vertex."),
    MessageSpec(TOE_NOT_LOWER, "The toe must be lower than the crest."),
    MessageSpec(FACE_NOT_ON_GROUND,
                "The toe and the crest are not joined by the ground surface."),
    # ``modes`` is the tuple's own text, as the f-string printed it: a tuple
    # in the values would come back a list from JSON and print otherwise
    MessageSpec(SLOPE_MODE_UNKNOWN, "mode is one of {modes}."),
    MessageSpec(ANGLE_OUT_OF_RANGE,
                "The new overall angle must be between 0° and 90°."),
    MessageSpec(AT_TOE_ELEVATION,
                "A face vertex at the toe's elevation cannot be projected "
                "horizontally."),
    MessageSpec(VERTICAL_FACE, "A vertical face cannot be projected vertically."),
    MessageSpec(ABOVE_TOE,
                "A face vertex above the toe cannot be projected vertically."),
    MessageSpec(NO_EXTERNAL, "The model has no External boundary."),
    MessageSpec(KEEP_BENCHES_ROTATE,
                "keep_benches is only read by the horizontal and vertical "
                "projections, not by 'rotate'."),
    MessageSpec(CHANGE_OR_TARGET, "Give exactly one of change_deg or target_deg."),
    MessageSpec(FACE_RUNS_INTO,
                "At that angle the face runs into the rest of the External "
                "boundary (past the next vertex of the crest or the toe)."),
    # ``names`` are data (the first ten); a support's default name is shown
    # in the reader's language (``support_names``)
    MessageSpec(SUPPORTS_NOT_MOVED,
                "{n} support(s) had their head on the old face and were not "
                "moved: {names}.",
                kinds=(("names", "support_names"),)),
    MessageSpec(LOADS_NOT_MOVED,
                "{n} load(s) were on the old face and were not moved: {names}."),
    MessageSpec(TOLERANCE_NOT_POSITIVE,
                "the simplification tolerance must be positive"),
    MessageSpec(TOLERANCE_TOO_COARSE,
                "a tolerance of {epsilon:g} leaves {n} vertices; this boundary "
                "needs at least {need}"),
    MessageSpec(EXTERNAL_NOT_CLOSED, "External must be a closed polyline."),
    MessageSpec(EXTERNAL_TOO_FEW, "External has too few vertices."),
    MessageSpec(POLYLINE_TOO_FEW, "Polyline needs at least 2 vertices."),
    MessageSpec(ENDPOINTS_OFF_EXTERNAL,
                "Both endpoints of the polyline must lie on the External "
                "Boundary (use snap — green cross)."),
    MessageSpec(EXPAND_SMALLER,
                "Expand produced a smaller polygon — intermediate points are "
                "probably INSIDE the External. Use Shrink, or redraw with "
                "points outside."),
    MessageSpec(OFFSET_NEEDS_POLYGON,
                "offset_polygon requires a closed polygon with ≥3 vertices"),
)}


def geometry_message(code: str, **args) -> Coded:
    """The message ``code`` with ``args``: its English sentence, carrying the
    code and the values (v0.1.434, D412)."""
    return coded(GEOMETRY_MESSAGES, code, **args)
