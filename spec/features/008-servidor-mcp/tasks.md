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
      los clientes stdio y HTTP del SDK; Claude Code, LM Studio, Open WebUI
      y ChatGPT (con un túnel HTTPS, desde v0.1.204) quedan para el
      propietario (tocan su configuración y su cuenta).
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
- [x] 3.9 Tanda propia: cargas puntuales `normal_to_boundary` y
      `angle_to_boundary` con validación externa (bloque B3, v0.1.199).
- [x] 3.10 Decisión del propietario sobre *Change Slope Angle*: rehacerla
      (bloque B2).

## Correcciones antes de F3 (decisión del propietario, 2026-09-24)

Tres defectos que F2 dejó reportados, cada uno su versión y su plan corto:

- [x] B1 (v0.1.197) Lentes: regiones con huecos de verdad (consultas,
      huellas, áreas, lienzo, ayudas, PNG, mallado); y un contorno cerrado
      nunca guarda su vértice de cierre (DXF, al añadir, al abrir).
- [x] B2 (v0.1.198) *Change Slope Angle* rehecha: pie y coronación como
      vértices, solo la cara, proyección horizontal/vertical/giro, bermas;
      en la interfaz y como `slope_angle_change`. De paso, *Insert Vertex*
      (a `_pick_edge` le faltaba el `def` desde v0.1.59).
- [x] B3 (v0.1.199) Cargas puntuales `normal_to_boundary` y
      `angle_to_boundary`: hacia el terreno, desde su superficie en el
      punto; validadas contra la cuña de Coulomb.

## F3–F4b

Plan corto antes de cada una. Al cerrar F4, `PENDING` del inventario vacío.

- [x] F3a (v0.1.200) Agua subterránea: `hydraulic_set`, `mesh_generate`,
      `mesh_reset`, `seepage_bc_set`, `seepage_bc_clear`, `transient_set`,
      `water_grid_set`, `water_grid_delete`, `groundwater_run` (trabajo, con
      el campo escrito de vuelta en un paso de deshacer),
      `groundwater_results`, `drawdown_sweep_run` (trabajo, por la puerta
      del análisis) y `model_render(field=...)`. Las unidades hidráulicas
      por modelo (decisión del propietario, 2026-09-24). Validado contra
      Darcy 1-D, medias por capas, erfc, Charnyi y Morgenstern (1963).
      Inventario: 108 cubiertas, 5 pendientes, techo 5.
- [x] F3b (v0.1.201) Estadística, retroanálisis, optimización e
      interpretación: `random_variable_list/set/delete`, `statistics_run`,
      `back_analysis_run` y `optimize_run` (trabajos, por la puerta del
      análisis) y `results_query`; `ogr_slip2d/interpretation.py` con lo
      que preguntaba la ventana. Inventario: 113 cubiertas, 23 de
      interfaz, **0 pendientes**, techo 0 (el plan lo dejaba para F4).
- [x] Bloque 4 (v0.1.202), antes de F4: *Abrir* limpia el proyecto
      anterior; el retroanálisis con Janbu coincide con el solver; las
      muestras de la estadística cuentan solo si son válidas y admisibles
      (`lost_by_cause` en el resumen); el tipo de la rejilla de presiones es
      el del método, y `water_grid_set(value_type=…)` fija el método en el
      mismo paso de deshacer.
- [x] F4 (v0.1.203) Puente en vivo con la ventana: *Herramientas > Puente
      para agentes (MCP)* (TCP en 127.0.0.1 con token y archivo de
      descubrimiento) y `ogr-slip2d-mcp --attach [PID]`, que reenvía cada
      herramienta al mismo registro. Un modelo y una pila de deshacer
      compartidos, `Busy` mientras la ventana calcula, `project_new/open` en
      la ventana y nunca sobre cambios sin guardar, el análisis del agente en
      el panel y `model_render(source="window")`. Corregidos A2, la ruta del
      handle con proveedor, la fusión de tres vías de `SnapshotCommand` y el
      «sin guardar» tras guardar.
- [x] F4b (v0.1.204) HTTPS remoto: con `--public-url` el servidor es su
      propio servidor OAuth 2.1 (PKCE S256, DCR con lista blanca de retorno,
      tokens opacos atados al recurso, renovación rotativa y revocación), y
      la autorización la concede el dueño tecleando el token del servidor en
      `/approve`. HTTPS detrás de un túnel o directo con `--tls-cert/--tls-key`.
      Probado de extremo a extremo contra un proceso real en local. La
      conexión real desde chatgpt.com queda en 2.7, a mano (pasos en
      `docs/mcp/clientes.md`).
