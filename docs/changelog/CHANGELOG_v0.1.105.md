# OGR Slip2D v0.1.105

**El eje de momentos llega a los cuatro métodos que lo necesitan, y por el
camino aparece un terremoto que sujetaba el talud en vez de tirarlo.**

Ocho guardas `if circle_R is not None:` repartían los términos de momento
**sísmico**, de **empuje horizontal del agua** y de **soporte** sólo a las
superficies que eran un `SlipCircle`. Sobre cualquier polilínea —Block,
Path, recocido simulado o superficie predefinida— esos términos
desaparecían sin decir nada. Anomalías A27-2, A42-1, A48-1 y A62-1;
defecto C1 de la auditoría del banco.

El error iba **siempre del lado inseguro**: +45 % en un talud homogéneo
con kh = 0,15, +157 % contra un coeficiente sísmico crítico publicado.

| | antes | ahora |
|---|---|---|
| Identidad boyante sobre polilínea (problema 42), Spencer | −27,05 % | **−0,51 %** |
| ídem, Bishop | −26,35 % | **−0,51 %** |
| ídem, Fellenius | −22,87 % | **+0,69 %** |
| Loukidis kc = 0,432 no circular, Spencer | 2,55539 sin converger | **0,99175** |
| ídem, GLE | 2,30680 sin converger | **0,99176** |
| ídem, Bishop | `nan` | **0,99174** |
| Mismo arco círculo/polilínea con kh, Spencer y GLE | +45,39 % | **−0,01 %** |

**Todas las columnas «antes» están medidas contra v0.1.104**, no copiadas de
la ficha. Importa: la anomalía se levantó con **v0.1.97** y entre medias hay
siete versiones, una de ellas —v0.1.100— tocando el rebanador por el centro
(base de cuerda, `weight_arm_ratio`). Al remedir aparecieron dos diferencias
que la ficha no podía contar, y están en el §2c.

---

## 1 · El eje no había que inventarlo

`moment_axis()` existe desde v0.1.92 y construye
`punto medio de la cuerda + rot90(cuerda)`. Antes de tocar nada lo contrasté
contra el `Axis Location` que publica el panel de una figura no circular del
manual, que es un dato publicado y no una interpretación:

| problema | extremos publicados | eje construido | eje publicado |
|---|---|---|---|
| 40 | (4,000, 53,000) y (105,000, 2,800) | 104,700 · 128,900 | 104,700 · 128,900 |
| 75 | (13,264, 30,500) y (151,231, 18,500) | 94,248 · 162,467 | 94,247 · 162,467 |

Exacto en el primero y a 5·10⁻⁴ en el segundo, que es el redondeo de los
propios extremos publicados a tres decimales. Cuarta y quinta confirmación,
tras Ej_1 y Ej_2.

La sexta llegó sola: con el balance de momentos general, **Fellenius acierta
las dos superficies de referencia a seis cifras**, 0,897423 contra 0,897423 y
1,369209 contra 1,369210, donde la forma vieja se quedaba a −0,65 % y +0,66 %.

## 2 · Lo que se encontró y no venía en el encargo

### 2a · El factor de seguridad SUBÍA con el terremoto

La fuerza pseudoestática es una **magnitud**, `kh·W`, y hay que darle
dirección antes de darle momento. Dos sitios se la daban mal:

- `OrdinaryFellenius`, en la **rama circular**: `H = s.weight·kh·slide_sign`
  sumado como `H·cos α`, de modo que con `slide_sign = −1` **restaba** del
  término motor;
- `BishopSimplified._general_moment_fos`, en la rama no circular: la aplicaba
  en +x pasara lo que pasara.

Talud homogéneo seco, un círculo cualquiera:

| talud | kh = 0 | kh = 0,10 | kh = 0,20 |
|---|---|---|---|
| baja a la derecha (`slide_sign = −1`) | 1,46817 | **1,89347** | **2,74151** |
| espejo, baja a la izquierda | 1,46817 | 1,13791 | 0,91751 |

Y sobre polilínea, con kh = 0,15, Bishop daba 1,318056 en un sentido y
**3,332505** en el espejo: un 152,8 % de diferencia entre un modelo y su
propia imagen.

