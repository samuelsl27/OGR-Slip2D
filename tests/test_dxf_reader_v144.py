# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.44 — DXF reader and layer catalogue (Phase D0).

Phase D0 only reads and inventories: it must not touch the project model.
The tests therefore check faithful extraction rather than any geometric
repair, which belongs to Phase D1.

Points worth pinning down:

* **bulges** — a polyline can carry arcs encoded as a bulge value;
  ignoring them silently turns arcs into chords, which would corrupt a
  water table without any error being raised;
* **discretisation density** expressed per FULL circle, so the parameter
  behaves the same for a small fillet and a large sweep;
* **unit conversion**, with ``$INSUNITS`` used only as a suggestion
  because it is so often missing or wrong;
* **a malformed entity must not abort the import** — it is counted so the
  problem report can mention it;
* layer recognition proposes a type but never forces it, since the user
  must be able to map an arbitrary layer such as ``0``.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import ezdxf
    _HAS_EZDXF = True
except ImportError:  # pragma: no cover
    _HAS_EZDXF = False

from ogr_core.dxf import (  # noqa: E402
    LAYER_DEFAULTS,
    UNIT_FACTORS,
    DxfEntityKind as K,
    guess_kind,
    read_dxf,
)


def _requires_ezdxf(cls):
    return cls if _HAS_EZDXF else type(cls.__name__, (), {})


_DXF = Path("/tmp/ogr_test_model.dxf")


def _make_dxf(path=_DXF):
    """A drawing exercising every entity type and layer situation."""
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 6            # metres
    msp = doc.modelspace()
    for name in ("OGR_EXTERNAL", "OGR_MATERIAL", "OGR_WATER_TABLE",
                 "0", "Capa_rara", "OGR_SUPPORT"):
        if name not in doc.layers:
            doc.layers.add(name)
    # Deliberately OPEN external boundary (D1 will have to close it)
    msp.add_lwpolyline(
        [(0, 0), (120, 0), (120, 25), (75, 25), (50, 50), (0, 50)],
        dxfattribs={"layer": "OGR_EXTERNAL"})
    msp.add_line((0, 30), (75, 25), dxfattribs={"layer": "OGR_MATERIAL"})
    msp.add_line((0, 20), (120, 10), dxfattribs={"layer": "OGR_MATERIAL"})
    # Water table carrying a BULGE (an arc inside a polyline)
    msp.add_lwpolyline([(0, 35, 0.3), (60, 30, 0), (120, 28, 0)],
                       format="xyb",
                       dxfattribs={"layer": "OGR_WATER_TABLE"})
    msp.add_arc(center=(60, 40), radius=10, start_angle=0, end_angle=90,
                dxfattribs={"layer": "0"})
    msp.add_circle(center=(100, 15), radius=5,
                   dxfattribs={"layer": "0"})
    msp.add_spline([(10, 45), (30, 42), (50, 44), (70, 40)],
                   dxfattribs={"layer": "Capa_rara"})
    msp.add_line((60, 35), (75, 28),
                 dxfattribs={"layer": "OGR_SUPPORT"})
    msp.add_text("nota", dxfattribs={"layer": "0"}).set_placement((5, 5))
    doc.saveas(str(path))
    return path


