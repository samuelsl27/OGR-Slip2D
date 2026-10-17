# OGR Slip2D v0.1.321

**Lo que llegaba a la pantalla por variable sale en castellano: las etiquetas
del núcleo, las tablas de la interfaz y los identificadores que se enseñaban
tal cual. Además, ninguna clave del diccionario está escrita dos veces (D300,
tablas e identificadores; D240).** Quinta versión de la tanda P8h. D240 se
cierra; D300 se cierra en 0.1.322, con los soportes.

## 0. Lo que se encontró

- **El hueco que ningún test de AST puede ver.**
  - El test de diálogos de 0.1.320 encontró una tabla de etiquetas que
    llegaba a Qt por subíndice.
  - Se midió de dos formas:
    - en pantalla, la ventana y los 44 diálogos del censo de D293, abiertos
      en castellano, enseñaban 95 textos con aspecto inglés;
    - en el código, un agente de solo lectura revisó los 158 sitios donde una
      llamada visible recibe una variable. 57 ya traducían, 56 eran datos y
      44 no pasaban por `tr()`, repartidos en 37 tablas de origen. Salieron
      además 11 casos que el escáner no ve: f-strings, `.title()`,
      condicionales.
  - En total, unos 300 textos. Por decisión de la propietaria se reparten
    así:
    - esta versión: la interfaz y los identificadores;
    - 0.1.322: los soportes;
    - una ficha nueva, D314: los mensajes del núcleo.
- **Tres listas venían del núcleo sin pasar por `tr()`.**
  - **Las filas de *Definir materiales*** se rotulaban con la clave
    («cohesion:», «mb:»). El núcleo guarda para cada una de las 48
    descripciones distintas su texto (`PARAMETERS = {clave: (defecto,
    unidad, descripción)}`), y solo lo enseñaba la ayuda.
  - **El nombre del modelo de resistencia** (`DISPLAY_NAME`).
  - **Las texturas de *Elegir…***, que son las claves de `MATERIAL_LIBRARY`
    y contrato del API.
- **Identificadores en pantalla, en cualquier idioma.** `addItem(m.value, m)`
  enseñaba el valor guardado:
  - `grid_total_head` y `fea_steady`, en el método de agua subterránea;
  - `water_table` y `none`, en la presión intersticial;
  - `mo` y `m/day`, en las unidades;
  - `bishop_simplified`, en la ventana de estadística y en el retroanálisis.

  Además, el nombre de los métodos vivía en tres tablas que no coincidían. La
  de *Interpret* tenía seis de los nueve, y enseñaba el identificador de
  Corps of Engineers y de Lowe-Karafiath.
- **Tablas de la interfaz pasadas por variable:**
  - los menús contextuales del lienzo;
  - las condiciones de contorno y sus lados;
  - la orientación de las cargas;
  - los modos de la grieta;
  - los tipos de contorno;
  - las páginas de *Project Settings*;
  - las distribuciones;
  - los campos de *Interpret Groundwater*;
  - los títulos y ejes de nuestros gráficos;
  - las tres tablas de la calculadora de Hoek-Brown (GSI, D y las 30
    litologías de mi).
- **Las ayudas de materiales y cargas** salían de `tooltip_html()`, que el
  núcleo escribe en inglés para cualquier llamador.
- **Las ayudas de datos** enseñaban `DistributedLoad` (el nombre de la clase,
  porque una carga no tiene nombre por defecto) y `orientation:
  normal_to_boundary`.
- **El heurístico del test de pantalla tiene un límite.** Busca palabras
  inglesas de una lista, y no vio las 30 litologías («Granite»,
  «Sandstone»), que no están en ella. Salieron leyendo la tabla.
- **D240: 20 claves estaban escritas dos o tres veces**, 22 entradas
  sobrantes.
  - Una clave repetida en un literal es Python válido, y gana la última sin
    decir nada.
  - Así «Add Grid» era «Añadir malla» y luego «Añadir rejilla», y «None» era
    «Ninguno», «Ninguna» y «Ninguno».
- **`_UNWRAPPED_BUDGET` de `test_i18n_coverage_v141` era 210** con un
  recuento real de 9, así que no podía fallar.
  - Ninguno de los nueve es texto de interfaz: cinco son el separador de un
    `"\n".join(...)`, tres son los símbolos de Hoek-Brown y uno es la lectura
    de coordenadas.
  - Además, una comprobación fijaba la constante (`== 210`) en vez del
    recuento.
  - **Había dos copias más de ese 210,** en `test_block_search_action_not_modal_v1167`
    y `test_add_surface_three_points_v1168`. Fijaban que su versión no
    movía el presupuesto, y las cazó la primera suite de esta versión (la
    búsqueda solo miró `test_i18n_coverage_v141`). Pasan a `<= 210`: lo que
    sigue valiendo es que el presupuesto solo baja.
