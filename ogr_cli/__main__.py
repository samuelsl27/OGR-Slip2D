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

The CLI runs the analysis the PROJECT describes, through the same
``ogr_slip2d.analysis_runner`` the graphical interface uses. Command-line
options override individual project settings when given, and change
nothing when omitted.

v0.1.77 — that sentence used to read "guaranteed identical behaviour
between interactive and automated runs", and it was false. ``compute``
read nothing at all from ``project.settings``: it built its own search
out of command-line defaults, so a terminal run silently skipped rapid
drawdown, the design-standard partial factors, four of the six search
strategies and every convergence setting. See CHANGELOG_v0.1.77.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import REGISTRY, Material, MohrCoulomb, PorePressureType
from ogr_core.project import Project, save_results
from ogr_slip2d import method_registry
from ogr_slip2d.analysis_runner import check_analysis_settings, run_analysis

app = typer.Typer(
    help="OGR Slip2D — limit-equilibrium slope stability analysis. "
         "OpenGeoRock Suite. © Samuel Sáez López (UPCT).",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _main() -> None:
    """Widen the output encoding before any command prints.

    v0.1.77 — ``ogr-slip2d-cli methods`` crashed outright on a Windows
    console: the ✓ and — in its table are not encodable in cp1252, which
    is what Python picks there, so printing the table raised a
    UnicodeEncodeError and the command produced a traceback instead of a
    list. ``tests/_runner.py`` had already met and documented the same
    trap; this is the same remedy, applied once for every command.
    """
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # non-reconfigurable stream
            pass


# Short spellings accepted by ``--method`` on top of the registered ids.
# The set of METHODS is not listed here: it comes from
# ``method_registry()``. A hand-written table is what let ``methods``
# advertise seven methods while ``compute`` accepted four of them.
METHOD_ALIASES = {
    "bishop": "bishop_simplified",
    "janbu": "janbu_simplified",
    "ordinary": "ordinary_fellenius",
    "fellenius": "ordinary_fellenius",
    "gle": "gle_morgenstern_price",
    "morgenstern_price": "gle_morgenstern_price",
    "lowe": "lowe_karafiath",
    "corps1": "corps_engineers_1",
    "corps2": "corps_engineers_2",
    "coe1": "corps_engineers_1",
    "coe2": "corps_engineers_2",
    "modified_swedish": "corps_engineers_1",
}


def _resolve_method(name: str) -> Optional[str]:
    """The registered method id ``name`` refers to, or None."""
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    key = METHOD_ALIASES.get(key, key)
    return key if key in method_registry() else None


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
    method: Optional[str] = typer.Option(
        None, help="LEM method id or alias. Default: the methods enabled "
                   "in the project. `methods` lists them all."),
    slices: Optional[int] = typer.Option(
        None, help="Number of slices per surface [project setting]"),
    nx: Optional[int] = typer.Option(
        None, help="Grid divisions along X [project setting]"),
    ny: Optional[int] = typer.Option(
        None, help="Grid divisions along Y [project setting]"),
    dr: Optional[float] = typer.Option(
        None, help="Radius increment, as a NUMBER OF INTERVALS "
                   "[project setting]"),
    search: Optional[str] = typer.Option(
        None, help="Search strategy: grid | slope | auto_refine | block | "
                   "path | simulated_annealing [project setting]"),
    samples: Optional[int] = typer.Option(
        None, help="Number of surfaces, random searches [project setting]"),
    output: Optional[Path] = typer.Option(
        None, help="HDF5 results output path"),
):
    """Run the analysis the project describes and report the critical FoS.

    Every option defaults to the value stored in the project, so a run
    with no options reproduces what the graphical interface would do.
    Passing an option overrides that one setting and nothing else.
    """
    if not project.exists():
        console.print(f"[red]File not found:[/red] {project}")
        raise typer.Exit(1)
    p = Project.load(project)

    # v0.1.77 — overrides are written onto the loaded project, which is an
    # in-memory copy; nothing is saved back, so the user's file is never
    # modified by a calculation.
    s = p.settings
    if slices is not None:
        s.methods.num_slices = int(slices)
    if search is not None:
        s.search.search_method = search.strip().lower()
    if nx is not None:
        s.search.grid_nx = int(nx)
    if ny is not None:
        s.search.grid_ny = int(ny)
    if dr is not None:
        s.search.radius_increment = dr
    if samples is not None:
        s.search.num_surfaces = int(samples)
        s.search.block_num_surfaces = int(samples)
        s.search.path_num_surfaces = int(samples)

    if method is not None:
        mid = _resolve_method(method)
        if mid is None:
            console.print(f"[red]Unknown method:[/red] {method}. "
                          f"Available: {sorted(method_registry())}")
            raise typer.Exit(2)
        method_ids = [mid]
    else:
        method_ids = list(s.methods.enabled_methods) or ["bishop_simplified"]

    # An analysis that cannot honour the settings it was given must say
    # so. Reporting a plausible number computed from silently dropped
    # settings is the failure mode this whole command was rewritten for.
    problems = check_analysis_settings(p)
    if problems:
        for why in problems:
            console.print(f"[red]Cannot compute:[/red] {why}")
        raise typer.Exit(3)

    gw = s.groundwater
    banner = s.search.search_method
    if gw.rapid_drawdown:
        banner += f", rapid drawdown ({gw.rapid_drawdown_method})"
    with console.status(f"[bold green]Running {banner}..."):
        outcome = run_analysis(p, method_ids)

    for note in outcome.warnings:
        console.print(f"[yellow]Note:[/yellow] {note}")

    # With a design standard active the result is not a factor of safety:
    # the partial factors are applied to the INPUTS, so what comes out is
    # an over-design factor, and it must be greater than 1.
    factored = bool(getattr(outcome.factor_report, "applied", False))
    label = "Over-design factor" if factored else "Critical FoS"
    # v0.1.127 - and with a seismic mode on it is neither. The reference
    # says of its own Ky analysis that "the output will be in terms of Ky
    # values rather than Factor of Safety", and the surface reported is
    # the one with the LOWEST Ky, which is not the one with the lowest
    # factor. Printing "Critical FoS" over that column would be the
    # terminal contradicting the analysis it just ran - the same fault
    # the Interpret window had, fixed in the same version.
    first = next(iter(outcome.results.values()), None)
    seismic_objective = getattr(first, "objective", "fos") == "ky"
    newmark_on = bool(
        first is not None and first.critical is not None
        and "newmark_displacement" in (first.critical.details or {}))
    if seismic_objective and not factored:
        label = "Newmark disp. (cm)" if newmark_on else "Critical Ky"
    if factored:
        console.print(f"[cyan]Design standard applied:[/cyan] "
                      f"{outcome.factor_report.summary()} — the reported "
                      f"value is an over-design factor, not a factor of "
                      f"safety, and must exceed 1")

    tbl = Table(title=f"{banner} — {len(outcome.results)} method(s)")
    tbl.add_column("Method", style="cyan")
    tbl.add_column(label)
    tbl.add_column("Valid")
    tbl.add_column("Invalid")
    tbl.add_column("Converged")
    for mid, result in outcome.results.items():
        critical = result.critical
        detail = (critical.details or {}) if critical is not None else {}
        if critical is None:
            shown = "[red]no valid surface[/red]"
        elif newmark_on:
            shown = ("[bold yellow]%.4f[/bold yellow]"
                     % (detail["newmark_displacement"] * 100.0))
        elif seismic_objective:
            shown = "[bold yellow]%.4f[/bold yellow]" % detail.get(
                "ky", float("nan"))
        else:
            shown = f"[bold yellow]{critical.fos:.4f}[/bold yellow]"
        tbl.add_row(
            mid,
            shown,
            str(result.valid_count),
            str(result.invalid_count),
            str(critical.converged) if critical is not None else "—",
        )
    console.print(tbl)

    if not outcome.results:
        raise typer.Exit(4)

    base = output or project.with_suffix(".h5")
    multi = len(outcome.results) > 1
    for mid, result in outcome.results.items():
        # save_results writes one SearchResult per file, so several
        # methods need several files rather than a silently truncated one.
        out = (base.with_name(f"{base.stem}_{mid}{base.suffix}")
               if multi else base)
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
