# OGR Slip2D v0.1.459

**Una carga que actúa en un punto cuenta en la masa en que está, una vez, y un modelo y su reflejo dan el mismo
factor (D427).** Una carga lineal, la presión sobre una cara vertical (que el rebanador integra en una fuerza) y el
exceso de presión intersticial que crea una carga lineal iban a una dovela por una prueba de abscisa propia, con un
1e-12 absoluto y sin mirar la cota:

- **la fuerza**, por el semiabierto `[x_left − 1e-12, x_right − 1e-12)` en todas las dovelas, también la última. Una
  carga en x_r no estaba en ninguna dovela, una en x_l estaba en la primera y una sobre un corte interior, en la de la
  derecha. Así desde 0.1.75, aunque la docstring decía que la última dovela cerraba su borde derecho;
- **el exceso**, por `|x − x_c| ≤ b/2 + 1e-12`. Sobre un corte interior cargaba las dos dovelas con toda la carga, y en
  x_r la última, en la que su fuerza no estaba.

Ahora las tres preguntan una sola regla, `ogr_core.loads.overburden.edge_share`, detrás del interruptor
`LOAD_SHARE_AT_EDGES`. Las decisiones son de la propietaria, tres de ellas tomadas tras la revisión adversaria:

- **En un corte interior**, a la tolerancia: la mitad a cada dovela, sea cual sea su cota.
- **En un extremo de la masa**, a la tolerancia: entera si está entre la base y el techo de ese extremo; si no,
  nada.
- **Estrictamente dentro de una dovela:** entera.
- **Una presión sobre una cara vertical** pregunta la misma regla. En un extremo actúa solo el tramo de la cara entre
  la base y el techo, con su centroide.
- **La tolerancia** es la del modelo (`_model_grid_tol`, relativa), pero nunca más de ¼ de la dovela más estrecha.
- **El exceso** sigue las mismas partes, por el rebanador y por una norma de diseño, que lo vuelve a pedir.

Medido con 0.1.458 (e51c22e), con `_auditoria/P10_D419_D428/medir_d427.py` del banco, que con 0.1.458 da el log de
0.1.435 línea a línea, y con el muro del 048 sin bulones (la cara x = 12 de y = 1 a 8), con 100 kN/m:

| | 0.1.458 | ahora |
|---|---|---|
| el plano de 60° por el pie con la carga en lo alto de la cara (su x_r) frente a su reflejo, Bishop | 4,9 % | 2,9e-14 |
| el círculo que sale por la cara en (12, 3), la carga en su x_r, frente a su reflejo, Bishop | 21,8 % | 5,5e-15 |
| la carga sobre un corte interior (un vértice en x = 10), frente a su reflejo, Bishop | 8,8e-4 | 5,4e-15 |
| Janbu en el plano, con la carga en x_r, frente a la cuña de Coulomb con W + P | 4,9 % | 3,8e-10 |
| 20 kPa sobre la cara en x = 12, el plano por el pie, Bishop | se pierden: 0,5279 | cuentan: 1,0638 |
| una masa al pie del muro, (12, 1)–(14; 0,3)–(17, 1), con la carga de la coronación (12, 8) | la lleva entera | no lleva nada |
| el exceso de una carga lineal de 500 kN/m sobre un corte, Σ Δσv·b | 1000 kN/m | 500 kN/m |
| los seis planos del 048 (`modelo.ogr`, Janbu, 50 dovelas) | el gunitado no cuenta | cuenta: de −0,73 % (45°) a −4,47 % (70°) |
| la crítica de la búsqueda del 048, con bulones (A/B del interruptor) | Bishop 1,0274, Janbu 1,0992, Spencer 1,1206 | Bishop 0,9577 (−6,8 %, la misma superficie), Janbu 1,1003 (otra), Spencer 1,1259 |
| la misma, sin bulones | Bishop 0,6210, Janbu 0,6829, Spencer 0,6888 | Bishop 0,6028, Janbu 0,6590 (otra), Spencer 0,7002 |
| la búsqueda del 047, con y sin bulones | — | bit a bit |

Es la trigésima segunda versión de la tanda P10 y la segunda del plan del 2026-11-15 (D407, D427 y D428).

## 0. Lo que se encontró

