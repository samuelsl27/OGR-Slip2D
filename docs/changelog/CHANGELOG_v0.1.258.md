# OGR Slip2D v0.1.258

**D244: los dos extremos de una poligonal están en el terreno, o la
superficie no se analiza, y se dice.** Hasta 0.1.257 el rebanador juzgaba los
extremos de una poligonal solo si la base quedaba POR ENCIMA del terreno. Un
extremo dentro del suelo se rebanaba tal cual, y la dovela extrema recibía
una cara vertical, del vértice al terreno, sin resistencia ni empuje: una
grieta que nadie había dibujado. La superficie salía válida y más baja, sin
aviso. La crítica del problema 15 hundida 5 m y 1 m pasaba de 0,4294 a
0,3929 en Janbu.

Tercera versión de la tanda P5. La propietaria decidió (2026-10-04) que se
investigara en la documentación y se adoptara lo mejor, la tolerancia (1e-4
del ancho) y que las dos superficies publicadas del banco que arrancaban
bajo el terreno se corrigieran en su origen.

## 0. Lo que se encontró

- **La referencia lo resuelve en tres puertas, y las tres se adoptan:**
  - **en el cálculo**, una superficie con «Only one (or none) slip surface /
    slope intersections» es el error −101, y un extremo enterrado deja una
    sola intersección;
  - **al introducir una superficie a mano**, los extremos «not entered
    exactly on the External Boundary … automatically "snap" to the nearest
    point on the External Boundary»;
  - **en la optimización**, la búsqueda local de Greco (1996), según la
    describe el artículo del recocido simulado de la documentación, comprueba
    la superficie movida «with respect to the boundaries» y la reajusta. El
    recocido simulado de OGR ya deslizaba sus extremos por el terreno.
- **La tolerancia del plan (1e-6 del ancho, la del rechazo por encima) habría
  rechazado archivos buenos.** Las poligonales archivadas llevan cuatro
  decimales. La crítica archivada del 15 «en el terreno» queda 6,7e-5 m bajo
  él, con una tolerancia de 4,1e-5. El censo de las 307 poligonales del banco
  lo midió: el redondeo deja los extremos hasta 2e-6 del ancho bajo el
  terreno, y los enterramientos reales empiezan en 3,3e-3. Con 1e-4 del ancho
  se separan sin solaparse.
- **Una regla ingenua habría rechazado tres casos legítimos:**
  - **una poligonal truncada por una grieta**, que acaba en la línea de
    grieta, bajo el terreno a propósito (19 modelos del banco tienen
    grieta);
  - **un extremo al pie de una cara vertical**, donde el terreno tiene dos
    cotas. El panel del 49 lo confirma: su extremo izquierdo es (0; 0), el
    pie de la cara x = 0, con el intercepto en (0; 30). Se compara con la
    menor;
  - **un extremo de grieta archivado.** La re-evaluación de las 301
    poligonales archivadas lo encontró en el 39 (arcilla). Su crítica
    archivada acaba 4,4e-5 bajo la línea de grieta, por el redondeo, y no
    lleva su grieta consigo, así que la exención que solo miraba la grieta
    de la superficie la rechazaba. La grieta se deduce del modelo (la regla
    de D90): un extremo sobre la línea de grieta del modelo, dentro de la
    tolerancia, es de grieta. Que esa misma poligonal pierda el empuje del
    agua es D192, abierta en P0.
- **Ninguna búsqueda del banco genera un extremo enterrado.** El censo
  dinámico (las 56 búsquedas no circulares, con el interruptor apagado y
  encendido) da la misma crítica en todas.
