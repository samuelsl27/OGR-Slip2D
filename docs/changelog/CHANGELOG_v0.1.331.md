# OGR Slip2D v0.1.331

***Medir* mide, en las dos ventanas, y *Acotar longitud* deja una cota en *Interpretar* sin tocar el
modelo (D329, primera parte).** Octava versión de la tanda P8i.

## 0. Lo que se encontró

- **En *Interpretar*,** *Herramientas → Medir* y *Herramientas → Acotar longitud* eran `QAction` sin nada
  conectado (regla 7; D329, encontrada al planificar P8i).
- **En la ventana principal, *Medir*** pedía los puntos tecleados y guardaba una cota en el modelo, igual
  que *Acotar longitud*: dos entradas para lo mismo, y una medida que editaba el proyecto. Se encontró al
  planificar esta versión, con D332.
- **`ToolMode.MEASURE` existía,** con su cursor y su ayuda («Medir: pulsa dos puntos, Esc para
  terminar»), y el lienzo no lo leía en ningún sitio.

- **Un test viejo se puso rojo, y debía.**
  - `test_add_surface_three_points_v1168` fija desde v0.1.168 los modos de herramienta que nadie activa
    (D142), y `MEASURE` era uno de ellos, andamiaje puro. Su docstring lo avisa: «se pondrá roja el día
    que alguien cablee uno, que es cuando la ficha del banco tiene que cambiar».
  - Pasa a fijar lo nuevo: `MEASURE` ya se activa, el total de ayudas de modo sube de 34 a 35 (la de
    `PICK_DIMENSION`, con su castellano), y el único andamiaje que queda es `ADD_SURFACE_CR`.
  - D142, que sigue abierta, lo apunta. Quedan cuatro: `ADD_SURFACE_CR`, `SCALE_BOUNDARY`,
    `ROTATE_BOUNDARY` y `EXPAND_SHRINK`.
- **Un caso de test que no medía nada.** «Esc devuelve los clics a la selección» pasaba también en el árbol
  viejo, porque allí *Medir* no cambiaba el modo y Esc lo dejaba como estaba. Ahora comprueba también que
  *Medir* pone el modo antes de pulsar Esc.

## 1. Qué cambia

Por decisión de la propietaria:

- ***Medir*, en las dos ventanas,** son dos clics en el lienzo.
  - `ToolMode.MEASURE` entra en el flujo de dos clics del lienzo, con los modos que ya lo usaban (carga
    distribuida, rejilla, soportes), y emite `segment_picked`.
  - La ventana principal lo atiende en su despachador único (D308), e *Interpretar* en el suyo.
  - La distancia y sus dos componentes salen en la barra de estado (`labels.measurement_text`, un solo
    sitio para las dos ventanas). No se escribe nada en el modelo.
  - El modo sigue activo para el par siguiente, hasta Esc.
- ***Acotar longitud*, en *Interpretar*,** deja la cota en el lienzo de esa ventana.
  - Modo nuevo, `ToolMode.PICK_DIMENSION`, con su cursor y su ayuda en castellano.
  - La cota se dibuja con el dibujo de 0.1.330 (`annotation_items`), en una lista propia del lienzo,
    `overlay_annotations`, que se vuelve a dibujar con el modelo. No se guarda en el proyecto y se va con
    la ventana. La barra de estado lo dice.
- **En la ventana principal, *Acotar longitud*** sigue como estaba: guarda su cota en el modelo, que
  ahora se ve (D332).
- **Tres claves nuevas.**

## 2. Tests

`tests/test_measure_dimension_v1331.py` (nuevo). Los clics son clics de ratón reales sobre un lienzo
mostrado y sin ajuste de puntos, y la distancia esperada sale de los puntos de escena a los que van esos
píxeles:

- **ventana principal:** *Medir* pone el modo; dos clics dan la distancia y sus componentes; no cambian
  las anotaciones, ni la historia de deshacer, ni la marca de cambios sin guardar; el modo sigue;
- ***Interpretar*:**
  - *Medir* da la distancia y no deja nada en el lienzo;
  - *Acotar longitud* deja una cota con su valor dibujado, que sobrevive a un redibujado del modelo, y el
    proyecto no cambia;
  - Esc devuelve los clics a la selección de superficies.

**Con el código de 0.1.330 fallan los 4 casos.** El árbol viejo abría un diálogo modal de coordenadas
en *Medir*; el test lo sustituye para que falle y no se cuelgue. Se corrió sobre un `git archive` de
0.1.330, sin el buscador editable.

## 3. Verificación

- **El test de esta versión**, 4/4. Con el test de v0.1.168 puesto al día, 44/44.
- **Los vecinos**, 405/408 en 26 archivos: los modos y sus ayudas, el lienzo, *Interpretar*, el
  despachador de D308, las anotaciones, el castellano en pantalla y deshacer. Los tres fallos eran los de
  `test_add_surface_three_points_v1168`, que debían ponerse rojos (§0) y pasan con lo nuevo.
- **Suite entera:** 6222/6222, `EXIT=0`, 79 min.
- **Banco:**
  - `verificar_cierres.py` entero: 78 comprobaciones y 0 bajadas;
  - D329 sigue abierta, porque le quedan las capas de agua (0.1.332);
  - D142 apunta que `MEASURE` ya se activa;
  - prompts (34) y auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** es interfaz.

## 4. Pendiente

- **D329, segunda parte (0.1.332):** las capas de agua de *Interpretar*. D329 se cierra entonces.
- **D314** después.
- **A mano, en la cuarta prueba de la interfaz:** medir en las dos ventanas, y acotar en *Interpretar* y
  cerrarlo.
