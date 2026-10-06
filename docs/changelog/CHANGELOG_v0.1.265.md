# OGR Slip2D v0.1.265

**La CI de 0.1.264 se puso en rojo en las tres Pythons por el test nuevo de
D250.** Su tolerancia de ±1 % venía de medir en una sola máquina, y Surface
Altering no da el mismo número con otra versión de SciPy. Pasa a ±2 %, con
la medida que lo justifica. El motor no cambia.

## 0. Lo que se encontró

- **El fallo.** `test_reaches_the_published_factor`, de
  `tests/test_auto_refine_noncircular_family_v1264.py`, fue el único fallo
  de la CI. Los otros 5702 casos pasaron, igual que el caso de la forma.

  | plataforma | Python | SciPy / NumPy | Bishop | frente a 1,268 |
  |---|---|---|---|---|
  | Windows (local) | 3.14.7 | 1.18.0 / 2.5.1 | 1,26915 | +0,09 % |
  | Linux (CI) | 3.11 y 3.13 | 1.17.1 / 2.4.6 | 1,28572 | +1,40 % |
  | Linux (CI) | 3.12 | 1.17.1 / 2.4.6 | 1,28658 | +1,47 % |

- **La causa probable.** Surface Altering minimiza con COBYQA de SciPy
  (`ogr_slip2d/surface_altering.py`, `minimize(method="COBYQA")`). Es
  determinista en una máquina, pero no entre versiones de la biblioteca:
  el optimizador recorre otro camino y acaba en otro mínimo local de la
  misma familia. Es una hipótesis: no se ha reproducido aquí la versión de
  SciPy de la CI.
- **Por qué no se vio.** El ±1 % de 0.1.264 se justificó con la dispersión
  entre partidas (−0,56 a +0,82 % en cinco), toda medida en una sola máquina.
  La dispersión entre plataformas no se midió. Es la misma lección que la CI
  roja de 0.1.209: lo que sale de una cadena de doubles hereda la aritmética
  de la plataforma.

## 1. Lo que cambia

- **El test** pasa a |F/1,268 − 1| ≤ 2 %, y la cabecera escribe las dos
  dispersiones y de dónde sale cada una. Con 2 % sigue fuera el Monte Carlo
  (+4,9 %), así que el test sigue fallando donde no hay Surface Altering.
  Decisión de la propietaria.
- **El banco:** `d250()` del `verificar_cierres.py` de la raíz usa la misma
  tolerancia (`_D250_TOL = 0.02`), con la misma razón. El documento
  `P5_0264/D250_mecanismo.md` lo cuenta.
- **El motor no cambia.** Ningún interruptor nuevo.
