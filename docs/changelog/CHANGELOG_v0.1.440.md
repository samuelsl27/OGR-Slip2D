# OGR Slip2D v0.1.440

**El retroanálisis de Interpretar lee la corrida sobre la que se abrió (D419).** Tasaba la superficie crítica con las
dovelas de la corrida, pero con el sismo y los soportes del proyecto **como estaba en ese momento**, y sin el
coeficiente sísmico de la norma que la corrida sí había aplicado. Medido con 0.1.439 sobre una rejilla de 64 círculos
del talud de ejemplo (Janbu, objetivo 1,5, cota 20; `medir_d419.py` del banco), en kN/m:

| caso | con los datos de la corrida | lo que publicaba Interpretar |
|---|---|---|
| nada cambia, sin sismo ni norma | 145,99 | 145,99 |
| kh de 0 a 0,1 tras calcular | 145,99 | 258,49 (+77 %) |
| kh 0,1 al calcular, sismo apagado después | 258,49 | 145,99 (−44 %) |
| un bulón añadido tras calcular | 145,99 | 36,42 (−75 %) |
| norma con coeficiente sísmico 1,5 y kh 0,1, **sin cambiar nada** | 314,73 | 258,49 (−18 %) |

Ahora:

- **kh y kv salen de la corrida:** los que el método aplicó (`details["kh"]` y `["kv"]`, con el coeficiente de la norma
  ya dentro), como el diagrama de cuerpo libre desde D173. Con la norma de coeficiente sísmico 1,5 la ventana publica
  314,73 kN/m (Bishop: 296,87), los de la corrida.
- **Con el modelo cambiado desde la corrida, el retroanálisis se niega antes de preguntar nada** (decisión de la
  propietaria): «Resultados de un modelo anterior: vuelve a calcular.», la frase del panel de Resultados (D304). Un
  resultado no guarda los soportes con que se calculó, así que la ventana no puede tasarlo contra otro modelo.
- **Interpretar marca el resultado viejo** (decisión de la propietaria): la misma banda del panel de Resultados, en lo
  alto de su panel de resumen, y «Retroanálisis...» en gris con ese motivo en la barra de estado. Al deshacer el cambio,
  las dos cosas se van. Las demás entradas no cambian.
- **Optimizar superficies se niega sobre el resultado de un modelo anterior**, con la misma frase y antes de preguntar
  nada (decisión de la propietaria en la revisión). Es un defecto anterior que dejaba abierto un camino al de D419: ver
  §0.
- **Una edición del agente marca también el resultado viejo**, aunque no notifique nada al proyecto (decisión de la
  propietaria en la revisión).
- **Sin cambios tras calcular, sin sismo y sin soportes, la ventana dice lo mismo que en 0.1.439, byte a byte.**

Es la decimotercera versión de la tanda P10.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.439 (38f0cae):** `medir_d419.py` da la tabla de arriba, y al final «Interpretar se abre sobre
  él: True; lo marca: False; «Back Analysis...» activo: True».
- **La referencia es una identidad, no una captura** (Bishop 1955; Janbu 1954; la de D210): con el objetivo igual al
  factor de la superficie y los datos con que se calculó, la fuerza es 0.
  - Se mide **sin recortar**: `required_force` da 0 por una fuerza negativa, y eso esconde la mitad del lado inseguro.
    En el caso de la norma, la ventana publicaba «activa 0,00, pasiva 0,00» en el propio factor de la crítica, con una
    fuerza de −0,044 veces el peso de la masa debajo.
  - Se mide sobre corridas resueltas a 1e-12: con la tolerancia por defecto (0,005), la fuerza «nula» de la propia
    corrida sale entre 5,9e-6 y 7,4e-4 del peso y la identidad no resuelve nada.
  - «Activa igual a pasiva con objetivo 1,0» no sirve aquí: con F = 1 las dos fórmulas son la misma suma, y se cumple
    con cualquier dato.
