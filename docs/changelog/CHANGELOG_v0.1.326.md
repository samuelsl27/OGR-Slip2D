# OGR Slip2D v0.1.326

**Lo que se veía mal: la fila crítica en el tema oscuro, los nombres de página cortados de *Ajustes de
proyecto* y las cajas aplastadas de *Opciones de superficie* (D319, D320, D321). Además, todo lo que
encontró el censo de diálogos al mirar más que botones.** Tercera versión de la tanda P8i.

## 0. Lo que se encontró

### Los tres defectos del informe

La tercera prueba de la interfaz (§3 y §4 del informe) vio tres cosas mal dibujadas. Medida la causa
de cada una:

- **D319, la fila crítica.**
  - El panel de resultados pintaba la fila del factor mínimo con `Qt.yellow` de fondo y dejaba la tinta
    al tema: en el oscuro, texto claro sobre amarillo.
  - La franja de resultado anterior, justo encima, ya usaba una pareja fija legible en los dos temas.
  - Otras dos tintas fijas en listas se leían en un solo tema: el gris de las capas sin entidades de
    *Importar DXF* (`Qt.darkGray`, casi invisible en oscuro) y el rojo de los problemas del DXF
    (`Qt.red`).
  - **La cabecera desactivada** de la tabla de etapas del transitorio tomaba el gris común de lo
    desactivado, `#7a7a7a`, sobre el `#404040` de las cabeceras oscuras: 2,4:1.
- **D320, *Ajustes de proyecto*.**
  - La lista de páginas tenía `setMaximumWidth(180)`, y era la única parte del diálogo que podía ceder.
    Medido sin pantalla, en castellano, enseñaba **56 px** de nombres que piden 246.
  - La página *Norma de diseño* cortaba su última nota por abajo: las páginas no se desplazaban.
  - **De paso:** el constructor añadía la pila de páginas al layout, añadía un layout vacío, sacaba los
    dos con dos `takeAt(1)` y montaba otro contenedor. El layout vacío quedaba huérfano.
- **D321, *Opciones de superficie*.**
  - Fijaba `setMinimumSize(460, 520)`. En una ventana, un mínimo explícito **sustituye** al que impondría
    su layout, que era de 939 × 725 px, así que el diálogo abría —y se podía arrastrar— más pequeño que
    sus páginas. La de búsqueda por bloques salía con cajas de 2–3 px de alto y los grupos de ángulos
    vacíos.
  - El subtítulo de la cabecera no ajustaba línea (911 px), y tampoco la fórmula hiperbólica de
    *Definir materiales*.

### Lo que encontró el censo al mirar más que botones

El censo de D293 (`test_dialogs_fit_v1315`) solo medía botones, y solo al tamaño mínimo. Ampliado a
etiquetas, casillas, cajas y listas, al abrir **y** al mínimo, encontró en **13 diálogos más** dos
defectos que la prueba no había mirado. Por decisión de la propietaria, se corrigen en esta misma
versión:

- **Una nota con ajuste de línea pide más altura cuanto más estrecha es la ventana, y Qt no suma esa
  altura al mínimo de una ventana.** El layout calcula su mínimo con el texto en las menos líneas
  posibles. Cuando la ventana es más estrecha, la nota ocupa más líneas y le quita la altura a lo demás.
  Medido con `totalHeightForWidth`, en los 13 la altura que necesita el layout a su ancho mínimo era
  mayor que la mínima de la ventana:
  - **al abrir:**
    - *Escalar contorno* (226 px de los 286 que pide a su ancho; las cajas a 13 px de 25);
    - *Añadir rejilla* (480 de 520; cajas a 21 px);
    - *Opciones de forzado* (la nota de las tolerancias, a 24 px de los 89 que necesita);
  - **solo al encogerlos:** *Exportar DXF* (su nota, a 98 de 164), *Definir soporte*, *Definir
    resistencia* del desembalse, *Expandir / contraer*, *Calculadora de parámetros*, *Simplificar
    contorno*, el diagrama de fuerzas del soporte, las etapas del transitorio, el panel de notas del
    análisis y el de problemas del DXF.
  - **Lo causó en parte D293:** la introducción de *Añadir rejilla* pasó a ajustar línea en 0.1.315 para
    que el diálogo dejara de medir 1616 px. Además, *Añadir rejilla* fijaba `setMinimumSize(380, 360)`
    por debajo de su layout (416 × 460): es el mismo defecto que D321.
- **Dos listas que cortaban su texto al abrir:**
  - *Variables aleatorias*, con «Silty clay — cohesión» en 186 de sus 340 px;
  - *Definir soporte*, con «Type 1  [Anclado en el extremo]» en 311 de 324. La columna tenía un máximo
    de 220 px, o el ancho de sus botones (D293).
