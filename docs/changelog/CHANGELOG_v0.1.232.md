# OGR Slip2D v0.1.232

**D109: la Block Search tiene los cuatro objetos de la referencia, y la
Polyline existe.** Un objeto de bloque dice si es ventana, línea, punto o
polilínea; la polilínea da a cada superficie DOS puntos y el tramo entre
ellos, con las tres opciones de la referencia para cada punto.

Es la primera versión de la tanda P5 (D109, D99, D100, D37 y D92; plan
aprobado el 2026-10-01), que va delante de la tanda D226–D232: ésta corre
tres números. Lo que cambia en el banco de verificación (`_tools/`,
`_auditoria/`, modelos, fichas) está fuera de git.

---

## 0. Lo que el encargo daba por sabido y no lo era

El prompt se escribió con 0.1.159 y se leyó con 0.1.231. Antes de escribir
una línea se midió, y cuatro premisas no se sostenían:

- **«7, 9, 20 y 109 son Line/Window/Point y no se mueven».** El manual
  declara *polyline* en el 9 («a block search polyline object within the
  weak layer»), en el 20 («Block search polyline in the weak seam») y en el
  109 («Block search polylines should be defined at the weak layers»). El 7
  dice «line», pero su superficie publicada tiene DOS vértices de base, que
  una Line (un punto) no puede generar. Y los `construir_modelo.py` del 7 y
  del 9 lo decían por escrito: partían la línea en dos tramos porque OGR
  tomaba un punto por objeto. Hay además SEIS modelos de bloque en el banco
  (7, 8, 9, 20, 75 y 109), no cinco, y los seis declaran objetos abiertos de
  dos vértices. La propietaria decidió redeclararlos «como la referencia»
  (§4).
- **`Evaluaciones/0.1.159` como base.** Los números de bloque se han movido
  desde entonces con el motor (el 7 Spencer de 1,29227 a 1,290767, el 75
  Spencer de 1,559961 a 1,571399). El «iguales a 0.1.159» se sustituye por un
  A/B contra una copia congelada de 0.1.231 (§4).
- **`correr_no_circular.py 7 9 20 75 109`** solo corre el 20 y el 75: el 7,
  el 9 y el 109 son `modelo.ogr` de `correr_todo.py`.
- **La nota de 0.1.156** decía que «every trial surface takes one vertex
  from each» objeto. Con la Polyline deja de ser cierto, así que cambia esa
  frase (§1), aunque el prompt de D100 la daba por intocable.

## 1. El motor

**El tipo se guarda.** `ogr_core/geometry/block_object.py` (nuevo):
`BlockObjectKind` (WINDOW, LINE, POINT, POLYLINE), `PolylinePointMode` (ANY,
SEGMENT, END_POINT) y `BlockObjectSpec`, que `Boundary.block_object` guarda y
el `.ogr` escribe solo para un objeto de bloque y solo si está puesto: un
modelo sin objetos, o con objetos guardados antes, escribe el archivo de
siempre. Hacía falta guardarlo porque una Line y una Polyline de dos
vértices tienen los mismos vértices y son objetos distintos («Do NOT confuse
a single line segment Block Search Polyline object, with a Block Search Line
object»).

**Un objeto sin tipo (un archivo anterior) se lee con la inferencia de
siempre**, que da exactamente lo que daba: un vértice es un Point, un
polígono cerrado de tres o más una Window, dos vértices una Line. La única
excepción es un objeto ABIERTO de más de dos vértices, que daba un punto a lo
largo de todo su recorrido y ahora es la Polyline que es: ese caso es el
propio defecto, y ningún modelo del banco lo tiene.

**Lo que da cada tipo** (`BlockSearch._sample_block_object`, que ahora
devuelve la cadena de vértices que el objeto aporta):

- Point: el punto, sin número aleatorio;
- Line: un punto al azar por longitud de arco;
- Window: un punto dentro, por rechazo sobre su caja; tras 50 intentos, la
  MEDIA de sus vértices (el comentario la llamaba centroide; no lo es, y en
  un polígono no convexo puede caer fuera: se dice en el docstring);
- Polyline (`_polyline_chain`): dos puntos según el modo de cada lado —en
  cualquier parte, en el segmento extremo o en el vértice extremo—, primero
  el izquierdo, y todos los vértices de la polilínea entre ellos. Si el
  derecho cae a la izquierda del izquierdo (ANY a un lado y SEGMENT al otro
  pueden hacerlo), se toman en orden a lo largo de la polilínea: la
  referencia no lo dice y el docstring lo declara como lectura nuestra.

