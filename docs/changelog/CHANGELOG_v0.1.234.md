# OGR Slip2D v0.1.234

**D241: la cara del talud es la racha de tramos colineales con el más
empinado, así que un vértice sobre la cara ya no cambia la búsqueda.**
Cuando un contacto de materiales llega a la cara, el perfil del terreno
lleva un vértice ahí, y una cara recta se partía en trozos colineales. Las
cinco búsquedas que leen la cara tomaban uno solo de esos trozos. En el 52
del banco, la Path Search doblaba todos los caminos hacia arriba a 6 m del
pie y no generaba la superficie profunda que publica el manual.

Tercera versión de la tanda P5. La propietaria pidió el 2026-10-01 corregir
D241 antes de D92, que pasa a 0.1.235. El banco está fuera de git.

---

## 0. Lo que se encontró, y dónde

D241 salió al analizar D37. Las ocho filas no circulares del 52 (Zhu y Lee
2002, «Surface 4 - Noncircular, deep - Path search») estaban entre un 16 y
un 33 % por encima del círculo de la superficie 3, muy fuera del sesgo de
la cuerda.

La causa no era la resolución. `steepest_face_index` elige como cara el
tramo MÁS EMPINADO del perfil. La cara del 52, de (0, 0) a (30, 15), llega
partida en tres tramos colineales por los contactos que la cortan en (6, 3)
y (18, 9). Los tres empatan y el desempate se queda con (0, 0)-(6, 3), un
quinto del talud. Con esa cara, el `crest_target` de la Path Search quedaba
en x = 6,15, y el calendario de giro doblaba los caminos junto al pie. Solo
el 0,8 % de los caminos generados bajaba de y = −8, cuando la superficie
crítica llega a −8,9.

La prueba de que era un defecto es una invariancia. Quitar del perfil los
vértices colineales no cambia el terreno, y aun así cambiaba la búsqueda.

## 1. El motor

- **`failure_direction.slope_face(top, project) -> (lo, hi)`.** Toma el
  tramo más empinado, elegido y desempatado exactamente como antes, y lo
  extiende a todos los vecinos que lo continúan en línea recta
  (`_same_line`). La tolerancia es relativa, `COLLINEAR_SINE = 1e-6`, como
  la banda de empate de `steepest_face_index`:
  - un vértice a un nanómetro de la recta no parte la cara;
  - un cambio real de inclinación sí la separa;
  - un escalón vertical nunca se une a una cara inclinada.
- **Los cinco lectores la toman de ahí:**
  - la Path Search (ventana de iniciación y `crest_target`);
  - la Block Search sin objetos (su región implícita);
  - el Simulated Annealing (sus extremos fijos);
  - a través de `slope_frame`, la Slope Search y la Particle Swarm.
- **Interruptor de módulo** `failure_direction.FACE_IS_THE_COLLINEAR_RUN`,
  para que el banco pueda reconstruir el motor anterior y atribuir un
  cambio. El motor nunca lo apaga.
- **Lo que NO cambia:** el `crest_target`, que es una heurística propia sin
  equivalente en la referencia. D241 proponía tres arreglos y se aplica el
  mínimo: restaurar la invariancia sin tocar la heurística.

## 2. Tests

**`tests/test_slope_face_collinear_v1234.py`**, 15 casos:

- **La racha colineal:**
  - una cara partida se lee entera;
  - un recodo real, no;
  - un vértice a un nanómetro de la recta, sí;
  - un escalón vertical nunca se une a la cara;
  - el desempate entre dos caras iguales no colineales sigue igual;
  - con el interruptor apagado, la cara es un solo tramo.
- **La invariancia, en los cinco lectores.** El mismo talud con y sin dos
  vértices colineales en la cara da los mismos intentos, las mismas
  evaluaciones, la misma validez y factores iguales a 1e-11. No se exige
  igualdad bit a bit: al interpolar el terreno sobre un tramo partido, el
  redondeo difiere en los últimos bits (medido: hasta 7e-14 relativo). La
  misma comparación con el interruptor apagado falla en al menos tres de
  las cinco, así que el test no puede pasar por construcción.
