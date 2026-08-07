# OGR FEM2D v0.1.27 — Changelog

**Lanzamiento:** 26 de julio de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase 3 del plan de agua subterránea: flujo no saturado con superficie
> freática libre y caras de rezume.** El bloque de mayor riesgo numérico
> del módulo. Seis modelos k(ψ) de la referencia, iteración de Picard con
> subrelajación y conmutación nodal para la condición unilateral de
> rezume. Validado por **convergencia al resultado analítico exacto de
> Charnyi/Dupuit**.

---

## 🆕 Modelos de permeabilidad (`ogr_core/hydraulic/permeability_models.py`)

Los **seis modelos** de la referencia, en registro extensible
(`register_model`) igual que el de modelos de resistencia:

| Modelo | Forma implementada | Referencia |
|---|---|---|
| **Constant** | kr = 1 | — |
| **Simple** | caída log-lineal de N décadas hasta ψ_ref, constante después; con **tipos de suelo** General/Sand/Silt/Clay/Loam | — |
| **Brooks-Corey** | kr = 1 si ψ≤ψb; kr = (ψb/ψ)^(2+3λ) si ψ>ψb | Brooks & Corey (1964) |
| **Fredlund-Xing** | kr = 1/{ln[e+(ψ/A)^B]}^C | Fredlund & Xing (1994) |
| **Gardner** | kr = 1/(1+a·h^n) | Gardner (1956) |
| **van Genuchten** | Se=[1+(αh)^n]^(−m); kr = Se^½·[1−(1−Se^(1/m))^m]² | van Genuchten (1980) |
| **User Defined** | tabla (succión, k) con interpolación log-lineal | — |

Detalles fieles a la especificación: el tipo *General* de Simple cae
**exactamente un orden de magnitud** y se estabiliza; van Genuchten usa
`m = 1 − 1/n` (restricción de Mualem) salvo que se active **Custom m**;
en User Defined el **primer punto es la permeabilidad saturada**. Todas
las funciones se acotan a `kr_min` para que la matriz de conductividad
no degenere en zonas muy secas — práctica estándar y lo que mantiene
resoluble la iteración de Picard.

**Biblioteca de materiales representativos** (`library_for()`), el
equivalente al botón *Pick*: valores de van Genuchten de Carsel & Parrish
para ocho texturas, más juegos para Brooks-Corey, Gardner y
Fredlund-Xing. Y **`curve()`** para el botón *Plot*.

## 🆕 Solver no lineal (`UnsaturatedSeepageSolver`)

Resuelve simultáneamente dos no linealidades:

1. **k(ψ)** por **iteración de Picard con subrelajación**
   `H ← (1−w)·H_old + w·H_new`. La subrelajación es lo que da robustez
   cuando la función de permeabilidad es abrupta (arenas), donde el punto
   fijo simple oscila.
2. **Cara de rezume**: condición unilateral (Signorini) «P = 0 **o**
   Q = 0» resuelta por **conmutación nodal** (Neuman 1973; Bathe &
   Khoshgoftaar 1979): un nodo libre cuya presión se vuelve positiva pasa
   a Dirichlet P = 0; un nodo conmutado cuya reacción indica entrada de
   agua se libera.

La superficie freática **no** se sigue como contorno móvil: es
simplemente la isolínea P = 0 de la solución convergida, con malla fija
(`free_surface_points()`). Se evita así el remallado.

## 🔴 Dos problemas reales encontrados y corregidos

**1. Signo de la reacción invertido.** La liberación de nodos de rezume
usaba el criterio contrario al correcto: liberaba cuando el agua *salía*
(el estado físicamente válido) y mantenía el nodo cuando entraba. Se fijó
la convención **empíricamente** con un caso 1D — reacción **positiva =
agua entrando** al dominio, con magnitudes que coinciden exactamente con
el caudal esperado — y se blindó en un test dedicado
(`TestReactionSignConvention`), porque todo el algoritmo de conmutación
depende de ese signo.

