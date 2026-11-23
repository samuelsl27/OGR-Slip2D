# OGR Slip2D v0.1.482

**D371: la actualización final del progreso de un trabajo se escribe con reintentos.** Un defecto
de lo que queda escrito en la carpeta del trabajo, no del análisis: no se mueve un número, ni la
salida de `job_get`.

## 0. Lo que se encontró

Ficha D371, abierta el 2026-10-28 con 0.1.377: en la primera suite entera con `--jobs 4` falló
`test_api_jobs_v1194::TestIsolation::test_progress_is_written_and_ends_complete` en
`assert prog["done"] == prog["total"] > 0`, con el trabajo ya en `done`. Ya se había visto frágil
hacia 0.1.301 con la máquina cargada.

- `_write_progress` (`ogr_api/jobs/worker.py`) escribe un temporal y lo renombra sobre
  `progress.json` con **un solo intento**, a propósito desde v0.1.198: el progreso es orientativo, y
  un `PermissionError` en la retrollamada llegaba a matar el análisis.
- La retrollamada del worker limita las escrituras a una cada 0,5 s y deja pasar siempre la final
  (`done == total`). **El limitador sí la protegía; los reintentos, no**: iba con el mismo único
  intento que las intermedias.
- El padre lee `progress.json` en cada sondeo (`Job.status`, cada 0,1 s en `Job.wait`), y Windows
  no deja renombrar sobre un archivo que otro proceso tiene abierto (WinError 5). Si la lectura
  coincidía con la última escritura, la carpeta de un trabajo terminado decía para siempre que iba
  por la penúltima. En Linux el renombrado no falla: la CI no lo podía ver.
- **Al API no le afectaba**: `Job.status()` solo enseña el progreso mientras el trabajo corre. Sí a
  quien lea la carpeta (el test, o un agente que la mire) y a la suite, de vez en cuando.
- Al planificar se vio un matiz: varias rutas del motor llaman `progress(n, n)` también a mitad del
  trabajo (el transitorio con factores, `transient_stability.py`, avisa al terminar el agua y luego
  siguen los factores; las búsquedas por fases). Con el arreglo esas llamadas también reintentan.
  El coste es el mismo: como mucho ~1 s, y solo si el padre tiene el archivo abierto en ese momento.

## 1. Decisión de la propietaria (2026-11-22)

De las tres alternativas de la ficha, **A**: la actualización final reintenta, las intermedias no.

- **B** (el estado final lleva el progreso y `job_get` lo enseña) cambiaba la salida del API para
  los trabajos terminados; descartada.
- **C** (declarar el progreso orientativo también al final y aflojar el test) dejaba una carpeta de
  trabajo terminado diciendo que va por la mitad; descartada.
- Una variante que se planteó (reescribir el último progreso visto una sola vez al terminar el
  runner, antes de `status.json`) no se eligió.

## 2. Cambio

- `_write_progress`: con `done >= total`, `tries=_REPLACE_TRIES` (40 × 25 ms, los mismos que
  `status.json`); las intermedias, `tries=1` como antes. Si los reintentos se agotan, devuelve
  `False` sin lanzar: la garantía de v0.1.198 no cambia. Con `total == 0` el caso es final, igual
  que en el limitador de la retrollamada.
- Nada más: `status.json`, `summary.json` y `result.pkl`, su contenido y su orden, y `job_get`,
  como estaban.

## 3. Qué se probó

- `tests/test_job_progress_final_v1482.py`, tres casos, sin reloj:
  - la final, con `progress.json` abierto desde otro hilo ~100 ms, espera y escribe 5 de 5;
  - la final, con el archivo abierto todo el rato, devuelve `False` sin lanzar, con 39 esperas
    (`time.sleep` del worker sustituido por un contador, restaurado);
  - una intermedia con el archivo abierto devuelve `False` con **cero** esperas y el archivo sigue en
    1 de 5: la garantía de v0.1.198.
  - En Linux el renombrado no falla, y los casos afirman lo que es cierto allí (escribe a la
    primera, nada espera).
- **Discriminación**, en Windows: el archivo nuevo en un `git worktree` de 0.1.481 (f018616), con el
  runner lanzado desde dentro (`tree: …ogr_wt_d371 @ f018616`, y `ogr_api.jobs.worker.__file__` en
  el worktree): fallan los dos casos de la final y pasa el de la intermedia, que es el invariante
  que no debía cambiar. En el árbol nuevo, 3 de 3.
- Vecinos (`api_jobs jobs_file_race job_progress mcp version_consistency`): 50 de 50.
- Banco: `d371()` en el `verificar_cierres.py` de la raíz, registrada en `COMPROBACIONES`, mide en
  vivo la final con el lector (5 de 5) y la intermedia (`False`, 0 esperas): **CUBIERTO POR TEST**.

## 4. Suite

En el `.venv` (`shared: ogr_core 0.2.2 … (installed, no git tree)`), fuera de pantalla,
**`--jobs 4`**: 7554 casos, 7553 pasan, 0 fallan, 1 saltado (`os.killpg`, solo POSIX), sin fugas
ni tramos muertos, código de salida 0. Última serie en verde: 7aff40b, 3 commits antes.

## 5. Fuera de git: las rutas del banco

Al correr `d371()` salió `SIGUE ABIERTO` con el arreglo medido bien: `_tools/banco.py` del banco
tenía `REPO_OGR = c:/Samuel/OGR_Suite/Slip2D/OGR-Slip2D`, y `generar_prompts.py` y
`comprobar_citas_prompts.py`, `c:/Samuel/OpenGeoRock_Slip2d/OGR-Slip2D`, rutas de PCs anteriores
que aquí no existen. El motor llegaba igual, por la instalación editable del `.venv`, pero
`_tests_con` no encontraba ningún test: le pasaba a toda comprobación que lea archivos del
repositorio. Por decisión de la propietaria (2026-11-23), las tres de la raíz deducen ahora el
repositorio de su propia ruta, como `_auditoria/COMPUTO/bench/comun.py` (v0.1.480).

Después del commit de la versión, también por decisión de la propietaria: las 33 herramientas
de `02_…/_tools` que escribían `c:/Samuel/OGR_Suite/Slip2D/OGR-Slip2D` (entre ellas
`ruta_motor.py`, el sitio que el resto importa desde D187) la deducen igual, con
`Path(__file__).resolve().parents[5] / "OGR-Slip2D"`. Las 37 compilan; `ruta_motor.REPO_MOTOR`
resuelve a este repositorio, y `verificar_cierres.py D187` del 02 sigue en CUBIERTO POR CODIGO.
No se han tocado `Evaluaciones/` (instantáneas congeladas), los scripts de investigación de
`_auditoria/` (registros de lo que se midió entonces) ni las rutas escritas en prosa dentro de
los prompts largos.

Una consecuencia que conviene saber: `banco.py` mete `REPO_OGR` delante de `sys.path` si la
cadena no está ya. Con la ruta vieja eso no hacía nada; ahora mete el árbol vivo, como hacía en
el PC anterior. En un A/B contra un worktree, el árbol viejo hay que ponerlo después de importar
el banco (como dice la memoria del buscador editable), igual que antes.
