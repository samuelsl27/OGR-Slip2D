# OGR Slip2D v0.1.467

**Interpretar con cuñas (D357).** La ventana Interpretar ya no enseña un resultado de Sarma como si sus cuñas fueran
dovelas verticales:
- **la selección** elige la cuña cuyo polígono contiene el clic, y **el zoom** encuadra ese polígono;
- **el resaltado** dibuja las fuerzas que el método resolvió sobre la cuña;
- **el panel** da E, E′, X y el ángulo de sus dos caras;
- **el diagrama de sólido libre** es el de la cuña, con la suma de sus fuerzas;
- **la línea de empujes** dice por qué no existe para Sarma.

Además, Sarma cumple el contrato de `base_shear_force`, la fuerza motriz, como los demás métodos. Ningún factor de
seguridad cambia, de ningún método.

Decisiones de la propietaria (2026-11-16):
- **Se puede seguir sin D452 hasta los ángulos optimizados,** y D452 va delante de ellos. Interpretar enseña las
  fuerzas de la solución sea cual sea la raíz, y la herramienta de ángulos es interfaz. Los ángulos optimizados
  minimizan F cruzando configuraciones donde un polo atraviesa las raíces, y la regla de la raíz decide qué F ve el
  optimizador.
- **Dos versiones:** 0.1.467 la ventana; 0.1.468 el informe y las exportaciones (CSV, API y HDF5).
- **El orden nuevo:** 0.1.469 la herramienta de ángulos y el menú contextual del vértice, 0.1.470 D452 y 0.1.471 los
  ángulos optimizados. La spec 009 se renumera en este commit.
- **Sarma cumple el contrato de `base_shear_force`.**
- **D453 se abre** (las unidades de la tabla de dovelas del informe) y va con el informe, en 0.1.468.

## 0. Lo que se encontró

### Las exploraciones del plan (solo lectura)

Nada reventaba con un resultado de Sarma, pero casi todo lo enseñaba mal:
- **El panel** decía «no — this method does not resolve them» en las fuerzas entre dovelas. Sarma las resuelve, y
  `details["sarma_face_*"]` no lo leía nadie.
- **El diagrama de sólido libre** preguntaba el número de dovela y después ponía un mensaje en la barra de estado.
- **La selección** iba por el rango en x de la base y por la columna vertical. Un clic en la parte alta de una cuña,
  más allá de una cara inclinada, elegía la vecina.
- **El zoom** encuadraba la columna; **las flechas** ponían W en el centro de la columna.
- **La línea de empujes** decía «unavailable», sin motivo.
- **`base_shear_force` de Sarma** era el cortante movilizado, (c′l + N′ tan φ′)/F. El contrato de `LEMResult` dice que
  es la fuerza motriz s·W·sen α, y el panel lo rotulaba «Driving shear W·sinα». Es el mismo defecto que 0.1.107
  arregló en otros cinco métodos (`bishop.driving_shear_forces`).
- **De paso, D453, de antes de Sarma:** la tabla de dovelas del informe PDF titula «Base σ [kPa]» y «Shear str.
  [kPa]» e imprime `base_normal_force` y `base_shear_strength`, que el contrato declara fuerzas en kN/m. Pasa en todos
  los métodos y va en 0.1.468.

### Al escribir

- **Las fuerzas de una cuña** (`solver.wedge_free_bodies`) salen de la misma recurrencia que la raíz (`_forces`), con
  la cortante de la base tomada de la ley de resistencia y no del resto del balance. Así, que sumen cero es una
  comprobación de verdad, no una tautología. Con la tolerancia de la raíz a 1e-12 cierran entre 1e-13 y 1e-16 de la
  carga, en el 4 seco y saturado, con 2 y 25 cuñas y reflejado. Con la de 1e-4 por defecto, el resto queda en la cuña
  de cabeza (2,6e-4 de su carga en el 4 saturado con la bisectriz), porque la cara de cabeza toma el empuje dado y no
  la última E de la recurrencia; el docstring lo dice. La N′ de la escarpa del 4 saturado con 2 cuñas es −20 012,33 kN/m, la de la herramienta del
  banco.