- **Qué lee del proyecto la cuenta, además de las dovelas:** los soportes (`resolve_support_terms`), y a través de un
  soporte lo que ese soporte lea del modelo. La adherencia de un geosintético en modo «coeficiente» es una fracción de
  la resistencia del suelo que lo rodea (Jewell 1996): con una norma que factoriza esa resistencia, el mismo
  geosintético aguanta menos en la copia factorizada.
  - Medido: con Eurocódigo 7 DA1-C2 y ese geosintético, la identidad sale 3e-14 del peso con la copia factorizada y
    −0,044 con el proyecto tal como está dibujado.
  - Lo encontró un mutante que sobrevivía (pasar el proyecto en vez de la copia factorizada): ningún caso del test
    dependía de qué modelo se entregaba. Ahora hay una corrida con ese geosintético.
  - Por eso la ventana sigue reconstruyendo el modelo analizado con `prepare_analysis_project`, y por eso tiene que
    saber que el modelo no ha cambiado.
- **El comentario de `AnalysisOutcome.project` era falso sin norma.** Decía «never the caller's project». Sin norma ni
  enlaces de material, `prepare_analysis_project` devuelve el mismo objeto, así que es el proyecto de quien llama, y
  una edición posterior se ve en él. Quien lo hubiera tomado por «el modelo de la corrida» habría leído el de ahora.
  Corregido.
- **Un test que el prompt daba por intocable cambiaba el modelo después de construir la ventana.**
  `test_the_back_analysis_names_its_target` (`tests/test_interpret_charts_v1435.py`) construía la ventana sin norma,
  ponía la norma en su proyecto y pedía el retroanálisis. Eso es un modelo cambiado desde la corrida, justo lo que
  ahora se niega. Lo que el test prueba (el objetivo se nombra por el informe de la corrida, no por la norma del
  proyecto) sigue en pie: la ventana se construye después de poner la norma. Sus asertos no cambian.
- **Una rama que nada distinguía.** La primera versión de la función nueva materializaba las dovelas volcadas a disco,
  como hace `run_back_analysis`. Su mutante sobrevivía: `required_force` ya las lee al recorrerlas. La rama se quitó,
  y queda el test de que un resultado con las dovelas en disco da la misma fuerza.
- **Comparar al último bit entre máquinas no vale.** Los literales de `_V1439` se midieron en esta máquina y la suite
  corre también en la CI, con otra libm. Las fuerzas medidas en 0.1.439 se comparan a 1e-9; al último bit solo se
  comparan dos valores calculados en el mismo proceso (lo que publica la ventana y `required_force` con los datos de
  la corrida).

### La revisión adversaria (dos agentes, 12 hallazgos, ninguno refutado)

Dos de severidad media, los dos anteriores a esta versión, y diez bajos. Dos de los bajos se quedan como están, y se
dicen: el test abre nueve ventanas principales donde alguna podría compartirse (medido: 7 s el archivo entero, 2,3 s
el caso más caro), y la rama con norma de `test_the_back_analysis_names_its_target` usa una ventana hecha a mano con
un informe de norma sobre un proyecto sin ella, que por la ventana principal ya no puede darse.

- **Optimizar superficies re-sellaba la huella del resultado entero** (anterior, de 0.1.366; media). Medido antes de
  tocarlo: se calcula con Janbu y Bishop, se añade un bulón (el panel dice «Resultados de un modelo anterior»), se
  optimiza la superficie de Bishop, y el panel deja de marcarlo. Interpretar daba entonces por actuales los resultados
  de Janbu, que son de antes del bulón, y su retroanálisis no se negaba: el defecto de D419 por otra puerta.
  - La causa: Optimizar parte de la crítica de la corrida anterior, toma la huella del modelo de ese momento y la pone
    sobre todo `last_search_results`, también sobre los métodos que no ha tocado.
  - **Decisión de la propietaria:** Optimizar se niega sobre un resultado viejo, antes de preguntar nada. Con el
    modelo cambiado, la superficie de la que parte y el resto de la población son de otro modelo.
- **Una edición del agente que no notifica** (un ajuste, `settings_set`) llegaba a la ventana solo por
  `after_edit`, que no arrancaba la comprobación: el panel de Resultados y la banda nueva se quedaban sin marcar hasta
  el siguiente evento del proyecto (anterior, de D304; baja). Al pulsar, el retroanálisis sí se negaba. **Decisión de
  la propietaria:** se arregla aquí.
