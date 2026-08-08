# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
OGR Slip2D — command-line interface (Typer).

Commands:

    ogr-slip2d-cli info <project.ogr>
    ogr-slip2d-cli compute <project.ogr> [--method ...] [--slices N] [--output file.h5]
    ogr-slip2d-cli methods
    ogr-slip2d-cli strength-models
    ogr-slip2d-cli new-demo <output.ogr>

The CLI uses the same numerical core as the GUI — guaranteed identical
behaviour between interactive and automated runs.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import REGISTRY, Material, MohrCoulomb, PorePressureType
from ogr_core.project import Project, save_results
from ogr_slip2d import (
    BishopSimplified,
    GridSearch,
    JanbuCorrected,
    JanbuSimplified,
    OrdinaryFellenius,
    SlopeSearch,
    method_registry,
)

app = typer.Typer(
    help="OGR Slip2D — limit-equilibrium slope stability analysis. "
         "OpenGeoRock Suite. © Samuel Sáez López (UPCT).",
    no_args_is_help=True,
)
console = Console()


METHOD_MAP = {
    "bishop": BishopSimplified,
    "bishop_simplified": BishopSimplified,
    "janbu": JanbuSimplified,
    "janbu_simplified": JanbuSimplified,
    "janbu_corrected": JanbuCorrected,
    "ordinary": OrdinaryFellenius,
    "fellenius": OrdinaryFellenius,
    "ordinary_fellenius": OrdinaryFellenius,
}


# ======================================================================
@app.command()
def info(
    project: Path = typer.Argument(..., help="Path to the .ogr project file"),
):
    """Show a summary of the project."""
    if not project.exists():
        console.print(f"[red]File not found:[/red] {project}")
        raise typer.Exit(1)
    p = Project.load(project)

    tbl = Table(title=f"OGR Project — {p.name}")
    tbl.add_column("Field", style="cyan", no_wrap=True)
    tbl.add_column("Value", style="white")
    tbl.add_row("Path", str(project))
    tbl.add_row("Author", p.settings.summary.author)
    tbl.add_row("Company", p.settings.summary.company)
    tbl.add_row("Boundaries", str(len(p.boundaries)))
    tbl.add_row("Materials", str(len(p.materials)))
    tbl.add_row("Supports", str(len(p.supports)))
    tbl.add_row("Distributed loads", str(len(p.distributed_loads)))
    tbl.add_row("Line loads", str(len(p.line_loads)))
    tbl.add_row("Seismic", str(p.seismic.enabled))
    tbl.add_row("Bounding box", str(p.bounding_box()))
    console.print(tbl)

    if p.materials:
        mtbl = Table(title="Materials")
        mtbl.add_column("Name", style="cyan")
        mtbl.add_column("Strength model")
        mtbl.add_column("γ (kN/m³)")
        mtbl.add_column("γsat")
        mtbl.add_column("Color")
        for m in p.materials:
            mtbl.add_row(
                m.name,
                type(m.strength).DISPLAY_NAME,
                f"{m.unit_weight:g}",
                # v0.1.60 — γsat only applies if the material opts into it
                f"{m.sat_unit_weight:g}" if m.use_sat_unit_weight else "—",
                f"[on {m.color}]   [/on {m.color}]",
            )
        console.print(mtbl)


