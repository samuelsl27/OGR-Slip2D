# OGR Slip2D v0.1.233

**D99 y D100: la Block Search tiene los *Multiple Groups* de la referencia,
y una búsqueda sin objetos dibujados dice que su región la ha elegido el
programa.** Cada objeto de bloque lleva su Group ID. Con la casilla
*Multiple Groups* activada, la búsqueda se hace por separado para cada
grupo, con el número de superficies repartido a partes iguales. El contador
que el panel llamaba «Number of Groups» pasa a llamarse por lo que es: las
bandas de la región que OGR usa cuando no hay ningún objeto.

Segunda versión de la tanda P5 (plan aprobado el 2026-10-01). Entre 0.1.232
y esta versión se cerró en el banco D37, replanteada, y se redeclaró el
Sarma 03-001 con su polilínea (§6). El banco de verificación está fuera de
git.

---

## 0. Lo que el encargo daba por sabido y no lo era

- **«El banco no se movería».** P-D99 lo daba por hecho: sus cinco modelos
  de bloque quedarían en un grupo, «que es el comportamiento de hoy». Es
  cierto para cinco de los seis (el A/B lo confirma: §4), pero no para el
  109. El manual pide «block search polylines at the weak layers», y sus
  tres juntas se SOLAPAN en x. Como la referencia no permite solapar una
  polilínea dentro de un grupo, tres polilíneas en esas juntas solo son
  posibles en grupos distintos. El 109 era `reproducible: false`
  precisamente por eso, y es el único modelo del banco que esta versión
  mueve.
- **«La nota de 0.1.156 es intocable».** P-D100 lo pedía para no romper las
  tres subcadenas que el banco reserva («stable» con «head», «edge of the
  search grid», «path_optimize»). La nota se mantiene, pero no puede seguir
  diciendo «Number of Groups»: ese es el nombre de la referencia para
  *Multiple Groups*, que esta versión implementa, y el contador no lo es. Se
  ha re-redactado con el mismo disparo y sin ninguna de las tres subcadenas,
  y un test lo vigila (§5).

## 1. El motor

- **`BlockObjectSpec.group_id`** (`ogr_core/geometry/block_object.py`) es el
  Group ID de la referencia. Se escribe en el `.ogr` solo si es distinto de
  0, así que un archivo que nunca usó grupos se guarda byte a byte como
  antes. Lo leen dos funciones nuevas:
  - `block_group_of(objeto)`: 0 si el objeto no guarda ninguno;
  - `block_groups(objetos, multiple)`: el reparto que usa la búsqueda. Con
    la casilla apagada es UN grupo con todos los objetos en el orden del
    modelo, sin leer los ids.
- **`SearchSettings.block_multiple_groups` vuelve, ahora con el significado
  de la referencia.** Desde 0.1.156 estaba retirado en `_SHADOW_FIELDS`
  porque se escribía en cada `.ogr` y no lo leía nadie. Sale del registro y
  lo lee `build_search`. Un archivo viejo que lo guardaba, a `true` o a
  `false`, lo carga tal cual; sin ids asignados es un grupo, como era.
- **`BlockSearch(multiple_groups=…)`.** Cada candidata pertenece a un
  grupo:
  - los grupos van en orden de id;
  - cada uno recibe `N // n` candidatas y el primero, además, el resto, de
    modo que `attempts == N` se sigue cumpliendo como identidad;
  - la candidata usa solo los objetos de su grupo, y el generador aleatorio
    es uno para toda la corrida;
  - la crítica es la mínima de todos los grupos;
  - cada superficie dice de qué grupo viene (`SlipSurface.block_group`) y
    el resultado resume el reparto (`SearchResult.block_groups`: id,
    objetos, presupuesto, válidas y mínimo).

  Con un solo grupo, las tiradas son las de antes una a una: lo prueba un
  test y lo confirma el A/B del banco (§4).
- **La regla de solape es por grupo** (`rules.block_objects_refusal`). Dos
  polilíneas de grupos distintos pueden solaparse en x, que es justo para lo
  que la referencia usa los grupos. En el mismo grupo se rechaza, y el
  mensaje dice el grupo. Con la casilla apagada, el rechazo dice cómo
  salir: activar *Multiple Groups* y dar ids distintos.
- **`_block_group_notes`**, con sus dos mitades:
  - **Con objetos dibujados**, la nota de 0.1.156 con el rótulo nuevo: «the
    Implicit Region Bands setting — N here — configures nothing».
  - **Sin objetos (D100):** «No Block Search object is drawn, so the
    sampling region is chosen by the program and not by the model…». La
    nota da el número de bandas y recuerda que la referencia exige al menos
    un objeto.
  - **Dos silencios de la propia casilla (regla 7):** activada sin objetos,
    o con todos los objetos en el mismo grupo. Los dos se dicen.

