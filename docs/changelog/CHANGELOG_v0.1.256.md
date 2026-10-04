# OGR Slip2D v0.1.256

**D237: los ángulos de proyección de la Block Search se leen como el arco
que denotan en su lado, y lo que no sigue la convención de la referencia se
dice.** Hasta 0.1.255 la búsqueda enderezaba un par escrito al revés con
`min`/`max` sin decirlo, calculaba con cualquier ángulo, y el panel de
*Surface Options* reescribía el modelo al pulsar OK.

Primera versión de la tanda P5 (D237, D238, D244, D243, D245, D247 con
D255, D248 y D250). La propietaria decidió (2026-10-04) que un par al revés
se trate «como sea correcto en lo geotécnico, lo físico y lo matemático» y
que un ángulo fuera de los límites de la referencia **solo se avise**.

## 0. Lo que se encontró

- **Qué dice la referencia.** Los ángulos se miden «COUNTER-CLOCKWISE from
  the positive horizontal axis», y «the Start Angle must always be LESS than
  the End Angle». En una búsqueda típica van de 95 a 175 a la izquierda y de
  5 a 85 a la derecha. Para superficies que salen por la cara con
  buzamiento descendente, la izquierda llega a 265 en un talud que mira a la
  izquierda y la derecha baja a −85 en uno que mira a la derecha, y solo de
  ese lado.
- **Un par al revés tiene una sola lectura con sentido.** Un ángulo de
  proyección es una dirección: 315° y −45° son el mismo rayo. Entre dos
  direcciones hay dos arcos, y en cada lado solo uno evita la dirección que
  ese rayo no puede tomar nunca (0° para el izquierdo, que apuntaría a la
  derecha; 180° para el derecho). El otro arco entre 45° y −45° contiene los
  rayos de 90° a 270°: un rayo derecho que apunta hacia atrás y cruza la
  propia superficie. Así que «45 to −45» a la derecha es [−45, 45], que es
  justo lo que hacía `min`/`max`. El arco no depende del orden en que se
  escriban los dos ángulos, y un sorteo uniforme sobre él tiene la misma
  distribución en los dos órdenes. Por eso se endereza; lo que faltaba era
  decirlo.
- **Donde `min`/`max` sí se equivocaba:** con un ángulo escrito en la otra
  vuelta. El panel solo admitía 0–360, así que la «−45» de la referencia
  había que escribirla 315, y «315 a 45» se calculaba como 45..315: rayos
  derechos que apuntan a la izquierda.
- **Los límites son cinemáticos.**
  - 5° de margen con la vertical, para que el rayo tenga lado y la
    superficie siga siendo monótona en x, que es lo que exige el rebanado
    vertical.
  - El lado de la coronación no puede bajar: el escarpe de cabeza sale hacia
    arriba, y un rayo descendente no llega nunca a una coronación
    horizontal.
  - Solo el lado de la cara puede salir por ella con buzamiento
    descendente.
- **El lado de la cara no se puede leer de la cara más inclinada.**
  `steepest_face_index` se salta los segmentos verticales, y con una cara
  vertical, el caso con el que la referencia dibuja el límite de 265°,
  acabaría en un segmento plano. Se lee de los dos extremos del terreno, como
  ya hacía `crest_end_is_on_the_right`.
- **El panel reescribía el modelo de dos maneras.** Las cuatro casillas
  recortaban a 0–360, así que abrir *Surface Options* sobre el problema 109
  del banco y pulsar OK guardaba su −45 como 0. Y su único decimal
  redondeaba cualquier ángulo puesto por la API. Medido con un `git archive`
  de 0.1.255 sobre el talud del test, con izquierda 135..225,25 y derecha
  45 → −45: OK dejaba 135; 225,3; 45; 0.
- **El 109 del banco:** el enunciado escribe «45 to −45» a la derecha. Leído
  como −45..45, baja de 5° del lado de la coronación, y la referencia no lo
  admite en un talud que mira a la izquierda. Los rayos de −45 a 5 no llegan
  a la coronación (y = 9). Desde el extremo trasero de la junta 1,
  (18,573; 5,890), tampoco llegan los de 5 a ~15°, que no alcanzan y = 9
  antes de x = 30. Las superficies válidas salen, por tanto, del mismo tramo
  de ángulos con «−45..45» que con «5..45»; lo que cambia es cuánto
  presupuesto se tira.

