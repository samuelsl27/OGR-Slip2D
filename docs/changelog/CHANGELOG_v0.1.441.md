# OGR Slip2D v0.1.441

**El retroanálisis deja de analizar las dos clases de superficie que la referencia no analiza (D418):** las que ya
alcanzan el factor objetivo, y las que la fuerza no toca. Analizaba toda superficie válida de la corrida. Medido con
0.1.435 y con 0.1.440 sobre una rejilla de 64 círculos del talud de ejemplo (coronación a la cota 25, pie a la 15;
objetivo 1,5; `medir_d418.py` del banco), en kN/m:

| caso | OGR publicaba | ahora |
|---|---|---|
| fuerza a la cota 20, en la cara | Janbu 145,99 · Bishop 136,95 | lo mismo, al último bit |
| fuerza a la cota 28, por encima de la coronación | Janbu 145,99 · Bishop 228,25 | ninguna fuerza, y dice por qué |
| fuerza a la cota 35 | Janbu 145,99 · Bishop 547,80 | ninguna fuerza, y dice por qué |
| objetivo 1,0, que todas superan | 0,00 sobre la primera de la lista (FS 5,25), como «gobernante» | ninguna fuerza, y dice por qué |

Decisiones de la propietaria (2026-11-12):

- **Las dos reglas.** No se analiza la superficie cuyo factor ya alcanza el objetivo (no necesita fuerza), ni aquella
  cuya masa no toca la fuerza (la fuerza no hace nada por ella).
- **El contacto es el punto de la cara:** la fuerza actúa donde el talud está a su cota, y toca una masa si esa cota
  cae entre la más baja y la más alta del **techo** de la masa, con los extremos dentro.
- **Sin superficie que analizar no hay fuerza**, y una nota dice el motivo. Si la fuerza no toca ninguna, dice entre
  qué cotas llegan las masas al terreno. La cota por defecto se queda en 0.
- **Interpretar sigue las mismas dos reglas** al tasar la crítica, con una sola regla del núcleo.
- **El ángulo de la fuerza no entra:** será D433, al final de P10 y sin versión.

Es la decimocuarta versión de la tanda P10.

## 0. Lo que se encontró

- **La referencia**, comprobada en su ayuda local y parafraseada: solo se retroanalizan las superficies por debajo
  del factor objetivo; una superficie cuya masa no está en contacto con la fuerza no se analiza, y avisa de que una
  superficie más local, por debajo del objetivo, puede gobernar sin que la fuerza la cambie.
- **Paso 0, sobre 0.1.440 (dd6904c):**
  - `medir_d418.py` da la tabla de la ficha;
  - **los dos criterios de contacto, medidos lado a lado** (`medir_d418_criterios.py`, en el banco): «la recta de la
    fuerza corta la masa» (hasta su base) y «el punto de la cara está en el techo de la masa». No se distinguen en
    ningún caso medido: el talud de ejemplo con Janbu y Bishop a seis cotas, Ej_1 a cinco, y los dos modelos del 037
    del banco. Un círculo deja el terreno donde lo deja su base. Solo se separarían en una masa que baja por debajo
    del punto más bajo de su techo, con la fuerza entre los dos;
  - **el 037 del banco no se mueve.** A/B en el mismo proceso, con la regla, sin ella y otra vez con ella:
    334,772066 kN/m (FS 1,0249) y 0,057670 kN/m (FS 1,4997) en los dos modelos, la misma superficie. Con la regla
    se analizan 3055 y 2 superficies de 3097;
  - **con grieta de tracción** la masa acaba en la grieta y su techo es el terreno hasta ahí: medido, 15,74 a 25 con
    la masa desde x = 22,76 en vez de 20,09;
  - **el rebanador no corta en los vértices del terreno** (corta en los cruces de capa y en los quiebros de la
    superficie), así que una cresta puede quedar dentro de una dovela. El techo se lee de los bordes de las dovelas
    **y** de los vértices del terreno entre los dos extremos de la masa.
- **Una fuerza justo a la cota del pie deja fuera las masas que salen un poco por encima.** En Ej_1 (pie a la cota
  25), con la fuerza a la cota 25 y objetivo 1,3, la superficie que gobernaba (877,97 kN/m, FS 0,9497) deja el terreno
  8 cm por encima del pie: la fuerza no la toca, y la gobernante pasa a ser otra (843,37 kN/m). Quedan fuera 53
  superficies por debajo del objetivo, la crítica entre ellas, y la nota lo dice. Es la regla decidida, aplicada tal
  cual; se enseña porque la fuerza publicada baja.
