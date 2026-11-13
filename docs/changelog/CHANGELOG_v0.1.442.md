# OGR Slip2D v0.1.442

**Los listados del agente incluyen las superficies que dibujó el usuario, y dicen cuáles son (D400).** Una corrida
analiza esas superficies junto a las de la búsqueda, y desde 0.1.427 una polilínea del usuario puede ser su superficie
crítica. Pero `results_query` con `filter` y con `raw_data` leía solo la población de la búsqueda, y ningún listado
decía de quién era una superficie. Medido con 0.1.441 sobre el talud de ejemplo, con una búsqueda Path de 5 a la que
se añade la polilínea `_WINNER`, que pasa a ser la crítica:

| pregunta del agente | 0.1.441 | ahora |
|---|---|---|
| `filter fos_max=1.2` (Janbu, crítica 1,123199) | 0 superficies | 1, la del usuario, marcada |
| `raw_data` | las 5 filas de la búsqueda | 6 filas, y una séptima columna `user_defined` |
| `critical` del resumen de `analysis_run` | la polilínea, sin decir de quién es | `surface.user_defined: true` |
| `minimum_per_centre`, `slices`, `surfaces_through_point` | la incluían, sin marca | marcada |
| el censo (`error_codes`, `invalid_summary`, `filter` con `code`) | de la búsqueda | igual, a propósito |

Decisiones de la propietaria: la celda de `user_defined` lleva «1» o «0» (2026-11-12); y, en el resumen de la
versión (2026-11-13), la marca dentro de `surface`, que `results_get` también marque, y la nota de la muestra de
`raw_data`, que no estaba en el plan.

Es la decimoquinta versión de la tanda P10. **Ningún factor cambia.**

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.441 (a16295f):** el fragmento del prompt da lo que dice la ficha. Janbu: crítica 1,123199, del
  usuario; `filter fos_max=1.2`, 0; `raw_data`, 5 filas. Bishop con la polilínea que m-alfa rechaza: crítica
  1,178925, los contadores sin mover (6 generadas, 5 válidas) y el censo vacío.
- **La regla** (del plan): las vistas que LISTAN superficies incluyen las del usuario y las marcan; el CENSO no. El
  censo describe lo que generó la búsqueda, la población que cuentan `total_count` y los contadores (D263). Así sigue
  valiendo, para todo código, `filter(code).count == by_code.get(code, 0)`.
  - **Salvo en −101**, que ya no la cumplía: ahí el censo suma los rechazos que no dejan evaluación (un extremo fuera
    del terreno, la base por encima, fuera de los límites del talud, el círculo que no corta el terreno dos veces), y
    `filter` solo recorre evaluaciones. En −101 la identidad es con esas cuentas restadas.
- **Qué lista cada vista de una superficie del usuario,** que no es lo mismo en todas:
  - `raw_data`: todas, válidas o no, en las últimas filas;
  - `filter` por factor: las que ninguna comprobación rechazó (la vista siempre dejó fuera las que tienen código);
  - `filter` con `code`: ninguna, porque es el censo;
  - `minimum_per_centre`, `slices`, `surfaces_through_point`, y el `critical` y el `top`: las válidas, como ya hacían.
- **Dónde va la marca.** El plan lo dejaba a esta versión. Va **dentro de `surface`**, donde
  `back_analysis_summary` la pone desde 0.1.428: `"surface": {"type": "polyline", …, "user_defined": true}`. Así el
  resumen de una superficie se lee igual venga de donde venga (`critical.surface` de la corrida, `critical_surface`
  del retroanálisis). Una superficie de la búsqueda no lleva la clave: nunca es `false`.
- **`results_get` con `critical` y `top` lista las mismas superficies** y el prompt no lo nombraba. Es la misma
  regla y entra, con la misma función.
- **El resumen de `analysis_run` se escribe en el proceso del trabajador** (`ogr_api/jobs/worker.py`). Un mutante
  puesto en el proceso del test no llega ahí (la trampa de D375), así que el resumen tiene además su test en el
  mismo proceso.
- **Hacía falta un censo que no estuviera vacío.** La rejilla de 64 círculos de
  `tests/test_back_analysis_user_surfaces_v1428.py` (centros de x 30 a 45 y de y 40 a 55) deja 12 sin rebanar y ningún
  código: con ella la identidad del censo era `0 == 0`. Se usa una rejilla baja (centros de x 30 a 38 y de y 17 a 23)
  con un límite de talud a la izquierda (x = 24). Bajo Bishop da dos −112, cuatro −111 y once −101, y los once son
  círculos que los límites rechazan sin dejar evaluación. Con ella:
  - un círculo del usuario que m-alfa rechaza (centro (32, 16), radio 5, F = 3,0019) tiene el código −112 y no es uno
    de los dos;
  - otro, válido (centro (36, 28), radio 12, F = 1,185), es la crítica de la corrida.
