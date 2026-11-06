# OGR Slip2D v0.1.432

**Con la interfaz en español, los textos que nombra esta versión ya salen en español, por una regla en
`ogr_gui/labels.py`. Los censos ven ahora los cuatro caminos por los que llegaban sin verse, y las formas retiradas se
buscan también con mayúscula (D399).** No es todo el inglés que queda: la revisión encontró unos veinte sitios más,
anteriores y por otros caminos, y la propietaria abrió D411 para ellos, en 0.1.433.
- **Lo que preveía la ficha:**
  - dos mensajes del lienzo salían en inglés: «Need at least 3 distinct points to close a boundary.» (Intro en un
    contorno exterior de dos vértices) y «Drawing cancelled.» (Esc a mitad de un dibujo);
  - la descripción emergente de Añadir rejilla estaba en la segunda rama de un condicional, sin `tr()`;
  - tres valores empezaban por «Superficie(s) de deslizamiento», la forma retirada en D318: la descripción emergente
    de una superficie en el lienzo (dos) y la de las tres acciones de los círculos dibujados a mano. Pasan a «de
    rotura».
- **Lo que apareció al escribir el test, y entra aquí por decisión de la propietaria:** tras dibujar CUALQUIER contorno,
  la barra decía «Añadido External Boundary con 6 vértices». Son 16 sitios donde un campo de un texto traducido se
  rellenaba con inglés:
  - el nombre que el contorno guarda por defecto, que es el nombre inglés de su tipo:
    - en Eliminado, Copiado y Movido (cinco mensajes);
    - en el título de Editar coordenadas y en la lista de Elegir contorno;
    - en la descripción emergente del contorno y en la cabecera de su menú contextual;
    - en el combo de líneas piezométricas del diálogo de la grieta;
  - el `display_name` del tipo en Añadido y en Convertido;
  - el identificador del modo de la grieta («Grieta de tracción: percent_filled») y el del tipo de foco
    («1: point (…)»);
  - dos descripciones emergentes del diálogo de la grieta, que iban por `setItemData` sin `tr()`.
- **Una regla para todos:**
  - `ogr_gui.labels.boundary_label` es la que `MainWindow._boundary_label` aplicaba solo a Escalar y Rotar: el nombre
    que dio el usuario, o si no el de su tipo en el idioma de la interfaz;
  - con ella, dos etiquetas nuevas (los tipos de foco y los niveles de agua de la grieta);
  - y la de las superficies de agua, que pasa del diálogo de materiales a `labels`: una línea piezométrica se llama
    igual en los dos diálogos.
- **Por decisión de la propietaria,** también en esta versión:
  - **«contorno» lleva el género:** «Contorno añadido: Línea de desembalse, con 2 vértices». Antes, «Añadido Línea de
    desembalse» no concordaba con los cinco tipos femeninos;
  - **«[objeto desactivado]»,** por la misma razón, detrás de «Ventana de foco» y «Línea de foco»;
  - **el nombre inglés de cualquier tipo cuenta como nombre por defecto,** no solo el del propio. Convertir contorno
    desde el menú contextual deja el nombre del tipo anterior, y un nivel freático convertido decía «Contorno eliminado:
    Material Boundary». Lo demás de ese camino va a D410;
  - **el singular** para el contorno de un solo vértice (un punto de búsqueda por bloques) y para el punto de foco:
    «con 1 vértice», «(1 vértice)», «(1 punto, …)».
- **Ningún número cambia.**

Es la quinta versión de la tanda P10. **La spec 009 (Sarma) se renumera +1, a 0.1.442–0.1.448,** porque D411 entra en
0.1.433 y desplaza una versión a D400–D409.

## 0. Lo que se encontró

- **Medido antes de tocar nada,** con los dos censos endurecidos sobre el árbol de 0.1.431:
  - con `status_message.emit` y las dos ramas de un condicional, el censo de `test_gui_spanish_v1318` encuentra justo
    los tres textos de la ficha, y ninguno más;
  - las ramas de `tr(a if c else b)` tienen todas su español: el censo de claves (N3) no encuentra nada que arreglar,
    y queda como guarda;
  - con `re.I`, y FEA con su mayúscula, el de las formas retiradas encuentra solo los tres valores.
