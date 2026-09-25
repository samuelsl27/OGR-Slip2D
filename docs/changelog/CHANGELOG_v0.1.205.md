# OGR Slip2D v0.1.205

**La CI de GitHub vuelve a verde.** El trabajo de tests fallaba desde, al
menos, v0.1.184, y nadie lo veía: la suite pasa en la máquina de desarrollo
(Windows, Python 3.14) y fallaba en la de GitHub (Linux, Python 3.11–3.13).

Ninguno de los fallos era un defecto del programa. Eran tres causas:

- las dos primeras ya estaban en la corrida de v0.1.192 (6 fallos de 4215);
- la corrida de v0.1.204 añadió la tercera, solo en 3.13 (§3).

## 1. Cinco tests exigían el último bit de un double

Son todos del solver de λ de Spencer/GLE (`test_lambda_closure_v1180` y
`test_lambda_floor_v1184`). Fijaban con `==` números medidos en una sola
plataforma:

| Test | Windows / 3.14 | Linux / 3.11–3.13 |
|---|---|---|
| factor de la salida que no cierra | 0,5559372612135**651** | 0,5559372612135**633** |
| factor de la raíz que sí cierra | 0,5592600533686**025** | 0,5592600533686**019** |
| doubles de λ que toman el valor prematuro | una parte de los 13 (el resto, el atractor) | los 13 |
| resoluciones que ahorra GLE con presupuesto 50 | 3 | 4 |
| resoluciones que ahorra GLE con presupuesto 200 | 153 | 154 |

- **Los dos factores** difieren en 2e-15: los últimos bits de un double, que
  cambian con la aritmética de la plataforma, no con el motor. Esos casos
  vigilan que un cambio en lo que una salida *dice* no mueva lo que *vale*.
  Ahora comparan con una tolerancia relativa de 1e-12; un movimiento real
  estaría muchos órdenes por encima.
- **Cuántos de 13 doubles adyacentes van por cada lado** es un fenómeno de un
  bit. El test fijaba el reparto. Ahora conserva aquello en lo que se apoya
  la refutación de D146, que se cumple en las dos plataformas:
  - con la aceptación de D145 apagada aparece el valor prematuro;
  - se admite antes que el atractor con la aceptación que se publica;
  - no aparece ningún otro valor.
- **Dónde se colapsa la horquilla sobre doubles adyacentes** también se
  decide en el último bit, y con ello cuántas vueltas quedan en el suelo (3
  o 4). La ley exacta se cumple en las dos plataformas: 153 − 3 =
  154 − 4 = **150**, es decir, el presupuesto más allá del suelo se ahorra
  entero.
  - Esa ley es ahora lo que se fija.
  - Al recuento solo se le pide que sean unas pocas vueltas (entre 1 y 5),
    nunca ninguna.

## 2. El `pytest` simulado no tenía `skip`

`test_support_failure_v1161::test_the_fifteen_sheets_give_what_they_gave`
necesita el banco de verificación, que vive fuera de git. En GitHub
intentaba saltarse con `pytest.skip`, y el runner del proyecto, que trae su
propio `pytest`, no lo tenía: fallaba con `AttributeError`.

- **El runner gana `pytest.skip`** como tercer resultado, contado aparte:
  - escribe `○ nombre — skipped: motivo`;
  - la línea de totales añade `Skipped: N` cuando hay saltados;
  - una corrida sin saltados escribe exactamente lo mismo que antes.
- **`Skipped` es `BaseException`**, como el de pytest, para que el
  `except Exception` de un test no pueda tragárselo.
- **Un salto no es un aprobado.** Hasta ahora la convención del resto de la
  suite era que un test al que le falta algo hace `return`, y eso cuenta como
  pasado. El runner ahora distingue los dos casos.

## 3. Una cancelación sorprendida a medio morir (solo en Python 3.13)

En la corrida de v0.1.204,
`test_api_jobs_v1194::test_cancel_kills_the_worker_and_everything_it_started`
falló en 3.13 con `orphaned processes [3033]`. En 3.11 y 3.12 pasó, en la
misma corrida.

- **Qué hace la cancelación en POSIX.** Manda `SIGKILL` a todo el grupo de
  procesos del trabajo y espera al trabajador principal, no a los procesos de
  su pool.
- **La entrega de `SIGKILL` es asíncrona.** Un proceso condenado puede
  seguir apareciendo vivo unos milisegundos. El test miraba en ese mismo
  instante, y en una máquina de CI cargada cazó uno.
- **Es una carrera, no un huérfano.** Un huérfano de verdad sería un proceso
  fuera del grupo: nadie le manda la señal y no muere nunca.

El test da ahora a los condenados hasta 5 s para terminar de morir, y sigue
fallando si alguno queda vivo. El código no cambia.

## Tests

`tests/test_runner_exit_v1203.py` cubre el resultado nuevo:

- un salto sale como «skipped», con su motivo;
- el `except Exception` de un test no se lo traga;
- los totales lo nombran.

Una trampa medida al escribirlo: el caso que lanzaba el salto con
`import pytest` salía él mismo como saltado. Ese `pytest` es el del runner
que ejecuta el archivo; su `Skipped` es otra clase y se le escapaba a él.
Los casos usan ahora el `pytest` de la copia que se prueba.

**Verificación:** la suite entera, sin filtros, pasa **4545 de 4545** en Windows con Python 3.14. En la CI de GitHub (Linux, Python 3.11, 3.12 y 3.13), lo dice la corrida de este mismo commit.
