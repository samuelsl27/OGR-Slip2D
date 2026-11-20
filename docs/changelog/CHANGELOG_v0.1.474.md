# OGR Slip2D v0.1.474

**El núcleo fijado sube a `ogr-core` 0.2.1.** `pyproject.toml` pasa a fijar
`ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.1`, y es lo único que hace esta versión. Lo pidió este
programa a OGR-Core (`peticion_ogr_core_fuga_locale.md`). La respuesta, con el changelog del núcleo, está en
`referencias/_traspaso_ogr_core_0.2.1/`.

La 0.2.1 trae dos arreglos del runner compartido, los dos en `ogr_core/testing/`:

1. **El locale que adopta la primera `QApplication` en Unix deja de contar como fuga.** Es la línea que la CI de
   Linux da desde v0.1.377 en el primer archivo de la suite que construye una aplicación:
   `✗ [LEAK] locale: LC_CTYPE=C.UTF-8;LC_NUMERIC=C;… → C.UTF-8`, en `test_action_inventory_v1195.py`. Qt, al
   construirse en Unix, llama a `setlocale(LC_ALL, "")`. La entrada nueva `locale` de la lista de la suite
   (regla `ADOPTED_WITH_THE_FIRST_APPLICATION`) solo deja pasar ese paso: el de «como arranca el intérprete» a
   «el locale del entorno», con los dos valores medidos en un intérprete nuevo, y solo en el archivo que crea
   la primera `QApplication`. Cualquier otro cambio de locale sigue siendo fuga.
2. **Los tests `async def` cuentan entre los declarados**: en `--list`, en el progreso y en la suma de los trozos
   de `--jobs`.

**Ningún número cambia**: el código de cálculo del núcleo es el de la 0.2.0.

Decisiones de la propietaria (2026-11-20):
- **El núcleo va instalado desde la etiqueta en el `.venv`, no en editable.** El árbol local de OGR-Core se queda
  en la 0.2.0, porque lo comparte OGR FEM2D, que fija la 0.2.0. FEM2D no se toca.
- **Sin huella del banco**: no cambia ningún módulo de cálculo (§0).
- **Push de esta versión**, para que la CI de Linux confirme la regla del locale (§3).

## 0. Lo que se encontró

- **La etiqueta es lo que dice el traspaso.** `v0.2.1` es una etiqueta anotada (objeto `d620dd9`) que apunta al
  commit `f1c3d1a`. `git diff v0.2.0 v0.2.1 -- ogr_core` solo toca `__init__.py` (el número),
  `testing/leaks.py` y `testing/runner.py`. Por eso no hace falta la huella del banco: entre las dos etiquetas no
  cambia ningún módulo de cálculo. La procedencia diría `ogr_core 0.2.1`, y nada más.
- **El árbol local de OGR-Core no está en una etiqueta.** Está en `main` (`9b72044`), por detrás de `v0.2.1`. Su
  `ogr_core/` es idéntico al de `v0.2.0`, y por eso el `.venv` medía hasta ahora la 0.2.0 fijada.
- **Fijar la 0.2.1 con ese árbol en editable deja sin suite a este programa.** El runner se niega, porque el
  núcleo importado no es el fijado. Si el árbol avanzara, se negaría el de FEM2D. Así que el `.venv` cambia de
  editable a la etiqueta, que es también lo que instala la CI:
  `pip install --no-deps --force-reinstall "ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.1"`.
  Comprobado después del cambio:
  - `pip list` dice `ogr-core 0.2.1` sin ruta de editable;
  - `ogr_core.__file__` está en `.venv\Lib\site-packages`;
  - la lista de la suite tiene 16 entradas, `locale` entre ellas;
  - no queda ningún gancho `__editable__` del núcleo;
  - la cabecera del runner dice `shared: ogr_core 0.2.1 … (installed, no git tree)`;
  - el árbol de OGR-Core sigue sin cambios (`git status` vacío).
- **Un test confundía «instalado en el `.venv`» con «copiado en el árbol».**
  `test_runner_wrapper_v1473::test_the_core_is_shared_and_lives_elsewhere` exigía que `ogr_core.__file__` no
  estuviera dentro de la raíz del repositorio. El `.venv` vive en esa carpeta, así que con el núcleo instalado
  desde la etiqueta el test fallaba (`…\OGR-Slip2D\.venv\Lib\site-packages\ogr_core\__init__.py`). Pasaba antes
  solo porque el núcleo estaba en editable fuera de la raíz, y pasa en la CI porque allí el entorno no está en el
  repositorio. Se encontró en una corrida dirigida, antes de la suite, y se reportó antes de corregirlo. Por
  decisión de la propietaria, la carpeta de bibliotecas del intérprete (`sysconfig`: `purelib` y `platlib`) no
  cuenta como árbol; cualquier otro sitio bajo la raíz sigue fallando. La copia en el árbol ya la prohibía
  `test_the_two_copies_are_gone`. Caso nuevo: `test_an_installed_core_inside_the_tree_is_not_a_copy`. Dos
  mutantes, y mueren los dos: si se ignoran las bibliotecas, fallan los dos casos; si todo cuenta como «fuera»,
  falla el nuevo.
- **`AGENTS.md` mandaba instalar el núcleo en editable** (`pip install -e ../../Core/OGR-Core`). Ahora dice que
  se instala desde la etiqueta fijada, que el editable solo vale con el árbol en esa etiqueta, y qué orden cambia
  la fijación del entorno.
