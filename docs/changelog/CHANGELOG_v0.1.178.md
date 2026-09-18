# OGR Slip2D v0.1.178

**Defecto D144.** El momento de un soporte en la rama de momentos **circular**
se formaba con el ángulo de la **cuerda** de la dovela que cruza, multiplicado
después por un brazo R que no es el suyo. Ya no: se toma el producto vectorial
de la fuerza en el punto donde cruza.

Lo que más enseña de esta versión no es el arreglo, que es de tres líneas, sino
tres cosas que la medición desmintió: la premisa del encargo sobre las
superficies no circulares es falsa **y al revés de como la leí**; el error no es
un sesgo sino una oscilación **que cambia de signo entre los dos círculos
publicados del mismo problema**; y el defecto llevaba **cuarenta versiones
escrito** en el docstring de un test que nadie siguió.

---

## 1. La frase que ya estaba escrita

`test_efp_wall_v1122::test_bishop_now_agrees_and_the_gap_shrinks_on_refinement`
sostiene desde v0.1.137 la identidad «la misma fuerza, en el mismo punto, da el
mismo factor de seguridad tanto si entra como SOPORTE como si entra como
CARGA», y decía de su residuo:

> what is left is discretisation — **the chord angle of a slice against the
> angle at the point where the force is applied**

Esa frase es D144 entera, escrita en v0.1.137 y tratada como un residuo
inevitable durante cuarenta versiones. No lo era.

## 2. Por qué NO se cambia el ángulo con que se descompone el soporte

Había tres lecturas y sólo una no rompe nada.

| | qué hace | por qué no |
|---|---|---|
| (A) | `a` pasa a ser la tangente en `resolve_support_terms` | **Rompe la rama de fuerzas.** Hoy `Σ t_active·sec a = F_h` EXACTAMENTE, porque el mismo ángulo aparece en la proyección y en la secante. Con `t_r` de tangente y `sec a` de cuerda saldría `F_h·cos α_tan/cos α_cuerda`: +1,17 % en el 085, en la única rama que ya era exacta |
| (A′) | la tangente en todos los sitios donde aparece el soporte | Mueve los métodos de SÓLO fuerzas (Corps 1/2, Lowe-Karafiath, Modified Swedish, Janbu), que no tienen brazo de momento — y rompe una identidad **exacta** para arreglar una aproximada |
| **(B)** | `t_active`/`t_passive` se quedan; se añade el momento exacto, y sólo lo leen los tres caminos de momento **circulares** | lo que se hizo |

El argumento de fondo: **descomponer una fuerza sobre la cuerda y su normal es
una ROTACIÓN, no una aproximación.** `t_active` y `n_press` recomponen
`(f_h, f_v)` bit a bit, y el equilibrio de fuerzas de la dovela está escrito
sobre una base que *es* la cuerda desde v0.1.100. Lo único aproximado en toda
la cadena era el **brazo**, y un brazo es geometría, no una proyección.

**Y eso ya estaba resuelto en este proyecto, para el peso, sin extenderlo al
soporte.** `slicer.py` declara en mayúsculas que la base de una dovela ES la
cuerda (v0.1.100, decisión medida: con tangente de punto medio Bishop daba
−4,34 % en el problema 23 y con cuerda +0,00 %), y a renglón seguido separa los
dos usos con `Slice.weight_arm_ratio = (xc − centre_x)/R`, documentado así:

> the chord's own angle is no longer the tangent at xc, so the moment arm is
> taken from the geometry instead of from the angle

El peso recibió ese tratamiento y el refuerzo no. D144 se lo da, con la misma
forma y por la misma razón.

## 3. El arreglo

`SupportTerms` gana dos escalares **detrás de `failure`** (las tres
construcciones del repositorio son posicionales y ninguna vive en un test):

```
moment_active / moment_passive = slide_sign ·
    [(x_P − x_c)·F_v − (y_P − y_c)·F_h] / R
```

