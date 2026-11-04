# OGR Slip2D v0.1.419

**Las listas de superficies van en el orden en que se elige la crítica: primero las admisibles, después las que las
comprobaciones rechazan, marcadas con su motivo. La primera fila del panel de resultados y de la tabla *Superficies*
de Interpretar es la crítica, y `rank=1` del API también (D361).**

Es la tercera de la tanda P8o. La ficha sale de la sexta prueba de la interfaz (H9 y H10 de
`INFORME_prueba_GUI_0.1.357.md`). **Decisión de la propietaria (2026-11-03):**
- una sola regla, en el motor: las admisibles primero y las demás detrás, marcadas;
- el API, con el mismo orden y `admissible` en cada fila.

Ningún número cambia: `critical` y `min_fos` son los de antes.

## 0. Lo que se encontró

- **`SearchResult.top_n`** ordenaba por la puntuación todas las superficies que convergen, admisibles o no.
  **`critical`** descarta las no admisibles, y solo si ninguna lo es vuelve a todas.
  - En el ejemplo 2 de Hammah et al. (2005) con el recocido simulado, la crítica es 0,9442. La primera de `top_n` era
    0,7911, rechazada por m-alfa en 3 dovelas.
- **Sus lectores:**
  - el panel de resultados, que resaltaba en negrita su fila 0 como la crítica, bajo una cabecera que daba la otra;
  - la tabla *Superficies* de Interpretar y su selección por fila;
  - el API: `results_get(view="top")` y `results_query(view="slices", rank=k)`.
  - La estadística y el lienzo usan `valid()` y no se ven afectados.
- **Centro y radio:** sin círculo, el panel escribía «nan» (el valor por defecto de `sd.get`) e Interpretar «0.00»,
  en la tabla y en el *Resumen*.
- **Un caso barato que lo reproduce, buscado al escribir el test:** el talud de ejemplo con Bishop y dos superficies
  sin círculo.
  - Una es tendida y admisible, con FS 1,4135.
  - La otra tiene una salida que sube a 74°, y la criba de m-alfa del motor la rechaza en 2 dovelas («m_alpha < 0.2
    on 2 slice(s)»), con FS 0,8621, más baja.
  - Con 0.1.418, el panel la ponía primera y en negrita.
- **Sin ficha, no se toca:** la señal `ResultsDock.surface_selected` no está conectada a nada, así que pulsar una
  fila del panel de la ventana principal no hace nada.

## 1. Qué cambia

- **`ogr_slip2d/search.py`:** `top_n` ordena con la clave `(no admisible, puntuación)`, la regla de `critical`.
  - `sorted` es estable y `min` devuelve el primero de los iguales, así que un empate se resuelve igual en los dos.
  - Por eso `top_n(1)[0] is critical` siempre que haya crítica, también cuando ninguna es admisible y con el
    objetivo Ky.
- **`ogr_slip2d/interpretation.py`:** `slip_circle(surface_dict)`, que da centro y radio con la regla de
  `slip_centre`: una superficie de capa débil, por su base.
- **`ogr_gui/labels.py`:** `circle_cells(surface_dict)`, los tres textos de una tabla, con «—» si no hay círculo.
- **El panel de resultados** (`ogr_gui/widgets/results_dock.py`) **y la tabla *Superficies*** de Interpretar:
  - una última columna, «Nota». Para una superficie rechazada, la etiqueta corta del motivo
    (`core_messages.invalid_label`), con el texto entero de ayuda (`invalid_text`), y la fila con la tinta `muted`
    del tema;
  - centro y radio por `circle_cells`;
  - el panel resalta la fila de `critical` (antes, la fila 0).
- **El *Resumen* de Interpretar:** centro y radio por `circle_cells`. Su plantilla recibe los textos, y la clave cambia
  con su castellano: `({10}, {11})` y `Radius: {12}`, con la «m» solo si hay radio.
