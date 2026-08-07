# OGR Slip2D v0.1.22 — Changelog

**Lanzamiento:** 7 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> Release que añade el **post-procesador de fuerzas interdovela**, el
> **diagrama de cuerpo libre método-consistente** y la **línea de
> empuje (line of thrust)** en el visor Interpret.

---

## 🆕 Motor: post-procesador de fuerzas interdovela (`ogr_slip2d/postprocess.py`)

Nuevo módulo `compute_interslice_state(result)` que, a partir de un
`LEMResult` convergido, marcha las ecuaciones de equilibrio dovela a
dovela (izquierda → derecha) al FoS del método y recupera:

- **E, X** — fuerzas interdovela horizontales/verticales en las n+1
  fronteras (condición E=X=0 en los extremos libres)
- **N, S** — normal total y cortante movilizado en la base, consistentes
  con la marcha (no estáticas de dovela aislada)
- **y_thrust** — la **línea de empuje**: altura de aplicación de la
  resultante interdovela en cada frontera, por balance de momentos
  respecto al punto medio de la base (Fredlund & Krahn, 1977)
- **closure** — el residuo |E_n| al cierre, reportado y no ocultado

**Ratios por método.** Cada método guarda ahora sus ratios X/E por
frontera en el nuevo campo `LEMResult.details["boundary_ratios"]`:
Spencer (λ constante), GLE (λ·f(x)), Lowe-Karafiath (tan θᵢ). Bishop,
Janbu y Ordinary asumen X=0 (ratios cero por defecto).

**Robustez de signo y refinamiento.** Como Spencer/GLE resuelven λ en
el marco invertido por `slide_sign`, el post-procesador prueba ambos
signos de los ratios y se queda con el de menor cierre. Además, a FoS
fijo, refina un multiplicador escalar k de los ratios por secante para
que la marcha cierre exactamente en esta discretización (el FoS nunca
se altera; es consistencia de visualización).

**Validación** (círculo de referencia, 25 dovelas):

| Método | cierre \|E_n\|/max\|E\| |
|---|---|
| Spencer | 0.00 % |
| GLE / Morgenstern-Price | 0.00 % |
| Lowe-Karafiath | 0.00 % |
| Janbu Simplified | 0.16 % |
| Bishop Simplified | 26.5 % (esperado: no satisface equilibrio horizontal; se reporta) |

El equilibrio por dovela (ΣFx, ΣFy) se verifica **exacto** (residuo
< 1e-6·W) para todas las dovelas.

---

## 👁️ Visor Interpret

### Diagrama de cuerpo libre ampliado (Query → Free Body Diagram)

Reescrito para usar el post-procesador en lugar de estáticas
aproximadas. Ahora dibuja, a **escala común** y con valores:

- **W** en el centroide real del cuadrilátero de la dovela
- **N** y **S** (cortante movilizado al FoS, con su signo) en la base
- **U = u·l** — resultante de presión intersticial en la base
- **Z_L, Z_R** — resultantes interdovela en cada cara, aplicadas a la
  altura de la línea de empuje, con el tramo de thrust line dibujado
- El título indica método, FoS y, si procede, el % de cierre (para
  métodos de solo momentos)

### Línea de empuje (Query → Line of Thrust)

Nueva acción checkable que superpone en el canvas la línea de empuje
del mínimo global (o de la superficie seleccionada) como polilínea
discontinua violeta. Se recalcula automáticamente al cambiar de método
y omite los extremos libres donde E≈0 (punto de aplicación indefinido).

---

## 📊 Tests

**389 tests, 389 verdes** (+9 desde v0.1.21, suite se mantiene 100%).

Cobertura nueva (`tests/test_postprocess_v122.py`):
- Cierre < 1 % para Spencer, GLE y Lowe-Karafiath
- Estado válido y cierre finito reportado para Bishop
- **Equilibrio por dovela exacto** (ΣFx, ΣFy < 1e-6·W en cada dovela)
- Condiciones de contorno de extremo libre (E₀ = X₀ = 0)
- Thrust line dentro de la altura de dovela en > 80 % de fronteras
- `details["boundary_ratios"]` presente y de longitud n+1 en los
  métodos rigurosos; X ≡ 0 para Bishop

---

## 📄 Documentos incluidos

- `docs/AUDITORIA_v0.1.22.md` — auditoría completa del código: qué hay,
  qué falta respecto a la referencia, y **anomalías detectadas**
  (reportadas sin corregir, pendientes de decisión)
- `docs/PLAN_AGUA_SUBTERRANEA.md` — plan por fases del módulo
  OGR FEM2D de flujo (ingeniería inversa de la referencia + literatura)

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
