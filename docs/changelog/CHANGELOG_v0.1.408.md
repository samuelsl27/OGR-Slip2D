# OGR Slip2D v0.1.408

**Las dovelas de la población de una rejilla grande esperan en disco (D383, V1: la rejilla en serie y el
retroanálisis).**

Primera versión de D383 tras su revisión de diseño con la propietaria (2026-11-01). Ningún número se mueve: la
huella de los 23 casos del banco de pruebas es idéntica a 0.1.377, con los valores por defecto y con el volcado
forzado en todos los casos.

## 0. Lo que se encontró

- **El problema (D383):** cada evaluación guardaba sus dovelas, 57 kB por superficie, el 90 % dovelas.
  - El caso de la prueba de la interfaz de 0.1.397 (124 848 evaluaciones) eran 7,1 GB por resultado.
  - La ventana mantiene dos resultados mientras recalcula (D362).
- **La revisión de diseño** (`_auditoria/P8_interfaz/D383_revision_diseno.md` en el banco) se hizo con un prototipo
  de fuera del programa. Sus medidas, con 0.1.407:
  - **6,81 kB por evaluación con volcado, frente a 57,37** (`tracemalloc`, el caso de la ficha);
  - el caso de la prueba a 51×51×12 retiene 1,39 GB en bytes privados, frente a ~7,9 GB;
  - la ida y vuelta es exacta bit a bit;
  - ~120 µs por evaluación al escribir: +3,6 % en el caso de la prueba, +6,4 % en K03;
  - +13 % en el `.h5` y en el retroanálisis, que leen todas;
  - 0,18 ms leer una superficie.
- **Caminos equivocados de la revisión:**
  - **`persistent_id`** para sacar los `Material` del registro costaba 327 µs por registro, porque el pickler lo llama
    por **cada** objeto, floats incluidos. Con un `dispatch_table` que solo llama a Python para un `Material` son
    101 µs, con los mismos bytes.
  - **Un `seek` antes de cada escritura** vaciaba el búfer y hacía de cada registro una llamada al sistema: 63 frente a
    9 µs.
  - **Unas «4816 lecturas durante la corrida»** resultaron ser del `.h5`: una corrida pura lee 2 veces, las notas
    sobre la crítica.
- **Decisiones de la propietaria:**
  - pickle con `dispatch_table` + **zlib nivel 1** (3,1 kB por evaluación en disco);
  - volcar a partir de **2000 círculos nominales**, solo en `run_analysis` y el retroanálisis;
  - borrar las carpetas huérfanas de más de una hora al crear un almacén;
  - **volver a volcar** al cruzar un proceso (V3);
  - adaptar la huella del banco;
  - el pico del `SliceShare`, a otra ficha.
- **Nace D393:** el `SliceShare` (V18, 0.1.397) causa el pico de la corrida y triplica lo retenido. Medido en K03 a
  31×31×12 con volcado: con dos métodos retiene 113 MB sin él y 334 MB con él, y el pico es de 856 MB. Requiere D383.
- **El `%TEMP%` de la máquina tiene 41 787 entradas:** buscar las carpetas huérfanas allí cuesta 2,4 s en frío. Por eso
  los almacenes viven en una carpeta propia, `%TEMP%\ogr_slices\<pid>_…`, y el barrido solo mira esa.

## 1. Qué cambia

- **`ogr_slip2d/slice_store.py`**, nuevo:
  - **`SliceStore`:**
    - una carpeta y un archivo de solo añadir por corrida;
    - registros pickle + zlib 1, con los `Material` como su posición en la tabla del almacén;
    - un cerrojo, y `seek` solo tras una lectura;
    - las últimas 16 lecturas en memoria;
    - `detach` reasigna la tabla de materiales;
    - `weakref.finalize` cierra el archivo y borra la carpeta;
    - se serializa con pickle como None, así que el trabajador de un pool conserva sus dovelas (eso es V2).
  - **`SpilledSlices`:**
    - longitud, traza de la base, área y los escalares de `Slices`, sin leer el archivo;
    - lo demás lee el registro;
    - `__eq__` materializa;
    - `__reduce__` envía el registro y la tabla, nunca los objetos, y al leerlo se materializa (V3 lo cambiará por volver
      a volcar).
  - `SPILL_MIN_CIRCLES = 2000`, `wants_store`, `rehydrate_special` y `remove_orphans`.
