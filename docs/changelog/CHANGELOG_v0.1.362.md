# OGR Slip2D v0.1.362

**El rescate sigue el camino de soluciones a través de los pliegues no lisos (D367). La presa 2 del
problema 9 converge, con los ajustes de la puerta, en las dos mallas finas que fallaban: 3691 y
3886 T3.**

D366 dejó medido el porqué. La continuación del rescate, que eleva cada kr a una potencia t de 0 a 1,
se para en t ≈ 0,62 en un pliegue no liso:
- el camino de soluciones da la vuelta en el quiebro de 9,8 kPa, donde la curva del dren cae a su
  suelo `kr_min`;
- el determinante del jacobiano cambia de signo saltando el quiebro, no pasando por cero, así que
  ningún valor singular de un lado lo ve;
- la continuación en t no puede pasar de ahí, busque como busque el paso.

D366 se cerró documentado y abrió D367 para un camino que siguiera el camino de soluciones a través
del pliegue.

Desde esta versión, cuando la continuación se rinde por el paso mínimo, el rescate sigue el camino
desde su último estado aceptado. Lo recorre por su longitud de arco, tramo a tramo por los quiebros
de las curvas (`_piecewise_path`, con la orientación y los métodos a trozos de Allgower & Georg
1990), y llega a t = 1.

## 0. Lo que se encontró

La medida está en `_auditoria/P6_0362/D367_medida.md` del banco. El motor no se tocó para medir: se
usaron las copias literales de D366 (su C0, al bit con el motor en las dos mallas), con los
candidatos en la posición «reanudar».

- **La fuente.**
  - Allgower & Georg (1990), *Introduction to Numerical Continuation Methods*, aportado por la
    propietaria y leído antes de escribir nada.
  - Su orientación del camino, det [H′; τ*] > 0 constante a lo largo de él (2.1.7), da por Cramer
    sign(τ_t) = sign(det J). En t = 0 el problema es lineal (J = K0, definida positiva) y el camino
    sale hacia t > 0. Donde det J < 0 sigue con t decreciente: la dirección se lee del signo, sin
    memoria de la tangente anterior.
  - Lo demás sale del mismo libro:
    - el seguimiento predictor-corrector de un mapa suave a trozos «con pequeñas actualizaciones
      cada vez que se entra en una pieza nueva» (§11.7);
    - el paso hasta la faceta por una prueba de razón mínima (14.1.2);
    - el cruce transversal de cada faceta y la orientación que se conserva al cruzarla
      (14.1.11–14.2.4).
- **D366 había visto un pliegue; hay cuatro, y el camino es una Z.**
  - En las dos mallas hay 3 pliegues no lisos, todos en el quiebro de 9,8 kPa del dren, y 1 liso.
  - El camino avanza hasta t ≈ 0,93 (3886) o 0,97 (3691), retrocede hasta 0,67 o 0,66 y vuelve a
    avanzar hasta 1. Entre esos dos t, el problema intermedio tiene tres soluciones.
  - Aunque la continuación hubiera cruzado el primer pliegue, se habría parado en el segundo.
- **El pliegue de D366 es el primero.** Desde el estado aceptado anterior a t* (t = 0,609, rama
  seca), el camino llega a t = 0,6175251 con el elemento 3349, el que D366 encontró clavado, en el
  quiebro, y det pasa de +1 a −1. D366 lo había situado entre 0,6172 y 0,6177.
- **En 3886, Newton ya había saltado de rama.** El estado donde se rinde la continuación (t* =
  0,6171875) está en la rama húmeda, con det −1. Desde ahí el camino sigue hacia atrás en t, y eso
  es lo que la continuación no podía hacer.
