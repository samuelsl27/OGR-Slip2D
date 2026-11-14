# OGR Slip2D v0.1.452

**El factor que Interpretar escribe junto al Ky dice con qué kh se calculó (D409).** En una corrida «Calcular Ky»,
Interpretar escribe junto al coeficiente sísmico crítico el factor de la crítica: «FS(0) = …», y «ODF(0) = …» con
norma (`_reported_value`, en la cursiva del resumen). «(0)» quiere decir «sin sismo». Pero ese factor es el del kh del
proyecto, y solo es el de kh = 0 cuando el proyecto no aplica ninguno. Medido con 0.1.451 (57e9d80) en el plano del
usuario de 0.1.429 (arena seca a 30 grados, Janbu), con kh = 0,10:

| norma | 0.1.451 | ahora | cuña a 0,10 | cuña a 0 |
|---|---|---|---|---|
| sin | «FS(0) = 1.454» | «FS(kh = 0.1) = 1.454» | 1,454067 | 2,020726 |
| custom ÷1,25 | «ODF(0) = 1.163» | «ODF(kh = 0.1) = 1.163» («FSD(kh = 0.1)» en castellano) | 1,163254 | 1,616581 |

Con kh = 0, el texto de siempre, byte a byte. **Ningún número cambia:** es el rótulo. Es la vigesimoquinta versión de
la tanda P10 y la última del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.451:** el REPRODÚCELO da su salida, la misma que con 0.1.435 y con 0.1.447.
- **La rama del `FactorReport` sobra.** El plan leía el kh «del resultado si lo guarda y si no del informe de la
  corrida». Los nueve métodos y el desembalse guardan `details["kh"]`, y el `FactorReport` no lleva kh: solo tiene la
  norma, lo factorizado y sus notas de diseño, y la nota `method.seismic_kh_replaced` va a los avisos de la corrida.
  Lo único que llega sin `details["kh"]` es el doble de
  `tests/test_seismic_interface_v1127.py`, que lee 0 y conserva «FS(0)». Por decisión de la propietaria, una sola
  rama.
- **La regla es la del informe.** `factor_kh(item)`, en el núcleo desde D408 (0.1.449), es la que usa ya el informe PDF
  para su «…of this surface, kh = 0.1». Interpretar la pregunta ahora: un mismo factor se nombra igual en las dos
  puertas.
- **«(0)» es kh = 0 con el kv del proyecto.** El resolvedor del Ky conserva el kv (`yield_acceleration.py`), y eso es lo
  que llama FS(0). Con kh = 0 y kv ≠ 0 el rótulo de hoy es correcto, y la regla mira solo el kh.
- **Ninguna cadena nueva.** «ODF» ya pasa por `tr()` («FSD»), y «(kh = %g) = %.3f» es notación, como el «(0) = %.3f»
  de siempre. El kh va con `%g` (0,075 no sale «0.07») y con el punto de todos los números de la ventana.
- **Las tres llamadas de `_reported_value`:** solo el resumen enseña este texto; las otras dos lo descartan. Cambia
  solo la cursiva del resumen.
- **La revisión adversaria (un agente) no encontró fallos en el código.** Comprobó que no hay camino por el que el
  rótulo mienta: los nueve métodos y el desembalse guardan su kh, `_solve_ky` no lo pisa, la norma no lo factoriza
  con Ky, y no queda ningún otro «FS(0)». Encontró, y se arregló:
  - **(media) ningún test protegía el formato del kh,** que este changelog daba por fijado. Cuatro mutantes
    sobrevivían, entre ellos `%.1f`, que habría rotulado «kh = 0.1» un kh de 0,075. Además, Interpretar y el informe
    escriben el kh cada uno en su frase. Ahora hay un caso con 0,075, 0,125 y 0,1 + 0,05, y otro que pasa un kh de
    0,075 por las dos puertas;
  - las desviaciones de Janbu que el test citaba eran relativas sin decirlo, y la banda de tres decimales no
    distinguía ese residuo del redondeo. El test fija ahora la tolerancia del método a 1e-8, compara el factor del
    motor con la cuña a 1e-9, y el número impreso con el factor del resultado, carácter a carácter;
  - este changelog situaba mal la nota del kh, un docstring pasaba de 100 caracteres y un comentario del informe daba
    D409 por abierta.

  Se reporta sin tocar:
  - el rótulo no nombra el kv, igual que el informe: con kh = 0,1 y kv = 0,05 da «FS(kh = 0.1) = 1.474»;
  - `%g` escribe con exponente un kh muy pequeño («FS(kh = 1e-05)»), y el informe igual;
  - la rama sin norma escribe «FS» sin `tr()`, cuando el resto de la interfaz dice «FoS». Ya pasaba con «FS(0)».