- **`ogr_slip2d/search.py`:**
  - `BaseSearch.slice_store`;
  - `GridSearch.nominal_circles()`;
  - `_run_centres` vuelca cada evaluación al añadirla, después de `_analyse`;
  - `BaseSearch.run` rehidrata las superficies especiales (con almacén) antes de la optimización y antes de
    `detach_materials`;
  - `detach_materials` reasigna la tabla de cada almacén sin leer ningún registro.
- **`ogr_slip2d/analysis_runner.py`:**
  - `run_analysis(..., spill_slices=True)`: un almacén para la corrida, que comparten todos sus métodos;
  - la base determinista de la estadística pasa `spill_slices=False`, porque solo guarda las críticas.
- **`ogr_slip2d/transient_stability.py`:** las etapas pasan `spill_slices=False`, porque solo guardan sus factores.
- **`ogr_slip2d/back_analysis.py`:**
  - vuelca su búsqueda si es grande y la recorre en flujo, una superficie materializada cada vez;
  - acepta una búsqueda sin el atributo, como la de pato de un test.
- **`ogr_slip2d/interpretation.py`:** `surface_path` y `surface_area` leen la traza y el área del objeto perezoso.
  Así la tabla de resultados y el Add Query, que se pregunta en cada movimiento del ratón, no tocan el disco.
- **`ogr_gui/interpret_window.py`:** el slice pick compara por identidad. El `in` caía en el `==` del dataclass, que
  compara las dovelas campo a campo y las habría leído del disco.
