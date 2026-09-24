# OGR Slip2D v0.1.194

**Primera fase del servidor MCP (spec 008): la capa de operaciones
`ogr_api`.** Todo lo que un agente de IA va a poder hacer con el programa pasa
por aquí: operaciones con nombre, argumentos tipados y respuestas en JSON
estricto, sin Qt y sin el SDK de MCP. El servidor en sí (`ogr_mcp`, stdio y
HTTP) llega en v0.1.195 sobre esta capa; esta versión no instala ninguna
dependencia nueva.

Tres reglas que hasta hoy sólo imponía la interfaz se **mueven** a
`ogr_core/project/rules.py` y la interfaz pasa a preguntarlas. Y al construir
por la vía nueva los dos casos de validación apareció una anomalía que no es
de esta capa (§3): la validación de Ej_1 mide una configuración que ningún
usuario obtiene por defecto.

---

## 0. Decisiones del propietario (2026-09-24)

- Mismo repositorio. `ogr_api` y `ogr_mcp` son paquetes de este árbol; el SDK
  entra como extra opcional `[mcp]`.
- Modo *headless* primero; puente en vivo con la ventana abierta en F4.
- `python_exec` —Python arbitrario contra el modelo— **siempre disponible**,
  como en los servidores de Blender y QGIS. Es ejecución de código por diseño,
  y por eso el HTTP de v0.1.195 exigirá token incluso en *loopback*.
- Clientes prioritarios: Claude (stdio), modelos locales con LM Studio u
  Ollama, Open WebUI y BionicGPT (HTTP / OpenAPI vía `mcpo`), OpenAI y ChatGPT.

## 1. Lo que impone la especificación MCP 2026-07-28

Investigado antes de escribir nada (F0, en `spec/features/008-servidor-mcp/`):

- El protocolo **ya no guarda estado**: sin `initialize` y sin sesiones. Lo
  que tenga que persistir entre llamadas viaja como *handle* que emite el
  servidor (SEP-2567). De ahí `project_id`, `job_id` y `result_id`.
- Las tareas largas pasaron a una extensión que el SDK de Python 2.x **no**
  implementa todavía. Por eso el patrón es propio: `analysis_run` espera hasta
  `wait_seconds` y, si no ha terminado, devuelve un `job_id`.
- *Spike* en un venv aislado con `mcp` 2.2.0, sin tocar el entorno:
  - `MCPServer` está en `mcp.server.mcpserver`.
  - El cliente en memoria es `mcp.Client(server)`.
  - `Annotated[..., Field(description=...)]` llega al esquema, y `Literal`
    se publica como `enum`.
  - Los manejadores síncronos corren en un hilo de trabajo de AnyIO.
  - `report_progress` exige un manejador asíncrono.
  - **El transporte stdio ya desvía el descriptor 1 a stderr** y sirve el
    protocolo desde un duplicado privado, así que no se reimplementa: se
    probará de extremo a extremo en v0.1.195.
  - **Una excepción que no sea `ToolError` llega al cliente sin detalle**,
    así que la envoltura tendrá que convertirlas.
- Licencias del árbol de `mcp` 2.2.0: MIT, BSD-3-Clause, Apache-2.0, PSF-2.0 y
  MIT-0. Todas compatibles con AGPL-3.0-or-later. `opentelemetry-api` es sólo
  la API: sin un SDK configurado no exporta nada, así que no hay telemetría.

## 2. Qué se escribió

### `ogr_core/project/rules.py` (nuevo) — movido, no copiado

- `boundary_refusal(project, btype)` da las respuestas que la interfaz daba
  atenuando menús:
  - un solo contorno exterior, un solo nivel freático y una sola grieta;
  - la línea de desembalse sólo con desembalse rápido activo, y una sola;
  - el objeto de Block Search sólo con Block Search.

  Devuelve un `code` estable y un mensaje. `refresh_action_availability` le
  pregunta y conserva sólo sus *tooltips*.
- `assign_water_surface`, movida desde `MainWindow.apply_water_surface_
  assignment`, con su historia. Ese método queda como entrada del diálogo.
- `compute_blockers`: los dos rechazos de modelo vacío de `act_compute`, con
  código. Se conserva el orden de la interfaz: primero el modelo, luego los
  ajustes y al final los materiales.
- Un test demuestra que es una delegación y no una segunda copia: cambiar la
  regla en `rules` cambia lo que la interfaz atenúa.

