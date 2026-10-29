# OGR Slip2D v0.1.378

**Los tests dejan de repetir lo que calculaban igual.** El archivo más caro de la suite,
`test_annealing_inequality_v1119` (753 s en la última corrida con `--jobs 4`), calcula una vez las dos
corridas que repetían 8 de sus 13 tests.
- **Medido:** de 281,7 s a **182,4 s solo (−35 %)**, con los mismos 13 tests y las mismas afirmaciones.
- **Una guarda nueva:** un memo de un archivo de test solo se alcanza desde ese archivo. La guarda encontró
  nueve que ya se alcanzaban desde otro.

Es la primera versión (V1) de la fase 3 de la auditoría del cómputo, y el informe de la auditoría
(`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`) entra en este commit. **Ningún módulo del programa cambia**,
salvo el número de versión.

## 0. Lo que se encontró y lo que se decidió

- **La auditoría del cómputo entra con esta versión.** Sus fases 1 y 2 midieron, sin tocar el programa, dónde
  se va el tiempo, en 22 casos con su huella bit a bit. Las cuatro cifras que mandan:
  - cada método repite la búsqueda entera, rebanado incluido;
  - el paralelo da ×1,6–2,2 y no mejora `--jobs 4`;
  - `Mesh.locate` recorre la malla;
  - 495 s de los tests caros son cálculos repetidos.
- **El plan de la fase 3** son 18 versiones, cada una con el OK de la propietaria.
  - Lo diseñaron cinco agentes de solo lectura y lo atacaron cuatro revisores adversariales; ninguna
    identidad bit a bit quedó refutada.
  - La revisión corrigió cifras del informe antes de su commit: K13 −20 % y no −40 %; en los tests, **~295 s
    compartibles y no 495**, porque el resto se repite a propósito; Overall Slope en paralelo −18 a −25 % y
    no −35 %.
- **Tres hallazgos de la revisión, reportados y no corregidos (regla 6):**
  - **D379**, abierta en el banco: con «Use checks for depth, elevation, concave surface» apagado, el paseo
    de Optimize evalúa con una copia de la búsqueda, y sus rechazos no llegan a las notas de la corrida.
    - La sonda S9 lo confirma: 3 superficies rechazadas por una base sobre el terreno y ninguna nota.
    - Es la familia de D255. No mueve ningún número.
  - **A15, refutada al medirla:** la guarda del recolector de la ventana (D310) no frena un cálculo grande.
    En K03 hubo 33 liberaciones, solo una con algo que recoger, y los tiempos con y sin ella coinciden.
  - **La interfaz, medida** (K03, offscreen; son cotas inferiores):
    - **guardar el HDF5 tarda 47,2 s en el hilo de la ventana tras Calcular** (198 MB);
    - el *hover*, ~32 ms por movimiento dentro de una celda y ~0,4 s por cambio de celda;
    - Add Query, ~0,3 s por movimiento;
    - el hash del modelo, 0,2–4,7 ms, no es problema.

    Van al plan.
- **Las decisiones de la propietaria (2026-10-29):**
  - V1 tal cual;
  - `_best_of` reutiliza la corrida de la semilla 1234;
  - se corrige la atribución del «48 s → 12 s»;
  - el informe entra con V1.
- **Lo que se comparte:**
  - el recocido de Bishop con semilla 1234 sobre el talud de 12 m. Lo leen seis tests:
    `test_on_the_annealing_slope` (la primera semilla de su `_best_of`),
    `test_the_admissibility_gate_moves_the_number`,
    `test_the_population_it_walks_is_almost_all_admissible`,
    `test_inadmissible_surfaces_are_still_counted`,
    `test_the_critical_surface_leaves_the_steepest_segment` y
    `test_the_slope_limits_bound_where_the_ends_may_go`;
  - el mejor de Spencer sobre las semillas 1234 y 2024 en el caso 002. Lo leen dos tests.

  Son idénticos porque la búsqueda tira de su propio `random.Random`, y el paseo del suyo. Lo demuestra
  `TestTheSeedIsTheSearchsOwn`, de este mismo archivo. Y quien los lee, solo los lee.
- **`_best_of(first=...)`:** la corrida ya calculada ocupa el sitio de la primera semilla. Así el orden en
  que se comparan las corridas, y con él cuál gana entre dos factores iguales, no cambia.
- **Lo que no se comparte, porque su sentido es calcular otra vez:**
  - la corrida «apagada» de la regla 7 (`check_m_alpha=False`);
  - los límites de talud estrechos;
  - la pareja de reproducibilidad con semilla 77;
  - las pruebas del generador global;
  - las corridas sin semilla;
  - el banco de cuatro capas (otras semillas).
