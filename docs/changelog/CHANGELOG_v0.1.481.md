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
