# OGR Slip2D v0.1.219

Segunda de las cuatro versiones que cierran lo que queda del paquete P4 del
banco de verificación. El sismo pseudoestático:

- **D206 — kh y kv actúan sobre el SUELO de cada dovela, no sobre la
  sobrecarga que el rebanador pliega en su peso.** Una carga repartida o
  lineal no recibe ninguna fuerza sísmica. Un relleno con masa se dibuja como
  material (decisión de la propietaria).
- **Dentro de D206, de la misma clase: kh es una magnitud.** La entrada lo
  rechaza negativo, y el motor lo aplica igual en todos los métodos: los
  momentos sobre círculo de Bishop y de Spencer/GLE saltaban un kh negativo
  que todos los equilibrios de fuerzas aplicaban. La propietaria pidió
  investigarlo y hacer «lo adecuado y matemáticamente correcto, así como
  física y geotécnicamente lógico» (sección 0).

Cero filas del banco: los 8 modelos con el sismo activo no tienen cargas y
ninguno tiene kh < 0.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Las fuentes, y lo que se decidió

### Sobre qué peso actúa el sismo

- **La documentación de la referencia**: «Seismic Force = Seismic Coefficient
  × Slice Weight = Seismic Coefficient × area of slice × Unit Weight of slice
  material». Aplicada en el centroide de la dovela. Sus cargas repartidas son
  «tractions», y sus diálogos de carga no tienen ninguna opción sísmica.
- **Duncan, Wright & Brandon (2014, §10.1)**: la fuerza pseudoestática en el
  centro de gravedad de cada dovela o de la masa de suelo deslizante
  (Terzaghi 1950).
- **SLOPE/W** (*Stability Modeling with SLOPE/W*, 2022, §10.3): `F = k·W`, con
  W el peso de la dovela, y el agua embalsada excluida («the seismic
  coefficient is only applied to the total slice weight minus the surcharge
  water weight»).
- **OGR contra sí mismo**: el docstring de
  `excess_pore_pressure.seismic_delta_sigma_v` decía que la sobrecarga no es
  masa acelerada «con el mismo convenio que `slice_forces` usa para kh», y
  `slice_forces` hacía lo contrario.

Se ofrecieron tres opciones a la propietaria:
- solo el suelo;
- un atributo «tiene masa» por carga, apagado;
- el mismo atributo, encendido.

Eligió **solo el suelo**, sin atributo y sin migración: un `.ogr` con sismo Y
cargas cambia de factor, como cambió uno con kv ≠ 0 en 0.1.214.

### El signo de kh

La propietaria no eligió entre las opciones que se le dieron. Pidió que se
investigara la documentación, el código e internet y que se hiciera lo
correcto.

- **La referencia**: «The HORIZONTAL seismic coefficient is always POSITIVE,
  and represents a horizontal seismic force directed OUT OF the slope (i.e. in
  the direction of failure)». El sentido de la rotura no afecta a la entrada.
  Ky es siempre ≥ 0: si el talud ya está por debajo del objetivo, Ky = 0.
- **EN 1998-5** (lección del JRC sobre la parte 5): el coeficiente de taludes
  es `0,5·a_g·S/g`, una magnitud, y solo el vertical lleva los dos signos,
  `kv = ±0,5·kh`.
- **Kramer (1996, §10.6.1) y DW&B (§10.1)**: la comprobación pseudoestática
  es el sentido desfavorable, hacia fuera del talud.
- **El código**: cada método aplica `h_seismic` en el sentido de
  deslizamiento de su superficie, y `yield_acceleration.py` ya llamaba a un kh
  negativo «a force up the slope». Pero
  `bishop.py` e `interslice.py` tenían `if kh > 0` en el momento sobre círculo
  y Janbu, las fuerzas de Spencer/GLE, el Ordinario, la familia de inclinación
  prescrita y el retroanálisis aplicaban cualquier signo. **Un mismo modelo
  daba respuestas distintas según el método**: medido en 0.1.218, Bishop con
  kh = −0,1 daba exactamente F(0) = 0,6869.

Lo que se hizo:

- **En el motor, lo matemáticamente correcto**: el término sísmico es lineal
  en kh en todas las ecuaciones, y ninguna razón física justifica tirarlo en
  una sola y para un solo signo. `if kh` en las dos guardas, como ya hacían
  `moment_balance` y el retroanálisis. Con kh ≥ 0, bit a bit lo de antes.
- **En la entrada, lo geotécnicamente lógico**: kh es la magnitud de una
  fuerza cuyo sentido decide cada superficie, así que un signo no aporta nada
  que el modelo necesite. Un kh negativo solo puede ser una fuerza hacia el
  talud, que ninguna comprobación pseudoestática usa, o, peor, un signo
  tecleado para decir «hacia la izquierda»: con el sentido automático, eso
  habría SUBIDO el factor sin avisar. `seismic_coefficient_refusal` lo
  rechaza, y la preguntan la API, `check_analysis_settings` (un `.ogr` o un
  script, con la razón) y el diálogo, cuyo kh empieza en 0 y, si el proyecto
  guardaba uno negativo, lo dice en vez de convertirlo en cero en silencio.