**Por qué llevaba ahí desde siempre sin que nadie lo viera**: ningún test de
la suite comprobaba el término sísmico numéricamente —`grep seismic tests/`
sólo daba ajustes y probabilístico—, y los tres problemas del banco con sismo
(4, 51 y 62) tienen el talud bajando a la izquierda, donde el signo acierta
por casualidad. El 51, el único que publica Fellenius con sismo, ya estaba
marcado `no_reproduce`, así que tampoco arbitraba.

La lección no es el signo: es que **una condición que sólo se ejercita en una
orientación no está ejercitada**. De ahí el test de simetría especular, que no
existía y ahora recorre los nueve métodos.

### 2b · El soporte se habría contado dos veces

Al unificar la contabilidad apareció que hay **dos convenios** para el
soporte y que no se pueden sumar: Bishop y Fellenius lo parten en una
componente normal (que entra en la resistencia) y una tangencial; Spencer y
GLE lo tratan como fuerza cartesiana externa. Pasar los dos canales al mismo
balance sumaba la misma fuerza dos veces. Está escrito en el contrato de
`moment_terms`, que acepta uno **o** el otro.

### 2c · Remedir en v0.1.104 lo que se midió en v0.1.97

La ficha del problema 62 archiva la anomalía con OGR **0.1.97**. Repetida sobre
un árbol limpio de **0.1.104**, el mismo arco con kc = 0,432 da:

| método | 0.1.97 (ficha) | 0.1.104 (remedido) | 0.1.105 |
|---|---|---|---|
| Spencer polilínea | 2,55526 | 2,55539 **`is_valid=False`** | 0,99175 |
| GLE polilínea | 2,30644 | 2,30680 **`is_valid=False`** | 0,99176 |
| Bishop polilínea | `nan` | `nan` | 0,99174 |
| Fellenius círculo | 0,91864 | 0,91864 | 0,94693 |
| Janbu círculo | 0,94132 | 0,94131 | 0,94131 |

Dos cosas que la ficha no dice y la remedida sí:

1. **El valor inflado no se publicaba callando.** Spencer y GLE lo devuelven
   con `converged=False` e `is_valid=False`, motivo «no λ-bracket; using
   nearest F_f≈F_m»: con el momento sísmico ausente, `F_m` y `F_f` no se
   cruzan en ningún λ del barrido. Una búsqueda descarta las superficies
   inválidas — de ahí las «0 válidas de 40000» de Bishop en la ficha—, pero la
   del Path sí devolvió 2,512735 para Spencer, así que **algunas superficies
   sí volvían válidas con el factor inflado**. El defecto es real; el síntoma
   es más variado de lo que la ficha recoge.
2. **La deriva de v0.1.98 a v0.1.104 es de la cuarta cifra** (2,55526 →
   2,55539). O sea: las siete versiones intermedias no tocaron esto, y el
   número de la ficha seguía siendo bueno. Merece decirse, porque lo contrario
   —dar por buena una medida de siete versiones atrás— es la clase de error
   que este proyecto ya lleva anotada dos veces.

Y una tercera, que sale de aquí: **arreglar esto no sólo cambia un número,
convierte tres resultados no convergidos en convergidos y válidos**.

### 2d · Una guarda que juzgaba con un número que iba a tirar

En Bishop, las dos guardas sobre `denominator` —«momento motor nulo» y
«soporte activo excesivo»— corrían **antes** del reparto circular/no circular.
Sobre una polilínea ese denominador se descarta tres líneas después, pero las
guardas ya habían podido rechazar la superficie con él. El reparto sube ahora
por encima de ellas.

## 3 · Los dos caminos que probé y no sirven

Esto es la mitad que merece recordarse, porque descartar bien fue lo que
decidió el diseño.

**Camino A — brazos reales sin el momento de la normal.** Escribir el momento
de cada término con su brazo geométrico, pero sin el momento que la normal de
la base aporta al no apuntar ya al eje. Parece la traducción directa de la
fórmula circular. Resultado:

| | Ej_1 | Ej_2 | dependencia del eje |
|---|---|---|---|
| camino A | +3,94 % | **−17,06 %** | **±50 a 123 %** |

La dependencia del eje es el diagnóstico: un balance de momentos al que le
falta un término no es un balance de momentos, y mover el eje 50 m cambiaba
el factor un 123 %.

**Camino B — momentos completos, que es el que entró.** Con el momento de la
normal, la invarianza de descripción pasa de +45,39 % a −0,01 % y la
dependencia del eje cae a un 2-4 % residual.