## 1. Los cambios

- **Una sola regla en `ogr_core/project/rules.py`:**
  - los límites de la referencia como constantes con nombre
    (`BLOCK_LEFT_MIN`, `BLOCK_LEFT_MAX`, `BLOCK_LEFT_MAX_FACE`,
    `BLOCK_RIGHT_MIN`, `BLOCK_RIGHT_MIN_FACE` y `BLOCK_RIGHT_MAX`);
  - `block_projection_range(start, end, side)`: lleva cada ángulo a la
    ventana **cerrada** de su lado ([0, 360] a la izquierda, [−180, 180] a la
    derecha) y devuelve el arco. Solo desplaza un valor estrictamente fuera
    de la ventana, así que dentro de ella devuelve exactamente
    `(min, max)`. Con una ventana semiabierta, una izquierda de 300..360
    habría salido 0..300, el arco opuesto;
  - `block_angle_limits(side, crest_on_right)` y
    `block_angle_notes(angles, crest_on_right)`: notas con código, valores y
    texto inglés, para que la interfaz las diga en su idioma.
- **`failure_direction.model_crest_is_on_the_right(project)`:**
  `crest_end_is_on_the_right` sobre los dos extremos del terreno del modelo.
- **`BlockSearch._run`** sortea con `rng.uniform(*block_projection_range(…))`:
  el mismo número de sorteos (uno por lado y candidata, también con inicio =
  fin) y en el mismo orden.
- **`settings_warnings`**, solo con Block Search, dice el par releído y lo
  que queda fuera de los límites. Llega a `run_analysis`, a
  `settings_get`/`settings_set` y a `settings_diagnostics` de la API. La
  fila de `settings_set` de la guía del MCP lo dice.
- **El panel de *Surface Options*:**
  - las casillas llegan de −360 a 360, y hasta el valor guardado si queda
    fuera;
  - `apply()` escribe un ángulo solo si el usuario tocó su casilla (o pulsó
    *Defaults*);
  - una etiqueta no modal bajo las casillas dice en vivo lo que hará la
    búsqueda, compuesta con `tr()` desde el código de cada nota y con su
    entrada en español.

## 2. Tests

**Nuevo `tests/test_block_angles_v1256.py`**, 19 casos:
- 315 ≡ −45 a la derecha y −135 ≡ 225 a la izquierda dan la misma búsqueda
  bit a bit;
- un par al revés dentro de su ventana sortea lo mismo que el derecho
  (control);
- la identidad `(min, max)` dentro de las ventanas, y la ventana cerrada;
- cada límite de la referencia, a cada lado del valor, por los dos lados, en
  las dos orientaciones y con cara inclinada y vertical;
- la nota por el análisis (`run_analysis`) y por la API (`settings_set`, sin
  `Conflict`);
- el panel: OK conserva el −45 y un 225,25, una casilla tocada sí se
  escribe, la etiqueta lo dice y lo dice en español (el idioma se restaura en
  `finally`).

Las comprobaciones de límites pasan por `settings_warnings`, que ya existía,
para que contra 0.1.255 fallen por comportamiento y no por una importación.

**Discriminación** contra un `git archive` de 2eb5ace (0.1.255), con el
envoltorio sin buscador editable: **fallan 14 de 19**:
- nueve por comportamiento (las dos equivalencias, las notas por el
  análisis y la API, el par al revés, los tres casos de límites que exigen
  nota, y el OK que reescribía);
- tres por la función nueva y dos por la etiqueta nueva.

Pasan los tres controles y las dos ausencias.

## 3. El banco

- **Censo:** 12 modelos con Block Search, seis del 02 (007, 008, 009,
  020 `modelo_bloque`, 075 `modelo_bloque` y 109) y seis del 03 (001, 003,
  004 ×2 y 005 ×2). Todos llevan sus ángulos dentro de la ventana de su
  lado, y solo el 109 sale de los límites de la referencia.
