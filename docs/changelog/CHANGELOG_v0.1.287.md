# OGR Slip2D v0.1.287

**Un «&» en una etiqueta que Qt lee como atajo de teclado ya se dibuja
(D288).** La lista de «Elegir…» decía «Rawls, Brakensiek  Saxton (1982)».

## 0. Lo que se encontró

- **La prueba de la interfaz** de 0.1.284
  (`_auditoria/P6_0284/INFORME_prueba_GUI_0.1.284.md`, H4) vio dos frases sin
  el «&»:
  - «Suelo (valores de Rawls, Brakensiek  Saxton (1982)):» con Brooks-Corey;
  - «Suelo (valores de Carsel  Parrish (1988)):» con van Genuchten.
- **La causa.** `_pick` da la frase a `QInputDialog.getItem`, y la etiqueta de
  ese diálogo tiene un compañero de teclado. Por eso Qt lee el «&» como marca de
  atajo y no lo dibuja. Comprobado: la etiqueta tiene compañero en cuanto el
  diálogo se muestra.
- **La fuente está bien escrita en todas partes:** `LIBRARY_SOURCES`, el API y
  el MCP (D273). Solo la ventana la perdía.
- **Al buscar otros «&»** apareció un caso más: el título del grupo «Surface
  Type & Algorithm» de *Surface Options*. Un título de grupo se lee igual, y
  se dibujaba «Surface Type  Algorithm», solo en inglés (en castellano es
  «Tipo de superficie y algoritmo»).

## 1. Qué cambia

- **`HydraulicPropertiesDialog._pick_prompt(mdl)`** devuelve la frase con el «&»
  doblado.
  - `_pick` se la pasa a `QInputDialog.getItem`, como antes.
  - `_pick_label` sigue devolviendo la fuente tal cual, para quien la lea.
- **El título del grupo** de *Surface Options* dobla también el «&».

## 2. Tests

`tests/test_pick_ampersand_v1287.py`, 4 casos que leen el texto tal como se
DIBUJA (con la regla de Qt: «&&» → «&», «&x» → «x»):
- la etiqueta del diálogo de «Elegir…» conserva el «&» con Brooks-Corey y con
  van Genuchten;
- `_pick` entrega a Qt la frase con el «&» doblado;
- el título de *Surface Options* conserva el «&».

Con el código de 0.1.286 fallan los 4: el título sale «Surface Type
 Algorithm».

**`test_pick_library_v1279`** comparaba el texto que se le daba a Qt, que es
justo el que perdía el «&». Ahora compara el texto que se dibuja. Su intención
(la lista nombra su fuente o dice que es ilustrativa) no cambia.

**Un camino descartado, que conviene recordar.** El primer arreglo construía el
diálogo y lo ejecutaba con `exec()`, para poder leerlo en un test.
`test_pick_library_v1279` sustituye `QInputDialog.getItem` para no abrir nada,
así que con `exec()` la corrida se quedó bloqueada (un diálogo modal sin
pantalla). Se paró y se volvió a `getItem`.

## 3. Verificación

- **Suite entera:** 5889 / 5889, con código de salida del proceso 0.
- **Tests de los diálogos implicados** (7 archivos, 86 casos): verdes.
- **`verificar_cierres.py` de la raíz:** `d288()` da CUBIERTO POR TEST;
  31 comprobaciones, ninguna bajada.

## 4. Lo que no se ha probado

- **A mano:** «Elegir…» con Brooks-Corey en la ventana.
