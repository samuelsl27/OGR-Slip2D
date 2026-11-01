# OGR Slip2D v0.1.399

**Cancelar una rejilla repartida en procesos para en un segundo, no cuando acaban los lotes ya entregados (D384).**

Es la segunda versión del plan que salió de la prueba de la interfaz de 0.1.397. La propietaria dio el OK a seguir
(«Si continua») sin elegir entre las dos opciones, y se hizo la recomendada, (a)+(b): el padre mira el Cancelar
mientras espera, y los trabajadores paran entre centros.

Ningún número se mueve. El cambio está en cómo se espera a los lotes y en cuándo se paran.

## 0. Lo que se encontró

- **Lo que vio la prueba (FALLO 2):**
  - el diálogo se quedó en «Cancelando…» 25 s o más;
  - los 4 procesos siguieron vivos unos 34 s;
  - la ventana subió de 2598 a 3298 MB entretanto.
  - En serie, Cancelar es instantáneo.
- **Dos esperas, las dos en el código:**
  - el hilo de cálculo esperaba en `as_completed` sin límite (`_run_batches`), así que el Cancelar solo se leía en el
    callback que sigue a un lote terminado;
  - después esperaba a los lotes ya entregados a un trabajador (D362/D368), hasta trabajadores + 1, porque el pool
    pone uno más en su cola. Los trabajadores no tenían ningún punto de parada: su `progress_cb` es None y no hay
    vigilante, así que cada lote, 1/32 de la rejilla de un método, corría hasta el final.
  - Los +700 MB eran los resultados de esos lotes llegando al padre para nada.
- **No es de V17:** el pool propio y el prestado soltaban los lotes por el mismo `drop()`.
- **Medido antes del cambio** (`_auditoria/P8_interfaz/d384_latencia_cancelar.py`):
  - K03 del banco de pruebas: 51×51×12, Bishop y Janbu corregido, con pool;
  - parado como lo para la ventana, con un vigilante en el hilo de cálculo y un callback que lanzan;
  - una corrida por proceso;
  - pedido a los 15 s, paró 9,77 s después; a los 35 s, 12,28 s después. Con la RAM libre: la prueba tenía la RAM
    llena y Spencer y GLE.

## 1. Qué cambia

- **`ogr_slip2d/processes.py`:**
  - **`stoppable_pool(workers)`:** devuelve un pool y su evento (`multiprocessing.Event`). Cada trabajador recibe el
    evento al arrancar, por el `initializer` (`_install_stop`), que es la única forma de que un evento llegue a un
    trabajador del pool.
  - **`stop_check()`:** el vigilante del trabajador; lanza **`BatchStopped`** cuando el evento está puesto. Es una
    `BaseException`, como el `TaskCancelled` de la ventana, porque el motor captura `Exception` alrededor de cada
    superficie, y una parada no puede contarse como una superficie fallida más.
  - **`pool_scope`:** `borrow` crea el pool con `stoppable_pool`, y `discard` pone el evento antes de cerrarlo. Al final
    del ámbito no corre ningún lote, y no cambia nada.
  - `_stop` es None en cualquier proceso que no sea un trabajador, así que un lote que corre aquí calcula como antes.
- **`ogr_slip2d/search.py`:**
  - **`_run_batches`:** espera con `concurrent.futures.wait(..., timeout=_STOP_POLL_S, return_when=FIRST_COMPLETED)`
    (0,2 s) y llama a `ogr_core.progress.checkpoint()` entre esperas. Los lotes terminados en una misma espera se
    toman por orden de envío; a `parts` llega lo mismo, por índice, como antes.
  - **`_grid_batch`:** en un trabajador, corre `_run_centres` dentro de `watching(processes.stop_check)`.
  - **`_run_centres`:** sin callback de progreso, cada centro es un `checkpoint()`, la regla de D362 para los bucles que
    no informan de progreso. Sin vigilante no hace nada.
  - **El pool propio de `_parallel_grid_run`:** sale de `stoppable_pool`, y su `drop()` pone el evento antes del
    `shutdown`.