- **Un test dejaba de medir.** `test_partial_method_loss_v1170` leía el
  **texto** del combo de estadística como identificador. Con nombres en el
  combo, su `_MID not in ids` habría pasado siempre, y su `index(_MID)` habría
  reventado. Ahora lee el dato.
- **`QMenu.exec` no se puede sustituir en la clase.** En este PySide6 la
  asignación se ignora, y un menú emergente bloquea para siempre sin
  pantalla. El test de los menús del lienzo los lee con un temporizador que
  corre dentro del bucle del menú y lo cierra. Lleva un tope de reintentos,
  para que un menú que no aparece no cuelgue la suite.
- **Dos incoherencias de términos, que no se tocan aquí:**
  - «Water Pressure Grid» se traduce «Malla de presiones de agua», aunque no
    es de elementos finitos;
  - «Pressure Head» es «Cabeza de presión», mientras que la ayuda de Hu de
    0.1.320 dice «altura de presión».

  Las etiquetas nuevas usan los términos que ya tenía el diccionario.

## 1. Qué cambia

- **`ogr_gui/labels.py` (nuevo)** es un solo sitio para el nombre de cada
  identificador guardado:
  - los métodos LEM;
  - el tipo de presión intersticial;
  - el método de agua subterránea;
  - la orientación y la distribución de las cargas;
  - los tipos de contorno;
  - las unidades de tiempo y de permeabilidad;
  - las claves de parámetro.

  Cada tabla guarda la etiqueta inglesa, y las funciones devuelven
  `tr(etiqueta)` al llamarlas. **El valor guardado no cambia:** el dato de
  cada combo sigue siendo el enum o el identificador. Sustituye las tres
  tablas de nombres de método.
  - **Donde se enseñaba un identificador, el inglés también cambia:** «Water
    Table», «Finite Element: Steady State», «Bishop Simplified». Es lo que se
    buscaba.
  - **En el resto, el inglés queda idéntico.** Las ayudas de datos siguen
    diciendo «unit weight», «friction angle» o «EXTERNAL», y el castellano
    les llega por `tr()`.
- **Las filas de *Definir materiales*** leen la descripción del núcleo,
  traducida (decisión de la propietaria): «Cohesión efectiva c'», «Ángulo de
  rozamiento efectivo φ'»…
  - La ayuda lleva la clave y la unidad («cohesion [kPa]»), para quien
    escriba un guion.
  - Los editores siguen indexados por clave.
- **Los nombres de los modelos de resistencia** pasan por `tr()` en el combo,
  las reglas del anisótropo generalizado, el rótulo de las funciones, las
  ayudas de datos, la tabla de propiedades y el panel de dovelas.
- ***Elegir…*** enseña las texturas traducidas y devuelve la clave inglesa.
- **Las tablas de la interfaz pasan por `tr()` donde se enseñan:**
  - las claves que son también datos (los lados del contorno, las páginas de
    *Project Settings*, los indicadores de la leyenda) se traducen solo en
    la llamada visible;
  - los sistemas de unidades y su resumen;
  - las guías de la calculadora de Hoek-Brown.
- **Las ayudas de materiales y cargas del lienzo** las compone la interfaz con
  `tr()`. `tooltip_html()` se queda para el API.
- **Las variables aleatorias se enseñan traducidas** (decisión de la
  propietaria).
  - La etiqueta guardada en el `.ogr` no se toca: la visible conserva el
    nombre tal como está guardado y traduce el parámetro, por ejemplo
    «Clay — ángulo de rozamiento».
  - Una etiqueta que no tiene la forma que escribe el núcleo se enseña tal
    cual.
  - Las de soportes, en 0.1.322.
- **248 claves nuevas con su castellano:**
  - 74 de etiquetas del núcleo y texturas;
  - 174 de tablas, identificadores, litologías y textos sueltos.

  Las que se escriben igual en castellano no llevan entrada: Spencer, GLE /
  Morgenstern-Price, Corps of Engineers (nombre propio del método, decisión de
  la propietaria) y los símbolos de unidad. «Hyperbolic» ya era clave, por la
  ley de los soportes («Hiperbólica»), y se queda.
- **D240:** se quitan las 22 entradas sobrantes y cada clave conserva el texto
  que ya ganaba. Medido: el diccionario cargado no pierde ni cambia ninguna
  entrada.
- **`test_i18n_coverage_v141`:** `_UNWRAPPED_BUDGET` baja de 210 a **9**, y la
  comprobación fija el recuento.

## 2. Tests

`tests/test_labels_spanish_v1321.py` (nuevo), 19 casos:

- **Las etiquetas del núcleo tienen castellano:** toda descripción, todo
  nombre de modelo salvo los epónimos, y toda textura, sin dos iguales.
- **D240:** ninguna clave aparece dos veces en el literal del diccionario,
  leído con el AST, y las dos que discrepaban conservan el texto que ganaba.
- ***Definir materiales* en castellano:** cada fila de cada modelo es su
  descripción y su ayuda empieza por la clave, y el combo nombra cada
  modelo. Control: en inglés, las descripciones tal cual.
