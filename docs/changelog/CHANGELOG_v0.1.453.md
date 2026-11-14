# OGR Slip2D v0.1.453

**Una sola regla responde «¿es aleatoria esta variable?», y la corrida dice qué deja fuera (D416).** Había dos reglas:
- la del cálculo, `Distribution.not_random_reason`, que lee `is_random` y con ella el muestreo de los dos análisis
  probabilísticos y el botón Graficar distribución, solo pedía desviación a la Normal y a la Lognormal;
- la del agente, `variable_problems`, se la pedía también a la Beta y a la Gamma, y las rechazaba sin ella.

Medido con 0.1.452 (2889daa), media 15, rango ±3, 200 muestras LHS con semilla 1:

| distribución, desviación 0 | `not_random_reason` | muestras | curva | agente |
|---|---|---|---|---|
| Beta | `''` (aleatoria) | 15,000000 a 15,000000 | 0 en todo el rango | la rechaza |
| Gamma | `''` (aleatoria) | 14,999988 a 15,000011 | 0 en todo el rango | la rechaza |

Con varianza cero son una masa puntual en la media. El núcleo solo las dibujaba así por sus guardas (`_frozen`): a la
Beta le sujeta la desviación a 1e-12, y a la Gamma la escala a 1e-12, lo que le deja una desviación de 3,9e-6 con media
15.

**Por decisión de la propietaria (opción A) manda la regla del agente:**
- las cuatro distribuciones que leen desviación (`USES_STD_DEV`) la necesitan;
- una Beta o una Gamma sin ella sale de la lista activa, el botón pasa a gris con su motivo y `random_variable_list`
  dice `is_random: false`.

**El rango vacío tiene también un solo umbral, el del cálculo (`high − low > 1e-15`),** por decisión de la propietaria.
El agente pedía `> 0` y aceptaba un rango de 5e-16 que el cálculo dejaba fuera.

**La revisión encontró dos defectos anteriores de la misma regla, y por decisión de la propietaria entran aquí:**
- **otras dos formas de no variar** que la regla llamaba aleatorias:
  - una lognormal, una gamma o una exponencial con media ≤ 0, y el kh, el kv y el desfase del nivel freático tienen
    media 0 por diseño;
  - una desviación que no es un número finito;
- **la corrida deja fuera una variable que no es aleatoria sin decir nada,** y la correlación que otra tenía con ella
  se pierde en silencio.

**Ningún número del banco se mueve.** Medido hoy sobre el árbol de 0.1.452, en los `.ogr` vivos:
- 4 `lognormal` (medias 10 y 30), 22 `normal` y 2 `uniform`, todas con desviación finita y rango;
- la única correlación tiene una pareja aleatoria;
- ningún guion construye una Beta, una Gamma, una exponencial ni una lognormal de media ≤ 0.

Solo se mueve un proyecto que tenga una de esas variables, por las vías que dice §1. Es la vigesimosexta versión de la
tanda P10 y la primera del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.452:** el REPRODÚCELO y los dos grep del banco dan lo de 0.1.435.
- **El agente acepta `none` a propósito:** es como apaga una variable (D413).
  - Por eso la identidad del test no es «el agente rechaza si y solo si `not_random_reason` da un motivo».
  - Es: el agente rechaza si y solo si el motivo es `no_range`, `no_std_dev` o `no_positive_mean`.
- **`not_random_reason` da un solo motivo y el agente da uno por cada condición que falla,** en `details.problems`, que
  no se puede mover.
  - Si el agente preguntara el motivo, perdería mensajes.
  - Por eso el núcleo expone los predicados: `has_range`, `lacks_std_dev` y `lacks_positive_mean`.
  - `not_random_reason` los compone en su orden (`none`, `no_range`, `no_std_dev`, `no_positive_mean`). El agente los
    pregunta uno a uno, con su inglés de siempre. El mensaje nuevo, el de la media, va el último.
