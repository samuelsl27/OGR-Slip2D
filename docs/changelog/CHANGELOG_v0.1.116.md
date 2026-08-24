# OGR Slip2D v0.1.116

**El arrancamiento del refuerzo devolvía un marcador de posición, y lo que
faltaba no era una fórmula sino un número: la tensión efectiva sobre la lámina**

---

## De dónde salió

El encargo era la anomalía **A30-1** (defecto **D19** del banco), verificada en
0.1.97: `GroutedTiebackFriction.force_at` y `Geosynthetic.force_at` prometían en
su propio *docstring* una ley de Mohr-Coulomb de interfaz

    τ = adhesión + σ'_n · tan φ

y calculaban `tau_bond = self.adhesion`. `friction_angle_bond` y
`friction_angle_interface` estaban declarados en `PARAMETERS`, salían en el
diálogo, se guardaban en el `.ogr` — y **no los leía nadie**. Los otros dos
modos de arrancamiento devolvían `coefficient * 10.0` y `friction_factor * 10.0`,
marcadores de posición literales. Es la **regla 7** rota cuatro veces en un solo
archivo.

Lo primero fue volver a medirlo, porque el encargo traía medidas de dieciocho
versiones atrás. Reproduce entero en 0.1.115:

| caso | resultado |
|---|---|
| `Geosynthetic(tensile=200, adhesion=0).force_at(14.7, 28)` | 0,000 con φ = 0 **y** con φ = 33,7 |
| `Geosynthetic(tensile=200, adhesion=20).force_at(14.7, 28)` | 200,000 con φ = 0 **y** con φ = 33,7 |
| `pullout_mode="coefficient"`, Ci = 0,2 … 1,0 | 10,000 kN/m, **el mismo número para todo Ci** |
| `pullout_mode="friction_factor"`, F* = 0,2 … 1,5 | 10,000 kN/m, idéntico |

La respuesta era **binaria** —o nada, o la capacidad a tracción entera— y el
ángulo no movía un decimal.

### Dos correcciones al encargo, ninguna cambia el diagnóstico

1. **La evidencia era de `Geosynthetic`, no de `GroutedTiebackFriction`.** El
   encargo señalaba `support.py:475`, que es el tirante inyectado, pero los
   0,000 / 200,000 sólo salen con `tensile_capacity = 200`, que es el
   geosintético del **problema 30** (Borges y Cardoso: «not anchored, no
   adhesion, tensile 200 kN/m, 33,7°»). El tirante con sus valores de fábrica da
   26,389 kN/m en ese punto. El defecto es el mismo en las dos clases; la medida
   pertenece a una.

2. **El problema 50 no estaba bloqueado por esto.** Su tabla 50.2 se titula
   *Soil Nail Properties* y da `bond strength` en lb/ft: SNAILZ modela el
   geotextil como bulones equivalentes y `SoilNail` ya implementaba eso. Lo que
   lo bloquea es A48-1 y D09, como decía la comparativa y no la ficha del
   defecto.

Y sobre «trece problemas»: el **39** ya corría y sus cinco `.ogr` **no llevan un
solo soporte** (lo que le falta son las tablas 39.6–39.9, que son una *fuerza
requerida* por retroanálisis, no una capacidad de arrancamiento); el **30** y el
**31** siguen bloqueados además por F23-1 (comprobado: no hay ningún modelo de
resistencia con datum en `builtin_models.py`). Lo que este arreglo desbloquea
solo son **los ocho de geotextil, 87–94**, y son los que se han hecho.

---

## La formulación, y de dónde sale cada término

Nada de esto se dedujo. Cada ley tiene su fuente y las tres se comprueban
contra una forma cerrada en los tests.

**Ley lineal** — Mohr-Coulomb sobre la interfaz suelo/refuerzo, la formulación
clásica del *bond* de un geotextil en **Jewell (1996)**:

    τ(s) = a + σ'_n(s) · tan δ

**Ley hiperbólica** — **Esterhuizen, Filz y Duncan (2001)**:

    τ(s) = a_∞ · σ'_n · tan φ_0 / (a_∞ + σ'_n · tan φ_0)

y en ella `a_∞` **no** significa lo que `a` en la lineal: es la resistencia
límite cuando σ_n → ∞, no la resistencia a σ_n = 0. Los tests la anclan por sus
dos límites definitorios —pendiente tan φ_0 en el origen, asíntota a_∞— porque
esa confusión es el error que el propio artículo advierte.