Cuatro decisiones, cada una con su razón medida:

1. **El signo no se inventa, se lee del peso.** La suma motora circular añade
   `slide_sign·W·weight_arm_ratio` para un peso `(0, −W)` en la abscisa `x`,
   que es `−slide_sign·M_z/R` con `M_z` antihorario sobre el centro. El par
   (`−slide_sign·couple/R`) y el momento del agua entran igual.
2. **Por EFECTO y no desde `x_app`/`y_app`**, que es una media ponderada por
   |F|: el brazo de una suma de fuerzas no es la suma de brazos salvo que los
   pesos sean los momentos. Con dos soportes de orientación distinta en una
   dovela, esa media no es donde actúa ninguna fuerza.
3. **En `intersection_*` y no en `application_*`**, porque `couple` ya lleva el
   traslado y tomarlo aquí lo contaría dos veces.
4. **El respaldo sin centro es `t_r`, no `0.0`**: el campo significa siempre
   «lo que el lado motor le debe a este refuerzo», y un cero borraría el
   refuerzo en silencio, que es la lección de D94.

**No hay que añadir ningún término normal**, y el comentario que decía lo
contrario se reescribe en vez de borrarse, porque su premisa era cierta y su
tesis falsa: una fuerza normal a la CUERDA no es normal al ARCO, así que sí
tiene momento sobre el centro — pero el producto vectorial entero ya lo
contiene, y sumar `nf_h`/`nf_v` encima lo contaría dos veces. Decirlo en ese
orden importa, porque la versión invertida lleva a añadir un término que sobra.

Consumidores: `bishop.py`, `ordinary.py` y la rama circular de
`GLESystem.__init__`, y ninguno más — el despacho circular es
`isinstance(surface, SlipCircle)`, de modo que `CompositeSurface` y
`WeakLayerSurface`, que tienen centro, van por el camino general.

## 4. Lo que la medición desmiente del encargo

**La premisa sobre las no circulares es falsa, y su consecuencia es la
contraria de la que yo había leído.** El prompt dice que `moment_terms` «ya usa
el punto de aplicación», y sólo es verdad de la mitad NORMAL: el término
tangencial se aplica en el punto medio de la base con la dirección de la
cuerda. Pero sobre una polilínea la base **es** un segmento recto y el cruce
está sobre él, así que trasladar la fuerza a lo largo de su propia línea de
acción no cambia su momento: **el camino no circular ya era exacto**. «Sólo en
superficies circulares» no es una restricción prudente; es una consecuencia.

**El error no es un sesgo.** A primer orden vale `−Δα·tan(α − θ)` con `Δα =
α_cuerda − α_tangente` y θ el ángulo de la **fuerza**, y `Δα` es O(1/n) con
signo que depende de dónde cae el cruce dentro de su dovela. En el círculo 85.2
la cuerda va 0,558° por encima y el término sale **1,17 % corto**; en el 85.3,
del mismo problema, va 0,442° por debajo y sale **1,06 % largo**. Una malla más
fina no iba a pagar eso en una dirección.

**El 1,531 contra el que un test comparaba estaba medido sobre otro círculo**
(§6), y el `1,378` que parecía su pareja natural no sirve: es GLE sobre un
crítico que el manual no dibuja.

## 5. El pre-vuelo, que es lo que autorizó tocar el motor

Con φ′ = 0 en el problema 85 la ecuación de momentos es un cociente de dos
sumas, así que el efecto se **predice** sin ejecutar código nuevo:

    sin soporte  F = Σc·l / D      activo  F = Σc·l/(D − T)
    pasivo       F = (Σc·l + T)/D  con  D = Σ slide_sign·W·weight_arm_ratio

Las cuatro reconstrucciones reprodujeron el motor de 0.1.177 a **0,00e+00,
0,00e+00, 0,00e+00 y −4,44e-16**, lo que valida `num` y `D` en vez de
suponerlos. Y después el motor arreglado devolvió los cuatro números predichos
**dígito a dígito**:

| escenario | círculo | cuerda | exacto | publicado para ese círculo | err antes | err después |
|---|---|---|---|---|---|---|
| 085 activo | 85.2 | 1,556171 | **1,569188** | 1,575 (GLE) | −1,195 % | **−0,369 %** |
| 085 pasivo | 85.3 | 1,325508 | **1,321350** | 1,324 (Bishop) | +0,114 % | **−0,200 %** |
| 085 pasivo | 85.2 | 1,327025 | 1,331903 | — | | |
| 085 activo | 85.3 | 1,539349 | 1,528816 | — | | |

Y Bishop = Fellenius en las cuatro filas, que es lo que φ′ = 0 obliga.

El censo de orientaciones se escribió **antes** de correr el banco, porque una
tabla sin predicción es una lista de números que cambiaron: de los 36 `.ogr`
con soporte, 6 son `horizontal`, 22 `parallel_to_support` (los ocho muros 87–94
entre ellos) y 1 mixto — primer orden —, y **7 son `tangent_to_slip`** (054,
060, 106 ×4, 111), que son de segundo orden porque esa orientación toma su
dirección de `_slip_tangent_at_x`, que también es la pendiente de la cuerda:
`cos(a_c − θ) = 1`, y lo que queda tras D144 es `cos Δα ≈ 1 + Δα²/2`.

## 5bis. El 1,17 % del 085 NO es el tamaño del defecto

Es el tamaño del defecto **en el 085**, y el banco lo dice en cuanto se le
pregunta. La ley es `−Δα·tan(α − θ)`, y el factor `tan α` **explota cerca de la
vertical**. En el problema 030 el soporte cruza una dovela cuya cuerda está a
**73,52°** mientras la tangente del arco allí vale **79,12°**: `tan 79° ≈ 5,1`,
y el término del refuerzo sale **+50,27 % largo** a 50 dovelas. Como además ese
término es el **36,8 %** del momento motor, el factor de seguridad se mueve
**−10,32 %**, de 1,824141 a 1,635848 — medido en A/B dentro del mismo proceso,
con el lado «cuerda» reproduciendo bit a bit lo que la instantánea archivaba.

Y en la misma tabla está la prueba de que el arreglo es el correcto, sin
necesidad de ningún valor publicado:

| dovelas | término de cuerda | término exacto |
|---|---|---|
| 50 | 56,73459 | **37,75491** |
| 200 | 42,81952 | **37,75491** |

El término exacto **no depende de la malla**; el de cuerda converge despacio
hacia él desde arriba. Eso es lo que `TestItIsNotTheChord` afirma con una
fixture sintética, visto aquí en un caso real del banco con un efecto del 50 %.

De paso, el 030 se **acerca** a lo publicado: el manual da 1,69, y el error pasa
de **+7,94 % a −3,21 %**.

## 6. Los tests que se re-anclan, y uno que se rompe por éxito

Diez casos de seis archivos. **Ninguna banda se ensancha.**

**`test_efp_wall_v1122`** es el control independiente y el que más dice.
`test_bishop_now_agrees_and_the_gap_shrinks_on_refinement` afirmaba
`abs(gaps[-1]) < 0.3·abs(gaps[0])` sobre un residuo de −0,010 / +0,0016 /
+0,0006 %. Con el brazo exacto ese residuo pasa a **0,0 / +1,4e-14 / −4,1e-14 %**
y la aserción se lee `4e-14 < 0`: un test roto porque arreglaron su asunto.
Pasa a la forma de su hermano de Janbu (`all(abs(g) < 1e-9)`), y la derivación
va escrita — la carga siempre tuvo el brazo exacto, y una fuerza horizontal
aporta idénticamente cero por `support_vertical_load`, así que no queda nada
que discretizar. **Si ese residuo no se hubiera apretado, el diseño estaría
mal**, y por eso este caso se eligió como control antes de escribir una línea
de motor.