- **El conjunto «lee desviación» tenía cuatro copias:**
  - la del cálculo, con dos distribuciones;
  - la de `variable_problems`, con las cuatro;
  - `_USES_STD` del diálogo;
  - y su complemento escrito a mano en la nota «std_dev is not read by a …» del API.

  Ahora es uno, `USES_STD_DEV`, en `ogr_core/statistics/distributions.py`. Queda una mención escrita a mano, correcta:
  la descripción del campo `std_dev` del servidor MCP («normal, lognormal, beta, gamma», `ogr_mcp/server.py:1666-1668`).
  Es texto para el agente y no decide nada.
- **La regla del rango tenía una tercera copia en la sensibilidad** (`sensitivity.py:274`, el mismo 1e-15). Entra en
  esta versión sin mover nada: el `abs` que tenía no hacía nada, porque `high − low` nunca es negativo.
- **El umbral exacto es rango vacío.** Un rango de exactamente 1e-15 (media 0, `rel_min` 1e-15) es vacío, como
  siempre dijo el `<= 1e-15` del cálculo. El primer test no tenía ese caso y un mutante (`>=`) sobrevivía.
- **La revisión adversaria (un agente) no encontró fallos en el código del primer borrador.** Encontró:
  - **(media) un defecto anterior de la misma regla:** media ≤ 0 en las distribuciones de solo valores positivos.
    Entra (§1). Medido con 0.1.452, 200 LHS:

    | distribución | media | rango | muestras | valores distintos |
    |---|---|---|---|---|
    | exponencial | 0 | ±0,1 | 6,7e-16 a 6,0e-12 | 200 |
    | lognormal (desv. 0,05) | 0 | ±0,1 | 3,4e-33 a 7,2e-15 | 200 |
    | lognormal, gamma o exponencial | −5 | ±2 | −5 siempre | 1 |

  - **(baja) una desviación NaN que llega por un `.ogr` contaba como desviación.** Entra (§1). Al medirla salió también
    la infinita. Con 0.1.452, en 20 muestras:
    - la NaN muestreaba NaN en las cuatro;
    - la infinita daba la media siempre con la Normal y la Gamma, NaN con la Lognormal, y solo los dos extremos (12 y
      18) con la Beta.
  - **(baja–media) la correlación con una variable que sale de la lista.** Una variable correlada con una Beta sin
    desviación conserva sus valores y cambia de orden: antes se reordenaba por rangos contra el ruido de los últimos
    dígitos de una constante. El primer borrador decía que las variables de delante no cambiaban, y era falso. La
    correlación se perdía además en silencio, igual que ya pasaba con una pareja Normal sin desviación. Entra (§1).
  - **(baja) la corrida deja fuera sin nota lo que no es aleatorio.** Entra (§1). Medido con 0.1.452 en el talud de
    ejemplo:
    - una cohesión Normal sin desviación junto a un ángulo de rozamiento Normal no dejaba ninguna nota;
    - sola, paraba la corrida con «No random variables defined… must be given a statistical distribution», un motivo
      falso para una Normal que sí tiene distribución.

    El primer borrador de este changelog ponía de ejemplo una Beta sin desviación, que en 0.1.452 era aleatoria y se
    muestreaba. Lo vio la segunda revisión.
  - **Frases falsas, arregladas:**
    - la Gamma no se sujetaba por la desviación sino por la escala;
    - «below this» era «at or below this»;
    - eran cuatro copias, no tres;
    - el test del API leía el texto de la fuente: un mutante con su propia tupla, correcta hoy, sobrevivía, y ahora
      el test cambia la lista del núcleo en memoria;
    - la cabecera decía «sin Qt» e importa el módulo del diálogo.

  Se reporta sin tocar: el rechazo de un rango de 5e-16 dice «rel_min + rel_max must be positive», y 5e-16 es positivo.
  El inglés del agente no se podía mover, y se queda.
