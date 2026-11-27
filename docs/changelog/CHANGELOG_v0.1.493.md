# OGR Slip2D v0.1.493

**D436: Optimizar dice por qué no pudo evaluar su superficie de partida, con la misma regla que la
puerta de una superficie.** Hasta esta versión, toda partida que volvía sin resultado se achacaba
al rebanador («the slicer refused it whole…»), la hubiera quitado un Área mínima, una capa débil,
un objeto de foco o el propio rebanador. Ningún número cambia.

## 0. Lo que se encontró

- **Medido con 0.1.492** (las sondas de la ficha), Bishop, por `run_configured_optimization`:

  | caso | motivo que registra la búsqueda | Optimizar decía | `evaluate_surfaces` dice |
  |---|---|---|---|
  | talud de ejemplo, crítica de la Path Search con 20 superficies (1,13577), Área mínima 1e6 | ninguno; filtro «Minimum Area 1e+06» | «the slicer refused it whole…» | «not analysed, and no reason was recorded; filters active…: Minimum Area 1e+06» |
  | junta de `test_weak_layer_v1121`, (2,2)–(16,1)–(30,10), 40 dovelas, techo a 10° | `weak_layer_steep` | «the slicer refused it whole…» | «a weak layer clips it…» |
  | talud de ejemplo, poligonal (10,25)–(28,23)–(30,21)–(35,15) | `base_above_ground` | «the slicer refused it whole…» | «between its two ends its base rises above the ground…» |

- **La regla ya existía en la otra puerta** (`_given_refusal`, 0.1.446, D403), y Optimizar no la
  preguntaba. Tampoco el foco registraba motivo: `_evaluate` devolvía None antes de llegar a la
  búsqueda, así que con un foco que quitaba la partida no había nada que leer.
- **La trampa de la copia** que avisaba la ficha (con las comprobaciones apagadas, el paseo evalúa
  con una copia superficial de la búsqueda) se evita leyendo el motivo del **evaluador**, que es
  donde se escribe, y no de la búsqueda que se pasó.
- **De paso:** el comentario de `optimize.py` que justifica la clave `error` citaba
  `main_window._optimize_current`; la acción se llama `MainWindow._optimize_surfaces`.

## 1. Qué cambia

- **Una regla, un sitio.** `_given_refusal` pasa a ser `BaseSearch.given_refusal(project)`
  (`ogr_slip2d/search.py`), sin cambiar su texto. `analysis_runner._given_refusal` queda como
  envoltorio de una línea (lo usa `tests/test_refused_surface_notes_v1446.py`).
- **Optimizar la pregunta** (`optimize._start_refusal`). Con un motivo conocido (el registrado o
  los filtros activos) dice la frase nueva `search.opt.start_refused_because`: «The optimisation
  cannot start from this surface, because {reason}», con el motivo anidado con su código. Sin
  nada que decir (sin motivo ni filtro, o una evaluación que lanzó una excepción) dice la frase de
  siempre, `OPT_START_REFUSED`.
- **El foco** (decisión de la propietaria del 2026-11-27): motivo propio,
  `REFUSED_OUTSIDE_FOCUS = "outside_focus"`, «a focus object of the search excludes it.».
- **La excepción tragada** (decisión de la propietaria): la frase de siempre. Se registra un
  motivo que el catálogo no conoce (`_RAISED`) para que no se lea como propio el motivo que dejó
  una evaluación anterior.
- La clave `error` no cambia: la ventana sigue cortando en ella.
- Castellano de las dos frases en `ogr_gui/i18n/__init__.py`.

## 2. Tests

- `tests/test_optimize_start_refusal_v1493.py` (nuevo, 5 tests). La referencia de cada caso es lo
  que dice `evaluate_surfaces` de la misma superficie: los tres casos de la tabla, la excepción
  (frase de siempre, sin leer un motivo viejo) y el foco. Un mutante que devuelve siempre
  `OPT_START_REFUSED` hace fallar 4 de los 5; el que pasa es el de la excepción, que pide
  justamente esa frase.
- `tests/test_optimize_start_v1187.py`, cambiado a propósito: la partida levantada sobre el terreno
  dice ahora el motivo del rebanador con sus palabras («its base rises above the ground
  surface»), no «refused it whole».
- `tests/test_search_notes_v1349.py`: las dos frases nuevas con su muestra, y `outside_focus` en
  la lista de motivos que registra una búsqueda.
- `d436()` en el `verificar_cierres.py` de la raíz: **CUBIERTO POR TEST**. Con el árbol de 0.1.492
  da SIGUE ABIERTO (las dos frases son la del rebanador). `d403()` sigue CUBIERTO POR TEST.

## 3. Lo que no se ha probado

- El mensaje en la ventana, a mano. El castellano se ha comprobado con `note_text` en español.
- La suite entera: va al final de la tanda.
