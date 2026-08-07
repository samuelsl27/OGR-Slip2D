# OGR Slip2D / OGR FEM2D v0.1.26 — Changelog

**Lanzamiento:** 26 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 2 del plan de agua subterránea: solver de filtración en régimen
> permanente saturado.** Elementos finitos Galerkin sobre la malla T3 de
> la Fase 1, con permeabilidad anisótropa por material y las condiciones
> de contorno de la referencia. Validado contra **soluciones analíticas
> cerradas**, no contra capturas de regresión.

---

## 🆕 Propiedades hidráulicas (`ogr_core/hydraulic/hydraulic_properties.py`)

Réplica de la especificación "Define Hydraulic Properties" de la
referencia:

- **`ks`** — permeabilidad saturada, siempre requerida; es la
  permeabilidad **primaria K1**.
- **`k2_k1`** — factor de anisotropía: permeabilidad relativa en la
  dirección ortogonal a K1.
- **`k1_angle_deg`** — dirección de K1 medida desde el eje **+X**
  horizontal, tal como especifica la referencia.
- **`unsaturated_model`** — enum con `SATURATED`, `SIMPLE`,
  `VAN_GENUCHTEN`, `FREDLUND_XING`, `USER_DEFINED`. La Fase 2 solo honra
  `SATURATED`; los demás se declaran ya para que el formato de archivo
  sea compatible hacia delante con la Fase 3, junto con sus parámetros
  (α, n, contenidos de agua saturado/residual).

**Tensor de conductividad** por rotación estándar
`K = R(θ)·diag(K1,K2)·R(θ)ᵀ`:

    Kxx = K1cos²θ + K2sin²θ    Kyy = K1sin²θ + K2cos²θ
    Kxy = (K1 − K2)sinθcosθ

Simétrico y definido positivo para K1,K2 > 0 — la condición que necesita
la matriz de rigidez para ser resoluble.

Integrado en **`Material.hydraulic`** con serialización en el `.ogr`,
como diálogo/propiedad independiente del modelo de resistencia (igual que
en la referencia, donde son dos diálogos sobre la misma lista de
materiales).

## 🆕 Solver (`ogr_fem2d/solvers/seepage.py`)

Resuelve `div(K·grad H) = 0` con `H = y + P/γw`.

**Condiciones de contorno** implementadas según la referencia:

| Tipo | Naturaleza | Valor |
|---|---|---|
| `TOTAL_HEAD` | Dirichlet en H | H |
| `PRESSURE_HEAD` | Dirichlet, H = y + hp | hp |
| `ZERO_PRESSURE` | Dirichlet, H = y | — |
| `NODAL_FLOW` | Neumann puntual | Q |
| `INFILTRATION` | Neumann sobre segmento | q por unidad de longitud |
| `UNKNOWN` | cara de rezume (P=0 o Q=0) | — |

**`default_boundary_conditions()`** reproduce los valores por defecto que
la referencia aplica al mallar: *Unknown* en la superficie del terreno
(incluida la cara del talud) y **flujo nodal nulo** en los bordes
izquierdo, derecho e inferior del contorno externo.

Detalles de implementación:

- **Ensamblaje Galerkin exacto**: en un T3 los gradientes de las
  funciones de forma son constantes, de modo que
  `Ke_ij = A·(∇Ni)ᵀ·K·(∇Nj)` es cerrado. No hace falta cuadratura
  numérica, lo que elimina el error de integración.
- **Infiltración** distribuida como `q·L/2` a cada nodo del segmento
  (vector de carga consistente exacto para elemento lineal).
- **Dirichlet por eliminación** conservando la simetría del sistema.
- **Resolución dispersa** con `scipy.sparse.linalg.spsolve`, con
  degradación a solve denso y finalmente a eliminación gaussiana
  puro-Python: el módulo nunca depende de SciPy de forma dura.
