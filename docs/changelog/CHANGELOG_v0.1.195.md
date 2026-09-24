# OGR Slip2D v0.1.195

**Segunda fase del servidor MCP (spec 008): el servidor en sí, `ogr_mcp`.**
Un agente de IA ya puede manejar OGR Slip2D sin abrir la interfaz: Claude
(Desktop o Code), un modelo local en LM Studio u Ollama, Open WebUI por HTTP,
BionicGPT u otro cliente OpenAPI a través de `mcpo`, o el Agents SDK de
OpenAI.

Tiene 28 herramientas, una por operación de `ogr_api` más `server_info`, en
dos perfiles, y dos transportes: stdio, y HTTP con token siempre.

```bash
pip install -e ".[mcp]"
ogr-slip2d-mcp --workdir C:\ruta\a\proyectos
```

Tres hallazgos de esta fase:

- El test de reenvío de parámetros encontró un fallo real antes de publicar:
  ninguna llamada a `boundary_edit` funcionaba (§2).
- `mcpo` 0.0.20 no arranca con el SDK `mcp` 2.x (§3).
- En v0.1.194 rompí la tabla de estructura de AGENTS.md (§3).

---

## 1. Qué se escribió

### `ogr_mcp/` (nuevo paquete)

| Módulo | Qué hace |
|---|---|
| `server.py` | Las 28 herramientas, escritas a mano con descripciones para el modelo, y los recursos `ogr://guide` y `ogr://catalog/{kind}` |
| `profiles.py` | Perfil `full` (28 herramientas) y `compact` (14, para modelos locales pequeños); `--toolsets` para elegir conjuntos |
| `security.py` | Token *bearer* comparado en tiempo constante; protección de `Host`/`Origin` del SDK activada |
| `cli.py` | `ogr-slip2d-mcp`: stdio o HTTP, perfil, `--workdir`, `--max-wait`, token por archivo o variable |
| `guide.py` | Las reglas que cambian el número (primer material por defecto, agua sin asignar, intervalos del grid...), en `instructions` y en el recurso |

Tres detalles del SDK marcaron el diseño:

- **Errores.** Una excepción que no sea `ToolError` llega al cliente como un
  «Error executing tool» sin detalle, así que cada herramienta corre dentro de
  un traductor. Un `OgrApiError` sale con su código y su sugerencia
  (`[E_INVALID_ARGUMENT] 'search_metod' is not a field of search. Hint: Did
  you mean 'search_method'?`); cualquier otra excepción, con su tipo y su
  mensaje.
- **Esperas.** Muchos clientes cortan una petición a los 60 s. Por eso
  `analysis_run` y `job_get` esperan como mucho `--max-wait` (50 s por
  defecto) informando del progreso y, si el análisis no ha terminado,
  devuelven el `job_id`.
- **stdout.** El SDK 2.x ya desvía el descriptor 1 mientras sirve por stdio.
  No se reimplementa: se prueba (§4).

### Contabilidad

- `pyproject.toml`: extra `mcp = ["mcp>=2.1,<3"]` y comando
  `ogr-slip2d-mcp`.
- CI: `pip install -e ".[mcp]"`. Los tests del servidor retornan pronto en
  una máquina sin el SDK, pero **fallan en CI** sin él, así que el extra no se
  puede olvidar en silencio.
- Versión en **nueve** sitios (`ogr_mcp` es el noveno). `ogr_mcp` entra
  también en los paquetes cuya procedencia comprueba el runner.
- `docs/mcp/`: `README.md`, `clientes.md`, `seguridad.md` y
  `herramientas.md`, que un test obliga a nombrar todas las herramientas.
- Los dos README tienen un apartado sobre el servidor MCP. AGENTS.md añade
  la fila de `ogr_mcp`, los comandos y un «No hagas»: no quitar el token del
  HTTP.
- `ogr_api/inventory.py` clasifica las 136 acciones de la ventana principal
  (§5).
- `ogr_api/coerce.py`: cuando hay sugerencia, el error ya no lista después
  los ~70 campos de `search`, que sólo gastaban contexto del modelo.

## 2. Un fallo real encontrado antes de publicar

`test_every_parameter_reaches_its_operation` llama a CADA herramienta con un
valor no predeterminado en CADA parámetro y comprueba, espiando la llamada,
que llega a su operación. Falló en `boundary_edit`:

- La herramienta tiene un parámetro llamado `op`.
- El auxiliar interno del servidor era `run(op, **kwargs)`.
- Así que toda llamada a `boundary_edit` levantaba un `TypeError` («multiple
  values for argument 'op'») **fuera** del traductor de errores, y el SDK
  habría contestado un «Error executing tool boundary_edit» sin más.

Nadie lo habría visto hasta usarlo. Es el mismo choque que v0.1.194 arregló
en `ogr_api.call` (con `project_new(name=...)`), y se arregla igual: el
nombre de la operación pasa a ser sólo posicional (`run(op_name, /, **kw)`).

## 3. Lo que se encontró

### `mcpo` no funciona con el SDK `mcp` 2.x

Medido: `mcpo` 0.0.20 importa `streamablehttp_client`, que la 2.0 del SDK
renombró a `streamable_http_client`, y su dependencia no fija versión. En un
entorno con `mcp` 2.x ni arranca.

