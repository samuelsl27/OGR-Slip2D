<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

<div align="center">

# OGR Slip2D

### part of the **OpenGeoRock** suite

**Open-source geotechnical software, built in the open.**

Slope stability, groundwater flow and rock mechanics — in Python, readable,
tested and free.

[![tests](https://img.shields.io/badge/tests-1724%20passing-brightgreen)](#tests)
[![licence](https://img.shields.io/badge/licence-AGPL--3.0--or--later-blue)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](#installation)
[![status](https://img.shields.io/badge/status-active%20development-orange)](#roadmap)

**English** · [Español](README.es.md)

[opengeorock.org](https://opengeorock.org) ·
[Contributing](CONTRIBUTING.md) ·
[Rules for AI agents](AGENTS.md) ·
[Licence](#licence)

<img src="docs/images/hero-analysis.png" alt="Grid search over a two-layer slope: the critical surface in red among the candidate surfaces in green" width="820">

</div>

---

## Why it exists

Almost every program a geotechnical engineer depends on is closed, expensive
and opaque — a black box at the centre of decisions about dams, slopes,
tunnels and foundations. When a factor of safety comes out at 1.32, there is
no way to read *why*.

OpenGeoRock rebuilds those tools in the open: a computation core in plain
Python, a modern desktop interface, and a test suite anyone can inspect.
**Every method ships with the reference case it was validated against**, so
results can be checked instead of believed.

---

## What OGR Slip2D does today

![The modelling window: geometry, toolbar, results table and embedded Python terminal](docs/images/01-modeler.png)

### Limit equilibrium

Seven methods, each validated against a reference case:

| Method | Equilibrium satisfied | Validation error |
|---|---|---|
| Ordinary / Fellenius | moment | +0.06 % |
| Bishop simplified | moment | +0.02 % |
| Janbu simplified | force | +0.13 % |
| Janbu corrected | force | +0.10 % |
| Spencer | force + moment | +0.64 % |
| GLE / Morgenstern-Price | force + moment | +0.53 % |
| Lowe-Karafiath | force | +0.09 % |

Six search algorithms — grid, slope, auto-refine, block, path and simulated
annealing — over **circular and non-circular** surfaces, with composite
surfaces, slope limits and random-walk optimisation.

**Focused search** by window, line, point or **tangent**, which filters
circles *before* evaluating them: on the reference case, a tangent to a weak
layer leaves 17 evaluations out of 206.

Eighteen strength models (Mohr-Coulomb, undrained, Hoek-Brown and generalised
Hoek-Brown, power curve, hyperbolic, Barton-Bandis, linear anisotropic,
shear-normal and generalised anisotropic functions, SHANSEP, vertical stress
ratio…), seven support types, distributed and line loads, pseudo-static
seismic loading and tension cracks.

<img src="docs/images/03-materials.png" alt="Material dialog: unit weight, strength type and pore pressure" width="620">

### Finite-element groundwater

A full seepage engine, not a lookup table:

- **T3 meshing** over the material regions, conforming across interfaces by
  construction.
- **Saturated steady state** with an anisotropic conductivity tensor per
  material.
- **Unsaturated flow** with six permeability functions — simple,
  Brooks-Corey, Fredlund-Xing, Gardner, van Genuchten and user-defined —
  solved by Picard iteration with relaxation.
- **Phreatic surface and seepage faces** by nodal switching.
- **Transient analysis** in stages, using the mixed form of the Richards
  equation, modified Picard iteration and a **factor of safety per stage**:
  a rapid drawdown becomes a stability history.
- **Coupling to stability**: pressures interpolated at the slice bases, with
  suction handled through the extended Mohr-Coulomb envelope.

### Probabilistic and sensitivity analysis

Seven distributions with **relative** minimum and maximum truncation, Monte
Carlo and **Latin hypercube** sampling, cohesion–friction correlation, Global
Minimum and Overall Slope analyses, probability of failure, reliability
index, critical probabilistic surface, convergence plots and sensitivity
sweeps ranked by influence.

### Interpreting results

![The interpretation window: critical surface, surfaces ranked by factor of safety and per-slice data](docs/images/02-interpret.png)

### And also

**Eurocode 7** partial factors (DA1-C1, DA1-C2, DA2, DA3), support-force back
analysis, a Hoek-Brown parameter calculator, **DXF** import and export with
geometry cleanup, an annotation layer, PDF reports, a **Spanish / English**
interface and a command-line interface.

---

## Verified behaviour, not just green tests

The suite is validated against **external references and analytic
identities**, never against snapshots of its own output — a snapshot locks in
whatever bug may be there.

| What | Check | Result |
|---|---|---|
| LEM methods | reference factor of safety | all within 0.7 % |
| Confined seepage | closed-form Darcy solution | 0.000 % |
| Layered media | harmonic and arithmetic averages | 0.000 % |
| Anisotropy | patch test with Kxy ≠ 0 | machine precision |
| Transient | erfc step response | 0.11 % |
| Transient at long time | must reproduce steady state | 0.0000 m |
| FE mesh | area equals the region's area | exact at every refinement |
| Back analysis | active = passive at FS = 1 | exact identity |
| Hoek-Brown | GSI = 100, D = 0 → mb = mi, s = 1, a = 0.5 | exact |
| DXF round trip | identical area, vertices on the originals | < 1e-6 |

Rapid drawdown reproduces the classical result without being told to: the
factor of safety is lowest right after the level drops and recovers as the
pressures dissipate.

---

## Installation

Python **3.11 or newer**.

```bash
git clone https://github.com/samuelsl27/OGR-Slip2D.git
cd OGR-Slip2D
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

Open the application:

```bash
ogr-slip2d          # or:  python -m ogr_gui
```

Or use it from Python:

```python
from ogr_core.project import Project
from ogr_slip2d import BishopSimplified, GridSearch

project = Project.load("my_slope.ogr")
search = GridSearch(method=BishopSimplified(), num_slices=25)
result = search.run(project)
print(f"critical FoS = {result.critical.fos:.4f}")
```

---

## Tests

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py
```

`QT_QPA_PLATFORM=offscreen` is needed because the GUI tests build real Qt
widgets; they simply never reach a display. Note that the project uses its
own runner in `tests/_runner.py` — **pytest is not required**, and the test
modules cannot be imported outside the runner.

To work on one area, run only that part of the suite:

```bash
python tests/_runner.py transient          # files whose name contains it
python tests/_runner.py -k erfc            # tests whose name contains it
python tests/_runner.py --list transient   # show the selection, run nothing
```

A pattern that matches nothing exits 2 rather than announcing an empty
success, and a filtered run prints a `FILTERED RUN` warning around its
totals — it is not evidence for a release.

About **43,600 lines** of implementation and **23,300 of tests**, **1724 of
them passing**, with no known failures. The full suite takes between 5 and
7½ minutes; the same code, unchanged, has taken 5:55, 6:19, 6:41 and 7:22 on
the same machine.

---

## Layout

| Package | Contents |
|---|---|
| `ogr_core/` | Geometry, materials, loads, supports, project model, hydraulics, statistics, annotations, DXF |
| `ogr_slip2d/` | Limit-equilibrium engine: methods, searches, slicer, focus, optimisation, back analysis |
| `ogr_fem2d/` | Finite elements: meshing and seepage solvers |
| `ogr_gui/` | PySide6 interface: canvas, dialogs, interpret windows, translations |
| `ogr_cli/` | Command-line interface |
| `ogr_data/` | Placeholder for the shared materials database (planned for v0.2.0) |
| `validacion/` | Validation cases: model, expected values and their source |
| `spec/` | Specifications (project constitution and features) |
| `docs/` | Plans, audits and the changelog |
| `tests/` | One file per feature area |

---

## Roadmap

OGR Slip2D is the first of five programs.

| # | Program | Scope | Status |
|---|---|---|---|
| 01 | **OGR Slip2D** | 2D stability, FE seepage, probabilistic analysis | **in development** |
| 02 | OGR Data | Property database, correlations and charts | planned |
| 03 | OGR FEM2D | 2D elastoplastic finite elements | planned |
| 04 | OGR Slip3D | 3D limit-equilibrium surfaces | planned |
| 05 | OGR FEM3D | 3D finite elements with coupled flow | planned |

Next up in Slip2D: installers, more validation cases and the materials
database.

---

## Contributing

Any help is welcome: code, validation against real cases, bug reports, or
simply running the program on an actual project and reporting what broke.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first: it explains the seven
conditions a change must satisfy and **why each one exists** — every one of
them traces back to a real problem in this project's history. The first is
the most important: numerical work is validated against something external,
never against a snapshot of the current output.

**The most valuable thing you can contribute is a validation case.** If you
have a slope whose factor of safety you know from a publication, another
program or a hand calculation, open an issue with the *Validation case*
template. That is how confidence in a computation engine gets built.

### If you develop with AI agents

The repository includes [`AGENTS.md`](AGENTS.md) with the full contract:
stack, commands, the seven rules, the workflow and an explicit list of what
not to do. There are also commands and *skills* in `.claude/`, and
specification templates in `spec/`.

AI-assisted code is accepted **by the same standard as everything else**: if
you cannot explain why a line is there, do not submit it. Responsibility for
what gets merged belongs to whoever signs it.

Contributions are accepted under the terms of [`CLA.md`](CLA.md).

---

## Licence

**GNU Affero General Public License v3.0 or later** (AGPL-3.0-or-later). The
full text is in [`LICENSE`](LICENSE).

In practice:

- You may use OGR Suite freely, **including for professional engineering
  work**, and bill that work without paying or publishing anything. Running a
  program is not a restricted activity.
- If you **modify** it and let others use your version **remotely over a
  network** (a web service or SaaS), you must offer them the source of your
  version. Charging for that service is allowed; keeping it closed is not.
- **There is no warranty of any kind.** Results must be checked against
  independent calculations before anything is based on them. A project is
  signed by a person, not by a program.

Every file carries its SPDX identifier, and a test fails if any is missing.

> **Note on the licence change.** Until v0.1.42 the project was GPL-3.0. It
> moved to AGPL in v0.1.43 so that a modified version offered as a network
> service has to publish its source — something the GPL does not require,
> because serving a program is not distributing it. Earlier changelogs still
> say GPL-3.0 on purpose: they record what was true at the time.

---

## Team

**Samuel Sáez López** — author, copyright holder and maintainer. Mining
engineer and PhD candidate at the **Universidad Politécnica de Cartagena
(UPCT)**, in the *Technology and Modelling in Civil, Mining and Environmental
Engineering* programme. His doctoral research on slope stability and rock
mechanics feeds directly into the numerical methods published here.

**Prof. Emilio Trigueros Tornero** — academic supervisor of the doctoral
research at UPCT and collaborator in the scientific direction of the project,
contributing judgement in rock mechanics and research methodology.

Collaborators: **Universidad Politécnica de Cartagena** (academic framework)
and **IMGA S.L.P.** — Ingeniería Minera, Geológica y Ambiental (professional
collaborator).

### Authorship

So that the split of contributions leaves no room for doubt: Samuel Sáez
López is the **author and copyright holder** of the source code; Emilio
Trigueros Tornero contributes **academic supervision and scientific
collaboration**.

---

## Citing

If OGR Suite contributes to published work:

```bibtex
@software{ogr_suite,
  author  = {Sáez López, Samuel},
  title   = {{OGR Suite (OpenGeoRock)}: open-source geotechnical analysis
             of slope stability and groundwater flow},
  year    = {2026},
  url     = {https://opengeorock.org},
  note    = {Universidad Politécnica de Cartagena. AGPL-3.0-or-later}
}
```

---

<div align="center">

**[opengeorock.org](https://opengeorock.org)**

© 2026 Samuel Sáez López — Universidad Politécnica de Cartagena ·
AGPL-3.0-or-later

</div>
