# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D230 and D233 — the water and the rapid drawdown of the materials a
Generalized Anisotropic range links, and the stage-1 state of the drawdown on
a base with no linear envelope.

**The invariant (D230).** A Generalized Anisotropic material (the parent)
gives each slice base the strength of the range that holds its angle; a range
may link a material of the project (the child). The weight is always the
parent's. The WATER is the parent's while its «water parameters of the
parent» switch (``use_parent_water``) is on, the default and what every
earlier version computed; with it off, a base whose range links a child takes
the child's water — water surface, Hu, Ru, grid, the B-bar of loading and the
unsaturated strength — and a range without a link keeps the parent's. The
rapid drawdown is always the child's: whether it drains, its R or Kc = 1
envelope, the c′ and φ′ it is read with and its B-bar. The reference's
documentation of the model, which describes the option, the list of what it
covers and that it leaves out "rapid drawdown and multi-stage seismic
settings"; the defaults are the owner's decision (2026-09-30).

**The invariant (D233).** The stage-1 state of the multi-stage drawdown on a
base whose material has no linear effective envelope is the strength that
pass solved that base with, τ_fc = s(σ′fc)/F1 (Duncan, Wright & Brandon
2014, Eq. 9.3), not a zero.

What each class pins, and against what (rule 1)
-----------------------------------------------
1. Identities in the nine methods: children with the parent's own water give
   the same number with the switch off as on; one range −90..90 that links a
   child with ANOTHER water surface is, with the switch off, the plain
   material with the child's strength and water and the parent's weight, and
   with it on, the plain material with the parent's water (the two differ:
   rule 7).
2. By hand: u by angle band from two horizontal piezometric lines; a range
   without a link keeps the parent's water; a child's Ru multiplies the
   PARENT's weight, ru·γ_parent·z, and with a design standard ru·ξ·γ·z.
3. The rapid drawdown of EM 1110-2-1902 Appendix G (validated in the suite,
   ``test_drawdown_usace_v169``) with its undrained material wrapped in a
   Generalized material of one range gives the plain number in the three
   multi-stage procedures and in B-bar, with the parent drained or marked
   undrained (which used to refuse every surface).
4. D233: a Power Curve's stage-1 τ_fc is its own strength over F1, by hand;
   on the Appendix G slope made of a Generalized material whose ranges meet
   at θ = −20°, a range without a link gives the factor its drained twin
   gives (the zero gave +0.30 % with Lowe-Karafiath at 50 slices).
5. The switches (``slicer.GA_CHILD_WATER``,
   ``rapid_drawdown.GA_CHILD_DRAWDOWN``,
   ``rapid_drawdown.STAGE1_OWN_STRENGTH``) give back the v0.1.246 behaviour.
6. The model keeps the switch through the file, the design factors, the link
   resolution, the property import and the API (``replaced``); the rule
   refuses a value that is not a bool; the API says when it changes nothing;
   the dialog greys it out without a link and stores it.

Comparisons are relative, never ``==`` on doubles of different computations;
the identities that are the same computation are asserted at 1e-12.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_GW = 9.81
_REL = 1e-12
_PARENT_GAMMA = 19.0
_CHILD_GAMMA = 5.0          # never weighs anything: the weight is the parent's
_WT_Y = 26.0                # the parent's water table
_PIEZO_Y = 38.0             # a child's piezometric line
_PIEZO_Y2 = 30.0            # another child's
_CIRCLE = dict(centre_x=55.0, centre_y=58.0, radius=34.0)
_SLICES = 160


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


def _mc(c=10.0, phi=30.0):
    from ogr_core.materials.builtin_models import MohrCoulomb
    return MohrCoulomb(cohesion=c, friction_angle=phi)


def _line(p, y, btype):
    from ogr_core.geometry import Boundary, Polyline, Vertex
    b = Boundary(polyline=Polyline(vertices=[Vertex(0.0, y), Vertex(100.0, y)],
                                   closed=False), btype=btype)
    p.add_boundary(b)
    return b


def _base(water=True):
    """The slope of ``test_tension_crack_truncation_v1109`` (ground at 20 to
    x = 30, a 2:3 face to (60, 40), crest at 40), with the parent's water
    table at y = 26 and two piezometric lines, at 38 and at 30."""
    import test_tension_crack_truncation_v1109 as U
    from ogr_core.geometry import BoundaryType
    p = U._phi0_slope(crack_y=None)
    p.materials = []
    lines = {}
    if water:
        lines["wt"] = _line(p, _WT_Y, BoundaryType.WATER_TABLE)
        lines["p1"] = _line(p, _PIEZO_Y, BoundaryType.PIEZOMETRIC)
        lines["p2"] = _line(p, _PIEZO_Y2, BoundaryType.PIEZOMETRIC)
    return p, lines


