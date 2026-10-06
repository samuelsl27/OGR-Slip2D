# OGR Slip2D v0.1.261

**Una rejilla circular con los dos juegos de Slope Limits solapados se
rechaza con su razón (D262). Los rechazos por los límites y los círculos que
no cortan el terreno se cuentan por su nombre, y una búsqueda que termina sin
ninguna superficie válida lo dice (D263). Y la rejilla en paralelo devuelve
las notas, los contadores y el progreso de sus procesos (D255).**

Las tres salieron de la tercera medida de D243, el problema 109 del banco
frente al manual (2026-10-06). Las tres eran silencios: un ajuste que no
filtraba nada, un filtro que lo filtraba todo y un modo de cálculo que tiraba
lo que los otros dos habrían dicho. **Ningún número cambia.**

## 0. Lo que se encontró

### El punto de partida: el segundo juego de límites del 109

- **El enunciado** pone «a second set of limits … at the bottom of the wall
  (14.473, 5.456) and the top of the slope (18, 9) to filter out smaller slip
  surfaces».
- **El banco lo había leído como una ventana**, 14,473..18, sobre un primer
  juego que cubre todo el modelo (0..30). Es la lectura (a).
- **La ayuda de la referencia** dice que los dos juegos son «allowable ranges
  for the starting and ending points». Con (a), la unión de los dos rangos es
  todo el contorno y **no se filtra nada**, contra el propio «to filter out»
  del enunciado.
- **La lectura con sentido sería la (b):** arranque en 0..14,473 y final en
  18..30.
- **Se mantiene (a)**, por decisión de la propietaria: la figura 109.2 dibuja
  superficies que afloran en la cara, así que la corrida publicada no las
  filtró.

Midiendo las dos lecturas salieron los tres defectos.

### D262: con la segunda ventana dentro de la primera, la rejilla no genera ningún círculo

Con Bishop, en la rejilla 10 × 10 de 10 radios sobre la ventana del 108:

| límites | F | círculo |
|---|---|---|
| ninguno | 1,8058 | (15,4; 11,0; 6,897) |
| solo 0..30 | 1,8058 | el mismo |
| 0..30 + 14,473..18 (lectura (a)) | **ninguno válido, sin una sola nota** | — |
| 0..14,473 + 18..30 (lectura (b)) | 1,9927 | (15,4; 13,0; 9,108) |

- **La causa.** `GridSearch._radius_bracket_two_windows` (D77) genera en cada
  centro los radios de los círculos que entran por una ventana y salen por la
  otra. Da cada cruce del terreno a la PRIMERA ventana que lo contiene, con
  las ventanas ordenadas por su límite izquierdo. Con una ventana dentro de
  otra que empieza más a la izquierda, ningún cruce es de la interior: en
  cada centro se emite el radio tangente degenerado, que no corta el terreno.
- **Con solape parcial** el tramo común va siempre a la ventana que empieza
  más a la izquierda, algo que nada medido respalda.
- **D77 midió la regla solo con ventanas separadas** (los muros 87–94), y qué
  hace la referencia con ventanas solapadas no está medido en ningún sitio.

### D263: el filtro de límites rechazaba sin dejar rastro

Con la lectura (b), la Block Search del 109 daba **0 válidas de 5000, sin
una sola nota ni una evaluación**.
- **Instrumentada:** 3804 superficies caían en el filtro de extremos, con el
  extremo izquierdo en la cara (x de 14,57 a 15,65). Con 135–225°, ningún
  rayo izquierdo desde una junta pasa bajo el pie del muro. El rechazo es
  correcto; el silencio, no.
- **Las tres puertas del filtro callaban.** Son el filtro común
  (`_best_of_masses`), el prefiltro de la Block Search y el generador de la
  Path Search. Todo acababa en un `invalid_count` anónimo, que el censo de
  inválidas contaba como «no rebanadas».
- **La puerta de una sola superficie** culpaba a una superficie que «does
  not cut the model».
- **El círculo que no corta el terreno dos veces** tampoco tenía nombre, y es
  el −101 de la referencia con sus propias palabras: «Only one (or none) slip
  surface / slope intersections».
- **Ninguna búsqueda decía nada** al terminar sin ninguna superficie válida.

### D255: la rejilla en paralelo perdía todas sus notas

Medido en el mismo 109, rejilla 10 × 10 con Bishop:

| modo | F | notas | `_outside_model` | `_on_model_edge` |
|---|---|---|---|---|
| en serie | 1,805845 | 99 | 190 | 19 175 |
| en paralelo (por defecto desde 400 círculos) | 1,805845 | **0** | **0** | **0** |

