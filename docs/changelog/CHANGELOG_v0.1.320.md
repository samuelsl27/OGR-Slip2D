# OGR Slip2D v0.1.320

**Los diálogos del agua, de la búsqueda y el resto hablan castellano, y el
presupuesto del test de AST llega a 0 (D300, familias c y d).** Cuarta
versión de la tanda P8h.

## 0. Lo que se encontró

- **Las reglas de 0.1.318 no miraban los elementos de un combo.**
  - `addItem("Line segments", …)` enseña su primer argumento, igual que un
    `QLabel`, y el test no lo contaba.
  - Tampoco veían `insertItem`, ni sabían que `%d` o `%.3f` son campos y no
    letras.
  - Con las tres cosas añadidas, la familia pasó de los 47 sitios que
    quedaban en 0.1.319 a **59**.
- **Once de los 59 no son texto que traducir:**
  - **los dos textos que el puente devuelve al agente** (`agent_bridge.py`).
    El agente lee en inglés, como todos los mensajes del API;
  - **símbolos y notación que se escriben igual en castellano:** los tres
    símbolos de Hoek-Brown de la calculadora («mb:», «s:», «a:»), «ΔX (m):» y
    «ΔY (m):», «Piezo {}» y «Circular»;
  - **el nombre por defecto de un tipo de soporte nuevo** («Type {}»), que
    el modelo guarda, como el «Untitled» de un proyecto;
  - **la línea de un registro sísmico** («%s %s %.3f g, %.1f s»: nombre,
    aceleración máxima en g y duración en s).

  Van a `EXCEPTIONS` con su razón.
- **Los cuatro literales de `main_window.py`** que sus dos tests de AST no
  veían (dos ayudas emergentes y dos `QAction`) entran aquí.
- **El test nuevo encontró una tabla que el de AST no puede ver.** El combo
  de métodos de *Surface Options* enseñaba «Particle Swarm Search» en inglés
  con la interfaz en castellano, aunque el diccionario tenía su traducción.
  - `grid_dialogs.py` guardaba los siete nombres de búsqueda en un
    diccionario de literales sin `tr()`, y los añadía con
    `addItem(self._method_labels[m], m)`. El censo de AST solo mira
    literales y f-strings como argumento, no un subíndice.
  - El test solo marcó el de Particle Swarm porque es el único de los siete
    con castellano: comprueba que no salga en inglés un texto que tenga
    traducción. Los otros seis no tenían entrada.
- **Medido después, abriendo en castellano la ventana y los 44 diálogos del
  censo de D293: 95 textos con aspecto inglés.**
  - 11 los resuelve 0.1.321, que traduce las etiquetas del núcleo.
  - Unos 15 son falsos positivos: castellano con «no» o «global», unidades
    sueltas, el nombre del proyecto.
  - El resto son tablas de opciones que se pasan por variable: orientación
    de cargas, agua de la grieta, tipos de contorno, soportes, sistemas de
    unidades y la calculadora de Hoek-Brown. A eso se suman combos que
    enseñan identificadores internos (`grid_total_head`, `water_table`,
    `none`) en cualquier idioma.
  - Por decisión de la propietaria, todo eso va en 0.1.321. Las ayudas de
    la barra de matplotlib, el mensaje del núcleo al leer un DXF y «Corps of
    Engineers #1/#2» (nombre propio del método) quedan en inglés como
    excepciones escritas.
- **«Malla» contra «rejilla».** «Grid Search Options» se traducía «Opciones
  de búsqueda en malla», pero el proyecto reserva *malla* para elementos
  finitos y *rejilla* para la de centros (D240, «Añadir rejilla»). Por
  decisión de la propietaria, rejilla en los dos.

## 1. Qué cambia

- **Los siete nombres de búsqueda pasan por `tr()`.** Los seis que no tenían
  castellano lo toman de los títulos de sus páginas de opciones: «Búsqueda
  por rejilla», «Búsqueda de talud», «Búsqueda de refinado automático»,
  «Búsqueda por bloques», «Búsqueda por caminos» y «Recocido simulado».
- **«Grid Search Options»** pasa a «Opciones de búsqueda por rejilla».

- **48 sitios pasan por `tr()`** en 16 archivos:
  - los diálogos del agua (condiciones de contorno, etapas transitorias,
    grieta de tracción, rejilla de presiones de agua);
  - los de la búsqueda (rejilla de centros, opciones de superficie);
  - contornos, cargas, opciones de visualización, sismo, ajustes del
    proyecto, patrones y propiedades de soportes, variables aleatorias y
    otros;
  - `main_window.py`.

  El inglés queda idéntico.
- **46 claves nuevas con su castellano.** Entre ellas está el cuadro de
  *About*, en HTML, traducido entero salvo el nombre de la licencia. Ninguna
  clave duplicada nueva.
- **`tests/test_gui_spanish_v1318.py`:**
  - las reglas leen también los elementos de combo y saltan los campos `%`;
  - once excepciones nuevas, con su razón;
  - `BUDGET` baja de 47 a **0**. Desde aquí, cualquier texto visible nuevo
    sin `tr()` hace fallar la suite, salvo que se escriba su excepción con
    su razón;
  - una clase nueva, `TestTheDialogsSpeakSpanish`.

## 2. Tests

`TestTheDialogsSpeakSpanish` abre con la interfaz en castellano seis
diálogos de las dos familias: *Add Grid*, *Surface Options*, *Define Tension
Crack*, las etapas transitorias, *Seismic Load* y *Project Settings*.

- **Ninguno enseña un texto inglés que tenga castellano.** Se recogen
  títulos, etiquetas, botones, grupos, ayudas emergentes, elementos de combo
  y cabeceras de tabla. Los botones estándar de una caja de botones no
  cuentan, porque los nombra el catálogo de Qt.
- **Cada uno enseña en castellano uno de los textos que envolvió esta
  versión**, y en inglés el texto de antes (control).

**Con el código de 0.1.319 fallan 4 de los 8 casos del archivo:**

- el recuento (48);
- el presupuesto exacto;
- los dos casos de los diálogos. *Add Grid* no enseña su introducción en
  castellano, y *Surface Options* enseña «Particle Swarm Search».

El control en inglés, *Interpret*, el panel de resultados y las excepciones
pasan en los dos árboles. Se corrió sobre un `git archive` de 0.1.319, sin el
buscador editable.

## 3. Verificación

- **Los tests vecinos**, antes de la suite:
  - el test de AST, i18n y la consistencia de versión, 28/28;
  - rejilla, superficies, transitorio, sismo, ajustes, contornos, cargas,
    soportes, variables aleatorias, visualización, presiones de agua,
    grieta, menús en castellano, la ventana en inglés, idioma, traducciones
    de Qt, tamaños de diálogos, el aviso de Block Search, los rótulos del
    menú de superficies y *About*, 1404/1404.
- **Suite entera:** 6119/6119, `EXIT=0`, 56 min.
- **Banco:** `verificar_cierres.py` entero, 59 comprobaciones y 0 bajadas.
  D300 sigue abierta.
- **Ningún número cambia:** son textos, y el inglés es idéntico.

## 4. Pendiente

- **Las etiquetas que vienen del núcleo, las tablas de opciones, los combos
  con identificadores internos y D240** (0.1.321).
- **A mano:** los diálogos del agua y de la búsqueda con Español guardado.
