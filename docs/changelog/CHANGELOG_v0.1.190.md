# OGR Slip2D v0.1.190

**Tres fichas de la cadena P3 en una tanda — D110, D114 y D61 —, y de las
tres hubo que corregir primero la premisa con la que estaban escritas.**

Cero dígitos movidos en cualquier cálculo, y esta vez el cero está medido
y no afirmado: el mismo medidor corrido contra el árbol de 0.1.189 y
contra el de 0.1.190 devuelve dos resúmenes que difieren en **una sola
clave, `version`**.

---

## 0. Lo que estaba mal en los tres encargos

### El criterio de cierre de D61 ya pasaba en 0.1.189, sin tocar nada

Pedía `grep` de «78.46» y de «Ching» sobre `ogr_slip2d/checks.py`. Los dos
estaban ahí desde v0.1.158: «Ching & Fredlund (1983)» en la línea 40 y
«78.463» en las líneas 48 y 337. **Un criterio que su propio estado
anterior satisface no es un criterio**, y es literalmente el defecto que
v0.1.189 documentó en `d111()` con el grep de «−112». `d61()` se endurece
por tres vías que 0.1.189 no puede pasar, y lo dice en mayúsculas dentro
de su propio docstring.

El de D110 sí discriminaba —ni «78.5» ni «acos» estaban en
`analysis_runner.py`— pero **un comentario lo habría satisfecho**. Se
endurece igual: `d110()` **ejecuta** la nota sobre cuatro modelos.

### Los números de reproducción de P-D61 son de un modelo que ya no existe

El prompt exige Bishop **1,611895** y Spencer **1,823021** con 3160 y 2631
válidas, y manda «medir antes de seguir» si no salen. No salen:

| método | prompt | archivo (0.1.185) | válidas | inadmisibles |
|---|---|---|---|---|
| bishop_simplified | 1,611895 | **1,412451** | 4036 | **0** |
| spencer | 1,823021 | **1,571399** | 3586 | **0** |
| gle_morgenstern_price | — | **1,600922** | 3449 | **0** |

La causa es **D108**, que el 2026-09-12 movió la polilínea de bloque del
contacto y = 7 al llano publicado y = 0,52; y `block_num_groups: 3` es
inerte con objeto dibujado (D109/D34), así que la tabla «2 grupos / 4
grupos» de la ficha D61 describe una **región implícita que este modelo ya
no usa**. Todo lo que esta versión escribe sobre el 75 sale del archivo
re-corrido, nunca del prompt.

### Y el testigo doméstico de D61 tampoco se reproduce

**`inadmisibles = 0` en los tres métodos.** El 75 de hoy no exhibe ni el
rechazo del 82,6 % de la peor banda ni la ganadora admitida por once
milésimas. Eso **refuerza** la rama (a) en vez de debilitarla —si el caso
que motivó la ficha ya no la ilustra, menos aún hay con qué calibrar un
límite— y va escrito con su margen, porque un cero sin margen es el cero
falso de D101, D103, D118, D127 y D129.

### El punto (b) de P-D114 no puede ser un A/B

Pedía sustituir la dovela empinada por dos más tendidas «de igual peso».
Con los extremos fijos, cualquier sustitución cambia el área encerrada y
por tanto el peso; y moviendo los extremos se mueven además **el eje de
momentos, los brazos y el afloramiento a la vez**. Se calcula igualmente y
se publica rotulado `NO_ES_UN_AB` con sus tres confusores nombrados, pero
**el cierre no se apoya en él**: se apoya en (b′), aritmética sobre la
MISMA geometría.

---

## 1. D110 — los dos techos, con nombre

Bajo φ = 0, `m_alpha ≡ cos α` exacto, así que `M_ALPHA_LIMIT = 0.2` es un
techo desnudo de **78,463°** sobre toda superficie de los cinco métodos
que `M_ALPHA_SCREENED` cubre. `max_base_angle_deg` tiene rótulo, spinbox,
ayuda y un valor de serie de 80°, y sólo alcanza a las `WeakLayerSurface`.
**El que tiene nombre es el que llega a menos**, y nada lo decía: quien
teclea 45° sigue teniendo 78,5° sobre todo lo demás.

### La nota es una función NUEVA, no un ensanche

