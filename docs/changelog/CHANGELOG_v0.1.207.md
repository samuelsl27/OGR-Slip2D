# OGR Slip2D v0.1.207

**Si el programa está abierto, lo que hace el agente se hace en su ventana,
por defecto y desde cualquier cliente.** Es decisión del propietario
(2026-09-25): «por defecto, en cualquier tipo de configuración, si pides que
haga algo, que lo muestre si tiene el programa abierto».

## Qué pasaba

Probado con Claude Desktop: el agente construía y calculaba un talud, y en
el programa abierto no se veía nada. El servidor trabajaba con modelos
propios salvo que se arrancara con `--attach`, y `--attach` tenía dos
problemas:

- **Se negaba a arrancar** si no había ya una ventana con el puente
  encendido.
- **Dependía del orden.** Abrir Claude antes que el programa dejaba el
  servidor muerto toda la sesión. Además, había que encender el puente a
  mano cada vez que se abría el programa.

Por eso decidía la configuración del cliente, y por defecto no se veía nada.

## Qué cambia

- **El servidor elige solo, en cada llamada** (`ogr_api.bridge.WindowRouter`,
  el modo por defecto de `ogr-slip2d-mcp`):
  - si hay una ventana de OGR Slip2D abierta, la llamada va a ella, a la más
    reciente si hay varias;
  - si no la hay, va a los modelos propios del servidor, como antes.
- **La ventana se busca cuando hace falta.** El orden en que se abran el
  programa y el cliente ya no importa.
  - Una ventana cerrada se detecta **antes** de enviar la llamada siguiente
    (`BridgeClient.alive`, que mira el socket sin enviar nada), así que esa
    llamada va donde debe.
  - Si el programa se vuelve a abrir, se encuentra de nuevo.
- **Lo que es del servidor sigue siendo suyo.** Una llamada con un
  `project_id`, `job_id` o `result_id` del servidor va a él aunque haya
  aparecido una ventana: un modelo empezado antes no se pierde.
- **Una llamada que la ventana estaba contestando cuando se cerró no se
  repite** en otro sitio. No se puede saber si llegó a ejecutarse, y una
  edición aplicada dos veces es peor que un error.
- **El programa enciende el puente al abrirse**
  (`ogr_gui.__main__.start_window`).
  - `--no-agent-bridge` lo deja apagado, y el menú lo apaga en la sesión.
  - Los tests que construyen `MainWindow` directamente no lo encienden.
- **El `--workdir` del servidor llega a la ventana** en el saludo del
  puente. Una ruta relativa significa la misma carpeta allí que en el
  servidor. Antes, en la ventana no había carpeta y las rutas tenían que ser
  absolutas.
- **Opciones del servidor:**
  - `--headless` no usa nunca la ventana: el comportamiento anterior;
  - `--attach [PID]` usa solo ventanas, ya no falla al arrancar sin
    ninguna, y sin ventana cada llamada dice qué abrir;
  - `--attach` y `--headless` juntas se rechazan.
- **`server_info` dice a dónde va la siguiente llamada**
  (`attached_to_window.next_call_goes_to`), y cada modelo de `open_models`
  dice si está en la ventana.
  - La guía del agente y sus instrucciones cortas lo explican.
  - Muchos clientes no leen la guía, por eso la frase va también en las
    instrucciones.

## Lo que había que proteger

- **Los tests nunca ven tu ventana.** Con el modo por defecto nuevo, un test
  que arranca un servidor como proceso buscaría ventanas en tu carpeta de
  usuario, y con el programa abierto durante la suite editaría tu modelo. El
  runner da ahora a toda la corrida, procesos hijos incluidos, una carpeta
  de descubrimiento vacía propia (`OGR_BRIDGE_DIR`), y un test lo comprueba.
- **La documentación de v0.1.203 decía algo falso**: que `project_new` y
  `project_open` abrían sobre cambios sin guardar con
  `discard_changes=true`. Ese parámetro solo existe en `project_close`;
  abrir sobre cambios sin guardar se niega siempre.
- **La ruta de Claude Desktop de la Microsoft Store**: su configuración vive
  en `%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\`, y no
  en `%APPDATA%\Claude\`. La guía de clientes lo dice ahora.

## Tests

`tests/test_window_by_default_v1207.py`:

- **El router, con ventanas simuladas:**
  - sin ventana, al modelo propio;
  - con ventana, a ella;
  - lo que es del servidor, al servidor;
  - una ventana cerrada se nota antes de la llamada siguiente, y una
    reabierta se encuentra;
  - una llamada cortada a medias no se repite;
  - `--attach` sin ventana dice qué abrir.
- **Con una ventana real:**
  - el programa arranca su puente, y `--no-agent-bridge` lo deja apagado
    (regla 7);
  - el servidor por defecto edita la ventana (un paso de *Deshacer* allí) y
    guarda `rel.ogr` en su `--workdir`.
- **La línea de órdenes:** las contradicciones se rechazan, y la corrida no
  ve la carpeta de ventanas del usuario.

`test_live_bridge_v1203::test_attaching_to_no_window_says_so` cambia con el
comportamiento: `--attach` ya no falla al arrancar, y lo que avisa es la
llamada.

**Verificación:** la suite entera, sin filtros, pasa **4557 de 4557** en Windows con Python 3.14. La CI de v0.1.206 quedó en verde en las tres versiones de Python (4546 pasados y 1 saltado, el del banco); la de este commit, en su corrida.
