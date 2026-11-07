# OGR Slip2D v0.1.433

**Con la interfaz en español, otros treinta sitios que enseñaban inglés lo dicen ya en español, por reglas de
`ogr_gui/labels.py`. Los censos leen ahora los caminos por los que llegaban sin verse (D411, la mitad de la
interfaz).** Los mensajes del núcleo y los nombres de deshacer son D412, en 0.1.434, por decisión de la propietaria.
- **Identificadores en pantalla:**
  - el método de búsqueda en la barra y en el Visor de información («Búsqueda: grid»);
  - el resumen de Condiciones de contorno («nodal_flow: 21»);
  - el informe de Limpiar geometría («[0] EXTERNAL «External Boundary»»);
  - las cuentas de Importar DXF («EXTERNAL: 1»);
  - las Tablas de propiedades («water_table», «cohesion», «shear», «constant») y el dato emergente de un soporte;
  - la columna «Tipo» de la Tabla de resultados de Interpretar («circle»);
  - el método en Exportar datos brutos;
  - la etiqueta guardada de una variable aleatoria («friction_angle»);
  - y once campos de notas con código que guardaban un identificador sin declarar su tipo («'non_circular'»,
    «'grid'», «b_bar, corps_2»).
- **Inglés al lado de un texto traducido:**
  - el mensaje de arranque («Listo — File → Load Demo Slope…»);
  - el Filtro de selección, con sus campos y «nothing selectable», y «no conditions»;
  - la gráfica de una variable aleatoria y «ΔFoS»;
  - el error de la vista previa del DXF;
  - un rechazo con código enseñado tal cual (el barrido de desembalse);
  - y « deg», en Definir soporte y en la ventana de materiales.
- **Nombres por defecto que pone el programa, en inglés:**
  - «Untitled» y «Demo slope», que se traducen por decisión de la propietaria;
  - «Original ground (from Expand/Shrink)»;
  - un tipo de soporte que un agente crea sin nombre, también en Modificar soporte, Mover soporte y el diagrama de
    fuerzas, y por la clase que tiene si se la cambian;
  - y «Untitled Project» en el informe PDF, que además ya dice «No circular» y nombra la búsqueda por enjambre.
- **«[BC]»,** que se escribía en la etiqueta de una etapa y quedaba guardado, ya no se escribe (decisión de la
  propietaria). Una etapa con sus propias condiciones se marca en una columna propia, y en Interpretar agua
  subterránea sale «[CC]», como «[FS]». En un archivo viejo, el « [BC]» del final se oculta y el diálogo lo quita al
  aceptar.
- **Los dos diálogos que ningún menú abría (decisiones de la propietaria):**
  - el tornado de sensibilidad se conecta en Interpretar («Tornado de sensibilidad...»), con las cifras del
    ranking;
  - «Graficar FS a lo largo del talud...» dibuja con SFAlongSlopeDialog, con las mismas cifras de antes.
- **Ningún número cambia.** El agente, la línea de órdenes y el `.ogr` siguen con su inglés y sus datos.

Es la sexta versión de la tanda P10. **La spec 009 (Sarma) se renumera +2, a 0.1.444–0.1.450,** porque la propietaria
partió D411 en dos (D412 entra en 0.1.434) y, en la revisión, abrió D413 en 0.1.435.

## 0. Lo que se encontró

- **Al planificar,** tres exploradores en solo lectura midieron sobre 2f498f6:
  - el inventario de los sitios y el ayudante que ya existía para cada uno;
  - los mensajes del núcleo y los nombres de deshacer (D412);
  - y cada regla posible de censo, contando sus aciertos de verdad y sus falsos positivos.
  - Un agente de diseño propuso partir la ficha, y la propietaria lo decidió así.
- **Paso 0, medido antes de arreglar:**
  - las reglas nuevas del censo contaron trece textos: los diez reales del inventario y tres notaciones («x (m)»,
    «y (m)», «FS = 1»), que van a excepciones con su motivo;
  - el barrido en tiempo de ejecución del explorador no vio nada fuera del inventario, salvo un error del sistema
    operativo (de D412) y falsos positivos conocidos.
