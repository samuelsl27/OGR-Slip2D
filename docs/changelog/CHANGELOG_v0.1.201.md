# OGR Slip2D v0.1.201

**F3b: estadística, retroanálisis, optimización e interpretación, para el
agente y por una sola puerta. No queda ninguna acción del programa fuera de
su alcance.**

- El agente alcanza **113 de las 136 acciones** de la ventana. Las otras 23
  son solo de interfaz (zoom, impresión, ayuda…) y cada una dice por qué.
  Quedan **0 pendientes** (5 en v0.1.200), y el techo baja a 0. El plan
  dejaba esto para F4; F3 lo adelanta.
- Estadística, retroanálisis y optimización pasan por la misma puerta que
  un *Compute*:
  - la copia con coeficientes de diseño;
  - las comprobaciones y avisos de ajustes;
  - los ajustes y la semilla del proyecto.

  La interfaz llama a lo mismo. Sin norma de diseño no cambia ningún número;
  con norma, sí, y se cuenta en §1.
- Lo que la ventana de interpretación preguntaba a un resultado vive ahora
  en `ogr_slip2d/interpretation.py`, y la ventana y el agente preguntan
  ahí.

Ningún número guardado se mueve. Los resultados de estadística,
retroanálisis y optimización no se guardan en el proyecto, y los scripts
del banco que llaman al motor probabilístico directamente no pasan
`prepare` ni leen el índice de muestra: dan lo mismo que antes.

---

## 1. Una sola puerta (decisión del propietario, 2026-09-24)

`analysis_runner` gana tres puertas, junto a la del barrido de desembalse
de v0.1.200:

- `run_configured_statistics`
- `run_configured_back_analysis`
- `run_configured_optimization`

Cada una:

- rechaza lo que rechaza `run_analysis`;
- trabaja sobre la copia factorizada;
- usa los ajustes y la semilla del proyecto;
- devuelve el informe de coeficientes y los avisos.

### Estadística: las muestras no se factorizaban

La interfaz corría el determinista por `run_analysis`, que factoriza, y
cada **muestra** sobre el proyecto crudo. Con una norma activa, el
histograma ponía factores de sobrediseño junto a factores de seguridad sin
factorizar.

Además, un rechazo del determinista (`AnalysisNotConfigured`) se tragaba y
salía como «no hay superficie crítica».

Ahora cada clon muestreado se factoriza **después** de aplicarle su muestra
(`prepare`, un parámetro nuevo de los tres motores). Así una cohesión
muestreada se factoriza como la determinista, en vez de sustituir un valor
ya factorizado por uno sin factorizar.

Medido en un talud de 10 m (c′ = 6 kPa, φ′ = 22°), Bishop, 200 muestras
LHS de la cohesión, en el mismo proceso:

| Norma | Determinista | Camino viejo: media · PF · β | Puerta única: media · PF · β |
|---|---|---|---|
| desactivada | 1,3105 | 1,3107 · 0 % · 9,693 | **idéntico** |
| EC7 DA1-C2 | 1,0488 | 1,3107 · 0 % · 9,693 | 1,0487 · **2,5 %** · **1,907** |

Con la norma, la estadística vieja decía «probabilidad de rotura nula»
sobre un modelo cuyo determinista estaba a 1,05.

### Retroanálisis

- Buscaba sobre el proyecto crudo. Mismo talud, objetivo 1,3, fuerza a
  y = 5:
  - sin norma, **0 kN/m** en los dos caminos;
  - con EC7 DA1-C2, **0 → 100,1 kN/m**.
- El camino de un solo círculo, el de la ventana de interpretación:
  - pasa ya el sismo del modelo (kh, kv), que `required_force` admitía y
    nunca recibía;
  - toma el objetivo y la cota de los ajustes, en vez de 1,3 y 0,0
    escritos a mano.

### Optimización

La acción *Optimize Surfaces…* tenía tres defectos:

- **No leía ningún ajuste de optimización.** Usaba 400 iteraciones
  tecleadas frente a las 4000 del ajuste, y los valores por defecto para el
  resto.
- **No tenía semilla**: dos ejecuciones del mismo modelo daban cosas
  distintas.
- **Sobrescribía el resultado a medias.** Cambiaba en su sitio la
  superficie, el factor y las dovelas del crítico guardado, pero dejaba las
  fuerzas, los detalles y la admisibilidad de la superficie vieja. Todas
  las ventanas de interpretación abiertas comparten ese objeto.

Ahora:

- usa `settings.optimize_settings()` (separado de `optimize_kwargs`, que
  ya lo usaba la búsqueda) y `analysis_seed()`;
- el diálogo parte del valor del ajuste;
- el resultado es **nuevo**: una copia del resultado de búsqueda con la
  superficie optimizada como `optimized` y una evaluación más, que es como
  lo guarda la pasada de optimización de la propia búsqueda.

## 2. Las muestras guardan su índice

Una muestra fallida no produce factor. El diagrama de dispersión
(`scatter_data`) y la exportación de estadística hacían un `zip` de las
muestras con los factores, así que **a partir del primer fallo cada par
emparejaba el factor con la muestra siguiente**. La exportación, además,
perdía las últimas filas.

- `MethodProbabilisticResult` y `OverallSlopeResult` guardan
  `sample_index`.
- `sample_pairs` empareja por él.
- Un resultado sin índice (anterior a esta versión) no se empareja: da una
  lista vacía, no una lista desplazada.

El test lo demuestra con una muestra de cada tres fallando a propósito:
los pares correctos son monótonos (el factor crece con la cohesión) y el
`zip` viejo no lo es.

## 3. La interpretación, fuera de la ventana

`ogr_slip2d/interpretation.py` contiene:

- `error_code`: la única correspondencia de −120 / −112 / −111 / −101;
- `invalid_reason` e `invalid_summary`, el censo por código y por motivo;
- `raw_data_rows`;
- `surfaces_through_point`;
- `minimum_per_centre`;
- `sf_along_slope` y `slope_intercepts`;
- `slice_rows`, `per_slice`, `slice_stress` y `base_parameter`;
- `surface_area` y `surface_path`.

La ventana, el lienzo y el panel de dovelas los llaman.

**Defectos que se corrigen al moverlos** (ninguno cambia un número del
cálculo):

- **«Show Values Along Surface» se inventaba σ′n.** Calculaba W·cos α / b
  − u, que no es la respuesta de ningún método. Ni siquiera la del
  ordinario, que divide por la longitud de la base, l = b / cos α: con él
  se equivocaba en 1/cos α. Ahora usa la N del método (N/l − u) y su
  resistencia.
- **«Surfaces Crossing Point» medía contra el círculo entero.**
  - Un punto en la parte de arriba del círculo, que no se rebana, contaba
    como cruce.
  - Una superficie de capa débil no casaba nunca.
  - Decía «se resaltarán» y no resaltaba nada.

  Ahora mide sobre la superficie que se calculó (la base de las dovelas),
  y el texto dice lo que hace: cuenta y da la de menor factor.
- **La columna Área de la tabla de resultados era siempre 0.** Dividía
  cada peso por un peso específico que la dovela no tiene, y la excepción
  lo convertía en 0,0. Además, la ordenación se activaba antes de rellenar
  las filas.
- **«Export Slice Data» exportaba superficies**, igual que «Export Data».
  Ahora exporta las dovelas de la superficie seleccionada (o la crítica)
  con los números del método.
- **Había dos `_scatter`.** El primero nunca estaba conectado a ningún
  menú; se borra.
- **«Graph SF Along Slope» perdía un corte con el terreno en x = 0.** Un
  `x_left` de 0,0 se leía como ausente y caía en centro − radio.
- **Un proyecto nuevo, uno abierto o la demo conservaban la estadística y
  el retroanálisis del anterior**, y *Show Statistics* y los menús de
  estadística de la interpretación seguían mostrándolos.
