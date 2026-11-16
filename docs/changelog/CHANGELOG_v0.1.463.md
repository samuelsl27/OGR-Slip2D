# OGR Slip2D v0.1.463

**Las cuñas de Sarma (D357, segunda de las siete versiones del método).** `ogr_slip2d/sarma/wedges.py` corta la masa
que ya resolvió el rebanador en cuñas con caras inclinadas. Calcula el peso, el agua y las cargas de cada una y se
las da al solver de 0.1.461. `ogr_slip2d/sarma/angles.py` da el ángulo de una cara que nadie da. El método sigue sin
registrarse: ningún análisis lo corre hasta 0.1.464, y ningún número del programa cambia.

Con la geometría publicada, el constructor da:

| caso | publicado | OGR, sentido fijo | OGR, cinemático | la herramienta del banco |
|---|---|---|---|---|
| 4 seco | 1,198 | 1,19833910 | 1,19833910 | 1,19833913 |
| 4 saturado | 0,434 | 0,43466206 | 0,43466206 | 0,43466201 |
| 5 (γw = 1) | 1,091 | 1,08827052 | 1,08905263 | 1,08827053 / 1,08905263 |

Lo que separa OGR de la herramienta (≤ 6·10⁻⁸) es la regla de Simpson de la herramienta; OGR integra exacto.

Por decisión de la propietaria (2026-11-15, paso 0 del plan):
- una cuña ES una `Slice`;
- la resistencia que lee la columna la lee en una columna sustituta, la dovela vertical que el rebanador corta sobre
  la base de cada cuña.

No hay ninguna cadena nueva en la interfaz, ni ajuste ni acción. Hay siete códigos de motivo nuevos del motor, con
su español y su muestra.

## 0. Lo que se encontró

### Al construir las cuñas

- **El constructor de regiones ajusta sus vértices a una rejilla.** En el talud del test, el contorno exterior en
  y = 10 sale como y = 9,99999979, y x = 80 como 79,99999998801562. La primera versión del peso intersecaba cada
  cuña con los polígonos de las regiones. Una cuña dibujada sobre el terreno de verdad sobresalía de su región una
  lámina que no pesaba nada: −1,7·10⁻⁷ en la cuña del pie, y la identidad con Janbu se quedaba en 2·10⁻⁸.
  - El rebanador no lo nota: corta sus bandas en los contornos de verdad y pregunta a las regiones solo qué material
    es cada banda.
  - Las cuñas hacen ahora lo mismo: se parten por los contactos tal como están dibujados (`polygonize` de la red que
    forman con el contorno de la cuña) y cada trozo pregunta su material en un punto interior. La identidad baja a
    10⁻¹³.
- **Las fronteras incluyen los cruces con el nivel freático.** Es una desviación pequeña del plan aprobado, que decía
  «vértices, contactos y divisiones uniformes». Con ella, las fronteras con los contactos activados son exactamente
  los cortes obligados del rebanador para el mismo número, por las mismas funciones. Así unas caras verticales sobre
  ellas SON sus dovelas, campo a campo, y Sarma sin resistencia en las caras es el Janbu de esas dovelas. U se integra
  exacta de todos modos, así que el corte en el freático no hace falta para la precisión.
  - No mueve el 4 ni el 5: allí el freático solo toca la superficie en sus extremos.
- **El número de cuñas no mueve F sobre un tramo recto de un solo material.** Con la política por defecto, el talud
  del test da 2,5430856155 con 5, 8 y 14 cuñas. No es un defecto, es el equilibrio de sólidos rígidos.
  - Dos cuñas sobre una misma base recta de un material suman las ecuaciones de la cuña que parten: las fuerzas de la
    cara entre ellas se cancelan, y la suma con sus incógnitas (N′ y F) se cierra sola.
  - Una cara ahí deja F donde estaba, con cualquier ángulo, resistencia o agua. Ahora es un test.
  - En un círculo sí lo mueve, porque las bases son cuerdas: allí más cuñas son otra superficie. Es lo que tendrá que
    decir 0.1.464 del ajuste de número de cuñas (regla 7).
