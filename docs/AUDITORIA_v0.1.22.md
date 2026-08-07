# Auditoría del código — OGR Suite v0.1.22

> **ACTUALIZACIÓN v0.1.24** — Anomalías **A1, A2 y A4 CORREGIDAS**
> (causa raíz común de A1/A2: signo del límite angular superior del
> *Initial Angle at Toe*). **A3 investigada**: confirmada como
> artefacto de superficies cinemáticamente inadmisibles; se añade el
> filtro opcional `reject_tensile`, desactivado por defecto pendiente
> de tu decisión. Ver `CHANGELOG_v0.1.24.md` para el detalle completo.
>
> **ACTUALIZACIÓN v0.1.32** — **A3 RESUELTA**: el mecanismo correcto es
> el *m-alpha check* (Whitman & Bailey 1967), no la tracción interdovela.
> Implementado como post-filtro real, y **desactivado por defecto** con
> justificación numérica: el círculo de referencia validado también lo
> incumple. Recomendado activarlo solo en búsquedas no circulares.
> Nueva anomalía **A5**: Simulated Annealing con Spencer da 0 superficies
> válidas. Ver `CHANGELOG_v0.1.32.md`.
>
> **ACTUALIZACIÓN v0.1.39** — **A5 RESUELTA**, y el diagnóstico inicial
> era incorrecto: no era cosa de Spencer sino del **bootstrap** del
> recocido, que sorteaba cada vértice de forma independiente y dependía
> del azar para pasar el filtro de unimodalidad (probabilidad < 1 %).
> Con ciertas semillas fallaban TODOS los métodos. Corregido construyendo
> la superficie inicial admisible por construcción.

**Autor:** Samuel Sáez López — UPCT
**Fecha:** 7 de julio de 2026

Auditoría completa de la base de código (~26.500 líneas de producción +
6.700 de tests) contra el conjunto de funciones de la referencia
comercial. Estado de la suite: **389/389 tests verdes**.

---

## 1. QUÉ TENEMOS (verificado funcionando)

### Motor LEM (`ogr_slip2d`) — COMPLETO en métodos
| Bloque | Estado |
|---|---|
| 7 métodos LEM (Ordinary, Bishop, Janbu S/C, Spencer, GLE/M-P, Lowe-Karafiath) | ✅ Validados < 0.7 % contra referencia |
| Funciones interdovela GLE (constant, half-sine, trapezoidal) | ✅ |
| Superficies circulares (`SlipCircle`) y **no circulares** (`SlipSurface` polilínea) | ✅ |
| 6 métodos de búsqueda: Grid, Slope, Auto Refine, Block, Path, Simulated Annealing | ✅ Corren de extremo a extremo (ver anomalías §3) |
| Dovelado con crack de tracción, cargas superficiales, sísmico kh/kv | ✅ |
| Integración de soportes (7 tipos: End Anchored, Grouted Tieback ±friction, Soil Nail, Micro Pile, GeoTextile, User Defined) | ✅ |
| Post-procesador interdovela + línea de empuje (v0.1.22) | ✅ Cierre 0.00 % en rigurosos |

### Núcleo (`ogr_core`)
| Bloque | Estado |
|---|---|
| Geometría: boundaries tipadas, regiones por subdivisión planar, welding de endpoints, cleanup, transforms, expand/shrink | ✅ |
| 14+ modelos de resistencia (MC, Undrained, Hoek-Brown ×2, Power Curve, Hyperbolic, Barton-Bandis, Drained-Undrained, Anisotropic Linear, Shear-Normal function, Vertical Stress Ratio, Infinite, NoStrength, Generalized Anisotropic…) | ✅ Registro extensible |
| Presión intersticial: None, Water Table, Piezo lines, Ru, Constante (+ hooks Hu, auto-Hu, B-bar, rapid drawdown) | ✅ |
| Enum `PorePressureType.FEM_SEEPAGE` ya reservado para acople con FEM2D | ✅ (hook, sin motor detrás) |
| Proyecto `.ogr` JSON, undo/redo por comandos, unidades, settings estilo referencia | ✅ |
| Informe PDF multipágina (reportlab) | ✅ |

### GUI (`ogr_gui`, 13.500 líneas)
Canvas CAD (snap, zoom, y-arriba), 15 diálogos, docks de resultados,
ventana Interpret con: selector de método, heatmap FoS por método, modos
Global Min / Minimum / All, Show Slices, Query Slice Data, Show Values
Along Surface, Filter Surfaces, Surfaces Crossing Point, tabla ordenable,
histogramas, **FBD método-consistente** y **Line of Thrust** (v0.1.22).

