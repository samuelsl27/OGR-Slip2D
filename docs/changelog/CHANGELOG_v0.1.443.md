# OGR Slip2D v0.1.443

**El panel de resultados e Interpretar enseñan la superficie crítica que dibujó el usuario y dicen de quién es, y el
retroanálisis de Interpretar dice qué superficie tasa (D401).** Las dos ventanas miraban solo la población de la
búsqueda. Medido con 0.1.442 sobre el talud de ejemplo (Janbu, Path de 5 más la polilínea `_WINNER`, F = 1,1232):

| caso | 0.1.442 | ahora |
|---|---|---|
| un foco rechaza toda la búsqueda y la polilínea del usuario es la crítica: el panel | «No results yet.» | «… Valid: 0 … Critical FoS: 1.123 (surface defined by the user)» |
| el resumen de Interpretar | «No results to display.» | «Critical surface, defined by the user» y 1.123 |
| la Tabla de resultados, el CSV y el filtro | «No valid surfaces.» y un CSV sin filas | la llevan, marcada; el filtro, «1 de 1» |
| sin el foco: el panel y Superficies de Interpretar | la listaban sin decir de quién es | «Defined by the user» en la columna Nota |
| sin el foco: la Tabla de resultados y el CSV | las 5 de la búsqueda, sin ella | las 6, y la suya marcada |
| sin el foco: el filtro, con todas las superficies dibujadas | «Showing 6 of 5 surfaces.» | «6 of 6» |
| el retroanálisis de Interpretar | la fuerza, sin decir sobre qué superficie | una línea más: «Back-analysed on the critical surface of the run (Janbu Simplified).» |

Decisiones de la propietaria (2026-11-12): el rótulo del retroanálisis es el de la ficha, y la fila del usuario se marca
en la columna Nota, delante del motivo de inadmisible si lo hay.

Es la decimosexta versión de la tanda P10. **Ningún factor ni ninguna fuerza cambia:** el rótulo dice qué superficie
se tasó, no cambia cuál se tasa.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.442 (b5a4d27):** el fragmento del prompt da lo que dice la ficha. Con el foco: `busqueda 0
  usuario 1`, «No results yet.», «No results to display.», «No valid surfaces.». Con la rejilla de 64 círculos y un
  círculo del usuario que no es el crítico: la corrida publica 166,33 kN/m sobre el círculo del usuario (F = 1,2869) e
  Interpretar 145,99 sobre el crítico de la rejilla (F = 1,1461), sin decir cuál tasó.
- **«Corrida» es una forma retirada del castellano de la interfaz** desde 0.1.325
  (`tests/test_voice_and_terms_v1325.py`: «corrida» → «cálculo»), y el texto que se decidió para el rótulo la llevaba:
  «Retroanálisis sobre la superficie crítica de la corrida ({0}).». El test de términos lo paró. Queda **«… sobre la
  superficie crítica del cálculo ({0}).»**, con la forma vigente; el inglés es el decidido. La propietaria lo
  confirmó en el resumen de la versión (2026-11-13).
- **Los contadores siguen siendo los de la búsqueda** (D58): con el foco, «Valid: 0» junto a un factor crítico de
  1,123. Por eso la crítica del usuario se rotula: el número de al lado no es uno de los contados.
- **La Tabla de resultados no tenía columna Nota.** Lleva ahora las superficies del usuario, y para que una fila
  diga de quién es se le añade una sexta columna, **solo cuando la corrida analizó alguna** (la regla de la columna
  `user_defined` de 0.1.442). No estaba en el plan con ese detalle; la propietaria lo confirmó en el resumen de la
  versión. Sin superficies del usuario, sus cinco columnas.