**2. Oscilación del conjunto activo (*chattering*).** Con la conmutación
nodal pura el conjunto de nodos de rezume oscilaba indefinidamente
(2→1→0→2→1→0…) y las cabezas nunca se estabilizaban: **300 iteraciones
sin converger**. Es la dificultad clásica del algoritmo. Se aplican dos
remedios estándar: **banda de histéresis** en ambas decisiones (tolerancia
de presión escalada al tamaño de elemento, y de flujo escalada al caudal
total, para ser dimensionalmente consistente entre permeabilidades) y
**presupuesto de conmutaciones por nodo** (`max_node_switches`, 3 por
defecto) tras el cual el nodo se congela, lo que garantiza que el
conjunto activo se estabilice. Resultado: **convergencia en 19
iteraciones**.

## ✔️ Validación: convergencia al resultado analítico exacto

Para el flujo a través de una presa rectangular sobre base impermeable,
el caudal es **exactamente** `q = K(H1²−H2²)/(2L)` cuando la zona sobre
la freática no conduce (resultado de Charnyi). Nuestra formulación no
saturada **sí** deja conducir esa zona, luego el caudal es legítimamente
mayor; al hacer k(ψ) progresivamente más abrupta debe converger al valor
analítico. Es exactamente lo que ocurre:

| k(ψ) | kr(2 m) | caudal | dif. vs analítico |
|---|---|---|---|
| Gardner a=0.05 n=2 (suave) | 8.3e-1 | 3.19e-5 | 32.9 % |
| Gardner a=1 n=3 | 1.1e-1 | 2.74e-5 | 14.4 % |
| Gardner a=50 n=4 | 1.3e-3 | 2.53e-5 | 5.5 % |
| Gardner a=1e4 n=5 (abrupta) | 3.1e-6 | 2.44e-5 | **1.6 %** |

La convergencia monótona valida el solver **y** explica el exceso: no era
un error, era la zona no saturada conduciendo. El 1.6 % residual es error
de discretización.

Además: la freática arranca a la cota del embalse (9.86 frente a H1=10) y
**aflora en el paramento aguas abajo por encima del nivel de aguas abajo**
(3.6 frente a H2=2), que es el rasgo definitorio de una cara de rezume.
Y con modelo *Constant* el solver no lineal **reproduce exactamente** el
resultado lineal de la Fase 2.

## 📚 Ingeniería inversa de la interfaz

Nuevo documento **`docs/INTERFAZ_AGUA_SUBTERRANEA.md`**: especificación
completa de la GUI del módulo (Fase 5) obtenida por ingeniería inversa de
la documentación de referencia — conmutador de modo de análisis, orden y
**dependencias duras** del menú (las condiciones de contorno están
deshabilitadas sin malla; las propiedades hidráulicas solo con método
FEA), estructura de los diálogos *Define Hydraulic Properties* (con Plot,
Pick, Custom m, Soil Type, y el detalle de que nombres y colores de
material **no** son editables ahí) y *Set Boundary Conditions* (iconos,
qué controles se habilitan por tipo, infiltración solo por segmentos), y
el inventario del Interpret de agua. Los nombres de parámetro se
confirmaron cruzando el diálogo con la lista de variables aleatorias
hidráulicas de la referencia.

## 🔄 Compatibilidad

`HydraulicProperties` acepta archivos de v0.1.26: la clave
`unsaturated_model` se lee y `"saturated"` se traduce a `CONSTANT`. El
enum `UnsaturatedModel` se conserva como alias.

## 📊 Tests

**504 tests, 504 verdes** (+29 desde v0.1.26; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_unsaturated_v127.py`): los seis modelos
(límite saturado kr(0)=1, monotonía, acotación, forma cerrada verificada
de Brooks-Corey/Gardner/Fredlund-Xing, m=1−1/n por defecto y Custom m,
Simple/General cayendo una década exacta, orden por textura,
interpolación User Defined, escalado de Ks y del tensor conservando la
anisotropía, Plot y Pick, serialización de todos los modelos y
compatibilidad con v0.1.26); convención de signo de reacción con balance
global; presa no saturada (convergencia sin oscilación, freática por
encima del nivel de aguas abajo, arranque en la cota del embalse, descenso
monótono, nodos de rezume reportados, **convergencia monótona a
Charnyi**, equivalencia con el solver lineal en modo Constant, aviso de
no convergencia, rango de kr, malla vacía).

## ⏳ Siguiente

**Fase 4 — acople con estabilidad**: `PorePressureType.FEM_SEEPAGE`
operativo, interpolando u en los puntos medios de base de dovela desde el
campo FE (`Mesh.interpolate()` ya está listo y validado). Decisión
pendiente: política de succión (¿truncar u<0 por defecto?).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
