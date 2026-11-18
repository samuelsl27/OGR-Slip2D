# Extraer el núcleo compartido a `ogr-core`

> **Aprobada por el propietario (2026-10-27)**, con P1–P7 decididas (al
> final). Se empieza cuando v0.1.370 esté confirmada y exista
> `samuelsl27/OGR-Core`.

## Qué hace

Saca de este repositorio `ogr_core`, junto con la malla y la filtración que
hoy están en `ogr_fem2d`, a un repositorio propio, **OGR-Core** (distribución
`ogr-core`, paquete de importación `ogr_core`), del que Slip2D pasa a
depender con una versión fijada. Al terminar, Slip2D ya no contiene ningún
paquete llamado `ogr_fem2d`.

## Por qué

- Este `AGENTS.md` dice que `ogr_core` «se extraerá a su propio paquete
  cuando exista un segundo programa que lo use». **OGR FEM2D** es ese
  programa, y el propietario aprobó la extracción el 2026-10-27 (OGR-FEM2D,
  `docs/decisiones/ADR-0002-nucleo-compartido-ogr-core.md`).
- Copiar el núcleo en FEM2D haría que las reglas y la geometría acabaran
  diciendo cosas distintas en cada programa. Hacer que FEM2D dependa de
  `ogr-slip2d` arrastraría el motor de equilibrio límite entero.
- **El nombre `ogr_fem2d` es el del programa 03.** Su propio docstring lo
  dice («OGR FEM2D — 2D Finite Element Method solver for groundwater flow.
  Planned for v0.5.0»). Mientras Slip2D lo use, los dos programas no pueden
  instalarse en el mismo entorno sin sobrescribirse.

## Lo que hay hoy

Censo del 2026-10-27, sobre `680837b` (v0.1.369) más los cambios de v0.1.370
aún sin confirmar.

| | `ogr_core` | `ogr_fem2d` |
|---|---|---|
| Archivos `.py` | 89 | 10 |
| Líneas | ≈30 000 | ≈4 100 |
| Importa de otros `ogr_*` | ninguno; lo imponen `test_core_layering_v1340` y `_closed_v1346` | solo `ogr_core` |
| Dependencias externas | numpy, scipy, shapely, ezdxf, reportlab, h5py | numpy, scipy |
| Archivos que no son `.py` | ninguno | ninguno |
| Lo importan | `ogr_slip2d` 37, `ogr_gui` 37, `ogr_api` 18, `ogr_cli` 1, `examples` 1, tests 370 | `ogr_gui` 4, `ogr_api` 1, `ogr_slip2d` 1, tests 46 |

- **`ogr_core/fem/` ya existe** (v0.1.342, D337): contiene la malla (`Mesh`,
  `Node`, `Element`) y los datos de filtración (`SeepageResult`, las
  condiciones de contorno, `element_fluxes`). `ogr_fem2d` los reexporta en
  sus rutas antiguas. En `ogr_fem2d` quedan el generador de malla
  (`mesh/generator.py`, 563 líneas), el solver (`solvers/seepage.py`,
  2651), `solvers/bc_targets.py` (375), `solvers/streamlines.py` (343) y los
  códigos `seepage.*` (`messages.py`, 99).
- 28 archivos de `ogr_core` nombran las capas superiores, pero solo en
  comentarios y docstrings.
- **Tests**: de 443 archivos, 42 importan solo `ogr_core` y/o `ogr_fem2d`.
  De esos, 5 toman un modelo de un test de Slip2D (`test_slide_validation_ej1`,
  `test_interpret_i3_v153`, `test_coupling_v128`) y prueban la integración,
  así que se quedan. Uno más (`test_settings_coverage_v1103`) recorre también
  `ogr_slip2d`. Quedan **34 que se pueden mover** (`censo.md` §3; el primer recuento daba 36). Además, **24 tests
  nombran rutas dentro de `ogr_core/` u `ogr_fem2d/`**: leen sus fuentes
  (licencia, nombres de productos, suelo de Python, capas, censos de
  mensajes y de ajustes, versión) o abren un archivo concreto. Hay que
  revisarlos uno a uno.
- **El runner se niega a ejecutar** si un paquete `ogr_*` resuelve fuera del
  repositorio (`foreign_packages`, v0.1.89), y además importa
  `ogr_gui.gc_guard`. Con `ogr_core` en otro árbol, hoy diría «WRONG TREE» y
  saldría con 2.
- `test_version_consistency_v176` exige la misma versión en nueve sitios,
  entre ellos `ogr_core/__init__.py` y `ogr_fem2d/__init__.py`.
- CI: `.github/workflows/tests.yml` instala con `pip install -e ".[mcp]"`.
  No hay instalador congelado ni publicación en PyPI: Slip2D se instala
  desde el código.

## Criterios de aceptación

### OGR-Core

- [ ] Existe el repositorio OGR-Core con `ogr_core/`, que ya incluye el
      generador de malla, la filtración, las líneas de corriente y los
      códigos `seepage.*` en el destino que fije P1. Lleva `pyproject.toml`
      de `ogr-core` con **solo** las dependencias que el censo de
      importaciones encuentra, AGPL-3.0-or-later, `LICENSE`, `CLA.md`,
      `CONTRIBUTORS.md` y cabeceras SPDX.
- [ ] En un entorno virtual limpio, `pip install -e .` lo instala sin
      PySide6 ni ninguna otra dependencia exclusiva de Slip2D, y su suite
      completa pasa con código de salida 0.
