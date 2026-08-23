# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Validation cases — the automatic runner.

Walks `validacion/casos/` and checks every case whose model and expected
values are present. **Adding a case requires no code**: a folder with
`modelo.ogr`, `esperado.json` and `caso.md` is enough. That matters more
than it looks — the friction of writing a test is exactly what stops
validation cases from being added, and a calculation engine is worth
precisely the set of cases it reproduces.

Three deliberate choices:

* **The tolerance lives in the case, not here.** A factor of safety read
  off a published figure does not deserve the same demand as a tabulated
  one, and only the case knows which it is.
* **A missing source fails the case.** An expected value without a
  citation is an opinion, and a test that enshrines an opinion is worse
  than no test.
* **A case with no model is skipped, not failed**, so the template folder
  can live alongside the real ones without going red.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CASES = _ROOT / "validacion" / "casos"


def _case_dirs():
    if not _CASES.is_dir():
        return []
    return sorted(p for p in _CASES.iterdir() if p.is_dir())


def _load(path: Path):
    """Expected values of a case, or None when it is not runnable yet."""
    spec = path / "esperado.json"
    model = path / "modelo.ogr"
    if not spec.is_file() or not model.is_file():
        return None
    return json.loads(spec.read_text(encoding="utf-8"))


def _search_for(project, data: dict, method_id: str):
    """The search a case asks for, built the way the program builds it.

    v0.1.78. This used to be ``GridSearch(method=..., num_slices=...)``,
    always, ignoring everything the model said. Two consequences, both
    bad: a case could not validate any of the other five strategies, and
    the grid it ran was the default one rather than the case's own — so
    a model carrying the search parameters of a published problem was
    analysed with different ones.

    ``analysis_runner.build_search`` is "the single instantiation point"
    of the six strategies and is what both the interface and the CLI go
    through, so a case now validates **the search the program actually
    runs**, not a reconstruction of it that can drift.

    The overrides in ``esperado.json`` are applied to a **copy** of the
    settings: a validation run must not rewrite the case's own model.
    """
    import copy
    from ogr_slip2d.analysis_runner import build_search

    spec = data.get("busqueda") or {}
    proj = copy.copy(project)
    proj.settings = copy.deepcopy(project.settings)
    if spec.get("tipo"):
        proj.settings.search.search_method = spec["tipo"]
    if spec.get("num_slices"):
        proj.settings.methods.num_slices = int(spec["num_slices"])
    if spec.get("num_surfaces"):
        proj.settings.search.num_surfaces = int(spec["num_surfaces"])
    if spec.get("semilla") is not None:
        # ``statistics.seed`` is the explicit override that wins over the
        # Random Numbers page — see ProjectSettings.analysis_seed().
        proj.settings.statistics.seed = int(spec["semilla"])
    search = build_search(proj, method_id)
    assert search is not None, f"método no registrado: {method_id}"
    return search


class TestCaseFilesAreWellFormed:
    """Checked for EVERY folder, including ones with no model yet: a case
    that is half written should say so before it is trusted."""

    def test_every_case_has_the_three_files(self):
        for path in _case_dirs():
            assert (path / "caso.md").is_file(), path.name
            assert (path / "esperado.json").is_file(), path.name

    def test_expected_json_is_valid(self):
        for path in _case_dirs():
            data = json.loads(
                (path / "esperado.json").read_text(encoding="utf-8"))
            assert isinstance(data, dict), path.name

    def test_every_case_cites_a_source(self):
        """An expected value without a citation is an opinion."""
        for path in _case_dirs():
            data = json.loads(
                (path / "esperado.json").read_text(encoding="utf-8"))
            fuente = str(data.get("fuente", "")).strip()
            assert len(fuente) > 10, f"{path.name}: fuente ausente o vaga"

    def test_tolerance_is_declared_and_sane(self):
        for path in _case_dirs():
            data = json.loads(
                (path / "esperado.json").read_text(encoding="utf-8"))
            tol = data.get("tolerancia_relativa")
            assert isinstance(tol, (int, float)), path.name
            # Above 10 % a "validation" stops discriminating anything.
            assert 0 < tol <= 0.10, f"{path.name}: tolerancia {tol}"

    def test_method_ids_exist(self):
        """A typo in a method id would silently validate nothing."""
        from ogr_slip2d.methods import method_registry
        known = set(method_registry())
        for path in _case_dirs():
            data = json.loads(
                (path / "esperado.json").read_text(encoding="utf-8"))
            for mid in (data.get("fos") or {}):
                assert mid in known, f"{path.name}: método '{mid}'"

    def test_search_type_exists(self):
        """Same reason as the method ids, one level along.

        Until v0.1.78 the runner instantiated ``GridSearch`` and nothing
        else, so a case declaring ``"tipo": "slope"`` would have been
        validated with the wrong search **in silence** — a setting that
        does not do what it says (rule 7). Now the type is honoured, so
        a typo in it has to be caught here.
        """
        from ogr_core.project.settings import SearchMethod
        known = {m.value for m in SearchMethod}
        for path in _case_dirs():
            data = json.loads(
                (path / "esperado.json").read_text(encoding="utf-8"))
            tipo = (data.get("busqueda") or {}).get("tipo")
            if tipo is None:
                continue          # the model's own setting is used
            assert tipo in known, f"{path.name}: búsqueda '{tipo}'"


