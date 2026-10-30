# OGR Slip2D v0.1.385

**Dos cambios en una versión, por decisión de la propietaria.**
- **V7:** las evaluaciones hechas fuera de una búsqueda congelan las cachés de regiones, como ya hacía la búsqueda.
- **D380:** una copia deja de heredar el congelado del proyecto del que sale.

**Lo medido en K19** (banco 028, Global Minimum sobre su círculo, N = 250 y 1000, en el proceso principal), con un
A/B en un mismo proceso, en el orden nuevo, viejo, viejo, nuevo, nuevo:
- gm1000 pasa de 12,06 y 14,19 s a **7,30 y 7,30 s**;
- gm250 pasa de 2,90 y 3,55 s a **1,92 y 1,89 s**;
- los resultados son idénticos en las cinco corridas.

Los dos viejos difieren un 17 % entre sí, así que manda el trabajo: las firmas de las regiones pasan de 129 162 a
**2710 (−98 %)**, unas dos por muestra, y las evaluaciones de muestra de 15,5 a 8,1 s.

**En el banco de pruebas,** una corrida de cada caso frente a la de 0.1.377:
- K19 pasa de 15,6 a **9,7 s** (gm250, de 2,72 a 1,55; gm1000, de 11,82 a 7,05);
- en K20, la parte de Global Minimum y sensibilidad, de 13,3 a 10,9 s;
- el paseo de Optimize de K10, de 12,2 a 10,9 s;
- el de K09 no se mueve (6,25 y 6,38 s).

