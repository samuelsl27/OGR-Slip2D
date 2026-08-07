# OGR Suite v0.1.54 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase M3: menú Tools y capa de anotación**, con la separación entre
> anotación y modelo físico impuesta por estructura, no por convención.

---

## 🆕 La capa de anotación

`ogr_core/annotations/` — trece tipos de primitiva (línea, flecha,
polilínea, polígono, rectángulo, círculo, texto, cuatro cotas, ejes e
imagen) que conviven con el modelo pero **no intervienen en el análisis**.

**La separación es el objetivo, y se impone estructuralmente**: las
anotaciones viven en `Project.annotations`, una lista que el solver nunca
lee. Un rectángulo dibujado para marcar una zona de interés **no puede**
confundirse con un contorno de material, y ningún resultado de análisis
puede cambiar porque alguien haya dibujado sobre el modelo. Hay tests que
lo fijan: cuatro anotaciones y cero contornos, y la serialización las
mantiene separadas.

**El único puente es `to_boundary_points`**, que usa *Convert Tool to
Boundary*: explícito, en un solo sentido e iniciado por el usuario. Nada
se convierte solo. Y hay un test que comprueba que **no existe puente
inverso**: la geometría nunca se convierte en anotación a espaldas del
usuario.

Las cotas, el texto, los ejes y las imágenes **no son convertibles**:
anotan el modelo, no lo definen, y convertirlas produciría un sinsentido.

Detalles del modelo: rectángulos y círculos se guardan por sus puntos
definitorios —que es lo que el usuario manipula— y se expanden en
`outline()`, de modo que todo lo que viene después ve una sola
representación. Las cotas devuelven un **número**, no una cadena
formateada, para que quien llame controle unidades y precisión. El ángulo
se mide en el **punto central**, que es el vértice que se elige en segundo
lugar, como en cualquier CAD.

## 🆕 Menú Tools estructurado

```
Tools
  Draw ▸ Line, Arrow, Polyline, Polygon, Rectangle, Circle, Add Text
  Dimensions ▸ Length, Angle, X, Y
  Add Axes · Add Image... · Measure
  Property Tables ▸ Materials, Supports, Hydraulic
  Convert Tool to Boundary...
  Annotations ▸ Manage..., Show All, Hide All, Delete All
```

De 5 entradas a 24.

## 🆕 Tablas de propiedades

Materiales, soportes e hidráulicas en una rejilla, **ordenables** y con
copia al portapapeles en texto tabulado.

**Son de solo lectura a propósito.** La edición vive en los diálogos
específicos, donde está la validación; una segunda vía de edición sería un
segundo sitio donde olvidarla. Lo que una tabla hace de verdad bien es
**comparar** — ver que un material tiene la mitad de cohesión que su
vecino, o que un soporte se quedó sin capacidad —, y para eso está.

Las columnas son la **unión de todos los parámetros de resistencia en
uso**, así que materiales con modelos distintos siguen alineándose en una
sola rejilla comparable. La anterior «tabla de materiales» era un mensaje
de marcador.

## 🆕 Gestor de anotaciones

Visibilidad, orden Z, duplicar (con desplazamiento, para que la copia no
quede escondida detrás del original), copiar estilo a otras y eliminar. El
borrado masivo **pregunta antes**, y aclara que el modelo físico no se ve
afectado.

## 🔴 Un fallo de mi propio test

`Qt.UserRole` vale **256**, no 32. Usé el literal numérico que sí funciona
en un `QTreeWidget` de otra parte del código y aquí devolvía `None`. Queda
anotado en el test, porque es el tipo de constante que se copia entre
widgets sin pensar.

## 📊 Tests

**1138 tests, 1138 verdes** (+46 desde v0.1.53; suite 100 % desde
v0.1.21).

Cobertura (`tests/test_annotations_m3_v154.py`): formas (rectángulo
expandido, perímetro de círculo frente al exacto, polígono que se cierra,
formas abiertas, bbox y traslación); cotas (longitud, proyecciones X e Y,
**ángulo en el punto central**, caso degenerado, no-cotas sin medida);
**aislamiento del modelo** (anotaciones que no son contornos,
serialización separada, proyecto sin anotaciones); puente de conversión
(tipos convertibles, cotas y texto que no lo son, rectángulo a contorno
cerrado, duplicados descartados, forma degenerada, **sin puente inverso**);
operaciones de capa (orden Z, ordenación para pintado, traer al frente,
alta y baja, visibilidad masiva, duplicado con nuevo id, copia de estilo
que no comparte objeto, vaciado, round-trip); menú Tools completo; tablas
(fila por material, **solo lectura**, ordenables, columnas unión, tablas
vacías que se explican, exportación tabulada); y gestor de anotaciones.

## ⏳ Siguiente

**Fase M4 — búsqueda de superficies**: Focus Search (ventana, línea,
tangente, punto), Optimize Surfaces, Add Surface por centro y radio, y el
submenú Slope Limits completo.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