def _water(m, line):
    from ogr_core.geometry import BoundaryType
    from ogr_core.materials import PorePressureType
    m.pore_pressure = (PorePressureType.WATER_TABLE
                       if line.btype == BoundaryType.WATER_TABLE
                       else PorePressureType.PIEZO_LINE)
    m.water_surface_id = line.id
    return m


def _paint(p, m):
    p.assign_material_at(*p.resolve_regions()[0].centroid(), m.id)


def _rule(lo, hi, child=None, model=None):
    r = {"angle_min": lo, "angle_max": hi,
         "model": (model or child.strength).to_dict()}
    if child is not None:
        r["material_id"] = child.id
    return r


def _generalized(rules_of, parent_water=True, children=(), parent_line="wt",
                 water=True):
    """A project whose one region is a Generalized parent (γ = 19, the
    parent's water table) with ``rules_of(children_by_name)`` ranges."""
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    p, lines = _base(water)
    kids = {}
    for name, line, strength in children:
        m = Material(name=name, unit_weight=_CHILD_GAMMA, strength=strength)
        if line is not None:
            _water(m, lines[line])
        kids[name] = m
    g = Material(name="parent", unit_weight=_PARENT_GAMMA,
                 strength=GeneralizedAnisotropic(
                     rules=rules_of(kids), use_parent_water=parent_water))
    if water and parent_line is not None:
        _water(g, lines[parent_line])
    p.materials = [g] + list(kids.values())
    _paint(p, g)
    return p, g, kids, lines


def _plain(line_name, strength=None):
    """The same slope, one plain material: γ = 19, the given water."""
    from ogr_core.materials import Material
    p, lines = _base()
    m = Material(name="plain", unit_weight=_PARENT_GAMMA,
                 strength=strength or _mc())
    if line_name is not None:
        _water(m, lines[line_name])
    p.materials = [m]
    _paint(p, m)
    return p


def _sliced(p):
    from ogr_core.project import prepare_analysis_project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    work = prepare_analysis_project(p)[0]
    c = SlipCircle(**_CIRCLE)
    sl = slice_surface(work, c, num_slices=_SLICES)
    assert sl is not None
    return work, c, sl


def _fos(p, method="bishop_simplified"):
    from ogr_slip2d.methods import get_method
    work, c, sl = _sliced(p)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


def _one_range(parent_water):
    return _generalized(lambda k: [_rule(-90.0, 90.0, k["child"])],
                        parent_water,
                        children=[("child", "p1", _mc())])[0]


class _Switch:
    """Set a module switch for a block, and put it back."""

    def __init__(self, module, name, value):
        self.module, self.name, self.value = module, name, value

    def __enter__(self):
        self.old = getattr(self.module, self.name)
        setattr(self.module, self.name, self.value)

    def __exit__(self, *exc):
        setattr(self.module, self.name, self.old)
        return False


# ======================================================================
class TestIdentities:
    """Rule 1: the nine methods against materials that are not Generalized."""

    def test_children_with_the_parents_water_ignore_the_switch(self):
        def build(parent_water):
            return _generalized(
                lambda k: [_rule(-90.0, 0.0, k["a"]),
                           _rule(0.0, 90.0, k["b"])],
                parent_water,
                children=[("a", "wt", _mc(10.0, 30.0)),
                          ("b", "wt", _mc(5.0, 35.0))])[0]
        for m in _nine():
            on, off = _fos(build(True), m), _fos(build(False), m)
            assert _close(on, off), (m, on, off)

    def test_switch_off_is_the_plain_material_with_the_childs_water(self):
        for m in _nine():
            g = _fos(_one_range(False), m)
            plain = _fos(_plain("p1"), m)
            assert _close(g, plain), (m, g, plain)

    def test_switch_on_is_the_plain_material_with_the_parents_water(self):
        for m in _nine():
            on = _fos(_one_range(True), m)
            plain = _fos(_plain("wt"), m)
            assert _close(on, plain), (m, on, plain)
            # Rule 7: the switch moves the number.
            off = _fos(_one_range(False), m)
            assert abs(off / on - 1.0) > 0.01, (m, on, off)