- **No es una lotería de arranques.**
  - El camino llega al mismo punto en las dos formas algebraicamente iguales (el caudal coincide a
    1e-13) y desde t*, el estado anterior y t = 0, con los mismos pliegues en los mismos t.
  - Ese punto es la solución que ya se conocía: a 7,8e-7 m de la referencia del banco en 3886 y a
    3,1e-7 m de la de Anderson en 3691, con la misma cara. El caudal queda a −1,44 % y −1,39 % del
    publicado (4,23e-6 m³/(min m), Chapuis et al. 2001).
  - D366 había encontrado esa solución con 2 y 4 de 24 combinaciones de arranque y ninguna común.
- **Lo que cuesta.**
  - Desde t*, 1242 Newton en 3886 y 1313 en 3691 (1433 con la tolerancia del banco), unos 30 s.
  - Son unos 720 cruces de quiebro, casi todos del núcleo: unos 300 pares de elemento y quiebro,
    casi todos cruzados tres veces por la Z.
  - A la continuación le quedan 734 y 749 Newton. Con ese presupuesto, la corrida entera se paraba
    en t ≈ 0,71 y salía «failed», como hoy; ni un presupuesto propio de 1000 bastaba.
  - La propietaria decidió que el camino no tenga presupuesto de Newton propio. Termina como un
    algoritmo PL: al llegar a t = 1, por paso mínimo, si la tangente no entra en la celda nueva o si
    t baja de 0. Como el camino sale del problema lineal de t = 0, regular y de solución única, no
    puede volver a t = 0 y, acotado, llega a t = 1.
- **El otro candidato no sirve.** El pseudo-transitorio con la escala física del transitorio no
  converge con ningún δ₀ en once décadas, en ninguna malla y con D fija o al día: 0 de 44. Es la
  masa concentrada por la capacidad (Celia et al. 1990), en lugar de la diag|J| de D366. Con la
  escala física, δ₀ no deja de importar: no queda ninguna década que converja.
- **Dos fallos del prototipo, encontrados al medir.** Ninguno cambia las corridas desde t* ni desde
  el estado anterior.
  - El paso mínimo se disparaba con un rechazo en un paso recortado por una faceta, que puede ser
    diminuto. Ahora solo lo mide un paso de arco.
  - Desde t = 0, el paso mínimo relativo a ds0 (139) valía 0,56 y se paraba en el pliegue liso;
    ahora se usa el de la posición «reanudar».

## 1. Lo que cambia

- **`HydraulicProperties.log_kr_pieces()`** (`ogr_core/hydraulic`): los tramos de una curva de
  usuario, en los que ln kr es lineal en la succión. Los quiebros son los puntos de la tabla y los
  cruces con el suelo y el techo, solo donde cambia la pendiente. Con los demás modelos devuelve None.
- **`_PiecewiseSystem`** (`ogr_fem2d/solvers/seepage.py`): el residuo de `_NewtonSystem` celda a
  celda, kr^t = exp(t (a + b s)), con su jacobiano y su derivada en t.
- **`UnsaturatedSeepageSolver._piecewise_path`**: el camino a trozos, con el predictor tangente, el
  corrector orlado de Keller (1977), la prueba de razón mínima, el cruce de faceta con la comprobación
  de que la tangente entra y el cierre de la continuación en t = 1.
- **`_continuation_newton`**, al rendirse por el paso mínimo, devuelve además `stopped` y `last`.
  No cambia ningún número.
- **`_rescue`** lo llama justo detrás de la continuación y lo publica como segmento
  `continuation-piecewise`. El interruptor es `RESCUE_PIECEWISE_PATH`; apagado, 0.1.361.
- **Con los otros modelos.** Si la continuación se rinde y algún material no tiene curva de usuario,
  el camino no corre: la nota `rescue_piecewise` vale «not applicable» y el aviso lo dice, con código
  propio (`seepage.picard_rescue_piecewise_na`) y traducción.
- **La ventana** rotula el segmento nuevo en la historia de iteraciones: «Rescate: continuación
  seguida a través de los quiebros de las curvas».
- **Docstrings:** `_rescue` lleva la sección nueva, con todo lo que comprueban `d365()` y `d366()`, y
  `_continuation_newton` explica qué devuelve al rendirse.