- **Las dos superficies publicadas que arrancaban bajo el terreno eran datos
  del banco mal puestos, no del motor:**
  - **el 49:** el vértice rotulado «(60, 66)» no es (60, 66). El panel de la
    figura 49.2 publica «Right Slip Surface Endpoint: 59.959, 65.619» y
    «Right Slope Intercept: 59.959 65.619», así que el terreno del programa
    de referencia pasa por ese punto. Con (60, 66), el extremo quedaba
    0,361 ft enterrado. Los rótulos son enteros; con (33, 53) y la x = 60
    del rótulo, el terreno pasa por el intercepto si y = 65,638, que se
    rotula «66»;
  - **el 25:** las superficies de GLE, de los dos Janbu y de
    Lowe-Karafiath eran las de la coronación anterior a P025-GEO2
    (2026-09-04), que movió la coronación de x = 6,0 a 5,7735 y actualizó
    solo la de Spencer. Su pie quedaba 0,050 bajo la cara y su extremo
    derecho fuera de la carga.
- **Una anomalía que se reporta, sin corregir (regla 6):** OGR usa −101 para
  «cualquier otro rechazo» (`interpretation.ERROR_OTHER`), y la referencia lo
  reserva para «una o ninguna intersección con el talud».

## 1. Los cambios

- **El rebanador** (`ogr_slip2d/slicer.py`):
  - rechaza una poligonal, también la base poligonal de una superficie de
    capa débil, cuyo primer o último vértice queda bajo la MENOR de las cotas
    del terreno en su x por más de `END_BELOW_GROUND_REL` = 1e-4 de su
    anchura;
  - quedan exentos los extremos de grieta, por la grieta que lleve la
    superficie o por la línea de grieta del modelo;
  - dentro de la tolerancia no toca nada;
  - razones propias para los dos sentidos: `REFUSED_END_BELOW_GROUND` y
    `REFUSED_END_ABOVE_GROUND`, porque el rechazo por encima, que ya existía
    desde v0.1.100, salía sin razón;
  - interruptor `slicer.END_ON_GROUND`.
- **La búsqueda** (`ogr_slip2d/search.py`):
  - cuenta cada razón aparte y la dice en una nota que no culpa al número
    de dovelas;
  - el resultado lleva `ends_below_ground` y `ends_above_ground`;
  - `refusal_text()` dice por qué la última `evaluate_surface` no dio nada;
  - la Auto Refine no circular fija también la y de sus extremos al terreno
    (`_pin_ends_to_ground`), salvo en un extremo de grieta.
- **El censo de inválidas** (`interpretation.invalid_summary`) cuenta los
  extremos fuera del terreno como −101, con su razón.
- **`evaluate_surfaces`** pone en los avisos por qué un método no dio
  resultado.
- **La API (`surface_evaluate`, y con ella el MCP):**
  - lleva el primer y el último vértice al punto más próximo del contorno
    exterior y lo dice (punto pedido, punto usado y distancia);
  - rechaza el movimiento si x dejaría de crecer;
  - sus `notes` dicen la razón de cada método sin resultado, en vez de «does
    not cut the model».

  La fila de la guía del MCP lo dice.
- **El optimizador con `move_endpoints=True`** mueve los extremos a lo largo
  del terreno, con los mismos dos números aleatorios por paso. El valor por
  defecto (`False`) no cambia nada.

## 2. Tests

**Nuevo `tests/test_polyline_endpoints_v1258.py`**, 14 casos:
- la premisa: con la regla apagada, un extremo hundido 2 m sale válido y más
  bajo;
- el rebanador lo rechaza con su razón;
- la búsqueda lo cuenta y su nota no habla de dovelas;
- el censo lo cuenta como −101;
- `evaluate_surfaces` lo dice;
- lo que está en el terreno, bit a bit;
- la tolerancia, relativa al ancho;
- el pie de una cara vertical;
- un extremo de grieta, con la premisa de que la grieta trunca de verdad la
  superficie (en x = 46,5);
- un extremo de grieta archivado a 2e-4 de la línea, fuera de la tolerancia
  de D189 y dentro de esta. Un primer intento a 4e-5 pasaba en vacío, porque
  en este modelo D189 ya lo reconocía;
