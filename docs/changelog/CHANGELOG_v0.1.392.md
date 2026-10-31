# OGR Slip2D v0.1.392

**El solucionador de filtración calcula los flujos de los elementos solo para los resultados que publica** (V13 de la
fase 3 de la auditoría del cómputo, `docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).

**Lo medido**, con una corrida por proceso nuevo y en orden ABBA:
- **K16** (banco 05/015, consolidación 1-D transitoria, mallas de 600 y 2400 elementos): de 61,2 y 61,7 s a **49,6 y
  50,0 s (−19 %)**. Las llamadas a `element_fluxes` bajan de 1600 a 20.
- **K15** (banco 05/004, presa permanente no saturada con dren de pie, 2400 y 9600 elementos): de 9,1 y 9,8 s a **7,0
  y 7,7 s (−21 %)**. Las llamadas bajan de 58 a 2.
- En los dos casos son idénticos todos los campos publicados (cargas, velocidades, gradientes, reacciones y
  contadores), con el mismo hash.

Clase A: la misma función sobre los mismos números. Lo demuestra la huella de los 23 casos, 23 de 23 idénticos a
0.1.377.

## 0. Lo que se encontró

- **La puerta de medida.** En K16, `element_fluxes` se llamaba 1600 veces y se llevaba 12,0 s de 59,5; en K15, 58
  veces y 1,8 s de 9,2.
- **Quién lee los flujos.** Cada resolución lineal calculaba la velocidad y el gradiente de Darcy de cada elemento,
  pero los bucles de Picard que la llaman solo leen las cargas y las reacciones:
  - el permanente no saturado publica su solución final, y no el arranque saturado ni las pasadas;
  - un paso del transitorio publica su última resolución;
  - `solve_transient` publica el último paso de cada etapa.
- **Más que lo previsto en el plan.** Este preveía 1600 → 800 llamadas en K16 (los flujos de cada paso) y dejaba
  anotada la variante «solo el último paso de cada etapa». Se tomó esa variante, porque encaja con lo aprobado («los
  flujos solo para el resultado que sale del solucionador»): de los 800 pasos de K16 solo salen 20 resultados. El
  método público `step()` sigue devolviendo sus flujos, porque tests y scripts lo llaman directamente.
- **Las condiciones del plan, cumplidas:**
  - por defecto los flujos se siguen calculando (`solve`, `step`), y solo renuncian los llamadores internos;
  - `_picard_map`, del rescate, conserva los suyos, porque `test_rescue_fold_v1362` lee su velocidad;
  - en el transitorio, el resultado se completa también a la salida sin converger.
- **Lo que encontraron los mutantes.** La rama que resuelve el estado final después del rescate no la recorría ningún
  test: en una columna sin flujo, el campo permanente es el hidrostático, sea cual sea `kr`, y el bucle converge en una
  pasada. Los casos permanentes usan ahora una columna con carga también en la cabeza: hay flujo, una zona no saturada
  y 17 pasadas; con tope de 1, el bucle no converge y lo rescata Anderson.

## 1. Qué cambia

- `ogr_fem2d/solvers/seepage.py`:
  - **`SeepageSolver.solve(..., fluxes=True)`:** con `fluxes=False` deja vacíos la velocidad y el gradiente. Así lo
    llama el permanente no saturado para el arranque saturado (que solo se publica si falló, y un fallo sale antes de
    los flujos) y para cada pasada;
  - **`TransientSeepageSolver`:**
    - `_solve_linear_step(..., fluxes=True)`, igual que `solve`;
    - el bucle de Picard de cada paso resuelve sin flujos;
    - `_step(..., fluxes=True)` hace lo que hacía `step()`, que ahora lo llama;
    - `solve_transient` pide los pasos sin flujos y completa el último de cada etapa;
  - **`_with_fluxes(result)`:** calcula los flujos de un resultado que no los tiene, a partir de su propia carga y de
    su `kr`, que es lo mismo que se calculaba en la resolución.
- `tests/test_published_fluxes_v1392.py`, nuevo: 11 tests.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_published_fluxes_v1392.py`:**
  - **lo publicado es lo de 0.1.391, bit a bit:** el permanente no saturado (el que converge y el que rescata Anderson),
    un paso y las etapas de un transitorio, cada uno una vez por el camino nuevo y otra con todas las resoluciones
    calculando sus flujos;
  - **cada resultado publicado tiene los flujos de `element_fluxes`** sobre su carga y su `kr`, calculados en el test:
    el permanente, un paso de `step`, las etapas y una etapa cuyos pasos no convergieron;
  - **una vez por resultado publicado**, contado en una subclase: el permanente, 1 frente a pasadas + 2 en 0.1.391; un
    transitorio, uno por etapa que avanza;
  - **`solve` los sigue calculando por defecto**, y con `fluxes=False` las cargas y las reacciones no se mueven.

  Ninguno pasa de 0,55 s.
- **Seis mutantes,** cada uno cazado:
  - las pasadas del permanente con flujos;
  - la solución final sin flujos;
  - los flujos sin la `kr` del resultado;
  - la etapa sin completar;
  - `step()` sin flujos;
  - las pasadas del transitorio con flujos.
- **Los tests de filtración, transitorio, no saturado, rescate y agua subterránea,** juntos: 353 de 353.
- **El banco:** la huella de los 23 casos frente a 0.1.377, 23 de 23 idénticos (`all identical`, código 0). En las
  corridas de identidad, frente a las de 0.1.391:
  - K15, de 8,5 a 6,8 s;
  - K16, de 57,8 a 45,9 s;
  - K18 (agua subterránea y factores por etapa), de 7,5 a 6,8 s.
- **La suite entera con `--jobs 4`:** **6870 de 6870, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 25 min.

## 3. Lo que queda

- **V14–V18,** cada una con su OK. La siguiente es V14: la geometría y las matrices saturadas de cada elemento, una vez
  por solucionador.

## Archivos

- `ogr_fem2d/solvers/seepage.py`
- `tests/test_published_fluxes_v1392.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.392.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
