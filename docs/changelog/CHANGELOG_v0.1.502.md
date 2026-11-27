# OGR Slip2D v0.1.502

**El diálogo Contour Options de Interpretar propone, ajusta y restaura la escala que la ventana
dibuja en una corrida Ky o Newmark.** Desde 0.1.500 (D438) el campo del factor de una corrida
sísmica pinta el número de la corrida, con su propia escala. El diálogo seguía con la del factor.
Ningún número del motor cambia.

## 0. Lo que se encontró

Lo avisó la sesión de OGR-GUI. Comparó `for_reported` con su gemela `ogr_ui.contours`, leyó el
diálogo de Slip2D y sacó tres desajustes, solo leyendo el código. Se midieron en vivo antes de
tocar nada (regla 6), con la ventana Interpretar y el diálogo construido sin `exec()`.

- **Casos medidos:**
  - Ky: el talud de ejemplo con c = 20 kPa, rejilla 5×5×3, el de
    `test_interpret_seismic_centres_v1500`;
  - Newmark: el caso de D437 sin talud arriba (c = 12 kPa, 5×5×6, sinusoide de 0,3 g y 2 Hz durante
    4 s más 2 s de calma). El Newmark del test de 0.1.500 no sirve: sus 74 desplazamientos son 0,
    y ahí el percentil no se nota.
- **1. El percentil: se confirma, y solo afecta a Newmark.**
  - Con Ky, el diálogo y el dibujo usan los dos el 0,98 y coinciden (0,3117 – 0,9661).
  - Con Newmark, la ventana dibuja de 0 a 31,083 cm, que es el desplazamiento de la crítica. El
    diálogo proponía 0 – 17,862 cm al abrirse (el constructor reajusta al 0,98), al volver a marcar
    la casilla y en *Fit*.
  - Con la casilla marcada, la ventana reajustaba con 1,0 al aceptar y el dibujo salía bien. Con la
    casilla desmarcada o tras *Fit*, el máximo quedaba fijo en 17,862 y la crítica caía fuera de la
    escala.
- **2. *Restore Defaults*: se confirma, con Ky y con Newmark.** Daba 0 – 6 en 24 bandas Rainbow
  (`for_field("fos")`). Además ponía «invertir» siempre a falso, así que en Newmark el rojo caía en
  el extremo no crítico.
- **3. Los 24 intervalos al tocar la casilla: no se reproduce.** Al desmarcar y volver a marcar se
  quedan en 8. `_on_auto_toggled` no cambia los intervalos. El `setValue(24)` es de
  `_range_0_to_6`, el botón del preajuste «0 a 6» de la leyenda del factor, que pone 24 a propósito.
  En una corrida sísmica ese botón ponía justo la escala que D438 quitó.
- **De paso, un fallo latente de 0.1.500, sin medir en un caso real.** La ventana ajustaba con
  percentil 1,0 según la magnitud de la corrida, sin mirar el campo. Un campo hidráulico (altura
  total, presión) de una corrida Newmark con filtración se habría ajustado al máximo, sin el
  percentil. Ahora el 1,0 es solo para el campo del factor.

## 1. Qué cambia

Arreglo con el OK de la propietaria (2026-11-27). Para el botón «0 a 6» se aplicó la
recomendación, deshabilitarlo con su porqué, porque la pregunta quedó sin respuesta.

- `ogr_gui/contours.py`: `ContourSettings.fit_percentile_for(caption)`, la única regla del
  percentil: 1,0 para un desplazamiento de Newmark y 0,98 para lo demás. La usan la ventana y el
  diálogo.
- `ogr_gui/dialogs/contour_options_dialog.py`: el diálogo recibe `quantity` (`"fos"`, `"ky"` o
  `"newmark"`; por defecto `"fos"`, el diálogo de siempre):
  - ajusta con el percentil de la magnitud al abrir, en la casilla y en *Fit* (`_percentile`);
  - *Restore Defaults* vuelve a la escala de la magnitud (`_start`: `for_reported` en el campo del
    factor de una corrida sísmica) y restaura «invertir» desde ella;
  - el botón «0 a 6» se deshabilita en el campo del factor de una corrida sísmica, con un
    *tooltip* que dice por qué y qué usar en su lugar. En los demás casos sigue con su *tooltip* de
    siempre. El estado se recalcula al cambiar de campo.
- `ogr_gui/interpret_window.py`: abre el diálogo con `quantity=self._run_quantity()`, y su ajuste
  usa `fit_percentile_for` solo en el campo del factor.
- `ogr_gui/i18n/__init__.py`: el castellano del *tooltip*, en los términos del programa: «cálculo»
  y no «corrida» (`test_texts_details_v1418`), y «por defecto» y no «predeterminado»
  (`test_voice_and_terms_v1325`). Por eso no cita el rótulo que Qt da al botón («Restaurar los
  valores predeterminados»), sino «el botón de restaurar los valores por defecto». Los dos tests
  lo cazaron en la primera suite entera de esta versión.
- **gemela en ogr_ui:** `contours` (`fit_percentile_for`). En `ogr_ui` esto ya está resuelto con
  `ContourField.fit_percentile` y `start`, y la casilla no toca los intervalos. Hay que avisar en
  OGR-GUI.

## 2. Lista de comprobación de la guía de interfaz

- Identidad: la leyenda del factor (Rainbow, 0–6, 24 bandas) y su botón siguen igual en una
  corrida de factores. Ningún nombre comercial.
- Acción: no aplica, no hay acciones nuevas. El botón «0 a 6» se deshabilita con su porqué y no
  se oculta (D-4).
- Diálogo: sus valores por defecto salen de la corrida, no de literales. El tamaño y la
  disposición no cambian. Sin `exec()` en los tests.
- Resultado y lienzo: la escala que propone el diálogo es la que dibuja la ventana (D-12).
- Mensaje: el *tooltip* dice qué pasa y cómo seguir.
- Suite: gemela en ogr_ui, anotada arriba.

## 3. Tests

- `tests/test_contour_dialog_seismic_v1502.py` (nuevo, 8 tests). El caso Newmark es el de
  `test_newmark_upslope_critical_v1499` con 3 incrementos de radio, que conserva la separación: el
  máximo de la ventana es 31,083 cm y el percentil 0,98 da 19,589.
  - la premisa: el percentil 0,98 recortaría la crítica;
  - con Newmark, los cuatro caminos (abrir, casilla, *Fit*, *Restore Defaults*) dan el máximo de la
    ventana, y *Restore Defaults* da la escala de la corrida;
  - con Ky, *Restore Defaults* da la escala del Ky;
  - el botón «0 a 6»: deshabilitado con su porqué en Ky y en Newmark, igual que siempre con factor;
  - con factor, nada cambia.

  El test pasa la magnitud solo si el diálogo la acepta, así que contra 0.1.501 falla por lo que
  propone y no por la firma: fallan 6 de 8 (pasan la premisa y el control de factores).
- Áreas `contour`, `interpret`, `legend`, `i18n`, `translation`, `dialogs_fit`, `terms_spanish` y
  `seismic`: 460 en verde.

## 4. Suite

- La primera suite entera dio 2 fallos, los dos del castellano del *tooltip* (§1). Corregido y
  repetida: 7666 casos, 7664 pasan, 0 fallan, 2 saltados, sin fugas ni tramos muertos. La
  última serie fue hace 39 commits.
