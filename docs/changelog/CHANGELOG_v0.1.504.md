# OGR Slip2D v0.1.504

**D442, segunda mitad: el agente sabe cuándo la superficie probabilística crítica la definió el
usuario**, como lo dice la barra de Interpretar desde 0.1.503. Decisión de la propietaria del
2026-11-27, al cerrar 0.1.503, que lo había dejado fuera a propósito. Ningún número cambia.

## 0. Lo que se encontró

- **Por dónde lo ve el agente.** `statistics_run` entrega `statistics_summary`
  (`ogr_api/results.py`), que toma de cada método el `summary()` del resultado probabilístico
  (`OverallSlopeResult.summary`, en `ogr_slip2d/probabilistic.py`). Es el único camino: el
  trabajador del subproceso lo llama igual. Basta con una clave en `summary()` para que la vean
  el agente y cualquier otro lector del resumen.
- **Medido antes de tocar nada**, con el caso de D442 (el talud de ejemplo, Path Search de 5,
  Janbu, la polilínea del usuario y la cohesión Normal, 20 muestras LHS, Overall Slope). Con
  0.1.503, el resumen daba el PF del 10 % de la polilínea y no había ninguna clave que dijera de
  quién era. Una superficie de la búsqueda con ese PF se habría leído igual.

## 1. Qué cambia

- `OverallSlopeResult.summary()` añade `critical_probabilistic_user_defined`:
  - `True` cuando la superficie crítica la definió el usuario;
  - `False` cuando es de la búsqueda;
  - `None` cuando no hay superficie, con la misma política que su PF (D127), porque entonces no
    es de nadie.

  Lo pone la corrida (`SurfaceProbability.user_defined`, de 0.1.503).

## 2. Tests

- `tests/test_statistics_summary_user_defined_v1504.py` (nuevo, 3 tests, sin Qt; las dos corridas
  estadísticas se calculan una vez por archivo):
  - la polilínea del usuario sale como del usuario, con PF 10 %;
  - una superficie de la búsqueda sale con `False`;
  - sin superficie, `None`.

  Contra 0.1.503 fallan los 3 (`KeyError`).
- Áreas `overall_slope`, `probabilistic`, `statistics`, `results`, `mcp`, `surface_key`,
  `interpret_crit` y `version_consistency`, con `--jobs 4`: 316 en verde con este changelog (el
  único fallo antes de escribirlo era el que lo pide).

## 3. Numeración de la tanda

Esta versión ocupa el 0.1.504 que el plan reservaba a D443. Las fichas del núcleo pasan a 0.1.505
(D443), 0.1.506 (D444), 0.1.507 (D445), 0.1.508 (D446) y 0.1.509 (D449).

## 4. Suite

La suite entera se corre al final de la tanda.
