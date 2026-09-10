# OGR Slip2D v0.1.158

**P-D61 pedía un caso publicado, no código. La búsqueda ha terminado en
negativo — y ha vuelto con un ancla que el proyecto no tenía.**

Cero dígitos movidos en cualquier cálculo. D61 queda **ABIERTO con la
búsqueda cerrada**, que es exactamente lo que su criterio de cierre
contempla: *«si no aparece, la ficha lo dice y el defecto se queda abierto
con la búsqueda documentada: eso también cierra este prompt, no el
defecto»*.

---

## 1. La búsqueda, y por qué termina en negativo

El paso 1 del encargo: **superficie no circular en suelo φ = 0 con base por
encima de 60°, con factor publicado**. Buscado en las tres fuentes que el
propio encargo señalaba, y en una cuarta que apareció por el camino:

| Dónde | Qué hay | Base máxima en φ = 0 |
|---|---|---|
| Los 111 problemas del banco | 11 con φ = 0 y mitad no circular (29, 47, 73, 74, 75, 78, 83, 84, 85…). Sólo el 47 publica coordenadas de la superficie | 47: plano publicado a **44,17°** · 29: poligonal digitalizada, **43,4°** |
| Duncan, Wright y Brandon (2014), 2ª ed. de Duncan y Wright (2005) | §7.7.6 Ej. 6 «James Bay Dike»: φ = 0, **no circular**, tabla **dovela a dovela** (Fig. 7.29), F = 1,17 | **43,7°** |
| Documentación de la referencia sobre *Check m-alpha* | El origen del 0,2 y una remisión; ningún caso | — |
| USACE (2003), EM 1110-2-1902, Fig. G-9 — ya en la suite | φ = 0 en las doce dovelas, base de **+61°**, F = 1,35 | **61°**, pero la superficie **no** se publica como no circular |

**No existe.** Y las dos fuentes que más se acercan lo hacen por lados
opuestos: la G-9 tiene los 61° pero no la superficie no circular; la 7.29
tiene la superficie no circular pero se queda en 43,7°.

**Ching y Fredlund (1983)**, *Some difficulties associated with the limit
equilibrium method of slices*, Can. Geotech. J. — que la documentación de la
referencia cita como *«a more complete discussion of issues related to the
variable m_alpha»* — **es de pago y no está en `referencias/`. No se ha
leído y no se ha reproducido.** Se cita en el código con esa advertencia
escrita al lado, que es la lección de v0.1.84 aplicada a una nota al pie:
una referencia que se tiene de segunda mano no es evidencia, y disimularlo
es cómo una frase falsa consigue un pie de página.

**Por tanto el techo no se toca**: ni `M_ALPHA_LIMIT`, ni
`max_base_angle_deg`, ni el alcance de `_base_angle_ok`. El aviso de
v0.1.135 sigue siendo la única defensa, como manda el paso 3 del encargo.

### Lo que sí decidiría el techo, escrito para el día que aparezca el caso

Duncan, Wright y Brandon §14.4 es la fuente científica de las dos preguntas
abiertas de la ficha, y contesta las dos **como doctrina**:

- de dónde sale el 0,2: *«Whitman and Bailey (1967) suggested that when the
  Simplified Bishop procedure is being used and the value of m_alpha […]
  becomes less than 0.2, alternative solutions should be explored»*, y el
  mecanismo que protege es explícitamente **friccional** — *«negative
  stresses in frictional materials will produce negative shear strengths!
  […] if an automatic search is being performed to locate a critical slip
  surface, the search may suddenly pursue an unrealistic minimum as a
  solution»*, que es D61 impreso;
- el alcance: *«It is also helpful to place constraints on the inclination
  of the slip surface in an automatic search for a noncircular slip surface
  to avoid very steep slip surfaces being considered at the toe of the
  slope»*, con la guía de arranque *«45 degrees or less»* y la Fig. 14.17
  (Jumikis 1962) para el ángulo de la zona pasiva.

**Es doctrina, no un caso medido.** Aplicarla movería los casos de
validación, y el encargo lo prohíbe. Queda escrito aquí y no en el código.

---

## 2. El ancla: `tests/test_james_bay_v1158.py`

