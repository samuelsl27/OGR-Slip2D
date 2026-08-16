# OGR Slip2D v0.1.80 — la suite no era lenta: era indivisible

Esta versión empieza con una pregunta que resultó estar mal planteada, y el
trabajo que valió la pena fue averiguar por qué.

---

## La pregunta: ¿serviría un linter tipo Oxlint para acelerar los tests?

No, y conviene dejar dicho por qué, porque la confusión es fácil de repetir.

**Oxlint y ESLint son linters de JavaScript.** No ejecutan tests: hacen
análisis estático del código (variables sin usar, imports muertos, patrones
sospechosos). Y no leen Python — no hay plugin, es que el parser es de otro
lenguaje. Oxlint es rápido de verdad, unas 50–100× más que ESLint por estar
escrito en Rust, pero lo que acelera es **el linting**, no la suite.

En los proyectos JS donde parece que "los tests van más rápido con Oxlint",
lo que ocurrió es que su etapa de *lint* en CI tardaba minutos y ahora tarda
segundos. El test runner sigue siendo el mismo y tarda lo mismo.

El equivalente Python existe y se llama Ruff. Está **medio adoptado en este
repositorio desde hace tiempo y nunca se ha ejecutado**: `pyproject.toml`
tiene `[tool.ruff]` con `line-length` y `target-version`, y lo declara en
`dev`, pero no está instalado ni hay job de CI que lo llame. Es una decisión
a medias, y sigue pendiente después de esta versión — con la advertencia de
que tampoco habría acelerado nada: un linter sobre las 66 000 líneas del
repositorio tarda menos de un segundo.

---

## Lo que apareció al medir

Antes de tocar nada se cronometraron los 99 archivos por separado, en una
corrida limpia y sin nada más compitiendo por los núcleos. **1706 tests,
518.6 s.** Lo interesante no es el total —AGENTS.md ya avisa de que el reloj
total varía ±40 s y no es una medida— sino el reparto:

| | archivos | tests | tiempo |
|---|---|---|---|
| Los 4 más lentos | 4 | 83 | 219 s — **42 %** |
| Los 20 más lentos | 20 | 460 | **85 %** |
| Los que bajan de 1 s | 58 | 798 (**47 % de los tests**) | 9.3 s — **1.8 %** |

Los cuatro monstruos:

```
80.2s   35 tests  test_transient_v130.py
60.0s   22 tests  test_overall_slope_v137.py
47.1s   17 tests  test_slide_validation_ej1.py
32.1s    9 tests  test_validation_cases.py
```

Casi la mitad de los tests son gratis. El tiempo es filtración transitoria,
mallado, búsqueda de superficies y widgets Qt de verdad. Ningún linter toca
un solo segundo de eso.

## El hallazgo de verdad

Al mirar el runner para instrumentarlo apareció algo que llevaba ahí desde
el principio y que nadie había nombrado: **`tests/_runner.py` no aceptaba
argumentos**. `main(root)` y los 99 archivos, siempre.

Tocar `ogr_fem2d/seepage.py` costaba siete minutos aunque solo importasen
dos archivos que suman 12 s. El problema nunca fue que la suite fuera lenta:
era que **no se podía no ejecutarla entera**.

---

## Lo que se ha hecho

`tests/_runner.py` acepta una selección:

```bash
python tests/_runner.py                          # todo (sin cambios)
python tests/_runner.py transient                # por fragmento de nombre
python tests/_runner.py transient seepage        # unión
python tests/_runner.py tests/test_mesh_v125.py  # por ruta
python tests/_runner.py -k erfc                  # por nombre de test
python tests/_runner.py --list transient         # enseña la selección
```

El ciclo típico de desarrollo pasa de siete minutos a segundos.

### El peligro que introduce un filtro, y la guarda que lo tapa

Es lo único genuinamente arriesgado del cambio, y merece nombrarse. Con la
implementación ingenua, `python tests/_runner.py transiant` —una letra
cambiada— no encontraría ningún archivo e imprimiría:

```
Total: 0    Passed: 0    Failed: 0
```

y saldría con **código 0**. Un falso verde perfecto: indistinguible de una
suite que pasó. Por eso una selección vacía **sale con código 2** y explica
qué se pidió, con una sugerencia de lo que probablemente se quería decir:

```
No test file matches ['transiant'].
Did you mean: test_transforms, test_transient_v130
100 files available — `python tests/_runner.py --list` shows them all.
```

Lo mismo si `-k` no casa con nada dentro de los archivos seleccionados.

### Y la segunda forma de mentir: parecer una suite completa

Un `Total: 35  Passed: 35  Failed: 0` pegado en un informe es idéntico
tanto si vienen de 35 tests como si vienen de 1706. Así que toda ejecución
filtrada imprime, **antes y después de los totales**:

```
FILTERED RUN — 1 of 100 files, patterns: ['transient'] — NOT the full suite
```

Repetido a propósito: el aviso tiene que viajar pegado a los números, o no
sirve para nada en un registro que se lee por el final.

### Un camino equivocado que costó rehacerlo