- **F1, medido sobre los valores de verdad.** La heurística por nombre daba 177 campos sin tipo. Las muestras que
  guardan los tests de cada catálogo (las de v0.1.349, no lo que pasa hoy el motor: la de
  `setting.drawdown_unknown` aún dice `duncan_wright_wong`) dieron once campos con un identificador. Al declararlos,
  y los de las plantillas hermanas, son dieciocho campos en trece notas, y un test vigila que ninguno quede sin
  tipo.
- **F2 cambió al planificar.** La propietaria eligió que «FS a lo largo del talud» fuera el FS mínimo por punto de
  salida. Medido después: Interpretar ya tenía ese gráfico con menú desde v0.1.82 («Graficar FS a lo largo del
  talud...»), y SFAlongSlopeDialog era el resto de la versión que v0.1.82 retiró por dibujar el FS global en cada
  dovela. Se le enseñó, y decidió que el menú existente dibuje con ese diálogo.
- **Caminos equivocados:**
  - **Mi primer arreglo del barrido de desembalse** llamaba a `note_text` en una función que la importa más abajo, lo
    que la hace local en toda la función: lanzaba `UnboundLocalError`. Lo cazó el test nuevo antes de la suite.
  - **La primera corrida del test nuevo se colgó** más de diez minutos. La gráfica de una variable aleatoria abre un
    aviso modal si la distribución no es aleatoria, y el test fijaba campos que no existen. Ahora lo comprueba antes.
  - **Otra prueba abortaba con código 127** corrida sola: construía la ventana sin una `QApplication`, que el resto de
    pruebas creaba sin decirlo.
  - **El censo en tiempo de ejecución tomaba «Demo slope» por un nombre dado** en inglés, porque comparaba el nombre
    con su etiqueta, que en inglés coinciden. Ahora compara con las constantes del núcleo.
  - **Intenté matar todos los procesos de Python** para cortar el cuelgue, y no se debe: la máquina se comparte con la
    sesión de OGR-FEM2D. Se pararon solo los dos procesos del test, por su línea de órdenes.
  - **En el script de la spec, un número se desplazó dos veces.** Se vio al releerla y se corrigió.
  - **La primera suite entera dio un fallo:** el test nuevo alcanzaba la memoria de otro archivo, el vocabulario que
    guarda `_reads_english` en `test_labels_spanish_v1321`. En la serie recibiría el objeto que calculó ese archivo,
    y con `--jobs` uno nuevo. Es seguro, porque el vocabulario sale del diccionario, ningún test lo cambia (medido) y
    solo se lee: entra en el `ALLOWED` de `test_shared_test_caches_v1378`, con ese motivo.
  - **Al repasar el diff, el selector de etapas y el diálogo trataban distinto el « [BC]» viejo.** `stage_entry`
    lo quitaba también de una etapa sin condiciones propias, donde no es la marca del programa, y `stage_label` solo
    de una que las tiene. Ahora los dos igual, y el test lo comprueba.
  - **La primera `d411()` del banco salía SIGUE ABIERTO en los dos árboles,** y no por el programa: leía la tabla de
    un diálogo temporal, que se destruía con ella (`Internal C++ object … already deleted`). Ahora guarda el
    diálogo.