- **`tests/test_slice_store_v1408.py`**, nuevo: 12 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_slice_store_v1408.py`** (ACADS 1(a) a 5×5×5, el umbral a 0 y devuelto):
  - lo leído es lo calculado: cada campo de cada dovela de cada evaluación con `float.hex`, y los factores;
  - la crítica es la misma y está en memoria;
  - la traza y el área, iguales a `surface_path` y `surface_area` de las dovelas reales;
  - nada lee el archivo por accidente: longitud, veracidad, traza, área, `surfaces_through_point`, `lem_summary` y el
    slice pick, con unas dovelas que fallan si alguien las compara;
  - un resultado en pickle lleva sus dovelas, y se lee igual después de que su almacén haya desaparecido;
  - la carpeta vive mientras un resultado la nombra y se borra con el último;
  - las dovelas leídas usan las copias de los materiales de la corrida, no los del proyecto (D381), y son las mismas
    que las de la crítica;
  - el umbral mueve el número (regla 7): por debajo no se vuelca nada, y la memoria por evaluación baja más de 3×;
  - las carpetas huérfanas viejas se borran, y las recientes y la propia no;
  - el retroanálisis da lo mismo volcando o no, y vuelca.
- **Mutantes** (`scratchpad/mutantes_v408.py`; cada uno se aplica, corre el archivo y lo restaura byte a byte):
  - caen los ocho con sentido, cada uno en un test: Interpretar comparando por valor, sin `detach` en el almacén, sin
    rehidratación, área mal guardada, traza sin el extremo izquierdo, un pickle que no lleva el registro, un
    retroanálisis que no vuelca y un `surface_area` que lee el archivo;
  - sobrevive uno, legítimo: quitar solo la rehidratación del final, que en V1 repite la del principio (servirá en V3,
    cuando otras búsquedas vuelquen mínimas y guiadas).
- **El archivo de tests tarda 9,2 s** con el arranque del intérprete, y no deja carpetas en `%TEMP%\ogr_slices`.
- **Vecinos** (retroanálisis, Interpretar, `SliceShare`, paralelo, `.h5`, liberar resultados, transitorio,
  `analysis_runner`): 218. La primera corrida dio 217: `test_back_analysis_loads_v1220` pasa una búsqueda de pato sin
  `slice_store`, y el motor ahora usa `getattr`.
- **La huella del banco de pruebas** (`orquestar.py version` y `version_serie`, con `comparar_version.py`): 23/23
  idénticos a 0.1.377 en las cuatro pasadas.
  - Con los valores por defecto, en la pasada `version` y en la `version_serie`, y en esta también serie = paralelo.
  - Con el volcado forzado (`OGR_VOLCADO_FORZADO=1`), igual. En esta pasada cada evaluación de los 23 casos se lee del
    disco y es idéntica bit a bit, dovela a dovela.
  - El lanzador sale con 1 por el manifiesto: el `modelo_fem.ogr` del 010 ya no tiene el hash de 0.1.377. Lo cambió a
    propósito la migración de D388 (0.1.403, 2026-11-01 16:14), y K17, que lo lee, sigue idéntico. El manifiesto no se
    ha rehecho: borraría el hash de referencia, y lo decide la propietaria.
- **El caso de la prueba con el almacén del programa** (`_auditoria/P8_interfaz/d383_medir_v1.py` y
  `d383_v1_prueba.log` en el banco; 51×51×12, cuatro métodos, en serie, umbral por defecto):
  - los cuatro factores son los del prototipo y los de 0.1.407, con todos sus dígitos;
  - 115 036 evaluaciones, de las que 115 032 se vuelcan (las cuatro críticas no);
  - **retiene 1386 MB de bytes privados, 12,63 kB por evaluación, frente a ~7,9 GB sin volcar.** Son las mismas cifras
    que el prototipo (1387 MB);
  - el pico de la corrida es de 3055 MB, el de D393;
  - el archivo ocupa 354 MB, 3,08 kB por registro;
  - la corrida tarda 371 s (393 con el prototipo sin zlib, que está dentro del ruido) y lee el archivo 4 veces;
  - leer una superficie cuesta 0,20 ms de mediana y 0,55 ms en el p99;
  - el `.h5` del primer método, leyendo del almacén, tarda 58,9 s.
  - **Camino equivocado:** la sonda dijo que la carpeta seguía tras soltar el resultado. La sujetaban sus propias
    variables de bucle (una evaluación y el almacén); soltándolas, la carpeta se va (comprobado a 20×20×12).
- **La suite entera con `--jobs 4`:** 6984/6984, sin fugas ni tramos muertos, en 23,7 min (con TextInputHost girando en
  un núcleo). Última serie en verde: 9 commits atrás.

## 3. El banco

- **`_auditoria/COMPUTO/bench/huella.py`:** un `SpilledSlices` se recorre como las `Slices` que lee, decisión de la
  propietaria.
- **`correr.py`:** `OGR_VOLCADO_FORZADO=1` pone el umbral a 0 (`comun.ENV_KEYS` lo registra en la procedencia).
- **D383 sigue abierta** hasta V3. D393 queda abierta, en P8, con su prompt largo.

## 4. Reportado y sin tocar (regla 6)

- **Un trabajo del agente cancelado deja la carpeta de su almacén.**
  - La suite dejó tres carpetas vacías en `%TEMP%\ogr_slices`, de procesos ya muertos.
  - Son de `test_api_jobs_v1194` (un `job_cancel` y un fallo simulado con `_kill_tree`) y de `test_mcp_server_v1195`
    (un `job_cancel`). Los tres usan una rejilla de 60×60×12, por encima del umbral.
  - `Job.cancel()` mata el árbol de procesos, así que el `weakref.finalize` del almacén nunca corre.
  - Es el camino de las huérfanas que se decidió: se borran al crear otro almacén pasada una hora. Pero, hasta entonces,
    un trabajo cancelado del caso de la prueba dejaría hasta 354 MB en disco.
  - El padre sabe el PID, y la carpeta empieza por él (`<pid>_…`). `Job.cancel()` podría borrar
    `%TEMP%\ogr_slices\<pid>_*` en cuanto el árbol haya muerto, porque entonces ya nadie tiene el archivo abierto.
    Queda para que la propietaria decida.

## 5. Lo que queda

- **V2 (paralelo):** hoy una rejilla repartida en procesos no vuelca, y la ventana calcula en paralelo por defecto. Los
  trabajadores devolverán registros y el padre los escribirá; además, el padre deja de deserializar dovelas
  (0,242 → 0,013 ms por evaluación).
- **V3:** las demás búsquedas, los `screen_states` del desembalse y volver a volcar al cruzar un proceso. Después,
  `d383()` y el cierre.
- **D393**, después de D383.

## Archivos

- `ogr_slip2d/slice_store.py` (nuevo), `ogr_slip2d/search.py`, `ogr_slip2d/analysis_runner.py`,
  `ogr_slip2d/transient_stability.py`, `ogr_slip2d/back_analysis.py`, `ogr_slip2d/interpretation.py`
- `ogr_gui/interpret_window.py`
- `tests/test_slice_store_v1408.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.408.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` y
  `ogr_mcp` (el número; `ogr_gui/main_window.py` también lo lleva)
