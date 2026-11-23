# OGR Slip2D v0.1.485

**D374: entre las masas disjuntas de una superficie gana la admisible, como en `critical`.**
`_best_of_masses` elegía solo por el factor. Por eso una superficie publicaba su masa más baja aunque
los chequeos la rechazaran y otra masa del mismo círculo fuera admisible. Ahora las tres elecciones
—la crítica, la lista de las más críticas y la masa de una superficie— comparten una sola clave. En
el banco no se mueve ninguna crítica ni ningún círculo publicado.

## 0. Lo que se encontró

Ficha D374, abierta el 2026-10-29 con la auditoría del cómputo de 0.1.377 (sonda S3, §10). Paquete
P3. Censada sobre 0.1.483 con una herramienta nueva de la raíz del banco,
`_tools/censo_masas_d374.py` (fuera de git), con salidas en `_auditoria/D374_masas/`.

- **El prompt estaba desfasado en las líneas.** La regla estaba en `search.py:1815-1819` y la de
  `critical` en `:475-480`. El defecto seguía vigente. Además, el mismo bucle elige entre los
  **casos de capa débil**, no solo entre masas.
- **La criba.** De 207 tareas del banco (raíz 03–07 y el 02), 175 pasan la criba. En 91 la búsqueda
  propia produce superficies con más de una masa, y en 1 hay casos de capa débil (02_109).
- **El censo**, con un envoltorio que devuelve exactamente lo mismo que el original, sobre las 175:
  - 137 618 elecciones resueltas (9 899 494 de una sola masa, saltadas);
  - 27 762 con varias candidatas resueltas, y 9930 con varias válidas;
  - 1188 que se quedan con una inadmisible;
  - **34 con una alternativa admisible**, todas en **02_059 con Spencer**. Las rechaza el propio
    método, no un cribado: `admissibility_reason` está vacío.
- **Ninguna crítica se mueve.** La alternativa más baja del 059 es 0,83496, frente a una crítica de
  0,565634. Lo confirmó una corrida entera en serie del 059 con sus cinco métodos. Ningún círculo
  publicado está entre las 34.
- **El control positivo** es la rejilla de Ej_2 del test de validación. Reproduce la sonda S3:
  - 125 elecciones con varias válidas;
  - 351 inadmisibles elegidas;
  - **2 con alternativa admisible:** 3,0395 frente a 3,5401, y 7,2051 frente a 24,2101;
  - la crítica no cambia (1,1544).
- **De paso:** el círculo crítico de Ej_2 también tiene dos masas, pero una no es válida. Para el
  caso de una sola masa del test hubo que buscar otro círculo.
- **La revisión adversaria vio dos consecuencias que el censo no medía.**
  - *La ventana de factores [0,2; 100] de las búsquedas* se aplica a la masa ya elegida. Un círculo
    con una masa inadmisible a 1,5 y otra admisible por encima de 100 era válido (inadmisible) y
    ahora sale del recuento de válidas. Al revés, una masa inadmisible por debajo de 0,2 ya no tira
    el círculo si hay otra admisible.
  - *Con el objetivo Ky*, una masa admisible sin Ky gana a una inadmisible con Ky. Es lo que
    `critical` ya hacía entre superficies.

  Medido en el 059, el único modelo donde la regla muerde: corrida entera en serie con los cinco
  métodos, en 0.1.484 y en 0.1.485.
  - Válidas y no válidas, **iguales** en los cinco métodos (Spencer 373 y 90).
  - Críticas, **iguales**.
  - Solo cambia el recuento de inadmisibles de Spencer: **34 → 0**.

  Las alternativas admisibles vistas están entre 0,83 y 0,94, dentro de la ventana. No se cambia
  nada por esto.

## 1. Decisión de la propietaria (2026-11-23)

**A**: la misma regla que `critical`. Se descartó **B**, dejarlo documentado sin tocar el código.

## 2. Lo que cambia

