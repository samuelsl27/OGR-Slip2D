# OGR Slip2D v0.1.212

**La etapa 1 del desembalse multietapa deja de fijar en silencio el estado de
consolidación (D202, paquete P3 del banco de verificación).** Decisión de la
propietaria (2026-09-27):

- una etapa 1 **no convergida** deja la superficie **inválida con la razón de
  su pasada**;
- una etapa 1 convergida pero **inadmisible para su propio método** deja la
  superficie **inadmisible con nota**, con el mismo factor.

Se midió antes de corregir, sobre un worktree de 0.1.211, y después sobre este
árbol, en las 16 búsquedas enteras del 095–098 (las 12 del censo P3 más las
cuatro del 095, que no corría) y sus 4 círculos publicados:

- **antes:** 1144 etapas 1 no convergidas con factor, **939 de ellas válidas**;
  1033 con F1 = 5,0, el techo del muestreo de la familia de inclinación
  prescrita;
- **después:** **0 válidas**, las 1144 con la razón de su etapa 1; **0 mínimos
  de búsqueda movidos y 0 filas publicadas movidas**, exactamente lo que
  predijo el censo de antes quitando esas superficies.

- **D202 cambia el motor.** `rapid_drawdown_fos` mira `r1.converged` antes de
  sus dos precondiciones y lanza `DrawdownStageUnconverged`; el resultado
  guarda la pasada de la etapa 1 (`stage1_result`) para que el envoltorio diga
  lo que su método dijo de ella.
- **Un test de D112b marcaba también la etapa 1** y se adapta, con su
  discriminación medida otra vez: los mismos 8 casos fallan en 0.1.209.
- **Del censo nace D203:** una etapa 2 no convergida cuando el casquete sí
  converge. En 0.1.212 son 528 superficies válidas, y de ellas dependen tres
  mínimos de búsqueda del 096. Reportada, no corregida.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git y se resume en la sección 5.

---

## 0. Lo que estaba mal en el encargo

### «Todas del 096» no era cierto: el censo no miraba el 095

El censo P3 (`_tools/censo_p3_desembalse.py`) solo corría el círculo publicado
del 095, no sus búsquedas. Pero la etapa 1 del 095 es la del 096: la misma
sección del Apéndice G, y la etapa 1 no depende del procedimiento (Corps en
dos etapas en el 095, Duncan-Wright-Wong en el 096). Con sus cuatro búsquedas:

| | etapa 1 no convergida con factor | de ellas válidas |
|---|---|---|
| 096 (lo que decía la ficha) | 796 | 643 |
| **095** | **348** (Corps 1 331, Spencer 17) | **296** (279 y 17) |
| total | **1144** | **939** |

### El caso tiene testigo dentro del repositorio

La ficha lo daba sobre el 096 del banco, que vive fuera de git. La sección es
la del Apéndice G de la EM 1110-2-1902 (Corps of Engineers 1970/2003), que la
suite ya tenía en `tests/test_drawdown_usace_v169.py`. En el mismo círculo,
(69; 110; 89,159), y sin salir del repositorio:

| método interior | F1 (etapa 1) | ¿convergida? | resultado del desembalse en 0.1.211 |
|---|---|---|---|
| Corps 1 | **5,0** (techo del muestreo) | no, `no_force_bracket` | **1,7093, válido** |
| Corps 2 | **5,0** | no, `no_force_bracket` | 1,7093, válido |
| Bishop | 1,852 | sí | 1,9467 |
| Spencer | 1,851–1,852 | sí | 1,9467–1,9468 |
| Lowe-Karafiath | 0,2137 | sí | «no aplica» (FS1 < 1) |

El 1,7093 queda un 12 % por debajo de lo que dan los métodos que sí resuelven
la etapa 1. Aquí cae del lado conservador, pero el sentido no está fijado:
τ_fc = s / FS1 es inversamente proporcional a F1, y un F de reserva por
DEBAJO del verdadero inflaría la resistencia no drenada.

### El testigo gastaba 18 pasadas sobre un estado que no era solución

En 0.1.211 el método interior se llamaba 18 veces en ese círculo: la etapa 1,
la etapa 2 (que tampoco encuentra horquilla: F2 = 5,0) y 16 pasadas del
casquete drenado, todas construidas sobre τ_fc = s / 5,0. Desde 0.1.212 se
llama una.

