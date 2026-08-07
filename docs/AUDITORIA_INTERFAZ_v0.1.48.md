# Auditoría de interfaz — prompt original vs. estado actual

**Autor:** Samuel Sáez López — UPCT
**Fecha:** 6 de agosto de 2026
**Versión auditada:** v0.1.48 (938 tests verdes)
**Fuentes de contraste:** prompt inicial `2026_04_19_Pront_v000.txt` (2150
líneas) y las 194 páginas de documentación de la referencia en
`/mnt/project/`.

---

## Resumen

| | |
|---|---|
| Acciones registradas | 88 |
| Iconos en la barra de herramientas | 52 |
| Entradas de menú (ventana principal) | 92 en 14 menús |
| Entradas de menú (Interpret) | 31 en 9 menús |
| Diálogos implementados | 25 |
| Modelos de resistencia | **18** (el prompt pedía 14) |
| Tipos de soporte | 7 |
| Métodos LEM | 7 |
| Algoritmos de búsqueda | 6 |

El **núcleo de cálculo está por encima de lo pedido**. Lo que falta se
concentra en **utilidades de dibujo, anotación y configuración fina** — la
capa que no afecta a los resultados pero sí a la comodidad de uso.

---

## ✅ Completo y conforme al prompt

**Menús presentes con su contenido:** File, Edit, View, Analysis,
Boundaries, Loading, Support, Surfaces, Properties, Tools, Window, Help,
más **Groundwater** y **Statistics** (que el prompt no listaba como menús
propios pero cuya funcionalidad sí describía).

**Motor de cálculo:** siete métodos LEM validados contra caso de
referencia (error < 0.7 %), seis algoritmos de búsqueda, superficies
circulares y no circulares, superficies compuestas, filtros de superficie,
grieta de tracción, cargas distribuidas y lineales, sísmico pseudoestático.

**Materiales:** 18 modelos de resistencia, por encima de los 14 del
prompt. Están todos los de las categorías A–D, incluidos los anisótropos,
la función discreta y la generalizada.

**Soportes:** los 7 tipos del prompt (User Defined, Soil Nail, Micro-Pile,
Grouted Tieback con y sin fricción, GeoTextile, End Anchored), con patrón
paramétrico y **retroanálisis de fuerza**.

**Agua subterránea:** malla FE, permanente saturado, no saturado con seis
funciones de permeabilidad, cara de rezume, transitorio por etapas con
FoS por etapa, y acople con la estabilidad. **Esto excede el prompt**, que
solo pedía «análisis del flujo mediante elementos finitos».

**Probabilístico y sensibilidad:** siete distribuciones, Monte Carlo y
Latin Hypercube, Global Minimum y Overall Slope, probabilidad de fallo,
índice de fiabilidad, superficie probabilística crítica, convergencia y
barridos de sensibilidad. **También excede el prompt.**

**Interpret:** ventana separada con menús Data, Query, Groundwater,
Statistics, Tools y Window. Incluye cosas que el prompt pedía —Global
Minimum / Minimum Surfaces / All Surfaces, Filter Surfaces, Graph SF Along
Slope, Export Raw Data, Show Slices, Query Slice Data, Show Values Along
Surface— **más** el diagrama de sólido libre de dovela y la línea de
empuje, que no estaban pedidos.

**DXF:** importación con mapeo de capas, saneado de geometría y informe de
problemas navegable; exportación con contrato de capas y viaje de ida y
vuelta verificado. El prompt pedía el importador con «limpiador de
superficie»; está, y con más alcance.

**Otros:** i18n ES/EN con 482 claves, formato `.ogr` JSON, informes PDF,
CLI, licencia AGPL con CLA, CI en GitHub Actions.

---

## ⚠️ Parcial

| Elemento | Estado | Falta |
|---|---|---|
| **Project Settings** | 4 páginas (General, Methods, Groundwater, Project Summary) | Páginas **Transient**, **Statistics**, **Random Numbers**, **Design Standard**, **Advanced**. Los ajustes existen en el modelo de datos y son accesibles desde otros diálogos, pero no desde el árbol de Project Settings que describe el prompt |
| **Menú Tools** | 5 entradas (texto, medida, cota longitud, cota ángulo, tabla de materiales) | Las primitivas de dibujo (línea, flecha, lápiz, polilínea, polígono, rectángulo, círculo), tablas de soportes e hidráulica, cotas X/Y, ejes, imagen, y la gestión de objetos (copiar, formato, Z-order, mostrar/ocultar todo) |
| **Menú View** | Zoom, Grid, Ruler, Grayscale, Display Options | **View Limits…**, **Snap…** (F3/F8/F9), **Data Tips**, **Custom Ruler Spacing**, Reset View Options, Zoom Slope |
| **Menú Surfaces** | Surface Options, Auto Grid, Add Grid, Add Surface, Define Limits | Submenú **Focus Search** (window/line/tangent/point), submenú **Slope Limits** completo (mover, restablecer), **Optimize Surfaces**, Add Surface por centro-radio |
| **Menú File** | 11 entradas | **Import Properties**, Print Scale, Page Setup, Print Preview, Export Image, Import/Export View State, Send by E-Mail, Recent Files |
| **Menú Window** | 5 entradas | Es una lista estática: falta el **registro dinámico de sesiones** con marca de activa y asterisco de no guardado (arquitectura MDI real) |
| **Menú Help** | 2 entradas | Tutorials, Technical Support, Product Updates, y el diálogo **About** con metadatos (versión, fecha de compilación, licencia, contacto) desde fichero de configuración |
| **Menú Edit** | Undo, Redo, Copy Image | Submenú **Picture Format** (Bitmap / Enhanced Metafile) |
| **Loading** | Añadir y borrar | **Modify Load…** |
| **Support** | 5 entradas | **Modify Support**, **Move Support**, **Ungroup Support Pattern** |