- **`ogr_slip2d/search.py`:**
  - función nueva `criticality_key(result, score)`, que ordena: válida antes que no válida,
    admisible antes que rechazada, y después la puntuación;
  - la usan `SearchResult.critical`, `SearchResult.top_n` y `BaseSearch._best_of_masses`;
  - `critical` y `top_n` dan lo mismo que antes, desempates incluidos: `min` y `sorted` se quedan
    con el primero de los iguales, como antes;
  - en `_best_of_masses` un candidato no válido sigue sin reemplazar al que hay;
  - `_not_worse` (Sarma, ángulos optimizados) no se toca. Ordena igual para dos resultados válidos,
    pero con uno no válido diría otra cosa, y eso queda fuera de esta ficha.
- **`ogr_slip2d/probabilistic.py`:** tres comentarios decían que `_best_of_masses` se queda con «el
  menor factor». Ahora dicen «el menor admisible». Solo comentarios.
- **Versión** en los siete sitios.

## 3. Tests

`tests/test_best_of_masses_admissible_v1485.py`, 7 casos. El testigo es natural: el círculo
(33,333333; 92,894737; 42,958327) de la rejilla de Ej_2, con Spencer. Sus dos masas válidas son una
inadmisible a 3,0395 y una admisible a 3,5401.

- **Guarda:** el testigo tiene las dos masas, y la baja es inadmisible por el método.
- **La masa admisible gana.**
- **Con todas las masas inadmisibles** (marcadas a mano), gana la más baja.
- **Con todas las masas no válidas** (marcadas a mano), se queda la primera, como antes.
- **Un círculo de una sola masa** (20; 90; 55) no cambia.
- **La clave** ordena válida, admisible y puntuación, en ese orden.
- **`top_n(1)[0] is critical`** en una población mixta y en una sin admisibles.

**Discriminación, medida:** el archivo, copiado a un worktree de 69446c6 (0.1.484), da **2 fallos y
5 pasan**. Uno falla por comportamiento (3,0395 inadmisible) y otro porque no existe la función. Un
mutante que hace que `critical` ordene solo por puntuación hace fallar
`critical_is_the_first_of_top_n`.

Vecinos: `python tests/_runner.py search admissib m_alpha disjoint mass`, 296 de 296.

## 4. En el banco (fuera de git)

- `_tools/censo_masas_d374.py` de la raíz, nuevo: la criba, el censo y el control de §0.
- **`d374()` en el `verificar_cierres.py` de la raíz.** Comprueba:
  - en vivo, que el testigo de Ej_2 con Spencer publique la masa admisible (3,5401);
  - por AST, que `critical`, `top_n` y `_best_of_masses` usen `criticality_key`;
  - los dos censos archivados de 0.1.483 (34 elecciones en el 059, ninguna crítica movida);
  - la discriminación archivada (2 de 7 fallan en 0.1.484);
  - que el test exista.

  Sale **CUBIERTO POR TEST**.
- **Ciclo de cierre:**
  - instantánea `Evaluaciones/0.1.485` de la raíz;
  - D374 retirada al índice de CERRADOS, tachada en la cadena de P3 y podada de `PAQUETES`;
  - prompts regenerados y `auditoria_invariantes.py` con 0 ERROR;
  - la instantánea, de nuevo con `--forzar`.
- Los `resultados*.json` del 059 no se recalculan: no se mueve ninguna fila. En una corrida nueva,
  Spencer contaría 0 inadmisibles en lugar de 34.

## 5. D464 cerrada en el banco, sin versión (2026-11-23)

D464 nació en 0.1.484, de la sonda de D203. La rejilla de F de Corps 1, Corps 2 y Lowe-Karafiath
termina en 5,0 sin extensión perezosa, y una raíz por encima sale como `no_force_bracket`. Se midió
con 0.1.485 antes de tocar nada (`_tools/censo_rejilla_f_d464.py` y `_tools/plausibilidad_d464.py`
de la raíz del banco, `_auditoria/D464_rejilla_f/`).

