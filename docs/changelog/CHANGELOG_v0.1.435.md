# OGR Slip2D v0.1.435

**Las gráficas de Interpretar ya no bloquean la aplicación, dicen qué método dibujan y, con una norma de diseño, nombran
el factor de sobredimensionamiento. Cada entrada de Estadística se activa con el resultado que dibuja (D413, la mitad de
las gráficas).** Son las cuestiones de diseño que la propietaria abrió en la revisión de 0.1.433. Las decidió una a una
al planificar esta versión, y la partió en dos: los nombres que pone el programa van a D415.

- **Siete gráficas eran modales** (`exec()`), contra AGENTS.md. Bloqueaban la aplicación y, sin pantalla, un test: el
  histograma, la acumulada, la dispersión, Mostrar valores a lo largo de la superficie, el diagrama de cuerpo libre, la
  Tabla de resultados y el barrido de desembalse de la ventana principal. Ahora todas se abren por una sola regla,
  `keep_chart`.
- **La gráfica de una variable aleatoria** tampoco es modal. Su botón se pone en gris con el motivo exacto, que es el
  mismo que lee el cálculo (`Distribution.not_random_reason`): antes un aviso modal daba un solo motivo para tres casos.
  Además, «Sin distribución» entra en la lista. Sin esa entrada, seleccionar una variable que el agente había apagado la
  guardaba como Normal, y Aceptar la volvía a encender (regla 7).
- **El Gráfico de sensibilidad y el tornado** dibujan el método que enseña Interpretar, si la corrida lo barrió, y lo
  nombran en el título. Antes dibujaban siempre el primero, sin decir cuál. La barra de Calcular estadística nombra el
  método cuando la corrida tiene más de uno.
- **Con una norma de diseño, las gráficas deterministas de Interpretar nombran el factor de sobredimensionamiento** en
  sus ejes, títulos y marcas, como ya hacían el resumen y la tabla de Superficies. Son FS a lo largo del talud, el
  histograma, la acumulada, la dispersión, la leyenda de los contornos, Mostrar valores, el cuerpo libre, la Tabla de
  resultados, las lecturas de consulta, Análisis de fuerzas de soporte y Elegir GM. También el retroanálisis, cuyo
  objetivo pasa a ser un factor de sobredimensionamiento porque corre sobre la copia con coeficientes. Sin norma, el
  texto de 0.1.434 byte a byte.
- **Cada entrada de Estadística se activa con el resultado que dibuja** y, si no, sale en gris con su motivo:
  sensibilidad, probabilístico, o los mínimos de una búsqueda multimodal. Antes cuatro respondían con un aviso modal al
  resultado que no era el suyo. Las entradas se recalculan al calcular estadística con Interpretar abierto: antes se
  calculaban una sola vez, al construir los menús.
- **«(none)»** ya no sale en pantalla, y el censo que lo encontró se queda. El clic que lo enseñaba, pintar con un
  material ya borrado, se rechaza desde la revisión: pintaba la región con un material que no existe.
- **Por decisión de la propietaria en la revisión,** entran cinco cosas que ya estaban en 0.1.434:
  - el barrido de desembalse dibuja cada método contra sus propios niveles y, con norma, nombra el FSD. Antes dibujaba
    todos contra los niveles del último, así que la curva mentía en cuanto un método perdía un nivel;
  - un clic de Asignar fuera de toda región ya no dice «Región pintada» ni deja un paso de deshacer;
  - Graficar consulta del factor se titula, con norma, «Factor de sobredimensionamiento»;
  - las Tablas de propiedades y el informe de Limpiar geometría dejan de ser modales;
  - y abrir el editor de variables y Aceptar sin tocar nada ya no redondea lo que guardó el agente.
- **Estirar un soporte** decía «Soporte 1 head estirado.». Lo encontró la regla del censo de esta versión, ampliada en
  la revisión.
- **Ningún número cambia, y el agente no ve nada de esto.**

Es la octava versión de la tanda P10. Al partir D413, la propietaria abrió **D415** (0.1.436, los nombres que pone el
programa), y en la revisión, **D416** (0.1.446, al final de P10): una Beta o una Gamma sin desviación típica. D414 pasa a
0.1.437 y D400–D409 a 0.1.438–0.1.445. En este commit la spec de Sarma se renumera +2, a 0.1.447–0.1.453.