Point, Line y Window hacen **exactamente** las tiradas de antes y en el mismo
orden, así que un modelo que solo declara esos da las mismas superficies bit
a bit (§4).

**El montaje no cambia.** La superficie se sigue armando ordenando por x
todos los vértices de todos los objetos. Eso mantiene entero el tramo de una
Polyline porque dos reglas nuevas lo garantizan
(`ogr_core/project/rules.py`, preguntadas por `check_analysis_settings`, la
API y la interfaz):

- `block_object_refusal`: el tipo concuerda con la geometría; una Polyline
  AVANZA en x (una que vuelve atrás daría una superficie que invierte el
  sentido); «Line Segment» exige dos segmentos («This assumes that the
  polyline consists of at least two line segments»);
- `block_objects_refusal`: ningún otro objeto solapa la extensión lateral de
  una Polyline, que la referencia no permite «because this is likely to
  create kinematically inadmissible slip surfaces». Tocarse en un extremo se
  admite, con la tolerancia relativa al tamaño de las coordenadas.

**De paso.** La caja del exterior con su margen se construía para cada
vértice de cada superficie; ahora una vez por búsqueda (misma expresión,
mismas respuestas), porque una Polyline aporta varios vértices por objeto.

**La nota de 0.1.156** (`_block_group_notes`): «every trial surface takes one
vertex from each of them» pasa a «the trial surfaces are built from them».
Conserva lo que leen sus tests y el banco («1 Block Search object», la
cifra, «Number of Groups») y esquiva las tres subcadenas reservadas.

## 2. La interfaz y la API

- Menú Surfaces: la acción de siempre (`block_object`) se llama ahora «Add
  Block Search Window», y hay tres nuevas: Line (dos clics y termina sola),
  Point (un clic) y Polyline (abierta, Intro o clic derecho). Cada modo del
  lienzo guarda su tipo. La precondición es una para las cuatro y el texto
  ya no nombra una acción: «Block Search objects are only available with
  the Block Search method...».
- Diálogo «Block Search Object», NO modal: el tipo (se enseña, no se edita:
  cambiar una Line en Polyline con un combo sería la reinterpretación
  silenciosa que guardar el tipo evita) y las dos opciones de punto de una
  Polyline. Se abre al dibujar una polilínea —la referencia pide esas
  opciones al añadirla (Tutorial 03)— y desde el menú contextual del objeto.
  Aceptar pasa por un método ligado, sin lambda que capture el diálogo, y
  es deshacible.
- Un Point se ve (una cruz con anillo de tamaño fijo en pantalla) y se
  puede elegir (`_pick_boundary` se saltaba los contornos de un vértice);
  «Edit Coordinates» admite su único vértice; convertir un objeto de bloque
  en otra cosa suelta el tipo.
- API: `boundary_add(block_object=...)`, `boundary_edit(op="block_object")`
  (con `None` vuelve al tipo inferido), `boundary_info` enseña el tipo y si
  está guardado, el catálogo lista tipos y modos. Cualquier edición de un
  objeto de bloque pasa la regla. Servidor MCP, guía y `docs/mcp/` al día.

## 3. El ancla externa: el Tutorial 03 de la referencia

El Tutorial 03 (Non-Circular Surfaces) corre sobre el modelo del Tutorial 02
(Materials & Loading), cuyo texto da cada coordenada, material y carga; le
añade una polilínea de un segmento (39, 23)–(81, 31) en la capa débil,
«Any Line Segment» en los dos puntos, ángulos fijos 135/45, 5000
superficies. Construido en OGR:

| | referencia | OGR 0.1.232 |
|---|---|---|
| superficies de tres segmentos | «all slip surfaces» | 5000 de 5000 (4 vértices) |
| Bishop, mínimo global | 0,762 | 0,747654 (5000) · 0,755177 (300) |
| el mismo objeto como Line | — | 1,997758 (3 vértices) |

OGR queda POR DEBAJO del publicado (−1,9 %): con los ángulos fijos la familia
es de dos dimensiones (los dos puntos sobre el segmento), las dos búsquedas
la muestrean con números aleatorios distintos, y la de OGR dio con una
superficie mejor. El test usa 300 superficies y un 3 %. No se ajustó nada.

## 4. El banco

**Primero, que el motor solo no mueve nada.** Los seis modelos de bloque
(7, 8, 9, 20, 75 y 109), con sus declaraciones de 0.1.231 (objetos de dos
vértices sin tipo), por `run_analysis`, con una copia congelada de 0.1.231
frente a una copia congelada del árbol nuevo: **19 búsquedas, 0 movidas**. En
cada una coinciden mínimo, vértices de la crítica, válidas, inválidas,
intentos y la huella sha256 de TODAS las evaluaciones (factor y vértices).
Solo cambia la frase de la nota de 0.1.156 en los seis, que es la del §1.
Archivado en `_auditoria/P5_0232/ab_bloque_seis_0.1.231_vs_0.1.232.json`.