### La etapa 1 perdía también su admisibilidad

Desde D112b el envoltorio pasa el veredicto de la pasada que DIO el factor
(etapa 2 o 3). El de la etapa 1 se perdía entero: la convergencia, que es la
ficha, y también la admisibilidad que su propio método declara (Spencer y GLE
con el empuje entre dovelas relajado). La propietaria decidió meterlo en la
misma ficha. En el 095–098 no hay ninguna etapa 1 inadmisible natural, así que
ese caso lo ejerce el test.

---

## 1. D202 — la etapa 1 se juzga como las etapas 2 y 3 (motor)

### El defecto

`rapid_drawdown_fos` pedía a la etapa 1 tener factor y que fuera ≥ 1, nada
más. `_stage1_state` fijaba entonces σ'_fc y τ_fc = s / FS1 en cada dovela con
una pasada que no era solución, y la etapa 2 construía con ellas las
resistencias no drenadas. Las etapas 2 y 3 se resuelven, no se fijan, y desde
D112b la pasada que DA el factor lleva su propio `converged` a la superficie.
La etapa 1 fija estado y nunca da el factor, así que su veredicto se perdía
siempre. (Una etapa 2 que no da el factor también pierde el suyo: es D203.)

### La decisión (de la propietaria)

- **Etapa 1 no convergida → inválida con la razón de su pasada.** Es la regla
  que D112b ya aplica a las etapas 2 y 3 y la de D194 para una etapa sin
  factor. Se comprueba **antes** de «FS1 < 1 → no aplica»: un factor no
  convergido no dice nada del talud, así que un FS1 < 1 no convergido es un
  cálculo fallido y no un talud inestable antes del desembalse. Conservar la
  superficie con una nota se descartó: el factor que se conservaría sale de un
  estado que ninguna pasada resolvió.
- **Etapa 1 inadmisible para su método → inadmisible con nota, mismo
  factor.** Ahí el estado SÍ se resolvió, y el veredicto es de su método, como
  en un análisis ordinario.
- **La etapa 2 no convergida con el casquete convergido no se toca**: lo que
  hacen las etapas 2 y 3 es de D112b, D194 y D200, y la ficha lo prohíbe. Se
  mide (sección 3).

### El arreglo

- `DrawdownStageUnconverged(DrawdownStageFailed)`: lleva `stage` y la pasada.
  Su mensaje dice que esa pasada SÍ tenía número, y cuál: «Stage 1 returned an
  unconverged factor of safety (F = 5.000, not a solution): <mensaje de la
  pasada>». Es subclase, así que quien ya capturaba `DrawdownStageFailed` la
  sigue capturando.
- `rapid_drawdown_fos`: `if not r1.converged: raise DrawdownStageUnconverged(1,
  r1)`, justo después de `r1.fos is None` y antes de `> 0` y `< 1`. La decisión
  está escrita en su docstring.
- `DrawdownResult.stage1_result`: la pasada de la etapa 1.
- `MultiStageDrawdownMethod.compute_fos`:
  - con la subclase, la razón de reserva es `not_converged` (no
    `non_physical_fos`) y `details["drawdown_stage_fos"]` guarda el F que no
    era solución; el camino de D194 queda byte a byte igual;
  - con la etapa 1 inadmisible: `admissible=False` y la nota «Stage 1 (full
    reservoir): <nota interior>», delante de la que ya trajera el veredicto de
    D112b/D200; `admissibility_reason` no se toca (un veredicto del método no
    es un cribado, D177);
  - `details["stage1_admissible"]` siempre, la mitad legible por máquina.
- Con la etapa 1 convergida y admisible, las banderas son idénticas a las de
  0.1.211.

### Lo que mueve en el banco

Censo del 095–098 con las búsquedas del 095 (`--salida D202_etapa1
--con-095`), antes sobre un worktree de 0.1.211 y después sobre este árbol:

| | 0.1.211 | **0.1.212** |
|---|---|---|
| etapas 1 no convergidas con factor | 1144 | 1144 |
| de ellas, superficies válidas | 939 | **0** |
| de ellas, publicadas como «no aplica» | 75 | **0** |
| razón publicada | la de la etapa 2 o 3 | la de su etapa 1: `no_force_bracket` 1110, `no_lambda_bracket` 22, `lambda_not_closed` 12 |
| etapas 1 inadmisibles (naturales) | 0 | 0 |
| «no aplica» en todo el censo | 321 | **246** (las 75 de arriba) |
| mínimos de búsqueda movidos (16) | — | **0**, y 0 fuera de la predicción |
| círculos publicados movidos (4) | — | **0** |

- **Ningún mínimo dependía de ellas.** Los críticos de las búsquedas afectadas
  convergen en la etapa 1, y el censo de antes predijo cada mínimo quitando
  esas superficies: coincide en las 16.
- **Por búsqueda:** Corps 1 331 en el 095 y 331 en el 096, Corps 2 358,
  Lowe-Karafiath 90, y Spencer 17 en cada uno. Todas las de la familia son
  `no_force_bracket`, y 1033 tienen F1 = 5,0 exacto, el techo de su rejilla.
- **El censo de después tarda 2459 s**, frente a 5439 s el de antes. No es una
  medida de coste: el de antes compartía los núcleos con la suite y con la
  línea base de los cierres. Pero sí hay trabajo que ya no se hace: las
  superficies con la etapa 1 no convergida paran ahí, y el Corps 1 del 096
  pasa de 505 s a 222 s.
- **La rama del casquete que cicla pierde población:** en Corps 1 y Corps 2
  pasa a 0 superficies (antes 15/20 en el 096 y 23 en el 095). Todas las que
  ciclaban tenían la etapa 1 sin converger.

---

## 2. El test de D112b que marcaba también la etapa 1

`test_drawdown_passthrough_v1210.py` construye sus veredictos con `_marked`,
que marcaba **todas** las pasadas, la etapa 1 incluida. Con el arreglo, dos
casos cambiaron de sentido: `an_unconverged_pass_stays_unconverged` (la
superficie ya no llega a tener factor) y `an_inadmissible_pass_stays_inadmissible`
(la nota lleva delante la de la etapa 1). Lo que ese archivo prueba es el
veredicto de la pasada que DIO el factor, así que `_marked` deja ahora la
etapa 1 intacta; la regla de la etapa 1 la prueba el test nuevo.

El guarda de la rama que cicla (`no_per_slice_key_travels`) deja pasar la
clave nueva `stage1_admissible`: es del envoltorio y la escriben todas las
ramas, no una clave por dovela de ninguna pasada.

**Un camino equivocado, medido antes de descartarlo.** El primer intento metió
`stage1_admissible` en `_DRAWDOWN_KEYS`. Pero ese conjunto se usa también como
EXIGENCIA en el control `kv_is_still_carried`, que pasó a fallar en 0.1.209 y
en 0.1.211 por mi clave, no por D112b (9 de 18 y 17 de 18). La clave va en una
constante aparte. Re-medido contra a6eceda con el archivo final: **fallan los
mismos 8 casos** de su cabecera; en 0.1.211 y 0.1.212 pasan los 18.

---

## 3. Lo que se reporta y NO se corrige (regla 6)

- **D203 (P3), ficha nueva: la etapa 2 no convergida.** `rapid_drawdown_fos`
  tampoco mira `r2.converged`. Con Duncan-Wright-Wong o Corps, el casquete
  drenado arranca de las normales de esa pasada, y el factor se elige con
  `fos_stage3 < fos_stage2` usando el F2 no convergido.
  - Si gana el casquete y su última pasada converge, la superficie sale
    **válida** y `details["fos_stage2"]` publica el F de reserva como si fuera
    un factor.
  - **Son tres mínimos de búsqueda del 096:** Corps 1, Corps 2 y
    Lowe-Karafiath comparten el círculo crítico (207,25; 183,33; 110,80). Ahí
    la etapa 2 da F2 = 5,0 (`no_force_bracket`), y 16 pasadas del casquete
    convergen a 1,4627, 1,462927 y 1,449929.
  - En ese círculo Bishop, Spencer y GLE **sí** convergen en la etapa 2, con
    **F2 ≈ 5,44**: la raíz existe y cae justo encima de la rejilla
    [0,2; 5,0] de la familia, que no tiene extensión perezosa (la de λ sí).
  - En 0.1.212 son 1190 etapas 2 no convergidas: **528 superficies válidas**
    (484 `no_force_bracket`, 44 `no_lambda_bracket` de Spencer y GLE) y 662
    inválidas porque esa etapa 2 fue la respuesta.
  - Ninguna fila publicada. No se tocó por la ficha de D202.