- **La revisión adversaria encontró en el diff** lo que sigue, y se arregló aquí:
  - **«[CC]» salía en TODAS las etapas.** La puerta del proyecto rellena una etapa sin condiciones propias con las
    actuales, así que `stage.bcs` nunca era None y `own_bcs` salía siempre verdadero. El test lo daba por bueno
    porque le pasaba a `stage_entry` notas escritas a mano. Ahora `TransientStage` lleva `own_bcs`, leído de la etapa
    guardada como lo lee el diálogo, y un test resuelve por `solve_project_groundwater`. La nota se guarda en el
    `.ogr` con el resultado (aditiva, no la lee el agente): §1 decía «sin cambiar ningún dato», y eso no era exacto.
  - **El título del informe PDF seguía en inglés desde la ventana.** La ventana pasa `title=summary.title`, que gana
    a la rama nueva, y el resumen nace con el nombre del proyecto («Untitled», «Demo slope»). El test llamaba a
    `generate_report` sin `title=`, que no es como llama la ventana. Ahora se traduce el título que se imprime, venga
    de donde venga, si es uno de los tres por defecto, y el test pasa por `act_generate_report`.
  - **El tornado juntaba en una barra dos variables con la misma etiqueta** (dos cargas de 20 kPa), porque se
    indexaba por la etiqueta y se dibujaba en un eje de categorías. Ahora es una lista de pares en posiciones
    numéricas. El eje decía «cambio del mínimo al máximo de la variable», que no es la barra en un barrido no
    monótono: dice ya lo que es (el rango del factor en el barrido, positivo si es mayor en el máximo). Y estaba
    activo con un resultado solo probabilístico, para contestar con un aviso: ahora pide uno de sensibilidad.
  - **Un conjunto de soportes con el nombre por defecto de otra clase salía con la clase vieja** (nació Anclado en
    el extremo, y el combo o `support_type_set` le cambiaron la clase). Como un contorno con `boundary_label`, se
    enseña ya por la clase que tiene.
  - **«Definido por el usuario» solo en la lista:** el combo de Definir soporte, el diagrama de fuerzas y el nombre
    de sus variables seguían en femenino. Los tres pasan por la misma clave.
  - **«una superficie superficie de capa débil»:** las dos plantillas del caso de capa débil ponían «una superficie»
    delante de un campo que ahora ya es «superficie de capa débil». Tienen su propio tipo (`surface_noun`: «superficie
    circular», «superficie poligonal», «superficie compuesta», «superficie de capa débil»).
  - **La lista de procedimientos de desembalse se leía con seis nombres en vez de cuatro,** porque uno lleva comas.
    Se une con «; », y la de técnicas también.
  - **«Línea piezométrica: … — SE CORTA A SÍ MISMO»:** la marca va detrás del tipo desde esta versión, y cinco de
    los nueve son femeninos. Pasa a «SE AUTOINTERSECA».
  - **El tipo de la nota de la exportación DXF no traducía nada:** el campo llevaba el nombre de una clase de Python.
    Lleva el tipo serializado cuando la superficie lo tiene.
  - **Los censos tenían huecos.** El vocabulario perdía las palabras inglesas que algún valor castellano cita como
    código («shear | ito_matsui», «build_method(project, method_id)»), y con ellas «surface», «method», «shear» y
    «constant». No leía las marcas de los ejes (donde el tornado nombra sus variables) ni los hijos de un árbol. Dos
    excepciones sin anclar eximían el texto entero. Y tres reglas del censo de árbol de sintaxis no tenían
    autocomprobación. **Al ampliar el censo apareció un sitio más, en la familia de « deg»:** la ventana de
    materiales enseñaba « deg» de sufijo, y pasa por `unit_symbol` como Definir soporte.
  - **Los tests no recorrían el camino real en cuatro sitios.** La aserción del error del DXF ya pasaba en 0.1.432
    (`preview_error_text` existía, y el arreglo estaba en `act_import_dxf`). El arranque, el informe y el tornado
    tampoco se probaban por la ventana. `variable_label` no lo probaba nadie. El tornado no comprobaba qué barra era
    de qué variable, ni que estuviera en el menú (regla 3). Y una aserción de F1 aceptaba la etiqueta inglesa. Ahora
    se prueban por el manejador, por el constructor o barra a barra. Los tres tests de Interpretar comparten la
    ventana, y el del título usa la ventana del archivo en vez de una segunda.