La Fig. 7.29 es una hoja de cálculo **publicada, dovela a dovela**, de una
superficie **no circular** en suelo **φ = 0**, resuelta por equilibrio de
fuerzas con θ = 2,7°. Es la clase de ancla que la regla 1 pide y que el
proyecto ya usa para los dos Corps of Engineers.

**Hasta esta versión el proyecto no tenía ni un solo caso de validación
externa con φ = 0 ni con superficie no circular**: los tres
`test_slide_validation_*` son círculos en suelos friccionales, y la tabla
de la EM en `test_modified_swedish_v198.py` es `c' = 0, φ' = 30` en todas
sus dovelas. Las dos anclas se hacen pinza: aquélla es el extremo de sólo
rozamiento de la misma recursión, ésta el de sólo cohesión.

**La ecuación de la Fig. 7.29 es la C-19 de la EM 1110-2-1902, término por
término**, así que la recursión que el proyecto ya tiene validada es la que
la reproduce. `_march` de `modified_swedish.py`, con el espejo a mano:

| Comprobación | Resultado |
|---|---|
| columna `Z` publicada (466 … −847) | peor desvío **16,3 sobre una escala de 6601 = 0,25 %** |
| raíz `Z_final = 0` | **1,17350** contra **1,17** publicado → **0,30 %** |
| con `c = 31,2` de la Fig. 7.24 en vez del 31,5 de la hoja | 1,16685 → 0,27 % |
| control: la misma hoja con θ = 0 | **1,08725**, un 7,1 % por debajo |

**Y la degeneración de D61 está PUBLICADA en esa figura.** La tabla trae
`n_α` para tres factores de prueba (1,0 / 1,2 / 1,4): para las dovelas
2–11, las de φ = 0, **el valor es el mismo en las tres columnas**; sólo
cambia el de la dovela 1, la única con φ = 30 (1,050 / 0,972 / 0,916). Lo
que la ficha D61 dedujo del código está impreso en una fuente externa.

**La geometría ata dos figuras publicadas independientes.** Marchando
`Δy = b·tan α` desde la coronación, la superficie baja por el trasdós
atravesando relleno (12 m), costra (4 m), marina (8 m) y lacustre (6,5 m),
corre **80,4 m plana sobre el techo del till** y vuelve a subir. Cierra a
**≤ 6,6 cm en cada contacto**, y **la capa que sale de la geometría lleva,
dovela a dovela, la cohesión que la otra figura le da**. Ni la 7.24
menciona a la 7.29 ni al revés.

**Y Spencer encuentra los DOS números que el libro publica.** El libro no
elige θ = 2,7°: lo reporta como lo que su procedimiento de Spencer
devuelve, y publica Spencer = 1,17 por separado. El Spencer de OGR, sin que
se le diga ninguno de los dos, da **F = 1,17508 (0,43 %) y λ = 0,0480, o
sea θ = 2,75°** contra el 2,7° publicado. Comprobado además que la única
cantidad de ese cálculo que la fuente **no** publica —la cota de coronación
de cada dovela— es **inerte bit a bit** sobre un rango de 118 m, así que el
ancla no descansa sobre ningún valor elegido aquí.

**El dato que cierra la búsqueda**: base máxima **57,2° global, 43,7° en
φ = 0** (la de 57,2° es la única dovela con rozamiento), contra
`acos(0,2) = 78,463°`. El caso publicado no calibra el techo porque el
techo **no le aprieta**.

### Lo que el ancla NO hace, y por qué

**No se construye la sección para que OGR la rebane.** Los pesos publicados
dicen que el dique tiene **berma** —`W/b` cae de 523,4 a 481,3 a 442,9 kPa
en las dovelas 5→8, así que el terreno sobre el llano no es la coronación—
y la Fig. 7.24 la da como dibujo, no como coordenadas. La única salida
sería invertir `W_i/b_i` para deducir el perfil: derivar la geometría del
mismo dato que la comparación debe poner a prueba, hasta que el número
salga. Es una instantánea con una cita encima, y la regla 1 existe para
prohibirla. El motivo va **en la cabecera del test**, no sólo aquí, para
que no se «arregle» dentro de tres versiones.

---

## 3. Cuatro correcciones, ninguna mueve un dígito

### D104 · El aviso de m-alpha se dirigía a la familia equivocada, cuatro veces