## 0. Lo que se encontró

- **Al planificar,** dos exploradores en solo lectura midieron sobre 9830ba5:
  - los nombres por defecto que pone el programa;
  - las cuatro cuestiones de las gráficas.
  - Un agente de diseño propuso el plan, y la propietaria decidió en tres rondas.
- **Decisiones de la propietaria (2026-11-09):**
  - la gráfica de una variable, no modal y con el botón en gris;
  - la sensibilidad, por el método de Interpretar y nombrado;
  - el factor con norma, en las cinco gráficas y en sus títulos;
  - las cuatro puertas, recalculadas;
  - y entran cuatro hallazgos de los exploradores (las siete gráficas modales, el editor que no se libera, las puertas
    que no se recalculan y «(none)») y dos anomalías del agente de diseño («Ninguna» que pasa a Normal y las superficies
    GM sin resultado probabilístico).
  - «Silty clay» se queda como dato.
  - **Se parte en dos:** los nombres por defecto («Type N», «(copy)», «Record» y las cargas) tocan mensajes del núcleo
    que lee el agente, y van a D415 con sus cuatro detalles y dos anomalías más (el kPa de una carga lineal y «Definida
    por el usuario»).
- **Lo que vio la planificación:**
  - **«Ninguna» no estaba en la lista de distribuciones** (`random_variables_dialog.py`, `_DIST_LABELS`), así que
    seleccionar una variable apagada dejaba la lista en Normal y `_on_dist_changed` la guardaba así. Se comprobó antes
    de decidir.
  - **El aviso modal de la gráfica de variable** decía «Introduce antes un mínimo y un máximo relativos.» también cuando
    el motivo era la desviación típica cero.
  - **El editor de variables no se liberaba:** cada apertura dejaba otro hijo de la ventana vivo, al contrario que el
    hidráulico (v0.1.276).
  - **Las puertas de Interpretar se calculaban una vez,** en `_build_menus`. Mostrar y Elegir superficies GM seguían
    activas con solo un resultado de sensibilidad, que no tiene mínimos.
  - **Una gráfica no modal es una foto:** si se cambia de método con ella abierta, no lo dice. Las de sensibilidad
    nombran su método; las demás se dejan así y se reporta.
  - **El cuerpo libre pide la dovela con `getInt`,** que sigue modal: es una entrada, no una gráfica.
- **Paso 0, medido antes de arreglar (regla 6):**
  - **El censo de «FoS» y «FS»** en `interpret_window.py` y `chart_dialogs.py` sobre 9830ba5 dio 20 literales:
    - los siete de la decisión;
    - los que había visto la planificación: la acumulada y su respaldo, las dos lecturas de consulta, el «FoS =» de
      Superficies por un punto y las dos cabeceras de tabla;
    - el «FS(0)» de `_reported_value`, que ya sigue a la norma desde D405/D409;
    - la cabecera del panel de Superficies (571) y la convergencia (2727), que ya la seguían;
    - y dos fuera del inventario, que se enseñaron antes de tocarlos: el retroanálisis («Factor de seguridad objetivo:»
      y «Fuerza de soporte requerida para FS = …»), que con norma corre sobre la copia con coeficientes, y la lectura de
      consulta «FS =1.234 r =…», que copia a propósito el formato de la referencia.
    - **La propietaria decidió:** el retroanálisis entra y la lectura de consulta se queda como la referencia.
  - **Las ventanas** del histograma y de FS a lo largo del talud nombraban el factor con la palabra entera («Factor of
    Safety»), que el censo de abreviaturas no ve. Entran con la misma regla.
  - **Lo que nombra el factor fuera de las gráficas se queda, y se reporta:**
    - la casilla «Por factor de seguridad» del filtro;
    - el combo de campos de la consulta de dovelas;
    - las descripciones emergentes;
    - el FS frente al tiempo del transitorio.
  - **El censo nuevo de «(none)»** sobre 9830ba5 encuentra un solo sitio, `main_window.py:5780`, y ninguno en el árbol
    nuevo.
