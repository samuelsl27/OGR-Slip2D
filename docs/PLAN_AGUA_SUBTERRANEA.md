# Plan de desarrollo: módulo de agua subterránea (OGR FEM2D)

**Autor:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Fecha:** 7 de julio de 2026
**Estado:** **Fase 0 COMPLETA** (v0.1.23 — Water Pressure Grid) · **Fase 1 COMPLETA** (v0.1.25 — malla FE T3) · **Fase 2 COMPLETA** (v0.1.26 — solver permanente saturado) · **Fase 3 COMPLETA** (v0.1.27) · **Fase 4 COMPLETA** (v0.1.28) · **Fase 5 COMPLETA** (v0.1.29) · **Fase 6 COMPLETA** (v0.1.30 — transitorio). **MÓDULO DE AGUA SUBTERRÁNEA COMPLETO: las 7 fases (0-6) terminadas** y cerrado funcionalmente en v0.1.31 (FoS por etapa y navegación temporal en el Interpret). Ver `INTERFAZ_AGUA_SUBTERRANEA.md` para la especificación de GUI de la Fase 5.

---

## 0. Ingeniería inversa de la referencia

Del análisis de la documentación (Groundwater_Overview, Groundwater_Methods,
Hydraulic_Properties, Set_Boundary_Conditions, Mesh_Overview/Setup,
Compute/Interpret_Groundwater, Water_Pressure_Grid, Add_Discharge_Section,
Transient_Groundwater, Advanced_Groundwater) se extrae la arquitectura
funcional completa del módulo de referencia:

**Principios de diseño observados:**

1. **Motores separados, acople unidireccional.** El motor de flujo FEM es
   completamente independiente del motor de estabilidad. Se ejecuta primero
   el flujo; sus presiones intersticiales alimentan luego el LEM
   automáticamente. Nuestro enum `PorePressureType.FEM_SEEPAGE` ya reserva
   ese hook.
2. **Modo de análisis conmutable.** Un selector "Analysis Mode"
   (Slope Stability ↔ Groundwater) cambia menús y toolbar. La geometría es
   compartida; malla, propiedades hidráulicas y condiciones de contorno
   son exclusivas del modo agua.
3. **Seis métodos de agua en Project Settings:** Water Surfaces,
   Ru Coefficients, Water Pressure Grid ×3 (Total Head / Pressure Head /
   Pore Pressure) y Steady State FEA. Nosotros ya tenemos los dos primeros;
   faltan los grids y el FEA.
4. **Flujo saturado/no saturado, régimen permanente** como base;
   transitorio como opción avanzada con etapas temporales y FoS por etapa.
5. **Malla FE automática** (triángulos 3/6 nodos, cuadriláteros 4/8),
   número aproximado de elementos, discretización personalizable,
   refinamiento local; condiciones por defecto al mallar: *Unknown
   (P=0 o Q=0)* en la cara del talud y *flujo nodal nulo* en laterales
   y fondo.
6. **Condiciones de contorno:** Total Head (H), Pressure Head (P),
   Zero Pressure, Nodal Flow Q (incluye Q=0), Infiltración vertical q,
   Seepage face (Unknown), Total Head linealmente variable a lo largo de
   un contorno.
7. **Post-proceso de flujo:** cabezas totales/de presión, presión
   intersticial (incluida succión negativa), vectores/líneas de flujo,
   superficie freática (isolínea P=0), **secciones de descarga** con
   caudal integrado, gradientes y velocidades.

## 0-bis. Base matemática (literatura)

- **EDP en permanente:** ∇·(k(ψ)·∇H) = 0, con H = z + ψ (cabeza total),
  k tensorial (k_x, k_y y ángulo) dependiente de la succión ψ en zona no
  saturada. Es la forma estacionaria de la ecuación de Richards.
- **No linealidad k(ψ):** funciones de permeabilidad relativas —
  la referencia usa un modelo *simple* (k cae varios órdenes bajo
  succión) y los estándar de la literatura: **Gardner (1958)**,
  **Brooks-Corey (1964)**, **van Genuchten (1980)**, **Fredlund-Xing
  (1994)**. Basta implementar Simple + van Genuchten + Fredlund-Xing
  para cubrir la práctica.
- **Discretización:** Galerkin estándar; K_e = ∫ Bᵀ k B dΩ con
  cuadratura de Gauss; sistema no lineal K(H)·H = Q resuelto por
  **Picard con subrelajación** (robusto y suficiente en permanente;
  Newton opcional después).
- **Seepage face:** condición unilateral (Signorini): en cada iteración,
  nodos "Unknown" con P>0 pasan a Dirichlet P=0 y nodos con flujo
  entrante no físico vuelven a Q=0 (algoritmo clásico de Neuman 1973 /
  Bathe & Khoshgoftaar 1979).
- **Transitorio:** añade término de almacenamiento m_w·γ_w·∂H/∂t
  (m_w de la curva de retención); integración temporal implícita
  (Euler hacia atrás), etapas con FoS bajo demanda.
- **Validación:** la propia `Slide_GroundwaterVerification.pdf` del
  proyecto contiene los casos con resultados numéricos (presas de
  tierra homogéneas/zonificadas, flujo confinado/no confinado, seepage
  faces) — es nuestro banco de pruebas natural, igual que hicimos con
  los 7 métodos LEM.

---

## FASES DE DESARROLLO

