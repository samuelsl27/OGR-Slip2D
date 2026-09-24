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

## F2 · cargas, soportes, búsqueda, anotaciones, archivos (v0.1.196)

- [x] 3.1 Cargas repartidas y puntuales, sismo y registros; se rechaza lo
      que el motor no leería (puntual relativa al contorno, `angle_deg` sin
      orientación angular, `magnitude_end` sin distribución).
- [x] 3.2 Tipos de soporte y soportes, patrón y desagrupar; parámetros contra
      los campos y los tokens de su clase; valores por defecto de la clase.
- [x] 3.3 Grieta de tracción, foco, superficies propias.
- [x] 3.4 Anotaciones y `annotation_to_boundary` por `boundary_add`.
- [x] 3.5 DXF (inspeccionar, importar en un paso, exportar), informe PDF,
      importar propiedades.
- [x] 3.6 `boundary_edit` copiar/escalar/girar/simplificar,
      `external_reshape`, `geometry_cleanup`, plantilla `demo`.
- [x] 3.7 Movido al núcleo con la interfaz llamándolo: demo, importar
      propiedades, registros sísmicos, referencias de soporte, inspección y
      simplificación, los dos modos de *Expand/Shrink*; siete defectos de la
      interfaz corregidos por el camino.
- [x] 3.8 Tests: regla 1 (cuña con anclaje y con sobrecarga), regla 7,
      deshacer de las 32 operaciones de edición, delegaciones por el
      manejador real.
- [ ] 3.9 Tanda propia: cargas puntuales `normal_to_boundary` y
      `angle_to_boundary` con validación externa (bloque B3).
- [x] 3.10 Decisión del propietario sobre *Change Slope Angle*: rehacerla
      (bloque B2).

## Correcciones antes de F3 (decisión del propietario, 2026-09-24)

Tres defectos que F2 dejó reportados, cada uno su versión y su plan corto:

- [x] B1 (v0.1.197) Lentes: regiones con huecos de verdad (consultas,
      huellas, áreas, lienzo, ayudas, PNG, mallado); y un contorno cerrado
      nunca guarda su vértice de cierre (DXF, al añadir, al abrir).
- [ ] B2 (v0.1.198) *Change Slope Angle* rehecha: pie y coronación como
      vértices, solo la cara, proyección horizontal/vertical/giro, bermas.
- [ ] B3 (v0.1.199) Cargas puntuales `normal_to_boundary` y
      `angle_to_boundary`, con validación externa.

## F3–F4b

Plan corto antes de cada una. Al cerrar F4, `PENDING` del inventario vacío.