`m_alpha_margin_note` se emite una vez por método y terminaba siempre igual:
*«A method of moments is not reliable there. Compare against a
complete-equilibrium method such as Spencer before quoting it.»* Son
**cuatro** faltas, todas medidas sobre corridas reales del banco:

| Familia | Métodos | Qué se les decía |
|---|---|---|
| equilibrio completo | `spencer`, `gle_morgenstern_price` | que se comparasen **consigo mismos** (problemas 39, 47, 85, 95, 96, 12, 13) |
| fuerzas | `janbu_simplified/corrected`, `lowe_karafiath`, `corps_engineers_1/2` | «a method of moments», que no lo son (47, 51, 96, 12, 13, 95) |
| momentos | `bishop_simplified` | correcto, y se conserva palabra por palabra |
| momentos | `ordinary_fellenius` | **no forma ese denominador en absoluto** (51, 96) |

**El de Ordinary es el peor y es el que no estaba fichado.** Su normal es la
proyección de las fuerzas externas: la cadena `m_alpha` no aparece ni una
vez en `methods/ordinary.py`. La nota le decía que dividía la normal «por
un número cercano a cero, inflándola 2,0 veces» cuando no divide por nada.
Y Duncan, Wright y Brandon §14.4.2 lo nombra como **uno de los cuatro
remedios** de este mismo problema: *«very large or negative normal stresses
at the toe of the slope do not occur in the Ordinary Method of Slices […]
the Ordinary Method of Slices can be used»*. Ahora **calla**.

**La cuarta falta la habían medido las auditorías del banco (veredictos 57
y 83) y tampoco tenía ficha**: la nota estaba *«redactada al revés»*. Decía
`m_alpha down to 0.4641 … which clears the 0.2 limit by 0.2641` —un margen
**mayor que el propio límite**— y a continuación llamaba a eso *«a number
near zero»* que *«is not reliable»*. A 0,4641 la amplificación es 2,2×. La
nota informa del margen ahora, y no denuncia: dice el valor por el que
divide y deja que hable.

La firma de `m_alpha_margin_note` **no cambia**, y es deliberado: lee
`result.method_id`. Con un parámetro nuevo, la 0.1.157 habría dado
`TypeError` —un fallo estructural—; leyendo el id, el test la llama con la
misma firma, le pasa un resultado de Spencer y la 0.1.157 devuelve la
redacción de momentos, de modo que **el assert cae por comportamiento**.
Las familias salen de `SATISFIES_FORCE` / `SATISFIES_MOMENT`, que ya
existían: no se ha inventado ninguna clasificación. Duncan §14.4.1 separa
los dos denominadores —su Ec. 14.5 para Spencer, con su propia inclinación,
y la 14.6 para Bishop, *«identical … when the interslice force inclination
(theta) is set to zero»*—, que es lo que hace falsa la frase única.

### D105 · La docstring sostenía una decisión revocada, **en dos sitios**

`checks.py:35-36` afirmaba *«Both checks are **disabled by default**,
matching the reference»*. Falso desde v0.1.84: `check_m_alpha` es `True` en
`settings.py`, en `search.py` y en el mapeador legacy. **Setenta y cuatro
versiones**, de la 84 a la 157.

Y la misma frase vivía en un segundo sitio que no estaba fichado:
`search.py:470-476`, comentario de v0.1.32, **contradicho diez líneas más
abajo por el de v0.1.89, dentro de la misma función**. Dos comentarios que
se desmienten en un mismo cuerpo es cómo sobrevive la mitad falsa: quien
lee el primero, deja de leer.

Reescritas las dos, y añadido lo que no estaba en el código en ninguna
parte: que **un `m_alpha` por debajo de 0,2 no implica por sí solo que el
factor esté mal** —la fuente lo dice dos veces— y que el límite es por eso
un ajuste y no una ley.

### D106 · `max_base_angle_deg = 90` no afloja el techo: lo quita

`_base_angle_ok` lo lee como `if not (0.0 < limit < 90.0): return True`, y
el spinbox ofrece hasta 90,0 con un decimal. Quien quiere «casi sin límite»
teclea justamente el número que significa «sin límite», y nada se lo dice.
Regla 7.

