# OGR Slip2D v0.1.403

**Un «Calcular agua subterránea» que se niega a resolver deja el proyecto como estaba, con su campo; y el 010 del
banco guarda las condiciones con que calculó el suyo (D388).**

Es la primera versión del plan que salió de la prueba de la interfaz de 0.1.402
(`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.402.md`), y arregla su único FALLO. La propietaria abrió D388–D391 el
2026-11-01 y pidió empezar por esta.

Ningún factor de seguridad se mueve: el cambio solo afecta al camino en que la filtración no calcula nada.

## 0. Lo que se encontró

- **Lo que vio la prueba (hallazgo 1):**
  - el problema 010 del banco (ACADS 5) con su campo de filtración guardado da Bishop 1,4803266154071344 y Spencer
    1,482191161214981 en la rejilla de 15×15×10;
  - *Agua subterránea → Calcular agua subterránea* falló al momento («no hay ninguna condición de contorno de altura
    (Dirichlet)…») y el resultado pasó a caducado;
  - el Calcular siguiente se negó: «este proyecto no tiene ningún campo calculado».
- **El motor:**
  - `solve_project_groundwater` escribía su resultado en el proyecto también cuando el solucionador se negaba. Un
    resultado así no tiene alturas, solo el motivo en `notes["error"]` (sin ninguna altura impuesta, o malla vacía);
  - con él vaciaba los transitorios, el estado inicial y las cachés, y la ventana lo copiaba al proyecto vivo
    (`_take_field`);
  - el transitorio cuyo estado inicial no se resuelve (D341) hacía lo mismo con su resultado vacío.
  - **El API ya se protegía desde 0.1.200:** `_finish_groundwater` solo copia un campo con `total_head`. La regla
    vivía en una capa y no en la puerta que comparten todos.
- **El banco:**
  - el `construir_modelo.py` del 010 calcula el campo con sus propias condiciones (el embalse a 26 m y aguas abajo a
    32 m) y no las guardaba en el proyecto, así que `modelo_fem.ogr` traía el campo sin las condiciones que lo
    producen;
  - al recalcular, la puerta pone las condiciones por defecto, sin ninguna altura, y el problema es singular;
  - el campo guardado declara 42 nodos de Dirichlet: 39 de altura fija y 3 de la cara de rezume que quedaron a
    presión cero.
- **Una consecuencia que había que medir antes de tocar el banco:**
  - las condiciones de una filtración también prescriben el agua embalsada cuyo peso lee el equilibrio límite
    (`ogr_core.hydraulic.ponded_water._fea_ponding_runs`): sin condiciones guardadas, el 010 por elementos finitos se
    calculaba sin el peso de su embalse sobre la banqueta;
  - medido en memoria antes de escribir nada (`_auditoria/P8_interfaz/d388_charca_010.py`): con las condiciones
    aparecen las dos láminas (el embalse a 26 m entre x = 15 y 31,6, y aguas abajo a 32 m), y Bishop y Spencer en la
    rejilla de 15×15×10 salen **idénticos bit a bit** con ellas y sin ellas, porque el círculo crítico no pasa bajo el
    embalse.

## 1. Qué cambia

- **`ogr_slip2d/transient_stability.py`:**
  - `_has_field(results)`: si algún resultado lleva alturas (`total_head`), el mismo predicado que el API;
  - `solve_project_groundwater`, en permanente, y `_solve_transient`: si no hay campo, devuelven el resultado con su
    motivo y no tocan el proyecto (el campo, los transitorios, el estado inicial, el solucionador y la caché del
    embalse);
  - un campo calculado se escribe igual que antes, haya convergido o no.
- **`ogr_gui/main_window.py`, `_compute_transient`:** devuelve los resultados de las etapas de la corrida
  (`outcome.stages`) y no los del proyecto. Cuando la corrida resuelve son los mismos objetos que `_take_field` acaba
  de poner en el proyecto. Cuando el estado inicial falla, es el resultado que lleva el motivo.
  - **El camino equivocado que lo destapó:** con el motor ya arreglado, el test de D341 se colgaba. La ventana leía el
    resultado en `project.transient_results`, que ahora queda vacío, y con la lista vacía `_compute_groundwater` abría
    un aviso modal («Transient analysis produced no results.»). En los tests se cuelga para siempre, y en la ventana
    real habría tapado el motivo verdadero.
- **`tests/test_seepage_run_notes_v1352.py`:** su test del transitorio de D341 leía el resultado fallido en
  `p.transient_results`, que es justo lo que D388 quita. Ahora comprueba que el proyecto, que no tenía etapas, sigue
  sin ellas. El motivo se sigue comprobando en los mensajes, sin cambios.
