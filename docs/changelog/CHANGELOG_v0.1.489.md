# OGR Slip2D v0.1.489

**El núcleo fijado sube de `ogr-core` 0.2.7 a 0.2.10, y la fila de Sarma del informe deja de decir
«least».** `pyproject.toml` fija ahora `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.10`.
Es una etiqueta anotada, `160f724` → `e982ab5`, comprobada en GitHub con `git ls-remote`. El
`.venv` tiene esa etiqueta instalada con `--no-deps --force-reinstall`. Cierra lo que D454
(v0.1.488) dejó pendiente del núcleo: OGR-Core renombró en su 0.2.10 la fila «Least Number of
Wedges» de `_sarma_settings_rows` a «Number of Wedges Asked For». También corrigió las viñetas
`num_slices` y `slice_angles` del docstring de `SarmaSettings`, que seguían con la regla de la
0.1.464.

`git diff --stat v0.2.7 v0.2.10 -- ogr_core` toca 13 archivos:

| Versión | Qué es | Para Slip2D |
|---|---|---|
| 0.2.8 | `dxf/reader.py`: las entidades `ARC`, `CIRCLE`, `LWPOLYLINE` y `POLYLINE` 2-D se leen en sus coordenadas (OCS); una inclinada va a `skipped` | **Aviso de salida**: §0 |
| 0.2.9 | `ogr_core/api/` (nuevo, ~2400 líneas): el armazón de la capa de operaciones | Nada: `ogr_api` no lo usa. Adoptarlo es decisión abierta (§2) |
| 0.2.10 | `report/report_generator.py` (la fila) y `project/settings.py` (el docstring) | La fila y su traducción (§1) |

## 0. Lo que se encontró

- **El aviso de la 0.2.8 no afecta a ningún DXF de Slip2D.** La importación da otra geometría, la
  correcta, en un dibujo con alguna `ARC`, `CIRCLE`, `LWPOLYLINE` o `POLYLINE` 2-D cuya extrusión no
  sea +Z. El censo de la 0.1.486 ya dejó dicho que no hay ningún `.dxf` en el repositorio, en
  `referencias` (banco incluido) ni en `historico`. El único que hay en `C:\Desarrollo` es
  `proyectos-mcp/prueba_gui_0355/H_export.dxf`, exportado por el programa. Contado ahora con
  `ezdxf`: 4 `LWPOLYLINE` y 2 `TEXT`, y cero entidades con extrusión distinta de +Z. Los tests
  dibujan sus DXF sin extrusión.
- **El paso intermedio, `b02a2d5`, ya probaba las dos filas.** Con un núcleo publicado, la suite
  exigía la fila de su versión, y con uno `.devN`, cualquiera de las dos, pero exactamente una.
  OGR-Core corrió contra su 0.2.10 esa suite entera: 7584 casos, 7582 pasan, 2 saltados, sin fallos
  ni fugas. Con la fijación en la 0.2.10, la rama por versión ya no tiene sentido y se quita: un
  núcleo que vuelva a decir «Least» es un fallo, también con `--dev-core`.
- **`d454()` del banco** (`_tools/verificar_cierres.py`, fuera de git) ya no dice «pendiente del
  núcleo». Ahora exige que la primera fila de `_sarma_settings_rows` sea
  `("Number of Wedges Asked For", 25)` y que la clave vieja no esté en `ogr_gui/i18n`. Con el
  núcleo 0.2.10 da CUBIERTO POR TEST: el 4 saturado, con 25 pedidas, da 19 cuñas y F 0,434662, y el
  círculo conserva sus 25 (F 3,3825). La copia de `Evaluaciones/0.1.488/_tools` no se toca: es la
  instantánea de esa versión.

## 1. Qué cambia

- `pyproject.toml`: la fijación, con su comentario.
- `ogr_gui/i18n/__init__.py`: fuera `'Least Number of Wedges'`; queda
  `'Number of Wedges Asked For': 'Número de cuñas pedido'`.
- `tests/test_sarma_report_v1468.py`: `_asked_row` exige la fila nueva y que no esté la vieja.
  `_ASKED_OLD` se queda solo para eso y para el test sin Sarma, que comprueba que ninguna de las dos
  sale.
- `tests/test_sarma_wedge_count_v1488.py`: `test_the_report_row_in_spanish` traduce la clave nueva y
  comprueba que la vieja ya no está en el diccionario español.
- `AGENTS.md`: la fijación y la cabecera del runner (`shared: ogr_core 0.2.10 …`); sigue en 499
  líneas.
- La versión, en siete sitios.

## 2. Pendiente, sin tocar

- **Adoptar `ogr_core.api` (0.2.9).** Su §2 dice qué valores daría `ogr_api` para que sus frases
  inglesas sigan siendo las de hoy byte a byte (`BridgeConfig("ogr-slip2d-bridge/1", "OGR Slip2D",
  ".ogr-slip2d")`, `resolve_field(…, example="methods.num_slices", lister="settings_get")`, los
  `JobHooks` de `slice_store`). Hay dos cambios que se ven igual: `status.json` de un trabajo
  fallido lleva `error_code` y `error_args`, y `to_dict()` de un error añade `message_code` y
  `hint_code`. Es una decisión de la propietaria, con su propio plan.
- **La fila de Slip2D en `docs/consumidores.md` de OGR-Core** pasa a `v0.2.10` desde esta versión.
  Se corrige allí; hasta entonces el trabajo `pins` de la CI de OGR-Core está en rojo.

## 3. Pruebas

- `sarma_report`, `sarma_wedge_count`, `version_consistency` y `agent_scaffolding`, con el núcleo
  0.2.10 instalado: en verde (la cabecera dice `shared: ogr_core 0.2.10 … installed`).
- `d454()` del banco: CUBIERTO POR TEST, con los números de §0.
- Suite entera con `--jobs 4`: §4.

## 4. Suite entera

`QT_QPA_PLATFORM=offscreen .venv/Scripts/python tests/_runner.py --jobs 4`, sin `--dev-core`, con
`shared: ogr_core 0.2.10 … (installed, no git tree)`: **7584 casos, 7582 pasan, 0 fallan, 2
saltados** (los de la plataforma), sin fugas ni tramos muertos. La última serie en verde fue hace 18
commits (`7aff40b`).
