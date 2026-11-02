# OGR Slip2D v0.1.409

**Una rejilla repartida en procesos también vuelca sus dovelas, y un trabajo del agente que se mata no deja su almacén
(D383, V2).**

Segunda versión de D383. En 0.1.408 solo volcaba la rejilla en serie, y la ventana reparte en procesos por defecto.
Ningún número se mueve: la huella de los 23 casos del banco de pruebas es idéntica a 0.1.377, con los valores por
defecto y con el volcado forzado.

## 0. Lo que se encontró

- **El camino en paralelo no volcaba.**
  - El `SliceStore` viajaba a cada trabajador como `None`, así que el trabajador guardaba todas las dovelas de su lote.
  - El padre deserializaba cada dovela de la rejilla: 0,242 ms por evaluación, según la revisión de diseño.
  - Después las guardaba en memoria, porque nadie las volcaba.
- **Un trabajo del agente cancelado o caído dejaba la carpeta de su almacén** (reportado en 0.1.408; la propietaria
  aprobó el arreglo el 2026-11-02).
  - `Job.cancel()` mata el árbol de procesos, así que el `weakref.finalize` del almacén nunca corre.
  - La suite dejaba tres carpetas por corrida.
- **El PID que conoce `Popen` puede no ser el del intérprete.** En un venv de Windows, el `python.exe` es un redirector
  que arranca el intérprete real como hijo, y la carpeta lleva el número del hijo. En esta máquina coinciden (medido);
  aun así, el trabajador escribe su propio PID en la carpeta del trabajo, y el padre limpia por los dos.
- **Camino equivocado:** un A/B del tiempo en paralelo dio 106–110 s frente a 11 s en serie, con o sin volcado, y
  parecía una anomalía del pool. Era el script, que no tenía guarda de `__main__`: en Windows, cada trabajador `spawn`
  reimporta el script principal y volvía a ejecutar las corridas (la trampa que ya describe `comun.py` del banco). Con
  la guarda, en ACADS 1(a) a 21×21×12 con Bishop:
  - en paralelo sin volcar, 6,9–7,7 s;
  - en paralelo con volcado, 6,5–6,6 s;
  - en serie, 11,0 s.

## 1. Qué cambia

- **`ogr_slip2d/slice_store.py`:**
  - **`_BatchStore`:** un `SliceStore` en la memoria del trabajador, para su lote. Es lo que pasa a ser un almacén
    enviado con la búsqueda: `SliceStore.__reduce__` ya no da `None`.
  - **`_Pending`:** un registro del lote en camino al padre. Lleva los bytes y lo que un `SpilledSlices` guarda en
    memoria.
  - **`SliceStore.adopt_part`:**
    - escribe en el archivo los registros de un lote en cuanto llega;
    - pone la tabla de materiales del lote al final de la suya;
    - cambia cada `_Pending` por un `SpilledSlices` con `_base`, la posición donde empieza la tabla de su lote.
  - `_material_at`, `load`, `recent` y `_from_record` cuentan desde `_base`.
  - `SpilledSlices.__reduce__` pregunta al almacén cómo se envía: el del padre manda el registro y su tabla; el del
    trabajador, un `_Pending`.
  - **`remove_folders_of(pid)`:** borra las carpetas que llevan el número de un proceso que ha terminado. Si un proceso
    vivo tiene abierto su archivo, Windows no deja borrarla.
- **`ogr_slip2d/search.py`:**
  - `_grid_batch` devuelve la tabla del lote (`_worker_table`) si la búsqueda trae almacén;
  - `_run_batches` y `_run_borrowed` reciben el almacén, y `_run_batches` adopta cada lote al llegar.
- **`ogr_api/jobs/worker.py`:** el trabajador escribe su PID en `pid`, en la carpeta del trabajo.
- **`ogr_api/jobs/__init__.py`:** `Job._finish`, que corre una vez cuando el trabajo llega a un estado final, borra las
  carpetas del PID de `Popen` y del que escribió el trabajador.
  - Cubre Cancelar y un fallo.
  - Si el trabajo terminó solo, no queda nada que borrar.