- **Reportado y sin tocar** (regla 6), todo anterior a esta versión salvo donde se dice:
  - **la escala de la leyenda y el mapa de colores no leen la misma lista.** La escala y la leyenda se ajustan a los
    factores de la búsqueda; el mapa de colores del lienzo pinta el mínimo por centro de `valid()`, que incluye los
    círculos del usuario (medido: 17 celdas con el círculo del usuario, 16 sin él). Consecuencias medidas: con el
    rango automático la escala va de 1,3094 a 1,4360 y la marca de la crítica del usuario (1,1232) cae fuera (con la
    escala por defecto, de 0 a 6, cae dentro); y con un foco que vacía la búsqueda no hay leyenda, aunque el mapa
    pinte los círculos del usuario;
  - **la Tabla de resultados numera sus filas desde 0 y ordena la columna «#» como texto** (9, 8, 7, 6, 51, 50, 5…).
    Las otras dos tablas numeran desde 1. Quien lo arregle tendrá que volver a medir `_V1442` del test nuevo, que
    fija esas tres primeras filas y su numeración;
  - **el CSV ordena por factor sin mirar si la superficie es admisible.** Con la polilínea del usuario que m-alfa
    rechaza (F = 0,223), esa fila sale con el rango 1, por delante de la crítica (1,1789), y el archivo no tiene
    columna de admisibilidad. Ya pasaba con las rechazadas de la búsqueda; con las del usuario dentro se ve más;
  - **el histograma, la dispersión y la curva acumulada** son de la búsqueda (abajo). Con la búsqueda vacía y la
    crítica del usuario, las dos primeras dicen «No valid surfaces.», que no es cierto de la corrida, y la tercera
    no dice nada;
  - **el máximo que propone el filtro se redondea a tres decimales** (1,436 por 1,436030) y deja fuera la superficie
    más alta: recién abierto dice «Showing 5 of 6 surfaces.»;
  - **el resumen de inválidas dice «Every surface evaluated successfully.»** sobre la rejilla de 64 círculos, con 12
    descartados antes de rebanar: ninguno lleva motivo;
  - **Interpretar tasa la crítica y la corrida la que más fuerza necesita.** Es así por diseño, y es justo lo que el
    rótulo nuevo hace visible;
  - **el informe PDF** imprime la crítica del usuario bajo «Global Minimums» sin decir de quién es. Es D404.
- **Dos casos límite que cambian de frase y no quedan bien del todo** (medidos con una evaluación de sustitución):
  - si la única superficie analizada es del usuario y **no tiene factor**, el panel dice «No valid surfaces found
    (27 invalid).» y el resumen «No valid surfaces (27 invalid)». Con 0.1.442 decían «No results yet.». La frase
    nueva es la cierta (la corrida analizó una superficie y no es válida), pero el recuento es el de la búsqueda y no
    la cuenta a ella;
  - si es válida pero **no tiene Ky** en una corrida Ky, el resumen dice «No valid surfaces», y no la frase de «N
    superficies válidas, ninguna con coeficiente sísmico crítico», porque esa rama mira el recuento de la búsqueda.
- **D-D, documentado y sin cambiar:** la dispersión, el histograma y la curva acumulada describen cómo se reparten
  los factores de una búsqueda, y siguen siendo solo de ella. Lo dicen ahora sus docstrings.

### La revisión

`/revisar` y la revisión adversaria (dos agentes; uno el código, otro el test y el changelog). **Ningún defecto
grave.** El primero midió «sin superficies del usuario, nada cambia» con un A/B contra 0.1.442 en 7 casos y dos
idiomas (rejilla, dos métodos, Path, Eurocódigo 7 DA1-C2, Ky, y las dos búsquedas vaciadas por el foco): solo
cambia la línea del retroanálisis; y las fuerzas activa y pasiva son idénticas en los 15 casos que dan una. Lo que
encontraron, y lo que se hizo:

- **Tres frases mías decían que los contornos son solo de la búsqueda.** No es cierto del mapa de colores (arriba).
  Se corrigieron los dos docstrings y este changelog; el comportamiento no se toca.
- **La columna Nota de la Tabla de resultados no pasaba por `surface_note`:** de la superficie del usuario que m-alfa
  rechaza decía solo «Defined by the user», y las otras dos tablas, además, el motivo. Pasa ya por la misma función,
  con su ayuda emergente.
