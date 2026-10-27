# OGR Slip2D v0.1.370

**Los textos fijos que seguían en inglés con la interfaz en castellano pasan por `tr()`: las diez fórmulas
con palabras de *Definir materiales*, la leyenda y el «[SF]» de *Interpretar agua subterránea*, la
convergencia de la estadística, «Añadido line», el «[deg]» del PDF, el nombre propuesto del informe y
los filtros y títulos de los diálogos de archivo (D344, cerrada).** Octava versión de la tanda P8l.

## 0. Lo que se encontró

- **Por qué no los vio ningún censo** (la regla 2 tiene un test de claves y dos presupuestos):
  - un diccionario de clase no es una llamada a `tr()`. `_FORMULA_TEXT` se escribía en su etiqueta sin
    traducir, y el censo de claves solo lee llamadas literales `tr("…")`;
  - los `label=` y `set_ylabel` de matplotlib y los `QFileDialog` quedaban fuera de la lista de
    receptores del censo de 0.1.318. Por eso, además de los filtros, había **tres títulos** sin `tr()`:
    «Export Image» y «Export Raw Data» en Interpretar, e «Import grid points» en la rejilla de presiones;
  - «Añadido line» era `tr("Added %s") % kind.value`: la plantilla se traducía, y el valor del enum era
    un dato.
- **Los nombres de las anotaciones:** las acciones del menú son verbos («Dimension Length» es «Acotar
  longitud»), y en «Anotación añadida: …» hace falta un sustantivo. La tabla nueva de `labels.py` nombra
  los dos tipos de cota como sustantivos («Cota de longitud», «Cota angular»). La plantilla castellana
  pasa de «Añadido %s» a «Anotación añadida: %s», que vale para cualquier género.
- **El mismo enum salía en dos sitios más:** la lista de *Convertir herramienta en contorno* y la
  primera columna de *Gestionar anotaciones*. Usan la misma tabla.
- **El término de la probabilidad de rotura:** el programa dice «probabilidad de rotura» en todas partes
  menos en una entrada antigua, «probability of failure (%)» → «probabilidad de fallo (%)», en
  Interpretar. Las claves nuevas usan «rotura». La antigua se deja y se dice aquí.
- **Sin ficha, visto al pasar:** *Gestionar foco* enseña el tipo del objeto de foco por el valor de su
  enum (`o.kind.value`). Es la misma familia y queda para otra ficha.
- **Un fallo de mi test, que conviene recordar:** la primera versión del test del nombre del informe
  llamaba a *Generar informe* sin resultados, y la acción lo dice con un `QMessageBox.warning` **modal**.
  Sin pantalla esperó para siempre (diez minutos sin CPU) hasta que se mató. Ahora calcula el ejemplo
  antes, acepta el diálogo de figuras y convierte cualquier otro modal en un fallo
  (`_no_modals` de `test_fos_chart_v1308`).

## 1. Qué cambia

- **`material_properties_dialog.py`:** la fórmula se traduce al escribirla. Las diez que llevan palabras
  tienen su castellano con los mismos símbolos; las que son solo símbolos no llevan entrada y `tr()` las
  devuelve tal cual.
- **`interpret_groundwater_window.py`:** «[SF]» es «[FS]» en castellano (`tr("SF")`), y la leyenda de la
  superficie libre usa la clave de su casilla, «Superficie freática (P=0)».
- **`statistics_window.py`:** la leyenda y el eje derecho de la convergencia.
- **`labels.py`:** `ANNOTATION_KIND` y `annotation_kind_label`, usados en la barra, en la lista de
  conversión y en el diálogo de anotaciones.
- **El PDF:** «Friction Angle [°]» en inglés y «Ángulo de rozamiento [°]» en castellano, como la tabla
  de dovelas escribe φ. **Es un cambio deliberado del inglés.**
- **Los diálogos de archivo:** el nombre propuesto del informe (`tr("{0}_report.pdf")`, «…_informe.pdf»),
  los filtros con palabras de la ventana, de Interpretar y de la rejilla de presiones, y los tres títulos.
  Los filtros que son solo formatos («CSV (*.csv)», «PNG (*.png);;JPEG (*.jpg)») no cambian.
- **Castellano:** 29 entradas nuevas y la plantilla de «Added %s».

## 2. Tests

- **`tests/test_texts_spanish_v1370.py`** (nuevo, 10 casos):
  - cada fórmula con palabras tiene su castellano con los mismos símbolos, y las demás no llevan ninguna
    palabra inglesa; el diálogo la enseña en castellano;
  - *Interpretar agua subterránea* («[FS]», la leyenda de la superficie freática), la convergencia, la
    anotación añadida, el PDF y el nombre y el filtro del informe, por las ventanas reales y en
    castellano;
  - **el censo que faltaba:** ningún título o filtro literal de un `QFileDialog` de `ogr_gui` lleva una
    palabra fuera de `tr()`, y cada filtro traducido conserva sus patrones `(*.ext)`.
- **Cambios deliberados:**
  - `test_report_spanish_v1355` congelaba «Friction Angle [deg]» en el inglés del informe; ahora espera
    «[°]»;
  - `test_gui_spanish_v1318` y `test_window_english_left_v1293` exceptuaban el f-string del nombre del
    informe; el primero tiene comprobación de fantasmas, así que la excepción se va con él;
  - `test_labels_spanish_v1321` recorre también la tabla de anotaciones.

**Con el código de 0.1.369 fallan 9 de los 10.** El que pasa es la guarda de las fórmulas de solo
símbolos, que se cumplía también antes.

## 3. Verificación

- **El test de esta versión:** 10/10.
- **Los vecinos:** 588/588 en 39 archivos (diálogos de materiales, agua subterránea, estadística,
  anotaciones, informe, traducciones y los censos de `tr()`).
- **Suite entera:** 6617 de 6618, **con un fallo de tiempo**. `test_optimizations_v111.py::
  test_grid_completes_quickly` exige que una búsqueda en rejilla de 507 círculos tarde menos de 5 s, y
  tardó 11,1 s. Lo que se midió antes de no repetirla:
  - la corrida entera duró unas 3 h 50 min, frente a 91–130 min de las siete anteriores de la tanda: la
    máquina estuvo cargada;
  - ese test, solo, pasa;
  - la misma búsqueda, en un proceso aparte con la guarda `__main__`, tarda 2,5 / 2,3 / 2,1 s en
    paralelo y 2,5 s en serie;
  - esta versión no toca la búsqueda.

  Por decisión de la propietaria no se repite: la suite entera de 0.1.371, que contiene todo esto, hace
  de confirmación antes de subir. **Una trampa al medir**, que conviene recordar: el primer script de
  medida no tenía la guarda `__main__`, y con *spawn* cada trabajador del pool volvía a lanzar la
  búsqueda; dio 12–14 s y parecía confirmar una regresión que no existe.
- **Banco:**
  - `verificar_cierres.py` de la raíz, entero: 105 comprobaciones, 0 bajadas; `d344()` da
    **CUBIERTO POR TEST**;
  - el del manual 02 en seco: 242, iguales;
  - D344 retirada, `PAQUETES` podado, la cadena de P8 tachada, prompts regenerados (35), las dos
    auditorías con 0 ERROR e instantánea `Evaluaciones/0.1.370` (983 y 3284 archivos).

## 4. Pendiente

- La tanda termina con D352 (0.1.371): la tabla de puntos de *Definir materiales*.
- Sin ficha, para decidir: *Gestionar foco* con `o.kind.value`, y la entrada antigua «probabilidad de
  fallo (%)» frente a «rotura» en el resto del programa.