- **La nota de «ya alcanzan el objetivo» no se da en cada corrida** (se aparta del plan; la propietaria lo
  confirmó en el resumen de la versión, el 2026-11-13). El plan la ponía
  siempre que hubiera alguna. Casi toda corrida tiene alguna, dejarlas fuera no cambia la fuerza (no necesitaban
  ninguna), y un test anterior fija que un retroanálisis sin nada que avisar no deja ninguna nota (D340). Queda así:
  - se cuentan (`surfaces_above_target` en el resumen del agente) y solo se dicen cuando son el motivo de que no haya
    fuerza;
  - las que están por debajo del objetivo y la fuerza no toca se dicen **siempre**: siguen por debajo.
- **Los tests que corrían el retroanálisis fuera de lo que ahora se analiza.** El paso 2 del prompt lo preguntaba.
  Con la regla puesta y antes de arreglar ninguno fallaban once tests de ocho archivos, todos anunciados en el plan:
  la cota por defecto, 0, o una cota 5 dada a mano, caen por debajo de esos modelos, y dos pedían un objetivo que
  ninguna superficie dejaba por encima. Cada uno conserva su invariante con la fuerza en la cara (§2).
- **Dos textos que dejaban de ser ciertos:** la ayuda del campo Cota decía «Solo afecta a Bishop», y el docstring del
  módulo, lo mismo. La fuerza que necesita una superficie solo depende de la cota con Bishop, pero la cota decide
  **qué** superficies se analizan con cualquier método.
- **Con la cota por encima del centro del círculo, Bishop da una fuerza negativa que se recorta a 0** (el brazo cambia
  de signo): un falso «no hace falta soporte». La regla de contacto quita casi todos los casos; queda el círculo con
  el centro por debajo de su coronación. Anterior, sin ficha, no se toca.
### La revisión adversaria (dos agentes, 14 hallazgos, ninguno refutado)

- **La cara vertical de la propia masa no contaba como techo** (del cambio; el más serio). En un corte vertical, un
  círculo que sale del terreno a través del muro acaba en la abscisa del muro con la base a media altura. El tramo
  del muro desde ahí hasta la coronación es la cara libre de esa masa, pero los dos vértices del escalón comparten
  la abscisa del extremo y no están «entre los extremos». Medido por el revisor: techo de 10 a 10, y una fuerza
  sobre la cara del corte no tocaba ninguna masa; con la cara inclinada un milímetro, todas. Ahora el extremo de la
  **base** cuenta cuando está sobre el terreno. El fondo de una grieta de tracción no lo está, y no cuenta.
- **Con varios motivos a la vez se decía el que no era.** Con Bishop, todos los círculos ya en el objetivo y una
  polilínea del usuario, el motivo que se daba era la polilínea, y nada decía que no hacía falta fuerza. Ahora va
  primero «alcanzan ya el objetivo», y la nota de las que Bishop no puede tasar se da al lado.
- **El rango de cotas de la nota es una envolvente, y lo dice.** Con dos masas de techos 15–18 y 22–25 y la fuerza a
  la cota 20, el texto decía que la fuerza no tocaba ninguna y que «sus masas llegan al terreno entre las cotas 15 y
  25». Ahora: «cada una de esas masas llega al terreno en una parte del tramo de cotas 15,00 a 25,00».
- **El progreso no se informaba para las superficies que se dejan fuera.** Era la última línea del bucle. Con las dos
  reglas casi toda la población se deja fuera: la barra se quedaba parada y Cancelar, que entra por esa llamada, no
  podía. Ahora es la primera.
- **Docstrings y documentación a medias:** el del módulo y el de `run_back_analysis` seguían diciendo «toda
  superficie», y también el de la operación del API y la fila de `docs/mcp/herramientas.md`. Corregidos.
- **Textos:** «Check them separately» por «apart»; la cota de la fuerza con siete cifras significativas y las del
  terreno con dos decimales (1234,567 salía «1234,57»).
- **Del test nuevo:** un docstring que prometía una precedencia que no se comprobaba (ahora sí), un aserto
  tautológico en `tests/test_f3b_ops_v1201.py`, ventanas sin `deleteLater()` y un coste mal contado.
