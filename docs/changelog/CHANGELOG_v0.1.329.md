# OGR Slip2D v0.1.329

**Los procesos de cálculo ya no abren ventanas, el idioma cambia también los textos de Qt en el
momento, y el talud de ejemplo declara la dirección de su geometría (D326, D327, D328).** Sexta versión
de la tanda P8i.

## 0. Lo que se encontró

- **D326, las consolas (H11).**
  - Arrancado sin consola, como en la prueba, y como con un acceso directo, calcular ponía tres o cuatro
    ventanas de terminal delante del programa, una de ellas maximizada en la estadística, que robaban
    el foco.
  - En Windows, un proceso sin consola que arranca hijos con `python.exe` les da a cada uno una consola
    propia. Arrancado desde una terminal, los hijos comparten la suya y no pasa nada.
  - El único pool del programa es el de la búsqueda por rejilla (`ogr_slip2d/search.py`).
  - La estadística no tiene otro. Su búsqueda determinista es esa misma, y en un análisis de «Talud
    completo» busca de nuevo en cada muestra.
  - **`pythonw.exe`**, que está junto a `python.exe`, es el mismo intérprete sin consola.
  - **Encontrado al escribirlo, y reportado antes de tocarlo: no es solo la ventana.**
    - Los trabajos del API, que el servidor MCP lanza para un agente, arrancan su proceso con
      `CREATE_NO_WINDOW`. Medido con un proceso arrancado así: `GetConsoleWindow()` da 0.
    - Sus búsquedas en paralelo abrirían también una consola por proceso, y lo mismo un servidor MCP
      arrancado sin consola.
    - El plan lo aplicaba solo al arrancar la ventana.
- **D327, el idioma de los avisos (H10).**
  - El catálogo de Qt de D302 (los botones estándar) se instalaba una vez, al arrancar, con el idioma
    guardado.
  - Al pasar a inglés, el aviso «Language changed…» salía con «Aceptar», y el «¿Guardar antes?» de
    después con «Guardar / Descartar / Cancelar».
  - **La trampa de la regla 5:** `test_language_saved_v1289` elige castellano en la ventana. Con el
    catálogo cambiando al momento, su `_Fresh` lo habría dejado instalado, y
    `test_qt_translations_v1292` habría leído «&Sí» donde espera «&Yes».
- **D328, la dirección del ejemplo (H5, ya visto al cerrar D305).**
  - El ejemplo no declaraba dirección, así que tomaba la de los ajustes por defecto, «De derecha a
    izquierda», que pone la coronación a la derecha. Su terreno es más alto a la izquierda (y = 25 frente
    a 15).
  - Cada cálculo lo advertía (`_failure_direction_note`), y la MCP en cada `settings_get` o
    `settings_set`.
  - **Leído en el código:** la declaración la leen el empuje del agua de una grieta de tracción, el
    sentido de un soporte y la cara de partida de la búsqueda por trayectoria. El ejemplo no tiene
    ninguno de los tres, así que su FS no puede depender de ella.

- **Medido antes de cambiarlo,** el ejemplo entero con las dos declaraciones, en el mismo proceso
  (`run_analysis`, los métodos que trae activos):

  | Declaración | Bishop simplificado | Janbu simplificado | Aviso |
  |---|---|---|---|
  | De derecha a izquierda (la de antes) | 1,0914331494631124 | 1,0434262254619202 | sí |
  | De izquierda a derecha | 1,0914331494631124 | 1,0434262254619202 | no |

  Son idénticos hasta el último bit y con el mismo círculo crítico (Bishop en (37,5; 31,67), R 16,54).
  Lo que cambia es el aviso.

## 1. Qué cambia

- **D326, por decisión de la propietaria: donde se crea el pool.**
  - **`ogr_slip2d/processes.py`** (nuevo, sin Qt):
    - `child_executable` decide el intérprete de los procesos de cálculo. Es `pythonw.exe` solo en
      Windows, sin consola (`GetConsoleWindow() == 0`), fuera de un ejecutable congelado y si existe
      junto al intérprete; en cualquier otro caso, nada cambia;
    - `windowless_children` se lo pasa a `multiprocessing.set_executable`.
  - La búsqueda lo llama justo antes de crear su `ProcessPoolExecutor`. Así cubre la ventana, el
    servidor MCP, sus trabajos y los scripts, arranquen como arranquen.
  - Cuesta una llamada al sistema y una comprobación de archivo por pool.
