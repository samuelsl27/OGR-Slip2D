# OGR Slip2D v0.1.447

**El bloque «Global Minimums» del informe identifica una polilínea (D424).** Escribía de ella su factor y su área,
y nada que dijera qué superficie era. Ahora, como el informe de la referencia, da el eje de sus momentos si el método
lo guarda, sus dos extremos y, en una sección nueva, «Global Minimum Coordinates», sus vértices. Medido con 0.1.446
(80bf5c6) y el guion de la ficha (`medir_d424.py`), con el informe en inglés:

| crítica | 0.1.446 | ahora |
|---|---|---|
| la polilínea de Ej_1 dibujada a mano, Bishop y Ordinario | «Factor of Safety (FS) 0.9239, Total Slice Area 225.000 m²» | además «Axis Location (82.500, 72.500)», «Left Slip Surface Endpoint (40.000, 50.000)», «Right Slip Surface Endpoint (75.000, 25.000)», y los seis vértices en la sección nueva |
| la misma, Janbu y Spencer | factor y área | factor, los dos extremos y área (sin eje: no lo guardan); y sus vértices |
| la polilínea de Path Search (13 vértices) y la del usuario de D404 (4) | factor y área | eje, extremos, área y vértices |
| un círculo, una compuesta (problema 22) y una capa débil | factor, centro y radio si los tiene, extremos y área | igual, carácter a carácter, y sin sección |

La referencia (`Slide2d_Ej_1_Block_Search.htm`) da por método el eje (82.500, 72.500), los extremos (40.000, 50.000) y
(75.000, 25.000) y «Total Slice Area=225 m2», y después los seis vértices.

**La revisión encontró además** que un encabezado que se queda con su tabla se la llevaba entera a la página
siguiente cuando no cabía: una página con solo su pie antes de los vértices de una polilínea larga y, desde D351
(0.1.417), entre 450 y 640 pt vacíos bajo el primer método de «Slice Data» a partir de unas 48 dovelas. Se arregla en
las dos secciones, por decisión de la propietaria. **Ningún número cambia:** es el texto y la maquetación del
informe. Es la vigésima versión de la tanda P10 y la última del plan aprobado el 2026-11-13.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.446:** `medir_d424.py` da lo mismo que con 0.1.435, salvo el rótulo del resumen de Interpretar
  («Critical surface, defined by the user»), que puso D401 en 0.1.443. El bloque no había cambiado.
- **La regla de los extremos vivía solo en el motor** (`interpretation.slope_intercepts`), y el núcleo no puede
  importarlo. Baja al núcleo palabra por palabra (`ogr_core/geometry/surface_ends.py`, `surface_x_ends`), y la
  preguntan el motor y el bloque del informe para todas las formas (decisión R6 del plan): `surface_ends` añade la y,
  el vértice en una polilínea y `base_y_at` en las demás, que es lo que el bloque escribía.
- **Un mutante enseñó una rama muerta.** El borrador de `surface_ends` giraba una polilínea dibujada de derecha a
  izquierda; el mutante que quitaba el giro sobrevivió, porque `SlipSurface` ordena sus vértices por x al construirse
  (`ogr_slip2d/surface.py`). La rama se quitó.
- **La revisión adversaria (un agente) encontró:**
  - **la página en blanco.** reportlab mete en un solo `KeepTogether` un encabezado que se queda con lo que sigue
    *y* lo que sigue, la tabla entera incluida; si no cabe, salta de página. El encabezado de sección, su regla y el
    del método se quedaban con la tabla de vértices: con la polilínea de 51 vértices y 3 líneas de comentario, la
    página 2 solo llevaba el pie. **Mi test de página no lo veía:** el encabezado quedaba siempre arriba de su página,
    así que «ningún encabezado al pie» no podía fallar, y su premisa (que el encabezado cambiara de página) se cumplía
    precisamente por el salto. El código y este changelog decían «sin agruparla entera», y era falso;
  - **lo mismo en «Slice Data», desde D351.** Medido: el segundo método se iba a la página siguiente con su tabla y
    dejaba 450 pt vacíos con 60 dovelas, 640 con 48 y 514 con 100 (con 40 cabe). Lo leyó la revisión y lo medí;
    por decisión de la propietaria se arregla aquí;
  - que «una sola regla» de extremos no era verdad: el bloque del círculo, la compuesta y la capa débil conservaba su
    copia. Ahora pregunta `surface_ends`, y un test cuenta las llamadas;
  - que la entradilla decía «si el método lo usó»: Spencer y GLE usan un punto de referencia y no lo guardan. Es «si
    lo guarda»;
  - el término: el menú dice «Definir eje de momentos», y por decisión de la propietaria la fila es «Posición del eje
    de momentos»;
  - huecos del test, todos cubiertos: los vértices de cada método (con tres métodos en un Path, Spencer tiene otra
    polilínea), el eje del Ordinario, y una copia literal de la regla que una comparación de valores no veía. Un caso
    de primer tramo vertical que ninguna puerta produce (`checked_points` lo rechaza) se quitó.