- **Cuatro sitios anteriores, con las reglas que esta versión ya tiene, entran aquí por decisión de la propietaria
  en la revisión:**
  - Modificar soporte, Mover soporte y el selector del diagrama de fuerzas decían «1: End Anchored» y «End Anchored
    [Anclado en el extremo]»: pasan por `support_name`;
  - el dato emergente de un soporte decía «modo de rotura: shear»: nombra las opciones por `support_choice_label`;
  - la columna «Tipo» de la Tabla de resultados de Interpretar decía «circle»: pasa por `surface_kind_label`;
  - el texto de respaldo de «Mostrar valores a lo largo de la superficie» empezaba con un título en inglés fuera de
    `tr()`.
  - Los demás anteriores van a D412 (los del núcleo) y a una ficha nueva, D413 (§3).
- **La segunda suite entera dio un fallo,** de mi arreglo: anclé la excepción del error del sistema a «No se pudo
  leer el archivo DXF: [Errno …]», y `test_dxf_messages_v1334` exige que ninguna excepción del censo nombre el DXF
  (v0.1.334 retiró la que eximía ese error). Ahora el marco se ancla sin nombrar el tipo de archivo.
- **Refutadas o fuera de alcance**, con su motivo:
  - aceptar sin tocar nada las etapas de un archivo viejo con «[BC]» deja un paso de deshacer y el resultado
    desfasado: es lo que se decidió (el diálogo lo quita al aceptar), y Aceptar cambia un dato;
  - quedan cuatro literales «Untitled» y «Demo slope» donde ya hay constante: hoy valen lo mismo y lo fijan los
    tests;
  - el censo de árbol de sintaxis no ve las formas con palabra clave, `setSuffix` ni `format_map`, y el vocabulario
    sigue sin «slope» ni «linear» (algún valor castellano los usa sin comillas). Hoy ningún texto real llega por
    ahí: queda dicho.
- **El inglés también cambia,** donde enseñaba un identificador:
  - las cuentas del DXF («External Boundary: 1»);
  - el método de búsqueda («Grid Search»);
  - las celdas y cabeceras de las Tablas de propiedades («friction angle», «Shear»);
  - los nombres de las variables aleatorias («friction angle»);
  - el informe («Non-Circular», «Particle Swarm Search»);
  - la clase de soporte «User Defined», que se lee «User-defined» (lleva su propia clave para ir en masculino en
    castellano);
  - el resumen de Condiciones de contorno («Nodal Flow Rate: 4»);
  - en la ventana, las notas con un campo que ahora declara su tipo («'Non-Circular'», «'Grid Search'», «Monte
    Carlo, Surface Altering», «(composite surface)», «Effective Stress using B-bar», «a circular surface on no weak
    layer»); el agente y la línea de órdenes siguen con el identificador;
  - las listas de procedimientos y de técnicas, unidas por «; »;
  - y el eje del tornado.

## 1. Qué cambia

- **`ogr_gui/labels.py`:**
  - `SEARCH_METHOD`, `SELECTABLE`, `SUPPORT_CHOICES` (desde Definir soporte), `PERMEABILITY_MODEL` (desde Definir
    propiedades hidráulicas), `SURFACE_TYPE`, `SURFACE_KIND`, `DRAWDOWN_PROCEDURE` (desde Ajustes del proyecto) y
    `OPTIMIZE_TECHNIQUE` (desde Optimizar superficies), con sus funciones;
  - `project_label`, `boundary_name` (los nombres que pone el programa), `default_support_name`, `support_name`,
    `variable_label` y `unit_symbol`;
  - `support_type_label` traduce el nombre por defecto de un conjunto.
- **`ogr_gui/main_window.py`:**
  - `_startup_message`, `_dxf_counts` y `_geometry_cleanup_lines`;
  - el filtro de selección, el método de búsqueda, el Visor de información, el título y el menú Ventana, el nombre
    del informe, el barrido de desembalse y la variable más influyente.
- **`ogr_gui/core_messages.py`:** siete tipos nuevos de campo: método de búsqueda, tipo de superficie, tipo
  serializado, el mismo como sustantivo de «una … superficie», procedimiento de desembalse, y listas de procedimientos
  y de técnicas (unidas por «; »).