- **El REPRODÚCELO da con 0.1.458 lo de 0.1.435,** línea a línea salvo la cabecera.
  - Con el árbol nuevo no queda ninguna línea `PERDIDA` en x_l ni en x_r del plano.
  - En el círculo, la carga en x_r + ε sale `PERDIDA` en el modelo y en el reflejo: cae en el suelo de delante (y = 1),
    por debajo de la salida (y = 3). Es la regla de la cota.
  - Las secciones «(a)» y «(b)» del guion, y su censo final, ya no miden nada: sustituyen `line_loads_on`, que con el
    interruptor encendido no se llama.
- **El censo ampliado** (`sitecustomize` sobre `_slice_boundaries`, en cada proceso; 38 archivos de tests con cargas,
  731 casos en verde) vio 10 136 rebanados, 273 con cargas:
  - en un extremo: la carga del 047, (0, 6), en x_l (v1112, v1113), que ya contaba; y la del 048, (12, 8), en x_r
    (v1113, 54 rebanados), que se perdía. Ninguna por debajo de la base;
  - sobre un corte interior: un rebanado de `test_excess_pore_pressure_v175`. Su test comprueba que la suma de los pesos
    sube la carga una vez, y lo sigue cumpliendo con la mitad a cada lado; su docstring («belongs to one slice») se
    reescribe;
  - **dentro de la masa y por debajo de la base: presiones sobre una cara en `test_efp_wall_v1122` y
    `test_support_arm_v1178`.** Son una construcción a propósito: representan la fuerza de un soporte con una presión
    equivalente centrada donde corta la superficie, y necesitan que cuente entera. Por eso la regla de la cota no va por
    dentro de la masa.
- **El banco:** de los 246 `.ogr` vivos, solo el 047 y el 048 tienen cargas lineales. Siete tienen cargas
  distribuidas, ninguna sobre un segmento vertical. Los `construir_modelo.py` que crean cargas son los mismos
  problemas; además está `_tools/muro_bancadas.py` (los muros 87–94), con sobrecargas horizontales sobre la
  coronación, a las que la regla no toca.
- **Un tercer lector de las cargas lineales:** el exceso de presión intersticial
  (`ogr_core/hydraulic/excess_pore_pressure.py`), con su propia regla, cerrada por los dos lados. Medido en el talud
  de v175: Σ Δσv·b de una carga de 500 kN/m sobre un corte da 1000, y en x_r da 500 aunque la fuerza se perdiera. Por
  decisión de la propietaria entra en D427: el rebanador le pasa las partes de cada carga.
- **El interruptor:** el motor tiene unos 40 interruptores de módulo («Off, the v0.1.xxx behaviour») con los que el
  banco reconstruye el motor que escribió cada archivo. Por decisión de la propietaria, D427 lleva el suyo, con su test.
  - Vive solo en `ogr_core.loads.overburden`, como `SIGNED_SURFACE_PRESSURE`, y los dos lectores lo leen allí al
    llamar: una copia que nadie apagase no movería nada (regla 7).
  - Apagado, el REPRODÚCELO da 0.1.458 línea a línea. La revisión lo comparó bit a bit, también los pesos, las
    presiones y los momentos de cada dovela, en 27 casos: iguales en los 27.
- **El 048 se calcula ahora con su gunitado.** Por decisión de la propietaria (5 del plan), las dos pruebas de
  `test_support_projection_v1113` que leían la forma del residuo (el residuo plano contra Sheahan y la horquilla contra
  el manual) pasan a medir el muro sin gunitado (`facing=False`), declarándolo: es lo que midieron de 0.1.142 a
  0.1.458 sin saberlo. Su cabecera se re-enuncia con lo medido:
  - contra Sheahan, el residuo pasa de −7,9…−8,2 % a −8,5…−12,3 %: una tendencia de 3,8 puntos, sin explicar;
  - contra la columna del manual, de −3,5…−11,8 % a −4,2…−15,8 %.
- **Una hipótesis abierta, que vio la revisión:** la referencia podría tener la misma asimetría que el OGR viejo,
  contando la carga en x_l y no en x_r. Cuadraría con el 047 (la carga en x_l, que reproduce su publicado) y con el
  048 a la vez. No se puede comprobar sin el programa. La propietaria sigue con (a): una carga en un extremo es de la
  masa, y el reflejo y la cuña de Coulomb lo exigen. Queda escrita aquí y en la nota del 048 del ERRORES.