- **El hallazgo que no estaba en la ficha:**
  - mi primer test del mensaje de «3 puntos» dibujaba un contorno de material. Un contorno de material es una polilínea
    abierta (`draws_closed_polygon` solo vale para el exterior y el objeto de búsqueda por bloques), así que Intro lo
    terminó con dos vértices, y la barra dijo «Añadido Material Boundary con 2 vértices»;
  - el censo de campos que escribí entonces encuentra cuatro sitios en 0.1.431: Añadido y Convertido con
    `display_name`, el modo de la grieta y el tipo de foco con `.value`;
  - la búsqueda a mano de los nombres guardados encontró nueve más, y la de los demás roles, las dos descripciones de
    `setItemData`;
  - **se enseñó a la propietaria antes de corregir** (regla 6), con el mensaje medido en la ventana y la lista de
    sitios. Decidió meterlo en D399, y la redacción con «Contorno …:»;
  - **el sitio 16,** el combo de líneas piezométricas de la grieta, apareció después, al buscar combos que enseñan un
    nombre guardado. Es de la misma familia y entra con la misma decisión.
- **Lo que el censo de campos no puede ver:** el nombre guardado de un contorno es un dato, como el de un material o
  el del proyecto, y por el árbol de sintaxis no se distinguen. El censo cuenta solo `display_name`, `DISPLAY_NAME` y
  el `value` de un enum. El test lee cada mensaje del nombre guardado por la ventana real.
- **La revisión adversaria** (cuatro lentes, un crítico de completitud y dos escépticos por hallazgo; 81 agentes, el
  crítico relanzado tras el límite de uso) dejó 38 hallazgos: 32 confirmados por los dos escépticos, 3 con un voto de
  cada lado y 3 refutados. Nueve son de este diff: seis confirmados y los tres refutados.
  - **De este diff, corregidos:**
    - `_window()` del test devolvía `_WINDOWS[0]`, y la misma lista guardaba los diálogos: con un `-k` que dejara fuera
      al primer test, otro test recibía un diálogo por ventana (rojos falsos, nunca verdes falsos). Ahora la ventana y
      los diálogos van en listas aparte;
    - la cabecera del menú contextual, uno de los 16 sitios, solo se comprobaba llamando a `boundary_heading`: el
      mutante que devolvía el menú a 0.1.431 sobrevivía. Ahora se lee en el propio menú;
    - el titular de este changelog y el invariante del test decían que no quedaba inglés en pantalla y que los censos
      veían todos los caminos. Medido, no es así: se acotan a lo que arregla la versión;
    - tres cifras del §2 y la cuenta del inglés que cambia (abajo), mal contadas;
    - el hueco de la regla y la concordancia de «[desactivado]», que la propietaria decidió (arriba).
  - **Anteriores, que la propietaria mandó a una ficha nueva, D411, en 0.1.433:**
    - el mensaje de arranque («Listo — File → Load Demo Slope to start with a sample model.»);
    - el Filtro de selección («boundaries, vertices…», «nothing selectable»);
    - el resumen de Condiciones de contorno («nodal_flow: 21», «no conditions»);
    - el informe de Limpiar geometría («[0] EXTERNAL «External Boundary»») y el mensaje de Importar DXF («EXTERNAL: 1»,
      y el error de la vista previa en inglés);
    - el método de búsqueda en «Búsqueda de superficies configurada: grid» y en el Visor de información;
    - la Tabla de propiedades (las claves de los parámetros y los identificadores de los enum);
    - los ejes de la gráfica de una variable aleatoria, y la sensibilidad («friction_angle», «ΔFoS»);
    - el identificador del método en Exportar datos brutos de Interpretar;
    - los mensajes del núcleo que la ventana enseña con `str(exc)` (ángulo del talud, simplificar, expandir), y las
      notas del lector de registros sísmicos;
    - los nombres de los pasos de deshacer que son f-strings, que salen en inglés en el menú Edición;
    - «[BC]», que se añade a la etiqueta de una etapa transitoria y queda guardado;
    - el nombre que Expandir/Encoger da al arco que conserva («Original ground (from Expand/Shrink)») y el de un tipo
      de soporte que un agente crea sin nombre, que la regla toma por nombres dados;
    - «objeto de enfoque» en dos valores, frente a «objeto de foco» en el resto;
    - la regla del censo para los operandos de un `or` («x or "no conditions"»), el hermano del condicional.
  - **Con un voto de cada lado:**
    - la «W» del nivel freático en el lienzo: la propietaria decidió en P8h que W, P y D son símbolos;
    - «Escalado ×2: Capa débil» y «Rotado 9°: Línea de desembalse». Uno de los escépticos lo refuta, porque el
      participio concuerda con lo que se transforma, el contorno.
  - **El nombre por defecto del proyecto** («Untitled», «Demo slope») en el título de Interpretar y en el Visor de
    información salió con un voto en contra: la regla escrita desde D291b lo trata como un dato. Se anota en D411 para
    que lo decida la propietaria.
  - **Del banco:** `d318()` del verificador de la raíz buscaba las formas retiradas con su mayúscula exacta, y en
    0.1.431 daba 0 aunque estaban los tres valores. Se pone al día al cerrar la ficha: sin distinguir mayúsculas, con
    las dos formas retiradas que le faltaban y con la lista de usted del test.