- **Las caras de una política se cruzan cerca de un quiebro cóncavo.** Pasa cuando las divisiones son finas.
  - Con 25 cuñas en el talud del test, la bisectriz en (40, 4) se inclina hacia el pie (100°). Las normales del
    tramo de debajo se inclinan hacia la cabeza (88°). Con el terreno 16 m por encima, sus topes se cruzan.
  - En una rejilla de 174 círculos del talud φ = 0 de v1109, con la bisectriz se rechazan 46 con 10 cuñas y 42 con
    25. Con la normal media, 53 y 53. Con caras verticales, ninguno. Casi todos son de caras que se cruzan; el resto,
    de una cara que sale del modelo antes de llegar al terreno.
  - Son los círculos de centro bajo, cuyas caras radiales convergen dentro de la masa.
  - El plan original decía «con política automática se reordenan y se anota», y el anexo de 0.1.462, «rechazos con
    código». Esta versión rechaza con código (`lem.sarma_faces_cross`). Qué hace una búsqueda con ellos lo decide la
    propietaria antes de 0.1.464, junto con la política por defecto.

### Al escribir los tests

- **Un defecto propio:** la resistencia de una cara no se partía nunca en los contactos. A `_segment_hits` le llegaba
  la lista de todas las polilíneas, no una, y no encontraba ningún cruce. Toda cara tomaba el material de su punto
  medio. Lo cazó el test de la media ponderada, escrito para eso; en el 4 y el 5 no se veía, porque sus caras no
  cruzan ningún contacto.
- **Otro:** un contacto cerrado (un recinto dentro de la masa) no recortaba su trozo de la cuña. La línea se construía
  sin cerrar el anillo, y `split` no corta un anillo entero dentro de un polígono. Ahora es `polygonize`, que lo ve.
- **El peso saturado necesita `use_sat_unit_weight`.** Los dos primeros modelos del test daban el peso seco por
  debajo del freático, y la forma cerrada a mano, el saturado. No es un defecto del programa: es la opción del
  material, y el rebanador hace lo mismo (`gamma_at`). Los modelos del test la activan.

### La revisión adversaria (un agente)

Corrió 23 sondas propias. Comprobó que la refactorización del rebanador es bit a bit: A/B en el mismo proceso de
`_slice_boundaries` de HEAD contra el árbol, en 925 pares (superficie, número), con contactos y freáticos al azar,
círculos y polilíneas. Comprobó también el reflejo con caras inclinadas, agua, agua libre, cargas, grieta, sismo y un
escalón (≤ 1,8·10⁻¹³). Lo que encontró, y lo que se hizo:

- **Alto: el peso salía mal cuando un contacto cruza una cara inclinada.** Los extremos de `line.intersection(poly)`
  caen a ~10⁻¹⁶ del contorno de la cuña. La unión no los anuda, el corte queda como un cabo suelto y `polygonize`
  devuelve la cuña entera, pesada con un solo material.
  - En el propio modelo con contacto del test, dos cuñas pesaban −1,3 %, y F salía −0,73 % (3,7704 frente a
    3,7980). En otras cotas del contacto, hasta 8 % en una cuña.
  - No lo veía ningún test: la forma cerrada caía en puntos exactos por suerte; la identidad con Janbu tiene caras
    verticales, donde las intersecciones son exactas; y el 4 y el 5 no tienen contactos dentro de una cuña.
  - **Arreglado:** la red se forma con las líneas de contacto ENTERAS. Test nuevo: un contacto inclinado que cruza
    caras inclinadas, contra un recorte por semiplano escrito en el test.
- **Medio: una carga en un escalón vertical se repartía por su x, mitad y mitad.**
  - Una carga lineal en la esquina de arriba de un escalón, con el tope de una cara a media altura, iba 250 + 250;
    movida 1 mm, 0 + 500 (F 3,4 % distinto).
  - Una presión horizontal sobre el escalón iba 250 + 250 en vez de 100 + 400 por altura (F +6,9 %).
  - **Arreglado:** las cargas lineales van por su posición A LO LARGO del terreno; las presiones sobre una cara
    vertical del terreno, por altura, sobre la parte que es tope de cada cuña (`_face_between`, la regla del
    rebanador).
- **Medio: una carga lineal dentro del suelo iba a la cuña cuyo tope estaba sobre su x,** no a la que la contiene.
  `edge_share` admite esas cargas a propósito: hacen de soporte equivalente en la superficie. Medido: 300 kN/m en la
  cuña equivocada, F +7,9 %. **Arreglado:** dentro del suelo, a la cuña que la contiene, mitad y mitad sobre una
  cara.
