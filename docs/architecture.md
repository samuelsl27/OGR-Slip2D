# OGR Slip2D — Architecture Overview

## Layered design

```
┌──────────────────────────────────────────────────────┐
│                      ogr_gui                         │   ← Qt / PySide6
│   MainWindow · CanvasView · Dialogs · Dock · i18n    │
└───────┬──────────────────────────────────────────────┘
        │ (reads / mutates through Command pattern)
        ▼
┌──────────────────────────────────────────────────────┐
│                     ogr_core                         │   ← pure Python
│   geometry · materials · loads · support · project   │
└──────┬───────────────────────────┬───────────────────┘
       │                           │
       ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│   ogr_slip2d    │         │  ogr_core.fem   │
│  (LEM solvers)  │         │  (seepage FEM)  │
└─────────────────┘         └─────────────────┘
        ▲
        │
┌──────────────────────────────────────────────────────┐
│                      ogr_cli                         │   ← Typer
│   ogr-slip2d-cli compute / info / methods / ...      │
└──────────────────────────────────────────────────────┘
```

**Golden rules**

1. `ogr_core` has zero GUI / plotting dependencies.
2. Every solver lives in its own sibling package (`ogr_slip2d`, future
   ones), and depends on `ogr_core` only. The finite-element seepage solver
   is part of the shared core (`ogr_core.fem`, what was `ogr_fem2d` until
   spec 009), because OGR FEM2D uses it too.
3. The GUI and the CLI are two independent front-ends on top of the
   same core — *never* duplicate business logic.

Since v0.1.473 (spec 010) `ogr_core` is not in this repository: it is the
`ogr-core` package of OGR-Core, pinned to a tag in `pyproject.toml`, and its
code is changed only there. In the diagram, the `ogr_core` box and the
`ogr_core.fem` one are that package.

## File persistence (hybrid)

```
my_project.ogr    →  JSON model file (human-readable, diffable)
my_project.h5     →  HDF5 numerical results (dense, compressed)
```

- The JSON file is the source of truth and what the user commits to
  version control.
- The HDF5 file is rebuilt automatically by every `Compute` run.
- Stem matches: if you rename one, rename the other.

## Plugin registries (all three auto-discoverable)

| Registry              | Base class         | Decorator             |
|-----------------------|--------------------|-----------------------|
| Strength models       | `StrengthModel`    | `@register`           |
| LEM methods           | `LEMMethod`        | `@register_method`    |
| Support types         | `SupportType`      | `@register_support`   |

See [plugins.md](plugins.md) for step-by-step guides.

## Command pattern for undo/redo

Every user action that mutates the project is encapsulated in a
`Command` subclass. Stacks live in `CommandStack`:

```python
stack.do(project, AddBoundaryCommand(boundary))
stack.undo(project)
stack.redo(project)
```

Macro commands group several primitives into a single undo unit.

## Observer pattern for GUI reactivity

`Project.add_listener(callable)` lets the canvas refresh itself every
time the model changes. No need for explicit "repaint" calls from the
action handlers.

## Numerical pipeline

```
Project   → slice_surface(project, surface, N)
          → LEMMethod.compute_fos(project, surface, slices)
          → LEMResult
```

The slicer is the single geometric bridge. Every method with vertical
slices consumes the same `Slices` object and returns a uniform `LEMResult`.

A method with non-vertical slices (`NON_VERTICAL = True`; since v0.1.464,
Sarma's, `ogr_slip2d/methods/sarma.py`) adds one step. The searches and
`evaluate_surfaces` call `method.wedges_for(project, surface, slices)`.
That builds the wedges on the slicer's vertical slices
(`ogr_slip2d/sarma/wedges.py`, `build_wedges`) and hands the method a
`Wedges`: a subclass of `Slices` that keeps the vertical slices it was
built on. Plain vertical slices still work: a test or a script that
passes them gets them read as wedges with vertical faces. Either way the
method returns the same `LEMResult`.

## Coordinate system

Internally, OGR uses SI base units everywhere:
- length: metres (m)
- force:  kilonewtons (kN)
- stress: kilopascals (kPa)
- weight: kN/m³
- time:   seconds (for hydraulic transient)

The GUI converts to/from imperial / alternative units at the display
boundary only. This keeps the solver free of dimensional ambiguity.
