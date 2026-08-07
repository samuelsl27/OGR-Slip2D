# OGR Suite v0.1.30 — Changelog

**Lanzamiento:** 1 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 6: análisis transitorio.** Con esta versión el **módulo de agua
> subterránea queda completo**: las siete fases del plan (0 a 6)
> terminadas, desde el Water Pressure Grid hasta el flujo transitorio por
> etapas acoplado con la estabilidad.

---

## 🆕 Curva de retención y almacenamiento

`HydraulicProperties` incorpora lo que el transitorio necesita, separado
—como en la referencia— de la función de permeabilidad: ésta gobierna a
qué velocidad **se mueve** el agua, la retención cuánta agua **se
almacena**.

- **`water_content(ψ)`** — curva de van Genuchten θ(ψ) entre θ_r y θ_s.
- **`specific_moisture_capacity(ψ)`** — C = dθ/dh, derivada analítica.
- **`specific_storage`** — almacenamiento elástico Ss de la zona
  saturada.
- **`storage_at(P)`** — C en la zona no saturada, Ss por debajo de la
  freática.

## 🆕 Solver transitorio (`TransientSeepageSolver`)

Resuelve la ecuación de Richards en **forma mixta**
`∂θ/∂t = ∇·(K(ψ)∇H)` con **Euler implícito** (incondicionalmente
estable) y dos medidas que la literatura identifica como imprescindibles
para esta ecuación:

- **Picard modificado** (Celia, Bouloutas & Zarba, 1990). La forma en
  cabeza de presión de la ecuación de Richards arrastra errores grandes
  de balance de masa; escribir el término de almacenamiento en forma
  mixta y llevar explícitamente la diferencia de θ entre niveles
  temporales mantiene la masa acumulada consistente con los flujos.
- **Mass lumping** de la matriz de almacenamiento (sumada por filas a una
  diagonal). Una matriz de masa consistente produce oscilaciones de
  presión junto a frentes de humectación abruptos; el *lumping* las
  suprime y mejora convergencia y balance de masa.

Las caras de rezume siguen funcionando igual que en la Fase 3: la
conmutación nodal se aplica dentro de cada paso de tiempo.

### 🔴 Un error de formulación encontrado y corregido

La primera implementación acumulaba `θ` directamente, y **daba el
régimen permanente en vez del transitorio**: al validar contra la
solución analítica, el error era del 57 % y el campo calculado resultaba
ser exactamente el estacionario.

La causa es sutil y merece quedar documentada: **en la zona saturada θ es
constante** (θ_s), luego el término `(θ^m − θ^n)` de la forma mixta se
anula y el almacenamiento elástico desaparece por completo, colapsando la
ecuación sobre el permanente. La forma mixta clásica solo describe el
almacenamiento capilar.

La solución es un **contenido de almacenamiento generalizado** que
unifica ambos mecanismos:

    W(P) = θ(−P)            si P < 0   (almacenamiento capilar)
    W(P) = θ_s + Ss·P       si P ≥ 0   (almacenamiento elástico)

cuya derivada es exactamente `storage_at`, de modo que la linealización
de Picard modificado sigue siendo consistente a ambos lados de la
freática. Tras el cambio, el error cayó del 57 % al **0.11 %**.

## ✔️ Validación

**1. Solución analítica de difusión (erfc).** Un acuífero confinado y
totalmente saturado cumple `∂H/∂t = D·∂²H/∂x²` con `D = K/Ss`, cuya
respuesta a un escalón es `H = H0 + (H1−H0)·erfc[x/(2√(Dt))]`:

| Tiempo | Long. difusión | Error máx. |
|---|---|---|
| T = 200 | 8.9 m | **0.11 %** del salto |
| T = 1000 | 20.0 m | **0.10 %** del salto |
| T = 5000 | 44.7 m | *no aplica* |