- **Con abatimiento rápido, el modelo que se entrega no es el de las dovelas** (anterior, de D210; leído, **sin
  medir**). Las dovelas que publica la corrida salen del modelo con el nivel abatido, y el retroanálisis, el de la
  corrida y el de Interpretar, entrega el proyecto sin abatir. Un soporte que lea el agua del suelo la leería del
  nivel inicial. **Decisión de la propietaria:** ficha nueva con su medida (D432). El docstring de la función nueva ya
  no dice que la copia sea siempre la de la corrida.
- **Del propio cambio, arreglados:**
  - la comprobación iba antes de los dos diálogos y la cuenta después: una edición del agente con un diálogo abierto
    entraba en la cuenta. Se pregunta otra vez con las respuestas en la mano, y el modelo analizado se reconstruye
    entonces;
  - un modelo que no se puede leer en el momento de comparar se daba por «anterior»; ahora la ventana dice que no
    puede saberlo, como la que no tiene huella;
  - la huella se calculaba dos veces al abrir;
  - el docstring decía que del proyecto «solo se leen los soportes».
- **Del test, arreglados:** un caso que no probaba lo que decía su nombre (ahora construye la ventana), tres asertos
  que comparaban dos literales del propio archivo, entradas de `_V1439` que no se comparaban con nada calculado, y una
  edición que podía quedarse a medias sobre el proyecto compartido.
- **Sin hallazgo:** los `details` de todo resultado válido de los tres métodos, el signo de kv, Ky y Newmark, la
  huella al empezar la corrida, abrir y deshacer, las ventanas cerradas y el cambio de idioma.

### Otras entradas de Interpretar que leen el modelo de ahora

Por decisión de la propietaria solo el retroanálisis se pone en gris. Se reporta lo que queda:

- *Análisis de fuerzas de soporte* y *Diagrama de fuerzas de soporte* leen `self.project.supports`: con un soporte
  añadido o cambiado después de calcular, enseñan los de ahora junto al factor de la corrida;
- las dos se activan según haya soportes en el modelo al abrir la ventana.

## 1. Qué cambia

- **Núcleo** (`ogr_slip2d/back_analysis.py`): `required_force_of_result(result, target_fos, elevation, project,
  method_id=None)`. Lee del resultado las dovelas, la superficie, el método y los coeficientes sísmicos aplicados, y
  llama a `required_force`. `required_force`, `run_back_analysis` y el retroanálisis del agente no cambian.
- **Interpretar** (`ogr_gui/interpret_window.py`):
  - el constructor recibe `model_fingerprint`, la huella de D304 del modelo de su corrida. Sin ella (una ventana
    construida a mano, como hacen los tests) toma la del modelo al construirse;
  - `results_are_current()` la compara con el modelo de ahora, y `refresh_stale()` pone o quita la banda y el gris;
  - `_back_analysis_report` pregunta si el modelo es el de la corrida antes de sus dos diálogos y otra vez después,
    y llama a la función del núcleo. Ya no lee `project.seismic`.
- **Ventana principal** (`ogr_gui/main_window.py`):
  - `act_interpret` entrega la huella del modelo cuando empezó la corrida;
  - `_check_results_stale` avisa también a cada Interpretar abierta, cada una contra su propia huella: la que se abrió
    antes del último cálculo conserva la del anterior, y la de un proyecto anterior se pregunta por el suyo;
  - `_schedule_stale_check` arranca la comprobación también cuando solo hay ventanas de Interpretar abiertas, y la
    llama el puente del agente (`ogr_gui/agent_bridge.py`) tras cada edición;
  - `_optimize_surfaces` se niega si el modelo ya no es el de los resultados. Los resultados puestos a mano, sin
    huella, no se niegan.
- **Lo que no cambia para el agente:** nada. `back_analysis_run` y `optimize_run` no pasan por la ventana.

## 2. Qué se probó