- **Sin tocar**: kv conserva los dos signos, porque arriba y abajo son dos
  casos reales. La búsqueda de Ky solo usa kh ≥ 0. El probabilístico comprueba
  el proyecto base una vez: un kh muestreado negativo lo aplican ahora todos
  los métodos por igual.

## 1. Los arreglos (motor)

- **`slicer.py`**: `Slice.soil_weight`, el peso del suelo guardado EXACTO
  antes de que se le sumen las cargas. Una dovela construida a mano (tests, el
  sustituto de los soportes) no lo tiene y es toda suelo.
- **`external_forces.py`**:
  - `seismic_soil_part(s)` y `seismic_vertical_load(s, kv)`, que calcula
    `W_suelo·(1 + kv) + (W − W_suelo)`;
  - con kv = 0 devuelve el propio `s.weight`, y sin carga el segundo término
    es exactamente cero;
  - `h_seismic = kh·W_suelo`;
  - `seismic_soil_weight` sigue siendo el único sitio del factor (1 + kv);
  - interruptor `SEISMIC_SOIL_ONLY`; la tabla `INTERRUPTORES` del banco pasa
    a 23.
- **Por el ayudante pasan** las cinco sumas del sentido de deslizamiento (Bishop,
  Spencer, GLE, Ordinario, familia prescrita) y el retroanálisis, con sus dos
  `kh·s.weight`.
- **La revisión del diseño encontró una trampa antes de escribir**:
  `(w − b)·(1 + kv) + b` no devuelve `w` bit a bit con kv = 0 (lo hace mal en
  un 4,9 % de pares aleatorios). Por eso se guarda el peso del suelo y no se
  reconstruye restando.
- **Docstrings y textos**: `seismic_delta_sigma_v` (ahora es verdad),
  `SeismicLoad`, `checks._denominator_sign` (con cargas y kv ≠ 0 el factor ya
  no es constante), la API, el servidor MCP, `docs/mcp/herramientas.md` y la
  etiqueta del diálogo sísmico, que pasa por `tr()`.

## 2. Tests

`test_seismic_surcharge_v1219.py`, 13 casos:

- **La cuña plana pseudoestática cerrada** (Kramer 1996, §10.6.1) con una
  sobrecarga sin inercia, `V = W(1 + kv) + Q` y `H = kh·W`. La reproducen
  Janbu, Corps 1, Corps 2 y Lowe-Karafiath a 1e-11/1e-8 con los cinco
  sismos de `test_seismic_convention_v1214`. Q es la que aplicó el rebanador,
  que lee la carga en el centro de cada dovela (un 0,14 % menos que la franja
  cargada).
- **Regla 7**: con el interruptor apagado la cuña es la de la sobrecarga con
  masa, a 1e-11.
- **Las fuerzas de la dovela**: el suelo aparte, bit a bit con kv = 0, bit a
  bit sin cargas y con una dovela hecha a mano.
- **kh como magnitud**:
  - la regla (y kv negativo sigue valiendo);
  - la API;
  - `check_analysis_settings`;
  - el diálogo;
  - y la identidad `1/F(kh) + 1/F(−kh) = 2/F(0)` en un círculo no drenado,
    donde todo término con kh es lineal: a 1e-12 en Bishop, el Ordinario y
    Janbu, y a 1e-9 en Spencer y GLE.

**Contra 0.1.218 fallan 9 de 13**: 6 por comportamiento y 3 por símbolo
(`soil_weight`, `SEISMIC_SOIL_ONLY`). Pasan los cuatro controles. En 0.1.218
Bishop daba F(−0,1) = F(0) = 0,6869.

## 3. Lo que se reporta y NO se corrige

- **El muestreo probabilístico no pregunta la regla**: `set_value` escribe el
  kh o el kv muestreado directamente, incluso fuera de |k| < 1. Con el motor
  coherente, un kh negativo ya no depende del método, pero el rango no se
  comprueba. No se abre ficha: el recorte al mínimo relativo es de la
  distribución que elige el usuario.
- **`factor_permanent` de las normas de diseño** sigue sin aplicarse a ninguna
  carga (reportado en 0.1.165). Es relevante aquí porque la referencia marca
  cada carga Variable/Permanent solo con una norma activa.

## 4. Verificación

- Selección dirigida (sismo, exceso de presión, cargas, retroanálisis,
  estanques, Newmark y Ky, los nueve métodos, marcha, API, i18n, diálogos,
  versión): 663 de 664 antes de escribir este archivo; la que faltaba era
  precisamente la existencia de este changelog.
- Suite entera: **4903 de 4903** (33 min 4 s).
- Banco: `d206()` cierra y da NO SE SOSTIENE contra 0.1.218 (la cuña da
  0,6597 frente a 0,6906, la regla admite kh < 0 y Bishop no es simétrico).