- **El equilibrio no ve una reflexión mal deshecha:** reflejar todas las fuerzas sigue sumando cero. Los mutantes que
  no deshacían la reflexión vivían. Un test nuevo compara la pendiente reflejada con la imagen especular de cada
  fuerza, cara por cara.
- **Las anclas de los mutantes de varias líneas** no casaban con el fuente desindentado de los métodos, y la barra
  invertida de un heredoc llegó como salto de línea (la trampa conocida). Pasaron a anclas de una sola línea.

### La revisión adversaria (un agente)

No encontró ningún alto: ningún factor se mueve, y las fuerzas de las cuñas cierran en todo lo que probó:
- el talud con cargas y agua estancada, kh y kv, grieta, grieta reflejada;
- el sentido cinemático, la política vertical y Ru;
- una rejilla real, con la población volcada y con norma de diseño.

Encontró dos medios y varios bajos, todos arreglados:
- **MEDIO — un clic justo por encima del terreno elegía una cuña lejana.** Fuera de todo polígono competían las
  cuñas cuya BASE cubría la x del clic: en el 4 saturado con 25 cuñas, una a 34,6 m cuando la de cabeza estaba a
  6,5 m. Ahora compiten las que la cubren con su polígono, y gana la más cercana.
- **MEDIO — el test no veía kh, kv, la grieta, el sentido cinemático ni Pₓ.** Cinco mutantes vivían: kh = 0, el
  sentido siempre fijo, el empuje de la grieta a cero, kh·W sobre la carga entera y el signo de Pₓ. Ahora el
  equilibrio se comprueba también en el talud con cargas y agua estancada, con kh y kv, con grieta, con grieta
  reflejada y en el 5 cinemático, y los cinco mueren.
- **BAJOS:**
  - La «W» del diagrama era la carga vertical entera (suelo·(1 + kv), cargas y agua estancada) y no la W del panel, y
    «kh·W» era kh por el suelo estático. Se llaman «Wv» y «kh·Ws».
  - Los rótulos eran módulos y escondían la tracción: la escarpa del 4 saturado tiene N′ = −20 012 kN/m, y el
    diagrama decía «N′=20012.3». Ahora llevan el signo de su convenio.
  - Los caminos de fallo daban un motivo falso. El diagrama decía «dovelas verticales dadas como tales» ante unas
    fuerzas que no se pudieron recuperar, preguntaba el número de cuña antes de saber si había algo que dibujar, y el
    resaltado volvía a las flechas de una dovela vertical sobre una cuña. Arreglado: cada caso con su motivo, sin
    preguntar, y el polígono solo.
  - El panel podía decir «no — este método no las resuelve» de un Sarma que había perdido sus fuerzas: ahora dice que
    sí.
  - El test del contrato era tautológico (comparaba con la misma función). Sarma entra en
    `test_janbu_base_forces_v1107.ALL_METHODS`, que lo compara con s·W·sen α escrito a mano y con el equilibrio
    vertical: pasa.
  - Textos de la spec que contaban mal las versiones o seguían con la guarda de 0.1.466.
- **Se declara, sin cambio:** Sarma sobre dovelas verticales dadas como tales (desde un guion, sin `faces`) tiene sus
  fuerzas en el panel y no tiene diagrama, con su motivo.
- **Se declara: cambian números exportados.** El cambio de `base_shear_force` mueve, para Sarma, la columna
  `driving_shear` del CSV de Interpretar y de la vista `slices` del API, el `base_shear_force` de `results_get` y el
  `LEMResult.to_dict` (el JSON de la CLI): pasan a ser la fuerza motriz. Ningún factor ni ninguna decisión del
  programa leen ese campo (lo comprobó la revisión: búsqueda, comprobaciones, HDF5, informe y desembalse).

## 1. El cambio

- **`ogr_slip2d/sarma/solver.py`:** `WedgeForce` y `wedge_free_bodies`, en el orden y las coordenadas del modelo,
  deshaciendo la reflexión del marco de resolución. Sin puntos de aplicación: la derivación equilibra las fuerzas de
  cada cuña, no sus momentos.
