# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The stage-2 materials of a rapid drawdown are copied, and the drained cap
reads each slice's c', phi' once.

WHAT INVARIANT THIS PROTECTS.

V16 of the compute audit (v0.1.395). Bank 097 (a multi-stage rapid
drawdown, Corps of Engineers) built 2.41 million stage-2 materials, 23.5 s
of 173 in serial, one base material per call of ``_undrained_slices``: the
constructor of ``Material`` assigns its 26 fields through a Python
``__setattr__``. And every pass of the drained cap read each undrained
slice's c', phi' again (2.85 million calls of ``_drawdown_material`` and
``_effective_c_phi``), the same call on the same slice of the same project
that stage 2 had made. Now the first stage-2 material of each base in a
call is constructed and the next ones are shallow copies of it with their
own ``Undrained`` and their own id, and stage 2 keeps the pair for the
cap. Class B: the same values, in the same fields and order.

1. **A drawdown is v0.1.394's, to the bit:** that version's
   ``rapid_drawdown_fos`` and ``_undrained_slices`` are written out below
   (without docstrings and comments) and run in a copy of the module's
   namespace; factors of every stage, cap passes, the cycle's horns and
   every number of the final result are compared, for the three
   procedures, on the converging and the oscillating circles of the
   Pilarcitos dam (test_rapid_drawdown_v168).
2. **Each stage-2 material is the constructor's,** field for field and in
   the same key order, with an id of its own drawn as the constructor draws
   it, a strength object of its own, and the slices around it unchanged —
   with bases interleaved, repeated and missing.
3. **A guard on ``Material``:** no default factory but ``id``, no
   ``__post_init__``, no ``__slots__``, no copy hooks, and the fields the
   stage-2 constructor leaves at their defaults hold immutable values —
   what makes a shallow copy the constructor's material.
4. **The work is counted:** the constructor once per base and call, and
   ``_effective_c_phi`` as often with the drained cap as without it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import uuid
from dataclasses import MISSING, fields

