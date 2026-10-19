# OGR Slip2D v0.1.332

**Las capas de agua de *Interpretar* dibujan lo que dicen, con líneas de corriente nuevas validadas
contra una solución cerrada (D329, segunda parte; D329 cerrada).** Novena y última versión de la tanda
P8i.

## 0. Lo que se encontró

- **Cuatro casillas sin conectar.** En *Interpretar*, *Agua subterránea → Superficie freática, Líneas
  piezométricas, Vectores de flujo* y *Líneas de corriente* eran casillas sin nada conectado: marcarlas
  no cambiaba el dibujo (regla 7; D329, encontrada al planificar P8i).
- **Lo que ya existía y se reutiliza:**
  - *Interpretar agua subterránea* ya dibujaba los vectores de flujo (la velocidad de Darcy de cada
    elemento, `SeepageResult.velocity`) y la superficie libre;
  - la superficie libre era un método del *solver*, aunque solo lee la malla y el resultado, y
    *Interpretar* tiene los dos en el proyecto (`fem_mesh` y `seepage_result`), pero no el *solver*.
- **Las líneas de corriente no existían en ningún sitio.**
- **Mi primer trazador se paraba en los nodos.**
  - Una línea que empezaba justo en un nodo no avanzaba, si el elemento elegido para arrancar no era
    aquel hacia el que apunta el flujo.
  - Una línea que cruzaba un vértice se paraba en él, porque el vecino «a través de la arista» por la
    que salía no es por donde sigue el rayo.
  - Lo vio la medida que se hizo para fijar la tolerancia del test: en el campo uniforme, una línea de
    (5, 0) se paraba en (6; 0,5), que es un nodo. Ahora el elemento siguiente es el que contiene un punto
    del rayo un pelo más allá, entre todos los que rodean los dos nodos de la salida.

- **Con el campo real, las líneas se cortaban.**
  - La captura de *Interpretar* con la filtración del primer ejemplo trabajado (107 elementos) enseñaba
    líneas de pocos elementos.
  - Contado: solo **una** de las 22 terminaciones (11 líneas, dos sentidos) llegaba al contorno. Las otras
    21 se paraban en una arista interior porque el punto de prueba, que el trazador usaba para elegir el
    elemento siguiente, no caía en ninguno.
  - El rayo salía casi rasante a su arista, y por redondeo el punto quedaba 5,7·10⁻⁸ dentro del elemento
    que dejaba y 5,4·10⁻⁸ fuera del siguiente.
- **Tres pasos para arreglarlo, uno de ellos equivocado:**
  - **El equivocado.** Una tolerancia de −10⁻⁶ en esa elección (el mejor candidato aunque quede algo
    fuera) era mayor que el propio paso de prueba, de unos 10⁻⁷ del elemento. Daba por buena también una
    velocidad que sale, y la línea iba y venía entre dos elementos hasta el detector de ciclos (19 de 22).
    En el campo uniforme dejó un tramo de 10⁻¹⁵ en un vértice del contorno.
  - **Lo que queda:**
    - por el interior de una arista, el elemento siguiente es el del otro lado, sin sondear;
    - solo en un vértice se sondea, y estricto;
    - donde los flujos de los dos elementos chocan en una arista (la componente normal de una velocidad
      constante por elemento no es continua), la línea corre a lo largo de esa arista, en el sentido de
      la componente tangencial de su media, hasta el vértice.
  - **Medido después:** 17 de las 22 terminaciones llegan al contorno.
    - Las otras cinco acaban en nodos a los que apuntan la mayoría de las velocidades de sus elementos
      (4 de 6 en uno de ellos), en contactos entre materiales: es convergencia del campo discreto, no del
      trazador.
    - En los campos de validación nunca se desliza, y sus errores no se mueven.

## 1. Qué cambia

- **`ogr_fem2d/solvers/streamlines.py`** (nuevo, sin Qt):
  - En un triángulo lineal la velocidad es constante, así que una línea de corriente es recta dentro de
    cada elemento. Se traza exacta, sin paso de integración: de un punto, a lo largo de la velocidad del
    elemento, hasta la arista por la que sale, y al elemento por donde sigue el rayo.
  - Por el interior de una arista pasa al elemento del otro lado. Por un vértice, al elemento en el que
    entra el rayo.
  - Donde el flujo de los dos elementos choca en una arista, corre a lo largo de ella, en el sentido de la
    componente tangencial de la media, hasta el vértice.
  - Se para en el contorno de la malla, en un elemento sin flujo, o en un nodo del que no sale el flujo de
    ninguno de sus elementos.
  - Las semillas van a lo largo de la recta que pasa por el centroide de la malla, perpendicular al
    flujo medio, repartidas por su anchura. Cada línea se traza aguas arriba y aguas abajo.
