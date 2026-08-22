# OGR Slip2D v0.1.98 — el hueco de dos métodos, y una tabla de 1970 que sabía la respuesta

El enum `LEMMethod` declaraba **nueve** métodos y el registro tenía **siete**.
Los dos que faltaban eran **Corps of Engineers #1 y #2**, el *Modified Swedish*.
Ya están, y con ellos se cierra el defecto **D31** del banco de verificación.

| Ej_1, círculo de referencia | FoS |
|---|---|
| Lowe-Karafiath | 0,885650 |
| **Corps of Engineers #1** | **0,885957** |
| **Corps of Engineers #2** | **0,893208** |

Lowe-Karafiath sale **bit a bit igual** que en 0.1.97, y eso es una
comprobación, no una casualidad: su motor se movió a un módulo compartido sin
tocar una sola operación.

Lo que no se esperaba encontrar está en §5 y §6, y una de las dos cosas **no se
ha corregido a propósito**.

---

## 1 · Qué son, y por qué el #2 no es lo que parecía

Los tres métodos de inclinación **prescrita** resuelven la misma recursión y
sólo discrepan en de dónde sale θ:

| | θ | ¿constante? |
|---|---|---|
| Lowe-Karafiath | ½·(β_i + α_i) | no |
| **Corps of Engineers #1** | la recta que une los dos extremos de la superficie | **sí** |
| **Corps of Engineers #2** | β_i, la pendiente del terreno **encima de cada dovela** | no |

El **#2 estuvo a punto de escribirse mal**. La descripción de partida era «la
pendiente media del terreno», que suena razonable y es lo que dice la EM
1110-2-1902 §C-4a de la hipótesis original del Corps —*«parallel to the average
embankment slope … usually taken to be the slope of a straight line drawn
between the crest and toe»*—, o sea una **constante**. Dos fuentes
independientes dicen que el #2 no es eso:

- la formulación de referencia de SLOPE/W tabula «*inclination of a line from
  crest to toe*» para el #1 y «*inclination of ground surface at top of slice*»
  para el #2, y añade la consecuencia que los separa: *«the interslice shear is
  zero when the ground surface is horizontal»*;
- la figura de la ayuda del programa de referencia para el #2 **dibuja las
  flechas cambiando de inclinación** de dovela a dovela: tumbadas bajo el
  terreno suave, empinadas bajo el talud. La del #1 las dibuja todas paralelas.

La lección no es la definición: es que la descripción plausible y la correcta
se parecían lo bastante como para que nadie mirara la figura. Un test lo fija
ahora, y con el criterio que de verdad los distingue —**#2 vale cero donde el
terreno es horizontal**—, no con un número.

Y la constante de la EM sí está implementada: es el **#1**, porque los dos
extremos de la superficie son la coronación y el pie cuando la superficie
aflora en ambos.

## 2 · Un motor, tres métodos

`ogr_slip2d/methods/modified_swedish.py` es nuevo y contiene
`PrescribedInclinationMethod`: la recursión, el buscador de raíz, la línea de
empujes y las fuerzas en la base. `lowe_karafiath.py` pasó de 321 líneas a 66 y
lo único que le queda propio es **una función de cinco líneas**, que es
exactamente cuánto se diferencian estos métodos entre sí.

Escribir la recursión tres veces habría sido la receta conocida: la misma que
dejó `janbu_corrected` marcable y sin resultado, y a Lowe-Karafiath gris
durante cincuenta y ocho versiones.

## 3 · Y la recursión resultó ser, literalmente, la de la EM

Al buscar la fuente para escribir el método nuevo apareció que **el motor que ya
había era el del manual**. Las ecuaciones C-19, C-20a-d y C-21 de la EM
1110-2-1902 son, término a término, el `_z_end` que Lowe-Karafiath tenía desde
v0.1.61, bajo el espejo α→−α, θ→−θ que `orient` aplica. Comprobados los cuatro:
el peso, el empuje entre caras, la carga de agua sobre la coronación de la
dovela —que OGR reparte en vertical y horizontal, y sale la misma fuerza— y el
término de cohesión.

`D⁻` en la recursión de OGR es la única diferencia, y es una generalización: con
θ constante `D⁻ = D_i` y la expresión **colapsa exactamente** en la del manual.

Eso convirtió una intención en una comprobación: el apéndice G de la EM publica
el cálculo **dovela a dovela** de un desembalse rápido resuelto a mano con hoja
de cálculo, con las columnas de fuerza entre dovelas y de normal en la base
impresas. Alimentando la recursión de OGR con esas doce dovelas publicadas:

| | OGR | manual |
|---|---|---|
| Fig. G-9, cierre en la última dovela a F = 1,35 | 5 kips | 0 kips |
| Fig. G-9, **factor de seguridad** | **1,3435** | **1,35** (−0,5 %) |
| Fig. G-7a, cierre a F = 3,49 | 11,6 kips | 10 kips |
| Fig. G-7b, columna de normal en la base | ±2,2 % | publicada |

