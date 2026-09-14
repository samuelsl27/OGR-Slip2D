# OGR Slip2D v0.1.166

**El encargo de P-D102 pedía que la acción «Add Surface» del menú Surfaces
dejara de llamarse así, porque no añade ninguna superficie: dibuja un objeto
de Block Search, exactamente lo que su propio docstring dice desde la primera
versión pública. Está hecho. Pero de las ocho cosas que la ficha da por
sentadas, la medición desmiente las ocho — y la más cara es su paso 2, que
manda retirar del diccionario una clave que NO está huérfana y cuya retirada
habría roto `test_every_wrapped_key_has_spanish`.**

Cierra **D102**. **Cero dígitos movidos**, y es consecuencia y no
coincidencia: el cambio vive entero en `ogr_gui/`, no toca una línea
ejecutable de cálculo, ni una constante, ni una tolerancia, ni un valor por
defecto, y ningún `.ogr` del banco pasa por una barra de menús. El banco no
se re-corre.

---

## 1. El defecto

`main_window.py:520` (en 0.1.165) registraba:

```python
self._mk("surf_3pts", "Add Surface", self.act_add_surface, "surface_3pts")
```

y `act_add_surface` no añade nada: entra en `ToolMode.DRAW_BLOCK_SEARCH`, el
único `_set_tool` de ese modo en el repositorio. Su docstring lo decía en su
primera línea —«Add a Block Search object (a search window) on the canvas»—
mientras el rótulo decía lo contrario.

Tres entradas más abajo, en el **mismo menú**, está «Add Surface (centre and
radius)...», que sí añade una superficie (D58, v0.1.157). Dos entradas que
empiezan igual, y la que un usuario pulsa primero era la que hacía otra cosa.

Y hay un detalle que agrava la confusión: las dos **nunca están habilitadas a
la vez**. La de bloque pide `search_method == "block"`; la de centro-radio
pide `surface_type == CIRCULAR`. De modo que el usuario que busca «añadir una
superficie» ve una de las dos en gris y pulsa la otra — la que no es.

Efecto numérico: ninguno. Efecto real: el rótulo.

## 2. Lo que la ficha da por sentado y la medición desmiente

Ocho cosas, y cuatro cambian el trabajo.

**(1) Sus citas ya no apuntan a código.** `_mk` estaba en 520 y no en 507; el
menú en 767 y no en 754; la barra en 887 y no en 874; el gating en 3769-3777 y
no en 3682-3686; `act_add_surface` en 1180-1204 y no en 1165-1189. La ficha
dice «leída con OGR 0.1.165», que es justo el árbol sobre el que no casan.

**(2) Su paso 2 está refutado, y es el caro.** Manda retirar
`'Add Surface'` (i18n:187) «si no la usa nadie más». La usa
`_add_surface_centre_radius` como título de sus **dos** diálogos —
`tr("Add Surface")` en 2218 y en 2222—, que es la **otra** acción, la que sí
añade una superficie. Retirarla habría dejado dos claves envueltas sin
traducción y roto `test_every_wrapped_key_has_spanish`. Se queda, y queda
fijado en un test para que el próximo que lea el paso 2 encuentre el porqué.

**(3) No hay ningún archivo de icono que renombrar.** `surface_3pts` es una
clave del catálogo `ogr_gui/resources/icons.py:81` que apunta al glifo
`fa6s.circle-dot`, heredada del modo «superficie por tres puntos» que nadie
activa (D101). Y hay una trampa debajo: `icon()` contesta con un **engranaje,
en silencio**, ante una clave desconocida (`_CATALOG.get(key, ("fa6s.gear",
None))`), y **no existe ningún test del catálogo**. Renombrar la clave en
`main_window.py` sin tocar `icons.py` habría puesto un engranaje en la barra
de herramientas sin que nada fallara. Por eso la comprobación de que la clave
existe es parte del arreglo y no higiene.

**(4) «el tooltip ya lo dice bien» es media verdad.** Lo dice bien la rama
**habilitada**. La rama **deshabilitada** —la que ve el usuario casi siempre,
porque Block Search no es el método por defecto— seguía diciendo «Add Surface
is only available with the Block Search…» y **sin `tr()`**. Renombrar la
etiqueta y no tocarla habría dejado el tooltip contradiciendo al rótulo que
describe: el mismo defecto un escalón más abajo.

**(5) Su prueba (b) no se puede escribir global.** Medido sobre las 135
acciones registradas hay **siete** pares de prefijo legítimos —`Save`/`Save
As...`, `Compute`/`Compute Statistics`, `Compute`/`Compute Groundwater`,
`Interpret`/`Interpret Groundwater`, `Select`/`Selection Filter...`,
`Assign Material`/`Assign Materials`, `Add Support`/`Add Support Pattern...`—
además del par de este defecto. Una invariante global de prefijos habría
fallado por siete razones que no son defectos. Va acotada al **menú
Surfaces**, donde el único par era el de D102.

