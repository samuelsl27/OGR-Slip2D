# OGR Slip2D v0.1.191

**Dos fichas de la cadena P3 en una tanda — D165 y D167 —, las dos en
`ogr_slip2d/checks.py`, las dos del tipo «una promesa escrita que el código
no puede cumplir», y de las dos hubo que corregir primero la premisa.**

Atribución separada por construcción: D165 sólo cambia la tolerancia a
tracción de un material cuyo criterio la define, y D167 sólo cambia la carga
de la base cuando hay sismo vertical. El banco no contiene ninguna de las dos
cosas, y eso está medido por identidad y no supuesto: ningún material de roca
en los 194 `.ogr`, y kv = 0 en todos.

---

## 0. Lo que estaba mal en los dos encargos

### D165: la fórmula no es «sólo con a = 0,5»

P-D165 pedía «decidir qué se hace cuando a ≠ 0,5» porque `s·σci/mb` sería la
tracción del criterio generalizado **sólo con a = 0,5**. Es falso. Con
σ'1 = σ'3 = σt, el criterio σ'1 = σ'3 + σci·(mb·σ'3/σci + s)^a deja
(mb·σt/σci + s)^a = 0, cuya raíz **no depende de a**: σt = −s·σci/mb para
todo a > 0. Lo que sí depende de a es la tracción uniaxial (σ'1 = 0), y esa no
es `s·σci/mb` ni siquiera con a = 0,5. Medido con `brentq`: la uniaxial vale
0,99936 de la biaxial con los valores de serie del generalizado a a = 0,5,
0,98701 con los del clásico, y 0,87244 a a = 0,65.

Y la biaxial es la cantidad que corresponde a este chequeo, no la otra: la
envolvente de Mohr del criterio termina en (σt, 0), el círculo de diámetro
nulo en σ3 = σt, y el chequeo compara la tensión NORMAL de un plano.

### D165: una excepción no invalidaría la superficie, la admitiría

La ficha pedía un acceso a `params` «que no reviente, porque una excepción ahí
invalidaría la superficie por la razón equivocada». Al revés:
`BaseSearch._is_admissible` (`search.py:602-611`) se traga la excepción y
**admite** la superficie. La guarda sigue haciendo falta, por la razón
contraria, y así queda escrita.

### D165: el alcance es menor del que la ficha supone

`AdvancedSettings.from_dict` (`settings.py:1128-1129`) convierte todo
`check_tensile_stresses: True` guardado en `False`, sin mirar qué versión
escribió el archivo — y el `.ogr` no lo dice (`format_version: "0.1"`). La
tolerancia de roca que esta tanda concede sólo alcanza, pues, análisis en la
misma sesión, por API o por CLI: un proyecto reabierto vuelve con el chequeo
apagado. Reportado como D178.

### D165: la referencia no publica la regla

Dice que Hoek-Brown, Hoek-Brown generalizado y la función corte-normal
«pueden» tener tracción finita, y no dice cómo se calcula para ninguno.
`s·σci/mb` es una inferencia de este programa y va escrita como tal. La
referencia tiene además una resistencia a tracción opcional POR MATERIAL para
casi todos los modelos, que OGR no tiene (D180).

### D167: el banco no tiene el sismo apagado

La ficha y su prompt decían que los 194 `.ogr` llevan el sismo desactivado
(`enabled=False`, `kh=0`, `kv=0`). Falso: **8 lo tienen activo** (004, 051,
062 ×4, 104 ×2) y 7 con kh ≠ 0. El cero sobre el banco se sostiene, pero por
kv = 0 en los 194 y porque kh no entra en `w_total`: el matiz «kh NO
interviene» que la ficha añadía de pasada es lo que sostiene el cero en siete
modelos.

### D167: el censo que se ofrecía «tal cual» no lee el sismo

`_tools/censo_m_alpha_d111_d112.py` lee `p.settings.seismic`, que es
`SeismicAnalysisSettings` (Ky y Newmark) y no tiene `kh`, `kv` ni `enabled`:
sus columnas de sismo son cero por construcción. Y `A_con_kv_degenerado` mide
kv == 1, no kv ≠ 0. Reportado como D174.

### D167: no es «una línea»

Son los **diez** literales `support_failure_details(sup, {...})` de seis
archivos más el de `MultiStageDrawdownMethod`: el chequeo de tracción y la
medida de m-alpha corren para los nueve métodos, y `m_alpha_sign` sólo lo
publican cinco.

### D167: la tabla 2×2 es falsa para el chequeo de tracción

«Los otros tres brazos dan cero exacto, porque con la envolvente recta tan φ
es la misma a cualquier tensión.» Vale para `base_m_alphas`, e incluso ahí no
es «exacto» con Mohr-Coulomb: no tiene tangente analítica y su secante varía
~1e−12 con σ. Para `base_effective_stresses` es falso sin matices: la carga
entra directamente en la normal (N_viejo − N_nuevo = kv·W_suelo/m_α), así que
el σ' del chequeo de tracción se movía con **cualquier** envolvente. La ficha
infraestimaba su propio alcance. El control nulo sí es exacto:
`x * (1.0 - 0.0)` es `x` en IEEE-754.

---

## 1. D165 — la tracción se pregunta al modelo

- **`StrengthModel.tensile_strength()`** (`ogr_core/materials/strength_model.py`)
  devuelve 0.0 salvo que el modelo lo sobrecargue: un modelo que nazca
  después hereda la respuesta conservadora en vez de tener que acordarse de
  apuntarse a una lista, que es lo que se había quedado viejo.
- **Las dos sobrecargas de Hoek-Brown** (`builtin_models.py`) leen
  `self.params["sigci" | "mb" | "s"]` y `"sigci" | "m" | "s"` — los mismos
  nombres que su `shear_strength` —, devuelven la magnitud positiva y 0.0 con
  constantes no positivas o no finitas. El docstring deriva la raíz, dice por
  qué es la cantidad de un chequeo sobre σ'n, publica el hueco medido con la
  uniaxial, cita Hoek, Carranza-Torres y Corkum (2002) y Hoek (1983) **marcados
  como no leídos** (el convenio de `checks.py:40-44`) y advierte que la
  envolvente que evalúa `shear_strength` todavía no es la de este criterio
  (D171).
- **`checks._material_tensile_strength`** es ahora una llamada guardada a ese
  método. **`_TENSILE_CAPABLE` desaparece sin sustituto**: la lista de
  capaces es la que el test y `d165()` derivan barriendo `REGISTRY`, y una
  función que la calculara sin llamador en producción sería código muerto.
- **La función corte-normal se queda en cero, y es una decisión**: ninguna
  fuente da la regla. No porque su tabla no pueda llegar a τ = 0 en tracción
  —una que empiece en (−50, 0) llega—, que fue la razón que el plan escribió
  primero y la revisión cazó.

## 2. D167 — el kv viaja con el resultado

- **`details["kv"]`**, escrito en las diez salidas desde el MISMO local que
  cada método pasa a `slice_forces` (verificado sin sombreado), y en
  `MultiStageDrawdownMethod` desde la pasada que dio la respuesta o, si no la
  hubo, desde el proyecto que todas las etapas compartieron. En `ordinary.py`
  sin la palabra que su guarda prohíbe.
- **`checks._applied_kv`** lo lee (ausente o no finito → 0.0, lo de antes), y
  **`_base_load_and_sigma(s, *, kv)`** lo exige por nombre y SIN valor por
  defecto: un cero por defecto es exactamente como esta función llegó a
  perderlo, y se lo haría perder al siguiente llamador. Llama a
  `slice_forces` y no copia `(1 − kv)`, así que el signo es de `slice_forces`
  (D170) y el chequeo lo seguirá.
- **kh no se lleva**: `w_total` no depende de él, y una clave que nadie lee
  sería la regla 7 en pequeño.
- **Lo que ni el kv correcto iguala**, escrito en el docstring y reportado
  como D172: con soporte, Bishop y Janbu suman `support_vertical_load` y
  Spencer, GLE y la familia prescrita restan `nf_v`; Fellenius tiene su propia
  forma; y el suelo de ℓ es 1e−12 frente a 1e−9.
- Textos viejos corregidos: la lista de claves de `LEMResult.details`, que no
  mencionaba ninguna de las dos que los chequeos leen; `docs/plugins.md` §1 y
  §2, con los dos contratos para quien escriba un modelo o un método; y el
  párrafo de `_denominator_sign` que nombraba dos tests como constructores de
  `LEMResult` a mano — construyen `Slice` y nunca llegan a los chequeos.

## 3. El censo de la regla 6

`_tools/censo_traccion_kv_d165_d167.py` (banco, SOLO MIDE, con `OGR_REPO`),
corrido contra un `git worktree` prístino de 0.1.190 **antes** de tocar el
motor y contra el árbol de 0.1.191 después. Comprueba qué `ogr_slip2d`
importó y se niega a correr si no es el del árbol que dice medir. Cada cero
lleva un control que demuestra que el medidor ve el caso:

- **A (D165)**: 194 `.ogr`, 400 materiales (mohr_coulomb 362, undrained 19,
  undrained_depth_datum 13, power_curve 5, infinite_strength 1), **0 con
  tolerancia no nula** en los dos árboles, y 0 con el chequeo encendido leído
  del JSON CRUDO (por `Project.load` sería cero por construcción, D178).
  Control: un Hoek-Brown sintético con parámetros NO de serie da 0,0 en
  0.1.190 y 68,8235 / 80,0 kPa —su forma cerrada— en 0.1.191.
- **B (D167)**: 8 con sismo activo, 7 con kh aplicado, **0 con kv aplicado**.
  Control: el 004 lee kh = 0,15, el caso que el censo de D111/D112 no podía
  ver.
- **C (D167, sintético)**: un resultado convergido por envolvente, variando
  sólo `details["kv"]`. Con kv = 0 la identidad con la fuerza normal del
  propio solver es **0,0 exacto en los dos árboles**; con kv ≠ 0 el residuo
  pasa de **0,66** en 0.1.190 a **0,0** en 0.1.191. Lo que mueve kv = ±0,2:
  m_α un 0,0347 con curva de potencia, 3,0e−13 con Mohr-Coulomb y 0 exacto sin
  drenaje; σ' un 25,7 %, 24,2 % y 79,5 %. Ninguna dovela cruza 0,2, con el
  m_α mínimo en 0,506, a 0,31 del límite.

Entre los dos censos difieren **ocho claves, todas declaradas** en
`CLAVES_QUE_PUEDEN_DIFERIR`, y las filas por modelo de A y B son idénticas.
`auditoria_traccion.py`, que no lee la tolerancia y por eso no discrimina
D165, da el mismo informe en 0.1.190 y 0.1.191 salvo el título: el σ' de los
círculos publicados del banco no se mueve.

## 4. Lo que se reporta y NO se corrige (regla 6)

Doce fichas nuevas, cada una con su prompt largo y su paquete. Todas medidas;
ninguna mueve hoy un número del banco.

- **D170** (P4) — `slice_forces` aplica un kv positivo HACIA ARRIBA
  (`W(1 − kv)`), contra la referencia («A POSITIVE vertical seismic
  coefficient represents a vertical seismic force directed DOWNWARDS»), contra
  cuatro textos de OGR que dicen lo mismo y contra `seismic_delta_sigma_v`,
  que suma `kv·σv`. En un talud sin drenaje, el kv = −0,2 de OGR da 0,5724,
  exactamente lo que el convenio de la referencia predice para kv = +0,2
  (0,6869/1,2).
- **D171** (P7) — la `shear_strength` de Hoek-Brown no es la envolvente de
  Mohr de su criterio: τ(0) = 0 donde el criterio da 307,5 kPa, y a
  σn = 145 kPa el valor de OGR (443) cae DENTRO del círculo de compresión
  simple del propio macizo (661).
- **D172** (P3) — la σ de los chequeos no ve el refuerzo ni la forma de
  Fellenius. Intersección soporte × envolvente dependiente de σ en el banco:
  vacía.
- **D173** (P4) — el posprocesador de fuerzas entre dovelas rehace
  `W(1 − kv)` a mano sin el agua embalsada: con 20 050 kN/m de agua sobre la
  superficie devuelve EXACTAMENTE los mismos N y E que sin ella; y una de sus
  dos llamadas en la ventana no pasa kv.
- **D174** (P0) — el censo de D111/D112 lee `p.settings.seismic`.
- **D175** (P0) — **doce** comprobaciones de cierre exigen artefactos con el
  nombre de la versión instalada y dejan de cerrar al subir la versión:
  corridas en seco con 0.1.191, D54, D125, D156, D157, D160, D162, D163, D113,
  D111, D112, D114 y D61 caen de su veredicto de cierre. El JSON archivado las
  conserva sólo porque acumula. `d165()` y `d167()` no repiten el error.
- **D176** (P1) — el botón de la calculadora GSI no escribe nada: busca
  `panel._widgets` y el panel guarda sus editores en `_editors`. Reproducido
  con el diálogo real, sin abrirlo.
- **D177** (P1) — un rechazo por tracción se exporta como −101 aunque el
  motor diga −120.
- **D178** (P1) — `check_tensile_stresses` vuelve a False al reabrir
  cualquier proyecto.
- **D179** (P1) — `tensile_tolerance` se acepta en las búsquedas y nadie lo
  lee.
- **D180** (P3) — falta la resistencia a tracción opcional por material que
  la referencia define.
- **D112b** (P3) — `MultiStageDrawdownMethod` no propaga `m_alpha_sign`, así
  que con Janbu dentro el chequeo vuelve a adivinar el signo con la suma de
  Bishop: el caso de D112 entrando por el envoltorio. **Alcanzable en el
  banco**: de cuatro desembalses multietapa, el 096 corre Janbu dentro. Si
  mueve algún veredicto no está medido.

Y de higiene, sin número: la línea corrupta del bloque de verificación de
P-D167 (un `\02` leído como escape) se quita, y P-D165 lleva una nota de que
su reproducción importa un símbolo que el arreglo retiró. El verificador de
citas de los prompts sigue marcando una cita de D135.md, anterior y ajena a
esta tanda.

## 5. Los tests

Ninguno de los 34 casos nuevos fija un factor de seguridad contra una
instantánea.

- **`tests/test_tensile_strength_rock_v1191.py`** (18): la forma cerrada con
  instancias de parámetros NO de serie, escritos en el test — leer
  `PARAMETERS` en vez de `params`, que es la forma exacta de D165, no pasaría
  —; la identidad del corchete; la independencia de a con guarda > 0; clásico
  = generalizado con a = 0,5; el barrido de los 21 modelos del registro, que
  tiene que dar EXACTAMENTE los dos Hoek-Brown; la ausencia de cualquier
  literal de conjunto con ids del registro en `checks.py`; la robustez; y el
  veredicto que se mueve, sobre un `LEMResult` hecho a mano con bases planas
  donde σ' = W/ℓ − u al último bit, con dos controles (más allá de −σt sigue
  rechazada; el mismo σ' con Mohr-Coulomb también).
- **`tests/test_sigma_seismic_v1191.py`** (16): la identidad con la fuerza
  normal del PROPIO solver para Bishop y los dos Janbu —medida antes del
  arreglo: 0,0 exacto a kv = 0 y ~0,32 a kv = 0,2—; el 2×2 sobre UN resultado
  cambiando sólo `details["kv"]`; los controles nulos bit a bit; el portador
  en los nueve métodos y en el envoltorio de desembalse, también en su rama
  sin pasada final (con el parche restaurado en `finally`); y dos guardas del
  modelo — la primera, que el sismo llega al solver, porque el helper de
  `test_slide_sign_by_method_v1189.py` escribe en un objeto que nadie lee.

**Reparto contra 0.1.190, MEDIDO** copiando cada fichero a un `git worktree`
en ese commit y corriéndolo allí:

| fichero | casos | fallan en 0.1.190 |
|---|---|---|
| `tests/test_tensile_strength_rock_v1191.py` | 18 | **11**: 9 por comportamiento, 1 estructural (la lista vieja está), 1 DÉBIL (falta el método) |
| `tests/test_sigma_seismic_v1191.py` | 16 | **8**: 3 por comportamiento y 5 DÉBILES (una clave o un parámetro que falta) |

Los que pasan en los dos árboles lo hacen por diseño —guardas, controles
nulos, guardas de la fixture— y cada cabecera los nombra. El único cambio a un
test existente es la prosa de `tests/test_checks_v132.py`, que prometía
tracción a la función corte-normal.

## 6. Errores propios detectados antes de publicar

Doce, y cinco estuvieron a punto de publicar una afirmación falsa.

1. **Mi primera medida del alcance de D112b daba cero, y era ceguera del
   medidor**: comparaba `advanced_option` —que es un MÉTODO— con una cadena.
   Con el booleano y Pilarcitos como control positivo, aparecen cuatro
   desembalses multietapa y el 096 con Janbu dentro. Es la trampa de D174,
   cometida por mí la misma tarde.
2. Mi recuento rápido del banco dio 204 `.ogr` y 428 materiales, y lo anoté
   como error de la ficha; incluía diez copias de `_auditoria/`. La población
   es 194 y 400, como la ficha decía.
3. **El plan hacía que los brazos «que se mueven» del 2×2 se resolvieran por
   separado**, así que el factor cambiaba con kv y el árbol viejo también «se
   movía»: las pruebas habrían pasado en vacío. Lo cazó la revisión del plan;
   ahora varía sólo `details["kv"]` sobre un mismo resultado.
4. El plan escribía «cero exacto» para Mohr-Coulomb en m-alpha; es ~1e−12, y
   el test lleva la tolerancia con su razón.
5. El plan pedía en `d165()` la ausencia de «todo literal de conjunto» en
   `checks.py`, que el árbol arreglado tampoco habría pasado
   (`M_ALPHA_SCREENED`); ahora es la ausencia de ids del registro.
6. La razón escrita en el plan para dejar la corte-normal en cero era falsa
   (§1).
7. Una frase de la cabecera de `test_sigma_seismic_v1191.py` decía que los
   casos débiles pasarían con un coeficiente EQUIVOCADO; pasarían con la
   clave publicada y el chequeo ignorándola, que es otra cosa.
8. La mitad C del censo salió primero sin control nulo, y su 66 % no era
   atribuible a kv hasta que kv = 0 dio 0,0 exacto.
9. Para D173 redacté que la N del posprocesador se separa un 93 % de la del
   solver; con Bishop esa diferencia es también de método (el posprocesador
   hace un equilibrio de fuerzas), así que no es atribuible al agua y se
   quitó. Lo que queda es exacto: con agua y sin agua, la misma N.
10. D175 empezó con cinco comprobaciones; medidas en seco son doce.
11. Los criterios de cierre del plan decían «cada id capaz existe en
    REGISTRY», una tautología en cuanto la lista sale del registro; se
    sustituyó por la igualdad del conjunto, medida.
12. **Llamé anomalía a los 26 minutos de la suite** porque AGENTS.md dice
    «entre 5 y 7½ minutos», y llegué a escribirlo en este changelog. El de
    v0.1.179 ya había medido 24 min 13 s y dejado dicho que esa horquilla
    está caducada. La cifra era normal; la referencia no. El propietario
    pidió actualizar la horquilla de AGENTS.md, y en esta misma versión dice
    «unos 25 minutos» con sus medidas.

## 7. Verificación

**Estructural**: el diff del motor es `checks.py`, los dos archivos de
`ogr_core/materials/`, los seis métodos (una clave en cada salida),
`rapid_drawdown.py`, un comentario de `methods/base.py` y los siete sitios
de versión. Ninguna línea ejecutable cambia fuera de `_material_tensile_strength`,
`_applied_kv`, `_base_load_and_sigma` y sus dos llamadoras, las dos
sobrecargas, el método base y la clave `kv`.

- **Suite entera, sin argumentos y con el changelog ya escrito: 4175/4175**,
  sin banner `FILTERED RUN`, **dos veces**: con el changelog a medias y otra
  sobre el estado definitivo, sin worktree. 0.1.190 traía 4141; los **+34**
  son exactamente los dos ficheros nuevos (18 + 16).
- Tardó 26 min 10 s y 25 min 29 s, en línea con los 24 min 13 s que
  v0.1.179 registró para 3863 casos. La horquilla de «5 a 7½ minutos» de
  AGENTS.md estaba caducada —v0.1.179 ya lo dejó escrito— y se corrige en
  esta versión a petición del propietario, con las cinco medidas que hay
  (error propio 12).
  Lo que sí se midió es el coste de lo añadido: los dos ficheros nuevos
  cuestan 0,4 s y 0,6 s solos, y la batería dirigida tardó 81 s con el
  arreglo puesto frente a 92 s en su primera corrida — ruido.
- Batería dirigida de 31 ficheros relacionados (chequeos, m-alpha,
  Hoek-Brown, desembalse, signo, base_normal, techos, ajustes, materiales,
  James Bay, licencias, λ, sismo y exceso de presión): **547/547**.
- `verificar_cierres.py D165 D167` → **CUBIERTO POR TEST** las dos; y contra
  el worktree de 0.1.190 las dos dan **NO SE SOSTIENE** (ocho fallos d165, más
  de ocho d167): los criterios no pasaban ya.
- Censos: los descritos en el §3.
- `generar_comparativa.py` + balance contra `Evaluaciones/0.1.190`:
  **559 → 559 filas, las 559 IGUAL, 0 sin pareja**.
- `retirar_cerrados.py --escribir D165 D167`: 2 secciones retiradas y 2
  renglones en el índice, citando `Evaluaciones/0.1.191` porque la instantánea
  se tomó ANTES. Restringido a las dos a propósito: sin ids también habría
  escrito los renglones de D141 y D38c, dos cierres viejos sin renglón que no
  son de esta tanda. A mano, lo de siempre: podar `PAQUETES`, tachar la
  cadena de P3 y regenerar `PROMPTS_RESOLUCION.md` (51 prompts, 42 largos;
  los 9 FALTA son anteriores). De paso se pusieron al día las filas P0 y P4
  de la tabla de paquetes, que arrastraban deriva previa (P0 seguía diciendo
  `D82 → D78 → D83`, las tres cerradas).
- `auditoria_invariantes.py` a **0 ERROR** en el 02 (748 hallazgos: 491
  AVISO, 257 INFO, el mismo perfil que en 0.1.186–0.1.190) y **0 ERROR** en la
  raíz (64 AVISO, ninguno de las fichas de esta tanda).
- Instantánea `Evaluaciones/0.1.191` con **1692 archivos comprobados byte a
  byte**, con el mismo reparto de versiones que la anterior: esta tanda no
  re-corrió nada.

Y una advertencia que va aquí porque es fácil de leer al revés: que el banco
no se mueva no quiere decir que los dos arreglos no hagan nada; quiere decir
que el banco no tiene ni roca de Hoek-Brown ni sismo vertical. Los dos
mueven lo que tienen que mover, y los tests lo demuestran sobre modelos
construidos para ello.
