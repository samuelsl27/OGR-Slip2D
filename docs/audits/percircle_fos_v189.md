# OGR contra la referencia en los 9691 círculos, no sólo en el crítico

**Estado: reportado, NO corregido.** Regla 6. Este documento es la evidencia de
dos divergencias que sólo se ven mirando la población entera; el arreglo, si lo
hay, va en su propia versión con su propia validación.

Ejecutado una vez, fuera de la suite, tras cerrar la regla de radios en
v0.1.88.

---

## 1 · Por qué existe

Todas las validaciones numéricas del proyecto comprueban **un** círculo: el de
mínimo global de la referencia. Eso fija la formulación en un punto, y v0.1.88
demostró de la peor manera lo que un punto no ve — durante ochenta versiones
los siete métodos coincidían al 0,26 % sobre ese círculo mientras el programa
ni siquiera lo generaba.

El `.s01` de la referencia lleva el factor de seguridad **de los siete
métodos** para **cada** círculo generado: 4851 × 7 en Ej_1 y 4840 × 7 en Ej_2,
67 837 valores de referencia. Comparar contra eso es comparar la población.

Un valor negativo en el `.s01` es un código de error de la referencia (−103
superficie fuera del contorno, −108 sin convergencia, −111…), no un factor de
seguridad; esos círculos se excluyen de los estadísticos y se cuentan aparte.

## 2 · Toda la población

| | Ej_1 | Ej_2 |
|---|---|---|
| círculos | 4851 | 4840 |
| valores de referencia | 33 957 | 33 880 |
| error mediano, los 7 métodos | +0,007 % a +0,068 % | −0,020 % a +0,075 % |
| p90 \|error\| | 0,35 % a 1,54 % | 0,38 % a 1,47 % |

El error **mediano** sobre miles de círculos está por debajo del 0,08 % en las
catorce combinaciones método × modelo. Eso es un resultado y conviene decirlo
antes de los problemas: la formulación no está sostenida por un solo círculo
afortunado.

## 3 · El error máximo no significa lo que parece

El máximo bruto llega a **8,7 · 10¹¹ %**, que invita a conclusiones
equivocadas. No hay ningún caso de «referencia ≈ 0»: el factor de seguridad de
la propia referencia va de 0,88 a **902** en Ej_1 y de 1,16 a **477** en Ej_2.
Los atípicos están todos en el extremo alto.

Un factor de seguridad de 902 no es un resultado de estabilidad de taludes: es
una astilla de círculo casi sin momento motor, un 0/0 numérico. Ninguno de los
dos programas lo reporta jamás — `GridSearch.run` descarta todo lo que caiga
fuera de [0,2 , 100].

Así que la medida útil es la **restringida a los círculos con FoS de
referencia < 3**, que es el rango que alguien mira:

### Ej_1 — círculos con 0 < FoS de referencia < 3

| método | círculos | OGR converge | mediana | p90 | p99 | dentro del 1 % |
|---|---|---|---|---|---|---|
| ordinary/fellenius | 2426 | 2426 | +0,025 % | 0,285 % | 11,1 % | 95,9 % |
| bishop simplified | 2255 | 2255 | −0,006 % | 0,355 % | 3,59 % | 95,0 % |
| janbu simplified | 2442 | 2442 | +0,066 % | 1,047 % | 14,0 % | 89,6 % |
| janbu corrected | 2380 | 2380 | +0,064 % | 0,992 % | 14,2 % | 90,1 % |
| spencer | 2247 | **1756** | +0,109 % | 0,338 % | 0,617 % | 99,8 % |
| lowe-karafiath | 1802 | 1802 | +0,053 % | 0,738 % | 1,645 % | 94,0 % |
| gle/morgenstern-price | 2236 | **1429** | +0,103 % | 0,347 % | 0,665 % | 100,0 % |

### Ej_2 — círculos con 0 < FoS de referencia < 3

| método | círculos | OGR converge | mediana | p90 | p99 | dentro del 1 % |
|---|---|---|---|---|---|---|
| ordinary/fellenius | 2500 | 2500 | +0,027 % | 0,357 % | 13,6 % | 95,5 % |
| bishop simplified | 2238 | 2238 | −0,017 % | 0,332 % | 3,88 % | 96,6 % |
| janbu simplified | 2511 | 2511 | +0,069 % | 0,918 % | 20,1 % | 90,6 % |
| janbu corrected | 2428 | 2428 | +0,065 % | 0,805 % | 16,8 % | 91,7 % |
| spencer | 2164 | **1658** | +0,099 % | 0,415 % | 0,818 % | 99,3 % |
| lowe-karafiath | 1640 | 1640 | −0,032 % | 0,616 % | 1,832 % | 96,2 % |
| gle/morgenstern-price | 2232 | **1271** | +0,070 % | 0,384 % | 0,685 % | 99,4 % |

---

## 4 · Hallazgo A — Spencer y GLE: el problema es la CONVERGENCIA, no la precisión

Es la vuelta de tuerca que la población da y el círculo único no daba.

`docs/audits/spencer_gle_interslice_v179.md` está abierto porque Spencer y GLE
se separan de Bishop mucho menos de lo que las referencias publicadas dicen.
Esa auditoría los mide sobre círculos concretos. Sobre la población aparece
algo distinto y más concreto:

**Donde convergen, Spencer y GLE son los DOS MÉTODOS MÁS EXACTOS del programa.**
p99 de 0,62 % y 0,67 % en Ej_1 frente al 11-14 % de Fellenius y Janbu; el
100,0 % de los círculos de GLE dentro del 1 %.

**Pero convergen en muy pocos:**