### El motor

- **`evaluate_surfaces`** (`analysis_runner.py`) es la puerta única para «el
  FoS de ESTA superficie». Aplica el mismo rechazo, la misma copia factorizada
  y la misma búsqueda configurada que una corrida, y pasa por
  `evaluate_surface`, que recorre las masas deslizantes (la lente del factor 24
  de v0.1.101).
- **`ogr_slip2d/reported.py`** decide qué ES el número de cabecera: FoS,
  sobrediseño, Ky o Newmark. La decisión se mueve desde
  `ogr_gui/reported_quantity.py`, que conserva sus `tr()`.
- **`SnapshotCommand`**, `capture_state` y `restore_state` en `commands.py`.
  Dan deshacer para cualquier edición:
  - es atómico: si la edición falla, restaura y no apila;
  - restaura sobre el MISMO objeto `Project`.
- **`CommandStack.record`** apila un comando ya ejecutado.
  **`CommandStack.history()`** devuelve las descripciones como texto.

### `ogr_api/` (nuevo paquete)

| Módulo | Qué hace |
|---|---|
| `workspace.py` | *Handles*, un `RLock` por modelo (también para leer: `resolve_regions` escribe cachés), deshacer por modelo y resultados en LRU |
| `coerce.py` | Rutas con puntos que sólo recorren campos de dataclass; coerción estricta (2,5 no es un entero, 1 no es un booleano, NaN no es un número) |
| `settings_schema.py` | Opciones de cada campo `str` que es un enum disfrazado, claves virtuales, reglas cruzadas y aplicación atómica por lotes, escrita campo a campo sobre el objeto vivo |
| `catalog.py` | Lo que ofrece el programa, leído de los registros al llamar; los campos que `PARAMETERS` no describe salen de una instancia por defecto |
| `results.py` | Resúmenes en JSON estricto; magnitud informada vía `ogr_slip2d.reported` |
| `render.py` | PNG con matplotlib Agg orientado a objetos, sin pyplot ni Qt |
| `pyexec.py` | `python_exec` con captura por hilo |
| `jobs/` | Análisis en subproceso no-daemon (el pool del grid sigue funcionando dentro), cancelación del árbol entero, estados `failed` y `crashed` |
| `ops/` | 27 operaciones registradas: 9 de proyecto y catálogo, 6 de modelo, 3 de ajustes, 6 de análisis y trabajos, y render, historia y Python |

`examples/api_acads.py` recorre la capa de principio a fin.

## 3. Lo que se encontró

### La validación de Ej_1 mide una configuración que nadie obtiene por defecto

Reportado y NO corregido (regla 6). Al construir Ej_1 por la vía nueva, Spencer
salía **+0,556 %** sobre su círculo publicado, fuera del 0,5 % que le exige
`test_slide_validation_ej1`. La vía nueva no tenía la culpa: reproduce
fielmente el camino configurado. Lo que difiere es la tolerancia.

- El test valida construyendo `Spencer()` y `GLEMorgensternPrice()` con la
  tolerancia **de la clase**, 0,001.
- Un proyecto lleva `methods.tolerance = 0.005`, y por ahí pasan la interfaz,
  la CLI y ahora `ogr_api`.

Medido sobre el círculo publicado de cada método:

| Tolerancia | Spencer | GLE | Bishop | Janbu simp. |
|---|---|---|---|---|
| 0,005 (la del proyecto) | +0,556 % | +0,389 % | −0,035 % | +0,034 % |
| 0,001 (la de la clase) | +0,343 % | +0,158 % | −0,035 % | +0,034 % |
| 1e−4 | +0,306 % | +0,109 % | −0,035 % | +0,027 % |

El test nuevo fija 0,001 con `settings_set` y lo dice en su cabecera. Queda
abierto si el defecto de proyecto debe cambiar o si la validación debe
declarar la tolerancia que usa.

La dirección de rotura no influye: con `R2L` (el valor por defecto, que
contradice la geometría de Ej_1 y el motor avisa) y con `L2R` salen los mismos
números.

### Anomalías de la exploración (regla 6: se reportan, no se corrigen)

A1 a A5 están verificadas leyendo el código; el resto viene de la exploración.

