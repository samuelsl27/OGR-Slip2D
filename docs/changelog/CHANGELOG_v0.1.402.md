# OGR Slip2D v0.1.402

**Un análisis del agente sobre la ventana se carga una sola vez, y la ventana y el API comparten el mismo resultado
(D387).**

Es la quinta versión del plan que salió de la prueba de la interfaz de 0.1.397, y la última del bloque de arreglos
pequeños. Quedan la prueba a mano redimensionada y D383 (las dovelas de la población), que lleva revisión de diseño.

Ningún número se mueve.

## 0. Lo que se encontró

- **De dónde sale:** del censo de D383 (2026-11-01), al buscar quién retiene resultados en el proceso de la ventana.
- **El mecanismo:**
  - `_finish_analysis` guardaba el resultado con un cargador perezoso (`loader=job.load_results`);
  - si el agente trabajaba sobre la ventana y el modelo seguía siendo el analizado, deserializaba `result.pkl` para
    enseñarlo allí;
  - a la primera pregunta (`results_get`, `results_query`), el `StoredResult` llamaba otra vez al mismo cargador y
    guardaba lo que devolvía.
- **Consecuencia:** dos copias completas del mismo resultado, con sus dovelas, en el proceso de la ventana. A 57 kB por
  evaluación (D383), en una rejilla grande son gigas. Viene de 0.1.203.
- **Los otros finalizadores, mirados:**
  - el barrido, la estadística y la optimización no cargan nada al terminar;
  - el agua subterránea carga el resultado para copiarlo dentro del proyecto y lo suelta. Guardarlo en el resultado del
    API retendría memoria que la ventana no usa, así que se queda como está.

## 1. Qué cambia

- **`ogr_api/ops/analysis.py`:** `_finish_analysis` carga el resultado con `res.payload()` del `StoredResult` que
  acaba de guardar, que se lo queda, y se lo pasa a la ventana. Sin ventana, o con el modelo cambiado, no carga nada,
  como antes: carga perezosa a la primera pregunta.
- **`tests/test_agent_result_loaded_once_v1402.py`**, nuevo: 3 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_agent_result_loaded_once_v1402.py`,** con un espacio de trabajo y resultados guardados reales, y un
  trabajo falso que cuenta las cargas y da objetos nuevos en cada una, como `result.pkl`:
  - con ventana, una carga, y la primera pregunta devuelve los mismos objetos que enseña la ventana sin cargar otra
    vez;
  - sin ventana, ninguna carga hasta la primera pregunta, y luego una;
  - con el modelo cambiado, ni se enseña ni se carga.
- **La discriminación:** con el `analysis.py` de 0.1.401 falla el primero («the stored result loaded it again»). Los
  otros dos son guardas.
- **Un camino equivocado, mío:** la primera versión del trabajo falso devolvía siempre el mismo objeto, así que la
  comprobación de que se compartía pasaba también con dos cargas. Solo el recuento discriminaba. Ahora cada carga da
  objetos nuevos y las dos comprobaciones miden.
- **Un mutante,** cargar siempre aunque no haya ventana: 2 fallos.
- **Los vecinos:** el puente en vivo, los trabajos y las operaciones del API y el redibujo del lienzo, 71 de 71.
- **La suite entera con `--jobs 4`:** **6947 de 6947, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 24 min. La
  serie no se repite: la versión no toca el pool, y la última en verde es la de 0.1.399, tres commits atrás.

## 3. El banco

- **D387 cerrada,** CUBIERTO POR TEST.
  - `d387()` en el `verificar_cierres.py` de la raíz, con un espacio de trabajo real, una ventana falsa y un trabajo
    falso que cuenta las cargas y da objetos nuevos en cada una:
    - con ventana, una carga al terminar, ninguna más a la primera pregunta, y el resultado compartido;
    - sin ventana, ninguna carga hasta la primera pregunta.
  - Discriminada: con el árbol de 0.1.397 da SIGUE ABIERTO («1 carga al terminar, 2 tras la primera pregunta, dos
    copias»); con este, CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.402` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.
- **De las seis fichas abiertas el 2026-11-01** queda D383.

## 4. Lo que queda

- **La prueba a mano redimensionada a 31×31×12:** un prompt nuevo para Claude Desktop, con los valores esperados
  recalculados. Comprobará en la ventana D382 (la memoria tras Cancelar), D384 (Cancelar en paralelo), D385 (sin
  cuelgue tras Calcular) y D386, y las secciones que quedaron bloqueadas.
- **D383,** con su revisión de diseño antes de escribir código.

## Archivos

- `ogr_api/ops/analysis.py`
- `tests/test_agent_result_loaded_once_v1402.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.402.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