## 2. Lo que no se mueve

- **Banco,** 255 corridas permanentes no saturadas (ω de 0,2 a 0,8), prototipo contra motor: 252 al
  bit. Las otras 3 son las que el camino resuelve, la ×4 de la presa 2 con ω 0,2, 0,4 y 0,8. No son
  tres aciertos independientes: la continuación no depende de ω.
- **Las tres mallas de la presa 2 que convergían con la puerta** (1921, 2901 y 4095 T3): al bit.
- **Los 115 tests que llegan a `_rescue`,** con el prototipo instalado: en verde, y el camino nuevo
  no corre en ninguno.
- **Motor contra prototipo:** la corrida entera de la presa 2 con la puerta sale al bit en 3691 y
  3886 T3 (cargas, convergencia, iteraciones, cara y notas enteras). Por eso lo medido con el
  prototipo, incluido el barrido del banco, vale para el motor (`embudo_d367_<obj>_motor0362.json`).
- **A/B árbol contra árbol** (`P6_0356/ab_arbol.py`, 0.1.361 contra 0.1.362, cada árbol en su
  proceso): 73 filas (el 05 entero en ×1 y ×4, el 02-010, el 02-038 y la presa del 102 permanente
  y transitoria), 0 distintas y ninguna clave de notas nueva.

## 3. Verificación

- **Primera suite: 6548 de 6549.** Falló `test_seepage_run_notes_v1352`, que exige una muestra de cada
  código de los catálogos de notas: el código nuevo no la tenía. Sus muestras, `_V1351`, son las
  frases que escribía 0.1.351, así que la nueva va en una lista aparte, `_LATER`, que cuenta para la
  cobertura y se comprueba en inglés y en castellano.
- **Verificador de cierres de la raíz, entero:** 96 comprobaciones, 0 bajadas.
  - `d367()` es nueva y da CUBIERTO POR TEST. Corre en vivo la presa 2 con la puerta en 3691 y 3886
    T3, con el modelo del propio banco: las dos convergen por `continuation-piecewise`, con la cara de
    la solución conocida, a 3,1e-7 y 7,8e-7 m de ella y con el caudal a −1,39 % y −1,44 %. Además
    comprueba la medida archivada y el test.
  - El único detalle que cambia es el de D335: el censo de códigos pasa de 425 a 426, que es el
    nuevo, con su castellano.
- **El cierre en el banco:**
  - D367 retirada, con su sección en `Evaluaciones/0.1.362`;
  - P6 queda vacío;
  - `comprobar_citas_prompts.py` da las mismas 19 citas con problema que en 0.1.357;
  - `auditoria_invariantes.py`: 0 ERROR en la raíz y en el 02.
- **Segunda suite, entera y sin argumentos: 6549 de 6549.** Son 12 tests nuevos sobre los 6537 de
  0.1.361; los README dicen 6549.
- **Verificador de cierres del 02 en seco:** los 242 veredictos, iguales a los guardados.
- **Instantáneas `Evaluaciones/0.1.362`,** forzadas tras el cierre: 979 archivos en la raíz y 3284 en
  el 02, comprobadas byte a byte.

## 4. Tests

`tests/test_rescue_fold_v1362.py`, 12 tests, unos 3 min:
- **identidades:** los tramos reproducen la curva, y los quiebros del dren son 6,9 y 9,8 kPa; el
  residuo de la celda es el del motor; el signo de det J de la LU es el de `slogdet`; en t = 0 el
  camino sale hacia t > 0;
- **la presa 2 en 3691 y 3886 T3:** la continuación se rinde por el paso mínimo y el camino converge,
  con la cara de un nodo asentada y el caudal a menos del 3 % del publicado (Chapuis et al. 2001; es
  el criterio de D367);
- **regla 7:** el interruptor mueve el número. Apagado, el rescate falla como en 0.1.361; encendido,
  converge por el camino;
- **con un modelo de Gardner,** el camino no corre, y la nota y el aviso lo dicen.