- **A1.** Con la norma de diseño activa, `apply_design_factors` copia el
  proyecto con `Project.from_dict(project.to_dict())` (`design_factors.py:91`).
  La migración de λ por valor (`settings.py:1151-1156`, D182) se aplica por
  eso **en memoria en cada cálculo**: un `max_lambda = 1,5` deliberado se
  calcula como 6,0 sin reabrir el archivo. Amplía el alcance de D182. Por la
  misma razón, `ogr_api` copia siempre con `deepcopy` y nunca por JSON.
- **A2.** `RemoveBoundaryCommand.undo` vuelve a añadir el contorno AL FINAL,
  mientras que `ReplaceBoundaryCommand` direcciona por índice. La secuencia
  Replace(3) → Remove(B) → deshacer → deshacer escribe sobre B: B se pierde y
  D queda duplicado. Trazado a mano, falta un test reproductor. `ogr_api` no
  usa esos comandos (edita con `SnapshotCommand`), pero bloquea el puente de
  F4, que compartirá la pila de la interfaz.
- **A3.** Hipótesis fuerte: en la interfaz la búsqueda en grid nunca va en
  paralelo.
  - La interfaz pasa su propio `Project` al cálculo (`main_window.py:3081`),
    con una lambda del lienzo como *listener* (`canvas_view.py:390`).
  - `Project` no define `__getstate__`, y `_parallel_grid_run` se traga el
    error de *pickle* (`search.py:1924`).
  - Si se confirma, `parallel_search` y `parallel_cpu_percent` no hacen nada
    en la interfaz (regla 7). Se mide con `pickle.dumps(mw.project)` en
    *offscreen*.
  - En `ogr_api` sí va en paralelo: el job lanzado en la prueba de
    cancelación tenía 5 procesos hijos.
- **A4.** `Project.save` pone `is_dirty = False` y a continuación
  `_notify("saved")` lo vuelve a poner a `True`. `ogr_api` decide si hay
  cambios sin guardar con una huella del modelo y no con `is_dirty`.
- **A5.** `test_acads_validation_v178.py` dice «20×20 intervalos, 11 círculos
  = 4851», pero pasa `grid_nx = 21` y `radius_increment = 11`. Con la
  convención que fija Ej_1 eso son 22×22×12 = 5808. No se toca, porque es un
  caso de validación; el test nuevo usa los intervalos del enunciado y afirma
  4851 por identidad.
- **A6.** Borrar un material no limpia sus referencias, y una región sin
  asignar toma `materials[0]`. `material_delete` se niega salvo `reassign_to`
  o `force`, y avisa si el borrado cambia el material por defecto.
- **A7.** Al crear una carga se pierde `creates_excess_pore_pressure`
  (`main_window.py:3946-3955`, 4159-4165); sólo «Modificar» lo aplica.
- **A8.** Ctrl+Shift+S está asignado a la vez a `save_as` y a `snap_opts`.
- **A9.** Hay acciones de `InterpretWindow` sin manejador: Phreatic Surface,
  Piezometric Lines, Flow Vectors, Streamlines y Measure.
- **A10.** `PaintRegionCommand.description` es un método y no un `str`.
  `CommandStack.history()` lo llama; `next_undo_description` sigue devolviendo
  el método.
- **A11.** Una `search_method` desconocida corre un grid sin avisar.
  `ogr_api` la rechaza con sugerencia. La CLI acepta `--search` libre, y su
  `--dr` es `float` cuando el campo es `int`.
- **A12.** La estadística y el retroanálisis parten del proyecto SIN factores
  de diseño, mientras que el determinista sí los lleva. Sin verificar si es
  intencionado.
- **A13.** El docstring de la terminal dice que Shift+Enter envía, pero el
  código envía con Enter.
- **A14.** Un límite de grid suelto (`grid_x_min` sin `grid_x_max`) se ignora
  en silencio y el grid pasa a automático (`_grid_range`). Es la regla 7.
  `ogr_api` exige el par completo.

### Errores propios detectados antes de publicar

1. `call(ws, name, **kwargs)` chocaba con las operaciones que tienen un
   argumento `name` (`project_new(name=...)`). El nombre de la operación pasa
   a ser sólo posicional.
2. `typing.get_type_hints(Material)` falla entero por una sola referencia
   adelantada que el módulo no importa (`Optional["HydraulicProperties"]`).
   Ahora se resuelve campo a campo y los irresolubles quedan como `Any`.
