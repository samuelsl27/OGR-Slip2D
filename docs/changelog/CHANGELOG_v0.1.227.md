# OGR Slip2D v0.1.227

**D217 — el diálogo de materiales habla las unidades del proyecto, rechaza lo
que no puede guardar y no mueve lo que nadie editó.** Con los hallazgos del
mismo diálogo (B, C, D, F, H, L, M).

**D225 — la ventana de interpretación da el desplazamiento de Newmark en la
unidad del proyecto.** Un proyecto imperial lee pulgadas; antes leía siempre
centímetros.

Tercera versión de la tanda D215–D219. El banco no pasa por el diálogo: cero
filas movidas.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se encontró y lo que se decidió

| Id | Qué pasaba | Qué hace ahora |
|---|---|---|
| D217 | Las tablas corte-normal y discreta enseñaban kPa bajo «σ'ₙ (kPa)», «τ (kPa)» fijos y sin `tr()`; una fila que no eran números se descartaba sin decirlo | Cada columna declara su magnitud (`_TABLE_COLUMNS`); las celdas se convierten con la misma función que los parámetros, bajo una cabecera traducida con la unidad del sistema |
| B | Cambiar de material o añadir uno guardaba la tabla sin el control de filas de D209, que solo se hacía en Aceptar | El control se hace en Aceptar, al cambiar de material (la selección vuelve, sin recargar, y las filas se conservan) y antes de añadir |
| C | La discreta enseñaba la tabla por defecto de la corte-normal | `DEFAULT_POINTS` en cada modelo; el diálogo lo lee de ahí |
| D | Una tabla guardada vacía se enseñaba, y se guardaba, como la de defecto | Se enseña vacía, con el motivo en la etiqueta; el análisis la rechaza (H) |
| F | u constante llevaba « kPa» fijo, AEV no llevaba unidad, ninguno convertía y sus tooltips no se traducían | Presión en la unidad del proyecto, con su etiqueta; tooltips con `tr()` |
| H | La API aceptaba `points: []`, que da τ = 0 en todas las bases | `rules.function_points_refusal` (al menos un punto, valores finitos, τ ≥ 0, σ′ₙ estrictamente creciente); la preguntan la API, el análisis y el diálogo |
| L | Enseñar una tabla guardada como puntos antes de 0.1.218 y pasar a otro material la guardaba como tramos, sin revisar | Una resistencia que nadie editó se conserva tal cual (`is_unchanged`); se convierte al editarla |
| M | γ, γsat, u, AEV, φb, ru, Hu y B̄ redondeaban a 2–4 decimales (la clase de D181), y en unidades con factor cada Aceptar los movía un ulp (x·f/f) | Todas son `_PreciseSpinBox`; un valor cuya pantalla no cambió vuelve exacto (`_put_si`/`_get_si`; y en el panel, `_given`) |
| D225 | `_reported_value` pedía `units.unit_system()`, que no existe; un `except` desnudo lo tapaba | `get_system()`; sin proyecto, cm como antes; el `except`, solo para los errores de conversión |

**Una decisión que se mantiene de 0.1.225:** Aceptar juzga solo las
resistencias que la sesión cambió. Una tabla vacía que ya venía así no
bloquea el diálogo. Se enseña con su motivo en cuanto se muestra, y el
análisis la rechaza.

## 1. Los cambios

- **`ogr_gui/dialogs/material_properties_dialog.py`:**
  - `_StrengthParamPanel` reescrito: `_TABLE_COLUMNS`, conversión de celdas,
    `_given`, `table_headers`, `table_unchanged`, `is_unchanged`, y
    `unparsed_table_rows` para todas las tablas y valores no finitos;
  - `_store` conserva una resistencia sin tocar;
  - `_on_select` y `_add_material` se niegan con filas malas;
  - el aviso al cargar;
  - las casillas del material, precisas y con unidades.
- **`ogr_core/materials/builtin_models.py`:** `DEFAULT_POINTS` en las dos
  funciones de σ′ₙ.
- **`ogr_core/project/rules.py`:** `function_points_refusal`, preguntada por
  `strength_model_refusal`.
- **`ogr_gui/interpret_window.py`:** D225.
- **`ogr_gui/i18n/__init__.py`:** doce entradas.

## 2. Tests

- **`tests/test_material_tables_units_v1227.py` (20 casos, en psf):**
  - celdas y cabeceras;
  - Aceptar sin tocar, bit a bit;
  - la celda editada;
  - la función anisótropa;
  - la tabla por defecto de la discreta;
  - la tabla vacía y la vaciada;
  - las filas malas en Aceptar, al salir y al añadir;
  - `nan`;
  - la tabla antigua que no se convierte;
  - u y AEV;
  - nada redondea ni deriva (en SI y en psf);
  - la regla y la API;
  - la guarda de traducciones de las cabeceras;
  - Newmark.

  Contra 0.1.226 fallan 18 de 20: 12 por comportamiento y 6 por símbolo.
- **Cambia a propósito
  `tests/test_anisotropic_function_ranges_v1218.py::test_ok_refuses_a_table_that_is_not_ranges`.**
  Pasa a `test_ok_refuses_an_edited_table_that_is_not_ranges`, y se añade
  `test_a_table_left_alone_is_not_converted`: la tabla antigua se juzga como
  tramos cuando se edita, y sin editar se conserva (L).

## 3. El banco

- D217 y D225 cerradas, con `d217()` y `d225()`.
- Cero filas: el banco no pasa por la interfaz.

## 4. Caminos equivocados

- **La primera idea para la ida y vuelta exacta** era comparar valor a valor
  en `get_params`. Bastaba para los números, pero no para lo que el panel no
  edita: una tabla antigua que se enseña como filas. La pregunta que decide es
  otra, si se ha tocado ALGO de la resistencia (`is_unchanged`). Si no, no se
  reconstruye.
- **El reemplazo de `_store` hecho con un script perdió la barra de
  continuación** y dejó el bloque de reglas de Generalized leyendo `params`
  cuando ya era None. Se reescribió a mano antes de ejecutar nada.
- **La tabla guardada vacía iba a rechazarse en Aceptar.** Choca con la regla
  de 0.1.225 (Aceptar juzga lo que la sesión cambió, para que un material que
  el diálogo no puede editar no lo bloquee). Se enseña el motivo al cargar.

## 5. Verificación

| Comprobación | Resultado |
|---|---|
| Selecciones dirigidas | 259 casos, en verde |
| Suite entera | 5058 de 5058 |
| `d217()` y `d225()` | CUBIERTO POR TEST; NO SE SOSTIENE contra 0.1.226 |
| `--seco` completo | 166 cierres; 0 bajadas, 0 subidas, 0 nuevas |
| `auditoria_invariantes.py` | 0 ERROR en el 02 y en la raíz |