- **Se quedan, y se dicen:**
  - Interpretar tasa primero y aplica las reglas después; la corrida, al revés. Solo cambia qué frase sale para una
    crítica que ya está en el objetivo **y además** tiene la envolvente sin asentar o el brazo nulo. Se queda así
    porque la comprobación de D419 (0.1.440) mide lo que la ventana pasa a las sumas en el propio factor;
  - `_rederived` de `tests/test_back_analysis_user_surfaces_v1428.py` no aplica las dos reglas: sus identidades
    valen porque en sus modelos, a la cota 20, el máximo está tocado y por debajo del objetivo;
  - tres corridas de `tests/test_back_analysis_v140.py` siguen con la fuerza a la cota 25, justo el pie de Ej_1: no
    corren en vacío, pero solo ven las masas que salen por el llano del pie.

- **En el banco:** `d343()`, `d348()` y `d340()` corrían el retroanálisis con la cota por defecto, como los tests, y
  se adaptan igual. `d340()` da SIGUE ABIERTO por otra cosa («el trabajador del barrido no guarda los avisos») y ya
  lo daba con 0.1.440: es deriva del verificador, anterior a esta versión. Se reporta y no se toca.

## 1. Qué cambia

- **Núcleo** (`ogr_slip2d/back_analysis.py`):
  - `mass_top_range(slices, ground)` y `force_touches(top_range, elevation)`: el techo de la masa (con la cara
    vertical por la que sale, si la tiene) y el contacto;
  - `run_back_analysis`, en este orden: no válida → compuesta → no es círculo (Bishop) → alcanza el objetivo (con
    «≥») → la fuerza no la toca → `required_force`. Las dos nuevas no cuentan en `surfaces_analysed`;
  - `BackAnalysisResult` gana `surfaces_above_target` y `surfaces_untouched`;
  - `required_force_of_result` aplica las dos reglas a la superficie que tasa y devuelve el motivo;
  - `required_force` y su recorte a 0 no cambian: es la función de una superficie;
  - el interruptor `REFERENCE_SCREENS` reconstruye el retroanálisis de 0.1.440 para un A/B.
- **Notas nuevas** (`ogr_slip2d/run_messages.py`, con «factor objetivo», que vale con y sin norma):
  - «Se dejaron fuera N superficie(s) que están por debajo del factor objetivo: la fuerza a la cota Y no toca su masa
    deslizante, así que no puede subir su factor. Compruébalas aparte, o mueve la fuerza.»;
  - «La fuerza a la cota Y no toca la masa deslizante de ninguna de las N superficie(s) que están por debajo del
    factor objetivo, así que no se da fuerza de soporte: sus masas llegan al terreno entre las cotas A y B.»;
  - «Todas las superficies que se podían retroanalizar alcanzan ya el factor objetivo: no hace falta fuerza de
    soporte.»;
  - y las dos de una superficie, para Interpretar.
- **Ventana:** el cuadro del retroanálisis dice el motivo una vez (es el mismo objeto que su recuento); la nota de
  las que la fuerza no toca va a Notas del análisis; la ayuda del campo Cota dice lo que hace.
- **Interpretar:** con la crítica ya en el objetivo dice que no necesita fuerza (escribía «activa: 0,00, pasiva:
  0,00»), y con la fuerza fuera de su masa lo dice con las cotas (publicaba un número).
- **Lo que cambia para el agente, y se declara:**
  - `surfaces` cuenta solo las analizadas (11 de 52 en el caso medido);
  - claves nuevas `surfaces_above_target` y `surfaces_untouched` en el resumen de `back_analysis_run`;
  - sin superficie que analizar, `required_force` es nulo y `notes.error` da el motivo, en vez de 0 kN/m;
  - con `elevation` sin dar se usa la del proyecto, 0 por defecto, que casi nunca toca nada: la guía y la
    descripción de la herramienta lo dicen.

## 2. Qué se probó

- **`tests/test_back_analysis_rules_v1441.py`** (21 casos):
  - **el contacto contra su forma cerrada:** el círculo de centro (34, 30) que pasa por (31, 19) deja la cara del
    talud de ejemplo a la cota 19 por construcción y entra en la coronación en x = 34 − √105. Su techo va de 19 a 25:
    se analiza a las cotas 19, 19,05 y 25, y no a 18,95 ni a 25,05;
  - un vértice del terreno dentro de una dovela cuenta, también en la corrida (un terraplén con la cresta en un
    vértice); en un escalón, la masa tiene la altura de su lado; **el corte vertical contra su forma cerrada** (el
    círculo de centro (12, 14) y R² = 125 sale por el muro x = 10 a la cota 3: techo de 3 a 10); y el fondo de una
    grieta no cuenta;
  - con varios motivos, cuál se dice; el rango de la nota, como envolvente; y el progreso de las que se dejan fuera;
  - las dos identidades sobre lo que se analiza (Bishop 1955; Janbu 1954): fuerza 0 en el propio factor, sin
    recortar, a 1e-9 del peso; y activa igual a pasiva con objetivo 1,0, sobre Ej_1 (crítica por debajo de 1);
  - por encima de la coronación y con todas por encima del objetivo no hay fuerza y se dice, y sin las reglas sale
    lo que publicaba 0.1.440;
  - donde la fuerza toca y el factor está por debajo, la gobernante y su fuerza son las de sin reglas al último bit,
    y las medidas en 0.1.440 a 1e-9; sin ninguna nota;
  - los recuentos medidos antes de escribir la regla: 41 y 42 de 52 por encima de 1,5; a la cota 16, 8 sin contacto;
  - Interpretar, el agente (por `ogr_api.call`) y el cuadro de la ventana.