- **La revisión adversaria (un agente) encontró:**
  - **(media) en un extremo no se miraba el techo de la masa.** Una masa al pie del muro, que arranca en la esquina
    del pie (12, 1), con el techo del extremo a la cota 1, recibía entera la carga de la coronación (12, 8), 7 m más
    arriba (Janbu 3,64, cuando sin cargas no da factor), y la presión de toda la cara. En x_l ya pasaba con 0.1.458,
    y el primer borrador lo había llevado también a x_r. Por decisión de la propietaria, en los dos extremos cuenta
    solo lo que está entre la base y el techo;
  - **(baja) la cota en un corte interior** (el primer borrador la aplicaba en todo borde, como decía R2 del plan, y la
    decisión 7 decía «en un extremo»). Una carga 0,5 m por debajo de la base sobre el corte no contaba, y a 2·tol de
    él contaba entera: el resultado dependía del número de dovelas. Por decisión de la propietaria la cota va solo en
    los dos extremos;
  - **(baja) dovelas más estrechas que la tolerancia del modelo.** En un modelo de 20 km (tol 0,02 m), una cuña de 4 m
    con 500 dovelas llevaba la carga 2 o 2,5 veces. Por decisión de la propietaria la tolerancia de la regla nunca pasa
    de ¼ de la dovela más estrecha, la misma para todas: en un rebanado normal es la del modelo, bit a bit;
  - **ocho mutantes vivos** (la cota sin tolerancia, el centroide desde el otro extremo, las presiones de la cara
    entera en el tramo recortado, toda cara de abajo arriba, el tramo recortado sin su parte, el exceso con norma sin
    saber los extremos, el recorte sin tolerancia, la cota solo en los extremos). Ahora mueren todos, por los casos
    nuevos: la cara recortada contra una cuadratura, las tolerancias y la norma en un extremo;
  - frases: el 4,9 % y el 21,8 % son de Bishop (Janbu da 4,7 % y 19,6 %); dos docstrings de `distributed_loads_on`
    que seguían diciendo el semiabierto; la cabecera del test con un párrafo entre sus viñetas. Arregladas;
  - sin hallazgos: las cargas estrictamente dentro y sin cargas, bit a bit; los demás lectores de cargas (DXF,
    lienzo, `slope_angle`, variables aleatorias) no usan intervalos; las firmas nuevas van al final y son opcionales;
  - una observación sin defecto: una carga normal al contorno en la esquina del pie cuenta entera en el plano por el
    pie (Bishop de 0,528 a 0,846), por la decisión (a).
- **Visto de paso al verificar la berma, sin investigar:** con la presión de la cara sobre esa masa (lo que ya no
  pasa), Janbu daba 0,466 en el modelo y ningún factor en el reflejo. Es una masa casi sin fuerza motriz, y la
  asimetría es anterior a D427.
- **Spencer en el 048** (el A/B del interruptor): cambian 973 superficies, todas las que salen por la cara en x_r = 12.
  Las que más se mueven son círculos pequeños junto a la cara, con factores de 10 a 30, que ganan o pierden la
  convergencia de Spencer al cargar el gunitado (65). No es un defecto: es el caso del gunitado, en superficies que no
  son críticas.
- **En Bishop y Janbu las dos corridas no comparan la misma población:** unas 30 superficies pasan de válidas a
  rechazadas, o al revés, al cargar el gunitado. Los centros de la rejilla son los mismos. La crítica de Bishop es el
  mismo círculo (16; 8; 5,30), que sale por la cara junto a la coronación.
- **Caminos equivocados:**
  - la primera rama de la cara repetía a mano la lógica de los bordes, dos reglas en vez de una. Ahora pregunta
    `edge_share` y `edge_of`;
  - el test pasaba al reflejo un vértice que `_plane` ya reflejaba;
  - el test comparaba el modelo reflejado con el factor del original sin carga, que difiere en el último bit;
  - el test de la primera versión tardaba 11 s: Spencer en todo el barrido y cincuenta cortes. Ahora Spencer va solo
    en x_r del círculo, y el barrido mira tres cortes (el primero, el obligado y el último);
  - el guion del A/B del banco, derivado del de 0.1.458 por un heredoc de la consola, perdió las barras de sus rutas
    (la trampa apuntada). Se arregló con Edit.

## 1. El arreglo

- `ogr_core/loads/overburden.py`:
  - `LOAD_SHARE_AT_EDGES`, el interruptor;
  - `edge_of`, en qué borde está una abscisa;
  - `edge_share`, la parte (0, ½ o 1) de una carga en un punto. Con `y = None` no mira la cota, que es lo que pregunta
    una cara.