**`test_support_projection_v1113::test_the_two_published_numbers`** evaluaba
**Bishop sobre el círculo que el manual publica para GLE** (85.2) y lo comparaba
con `_DW_ACTIVE = 1.531`, que es Bishop sobre el crítico de Bishop — que el
manual **no dibuja**. Pasaba a +1,64 % porque el brazo de cuerda tiraba del
número hacia abajo un 0,84 %; con el brazo exacto va a +2,49 % y cruza la banda
del 2 %. La banda no se toca: se arregla el emparejamiento, cada escenario
sobre el círculo que el manual publica **para él**, y las dos mitades quedan más
cerca de lo que estaba ninguna antes (−0,369 % y −0,200 %). Que Bishop pueda
compararse con una cifra de GLE sobre el 85.2 no es una licencia: con φ′ = 0
Bishop, Fellenius y la rama de momentos de GLE son el mismo cociente sobre
cualquier círculo, y el test lo **afirma** en vez de suponerlo, exigiendo que
los dos métodos coincidan a 1e-12. El principio ya estaba escrito en la cabecera
de `test_support_active_passive_v1115`: comparar un método contra un factor
obtenido sobre otra superficie mide dos cosas a la vez.

**Las reconstrucciones de la ecuación de Bishop** (`test_support_normal_v1137`,
`test_supports_all_methods_v164`) descansaban en una premisa que D144 mata:
«un soporte puramente normal añade `T_N·tanφ'` a ΣR **y nada a ΣD**». Es falsa,
y por el mismo motivo visto desde el otro lado: *puramente normal* significa
normal a la CUERDA, y la normal de una cuerda no apunta al centro del arco, así
que ese soporte no tiene fuerza tangencial y **sí** tiene momento. Hasta D144 el
motor formaba el término desde la proyección sobre la cuerda, que ahí es cero,
así que los dos coincidían: **equivocados en el mismo sitio**. En v1137 se añade
además la aserción de que `moment_active` NO es cero, con la razón al lado, que
es el caso más instructivo del archivo.

**`test_support_active_passive_v1115`** es el `TANGENT_TO_SLIP` y falla por
**+0,001 %**: exactamente la cancelación de segundo orden que el censo predijo.
El valor esperado deja de ser `CAPACITY` y pasa a ser el momento que la fixture
produce, con una guarda de que sigue a menos de 1e-3 de la capacidad — si
creciera al tamaño de un error de cuerda, la fixture habría dejado de ser
tangencial y estos casos medirían otra cosa.

**`test_support_failure_v1161`** fija bit a bit el modelo 091 del banco, quince
láminas `parallel_to_support`: Bishop 0,9835740303049271 → **0,9829608966855081**
(−0,0623 %) y Spencer 0,9641378773625315 → **0,9636163385716956** (−0,0541 %).
Que los dos se muevan casi lo mismo y en la misma dirección es lo que un término
de momento compartido tiene que hacer; un cambio que moviera sólo uno no sería
este defecto. Lo que v0.1.172 usaba de Bishop sigue disponible: Bishop no entra
en `interslice.py` y sigue siendo el control de lo que allí pase.

## 7. El test nuevo

`tests/test_support_arm_v1178.py`, 21 casos en seis clases, **ninguna aserción
fija un factor de seguridad**. Contra el árbol de 0.1.177, con sólo el fichero
presente, **fallan 9 y pasan 12** — y de los 9 sólo **3 discriminan de verdad**
(los dos de forma cerrada con φ′ = 0, por −1,05 % y −0,17 %, y la identidad
carga ≡ soporte, por −1,05 %); los otros 6 fallan con `AttributeError`, que es
discriminación débil y va etiquetado como tal en la cabecera en vez de contado.

