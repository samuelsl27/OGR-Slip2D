# OGR Slip2D v0.1.86 — el clic del lienzo llevaba setenta y cuatro versiones sin existir

El informe del Ejemplo 2 pedía dos cosas distintas del Interpret: poder
**fijar** una superficie con un clic para comparar varios FS a la vez, y
que el panel de Query Slice Data se abriera. Resultaron ser **el mismo
bug**, y de una línea.

**Ningún cálculo cambia.**

---

## 1 · La línea

`ogr_gui/canvas/canvas_view.py`:

```python
if (event.button() == Qt.LeftButton
        and mode == ToolMode.SELECT
        and not event.isAccepted()):       # <-- nunca se cumple
    self.scene_clicked.emit(scene_pt.x(), scene_pt.y())
```

Un `QMouseEvent` de **pulsación llega ya aceptado**. Comprobado en
ejecución:

```
ev.isAccepted() = True
emisiones de scene_clicked = []
```

Así que la condición era falsa siempre y **la señal no se emitió jamás**,
en ninguna compilación, desde v0.1.12.

`scene_clicked` es lo que dispara **las dos** cosas que el informe pide:

- el clic que convierte la superficie previsualizada en una Query
  (`_on_canvas_click_default` → `_commit_query`), y
- el clic que elige una dovela para el panel de datos
  (`_on_canvas_click_for_query` → `slice_dock.show_slice`).

Las dos parecían implementadas. Ninguna podía ejecutarse.

### Por qué el guard sobraba entero

No se ha sustituido por otro más listo: se ha **quitado**. Llegar a esa
línea ya significa que nadie consumió el evento — todas las ramas
anteriores terminan en `event.accept(); return`. **La posición en el
método era el guard**, y no quedaba nada que comprobar.

### Por qué el test no lo vio

Porque **llamaba al slot directamente**. `w._on_canvas_click_default(x, y)`
demuestra que el manejador funciona; no demuestra que alguien lo llame
nunca. Es la diferencia entre probar la pieza y probar que está enchufada,
y aquí costó setenta y cuatro versiones.

Todos los casos nuevos despachan un `QMouseEvent` real a través de
`CanvasView.mousePressEvent`. Uno de ellos afirma, además, que un evento de
pulsación llega aceptado, para que la premisa del bug quede escrita en la
suite y no en un changelog.

## 2 · Una Query se quedaba sin su número

`_commit_query` llamaba a `_clear_query_label()`, así que **el factor de
seguridad desaparecía de la pantalla en el instante exacto en que la
superficie pasaba a ser una Query**. Aunque el clic hubiera funcionado, lo
que el informe pide —«ver a la vez los FS de distintas superficies»— no se
podía hacer.

Ahora cada Query conserva su lectura, anclada al **centro de giro**, que es
donde convergen las líneas radiales y donde la pone la referencia. En rojo
si la Query está sobre el mínimo global, en negro si no, para que dos
superficies encimadas no parezcan la misma.

Las etiquetas se redibujan desde `_refresh_canvas_with_highlights`, que es
el único sitio que dibuja el resultado. Añadirlas en cualquier otro lado
las habría dejado sobrevivir a un cambio de modo de visualización o
apiladas tras varios redibujados; las dos cosas tienen su caso.

---

## Verificación

`tests/test_interpret_pinned_queries_v186.py`, 12 casos:

- `scene_clicked` se emite con un clic izquierdo **real** — el bug, en una
  afirmación;
- un evento de pulsación llega aceptado — la premisa, por escrito;
- un clic crea la Query y sale del modo de selección, como documenta la
  referencia;
- **dos superficies se pueden tener fijadas a la vez**, que es lo pedido;
- la misma superficie dos veces sigue siendo una sola Query;
- la lectura del FS sigue en pantalla tras fijar, tras un redibujado, y
  tras cambiar el modo de visualización;
- cuatro redibujados seguidos no apilan cuatro etiquetas.

Suite completa, sin argumentos.

---

## Lo que queda del punto 4 del informe

El panel *Query Slice Data* ya puede recibir clics con este arreglo, pero
lo que la referencia describe —resaltar la dovela elegida, dibujar las
flechas de fuerzas sobre ella, y las dos columnas que faltan (cohesión y
ángulo de rozamiento en la base)— es v0.1.87. Las ~22 etiquetas del panel
siguen además sin pasar por `tr()`, que es regla 2.