- **Reportado y sin tocar** (regla 6), todo anterior a esta versión:
  - **la fila de `raw_data` de una polilínea no lleva geometría.** Centro, radio y los dos cortes con el talud salen
    vacíos, para las de la búsqueda y para las del usuario: en una corrida no circular las filas solo se distinguen
    por el factor, y la del usuario por su marca. Es así desde que existe la vista (las cinco columnas son de un
    círculo). Rellenar los cortes cambiaría las filas de hoy, que esta ficha no puede mover;
  - **`minimum_per_centre` ordena solo por factor.** Con la polilínea que m-alfa rechaza (F = 0,223) la primera fila
    es esa, por delante de la crítica (1,178925). `top` usa el orden de la crítica desde D361 (primero las
    admisibles); esta vista no. La fila lleva `admissible: false` y su código, y ahora la marca;
  - **el barrido de desembalse no dice de quién es su superficie crítica.** `drawdown_sweep_summary` publica la de
    cada método como el diccionario que guardó el barrido, que no sabe de quién es. Leído, sin medir;
  - **el otro exportador de Interpretar** (Archivo > Exportar datos (CSV)) recorre solo la búsqueda y escribe su
    cabecera a mano. Es de D401 (0.1.443);
  - **un círculo inadmisible del usuario no deja nota en la corrida**, y una polilínea sí. Es D402 (0.1.444).
- **`search_summary(top=…)` no lo pide ninguna operación** hoy. Se marca igual, con su test, para que no quede un
  camino sin la regla.

### La revisión

`/revisar` y la revisión adversaria (dos agentes; uno el código, otro el test y el changelog). **Ningún defecto en el
código.** El primero midió la restricción de «nada cambia» con un A/B contra 0.1.441 sobre cuatro corridas sin
superficies del usuario (rejilla con dos métodos, superficies compuestas, Path con Optimizar, y Ky): dos volcados de
31 672 líneas, iguales salvo los identificadores aleatorios. Lo que encontraron, y lo que se hizo:

- **La guía del agente decía de más** («una superficie del usuario está en todos los listados»). Una rechazada no
  sale en ninguno de los dos `filter`. Corregida, con lo que lista cada vista; y `docs/mcp/herramientas.md`, que
  además nombraba un `top` del resumen que `analysis_run` no devuelve.
- **Las filas del usuario no se veían en la muestra de `raw_data`.** Sin `save_path` la vista enseña las 20 primeras
  filas, y las del usuario van al final: en una corrida de 60 filas el agente veía la séptima columna con todo «0» y
  ninguna de las filas para las que existe. Sigue de un orden que el plan fija, así que no se cambia el orden: **se
  añade una nota** que dice cuántas son y que son las últimas. No estaba en el plan.
- **Cinco reglas que el test no protegía** (sobrevivían 7 de los 24 mutantes del revisor), todas con su caso ahora:
  - la cláusula de −101 no se ejercitaba (ninguna corrida tenía rechazos sin evaluación): de ahí el límite de talud
    de la rejilla;
  - «válida o no» de la séptima columna: el caso con solo la superficie rechazada;
  - `filter` con `code` y una cota de factor a la vez;
  - las filas de la búsqueda, intactas, también con círculos (en la corrida Path cinco de las seis celdas van
    vacías y no probaban nada);
  - la marca por identidad (una superficie del usuario que repite una de la búsqueda), y `admissible: false` en la
    fila de la rechazada.
- **El comparador del test daba por iguales** un entero y un decimal, y dos textos numéricos con distinto número de
  decimales. Ya no.
- **Un guion del banco** (`medir_d423.py`, el paso 0 de una ficha por hacer) llamaba a `_row` con la firma vieja.
  Acepta las dos.
- **Camino equivocado:** se añadió la marca a la descripción de `results_get` del servidor MCP, y el perfil compacto
  pasó su presupuesto (14 043 caracteres de 14 000,
  `tests/test_mcp_server_v1195.py`). Se retiró: lo dice la guía.

## 1. Qué cambia

- **Núcleo** (`ogr_slip2d/interpretation.py`):
  - `raw_data_rows` recorre `all_evaluations_of`: primero las filas de la búsqueda, sin cambios y en su orden, y
    después las del usuario. Si la corrida analizó alguna del usuario, válida o no, **todas** las filas llevan una
    séptima celda, «1» o «0»;
  - `raw_data_columns(sr)`, nueva: la cabecera de esas filas, seis nombres o siete. La escribían a mano el API y
    Exportar datos brutos de Interpretar, que ahora la piden aquí;
  - `invalid_summary` no cambia, y su docstring dice por qué lee solo `evaluations`.
- **API** (`ogr_api/results.py`, `ogr_api/ops/statistics.py`, `ogr_api/ops/analysis.py`):
  - `summary_in_search(search_result, res)`, nueva: `lem_summary` más la marca cuando la superficie es del usuario
    (por identidad, `is_user_surface_of`). La usan el `critical` y el `top` de `search_summary`, `results_get`
    (`critical`, `top`) y cada fila de `results_query`;
  - el `filter` por factor recorre todas las superficies analizadas; el `filter` con `code`, las de la búsqueda,
    también cuando lleva además una cota de factor;
  - `raw_data` sin `save_path`, con más de 20 filas y alguna del usuario, añade a `notes`: «The surfaces the user
    drew (user_defined = 1) are the last N row(s) of the M: pass save_path to read them all.».
