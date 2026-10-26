# OGR Slip2D v0.1.368

**El segmento recto que salía del vértice (0, 0) del talud de ejemplo era un arco que empezaba en el
origen del camino de dibujo: el lienzo se saltaba el primer punto de los círculos cuyo extremo cae fuera
del círculo por un ulp. Ahora pregunta la regla del arco al núcleo, y cada arco empieza en su extremo
(D347, cerrada).** Sexta versión de la tanda P8l.

## 0. Lo que se encontró

- **La quinta prueba de la interfaz** (H13) vio, tras Calcular el talud de ejemplo, un segmento recto
  desde el vértice (0, 0) hasta unos (20, 21), entre las superficies válidas. Sin medir.
- **Medido por la escena real (regla 6), antes de tocar nada**, con el código de 0.1.367:
  - en la vista «mínimo», **2 de 143** círculos tienen un camino que empieza en (0, 0); en la vista
    «todas», **23 de 1366**;
  - todos tienen el centro a la cota de la coronación (y = 25): centro (32,5; 25) con radio 8,72, centro
    (30; 25) con radio 6,17…;
  - el segundo punto de esos caminos, el primero de verdad, está en (23,95; 23,31) y similares. Es el
    segmento que vio la prueba.
- **La causa:**
  - `SlipSurfaceItem` dibuja cada círculo con 61 puntos de `x_left` a `x_right`, y se saltaba los que dan
    `R² − (x − xc)² < 0`;
  - un círculo con el centro a la cota de la coronación la toca con tangente vertical, y su `x_left` cae
    unos ulps **fuera** del círculo (disc ≈ −1e−14);
  - se saltaba el primer punto, el camino empezaba con un `lineTo`, y un `QPainterPath` dibuja un primer
    `lineTo` desde su origen, el (0, 0).
- **El núcleo ya lo resolvía:** `SlipCircle._lower_arc_disc` toma un extremo así como sobre el círculo
  (`_ARC_EPS`), desde la tangencia de v0.1.100 que dejó Bishop un 25 % bajo en el problema 23. El lienzo
  tenía su propia copia de la regla, más estricta.
- **`SlipRadiiItem` tenía la misma prueba estricta:** no dibujaba el radio a ese extremo.
- **El PNG del agente** (`model_render`) no tiene el defecto: dibuja la superficie desde las bases de las
  dovelas, no desde el círculo.
- **No era otra cosa** (las posibilidades que dejaba abiertas la ficha): ni la rejilla, ni los límites del
  talud, ni el foco, ni un círculo de radio enorme. Era una superficie válida de verdad, dibujada mal.

## 1. Qué cambia

- **`ogr_gui/canvas/graphics_items.py`:**
  - `SlipSurfaceItem` pide cada punto del arco a `SlipCircle.base_y_at`, la regla del núcleo, sin copiarla,
    y el primer punto dibujado es siempre un `moveTo`;
  - `SlipRadiiItem` pide los extremos igual, y dibuja los dos radios.
- **Ningún número cambia:** el FS del ejemplo sigue siendo 1,0914331494631124.

## 2. Tests

- **`tests/test_canvas_arc_v1368.py`** (nuevo, 3 casos):
  - el ejemplo calculado, en las vistas «mínimo» y «todas»: ningún camino empieza en el origen, y cada uno
    empieza en su extremo izquierdo, sobre el arco. El FS es el de siempre;
  - la premisa se ejercita: entre las superficies del ejemplo hay extremos fuera del círculo por redondeo,
    contados desde las propias superficies;
  - un círculo con el extremo un ulp fuera empieza ahí, y se dibujan sus dos radios.

**Con el código de 0.1.367 fallan los 3.**

## 3. Verificación

- **El test de esta versión:** 3/3.
- **Los vecinos:** 246/246 en el lienzo, Interpretar, el dibujo de capas débiles y de grietas, las
  superficies del usuario, las consultas, los resultados desfasados, el castellano y los temas.
- **Suite entera:** 6602/6602, `EXIT=0`, 107 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 102 comprobaciones (una más, `d347`), 0 bajadas. D347 queda
    **CUBIERTO POR TEST**: por la escena del ejemplo calculado, 0 de 143 y 0 de 1366 arcos desde
    (0, 0), y las mismas 2 y 23 superficies con el extremo fuera del círculo empiezan ahora en él;
    FS 1,0914331494631124;
  - manual 02: `verificar_cierres.py --seco`, 238 veredictos iguales;
  - **D347 retirada**, podada de `PAQUETES` y tachada en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.368` (raíz 983 archivos, 02 3284), prompts (38) y auditorías con
    0 ERROR.

## 4. Pendiente

- La tanda sigue con D343 y D345 (0.1.369): el nombre del método y las unidades del retroanálisis, la
  leyenda de FS frente al tiempo y la cabecera FS/FSD/Ky de la tabla de superficies.