- **El ancla externa**, Zhu y Lee (2002): el 52 seco, reconstruido en el
  test campo a campo e idéntico al `.ogr` del banco.

  | | Path Search Bishop, 1000 superficies | frente al manual (1,624) |
  |---|---|---|
  | cara entera | **1,6432** | +1,2 % |
  | cara partida (interruptor apagado) | 2,1395 | +31,7 % |

  Es también la prueba de la regla 7: el interruptor mueve el número.
- **Discriminación** contra `git archive` 661dd71 (0.1.233): **15 de 15
  fallan**. Seis por comportamiento: las cinco búsquedas cambian con el
  vértice, y el ancla da 2,1395. Nueve por símbolo.

## 3. El banco

- **Censo de los lectores de la cara en todos los manuales:** 44 modelos
  (35 Path y 9 Particle Swarm). Cambian de cara 3, los tres Path: 015, 052
  seco y 052 húmedo. En los otros 41, la cara, el pie, la coronación, la
  ventana y el `crest_target` son idénticos con el interruptor encendido y
  apagado. Como esos son los únicos datos de entrada que el arreglo puede
  tocar, sus búsquedas son las mismas por construcción
  (`_auditoria/P5_0234/censo_lectores_de_la_cara.json`).
- **Los tres re-corridos con `correr_no_circular.py 15 52 --forzar`:**

  | 52, superficie 4 | antes (búsqueda / optimizado) | ahora | manual |
  |---|---|---|---|
  | seco · Bishop | 2,1395 / 2,0132 | **1,6068** / 1,5814 | 1,624 |
  | seco · GLE | 2,1838 / 2,0567 | **1,7930** / 1,7355 | 1,776 |
  | seco · Spencer | 2,2515 / 2,0688 | **1,7901** / 1,7423 | 1,796 |
  | húmedo · Bishop | 1,6228 / 1,4709 | **1,0664** / 1,0379 | 1,073 |
  | húmedo · GLE | 1,7035 / 1,5491 | **1,1640** / 1,1267 | 1,162 |
  | húmedo · Spencer | 1,7727 / 1,5752 | **1,1569** / 1,1260 | 1,175 |

  La búsqueda queda entre −1,5 y +1,0 % del manual. El optimizado baja un
  2–4 % más. Los intentos pasan de unos 14 000 a unos 6850: la mitad de lo
  que se generaba era desperdicio.
- **El 15, con un efecto mixto que se reporta (regla 6).** A/B en el mismo
  motor, interruptor apagado frente a encendido; el apagado reproduce el
  archivo de 0.1.185 al dígito:
  - la búsqueda baja en los tres métodos (Spencer 0,4563 → 0,4396);
  - el optimizado de Spencer mejora (0,4282 → 0,4253, frente a 0,414);
  - el de Janbu sube (simplificado 0,3935 → 0,4024, frente a 0,396), y esa
    fila pasa de OK a REVISAR.

  La primera hipótesis era la dispersión de semilla (D138), y no se
  sostiene. Cinco semillas por lado con el flujo del banco:

  | optimizado | cara partida | cara entera | manual |
  |---|---|---|---|
  | Janbu simplificado | 0,3935–0,4022 | 0,4021–0,4277 | 0,396 |
  | Janbu corregido | 0,4120–0,4198 | 0,4296–0,4610 | 0,418 |
  | Spencer | 0,4198–0,4474 | 0,4201–0,4297 | 0,414 |

  En Janbu los rangos apenas se tocan: es un desplazamiento. La causa la da
  el censo de salidas. El 15 tiene una capa débil de 8 m bajo una cuña
  resistente que termina en x = 72. La familia que el optimizador lleva a
  0,394 es la de los caminos largos y rectos por la capa débil, que salen
  más allá de x = 68 sin cortar la cuña. Con la cara partida, `crest_target`
  estaba en 24,15 y el calendario de giro dejaba los caminos rectos desde
  ahí: el 15,4 % de las válidas salía entre 68 y 96, con mínimo 0,4476.
  Con la cara entera, `crest_target` está en 48,75 y los caminos giran
  hasta 55° en la coronación: sale por ahí el 3,5 %, y ninguno baja de
  0,93.

  El optimizador del banco deja fijos los extremos
  (`move_endpoints=False`), así que hereda esa salida.
  - D241 no lo causa: la cara partida acertaba por accidente, por un
    contacto que aflora en (24, 19).
  - Lo que sí decide la familia es la heurística propia `crest_target`.
    Queda reportada como **D245**.
  - Liberar los extremos no sirve para comprobarlo: el optimizador los
    entierra, y eso es **D244**.
