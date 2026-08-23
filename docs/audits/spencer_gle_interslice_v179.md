# Spencer y GLE devuelven prácticamente el valor de Bishop

**Estado: CERRADO en v0.1.106.** Eran **tres** defectos, no uno, y sólo uno de
los tres estaba nombrado correctamente antes de medirlo. El apartado de
**v0.1.106** los separa y publica la corrección; léase ése primero. Los de
**v0.1.90** (el alcance de λ) y **0.1.97** (la separación es CERO, no pequeña)
siguen siendo válidos y son los que llevaron hasta aquí. El resto del documento
se conserva tal como se escribió en v0.1.79 porque las mediciones siguen siendo
válidas; lo que cambia es qué explican — con una salvedad que el apartado de
0.1.97 detalla: las de la tabla del síntoma se tomaron a la tolerancia por
defecto y llevan ruido de parada dentro.

---

## ACTUALIZACIÓN v0.1.106 — eran TRES defectos, y la mitad de momentos estaba mal atribuida

Reproducido primero sobre 0.1.105 sin tocar nada, con los dos anclajes exactos
de Fredlund y Krahn (1977): en λ = 0 la rama de fuerzas **es** Janbu
simplificado (fuerzas interdovela horizontales, sin cortante: la misma
ecuación) y la rama de momentos **es** Bishop simplificado sobre un círculo.

| Problema | Bishop | Janbu simp. | Spencer | GLE | λ | F_f(0)/Janbu | F_m(0)/Bishop |
|---|---|---|---|---|---|---|---|
| 1 (ACADS 1a) | 0,986936 | 0,950307 | **0,986936** | **0,986936** | 0,68 | **0,774** | 0,977 |
| 3 (ACADS 1c) | 1,405251 | 1,291785 | **1,405251** | **1,405251** | 1,05 | **0,700** | 0,961 |
| 6 (Talbingo) | 2,208783 | 1,949617 | **2,208783** | **2,208783** | 1,08 | **0,794** | 0,979 |
| 8 (no circular) | 1,229727 | 1,208040 | **1,229727** | **1,229727** | 1,44 | **0,497** | 1,017 |

Spencer y GLE valen Bishop a seis cifras en los cuatro, incluido el problema 8,
que desde v0.1.105 ya **no** pasa por la guarda `circle_R`: quitar esa guarda no
tocó nada de esto.

### (A) La rama de fuerzas llevaba `cos α` donde va `sec α`

`spencer.py:381` y `gle.py:415`. Ya estaba escrito en `PENDIENTES.md` §9 desde
v0.1.98. El equilibrio horizontal del conjunto con X = 0 lo cierra sin margen:

```
N = (W − S·senα)/cos α          (equilibrio vertical de la dovela)
Σ N·senα = Σ S·cos α            (equilibrio horizontal del conjunto)
  ⇒  F · Σ W·tanα = Σ S_term·sec α
```

y `Σ S_term·secα / Σ W·tanα` **es** Janbu simplificado, término a término,
porque `n_α = cos α · m_α`.

### (B) Las dos ramas compartían UNA sola F — y esto no estaba nombrado en ninguna parte

`_inner_solve` iteraba `new_F = 0.5·(new_fm + new_ff)` y evaluaba `m_α` con esa
media. Ninguna de las dos ramas era, por tanto, su propio punto fijo: `F_m` se
calculaba con la `m_α` de un factor que no era `F_m`.

**Eso, y no `m_α` sin λ, es la causa entera del `F_m(0)/Bishop = 0,961–0,979`.**
El defecto D10 del banco lo venía atribuyendo desde el 2026-08-20 a que «λ no
llega a la normal en la base», y esa atribución es falsa para la mitad de
momentos: **en λ = 0 no hay cortante interdovela**, así que `m_α` sin λ y
`W_eff` sin `X` son las expresiones correctas ahí. Es el mismo error de
razonamiento que la regla 6 registra para `m_alpha` en v0.1.82: una medición
correcta sosteniendo una explicación equivocada.

Con (A) y (B) corregidos y nada más, las dos identidades salen **exactas a ocho
cifras** en los problemas 1, 3 y 6, y también con presión intersticial:

```
F_f(0)/Janbu  = 1,00000000        F_m(0)/Bishop = 1,00000000
```

### (C) La normal en la base omitía (X_R − X_L)

Éste sí es el que decía D10, y es el de fondo. **Arreglar (A) y (B) no
basta**: la rama de momentos seguiría sin contener λ por ninguna parte, `F_m(λ)`
sería constante, y la raíz `F_f = F_m` volvería a aterrizar exactamente sobre
Bishop. Es lo que el apartado de 0.1.97 de este mismo documento ya demostraba
desde el código.

La forma completa de Fredlund y Krahn (1977) —recursión horizontal de `E`,
`X_i = λ·f(x_i)·E_i`, y `N = [W + (X_R − X_L) − (c'l − u·l·tanφ')·senα/F] / m_α`—
reproduce los valores publicados:

| Problema | Bishop OGR | **Spencer** | publicado | error | separación OGR | separación publicada |
|---|---|---|---|---|---|---|
| 1 | 0,986936 | **0,986078** | 0,986 | **+0,01 %** | −0,09 % | −0,10 % |
| 3 | 1,405251 | **1,374693** | 1,375 | **−0,02 %** | −2,17 % | −2,14 % |
| 6 | 2,208783 | **2,292801** | 2,292 | **+0,03 %** | +3,80 % | +3,80 % |

Y con agua, que es donde este documento medía CERO separación
(`Ej_2_Piezometric_Line`, círculo de referencia de la propia referencia):

| | Bishop | Spencer | separación |
|---|---|---|---|
| referencia | 0,674931 | 0,687672 | **+1,888 %** |
| OGR 0.1.105 | 0,673203 | 0,673203 | **+0,000 %** |
| **OGR 0.1.106** | 0,673203 | **0,685984** | **+1,898 %** |

λ pasa de 0,68–3,21 a **0,39–0,63**. Las dos ampliaciones del rango de λ
—a ±1,5 en v0.1.74 y a +6 en v0.1.90— perseguían raíces que sólo estaban lejos
porque `F_f` venía deprimido por (A). Se conservan: no estorban, y ahora se
sabe qué eran.

### Lo que se movió en el banco de verificación

60 de sus problemas declaran Spencer o GLE, y se han vuelto a correr los 60.

| | antes | **ahora** |
|---|---|---|
| problemas con un método de λ enteramente `OK` | 12 | **15** |
| de ellos corroborados sobre el círculo publicado | 8 | **11** |
| problemas del banco enteramente `OK` (de 77) | 16 | **20** |

Sobre la superficie publicada —que aísla el método de la búsqueda— de 40
valores comparables con su publicado, **28 mejoran** y 12 empeoran; once de
esos doce por menos de 0,75 puntos. El duodécimo es el problema 12, y no es de
esta corrección: su Bishop ya erraba **+21 %** porque la grieta de tracción seca
no trunca el arco (defecto D13 del banco, abierto), así que la masa analizada no
es la del enunciado y su separación no es comparable con la publicada.

El desplazamiento número a número está en
`_auditoria/DESPLAZAMIENTO_v1106.md` del banco, con una advertencia que costó
una lectura equivocada: el base de esa resta **no es 0.1.105** sino la versión en
que cada caso se corrió por última vez, y 52 de 60 eran de 0.1.97. Por eso el
informe mide además la **separación respecto de Bishop**, que cancela la deriva
común porque Bishop se recorre en la misma corrida.

### Lo que sujeta esto de aquí en adelante

`tests/test_gle_interslice_v1106.py`, con cuatro identidades analíticas —la
mejor clase de test que admite este proyecto— y ninguna instantánea:

| | identidad | fuente |
|---|---|---|
| I1 | `F_f(λ=0)` ≡ Janbu simplificado | Fredlund y Krahn (1977) |
| I2 | `F_m(λ=0)` ≡ Bishop simplificado (circular) | íd. |
| I3 | `F_f(λ)` ≡ el motor de inclinación prescrita con θ = arctan λ, **para todo λ** | Spencer (1967) es Modified Swedish con θ resuelto en vez de prescrito |
| I4 | GLE con `f(x) ≡ 1` ≡ Spencer | Fredlund y Krahn (1977) |