`_base_angle_scope_notes(project, method_ids=())`, junto a
`_base_angle_ceiling_notes` y enganchada inmediatamente después de ella.
Cuatro razones, y la cuarta decide: los predicados de alcance son
distintos; los asuntos son distintos; el archivo tiene un asunto por
función; y **el docstring de D106 es un argumento cerrado para D106**, así
que ensancharlo obligaría a reescribir ese argumento para cubrir un caso
que no razona.

Dos cosas no se teclean, y las dos son la diferencia entre una frase sobre
el código y una frase al lado del código: **el techo se calcula** de
`M_ALPHA_LIMIT` —`d110()` lo comprueba moviendo el límite a 0,5 y
exigiendo que la nota diga 60,0°— y **el valor de serie se lee del
`dataclass field`**, de modo que moverlo mueve el silencio por sí solo.

La cláusula de m-alfa es exacta sobre el interruptor **y** sobre qué
métodos criba, que es lo que los prompts —escritos antes de v0.1.189— no
podían contemplar: con `check_m_alpha` apagado la nota **no afirma 78,5**,
y con un solo método no cribado dice que el cribado no alcanza a nada en
esa corrida.

### Interfaz: seis cadenas, y una rama que no existía

Rótulo (*Maximum base angle on weak-layer clips*), las dos ayudas y la
etiqueta viva, que pasa de dos ramas a **tres**: entre 78,463° y 90° el
techo tecleado es **más flojo** que el que ya está en vigor, así que no
llega a actuar — y eso era inexpresable con dos ramas. El umbral se
calcula, no se teclea. Las entradas castellanas viejas se **sustituyen** y
no se duplican: una clave huérfana en el diccionario es un sitio donde una
afirmación retirada sobrevive, que es D107.

El nombre del campo en el `.ogr` **no cambia** (compatibilidad), y el
spinbox sigue llegando a 90,0 por la razón que v0.1.158 dejó escrita.

### `_base_angle_ok` NO se ensancha

Ni una línea ejecutable de `search.py`. Sólo una remisión en su docstring,
para que quien lea el alcance restringido encuentre el otro techo sin
salir del archivo. `d110()` comprueba por AST que la guarda de
`WeakLayerSurface` sigue ahí, porque el prompt lo prohíbe expresamente y
un ensanche silencioso movería los casos validados.

### El único cambio a un test existente, y por qué

`test_base_angle_ceiling_v1158.py`, **una línea**: su helper `_notes`
seleccionaba `"base angle" in n.lower()` y ahora nombra la oración propia
de D106. Ni un assert, ni un número, ni un invariante se mueven.

**El filtro era ambiguo por accidente y no por diseño.** Cuando se
escribió, `_base_angle_ceiling_notes` era la **única** nota de
`settings_warnings` que decía «base angle», así que «las notas sobre el
ángulo de base» y «la nota de D106» eran el mismo conjunto: el filtro no
tuvo que elegir, luego no eligió, y nadie tuvo que escribir cuál de los
dos significaba. Que funcionara era una propiedad **del resto del
archivo**, no del helper. Medido antes de tocarlo: con la nota nueva
puesta, el filtro viejo devuelve 2 notas donde el test exige 1, y cuatro
casos caen en un archivo cuyo objeto no ha cambiado. El alambre que
sostiene esto —que exactamente una nota lleve la frase de D106— lo pone
`TestTheTwoNotesStayTellingApart`, y `d110()` lo repite.

---

## 2. D114 — la medida, y lo que enseñó de más

D61 afirma que bajo φ = 0 el chequeo «deja de ser una afirmación sobre el
método». **La mitad exacta**: con `tanφ = 0` y `u = 0`,
`q = c·b/cos α = c·ℓ` **exactamente**, así que en la rama circular filtra
por una cantidad que se cancela. **La mitad falsa**: en
`_general_moment_fos` la normal conserva el `1/cos α` que `q` sí pierde, y
`normals` entra en `moment_terms` **del lado del denominador**
(`driving = weight + normal + external`, `F = −shear/driving`; el reparto
es Fredlund y Krahn, 1977).

### Qué sale