Con θ = 0 el cierre de la G-9 sale **109** en vez de 0: **el ángulo lo
identifican los datos**, no se ha elegido para que cuadre. Ése es el detalle que
hace que la comprobación signifique algo.

El 1,35 no es un número cualquiera: es el que el manual de verificación cita
como *«Reference factor of safety … [Corps of Engineers]»* para su problema 95,
el que el banco atribuyó a Bishop.

## 4 · Fuerza entre dovelas: efectiva o total, y ahora se elige

Ajuste nuevo en Project Settings → Methods, leído **sólo** por los tres métodos
de inclinación prescrita:

- **Efectivas** (predeterminado): la presión del agua sobre las caras verticales
  se saca fuera y se aplica como carga horizontal propia. Es lo que OGR hacía
  siempre, así que **ningún proyecto guardado se mueve**.
- **Totales**: el agua va dentro de la resultante cuya inclinación se impone.

Las dos son legítimas, y lo dice la fuente: la EM §C-4a recomienda las efectivas
para la hipótesis del Corps, y su **propio ejemplo resuelto** del apéndice G usa
las totales, *«consistent with most computer software»*. Medido sobre el modelo
con freática del test: 0,896 con efectivas y 1,011 con totales, un **12,8 %**.
Un ajuste que no moviera el número sería peor que no tenerlo (regla 7), y éste
lo mueve.

**Esto no cierra D20.** Lo hace visible y medible, que es distinto. Ver §6.

## 5 · `base_normal` en toda la familia, y lo que desbloquea

La ecuación **G-16** de la EM publica la normal en la base, y sale del
equilibrio **vertical** de la dovela y de nada más —las fuerzas horizontales no
aparecen porque no tienen componente vertical—. Implementada, y contrastada
contra la columna que la figura G-7b imprime.

No es un número de adorno. `rapid_drawdown._stage1_state` lee `base_normal` para
recuperar el estado de consolidación de la etapa 1, y hasta ahora **sólo
`bishop.py` y `ordinary.py` la rellenaban**: con cualquier método de fuerzas la
lista llegaba vacía, el bucle se rompía en la primera vuelta y el desembalse de
dos etapas aplicaba resistencia sin drenar a **cero dovelas**, degradándose en
silencio a volver a resolver la etapa 1 (anomalía **A95-1** del banco: Spencer
daba 2,0773 donde el manual publica 1,347, un +54 % del lado inseguro).

Los tres métodos de esta familia ya no hacen eso. **Spencer, GLE y Janbu siguen
haciéndolo**, y decirlo forma parte del arreglo: A44-1 sigue abierta para ellos.

## 6 · Dos cosas que se encontraron y NO se han corregido

Regla 6. Las dos salieron de buscar una identidad con la que validar lo nuevo.

### 6.1 · La rama de equilibrio de fuerzas de Spencer y GLE, medida contra Janbu

La EM §C-4a dice que una hipótesis de fuerzas entre dovelas **horizontales** en
un método de sólo equilibrio de fuerzas *«is sometimes referred to as the
"Simplified Janbu" Method»*. Es una identidad exacta y sirve de test. Con θ = 0
la recursión nueva da **0,845089** y el Janbu simplificado de OGR da
**0,845273**: 0,02 %. El motor nuevo pasa.

Al usar la misma identidad sobre `GLEMorgensternPrice._inner_solve` con
λ = 0 —que es la misma hipótesis— sale **0,4119**, la mitad.

La causa está a la vista y es una línea, la misma en los dos archivos:

```
spencer.py:314   num_f += S_term * math.cos(alpha)
gle.py:377       num_f += S_term * math.cos(alpha)
janbu.py:150     n_alpha = cos²α · (1 + tanα·tanφ/F)   →   S_term / cos α
```

Con los denominadores idénticos —`Σ (W·tanα + H)` en los tres—, las dos
expresiones difieren en **cos²α por dovela**. Y el equilibrio horizontal del
conjunto con X = 0 da `Σ S·secα = Σ W·tanα`, o sea la forma de Janbu:

| forma | F sobre el círculo de Ej_1 |
|---|---|
| `S_term · cos α` (Spencer y GLE hoy) | 0,3074 |
| `S_term / cos α` (equilibrio horizontal) | 0,8451 |
| `janbu_simplified` de OGR | 0,8453 |

**Y corrige un diagnóstico que ya existía.** El defecto D10 del banco de
verificación mide desde el 2026-08-20 que `F_f(0)/Janbu` vale 0,500, 0,701,
0,774 y 0,794 en cuatro problemas, y lo atribuye a que «λ no llega a la normal
en la base». Eso **no puede** ser la causa en λ = 0: ahí no hay cortante entre
dovelas, así que las omisiones que D10 señala son correctas. El `cos²α` sí lo
explica — y explica además que el ratio **no sea constante**, porque pondera por
dovela y da menos cuanto más empinada es la superficie.

**Por qué ha sobrevivido a la validación**: Spencer y GLE publican el factor en
la λ donde `F_f = F_m`, y `F_m` es correcto y bishopiano. Un `F_f` deprimido no
mueve mucho el valor final —lo empuja hacia Bishop— pero **desplaza la λ de
cruce hacia arriba**. Eso encaja con tres cosas ya escritas en este repositorio
y nunca explicadas:

- `docs/audits/spencer_gle_interslice_v179.md`, abierto desde v0.1.79: «Spencer
  y GLE se separan de Bishop mucho menos de lo que dicen las referencias
  publicadas»;
- la medida con piezométrica de `PENDIENTES.md`: con agua la referencia separa
  +1,89 % y OGR separa −0,00 %;
- el rango de λ, ensanchado dos veces persiguiendo raíces que no llegaban —a
  ±1,5 en v0.1.74 porque el círculo de Ej_1 «necesitaba λ = 1,4919», y a +6 en
  v0.1.90.

**No se ha tocado nada.** Es un cambio que mueve dos métodos validados y merece
su propia versión, su propia medición y sus propios casos de referencia. Queda
anotado en `docs/PENDIENTES.md` con el reproductor completo.

### 6.2 · La geometría del problema 95 del banco es la que no es

Buscando el origen del 1,35 apareció el enunciado original: la figura G-5 de la
EM da la sección con **dos pendientes**, 3:1 de la cota 0 a la **74** y 2,5:1 de
la 74 a la 110, con el embalse lleno en **103**. El banco la había reconstruido
como un talud único 1:3 con nivel inicial 110.

Y lo confirma la figura del propio manual de verificación, no sólo la EM: los
vértices de su figura 95.1 caen en (222, 74) y (312, 110), y su línea `W
(Initial)` está trazada en y ≈ 103 — **el texto del manual, que dice 110,
contradice a su propia figura**. El extremo izquierdo publicado del círculo,
(72,139 · 24,046), cae exactamente sobre y = x/3, y por eso el 1:3 parecía
confirmado: lo está, pero **sólo por debajo de la cota 74**. Entre x ≈ 222 y la
coronación las dos geometrías difieren, y ahí es donde estaban los pesos mal.

Corregido en el banco, que vive fuera de este repositorio. La comprobación de
que la corrección es la buena es exacta: con la geometría nueva **los dos
extremos** del círculo publicado salen en (72,139 · 24,046) y (354,048 ·
110,000), que es lo que imprime el panel, a la milésima en las cuatro
coordenadas.

Y el resultado, que no es el esperado y por eso se cuenta: sobre ese círculo
OGR da **1,3993** con Corps of Engineers #1 contra el **1,347** del panel,
**+3,88 %**. No está en el método —la recursión reproduce el 1,35 del manual a
−0,5 %— sino en la referencia: la tabla G-9 tiene φ = 0, así que Bishop sobre
esas mismas dovelas sale a mano, `Σc·ℓ / ΣW·senα = 1,2733`, y el 1,35 publicado
está **+6,03 % por encima de Bishop**. OGR reproduce esa separación (Corps #2 /
Bishop = 1,0543 contra 1,0603), mientras que **el 1,347 del panel está a
+0,21 % del Bishop de OGR**: no se comporta como el Modified Swedish que su
propia etiqueta nombra. El problema 95 queda en **REVISAR con causa nombrada**,
que es más de lo que tenía, y **D31 cerrado**.

## 7 · Lo demás

- `analysis_runner._PRESCRIBED_THETA_METHODS`, la tercera lista de este tipo, y
  como las otras dos está **junto a la que decide** y no repartida.
- El diálogo: las dos casillas se encendieron **solas**. Ni una línea de
  `_MethodsPage` cambió, porque desde v0.1.78 pregunta al registro. Es la
  demostración de que el invariante de `test_methods_page_v178.py` servía para
  algo.
- `test_corps_of_engineers_stays_disabled` **cambió de sentido y no se borró**:
  ahora es `test_corps_of_engineers_is_now_offered`, y el propio test explica
  por qué. La mitad del invariante que protegía —que el gris siga al registro en
  **las dos direcciones**— sigue en pie.
- Alias del CLI: `corps1`, `corps2`, `coe1`, `coe2`, `modified_swedish`.

## 8 · Qué se probó

- `tests/test_modified_swedish_v198.py`, 21 tests: la recursión contra las
  tablas publicadas del apéndice G (fuerza entre dovelas y normal en la base),
  el factor 1,35, la identidad de Janbu con θ = 0, las tres reglas de θ como
  geometría exacta, y la regla 7 por triplicado.
- Lowe-Karafiath **bit a bit** contra 0.1.97 sobre el círculo de referencia de
  Ej_1: `0.885649921202` las dos veces, mismas iteraciones, misma razón de
  empujes en el primer contorno.
- La suite entera, sin argumentos.

### Qué falta por probar

- El **problema 99** del banco sigue **NO REPRODUCIBLE**: su comprobación
  independiente de la figura falla por 7 y 6 pies, y tener el método no arregla
  eso.
- Los métodos nuevos **con soportes** y **con sismo** no tienen caso publicado
  propio: heredan el tratamiento de Lowe-Karafiath, que sí lo tiene, pero no es
  lo mismo que medirlo.
- §6.1, entera.
