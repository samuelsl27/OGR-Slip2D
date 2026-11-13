# OGR Slip2D v0.1.445

**Un círculo que sale del contorno exterior entre sus cortes con el terreno dice por qué, y el censo lo cuenta como
el −103 de la referencia (D420).** Hasta ahora la búsqueda lo descartaba sin motivo ni cuenta, y las tres puertas
daban una razón falsa. Medido con 0.1.444, talud de ejemplo, círculo de centro (25, 20) y radio 21, que corta el
terreno en x = 4,604 y 45,396 y baja hasta y = −1, por debajo del fondo (y = 0):

| puerta | 0.1.444, Área mínima por defecto | 0.1.444, Área mínima 0 | ahora |
|---|---|---|---|
| la corrida (nota del círculo del usuario) | «Minimum Area 1 (the search's default…)» | «does not meet the ground twice» | «between its two crossings with the ground the circle runs outside the External Boundary… (the reference's error -103). Composite Surfaces makes a circle follow the base of the External Boundary instead.» |
| `evaluate_surfaces` y `surface_evaluate` | «does not cut the model» | «does not cut the model» | la misma frase |

| censo (Ordinario, la rejilla de la referencia) | −103 publicado | 0.1.444 | ahora |
|---|---|---|---|
| Ej_1, 4851 círculos | 183 | sin código; `not_sliced` 429 | −103: 183; `not_sliced` 246 |
| Ej_2, 4840 círculos | 287 | sin código; `not_sliced` 376 | −103: 287; `not_sliced` 89 |
| talud de ejemplo, rejilla x 20..35, y 20..30, 7 × 7 × 11 | — | sin código | −103: 12, los 12 de la forma cerrada |

El censo es el de la **población** de la búsqueda: el paseo de refinado de la Slope Search evalúa círculos que no son
de ella, y lo que cuentan ya no entra (eso arregla también el −101 de D263, que tenía el mismo defecto desde
0.1.261). Interpretar deja de decir «Todas las superficies se evaluaron correctamente.» de una corrida que rechazó
algo, en su resumen y en el filtro.

Es la decimoctava versión de la tanda P10 y la primera del plan aprobado el 2026-11-13 (D420, D403, D424). **Ningún
factor ni ninguna superficie crítica cambia:** se analizan las mismas masas.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.444 (7ac4a6b):** el guion de la ficha (`medir_d420.py`) da lo mismo que con 0.1.435: las tres
  frases falsas, los 12 de la forma cerrada y las dos sumas.
- **Las sumas se sostienen círculo a círculo.** Clasificando por qué cae cada cuerda (`paso0_d420.py`): en Ej_1, 172
  círculos tienen todas sus masas por debajo del fondo y 11 caen antes, por curvatura inversa con la grieta fuera del
  perfil (x = cx ∓ R fuera del modelo: el arco sale por un **lado**); 172 + 11 = 183. En Ej_2, 207 + 80 = 287.
  Ningún círculo de Ej_1, de Ej_2 ni del talud de ejemplo pierde una masa así y entrega otra.
- **El rebanador también se llama −103** (`slicer.py`: una base de dovela fuera del suelo). En Ej_1 y Ej_2 no salta
  nunca (`_outside_model` = 0), así que el censo coincide con lo publicado sin él. Su comentario dice ahora qué
  cuenta cada uno.
- **La zona de la grieta tenía el mismo defecto** (sin medir en la ficha): con una grieta de tracción a la cota 22 en
  el talud de ejemplo, 86 círculos de una rejilla junto a la coronación caen solo por estar enteros dentro de la
  zona, y el círculo (10, 30) de radio 5,5 decía «does not cut the model» en `evaluate_surfaces` y culpaba al «Minimum
  Area 1» en la corrida. Entra con su frase, sin censo (decisión R3 del plan).
- **Con la opción «Crear grieta de tracción por curvatura inversa» desactivada**, 640 círculos de Ej_1 caen por esa
  opción y el −103 baja a 13. Esos 640 tienen su frase y no cuentan como −103: es la opción del usuario, no el
  modelo.
- **La ventana de Interpretar tenía su propio censo** (`_query_invalid_summary`): contaba solo las evaluaciones y
  llamaba a todo lo demás «descartadas antes del dovelado, sin código de error». Ya contradecía los −101 de D263, y
  esta versión habría añadido el −103. Además, en un modelo cuyos rechazos no dejan evaluación (el muro de D77: 27
  círculos que no cortan el terreno) decía «Todas las superficies se evaluaron correctamente.». Ahora lee el censo
  (decisión R4 del plan). El prompt suponía que la frase «%d más se descartaron…» bajaría sola; no era así.