- la API lleva el extremo al contorno y lo dice, y no dice nada con los
  extremos en el terreno;
- regla 7: con los extremos libres, el número se mueve y cada extremo sigue
  en el terreno;
- la Auto Refine no circular, con las dos coordenadas de sus extremos sobre
  el terreno.

**Seis tests existentes traían un extremo de poligonal fuera del terreno de su
modelo**, y la suite entera los encontró con la regla nueva. Ninguno vigilaba
eso: vigilan Steffensen, el error del desembalse, el filtro de cota mínima,
la idempotencia de la grieta y la pared arrastrada. Por decisión de la
propietaria se corrigieron sus DATOS, no sus aserciones, cada uno con un
comentario que dice qué traía:

| test | extremo | bajo el terreno | corrección |
|---|---|---|---|
| `test_drawdown_methods_v1108` | (300; 96) | 9,5 m | (300; 105,5) |
| `test_steffensen_scope_v1174` (dos casos) | (8; 26) | 4 m | (8; 30) |
| `test_surface_filters_v1102` | (44; 8,39) | 6 mm | sobre la cara, calculado |
| `test_tension_crack_truncation_v1109` | (35; 23,33) | 3,3 mm | (35; 20 + 10/3) |
| `test_tension_crack_wall_roundtrip_v1240` | el pie del arco | 0,36 m | el terreno sube solo detrás de la cara |

- El de los filtros lo había bajado su autor a propósito, porque 4 mm por
  encima ya se rechazaba desde v0.1.100.
- En el de la pared, subir la coronación de 40 a 41 movía también el vértice
  de la cara y la inclinaba bajo el pie del arco. Ahora la cara se queda y el
  terreno sube en un escalón detrás de ella (`_slope(face_top=…)`); la pared
  nueva sigue arriba en 41, que es lo que el caso comprueba.
- Los cinco archivos corregidos pasan también con el motor de 0.1.257 (112
  de 112): la corrección no depende de D244 ni afloja ninguno.

**Discriminación** contra un árbol de 0.1.257, con el envoltorio sin
buscador editable: **fallan 8 de 14**, seis por comportamiento y dos por
símbolo nuevo. Pasan la premisa y los cinco controles. Una primera versión
del ayudante del test leía el interruptor nuevo directamente, y en el motor
viejo hacía fallar también a los controles; ahora lo lee con `getattr`.

## 3. El banco

- **Censo estático** (`_auditoria/P5_0258/censo_extremos_d244.py`): la
  distancia al terreno de los extremos de las 307 poligonales archivadas
  (críticas, optimizadas y publicadas re-evaluadas).
  - Antes de corregir los datos, sin grieta: el 109, 0,99 m (D238, ya
    corregido); la publicada del 49, 0,361 ft; la del 25, 0,050; y el
    redondeo de los archivos, de 3e-5 a 7e-5 m.
  - Después: ninguno por encima de 1e-4 del ancho sin grieta. Quedan 25 de
    grieta, que la regla exime.
- **Censo dinámico** (`censo_familias_d244.py`, sobre un árbol con la
  tolerancia de 1e-6, más estricta que la publicada): las 56 búsquedas no
  circulares del banco (Path, Block y Particle Swarm), con el interruptor
  apagado y encendido.
  - Las 56 dan la misma crítica. La única que comparaba distinta solo
    difería en el identificador aleatorio de su círculo.
  - Ningún rechazo por debajo del terreno. Los 46 rechazos por encima son
    del 109 y ya se rechazaban antes.
  - La corrida se cortó dos veces en el límite de dos horas de una tarea en
    segundo plano y se reanudó con un salto de los ya hechos. Desde la
    segunda parte escribe cada fila al terminarla.
- **Re-evaluación de las 301 poligonales archivadas**
  (`reevaluar_archivadas_d244.py`), con el interruptor apagado y encendido:
  ningún factor se mueve. Las 13 que ya se rechazaban (un extremo en el
  aire, por redondeo) llevan ahora su razón en vez de «no se pudo rebanar».
