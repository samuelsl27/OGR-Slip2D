# OGR Suite v0.1.41 — Changelog

**Lanzamiento:** 2 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** GPL-3.0

> **Cobertura de internacionalización.** La auditoría la marcaba como
> «parcial»; al medirla resultó que el problema no eran traducciones
> ausentes, sino **cadenas que nunca llegaban a la capa de traducción**.

---

## 🔍 El diagnóstico

| | Antes | Ahora |
|---|---|---|
| Claves traducidas al español | 111 | **422** |
| Cadenas envueltas en `tr()` | 62 (en 8 de ~30 archivos) | **335** (en 25 archivos) |
| Cadenas visibles **sin envolver** | **380** | 207 |
| Claves envueltas sin traducción | 9 | **0** |

El dato revelador es el de la tercera fila: había **380 textos de interfaz
que no consultaban el diccionario en absoluto**. Aunque el usuario
cambiase a español, esos 380 seguían en inglés — no por falta de
traducción, sino porque nunca preguntaban. Los peores archivos eran los
diálogos: `grid_dialogs` (66), `boundary_dialogs` (40),
`project_settings_dialog` (32).

## 🔧 Qué se hizo

**273 cadenas envueltas en `tr()`** en 17 archivos, mediante un pase
automático sobre los constructores y métodos que muestran texto
(`setWindowTitle`, `QLabel`, `QPushButton`, `QCheckBox`, `QGroupBox`,
`addRow`, `setText`, `setToolTip`), insertando el import donde faltaba.

Dos precauciones que resultaron necesarias:

- **Inserción del import mediante AST**, no por búsqueda de líneas: el
  primer intento lo colocó dentro de bloques `import (...)` multilínea y
  rompió 17 archivos.
- **Detección de concatenación implícita de literales**: en
  `QLabel("una parte" "y otra")`, envolver solo la primera produce un
  error de sintaxis. Un *lookahead* deja intactos esos casos, que se
  traducirán a mano más adelante.

Tras ambas correcciones: **0 errores de sintaxis**.

**317 claves nuevas traducidas a mano.** Un primer intento de traducción
automática por sustitución de glosario produjo español roto en las frases
(«Añadir a Búsqueda por bloques object»), así que se descartó: el
diccionario está **curado término a término**, con la terminología
geotécnica estándar en castellano.

| Inglés | Español |
|---|---|
| Water Table | Nivel freático |
| Tension Crack | Grieta de tracción |
| Number of slices: | Número de dovelas: |
| Seepage face | Cara de rezume |
| Standard deviation: | Desviación típica: |
| Back Analysis of Support Force | Retroanálisis de la fuerza de soporte |
| Air Entry Value | Valor de entrada de aire |

## 🔒 Lo que impide que vuelva a degradarse

El valor duradero de esta versión no son las traducciones sino los
**tests de cobertura**, que convierten en fallo lo que antes se degradaba
en silencio:

- **Toda clave envuelta en `tr()` debe tener traducción al español** — la
  comprobación que le faltaba al proyecto y que habría detectado el
  problema desde el principio.
- **Presupuesto de cadenas sin envolver** (207 hoy): puede bajarse, nunca
  subirse. Un diálogo nuevo con texto sin traducir hace fallar la suite.
- Ninguna traducción puede quedar **idéntica al inglés** (señal de
  entrada olvidada), salvo una lista corta de casos legítimos (símbolos,
  unidades, nombres propios).
- La terminología geotécnica clave se verifica explícitamente, porque en
  un programa técnico importa más que la traducción sea *correcta* que
  literal.

## 📊 Tests

**786 tests, 786 verdes** (+13 desde v0.1.40; suite 100 % desde v0.1.21).

Cobertura nueva (`tests/test_i18n_coverage_v141.py`): completitud del
diccionario, tamaño mínimo, ausencia de traducciones perezosas, inglés
como referencia, clave desconocida devuelta tal cual, presupuesto de
cadenas sin envolver, número mínimo de cadenas envueltas, los diálogos
que la auditoría señalaba como peores, cambio efectivo de idioma,
idiomas disponibles, idioma actual, terminología geotécnica y un diálogo
real mostrando su título traducido.

## ⏳ Siguiente

**Import DXF**, la última pendiente de la auditoría, con plan propio:
simplificación de geometría, detección de intersecciones, autocorrección
y —lo más delicado— el mapeo de capas del DXF a entidades del modelo
(contorno externo, materiales, líneas de agua, soportes).

---

© 2026 Samuel Sáez López — UPCT — GPL-3.0
