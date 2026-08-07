---
name: gui-pyside6
description: Reglas de la interfaz PySide6 del proyecto. Úsalo al crear o modificar diálogos, acciones de menú, el lienzo o traducciones.
---

# Interfaz PySide6 en OGR Suite

## Lo que rompe los tests sin avisar

- **Diálogos modales**: `QMessageBox.information()` y `QDialog.exec()`
  bloquean **indefinidamente** en un entorno sin pantalla. Los gráficos
  informativos van **no modales** con `show()`, guardando la referencia
  para que Qt no los recoja. Si un método abre un modal, el test debe
  comprobar sus **guardas y datos**, no invocarlo.
- **`isVisible()` es falso** para todo hijo de una ventana que no se ha
  mostrado. Para comprobar visibilidad usa **`isHidden()`**.
- **`Qt.UserRole` vale 256**, no 32. Nunca escribas el literal.
- **Fugas de estado**: si un test cambia el idioma, debe restaurarlo.

## Al añadir una acción

1. Regístrala con `self._mk("clave", "Etiqueta", callback, icono)`.
2. **Añádela a un menú.** Hay un test que recorre la barra real. Doce
   acciones se publicaron invisibles por saltarse este paso.
3. Envuelve la etiqueta en `tr()` y añade su traducción española.
4. Si depende de algo que el proyecto puede no tener (transitorio,
   soportes, resultado estadístico), **deshabilítala con un tooltip que
   diga qué ejecutar primero**. Ocultarla impide descubrir la capacidad.

## Diálogos

- Los valores por defecto salen del modelo, no de literales.
- Las opciones que no aplican se **deshabilitan**, no se ocultan.
- Las tolerancias se expresan en las unidades que las hacen robustas
  —píxeles de pantalla o porcentaje del modelo— y **el diálogo lo dice**,
  para que nadie las "corrija" a unidades absolutas.
- Una vista previa vale más que una lista de nombres: muestra los colores
  reales, el conteo real, el tamaño de intervalo real.

## i18n

```python
from ogr_gui.i18n import tr
```

Las claves se extraen con **AST**, no con expresiones regulares: la
concatenación implícita de Python hace que `tr("una " "cadena")` sea una
sola clave, y un regex solo vería el primer fragmento.