### CLI (`ogr_cli`) — funcional para análisis por lotes.

---

## 2. QUÉ FALTA (respecto a la referencia)

Ordenado por impacto:

1. **Módulo de agua subterránea FEM** — `ogr_fem2d` es un stub de 11
   líneas. Es el bloque mayor pendiente → ver `PLAN_AGUA_SUBTERRANEA.md`.
2. **Water Pressure Grid** (Total Head / Pressure Head / Pore Pressure):
   el método de interpolación de presiones desde malla de puntos no
   existe (`GroundwaterMethod` solo tiene water surfaces / Ru). Encaja
   como Fase 0 del plan de agua (es útil por sí solo y sirve de puente).
3. **Análisis probabilístico / sensibilidad**: distribuciones
   (Normal, Lognormal, Beta, Gamma, Exponencial, Triangular, Uniforme),
   muestreo Monte Carlo / Latin Hypercube, PF y RI. Nada implementado.
4. **Back Analysis de fuerza de soporte** — no implementado.
5. **Import DXF / imagen de fondo / import de formatos ajenos** — no.
6. **Optimize Surfaces** post-búsqueda (refinado local de la crítica):
   `PathSearch` tiene flag `optimize` pero no hay optimizador global
   aplicable a cualquier superficie.
7. **i18n**: el selector de idioma ES/EN existe en preferencias pero la
   cobertura de cadenas traducidas es parcial.
8. Detalles menores del Interpret: export de gráficos por lotes, query
   multi-superficie simultánea.

---

## 3. ⚠️ ANOMALÍAS DETECTADAS (reportadas SIN corregir, como acordado)

Prueba: caso de referencia, Bishop, misma configuración de dovelas.
Contexto: Grid Search da crítico **0.899–0.904** y AutoRefine **0.892**
(coherentes con la referencia 0.883).

### A1 — PathSearch: 97 % de superficies rechazadas
`PathSearch(num_paths=150)` → **solo 4 superficies válidas** y crítico
FoS = 1.60 (muy por encima del 0.88 esperado). El generador de caminos
produce casi siempre geometrías inválidas o el filtro de validez es
demasiado agresivo. **Sospecha**: generación de caminos que no cortan
bien el talud (ángulos iniciales/elevación mínima mal acotados) o
rechazo en `min_area`/intersección con terreno.

### A2 — SlopeSearch: FoS alto y pocas válidas
`SlopeSearch(num_surfaces=200)` → 46 válidas, crítico **1.049** (20 %
por encima de Grid/AutoRefine en el mismo modelo). Un Slope Search sano
debería aterrizar cerca del mínimo global (~0.88–0.92). **Sospecha**:
el muestreo de extremos sobre el talud no cubre la zona del pie donde
vive la crítica, o el rango de ángulos iniciales la excluye.

### A3 — BlockSearch/SimAnnealing dan crítico ~0.70–0.74 (a verificar)
Ambos no circulares coinciden entre sí (0.701 y 0.745), un 20 % por
debajo del mínimo circular. Puede ser **legítimo** (los mecanismos
poligonales pueden ser más críticos si el modelo tiene un contraste de
materiales que lo favorece) o puede ser un artefacto (superficies con
tramos casi verticales aceptadas como válidas, o el guardado de
admisibilidad de fuerzas no aplicado en métodos de momentos con
geometrías extremas). **Requiere contraste con la referencia** en el
mismo modelo con Block Search antes de tocar nada: si la referencia
también da ~0.7 en no circular, no hay bug.

### A4 — `ogr_slip2d.__version__ = "0.1.1"` desincronizado
Cosmético: el paquete motor declara 0.1.1 mientras `pyproject.toml` va
por 0.1.22. Corrección trivial (una línea) pendiente de tu OK para
unificar la fuente de versión.

**Recomendación de orden**: A1 y A2 primero (afectan a resultados que
un usuario puede tomar por buenos); A3 tras contraste con referencia;
A4 cuando quieras.

---

## 4. Riesgos estructurales menores

- `interpret_window.py` (~1.900 líneas) y `canvas_view.py` (~1.400)
  van camino de monolito; conviene trocear en mixins/paneles cuando se
  añada la vista de resultados de agua (Fase 5 del plan GW).
- Los buscadores comparten poca infraestructura de validación de
  superficie; unificar el "validador de superficie candidata" evitaría
  que A1–A3 se reproduzcan por caminos distintos.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
