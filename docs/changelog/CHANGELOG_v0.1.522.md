# OGR Slip2D v0.1.522

**D462 cerrada: el diálogo de ajustes conserva un valor que no conoce, en vez de cambiarlo en silencio
por la primera opción del combo.** La propietaria eligió el 2026-11-28 la opción A en los once combos:
el valor se conserva y se dice.

## 0. Lo que se encontró

- **El mecanismo, reproducido con 0.1.521.** Once combos de `ogr_gui/dialogs/project_settings_dialog.py`
  elegían su opción con `max(0, findData(valor))`. Un valor que el combo no lista da −1, `max` lo
  convierte en 0 y `apply()` escribe esa primera opción al Aceptar, aunque el usuario no haya tocado el
  combo. La sonda de la ficha (cinco valores desconocidos en la página Métodos) dio
  `bisector materials fixed half_sine effective`, igual que en 0.1.485.
- **Los seis combos que la ficha no había ejecutado hacen lo mismo** (medido ahora con el test nuevo
  contra el diálogo de 0.1.521), y alguno de forma peor:
  - el método de agua subterránea desconocido pasaba a `none`, o sea, el proyecto se quedaba **sin
    agua**;
  - el desembalse pasaba a `b_bar`;
  - el tipo y el muestreo de Estadística, a `global_minimum` y `monte_carlo`;
  - la generación, a `pseudo_random`;
  - la norma de diseño, a `none`.
  Como en la fuerza entre dovelas (`effective`, cuando el defecto del ajuste es `total`), la primera
  opción ni siquiera es el valor por defecto.
- **El valor llega vivo hasta el diálogo:** `from_dict` tira las claves desconocidas, no los valores. El
  análisis ya decide qué hacer con él: Sarma se omite con su nota y un desembalse desconocido se
  rechaza. El diálogo era el único sitio que lo cambiaba sin decirlo. Eso no se toca aquí.
- **El mismo patrón en otros diálogos:** `grep -rn "max(0, .*findData\|max(0, i)\|max(0, j)" ogr_gui/`
  da 16 líneas fuera de este archivo, en `boundary_dialogs`, `contour_options_dialog`,
  `dxf_import_dialog`, `hydraulic_properties_dialog`, `material_properties_dialog` (cinco),
  `random_variables_dialog` (tres), `snap_dialog` y `main_window`. No se ha mirado cuáles leen un valor
  guardado. Por decisión de la propietaria, van a una ficha nueva del banco, **D470**.

## 1. Qué cambia

- **`ogr_gui/combo_values.py`, nuevo:** `select_stored_value(combo, valor)`.
  - Con un valor que el combo lista, lo selecciona y no añade nada.
  - Con uno que no lista, añade al final una entrada «Valor desconocido: <valor>», en cursiva, con ese
    valor como dato y un *tooltip* que dice que esta versión no lo conoce y que se conserva salvo que
    se elija otra opción, y la selecciona.
  - `None` (nada guardado) sigue eligiendo la primera opción.
- **`project_settings_dialog.py`:** los once combos pasan por el ayudante:
  - función y fuerza entre dovelas;
  - ángulos, resistencia y sentido del cortante de Sarma;
  - método de agua subterránea y desembalse;
  - tipo y muestreo de Estadística;
  - generación de números aleatorios;
  - norma de diseño.

  Los dos `max(0, …currentIndex())` del registro sísmico no leen un valor guardado y se quedan como
  están. Los manejadores conectados (`_on_standard`, `_on_method`) se conectan después de elegir, y
  `apply()` escribe `currentData()` sin convertirlo, así que un dato desconocido pasa intacto.
- **`ogr_gui/i18n/__init__.py`:** las dos cadenas nuevas con su español.
- **Ningún número del motor cambia.** Con un proyecto normal, los combos ofrecen exactamente las opciones
  de siempre. Lo comprueba el test, y el combo de ángulos con `ProjectSettings()` sigue teniendo sus
  cinco datos, que es lo que lee `d357()`.

## 2. Tests

`tests/test_settings_unknown_values_v1522.py`, clase `TestUnknownComboValues`, cinco tests:

- con un valor desconocido, cada uno de los once combos lo enseña como desconocido y `apply()` lo
  devuelve intacto;
- la entrada lleva su *tooltip* y va en cursiva;
- con cada valor conocido nada cambia: ni las opciones ni lo que se escribe;
- el combo de ángulos de un proyecto por defecto tiene sus cinco datos;
- la sonda de la ficha.

Contra el diálogo de 0.1.521 caen tres de los cinco, y el primero, en los once combos. Tests dirigidos
(`settings texts_details i18n methods_page design spanish budget license statistics`, 38 archivos): 564
en verde.

## 3. Lista de comprobación de la guía de interfaz

- **Identidad:** no cambia nada de la tabla. Ninguna marca comercial.
- **Acción:** no aplica, no hay acciones nuevas.
- **Diálogo:**
  - el valor mostrado es el del modelo, ahora también cuando es desconocido;
  - regla 7: el ayudante cambia lo que escribe `apply()`, y el test lo demuestra;
  - con un proyecto normal no hay entrada nueva, así que el tamaño del diálogo no cambia;
  - sin `exec()` ni `QMessageBox`;
  - probado sin pantalla y sin dejar estado.
- **Resultado, lienzo y proceso largo:** no aplica.
- **Mensaje:** la entrada dice qué pasa y qué hacer: se conserva salvo que se elija otra opción.
- **Suite:** `combo_values` no tiene gemela en `ogr_ui`. Si OGR-GUI quiere la regla para todos los
  programas, hay que pedírsela allí.

## 4. Prueba a mano pendiente

Abrir un `.ogr` con `"slice_angles": "optimized_future"`, entrar en Ajustes, ver la entrada «Valor
desconocido: optimized_future» en cursiva, pulsar Aceptar sin tocarla, guardar y comprobar que el
archivo conserva el valor. Queda apuntada en `PRUEBAS_A_MANO.md`.