- **Notas con código** (`ogr_slip2d/note_messages.py`, `setting_messages.py`, `search_note_messages.py`,
  `stat_messages.py`; `ogr_core/project/messages.py`, `ogr_core/dxf/messages.py`): dieciocho campos de trece notas
  declaran su tipo. El inglés de las plantillas no cambia (el agente lo lee igual); la ventana en inglés nombra esos
  valores por su etiqueta (§0). `interpretation.critical_drawings` da el tipo serializado de la superficie que no
  sabe dibujar.
- **Diálogos:**
  - Condiciones de contorno, Tabla de propiedades, Definir soporte (su lista y « °»), gráfica de variable aleatoria,
    Opciones de superficie, Ajustes del proyecto, Optimizar superficies, propiedades hidráulicas;
  - etapas transitorias, con su columna «Condiciones» y `stage_label`;
  - SFAlongSlopeDialog y SensitivityDialog (con `sensitivity_effects`).
- **Interpretar:**
  - el título, el soporte, la sensibilidad, Exportar datos brutos, el tornado nuevo y «Graficar FS a lo largo del
    talud...»;
  - Interpretar agua subterránea, con `stage_entry` y «[CC]».
- **El lienzo:** la descripción emergente y el menú contextual de un soporte. **El puente del agente:** el título.
- **El núcleo**, sin cambiar ningún número:
  - constantes de los nombres por defecto (`DEFAULT_PROJECT_NAME`, `DEMO_PROJECT_NAME`, `DEFAULT_SUMMARY_TITLE`);
  - el informe: el título por defecto en el idioma del lector (venga de donde venga), el tipo de superficie y el
    nombre de la búsqueda por enjambre;
  - `TransientStage.own_bcs` y la nota `own_bcs` del solucionador transitorio, que se guarda con el resultado en el
    `.ogr` (una clave más en las notas de cada etapa).
- **`ogr_gui/i18n`:** treinta y cinco entradas nuevas, y cinco valores cambiados: «Importado — %s», los dos de
  «objeto de enfoque», «SE AUTOINTERSECA» y las dos plantillas del caso de capa débil.
- **La ventana de materiales:** « °» de sufijo, por `unit_symbol`.
- **Censos, cambiados a propósito:**
  - `test_gui_spanish_v1318` lee los operandos de un `or`, cada literal de una concatenación, los campos de un texto
    traducido, los constructores de elementos, los receptores de matplotlib y un condicional medio traducido; tres
    excepciones nuevas, una sustituida («{}: t = {}{}{}» por la de cinco campos) y dos que se van (los títulos con
    nombre por defecto);
  - `test_labels_spanish_v1321` lee más de la pantalla (descripciones de estado, sufijos, textos de edición, listas,
    árboles con sus hijos y figuras con sus marcas, salvo la barra de matplotlib), decide con un vocabulario medido
    sin lo que los valores citan como código, ancla sus excepciones a su marco castellano, ya no da por dato un nombre
    por defecto, y construye los diálogos que el censo no construía;
  - `test_voice_and_terms_v1325` retira «enfoque»; `test_window_english_left_v1293` deja dos títulos;
    `test_dialogs_fit_v1315` usa el informe de limpieza real; `test_chart_dialogs_v170`, la firma nueva;
    `test_shared_test_caches_v1378`, una entrada en `ALLOWED` con su motivo.
