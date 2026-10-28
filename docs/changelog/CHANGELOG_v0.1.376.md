# OGR Slip2D v0.1.376

**Publicar una versión pasa a pedir la suite entera con `--jobs 4`, y la corrida en serie una vez cada
100 commits; el runner lleva la cuenta y avisa cuando toca.** Para el desarrollo, `--fast` deja fuera
los 42 archivos lentos de `tests/_slow.txt` (737 de los 6708 tests), y `--fast --jobs 4` tarda
**12,7 min** frente a los 34,6 de la suite entera. Es la etapa 4 del plan de la auditoría de la
suite (`docs/audits/AUDITORIA_SUITE_v0.1.372.md`), con las decisiones de la propietaria. **Ningún módulo
del programa cambia**, salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **La decisión de la propietaria:** «adoptamos jobs 4, pero conviene cada 100 commits correr todos en
  serie para detectar posibles fallos».
  - La serie es la única corrida que mantiene la suite entera en un proceso. El aborto de v0.1.302 (D310)
    solo se veía así, y con la suite repartida habría quedado escondido.
  - La CI también corre en serie, pero en Linux: lo que solo falla en Windows lo ve solo la serie local.
- **Una cuenta que dependa de acordarse no se cumple,** como pasó con la lista de los nueve sitios del
  número. Por eso la lleva el runner:
  - una serie entera en verde apunta su commit en `%TEMP%/ogr-slip2d-serial-run.json`;
  - cada corrida entera con `--jobs` termina con `last full serial run: <commit>, <fecha>, N commit(s)
    ago`, o con `SERIAL RUN DUE` a partir de 100;
  - **también avisa cuando no puede saberlo:** sin registro en la máquina, con un commit que la historia
    no tiene, o sin git. La duda cuesta una serie, mientras que la respuesta contraria podría saltarse
    una para siempre;
  - el commit apuntado es el HEAD de la corrida, el anterior al de la versión. La cuenta lleva así un
    commit de ventaja, en el sentido seguro;
  - **la serie de 0.1.375** (`8c4dcd3`, 6678/6678, terminada el 2026-10-28 a las 18:28) es anterior al
    mecanismo, y se apuntó a mano.
- **Un camino equivocado mío: la lista por tests.** El plan proponía dejar fuera los tests de más de 5 s.
  - **La primera lista** nombraba los 174 tests de 10 s o más en la suite entera con `--jobs 4`: 10 s
    en tramos son unos 5 s en serie, porque con cuatro tramos a la vez cada test tarda casi el doble
    (126,7 min de tests frente a 68,6 en serie).
  - El reparto preveía 10–11 min por tramo, y **`--fast --jobs 4` tardó 19,3 min.**
  - **La causa:** los tests de un archivo comparten lo caro, sea una búsqueda a nivel de módulo, una
    malla o un modelo resuelto. En la corrida entera lo paga el primero que lo usa, que es el que entra
    en la lista; quitado ese, lo paga el siguiente.
    - `TestTutorial20NonCircular.test_reaches_the_published_factor` pasó de casi 0 a 275 s.
    - `test_rescue_fold_v1362::test_switched_off_it_fails_as_before` pasó a 197 s.
    - Los tests que se quedaban sumaron 63,8 min, frente a los 43,4 que sumaban en la corrida entera.
  - **Reescribir la lista con esos tiempos no lo arreglaría:** la siguiente corrida entera devuelve el
    coste al primer test, y la lista oscilaría.
  - **La lista va por archivos.** Un archivo fuera cuesta cero y uno dentro cuesta su duración, la
    reparta como la reparta entre sus tests. El reparto lo predice, y la medida lo confirma (§2).
  - **El umbral son 45 s** en una corrida entera con `--jobs 4`. Deja fuera 42 archivos con 737 tests,
    que suman 85,9 de los 126,8 min medidos.
  - Con 60 s quedarían unos 13 min por tramo, y con 30 s unos 7,5, dejando fuera un 15 % de los tests.
    El de 45 s cumple los 15 min con margen y deja dentro el 89 % de los tests.