| medida | valor |
|---|---|
| James Bay **publicada**, base cohesiva 43,7°: aportación de esa dovela | **3,66 %** del momento motor |
| la misma, quitando sólo esa aportación | el factor mueve **−3,53 %** |
| barrido sintético φ = 0 de 40° a 76°: `terms.normal / driving` | de **+18,0 %** a **−131,6 %**, monótono |
| círculo con el eje en el centro, normales **arbitrarias** | **2,9e−16** relativo, sobre dos radios y dos recuentos |

El cero circular es **exacto por geometría y no pequeño por suerte**:
`base_frame` toma el punto medio de la cuerda y su perpendicular, que es
la mediatriz de la cuerda y pasa por el centro. Por eso se comprueba con
normales aleatorias — si dependiera de las que el solver produce sería una
coincidencia, y es un teorema.

**El caso publicado es el extremo modesto, y eso es la mitad honesta de la
medida**: su base cohesiva más inclinada está a 43,7° y no llega al techo.
Una medición que sólo enseñara el extremo dramático sería un argumento.

### La monotonía que se afirmó antes de medirla era FALSA

El plan decía que la fracción de la dovela empinada crece con β. Medido:
**no**. A 45° da 2,80 %, a 60° baja a 1,93 % y a 65° salta a 30,7 % entre
vecinas de 2 y 6 %, porque **cuál acaba siendo la dovela más empinada tras
rebanar, y su brazo, se mueven**. Lo que sí es monótono es la fracción del
**término normal entero**, sobre once betas y sin excepción. Se afirma lo
que se mide, no lo que quedaría mejor.

### Dónde se escribe

En `m_alpha_check.__doc__`, **no** en `base_m_alphas.__doc__`: ese otro
tiene siete literales obligatorios desde v0.1.189, su asunto es *qué forma
se mide y qué cuesta*, y el de D114 es *qué significa el cribado*, que es
el asunto de la **puerta**. `d114()` re-exige los siete, porque este
cierre no se puede comprar moviendo texto de una función a otra.

### Y el endurecimiento que hace que el literal valga algo

`d114()` **compara la cifra del docstring con `F1_SHARE_PCT` del JSON
archivado**. Un literal solo es discriminación débil; un literal que tiene
que concordar con una medida, no. Además exige `CIRCULAR_RESIDUO_REL` con
su margen, `RESIDUO_RECOMPUTO` dentro de la tolerancia y, por AST, que
`MomentTerms.driving` siga sumando lo que se midió.

---

## 3. D61 — la decisión, rama (a)

**`M_ALPHA_LIMIT` se queda en 0,2**, y eso se escribe como decisión
cerrada en el docstring de módulo de `checks.py`, borrando la frase que
decía que el defecto estaba abierto.

Lleva dentro, con sus números: la **búsqueda negativa** de v0.1.158 con
sus cuatro fuentes (el banco, con el 47 a 44,17° y el 29 a 43,4°; James
Bay a 43,7°; la G-9 de la EM 1110-2-1902 con sus 61° pero sin publicar la
superficie como no circular; y Ching y Fredlund, **no leída**, con la
advertencia intacta); la **doctrina marcada como doctrina** (Duncan,
Wright y Brandon §14.4, «45 degrees or less», Jumikis 1962), citada y no
aplicada porque movería los casos validados; y la medida de D114 como
justificación y no como disparador.

### Lo que despejar 0,2 NO compra, y va escrito para que no se lea al revés

Sobre superficies que **todas** pasan el chequeo, las nueve familias
discrepan por un factor de **6,8 a 70°** (min m_alpha 0,342), **34,9 a
75°** (0,259) y **1501 a 78°** (0,208, o sea admitida por ocho
milésimas). La ficha original ponía esa separación en un 44 %. **El límite
criba aritmética que se ha vuelto poco de fiar; no certifica lo que
sobrevive.**

---

## 4. Lo que se reporta y NO se corrige (regla 6)

Último defecto del banco: **D167** (v0.1.189). Estos van del D168.

- **D168 — pasado el techo, la rama no circular converge a un punto fijo
  donde la normal domina el denominador y el factor colapsa.** Sobre la
  poligonal φ = 0 a 78°, con min m_alpha **0,2079** —o sea **admisible por
  ocho milésimas**— Bishop general publica **0,0023**, y con la tolerancia
  apretada a 1e−8 el punto fijo verdadero es **2,6e−8**, estable con 30,
  60 y 120 dovelas. Spencer, GLE y el Ordinario no devuelven factor sobre
  esa misma superficie. No se corrige porque elegir el remedio sin fuente
  sería inventar un criterio, y el remedio obvio —apretar el techo— es
  justo lo que D61 acaba de decidir no hacer por falta de caso publicado.
  Ninguna fila del banco lo ejerce: el testigo es construido.
