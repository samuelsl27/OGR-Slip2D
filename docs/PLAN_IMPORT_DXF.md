# Plan de desarrollo: importación de DXF

**Autor:** Samuel Sáez López — UPCT
**Fecha:** 5 de agosto de 2026
**Estado:** ✅ D0 completa (v0.1.44) · ✅ D1 completa (v0.1.45) · ✅ D2 completa (v0.1.46) · ✅ D3 completa (v0.1.47). **IMPORTADOR DXF COMPLETO: las 4 fases terminadas.**

---

## Por qué esto es delicado

La construcción de geometría válida ya costó varias iteraciones en el
editor propio. El problema de fondo fue el **soldado de extremos**: al
dibujar contornos de material había regiones que no se detectaban, y se
resolvió forzando la inserción de nodo cuando un extremo cae en el
**interior de un segmento** (no solo sobre otro extremo), eliminando así
la dependencia del orden de dibujo.

Un DXF llega en peores condiciones que el editor:

- líneas que *parecen* tocarse pero acaban a 0.3 mm;
- polilíneas con cientos de vértices de una digitalización;
- contornos externos abiertos;
- cruces sin nodo compartido;
- arcos, círculos y splines que no son polilíneas;
- unidades desconocidas (mm, cm, m, pies);
- capas con nombres arbitrarios (`0`, `Capa1`, `TALUD`).

Cualquiera de ellos produce **regiones abiertas** y, por tanto, materiales
sin asignar y un modelo inservible. El import no puede ser un lector de
DXF: tiene que ser un **saneador de geometría**.

---

## Decisiones de diseño (cerradas)

| Cuestión | Decisión |
|---|---|
| Tolerancia de soldadura | **Relativa** al tamaño del modelo, con el porcentaje **editable por el usuario**; valor por defecto recomendado y rango sugerido en el diálogo |
| Simplificación | **Activada** por defecto con tolerancia relativa pequeña, y **vista previa con el conteo de vértices antes/después** antes de confirmar |
| Arcos, círculos y splines | **Se discretizan**, con densidad **elegible por el usuario** |
| Geometría irreparable | **Se importa igualmente** y el usuario corrige en el editor, con informe de problemas |
| Unidades | **Se pregunta**, con **metros por defecto** |

---

## Nombres de capa por defecto

Reconocimiento automático, insensible a mayúsculas y con alias, pero
**siempre reasignable a mano** en el diálogo:

| Capa por defecto | Alias reconocidos | Geometría |
|---|---|---|
| `OGR_EXTERNAL` | `EXTERNAL`, `EXTERIOR`, `CONTORNO` | Contorno externo |
| `OGR_MATERIAL` | `MATERIAL`, `MATERIALES`, `SUELO` | Contornos de material |
| `OGR_WATER_TABLE` | `WATER`, `FREATICO`, `NIVEL_FREATICO`, `WT` | Nivel freático |
| `OGR_PIEZO` | `PIEZO`, `PIEZOMETRICA` | Líneas piezométricas |
| `OGR_DRAWDOWN` | `DRAWDOWN`, `DESEMBALSE` | Línea de desembalse |
| `OGR_CRACK` | `CRACK`, `GRIETA`, `TENSION_CRACK` | Grieta de tracción |
| `OGR_SUPPORT` | `SUPPORT`, `SOPORTE`, `ANCLAJE`, `BULON` | Soportes |

El diálogo lista **todas** las capas del DXF con su número de entidades y
un desplegable por capa; las no reconocidas quedan en *(ignorar)* y el
usuario decide.

---

## Condiciones que debe cumplir cada geometría

Esto es lo que el saneador tiene que garantizar, y de donde salen los
algoritmos:

**Contorno externo**
- Cerrado. Si llega abierto, **se cierra** uniendo los extremos.
- Simple (sin autointersecciones).
- Orientación normalizada (antihorario).
- Un único contorno; si hay varios, se avisa y se toma el de mayor área.

**Contornos de material**
- Sus extremos deben **caer exactamente sobre** el contorno externo u
  otro contorno de material, insertando nodo si caen en el interior de un
  segmento — la lección aprendida del editor.
- Se prolongan hasta el contorno externo si se quedan cortos por debajo
  de la tolerancia.
- Las intersecciones mutuas deben tener **nodo compartido**.

**Superficies de agua** (freático, piezométricas, desembalse)
- Abiertas, monótonas en x, y que abarquen el ancho del modelo (se
  prolongan horizontalmente si no llegan).

**Soportes**
- Segmentos de dos puntos; los de más se parten o se toma el trazado.

---

## FASES

### ✅ Fase D0 — Lector y catálogo de capas *(COMPLETADA en v0.1.44)*
Lectura con `ezdxf` (ya es dependencia). Extracción de `LINE`,
`LWPOLYLINE`, `POLYLINE`, `ARC`, `CIRCLE`, `SPLINE`. Discretización de
curvas con densidad configurable. Conversión de unidades (se pregunta,
metros por defecto; se lee `$INSUNITS` solo como **sugerencia**).
Catálogo: capas presentes, tipo y número de entidades, y detección
automática por nombre y alias.
*Sin tocar el modelo: es solo lectura e inventario.*

### ✅ Fase D1 — Saneador de geometría *(COMPLETADA en v0.1.45)*
El núcleo, y donde está el riesgo:
1. **Fusión de vértices coincidentes** dentro de la tolerancia relativa.
2. **Soldado de extremos a segmentos**: proyección de un extremo sobre el
   interior de un segmento cercano, con **inserción de nodo en el
   segmento** — exactamente el punto que costó resolver en el editor.
3. **Detección de intersecciones** entre todas las polilíneas y partición
   en los cruces, para que no queden cruces sin nodo.
4. **Cierre del contorno externo** si viene abierto.
5. **Prolongación** de contornos de material y superficies de agua que se
   quedan cortos.
6. **Simplificación Douglas-Peucker** con tolerancia relativa, contando
   vértices antes y después.
*Validación: reconstruir regiones con `build_regions` y comprobar que el
área de las regiones iguala el área del contorno externo — el mismo
invariante que usamos para validar la malla FE, que detecta huecos y
solapes.*

### ✅ Fase D2 — Diálogo de importación *(COMPLETADA en v0.1.46)*
Tabla de capas con desplegable de tipo, unidades, tolerancia de soldadura
(con rango recomendado), tolerancia de simplificación, densidad de
discretización de curvas, y **vista previa**: conteo de vértices
antes/después, regiones detectadas, y lista de problemas encontrados.
Botón de importar habilitado siempre (se importa aunque haya problemas).

### ✅ Fase D3 — Informe de problemas y corrección asistida *(COMPLETADA en v0.1.47)*
Panel con los problemas que el saneador no pudo resolver (regiones
abiertas, contornos que no llegan, entidades ignoradas), cada uno
**seleccionable para centrar la vista** en el punto afectado, de modo que
la corrección manual sea rápida.

**Orden:** D0 → D1 → D2 → D3.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
