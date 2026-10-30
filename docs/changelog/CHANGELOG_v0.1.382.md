# OGR Slip2D v0.1.382

**El memo de `_det` de `test_probabilistic_all_failed_v1169` reconoce el modelo, y `tests/_slow.txt` se
reescribe tras el bloque de tests.**
- **El memo:** estaba cifrado solo por el conjunto de métodos. Una llamada con otro modelo y los mismos métodos
  recibía las superficies de este archivo. Ahora la clave lleva también el modelo.
- **La lista de lentos:** se reescribe con `--write-slow-list`, porque las versiones 0.1.378–0.1.381
  compartieron lo repetido en los tests. Pasa de 42 archivos a 37: salen nueve y entran cuatro.

Es la versión que la propietaria decidió para después de V4, en la fase 3 de la auditoría del cómputo.
**Ningún módulo del programa cambia**, salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **El riesgo latente de `_det`**, que la guarda `test_shared_test_caches_v1378` listaba desde 0.1.378.
  - `_det(project, methods)` memoizaba `{método: superficie crítica}` con la clave `tuple(methods)`, sin el
    proyecto.
  - Lo llaman tres sitios: dos de este archivo y uno de `test_partial_method_loss_v1170`, más `_run_gm`, que lo
    lee. Los tres pasaban el mismo modelo Ej_1, construido cada vez de nuevo, así que no había ningún error.
  - Pero el día que uno pasara otro modelo, recibiría en silencio las superficies de Ej_1, y solo en la serie:
    con `--jobs` el archivo puede caer en otro proceso.
- **La clave nueva:** el modelo tal como lo lee la búsqueda, comparable entre dos construcciones. Es su
  `to_dict()` sin las fechas que pone cada construcción, y con cada uuid renombrado por su orden de aparición.
  - Dos construcciones de Ej_1 comparten clave, y los tests del archivo siguen compartiendo una búsqueda.
  - Otro modelo obtiene la suya.
  - Cuesta un `to_dict` y un `json.dumps` por llamada.
- **Dos tests nuevos** (`TestTheDeterministicMemoKnowsTheModel`):
  - el mismo modelo construido dos veces comparte la clave;
  - un modelo más pesado (+2 kN/m³) tiene otra clave y otra superficie crítica.

  Tardan 0,02 y 0,35 s.
- **La guarda:** las dos entradas de `_det` y `_run_gm` siguen en su lista blanca, porque el alcance entre
  archivos existe, pero su razón ya no es «latente».
- **`tests/_slow.txt`.** La propietaria decidió reescribirla tras dos corridas enteras con `--jobs 4` desde la
  última versión de tests: la de 0.1.381 y la de esta.
  - **De qué corrida sale:** `--write-slow-list` lee solo la última, la de esta versión. La de 0.1.381 no
    cuenta en la lista: solo dio a esta las duraciones con que cortó sus tramos, porque `--jobs` reparte
    según lo que tardó cada archivo la vez anterior.
  - **El criterio, el de siempre:** 45 s o más. Quedan 37 archivos, con 664 de los 6726 tests, y el runner
    los cuenta como 67,2 de los 109,6 min cronometrados.
  - **Lo que se mueve,** con el tiempo de la corrida que escribió la lista anterior (`--jobs 4`, 2026-10-28) y
    el de esta:

    | Archivo | Lista anterior (s) | Esta corrida (s) |
    |---|---:|---:|
    | *Salen* | | |
    | `test_reverse_curvature_v182` | 71 | 18,7 |
    | `test_user_surfaces_v1157` | 65 | 33,5 |
    | `test_acads_validation_v178` | 67 | 40,9 |
    | `test_sa_autorefine_v117` | 53 | 37,3 |
    | `test_initial_factor_v1309` | 50 | 39,6 |
    | `test_unsaturated_v127` | 48 | 29,6 |
    | `test_texts_spanish_v1370` | 46 | 39,8 |
    | `test_background_tasks_v1365` | 45 | 37,4 |
    | `test_transient_celia_v1268` | 45 | 42,7 |
    | *Entran* | | |
    | `test_dialogs_fit_more_v1326` | < 45 | 61,7 |
    | `test_probabilistic_v135` | < 45 | 47,0 |
    | `test_remote_oauth_v1204` | < 45 | 46,2 |
    | `test_face_tie_search_v1136` | < 45 | 46,0 |

  - **Dos salen por lo que compartió 0.1.381:** `test_reverse_curvature_v182` y `test_user_surfaces_v1157`.
  - **Los otros once no han cambiado desde 0.1.376, y el motor tampoco:** su diferencia es de la corrida, no
    del código.
    - Con `--jobs 4`, lo que tarda un archivo depende de qué corre a la vez y de lo que su proceso ya lleva
      dentro («Coste de los tests», en AGENTS.md). Y V1–V4 movieron las duraciones con que se cortan los
      tramos.
    - `test_remote_oauth_v1204` corre solo, en el carril en serie: a él la contención no lo explica.
    - Cuánto pesa cada causa en cada archivo no se ha medido.
  - **Consecuencia:** con el mismo código, el umbral de 45 s mete y saca archivos de una corrida a otra. La
    lista vale lo que vale la corrida que la escribe.
  - **`test_fos_chart_v1308` sigue dentro** (65 → 59 s). El changelog de 0.1.381 decía que bajaría de los 45 s
    «con lo compartido», y la frase no tenía base: ese archivo no comparte nada, por decisión de la
    propietaria en V2.
  - **`--fast` corre nueve archivos más y deja de correr cuatro.** En esta corrida, los nueve sumaron 319,5 s y
    los cuatro, 200,9. Lo que tardará `--fast` no se ha medido.

## 1. Qué cambia

- `tests/test_probabilistic_all_failed_v1169.py`: `_model_key()` y la clave de `_det`; dos tests nuevos.
- `tests/test_shared_test_caches_v1378.py`: las razones de `_det` y `_run_gm`, y su docstring.
- `tests/_slow.txt`, reescrita con `--write-slow-list`.
- El número, en los nueve sitios, y el contador de los dos README (6726).

## 2. Qué se probó

- `test_probabilistic_all_failed_v1169` y `test_partial_method_loss_v1170`, solos: 67 de 67.
- `test_shared_test_caches_v1378` solo: 12 de 12.
- La suite entera con `--jobs 4`: **6726 de 6726, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 29,3 min. La
  última serie en verde fue `8c4dcd3`, hace 6 commits.
- **Sin correr:**
  - la serie entera, que no toca;
  - la huella de los 23 casos, porque no aplica: ningún módulo `ogr_*` cambia salvo la línea del número.

## 3. Lo que queda

- **Las versiones del motor (V5–V18)**, cada una con su OK. La primera es el localizador del MEF.

## Archivos

- `tests/test_probabilistic_all_failed_v1169.py`
- `tests/test_shared_test_caches_v1378.py`
- `tests/_slow.txt`
- `docs/changelog/CHANGELOG_v0.1.382.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