- **Caminos equivocados:**
  - **El nombre del modo de la grieta empezó siendo un método de la clase del diálogo.**
    `test_undo_materials_water_v1303` sustituye esa clase por un doble, y la ventana lanzó `AttributeError`. El nombre
    de un identificador vive en `ogr_gui/labels.py`, que es el sitio de los nombres, y el diálogo lee de ahí su lista.
  - **En la pregunta a la propietaria escribí el ejemplo con coma decimal,** «(1,00, 2,00)». El programa imprime
    punto decimal en todos sus mensajes, y esta versión no lo toca.
  - **Mi primer `boundary_has_given_name` comparaba solo con el nombre de su propio tipo.** Así tomaba por nombre dado
    el de otro tipo, que es lo que dejan Convertir desde el menú contextual y la migración de v0.1.69.
- **El inglés también cambia,** en seis sitios de los dieciséis:
  - porque enseñaba el identificador: Gestionar objetos de foco dice «1: Focus Point (…)», y no «1: point (…)»; y la
    barra, «Tension Crack: Percent Filled», y no «percent_filled»;
  - porque repetía el nombre por defecto detrás del tipo: la descripción emergente de un contorno («<b>Material
    Boundary</b>», sin la segunda línea), la cabecera de su menú contextual («Material Boundary», sin «— Material
    Boundary») y la lista de Elegir contorno («[0] Material Boundary (2 verts)», sin el nombre entre comillas);
  - el combo de líneas piezométricas de la grieta numera todas sus líneas, como el de materiales: «Piezometric Line 1»
    donde decía «Piezometric Line», y «Piezometric Line 2» donde decía el nombre propio «Pozo A».
  - Y con el singular, «with 1 vertex», «(1 vert)» y «(1 point, …)», donde decía «1 vertices», «1 verts» y «1 points».

## 1. Qué cambia

- **`ogr_gui/labels.py`:**
  - `boundary_has_given_name`, `boundary_label` y `boundary_heading` («Contorno de material — Arcilla», o solo el
    tipo si el contorno conserva un nombre por defecto). El nombre inglés de cualquier tipo es un nombre por defecto;
  - las tablas `FOCUS_KIND` y `WATER_LEVEL_MODE`, con sus funciones;
  - `water_surface_label`, la regla que tenía `MainWindow._water_surface_choices`.
- **`ogr_gui/main_window.py`:**
  - Añadido, Eliminado (dos), Copiado, Movido (dos), Convertido, la lista de Elegir contorno, Gestionar objetos de
    foco y el mensaje de la grieta preguntan la etiqueta, y los tres primeros textos con número dicen el singular;
  - `_boundary_label` y `_water_surface_choices` delegan en `labels`;
  - la descripción emergente de Añadir rejilla pasa por `tr()`.
- **`ogr_gui/canvas/canvas_view.py`:**
  - los dos mensajes, por `tr()`;
  - la cabecera del menú contextual de un contorno, por `boundary_heading`.
- **`ogr_gui/canvas/graphics_items.py`:** la descripción emergente de un contorno es su tipo, en negrita, si conserva su
  nombre por defecto. Si no, su nombre y debajo el tipo, como antes.