- **Las dos filas corregidas en su origen**, con su A/B
  (`ab_publicadas_d244.py`):

  | problema | método | dato viejo | dato viejo, con la regla | dato corregido | manual |
  |---|---|---|---|---|---|
  | 49 | Janbu simplificado | 1,4332 | rechazada | 1,4397 | 1,446 |
  | 49 | Janbu corregido | 1,4656 | rechazada | 1,4722 | 1,479 |
  | 49 | recta, los dos Janbu | 1,4432 | rechazada | 1,4491 | — |
  | 25 | GLE | 1,1074 | rechazada | 1,0648 | 1,0 (teórico) |
  | 25 | Janbu corregido | 1,0919 | rechazada | 1,0359 | 1,0 |
  | 25 | Lowe-Karafiath | 1,0650 | rechazada | 1,0132 | 1,0 |
  | 25 | Janbu simplificado | 1,0217 | rechazada | 0,9694 | 1,0 |
  | 25 | Spencer | 1,0485 | 1,0485 | 1,0485 | 1,0 |

  - Las razones van en `construir_modelo.py` del 49 y en los
    `referencia.json` de los dos, con los archivos anteriores en
    `_auditoria/P5_0258/`.
  - Re-corridos con `ejecutar_caso.py --solo-publicado`.
  - En la comparativa del 02, las dos filas del 49 pasan de −0,88 % y
    −0,90 % a −0,44 % y −0,46 % (OK). La fila del 25 solo compara Spencer, lo
    único que publica el manual, y no cambia; las otras cuatro superficies
    corregidas no tienen cifra publicada.
- **Con los extremos libres, en el 15**, la caminata da ahora 0,4033 sin
  enterrar nada. Antes llegaba a 0,29–0,35 enterrando los dos extremos, y el
  manual publica para este talud entre 0,39 y 0,44.
- **Interruptor** `slicer.END_ON_GROUND` en `INTERRUPTORES` con (0, 1, 258)
  (42).
- **`d244()`**, en el verificador del 02:
  - en vivo, el 15 en el terreno da el mismo factor con la regla y sin ella,
    y hundido se rechaza con su razón;
  - con los extremos libres, los dos quedan en el terreno;
  - los censos;
  - el 25 y el 49 corregidos y corridos con 0.1.258;
  - la discriminación.

  Veredicto CUBIERTO POR TEST. Con 0.1.257 da NO SE SOSTIENE: la hundida
  sale válida, y con los extremos libres la caminata los entierra 3,46 m y
  0,45 m.
- **Dos cierres archivados bajaron por lo mismo que los seis tests.**
  - `d115()` copia la poligonal de v1174, con el extremo en (8; 26). Con
    `slice_surface` devolviendo None, `compute_fos` reventaba.
  - `d90()` sube la coronación de su talud a 41 inclinando la cara, como
    v1240.

  Se corrigieron sus datos con el mismo criterio que los tests:
  - en `d115()`, (8; 30);
  - en `d90()`, `_talud_phi0_d90(cara=…)`, con el escalón detrás de la cara.

  Los dos vuelven a CUBIERTO POR TEST. Medido aparte: el v1240 corregido sigue
  fallando en 0.1.239 en los mismos 4 de 9 casos que dice la discriminación
  archivada de D90, `test_the_ground_raised` incluido
  (`discriminacion_v1240_corregido_en_0.1.239.txt`). Los datos nuevos no le
  quitan al caso la capacidad de ver el defecto.

## 4. Verificación

- **Suite entera:** 5637 de 5637. Una primera pasada dio 6 fallos, los seis
  tests de datos con un extremo fuera del terreno (sección 2).
- **Los seis archivos tocados** y el nuevo: 126 de 126.

**Qué falta por probar:** nada en pantalla. La versión no toca la interfaz;
la nota nueva de la búsqueda sale en las notas del análisis como las demás.
