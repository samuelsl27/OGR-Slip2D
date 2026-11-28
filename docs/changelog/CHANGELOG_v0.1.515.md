# OGR Slip2D v0.1.515

**D450: el agua libre contra un acantilado empuja a la masa que sale por él.** Pasa cuando una superficie
sale por una cara vertical del terreno por debajo del agua libre. El tramo mojado de esa cara, entre la
salida y el agua, es el borde de la masa, y el agua lo empuja hacia dentro. Hasta 0.1.514 nadie lo
contaba: ni el rebanador ni las cuñas de Sarma. Con el bloque de la ficha se perdían 44,1 kN/m.

En el banco hay un solo problema afectado, el 092, y es «NO REPRODUCIBLE». Allí el círculo publicado
pasa en Bishop de **0,858 a 1,042**, frente al **1,037** de la referencia. La propietaria decidió
publicarlo y volver a correr el 092.

## 0. Lo que se encontró

- **El defecto, medido de nuevo** con el guion de la ficha (`_auditoria/P10_D450/reproducir_d450.py`).
  El bloque es un escalón de (50, 10) a (50, 20), con el agua a 17 y la salida a 14:
  - el rebanador mide el agua libre sobre el tope de cada dovela. La primera empieza en la cara con el
    tope a 20, así que suma 0;
  - las cuñas la miden sobre el terreno entre los topes de sus caras. La cara del pie va de (50, 14) a
    (50, 20), y también suman 0.

  La forma cerrada es ½·γw·3² = 44,145 kN/m a la cota 15.
- **Por qué solo una cara vertical:** una cara del terreno con anchura, por empinada que sea, es el tope
  de alguna dovela, y esa dovela recibe la componente horizontal del agua (`column * slope`). Solo una
  cara de anchura cero (dx = 0) no es el tope de nadie.
- **Las fuentes:**
  - Duncan, Wright & Brandon (2014), pp. 28-29: las presiones del agua exterior son parte de la tensión
    total en el contorno de la masa y hay que incluirlas para su equilibrio. En su §14.6 (p. 245), con
    todas ellas, los pesos totales y el agua del contorno dan el factor de los pesos sumergidos;
  - USACE EM 1110-2-1902: su texto extraído no dice nada de una cara vertical;
  - la ayuda de la referencia sí lo dice. Con agua libre, el extremo de la superficie se prolonga con un
    **segmento vertical** hasta la superficie del agua (su «slip surface endpoint» frente al «slope
    intercept»), y la línea de empuje de la primera y la última dovela tiene en cuenta las fuerzas
    hidrostáticas del agua libre. En el bloque de la ficha, ese segmento es justo la cara mojada: de 14
    a 17.
- **El Ordinario (D199):** el agua libre entra en la normal de la base solo por sus componentes
  verticales, para que una masa sumergida dé el factor de sus pesos sumergidos. El empuje de la cara es
  horizontal y es del mismo estanque, así que entra en `pond_force_h`, como el del tope.
- **Censo en seco del banco** (`_auditoria/P10_D450/censo_d450.py` y su log de 0.1.514): de 230
  modelos vivos, 61 caras verticales en el terreno, y solo **2** con el agua por encima de su pie. Las
  dos son del **092** (`modelo.ogr` y `modelo_sin_conexion.ogr`): la cara está en x = 6, de 6 a 9, con
  el agua a 9. El círculo publicado sale justo por ella, en (6,000; 6,069).
- **A/B del 092 en disco**, árbol de 0.1.514 contra el de 0.1.515 (`_auditoria/P10_D450/ab_d450_092.py`
  y sus cuatro logs). Va en disco porque la búsqueda reparte en procesos `spawn`, que no ven un
  interruptor del padre (D375). 0.1.514 reproduce los `resultados.json` de 0.1.188 bit a bit:

  | 092 | 0.1.514 | 0.1.515 | Referencia |
  |---|---|---|---|
  | Bishop, círculo publicado | 0,857614 | **1,042182** | 1,037 |
  | Bishop, crítica de la búsqueda | 0,702866 | 0,967107 | 1,037 |
  | Spencer | 0,998046 | 1,026664 | 1,111 |
  | GLE | 1,006545 | 1,024975 | 1,111 |
  | Sin conexión: círculo publicado | 0,825831 | 1,007700 | — |
  | Sin conexión: Bishop / Spencer / GLE | 0,647391 / 0,998342 / 0,998726 | 0,964846 / 1,023243 / 1,022576 | — |

  En el círculo publicado entran 42,13 kN/m (2,931 m de cara mojada). Lo que queda hasta la referencia
  es lo que hace al 092 «NO REPRODUCIBLE»: el arranque del geotextil y la geometría de las bancadas.