- **El diálogo de variables aleatorias** decía «10 % a cada lado» y ponía
  una desviación del 10 % con un rango del 30 %. La regla pasa al núcleo
  (`default_dispersion`), con el comentario corregido, y la limpieza de
  correlaciones también (`forget_variable`).

## 4. Las operaciones nuevas

| Operación | Qué hace |
|---|---|
| `random_variable_list` | Las entradas que pueden ser aleatorias, con su clave y su valor, y las definidas. |
| `random_variable_set` | Define o cambia una variable. **La media es siempre el valor del modelo**, y lo avisa si lo actualiza. Rechaza (`variable_problems`): desviaciones o rangos negativos, una normal sin desviación, un rango nulo, correlacionarse consigo misma, con una variable no definida, o dar `correlation` sin `correlated_with`. |
| `random_variable_delete` | Borra una variable o todas. Las correlaciones que apuntaban a ella se limpian. |
| `statistics_run` | Trabajo en segundo plano, por la puerta. |
| `back_analysis_run` | Trabajo en segundo plano, por la puerta. |
| `optimize_run` | Trabajo en segundo plano, por la puerta. Parte de la superficie crítica no circular de un resultado de análisis y guarda un resultado **nuevo** (tipo `optimized`, legible con `results_get`). |
| `results_query` | Vistas de un análisis: `error_codes`, `invalid_summary`, `raw_data`, `surfaces_through_point`, `minimum_per_centre`, `sf_along_slope`, `slices` y `filter`. Vistas de una estadística: `histogram`, `convergence`, `samples` (cada factor con **su** muestra) y `sensitivity`. Un parámetro que la vista no lee se rechaza. |

Otros cambios:

- el trabajador gana tres tipos (`statistics`, `back_analysis`,
  `optimize`);
- **MCP:** 74 herramientas en `full` (67 antes); `compact` sigue con 14;
- `docs/mcp/` y la guía del agente, al día.

## 5. Reportado, sin corregir

Cada punto necesita una decisión o una ficha; ninguno se ha tocado.

**Estadística**
- **Las muestras no filtran la admisibilidad.**
  - La reevaluación de cada muestra usa una `GridSearch` con los valores
    por defecto (`check_m_alpha=True`, `reject_tensile=False`), no los
    ajustes del proyecto.
  - Cuenta en la PF superficies que el determinista descartaría como −112
    o −120.
  - Corregirlo cambia números incluso sin norma de diseño, así que queda
    fuera de lo decidido.
- **La media de una variable definida en la interfaz no se actualiza**
  cuando cambia el modelo: las muestras siguen centradas en el valor viejo.
  El agente sí la actualiza.
- `correlate_pair` usa una semilla fija, `Random(12345)`, y no la del
  proyecto.
- El diálogo deja correlacionar con cualquier variable, aunque el
  comentario del modelo dice «del mismo material».
- Las variables de soporte probablemente nunca se ofrecen: `available_variables`
  busca `PARAMETERS` en la instancia, no en su tipo. Ya estaba anotado en
  D66.

**Retroanálisis**
- Usa sus propias sumas simplificadas (N = W cos α) y deja fuera fuerzas
  de agua, soportes, grieta y cargas.
- En Janbu, el término resistente se multiplica por cos α donde el solver
  divide por n_α = cos α · m_α: es una discrepancia de cos²α por
  comprobar. Solo Bishop tiene un test de «fuerza nula en el factor sin
  soporte».
- Incluye superficies inadmisibles.
- El parámetro `num_slices` no se usa.
- `back_analysis.enabled` se escribe y nadie lo lee (regla 7).

**Optimización**
- `rep.improved` compara factores de seguridad, pero el paseo minimiza la
  puntuación de la búsqueda, que en modo sísmico es Ky.
- La reevaluación final no comprueba la admisibilidad.

