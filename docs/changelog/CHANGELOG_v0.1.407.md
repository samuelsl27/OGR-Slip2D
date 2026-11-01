# OGR Slip2D v0.1.407

**Archivo → Nuevo, y Cargar talud de demostración, sustituyen el proyecto solo si sus cambios se han guardado o
descartado (D392).**

Es el hermano de D391, reportado al cerrarla en 0.1.406 y abierto por decisión de la propietaria. Del plan de la
prueba de la interfaz de 0.1.397 sigue abierta D383.

Ningún número se mueve.

## 0. Lo que se encontró

- **El código:** `act_new` preguntaba con `_ask_unsaved` y, con Guardar, llamaba a `act_save()` y seguía al proyecto
  nuevo sin mirar si había guardado.
  - En un proyecto nunca guardado, `act_save` abre Guardar como. Cancelarlo, o un error al escribir (que `act_save`
    dice en un aviso), deja `is_dirty` en True, y `act_new` sustituía igualmente el proyecto por uno vacío.
  - Los cambios se perdían sin aviso justo cuando el usuario había pedido guardarlos.
- **Las otras puertas ya lo comprobaban:** `closeEvent` (D283, 0.1.296) y `act_open` (D391, 0.1.406, con
  `_may_replace_project`).
- **Cargar talud de demostración (`act_load_demo`),** mirado como pedía la ficha y reportado antes de tocarlo:
  - hacía su propia pregunta Sí/No, sin Guardar;
  - la hacía con `QMessageBox.question` directo, sin la guarda de `_ask_unsaved` para la plataforma `offscreen`.
    Con un proyecto con cambios, un test se habría quedado colgado en el diálogo modal. Ninguno lo hacía, porque
    los ~28 tests que la llaman lo hacen sobre una ventana recién creada.
  - La propietaria decidió que siga la misma regla que Nuevo y Abrir.
- **La discriminación lo confirma:** con el árbol de 0.1.406, el test del Guardar que no guarda en Nuevo falla, y
  los tres de la demo se quedan colgados en el diálogo modal (cortados a los 90 s).

## 1. Qué cambia

- **`ogr_gui/main_window.py`:**
  - **`act_new`** llama a `_may_replace_project(tr("New Project"))` y no sigue si devuelve False.
  - **`act_load_demo`** llama a `_may_replace_project(tr("Load Demo Slope"))`: la pregunta de siempre, con Guardar,
    Descartar y Cancelar.
  - Sin textos nuevos. La cadena «Current project has unsaved changes. Load demo anyway?» queda sin uso. Su
    entrada en español se queda, porque ningún test protesta por las claves sin uso.
- **`tests/test_new_asks_v1407.py`**, nuevo: 8 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_new_asks_v1407.py`,** con la ventana real y la pregunta y el diálogo de guardar sustituidos, sin
  ningún diálogo modal:
  - Nuevo:
    - un proyecto sin cambios se sustituye sin preguntar;
    - Cancelar no crea nada;
    - Descartar crea el vacío;
    - Guardar guarda y crea el vacío;
    - un Guardar que no guarda (Guardar como cancelado) enseña el diálogo y deja el proyecto, con sus cambios.
  - Cargar talud de demostración: Cancelar no carga nada, Descartar carga la demo, y un Guardar que no guarda deja el
    proyecto.
- **La discriminación,** con el árbol de 0.1.406 (`git archive 3f921cb`): falla el Guardar que no guarda de Nuevo, y
  los tres de la demo se cuelgan. Los otros cuatro de Nuevo son guardas.
- **Los vecinos:** cerrar con cambios, Abrir, los menús, las traducciones, el informe de coeficientes (que llama a
  `act_new`), las reglas F2 y deshacer en la ventana: 107 de 107.
- **La suite entera con `--jobs 4`:** **6972 de 6972, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 24,9 min.
  `TextInputHost.exe` estaba girando en un núcleo durante toda la corrida (4,7 s de CPU cada 5 s), el mismo síntoma
  de octubre, así que el reloj no es una medida. La serie no toca: 8 commits desde la última, y la versión no toca el
  pool.

## 3. El banco

- **D392 cerrada,** CUBIERTO POR TEST.
  - `d392()` en el `verificar_cierres.py` de la raíz, con la ventana real: un proyecto con cambios y sin ruta, con
    Guardar y el Guardar como cancelado, sigue siendo el mismo y sigue sucio; Cancelar no cambia nada; Descartar crea
    `Untitled`. La demo no entra en la comprobación: con el árbol viejo se quedaría colgada en su diálogo modal.
  - Discriminada: con el árbol de 0.1.406 da SIGUE ABIERTO («Nuevo sustituye el proyecto aunque el Guardar no
    guarde»), con el test copiado dentro para que decida el comportamiento y no su ausencia; con este, CUBIERTO POR
    TEST.
  - **Un camino equivocado en la discriminación:** la primera vez cargó el `ogr_gui` instalado, no el del árbol viejo,
    porque `banco.py` pone el repositorio el primero de `sys.path` al importarse. El «SIGUE ABIERTO» salía solo
    porque faltaba el test. La segunda pasada pone el árbol viejo delante después de importar el banco y vacía los
    `ogr_*` de `sys.modules`.
  - Instantáneas `Evaluaciones/0.1.407` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos (71 AVISO en la raíz, los mismos que en 0.1.406).

## 4. Lo que queda

- **D383** (las dovelas de la población en RAM), con su revisión de diseño antes de escribir código.
- **La próxima prueba a mano en la ventana** de D388–D392.

## Archivos

- `ogr_gui/main_window.py`
- `tests/test_new_asks_v1407.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.407.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`, `ogr_cli`, `ogr_api` y
  `ogr_mcp` (el número; `ogr_gui/main_window.py` también lo lleva)
