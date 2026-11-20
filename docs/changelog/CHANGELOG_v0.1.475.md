# OGR Slip2D v0.1.475

**El núcleo fijado sube a `ogr-core` 0.2.2, y la suite sale en verde también contra un núcleo en
desarrollo.** `pyproject.toml` pasa a fijar
`ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.2` (etiqueta anotada `fde9cbc` →
`96f0305`). Lo pide la sesión de OGR-Core (traspaso en `referencias/_traspaso_ogr_core_0.2.2/`): su
CI va a correr esta suite contra el núcleo de cada PR, con `--dev-core`, antes de etiquetarlo, y para
eso la suite tiene que salir **entera en verde** en una corrida así. Medido por esa sesión sobre
`302a97c` contra `0.2.2.dev0`: 7527 de 7532, tres fallos por construcción, ninguna fuga.

La 0.2.2 trae una sola cosa del runner compartido: **una corrida con `--dev-core` se lo dice a sus
tests** (`OGR_DEV_CORE=1` mientras dura, `ogr_core.testing.runner.dev_core_run()`), y un runner
relanzado por un test acepta el mismo núcleo sin la opción. `git diff v0.2.1 v0.2.2 -- ogr_core` solo
toca `testing/runner.py` y el número: **ningún número cambia**, y por eso no hay huella del banco.

## 0. Lo que se encontró

- **El árbol local de OGR-Core ya no está en la 0.2.0**, contra lo que decía el traspaso. Está en
  `main` = `b804724` (su PR 5), limpio, y su `ogr_core/__init__.py` dice `0.2.3.dev0`;
  `git diff v0.2.2 b804724` solo toca los dos números de versión. La corrida de desarrollo que pedía el
  traspaso, y que daba por imposible todavía, se ha podido hacer contra ese árbol, solo leyéndolo por
  `PYTHONPATH` (§3). El árbol no se ha tocado.
- **Por qué el censo de textos en español leía `ogr-core 0.2.2.dev0` como inglés.** No es la versión:
  es la palabra `dev`, que está en el vocabulario inglés del censo porque sale de la clave
  `std dev: …` de la ventana de estadística y ningún texto español la usa. Medido con
  `_reads_english`: `"ogr-core 0.2.1"` → no inglés, `"ogr-core 0.2.3.dev0"` → inglés, `"dev"` →
  inglés. Consecuencia: una excepción por la palabra `dev`, o por cualquier `.devN`, cegaría el censo
  justo donde caza un `std dev` sin traducir.
- **La excepción no podía ir a `SHOWN_EXCEPTIONS`.** El censo exige que cada patrón de esa lista case
  con algo leído como inglés («no ghosts»), y en una corrida normal `ogr-core 0.2.2` no se lee como
  nada: el patrón sería un fantasma y el test fallaría justo en la corrida normal.
- **Los tests que relanzan el runner no necesitaban nada**, como decía el traspaso:
  `test_shutdown_release_v1422` pasa por la variable heredada, y
  `test_runner_wrapper_v1473::TestWithoutAPinNothingRuns` se para antes, por no tener fijación.
  Ningún test compara la cabecera ni los totales de un runner relanzado con la versión fijada (grep
  de `shared: `, `DEV CORE`, `pinned_from_pyproject`).

## 1. Qué cambia

- **Fijación**: `pyproject.toml`, `@v0.2.1` → `@v0.2.2`, con su comentario.
- **Entorno**: `.venv` con `pip install --no-deps --force-reinstall "ogr-core @ git+…@v0.2.2"`.
  `pip show` dice `0.2.2` en `.venv\Lib\site-packages`, y la cabecera del runner,
  `shared: ogr_core 0.2.2 … (installed, no git tree)`.
- **Los dos tests de la fijación** comprueban el núcleo al que se sujetó la corrida, no «importado ==
  fijado»: en una corrida normal es el fijado, exactamente; en una de desarrollo, el que acepta
  `--dev-core` y nada más. Lo dice `core_problems()` (`tests/test_version_consistency_v176.py`), que es
  `runner.shared_problems(package_origins(...), pinned, dev_core=runner.dev_core_run())`, y lo usan
  `test_the_imported_core_is_the_version_pyproject_pins` y
  `test_runner_wrapper_v1473::test_the_pin_is_the_core_that_is_imported` (este con `W.SHARED` y
  `W.pinned()`, lo que recibe el runner). Fuera de una corrida de desarrollo, los dos mantienen además
  la igualdad exacta de siempre. Dientes, en `TestWhatTheCheckOfThePinAccepts`, con paquetes
  `ogr_core` inventados y fijación `0.2.2`:
  - corrida normal: pasa `0.2.2`; fallan `0.2.3.dev0`, `0.2.2.dev0`, `0.2.3` y `0.2.1`;
  - corrida de desarrollo: pasan `0.2.2` y `0.2.3.dev0`; fallan `0.2.2.dev0` (anterior a la
    fijada), `0.2.1.dev0`, `0.2.3rc1` (candidata), `0.2.3` y `0.2.1`;
  - por defecto sigue a la corrida: un `0.2.3.dev0` pasa exactamente cuando `dev_core_run()` es
    verdad;
  - un núcleo que no resuelve no pasa nunca.
