# OGR Slip2D v0.1.478

**Los tests de la búsqueda en paralelo reparten de verdad en cualquier máquina, o se saltan diciendo
por qué.** Primera versión en el PC nuevo (`C:\Desarrollo\OGR_Suite`, 16 núcleos físicos y 32
procesadores lógicos, 2026-11-22). Solo cambian tests: el motor no se toca y no se mueve un número.

## 0. Lo que se encontró

### Un test fallaba aquí, y siete pasaban sin probar lo que decían

La suite entera de la puesta en marcha (sobre `45c5146`) dio un fallo, siempre y también solo:
`test_the_search_asks_before_every_pool` (`tests/test_console_language_demo_v1329.py`), con
`calls == []`.

- El ayudante `_search(project, workers)` de `tests/test_parallel_search_v197.py` traducía «N
  procesos» a `parallel_cpu_percent = round(100·N/cpu_count)`. El motor (`_worker_count`, en
  `ogr_slip2d/search.py`) redondea **hacia abajo** a procesos enteros, como dice su docstring. Con
  los 8 lógicos del portátil, 2 procesos daban 25 % → 2. Con 32 dan 6 % → `int(32·0,06) = 1`, y no
  se abre ningún pool.
- Lo grave no era el fallo. En este PC, **siete tests que dicen comparar una búsqueda repartida
  corrían en un proceso y pasaban**:

  | Archivo | Test | Por qué pasaba en falso |
  |---|---|---|
  | `test_parallel_search_v197` | `test_same_evaluations_in_the_same_order` | comparaba la serie consigo misma |
  | ″ | `test_same_counts` | igual |
  | ″ | `test_same_critical_surface_to_the_last_bit` | igual |
  | ″ | `test_a_broken_pool_still_returns_the_sequential_answer` | el pool roto nunca se pedía |
  | ″ | `test_the_progress_callback_survives_the_trip` | el camino en serie también informa del progreso |
  | `test_console_language_demo_v1329` | `test_a_split_search_under_it_is_bit_identical` | sin pool tampoco hay nota «ran in one» |
  | ″ | `test_the_search_asks_before_every_pool` | el único que fallaba |

  Los demás tests de paralelo fijan su propio porcentaje y estaban bien: con 100 % piden el tope de
  8, o se saltan si `_worker_count < 2`. `test_slice_store_parallel_v1409` ya redondeaba hacia
  arriba. `test_shared_pool_v1396` solo toma `_project` y `_fingerprint`.
- **La regla del motor no está mal.** Con 100 o menos procesadores lógicos, un punto porcentual
  equivale como mucho a un proceso, así que con un porcentaje entero se llega a cualquier cuenta de
  1 a 8: en 32, 2 procesos es el 7 %.
- **Observación sobre el motor, sin tocarlo**: por encima de 100 lógicos ya no se llega a todas las
  cuentas. En 128, el 3 % da 3 procesos y el 4 % da 5, y ningún porcentaje entero da 4. Es la
  granularidad de un control entero, no un error de redondeo, y en máquinas de hoy no se ve. Queda
  dicho para quien decida si importa.

### Un camino equivocado propio

El caso nuevo afirmaba al principio que cualquier cuenta hasta el tope se alcanza en cualquier
máquina, que es lo que el plan de esta versión decía. Falló en `(128, 4)` y así salió la
observación de arriba. El caso dice ahora lo que es verdad: hasta 100 lógicos, todas las cuentas;
por encima, el ayudante se salta cuando no hay porcentaje entero.

## 1. Cambios (solo tests)

- `_share_for(workers)`: el porcentaje entero más bajo con el que **esta** máquina da exactamente
  esos procesos. Se pregunta al propio `_worker_count` y no se copia su regla. Si no existe (menos
  lógicos que procesos, o la granularidad de arriba), `_search` hace `pytest.skip` con el número de
  lógicos.
- `_pools()`: un espía sobre `processes.stoppable_pool`, por donde pasan los dos caminos del motor
  (el pool propio de la búsqueda y el que presta un cálculo, `PoolScope.borrow`). `_assert_pools`
  exige un pool de exactamente N, o ninguno para uno. `_run` lo comprueba **en cada llamada** y no
  solo en la primera: con la comprobación dentro de la caché, solo el primer caso habría visto una
  corrida sin repartir.
- Los siete tests de la tabla lo comprueban.
- Caso nuevo, `test_the_helper_asks_for_exactly_the_processes_named`: máquinas simuladas de 1, 2,
  3, 8, 32 y 128 lógicos (`os.cpu_count` restaurado en `finally`); en 32, `_share_for(2) == 7` y el
  `round` de antes da un proceso; en 128, `_share_for(4) is None`.

## 2. Qué se probó

- Los dos archivos, solos: 22 casos, 22 pasan. Los siete del censo abren ahora un pool de 2
  procesos y salen iguales bit a bit que la serie.
- **Mutante**: `_share_for` vuelto al `round` de antes. Mueren 8: los siete con «asked for 2
  processes, pools opened: []» y el caso nuevo.
- Suite entera, `--jobs 4`, `QT_QPA_PLATFORM=offscreen`, en el `.venv`: ver §3.

## 3. Suite

Suite entera con `--jobs 4`, fuera de pantalla, en el `.venv` (`shared: ogr_core 0.2.2 …
(installed, no git tree)`): **7548 casos, 7546 pasan, 0 fallan, 2 saltados**, sin fugas ni tramos
muertos, código de salida 0. Los dos saltados son los de siempre: `os.killpg` (solo POSIX) y
`test_the_fifteen_sheets_give_what_they_gave` (la ruta del banco del PC antiguo; se arregla en
0.1.480). La corrida termina con `SERIAL RUN DUE`: en este PC no hay serie registrada; la serie va en
la última versión de esta tanda.