- **`ogr_gui/dialogs/boundary_dialogs.py`:** el título de Editar coordenadas.
- **`ogr_gui/dialogs/tension_crack_dialog.py`:**
  - su lista de modos sale de `WATER_LEVEL_MODE`;
  - las dos descripciones emergentes pasan por `tr()`;
  - las líneas piezométricas se llaman por `water_surface_label`.
- **`ogr_gui/i18n`:**
  - catorce entradas nuevas: las diez de los textos de arriba y cuatro singulares;
  - tres valores pasan a «de rotura», cinco a «Contorno añadido/eliminado/copiado/movido: …» y uno a
    «[objeto desactivado]».
- **Censos, cambiados a propósito:**
  - **`tests/test_gui_spanish_v1318.py`:** lee `status_message.emit`, las dos ramas de un condicional y los roles de
    texto de `setItemData`. Lleva además un censo nuevo, el de los campos rellenados con inglés (`english_fields`).
    BUDGET sigue en 0, y la excepción «Piezo {}» se va con el texto que la tenía;
  - **`tests/test_voice_and_terms_v1325.py`:** busca sin distinguir mayúsculas, con FEA en su mayúscula
    (`holds_retired`);
  - **`tests/test_i18n_coverage_v141.py`:** `_wrapped_keys` lee las dos ramas de `tr(a if c else b)` y admite fuentes
    propias, para comprobarse;
  - **`tests/test_labels_spanish_v1321.py`:** cuenta las dos tablas nuevas, cada miembro con su etiqueta y cada
    etiqueta con su español.