- **Problemas singulares detectados**: sin ninguna condición de cabeza el
  problema es Neumann puro y la cabeza queda definida solo salvo
  constante. El solver lo **reporta explícitamente** en vez de devolver
  un campo sin sentido.
- **Post-proceso**: cabeza total, de presión y presión intersticial
  nodales; velocidad de Darcy `v = −K·grad H` y módulo del gradiente por
  elemento; y **`flux_through_segment()`** que integra el caudal normal a
  través de una sección (la "discharge section" del Interpret de la
  referencia). Convención documentada: la normal es la tangente girada
  +90°, de modo que invertir la sección invierte el signo.

## ✔️ Validación contra soluciones analíticas cerradas

| Caso | Objetivo exacto | Resultado |
|---|---|---|
| Flujo confinado 1D, campo de cabezas | H lineal | error **1.1e-13 m** (precisión de máquina) |
| Caudal, ley de Darcy | K·ΔH/L·h | error **0.000 %** |
| Balance de masa entre 5 secciones | idéntico | dispersión **0.000 %** |
| **Patch test anisótropo** (5 tensores, Kxy≠0) | H y v exactos | error H **~1e-14**, v **~1e-19** |
| Capas en serie (flujo perpendicular) | media **armónica** | error **0.000 %** |
| Capas en paralelo (flujo paralelo) | media **aritmética** | error **0.000 %** |
| Balance de masa cruzando contraste 100× | idéntico | dispersión **0.000 %** |
| Infiltración: entrada = salida | q·L | error **0.000 %** |

El **patch test** es la prueba rigurosa del tensor completo: se impone un
gradiente de cabeza constante en todo el contorno y se comprueba que el
campo se reproduce exactamente y que `v = −K·grad H` también, incluyendo
los casos con `Kxy ≠ 0` (ángulos de 30°, 45°, −60°).

### Nota metodológica

Un primer intento de validar la anisotropía comparando el caudal con
`Kxx·ΔH/L·h` daba un 28 % de error en el caso θ=45°. **El error estaba en
la fórmula de comparación, no en el solver**: con `Kxy ≠ 0` un gradiente
horizontal genera velocidad vertical, así que imponer cabeza uniforme en
los bordes verticales y flujo nulo en los horizontales es *incompatible*
con un gradiente uniforme, y la solución desarrolla capas límite. El
patch test evita esa trampa imponiendo el campo lineal en todo el
contorno, donde sí es solución exacta.

## 📊 Tests

**475 tests, 475 verdes** (+31 desde v0.1.25; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_seepage_v126.py`): tensor de conductividad
(isótropo, alineado, rotado 90°, definido positivo, traza invariante bajo
rotación, serialización); flujo confinado 1D (campo exacto, Darcy,
balance de masa, cabeza de presión y presión intersticial, convención de
normal); patch test anisótropo (cabezas y velocidades exactas para 5
tensores, módulo del gradiente); medios estratificados (armónica,
aritmética, balance cruzando contraste, y que la pérdida de cabeza se
concentra >90× en la capa poco permeable); tipos de condición de contorno
(cabeza de presión, presión nula, infiltración, flujo nodal, singular,
malla vacía, defaults, serialización, sobrescritura); integración con
`Material` y con proyecto.

## ⏳ Siguiente

**Fase 3 — no saturado + cara de rezume**: funciones k(ψ) (Simple, van
Genuchten, Fredlund-Xing) en registro extensible, iteración de Picard con
subrelajación, y condición unilateral de rezume por conmutación nodal
(Neuman 1973; Bathe & Khoshgoftaar 1979). Es el bloque de mayor riesgo
numérico del módulo; banco de pruebas: los casos de presa homogénea con
superficie freática libre del PDF de verificación de flujo del proyecto.

Pendientes previos: decisión sobre `reject_tensile` por defecto en
búsquedas no circulares (anomalía A3) y política de succión en la Fase 4.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
