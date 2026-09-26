# OGR Slip2D v0.1.209

**Las dos fichas que quedaban en P2 con número de motor, D155 y D158, se
resuelven juntas porque se vigilan una a la otra (decisión del propietario,
2026-09-25).** D155 avisaba de que «la próxima versión que toque el solver de
ramas» volcaría sus filas al borde, y esa versión es D158. Así que primero se
midió D155 con 0.1.208, después se tocó el motor, y el censo de D155 hizo de
cable trampa del cambio.

- **D158 cambia el motor.** El detector de estancamiento de `solve_branch`
  mira ahora el PAR (F, X): el contador se pone a cero cuando cualquiera de los
  dos residuos bate su récord (`BRANCH_STALL_PAIR`).
- **D155 no cambia el motor.** El veredicto de admisibilidad por el signo del
  empuje es binario a propósito, y se declara con el censo delante.
- **De la medida nace D193**, que se reporta y no se corrige: la exención plana
  de D152 lee el signo del empuje antes de que se asiente.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
no está en git y se describe aquí.

---

## 0. Lo que estaba mal en los encargos y en las herramientas

### P-D158 estaba desfasado respecto a su propia ficha

El prompt seguía diciendo «el censo dice que hoy está DORMIDO» y pedía
«instrumentar antes de decidir». La ficha, el changelog de v0.1.186 y
`docs/audits/branch_stall_v1186.md` ya lo habían refutado sobre búsquedas
enteras: 60 536 ramas estancadas y una población de 627 (616 en el cubo ii,
11 en el iv). El paso 1 del prompt estaba hecho desde 0.1.186; faltaba el 2.

### El cubo (iv) del censo de 0.1.186 medía otra cosa

En `estancamiento_d158._clasificar` el `paso` de F de una rama estancada
valía **0,0 bit a bit, siempre**. El estancamiento hace `break` antes de
actualizar F, así que la rama estancada devuelve F_k; la llamada limitada a
`passes − 1` termina su última pasada con la actualización, que produce ese
mismo F_k. Medido en la cuña de D152: 0,0 frente a un |ΔF| real de 4,4e-16.

Consecuencia: el cubo (iv), «F y X asentadas», solo exigía `d_x < tol`. La
población de 627 sigue valiendo como «empuje contrayendo o ya dentro de
tolerancia»; lo que era falso es la etiqueta. Corregido: el paso es ahora
F_{k+1} − F_k, con el detector fuera.

### P-D155 decía 14 filas al borde y el informe publicado, 13

No era un error, era el denominador. La ficha contó todas las filas del
censo; el informe de 0.1.185, solo las medidas. La que sobraba (085 no
circular pasivo, Spencer, margen 0,0033) estaba descuadrada.

### La tabla interruptor→versión se había parado en 0.1.185

`elegibilidad_critica_d155.py` reconstruye «el motor que escribió cada
archivo» apagando los interruptores posteriores a su versión. Tenía 9 y el
motor 12: faltaban `LAMBDA_STATE_CACHE` (0.1.186), `BRANCH_PARTNER_RETRY`
(0.1.193, que sí mueve factores) y `slicer.CRACK_WALL_ON_LINE` (0.1.208, en
otro módulo, que el contexto no sabía tocar). Con la tabla vieja, un archivo
de 0.1.180 se reconstruía con el reintento del compañero encendido.
Ampliada, con `BRANCH_STALL_PAIR` (0.1.209) incluido. El contexto acepta
ahora `modulo.NOMBRE`. La atribución del 085 contra 0.1.180 sale igual: 3
vuelcos, 2 atribuidos a `BRANCH_PAIR_TIGHTEN`.

### Una frase del informe de D155 contradecía su propia tabla

`path_eligibility_v1185.md` decía «35 de 38 [archivos no circulares] son de
0.1.173 y uno de 0.1.147», escrito a mano, justo debajo de una tabla que
decía 37 de 0.1.185 y 1 de 0.1.147. Ahora la frase sale de los datos.

---

## 1. D158 — el detector de estancamiento mira el par (motor)

### El defecto