- **Por qué la familia de inclinación prescrita no encuentra horquilla** en
  el testigo, donde Bishop y Spencer convergen: no investigado. Puede ser
  legítimo (el equilibrio de fuerzas con θ impuesto no siempre tiene raíz) o
  una raíz que la rejilla [0,2; 5,0] no ve.

---

## 4. Los tests

| Archivo | Casos | Fallan en 0.1.211 | Por comportamiento |
|---|---|---|---|
| `test_drawdown_stage1_v1212.py` (nuevo) | 16 | 10 | 10 |
| `test_drawdown_passthrough_v1210.py` (adaptado) | 18 | 0 (8 en 0.1.209, como antes) | — |

Los 6 que pasan en 0.1.211 son las dos guardas del testigo y los cuatro
controles (el factor de la etapa 1 marcada inadmisible es bit a bit el del
método sin marcar; el círculo publicado del Apéndice G sigue válido; LK
convergido por debajo de 1 sigue siendo «no aplica»; Bishop y Spencer en el
testigo no se mueven).

**Suite entera, sin argumentos: 4680 casos, 4680 pasan, 0 fallan** (266
archivos), sobre el estado final, en 34 min 10 s (sección 6).

---

## 5. El banco (fuera de git)

- **`_tools/censo_p3_desembalse.py`, ampliado:**
  - `--salida <carpeta>`: un solo JSON en `_auditoria/<carpeta>/`, sin la
    copia de D184; `--comparar` lee la base de la misma carpeta;
  - `--con-095`: las búsquedas enteras del 095 (su etapa 1 es la del 096);
  - `--doc <nombre>` para `--informe` (aquí
    `docs/audits/drawdown_stage1_v1212.md`);
  - por superficie, el veredicto de la etapa 1 (factor, convergencia, razón,
    admisibilidad) y la convergencia de la etapa 2; por búsqueda, los
    recuentos de D202 y de (b), cinco ejemplos de cada clase para
    reproducirlos, y `minimo_predicho_d202`;
  - un control nuevo: el testigo del Apéndice G y la etapa 1 inadmisible
    sintética, que los espías tienen que ver en los dos árboles.
- **Una trampa evitada: las carpetas de D184/D194/D200 son evidencia
  congelada.** `verificar_cierres._censo_desde` toma el `censo_<v>.json` más
  nuevo ≥ la versión de cierre. Un `censo_0.1.212.json` en
  `D194_D200_casquete/` o `D184_cribado/` habría tumbado d184, d194 y d200, que
  exigen `comparado_con == "0.1.210"`, sin que su arreglo hubiera regresado.
  El censo ahora aborta si mide un motor posterior a 0.1.211 sin `--salida`.
- **Censos:** `_auditoria/D202_etapa1/censo_0.1.211.json` (antes, worktree en
  03c9447) y `censo_0.1.212.json` (después, este árbol), más las dos
  discriminaciones archivadas y el `verificar_cierres.py` de 0.1.211.
- **Cierre nuevo en `verificar_cierres.py`:** `d202`, CUBIERTO POR TEST, con
  `CIERRE = 0.1.212`.
  - En vivo usa solo símbolos que ya existían en 0.1.211: el testigo del
    Apéndice G (copia del fixture), un Bishop sintético no convergido y otro
    inadmisible.
  - AST: `r1.converged` se lee antes de la llamada a `_stage1_state`, y
    «D202» está en el docstring.
  - Censos: antes y después, con la predicción cumplida y el 1,7093 del
    control de antes citado en el docstring del motor.
  - Discriminación: 10 de 16.
- **Ficha nueva:** D203, con su prompt largo, en P3. El siguiente número libre
  es D204.

### Una trampa de herramienta, no del motor