# ======================================================================
class TestByHand:

    def test_the_pore_pressure_follows_the_band_of_each_base(self):
        from ogr_core.materials.builtin_models import fold_plane_angle_deg
        p, _g, kids, _l = _generalized(
            lambda k: [_rule(-90.0, 0.0, k["a"]), _rule(0.0, 90.0, k["b"])],
            False, children=[("a", "p1", _mc()), ("b", "p2", _mc())])
        _w, _c, sl = _sliced(p)
        seen = set()
        for s in sl.slices:
            a = fold_plane_angle_deg(math.degrees(s.base_angle))
            band = "a" if a <= 0.0 + 1e-9 else "b"
            y_w = _PIEZO_Y if band == "a" else _PIEZO_Y2
            y = 0.5 * (s.base_y_left + s.base_y_right)
            expected = _GW * max(0.0, y_w - y)
            assert _close(s.pore_pressure, expected, 1e-12), (
                s.index, a, s.pore_pressure, expected)
            assert s.water_material.id == kids[band].id
            seen.add(band)
        assert seen == {"a", "b"}

    def test_a_range_without_a_link_keeps_the_parents_water(self):
        from ogr_core.materials.builtin_models import fold_plane_angle_deg
        p, g, kids, _l = _generalized(
            lambda k: [_rule(-90.0, 0.0, model=_mc()),
                       _rule(0.0, 90.0, k["b"])],
            False, children=[("b", "p1", _mc())])
        _w, _c, sl = _sliced(p)
        own = linked = 0
        for s in sl.slices:
            a = fold_plane_angle_deg(math.degrees(s.base_angle))
            y = 0.5 * (s.base_y_left + s.base_y_right)
            if a <= 1e-9:
                assert s.water_material is None
                expected = _GW * max(0.0, _WT_Y - y)
                own += 1
            else:
                assert s.water_material.id == kids["b"].id
                expected = _GW * max(0.0, _PIEZO_Y - y)
                linked += 1
            assert _close(s.pore_pressure, expected, 1e-12), (
                s.index, s.pore_pressure, expected)
        assert own and linked

    def _ru(self, design=False):
        from ogr_core.materials import PorePressureType
        p, g, kids, _l = _generalized(
            lambda k: [_rule(-90.0, 90.0, k["ru"])], False,
            children=[("ru", None, _mc())], water=False, parent_line=None)
        kids["ru"].pore_pressure = PorePressureType.RU_COEFFICIENT
        kids["ru"].ru = 0.3
        if design:
            ds = p.settings.design_standard
            ds.enabled = True
            ds.apply_preset("eurocode7_da1c1")
        return p

    def test_a_childs_ru_multiplies_the_parents_weight(self):
        _w, _c, sl = _sliced(self._ru())
        for s in sl.slices:
            z = 0.5 * (s.top_y_left + s.top_y_right) - 0.5 * (
                s.base_y_left + s.base_y_right)
            expected = 0.3 * _PARENT_GAMMA * max(0.0, z)
            assert _close(s.pore_pressure, expected, 1e-12), (
                s.index, s.pore_pressure, expected)

    def test_with_a_design_standard_the_childs_ru_takes_the_factor(self):
        _w, _c, sl = _sliced(self._ru(design=True))
        factors = {s.weight_factor for s in sl.slices}
        assert factors == {1.35}, factors
        for s in sl.slices:
            z = 0.5 * (s.top_y_left + s.top_y_right) - 0.5 * (
                s.base_y_left + s.base_y_right)
            expected = 0.3 * (1.35 * _PARENT_GAMMA) * max(0.0, z)
            assert _close(s.pore_pressure, expected, 1e-12), (
                s.index, s.pore_pressure, expected)


# ======================================================================
def _appendix_g_wrapped(procedure, parent_undrained=False, b_bar=None):
    """Appendix G (``test_drawdown_usace_v169``) with its one material
    linked by a Generalized parent of one range: the parent weighs what the
    material weighs and keeps the water table; the child is the undrained
    one, with the R envelope."""
    import test_drawdown_usace_v169 as G
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    p = G._appendix_g(procedure=procedure)
    child = p.materials[0]
    if b_bar is not None:
        child.b_bar = b_bar
    g = Material(name="parent", unit_weight=child.unit_weight,
                 sat_unit_weight=child.sat_unit_weight,
                 strength=GeneralizedAnisotropic(rules=[
                     _rule(-90.0, 90.0, child)]),
                 pore_pressure=PorePressureType.WATER_TABLE)
    g.undrained_behaviour = parent_undrained
    p.materials = [g, child]
    _paint(p, g)
    return p