- **`tests/test_interpret_back_analysis_v1440.py`** (23 casos):
  - la identidad sin recortar, a 1e-9 del peso, con el sismo subido o apagado en el proyecto después de la corrida
    (kh y kv), con la norma de coeficiente sísmico 1,5 y con el geosintético bajo Eurocódigo 7 DA1-C2;
  - la ventana se niega con cada cambio (kh subido, sismo apagado, bulón añadido), sin abrir ningún diálogo ni llamar
    a `required_force`, con la huella de la corrida y con la que toma al construirse, y lo dice en castellano; también
    con el modelo editado mientras el segundo diálogo está abierto;
  - con la norma publica, al último bit, `required_force` con los datos de la corrida (314,73 y 296,87 kN/m);
  - sin cambios, el mensaje de 0.1.439 byte a byte (145,99 y 136,95 kN/m);
  - la banda y el gris: aparecen con el cambio y se van al deshacerlo, en los dos idiomas; una ventana abierta sobre
    un resultado ya viejo nace marcada; cada ventana guarda la huella de su corrida; una ventana de otro proyecto no
    se marca por una edición del nuevo;
  - Optimizar se niega con el modelo cambiado, en los dos idiomas, sin abrir sus diálogos y sin tocar los resultados
    ni la huella; con el modelo como estaba, sigue hasta la pregunta del motor; y una edición del agente arranca la
    comprobación.
- **La referencia `_V1439`** se midió ejecutando el `_capture()` del propio test sobre el árbol de 0.1.439
  (`capture_d419.py`, en el banco): 6 entradas, iguales en dos capturas.
- **Discriminación:** en el árbol de 0.1.439, sin el buscador editable, fallan 20 de los 23 casos. Por lo que miden:
  la ventana publica 258,49 donde debe negarse, y −0,044 del peso en la identidad. Pasan los tres controles (el
  mensaje sin cambios, que los casos son los que dicen ser, y que un resultado sin huella no se niega).
- **Mutantes** (`mutants_d419.py`, en el banco): 27, todos muertos. Dos sobrevivieron en la primera pasada y están
  contados arriba (la rama redundante y el modelo factorizado).
- **Tests que cambian a propósito:**
  - `tests/test_back_analysis_loads_v1220.py`: el AST exige ahora una sola llamada a `required_force_of_result` con
    `project=`, y sigue exigiendo `prepare_analysis_project`;
  - `tests/test_interpret_charts_v1435.py`: la preparación de `test_the_back_analysis_names_its_target`;
  - `tests/test_seepage_run_notes_v1352.py`: la función nueva entra en el censo de frases sin código.
- **Medido a mano y sin test propio:** Janbu corregido en la ventana, con kh 0,1, kv 0,05 y la norma de coeficiente
  sísmico 1,5. La ventana pasa kh 0,15 y kv 0,075, los aplicados, y la identidad sin recortar da 0 del peso.
- **`medir_d419.py` con el árbol nuevo:** los seis casos con el modelo cambiado, «Interpretar SE NIEGA»; el control,
  145,99 y 136,95; la norma sin cambios, 314,73 y 296,87 con la identidad en 1,5e-16 y 9,8e-14 del peso; y al final
  «lo marca: True; «Back Analysis...» activo: False». El guion se adaptó para imprimir la negativa.
- **Banco:** `d419()` da SIGUE ABIERTO con el árbol de 0.1.439 (+0,11 y −0,044 del peso) y CUBIERTO POR TEST con el
  nuevo; `d413()`, que abre la misma ventana, sigue cerrando.
- **La suite entera** con `--jobs 4`, dos veces: antes de la revisión, 7444 casos, 7443 en verde y 1 omitido; con el
  árbol final, **7448 casos, 7447 en verde, 0 fallos y 1 omitido**, sin fugas ni tramos muertos. La serie no toca (18
  commits desde la última).

## 3. Qué queda

- **D432, nueva** (al final de P10, sin versión): con abatimiento rápido, el retroanálisis entrega el proyecto sin
  abatir junto a las dovelas del nivel abatido. Leído y sin medir; pide un caso con un soporte que lea el suelo. El
  ángulo de la fuerza del retroanálisis, que el plan llamaba D432, pasa a ser D433 cuando se abra con D418.
- **Las dos entradas de soportes de Interpretar** siguen leyendo el modelo de ahora (arriba). Sin ficha.
- **A mano, por la propietaria:** calcular, abrir Interpretar y cambiar kh en el modelo: la banda, «Retroanálisis...»
  en gris con su motivo en la barra de estado, y al deshacer vuelven. Y Optimizar superficies tras editar el modelo.
- **Fichas que siguen en P10:** D418 (0.1.441), D400 (0.1.442), D401 (0.1.443) y D402 (0.1.444).