**Después, la redeclaración que decidió la propietaria** («como la
referencia»): una Block Search Polyline por modelo en el 7 y el 9 (sus
`construir_modelo.py`, que partían la línea en dos tramos «porque BlockSearch
toma un punto por objeto»), en el 20 (la costura entera, con su quiebro en
x = 120) y en el 75 (`derivar_no_circular.py`, que gana el tipo y un filtro
por número de problema: sin él, `--forzar` regeneraba TODOS los derivados
con ids nuevos y la guarda de D78 habría dado por caducos todos sus
resultados). El 8 importa la geometría del 7 y se regeneró con él; se corre
solo sobre la superficie publicada, así que su objeto no toca sus números (y
no se movieron). Al regenerarse, el 7, el 8 y el 9 ganan dos campos de la
norma de diseño de 0.1.226 con su valor por defecto: deriva de esquema,
inerte sin norma.

| | antes | ahora (Polyline) | publicado |
|---|---|---|---|
| 7 · Bishop / Spencer / GLE / Janbu c. | 1,2343 / 1,2908 / 1,2815 / 1,3098 | 1,2352 / 1,2930 / 1,2816 / 1,3101 | 1,258 / 1,258 / 1,246 / 1,275 |
| 9 · Spencer / GLE / Janbu c. | 0,7071 / 0,6811 / 0,6955 | 0,7101 / 0,6818 / 0,6956 | 0,760 / 0,720 / 0,734 |
| 20 · Spencer (búsqueda / optimizado) | — | 1,0499 / 1,0256 | 1,010 |
| **75 · Bishop** | **1,4125 (+27,8 %)** | **1,1302 (+2,3 %)**, optimizado 1,0959 | 1,105 |
| **75 · Spencer** | **1,5714 (+34,6 %)** | **1,2001 (+2,8 %)**, optimizado 1,1697 | 1,167 |
| **75 · GLE** | **1,6009 (+40,2 %)** | **1,1765 (+3,0 %)**, optimizado 1,1306 | 1,142 |

El 75 recorre ahora el llano: su crítica de Bishop va de x = 45,2 a 129,8
sobre y = 0,52, donde la publicada lo hace de 47,06 a 127,46. En el 7 y el 9
los mínimos suben entre un 0,01 % y un 0,42 % (el 9 Spencer): la Polyline
muestrea una familia más amplia que los dos tramos con las mismas 5000
superficies, y bajan también las válidas (7 Bishop, 4878 → 3866). El 9 sigue
un 5–7 % por debajo de lo publicado, como antes.

Comparativa contra `Evaluaciones/0.1.231`: 559 filas, **548 iguales, 8
mejoran y 3 empeoran, cero cambios de estado**; los 14 pares medidos con
versiones distintas son exactamente las filas re-corridas.

**D109 cerrada**: `d109()` mide en vivo el modelo del Tutorial 03 (Polyline,
cuatro vértices; sin tipo, tres; con un vértice colineal y sin tipo, cuatro o
cinco), el 75 a menos del 5 % de lo publicado y recorriendo el llano, las
cuatro declaraciones, el A/B y la discriminación. Contra 0.1.231 da NO SE
SOSTIENE también por comportamiento (la polilínea sin tipo de tres vértices
da superficies de tres).

**D37, en suspenso.** El ×8 del 74, que la ficha daba por no terminado,
terminó el 2026-09-08 y no converge. Hoy, con el control ×1 bueno en los dos
ejes, el patrón se repite: centros 1,2115 → 1,2041 → 1,2000, radios 1,2115 →
1,2115 → 1,2031, frente a un `f_pub` de 1,1969. Pero el reparto ya no deja
una sola fila: con 0.1.231 hay 40 filas C5 y, tras D109, 39. Seis entran sin
razón escrita:

- el **3**, que es resolución (la escalera converge en 1,373792 < 1,374668);
- el **75** con las claves de la superficie de D108 (la familia de bloque
  tiene 4 vértices y la publicada 12; la optimizada la alcanza);
- el **91** en dos archivos, que pasa de C0 a C5 por el rescate de rama de
  D125 y está sin medir (su escalera son horas).

El cierre lo decide la propietaria; la ficha lleva la nota con las medidas.

## 5. Tests

