# OGR Slip2D v0.1.514

**D455 (parte de Slip2D): el panel de datos de dovela de Interpretar escribe sus fuerzas en kN/m.**
El panel escribía sus nueve fuerzas en «(kN)», pero `LEMResult` las da por metro de talud, y la tabla
de caras de Sarma del informe ya escribe `[kN/m]`. Por decisión de la propietaria del 2026-11-28 hay
una sola unidad, **kN/m**. Ningún número cambia, solo la unidad escrita. La cabecera «Weight [kN]» de
la tabla de dovelas del informe es de OGR Core y se pide allí (§4). D455 no cierra hasta que llegue esa
fijación.

## 0. Lo que se encontró: censo de las fuerzas por metro

| Dónde | Qué escribe hoy | Veredicto |
|---|---|---|
| Panel de dovela de Interpretar (`_SliceDataDock.FIELDS`) | 9 filas en «(kN)»: Weight W, Base normal force N, Driving shear W·sinα, E/X/E′ left/right | **Mal**: pasan a «(kN/m)», con su castellano |
| Informe PDF, tabla de dovelas (OGR Core 0.2.14, `report_generator.py:937`) | `Weight\n[kN]` | **Mal**: se pide a OGR Core (§4) |
| Informe PDF, tabla de caras de Sarma (`report_generator.py:1079-1080`) | `PW`, `E`, `E′`, `X` en `[kN/m]` | Bien |
| Graph Query de Interpretar | «Slice weight» y el resto, **sin unidad** | No dice nada falso. Fuera de esta ficha |
| CSV de dovelas (`_export_slice_data_csv`) y agente (`slice_rows`, `results_get`, `results_query`) | Claves sin unidad (`weight`, `base_normal_force`…) | No dicen nada falso, y no se tocan: cambiarlas rompería a quien las lee |
| Guía del agente (`ogr_mcp/guide.py:47`) | «forces in kN (per metre out of plane)» | Se precisa: «forces in kN/m (per metre out of plane)». Las listas de unidades SI («m, kN, kPa…») nombran la unidad de fuerza y se quedan |
| Capacidad de un soporte (Interpretar, «capacity %.2f kN»; `data_tips`; la tabla fuerza-distancia de Define Support, «Force (kN)») | kN | Bien: es la fuerza **de un elemento** (un bulón, un anclaje), no por metro |
| Cargas lineales, diagrama de fuerzas de la dovela (`interpret_window`, «Sum of the forces: … kN/m») | kN/m | Bien |
| Línea de órdenes | Solo «γ (kN/m³)» | Bien |

Las unidades que ya eran correctas se quedan: kN/m³ de los pesos específicos, kPa de las tensiones,
kN·m de los momentos. La referencia titula «Weight [kN]» en su tabla de dovelas (lo cita el comentario
de `tests/test_slide_validation_ej2_piezo_v194.py:111`, que no se toca). Aquí manda el contrato del
programa.

## 1. Qué cambia

- `ogr_gui/interpret_window.py`: las nueve filas de fuerza, de «(kN)» a «(kN/m)».
- `ogr_gui/i18n/__init__.py`: sus nueve claves, cambiadas a la vez (regla 2): «Peso W (kN/m)», «Fuerza
  normal en la base N (kN/m)», «Cortante motor W·senα (kN/m)», «E izquierda (kN/m)»…
- `ogr_mcp/guide.py`: la línea de unidades de la guía del agente.

## 2. Tests

- `tests/test_force_units_d455_v1514.py` (nuevo, 4 tests, sin ventana): ninguna fila del panel escribe
  «(kN)»; las nueve fuerzas llevan «(kN/m)», en inglés y en castellano; kN/m³ y kPa se quedan.
- **Textos fijados que cambian a propósito**, solo el rótulo: `tests/test_interpret_slice_data_v187.py`
  (8), `tests/test_sarma_interpret_v1467.py` (9) y `tests/test_slice_panel_buttons_v191.py` (4).
  `tests/test_report_spanish_v1355.py` sigue con `'Weight\n[kN]'` hasta la fijación nueva.
- Áreas `force_units`, `interpret_slice_data`, `sarma_interpret`, `slice_panel_buttons`, `i18n`,
  `report_spanish` y `mcp`, con `--jobs 4`: 96 casos en verde.

## 3. Suite

La suite entera se corre al final de la tanda.

## 4. Lo que queda: la petición a OGR Core

En la ventana de OGR-Core, para una versión nueva (v0.2.15):

> **D455 de Slip2D.** En `ogr_core/report/report_generator.py`, `_slice_table`, la cabecera
> `T("Weight") + "\n[kN]"` (línea 937 en v0.2.14) pasa a `"\n[kN/m]"`. Es la unidad del contrato de
> `LEMResult` y la que ya escribe `_face_table` justo debajo. Ningún número cambia. Antes de etiquetar,
> la suite de Slip2D con `--dev-core`, en la que cae a propósito `tests/test_report_spanish_v1355.py`
> (su texto fijado `'Weight\n[kN]'`).

Cuando esté etiquetada, en Slip2D y en un commit propio: subir la fijación, cambiar el texto fijado de
`test_report_spanish_v1355.py` a `'Weight\n[kN/m]'` (declarado), y añadir la tabla de dovelas del
informe a `tests/test_force_units_d455_v1514.py`.