# ======================================================================
@app.command()
def compute(
    project: Path = typer.Argument(..., help="Path to the .ogr project file"),
    method: str = typer.Option("bishop", help="LEM method: bishop, janbu, janbu_corrected, ordinary"),
    slices: int = typer.Option(30, help="Number of slices per surface"),
    nx: int = typer.Option(8, help="Grid divisions along X"),
    ny: int = typer.Option(8, help="Grid divisions along Y"),
    dr: float = typer.Option(1.5, help="Radius increment [m]"),
    search: str = typer.Option("grid", help="Search strategy: grid | slope"),
    samples: int = typer.Option(1000, help="Number of surfaces (slope search)"),
    output: Path = typer.Option(None, help="HDF5 results output path"),
):
    """Run a full surface-search and report the critical FoS."""
    if not project.exists():
        console.print(f"[red]File not found:[/red] {project}")
        raise typer.Exit(1)
    p = Project.load(project)

    mcls = METHOD_MAP.get(method.lower())
    if mcls is None:
        console.print(f"[red]Unknown method:[/red] {method}. "
                      f"Available: {sorted(set(METHOD_MAP))}")
        raise typer.Exit(2)
    method_obj = mcls()

    with console.status(f"[bold green]Running {mcls.DISPLAY_NAME}..."):
        if search == "grid":
            engine = GridSearch(method=method_obj, grid_nx=nx, grid_ny=ny,
                                radius_increment=dr, min_radius=3.0,
                                num_slices=slices, min_area=1.0)
        else:
            engine = SlopeSearch(method=method_obj, num_surfaces=samples,
                                 num_slices=slices, min_area=1.0)
        result = engine.run(p)

    tbl = Table(title=f"{mcls.DISPLAY_NAME} — {search} search")
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value")
    tbl.add_row("Surfaces evaluated", str(len(result.evaluations)))
    tbl.add_row("Valid", str(result.valid_count))
    tbl.add_row("Invalid", str(result.invalid_count))

    critical = result.critical
    if critical is not None:
        sd = critical.surface.to_dict()
        tbl.add_row("Critical FoS", f"[bold yellow]{critical.fos:.4f}[/bold yellow]")
        tbl.add_row("Converged", str(critical.converged))
        tbl.add_row("Iterations", str(critical.iterations))
        if sd.get("type") == "circle":
            tbl.add_row("Centre (x, y)", f"({sd['centre_x']:.3f}, {sd['centre_y']:.3f})")
            tbl.add_row("Radius", f"{sd['radius']:.3f} m")
    else:
        tbl.add_row("Critical FoS", "[red]no valid surface[/red]")
    console.print(tbl)

    out = output or project.with_suffix(".h5")
    save_results(out, result, project_id=p.id)
    console.print(f"[green]Results saved:[/green] {out}")


# ======================================================================
@app.command()
def methods():
    """List all available LEM methods."""
    tbl = Table(title="Registered LEM methods")
    tbl.add_column("ID", style="cyan")
    tbl.add_column("Display Name")
    tbl.add_column("Force eq.")
    tbl.add_column("Moment eq.")
    for mid, cls in method_registry().items():
        tbl.add_row(
            mid, cls.DISPLAY_NAME,
            "✓" if cls.SATISFIES_FORCE else "—",
            "✓" if cls.SATISFIES_MOMENT else "—",
        )
    console.print(tbl)


# ======================================================================
@app.command("strength-models")
def strength_models():
    """List all registered constitutive (strength) models."""
    tbl = Table(title="Registered strength models")
    tbl.add_column("ID", style="cyan")
    tbl.add_column("Display Name")
    tbl.add_column("Parameters")
    for mid, cls in REGISTRY.all().items():
        params = ", ".join(f"{k}({u})" for k, (_, u, _) in cls.PARAMETERS.items())
        tbl.add_row(mid, cls.DISPLAY_NAME, params or "—")
    console.print(tbl)


# ======================================================================
@app.command("new-demo")
def new_demo(output: Path = typer.Argument(..., help="Destination .ogr file")):
    """Create a small homogeneous-slope demo project and save it."""
    p = Project("Demo slope")
    ext = Polyline(
        vertices=[
            Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
            Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
        ],
        closed=True,
    )
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(
        name="Silty clay",
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
        unit_weight=19.0, sat_unit_weight=20.5,
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    p.add_material(mat)
    wt = Boundary(
        polyline=Polyline(vertices=[Vertex(0, 8), Vertex(50, 8)]),
        btype=BoundaryType.WATER_TABLE,
    )
    p.add_boundary(wt)
    mat.water_surface_id = wt.id

    if not str(output).endswith(".ogr"):
        output = output.with_suffix(".ogr")
    p.save(output)
    console.print(f"[green]Demo project saved:[/green] {output}")


if __name__ == "__main__":
    app()