## 1. Qué cambia

- **`ogr_gui/interpret_window.py`, `_reported_value`:** el rótulo del factor junto al Ky lleva el kh del resultado
  (`factor_kh`): «FS(kh = 0.1)» u «ODF(kh = 0.1)» con un kh distinto de cero, y «FS(0)» u «ODF(0)» con cero o sin kh
  guardado.
- **`ogr_gui/reported_quantity.py`:** el docstring de `fos_label`, que nombraba «FS(0)», dice la regla.

## 2. Qué se probó

- **`tests/test_interpret_fs_kh_v1452.py`** (12 casos, alrededor de 1,5 s), contra la cuña pseudoestática de Coulomb
  (Kramer 1996, §10.6.1.1):
  - con c = 0 el peso se va: F(kh) = (cos β − kh·sin β)·tan φ / (sin β + kh·cos β). Valen 1,454067 y 1,163254 a 0,10, y
    2,020726 y 1,616581 a 0;
  - con kh = 0,10, el rótulo dice el kh y su número es el factor del resultado, que es F(0,10) (a 1e-9, con la
    tolerancia del método a 1e-8) y no F(0), con norma y sin ella;
  - el kh escrito con `%g`: 0,075, 0,125 y 0,1 + 0,05, y un kh de 0,075 igual en Interpretar y en el informe;
  - el Ky de al lado sigue en tan(φ − β), igual que con kh = 0;
  - en castellano, «FSD(kh = 0.1)»;
  - se lee del resultado: cambiar el kh del proyecto después de calcular no cambia el rótulo;
  - por el resumen real (`_SummaryDock.show_result`), que desde D401 enseña la crítica del usuario;
  - con kh = 0, «FS(0)» y «ODF(0)» byte a byte, y un resultado sin `details["kh"]` también.

  Tolerancia: con la del proyecto (0,005), Janbu se aparta de la cuña 3,3e-6 sin norma y 2,0e-4 con ella, en
  absoluto (la medida de la revisión). Por eso el test fija la del método a 1e-8.
- **Discriminación:** en el árbol de 0.1.451, sin el buscador editable, fallan los 7 casos del rótulo («FS(0) =
  1.454», también los del formato del kh). Pasan las formas cerradas, la premisa, el Ky y los dos controles.
- **Mutantes** (`mutants_d409.py`, en el banco): 11, todos muertos:
  - el kh nunca dicho, o dicho también a 0;
  - el kh del proyecto abierto;
  - el kh con dos decimales;
  - «ODF» sin traducir;
  - un resultado sin su kh que revienta;
  - y los cinco de la revisión: el kh con un decimal, como `str`, redondeado a un decimal, con dos cifras
    significativas, y el informe que redondea el suyo.
- **Vecinos**, con los patrones `interpret seismic reported_caption design_factor material_tables seismic_interface
  report_seismic i18n voice_and_terms version_consistency` (cada uno comprobado con `--list`): 459 casos en verde en 29
  archivos.
- **La suite entera** con `--jobs 4`, tras los arreglos de la revisión: **7675 casos, 7674 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (30 commits desde la última).

## 3. Qué queda

- **El plan de 0.1.448–0.1.452 está TERMINADO.** En P10 quedan, por su orden, D416 (0.1.453), D417, D410, D425, D426,
  D407, D427 y D428, y sin versión D429–D440 (D437–D440 las abrió este plan). Después viene Sarma.
