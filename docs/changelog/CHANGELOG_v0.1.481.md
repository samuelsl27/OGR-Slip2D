# OGR Slip2D v0.1.481

**`server_info` dice la carpeta de trabajo también con `--attach`.** Un defecto de lo que se
informa, no de lo que se hace: las rutas relativas ya se resolvían bien. No se mueve un número.

## 0. Lo que se encontró

Observado el 2026-11-22 en el PC nuevo, sin diagnóstico: con el servidor lanzado con
`--attach --workdir <carpeta>` (se ve en la línea de órdenes del proceso), `server_info` devolvía
`"workdir": null`.

- Con `--attach`, `ogr_mcp/cli.py` no crea espacio de trabajo propio (`ws = None`), a propósito:
  en ese modo el servidor solo trabaja sobre una ventana. El `--workdir` no se pierde: lo guarda el
  `WindowRouter` (`ogr_api/bridge.py`) y lo manda a la ventana en el saludo del puente (v0.1.207),
  así que una ruta relativa significa esa carpeta también en la ventana.
- `server_info` (`ogr_mcp/server.py`) solo miraba `ws.workdir`. El servidor usaba una carpeta y
  decía que no tenía ninguna: un agente que leyera `null` podía pensar que una ruta relativa no
  tenía a qué agarrarse.

## 1. Cambio

- `server_info`: el `workdir` del espacio de trabajo si lo hay; si no, el del router; si tampoco,
  `null`. Con espacio de trabajo propio no cambia nada: el router toma el mismo `--workdir`.

## 2. Qué se probó

- `tests/test_mcp_attach_workdir_v1481.py`, tres casos con un router sin ventana
  (`finder=lambda: None`): con `--attach` y carpeta da la carpeta; con `--attach` sin carpeta,
  `null`; con espacio de trabajo propio, la de este.
- **Mutante**: `server.py` como en la 0.1.480. Muere `test_attached_it_is_the_routers`, y los otros
  dos siguen pasando, como deben.
- `test_bridge_version_v1300` (server_info con ventana falsa): 7 de 7.
- Suite entera, `--jobs 4`, y la serie: ver §3.

## 3. Suite

En el `.venv` (`shared: ogr_core 0.2.2 … (installed, no git tree)`), fuera de pantalla, una
detrás de otra:

- **`--jobs 4`**: 7551 casos, 7550 pasan, 0 fallan, 1 saltado (`os.killpg`, solo POSIX), sin fugas
  ni tramos muertos, código de salida 0.
- **En serie**, sin argumentos: la primera en este PC (16 núcleos físicos, 32 lógicos). Mismos
  totales (7551, 7550, 0, 1), código de salida 0, en **25,7 min** de reloj (17:30:10 → 17:55:49).
  El runner la apuntó como `full serial run recorded: 7aff40b`: guarda el último commit, y la
  corrida fue sobre el árbol de esta versión antes de confirmarla. `SERIAL RUN DUE` deja de salir.
  Es una sola corrida: no reescribe la tabla «Coste de los tests» de AGENTS.md, que sigue siendo
  del portátil antiguo.

## 4. Después de esta versión, sin número: suites a la vez

Decisión de la propietaria (2026-11-22). En este PC (16 núcleos físicos, 32 lógicos, 64 GB) se
llevan varios desarrollos a la vez, y «nunca dos corridas a la vez» era del portátil anterior
(4 núcleos, 16 GB), donde competían por los núcleos y la máquina paginaba. Probado ese día: con
esta suite en marcha (`--jobs 4`), las de OGR-Core y OGR FEM2D dieron 796 de 796 en 1,3 min y
205 de 205 en 0,9 min, sin fugas. AGENTS.md («Coste de los tests») dice ahora:

- las suites de programas distintos pueden correr a la vez;
- dos de este programa, no: comparten `%TEMP%/ogr-slip2d-test-durations.json`, `-test-times.json`
  y `-serial-run.json`. Pasa cuando la sesión de OGR-Core corre esta suite contra un núcleo sin
  etiquetar (`--dev-core`) mientras esta sesión corre la suya: se avisa antes;
- lo que se cronometra va solo, también el banco de cómputo: si comparte máquina, su reloj no se
  compara con nada.

Cabe en las mismas siete líneas: AGENTS.md sigue en 499 (tope 500, `test_agent_scaffolding_v158`).

**Lo que se buscó antes de escribirlo**, por si la regla rompía algo:

- **Nada choca entre programas.** Los registros del runner llevan el nombre del programa
  (`ogr_core.testing.runner`, `Records`); los tramos de `--jobs` y las dos carpetas de cada
  corrida (puente y preferencias) son `mkdtemp`; todo puerto de los tests es efímero
  (`bind(("127.0.0.1", 0))`) y el puente de la ventana toma uno aleatorio. OGR FEM2D no importa
  `ogr_slip2d`, y ningún nombre fijo de la carpeta temporal de esta suite aparece en OGR-Core ni
  en OGR FEM2D.
- **Los tres archivos con reloj** (`SERIAL_LANE = True`: `test_optimizations_v111`, < 5 s para
  ~1 s; `test_jobs_file_race_v1198`, < 5 s; `test_remote_oauth_v1204`, 40 s para arrancar)
  siguen corriendo solos dentro de esta suite, pero ya no en la máquina: el comentario de
  `test_optimizations_v111` («so that no other process shares its cores») deja de ser cierto con
  otra suite en marcha. Con 32 lógicos el margen es holgado; no se tocan salvo que fallen a ratos.
- **Dos nombres fijos en la carpeta temporal, preexistentes**, que solo chocan entre dos corridas
  de este programa (lo que la regla prohíbe) y van contra «nunca en una ruta fija»:
  `test_seepage_serialisation_v178` (`ogr_seepage_roundtrip.ogr`) y `test_slide_validation_ej1`
  (`ogr_test_report.pdf`, un caso de validación). Anotados, sin tocar.
- `%TEMP%/ogr_slices` lo comparten todos los procesos de OGR Slip2D (suite, ventana, banco); sus
  limpiezas no pueden borrar en Windows una carpeta abierta. Tampoco es un choque entre programas.
