# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The messages of the project's rules and settings, with stable codes
(v0.1.347, D335).

``rules.py`` and ``settings.py`` write sentences the interface shows: why a
run cannot start, why a Block Search object cannot be searched, what the
projection angles were read as, which region lost its material, what a
setting migrated from an old file could not carry. They were English with
their values baked in; each is a code here, with its English template and
the very format specs the f-string used, so the sentence is the one the
core wrote before and the interface translates the template.

A sentence assembled from English words ("left" / "right", "lower" /
"upper", one reason or another) is one whole template per variant.

The coarse ``Refusal.code`` stays what it was -- a program branches on it --
and the message carries this finer code.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ..messages import Coded, MessageSpec, coded

NO_BOUNDARIES = "rule.no_boundaries"
NO_MATERIALS = "rule.no_materials"
BLOCK_OBJECT_EMPTY = "rule.block_object_empty"
BLOCK_POINT_VERTICES = "rule.block_point_vertices"
BLOCK_LINE_VERTICES = "rule.block_line_vertices"
BLOCK_WINDOW_OPEN = "rule.block_window_open"
BLOCK_POLYLINE_SHAPE = "rule.block_polyline_shape"
BLOCK_POLYLINE_NOT_MONOTONE = "rule.block_polyline_not_monotone"
BLOCK_POLYLINE_SEGMENT_MODE = "rule.block_polyline_segment_mode"
BLOCK_ANGLE_REREAD_LEFT = "rule.block_angle_reread_left"
BLOCK_ANGLE_REREAD_RIGHT = "rule.block_angle_reread_right"
BLOCK_ANGLE_OUT_LEFT_LEFT_FACING = "rule.block_angle_out_left_left_facing"
BLOCK_ANGLE_OUT_LEFT_RIGHT_FACING = "rule.block_angle_out_left_right_facing"
BLOCK_ANGLE_OUT_RIGHT_LEFT_FACING = "rule.block_angle_out_right_left_facing"
BLOCK_ANGLE_OUT_RIGHT_RIGHT_FACING = "rule.block_angle_out_right_right_facing"
ORPHAN_REGION = "rule.orphan_region"
MIGRATION_COOLING = "rule.migration_cooling"
MIGRATION_FRAME = "rule.migration_frame"
MIGRATION_TOE_ANGLE_LOWER = "rule.migration_toe_angle_lower"
MIGRATION_TOE_ANGLE_UPPER = "rule.migration_toe_angle_upper"
MIGRATION_PATH_OPTIMIZE = "rule.migration_path_optimize"

_REREAD = (
    "The {label} projection angles are written from {start:g}° to {end:g}°, "
    "and the reference measures them counter-clockwise from the positive x "
    "axis with the Start Angle less than the End Angle. They were read as "
    "{lo:g}° to {hi:g}°: the arc between the two that avoids {forbidden}°, a "
    "direction no {label} projection can take.")
_OUT = (
    "The {label} projection angles, {lo:g}° to {hi:g}°, go outside "
    "{limit_lo:g}° to {limit_hi:g}°, the range the reference gives for "
    "kinematically valid surfaces on a {facing}-facing slope. The search uses "
    "them as given; a projection that cannot reach the ground leaves its "
    "surface invalid.")
_MIGRATION = ("This model carries {shadow} = {old}, removed in v0.1.103: "
              "{why} {survivor}. The stored value was NOT converted.")
_TOE_ANGLE = (
    "This model was saved before v0.1.103, and its Path Search {side} "
    "Initial Angle at Toe is ON at {angle}°. That number was read in the "
    "search's own toe-to-crest frame then and is read as ABSOLUTE now — "
    "counter-clockwise from the +x axis — so it does not describe the same "
    "limit. It was NOT converted: doing so needs the failure direction, "
    "which is not part of this block. Check "
    "path_initial_angle_at_toe_{side}_deg before trusting this run.")


def _fill(template: str, **words) -> str:
    """``template`` with some of its fields written in: the words that make
    one variant of a sentence, leaving the values as fields."""
    for k, v in words.items():
        template = template.replace("{%s}" % k, str(v))
    return template