- **La segunda revisión adversaria (un agente), sobre lo que entró.** No encontró fallos graves.
  - **(media) las variables aleatorias de detrás se vuelven a sortear.** Una variable que pasa a no ser aleatoria ya
    no gasta su corriente del generador. Medido: la media de FS pasa de 1,093265 a 1,092999, y el PF queda igual por
    casualidad. Es la consecuencia que el prompt daba a la opción A.
    - Hay un precedente contrario: las variables hidráulicas se siguen sorteando para no mover a las demás (D372).
    - Por decisión de la propietaria se queda como está. Sortear también las que no son aleatorias movería todo
      proyecto que tenga hoy una Normal sin desviación, un rango vacío o una `none` delante de otras. Así solo se
      mueve el que tenga una de las variables nuevas, y el banco no tiene ninguna.
  - **(baja) una correlación NaN se reordenaba distinto, en silencio.** El primer borrador escribía la condición del
    muestreador como `>= 1e-12`, que no es la negación de `< 1e-12` con un NaN. 0.1.452 aplicaba la correlación NaN
    (`correlate_pair` la sujeta a 1) y el borrador la saltaba. Ahora la condición es la vieja al pie de la letra, y
    una correlación NaN se aplica bit a bit como antes. Que una correlación NaN valga 1 es anterior y se reporta, sin
    tocarlo.
  - **(baja) un rango o una media NaN pasan a rango vacío.** `has_range` pregunta `> 1e-15`, como la sensibilidad, y
    no `<= 1e-15` como el cálculo, y los dos se separan con un NaN. Con 0.1.452 un `rel_min` NaN muestreaba NaN, y
    ahora da la media. Es una mejora y se queda, dicha en `EMPTY_RANGE` y en este changelog. Solo la trae un `.ogr`
    editado a mano.
  - **(baja, de diseño) una variable apagada a propósito avisaba en cada corrida, en rojo.** La ventana de
    Estadística enseña los avisos como «lo que este cálculo no pudo hacer». Por decisión de la propietaria, una
    variable `none` junto a otras aleatorias se deja fuera sin aviso. Si todas son `none`, el error la nombra.
  - **(baja) tres «; » anidados en la barra de estado.** Los usaban la unión de notas, los grupos y las etiquetas de
    un grupo. Ahora cada grupo va entre paréntesis y los grupos se separan con «, »: «…: sin desviación típica (Silty
    clay — cohesión), con una media … (coeficiente sísmico k_h)». Y la frase ya no dice «variables aleatorias no son
    aleatorias»: «no se pueden muestrear y se han dejado fuera».
  - **(baja) la guía y la tabla de herramientas del agente no lo decían.** `ogr_mcp/guide.py` y
    `docs/mcp/herramientas.md` dicen ahora qué distribuciones necesitan desviación y media positiva, y los tres
    códigos nuevos.
  - **(baja) huecos del test.** `test_the_rule_is_the_samplers` no corría el muestreador. Ahora lo corre, con una
    pareja aleatoria y otra que no lo es, con correlaciones de 0,5, 1e-13, 0 y NaN. Añade además una variable no
    aleatoria que declara una correlación con una pareja que tampoco se muestrea. Ese caso mata un mutante que
    sobrevivía.
  - **Frases y detalles:**
    - la exponencial se sujeta en `cdf` y `ppf`, no en `_frozen`;
    - el docstring de v1435 decía «tres condiciones».

  Se reporta sin tocar:
  - un mensaje del agente con una desviación infinita diría «needs a positive std_dev», y el infinito es positivo.
    El agente no deja enviar infinitos, y el mensaje no se mueve;
  - `stat.vars_not_random` cuenta su total sobre las variables declaradas, y `stat.vars_hydraulic` sobre las
    muestreadas;
  - con todas las variables fuera, la puerta sigue corriendo la búsqueda determinista entera antes de negarse
    (anterior).
