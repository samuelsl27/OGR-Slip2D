# OGR Slip2D v0.1.410

**Todas las búsquedas vuelcan su población, los estados del desembalse van con su resultado, y un resultado que cruza
un proceso sigue en disco (D383, V3: la última).**

Tercera y última versión de D383. Ningún número se mueve: la huella de los 23 casos del banco de pruebas es idéntica a
0.1.377, con los valores por defecto y con el volcado forzado.

## 0. Lo que se encontró

- **Solo volcaba la rejilla.** Slope, Auto Refine (circular y no circular), Block, Path, Simulated Annealing y el
  enjambre añadían sus evaluaciones con sus dovelas en memoria. Había diez sitios de añadido sin una puerta común.
- **El umbral era de la rejilla.** `wants_store` preguntaba por `nominal_circles`, que solo tiene `GridSearch`. Para
  las demás búsquedas lo natural era la misma regla de la propietaria (2000), aplicada a las superficies que planea
  cada una:
  - **Auto Refine** ya las calculaba: es `surfaces_generated`, la cifra que enseña su diálogo;
  - **Slope:** la población y su paseo de refinamiento, `num_surfaces + 8 × 120`. Medido con una población de 80: el
    paseo deja diez veces más evaluaciones (810), así que `num_surfaces` solo se quedaba corto;
  - **Block y Path:** `num_surfaces`;
  - **Simulated Annealing:** `generation_steps`, porque su programa de temperaturas hace aproximadamente esos;
  - **el enjambre:** partículas × iteraciones.
- **`steered` no necesita sus dovelas en memoria.** V1 rehidrataba `steered` junto con la crítica, y con la rejilla
  eran pocas (las optimizadas). El paseo de Slope mete ahí cientos de evaluaciones, y lo único que se pregunta de ellas
  es su identidad: `probabilistic` las deja fuera con `id(r)`. Ahora se quedan en disco. Las optimizadas siguen en
  memoria por `optimized` y `minima`.
- **Los estados del desembalse.** En el drenaje que cicla, el envoltorio publica las dovelas del último cuerno
  (`published = horns[-1].slices`) y guarda los dos cuernos en `screen_states`, cada uno un resultado con sus dovelas.
  Hay que volcarlos con su resultado y conservar ese «es el mismo objeto», porque `checks.screen_surface` juzga por
  ellos.
- **El único cruce de proceso de un resultado entero** es `Job.load_results`: el API leyendo el `result.pkl` del
  trabajo del agente, que luego también ve la ventana (D387). Hasta ahora, un `SpilledSlices` que cruzaba se
  materializaba, y el proceso que lo leía volvía a tener todas las dovelas en memoria.

## 1. Qué cambia

- **`ogr_slip2d/search.py`:**
  - **`BaseSearch._keep(result, res)`:** la puerta única de la población de cualquier búsqueda. Añade y, si hay
    almacén, vuelca. Pasan por ella la rejilla, Slope (la población y el paseo), Auto Refine, Block, Path, Simulated
    Annealing (el arranque y `_steer`) y el enjambre.
  - Las superficies que añade una optimización no pasan por ella: son especiales, como la crítica.
  - **`BaseSearch.nominal_surfaces()`** (None por defecto, que no vuelca), con la cifra propia de cada búsqueda. En la
    rejilla es `nominal_circles`.
- **`ogr_slip2d/particle_swarm.py`:** `nominal_surfaces` y `_keep`.
- **`ogr_slip2d/slice_store.py`:**
  - **`wants_store`** pregunta por `nominal_surfaces`.
  - **`spill`** vuelca también los `screen_states`. El estado que comparte las dovelas del resultado comparte su
    registro; el otro tiene el suyo.
  - **`adopt_part`** (V2) convierte también los estados, conservando el compartido.
  - **`rehydrate`** devuelve los estados a memoria con el mismo «es el mismo objeto».
  - **`rehydrate_special`** ya no rehidrata `steered`.
  - **`arriving()`:** dentro de este bloque, un registro deserializado se escribe en un almacén nuevo del proceso que
    lo lee, que solo se crea si llega alguno. Cada tabla de materiales del remitente se pone al final de la suya, una
    sola vez. Fuera del bloque, el registro se materializa como antes.
  - El registro que cruza lleva ahora la traza y el área.