Entra `_base_angle_ceiling_notes` en `settings_warnings`, calcada de
`_block_group_notes` (v0.1.156) y **acotada igual**: calla si el modelo no
lleva capa débil, porque ahí el ajuste es inerte diga lo que diga y una
línea en cada corrida sería ruido —la lección que v0.1.155 escribió al
preferir la agregación a una pared de avisos—. Y una etiqueta viva bajo el
spinbox, patrón `lbl_cpu` de esa misma página, porque el aviso del motor
llega **después** de calcular y quien elige el valor está mirando el panel
**antes**.

**El rango del spinbox NO se estrecha a 89,9, y es una medida y no un
olvido**: un proyecto ya guardado con 90,0 se enseñaría clampeado, y
`apply()` escribe el valor del widget, así que abrir el diálogo y pulsar
Aceptar convertiría el «sin techo» de ese proyecto en «techo de 89,9°».
Sería mover un dígito en el archivo del usuario para arreglar una etiqueta.

### D107 · Una afirmación refutada seguía en el diccionario de traducción

`ogr_gui/i18n/__init__.py` conservaba que el chequeo *«rejects the
reference-validated critical circle»* — refutado por v0.1.82, que midió
+0,9282 y no −0,0100. **Huérfana**: ningún widget la envolvía, cero
ocurrencias en todo el árbol fuera del diccionario. Retirada, con un test
que comprueba a la vez la ausencia y **por qué** era falsa, para que las dos
mitades no se separen. La lección: un diccionario de traducción también es
un sitio donde una afirmación equivocada sobrevive a la decisión que la
revocó, y **ningún test miraba ahí**.

---

## 4. Lo que se reporta y NO se corrige (regla 6)

Último defecto del banco: **D103** (v0.1.157). Estos van del D104.

- **D108 — la polilínea de bloque del 75 está en el nivel equivocado, y el
  motivo escrito para no compararla es falso.** El banco la asume sobre el
  contacto y = 7 razonando *«la capa más débil, c = 31.2 frente a 34.5»*, o
  sea el **techo** de la lacustre. La superficie **publicada** corre por el
  **techo del till** —y = 0 en coordenadas del banco, la **base** de la
  lacustre—, y ahí tiene su llano de 80,4 m. Y la ficha dice *«cuyas
  polilíneas el manual no publica»*: **sí las publica**, en las columnas `b`
  y `α` de la Fig. 7.29, que las reconstruyen a 6,6 cm.
- **D109 — OGR no implementa el objeto Block Search *Polyline*, sólo el
  *Line*.** `search.py` infiere el tipo por número de vértices y toma **un
  punto por objeto**; la referencia: *«a Block Search Polyline generates TWO
  points along the polyline. The slip surface will then be constrained to
  follow the polyline, BETWEEN the two points»*. El `.ogr` del 75 declara un
  objeto de **dos** vértices y OGR devuelve superficies de **tres**. Con la
  capa débil recorrida en un solo punto, el llano publicado es inalcanzable
  **por construcción**.

  **Y las dos cosas juntas están medidas**, que es lo que las convierte en
  la explicación del 75 y no en una sospecha. Sobre la superficie
  **publicada**, con el motor de hoy:

  | método | publicado | OGR sobre la superficie publicada | Δ | superficie asumida por el banco | Δ |
  |---|---|---|---|---|---|
  | Bishop | 1,105 | **1,127936** | **+2,1 %** | 1,611895 | +45,9 % |
  | Spencer | 1,167 | **1,175085** | **+0,7 %** | 1,823021 | +56,2 % |
  | GLE / M-P | 1,142 | **1,156025** | **+1,2 %** | 1,841683 | +61,3 % |

  El +29,0 / +48,8 / +37,4 % que la ficha del 75 publica son los mismos
  desvíos medidos contra los valores **optimizados**. En cualquiera de las
  dos formas, **el desvío del 75 es la superficie asumida, no el motor, y
  no m-alpha.** El banco está fuera de git y no se toca: esto se reporta.

- **D110 — hay dos techos y el que tiene nombre es el que no llega.** Bajo
  φ = 0, `M_ALPHA_LIMIT` equivale a **78,463°** y alcanza a **toda**
  superficie por `_is_admissible`; `max_base_angle_deg` tiene control en la
  interfaz, vale 80° y sólo alcanza a `WeakLayerSurface`. Quien teclee 45°
  sigue teniendo 78,463° sobre todo lo demás.