## 2. La interfaz y la API

- **Panel de Block Search:**
  - casilla «Multiple Groups», con un tooltip que explica para qué sirve;
  - el contador pasa a llamarse «Implicit Region Bands», y su tooltip dice
    que solo actúa sin objetos dibujados y que la referencia no tiene ese
    ajuste;
  - el botón de valores por defecto repone también la casilla.
- **Diálogo «Block Search Object…»:**
  - nuevo campo «Group ID», activo solo con *Multiple Groups*;
  - con la casilla apagada, el campo conserva el id que tenga el objeto;
  - se abre al dibujar CUALQUIER objeto mientras la casilla esté puesta, no
    solo una polilínea.
- **API y MCP:**
  - `block_object` acepta `group_id`, un entero no negativo; un valor
    inválido se rechaza diciendo cuál;
  - `boundary_info` lo enseña;
  - el catálogo dice cuándo se lee;
  - el ajuste `search.block_multiple_groups` funciona por `settings_set` y
    por `model_define`;
  - la guía MCP y `herramientas.md` explican el uso de varias capas
    débiles.
- Todas las cadenas nuevas pasan por `tr()` y tienen su entrada en español.
  Se quitan las dos claves que ya no usa nadie (el rótulo viejo y su
  tooltip).

## 3. Tests

- **`tests/test_block_groups_v1233.py`** (19 casos). No hay número
  publicado para un modelo sintético de dos capas, así que las anclas son
  las identidades que fija la descripción de la referencia:
  - el presupuesto: 30 y 30 de 60, y 41 y 40 de 81;
  - la pertenencia: toda superficie de un grupo tiene vértices de SU capa y
    de ninguna otra. Es el criterio de cierre de D99, literal;
  - un grupo reproduce, tirada a tirada, la búsqueda sin grupos.

  Además: la regla 7 (la casilla mueve el número donde puede), la regla de
  solape por grupo, el `.ogr` de ida y vuelta, el archivo viejo, la API y la
  interfaz.
- **`tests/test_block_fallback_note_v1233.py`** (12 casos): las
  notas sin objetos, con objetos y de los dos silencios de la casilla; las
  tres subcadenas reservadas; y el rótulo y el tooltip del panel, leídos en
  inglés y con el idioma restaurado al salir (regla 5).
- **Discriminación:** copiados al `git archive` de 0.1.232 (5cde1fa) y
  corridos con el runner de ese árbol: **29 de 31 fallan**. Siete fallan por comportamiento: sin objetos no hay nota, el rótulo es «Number of Groups:» y la API rechaza `search.block_multiple_groups` como «not a setting any more». Los 22 restantes fallan por símbolo (`group_id`). Pasan los dos que tienen que pasar en los dos árboles: otra búsqueda no recibe nota y, sin objetos, no se dice que el contador «no hace nada».
- **Cambian a propósito, y lo dice su cabecera:**
  - `test_block_groups_v1156.py`: la clase que exigía el campo RETIRADO pasa
    a exigirlo VIVO y fuera del registro. Lo que el archivo protegía sigue
    afirmándose: el booleano no gobierna el contador. Además, la nota se
    busca por el rótulo nuevo;
  - `test_block_polyline_v1232.py`: la misma búsqueda por rótulo.

## 4. El banco

- **A/B de los seis modelos de bloque** (7, 8, 9, 20, 75 y 109), con sus
  declaraciones de 0.1.232 y sin grupos. Motor congelado de 0.1.232 frente
  al nuevo, por `run_analysis` con los ajustes de cada modelo: **19
  búsquedas, 0 movidas**. La comparación incluye la huella de todas las
  evaluaciones, no solo el mínimo. Solo cambian los avisos, y es el rótulo
  del contador (`_auditoria/P5_0233/ab_bloque_seis_0.1.232_vs_0.1.233.json`).
- **El 109, como dice el manual:** tres Block Search Polylines en las tres
  juntas, Group ID 1, 2 y 3, *Multiple Groups* activado. Pasa a
  `reproducible: true`.

  | método | 0.1.232 (Lines, un grupo) | 0.1.233 (polilíneas en grupos) | manual |
  |---|---|---|---|
  | Bishop | 6,576 | **4,692** | 1,799 |
  | Janbu | 6,089 | **4,320** | 1,610 |
  | Spencer | 6,731 | **4,768** | 1,803 |
  | GLE | 6,744 | **4,801** | 1,804 |

  Se acerca, pero sigue 2,6 veces por encima. Antes de atribuirlo se midió,
  en el mismo proceso y sin tocar el motor, el efecto de las dos fichas
  abiertas que podían explicarlo: el corte exacto de la proyección (D238) y
  los rangos de ángulo sin su mitad descendente (D237). Las cuatro variantes
  dan entre 4,68 y 5,17 (`_auditoria/P5_0233/exp_109.json`), así que la
  distancia no está en ellas. Queda abierta como **D243**.