**Lo que ese 2-4 % es, con nombre.** La normal sale del equilibrio vertical de
la dovela, `N = (W − S·senα)/cos α`, que omite `(X_R − X_L)`, la diferencia de
cortante entre caras. En un círculo eso no cuesta nada: la normal apunta al
centro y su momento es cero. Fuera de él sí cuesta, y el término omitido es
**exactamente lo que separa Spencer de Bishop**, así que sobre una superficie
muy quebrada los dos convergen al mismo número.

Que Fellenius —que por definición no tiene fuerzas entre dovelas, y por tanto
tampoco ese residuo— dé **en el blanco** en las dos superficies es lo que
identifica el término que falta, en vez de limitarse a sospecharlo.

## 4 · El coste, aceptado y anotado

`tests/test_noncircular_validation_v192.py` sube la tolerancia de Spencer y
GLE en Ej_1/Ej_2 de 0,5 %/1,0 % a **5 %**:

| | publicado | antes | ahora |
|---|---|---|---|
| Ej_1 Spencer | 0,942419 | 0,941354 | 0,922940 (−2,07 %) |
| Ej_2 Spencer | 1,479930 | 1,483330 | 1,423177 (−3,83 %) |

Se cambió **con permiso explícito** y no en silencio. Cómo queda escrito para
que no se convierta en una suite verde tapando algo:

- la cabecera del archivo lleva la medida, la causa (`X_R − X_L`) y la
  condición de salida — cuándo hay que volver a apretar las tolerancias;
- `TestBishopNoLongerCoincidesWithSpencer` pasa a llamarse
  `TestSpencerHasCollapsedOntoBishop` y **afirma lo contrario que afirmaba**,
  como alambre de dos lados: falla si la brecha crece (alguien pagó la deuda:
  hay que apretar) y falla si se comporta de otro modo. En v0.1.92 esa clase
  fue la regresión que guardaba un arreglo real; ahora guarda una deuda con
  nombre.

**Y medido contra una SOLUCIÓN CERRADA, que es más duro que contra otro
programa.** La cuña plana del problema 43 (talud de 10 m, plano a 50°, c = 30,
φ = 30, γ = 20) con una fuerza horizontal resistente F como soporte pasivo:
una masa deslizante sobre un plano es un bloque rígido, las fuerzas entre
dovelas son internas, y cualquier método con equilibrio de fuerzas debe dar la
fórmula exacta.

| F (kN/m) | cerrada | Spencer antes | Spencer ahora |
|---|---|---|---|
| 0 | 1,4328 | 1,4324 (−0,02 %) | 1,3817 (**−3,57 %**) |
| 20 | 1,4853 | 1,4324 (−3,56 %) | 1,4371 (−3,24 %) |
| 50 | 1,5641 | 1,4325 (−8,42 %) | 1,5262 (−2,43 %) |
| 100 | 1,6955 | 1,4325 (−15,51 %) | 1,6924 (−0,18 %) |
| 200 | 1,9582 | 1,4325 (**−26,85 %**) | 2,1126 (+7,88 %) |

Las dos caras, sin adornar. **A favor**: antes el refuerzo no hacía
absolutamente nada —1,4324 con F = 0 y 1,4325 con F = 200, un control que no
afecta al resultado, que es la regla 7 en su forma pura— y el error máximo baja
de 26,85 % a 7,88 %. **En contra**: con F = 0, donde la fórmula es exacta y el
código viejo acertaba a −0,02 %, ahora se queda a −3,57 %.

No es una deuda nueva: es la misma `(X_R − X_L)`, y el plano lo enseña más
claro que Ej_1/Ej_2 porque ahí hay solución cerrada. Sobre un plano la vieja
`Σ S_term / Σ W·senα` degenera exactamente en el cociente de la fórmula, y por
eso acertaba; en cuanto hay una fuerza externa deja de acertar, y a partir de
F = 50 la nueva ya es mejor. Janbu simplificado, que no tiene ecuación de
momentos, se queda igual en las dos versiones (−0,02 % a +3,84 %).

La salida es la forma completa de Fredlund y Krahn (1977),

```
N   = [W + (X_R − X_L) − (c'·l·senα)/F + (u·l·tanφ'·senα)/F] / m_α
X_i = λ·f(x_i)·E_i,   con E_i por recursión de equilibrio horizontal
```

que exige formar `E_i`. Este solver no lo forma nunca: su `F_f` es el
agregado `Σ S_term(cos α + λ sen α) / Σ(W tan α + H)`. Montar la recursión
encima dejaría las dos ecuaciones resolviendo sistemas de fuerzas distintos,
así que es una reescritura del método y no un término que añadir. **No es
trabajo de esta versión**, y está dicho donde toca.