- **Las casillas largas fijaban el ancho de su diálogo:** una `QCheckBox` no parte su texto.
  - «Anclajes: el coeficiente de acciones permanentes en la tensión efectiva…» medía 740 px en
    castellano, y «Fuente única…» 617, las dos en *Norma de diseño*.
  - «Superficies compuestas (la superficie de rotura sigue la base del contorno exterior)» medía 716, en
    *Opciones de superficie*.

### Tres caminos equivocados al arreglarlo

- **El primer filtro de altura guardaba la ventana en un atributo, y la ventana guardaba el filtro.**
  - El recolector de basura rompió ese ciclo vaciando los atributos del filtro mientras los objetos de
    Qt seguían vivos.
  - El filtro reventó con `'_WrappedHeight' object has no attribute '_window'`, y con él un `KeyError` de
    matplotlib en el diagrama de fuerzas.
  - Es la misma familia que el aborto de D310 (ciclos de objetos de Qt que recoge el recolector). La
    versión final no guarda ninguna referencia Python en ningún sentido.
- **La primera `WrappingCheckBox` no cambiaba nada:** el mínimo de *Ajustes de proyecto* seguía en
  1334 px.
  - Una casilla lleva por defecto la política horizontal `Minimum`, que hace de su `sizeHint` lo menos
    que se le puede dar, sea de una línea o no.
  - Con `Preferred`, baja a 1258.
- **La segunda partía su texto y se quedaba en una línea.**
  - En *Opciones de superficie*, «Superficies compuestas…» tenía 549 px de ancho y 20 de alto, de los 35
    que pedían sus dos líneas. Lo vio el censo.
  - La política vertical de una casilla es `Fixed`, y un layout nunca da a un elemento `Fixed` más que
    su `sizeHint`, que era la altura de una línea.
  - Una etiqueta con ajuste de línea es `Preferred` en los dos sentidos, y es lo que lleva ahora la
    casilla.

## 1. Qué cambia

- **D319:**
  - la fila crítica lleva una pareja fija, `CRITICAL_ROW_BACKGROUND = #fff1c2` y
    `CRITICAL_ROW_INK = #5a3b00` (9,0:1), como la franja de resultado anterior;
  - las tintas de *Importar DXF* y del panel de problemas siguen el tema (`theme_color("muted")` y
    `theme_color("error")`);
  - el tema oscuro da a la cabecera desactivada una regla propia, `#a8a8a8` (4,4:1); el resto de lo
    desactivado conserva su gris.
- **D320:**
  - la lista de páginas se fija al ancho de su elemento más largo (`list_width`, 189 px en castellano),
    sin barra horizontal;
  - cada página va en un `VerticalScrollArea`, y `pages` sigue guardando la página misma;
  - las dos casillas largas de *Norma de diseño* parten su texto;
  - el diálogo abre con `open_at_content_size`, y el layout se monta una sola vez.
- **D321:**
  - *Opciones de superficie* deja de fijar mínimo y tamaño, y abre con `open_at_content_size`;
  - las opciones van en un `VerticalScrollArea`, con los botones siempre a la vista;
  - el subtítulo, «Superficies compuestas…» y la fórmula de *Definir materiales* parten su texto.
- **`ogr_gui/dialog_size.py`, tres piezas nuevas:**
  - **`hold_wrapped_height(window)`:** un filtro de eventos que, al mostrarse la ventana y cada vez que
    su layout se recoloca, sube su altura mínima a la que pide el layout a su ancho mínimo, donde el
    texto que se parte ocupa más líneas.
    - Al reaplicarse con cada recolocación, sigue al contenido (una página que cambia, una fila que
      aparece). Un mínimo fijado una sola vez tendría el defecto de D321.
    - Lo llaman los 13 diálogos, y también `open_at_content_size`, que además abre a la altura que pide
      el texto al ancho de apertura.
  - **`WrappingCheckBox`:** una casilla que parte su texto al ancho que le dan y pide la altura que este
    necesita, como una etiqueta con ajuste de línea.
    - Conserva `text()`, el estado, la ayuda y el clic en todo el texto.
    - Pide como mucho 80 caracteres medios de ancho (el límite de `QLabel` para texto que se parte) y
      como poco 30.
  - **`list_width(view)`:** lo que necesita una lista para enseñar entero su elemento más ancho. La usan
    la lista de páginas y las dos listas.
    - En *Definir soporte*, la lista se reajusta con lo que escribe el programa: al crear, duplicar o
      cambiar de tipo.
    - Un nombre que escribe el usuario no la reajusta, porque el diálogo se ensancharía a cada tecla.
      Cada elemento lleva su texto entero como ayuda.