**(6) `d102()` NO EXISTÍA** en `_tools/verificar_cierres.py`, aunque el
criterio de cierre la cite como si estuviera escrita. Igual que D91, D95, D96
y D98. Y el test no es `_v1160` sino **`_v1166`**, porque `_vNNNN` es la
versión en que **aterriza**.

**(7) El presupuesto de 210 es un fantasma.** La cuenta real hoy es **20**:
190 de holgura. Y ninguna línea que este cambio toca casa con los siete
patrones `_VISIBLE` —`_mk(`, `QAction(`, `setToolTip(` y `QMessageBox.*(` no
están entre ellos—, así que desde aquí el presupuesto **no se puede mover ni
queriendo**. La restricción «no sube» se cumplía sola.

**(8) Su línea de verificación ignora en silencio un patrón que no casa.**
Medido antes de escribir el test: `--list menu_reachability i18n_coverage
user_surfaces surfaces_menu_labels` seleccionaba **3 archivos y salía con
código 0**, callando el cuarto. Es inocuo aquí porque el archivo existe al
terminar; pero si el test hubiera acabado con otro nombre, la verificación
habría pasado sin haberlo corrido nunca. Se comprueba el **recuento**, no el
código de salida.

## 3. El arreglo

**El rótulo va sin puntos suspensivos**, y no por gusto: medido sobre las 135
acciones, «...» aparece sólo cuando se abre un diálogo, y **todas** las de
modo de dibujo van sin ellos (`Add External Boundary`, `Add Water Table`,
`Add Tension Crack`, `Add Support`, `Add Text`). Ésta entra en modo de dibujo.
La ficha proponía «Add Block Search Object...»; los puntos habrían prometido
un diálogo que la acción no abre — una mentira nueva, pequeña, en el arreglo
de una mentira.

- `main_window.py:524-525` — clave `surf_3pts` → **`block_object`**, rótulo
  **«Add Block Search Object»**, manejador `act_add_surface` →
  `act_add_block_search_object`. La clave se cambia en los cuatro sitios (772
  menú, 892 barra, 3780-3787 gating) y en el comentario de v0.1.17 que
  entrecomillaba el rótulo viejo.
- `icons.py:81` — clave **y** glifo: `"block_object": ("fa6s.object-group",
  None)`. Se comprobó que `fa6s.object-group` **resuelve** en el qtawesome
  instalado (1.4.2) antes de escribirlo, porque `_safe_qta_icon` habría
  servido un círculo gris sin decir nada. Con esto `surface_3pts` queda libre
  para D101, que es de quien era el círculo.
- `main_window.py:3780-3790` — el tooltip deshabilitado pasa por `tr()` y deja
  de decir «Add Surface».
- `main_window.py:1185-1212` — las **palabras** del modal siguen al nombre
  nuevo. El modal **sigue siendo modal y sigue fuera de `tr()`**: eso es
  P-D103 entero, y se deja escrito en un comentario para que nadie lo lea como
  medio arreglado.

**La traducción no es la que pide la ficha.** Proponía «Añadir objeto de Block
Search», y el diccionario ya había fijado el término castellano para esta
misma acción: su tooltip habilitado dice «objeto de **búsqueda por bloques**»
(i18n:771) y «Block Search Options» es «Opciones de **búsqueda por bloques**»
(790). Dejar el anglicismo habría hecho que la etiqueta y su propio tooltip se
contradijeran. Queda `'Add Block Search Object': 'Añadir objeto de búsqueda
por bloques'` (i18n:194).

**Pero los VALORES de los controles se quedan en inglés**, y eso sí es
deliberado: el botón de radio pone `"Non-Circular"` (`grid_dialogs.py:282`) y
el elemento del combo pone `"Block Search"` (`:304`), ninguno de los dos
traducido. Un nombre castellano en el tooltip habría mandado al usuario a
buscar un control que no existe con ese nombre.

## 4. El hallazgo que el encargo no menciona, y que decide el alcance del test

`_mk` llama `tr(text)` con una **variable** (`main_window.py:337`). El escáner
del test de cobertura recoge por AST los literales constantes pasados a `tr`,
así que **no ve ni una sola etiqueta de acción**; y los siete patrones
`_VISIBLE` tampoco cubren `_mk(` ni `QAction(`. Resultado medido: **28 de las
135 etiquetas de menú no tenían entrada en español**, y salen en inglés con el
idioma puesto en español, sin que ningún test lo vea.

