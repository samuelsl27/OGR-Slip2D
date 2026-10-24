# OGR Slip2D v0.1.361

**El test que demuestra que `LOOP_SETTLED_FACE` mueve el número ya no depende del redondeo de la
máquina. La primera CI que corrió los tests de 0.1.358 lo encontró: en el runner de Python 3.12, la
presa 2 de la puerta, con el interruptor apagado, sale convergida. Sin cambios en el motor.**

## 0. Lo que se encontró

- **La CI.** Es la 40114552618, de la subida de 0.1.358 a 0.1.360, que hasta entonces estaban sin
  subir.
  - En Python 3.11 y 3.13: 6534 tests aprobados, 2 omitidos y 0 fallos. El rojo es solo el fallo de
    segmentación al salir, el de siempre (desde 0.1.276, sin diagnosticar).
  - En Python 3.12, un fallo: `test_picard_loop_face_v1358::TestTheDoorOnDam2::test_switched_off_the_loop_stops_with_the_face_unsettled`,
    en `assert r.converged is False`. Con el interruptor apagado, la presa 2 ×1 con los ajustes de la
    puerta salía convergida.
- **No era una versión de librería.** Los runners de 3.12 y 3.13 llevan las mismas NumPy (2.5.4) y
  SciPy (1.18.1), y solo falla 3.12.
- **Era el redondeo.** Encendido y apagado hacen el mismo bucle; el interruptor solo actúa cuando el
  bucle acaba.
  - En 3.12, el «encendido» pasó con el rescate por la continuación. La única lectura coherente: allí
    el bucle no llegó a parar en 200 pasadas, y el rescate lo resolvió en los dos casos.
  - En esta presa, el bucle para en el filo de la tolerancia: su último cambio relajado es de 6e-6 a
    9,9e-6, frente a 1e-5.
- **La medida, sin tocar el motor** (`_auditoria/P6_0361/apagado_v1358.py` del banco). Se emula otra
  máquina desplazando ω unas unidades del último lugar, que cambia el redondeo de cada pasada sin
  cambiar el problema.

  | Caso, apagado | ω exacto | ω ±1, ±4, ±8 ulp | ω ±2 ulp |
  |---|---|---|---|
  | Presa 2 ×1 con la puerta | el defecto | el defecto | el bucle no para (2,3e-5 y 4,8e-5) y el rescate lo asienta |
  | Presa de Harr con presupuesto 1 | el defecto | el defecto | el defecto |

  - En la presa de Harr, el defecto es idéntico en las 9 corridas: un cambio de 9,52e-7, 120 pasadas
    y un nodo sin asentar.
  - Encendido, en las 9 el rescate la lleva al punto fijo del bucle solo: Anderson 5, la misma cara, a
    1,7e-6 m.
- **La rama que solo vería otra máquina se probó aquí también.** En la presa 2 con ω ±2 ulp, el
  apagado cumple las aserciones de la rama «el bucle falla». Los dos tests de «encendido» pasan, con el
  caudal en −0,46 %.

## 1. Qué cambia

Solo `tests/test_picard_loop_face_v1358.py`, con la decisión de la propietaria:
- **`TestSwitchedOffTheDefect`, nuevo.** La presa de Harr con presupuesto 1, apagada, para con la cara
  sin asentar, sin rescate y no convergida. Ahora la regla 7 (el interruptor mueve el número) la
  demuestra este caso, que no depende de la máquina.
- **El apagado de la puerta** pasa a llamarse
  `test_switched_off_it_is_never_published_settled_when_it_is_not`, y pide lo que vale en los dos
  regímenes:
  - si el bucle para, la corrida sale no convergida, sin rescate y sin caudal;
  - si no para, el rescate la asienta por la continuación y ningún nodo de la cara rompe la condición.
- **La cabecera** explica por qué, con esta medida.
- **Los dos tests de «encendido» de la puerta no cambian:** valen en los dos regímenes.

En el banco, `d356()` del verificador de la raíz usaba la misma presa 2 apagada para afirmar «reproduce
el defecto». Ahora el defecto se pide a Harr con presupuesto 1, y a la presa 2 apagada solo que no se
publique convergida con la cara sin asentar.

## 2. Tests

Uno más, 6537. El cambio está entero en `test_picard_loop_face_v1358.py`, que pasa de 8 a 9 casos
(unos 90 s).

## 3. Verificación

- **El archivo del test:** 9/9.
- **La rama que este equipo no recorre:** probada con ω ±2 ulp (`_auditoria/P6_0361/rama_bucle_falla.log`
  del banco). El apagado de la puerta va por «el bucle falla» y cumple sus aserciones; los dos de
  «encendido» pasan, con el caudal en −0,46 %.
- **Suite entera:** 6537/6537, unos 84 min.
  - Corrió a la vez que el verificador de cierres de la raíz: el reloj no es una medida.
  - Después solo se tocaron los README (el contador, 6536 → 6537) y este changelog. Se repitieron sus
    tests.
- **Banco:**
  - `verificar_cierres.py` de la raíz entero: 95 comprobaciones, 0 bajadas. Solo cambia el detalle de
    `d356`, como se esperaba.
  - `d356` sigue en CUBIERTO POR TEST: la presa 2 apagada (aquí el bucle para), Harr con presupuesto
    1 (apagado, el defecto; encendido, a 1,7e-6 m del bucle solo), el caso (b) y el (a).
  - Instantáneas de 0.1.361 de los dos bancos.

## 4. Lo que sigue abierto

- El fallo de segmentación al salir en Linux, que pone la CI en rojo con todos los tests pasados.
- D367 (P6): un camino del rescate que cruce pliegues no lisos.

## 5. Lo que no se ha probado

- Que el runner de 3.12 pase ahora: lo dirá la CI tras subir.