- ***Elegir…* en castellano:** «Franco arenoso» carga los valores de «Sandy
  loam», los mismos que eligiéndolo en inglés.
- **`TestNothingOnScreenReadsEnglish`** abre en castellano la ventana, los
  44 diálogos del censo e *Interpret*.
  - Falla ante cualquier texto con aspecto inglés que no esté en
    `SHOWN_EXCEPTIONS`, cada una con su razón, y ante una excepción
    fantasma.
  - Las excepciones son:
    - el mensaje del núcleo al leer un DXF (D314);
    - Corps of Engineers;
    - la ayuda «clave [unidad]»;
    - los símbolos `in` y `min`;
    - lo de soportes, marcado «0.1.322».
  - La barra de navegación de matplotlib no la ve este test. Queda en inglés
    por decisión de la propietaria.
- **`ogr_gui.labels`:**
  - cada miembro de cada enum tiene etiqueta;
  - cada etiqueta tiene castellano o se escribe igual, con una lista exacta;
  - los nombres de método son los del registro del motor.
- **Los menús contextuales del lienzo en castellano:** vértice, contorno,
  soporte y dibujo, con su control en inglés.
- ***Project Settings*:** las páginas, el sistema de unidades, el tiempo, los
  métodos y el método de agua subterránea. En ningún idioma el texto de un
  elemento es su identificador.
- **El combo de presión intersticial**, en castellano y en inglés.
- **La ventana de estadística** nombra el método.
- **Las variables aleatorias:** la etiqueta visible en siete casos, y la
  guardada intacta.
- **Las ayudas de datos** de material, contorno y carga, con su control en
  inglés.

**Con el código de 0.1.320 fallan 18 de los 19 casos.** El que pasa es el
control de que «Add Grid» y «None» conservan el texto que ya ganaba, igual en
los dos árboles a propósito. Los dos tests modificados, `test_i18n_coverage_v141`
(recuento exacto 9) y `test_partial_method_loss_v1170` (lee el dato), pasan en
los dos árboles. Se corrió sobre un `git archive` de 0.1.320, sin el buscador
editable.

## 3. Verificación

- **Los tests vecinos,** antes de la suite: 1493/1493 en 93 archivos.
  - Son materiales, *Elegir…*, retención e hidráulico, la tabla de
    propiedades, las ayudas de datos, *Interpret*, los anisótropos y las
    funciones, los tamaños de diálogos, los menús y la ventana en los dos
    idiomas, estadística y variables aleatorias, *Project Settings*, cargas,
    grieta, contornos, lienzo, leyenda, retroanálisis, gráficos, la
    calculadora, sismo, unidades, agua, la identidad de soportes, deshacer e
    i18n.
- **La primera suite entera dio un fallo:** las dos copias del 210 de §0. Se
  paró, se corrigieron y se volvió a lanzar.
- **Suite entera:** 6138/6138, `EXIT=0`, 57 min.
- **Banco:** `verificar_cierres.py` entero, 60 comprobaciones, D240 **CUBIERTO
  POR TEST** y 0 bajadas.
  - Instantánea `Evaluaciones/0.1.321`, D240 retirada y podada de P1, los
    prompts regenerados (34, con D314 nueva).
  - Las auditorías dan 0 ERROR, en la raíz y en el 02.
- **Ningún número del motor cambia:** es texto de pantalla, y el `.ogr`, las
  claves y el API no cambian.

## 4. Banco

- **D240 se cierra:** ninguna clave repetida, medido con el AST.
  **CUBIERTO POR TEST**. Se poda de P1 y se tacha en su fila.
- **D300 sigue abierta,** hasta los soportes de 0.1.322.
- **Nace D314 (P8):** los mensajes del núcleo que la interfaz enseña en
  inglés.
  - Son las 25 razones del motor en *Interpret* (`methods/base.py` dice que
    la interfaz las traduce, y no lo hace) y los 7 problemas del DXF.
  - Por decisión de la propietaria, con códigos estables que la interfaz
    traduce. Va después de P8h.

## 5. Pendiente

- **0.1.322:** los soportes. Son 9 nombres, 9 descripciones, 54 descripciones
  de parámetros, 36 etiquetas de fila, 9 pestañas, y la aplicación y la
  orientación; también sus partes en las ayudas de datos y en las variables
  aleatorias. Con ellos se cierra D300.
- **La leyenda de sensibilidad de la ventana de estadística** enseña la
  etiqueta guardada del barrido, que no lleva el tipo ni el parámetro.
- **D314,** después de P8h.
- **A mano, en la tercera prueba de la interfaz,** con Español guardado:
  - *Definir materiales* con un modelo de varios parámetros;
  - *Elegir…*;
  - *Project Settings*;
  - los menús del lienzo;
  - la calculadora de Hoek-Brown;
  - las variables aleatorias.