Los 12 que pasan por los dos lados son los controles, y uno de ellos existe por
lo que este cambio podría haber roto: `TestTheForceBranchStillTelescopes` fija
que `Σ t_active·sec a` sigue siendo la fuerza horizontal, que es la identidad
exacta que la lectura (A) habría destruido.

Dos cosas que el archivo **no** afirma, dichas en voz alta. La identidad
`moment_active == producto vectorial` es **exacta por construcción a 1e-15, no a
1e-9**: comprueba la contabilidad, no dónde está el punto. Y el punto de cruce
se calcula contra la **polilínea de cuerdas**, así que queda O(1/n²) dentro del
arco. `TestTheResidualThatRemains` mide ese sobrante en vez de darlo por
inexistente, y el enunciado no es «es pequeño» —en esta fixture es el 28 % del
defecto a 20 dovelas— sino que **son órdenes distintos**: el residuo cae ~4× al
duplicar la malla y el defecto no cae en absoluto (sube entre 80 y 160 dovelas).

## 8. Reportado y NO corregido (regla 6)

1. **`x_app`/`y_app` es una media ponderada por |F|**, así que en el camino NO
   circular, con dos soportes de orientación distinta en una misma dovela, el
   brazo de la parte normal se toma donde no actúa ninguna fuerza. Ficha nueva.
2. **`_slip_tangent_at_x` devuelve la pendiente de la CUERDA** y orienta la
   fuerza en `TANGENT_TO_SLIP`, `BISECTOR` y `PERPENDICULAR_TO_PILE`, de modo
   que la aproximación entraba dos veces. Con una consecuencia que hay que
   escribir o alguien la leerá como un error: **hoy los dos errores se
   cancelaban** para esa orientación y tras D144 dejan de cancelarse, quedando
   `cos Δα ≈ 5e-5`. Este cambio mejora los demás en primer orden y empeora ése
   en segundo. Arreglarlo mueve el 054, el 060, el 106 y el 111: ficha propia.
   Dos detalles del mismo símbolo: su comparación por la izquierda no lleva la
   holgura `1e-9` que sí lleva la búsqueda de dovela, y el `or 0.0` confunde
   «pendiente nula» con «no hay pendiente».
3. **`total_active_t()` y `total_passive_t()` se quedan sin un solo consumidor
   de producción**: la rama de fuerzas usa `t_active` por dovela con su `sec a`,
   nunca la suma. Es la situación que el docstring de la clase describe al
   contar por qué se borró el par `h_active`/`h_passive` — «un campo muerto es
   una invitación a volver a enrutar un método por él». Se quedan porque los
   tests los usan para fijar que la descomposición de cuerda NO se movió, y eso
   va escrito en su docstring.
4. **`GLESystem._driving` se escribe y no se lee nunca**: está en `__slots__`,
   se le asigna `den`, y no hay una sola lectura en el repositorio ni en los
   tests. Es precisamente el número que D144 cambia, calculado para nadie.
5. **`from ogr_core.support import ForceApplication` dentro de
   `resolve_support_terms` está muerto**, y es un `import` en el camino
   caliente, una vez por superficie reforzada por método.
6. Queda vivo el brazo de la propia `S_i`, tomado como R cuando la cuerda está
   a `R·cos(θ/2)` del centro (`bishop.py` ya lo documenta y lo mide: 0,055–0,067 %
   a 25 dovelas). Es O(1/n²) y **se cancela** en la identidad carga ≡ soporte,
   así que no es objeción a este diseño — pero si alguien mide ese residuo y lo
   ve no-cero, ése es el sospechoso.
7. `test_support_failure_v1161` sigue usando `pytest.skip`, que el runner no
   implementa (ya reportado en v0.1.176).
8. **`D141` consta `SE SOSTIENE` en `verificacion_cierres.json` y no tiene
   renglón en el índice de cerrados** — una ficha cerrada que nadie retiró, y
   no es de esta versión. Se deja dicho en vez de arreglarse de paso, porque
   retirar una ficha ajena sin leer lo que su cierre afirmó es cómo se
   encadenan los errores.
