# OGR Slip2D v0.1.379

**El desembalse de `test_transient_v130` se calcula una vez para sus siete lectores.**
- **Medido:** el archivo solo pasa de 165,4 s a **78,1 s (−53 %)**, con los mismos 35 tests.
- **La guarda de 0.1.378 se reescribe**, porque una revisión adversarial demostró que prometía más de lo
  que hacía: solo reconocía un memo por su nombre y a una llamada de distancia. Ahora lo reconoce por su
  forma, sigue las cadenas entre archivos, los ayudantes que devuelven un módulo y las variables, y lee los
  alias por función. Encontró nueve alcances más, todos de objetos que se leen, y una razón que yo había
  escrito mal.

Es la V2 de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`). **Ningún
módulo del programa cambia**, salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **Las decisiones de la propietaria (2026-10-29):**
  - V2;
  - **compartir solo en `test_transient_v130`**: `test_fos_chart_v1308` y `test_transient_initial_result_v1307`
    cierran su ventana, y una ventana cerrada compartida viviría hasta el final del proceso;
  - el arreglo de la clave de `_det`, después de V4.
- **Lo que no se preguntó y se deja como está:** `TestTransientGui._setup`. Tres de sus cinco tests cambian el
  proyecto, y compartir el de los otros dos era otra decisión.
- **Lo que se comparte:** el desembalse por defecto, con las etapas de 1e4 y 1e6 s y las dos con factor de
  seguridad. Lo leen siete tests:
  - cuatro de `TestStageFactorsOfSafety`: hay factor por etapa, el campo evoluciona, la seguridad se recupera y
    el resultado activo se restaura;
  - los tres de `TestInterpretStageNavigation`. Su visor, `InterpretGroundwaterWindow`, es de solo lectura:
    `_on_stage` solo cambia el resultado que enseña la ventana, y el constructor no escribe en el proyecto.
- **Lo que conserva su corrida:**
  - la variante `calc_sf=False`;
  - `test_warning_when_materials_ignore_seepage`, que apaga la filtración de los materiales y recalcula: cambia
    el proyecto.
- **El ayudante sigue sin memoizar.** `TestStageFactorsOfSafety._drawdown` lo llaman `test_fos_chart_v1308` y
  `test_transient_initial_result_v1307`, que cambian lo que reciben. El memo es una función aparte del
  archivo, `_shared_drawdown`.
- **Dónde está el coste:** un desembalse cuesta ~14 s, y casi todo es el factor de seguridad de cada etapa. La
  variante sin factores tarda 1,0 s.
- **La ganancia, medida.** El archivo solo, antes y después, seguidos y con `TEMP`/`TMP` redirigidos: 165,4 s →
  78,1 s (−87 s).
  - Ahora paga el primer lector por orden de nombre, `test_stage_selector_lists_every_stage` (17,9 s). Los
    otros seis lectores bajan a ~0.
  - **Según la proyección calibrada del informe:** la serie −1,5 min y `--jobs 4` −1,3 min. Con V1, la serie
    bajaría ~3,1 min. Esta suite tardó 31,6 min, pero el reloj de una sola corrida no mide esto.
  - **Seis `MainWindow` menos** siguen vivas en la serie hasta el final del proceso. Eso abarata, sin medirlo,
    los archivos que recorren todas las ventanas vivas al cambiar de tema (§8.2 del informe).
- **La revisión adversarial de V1 y V2.** Tres revisores de solo lectura, uno por enfoque, y un verificador
  por hallazgo que intentaba refutarlo.
  - **Lo compartido: limpio.** Ningún lector cambia lo compartido ni nada que cuelgue de ello, y el orden de
    los tests no puede mover ninguna afirmación.
  - **La semántica de los tests: limpia.** Ninguna regla 7 se debilita, y `_best_of` conserva el orden y el
    desempate. Solo una frase de su docstring: «con los mismos argumentos» era «sobre un modelo igual».
  - **La guarda (`test_shared_test_caches_v1378`): cinco hallazgos confirmados.** La versión de 0.1.378
    prometía más de lo que hacía:
    - solo reconocía un memo por su nombre (`*CACHE*`, `_SHARED`). `test_report_spanish_v1355._RUN` y
      `test_add_surface_three_points_v1168._WINDOWS` son memos con otro nombre, y otro archivo los alcanza;
    - no seguía una cadena a través de un segundo archivo. `test_statistics_surface_line_v1255` llega a
      `_notched` por `test_mass_switch_note_v1238._model()`, y `test_stat_notes_v1353` por
      `test_partial_method_loss_v1170._real_partial()`;
    - no seguía un ayudante que devuelve el módulo (`_helpers()._canvas_ready()`), ni una variable, ni un
      alias usado para dos módulos en dos funciones (`T` en `test_stat_notes_v1353`). Mi docstring decía que
      esto último no ocurría en `tests/`, y ocurre;
    - **una razón de su lista blanca era falsa, y la escribí yo:** cité «su docstring» en `_notched`, y la
      frase «NEVER handed out to be mutated» está en `_project`;
    - el nombre `_shared_*` convertía en memo a un constructor que construye de nuevo cada vez
      (`test_support_normal_arm_v1214._shared_meshes`).
- **La guarda, reescrita con esas reglas.**
  - **Qué es un memo:**
    - un contenedor con nombre de caché, y lo que lo lee;
    - otro contenedor vacío de módulo que una función comprueba (`in`, `not`, `if X`) y del que devuelve
      algo. Una lista a la que solo se añade es un registro, no un memo, y el nombre no prueba nada;
    - un método juzgado por sí mismo (`Clase.método`, también a través de `self`);
    - lo que llega a un memo propio o de otro archivo, en un punto fijo sobre todos los archivos.
  - **Qué es alcanzarlo:** importarlo, o llegar por un atributo de un módulo o de una clase importados
    (`T.f`, `C.m`, `C().m`, `T.C().m`), por un ayudante que devuelve el módulo, o por una variable atada a
    cualquiera de ellos. Los nombres se resuelven por función.
  - **Límite que queda, dicho en su docstring:** el acceso dinámico (`getattr`, `importlib`), que no aparece
    en `tests/`.
  - **Encontró diez alcances más** y van a su lista blanca, cada uno con su razón comprobada en el código:
    - `_run_gm`, el mismo riesgo latente de `_det`. Su única llamada pasa el mismo modelo Ej_1, y se arregla
      después de V4;
    - los cinco de la cadena de `_notched` por `test_mass_switch_note_v1238`. La ventana de estadística no
      escribe en su proyecto, el motor clona por muestra, y `_wide` y `_narrow` construyen una variable nueva
      cada vez;
    - `_real_partial`;
    - `_capture` del informe en español. El generador del informe y sus figuras no escriben en lo que leen;
    - `_window` y `_canvas_ready`. Quien los lee va antes por orden de nombre y es el único que los importa,
      así que el runner carga después el archivo dueño como un módulo nuevo.

    Son 19 en total. Las razones de `_notched`, corregidas.
  - **Doce tests**, siete de ellos sintéticos para que pueda fallar: la forma frente al nombre, el registro,
    el ayudante, la variable, el alias en dos funciones y la cadena por un segundo archivo.
  - **Un camino equivocado más:** la primera reescritura tardaba 2,9 s porque abría todo archivo que
    declarase un contenedor. Ahora solo abre los que el texto delata como memo (lo comprueban y lo
    devuelven) y, mientras se encuentre uno, los que los importan: 0,94 s.
- **La reescritura no tuvo segunda revisión independiente:** los dos agentes de esa revisión chocaron con el
  límite de uso de la cuenta y no devolvieron nada. La respaldan sus doce tests, siete de ellos sintéticos, y
  que encuentra exactamente los alcances que señaló la primera revisión.
- **La relación con V5, el localizador del MEF:** en K18, `Mesh.locate` es la mitad de este desembalse. La
  versión que llegue primero encoge lo que la otra gana en este archivo.
- **La huella del banco de pruebas no aplica:** ningún módulo `ogr_*` cambia salvo la línea del número.

## 1. Qué cambia

- `tests/test_transient_v130.py`: `_SHARED` y `_shared_drawdown()`; siete tests leen lo compartido.
- `tests/test_shared_test_caches_v1378.py`, reescrita: memos por su forma, cadenas entre archivos, ayudantes,
  variables y alias por función. La lista blanca pasa de 9 a 19, con las razones de `_notched` corregidas, y
  los tests pasan de 6 a 12.
- `tests/test_annealing_inequality_v1119.py`: el docstring de `_best_of`.
- El número, en los nueve sitios, y el contador de tests de los dos README.

## 2. Qué se probó

- `test_transient_v130` solo, antes y después: 35 de 35 las dos veces.
- `test_shared_test_caches_v1378` solo, reescrita: 12 de 12, 0,94 s.
- La suite entera con `--jobs 4`, dos veces:
  - antes de la revisión: 6720 de 6720, en 31,6 min;
  - **después de reescribir la guarda: 6724 de 6724, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 31,5 min.
    La última serie en verde fue `8c4dcd3`, hace 3 commits.
- **Sin correr:**
  - la serie entera, que no toca;
  - la huella de los 23 casos, porque no aplica.

## 3. Lo que queda

- **V3 y V4**, las dos versiones de tests que faltan: Overall Slope, y las rejillas con el enjambre y las
  superficies de usuario. Después, la clave de `_det`, y luego las versiones del motor. Cada una con su OK.

## Archivos

- `tests/test_transient_v130.py`
- `tests/test_shared_test_caches_v1378.py`
- `docs/changelog/CHANGELOG_v0.1.379.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