---

## ❌ No implementado

Por orden de impacto en el uso diario:

1. **Snap / Ortho / OSnap** (F9/F8/F3) con barra de estado interactiva.
   Es lo que más se echa en falta al dibujar geometría con precisión, y
   el prompt lo detalla con sincronización bidireccional barra-diálogo.
2. **Data Tips** — al pasar el cursor sobre materiales, soportes y cargas
   deben salir sus propiedades. **El prompt lo pide explícitamente** en su
   párrafo de apertura, y no está.
3. **Primitivas de dibujo y anotación** del menú Tools, con la capa de
   anotación separada de la física y el comando *Convert Tool to
   Boundary* como único puente entre ambas.
4. **Focus Search** (ventana, línea, tangente, punto) para acotar la
   búsqueda de superficies.
5. **Optimize Surfaces** — refinamiento de la superficie crítica
   encontrada.
6. **Parameter Calculator** e **Import Properties** desde otro proyecto.
7. **Design Standard** (Eurocódigo 7 y otros) con factores parciales.
8. **Random Numbers** — control de semilla y generador (parcialmente: la
   semilla existe en los ajustes de estadística, pero sin página propia
   ni selección de generador).
9. **Print Preview / Page Setup / Print Scale** y **Export Image**.
10. **MDI real** con múltiples proyectos simultáneos.
11. **Scale Image** e importación de imagen de fondo.

---

## 🔄 Cambios deliberados respecto al prompt — **no revertir**

Estos se apartan del prompt por decisión tomada durante el desarrollo, y
se documentan para que no se «corrijan» por error:

1. **Licencia AGPL-3.0-or-later**, no la GPL inicial, más `CLA.md` para
   conservar la opción de servicio alojado comercial *(decisión tuya,
   v0.1.43)*.
2. **`.ogr` es JSON puro**, sin la parte HDF5 que preveía el prompt. Los
   resultados se recalculan en lugar de almacenarse: más simple, sin
   dependencia binaria, y evita que resultados obsoletos sobrevivan a un
   cambio del modelo.
3. **`scipy.spatial.Delaunay` en lugar de la librería `triangle`**, cuya
   licencia prohíbe el uso comercial y es incompatible con AGPL.
4. **Tolerancias del importador DXF relativas** a la diagonal del modelo,
   no absolutas *(decisión tuya)*.
5. **El m-alpha check queda desactivado por defecto**, con justificación
   numérica: el círculo de referencia validado también lo incumple, así
   que activarlo rechazaría la superficie correcta.
6. **Métodos LEM: siete implementados**, sin Corps of Engineers #1 y #2
   que listaba el prompt. Se priorizaron los de uso general; los dos de
   Corps son variantes de la función interdovela y encajan en el motor
   GLE existente.
7. **La ventana Interpret añade** diagrama de sólido libre de dovela y
   línea de empuje, no pedidos.

---

## Recomendación de prioridades

Si el criterio es «lo que más mejora el uso por esfuerzo invertido»:

**Primero — utilidades de dibujo (alto impacto, coste medio)**
Snap/Ortho/OSnap con barra de estado, Data Tips, y View Limits. Son las
tres cosas que se usan continuamente al construir un modelo, y las dos
primeras están pedidas explícitamente en el prompt.

**Segundo — completar Project Settings**
Las cinco páginas que faltan. Coste bajo: los datos ya existen en el
modelo, es sobre todo interfaz, y cierra un elemento central del prompt.

**Tercero — menú Tools completo**
Primitivas, tablas de soporte e hidráulica, cotas X/Y, ejes, y la
separación explícita capa de anotación / capa física.

**Cuarto — Focus Search y Optimize Surfaces**
Afectan a la calidad del resultado, no solo a la comodidad.

**Quinto — impresión, exportación de imagen y MDI**
Necesarios para uso profesional, pero no bloquean el trabajo técnico.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