- **El servidor MCP:** las descripciones de `view="top"` («the n most critical surfaces: the admissible ones first…»)
  y de `rank` («the n-th surface in the order of results_get's 'top' (1 is the critical…)»), que decían «n best» y «the
  n-th lowest».
- **`tests/test_surface_ranking_v1419.py`,** nuevo.
- El número en los nueve sitios y el contador de los dos README.

- **Sin ficha, no se toca:** la etiqueta castellana del motivo de m-alfa dice «m_alpha < 0.2 en … dovela(s)», con el
  identificador del motor, donde el resto del castellano escribe «m-alfa» (12 veces). La congela
  `test_core_messages_v1333`.

## 2. Qué se probó

- **`tests/test_surface_ranking_v1419.py`,** con 9 tests:
  - **la ley,** sobre grupos hechos a mano: las admisibles por puntuación y después las demás. `top_n(1)[0] is
    critical`, también sin ninguna admisible, en un empate y con el objetivo Ky. Las inválidas no se listan;
  - **el par real** del motor: 1,4135 admisible y 0,8621 rechazada por m-alfa. Lo comprueba con su tolerancia y lo
    cita la cabecera;
  - **el panel de resultados,** en castellano:
    - la fila 0 es la crítica, en negrita;
    - la otra, sin negrita, con su motivo («m_alpha < 0.2 en … dovela(s)») y el texto entero de ayuda;
    - «—» en centro y radio;
  - **Interpretar:**
    - la tabla en el mismo orden;
    - pulsar la fila 0 elige la crítica;
    - el *Resumen* dice «(—, —)» y no «0.00»;
  - **el API:** `results_get(view="top")` en ese orden con `admissible` [True, False], y
    `results_query(view="slices", rank=1)` lee la crítica (el API redondea el FS a 6 decimales).
- **La discriminación,** con el árbol de 0.1.418 y el test copiado: **fallan 7 de 9**. Pasan las dos guardas que
  también valían antes: las inválidas no se listan, y si ninguna es admisible la primera ya era la crítica.
- **Los vecinos:**
  - cabeceras y nombres, Interpretar, el panel;
  - el API de resultados y su render, `results_query`, el servidor MCP;
  - los mensajes del núcleo, la interpretación;
  - los tests que construyen resultados a mano (población de la ruta, error de la criba, sin número, sismo, tablas
    de materiales);
  - los mínimos por centro, las superficies del usuario.
  - En total, 316 de 316.
- **La suite entera con `--jobs 4`:**
  - la primera dio 7086 de 7088. Hubo dos fallos:
    - `test_gui_spanish_v1318::test_the_results_panel_headers` congelaba las seis cabeceras del panel. Es un
      **cambio deliberado**: ahora son siete, con «Nota» («Note»);
    - `test_api_jobs_v1194::test_progress_is_written_and_ends_complete`: el `progress.json` acabó sin su última
      actualización. Es **D371**, abierta en P8, que falla así cuando la máquina va cargada; solo pasa. No es de la
      tanda;
  - la segunda: **7088 de 7088**, `Failed: 0`, sin `Leaks` ni `Chunks died`.
  - La serie no toca: 20 commits desde la última.
- **El banco:**
  - `d361()`, nueva en el `verificar_cierres.py` de la raíz, mide el par real en el panel, en Interpretar y en el API.
    - Con 0.1.418 da SIGUE ABIERTO en los cuatro puntos: panel, Interpretar, `rank=1` y centro y radio.
    - Con 0.1.419 da CUBIERTO POR TEST.
  - El VC de la raíz entero da 129 comprobaciones con 0 bajadas.
  - **El del 02, entero, porque se toca el motor:** 242 defectos, 0 bajadas apartadas, ninguna línea de cambio de
    veredicto.
  - Nada del banco lee `top_n`, salvo `repro_d361.py` y `d345()` de la raíz. `d345()` compara la primera fila de la
    tabla con `top_n(1)`, que es coherente con el cambio, y no baja.
  - D361 se cierra:
    - instantánea y retirada;
    - `PAQUETES` podado y la cadena tachada;
    - 37 prompts, con las 17 FALTA anteriores;
    - auditorías con 0 ERROR;
    - instantánea `--forzar`.

## 3. Qué falta

- **A mano:** la C.3 de `PROMPT_prueba_GUI_0.1.357.md`, con el recocido simulado del ejemplo 2 de Hammah: la primera
  fila tiene que ser la crítica. Va en el prompt de la prueba a mano del final de la tanda.