En un entorno aparte con `mcp` 1.30 funciona entero:

- 28 rutas en `openapi.json`;
- 401 sin la clave;
- análisis completo, con FoS 1,002838;
- la imagen como *data URI* y guardada en disco con `save_path`;
- los errores con su mensaje en `detail` (HTTP 500).

Esto demuestra, de paso, que el servidor atiende a los clientes antiguos del
protocolo de 2025. `docs/mcp/clientes.md` lo documenta: `mcpo` en su propio
entorno, con `mcp<2`.

### Mi tabla rota en AGENTS.md (v0.1.194)

En v0.1.194 metí el párrafo «Capas en un solo sentido» DENTRO de la tabla de
estructura de AGENTS.md, y las filas `tests/`, `docs/` y `spec/` quedaron
huérfanas bajo él. Corregido: el párrafo va detrás de la tabla.

### El Agents SDK de OpenAI corta pronto

Su `client_session_timeout_seconds` es corto por defecto, y `analysis_run`
espera hasta 30 s. La guía de clientes dice que se suba o que se usen
`wait_seconds` pequeños con `job_get`. **No lo he medido**: sale de la
documentación del SDK.

## 4. Tests

| Archivo | Casos | Anclaje |
|---|---|---|
| `test_mcp_server_v1195.py` | 14 | Herramientas = operaciones en los dos sentidos; **cada parámetro llega a su operación** (por espía); descripciones en toda herramienta y parámetro; orden estable; perfil `compact` ≤ 14 000 caracteres (medido 12 774); errores con código, sugerencia y tipo; regla 1 por el protocolo (ACADS 1(a) por llamadas de herramienta, IDÉNTICO al número de `ogr_api` y dentro de 0,991 ± 2 %); `wait_seconds` decide entre resultado y `job_id` (regla 7 del único argumento que consume esta capa); imagen PNG; recursos; `server_info` |
| `test_mcp_transports_v1195.py` | 6 | stdio en subproceso: `print`, `os.write(1, …)` y un proceso HIJO que escribe en su stdout, y la llamada siguiente sigue funcionando. HTTP: 401 sin token o con uno falso, 403 con un `Origin` ajeno y 421 con un `Host` ajeno (con token), servicio completo con token. Sin red sin token (código 2, también con `--no-auth` fuera de *loopback*). SDK ausente → código 3 y qué instalar. El paquete se importa sin el SDK. El extra y el comando están declarados |
| `test_action_inventory_v1195.py` | 4 | La ventana REAL: cada una de sus 136 acciones está clasificada una sola vez; las cubiertas nombran operaciones que existen; los motivos y las fases están escritos; las pendientes no pasan de su techo |

24 casos nuevos. Todos los que necesitan el SDK retornan pronto sin él,
salvo en CI.

## 5. Cuánto del programa alcanza ya un agente

`ogr_api/inventory.py` clasifica las 136 acciones de `MainWindow._actions`:

- **42 cubiertas**: archivo, deshacer, ajustes, cálculo, resultados, todos
  los contornos y sus ediciones, materiales y su asignación, opciones de
  superficie, grid, límites de talud, eje de momentos, imagen y terminal.
- **23 sólo de interfaz**, cada una con su motivo escrito: zoom, *pan*,
  rejilla, impresión, ayuda...
- **71 pendientes**: 57 de F2 (cargas, soportes, DXF, informe, foco,
  superficies de usuario, anotaciones, transformaciones) y 14 de F3 (agua con
  elementos finitos, estadística, retroanálisis, optimización).

El techo de pendientes queda en 71, sólo puede bajar, y F4 cierra en cero.
`server_info` publica esta cobertura. Hasta entonces, lo pendiente se alcanza
con `python_exec`.

## 6. Verificación

- Suite entera y sin argumentos: **4328/4328**, sin banner FILTERED RUN,
  con siete paquetes medidos de este árbol. v0.1.194 traía 4304; los +24 son
  los tres archivos nuevos. 33 min (10:05 → 10:38), sola en la máquina.
- Clientes reales, por sus mismos caminos:
  - el cliente stdio del SDK, que es como lanzan el servidor Claude, LM
    Studio y el Agents SDK;
  - el cliente HTTP del SDK con token, que es el camino de Open WebUI;
  - `mcpo` real con un cliente antiguo, que es el camino de BionicGPT.
- **No probado a mano** con Claude Desktop, Claude Code, LM Studio ni Open
  WebUI: registrarlo en su configuración cambia la tuya, y eso queda para ti
  con `docs/mcp/clientes.md`.
- La discriminación contra v0.1.194 no se midió en un *worktree*. Todos los
  tests nuevos importan `ogr_mcp`, que no existía, así que fallarían por
  ausencia; el reenvío de parámetros sí discrimina por comportamiento, porque
  destapó el fallo de §2 en el propio árbol de trabajo.

## 7. Qué falta

- F2 a F4b según la spec 008, empezando por un plan corto de F2: cargas,
  soportes, grieta, sismo, foco, superficies de usuario, anotaciones, DXF,
  informe y transformaciones.
- Las anomalías A1–A14 y la tolerancia de Ej_1 de v0.1.194 siguen reportadas
  y sin corregir.