- [ ] Su suite tiene los 34 archivos movidos **sin cambiar ningún valor
      esperado ni ninguna tolerancia**, más sus propias versiones de los
      tests de licencia, nombres de productos, suelo de Python, capas
      (censo estático y comprobación en tiempo de ejecución) y versión.
- [ ] Los tests de filtración contra soluciones cerradas (respuesta escalón
      erfc, medias armónica y aritmética por capas, Celia et al. 1990)
      pasan en OGR-Core.

### OGR Slip2D

- [ ] No quedan `ogr_core/` ni `ogr_fem2d/` en el árbol, y ninguna línea
      importa `ogr_fem2d` (búsqueda vacía).
- [ ] `pyproject.toml` declara `ogr-core` fijada a una etiqueta git (P3), y
      `pip install -e ".[mcp]"` en un entorno limpio la trae.
- [ ] La suite completa, sin argumentos, pasa con código 0. Su total de
      casos es el de antes menos los movidos, y las dos cifras se anotan
      en el changelog.
- [ ] **Ningún caso de validación cambia**: el diff de
      `tests/test_slide_validation_*`, `tests/test_acads_*` y `validacion/`
      está vacío (ninguno importa `ogr_fem2d`).
- [ ] **Mismos números al bit**: el código se mueve sin cambiar, así que
      los factores de seguridad de los casos de validación y un campo de
      filtración de referencia dan exactamente lo mismo antes y después
      (A/B en el mismo proceso, como manda `AGENTS.md`).
- [ ] El runner nombra los dos árboles, Slip2D y ogr-core, cada uno con su
      ruta, su commit y su versión. Se niega a ejecutar si `ogr_core` no es
      importable o si su versión no es la fijada.
- [ ] `test_version_consistency_v176` cubre los siete sitios que quedan y
      comprueba que la versión de `ogr_core` que se importa es la fijada.
- [ ] CI en verde en los dos repositorios.

### Documentación

- [ ] `AGENTS.md` (primer párrafo, estructura, capas, stack, lista de sitios
      de versión), `CONTRIBUTING.md`, los README, `docs/architecture.md` y
      `spec/constitution/*` dicen dónde vive el núcleo.
- [ ] Changelog de cada versión, registrando **qué se encontró**.

## Validación numérica

No hay cálculo nuevo. La referencia es una **identidad**: el código se mueve
sin cambiar, así que todo número debe salir idéntico. Los tests que validan
la filtración contra soluciones cerradas viajan con ella, y los casos de
validación del equilibrio límite se quedan aquí sin tocarse.

## Decisiones del propietario (2026-10-27)

| # | Pregunta | Decisión | Consecuencia |
|---|---|---|---|
| P1 | ¿Dónde van el generador de malla y la filtración? | **Dentro de `ogr_core/fem/`**, junto a la malla y los datos de filtración que ya están ahí desde v0.1.342 | **El núcleo contiene el solver de filtración compartido**, y la regla de capas tiene que decirlo |
| P2 | ¿Qué versión lleva `ogr-core`? | **Serie propia desde 0.1.0** | `ogr_core.__version__` pasa de 0.1.37x a 0.1.0. Como el núcleo ya tuvo versiones 0.1.0–0.1.37x dentro de Slip2D, un informe que cite solo «ogr_core 0.1.5» será ambiguo: el primer changelog de OGR-Core dice de qué commit de Slip2D sale, y el banner del runner y la ventana *Acerca de* dan las dos versiones |
| P3 | ¿Cómo obtienen Slip2D y su CI el núcleo? | **Dependencia git con etiqueta**: `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.1.0` | Nada se publica en PyPI. Si algún día Slip2D se publica allí, `ogr-core` tendrá que publicarse antes, porque PyPI no acepta dependencias por URL |
| P4 | ¿Cómo se comparte el runner de tests? | **Un único runner en `ogr-core`** (`ogr_core/testing/runner.py`, solo biblioteca estándar), con un gancho opcional para el `gc_guard` de la interfaz | Los `tests/_runner.py` de Slip2D y FEM2D quedan como envolturas finas |
| P5 | ¿Historia de git en OGR-Core? | **Historia nueva**; el primer commit cita el commit de Slip2D del que sale | Sin herramientas nuevas; la historia completa sigue en Slip2D |
| P6 | ¿Carpeta local y nombre en GitHub? | **`C:\Samuel\OpenGeoRock_Core\OGR-Core`** y **`samuelsl27/OGR-Core`** | Los repositorios los crea el propietario |
| P7 | ¿Cuándo, y con qué versiones? | **Dos versiones de parche** (F1 y F3), en la rama `dev/extraer-ogr-core`, después de confirmar v0.1.370 | Hoy hay 21 archivos modificados sin confirmar, entre ellos `ogr_core/__init__.py`, `ogr_core/report/report_generator.py` y `ogr_fem2d/__init__.py` |

## Fuera de alcance

- `ogr_gui`, `ogr_api`, `ogr_mcp` y `ogr_cli` se quedan en Slip2D. Qué
  partes genéricas de la interfaz se comparten se decide en la fase 1 de
  OGR FEM2D.
- `ogr_data` (marcador del programa 02).
- Crear los repositorios en GitHub y publicar nada en PyPI (salvo que P3
  diga otra cosa).
- Cualquier cambio en el cálculo o en sus números, y renombrar clases o
  funciones. (Lo único visible que cambia es que *Acerca de* da también la
  versión del núcleo, por P2.) Los comentarios que nombran capas superiores solo se tocan
  donde, tras la extracción, digan algo falso.
- Código de OGR FEM2D.