`tests/test_block_polyline_v1232.py`, 29 casos: el Tutorial 03 (tres
segmentos en todas, el mínimo publicado, el tramo dentro de la capa débil, y
la misma línea con un vértice colineal leída como Polyline sin tipo); lo que
da cada tipo como identidad sobre la población (el tramo completo, End Point
en el vértice extremo, Line Segment en el segmento extremo, Line con un
vértice); el tipo guardado y el inferido (un objeto de dos vértices sin tipo
da las MISMAS superficies que una Line, bit a bit); regla 7 (Line frente a
Polyline, 1,998 frente a 0,755, y cada opción de punto); las reglas de la
referencia; la API; la interfaz.

Contra un `git archive` de 0.1.231 con el test copiado dentro fallan **28 de
29**: 2 por comportamiento (la polilínea sin tipo de tres vértices da
1,9978, no el 0,762 del tutorial; un punto no se puede elegir), 4 por lo que
falta en el menú, el catálogo y la API, y 22 por el símbolo nuevo. Pasa el de
conservación: un objeto sin tipo escribe el archivo de siempre.

Cambian a propósito tres tests, y lo que protegen no cambia:

- `test_block_search_action_not_modal_v1167.py`: su `_PRECONDITION` era
  «Add Block Search Object is only available...», el rótulo de esta acción;
  ahora la precondición es de los cuatro objetos. Sigue protegiendo que no
  haya modal y que un mismo texto sirva a los dos caminos.
- `test_add_surface_three_points_v1168.py`: su censo de modos activados por
  AST solo veía un `ToolMode` literal en `_set_tool(...)`. Las cuatro
  acciones de bloque entran en su modo por la guarda común
  (`mode=ToolMode.X` y `_set_tool(mode or ToolMode.DRAW_BLOCK_SEARCH)`), y
  el censo lee ahora las dos formas. Sin eso decía que nadie activa la
  línea, el punto y la polilínea, y `trigger()` los activa. Los modos que
  nadie activa siguen siendo exactamente los de `_NEVER_ENTERED`.
- `test_f3b_ops_v1201.py`: las acciones mapeadas a la API pasan de 113 a
  116 (las tres nuevas, a `boundary_add`). El inventario de
  `ogr_api/inventory.py` las clasifica, como exige
  `test_action_inventory_v1195.py`.

## 6. Lo que se reporta y NO se corrige

Nacen cinco fichas al preparar la tanda, sin prompt largo:

- **D236** (banco, P0): la comparativa mezcla familias. La fila circular GLE
  del 75 enseña como «superficie publ.» el valor de la POLIGONAL de la
  fig. 7.29 (1,1456, −21,86 %, DISCREPANCIA falsa), y el 7 y el 9, que son
  búsquedas de bloque, salen rotulados «circular».
- **D237** (P5): los rangos de los ángulos de proyección no se validan. La
  referencia exige el de inicio menor que el de fin y unos rangos (95–175 /
  5–85, o 95–265 / −85–85); la interfaz admite 0–360 y el 109 guarda 45 → −45.
- **D238** (P5): `_project_to_top` marcha a pasos ABSOLUTOS de 0,5 y devuelve
  la x del paso, no el corte con el terreno.
- **D239** (banco, P0): el 20 tiene dos productores de su
  `modelo_bloque.ogr`, con ajustes distintos (los dos declaran ya la misma
  Polyline).
- **D240** (P1): el diccionario español lleva 20 claves duplicadas, y dos con
  traducciones distintas: `'None'` y `'Add Grid'` («Añadir malla» frente a
  «Añadir rejilla»). Gana la buena en las dos, pero la muerta engaña.

Y una nota en una ficha abierta, sin número porque es de su misma clase:
**D93** está resuelta de hecho desde 0.1.201 (`run_configured_statistics`
factoriza cada muestra), y su prompt pide un `grep` que no casaría con la
implementación de hoy. Sigue abierta: no es de esta tanda.

## 7. Caminos equivocados

- **El primer A/B se cayó en el sexto modelo y se llevó los cinco
  anteriores.** El guion pedía `surface.polyline`, y el 109 tiene capas
  débiles: sus superficies son `WeakLayerSurface`, sin ese atributo. Y solo
  escribía el JSON al final. Ahora saca los vértices de cualquier superficie
  y escribe tras cada modelo; los dos lados se corrieron en paralelo.
- **La primera escalera del 74 murió por el límite de 30 minutos** de una
  tarea en segundo plano, a mitad del ×4. No llegó a escribir su informe, así
  que el ×8 archivado no se perdió; se relanzó con dos horas de margen.
