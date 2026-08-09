# OGR Slip2D v0.1.71 — el tope drenado converge siempre, y se nota cuando no

Lo que v0.1.70 dejó anotado: *«8–12 de 185 superficies agotan las 20
pasadas, pero ninguna se acerca a la crítica»*. Investigado, el enunciado
era cierto y **el problema era peor de lo que sugería**: no era falta de
presupuesto, era que allí no había punto fijo al que llegar.

Y la causa de fondo resultó ser **una constante que elegí midiendo sobre
una muestra que excluía justo los casos malos**.

---

## 1. El mecanismo: un ciclo de periodo 2 en una sola dovela

El tope drenado es un punto fijo: topar una dovela baja el FS → cambian
las normales de base → cambia el tope. En esas superficies **una sola
dovela de 25 —la última, en el extremo de coronación— alternaba entre
topada y sin topar**:

```
pasada   FS        tau_actual   tau_objetivo   tau_no_drenada
   1   1.25861       275.19        107.43         275.19   <- topada a fondo
   2   1.24473       157.76        275.19         275.19   <- ya no topa
   3   1.25445       239.96        172.63         275.19
   4   1.24887       192.83        260.53         275.19
```

Y la amplitud **crecía** (240.2 → 240.5 → 240.8 → 241.0 → 241.3 → 241.6):
con ω = 0.70 ese punto fijo era **repulsor**. Iterar más no arreglaba
nada, y por eso el presupuesto de 20 pasadas no era el problema.

### Por qué esa dovela: m-α

Es la del extremo de coronación, con la base a 67°–74°. En Bishop
`N = [W − c·l·sinα/F] / m_α`, así que un m-α pequeño amplifica `dN/dF`, y
el tope drenado cierra el lazo `τ ← f(N(F))`. Contrastado con
`base_m_alphas`, que ya existía en `ogr_slip2d/checks.py`:

| Superficies | m-α mínimo (siempre la dovela 24 de 25) | Pasadas |
|---|---|---|
| Que oscilaban | **0.446 – 0.716** | 20 |
| Que convergían | **0.963 – 1.046** | 0 – 4 |

Separación limpia, sin solape. Pero **muy por encima del límite 0.2 de
Whitman y Bailey**, así que la comprobación de m-α existente tampoco las
habría detectado — y además está desactivada por defecto por una razón
documentada: bajarla rechazaría el círculo crítico validado de
Pilarcitos.

---

## 2. Por qué importaba, aunque ningún resultado publicado cambiara

**El FS reportado dependía de la paridad del tope de pasadas:**

| `CAP_MAX_PASSES` | 17 | 18 | 19 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|
| FS | 1.24865 | 1.25470 | 1.24862 | **1.25474** | 1.24858 | 1.25477 |

Un **0.50 % decidido por que 20 sea par**. Ninguna de esas superficies
era crítica en Pilarcitos; nada garantizaba eso en otro modelo.

Y **refinar el rebanado no ayudaba**: la misma superficie seguía atascada
de 25 a 150 dovelas, con el FS vagando entre 1.2401 y 1.2737 — un
**2.7 %**. No era un artefacto de discretización sino una propiedad del
sistema acoplado en esa superficie.

---

## 3. La constante estaba mal elegida, y así se eligió mal

La tabla que justificó ω = 0.70 en v0.1.70 tiene **todas sus columnas
sobre la superficie crítica**, que converge en 4 pasadas con cualquier
amortiguación. Las que no convergían estaban en otra parte de la
rejilla. Sobre la rejilla entera (729 candidatos, 185 válidas) la imagen
se invierte:

| ω | Pasadas DWW | Sin converger | Pasadas Corps | Sin converger | FS crítico |
|---|---|---|---|---|---|
| 0.70 (v0.1.70) | 515 | **8** | 613 | **12** | 1.0847 / 0.8383 |
| **0.50** | 365 | 0 | 381 | 0 | 1.0847 / 0.8383 |
| 0.35 | 453 | 0 | 441 | **1** | 1.0847 / 0.8383 |

**No es monótono** — con 0.35 reaparece una — así que un ω fijo es frágil
por construcción y cambiar la constante sola no bastaba.

Esa es la lección que merece recordarse: *la constante se validó con la
misma muestra con la que se eligió*. La tabla parecía una medición
cuidadosa y era una tautología.

---

## 4. Lo que se ha hecho

**Amortiguación adaptativa.** ω por defecto a 0.50, y **halvado cuando el
FS cambia de dirección entre pasadas**, con suelo en 0.05. Una inversión
de signo es la firma del ciclo de periodo 2, y halvar lo colapsa. ω pasa
a ser variable local del bucle, no constante global, para que una
superficie difícil no contamine a la siguiente (regla 5).

**Nunca se devuelve un iterado arbitrario.** Si aun así se agota el
presupuesto, se devuelve la **media de las dos últimas pasadas** — el
centro del ciclo, que no depende de la paridad, que era el defecto
concreto.

**Se reporta cuando no converge.** `DrawdownResult.cap_converged` y
`cap_min_m_alpha`, ambos también en `details`. El m-α solo se calcula en
ese caso, así que el camino normal no paga nada, y dice *por qué* no
convergió en vez de solo que no lo hizo.

**La dovela del extremo se documenta, no se toca.** La investigación
ampliada concluyó que no hay nada que arreglar en la geometría: refinar
no elimina el ciclo, el m-α de esas dovelas está muy por encima del
límite de rechazo, y tocar el rebanado afectaría a los siete métodos LEM
para resolver un problema del tope drenado.

---

## 5. Resultado

| | v0.1.70 | v0.1.71 |
|---|---|---|
| Pasadas totales, DWW | 515 | **349** (−32 %) |
| Pasadas totales, Corps | 613 | **353** (−42 %) |
| Superficies sin converger | 8 y 12 | **0 y 0** |
| Pilarcitos DWW / Corps | 1.0847 / 0.8383 | **igual** |
| Apéndice G Corps (árbitro 1.35) | 1.3494 | **1.3495** (−0.04 %) |
| Apéndice G DWW (árbitro 1.44) | 1.4456 | **1.4457** (+0.39 %) |

El arreglo **sale más barato que el fallo**: una superficie que no
converge quema el presupuesto entero cada vez, así que quitarlas ahorra
más de lo que cuesta amortiguar mejor. Es un recuento de trabajo, no de
reloj, así que vale aunque la máquina esté ocupada — que es la lección
que v0.1.70 aprendió a base de medir con la suite corriendo de fondo y
obtener dos controles que diferían un 173 %.

---

## Archivos

| Archivo | Qué cambia |
|---|---|
| `ogr_slip2d/rapid_drawdown.py` | Amortiguación adaptativa, media del ciclo, `cap_converged`, `cap_min_m_alpha` |
| `tests/test_rapid_drawdown_v168.py` | `TestTheCapCannotDependOnWhereItStopped`, y la independencia de ω extendida a una superficie que oscilaba |

## Lo que queda anotado

* **El suelo de ω = 0.05 no se ha puesto a prueba.** Ninguna superficie
  de los modelos que hay llega a bajar tanto, así que ese camino está
  escrito pero no ejercitado. Si algún modelo lo alcanza, lo que hay que
  mirar es si el problema es la amortiguación o la superficie.
* **`cap_converged` no llega a la interfaz.** Está en el resultado y en
  `details`, pero ni la ventana de interpretación ni el informe lo
  enseñan. Un usuario con una superficie que no converge hoy no se
  entera, y ese era medio motivo de añadir la bandera.