- **`tests/test_undo_materials_water_v1303.py`, tres tests que pasaban sobre el defecto,** destapados por la primera
  suite entera:
  - `test_compute_groundwater_is_a_step_and_marks_the_project`, `test_an_agent_field_marks_the_window_project` y
    `test_with_an_agent_step_in_between` calculaban el agua de la demostración con las condiciones por defecto de su
    malla, que no imponen ninguna altura;
  - medido con 0.1.402: aquel *Calcular agua subterránea* era la negativa del solucionador (0 alturas, «no Dirichlet»),
    y los tests pasaban porque el resultado vacío se escribía y contaba como el paso de deshacer;
  - ahora `_with_head` añade una altura en el borde izquierdo (23 m) a las condiciones por defecto, fuera de todo paso,
    y el tercero la pone con el `seepage_bc_set` del agente, que suma su paso «Set boundary conditions» a la historia;
  - los tres comprueban ya un campo de verdad (55 alturas), y pasan con el motor de 0.1.402 y con este.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_failed_seepage_keeps_field_v1403.py`,** sobre un rectángulo de un material con una malla gruesa:
  - una negativa en permanente conserva el campo, los transitorios, el estado inicial, el solucionador y la caché
    del embalse (los mismos objetos);
  - un transitorio cuyo estado inicial falla, también;
  - un campo calculado se sigue escribiendo, como guarda contra negarse de más;
  - con la ventana real, *Calcular agua subterránea* dice el motivo, conserva el campo, deja el resultado vigente y
    no deja paso de deshacer ni cambios sin guardar.
- **La discriminación:** con `transient_stability.py` y `main_window.py` de 0.1.402 fallan tres de los cuatro. El
  cuarto es la guarda.
- **Dos mutantes, uno por guarda del motor:** sin la del permanente, 2 fallos; sin la del transitorio, 1. Devolver
  los resultados del proyecto en la ventana lo caza el test de D341, que se colgaba.
- **El 010 del banco, a mano:**
  - la puerta arreglada conserva sus 791 alturas ante la negativa;
  - con las condiciones guardadas, el campo recalculado difiere del guardado en 5·10⁻⁸ m, y Bishop y Spencer en
    unos 2·10⁻¹⁰ (lo que la prueba esperaba en G.4: menos de 0,001).
- **Los vecinos:** filtración, transitorio, notas, desembalse, operaciones de agua, tareas en hilo, Cancelar y
  rescate: 296 de 296.
- **La suite entera con `--jobs 4`:**
  - la primera salió con 4 fallos: los tres tests de deshacer de arriba, y
    `test_api_jobs_v1194::test_progress_is_written_and_ends_complete`, que es la fragilidad de D371, abierta (un
    trabajo del API pierde a veces la última escritura de su `progress.json`), y que pasa entera al correr su
    archivo solo;
  - con los tests corregidos, **6951 de 6951, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 24 min;
  - la serie no se repite: la versión no toca el pool.

## 3. El banco

- **`02_Slide2_Problema010/construir_modelo.py`:** la regla de las condiciones sale a `condiciones_fem(mesh)`, y
  `construir_fem` guarda `p.seepage_bcs = b`.
- **`modelo_fem.ogr`, con una migración puntual** (`_auditoria/P8_interfaz/d388_migrar_010.py`), no con el
  productor:
  - volver a correr el productor habría remallado, resuelto otra vez y guardado con el esquema de hoy (diez claves
    nuevas);
  - la migración cambia solo el valor de `seepage_bcs`, de null a las condiciones que `condiciones_fem` da sobre la
    malla guardada, serializadas como lo hace `Project.to_dict`;
  - comprueba antes que el original se reescribe byte a byte y que 39 + 3 = 42;
  - tras escribir, el campo recargado es idéntico.
- **`resultados_modelo_fem.json`,** vuelto a correr con `ejecutar_caso.py --modelo modelo_fem.ogr --solo-publicado`:
  los cuatro FS sobre la superficie publicada, **idénticos** a los archivados en 0.1.188 (Bishop 1,478883, Spencer
  1,480204, GLE 1,479725 y Janbu corregido 1,440455). Cambian la versión y la huella del modelo.
- **La comparativa del 02,** regenerada (`generar_comparativa.py`): sus cuatro filas del 010 por elementos finitos
  pasan de 0.1.188 a 0.1.403, con los mismos números. Sin regenerarla, la auditoría del 02 daba 1 ERROR.
- **D388 cerrada,** CUBIERTO POR TEST.
  - `d388()` en el `verificar_cierres.py` de la raíz, sobre el `modelo_fem.ogr` del 010:
    - con sus condiciones vaciadas en memoria, la negativa conserva el campo;
    - el archivo lleva 39 alturas fijas y el productor las guarda;
    - recalcular con ellas reproduce el campo a 5·10⁻⁸ m.
  - Discriminada: con el motor de 0.1.397 da SIGUE ABIERTO («el campo se pierde»); con este, CUBIERTO POR TEST.
  - El `verificar_cierres` del 02 en seco sobre D113, la única comprobación que lee el 010: sigue CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.403` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.

## 4. Lo que queda

- **El plan, en orden:** D389 (cerrar Interpretar la destruye y suelta su resultado), D390 (Calcular y Abrir esperan
  al `.h5` pendiente) y D391 (Abrir pregunta si guardar). Después, D383.
- **Sin cambiar:** `_current_bcs` sigue escribiendo las condiciones por defecto en el proyecto cuando no tiene unas
  válidas; en la ventana ocurre sobre la copia de trabajo.

## Archivos

- `ogr_slip2d/transient_stability.py`, `ogr_gui/main_window.py`
- `tests/test_failed_seepage_keeps_field_v1403.py` (nuevo), `tests/test_seepage_run_notes_v1352.py`,
  `tests/test_undo_materials_water_v1303.py`
- `docs/changelog/CHANGELOG_v0.1.403.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