- **El censo.** Con la rejilla extendida hasta 100 (solo cuando la de hoy no encuentra horquilla),
  en los 14 modelos del banco con la familia:
  - 38 551 superficies válidas más;
  - **ningún mínimo movido;**
  - **ningún círculo publicado movido.**
- **Las raíces nuevas no siempre son plausibles.** Comparadas con Spencer (1967) sobre las mismas
  dovelas:
  - en los modelos ordinarios (027, 051, 056) coinciden, con razón mediana 1,00, pero valen más de 5
    y no deciden nada;
  - en el talud sumergido del Apéndice G a embalse lleno son espurias: 123 círculos, mediana 3,0
    veces el factor de Spencer y hasta 9 veces; en 102 de ellos Spencer queda por debajo de 5, y el
    método las declara admisibles;
  - el testigo de D202 daría F1 = 9,77, donde Bishop y Spencer dan 1,85;
  - en el 096, el mínimo de Corps 1 bajaría a 1,3881 en (69; 124,67; 98,75), donde Bishop y Spencer
    dan 1,769: del lado inseguro.
- **Decisión de la propietaria: no extender.** La reserva 5,0 sin convergir es la respuesta
  honesta: la superficie sale inválida y dice por qué. Los testigos de D202 y D203 siguen valiendo.
  Sin cambio de código.
- **`d464()`** en el `verificar_cierres.py` de la raíz, **CIERRE DOCUMENTAL**. Comprueba que la
  rejilla sigue terminando en 5,0 sin extensión, que en vivo ese círculo del 096 sigue inválido con
  Corps 1 (Bishop, 1,7686) y que las medidas archivadas dicen lo citado. Hecho el ciclo de cierre:
  instantánea `Evaluaciones/0.1.485` de la raíz con `--forzar`, y `auditoria_invariantes.py` con
  0 ERROR. El banco está fuera de git: aquí solo la nota.

## 6. D193 cerrada en el banco, sin versión (2026-11-23)

D193 nació en 0.1.209, al cerrar D158. La exención plana de D152 acepta la rama de FUERZAS sobre un
plano sin esperar al empuje, porque ahí el factor no depende de él (Krahn 2003; EM 1110-2-1902,
SC-7a). Pero la admisibilidad (`thrust_is_admissible`, el signo de ΣE interior) se lee sobre el
empuje de esa pasada. En la cuña de `test_stall_pair_v1209` lo lee con el signo contrario al de su
punto fijo: margen −0,1195 en la pasada 48 y +0,4198 en la 1218. Con 0.1.485 se reproduce bit a bit.

- **El censo** (`_tools/exencion_plana_d193.py` de la raíz del banco,
  `_auditoria/D193_exencion_plana/`). Se corrieron enteras 54 tareas: todas las de búsqueda no
  circular de los manuales 02, 03, 06 y 07, el barrido de planos del 047 (el de `correr_47.py`, que
  es quien escribe su `resultados.json`), la cuña como control positivo y dos controles circulares,
  que dan 0 ramas planas. No se corrieron 156: 129 circulares, donde α cambia de dovela a dovela, y
  27 sin Spencer ni GLE.
  - de 8,8 millones de ramas, la exención dispara en **2500**, en el 047 y en tres búsquedas de
    trayectoria (078_3a, 085 activo y 085 pasivo);
  - **23** cambian de veredicto al asentar el empuje: 12 en el 047 y 11 en el 085, en los dos
    sentidos;
  - **355** no se asientan en 20 000 pasadas.
- **El A/B** (el prototipo de la opción (b), sin tocar el motor: la rama aceptada conserva su factor
  y lleva el empuje asentado):
  - en las tres búsquedas, los `datos` de `ejecutar_caso` salen idénticos clave a clave;
  - en el 047 no se mueve ningún factor, veredicto, mínimo ni crítica. Solo cambian los márgenes
    de 70 planos que ya eran inadmisibles;
  - la crítica inadmisible del 047 no es este mecanismo: sus 86 planos válidos salen por la reserva
    e inadmisibles, con la exención y sin ella.
