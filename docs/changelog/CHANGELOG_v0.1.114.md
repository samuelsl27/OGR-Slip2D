# OGR Slip2D v0.1.114

**La superficie del terreno inventaba suelo delante de toda cara vertical, y
el defecto apareció buscando otra cosa: el encargo era el anclaje del
problema 59 y el anclaje no tenía la culpa**

---

## De dónde salió

El encargo pedía cerrar **D39**, «la fuerza que moviliza un anclaje inyectado
es demasiado grande»: el problema 59 del banco de verificación —Pockoski y
Duncan (2000), su quinto talud, un muro anclado de 20 ft en arena— daba Bishop
**1,135** frente a **0,582** publicado, un **+95 %**.

Lo primero que se hizo fue lo que manda la ficha del problema, cuya confianza
geométrica está declarada como *media*: **volver a medir la geometría sobre la
figura antes de acusar al motor**. Y la figura dio más de lo que se le pedía.
El panel de resultados de la **figura 59.2** no publica sólo el centro y el
radio del círculo crítico; publica **los dos extremos de la superficie**:

```
Method: spencer          Left  Slip Surface Endpoint:  0.000,  0.000
Factor of Safety: 0.596  Right Slip Surface Endpoint: 12.583, 24.580
Center: -30.872, 31.315
Radius: 43.975
```

Doce coma seis pies de ancho. **OGR analizaba ese mismo círculo de x = −40,76 a
x = +12,61: cincuenta y tres pies.** El extremo derecho coincidía al centímetro
—12,607 contra 12,583— y el izquierdo no se parecía en nada.

## El defecto

`ogr_core/geometry/ground.py` es, desde v0.1.84, **la única definición del
terreno** en el proyecto: el rebanador toma de ahí el peso de cada dovela, la
búsqueda corta el arco contra ella, el optimizador engancha vértices y el
lienzo dibuja. Se construye muestreando `upper_y_at` —la envolvente superior
del polígono cerrado— en los puntos de ruptura y **uniendo las muestras con
rectas**.

Esa construcción es exacta mientras la envolvente sea **continua**. Deja de
serlo en cuanto el contorno tiene una **cara vertical**: un muro salta de la
banqueta que tiene delante a su propia coronación en una sola abscisa, y una
polilínea de x estrictamente creciente **no puede contener un salto**. Lo que
hacía era dibujar una **rampa** por la cara, e inventarse el suelo de debajo.

Reproducido en el modelo más pequeño que lo enseña, cinco vértices
`(0,0) (30,0) (30,10) (10,10) (10,0)`:

```
  x     upper_y_at (la definición)   ground_surface() (lo que usaba el motor)
 2.0            0.000                        2.000
 5.0            0.000                        5.000
 9.9            0.000                        9.900
10.0           10.000                       10.000
```

La banqueta llana convertida en una rampa a 45°. `upper_y_at` estaba bien; la
polilínea derivada de ella, no. **El docstring del módulo prometía «the exact
envelope for any simple polygon»**, y era falso desde que existe.

## Lo que costaba

**Peso.** En el problema 59 son **100 ft² de suelo que no está ahí**, sobre la
banqueta entre x = −10 y x = 0. La masa que el rebanador pesaba salía un
**26 %** más grande que la que encierra el polígono medido con Shapely:

| dovelas | área OGR | área Shapely | diferencia |
|---|---|---|---|
| 200 | 481,07 | 381,06 | **+26,2 %** |

Y no es un error que se encoja al refinar, porque no es de discretización: al
arreglarlo, la misma comparación baja a +0,59 % con 200 dovelas y a +0,014 %
con 3 200, que es ya sólo cuerda contra arco.

**Y algo peor que el peso: la masa analizada.** Borrar la banqueta borra un
**cruce con el terreno**. El arco del círculo que publica la figura 59.2 llega
al terreno exactamente en el pie del muro, lo que parte el círculo en **dos
masas que se tocan en un punto**; con la banqueta sustituida por la rampa ese
cruce no existe, `candidate_chords` devuelve una sola cuerda y OGR pesa los dos
lóbulos como uno.

```
cuerdas, radio exacto por el pie (43,973965):
  antes  : [(-40,756 · 12,606)]
  ahora  : [(-40,756 · 0,000), (0,000 · 12,606)]   <- los dos lóbulos del manual
```

**Alcance.** De los 142 contornos externos del banco, **4 tienen cara vertical
interior y los cuatro llevaban suelo inventado**: problema 47 (18,0 ft²), 48
(28,0 ft²), 59 (100,0 ft²) y 60 (175,0 ft²). Fuera del banco, cualquier muro,
excavación o banqueta que dibuje un usuario.

## El arreglo