- **`tests/test_spanish_paths_v1433.py`,** nuevo.
- **`spec/features/009-sarma-dovelas-no-verticales/`:** las versiones de Sarma, +2.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_spanish_paths_v1433.py`,** 33 tests (25 antes de la revisión): cada sitio por la ventana o el
  diálogo real (el arranque por el constructor, Importar DXF por su manejador, el informe por `act_generate_report`),
  en castellano y en inglés, con cada estático sustituido y restaurado.
  - **Las dos identidades de F2:**
    - cada barra del tornado es el `fos_range` de su variable, con el signo de `is_increasing`: las cifras del
      ranking, leídas barra a barra contra su rótulo, con dos variables de la misma etiqueta y dos del modelo
      nombradas por `variable_label`;
    - el gráfico del talud dibuja exactamente la serie de `interpretation.sf_along_slope`, y su mínimo es el menor
      factor de las superficies válidas, que es el de la crítica.
  - **El censo de F1:** sobre las muestras de los tests de cada catálogo, ningún campo con un identificador queda sin
    tipo.
  - **El inglés del agente y los datos, iguales:** las claves del DXF, el nombre guardado de un contorno, de un
    proyecto y de un conjunto de soportes.
  - **Las reglas nuevas de los dos censos,** comprobadas sobre fuentes propias, con sus controles.
- **Discriminación en el árbol de 0.1.432** (`git archive` de 2f498f6, sin el buscador editable): fallan los 25.
  - Trece fallan por lo que hace el programa: el inglés o el identificador en pantalla, o un censo que no ve su
    fuente.
  - Doce fallan por un nombre que 0.1.432 no tenía, o porque el gráfico del talud no devolvía diálogo. Los mutantes de
    abajo dicen que cada una de esas reglas es la que su test necesita.
- **Mutantes, uno a uno y en memoria.**
  - **Del programa,** nueve, cada uno cazado por los tests de su regla:
    - el método por su identificador;
    - sin los nombres que pone el programa;
    - sin el nombre por defecto de un soporte;
    - el arranque viejo;
    - el tornado sin signo;
    - la etiqueta de la etapa sin limpiar;
    - las cuentas del DXF viejas;
    - el nombre del proyecto sin traducir;
    - y los tipos de campo nuevos sin nombre.
  - **Del censo de árbol de sintaxis,** seis; cada uno hace fallar su autocomprobación. La revisión vio que tres
    reglas más no tenían caso propio (los campos de `tr() % (...)`, `QTreeWidgetItem` y `legend`): ya lo tienen.
  - **De los arreglos de la revisión,** trece, cada uno cazado por su test: la marca de la etapa leída de `bcs`, la
    clase vieja de un soporte, «Definida», el tornado por etiqueta, `variable_label` sin usar, el título del informe
    sin reconocer, el tipo de capa débil como en 0.1.432, la lista unida por comas, el manejador del DXF con el error
    del núcleo, « deg», la lista de Modificar soporte sin `support_name`, el dato emergente con el valor guardado y la
    columna «Tipo» con el identificador.
  - Seis de los doce tests que en 0.1.432 fallaban por un nombre no tienen mutante propio: el del informe PDF, el
    del gráfico del talud y las cuatro comprobaciones de tablas de `labels.py` contra sus enums. Estas cuatro son
    identidades sin Qt: fallan si una tabla y su enum dejan de coincidir.
- **Vecinos:** notas con código, rechazos, etiquetas, español, i18n, gráficas, transitorio, rejilla, Tablas de
  propiedades, soportes, informe, Interpretar, estadística, sensibilidad, DXF, limpieza, reglas de F2, filtro de
  selección, condiciones de contorno, agua subterránea, desembalse, optimización, el inglés de la ventana, voz,
  diálogos, versión, mensajes, menús, notas de la filtración, M4 y deshacer: 1972 casos. La primera pasada dio 1969:
  los tres fallos eran del censo de árbol de sintaxis, cuya excepción para el texto de una etapa en Interpretar agua
  subterránea no tenía el campo nuevo de «[CC]». Tras los dos arreglos de §0, los vecinos de Interpretar agua
  subterránea y de las etapas, 109 de 109.
- **Suite entera con `--jobs 4`:** la primera corrida, antes de la revisión, dio 7290 de 7292, 1 saltado y 1 fallo
  (la memoria de §0), sin fugas ni tramos muertos. La segunda, con los arreglos de la revisión, 7296 de 7298 y un
  fallo (la excepción anclada de §0). **La final, sobre este árbol: 7299 de 7300, 1 saltado, 0 fallos,** sin fugas
  ni tramos muertos; la última serie en verde fue hace 11 commits.
- **Banco, en seco:** D300, D315, D318, D335, D344 y D399, todas CUBIERTO POR TEST. `d411()`, aún sin aplicar al
  verificador, probada dentro de él sin escribir nada:
  - con el árbol vivo, CUBIERTO POR TEST;
  - con el de 0.1.432, SIGUE ABIERTO por lo que hace en los seis puntos que mide:
    - el arranque, «Listo — File → Load Demo Slope…»;
    - el Visor de información, «Demo slope»;
    - la Tabla de propiedades, «cohesion» y «friction angle»;
    - el resumen de condiciones, «nodal_flow: 1»;
    - Definir soporte, «End Anchored  [Anclado en el extremo]»;
    - y dos valores con «enfoque».
- **Revisión adversaria:** cinco lentes (código; F2, «[BC]» y núcleo; tests y changelog; castellano y censos; un
  barrido de lo que no entró), dos escépticos por hallazgo y un crítico de completitud. **Volvió a medias:** de 110
  agentes, 64 chocaron con el límite de uso, entre ellos el crítico y los escépticos de 31 hallazgos.
  - De 52 hallazgos, 21 se votaron: 19 confirmados por los dos escépticos (cuatro de ellos, el mismo de `own_bcs`) y
    2 refutados por los dos (los de §0).
  - Los 31 sin votar los comprobé uno a uno con las sondas de cada hallazgo y el código. Los del diff eran reales y
    están arreglados (§0), salvo los límites que §0 deja dichos. Los anteriores a esta versión van en §3, para la
    propietaria.

## 3. Qué queda

- **D412,** en 0.1.434: los mensajes del núcleo con código (Cambiar ángulo del talud, Simplificar, Expandir /
  contraer, el lector sísmico) y los nombres de deshacer. Por decisión de la propietaria en la revisión, también tres
  sitios anteriores del núcleo y de las notas: el identificador de la norma de diseño («eurocode7_da1c2») en Notas
  del análisis y en el PDF; una variable aleatoria hidráulica nombrada por su clave con UUID; y las unidades de
  tiempo y de permeabilidad que la tabla del informe no conoce («Minutes», «M Day»). Se abre al cerrar D411.
- **D413,** en 0.1.435, abierta por la propietaria en la revisión: cinco cuestiones de diseño anteriores a esta
  versión:
  - si los nombres que el programa pone a un conjunto o a una carga nuevos («Type 1», «… (copy)», «Dist 20.0 kN/m²»,
    «Line 50.0 kN/m») se traducen al enseñarlos, como «Untitled»;
  - la gráfica de una variable aleatoria, que se abre modal;
  - el Gráfico de sensibilidad y el tornado, que dibujan siempre el primer método sin decir cuál;
  - «Graficar FS a lo largo del talud», que llama «Factor de seguridad» al factor de sobredimensionamiento con norma;
  - y el Gráfico de sensibilidad, activo con solo un resultado probabilístico (el tornado ya no).
- El resto de la tanda P10, dos versiones más tarde que antes de D411:
  - D400–D404 en 0.1.436–0.1.440;
  - D408 en 0.1.441, D406 en 0.1.442 y D409 en 0.1.443;
  - D407 y D410 siguen sin versión.
  - Sarma va en 0.1.444–0.1.450.
- **La razón de un soporte que no se puede calcular** sigue en inglés dentro de la frase traducida: es el motivo de
  `SupportEvaluationError`, que la regla de D335 deja como dato (la decisión ya tomada para D412).
- **Prueba a mano, para la propietaria,** con la interfaz en español:
  - el arranque, el Filtro de selección, el Visor de información y Opciones de superficie;
  - Importar DXF con un archivo bueno y con todas las capas en «(ignorar)»;
  - Limpiar geometría, las Tablas de propiedades y Definir soporte;
  - las etapas transitorias, capturando unas condiciones;
  - en Interpretar, «Tornado de sensibilidad...», «Graficar FS a lo largo del talud...», «Exportar datos
    brutos...» y la Tabla de resultados;
  - Modificar soporte, Mover soporte, el diagrama de fuerzas y el dato emergente de un pilote.
