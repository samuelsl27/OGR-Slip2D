# Quick Start — OGR Slip2D

## 1. Install

```bash
git clone https://github.com/samuelsl27/OGR-Slip2D.git
cd OGR-Slip2D
python -m venv .venv
source .venv/bin/activate           # Linux/macOS
# .venv\Scripts\activate            # Windows
pip install -e .
```

Core runtime dependencies (auto-installed): `numpy`, `scipy`, `shapely`,
`h5py`, `ezdxf`, `PySide6`, `qtawesome`, `typer`, `rich`, `pydantic`.

## 2. Launch the GUI

```bash
ogr-slip2d
```

A demo slope (20 m high, c=10 kPa, φ=25°, γ=19 kN/m³) is loaded
automatically so you can try the tools immediately.

### First-time workflow

1. **Analysis → Project Settings...** (Ctrl+J) — pick units, active LEM
   methods, number of slices, surface-search parameters.
2. **Properties → Define Materials...** — edit the two demo materials
   or add more. Each row shows live colour swatches; hovering on a
   region of the canvas shows that material's full property tooltip.
3. **Analysis → Compute** (Ctrl+T) — runs the selected LEM method with
   a grid search. A progress dialog appears.
4. **Interpret** tab (bottom dock) — top-50 critical surfaces by
   ascending FoS; the critical surface is highlighted in red on the
   canvas.

## 3. Use the CLI

```bash
# Create a demo project
ogr-slip2d-cli new-demo demo.ogr

# Inspect it
ogr-slip2d-cli info demo.ogr

# Run Bishop Simplified with a 10×10 grid search
ogr-slip2d-cli compute demo.ogr --method bishop --nx 10 --ny 10 \
                                --slices 30 --output demo.h5

# List available methods and strength models
ogr-slip2d-cli methods
ogr-slip2d-cli strength-models
```

## 4. Use the Python API

```python
from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material, MohrCoulomb
from ogr_core.project import Project
from ogr_slip2d import BishopSimplified, GridSearch

# Build a slope
p = Project("my slope")
ext = Polyline(
    vertices=[Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
              Vertex(35, 15), Vertex(25, 25), Vertex(0, 25)],
    closed=True,
)
ext.ensure_ccw()
p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
p.add_material(Material(
    name="silty clay",
    strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
    unit_weight=19.0,
))

# Run Bishop Simplified
search = GridSearch(
    method=BishopSimplified(),
    grid_nx=8, grid_ny=8, radius_increment=1.5, min_radius=3.0,
    num_slices=30, min_area=1.0,
)
result = search.run(p)

print(f"Critical FoS: {result.critical.fos:.3f}")
print(f"Centre: ({result.critical.surface.centre_x:.1f}, "
      f"{result.critical.surface.centre_y:.1f})")
print(f"Radius: {result.critical.surface.radius:.1f} m")
```

## 5. Keyboard shortcuts

| Shortcut  | Action                    |
|-----------|---------------------------|
| Ctrl+N    | New project               |
| Ctrl+O    | Open project              |
| Ctrl+S    | Save                      |
| Ctrl+Z    | Undo                      |
| Ctrl+Y    | Redo                      |
| Ctrl+J    | Project settings          |
| Ctrl+T    | Compute                   |
| Ctrl+I    | Info viewer               |
| F2        | Zoom all                  |
| F4 / F5   | Zoom out / in             |
| F7        | Toggle grid               |
| Ctrl+1…6  | Add boundary (each type)  |
| F1        | Help                      |

## 6. Language

**File → Preferences... → Language** — pick English or Español. More
languages can be added by calling
`ogr_gui.i18n.add_translations(code, dict)` from a plugin.

---

For advanced topics:
- [architecture.md](architecture.md) — package structure and design
- [plugins.md](plugins.md) — adding new materials / methods / supports
- [roadmap.md](roadmap.md) — upcoming features