- **Un parche de `verificar_cierres.py` escribió el archivo ANTES de
  comprobar su sintaxis** y lo dejó mal sangrado unos segundos. Se arregló en
  el acto y el siguiente comprueba antes de escribir. Detrás de eso había una
  mejora real: con todos los casos en vivo dentro de un solo `try`, el
  `ImportError` del árbol viejo tapaba el caso que lo discrimina por
  comportamiento; ahora cada caso va en su propio `try`.
- **El 8 hereda la geometría del 7** y no estaba en la lista de modelos a
  redeclarar. Se vio porque el A/B daba al 8 los mismos números que al 7.
- **El primer `--seco` completo bajaba dos cierres viejos, D102 y D103**, y
  los dos por cómo estaba escrito el código, no por lo que hace:
  - D103 lee por AST la guarda de `act_add_block_search_object` (su `return`,
    sus cadenas y la clave que comparte con el tooltip), y la primera versión
    la había llevado a un ayudante `_start_block_object` que llamaban las
    cuatro acciones. El comportamiento era el mismo (los tests de 0.1.167
    pasaban), pero la medida ya no la encontraba. Se deshizo el ayudante: la
    guarda vuelve a esa función, con el modo y el texto **solo por nombre**
    (`*, mode=None, prompt=None`), para que `QAction.triggered`, que pasa
    `checked` a un slot con argumento posicional, no tenga dónde ponerlo.
    Comprobado con `trigger()` en las cuatro acciones. D103 no se toca.
  - D102 comprueba que la clave de la acción, `"block_object"`, no salga de
    `ogr_gui`, y desde esta versión es también, por casualidad de nombre, la
    clave del `.ogr` donde el objeto guarda su tipo. Su censo excluye ahora
    esa cadena en los dos archivos del modelo que la escriben y la leen, con
    la razón escrita. Lo que D102 protege (ninguna acción llamada «Add
    Surface», la de bloque nombra Block Search, con español e icono) no
    cambia.

## 8. Verificación

- **Suite entera, sin argumentos: 5208/5208** (0.1.231: 5179; más los 29 del
  test nuevo). Hicieron falta tres corridas. La primera dio 5206/5208, con
  dos inventarios que no conocían las acciones nuevas:
  `test_action_inventory_v1195` (clasificarlas en `ogr_api/inventory.py`) y
  el censo de modos de `test_add_surface_three_points_v1168`. La segunda dio
  5207/5208: al mapearlas, la cuenta de `test_f3b_ops_v1201` pasó de 113 a
  116. Los tres cambios a propósito están en el §5.
- **Discriminación**: el test nuevo, copiado dentro de un `git archive` de
  c02c8b5 (0.1.231) y corrido con el runner de ese árbol, falla 28 de 29
  (§5). Archivado en `_auditoria/P5_0232/`.
- **A/B del banco**: 19 búsquedas de los seis modelos de bloque con sus
  declaraciones de 0.1.231, 0 movidas (§4).
- **El Tutorial 03 de la referencia**, construido en OGR: 0,747654 con 5000
  superficies frente a 0,762 publicado, y todas de tres segmentos (§3).
- **Banco**: re-corridos el 7, el 8, el 9, el 20 (no circular) y el 75 (no
  circular). Comparativa contra `Evaluaciones/0.1.231`: 11 filas movidas,
  cero cambios de estado. `verificar_cierres.py --seco` completo: 202
  cierres y **0 bajadas**, tras deshacer el ayudante que movía la guarda de
  D103 y enseñar al censo de D102 la clave del `.ogr` (§7). D109 retirada al
  índice (CUBIERTO POR TEST), D236–D240 abiertas, `PAQUETES` podado y cadena
  de P5 tachada, `PROMPTS_RESOLUCION.md` regenerado (47 prompts, 18 FALTA,
  todos de fichas sin prompt largo), auditorías con **0 ERROR** en el 02 y
  en la raíz, e instantánea `Evaluaciones/0.1.232` congelada y comprobada
  byte a byte.
- **Interruptores**: ninguno nuevo; `INTERRUPTORES` sigue en 31.

**Qué falta por probar.**

- La interfaz se ha probado sin pantalla (dibujo por coordenadas, diálogo,
  menú, `trigger()` de las cuatro acciones), no a mano con el ratón.
- Los tres modos por lado no tienen un caso del banco que los use: los
  manuales usan siempre «Any Line Segment».
- El 03-001 (Sarma) también es una polilínea en su manual y el banco lo
  declara con dos líneas. No se tocó: la decisión de redeclarar era sobre el
  banco del 02, y afecta a D131.