| | Ej_1 | Ej_2 |
|---|---|---|
| spencer | 1756 / 2247 = **78 %** | 1658 / 2164 = **77 %** |
| gle/morgenstern-price | 1429 / 2236 = **64 %** | 1271 / 2232 = **57 %** |

Sobre la población completa, los círculos donde la referencia da número y OGR
no: Spencer 936 y GLE **1433**. La referencia converge donde OGR se rinde, en
casi un tercio de los casos de GLE.

Eso reorienta la auditoría v0.1.79. Si la hipótesis fuera «la formulación
interdovela está mal», los círculos donde converge tendrían que salir mal, y
salen **mejor que ningún otro método**. La lectura que los datos apoyan es que
el solver abandona los casos difíciles y que el sesgo hacia Bishop puede venir
de qué círculos sobreviven, no de la ecuación. Es una hipótesis, no una
conclusión, y esta auditoría no la resuelve.

## 5 · Hallazgo B — la cola del 1 % en Fellenius y Janbu, y son DOS causas

Mediana excelente y p99 de 11-20 %: en torno al 1 % de los círculos falla
mucho. Caracterizados, no son un fenómeno sino dos.

### B1 · Ej_2: masas deslizantes distintas (6 círculos, medido)

Los seis peores de Ej_2 son los mismos en los cinco métodos que los analizan,
con el mismo error (48,6-48,9 % el peor). Centros muy altos sobre el modelo
(y = 114 a 135) y radios grandes (73 a 99 m).

Contados los cortes con el terreno, la causa es directa:

```
centro (−3,333 , 135,000) r = 98,637
  4 cortes con el terreno, en x = 25,75 · 54,37 · 56,86 · 70,86
  OGR analiza  x de 25,75 a 54,37   ->  FoS 1,507
  la referencia                     ->  FoS 2,949
```

Cuatro cortes son **dos masas deslizantes disjuntas**, y los dos programas
analizan masas distintas: OGR la primera, la referencia (por el valor) la
segunda. Es el invariante 2 de v0.1.84 — «la crítica es la que se analiza» —
visto desde el otro lado: aquí la referencia **no** parece quedarse con la más
crítica.

No se corrige. Cambiar la selección de masa movería el mínimo global de Ej_2,
que es un caso validado, y estos seis círculos tienen FoS 2,6-2,9: ninguno es
ni será la superficie crítica. Antes de tocarlo hay que saber cuál es la regla
de la referencia, y para eso hace falta un modelo hecho a propósito con un
círculo de cuatro cortes y las dos masas medidas por separado.

### B2 · Ej_1: NO es selección de masa. Sin explicar

La misma hipótesis, comprobada sobre los peores de Ej_1, **falla**:

```
centro (80,0 , 34,5) r = 30,997   ->  2 cortes, en x = 52,07 y 109,52
centro (64,0 , 30,0) r =  6,842   ->  2 cortes, en x = 63,20 y  70,80
```

Dos cortes es una sola masa. Son 49 círculos con FoS de referencia 1,78-2,90 y
centros **bajos** (y = 30 a 39, por debajo de la coronación en y = 50); OGR da
sistemáticamente **más** que la referencia (2,70 → 3,83 el peor), al contrario
que en Ej_2, donde daba menos.

Una pista sin seguir, anotada porque es lo primero que habría que mirar: para
ese círculo, el `x_left` que devuelve `evaluate_circle` es **49,003**, que es
exactamente `centre_x − r`, el extremo izquierdo del círculo — mientras que
llamar a `intersect_with_ground` sobre la misma geometría da **52,066**. Los
dos caminos no coinciden, y 3 m de diferencia en la entrada explicarían sobrar
un 25 %. Puede ser un artefacto de cómo se rellena el objeto y no un error de
cálculo; no se ha comprobado.

## 6 · Círculos que la referencia descarta y OGR no

Hasta **975** en Ej_2 (Bishop). Son círculos con código de error en el `.s01`
que OGR sí analiza. No están medidos uno a uno y no se afirma nada sobre
ellos: hacen falta las tablas de códigos de la referencia para saber si el
motivo del descarte es uno que OGR debería aplicar. Queda anotado como lo que
es, un recuento sin diagnóstico.

Al revés, OGR se rinde donde la referencia no en 3 a 16 círculos de los
métodos de momentos — despreciable— y en los cientos de Spencer/GLE del
hallazgo A.

---

## 7 · Reproducir

Los scripts no se guardan en el repositorio: son de un solo uso y dependen de
`referencias/`, que no forma parte de él. Lo que hace falta saber para
reescribirlos:

- Los `.slim` son ZIP; dentro, el `.s01` es texto.
- Tras `*   all circles (r,yleft,x1,y1,x2,y2,yright,fs...,b1)`, cada centro es
  una línea `xc yc n` seguida de `n` líneas de círculo. Los campos 8 a 14 son
  los factores de seguridad **en el orden del bloque «Analysis names»**:
  ordinary/fellenius, bishop, janbu simplified, janbu corrected, spencer,
  lowe-karafiath, gle/morgenstern-price.
- Un valor negativo es código de error, no factor de seguridad.
- Comparar con `GridSearch.evaluate_circle` sobre `SlipCircle(xc, yc, r)`, 25
  dovelas, sin comprobación de m-alpha (para no mezclar el filtro con la
  comparación).
- Filtrar por el FoS **de la referencia** antes de evaluar abarata el trabajo
  sin sesgar nada: el criterio no depende de lo que calcule OGR.

Coste: unos 25 minutos para las catorce combinaciones. Fuera de la suite, que
no puede pagar eso.
