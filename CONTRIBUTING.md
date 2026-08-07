# Contributing to OGR Slip2D

Thanks for wanting to help. This document explains how the project is put
together and what a change needs to satisfy before it can be merged.

*OpenGeoRock* (or *OGR Suite*) is the umbrella over five planned programs;
**OGR Slip2D** is this one, and it is what this repository contains.

Licence: **AGPL-3.0-or-later**. Contributions are accepted under the terms
in [`CLA.md`](CLA.md) — read it before your first pull request; it takes
two minutes and it exists so the free version can never be taken away.

---

## Getting set up

```bash
git clone https://github.com/samuelsl27/OGR-Slip2D.git
cd OGR-Slip2D
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Run the whole suite:

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py
```

`QT_QPA_PLATFORM=offscreen` is needed because the GUI tests build real
widgets; they simply never reach a display. The runner exits non-zero if
anything fails, which is what CI checks.

---

## Layout

| Package | Contents |
|---|---|
| `ogr_core` | Geometry, materials, loads, supports, project model, hydraulics, statistics |
| `ogr_slip2d` | Limit-equilibrium engine: 7 methods, 6 search algorithms, slicer, post-processing, back analysis |
| `ogr_fem2d` | Finite-element seepage: mesh generation and solvers |
| `ogr_gui` | PySide6 interface: canvas, dialogs, interpret windows, i18n |
| `ogr_cli` | Command-line interface |
| `ogr_data` | Placeholder for the shared materials database (planned for v0.2.0) |
| `tests` | The test suite, one file per feature area |
| `validacion` | Validation cases: model, expected values and their source |
| `spec` | Specifications: project constitution and per-feature specs |
| `docs` | Plans, audits and the changelog |

---

## What a change must satisfy

These are not bureaucracy; each one exists because its absence caused a
real problem in this project's history.

### 1. Numerical work is validated against something external

A new analysis method, solver or formula needs a **reference value** — a
published case, a closed-form solution, or an analytic property — not a
snapshot of what the code currently prints. Snapshot tests lock in bugs.

Examples of what counts:

- the reference factor of safety for a known case (the LEM methods are all
  validated this way, to better than 0.7 %);
- a closed-form solution (the seepage solver is checked against the erfc
  step response and against harmonic/arithmetic layer averages);
- an analytic identity (the back analysis is checked by the fact that
  active and passive support force must coincide exactly at a target
  factor of 1.0);
- asymptotic consistency with an already-validated path (the transient
  solver at large time must reproduce the steady-state solver).

### 2. Every user-visible string goes through `tr()`

```python
from ogr_gui.i18n import tr
label = QLabel(tr("Number of slices:"))
```

and gets a Spanish entry in `ogr_gui/i18n/__init__.py`. There is a test
that fails if a key is wrapped without a translation, and a budget test
that fails if the number of *unwrapped* strings grows. Terminology matters
more than literal translation: use the standard Spanish geotechnical term
(*dovela*, *nivel freático*, *grieta de tracción*).

### 3. Every new action is reachable from a menu

A whole module was once implemented, tested and shipped **invisible**
because its actions were registered but never added to the menu bar. There
is now a test that walks the real menu bar and fails on any unreachable
action. If your action is deliberately toolbar-only, add it to that test's
allow-list with a reason.

### 4. Every source file carries the licence header

```python
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
```

Checked by a test, and separately in CI.

### 5. Tests must not leak state

Anything global — the active language, the current units, a module-level
cache — must be restored. A test that left the language in Spanish once
made unrelated menu tests fail only when the whole suite ran, which is the
worst kind of failure to diagnose.

### 6. Anomalies are reported before they are corrected

If you find behaviour that looks wrong, **say so and show the evidence**
before changing it. Two of this project's most instructive findings came
from that discipline: an m-alpha check that would have rejected the
reference-validated critical circle (so it must stay opt-in), and a
Simulated Annealing bootstrap that depended on luck (200 rejections for
unlucky seeds). Both would have been papered over by a quick fix.

### 7. No setting may do nothing

A configurable control that does not change the result is **worse** than
not having it, because the user believes the analysis honours it. The
design-standard partial factors were configurable but unapplied for two
releases (v0.1.52 → v0.1.57): the dialog wrote the values, the engine
never read them, and nothing failed. If you add an option, add the test
that proves it **moves the number**.

---

## Commits and branches

- Branch from `main` as `dev/short-description`.
- Sign off your commits: `git commit -s -m "..."` (Developer Certificate
  of Origin).
- Write commit subjects that say what changed and why, not "fix stuff".
- Keep unrelated changes in separate commits; mechanical reformatting
  should never travel with a behavioural change.

## Versioning

Semantic-ish: `0.MINOR.PATCH` while pre-1.0. Each release bumps the
version in `pyproject.toml`, `ogr_gui/main_window.py`,
`ogr_slip2d/__init__.py` and `ogr_fem2d/__init__.py`, and adds a changelog
entry recording **what was found**, not only what was written — including
wrong turns, because those are the parts worth remembering.

## Style

- Python ≥ 3.11, type hints where they clarify.
- Comments explain *why*, not *what*. A comment stating a non-obvious
  reason (a sign convention, a numerical guard, a licence constraint) is
  worth more than ten describing syntax.
- Docstrings on public functions, with the reference for any formula.

## Reporting a problem

Use the issue templates. For anything numerical, include the model and
both the value obtained and the value expected — a factor of safety
without a reference is not actionable.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