A T = 5000 la longitud de difusión (44.7 m) ya cubre casi todo el
dominio (50 m), así que es la **solución analítica de medio infinito** la
que deja de ser válida, no el solver. La comparación se restringe por
tanto a la ventana donde la hipótesis se sostiene, y el test lo comprueba
explícitamente.

**2. Consistencia asintótica.** El transitorio a t → ∞ debe reproducir el
permanente de las mismas condiciones de contorno: **diferencia máxima
0.0000 m** contra el solver validado de la Fase 3. Es la comprobación más
fuerte, porque amarra toda la maquinaria nueva a la ya verificada.

**3. Física del almacenamiento.** El drenaje reduce monótonamente el agua
almacenada; multiplicar Ss por diez retrasa el frente de presión; y la
derivada de `storage_content` coincide con `storage_at` a ambos lados de
la freática (la consistencia que hace válido el esquema).

## 🖥️ Interfaz

- **Diálogo *Transient Groundwater***: tabla de etapas con tiempo,
  casilla **Calculate SF** por etapa y etiqueta, más las opciones FEA
  transitorias (tolerancia, iteraciones máximas y número de pasos de
  tiempo, con **Auto** cuando vale 0). Valida que los tiempos sean
  positivos y distintos, y los ordena.
- **Exclusividad de opciones avanzadas**: `set_advanced_option()` en los
  ajustes garantiza que transitorio, exceso de presión intersticial y
  descenso rápido **no puedan estar activos a la vez**, como especifica
  la referencia. El diálogo avisa antes de conmutar.
- **Compute Groundwater** deriva automáticamente al solver transitorio
  cuando la opción está activa y hay etapas definidas; el campo de la
  última etapa alimenta el análisis de estabilidad. Los resultados por
  etapa quedan en `project.transient_results`.
- **Número de pasos automático**: criterio de difusión sobre el tamaño de
  elemento (el frente no debe cruzar más de un elemento por paso),
  acotado a un rango práctico.

## 📊 Tests

**569 tests, 569 verdes** (+25 desde v0.1.29; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_transient_v130.py`): curva de retención
(límites analíticos, monotonía, capacidad contra diferencias finitas,
`storage_content` como integral de `storage_at`, rama elástica no
degenerada, serialización); difusión analítica (erfc, avance del frente,
retardo con mayor almacenamiento); consistencia asintótica con el
permanente y reducción de agua almacenada al drenar; etapas y ajustes
(serialización, exclusividad de opciones avanzadas, selección de etapas
con SF, metadatos por etapa, lista vacía, pasos automáticos); y GUI
(acción habilitada con FEA, guardado con exclusividad, ordenación de
etapas, derivación del cálculo al transitorio y camino permanente
intacto cuando está desactivado).

## 🏁 Estado del módulo de agua subterránea

| Fase | Contenido | Versión |
|---|---|---|
| 0 | Water Pressure Grid | v0.1.23 |
| 1 | Malla FE T3 | v0.1.25 |
| 2 | Solver permanente saturado | v0.1.26 |
| 3 | No saturado + cara de rezume | v0.1.27 |
| 4 | Acople con estabilidad | v0.1.28 |
| 5 | GUI modo Groundwater e Interpret | v0.1.29 |
| 6 | **Transitorio** | **v0.1.30** |

**Módulo completo.**

## ⏳ Siguiente

Vuelven a primer plano los pendientes ajenos al agua, por orden de
impacto según `docs/AUDITORIA_v0.1.22.md`:

1. **Anomalía A3** — reimplementar `reject_tensile` como post-filtro (al
   seleccionar la superficie crítica) en vez de filtro durante la
   búsqueda, que es lo que dejaba a Simulated Annealing sin superficies.
2. **Análisis probabilístico y de sensibilidad** — el mayor ausente
   frente a la referencia.
3. Back analysis de soportes, import DXF, cobertura i18n.

Las otras dos opciones avanzadas de agua (exceso de presión intersticial
por B-bar y descenso rápido) tienen ya *hooks* parciales y la
infraestructura de exclusividad lista.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
