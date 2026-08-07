# OGR Slip2D / OGR FEM2D v0.1.25 — Changelog

**Lanzamiento:** 26 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 1 del plan de agua subterránea: generador de malla de elementos
> finitos.** `ogr_fem2d` deja de ser un stub y pasa a producir mallas
> triangulares T3 conformes sobre las regiones de material del modelo.

---

## 🆕 `ogr_fem2d/mesh` — malla FE T3

### Estructuras (`mesh.py`)

- **`Node`** — vértice inmutable con id estable.
- **`Element`** — triángulo lineal T3 (nodos CCW) que porta su material
  y la región de origen. Incluye lo que el solver necesitará en la Fase
  2: `shape_gradients()` (dN/dx, dN/dy y área, constantes en T3),
  `barycentric()`, `contains()`, `area()`, `angles_deg()`.
- **`Mesh`** — contenedor con `quality_stats()`, `edge_map()`,
  `boundary_edges()` (donde se aplicarán las condiciones de contorno de
  filtración), `is_conforming()`, `locate()` e `interpolate()` (que ya
  prepara el acople LEM de la Fase 4), y serialización completa.

### Generador (`generator.py`)

Algoritmo en tres etapas:

1. **Discretización de contornos con registro global de nodos.** Cada
   arista de región se parte en tramos de ~`target_size`, y todos los
   nodos pasan por un registro único indexado por coordenadas
   cuantizadas. Así, una arista compartida por dos regiones produce
   **los mismos ids de nodo en ambas** — de ahí sale la conformidad
   entre interfaces de material, sin ninguna pasada de cosido posterior.
2. **Triangulación por regiones.** Cada región se triangula por separado
   con sus nodos de contorno más puntos interiores sembrados en retícula
   escalonada (casi equilátera); se calcula la triangulación de Delaunay
   y se descartan los triángulos cuyo centroide cae fuera del polígono.
   Al triangular región por región se garantiza que **ningún elemento
   cruza una interfaz de material**, por lo que la asignación de material
   es exacta y no aproximada.
3. **Refinamiento por calidad.** Los triángulos con ángulo mínimo por
   debajo de `min_angle` aportan su circuncentro como nuevo punto
   interior (refinamiento tipo Chew/Ruppert) y la región se retriangula.
   Se rechazan circuncentros fuera del polígono o demasiado próximos a
   un nodo existente, que es lo que garantiza la terminación.

## ⚖️ Decisión de dependencia: SciPy, no Triangle

Se usa **`scipy.spatial.Delaunay`** (Qhull, BSD). Se descartó
`triangle` — el wrapper de *Triangle* de Shewchuk — por un motivo
dirimente que conviene dejar por escrito: **su licencia prohíbe el uso
comercial**, lo que es incompatible con la GPL-3.0 de este proyecto.
SciPy ya era dependencia núcleo, de modo que **esta fase no añade
ninguna dependencia nueva**. Se incluye además un triangulador
**Bowyer–Watson puro-Python** como fallback si SciPy no estuviese
disponible.

Elementos: **T3 primero**, suficiente para flujo (H lineal ⇒ flujo
constante por elemento, formulación clásica de filtración; Bathe &
Khoshgoftaar, 1979). El contenedor admite T6 más adelante sin cambios
estructurales.

## 🔗 Integración

- **`Project.fem_mesh`** con serialización en el `.ogr` (round-trip
  probado).
- **Menú: `Generate FE Mesh…`** (pide el nº aproximado de elementos y
  reporta elementos/nodos/ángulo mínimo en la barra de estado) y
  **`Reset FE Mesh`**.
- **Canvas**: aristas de la malla en gris fino por debajo de la
  geometría, con opción de visualización `show_fem_mesh`.
- Los materiales se resuelven por región consultando el proyecto en el
  centroide (igual que hace el dovelador), porque las propiedades
  hidráulicas de las Fases 2–3 son por material.

## ✔️ Validación

Malla del modelo de referencia (3 regiones de material):

| Pedidos | Elementos | Nodos | Ángulo mín. | Área |
|---|---|---|---|---|
| 200 | 181 | 114 | 25.75° | 4562.50 |
| 600 | 576 | 328 | 25.82° | 4562.50 |
| 1500 | 1430 | 778 | 24.68° | 4562.50 |
| 3000 | 2962 | 1569 | 24.45° | 4562.50 |

Dos invariantes clave: el **área es exactamente constante** en todos los
niveles de refinado y coincide con la de las regiones (sin huecos,
solapes ni fugas fuera del dominio), y la **calidad no degrada** al
refinar (ángulo mínimo estable en ~25°).

## 📊 Tests

**444 tests, 444 verdes** (+28 desde v0.1.24; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_mesh_v125.py`):
- **Conservación de área exacta** sobre cuadrado analítico y modelo de
  referencia, e invariante entre niveles de refinado
- Conformidad, orientación CCW, área positiva de todos los elementos
- Umbral de calidad (0 % de elementos por debajo de 20°)
- **Conformidad entre regiones**: nodos de la interfaz compartidos, la
  interfaz no genera aristas de contorno, y ningún elemento cruza la
  interfaz
- **Funciones de forma T3**: gradientes que derivan exactamente un campo
  lineal, partición de la unidad, baricéntricas e interpolación exacta
- Contorno cerrado (todo nodo de contorno con grado 2 y sobre el
  perímetro)
- Triangulador de fallback Bowyer–Watson (área correcta, entrada
  degenerada)
- Serialización de malla y de proyecto con/sin malla, e integración GUI

## ⏳ Siguiente

**Fase 2 — solver permanente saturado**: ensamblaje Galerkin
(k anisótropo por material), Dirichlet (H, P) y Neumann (Q, infiltración),
resolución dispersa con `scipy.sparse`. Validación contra soluciones
cerradas (flujo confinado bajo presa, Dupuit en acuífero libre).

Pendientes previos: decisión sobre activar `reject_tensile` por defecto
en búsquedas no circulares (anomalía A3, ver `CHANGELOG_v0.1.24.md`) y
la política de succión al acoplar en la Fase 4.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
