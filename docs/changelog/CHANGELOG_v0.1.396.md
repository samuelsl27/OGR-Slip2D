# OGR Slip2D v0.1.396

**Un cálculo que encadena varias búsquedas les presta un solo pool de procesos** (V17 de la fase 3 de la auditoría del
cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido**, con una corrida por proceso nuevo y en orden ABBA. El lado viejo es el mismo código con ningún ámbito
prestado, que es el camino de 0.1.395; aquí sí vale parchear, porque los pools los crea el padre:
- **K01b** (caso 001 a 7 × 7 × 11, cuatro métodos): de 5,0 y 7,0 s a **2,8 y 4,0 s**, en torno a −40 %;
- **K21** (barrido del desembalse, cinco niveles), bajo un ámbito, como lo abre la puerta del barrido: de 13,8 y
  13,6 s a **10,8 y 10,5 s (−22 %)**;
- **K02** (caso 001 tal cual, cuatro métodos): de 35,0 y 33,7 s a 37,0 y 32,1 s. No resuelve: el ruido de la
  máquina (±2,5 s) supera el efecto esperado, tres pools menos, unos 1,5 s (−4 %).

Los resultados son idénticos en todas las corridas de K01b y K02, con el mismo hash. El de K21 lo comprueba la
huella del banco (abajo).

Clase A: los mismos lotes a la misma función. Lo demuestran la huella de los 23 casos y la de sus gemelos en serie.

## 0. Lo que se encontró

- **La puerta de medida.** Cada búsqueda de rejilla abría y cerraba su propio pool:
  - arrancar uno de cuatro trabajadores cuesta 0,43–0,48 s hasta los primeros resultados, más 0,06–0,07 s al
    cerrarlo;
  - K01b abría 4 pools en 4,3 s, K02 4 en 35,8 s, K03 2 en 55,0 s, el barrido K21 5 en 11,7 s, y Overall Slope con
    Global Minimum (K20) 8 en 106,6 s;
  - K18 no abre ninguno.
- **Las decisiones de la propietaria:**
  - **un ámbito por hilo**, con el patrón de `ogr_core.progress`, y no un argumento `pool=` que cambiaría firmas
    públicas;
  - **los conductores del plan:** `run_analysis` (los métodos), la puerta del barrido (niveles × métodos), la puerta
    de la estadística (la corrida determinista y Overall Slope o Global Minimum) y `run_transient_stability` (etapas
    × métodos);
  - **aceptar los trabajadores ociosos** durante la llamada: entre métodos, durante la optimización de la superficie
    crítica, que corre en el padre, y entre las etapas del transitorio mientras corre el MEF. Un trabajador recién
    arrancado ocupa unos 39 MB.
- **Cómo queda:**
  - `processes.pool_scope` abre un ámbito en el hilo. El pool lo crea la primera búsqueda que reparte, con el
    tamaño que pide, y se cierra cuando acaba el ámbito más externo, acabe como acabe. Un ámbito abierto dentro de
    otro comparte el pool del de fuera: la puerta de la estadística llama a `run_analysis`, y el transitorio también.
  - El decorador `processes.pooled` marca los cuatro conductores sin reindentar sus cuerpos, y conserva nombre,
    docstring y firma.
  - Sin ámbito, que es cualquier búsqueda que lanza un script, un test o la API por su cuenta, la búsqueda abre y
    cierra su pool como antes.
- **Un solo bucle para los dos caminos.** El bucle de lotes de `_parallel_grid_run` pasa a `_run_batches`, sin
  tocarlo, y lo usan el pool propio y el prestado. Así el Cancelar de D362 y D368 (cancelar futuro a futuro, cerrar
  y relanzar) vive en un solo sitio; con el pool prestado, «cerrar» es descartarlo del ámbito.
- **Las condiciones del plan, cumplidas:**
  - **`discard()` es idempotente:** llegan a él la búsqueda que se para, la que falla y el final del ámbito;
  - **un pool prestado que se encuentra roto** (`BrokenProcessPool`: un trabajador murió mientras esperaba, cosa que
    a un pool propio no le pasaba) se descarta y se rehace una vez antes de caer a serie. Si no, aparecería una nota
    `PARALLEL_FALLBACK` donde hoy no sale. Roto otra vez, cae a serie y lo dice, como siempre;
  - **cualquier otro fallo** cae a serie como antes, y descarta el pool: la búsqueda siguiente empieza con uno nuevo,
    como siempre ha hecho;
  - **el cierre va en el `__exit__` del ámbito,** así que se cierra también si el Cancelar llega fuera de la rejilla
    (en la optimización o en el MEF);
  - **ninguna caché entre llamadas:** cada búsqueda sigue mandando su proyecto y su búsqueda con cada lote;
  - **ninguna cadena de mensaje nueva.**
- **Un error mío al escribir los tests:** usé el identificador `ordinary` en vez de `ordinary_fellenius`.
  `run_analysis` lo saltó con un aviso, y el test contaba los pools de un solo método. Ahora el test comprueba
  también que corren los dos métodos.

## 1. Qué cambia

- `ogr_slip2d/processes.py`: **`pool_scope`** (`borrow`, `discard`), **`current_pool_scope`** y **`pooled`**.
- `ogr_slip2d/search.py`:
  - **`_run_batches`:** el bucle de lotes de siempre;
  - **`_run_borrowed`:** con el pool del ámbito, rehecho una vez si está roto;
  - **`_parallel_grid_run`:** pool propio sin ámbito, prestado con él, y el pool descartado tras un fallo.
- `ogr_slip2d/analysis_runner.py`: `@pooled` en `run_analysis`, `run_configured_drawdown_sweep` y
  `run_configured_statistics`.
- `ogr_slip2d/transient_stability.py`: `@pooled` en `run_transient_stability`.
- `tests/test_shared_pool_v1396.py`, nuevo: 11 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_shared_pool_v1396.py`.** Los pools son un ejecutor que corre cada lote en el acto, en el propio
  proceso, sobre una copia en pickle de lo que recibiría un trabajador. Así se cuentan sin procesos. Las rejillas
  son de 96 círculos, con el umbral del pool rebajado durante el test, porque lo que se prueba es el préstamo y no
  el tamaño al que reparte una rejilla:
  - **las mismas evaluaciones, un pool:** un Compute con dos métodos da, evaluación por evaluación, lo que daba con
    un pool por método. Abre uno en vez de dos, y lo cierra al volver;
  - **los ámbitos:** el anidado comparte el pool y solo el más externo lo cierra; una excepción no deja ámbito y
    cierra el pool; `discard` es idempotente; un tamaño distinto rehace el pool;
  - **un pool prestado roto** se rehace una vez y la búsqueda reparte sin nota; roto otra vez, cae a serie, lo dice
    y da la respuesta en serie. Tras otro fallo (un `OSError`), la búsqueda siguiente empieza con un pool nuevo;
  - **una parada:** dentro de la rejilla, descarta el pool prestado, y la búsqueda siguiente hace otro; fuera de
    una rejilla, lo cierra al salir;
  - **sin ámbito,** cada búsqueda abre y cierra su pool;
  - **los cuatro conductores** abren ámbito.

  El archivo entero tarda 2,1 s, con el arranque del intérprete.
- **Once mutantes,** todos cazados:
  - sin rehacer el pool roto;
  - rehaciéndolo sin fin;
  - un pool fallido prestado a la siguiente búsqueda;
  - una parada que no descarta el pool;
  - nunca pedir prestado;
  - un ámbito anidado que también cierra;
  - pedir prestado sin mirar el tamaño;
  - `discard` no idempotente;
  - una excepción que deja el ámbito;
  - el transitorio sin ámbito;
  - la puerta del barrido sin ámbito.
- **Los tests del paralelo, el Cancelar, el barrido, Overall Slope, el transitorio, el censo de notas, el umbral del
  pool, la estadística y la rejilla de la ventana,** juntos: 323 de 323.
- **El banco:**
  - la huella de los 23 casos frente a 0.1.377: 23 de 23 idénticos (`all identical`, código 0);
  - los gemelos en serie de los 12 casos con pool (`version_serie`): 12 de 12 idénticos a los de 0.1.377, y en
    serie igual que en paralelo (`all identical`, código 0);
  - ninguna corrida contaminada.

  En las corridas de identidad, frente a 0.1.395 (tiempo interno de cada caso):
  - K20, de 107,9 a 93,4 s (−13 %);
  - K02, de 33,4 a 30,9 s;
  - K03, de 53,4 a 52,6 s;
  - K21, igual (11,4 s): el caso llama al barrido por debajo de su puerta, sin ámbito, y por eso se midió aparte;
  - K01b, de 4,7 a 4,9 s, una corrida suelta dentro del ruido de la máquina.

  Contados con la puerta de medida, K01b hace sus cuatro rejillas con un pool en vez de cuatro (2,8, 2,8 y 4,2 s en
  tres corridas seguidas, frente a 4,3 s con cuatro pools).
- **La suite entera con `--jobs 4`:** **6917 de 6917, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 20 min.
- **La serie entera,** que el plan pide en las versiones que tocan lo paralelo (guarda de D310): **6917 de 6917,
  `Failed: 0`**, sin fugas, en 39,7 min (apuntada por el runner). En v0.1.375 eran 68,6 min; la tabla de «Coste de
  los tests» de AGENTS.md se actualiza al terminar las 18 versiones, como dice el plan. Sigue el aviso de
  `test_points_table_v1371.py` (93,7 s, fuera de `tests/_slow.txt`), pendiente de decisión.

## 3. Lo que queda

- **La prueba a mano en la ventana** (propietaria): una búsqueda grande con varios métodos, Calcular y Cancelar a
  mitad de rejilla y durante la optimización. El Cancelar debe soltar la cola como desde D362/D368, y no deben
  quedar trabajadores vivos al acabar.
- **V18,** con su OK: rebanar una vez para todos los métodos, en serie.

## Archivos

- `ogr_slip2d/processes.py`, `ogr_slip2d/search.py`, `ogr_slip2d/analysis_runner.py`,
  `ogr_slip2d/transient_stability.py`
- `tests/test_shared_pool_v1396.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.396.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