- **`ogr_slip2d/postprocess.py`:** `WedgeArrow` y `sarma_wedge_forces(result)`. Usa `wedges.to_solver` con el kh, el
  kv y el sentido del cortante que aplicó el método, y rehidrata una población volcada.
  - Los puntos son un convenio: el centroide del polígono para W, kh·W y Pₓ; el punto medio de la base para N′, U y S;
    el punto medio de la cara para E y X.
- **`ogr_slip2d/methods/sarma.py`:** `base_shear_force` es `driving_shear_forces`, y el cortante movilizado pasa a
  `details["sarma_base_shear"]`.
- **`ogr_gui/interpret_window.py`:**
  - la selección por polígono, el zoom al polígono y las flechas de la cuña;
  - en el panel, las fuerzas de cara de Sarma desde sus `details` y las filas E′ y θ a cada lado (90° en una dovela
    vertical);
  - `_wedge_free_body_diagram`, no modal;
  - el motivo de la línea de empujes;
  - para Sarma sobre dovelas verticales dadas como tales, un mensaje con su motivo.
- **Español** de cada texto nuevo; sale el del mensaje provisional de 0.1.464.
- **La spec 009:** las versiones nuevas y la tarea 28 hecha.

## 2. El test

`tests/test_sarma_interpret_v1467.py`, 14 casos. Comprueba:
- **las fuerzas de cada cuña:**
  - el equilibrio, en el 4 (ocho configuraciones) y con cada fuerza que toma el solver (cargas y agua estancada, kh y
    kv, grieta, grieta reflejada, el 5 cinemático);
  - la imagen especular;
  - la N′ de la escarpa contra la herramienta;
  - el contrato de `base_shear_force`;
- **la ventana:**
  - un clic dentro de la cuña de la escarpa, a la izquierda de su base, la elige a ella, donde la columna elegía la
    vecina, y un clic justo por encima del terreno elige la cuña más cercana;
  - el zoom encuadra su polígono;
  - el panel da E, E′, X, θ y la fuerza motriz;
  - el resaltado dibuja una flecha por fuerza;
  - el diagrama se abre no modal, con su título, la suma y los rótulos con signo (N′ = −20 012,3 en la escarpa);
  - sin fuerzas que recuperar, el motivo verdadero, sin preguntar el número, y el polígono solo;
  - la línea de empujes dice su motivo;
  - el español;
- **nada más se mueve:** el panel de Spencer sigue con la marcha de siempre y caras de 90°.

`test_interpret_slice_data_v187` admite ahora las filas E′ como guion en Bishop, y `test_janbu_base_forces_v1107`
cuenta a Sarma entre sus métodos.

Mutantes: `_auditoria/P9_D357/mutants_v1467.py` del banco, con su log. Son 21, contando los cinco que vivían contra el
primer test, y no vive ninguno.

## 3. La suite

- `test_interpret_slice_data_v187`: las filas E′ pueden ser guion con Bishop.
- `test_janbu_base_forces_v1107`: Sarma entra en `ALL_METHODS`.

## 4. Verificación

- **La suite entera, `--jobs 4`, una vez tras la revisión:** 7950 casos; pasan 7949 y uno queda saltado, sin fugas ni
  tramos muertos. La última serie en verde es de hace 45 commits.
- **El test nuevo:** 14 de 14. **Mutantes:** 21, ninguno vivo.
- **Los README:** 7935 → 7949 tests.

## 5. Lo que queda

- 0.1.468: el informe (tabla de cuñas, tabla de caras, ajustes de Sarma, D453) y las exportaciones (CSV, API, HDF5).
- El banco, tras el commit: D453 abierta con versión 0.1.468, D452 con 0.1.470, y el progreso de D357.
- **Prueba a mano para la propietaria:** Interpretar sobre el 4 saturado con 25 cuñas: seleccionar una cuña de la
  escarpa, ver el panel, el diagrama y la línea de empujes.
