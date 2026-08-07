# Plan de desarrollo: análisis probabilístico y de sensibilidad

**Autor:** Samuel Sáez López — UPCT
**Fecha:** 2 de agosto de 2026
**Estado:** ✅ P0 completa (v0.1.33) · ✅ P1 completa (v0.1.34) · ✅ P2 completa (v0.1.35) · ✅ P4 completa (v0.1.36) · ✅ P3 completa (v0.1.37) · ✅ P5 completa (v0.1.38). **MÓDULO PROBABILÍSTICO COMPLETO: las 6 fases terminadas.**

Obtenido por ingeniería inversa de la documentación de referencia
(`Probabilistic_Analysis_Overview`, `Probabilistic_Analysis`,
`Random_Variables`, `Statistical_Distributions_Overview`, las siete
páginas de distribuciones, `Material_Statistics`, `Load_Statistics`,
`Support_Statistics`, `Water_Table_Statistics`, `Piezo_Line_Statistics`,
`Seismic_Load_Statistics`, `Tension_Crack_Statistics`,
`Sensitivity_Analysis_Overview`, `Statistics_Settings`,
`Random_Numbers`).

---

## Qué hay que construir

### Distribuciones (7)
Normal, Uniform, Triangular, Beta, Exponential, Lognormal, Gamma.

Cada variable aleatoria se define con: **distribución**, **desviación
típica** (si aplica), y **valores mínimo y máximo RELATIVOS** — un matiz
importante de la referencia: no son valores absolutos sino distancias
respecto a la media, lo que trunca la distribución a
`[media − rel_min, media + rel_max]`.

### Muestreo (2)
- **Monte Carlo** — números aleatorios directos.
- **Latin Hypercube** — muestreo estratificado con selección aleatoria
  dentro de cada estrato. La referencia indica que 1000 muestras por LHS
  dan resultados comparables a 5000 por Monte Carlo.

### Variables aleatorias posibles
Propiedades de material (cohesión, ángulo de rozamiento, peso
específico, y los parámetros de los modelos no lineales), propiedades de
soporte (capacidad a tracción, etc.), magnitudes de carga, coeficiente
sísmico, posición de la freática y de las líneas piezométricas, grieta
de tracción, y parámetros hidráulicos. **Correlación c–φ** para
materiales Mohr-Coulomb.

### Tipos de análisis (2)
- **Global Minimum** — se hace primero el análisis determinista, y el
  probabilístico se repite N veces **sobre la superficie crítica**
  resultante. Independiente por cada método de análisis, ya que cada uno
  puede dar un mínimo global distinto.
- **Overall Slope** — se repite **toda la búsqueda** N veces, con una
  muestra distinta cada vez, dando varios mínimos globales.

### Resultados
Distribución de factores de seguridad, **probabilidad de fallo**
(PF = nº de casos con FS < 1 / N), **índice de fiabilidad**, **superficie
probabilística crítica** (la de máxima PF / mínimo índice de fiabilidad,
que **no** tiene por qué coincidir con la crítica determinista), y
**gráfico de convergencia** de muestras.

### Sensibilidad
Se varía **una sola variable cada vez** entre su mínimo y su máximo,
manteniendo las demás en su valor medio, y se representa el factor de
seguridad frente al valor del parámetro. Comparte la definición de
variables con el probabilístico pero solo usa mínimo y máximo.

---

## FASES

### ✅ Fase P0 — Núcleo estadístico *(COMPLETADA en v0.1.33)*
Las siete distribuciones con función de densidad, acumulada e inversa;
truncado por mínimo/máximo relativos; muestreadores Monte Carlo y Latin
Hypercube; semilla reproducible. **Validación contra momentos analíticos**
(la media y la desviación muestrales deben converger a los teóricos) y
contra la propiedad de estratificación del LHS.
*Sin dependencias nuevas: `scipy.stats` ya es dependencia núcleo.*

### ✅ Fase P1 — Variables aleatorias *(COMPLETADA en v0.1.34)*
Modelo de datos que identifica *qué parámetro de qué objeto* es
aleatorio (material/soporte/carga/sísmico/freática), aplicación de una
muestra a una **copia** del proyecto, y **correlación c–φ**. Serialización
en el `.ogr`.

### ✅ Fase P2 — Motor probabilístico (Global Minimum) *(COMPLETADA en v0.1.35)*
Análisis determinista previo, N repeticiones sobre la crítica,
estadísticos de salida (media, desviación, mínimo, máximo, PF, índice de
fiabilidad) y datos del gráfico de convergencia.

### ✅ Fase P3 — Overall Slope y superficie probabilística crítica *(COMPLETADA en v0.1.37)*
Repetición de la búsqueda completa, agrupación de mínimos globales y
determinación de la superficie de máxima probabilidad de fallo.

### ✅ Fase P4 — Análisis de sensibilidad *(COMPLETADA en v0.1.36)*
Barrido de una variable cada vez entre mínimo y máximo con las demás en
su media; curvas FoS-parámetro y ordenación por influencia.

### ✅ Fase P5 — Interfaz *(COMPLETADA en v0.1.38)*
Página *Statistics* en Project Settings, menú *Statistics* con los
diálogos de definición de variables (asistente de tres pasos para
materiales), y en Interpret: histograma de FoS, gráfico de convergencia,
diagramas de dispersión y curvas de sensibilidad.

**Orden:** P0 → P1 → P2 → P4 → P3 → P5. La sensibilidad (P4) se adelanta
a Overall Slope (P3) porque es más simple, comparte la definición de
variables y da resultados útiles antes.

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