9. `total_active_t()` y `total_passive_t()` sobreviven sin consumidor de
   producción (§8.3), y la rama de fuerzas usa `t_active` por dovela: quien
   quiera la suma para el equilibrio de fuerzas la necesita con `sec a`, así
   que ninguno de los dos accesores es hoy la magnitud que su nombre sugiere.

## 9. Errores propios detectados antes de publicar

Quince, y tres de ellos habrían hecho falsa una afirmación publicada: los dos
primeros sobre el test y el decimotercero sobre el banco entero.

1. **La ley de primer orden llevaba el ángulo equivocado.** Escribí
   `−Δα·tan α`, y el cociente es `cos(a_c − θ)/cos(a_t − θ)` con θ el ángulo de
   la **fuerza**: la ley es `−Δα·tan(a_t − θ)`. Con una fuerza horizontal las
   dos coinciden; con la inclinada a 25° la versión corta se equivoca por un
   factor **5,8**. El ancla inclinada estaba en la fixture justamente para que
   un atajo así no pudiera pasar, y lo cazó.
2. **El signo de esa ley, que la salida del pre-vuelo ya enseñaba** (−1,17 %
   medido contra +1,17 % de la ley) y no leí.
3. **El ancla inclinada no cruzaba el arco.** La dibujé más abajo en el
   paramento y el círculo sólo abarca x ∈ [40,2, 52,3]: cero efectos, y una
   lista vacía hace **vacua** cada aserción sobre ella en vez de falsa. Lo que
   se inclina es la FUERZA, no la geometría.
4. **«cien veces más dispersión» era falso**: medido son 27× y 12×. La
   aserción pasa a 8×, la menor de las dos con margen; escribir 27 sería
   congelar la malla de esta fixture.
5. **«dos órdenes por debajo del defecto» era falso** en esta fixture. Lo que
   sí es cierto —y es mejor test— es que el residuo converge y el defecto no.
6. **Ejecuté `correr_todo.py --help` y el lanzador ignora la bandera**: empezó
   a correr el banco y el `| head -25` lo cortó tras el problema 001 y parte
   del 002. Los dos son problemas **sin soporte**, así que el accidente se
   convirtió en verificación: re-corridos enteros con 0.1.178, **124 números
   comparados contra la instantánea y 0 movidos**.
7. `slice_forces` no vive en `ogr_slip2d.slicer` sino en `external_forces`.
8. `LoadDistribution.UNIFORM` no existe; es `CONSTANT`.
9. El plano de `test_a_plane_falls_back_to_the_chord_sum` no cortaba el talud y
   no producía dovelas.
10. En `test_supports_all_methods_v164` puse el término en el denominador
    creyendo el soporte ACTIVO, y es PASIVO: va al numerador.
11. El informe de auditoría salía como `v01178` en vez de `v1178`.
12. **El comparador del A/B no imprimía la versión del lado A**, y sin ella
    habría imputado a D144 todos los dígitos que movieron 0.1.175 y 0.1.176 —
    el rescate de rama mueve el censo de válidas de todo Spencer/GLE. Lo
    destapó una fila que no podía ser mía: `054 modelo_sin_pilote`, un modelo
    **sin soporte**, con dos números movidos. Es la misma trampa que v0.1.173
    documentó, y la única defensa es publicar la versión de cada lado.
13. Al insertar el bloque del A/B en el medidor del banco por heredoc, `\n`
    llegó como salto real y el parche no casó — la trampa de las capas de
    escapado que este proyecto ya tiene escrita. Rehecho leyendo el bloque de
    un archivo en vez de incrustarlo en la orden.
14. `d144()` nació con un `%%` literal en una cadena que no pasa por `%`, que
    es literalmente uno de los errores que v0.1.175 dejó listados.
15. El aislador leía `centro_x`/`centro_y`/`radio` del `referencia.json`,
    y las claves son `centre_x`/`centre_y`/`radius`.