class TestLayerRecognition:
    def test_default_names(self):
        assert guess_kind("OGR_EXTERNAL") == K.EXTERNAL
        assert guess_kind("OGR_MATERIAL") == K.MATERIAL
        assert guess_kind("OGR_WATER_TABLE") == K.WATER_TABLE
        assert guess_kind("OGR_SUPPORT") == K.SUPPORT

    def test_case_and_separator_insensitive(self):
        for name in ("ogr_external", "OGR EXTERNAL", "OgrExternal",
                     "OGR-EXTERNAL"):
            assert guess_kind(name) == K.EXTERNAL, name

    def test_spanish_aliases(self):
        assert guess_kind("FREATICO") == K.WATER_TABLE
        assert guess_kind("NIVEL_FREATICO") == K.WATER_TABLE
        assert guess_kind("GRIETA") == K.TENSION_CRACK
        assert guess_kind("ANCLAJES") == K.SUPPORT
        assert guess_kind("DESEMBALSE") == K.DRAWDOWN
        assert guess_kind("MATERIALES") == K.MATERIAL

    def test_unknown_layers_are_left_to_the_user(self):
        """Layer 0 and arbitrary names must NOT be guessed: the dialog
        lets the user map them."""
        for name in ("0", "Capa_rara", "Layer1", ""):
            assert guess_kind(name) == K.IGNORE, name

    def test_exact_match_wins_over_partial(self):
        assert guess_kind("MATERIAL") == K.MATERIAL

    def test_every_kind_has_defaults(self):
        for kind in (K.EXTERNAL, K.MATERIAL, K.WATER_TABLE, K.PIEZO,
                     K.DRAWDOWN, K.TENSION_CRACK, K.SUPPORT):
            assert kind in LAYER_DEFAULTS
            assert LAYER_DEFAULTS[kind]


@_requires_ezdxf
class TestReading:
    def test_all_layers_catalogued(self):
        cat = read_dxf(_make_dxf(), unit="m", segments_per_circle=32)
        names = {lay.name for lay in cat.layers}
        assert {"OGR_EXTERNAL", "OGR_MATERIAL", "OGR_WATER_TABLE",
                "OGR_SUPPORT", "0", "Capa_rara"} <= names

    def test_entity_counts_per_layer(self):
        cat = read_dxf(_make_dxf(), unit="m")
        mat = cat.by_name("OGR_MATERIAL")
        assert mat.entity_counts.get("LINE") == 2
        zero = cat.by_name("0")
        assert zero.entity_counts.get("ARC") == 1
        assert zero.entity_counts.get("CIRCLE") == 1

    def test_proposed_kinds(self):
        cat = read_dxf(_make_dxf(), unit="m")
        assert cat.by_name("OGR_EXTERNAL").proposed_kind == K.EXTERNAL
        assert cat.by_name("OGR_MATERIAL").proposed_kind == K.MATERIAL
        assert cat.by_name("0").proposed_kind == K.IGNORE
        assert cat.by_name("Capa_rara").proposed_kind == K.IGNORE

    def test_lines_become_two_point_polylines(self):
        cat = read_dxf(_make_dxf(), unit="m")
        for p in cat.by_name("OGR_MATERIAL").polylines:
            assert p.n == 2
            assert p.closed is False

    def test_external_read_as_open(self):
        """The drawing has it open on purpose; D0 must report that
        faithfully instead of quietly closing it."""
        cat = read_dxf(_make_dxf(), unit="m")
        ext = cat.by_name("OGR_EXTERNAL").polylines[0]
        assert ext.closed is False
        assert math.dist(ext.points[0], ext.points[-1]) > 1.0

    def test_spline_is_flattened(self):
        cat = read_dxf(_make_dxf(), unit="m", segments_per_circle=32)
        lay = cat.by_name("Capa_rara")
        assert lay.polylines, "spline was not read"
        assert lay.polylines[0].n > 4      # more than the control points

    def test_unsupported_entities_are_counted_not_fatal(self):
        cat = read_dxf(_make_dxf(), unit="m")
        assert "TEXT" in cat.skipped
        assert cat.total_entities > 0      # the rest still came through

    def test_handles_recorded_for_the_problem_report(self):
        cat = read_dxf(_make_dxf(), unit="m")
        for lay in cat.layers:
            for p in lay.polylines:
                assert p.handle


@_requires_ezdxf
class TestBulges:
    def test_bulge_becomes_an_arc_not_a_chord(self):
        """A bulge silently ignored would turn an arc into a straight
        line: the water table has three points, so a chord reading would
        give exactly three vertices."""
        cat = read_dxf(_make_dxf(), unit="m", segments_per_circle=32)
        wt = cat.by_name("OGR_WATER_TABLE").polylines[0]
        assert wt.n > 3, wt.n

    def test_bulge_keeps_the_exact_endpoints(self):
        cat = read_dxf(_make_dxf(), unit="m", segments_per_circle=32)
        wt = cat.by_name("OGR_WATER_TABLE").polylines[0]
        assert abs(wt.points[0][0] - 0.0) < 1e-9
        assert abs(wt.points[-1][0] - 120.0) < 1e-9