- **D111 — el chequeo evalúa el denominador de Bishop sobre métodos cuyo
  denominador es otro.** Janbu divide por `cos²α(1+s·tanα·tanφ/F)`; la
  familia de inclinación prescrita, por `cos(α−θ)+…`. Medido en la base
  φ = 0 más inclinada de la superficie publicada (−43,7°): `cos α = 0,7230`
  contra el `n_α = 0,6896` que publica la fuente, **4,8 %**. **Es heredado,
  no inventado aquí** —la referencia define el −112 con esa forma para todos
  los métodos—, y ésa es la razón para no tocarlo sin caso publicado. El
  test lo fija como **desigualdad**, etiquetada como medición y no como
  validación, precisamente para que nadie confunda las dos.
- **D112 — `_slide_sign` usa siempre la forma de Bishop.** Contra **Janbu**
  la divergencia es real y puede invertir el signo por dos vías: `w_total`
  incluye el agua embalsada y `tan` pesa las bases empinadas mucho más que
  `sin`. **Contra Bishop no**, y conviene decirlo con esa medida: `kv` está
  acotado a [−1, 1], luego `(1−kv) ≥ 0` y un factor constante no negativo no
  invierte una suma; coinciden en todo modelo alcanzable salvo en `kv = 1,0`
  exacto, donde la suma de Bishop es idénticamente cero. **Una ficha que
  exagera se descuenta entera**, así que el `(1−kv)` va escrito como
  discrepancia de forma y no de resultado.
- **D113 — la corrección de v0.1.67 entró en una de las dos funciones.**
  `base_effective_stresses` estima σ con `s.weight + water_weight`;
  `base_m_alphas`, mismo bucle diez líneas abajo, sigue con `s.weight`.
  Muerde donde la resistencia depende de σ **y** hay agua encima, que es
  justo el caso para el que se escribió la corrección.
- **D114 — la premisa de D61 es cierta sobre el denominador y demasiado
  fuerte sobre la consecuencia.** Que bajo φ = 0 `m_alpha ≡ cos α` es exacto
  y está anclado. Que por eso el chequeo *«deja de ser una afirmación sobre
  el método»* es cierto **en Bishop circular**: `(c·b + …)/m_alpha` con
  `tanφ = 0` da `c·ℓ` y `m_alpha` **se cancela exactamente**, así que ahí
  filtra por una cantidad que no toca el número. **No es cierto en
  `_general_moment_fos`**, que es la rama no circular y por tanto la de
  D61: `q` también se limpia, pero `normal = (w_n − (q/F)·sin α)/cos α`
  conserva el `1/cos α ≡ 1/m_alpha`, y `normals` entra en `moment_terms` con
  su propio brazo. **Ahí sigue amplificando algo real**, y es parte de por
  qué el techo no se toca.

---

## 5. Alcance y verificación

**Estructural, y es la primera barrera**: el `git diff` de
`ogr_slip2d/checks.py` y `ogr_slip2d/search.py` **no toca una sola línea
ejecutable** —sólo docstring y comentario— y `ogr_slip2d/methods/` no
cambia en absoluto. Los tres archivos donde vive el techo no cambian de
comportamiento **por construcción**, no por medición. El único código nuevo
del motor está en dos funciones que devuelven texto y en la que las agrega.

- Suite entera, sin argumentos: ver §6.
- **17 de los 58 tests nuevos fallan con el código de 0.1.157, y los
  diecisiete por comportamiento — ni un `ImportError`**: 6 de la redacción
  de la nota, 4 de la prosa contra los defectos, 5 del techo silencioso, 2
  de la traducción retirada. Los 22 del ancla de James Bay pasan también con
  0.1.157, y es lo correcto: es una medición de la regla 1, no una
  reparación.
- **Problema 75 con su objeto declarado**, contra sus valores congelados:
  ver §6.
- El ancla nueva no lleva ninguna de las tres subcadenas que el banco
  reserva —«stable» junto a «head», «edge of the search grid»,
  «path_optimize»—, comprobado en crudo **y** en minúsculas sobre las cuatro
  ramas de la nota y sobre la del techo, porque «unstable» contiene
  «stable» y «ahead» contiene «head».
- Entra además un **tripwire** que no existía: `interpret_window` decide el
  código −112 publicado buscando el literal `m_alpha` dentro de la razón que
  construye `check_surface`. Es un acoplamiento entre dos archivos a través
  de la ortografía de una palabra, decide un número que el banco compara, y
  no tenía **ni un test**. Ahora ata los dos extremos y **declara** que es un
  acoplamiento por cadena en vez de esconderlo.