La parte V7 es la séptima versión de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`)
y es de clase B: idéntica por construcción, y lo demuestran la huella de los 23 casos, 23 de 23 idénticos a 0.1.377, y serie igual a paralelo en los 12 casos
con pool. La parte D380 es
una corrección: cambia el número solo donde estaba mal, en copias hechas mientras otro hilo tenía el proyecto
congelado.

## 0. Lo que se encontró y lo que se decidió

- **La puerta de medida se reproduce al elemento:** en K19, 129 162 firmas, 125 400 resoluciones de regiones y 1250
  evaluaciones de muestra, como en 0.1.377. La firma se lleva 5,5 de los 13,6 s de esas evaluaciones (41 %).
- **Las decisiones de la propietaria:**
  - congelar dentro de `optimize_surface`, para todas sus puertas;
  - que `evaluate_surfaces` pase por el mismo ayudante;
  - arreglar D380 en esta versión;
  - arreglar también las copias de nivel del desembalse, de la misma familia.
- **El ayudante** (`ogr_slip2d/search.py`, `frozen_evaluation(search, project, *, fallback=True)`):
  - **ya congelado** (un paseo dentro de una búsqueda): no hace nada;
  - **si no:** vacía la caché de capas débiles de la búsqueda, entra en `project.regions_frozen()` y, al salir,
    suelta el congelado y vuelve a vaciar la caché. Esa caché vive en la búsqueda, que estas puertas reutilizan
    entre proyectos (cada muestra es otro clon), y un proyecto congelado se fía de ella la haya construido quien la
    haya construido;
  - **si entrar lanza:** entrar resuelve en el acto las regiones y la caja. Con `fallback`, la evaluación sigue sin
    congelar y falla donde fallaba; sin él, el error sale del ayudante;
  - **el cuerpo no se captura nunca:** una excepción de la evaluación sale como entró, con el congelado suelto.
- **Dónde entra:**
  - **la muestra de Global Minimum y el punto de sensibilidad,** dentro de `probabilistic._evaluate_on`, sobre el
    clon ya perturbado y preparado;
  - **la sonda de D88,** alrededor de su despacho directo, que se queda como estaba: un test cuenta las llamadas a
    `_evaluate_on` y la comprobación `d88` del banco busca ese nombre en el texto de la función;
  - **`optimize_surface`,** tras sus dos salidas sin evaluación y **antes** de `_evaluator_for`. Con las
    comprobaciones de superficie apagadas, Optimize puntúa contra una copia superficial de la búsqueda, que se lleva
    la caché tal como la encuentra; el congelado la vacía antes. El paseo pasó tal cual a `_walk`;
  - **`evaluate_surfaces`,** sin respaldo. Entraba en el congelado por su cuenta y dejaba salir el error de un modelo
    que no se puede congelar. Con respaldo, un círculo alejado del modelo se habría rechazado por no tocar el terreno
    y habría respondido None.
- **La auditoría previa** (tres agentes: los sitios, lo que cambia dentro de un congelado y quién podría verlo):
  - **el respaldo hace falta:** con una asignación de región sin punto de clic, entrar lanza `KeyError`, mientras que
    la evaluación sin congelar de un círculo descartado por la caja devuelve None;
  - **el orden en Optimize:** la copia superficial se haría antes de vaciar la caché;
  - **las trampas del ayudante:** que el `try` solo cubra la entrada, y que el `yield` del respaldo quede fuera del
    `except`. Si se tragara la excepción del cuerpo, una muestra de Global Minimum se quedaría con el resultado de la
    anterior;
  - **la anomalía D380,** que se te reportó antes de tocarla (regla 6).
- **D380, las copias detached:**
  - **qué pasaba:** `detached_copy`, y `clone_project`, que pasa por ella, copiaban la profundidad de congelado. Una
    copia hecha mientras su proyecto estaba congelado se fiaba para siempre de sus cachés, la adherencia de un anclaje
    entre ellas;
  - **medido:** con el nivel freático 5 m más alto, 1,9559 en vez de 1,9019 (+2,8 %); con 8 m, 1,8633 en vez de
    1,7262 (+7,9 %);
  - **cuándo ocurría:** cuando el puente del agente copiaba el proyecto vivo mientras la ventana calculaba. Siete
    operaciones de `ogr_api` copian así: analysis_run, statistics_run, back_analysis_run, optimize_run,
    surface_evaluate, groundwater_run y drawdown_sweep_run;
  - **el arreglo:** `detached_copy` pone a 0 la profundidad de la copia.
- **D380, las copias de nivel del desembalse** (lo encontró la revisión):
  - **qué pasaba:** `level_project` y `project_at_level` (`ogr_core/hydraulic/drawdown_levels.py`) hacen una copia
    superficial dentro del congelado del análisis, y compartían la caché de adherencia del proyecto. Una lectura del
    agente (`settings_diagnostics` → `_bond_profiles`) que la llenaba mientras la ventana calculaba dejaba al nivel
    bajado con el perfil del embalse lleno;
  - **medido:** B-bar, F = 0,8197 en vez de 0,6287;
  - **lo que hacía V7 con esto:** en HEAD ya lo sufrían Compute y la corrida determinista de la estadística. Con V7
    lo habría sufrido también Optimize lanzado desde el menú: con la lectura, 0,9267 en vez de 0,6903;
  - **el arreglo:** `_water_copy` vacía la caché de adherencia de la copia y conserva el congelado, que es lo que le
    da la velocidad. En una corrida que nadie lee, esa caché ya estaba vacía ahí y no se mueve ningún número.
- **La revisión** (cuatro revisores y un verificador por hallazgo):
  - **identidad de V7: ningún problema.** El revisor comparó con HEAD en ocho experimentos, todos bit a bit iguales:
    anclajes, desembalse del Apéndice G con anclajes, Ky, capas débiles, norma de diseño, combinaciones de los tres
    últimos y un modelo que no se puede congelar;
  - **D380:** las copias de nivel (arriba);
  - **los tests:** un hueco real, que Optimize siga rechazando su arranque cuando congelar lanza, y dos
    endurecimientos (la caché vaciada al salir por una excepción y el recuento sobre una polilínea);
  - **observadores:** el censo de frases de `tests/test_search_notes_v1349.py` dejó de ver el paseo al pasar este a
    `_walk`. `_walk` entra en su lista. En el banco de pruebas se corrigieron dos descripciones obsoletas.
- **Lo que queda frágil, sin disparar:** la copia de prueba de Ky comparte la caché de adherencia, lo que es correcto
  porque el perfil no lee kh y kv coincide. Un tipo de soporte cuyo `interface_tau` leyera `project.seismic`
  rompería esa igualdad.

## 1. Qué cambia

- `ogr_slip2d/search.py`: `frozen_evaluation` y `_forget_weak_bands`.
- `ogr_slip2d/probabilistic.py`: `_evaluate_on` y la sonda de D88, congeladas.
- `ogr_slip2d/optimize.py`: `optimize_surface` congela antes de elegir el evaluador; el paseo, tal cual, en `_walk`.
- `ogr_slip2d/analysis_runner.py`: `evaluate_surfaces` por el ayudante, sin respaldo.
- `ogr_core/project/copies.py`: `detached_copy` pone a 0 la profundidad de la copia (D380).
- `ogr_core/hydraulic/drawdown_levels.py`: `_water_copy`, la copia de nivel sin la caché de adherencia (D380).
- `ogr_core/project/project.py` y `ogr_slip2d/support_integration.py`: los docstrings de `regions_frozen` y de
  `_bond_profiles`, que prometían más de lo que hacían las copias.
- `tests/test_frozen_evaluation_v1385.py`, nuevo: 17 tests.
- `tests/test_search_notes_v1349.py`: el censo incluye `_walk`.
- El número, en los nueve sitios, y el contador de los dos README (6784).

## 2. Qué se probó

- `tests/test_frozen_evaluation_v1385.py`:
  - las reglas del ayudante: ya congelado, la caché vaciada a los dos lados y en una excepción, el cuerpo sin
    capturar (también una `BaseException`), el respaldo y su ausencia;
  - cada puerta frente a la misma llamada con un congelado neutro (`Project.regions_frozen` sustituido y devuelto en
    `finally`), con un modelo con anclaje y nivel freático: Global Minimum, la sensibilidad, un paseo de Optimize y
    una superficie fija;
  - el trabajo contado: dos firmas por muestra, en círculo y en polilínea, y al entrar en un paseo;
  - `evaluate_surfaces` sigue lanzando, y Optimize sigue rechazando su arranque, cuando congelar lanza;
  - una caché de capas débiles de otro modelo no llega al paseo;
  - D380: las copias hechas en congelado no lo están; una muestra copiada en congelado lee su propio nivel
    freático; y el nivel bajado del desembalse construye su propia adherencia.

  Tardan 1,2 s el que más, el primero que carga los anclajes.
- Trece mutantes del código, cada uno cazado por al menos un test.
- Los tests que protegen estas puertas, solos: 203 de 203. El censo de frases, en verde con `_walk`.
- El `verificar_cierres` del manual 02, para las 22 fichas que leen estas funciones (D85, D88, D89, D91, D92, D93,
  D95, D98, D127, D128, D129, D161, D164, D218b, D233, D241, D244, D246, D248, D251, D253 y D259): todas cubiertas,
  sin ninguna bajada.
- La huella de los 23 casos frente a 0.1.377, con el código final: 23 de 23 idénticos (`all identical`, código 0). Los 12
  gemelos en serie, idénticos a los de 0.1.377 y a su corrida en paralelo (código 0). Una corrida anterior, antes del
  arreglo del desembalse, dio lo mismo.
- La suite entera con `--jobs 4`: **6784 de 6784, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 27,1 min. La
  última serie en verde fue `8c4dcd3`, hace 9 commits.

## 3. Lo que queda

- **V8–V18,** cada una con su OK. La siguiente es V8: el umbral del pool por círculos efectivos. La rejilla de 539
  círculos del modelo 010, que con el índice de V5 tarda 1,2–1,4 s en serie y 1,8–2,7 s con el pool, es un dato para
  ella.
- **D380 en el banco:** registrada en `ERRORES_Y_DISCREPANCIAS.md`, como resuelta en esta versión. Falta su cierre
  formal: la instantánea, el índice de cerrados, `CIERRE`, la comprobación `d380()` y los prompts.

## Archivos

- `ogr_slip2d/search.py`
- `ogr_slip2d/probabilistic.py`
- `ogr_slip2d/optimize.py`
- `ogr_slip2d/analysis_runner.py`
- `ogr_slip2d/support_integration.py`
- `ogr_core/project/copies.py`
- `ogr_core/project/project.py`
- `ogr_core/hydraulic/drawdown_levels.py`
- `tests/test_frozen_evaluation_v1385.py` (nuevo)
- `tests/test_search_notes_v1349.py`
- `docs/changelog/CHANGELOG_v0.1.385.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)