### ✅ Fase 0 — Water Pressure Grid  *(COMPLETADA en v0.1.23)*
Implementar el método de grid de presiones (Total Head / Pressure Head /
Pore Pressure): entidad `WaterPressureGrid` en `ogr_core`, interpolación
espacial (la referencia ofrece varios interpoladores; empezar con TIN +
inverso de distancia), integración en `pore_pressure_at`, diálogo de
edición/importación CSV y pintado en canvas. **Valor:** permite consumir
resultados de cualquier programa de flujo externo ya hoy, y define la
interfaz de consumo que reutilizará el FEM propio.
*Entregable:* método seleccionable en Project Settings + tests de
interpolación contra valores analíticos.

### ✅ Fase 1 — Malla FE (`ogr_fem2d/mesh`)  *(COMPLETADA en v0.1.25)*
Generador de malla triangular (T3, luego T6) sobre las regiones ya
existentes (reutiliza la subdivisión planar de `ogr_core.geometry`):
discretización de contornos por nº aproximado de elementos, mallado
Delaunay restringido (vía `triangle` o implementación propia con
shapely + refinamiento Ruppert simplificado), calidad mínima de ángulo,
refinamiento local por región/línea. Estructuras: `Node`, `Element`,
`Mesh` con mapeo región→material.
*Entregable:* `Discretize & Mesh` desde CLI + visor de malla en canvas +
tests de calidad (ángulo mínimo, conformidad, nº de elementos).

### ✅ Fase 2 — Solver permanente saturado  *(COMPLETADA en v0.1.26)*
Ensamblaje Galerkin lineal (k constante por material, anisótropo con
ángulo), condiciones Dirichlet (H, P) y Neumann (Q nodal, infiltración),
resolución dispersa (`scipy.sparse`). Sin no linealidad todavía.
*Entregable:* validación contra soluciones cerradas (flujo confinado
bajo presa, dupuit en acuífero libre rectangular) con error < 1 %.

### ✅ Fase 3 — No saturado + seepage face  *(COMPLETADA en v0.1.27)*
Funciones k(ψ): Simple, van Genuchten, Fredlund-Xing (registro
extensible como el de modelos de resistencia). Iteración de Picard con
subrelajación adaptativa; condición Unknown/seepage face por conmutación
nodal. Este es el corazón del módulo y el bloque de mayor riesgo
numérico.
*Entregable:* casos del PDF de verificación de flujo (presa homogénea
con superficie freática libre y cara de rezume) dentro de tolerancia;
tests de regresión de convergencia (nº de iteraciones acotado).

### ✅ Fase 4 — Acople con estabilidad  *(COMPLETADA en v0.1.28)*
`PorePressureType.FEM_SEEPAGE` operativo: interpolación de u en los
puntos medios de base de dovela desde el campo FE (localización de
elemento + shape functions). Flujo de trabajo Compute GW → Compute
Slope. Succiones: opción de truncar u<0 o usarla (resistencia no
saturada φ_b, ya previsto en materiales).
*Entregable:* caso de verificación combinado flujo+estabilidad
reproducido de la referencia.

### ✅ Fase 5 — GUI modo Groundwater + Interpret de flujo  *(COMPLETADA en v0.1.29)*
Selector Analysis Mode, diálogo de propiedades hidráulicas (Ks, k2/k1,
ángulo, función no saturada con vista previa de curva), Set Boundary
Conditions interactivo sobre la malla, Mesh Setup, y en Interpret:
contornos de H/P/u, vectores de flujo, freática P=0, secciones de
descarga con caudal integrado. Reutiliza el heatmap y la infraestructura
de overlays de v0.1.20–22.

### ✅ Fase 6 — Transitorio  *(COMPLETADA en v0.1.30)*
Etapas temporales, almacenamiento m_w, FoS por etapa, rapid drawdown
acoplado, exportación de resultados por etapa al informe PDF.

**Orden recomendado:** 0 → 1 → 2 → 3 → 4 → 5 → 6. Cada fase termina
con ZIP versionado, changelog y tests de validación cuantitativa, como
venimos haciendo con el LEM.

---

## Decisiones RESUELTAS (Fase 1, v0.1.25)

1. **Dependencia de mallado → `scipy.spatial.Delaunay`.** Se descartó
   `triangle` (wrapper de *Triangle* de Shewchuk) por un motivo
   dirimente: **su licencia prohíbe el uso comercial**, lo que es
   incompatible con la GPL-3.0 de este proyecto. SciPy (BSD) ya era
   dependencia núcleo, así que la Fase 1 **no añade ninguna dependencia
   nueva**. Se incluye además un triangulador Bowyer–Watson puro-Python
   como fallback si SciPy no estuviese disponible.
2. **Elementos → T3 primero.** Suficiente para flujo (H lineal ⇒ flujo
   constante por elemento, formulación clásica de filtración). El
   contenedor `Mesh` admite T6 más adelante por inserción de nodos
   intermedios sin cambios estructurales.

## Decisión RESUELTA (Fase 4, v0.1.28)

3. **Succión en resistencia → NO es un checkbox de truncado.** La
   referencia no trunca: mantiene la presión negativa y controla su
   aportación mediante la **envolvente bilineal de Mohr-Coulomb extendida**
   (Fredlund et al. 1978) con dos parámetros por material,
   `phi_b` (ángulo de resistencia no saturada) y `air_entry_value`,
   **ambos 0 por defecto**. Con esos defectos la succión no aporta nada,
   que es exactamente el truncado conservador — pero obtenido como *caso
   particular* de una formulación general, no como un interruptor
   aparte. Implementado así.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
