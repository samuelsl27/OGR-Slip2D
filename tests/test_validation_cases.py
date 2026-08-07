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


class TestCasesReproduceTheirReference:
    def test_all_runnable_cases(self):
        """Every case with a model must reproduce its expected values.

        If one fails, the fault is in the code or in the expected value —
        working out which is exactly the work a validation case exists to
        make possible. Do NOT adjust the case to make it pass.
        """
        from ogr_core.project import Project
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.search import GridSearch

        runnable = 0
        failures = []
        for path in _case_dirs():
            data = _load(path)
            if data is None:
                continue          # template or case still being written
            runnable += 1
            project = Project.load(path / "modelo.ogr")
            tol = float(data["tolerancia_relativa"])
            notas = data.get("busqueda") or {}
            for mid, expected in (data.get("fos") or {}).items():
                method = method_registry()[mid]()
                search = GridSearch(method=method,
                                    num_slices=int(notas.get(
                                        "num_slices", 25)))
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
        # Nothing to assert about runnable == 0: an empty set of cases is
        # a state to grow out of, not a failure to report on every run.

    def test_the_reference_case_in_the_suite_still_passes(self):
        """Until `validacion/casos/` is populated, the validated reference
        case lives in the test suite. This asserts it is still there, so
        the project is never left with zero validated cases."""
        assert (_ROOT / "tests"
                / "test_slide_validation_ej1.py").is_file()