- **Decisión de la propietaria: la (a).** Se declara con su denominador y el criterio pasa de «cero
  fuera de la cuña» a «cero en lo publicado». Sin cambio de código.
- **`d193()`** en el `verificar_cierres.py` de la raíz, **CIERRE DOCUMENTAL**. Comprueba en vivo
  que la cuña sigue dando el veredicto contrario a su punto fijo con el mismo factor, y que el censo
  archivado dice lo citado. Hecho el ciclo de cierre:
  - retirada la ficha, podado `PAQUETES` y tachada la cadena de P2;
  - prompts regenerados;
  - `auditoria_invariantes.py` con 0 ERROR en la raíz y en el 02;
  - instantánea `Evaluaciones/0.1.485` con `--forzar`.

  El banco está fuera de git: aquí solo la nota.

## 7. D201 cerrada en el banco, sin versión, y nace D465 (2026-11-23)

D201 nació en 0.1.210, al cerrar D172. En el círculo de Ej_2 piezométrico, la σ' propia de tres
métodos se separaba de las columnas publicadas: 4,86 kPa en Spencer, 1,26 en GLE y 4,29 en
Lowe-Karafiath, sin causa conocida. Con 0.1.485, Spencer y GLE dan lo mismo y Lowe-Karafiath da
3,23. Medido con `_tools/hueco_sigma_d201.py` del 02 (`_auditoria/D201_hueco_sigma/`). Antes hubo
que corregir la guarda de `censo_sigma_propia_d172.py`, que todavía exigía `ogr_core` dentro del
árbol (la spec 010 lo sacó).

- **La referencia para en tolerancia 0,005 y 50 iteraciones**, según su propio informe, y el
  fixture del test de Ej_2 usa lo mismo. Ninguno de los tres huecos es del motor:
  - **GLE es el λ donde paró la referencia.** Con el λ que publica (tan 36,2° = 0,7317), la rama
    de fuerzas de OGR da su factor a 4e-5 (0,680367 frente a 0,680394) y el hueco baja de 1,26 a
    0,26 kPa. OGR converge a λ = 0,7549, y su F queda a +0,39 % del publicado.
  - **En Spencer, el 4,86 es la parada en la dovela 25.** Entre 0,005 y el cálculo convergido, su
    σ' se mueve 5,40 kPa. La de la tabla publicada no cierra su propio equilibrio vertical por
    4,58 kPa. Convergido, el hueco es de 0,89 kPa y el factor está a −0,25 % del publicado (a
    0,005 estaba a +0,20 %; la ficha decía +0,10).
  - **Lowe-Karafiath bajó de 4,29 a 3,23 con D222** (0.1.223, `THETA_AT_BOUNDARY`; con el
    interruptor apagado sale otra vez 4,288). Hoy la inclinación de cada contacto coincide con la
    publicada a 0,033° o menos del 2 al 21. Se separa en los contactos 23-25, junto a la
    coronación (1,75° en el 24), y ahí vive el hueco. En esas dovelas la tabla publicada no cierra
    su equilibrio vertical por hasta 13 kPa.
- **Los márgenes.** El −120 de GLE y de Lowe-Karafiath pasa tanto a 0,005 como convergido, y las
  columnas publicadas también son positivas en las dovelas que se prueban (mínimos de 1,14 y
  0,12 kPa). El veredicto no depende del residuo.
- **Decisión de la propietaria:** CIERRE DOCUMENTAL, y la inclinación de Lowe-Karafiath en los
  contactos de la coronación sigue como **D465**, en P2, al final y sin versión. Sin cambio de
  código; los factores validados de Ej_2 y su fixture no se tocan.