RULES = {s.code: s for s in (
    MessageSpec(NO_BOUNDARIES,
                "No model to compute. Add an external boundary first."),
    MessageSpec(NO_MATERIALS, "No materials defined."),
    MessageSpec(BLOCK_OBJECT_EMPTY,
                "A Block Search object needs at least one vertex."),
    MessageSpec(BLOCK_POINT_VERTICES,
                "A Block Search Point is a single point; this one has {n} "
                "vertices."),
    MessageSpec(BLOCK_LINE_VERTICES,
                "A Block Search Line is one segment given by two points; "
                "this one has {n} vertices. A path of several segments that "
                "the surface should follow is a Block Search Polyline."),
    MessageSpec(BLOCK_WINDOW_OPEN,
                "A Block Search Window is a closed polygon of at least three "
                "vertices."),
    MessageSpec(BLOCK_POLYLINE_SHAPE,
                "A Block Search Polyline is an open line of at least two "
                "vertices."),
    MessageSpec(BLOCK_POLYLINE_NOT_MONOTONE,
                "A Block Search Polyline has to advance in x from one end to "
                "the other: the trial surface follows it between its two "
                "points, and a polyline that doubles back (or has a vertical "
                "segment) would give a surface that reverses direction."),
    MessageSpec(BLOCK_POLYLINE_SEGMENT_MODE,
                "The Left / Right Line Segment option places its point on the "
                "end segment of that side, which needs a polyline of at least "
                "two segments; this one has one. Use Any Line Segment or End "
                "Point."),
    MessageSpec(BLOCK_ANGLE_REREAD_LEFT,
                _fill(_REREAD, label="left", forbidden=0)),
    MessageSpec(BLOCK_ANGLE_REREAD_RIGHT,
                _fill(_REREAD, label="right", forbidden=180)),
    MessageSpec(BLOCK_ANGLE_OUT_LEFT_LEFT_FACING,
                _fill(_OUT, label="left", facing="left")),
    MessageSpec(BLOCK_ANGLE_OUT_LEFT_RIGHT_FACING,
                _fill(_OUT, label="left", facing="right")),
    MessageSpec(BLOCK_ANGLE_OUT_RIGHT_LEFT_FACING,
                _fill(_OUT, label="right", facing="left")),
    MessageSpec(BLOCK_ANGLE_OUT_RIGHT_RIGHT_FACING,
                _fill(_OUT, label="right", facing="right")),
    MessageSpec(ORPHAN_REGION,
                "The region at ({x:.2f}, {y:.2f}) is assigned a material that "
                "no longer exists. Assign it another material (Properties > "
                "Assign Materials); a surface through it cannot be analysed."),
    MessageSpec(MIGRATION_COOLING,
                _fill(_MIGRATION,
                      why="it held a geometric cooling rate that no analysis "
                          "ever read; the coefficient the schedule does use "
                          "is")),
    MessageSpec(MIGRATION_FRAME,
                _fill(_MIGRATION,
                      why="it held an angle in the search's own toe-to-crest "
                          "frame and the field replacing it is absolute, so "
                          "converting it needs the failure direction, which "
                          "is not part of this block. The field to set is")),
    MessageSpec(MIGRATION_TOE_ANGLE_LOWER, _fill(_TOE_ANGLE, side="lower")),
    MessageSpec(MIGRATION_TOE_ANGLE_UPPER, _fill(_TOE_ANGLE, side="upper")),
    MessageSpec(MIGRATION_PATH_OPTIMIZE,
                "This model carries path_optimize = True, removed in v0.1.104. "
                "Path Search used to optimise its best surfaces whether or not "
                "anything asked it to, because that field defaulted to True "
                "and the interface never showed it. The optimisation is now "
                "the Optimize Surfaces checkbox, which is UNTICKED here, so "
                "this run does not optimise. Tick it to get the old "
                "behaviour."),
)}


def rule_message(code: str, **args) -> Coded:
    """The message ``code`` with ``args``: its English sentence, carrying the
    code and the values."""
    return coded(RULES, code, **args)
