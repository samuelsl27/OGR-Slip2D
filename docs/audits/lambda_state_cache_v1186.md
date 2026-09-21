# La caché por λ de `GLESystem.states` — A/B de D159 — OGR 0.1.186

Medido en el repositorio del motor, no en el banco: lo que D159 cambia es el
número de veces que se resuelve una rama, y eso se ve entero en una búsqueda de
un solo modelo. El banco entra sólo como control de que nada publicado se mueve.

## Qué se midió, y con qué

Una búsqueda de rejilla **completa** del modelo del problema 059 —la fixture en
código de `tests/test_lambda_closure_v1180._slope`, que reproduce el modelo del
banco dígito a dígito— con `parallel_search = False`, en **un solo proceso**.
1795 superficies evaluadas por `compute_fos`, 1736 archivadas por la búsqueda.

## El recuento de repeticiones, y el 80 % que era del medidor

| | |
|---|---|
| llamadas a `GLESystem.states` | 17 872 |
| de ellas, un λ que ese sistema ya había resuelto | **3578 (20,0 %)** |
| pasadas de rama totales | 757 378 |
| gastadas en esas repeticiones | **144 114 (19,0 %)** |
| reparto | 1783 superficies con 2 repeticiones, 12 con 1 |

**La primera versión de esta medida dijo 80 %, y estaba mal por una razón que
merece quedar escrita**: agrupaba las repeticiones por `id(system)`, y CPython
reutiliza un `id` en cuanto el objeto se libera, así que 1795 superficies
distintas se leían como una sola. Con un contador de generación que
`compute_fos` incrementa, el número es 20,0 %. Un medidor que se equivoca en la
dirección que favorece al cambio es el peor de los dos errores posibles.

## La cautela de la ficha es falsa, y se puede nombrar por qué

D159 avisa de que contar pares «puede sobreestimar el tiempo por un factor
grande», porque el par final «arranca de un `initial_fos` pegado al punto fijo».
**No hay arranque en caliente.** `GLESystem.states` pasa siempre
`self.initial_fos`, escrito una sola vez en `__init__` y nunca más, así que toda
rama de todo λ arranca de la misma F y una repetición cuesta exactamente lo que
costó la primera, a la pasada. Por eso el 20,0 % de las llamadas son el 19,0 %
de las pasadas: la diferencia entre esos dos números no es un arranque caliente,
es qué λ resultan ser las repeticiones.

## El A/B, en un proceso y espalda con espalda

`ON → OFF → ON`, con el control repetido, como exige AGENTS.md:

| corrida | segundos | pares de rama | crítico |
|---|---|---|---|
| ON (control 1) | 38,0 | 28 588 | 0,202605263147 |
| OFF | 49,5 | 35 744 | 0,202605263147 |
| ON (control 2) | 41,3 | 28 588 | 0,202605263147 |

**El número que no tiene ruido es el de pares**: 35 744 → 28 588, exactamente
**−7156, el 20,02 %**, idéntico en las dos corridas de control. El crítico
coincide a doce cifras en las tres, y las tres evalúan 1736 superficies.

**El cronómetro dice menos, y se publica igual.** Los dos controles difieren
entre sí un **8,7 %** (38,0 s contra 41,3 s), y el efecto contra la media de los
controles es del 19,9 %. O sea que el reloj **sí** distingue un efecto de este
tamaño —es unas 2,3 veces la dispersión de sus propios controles— pero no fija
su valor. AGENTS.md dice que en esa situación manda el razonamiento sobre el
trabajo suprimido, y aquí el razonamiento es exacto y no una estimación: dos
pares de rama por superficie que horquilla, sobre 1783 de 1795, que son 7156 de
35 744 medidos uno a uno.

## Sobre una superficie sola

| | ON | OFF |
|---|---|---|
| Spencer, círculo de la fixture del 059 | 16 llamadas a `solve_branch` | 20 |
| GLE, círculo de `test_lambda_floor_v1184` | 18 | 22 |

Cuatro llamadas = **dos pares**: el `solve(lam_lo)` del cierre y el
`system.states(lam_lo)` de dos líneas más abajo. Y el factor idéntico al último
bit en los dos métodos.

## Que es una identidad: medido, no argumentado

Sobre la misma búsqueda entera, comparando cada repetición con el primer
cálculo de ese λ **campo a campo y lista a lista** —`fos`, `converged`,
`passes`, `abandoned`, `rescued`, `normals`, `resisting`, `boundary_e`,
`boundary_x`—:

| | |
|---|---|
| repeticiones comparadas | 3578 |
| **idénticas bit a bit** | **3578** |
| distintas | **0** |

Esa determinación era, hasta esta versión, una afirmación del docstring de
`thrust_rejected_pairs` (v0.1.182) de la que el paquete ya dependía —
`recover_thrust_edge` se fía de un par registrado en una pasada anterior
precisamente por ella— y que nadie había ejecutado. Ahora la ejecuta
`test_lambda_state_cache_v1186::test_two_calls_from_scratch_agree_bit_for_bit`.

## Por qué no hay corrida de banco, y por qué eso no es un atajo

La ficha D159 exige un A/B del banco declarando fila a fila qué contadores se
mueven, «porque moverse se van a mover». **Eso es cierto del otro arreglo que la
ficha ofrece y falso de éste**, y la diferencia se puede escribir en tres
líneas:

1. los siete contadores se incrementan **dentro de `GLESystem.branches`**
   (`interslice.py`), a partir de los objetos `BranchState` que `states`
   devuelve — y eso lo comprueba por AST
   `test_lambda_state_cache_v1186::test_every_counter_moves_inside_branches`,
   en vez de dejarlo en una frase;
2. la caché vive **debajo** de `branches`: no desaparece ni una llamada. El
   `solve(lam_lo)` del cierre es un **acierto**, no una supresión;
3. luego `branches` se entra el mismo número de veces con los mismos objetos, y
   `n_rescued`, `n_stalled`, `n_passes_exhausted`, `n_thrust_overflow`,
   `n_inadmissible`, `n_thrust_rejected` y `thrust_rejected_pairs` leen lo que
   leían.

El arreglo que la ficha describe al pie de la letra —`ff_final, fm_final =
ff_lo, fm_lo`— **sí** quita esa llamada, y con ella un incremento, y por eso
habría pedido la corrida. Esta versión no lo hace.

Dos pruebas de esto ya existían y corrían antes de que hiciera falta:
`tests/test_branch_rescue_v1176.py::test_a_loss_is_counted_even_when_the_partner_is_none`
pide `states(1.0)` y después `branches(1.0)` sin cambiar nada en medio y exige
que el contador suba; y
`tests/test_max_iterations_scope_v1173.py` hace lo mismo con
`n_passes_exhausted`. Las dos son exactamente el patrón «acierto de caché y el
contador sube igual», y las dos siguen verdes.

## El riesgo que la caché sí tiene, y la guarda

Un `GLESystem` **capturado** que sobrevive a un cambio de interruptor devolvería
el par viejo en silencio. No es hipotético:
`tests/test_branch_rescue_v1176.py::test_a_stall_is_counted` construye el
sistema con `_system_091()`, que resuelve la rejilla **fuera** de cualquier
context manager, y después pregunta por `branches(0.40)` **dentro** de
`_unrescued()`. Medido: λ = 0,40 es nodo de `_LAMBDA_SHAPE` y queda en la caché,
y el estado difiere por completo entre los dos lados.

| | `converged` | `rescued` | `passes` | `fos` |
|---|---|---|---|---|
| rescate ON | True | True | 45 | 0,970571490929 |
| rescate OFF | False | False | 81 | 1,11632765164 |

La guarda es que **cualquier cambio en `_BRANCH_SWITCH_NAMES` vacía la caché**.
Se eligió eso y no un interruptor que haya que acordarse de apagar, ni un `with`
alrededor del cuerpo de los dos métodos, por dos razones: no obliga a editar
ningún test ni ninguna herramienta del banco —ese caso sigue verde sin tocar una
línea—, y su único punto débil, que la lista se quede vieja, lo cierra un caso
que la compara **por AST** con los globales que el cuerpo de `solve_branch`
realmente lee.

`test_the_guard_is_load_bearing` lo demuestra en vez de argumentarlo: anulando
la firma, el lado «sin rescate» devuelve la rama **rescatada**.

## Lo que esta medida NO dice

- No dice cuánto se ahorra en el banco. El reparto de λ repetidos depende de
  cuántas superficies horquillan, y eso varía por problema.
- No dice que el ahorro sea el 20 % del tiempo de un análisis. Es el 20 % de los
  **pares de rama**, y una búsqueda también rebana, resuelve soportes y puntúa.
- No mide el arranque de la aplicación ni la memoria en una corrida larga. La
  cota de memoria está razonada en el bloque `#:` de `LAMBDA_STATE_CACHE` y
  fijada por `test_the_cache_holds_one_entry_per_distinct_lambda`.