## 5 · El único test que se cayó, y lo que resultó ser

De 2191 casos, uno: `test_the_walk_spends_the_budget_it_was_given`. Afirmaba
`iterations > 150` sobre **una sola semilla** del paseo de optimización, que
corre Spencer sobre una polilínea de Path Search — justo lo que esta versión
mueve. Con el paisaje nuevo, la semilla 7 se paraba a las 57 evaluaciones.

Antes de tocar el umbral, el barrido sobre ocho semillas, misma superficie,
antes y después:

| paseo plano, 200 evaluaciones | v0.1.104 | v0.1.105 |
|---|---|---|
| semillas que llegan a 150+ | 7 de 8 | 6 de 8 |
| mediana | 200 | 200 |
| mejora del factor | +0,0926 … +0,1079 | +0,0592 … **+0,1391** |
| semilla 13 | **100** | 99 |

El paisaje no empeoró: **el paseo encuentra MÁS** en siete de las ocho
semillas. Lo que pasa es que la semilla 7 tiene mala suerte — y la 13 ya
estaba por debajo del umbral en v0.1.104, así que el caso estaba a un empujón
de caerse allí también. Lo que medía «pasa el presupuesto» era, en realidad,
si esa semilla concreta tuvo suerte.

El test pasa a sostener la **mediana** de cinco semillas, que es lo que la
frase afirma y lo que hundiría una vuelta de la regla de parada vieja (allí
paraba el paseo TÍPICO a las 36, no una semilla desafortunada). Comprobado
**contra los dos árboles**: la forma nueva pasa en v0.1.104 y en v0.1.105, así
que mide el invariante y no esta versión. Coste: el archivo pasa de 11 s a
20 s; con ocho semillas y barriendo también el densificado eran 45 s, y no
aportaba nada — con doce vértices las ocho semillas llegan a 200 en las dos
versiones.

**Lo que NO se ha arreglado, y queda anotado**: que el mismo paseo, sobre la
misma superficie y con el mismo presupuesto, dé entre +0,0592 y +0,1391 según
la semilla — un factor 2,4. Es de la misma familia que el arranque de recocido
simulado que dependía de la suerte (regla 6). No es trabajo de esta versión.

## 6 · Lo que se midió y no se tocó

Fellenius **no** satisface la identidad boyante en el modelo profundamente
sumergido del problema 70: falla por **+66,41 %** (2,517148 contra 1,512605).
Comprobado contra el código de HEAD: **idéntico antes y después**, y en el
círculo tanto como en la polilínea. Es una limitación del método con agua
profunda, ajena a esta versión —`test_ponded_water_v161` ya lo dejaba fuera
de su lista `RIGOROUS` por eso—, y por eso queda fuera del test nuevo, con la
medida escrita al lado en vez de una omisión sin explicar. En la geometría
más somera del problema 42 el mismo método pasa de −22,87 % a +0,69 %.

## 7 · Otro número que se mueve, y hay que declararlo

El término sísmico de Fellenius cambia de **forma** además de signo: pasa de
`H·cos α`, que es la proyección de una fuerza horizontal sobre la base, a
`h_seismic·(y_c − y_g)/R`, que es un brazo de momento. Todos los demás
términos de esa suma motora ya eran momentos partidos por R, y Bishop trata
esa misma fuerza así.

**No hay árbitro externo para la forma** en todo el banco, y conviene decirlo:
la justificación es consistencia interna, no un valor publicado. Efecto
medible: en el problema 62 circular, Fellenius pasa de 0,91864 a 0,94693. Es
también lo único que permite que un arco y la polilínea muestreada de él den
el mismo número bajo un terremoto, porque `cos α` no es un brazo.

Y de paso, `H` pasa a construirse con `f.h_seismic` en vez de `s.weight·kh`,
de modo que la fuerza sea proporcional al peso **después** del coeficiente
vertical, como en los otros ocho métodos. Con kv = 0 —todos los modelos
sísmicos del banco— es el mismo número, que es por lo que no se había notado.

---

## Archivos

- `ogr_slip2d/moment_balance.py` — **nuevo**. Toda la contabilidad de momentos
  como productos vectoriales `(P − O) × F`, en un solo sitio. El sentido de
  giro sale del momento del propio peso, el del cortante de oponerse al
  movimiento que ese giro produce, y el de la fuerza sísmica del primero.
