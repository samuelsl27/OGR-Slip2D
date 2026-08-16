# OGR Slip2D v0.1.84 — el programa creía que había un barranco donde había un llano

El Ejemplo 2 daba un factor de seguridad de **0,792** contra los **1,156**
de la referencia: un 31 % bajo. El círculo crítico que dibujaba era medio
arco que salía por el **fondo del modelo**, y buena parte de las
superficies analizadas bajaban por debajo del terreno.

Dos bugs, ninguno en la formulación. Sobre la **misma** superficie que la
referencia, los siete métodos ya coincidían con ella al 0,26 %. El
problema era **qué** superficie se analizaba.

---

## 1 · La superficie del terreno se sacaba de los vértices, no de las aristas

`_ground_surface_from_external` agrupaba los vértices del contorno externo
por `x` y se quedaba con la `y` mayor de cada grupo. Eso solo es correcto
si toda `x` de un vértice del fondo la comparte algún vértice de arriba.

El contorno del Ejemplo 2 tiene un vértice en **(0, 0)**, sobre la arista
inferior, y ningún vértice superior está en `x = 0`:

```
externo : (100,0) (100,70) (70,70) (55,55) (40,55) (15,30) (-50,30) (-50,0) (0,0)

perfil publicado : (-50,30) ( 0, 0) (15,30) (40,55) (55,55) (70,70) (100,70)
perfil real      : (-50,30) ( 0,30) (15,30) (40,55) (55,55) (70,70) (100,70)
                            ^^^^^^
```

El programa creía que el terreno llano de `y = 30` tenía un **barranco de
30 m** en `x = 0`. De ahí todo lo demás: el círculo crítico «afloraba» en
`x ≈ 0,39` sobre el suelo del modelo, se quedaba en medio arco, y bajaba
hasta `y = −2,05`.

Un vértice de más en el fondo — algo que cualquiera dibuja sin pensar — y
el análisis entero cambia de sitio.

### Había tres definiciones de «superficie del terreno», y dos estaban mal

| dónde | cómo | en el Ejemplo 2 |
|---|---|---|
| `slicer._ground_surface_from_external` | vértices agrupados por `x` | barranco en (0,0) |
| `canvas_view._ground_polyline` | vértices con `y ≥ y_media` | **se come la mitad izquierda**: devuelve solo (40,55) (55,55) (70,70) (100,70) |
| `PathSearch._ground_profile` | envolvente sobre **aristas** | correcta |

La buena era la que el solver no usaba. Ahora hay una sola,
`ogr_core.geometry.ground_surface`, y las tres delegan en ella. La del
lienzo dibujaba la zona de grieta de tracción contra un terreno que
empezaba pasada la mitad del talud; eso también queda arreglado de paso.

La función añade además los puntos de ruptura donde **dos aristas se cruzan
en proyección**, no solo las `x` de los vértices: muestrear solo en los
vértices es exacto para un perfil monótono, pero no para un contorno con
voladizo o reentrante.

## 2 · Con varias masas deslizantes se cogía la primera, no la crítica

Un círculo que corta el terreno más de dos veces define **varias masas
deslizantes disjuntas**. El código tomaba el primer par de cortes por la
izquierda y descartaba el resto sin mirarlos.

El círculo crítico de la propia referencia corta este perfil **cuatro**
veces:

```
cortes: -20,925   14,259   15,342   47,323

-20,925 .. 14,259   área  61,7 m²   lente somera bajo el llano   -> bishop = ∞
 14,259 .. 15,342   el arco va POR ENCIMA del terreno            -> no es masa
 15,342 .. 47,323   área 184,5 m²   la rotura del talud          -> bishop = 1,1548
```

Se quedaba con la lente —momento motor ≈ 0, o sea ningún factor de
seguridad— y **tiraba el círculo crítico verdadero a la basura como
inválido**. Por eso el mínimo global caía en otro círculo peor.

Ahora `evaluate_circle` evalúa **todas** las masas del círculo y se queda
con la de menor factor de seguridad, que es la mecánica crítica y es lo
que una búsqueda de superficie crítica busca por definición. Reproduce la
referencia en los dos ejemplos:

- **Ej_2**: descarta la lente, coge la rotura del talud (1,1548 vs 1,1556).
- **Ej_1**: descarta la lente del banco `75,4..100,6` y coge la salida por
  el pie `45,47..74,84` — que es justo lo que v0.1.18 arregló a mano con
  la regla «la primera cuerda». La regla nueva lo hace por criticidad en
  vez de por orden, y `test_non_composite_exit_at_toe` sigue en verde.

`intersect_with_ground` se mantiene con el criterio antiguo para quien solo
quiere una superficie que dibujar; lo que no puede hacer una búsqueda es
usarlo a solas.

## 3 · Nada impedía que una superficie se saliera del terreno

La referencia lo dice sin rodeos en *Grid Search*:

> if a circular surface extends past the lower limits of the External
> Boundary, the surface is discarded, and is not analyzed

y su informe las cuenta como error **−103** — 287 de las 4840 del Ejemplo
2, 183 de las 4851 del Ejemplo 1. Aquí no se comprobaba **nada** contra la
frontera inferior: arreglado el punto 1, seguían quedando **162
superficies válidas** que bajaban de `y = 0`.

`leaves_soil_region` lo comprueba de forma exacta, no por muestreo: entre
los dos afloramientos la cuerda no puede cortar ningún tramo del contorno
que no sea terreno. Se salta cuando *Composite Surfaces* está activo, que
es exactamente lo que ese ajuste significa. Y se juzga **después** de la
grieta por curvatura inversa, porque la superficie que se analiza es la
que lleva el factor de seguridad.

## 4 · M-alpha: la justificación para tenerlo apagado era falsa

`AGENTS.md` decía que el filtro `m-alpha < 0,2` venía desactivado «porque
así la trae la referencia». Los informes de los **dos** ejemplos dicen lo
contrario: filtran con él por defecto y lo cuentan como error **−112**.

| | Ej_1 bishop | Ej_2 bishop |
|---|---|---|
| superficies con −112 en la referencia | 97 | 225 |

Es la segunda mitad del error de v0.1.74. Aquella versión lo apagó porque
medía `min m_alpha = −0,0100` en el círculo validado; v0.1.82 encontró que
esa medición era el bug —`m_alpha` no es simétrica en α y se estaba leyendo
en el espejo— y con el signo correcto ese círculo da **+0,928**. Pero la
frase que justificaba el defecto se quedó dos versiones más, y era falsa.

Activado por defecto. Medido en Ej_1: **el círculo crítico no se mueve**
(0,884517 en (88 , 70,5)) y se descartan 64 superficies, frente a las 97
de la referencia.

La lección no es el signo. Es que **una medición equivocada se quedó dos
versiones sosteniendo una decisión**, y nadie volvió a mirarla porque ya
había una frase que la explicaba.

### Y el recuento tenía que seguirla

Una superficie descartada por m-alpha **converge**, así que contaba como
válida — pero no puede ser nunca la crítica. Con el filtro apagado ese
hueco era cero; encendido, el panel habría dicho «2966 válidas» mientras 64
tenían prohibido ser la respuesta. `SearchResult.analysed_count` es el
número que ahora se enseña. La referencia hace lo mismo: las −112 van en
«Number of Invalid Surfaces».

---

## Resultados

Ejemplo 2, Bishop, 4840 círculos generados (= 22 × 20 × 11, la misma
población que la referencia):

| estado | FoS | centro | R | afloramientos | bajo el suelo |
|---|---|---|---|---|---|
| v0.1.83 | 0,7923 | (−13,81 , 35,00) | 37,05 | 0,39 .. 23,24 | 162 |
| + punto 1 | 1,1694 | (7,14 , 71,84) | 40,88 | 17,23 .. 44,39 | 162 |
| + punto 2 | 1,1669 | (1,90 , 82,37) | 53,45 | 15,74 .. 47,82 | 162 |
| + punto 3 | **1,1491** | (−3,33 , 82,37) | 55,40 | 15,14 .. 44,84 | **0** |
| referencia | 1,1556 | (−3,33 , 87,63) | 60,26 | 15,34 .. 47,32 | 0 |