La primera versión trataba el patrón como ruta cuando parecía una ruta:
`Path(patrón).resolve()` comparado con cada archivo. Funciona… desde el
directorio raíz del repositorio. Desde cualquier otro,
`tests/test_mesh_v125.py` no resuelve a nada y el patrón **selecciona cero
archivos en silencio** — el falso verde otra vez, por la puerta de atrás.

La regla buena no mira el sistema de archivos: normaliza el patrón quitando
la parte de directorio y la extensión, y compara subcadenas. Así
`transient`, `test_transient_v130.py` y `tests/test_transient_v130.py`
significan lo mismo se escriban desde donde se escriban. Una regla en lugar
de dos, y ninguna dependencia del directorio actual.

### `-k` es una subcadena, y lo dice

No se ha implementado la gramática `and`/`or`/`not` del `-k` de pytest, a
propósito. Un parseador booleano a medias que interprete mal un `not`
selecciona un conjunto distinto del que el lector cree, y no avisa. Una
subcadena documentada no se puede malinterpretar así.

---

## Lo que **no** se ha hecho, y por qué

- **Paralelizar el runner.** Está medido: reparto voraz por archivo sobre 8
  núcleos daría **80 s (6.5×)**, con el techo puesto por
  `test_transient_v130.py`, y el arranque en frío de un proceso con
  PySide6+SciPy son 1.9 s, despreciable. El motivo de no hacerlo aún no es
  técnico: **aislar archivos en procesos separados esconde justo las fugas
  de estado que la regla 5 existe para cazar**. El bug del idioma que solo
  aparecía en la suite completa no habría aparecido nunca. Si se hace,
  el CI en serie tiene que seguir siendo el autoritativo.
- **Ruff.** Pendiente, y sin prisa: no acelera los tests.
- **Partir el CI en un job rápido y otro lento.** El job de licencia ya usa
  esa idea; extenderla a versión, i18n y python floor daría aviso en menos
  de un minuto en vez de en siete.
- **Adelgazar los cuatro archivos caros.** `transient` gasta 2.3 s por test
  y hay precedente de ganar 4× compartiendo geometría, pero aquí manda la
  regla 6: bajar la resolución de una malla para ganar segundos puede
  desactivar en silencio la validación contra la solución erfc. Antes de
  tocarlos hay que saber si la finura *es* el invariante.

---

## Dos cosas que aparecieron de paso

**Los dos README llevaban tiempo mintiendo.** Anunciaban «**1280** tests en
verde», «18 000 líneas de tests» y «la suite tarda unos 290 s», insignia
incluida. Los números reales son **1724 tests**, 23 300 líneas y entre 5 y
7½ minutos; el 1280 venía de v0.1.53 y el changelog de v0.1.79 ya decía
1706. Corregidos, y el tiempo se expresa ahora como la horquilla honesta
que usa AGENTS.md en vez de un número redondo que ningún reloj reproduce.

**Editar el árbol mientras corre la suite produce un fallo falso.** La
primera corrida completa terminó `1723 passed, 1 failed`, en
`test_about_version_is_not_a_stale_literal`: `VERSION` valía `0.1.79` y
`pyproject.toml` decía `0.1.80`. Ninguno de los dos estaba mal — el módulo
se había importado antes de subir la versión y el `.toml` se leyó después.
El test hizo justo su trabajo; el error fue del procedimiento. La suite que
vale es la que corre con el árbol quieto.

## Archivos

- `tests/_runner.py` — `select_files()`, `match_test()`, `_declared_tests()`
  y `_suggest()` nuevas; `_count_tests()` pasa a recibir la selección para
  que el denominador del progreso no mienta bajo `-k`; `main()` acepta
  `patterns`, `k` y `list_only`; parseo con `argparse`.
- `tests/test_runner_selection_v180.py` — **nuevo**, 18 tests.
- `AGENTS.md`, `CONTRIBUTING.md`, `docs/EMPEZAR_EN_VSCODE.md`,
  `README.es.md` — las formas filtradas, con el aviso de que no valen como
  evidencia para publicar.
- `.vscode/tasks.json` — tarea *Tests: selección*, que pregunta el patrón.
- `.claude/settings.json` — las reglas del runner pasan a `:*`. Eran
  coincidencia exacta, así que cualquier invocación con patrón habría
  empezado a pedir permiso.

## Qué protege el test nuevo

Que **sin argumentos no ha cambiado nada** —la lista de archivos es la misma
y en el mismo orden, que es lo que ejecuta el CI—, que un patrón selecciona
estrictamente menos (regla 7: el control mueve el número), que las tres
formas del patrón coinciden, que el emparejamiento no distingue mayúsculas,
que la selección no reordena (la reproducibilidad del orden es lo que
sostiene la regla 5) y que **una selección vacía sale con código distinto de
cero** y explica qué pasó.

Lleva además una advertencia para quien lo edite: `main()` solo puede
llamarse ahí por caminos que retornan *antes* del bucle de ejecución. Una
llamada que llegue al bucle mientras ese archivo está seleccionado lo
ejecutaría dentro de sí mismo, indefinidamente.