- **`d201()`** en el `verificar_cierres.py` del 02, **CIERRE DOCUMENTAL**. Mide en vivo GLE al λ
  publicado, Spencer convergido, Lowe-Karafiath con su θ y el −120. Hecho el ciclo de cierre:
  - instantánea `Evaluaciones/0.1.485` del 02, y la de la raíz con `--forzar`;
  - retirada la ficha, abierta D465 y actualizada la cadena de P2 y `PAQUETES`;
  - prompts regenerados (D465 sale como FALTA: el generador no redacta);
  - `auditoria_invariantes.py` con 0 ERROR en la raíz y en el 02.

## 8. Los prompts largos que faltaban, y D234 cerrada sin versión (2026-11-24)

`PROMPTS_RESOLUCION.md` sacaba 48 de sus 55 prompts como «FALTA EL PROMPT LARGO». Antes de
escribir cada uno se volvió a medir su ficha en 0.1.485: una sonda con el motor o la herramienta
del banco que le toca. 47 siguen vivas y tienen ya su largo, con la medida de hoy y un `dNNN()` de
cierre que hoy falla. Varias fichas cambian al medirlas otra vez, y el prompt lo cuenta:

- **Persisten solo en parte:**
  - D138: la dispersión por semilla del 85 pasivo es hoy del 1,8 %, no del 9,5 %. Lo que sigue
    vivo es que la comparativa publica los mínimos de las búsquedas aleatorias sin su dispersión.
  - D441: la ayuda de la referencia sí barre una variable sin distribución. Lo que sigue vivo es
    la variable sin rango, que desaparece sin nota.
  - D448: el efecto es de +4,75 % a +8,13 %, no de +14 a +25 %, y no mueve nada publicado.
- **Mecanismos que la ficha no conocía:**
  - D254: la rama de momentos se acepta lejos de su punto fijo con la tolerancia 0,005; las dos
    hipótesis de la ficha no se sostienen.
  - D461: el salto sale de `_face_factor`, en la cara que separa cuñas con coeficientes distintos.
  - D449: un vértice a menos de `weld_tol` gana a un segmento que está a distancia cero, y por eso
    el resultado depende del orden en que se añaden los contactos.
  - D434: los 231 círculos son la columna de centros x = 120, no una fila.
- **El arreglo va a OGR-Core:** D235, D249, D431, D445, D455, el rótulo de D454 y parte de D429.

**D234 ya no pasaba.** Nació en 0.1.231: el recolector cíclico corre en el `QThread` del cálculo y
destruiría allí objetos Qt en ciclo. La resolvió `ogr_gui/gc_guard.py` (D310, 0.1.302) sin
nombrarla. El guardián retiene lo que encuentra *cualquier* recolección que empiece fuera del hilo
principal, no solo las de los hilos de un pool, y lo suelta `release()`, que la ventana llama
desde un `QTimer`.

Se re-midió en un `QThread` de verdad con `_tools/sonda_gc_qthread_d234.py` del 02:

- con el guardián, el diálogo en ciclo no se destruye en la recolección del hilo, queda retenido
  y se destruye tras `release()`;
- sin él (el control), se destruye en la recolección del hilo.

Decisión de la propietaria (2026-11-24): cerrarla. La comprobación es `d234()`, en el
`verificar_cierres.py` del 02. Mide en vivo, en un subproceso, y su veredicto es **CUBIERTO POR
TEST**: `tests/test_gc_guard_v1302.py`, que usa `threading.Thread`, más esta medida para el
`QThread`.

Ciclo de cierre hecho:

- retirada la ficha y tachada en la cadena de P1;
- podado `PAQUETES` y regenerados los prompts: 54 prompts, 54 largos y 0 FALTA;
- `auditoria_invariantes.py` a 0 ERROR en la raíz y en el 02;
- instantáneas `Evaluaciones/0.1.485` de los dos bancos con `--forzar`.

Sin cambio de código.
