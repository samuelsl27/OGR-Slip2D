# OGR Slip2D v0.1.401

**Cambiar «Buscar superficies en paralelo» o el porcentaje de CPU ya no deja el resultado como «de un modelo
anterior» (D386).**

Es la cuarta versión del plan que salió de la prueba de la interfaz de 0.1.397. La propietaria dio su acuerdo el
2026-11-01: «como dices el cálculo en serie o paralelo no modifica resultados, por lo que ese mensaje no tiene
sentido al cambiar el ajuste».

Ningún número se mueve: el cambio está en la huella que decide si un resultado está caducado.

## 0. Lo que se encontró

- **Lo que vio la prueba (DUDA 4):** marcar o desmarcar la casilla en Ajustes de proyecto → Avanzado dejaba el panel
  en «Resultados de un modelo anterior: vuelve a calcular.», con los factores idénticos bit a bit en serie y en
  paralelo.
- **La causa:** `model_hash` (`ogr_api/snapshot.py`) hasheaba todo `to_dict` menos las anotaciones, y eso incluye
  `settings.advanced.parallel_search` y `parallel_cpu_percent`.
- **Por qué no deben contar:**
  - que una rejilla repartida en procesos sea la de serie es un invariante del motor: los lotes son contiguos y se
    reensamblan por orden de envío (`ogr_slip2d/search.py`, `_run_batches`), y `test_parallel_search_v197` lo
    protege;
  - el lote `version_serie` del banco de pruebas lo comprobó en los 12 casos con pool, 12 de 12, en cada versión de
    la fase 3 de la auditoría del cómputo y en 0.1.399.
- **No hay huellas guardadas en disco** que este cambio deje desfasadas: el API las guarda solo en memoria, y la
  `modelo_huella` del banco hashea el `.ogr` entero por su cuenta.

## 1. Qué cambia

- **`ogr_api/snapshot.py`:**
  - `COMPUTATION_MODE = ("parallel_search", "parallel_cpu_percent")`, con el porqué;
  - `model_hash` quita esas dos claves de `settings.advanced` antes de hashear.
  - La regla vive en la función que preguntan la ventana (`_check_results_stale`, `_results_are_current`) y el API
    (los `stale` de `ogr_api/ops`), así que las dos dicen lo mismo.
  - `document_hash` no cambia: los dos ajustes se guardan en el `.ogr`, y cambiarlos sigue pidiendo guardar.
- **`tests/test_model_hash_mode_v1401.py`**, nuevo: 3 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_model_hash_mode_v1401.py`:**
  - cambiar cada una de las dos claves no mueve `model_hash` y sí `document_hash`; y las dos existen en `to_dict`,
    porque si un cambio de nombre las moviera la regla quitaría una clave que ya no está y el test pasaría sin medir
    nada;
  - un censo sobre los campos de `AdvancedSettings`: cualquier otro mueve `model_hash`, así que un ajuste nuevo no
    puede quedarse fuera de la huella sin que se note;
  - en la ventana real, tras un Calcular, cambiar cualquiera de las dos deja el resultado vigente, y cambiar
    `check_m_alpha` lo marca como caducado.
- **La discriminación:** con el `snapshot.py` de 0.1.400 fallan dos de los tres («parallel_search made the result
  stale»). El censo es una guarda y pasa en los dos.
- **Dos mutantes, cada uno cazado con 2 fallos:**
  - dejar fuera solo `parallel_search`;
  - dejar fuera todo `advanced`.
- **Los vecinos:** los tests de la marca de resultado caducado, de los trabajos y las operaciones del API, de las
  notas y de las huellas: 25 + 154, todos en verde.
- **La suite entera con `--jobs 4`:** **6944 de 6944, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 23,5 min. La
  serie no se repite: la versión no toca el pool, y la última en verde es la de 0.1.399, dos commits atrás.

## 3. El banco

- **D386 cerrada,** CUBIERTO POR TEST.
  - `d386()` en el `verificar_cierres.py` de la raíz, sobre un proyecto nuevo: cambiar cada una de las dos claves no
    mueve `model_hash` y sí `document_hash`, y cambiar `check_m_alpha` sí lo mueve.
  - Discriminada: con el árbol de 0.1.397 da SIGUE ABIERTO («parallel_search, parallel_cpu_percent caduca el
    resultado»); con este, CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.401` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.

## 4. Lo que queda

- **El plan:** D387 (un análisis del agente se deserializa una vez).
- **Después:** la prueba a mano redimensionada a 31×31×12, y D383 con su revisión de diseño.

## Archivos

- `ogr_api/snapshot.py`
- `tests/test_model_hash_mode_v1401.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.401.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