- **La lista solo la escribe `--write-slow-list`, a propósito.**
  - Si la reescribiera cada corrida, un archivo lento nuevo saldría de las corridas de desarrollo sin
    que nadie lo decidiera.
  - Al revés también se ve: cada corrida entera termina con `SLOW, NOT IN tests/_slow.txt` y los
    archivos de 90 s o más que la lista deja dentro. El doble del umbral, para que un archivo en la
    frontera no entre y salga en cada corrida.
- **El tiempo de cada test se sigue guardando** (`%TEMP%/ogr-slip2d-test-times.json`), aunque ya no
  decide la lista. Dice qué tests hacen lento un archivo, y es la tabla de partida del prompt de la
  auditoría del cómputo.
- **Otro fallo mío, que destapó la primera suite entera.** El runner escribía la cabecera de la lista con
  el identificador SPDX dentro de una cadena, y el test nuevo lo comparaba igual.
  `test_license_v143::test_no_stale_gpl_identifiers` lee todo identificador escrito en las fuentes y
  leyó `AGPL-3.0-or-later\n"`, comillas incluidas.
  - Ahora el runner copia sus dos primeras líneas, y el test compara con las suyas.
- **Corrección del changelog de 0.1.375.**
  - **Lo que decía:** que los 3 GB ajenos eran 11 servidores MCP de Claude Desktop abiertos desde el 22 y
    el 23 de octubre.
  - **Lo que eran:** 10 servidores `ogr-slip2d-mcp`, cada uno lanzado por una sesión distinta de Claude
    Code en VS Code (un `claude.exe` por sesión), del 22 al 27 de octubre.
  - Se cerraron 9 con el permiso de la propietaria. El décimo es el de la sesión que escribe esto.
  - Corregido allí.
- **Cerrarlos no cambió el reloj.** La suite entera con `--jobs 4` tardó 34,6 min frente a 35,2, y siguió
  bajando a 307 MB libres. La memoria privada de la suite llega a ~15,4 GB: los 3 GB liberados los ocupó
  ella.
- **Se queda el párrafo que 0.1.374 añadió a la regla 5 de AGENTS.md.** La propietaria pidió quitarlo si
  no hacía falta, y sí hace falta:
  - es el único sitio que dice que una `✗ [LEAK]` se arregla en el test, y que la lista blanca es solo
    para lo que no hace el test;
  - sin él, lo más fácil para un agente es añadir su fuga a la lista blanca.
- **Tres cambios respecto al plan:**
  - las opciones se llaman `--fast` y `--write-slow-list`, no `--rapido` ni `--escribir-lentos`, porque
    los nombres del código van en inglés;
  - la lista va por archivos y no por tests (arriba);
  - sale de la última corrida de cada archivo en la máquina, no de «la última serie», porque las
    versiones ya no corren en serie.

## 1. Qué cambia

**`tests/_runner.py`:**

- **`--fast`** deja fuera los archivos de `tests/_slow.txt`, en serie y en tramos.
  - Lo dice antes y después de los totales (`FILTERED RUN — … --fast: N slow file(s) left out`).
  - **Nunca hace nada vacío (regla 7):** sale con código 2 si no hay lista, o si todos los archivos
    seleccionados están en ella.
- **`--write-slow-list [SEGUNDOS]`** reescribe la lista: los archivos que tardaron eso o más (45 s por
  defecto), con sus segundos y sus tests al lado. Solo para la carpeta entera, sin patrones.
- **El tiempo de cada test** (`archivo::Clase::método`). Va en el informe de cada archivo y en
  `%TEMP%/ogr-slip2d-test-times.json`, bajo cualquier filtro.
- **El registro de la serie y su aviso.** La línea que decía «a release still needs the serial run» es
  ahora el aviso de la serie.
- **El aviso `SLOW, NOT IN tests/_slow.txt`** al final de cada corrida entera.

**`tests/_slow.txt` (nuevo):** 42 archivos, con la cabecera de licencia.

