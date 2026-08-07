# OGR Suite — Development Roadmap

## v0.1.0 (current) — "Foundations"

**Delivered**

- Project data model (boundaries, materials, supports, loads, seismic)
- Geometry core (vertex, polyline, cleanup: duplicates, RDP, intersections)
- 7 constitutive strength models (Mohr-Coulomb, Undrained, Hoek-Brown,
  Power Curve, Vertical Stress Ratio, Infinite, None) — plugin-based
- 4 LEM methods (Ordinary, Bishop, Janbu Simplified, Janbu Corrected)
- Grid & Slope surface search
- Hybrid JSON / HDF5 file format
- Undo/Redo with Command pattern
- GUI: QGIS-style MainWindow with 12 menus, 50+ tool actions, dockable
  results panel, light/dark themes, i18n (ES/EN)
- CLI (Typer): `info`, `compute`, `methods`, `strength-models`, `new-demo`
- Test suite (54 tests, passing)

## v0.2.0 — "Interactive Geometry"

- [ ] Interactive boundary drawing on the canvas (click-click-click to
      create a polyline, Esc/Enter to finish)
- [ ] Vertex drag-edit with live geometry-cleanup
- [ ] Interactive load placement with live-updating arrow preview
- [ ] Interactive support placement with angle snap
- [ ] DXF import with the full layer-mapping dialog
- [ ] DXF export
- [ ] Print preview & Print

## v0.3.0 — "More solvers"

- [ ] Spencer method (force + moment equilibrium)
- [ ] GLE / Morgenstern-Price method
- [ ] Non-circular slip surface search (path optimisation)
- [ ] Auto-refine grid search (multi-scale)
- [ ] Back analysis (solve for `c` / `φ` given a target FoS)

## v0.4.0 — "Probabilistic & Sensitivity"

- [ ] Random variables on material parameters
- [ ] Monte Carlo sampler
- [ ] Probability of failure P_f and reliability index β
- [ ] Sensitivity (Tornado / Sobol) plots
- [ ] Latin Hypercube sampling option

## v0.5.0 — "OGR FEM2D — Steady-state groundwater"

- [ ] Triangular mesh generator (meshpy / triangle)
- [ ] Linear-element FEM solver for Laplace's equation
- [ ] Boundary conditions (fixed head, flux, seepage face)
- [ ] Results visualisation (total head, pore pressure, flow vectors,
      streamlines)
- [ ] Coupling Slip2D ↔ FEM2D (pore pressure field from FEM feeds LEM)

## v0.6.0 — "Transient groundwater"

- [ ] Time-dependent FEM
- [ ] Rapid drawdown analysis
- [ ] Unsaturated flow (van Genuchten SWCC)

## v1.0.0 — "Production-ready"

- [ ] Comprehensive user manual (Sphinx)
- [ ] Plugin installer from PyPI / GitHub
- [ ] MDI (multi-document) window management
- [ ] Printable reports (LaTeX / HTML templates)
- [ ] CI/CD with automated test runs and wheels for Win/Mac/Linux
- [ ] Submission to Journal of Open Source Software (JOSS)

## Post-1.0 research directions

- 3D slope stability (OGR Slope3D)
- Strength Reduction Method (SRM) — FEM-based stability
- Earthquake time-history analysis (Newmark sliding block)
- Machine-learning-assisted surface search
- Integration with QGIS as a processing provider

---

**Maintainer**: Samuel Sáez López — PhD Student, UPCT