@_requires_ezdxf
class TestDiscretisationDensity:
    def test_density_controls_vertex_count(self):
        counts = [read_dxf(_make_dxf(), unit="m",
                           segments_per_circle=spc).total_vertices
                  for spc in (8, 32, 128)]
        assert counts[0] < counts[1] < counts[2], counts

    def test_circle_gets_the_requested_segments(self):
        """A full circle must receive the density verbatim; the arc of 90
        degrees a quarter of it."""
        cat = read_dxf(_make_dxf(), unit="m", segments_per_circle=64)
        zero = cat.by_name("0")
        circle = [p for p in zero.polylines if p.source == "CIRCLE"][0]
        arc = [p for p in zero.polylines if p.source == "ARC"][0]
        assert 60 <= circle.n <= 70, circle.n
        assert 14 <= arc.n <= 20, arc.n

    def test_arc_points_lie_on_the_circle(self):
        cat = read_dxf(_make_dxf(), unit="m", segments_per_circle=32)
        arc = [p for p in cat.by_name("0").polylines
               if p.source == "ARC"][0]
        for x, y in arc.points:
            assert abs(math.dist((x, y), (60.0, 40.0)) - 10.0) < 1e-6


@_requires_ezdxf
class TestUnits:
    def test_conversion_to_metres(self):
        in_m = read_dxf(_make_dxf(), unit="m")
        in_mm = read_dxf(_make_dxf(), unit="mm")
        assert abs(in_mm.diagonal() / in_m.diagonal() - 0.001) < 1e-9

    def test_all_unit_factors(self):
        for name, factor in UNIT_FACTORS.items():
            cat = read_dxf(_make_dxf(), unit=name)
            base = read_dxf(_make_dxf(), unit="m")
            assert abs(cat.diagonal() / base.diagonal() - factor) < 1e-9

    def test_insunits_is_only_a_suggestion(self):
        """The header says metres, but reading as millimetres must be
        honoured: the header is advice, not a command."""
        cat = read_dxf(_make_dxf(), unit="mm")
        assert cat.suggested_unit() == "m"     # what the header says
        assert abs(cat.unit_factor - 0.001) < 1e-12   # what was used

    def test_default_is_metres(self):
        cat = read_dxf(_make_dxf())
        assert abs(cat.unit_factor - 1.0) < 1e-12


@_requires_ezdxf
class TestCatalogueHelpers:
    def test_polylines_for_kind_follows_user_choice(self):
        cat = read_dxf(_make_dxf(), unit="m")
        # The user maps layer 0 to material
        cat.by_name("0").kind = K.MATERIAL
        mats = cat.polylines_for(K.MATERIAL)
        assert len(mats) == 2 + len(cat.by_name("0").polylines)

    def test_diagonal_is_the_tolerance_reference(self):
        cat = read_dxf(_make_dxf(), unit="m")
        bb = cat.bbox()
        assert bb is not None
        assert abs(cat.diagonal()
                   - math.dist((bb[0], bb[1]), (bb[2], bb[3]))) < 1e-9
        assert cat.diagonal() > 100.0

    def test_layer_summary_is_readable(self):
        cat = read_dxf(_make_dxf(), unit="m")
        text = cat.by_name("OGR_MATERIAL").summary()
        assert "OGR_MATERIAL" in text and "LINE" in text

    def test_recognised_flag(self):
        cat = read_dxf(_make_dxf(), unit="m")
        assert cat.by_name("OGR_EXTERNAL").recognised is True
        assert cat.by_name("0").recognised is False


class TestErrorHandling:
    def test_missing_file_raises_clearly(self):
        try:
            read_dxf("/tmp/definitely_not_here.dxf")
        except RuntimeError as exc:
            assert "DXF" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")

    def test_not_a_dxf_raises(self):
        p = Path("/tmp/ogr_not_a_dxf.txt")
        p.write_text("this is not a drawing", encoding="utf-8")
        try:
            read_dxf(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected RuntimeError")
