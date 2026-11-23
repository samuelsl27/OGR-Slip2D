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