- **La causa.** Los contadores de rechazo y las notas pendientes viven en el
  objeto de búsqueda, no en su resultado. Cada proceso trabaja sobre su copia
  serializada, y `_parallel_grid_run` solo sumaba los cinco campos del
  resultado parcial. `BaseSearch.run` leía los contadores en el padre, que no
  había evaluado nada.
- **El progreso** se quitaba para el viaje y solo se llamaba una vez, al
  final.
- **La ficha ya existía:** se abrió el 2026-10-04 al leer D247, con la medida
  pendiente. El plan de esta versión la llamó N4, como si fuera nueva, hasta
  que la memoria de la tanda la reconoció. Se cierra aquí sin D247, que queda
  sola.

## 1. Lo que cambia

### D262
- **`ogr_core/project/rules.py`:**
  - `slope_limit_windows` y `slope_limit_windows_overlap` dicen, en un solo
    sitio, si los dos juegos están separados, anidados o solapados en parte.
    El solape exige un tramo común de longitud positiva frente a 1e-9 del
    vano de las dos ventanas, así que dos ventanas que solo se tocan en un
    punto siguen separadas.
  - `slope_limit_windows_refusal` **rechaza la rejilla con ventanas
    solapadas**, con el texto que pide dos ventanas separadas o un solo
    juego. `check_analysis_settings` la llama.
- **`settings_warnings`:** en las demás búsquedas, cuando un juego está
  dentro del otro, una nota dice que como filtro no hace nada (regla 7). En la
  Path Search añade que la ventana más cercana al pie sigue eligiendo dónde
  arrancan las superficies. Con solape parcial no hay nota: la unión es más
  ancha que cualquiera de los dos y el ajuste actúa.

### D263
- **`search.py`:**
  - `REFUSED_OUTSIDE_SLOPE_LIMITS` y `REFUSED_MISSES_GROUND`, con su texto en
    `_REFUSAL_TEXT`;
  - los contadores `_outside_slope_limits` y `_misses_ground`, que suman en
    el filtro común (una vez por superficie, si no sobrevive ninguna masa), en
    el prefiltro de la Block Search, en el generador de la Path Search, en los
    tres descartes por caja de `evaluate_circle` y en el círculo sin cuerdas
    de `_candidate_surfaces`;
  - `SearchResult.outside_slope_limits` y `misses_ground`, tomados **antes**
    de la optimización y de las superficies del usuario, que pasan por las
    mismas puertas y añadirían superficies que la búsqueda no generó;
  - `_no_valid_surface_note`: solo cuando no queda ninguna superficie
    válida, porque el rechazo por un filtro es rutina. Dice lo que contó y
    que el resto no tiene motivo registrado.
- **`interpretation.invalid_summary`** cuenta los dos en −101, cada uno con su
  razón, como D244 y D256.
- **Fuera de alcance, y dicho en la nota.** Los demás prefiltros de la Block
  Search y los demás `None` del generador de la Path Search siguen sin
  nombre. Por eso la nota no pretende haberlo contado todo.

### D255
- **`_RUN_COUNTERS`**, una sola lista de los contadores que viven en la
  búsqueda. La leen `BaseSearch.run`, para ponerlos a cero, y la fusión en
  paralelo.
- **`_grid_batch`** devuelve, con el resultado parcial, los contadores y las
  notas de su lote, como diferencia sobre el lote.
- **`_parallel_grid_run`** los suma en el padre y une las notas en orden de
  lote, conservando la primera aparición, que es el orden de la corrida en
  serie. El progreso avanza a medida que terminan los lotes, en centros, como
  en serie.
- **Un error del propio `progress_cb`** se devuelve a quien llama y no se
  confunde con un fallo del pool, que sigue volviendo al cálculo en serie.

## 2. Caminos equivocados

- **«Depende del orden en que se escriban los juegos».** Así lo decían el
  primer borrador del texto de rechazo y el plan. Es falso:
  `_normalise_slope_limits` ordena los juegos por su límite izquierdo, y lo
  que decide es cuál empieza más a la izquierda. Lo destapó el test de la
  premisa, al escribirlo, antes de publicar nada.
- **N4 como ficha nueva.** Ver arriba: era D255.
- **La primera calibración de la identidad serie = paralelo no probaba
  nada.** Con la capa débil de juguete no salía ninguna nota, y la igualdad
  era verdadera en las dos versiones. Con el techo de ángulo de base a 40°
  salen unas cincuenta notas, una por cada superficie recortada que se
  descarta.