De −31 % a **−0,57 %**. La `x` del centro coincide exactamente.

Sobre el **mismo** círculo que la referencia, los siete métodos:

| método | Slide | OGR | dif |
|---|---|---|---|
| ordinary/fellenius | 1,11442 | 1,11413 | −0,03 % |
| bishop simplified | 1,15564 | 1,15485 | −0,07 % |
| janbu simplified | 1,08493 | 1,08461 | −0,03 % |
| janbu corrected | 1,14924 | 1,14922 | −0,00 % |
| spencer | 1,15664 | 1,15454 | −0,18 % |
| lowe-karafiath | 1,16310 | 1,16167 | −0,12 % |
| GLE/Morgenstern-Price | 1,15785 | 1,15484 | −0,26 % |

Área de la masa: 184,462 m² contra 184,457 m² (+0,003 %).

Coste: 5,9 s contra 7,6 s antes. Más rápido, no más lento: se rechazan
antes muchas superficies que se estaban sliceando y resolviendo para nada.

### Una trampa de coste que el cronómetro no habría enseñado

La envolvente nueva es correcta pero **cuadrática** en el número de
vértices, porque busca los cruces de aristas en proyección; la vieja era
lineal. Y el slicer la pide **una vez por superficie**, o sea miles de
veces para un contorno que no cambia:

| contorno | sin caché | con caché |
|---|---|---|
| Ej_2, 9 vértices | 100 µs | 12 µs |
| perfil de 101 vértices | **10,5 ms** | 90 µs |

En el Ejemplo 2 el cronómetro de la suite no lo habría distinguido del
ruido: medio segundo sobre seis. En un perfil levantado en campo o
importado de DXF serían **51 s por búsqueda**, todos gastados en recalcular
la misma respuesta. Es justo el caso que `AGENTS.md` describe: manda contar
el trabajo añadido, no el reloj.

Memoizada sobre las **coordenadas**, no sobre el objeto: el contorno se
edita in situ al arrastrar un vértice, y una clave por identidad habría
devuelto el perfil viejo después de cada arrastre. Comprobado con un test
de invalidación.

---

## El camino equivocado: la regla de radios

Queda un **+0,98 %** en el mínimo global del Ejemplo 2 que no es
formulación: es **muestreo de radios**. En el centro del círculo crítico de
la referencia, (−3,333 , 87,632), los once radios que genera este programa
son `53,72 · 58,83 · 63,94 … 104,83`. El radio crítico, **60,257, no está**.

La documentación dice solo que «suitable Minimum and Maximum radii are
determined, based on the distances from the slip center to the slope
surface», y su figura `fig_gridsearch2.gif` dibuja el radio mínimo hasta el
punto más cercano de la cara del talud y el máximo hasta el límite de talud
más lejano.

**Se implementó literalmente y se midió. Salió peor:**

| bracket | Ej_1 (ref 0,882889) | Ej_2 (ref 1,155640) |
|---|---|---|
| el que había | 0,88452 (+0,18 %) | 1,16693 (+0,98 %) |
| según la figura | 0,90049 (**+1,99 %**) | 1,14910 (−0,57 %) |

Mejor en un modelo y **el doble de malo en el otro** — y en el modelo que
empeora, el Ejemplo 1, es el que está validado contra un valor publicado.
Además ninguna de las dos lecturas reproduce los radios críticos de la
referencia: con ningún `k` entero de ninguno de los dos brackets sale
60,257 en ese centro, ni 47,212 en el centro (88 , 70,5) del Ejemplo 1.

Conclusión: **la figura no se está leyendo como el programa la implementa**,
y cambiar un resultado validado a partir de una conjetura es exactamente lo
que la regla 1 existe para impedir. Se revirtió. El bracket antiguo se
queda, con el resultado del A/B escrito en su docstring para que nadie
vuelva a intentarlo a ciegas.

