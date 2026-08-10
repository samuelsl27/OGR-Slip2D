# Spencer y GLE devuelven prácticamente el valor de Bishop

**Estado: reportado, NO corregido.** Regla 6. Este documento es la evidencia;
el arreglo, si lo hay, va en su propia versión con su propia validación.

Encontrado en v0.1.79, al añadir los casos de validación publicados. No es un
fallo introducido por ese trabajo: es un comportamiento que llevaba desde
siempre y que **ningún test podía ver**, por el motivo que se explica al
final.

---

## El síntoma

Sobre un círculo dado, Spencer y GLE/Morgenstern-Price devuelven un factor de
seguridad que coincide con el de Bishop simplificado hasta la tercera o
cuarta cifra. Las referencias publicadas los sitúan **por debajo** de Bishop.

### Ej_1, sobre el círculo de mínimo global de la referencia (88, 70.5) R 47.212

| Método | OGR | Referencia | Error |
|---|---|---|---|
| Bishop simplificado | 0.883074 | 0.882889 | **+0.02 %** |
| Spencer | 0.882498 | 0.876917 | +0.64 % |
| GLE / Morgenstern-Price | 0.883003 | 0.878343 | +0.53 % |

Separación respecto a Bishop, sobre ese mismo círculo:

```
    referencia:   Spencer −0.68 %      GLE −0.51 %
    OGR:          Spencer −0.065 %     GLE −0.008 %
```

### ACADS 1(c), sobre el círculo crítico publicado (34.121, 43.254) R 18.781

Este es el caso más limpio, porque **la geometría está verificada de forma
independiente**: sobre ella, ese círculo corta el terreno en x = 29.703 y
50.991 frente a los 29.702 y 50.991 publicados. Un milímetro. No cabe
atribuir la diferencia a un modelo distinto.

| Método | OGR | Publicado | Error |
|---|---|---|---|
| Bishop simplificado | 1.4068 | 1.405 | **+0.13 %** |
| Spencer | 1.4065 | 1.375 | **+2.29 %** |
| GLE / Morgenstern-Price | 1.3930 | 1.374 | +1.38 % |
| Janbu corregido | 1.3798 | 1.357 | +1.68 % |

```
    referencia:   Spencer −2.1 % respecto a Bishop
    OGR:          Spencer −0.02 %
```

**El patrón es el mismo en los dos modelos y en la misma dirección**, y su
tamaño escala con lo que la referencia separa los métodos: donde la
referencia separa un 0.7 %, nosotros nos quedamos en 0.07 %; donde separa un
2.1 %, nos quedamos en 0.02 %.

Es decir: **la contribución de la fuerza de cortante entre dovelas está
llegando al resultado con un peso muy inferior al que debería**, o no está
llegando. Spencer y GLE comparten la maquinaria de λ, lo que es coherente con
una única causa común.

---

## Lo que NO es

Conviene descartarlo por escrito, porque cada una de estas hipótesis parecía
la explicación y ninguna lo es.

**No es una diferencia de búsqueda.** Todos los números de arriba están
evaluados sobre el **mismo círculo**, dado explícitamente, sin buscar.

**No es la geometría.** En ACADS 1(c) la entrada y la salida del círculo
publicado se reproducen con error de 1 mm sobre 21 m de cuerda.

**No es que λ esté clavado.** Fue mi primera sospecha, al ver λ = 1.046662 en
ACADS 1(c) y λ = 1.046603 en Ej_1 — dos modelos sin nada en común coincidiendo
en cinco cifras. Es casualidad: barriendo cinco círculos distintos del mismo
modelo, λ recorre 1.0278, 1.0466, 1.0707, 1.0957. **λ sí depende del
círculo.** La hipótesis era razonable y era falsa.

**No es falta de convergencia.** En los casos de arriba `converged` es True.

---

## Lo que sí hace falta mirar

En orden de sospecha:

1. **Cómo entra λ·f(x) en el equilibrio de momentos.** Que Spencer converja a
   Bishop es exactamente lo que pasa cuando el término de cortante entre
   dovelas se anula o casi. Para superficies circulares Bishop y Spencer
   *deben* parecerse —es un resultado clásico, Duncan & Wright—, pero
   parecerse un 0.02 % cuando la referencia da un 2.1 % no es parecerse: es
   no estar.
2. **El criterio de cruce Ff = Fm.** `spencer.py` busca λ tal que el factor de
   fuerzas y el de momentos coincidan. Si el de momentos es insensible a λ, el
   cruce se resuelve pero no significa nada, y λ acaba donde acabe.
3. **Un caso más, ya medido**, para descartar que sea propio de dos modelos:
   en Arai & Tagyo (1985) ejemplo 1 la referencia separa Spencer de Bishop
   solo un 0.2 % — y ahí sí coincidimos (Spencer 1.4142, Bishop 1.4146). Es
   decir, **acertamos justo donde no hay nada que acertar**.

---

## Por qué ningún test lo veía

Esta es la parte que más merece recordarse.

`tests/test_slide_validation_ej1.py` valida los siete métodos sobre el
círculo de referencia, con una tolerancia por método:

```python
("ordinary_fellenius",     0.849535, 0.5),
("bishop_simplified",      0.882889, 0.5),
("janbu_simplified",       0.842548, 0.5),
("janbu_corrected",        0.883036, 0.5),
("spencer",                0.876917, 1.0),   # <-- el doble
("gle_morgenstern_price",  0.878343, 1.0),   # <-- el doble
```

Los errores reales son 0.64 % y 0.53 %: **por debajo del 1 % que se les
concede, y por encima del 0.5 % que se le exige a todo lo demás.** El test
pasa, y lleva pasando desde v0.1.19.

La tolerancia doble no se documentó nunca como una decisión. Vista ahora, la
asimetría *era* el hallazgo: los dos únicos métodos que necesitaban el doble
de margen son exactamente los dos que comparten la maquinaria de λ. Una
tolerancia que se afloja para que un test pase deja de medir el código y pasa
a medir la paciencia de quien la puso.

**Nada de esto se ha tocado.** Estrechar esas tolerancias ahora convertiría
un test verde en uno rojo sin arreglar nada, y los casos de validación no se
tocan para que pasen ni para que fallen. Cuando se corrija el fondo, las dos
tolerancias deberían bajar a 0.5 % como las demás, y ese será el test de que
la corrección funcionó.

---

## Consecuencia inmediata

Los casos `002`, `003` y `004` de `validacion/casos/` **no declaran Spencer ni
GLE** en su `esperado.json`, aunque las tres fuentes publican valores para
ellos. Escribirlos con los números que hoy salen consagraría el
comportamiento que está en duda, que es precisamente lo que la regla 1
prohíbe:

> Nunca una captura de lo que el código imprime hoy: un test de instantánea
> consagra el bug.

Los valores publicados quedan aquí anotados, listos para el día que se
arregle:

| Caso | Spencer | GLE |
|---|---|---|
| Ej_1 | 0.876917 | 0.878343 |
| ACADS 1(a) | 0.986 | 0.986 |
| ACADS 1(c) | 1.375 | 1.374 |
| Arai & Tagyo ej.1 | 1.406 | — |
