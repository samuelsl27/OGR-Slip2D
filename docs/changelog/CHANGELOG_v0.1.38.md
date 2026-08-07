# OGR Suite v0.1.38 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Fase P5: interfaz estadística.** Con esta versión el **módulo
> probabilístico y de sensibilidad queda completo**: las seis fases del
> plan terminadas y utilizable de principio a fin desde la interfaz
> gráfica.

---

## 🆕 Diálogo *Random Variables*

Catálogo de **todos** los parámetros que pueden aleatorizarse a la
izquierda, variables definidas en el centro, y estadística a la derecha:
distribución (las siete), desviación típica, **mínimo y máximo
relativos** con el rango real calculado en vivo, y correlación con otra
variable.

Detalles fieles a la referencia:

- La media es **de solo lectura**: es el valor determinista del modelo.
- Los límites se introducen como **distancias relativas** a la media, y
  el diálogo muestra el rango absoluto resultante para que no haya
  ambigüedad.
- La **desviación típica solo se habilita** en las distribuciones que la
  usan (Normal, Lognormal, Beta, Gamma).
- **Correlación** con cualquier otra variable definida — pensada para el
  par cohesión / ángulo de rozamiento, donde lo físicamente habitual es
  un coeficiente negativo.
- Botón **Plot** que grafica la función de densidad resultante con la
  media marcada, para ver el efecto de los parámetros antes de calcular.
- Al eliminar una variable se limpian las correlaciones que apuntaban a
  ella, en vez de dejarlas colgando.

## 🆕 Ventana de resultados estadísticos

- **Histograma** de factores de seguridad con el umbral de fallo y la
  media marcados, y los números de cabecera en la barra de estado:
  muestras, media, desviación, mínimo, máximo, **probabilidad de fallo**
  e **índice de fiabilidad** (normal y lognormal).
- **Gráfico de convergencia** con doble eje: media del factor de
  seguridad y probabilidad de fallo frente al número de muestras — la
  forma que propone la referencia para juzgar si se han usado bastantes.
- **Curvas de sensibilidad** con el eje x en **porcentaje de rango**, de
  modo que variables con unidades distintas comparten ejes, y el ranking
  de influencia en la barra de estado.
- **Datos de dispersión** (`scatter_data`) que emparejan cada valor
  muestreado con su factor de seguridad.

## 🔒 Disponibilidad del menú

Igual que el resto de la suite, las opciones se habilitan por
dependencias reales: *Random Variables* requiere haber activado un
análisis probabilístico o de sensibilidad en Project Settings, *Compute
Statistics* requiere además al menos una variable definida, y *Show
Statistics* requiere un resultado.

## 🔧 `build_search`: una sola fuente de verdad

El análisis Overall Slope necesita reconstruir **exactamente** la misma
búsqueda configurada una vez por muestra. En lugar de duplicar el
despacho de métodos y ajustes de búsqueda —unas cien líneas— se añadió
`_ComputeWorker.build_search(method_id)`, que **captura** el objeto que
construye el propio `run`. Así la corrida probabilística honra por
construcción los mismos ajustes que un *Compute* normal, y no hay dos
sitios que mantener sincronizados.

## ⚙️ Ajustes ampliados

`StatisticsSettings` incorpora el **tipo de análisis probabilístico**
(Global Minimum / Overall Slope), el **número de intervalos** de
sensibilidad (50 por defecto, como la referencia) y una **semilla**
opcional para corridas reproducibles. Todo serializado en el `.ogr`.

## ✔️ Validación de extremo a extremo

Caso de referencia con probabilístico y sensibilidad activados
simultáneamente, 40 muestras LHS:

| | |
|---|---|
| Catálogo de parámetros | 26 |
| Probabilidad de fallo | 0.850 |
| Índice de fiabilidad | −1.120 |
| Media FoS | 0.9119 |
| Variable más influyente | ángulo de rozamiento de Mat1 |
| Gráficos disponibles | 3, todos renderizados |
| Puntos de dispersión | 40 |

## 📊 Tests

**738 tests, 738 verdes** (+28 desde v0.1.37; suite 100 % desde v0.1.21).

Cobertura: disponibilidad del menú en los cuatro estados; catálogo
completo en el diálogo, alta y baja, alta duplicada ignorada, **rango
real derivado de los límites relativos**, desviación típica habilitada
solo donde se usa, correlación que ofrece las demás variables, guardado
al aceptar, **Cancel que no guarda**, y limpieza de correlaciones
colgantes; ejecución de Global Minimum, de Overall Slope, de sensibilidad
y de ambos a la vez; `build_search` devolviendo la búsqueda configurada;
**proyecto sin modificar tras la corrida**; renderizado de los tres
gráficos, números de cabecera del histograma, listado solo de los
gráficos disponibles, y emparejamiento correcto de los datos de
dispersión; y round-trip de los ajustes nuevos.

## 🏁 Módulo probabilístico completo

| Fase | Contenido | Versión |
|---|---|---|
| P0 | Núcleo estadístico | v0.1.33 |
| P1 | Variables aleatorias | v0.1.34 |
| P2 | Motor Global Minimum | v0.1.35 |
| P4 | Análisis de sensibilidad | v0.1.36 |
| P3 | Overall Slope | v0.1.37 |
| P5 | **Interfaz** | **v0.1.38** |

## ⏳ Siguiente

Con el agua y el probabilístico cerrados, los pendientes de la auditoría
que quedan son: **back analysis** de fuerza de soporte, **import DXF**,
cobertura de **i18n**, y la anomalía **A5** (Simulated Annealing con
Spencer no produce superficies válidas).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
