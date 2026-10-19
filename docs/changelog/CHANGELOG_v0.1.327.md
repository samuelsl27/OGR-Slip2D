# OGR Slip2D v0.1.327

**El lienzo: lo que toma el puntero, lo que se vuelve a dibujar, el resultado del agente y una ayuda de
datos que no se veía (D322, D323, D330, D331).** Cuarta versión de la tanda P8i.

## 0. Lo que se encontró

- **D322, la ayuda de una región.**
  - Dentro del talud, la ayuda emergente era siempre la del contorno exterior y nunca la de la región, y
    un clic dentro seleccionaba el contorno exterior.
  - `BoundaryItem` es un `QGraphicsPathItem` de camino cerrado. Para Qt, la forma de un camino cerrado
    es todo su interior, tenga relleno o no, y el contorno está por encima de las regiones.
  - **`MaterialRegionItem`** (una región sombreada) no lo crea nadie en todo el historial del
    repositorio, que empieza en v0.1.59: solo está su definición. Las regiones las dibuja
    `_region_to_item`.
- **D323, deshacer y volver a dibujar.**
  - Tras calcular, mover el pie y deshacer, el panel volvía a dar el resultado por vigente (D304), pero el
    lienzo no dibujaba sus superficies.
  - Cada evento del proyecto vuelve a dibujar la escena entera, resultados incluidos, y solo un cálculo
    nuevo los ponía otra vez.
  - Por lo mismo, *Opciones de visualización* y las anotaciones, que dejan el resultado vigente, también
    borraban las superficies.
  - **El marcador de forzado** (`_last_snap`) solo se borraba al terminar de dibujar un contorno. Se
    quedaba donde se soltó un vértice, después de salir del modo, e incluso tras *Archivo → Nuevo*.
- **D330, el resultado del agente.**
  - `agent_bridge.show_analysis` enseñaba el resultado en la ventana sin recordar de qué modelo era.
  - Una edición posterior no lo marcaba nunca como de un modelo anterior: `_check_results_stale` salía
    sin hacer nada, o comparaba con el cálculo anterior de la ventana.

- **D331, encontrada al medir D322: la ayuda de datos no se veía nunca dentro del modelo.**
  - La ventana calcula la ayuda del punto (`data_tips.tip_at`, en «máximo» por defecto: «Silty clay
    (region 1) / strength: Mohr-Coulomb / cohesion: 10…») y la pone como ayuda del propio lienzo.
  - Qt enseña primero la ayuda propia del elemento bajo el puntero, y la del lienzo solo donde no hay
    ninguno.
  - Medido enviando la petición de ayuda al lienzo: dentro del talud salía la del contorno exterior en
    0.1.326 y, con D322 corregido, la de la región («Región / Material / Área»), **la misma con la ayuda
    de datos encendida o apagada**.
  - Las regiones, las cargas y los soportes cubren el modelo, así que el ajuste no cambiaba nada de lo
    que se ve: un caso de la regla 7. Se reportó antes de tocarlo y se abrió D331.
- **Un test mío que no medía lo que decía.**
  - El test de D323 movía el pie con la edición de `test_results_stale_v1297`, que cambia los vértices
    en su sitio sin avisar al proyecto.
  - Sin ese aviso el lienzo no se vuelve a dibujar, así que el control «tras mover no hay superficies»
    fallaba sobre el código ya corregido.
  - Una edición real avisa, y es ese aviso lo que vuelve a dibujar el lienzo. El test lo envía ahora.

## 1. Qué cambia

- **D322:**
  - la forma de un contorno es su trazo, ensanchado `BoundaryItem.PICK_PX = 4` píxeles de pantalla
    convertidos a unidades de modelo (la regla del proyecto para tolerancias de pantalla);
  - el lienzo actualiza esa tolerancia en cada cambio de escala. Todos pasan por los cuatro métodos de la
    vista (`setTransform`, `scale`, `fitInView`, `resetTransform`): `fitInView` escala por dentro de C++
    y no pasa por `scale`;
  - el rectángulo envolvente cambia con la tolerancia y avisa a Qt con `prepareGeometryChange`, para que
    el índice de la escena no se quede con el viejo;
  - el punto de la búsqueda por bloques, que se dibuja en unidades de pantalla, conserva su forma;
  - `MaterialRegionItem` se quita.