- `ogr_slip2d/slicer.py`:
  - `_line_load_shares`, las cargas lineales de una dovela con su parte;
  - `_face_between`, el tramo de una cara entre dos cotas, exacto para la rampa lineal;
  - `distributed_loads_on(..., edges=)`, la cara por la regla;
  - `slice_surface`: `share_tol` (la tolerancia de la regla), las partes de cada dovela para la fuerza, el momento,
    las `load_parts` y el exceso;
  - `line_loads_on`, el camino del interruptor apagado, con su docstring corregida.
- `ogr_core/hydraulic/excess_pore_pressure.py`: `line_shares` en `load_delta_sigma_v`, `delta_sigma_v_at` y
  `excess_at`. Sin ellas, la prueba de antes, que es lo que obtiene quien pregunta en un punto que no es una dovela.
- `ogr_slip2d/design_actions.py`: `refresh_pore_pressures` vuelve a pedir las partes con los bordes, las bases, los
  techos y los anchos que guardó cada dovela.
- `design_actions.load_factors` clasifica cada carga sumando sobre las dovelas, así que dos mitades no le cambian
  nada.

## 2. El test

`tests/test_line_load_ends_v1459.py`, 24 casos, sin Qt, 1,9 s el archivo con la máquina libre y ningún caso por encima
de 0,7 s. Cada número se contrasta con el reflejo, la cuña o la cuadratura. Invariante: una carga actúa sobre la
masa en la que está, una vez, y un modelo y su reflejo dan el mismo factor.

- **El reflejo**, a 1e-9, con la carga en cada extremo y a ±1e-9, ±5e-13, ±tol/2 y ±2·tol de él, en el plano y en el
  círculo, con Bishop y Janbu, y Spencer en x_r del círculo.
- **La cuña de Coulomb** (Coulomb 1776; Duncan y Wright 2005, §6), a 1e-6 con Janbu, los dos Corps of Engineers y
  Lowe-Karafiath:
  - los seis planos del 048 con su gunitado, el efecto que v1113 deja fuera de sus dos pruebas del residuo;
  - la carga en los dos extremos y por dentro;
  - la presión sobre la cara.
- **El corte interior:** la mitad a cada dovela, para una carga lineal y para una cara; el reflejo; la cuña.
- **Por debajo de la salida y por encima del techo:** la carga en (12, 2) del círculo no cuenta, la de (12, 8) sí; la
  masa al pie del muro no lleva ni la carga de la coronación ni la cara.
- **La cara recortada contra una cuadratura** (Simpson compuesto, exacto para una rampa lineal): la fuerza y su cota
  son la integral de la presión sobre el tramo entre la salida y la coronación. Con caras dibujadas hacia arriba y
  hacia abajo, constante, triangular y trapezoidal, más allá de la coronación o no. Y un pie a tol/2 por debajo de la
  base no se recorta.
- **Las tolerancias:**
  - en cota, por la base y por el techo;
  - una carga por debajo de la base sobre un corte cuenta una vez, como a su lado;
  - dovelas de 8 mm en un modelo de tolerancia 2 cm cuentan la carga una vez.
- **Una vez:** en los dos extremos y en tres cortes, a fracciones de la tolerancia, la suma de las partes es 1 en
  [x_l − tol, x_r + tol] y 0 fuera, en metros y en milímetros.
- **El exceso:** Σ Δu·b = B̄·P por la parte, sobre un corte, en x_r y por debajo de la salida, y con la norma DA1-C1
  sobre un corte y en un extremo.
- **El interruptor:** apagado, la carga en x_r se pierde, la del corte va entera a la derecha y el exceso cuenta
  doble; encendido, no.

Discriminación: sobre el `git archive` de 0.1.458, sin el buscador editable y con los `__file__` comprobados, fallan
20 de los 24. Pasan cuatro que la regla vieja también cumplía (su intervalo semiabierto da cada punto a una sola
dovela), que están para matar mutantes de la regla nueva. Los mutantes (`mutants_d427.py` del banco) mueren los 18:
el extremo derecho abierto, 1e-12 absoluto, el corte a la derecha, sin cota, sin techo, la cota en todo borde, la cota
sin tolerancia, la mitad solo para las lineales, la cara entera, el centroide desde el otro extremo, las presiones de
la cara entera, toda cara de abajo arriba, el recorte sin tolerancia, sin el cuarto de dovela, el exceso sin las
partes, `design_actions` sin las partes y sin los extremos, y un interruptor que no apaga.

## 3. Lo que cambia y lo que no