- **Bajos, arreglados:**
  - **Ru bajo agua libre:** U no era exacta. El quiebro donde el nivel del agua corta el terreno no era fin de tramo
    (4,6·10⁻³ en una base, −2,8·10⁻³ en una cara). Ahora los cruces entre cualquier par de líneas lo son: contorno,
    contactos, freáticos y piezométricas. Contra una cuadratura fina de la propia u del programa, a 2·10⁻¹¹.
  - **Ru en una cara con γG y γG,fav distintos:** tomaba la media de los factores de sus dos cuñas. La columna sobre
    cualquier punto de una cara inclinada está entera en la cuña sobre la que se inclina; ahora lee el factor de
    esa (PW 485 frente a 557, F −0,5 %). En una cara vertical sigue la media.
  - **Datos por vértice sin validar:** una c negativa, φ ≥ 90° o un ángulo NaN pasaban (tan φ = −11,4 o 1,6·10¹⁶).
    Ahora dan `ValueError`, como los globales. También dos datos sobre un mismo vértice, donde antes ganaba el último
    sin aviso.
  - **Defectos del test y del texto:**
    - el test de la sobrecarga filtraba por los ids de un proyecto NUEVO (uuid) y no filtraba nada;
    - la cabecera decía «tres cuñas», y son cinco;
    - el docstring del módulo decía que el peso se interseca con las regiones, justo lo que se dejó de hacer.
- **Lo que deciden la propietaria o 0.1.464 (§6):**
  - el número de cuñas y la política por defecto ante la regla 7;
  - los factores parciales de los materiales, que no llegan a una resistencia de cara dada a mano;
  - dos defectos anteriores a esta versión: el agua libre contra un acantilado, que pierde también el rebanador, y
    la sonda absoluta de 0,01 del material de la base.

### Corregido de 0.1.462

- **Una frase falsa del §0 de su changelog:** «con los extremos sobre el contorno exterior no pasa», del borrado de
  la capa fina. Se midió después con `_auditoria/P10_D449/reproducir_d449.py` del banco: en un bloque de 100 × 30,
  una capa de menos de unos 0,9 m desaparece también con los extremos de los dos contactos sobre el contorno
  exterior. La causa sigue sin diagnosticar, y es D449.
- **El comentario del fixture `bottom`** de `test_base_on_contact_v1462` daba la misma causa (`regions.weld_tol`) sin
  haberla medido. Ahora dice lo medido.

## 1. El cambio