- **A/B árbol contra árbol** (`_auditoria/P5_0256/ab_d237.py`): un
  `git archive` de 0.1.255 frente a este árbol. Corre la búsqueda entera de
  cada modelo con su primer método y guarda una huella de todas las
  evaluaciones (factor y vértices en `repr`) y de la crítica. Con el 109
  **tal como estaba**: 0 de 12 modelos distintos y las mismas 36 984
  evaluaciones bit a bit. El A/B de las tandas anteriores re-evalúa
  superficies archivadas y no vuelve a correr la búsqueda, así que no
  habría visto un cambio en el sorteo.
- **El 109, re-declarado aparte**, con la derecha 5..45 por decisión de la
  propietaria. La razón va en `construir_modelo.py` y en `referencia.json`
  (`angulos_declarados`). El `.ogr` regenerado cambia en los dos ángulos y
  en cinco campos de la norma de diseño que el archivo viejo no traía y
  ahora salen con su valor por defecto (deriva de esquema: la norma está
  apagada).

  | método | 0.1.233 (45 → −45) | 0.1.256 (5..45) | manual |
  |---|---|---|---|
  | Bishop | 4,692466 (242 válidas) | 4,684206 (533) | 1,799 |
  | Janbu simplificado | 4,320419 (279) | 4,301805 (638) | 1,610 |
  | Spencer | 4,768045 (239) | 4,848857 (526) | 1,803 |
  | GLE | 4,800815 (239) | 4,870487 (524) | 1,804 |

  Con 0.1.256 y la declaración vieja, el A/B da exactamente el Bishop de
  0.1.233 (4,692465664907131, 242 válidas): el cambio es de la declaración,
  no del motor. Más válidas, porque los rayos que no llegaban a la
  coronación ya no se sortean; el mínimo apenas se mueve, como ya midió la
  variante «d237» de 0.1.233. La crítica de Bishop sigue empezando en
  (14,6126; 5,456), 0,99 m bajo la huella: es D238, la siguiente versión.
  D243 sigue abierta.
- **`d237()`**, en el verificador del 02:
  - en vivo, el 109 con 45 → −45 en memoria se lee −45..45 y se dice por
    el análisis, la API y el panel, y OK no lo reescribe;
  - el A/B;
  - el 109 re-declarado y corrido con 0.1.256;
  - la discriminación.

  Veredicto CUBIERTO POR TEST. Con 0.1.255 da NO SE SOSTIENE: la parte en
  vivo no encuentra la regla.
- **Verificación entera:** 226 cierres y 0 bajadas.
- **Cierre del ciclo:**
  - instantánea 0.1.256;
  - D237 retirada, con su nota de cierre en la ficha;
  - `PAQUETES` de P5 podado y **reordenado**: D244 pasa delante de D243,
    porque sin las razones de rechazo de D244 el censo de D243 contaría
    como «sin rebanar» lo que son extremos fuera del terreno. La cadena de
    la tabla de paquetes, tachada y con el mismo orden;
  - prompts regenerados (las 15 FALTA son anteriores y ninguna es de la
    tanda);
  - auditorías del 02 y de la raíz con 0 ERROR;
  - instantánea con `--forzar`;
  - `--seco` completo tras retirar, llamado comprobación a comprobación
    contra una copia del motor de este árbol: los 226 veredictos, iguales al
    JSON. Tres detalles difieren en contadores que crece el propio cierre:
    los `.ogr` contados por D96 (15 436 → 15 641, porque cuentan la
    instantánea nueva), las claves del JSON de D186 (225 → 226) y las citas
    del índice de D188 (172 → 173).

## 4. Verificación

- **Suite entera:** 5609 de 5609.
- **Selección** de Block Search, *Surface Options*, ajustes, API de
  ajustes, i18n, dirección de rotura, desigualdad de búsquedas y menús:
  375 de 375 (23 archivos).

**Qué falta por probar:**
- **En pantalla:** el panel de *Surface Options* con la etiqueta de avisos a
  la vista, sobre el 109 y sobre un modelo con los ángulos dentro de los
  límites (donde no tiene que salir nada).
