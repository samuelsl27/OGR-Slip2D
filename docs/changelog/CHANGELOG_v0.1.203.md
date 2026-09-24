# OGR Slip2D v0.1.203

**F4 del servidor MCP: el agente maneja la ventana abierta.**

Hasta ahora el servidor trabajaba con sus propios modelos, sin interfaz. Lo
que construía el agente no se veía hasta guardarlo y abrirlo en la ventana.

Con *Herramientas > Puente para agentes (MCP)* y
`ogr-slip2d-mcp --attach`, el agente trabaja sobre **el modelo de la
ventana**:

- sus ediciones son pasos de *Edición > Deshacer*;
- sus análisis se ven en el panel de resultados;
- puede pedir una captura del lienzo real.

Las 74 herramientas son las mismas y pasan por la misma puerta: el puente
solo cambia el transporte.

Para compartir la pila de deshacer hubo que corregir antes tres defectos
(§3).

---

## 1. Arquitectura

El diseño sigue el de los servidores MCP de Blender y QGIS.

- **En la ventana**, una acción marcable del menú *Herramientas* arranca un
  servidor TCP en `127.0.0.1`, en un puerto libre, con un token aleatorio
  (`QTcpServer`, en el hilo de Qt).
  - Lo anuncia en `~/.ogr-slip2d/bridges/<pid>.json`, legible solo por el
    usuario.
  - El archivo se borra al apagarlo o cerrar la ventana. Si una ventana
    muere sin avisar, su archivo se limpia la próxima vez que alguien busca
    ventanas.
- **En el servidor MCP**, `--attach [PID]` no abre un `Workspace` propio.
  Reenvía cada herramienta como `(operación, argumentos)` al puente.
  - Sin PID, se conecta a la única ventana con el puente activo.
  - Si hay varias, dice cuáles.
- **Protocolo** (`ogr_api/bridge.py`, solo biblioteca estándar): JSON por
  líneas. La primera línea es el saludo con el token; los bytes (un PNG)
  viajan en base64; un error llega como el mismo `OgrApiError` que habría
  dado la operación en local.

**Por qué TCP en *loopback* con token y no una tubería con nombre:**

- el cliente es `socket` puro en los tres sistemas;
- nada sale de la máquina;
- el token se exige en cada conexión, como exige AGENTS.md para el HTTP.

## 2. Qué significa «en vivo»

- **Un solo modelo.** El handle del puente lee `window.project` en cada
  llamada: *Nuevo* y *Abrir* en la ventana se ven al instante. Cuando la
  ventana cambia de modelo, los resultados y el espacio de `python_exec` del
  modelo anterior se descartan.
- **Una sola pila.** `handle.stack` es `window.command_stack`. Cada edición
  del agente es un paso de *Deshacer* de la ventana, y el agente puede
  deshacer los pasos del usuario.
- **Todo en el hilo de Qt.** El servidor TCP entrega por el bucle de
  eventos: una edición del agente y una del usuario nunca compiten. Tras
  cada edición se redibuja el lienzo.
- **`Busy` mientras la ventana calcula.** Un *Compute* o un barrido de
  desembalse usan el modelo vivo en otro hilo, así que una edición en ese
  momento se niega.
- **Un análisis del agente se ve.** Aparece en el panel y en el lienzo, como
  un *Compute*, si el modelo sigue siendo el analizado.
- **`project_new` y `project_open` abren en la ventana.**
  - Se niegan si hay cambios sin guardar: el agente no decide tirar el
    trabajo del usuario.
  - `project_close` se niega sobre el modelo de la ventana.
- **`model_render(source="window")`** es una captura del lienzo real. Fuera
  del puente se rechaza con el motivo.

## 3. Tres defectos que bloqueaban compartir la pila

- **A2** (reportado en v0.1.194). Deshacer el borrado de un contorno lo
  devolvía **al final** de la lista, no a su sitio. Ahora recuerda el
  índice.
- **Un handle con proveedor guardaba la ruta del modelo anterior.** Tras
  *Abrir* en la ventana, `project_save` sin ruta habría escrito el modelo
  nuevo **sobre el archivo del viejo**. La ruta se lee ahora de
  `project.file_path`.
- **Deshacer una instantánea del agente revertía ediciones de la interfaz
  hechas sin comando.** Hay 27 sitios de la interfaz que editan sin pasar
  por un comando: materiales, cargas, ajustes...
  - `SnapshotCommand` restaura ahora solo los atributos que siguen como
    los dejó: una fusión de tres vías por atributo.
  - Los que otra mano cambió después se conservan y se nombran en
    `cmd.kept`.
  - Sin nada en medio, que es el caso normal, hace exactamente lo de antes.

De paso: `Project._notify("saved")` volvía a marcar el proyecto como
modificado justo después de guardarlo (reportado en v0.1.194). Con el
puente, eso habría impedido abrir un archivo sobre una ventana sin nada que
perder.

## 4. El agente lo sabe

La guía que lee el agente (`ogr://guide`) gana la sección *Attached to a
window*. En ella se le explica:

- que el modelo es el del usuario;
- que sus pasos y los del usuario comparten *Deshacer*;
- que no puede abrir otro modelo sobre cambios sin guardar;
- qué significa `E_BUSY`;
- cómo pedir la captura.

`server_info` dice si está conectado a una ventana (`attached_to_window`).

## 5. El runner: una prueba que llama a `sys.exit` ya no corta la suite

Medido al preparar v0.1.202: la suite entera se detuvo al 44 %, sin totales.
El archivo de tests de esta versión ya estaba en `tests/`, y una de sus
pruebas llamaba a `main(["--attach"])` sobre un código que aún no conocía la
opción. argparse respondió con `sys.exit(2)`, que es `BaseException`. El
bucle del runner capturaba solo `Exception`, así que la salida lo atravesó y
terminó el proceso: todos los archivos siguientes se quedaron sin correr. No
era un falso verde, porque el código de salida era 2 y faltaban los totales,
pero se perdió una corrida entera por una sola prueba.

Ahora cada prueba pasa por `run_test`, que trata `SystemExit` como un fallo
de esa prueba, con su motivo. `KeyboardInterrupt` sigue parando la corrida.

## 6. Tests

`tests/test_live_bridge_v1203.py`, con la ventana real en `offscreen` y el
cliente en un hilo:

- el protocolo y el descubrimiento;
- sin token, se rechaza;
- una edición del agente se deshace con el *Deshacer* de la ventana;
- `project_open` nunca abre sobre cambios sin guardar;
- `Busy` durante un cálculo de la interfaz;
- la captura del lienzo, y su rechazo sin ventana;
- A2 y la fusión de tres vías;
- guardar deja el proyecto sin cambios pendientes;
- `--attach` sin ventana sale con código 2;
- el reenvío MCP → puente de todas las herramientas: el test «cada parámetro
  llega a su operación» se reutiliza con el `call` del puente (sus valores,
  ahora `_value` a nivel de módulo en `test_mcp_server_v1195`).

`tests/test_runner_exit_v1203.py`: `SystemExit`, una aserción y una excepción
dentro de una prueba son fallos de esa prueba, cada uno con su motivo, y el
bucle del runner pasa por `run_test`.

**Verificación:** la suite entera, sin filtros, pasa **4534 de 4534**.