- **Una guarda del test se tragaba un fallo.** El caso del texto del diálogo importaba la función dentro de un
  `except ImportError`, pensado para cuando no hay PySide6. En el árbol de 0.1.452 la función no existe, y el caso
  pasaba como «sin PySide6». Ahora pregunta antes si PySide6 está, y la importa sin guarda.
- **Fuera de esta versión, medido: la sensibilidad barre una variable con distribución `none`.** En el talud de
  ejemplo, con la cohesión en `none` y un rango de ±2, barre de 8 a 12 kPa (factores 1,0458 a 1,2097) sin ninguna
  nota. No se sabe todavía si la referencia lo hace: su sensibilidad lee solo el mínimo y el máximo. Va a una ficha
  nueva, sin tocar. Tampoco dice nada cuando deja fuera una variable sin rango, que es su regla propia: va a la misma
  ficha.

## 1. Qué cambia

- **`ogr_core/statistics/distributions.py`:**
  - `USES_STD_DEV` = {Normal, Lognormal, Beta, Gamma}, `POSITIVE_ONLY` = {Lognormal, Gamma, Exponencial} y
    `EMPTY_RANGE` = 1e-15;
  - las propiedades `has_range`, `lacks_std_dev` (sin desviación, o con una que no es un número finito) y
    `lacks_positive_mean`;
  - `not_random_reason` las compone y da `no_std_dev` también a la Beta y a la Gamma, y `no_positive_mean`.
- **`ogr_core/statistics/random_variables.py`:**
  - `variable_problems`: los mensajes de desviación y de rango salen de los predicados del núcleo, con su inglés de
    siempre, y uno nuevo de la media va el último («A lognormal distribution takes only positive values; with a mean of
    0 the variable is not random.»). Una variable sin distribución se sigue aceptando;
  - `unapplied_correlations`: las correlaciones que el muestreador declara y no aplica, con sus mismas condiciones
    (`_declares_correlation`, la condición vieja al pie de la letra).
- **`ogr_slip2d/probabilistic.py`, `_sampled_variables`:** la preguntan Global Minimum y Overall Slope.
  - Sin variables: `stat.no_variables`, como siempre.
  - Ninguna aleatoria: un error, `stat.vars_not_random_only`, con cada variable y su motivo.
  - Algunas: un aviso, `stat.vars_not_random`, con las que se dejan fuera agrupadas por motivo en el orden del núcleo,
    cada grupo entre paréntesis. Una variable `none` junto a otras aleatorias se deja fuera sin aviso (decisión de la
    propietaria).
  - Una correlación cuya pareja no se muestrea: un aviso cada una, `stat.correlation_not_applied`.
  - Siete códigos nuevos en `ogr_slip2d/stat_messages.py`, con su castellano. Las variables se nombran por su clave
    para el agente y por su etiqueta en la ventana (`variable_keys`).
- **`ogr_slip2d/sensitivity.py`:** las variables que se barren son las de `has_range`.
- **`ogr_mcp/guide.py` y `docs/mcp/herramientas.md`:** qué distribuciones necesitan desviación y media positiva, que
  el kh y el kv tienen media 0, y los tres códigos que el agente puede leer.
- **`ogr_api/ops/statistics.py`:** la nota «std_dev is not read by a …» pregunta `USES_STD_DEV`.
- **`ogr_gui/dialogs/random_variables_dialog.py`:**
  - el campo de la desviación lee `USES_STD_DEV`;
  - los motivos del botón en gris pasan a una función del módulo, `not_random_text`;
  - el de la desviación pasa de «A normal or lognormal distribution needs a standard deviation greater than zero.» a
    «This distribution needs a standard deviation greater than zero.» («Esta distribución necesita una desviación
    típica mayor que cero.»). El texto viejo nombraba dos de las cuatro;
  - y el nuevo de la media: «This distribution takes only positive values, and the mean is not positive: choose
    another distribution.» («Esta distribución solo toma valores positivos, y la media no es positiva: elige otra
    distribución.»). La media es el valor del modelo, así que lo que se puede cambiar es la distribución.