- **Caminos equivocados:**
  - **El test de la gráfica de variable suponía un diálogo sin selección al abrirse.** Abre en la primera variable, así
    que el estado «nada seleccionado» se prueba con un diálogo sin variables.
  - **El guion del diccionario no veía una entrada partida en tres líneas** (la razón de las superficies GM). Falló
    antes de escribir nada y la entrada se quitó por su texto exacto.
  - **El censo del paso 0 buscaba abreviaturas,** y el título de dos ventanas decía el nombre entero. Se amplió a mano.

### La revisión adversaria

Siete agentes: cuatro lentes (las gráficas, la norma y el método, las puertas y las variables, y los tests con los
censos y el changelog), un crítico de completitud y dos escépticos que intentaron refutar cada hallazgo con sondas
propias. Dieron 26 hallazgos:
- **dos, refutados:** «Sin distribución» no saca la variable de la sensibilidad, pero la sensibilidad solo lee el
  rango, sea cual sea la distribución; y con un probabilístico de Mínimo global, Mostrar y Elegir GM y la Superficie
  probabilística crítica siguen activas sin nada que dibujar, que es la regla que decidió la propietaria e igual que en
  0.1.434;
- **diecisiete, nacidos con esta versión,** arreglados con su test o su mutante;
- **siete, que ya estaban en 0.1.434,** decididos por la propietaria (2026-11-10).

**Lo que la versión había hecho mal:**
- **El editor de variables seguía sin liberarse,** y el arreglo anunciado no funcionaba. La conexión nueva del botón era
  una lambda que nombraba al diálogo. PySide la retiene desde C++, el recolector no ve el ciclo, y `setParent(None)` solo
  lo cambiaba de hijo oculto de la ventana a ventana de nivel superior oculta, con su proyecto (que sobrevivía a
  Archivo → Nuevo) y sus gráficas. Como la gráfica ya no era modal, aparecía algo que 0.1.434 no podía hacer: seguía en
  pantalla tras Aceptar o Cancelar, enseñando una distribución que Cancelar había descartado. El test miraba
  `findChildren` y pasaba con la fuga.
  - Ahora son métodos ligados, y `done()` cierra las gráficas del editor.
  - El test mide la destrucción: un `weakref`, las ventanas de nivel superior y la validez de la gráfica.
- **El retroanálisis nombraba su objetivo por la norma del proyecto de ahora,** no por la de la corrida, contra la regla
  de `ogr_gui/reported_quantity.py` («se pregunta al resultado y al informe de la corrida, nunca a `project.settings`»).
  La fuerza sale de las dovelas de la corrida, así que lo que el objetivo es lo dice la corrida. Ahora se nombra por
  `_factored_view()`, como el resto de la ventana. El test que lo consagraba encendía la norma en el proyecto sobre una
  corrida sin ella.
- **Dos textos con norma se quedaron a medias:**
  - el rechazo de la envolvente del retroanálisis decía «el factor de seguridad objetivo» bajo una pregunta por el FSD;
  - el formulario de Superficies por un punto prometía «la de menor factor de seguridad» y la respuesta daba el FSD.
- **Mostrar GM y la Superficie probabilística crítica se quedaban marcadas al pasar a gris,** con los mínimos de un
  resultado borrado en el lienzo y sin poder quitarlos: la única entrada que lo hace estaba en gris. Ahora se desmarcan,
  como la línea de empuje.
- **El motivo nuevo de las entradas probabilísticas mandaba a Calcular estadística,** que no sirve si en Ajustes de
  proyecto solo está la sensibilidad. Ahora el motivo de cada análisis depende de si está activado («actívalo en Ajustes
  de proyecto > Estadística y ejecuta…»).
- **La spec de Sarma no estaba renumerada,** aunque este changelog lo decía. Ahora sí (+2, con D416).
- **Huecos de los tests:**
  - seis textos con norma sin ningún test: el paso del ratón, el clic, Superficies por un punto, Elegir GM y de qué
    fuente sale su factor, el respaldo de la acumulada y el formulario de FS a lo largo del talud;
  - la prueba de las puertas comparaba booleanos y no el motivo, y no cubría los mínimos de una búsqueda ni el cambio de
    método;
  - quitar la última variable no tenía test;
  - y `test_task_notes_v1363` sustituía un `exec` que ya no se llama.
