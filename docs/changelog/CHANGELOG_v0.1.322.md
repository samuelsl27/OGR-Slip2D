# OGR Slip2D v0.1.322

**Los soportes hablan castellano: sus nombres, sus descripciones, las filas y
la ayuda de cada parámetro, las pestañas, y la aplicación y la orientación de
su fuerza (D300, soportes).** Última versión de la tanda P8h. D300 se cierra.

## 0. Lo que se encontró

- **La familia de los soportes venía del núcleo en inglés** y no pasaba por
  `tr()`:
  - **el nombre y la descripción de cada tipo** (`DISPLAY_NAME`,
    `DESCRIPTION`). Salían en *Define Support*, en el tipo de un soporte y de
    un patrón, en la ayuda del lienzo, en las ayudas de datos, en la tabla de
    propiedades, en *Interpret* y en el diagrama de fuerzas;
  - **cada fila de parámetros de *Define Support***, rotulada con la clave en
    mayúsculas iniciales («Out Of Plane Spacing:»), y su ayuda, la
    descripción del núcleo. Son 36 claves y 54 descripciones distintas en los
    9 tipos;
  - **las 9 pestañas del editor** (`PARAMETER_TABS`), de las que 6 no tenían
    castellano.
- **Dos nombres ingleses para la misma orientación.** *Define Support* decía
  «Tangent to slip surface», y los otros tres diálogos de soportes
  (propiedades, patrón y modificar patrón) `value.title()`: «Tangent To
  Slip». La aplicación era `value.capitalize()`, y la ayuda del lienzo y las
  de datos escribían el valor del enum («active», «tangent to slip»).
- **El nombre de un juego es dato.** Un juego nuevo de *Define Support* se
  llama, por defecto, como su clase en inglés, y ese nombre se guarda. Como
  el «Type {}» de 0.1.320, no se traduce. Solo se traduce el nombre de la
  clase, entre corchetes en la lista y como respaldo donde el juego no tiene
  nombre propio.
- **El heurístico del test de pantalla daba una falsa alarma.** Leía como
  inglés «Horizontal», que es la misma palabra en castellano. Salen de su
  lista las palabras que también son castellanas: «horizontal»,
  «vertical», «material», «global», «local», «no» y «factor».

## 1. Qué cambia

- **Las filas de *Define Support*** conservan en inglés el rótulo de
  siempre y pasan por `tr()`. En castellano: «Separación fuera del plano:»,
  «Capacidad a tracción:», «Longitud del bulbo (%):»…
  - Cada clave se escribe una vez en castellano y da las dos formas: el
    rótulo de la fila y la clave que enseñan las ayudas de datos y las
    variables aleatorias («separación fuera del plano»). Así no pueden
    divergir.
  - La ayuda de cada fila y de su editor es la descripción traducida.
- **Los nombres, las descripciones y las pestañas** pasan por `tr()` donde se
  enseñan.
  - `support_type_label` (en `ogr_gui/labels.py`) da el nombre de un juego:
    el que le puso el usuario o, si no tiene, el de su clase traducido.
  - Lo usan el lienzo, las ayudas de datos, la ventana principal, la tabla de
    propiedades, *Interpret* y los tres diálogos de soportes.
- **La aplicación y la orientación de la fuerza** tienen una sola tabla, en
  `ogr_gui/labels.py` (`FORCE_APPLICATION`, `FORCE_ORIENTATION`): la de
  *Define Support*. La usan los cuatro diálogos, la ayuda del lienzo y las
  ayudas de datos. En inglés, los tres diálogos que decían «Tangent To Slip»
  dicen ahora lo mismo que *Define Support*.
- **Las variables aleatorias de soportes** se enseñan traducidas, con la
  etiqueta guardada intacta: «Anclado en el extremo — capacidad del anclaje».
