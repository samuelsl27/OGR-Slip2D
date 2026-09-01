# OGR Slip2D v0.1.144

**El encargo no pedía arreglar nada: pedía DECIDIR. Y lo que la decisión
destapó es que las dos formulaciones no compiten — se reparten el mundo
según DÓNDE esté el agua, y eso no lo decía ninguna de las cinco líneas
de evidencia que llevaban dos versiones escritas. El guardián que la
decisión mandaba escribir NO se escribió, y esa es la segunda cosa que
enseña: los cuatro criterios candidatos se midieron y los cuatro fallan.**

Cierra **D20 / A55-1**, que estaba re-enunciado desde v0.1.117 como
decisión de producto. El predeterminado de
`MethodsSettings.interslice_forces` pasa de `effective` a **`total`**.

---

## La decisión, y por qué no había un criterio numérico

Los tres métodos que **prescriben** la inclinación interdovela —Lowe y
Karafiath (1960) y los dos Corps of Engineers de USACE (2003) EM
1110-2-1902 §C-4a— pueden formularse con la resultante de cara efectiva o
total. La norma da las dos por válidas y advierte de que el factor de
seguridad difiere. Desde v0.1.98 el ajuste existe; hasta hoy el
predeterminado era `effective`.

El criterio de cierre que la ficha llevaba escrito era **insatisfacible**,
y eso ya se sabía: pedía a la vez relación con Bishop > 1 en los problemas
51, 55 y 56 (exige totales) e invarianza con el calado en el 70 (exige
efectivas), y una identidad analítica demuestra que con totales esa
familia **no puede** ser invariante. No hay un valor que cumpla las dos.

Se elige **totales**, con cinco líneas de evidencia que apuntan al mismo
sitio: la referencia lo declara por escrito citando a Duncan, Wright y
Brandon §6.8.1; EM §C-4a lo recomienda para esta hipótesis; §G-5a dice que
su propio ejemplo resuelto está en fuerzas totales — y ese ejemplo es el
que este motor reproduce **dovela a dovela** desde v0.1.98; tres
implementaciones independientes (la referencia, UTEXAS4 y Zhu 2003) ponen
Lowe-Karafiath por encima de Bishop con freática; y con totales tres
valores publicados salen dentro del 0,25 %.

### Remedido en 0.1.143 antes de tocar nada

Las cifras de la ficha eran de 0.1.116/0.1.127, y entre medias entraron
D39/D42/D44 (0.1.137) y D48r (0.1.143), capaces de moverlas. No las
mueven, ni un dígito:

| caso | método | `effective` | `total` | publicado |
|---|---|---|---|---|
| 55 | lowe_karafiath | 1,25346 | **1,31520** | 1,318 · UTEXAS4 1,32 |
| 56 | lowe_karafiath | 1,24744 | **1,30259** | 1,304 · UTEXAS4 1,31 |
| 56 | corps #1 / #2 | 1,25477 / 1,27754 | 1,30949 / 1,34740 | — |

Bishop, Spencer, Janbu y GLE dan el mismo número en las dos columnas, en
los dos problemas: la comparación es del método, no de la geometría.

---

## Lo que el encargo no tenía, y cambia la forma del cambio

### 1 · Cambiar el predeterminado NO mueve el banco

`ProjectSettings.to_dict` guarda el bloque `methods` entero
(`asdict`), así que **todo proyecto salvado desde v0.1.98 lleva el campo
escrito**: **86 de los 88 modelos del banco fijan `"effective"` en el
`.ogr`**. Un cambio de predeterminado alcanza sólo a proyectos nuevos y a
archivos anteriores a v0.1.98. Por eso re-guardar los modelos del banco es
**parte del trabajo** y no una comprobación, y por eso hay un test que
comprueba que un proyecto que guardó `effective` lo conserva.

### 2 · El valor espurio era alcanzable HOY

Con el predeterminado anterior, cualquiera que eligiera `total` —una
opción legítima según la norma— podía obtenerlo. Medido en 0.1.143 sobre
el círculo publicado del problema 70 con 50 dovelas:

| | lámina a 75 ft | lámina a 105 ft |
|---|---|---|
| lowe_karafiath | 5,0 · `converged=False` | **0,22043 · `converged=True`** |
| corps #1 y #2 | 5,0 · `converged=False` | 5,0 · `converged=False` |

El 0,22043 es el peor de los tres: convergido, plausible y mudo. El aviso
hacía falta **con cualquiera de los dos predeterminados**; no es el precio
de haber cambiado éste.

---

## El hallazgo que no estaba previsto: el reparto es por DÓNDE está el agua