def _stated_surface(data: dict):
    """The slip surface a case STATES, or None when it asks for a search.

    v0.1.106. Every case in the folder until now validated a **search**, so
    the runner could only ever answer "does the program find the published
    minimum?". Some published problems state the surface instead and publish
    the factor of safety ON it — ACADS 2(b) tabulates its circle — and those
    answer the other question, "does the METHOD give the published number on
    a surface both programs agree about?".

    That second question is the one the folder could not ask, and it is the
    only one that separates the methods: on a critical circle that each
    method finds for itself, a difference between two methods mixes the
    method with the search.
    """
    spec = data.get("superficie")
    if not spec:
        return None
    from ogr_slip2d.surface import SlipCircle
    cx, cy = spec["centro"]
    return SlipCircle(centre_x=float(cx), centre_y=float(cy),
                      radius=float(spec["radio"]))


def _fos_on_stated_surface(project, data: dict, method_id: str, surface):
    """Evaluate one method on the stated surface, as the program would."""
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle

    n = int((data.get("busqueda") or {}).get("num_slices")
            or project.settings.methods.num_slices)
    method = build_method(project, method_id, n)
    assert method is not None, f"método no registrado: {method_id}"
    ev = GridSearch(method=method, num_slices=n, min_area=0.0)
    # A circle goes through evaluate_CIRCLE: it is the only path that walks
    # the disjoint masses a circle can cut and keeps the lowest (v0.1.84).
    from copy import copy as _copy
    s = _copy(surface)
    res = (ev.evaluate_circle(project, s) if isinstance(s, SlipCircle)
           else ev.evaluate_surface(project, s))
    return None if res is None else float(res.fos)


class TestCasesReproduceTheirReference:
    def test_all_runnable_cases(self):
        """Every case with a model must reproduce its expected values.

        If one fails, the fault is in the code or in the expected value —
        working out which is exactly the work a validation case exists to
        make possible. Do NOT adjust the case to make it pass.
        """
        from ogr_core.project import Project

        runnable = 0
        failures = []
        for path in _case_dirs():
            data = _load(path)
            if data is None:
                continue          # template or case still being written
            runnable += 1
            project = Project.load(path / "modelo.ogr")
            tol = float(data["tolerancia_relativa"])
            stated = _stated_surface(data)
            for mid, expected in (data.get("fos") or {}).items():
                if stated is not None:
                    got = _fos_on_stated_surface(project, data, mid, stated)
                    if got is None:
                        failures.append(f"{path.name}/{mid}: el método no "
                                        f"devolvió resultado sobre la "
                                        f"superficie del enunciado")
                        continue
                    error = abs(got - expected) / abs(expected)
                    if error > tol:
                        failures.append(
                            f"{path.name}/{mid}: esperado {expected:.4f}, "
                            f"obtenido {got:.4f} ({error * 100:.2f} %)")
                    continue
                search = _search_for(project, data, mid)
                result = search.run(project)
                if result.critical is None:
                    failures.append(f"{path.name}/{mid}: sin superficie "
                                    f"crítica")
                    continue
                got = result.critical.fos
                error = abs(got - expected) / abs(expected)
                if error > tol:
                    failures.append(
                        f"{path.name}/{mid}: esperado {expected:.4f}, "
                        f"obtenido {got:.4f} ({error * 100:.2f} %)")
        assert not failures, "\n".join(failures)

    def test_at_least_one_case_actually_runs(self):
        """v0.1.78 — the directory grew out of being empty, so an empty
        run is now a failure rather than a state.

        This assertion is not bookkeeping. A case with no ``modelo.ogr``
        is **skipped, not failed** (deliberately, so a half-written case
        can sit beside the real ones), and `.gitignore` excluded `*.ogr`
        wholesale — so the first real case was one `git add` away from
        being committed without its model, and every clone afterwards
        would have validated nothing while reporting all green.

        If this fails, look at `.gitignore` before looking at the case.
        """
        runnable = [p.name for p in _case_dirs() if _load(p) is not None]
        assert runnable, (
            "no runnable validation case: every case folder is missing its "
            "modelo.ogr or esperado.json — check that the models are "
            "actually tracked by git")

    def test_the_reference_case_in_the_suite_still_passes(self):
        """Until `validacion/casos/` is populated, the validated reference
        case lives in the test suite. This asserts it is still there, so
        the project is never left with zero validated cases."""
        assert (_ROOT / "tests"
                / "test_slide_validation_ej1.py").is_file()