El volcado de veredictos que hice para comparar los cierres antes y después no
tenía guarda de `__main__`. Varias comprobaciones lanzan hijos con `spawn`, que
en Windows re-importan el módulo principal: cada hijo volvía a correr el
volcado entero. Es la trampa que la memoria del banco ya anotaba para los
censos con `sitecustomize`. Se paró a mano, se tiró la corrida y se repitió con
la guarda: 162 claves en 912 s.

---

## 6. Verificación

- **Suite entera, sin argumentos, sobre el estado final:** 4680 de 4680 (266
  archivos), 34 min 10 s. Una primera corrida, antes de corregir tres
  docstrings que decían que las etapas 2 y 3 llevan SIEMPRE su veredicto, dio
  también 4680 de 4680.
- **Discriminación de los tests**, medida en worktrees y archivada en el
  banco: el nuevo, 10 de 16 en 0.1.211; el de D112b adaptado, los mismos 8 de
  18 en 0.1.209.
- **Censos antes y después** (095–098 con las búsquedas del 095):
  - 0 filas y 0 mínimos movidos, 0 fuera de la predicción, 0 sin pareja;
  - los cuatro controles ven su caso;
  - 0 excepciones del cribado (D184) en los dos.
- **`d202`:**
  - contra este árbol, CUBIERTO POR TEST;
  - contra el worktree de 0.1.211, NO SE SOSTIENE por comportamiento: el
    testigo vuelve válido con 1,7093, el Bishop no convergido vuelve válido y
    el inadmisible, admitido;
  - con `_SIN_HISTORICO = True` deja de cerrar;
  - `d175`, `d186` y `d187` siguen cerrando.
- **Regresión de cierres, clave a clave:** todos los veredictos de
  `verificar_cierres.py`, antes (motor y herramienta de 0.1.211, 162 claves) y
  después sobre el estado final del banco (163), con el detalle entero:
  - **0 bajadas y 0 cambios de veredicto**; solo entra D202;
  - cuatro detalles cambian, todos por un recuento que la tanda mueve: D174
    cuenta un archivo más (el test nuevo), D186 una clave más (D202), D188 una
    cita más en el índice (el renglón de D202) y la instantánea 0.1.212, y D96
    204 `.ogr` más (los de la instantánea nueva).
- **Banco:**
  - instantánea `Evaluaciones/0.1.212`, antes de retirar y otra vez con
    `--forzar` al final (2637 archivos, comprobados byte a byte);
  - `retirar_cerrados.py --escribir D202`, con la sección guardada en
    `ERRORES_Y_DISCREPANCIAS_retiradas.md`;
  - `PAQUETES` podado (P3 queda D168, D169, D203) y la cadena de P3 tachada;
  - `generar_prompts.py`: 50 prompts, 41 largos, las 9 FALTA previas y 0 sin
    paquete;
  - `generar_comparativa.py` y `balance_evaluaciones.py` contra
    `Evaluaciones/0.1.211`: 559 → 559 filas, todas IGUAL, 0 sin pareja;
  - `auditoria_invariantes.py`: 0 ERROR en el 02 (487 AVISO y 257 INFO, los
    mismos recuentos que en 0.1.211) y 0 ERROR en la raíz;
  - `comprobar_citas_prompts.py`: nada en D203; el único problema es el de
    D135, anterior a esta tanda.

**Lo que falta por probar, dicho:**

- una etapa 1 inadmisible NATURAL: no hay ninguna en el 095–098, así que ese
  camino solo lo ejerce el Bishop sintético del test;
- D203, reportada y sin corregir: tres mínimos del 096 dependen de una etapa 2
  no convergida;
- el probabilístico y el barrido de niveles sobre modelos con desembalse
  multietapa del banco: no hay ninguno (el 100 y el 101 son B-bar, a los que
  este cambio no llega);
- por qué la familia de inclinación prescrita no encuentra horquilla en la
  etapa 1 del testigo (ahí la raíz, si la hay, estaría dentro de su rejilla);
- la CI de GitHub (Linux, Python 3.11–3.13): los tests nuevos usan
  `math.isclose` y una ley (una llamada, no un recuento de pasadas), pero solo
  se sabrá tras el push.