- **La regla nueva del censo tenía huecos y falsos positivos,** y su autocomprobación dejaba vivos cinco de seis
  mutantes. Atribuía a una función lo que asignaba otra anidada, y no veía estas formas:
  - un destino en tupla, una anotación, `+=`, la morsa o un `for` sobre literales;
  - un diccionario o una tupla tras `%`, `*args`, `str(nombre)` o `nombre.strip()`;
  - un segundo nombre, o una plantilla guardada antes de rellenarla.
  - Ahora lee cada función una sola vez y sin sus anidadas. La autocomprobación tiene veinte casos que debe encontrar y
    cinco controles que no.
  - **Ampliada, encontró un texto en inglés que ya estaba:** «Soporte 1 head estirado.». También dio una unidad y cinco
    extensiones de archivo, que van a las excepciones con su motivo.
  - Las constantes de módulo como ámbito se midieron y no se añadieron: solo dan los nombres propios de Acerca de.
- **Higiene:** el test de la gráfica de variable de `test_spanish_paths_v1433` la dejaba abierta el resto del proceso;
  este changelog decía que la Tabla de resultados «ya no sustituye `exec`», y lo sigue sustituyendo por uno que falla si
  se llama; y `_has_statistics` se quedó sin llamadas, con un test que solo comprobaba una sustitución suya.

**Lo que ya estaba en 0.1.434, y lo que decidió la propietaria:**
- **Entran aquí:**
  - el barrido de desembalse contra los niveles del último método, y el FS con norma (el trabajador tiraba el informe de
    coeficientes);
  - pintar con el id de un material borrado (ahora se rechaza) y el clic fuera de toda región, que no pintaba nada y lo
    anunciaba, con un paso de deshacer vacío;
  - Graficar consulta del factor con norma;
  - las Tablas de propiedades y el informe de Limpiar geometría, modales;
  - Aceptar sin tocar nada, que reescribía con el redondeo de los controles (la correlación a tres decimales, la
    desviación a seis, y 4e-7 pasaba a 0 y apagaba la variable). Ahora cada control guarda solo su campo, y solo cuando
    el usuario lo cambia;
  - y el soporte estirado, con una clave por extremo: el inglés no cambia.
- **A una ficha aparte, D416 (0.1.446):** con desviación típica cero, una Beta o una Gamma cuentan como aleatorias para
  el cálculo y para el botón (que dibuja una curva plana en cero, y cada muestra vale la media), y la regla del agente
  las rechaza como no aleatorias. Unificarlo cambia qué se muestrea, así que va en su versión, midiendo antes el banco.
  `not_random_reason` copia byte a byte el criterio de `is_random`, como prometía esta versión.
- **Al buscar el arreglo** apareció otra cosa: al seleccionar una variable cuya pareja de correlación no estaba en la
  lista, el combo se quedaba con la pareja de la variable anterior, y la primera edición la guardaba. Ahora enseña
  «(ninguna)» y no guarda nada.

## 1. Qué cambia

- **`ogr_gui/xy_chart.py`:** `keep_chart(owner, dlg)` enseña la gráfica no modal y la guarda en `owner._chart_windows`.
  Antes suelta con `setParent(None)` las que el usuario cerró (la regla de v0.1.277), porque la ventana principal vive
  toda la sesión. `show_xy_chart` la usa.
- **Interpretar (`ogr_gui/interpret_window.py`):**
  - el histograma, la acumulada, la dispersión, Mostrar valores, el cuerpo libre y la Tabla de resultados, por
    `keep_chart`. También el tornado, FS a lo largo del talud y el diagrama de fuerzas, que ya eran no modales;
  - `_sensitivity_method(sens)` da el método de Interpretar o el primero, y los dos títulos lo nombran;
  - `_factored_view()` pregunta si la corrida tiene norma. Cada texto que nombra el factor elige entre su clave de
    siempre y una con «ODF» (en castellano «FSD»), así que sin norma no cambia ni un byte;
  - el retroanálisis pregunta y nombra su objetivo según la norma de la corrida (`_factored_view()`), también en el
    rechazo de la envolvente;
  - `refresh_statistics_gates()` decide las siete entradas de Estadística. La llaman `_build_menus`,
    `_on_method_changed` y la ventana principal. El motivo depende de si el análisis está activado en Ajustes de
    proyecto, y una entrada marcada que pasa a gris se desmarca;
  - el formulario de Superficies por un punto y Graficar consulta del factor, con norma, nombran el FSD;
  - `_has_statistics`, sin llamadas, se va.
