# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The model of a Generalized Anisotropic child is served from its cache with
nothing else asked.

WHAT INVARIANT THIS PROTECTS.

V9 of the compute audit (v0.1.388). ``GeneralizedAnisotropic._child_model``
returns the strength model of a rule, of the base or of a joint, built once
per content of its dict. Until v0.1.387 every call — a hit too — imported
two modules and built the child's label before looking at the cache, and
the label is read only by the message of a child that cannot be built.
Tutorial 20 calls it 6 745 641 times with 3 misses; the run went from
66.8-68.4 s to 57.8-59.9 s (one fresh process per run, ABBA), with every
evaluation identical. Class A: no arithmetic is touched.

1. **What it answers is v0.1.387's, call for call:** the v0.1.387 method is
   written out below and both are driven through the same sequence — a
   build, hits, a rule edited in place, a rule replaced by an equal dict, a
   child with no model and one that cannot be built — comparing the object
   returned (or the exception's type and message) at every step.
2. **A hit is served from the cache:** the same object as the build, and
   the label is not built for it. A miss builds it once.
3. **The comparison by value stays:** a dict edited in place is rebuilt,
   and so is one replaced by another object, as before.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def _ga(**over):
    """Three rules over two Mohr-Coulomb models, as in Tutorial 20."""
    from ogr_core.materials.builtin_models import (GeneralizedAnisotropic,
                                                   MohrCoulomb)
    soil = MohrCoulomb(cohesion=5.0, friction_angle=30.0).to_dict()
    bed = MohrCoulomb(cohesion=0.0, friction_angle=20.0).to_dict()
    rules = [{"model": dict(soil), "angle_min": -90.0, "angle_max": -10.0},
             {"model": dict(bed), "angle_min": -10.0, "angle_max": 10.0},
             {"model": dict(soil), "angle_min": 10.0, "angle_max": 90.0}]
    rules = over.get("rules", rules)
    return GeneralizedAnisotropic(rules=rules)


def _old_child_model(self, key, entry):
    """``GeneralizedAnisotropic._child_model`` of v0.1.387, copied."""
    import copy

    from ogr_core.materials.builtin_models import (
        IncompleteGeneralizedAnisotropic)
    from ogr_core.materials.strength_model import StrengthModel as _SM

    label = self.child_label(key)
    mdict = entry.get("model") if isinstance(entry, dict) else None
    cached = self._built.get(key)
    if cached is None or cached[0] is not mdict or cached[1] != mdict:
        if not mdict:
            built = IncompleteGeneralizedAnisotropic(
                f"{label} has no model")
        else:
            try:
                built = _SM.from_dict(mdict)
            except Exception as exc:  # noqa: BLE001 - as in v0.1.387
                built = IncompleteGeneralizedAnisotropic(
                    f"the model of {label} cannot be built: "
                    f"{type(exc).__name__}: {exc}")
        cached = (mdict, copy.deepcopy(mdict), built)
        self._built[key] = cached
    if isinstance(cached[2], Exception):
        raise cached[2]
    return cached[2]


def _answer(call):
    """What a call gives: the model's class and parameters, or the
    exception's type and message."""
    try:
        m = call()
    except Exception as exc:  # noqa: BLE001 - compared, not swallowed
        return ("raises", type(exc).__name__, str(exc))
    return ("model", type(m).__name__, dict(m.params), id(m))


def _drive(child_model):
    """The same sequence of calls against a fresh model; what each gave,
    with object identities replaced by the step that first returned them."""
    ga = _ga()
    seen, out = {}, []

    def step(key, entry):
        a = _answer(lambda: child_model(ga, key, entry))
        if a[0] == "model":
            a = a[:3] + (seen.setdefault(a[3], len(seen)),)
        out.append(a)

    r0 = ga.rules[0]
    step(("rules", 0), r0)                         # build
    step(("rules", 0), r0)                         # hit
    step(("rules", 1), ga.rules[1])                # another child
    step(("rules", 0), r0)                         # hit again
    r0["model"]["params"]["cohesion"] = 7.5        # edited in place
    step(("rules", 0), r0)
    step(("rules", 0), r0)
    r0["model"] = dict(r0["model"])                # replaced, equal content
    step(("rules", 0), r0)
    step(("rules", 2), {"angle_min": 10.0})        # no model
    step(("rules", 2), {"angle_min": 10.0})
    step(("joints", 0), {"model": {"model_id": "no_such_model"}})
    step(("joints", 0), {"model": {"model_id": "no_such_model"}})
    step(("base", None), "not a dict")
    return out


# ======================================================================
class TestItAnswersAsV0_1_387:
    """Invariant 1."""

    def test_the_same_sequence(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        new = _drive(GeneralizedAnisotropic._child_model)
        old = _drive(_old_child_model)
        assert new == old
        # and the sequence really went through every branch
        kinds = [a[0] for a in new]
        assert kinds.count("raises") == 5
        assert len({a[3] for a in new if a[0] == "model"}) == 4


# ======================================================================
class TestAHitIsServedFromTheCache:
    """Invariant 2."""

    def _spy_label(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        real = GeneralizedAnisotropic.__dict__["child_label"]
        calls = []

        def spy(key):
            calls.append(key)
            return real.__func__(key)

        GeneralizedAnisotropic.child_label = staticmethod(spy)
        return calls, real

    def test_the_same_object_and_no_label(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        ga = _ga()
        calls, real = self._spy_label()
        try:
            first = ga._child_model(("rules", 1), ga.rules[1])
            assert calls == [("rules", 1)], "a miss builds its label once"
            for _ in range(5):
                assert ga._child_model(("rules", 1), ga.rules[1]) is first
            assert calls == [("rules", 1)], "a hit built the label"
        finally:
            GeneralizedAnisotropic.child_label = real


# ======================================================================
class TestTheComparisonByValueStays:
    """Invariant 3."""

    def test_a_rule_edited_in_place_is_rebuilt(self):
        ga = _ga()
        r = ga.rules[0]
        first = ga._child_model(("rules", 0), r)
        r["model"]["params"]["friction_angle"] = 35.0
        again = ga._child_model(("rules", 0), r)
        assert again is not first
        assert again.params["friction_angle"] == 35.0

    def test_a_rule_replaced_by_an_equal_dict_is_rebuilt(self):
        ga = _ga()
        r = ga.rules[0]
        first = ga._child_model(("rules", 0), r)
        r["model"] = dict(r["model"])
        assert ga._child_model(("rules", 0), r) is not first