def _plain_g(procedure, b_bar=None):
    import test_drawdown_usace_v169 as G
    p = G._appendix_g(procedure=procedure)
    if b_bar is not None:
        p.materials[0].b_bar = b_bar
    return p


def _drawdown(p, procedure, n=50):
    import test_drawdown_usace_v169 as G
    from ogr_core.project import prepare_analysis_project
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import (B_BAR, BBarDrawdownMethod,
                                           rapid_drawdown_fos)
    from ogr_slip2d.slicer import slice_surface
    work = prepare_analysis_project(p)[0]
    c = G._circle()
    if procedure == B_BAR:
        meth = BBarDrawdownMethod(BishopSimplified(), num_slices=n)
        return meth.compute_fos(work, c, slice_surface(work, c,
                                                       num_slices=n)).fos
    return rapid_drawdown_fos(work, c, BishopSimplified(), num_slices=n,
                              procedure=procedure).fos


class TestRapidDrawdown:
    """The drawdown is the linked material's, whatever the switch says."""

    PROCEDURES = ("duncan_wright", "lowe_karafiath", "corps_2")

    def test_appendix_g_wrapped_is_appendix_g(self):
        for proc in self.PROCEDURES:
            plain = _drawdown(_plain_g(proc), proc)
            for undrained in (False, True):
                g = _drawdown(_appendix_g_wrapped(proc, undrained), proc)
                assert _close(g, plain), (proc, undrained, g, plain)

    def test_b_bar_reads_the_childs_switch_and_b_bar(self):
        plain = _drawdown(_plain_g("b_bar", 0.6), "b_bar")
        g = _drawdown(_appendix_g_wrapped("b_bar", b_bar=0.6), "b_bar")
        assert _close(g, plain), (g, plain)

    def test_off_the_parent_decides_again(self):
        import ogr_slip2d.rapid_drawdown as rd
        proc = "duncan_wright"
        plain = _drawdown(_plain_g(proc), proc)
        with _Switch(rd, "GA_CHILD_DRAWDOWN", False):
            drained = _drawdown(_appendix_g_wrapped(proc), proc)
            try:
                _drawdown(_appendix_g_wrapped(proc, True), proc)
            except rd.RapidDrawdownError as exc:
                assert "linear effective envelope" in str(exc)
            else:
                raise AssertionError("the parent marked undrained ran")
        # The parent is not undrained: every base drains, a higher factor.
        assert drained > plain * 1.2, (drained, plain)


# ======================================================================
def _band_model(theta, twin):
    """Appendix G, all of a Generalized material: [−90, θ] its own
    Mohr-Coulomb (or, ``twin``, a drained material with the same
    strength), [θ, 90] an undrained core."""
    import test_drawdown_usace_v169 as G
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    from ogr_core.materials.drawdown_envelopes import REnvelope
    p = G._appendix_g(procedure="lowe_karafiath")
    wt = p.materials[0].water_surface_id

    def soil(name):
        m = Material(name=name, unit_weight=135.0, sat_unit_weight=135.0,
                     strength=_mc(0.0, 30.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
        m.water_surface_id = wt
        return m
    core, other = soil("core"), soil("twin")
    core.undrained_behaviour = True
    core.drawdown_envelope = REnvelope(c_r=1200.0, phi_r_deg=16.0)
    first = (_rule(-90.0, theta, other) if twin
             else _rule(-90.0, theta, model=_mc(0.0, 30.0)))
    g = soil("parent")
    g.strength = GeneralizedAnisotropic(rules=[first,
                                               _rule(theta, 90.0, core)])
    p.materials = [g, core, other]
    _paint(p, g)
    return p


class TestStage1State:
    """D233: τ_fc is the strength the stage-1 pass solved the base with."""

    def test_a_power_curve_gives_its_own_strength_over_f1(self):
        import test_drawdown_usace_v169 as G
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import Material, PorePressureType
        from ogr_core.materials.builtin_models import PowerCurve
        from ogr_slip2d.checks import equilibrium_fos
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import _level_project, _stage1_state
        from ogr_slip2d.slicer import slice_surface
        p = G._appendix_g(procedure="duncan_wright")
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(150.0, 0.0), Vertex(150.0, 200.0)],
            closed=False), btype=BoundaryType.MATERIAL))
        a, b, c0 = 0.8, 0.9, 50.0
        rock = Material(name="rock", unit_weight=135.0, sat_unit_weight=135.0,
                        strength=PowerCurve(a=a, b=b, c=c0, d=0.0,
                                            waviness=0.0),
                        pore_pressure=PorePressureType.WATER_TABLE)
        rock.water_surface_id = p.materials[0].water_surface_id
        p.materials.append(rock)
        p.assign_material_at(160.0, 20.0, rock.id)
        p1 = _level_project(p, use_drawdown=False)
        sl = slice_surface(p1, G._circle(), num_slices=50)
        r1 = BishopSimplified().compute_fos(p1, G._circle(), sl)
        f1 = equilibrium_fos(r1)
        state = _stage1_state(p, G._circle(), sl, r1)
        n = 0
        for (x0, x1, sigma, tau), s in zip(state, sl.slices):
            if s.material is not rock:
                continue
            n += 1
            assert sigma > 0.0
            expected = (c0 + a * sigma ** b) / f1
            assert _close(tau, expected, 1e-12), (s.index, tau, expected)
        assert n > 5, n

    def test_a_range_without_a_link_is_its_drained_twin(self):
        # Measured with the zero: +0.30 % at θ = −20°, 50 slices.
        a = _drawdown(_band_model(-20.0, False), "lowe_karafiath")
        b = _drawdown(_band_model(-20.0, True), "lowe_karafiath")
        assert _close(a, b), (a, b)

    def test_off_the_zero_comes_back(self):
        import ogr_slip2d.rapid_drawdown as rd
        twin = _drawdown(_band_model(-20.0, True), "lowe_karafiath")
        with _Switch(rd, "STAGE1_OWN_STRENGTH", False):
            zero = _drawdown(_band_model(-20.0, False), "lowe_karafiath")
        assert zero / twin - 1.0 > 0.002, (zero, twin)


