# OGR Slip2D v0.1.500

**D438: Interpretar, Minimum Surfaces y la vista `minimum_per_centre` del API leen una corrida Ky o
Newmark por lo que la corrida minimiza.** Hasta esta versión, en una corrida cuya crítica es la de
menor Ky, esas tres puertas enseñaban el menor factor de cada centro. Ningún número del motor
cambia.

## 0. Lo que se encontró

- **La medida de la ficha, repetida con 0.1.499** (`_auditoria/P10_D419_D428/medir_d423.py`): el
  talud de ejemplo con c = 20 kPa, rejilla 5×5×6, Bishop. Con Ky sin norma, la crítica tiene Ky
  0,2941 en (40, 45), y las tres puertas enseñaban otra cosa:
  - la leyenda de Interpretar decía «Factor of safety», con la marca en 1,6237;
  - su celda más baja era «(34, 29) — FoS = 1.529»;
  - la primera fila de la vista del API era fos 1,528675, en (34, 29).

  Con Newmark y la norma 1,05 pasaba lo mismo. Idéntico a 0.1.485.
- **Con el arreglo**, en el mismo guion:
  - con Ky, la leyenda es «Critical seismic coefficient» con la marca en 0,2941, y la celda más
    baja «(40, 45) — Ky = 0.2941»;
  - con Newmark, la leyenda es «Newmark displacement [cm]» con la marca en 1,2163;
  - con factor y norma no cambia nada: «Over-design factor», 1,4559, (34, 29).
- **El mapa pasa de 30 celdas a 27 (o 28).** Las superficies sin Ky por debajo del techo no tienen
  el número de la corrida y quedan fuera, como en la figura del informe desde D423, que ya
  contorneaba 27 centros.
- **Los colores fijos del mapa** (rojo por debajo de 1, naranja hasta 1,5…) son bandas de factor.
  Con contornos activos, el mapa se pinta con la escala de la ventana, así que se ven con la escala
  nueva. Con los contornos apagados, el mapa de una corrida sísmica ya no se pinta: esas bandas no
  significan nada para un Ky. El de una corrida de factores sigue como estaba.
- **Lo que no cambia, a propósito:** el filtro de superficies (FS mínimo y máximo, las N más bajas)
  sigue filtrando por el factor, que es lo que dice su diálogo. El campo de contornos sigue
  llamándose «Factor of safety» en el diálogo de opciones, aunque en una corrida sísmica pinte el
  número de la corrida. Las dos cosas quedan anotadas sin ficha.

## 1. Qué cambia

Opción **(a)** en las tres puertas, y la vista conserva su clave. Decisiones de la propietaria del
2026-11-27. `minimum_per_centre` no cambia: las puertas llaman a `critical_per_centre`, que en una
corrida de factores es `minimum_per_centre` bit a bit.

- **API** (`ogr_api/ops/statistics.py`): en una corrida Ky o Newmark, la vista `minimum_per_centre`
  da las filas de `critical_per_centre`, ordenadas como la corrida ordena sus superficies
  (`SearchResult.rank_key`, D437). La primera fila es la crítica, y la vista añade `ranked_by:
  "ky" | "newmark_displacement"`. En una corrida de factores la salida es la de siempre, sin
  `ranked_by`. La descripción de `results_query` en el servidor MCP lo dice en una línea.
- **Lienzo** (`ogr_gui/canvas/canvas_view.py`):
  - Minimum Surfaces dibuja `critical_per_centre`;
  - el mapa de centros pinta el número de la corrida de cada centro, con su *tooltip* («Ky = …» o
    el desplazamiento en la unidad del proyecto);
  - las líneas se colorean con ese mismo número (`SlipSurfaceItem(colour_value=…)`) y se dibujan
    en el orden de la corrida, la más crítica al final;
  - el *caption* de la corrida se pregunta una vez por dibujo, no una vez por superficie (la trampa
    de D423).
- **Interpretar** (`ogr_gui/interpret_window.py`):
  - el campo del factor, en una corrida sísmica, toma los valores de la corrida, siempre de la
    población de la búsqueda (D401);
  - la leyenda lleva por título la magnitud con su unidad, y la marca va en el número de la crítica;
  - la escala de partida es `ContourSettings.for_reported`: rango automático en ocho bandas, rojo
    en el extremo crítico (el menor Ky, el mayor desplazamiento), como la figura de D423. Para un
    desplazamiento, el rango llega hasta el máximo, porque el percentil que recorta un factor
    profundo cortaría la crítica;
  - al cambiar de método se toma la escala de la magnitud nueva, salvo que el usuario haya puesto
    la suya en las opciones de contornos.
- `ogr_gui/reported_quantity.py`: `centre_value` y `centre_scale_title`, la única regla de qué
  número y qué título pinta la ventana.
- `ogr_gui/i18n/__init__.py`: el castellano de los dos *tooltips* nuevos.
- **gemela en ogr_ui:** `contours` (el método `for_reported`) e `i18n` (las entradas nuevas). Hay
  que llevarlo a la sesión de OGR-GUI.

## 2. Lista de comprobación de la guía de interfaz

- Identidad: la leyenda del factor (Rainbow, 0–6, 24 bandas) sigue igual para los factores. Una
  corrida Ky o Newmark tiene ahora su propia escala, que es lo que decidió la propietaria en D438.
  Ningún nombre comercial.
- Acción: no aplica, no hay acciones nuevas. El modo Minimum Surfaces es el del menú Data.
- Diálogo: no aplica, ningún diálogo cambia.
- Resultado y lienzo: la leyenda dice la magnitud y la unidad (D-12), y el rango es el de la
  corrida. Los colores de objeto no cambian.
- Proceso largo: no aplica.
- Mensaje: los *tooltips* dicen la magnitud que enseñan.
- Suite: gemela en ogr_ui, anotada arriba.

## 3. Tests

- `tests/test_interpret_seismic_centres_v1500.py` (nuevo, 9 tests, rejilla 5×5×3, que conserva la
  separación: la crítica está en (40, 37) con Ky 0,3117 y el menor factor en (34, 29)):
  - la premisa, medida;
  - la vista del API: su primera fila es la crítica, cada fila es la de su centro y con Newmark
    ordena por el desplazamiento; con factor, la de siempre;
  - la ventana: las celdas, la leyenda y Minimum Surfaces (por la puerta del menú,
    `_set_surface_mode`), con Ky, con Newmark y con factor.

  Contra 0.1.499 fallan 5 de 9.
- Áreas `interpret`, `report_figures`, `results_query`, `mcp_server`, `contour`, `canvas`,
  `legend`, `i18n`, `translation`, `seismic`, `newmark`, `minimum` y `heatmap`: 612 en verde.
- Banco: `d438()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST**.