### El experimento que lo cerraría

Cuatro restricciones (dos centros críticos por ejemplo) no bastan para
despejar la regla. Hacen falta más, y se pueden fabricar en Slide sin
ajustar nada:

> Un modelo con una rejilla de **pocos centros** y **Radius Increment = 1**
> genera exactamente **dos** círculos por centro, que son `r_min` y
> `r_max`. Leyéndolos con *Add Query* en varios centros de coordenadas
> conocidas, el bracket queda despejado por lectura directa, no por ajuste.

Pendiente de esos datos.

---

## Lo que la regla de contención destapó en la propia suite

La suite completa cayó en tres sitios, y dos de ellos resultaron ser el
**mismo modelo mal planteado**, compartido por siete archivos de test:

```
externo: (0,0) (60,0) (60,12) (crest,12) (toe,0)
```

La última arista vuelve por encima de la primera: entre `x = 0` y el pie en
`x = 30`, **la superficie del terreno y la base del modelo son la misma
recta** `y = 0`. Ese tramo no encierra suelo ninguno. Todo círculo que
afloraba ahí tenía su arco por debajo de la base y **pesaba terreno que no
existe** — dovelas con altura positiva medida hacia un suelo inexistente.

Hasta v0.1.83 esas superficies se analizaban, y dos tests dependían de
ellas sin saberlo:

- **`test_support_increases_fos`**: con la contención puesta, los únicos
  círculos que quedaban dentro del suelo eran demasiado pequeños para los
  cinco bulones de 200 kN, así que **todos** caían por «la fuerza activa
  supera al momento motor» y la búsqueda no devolvía crítica ninguna. Con
  10 m de cimiento el resultado vuelve a ser exactamente el de antes:
  1,159 → 2,128.
- **`test_agrees_with_grid_search`**: el mínimo de la malla era una de esas
  superficies por debajo de la base. Sin ella, la malla 12×12 con 5 radios
  se queda en 1,157 frente a los 1,103 de la Slope Search — un 4,7 %, justo
  fuera del 5 % que el test tolera. **No es desacuerdo, es resolución**:

  | malla | FoS | diferencia |
  |---|---|---|
  | 12×12, 5 radios (845 círculos) | 1,1572 | 4,7 % |
  | 16×16, 9 radios (2601 círculos) | 1,1209 | 1,6 % |
  | 20×20, 11 radios (4851 círculos) | 1,1114 | 0,8 % |

  Comparar dos búsquedas exige darles a las dos resolución suficiente para
  converger. Cuesta 0,9 s.

Se corrigieron **solo esos dos** modelos. Los otros cinco archivos que
comparten la geometría siguen en verde porque no afirman nada sensible a
ella, y cambiarlos sin necesidad movería números que nadie ha pedido mover.
Queda dicho aquí para quien se lo encuentre.

El tercer fallo era el esperado: un segundo test afirmaba el defecto viejo
de m-alpha. También llevaba la justificación falsa escrita en su docstring,
y el aviso del diálogo de Project Settings decía lo mismo. Las tres copias
de la frase corregidas.

---

## Verificación

- `tests/test_slide_validation_ej2_v184.py`, nuevo: el segundo banco de
  pruebas contra la referencia. Los siete métodos sobre los dos círculos
  críticos al 0,5 %, el área de la masa al 0,5 %, la cuerda que debe
  elegirse, que ninguna superficie analizada baje del suelo, y la
  población generada = 4840.
- Ej_1 ya validaba los siete métodos; sigue en verde sin tocarlo, y con él
  `test_non_composite_exit_at_toe`, que es el caso que motivó la regla
  antigua de la cuerda.
- Suite completa, sin argumentos.

Un detalle que costó un rato y merece quedar escrito: alimentar la cuerda
con los extremos **impresos** por la referencia (`47,323`, tres decimales)
en vez del corte real (`47,322908`) deja el arco 1,4·10⁻⁴ por encima del
terreno, el slicer descarta la última dovela y el área baja un 0,6 %. La
precisión de un informe no es geometría exacta.