I3 es la más fuerte: ese motor está validado término a término contra el
ejemplo resuelto de **USACE EM 1110-2-1902 apéndice G**, así que la rama de
fuerzas de Spencer queda anclada a un caso publicado dovela a dovela. Medida a
< 1,5·10⁻⁹ en λ = 0 / 0,2 / 0,43 / 0,8.

---

## ACTUALIZACIÓN v0.1.90 — el problema no era la formulación, era el alcance

Este documento llevaba once versiones buscando el fallo en la formulación
interdovela. La auditoría por círculo de v0.1.89 —67 837 valores de
referencia, no catorce— apuntó a otro sitio, y v0.1.90 lo confirmó midiendo.

**Lo que ya no encajaba.** Donde Spencer y GLE convergen, son **los dos
métodos más exactos del programa**: p99 de 0,62 % y 0,67 % en Ej_1, contra el
11-14 % de Fellenius y Janbu, y el 100,0 % de los círculos de GLE dentro del
1 %. Si la ecuación estuviera mal, ahí es donde se vería.

**Lo que sí fallaba: convergían en muy pocos.** El λ se busca muestreando un
grid y localizando el cambio de signo de `F_f(λ) − F_m(λ)`. El grid **paraba
en ±1,5**, y para las superficies difíciles `F_f − F_m` es monótona y sigue
negativa ahí. «Sin cambio de signo» nunca quiso decir «no hay raíz»: quería
decir que estaba fuera de alcance.

```
λ = 1,500   F_f 0,7351   F_m 1,0551   F_f−F_m = −0,320
λ = 2,994   F_f 1,1257   F_m 1,1262   F_f−F_m = −0,0005   <-- la raíz
```

La referencia no restringe λ por defecto: sus modelos traen `min_lambda: -0.1`
y `max_lambda: 6` con las casillas de aplicación **desmarcadas**.

**Efecto, sobre las mismas rejillas de referencia** (círculos que la
referencia resuelve y este programa abandonaba):

| | v0.1.89 | v0.1.90 |
|---|---|---|
| Ej_1 spencer | 2301 / 3237 = 71,1 % | **3065 = 94,7 %** |
| Ej_1 gle | 1908 / 3222 = 59,2 % | **2800 = 86,9 %** |
| Ej_2 spencer | 2115 / 3047 = 69,4 % | **2921 = 95,9 %** |
| Ej_2 gle | 1708 / 3141 = 54,4 % | **2695 = 85,8 %** |

**Qué queda de la hipótesis original.** El síntoma que abrió este documento
—que sobre un círculo dado Spencer y GLE se separan de Bishop mucho menos de
lo que dicen las referencias publicadas— **no queda explicado por esto**, y
las tablas de abajo siguen en pie. Lo que cambia es que ya no se puede
atribuir a «la formulación está mal» sin más: ahora sabemos que una parte
grande de la población nunca llegaba a resolverse, y que la que se resolvía
salía muy bien. Antes de seguir buscando en la ecuación hay que **rehacer la
comparación con Bishop sobre la población completa**, que hasta v0.1.90 no
existía.

---

## ACTUALIZACIÓN 0.1.97 — la separación no es pequeña, es CERO, y la que se veía era ruido de parada

Esta salió de otro sitio: de medir el defecto **D03c** del banco de
verificación, que preguntaba si la tolerancia de parada (0,005, absoluta sobre
el factor de seguridad) explicaba la banda de resultados marcados `REVISAR`.
No la explica —el efecto máximo es 0,155 % contra un `REVISAR` mínimo de
2,17 %— pero al medirlo aparece esto.

**Lo que este documento no había hecho nunca.** Arriba, en «Lo que NO es», se
lee «no es falta de convergencia», y se sostenía sólo sobre `converged` a
True. **Nadie había variado la tolerancia.** Con Spencer parando su búsqueda de
λ sobre el residuo `|F_f − F_m| < tol` y devolviendo `(F_f + F_m)/2`, una
tolerancia de 0,005 acota ese residuo a la mitad: **±0,0025, o ±0,18 % sobre
un FoS de 1,4** — el mismo orden que las separaciones que este documento
llevaba once versiones citando.

