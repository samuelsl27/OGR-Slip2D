# OGR Slip2D v0.1.494

**D432: con abatimiento rápido, el retroanálisis lee los soportes en el nivel abatido, que es el de
las dovelas que publica el resultado.** Hasta esta versión, la corrida (`run_back_analysis`) y la
ventana de Interpretar (`required_force_of_result`) los leían sobre el proyecto con el nivel
inicial. Un soporte cuya capacidad sale del suelo lee la tensión vertical efectiva, y con ella el
agua, así que daba otra fuerza. Cambia la fuerza del retroanálisis de un modelo con abatimiento y
un soporte así. Ningún factor de seguridad cambia.

## 0. Lo que se encontró

- **Medido con 0.1.493**, sobre el terraplén de Pilarcitos de `tests/test_rapid_drawdown_v168.py`
  (nivel 72 → 37), su círculo fijo (100, 200, R 160), 25 dovelas, y un geosintético en modo
  coeficiente (0,8, resistencia a tracción 1e8) a la cota 50, entre los dos niveles. Es la
  identidad de D210 sin recortar, sobre el peso, calculada en el factor propio:

  | procedimiento | Janbu, como se dibujó / abatido | Bishop, como se dibujó / abatido |
  |---|---|---|
  | Duncan-Wright-Wong | +0,1731 / 0 | +0,1731 / 0 |
  | Lowe-Karafiath | +0,1731 / 0 | +0,1731 / 0 |
  | Corps 2 | +0,1731 / 0 | +0,1731 / −1e-16 |
  | B-bar (B̄ = 1) | +0,2097 / −1e-14 | +0,2105 / −1e-14 |

  Los cuatro procedimientos publican dovelas de su etapa abatida: la segunda de Lowe-Karafiath,
  la última pasada con el tope drenado de DWW y de Corps 2, y la única pasada de B-bar. Las cuatro
  usan el mismo modelo, `level_project(…, use_drawdown=True)`. La etapa 3 no cambia de modelo.
- **B-bar con el círculo de la ficha.** Con B̄ = 0 da `non_physical_fos`. Con B̄ = 1, el mismo
  círculo es válido y basta para medirlo.
- **El fragmento de la ficha resolvía a 1e-3, no a 1e-12.** `M()` sin argumentos toma la
  tolerancia por defecto del método. La tolerancia del proyecto no llega a un método construido a
  mano. Con DWW la identidad daba 1e-16 de todos modos. Con B-bar daba −5e-5 incluso sin soporte,
  y parecía otro defecto. Con `M(tolerance=1e-12, max_iterations=400)`, todo da 0 a 1e-14.
- **Las dos puertas reales, medidas.**
  - En la corrida entera (`run_configured_back_analysis` sobre una rejilla de 9 centros), las 18
    llamadas a `required_force` recibían un modelo con el nivel freático a y = 72.
  - La ventana pasaba `prepare_analysis_project(self.project)`, que es el mismo modelo sin abatir.
- **Qué soportes leen el suelo.** Todo tipo con perfil de adherencia (`NEEDS_BOND_PROFILE`): el
  geosintético, el anclaje inyectado por fricción, el anclaje helicoidal y el pilote o micropilote
  cuando lo pide. El arreglo no depende del tipo: les da a todos el modelo de las dovelas. Solo se
  ha medido el geosintético.
- **El control.** Sin el soporte, o con el geosintético limitado por su tracción (5000, que no lee
  el agua), los dos modelos dan 0.

## 1. Qué cambia

- `ogr_slip2d/back_analysis.py`: función nueva `model_of_slices(project)`. Si el proyecto pide
  abatimiento rápido, devuelve `level_project(project, use_drawdown=True)`; si no, el mismo
  proyecto. Una regla en un sitio, del motor (opción (a), decisión de la propietaria del
  2026-11-27):
  - `run_back_analysis` la llama una vez, antes del bucle;
  - `required_force_of_result` la llama con el modelo que recibe.

  Interpretar no cambia: sigue pasando la copia factorizada, y la regla la aplica el motor. El
  terreno que leen las cribas de D418 es el mismo con los dos modelos, porque solo se mueve el
  agua.
- Docstring de `required_force_of_result`, con la regla.

## 2. Tests

- `tests/test_back_analysis_drawdown_v1494.py` (nuevo, 5 tests). La referencia es la identidad
  de D210. Comprueba:
  - `model_of_slices` da el nivel abatido, no toca el proyecto y sin abatimiento devuelve el mismo
    objeto;
  - por la función de la ventana, el círculo fijo con los cuatro procedimientos y los dos métodos,
    a ≤ 1e-9 del peso;
  - el control sin soporte y con el soporte limitado por tracción;
  - por la corrida entera, los círculos de una rejilla que cruzan el geosintético, cada uno en su
    factor propio. Como se dibujó, quedan entre 0,03 y 0,06 del peso;
  - por la ventana de Interpretar, espiando `required_force` como `_ask` de
    `test_interpret_back_analysis_v1440`.

  Contra el árbol de 0.1.493 fallan los cinco: los tres de las puertas por +0,173 W o +0,03…0,06
  W, y los dos de `model_of_slices` porque no existe.
- `back_analysis rapid_drawdown drawdown`: 296 de 296 en verde, con
  `tests/test_interpret_back_analysis_v1440.py` y los `test_back_analysis_*` sin tocar.
- Banco: `d432()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST** (con el árbol de
  0.1.493, SIGUE ABIERTO con +0,1731). `d418()` de la raíz y `d210()` del 02 (`--seco`) siguen
  CUBIERTO POR TEST.

## 3. Lo que no se ha probado

- Los demás tipos de soporte que leen el suelo, uno a uno. El arreglo no distingue tipos.
- La ventana a mano. La suite entera va al final de la tanda.