- **`filter(code=-103)` da siempre 0:** esos círculos no se dovelan, así que ninguna superficie lleva el código. Lo
  dicen el API, la descripción de `results_query` y la guía del agente (`ogr_mcp/guide.py`, que repetía la lista de
  códigos y el prompt no nombraba).
- **La referencia del test ya estaba en la suite:** `tests/test_m_alpha_screening_v1189.py` tiene el −103 = 183 de
  Ej_1 para los siete métodos, leído del informe publicado. El test nuevo lo importa. El 287 de Ej_2 está escrito en
  la cabecera de `tests/test_slide_validation_ej2_v184.py`, y ningún test lo afirmaba.
- **Camino equivocado.** Escribí la forma cerrada del test mirando solo los cortes con la coronación y con el pie; el
  corte derecho de algunos círculos cae en la cara del talud. Ahora corta la circunferencia con cada tramo del
  terreno.
- **La revisión adversaria (dos agentes) encontró, los dos por separado, que el censo contaba círculos que no son de
  la población:** el paseo de refinado de la Slope Search llama a `evaluate_circle` dentro de `_run`, antes de que
  `run()` copie los contadores al resultado, y un paso que falla no entra ni en `valid_count` ni en
  `invalid_count`. Medido en un talud con la forma del de ejemplo y el fondo a y = 14, un metro bajo el pie
  (Ordinario, 100 superficies de 10 dovelas): el borrador de esta versión daba −103 = 79 y −101 = 159; la población
  tiene 10 y 0. **El −101 de D263 tenía el defecto desde 0.1.261:** en Ej_1, Ej_2 y el talud de ejemplo, todos los
  −101 de una Slope Search venían del paseo (los círculos de la población pasan por el pie y la coronación, así que
  siempre cortan el terreno). Con esta versión la ventana los habría listado. Se arregla aquí por decisión de la
  propietaria. Ninguna otra búsqueda evalúa fuera de su población (leído): Simulated Annealing cuenta cada candidato
  (`_candidate`), Auto Refine cada prueba, Block y Path cada superficie, y la rejilla evalúa una vez por círculo; en
  el enjambre de partículas lo midió la revisión (el mismo −103 con y sin la memoria de D377).
- **La revisión encontró además, y entran por decisión de la propietaria:**
  - el resumen de Interpretar, cuando solo quedan descartados sin código (la curvatura inversa con la opción
    desactivada y todas las evaluaciones válidas), decía «2 more were discarded…» con nada listado delante y dos
    líneas en blanco (en 0.1.444 decía, falsamente, «Todas las superficies se evaluaron correctamente.»);
  - el desplegable «Error code:» del filtro de Interpretar decía «Every surface evaluated successfully.» siempre que
    ninguna evaluación tuviera motivo, también con −103 o −101 contados (ya pasaba con los −101);
  - la frase de `leaves_external` decía «the lower edge of the model» y la interfaz llama a lo mismo «the base of the
    External Boundary»;
  - la frase de la opción desactivada decía «in the search options»: la casilla está en Opciones de superficie, y solo
    en los paneles Búsqueda por rejilla y Búsqueda de talud.
- **Camino equivocado en este changelog:** el borrador listaba `interpret_window` entre los patrones de los vecinos
  «comprobados con `--list`». No selecciona ningún archivo, y el runner no lo dijo: es D431, abierta desde 0.1.439,
  donde pasó lo mismo con tres patrones. Ahora cada patrón se comprueba por separado.
- **La primera corrida entera tras la revisión dio un fallo:** la guarda de memorias compartidas
  (`tests/test_shared_test_caches_v1378.py`) vio que el test nuevo lee la rejilla de Ej_2 de la memoria de
  `test_slide_validation_ej2_v184` (`_grid_search`), que en serie le da el objeto que calculó ese archivo y con
  `--jobs`, uno nuevo. Sus cinco lectores y el nuevo solo leen el resultado, así que entra en `ALLOWED` con esa razón,
  en vez de pagar otra rejilla de 4840 círculos.

## 1. Qué cambia

- **Núcleo** (`ogr_core/geometry/slip_circle.py`): `apply_reverse_curvature(…, reasons=None)` dice por qué descarta un
  círculo, con tres constantes: `REVERSE_CURVATURE_SIDE` (la grieta cae fuera del perfil), `…_DISCARDED` (la opción
  desactivada) y `…_NO_CRACK` (sin sitio para la grieta, con el terreno bajo el centro o sin anchura). Lo que
  devuelve no cambia.