- **El bloque de la ficha, con el factor** (A/B en el mismo proceso): Spencer pasa de 7,4726 a 8,6832
  (+16,2 %), Janbu simplificado de 6,8548 a 7,9471 (+15,9 %), el Ordinario de 7,6539 a 9,0952
  (+18,8 %) y Sarma de 7,1875 a 8,3560 (+16,3 %). El agua empuja desde el lado hacia el que desliza la
  masa.
- **Hallazgo nuevo, D468, sin corregir** (regla 6; por decisión de la propietaria va en una ficha
  aparte). Una masa que **cruza** el acantilado tiene la cara dentro de su tope, no en un extremo. El
  rebanador corta en la x del escalón, y la cara cae entre dos dovelas de topes planos: se pierden
  ½·γw·7² = 240,3 kN/m con 30, 31 y 97 dovelas. Las cuñas de Sarma **sí** lo cuentan (240,345 kN/m),
  porque su camino entre topes recorre el escalón. Guion en `_auditoria/P10_D468/`.

## 1. Qué cambia

- `ogr_slip2d/slicer.py`:
  - `END_FACE_PONDED_WATER = True`, el interruptor de módulo, que se lee en cada llamada;
  - `end_face_water(project, ground, x, y_base, y_top, tol)` devuelve `(F, y_c)`. Solo si el extremo
    está en una cara vertical del terreno (`_ground_face_at`). La parte mojada sobre la masa va de
    `max(y_base, pie)` a `min(nivel, y_top, coronación)`, con F = ½·γw·[(n − y_lo)² − (n − y_hi)²]
    aplicada en el centroide del trapecio. Un extremo enterrado (con `END_ON_GROUND` apagado) no
    recibe nada, porque no tiene agua libre delante;
  - `_apply_end_face_water` pone +x en la primera dovela y −x en la última, por `add_water_force` (que
    guarda el momento) y en `pond_force_h`. **Salta el extremo que sea la pared de una grieta de
    tracción**: allí el empuje es el agua de la grieta, y sumar el del estanque la contaría dos veces.
- `ogr_slip2d/sarma/wedges.py`: la misma función sobre la cara exterior de la primera y la última
  cuña, cuando es vertical, con el mismo salto de la grieta. Como el resto del agua de una cuña, llega
  al solver como la fuerza horizontal de su base: Sarma equilibra fuerzas, no momentos, por cuña.

## 2. Tests

- `tests/test_end_face_ponded_d450_v1515.py` (nuevo, 6 tests, menos de 1 s), contra la forma cerrada:
  - el bloque de la ficha: la primera dovela y la primera cuña llevan +44,145 kN/m a la cota 15, también
    en `pond_force_h`, y nada más de la masa está bajo el agua;
  - el espejo: −44,145 kN/m en la última dovela y la última cuña;
  - con el agua sobre la coronación (nivel 22), el trapecio ½·γw·(8² − 2²) a 16,4, que es el centroide
    h·(b + 2a)/(3·(a + b));
  - un extremo que es la pared de una grieta no recibe nada del estanque;
  - control: una superficie con los dos extremos en el terreno llano queda igual bit a bit;
  - el interruptor mueve el factor de Spencer y el de Sarma (regla 7).

  Contra 0.1.514 caen el bloque, el espejo, el trapecio y el interruptor.
- **Cambiado a propósito**, `tests/test_sarma_angle_tool_v1469.py`,
  `test_interprets_canvas_offers_none_of_it`. Ese test lo rompió 0.1.513 (D456), y lo vio esta corrida
  del área `sarma`, que el patrón de D456 no incluía. Su control «Move Vertex» del menú del vértice ya
  no sale en un lienzo sin los menús de edición. Ahora exige «Copy Coordinates» y que no salga «Move
  Vertex». Su invariante, que no salgan las acciones de la superficie del usuario, sigue igual.
- Áreas `ponded`, `sarma`, `tension_crack`, `end_face`, `interslice`, `drawdown` y
  `slide_validation`, con `--jobs 4`: 746 casos. Falló uno, el de arriba, antes de cambiarlo. Los otros
  seis archivos que leen menús desde un lienzo suelto: 117 casos en verde.

## 3. Suite

La suite entera se corre al final de la tanda. El 092 se vuelve a correr en el banco tras el commit.