- **D37.** Las siete filas del 52 que se reenviaban a D241 salen de C5:
  quedan 19 filas, todas con razón. `razones_d37.py` las quita de su tabla,
  y `d37()` sigue sosteniéndose.
- **D241 cerrada.** `d241()` sale CUBIERTO POR TEST: mide en vivo la cara
  del 52 y la invariancia, y comprueba los resultados del 52, el censo y la
  discriminación.
- **El interruptor** queda registrado en `INTERRUPTORES`, que tiene ahora
  32.

## 4. Lo que se reporta y NO se corrige

- **D244 (nueva, P5): una poligonal con un extremo dentro del suelo se
  rebana tal cual.** La primera dovela empieza con una cara vertical, del
  extremo enterrado al terreno, sin resistencia ni empuje; la superficie
  sale válida y nadie lo dice. En el 15, la crítica de Janbu con los
  extremos bajados 5 m y 1 m pasa de 0,4294 a 0,3929 (−8,5 %, por debajo
  del manual). El optimizador con `move_endpoints=True` mueve los extremos
  en el plano y llega a 0,29–0,35, cuando todo lo publicado para este
  talud está entre 0,39 y 0,44.

  La referencia lleva los extremos al contorno exterior al dibujar («snap
  to the nearest point on the External Boundary») y da el error −101 a una
  superficie con menos de dos cortes con el talud. Hoy se llega por dos
  puertas: los extremos libres (solo por script) y `surface_evaluate` con
  una poligonal (API y MCP). Ninguna corrida del banco las usa.
- **D245 (nueva, P5): la Path Search decide su familia con
  `crest_target`.** Es la heurística propia de la sección anterior, la que
  mueve la fila del 15. Cambiarla mueve, en principio, las 35 corridas
  Path del banco, así que decide la propietaria.
- **D236, ampliada.** Las ocho filas de la superficie 4 del 52 siguen
  rotuladas «MECANISMO NO REPRODUCIDO» aunque ahora quedan entre −4,2 y
  +0,8 % del manual. El `mecanismo: restringido` del 52 describe las
  superficies 1 y 2 («must pass through toe of slope»), pero la
  comparativa lo aplica a todas las filas del problema. Es de la misma
  clase que D236: un dato de un escenario rotula las filas de otro.
- En el 52 húmedo, Spencer optimizado queda un 4,2 % por debajo del
  manual: el optimizador baja más que la superficie publicada.

## 5. Verificación

- **Suite entera:** 5253/5253, en unos 42 min, con medidas del banco
  corriendo a la vez (el reloj no es una medida).
- **Discriminación:** el test nuevo, copiado en un `git archive` de 661dd71
  y corrido con el runner de ese árbol, falla 15 de 15 casos.
- **Banco:**
  - `--seco` completo: 206 cierres, el único cambio es D241 (nueva,
    CUBIERTO POR TEST) y no baja ninguno;
  - D241 retirada a `Evaluaciones/0.1.234`;
  - auditorías de invariantes en 0 ERROR, en el 02 y en la raíz;
  - instantánea congelada antes y después de retirar.

**Qué falta por probar:**
- **Las búsquedas de los 41 lectores que no cambian de cara no se han
  re-corrido.** Que no se mueven se deduce de que sus datos de entrada
  (cara, pie, coronación, ventana, `crest_target`) son idénticos con el
  interruptor encendido y apagado.
- **Las tres opciones de D245 están sin medir:** el giro aleatorio, el
  `crest_target` sorteado por camino y la declaración.
- **El efecto de D244 en modelos de usuario:** el banco no tiene
  ninguno.