- **Búsqueda** (`ogr_slip2d/search.py`):
  - `_candidate_surfaces` anota por qué cae cada cuerda y, **solo si no entrega ninguna masa**, registra el motivo;
    si alguna salió del contorno (por el fondo o por un lado), cuenta el círculo una vez como −103
    (`_count_leaves_external`). La rama de la masa nombrada (con los extremos ya puestos) igual;
  - `_RUN_COUNTERS` gana `_leaves_external`, y con él lo llevan el paralelo (D255) y la memoria (D377);
    `SearchResult.leaves_external` se toma junto a `misses_ground`, antes de Optimizar y de las superficies del
    usuario;
  - `_CENSUS_COUNTERS` nombra los tres contadores que lee el censo (`_outside_slope_limits`, `_misses_ground`,
    `_leaves_external`), y `_off_the_census()` los devuelve como estaban al salir. El paseo de refinado de la Slope
    Search corre dentro. Los contadores del rebanador no están: sus notas hablan de toda superficie que la corrida
    doveló, también las del paseo;
  - la nota «ninguna superficie válida» nombra los que salieron del contorno.
- **Frases con código** (`ogr_slip2d/search_note_messages.py`), con su español:
  - `leaves_external`: «…between its two crossings with the ground the circle runs outside the External Boundary, so
    part of the mass would not be soil (the reference's error -103). Composite Surfaces makes a circle follow the base
    of the External Boundary instead.»;
  - `reverse_curvature_side`: «…the circle turns back above its centre (reverse curvature), and the vertical tension
    crack that would end it falls outside the model: the arc leaves through a side of the External Boundary (the
    reference's error -103).»;
  - `reverse_curvature_discarded`: «…and "Create tension crack for reverse curvature" is off in Surface Options (the
    Grid Search and Slope Search panels), so such a circle is discarded.»;
  - `reverse_curvature_no_crack` y `tension_crack_zone`, sin −103;
  - `search.refused.leaves_external`: «{n} circles that leave the External Boundary between their crossings with the
    ground», distinta de «that left the model».
  La nota del círculo del usuario sale por `search.user_refused` y `evaluate_surfaces` por `refusal_text()`, sin
  código de nota nuevo.
- **Censo** (`ogr_slip2d/interpretation.py`): `ERROR_CODES` gana −103; `COUNTED_REJECTIONS` y `counted_rejections`
  son la única lista de los rechazos contados sin evaluación (los −101 de D244, D256 y D263, y el −103), que leen
  `invalid_summary` y la ventana. `not_sliced` baja en lo mismo.
- **Interpretar** (`ogr_gui/interpret_window.py`):
  - `_unevaluated_rejections` lee del censo los contados y `not_sliced`, para el resumen y para el filtro;
  - el resumen de inválidas lista también los contados, traducidos, y «%d más se descartaron antes del dovelado…» es
    `not_sliced`; sin nada listado delante dice «%d se descartaron antes del dovelado…», sin «más» ni la segunda línea
    en blanco. Solo de una corrida que no rechazó nada dice «Todas las superficies se evaluaron correctamente.»;
  - el desplegable «Error code:» del filtro, sin motivos por los que filtrar, dice esa misma frase solo de una corrida
    que no rechazó nada; si no, «No se puede mostrar ninguna superficie rechazada: se descartaron antes del
    dovelado.» (`_no_reason_text`).
- **Agente:** la vista `error_codes` lista el −103; la descripción de `results_query`, `ogr_mcp/guide.py` y
  `docs/mcp/herramientas.md` dicen qué es y que `filter` con él no lista ninguna. Las claves del JSON de
  `surface_evaluate` no cambian: cambia el texto de `notes`.

## 2. Qué se probó

- **`tests/test_left_soil_refusal_v1445.py`** (26 casos, unos 21 s solo: las rejillas de las dos referencias, Ej_1 en
  paralelo y Ej_2, que comparte la de su archivo cuando caen en el mismo proceso; la cabecera lo dice):
  - **referencias:** el −103 publicado de Ej_1, 183, con su rejilla en paralelo (el recuento vuelve de los
    trabajadores), y el de Ej_2, 287; y la forma cerrada del talud de ejemplo, calculada en el test cortando la
    circunferencia con el terreno, sin el programa: los 12 círculos que dice la búsqueda son exactamente los suyos;
  - las críticas de las dos rejillas y el factor con Composite, los de 0.1.444 (`_V1444`);
  - el círculo de la ficha en las tres puertas, en inglés y en castellano, sin «Minimum Area», «meet the ground
    twice» ni «does not cut the model», con Área mínima por defecto y 0; y la masa nombrada;
  - la salida por un lado, con su frase y contada; la opción desactivada y la zona de la grieta, con la suya y sin
    contar; `apply_reverse_curvature` sigue devolviendo un booleano;
  - una masa entregada responde por el círculo, y salir del contorno se dice antes que otro motivo (sobre el círculo
    de dos masas de Ej_2, con la contención sustituida: ningún círculo medido tiene los dos casos a la vez);
  - **el paseo no es la población:** en la Slope Search del talud con el fondo a 14, el censo es lo que contaron los
    círculos de la población, separados de los del paseo por la variable de su bucle; la premisa (el paseo cuenta −103
    y −101) va en su propio caso;
  - el censo del agente, la nota de la corrida que no encontró nada y el resumen de Interpretar, en los dos idiomas,
    con el muro de D77 que ya no se llama un éxito; el recuento del resumen suma desde sus propias líneas (lo listado
    más lo «más» es lo rechazado); el resumen sin nada listado y el de una corrida limpia; y el filtro.
- **Discriminación:** en el árbol de 0.1.444, sin el buscador editable, fallan 22 de 26. Pasan los tres de control
  (las dos críticas y el factor con Composite) y «una masa entregada responde por el círculo», que el árbol viejo
  cumple porque no decía nada de ningún círculo. «Una corrida limpia» falla allí porque no existe
  `_unevaluated_rejections`, no por lo que mide: 0.1.444 ya decía el éxito de una corrida limpia.
- **Mutantes** (`mutants_d420.py`, en el banco): 27, todos muertos (los 20 del borrador, dos con su texto puesto al
  día, y siete del paseo, del resumen sin nada listado y del filtro).
- **Cambian a propósito:**
  - `tests/test_search_notes_v1349.py`: las muestras de las claves nuevas y el conjunto de motivos que registra una
    búsqueda;
  - `tests/test_f3b_ops_v1201.py`: la suma de `by_code` y la identidad por código ganan los contados sin evaluación
    (su talud tiene tres círculos que salen por el fondo). «filter(code).count == by_code[code]» valía allí solo
    porque no tenía ninguno;
  - `tests/test_results_query_user_surfaces_v1442.py`: `_no_evaluation` pasa a ser por código;
  - `tests/test_shared_test_caches_v1378.py`: una entrada de `ALLOWED`, la rejilla de Ej_2 que el test nuevo lee.
- **Vecinos**, con los patrones `user_surface_note min_area_zero search_notes slope_limit_refusals f3b_ops
  composite_surfaces surface_purity disjoint_masses method_notes spanish_texts results_query_user_surfaces
  reverse_curvature ground_refusals polyline_endpoints drawdown_stage1 screen_error interpret m_alpha_screening i18n
  voice_and_terms mcp_server pool_threshold dxf_export_census core_layering left_soil_refusal slope_search acads
  search_effort` (cada uno comprobado por separado con `--list`): 628 casos en verde en 40 archivos.
- **La suite entera** con `--jobs 4`: **7564 casos, 7563 en verde, 0 fallos y 1 omitido**, sin fugas ni tramos
  muertos (tras la entrada de `ALLOWED`; la corrida anterior, 7562 y el fallo de la guarda). La serie no toca (23
  commits desde la última).

## 3. Qué queda

- **Sigue en P10:** D403 (0.1.446), que lee el motivo que esta versión registra, y D424 (0.1.447).
- **Se abre D434** (sin versión): la tabla publicada de Ej_1 pone 231 círculos bajo −1000, y OGR mide exactamente 231
  círculos que no cortan el terreno y desde 0.1.261 los censa como −101 («its −101 in its own words», D263).
  231 = 21 × 11 encaja con una fila entera de centros.
- **Reportado y sin tocar:**
  - la búsqueda que convierte círculos en polilíneas (`_evaluate_trial`) descarta sin motivo las polilíneas
    convertidas que salen del suelo. Es otro camino, sin doble cuenta;
  - Auto Refine respeta «Crear grieta de tracción por curvatura inversa», pero su panel de Opciones de superficie no
    la enseña (solo los de Búsqueda por rejilla y Búsqueda de talud);
  - el runner ignora en silencio un patrón que no selecciona nada si otro sí selecciona algo (`--list interpret_query
    interpret_window` sale con 0; `interpret_window` solo, con 2): es D431, abierta, y esta versión lo vuelve a medir;
  - el resumen de Interpretar pone los contados detrás de los motivos de las evaluaciones, así que la lista deja de ir
    de más a menos frecuente.
- **Banco:** las huellas de `_auditoria/COMPUTO/bench/` cambian por el censo, sin ningún factor distinto; en las
  corridas con Slope Search baja además el −101 que contaba el paseo.