- **D327, por decisión de la propietaria: el catálogo cambia al momento.**
  - **`ogr_gui/qt_catalog.py`** (nuevo):
    - `install_qt_translator`, que se muda aquí y sigue importable desde `ogr_gui.__main__`;
    - `switch_qt_translator`, que pone el catálogo del idioma nuevo en lugar del que instaló antes, y no
      encima;
    - `reset_qt_translator`, para quitarlo.
  - `apply_saved_preferences` instala el del arranque con `switch_qt_translator`.
  - `_apply_language` cambia el catálogo **antes** del aviso.
  - **`test_language_saved_v1289`:** su `_Fresh` lo quita al salir.
- **D328, por decisión de la propietaria:** `build_demo_project` declara «De izquierda a derecha».

## 2. Tests

`tests/test_console_language_demo_v1329.py` (nuevo):

- **D326:**
  - sin consola en Windows, el intérprete es el `pythonw.exe` de al lado;
  - con consola, en otro sistema, congelado o sin `pythonw.exe`, nada cambia;
  - es lo que arranca `multiprocessing`, y se devuelve el de antes (regla 5);
  - la búsqueda lo pide una vez antes de su pool;
  - **con el `pythonw.exe` real y el pool real**, la búsqueda repartida de `test_parallel_search_v197`
    da las mismas evaluaciones, en el mismo orden y hasta el último bit, que la secuencial, sin volver a
    un solo proceso. En un sistema sin `pythonw.exe`, se salta.
- **D327:**
  - elegir castellano y después inglés deja «&Sí» y «&Yes», y el aviso de cada vez sale ya en el idioma
    elegido;
  - un cambio sustituye al anterior y no se apila;
  - al terminar no queda nada instalado.
- **D328:**
  - el ejemplo declara «De izquierda a derecha», que es lo que dice su geometría, y calcularlo no da el
    aviso;
  - su FS con las dos declaraciones, en un mismo proceso, es idéntico para cada método.

**Con el código de 0.1.328 fallan 8 de los 9 casos.** El que pasa en los dos árboles es la identidad
de las dos declaraciones, que por construcción da lo mismo antes y después. Se corrió sobre un
`git archive` de 0.1.328, sin el buscador editable.

## 3. Verificación

- **El test de esta versión**, 9/9. Los dos tests del idioma en el orden en que se habría visto la
  fuga (`language_saved` antes que `qt_translations`), 11/11.
- **Los vecinos**, 657/657 en 46 archivos:
  - el ejemplo y la dirección de rotura;
  - el servidor MCP, el API, la línea de órdenes, los ajustes y el informe;
  - el idioma y el catálogo de Qt;
  - el paralelo, la búsqueda, la estadística y la rejilla de la ventana.
- **Suite entera:** 6208/6208, `EXIT=0`, 85 min.
- **Banco:**
  - `verificar_cierres.py` entero: 77 comprobaciones, D326, D327 y D328 **CUBIERTO POR TEST**.
  - **La primera corrida apartó una bajada: D302**, de CUBIERTO a SIGUE ABIERTO. Su comprobación buscaba
    `install_qt_translator` en `ogr_gui/__main__.py` y la llamada del arranque con su forma vieja. La
    busca ahora también en `qt_catalog.py`, y acepta la llamada nueva. La segunda corrida da 0 bajadas.
    Es lo mismo que D289 en 0.1.328.
  - instantánea `Evaluaciones/0.1.329`, las tres fichas retiradas y podadas de P8;
  - prompts (35, que ya cuentan D332, abierta en esta tanda);
  - auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia.** D328 lo ha medido hasta el último bit, y D326 lo comprueba con el
  `pythonw.exe` real.

## 4. Pendiente

- **D329** (resto de P8i: *Medir*, *Acotar longitud* y las capas de agua de *Interpretar*), y D314
  después.
- **A mano, en la cuarta prueba de la interfaz:**
  - un arranque sin consola (un acceso directo a `pythonw -m ogr_gui`, o desacoplado) y calcular;
  - cambiar de idioma y ver el aviso y el «¿Guardar antes?» siguiente;
  - el ejemplo sin aviso de dirección.