**Cambian a propósito:**
- los números del 048 del banco (arriba y §5);
- las dos pruebas de v1113, solo de modelo (`facing=False`), y su cabecera;
- la docstring de una prueba de v175.

**No cambian:**
- ninguna carga estrictamente dentro de una dovela, ni nada sin cargas: bit a bit (la revisión volcó en hexadecimal
  cada número de cada dovela);
- el 047, bit a bit, en sus dos modelos;
- las cuñas de `test_line_load_boundary_v1199` y `test_janbu_wedge_v1142`;
- los `test_slide_validation_*`;
- la API y el JSON del agente de las cargas;
- ninguna cadena de la interfaz, ajuste del usuario ni acción.

## 4. Verificación

- El test solo: 24 de 24. Su discriminación y sus mutantes, arriba.
- Los vecinos, con cada patrón comprobado con `--list` (D431): `line_load_ends support_projection support_orientation
  line_load janbu_wedge load_actions back_analysis_loads excess_pore ordinary_ponded design_weight_factors
  design_anchors design_pore_pressure failure_direction efp_wall support_arm upward_load overburden_in_core
  seismic_surcharge test_loads slice_last_cut slide_validation tension_crack`: 475 casos, en verde.
- **La suite entera con `--jobs 4`,** tras los arreglos de la revisión, sola en la máquina:
  - 7778 casos: 7777 en verde y 1 saltado, `Failed: 0`;
  - sin `Leaks` ni `Chunks died`, y sin el aviso `SLOW, NOT IN tests/_slow.txt`;
  - la última serie en verde fue hace 37 commits (bea135c), así que no toca serie;
  - los contadores de los dos README pasan de 7753 a 7777: los 24 casos nuevos.
- **No hubo segunda revisión adversaria** de los arreglos de la primera. Los cubren los casos nuevos y los 18
  mutantes, también los ocho que la revisión encontró vivos.

## 5. Banco

- `d427()` en el `verificar_cierres.py` de la raíz, registrada en `COMPROBACIONES`. Mide en vivo, sin los nombres
  nuevos, el muro del 048 sin bulones y su reflejo:
  - el plano con la carga en x_r frente a su reflejo y frente a la cuña;
  - el corte interior;
  - la carga por debajo de la salida y en lo alto de la cara;
  - el exceso sobre un corte;
  - la masa al pie del muro.

  Exige además las once clases del test.
  - Con el árbol nuevo: CUBIERTO POR TEST.
  - Con el de 0.1.458: SIGUE ABIERTO por lo que hace (5,1 %, 8,8e-4, la carga en lo alto de la cara que no cuenta,
    el exceso doble y la berma con los 100 kN/m).
- **El 048 en el banco** (sus `resultados*.json`, `generar_comparativa.py` del 02 y la nota del 048 del ERRORES), al
  cerrar la ficha, tras el commit.
- **El A/B del interruptor en las búsquedas del banco** (`paso0_d427_banco.py` y su log):
  - las búsquedas enteras del 047 y del 048, con y sin bulones, con Janbu, Janbu corregido, Spencer y Bishop: el
    interruptor apagado, encendido y otra vez apagado como control, en serie y en un mismo proceso;
  - las cuatro corridas de control repiten la primera bit a bit;
  - **el 047, bit a bit en sus dos modelos**: su carga está en x_l, que ya contaba;
  - **el 048 cambia** (la tabla de arriba). De las superficies que se evalúan con las dos reglas, cambian 939 con
    Bishop y 908 con Spencer, y 65 más ganan o pierden el factor de Spencer. Las 973 de Spencer salen todas por la cara
    en x_r = 12 (medido aparte); las de Bishop no se miraron una a una;
  - se corrió dos veces, antes y después de las tres decisiones de la revisión (el techo, la cota solo en los
    extremos, el cuarto de dovela). Las críticas son las mismas: la regla del techo no toca ni el 047 ni el 048.
- **El VC de la raíz entero, en seco** (169 comprobaciones): las 168 de antes dicen lo que el JSON archivado, y
  `D427` entra CUBIERTO POR TEST.
- **El VC del 02 entero, con `--seco`:**
  - los 242 veredictos dicen lo que su JSON archivado;
  - frente a la corrida de 0.1.458 cambian dos recuentos y ningún factor: un archivo más en `D174` (el test nuevo) y una
    cita más en `D188` (el cierre de D407);
  - `d16` y `d39`, que miden el 047 en vivo, dicen lo mismo.
- [VC]