- **`ogr_slip2d/sarma/wedges.py`** (nuevo): `build_wedges`, `boundaries_on`, `to_solver` y `solve_wedges`; las
  clases `Wedge` (una `Slice`), `WedgeFace` y `Wedges` (unas `Slices`).
  - **Fronteras:** los vértices de la superficie, sus cruces con el nivel freático y, con `boundaries_at_materials`
    (activado por defecto), con los contactos de material. Luego, divisiones uniformes hasta `num_wedges`, que es un
    mínimo. Los cortes salen de las funciones del rebanador.
  - **Caras:** el ángulo dado por vértice (en grados desde +x, de 0 a 360; cuenta solo la recta) o el de la política,
    hasta donde el rayo sale del suelo (`ray_ground_exit`). Las dos caras de los extremos son verticales y no llevan
    nada. Con una grieta, la de cabeza es su pared, y su agua, el empuje sobre ella.
  - **Peso:** exacto por material. El polígono de la cuña se parte por los contactos tal como están dibujados
    (Shapely), cada trozo pregunta su material en un punto interior, y debajo del freático más alto lleva el peso
    saturado, como `_column_weight`.
  - **Los quiebros de u:** también son fin de tramo los cruces entre las líneas (contorno, contactos, freáticos y
    piezométricas).
  - **U y PW:** ∫u dl con Gauss–Legendre de dos puntos en cada tramo donde u es lineal. Los tramos se cortan en los
    cruces con contactos, freáticos, piezométricas y terreno, y en las abscisas de sus vértices. u es la del rebanador
    en cada punto (`_base_pore_pressure`), con el recorte y la política de no saturado. Con una malla de presiones o
    una filtración por elementos finitos, 16 subtramos por tramo: una aproximación, declarada.
  - **Sobre el tope de cada cuña:**
    - las cargas repartidas, por tramos entre sus extremos;
    - las lineales, por dónde está su punto: sobre el terreno, por su posición a lo largo de él (la mitad en el tope
      de una cara interior); dentro del suelo, a la cuña que la contiene. Con caras verticales es la regla de bordes
      de 0.1.459 (`edge_share`);
    - una presión sobre una cara vertical del terreno, por altura;
    - el agua libre, como presión γw·d normal al terreno.
  - **Factores de acción** del diseño, por `apply_action_factors`. Ru se vuelve a leer con el factor a lo largo de
    bases y caras; una cara, con el de la cuña sobre la que se inclina.
  - **Resistencia de la base:** la de su material a la tensión de Fellenius de la cuña, max(0, W cos α − U)/l, que es
    donde la lee Janbu. Se lee sobre la columna sustituta, con la succión de la cuña. El material es el de esa
    columna: el más débil sobre un contacto (D447) o la capa débil.
  - **Resistencia de cara:** la del vértice, si no la dada para todas, si no la media ponderada por longitud de los
    materiales Mohr–Coulomb que cruza (c y tan φ, con la succión media), o ninguna.
  - **Rechazos con código:** presión en exceso (B-bar), ángulo horizontal, cara que no llega al terreno, caras que se
    cruzan, cuña que no es un polígono dentro de la masa, cuña fuera de toda región con material, y cara que cruza un
    material que no es Mohr–Coulomb. Una llamada mal hecha es `ValueError`, también con los datos por vértice.
- **`ogr_slip2d/sarma/angles.py`** (nuevo): `vertical`, `bisector` y `mean_normal` (la normal media ponderada por la
  longitud de las dos bases), `upward` y `delta_of`. Ninguna de las tres viene de una fuente: son elecciones
  geométricas para donde no se da el ángulo.
- **`ogr_slip2d/slicer.py`:**
  - de `_slice_boundaries` salen `_crossing_cuts`, `_merged_segments` y `_share_out`, sin cambiar nada, para que las
    cuñas corten por la misma regla;
  - `slice_surface(cuts=...)` sustituye los cortes del rebanador y levanta el mínimo de tres dovelas (una masa de dos
    cuñas tiene dos columnas). Sus extremos han de ser los de la superficie y crecer; si no, `ValueError`.
- **`ogr_slip2d/design_actions.py`:** `apply_action_factors(project, slices, refresh=None)`, para que las cuñas
  pidan otra vez su agua integrada.
- **`ogr_slip2d/messages.py`:** siete códigos `lem.sarma_*`, con su español en `ogr_gui/i18n/__init__.py`.
- Comentarios: el paquete `sarma` y `vertical.py` decían «hasta 0.1.463» y «de 0.1.462», de antes de D447.

## 2. El test

`tests/test_sarma_wedges_v1463.py`, 31 casos, unos 1,6 s. Contra:
- **áreas y pesos en forma cerrada** a 10⁻¹², con polígonos escritos a mano, recortados por el contacto y el freático
  con un recortador propio (Sutherland y Hodgman 1974); y un contacto inclinado que cruza caras inclinadas, contra el
  mismo recortador sobre un semiplano;
- **una cuña sobre un plano**, F = (cL + (W cos α − U) tan φ)/(W sen α);
- **Janbu simplificado** (Janbu 1954, 1973) a 10⁻¹², sobre las dovelas del propio rebanador, que las cuñas verticales
  reproducen campo a campo. Los casos: freático, agua libre, sobrecarga, cargas lineales, kh = 0,1 con kv = ±0,05,
  grieta llena, reflejo y un freático que corta dos bases. Y una envolvente curva leída donde la lee Janbu;
- **la columna:** SHANSEP (Ladd y Foott 1974) y una razón de tensión vertical leen sobre la dovela que está sobre la
  base, a la tensión de Fellenius de la cuña (Fellenius 1936);
- **el diseño:**
  - Frank et al. (2004), §11.5, con caras inclinadas (Γ = F/γG y F/γcu);
  - Ru (Bishop y Morgenstern 1960), que sigue al peso factorizado;
  - con γG y γG,fav distintos, cada cara lee el factor de la cuña sobre la que se inclina;
