# OGR Slip2D v0.1.495

**D434: los círculos de un centro de la rejilla sin ningún radio válido son el −1000 de la
referencia, los rechace lo que los rechace.** Hasta esta versión, el censo los contaba como −101
(«the circle does not cut the ground surface twice»). En Ej_1 son 231: la referencia publica
−1000: 231 en sus siete métodos y ningún −101. No cambia ningún factor, ni el recuento de
válidas, ni la población.

## 0. Lo que se encontró

- **Medido con 0.1.494, sin tocar el motor.** Se espió `evaluate_circle` y se clasificó cada
  `misses_ground` según la horquilla de su centro:

  | modelo | `misses_ground` | de un centro sin radio válido | de un radio que no corta |
  |---|---|---|---|
  | Ej_1 (rejilla de referencia) | 231 | 231 (21 centros, x = 120) | 0 |
  | Ej_2 | 0 | 0 | 0 |
  | 02/001, 02/003, 02/027 | 0 | 0 | 0 |
  | 02/087 (dos ventanas) | 2440 | 2440 (40 centros × 61) | 0 |

  En ningún modelo medido hay un `misses_ground` de un radio normal, así que las opciones A y B
  de la ficha dan lo mismo en Ej_1.
- **El 087 tiene 3 centros más sin radio válido** (183 círculos), que se rechazan por los Límites
  del talud y no por `misses_ground`. En esos centros los dos extremos de la horquilla se cruzan:
  el margen 1,001 / 0,999 deja el intervalo más estrecho que el propio margen, y se emite 61 veces
  el mismo radio, en un borde. Con ellos son 43 centros y 2623 círculos. Es lo que el docstring de
  la rejilla de dos ventanas mide en la referencia: «43 centres without a valid radius… 0 valid of
  2623».
- **La ayuda de la referencia** («Summary of Error Codes», leída el 2026-11-27) dice del −1000 solo
  «No valid slip surface is generated», y del −101, «Only one (or none) slip surface / slope
  intersections». El informe de Ej_1 es el que asigna los 231.
- **Ningún modelo del 02 publica un −1000.** Se ha buscado en sus `referencia.json`, textos y
  fichas.

## 1. Qué cambia

Opción **A**, decisión de la propietaria del 2026-11-27: el −1000 se decide por el **centro**, no
por el motivo del rechazo.

- `ogr_slip2d/search.py`:
  - `_NoValidRadius`, una tupla marcada: los dos mismos números de siempre, para un centro sin
    radio válido. La devuelven tres casos:
    - con una ventana, `_radius_bracket` cuando el punto más cercano de la superficie del talud es
      un punto límite (`d_min == d_max`, con tolerancia relativa 1e-9);
    - con dos, `_radius_bracket_two_windows` sin ningún radio válido;
    - con dos, cuando los dos extremos se cruzan.
  - `_run_centres` evalúa los círculos de un centro así con `_evaluate_without_radius`. Un rechazo
    que el censo cuenta (`misses_ground`, `outside_slope_limits`, `leaves_external`) se devuelve y
    se cuenta una vez en `_no_valid_radius`. Un resultado, si alguna vez lo hubiera, se queda como
    está.
  - Contador nuevo en `_RUN_COUNTERS` y `_CENSUS_COUNTERS`, y campo nuevo
    `SearchResult.no_valid_radius`. La rejilla en paralelo lo suma como los demás.
  - Una parte más en la nota de rechazos: «{n} circles of grid centres with no valid radius».
  - El comentario de `REFUSED_MISSES_GROUND` explica la excepción.
- `ogr_slip2d/interpretation.py`: `ERROR_NO_SURFACE = -1000` en `ERROR_CODES`, que lista la vista
  `error_codes` del agente, y una fila nueva en `COUNTED_REJECTIONS` («the circle is one of a grid
  centre with no valid radius»).
- El castellano de las dos frases, en `ogr_gui/i18n/__init__.py`.

## 2. Tests

- `tests/test_no_valid_radius_v1495.py` (nuevo, 5 tests):
  - la referencia es la tabla publicada de Ej_1 (`EJ1` de `test_m_alpha_screening_v1189`):
    −1000 = 231;
  - los 231 son los 21 centros de x = 120, cada uno con r = y − 25;
  - frente al censo de 0.1.494, en el mismo proceso: el −101 pierde justo 231 y la población
    (4851), las válidas y el factor crítico no cambian, al bit;
  - el muro de D77 con dos ventanas: 27 de 27 bajo −1000;
  - la vista del agente lista el código.

  Contra el árbol de 0.1.494 fallan los cinco.
- Cambiados a propósito porque el muro de D77 tiene 27 círculos de centros sin radio válido:
  - `tests/test_slope_limit_refusals_v1261.py`: el test de los 27 pasa a llamarse
    `test_a_circle_of_a_centre_with_no_valid_radius_is_the_1000`, y el de la serie frente al
    paralelo compara `no_valid_radius`;
  - `tests/test_left_soil_refusal_v1445.py` y `tests/test_refused_surface_notes_v1446.py`;
  - `tests/test_search_notes_v1349.py`, con la muestra de la frase nueva.
- Las áreas del censo, de la rejilla, de los casos de validación y de Interpretar: 615 de 615 en
  verde.
- Banco: `d434()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST** (Ej_1
  `{-1000: 231, -111: 859, -103: 183, -101: 1}`). `d420()` sigue cubierto, con −103 = 183.

## 3. Lo que no se ha probado

- Las huellas de `_auditoria/COMPUTO/bench/`: este cambio mueve el `SearchResult` de las
  rejillas con centros sin radio válido (`misses_ground`, `no_valid_radius` y la nota). Se
  regeneran y se declaran con D435 (0.1.496), que también mueve el censo.
- Ej_2 no tiene la tabla de códigos publicada en la suite. Aquí da 0 círculos de este tipo.