- **Ventana:** Exportar datos brutos de Interpretar lleva las filas del usuario y la séptima columna, por la misma
  función. Ningún texto nuevo.
- **Documentación del agente:** la descripción de `results_query`, la guía y `docs/mcp/herramientas.md`.
- **Lo que cambia para el agente, y se declara:**
  - sin superficies del usuario, nada: ni una clave ni una columna (medido contra 0.1.441);
  - con ellas, `raw_data` tiene una columna más en todas sus filas y más filas, y la nota de arriba; `filter` por
    factor puede devolver más superficies; y aparece `surface.user_defined` en las del usuario;
  - un `minima` (los mínimos globales de una búsqueda) no se marca: las superficies del usuario no entran en él, y su
    identificación es de D424.

## 2. Qué se probó

- **`tests/test_results_query_user_surfaces_v1442.py`** (25 casos, sin Qt; cinco corridas por `analysis_run`
  calculadas una vez, unos 0,7 s cada una, casi todo el arranque del subproceso):
  - **la definición, re-derivada de la propia corrida:** `filter` por factor son las superficies sin código de las
    dos listas dentro de las cotas; los datos brutos, una fila por cada una de las dos listas, las de la búsqueda
    primero e iguales, celda a celda, a las de la misma corrida sin las del usuario (con polilíneas y con círculos);
  - cada listado marca la del usuario y solo esa: la crítica del resumen de `analysis_run`, `results_get`
    (`critical`, `top`), `filter`, `minimum_per_centre`, `slices` y `surfaces_through_point` (por un vértice de la
    polilínea); la marca es `true` o no está, y va por identidad;
  - el CSV guardado con `save_path`, con sus siete columnas; y la nota de la muestra, cuándo sale y cuándo no;
  - **la identidad del censo** para todo código, sobre la rejilla con dos −112, cuatro −111 y once −101, con y sin
    los dos círculos del usuario, y con la polilínea que m-alfa rechaza: el censo y los contadores no se mueven, y la
    superficie rechazada del usuario está en `raw_data` con su código y no en el censo; también con `code` y una
    cota a la vez;
  - **sin superficies del usuario, lo de 0.1.441:** `_V1441`, doce respuestas de cada una de dos corridas (la Path
    de Janbu y la rejilla de Bishop) medidas en el árbol de 0.1.441 con el `_capture()` del propio test
    (`capture_d400.py`, en el banco). El orden de las claves, los textos, los recuentos y los booleanos, exactos; los
    números, a 2e-6, porque se redondearon en una máquina y la suite corre también en otra. En el mismo proceso la
    comparación es exacta: una fila es `lem_summary`, hasta la última clave;
  - los dobles con solo `evaluations` (el `d177` del banco y `tests/test_tensile_export_code_v1192.py`), con seis
    columnas; y la cabecera, escrita en un solo sitio del programa (una comprobación del código fuente: la ventana
    abre un diálogo modal y no se recorre).
- **Discriminación:** en el árbol de 0.1.441, sin el buscador editable, fallan 14 de 25. Trece, por lo que el
  programa lista o marca; uno, porque la cabecera estaba escrita en dos archivos. Pasan los once que comprueban lo
  que no debe cambiar (uno de ellos solo lee el literal medido).
- **Mutantes** (`mutants_d400.py`, en el banco): 38, todos muertos; 11 son de la revisión.
- **Vecinos**, con los patrones `f3b interpret_query user_surfaces user_polylines tensile_export m_alpha_notes mcp
  results_ api_ ops_` del runner (25 archivos, el nuevo entre ellos): 403 casos en verde.
- **Banco, en seco:** `d400()` da SIGUE ABIERTO con el árbol de 0.1.441 (el `filter` vacío, cinco filas, sin marca)
  y CUBIERTO POR TEST con el nuevo; `d361()`, `d396()` y `d418()` de la raíz, y `d177` y `d58` del 02, siguen
  cerrando.
- **La suite entera** con `--jobs 4`, sobre el árbol final: **7494 casos, 7493 en verde, 0 fallos y 1 omitido**, sin
  fugas ni tramos muertos. La serie no toca (20 commits desde la última).

## 3. Qué queda

- **Sin ficha, a decidir por la propietaria:** la fila de `raw_data` de una polilínea sin geometría; el orden de
  `minimum_per_centre` con una superficie inadmisible; y el barrido de desembalse, que no dice de quién es su
  superficie crítica.
- **Sin test:** una corrida con dos métodos (el revisor la midió y la marca sale bien en cada uno), y una superficie
  del usuario no válida (−111 o −101), que solo puede salir en `raw_data`.
- **Fichas que siguen en P10:** D401 (0.1.443), que lleva la misma marca a las ventanas, y D402 (0.1.444).