- **El filtro sí se podía medir** (tres tests ya sustituían `QDialog.exec`). Mi test solo leía el código, y el
  revisor escribió tres versiones defectuosas que lo pasaban. Ahora se abre el diálogo con su `exec` sustituido y se
  lee la M de «Showing N of M».
- **Sobrevivían 17 mutantes del revisor.** Las reglas que no tenían caso, y lo tienen:
  - la etiqueta es de la crítica, no de la corrida: con un círculo del usuario que no es el crítico, ni la cabecera
    ni el resumen dicen «del usuario»;
  - la fila del usuario se marca aunque no sea la crítica ni esté entre las primeras;
  - cada fila del CSV y de la Tabla de resultados, entera, y no tres de sus celdas;
  - la columna aparece también cuando la única superficie del usuario no es válida;
  - toda la fila rechazada va en gris, y ninguna otra; el castellano de la línea del retroanálisis, leído de la
    ventana; la identidad en la ventana; y la superficie sin factor, que no es «sin resultados».
- **El ayudante del CSV de mi test podía colgar la suite:** el camino de error de la exportación es un cuadro modal,
  y no lo sustituía. Ahora un fallo ahí falla el test.
- **Camino equivocado:** para no dejar cuatro ventanas de Interpretar abiertas probé a cerrarlas nada más
  construirlas. Pedirle algo después a una ventana cerrada colgó la corrida. Se quedan sin cerrar (nunca se
  muestran), como estaban.

## 1. Qué cambia

- **Las guardas** del panel (`ogr_gui/widgets/results_dock.py`) y del resumen de Interpretar
  (`ogr_gui/interpret_window.py`) leen `all_evaluations_of`: hay resultado si la corrida analizó alguna superficie, de
  la búsqueda o del usuario.
- **Los rótulos**, cuando la crítica es del usuario (por identidad, `is_user_surface_of`):
  - la cabecera del panel acaba en «(surface defined by the user)» → «(superficie definida por el usuario)»;
  - el resumen dice «Critical surface, defined by the user» → «Superficie crítica, definida por el usuario».
- **La columna Nota** la escribe una sola función, `surface_note` (`ogr_gui/core_messages.py`), en las tres tablas
  (el panel, Superficies de Interpretar y, cuando tiene la columna, su Tabla de resultados): «Defined by the user» →
  «Definida por el usuario»; si además una comprobación la rechazó, «Defined by the user: {motivo}», con el motivo
  entero en la ayuda emergente, como antes.
- **`InterpretWindow._valid_surfaces()`**, nueva: las superficies válidas de las dos listas, las de la búsqueda
  primero. La leen:
  - **Exportar datos (CSV):** lleva las del usuario y, solo si la corrida analizó alguna, una última columna
    `user_defined` con «1» o «0»;
  - **Filtrar superficies:** su lista, su rango y la M de «Mostrando N de M»;
  - **la Tabla de resultados:** las lleva, con la sexta columna de arriba.
- **El retroanálisis de Interpretar**, solo cuando publica una fuerza, añade tras su primera línea:
  - «Back-analysed on the critical surface of the run ({0}).» → «Retroanálisis sobre la superficie crítica del
    cálculo ({0}).»;
  - «… ({0}), defined by the user.» → «… ({0}), definida por el usuario.»; `{0}` es el nombre del método.
- **Sin superficies del usuario,** las ventanas son las de 0.1.442, salvo esa línea del retroanálisis.

## 2. Qué se probó

