# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una
tarea: es un deseo.

## F0 · Antes de tocar código

- [x] 0.1 Investigar la especificación MCP vigente (2026-07-28), el SDK de
      Python y lo que pide cada cliente (stdio, HTTP, OpenAPI vía `mcpo`).
- [x] 0.2 *Spike* del SDK en un venv aislado: `mcp` 2.2.0 instalado; ruta
      `mcp.server.mcpserver.MCPServer`; cliente en memoria `mcp.Client(server)`;
      `Annotated[..., Field(description=…)]` llega al esquema; `Literal` se
      publica como `enum`; `TypedDict` produce `outputSchema` y
      `structuredContent`; los manejadores síncronos corren en un hilo de
      trabajo de AnyIO; `ctx.report_progress` exige un manejador asíncrono; una
      excepción que no es `ToolError` llega al cliente sin detalle; el
      transporte stdio desvía ya el descriptor 1 a stderr.
- [x] 0.3 Licencias del árbol de `mcp` 2.2.0: MIT, BSD-3-Clause, Apache-2.0,
      PSF-2.0 y MIT-0. Todas compatibles con AGPL-3.0-or-later.
      `opentelemetry-api` es sólo la API: sin SDK configurado no exporta nada.
- [x] 0.4 Anotar las anomalías de la exploración (A1–A13) antes de tocar nada
      — regla 6. Van en el changelog de v0.1.194.

## F1a · `ogr_api` (v0.1.194)

- [x] 1.1 `ogr_core/project/rules.py`: conflicto de instancia única,
      asignación de superficie de agua (movida), bloqueos de cálculo.
- [x] 1.2 `SnapshotCommand` atómico en `commands.py`.
- [x] 1.3 `evaluate_surfaces` en `analysis_runner.py`.
- [x] 1.4 `ogr_api`: errores, workspace, instantáneas, coerción, esquema de
      ajustes, catálogo.
- [x] 1.5 Operaciones: proyecto, modelo, ajustes, análisis, vista, historia,
      Python.
- [x] 1.6 Resúmenes de resultados y magnitud informada (delegada por la GUI).
- [x] 1.7 Render PNG con Agg.
- [x] 1.8 `python_exec` con captura por hilo.
- [x] 1.9 Jobs en subproceso: progreso, aislamiento, cancelación, caída.
- [x] 1.10 La GUI delega en `rules.py`.
- [x] 1.11 Tests: validación ACADS y Ej_1 por la vía nueva, ajustes (regla 7),
      deshacer genérico, jobs, render, resultados, capas, `python_exec`.
- [x] 1.12 El runner falla si un test devuelve una corrutina.
- [x] 1.13 Versión en ocho sitios (`ogr_api` es el octavo; `ogr_mcp` será
      el noveno en F1b), AGENTS.md, `tech-stack.md`, changelog.
- [x] 1.14 Suite completa en verde, sin argumentos: 4304/4304.

## F1b · `ogr_mcp` (v0.1.195)

- [x] 2.1 Servidor, perfiles `full`/`compact`, errores como `ToolError`.
- [x] 2.2 stdio y HTTP con token, `Origin`/`Host`.
- [x] 2.3 Recursos: guía de modelado, catálogo.
- [x] 2.4 Extra `[mcp]`, script `ogr-slip2d-mcp`, CI con `.[mcp]`.
- [x] 2.5 `docs/mcp/`: clientes, seguridad, herramientas.
- [x] 2.6 Tests: ACADS por el protocolo, esquemas y descripciones,
      presupuesto de `compact`, stdio de extremo a extremo, seguridad HTTP,
      inventario de acciones.
- [~] 2.7 Prueba manual: `mcpo` real (en su propio entorno con `mcp<2`) y
      los clientes stdio y HTTP del SDK; Claude Code, LM Studio y Open WebUI
      quedan para el propietario (tocan su configuración).
- [x] 2.8 Suite completa (4328/4328) y changelog.

## F2–F4b

Plan corto antes de cada una. Al cerrar F4, `PENDING` del inventario vacío.