El estado que itera `solve_branch` es el par (F, X). Desde v0.1.179 (D145)
lo saben la aceptación y la entrada al rescate, pero el contador de
estancamiento se ponía a cero solo cuando el paso de F batía su récord. Su
comentario lo justificaba con que un punto fijo que contrae «bate su récord
en cada pasada», y eso es falso justo en el punto fijo. Con `step == 0.0`,
`0.0 < 0.0` no vuelve a cumplirse: la rama se cortaba **por haber llegado**,
con su empuje todavía contrayendo.

### El arreglo

`best_d_x` junto a `best_step`, también reiniciado a la entrada del rescate.
El contador vuelve a cero si **cualquiera** de los dos bate su récord.

Neutralidad demostrada:
- `best_step` se actualiza exactamente igual que antes, y el empuje solo
  puede *añadir* reinicios;
- nada más del bucle lee el contador;
- por tanto, la trayectoria es la de 0.1.208 pasada a pasada hasta el `break`
  que cortaba la rama. **Solo pueden cambiar las ramas que antes se
  estancaban.**

Con su interruptor (`BRANCH_STALL_PAIR`), leído en tiempo de llamada y
añadido a `_BRANCH_SWITCH_NAMES` para que la caché de λ lo lleve en su firma.

### El testigo, contra una referencia externa (regla 1 y regla 7)

Cuña anclada activa, plano de 50°, λ = 1,25, tolerancia 1e-10, exención
plana de D152 apagada para que decida el detector:

| | pasadas | converge | error frente a la forma cerrada |
|---|---|---|---|
| interruptor apagado | 271 (estancada) | no | 2,3e-14 (F ya era correcto) |
| encendido, presupuesto 400 | 400 (presupuesto) | no | — |
| encendido, `max_iterations = 2000` | **1218** | **sí** | **2,3e-14** |
| configuración de serie (exención encendida) | 48 | sí | idéntica bit a bit |

Forma cerrada: Coulomb (1776), con el soporte resuelto en la base como en
Duncan y Wright (2005) §6. Independencia respecto al empuje: Krahn (2003) y
EM 1110-2-1902 SC-7a. Con el presupuesto por defecto el cambio solo
*renombra la salida*, como la ficha predijo: 1218 pasadas no caben en 400.

### Lo que también arregla, sin buscarlo

El «límite honrado» escrito bajo `STALL_PATIENCE` desde D63 queda resuelto.
La rama de momentos del plano de 50° en λ = 2,0, con el rescate apagado, se
cortaba en la pasada 85 por un récord accidental temprano de F. Ahora
converge en la **117** solo por amortiguamiento, a 11,7
tolerancias del punto fijo (el límite `tol·r/(1−r)` con r = 0,96 da unas
25). Con el rescate encendido, como se distribuye, es la misma rama de 116
pasadas en los dos casos: el rescate ya la tomaba en la pasada 81.

Un ciclo de periodo 2 **sigue cortándose**: su empuje cicla con F, así que
ninguno de los dos récords se bate. El 091 en λ = 0,40, con el rescate
apagado, sale en la pasada 83 en vez de la 81.

### El A/B sobre el banco

Búsquedas **enteras**, no críticas archivadas. Cada fila se corre dos veces
en el mismo proceso, con el interruptor encendido y apagado. Población: los
22 problemas del censo de 0.1.186 y todos los archivos de los reforzados
(085, 087–094), donde están las 14 filas al borde de D155. Informe en
`docs/audits/branch_stall_v1209.md`, generado por
`_tools/estancamiento_d158.py --ab`.

| | |
|---|---|
| filas / problemas | **73 / 30**, ninguna saltada ni sin medir |
| **mínimos publicados que se mueven** | **0** (tampoco cambia ninguna bandera de admisibilidad) |
| neutralidad, rama a rama | **3 657 568 ramas idénticas bit a bit, 0 rotas** |
| control de determinismo | 30 de 30 |
| pasadas, apagado → encendido | 663 045 415 → 741 550 931, **+11,84 %** |
| Spencer / GLE | +3,3 % (41 filas) / **+20,8 %** (31 filas) |
| ramas que se estancaban (convertidas) | 897 366 |
| … ahora convergen | **259 203** |
| … ahora agotan el presupuesto | 176 699 |
| … se estancan más tarde | 461 314 |
| … desbordan / sin estado | 20 / 130 |