- `ogr_slip2d/methods/bishop.py` — momento del empuje del agua; dirección
  sísmica; el reparto por encima de las guardas circulares.
- `ogr_slip2d/methods/ordinary.py` — balance general fuera del círculo; signo
  y forma del término sísmico.
- `ogr_slip2d/methods/spencer.py`, `gle.py` — lado de momentos general fuera
  del círculo; los cinco y cuatro puntos de llamada al solver interno pasan
  por una única clausura.
- `tests/test_noncircular_moments_v1105.py` — **nuevo**, 14 casos: invarianza
  de descripción, simetría especular, identidad boyante sobre polilínea,
  regla 7 sobre kh, y el kc de Loukidis.
- `tests/test_noncircular_validation_v192.py` — la deuda del §4.

## Probado

- **Suite entera sin argumentos: 2191 de 2191.**
- Bishop, contra un árbol limpio de v0.1.104: **bit a bit idéntico** en el
  círculo crítico de Ej_1 y en las dos superficies no circulares en seco
  (delta 0,00e+00), que es lo que demuestra que sólo se movió lo que llevaba
  agua, sismo o soporte.
- Identidad boyante del problema 42, círculo y polilínea.
- Problema 62, el mismo arco en las dos representaciones, contra v0.1.104.
- **Problema 27, A27-2 cerrada**, con el guion propio del banco
  (`anomalias.py`, `modelo_grieta.ogr`, 30 dovelas, la misma superficie como
  círculo y como polilínea de 25 vértices):

  | kh 0 → 0,15 | círculo | polilínea |
  |---|---|---|
  | Bishop | −31,8 % | **−31,7 %** (antes **+79,8 %**) |
  | Spencer | −31,8 % | **−31,7 %** (antes 5 partes por millón) |
  | GLE | −31,8 % | **−31,7 %** (antes nada) |
  | los otros cuatro | −32 a −33 % | igual |

  Los siete métodos responden ya al terremoto sobre polilínea como sobre
  círculo, y las dos descripciones concuerdan dentro del 0,2 %.
- Simetría especular en los nueve métodos, sobre círculo y sobre polilínea.
- **Problema 62, la búsqueda Path entera** (`modelo_seco_path.ogr`, 50 dovelas,
  76 s), que es la comprobación de punta a punta y **no sale del todo bien**:

  | | antes (0.1.97) | ahora | publicado |
  |---|---|---|---|
  | Spencer | 2,512735 | **1,018849** | 0,999 (+1,99 %) |
  | Bishop | `null`, 0 válidas de 40000 | **1,018759** | 0,989 (+3,01 %) |

  De +151 % y «ninguna superficie válida» a converger las dos dentro del 2-3 %.
  Pero **el criterio era 1,000 ± 1 % y no se cumple**: la búsqueda se queda en
  1,0188.

  El residuo **no es de la ecuación de momentos**, y se puede enseñar: esa
  misma búsqueda evalúa correctamente el arco crítico circular descrito como
  polilínea, que da 0,99175 —dentro del 1 %—, o sea que hay una superficie
  mejor que la que la búsqueda devuelve como crítica. Lo que falta es la
  BÚSQUEDA no circular, que es el defecto D21 del banco, y hasta esta versión
  no se podía ni medir porque el factor que devolvía no significaba nada.

## Sin probar

- **Las búsquedas no circulares completas del banco** (Block, Path, recocido)
  no se han vuelto a correr enteras aquí: el Path del problema 62 tardaba 740 s
  en su día. Lo verificado es la evaluación de superficie, que es donde estaba
  el defecto.
- **kv ≠ 0 sobre superficie no circular.** El término existe y entra por
  `w_total`, pero ningún caso del banco lo ejercita.
- **Los diagnósticos por dovela del camino general de Fellenius**
  (`base_normal`, `base_shear_force`, `base_shear_strength`, que alimentan el
  panel *Query Slice Data*). El factor de seguridad sí está validado;
  `test_interpret_slice_data_v187` contrasta esa tabla contra la del programa
  de referencia, pero **sobre un círculo**, así que la rama no circular queda
  apoyada sólo en que usa las mismas magnitudes.
- El eje de momentos **sigue sin dibujarse** en el lienzo (pendiente desde
  v0.1.92), y ahora lo usan cuatro métodos en vez de uno.