- **`tests/test_spanish_texts_v1432.py`,** nuevo.
- **`spec/features/009-sarma-dovelas-no-verticales/`:** las versiones de Sarma, +1.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_spanish_texts_v1432.py`,** 24 tests en unos 3 s, con una ventana para todo el archivo, construida en
  español, y los diálogos en una lista aparte.
  - **La referencia** es el texto de cada mensaje, en los dos idiomas, leído donde lo lee el usuario: la barra de
    estado, la descripción emergente, el título, la lista y el menú contextual.
  - **Por la ventana real:**
    - los vértices se teclean en el campo de coordenadas de la barra, y se pulsan Intro y Esc sobre el lienzo;
    - Añadido, Copiado, Movido, el arrastre y Eliminado, por el menú y por el contextual, con un contorno con su
      nombre por defecto y con uno con nombre propio; y un punto de búsqueda por bloques, de un vértice;
    - Convertido desde el menú y desde el menú contextual, con el diálogo sustituido;
    - la lista de Elegir contorno y Gestionar objetos de foco (con un objeto desactivado y un punto), con el `getItem`
      sustituido y restaurado;
    - la cabecera del menú contextual, leída en el menú con el temporizador de `test_labels_spanish_v1321`;
    - el mensaje de la grieta, con su `exec` sustituido;
    - las descripciones emergentes de Añadir rejilla, de los círculos, de una superficie y de un contorno, y el título
      de Editar coordenadas;
    - el combo de la grieta: las dos descripciones de sus entradas en gris, y sus líneas piezométricas con los mismos
      nombres que el diálogo de materiales.
  - **En inglés,** lo que leen los tests y los usuarios (control).
  - **Los censos se comprueban a sí mismos,** sobre fuentes propias:
    - cuentan un texto en inglés en `status_message.emit`, en cualquier rama de un condicional y en un rol de texto
      de `setItemData`, y no el mismo con `tr()`;
    - otra señal y otro rol son datos;
    - cuentan un campo con `display_name` o con el `value` de un enum, y no uno con su etiqueta;
    - `_wrapped_keys` lee las dos ramas;
    - una forma retirada se caza con mayúscula, y «fea» no pasa por FEA.
  - **Las corridas filtradas** con `-k the_`, `disabled_entries`, `context_menu`, `piezometric` y
    `canvas_and_the_dialog` pasan: ningún test recibe un diálogo por ventana.
- **Discriminación en el árbol de 0.1.431** (`git archive` de 8a6a655, sin el buscador editable, `__file__`
  comprobados): fallan 21 de 24, y pasan los tres controles en inglés.
  - Dieciséis fallan por lo que hace el programa: el inglés en pantalla (doce), la forma retirada en la descripción de
    una superficie (uno), o un censo que no ve el texto de su fuente propia (tres).
  - El del nombre propio falla solo por la redacción nueva: «Copiado Arcilla» ya decía el nombre dado.
  - Cuatro fallan antes de llegar a comprobar nada, por un nombre que 0.1.431 no tenía: `boundary_heading`,
    `english_fields`, `holds_retired` y la fuente propia de `_wrapped_keys`. Los mutantes de abajo dicen que la regla de
    cada uno es la que su comprobación necesita.
- **Los censos nuevos sobre el código de 0.1.431:**
  - el de `test_gui_spanish_v1318` sale en rojo con seis textos sueltos: los dos del lienzo, el de Añadir rejilla, las
    dos descripciones de la grieta y «Piezo {}», cuya excepción retira esta versión. Además, cuatro campos;
  - el de las formas retiradas, con los tres valores;
  - el de las claves, en verde, porque no había ninguna sin español.
- **Mutantes,** uno a uno, en memoria y sin tocar el disco.
  - **De los censos,** en el mismo proceso: cada regla quitada hace fallar su propia comprobación, y solo esa. La
    excepción es la regla de `emit`, que se lleva también la del condicional anidado, porque ese caso va dentro de un
    `emit`:
    - sin `emit`;
    - sin las ramas;
    - sin los roles;
    - sin el censo de campos;
    - con las formas retiradas sensibles a la mayúscula;
    - con FEA sin su mayúscula;
    - sin las ramas de `tr()`.
  - **Del programa,** con el runner del proyecto, y en cada caso falla solo el test de esa regla:
    - con la cabecera del menú contextual de 0.1.431, falla el que la lee en el menú;
    - con `boundary_has_given_name` comparando solo con su propio tipo, falla el de Convertir desde el contextual.
- **Vecinos:** lienzo, arrastre de contornos, superficies a tres puntos, polilíneas y superficies del usuario,
  dibujo, reglas, motivos de lo deshabilitado, ángulo de talud, Escalar y Rotar, búsqueda por bloques, foco, grieta,
  superficies de agua, materiales, menús, deshacer, tema oscuro, diálogos, DXF, i18n, español, etiquetas, versión y
  cachés de los tests: 885 de 885. La primera pasada dio 701 de 703: el doble del diálogo de la grieta (§0, caminos
  equivocados) y el changelog, que aún no estaba escrito.
- **Suite entera con `--jobs 4`: 7265 en verde, 1 saltado y 0 fallos,** sin fugas ni tramos muertos, sobre el árbol
  final. La primera corrida, antes de la revisión, dio 7262 en verde. La última serie en verde fue hace 10 commits, y
  toca a los 100.
- **Banco, en seco:** D300, D318, D335, D291, D291b, D315, D344, D349 y D398, todas CUBIERTO POR TEST. `d399()`, aún
  sin aplicar al verificador, probada dentro de él sin escribir nada: con el árbol vivo, CUBIERTO POR TEST; con el de
  0.1.431, SIGUE ABIERTO por lo que hace (los cuatro textos en inglés y las tres formas retiradas).

## 3. Qué queda

- **D411,** en 0.1.433, por decisión de la propietaria: el inglés en pantalla que la revisión encontró (§0), con un
  censo pensado para esos caminos. Se abre al cerrar D399.
- **D410** (sin versión) recoge también Convertir contorno desde el menú contextual: no renombra, no abre el polígono,
  no quita `material_id` y no pregunta la regla de su tipo.
- El resto de la tanda P10, una versión más tarde:
  - D400–D404 en 0.1.434–0.1.438;
  - D408 (el informe PDF) en 0.1.439;
  - D406 (`surface_evaluate`) en 0.1.440;
  - D409 (el FS(0) con kh) en 0.1.441;
  - D407 (el rebanador) y D410 siguen sin versión.
  - Sarma va en 0.1.442–0.1.448.
- **Prueba a mano, para la propietaria,** con la interfaz en español:
  - dibujar cada tipo de contorno, también un punto de búsqueda por bloques, y leer la barra;
  - copiar, mover (por el menú y arrastrando), convertir (por el menú y por el clic derecho) y eliminar un contorno,
    con su nombre por defecto y con uno propio;
  - abrir el diálogo de la grieta en un modelo sin nivel freático ni líneas piezométricas y pasar el ratón por sus
    entradas en gris; con dos líneas, comparar sus nombres con los del diálogo de materiales;
  - Gestionar objetos de foco con uno de cada tipo, uno desactivado.
