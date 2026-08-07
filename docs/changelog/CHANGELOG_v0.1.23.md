# OGR Slip2D v0.1.23 — Changelog

**Lanzamiento:** 14 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 0 del plan de agua subterránea: Water Pressure Grid.** Presión
> intersticial definida por malla de puntos (Total Head / Pressure Head
> / Pore Pressure), con interpolación Thin Plate Spline e IDW. Primer
> bloque del camino hacia el módulo FEM de flujo; define además la
> interfaz de consumo que reutilizará el futuro solver (Fase 4).

---

## 🆕 Motor: `ogr_core/hydraulic/water_pressure_grid.py`

- **`WaterPressureGrid`**: puntos (x, y, valor) + tipo de grid:
  - **Total Head** → u = γw·(H − y)
  - **Pressure Head** → u = γw·hp
  - **Pore Pressure** → u directo
- **Interpoladores**:
  - **Thin Plate Spline** (Franke, 1985): RBF r²·ln r + polinomio
    lineal; exacto en los datos y **reproduce campos planos exactamente**
    (comportamiento analíticamente correcto para condiciones
    hidrostáticas). Con guardas de condicionamiento (cond > 1e12 →
    fallback) y fallback automático a IDW con > 300 puntos.
  - **IDW** (Shepard, potencia 2, k vecinos): robusto para nubes grandes.
- Succión: truncado u ≥ 0 por defecto, opción `allow_suction`.
- Serialización completa en el `.ogr` (round-trip probado).

## 🔗 Integración

- `GroundwaterMethod` amplía con `GRID_TOTAL_HEAD`, `GRID_PRESSURE_HEAD`
  y `GRID_PORE_PRESSURE` (aparecen automáticamente en Project Settings).
- `pore_pressure_at`: cuando el método del proyecto es grid, este
  gobierna por defecto para todos los materiales (incluidos los NONE por
  defecto), respetando overrides explícitos CONSTANT/RU — espejo del
  comportamiento de la referencia.
- `Project.water_pressure_grid` con to_dict/from_dict.

## 👁️ GUI

- **Boundaries → Water Pressure Grid…**: diálogo con tabla editable,
  importación CSV (separadores coma/;/tab/espacio, cabeceras y
  comentarios ignorados), tipo de grid, interpolador, k vecinos y
  succión.
- **Canvas**: puntos del grid como triángulos azules con su valor.

## ✔️ Validación física

Círculo de referencia, Bishop: FoS seco 0.8831 → con grid de cabeza
total H=30 (freática horizontal y=30) **0.7952**. La presión reduce el
FoS como corresponde.

## 📊 Tests

**407 tests, 407 verdes** (+18 desde v0.1.22):
- TPS exacto en datos y **exacto en campos planos** en puntos arbitrarios
- IDW exacto en datos y acotado por los datos
- Fallback automático a IDW con nubes grandes
- Conversión de los tres tipos de grid (hidrostática analítica)
- Truncado/permiso de succión
- Round-trip de serialización (grid y proyecto, con y sin grid)
- El grid gobierna materiales por defecto y **reduce el FoS** vs seco
- Parser CSV (separadores mixtos, cabeceras, líneas malformadas)

## ⏳ Siguiente (plan de agua)

**Fase 1**: generador de malla FE triangular sobre las regiones
existentes. Decisiones abiertas: librería `triangle` vs propia; T3 solo.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