- **`ogr_gui/dialogs/chart_dialogs.py`:** `factored=` en el histograma, la acumulada y FS a lo largo del talud, y
  `method=` en el tornado. Los dos son opcionales y, por defecto, dan el texto de siempre. `MultiLineDialog` acepta una
  serie con sus propias x, `(etiqueta, xs, ys)`.
- **La ventana principal:**
  - `_update_statistics_actions` refresca las puertas de cada Interpretar abierto;
  - el barrido de desembalse, por `keep_chart`, con cada método contra sus niveles (el desembalse total, en el más bajo
    de todos), y con norma el título y la barra dicen FSD: el trabajador guarda el informe de coeficientes;
  - las Tablas de propiedades y el informe de Limpiar geometría, por `keep_chart`;
  - `_edit_random_variables` libera el editor;
  - «la más influyente (método): …» cuando la corrida tiene más de uno;
  - pintar con un material que ya no existe se rechaza, y un clic fuera de toda región lo dice y no deja paso de
    deshacer (`PaintRegionCommand` se ejecuta y solo se apunta si pintó, con `CommandStack.record`);
  - estirar un soporte, con un texto por extremo.
- **Definir variables aleatorias:**
  - «Sin distribución» en la lista;
  - `btn_plot` en gris con su motivo (`_plot_reason`, `_update_plot_gate`);
  - `_plot` no modal, que devuelve la ventana;
  - cada control guarda solo su campo, con métodos ligados, y seleccionar una variable o Aceptar no guardan nada;
  - `done()` cierra las gráficas que abrió el editor.
- **El núcleo:** `Distribution.not_random_reason()`, y `is_random` lee esa regla. Ningún número cambia.
- **`ogr_gui/i18n`:** 38 entradas nuevas y cuatro retiradas, sin ningún valor cambiado ni ninguna clave repetida. Se
  retiraron «Enter a relative minimum and maximum first.», las dos razones de «análisis probabilístico o de
  sensibilidad» y «Support {0} {1} stretched.», que ya no usaba ningún código.
- **Tests:**
  - `tests/test_interpret_charts_v1435.py`, nuevo;
  - `test_gui_spanish_v1318` gana la regla de un nombre que llega a un campo de un texto traducido
    (`carried_into_fields`), con seis excepciones nuevas: la unidad de un radio y cinco extensiones de archivo;
  - cambian a propósito cinco de `test_spanish_paths_v1433`:
    - la gráfica de variable devuelve su ventana, y el test la cierra;
    - el título del tornado nombra el método;
    - el Gráfico de sensibilidad pasa a gris con solo un resultado probabilístico;
    - y el motivo del tornado y del Gráfico es el de una sensibilidad apagada en Ajustes de proyecto, que es como la
      tiene ese proyecto;
    - la Tabla de resultados se lee de la ventana que devuelve, y su `exec`, sustituido, falla si se llama;
  - `test_task_notes_v1363` comprueba que la gráfica del barrido es no modal, en vez de sustituir un `exec` que ya no se
    llama;
  - `test_interpret_i3_v153` comprueba la puerta real de Exportar datos estadísticos, no una sustitución de
    `_has_statistics`;
  - el `_Fake` de `test_undo_settings_annotations_v1305` gana `setParent`, y el informe falso de
    `test_f2_rules_v1196`, `show`, `isHidden` y `setParent`.