# v0.1.394's two functions, copied (ast.unparse of the source, docstrings
# and comments dropped: the same statements in the same order).
_OLD_SRC = '''
def _undrained_slices(slices, tau_by_index: dict):
    from ogr_core.materials.builtin_models import Undrained
    out = copy.copy(slices)
    out.slices = []
    for i, s in enumerate(slices.slices):
        if i not in tau_by_index:
            out.slices.append(s)
            continue
        s2 = copy.copy(s)
        base = s.material
        s2.material = Material(name=f"{getattr(base, 'name', 'soil')} (stage 2)", strength=Undrained(cohesion=tau_by_index[i]), unit_weight=getattr(base, 'unit_weight', 20.0), sat_unit_weight=getattr(base, 'sat_unit_weight', 21.0), use_sat_unit_weight=getattr(base, 'use_sat_unit_weight', False))
        s2.pore_pressure = 0.0
        s2.raw_pore_pressure = 0.0
        s2.suction_cohesion = 0.0
        out.slices.append(s2)
    return out


def rapid_drawdown_fos(project, surface, method, *, num_slices: int=25, procedure: str=DWW) -> DrawdownResult:
    from .slicer import slice_surface
    if procedure not in MULTISTAGE_METHODS:
        raise _refusal(msg.DRAWDOWN_UNKNOWN_PROCEDURE, procedure=procedure)
    corps = procedure == CORPS_2
    drained_cap = procedure in (DWW, CORPS_2)
    p1 = _level_project(project, use_drawdown=False)
    sl1 = slice_surface(p1, surface, num_slices=num_slices)
    if sl1 is None:
        raise _refusal(msg.DRAWDOWN_UNSLICEABLE_INITIAL)
    r1 = method.compute_fos(p1, surface, sl1)
    if r1.fos is None:
        raise DrawdownStageFailed(1, r1)
    if not r1.converged:
        raise DrawdownStageUnconverged(1, r1)
    if not r1.fos > 0.0:
        raise _refusal(msg.DRAWDOWN_STAGE1_UNUSABLE)
    if r1.fos < 1.0:
        raise _refusal(msg.DRAWDOWN_STAGE1_UNSTABLE, factor=r1.fos)
    state = _stage1_state(project, surface, sl1, r1)
    p2 = _level_project(project, use_drawdown=True)
    sl2 = slice_surface(p2, surface, num_slices=num_slices)
    if sl2 is None:
        raise _refusal(msg.DRAWDOWN_UNSLICEABLE_DRAWN_DOWN)
    tau_by_index: dict = {}
    for i, s in enumerate(sl2.slices):
        mat = _drawdown_material(p2, s)
        if not getattr(mat, 'undrained_behaviour', False):
            continue
        sampled = _sample_state(state, s.x_centre)
        if sampled is None:
            continue
        sigma_fc, tau_fc = sampled
        c_eff, phi_eff = _effective_c_phi(mat)
        if corps:
            tau_ff = _r_of(mat, phi_eff).strength_at(sigma_fc)
        else:
            tau_ff = undrained_strength_dww(sigma_fc, tau_fc, c_eff, phi_eff, _kc1_of(mat, phi_eff))
        tau_by_index[i] = max(0.0, tau_ff)
    sl2u = _undrained_slices(sl2, tau_by_index)
    r2 = method.compute_fos(p2, surface, sl2u)
    if r2.fos is None:
        raise DrawdownStageFailed(2, r2)
    res = DrawdownResult(fos=r2.fos, method=procedure, fos_stage1=r1.fos, fos_stage2=r2.fos, n_undrained_slices=len(tau_by_index), final_result=r2, invariant_details=_invariant_details(r2), stage1_result=r1)
    if not drained_cap or not tau_by_index:
        return res
    cur = dict(tau_by_index)
    omega = CAP_RELAXATION
    prev_fos = r2.fos
    prev_delta = None
    last = r2
    horn = None
    recent: list[float] = []
    passes = 0
    converged = False
    for _ in range(CAP_MAX_PASSES):
        normals2 = list(getattr(last, 'base_normal_force', ()) or ())
        if len(normals2) < len(sl2.slices):
            raise _refusal(msg.DRAWDOWN_CAP_NORMALS, method=getattr(last, 'method_id', '?'), count=len(normals2), slices=len(sl2.slices))
        nxt: dict = {}
        for i, tau_ff in tau_by_index.items():
            l = max(sl2.slices[i].base_length, 1e-09)
            sigma_d = max(0.0, normals2[i]) / l
            c_eff, phi_eff = _effective_c_phi(_drawdown_material(p2, sl2.slices[i]))
            target = composite_strength(tau_ff, sigma_d, c_eff, phi_eff)
            nxt[i] = (1.0 - omega) * cur[i] + omega * target
        if all((abs(nxt[i] - cur[i]) < 1e-12 for i in nxt)):
            converged = True
            break
        cur = nxt
        r3 = method.compute_fos(p2, surface, _undrained_slices(sl2, cur))
        if r3.fos is None:
            raise DrawdownStageFailed(3, r3, cap_pass=passes + 1)
        horn = last
        last = r3
        recent.append(r3.fos)
        passes += 1
        delta = r3.fos - prev_fos
        if abs(delta) < CAP_TOL:
            converged = True
            break
        if prev_delta is not None and delta * prev_delta < 0.0:
            omega = max(CAP_RELAXATION_MIN, 0.5 * omega)
        prev_delta = delta
        prev_fos = r3.fos
    if converged or len(recent) < 2:
        res.fos_stage3 = recent[-1] if recent else r2.fos
        res.final_result = last
    else:
        res.fos_stage3 = 0.5 * (recent[-1] + recent[-2])
        res.final_result = None
        res.cycle_horns = (horn, last)
        res.invariant_details = _invariant_details(last)
    res.n_cap_passes = passes
    res.cap_converged = converged
    if not converged:
        from .checks import base_m_alphas
        vals = base_m_alphas(last)
        res.cap_min_m_alpha = min(vals) if vals else None
    res.n_stage3_switched = sum((1 for i, tau_ff in tau_by_index.items() if cur[i] < tau_ff - 1e-12))
    if res.fos_stage3 < res.fos_stage2:
        res.fos = res.fos_stage3
    else:
        res.fos = res.fos_stage2
        res.final_result = r2
    return res
'''


def _old():
    """v0.1.394's ``rapid_drawdown_fos`` and ``_undrained_slices``, defined
    in a copy of the module's namespace (the old one calls the old one)."""
    import ogr_slip2d.rapid_drawdown as RD
    ns = dict(vars(RD))
    exec(compile(_OLD_SRC, "<rapid_drawdown v0.1.394>", "exec"), ns)
    return ns["rapid_drawdown_fos"], ns["_undrained_slices"]