El reparto entre Spencer y GLE está medido, pero su causa no.

**La neutralidad se ejecutó, no solo se demostró.** Dentro de la corrida
encendida, cada rama de más de 80 pasadas o sin estado se volvió a resolver
con el detector viejo. Si ahí no se estancaba, tenía que salir idéntica:
`fos`, pasadas, convergencia y `boundary_x`.

**Un caso límite que parecía una rotura y no lo es.** El detector viejo
puede cortar justo en la última pasada del presupuesto. `GLESystem.branches`
lo cuenta entonces como «presupuesto agotado» (`passes == max_passes`), pero
el corte ocurre **antes** de actualizar F. El detector nuevo completa esa
pasada y devuelve una rama con las mismas pasadas y F una actualización más
allá. Ninguna de las dos converge y el λ se pierde en ambos lados. Hubo 48
casos, todos en la pasada 400; la herramienta los reclasifica como ramas
convertidas.

**El coste de la medida, que conviene recordar.** El A/B tardó unas 24 h de
reloj en este portátil (i7-8550U, 4 núcleos físicos): 7 procesos agotaron la
memoria a las 2 h 20 min, y hubo que relanzar con 4 y soltar cada búsqueda
en cuanto se había leído. Además, el equipo se suspendió 3 h 20 min de
madrugada.

**Qué no hay que re-correr.** Ningún mínimo se mueve, así que ningún
`resultados*.json` del banco cambia con esta versión y no se re-corre nada.

---

## 2. D155 — el veredicto del empuje es binario a propósito (banco)

### El censo con 0.1.208, antes de tocar el motor

`_tools/elegibilidad_critica_d155.py`, con la tabla de interruptores ya
completa. Informe en `docs/audits/path_eligibility_v1208.md`.

| censo | medidas | al borde (\|margen\| < 0,05) | vuelcan |
|---|---|---|---|
| banco vivo, motor 0.1.208 | 230 | **14** | 0 |
| contra la instantánea 0.1.180 | 229 | 11 | **3**, las tres del 085 no circular, 2 atribuidas a `BRANCH_PAIR_TIGHTEN` (igual que en 0.1.185) |
| contra la instantánea 0.1.207 | 230 | 14 | 0 |

Las 14 filas son reforzadas y salen todas por la reserva de λ. Cinco están
por debajo de 0,001: 093 y 094 sin conexión, 087 ×2 y 094 `resultados`,
todas en GLE. Desde 0.1.185 ha entrado al borde 092 Spencer (0,448 → 0,012,
re-corrido en 0.1.188), y se han alejado 090 y 093 Spencer.

### El cable trampa: 0.1.209 contra la instantánea 0.1.208

Ninguna de las 237 críticas archivadas cambia un bit (factor, margen ni
bandera). 0 vuelcos, las mismas 14 al borde.

### La banda muerta, estimada y descartada

P-D155 dejaba dos salidas: medir si `thrust_is_admissible` debía llevar una
banda muerta, con referencia externa y A/B, o declarar el veredicto binario
a propósito. Se toma la segunda (decisión del propietario, 2026-09-25), y la
medida la respalda.

**No hay referencia para una banda.** Spencer (1967) y Ching y Fredlund
(1983) justifican el **signo** del empuje entre dovelas, no una tolerancia
alrededor de cero.

**Una banda razonable no habría parado el vuelco que abrió la ficha.** En
el 085 el margen pasó de +0,044 a −0,627 con un cambio del 0,10 % en el
factor: 0,67 de margen, trece veces la banda más ancha considerada.

**Lo que sí haría una banda.** Estimación de primer orden sobre las mismas
búsquedas del A/B de D158, sin corridas extra. Se cuenta como admisible una
superficie que la criba dejó pasar y que el método rechazó **solo** por el
signo del empuje, si `margen > −ε`:

| ε | filas cuya crítica cambia | superficies en la banda | mayor bajada |
|---|---|---|---|
| 0,001 | **0** | 86 | — |
| 0,01 | 3 | 977 | −1,22 % |
| 0,05 | 12 | 6 317 | −7,63 % |

- **ε = 0,001 no mueve nada**: sería un ajuste que no hace nada (regla 7).
- **Las bandas mayores mueven filas de problemas reforzados**, incluidas
  algunas que no estaban al borde. Lo hacen **admitiendo superficies cuyas
  caras de suelo están en tracción neta**.
- **Es de primer orden**: la banda solo actúa en la elección de la crítica,
  no dentro de la búsqueda de λ.

**Lo que queda.**
- `thrust_is_admissible` sigue comparando con cero, y su docstring explica
  ahora por qué («WHY NO DEAD BAND»).
- `thrust_margin` publica a qué distancia está cada veredicto de volcar
  (desde 0.1.185).
- La comparativa del banco marca con «⚠ N descartadas» la fila cuyo mínimo
  se eligió dejando fuera superficies más bajas (desde 0.1.185; 203 filas
  hoy).

**Cable trampa cumplido.** La versión que tocó el solver de ramas no volcó
ninguna de las 14 filas al borde, ni sobre las críticas archivadas ni sobre
las búsquedas enteras.

---

## 3. Lo que se reporta y NO se corrige (regla 6)

### D193 — la exención plana lee el signo del empuje antes de que se asiente

D152 (v0.1.183) deja aceptar la rama de fuerzas de un plano sin esperar al
empuje, porque ahí el factor no depende de él. Pero la rama aceptada lleva
el empuje **de esa pasada**, y sobre él se decide la admisibilidad. Medido
en la cuña anclada (activa, 50°, λ = 1,25, tolerancia 1e-10):

| estado | pasada | ΣE interior (kN/m) | margen | admisible |
|---|---|---|---|---|
| aceptado por la exención | 48 | −64,35 | **−0,119** | **no** |
| punto fijo (detector por pares, `max_iterations = 2000`) | 1218 | +258,00 | **+0,420** | **sí** |

El factor es el mismo en los dos casos. Lo que se lee demasiado pronto es el
signo, y sale el contrario al del punto fijo. Queda sin medir cuántas ramas
del banco lo ejercen: la única rama de fuerzas plana conocida es la del 047,
y que su crítica inadmisible (margen −1,0) se deba a esto no está medido.
Ficha y prompt largo en el banco; fijado en
`test_stall_pair_v1209::TestWhatThisVersionDoesNotDo`. Va en P2.

### Sin número: `GLESystem` cuenta como presupuesto un estancamiento en la última pasada

Es el caso límite de §1. Solo cambia el contador (`lambdas_lost_to_budget`
frente a `lambdas_lost_to_stall`) y, con él, la frase de la nota que ve el
usuario; ningún número. Es de la misma clase que D158, así que se anota en
ella y no consume número. No se corrige aquí.

---

## 4. Los tests

**Nuevo: `tests/test_stall_pair_v1209.py`, 9 casos.**
- El testigo contra la forma cerrada.
- La neutralidad, llamada a llamada, sobre la escalera de cuñas y sobre
  ACADS 1(c) con Spencer y GLE.
- Que con el presupuesto por defecto solo cambia la salida.
- Que con la exención encendida no se mueve nada.
- La firma de la caché de λ.
- Que el interruptor apagado es el detector de 0.1.208.
- D193, fijado como lo que esta versión no hace.

Ejecutado contra un worktree de 0.1.208 (`PYTHONPATH` apuntando a él):
**fallan 4**. Tres por diferencia medida: converge a la forma cerrada, solo
renombra la salida, y el juicio del empuje sin asentar. Uno por el símbolo
ausente (la firma de la caché). Los otros cinco pasan en los dos árboles a
propósito: son los controles.

**Recalibrados, cada uno con la razón escrita y sin ensanchar bandas:**
- `test_branch_contraction_v1172::TestWhatThisDoesNotFix`. La clase se
  escribió para ponerse roja el día que se reparara uno de sus límites, y es
  lo que ha pasado. El límite queda fijado **tal como era**, con el detector
  viejo (pasada 85, sin converger). Un caso nuevo fija la reparación: pasada
  117, a menos de 25 tolerancias del punto fijo.
