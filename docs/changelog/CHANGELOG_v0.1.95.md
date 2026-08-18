# OGR Slip2D v0.1.95 — asignar una superficie de agua a un material no hacía nada

| | antes | ahora |
|---|---|---|
| u tras marcar un material en *Assign Water Surface* | **0,000 kPa** | **196,200 kPa** |
| campos que escribe la asignación | 1 (`water_surface_id`) | 2 (+ `pore_pressure`) |
| el panel aparece al terminar de dibujar | no | **sí** |

Suite completa: 1972 → **1990** tests, todos en verde.

---

## 1 · El control que no hacía nada

`Assign Water Surface` existe desde v0.1.62. Escribía
`Material.water_surface_id` y nada más. Y `pore_pressure_at` sale por

```python
if ppt == PorePressureType.NONE:
    return 0.0
```

**antes** de mirar ese campo. Así que marcar un material en el diálogo
cambiaba el archivo del proyecto y no cambiaba ningún resultado.

Medido sobre la geometría de `Ej_2_Piezometric_Line`, punto (0, 10):

```
Material 1, water_surface_id = piezo         u = 0,000 kPa
Material 1, + pore_pressure = PIEZO_LINE     u = 196,200 kPa
```

Es la regla 7 —«ningún ajuste puede no hacer nada»— y es **el mismo fallo** que
tuvieron los coeficientes parciales de la norma de diseño entre v0.1.52 y
v0.1.57: configurables, guardados y nunca aplicados. Que se repita el patrón es
lo que merece anotarse: un campo que se guarda parece que funciona, porque
sobrevive a guardar y abrir.

Se descubrió al preparar el panel nuevo, no buscándolo: el panel iba a escribir
exactamente ese campo.

### El arreglo

`MainWindow.apply_water_surface_assignment` es ahora la única puerta, separada
del manejador del diálogo para poder probarla sin abrir un modal. Escribe
también `pore_pressure`, con el modelo que corresponda al **tipo** de la
superficie elegida (`WATER_TABLE` o `PIEZO_LINE`).

Al desmarcar restaura `NONE`, **pero sólo si el material estaba usando una
superficie de agua**. Uno con Ru, con presión constante o con campo de
elementos finitos se queda como está: su modelo de presión intersticial nunca
fue de este diálogo, y apropiárselo al desmarcar habría sido el mismo error al
revés.

## 2 · El panel, y cuándo aparece

La referencia abre *Assign Piezo Line* al terminar de dibujar la línea, y su
documentación explica por qué existe además del combo por material: el diálogo
de materiales obliga a hacerlo de uno en uno, «which can be quite slow, if your
model uses many materials». **Se mantienen los dos caminos**, como pedía el
enunciado y como hace la referencia, que llama al panel «simply a shortcut».

Ahora:

- se abre solo al terminar un nivel freático o una línea piezométrica, ya
  preseleccionado en la que se acaba de dibujar;
- enseña la **superficie de agua actual** de cada material, así que se puede
  leer como tabla de estado y no sólo rellenar como formulario;
- *Select All* / *Clear All*.

### Una diferencia deliberada con la referencia, dicha en voz alta

El panel de la referencia avisa de que «assignment for unchecked materials will
not be changed»: allí desmarcar es inerte y quitar una asignación se hace en
*Define Materials*.

Aquí las casillas **abren marcadas según el estado actual**, de modo que el
diálogo enseña lo que es verdad, y desmarcar un material que apunta a **esta**
superficie le quita la asignación. Los que apuntan a **otra** no se tocan
nunca — eso es lo que lo hace seguro, y estaba ya resuelto así en
`cleared_material_ids` desde v0.1.62.

La etiqueta del pie dice lo que hace OGR en vez de repetir la frase de la
referencia, que aquí sería **falsa**. Copiar el texto de un producto cuyo
comportamiento no se copia es la manera más barata de mentirle al usuario.

### Los modales y los tests

La apertura automática va detrás de `MainWindow.PROMPT_ASSIGN_ON_DRAW`, un
atributo de clase que los tests apagan. `QDialog.exec()` en código que un test
ejecuta bloquea indefinidamente sin pantalla, que es lo único que el proyecto
prohíbe de plano. **Ningún test de este archivo llama a `exec()`**: atacan la
lógica del diálogo directamente y el interruptor tiene su propio test en los
dos sentidos.

## 3 · Los tests

`tests/test_assign_water_surface_v195.py`, 18 casos.

El ancla **no** es un factor de seguridad capturado, sino la forma cerrada que
la referencia documenta:

```
u = gamma_w · Hu · h
```

con una línea piezométrica horizontal, así que `u = 9,81 · 10 = 98,1` es una
identidad y no una medición. El test dice lo que el número **tiene que ser**.

Y uno que existe para que el resto no pueda pasar por la razón equivocada:

- `test_writing_only_the_id_would_have_changed_nothing` reproduce el
  comportamiento anterior —escribir sólo el id— y **exige que u siga siendo
  cero**. Sin él, alguien podría volver a escribir un solo campo y ningún otro
  test de la suite se enteraría.

Más: que desmarcar devuelve el material a seco, que un material en Ru sobrevive
a que lo desmarquen, que un nivel freático escribe `WATER_TABLE` y no
`PIEZO_LINE`, y las cinco combinaciones del aviso automático.

## 4 · Lo que sigue abierto

Sin cambios respecto de v0.1.94, y se repite aquí porque son de agua:

- **Lowe-Karafiath, −10,9 %** con línea piezométrica. `PENDIENTES.md` §7.
  Sigue esperando **un dato**: el Lowe-Karafiath de la referencia sobre un
  modelo con agua embalsada.
- **Spencer −2,0 % y GLE −0,8 %**: la auditoría
  `spencer_gle_interslice_v179.md`, ahora con una medida que la hace visible.
- **La resistencia reportada truncada en σ' = 0** (`bishop.py:563`), **el peso
  de una dovela con un quiebro del terreno dentro**, y **una piezométrica que
  no cubre la dovela leída como talud seco**. Las tres medidas en el changelog
  de v0.1.94, ninguna corregida todavía.

---

## Archivos

| archivo | qué |
|---|---|
| `ogr_gui/main_window.py` | `apply_water_surface_assignment` escribe el modelo; aviso al dibujar; `PROMPT_ASSIGN_ON_DRAW` |
| `ogr_gui/dialogs/assign_water_surface_dialog.py` | tabla con la superficie actual, Select/Clear All, preselección, título |
| `ogr_gui/i18n/__init__.py` | cinco cadenas nuevas en español |
| `tests/test_assign_water_surface_v195.py` | 18 tests; el ancla es la forma cerrada de u |

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