- **La ganancia, medida.** El archivo solo, antes y después, en la misma máquina y seguidos, con `TEMP`/`TMP`
  redirigidos para no tocar los tiempos de la propietaria: 281,7 s → 182,4 s.
  - **El diseñador estimaba ~80 s y son 99:** la corrida de Bishop con semilla 1234 cuesta ~16,5 s, no ~12.
  - **Ahora paga el primer lector por orden de nombre:** `test_it_is_below_the_circular_minimum_of_the_same_model`
    lleva el Spencer (29,7 s) y `test_the_critical_surface_leaves_the_steepest_segment` el Bishop (18,7 s).
  - **En la suite, según la proyección calibrada del informe:** la serie baja ~1,3 min. Con `--jobs 4` esta
    versión sola baja solo ~0,4 min, porque manda el tramo más lento; las cuatro versiones de tests juntas
    bajarían 3,1. La suite de esta versión tardó 29,2 min, pero el reloj de una sola corrida no mide
    esto: dos corridas iguales de 0.1.374 difirieron 3,7 min.
  - **`--fast` no cambia**, porque el archivo está en `tests/_slow.txt`. La lista no se reescribe: es
    decisión de la propietaria, tras todas las versiones de tests.
- **La guarda nueva, `test_shared_test_caches_v1378`.**
  - **Qué prohíbe:** que un ayudante que lee o escribe un caché de su módulo (o se llama `_shared_*`) se
    importe o se alcance desde otro archivo de test.
  - **Por qué:** el runner nunca saca un módulo de `sys.modules`. En la serie, el segundo archivo recibiría
    lo que calculó, y quizá cambió, el primero; con `--jobs`, un objeto nuevo. Una diferencia que depende
    del orden de los archivos es la peor de diagnosticar (regla 5).
  - **Encontró nueve que ya existían.** Todas reparten objetos que sus lectores solo leen, y van en su lista
    blanca con su porqué. **Una guarda un riesgo latente:** `test_probabilistic_all_failed_v1169._det`
    memoiza por el conjunto de métodos y no por el proyecto. Es segura solo porque sus tres llamadas pasan el
    mismo modelo Ej_1, construido de nuevo. Se reporta y no se toca.
  - **Un camino equivocado:** la primera versión analizaba todo archivo que mencionaba un caché y tardaba
    1,5 s. Ahora lee primero las líneas de importación y solo analiza quién importa y a quién: 0,87 s.
  - **Tiene sus controles:** casos sintéticos con una importación, un atributo, el memo propio y la detección
    de importaciones, para que pueda fallar.
- **La atribución del «48 s → 12 s».** El archivo que cita AGENTS.md es `test_focus_optimize_m4_v155`, que
  bajó compartiendo su superficie de partida (`CHANGELOG_v0.1.55.md`). No es un archivo de filtración, como
  decían `CHANGELOG_v0.1.70.md`, el comentario de `tests/test_drawdown_sweep_v170.py` y la skill
  `tests-numericos`; corregido en los tres. AGENTS.md lo decía bien.
- **La huella del banco de pruebas no aplica a esta versión.** Ningún módulo `ogr_*` cambia salvo la línea
  del número (`git diff`), y las 23 huellas dependen solo del programa y de los modelos.

## 1. Qué cambia

- `tests/test_annealing_inequality_v1119.py`: `_SHARED`, `_shared_bishop_1234()`, `_shared_spencer_best()` y
  `_best_of(..., first=None)`; ocho tests leen lo compartido.
- `tests/test_shared_test_caches_v1378.py` (nuevo, 6 tests).
- `docs/changelog/CHANGELOG_v0.1.70.md`, `tests/test_drawdown_sweep_v170.py` y
  `.claude/skills/tests-numericos/SKILL.md`: la atribución del «48 s → 12 s».
- `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md` (nuevo): el informe de la auditoría del cómputo.
- El número, en los nueve sitios, y el contador de tests de los dos README.

## 2. Qué se probó

- `test_annealing_inequality_v1119` solo, antes y después: 13 de 13 las dos veces.
- `test_shared_test_caches_v1378` solo: 6 de 6, 0,87 s.
- La suite entera con `--jobs 4`: **6718 de 6718, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 29,2 min.
- **Sin correr:**
  - la serie entera, que no toca: la última en verde fue `8c4dcd3`, hace 2 commits, y toca a los 100;
  - la huella de los 23 casos, porque no aplica (ver arriba).

## 3. Lo que queda

- **V2–V4,** las otras tres versiones de tests: la familia del desembalse de v130, Overall Slope, y las
  rejillas con el enjambre y las superficies de usuario. Después, las versiones del motor. Cada una con su OK.
- **La clave de `_det`**, que espera la decisión de la propietaria.

## Archivos

- `tests/test_annealing_inequality_v1119.py`
- `tests/test_shared_test_caches_v1378.py` (nuevo)
- `tests/test_drawdown_sweep_v170.py`
- `docs/changelog/CHANGELOG_v0.1.70.md`
- `docs/changelog/CHANGELOG_v0.1.378.md` (nuevo)
- `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md` (nuevo)
- `.claude/skills/tests-numericos/SKILL.md`
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
