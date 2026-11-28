# OGR Slip2D v0.1.521

**D455 cerrada: Slip2D fija OGR Core v0.2.15, cuyo informe titula el peso de la tabla de dovelas en kN/m.**
Con esto, todas las fuerzas por metro de talud que se enseñan van en una sola unidad, kN/m, la que decidió la
propietaria el 2026-11-28. El panel de Interpretar lo hace desde 0.1.514; las tablas de dovelas y de caras
del informe, desde esta versión.

## 0. Lo que se encontró

- **OGR Core v0.2.15** (etiqueta `10af28d`, commit `dcaf8a4`; la rama era `d455-peso-kn-por-metro`):
  `_slice_table` escribe `Weight\n[kN/m]`. Antes de etiquetarlo, la sesión del núcleo corrió contra
  0.2.15.dev0 la suite de Slip2D, y en ese árbol cayeron 20 tests: eran de Slip2D 0.1.519, no del núcleo,
  y 0.1.520 los arregló (D468). Contra 0.1.520 salió en verde.
- **El rótulo no mueve ningún número.**

## 1. Qué cambia

- `pyproject.toml`: `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.15`. El `.venv` se reinstaló
  desde la etiqueta, con `--no-deps --force-reinstall`, y el ejecutor de tests nombra `ogr_core 0.2.15`.
- `AGENTS.md`: la fijación y la línea `shared: ogr_core 0.2.15` del ejecutor de tests.
- La fila de OGR Slip2D en `docs/consumidores.md` de OGR-Core se corrige allí (v0.2.15 desde 0.1.521). Hay
  que pedírselo a la sesión del núcleo.

## 2. Tests

- `tests/test_report_spanish_v1355.py`: la cabecera del peso queda fija en `'Weight\n[kN/m]'`. La condición
  por la versión del núcleo de 0.1.518 ya no hace falta.
- `tests/test_force_units_d455_v1514.py`: un test más. La tabla de dovelas del informe (`_slice_table` de un
  círculo del talud de ejemplo) titula el peso en `[kN/m]` y no le queda ninguna cabecera en `[kN]`.

## 3. Suite

La suite entera con `--jobs 4` y el núcleo 0.2.15, tras el commit.