- **los publicados 4 y 5** (Hoek 1987) a ±1 %, y la herramienta del banco a 10⁻⁶, con sus pesos. Reducir solo las
  bases se aparta +14,8 %, −58 % y +2,8 %;
- **la identidad de los tramos rectos** y el reflejo;
- **las cargas, una vez y donde están:** el tope de una cara, la esquina de un escalón, dentro del suelo, y la presión
  del escalón por altura;
- **el agua libre:** γw·24 hacia abajo y ½γw·2² contra el talud;
- **Ru bajo agua libre,** contra una cuadratura fina de la u del programa;
- **cada opción que mueve el número, cada rechazo y las llamadas mal hechas.**

Mutantes: `_auditoria/P9_D357/mutants_v1463.py` del banco, con su log. Mueren 43 de 44: los 36 de antes de la
revisión y uno por cada uno de sus arreglos. Vive uno, declarado equivalente: Gauss en el punto medio, porque u es
lineal en cada tramo y el punto medio también es exacto ahí. Dos ramas no tienen test, y se declara: la de una malla
o una filtración (16 subtramos) y la de una grieta al pie del sentido de deslizamiento.

`tests/test_core_messages_v1333.py` gana las muestras de los siete códigos nuevos.

## 3. Lo que no cambia

- Ningún número del programa: el método no está registrado, y el rebanador da lo mismo bit a bit a todo el que no
  pasa `cuts`. Lo comprueban las 37 áreas de rebanado, Sarma, diseño, contactos, cargas lineales, mensajes e i18n:
  584 de 584.
- Ninguna cadena de la interfaz, ajuste ni acción.

## 4. Verificación

- **La suite entera, `--jobs 4`:** 7884 casos; pasan 7883, uno saltado, sin fugas ni tramos muertos. La primera
  pasada dio un fallo: el español de `lem.sarma_excess_pore_pressure` decía «B-bar», forma retirada del vocabulario
  (`test_voice_and_terms_v1325`: «B-barra»). Corregido, y la segunda pasada, entera, sale en verde.
- **El test nuevo**, solo: 31 de 31, en unos 2,6 s con el arranque del runner.
- **Mutantes:** 44, y vive uno, el equivalente declarado.
- **Los README:** 7852 → 7883 tests.

## 5. Banco

- `_auditoria/P9_D357/mutants_v1463.py` y su log.
- La ficha D357, el progreso de esta versión.

## 6. Lo que queda para la propietaria y para 0.1.464

- **Caras de una política que se cruzan:** se rechazan con código (§0). Hay que decidir qué hace una búsqueda con
  esos círculos: rechazarlos, reordenar sus topes o volver a la vertical en esas caras. Va junto con la política por
  defecto, la bisectriz en el plan.
- **El número de cuñas y la regla 7:** sobre una polilínea de bases Mohr–Coulomb no mueve F (§0). En cuatro
  polilíneas en cuenco de la revisión, 1, 6, 12 y 25 cuñas dan el mismo F a 12 cifras. Con 25 y la bisectriz solo
  añaden rechazos: 42 de 51 cuencos al azar, frente a 3 con una cuña por tramo. La revisión propone, para 0.1.464,
  dividir en una polilínea solo donde la resistencia de la base dependa de la tensión.
- **El corte en el freático** (§0, la desviación del plan) puede provocar un cruce incluso con el mínimo de cuñas: en
  una sonda de la revisión, un corte a 0,42 m de un quiebro. La revisión propone cortar ahí solo con caras
  verticales.
- **Los factores parciales de los materiales** no llegan a una resistencia de cara dada a mano, global o por vértice.
  Las tareas lo ponen en 0.1.464 (global) y 0.1.465 (por vértice).
- **Anteriores a esta versión, sin tocar:**
  - el agua libre contra un acantilado, sobre el pie que sale por él, se pierde: 44,1 kN/m (½γw·3²) en las cuñas y en
    el rebanador;
  - la sonda del material de la base es un 0,01 absoluto (D48r y D64): en una copia del modelo a escala 1:100, Janbu
    pasa de 2,9427 a 2,7579, y las cuñas lo heredan por sus columnas.
