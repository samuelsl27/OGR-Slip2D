# Plan de finalización de la interfaz

**Autor:** Samuel Sáez López — UPCT
**Fecha:** 6 de agosto de 2026
**Base:** `docs/AUDITORIA_INTERFAZ_v0.1.48.md`
**Estado:** ✅ I1 completa (v0.1.49) · ✅ I2 completa (v0.1.50) · ✅ M1 completa (v0.1.51) · ✅ M2 completa (v0.1.52) · ✅ I3 completa (v0.1.53) · ✅ M3 completa (v0.1.54) · ✅ M4 completa (v0.1.55) · ✅ M5 completa (v0.1.56) · ✅ M6 completa (v0.1.57). **PLAN DE INTERFAZ COMPLETO: las 9 fases terminadas.**

Cierra la distancia entre el prompt original y v0.1.48. El motor de
cálculo ya excede lo pedido; lo que falta es la capa de interacción.

---

## Bloque I — INTERPRET *(prioritario)*

El post-procesador es donde más se separa lo implementado de lo
especificado. El prompt lo describe con detalle en su sección
«INTERPRET», y de sus cuatro capas de renderizado y su barra de estado
falta casi todo.

### ✅ Fase I1 — Capa de resultados y contexto visual *(COMPLETADA en v0.1.49)*
- **Barra de color gráfica** (*Color Scale Legend*) sustituyendo la
  leyenda de texto actual: barra vertical que mapea color a valor.
- **Etiqueta de FoS anclada** a la superficie crítica, que se mueve con
  ella si cambia el mínimo.
- **Indicador de algoritmo activo** en la barra de herramientas.
- **Barra de estado** con los indicadores del prompt: DATA TIPS,
  SNAP / GRID / ORTHO / OSNAP y lectura de coordenadas.
- **Menú View** en Interpret, hoy inexistente.

### ✅ Fase I2 — Motor de contornos *(COMPLETADA en v0.1.50)*
- **Contour Options**: mínimo, máximo, intervalo, número de pasos, modo
  (relleno, relleno con líneas, líneas, desactivado) y paleta.
- **Legend Options**: formato numérico (decimal/científico), precisión,
  posición (flotante/anclada) y fondo con transparencia.
- Campos escalares seleccionables sobre la malla: presión intersticial,
  cabeza total, tensiones.

### ✅ Fase I3 — Completar los menús de Interpret *(COMPLETADA en v0.1.53)*
- **Data**: Graph SF with Time *(dependiente de transitorio)*, Support
  Force Analysis *(dependiente de soportes)*, Supplemental Contours,
  Back Analysis.
- **Query**: Add Query / Graph Query / Delete Query, Query Invalid
  Surfaces, Text during Query.
- **Groundwater**: Contour Options, Legend Options, Query, Define User
  Data, Iteration History, Convergence Plot.
- **Statistics**: Sensitivity Plot, Convergence Plot, Export Statistics
  Data, Show GM Surfaces, Pick GM Surfaces, Critical Probabilistic
  Surface.
- **Habilitación condicional**: las entradas dependientes de transitorio,
  soportes o estadística deben estar deshabilitadas si el proyecto no las
  tiene, como especifica el prompt.

---

## Bloque M — MODELADOR

### ✅ Fase M1 — Utilidades de precisión *(COMPLETADA en v0.1.51)*
- **Data Tips**: al pasar el cursor sobre materiales, soportes y cargas,
  mostrar sus propiedades. Está en el **párrafo de apertura del prompt** y
  no existe. Modos None / Maximum / Minimum.
- ~~**Snap / Ortho / OSnap**~~ — **CORRECCIÓN DE LA AUDITORÍA**: el motor
  ya existía (`ogr_gui/canvas/snap_engine.py`, 355 líneas, con vértice,
  línea, rejilla, orto y extensiones) conectado a la barra de estado. Solo
  faltaban el **diálogo** de configuración y las teclas **F3/F8/F9**,
  añadidos en v0.1.51.
- **View Limits…** con coordenadas mínima y máxima.
- **Custom Ruler Spacing** (Auto, 0.1…50).
- Zoom Slope y Reset View Options.

### ✅ Fase M2 — Project Settings completo *(COMPLETADA en v0.1.52)*
Faltan cinco de las nueve páginas descritas: **Transient**,
**Statistics**, **Random Numbers**, **Design Standard** y **Advanced**.
Coste bajo: los datos ya existen en el modelo, es sobre todo interfaz.

### ✅ Fase M3 — Menú Tools y capa de anotación *(COMPLETADA en v0.1.54)*
- Primitivas: línea, flecha, lápiz, polilínea, polígono, rectángulo,
  círculo.
- Tablas de propiedades de soportes e hidráulicas.
- Cotas X e Y, ejes, imagen de fondo con escalado.
- Gestión de objetos: copiar, formato, pegar formato, Z-order,
  mostrar/ocultar todo, borrar todo.
- **Separación explícita capa de anotación / capa física**, con
  *Convert Tool to Boundary* como único puente.

### ✅ Fase M4 — Búsqueda de superficies *(COMPLETADA en v0.1.55)*
- **Focus Search**: ventana, línea, tangente y punto.
- **Optimize Surfaces**.
- Add Surface por centro y radio.
- Submenú Slope Limits completo (mover, restablecer).

### ✅ Fase M5 — Menús menores *(COMPLETADA en v0.1.56)*
- File: Import Properties, Export Image, Print Scale / Page Setup /
  Print Preview, archivos recientes, Import/Export View State.
- Edit: submenú Picture Format (Bitmap / EMF).
- Loading: Modify Load.
- Support: Modify Support, Move Support, Ungroup Support Pattern.
- Help: About con metadatos desde fichero de configuración, Tutorials,
  Technical Support, Check for Updates.

### ✅ Fase M6 — MDI y utilidades avanzadas *(COMPLETADA en v0.1.57)*
- Registro dinámico de sesiones con marca de activa y asterisco de no
  guardado.
- Parameter Calculator.
- Design Standard con factores parciales (Eurocódigo 7 y otros).

---

## Orden

**I1 → I2 → M1 → M2 → I3 → M3 → M4 → M5 → M6**

Interpret primero por indicación expresa. Dentro del modelador, M1 antes
que el resto porque Data Tips y Snap se usan continuamente y están
pedidos de forma explícita en el prompt.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
