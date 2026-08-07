# OGR Suite v0.1.46 — Changelog

**Lanzamiento:** 6 de agosto de 2026
**Desarrollador:** Samuel Sáez López — Estudiante de Doctorado, UPCT
**Licencia:** AGPL-3.0-or-later

> **Fase D2 del import DXF: el diálogo de importación.** Con esto la
> importación ya es utilizable de principio a fin: leer, mapear capas,
> reparar, previsualizar e importar.

---

## 🆕 Puente al modelo (`ogr_core/dxf/importer.py`)

Une las fases D0 (lectura) y D1 (saneado) con el `Project`. Se mantiene
separado del diálogo para que toda la importación pueda ejercitarse — y
**automatizarse por script** — sin interfaz.

Dos decisiones que conviene dejar escritas:

- **La vista previa ejecuta el pipeline real.** `preview()` recorre
  exactamente el mismo camino de lectura y saneado que la importación, de
  modo que los conteos de vértices y la lista de problemas que ve el
  usuario **son los que se van a aplicar**. Una vista previa calculada con
  una aproximación más barata sería peor que no tenerla.
- **Nada se escribe si la lectura falló**, para que un archivo corrupto no
  pueda dejar el modelo a medio poblar. Los problemas *no resueltos*, en
  cambio, no bloquean: se importa y el usuario corrige, como acordamos.

`replace_model` elimina solo los contornos **de los tipos que el dibujo
define**, así que un contorno externo antiguo no sobrevive detrás del
nuevo pero una grieta de tracción que el DXF no toca permanece.

## 🆕 Diálogo (`ogr_gui/dialogs/dxf_import_dialog.py`)

- **Tabla con todas las capas** del dibujo: nombre, entidades por tipo,
  número de vértices y un **desplegable** con los ocho destinos posibles.
  Las capas reconocidas vienen preseleccionadas; las demás —incluida la
  ubicua `0`— quedan en *(ignorar)* y **en gris**, para que se vea que
  requieren decisión. Cualquier capa es mapeable, y el usuario puede
  además **anular la propuesta automática**.
- **Unidades** con la sugerencia del archivo aplicada pero etiquetada
  explícitamente como indicación que «a menudo falta o es incorrecta».
- **Densidad de discretización** de curvas.
- **Tolerancias relativas** en porcentaje de la diagonal, con el **rango
  recomendado impreso junto al campo** y explicación en el *tooltip* de
  por qué es relativa: el mismo valor sirve en milímetros y en metros.
- **Vista previa** que informa de vértices antes → después, extremos
  soldados y nodos insertados, cruces partidos, regiones encontradas y —lo
  decisivo— **si las áreas de las regiones suman el contorno externo**. Si
  no cuadran, lo dice con palabras y sugiere aumentar la tolerancia de
  soldadura.
- **Lista de problemas** con sus coordenadas guardadas, listas para que la
  Fase D3 centre la vista en ellos.
- Aceptar **recalcula** el pipeline, para que se aplique lo que hay en los
  controles en ese momento y no un resultado obsoleto de la última vista
  previa.

La acción `Import DXF...` deja de ser un *stub*.

## ✔️ Validación de extremo a extremo

Dibujo realista (contorno externo abierto, materiales que se quedan
cortos, capa `0` con geometría útil):

| | |
|---|---|
| Vértices | 13 → 20 |
| Extremos soldados | 5 (4 nodos insertados) |
| Cruces partidos | 1 |
| Regiones | **3** |
| Áreas | **coinciden exactamente** (4562.50) |
| Importado | 1 externo, 2 materiales, 1 freático |

## 🔴 Un límite de mi propio test de i18n, corregido

El test de cobertura de traducciones extraía las claves de `tr()` con una
expresión regular, y eso **no puede ser correcto**: la concatenación
implícita de Python significa que

```python
tr("Press Preview to check the "
   "geometry before importing.")
```

pasa **una** cadena unida en ejecución, mientras el regex solo veía el
primer fragmento y reportaba como no traducida una clave perfectamente
traducida. Ahora la extracción usa el **AST**, que da el valor
concatenado — lo que `tr` recibe de verdad.

## 📊 Tests

**887 tests, 887 verdes** (+28 desde v0.1.45; suite 100 % desde v0.1.21).

Cobertura (`tests/test_dxf_import_v146.py`): vista previa (repara y cierra
regiones, expone el invariante de área, cierra y reporta el contorno
abierto, **la capa `0` es mapeable**, el mapeo del usuario prevalece sobre
la propuesta, sin mapeo es error, archivo ausente reportado,
simplificación, resumen legible, unidades); aplicación al proyecto
(contornos creados, **la importación coincide con la vista previa**,
sustitución que respeta los tipos no definidos, sin sustitución,
**lectura fallida que no escribe nada**, proyecto marcado como
modificado, y **la geometría importada construye regiones**); y diálogo
(fila y desplegable por capa, preselección de las reconocidas con la `0`
sin decidir, los ocho tipos ofrecidos, sugerencia de unidad como
indicación, vista previa que informa del cierre y lista problemas **con
coordenadas**, casilla de simplificar que habilita su tolerancia, opciones
recogidas de la tabla, **aceptar que recalcula**, rango recomendado
visible, y acción de menú sin el stub).

## ⏳ Siguiente

**Fase D3 — informe de problemas y corrección asistida**: panel con los
problemas no resueltos, cada uno seleccionable para **centrar la vista**
en el punto afectado, de modo que la corrección manual sea rápida.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
