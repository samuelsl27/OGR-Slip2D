# Pendientes abiertos

Lo que quedó sin cerrar y **por qué**, para que no se pierda entre
changelogs. Cada entrada dice qué falta exactamente y qué haría falta para
cerrarla. Se borra la entrada cuando se cierra, no se marca.

Origen: trabajo sobre los ejemplos Ej_1 y Ej_2 de `referencias/Ejemplos/`
(v0.1.84 en adelante).

---

## 1 · La regla de radios del Grid Search — BLOQUEADO, necesita datos de Slide2

**Estado**: bloqueado esperando una medición que solo se puede hacer en
Slide2.

**Qué pasa.** Tras arreglar los dos bugs de v0.1.84, el mínimo global de
Ej_2 queda a **−0,57 %** de la referencia y el de Ej_1 a **+0,18 %**. Lo
que queda **no es formulación**: sobre la *misma* superficie los siete
métodos coinciden entre −0,00 % y −0,26 %. Es **muestreo de radios**.

En el centro del círculo crítico de la referencia, `(−3,333 , 87,632)`, los
once radios que genera este programa son

```
53,72 · 58,83 · 63,94 · 69,05 · 74,16 · 79,27 · 84,38 · 89,49 · 94,60 · 99,72 · 104,83
```

y el radio crítico de la referencia, **60,257, no está entre ellos**.

**Lo que ya se descartó, midiéndolo.** La documentación solo dice que
«suitable Minimum and Maximum radii are determined, based on the distances
from the slip center to the slope surface»; la figura
`fig_gridsearch2.gif` dibuja el mínimo hasta el punto más cercano de la
cara del talud y el máximo hasta el límite de talud más lejano.
Implementado literalmente:

| bracket | Ej_1 (ref 0,882889) | Ej_2 (ref 1,155640) |
|---|---|---|
| el que hay | 0,88452 (+0,18 %) | 1,16693 (+0,98 %) |
| según la figura | 0,90049 (**+1,99 %**) | 1,14910 (−0,57 %) |

Mejor en un modelo, el doble de malo en el otro — y el que empeora es el
validado contra un valor publicado. Revertido. Además **ninguna** de las
dos lecturas reproduce los radios críticos de la referencia: con ningún
`k` entero sale 60,257 en `(−3,333 , 87,632)` ni 47,212 en `(88 , 70,5)`.

Cuatro restricciones (dos centros críticos por ejemplo) no bastan para
despejar la regla, y ajustar parámetros hasta que cuadren cuatro números es
exactamente lo que la regla 1 prohíbe.

### Qué hace falta (a ejecutar en Slide2)

> Un modelo con una rejilla de **pocos centros** (por ejemplo 2×2, de
> coordenadas redondas y anotadas) y **Radius Increment = 1**. Con
> incremento 1 se generan **exactamente dos círculos por centro**, que son
> `r_min` y `r_max`. Leyendo esos dos radios con *Add Query* en cada
> centro, el bracket queda despejado por **lectura directa**, sin ajustar
> nada.
>
> Conviene repetirlo con dos geometrías distintas (por ejemplo la de Ej_1
> y la de Ej_2) y con los Slope Limits en su posición automática, anotando
> también dónde caen los marcadores triangulares.

Con esa tabla —centro, `r_min`, `r_max`— la regla se deduce o se refuta en
una tarde.

---

## 2 · La geometría degenerada compartida por cinco archivos de test

**Estado**: conocido, sin corregir a propósito.

Siete archivos de test usan este contorno externo:

```
(0,0) (60,0) (60,12) (crest,12) (toe,0)
```

La última arista vuelve por encima de la primera: entre `x = 0` y el pie en
`x = 30`, la superficie del terreno y la base del modelo son la misma recta
`y = 0`, y ese tramo **no encierra suelo**.

v0.1.84 corrigió los dos que dependían de ello para pasar
(`test_supports_v114.py` y `test_slope_search_v117.py`, ambos con 10 m de
cimiento). Los otros cinco —`test_block_search_v117`,
`test_grid_search_v117`, `test_noncircular_v115`, `test_sa_autorefine_v117`,
`test_strength_models_v115`— siguen en verde porque no afirman nada
sensible a la degeneración.

**Por qué no se tocaron**: cambiar cinco modelos que pasan movería números
que nadie ha pedido mover. Queda anotado para quien se lo encuentre.

---

## 3 · Diagnóstico fuera del runner que no reproducía el fallo

**Estado**: sin explicar.

Diagnosticando la caída de `test_support_increases_fos` (v0.1.84), un
script suelto que replicaba el test **línea por línea** daba el mismo
resultado en el árbol de trabajo y en HEAD, y habría llevado a la
conclusión contraria a la correcta. Instrumentando **dentro** del runner
apareció la diferencia real: HEAD 10 válidas y crítica 2,1279, árbol de
trabajo 0 válidas.

No se ha averiguado por qué el script suelto no reproducía. Mientras no se
sepa, **el diagnóstico se hace dentro del runner**, que es donde ocurre el
fallo.