La suite lo encontró sola. `test_drawdown_methods_v1108` compara contra el
Apéndice G de la EM 1110-2-1902 —**el mismo apéndice cuyo §G-5a declara
fuerzas totales**— y con totales Lowe-Karafiath **empeora**:

| método | procedimiento | `effective` | `total` | publicado |
|---|---|---|---|---|
| lowe_karafiath | Corps 2 etapas | +0,71 % | +1,84 % | 1,35 |
| lowe_karafiath | DWW 3 etapas | +1,19 % | **+3,85 %** | 1,44 |
| corps #1 | DWW 3 etapas | +3,56 % | +6,11 % | 1,44 |
| corps #2 | DWW 3 etapas | +5,44 % | +7,92 % | 1,44 |

Bishop, Spencer y GLE no se mueven un dígito entre las dos columnas, que
es lo que dice que esto es la hipótesis y no el procedimiento de
desembalse.

**No contradice la evidencia de arriba: la ordena.** El Apéndice G es un
embalse apoyado contra el paramento —103 ft de agua sobre un terraplén
cuya coronación está a 110—, mientras que el 51, el 55, el 56 y el Ej_2
tienen el agua **dentro** del talud. Los dos anclajes no discuten cuál es
el convenio correcto: se reparten según **dónde** está el agua.

- agua **dentro** del talud → totales reproducen lo publicado al 0,25 %;
- agua **encima** del talud → la hipótesis de inclinación prescrita exige
  una componente vertical que una presión horizontal no da, y efectivas es
  lo único que sobrevive.

Y eso es exactamente lo que dispara la nota nueva. En el modelo del
Apéndice G la nota salta; en el 55, que está empapado de pie a coronación,
**calla**. Ese control es el que le da sentido: una nota que sonara
también ahí estaría avisando del agua y no de la hipótesis.

---

## El guardián que NO se escribió, y los cuatro criterios que lo mataron

El encargo pedía —y la decisión confirmó— rechazar la raíz espuria en vez
de publicarla. Se midieron cuatro criterios para reconocerla. **Los cuatro
fallan**, y el cuarto sólo se cayó al mirar la población entera, no los
círculos publicados.

Los tres primeros, todos razonables y todos falsos:

1. **El residuo relativo.** Se suponía que 0,22043 era un polo disfrazado.
   No lo es: `Z_n = −0,000`, `|Z_n|/max|Z_i| = 8,6e−12`. Es un cero
   legítimo del residuo de cierre, y por eso la guarda de admisibilidad
   que `_march` ya tiene —la que rechaza `D_i ≤ 0`, escrita justamente
   contra los polos— no lo ve.
2. **La tracción neta interdovela**, que es el criterio con el que Spencer
   y GLE rechazan sus raíces espurias desde v0.1.106
   (`thrust_is_admissible`). Tampoco: `sum(Z_interior)` sale **negativo en
   las dos**, en la buena y en la espuria. No las separa.

Y un tercero que también se midió y **también** se cayó: **contar dovelas
con la base en tracción**. En el problema 51 hay raíces legítimas con 1 y 2
dovelas de 95 en tracción (min N −262 y −1066), a 0,75 de camino del pie —
no en la coronación, donde la tracción sí es legítima. Un criterio de
recuento con umbral 1 se come raíces buenas, y con umbral 3 no ve la
espuria, que aquí tiene 1.

El cuarto candidato sí las separaba **sobre los círculos publicados**: la
**inversión del empuje interdovela** —la mayor fuerza que empuja contra el
sentido dominante de la propia marcha— deja todas las raíces que
reproducen un valor publicado por debajo del 2,3 % del pico, y la espuria
llega al **27,9 %**. Doce veces de separación sobre 30 filas.

La medida se toma **contra el sentido dominante** y no contra un signo
fijo, y no es un detalle: `_force_balance` prueba dos orientaciones de
marcha y la reflejada niega todos los signos. Medir contra un signo fijo
es el fallo que `prepare_rows` documenta para la recursión de GLE, donde
puso las 39 caras del problema 26 en falsa tracción. Con el criterio
ingenuo, dos de las filas medidas daban 1,0 —traccionadas del todo— y con
el sentido dominante dan 0,0.

### Y aun así NO se veta con él, porque 30 filas no eran la población

Antes de escribir el guardián se midió lo que de verdad decide: **las
22 000 superficies que evalúan las búsquedas de los nueve modelos**, en
los dos modos. Los círculos publicados no eran representativos ni de
lejos:

| modelo | superficies convergidas | por encima del 5 % | por encima del 20 % | p99 |
|---|---|---|---|---|
| 55 `effective` | 4605 | **1087** | 119 | 0,289 |
| 51 `effective` | 1511 | 144 | 61 | 0,420 |
| 59 `effective` | 377 | 325 | 297 | **1,000** |
| 60 `effective` | 33 | 17 | 13 | 0,951 |
| 56 `effective` | 4392 | 2 | 2 | 0,005 |

El 59 y el 60 tienen el percentil 99 en **1,0 con fuerzas efectivas**, que
es el ajuste validado contra la referencia. Un veto al 5 % marcaría 1087
de las 4605 superficies del 55, cuyo círculo crítico reproduce a Pockoski
y Duncan (2000). Y marcar no es gratis: `SearchResult.critical` **excluye
las inadmisibles**, así que el guardián cambiaría la superficie que se
reporta en modelos que no tienen ningún problema.

**Condición de parada del plan, cumplida.** El plan decía: *si alguna raíz
legítima presenta tracción fuera de la coronación, el criterio no vale;
entonces se implementa sólo la nota y se dice por qué, en vez de inventar
un umbral.* Eso es lo que se ha hecho. La inversión se publica como
**diagnóstico** en `details["thrust_reversal"]` —una marcha por superficie
sobre las dieciséis o más que ya gasta el buscador de raíces— y no veta
nada; hay un test que lo dice, para que quien lo conecte tenga que venir a
explicarlo.

### Y la medición trajo algo peor de lo que decía la ficha

Sobre el 70 con totales, el síntoma no es un círculo desafortunado: **la
búsqueda entera colapsa**. Las tres familias devuelven F ≈ 0,2000 —el
suelo mismo de la rejilla de arranque— como superficie crítica, sobre
miles de superficies, donde con efectivas devuelven 1,6087. Por eso la
nota no dice «menos exacto» sino **«trata estos números como no fiables»**,
y hay un test que comprueba justamente esa palabra.

*(Una columna de la medición no midió nada y se dice: `mueve_la_critica`
sale `True` incluso donde se marcan 0 superficies, porque compara el
mínimo de las convergidas contra `critical`, que puntúa también las no
convergidas. No se ha usado para decidir nada.)*

*(Y un hueco del diagnóstico, anotado: no sobrevive al envoltorio de
desembalse. Los problemas 95 y 96 tienen `rapid_drawdown` activo, y el
`LEMResult` que devuelve el envoltorio no arrastra los `details` del
método interior, así que ahí `thrust_reversal` no llega.)*

---

## Hallazgo reportado y NO corregido (regla 6)

`PrescribedInclinationMethod._force_balance` **recibe `slide_sign` y no lo
usa en ninguna línea**: la orientación de marcha se elige por «la primera
que bracketee», no por el sentido de deslizamiento del que se acaba de
calcular. Y ordenarlo por `slide_sign` **no** es el arreglo: en el
problema 70 la raíz buena sale de la orientación que contradice a
`slide_sign` y la espuria de la que coincide. Tocarlo movería casos ya
validados. Queda anotado en `docs/PENDIENTES.md`.

---

## El banco: los nueve modelos, antes y después

Los nueve `.ogr` que habilitan un método de esta familia se re-guardaron con
`interslice_forces: "total"` (`_tools/migrar_d20_totales.py`) y se
recorrieron enteros. La tabla es un **A/B en la misma versión**, cambiando
sólo el ajuste, que es la única forma de que la diferencia sea el ajuste:

| caso | método | `effective` | `total` | dif |
|---|---|---|---|---|
| 27 | los tres | 0,3102 / 0,3295 / 0,3295 | idénticos | 0,00 % |
| 40 | los tres | 0,9654 / 0,9690 / 0,9706 | idénticos | 0,00 % |
| 51 | lowe-k | 0,9251 | 0,9650 | +4,31 % |
| 55 | lowe-k | 1,2498 | **1,3136** | +5,10 % |
| 56 | lowe-k | 1,2398 | **1,3010** | +4,93 % |
| 59 | lowe-k | 0,4916 | 0,5611 | +14,13 % |
| 59 | corps #1 | 0,3424 | 0,5355 | +56,37 % |
| 60 | los tres | 1,5651 / 1,5879 / 1,5414 | idénticos | 0,00 % |
| 95 | corps #1 | 1,4183 | 1,4259 | +0,54 % |
| 96 | corps #1 / #2 | 1,4747 | 1,4627 | −0,81 % |

Y contra lo publicado, que es lo que decide:

| caso | publicado | error `effective` | error `total` |
|---|---|---|---|
| 55 lowe-k | 1,318 | −5,18 % | **−0,34 %** |
| 56 lowe-k | 1,304 | −4,92 % | **−0,23 %** |
| 59 lowe-k | 0,588 | −16,39 % | **−4,58 %** |
| 51 lowe-k | 1,288 | −28,17 % | −25,08 % |
| 95 corps #1 | 1,347 | +5,29 % | **+5,86 %** |
| 27 lowe-k | 1,411 | −78,02 % | −78,02 % (no se mueve) |
| 60 lowe-k | 1,021 | +53,29 % | +53,29 % (no se mueve) |

**El 95 es el único que empeora, y es el único con embalse**: tiene
`rapid_drawdown` activo contra el paramento. El 51 no puede llegar —su capa
4 no está publicada y gobierna media superficie—, y el 27 y el 60 arrastran
divergencias de otras causas y **no se mueven un dígito**, porque su agua no
toca ninguna cara vertical.

### La nota, comprobada donde no se la ajustó

Pasada por los nueve modelos del banco sin tocarla, dispara en **el 95 y el
96 y en ningún otro** — los dos únicos con embalse, y los dos únicos donde
totales empeora. El predicado no se calibró con ellos: se escribió desde la
identidad analítica y coincide.

## Un control mío que estaba mal montado, y se dice

La primera comprobación de «los cinco métodos que no leen el ajuste no
pueden moverse» comparó los `resultados.json` nuevos contra los guardados, y
marcó **dos filas movidas**: Janbu simplificado −12,83 % en el 59 y +2,31 %
en el 60. Eso es la condición de parada del encargo, así que se paró y se
midió.

**El control era inválido, no el cambio.** Los `resultados.json` del banco
se escribieron con versiones que van de 0.1.100 a 0.1.138, así que esa
comparación mezcla este cambio con D39/D42/D44 (0.1.137) y D48r (0.1.143).
El control honesto es el A/B **en la misma versión**, y ahí Janbu da
`0,55587` con efectivas y `0,55587` con totales en el 59, y `1,541394`
contra `1,541394` en el 60. Ni un dígito. Lo mismo Bishop y Spencer en los
dos.

## Cambios

- `ogr_core/project/settings.py` — `interslice_forces` pasa a `"total"`,
  con la decisión, su evidencia y su precio escritos donde vive el campo.
- `ogr_slip2d/methods/modified_swedish.py` — el predeterminado de la
  clase pasa a `TOTAL_INTERSLICE`, **el mismo**: dos predeterminados que
  discrepan son el fallo de v0.1.78 y de D33 otra vez. Y
  `_thrust_reversal`, el diagnóstico nuevo, publicado en
  `details["thrust_reversal"]`; cuesta una marcha por superficie sobre las
  dieciséis o más que ya gasta el buscador de raíces.
- `ogr_slip2d/analysis_runner.py` — `_interslice_convention_notes`,
  enganchada en `settings_warnings`: dispara con agua **encima** del
  terreno y calla con agua dentro; y el respaldo del `getattr` alineado
  con el predeterminado nuevo, que era una tercera opinión sobre el mismo
  valor.
- `ogr_gui/dialogs/project_settings_dialog.py` — el tooltip dice ahora
  **cuál elegir y cuándo**, no sólo qué son; con su entrada en español.
- `tests/test_interslice_guard_v1144.py` — nuevo: la nota con su control
  que **no** debe dispararse, el diagnóstico sobre los círculos
  publicados, y el test de que nada veta con él.
- `tests/test_interslice_split_v1117.py` — la decisión, y el test de que
  el predeterminado llega al solver (regla 7 en su forma estricta: no que
  el campo valga algo, sino que su valor llegue a quien lo usa).
- `tests/test_drawdown_methods_v1108.py` — el Apéndice G declara
  `effective` en el modelo, con la medición de las dos columnas escrita al
  lado; y el método deja de instanciarse a pelo desde el registro.
- `tests/test_ponded_water_v161.py` — la identidad boyante de Duncan y
  Wright pide `effective` explícitamente: es un enunciado en efectivas.
- `tests/test_slide_validation_ej2_piezo_v194.py` — la divergencia de
  lowe-karafiath, **−10,9 % desde v0.1.94, pasa a +0,09 %** y se muda a
  `CLOSED`. Es la tercera de las tres que abrió ese archivo.

---

## Verificación

- Suite entera, sin filtro: **3066 tests, 3066 pasan**.
- Banco: los nueve modelos re-guardados y recorridos con 0.1.144;
  `COMPARATIVA_Slide2_vs_OGR.md` regenerada (97/111 analizados, 19
  anomalías). El 55 y el 56 pasan de REVISAR a **OK**.
- Lo que NO se pudo verificar y se dice: el diagnóstico
  `thrust_reversal` no llega a los modelos con desembalse (el envoltorio
  no arrastra los `details`), así que en el 95 y el 96 no se ha medido.