- **Lo que mueve, a propósito:** una variable que no es aleatoria sale de la lista activa.
  - Si es la única, el análisis para con su motivo.
  - Si hay otras, cambian las muestras de las que van detrás: `sample_variables` gasta una corriente del generador
    por variable, en el orden de la lista.
  - Una variable correlada con ella conserva sus valores y cambia de orden, esté donde esté en la lista. Con una
    tercera variable cambia con quién se empareja cada muestra, así que el PF se puede mover.
  - Sus propias muestras eran ya (casi) la media, o NaN.

## 2. Qué se probó

- **`tests/test_random_variable_rule_v1453.py`** (24 casos, sin `QApplication`, unos 2 s en el runner, casi todo
  imports).
  - **La referencia son identidades de las distribuciones:**
    - con desviación 0, la Beta y la Gamma son la masa puntual en su media;
    - una distribución de solo valores positivos tiene media positiva.
  - **Las medidas de 0.1.452 salen del propio código:**
    - la Beta y la Gamma con desviación 1e-12, que el núcleo muestrea todavía y pasa por las mismas guardas, dan los
      mismos números;
    - las medias ≤ 0 y las desviaciones no finitas, muestreadas con la regla de 0.1.452 sustituida en el mismo proceso,
      dan lo medido.
  - **La identidad:** para las ocho distribuciones, con medias 10, 0 y −5, desviaciones −1, 0, 1, NaN e ∞ y tres rangos,
    el agente rechaza por aleatoriedad si y solo si el cálculo no la muestrea.
  - Cada mensaje del agente es un predicado del núcleo, y cuando fallan todas las condiciones sale un mensaje por cada
    una, en su orden.
  - **Las muestras:**
    - con desviación no se mueven, bit a bit, frente a la regla de 0.1.452 sustituida en el mismo proceso;
    - sin ella, la variable de detrás se muestrea como si la otra no estuviera;
    - una variable correlada con ella conserva sus valores y pierde el orden de 0.1.452.
  - **La corrida dice lo que deja fuera,** igual en Global Minimum y en Overall Slope:
    - sola, una Beta sin desviación para los dos con `stat.vars_not_random_only` y su motivo;
    - sin variables, `stat.no_variables`;
    - cuatro variables fuera, una por motivo, dadas en otro orden: tres salen en el orden del núcleo, y la `none`, sin
      nombrar;
    - una `none` junto a otra aleatoria no deja nota, y sola la nombra el error;
    - la correlación con una pareja que no es aleatoria, o que no está definida, se dice, y con una pareja aleatoria
      no;
    - `unapplied_correlations` nombra justo los pares que el muestreador declara y no reordena, medido corriéndolo:
      una correlación de 1e-13 no cuenta, una NaN se aplica como en 0.1.452 bit a bit, y una variable no aleatoria no
      declara nada;
    - y todo en castellano.
  - Un rango o una media NaN son rango vacío (0.1.452 muestreaba NaN).
  - El rango de 5e-16 y el de 1e-15 son vacíos para el cálculo, el agente y la sensibilidad; el de 2e-15, para ninguno.
  - **Por el agente:**
    - `random_variable_set` rechaza una Beta y una Gamma sin desviación, y una lognormal y una exponencial en el kh
      (media 0);
    - una variable que llega por un archivo sale con `is_random: false`;
    - la nota de la desviación dice las mismas cuatro (control).
  - **Una sola lista:** el diálogo y el agente preguntan la del núcleo; la del agente, por lo que dice con la lista
    cambiada en memoria.
  - El texto del botón para cada motivo del núcleo, en castellano.