- **Resultado:**
  - *Ajustes de proyecto* tiene un mínimo de 1258 px: era 1189 en 0.1.325, más la lista de páginas
    entera y la barra de las páginas.
  - *Opciones de superficie* tiene un mínimo de 804 px, frente a los 939 que pedía su layout.
  - Lo que queda lo fija la página *Avanzado* (1023 px). Cabe en 1366 y no se toca.

## 2. Tests

- **`tests/test_dialogs_fit_v1315.py`, ampliado.** El censo de los diálogos mide, al tamaño con el que
  abre cada uno **y** a su mínimo, en castellano y en los dos temas, además de los botones:
  - una etiqueta o casilla sin ajuste de línea más estrecha que su texto;
  - una etiqueta o casilla que se parte y tiene menos altura de la que su texto necesita a su ancho;
  - una caja numérica o un desplegable más bajos que su propio mínimo;
  - una lista cuyo elemento más ancho no cabe.
- **`tests/test_dialogs_fit_more_v1326.py`** (nuevo):
  - *Ajustes de proyecto* enseña entero el nombre de página más largo, sin barra horizontal y en los dos
    temas, y cada página se desplaza;
  - el mínimo de *Opciones de superficie* es el de su layout, y en ninguna de sus páginas, ni al abrir
    ni al mínimo, hay una caja más baja que su mínimo;
  - la pareja de la fila crítica pasa 4,5:1, y la fila la lleva en todas sus celdas (control: la
    segunda fila conserva los colores del tema);
  - la cabecera desactivada del tema oscuro pasa 4,0:1 sobre el fondo de las cabeceras;
  - las dos listas DXF no tienen tinta fija;
  - `WrappingCheckBox` pide más líneas cuanto más estrecha es, su mínimo baja de la mitad de una línea,
    conserva su texto y se marca con un clic en su última línea; control: una `QCheckBox` no parte;
  - el filtro de altura y su ventana no se guardan el uno al otro en Python, una segunda llamada no
    añade otro, y una nota que se parte queda entera al ancho mínimo de su ventana.

**Con el código de 0.1.325 fallan 11 de los 12 casos nuevos o ampliados.** El control (una
`QCheckBox` normal no parte su texto) pasa en los dos árboles, y los cuatro casos viejos del censo
también. Se corrió sobre un `git archive` de 0.1.325, sin el buscador editable.

## 3. Verificación

- **Los dos archivos de diálogos**, 16/16. Pasaron a la primera salvo un umbral mío, «el mínimo baja de
  la mitad de una línea», que dependía de la fuente del runner; ahora el test pide menos de una línea.
- **Los vecinos**, 1948/1971 en la copia de trabajo.
  - 22 de los fallos eran de la copia: le faltaba la carpeta `examples/`, que importa
    `test_user_surfaces_v1157`. Repetido con ella, pasa entero.
  - El otro fallo era el de la casilla en una línea (§0); corregido, los 17 archivos afectados dan
    335/335.
  - Son los diálogos, ajustes de proyecto, superficie, rejilla, soportes, variables aleatorias,
    contornos, desembalse, calculadora, forzado, DXF, notas, transitorio, hidráulica, resultados,
    temas, castellano, norma de diseño, superficies compuestas, búsqueda por bloques, versión y
    traducciones.
- **Suite entera:** 6174/6174, `EXIT=0`, 104 min.
  - Es más que los 78 de 0.1.325.
  - Los dos archivos de diálogos tardan 21 s (el censo) y 14 s (el nuevo), cronometrados uno detrás
    de otro sin nada más corriendo; en 0.1.325 el censo tardaba 34 s.
  - El resto de la suite no cambia en esta versión. No se ha medido más.
- **Banco:**
  - `verificar_cierres.py` entero: 68 comprobaciones, D319, D320 y D321 **CUBIERTO POR TEST** y 0
    bajadas;
  - instantánea `Evaluaciones/0.1.326`, las tres fichas retiradas y podadas de P8;
  - prompts (42);
  - auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** es maquetación y color.

## 4. Pendiente

- **D322–D330** (resto de P8i).
- **A mano, en la cuarta prueba de la interfaz:**
  - el tema oscuro con resultados;
  - *Ajustes de proyecto*, *Opciones de superficie*, *Escalar contorno* y *Añadir rejilla* a su tamaño
    inicial y encogidos;
  - el clic sobre una casilla que se parte.
