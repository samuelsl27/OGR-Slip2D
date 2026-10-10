# OGR Slip2D v0.1.299

**Un material nuevo recibe un color que ningún otro material del modelo usa, y
un cambio de nombre hecho por el agente llega al título de la ventana
(D297).** Segunda versión de la tanda P8d.

## 0. Lo que se encontró

- **El color.** En la segunda prueba de la interfaz (H15), «Arriba» y «Abajo»,
  creados con `model_define`, salieron los dos `#d4a373`, el valor por defecto
  de `Material.color`, y en el lienzo no se distinguían.
  - La ventana hacía lo mismo: *Definir materiales* → Añadir creaba «Material
    N» con ese color.
  - No había ninguna paleta de materiales en el código.
- **El nombre.** `project_new(name=…)` cambia el título de la ventana;
  `model_define {"name": …}` escribía `project.name`, pero `WindowHost.after_edit`
  no tocaba el título.
- **Decisión de la propietaria:** el `name` de `model_define` es el nombre del
  proyecto, y la ventana lo pone en su título como con `project_new`.

## 1. Qué cambia

- **`ogr_core/materials/palette.py`** (nuevo):
  - **`MATERIAL_PALETTE`:** doce tonos tierra y pastel, distintos entre sí y
    legibles bajo los contornos negros. El primero es el color de siempre, así
    que un modelo de un solo material se ve igual;
  - **`next_material_color(usados)`:** el primero que nadie usa. Con los doce
    usados, se repiten en orden.
- **Quién la usa:**
  - el API, al crear un material (`model_define` y `material_set`). Un `color`
    dado explícitamente sigue mandando;
  - la ventana, en *Definir materiales* → Añadir.
  - Un color elegido a mano, o leído de un archivo, no se toca nunca.
- **`WindowHost.after_edit`** refresca el título tras cada edición del agente.
  Usa la regla de `after_save`: el nombre del archivo, o el del proyecto si no
  hay archivo.

## 2. Tests

`tests/test_material_colours_v1299.py`, 8 casos:
- **la paleta:**
  - el primer color es el de siempre;
  - los colores en uso se saltan, también en mayúsculas;
  - con los doce usados, se repiten en orden;
  - no tiene colores repetidos;
- **`model_define`** con tres materiales da tres colores distintos, y
  `material_set` un cuarto;
- **un color explícito** se respeta;
- **la ventana:** Añadir da colores que la lista no usa;
- **tras una edición del agente,** el título lleva el nombre del proyecto.

Con el código de 0.1.298 el archivo no puede importarse.

## 3. Verificación

- **Suite entera:** 5948/5948, código de salida 0.
- **Tests del puente, del API y de render** (6 archivos, 54 casos): verdes.
- **Banco:** `d297()` en `verificar_cierres.py` → CUBIERTO POR TEST.