## 3. Tests

**`tests/test_slope_limit_refusals_v1261.py`, 16 casos:**
- **la regla de rechazo**, como tabla de verdad, y su premisa: la propia
  regla de D77 es degenerada en los 20 centros con la ventana interior, y no
  con las mismas anchuras separadas;
- **el rechazo en `run_analysis`** y la nota del juego anidado (Block y Path,
  y sus controles);
- **la Block Search de forma cerrada.** Desde un objeto punto en (25, 6), los
  rayos de 135–160° afloran entre x = 14,01 y 20,5: con la ventana fuera, 40
  de 40 rechazos con nombre, la nota de búsqueda vacía y el censo; con la
  ventana encima, ninguno;
- **la Path Search** con una sola ventana alrededor del pie;
- **la puerta de una sola superficie**;
- **los 27 círculos del muro de D77** que no cortan el terreno;
- **que la nota calla** cuando hay una válida;
- **la identidad serie = paralelo** de las notas (unas cincuenta) y de los
  contadores, y el progreso por lote. Se saltan en una máquina de un solo
  proceso.

**Discriminación** contra un `git archive` de 0.1.260 (d669b8e), con su runner
y sin el buscador editable: **13 de 16 fallan**. Pasan las dos premisas
geométricas y el control de «sin nota», que tienen que pasar en cualquier
versión.

**Selección:** 23 archivos, 368 de 368 (límites, rejilla de dos ventanas,
paralelo, rechazos de terreno, poligonales, API, interpretación, Block,
Path, capas débiles, superficies del usuario).

**Suite entera:** 5690 de 5690.

## 4. Banco (fuera de git)

- **Fichas.** D262 y D263 se abrieron con la medida y se cerraron. D255 se
  cerró con ellas. Las tres funciones (`d262`, `d263`, `d255`) dan CUBIERTO
  POR TEST, y con el motor de 0.1.260 NO SE SOSTIENEN: `d255` mide allí 99
  notas frente a 0 y una sola llamada de progreso.
- **El 109.**
  - Su constructor anota por qué se mantiene la lectura (a) de los límites.
  - Re-corrido con 0.1.261 por el flujo no circular, los números salen
    idénticos clave a clave. Solo cambian cuatro claves: los avisos (con la
    nota del juego anidado), la técnica archivada, el tiempo y la versión.
- **El 087, árbol contra árbol, con dos ventanas separadas y en paralelo**
  (`_auditoria/P5_0261/ab_087_0.1.26{0,1}.json`).
  - Factores, válidas, inválidas y total, idénticos en los tres métodos.
  - Con 0.1.261 aparece una nota por método: 20 círculos que no se pudieron
    rebanar. La rejilla en paralelo de 0.1.260 la tiraba (D255).
  - Primera corrida descartada: los procesos hijos (`spawn`) cargaban el
    motor editable y no el del árbol viejo. Se repitió con `PYTHONPATH`.
- **Ningún modelo vivo del banco usa rejilla con ventanas solapadas**, así
  que el rechazo no deja ninguna fila sin número.
- **Ciclo:**
  - verificación del 02, 235 cierres y 0 bajadas; la raíz, 0 bajadas;
  - instantáneas 0.1.261 en el 02 y en la raíz;
  - las tres fichas retiradas, `PAQUETES` podado y la cadena de P5 tachada;
  - prompts: 39, con 18 FALTA, todas de fichas anteriores;
  - auditorías del 02 y de la raíz con 0 ERROR;
  - `--forzar`.

### D243, de paso (sigue abierta)

Las mismas medidas cerraron casi todo lo que D243 tenía pendiente
(`02_…/_auditoria/P5_0260/D243_tercera_medida.md`):
- **La tabla 109.2 tiene la huella de un círculo.** Su Spencer/Bishop es
  1,0022, el mismo que el de la tabla circular del 108. En las superficies no
  circulares de este mecanismo ese cociente vale 1,12–1,14.
- **El 109 con los extremos libres reproduce la tabla no circular del 108:**
  1,519 / 1,441 / 1,726 / 1,722, frente a 1,512 / 1,43 / 1,72 / 1,723, y el
  1,516 de la figura.
- **En todo el banco, los extremos libres duplican las filas que caen
  prácticamente sobre el publicado:** a menos del 0,25 %, de 14 a 29 de 91.
  La optimización de la referencia mueve los extremos. La de OGR los deja
  fijos, sin fuente (`move_endpoints = False`).
- **Su cierre lo decide la propietaria.**