- **Cabo suelto de 0.1.473: los metadatos del `.venv` decían `ogr-slip2d 0.1.472`.** Slip2D se instaló con
  `--no-deps` antes de que su número subiera. `pip install --no-deps -e .` los deja en 0.1.474, y el núcleo sigue
  en 0.2.1.
- **Dos comentarios nombraban la 0.2.0 como si fuera el núcleo vigente.** Están en
  `ogr_gui/dialogs/misc_dialogs.py` y en la cabecera de `tests/test_version_consistency_v176.py`. El primero ahora
  dice «la que fija `pyproject.toml`», que no caduca. El segundo cuenta las dos versiones con la suya. Las
  menciones de la 0.2.0 en `tests/_runner.py`, `tests/_leaks.py` y `tests/test_runner_wrapper_v1473.py` no se
  tocan: dicen de qué versión del núcleo salió el runner, y eso es historia. Tampoco se tocan las de `ogr_data`
  («planned for v0.2.0»), ni la impresión, ni el roadmap: son la serie del programa, no el núcleo.

## 1. Qué cambia

- `pyproject.toml`: la fijación del núcleo, `@v0.2.0` → `@v0.2.1`, con su porqué en un comentario.
- `AGENTS.md`: la fijación, la instalación para desarrollo y la cabecera del runner.
- Dos comentarios (§0).
- `tests/test_runner_wrapper_v1473.py`: `_core_lives_elsewhere` y un caso nuevo (§0).
- Versión 0.1.474 en los siete sitios.

## 2. Para información, sin tocar

- **Con `--dev-core`, cuatro tests fallan por construcción** (lo midió la sesión de OGR-Core contra
  `0.2.1.dev0`): `test_the_imported_core_is_the_version_pyproject_pins`,
  `test_the_pin_is_the_core_that_is_imported`, `test_a_file_that_left_a_dialog_ends_with_zero` (relanza el
  runner sin la opción) y `test_the_window_and_every_dialog_of_the_census` (`dev` cuenta como texto en inglés en
  «Acerca de»). Qué se hace con ellos se decide con la forma de trabajar de la suite.
- **Los otros fallos de la CI de Linux no son de esto**: `test_cli_reported_caption_v1430` (×4) y
  `test_mcp_server_v1195::test_the_compact_profile_stays_small`. Están aparcados.

## 3. Pruebas

Windows, Python 3.14.7, con el `.venv` y el núcleo instalado desde la etiqueta, de una en una.

| Qué | Resultado |
|---|---|
| Suite entera, `--jobs 4`, fuera de pantalla | 7532 casos, 7530 pasan, 0 fallan, 2 saltados, sin fugas ni tramos muertos, código 0 |
| Cabecera del runner | `shared: ogr_core 0.2.1  …\.venv\Lib\site-packages\ogr_core  (installed, no git tree)` |
| Frente a 0.1.473 (7531, 7529 pasan, 2 saltados) | El caso nuevo de §0; ningún otro resultado cambia |
| Serie | No toca: la última serie en verde es `07524e8`, hace un commit (`SERIAL RUN DUE` no sale); tampoco sale `SLOW, NOT IN` |
| Dientes del caso nuevo | Dos mutantes, sobre una copia, y mueren los dos (§0) |
| Arranque | `ogr_gui` fuera de pantalla (`MainWindow.VERSION` 0.1.474, «Acerca de» con `ogr-core 0.2.1`), `ogr_cli --help`, `ogr_mcp --help` |

### La CI de Linux: la regla del locale, confirmada con Qt

Run 44696129877, sobre `dba074c`. Frente a la de `dbc316c` (run 44399595565, núcleo 0.2.0):

| Trabajo | `dbc316c` (núcleo 0.2.0) | `dba074c` (núcleo 0.2.1) |
|---|---|---|
| 3.11 | 7520 pasan, 5 fallan, 6 saltados, **Leaks: 1** | 7521 pasan, 5 fallan, 6 saltados, **sin fugas** |
| 3.12 | 7520 pasan, 5 fallan, 6 saltados, **Leaks: 1** | 7521 pasan, 5 fallan, 6 saltados, **sin fugas** |
| 3.13 | 7521 pasan, 4 fallan, 6 saltados, **Leaks: 1** | 7522 pasan, 4 fallan, 6 saltados, **sin fugas** |

- La cabecera de los tres trabajos dice `shared: ogr_core 0.2.1 … (installed, no git tree)`.
- `test_action_inventory_v1195.py` ya no da `✗ [LEAK] locale: LC_CTYPE=C.UTF-8;LC_NUMERIC=C;… → C.UTF-8`, y sus
  tests pasan. No queda ninguna línea `LEAK` en ninguno de los tres logs. Es la primera prueba con Qt real en
  Linux de la regla `ADOPTED_WITH_THE_FIRST_APPLICATION` de OGR-Core, que solo la había probado sin Qt.
- Los fallos son los aparcados y no cambian: `test_cli_reported_caption_v1430` (×4) en los tres trabajos.
  `test_mcp_server_v1195::test_the_compact_profile_stays_small` solo falla en 3.11 y 3.12: en 3.13 ya pasaba con
  `dbc316c`. El traspaso lo daba como fallo de Linux sin distinguir versiones.
- *Licence consistency*, en verde.
