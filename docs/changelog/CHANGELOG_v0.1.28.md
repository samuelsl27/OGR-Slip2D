# OGR Suite v0.1.28 — Changelog

**Lanzamiento:** 26 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 4 del plan de agua subterránea: acople flujo → estabilidad.**
> `PorePressureType.FEM_SEEPAGE` operativo, y la succión tratada con la
> envolvente de Mohr-Coulomb extendida tal como hace la referencia.

---

## 🔗 Acople: la presión intersticial sale del campo FE

`FEM_SEEPAGE` deja de ser un hook reservado. La presión en el punto medio
de la base de cada dovela se interpola del campo de filtración convergido
con las funciones de forma T3 (`Mesh.interpolate()`, exacta para campos
lineales, validada en la Fase 1). Flujo de trabajo:
**Compute Groundwater → Compute Slope**, con `project.seepage_result`
como puente.

Degradación segura: si no hay campo calculado, o si un punto cae fuera de
la malla, se devuelve presión nula en vez de extrapolar o fallar.

## 💧 Política de succión: la envolvente bilineal de la referencia

La decisión que quedaba abierta era «¿truncar u<0 por defecto?». La
respuesta obtenida de la documentación de la referencia es que **no se
trunca**: se conserva la presión negativa y su aportación se controla con
la **ecuación de Mohr-Coulomb extendida** (Fredlund et al. 1978) mediante
dos parámetros por material:

- **`phi_b`** — ángulo de resistencia al corte no saturada. **Por defecto
  0**, con lo que «la succión matricial NO tiene ningún efecto sobre la
  resistencia ni sobre el factor de seguridad».
- **`air_entry_value`** — succión por debajo de la cual el suelo sigue
  efectivamente saturado, de modo que la envolvente es **bilineal**:

| Estado | Tratamiento |
|---|---|
| u ≥ 0 | u sin cambios |
| 0 < succión ≤ AEV | u sin cambios: el **φ′ saturado** acredita la succión |
| succión > AEV | u limitada a −AEV + cohesión extra (succión−AEV)·tan φ_b |

Con `phi_b = 0` y `AEV = 0` (los defectos de la referencia) cualquier
presión negativa se anula y no aporta nada: **el truncado conservador
sale como caso particular** de la formulación general, en vez de ser un
interruptor aparte. Esta es la razón de fondo por la que se implementó
así y no con un checkbox.

La documentación de la referencia añade un dato histórico útil que
confirma la lectura: antes de su versión 5.010, φ_b se aplicaba en
cualquier punto con presión negativa, «lo que equivale a definir el valor
de entrada de aire como cero».

**Punto de inyección único**: la política se aplica en el dovelador
(`apply_unsaturated_policy`), que guarda en cada dovela la presión
efectiva, la presión cruda (`raw_pore_pressure`) y la cohesión por
succión. Ésta se suma en `_local_c_phi`, de modo que **los siete métodos
LEM la recogen sin tocar ninguno**.

## ✔️ Validación

Círculo de referencia con un campo de filtración convergido
(u entre −165 y +392 kPa, es decir con zona no saturada real):

| Caso | FoS |
|---|---|
| Modelo seco (sin agua) | 0.8831 |
| Con filtración, phi_b=0 AEV=0 (defecto) | **0.8455** |
| phi_b=10° | 0.9836 |
| phi_b=20° | 1.1350 |
| phi_b=20°, AEV=50 kPa | 1.1840 |

Con los defectos el FoS **baja** respecto al modelo seco (las presiones
positivas reducen la resistencia y la succión no aporta), y crece de
forma monótona al activar φ_b. Todo el comportamiento esperado.

## 📊 Tests

**521 tests, 521 verdes** (+17 desde v0.1.27; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_coupling_v128.py`): política de succión
(presión positiva intacta, defectos que anulan la succión, tramo por
debajo del AEV que conserva u real, tramo por encima que limita u y añade
cohesión, escalado lineal de la cohesión, φ_b=0 con AEV≠0, material
nulo, serialización, defectos a cero); acople (el campo tiene succión, el
FoS baja respecto al seco, φ_b lo sube monótonamente, las dovelas llevan
presión cruda y efectiva y la cohesión por succión, degradación segura
sin campo o fuera de la malla, y los **seis métodos LEM** aceptando el
proyecto acoplado).

## ⏳ Siguiente

**Fase 5 — GUI modo Groundwater e Interpret de flujo**, con la
especificación ya escrita en `docs/INTERFAZ_AGUA_SUBTERRANEA.md`. Nota
para esa fase: el diálogo de propiedades de material necesita ahora los
campos *Unsaturated Shear Strength Angle* y *Air Entry Value*, que la
referencia **solo muestra cuando el método de agua es FEA**.

Pendiente previo: decisión sobre `reject_tensile` por defecto en
búsquedas no circulares (anomalía A3).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
