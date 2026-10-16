# OGR Slip2D v0.1.319

**El lienzo, sus ayudas, el panel de resultados y la barra de estado hablan
castellano (D300, familia b).** Tercera versión de la tanda P8h.

## 0. Lo que se encontró

- **La familia (b) tenía 47 sitios** con las reglas de 0.1.318:
  - el lienzo y sus elementos gráficos: ayudas emergentes de regiones,
    cargas, soportes y vértices, y menús contextuales;
  - las ayudas de datos (`data_tips.py`);
  - el panel de asignar materiales, el de resultados, la barra de estado y
    la cabecera de la terminal.
- **Ocho de los 47 no son texto que traducir:**
  - una magnitud con su unidad (`{} kN/m²`, `{} → {} kN/m²`, `{} kN/m`,
    `{}: {} kPa`);
  - las coordenadas del puntero en la leyenda y en la barra de estado
    (`X: …   Y: …`), y el formato que se pide al teclear (`x, y`).

  Van a `EXCEPTIONS` con su razón. Envolverlos pediría una traducción
  idéntica, que `test_i18n_coverage_v141` cuenta como olvido.
- **Las 30 ayudas de los modos de herramienta** que nombraba el plan ya se
  traducían por variable desde v0.1.168 (D101), con su propio censo. No había
  nada que hacer en ellas.
- **«FoS» de la cabecera del panel de resultados pasa a «FS»,** el término
  castellano que ya usaba la ventana de interpretación (0.1.318).
- **El convertidor de la tanda no añadió la importación de `tr`** en
  `widgets/terminal.py`, el único archivo convertido que no la tenía.
  - El test de AST no lo ve, porque cuenta textos y no nombres.
  - Lo cazó el test de la ventana: `MainWindow()` lanzaba `NameError` al
    construir la terminal.
  - Se añadió a mano, y se comprobó con el AST que ningún otro archivo de
    `ogr_gui` llama a `tr` sin importarlo, tampoco en las copias de 0.1.320
    y 0.1.321.

## 1. Qué cambia

- **39 sitios pasan por `tr()`** en `canvas/canvas_view.py`,
  `canvas/graphics_items.py`, `data_tips.py` y `widgets/`
  (`assign_materials_panel`, `results_dock`, `status_bar`, `terminal`). El
  inglés queda idéntico.
- **30 claves nuevas con su castellano** («presión intersticial», «Fuerza en
  la cabeza», «Definir grieta de tracción…», «Deshacer el último vértice»…),
  sin ninguna clave duplicada nueva.
- **`tests/test_gui_spanish_v1318.py`:**
  - `BUDGET` baja de 94 a **47**;
  - ocho excepciones nuevas, con su razón;
  - una clase nueva, `TestTheMainWindowSpeaksSpanish`.

## 2. Tests

`TestTheMainWindowSpeaksSpanish` abre la ventana principal real:

- **en castellano,** las cabeceras del panel de resultados son «#», «FS»,
  «Método», «Centro X», «Centro Y» y «Radio»;
- **control:** en inglés siguen siendo «#», «FoS», «Method», «Centre X»,
  «Centre Y» y «Radius».

**Con el código de 0.1.318 fallan 3 de los 6 casos del archivo:**

- el recuento, que es 86 con las excepciones de esta versión;
- el presupuesto exacto;
- las cabeceras en castellano.

El control en inglés, *Interpret* y las excepciones pasan en los dos árboles.
Se corrió sobre un `git archive` de 0.1.318, sin el buscador editable.

## 3. Verificación

- **Los tests vecinos**, antes de la suite:
  - el test de AST, i18n y la consistencia de versión, 26/26;
  - lienzo, barra de estado, leyenda, terminal, resultados, menús en
    castellano, la ventana en inglés, idioma y traducciones de Qt, 62/62.
- **Suite entera:** 6117/6117, `EXIT=0`, 54 min.
- **Banco:** `verificar_cierres.py` entero, 59 comprobaciones y 0 bajadas.
  D300 sigue abierta hasta 0.1.321.
- **Ningún número cambia:** son textos, y el inglés es idéntico.

## 4. Pendiente

- **Las familias (c) y (d)** (0.1.320), y las etiquetas y D240 (0.1.321).
- **A mano:** el lienzo con Español guardado: ayudas de cargas, soportes y
  regiones, menú contextual de un contorno, panel de resultados y barra de
  estado.