La envolvente **lleva sus saltos**: donde los límites laterales difieren, la
polilínea recibe dos (o tres) vértices que comparten abscisa y el salto queda
como segmento vertical de verdad. Los límites se toman **de las aristas** y no
sondeando en `x ± δ` — un sondeo necesita un paso a la vez lo bastante pequeño
para no salirse del punto de ruptura vecino y lo bastante grande para
sobrevivir a la tolerancia con que se prueban las aristas, y las dos cosas no
siempre se pueden a la vez.

Eso le cuesta al perfil su monotonía estricta en x, así que **todos los
consumidores pasan a leerlo por `envelope_y_at`**, con una regla explícita: en
la envolvente **superior** un segmento vertical vale su extremo **alto**; en la
**inferior**, su extremo **bajo**.

- `ogr_slip2d/surface.py::ground_y_at` devolvía el **punto medio** de un
  segmento vertical y paraba en el primer tramo que casara. En el pie del muro
  del 59 eso son 10 ft entre la banqueta (0) y la coronación (20), y ninguno de
  los dos es el terreno.
- `ogr_slip2d/optimize.py::_ground_y` y `search.py::_interpolate_top_y` **ya
  sabían** que un tramo vertical vale su extremo alto. Lo que no sabían es que
  el tramo **anterior** al salto también abarca esa abscisa y va primero, así
  que nunca llegaban al escalón.
- `_mean_polyline_y`, que es de donde sale el peso, integra ahora leyendo los
  dos extremos **del segmento** que cubre cada subintervalo, en vez de preguntar
  «y en esta x». Sobre un escalón la segunda pregunta es ambigua y la primera
  nunca lo es, y así la integral de una función escalonada vuelve a ser exacta.
- `envelope_y_at` admite además un **lado**: una dovela cuya esquina cae justo
  en el escalón necesita la rama sobre la que se apoya su propio cuerpo, no «el
  terreno en esa abscisa», que contesta la coronación para las dos.
- Mismo arreglo en `_lower_envelope`, que tiene el defecto en espejo y alimenta
  las superficies compuestas.

## Lo que se movió, y en qué sentido

En el círculo publicado del problema 59, Bishop pasa de **1,0439 a 1,1497** con
anclaje y de **0,5325 a 0,4791** sin él.

**El signo no era el que se supuso.** La primera redacción de este changelog
decía que la rampa erraba del lado inseguro; es al revés: la rampa **baja** el
factor, porque la cuña inventada se apoya sobre la banqueta, en la mitad del
pie de la masa, donde su peso empuja más de lo que sujeta. Eso es la respuesta
de esta geometría y no una regla — una cuña fantasma detrás de la coronación
tiraría al otro lado. Va escrito en el test, porque el error estuvo en suponerlo
en vez de medirlo.

## Lo que se movió en el banco, y no era sobre todo el peso

Los cuatro problemas con cara vertical, medidos espalda con espalda en la misma
máquina: la rampa contra el escalón, mismo modelo, misma rejilla.

| problema | método | rampa | escalón | publicado | antes | ahora | válidas |
|---|---|---|---|---|---|---|---|
| 47 | janbu simp. | 1,4044 | **1,0265** | 0,890 | +57,8 % | **+15,3 %** | 122 → **1051** |
| 47 | janbu corr. | 1,5070 | **1,0750** | 0,890 | +69,3 % | **+20,8 %** | 122 → 1049 |
| 48 | janbu simp. | 1,5031 | **1,1182** | 0,922 | +63,0 % | **+21,3 %** | 79 → **1044** |
| 59 | bishop | 1,1350 | **0,8979** | 0,582 | +95,0 % | **+54,3 %** | 8 → 20 |
| 59 | spencer | 0,9688 | **0,7093** | 0,596 | +62,6 % | **+19,0 %** | 1 → 13 |
| 59 | janbu simp. | 0,7938 | **0,6546** | 0,583 | +36,2 % | **+12,3 %** | 8 → 20 |
| 59 | lowe-karafiath | 0,7527 | **0,5383** | 0,588 | +28,0 % | **−8,5 %** | 8 → 20 |
| 59 | ordinary | 1,0263 | **0,8504** | 0,859 | +19,5 % | **−1,0 %** | 8 → 20 |
| 60 | los cinco | **sin resultado** | 1,61 – 2,10 | — | — | — | **0** → 8–17 |

**La sorpresa está en la última columna, y es más grande que el peso.** La
rampa no sólo añadía suelo: **invalidaba superficies**. En el problema 47 la
búsqueda pasaba de 122 superficies válidas de 1859 a **1051**, ocho veces y
media más; en el 48, de 79 a 1044. Y el problema **60 no daba ningún resultado
en absoluto** —0 válidas de 48, los cinco métodos en blanco— porque la rampa le
tapaba la banqueta entera. Con el escalón responde.

