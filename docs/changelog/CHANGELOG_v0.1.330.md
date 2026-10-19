# OGR Slip2D v0.1.330

**Las anotaciones se dibujan (D332).** Séptima versión de la tanda P8i, intercalada por decisión de la
propietaria antes de D329a, que la reutiliza.

## 0. Lo que se encontró

Al planificar D329a (*Acotar longitud* en *Interpretar* tenía que dejar una cota dibujada) se buscó el
dibujo de cotas que reutilizar, y no había ninguno.

- **Las anotaciones se guardaban, pero ningún lienzo las dibujaba.**
  - Medido: el ejemplo, con tres anotaciones (una cota, un texto y una línea) y sin ellas, da los mismos
    352 elementos de escena.
  - En `ogr_gui`, solo `main_window.py` leía la capa de anotaciones, para guardarla, editarla, mostrarla
    u ocultarla y medirla.
  - Las anotaciones se guardan en el `.ogr`, se editan en *Gestionar anotaciones* y por un agente
    (`annotation_set`), y *Mostrar / Ocultar todas* no cambiaba nada que se viera (regla 7).
  - La exportación DXF tampoco las saca: su capa de anotaciones solo lleva las etiquetas de FS. No se
    toca en esta versión.
- **Los ejes** se creaban con un punto, en la ventana y en el API. La referencia los dibuja entre dos
  esquinas, con las coordenadas de una a otra.
- **El *Medir* de la ventana principal** pide los puntos tecleados y guarda una cota en el modelo, igual
  que *Acotar longitud*: dos entradas para lo mismo. Se arregla con D329a, en 0.1.331.
- **Una afirmación mía, corregida.** Al preguntar por los ejes dije que *Gestionar anotaciones* permite
  completar unos de un solo punto. No es así: el diálogo no edita puntos (los cuenta, y permite activar,
  ordenar, duplicar, copiar el estilo y borrar). Se completan con `annotation_set` (`points_xy`) o
  volviéndolos a añadir.

- **Al probarlo:**
  - **El test del tamaño en pantalla contaba de más.** Tomaba todo lo que no se escala y está por encima
    de z = 20, y el modelo ya tiene etiquetas de pantalla propias: la «W» del nivel freático está en z =
    21. Ahora cuenta solo la banda de las anotaciones (`Z_ANNOTATION` ± 0,5).
  - **Se ha mirado, no solo contado.** Una captura del lienzo del ejemplo con un tipo de cada salió bien:
    - la punta de la flecha sigue su dirección;
    - el ángulo de la coronación da 135,0°, que es el que forman sus brazos;
    - la línea de referencia de la cota X está a trazos;
    - la imagen está en su rectángulo.

    La etiqueta de una cota vertical caía encima de su línea, y ahora se pone a un lado cuando la línea es
    casi vertical en pantalla.

## 1. Qué cambia

- **`ogr_gui/canvas/annotation_items.py`** (nuevo) convierte cada anotación en elementos de escena, y el
  lienzo los añade sobre el modelo. Es el mismo en la ventana principal y en *Interpretar*.
  - **La geometría es la del modelo:** `Annotation.outline()` para las formas (un rectángulo por dos
    esquinas, un círculo por un centro y un punto) y `measured_value()` para lo que mide una cota.
  - **Lo que tiene tamaño en pantalla no se escala con el zoom** (la regla del proyecto para medidas de
    pantalla): el texto, las puntas de flecha, las marcas de una cota, el arco de un ángulo y las
    etiquetas de los ejes.
  - **Por tipo:**
    - línea, polilínea, polígono, rectángulo y círculo: su contorno, con relleno los cerrados si lo
      tienen;
    - flecha: la línea y su punta;
    - texto: su texto;
    - cota de longitud, X e Y: su línea, una marca en cada extremo, líneas de referencia a trazos y el
      valor (o su propio texto si lo tiene);
    - cota de ángulo: sus dos brazos, un arco en el vértice y los grados;
    - ejes: los dos ejes del rectángulo de sus esquinas, con marcas y coordenadas a pasos redondos
      (`nice_step` de una quinta parte del tramo). Unos guardados con un solo punto son una cruz sin
      coordenadas;
    - imagen: estirada sobre el rectángulo de sus dos esquinas, **debajo** del modelo. Si falta el
      archivo, un marco a trazos con su nombre.
  - El estilo de cada una (color, grosor, trazo, relleno y su opacidad, tamaño de letra), su visibilidad
    y su orden.
- **Los ejes, por decisión de la propietaria, entre dos esquinas:**
  - la ventana pide dos puntos;
  - el API exige dos (`_MIN_POINTS["axes"] = 2`);
  - la descripción de `points_xy` de la herramienta MCP lo dice.

## 2. Tests

`tests/test_annotations_drawn_v1330.py` (nuevo), sobre el ejemplo en una ventana mostrada:

- **los trece tipos:** cada uno añade algo a la escena, y la acción de la ventana que oculta la capa lo
  quita y la que la muestra lo devuelve;
- **lo que se dibuja es lo del modelo:**
  - una cota enseña su valor o su texto;
  - X e Y, sus valores;
  - un ángulo recto, «90.0°»;
  - los ejes, sus coordenadas a pasos redondos;
  - unos ejes de un punto, una cruz sin coordenadas;
  - una imagen cubre su rectángulo, debajo del modelo, y la que falta es un marco con su nombre;
- **en pantalla:** el texto mide lo mismo con el zoom ×4; control: el trazo de la flecha, en unidades
  de modelo, crece;
- *Interpretar* las dibuja también;
- los ejes con un solo punto los rechaza el API, y la ventana pide dos.

**Con el código de 0.1.329 fallan los 10 casos.** Se corrió sobre un `git archive` de 0.1.329, sin el
buscador editable.

## 3. Verificación

- **El test de esta versión**, 10/10 después de la corrección de §0. Con los tests del módulo de
  anotaciones, 56/56.
- **Los vecinos**, 564/564 en 32 archivos:
  - el lienzo, las anotaciones, el DXF, el servidor MCP y el API;
  - *Interpretar*, el redibujado, el castellano en pantalla, el ejemplo y los modos.
- **Suite entera:** 6218/6218, `EXIT=0`, 83 min.
- **Banco:**
  - `verificar_cierres.py` entero: 78 comprobaciones, D332 **CUBIERTO POR TEST** y 0 bajadas.
  - `d332` lo mide sobre el ejemplo: 352 elementos de escena sin anotaciones y 358 con tres;
  - D332, abierta en esta tanda, retirada y podada de P8;
  - instantánea `Evaluaciones/0.1.330`, prompts (34) y auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** es dibujo.

## 4. Pendiente

- **D329** (resto de P8i: *Medir* y *Acotar longitud*, y las capas de agua), y D314 después.
- **La exportación DXF de las anotaciones**, que no se ha tocado.
- **A mano, en la cuarta prueba de la interfaz:** añadir una anotación de cada tipo, con zoom, y
  ocultarlas y mostrarlas; una imagen detrás del modelo.
