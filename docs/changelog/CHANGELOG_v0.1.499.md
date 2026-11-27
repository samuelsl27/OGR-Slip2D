# OGR Slip2D v0.1.499

**D437: con Newmark y «Permitir desplazamiento talud arriba», la crítica publicada es la que más
se mueve.** Hasta esta versión era la de menor Ky, que es lo que minimiza la búsqueda. Sin talud
arriba son la misma superficie (Newmark 1965), pero con talud arriba el desplazamiento es neto y
una superficie de Ky mayor puede moverse más. La búsqueda no cambia: sigue guiándose por el Ky, y
la población es la misma.

## 0. Lo que se encontró

- **La medida de la ficha, repetida con 0.1.498** (`_auditoria/P10_D437/medir_d437.py`): el
  talud de ejemplo con c = 12 kPa, rejilla 5×5×6, Bishop, la sinusoide de 0,3 g y 2 Hz durante
  4 s más 2 s de calma, polaridad máxima. Sale igual cifra a cifra que con 0.1.485 y 0.1.449:
  - sin talud arriba, la crítica (Ky 0,1137) se mueve 31,083 cm y ninguna se mueve más;
  - con talud arriba, la crítica (Ky 0,1137) se mueve 0,236 cm, 4 de 152 se mueven más, y la
    que más se mueve llega a 1,269 cm, con Ky 0,1543.
- **Lo que la ficha no había medido:** si la de mayor desplazamiento neto puede no estar en la
  población guardada de una búsqueda que no es de rejilla. Sigue sin medirse. La regla elige
  entre lo que la corrida analizó, que es lo único que tiene desplazamiento.
- **Una rejilla menor no conserva la separación.** De 2×2×2 a 4×4×3, la que más se mueve es
  siempre la de menor Ky. 5×5×4 sí la conserva (0,050 cm frente a 1,081 cm), y es la del test.
- **Lo que la regla nueva deja falso fuera de este repositorio.** El informe PDF (OGR-Core,
  `ogr_core/report/report_generator.py`, `_seismic_rows`) escribe en el bloque «Global Minimums»
  la fila «Critical surface: the one with the lowest Ky of this method». Con talud arriba, desde
  esta versión, esa fila es falsa. No se toca aquí, porque es código del núcleo: hace falta una
  versión de OGR-Core en la que la fila lea `SearchResult.net_newmark` y diga «la de mayor
  desplazamiento neto». **Queda pendiente para la propietaria.** El docstring de
  `SeismicAnalysisSettings` (OGR-Core, `ogr_core/project/settings.py`) repite la premisa sin la
  salvedad del talud arriba.

## 1. Qué cambia

Opción **(a)**, decisión de la propietaria del 2026-11-27.

- `ogr_slip2d/search.py`:
  - `newmark_net_key`: válida antes que inválida, admisible antes que inadmisible, después el
    mayor desplazamiento neto, y entre dos que se mueven igual, el menor Ky. Una superficie sin
    desplazamiento queda detrás de todas las que lo tienen;
  - `SearchResult.net_newmark` (False por defecto), y `SearchResult.rank_key`, que eligen
    `critical` y `top_n`. Así sigue valiendo `top_n(1)[0] is critical` (D361), y
    `results_query(rank=1)` da la crítica;
  - `objective` sigue siendo "ky", porque es lo que la búsqueda minimizó, y lo comparan
    `reported_caption`, `results_io`, la estadística, Interpretar y la CLI;
  - se corrige el comentario del objetivo: la premisa solo vale sin talud arriba.
- `ogr_slip2d/analysis_runner.py`:
  - `_seismic_lines` pone `net_newmark` cuando Newmark tiene talud arriba y alguna superficie
    recibió desplazamiento. Sin un registro utilizable se queda la de menor Ky, que es lo que
    informa entonces;
  - en `run_analysis`, las líneas sísmicas se calculan justo después de la búsqueda, antes de las
    notas que leen la crítica (perfil, m-alpha, soportes…). Así esas notas hablan de la superficie
    publicada. Se añaden donde siempre, así que el orden de los avisos no cambia.
- `ogr_slip2d/interpretation.py`: el docstring de `critical_per_centre`. La figura del informe ya
  elegía por centro el mayor desplazamiento (D423), y ahora la estrella de la crítica cae también
  en el mayor.
- `ogr_gui/dialogs/project_settings_dialog.py`: la nota de la página Seismic dice que, con
  Newmark y talud arriba, la crítica es la de mayor desplazamiento neto. Con su castellano.
- Los pickles que trae un trabajo del agente llevan el campo. Uno viejo, sin él, lee el valor por
  defecto de la clase.

## 2. Tests

- `tests/test_newmark_upslope_critical_v1499.py` (nuevo, 8 tests, rejilla 5×5×4, unos 1,4 s):
  - la premisa: con talud arriba, alguna de Ky mayor se mueve más que la de menor Ky;
  - la identidad: la crítica es el máximo de `details["newmark_displacement"]` entre las
    válidas, y es `top_n(1)[0]`;
  - regla 7: `allow_upslope` cambia la crítica;
  - sin talud arriba, la crítica es la de menor Ky por la clave de siempre, y es también la que
    más se mueve (Newmark 1965);
  - sin registro, la de menor Ky;
  - el campo sobrevive al pickle.

  Contra 0.1.498 fallan 5 de 8.
- Áreas `newmark`, `report_seismic`, `report_figures_seismic`, `results_query`, `seismic`,
  `surface_evaluate`, `method_notes`, `i18n`, `translation`, `critical`, `project_settings`,
  `cli_wiring`, `mcp_server`, `search_algorithms` y `grid_search`: 365 en verde.
- Banco: `d437()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST** (31,083 cm sin
  talud arriba, 1,269 cm con él).