- `test_branch_rescue_v1176`, dos casos. Su lado «antes» es el solver de
  0.1.175, así que también lleva el detector viejo. Además, el ciclo de
  periodo 2 del 091 se sigue cortando con el detector nuevo (pasada 83).
- `test_planar_force_branch_v1183`. El caso que leía el código fuente para
  afirmar que el detector miraba media pareja ahora **ejecuta** la
  predicción de su propio docstring: 400 pasadas, sin converger. Un segundo
  caso gana una nota sobre D193.

---

## 5. El banco (fuera de git)

**Herramientas:**
- `_tools/elegibilidad_critica_d155.py`:
  - la tabla de interruptores, completa hasta `BRANCH_STALL_PAIR`, con
    nombres `modulo.NOMBRE`;
  - la frase de obsolescencia, que ahora sale de los datos.
- `_tools/estancamiento_d158.py`:
  - modo `--ab` (búsquedas enteras encendido/apagado con contabilidad rama a
    rama, estimación de la banda de D155, un JSON por proceso que se puede
    reanudar, avance visible, y cada búsqueda soltada en cuanto se ha leído);
  - `--ab-informe`;
  - el `paso` de `_clasificar` corregido;
  - `asegurar_motor` en lugar de meter el repositorio en `sys.path` (D187).
- `_tools/verificar_cierres.py`:
  - `d158()` reescrita para la segunda rama de su criterio, con
    `CIERRE["D158"] = "0.1.209"`;
  - `d155()` ampliada: mientras la re-enunciación de 0.1.185 se sostenga
    sigue devolviendo al menos RE-ENUNCIADO, que `d175` acepta, y cierra
    como SE SOSTIENE con el censo, el cable trampa, la declaración y la
    banda.
- `_tools/generar_prompts.py` (raíz): P2 podado a `["D143", "D193"]`.

**Fichas y prompts:**
- D155 y D158, con su párrafo de cierre y retiradas a
  `Evaluaciones/0.1.209/ERRORES_Y_DISCREPANCIAS_retiradas.md`;
- D193, nueva, con su prompt largo en `_auditoria/doc/prompts_largos/`;
- la cabecera del ERRORES pasa a «último D193, siguiente libre D194»;
- la cadena de P2 queda tachada.

**Censos:**
- `_auditoria/D155_elegibilidad/censo_0.1.208*.json` y
  `censo_0.1.209_desde0.1.208.json`;
- `_auditoria/D158_estancamiento/ab/ab_0.1.209_*.json` (41 archivos, 73
  filas).

**Instantánea:** `Evaluaciones/0.1.209`, congelada antes de retirar y otra
vez al final (1791 archivos, comprobados byte a byte).

---

## 6. Verificación

- **`tests/_runner.py` entera y sin argumentos: 4579 de 4579**, en 43 min 55 s.
- **`test_stall_pair_v1209.py` contra un worktree de 0.1.208**: fallan 4 de 9
  (§4).
- **`verificar_cierres.py`:**
  - D155 SE SOSTIENE y D158 CUBIERTO POR TEST, con todas sus medidas;
  - D175, D186 y D187, que vigilan a los demás cierres, CUBIERTO POR CODIGO;
  - ninguna bajada.
- **`generar_comparativa.py`**: las 559 filas iguales. Solo cambia la frase
  que nombra la versión instalada (decía 0.1.207: en 0.1.208 no se
  regeneró).
- **`balance_evaluaciones.py`** contra `Evaluaciones/0.1.208`: 559 → 559,
  todas IGUAL, ninguna sin pareja.
- **`auditoria_invariantes.py`**: 0 ERROR en el 02 y en la raíz.
- **`generar_prompts.py`**: 47 prompts, 0 sin paquete, ninguno cerrado en
  `PAQUETES`.
- **Versión**: los nueve sitios a 0.1.209
  (`test_version_consistency_v176`, dentro de la suite).
