# OGR Slip2D v0.1.363

**Los avisos del retroanálisis, de Optimizar superficies, del barrido de desembalse y de las etapas del
transitorio llegan a *Análisis > Notas del análisis*, cada uno bajo su cálculo y en castellano, y la barra
de estado dice que están ahí (D340, cerrada).** Primera versión de la tanda P8l.

## 0. Lo que se encontró

- **Cuatro cálculos devolvían avisos a la ventana y la ventana los tiraba:**
  - el retroanálisis: `res, _report, _warnings = run_configured_back_analysis(...)`;
  - Optimizar superficies: `best, res, rep, _report, _w = run_configured_optimization(...)`;
  - el barrido de desembalse, dentro de su hilo: `self.result, _report, _warnings = ...`. El trabajador
    no los guardaba;
  - el transitorio:
    - los avisos generales iban a la barra de estado, cada uno pisando al anterior, y el último lo pisaba
      la línea de la ventana;
    - los de cada etapa (`stage.warnings`, lo que dijo la búsqueda de esa etapa) y los del estado inicial
      no los leía nadie.
- **El retroanálisis tiene dos notas propias** (`composite_skipped` y `envelope_not_settled`), con código
  desde 0.1.352. La ventana leía solo `notes["error"]`.
- **La optimización tenía una tercera nota callada:** `rep.notes["snap"]`, cuando el ajuste de las
  superficies someras al talud da una superficie inválida (`OPT_SNAP_FAILED`). No va en `rep.summary()`,
  así que no se veía en ningún sitio. Ahora va al panel con los avisos.
- **El modelo del transitorio de los tests (Ej1) dice su dirección de rotura** en cada etapa y en el
  estado inicial: la coronación queda a la derecha y el terreno está más alto a la izquierda. Es una nota
  real que hasta hoy no llegaba a la pantalla en un transitorio. El test lo encontró al escribirlo, porque
  esperaba una sola nota por etapa.
- **Sin cambiar, dicho aquí:**
  - los avisos deterministas de Calcular estadística siguen sin ir al panel. Es la decisión D129 de
    0.1.236 (`CHANGELOG_v0.1.236.md`), y dos tests exigen `last_statistics_notes == []` en una corrida
    sana;
  - Optimizar superficies enseña en el panel de resultados el informe de la norma del último Calcular
    (`results_dock.show_result(new, self.last_factor_report)`), no el de su propia corrida. Con los
    mismos ajustes coinciden; si se cambiaron entre una y otra, el resultado de la búsqueda ya es viejo;
  - el barrido de desembalse también enseña el identificador del método, en la barra («Critical drawdown
    level (bishop_simplified)») y en la leyenda de su gráfico, y Optimizar superficies lo enseña en su
    lista de métodos. Es la familia de D343: se mira en 0.1.369.

## 1. Qué cambia

- **`ogr_gui/dialogs/analysis_notes_panel.py`:**
  - `populate(notes, sections=())` acepta secciones `[(título, [(subtítulo o None, notas)])]`;
  - cada cálculo con notas es un nodo de primer nivel, después de los de Calcular; dentro, cada nota
    con su método delante (`note_line`);
  - el transitorio lleva un subnodo por etapa: «0: t = 0 (estado inicial)» y «Etapa N: t = …» con su
    etiqueta;
  - *Copiar todo* añade las líneas de las secciones con su cálculo y su etapa delante;
  - **sin secciones, el árbol es el de antes**, nodo a nodo.
- **`ogr_gui/main_window.py`:**
  - `last_task_notes`: una entrada por cálculo, que reemplaza la de su corrida anterior. Una corrida
    rechazada la vacía, y `_attach_project` las vacía todas;
  - `_set_task_notes`, `_task_note_sections`, `_refresh_notes_panel` y `_with_notes_hint`. Los dos sitios
    que refrescaban el panel (Calcular y la estadística) pasan por `_refresh_notes_panel`, y así no pierden
    las secciones;
  - cada cálculo añade a su línea de la barra «[N nota(s) — Análisis > Notas del análisis]», solo si hay
    notas. El transitorio, como Calcular: primero su primera nota con «[+N más …]» y luego la línea de la
    ventana con el aviso;
  - un agua permanente vacía las notas del transitorio, porque reemplaza su campo;
  - `_DrawdownSweepWorker` guarda `warnings`, como `_ComputeWorker`.
- **Castellano:** 2 entradas nuevas: «{0}  [{1} note(s) — …]» y «Stage {0}: t = {1:g}».
- **Ningún número cambia, ni lo que devuelve el API.**

## 2. Tests

- **`tests/test_task_notes_v1363.py`** (nuevo, 9 casos), por la ventana real y en castellano:
  - **un aviso real por cálculo** (`model.slope_limits_one_side`: un segundo juego de Slope Limits con un
    solo lado, que los cuatro dicen y ninguno aplica) en el panel, bajo su cálculo:
    - el retroanálisis en el talud de ejemplo;
    - Optimizar superficies en el talud de `test_optimize_wiring_v1104`;
    - el barrido en el talud de Morgenstern;
    - el transitorio en el desembalse de `test_initial_factor_v1309`, con la nota bajo el estado inicial y
      bajo la etapa;
  - las dos notas propias del retroanálisis, con la corrida simulada: lo que se prueba es que la ventana
    las lee;
  - la barra dice cuántas notas hay y dónde;
  - **sin avisos, el panel es el de antes:** sin sección del retroanálisis, el mismo encabezado y el mismo
    árbol con y sin secciones vacías;
  - *Copiar todo* con las secciones.

**Con el código de 0.1.362 fallan los 9** (árbol de HEAD, sin el buscador del paquete editable).

## 3. Verificación

- **El test de esta versión:** 9/9.
- **Los vecinos:** 333/333 en 19 archivos: notas de Calcular, del modelo, de método y de búsqueda, la norma
  de cálculo, la estadística, el transitorio, el retroanálisis y la optimización, deshacer y el castellano.
  `test_seepage_run_notes_v1352` sigue en verde sin tocarlo: su espía busca la nota del transitorio al
  principio de una línea de la barra, y sigue estando.
- **Suite entera:** 6558/6558, `EXIT=0`, 91 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 97 comprobaciones (una más, `d340`).
    - D340 queda **CUBIERTO POR TEST**. Se mide en el código de la ventana (no queda ninguna de las tres
      asignaciones que tiraban los avisos) y, por la ventana real, con un retroanálisis de verdad del
      talud de ejemplo cuya nota llega al panel en castellano;
  - **una bajada que no era de esta versión: D366.**
    - Su comprobación exigía la sección `## D367` del ERRORES, y D367 se retiró al índice de cerrados en
      0.1.362, después de correr el verificador de esa versión. Cerrar D367 era justo lo que el cierre
      documental de D366 dejaba pendiente;
    - `d366()` acepta ahora D367 abierta o cerrada, y vuelve a CIERRE DOCUMENTAL;
  - manual 02: `verificar_cierres.py --seco`, 238 veredictos iguales a los archivados, ninguno distinto;
  - **D340 retirada** al índice de cerrados, podada de `PAQUETES` y tachada en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.363` (raíz, 979 archivos; 02, 3284), prompts (43) y auditorías con
    0 ERROR.
- **Encontrado al cerrar:** el defecto que el plan de la tanda pensaba abrir como D368 (Cancelar no para)
  **ya era D362**, de la sexta prueba de la interfaz (0.1.357), con más alcance. La tanda lo hará como
  D362, y no se abre ninguna ficha.

## 4. Pendiente

- La tanda sigue con D342 (0.1.364): un campo de filtración guardado pierde los códigos de sus notas.