---

## 6. Resultados de la verificación

**Suite entera, sin argumentos.** Línea base con 0.1.157: **3302/3302**.
Con 0.1.158: **3360/3360** (188 archivos). La diferencia son 3302 + 58, o
sea exactamente los tests nuevos: ni uno de los existentes cambia de
veredicto.

**Los 58 tests nuevos contra el código de 0.1.157**: **17 fallan, los
diecisiete por comportamiento y ni uno por `ImportError`**.

| Defecto | Tests que caen con 0.1.157 |
|---|---|
| D104, redacción de la nota | 6 — equilibrio completo, fuerzas, Ordinary mudo, «cercano a cero», valor enunciado |
| D105, la prosa contra los defectos | 4 — las dos frases falsas, las dos citas |
| D106, el techo silencioso | 5 — 90°, valores ≤ 0, y la etiqueta del panel |
| D107, la traducción refutada | 2 |

Los **22 del ancla de James Bay pasan también con 0.1.157**, y es lo
correcto: es una medición de la regla 1 y no una reparación. Se dice aquí
porque el proyecto pide la lista de fallos por comportamiento, y éste no
está en ella.

**Comprobación estructural de los cero dígitos.** El `git diff` de
`ogr_slip2d/checks.py` y `ogr_slip2d/search.py` no toca **una sola línea
ejecutable** —sólo docstring y comentario— y `ogr_slip2d/methods/` no
cambia en absoluto. Los tres sitios donde vive el techo no cambian de
comportamiento por construcción y no por medición.

**Problema 75 con su objeto de bloque declarado** (5000 superficies, 50
dovelas), contra sus valores congelados en 0.1.153 — **los seis coinciden
hasta el último dígito publicado**:

| método | ahora | congelado | válidas |
|---|---|---|---|
| `bishop_simplified` | 1,6118946113151422 | 1,611895 | 3160 / 3160 |
| `spencer` | 1,823020669904262 | 1,823021 | 2631 / 2631 |
| `gle_morgenstern_price` | 1,841682561319247 | 1,841683 | 2344 / 2344 |

Y los avisos de esa corrida son la otra mitad de la comprobación: el único
que sale es el de grupos de bloque de v0.1.156. **La nota nueva del techo
no dispara** —el 75 no lleva capa débil, que es exactamente el
acotamiento que se le puso— y ninguna nota de m-alpha aparece, igual que
en el JSON congelado. El acotamiento se sostiene sobre un modelo real del
banco y no sólo sobre el modelo de un test.

**Problema 74, que es el modelo del banco que SÍ emite la nota** (φ = 0 en
la cimentación, `modelo_path.ogr`, 5146 candidatas). Los cuatro factores
coinciden con sus valores congelados en 0.1.152 hasta el último dígito
publicado —1,1322124270514846 · 1,1675311655041234 · 1,0723069568155077 ·
1,2255309473089042, 5000/5000 válidas en los cuatro— y la redacción nueva
se ve sobre geometría publicada: Bishop conserva su frase palabra por
palabra, los dos Janbu dejan de llamarse métodos de momentos, y el «número
cercano a cero» pasa a ser el número — *«divides the normal force on that
base by 0.4755, inflating it 2.1-fold»*. Spencer no emite nota aquí, igual
que en el JSON congelado.

Y de paso deja un dato que vale para D61: esa base está a **61,6°** en
material φ = 0 —`cos 61,6° = 0,4755` exacto, la degeneración otra vez— y
ahí OGR queda a +1,1 % / −0,2 % de lo publicado. Por encima de 60°, con
φ = 0, y el resultado es bueno. No sirve como caso de cierre porque la
superficie es la que encuentra OGR y no una publicada, pero es una medida
más en contra de que el problema esté en el entorno de los 60°.

**No se ha corrido `verificar_cierres.py`**, y es una decisión: escribe en
`_auditoria/` del banco, que esta versión no toca. El criterio que ese
script lee queda fijado **dentro del repositorio**: hay test que pasa cada
nota nueva —las cuatro ramas de la de m-alpha y la del techo— por las tres
subcadenas que el banco reserva, en crudo y en minúsculas.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later
