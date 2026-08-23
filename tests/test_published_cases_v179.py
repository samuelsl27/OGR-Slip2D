# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What `validacion/casos/` cannot assert on its own.

The case runner checks one thing per case: that the search reproduces the
published factor of safety. Three things it cannot check live here.

**1. That the geometry was read correctly.** Cases 001, 002 and 004 take
every coordinate from printed text or from labels drawn on the figure, so
there is nothing to verify. Case 003 (ACADS 1(c)) is different: the
coordinates are in the text but **how they connect is only in a drawing**,
and a plausible misreading would still produce a slope with a believable
factor of safety.

The independent check is the published critical circle. Its centre and its
two ground intersections are published; both intersections sit at exactly
18.781 from the centre, which is also how the radius was recovered (the
figure reads ambiguously between 16.781 and 18.781 — the endpoints settle
it). Placing that circle on our geometry has to daylight where the
reference says, and it does, to a millimetre. That is a fact about the
geometry alone, independent of any factor of safety.

**2. That Slope Search reproduces them too.** The runner executes what each
model declares, and all four declare a grid. Validating the directed search
on the published models is the whole point of v0.1.78, so it is asserted
here for the two homogeneous cases as well.

**3. That the cases stay honest.** Spencer and GLE are deliberately absent
from every `esperado.json` while
`docs/audits/spencer_gle_interslice_v179.md` is open. A test asserts that
absence, so re-adding them is a decision someone has to make on purpose
rather than a tidy-up.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CASES = _ROOT / "validacion" / "casos"

_CACHE: dict = {}


def _case(name):
    if name not in _CACHE:
        from ogr_core.project import Project
        _CACHE[name] = Project.load(_CASES / name / "modelo.ogr")
    return _CACHE[name]


def _expected(name):
    return json.loads((_CASES / name / "esperado.json").read_text(
        encoding="utf-8"))


