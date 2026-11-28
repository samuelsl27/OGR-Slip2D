# OGR Slip2D v0.1.510

**D446: el informe PDF escribe con sus decimales una coordenada entera, y una cuenta sin ellos.** El
arreglo es de OGR Core 0.2.14: `_fmt` trata como real todo número que no sea `bool`, la decisión B de
la propietaria del 2026-11-27. Slip2D lo fija desde 0.1.505. Esta versión solo trae tests, sin
código del programa.

## 0. Lo que se encontró

- **El defecto, medido con 0.1.457.** El talud de ejemplo tiene los vértices enteros, y la «List of
  Coordinates» imprimía «0» donde una coordenada real imprime «0.000». Con un vértice editado a
  (35,5; 15), la misma fila mezclaba «35.500» y «15».
- **El censo del núcleo** (su changelog de 0.2.14): 52 llamadas a `_fmt`, todas de coordenadas o
  magnitudes. Las cuentas ya se escribían con `str()` en su sitio, así que no había ninguna que mover.
- **La suite de Slip2D contra ese núcleo** no tenía fijado ningún texto del informe con un entero sin
  decimales. No hay ningún cambio que declarar.
- **A/B en el mismo proceso**, con el `_fmt` de 0.2.12 reconstruido por la ficha: la «List of
  Coordinates» del talud de ejemplo sale «0», «0», «50», «0», y con el de 0.2.14 sale «0.000»,
  «0.000», «50.000», «0.000».

## 1. Qué cambia

Nada en el código del programa.

## 2. Tests

- `tests/test_report_integer_cells_d446_v1510.py` (nuevo, 3 tests; una corrida pequeña, Bishop con
  una rejilla de 3×3, y dos informes). Recorre el informe entero que genera Slip2D, leyendo las celdas
  de cada tabla:
  - la premisa (los vértices del talud de ejemplo son enteros) y todas las celdas de la «List of
    Coordinates» con tres decimales;
  - el vértice editado a (35,5; 15) sale «35.500» y «15.000»;
  - el número de dovela de «Slice Data» sigue siendo una cuenta: «1», «2», «3».

  Con el `_fmt` de 0.2.12 caería el primero, como muestra el A/B de arriba. La ficha cuenta que ese
  fue el mismo caso que falló en el segundo.
- Área `report`, con `--jobs 4`: en verde.

## 3. Suite

La suite entera se corre al final de la tanda.