- **D169 — el criterio de parada es un paso ABSOLUTO.**
  `abs(new_fos - fos) < self.tolerance` con `tolerance = 1e-3`, así que
  sobre un factor de 3,7e−3 admite un paso del **27 %** y publica
  `converged = True`. La misma superficie da 0,002303 con 1e−3 y 2,66e−08
  con 1e−8: **cinco órdenes de magnitud entre dos resultados igualmente
  convergidos**. Es el linaje de v0.1.100 por el otro extremo — aquel
  arreglo (`it > 1`) sigue siendo correcto y no tocó la escala. No se
  corrige porque un criterio relativo mueve el punto de parada de las
  nueve familias sobre las 559 filas y pide su propia versión. **El efecto
  sobre el banco NO está medido, y se dice en vez de escribirlo como
  cero.**

Y una observación del repositorio, no del banco:
`tests/test_i18n_coverage_v141.py:233` deja el idioma activo en español y
su `teardown_method` (línea 306) es **decorativo, porque el runner del
proyecto no ejecuta teardowns**. Se descubrió porque hizo fallar tres
casos del fichero nuevo con las ayudas traducidas — la regla 5 exactamente
como AGENTS.md la cuenta. El fichero nuevo se blinda con try/finally y
deja la medida escrita; el ajeno no se toca en esta tanda.

---

## 5. Los tests

Ninguno de los 48 casos nuevos fija un factor de seguridad contra una
instantánea. Los anclajes son identidades algebraicas (`q ≡ c·ℓ` y
`m_alpha ≡ cos α` bajo φ = 0), una identidad **geométrica** (el momento de
la normal se anula sobre un círculo para normales arbitrarias), una
descomposición exacta, **orden** en vez de valor, y las formas cerradas de
los dos techos.

**El reparto contra 0.1.189 está MEDIDO**, copiando cada fichero a un
`git worktree` en ese commit y corriéndolo allí — no predicho:

| fichero | casos | fallan en 0.1.189 |
|---|---|---|
| `tests/test_two_ceilings_named_v1190.py` | 18 | **10**, todos por comportamiento o por una cadena que el usuario lee |
| `tests/test_phi_zero_general_branch_v1190.py` | 17 | **1**, y es por la ausencia de un símbolo: discriminación DÉBIL, etiquetada |
| `tests/test_phi_zero_ceiling_decision_v1190.py` | 13 | **5**, y el más fuerte es una AUSENCIA, que ningún grep ve |

El de D114 declara en su cabecera que **fija una medida y no un cambio**,
en vez de dejar que parezca lo segundo; por eso el peso del cierre recae
en `d114()`, que exige la concordancia con el JSON.

---

## 6. Errores propios detectados antes de publicar

Nueve, y tres estuvieron a punto de publicar una afirmación falsa.

1. **La monotonía de la dovela suelta, afirmada en el plan antes de
   medirla, era falsa** (§2). Se cambió el invariante a lo que se mide.
2. `COS_ALPHA_IDENTIDAD` se medía sobre **todas** las dovelas y daba 0,43
   en James Bay — que tiene una friccional. La identidad sólo vale donde
   `tanφ = 0`, y romperla ahí habría sido un fallo del medidor leído como
   uno del motor.
3. La «dovela gobernante» era la más empinada **a secas**, que en James
   Bay es la de 57,2°, la única con rozamiento. El sujeto de D114 es
   φ = 0, así que la medida contestaba otra pregunta.
4. `RESIDUO_RECOMPUTO` se comparaba contra cero. El factor publicado es el
   `new_fos` de la última pasada calculado con el iterado anterior, así
   que rehacer la pasada **no** devuelve el mismo número: devuelve uno
   dentro de la tolerancia. Ahora se publica la tolerancia al lado — y el
   residuo **relativo**, que es lo que destapó D168.
5. El criterio «dovela cohesiva» era `q == c·ℓ` a 1e−9, y en James Bay
   llamó friccionales a seis cohesivas: la columna `ℓ` publicada es la
   longitud medida y concuerda con `b/cos α` al 1 %, no a precisión de
   máquina. Ahora se **interroga a la envolvente**.
