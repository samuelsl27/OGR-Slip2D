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
│   ogr_slip2d    │         │    ogr_fem2d    │
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
2. Every solver lives in its own sibling package (`ogr_slip2d`,
   `ogr_fem2d`, future ones). They depend on `ogr_core` only.
3. The GUI and the CLI are two independent front-ends on top of the
   same core — *never* duplicate business logic.

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

The slicer is the single geometric bridge. Every LEM method consumes
the same `Slices` object and returns a uniform `LEMResult`.

## Coordinate system

Internally, OGR uses SI base units everywhere:
- length: metres (m)
- force:  kilonewtons (kN)
- stress: kilopascals (kPa)
- weight: kN/m³
- time:   seconds (for hydraulic transient)

The GUI converts to/from imperial / alternative units at the display
boundary only. This keeps the solver free of dimensional ambiguity.