Entre ellas **«Add Grid...»**, en este mismo menú, que sí tiene `"Add Grid"`
*sin* puntos en el diccionario: alguien añadió los puntos suspensivos a la
etiqueta y la traducción dejó de casar en silencio, porque `tr()` cae a la
clave. Es la forma exacta del defecto que esta versión corrige —una palabra de
un rótulo que dejó de decir la verdad sin que nada avisara—, así que se
traduce aquí y el censo baja a **27**, que queda como techo.

Al medirlo apareció algo más: **el diccionario español tiene 19 claves
duplicadas** sobre 1280 entradas. Diecisiete son inofensivas (el mismo valor
dos veces), pero **dos discrepan** y la última gana:

- `'Add Grid'` — 751 «Añadir malla» y 1269 «Añadir rejilla». Gana «rejilla»,
  que es lo correcto; la sombreada llama **malla** a una rejilla de búsqueda,
  que es el término de la malla de elementos finitos. Si alguien reordenara o
  partiera el diccionario, la rejilla de centros empezaría a llamarse malla.
- `'None'` — 563 «Ninguno», 1470 «Ninguna», 1651 «Ninguno».

No se corrigen aquí: son una limpieza propia de 19 entradas y ninguna mueve un
número. Quedan medidas.

## 5. El test

`tests/test_surfaces_menu_labels_v1166.py`, 18 casos. Lo que comprueba y por
qué cada cosa:

- **El rótulo contra el COMPORTAMIENTO, no contra otra cadena**: se dispara la
  acción y el lienzo tiene que quedar en `ToolMode.DRAW_BLOCK_SEARCH`. Un test
  que sólo comparase textos habría pasado en verde sobre una etiqueta que
  volviera a separarse de su manejador. Se pone Block Search **antes** de
  disparar: fuera de ese método la acción abre un `QMessageBox` modal que
  bloquea sin pantalla — ese modal es P-D103, sigue abierto.
- **Dentro del menú Surfaces ninguna etiqueta repite a otra ni es prefijo de
  otra**, acotado a ese menú por el hallazgo (5) y con el porqué escrito.
- **Ninguna acción del programa comparte texto con otra.** Ésta sí es global,
  y protege a un test antes que a un usuario: `test_menu_reachability_v142`
  identifica las acciones por **texto contra un conjunto**, de modo que dos
  acciones con la misma etiqueta son indistinguibles para él y una duplicada
  podría tapar una acción inalcanzable, que es la regla 3 misma.
- **El censo de etiquetas sin traducir con techo 27**, más un caso que **mide
  la razón** de que nadie las viera, contra el escáner de verdad y no en un
  comentario: la etiqueta nueva **no** está en `_wrapped_keys()`, mientras que
  las mismas palabras escritas dentro de un `tr("...")` **sí** lo están. Se
  comprueban las dos mitades, porque una ausencia sola también pasaría si el
  escáner estuviera roto.
- **La clave de icono existe en el catálogo** y `surface_3pts` ya no está.
- **Lo que hay que CONSERVAR**: habilitada si y sólo si Block Search;
  alcanzable desde el menú (regla 3); **y todavía en la barra de
  herramientas**, porque el bucle de `_build_toolbar` lleva un
  `if k in self._actions` que descarta una clave mal escrita **en silencio**.
- **Que `'Add Surface'` sigue en el diccionario**, que es el paso 2 refutado.

Falla **15 de 18 contra el árbol de 0.1.165**, que es la prueba de que mide
algo, y los **3** que pasan son justo los que deben pasar: las dos identidades
que el arreglo conserva —ninguna etiqueta repetida, ningún par igual dentro de
Surfaces— y la premisa refutada. Ninguna aserción fija un factor de seguridad:
aquí no hay ninguno que fijar.

Un error propio, detectado al correrlo: la primera redacción devolvía el
`QMenu` desde una función auxiliar y lo recorría en la siguiente llamada, con
lo que reventaba con «Internal C++ object (QMenu) already deleted». Es
exactamente lo que `test_menu_reachability_v142` avisa en su cabecera de
módulo: sostener el envoltorio de un menú más allá del bucle que lo produjo
sobrevive al objeto C++. El recorrido no devuelve ya ningún `QMenu`.

Y dos más, de medición, corregidos antes de publicar:

- el censo de `d102()` buscaba `block_object` como subcadena y daba **falso
  positivo** en `ogr_slip2d/search.py`, donde `block_objects` y
  `_sample_block_object` son nombres del motor de Block Search desde mucho
  antes y no tienen nada que ver con esta acción. Un censo así no se queda
  en ruido: habría acabado con alguien «arreglando» `search.py` para hacer
  callar al verificador. La clave va ahora **entrecomillada**, que es como
  aparece cuando de verdad es una clave de acción;
