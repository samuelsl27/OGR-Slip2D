# OGR Slip2D v0.1.263

**Una corrida estadística llamada directamente rebana como el proyecto, igual
que el análisis (D248). Y el retroanálisis pierde un `num_slices` que nunca
leyó.** Ningún número del banco ni de la suite cambia: nadie dependía del 25
en un proyecto que no tuviera 25 dovelas.

## 0. Lo que se encontró

### D248: 25 dovelas por defecto, dijera lo que dijera el proyecto

- **El defecto.** `run_global_minimum` (`ogr_core/statistics/probabilistic.py`)
  y `run_sensitivity` (`sensitivity.py`) tenían `num_slices: int = 25`.
  - La puerta del análisis, `analysis_runner.run_configured_statistics`, pasa
    las dovelas del proyecto. Es la que usan la ventana, la API y el MCP.
  - La llamada directa, desde un script, un test o `python_exec`, evaluaba
    cada muestra con 25, al lado de un determinista que había usado las del
    proyecto, y nada lo decía.
- **Es la misma clase que D92 y D93:** la llamada directa no hace lo que
  hace el análisis.
- **El 25 llegaba a dos sitios:** al evaluador (`build_evaluator`) y a
  `build_method`, y por este a la envoltura del desembalse rápido
  (`wrap_for_drawdown`). El test lo enseña con un espía, que en 0.1.262 ve
  `[51, 25]`: el determinista con las 51 del proyecto y las muestras con 25.
- **Quién dependía del 25.** La exploración leyó todos los llamadores:
  - los de producción y los del banco pasan las dovelas del proyecto o un
    número explícito;
  - los cuatro tests que se apoyaban en el valor por defecto corren sobre
    proyectos de 25 dovelas.

  Así que el cambio no mueve ningún número, y se comprobó con la suite.

### Un ajuste muerto de la misma clase, sin número

`ogr_slip2d/back_analysis.py::run_back_analysis(…, num_slices=25, …)` no
leía su `num_slices`: el rebanado lo pone la búsqueda que recibe. Nadie lo
pasaba, ni la puerta, ni los tests, ni el banco. Es un ajuste que no hace
nada (regla 7).

## 1. Lo que cambia

- **`run_global_minimum` y `run_sensitivity`:** `num_slices: Optional[int] =
  None`. Con None se toman las dovelas del proyecto tal como lo prepara el
  análisis, que es lo que `build_method` y `build_evaluator` ya hacían con
  None. Un número explícito sigue mandando.
- **`run_back_analysis`:** se quita el parámetro. Quien todavía lo pase
  recibe un `TypeError` que dice la verdad, en vez de un número que lo
  ignora.

## 2. Tests

**`tests/test_statistics_project_slices_v1263.py`, 6 casos**, sobre un
proyecto de **51 dovelas**: ni 25 ni un múltiplo suyo, porque las cuentas
anidadas comparten dovelas. En ese círculo, 51 y 25 dovelas difieren en
7,7e-4.
- **Cada muestra es su propio recálculo:** sus valores aplicados a una copia
  del proyecto y el círculo determinista evaluado ahí con las dovelas del
  proyecto. Coinciden a 1e-12.
- **El punto medio del barrido de sensibilidad**, la variable en su media,
  es el factor determinista a 1e-12.
- **La envoltura del desembalse** recibe 51.
- **El control:** con `num_slices=25` explícito, las muestras no son el
  recálculo.
- **`run_back_analysis`** rechaza `num_slices`.

**Discriminación** contra un `git archive` de 0.1.262 (d6f3b03): fallan 4 de
6. Pasan el control y la premisa.