- **Cambian a propósito:**
  - `tests/test_interpret_charts_v1435.py`: la tabla de `test_the_reason_is_the_rule_of_is_random` (la Beta y la Gamma
    con desviación ≤ 0 pasan a `no_std_dev`) y el texto de `test_the_button_says_why`;
  - `tests/test_stat_notes_v1353.py`: las muestras de los siete códigos nuevos en `_LATER`, y `_sampled_variables` en
    su censo `_CODED`.
- **Discriminación:** en el árbol de 0.1.452, sin el buscador editable, fallan 21 de los 24 casos.
  - 12 fallan por lo que hacen: la identidad, el rechazo por cada condición, el agente con el kh, las medias ≤ 0, las
    desviaciones no finitas, el rango NaN, la masa puntual, el rango de 5e-16, el castellano de la corrida, el aviso de
    lo que deja fuera, las muestras de detrás y la correlación.
  - 9 fallan por los nombres nuevos.
  - Pasan los tres controles: la medida de la masa puntual, la nota de la desviación y `stat.no_variables`.
- **Mutantes** (`mutants_d416.py`, en el banco): 36, todos muertos (los cinco últimos, de la segunda revisión: la
  correlación NaN saltada, la variable no muestreada que dice su correlación, la `none` nombrada entre otras o no
  nombrada sola, y el rango NaN de 0.1.452).
  - Las listas:
    - sin la Beta, sin la Gamma, la de 0.1.452, y la positiva sin la exponencial;
    - la nota del API escrita a mano sin la Beta, o con su complemento correcto (sobrevivía al primer test);
    - la copia propia del diálogo.
  - El umbral: a 0, `has_range` con `>=` (sobrevivía al primer test).
  - La desviación: 0 cuenta, NaN cuenta (0.1.452), ∞ cuenta (sobrevivió al primer test ampliado y trajo su caso).
  - La media: 0 cuenta como positiva.
  - El motivo: sin la desviación, sin la media, con su copia de dos distribuciones, con su rango a 0, o con los motivos
    cambiados de orden.
  - El agente: con su propia copia, con su rango de 0.1.452, preguntando solo el primer motivo, u olvidando la media.
  - La sensibilidad con su rango a 0.
  - El diálogo sin el texto de la media.
  - La corrida:
    - sin el aviso, o con `stat.no_variables` cuando ninguna es aleatoria;
    - con los motivos en el orden de las variables;
    - sin las correlaciones, o sin la de una pareja no definida;
    - con cualquier correlación;
    - Overall Slope con su propia lista de 0.1.452.
- **Vecinos**, con los patrones `random_variable_rule stat_notes edit_messages spanish_paths core_messages
  hydraulic_variables interpret_charts f3b_ops random_variables_v134 probabilistic statistics sensitivity
  i18n_coverage mcp_server mcp_transports model_notes cli_reported_caption focus_all_searches` (cada uno comprobado con
  `--list`): 545 casos en verde.
- **La suite entera** con `--jobs 4`:
  - la del primer borrador: 7688 casos, 7687 en verde, 0 fallos y 1 omitido, sin fugas ni tramos muertos;
  - tras lo que entró por la primera revisión: 7697 casos, 7696 en verde, 0 fallos y 1 omitido;
  - tras la segunda, el árbol de este commit: **7699 casos, 7698 en verde, 0 fallos y 1 omitido**, sin fugas ni tramos
    muertos. La serie no toca (31 commits desde la última).

  Fueron tres corridas porque el código cambió dos veces después de una en verde. La segunda se podía haber ahorrado:
  se lanzó antes de la segunda revisión, que traía cambios.

## 3. Qué queda

- La ficha nueva de la sensibilidad (§0): barre una variable `none` y deja fuera sin nota una variable sin rango. Hay
  que medirla contra la ayuda de la referencia.
- Las correlaciones con una pareja que no se muestrea se dicen, pero no se rechazan al guardarlas: el agente ya rechaza
  una pareja no definida, y una pareja definida que deja de ser aleatoria se dice al calcular.
- En el plan del 2026-11-14 siguen D417 (0.1.454), D410, D425 y D426.