6. Tres fixtures prestados mal: `_project` de `test_weak_layer_v1121` no
   lleva capa débil por defecto, y `_STEEP` gira a 74,5°, que está **por
   debajo** del techo a propósito — es el fixture de «aceptada y
   dividiendo por un cuarto», no sirve para enseñar los dos alcances
   discrepando.
7. **La trampa del salto de línea, por cuarta vez en el proyecto**: la
   subcadena «zero by construction» cruzaba un `\n` en el docstring. Se
   arregla NORMALIZANDO EL ESPACIO, no eligiendo subcadenas con cuidado,
   que es lo que deja de funcionar en cuanto alguien reflue el texto.
8. Dos frases de la nota se encadenaban con minúscula tras punto.
9. Los recuentos de discriminación de dos cabeceras se escribieron antes
   de medirlos (17 por 18, y 12 por 17). Se midieron y se corrigieron.

---

## 7. Verificación

**Estructural, y es la primera barrera**: comparados por AST con los
docstrings quitados, `ogr_slip2d/checks.py` y `ogr_slip2d/search.py` son
**idénticos** a los de 0.1.189 — todo lo que cambia en esos dos archivos
es texto — y `ogr_slip2d/methods/` no se toca en absoluto. Lo único
ejecutable que entra al motor es `_base_angle_scope_notes` y su llamada.


- **Suite entera y sin argumentos: 4141/4141**, sin banner `FILTERED RUN`,
  sola en la máquina y con el changelog ya escrito. 0.1.189 traía 4093; los
  **+48** son exactamente los 18 + 17 + 13 de los tres ficheros nuevos.
- `censo_techos_d114_d61.py` corrido contra los dos árboles: los dos
  resúmenes difieren en **una sola clave, `version`**. Ésa es la prueba de
  que la tanda no mueve un dígito.
- **El 75 no circular re-corrido con 0.1.190** (535,3 s), y los tres
  factores salen **bit a bit idénticos** a los que archivó 0.1.185:
  1,412451 / 1,571399 / 1,600922, con las mismas 5000 generadas y las
  mismas 4036 / 3586 / 3449 válidas. Cinco versiones de motor sobre este
  problema y cero dígitos movidos.
- **Y el cero de `inadmisibles` llega con su margen**, porque un cero sin
  margen no dice nada: la crítica publicada de cada método tiene
  `min m_alpha` **0,750 / 0,835 / 0,857**, o sea entre +0,55 y +0,66 por
  encima del límite. No es que el cribado no actuara: es que estas
  críticas están a media unidad de él.
- `verificar_cierres.py D110 D114 D61`: **CUBIERTO POR TEST**,
  **CUBIERTO POR TEST** y **CIERRE DOCUMENTAL**.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257
  INFO, el mismo perfil que en 0.1.186, 0.1.187, 0.1.188 y 0.1.189). La
  corrida intermedia dio **2 ERROR** y se dice: eran las tres fichas
  cerradas conservando sección y prompt, que es justo lo que
  `retirar_cerrados.py` resuelve.
- Balance contra `Evaluaciones/0.1.189`: **559 → 559 filas, las 559
  IGUAL, 0 sin pareja**. Cero dígitos movidos sobre el banco entero.
- Instantánea `Evaluaciones/0.1.190` con **1686 archivos comprobados
  byte a byte**, de los que uno es de 0.1.190 — el 75, lo único que esta
  tanda re-corrió.
- `retirar_cerrados.py --escribir` retira las tres secciones y deja sus
  tres renglónes en el índice; **PAQUETES, la cadena tachada y la fila de
  índice abierto de D61 van a mano**, como siempre, y esta vez PAQUETES
  además adopta a D168 y D169.

**Una advertencia que va aquí porque es fácil de leer al revés**: que el
banco no se mueva no quiere decir que los dos techos den igual. Quiere
decir que el banco no contiene ningún modelo con capa débil **y** un
ajuste de ángulo de base cambiado del de serie, que es la única
combinación donde la nota nueva cambia lo que se imprime. Y que el 75 ya
no exhiba el defecto de D61 no quiere decir que el defecto no exista:
quiere decir que D108 le cambió la superficie debajo.