- **Caminos equivocados en el test de página**, tres: con los 13 vértices de Path la tabla nunca se parte; el primer
  barrido (0 a 7 líneas) no ponía ningún encabezado al pie; y la primera versión del arreglo reconocía los encabezados
  por su estilo, así que sobre 0.1.446 no encontraba ninguno y pasaba en vacío (allí un `LCActionFlowable` de altura
  cero abría la página). Cada posición del barrido y el caso de 82 dovelas salen de una medida.
- **La capa débil guarda su eje** (`moment_axis`) y no lleva la fila: la decisión de la propietaria es para una
  polilínea. El Ordinario también guarda el suyo, como la referencia, que lo da para él.
- **La referencia lista X e Y** en «Global Minimum Coordinates»; OGR añade el número del vértice, como decía el plan.

## 1. Qué cambia

- **Núcleo** (`ogr_core/geometry/surface_ends.py`, nuevo): `surface_x_ends` (la regla de `slope_intercepts`, literal),
  `polyline_points` (los vértices de una polilínea, o None) y `surface_ends`. `interpretation.slope_intercepts` la
  pregunta.
- **El bloque** (`ogr_core/report/report_generator.py`): para una superficie con `polyline`, tras el factor, «Axis
  Location» cuando `details` trae `moment_axis` y los dos extremos con el formato de siempre; para las demás, los
  extremos de `surface_ends`, con el mismo texto.
- **La sección «Global Minimum Coordinates»**, tras el bloque y solo si algún método tiene una polilínea por crítica:
  por método, su encabezado y una tabla Vértice / X / Y que repite su cabecera al partirse y cabe en el marco.
- **Las tablas largas** («Global Minimum Coordinates» y «Slice Data»): el encabezado del método ya no se queda con su
  tabla (`h_table_method`, el mismo nombre de estilo `OGRMethod`), y un `CondPageBreak` de 35 mm (`table_room`) antes
  de él, o antes de la sección, lo saca del pie de página.
- **Español:** «Posición del eje de momentos», «Coordenadas de los mínimos globales» y «Vértice».

## 2. Qué se probó

- **`tests/test_report_global_minimums_v1447.py`** (20 casos, unos 5 s: los barridos maquetan 16 informes, y la
  cabecera lo dice):
  - **la referencia publicada** de la polilínea de Ej_1 (el modelo de `test_slide_validation_ej1` y la superficie de
    `test_noncircular_validation_v192`, sin tocarlos), sus números escritos en el test: Bishop y el Ordinario con eje,
    extremos y área; Janbu y Spencer sin eje; los seis vértices de cada método; y en castellano;
  - una polilínea de la búsqueda (Path, 13 vértices), y tres métodos con sus propios vértices;
  - **los controles:** el círculo, la capa débil y la compuesta, con sus bloques de 0.1.446 carácter a carácter
    (`_V1446`, medidos con ese árbol) y sin la sección;
  - **los extremos:** el informe y el motor preguntan al núcleo (contado con un espía); una polilínea dibujada al revés
    da los mismos; y las otras formas, los del bloque;
  - **las reglas de página**, con la polilínea de 51 vértices en dos barridos medidos del resumen y con «Slice Data» a
    60 y 82 dovelas: ninguna página con solo su pie, ningún encabezado de tabla que abra página dejando su sitio
    detrás, ninguno al pie, y la tabla que se parte con su cabecera y cabe en el marco.
- **Discriminación:** en el árbol de 0.1.446, sin el buscador editable, fallan 14 de 20; entre ellos, «Slice Data» deja
  405 pt detrás. Pasan los tres controles, una premisa y las dos reglas de página que allí no tienen sección que mirar.
- **Mutantes** (`mutants_d424.py`, en el banco): 14, todos muertos, con los de la maquetación (el encabezado que se
  queda con su tabla, sin `CondPageBreak` antes del encabezado o de la sección, «Slice Data» como antes) y los de la
  regla única (la copia del motor, literal o no, y la del bloque). La cabecera cuenta el mutante que se quitó por
  equivalente.
- **Vecinos**, con los patrones `report user_polylines noncircular spanish_paths core_layering f3b_ops interpret
  chart_dialogs spanish_texts i18n voice_and_terms shared_test_caches` (cada uno comprobado por separado con `--list`):
  550 casos en verde en 33 archivos.
- **La suite entera** con `--jobs 4`, tras los arreglos de la revisión: **7600 casos, 7599 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (25 commits desde la última).

## 3. Qué queda

- **El plan de 0.1.445–0.1.447 está TERMINADO.** Sigue en P10 D404 (0.1.448), que dirá de quién es la crítica que este
  bloque ya identifica; al cerrar esta ficha se reescribe la salida esperada del REPRODÚCELO de su prompt.
- **Reportado y sin tocar:** el eje sale solo con Bishop y el Ordinario, que lo guardan; la referencia lo da para todos
  los métodos.