# ======================================================================
class TestTheAcads1cGeometryIsTheReferenceGeometry:
    """The check that made case 003 admissible."""

    # Published with the critical circle in the verification manual.
    CENTRE = (34.121, 43.254)
    RADIUS = 18.781
    ENTRY_X, EXIT_X = 29.702, 50.991

    def test_the_published_endpoints_fix_the_radius(self):
        """Both published ground intersections lie at the same distance
        from the published centre, and that distance is the radius. This
        is what resolved the ambiguous digit in the figure."""
        import math
        cx, cy = self.CENTRE
        d1 = math.dist((cx, cy), (self.ENTRY_X, 25.0))
        d2 = math.dist((cx, cy), (self.EXIT_X, 35.0))
        assert abs(d1 - self.RADIUS) < 0.001, d1
        assert abs(d2 - self.RADIUS) < 0.001, d2

    def test_the_circle_daylights_where_the_reference_says(self):
        """A misread material boundary cannot survive this: the slope
        surface the circle cuts is fixed by the external boundary, and
        the entry and exit are published to three decimals."""
        from ogr_slip2d.slicer import _ground_surface_from_external
        from ogr_slip2d.surface import SlipCircle
        p = _case("003-acads-1c")
        c = SlipCircle(centre_x=self.CENTRE[0], centre_y=self.CENTRE[1],
                       radius=self.RADIUS)
        c.intersect_with_ground(_ground_surface_from_external(
            p.external_boundary()))
        assert abs(c.x_left - self.ENTRY_X) < 0.01, c.x_left
        assert abs(c.x_right - self.EXIT_X) < 0.01, c.x_right

    def test_three_regions_with_distinct_materials(self):
        """The layering is what distinguishes this case from 001."""
        p = _case("003-acads-1c")
        assert len(p.resolve_regions()) == 3
        assert len({m.id for m in p.materials}) == 3

    def test_bishop_on_the_published_circle(self):
        """On the exact published circle, not on one we searched for."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        res = ev.evaluate_circle(_case("003-acads-1c"), SlipCircle(
            centre_x=self.CENTRE[0], centre_y=self.CENTRE[1],
            radius=self.RADIUS))
        assert res is not None
        err = abs(res.fos - 1.405) / 1.405
        assert err < 0.01, f"FS={res.fos:.4f} err={err * 100:.2f}%"


class TestSlopeSearchOnThePublishedModels:
    """v0.1.78 validated the directed search on ACADS 1(a). These extend
    it to the two journal-referenced slopes, which have different heights
    and angles."""

    def _slope(self, case, method, n=2000, seed=42):
        from ogr_slip2d.search import SlopeSearch
        key = ("s", case, method.__class__.__name__, n, seed)
        if key not in _CACHE:
            _CACHE[key] = SlopeSearch(
                method=method, num_surfaces=n,
                num_slices=_expected(case)["busqueda"]["num_slices"],
                seed=seed).run(_case(case))
        return _CACHE[key]

    def test_yamagami_ueta(self):
        """Published Bishop 1.348 (Yamagami & Ueta 1988)."""
        from ogr_slip2d import BishopSimplified
        r = self._slope("002-yamagami-ueta-1988", BishopSimplified())
        assert r.critical is not None
        err = abs(r.critical.fos - 1.348) / 1.348
        assert err < 0.02, f"FoS={r.critical.fos:.4f} err={err * 100:.2f}%"

    def test_arai_tagyo(self):
        """Published Bishop 1.451 (Arai & Tagyo 1985), with the same 3.5 %
        the case declares — the spread is the source's, not ours."""
        from ogr_slip2d import BishopSimplified
        r = self._slope("004-arai-tagyo-1985-ej1", BishopSimplified())
        assert r.critical is not None
        err = abs(r.critical.fos - 1.451) / 1.451
        assert err < 0.035, f"FoS={r.critical.fos:.4f} err={err * 100:.2f}%"

    def test_it_is_at_least_as_critical_as_the_declared_grid(self):
        """The defining property of a directed search, on a slope four
        times taller than ACADS 1(a)."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.analysis_runner import build_search
        case = "004-arai-tagyo-1985-ej1"
        p = _case(case)
        grid = build_search(p, "bishop_simplified").run(p)
        slope = self._slope(case, BishopSimplified())
        assert slope.critical.fos <= grid.critical.fos * 1.01, (
            slope.critical.fos, grid.critical.fos)


class TestTheWaterTableMovesTheNumber:
    """Cases 004 and 005 are the SAME slope — same external boundary, same
    c', phi' and gamma — and differ only in that 005 carries a water
    table. That makes the pair a rule-7 check on pore pressure itself:
    if u were computed as zero, or at the wrong scale, 005 would drift
    and 004 would not.

    The published values put the drop at 22 % (1.451 dry, 1.138 wet), and
    a case that is only ever run alone cannot notice if that collapses.
    """

    def test_the_two_models_share_their_geometry_and_material(self):
        """The premise. If someone edits one model, this fails before the
        comparison below turns into a comparison of two different slopes."""
        dry, wet = _case("004-arai-tagyo-1985-ej1"), _case(
            "005-arai-tagyo-1985-ej3")
        vd = [(v.x, v.y) for v in dry.external_boundary().polyline.vertices]
        vw = [(v.x, v.y) for v in wet.external_boundary().polyline.vertices]
        assert vd == vw, (vd, vw)
        md, mw = dry.materials[0], wet.materials[0]
        assert md.unit_weight == mw.unit_weight
        # ``params`` and not attributes: a strength model that has been
        # through a save/load keeps its values in the dict.
        assert md.strength.params == mw.strength.params, (
            md.strength.params, mw.strength.params)

    def test_only_the_wet_model_has_a_water_table(self):
        from ogr_core.geometry import BoundaryType
        def tables(p):
            return [b for b in p.boundaries
                    if b.btype == BoundaryType.WATER_TABLE]
        assert not tables(_case("004-arai-tagyo-1985-ej1"))
        assert len(tables(_case("005-arai-tagyo-1985-ej3"))) == 1

    def test_the_water_drops_the_factor_of_safety_as_published(self):
        """Published: 1.451 dry, 1.138 wet — a 21.6 % drop. Ours has to
        land in the same neighbourhood, not merely be lower."""
        from ogr_slip2d.analysis_runner import build_search
        out = {}
        for name in ("004-arai-tagyo-1985-ej1", "005-arai-tagyo-1985-ej3"):
            p = _case(name)
            out[name] = build_search(p, "bishop_simplified").run(p).critical.fos
        dry = out["004-arai-tagyo-1985-ej1"]
        wet = out["005-arai-tagyo-1985-ej3"]
        drop = (dry - wet) / dry
        published = (1.451 - 1.138) / 1.451
        assert abs(drop - published) < 0.05, (
            f"water changes the FoS by {drop * 100:.1f} %, published "
            f"{published * 100:.1f} % (dry {dry:.4f}, wet {wet:.4f})")


class TestTheCasesStayHonestAboutSpencer:
    """Guards the decision recorded in
    docs/audits/spencer_gle_interslice_v179.md.

    v0.1.106 turned this class inside out, and the reason is worth stating
    because it is not "the audit closed, so the guard is obsolete".

    Until now the guard demanded that Spencer and GLE be ABSENT from every
    case, because the two returned the Bishop value and writing that down
    would have consecrated it (rule 1). The audit is closed and they no
    longer do — but they still do not belong in cases 001 to 004, for a
    DIFFERENT and permanent reason: those four expect a published CONSENSUS
    ("mean Bishop of 16 samples"), never one program's output, and the ACADS
    survey publishes no Spencer-specific mean for any of them. Its tables
    give "Mean Bishop FOS (n samples)" and "Mean FOS (n samples)" and nothing
    per rigorous method. A Spencer value taken from the verification manual's
    own results table would be one program's answer wearing a citation.

    So the guard now asserts the two things that are actually true: those
    four cases must NOT quote a per-method value they cannot source, and at
    least one case MUST discriminate a rigorous method from Bishop against a
    published number — which is what 007 does, on a circle the statement
    tabulates and against the arbitrated 2.29 that Bishop does not reproduce.
    """

    _RIGOROUS = ("spencer", "gle_morgenstern_price")
    # The cases whose expected values are survey CONSENSUS figures. The ACADS
    # report publishes no per-method mean for a rigorous method, so none of
    # these four can declare one without sourcing it to a single program.
    _CONSENSUS_CASES = ("001-acads-1a", "002-yamagami-ueta-1988",
                        "003-acads-1c", "004-arai-tagyo-1985-ej1")

    @staticmethod
    def _fos(path):
        spec = path / "esperado.json"
        if not spec.is_file():
            return None
        return json.loads(spec.read_text(encoding="utf-8")).get("fos") or {}

    def test_the_consensus_cases_quote_no_unsourced_per_method_value(self):
        for name in self._CONSENSUS_CASES:
            fos = self._fos(_CASES / name)
            if fos is None:
                continue
            offenders = [m for m in self._RIGOROUS if m in fos]
            assert not offenders, (
                f"{name} declares {offenders}, but the ACADS survey publishes "
                f"no per-method consensus for them — only 'Mean Bishop' and "
                f"'Mean FOS'. A value taken from the verification manual's "
                f"results table is one program's output.")

    def test_some_case_separates_a_rigorous_method_from_bishop(self):
        """The gap that let the defect live eighty versions.

        Every case validated a SEARCH, so each method was compared on the
        circle it found for itself and a method returning Bishop's number
        looked fine. A case is only evidence here if it states its surface
        and expects a rigorous method to differ from Bishop by more than the
        tolerance it allows.
        """
        import json as _json
        witnesses = []
        for path in sorted(p for p in _CASES.iterdir() if p.is_dir()):
            spec = path / "esperado.json"
            if not spec.is_file():
                continue
            data = _json.loads(spec.read_text(encoding="utf-8"))
            fos = data.get("fos") or {}
            if not data.get("superficie"):
                continue          # a search case cannot separate methods
            bishop = fos.get("bishop_simplified")
            if bishop is None:
                continue
            tol = float(data["tolerancia_relativa"])
            for mid in self._RIGOROUS:
                if mid not in fos:
                    continue
                gap = abs(fos[mid] - bishop) / abs(bishop)
                if gap > tol:
                    witnesses.append((path.name, mid, round(gap * 100, 2)))
        assert witnesses, (
            "no validation case can tell a rigorous method from Bishop: "
            "every case either searches for its own surface or expects the "
            "two to agree, which is exactly the blind spot that hid "
            "docs/audits/spencer_gle_interslice_v179.md for eighty versions")

    def test_the_report_exists(self):
        """A test that points at a document is only worth the document."""
        doc = _ROOT / "docs" / "audits" / "spencer_gle_interslice_v179.md"
        assert doc.is_file()
        assert len(doc.read_text(encoding="utf-8")) > 2000
