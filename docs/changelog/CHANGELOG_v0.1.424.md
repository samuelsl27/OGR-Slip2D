# OGR Slip2D v0.1.424

**Un nivel del barrido de desembalse da el mismo factor de seguridad sea cual sea el resto de niveles que se barran
(D373).** El barrido configurado (el de la ventana, el API y el servidor MCP) construye una búsqueda **nueva para cada
nivel**. Antes reutilizaba una por método en todos los niveles, y la búsqueda Slope y el enjambre arrastraban su
generador aleatorio de un nivel al siguiente.

Es la segunda de la tanda P5c. La ficha sale de la sonda S2 de la auditoría del cómputo (`AUDITORIA_COMPUTO_v0.1.377.md`
§10, A2). **Decisión de la propietaria (2026-11-04): opción A, una búsqueda nueva por nivel**, local al barrido, como ya
hace Overall Slope por muestra.

**Cambian números:** los barridos con Slope o con el enjambre, en todos los niveles menos el primero. Los barridos con
rejilla, Block, Path o Simulated Annealing no cambian, porque esas búsquedas ya se siembran en cada corrida (o no
sortean). Nada que no sea un barrido cambia.

## 0. Lo que se encontró

- **El mecanismo.**
  - `run_configured_drawdown_sweep` construía una búsqueda por método y le pasaba a `run_drawdown_sweep` el
    `searches.__getitem__` como fábrica. Así, cada nivel volvía a correr **el mismo objeto**.
  - `SlopeSearch` y `ParticleSwarmSearch` crean `self.rng` en `__init__`, y `run` no lo reinicia: solo pone a cero los
    contadores de la corrida. Cada nivel empezaba con el estado aleatorio que había dejado el anterior.
  - Block, Path y Simulated Annealing crean su generador dentro de `_run` con su semilla, y la rejilla no sortea.
- **Medido en la auditoría** (S2, 0.1.377): el talud de Morgenstern con Slope sembrada (300 superficies, semilla
  12345, 18 dovelas).
  - El desembalse total daba 1,20381 en un barrido de 2 niveles y 1,20561 en uno de 4.
  - El nivel 0, que es el mismo estado del agua, daba 1,20249 y 1,20614.
  - La rejilla daba lo mismo en los dos barridos.
- **Medido aquí, en el árbol anterior** (el test nuevo, con 20 superficies, un enjambre de 8 × 5 y 10 dovelas):
  - Slope: 1,22643 frente a 1,21223 en el desembalse total;
  - el enjambre: 1,36863 frente a 1,44340.
  - Además, ningún nivel después del primero coincidía con la misma búsqueda corrida sola en ese nivel.
- **A quién afectaba:** a todo barrido configurado con Slope o con el enjambre, desde la ventana, el API o el servidor
  MCP. K21, el caso del banco de pruebas del cómputo, llama a `run_drawdown_sweep` por debajo de la puerta, con su
  propia fábrica de rejilla, y no pasaba por aquí.

## 1. Qué cambia

- **`ogr_slip2d/analysis_runner.py`, `run_configured_drawdown_sweep`:**
  - la fábrica que recibe `run_drawdown_sweep` construye con `build_search` en cada llamada, con el mismo
    `checkpoint` de Cancelar (D362);
  - las búsquedas que se construyen antes del primer nivel se quedan, y solo sirven para comprobarlas. Un método sin
    búsqueda se rechaza con `SEARCH_NOT_BUILT`, y un rechazo del envoltorio de desembalse sale antes del barrido y no
    como un nivel perdido en silencio;
  - el porqué, con la medida, va en un comentario.
- **`tests/test_drawdown_sweep_seed_v1424.py`,** nuevo, con 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_drawdown_sweep_seed_v1424.py`,** 6 tests, unos 12 s más el arranque. La cabecera explica el coste: son 11
  búsquedas por tipo, y el paseo de refinamiento de Slope no tiene ajuste.
  - **La ley:** cada nivel del barrido es igual, bit a bit, a la misma búsqueda construida de nuevo y corrida sola en ese
    nivel (`build_search(...).run(project_at_level(...))`). Se comprueba con Slope, con el enjambre y con la rejilla.
  - **El síntoma:** el desembalse total da el mismo factor con 2 niveles y con 4, con Slope, con el enjambre y con la
    rejilla de control. Se compara el desembalse total, no el «0»: con 4 niveles, el más bajo es −1,4e-14.
  - Optimize va apagado en el test. Para el enjambre está encendido por defecto, y aquí era el 95 % de su coste (3267
    evaluaciones del paseo por nivel). Su paseo se siembra aparte y no lee el generador del enjambre.
- **Discriminación.** En el árbol anterior (worktree de 4dfcd0b, sin el buscador editable) fallan los 4 casos de Slope
  y del enjambre, por comportamiento, y pasan los 2 de la rejilla.
- **Vecinos:** `test_drawdown_sweep_v170`, `test_groundwater_ops_v1200` (la fábrica «a mano» con `build_search` por
  llamada sigue siendo igual a la puerta), `test_cancel_v1366`, `test_task_notes_v1363`, el censo de
  `test_seepage_run_notes_v1352` y el `@pooled` de `test_shared_pool_v1396`: 126 de 126.
- **Suite entera** con `--jobs 4`: 7119 en verde, 1 saltado, 0 fallos, sin fugas ni tramos muertos.
- **Banco:** no tiene ningún caso de barrido, así que no hay filas que mover.
- **`d373()`**, nueva en el `verificar_cierres.py` de la raíz, con el caso de S2 en vivo (Morgenstern, Slope sembrada,
  300 superficies, semilla 12345, 18 dovelas): **CUBIERTO POR TEST**.
  - El desembalse total da 1,2031747334653147 con 2 niveles y con 4.
  - El nivel 100, el primero, da 2,5844834982822724 en los dos.
  - Discriminada con el motor de 0.1.422: **SIGUE ABIERTO**, con 1,2038100585910254 frente a 1,2056135118140106 en el
    desembalse total. Son los números de S2, al dígito.
  - El valor nuevo es el que da una búsqueda Slope recién sembrada en ese nivel. Queda por debajo de los dos viejos, que
    eran el desembalse total buscado con el generador gastado por los niveles anteriores.
- **El VC de la raíz entero:** 135 comprobaciones, todas cierran, y 0 bajadas. **El del 02 en seco:** 242 de 242
  iguales, por la primera línea de cada ficha.
- **El cierre del banco:** `Evaluaciones/0.1.424` de la raíz, D373 retirada al índice, podada de `PAQUETES` y tachada en
  la cadena de P5. `auditoria_invariantes.py` da 0 ERROR en la raíz y en el 02.