- **`tests/test_cancel_stops_workers_v1399.py`**, nuevo: 6 tests.
- **`tests/test_shared_pool_v1396.py`:** su ejecutor en línea acepta `initializer` e `initargs` y los guarda sin
  ejecutarlos, porque sus lotes corren en este proceso.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **La latencia, después del cambio**, con la misma sonda, una corrida por proceso:

  | Pedido a los | 0.1.397 / 0.1.398 | 0.1.399 |
  |---|---:|---:|
  | 15 s | 9,77 s | **0,69 s** |
  | 25 s | 11,61 s | **1,42 s** |
  | 35 s | 12,28 s | **1,40 s** |

  - En las seis corridas no queda ningún trabajador vivo después.
  - El par de 25 s es árbol contra árbol, el viejo con `PYTHONPATH` para que también lo carguen los trabajadores.
- **`tests/test_cancel_stops_workers_v1399.py`,** sin reloj que decida nada:
  - el padre lee la parada mientras espera a un lote que nunca termina, cancela el lote y suelta el pool;
  - un lote de trabajador con el evento puesto no evalúa ningún centro;
  - con el evento puesto tras k centros, evalúa exactamente los círculos de esos k, con una comprobación por centro;
  - el pool propio y el del ámbito ponen el evento antes del `shutdown`;
  - sin evento, un lote da las evaluaciones de la corrida en serie, con `float.hex`.
- **La discriminación:** con `search.py` y `processes.py` de 0.1.398 fallan los seis. Ninguno se cuelga: los seguros
  de 5 s terminan el lote que el árbol viejo no sabe parar.
- **Cinco mutantes, uno por pieza, cada uno cazado:**
  - sin el `checkpoint` de la espera: 2 fallos;
  - sin el vigilante del lote: 2;
  - sin el `checkpoint` por centro: 2;
  - el `drop()` del pool propio sin poner el evento: 1;
  - `discard` sin ponerlo: 1.
- **La identidad**, con el banco de pruebas de la auditoría del cómputo:
  - la huella de los 23 casos, **23 de 23 idénticos a 0.1.377** (`all identical`, código 0);
  - `version_serie`: los 12 casos con pool idénticos en serie a 0.1.377 y **serie igual a paralelo** (`all
    identical`).
- **La suite:**
  - entera con `--jobs 4`: **6936 de 6936, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en unos 24 min;
  - **la serie entera**, porque la versión toca el pool (la guarda de D310): **6936 de 6936** en 47,7 min, apuntada
    (`full serial run recorded`).
  - Los dos tiempos salen un 20 % por encima de la tabla de AGENTS.md (20,1 y 39,7 min), y no es el código. Dos
    causas en la máquina:
    - `TextInputHost.exe` lleva colgado desde el 28 de octubre girando un núcleo entero (4,7 s de CPU en 5 s), el
      mismo cuelgue que ya frenó la suite del 22 al 28 de octubre;
    - el portátil corría sin su base de refrigeración, y el procesador de 15 W baja de frecuencia con los cuatro
      núcleos cargados (aviso de la propietaria).

    No son tiempos de referencia.
  - El aviso `SLOW, NOT IN tests/_slow.txt` vuelve a nombrar `test_points_table_v1371.py` (116,6 s en serie), que
    sigue pendiente de la decisión de la propietaria.

## 3. El banco

- **D384 cerrada,** CUBIERTO POR TEST.
  - `d384()` en el `verificar_cierres.py` de la raíz, sin procesos ni reloj que decida:
    - con un lote que nunca termina, la parada llega a través de la espera;
    - un lote de trabajador con el evento puesto no evalúa ningún círculo de la rejilla de demostración;
    - `pool_scope.discard` pone el evento antes del `shutdown`.
  - Discriminada: con el árbol de 0.1.397, cuyo motor es el de 0.1.398, da SIGUE ABIERTO en las tres («no llega hasta
    que acaba el lote», sin punto de parada, «evento puesto: [None]»); con este, CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.399` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.
- La sonda de latencia queda en `_auditoria/P8_interfaz/d384_latencia_cancelar.py`, y las corridas de identidad en
  `_auditoria/COMPUTO/bench/datos/v0.1.399/`.

## 4. Lo que queda

- **El plan, en orden:** D385 (el `.h5` fuera del hilo de la ventana), D386 (si la propietaria está de acuerdo) y D387.
- **Después:** la prueba a mano redimensionada a 31×31×12, que comprobará también este Cancelar en la ventana, y D383
  con su revisión de diseño.

## Archivos

- `ogr_slip2d/processes.py`, `ogr_slip2d/search.py`
- `tests/test_cancel_stops_workers_v1399.py` (nuevo), `tests/test_shared_pool_v1396.py`
- `docs/changelog/CHANGELOG_v0.1.399.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