- **`tests/test_windows_user_surfaces_v1443.py`** (27 casos; cinco corridas en el proceso y cinco ventanas de
  Interpretar, construidas una vez):
  - con la población vacía y la del usuario crítica: el panel y el resumen dan su factor, rotulado, en los dos
    idiomas, con el contador de la búsqueda en 0; la Tabla de resultados, el CSV y el filtro la llevan; un resultado
    sin ninguna superficie sigue diciendo que no hay resultados, y uno con una superficie sin factor, que no hay
    ninguna válida;
  - las tres tablas marcan la fila del usuario y solo esa, sea o no la crítica; la rechazada del usuario dice las dos
    cosas, con su ayuda y toda en gris; una rechazada de la búsqueda se lee como antes; la marca va por identidad;
  - la lista de las tres salidas es, por definición, las válidas de las dos listas en su orden; el CSV y la Tabla
    de resultados, fila a fila y celda a celda contra esa definición; el filtro, abierto con su `exec` sustituido;
  - **el retroanálisis:** con el círculo del usuario que no es el crítico, la línea nombra el método y no dice
    «usuario», la fuerza es la de `required_force_of_result` sobre la crítica, y la corrida publica otra, más de
    10 kN/m mayor, sobre el círculo del usuario; con la polilínea crítica, lo dice, en los dos idiomas; sin fuerza
    (la superficie ya alcanza el objetivo) no hay línea;
  - **sin superficies del usuario, lo de 0.1.442:** `_V1442`, ocho lecturas de las ventanas medidas en ese árbol con
    el `_capture()` del propio test (`capture_d401.py`, en el banco). Los textos, exactos; una celda que es un número
    con decimales, a 1e-6. El mensaje del retroanálisis es el medido con la línea nueva tras la primera, y nada más.
    De cada tabla y del CSV se fijan el recuento y las tres primeras filas, en inglés.
- **Discriminación:** en el árbol de 0.1.442, sin el buscador editable, fallan 18 de 27, todos por lo que las
  ventanas dicen o listan; pasan los nueve que comprueban lo que no debe cambiar (uno de ellos solo lee el literal
  medido).
- **Mutantes** (`mutants_d401.py`, en el banco): 51, todos muertos; 20 son de la revisión.
- **Tests que cambian a propósito:**
  - `tests/test_interpret_back_analysis_v1440.py` y `tests/test_back_analysis_rules_v1441.py` fijaban el mensaje del
    retroanálisis byte a byte: siguen exigiendo el texto medido entero, con la línea nueva tras la primera;
  - `tests/test_cli_reported_caption_v1430.py`: tres comentarios que describían el «No results yet.» de antes.
    Ningún aserto.
- **Vecinos**, con los patrones `interpret back_analysis names_and_headings spanish surface_ranking labels i18n
  results_dock user_surfaces user_polylines tensile_export newmark_user caption budget translat terms` del runner:
  657 casos en verde en 42 archivos (630 en 41 sin contar el nuevo).
- **Banco, en seco:** `d401()` da SIGUE ABIERTO con el árbol de 0.1.442 y CUBIERTO POR TEST con el nuevo; `d345()`,
  `d361()`, `d363()` y `d400()` siguen cerrando.
- **La suite entera** con `--jobs 4`, sobre el árbol final: **7521 casos, 7520 en verde, 0 fallos y 1 omitido**, sin
  fugas ni tramos muertos. La serie no toca (21 commits desde la última).

## 3. Qué queda

- **Sin ficha, a decidir por la propietaria** (el detalle, en §0): la escala de la leyenda frente al mapa de colores;
  la Tabla de resultados, que numera desde 0 y ordena «#» como texto; el CSV, que ordena sin mirar la
  admisibilidad; las frases de las tres gráficas y de los dos casos límite; el máximo del filtro; y el resumen de
  inválidas con superficies descartadas sin motivo.
- **Sin test:** una corrida con norma o con Ky (el revisor las midió: el rótulo sale bien, «Over-design factor:
  1.617 (surface defined by the user)»), y la línea del retroanálisis bajo una norma.
- **A mano, por la propietaria,** con la interfaz en español: una polilínea del usuario como crítica con un foco que
  vacía la búsqueda (el panel, el resumen y las tablas); y el retroanálisis de Interpretar, que diga qué tasó.
- **Fichas que siguen en P10:** D402 (0.1.444).