- **La spec de Sarma** (`spec/features/009-sarma-dovelas-no-verticales/`) se renumera +2: 0.1.447–0.1.453.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_interpret_charts_v1435.py`,** 26 tests, unos 8 s en total (20 antes de la revisión, que añadió seis y
  amplió cuatro):
  - **las siete gráficas** son no modales y quedan guardadas, bajo `_no_modals()`. Identidades:
    - las barras del histograma suman las superficies válidas;
    - la dispersión tiene un punto por cada una;
    - los factores de la Tabla de resultados son los suyos;
    - el cuerpo libre nombra su dovela;
    - una gráfica cerrada se suelta al abrir otra;
  - **la gráfica de variable:**
    - el motivo del núcleo, sobre una rejilla de tipos × desviación típica × rango, contra las tres condiciones
      escritas en el test;
    - el botón, en vivo: sin variable, desviación típica cero, rango vacío y «Sin distribución»;
    - una variable apagada sigue apagada tras Aceptar;
    - la ventana no es modal;
    - el editor se libera;
  - **el método:** con dos métodos y Bishop activo, las barras del tornado son las de Bishop y las curvas de la gráfica,
    sus barridos, con los dos títulos nombrándolo. Sin Bishop, el primero, nombrado. La barra de estado, con dos métodos
    y con uno;
  - **con norma,** cada eje dice lo mismo que el resumen de Interpretar (`reported_quantity`) y la cabecera de la tabla
    lo mismo que la de Superficies (`column_caption`); ningún texto dice «Factor de seguridad». También la leyenda de los
    contornos, el retroanálisis y los soportes. **Sin norma,** los textos de 0.1.434;
  - **las puertas,** con la ventana principal y su Interpretar abierto: sin resultados, solo probabilístico, solo de
    sensibilidad, y otra vez sin resultados. En cada paso, cada entrada tiene el estado, el motivo y la descripción que le
    tocan;
  - **«(material eliminado)»** por el clic real de Asignar, y la regla del censo, con su autocomprobación.
- **Lo que añadió la revisión al test:**
  - **el editor de variables, destruido con sus gráficas,** tras Cancelar y tras Aceptar: un `weakref` muerto tras
    `gc.collect()`, ninguna ventana de nivel superior nueva y la gráfica ya no válida (y oculta antes);
  - **abrir y Aceptar no cambian nada:** una correlación de −0,8765, una desviación de 1,23456789 y otra de 4e-7 salen
    iguales, y cambiar la desviación no toca la correlación ni el rango;
  - **quitar la última variable** pone el botón en gris con su motivo;
  - **el retroanálisis**, por el informe de la corrida con la norma del proyecto al revés, también en el rechazo de la
    envolvente;
  - **las lecturas y las consultas con norma y sin ella:** el paso del ratón, el clic, Superficies por un punto (su
    formulario y su respuesta), Elegir GM con los mínimos de una búsqueda y con los de un probabilístico, el respaldo de
    la acumulada y Graficar consulta; y el formulario de FS a lo largo del talud;
  - **las puertas, por el texto de su motivo** en cada paso, con el análisis apagado y encendido en Ajustes de proyecto;
    los mínimos de una búsqueda siguiendo al método de la ventana; y las dos entradas marcadas que pasan a gris,
    desmarcadas;
  - **el barrido de desembalse con dos métodos de niveles distintos:** cada curva tiene los suyos (el desembalse total,
    en el más bajo de todos), y con norma dicen FSD el título y la barra;
  - **las Tablas de propiedades y el informe de Limpiar geometría,** no modales;
  - **pintar:** con un material borrado, fuera de toda región y, de control, dentro, por el clic real, con la cuenta de
    los pasos de deshacer;
  - **estirar un soporte** por la cola y por la cabeza, en castellano, y en inglés el texto de siempre;
  - **la autocomprobación del censo:** veinte formas que debe encontrar y cinco controles que no (una función anidada,
    un literal traducido en su sitio, un `.format` que no es de `tr()`, un nombre de dato y un texto traducido).
- **Discriminación en el árbol de 0.1.434** (`git archive` de 9830ba5, sin el buscador editable): fallan los 26. El
  control «sin norma, los textos de 0.1.434» falla allí solo porque esas gráficas eran modales.
- **Mutantes, uno a uno y en memoria:** 53, todos cazados. Trece de los catorce de antes de la revisión, por los
  tests de su regla (el de «(none)» ya no tiene sitio, porque ese clic se rechaza):
  - las gráficas modales otra vez;
  - `keep_chart` sin soltar las cerradas;
  - el primer método siempre;
  - el tornado sin nombrarlo;
  - sin la vista con norma;
  - las puertas por «cualquier resultado»;
  - las puertas sin refrescar desde la ventana principal;
  - el motivo vacío;
  - «Sin distribución» fuera de la lista;
  - el editor sin liberar;
  - «(none)»;
  - el censo sin su regla;
  - la barra sin el método;
  - el retroanálisis con «FS».
  - Dos mutantes se reescribieron antes de valer: el guion quitaba la sangría al código antes de sustituir, y un
    `__init__` recompilado fuera de su clase pierde `super()`.
  - **Los 40 de la revisión:**
    - uno por cada arreglo: el editor (la lambda, `done()`, guardar al seleccionar y al Aceptar, el botón al quitar la
      última), el retroanálisis (con «FS», por el proyecto, la envolvente), cada lectura y formulario con norma, las
      puertas (el motivo de la sensibilidad en Exportar, GM sin los mínimos de la búsqueda, el motivo sin mirar los
      Ajustes, sin desmarcar, sin refrescar al cambiar de método), el barrido (las x compartidas, el FS), las dos tablas
      modales, el pintado (el material borrado aceptado, el clic fuera anunciado) y el soporte estirado;
    - y doce de la regla del censo: los cinco que la revisión dejó vivos (las palabras clave, la tupla de `%`, solo el
      primer destino, solo la última asignación, solo la primera), sin el `%`, leyendo las anidadas, sin el literal
      traducido en su sitio, sin la plantilla guardada, sin `+=`, sin el `for` y sin `self.x`.
  - **Dos caminos equivocados de los mutantes:**
    - el de Aceptar mataba el proceso con una violación de acceso, sin un solo test. Su envoltorio se llamaba `accept`:
      PySide conecta un método ligado cuyo nombre es una ranura del receptor (`QDialog.accept`) a esa ranura de C++, y
      la conexión del botón Aceptar reventaba en el `__init__`. Con otro nombre, el test lo caza;
    - el de las x compartidas sobrevivía: con los datos del test, el desembalse total en el nivel más bajo de todos
      daba a los dos métodos las mismas x. Ahora cada método pierde un nivel distinto.
- **Suite entera con `--jobs 4`,** antes de la revisión: 7349 de 7350, 1 saltado y 0 fallos, sin fugas ni tramos muertos
  y sin archivos lentos fuera de `tests/_slow.txt`. **Después de la revisión:** 7355 de 7356, 1 saltado y 0 fallos, sin fugas ni
  tramos muertos y sin archivos lentos fuera de `tests/_slow.txt`. La última serie en verde está a 13 commits.
- **Los vecinos,** antes de la suite (34 archivos, `--jobs 4`): 522 de 523. El que fallaba es uno de los cambios a
  propósito de `test_spanish_paths_v1433`: su proyecto tiene la sensibilidad apagada.
- **Banco, en seco:**
  - `d413()`, en vivo, da CUBIERTO POR TEST;
  - con el árbol de 0.1.434 da SIGUE ABIERTO, por lo que hace cada medida: la gráfica y el histograma por `exec`, el eje
    «Factor de seguridad», el tornado sin método, el Gráfico de sensibilidad activo y el pintado con «(none)» y su paso
    de deshacer;
  - D300, D315, D318, D335, D344, D399, D411 y D412 siguen CUBIERTO POR TEST.

## 3. Qué queda

- **D415,** en 0.1.436: los nombres que pone el programa, con lo que decidió la propietaria:
  - «Tipo 3», «… (copia)» (también tras un nombre dado) y «Registro», traducidos al enseñarlos;
  - «Type N» con el primer número libre, y Duplicar sin repetir;
  - las cargas sin nombre dado, por su tipo y su magnitud actual;
  - las comillas en las notas de carga lineal;
  - el kPa de una carga lineal;
  - y «Definida por el usuario» en masculino.
- **D414,** en 0.1.437. El resto de la tanda P10: D400–D404 en 0.1.438–0.1.442, D408 en 0.1.443, D406 en 0.1.444, D409
  en 0.1.445 y **D416** en 0.1.446 (una Beta o una Gamma sin desviación típica); D407 y D410 siguen sin versión. Sarma
  va en 0.1.447–0.1.453.
- **Una gráfica no modal es una foto,** y se reporta: si se cambia de método con ella abierta, no lo dice. Las de
  sensibilidad nombran su método, y las del editor de variables se cierran con él.
- **Prueba a mano, para la propietaria,** con la interfaz en español:
  - abrir el histograma, la dispersión y la Tabla de resultados a la vez, y seguir usando Interpretar;
  - Graficar distribución con desviación típica cero, y cerrar el editor con la gráfica abierta;
  - el tornado con dos métodos;
  - las gráficas con una norma de diseño;
  - Calcular estadística con Interpretar abierto, mirando el menú Estadística;
  - el barrido de desembalse con dos métodos;
  - y pintar fuera del modelo.