## 10. El banco, fila a fila

Instantánea `Evaluaciones/0.1.177` congelada **antes** de tocar nada (1617
archivos, comprobados byte a byte). Corrida de los **35 modelos circulares** de
los 21 problemas con soporte, **4,2 h**, 35 de 35 sin fallos, más las dos
mitades no circulares del 085. A/B: **1986 números comparados en 46 archivos,
313 movidos**.

Y una columna que la tabla necesita y que casi se me olvida poner: **la versión
del lado A**. La instantánea no es una corrida homogénea —lo dice ella misma—,
así que de los 46 archivos sólo **19 dan un A/B limpio de D144** (los que ya
estaban a 0.1.176); 16 arrastran también 0.1.175 y 0.1.176, y el rescate de rama
de 0.1.176 mueve el censo de válidas de todo Spencer/GLE. Sin esa columna esos
dígitos se imputan a D144, que es exactamente la trampa que v0.1.173 dejó
documentada. Lo destapó el `054 modelo_sin_pilote`: un modelo **sin soporte** con
dos números movidos, que no podían ser míos.

**La predicción escrita antes de correr se sostiene**, y donde no lo hace la
razón es mejor que la predicción:

| familia | predicción | medido |
|---|---|---|
| `tangent_to_slip` (054, 060, 106) | 2.º orden, < 0,01 % | −0,0021 %, −0,0009 %, −0,0004 % |
| `horizontal` (085, 086) | 1.er orden | −0,31 % / +0,37 %, −0,10 % |
| `parallel_to_support` (030, 059, 087–094) | 1.er orden | de **−10,32 %** a **+0,01 %** |

Las **cuatro filas quietas** son las que más dicen, porque se predijo que se
moverían:

* **031** — 0 de 11. Su ancla va de (0, 0) a (43, 0) y la masa crítica vive entre
  x = −26,19 y −0,01: **el soporte no cruza la superficie que gana**, cero
  efectos, `present = False`. Es el caso de D62 visto desde aquí.
* **048, 049, 050** — 0 de 9, 34 y 22. Sus superficies publicadas son
  **polilíneas** y sus métodos los dos Janbu, que sólo cierran equilibrio de
  fuerzas. D144 no toca ni el camino no circular ni la rama de fuerzas: cero por
  construcción, y ahora con la construcción escrita.

Los ocho muros 87–94 se mueven **+0,01 a +0,06 %** en su círculo publicado y
−0,12 a −0,80 % en el mínimo global de Bishop, que es lo que cabe esperar: un
mínimo se busca sobre miles de círculos y algunos tienen bases mucho más
empinadas que el publicado. El 059 mueve su círculo publicado **−2,08 %**.

**Lo que NO se re-corrió, y por qué**, con el denominador delante: 11 de los 46
archivos. Los 30 problemas **sin soporte** no se re-corren, y es una identidad
demostrable en cinco líneas —`resolve_support_terms` devuelve `_EMPTY_TERMS`
antes de asignar nada cuando el proyecto no tiene soportes—; los dos que el
accidente del error 6 re-corrió enteros lo confirman con número delante: **124
números, 0 movidos**. El `modelo.ogr` del **047** y el del **111** —el único
ancla helicoidal del banco— los escribe otra herramienta y el lanzador los salta
por diseño, así que su fila queda declarada como NO RE-CORRIDO y no como
invariante. Las mitades no circulares de los demás problemas no se corren por la
misma razón de código que las hace inmunes, más el caso del test que fija
`moment_active == total_active_t()` con `==` sobre un plano.

## 11. Un cambio de estado que la ficha del 085 ahora oculta a propósito

El arreglo cierra el brazo y, con él, mueve la **reserva**. Sobre el círculo
publicado del 085 activo, GLE:

| | fos publicado por OGR | residuo de λ | aviso |
|---|---|---|---|
| 0.1.176 | **ninguno** | 0,022980 | «no λ-bracket; the nearest λ leaves F_f ≈ F_m at 0.023» |
| 0.1.178 | **1,574170** | **0,009963** | INADMISIBLE, pero publica |

El residuo cruza `FALLBACK_RESIDUAL_LIMIT` = 0,02 y el motor publica por fin
un factor sobre ese círculo: **−0,053 % del 1,575 del manual**.

La marca `estado_forzado: NO REPRODUCIBLE` **se mantiene**, por decisión del
propietario y con la medida delante: describe el MECANISMO, no la cercanía del
número. Sigue sin haber raíz de λ —0,009963 no es cero—, la superficie sigue
marcada INADMISIBLE por empuje en tracción neta, y lo que ha cambiado es que un
valor de reserva ha entrado bajo un umbral, no que el método cierre. Lo que sí
se corrige es el texto de la ficha, porque **la etiqueta oculta desde ahora una
coincidencia del 0,05 % con el publicado** y quien la lea tiene que saberlo.

Y una nota sobre la nota: la primera versión de esa corrección, escrita antes
de re-correr, decía «eso NO cambia esta marca». Era falsa, y la desmintió la
propia corrida. Va aquí porque el orden importa: se escribió una conclusión
antes de tener el número.

## 12. La comparativa

**559 → 559 filas, 528 IGUAL, sin pareja 0/0.** Un solo cambio de estado, y es
una mejora: **30 Bishop, DISCREPANCIA → REVISAR**. Su mínimo global no se
movió, pero su círculo publicado pasó de +7,94 % a −3,20 %, así que la
discrepancia deja de atribuirse a la formulación.

Las otras 37 filas que se mueven no cambian de estado: **14 mejoran y 16
empeoran**, y ese empate es exactamente lo que cabe esperar de un error que
cambiaba de signo. **El argumento de esta versión no es que el banco mejore**,
porque no lo hace en conjunto; es que el término del refuerzo ya no depende de
la malla y que el caso con forma cerrada cae a −0,37 % del publicado. El
recuento sirve para descartar la lectura contraria, que era plausible.

Las **38 filas que se mueven son todas de problemas con soporte**. Ninguna de
los 90 restantes.

Una marca que aparece y NO es del motor, dicha para que nadie la impute: el
**60 Spencer** gana `**publ**` sin que su número se mueva más de 1e-6. La clave
`reserva_circulo_publicado` la creó v0.1.175 y el archivo del 60 en la
instantánea era de **0.1.173**, que no la traía: una ausencia de medida que
pasa a ser medida, exactamente el caso que el docstring de
`generar_comparativa.py` describe.

## 13. La suite

Suite entera y sin argumentos **3843/3843**, sobre el árbol final y sin banner
`FILTERED RUN` (0.1.177 traía 3822; los 21 nuevos son este fichero). La corrida
intermedia que destapó los diez re-anclajes dio 3833/3843 y no es evidencia de
nada salvo de cuáles eran.

`auditoria_invariantes.py` a **0 ERROR** (749 hallazgos: 491 AVISO, 258 INFO).
`generar_prompts.py` con salida 0, sin fichas sin paquete y sin cerradas sin
prompt. `verificar_cierres.py D144` da **CUBIERTO POR TEST**, y se comprobó que
**discrimina por los dos lados**: con el brazo de cuerda contesta NO SE SOSTIENE
nombrando la causa — «el denominador sigue siendo la proyección sobre la cuerda
(5680.95 frente a 5748.21)». Esa comprobación NO se hizo con `git stash` sino
con un parche en proceso que devuelve `moment_* = total_*_t()`; vale lo mismo
porque el import de `resolve_support_terms` está **dentro de `compute_fos`** y
se resuelve en cada llamada, así que alcanza a los nueve métodos, y porque el
lado «cuerda» reproduce bit a bit los valores que la instantánea archivaba.
