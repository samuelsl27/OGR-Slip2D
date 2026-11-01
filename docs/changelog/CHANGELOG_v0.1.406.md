# OGR Slip2D v0.1.406

**Archivo → Abrir pregunta por los cambios sin guardar, como Nuevo y Salir (D391).**

Es la cuarta y última versión del plan que salió de la prueba de la interfaz de 0.1.402. De las cuatro fichas que
abrió (D388–D391) quedan todas cerradas; del plan anterior sigue abierta D383.

Ningún número se mueve.

## 0. Lo que se encontró

- **Lo que vio la prueba (hallazgo 4):** con cambios sin guardar, Abrir cargó otro `.ogr` sin preguntar tres veces
  (C.6, G.1 y J.1). Archivo → Salir sí preguntó.
- **El código:** `act_new` y `closeEvent` preguntan con `_ask_unsaved` desde 0.1.296 (D283), y `act_open` no miraba
  `is_dirty`: sustituía el proyecto y el trabajo se perdía sin aviso.
- **Las demás puertas, mirados:** el otro `Project.load` de la ventana es Importar propiedades, que copia materiales
  de otro archivo y no sustituye el proyecto. `project_open` del agente ya se niega con cambios sin guardar
  (`WindowHost.replace_project`).
- **Un defecto hermano, reportado y sin tocar aquí:** `act_new` llama a `act_save()` si se elige Guardar, pero no
  comprueba que haya guardado. Con un Guardar como cancelado, crea el proyecto nuevo igualmente y lo no guardado se
  pierde. `closeEvent` sí lo comprueba. Queda para la decisión de la propietaria.

## 1. Qué cambia

- **`ogr_gui/main_window.py`:**
  - **`_may_replace_project(title)`:** si no hay cambios, sí. Si los hay, la pregunta de Nuevo y Salir; sí solo con
    Descartar, o con Guardar si ha guardado de verdad. Un Guardar como cancelado o un guardado fallido dejan el
    proyecto donde estaba.
  - **`act_open`** la llama antes del diálogo de archivo, como Nuevo pregunta antes de nada.
  - Sin textos nuevos: el título es el del diálogo de abrir y la pregunta, la de Nuevo, los dos con su castellano.
- **`tests/test_open_asks_v1406.py`**, nuevo: 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_open_asks_v1406.py`,** con la ventana real y la pregunta y los diálogos de archivo sustituidos, sin
  ningún diálogo modal:
  - un proyecto sin cambios abre sin preguntar;
  - Cancelar no abre nada, ni enseña el diálogo de archivo;
  - Descartar abre;
  - Guardar guarda y abre;
  - un Guardar que no guarda (Guardar como cancelado) no abre nada;
  - un diálogo de archivo cancelado después de Descartar deja el proyecto como estaba.
- **La discriminación:** con el `main_window.py` de 0.1.405 fallan los tres que dependen de la pregunta. Los otros
  tres son guardas.
- **Un mutante,** abrir tras Guardar sin comprobar que guardó: lo caza el test del Guardar que no guarda.
- **Los vecinos:** cerrar con cambios, los menús, el puente y las traducciones: 105 de 105.
- **La suite entera con `--jobs 4`:** **6964 de 6964, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 23 min. La serie
  no se repite: la versión no toca el pool.

## 3. El banco

- **D391 cerrada,** CUBIERTO POR TEST.
  - `d391()` en el `verificar_cierres.py` de la raíz, con la ventana real: con cambios, Cancelar hace una pregunta, no
    enseña el diálogo de archivo y deja el proyecto; Descartar abre el otro.
  - Discriminada: con el árbol de 0.1.397 da SIGUE ABIERTO («0 preguntas, diálogo de abrir, proyecto otro»); con este,
    CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.406` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.

## 4. Lo que queda

- **D383** (las dovelas de la población en RAM), con su revisión de diseño antes de escribir código.
- **El defecto hermano de Nuevo**, si la propietaria quiere ficha.
- **La próxima prueba a mano en la ventana** de D388–D391: el agua sobre el 010, la memoria tras cerrar Interpretar,
  el diálogo de espera del `.h5` y la pregunta de Abrir.

## Archivos

- `ogr_gui/main_window.py`
- `tests/test_open_asks_v1406.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.406.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` y
  `ogr_mcp` (el número; `ogr_gui/main_window.py` también lo lleva)