- **D323:**
  - el lienzo recuerda el último resultado que dibujó y con qué opciones, y `refresh_scene` lo vuelve a
    dibujar si su dueño dice que sigue vigente (`result_is_current`);
  - la ventana principal se lo dice con la huella de D304 (`_results_are_current`, `model_hash`). Solo
    se calcula cuando hay un resultado que volver a dibujar.
    - Medido en el ejemplo, en el mismo proceso: la huella cuesta 0,3–0,6 ms, frente a 5–8 ms del
      redibujado del modelo y 38–56 ms con el resultado.
    - Lo que cuesta es volver a dibujar las superficies, que es lo que se pedía;
  - el lienzo de *Interpretar* no lleva ese predicado y sigue dibujando lo suyo como antes;
  - el marcador de forzado se borra al salir del modo, al soltar el arrastre de un vértice y al cambiar
    de proyecto.
- **D330:** `show_analysis` llama a `_remember_results_model`, y sin resultado deja la huella vacía.
- **D331, por decisión de la propietaria: gana la ayuda de datos.**
  - El lienzo atiende él mismo la petición de ayuda (`viewportEvent`): si hay ayuda de datos, la enseña.
    Apagada, o sin nada que decir, hablan los elementos como antes.
  - **Sobre la línea de un contorno, el contorno conserva la suya.** `tip_at` no conoce contornos, y su
    propia regla pone primero lo que está colocado con precisión, porque el material está en todas
    partes. Si no, el nombre del contorno, que la prueba B3b dio por bueno, dejaría de verse con la ayuda
    de datos encendida por defecto.
  - **Solo en Seleccionar:** la ventana actualiza la ayuda de datos solo al pasar el puntero en ese modo,
    así que en cualquier otro sería la última, de otro sitio.

## 2. Tests

`tests/test_canvas_redraw_v1327.py` (nuevo), sobre la ventana mostrada y el talud pequeño de
`test_results_stale_v1297`, calculado por el camino real de la ventana:

- **D322:**
  - dentro del talud no hay contorno bajo el puntero, y la ayuda es la de la región;
  - sobre su línea, la del contorno;
  - a medio `PICK_PX` de la línea lo toma, y a tres veces no, con el zoom a 1×, 4× y ¼×;
  - un clic dentro no selecciona ningún contorno.
- **D323:**
  - tras mover el pie no hay superficies (control: un resultado de otro modelo no se dibuja), y al
    deshacer vuelven;
  - *Opciones de visualización* y una anotación las conservan;
  - un proyecto nuevo no dibuja nada del anterior;
  - el marcador se borra al salir del modo y al cambiar de proyecto.
- **D330:** un resultado del agente está vigente al enseñarse (control), una edición lo marca, y al
  deshacer deja de estar marcado y sus superficies vuelven.
- **D331:**
  - encendida, dentro del talud se enseña la ayuda de datos; apagada, la de la región;
  - en «mínimo», solo el nombre del material;
  - sobre la línea de un contorno, la del contorno;
  - la petición de ayuda llega a la pantalla con el texto de la ayuda de datos.

**Con el código de 0.1.326 fallan 13 de los 14 casos.** El control («sobre su línea, la ayuda es la del
contorno») pasa en los dos árboles. Se corrió sobre un `git archive` de 0.1.326, sin el buscador
editable.

## 3. Verificación

- **El test de esta versión**, 14/14, después de corregir el control de D323 (§0).
- **Los vecinos**, 589/589 en 40 archivos: lienzo, ayudas y ayudas de datos, resultados y resultado
  anterior, *Interpretar*, anotaciones, forzado, vértices, contornos, selección, castellano en pantalla,
  puente del agente, deshacer, modos, búsqueda por bloques y visualización.
- **Suite entera:** 6188/6188, `EXIT=0`, 89 min.
- **Banco:**
  - `verificar_cierres.py` entero: 72 comprobaciones, D322, D323, D330 y D331 **CUBIERTO POR TEST** y 0
    bajadas;
  - D331 abierta en P8 y cerrada en la misma versión;
  - instantánea `Evaluaciones/0.1.327`, las cuatro fichas retiradas y podadas de P8;
  - prompts (39);
  - auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia:** es lo que dibuja y enseña el lienzo.

## 4. Pendiente

- **D324–D329** (resto de P8i), y D314 después.
- **A mano, en la cuarta prueba de la interfaz:**
  - la ayuda de una región y la del contorno, y un clic dentro;
  - calcular, mover, deshacer y ver volver las superficies;
  - el marcador tras mover un vértice;
  - la ayuda de datos encendida y apagada, dentro del talud y sobre un contorno.