- las acciones registradas son **135** y no 129. El 129 salía de contar
  llamadas a `_mk` en el árbol sintáctico y sumarle a mano el bucle de
  objetos de foco: hay **dos** bucles, y el segundo —el de anotaciones,
  línea 631— registra otras seis. Contadas donde se ven, sobre
  `w._actions` de una ventana real, son 135. Las otras dos cifras que
  dependían de ella no se mueven: los pares de prefijo legítimos siguen
  siendo **siete** y las etiquetas sin español **27**, ahora medidas sobre
  el conjunto entero y no sobre una aproximación.

## 6. Lo que se ha medido

- **Suite entera y sin argumentos: 3531/3531.** 0.1.165 traía 3513, y los
  **18** nuevos son este archivo.
- Selección dirigida `menu_reachability i18n_coverage user_surfaces
  surfaces_menu_labels m6 minor_menus`: **124/124**.
- `grep -rn "surf_3pts\|surface_3pts\|act_add_surface" ogr_gui` → **0**.
- De punta a punta con la ventana real: la etiqueta, el botón presente en la
  barra, el gating en los dos sentidos, el modo de herramienta tras disparar,
  y la etiqueta y el tooltip en español.
- **Cero dígitos**: el cambio no sale de `ogr_gui/`.

## 7. Se reporta y NO se corrige (regla 6)

- **27 etiquetas de menú sin español** — «Generate Report...», «Zoom Mouse»,
  «Select», «Compute Statistics», «Compute Groundwater», «Interpret
  Groundwater», «Move Boundary», «Copy Boundary», «Scale Boundary...»,
  «Rotate Boundary...», «Expand / Shrink External...», «Change Slope
  Angle...», «Convert Boundary...», «Edit Coordinates...», «Selection
  Filter...», «Stretch Support», «Define Tension Crack...», «Define Hydraulic
  Properties...», «Generate FE Mesh...», «Reset FE Mesh», «Set Boundary
  Conditions...», «Transient Groundwater...», «Water Pressure Grid...», «Back
  Analysis of Support Force...», «Random Variables...», «Show Statistics» y
  «Terminal». Traducirlas mueve texto visible en veintisiete sitios y es un
  encargo propio; aquí quedan **medidas y con techo**.
- **El agujero estructural que las esconde**: `_mk` pasa una variable a
  `tr()`, y los siete patrones `_VISIBLE` no cubren `_mk(`, `QAction(`,
  `setToolTip(`, `addItem(`, `QRadioButton(` ni `QMessageBox.*(`. Ampliar el
  escáner es tocar el test de cobertura entero.
- **`"Non-Circular"` (`grid_dialogs.py:282`) y `"Block Search"` (`:304`) no
  pasan por `tr()`**, y por lo anterior no los cuenta nadie. Esta versión se
  apoya en que están en inglés en pantalla; si alguien los traduce, el tooltip
  nuevo hay que traducirlo con ellos.
- **19 claves duplicadas en el diccionario español**, dos con valores
  distintos (§4).
- **El presupuesto de 210 ya no muerde**: la cuenta real es 20. De paso, el
  criterio de cierre de **D103** —«el presupuesto de cadenas sin envolver
  bajado en seis»— no es alcanzable tal como está escrito, porque esas seis
  líneas no están contadas en él; la propia ficha corrigió el mecanismo el
  2026-09-11 y dejó el criterio sin corregir.
- **`test_menu_reachability_v142` identifica por texto**, no por clave. No es
  explotable hoy —cero etiquetas repetidas, medido— y el test nuevo lo cierra
  hacia el futuro, pero el test sigue escrito así.
- **`icon()` sirve un engranaje en silencio** ante una clave desconocida y no
  hay test del catálogo: el test nuevo guarda **una** clave, no las sesenta.
- **`"Add Grid"` sin puntos NO queda huérfana**, y conviene decirlo porque a
  primera vista lo parece: ya no la usa ninguna etiqueta de menú, pero sí el
  título del diálogo (`tr("Add Grid")`, `grid_dialogs.py:56`). Es el mismo
  error que el paso 2 de la ficha comete con `'Add Surface'`, y la forma de no
  cometerlo es mirar los `tr()` antes de retirar nada. Lo que sí queda
  huérfano de verdad es `"Add Surface (three points)"` (i18n:1294), y es de
  **D101**: retirar claves huérfanas es una pasada propia y no se hace aquí.
- **El modal de `act_add_block_search_object` sigue modal y sin `tr()`** —
  P-D103, que este prompt desbloquea y no toca.
- **En el banco, la arista `"D103": ["D102"]` de `REQUIERE` se queda**, y con
  ella la línea «requiere P-D102» en las cabeceras de P-D103 y P-D101, que
  ya no está pendiente. Es la convención del archivo y no un descuido de
  esta versión: P-D60 pide P-D79 y P-D38 pide P-D82, cerrados los dos. Lo
  que sí se poda a mano, porque el generador lo pide por su nombre, es la
  lista del paquete P1.