**Interpretación**
- El mínimo por centro y el factor a lo largo del talud incluyen
  superficies inadmisibles, que la crítica excluye.
- «Export Data» las escribe con su factor y sin marca.
- La sensibilidad de la ventana dibuja solo el primer método, y la
  exportación de estadística solo exporta el método que se informa.

**Abrir un archivo no limpia los resultados del proyecto anterior**
- *Nuevo* y la demo vacían el panel de resultados y limpian:
  - `last_search_result(s)`;
  - los avisos del cálculo;
  - el informe de coeficientes;
  - las notas de estadística.
- *Abrir* (`act_open`) no limpia nada de eso. Tras abrir un archivo, el
  panel enseña el resultado del proyecto anterior, e *Interpret* u
  *Optimize Surfaces* trabajarían con sus superficies sobre el modelo
  recién abierto.
- La estadística y el retroanálisis sí se limpian ya en los tres casos
  (§3), porque viven en `_attach_project`.
- Encontrado al revisar esta versión; se reporta antes de corregirlo
  (regla 6).

**Test no hecho: los recuentos publicados de −112**
- El plan pedía contrastarlos: 97 en Ej_1 con Bishop.
- Reproducirlos exige la población entera de la referencia: 4851
  superficies, con los códigos de antes de rebanar (−103, −106, −107,
  −108, −1000) que OGR no genera.
- Un −112 aislado frente a 97 no mide nada. Queda para una ficha.

## 6. Tests

`tests/test_f3b_ops_v1201.py`, con 22 casos:

- **Variables:**
  - la dispersión inicial;
  - la media que sigue al modelo;
  - cada rechazo deja el modelo intacto;
  - borrar limpia las correlaciones.
- **Estadística por la API:**
  - la PF es la fracción contada y β = (media − 1)/σ;
  - el histograma suma n;
  - con varianza nula, las muestras reproducen el determinista
    **factorizado** (EC7 DA1-C2): es lo que discrimina la puerta;
  - sin norma, es idéntica al camino viejo;
  - una muestra de cada tres falla y los pares siguen monótonos, cosa que
    el `zip` viejo no cumple;
  - los rechazos.
- **Retroanálisis:**
  - a objetivo 1,0 la fuerza activa y la pasiva coinciden (identidad, por
    el trabajo del agente);
  - sin norma es el camino viejo;
  - con EC7 mueve el número.
- **Optimización:**
  - es reproducible con la semilla;
  - da un resultado nuevo y el original queda intacto;
  - rechaza un círculo;
  - en la interfaz, un resultado nuevo sin tocar el crítico viejo.
- **Interpretación:**
  - la fila 1 de la tabla de dovelas de Ej_2 (método ordinario) por
    `slice_rows`;
  - el área de un segmento circular, R²(θ − sin θ)/2, con error O(1/n²);
  - un punto en la parte sin rebanar del círculo no está sobre la
    superficie;
  - un corte en x = 0;
  - el censo cuadra con el filtro por código;
  - los parámetros que una vista no lee se rechazan.
- **Inventario:** no queda ninguna acción pendiente.
- **Interfaz:** un proyecto nuevo borra la estadística vieja.

**Tests existentes que se ajustaron:**

- `test_api_undo_v1194.py`: ejemplos de deshacer para las dos operaciones
  de variables.
- `test_mcp_server_v1195.py`: `wait_seconds` lo consumen también las tres
  herramientas de trabajo nuevas.
- `test_m_alpha_notes_v1158.py`: el test que vigila dónde se asigna el −112
  mira ahora en `ogr_slip2d/interpretation.py`, adonde se movió.

**Verificación:** la suite entera, sin filtros, pasa 4507 de 4507. Una
primera pasada dio 4506: `test_design_factor_report_gui_v1165` cuenta los
sitios que limpian las notas y exige que limpien también el informe de
coeficientes, y la limpieza nueva de `_attach_project` añadía uno. Ahí se
limpian ahora solo los resultados de estadística y retroanálisis.