- **`ogr_api/jobs/__init__.py`:** `Job.load_results` lee dentro de `arriving()`.
- **`tests/test_slice_store_searches_v1410.py`**, nuevo: 7 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_slice_store_searches_v1410.py`** (el talud de `test_block_search_v117`; cada búsqueda con unas decenas
  de superficies):
  - **cada búsqueda lee lo que calculó:** las siete con almacén son iguales, dovela a dovela y con `float.hex`, a la
    misma búsqueda en memoria; la crítica queda en memoria;
  - **el paseo de Slope se queda en disco;**
  - **cada búsqueda dice lo que planea, y el umbral la sigue** (regla 7);
  - **los estados del desembalse van con su resultado:**
    - el estado que publica las dovelas comparte el registro, y el otro tiene el suyo;
    - `screen_surface` da el mismo veredicto en memoria y volcado;
    - al volver a memoria, y tras pasar por un lote de un pool y por `arriving`, el «es el mismo objeto» se conserva y
      el contenido es el mismo.

    Es un caso sintético, con la forma que da el envoltorio: el cuerno B comparte las dovelas del resultado y el A
    tiene una copia.
  - **un resultado que cruza un proceso sigue en disco:** leído con `arriving`, va a un almacén de este proceso (su
    carpeta lleva el PID de este proceso), es igual a lo calculado y la carpeta se va con él. Fuera de `arriving`
    vuelve como dovelas. `Job.load_results` lee así.
  - El archivo tarda 10 s con el arranque. El paseo de Slope, 8 × 120 pasos, es la mayor parte.
- **Mutantes** (`scratchpad/mutantes_v410.py`): caen los nueve:
  - `_keep` no vuelca;
  - Slope planea sin su paseo;
  - el enjambre no planea;
  - un estado nunca comparte el registro;
  - `rehydrate` rompe el «es el mismo objeto»;
  - `adopt_part` se salta los estados;
  - `steered` se rehidrata otra vez;
  - el registro viaja sin su traza;
  - el API lee fuera de `arriving`.
- **Contra el árbol de 0.1.409** fallan los 7. Uno pasaba de vacío, porque allí Path no vuelca y comparaba 0 con 0; se
  reforzó para que exija que haya algo volcado.
- **Vecinos** (las siete búsquedas, el desembalse y los cuernos, la estadística, los trabajos del API, el servidor
  MCP, el almacén, liberar resultados, el `.h5`, el retroanálisis, el paralelo y el pool compartido): 649/649, sin
  carpetas.
- **La huella del banco de pruebas:** 23/23 idéntica a 0.1.377 en las cuatro pasadas (por defecto y con el volcado
  forzado, cada una en paralelo y en serie, con «serie == paralelo» caso a caso). El manifiesto de entradas, con la
  opción D: «sin cambios en este lote» y, contra 0.1.377, solo el cambio aceptado de D388.
- **Memoria del proceso principal en el banco**, conjunto de trabajo al terminar, 0.1.409 → 0.1.410, por defecto:

  | Caso | Búsqueda | 0.1.409 | 0.1.410 |
  |---|---|---|---|
  | K09 | Block (020) | 165 MB | 68 MB |
  | K10 | Path (019, 5000 superficies) | 453 MB | 108 MB |
  | K11 | enjambre 50 × 50 (104) | 197 MB | 74 MB |
  | K13 | Auto Refine no circular (tutorial 20) | 277 MB | 112 MB |

  Los demás casos no se mueven (±1 MB). K12, Simulated Annealing con 300 pasos, queda por debajo del umbral y no
  vuelca.
- **Tiempo.** En la huella, esos cuatro casos tardaron entre un 29 % y un 43 % más que con 0.1.409, y los que no
  cambian, hasta un 12 % más en la pasada forzada y un 29 % en la otra: TextInputHost volvía a girar en un núcleo.
  El reloj de la huella no distingue eso, así que se midió un A/B en el mismo proceso, espalda con espalda, con
  `run_analysis` en serie y el umbral subido para no volcar (`scratchpad/v3_ab.py`):
  - **K09** (Block, 1396 evaluaciones): volcando 52,1 y 52,1 s; en memoria 50,9 y 50,0 s. Entre un 2 % y un 4 %,
    alrededor de 1 ms por evaluación;
  - **K10** (Path, 5008 evaluaciones): volcando 113,7 y 107,1 s; en memoria 105,4 y 105,3 s. La primera pasada iba
    en frío, y las dos con volcado difieren entre sí más que el efecto. La segunda da alrededor de un 2 %, unos
    0,4 ms por evaluación, lo mismo que cuesta escribir un registro.

  Lo que se ve en la huella es la máquina, no el volcado.
- **La suite entera con `--jobs 4`:** 6997/6997, sin fugas y sin tramos muertos, en 24,7 min con TextInputHost
  girando en un núcleo. No deja carpetas en `%TEMP%\ogr_slices`. La última serie en verde fue hace 11 commits.

## 3. El banco y el cierre de D383

- **`d383()`** en `_tools/verificar_cierres.py` de la raíz del banco, en el proceso vivo:
  - **el umbral por defecto (2000):** la rejilla del caso de validación 001 tal como está guardada (21×21×12, 5292
    círculos) vuelca, y una de 400 no;
  - **la memoria, con `tracemalloc`:** la misma rejilla a 6×6×4 con Bishop, en serie, retiene 61,13 kB por
    evaluación en memoria y 5,96 kB volcando. La revisión de diseño buscaba unos 6 kB. Quedan volcadas 206 de 207
    evaluaciones, y la crítica está en memoria;
  - **una búsqueda que no es la rejilla:** un Path de 40 superficies con almacén vuelca 39 de 40;
  - **los tres archivos de tests existen.**

  Sale CUBIERTO POR TEST. Discriminada:
  - con 0.1.406 sale SIGUE ABIERTO porque no hay almacén;
  - con 0.1.409 sale SIGUE ABIERTO porque el Path vuelca 0 de 40 y falta el test de V3.

  La primera versión de `d383()` solo medía la rejilla, que ya volcaba en V1, y con 0.1.409 salía cubierta. Camino
  equivocado: el árbol de 0.1.409 del scratchpad llevaba copiado el test nuevo, el que sirvió para discriminarlo.
  Hubo que quitarlo para discriminar `d383()`, y se le añadió la comprobación del Path.
- **Los dos `verificar_cierres` enteros**, como pide el cierre de una tanda de motor: el del 02, 242 fichas, sin
  bajadas; el de la raíz, 120 fichas, apartó dos:
  - **D326**, desde 0.1.399 (D384). D384 llevó la creación del pool a `processes.stoppable_pool`, que llama a
    `windowless_children()` justo antes de `ProcessPoolExecutor(`. La comprobación buscaba ese texto en `search.py`,
    donde ya no queda ningún pool. Ahora mira cada `ProcessPoolExecutor(` del motor;
  - **D341**, desde 0.1.403 (D388). D388 hizo que una filtración que se niega no toque el proyecto. La comprobación
    leía el resultado fallido de `project.transient_results`, y ahora lo lee de lo que devuelve la corrida
    (`_compute_transient`, espiado), como hace su test desde D388.

  Las dos bajadas eran falsas: los dos defectos siguen corregidos y sus tests pasan. Nadie las vio porque desde
  0.1.397 no se había corrido entero el `verificar_cierres` de la raíz. Discriminadas:
  - D326: cubierta con 0.1.398 (el árbol de antes del cambio, con sus dos pools) y con 0.1.410; abierta con 0.1.328;
  - D341: cubierta con 0.1.402 y con 0.1.410; abierta con 0.1.351, con el mismo `ValueError` que dio origen a la
    ficha.
- **D383 queda cerrada:**
  - instantáneas de 0.1.410 en la raíz y en el 02, la sección guardada en `ERRORES_Y_DISCREPANCIAS_retiradas.md`;
  - podada de `PAQUETES` y tachada en la cadena de P8;
  - prompts regenerados;
  - invariantes con 0 ERROR en la raíz y en el 02.

  Le sigue D393 en P8: el pico del `SliceShare` en la rejilla en serie.

## Archivos

- `ogr_slip2d/slice_store.py`, `ogr_slip2d/search.py`, `ogr_slip2d/particle_swarm.py`
- `ogr_api/jobs/__init__.py`
- `tests/test_slice_store_searches_v1410.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.410.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` y
  `ogr_mcp` (el número; `ogr_gui/main_window.py` también lo lleva)
