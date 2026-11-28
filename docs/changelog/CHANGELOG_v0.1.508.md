# OGR Slip2D v0.1.508

**D444: los tres caminos de la ventana que añadían contornos sin la regla de su tipo preguntan ahora
la regla del núcleo, igual que el agente.** Las reglas son de OGR Core 0.2.14: `boundary_refusal`
con la polilínea, `import_refusal` y `conversion_refusal` sobre la polilínea convertida. Slip2D las
fija desde 0.1.505. Una importación que deja dos contornos de un tipo único se rechaza entera, por
decisión de la propietaria del 2026-11-27.

## 0. Lo que se encontró

- **El defecto, medido con 0.1.455** con el guion del banco
  `_auditoria/P10_D443_D444/medir_d443_d444.py`, en el talud de ejemplo:
  - **Convertir herramienta en contorno** añadía un segundo nivel freático, un segundo exterior
    (además abierto) y una segunda grieta. El agente rechazaba los tres;
  - **Importar DXF** sin sustituir escribía un segundo exterior, que el constructor de regiones no
    lee nunca. El agente lo rechazaba;
  - **Convertir contorno** hacía línea piezométrica o capa débil de una polilínea que se corta a sí
    misma. El agente la rechazaba.
- **El agente tenía las dos comprobaciones escritas a mano:**
  - la autointersección después de editar;
  - los dos exteriores, contados después de escribir la importación (el paso atómico lo deshacía).

  Las dos dejaban pasar un segundo nivel freático, una segunda grieta o una segunda línea de
  desembalse llegados por el DXF. Ahora pregunta la regla del núcleo antes de escribir, y los
  rechaza también.
- **Para poder probarlo sin diálogos**, los dos caminos con diálogos modales se partieron:
  `_convert_annotation` es el paso de después de los dos `QInputDialog` de Convertir herramienta en
  contorno, y `_apply_dxf_import`, el de después del diálogo de importación. Los diálogos llaman a
  esos pasos como antes.

## 1. Qué cambia

- `ogr_gui/main_window.py`:
  - `_convert_annotation` pregunta `boundary_refusal(project, btype, polyline=…)`. Si rechaza, la
    barra da el motivo y «The boundary was not added.», y el modelo no cambia;
  - `_apply_dxf_import` pregunta `import_refusal` antes de `apply_to_project`. Si rechaza, no se
    escribe nada, y la barra dice el motivo con el consejo de la ventana, que nombra su casilla («Tick
    «Replace existing boundaries of the imported types», or map only one layer to …»). El consejo
    del núcleo nombra los argumentos del agente;
  - `_boundary_refusal_text` traduce `self_intersecting`. Convertir contorno ya preguntaba
    `conversion_refusal`, y la autointersección le llega sola con el núcleo 0.2.14.
- `ogr_api/ops/files.py`: `dxf_import` pregunta `import_refusal` antes de escribir, con el consejo
  `import_hint` de cada tipo.
- `ogr_api/ops/model.py`: `boundary_edit` pregunta `polyline_refusal` en vez de su
  `has_self_intersections` propio. El texto es el mismo. **Un cambio para el agente:** convertir una
  polilínea que se corta a sí misma ahora lo rechaza `conversion_refusal`, que da `Conflict`, donde
  antes daba `InvalidArgument`. La frase no cambia.
- `ogr_gui/i18n/__init__.py`: el castellano de `SELF_INTERSECTING`, de los cuatro textos de
  `IMPORT_TWO` y del consejo de la ventana.

## 2. Lista de comprobación de la guía de interfaz

- Mensaje: cada rechazo dice qué pasa y qué hacer, con los controles de la ventana y en el idioma del
  lector; el modelo queda como estaba (test).
- Paridad entre puertas: la ventana y el agente dicen las mismas frases, porque leen las mismas
  reglas.
- Acción: Convertir herramienta en contorno sigue en su menú. Ningún diálogo nuevo, y ningún diálogo
  modal en el camino que corre el test.

## 3. Tests

- `tests/test_boundary_rules_d444_v1508.py` (nuevo, 11 tests, una ventana para todo el archivo):
  - Convertir herramienta en contorno: el segundo nivel freático, el segundo exterior y la polilínea
    que se cruza se rechazan con su motivo, y el control, un contorno de material, se añade;
  - Importar DXF sin sustituir: el segundo exterior y el segundo nivel freático no escriben nada y lo
    dicen, y el control con sustituir se escribe;
  - Convertir contorno rechaza la polilínea que se cruza;
  - el agente rechaza el segundo nivel freático del DXF con su consejo, y la conversión que se cruza
    con la misma frase;
  - el castellano de las frases nuevas.
- **Cambio declarado** en dos tests anteriores: las vistas previas falsas de
  `tests/test_spanish_paths_v1433.py` y `tests/test_undo_settings_annotations_v1305.py` llevan
  `sanitised={}`, el campo que lee la regla de importación. Una vista previa de verdad siempre lo
  tiene.
- Áreas `dxf`, `annotation`, `convert`, `boundary`, `mcp`, `api`, `i18n`, `translation`, `texts`,
  `terms`, `voice`, `budget`, `wrap` y `menu`, con `--jobs 4`: 628 en verde, después del cambio
  declarado.

## 4. Suite

La suite entera se corre al final de la tanda.
