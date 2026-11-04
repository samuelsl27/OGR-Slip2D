# OGR Slip2D v0.1.420

***Consultar datos de dovela* es un modo con un solo dueño de los clics. Entra por el menú y sale con Esc, con el
mismo menú o con otra consulta. Las dovelas se numeran desde 1 en todo lo que se ve (D360).**

Es la cuarta de la tanda P8o. La ficha sale de la sexta prueba de la interfaz (H1 y H2 de
`INFORME_prueba_GUI_0.1.357.md`). **Decisión de la propietaria (2026-11-03):** las dovelas van desde 1 en pantalla:
en el panel, su Copiar, la barra y el diagrama de fuerzas. El `index` del motor sigue desde 0 en el API y en el CSV
que exporta Interpretar, que son datos.

Ningún número cambia, ni ningún dato de la tabla de la dovela salvo su número. Elegir una superficie pulsando la
rejilla, con la consulta apagada, funciona como antes, y *Añadir consulta* también.

## 0. Lo que se encontró

- **Dos manejadores de `scene_clicked` a la vez.**
  - `_on_canvas_click_default` elige la mejor superficie de la celda de la rejilla bajo el clic y pone su dovela 0 en
    el panel. Se conectaba al crear la ventana. Su docstring decía «cuando la consulta NO está activa», pero nada lo
    comprobaba.
  - `_on_canvas_click_for_query` se conectaba la primera vez que se abría la consulta y no se desconectaba nunca.
- **Ningún modo.** La consulta no tenía estado: una vez abierta, cada clic iba también a ella para siempre.
- **El Esc.** El de la ventana solo salía de *Añadir consulta*, y además el lienzo se queda el Esc cuando tiene el
  foco: pone Seleccionar y acepta el evento (`canvas_view.py`). Así que, con el foco en el lienzo, tampoco se salía de
  *Añadir consulta* con Esc. El test que lo probaba llamaba a `keyPressEvent` de la ventana directamente.
- **Medido con `repro_d360.py`** (Hammah et al. 2005, ej. 1, Bishop, rejilla 6 × 6 con 4 radios, 50 dovelas), y
  repetido por el test nuevo en el árbol de 0.1.419:
  - fuera de rango, el panel enseñaba la dovela 0 de otra superficie, que pasaba a ser la elegida;
  - de las 50 dovelas pulsadas en su centro, las 11 últimas (de la 40 a la 50) movían además la selección;
  - tras Esc, una pulsación en una dovela la seguía consultando («Slice 25 of 50»);
  - la última era «Slice 49 of 50», y el diagrama de fuerzas pedía un índice de 0 a 49.
- **La numeración:** desde 0 en el panel, la barra y el diagrama de fuerzas; desde 1 en el gráfico a lo largo de la
  superficie y en la tabla del PDF.

## 1. Qué cambia

- **`ogr_gui/canvas/canvas_view.py`:** una señal nueva, `escape_pressed`. Se emite cuando el Esc no tenía nada del
  lienzo que cancelar (un arrastre, una transformación o un dibujo a medias), justo cuando el lienzo vuelve a
  Seleccionar.
- **`ogr_gui/interpret_window.py`:**
  - **un solo dueño de los clics**, `_on_scene_clicked`, conectado una vez. Con la consulta de dovelas puesta, y sin
    *Añadir consulta*, el clic va a la consulta; si no, al manejador de siempre, que sigue llevando también *Añadir
    consulta*. Es el patrón de `_on_segment_picked` de la ventana principal (D308). Ya no existen la segunda
    conexión ni la bandera `_slice_pick_connected`;
  - **el modo:** `_slice_query_active` y una entrada del menú marcable, «Consultar datos de dovela» (sin «...»,
    porque es un modo y no un diálogo).
    - Se sale con Esc (el de la ventana y el del lienzo, por `escape_pressed`), con la misma entrada, con cualquier
      otra consulta del menú Consulta (las siete llaman a `_leave_slice_query` al empezar) y con Medir o Acotar (al
      cambiar el lienzo de modo).
    - La barra lo dice al entrar, con el mensaje de siempre, y al salir: «Consulta de dovelas terminada.»;
  - **Esc**, en `keyPressEvent` y desde el lienzo, pasa por `_leave_query_modes`, que sale de *Añadir consulta* o de
    la consulta de dovelas, la que esté puesta;
  - **desde 1:**
    - la fila «Número de dovela» del panel enseña `s.index + 1`, y Copiar copia lo que enseña;
    - la barra dice «Dovela %d de %d» con `index + 1`;
    - el diagrama de fuerzas pide «Número de dovela:» de 1 a n y lo pasa a `idx - 1`, y su título y su pie dicen
      `idx + 1`.