3. El *spike* dio por roto `report_progress` y el fallo era mío: el cliente
   espera una devolución de progreso asíncrona.
4. La prueba de «sin huérfanos» al cancelar sería vacía si el pool no llegara
   a arrancar. Se midió aparte: el job tenía 5 hijos y ninguno sobrevive.
5. El `pytest.raises` simulado no expone `exc.value`, así que los tests que
   leen el mensaje usan un auxiliar local en vez de cambiar el runner.

## 4. El runner

`tests/_runner.py` **falla** si un test devuelve una corrutina. Hasta hoy un
`async def test_*` devolvía la corrutina sin ejecutar una línea y contaba como
aprobado. Los tests del servidor MCP son los primeros de la suite con código
asíncrono que conducir, que es justo cuando ese desliz deja de ser
hipotético. `ogr_api` entra en `PACKAGES`, así que la comprobación de
procedencia también lo mide.

## 5. Tests

| Archivo | Casos | Anclaje |
|---|---|---|
| `test_api_validation_v1194.py` | 7 | Regla 1 por la vía nueva: ACADS 1(a) dentro de 0,991 ± 2 % (Bishop 0,987035; `_MEAN_33` y `_TOL` importados); Ej_1, los seis métodos sobre sus círculos publicados y el grid publicado, que encuentra exactamente el centro y el radio publicados (Bishop (88; 70,5), R = 47,212444; Janbu (84; 66), R = 41,501436) con 4851 superficies |
| `test_api_settings_v1194.py` | 22 | Rechazos con sugerencia, lote atómico, reglas cruzadas, clasificación de todo campo `str`, cada valor por defecto dentro de sus opciones; regla 7: el número de dovelas, la norma y la lista de métodos mueven el resultado |
| `test_api_undo_v1194.py` | 6 | Para CADA operación que edita, que la tabla está obligada a cubrir: hacer, deshacer y rehacer dan el `to_dict` exacto sobre el mismo objeto; lo fallido no deja rastro; un *script* es un paso y se revierte si lanza |
| `test_api_jobs_v1194.py` | 8 | Aislamiento (se revalora la crítica sobre el modelo ORIGINAL a 1e−6), progreso, procedencia, cancelación sin huérfanos, `crashed`, `failed`, `Busy` |
| `test_api_render_results_v1194.py` | 10 | PNG del tamaño pedido leído del IHDR; la superficie sólo con resultado (píxeles contados); JSON estricto; la magnitud informada igual que en la interfaz |
| `test_api_layering_pyexec_v1194.py` | 8 | Capas por AST; captura por hilo con dos *scripts* simultáneos; flujos restaurados |
| `test_rules_moved_v1194.py` | 10 | Las reglas, la delegación de la interfaz, `SnapshotCommand` y el runner contra corrutinas |

71 casos nuevos. Ninguno fija un número contra una instantánea. Los anclajes son casos
publicados, identidades de población, identidades de deshacer y estructura
leída del propio archivo.

## 6. Verificación

- Suite entera y sin argumentos: **4304/4304**, sin banner FILTERED RUN, con
  seis paquetes medidos de este árbol (`ogr_api` incluido en la comprobación
  de procedencia). v0.1.193 traía 4233; los +71 son exactamente los siete
  archivos nuevos. Unos 28 min (08:34 → 09:02), sola en la máquina.
- Discriminación contra v0.1.193, razonada y no medida en un *worktree*: todos
  los tests nuevos importan símbolos que 0.1.193 no tiene, así que fallarían
  por AUSENCIA, que es discriminación débil. La excepción es el del runner,
  que falla por COMPORTAMIENTO: el `_run_method` de 0.1.193 cuenta la
  corrutina como aprobada.
- Tests preexistentes de lo tocado en la interfaz (asignación de agua,
  disponibilidad de acciones, magnitud informada, pila de comandos,
  superficies de usuario): 278/278 en corrida filtrada antes de la suite.
- `examples/api_acads.py`: Bishop 0,987035, Spencer 0,986682, PNG y `.ogr`
  que la interfaz abre.

## 7. Qué falta

- F1b (v0.1.195): `ogr_mcp`, stdio y HTTP con token, perfiles `full` y
  `compact`, `docs/mcp/` y prueba manual con Claude Code, LM Studio y `mcpo`.
  Allí se instala `mcp>=2.1,<3`.
- F2 a F4b según el plan de la spec 008.