- **`tests/test_slice_store_v1408.py`:** el invariante de que el almacén viaja como `None` cambia a propósito. Ahora
  viaja como un almacén en memoria, sin carpeta.
- **`tests/test_slice_store_parallel_v1409.py`**, nuevo: 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_slice_store_parallel_v1409.py`** (ACADS 1(a) a 9×9×4, 500 círculos, por encima del umbral de 400 del
  pool):
  - **lo que una corrida en paralelo lee del disco es lo calculado:** la misma rejilla en serie y en memoria, dovela a
    dovela, con `float.hex`;
  - **un lote vuelve como registros, y solo con almacén:** con almacén, cada evaluación con dovelas llega como
    `_Pending`, junto con la tabla; sin almacén llegan dovelas, como antes;
  - **cada lote nombra su propia tabla:** los `_base` difieren por lote, y las dovelas leídas usan los materiales de su
    lote;
  - **lo mismo con un pool real**, de dos procesos, a través de `run_analysis`; la carpeta se va con el resultado;
  - **un trabajo cancelado no deja carpeta:** se borran las del PID de `Popen` y las del PID del archivo, y no la de
    otro proceso cuyo número empieza igual (`<pid>0_…`).
  - Los casos 1–3 usan un pool en el mismo proceso: cada lote y cada parte pasan por pickle, que es la frontera que
    importa. Así no arrancan trabajadores.
  - El archivo tarda 8,5 s con el arranque del intérprete y el pool real.
- **Mutantes** (`scratchpad/mutantes_v409.py`): caen los ocho, cada uno en al menos un test:
  - el almacén viaja como `None` (V1);
  - el trabajador no manda la tabla;
  - el padre no adopta;
  - el `_base` adoptado se ignora;
  - las lecturas ignoran el `_base`;
  - el final del trabajo no borra nada;
  - solo se borra el PID de `Popen`;
  - el prefijo sin el guion bajo.
- **Contra el árbol de 0.1.408**, fallan 5 de 6. El que pasa es el caso sin almacén, que no cambia.
- **Vecinos** (paralelo, pool, `pool_scope`, trabajos del API, servidor MCP, Cancelar, retroanálisis, `SliceShare`,
  la rejilla de la ventana en paralelo y los dos archivos del almacén): 213 de 213, y ya no queda ninguna carpeta en
  `%TEMP%\ogr_slices`.
- **La huella del banco de pruebas** (`orquestar.py version` y `version_serie`, con `comparar_version.py`): **23/23
  idénticos a 0.1.377 en las cuatro pasadas.**
  - Con los valores por defecto y con el volcado forzado (`OGR_VOLCADO_FORZADO=1`, comprobado en la procedencia de cada
    corrida).
  - En `version_serie`, también serie = paralelo en los 12 casos con pool.
  - Con el volcado forzado, cada evaluación de una rejilla repartida se lee de un registro que hizo un trabajador y
    escribió el padre, y es idéntica bit a bit a 0.1.377.
  - **K03 en paralelo** (51×51×12, dos métodos), en el proceso principal, medido al final de la corrida del banco:
    - conjunto de trabajo: 4226 MB en 0.1.408, 379 MB en 0.1.409;
    - pico de memoria comprometida: 4509 MB y 590 MB;
    - tiempo: 64,9 s y 59,8 s (una corrida de cada, dentro del ruido).
  - **Camino equivocado:** la primera comparación dio «MISSING» en los 23 casos, y no por el motor.
    - Mi lanzador pasó a `orquestar.py` la salida como ruta relativa, y los trabajos corren con el repositorio del
      programa como carpeta de trabajo, así que las 70 corridas se escribieron en `OGR-Slip2D/datos/`.
    - Se movieron al banco y se volvieron a comparar sin volver a correr nada. La carpeta del repositorio se borró, y
      `git status` no recoge nada de ella.
    - `orquestar.py` hace ahora absoluta la ruta relativa (ver §3).
- **El caso de la prueba en paralelo** (`_auditoria/P8_interfaz/d383_medir_v1.py paralelo`,
  `d383_v2_prueba_paralelo.log`; 51×51×12, cuatro métodos, el pool por defecto):
  - los cuatro factores son los de 0.1.407, con todos sus dígitos;
  - 115 036 evaluaciones, de las que 115 032 se vuelcan;
  - **el proceso principal retiene 922 MB (8,41 kB por evaluación), con un pico de 1178 MB.** Sin volcar eran ~7,9 GB;
  - la corrida tarda 234 s (en serie, 371);
  - el archivo ocupa 354 MB, y leer una superficie cuesta 0,21 ms de mediana;
  - la carpeta se va al soltar el resultado: la sonda corregida en 0.1.408 ya no se sujeta a sí misma.
  - En serie retiene 1386 MB, con un pico de 3055: es el `SliceShare` (D393), que la rejilla repartida no usa.
- **La suite entera con `--jobs 4`:** 6990/6990, sin fugas ni tramos muertos, en 24,8 min, y ninguna carpeta en
  `%TEMP%\ogr_slices` al terminar. La suite de 0.1.408 dejaba tres, de los trabajos del API y del MCP cancelados.
  - **Aviso `SLOW, NOT IN tests/_slow.txt`:** `test_search_notes_v1349.py` tardó 92,9 s, y en la corrida de 0.1.408
    no pasó de 90.
  - Medido solo, alternando árboles: 17,8 s con 0.1.409, 19,3 s con 0.1.408 y 16,7 s con 0.1.409. El código no lo ha
    encarecido; los 92,9 s son de su tramo en la corrida en paralelo.
  - La lista de lentos no se reescribe por una sola medida con ruido.

## 3. El banco

- **El manifiesto de las entradas separa sus dos trabajos** (`_auditoria/COMPUTO/bench/orquestar.py`, opción D,
  decisión de la propietaria del 2026-11-02).
  - **El problema:** una sola comparación de hashes, contra los de 0.1.377, hacía dos trabajos:
    - vigilar que un lote no escriba en sus entradas;
    - garantizar que una comparación con 0.1.377 usa las mismas entradas.

    La migración de D388 (0.1.403) cambió a propósito el `modelo_fem.ogr` del 010. Desde entonces todos los lotes
    salían con 1 sin haber fallado nada, y una escritura de verdad habría dado el mismo 1.
  - **Ahora, dos comprobaciones:**
    - **lo que cambió el lote:** hashes de antes contra los de después; si difieren, sale con 1;
    - **la deriva respecto a la referencia:** hashes de hoy contra los de 0.1.377. Un cambio registrado en
      `aceptados` (con `orquestar.py aceptar --ruta … --motivo …`: el hash nuevo, el motivo y la fecha) se imprime y
      deja pasar el lote; uno sin registrar sale con 1.
  - El de D388 está registrado, con su motivo. Los 23 hashes de referencia siguen idénticos, y el manifiesto plano
    original está copiado en `datos/manifiesto_0.1.377_plano.json`.
  - `orquestar.py manifiesto` se niega a sobrescribir un manifiesto que ya existe.
  - Un `--salida` relativo se hace absoluto contra la carpeta desde la que se llama.
  - **Probado:**
    - las funciones, sobre archivos temporales: sin cambios, deriva sin registrar, deriva registrada, una escritura del
      lote, y un segundo cambio de una entrada ya aceptada;
    - una tanda real con K17 y salida relativa: sale con 0, imprime el cambio aceptado, no escribe nada en el
      repositorio, y K17 sigue idéntico a 0.1.377.
  - `bench/LEEME.md` lo describe.

## 4. Lo que queda

- **V3:**
  - las demás búsquedas;
  - los `screen_states` del desembalse;
  - volver a volcar al cruzar un proceso: hoy un resultado leído de `result.pkl` materializa todas sus dovelas.
- Después, `d383()` y el cierre. Luego, D393.

## Archivos

- `ogr_slip2d/slice_store.py`, `ogr_slip2d/search.py`
- `ogr_api/jobs/__init__.py`, `ogr_api/jobs/worker.py`
- `tests/test_slice_store_parallel_v1409.py` (nuevo), `tests/test_slice_store_v1408.py`
- `docs/changelog/CHANGELOG_v0.1.409.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` y
  `ogr_mcp` (el número; `ogr_gui/main_window.py` también lo lleva)