Tiene sentido visto el mecanismo: la rampa levanta el terreno delante del muro,
así que todo arco que aflore ahí queda «por encima del terreno» y se rechaza.
El defecto se llevaba por delante justo la familia de superficies que sale del
pie del muro, que es donde está el mecanismo.

**Ninguno cierra todavía.** El 47 sigue a +15,3 % y el 48 a +21,3 % de lo
publicado, y los dos avisan de que su centro crítico cae en el borde de la
rejilla: son búsquedas por revisar, no valores por citar. Lo que este cambio
demuestra es la dirección — los cuatro se acercan y ninguno se aleja.

## El test

`tests/test_ground_envelope_v1114.py`, once casos. Tres anclajes y ninguno es
una captura de lo que el código imprime:

- **identidad** — la polilínea debe reproducir `upper_y_at` en todo x.
  `upper_y_at` es la *definición* de la envolvente y llega a ella por otro
  camino, un máximo sobre las aristas; se mide como **área entre las dos curvas
  = 0**;
- **externo (Shapely)** — la masa que pesa el rebanador debe ser la que encierra
  el polígono, medida por una implementación independiente, y el error tiene que
  **converger** al refinar;
- **publicado** — los dos lóbulos del círculo del 59 deben caer en los extremos
  que imprime el panel de la figura 59.2.

Y uno más, que es el que evita repetir el error de v0.1.110: **la rampa se
reconstruye a propósito** desde los mismos puntos de ruptura y se comprueba que
el factor de seguridad se mueve. Un arreglo que no mueve ningún número no es un
arreglo (regla 7).

**Una sutileza que costó una hora y que va en la cabecera del test.** El radio
publicado, 43,975, está **redondeado**. Con él el arco pasa **0,00145 ft por
debajo** del pie del muro y las dos masas son de verdad una sola, así que el
círculo **no** debe partirse — y no se parte. El radio que lo hace pasar exacto
por (0 · 0) es 43,973965, y es el único que discrimina. Un test escrito sólo
sobre el redondeo publicado **habría pasado por encima del defecto**.

---

## Lo que este cambio NO cierra, y por qué el encargo estaba mal enunciado

**D39 no lo sostiene la medida.** Sobre la superficie que el propio manual
publica, y con los **13 750 lb/ft completos** del anclaje —el arranque entero,
porque el cruce cae en la longitud libre—:

| método | OGR | publicado | Δ |
|---|---|---|---|
| **spencer** | **0,5720** | 0,596 | **−4,0 %** |
| lowe_karafiath | 0,5212 | 0,588 | −11,4 % |
| bishop | 1,2636 | 0,582 | +117 % |
| janbu simplificado | 0,7225 | 0,583 | +23,9 % |
| ordinary | 0,9548 | 0,859 | +11,2 % |

Spencer es justamente el método al que pertenece esa figura, y **reproduce lo
publicado a −4 % con la fuerza entera**. La fuerza no está demostrada como
excesiva.

Aislando los términos del soporte sobre esa misma superficie:

| | sin anclaje | completo | sin `T_N` | sólo `T_N` |
|---|---|---|---|---|
| bishop | 0,0967 | 1,2636 | 0,2933 | 0,9456 |
| **spencer** | 0,1378 | **0,5720** | 0,5720 | 0,5720 |

Los métodos de equilibrio completo son **insensibles** a `T_N` y a `T_S`, porque
toman el soporte como fuerza externa. En los de cociente, el `T_N·tanφ'` crudo
—fuera de `m_α`, que es como lo escribe la referencia— se lo lleva casi todo: el
anclaje cae a **13,9° de la normal** a una base de **61°**, así que la aprieta
con 13 348 lb/ft y OGR le acredita **7 706 lb/ft** de rozamiento frente a
**984 lb/ft** de toda la resistencia del suelo. El comentario de
`bishop.py` ya avisaba de que la diferencia «is second-order for the usual
near-horizontal bases» — aquí las bases van de **44° a 81°**.

**D39 se re-atribuye**: no es la magnitud de la fuerza del anclaje, es el
término `T_N·tanφ'` de los métodos de cociente sobre base muy inclinada. Y
decidirlo necesita un caso publicado que dé la superficie crítica **de Bishop**,
que el 59 no da: su figura es la de Spencer.

**Queda también, y es del banco, no del programa**: la rejilla de búsqueda del
`construir_modelo.py` del 59 no es la de la referencia. El recuadro de la figura
59.2 la sitúa en torno a x∈[−46, −3], y∈[9, 53]; el modelo usa x∈[−15, 40],
y∈[15, 80], y el centro publicado (−30,872 · 31,315) **cae fuera**. La búsqueda
genera 42 superficies, de las que Bishop valida 8 y Spencer **1**. Ese mínimo no
es evidencia de nada, y compararlo con lo publicado fue lo que produjo el +95 %
del encargo.