## 5. Lo que se reporta y NO se corrige

- **D243**: el 109, ya expresable, da 4,69 frente a 1,799. Causa sin
  identificar; D237 y D238 descartadas por medida.
- D237 (rangos de ángulo sin validar) y D238 (proyección a pasos de 0,5 m)
  siguen abiertas: su efecto en el 109 está medido arriba.

## 6. En el banco, entre 0.1.232 y 0.1.233 (fuera de git)

- **D37 cerrada, replanteada.** La propietaria pidió analizar si el problema
  venía de otro sitio o había que cambiar el planteamiento, y fueron las dos
  cosas:
  - **El planteamiento.** «Mínimo de búsqueda > F del círculo publicado» no
    es un criterio de corrección para una búsqueda discreta o aleatoria,
    porque su familia finita casi nunca contiene la superficie publicada.
    Cada una de las 26 filas C5 lleva ahora su razón, comprobada contra
    evidencia medida con el motor de hoy (`_tools/razones_d37.py`, que exige
    igualdad de conjuntos).
  - **Los mínimos de frontera.** En el 74, el 79 y el 81 el círculo crítico
    es tangente al fondo firme. Ahí la retícula de radios pierde la
    tangencia por una fase, el error es O(h) y no O(h²), y el criterio del
    1 ‰ de la escalera no vale: en el 74 los radios ×1 y ×2 dan el MISMO
    radio. La prueba buena es el círculo tangente en los nodos de la propia
    rejilla.
  - **Del clasificador del banco, 13 filas.** No aplicaba el foco del
    modelo y juzgaba las no circulares sin su optimización.
  - **Del motor, D241.** La Path Search toma como cara del talud un tramo
    colineal. En el 52, Spencer seco pasa de 2,2515 a 1,7901 con el mismo
    terreno, frente al 1,796 del manual. Abierta, con tres arreglos
    posibles para que decida la propietaria.
  - **Una ficha retirada el mismo día.** Con dos semillas, el 70 parecía un
    defecto propio; la tercera bajó del círculo publicado (1,594470). Es
    dispersión por semilla, D138.
- **Sarma 03-001**: una Block Search Polyline en la capa débil, como su
  manual. Entre −0,02 y −0,12 % según el método, y sigue en REVISAR.
  Regenerar el modelo cambiaba también la tolerancia, de 0,005 a 1e-4,
  porque el constructor genérico la pone hoy por defecto; el constructor la
  fija ahora explícitamente.

## 7. Caminos equivocados

- **El primer guion de las traducciones dejó el diccionario sin
  compilar.** Escribía el archivo antes de comprobar la sintaxis, y la
  herramienta Bash convirtió en una sola la barra doble de «object\\'s».
  Se reformuló la frase sin apóstrofo, en la interfaz y en la clave.
- **`surface.py` salió entero en CRLF** al editarlo, y se devolvió a LF.

## 8. Verificación

- **Suite entera: 5238/5238** (5208 de 0.1.232, más 31 nuevos, menos uno que
  pierde la clase reescrita de `test_block_groups_v1156`), sin filtro, con
  `QT_QPA_PLATFORM=offscreen`.
- **Discriminación:** 29 de 31 en 0.1.232 (§3).
- **Banco:**
  - A/B de los seis modelos de bloque, 19/0 (§4);
  - `d99()` y `d100()` CUBIERTO POR TEST, midiendo en vivo y no por grep;
  - `--seco` de todos los cierres comparado clave a clave con el veredicto
    anterior: de 203 a 205 (D99 y D100), **0 bajadas** y 0 cambios;
  - D99 y D100 retiradas a `Evaluaciones/0.1.233`;
  - `auditoria_invariantes.py` con 0 ERROR en el 02 y en la raíz;
  - `d07c_b()` re-anclado, porque comprobaba que ningún `.ogr` llevara el
    campo y desde esta versión todos lo escriben. Mide ahora en vivo lo que
    D07c(b) protegía: la casilla llega al motor como lo que es, y el
    contador no depende de ella.

**Qué falta por probar:**
- la casilla y el diálogo en la aplicación con pantalla real (los tests los
  manejan sin `exec()`);
- el 109 contra el manual, que queda en D243.