def _pilarcitos():
    import importlib
    return importlib.import_module("test_rapid_drawdown_v168")._pilarcitos()


def _two_materials():
    """The Pilarcitos dam with a second undrained material upstream of
    x = 120 ft, of other c', phi' and envelope: the slices of one circle
    read two pairs, so the cap cannot take one slice's for another's."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.materials.drawdown_envelopes import REnvelope
    p = _pilarcitos()
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(120.0, 0.0), Vertex(120.0, 100.0)], closed=False),
        btype=BoundaryType.MATERIAL))
    m = Material(name="Upstream", unit_weight=130.0, sat_unit_weight=132.0,
                 strength=MohrCoulomb(cohesion=4.0, friction_angle=38.0),
                 pore_pressure=PorePressureType.WATER_TABLE)
    m.water_surface_id = p.materials[0].water_surface_id
    m.undrained_behaviour = True
    m.drawdown_envelope = REnvelope(c_r=40.0, phi_r_deg=20.0)
    p.materials.append(m)
    p.assign_material_at(60.0, 10.0, m.id)
    return p


def _circles():
    """The converging and the oscillating circles of
    test_rapid_drawdown_v168."""
    from ogr_slip2d.surface import SlipCircle
    return [SlipCircle(centre_x=100.0, centre_y=200.0, radius=160.0),
            SlipCircle(centre_x=120.0, centre_y=100.0, radius=80.0)]


def _plain(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return True
    if isinstance(v, (list, tuple)):
        return all(_plain(x) for x in v)
    return False


def _hexed(v):
    if isinstance(v, float):
        return v.hex()
    if isinstance(v, (list, tuple)):
        return [_hexed(x) for x in v]
    return v


def _numbers(obj):
    """Every plain value of a result, floats as hex."""
    if obj is None:
        return None
    return sorted((k, _hexed(v)) for k, v in vars(obj).items() if _plain(v))


def _drawdown_fields(res):
    horns = getattr(res, "cycle_horns", None)
    return (_numbers(res), _numbers(res.final_result),
            _numbers(res.stage1_result),
            [_numbers(h) for h in horns] if horns else None)


# ======================================================================
class TestADrawdownIsV0_1_394s:
    """Invariant 1."""

    def _compare(self, p):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        old_fos, _old_us = _old()
        passes = []
        for procedure in ("duncan_wright", "corps_2", "lowe_karafiath"):
            for c in _circles():
                new = rapid_drawdown_fos(p, c, BishopSimplified(),
                                         num_slices=25, procedure=procedure)
                old = old_fos(p, c, BishopSimplified(), num_slices=25,
                              procedure=procedure)
                assert _drawdown_fields(new) == _drawdown_fields(old)
                passes.append(new.n_cap_passes)
        return passes

    def test_three_procedures_two_circles(self):
        assert max(self._compare(_pilarcitos())) > 2, "the cap iterated"

    def test_two_undrained_materials(self):
        p = _two_materials()
        from ogr_slip2d.rapid_drawdown import (_drawdown_material,
                                               _effective_c_phi,
                                               _level_project)
        from ogr_slip2d.slicer import slice_surface
        sl = slice_surface(_level_project(p, use_drawdown=True),
                           _circles()[0], num_slices=25)
        pairs = {_effective_c_phi(_drawdown_material(p, s))
                 for s in sl.slices}
        assert len(pairs) == 2, pairs
        assert max(self._compare(p)) > 2, "the cap iterated"


# ======================================================================
def _interleaved():
    """Stage-2 slices of the Pilarcitos dam with three bases put on them:
    A, B, A again after B, and no material at all."""
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_slip2d.rapid_drawdown import _level_project
    from ogr_slip2d.slicer import slice_surface
    p = _pilarcitos()
    sl = slice_surface(_level_project(p, use_drawdown=True), _circles()[0],
                       num_slices=12)
    a = p.materials[0]
    b = Material(name="Core", unit_weight=118.0, sat_unit_weight=124.0,
                 strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
    b.use_sat_unit_weight = True
    bases = [a, a, b, b, a, None, a, b, None, a, a, b]
    assert len(sl.slices) == len(bases)
    for s, m in zip(sl.slices, bases):
        s.material = m
    tau = {i: 10.0 + 3.5 * i for i in (0, 1, 2, 4, 5, 6, 7, 8, 9, 11)}
    return sl, tau


def _material_fields(m):
    return [(f.name, getattr(m, f.name)) for f in fields(m)
            if f.name not in ("strength", "id")]


class TestEachStage2MaterialIsTheConstructors:
    """Invariant 2."""

    def test_field_for_field(self):
        from ogr_slip2d.rapid_drawdown import _undrained_slices
        _old_fos, old_us = _old()
        sl, tau = _interleaved()
        new, old = _undrained_slices(sl, tau), old_us(sl, tau)
        ids = set()
        strengths = set()
        for i, (s, n, o) in enumerate(zip(sl.slices, new.slices,
                                          old.slices)):
            if i not in tau:
                assert n is s and o is s
                continue
            mn, mo = n.material, o.material
            assert type(mn) is type(mo)
            assert _material_fields(mn) == _material_fields(mo)
            assert list(vars(mn)) == list(vars(mo)), "the key order"
            assert type(mn.strength) is type(mo.strength)
            assert ({k: v.hex() for k, v in mn.strength.params.items()}
                    == {k: v.hex() for k, v in mo.strength.params.items()})
            assert uuid.UUID(mn.id).version == 4 and len(mn.id) == 36
            assert mn.id != mo.id
            ids.add(mn.id)
            strengths.add(id(mn.strength))
            others = {k: v for k, v in vars(n).items() if k != "material"}
            assert repr(others) == repr(
                {k: v for k, v in vars(o).items() if k != "material"})
        assert len(ids) == len(tau) and len(strengths) == len(tau)
        assert len(new.slices) == len(old.slices) == len(sl.slices)


# ======================================================================
class TestAGuardOnMaterial:
    """Invariant 3."""

    def test_what_makes_a_shallow_copy_the_constructors(self):
        from enum import Enum
        from ogr_core.materials import Material, MohrCoulomb
        assert [f.name for f in fields(Material)
                if f.default_factory is not MISSING] == ["id"]
        for hook in ("__post_init__", "__slots__", "__copy__",
                     "__deepcopy__", "__reduce__", "__reduce_ex__",
                     "__getstate__", "__setstate__"):
            assert hook not in vars(Material), hook
        m = Material(name="x", strength=MohrCoulomb())
        passed = {"name", "strength", "unit_weight", "sat_unit_weight",
                  "use_sat_unit_weight", "id"}
        for f in fields(Material):
            if f.name not in passed:
                v = getattr(m, f.name)
                assert v is None or isinstance(
                    v, (bool, int, float, str, Enum)), (f.name, type(v))


# ======================================================================
class TestTheWorkIsCounted:
    """Invariant 4."""

    def test_the_constructor_once_per_base_and_call(self):
        from ogr_core.materials import Material
        from ogr_slip2d.rapid_drawdown import _undrained_slices
        sl, tau = _interleaved()
        real = Material.__dict__["__init__"]
        calls = [0]

        def init(self, *a, **k):
            calls[0] += 1
            real(self, *a, **k)

        Material.__init__ = init
        try:
            for _ in range(2):
                _undrained_slices(sl, tau)
            assert calls[0] == 2 * 3, "A, B and no material, per call"
        finally:
            Material.__init__ = real

    def test_c_phi_as_often_with_the_cap_as_without(self):
        import ogr_slip2d.rapid_drawdown as RD
        from ogr_slip2d.methods.bishop import BishopSimplified
        p = _pilarcitos()
        circle = _circles()[1]
        real = RD._effective_c_phi
        calls = [0]

        def counting(material):
            calls[0] += 1
            return real(material)

        RD._effective_c_phi = counting
        try:
            counts = {}
            for procedure in ("lowe_karafiath", "duncan_wright"):
                calls[0] = 0
                res = RD.rapid_drawdown_fos(p, circle, BishopSimplified(),
                                            num_slices=25,
                                            procedure=procedure)
                counts[procedure] = (calls[0], res.n_cap_passes)
        finally:
            RD._effective_c_phi = real
        assert counts["duncan_wright"][1] > 2
        assert counts["duncan_wright"][0] == counts["lowe_karafiath"][0]