- **153 claves nuevas con su castellano:**
  - 6 nombres y 6 descripciones de tipos (la del pilote ya la tenía);
  - 72 de las 36 claves, en sus dos formas;
  - 54 descripciones de parámetros;
  - 6 pestañas;
  - 7 etiquetas de aplicación y orientación («Horizontal» se escribe
    igual);
  - la plantilla «application: {0}» y el respaldo «support».

  Los valores que algunas descripciones citan para el API (`shear |
  ito_matsui`, `linear | hyperbolic`) se dejan tal cual, porque son lo que
  se escribe.
- **`test_labels_spanish_v1321`:**
  - el test de pantalla ya no lleva las excepciones de soportes;
  - la exhaustividad de `labels.py` cubre la aplicación y la orientación;
  - «Horizontal» pasa a la lista de etiquetas que se escriben igual;
  - el heurístico deja de tomar por inglés siete palabras que también son
    castellanas.

## 2. Tests

`tests/test_supports_spanish_v1322.py` (nuevo), 9 casos:

- **Todo texto de los soportes tiene castellano:** el nombre y la descripción
  de cada tipo registrado, cada parámetro en sus tres formas (fila, clave y
  ayuda) y cada pestaña. La fila y la clave dicen lo mismo.
- ***Define Support* en castellano:** para cada tipo, cada fila es su rótulo
  traducido (nunca el inglés), su ayuda es la descripción traducida, y las
  pestañas también lo son. El combo de tipos dice «Anclado en el extremo», la
  aplicación «Activa» y «Pasiva», y la orientación «Tangente a la superficie
  de deslizamiento».
- **Control en inglés:** «Out Of Plane Spacing:» y «Anchor Capacity:», como
  siempre.
- **Las propiedades de un soporte** nombran la orientación igual que *Define
  Support*, en los dos idiomas, y ya no dicen «Tangent To Slip».
- **La ayuda de datos de un soporte** y **su variable aleatoria**, en
  castellano y con su control en inglés.

**Con el código de 0.1.321 fallan 8 de los 9 casos del archivo nuevo.** El
que pasa es el control en inglés. Del test de 0.1.321 retocado fallan los
tres casos que tocan los soportes:

- los dos de exhaustividad de `labels.py`, que ahora piden la aplicación y
  la orientación;
- el test de pantalla, que ya no tiene sus excepciones y encuentra «End
  Anchored» y «Tangent To Slip».

Se corrió sobre un `git archive` de 0.1.321, sin el buscador editable.

## 3. Verificación

- **Los tests nuevos y sus vecinos**, antes de la suite:
  - soportes, etiquetas, el test de AST, i18n y la consistencia de versión,
    56/56 a la primera;
  - soportes, patrones, ayudas de datos, lienzo, elementos gráficos,
    *Interpret*, la tabla de propiedades, variables aleatorias, estadística,
    tamaños de diálogos, menús y ventana en los dos idiomas, idioma, i18n y
    los tipos de soporte uno a uno, 888/888.
- **Suite entera:** 6147/6147, `EXIT=0`, 54 min.
- **Banco:**
  - `verificar_cierres.py` entero: 61 comprobaciones, D300 **CUBIERTO POR
    TEST** y 0 bajadas;
  - instantánea `Evaluaciones/0.1.322`, con D300 retirada y podada de P8,
    donde queda D314;
  - prompts regenerados: 33;
  - auditorías: 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** es texto de pantalla, y el `.ogr`, las
  claves y el API no cambian.

## 4. Banco

- **D300 se cierra.** La comprobación mide contra el diccionario las tres
  listas del núcleo y los soportes, y pide:
  - el censo de AST con presupuesto 0;
  - el test de pantalla;
  - la exhaustividad de `labels.py`;
  - los tests de los soportes.

  **CUBIERTO POR TEST**. Se poda de P8, donde queda D314.
- **Tanda P8h terminada.**

## 5. Pendiente

- **D314,** los mensajes del núcleo con códigos estables.
- **La leyenda de sensibilidad de la ventana de estadística**, que enseña la
  etiqueta guardada del barrido.
- **La tercera prueba de la interfaz,** con Español guardado.