- **`ogr_gui/i18n/__init__.py`:** «Consultar datos de dovela», «Consulta de dovelas terminada.» y «Número de
  dovela:».
- **`tests/test_slice_query_mode_v1420.py`,** nuevo, con 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_slice_query_mode_v1420.py`**, con la ventana entera mostrada y el modelo de `repro_d360.py`. El
  cálculo es una rejilla de 245 círculos, sin pool, y se comparte entre los casos:
  - fuera de las dovelas, ni el panel ni la selección cambian;
  - ninguna de las 50 dovelas pulsadas en su centro mueve la selección;
  - un Esc mandado al lienzo con `QTest` sale del modo:
    - una dovela pulsada después ya no se consulta;
    - la entrada se desmarca;
    - la rejilla vuelve a elegir la superficie de su celda;
  - la misma entrada y *Añadir consulta* salen del modo;
  - la última es «Slice 50 of 50», con «50» en el panel y «1» en la primera; el `index` del motor sigue en 0;
  - el diagrama de fuerzas pide de 1 a 50.
- **La discriminación,** con el árbol de 0.1.419 y el test copiado: **fallan los 6**, por comportamiento.
  - El primer borrador entraba en el modo por la acción nueva, y en el árbol viejo fallaba por su ausencia. Ahora
    entra por `_query_slice()` cuando no hay acción marcable.
  - Así repite las medidas de la ficha: las dovelas 40 a 50 movían la selección, «Slice 49 of 50», Esc sin efecto y
    de 0 a 49.
- **Los vecinos:** Interpretar y sus consultas, el panel de la dovela y sus botones, el diagrama de fuerzas, el Esc
  y el modo del lienzo, Medir y Acotar, las ayudas, el castellano y el catálogo: 244 de 244.
  - `test_slice_panel_buttons_v191`, que el plan esperaba cambiar a propósito, pasa sin tocarlo: compara la celda con
    lo que da el propio campo.
- **La suite entera con `--jobs 4`:** **7094 de 7094**, `Failed: 0`, sin `Leaks` ni `Chunks died`. La serie no toca.
- **El banco:**
  - `d360()`, nueva en el `verificar_cierres.py` de la raíz, mide lo mismo que `repro_d360.py`.
    - Con 0.1.419 da SIGUE ABIERTO: fuera de rango cambia el panel, 11 de 50 clics mueven la selección, Esc no sale
      del modo y la última es «Slice 49 of 50».
    - Con 0.1.420 da CUBIERTO POR TEST: sin cambios, 0 de 50, Esc sale y «Slice 50 of 50».
  - El VC de la raíz entero da 130 comprobaciones con 0 bajadas.
  - El del 02 en seco da 242 de 242 iguales a los archivados.
  - D360 se cierra:
    - instantánea y retirada;
    - `PAQUETES` podado y la cadena tachada;
    - 36 prompts, con las 17 FALTA anteriores;
    - auditorías con 0 ERROR;
    - instantánea `--forzar`.

## 3. Qué falta

- **A mano:** la B.3 de `PROMPT_prueba_GUI_0.1.357.md`, con el ratón y el teclado reales: una pulsación fuera de rango
  y Esc. Va en el prompt de la prueba a mano del final de la tanda.