- **`ogr_fem2d.solvers.seepage.free_surface_points(malla, resultado)`**, la superficie libre como
  función. El método del *solver* la llama, y no cambia nada de lo que calcula.
- ***Interpretar*, las cuatro casillas:**
  - **Superficie freática:** la superficie libre del resultado por elementos finitos o, sin él, el nivel
    freático del modelo;
  - **Líneas piezométricas:** las del modelo;
  - **Vectores de flujo:** uno por elemento dibujado, a lo largo de su velocidad, con la longitud
    proporcional a ella;
  - **Líneas de corriente:** doce como mucho.
  - Se dibujan como anotaciones solo de esta ventana (D332), junto a las cotas de D329a, y no se guardan.
  - **Sin resultado por elementos finitos**, *Vectores de flujo* y *Líneas de corriente* se desactivan
    con su motivo (D324).

## 2. Tests

- **`tests/test_streamlines_v1332.py`** (nuevo, sin Qt), contra identidades externas (regla 1):
  - **una solución cerrada:** el flujo hacia un punto de estancamiento del potencial φ = x² − y², de
    velocidad (−2x, 2y) y función de corriente ψ = 2xy (su armónica conjugada por Cauchy-Riemann:
    φ + iψ = z²), cuyas líneas de corriente son las hipérbolas x·y = constante.
    - Con las velocidades exactas en los centroides, x·y se conserva a lo largo de cada línea con un
      error por debajo del 0,3 % en una malla de 40 × 40, y el error baja al refinar.
    - Medido en el ejemplo de cuatro arranques: 1,19 %, 0,24 %, 0,095 % y 0,023 % con 10, 20, 40 y 80
      divisiones;
  - **exacta tramo a tramo:** cada tramo está en un elemento y va a lo largo de su velocidad, hasta el
    redondeo, y aguas abajo;
  - **un campo uniforme** da rectas de contorno a contorno, también a través de un vértice;
  - control: sin flujo no hay líneas;
  - **en el campo real del primer ejemplo trabajado**, al menos tres cuartas partes de las terminaciones
    llegan al contorno (hoy, 17 de 22; con el primer trazador, una).
- **`tests/test_interpret_water_layers_v1332.py`** (nuevo), sobre el primer ejemplo trabajado con un
  nivel freático y una línea piezométrica añadidos y, para las capas de elementos finitos, con la
  filtración que resuelve `test_interpret_i3_v153`:
  - cada casilla mueve el dibujo, con resultado y sin él (regla 7);
  - la superficie freática son los mismos puntos que da el método del *solver*;
  - los vectores siguen la velocidad de su elemento;
  - las líneas de corriente son las del trazador;
  - sin resultado, las dos capas que lo necesitan se desactivan y dicen por qué.

**Con el código de 0.1.331 fallan los 13 casos** (allí no existe el módulo nuevo, ni la superficie
libre como función, ni las casillas con nombre). Se corrió sobre un `git archive` de 0.1.331, sin el
buscador editable.

## 3. Verificación

- **Los dos tests de esta versión**, 13/13, después de los arreglos de §0. Con los de 0.1.331, 16/16.
- **Los vecinos**, 574/574 en 34 archivos: la filtración, el agua subterránea, el transitorio, la malla,
  el acoplamiento, Picard, *Interpretar*, las anotaciones, el lienzo y medir.
- **Suite entera:** 6235/6235, `EXIT=0`, 96 min.
- **Banco:**
  - `verificar_cierres.py` entero: 79 comprobaciones, D329 **CUBIERTO POR TEST** (con sus tres tests: el
    de 0.1.331 y los dos de esta) y 0 bajadas;
  - instantánea `Evaluaciones/0.1.332`, D329 retirada y podada de P8. En P8 queda abierta solo D314;
  - prompts (33) y auditorías con 0 ERROR en la raíz y en el 02.
- **Ningún número del motor cambia.**
  - La superficie libre es la misma función, que el método del *solver* llama.
  - Las líneas de corriente son dibujo, y están validadas contra la solución cerrada.

## 4. Pendiente

- **Tanda P8i terminada.** Queda en P8 **D314** (mensajes del núcleo con códigos estables).
- **La cuarta prueba de la interfaz**, que tendrá que mirar a mano lo de D315–D332.
- **La exportación DXF de las anotaciones** (D332), que no se ha tocado.