**AGENTS.md:**

- los comandos;
- qué vale para publicar;
- «Coste de los tests» reescrita: la tabla de tiempos, qué corrida pide cada momento y una sección nueva,
  **«Dónde y cómo van los tests nuevos»**.

**`.claude/commands/release.md`:** el paso 4 corre `--jobs 4` y lee las dos líneas del final.

**`.claude/commands/test.md`:** corre `--jobs 4`.

**La skill `tests-numericos`:** remite a la sección nueva de AGENTS.md.

**`tests/test_runner_fast_v1376.py` (30 casos)**, sobre archivos desechables. Comprueba que:

- `--fast` deja fuera exactamente los archivos de la lista, en serie y en tramos, con el mismo resultado
  y el aviso en sus dos sitios;
- `--fast` no corre nada vacío;
- la lista se escribe a partir de los tiempos, con su cabecera, solo con archivos que existen, nada sin
  tiempos y solo para la carpeta entera; y la lista real nombra solo archivos que existen;
- los tiempos se guardan por test y por archivo;
- una corrida entera nombra los archivos lentos que la lista deja dentro;
- el registro de la serie se escribe solo tras una serie entera en verde;
- el aviso se cuenta en commits, en un repositorio git desechable;
- el 100 de AGENTS.md y el del runner son el mismo número;
- ningún test escribe los archivos de la máquina.

Para lo que el runner solo escribe en su propia carpeta, el test lo copia en `tests/` de un repositorio
desechable y lo corre desde allí.

**`tests/test_runner_jobs_v1375.py`:** el test de la línea final pasa a comprobar el aviso de la serie.

**Los dos README:** el párrafo de `--jobs` y el de `--fast`.

**`docs/changelog/CHANGELOG_v0.1.375.md`:** la frase de los servidores MCP.

## 2. Medida

Suites el 2026-10-28, en el portátil de desarrollo (4 núcleos físicos y 8 lógicos, 15,9 GB), una cada
vez:

| Corrida | Casos | Resultado | Reloj | Mínimo libre | Tiempo con < 1 GB libre |
|---|---|---|---|---|---|
| `--jobs 4`, primera, sin lista | 6708 | 2 fallos (§0: la cabecera y la lista que faltaba) | 34,6 min | 307 MB | 12,0 min |
| `--fast --jobs 4`, lista por tests (174) | 6534 | verde | 19,3 min | 336 MB | 2,8 min |
| `--fast --jobs 4`, lista por archivos (42) | 5971 | verde | **12,7 min** | 328 MB | 2,3 min |
| `--jobs 4`, la de publicar | 6708 | verde, sin fugas ni tramos muertos | 34,7 min | 238 MB | 12,1 min |

- La corrida de publicar terminó con `last full serial run: 8c4dcd3, 2026-10-28 18:28, 0 commit(s) ago (the
  next is due at 100)`, y sin la línea `SLOW, NOT IN tests/_slow.txt`: ningún archivo de 90 s o más se
  queda dentro de `--fast`.
- **El reparto predice bien `--fast` por archivos.** Planeó 9,8–10,3 min por tramo, y la corrida entera,
  con el carril en serie y el arranque, salió en 12,7. La lista por tests planeó 10,4–11,0 y salió en
  19,3.
- La suite en tramos sigue paginando: 238–328 MB libres de mínimo, también sin los servidores ajenos.

## 3. Qué no cambia

- **Ningún número del programa.** Cambian el runner, sus tests, la lista, AGENTS.md, los comandos y la
  skill, los README y la versión.
- **`python tests/_runner.py` sin argumentos** corre lo mismo y da el mismo veredicto, que es el de la
  CI. Al terminar, además, guarda los tiempos y, si sale en verde, el registro de la serie.
- **La CI** sigue en serie en cada push y sigue siendo la referencia.
- **Pendiente para la etapa 5:**
  - la CI con un verde de verdad: el segfault al salir en Linux y si se usa `os._exit` tras los
    totales, que decide la propietaria;
  - el push.