- **Discriminación:** en el árbol de 0.1.440, sin el buscador editable, fallan 20 de 21. Los de la corrida, por la
  fuerza que se publica; los de las funciones nuevas, porque no existen. Pasa la identidad en el propio factor.
- **Mutantes** (`mutants_d418.py`, en el banco): 28, todos muertos. Uno sobrevivió en la primera pasada (la corrida
  sin los vértices del terreno) y trajo el caso del terraplén.
- **Tests que cambian a propósito,** cada uno con su porqué en un comentario:
  - `tests/test_back_analysis_v140.py`: la derivación independiente del máximo aplica las dos reglas a mano, desde la
    geometría de Ej_1, con la fuerza a la cota 30; dos corridas que no miraban la fuerza pasan a la cota 30;
  - `tests/test_back_analysis_loads_v1220.py`: «la corrida entrega su proyecto» se pide un 10 % por encima del factor
    de la superficie y con la fuerza en la cara, comparando al último bit con `required_force`;
  - `tests/test_f3b_ops_v1201.py`: la identidad a objetivo 1,0 por el agente, con un suelo que deja superficies por
    debajo de 1; y «sin norma igual, con norma más» con objetivo 1,5 y la fuerza en la cara;
  - `tests/test_task_notes_v1363.py`, `tests/test_background_tasks_v1365.py` y
    `tests/test_names_and_headings_v1369.py`: la cota tecleada en la cara; `tests/test_slice_store_v1408.py` y
    `tests/test_cancel_v1366.py`: la cota en la cara, por argumento;
  - `tests/test_interpret_charts_v1435.py`: la cota de Interpretar, en la cara;
  - `tests/test_seepage_run_notes_v1352.py`: las muestras de los cinco códigos nuevos.
- **Banco:** `d418()` da SIGUE ABIERTO con el árbol de 0.1.440 (publica 145,99, 547,80 y 0 kN/m) y CUBIERTO POR TEST
  con el nuevo; `d419()`, `d396()`, `d343()`, `d345()` y `d348()` siguen cerrando.
- **Algo que se le escapó a 0.1.440 y salió aquí:** `d210()` del verificador del banco 02 lee por AST que
  `_back_analysis_report` llame a `required_force` con el proyecto, la misma regla que el test que 0.1.440 cambió a
  propósito. Con la función nueva daba «NO SE SOSTIENE» sin que se moviera ningún número (el 037 sigue en
  334,772066 kN/m). Acepta ya los dos nombres. Al cerrar 0.1.440 no se pasó el verificador del 02, que es el que
  lo habría visto.
- **La suite entera** con `--jobs 4`, dos veces: antes de la revisión, 7465 casos, 7464 en verde y 1 omitido; con el
  árbol final, **7469 casos, 7468 en verde, 0 fallos y 1 omitido**, sin fugas ni tramos muertos. La serie no toca (19
  commits desde la última).

## 3. Qué queda

- **D433, nueva** (al final de P10, sin versión): el ángulo de la fuerza del retroanálisis. Es una entrada nueva, con
  formulación propia: el momento de una fuerza inclinada pide su punto de aplicación, y su componente vertical entra
  en el equilibrio de la dovela que la recibe.
- **Sin ficha:** el falso 0 de Bishop con la cota por encima del centro, y la deriva de `d340()` en el verificador
  del banco.
- **A mano, por la propietaria:** el retroanálisis con la cota por defecto (la nota con las cotas) y con una cota de
  la cara; e Interpretar con un objetivo por debajo del factor de la crítica.
- **Fichas que siguen en P10:** D400 (0.1.442), D401 (0.1.443) y D402 (0.1.444).