# ======================================================================
class TestSwitchOff:

    def test_without_the_child_water_the_parent_decides(self):
        import ogr_slip2d.slicer as S
        with _Switch(S, "GA_CHILD_WATER", False):
            off = _fos(_one_range(False))
        on_parent = _fos(_plain("wt"))
        assert _close(off, on_parent), (off, on_parent)


# ======================================================================
class TestTheSwitchTravels:

    def test_the_file_keeps_it_and_an_old_file_is_on(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.materials.strength_model import StrengthModel
        g = GeneralizedAnisotropic(rules=[_rule(-90.0, 90.0, model=_mc())],
                                   use_parent_water=False)
        d = g.to_dict()
        assert d["use_parent_water"] is False
        assert StrengthModel.from_dict(d).use_parent_water is False
        del d["use_parent_water"]
        assert StrengthModel.from_dict(d).use_parent_water is True

    def test_the_rebuilt_models_keep_it(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.project import prepare_analysis_project
        from ogr_core.project.properties_import import import_properties
        # Design factors on an unlinked range, and the link resolution.
        p, g, kids, _l = _generalized(
            lambda k: [_rule(-90.0, 0.0, model=_mc(5.0, 25.0)),
                       _rule(0.0, 90.0, k["b"])],
            False, children=[("b", "p1", _mc())])
        ds = p.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da1c2")
        work = prepare_analysis_project(p)[0]
        wg = next(m for m in work.materials if m.name == "parent")
        assert wg.strength is not g.strength
        assert wg.strength.use_parent_water is False
        # The property import.
        p2, _l2 = _base()
        import_properties(p2, p, support_types=False)
        imported = next(m for m in p2.materials if m.name == "parent")
        assert isinstance(imported.strength, GeneralizedAnisotropic)
        assert imported.strength.use_parent_water is False
        # ``replaced`` itself.
        r = g.strength.replaced(rules=[])
        assert r.use_parent_water is False and r.rules == []

    def test_the_api_keeps_it_through_a_delete(self):
        from ogr_api import call
        ws, pid = self._ws(False)
        call(ws, "material_delete", project_id=pid, material="Clay",
             force=True)
        g = next(m for m in ws.get(pid).project.materials
                 if m.name == "Bedded")
        assert g.strength.use_parent_water is False

    def test_an_angle_no_rule_holds_raises_and_the_water_is_the_parents(self):
        # D218: the model never answers in place of a rule it lacks, the
        # lookup of a link included; the slicer's water falls to the parent,
        # and the strength at that base raises.
        import ogr_slip2d.slicer as S
        from ogr_core.materials.builtin_models import (
            IncompleteGeneralizedAnisotropic)
        p, g, kids, _l = _generalized(
            lambda k: [_rule(-90.0, 0.0, k["a"]), _rule(10.0, 90.0, k["a"])],
            False, children=[("a", "p1", _mc())])
        for call in (g.strength.rule_index_for_angle,
                     g.strength.linked_material_id):
            try:
                call(5.0)
            except IncompleteGeneralizedAnisotropic:
                pass
            else:
                raise AssertionError(f"{call.__name__} answered at 5°")
        assert S.water_material(p, g, math.radians(5.0)) is g
        assert S.water_material(p, g, math.radians(-5.0)) is kids["a"]

    def test_the_rule_wants_a_bool(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.project.rules import strength_model_refusal
        ok = GeneralizedAnisotropic(rules=[_rule(-90.0, 90.0, model=_mc())],
                                    use_parent_water=False)
        assert strength_model_refusal(ok, "G") is None
        bad = GeneralizedAnisotropic(rules=[_rule(-90.0, 90.0, model=_mc())],
                                     use_parent_water=0)
        why = strength_model_refusal(bad, "G")
        assert why is not None and why.code == "generalized_parent_water"

    # ------------------------------------------------------------------
    @staticmethod
    def _ws(parent_water, link=True):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="Water")["project_id"]
        rule = ({"angle_min": -90, "angle_max": 90, "material": "Clay"}
                if link else
                {"angle_min": -90, "angle_max": 90,
                 "model": _mc().to_dict()})
        out = call(ws, "model_define", project_id=pid, spec={
            "external": [[0, -10], [60, -10], [60, 12], [50, 12], [30, 0],
                         [0, 0]],
            "materials": [
                {"name": "Clay", "unit_weight": 20.0,
                 "strength": {"model": "mohr_coulomb",
                              "params": {"cohesion": 5.0,
                                         "friction_angle": 30.0}}},
                {"name": "Bedded", "unit_weight": 20.0, "strength": {
                    "model": "generalized_anisotropic", "rules": [rule],
                    "use_parent_water": parent_water}}]})
        ws.last_notes = out.get("notes", [])
        return ws, pid

    def test_the_api_stores_it_and_says_when_it_changes_nothing(self):
        ws, pid = self._ws(False)
        g = next(m for m in ws.get(pid).project.materials
                 if m.name == "Bedded")
        assert g.strength.use_parent_water is False
        assert not any("changes nothing" in n for n in ws.last_notes)
        ws, pid = self._ws(False, link=False)
        assert any("use_parent_water=false changes nothing" in n
                   for n in ws.last_notes), ws.last_notes


# ======================================================================
class TestTheDialog:

    def _materials(self, link=True, parent_water=True):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        clay = Material(name="Clay", strength=_mc(5.0, 30.0))
        rule = (_rule(-90.0, 90.0, clay) if link
                else _rule(-90.0, 90.0, model=_mc(2.0, 20.0)))
        g = Material(name="G", strength=GeneralizedAnisotropic(
            rules=[rule], use_parent_water=parent_water))
        return [clay, g]

    def _dialog(self, materials, row):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        dlg = MaterialPropertiesDialog(materials)
        dlg.list.setCurrentRow(row)
        calls = dlg.accepted_calls = []
        dlg.accept = lambda: calls.append(True)
        return dlg

    def test_greyed_out_without_a_link(self):
        dlg = self._dialog(self._materials(link=False), 1)
        chk = dlg.param_panel._chk_parent_water
        assert chk is not None and chk.isChecked()
        assert not chk.isEnabled()
        # Choosing a material for the range brings it to life.
        clay = dlg.materials[0]
        combo = dlg.param_panel._table.cellWidget(0, 1)
        combo.setCurrentIndex(combo.findData(f"material:{clay.id}"))
        assert chk.isEnabled()

    def test_unticked_is_stored_and_shown_again(self):
        mats = self._materials()
        dlg = self._dialog(mats, 1)
        chk = dlg.param_panel._chk_parent_water
        assert chk.isEnabled() and chk.isChecked()
        assert dlg.param_panel.is_unchanged()
        chk.setChecked(False)
        assert not dlg.param_panel.is_unchanged()
        dlg._ok()
        assert dlg.accepted_calls == [True]
        stored = dlg.result_materials()[1].strength
        assert stored.use_parent_water is False
        dlg2 = self._dialog(dlg.result_materials(), 1)
        assert not dlg2.param_panel._chk_parent_water.isChecked()