- **El censo de textos en español** (`tests/test_labels_spanish_v1321.py`): **la versión del núcleo
  importado es un dato, como el nombre de un material.** Antes de leer palabras, `_reads_english`
  quita exactamente `ogr-core <ogr_core.__version__>`, acotado (ni letra, dígito, punto o guion antes;
  ni letra, dígito o punto después), y deja `ogr-core`, que ya pasaba. Ni la palabra `dev`, ni otra
  versión, ni el resto de «Acerca de». Dientes en `TestTheCoresVersionIsData`, con `0.2.3.dev0`: esa
  cadena pasa; sin la excepción se lee como inglés; `ogr-core 0.9.9.dev3`, `ogr-core 0.2.3.dev01`,
  `std dev: 1.0`, `0.2.3.dev0` sin marco, `ogr-core 0.2.3.dev0 settings` y
  `Version: ogr-core 0.2.3.dev0` siguen leyéndose como inglés.
- **`AGENTS.md`**: la fijación (`v0.2.2`, `shared: ogr_core 0.2.2 …`); «Instalación para desarrollo»
  ya no deja la puerta al editable (el `.venv` tiene siempre la etiqueta), y dice cómo se prueba un
  núcleo sin etiquetar sin instalar nada (`PYTHONPATH=<árbol o worktree> … --jobs 4 --dev-core`); y
  una sección nueva, «Un núcleo y varios programas», con las reglas del núcleo dichas desde este lado
  (un solo `main` y ramas cortas con PR; `ogr_core` no se cambia ni se copia aquí; la fijación se sube
  a propósito, en un commit, y la fila de este programa en `docs/consumidores.md` de OGR-Core se
  corrige allí; la suite contra un núcleo antes de etiquetarlo; `dev_core_run()` en los tests).
- **`CONTRIBUTING.md`**: lo mismo en inglés (sin editable; `PYTHONPATH` y `--dev-core`).
- Versión en siete sitios.

## 2. Para información, sin tocar

- Las menciones de `0.2.1` en `spec/features/010-adoptar-ogr-core/` y en el docstring de
  `test_runner_wrapper_v1473` cuentan el pasado y se quedan.
- **La fila de OGR Slip2D en `docs/consumidores.md` de OGR-Core** sigue diciendo `v0.2.1` / «su
  v0.1.474». Pasa a `v0.2.2` / «su v0.1.475», y se corrige allí, por la sesión de OGR-Core.
- Los cinco fallos aparcados de la CI de Linux (`test_cli_reported_caption_v1430` ×4 y
  `test_the_compact_profile_stays_small` en 3.11 y 3.12) no entran en esta versión. Mientras sigan, la
  CI de OGR-Core no enciende el trabajo de esta suite.

## 3. Pruebas

Windows, `.venv`, fuera de pantalla, de una en una.

| Qué | Resultado |
|---|---|
| Los tres archivos tocados, normal (filtrada) | 61 casos, 60 pasan; el que falta era este changelog, sin escribir |
| Los tres archivos tocados, `--dev-core` contra `b804724` (filtrada) | Lo mismo: los tres rojos por construcción de `302a97c` pasan |
| Nueve mutantes, uno a uno, cada uno en las dos corridas | Mueren los nueve (abajo); los dos archivos, idénticos byte a byte después |
| Suite entera `--jobs 4`, contra la etiqueta instalada (1.ª) | 7541 casos, 7538 pasan, **1 falla** (error propio, abajo), 2 saltados, sin fugas |
| Suite entera `--jobs 4`, contra la etiqueta instalada (2.ª) | **7541 casos, 7539 pasan, 0 fallan, 2 saltados, sin fugas**, ~27 min; `shared: ogr_core 0.2.2  …\.venv\Lib\site-packages\ogr_core  (installed, no git tree)` |
| Suite entera `--jobs 4 --dev-core`, `PYTHONPATH` al árbol de OGR-Core | **7541 casos, 7539 pasan, 0 fallan, 2 saltados, sin fugas**, ~29 min; `shared: ogr_core 0.2.3.dev0  C:\Samuel\OGR_Suite\Core\OGR-Core\ogr_core  @ b804724`, y `DEV CORE — ogr_core 0.2.3.dev0 runs in place of the pinned 0.2.2 — NOT evidence for a release` antes y después de los totales |

Son 7541 = los 7532 de antes y 9 nuevos (4 de la fijación y 5 del censo). Los dos saltados son los de
siempre (uno de POSIX y otro que pide el banco de verificación). La última serie en verde sigue siendo
`07524e8`, a 3 commits: no toca.

**Mutantes.** Fijación: el valor por defecto de `dev` fijo a `True` (muere en la corrida normal) o a
`False` (en la de desarrollo: los dos tests de la fijación y el del valor por defecto); el helper que
devuelve `[]` (cuatro casos, en las dos); el helper que ignora su `dev` (en las dos); y el test que
vuelve a comparar cadenas (en la de desarrollo, con `('0.2.3.dev0', '0.2.2')`, el fallo de
`302a97c`). Censo: cualquier versión detrás de `ogr-core`, `dev` fuera del vocabulario, todo texto que
empiece por `ogr-core`, y sin la excepción; mueren los cuatro en las dos corridas.

**Error propio.** La primera corrida entera falló en
`test_agent_scaffolding_v158::test_exists_and_is_substantial`: `AGENTS.md` tiene que quedarse por
debajo de 500 líneas, y con lo añadido tenía 526 (483 antes). No se tocó el test: el texto se reescribió
más corto y el párrafo de «Estructura» que ya decía que `ogr_core` solo se cambia en OGR-Core se fundió
con la sección nueva, que lo repetía. Queda en 499, a una línea del tope, y lo próximo que entre en
`AGENTS.md` tendrá que sacar algo.

**Para información.** La corrida de publicar sigue avisando `SLOW, NOT IN tests/_slow.txt` por
`test_dialogs_fit_v1315.py` (103,8 y 115,5 s); no cambia en esta versión y `_slow.txt` no se ha
reescrito. La de desarrollo no da ese aviso ni el de la serie, y no apunta nada como serie: no vale
para publicar.