**Coeficiente de interacción** — una fracción de la resistencia del **suelo que
rodea la lámina**, el *bond coefficient* de **Jewell (1996)**:

    τ(s) = C_i · τ_suelo(σ'_n(s))

Se evalúa preguntándole su resistencia al **modelo del material**, no leyéndole
una cohesión y un ángulo: así vale para los veinte modelos del programa y no
sólo para Mohr-Coulomb, y es la respuesta honesta donde habría que inventarse
un «valor equivalente». Para un suelo Mohr-Coulomb es `C_i·(c + σ'_n·tanφ)`.

**Factor de rozamiento** — **FHWA-NHI-10-024** (Berg, Christopher y Samtani
2009), **ecuación 3-2**, leída en el propio manual:

    P_r = F* · α · σ'_v · L_e · C

Esa ecuación publicada resuelve **tres** cosas de golpe, y las tres estaban mal
o sin decidir:

- `C = 2` para láminas, «*the reinforcement effective unit perimeter*» —
  el factor dos no es una elección de modelado, es que una lámina tiene dos
  caras;
- `σ'_v` es «*the effective vertical stress at the soil-reinforcement
  interfaces*» — efectiva, no total;
- **`L_e` es la longitud embebida «*in the resisting zone behind the failure
  surface*»**, y hasta esta versión OGR usaba el **lado más corto** de los dos,
  `min(L_a, L_b)`. Eso coincide con `min(F1, F3)` sólo mientras τ es uniforme y
  la resistencia de conexión es cero, que es precisamente el caso en que nadie
  lo notaría.

El factor de escala α no es una entrada aparte: se multiplica dentro de F*.

**Un cambio de comportamiento que conviene decir en voz alta**: separar F₁ de F₃
cambia lo que vale una lámina **en sus dos extremos**. Antes, con el lado más
corto, en la cabeza salía la capacidad a tracción entera; ahora sale la
resistencia de conexión, que por defecto es cero. Es lo que dibuja el diagrama
de fuerza publicado —arranca en C, sube por descabezamiento, se aplana en
tracción y baja por arrancamiento hasta cero en la cola— y devolver la tracción
entera donde no hay ni un metro de lámina dentro de la masa era, sencillamente,
falso.

---

## De dónde sale σ'_n, y por qué no del contexto de dovela

El encargo apuntaba a `SliceContext`, que trae `sigma_v_eff`, `depth` e
`y_base`. **No sirve de vehículo**, y decirlo importa porque la razón es la que
hace todo lo demás posible: `SliceContext` describe la **base de una dovela** y
lo puebla el solver **por superficie de ensayo**, mientras que la tensión a lo
largo de un refuerzo depende sólo de lo que tiene encima — y por tanto **no
depende de la superficie de ensayo en absoluto**.

De ahí sale el diseño: `ogr_core/support/bond.py` construye un `BondProfile`
—τ muestreada en 50 segmentos a lo largo del refuerzo, con la integral
acumulada— **una vez por análisis** y no una vez por superficie. Medido: una
rejilla 8×8 sobre un modelo de 15 láminas llama a `build_bond_profile`
**15 veces**, una por lámina, no 15 × el número de superficies. Sin eso el
arreglo habría sido inaplicable: son 50 pesos de columna por refuerzo.

La caché vive en el `Project` y `regions_frozen()` la limpia al entrar, que es
el mismo contrato con el que ya funcionaban la caché de regiones y la del
*bounding box*. Un perfil rancio es imposible: dentro del bloque el proyecto no
cambia por contrato, y fuera se recalcula siempre.

`SliceContext` **sí** se reutiliza para lo que es: preguntarle su resistencia al
material en el modo C_i, con el ángulo del propio refuerzo como ángulo de base,
que es el plano que interesa en un modelo anisótropo.

---

## Un segundo ajuste inerte, al lado del primero

Buscando el que venía a arreglar apareció otro: **`Geosynthetic.reference_elevation`**
estaba declarado, era editable, se serializaba desde v0.1.14 — y no lo leía
nadie. En la guía pertenece a un F* que varía con la profundidad, que el
programa no tenía.

No se ha quitado: se ha implementado. F* interpola linealmente entre su valor a
`reference_elevation` y `friction_factor_at_depth` a `reference_depth` por
debajo, y se mantiene constante fuera de ese tramo — extrapolar una recta
ajustada más allá de sus datos acabaría dando F* negativo. Con
`reference_depth = 0` es el modo constante de siempre.

---

## Lo que cambia en el número

Nada, para un modelo que no usara ninguna de las cuatro entradas muertas. La
compatibilidad hacia atrás es exacta y está en el test: con `bond=None` la ley
se evalúa a σ'_n = 0, que para una interfaz descrita **sólo por adhesión** es la
respuesta correcta, y reproduce dígito a dígito los números de 0.1.115
—200,0 / 0,0 del problema 30, 26,38937829015426 del tirante, y los tres asertos
de `test_supports_v114.py`, que no se han tocado.

Para todo lo demás cambia mucho, y esa es la idea.

### Entradas nuevas del geosintético

| entrada | defecto | por qué ese defecto |
|---|---|---|
| `strip_coverage` (A, %) | 100 | una lámina continua; ningún modelo actual se mueve |
| `connection_strength` (C) | 0 | la fuerza en la cabeza del diagrama de hoy |
| `anchorage` | `none` | los tres modos posibles, que es lo de hoy |
| `shear_strength_model` | `linear` | la hiperbólica es opcional |
| `friction_factor_mode` | `constant` | `function` activa F*(profundidad) |
| `reference_depth`, `friction_factor_at_depth` | 0 / 0,6 | pareja de `reference_elevation` |

`anchorage` decide **sólo si el arrancamiento es posible**: un extremo embebido
anclado es una condición de contorno, no una adherencia mayor, así que el modo
desaparece del mínimo en vez de hacerse grande. Y las dos formulaciones de la
guía —la antigua, «anclado al paramento ⇒ no hay descabezamiento», y la actual,
«el descabezamiento siempre es posible y arranca en C»— son **la misma** con
C = capacidad a tracción, porque entonces F3 ≥ F2 siempre. Una entrada cubre las
dos versiones.

---

## Los ocho problemas de geotextil (87–94)

### La geometría no era irrecuperable

Las ocho fichas decían «figura sin vértices rotulados» y de ahí
`confianza_geometria: baja`. **La sección está sobredeterminada por cuatro
anclajes independientes que concuerdan**, y ninguno de ellos es «lo que hace
que salga el número publicado»:

1. **Los círculos publicados de los ocho.** Siete afloran en x = 6,000
   exactamente y los ocho llegan a y = 15,000. El 91, con el cimiento debilitado,
   aflora en (−1,552 · 6,000) — sobre el cimiento y a la izquierda del muro. Dos
   caminos distintos fijan lo mismo: **pie en x = 6, cimiento en y = 6,
   coronación en y = 15**.
2. **Leshchinsky y Han (2004)**: muro de **9 m** y retranqueo de **1,2 m** en el
   caso estático de tres bancadas. Y 15 − 6 = 9.
3. **Los ejes de la figura 87.1**, medidos píxel a píxel: marcas cada 2,5 m en x
   a 78,64 px/m y cada 5 m en y a 61,20 px/m. La figura **no es isótropa** —es
   una captura reescalada—, así que las dos escalas se miden por separado, y no
   verlo habría metido un 28 % de error en una dirección.
4. **Las quince láminas dibujadas**, leídas con esas escalas: y = 6,340 / 6,912 /
   7,500 / 8,121 / 8,693 … 14,722, que son 6,3 / 6,9 / 7,5 … 14,7 con error
   máximo **0,03 m** — quince capas a 0,60 m. Y sus extremos izquierdos, 6,409 /
   7,604 / 8,800, dan un retranqueo de **1,195 y 1,196 m**: el 1,2 m del
   artículo, **medido sobre la figura sin haberlo supuesto**.

El único número que la calibración no cierra sola es el ancho de la columna de
bloques (el mascarón del refuerzo la tapa; lo medible es ≥ 0,18 m). Se toma
0,20 m, que es lo que hace cuadrar a la vez las otras dos medidas: las láminas
dibujadas miden 6,09 m contra los 6,3 m de la tabla 87.2, y sus extremos
derechos caen en 12,50 / 13,70 / 14,90 = cara + 0,2 + 6,3.

### Dos hallazgos sobre el propio manual

- **El 91 NO tiene «la misma geometría que el 87», aunque su enunciado lo
  diga.** Su modelo llega a **x = −2**, no a x = 0, y **tiene** que llegar: su
  círculo publicado aflora en x = −1,552, fuera de la sección de los otros
  siete. Con la sección de los siete, OGR no producía **ninguna** dovela sobre
  el círculo publicado y el problema no daba resultado. Con x = −2 pasa a ser
  **el mejor acuerdo de los ocho**.
- **El retranqueo del 94 no es 1,2 m sino 0,6.** Medido sobre la figura 94.1:
  0,632 / 0,589 / 0,610 / 0,589. Y 4 × 0,6 = 2,4 m, **exactamente el mismo
  retroceso total** que 2 × 1,2 del muro de tres — que es como se compara
  «efecto del número de bancadas» a talud global constante. El pie de la figura
  94.1 dice «A Three-Tiered Wall» y el enunciado dice cinco; la figura dibuja
  cinco.

### Una hipótesis que un solo problema habría hecho aceptar

Sobre la resistencia de conexión no hay dato en el manual, así que se corrieron
las dos hipótesis. En el **problema 88**, C = 0 daba Spencer **+1,0 %** contra
**+5,4 %** de C = T: convincente. Con los ocho delante deja de serlo — 88, 89 y
93 mejoran con C = 0, y **87, 90, 92 y 94 empeoran**. No es sistemática, así que
no se elige por el número: se declara la que dice la guía (conectado al
paramento, C = T) y el `.ogr` de la contraria se guarda al lado como
`modelo_sin_conexion.ogr` para que la medida esté a mano.

### Lo que dan

Columna circular de la tabla NN.3, mínimo de la búsqueda con la **misma
rejilla para los ocho**, elegida antes de mirar ningún resultado por cubrir los
ocho centros publicados:

| # | Bishop | Spencer | GLE/M-P |
|---|---|---|---|
| 87 | +32,2 % | **−2,9 %** | −7,4 % |
| 88 | +8,5 % | +5,2 % | +5,0 % |
| 89 | +20,0 % | +12,3 % | +12,6 % |
| 90 | +26,5 % | **−5,0 %** | −5,3 % |
| 91 | **+2,9 %** | **+4,7 %** | **+3,7 %** |
| 92 | +15,7 % | −12,2 % | −11,1 % |
| 93 | +38,1 % | +9,4 % | +9,7 % |
| 94 | +30,0 % | −8,1 % | **−4,1 %** |

Seis filas pasan a REVISAR y el resto a DISCREPANCIA; los ocho salen de
OMITIDO, que es lo que pedía el criterio de cierre. **El 91 es el mejor de los
ocho en los tres métodos** — y no es casualidad: es el único cuyo mecanismo
crítico baja al cimiento débil en vez de salir por la cara del muro.

Dos avisos que el propio motor de OGR levanta y que conviene leer: la búsqueda
libre encuentra mínimos que **afloran a 90° por la cara vertical** de una
bancada y con el centro en el borde inferior de la rejilla. Son fallos
**locales de una bancada**, y el enunciado del 87 dice literalmente *«the global
slope failure, not the local failure at each tier, is of interest»*. Por eso la
columna del círculo publicado, donde la hay, es la comparación limpia; el mínimo
de la búsqueda se registra igual, con su aviso.

---

## El defecto NUEVO que sale de correrlos, medido y NO corregido

Es el hallazgo más caro de esta versión y no es el defecto que se venía a
arreglar, así que se reporta antes de tocarlo (**regla 6**).

**Sin refuerzo, Bishop y Spencer coinciden dentro del 0,4 % en los siete
problemas que dan resultado. Con refuerzo se separan entre el 14 % y el 40 %** —
y el manual publica su Bishop y su Spencer de acuerdo dentro del 0,5 % en cuatro
de los ocho.

| # | sin refuerzo B / S | con refuerzo B / S | publicado B / S |
|---|---|---|---|
| 87 | 0,5492 / 0,5488 | 1,4114 / 1,0466 | 1,040 / 1,097 |
| 88 | 0,7031 / 0,7046 | 1,1970 / 1,0988 | 1,045 / 1,043 |
| 89 | 0,7416 / 0,7415 | 1,1485 / 1,0098 | 0,976 / 0,971 |
| 90 | 0,5388 / 0,5388 | 1,2286 / 0,9194 | 1,004 / 1,002 |
| 92 | 0,4242 / 0,4225 | 1,2204 / 0,8734 | 1,037 / 1,111 |
| 93 | 0,5285 / 0,5282 | 1,3795 / 1,0208 | 0,958 / 0,957 |
| 94 | 0,5508 / 0,5505 | 1,4082 / 1,0477 | 1,040 / 1,129 |

Eso **descarta la geometría, los materiales, el agua, la sobrecarga y el
dovelado**: los dos métodos ven lo mismo hasta que aparece el refuerzo, y el
refuerzo les entrega exactamente la misma `force_at` (Σ|F| es idéntica para los
dos).

**El término responsable está nombrado**: anular `n_press · tanφ'` en el
numerador de Bishop lleva los cuatro problemas medidos de +35,7 / +14,5 / +22,4 /
+44,0 % a **−1,0 / +4,6 / −7,5 / +5,9 %**. Es T_N·tanφ', la resistencia
friccional que moviliza la componente normal del refuerzo.

**Dos explicaciones plausibles se midieron y se descartaron**, que es la parte
que merece recordarse:

- **Dividir el término pasivo por F**, como Spencer hace desde 0.1.115 y Bishop
  no. Deja Bishop en +27,5 / +10,1 / +15,1 / +18,0 / +13,2 / +35,6 / +27,2 %.
  Explica una parte y no es la causa.
- **La orientación de la fuerza.** La guía dice expresamente que para una lámina
  la orientación **no** se supone paralela y ofrece cuatro. Con tangente a la
  superficie `n_press` sale exactamente 0,00 — y Bishop **sigue** en +29,9 /
  +10,8 / +11,5 / +16,9 / +12,0 / +36,9 / +29,5 %. Tampoco es la causa.

**Y el problema 91 lo confirma por el otro lado**: es el único cuyo círculo
crítico atraviesa el cimiento débil en profundidad, cruzando las láminas con la
base tendida en vez de a 56°, y ahí Bishop sale a **+1,3 %**. El desvío escala
con |sen α| en los cortes del refuerzo, que es justamente lo que multiplica a
T_N.

No se corrige aquí. Las ecuaciones publicadas del programa de referencia
**incluyen** T_N·tanφ' en el numerador de los métodos de cociente, así que
quitarlo sin más contradiría la formulación documentada; y v0.1.115 ya dejó
escrito que el arreglo evidente de la familia vecina se midió y no valía. Queda
como defecto abierto con causa nombrada y tres hipótesis ya descartadas.

---

## Archivos

| archivo | qué |
|---|---|
| `ogr_core/support/bond.py` | **nuevo** — `BondProfile`, `build_bond_profile`, `sigma_v_effective_at`, `soil_shear_strength_at` |
| `ogr_core/support/support.py` | `interface_shear` (lineal e hiperbólica), `interface_tau` por tipo, `force_at(..., bond)`, entradas nuevas del geosintético, F*(profundidad) |
| `ogr_core/support/__init__.py` | exporta lo nuevo |
| `ogr_core/project/project.py` | `_support_bond_cache`, limpiada al entrar en `regions_frozen()` y en cada invalidación |
| `ogr_slip2d/support_integration.py` | `_bond_profiles`, y `force_at` recibe el perfil |
| `ogr_gui/dialogs/define_support_dialog.py` | `_CHOICES`, los desplegables de cadena envueltos en `tr()` — incluidos los tres de `pullout_mode`, que estaban sueltos |
| `ogr_gui/i18n/__init__.py` | once traducciones nuevas |
| `ogr_gui/canvas/graphics_items.py` | el *tooltip* construye un perfil real en vez de leer 0 kN/m |
| `tests/test_support_pullout_v1116.py` | **nuevo**, 42 tests |

## Qué se probó

- `tests/test_support_pullout_v1116.py`, **42 pasan**: la identidad cerrada
  σ'_v = γz, la ecuación 3-2 de la FHWA con C = 2 a 1e-9, la linealidad en L_o y
  en σ'_v por separado, la flotación (γ' exacta), los dos límites de la
  hiperbólica, C_i contra la resistencia del propio material, la continuidad de
  `force_at` a lo largo del refuerzo con paso fino, la invariancia al número de
  segmentos, la forma del diagrama publicado, y la regla 7 sobre las ocho
  entradas.
- `tests/test_supports_v114.py`, **73 pasan sin tocarlos** — la
  retrocompatibilidad.
- Los ocho modelos del banco, construidos y corridos.

## Qué falta por probar

- El defecto nuevo de arriba: por qué la referencia no separa Bishop de Spencer
  con refuerzo y OGR sí.
- La columna **no circular** de los ocho problemas: sólo se ha hecho la circular.
- Los problemas **30, 31 y 32**, que siguen omitidos por F23-1 y por geometría,
  y el **39**, cuyas tablas reforzadas son un retroanálisis con Spencer que la
  función de retroanálisis actual no cubre (sólo Bishop y los dos Janbu).
- Las tres copias de «qué hay encima de este punto» —`_column_weight`,
  `_loading_bands` y ahora `sigma_v_effective_at`— deberían ser una. Unificarlas
  toca el bucle caliente del dovelado y no era esta tarea.