**Medido a 10⁻⁷, sobre el mismo círculo**, en los cinco modelos que el banco
usa para esto:

| Modelo | círculo | Bishop | Spencer | separación |
|---|---|---|---|---|
| ACADS 1(c) | (34,121 · 43,254) R 18,781 | 1,405090162 | 1,405090142 | **−0,000001 %** |
| ACADS 1(d) | (35,0 · 53,75) R 29,564 | 1,016579644 | 1,016579628 | **−0,000002 %** |
| Arai & Tagyo ej.2 | (26,264 · 52,042) R 38,046 | 0,421359426 | 0,421359422 | **−0,000001 %** |
| Duncan & Wright | (500,0 · 172,5) R 170,053 | 1,239159044 | 1,239159035 | **−0,000001 %** |
| Duncan & Wright | (54,2 · 50,0) R 49,889 | 1,235635348 | 1,235635337 | **−0,000001 %** |

GLE da lo mismo. Las fuentes separan Spencer de Bishop entre un 1,7 y un 2,6 %
en estos mismos problemas.

**Dos cosas cambian con esto.**

1. **El síntoma era más grave de lo que este documento decía.** La tabla de
   arriba registra «OGR: Spencer −0,065 %» y «−0,02 %», y se leía como *una
   separación pequeña*. **No era una separación pequeña: era ruido de
   parada.** A tolerancia suficiente el residuo se va y queda cero exacto, a
   siete cifras. Un número que se estaba interpretando como señal era el
   criterio de parada.

2. **La causa deja de ser una sospecha y pasa a ser demostrable desde el
   código**, sin necesidad de medir nada: en `spencer.py` la rama de momentos

   ```python
   S_term = (c_loc * b + (W_eff - u * b) * tan_phi) / m_alpha   # sin lam
   num_m += S_term
   den_m += W_eff * math.sin(alpha)                             # sin lam
   new_fm = num_m / den_m
   ```

   **no contiene λ por ninguna parte** — `m_alpha` tampoco. En la raíz, donde
   `F_f = F_m`, ambas ramas comparten la `F` de la iteración interna, así que
   ese valor común satisface exactamente la ecuación de punto fijo de Bishop.
   λ decide **dónde** se cruzan las dos ramas; no puede mover el valor en que
   se cruzan. Para una superficie circular, Spencer tal como está escrito es
   **incapaz** de dar algo distinto de Bishop.

   Eso confirma la sospecha 1 de «Lo que sí hace falta mirar» y **cierra la
   sospecha 2**: el cruce `F_f = F_m` sí se resuelve, y sí es cierto que «no
   significa nada», pero no porque el criterio esté mal — porque la rama de
   momentos es constante en λ por construcción.

**Y la nota sobre las tolerancias dobles de `test_slide_validation_ej1.py`
sigue en pie, con un matiz.** Los errores de 0,64 % y 0,53 % que se les
concedían se midieron a la tolerancia por defecto, así que **parte de esos
números era ruido de parada** y no error de formulación. Cuando se corrija el
fondo, la revalidación tendrá que hacerse a tolerancia estrecha para que la
comparación mida la ecuación y no el criterio de parada.

**Lo que protege esto de aquí en adelante**:
`tests/test_convergence_tolerance_v198.py`. Fija que apretar la tolerancia no
mueve el punto fijo más de lo que su mecanismo predice — y **deliberadamente
no fija** que los cuatro métodos coincidan a 10⁻⁷, porque eso es el síntoma de
este documento y consagrarlo en un test sería exactamente lo que prohíbe la
regla 1.

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

> **v0.1.106**: hecho. Las dos bajaron a 0.5 %, y pasan. La asimetría
> desapareció con la causa que la producía, que es la única manera legítima de
> quitar una tolerancia doble.

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

> **v0.1.106**: ese día llegó. ACADS 1(a) sale 0.986078 y 0.986059 contra el
> 0.986 publicado; ACADS 1(c), 1.374693 y 1.374028 contra 1.375 y 1.374. Los
> `esperado.json` de los casos 002, 003 y 004 pueden escribirse ya, y con la
> **fuente publicada** como valor esperado — no con lo que imprime el código,
> que es lo que la regla 1 prohibía y por lo que llevaban vacíos.
